"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ComposedChart } from "recharts"
import { useAnalysisStore } from "@/lib/store"
import { apiClient } from "@/lib/api-client"
import { deriveOverlayHistogramRenderState } from "@/lib/fcs-compare-acceptance-helpers"
import { runOverlayHistogramWorker } from "@/lib/fcs-series-worker-client"
import { buildOverlayHistogramCacheKey, estimateSeriesBytes } from "@/lib/fcs-series-cache-utils"
import { Layers, Eye, EyeOff, Loader2, RefreshCw, AlertCircle } from "lucide-react"
import { useState, useEffect, useMemo, useRef } from "react"

interface OverlayHistogramChartProps {
  title?: string
  parameter?: string
  loadingBySampleId?: Record<string, boolean>
  errorsBySampleId?: Record<string, string>
  onRetrySample?: (sampleId: string) => void
  replicateRenderMode?: "standard" | "histogram-average" | "merged-points"
  visibleSampleIds?: string[]
  primaryCompareSampleId?: string | null
  primarySampleId?: string | null
  compareScatterBySampleId?: Record<string, Array<{ x: number; y: number; diameter?: number }>>
  sampleLabelsById?: Record<string, string>
}

type HistogramSeriesPoint = { bin: string; binValue: number; [key: string]: number | string }
type HistogramSeriesDescriptor = {
  key: string
  sampleId: string
  label: string
  color: string
  isPrimary: boolean
}
const FIXED_HISTOGRAM_BINS = 50

const COMPARISON_PALETTE = [
  "#F97316",
  "#0EA5E9",
  "#22C55E",
  "#EAB308",
  "#EF4444",
  "#14B8A6",
  "#F43F5E",
]

function resolvePeerColor(index: number, secondaryColor: string): string {
  const safeSecondaryColor = typeof secondaryColor === "string" && secondaryColor.trim().length > 0
    ? secondaryColor
    : "#F97316"

  if (index === 0) {
    return safeSecondaryColor
  }

  const normalizedSecondary = safeSecondaryColor.trim().toLowerCase()
  const dedupedPalette = COMPARISON_PALETTE.filter((color) => color.trim().toLowerCase() !== normalizedSecondary)
  const palette = dedupedPalette.length > 0 ? dedupedPalette : COMPARISON_PALETTE
  return palette[(index - 1) % palette.length]
}

function extractHistogramValue(point: { x: number; y: number; diameter?: number }, parameter: string): number | null {
  if (parameter === "FSC-A") return point.x
  if (parameter === "SSC-A") return point.y
  if (parameter === "size" && point.diameter) return point.diameter
  return point.x
}

