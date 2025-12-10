"use client"

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
  Table2 
} from "lucide-react"
import { useAnalysisStore } from "@/lib/store"
import { SizeDistributionChart } from "./charts/size-distribution-chart"
import { ScatterPlotChart } from "./charts/scatter-plot-chart"
import { TheoryVsMeasuredChart } from "./charts/theory-vs-measured-chart"
import { StatisticsCards } from "./statistics-cards"
import { SizeCategoryBreakdown } from "./size-category-breakdown"
import { useToast } from "@/hooks/use-toast"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

export function AnalysisResults() {
  const { pinChart, fcsAnalysis } = useAnalysisStore()
  const { toast } = useToast()

  // Use real results from the API
  const results = fcsAnalysis.results
  const sampleId = fcsAnalysis.sampleId
  const fileName = fcsAnalysis.file?.name

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

  const handleExport = (format: string) => {
    toast({
      title: "Exporting...",
      description: `Preparing ${format.toUpperCase()} export`,
    })
    // TODO: Implement actual export functionality
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
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Statistics Cards */}
      <StatisticsCards results={results} />

      {/* Size Category Breakdown */}
      <SizeCategoryBreakdown 
        totalEvents={totalEvents}
        medianSize={medianSize}
      />

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
          <Tabs defaultValue="distribution" className="space-y-4">
            <TabsList className="bg-secondary/50 w-full justify-start overflow-x-auto flex-nowrap">
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
                <Badge variant="outline" className="bg-destructive/20 text-destructive border-destructive/50">
                  Anomalies highlighted
                </Badge>
                <div className="flex items-center gap-1">
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
              <ScatterPlotChart title="FSC vs SSC" xLabel="FSC-A" yLabel="SSC-A" />
            </TabsContent>

            <TabsContent value="diameter" className="space-y-4">
              <div className="flex items-center justify-end gap-1">
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
              <ScatterPlotChart title="Diameter vs SSC" xLabel="Diameter (nm)" yLabel="SSC-A" />
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
    </div>
  )
}
