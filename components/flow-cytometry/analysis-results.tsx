"use client"

import { useState, useMemo, useEffect, useCallback, useRef, useTransition } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  Pin, 
  Download, 
  Maximize2, 
  FileText, 
  AlertCircle,
  Table2,
  Eye,
  EyeOff,
  Loader2,
  RotateCcw,
  Layers,
  Grid3X3
} from "lucide-react"
import { useAnalysisStore } from "@/lib/store"
import { useShallow } from "zustand/shallow"
import { useApi } from "@/hooks/use-api"
import { SizeDistributionChart } from "./charts/size-distribution-chart"
import { ScatterPlotChart, type ScatterDataPoint } from "./charts/scatter-plot-with-selection"
import { InteractiveScatterChart } from "./charts/interactive-scatter-chart"
import { ClusteredScatterChart } from "./charts/clustered-scatter-chart"
import { ScatterAxisSelector } from "./charts/scatter-axis-selector"
import { TheoryVsMeasuredChart } from "./charts/theory-vs-measured-chart"
import { DiameterVsSSCChart } from "./charts/diameter-vs-ssc-chart"
import { EventVsSizeChart } from "./charts/event-vs-size-chart"
import { FullAnalysisDashboard } from "./full-analysis-dashboard"
import { StatisticsCards } from "./statistics-cards"
import { ParticleSizeVisualization } from "./particle-size-visualization"
import { AnomalySummaryCard } from "./anomaly-summary-card"
import { AnomalyEventsTable, type AnomalyEvent } from "./anomaly-events-table"
import { IndividualFileSummary } from "./individual-file-summary"
import { GatedStatisticsPanel } from "./gated-statistics-panel"
import { useToast } from "@/hooks/use-toast"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { resolveFCSAxes } from "@/lib/fcs-axis-utils"
import { captureChartAsImage } from "@/components/dashboard/saved-images-gallery"
import { 
  exportAnomaliesToCSV, 
  exportScatterDataToCSV, 
  exportToParquet, 
  generateMarkdownReport, 
  downloadMarkdownReport,
  exportFCSToExcel,
  exportFCSToPDF,
  type FCSExportData
} from "@/lib/export-utils"

// Deterministic pseudo-random for SSR compatibility — defined outside component to avoid recreation
const seededRandom = (seed: number): number => {
  const x = Math.sin(seed * 9999) * 10000
  return x - Math.floor(x)
}

