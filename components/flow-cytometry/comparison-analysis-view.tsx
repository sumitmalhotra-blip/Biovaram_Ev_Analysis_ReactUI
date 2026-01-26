"use client"

import { useState, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  FileText, 
  Layers, 
  GitCompare, 
  RotateCcw, 
  Eye, 
  EyeOff,
  AlertCircle
} from "lucide-react"
import { useAnalysisStore } from "@/lib/store"
import { useToast } from "@/hooks/use-toast"
import { FullAnalysisDashboard } from "./full-analysis-dashboard"
import { StatisticsCards } from "./statistics-cards"
import { ScatterPlotChart } from "./charts/scatter-plot-chart"
import { OverlayHistogramChart } from "./overlay-histogram-chart"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { cn } from "@/lib/utils"

/**
 * ComparisonAnalysisView
 * 
 * Enhanced component for comparing two FCS files with separate tabs:
 * 1. Primary Tab - Complete analysis of primary file
 * 2. Comparison Tab - Complete analysis of comparison file
 * 3. Overlay Tab - Side-by-side comparison with overlay charts
 */
export function ComparisonAnalysisView() {
  const { 
    fcsAnalysis, 
    secondaryFcsAnalysis, 
    overlayConfig,
    setOverlayConfig,
    resetFCSAnalysis,
    resetSecondaryFCSAnalysis
  } = useAnalysisStore()
  const { toast } = useToast()
  
  const [activeView, setActiveView] = useState<"primary" | "comparison" | "overlay">("primary")
  
  const hasPrimaryResults = fcsAnalysis.results !== null
  const hasComparisonResults = secondaryFcsAnalysis.results !== null
  const canShowOverlay = hasPrimaryResults && hasComparisonResults

  const handleResetAll = useCallback(() => {
    resetFCSAnalysis()
    resetSecondaryFCSAnalysis()
    setOverlayConfig({ enabled: false })
    toast({
      title: "Analysis Reset",
      description: "Both files cleared. Upload new files to start fresh.",
    })
  }, [resetFCSAnalysis, resetSecondaryFCSAnalysis, setOverlayConfig, toast])

  const handleResetPrimary = useCallback(() => {
    resetFCSAnalysis()
    setOverlayConfig({ enabled: false })
    toast({
      title: "Primary File Reset",
      description: "Primary analysis cleared.",
    })
  }, [resetFCSAnalysis, setOverlayConfig, toast])

  const handleResetComparison = useCallback(() => {
    resetSecondaryFCSAnalysis()
    setOverlayConfig({ enabled: false })
    toast({
      title: "Comparison File Reset",
      description: "Comparison analysis cleared.",
    })
  }, [resetSecondaryFCSAnalysis, setOverlayConfig, toast])

  const toggleOverlay = useCallback(() => {
    if (!canShowOverlay) {
      toast({
        title: "Cannot Enable Overlay",
        description: "Upload both primary and comparison files first.",
        variant: "destructive"
      })
      return
    }
    
    const newEnabled = !overlayConfig.enabled
    setOverlayConfig({ enabled: newEnabled })
    
    if (newEnabled) {
      setActiveView("overlay")
    }
    
    toast({
      title: newEnabled ? "Overlay Enabled" : "Overlay Disabled",
      description: newEnabled 
        ? "Viewing combined analysis" 
        : "Switched to individual file view",
    })
  }, [canShowOverlay, overlayConfig.enabled, setOverlayConfig, toast])

  // If no results at all, show placeholder
  if (!hasPrimaryResults && !hasComparisonResults) {
    return (
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>No Analysis Results</AlertTitle>
        <AlertDescription>
          Upload FCS files to see analysis results. Use the tabs above to upload primary and comparison files.
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-4">
      {/* View Tabs and Controls */}
      <Card className="card-3d">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <CardTitle className="text-base">Analysis View</CardTitle>
              {canShowOverlay && (
                <Badge variant={overlayConfig.enabled ? "default" : "outline"} className="gap-1">
                  <GitCompare className="h-3 w-3" />
                  {overlayConfig.enabled ? "Overlay Active" : "Overlay Available"}
                </Badge>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              {canShowOverlay && (
                <Button
                  variant={overlayConfig.enabled ? "default" : "outline"}
                  size="sm"
                  onClick={toggleOverlay}
                  className="gap-1"
                >
                  {overlayConfig.enabled ? (
                    <>
                      <EyeOff className="h-3 w-3" />
                      Disable Overlay
                    </>
                  ) : (
                    <>
                      <Eye className="h-3 w-3" />
                      Enable Overlay
                    </>
                  )}
                </Button>
              )}
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
          <Tabs value={activeView} onValueChange={(v) => setActiveView(v as "primary" | "comparison" | "overlay")}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="primary" disabled={!hasPrimaryResults} className="gap-2">
                <FileText className="h-4 w-4" />
                Primary
                {hasPrimaryResults && (
                  <Badge variant="outline" className="ml-1 h-5 px-1.5 text-[10px]">
                    {(fcsAnalysis.results?.total_events || 0).toLocaleString()}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="comparison" disabled={!hasComparisonResults} className="gap-2">
                <Layers className="h-4 w-4" />
                Comparison
                {hasComparisonResults && (
                  <Badge variant="outline" className="ml-1 h-5 px-1.5 text-[10px]">
                    {(secondaryFcsAnalysis.results?.total_events || 0).toLocaleString()}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="overlay" disabled={!canShowOverlay} className="gap-2">
                <GitCompare className="h-4 w-4" />
                Overlay
                {canShowOverlay && overlayConfig.enabled && (
                  <Badge className="ml-1 h-5 px-1.5 text-[10px]">Active</Badge>
                )}
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </CardContent>
      </Card>

      {/* Tab Contents */}
      {activeView === "primary" && hasPrimaryResults && (
        <PrimaryAnalysisPanel 
          onReset={handleResetPrimary}
        />
      )}

      {activeView === "comparison" && hasComparisonResults && (
        <ComparisonAnalysisPanel 
          onReset={handleResetComparison}
        />
      )}

      {activeView === "overlay" && canShowOverlay && (
        <OverlayAnalysisPanel />
      )}
    </div>
  )
}

/**
 * Primary Analysis Panel - Full analysis of the primary file
 */
function PrimaryAnalysisPanel({ onReset }: { onReset: () => void }) {
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
                <p className="font-medium">{fcsAnalysis.file?.name || fcsAnalysis.sampleId || "Primary File"}</p>
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

      {/* Full Analysis Dashboard will show all charts */}
      <FullAnalysisDashboard results={results} />
    </div>
  )
}

/**
 * Comparison Analysis Panel - Full analysis of the comparison file
 */
function ComparisonAnalysisPanel({ onReset }: { onReset: () => void }) {
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
                <p className="font-medium">{secondaryFcsAnalysis.file?.name || secondaryFcsAnalysis.sampleId || "Comparison File"}</p>
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

      {/* Full Analysis Dashboard - show all charts including scatter plots */}
      <FullAnalysisDashboard results={results} />
    </div>
  )
}

/**
 * Overlay Analysis Panel - Combined comparison view
 */
function OverlayAnalysisPanel() {
  const { fcsAnalysis, secondaryFcsAnalysis, overlayConfig } = useAnalysisStore()
  const primaryResults = fcsAnalysis.results
  const secondaryResults = secondaryFcsAnalysis.results

  if (!primaryResults || !secondaryResults) return null

  return (
    <div className="space-y-4">
      {/* Side-by-side Statistics Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Primary Stats */}
        <Card className="bg-primary/5 border-primary/20">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: overlayConfig.primaryColor }}
              />
              <CardTitle className="text-sm">
                {fcsAnalysis.file?.name || "Primary"}
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <p className="text-muted-foreground text-xs">Events</p>
              <p className="font-mono font-medium">{primaryResults.total_events?.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">D50 Size</p>
              <p className="font-mono font-medium">{primaryResults.size_statistics?.d50?.toFixed(1) || "N/A"} nm</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">FSC Median</p>
              <p className="font-mono font-medium">{primaryResults.fsc_median?.toFixed(1) || "N/A"}</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">Debris %</p>
              <p className="font-mono font-medium">{primaryResults.debris_pct?.toFixed(1) || "N/A"}%</p>
            </div>
          </CardContent>
        </Card>

        {/* Secondary Stats */}
        <Card className="bg-orange-500/5 border-orange-500/20">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: overlayConfig.secondaryColor }}
              />
              <CardTitle className="text-sm">
                {secondaryFcsAnalysis.file?.name || "Comparison"}
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <p className="text-muted-foreground text-xs">Events</p>
              <p className="font-mono font-medium">{secondaryResults.total_events?.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">D50 Size</p>
              <p className="font-mono font-medium">{secondaryResults.size_statistics?.d50?.toFixed(1) || "N/A"} nm</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">FSC Median</p>
              <p className="font-mono font-medium">{secondaryResults.fsc_median?.toFixed(1) || "N/A"}</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">Debris %</p>
              <p className="font-mono font-medium">{secondaryResults.debris_pct?.toFixed(1) || "N/A"}%</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Difference Summary */}
      <Card className="card-3d">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <GitCompare className="h-4 w-4 text-primary" />
            <CardTitle className="text-base">Comparison Summary</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <DifferenceMetric 
              label="Event Count Diff" 
              primary={primaryResults.total_events || 0}
              secondary={secondaryResults.total_events || 0}
            />
            <DifferenceMetric 
              label="D50 Size Diff" 
              primary={primaryResults.size_statistics?.d50 || 0}
              secondary={secondaryResults.size_statistics?.d50 || 0}
              unit="nm"
            />
            <DifferenceMetric 
              label="FSC Median Diff" 
              primary={primaryResults.fsc_median || 0}
              secondary={secondaryResults.fsc_median || 0}
            />
            <DifferenceMetric 
              label="Debris % Diff" 
              primary={primaryResults.debris_pct || 0}
              secondary={secondaryResults.debris_pct || 0}
              unit="%"
              isPercentage
            />
          </div>
        </CardContent>
      </Card>

      {/* Overlay Charts */}
      <OverlayHistogramChart title="Size Distribution Overlay" parameter="size" />
      
      {/* Side-by-side Scatter Plots */}
      <Card className="card-3d">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <GitCompare className="h-4 w-4 text-primary" />
            <CardTitle className="text-base">FSC vs SSC Scatter Comparison</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Primary Scatter */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div 
                  className="w-3 h-3 rounded-full" 
                  style={{ backgroundColor: overlayConfig.primaryColor }}
                />
                <span className="text-sm font-medium">{fcsAnalysis.file?.name || "Primary"}</span>
                <Badge variant="outline" className="text-xs">
                  {primaryResults.total_events?.toLocaleString()} events
                </Badge>
              </div>
              <div className="h-[300px] bg-secondary/20 rounded-lg p-2">
                <ScatterPlotChart 
                  title="Primary FSC vs SSC"
                  xLabel="FSC-A"
                  yLabel="SSC-A"
                  height={280}
                  showLegend={false}
                />
              </div>
            </div>
            
            {/* Comparison Scatter */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div 
                  className="w-3 h-3 rounded-full" 
                  style={{ backgroundColor: overlayConfig.secondaryColor }}
                />
                <span className="text-sm font-medium">{secondaryFcsAnalysis.file?.name || "Comparison"}</span>
                <Badge variant="outline" className="text-xs">
                  {secondaryResults.total_events?.toLocaleString()} events
                </Badge>
              </div>
              <div className="h-[300px] bg-secondary/20 rounded-lg p-2">
                <ScatterPlotChart 
                  title="Comparison FSC vs SSC"
                  data={secondaryFcsAnalysis.scatterData || []}
                  xLabel="FSC-A"
                  yLabel="SSC-A"
                  height={280}
                  showLegend={false}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <OverlayHistogramChart title="Forward Scatter (FSC) Overlay" parameter="FSC-A" />
      <OverlayHistogramChart title="Side Scatter (SSC) Overlay" parameter="SSC-A" />
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