function buildHistogramDataLocal(params: {
  primaryValues: number[]
  secondaryValues: number[]
  primaryMean: number
  primaryStd: number
  secondaryMean: number
  secondaryStd: number
  bins?: number
}): { data: HistogramSeriesPoint[]; isApproximate: boolean } {
  const primaryValues = params.primaryValues.filter((value) => Number.isFinite(value))
  const secondaryValues = params.secondaryValues.filter((value) => Number.isFinite(value))

  const hasRealPrimary = primaryValues.length > 0
  const hasRealSecondary = secondaryValues.length > 0
  const hasRealData = hasRealPrimary || hasRealSecondary

  const bins = Math.max(10, Math.min(200, params.bins ?? 50))

  const allValues = [...primaryValues, ...secondaryValues]
  let minVal: number
  let maxVal: number

  if (allValues.length > 0) {
    const sorted = [...allValues].sort((a, b) => a - b)
    const q01 = sorted[Math.floor(sorted.length * 0.01)] ?? sorted[0]
    const q99 = sorted[Math.floor(sorted.length * 0.99)] ?? sorted[sorted.length - 1]
    minVal = q01
    maxVal = q99

    if (!hasRealPrimary) {
      minVal = Math.min(minVal, params.primaryMean - 3 * params.primaryStd)
      maxVal = Math.max(maxVal, params.primaryMean + 3 * params.primaryStd)
    }
    if (!hasRealSecondary) {
      minVal = Math.min(minVal, params.secondaryMean - 3 * params.secondaryStd)
      maxVal = Math.max(maxVal, params.secondaryMean + 3 * params.secondaryStd)
    }
  } else {
    minVal = Math.min(params.primaryMean - 3 * params.primaryStd, params.secondaryMean - 3 * params.secondaryStd)
    maxVal = Math.max(params.primaryMean + 3 * params.primaryStd, params.secondaryMean + 3 * params.secondaryStd)
  }

  if (!Number.isFinite(minVal) || !Number.isFinite(maxVal) || maxVal <= minVal) {
    return { data: [], isApproximate: true }
  }

  const binSize = (maxVal - minVal) / bins
  const data: HistogramSeriesPoint[] = []

  for (let i = 0; i < bins; i += 1) {
    const binStart = minVal + i * binSize
    const binEnd = binStart + binSize
    const binMid = binStart + binSize / 2

    const primaryValue = hasRealPrimary
      ? primaryValues.filter((value) => value >= binStart && value < binEnd).length
      : Math.exp(-0.5 * Math.pow((binMid - params.primaryMean) / params.primaryStd, 2)) * 100

    const secondaryValue = hasRealSecondary
      ? secondaryValues.filter((value) => value >= binStart && value < binEnd).length
      : Math.exp(-0.5 * Math.pow((binMid - params.secondaryMean) / params.secondaryStd, 2)) * 100

    data.push({
      bin: binMid.toFixed(0),
      binValue: binMid,
      primary: Math.round(primaryValue),
      secondary: Math.round(secondaryValue),
    })
  }

  if (hasRealPrimary !== hasRealSecondary && data.length > 0) {
    const realSide = hasRealPrimary ? "primary" : "secondary"
    const gaussSide = hasRealPrimary ? "secondary" : "primary"
    const maxReal = Math.max(...data.map((entry) => entry[realSide]), 1)
    const maxGauss = Math.max(...data.map((entry) => entry[gaussSide]), 1)
    const scale = maxReal / maxGauss

    data.forEach((entry) => {
      entry[gaussSide] = Math.round(entry[gaussSide] * scale)
    })
  }

  return { data, isApproximate: !hasRealData }
}

function computeHistogramCounts(values: number[], minVal: number, maxVal: number, bins: number): number[] {
  const counts = Array.from({ length: bins }, () => 0)
  const width = maxVal - minVal
  if (width <= 0) return counts

  for (const value of values) {
    if (!Number.isFinite(value) || value < minVal || value > maxVal) continue
    const normalized = (value - minVal) / width
    const index = Math.min(bins - 1, Math.max(0, Math.floor(normalized * bins)))
    counts[index] += 1
  }
  return counts
}

function buildHistogramDataForSeries(params: {
  seriesValuesByKey: Record<string, number[]>
  bins?: number
}): { data: HistogramSeriesPoint[]; isApproximate: boolean } {
  const bins = Math.max(10, Math.min(200, params.bins ?? 50))
  const entries = Object.entries(params.seriesValuesByKey).map(([key, values]) => [
    key,
    values.filter((value) => Number.isFinite(value)),
  ] as const)
  const allValues = entries.flatMap(([, values]) => values)

  if (allValues.length === 0) {
    return { data: [], isApproximate: true }
  }

  const sorted = [...allValues].sort((a, b) => a - b)
  const minVal = sorted[Math.floor(sorted.length * 0.01)] ?? sorted[0]
  const maxVal = sorted[Math.floor(sorted.length * 0.99)] ?? sorted[sorted.length - 1]
  if (!Number.isFinite(minVal) || !Number.isFinite(maxVal) || maxVal <= minVal) {
    return { data: [], isApproximate: true }
  }

  const countsByKey: Record<string, number[]> = {}
  entries.forEach(([key, values]) => {
    countsByKey[key] = computeHistogramCounts(values, minVal, maxVal, bins)
  })

  const binSize = (maxVal - minVal) / bins
  const data = Array.from({ length: bins }, (_, index) => {
    const binMid = minVal + (index + 0.5) * binSize
    const row: HistogramSeriesPoint = {
      bin: binMid.toFixed(0),
      binValue: binMid,
    }
    entries.forEach(([key]) => {
      row[key] = countsByKey[key]?.[index] ?? 0
    })
    return row
  })

  return { data, isApproximate: false }
}