export function AnalysisResults() {
  const { 
    pinChart, 
    fcsAnalysis, 
    fcsAnalysisSettings,
    resetFCSAnalysis, 
    secondaryFcsAnalysis,
    overlayConfig,
    setSecondaryFCSScatterData,
    setSecondaryFCSLoadingScatter,
    setSecondaryFCSAnomalyData
  } = useAnalysisStore(useShallow((s) => ({
    pinChart: s.pinChart,
    fcsAnalysis: s.fcsAnalysis,
    fcsAnalysisSettings: s.fcsAnalysisSettings,
    resetFCSAnalysis: s.resetFCSAnalysis,
    secondaryFcsAnalysis: s.secondaryFcsAnalysis,
    overlayConfig: s.overlayConfig,
    setSecondaryFCSScatterData: s.setSecondaryFCSScatterData,
    setSecondaryFCSLoadingScatter: s.setSecondaryFCSLoadingScatter,
    setSecondaryFCSAnomalyData: s.setSecondaryFCSAnomalyData,
  })))
  const { getScatterData, getScatterDataWithAxes, getSizeBins, detectAnomalies } = useApi()
  const { toast } = useToast()
  const [showAnomalyDetails, setShowAnomalyDetails] = useState(false)
  const [highlightAnomalies, setHighlightAnomalies] = useState(true)
  const [scatterData, setScatterData] = useState<ScatterDataPoint[]>([])
  const [loadingScatter, setLoadingScatter] = useState(false)
  const [sizeCategories, setSizeCategories] = useState<{ small: number; medium: number; large: number } | null>(null)
  const [loadingSizeBins, setLoadingSizeBins] = useState(false)
  const [selectedIndices, setSelectedIndices] = useState<number[]>([])
  const [gateCoordinates, setGateCoordinates] = useState<{ x1: number; y1: number; x2: number; y2: number } | null>(null)
  
  // CRMIT-002: Auto Axis Selection state - initialize as empty, will be set from FCS results
  const [xChannel, setXChannel] = useState<string>("")
  const [yChannel, setYChannel] = useState<string>("")
  const [channelsInitialized, setChannelsInitialized] = useState(false)
  
  // UI-002: Clustered scatter view mode for large datasets
  const [scatterViewMode, setScatterViewMode] = useState<"standard" | "clustered">("standard")
  const [isPending, startTransition] = useTransition()
  
  // Non-blocking toggle handler — keeps UI responsive during mode switch
  const handleViewModeChange = useCallback((mode: "standard" | "clustered") => {
    startTransition(() => {
      setScatterViewMode(mode)
    })
  }, [])
  
  // Distribution analysis state
  const [distributionAnalysis, setDistributionAnalysis] = useState<import("@/lib/api-client").DistributionAnalysisResponse | null>(null)
  const [distributionLoading, setDistributionLoading] = useState(false)
  const [activeVisualizationTab, setActiveVisualizationTab] = useState("dashboard")
  const [avgFrameMs, setAvgFrameMs] = useState<number | null>(null)

  // Phase 4: Gain mismatch warnings from scatter-data response
  const [gainMismatchWarnings, setGainMismatchWarnings] = useState<string[]>([])

  // PERFORMANCE: Debounce Mie settings changes to avoid 3 simultaneous API calls on every slider tick
  const [debouncedMieSettings, setDebouncedMieSettings] = useState({
    wavelength: fcsAnalysisSettings?.laserWavelength,
    particleRI: fcsAnalysisSettings?.particleRI,
    mediumRI: fcsAnalysisSettings?.mediumRI,
  })
  const mieDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  
  useEffect(() => {
    if (mieDebounceRef.current) clearTimeout(mieDebounceRef.current)
    mieDebounceRef.current = setTimeout(() => {
      setDebouncedMieSettings({
        wavelength: fcsAnalysisSettings?.laserWavelength,
        particleRI: fcsAnalysisSettings?.particleRI,
        mediumRI: fcsAnalysisSettings?.mediumRI,
      })
    }, 500) // 500ms debounce — waits for user to stop adjusting
    return () => { if (mieDebounceRef.current) clearTimeout(mieDebounceRef.current) }
  }, [fcsAnalysisSettings?.laserWavelength, fcsAnalysisSettings?.particleRI, fcsAnalysisSettings?.mediumRI])

  // Use real results from the API
  const results = fcsAnalysis.results
  const anomalyData = fcsAnalysis.anomalyData
  const sampleId = fcsAnalysis.sampleId
  const fileName = fcsAnalysis.file?.name
  
  // Secondary file data for overlay
  const secondaryResults = secondaryFcsAnalysis.results
  const secondarySampleId = secondaryFcsAnalysis.sampleId
  const secondaryScatterData = secondaryFcsAnalysis.scatterData
  const secondaryAnomalyData = secondaryFcsAnalysis.anomalyData
  const isDevTelemetry = process.env.NODE_ENV === "development"

  const primaryAnomalyIndexSet = useMemo(
    () => new Set(anomalyData?.anomalous_indices ?? []),
    [anomalyData?.anomalous_indices]
  )

  const secondaryAnomalyIndexSet = useMemo(
    () => new Set(secondaryAnomalyData?.anomalous_indices ?? []),
    [secondaryAnomalyData?.anomalous_indices]
  )

  const primaryAxisResolution = useMemo(
    () => resolveFCSAxes({
      availableChannels: results?.channels || [],
      requestedX: xChannel || "FSC-A",
      requestedY: yChannel || "SSC-A",
    }),
    [results?.channels, xChannel, yChannel]
  )

  const secondaryAxisResolution = useMemo(
    () => resolveFCSAxes({
      availableChannels: secondaryResults?.channels || [],
      requestedX: primaryAxisResolution.resolvedX,
      requestedY: primaryAxisResolution.resolvedY,
    }),
    [secondaryResults?.channels, primaryAxisResolution.resolvedX, primaryAxisResolution.resolvedY]
  )

  // CRMIT-002: Handle axis change from selector
  const handleAxisChange = useCallback((newXChannel: string, newYChannel: string) => {
    setXChannel(newXChannel)
    setYChannel(newYChannel)
  }, [])

  // PERFORMANCE: Memoized callbacks to prevent child chart re-renders
  const handleSelectionChange = useCallback((indices: number[], coords?: { x1: number; y1: number; x2: number; y2: number }) => {
    setSelectedIndices(indices)
    setGateCoordinates(coords || null)
    if (indices.length > 0) {
      toast({
        title: "Population Gated",
        description: `${indices.length} events selected. Click "Analyze Selection" or "Save Gate" for further analysis.`,
      })
    }
  }, [toast])

  const handleGatedAnalysis = useCallback((selectedData: Array<{ x: number; y: number; diameter?: number }>) => {
    if (selectedData.length === 0) return
    const xValues = selectedData.map(p => p.x)
    const yValues = selectedData.map(p => p.y)
    const diameters = selectedData.filter(p => p.diameter).map(p => p.diameter!)
    
    const meanX = xValues.reduce((a, b) => a + b, 0) / xValues.length
    const meanY = yValues.reduce((a, b) => a + b, 0) / yValues.length
    const meanDiam = diameters.length > 0 
      ? diameters.reduce((a, b) => a + b, 0) / diameters.length 
      : null
    
    toast({
      title: `Gated Population Analysis (${selectedData.length} events)`,
      description: `Mean ${xChannel}: ${meanX.toFixed(1)}, Mean ${yChannel}: ${meanY.toFixed(1)}${meanDiam ? `, Mean Diameter: ${meanDiam.toFixed(1)} nm` : ''}`,
      duration: 8000,
    })
  }, [toast, xChannel, yChannel])

  const handleExportSelection = useCallback((indices: number[]) => {
    const selectedData = scatterData.filter((_, idx) => indices.includes(idx))
    const csv = [
      ["Index", xChannel, yChannel, "Diameter (nm)"],
      ...selectedData.map((p, idx) => [p.index ?? idx, p.x, p.y, p.diameter ?? "N/A"]),
    ]
      .map((row) => row.join(","))
      .join("\n")

    const blob = new Blob([csv], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `gated_population_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    toast({
      title: "Export Complete",
      description: `Exported ${indices.length} events to CSV`,
    })
  }, [scatterData, xChannel, yChannel, toast])

  // Stable empty array references to avoid re-renders
  const emptyAnomalyIndices = useMemo(() => [] as number[], [])

  // Initialize channel selection from FCS results when available
  useEffect(() => {
    if (results?.channels && results.channels.length > 0 && !channelsInitialized) {
      const resolved = resolveFCSAxes({
        availableChannels: results.channels,
        requestedX: "FSC-A",
        requestedY: "SSC-A",
      })

      setXChannel(resolved.resolvedX)
      setYChannel(resolved.resolvedY)
      setChannelsInitialized(true)
    }
  }, [results?.channels, channelsInitialized])

  useEffect(() => {
    if (!channelsInitialized || !results?.channels?.length) return

    if (xChannel !== primaryAxisResolution.resolvedX) {
      setXChannel(primaryAxisResolution.resolvedX)
    }
    if (yChannel !== primaryAxisResolution.resolvedY) {
      setYChannel(primaryAxisResolution.resolvedY)
    }
  }, [
    channelsInitialized,
    results?.channels,
    xChannel,
    yChannel,
    primaryAxisResolution.resolvedX,
    primaryAxisResolution.resolvedY,
  ])

  // Reset channel initialization when sample changes
  useEffect(() => {
    setChannelsInitialized(false)
  }, [sampleId])

  // Load real scatter data from backend - CRMIT-002: Updated to use custom axes
  // Also refreshes when Mie settings change (wavelength, RI, etc.)
  useEffect(() => {
    let cancelled = false
    // Only fetch if channels are set and sample exists
    if (sampleId && results && primaryAxisResolution.resolvedX && primaryAxisResolution.resolvedY) {
      setLoadingScatter(true)
      // Use getScatterDataWithAxes for custom channel selection
      getScatterDataWithAxes(sampleId, primaryAxisResolution.resolvedX, primaryAxisResolution.resolvedY, 2000)
        .then((data) => {
          if (!cancelled && data) {
            setScatterData(data.data)
            // Phase 4: Capture gain mismatch warnings from response
            if (data.warnings && data.warnings.length > 0) {
              setGainMismatchWarnings(data.warnings)
            } else {
              setGainMismatchWarnings([])
            }

          }
        })
        .finally(() => {
          if (!cancelled) setLoadingScatter(false)
        })
    }
    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    sampleId,
    results,
    primaryAxisResolution.resolvedX,
    primaryAxisResolution.resolvedY,
    debouncedMieSettings.wavelength,
    debouncedMieSettings.particleRI,
    debouncedMieSettings.mediumRI,
  ])
  
  // Load secondary scatter data when overlay is enabled
  // Uses fallback channels if primary channels don't exist in secondary file
  useEffect(() => {
    let cancelled = false
    if (overlayConfig.enabled && secondarySampleId && secondaryResults && primaryAxisResolution.resolvedX && primaryAxisResolution.resolvedY) {
      setSecondaryFCSLoadingScatter(true)

      getScatterDataWithAxes(
        secondarySampleId,
        secondaryAxisResolution.resolvedX,
        secondaryAxisResolution.resolvedY,
        2000
      )
        .then((data) => {
          if (!cancelled && data) {
            setSecondaryFCSScatterData(data.data)
          }
        })
        .catch((err) => {
          console.error("[AnalysisResults] Failed to load secondary scatter data:", err)
        })
        .finally(() => {
          if (!cancelled) setSecondaryFCSLoadingScatter(false)
        })
    }
    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    overlayConfig.enabled,
    secondarySampleId,
    secondaryResults,
    primaryAxisResolution.resolvedX,
    primaryAxisResolution.resolvedY,
    secondaryAxisResolution.resolvedX,
    secondaryAxisResolution.resolvedY,
  ])

  // Load secondary anomaly data when overlay is enabled
  useEffect(() => {
    let cancelled = false
    if (overlayConfig.enabled && secondarySampleId && secondaryResults && !secondaryFcsAnalysis.anomalyData) {
      detectAnomalies(secondarySampleId, { method: "zscore", zscore_threshold: 3.0 })
        .then((data) => {
          if (!cancelled && data) {
            setSecondaryFCSAnomalyData({
              method: data.method === "zscore" ? "Z-Score" : data.method === "iqr" ? "IQR" : "Both",
              total_anomalies: data.total_anomalies,
              anomaly_percentage: data.anomaly_percentage,
              anomalous_indices: data.anomalous_indices
            })
          }
        })
        .catch((err) => {
          console.error("Failed to load secondary anomaly data:", err)
        })
    }
    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [overlayConfig.enabled, secondarySampleId, secondaryResults])

  // Load distribution analysis (normality tests + distribution fitting)
  useEffect(() => {
    let cancelled = false
    if (sampleId && results) {
      setDistributionLoading(true)
      import("@/lib/api-client").then(({ apiClient }) => {
        apiClient.getDistributionAnalysis(sampleId, {
          wavelength_nm: debouncedMieSettings.wavelength,
          n_particle: debouncedMieSettings.particleRI,
          n_medium: debouncedMieSettings.mediumRI,
          include_overlays: true,
        })
          .then((data) => {
            if (!cancelled && data) {
              setDistributionAnalysis(data)
            }
          })
          .catch((err) => {
            console.warn("[AnalysisResults] Distribution analysis failed (non-critical):", err)
          })
          .finally(() => {
            if (!cancelled) setDistributionLoading(false)
          })
      })
    } else {
      setDistributionAnalysis(null)
    }
    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sampleId, results, debouncedMieSettings.wavelength, debouncedMieSettings.particleRI, debouncedMieSettings.mediumRI])

  // Load real size bins from backend - PERFORMANCE FIX: Removed callback AND sizeRanges from deps
  // sizeRanges is an array reference that changes on every Zustand notify → caused infinite API loop
  useEffect(() => {
    let cancelled = false
    if (sampleId && results) {
      setLoadingSizeBins(true)
      getSizeBins(sampleId)
        .then((data) => {
          if (!cancelled && data) {
            setSizeCategories(data.bins)
          }
        })
        .finally(() => {
          if (!cancelled) setLoadingSizeBins(false)
        })
    }
    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sampleId, results, debouncedMieSettings.wavelength, debouncedMieSettings.particleRI, debouncedMieSettings.mediumRI])

  if (!results) {
    return (
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>No Results</AlertTitle>
        <AlertDescription>
          Analysis results are not available. This might indicate a parsing error.
        </AlertDescription>
      </Alert>
    )
  }

  const totalEvents = results.total_events || results.event_count || 0
  const medianSize = results.particle_size_median_nm

  // PERFORMANCE FIX: Memoize derived data arrays to prevent cascading re-renders.
  // Previously, .filter().map() chains in JSX created new array references every render,
  // forcing all chart children to fully re-render.
  const scatterDiameters = useMemo(() => 
    scatterData.filter(p => p.diameter !== undefined && p.diameter > 0).map(p => p.diameter as number),
    [scatterData]
  )

  const theoryMeasuredData = useMemo(() => {
    if (scatterData.length === 0) return undefined
    const valid = scatterData.filter((p) => p.diameter && p.diameter > 0 && p.y > 0)
    const maxPoints = 1800
    const step = valid.length > maxPoints ? Math.ceil(valid.length / maxPoints) : 1
    return valid.filter((_, i) => i % step === 0).map((p) => ({ diameter: p.diameter as number, intensity: p.y }))
  }, [scatterData])

  const secondaryTheoryData = useMemo(() => {
    if (!secondaryScatterData || secondaryScatterData.length === 0) return undefined
    const valid = secondaryScatterData.filter((p) => p.diameter && p.diameter > 0 && p.y > 0)
    const maxPoints = 1800
    const step = valid.length > maxPoints ? Math.ceil(valid.length / maxPoints) : 1
    return valid.filter((_, i) => i % step === 0).map((p) => ({ diameter: p.diameter as number, intensity: p.y }))
  }, [secondaryScatterData])

  const secondarySizeData = useMemo(() =>
    secondaryScatterData?.filter(p => p.diameter).map(p => p.diameter as number),
    [secondaryScatterData]
  )

  const diameterVsSSCData = useMemo(() =>
    scatterData
      .filter(p => p.diameter !== undefined && p.y !== undefined)
      .map(p => ({
        diameter: p.diameter as number,
        ssc: p.y,
        index: p.index,
        isAnomaly: primaryAnomalyIndexSet.has(p.index ?? -1),
      })),
    [scatterData, primaryAnomalyIndexSet]
  )

  const secondaryDiameterVsSSCData = useMemo(() =>
    secondaryScatterData
      ?.filter(p => p.diameter !== undefined && p.y !== undefined)
      .map(p => ({
        diameter: p.diameter as number,
        ssc: p.y,
        index: p.index,
        isAnomaly: secondaryAnomalyIndexSet.has(p.index ?? -1),
      })),
    [secondaryScatterData, secondaryAnomalyIndexSet]
  )

  const estimatedRenderedPoints = useMemo(() => {
    const INTERACTIVE_SCATTER_MAX_POINTS = 1200
    const DIAMETER_MAX_POINTS = 1500
    const THEORY_MAX_POINTS_PER_SERIES = 1800
    const EVENT_MAX_POINTS = 2500

    switch (activeVisualizationTab) {
      case "fsc-ssc":
        return Math.min(scatterData.length, INTERACTIVE_SCATTER_MAX_POINTS)
      case "diameter": {
        const primary = Math.min(diameterVsSSCData.length, DIAMETER_MAX_POINTS)
        const secondary = secondaryDiameterVsSSCData ? Math.min(secondaryDiameterVsSSCData.length, DIAMETER_MAX_POINTS) : 0
        return primary + secondary
      }
      case "theory": {
        const primary = Math.min(theoryMeasuredData?.length ?? 0, THEORY_MAX_POINTS_PER_SERIES)
        const secondary = Math.min(secondaryTheoryData?.length ?? 0, THEORY_MAX_POINTS_PER_SERIES)
        return primary + secondary
      }
      case "event-size":
        return Math.min(scatterData.length, EVENT_MAX_POINTS)
      case "distribution":
        return Math.max(25, Math.min(scatterDiameters.length, 2500))
      default:
        return Math.min(scatterData.length, INTERACTIVE_SCATTER_MAX_POINTS) + Math.max(25, Math.min(scatterDiameters.length, 1000))
    }
  }, [
    activeVisualizationTab,
    scatterData.length,
    diameterVsSSCData.length,
    secondaryDiameterVsSSCData,
    theoryMeasuredData,
    secondaryTheoryData,
    scatterDiameters.length,
  ])

  useEffect(() => {
    if (!isDevTelemetry) return

    let rafId = 0
    let lastTs = 0
    const samples: number[] = []

    const tick = (ts: number) => {
      if (lastTs > 0) {
        samples.push(ts - lastTs)
        if (samples.length > 60) {
          samples.shift()
        }
        if (samples.length >= 30) {
          const avg = samples.reduce((sum, ms) => sum + ms, 0) / samples.length
          setAvgFrameMs(avg)
        }
      }
      lastTs = ts
      rafId = window.requestAnimationFrame(tick)
    }

    rafId = window.requestAnimationFrame(tick)
    return () => window.cancelAnimationFrame(rafId)
  }, [isDevTelemetry, activeVisualizationTab])

  const frameBudgetHint = useMemo(() => {
    if (avgFrameMs === null) return "profiling"
    if (avgFrameMs <= 16.7) return "within budget"
    if (avgFrameMs <= 24) return "watch"
    return "over budget"
  }, [avgFrameMs])

  // Generate mock anomaly events for table (TODO: Replace with real data)
  const anomalyEvents: AnomalyEvent[] = useMemo(() => {
    if (!anomalyData || !anomalyData.anomalous_indices) return []
    
    return anomalyData.anomalous_indices.slice(0, 100).map((index, i) => ({
      index,
      fsc: seededRandom(i * 6) * 1000 + 100,
      ssc: seededRandom(i * 6 + 1) * 800 + 50,
      zscore_fsc: (seededRandom(i * 6 + 2) - 0.5) * 8,
      zscore_ssc: (seededRandom(i * 6 + 3) - 0.5) * 8,
      iqr_outlier_fsc: seededRandom(i * 6 + 4) > 0.5,
      iqr_outlier_ssc: seededRandom(i * 6 + 5) > 0.5,
    }))
  }, [anomalyData])

  const chartCaptureKeyByTitle: Record<string, string> = {
    "Size Distribution": "distribution",
    "Theory vs Measured": "theory",
    "FSC vs SSC": "fsc-ssc",
    "Diameter vs SSC": "diameter",
    "Event vs Size": "event-size",
  }

  const buildPinContext = (
    chartTitle: string,
    chartType: "histogram" | "scatter" | "line",
    data: Array<{ x: number; y: number; label?: string }>
  ) => {
    const xVals = data.map((d) => d.x).filter((v) => Number.isFinite(v))
    const yVals = data.map((d) => d.y).filter((v) => Number.isFinite(v))
    const xMin = xVals.length > 0 ? Math.min(...xVals) : null
    const xMax = xVals.length > 0 ? Math.max(...xVals) : null
    const yMin = yVals.length > 0 ? Math.min(...yVals) : null
    const yMax = yVals.length > 0 ? Math.max(...yVals) : null
    const fmt = (v: number | null) => (v == null ? "N/A" : Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 }))

    const lines = [
      `Chart: ${chartTitle}`,
      `Type: ${chartType}`,
      `Sample: ${sampleId || "Unknown"}`,
      `Point Count: ${data.length.toLocaleString()}`,
      `X Range: ${fmt(xMin)} to ${fmt(xMax)}`,
      `Y Range: ${fmt(yMin)} to ${fmt(yMax)}`,
      `Overlay Active: ${overlayConfig.enabled && secondaryResults ? "Yes" : "No"}`,
      `Primary Axes: ${xChannel || "FSC"} vs ${yChannel || "SSC"}`,
      `Total Events: ${(results?.total_events || results?.event_count || 0).toLocaleString()}`,
    ]

    if (results?.particle_size_median_nm != null) {
      lines.push(`Median Particle Size: ${results.particle_size_median_nm.toFixed(2)} nm`)
    }

    if (anomalyData?.total_anomalies != null) {
      lines.push(`Anomalies: ${anomalyData.total_anomalies.toLocaleString()} (${anomalyData.anomaly_percentage.toFixed(2)}%)`)
    }

    return lines.join("\n")
  }

  const handlePin = async (chartTitle: string, chartType: "histogram" | "scatter" | "line") => {
    if (loadingScatter && scatterData.length === 0) {
      toast({
        title: "Data Still Loading",
        description: "Please wait for the analysis data to finish loading before pinning.",
        variant: "destructive",
      })
      return
    }

    let pinData: Array<{ x: number; y: number; label?: string }> = []
    let pinConfig: { xAxisLabel?: string; yAxisLabel?: string; color?: string } = {}

    switch (chartTitle) {
      case "Size Distribution": {
        if (scatterDiameters.length > 0) {
          const binCount = 25
          const maxSize = Math.min(1000, Math.max(...scatterDiameters) * 1.1)
          const binWidth = maxSize / binCount
          pinData = Array.from({ length: binCount }, (_, i) => {
            const binStart = i * binWidth
            const binEnd = (i + 1) * binWidth
            const count = scatterDiameters.filter(s => s >= binStart && s < binEnd).length
            return { x: Math.round(binStart + binWidth / 2), y: count }
          })
        } else if (scatterData.length > 0) {
          // Fallback: use SSC (y) values as size proxy when diameter not computed
          const yValues = scatterData.map(p => p.y).filter(v => v > 0)
          if (yValues.length > 0) {
            const binCount = 25
            const maxVal = Math.max(...yValues) * 1.1
            const binWidth = maxVal / binCount
            pinData = Array.from({ length: binCount }, (_, i) => {
              const binStart = i * binWidth
              const binEnd = (i + 1) * binWidth
              const count = yValues.filter(v => v >= binStart && v < binEnd).length
              return { x: Math.round(binStart + binWidth / 2), y: count }
            })
          }
        }
        pinConfig = { xAxisLabel: scatterDiameters.length > 0 ? "Diameter (nm)" : "Intensity", yAxisLabel: "Count", color: "#8b5cf6" }
        break
      }
      case "Theory vs Measured": {
        if (theoryMeasuredData && theoryMeasuredData.length > 0) {
          const step = Math.max(1, Math.floor(theoryMeasuredData.length / 300))
          pinData = theoryMeasuredData
            .filter((_, i) => i % step === 0)
            .map(p => ({ x: p.diameter, y: p.intensity }))
        } else if (scatterData.length > 0) {
          // Fallback: use raw scatter x vs y
          const step = Math.max(1, Math.floor(scatterData.length / 300))
          pinData = scatterData
            .filter((_, i) => i % step === 0)
            .map(p => ({ x: p.x, y: p.y }))
        }
        pinConfig = { xAxisLabel: theoryMeasuredData && theoryMeasuredData.length > 0 ? "Diameter (nm)" : xChannel, yAxisLabel: "Intensity", color: "#10b981" }
        break
      }
      case "Diameter vs SSC": {
        if (diameterVsSSCData.length > 0) {
          const step = Math.max(1, Math.floor(diameterVsSSCData.length / 500))
          pinData = diameterVsSSCData
            .filter((_, i) => i % step === 0)
            .map(p => ({ x: p.diameter, y: p.ssc }))
        } else if (scatterData.length > 0) {
          // Fallback: use raw scatter x vs y
          const step = Math.max(1, Math.floor(scatterData.length / 500))
          pinData = scatterData
            .filter((_, i) => i % step === 0)
            .map(p => ({ x: p.x, y: p.y }))
        }
        pinConfig = { xAxisLabel: diameterVsSSCData.length > 0 ? "Diameter (nm)" : xChannel, yAxisLabel: "SSC", color: "#f59e0b" }
        break
      }
      case "FSC vs SSC": {
        if (scatterData.length > 0) {
          const step = Math.max(1, Math.floor(scatterData.length / 500))
          pinData = scatterData
            .filter((_, i) => i % step === 0)
            .map(p => ({ x: p.x, y: p.y }))
        }
        pinConfig = { xAxisLabel: xChannel || "FSC", yAxisLabel: yChannel || "SSC", color: "#3b82f6" }
        break
      }
      case "Event vs Size": {
        if (scatterData.length > 0) {
          // Use diameter if available, otherwise fall back to y (SSC) values
          const hasAnyDiameter = scatterData.some(p => p.diameter && p.diameter > 0)
          if (hasAnyDiameter) {
            const validEvents = scatterData.filter(p => p.diameter && p.diameter > 0)
            const step = Math.max(1, Math.floor(validEvents.length / 500))
            pinData = validEvents
              .filter((_, i) => i % step === 0)
              .map((p, i) => ({ x: i, y: p.diameter as number }))
          } else {
            const step = Math.max(1, Math.floor(scatterData.length / 500))
            pinData = scatterData
              .filter((_, i) => i % step === 0)
              .map((p, i) => ({ x: i, y: p.y }))
          }
        }
        pinConfig = { xAxisLabel: "Event #", yAxisLabel: scatterData.some(p => p.diameter && p.diameter > 0) ? "Size (nm)" : yChannel || "SSC", color: "#3b82f6" }
        break
      }
    }

    if (pinData.length === 0) {
      toast({
        title: "No Data to Pin",
        description: `${chartTitle} has no data available to pin. Please ensure analysis is complete.`,
        variant: "destructive",
      })
      return
    }

    let snapshotDataUrl: string | undefined
    let snapshotThumbnailUrl: string | undefined
    const captureKey = chartCaptureKeyByTitle[chartTitle]
    const chartElement = captureKey
      ? document.querySelector(`[data-pin-chart="${captureKey}"]`) as HTMLElement | null
      : null

    if (chartElement) {
      const captured = await captureChartAsImage(chartElement, chartTitle, "Flow Cytometry", chartType)
      if (captured) {
        snapshotDataUrl = captured.dataUrl
        snapshotThumbnailUrl = captured.thumbnailUrl
      }
    }

    const chartContext = buildPinContext(chartTitle, chartType, pinData)

    pinChart({
      id: crypto.randomUUID(),
      title: chartTitle,
      source: "Flow Cytometry",
      timestamp: new Date(),
      type: chartType,
      data: pinData,
      config: pinConfig,
      snapshotDataUrl,
      snapshotThumbnailUrl,
      chartContext,
      sourceData: {
        fcsResults: results || undefined,
      },
    })
    toast({
      title: "Pinned to Dashboard",
      description: `${chartTitle} has been pinned.`,
    })
  }

  const handleReset = () => {
    resetFCSAnalysis()
    toast({
      title: "Tab Reset",
      description: "FCS analysis cleared. Upload a new file to analyze.",
    })
  }

  const handleExport = async (format: string) => {
    if (format === "anomalies" && anomalyData && sampleId) {
      exportAnomaliesToCSV(anomalyEvents, anomalyData, sampleId)
      toast({
        title: "✅ Export Complete",
        description: `Anomaly data exported successfully`,
      })
      return
    }

    if (format === "scatter" && sampleId) {
      exportScatterDataToCSV(scatterData, sampleId)
      toast({
        title: "✅ Export Complete",
        description: `Scatter plot data exported successfully`,
      })
      return
    }

    if (format === "parquet" && sampleId) {
      toast({
        title: "Exporting...",
        description: "Preparing Parquet export...",
      })
      
      const success = await exportToParquet(sampleId, "fcs", {
        includeMetadata: true,
        includeStatistics: true,
        onSuccess: (filename) => {
          toast({
            title: "✅ Export Complete",
            description: `${filename} downloaded successfully`,
          })
        },
        onError: (error) => {
          toast({
            title: "Export Failed",
            description: error,
            variant: "destructive",
          })
        },
      })
      return
    }

    // NEW: Excel Export (P-002)
    if (format === "excel" && sampleId && results) {
      try {
        const exportData: FCSExportData = {
          sampleId,
          fileName: fileName || undefined,
          results: {
            total_events: results.total_events,
            gated_events: results.gated_events,
            fsc_mean: results.fsc_mean,
            fsc_median: results.fsc_median,
            ssc_mean: results.ssc_mean,
            ssc_median: results.ssc_median,
            particle_size_median_nm: results.particle_size_median_nm,
            particle_size_mean_nm: results.particle_size_mean_nm,
            size_statistics: results.size_statistics,
            fsc_cv_pct: results.fsc_cv_pct,
            ssc_cv_pct: results.ssc_cv_pct,
            debris_pct: results.debris_pct,
            noise_events_removed: results.noise_events_removed,
            channels: results.channels,
          },
          scatterData: scatterData,
          sizeDistribution: results.size_distribution?.histogram?.map((h: any) => ({ size: h.bin_center, count: h.count })),
          anomalyData: anomalyData || undefined,
          experimentalConditions: fcsAnalysis.experimentalConditions || undefined,
        }
        
        exportFCSToExcel(exportData)
        
        toast({
          title: "✅ Excel Export Complete",
          description: `${sampleId}_FCS_Report.xlsx downloaded successfully`,
        })
      } catch (error) {
        toast({
          title: "Export Failed",
          description: error instanceof Error ? error.message : "Failed to export Excel file",
          variant: "destructive",
        })
      }
      return
    }

    // NEW: PDF Export (P-003)
    if (format === "pdf" && sampleId && results) {
      try {
        toast({
          title: "Generating PDF...",
          description: "Please wait while we create your report",
        })
        
        const exportData: FCSExportData = {
          sampleId,
          fileName: fileName || undefined,
          results: {
            total_events: results.total_events,
            gated_events: results.gated_events,
            fsc_mean: results.fsc_mean,
            fsc_median: results.fsc_median,
            ssc_mean: results.ssc_mean,
            ssc_median: results.ssc_median,
            particle_size_median_nm: results.particle_size_median_nm,
            particle_size_mean_nm: results.particle_size_mean_nm,
            size_statistics: results.size_statistics,
            fsc_cv_pct: results.fsc_cv_pct,
            ssc_cv_pct: results.ssc_cv_pct,
            debris_pct: results.debris_pct,
            noise_events_removed: results.noise_events_removed,
          },
          anomalyData: anomalyData || undefined,
          experimentalConditions: fcsAnalysis.experimentalConditions || undefined,
        }
        
        await exportFCSToPDF(exportData)
        
        toast({
          title: "✅ PDF Export Complete",
          description: `${sampleId}_FCS_Report.pdf downloaded successfully`,
        })
      } catch (error) {
        toast({
          title: "Export Failed",
          description: error instanceof Error ? error.message : "Failed to export PDF file",
          variant: "destructive",
        })
      }
      return
    }

    if (format === "markdown" && sampleId && results) {
      const reportContent = generateMarkdownReport({
        title: `FCS Analysis Report - ${sampleId}`,
        sampleId,
        analysisType: "FCS",
        timestamp: new Date(),
        results: {
          total_events: results.total_events,
          gated_events: results.gated_events,
          fsc_median: results.fsc_median,
          fsc_mean: results.fsc_mean,
          ssc_median: results.ssc_median,
          ssc_mean: results.ssc_mean,
          particle_size_median_nm: results.particle_size_median_nm,
          particle_size_mean_nm: results.particle_size_mean_nm,
        },
        statistics: {
          fsc_cv_percent: results.fsc_cv_pct || 0,
          ssc_cv_percent: results.ssc_cv_pct || 0,
          noise_events_removed: results.noise_events_removed || 0,
        },
        charts: [
          { title: "Size Distribution", description: "Particle diameter histogram" },
          { title: "FSC vs SSC Scatter", description: "Forward vs Side scatter density plot" },
          { title: "Theory vs Measured", description: "Mie theory prediction comparison" },
        ],
      })
      
      downloadMarkdownReport(
        reportContent,
        `${sampleId}_fcs_report_${new Date().toISOString().split('T')[0]}.md`
      )
      
      toast({
        title: "✅ Report Generated",
        description: "Markdown report downloaded successfully",
      })
      return
    }

    // CSV Export
    if (format === "csv" && sampleId && results) {
      const csvContent = [
        "# FCS Analysis Export",
        `# Sample ID: ${sampleId}`,
        `# Export Date: ${new Date().toISOString()}`,
        "#",
        "Parameter,Value",
        `Total Events,${results.total_events || 'N/A'}`,
        `Gated Events,${results.gated_events || 'N/A'}`,
        `FSC Mean,${results.fsc_mean?.toFixed(2) || 'N/A'}`,
        `FSC Median,${results.fsc_median?.toFixed(2) || 'N/A'}`,
        `SSC Mean,${results.ssc_mean?.toFixed(2) || 'N/A'}`,
        `SSC Median,${results.ssc_median?.toFixed(2) || 'N/A'}`,
        `Particle Size Median (nm),${results.particle_size_median_nm?.toFixed(2) || 'N/A'}`,
        `Particle Size Mean (nm),${results.particle_size_mean_nm?.toFixed(2) || 'N/A'}`,
        `D10 (nm),${results.size_statistics?.d10?.toFixed(2) || 'N/A'}`,
        `D50 (nm),${results.size_statistics?.d50?.toFixed(2) || 'N/A'}`,
        `D90 (nm),${results.size_statistics?.d90?.toFixed(2) || 'N/A'}`,
      ].join('\n')
      
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${sampleId}_fcs_summary.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      
      toast({
        title: "✅ Export Complete",
        description: "CSV file downloaded successfully",
      })
      return
    }

    // JSON Export
    if (format === "json" && sampleId && results) {
      const jsonContent = JSON.stringify({
        sample_id: sampleId,
        export_timestamp: new Date().toISOString(),
        analysis_type: "FCS",
        results: {
          total_events: results.total_events,
          gated_events: results.gated_events,
          fsc_statistics: {
            mean: results.fsc_mean,
            median: results.fsc_median,
            cv_pct: results.fsc_cv_pct,
          },
          ssc_statistics: {
            mean: results.ssc_mean,
            median: results.ssc_median,
            cv_pct: results.ssc_cv_pct,
          },
          particle_size: {
            median_nm: results.particle_size_median_nm,
            mean_nm: results.particle_size_mean_nm,
            d10: results.size_statistics?.d10,
            d50: results.size_statistics?.d50,
            d90: results.size_statistics?.d90,
          },
          debris_pct: results.debris_pct,
          channels: results.channels,
        },
        experimental_conditions: fcsAnalysis.experimentalConditions,
      }, null, 2)
      
      const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${sampleId}_fcs_results.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      
      toast({
        title: "✅ Export Complete",
        description: "JSON file downloaded successfully",
      })
      return
    }

    toast({
      title: "Export Not Available",
      description: `${format.toUpperCase()} export is not implemented yet`,
      variant: "destructive",
    })
  }

  return (
    <div className="space-y-4 md:space-y-6">
      {/* Header with Sample Info */}
      <Card className="card-3d">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="space-y-1">
              <h3 className="text-lg font-semibold">FCS Analysis Results</h3>
              <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                {sampleId && (
                  <>
                    <span className="font-medium text-foreground">{sampleId}</span>
                    <span>•</span>
                  </>
                )}
                {fileName && <span>{fileName}</span>}
                {results.processed_at && (
                  <>
                    <span>•</span>
                    <span>{new Date(results.processed_at).toLocaleString()}</span>
                  </>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="bg-emerald/20 text-emerald border-emerald/50">
                Analysis Complete
              </Badge>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handleReset}
                className="gap-2"
              >
                <RotateCcw className="h-4 w-4" />
                Reset Tab
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Statistics Cards */}
      <StatisticsCards results={results} />

      {/* Individual File Summary - shown when comparing two files */}
      {secondaryResults && (
        <IndividualFileSummary
          primaryFile={{
            fileName: fileName,
            sampleId: sampleId ?? undefined,
            results: results,
          }}
          secondaryFile={{
            fileName: secondaryFcsAnalysis.file?.name,
            sampleId: secondarySampleId ?? undefined,
            results: secondaryResults,
          }}
        />
      )}

      {/* Particle Size Visualization with Real Data */}
      {(loadingSizeBins || loadingScatter) ? (
        <Card className="card-3d">
          <CardContent className="p-8 flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-primary mr-3" />
            <span className="text-muted-foreground">{loadingScatter ? 'Loading scatter data...' : 'Calculating size distribution...'}</span>
          </CardContent>
        </Card>
      ) : scatterData.length > 0 ? (
        <ParticleSizeVisualization
          totalEvents={totalEvents}
          medianSize={medianSize}
          scatterData={scatterData}
        />
      ) : null}

      {/* NOTE: SizeCategoryBreakdown and CustomSizeRanges removed — 
           ParticleSizeVisualization above already shows the same size breakdown 
           with donut chart + per-category detail. Having 3 sections was redundant. */}

      {/* Anomaly Detection Summary - show if anomaly data exists */}
      {anomalyData && (
        <AnomalySummaryCard
          anomalyData={anomalyData}
          totalEvents={totalEvents}
          onExportAnomalies={() => handleExport("anomalies")}
          onViewDetails={() => setShowAnomalyDetails(!showAnomalyDetails)}
        />
      )}

      {/* Visualization Tabs */}
      <Card className="card-3d">
        <CardHeader className="pb-2">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <CardTitle className="text-base md:text-lg">Analysis Visualizations</CardTitle>
            <div className="flex items-center gap-2 flex-wrap">
              {isDevTelemetry && (
                <Badge
                  variant="outline"
                  className="text-[11px] bg-slate-500/10 border-slate-500/30 text-slate-700 dark:text-slate-300"
                  title="Development-only telemetry for render/regression tracking"
                >
                  Dev Telemetry: ~{estimatedRenderedPoints.toLocaleString()} pts • {avgFrameMs ? `${avgFrameMs.toFixed(1)}ms` : "--.-ms"} • {frameBudgetHint}
                </Badge>
              )}
              <Button 
                variant="outline" 
                size="sm" 
                className="w-fit bg-transparent"
                onClick={() => handleExport("all")}
              >
                <Download className="h-4 w-4 mr-1" />
                Export All Charts
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Tabs value={activeVisualizationTab} onValueChange={setActiveVisualizationTab} className="space-y-4">
            <div className="relative">
              <TabsList className="bg-secondary/50 w-full justify-start overflow-x-auto flex-nowrap scrollbar-thin scrollbar-thumb-primary/50 pb-1 flex gap-1">
                <TabsTrigger value="dashboard" className="shrink-0 text-xs sm:text-sm">
                  Full Dashboard
                </TabsTrigger>
                <TabsTrigger value="event-size" className="shrink-0 text-xs sm:text-sm bg-blue-500/20 border border-blue-500/50 rounded-md">
                  📊 Event vs Size
                </TabsTrigger>
                <TabsTrigger value="distribution" className="shrink-0 text-xs sm:text-sm">
                  Size Distribution
                </TabsTrigger>
                <TabsTrigger value="theory" className="shrink-0 text-xs sm:text-sm">
                  Theory vs Measured
                </TabsTrigger>
                <TabsTrigger value="fsc-ssc" className="shrink-0 text-xs sm:text-sm">
                  FSC vs SSC
                </TabsTrigger>
                <TabsTrigger value="diameter" className="shrink-0 text-xs sm:text-sm">
                  Diameter vs SSC
                </TabsTrigger>
              </TabsList>
              <div className="absolute right-0 top-0 h-full w-8 bg-linear-to-l from-background to-transparent pointer-events-none" />
            </div>

            <TabsContent value="dashboard" className="space-y-4">
              {activeVisualizationTab === "dashboard" && (
                <>
              {/* Phase 4: Gain Mismatch Warning Banner (B3) */}
              {gainMismatchWarnings.length > 0 && (
                <Alert className="border-amber-300 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800">
                  <AlertCircle className="h-4 w-4 text-amber-500" />
                  <AlertTitle className="text-sm font-semibold text-amber-700 dark:text-amber-400">Detector Gain Mismatch</AlertTitle>
                  <AlertDescription className="text-xs text-amber-600 dark:text-amber-300 space-y-0.5">
                    {gainMismatchWarnings.map((w, i) => (
                      <div key={i}>{w}</div>
                    ))}
                  </AlertDescription>
                </Alert>
              )}
              {primaryAxisResolution.usedFallback && (
                <Alert className="border-amber-300 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800">
                  <AlertCircle className="h-4 w-4 text-amber-500" />
                  <AlertTitle className="text-sm font-semibold text-amber-700 dark:text-amber-400">Axis fallback applied</AlertTitle>
                  <AlertDescription className="text-xs text-amber-600 dark:text-amber-300">
                    Using {primaryAxisResolution.resolvedX} vs {primaryAxisResolution.resolvedY} for this file.
                  </AlertDescription>
                </Alert>
              )}
              {overlayConfig.enabled && secondaryResults && secondaryAxisResolution.usedFallback && (
                <Alert className="border-amber-300 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800">
                  <AlertCircle className="h-4 w-4 text-amber-500" />
                  <AlertTitle className="text-sm font-semibold text-amber-700 dark:text-amber-400">Comparison axis fallback applied</AlertTitle>
                  <AlertDescription className="text-xs text-amber-600 dark:text-amber-300">
                    Comparison file uses {secondaryAxisResolution.resolvedX} vs {secondaryAxisResolution.resolvedY}.
                  </AlertDescription>
                </Alert>
              )}
              {/* Axis Selection for Dashboard - allows changing scatter plot axes */}
              {sampleId && (
                <ScatterAxisSelector
                  sampleId={sampleId}
                  xChannel={xChannel}
                  yChannel={yChannel}
                  onAxisChange={handleAxisChange}
                  disabled={loadingScatter}
                  availableChannels={results?.channels || []}
                />
              )}
              <FullAnalysisDashboard
                results={results}
                scatterData={scatterData}
                anomalyData={anomalyData}
                sampleId={sampleId || undefined}
                xChannel={xChannel}
                yChannel={yChannel}
                secondaryResults={secondaryResults}
                secondaryScatterData={secondaryScatterData}
                secondaryAnomalyData={secondaryAnomalyData}
                secondarySizeData={secondarySizeData}
              />
                </>
              )}
            </TabsContent>

            <TabsContent value="distribution" className="space-y-4">
              {activeVisualizationTab === "distribution" && (
                <>
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge variant="outline" className="bg-cyan/20 text-cyan border-cyan/50">
                    Small EVs
                  </Badge>
                  <Badge variant="outline" className="bg-purple/20 text-purple border-purple/50">
                    Exosomes
                  </Badge>
                  <Badge variant="outline" className="bg-amber/20 text-amber border-amber/50">
                    Large EVs
                  </Badge>
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Maximize2 className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => handlePin("Size Distribution", "histogram")}
                  >
                    <Pin className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div data-pin-chart="distribution">
                <SizeDistributionChart 
                  sizeData={scatterDiameters}
                  secondarySizeData={secondarySizeData}
                  d10={results.size_statistics?.d10}
                  d50={results.size_statistics?.d50}
                  d90={results.size_statistics?.d90}
                  secondaryD10={secondaryResults?.size_statistics?.d10}
                  secondaryD50={secondaryResults?.size_statistics?.d50}
                  secondaryD90={secondaryResults?.size_statistics?.d90}
                  distributionAnalysis={distributionAnalysis}
                  distributionLoading={distributionLoading}
                />
              </div>
                </>
              )}
            </TabsContent>

            <TabsContent value="theory" className="space-y-4">
              {activeVisualizationTab === "theory" && (
                <>
              <div className="flex items-center justify-end gap-1">
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <Maximize2 className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => handlePin("Theory vs Measured", "line")}
                >
                  <Pin className="h-4 w-4" />
                </Button>
              </div>
              <div data-pin-chart="theory">
                <TheoryVsMeasuredChart 
                  primaryMeasuredData={theoryMeasuredData}
                  secondaryMeasuredData={secondaryTheoryData}
                />
              </div>
                </>
              )}
            </TabsContent>

            <TabsContent value="fsc-ssc" className="space-y-4">
              {activeVisualizationTab === "fsc-ssc" && (
                <>
              {/* View Mode Toggle + Axis Selection */}
              <div className="flex items-center justify-between gap-4 flex-wrap">
                {/* CRMIT-002: Auto Axis Selection */}
                {sampleId && (
                  <ScatterAxisSelector
                    sampleId={sampleId}
                    xChannel={xChannel}
                    yChannel={yChannel}
                    onAxisChange={handleAxisChange}
                    disabled={loadingScatter}
                    availableChannels={results?.channels || []}
                  />
                )}
                
                {/* UI-002: View Mode Toggle */}
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => handlePin("FSC vs SSC", "scatter")}
                    title="Pin to Dashboard"
                  >
                    <Pin className="h-4 w-4" />
                  </Button>
                  <span className="text-xs text-muted-foreground">View:</span>
                  <div className="flex rounded-md border">
                    <Button
                      variant={scatterViewMode === "standard" ? "secondary" : "ghost"}
                      size="sm"
                      className="h-8 rounded-r-none gap-1.5"
                      disabled={isPending}
                      onClick={() => handleViewModeChange("standard")}
                    >
                      <Grid3X3 className="h-3.5 w-3.5" />
                      Standard
                    </Button>
                    <Button
                      variant={scatterViewMode === "clustered" ? "secondary" : "ghost"}
                      size="sm"
                      className="h-8 rounded-l-none gap-1.5"
                      disabled={isPending}
                      onClick={() => handleViewModeChange("clustered")}
                    >
                      <Layers className="h-3.5 w-3.5" />
                      Clustered
                    </Button>
                  </div>
                  {isPending && (
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  )}
                  {scatterViewMode === "clustered" && (
                    <Badge variant="outline" className="text-xs">
                      Large Dataset Mode
                    </Badge>
                  )}
                </div>
              </div>
              
              <div data-pin-chart="fsc-ssc">
                {loadingScatter ? (
                  <div className="flex items-center justify-center h-[400px]">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    <span className="ml-3 text-muted-foreground">Loading scatter data...</span>
                  </div>
                ) : scatterViewMode === "clustered" && sampleId ? (
                  // UI-002: Clustered scatter view for large datasets
                  <ClusteredScatterChart
                    sampleId={sampleId}
                    title={`${xChannel} vs ${yChannel} (Clustered)`}
                    xLabel={xChannel}
                    yLabel={yChannel}
                    xChannel={xChannel}
                    yChannel={yChannel}
                    height={500}
                    onClusterClick={(cluster) => {
                      toast({
                        title: `Cluster ${cluster.id + 1}`,
                        description: `${cluster.count.toLocaleString()} events (${cluster.pct}%)${cluster.avg_diameter ? `, Avg diameter: ${cluster.avg_diameter.toFixed(1)} nm` : ''}`,
                      })
                    }}
                  />
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                    <div className="lg:col-span-3">
                      {/* Standard: Interactive SVG-based scatter chart with reliable selection */}
                      <InteractiveScatterChart
                        title={`${xChannel} vs ${yChannel}`}
                        xLabel={xChannel}
                        yLabel={yChannel}
                        data={scatterData}
                        anomalousIndices={anomalyData?.anomalous_indices ?? emptyAnomalyIndices}
                        highlightAnomalies={highlightAnomalies}
                        height={450}
                        onSelectionChange={handleSelectionChange}
                        onGatedAnalysis={handleGatedAnalysis}
                      />
                    </div>
                    <div className="lg:col-span-1">
                      <GatedStatisticsPanel
                        scatterData={scatterData}
                        xLabel={xChannel}
                        yLabel={yChannel}
                        selectedIndices={selectedIndices}
                        sampleId={sampleId}
                        gateCoordinates={gateCoordinates}
                        onExportSelection={handleExportSelection}
                      />
                    </div>
                  </div>
                )}
              </div>
                </>
              )}
            </TabsContent>

            <TabsContent value="diameter" className="space-y-4">
              {activeVisualizationTab === "diameter" && (
                <>
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  {anomalyData && anomalyData.total_anomalies > 0 && highlightAnomalies && (
                    <Badge variant="outline" className="bg-amber/20 text-amber border-amber/50">
                      Anomalies highlighted
                    </Badge>
                  )}
                  <Badge variant="outline" className="bg-purple/20 text-purple border-purple/50">
                    Mie Theory Reference
                  </Badge>
                </div>
                <div className="flex items-center gap-1 ml-auto">
                  <Button 
                    variant="ghost" 
                    size="icon" 
                    className="h-8 w-8"
                    onClick={() => handleExport("scatter")}
                  >
                    <Download className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Maximize2 className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => handlePin("Diameter vs SSC", "scatter")}
                  >
                    <Pin className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div data-pin-chart="diameter">
                <DiameterVsSSCChart
                  data={diameterVsSSCData}
                  anomalousIndices={anomalyData?.anomalous_indices || []}
                  highlightAnomalies={highlightAnomalies}
                  showMieTheory={true}
                  showLegend={true}
                  height={450}
                  secondaryData={secondaryDiameterVsSSCData}
                  secondaryAnomalousIndices={secondaryAnomalyData?.anomalous_indices || []}
                />
              </div>
                </>
              )}
            </TabsContent>

            <TabsContent value="event-size" className="space-y-4">
              {activeVisualizationTab === "event-size" && (
                <>
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge variant="outline" className="bg-blue-500/20 text-blue-500 border-blue-500/50">
                    Per-Event Size Analysis
                  </Badge>
                </div>
                <div className="flex gap-1">
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Maximize2 className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => handlePin("Event vs Size", "scatter")}
                  >
                    <Pin className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div data-pin-chart="event-size">
                {sampleId ? (
                  <EventVsSizeChart
                    sampleId={sampleId}
                    onPin={() => handlePin("Event vs Size", "scatter")}
                    title="Event Index vs Estimated Diameter"
                  />
                ) : (
                  <div className="h-[400px] flex items-center justify-center text-muted-foreground border border-dashed rounded-lg">
                    <p>Upload a sample to see per-event size analysis</p>
                  </div>
                )}
              </div>
                </>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Export and Data Table */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="card-3d">
          <CardHeader className="pb-3">
            <CardTitle className="text-base md:text-lg">Export Options</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => handleExport("csv")}
                >
                  <Download className="h-4 w-4 mr-1" />
                  CSV
                </Button>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => handleExport("excel")}
                >
                  <Download className="h-4 w-4 mr-1" />
                  Excel
                </Button>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => handleExport("parquet")}
                >
                  <Download className="h-4 w-4 mr-1" />
                  Parquet
                </Button>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => handleExport("json")}
                >
                  <Download className="h-4 w-4 mr-1" />
                  JSON
                </Button>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="text-amber border-amber/50 hover:bg-amber/20 bg-transparent"
                  onClick={() => handleExport("anomalies")}
                >
                  <AlertCircle className="h-4 w-4 mr-1" />
                  Anomalies Only
                </Button>
                <Button 
                  variant="secondary" 
                  size="sm"
                  onClick={() => handleExport("pdf")}
                >
                  <FileText className="h-4 w-4 mr-1" />
                  PDF Report
                </Button>
                <Button 
                  variant="secondary" 
                  size="sm"
                  onClick={() => handleExport("markdown")}
                >
                  <FileText className="h-4 w-4 mr-1" />
                  Markdown
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Export analysis results and visualizations in various formats for further processing or reporting.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="card-3d">
          <CardHeader className="pb-3">
            <CardTitle className="text-base md:text-lg flex items-center gap-2">
              <Table2 className="h-4 w-4" />
              Quick Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-muted-foreground">Sample ID:</span>
                <span className="font-medium">{sampleId || "N/A"}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-muted-foreground">Total Events:</span>
                <span className="font-medium">{totalEvents.toLocaleString()}</span>
              </div>
              {medianSize && (
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Median Size:</span>
                  <span className="font-medium">{medianSize.toFixed(1)} nm</span>
                </div>
              )}
              {results.fsc_median && (
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">FSC Median:</span>
                  <span className="font-medium">{results.fsc_median.toLocaleString()}</span>
                </div>
              )}
              {results.ssc_median && (
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">SSC Median:</span>
                  <span className="font-medium">{results.ssc_median.toLocaleString()}</span>
                </div>
              )}
              {results.channels && results.channels.length > 0 && (
                <div className="flex justify-between py-1">
                  <span className="text-muted-foreground">Channels:</span>
                  <span className="font-medium">{results.channels.length}</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Anomaly Events Table - show when user clicks "View Details" */}
      {showAnomalyDetails && anomalyData && anomalyEvents.length > 0 && (
        <AnomalyEventsTable
          events={anomalyEvents}
          onExport={() => handleExport("anomalies")}
          maxHeight="500px"
        />
      )}
    </div>
  )
}
