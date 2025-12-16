"use client"

import { useState, useMemo, useEffect } from "react"
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
import { TheoryVsMeasuredChart } from "./charts/theory-vs-measured-chart"
import { DiameterVsSSCChart } from "./charts/diameter-vs-ssc-chart"
import { FullAnalysisDashboard } from "./full-analysis-dashboard"
import { StatisticsCards } from "./statistics-cards"
import { ParticleSizeVisualization } from "./particle-size-visualization"
import { CustomSizeRanges } from "./custom-size-ranges"
import { AnomalySummaryCard } from "./anomaly-summary-card"
import { AnomalyEventsTable, type AnomalyEvent } from "./anomaly-events-table"
import { useToast } from "@/hooks/use-toast"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { exportAnomaliesToCSV, exportScatterDataToCSV, exportToParquet, generateMarkdownReport, downloadMarkdownReport } from "@/lib/export-utils"

export function AnalysisResults() {
  const { pinChart, fcsAnalysis, resetFCSAnalysis } = useAnalysisStore()
  const { getScatterData, getSizeBins } = useApi()
  const { toast } = useToast()
  const [showAnomalyDetails, setShowAnomalyDetails] = useState(false)
  const [highlightAnomalies, setHighlightAnomalies] = useState(true)
  const [scatterData, setScatterData] = useState<ScatterDataPoint[]>([])
  const [loadingScatter, setLoadingScatter] = useState(false)
  const [sizeCategories, setSizeCategories] = useState<{ small: number; medium: number; large: number } | null>(null)
  const [loadingSizeBins, setLoadingSizeBins] = useState(false)
  const [selectedIndices, setSelectedIndices] = useState<number[]>([])

  // Use real results from the API
  const results = fcsAnalysis.results
  const anomalyData = fcsAnalysis.anomalyData
  const sampleId = fcsAnalysis.sampleId
  const fileName = fcsAnalysis.file?.name

  // Load real scatter data from backend
  useEffect(() => {
    if (sampleId && results) {
      setLoadingScatter(true)
      getScatterData(sampleId, 5000)
        .then((data) => {
          if (data) {
            setScatterData(data.data)
          }
        })
        .finally(() => setLoadingScatter(false))
    }
  }, [sampleId, results, getScatterData])

  // Load real size bins from backend
  useEffect(() => {
    if (sampleId && results) {
      setLoadingSizeBins(true)
      getSizeBins(sampleId)
        .then((data) => {
          if (data) {
            setSizeCategories(data.bins)
          }
        })
        .finally(() => setLoadingSizeBins(false))
    }
  }, [sampleId, results, getSizeBins])

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

  // Generate mock anomaly events for table (TODO: Replace with real data)
  const anomalyEvents: AnomalyEvent[] = useMemo(() => {
    if (!anomalyData || !anomalyData.anomalous_indices) return []
    
    return anomalyData.anomalous_indices.slice(0, 100).map((index) => ({
      index,
      fsc: Math.random() * 1000 + 100,
      ssc: Math.random() * 800 + 50,
      zscore_fsc: (Math.random() - 0.5) * 8,
      zscore_ssc: (Math.random() - 0.5) * 8,
      iqr_outlier_fsc: Math.random() > 0.5,
      iqr_outlier_ssc: Math.random() > 0.5,
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

    toast({
      title: "Exporting...",
      description: `Preparing ${format.toUpperCase()} export`,
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
          sizeCategories={sizeCategories || undefined}
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
            <TabsList className="bg-secondary/50 w-full justify-start overflow-x-auto flex-nowrap">
              <TabsTrigger value="dashboard" className="shrink-0">
                Full Dashboard
              </TabsTrigger>
              <TabsTrigger value="distribution" className="shrink-0">
                Size Distribution
              </TabsTrigger>
              <TabsTrigger value="theory" className="shrink-0">
                Theory vs Measured
              </TabsTrigger>
              <TabsTrigger value="fsc-ssc" className="shrink-0">
                FSC vs SSC
              </TabsTrigger>
              <TabsTrigger value="diameter" className="shrink-0">
                Diameter vs SSC
              </TabsTrigger>
            </TabsList>

            <TabsContent value="dashboard" className="space-y-4">
              <FullAnalysisDashboard
                results={results}
                scatterData={scatterData}
                anomalyData={anomalyData}
                sampleId={sampleId || undefined}
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
              <SizeDistributionChart />
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
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  {anomalyData && anomalyData.total_anomalies > 0 && (
                    <Badge variant="outline" className="bg-destructive/20 text-destructive border-destructive/50">
                      {anomalyData.total_anomalies.toLocaleString()} anomalies detected
                    </Badge>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setHighlightAnomalies(!highlightAnomalies)}
                    className="h-7 text-xs"
                  >
                    {highlightAnomalies ? (
                      <>
                        <Eye className="h-3 w-3 mr-1" />
                        Highlighting ON
                      </>
                    ) : (
                      <>
                        <EyeOff className="h-3 w-3 mr-1" />
                        Highlighting OFF
                      </>
                    )}
                  </Button>
                </div>
                <div className="flex items-center gap-1">
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
                    onClick={() => handlePin("FSC vs SSC Scatter", "scatter")}
                  >
                    <Pin className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              {loadingScatter ? (
                <div className="flex items-center justify-center h-[400px]">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  <span className="ml-3 text-muted-foreground">Loading scatter data...</span>
                </div>
              ) : (
                <ScatterPlotChart
                  title="FSC vs SSC - Interactive"
                  xLabel="FSC-A"
                  yLabel="SSC-A"
                  data={scatterData}
                  anomalousIndices={anomalyData?.anomalous_indices || []}
                  highlightAnomalies={highlightAnomalies}
                  showLegend={true}
                  height={400}
                  onSelectionChange={(indices) => {
                    setSelectedIndices(indices)
                    if (indices.length > 0) {
                      toast({
                        title: "Selection made",
                        description: `${indices.length} events selected`,
                      })
                    }
                  }}
                />
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
              />
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