function buildHistogramDataWithAveragedReplicates(params: {
  primaryValues: number[]
  replicateValues: number[][]
  bins?: number
}): { data: HistogramSeriesPoint[]; isApproximate: boolean } {
  const bins = Math.max(10, Math.min(200, params.bins ?? 50))
  const primaryValues = params.primaryValues.filter((value) => Number.isFinite(value))
  const replicateSets = params.replicateValues
    .map((set) => set.filter((value) => Number.isFinite(value)))
    .filter((set) => set.length > 0)

  const allValues = [
    ...primaryValues,
    ...replicateSets.flatMap((set) => set),
  ]
  if (allValues.length === 0) {
    return { data: [], isApproximate: true }
  }

  const sorted = [...allValues].sort((a, b) => a - b)
  const minVal = sorted[Math.floor(sorted.length * 0.01)] ?? sorted[0]
  const maxVal = sorted[Math.floor(sorted.length * 0.99)] ?? sorted[sorted.length - 1]
  if (!Number.isFinite(minVal) || !Number.isFinite(maxVal) || maxVal <= minVal) {
    return { data: [], isApproximate: true }
  }

  const primaryCounts = computeHistogramCounts(primaryValues, minVal, maxVal, bins)
  const replicateCounts = replicateSets.map((set) => computeHistogramCounts(set, minVal, maxVal, bins))
  const binSize = (maxVal - minVal) / bins

  const data: HistogramSeriesPoint[] = Array.from({ length: bins }, (_, i) => {
    const binMid = minVal + (i + 0.5) * binSize
    const secondaryAvg = replicateCounts.length > 0
      ? Math.round(replicateCounts.reduce((sum, counts) => sum + counts[i], 0) / replicateCounts.length)
      : 0

    return {
      bin: binMid.toFixed(0),
      binValue: binMid,
      primary: primaryCounts[i],
      secondary: secondaryAvg,
    }
  })

  return {
    data,
    isApproximate: primaryValues.length === 0 && replicateSets.length === 0,
  }
}

