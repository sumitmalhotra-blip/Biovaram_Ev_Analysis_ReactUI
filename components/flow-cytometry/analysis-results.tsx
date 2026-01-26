"use client"

import { useState, useMemo, useEffect, useCallback } from "react"
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
  RotateCcw
} from "lucide-react"
import { useAnalysisStore } from "@/lib/store"
import { useApi } from "@/hooks/use-api"
import { SizeDistributionChart } from "./charts/size-distribution-chart"
import { ScatterPlotChart, type ScatterDataPoint } from "./charts/scatter-plot-with-selection"
import { InteractiveScatterChart } from "./charts/interactive-scatter-chart"
import { ScatterAxisSelector } from "./charts/scatter-axis-selector"
import { TheoryVsMeasuredChart } from "./charts/theory-vs-measured-chart"
import { DiameterVsSSCChart } from "./charts/diameter-vs-ssc-chart"
import { EventVsSizeChart } from "./charts/event-vs-size-chart"
import { FullAnalysisDashboard } from "./full-analysis-dashboard"
import { StatisticsCards } from "./statistics-cards"
import { ParticleSizeVisualization } from "./particle-size-visualization"
import { CustomSizeRanges } from "./custom-size-ranges"
import { AnomalySummaryCard } from "./anomaly-summary-card"
import { AnomalyEventsTable, type AnomalyEvent } from "./anomaly-events-table"
import { IndividualFileSummary } from "./individual-file-summary"
import { GatedStatisticsPanel } from "./gated-statistics-panel"
import { useToast } from "@/hooks/use-toast"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
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
  } = useAnalysisStore()
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

  // CRMIT-002: Handle axis change from selector
  const handleAxisChange = useCallback((newXChannel: string, newYChannel: string) => {
    setXChannel(newXChannel)
    setYChannel(newYChannel)
  }, [])

  // Initialize channel selection from FCS results when available
  useEffect(() => {
    if (results?.channels && results.channels.length > 0 && !channelsInitialized) {
      const channels = results.channels
      
      // Try to find FSC/SSC channels, or use first two channels
      const fscPatterns = ['FSC-A', 'VFSC-A', 'FSC-H', 'VFSC-H']
      const sscPatterns = ['SSC-A', 'VSSC1-A', 'SSC-H', 'VSSC1-H', 'VSSC2-A']
      
      let detectedFsc = channels.find(ch => fscPatterns.some(p => ch.toUpperCase().includes(p.toUpperCase())))
      let detectedSsc = channels.find(ch => sscPatterns.some(p => ch.toUpperCase().includes(p.toUpperCase())))
      
      // Fallback to first two channels if standard names not found
      if (!detectedFsc && channels.length >= 1) {
        detectedFsc = channels[0]
      }
      if (!detectedSsc && channels.length >= 2) {
        detectedSsc = channels[1]
      }
      
      if (detectedFsc) setXChannel(detectedFsc)
      if (detectedSsc) setYChannel(detectedSsc)
      setChannelsInitialized(true)
      
      console.log(`[AnalysisResults] Auto-detected channels: X=${detectedFsc}, Y=${detectedSsc} from ${channels.length} available channels`)
    }
  }, [results?.channels, channelsInitialized])

  // Reset channel initialization when sample changes
  useEffect(() => {
    setChannelsInitialized(false)
  }, [sampleId])

  // Load real scatter data from backend - CRMIT-002: Updated to use custom axes
  // Also refreshes when Mie settings change (wavelength, RI, etc.)
  useEffect(() => {
    let cancelled = false
    // Only fetch if channels are set and sample exists
    if (sampleId && results && xChannel && yChannel) {
      setLoadingScatter(true)
      // Use getScatterDataWithAxes for custom channel selection
      getScatterDataWithAxes(sampleId, xChannel, yChannel, 2000)
        .then((data) => {
          if (!cancelled && data) {
            setScatterData(data.data)
            // Debug: Log scatter data with diameters
            const withDiameters = data.data.filter((p: { diameter?: number }) => p.diameter !== undefined && p.diameter !== null && p.diameter > 0)
            console.log('[AnalysisResults] Scatter data loaded:', {
              totalPoints: data.data.length,
              pointsWithDiameters: withDiameters.length,
              sampleDiameters: withDiameters.slice(0, 5).map((p: { diameter?: number }) => p.diameter),
              totalEvents: data.total_events
            })
          }
        })
        .finally(() => {
          if (!cancelled) setLoadingScatter(false)
        })
    }
    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sampleId, results, xChannel, yChannel, fcsAnalysisSettings?.laserWavelength, fcsAnalysisSettings?.particleRI, fcsAnalysisSettings?.mediumRI])
  
  // Load secondary scatter data when overlay is enabled
  // Uses fallback channels if primary channels don't exist in secondary file
  useEffect(() => {
    let cancelled = false
    if (overlayConfig.enabled && secondarySampleId && secondaryResults && xChannel && yChannel) {
      setSecondaryFCSLoadingScatter(true)
      
      // Check if secondary file has the same channels, otherwise use its first two channels
      const secondaryChannels = secondaryResults.channels || []
      let secXChannel = xChannel
      let secYChannel = yChannel
      
      // If primary channels don't exist in secondary file, use fallback
      if (!secondaryChannels.includes(xChannel) || !secondaryChannels.includes(yChannel)) {
        console.log(`[AnalysisResults] Secondary file doesn't have channels ${xChannel}/${yChannel}, using fallback`)
        // Try to find FSC/SSC patterns in secondary file
        const fscPatterns = ['FSC-A', 'VFSC-A', 'FSC-H', 'VFSC-H']
        const sscPatterns = ['SSC-A', 'VSSC1-A', 'SSC-H', 'VSSC1-H', 'VSSC2-A']
        
        secXChannel = secondaryChannels.find(ch => fscPatterns.some(p => ch.toUpperCase().includes(p.toUpperCase()))) || secondaryChannels[0] || xChannel
        secYChannel = secondaryChannels.find(ch => sscPatterns.some(p => ch.toUpperCase().includes(p.toUpperCase()))) || secondaryChannels[1] || yChannel
      }
      
      getScatterDataWithAxes(secondarySampleId, secXChannel, secYChannel, 2000)
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
  }, [overlayConfig.enabled, secondarySampleId, secondaryResults, xChannel, yChannel])

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

  // Load real size bins from backend - PERFORMANCE FIX: Removed callback from deps
  // Also refreshes when Mie settings or size ranges change
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
  }, [sampleId, results, fcsAnalysisSettings?.laserWavelength, fcsAnalysisSettings?.particleRI, fcsAnalysisSettings?.mediumRI, fcsAnalysis.sizeRanges])

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

  // Deterministic pseudo-random for SSR compatibility
  const seededRandom = (seed: number): number => {
    const x = Math.sin(seed * 9999) * 10000
    return x - Math.floor(x)
  }

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

  const handlePin = (chartTitle: string, chartType: "histogram" | "scatter" | "line") => {
    pinChart({
      id: crypto.randomUUID(),
      title: chartTitle,
      source: "Flow Cytometry",
      timestamp: new Date(),
      type: chartType,
      data: results,
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
      {loadingSizeBins ? (
        <Card className="card-3d">
          <CardContent className="p-8 flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-primary mr-3" />
            <span className="text-muted-foreground">Calculating size distribution...</span>
          </CardContent>
        </Card>
      ) : (
        <ParticleSizeVisualization
          totalEvents={totalEvents}
          medianSize={medianSize}
          scatterData={scatterData}
        />
      )}

      {/* Custom Size Range Analysis */}
      <CustomSizeRanges 
        sizeData={scatterData
          .filter((p) => p.diameter !== undefined)
          .map((p) => p.diameter as number)
        }
      />

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
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="dashboard" className="space-y-4">
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
              <div className="absolute right-0 top-0 h-full w-8 bg-gradient-to-l from-background to-transparent pointer-events-none" />
            </div>

            <TabsContent value="dashboard" className="space-y-4">
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
                secondarySizeData={secondaryScatterData?.filter(p => p.diameter).map(p => p.diameter as number)}
              />
            </TabsContent>

            <TabsContent value="distribution" className="space-y-4">
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
              <SizeDistributionChart 
                sizeData={scatterData.filter(p => p.diameter).map(p => p.diameter as number)}
                secondarySizeData={secondaryScatterData?.filter(p => p.diameter).map(p => p.diameter as number)}
                d10={results.size_statistics?.d10}
                d50={results.size_statistics?.d50}
                d90={results.size_statistics?.d90}
                secondaryD10={secondaryResults?.size_statistics?.d10}
                secondaryD50={secondaryResults?.size_statistics?.d50}
                secondaryD90={secondaryResults?.size_statistics?.d90}
              />
            </TabsContent>

            <TabsContent value="theory" className="space-y-4">
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
              <TheoryVsMeasuredChart />
            </TabsContent>

            <TabsContent value="fsc-ssc" className="space-y-4">
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
              
              {loadingScatter ? (
                <div className="flex items-center justify-center h-[400px]">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  <span className="ml-3 text-muted-foreground">Loading scatter data...</span>
                </div>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                  <div className="lg:col-span-3">
                    {/* NEW: Interactive SVG-based scatter chart with reliable selection */}
                    <InteractiveScatterChart
                      title={`${xChannel} vs ${yChannel}`}
                      xLabel={xChannel}
                      yLabel={yChannel}
                      data={scatterData}
                      anomalousIndices={anomalyData?.anomalous_indices || []}
                      highlightAnomalies={highlightAnomalies}
                      height={450}
                      onSelectionChange={(indices, coords) => {
                        setSelectedIndices(indices)
                        setGateCoordinates(coords || null)
                        if (indices.length > 0) {
                          toast({
                            title: "Population Gated",
                            description: `${indices.length} events selected. Click "Analyze Selection" or "Save Gate" for further analysis.`,
                          })
                        }
                      }}
                      onGatedAnalysis={(selectedData) => {
                        // Calculate statistics for selected population
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
                      }}
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
                      onExportSelection={(indices) => {
                        // Export selected events to CSV
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
                      }}
                    />
                  </div>
                </div>
              )}
            </TabsContent>

            <TabsContent value="diameter" className="space-y-4">
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
              <DiameterVsSSCChart
                data={scatterData
                  .filter((p) => p.diameter !== undefined && p.y !== undefined)
                  .map((p) => ({
                    diameter: p.diameter as number,
                    ssc: p.y,
                    index: p.index,
                    isAnomaly: anomalyData?.anomalous_indices?.includes(p.index ?? -1) || false,
                  }))
                }
                anomalousIndices={anomalyData?.anomalous_indices || []}
                highlightAnomalies={highlightAnomalies}
                showMieTheory={true}
                showLegend={true}
                height={450}
                secondaryData={secondaryScatterData
                  ?.filter((p) => p.diameter !== undefined && p.y !== undefined)
                  .map((p) => ({
                    diameter: p.diameter as number,
                    ssc: p.y,
                    index: p.index,
                    isAnomaly: secondaryAnomalyData?.anomalous_indices?.includes(p.index ?? -1) || false,
                  }))
                }
                secondaryAnomalousIndices={secondaryAnomalyData?.anomalous_indices || []}
              />
            </TabsContent>

            <TabsContent value="event-size" className="space-y-4">
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
              {sampleId ? (
                <EventVsSizeChart
                  sampleId={sampleId}
                  onPin={() => handlePin("Event vs Size", "scatter")}
                  title="Event Number vs Calculated Size"
                />
              ) : (
                <div className="h-[400px] flex items-center justify-center text-muted-foreground border border-dashed rounded-lg">
                  <p>Upload a sample to see per-event size analysis</p>
                </div>
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
