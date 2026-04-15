"use client"

import { useState, useCallback, useEffect, useMemo, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { 
  FileText, 
  Layers, 
  GitCompare, 
  RotateCcw, 
  X,
  Eye, 
  EyeOff,
  AlertCircle,
  Loader2,
  RefreshCw,
  Copy,
  Pin,
  Download,
  Maximize2,
  Minimize2,
  Plus,
  Trash2,
} from "lucide-react"
import { useAnalysisStore } from "@/lib/store"
import { useToast } from "@/hooks/use-toast"
import { useApi } from "@/hooks/use-api"
import { FullAnalysisDashboard } from "./full-analysis-dashboard"
import { StatisticsCards } from "./statistics-cards"
import { ScatterPlotChart } from "./charts/scatter-plot-chart"
import { ScatterAxisSelector } from "./charts/scatter-axis-selector"
import { OverlayHistogramChart } from "./overlay-histogram-chart"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { cn } from "@/lib/utils"
import { resolveFCSAxes } from "@/lib/fcs-axis-utils"
import { deriveCompareSampleStatus } from "@/lib/fcs-compare-acceptance-helpers"
import { apiClient } from "@/lib/api-client"
import {
  buildNormalizationSummary,
  buildReplicateGroups,
  formatChannelMappingLabel,
  getNormalizedChannelOptions,
  normalizeFCSChannels,
  resolveChannelForSample,
  type FCSNormalizationSchema,
} from "@/lib/flow-cytometry/compare-normalization-adapter"
import { runScatterDensitySeriesWorker } from "@/lib/fcs-series-worker-client"

const INTERACTIVE_SCATTER_CAP = 1200
const SETTLED_SCATTER_CAP = 3500
const PRIMARY_CHART_GATE_MS = 1500
const COMPARE_FIVE_FILE_GATE_MS = 3000
const EMPTY_SCATTER_POINTS: Array<{ x: number; y: number; index?: number; diameter?: number }> = []

type ReplicateGroupingMode = "none" | "prefix"
type ReplicateRenderMode = "standard" | "histogram-average" | "merged-points"
type ScatterDensityMode = "auto" | "raw" | "density"
type ScatterZoomPreset = "auto" | "center-60" | "core-30" | "high-signal"
type CompareMode = "pairwise" | "multi-overlay"

const DENSITY_TRIGGER_POINTS = 1400
const COMPARE_OVERLAY_PALETTE = ["#F97316", "#0EA5E9", "#22C55E", "#EAB308", "#EF4444", "#14B8A6", "#F43F5E"]

function getQuantile(sorted: number[], q: number): number {
  if (sorted.length === 0) return 0
  const index = Math.max(0, Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * q)))
  return sorted[index]
}

function buildZoomDomain(
  primary: Array<{ x: number; y: number }>,
  secondary: Array<{ x: number; y: number }>,
  preset: ScatterZoomPreset
): { xDomain?: [number, number]; yDomain?: [number, number] } {
  if (preset === "auto") {
    return {}
  }

  const all = [...primary, ...secondary]
  if (all.length === 0) {
    return {}
  }

  const xs = all.map((point) => point.x).filter((value) => Number.isFinite(value)).sort((a, b) => a - b)
  const ys = all.map((point) => point.y).filter((value) => Number.isFinite(value)).sort((a, b) => a - b)

  if (xs.length < 2 || ys.length < 2) {
    return {}
  }

  if (preset === "center-60") {
    return {
      xDomain: [getQuantile(xs, 0.2), getQuantile(xs, 0.8)],
      yDomain: [getQuantile(ys, 0.2), getQuantile(ys, 0.8)],
    }
  }

  if (preset === "core-30") {
    return {
      xDomain: [getQuantile(xs, 0.35), getQuantile(xs, 0.65)],
      yDomain: [getQuantile(ys, 0.35), getQuantile(ys, 0.65)],
    }
  }

  return {
    xDomain: [getQuantile(xs, 0.2), getQuantile(xs, 0.8)],
    yDomain: [getQuantile(ys, 0.6), getQuantile(ys, 0.98)],
  }
}

declare global {
  interface Window {
    __FCS_PERF_COMPARE_SAMPLE_IDS__?: string[]
  }
}

/**
 * ComparisonAnalysisView
 * 
 * Compare-session component for multi-file FCS analytics:
 * 1. Reference Tab - Reference sample analysis
 * 2. Peer Tab - Active peer sample analysis
 * 3. Overlay Tab - Session overlay analytics
 * 4. Sample Detail Tab - Full single-sample analysis for any compare-session file
 */