export function OverlayHistogramChart({ 
  title = "Size Distribution Overlay",
  parameter = "FSC-A",
  loadingBySampleId = {},
  errorsBySampleId = {},
  onRetrySample,
  replicateRenderMode = "standard",
  visibleSampleIds = [],
  primaryCompareSampleId: primaryCompareSampleIdProp = null,
  primarySampleId: primarySampleIdProp = null,
  compareScatterBySampleId = {},
  sampleLabelsById = {},
}: OverlayHistogramChartProps) {
  const {
    fcsAnalysis,
    secondaryFcsAnalysis,
    overlayConfig,
    fcsCompareSession,
    getFCSSeriesCacheEntry,
    setFCSSeriesCacheEntry,
  } = useAnalysisStore()
  const [showSeries, setShowSeries] = useState<Record<string, boolean>>({})
  const [histogramData, setHistogramData] = useState<{ data: HistogramSeriesPoint[]; isApproximate: boolean }>({
    data: [],
    isApproximate: true,
  })
  const [histogramLoading, setHistogramLoading] = useState(false)
  const [workerFallbackActive, setWorkerFallbackActive] = useState(false)
  const histogramRequestIdRef = useRef(0)

  // Fetch primary scatter data on-demand (not stored in global state)
  const [primaryScatter, setPrimaryScatter] = useState<Array<{ x: number; y: number; diameter?: number }>>([])
  const primarySampleIdFromAnalysis = fcsAnalysis.sampleId
  const effectivePrimaryBackendSampleId = primarySampleIdProp || primarySampleIdFromAnalysis
  const effectivePrimaryCompareSampleId = primaryCompareSampleIdProp || primarySampleIdProp || primarySampleIdFromAnalysis

  useEffect(() => {
    if (!effectivePrimaryBackendSampleId) return
    let cancelled = false
    const fetchPrimaryScatter = async () => {
      try {
        const result = await apiClient.getScatterData(effectivePrimaryBackendSampleId, 10000)
        if (!cancelled && result?.data) {
          setPrimaryScatter(result.data)
        }
      } catch {
        // Scatter data is optional — Gaussian fallback still works
      }
    }
    fetchPrimaryScatter()
    return () => { cancelled = true }
  }, [effectivePrimaryBackendSampleId])

  const primaryResults = fcsAnalysis.results
  const secondaryResults = secondaryFcsAnalysis.results
  const secondarySampleId = secondaryFcsAnalysis.sampleId
  const resolveScatterSeries = useMemo(() => {
    const compareMetaById = fcsCompareSession.compareItemMetaById ?? {}
    const ensureScatterArray = (value: unknown) => (Array.isArray(value) ? value : [])
    return (sampleId: string) => {
      const direct = compareScatterBySampleId[sampleId]
      if (Array.isArray(direct) && direct.length > 0) {
        return direct
      }

      const backendSampleId = compareMetaById[sampleId]?.backendSampleId
      if (!backendSampleId) {
        return ensureScatterArray(direct)
      }

      const directByBackend = compareScatterBySampleId[backendSampleId]
      if (Array.isArray(directByBackend) && directByBackend.length > 0) {
        return directByBackend
      }

      const siblingWithSameBackend = Object.entries(compareMetaById).find(([compareId, meta]) => {
        if (!meta || meta.backendSampleId !== backendSampleId || compareId === sampleId) {
          return false
        }
        const siblingScatter = compareScatterBySampleId[compareId]
        return Array.isArray(siblingScatter) && siblingScatter.length > 0
      })

      if (siblingWithSameBackend) {
        return ensureScatterArray(compareScatterBySampleId[siblingWithSameBackend[0]])
      }

      return ensureScatterArray(directByBackend) || ensureScatterArray(direct)
    }
  }, [compareScatterBySampleId, fcsCompareSession.compareItemMetaById])
  const comparisonSampleIds = useMemo(
    () => visibleSampleIds.filter((id) => id && id !== effectivePrimaryCompareSampleId),
    [visibleSampleIds, effectivePrimaryCompareSampleId]
  )
  const isMultiOverlay = overlayConfig.enabled && comparisonSampleIds.length > 1
  const sampleColorMap = useMemo(() => {
    const map: Record<string, string> = {}
    comparisonSampleIds.forEach((sampleId, index) => {
      map[sampleId] = resolvePeerColor(index, overlayConfig.secondaryColor)
    })
    return map
  }, [comparisonSampleIds, overlayConfig.secondaryColor])
  const seriesDescriptors = useMemo<HistogramSeriesDescriptor[]>(() => {
    const descriptors: HistogramSeriesDescriptor[] = []
    const resolvedPrimarySampleId = effectivePrimaryCompareSampleId || "primary"

    descriptors.push({
      key: "primary",
      sampleId: resolvedPrimarySampleId,
      label:
        sampleLabelsById[resolvedPrimarySampleId]
        || fcsAnalysis.file?.name
        || fcsAnalysis.sampleId
        || "Reference",
      color: overlayConfig.primaryColor,
      isPrimary: true,
    })

    if (isMultiOverlay) {
      comparisonSampleIds.forEach((sampleId) => {
        descriptors.push({
          key: sampleId,
          sampleId,
          label: sampleLabelsById[sampleId] || sampleId,
          color: sampleColorMap[sampleId] || overlayConfig.secondaryColor,
          isPrimary: false,
        })
      })
      return descriptors
    }

    if (comparisonSampleIds.length > 0 || secondarySampleId) {
      const resolvedSampleId = comparisonSampleIds[0] || secondarySampleId || "secondary"
      descriptors.push({
        key: "secondary",
        sampleId: resolvedSampleId,
        label:
          sampleLabelsById[resolvedSampleId]
          || secondaryFcsAnalysis.file?.name
          || secondaryFcsAnalysis.sampleId
          || "Session Peer",
        color: overlayConfig.secondaryColor,
        isPrimary: false,
      })
    }

    return descriptors
  }, [
    comparisonSampleIds,
    effectivePrimaryCompareSampleId,
    fcsAnalysis.file?.name,
    fcsAnalysis.sampleId,
    isMultiOverlay,
    overlayConfig.primaryColor,
    overlayConfig.secondaryColor,
    sampleColorMap,
    sampleLabelsById,
    secondaryFcsAnalysis.file?.name,
    secondaryFcsAnalysis.sampleId,
    secondarySampleId,
  ])
  const seriesDescriptorByKey = useMemo(
    () => Object.fromEntries(seriesDescriptors.map((descriptor) => [descriptor.key, descriptor])) as Record<string, HistogramSeriesDescriptor>,
    [seriesDescriptors]
  )
  useEffect(() => {
    setShowSeries((previous) => {
      const next: Record<string, boolean> = {}
      seriesDescriptors.forEach((descriptor) => {
        next[descriptor.key] = previous[descriptor.key] ?? true
      })
      return next
    })
  }, [seriesDescriptors])
  const primaryLoadingSampleId = effectivePrimaryCompareSampleId || effectivePrimaryBackendSampleId
  const secondaryLoadingSampleId = comparisonSampleIds[0] || secondarySampleId
  const primaryLoading = !!(primaryLoadingSampleId && loadingBySampleId[primaryLoadingSampleId])
  const secondaryLoading = !!(secondaryLoadingSampleId && loadingBySampleId[secondaryLoadingSampleId])
  const primaryError = primaryLoadingSampleId ? errorsBySampleId[primaryLoadingSampleId] : undefined
  const secondaryError = secondarySampleId ? errorsBySampleId[secondarySampleId] : undefined

  useEffect(() => {
    if (!primaryResults && !secondaryResults) {
      setHistogramData({ data: [], isApproximate: true })
      setHistogramLoading(false)
      setWorkerFallbackActive(false)
      return
    }

    const mergedComparisonScatter = comparisonSampleIds.flatMap((sampleId) => resolveScatterSeries(sampleId))
    const secondaryScatter = replicateRenderMode === "merged-points"
      ? mergedComparisonScatter
      : (secondaryFcsAnalysis.scatterData ?? [])
    const primaryValues = primaryScatter.length > 0
      ? primaryScatter
          .map((point) => extractHistogramValue(point, parameter))
          .filter((value): value is number => value !== null && Number.isFinite(value))
      : []
    const secondaryValues = secondaryScatter.length > 0
      ? secondaryScatter
          .map((point) => extractHistogramValue(point, parameter))
          .filter((value): value is number => value !== null && Number.isFinite(value))
      : []

    const primaryMean = parameter === "FSC-A"
      ? (primaryResults?.fsc_mean || primaryResults?.size_statistics?.mean || 100)
      : parameter === "SSC-A"
        ? (primaryResults?.ssc_mean || 50)
        : (primaryResults?.size_statistics?.mean || primaryResults?.particle_size_median_nm || 100)
    const primaryStd = primaryResults?.size_statistics?.std || primaryMean * 0.3

    const secondaryMean = parameter === "FSC-A"
      ? (secondaryResults?.fsc_mean || secondaryResults?.size_statistics?.mean || 100)
      : parameter === "SSC-A"
        ? (secondaryResults?.ssc_mean || 50)
        : (secondaryResults?.size_statistics?.mean || secondaryResults?.particle_size_median_nm || 100)
    const secondaryStd = secondaryResults?.size_statistics?.std || secondaryMean * 0.3

    if (isMultiOverlay) {
      const seriesValuesByKey: Record<string, number[]> = {
        primary: primaryValues,
      }

      comparisonSampleIds.forEach((sampleId) => {
        const sampleValues = resolveScatterSeries(sampleId)
          .map((point) => extractHistogramValue(point, parameter))
          .filter((value): value is number => value !== null && Number.isFinite(value))
        seriesValuesByKey[sampleId] = sampleValues
      })

      setHistogramData(buildHistogramDataForSeries({
        seriesValuesByKey,
        bins: FIXED_HISTOGRAM_BINS,
      }))
      setHistogramLoading(false)
      setWorkerFallbackActive(false)
      return
    }

    if (replicateRenderMode === "histogram-average" && comparisonSampleIds.length > 0) {
      const comparisonReplicateValues = comparisonSampleIds
        .map((sampleId) => resolveScatterSeries(sampleId)
          .map((point) => extractHistogramValue(point, parameter))
          .filter((value): value is number => value !== null && Number.isFinite(value)))
        .filter((values) => values.length > 0)

      if (comparisonReplicateValues.length > 0) {
        setHistogramData(buildHistogramDataWithAveragedReplicates({
          primaryValues,
          replicateValues: comparisonReplicateValues,
          bins: FIXED_HISTOGRAM_BINS,
        }))
        setHistogramLoading(false)
        setWorkerFallbackActive(false)
        return
      }
    }

    const workerPayload = {
      primaryValues,
      secondaryValues,
      primaryMean,
      primaryStd,
      secondaryMean,
      secondaryStd,
      bins: FIXED_HISTOGRAM_BINS,
    }

    const histogramCacheKey = buildOverlayHistogramCacheKey({
      primarySampleId: effectivePrimaryBackendSampleId,
      secondarySampleId,
      parameter,
      bins: workerPayload.bins,
      primaryCount: primaryValues.length,
      secondaryCount: secondaryValues.length,
      primaryMean,
      primaryStd,
      secondaryMean,
      secondaryStd,
    })

    const cachedEntry = getFCSSeriesCacheEntry(histogramCacheKey)
    if (cachedEntry && cachedEntry.task === "overlayHistogram") {
      const cachedPayload = cachedEntry.data as { data?: HistogramSeriesPoint[]; isApproximate?: boolean }
      if (Array.isArray(cachedPayload.data)) {
        setHistogramData({
          data: cachedPayload.data,
          isApproximate: Boolean(cachedPayload.isApproximate),
        })
        setHistogramLoading(false)
        setWorkerFallbackActive(false)
        return
      }
    }

    const requestId = histogramRequestIdRef.current + 1
    histogramRequestIdRef.current = requestId
    setHistogramLoading(true)
    setWorkerFallbackActive(false)

    runOverlayHistogramWorker(requestId, workerPayload)
      .then((result) => {
        if (histogramRequestIdRef.current !== requestId) {
          return
        }

        setFCSSeriesCacheEntry({
          key: histogramCacheKey,
          task: "overlayHistogram",
          data: result,
          approxBytes: estimateSeriesBytes(result),
        })
        setHistogramData(result)
      })
      .catch(() => {
        if (histogramRequestIdRef.current !== requestId) {
          return
        }

        // Worker failures should not block compare rendering.
        setWorkerFallbackActive(true)
        setHistogramData(buildHistogramDataLocal(workerPayload))
      })
      .finally(() => {
        if (histogramRequestIdRef.current !== requestId) {
          return
        }
        setHistogramLoading(false)
      })
  }, [
    primaryResults,
    secondaryResults,
    primaryScatter,
    secondaryFcsAnalysis.scatterData,
    parameter,
    effectivePrimaryBackendSampleId,
    secondarySampleId,
    isMultiOverlay,
    replicateRenderMode,
    comparisonSampleIds,
    compareScatterBySampleId,
    resolveScatterSeries,
    getFCSSeriesCacheEntry,
    setFCSSeriesCacheEntry,
  ])

  const hasOverlay = overlayConfig.enabled && comparisonSampleIds.length > 0
  const chartData = Array.isArray(histogramData.data) ? histogramData.data : []
  const isApproximate = Boolean(histogramData.isApproximate)
  const primaryTotalEvents = primaryResults?.total_events || 0
  const secondaryTotalEvents = secondaryResults?.total_events || 0
  const primaryRenderedEvents = primaryScatter.length
  const secondaryRenderedEvents = (replicateRenderMode === "merged-points"
    ? comparisonSampleIds.reduce((sum, sampleId) => sum + resolveScatterSeries(sampleId).length, 0)
    : (secondaryFcsAnalysis.scatterData?.length || 0))
  const downsampledPrimary = primaryTotalEvents > primaryRenderedEvents && primaryRenderedEvents > 0
  const downsampledSecondary = !isMultiOverlay && hasOverlay && secondaryTotalEvents > secondaryRenderedEvents && secondaryRenderedEvents > 0
  const comparisonErrorSampleIds = comparisonSampleIds.filter((sampleId) => !!errorsBySampleId[sampleId])
  const showAnySeries = seriesDescriptors.some((descriptor) => showSeries[descriptor.key])
  const renderState = deriveOverlayHistogramRenderState({
    primaryLoading: primaryLoading || histogramLoading,
    hasPrimaryResults: !!primaryResults,
    primaryError,
    chartDataLength: chartData.length,
  })

  if (renderState === "loading") {
    return (
      <Card className="card-3d">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Layers className="h-4 w-4" />
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-75 text-muted-foreground gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading reference chart data...
        </CardContent>
      </Card>
    )
  }

  if (renderState === "error") {
    return (
      <Card className="card-3d">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Layers className="h-4 w-4" />
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Failed to load reference sample</AlertTitle>
            <AlertDescription>{primaryError}</AlertDescription>
          </Alert>
          {onRetrySample && primaryLoadingSampleId && (
            <Button variant="outline" size="sm" onClick={() => onRetrySample(primaryLoadingSampleId)} className="gap-1">
              <RefreshCw className="h-3 w-3" />
              Retry Reference
            </Button>
          )}
        </CardContent>
      </Card>
    )
  }

  if (renderState === "empty") {
    return (
      <Card className="card-3d">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Layers className="h-4 w-4" />
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-75 text-muted-foreground">
          Upload a file to view histogram
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="card-3d">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Layers className="h-4 w-4" />
            {title}
          </CardTitle>
          <div className="flex items-center gap-2">
            {secondaryLoading && (
              <Badge variant="outline" className="gap-1">
                <Loader2 className="h-3 w-3 animate-spin" />
                Loading peer
              </Badge>
            )}
            {seriesDescriptors.map((descriptor) => (
              <Button
                key={descriptor.key}
                variant={showSeries[descriptor.key] ? (descriptor.isPrimary ? "default" : "secondary") : "outline"}
                size="sm"
                className="h-7 text-xs"
                onClick={() => {
                  setShowSeries((prev) => ({
                    ...prev,
                    [descriptor.key]: !prev[descriptor.key],
                  }))
                }}
              >
                {showSeries[descriptor.key] ? <Eye className="h-3 w-3 mr-1" /> : <EyeOff className="h-3 w-3 mr-1" />}
                {descriptor.isPrimary ? "Reference" : descriptor.label.slice(0, 24)}
              </Button>
            ))}
            {hasOverlay && (
              <Badge variant="secondary">
                <Layers className="h-3 w-3 mr-1" />
                Overlay {seriesDescriptors.length} series
              </Badge>
            )}
            {isApproximate && (
              <Badge variant="outline" className="text-xs text-amber-500 border-amber-500/50">
                Approximated
              </Badge>
            )}
            <Badge variant="outline" className="text-xs">
              {FIXED_HISTOGRAM_BINS} fixed bins
            </Badge>
            {(downsampledPrimary || downsampledSecondary) && (
              <Badge variant="secondary" className="text-xs">
                High density: downsampled
              </Badge>
            )}
            {workerFallbackActive && (
              <Badge variant="outline" className="text-xs">
                Worker Fallback
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-75">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis 
                dataKey="bin" 
                tick={{ fontSize: 10 }}
                label={{ value: parameter, position: 'bottom', fontSize: 12 }}
              />
              <YAxis 
                tick={{ fontSize: 10 }}
                label={{ value: 'Count', angle: -90, position: 'insideLeft', fontSize: 12 }}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(0,0,0,0.8)', 
                  border: 'none',
                  borderRadius: '8px',
                  color: 'white'
                }}
                formatter={(value: number, name: string) => [
                  value,
                  seriesDescriptorByKey[name]?.label || name
                ]}
              />
              <Legend 
                verticalAlign="top"
                height={36}
                formatter={(value) => (seriesDescriptorByKey[String(value)]?.label || String(value)).slice(0, 24)}
              />
              {seriesDescriptors.filter((descriptor) => showSeries[descriptor.key]).map((descriptor) => (
                <Area
                  key={descriptor.key}
                  type="monotone"
                  dataKey={descriptor.key}
                  fill={descriptor.color}
                  fillOpacity={descriptor.isPrimary && !hasOverlay ? 0.6 : 0.35}
                  stroke={descriptor.color}
                  strokeWidth={2}
                />
              ))}
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* Statistics comparison */}
        {comparisonErrorSampleIds.length > 0 && (
          <div className="mb-3">
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Overlay sample warnings</AlertTitle>
              <AlertDescription className="space-y-2">
                {comparisonErrorSampleIds.slice(0, 3).map((sampleId) => (
                  <div key={sampleId} className="flex items-center justify-between gap-2">
                    <span>{sampleLabelsById[sampleId] || sampleId}: {errorsBySampleId[sampleId]}</span>
                    {onRetrySample && (
                      <Button variant="outline" size="sm" className="h-7" onClick={() => onRetrySample(sampleId)}>
                        Retry
                      </Button>
                    )}
                  </div>
                ))}
                {comparisonErrorSampleIds.length > 3 && (
                  <div className="text-xs">+{comparisonErrorSampleIds.length - 3} more sample warnings</div>
                )}
              </AlertDescription>
            </Alert>
          </div>
        )}

        {!showAnySeries && (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>All overlay series hidden</AlertTitle>
            <AlertDescription>Enable at least one series toggle to render the histogram.</AlertDescription>
          </Alert>
        )}

        {chartData.length === 0 && !primaryLoading && (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>No chart data available</AlertTitle>
            <AlertDescription>
              No histogram points are currently available for this parameter.
            </AlertDescription>
          </Alert>
        )}

        {hasOverlay && !isMultiOverlay && (
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="p-3 rounded-lg" style={{ backgroundColor: `${overlayConfig.primaryColor}20` }}>
              <p className="text-xs font-medium mb-2 truncate" title={fcsAnalysis.file?.name}>
                {fcsAnalysis.file?.name?.slice(0, 25) || 'Reference'}
              </p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-muted-foreground">FSC Mean:</span>
                  <span className="ml-1 font-medium">{primaryResults.fsc_mean?.toFixed(2) || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">SSC Mean:</span>
                  <span className="ml-1 font-medium">{primaryResults.ssc_mean?.toFixed(2) || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Events:</span>
                  <span className="ml-1 font-medium">{primaryResults.total_events?.toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Size (D50):</span>
                  <span className="ml-1 font-medium">{primaryResults.size_statistics?.d50?.toFixed(1) || 'N/A'} nm</span>
                </div>
              </div>
            </div>
            <div className="p-3 rounded-lg" style={{ backgroundColor: `${overlayConfig.secondaryColor}20` }}>
              <p className="text-xs font-medium mb-2 truncate" title={secondaryFcsAnalysis.file?.name}>
                {secondaryFcsAnalysis.file?.name?.slice(0, 25) || 'Session Peer'}
              </p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-muted-foreground">FSC Mean:</span>
                  <span className="ml-1 font-medium">{secondaryResults?.fsc_mean?.toFixed(2) || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">SSC Mean:</span>
                  <span className="ml-1 font-medium">{secondaryResults?.ssc_mean?.toFixed(2) || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Events:</span>
                  <span className="ml-1 font-medium">{secondaryResults?.total_events?.toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Size (D50):</span>
                  <span className="ml-1 font-medium">{secondaryResults?.size_statistics?.d50?.toFixed(1) || 'N/A'} nm</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {hasOverlay && isMultiOverlay && (
          <div className="mt-4">
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Multi-overlay active</AlertTitle>
              <AlertDescription>
                Rendering {seriesDescriptors.length} visible series with shared bins. Reference and peer summary cards are suppressed in this mode to avoid two-series bias.
              </AlertDescription>
            </Alert>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
