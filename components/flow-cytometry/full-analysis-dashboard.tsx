"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { 
  Maximize2, 
  Minimize2, 
  Pin, 
  Download, 
  Grid2X2, 
  LayoutGrid,
  Eye,
  EyeOff
} from "lucide-react"
import { SizeDistributionChart } from "./charts/size-distribution-chart"
import { ScatterPlotChart, type ScatterDataPoint } from "./charts/scatter-plot-with-selection"
import { TheoryVsMeasuredChart } from "./charts/theory-vs-measured-chart"
import { DiameterVsSSCChart, type DiameterDataPoint } from "./charts/diameter-vs-ssc-chart"
import { useAnalysisStore, type AnomalyDetectionResult } from "@/lib/store"
import { useToast } from "@/hooks/use-toast"
import type { FCSResult } from "@/lib/api-client"
import { cn } from "@/lib/utils"

interface FullAnalysisDashboardProps {
  results: FCSResult
  scatterData?: ScatterDataPoint[]
  anomalyData?: AnomalyDetectionResult | null
  sampleId?: string
}

type ChartType = "distribution" | "fsc-ssc" | "diameter-ssc" | "theory"

interface ChartConfig {
  id: ChartType
  title: string
  description: string
  pinType: "histogram" | "scatter" | "line"
}

const CHART_CONFIGS: ChartConfig[] = [
  { 
    id: "distribution", 
    title: "Size Distribution", 
    description: "Particle diameter histogram with EV categories",
    pinType: "histogram"
  },
  { 
    id: "fsc-ssc", 
    title: "FSC vs SSC", 
    description: "Forward vs side scatter density plot",
    pinType: "scatter"
  },
  { 
    id: "diameter-ssc", 
    title: "Diameter vs SSC", 
    description: "Estimated size vs scattering with Mie theory",
    pinType: "scatter"
  },
  { 
    id: "theory", 
    title: "Theory vs Measured", 
    description: "Mie prediction comparison",
    pinType: "line"
  },
]