export function ComparisonAnalysisView() {
  const { 
    fcsAnalysis, 
    secondaryFcsAnalysis, 
    overlayConfig,
    fcsCompareSession,
    fcsCompareTelemetry,
    recordFCSCompareLoadMetrics,
    recordFCSCompareCacheStats,
    setFCSCompareSelectedSampleIds,
    setFCSCompareVisibleSampleIds,
    toggleFCSCompareSampleVisibility,
    setFCSComparePrimarySampleId,
    setFCSSampleId,
    setSecondaryFCSSampleId,
    setFCSResults,
    setSecondaryFCSResults,
    setSecondaryFCSScatterData,
    setOverlayConfig,
    resetFCSAnalysis,
    resetSecondaryFCSAnalysis,
    apiSamples,
    clearFCSCompareSession,
    fcsCompareGraphInstances,
    activeFCSCompareGraphInstanceId,
    setActiveFCSCompareGraphInstance,
    createFCSCompareGraphInstance,
    duplicateFCSCompareGraphInstance,
    removeFCSCompareGraphInstance,
    updateFCSCompareGraphInstance,
    pinChart,
  } = useAnalysisStore()
  const { toast } = useToast()
  const { loadFCSCompareSamples } = useApi()
  
  const [activeView, setActiveView] = useState<"primary" | "comparison" | "overlay" | "sample">("primary")
  const [compareLoadInFlight, setCompareLoadInFlight] = useState(false)
  const [compareLoadingBySampleId, setCompareLoadingBySampleId] = useState<Record<string, boolean>>({})
  const [compareErrorsBySampleId, setCompareErrorsBySampleId] = useState<Record<string, string>>({})
  const [lodMode, setLodMode] = useState<"interactive" | "settled">("settled")
  const [activeScatterPointCap, setActiveScatterPointCap] = useState(SETTLED_SCATTER_CAP)
  const [replicateGroupingMode, setReplicateGroupingMode] = useState<ReplicateGroupingMode>("none")
  const [replicateRenderMode, setReplicateRenderMode] = useState<ReplicateRenderMode>("merged-points")
  const [compareMode, setCompareMode] = useState<CompareMode>(() => (overlayConfig.enabled ? "multi-overlay" : "pairwise"))
  const [activePeerSampleId, setActivePeerSampleId] = useState<string | null>(null)
  const [inspectionSampleId, setInspectionSampleId] = useState<string | null>(null)
  const activeGraphInstance = useMemo(() => {
    return fcsCompareGraphInstances.find((instance) => instance.id === activeFCSCompareGraphInstanceId)
      || fcsCompareGraphInstances[0]
      || null
  }, [fcsCompareGraphInstances, activeFCSCompareGraphInstanceId])

  const axisMode = activeGraphInstance?.axisMode ?? "unified"
  const unifiedAxis = activeGraphInstance?.unifiedAxis ?? { x: "FSC-A", y: "SSC-A" }
  const primaryAxis = activeGraphInstance?.primaryAxis ?? { x: "FSC-A", y: "SSC-A" }
  const comparisonAxis = activeGraphInstance?.comparisonAxis ?? { x: "FSC-A", y: "SSC-A" }
  const [progressiveLoadMetrics, setProgressiveLoadMetrics] = useState<{
    primaryRenderMs: number | null
    settledRenderMs: number | null
    lastUpdatedAt: number | null
  }>({
    primaryRenderMs: null,
    settledRenderMs: null,
    lastUpdatedAt: null,
  })
  
  const hasPrimaryResults = fcsAnalysis.results !== null
  const hasComparisonResults = secondaryFcsAnalysis.results !== null || fcsCompareSession.selectedSampleIds.length > 1
  const benchmarkCompareSampleIds = useMemo(() => {
    if (typeof window === "undefined") return []
    const raw = window.__FCS_PERF_COMPARE_SAMPLE_IDS__
    if (!Array.isArray(raw)) return []

    return Array.from(new Set(raw.map((id) => String(id).trim()).filter(Boolean))).slice(0, 10)
  }, [])
  const compareSampleIds = useMemo(
    () => {
      if (benchmarkCompareSampleIds.length > 0) {
        return benchmarkCompareSampleIds
      }
      if (fcsCompareSession.selectedSampleIds.length > 0) {
        return fcsCompareSession.selectedSampleIds
      }
      return [fcsAnalysis.sampleId, secondaryFcsAnalysis.sampleId].filter(Boolean) as string[]
    },
    [benchmarkCompareSampleIds, fcsCompareSession.selectedSampleIds, fcsAnalysis.sampleId, secondaryFcsAnalysis.sampleId]
  )
  const visibleSampleIds = useMemo(() => {
    if (benchmarkCompareSampleIds.length > 0) {
      return compareSampleIds
    }
    if (fcsCompareSession.selectedSampleIds.length > 0) {
      return fcsCompareSession.visibleSampleIds
    }
    return compareSampleIds
  }, [benchmarkCompareSampleIds.length, compareSampleIds, fcsCompareSession.selectedSampleIds.length, fcsCompareSession.visibleSampleIds])
  const replicateGroups = useMemo(
    () => buildReplicateGroups(compareSampleIds, replicateGroupingMode),
    [compareSampleIds, replicateGroupingMode]
  )
  const primarySampleId = fcsAnalysis.sampleId
  const comparisonSampleId = secondaryFcsAnalysis.sampleId
  const canShowOverlay = compareSampleIds.length > 1
  const sessionCardSampleIds = useMemo(() => {
    if (compareSampleIds.length > 0) {
      return compareSampleIds
    }

    return Array.from(
      new Set([fcsAnalysis.sampleId, secondaryFcsAnalysis.sampleId].filter(Boolean) as string[])
    )
  }, [compareSampleIds, fcsAnalysis.sampleId, secondaryFcsAnalysis.sampleId])

  const peerOptions = useMemo(
    () => compareSampleIds.filter((id) => id !== primarySampleId),
    [compareSampleIds, primarySampleId]
  )

  const effectivePeerSampleId = useMemo(() => {
    if (activePeerSampleId && activePeerSampleId !== primarySampleId && compareSampleIds.includes(activePeerSampleId)) {
      return activePeerSampleId
    }
    if (secondaryFcsAnalysis.sampleId && secondaryFcsAnalysis.sampleId !== primarySampleId && compareSampleIds.includes(secondaryFcsAnalysis.sampleId)) {
      return secondaryFcsAnalysis.sampleId
    }
    return peerOptions[0] ?? null
  }, [activePeerSampleId, compareSampleIds, peerOptions, primarySampleId, secondaryFcsAnalysis.sampleId])

  const canUseMultiOverlay = canShowOverlay

  useEffect(() => {
    if (!canUseMultiOverlay && compareMode === "multi-overlay") {
      setCompareMode("pairwise")
      setOverlayConfig({ enabled: false })
    }
  }, [canUseMultiOverlay, compareMode, setOverlayConfig])

  const handleCompareModeChange = useCallback((nextMode: CompareMode) => {
    if (nextMode === "multi-overlay" && !canUseMultiOverlay) {
      toast({
        title: "Cannot Enable Multi-overlay",
        description: "Select at least two compare files and ensure results are loaded.",
        variant: "destructive",
      })
      return
    }

    setCompareMode(nextMode)
    const nextOverlayEnabled = nextMode === "multi-overlay"
    setOverlayConfig({ enabled: nextOverlayEnabled })

    if (nextOverlayEnabled) {
      setActiveView("overlay")
    } else if (activeView === "overlay") {
      setActiveView("comparison")
    }

    toast({
      title: nextMode === "pairwise" ? "Pairwise Mode" : "Multi-overlay Mode",
      description:
        nextMode === "pairwise"
          ? "Comparing reference vs one peer sample."
          : "Comparing reference vs visible compare set.",
    })
  }, [activeView, canUseMultiOverlay, setOverlayConfig, toast])

  useEffect(() => {
    if (effectivePeerSampleId !== activePeerSampleId) {
      setActivePeerSampleId(effectivePeerSampleId)
    }
  }, [activePeerSampleId, effectivePeerSampleId])

  useEffect(() => {
    if (inspectionSampleId && compareSampleIds.includes(inspectionSampleId)) {
      return
    }
    setInspectionSampleId(compareSampleIds[0] ?? null)
  }, [compareSampleIds, inspectionSampleId])

  useEffect(() => {
    if (compareSampleIds.length === 0) {
      return
    }

    const sessionPrimary = fcsCompareSession.primarySampleId && compareSampleIds.includes(fcsCompareSession.primarySampleId)
      ? fcsCompareSession.primarySampleId
      : (compareSampleIds[0] ?? null)

    if (!sessionPrimary) {
      return
    }

    const compareMetaById = fcsCompareSession.compareItemMetaById ?? {}
    const resolveBackendSampleId = (compareItemId: string) => compareMetaById[compareItemId]?.backendSampleId || compareItemId
    const sessionPrimaryBackendId = resolveBackendSampleId(sessionPrimary)

    if (fcsAnalysis.sampleId !== sessionPrimaryBackendId) {
      setFCSSampleId(sessionPrimaryBackendId)
    }

    const primaryResult = fcsCompareSession.resultsBySampleId[sessionPrimary] ?? null
    if (fcsAnalysis.results !== primaryResult) {
      setFCSResults(primaryResult)
    }

    const secondaryCandidate = compareMode === "pairwise"
      ? (
        (effectivePeerSampleId && effectivePeerSampleId !== sessionPrimary && compareSampleIds.includes(effectivePeerSampleId))
          ? effectivePeerSampleId
          : (compareSampleIds.find((id) => id !== sessionPrimary) ?? null)
      )
      : (
        visibleSampleIds.find((id) => id !== sessionPrimary)
          ?? compareSampleIds.find((id) => id !== sessionPrimary)
          ?? null
      )

    if (secondaryCandidate) {
      const secondaryBackendId = resolveBackendSampleId(secondaryCandidate)

      if (secondaryFcsAnalysis.sampleId !== secondaryBackendId) {
        setSecondaryFCSSampleId(secondaryBackendId)
      }

      const secondaryResult = fcsCompareSession.resultsBySampleId[secondaryCandidate] ?? null
      if (secondaryFcsAnalysis.results !== secondaryResult) {
        setSecondaryFCSResults(secondaryResult)
      }

      const secondaryScatter = fcsCompareSession.scatterBySampleId[secondaryCandidate] ?? EMPTY_SCATTER_POINTS
      if (secondaryFcsAnalysis.scatterData !== secondaryScatter) {
        setSecondaryFCSScatterData(secondaryScatter)
      }
      return
    }

    if (secondaryFcsAnalysis.sampleId !== null) {
      setSecondaryFCSSampleId(null)
    }
    if (secondaryFcsAnalysis.results !== null) {
      setSecondaryFCSResults(null)
    }
    if ((secondaryFcsAnalysis.scatterData?.length ?? 0) > 0) {
      setSecondaryFCSScatterData(EMPTY_SCATTER_POINTS)
    }
  }, [
    compareSampleIds,
    visibleSampleIds,
    effectivePeerSampleId,
    compareMode,
    fcsCompareSession.primarySampleId,
    fcsCompareSession.compareItemMetaById,
    fcsCompareSession.resultsBySampleId,
    fcsCompareSession.scatterBySampleId,
    fcsAnalysis.sampleId,
    fcsAnalysis.results,
    secondaryFcsAnalysis.sampleId,
    secondaryFcsAnalysis.results,
    secondaryFcsAnalysis.scatterData,
    setFCSSampleId,
    setSecondaryFCSSampleId,
    setFCSResults,
    setSecondaryFCSResults,
    setSecondaryFCSScatterData,
  ])

  useEffect(() => {
    if (activeView === "overlay" && !canShowOverlay) {
      setActiveView(hasPrimaryResults ? "primary" : "comparison")
      return
    }

    if (activeView === "comparison" && !hasComparisonResults && hasPrimaryResults) {
      setActiveView("primary")
    }
  }, [activeView, canShowOverlay, hasComparisonResults, hasPrimaryResults])

  const sampleMetadataById = useMemo(() => {
    const map = new Map<string, { treatment?: string; dye?: string }>()
    apiSamples.forEach((sample) => {
      map.set(sample.sample_id, {
        treatment: sample.treatment,
        dye: sample.dye,
      })
    })
    return map
  }, [apiSamples])

  const getCompareDisplayLabel = useCallback((compareItemId: string) => {
    const compareMetaById = fcsCompareSession.compareItemMetaById ?? {}
    return compareMetaById[compareItemId]?.sampleLabel || compareItemId
  }, [fcsCompareSession.compareItemMetaById])

  const normalizationSummary = useMemo(() => {
    const schemas: FCSNormalizationSchema[] = []
    const seen = new Set<string>()

    const addSchema = (sampleId: string | null | undefined, channels: string[] | null | undefined) => {
      if (!sampleId || !channels || channels.length === 0 || seen.has(sampleId)) {
        return
      }
      seen.add(sampleId)
      schemas.push(normalizeFCSChannels(sampleId, channels))
    }

    addSchema(primarySampleId, fcsAnalysis.results?.channels)
    addSchema(comparisonSampleId, secondaryFcsAnalysis.results?.channels)

    Object.entries(fcsCompareSession.resultsBySampleId).forEach(([sampleId, result]) => {
      addSchema(sampleId, result?.channels)
    })

    return buildNormalizationSummary(schemas)
  }, [
    primarySampleId,
    fcsAnalysis.results?.channels,
    comparisonSampleId,
    secondaryFcsAnalysis.results?.channels,
    fcsCompareSession.resultsBySampleId,
  ])

  const primarySchema = primarySampleId ? normalizationSummary.schemasBySampleId[primarySampleId] ?? null : null
  const comparisonSchema = comparisonSampleId ? normalizationSummary.schemasBySampleId[comparisonSampleId] ?? null : null
  const normalizationWarningGroups = useMemo(() => {
    const grouped = new Map<string, Set<string>>()

    normalizationSummary.warnings.forEach((warning) => {
      const separatorIdx = warning.indexOf(": ")
      if (separatorIdx <= 0) {
        if (!grouped.has(warning)) {
          grouped.set(warning, new Set())
        }
        return
      }

      const sampleId = warning.slice(0, separatorIdx)
      const message = warning.slice(separatorIdx + 2)
      if (!grouped.has(message)) {
        grouped.set(message, new Set())
      }
      grouped.get(message)?.add(sampleId)
    })

    return Array.from(grouped.entries())
      .map(([message, samples]) => ({
        message,
        sampleCount: samples.size,
      }))
      .sort((a, b) => b.sampleCount - a.sampleCount || a.message.localeCompare(b.message))
  }, [normalizationSummary.warnings])

  const normalizedPrimaryOptions = useMemo(
    () => getNormalizedChannelOptions(primarySchema, fcsAnalysis.results?.channels || []),
    [primarySchema, fcsAnalysis.results?.channels]
  )
  const normalizedComparisonOptions = useMemo(
    () => getNormalizedChannelOptions(comparisonSchema, secondaryFcsAnalysis.results?.channels || []),
    [comparisonSchema, secondaryFcsAnalysis.results?.channels]
  )
  const normalizedUnifiedOptions = useMemo(
    () => Array.from(new Set([...normalizedPrimaryOptions, ...normalizedComparisonOptions])),
    [normalizedPrimaryOptions, normalizedComparisonOptions]
  )

  const requestedPrimaryX = axisMode === "unified" ? unifiedAxis.x : primaryAxis.x
  const requestedPrimaryY = axisMode === "unified" ? unifiedAxis.y : primaryAxis.y
  const requestedComparisonX = axisMode === "unified" ? unifiedAxis.x : comparisonAxis.x
  const requestedComparisonY = axisMode === "unified" ? unifiedAxis.y : comparisonAxis.y
  const requestedPrimaryXNative = resolveChannelForSample(requestedPrimaryX, primarySchema)
  const requestedPrimaryYNative = resolveChannelForSample(requestedPrimaryY, primarySchema)
  const requestedComparisonXNative = resolveChannelForSample(requestedComparisonX, comparisonSchema)
  const requestedComparisonYNative = resolveChannelForSample(requestedComparisonY, comparisonSchema)
  const primaryAxisResolution = useMemo(
    () => resolveFCSAxes({
      availableChannels: fcsAnalysis.results?.channels || [],
      requestedX: requestedPrimaryXNative,
      requestedY: requestedPrimaryYNative,
    }),
    [fcsAnalysis.results?.channels, requestedPrimaryXNative, requestedPrimaryYNative]
  )
  const comparisonAxisResolution = useMemo(
    () => resolveFCSAxes({
      availableChannels: secondaryFcsAnalysis.results?.channels || [],
      requestedX: requestedComparisonXNative,
      requestedY: requestedComparisonYNative,
    }),
    [
      secondaryFcsAnalysis.results?.channels,
      requestedComparisonXNative,
      requestedComparisonYNative,
    ]
  )

  const handleUnifiedAxisChange = useCallback((xChannel: string, yChannel: string) => {
    if (!activeGraphInstance) return
    updateFCSCompareGraphInstance(activeGraphInstance.id, {
      unifiedAxis: { x: xChannel, y: yChannel },
    })
  }, [activeGraphInstance, updateFCSCompareGraphInstance])

  const handlePrimaryAxisChange = useCallback((xChannel: string, yChannel: string) => {
    if (!activeGraphInstance) return
    updateFCSCompareGraphInstance(activeGraphInstance.id, {
      primaryAxis: { x: xChannel, y: yChannel },
    })
  }, [activeGraphInstance, updateFCSCompareGraphInstance])

  const handleComparisonAxisChange = useCallback((xChannel: string, yChannel: string) => {
    if (!activeGraphInstance) return
    updateFCSCompareGraphInstance(activeGraphInstance.id, {
      comparisonAxis: { x: xChannel, y: yChannel },
    })
  }, [activeGraphInstance, updateFCSCompareGraphInstance])

  const handleAxisModeChange = useCallback((mode: "unified" | "per-file") => {
    if (!activeGraphInstance) return
    updateFCSCompareGraphInstance(activeGraphInstance.id, { axisMode: mode })
  }, [activeGraphInstance, updateFCSCompareGraphInstance])

  const handleCreateGraphInstance = useCallback(() => {
    const nextIndex = fcsCompareGraphInstances.length + 1
    const nextId = createFCSCompareGraphInstance(`Overlay Graph ${nextIndex}`)
    setActiveFCSCompareGraphInstance(nextId)
    toast({
      title: "Graph Instance Added",
      description: `Overlay Graph ${nextIndex} created.`,
    })
  }, [fcsCompareGraphInstances.length, createFCSCompareGraphInstance, setActiveFCSCompareGraphInstance, toast])

  const handleDuplicateGraphInstance = useCallback(() => {
    if (!activeGraphInstance) return
    const duplicatedId = duplicateFCSCompareGraphInstance(activeGraphInstance.id)
    if (!duplicatedId) return
    setActiveFCSCompareGraphInstance(duplicatedId)
    toast({
      title: "Graph Duplicated",
      description: `${activeGraphInstance.title} copied with isolated axis config.`,
    })
  }, [activeGraphInstance, duplicateFCSCompareGraphInstance, setActiveFCSCompareGraphInstance, toast])

  const handleRemoveGraphInstance = useCallback(() => {
    if (!activeGraphInstance) return
    if (fcsCompareGraphInstances.length <= 1) {
      toast({
        title: "Cannot Remove",
        description: "At least one graph instance is required.",
        variant: "destructive",
      })
      return
    }
    removeFCSCompareGraphInstance(activeGraphInstance.id)
    toast({
      title: "Graph Removed",
      description: `${activeGraphInstance.title} removed.`,
    })
  }, [activeGraphInstance, fcsCompareGraphInstances.length, removeFCSCompareGraphInstance, toast])

  const runCompareLoad = useCallback(
    async (
      sampleIds: string[],
      visibleSampleIds: string[],
      options?: {
        silent?: boolean
        scatterPointLimit?: number
        resultConcurrency?: number
        scatterConcurrency?: number
        preserveSessionSelection?: boolean
      }
    ) => {
      if (sampleIds.length === 0) return

      const startedAt = Date.now()
      const queueDepth = sampleIds.length
      const scatterPointLimit = options?.scatterPointLimit ?? SETTLED_SCATTER_CAP
      const resultConcurrency = options?.resultConcurrency ?? 2
      const scatterConcurrency = options?.scatterConcurrency ?? 2
      const preserveSessionSelection = options?.preserveSessionSelection ?? false

      setCompareLoadInFlight(true)
      setCompareLoadingBySampleId((prev) => {
        const next = { ...prev }
        sampleIds.forEach((id) => { next[id] = true })
        return next
      })

      try {
        const summary = await loadFCSCompareSamples(sampleIds, {
          visibleSampleIds,
          resultConcurrency,
          scatterConcurrency,
          scatterPointLimit,
          preserveSessionSelection,
        })

        if (summary.cancelled) {
          return
        }

        recordFCSCompareCacheStats(summary.cacheStats)

        setCompareErrorsBySampleId((prev) => {
          const next = { ...prev }
          sampleIds.forEach((id) => {
            if (summary.errorsBySampleId[id]) {
              next[id] = summary.errorsBySampleId[id]
            } else {
              delete next[id]
            }
          })
          return next
        })

        if (!options?.silent && summary.failed > 0) {
          toast({
            variant: "destructive",
            title: "Compare load issues",
            description: `${summary.failed} sample(s) could not be fully loaded.`,
          })
        }
      } finally {
        setCompareLoadingBySampleId((prev) => {
          const next = { ...prev }
          sampleIds.forEach((id) => { next[id] = false })
          return next
        })
        setCompareLoadInFlight(false)
        recordFCSCompareLoadMetrics({
          durationMs: Date.now() - startedAt,
          queueDepth,
        })
      }
    },
    [
      loadFCSCompareSamples,
      recordFCSCompareCacheStats,
      recordFCSCompareLoadMetrics,
      toast,
    ]
  )

  const runProgressiveCompareLoad = useCallback(
    async (sampleIds: string[], visibleSampleIds: string[], options?: { silent?: boolean }) => {
      if (sampleIds.length === 0) return

      const currentPrimary = useAnalysisStore.getState().fcsCompareSession.primarySampleId
      const primaryOnlySample = currentPrimary && sampleIds.includes(currentPrimary)
        ? currentPrimary
        : sampleIds[0]

      setCompareLoadInFlight(true)
      setLodMode("interactive")
      setActiveScatterPointCap(INTERACTIVE_SCATTER_CAP)

      const primaryStartedAt = Date.now()
      await runCompareLoad([primaryOnlySample], [primaryOnlySample], {
        silent: true,
        scatterPointLimit: INTERACTIVE_SCATTER_CAP,
        resultConcurrency: 1,
        scatterConcurrency: 1,
        preserveSessionSelection: true,
      })

      const primaryRenderMs = Date.now() - primaryStartedAt
      setProgressiveLoadMetrics((prev) => ({
        ...prev,
        primaryRenderMs,
        lastUpdatedAt: Date.now(),
      }))

      // Yield to the browser so controls remain responsive before settled pass starts.
      await new Promise((resolve) => setTimeout(resolve, 0))

      setLodMode("settled")
      setActiveScatterPointCap(SETTLED_SCATTER_CAP)

      const settledStartedAt = Date.now()
      await runCompareLoad(sampleIds, visibleSampleIds, {
        silent: options?.silent,
        scatterPointLimit: SETTLED_SCATTER_CAP,
        resultConcurrency: 2,
        scatterConcurrency: 2,
      })

      const settledRenderMs = Date.now() - settledStartedAt
      setProgressiveLoadMetrics((prev) => ({
        ...prev,
        settledRenderMs,
        lastUpdatedAt: Date.now(),
      }))
      setCompareLoadInFlight(false)
    },
    [runCompareLoad]
  )

  useEffect(() => {
    if (compareSampleIds.length === 0) {
      setCompareErrorsBySampleId({})
      return
    }

    // Avoid reloading large compare payloads on pure visibility/UI toggles when data is already hydrated.
    const allResultsReady = compareSampleIds.every((sampleId) => Boolean(fcsCompareSession.resultsBySampleId[sampleId]))
    const allScatterReady = compareSampleIds.every((sampleId) => {
      const points = fcsCompareSession.scatterBySampleId[sampleId]
      return Array.isArray(points) && points.length > 0
    })
    if (allResultsReady && allScatterReady) {
      return
    }

    let cancelled = false

    const preloadCompare = async () => {
      try {
        await runProgressiveCompareLoad(compareSampleIds, visibleSampleIds, { silent: true })

        if (cancelled) {
          return
        }
      } finally {
        if (!cancelled) {
          // no-op: state managed by runCompareLoad
        }
      }
    }

    preloadCompare()

    return () => {
      cancelled = true
    }
  }, [compareSampleIds, runProgressiveCompareLoad])

  const retrySample = useCallback(async (sampleId: string) => {
    await runProgressiveCompareLoad([sampleId], [sampleId])
  }, [runProgressiveCompareLoad])

  const retryAllCompareSamples = useCallback(async () => {
    await runProgressiveCompareLoad(compareSampleIds, visibleSampleIds)
  }, [compareSampleIds, visibleSampleIds, runProgressiveCompareLoad])

  const compareStatusBySampleId = useMemo(() => {
    const status: Record<string, "loading" | "error" | "ready" | "idle"> = {}

    compareSampleIds.forEach((sampleId) => {
      const isLoading = Boolean(compareLoadingBySampleId[sampleId] || fcsCompareSession.loadingBySampleId[sampleId])
      const error = compareErrorsBySampleId[sampleId] || fcsCompareSession.errorBySampleId[sampleId]
      const hasResult = Boolean(
        fcsCompareSession.resultsBySampleId[sampleId] ||
        (sampleId === primarySampleId && hasPrimaryResults) ||
        (sampleId === comparisonSampleId && hasComparisonResults)
      )

      if (isLoading) {
        status[sampleId] = "loading"
      } else if (error) {
        status[sampleId] = "error"
      } else if (hasResult) {
        status[sampleId] = "ready"
      } else {
        status[sampleId] = "idle"
      }
    })

    return status
  }, [
    compareSampleIds,
    compareLoadingBySampleId,
    compareErrorsBySampleId,
    fcsCompareSession.loadingBySampleId,
    fcsCompareSession.errorBySampleId,
    fcsCompareSession.resultsBySampleId,
    primarySampleId,
    comparisonSampleId,
    hasPrimaryResults,
    hasComparisonResults,
  ])

  const showAllVisible = useCallback(() => {
    setFCSCompareVisibleSampleIds(compareSampleIds)
  }, [compareSampleIds, setFCSCompareVisibleSampleIds])

  const showPrimaryOnly = useCallback(() => {
    const primary = fcsCompareSession.primarySampleId || compareSampleIds[0] || null
    setFCSCompareVisibleSampleIds(primary ? [primary] : [])
  }, [fcsCompareSession.primarySampleId, compareSampleIds, setFCSCompareVisibleSampleIds])

  const clearVisible = useCallback(() => {
    setFCSCompareVisibleSampleIds([])
  }, [setFCSCompareVisibleSampleIds])

  const removeFromSession = useCallback((sampleId: string) => {
    setFCSCompareSelectedSampleIds(compareSampleIds.filter((id) => id !== sampleId))
  }, [compareSampleIds, setFCSCompareSelectedSampleIds])

  const clearCompareSessionState = useCallback(() => {
    clearFCSCompareSession()
    setCompareLoadingBySampleId({})
    setCompareErrorsBySampleId({})
    setActivePeerSampleId(null)
    setInspectionSampleId(null)
    resetFCSAnalysis()
    resetSecondaryFCSAnalysis()
    setOverlayConfig({ enabled: false })
    toast({
      title: "Compare Session Cleared",
      description: "Selected and visible compare samples were reset.",
    })
  }, [clearFCSCompareSession, resetFCSAnalysis, resetSecondaryFCSAnalysis, setOverlayConfig, toast])

  const handleResetAll = useCallback(() => {
    resetFCSAnalysis()
    resetSecondaryFCSAnalysis()
    clearFCSCompareSession()
    setOverlayConfig({ enabled: false })
    toast({
      title: "Analysis Reset",
      description: "Reference and peer analyses cleared. Upload compare files to start fresh.",
    })
  }, [resetFCSAnalysis, resetSecondaryFCSAnalysis, clearFCSCompareSession, setOverlayConfig, toast])

  const handleResetPrimary = useCallback(() => {
    resetFCSAnalysis()
    setOverlayConfig({ enabled: false })
    toast({
      title: "Reference Sample Reset",
      description: "Reference sample analysis cleared.",
    })
  }, [resetFCSAnalysis, setOverlayConfig, toast])

  const handleResetComparison = useCallback(() => {
    resetSecondaryFCSAnalysis()
    setOverlayConfig({ enabled: false })
    toast({
      title: "Session Peer Reset",
      description: "Peer sample analysis cleared.",
    })
  }, [resetSecondaryFCSAnalysis, setOverlayConfig, toast])

  const primaryStatus = deriveCompareSampleStatus({
    sampleId: primarySampleId,
    loadingBySampleId: compareLoadingBySampleId,
    errorsBySampleId: compareErrorsBySampleId,
    hasResults: hasPrimaryResults,
  })

  const comparisonStatus = deriveCompareSampleStatus({
    sampleId: comparisonSampleId,
    loadingBySampleId: compareLoadingBySampleId,
    errorsBySampleId: compareErrorsBySampleId,
    hasResults: hasComparisonResults,
  })

  return (
    <div className="space-y-4">
      {/* View Tabs and Controls */}
      <Card className="card-3d">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <CardTitle className="text-base">Analysis View</CardTitle>
              {canShowOverlay && (
                <Badge variant={compareMode === "multi-overlay" ? "default" : "outline"} className="gap-1">
                  <GitCompare className="h-3 w-3" />
                  {compareMode === "multi-overlay" ? "Multi-overlay Active" : "Pairwise Active"}
                </Badge>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              {(primaryStatus === "loading" || comparisonStatus === "loading") && (
                <Badge variant="outline" className="gap-1">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Loading
                </Badge>
              )}

              {(primaryStatus === "error" || comparisonStatus === "error") && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={retryAllCompareSamples}
                  className="gap-1"
                >
                  <RefreshCw className="h-3 w-3" />
                  Retry Failed
                </Button>
              )}

              <div className="flex items-center gap-1">
                <Button
                  variant={compareMode === "pairwise" ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleCompareModeChange("pairwise")}
                  className="gap-1"
                >
                  <GitCompare className="h-3 w-3" />
                  Pairwise
                </Button>
                <Button
                  variant={compareMode === "multi-overlay" ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleCompareModeChange("multi-overlay")}
                  className="gap-1"
                  disabled={!canUseMultiOverlay}
                >
                  <Layers className="h-3 w-3" />
                  Multi-overlay
                </Button>
              </div>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handleResetAll}
                className="gap-1 text-destructive hover:text-destructive"
              >
                <RotateCcw className="h-3 w-3" />
                Reset All
              </Button>
            </div>
          </div>
        </CardHeader>
        
        <CardContent className="pt-0">
          {fcsCompareTelemetry.totalLoads > 0 && (
            <div className="mb-3 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
              <Badge variant="outline" className="justify-center">
                Last Load: {fcsCompareTelemetry.lastLoadMs}ms
              </Badge>
              <Badge variant="outline" className="justify-center">
                Avg Load: {fcsCompareTelemetry.averageLoadMs}ms
              </Badge>
              <Badge variant="outline" className="justify-center">
                Queue: {fcsCompareTelemetry.lastQueueDepth} (max {fcsCompareTelemetry.maxQueueDepth})
              </Badge>
              <Badge variant="outline" className="justify-center">
                Cache H/M/E: {fcsCompareTelemetry.cacheHits}/{fcsCompareTelemetry.cacheMisses}/{fcsCompareTelemetry.cacheEvictions}
              </Badge>
              <Badge variant={lodMode === "interactive" ? "secondary" : "outline"} className="justify-center">
                LOD: {lodMode === "interactive" ? `Interactive (${INTERACTIVE_SCATTER_CAP})` : `Settled (${SETTLED_SCATTER_CAP})`}
              </Badge>
              <Badge
                variant={progressiveLoadMetrics.primaryRenderMs !== null && progressiveLoadMetrics.primaryRenderMs <= PRIMARY_CHART_GATE_MS ? "default" : "destructive"}
                className="justify-center"
              >
                Reference Gate: {progressiveLoadMetrics.primaryRenderMs ?? "--"}ms / {PRIMARY_CHART_GATE_MS}ms
              </Badge>
              <Badge
                variant={progressiveLoadMetrics.settledRenderMs !== null && progressiveLoadMetrics.settledRenderMs <= COMPARE_FIVE_FILE_GATE_MS ? "default" : "destructive"}
                className="justify-center"
              >
                Compare Gate: {progressiveLoadMetrics.settledRenderMs ?? "--"}ms / {COMPARE_FIVE_FILE_GATE_MS}ms
              </Badge>
            </div>
          )}

          {compareLoadInFlight && (
            <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <Badge variant="outline">Loading compare samples...</Badge>
              {compareSampleIds.map((id) => (
                <Badge key={id} variant="outline" className="font-mono">
                  {getCompareDisplayLabel(id)}
                </Badge>
              ))}
            </div>
          )}

          {!compareLoadInFlight && Object.keys(compareErrorsBySampleId).length > 0 && (
            <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
              {Object.entries(compareErrorsBySampleId).map(([id, message]) => (
                <div key={id} className="flex items-center gap-1">
                  <Badge variant="destructive" className="font-mono" title={message}>
                    {getCompareDisplayLabel(id)}: load warning
                  </Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2 text-[10px]"
                    onClick={() => retrySample(id)}
                  >
                    Retry
                  </Button>
                </div>
              ))}
            </div>
          )}

          {normalizationWarningGroups.length > 0 && (
            <Alert className="mb-3 border-amber-300 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800">
              <AlertCircle className="h-4 w-4 text-amber-500" />
              <AlertTitle className="text-sm font-semibold text-amber-700 dark:text-amber-400">
                Cross-instrument normalization warnings
              </AlertTitle>
              <AlertDescription className="text-xs text-amber-700 dark:text-amber-300 space-y-1">
                {normalizationWarningGroups.slice(0, 4).map((warning) => (
                  <div key={warning.message}>
                    {warning.message}
                    {warning.sampleCount > 1 ? ` (${warning.sampleCount} samples)` : ""}
                  </div>
                ))}
                {normalizationWarningGroups.length > 4 && (
                  <div>+{normalizationWarningGroups.length - 4} more warning type(s)</div>
                )}
              </AlertDescription>
            </Alert>
          )}

          <Tabs value={activeView} onValueChange={(v) => setActiveView(v as "primary" | "comparison" | "overlay" | "sample")}>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="primary" disabled={!hasPrimaryResults} className="gap-2">
                <FileText className="h-4 w-4" />
                Reference
                {hasPrimaryResults && (
                  <Badge variant="outline" className="ml-1 h-5 px-1.5 text-[10px]">
                    {(fcsAnalysis.results?.total_events || 0).toLocaleString()}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="comparison" disabled={!hasComparisonResults} className="gap-2">
                <Layers className="h-4 w-4" />
                Session Peer
                {hasComparisonResults && (
                  <Badge variant="outline" className="ml-1 h-5 px-1.5 text-[10px]">
                    {(secondaryFcsAnalysis.results?.total_events || 0).toLocaleString()}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="overlay" className="gap-2" disabled={!canShowOverlay}>
                <GitCompare className="h-4 w-4" />
                Overlay
                {canShowOverlay && compareMode === "multi-overlay" && (
                  <Badge className="ml-1 h-5 px-1.5 text-[10px]">Active</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="sample" disabled={compareSampleIds.length === 0} className="gap-2">
                <Layers className="h-4 w-4" />
                Sample Detail
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </CardContent>
      </Card>

      {compareSampleIds.length > 0 && (
        <Card className="card-3d">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <CardTitle className="text-sm">Compare Session</CardTitle>
              <div className="flex items-center gap-2 flex-wrap">
                <div className="flex items-center gap-1">
                  <Badge variant="outline" className="h-7">Replicates: {replicateGroups.length}</Badge>
                  {compareMode === "pairwise" ? (
                    <Select
                      value={effectivePeerSampleId ?? "none"}
                      onValueChange={(value) => setActivePeerSampleId(value === "none" ? null : value)}
                    >
                      <SelectTrigger className="h-7 w-[180px] text-xs">
                        <SelectValue placeholder="Peer sample" />
                      </SelectTrigger>
                      <SelectContent>
                        {peerOptions.length === 0 ? (
                          <SelectItem value="none">Peer: none</SelectItem>
                        ) : (
                          peerOptions.map((id) => (
                            <SelectItem key={id} value={id}>Peer: {getCompareDisplayLabel(id)}</SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Badge variant="secondary" className="h-7">Visible set drives overlay membership</Badge>
                  )}
                  <Select value={replicateGroupingMode} onValueChange={(value) => setReplicateGroupingMode(value as ReplicateGroupingMode)}>
                    <SelectTrigger className="h-7 w-[170px] text-xs">
                      <SelectValue placeholder="Group mode" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Group: none</SelectItem>
                      <SelectItem value="prefix">Group: sample prefix</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select value={replicateRenderMode} onValueChange={(value) => setReplicateRenderMode(value as ReplicateRenderMode)}>
                    <SelectTrigger className="h-7 w-[205px] text-xs">
                      <SelectValue placeholder="Render mode" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="standard">Render: standard</SelectItem>
                      <SelectItem value="histogram-average">Render: histogram average</SelectItem>
                      <SelectItem value="merged-points">Render: merged points</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center gap-1">
                <Button variant="outline" size="sm" className="h-7 text-xs" onClick={showAllVisible}>Show All</Button>
                <Button variant="outline" size="sm" className="h-7 text-xs" onClick={showPrimaryOnly}>Reference Only</Button>
                <Button
                  variant={axisMode === "unified" ? "default" : "outline"}
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => handleAxisModeChange("unified")}
                >
                  Unified Axis
                </Button>
                <Button
                  variant={axisMode === "per-file" ? "default" : "outline"}
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => handleAxisModeChange("per-file")}
                >
                  Per-file Axis
                </Button>
                <Button variant="outline" size="sm" className="h-7 text-xs" onClick={clearVisible}>Hide All</Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs text-destructive hover:text-destructive"
                  onClick={clearCompareSessionState}
                >
                  Clear Session
                </Button>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {sessionCardSampleIds.map((sampleId) => {
              const isVisible = visibleSampleIds.includes(sampleId)
              const isPrimary = (fcsCompareSession.primarySampleId || sessionCardSampleIds[0]) === sampleId
              const status = compareStatusBySampleId[sampleId]
              const compareMeta = (fcsCompareSession.compareItemMetaById ?? {})[sampleId]
              const metadata = compareMeta
                ? { treatment: compareMeta.treatment, dye: compareMeta.dye }
                : sampleMetadataById.get(sampleId)
              const statusVariant = status === "error" ? "destructive" : status === "ready" ? "default" : "outline"
              const statusLabel = status === "loading"
                ? "Loading"
                : status === "error"
                  ? "Error"
                  : status === "ready"
                    ? "Ready"
                    : "Queued"

              return (
                <div key={sampleId} className="flex items-center gap-2 rounded-md border p-2">
                  <Badge variant="outline" className="font-mono">{getCompareDisplayLabel(sampleId)}</Badge>
                  <Badge variant={statusVariant}>{statusLabel}</Badge>
                  {isPrimary && <Badge variant="secondary">Reference</Badge>}
                  {isVisible ? <Badge>Visible</Badge> : <Badge variant="outline">Hidden</Badge>}
                  {metadata?.treatment && <Badge variant="outline">Tx: {metadata.treatment}</Badge>}
                  {metadata?.dye && <Badge variant="outline">Dye: {metadata.dye}</Badge>}
                  {replicateGroupingMode === "prefix" && (
                    <Badge variant="outline">
                      Group {getCompareDisplayLabel(sampleId).split(/[_-]/)[0] || getCompareDisplayLabel(sampleId)}
                    </Badge>
                  )}

                  <div className="ml-auto flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2"
                      onClick={() => setFCSComparePrimarySampleId(sampleId)}
                      disabled={isPrimary}
                    >
                      Set Reference
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2"
                      onClick={() => {
                        setActivePeerSampleId(sampleId)
                        setActiveView("comparison")
                      }}
                      disabled={compareMode !== "pairwise" || isPrimary || effectivePeerSampleId === sampleId}
                    >
                      Set Peer
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2"
                      onClick={() => {
                        setInspectionSampleId(sampleId)
                        setActiveView("sample")
                      }}
                    >
                      Details
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2"
                      onClick={() => toggleFCSCompareSampleVisibility(sampleId)}
                      disabled={compareMode !== "multi-overlay"}
                    >
                      {isVisible ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2 text-destructive hover:text-destructive"
                      onClick={() => removeFromSession(sampleId)}
                    >
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              )
            })}
          </CardContent>
        </Card>
      )}

      {/* Tab Contents */}
      {activeView === "primary" && hasPrimaryResults && (
        <PrimaryAnalysisPanel 
          onReset={handleResetPrimary}
          sampleId={fcsAnalysis.sampleId}
          scatterData={
            (fcsCompareSession.primarySampleId
              ? (fcsCompareSession.scatterBySampleId[fcsCompareSession.primarySampleId] ?? EMPTY_SCATTER_POINTS)
              : EMPTY_SCATTER_POINTS)
          }
          secondarySampleId={secondaryFcsAnalysis.sampleId}
          secondaryResults={secondaryFcsAnalysis.results}
          secondaryScatterData={secondaryFcsAnalysis.scatterData ?? EMPTY_SCATTER_POINTS}
        />
      )}

      {activeView === "comparison" && hasComparisonResults && (
        <ComparisonAnalysisPanel 
          onReset={handleResetComparison}
          sampleId={secondaryFcsAnalysis.sampleId}
          scatterData={
            (effectivePeerSampleId
              ? (fcsCompareSession.scatterBySampleId[effectivePeerSampleId] ?? EMPTY_SCATTER_POINTS)
              : EMPTY_SCATTER_POINTS)
          }
          secondarySampleId={fcsAnalysis.sampleId}
          secondaryResults={fcsAnalysis.results}
          secondaryScatterData={
            (fcsCompareSession.primarySampleId
              ? (fcsCompareSession.scatterBySampleId[fcsCompareSession.primarySampleId] ?? EMPTY_SCATTER_POINTS)
              : EMPTY_SCATTER_POINTS)
          }
        />
      )}

      {activeView === "overlay" && (
        <OverlayAnalysisPanel
          graphInstances={fcsCompareGraphInstances}
          activeGraphInstanceId={activeGraphInstance?.id || null}
          onSelectGraphInstance={setActiveFCSCompareGraphInstance}
          onCreateGraphInstance={handleCreateGraphInstance}
          onDuplicateGraphInstance={handleDuplicateGraphInstance}
          onRemoveGraphInstance={handleRemoveGraphInstance}
          graphTitle={activeGraphInstance?.title || "Overlay Graph"}
          graphMaximized={Boolean(activeGraphInstance?.isMaximized)}
          onToggleGraphMaximize={() => {
            if (!activeGraphInstance) return
            updateFCSCompareGraphInstance(activeGraphInstance.id, {
              isMaximized: !activeGraphInstance.isMaximized,
            })
          }}
          pinChart={pinChart}
          axisMode={axisMode}
          onAxisModeChange={handleAxisModeChange}
          onUnifiedAxisChange={handleUnifiedAxisChange}
          onPrimaryAxisChange={handlePrimaryAxisChange}
          onComparisonAxisChange={handleComparisonAxisChange}
          loadingBySampleId={compareLoadingBySampleId}
          errorsBySampleId={compareErrorsBySampleId}
          onRetrySample={retrySample}
          primaryAxisResolution={primaryAxisResolution}
          comparisonAxisResolution={comparisonAxisResolution}
          normalizedPrimaryOptions={normalizedPrimaryOptions}
          normalizedComparisonOptions={normalizedComparisonOptions}
          normalizedUnifiedOptions={normalizedUnifiedOptions}
          primaryAxisMappingLabel={formatChannelMappingLabel(primarySchema, requestedPrimaryX)}
          comparisonAxisMappingLabel={formatChannelMappingLabel(comparisonSchema, requestedComparisonX)}
          replicateRenderMode={replicateRenderMode}
          replicateGroups={replicateGroups}
          visibleSampleIds={visibleSampleIds}
          compareScatterBySampleId={fcsCompareSession.scatterBySampleId}
          primarySampleId={primarySampleId}
          sampleLabelsById={Object.fromEntries(
            compareSampleIds.map((id) => [id, getCompareDisplayLabel(id)])
          )}
          scatterPointCap={activeScatterPointCap}
        />
      )}

      {activeView === "sample" && (
        <SampleDetailAnalysisPanel
          sampleIds={compareSampleIds}
          sampleLabelsById={Object.fromEntries(
            compareSampleIds.map((id) => [id, getCompareDisplayLabel(id)])
          )}
          selectedSampleId={inspectionSampleId}
          onSelectSampleId={setInspectionSampleId}
          scatterBySampleId={fcsCompareSession.scatterBySampleId}
          compareItemMetaById={fcsCompareSession.compareItemMetaById}
        />
      )}
    </div>
  )
}

function SampleDetailAnalysisPanel({
  sampleIds,
  sampleLabelsById,
  selectedSampleId,
  onSelectSampleId,
  scatterBySampleId,
  compareItemMetaById,
}: {
  sampleIds: string[]
  sampleLabelsById: Record<string, string>
  selectedSampleId: string | null
  onSelectSampleId: (sampleId: string) => void
  scatterBySampleId: Record<string, Array<{ x: number; y: number; index?: number; diameter?: number }> | null>
  compareItemMetaById: Record<string, { backendSampleId: string } | undefined>
}) {
  const { fcsCompareSession } = useAnalysisStore()

  const resolvedSampleId = selectedSampleId && sampleIds.includes(selectedSampleId)
    ? selectedSampleId
    : (sampleIds[0] ?? null)

  const selectedResult = resolvedSampleId
    ? (fcsCompareSession.resultsBySampleId[resolvedSampleId] ?? null)
    : null
  const selectedScatter = resolvedSampleId
    ? (scatterBySampleId[resolvedSampleId] ?? EMPTY_SCATTER_POINTS)
    : EMPTY_SCATTER_POINTS
  const selectedBackendSampleId = resolvedSampleId
    ? (compareItemMetaById[resolvedSampleId]?.backendSampleId || resolvedSampleId)
    : null

  if (!resolvedSampleId) {
    return (
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>No compare samples selected</AlertTitle>
        <AlertDescription>Upload compare files to inspect per-sample details.</AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-4">
      <Card className="card-3d">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <CardTitle className="text-base">Sample Detail View</CardTitle>
            <Select value={resolvedSampleId} onValueChange={onSelectSampleId}>
              <SelectTrigger className="h-8 w-60">
                <SelectValue placeholder="Select sample" />
              </SelectTrigger>
              <SelectContent>
                {sampleIds.map((id) => (
                  <SelectItem key={id} value={id}>{sampleLabelsById[id] || id}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
      </Card>

      {!selectedResult ? (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Sample still loading</AlertTitle>
          <AlertDescription>
            {sampleLabelsById[resolvedSampleId] || resolvedSampleId} has not finished loading yet. Wait for compare loading to complete, then retry.
          </AlertDescription>
        </Alert>
      ) : (
        <>
          {(selectedScatter.length === 0 || !selectedBackendSampleId) && (
            <Alert className="border-amber-300 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800">
              <AlertCircle className="h-4 w-4 text-amber-500" />
              <AlertTitle className="text-sm font-semibold text-amber-700 dark:text-amber-400">
                Limited chart inputs for sample detail
              </AlertTitle>
              <AlertDescription className="text-xs text-amber-700 dark:text-amber-300">
                {selectedScatter.length === 0
                  ? "Scatter points are unavailable for this sample, so scatter-based charts may appear sparse or empty."
                  : "Sample ID mapping is unavailable, so per-event charts may not load until mapping is resolved."}
              </AlertDescription>
            </Alert>
          )}
          <StatisticsCards results={selectedResult} />
          <FullAnalysisDashboard
            results={selectedResult}
            scatterData={selectedScatter}
            sampleId={selectedBackendSampleId || undefined}
          />
        </>
      )}
    </div>
  )
}

/**
 * Reference Analysis Panel - Full analysis of the reference sample
 */
function PrimaryAnalysisPanel({
  onReset,
  sampleId,
  scatterData,
  secondarySampleId,
  secondaryResults,
  secondaryScatterData,
}: {
  onReset: () => void
  sampleId: string | null
  scatterData: Array<{ x: number; y: number; index?: number; diameter?: number }>
  secondarySampleId: string | null
  secondaryResults: ReturnType<typeof useAnalysisStore.getState>["secondaryFcsAnalysis"]["results"]
  secondaryScatterData: Array<{ x: number; y: number; index?: number; diameter?: number }>
}) {
  const { fcsAnalysis } = useAnalysisStore()
  const results = fcsAnalysis.results

  if (!results) return null

  return (
    <div className="space-y-4">
      {/* File Info Header */}
      <Card className="bg-primary/5 border-primary/20">
        <CardContent className="py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">{fcsAnalysis.file?.name || fcsAnalysis.sampleId || "Reference File"}</p>
                <p className="text-xs text-muted-foreground">
                  {results.total_events?.toLocaleString()} events • {results.channels?.length || 0} channels
                </p>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={onReset} className="text-muted-foreground hover:text-destructive">
              <RotateCcw className="h-4 w-4 mr-1" />
              Reset
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Statistics Cards */}
      <StatisticsCards results={results} />

      {(scatterData.length === 0 || !sampleId) && (
        <Alert className="border-amber-300 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800">
          <AlertCircle className="h-4 w-4 text-amber-500" />
          <AlertTitle className="text-sm font-semibold text-amber-700 dark:text-amber-400">
            Limited chart inputs for reference view
          </AlertTitle>
          <AlertDescription className="text-xs text-amber-700 dark:text-amber-300">
            {scatterData.length === 0
              ? "Reference scatter data is not available yet, so distribution and scatter charts can appear empty."
              : "Reference sample ID is missing, so per-event charts may not load."}
          </AlertDescription>
        </Alert>
      )}

      {/* Full Analysis Dashboard will show all charts */}
      <FullAnalysisDashboard
        results={results}
        scatterData={scatterData}
        sampleId={sampleId || undefined}
        secondaryResults={secondaryResults}
        secondaryScatterData={secondaryScatterData}
      />
    </div>
  )
}

/**
 * Session Peer Analysis Panel - Full analysis of the active peer sample
 */
function ComparisonAnalysisPanel({
  onReset,
  sampleId,
  scatterData,
  secondarySampleId,
  secondaryResults,
  secondaryScatterData,
}: {
  onReset: () => void
  sampleId: string | null
  scatterData: Array<{ x: number; y: number; index?: number; diameter?: number }>
  secondarySampleId: string | null
  secondaryResults: ReturnType<typeof useAnalysisStore.getState>["fcsAnalysis"]["results"]
  secondaryScatterData: Array<{ x: number; y: number; index?: number; diameter?: number }>
}) {
  const { secondaryFcsAnalysis } = useAnalysisStore()
  const results = secondaryFcsAnalysis.results

  if (!results) return null

  return (
    <div className="space-y-4">
      {/* File Info Header */}
      <Card className="bg-orange-500/5 border-orange-500/20">
        <CardContent className="py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="h-5 w-5 text-orange-500" />
              <div>
                <p className="font-medium">{secondaryFcsAnalysis.file?.name || secondaryFcsAnalysis.sampleId || "Session Peer"}</p>
                <p className="text-xs text-muted-foreground">
                  {results.total_events?.toLocaleString()} events • {results.channels?.length || 0} channels
                </p>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={onReset} className="text-muted-foreground hover:text-destructive">
              <RotateCcw className="h-4 w-4 mr-1" />
              Reset
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Statistics Cards for secondary file */}
      <StatisticsCards results={results} />

      {(scatterData.length === 0 || !sampleId) && (
        <Alert className="border-amber-300 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800">
          <AlertCircle className="h-4 w-4 text-amber-500" />
          <AlertTitle className="text-sm font-semibold text-amber-700 dark:text-amber-400">
            Limited chart inputs for session peer view
          </AlertTitle>
          <AlertDescription className="text-xs text-amber-700 dark:text-amber-300">
            {scatterData.length === 0
              ? "Peer scatter data is not available yet, so distribution and scatter charts can appear empty."
              : "Peer sample ID is missing, so per-event charts may not load."}
          </AlertDescription>
        </Alert>
      )}

      {/* Full Analysis Dashboard - show all charts including scatter plots */}
      <FullAnalysisDashboard
        results={results}
        scatterData={scatterData}
        sampleId={sampleId || undefined}
        secondaryResults={secondaryResults}
        secondaryScatterData={secondaryScatterData}
      />
    </div>
  )
}

/**
 * Overlay Analysis Panel - Combined comparison view
 */
function OverlayAnalysisPanel({
  graphInstances,
  activeGraphInstanceId,
  onSelectGraphInstance,
  onCreateGraphInstance,
  onDuplicateGraphInstance,
  onRemoveGraphInstance,
  graphTitle,
  graphMaximized,
  onToggleGraphMaximize,
  pinChart,
  axisMode,
  onAxisModeChange,
  onUnifiedAxisChange,
  onPrimaryAxisChange,
  onComparisonAxisChange,
  loadingBySampleId,
  errorsBySampleId,
  onRetrySample,
  primaryAxisResolution,
  comparisonAxisResolution,
  normalizedPrimaryOptions,
  normalizedComparisonOptions,
  normalizedUnifiedOptions,
  primaryAxisMappingLabel,
  comparisonAxisMappingLabel,
  replicateRenderMode,
  replicateGroups,
  visibleSampleIds,
  compareScatterBySampleId,
  primarySampleId,
  sampleLabelsById,
  scatterPointCap,
}: {
  graphInstances: Array<{ id: string; title: string }>
  activeGraphInstanceId: string | null
  onSelectGraphInstance: (instanceId: string) => void
  onCreateGraphInstance: () => void
  onDuplicateGraphInstance: () => void
  onRemoveGraphInstance: () => void
  graphTitle: string
  graphMaximized: boolean
  onToggleGraphMaximize: () => void
  pinChart: (chart: {
    id: string
    title: string
    source: string
    timestamp: Date
    type: "histogram" | "scatter" | "line" | "bar"
    data: unknown
    config?: {
      xAxisLabel?: string
      yAxisLabel?: string
      color?: string
      secondaryColor?: string
      showGrid?: boolean
      domain?: { x?: [number, number]; y?: [number, number] }
    }
  }) => void
  axisMode: "unified" | "per-file"
  onAxisModeChange: (mode: "unified" | "per-file") => void
  onUnifiedAxisChange: (xChannel: string, yChannel: string) => void
  onPrimaryAxisChange: (xChannel: string, yChannel: string) => void
  onComparisonAxisChange: (xChannel: string, yChannel: string) => void
  loadingBySampleId: Record<string, boolean>
  errorsBySampleId: Record<string, string>
  onRetrySample: (sampleId: string) => void
  primaryAxisResolution: ReturnType<typeof resolveFCSAxes>
  comparisonAxisResolution: ReturnType<typeof resolveFCSAxes>
  normalizedPrimaryOptions: string[]
  normalizedComparisonOptions: string[]
  normalizedUnifiedOptions: string[]
  primaryAxisMappingLabel: string
  comparisonAxisMappingLabel: string
  replicateRenderMode: ReplicateRenderMode
  replicateGroups: Array<{ id: string; label: string; sampleIds: string[] }>
  visibleSampleIds: string[]
  compareScatterBySampleId: Record<string, Array<{ x: number; y: number; index?: number; diameter?: number }>>
  primarySampleId: string | null
  sampleLabelsById: Record<string, string>
  scatterPointCap: number
}) {
  const { fcsAnalysis, secondaryFcsAnalysis, overlayConfig, fcsCompareSession } = useAnalysisStore()
  const { toast } = useToast()
  const primaryResults = fcsAnalysis.results
  const secondaryResults = secondaryFcsAnalysis.results
  const effectivePrimaryResults = primaryResults ?? secondaryResults
  const effectiveSecondaryResults = secondaryResults ?? primaryResults
  const comparisonSampleIds = useMemo(
    () => visibleSampleIds.filter((sampleId) => sampleId && sampleId !== primarySampleId),
    [visibleSampleIds, primarySampleId]
  )
  const isMultiOverlay = overlayConfig.enabled && comparisonSampleIds.length > 1
  const comparisonColorBySampleId = useMemo(() => {
    const map: Record<string, string> = {}
    comparisonSampleIds.forEach((sampleId, index) => {
      map[sampleId] = index === 0
        ? overlayConfig.secondaryColor
        : COMPARE_OVERLAY_PALETTE[(index - 1) % COMPARE_OVERLAY_PALETTE.length]
    })
    return map
  }, [comparisonSampleIds, overlayConfig.secondaryColor])
  const [primaryScatterData, setPrimaryScatterData] = useState<Array<{ x: number; y: number; index?: number; diameter?: number }>>([])
  const [secondaryScatterData, setSecondaryScatterData] = useState<Array<{ x: number; y: number; index?: number; diameter?: number }>>([])
  const [scatterDensityMode, setScatterDensityMode] = useState<ScatterDensityMode>("auto")
  const [scatterZoomPreset, setScatterZoomPreset] = useState<ScatterZoomPreset>("auto")
  const [showRawOverlayInDensity, setShowRawOverlayInDensity] = useState(false)
  const [primaryDensityCells, setPrimaryDensityCells] = useState<Array<{ x: number; y: number; count: number; normalized: number }>>([])
  const [secondaryDensityCells, setSecondaryDensityCells] = useState<Array<{ x: number; y: number; count: number; normalized: number }>>([])
  const [primaryScatterLoaded, setPrimaryScatterLoaded] = useState(false)
  const [secondaryScatterLoaded, setSecondaryScatterLoaded] = useState(false)
  const densityRequestIdRef = useRef(1)

  useEffect(() => {
    if (!fcsAnalysis.sampleId) return

    let cancelled = false
    setPrimaryScatterLoaded(false)

    const loadPrimaryScatter = async () => {
      try {
        const response = await apiClient.getScatterDataWithAxes(
          fcsAnalysis.sampleId!,
          primaryAxisResolution.resolvedX,
          primaryAxisResolution.resolvedY,
          scatterPointCap
        )
        if (cancelled) return
        const points = (response?.data ?? []) as Array<{ x: number; y: number; index?: number; diameter?: number }>
        setPrimaryScatterData(points)
      } catch {
        if (!cancelled) {
          setPrimaryScatterData([])
        }
      } finally {
        if (!cancelled) {
          setPrimaryScatterLoaded(true)
        }
      }
    }

    loadPrimaryScatter()

    return () => {
      cancelled = true
    }
  }, [fcsAnalysis.sampleId, scatterPointCap, primaryAxisResolution.resolvedX, primaryAxisResolution.resolvedY])

  useEffect(() => {
    if (!secondaryFcsAnalysis.sampleId) return

    let cancelled = false
    setSecondaryScatterLoaded(false)

    const loadSecondaryScatter = async () => {
      try {
        const response = await apiClient.getScatterDataWithAxes(
          secondaryFcsAnalysis.sampleId!,
          comparisonAxisResolution.resolvedX,
          comparisonAxisResolution.resolvedY,
          scatterPointCap
        )
        if (cancelled) return
        const points = (response?.data ?? []) as Array<{ x: number; y: number; index?: number; diameter?: number }>
        setSecondaryScatterData(points)
      } catch {
        if (!cancelled) {
          setSecondaryScatterData([])
        }
      } finally {
        if (!cancelled) {
          setSecondaryScatterLoaded(true)
        }
      }
    }

    loadSecondaryScatter()

    return () => {
      cancelled = true
    }
  }, [secondaryFcsAnalysis.sampleId, scatterPointCap, comparisonAxisResolution.resolvedX, comparisonAxisResolution.resolvedY])

  const mergedComparisonScatterData = useMemo(() => {
    if (replicateRenderMode !== "merged-points") {
      return secondaryScatterData
    }

    const merged = visibleSampleIds
      .filter((sampleId) => sampleId !== primarySampleId)
      .flatMap((sampleId) => compareScatterBySampleId[sampleId] || [])
      .slice(0, scatterPointCap)

    return merged.length > 0 ? merged : secondaryScatterData
  }, [
    replicateRenderMode,
    visibleSampleIds,
    primarySampleId,
    compareScatterBySampleId,
    scatterPointCap,
    secondaryScatterData,
  ])

  const primaryShouldUseDensity = scatterDensityMode === "density"
    || (scatterDensityMode === "auto" && primaryScatterData.length >= DENSITY_TRIGGER_POINTS)
  const secondaryShouldUseDensity = scatterDensityMode === "density"
    || (scatterDensityMode === "auto" && mergedComparisonScatterData.length >= DENSITY_TRIGGER_POINTS)

  const zoomDomain = useMemo(
    () => buildZoomDomain(primaryScatterData, mergedComparisonScatterData, scatterZoomPreset),
    [primaryScatterData, mergedComparisonScatterData, scatterZoomPreset]
  )

  useEffect(() => {
    let cancelled = false

    const buildDensityFallbacks = async () => {
      if (!primaryShouldUseDensity && !secondaryShouldUseDensity) {
        setPrimaryDensityCells([])
        setSecondaryDensityCells([])
        return
      }

      const requests: Array<Promise<void>> = []

      if (primaryShouldUseDensity) {
        const requestId = densityRequestIdRef.current++
        requests.push(
          runScatterDensitySeriesWorker(requestId, {
            points: primaryScatterData,
            xBins: 36,
            yBins: 36,
            maxCells: 900,
          }).then((payload) => {
            if (!cancelled) {
              setPrimaryDensityCells(payload.cells)
            }
          }).catch(() => {
            if (!cancelled) {
              setPrimaryDensityCells([])
            }
          })
        )
      } else {
        setPrimaryDensityCells([])
      }

      if (secondaryShouldUseDensity) {
        const requestId = densityRequestIdRef.current++
        requests.push(
          runScatterDensitySeriesWorker(requestId, {
            points: mergedComparisonScatterData,
            xBins: 36,
            yBins: 36,
            maxCells: 900,
          }).then((payload) => {
            if (!cancelled) {
              setSecondaryDensityCells(payload.cells)
            }
          }).catch(() => {
            if (!cancelled) {
              setSecondaryDensityCells([])
            }
          })
        )
      } else {
        setSecondaryDensityCells([])
      }

      await Promise.all(requests)
    }

    buildDensityFallbacks()

    return () => {
      cancelled = true
    }
  }, [
    primaryShouldUseDensity,
    secondaryShouldUseDensity,
    primaryScatterData,
    mergedComparisonScatterData,
  ])

  if (!effectivePrimaryResults || !effectiveSecondaryResults) return null

  const handlePinGraph = useCallback(() => {
    const comparisonScatterBySampleId: Record<string, Array<{ x: number; y: number; index?: number; diameter?: number }>> = {}
    comparisonSampleIds.forEach((sampleId) => {
      if (sampleId === secondaryFcsAnalysis.sampleId && secondaryScatterData.length > 0) {
        comparisonScatterBySampleId[sampleId] = secondaryScatterData
      } else {
        comparisonScatterBySampleId[sampleId] = compareScatterBySampleId[sampleId] || []
      }
    })

    const combinedPoints = [
      ...primaryScatterData.map((point) => ({
        x: point.x,
        y: point.y,
        label: sampleLabelsById[primarySampleId || ""] || fcsAnalysis.file?.name || "Reference",
        category: "primary",
        sampleId: primarySampleId,
      })),
      ...(isMultiOverlay
        ? comparisonSampleIds.flatMap((sampleId) =>
            (comparisonScatterBySampleId[sampleId] || []).map((point) => ({
              x: point.x,
              y: point.y,
              label: sampleLabelsById[sampleId] || sampleId,
              category: sampleId,
              sampleId,
            }))
          )
        : mergedComparisonScatterData.map((point) => ({
            x: point.x,
            y: point.y,
            label: sampleLabelsById[comparisonSampleIds[0] || ""] || "Session Peer",
            category: "comparison",
            sampleId: comparisonSampleIds[0] || secondaryFcsAnalysis.sampleId,
          }))),
    ]

    if (combinedPoints.length === 0) {
      toast({
        title: "No Data to Pin",
        description: "Load overlay scatter data before pinning this graph.",
        variant: "destructive",
      })
      return
    }

    pinChart({
      id: crypto.randomUUID(),
      title: `${graphTitle}: Scatter Overlay`,
      source: "Flow Cytometry Compare",
      timestamp: new Date(),
      type: "scatter",
      data: combinedPoints,
      config: {
        xAxisLabel: primaryAxisResolution.resolvedX,
        yAxisLabel: primaryAxisResolution.resolvedY,
        color: overlayConfig.primaryColor,
        secondaryColor: overlayConfig.secondaryColor,
      },
    })

    toast({
      title: "Graph Pinned",
      description: isMultiOverlay
        ? `${graphTitle} pinned with ${comparisonSampleIds.length + 1} overlay series.`
        : `${graphTitle} pinned with reference and peer series context.`,
    })
  }, [
    compareScatterBySampleId,
    comparisonSampleIds,
    graphTitle,
    isMultiOverlay,
    overlayConfig.primaryColor,
    overlayConfig.secondaryColor,
    pinChart,
    primarySampleId,
    primaryAxisResolution.resolvedX,
    primaryAxisResolution.resolvedY,
    primaryScatterData,
    sampleLabelsById,
    secondaryFcsAnalysis.sampleId,
    secondaryScatterData,
    mergedComparisonScatterData,
    toast,
  ])

  const handleExportGraph = useCallback(() => {
    const comparisonRows = isMultiOverlay
      ? comparisonSampleIds.flatMap((sampleId) => {
          const points = (sampleId === secondaryFcsAnalysis.sampleId && secondaryScatterData.length > 0)
            ? secondaryScatterData
            : (compareScatterBySampleId[sampleId] || [])
          return points.map((point) =>
            `${sampleLabelsById[sampleId] || sampleId},${sampleId},${comparisonAxisResolution.resolvedX},${comparisonAxisResolution.resolvedY},${point.x},${point.y},${point.index ?? ""},${point.diameter ?? ""}`
          )
        })
      : mergedComparisonScatterData.map((point) =>
          `comparison,${secondaryFcsAnalysis.sampleId || ""},${comparisonAxisResolution.resolvedX},${comparisonAxisResolution.resolvedY},${point.x},${point.y},${point.index ?? ""},${point.diameter ?? ""}`
        )

    const rows = [
      "series,sample_id,x_channel,y_channel,x,y,index,diameter",
      ...primaryScatterData.map((point) =>
        `primary,${fcsAnalysis.sampleId || ""},${primaryAxisResolution.resolvedX},${primaryAxisResolution.resolvedY},${point.x},${point.y},${point.index ?? ""},${point.diameter ?? ""}`
      ),
      ...comparisonRows,
    ]

    const csvBlob = new Blob([rows.join("\n")], { type: "text/csv;charset=utf-8;" })
    const url = URL.createObjectURL(csvBlob)
    const link = document.createElement("a")
    link.href = url
    link.download = isMultiOverlay
      ? `${(fcsAnalysis.sampleId || "reference")}_overlay_${comparisonSampleIds.length + 1}_series.csv`
      : `${(fcsAnalysis.sampleId || "reference")}_vs_${(secondaryFcsAnalysis.sampleId || "peer")}_overlay.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    toast({
      title: "Export Complete",
      description: `${graphTitle} overlay data exported to CSV.`,
    })
  }, [
    compareScatterBySampleId,
    comparisonAxisResolution.resolvedX,
    comparisonAxisResolution.resolvedY,
    comparisonSampleIds,
    fcsAnalysis.sampleId,
    graphTitle,
    isMultiOverlay,
    mergedComparisonScatterData,
    primaryAxisResolution.resolvedX,
    primaryAxisResolution.resolvedY,
    primaryScatterData,
    sampleLabelsById,
    secondaryFcsAnalysis.sampleId,
    secondaryScatterData,
    toast,
  ])

  const primaryDisplayed = primaryScatterData.length
  const primaryTotal = effectivePrimaryResults.total_events || 0
  const secondaryDisplayed = mergedComparisonScatterData.length
  const secondaryTotal = effectiveSecondaryResults.total_events || 0
  const primaryDownsampled = primaryTotal > primaryDisplayed && primaryDisplayed > 0
  const secondaryDownsampled = secondaryTotal > secondaryDisplayed && secondaryDisplayed > 0
  const comparisonDisplayedBySampleId = useMemo(() => {
    const map: Record<string, number> = {}
    comparisonSampleIds.forEach((sampleId) => {
      if (sampleId === secondaryFcsAnalysis.sampleId && secondaryScatterData.length > 0) {
        map[sampleId] = secondaryScatterData.length
      } else {
        map[sampleId] = (compareScatterBySampleId[sampleId] || []).length
      }
    })
    return map
  }, [compareScatterBySampleId, comparisonSampleIds, secondaryFcsAnalysis.sampleId, secondaryScatterData.length])

  const comparisonResultsBySampleId = useMemo(() => {
    const map: Record<string, ReturnType<typeof useAnalysisStore.getState>["fcsCompareSession"]["resultsBySampleId"][string] | null> = {}
    comparisonSampleIds.forEach((sampleId) => {
      map[sampleId] = fcsCompareSession.resultsBySampleId[sampleId]
        || (sampleId === secondaryFcsAnalysis.sampleId ? secondaryFcsAnalysis.results : null)
    })
    return map
  }, [comparisonSampleIds, fcsCompareSession.resultsBySampleId, secondaryFcsAnalysis.results, secondaryFcsAnalysis.sampleId])

  const multiOverlayDifferences = useMemo(() => {
    if (!effectivePrimaryResults) {
      return []
    }

    return comparisonSampleIds.map((sampleId) => {
      const sampleResults = comparisonResultsBySampleId[sampleId]
      return {
        sampleId,
        label: sampleLabelsById[sampleId] || sampleId,
        eventDiff: (sampleResults?.total_events || 0) - (effectivePrimaryResults.total_events || 0),
        d50Diff: (sampleResults?.size_statistics?.d50 || 0) - (effectivePrimaryResults.size_statistics?.d50 || 0),
        fscMedianDiff: (sampleResults?.fsc_median || 0) - (effectivePrimaryResults.fsc_median || 0),
        debrisDiff: (sampleResults?.debris_pct || 0) - (effectivePrimaryResults.debris_pct || 0),
      }
    })
  }, [comparisonResultsBySampleId, comparisonSampleIds, effectivePrimaryResults, sampleLabelsById])

  return (
    <div className={cn("space-y-4", graphMaximized && "fixed inset-4 z-50 bg-background p-4 overflow-auto border rounded-lg shadow-2xl")}>
      <Card className="card-3d">
        <CardContent className="py-3">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div className="flex items-center gap-2">
              <Select value={activeGraphInstanceId || undefined} onValueChange={onSelectGraphInstance}>
                <SelectTrigger className="w-[220px] h-8">
                  <SelectValue placeholder="Select graph" />
                </SelectTrigger>
                <SelectContent>
                  {graphInstances.map((instance) => (
                    <SelectItem key={instance.id} value={instance.id}>{instance.title}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Badge variant="outline">{graphTitle}</Badge>
              <Badge variant="outline">Replicate mode: {replicateRenderMode}</Badge>
              {replicateGroups.length > 0 && (
                <Badge variant="secondary">Groups: {replicateGroups.length}</Badge>
              )}
            </div>
            <div className="flex items-center gap-1">
              <Button variant="outline" size="sm" className="h-8 text-xs" onClick={onCreateGraphInstance}>
                <Plus className="h-3.5 w-3.5 mr-1" />
                New
              </Button>
              <Button variant="outline" size="sm" className="h-8 text-xs" onClick={onDuplicateGraphInstance}>
                <Copy className="h-3.5 w-3.5 mr-1" />
                Duplicate
              </Button>
              <Button variant="outline" size="sm" className="h-8 text-xs" onClick={handlePinGraph}>
                <Pin className="h-3.5 w-3.5 mr-1" />
                Pin
              </Button>
              <Button variant="outline" size="sm" className="h-8 text-xs" onClick={handleExportGraph}>
                <Download className="h-3.5 w-3.5 mr-1" />
                Export
              </Button>
              <Button variant="outline" size="sm" className="h-8 text-xs" onClick={onToggleGraphMaximize}>
                {graphMaximized ? <Minimize2 className="h-3.5 w-3.5 mr-1" /> : <Maximize2 className="h-3.5 w-3.5 mr-1" />}
                {graphMaximized ? "Restore" : "Maximize"}
              </Button>
              <Button variant="outline" size="sm" className="h-8 text-xs text-destructive hover:text-destructive" onClick={onRemoveGraphInstance}>
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
      {/* Session Statistics Summary */}
      {!isMultiOverlay ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="bg-primary/5 border-primary/20">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: overlayConfig.primaryColor }} />
                <CardTitle className="text-sm">{fcsAnalysis.file?.name || "Reference"}</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <p className="text-muted-foreground text-xs">Events</p>
                <p className="font-mono font-medium">{effectivePrimaryResults.total_events?.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">D50 Size</p>
                <p className="font-mono font-medium">{effectivePrimaryResults.size_statistics?.d50?.toFixed(1) || "N/A"} nm</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">FSC Median</p>
                <p className="font-mono font-medium">{effectivePrimaryResults.fsc_median?.toFixed(1) || "N/A"}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Debris %</p>
                <p className="font-mono font-medium">{effectivePrimaryResults.debris_pct?.toFixed(1) || "N/A"}%</p>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-orange-500/5 border-orange-500/20">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: overlayConfig.secondaryColor }} />
                <CardTitle className="text-sm">{secondaryFcsAnalysis.file?.name || "Session Peer"}</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <p className="text-muted-foreground text-xs">Events</p>
                <p className="font-mono font-medium">{effectiveSecondaryResults.total_events?.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">D50 Size</p>
                <p className="font-mono font-medium">{effectiveSecondaryResults.size_statistics?.d50?.toFixed(1) || "N/A"} nm</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">FSC Median</p>
                <p className="font-mono font-medium">{effectiveSecondaryResults.fsc_median?.toFixed(1) || "N/A"}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Debris %</p>
                <p className="font-mono font-medium">{effectiveSecondaryResults.debris_pct?.toFixed(1) || "N/A"}%</p>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          <Card className="bg-primary/5 border-primary/20">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: overlayConfig.primaryColor }} />
                <CardTitle className="text-sm">{sampleLabelsById[primarySampleId || ""] || fcsAnalysis.file?.name || "Reference"}</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <p className="text-muted-foreground text-xs">Events</p>
                <p className="font-mono font-medium">{effectivePrimaryResults.total_events?.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Rendered</p>
                <p className="font-mono font-medium">{primaryDisplayed.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">D50</p>
                <p className="font-mono font-medium">{effectivePrimaryResults.size_statistics?.d50?.toFixed(1) || "N/A"} nm</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Debris %</p>
                <p className="font-mono font-medium">{effectivePrimaryResults.debris_pct?.toFixed(1) || "N/A"}%</p>
              </div>
            </CardContent>
          </Card>

          {comparisonSampleIds.map((sampleId) => {
            const result = comparisonResultsBySampleId[sampleId]
            const displayed = comparisonDisplayedBySampleId[sampleId] || 0
            const total = result?.total_events || 0
            const downsampled = total > displayed && displayed > 0
            const color = comparisonColorBySampleId[sampleId] || overlayConfig.secondaryColor
            return (
              <Card key={sampleId} className="border-orange-500/20 bg-orange-500/5">
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                    <CardTitle className="text-sm truncate" title={sampleLabelsById[sampleId] || sampleId}>
                      {sampleLabelsById[sampleId] || sampleId}
                    </CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <p className="text-muted-foreground text-xs">Events</p>
                    <p className="font-mono font-medium">{total.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Rendered</p>
                    <p className="font-mono font-medium">{displayed.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">D50</p>
                    <p className="font-mono font-medium">{result?.size_statistics?.d50?.toFixed(1) || "N/A"} nm</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Debris %</p>
                    <p className="font-mono font-medium">{result?.debris_pct?.toFixed(1) || "N/A"}%</p>
                  </div>
                </CardContent>
                {downsampled && (
                  <div className="px-6 pb-3 text-xs text-muted-foreground">Downsampled for rendering cap</div>
                )}
              </Card>
            )
          })}
        </div>
      )}

      {/* Difference Summary */}
      {!isMultiOverlay ? (
        <Card className="card-3d">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <GitCompare className="h-4 w-4 text-primary" />
              <CardTitle className="text-base">Session Difference Summary</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <DifferenceMetric
                label="Event Count Diff"
                primary={effectivePrimaryResults.total_events || 0}
                secondary={effectiveSecondaryResults.total_events || 0}
              />
              <DifferenceMetric
                label="D50 Size Diff"
                primary={effectivePrimaryResults.size_statistics?.d50 || 0}
                secondary={effectiveSecondaryResults.size_statistics?.d50 || 0}
                unit="nm"
              />
              <DifferenceMetric
                label="FSC Median Diff"
                primary={effectivePrimaryResults.fsc_median || 0}
                secondary={effectiveSecondaryResults.fsc_median || 0}
              />
              <DifferenceMetric
                label="Debris % Diff"
                primary={effectivePrimaryResults.debris_pct || 0}
                secondary={effectiveSecondaryResults.debris_pct || 0}
                unit="%"
                isPercentage
              />
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="card-3d">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <GitCompare className="h-4 w-4 text-primary" />
              <CardTitle className="text-base">Reference vs Each Overlay Sample</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {multiOverlayDifferences.map((item) => (
              <div key={item.sampleId} className="grid grid-cols-2 md:grid-cols-5 gap-2 rounded-lg border p-2 text-xs">
                <div className="font-medium truncate" title={item.label}>{item.label}</div>
                <div>Events: {item.eventDiff >= 0 ? "+" : ""}{item.eventDiff.toLocaleString()}</div>
                <div>D50: {item.d50Diff >= 0 ? "+" : ""}{item.d50Diff.toFixed(1)} nm</div>
                <div>FSC: {item.fscMedianDiff >= 0 ? "+" : ""}{item.fscMedianDiff.toFixed(1)}</div>
                <div>Debris: {item.debrisDiff >= 0 ? "+" : ""}{item.debrisDiff.toFixed(1)}%</div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Overlay Charts */}
      <OverlayHistogramChart
        title="Size Distribution Overlay"
        parameter="size"
        loadingBySampleId={loadingBySampleId}
        errorsBySampleId={errorsBySampleId}
        onRetrySample={onRetrySample}
        replicateRenderMode={replicateRenderMode}
        visibleSampleIds={visibleSampleIds}
        primarySampleId={primarySampleId}
        compareScatterBySampleId={compareScatterBySampleId}
        sampleLabelsById={sampleLabelsById}
      />
      
      {/* Scatter Comparison */}
      <Card className="card-3d">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div className="flex items-center gap-2">
              <GitCompare className="h-4 w-4 text-primary" />
              <CardTitle className="text-base">
                {primaryAxisResolution.resolvedX} vs {primaryAxisResolution.resolvedY} Scatter Comparison{isMultiOverlay ? " (Multi-overlay)" : ""}
              </CardTitle>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant={axisMode === "unified" ? "default" : "outline"}
                size="sm"
                className="h-8 text-xs"
                onClick={() => onAxisModeChange("unified")}
              >
                Unified Axis
              </Button>
              <Button
                variant={axisMode === "per-file" ? "default" : "outline"}
                size="sm"
                className="h-8 text-xs"
                onClick={() => onAxisModeChange("per-file")}
              >
                Per-file Axis
              </Button>
              <Select value={scatterDensityMode} onValueChange={(value) => setScatterDensityMode(value as ScatterDensityMode)}>
                <SelectTrigger className="h-8 w-[172px] text-xs">
                  <SelectValue placeholder="Scatter mode" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Scatter: auto density</SelectItem>
                  <SelectItem value="raw">Scatter: raw points</SelectItem>
                  <SelectItem value="density">Scatter: density/contour</SelectItem>
                </SelectContent>
              </Select>
              <Select value={scatterZoomPreset} onValueChange={(value) => setScatterZoomPreset(value as ScatterZoomPreset)}>
                <SelectTrigger className="h-8 w-[196px] text-xs">
                  <SelectValue placeholder="Zoom preset" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Zoom: auto</SelectItem>
                  <SelectItem value="center-60">Zoom: center 60%</SelectItem>
                  <SelectItem value="core-30">Zoom: core 30%</SelectItem>
                  <SelectItem value="high-signal">Zoom: high signal band</SelectItem>
                </SelectContent>
              </Select>
              {(primaryShouldUseDensity || secondaryShouldUseDensity) && (
                <Button
                  variant={showRawOverlayInDensity ? "default" : "outline"}
                  size="sm"
                  className="h-8 text-xs"
                  onClick={() => setShowRawOverlayInDensity((prev) => !prev)}
                >
                  Raw Overlay
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="mb-3 grid grid-cols-1 md:grid-cols-2 gap-2">
            {axisMode === "unified" ? (
              <ScatterAxisSelector
                sampleId={fcsAnalysis.sampleId || secondaryFcsAnalysis.sampleId || ""}
                xChannel={primaryAxisResolution.requestedX}
                yChannel={primaryAxisResolution.requestedY}
                onAxisChange={onUnifiedAxisChange}
                compact
                availableChannels={normalizedUnifiedOptions}
              />
            ) : (
              <>
                <ScatterAxisSelector
                  sampleId={fcsAnalysis.sampleId || ""}
                  xChannel={primaryAxisResolution.requestedX}
                  yChannel={primaryAxisResolution.requestedY}
                  onAxisChange={onPrimaryAxisChange}
                  compact
                  availableChannels={normalizedPrimaryOptions}
                />
                <ScatterAxisSelector
                  sampleId={secondaryFcsAnalysis.sampleId || ""}
                  xChannel={comparisonAxisResolution.requestedX}
                  yChannel={comparisonAxisResolution.requestedY}
                  onAxisChange={onComparisonAxisChange}
                  compact
                  availableChannels={normalizedComparisonOptions}
                />
              </>
            )}
          </div>
          <div className="mb-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
            <Badge variant="outline">Reference map: {primaryAxisMappingLabel}</Badge>
            <Badge variant="outline">Comparison map: {comparisonAxisMappingLabel}</Badge>
            <Badge variant="outline">Zoom preset: {scatterZoomPreset}</Badge>
            {(primaryShouldUseDensity || secondaryShouldUseDensity) && (
              <Badge variant="secondary">Density fallback active</Badge>
            )}
            {isMultiOverlay && (
              <Badge variant="secondary">Multi-overlay peers render in raw mode</Badge>
            )}
          </div>
          {(primaryAxisResolution.usedFallback || comparisonAxisResolution.usedFallback) && (
            <Alert className="mb-3 border-amber-300 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800">
              <AlertCircle className="h-4 w-4 text-amber-500" />
              <AlertTitle className="text-sm font-semibold text-amber-700 dark:text-amber-400">Axis fallback active</AlertTitle>
              <AlertDescription className="text-xs text-amber-600 dark:text-amber-300 space-y-1">
                <div>
                  Reference: {primaryAxisResolution.resolvedX} vs {primaryAxisResolution.resolvedY}
                </div>
                <div>
                  Comparison: {comparisonAxisResolution.resolvedX} vs {comparisonAxisResolution.resolvedY}
                </div>
              </AlertDescription>
            </Alert>
          )}
          {!isMultiOverlay ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: overlayConfig.primaryColor }} />
                  <span className="text-sm font-medium">{fcsAnalysis.file?.name || "Reference"}</span>
                  <Badge variant="outline" className="text-xs">
                    {effectivePrimaryResults.total_events?.toLocaleString()} events
                  </Badge>
                  <Badge variant="outline" className="text-xs">
                    Rendered {primaryDisplayed.toLocaleString()} / cap {scatterPointCap.toLocaleString()}
                  </Badge>
                  {primaryDownsampled && (
                    <Badge variant="secondary" className="text-xs">Downsampled</Badge>
                  )}
                </div>
                <div className="h-75 bg-secondary/20 rounded-lg p-2">
                  <ScatterPlotChart
                    title={`Reference ${primaryAxisResolution.resolvedX} vs ${primaryAxisResolution.resolvedY}`}
                    data={primaryScatterData}
                    densityData={primaryDensityCells}
                    renderMode={primaryShouldUseDensity ? "density" : "raw"}
                    showRawOverlayInDensity={showRawOverlayInDensity}
                    xDomain={zoomDomain.xDomain}
                    yDomain={zoomDomain.yDomain}
                    xLabel={primaryAxisResolution.resolvedX}
                    yLabel={primaryAxisResolution.resolvedY}
                    height={280}
                    showLegend={false}
                  />
                  {!primaryScatterLoaded && (
                    <div className="text-xs text-muted-foreground mt-1">Loading reference scatter points...</div>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: overlayConfig.secondaryColor }} />
                  <span className="text-sm font-medium">{secondaryFcsAnalysis.file?.name || "Session Peer"}</span>
                  <Badge variant="outline" className="text-xs">
                    {effectiveSecondaryResults.total_events?.toLocaleString()} events
                  </Badge>
                  <Badge variant="outline" className="text-xs">
                    Rendered {secondaryDisplayed.toLocaleString()} / cap {scatterPointCap.toLocaleString()}
                  </Badge>
                  {secondaryDownsampled && (
                    <Badge variant="secondary" className="text-xs">Downsampled</Badge>
                  )}
                </div>
                <div className="h-75 bg-secondary/20 rounded-lg p-2">
                  <ScatterPlotChart
                    title={`Session Peer ${comparisonAxisResolution.resolvedX} vs ${comparisonAxisResolution.resolvedY}`}
                    data={mergedComparisonScatterData}
                    densityData={secondaryDensityCells}
                    renderMode={secondaryShouldUseDensity ? "density" : "raw"}
                    showRawOverlayInDensity={showRawOverlayInDensity}
                    xDomain={zoomDomain.xDomain}
                    yDomain={zoomDomain.yDomain}
                    xLabel={comparisonAxisResolution.resolvedX}
                    yLabel={comparisonAxisResolution.resolvedY}
                    height={280}
                    showLegend={false}
                  />
                  {!secondaryScatterLoaded && (
                    <div className="text-xs text-muted-foreground mt-1">Loading peer scatter points...</div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: overlayConfig.primaryColor }} />
                  <span className="text-sm font-medium">{sampleLabelsById[primarySampleId || ""] || fcsAnalysis.file?.name || "Reference"}</span>
                  <Badge variant="outline" className="text-xs">{primaryDisplayed.toLocaleString()} rendered</Badge>
                  {primaryDownsampled && <Badge variant="secondary" className="text-xs">Downsampled</Badge>}
                </div>
                <div className="h-75 bg-secondary/20 rounded-lg p-2">
                  <ScatterPlotChart
                    title={`Reference ${primaryAxisResolution.resolvedX} vs ${primaryAxisResolution.resolvedY}`}
                    data={primaryScatterData}
                    densityData={primaryDensityCells}
                    renderMode={primaryShouldUseDensity ? "density" : "raw"}
                    showRawOverlayInDensity={showRawOverlayInDensity}
                    xDomain={zoomDomain.xDomain}
                    yDomain={zoomDomain.yDomain}
                    xLabel={primaryAxisResolution.resolvedX}
                    yLabel={primaryAxisResolution.resolvedY}
                    height={280}
                    showLegend={false}
                  />
                </div>
              </div>

              {comparisonSampleIds.map((sampleId) => {
                const samplePoints = sampleId === secondaryFcsAnalysis.sampleId && secondaryScatterData.length > 0
                  ? secondaryScatterData
                  : (compareScatterBySampleId[sampleId] || [])
                const sampleResult = comparisonResultsBySampleId[sampleId]
                const displayed = comparisonDisplayedBySampleId[sampleId] || 0
                const total = sampleResult?.total_events || 0
                const downsampled = total > displayed && displayed > 0
                const color = comparisonColorBySampleId[sampleId] || overlayConfig.secondaryColor
                return (
                  <div key={sampleId} className="space-y-2">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                      <span className="text-sm font-medium truncate" title={sampleLabelsById[sampleId] || sampleId}>
                        {sampleLabelsById[sampleId] || sampleId}
                      </span>
                      <Badge variant="outline" className="text-xs">{displayed.toLocaleString()} rendered</Badge>
                      {downsampled && <Badge variant="secondary" className="text-xs">Downsampled</Badge>}
                    </div>
                    <div className="h-75 bg-secondary/20 rounded-lg p-2">
                      <ScatterPlotChart
                        title={`${sampleLabelsById[sampleId] || sampleId} ${comparisonAxisResolution.resolvedX} vs ${comparisonAxisResolution.resolvedY}`}
                        data={samplePoints}
                        densityData={[]}
                        renderMode="raw"
                        showRawOverlayInDensity={false}
                        xDomain={zoomDomain.xDomain}
                        yDomain={zoomDomain.yDomain}
                        xLabel={comparisonAxisResolution.resolvedX}
                        yLabel={comparisonAxisResolution.resolvedY}
                        height={280}
                        showLegend={false}
                      />
                      {!!loadingBySampleId[sampleId] && (
                        <div className="text-xs text-muted-foreground mt-1">Loading sample scatter points...</div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <OverlayHistogramChart
        title="Forward Scatter (FSC) Overlay"
        parameter="FSC-A"
        loadingBySampleId={loadingBySampleId}
        errorsBySampleId={errorsBySampleId}
        onRetrySample={onRetrySample}
        replicateRenderMode={replicateRenderMode}
        visibleSampleIds={visibleSampleIds}
        primarySampleId={primarySampleId}
        compareScatterBySampleId={compareScatterBySampleId}
        sampleLabelsById={sampleLabelsById}
      />
      <OverlayHistogramChart
        title="Side Scatter (SSC) Overlay"
        parameter="SSC-A"
        loadingBySampleId={loadingBySampleId}
        errorsBySampleId={errorsBySampleId}
        onRetrySample={onRetrySample}
        replicateRenderMode={replicateRenderMode}
        visibleSampleIds={visibleSampleIds}
        primarySampleId={primarySampleId}
        compareScatterBySampleId={compareScatterBySampleId}
        sampleLabelsById={sampleLabelsById}
      />
    </div>
  )
}

/**
 * Difference Metric Component
 */
function DifferenceMetric({ 
  label, 
  primary, 
  secondary, 
  unit = "",
  isPercentage = false
}: { 
  label: string
  primary: number
  secondary: number
  unit?: string
  isPercentage?: boolean
}) {
  const diff = secondary - primary
  const percentDiff = primary !== 0 ? ((diff / primary) * 100) : 0
  const isPositive = diff > 0
  const isSignificant = Math.abs(percentDiff) > 10

  return (
    <div className="text-center p-2 bg-secondary/30 rounded-lg">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className={cn(
        "font-mono font-medium",
        isSignificant && (isPositive ? "text-orange-500" : "text-emerald-500")
      )}>
        {isPositive ? "+" : ""}{isPercentage ? diff.toFixed(1) : diff.toLocaleString(undefined, { maximumFractionDigits: 1 })}{unit}
      </p>
      <p className="text-[10px] text-muted-foreground">
        ({isPositive ? "+" : ""}{percentDiff.toFixed(1)}%)
      </p>
    </div>
  )
}
