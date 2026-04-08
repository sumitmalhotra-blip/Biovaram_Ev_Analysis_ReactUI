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
  primarySampleId?: string | null
  compareScatterBySampleId?: Record<string, Array<{ x: number; y: number; diameter?: number }>>
}

type HistogramSeriesPoint = { bin: string; binValue: number; primary: number; secondary: number }
const FIXED_HISTOGRAM_BINS = 50

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
  primarySampleId: primarySampleIdProp = null,
  compareScatterBySampleId = {},
}: OverlayHistogramChartProps) {
  const {
    fcsAnalysis,
    secondaryFcsAnalysis,
    overlayConfig,
    getFCSSeriesCacheEntry,
    setFCSSeriesCacheEntry,
  } = useAnalysisStore()
  const [showPrimary, setShowPrimary] = useState(true)
  const [showSecondary, setShowSecondary] = useState(true)
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
  const effectivePrimarySampleId = primarySampleIdProp || primarySampleIdFromAnalysis

  useEffect(() => {
    if (!effectivePrimarySampleId) return
    let cancelled = false
    const fetchPrimaryScatter = async () => {
      try {
        const result = await apiClient.getScatterData(effectivePrimarySampleId, 10000)
        if (!cancelled && result?.data) {
          setPrimaryScatter(result.data)
        }
      } catch {
        // Scatter data is optional — Gaussian fallback still works
      }
    }
    fetchPrimaryScatter()
    return () => { cancelled = true }
  }, [effectivePrimarySampleId])

  const primaryResults = fcsAnalysis.results
  const secondaryResults = secondaryFcsAnalysis.results
  const secondarySampleId = secondaryFcsAnalysis.sampleId
  const comparisonSampleIds = useMemo(
    () => visibleSampleIds.filter((id) => id && id !== effectivePrimarySampleId),
    [visibleSampleIds, effectivePrimarySampleId]
  )
  const primaryLoading = !!(effectivePrimarySampleId && loadingBySampleId[effectivePrimarySampleId])
  const secondaryLoading = !!(secondarySampleId && loadingBySampleId[secondarySampleId])
  const primaryError = effectivePrimarySampleId ? errorsBySampleId[effectivePrimarySampleId] : undefined
  const secondaryError = secondarySampleId ? errorsBySampleId[secondarySampleId] : undefined

  useEffect(() => {
    if (!primaryResults && !secondaryResults) {
      setHistogramData({ data: [], isApproximate: true })
      setHistogramLoading(false)
      setWorkerFallbackActive(false)
      return
    }

    const mergedComparisonScatter = comparisonSampleIds.flatMap((sampleId) => compareScatterBySampleId[sampleId] || [])
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

    if (replicateRenderMode === "histogram-average" && comparisonSampleIds.length > 0) {
      const comparisonReplicateValues = comparisonSampleIds
        .map((sampleId) => (compareScatterBySampleId[sampleId] || [])
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
      primarySampleId: effectivePrimarySampleId,
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
    effectivePrimarySampleId,
      secondarySampleId,
    replicateRenderMode,
    comparisonSampleIds,
    compareScatterBySampleId,
    getFCSSeriesCacheEntry,
    setFCSSeriesCacheEntry,
  ])

  const hasOverlay = overlayConfig.enabled && secondaryResults
  const { data: chartData, isApproximate } = histogramData
  const primaryTotalEvents = primaryResults?.total_events || 0
  const secondaryTotalEvents = secondaryResults?.total_events || 0
  const primaryRenderedEvents = primaryScatter.length
  const secondaryRenderedEvents = (replicateRenderMode === "merged-points"
    ? comparisonSampleIds.reduce((sum, sampleId) => sum + (compareScatterBySampleId[sampleId]?.length || 0), 0)
    : (secondaryFcsAnalysis.scatterData?.length || 0))
  const downsampledPrimary = primaryTotalEvents > primaryRenderedEvents && primaryRenderedEvents > 0
  const downsampledSecondary = hasOverlay && secondaryTotalEvents > secondaryRenderedEvents && secondaryRenderedEvents > 0
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
          {onRetrySample && effectivePrimarySampleId && (
            <Button variant="outline" size="sm" onClick={() => onRetrySample(effectivePrimarySampleId)} className="gap-1">
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
            {hasOverlay && (
              <>
                <Button
                  variant={showPrimary ? "default" : "outline"}
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => setShowPrimary(!showPrimary)}
                >
                  {showPrimary ? <Eye className="h-3 w-3 mr-1" /> : <EyeOff className="h-3 w-3 mr-1" />}
                  Reference
                </Button>
                <Button
                  variant={showSecondary ? "secondary" : "outline"}
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => setShowSecondary(!showSecondary)}
                >
                  {showSecondary ? <Eye className="h-3 w-3 mr-1" /> : <EyeOff className="h-3 w-3 mr-1" />}
                  Peer
                </Button>
              </>
            )}
            {hasOverlay && (
              <Badge variant="secondary">
                <Layers className="h-3 w-3 mr-1" />
                Overlay
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
                  name === 'primary' 
                    ? fcsAnalysis.file?.name || 'Reference' 
                    : secondaryFcsAnalysis.file?.name || 'Session Peer'
                ]}
              />
              <Legend 
                verticalAlign="top"
                height={36}
                formatter={(value) => value === 'primary' 
                  ? fcsAnalysis.file?.name?.slice(0, 20) || 'Reference' 
                  : secondaryFcsAnalysis.file?.name?.slice(0, 20) || 'Session Peer'
                }
              />
              {showPrimary && (
                <Area
                  type="monotone"
                  dataKey="primary"
                  fill={overlayConfig.primaryColor}
                  fillOpacity={hasOverlay ? 0.4 : 0.6}
                  stroke={overlayConfig.primaryColor}
                  strokeWidth={2}
                />
              )}
              {hasOverlay && showSecondary && (
                <Area
                  type="monotone"
                  dataKey="secondary"
                  fill={overlayConfig.secondaryColor}
                  fillOpacity={0.4}
                  stroke={overlayConfig.secondaryColor}
                  strokeWidth={2}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* Statistics comparison */}
        {hasOverlay && (
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="p-3 rounded-lg" style={{ backgroundColor: `${overlayConfig.primaryColor}20` }}>
              <p className="text-xs font-medium mb-2 truncate" title={fcsAnalysis.file?.name}>
                {fcsAnalysis.file?.name?.slice(0, 25) || 'Reference'}
              </p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>

                {hasOverlay && secondaryError && (
                  <div className="mb-3">
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertTitle>Peer sample load warning</AlertTitle>
                      <AlertDescription className="flex items-center justify-between gap-2">
                        <span>{secondaryError}</span>
                        {onRetrySample && secondarySampleId && (
                          <Button variant="outline" size="sm" className="h-7" onClick={() => onRetrySample(secondarySampleId)}>
                            Retry
                          </Button>
                        )}
                      </AlertDescription>
                    </Alert>
                  </div>
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
      </CardContent>
    </Card>
  )
}