export function FullAnalysisDashboard({
  results,
  scatterData = [],
  anomalyData,
  sampleId,
}: FullAnalysisDashboardProps) {
  const { pinChart } = useAnalysisStore()
  const { toast } = useToast()
  const [expandedChart, setExpandedChart] = useState<ChartType | null>(null)
  const [highlightAnomalies, setHighlightAnomalies] = useState(true)
  const [isCompactMode, setIsCompactMode] = useState(false)

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

  const handleExpand = (chartId: ChartType) => {
    setExpandedChart(expandedChart === chartId ? null : chartId)
  }

  // Convert scatter data to diameter format for the Diameter vs SSC chart
  const diameterData: DiameterDataPoint[] = scatterData
    .filter((p) => p.diameter !== undefined && p.y !== undefined)
    .map((p) => ({
      diameter: p.diameter as number,
      ssc: p.y,
      index: p.index,
      isAnomaly: anomalyData?.anomalous_indices?.includes(p.index ?? -1) || false,
    }))

  const renderChart = (chartId: ChartType, compact: boolean = false) => {
    const height = compact ? 200 : expandedChart === chartId ? 450 : 280

    switch (chartId) {
      case "distribution":
        return <SizeDistributionChart height={height} compact={compact} />
      case "fsc-ssc":
        return (
          <ScatterPlotChart
            title="FSC vs SSC"
            xLabel="FSC-A"
            yLabel="SSC-A"
            data={scatterData}
            anomalousIndices={anomalyData?.anomalous_indices || []}
            highlightAnomalies={highlightAnomalies}
            showLegend={!compact}
            height={height}
          />
        )
      case "diameter-ssc":
        return (
          <DiameterVsSSCChart
            data={diameterData.length > 0 ? diameterData : undefined}
            anomalousIndices={anomalyData?.anomalous_indices || []}
            highlightAnomalies={highlightAnomalies}
            showMieTheory={true}
            showLegend={!compact}
            height={height}
          />
        )
      case "theory":
        return <TheoryVsMeasuredChart />
      default:
        return null
    }
  }

  // If a chart is expanded, show only that chart
  if (expandedChart) {
    const config = CHART_CONFIGS.find((c) => c.id === expandedChart)!
    return (
      <Card className="card-3d">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg">{config.title}</CardTitle>
              <CardDescription>{config.description}</CardDescription>
            </div>
            <div className="flex items-center gap-1">
              {(expandedChart === "fsc-ssc" || expandedChart === "diameter-ssc") && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setHighlightAnomalies(!highlightAnomalies)}
                  className="h-8 text-xs gap-1"
                >
                  {highlightAnomalies ? (
                    <>
                      <Eye className="h-3.5 w-3.5" />
                      Anomalies ON
                    </>
                  ) : (
                    <>
                      <EyeOff className="h-3.5 w-3.5" />
                      Anomalies OFF
                    </>
                  )}
                </Button>
              )}
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => handlePin(config.title, config.pinType)}
              >
                <Pin className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setExpandedChart(null)}
              >
                <Minimize2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>{renderChart(expandedChart)}</CardContent>
      </Card>
    )
  }

  return (
    <Card className="card-3d">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-primary/10">
              <Grid2X2 className="h-4 w-4 text-primary" />
            </div>
            <div>
              <CardTitle className="text-base">Full Analysis Dashboard</CardTitle>
              <CardDescription className="text-xs">
                All visualizations in a single view • Click expand for details
              </CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {anomalyData && anomalyData.total_anomalies > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setHighlightAnomalies(!highlightAnomalies)}
                className="h-7 text-xs gap-1"
              >
                {highlightAnomalies ? (
                  <>
                    <Eye className="h-3 w-3" />
                    Anomalies
                  </>
                ) : (
                  <>
                    <EyeOff className="h-3 w-3" />
                    Hidden
                  </>
                )}
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsCompactMode(!isCompactMode)}
              className="h-7 text-xs gap-1"
            >
              <LayoutGrid className="h-3 w-3" />
              {isCompactMode ? "Expand" : "Compact"}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className={cn(
          "grid gap-4",
          isCompactMode ? "grid-cols-2 lg:grid-cols-4" : "grid-cols-1 md:grid-cols-2"
        )}>
          {CHART_CONFIGS.map((config) => (
            <div
              key={config.id}
              className="relative group border rounded-lg p-3 bg-secondary/20 hover:bg-secondary/40 transition-colors"
            >
              {/* Chart Header */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-medium">{config.title}</h4>
                  {config.id === "diameter-ssc" && (
                    <Badge variant="outline" className="text-[10px] h-4 px-1 bg-purple/20 text-purple border-purple/50">
                      Mie
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => handlePin(config.title, config.pinType)}
                  >
                    <Pin className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => handleExpand(config.id)}
                  >
                    <Maximize2 className="h-3 w-3" />
                  </Button>
                </div>
              </div>

              {/* Chart */}
              <div className="cursor-pointer" onClick={() => handleExpand(config.id)}>
                {renderChart(config.id, isCompactMode)}
              </div>

              {/* Quick Stats Badge */}
              {config.id === "distribution" && results.particle_size_median_nm && (
                <div className="absolute bottom-2 right-2">
                  <Badge variant="secondary" className="text-[10px] h-4 px-1.5">
                    Median: {results.particle_size_median_nm.toFixed(0)}nm
                  </Badge>
                </div>
              )}
              {config.id === "fsc-ssc" && anomalyData && highlightAnomalies && (
                <div className="absolute bottom-2 right-2">
                  <Badge 
                    variant="outline" 
                    className="text-[10px] h-4 px-1.5 bg-destructive/20 text-destructive border-destructive/50"
                  >
                    {anomalyData.total_anomalies} anomalies
                  </Badge>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Summary Row */}
        <div className="mt-4 pt-3 border-t flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
          <div className="flex items-center gap-4">
            <span>
              <strong className="text-foreground">{(results.total_events || results.event_count || 0).toLocaleString()}</strong> total events
            </span>
            {results.particle_size_median_nm && (
              <span>
                <strong className="text-foreground">{results.particle_size_median_nm.toFixed(1)}</strong> nm median
              </span>
            )}
            {anomalyData && (
              <span className="text-destructive">
                <strong>{anomalyData.total_anomalies.toLocaleString()}</strong> anomalies ({((anomalyData.total_anomalies / (results.total_events || results.event_count || 1)) * 100).toFixed(1)}%)
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-[10px] h-5">
              Sample: {sampleId || "Unknown"}
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
