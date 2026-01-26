"use client"

import { useMemo, useState, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { 
  Target, 
  Download, 
  Trash2, 
  BarChart3, 
  Layers,
  ChevronDown,
  ChevronUp,
  Server,
  Loader2,
  AlertCircle,
  Play,
  CheckCircle2
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useAnalysisStore, type GatedStatistics, type Gate } from "@/lib/store"
import { useApi } from "@/hooks/use-api"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

interface GatedStatisticsPanelProps {
  scatterData: Array<{ x: number; y: number; diameter?: number; index?: number }>
  xLabel: string
  yLabel: string
  selectedIndices: number[]
  sampleId?: string | null
  gateCoordinates?: { x1: number; y1: number; x2: number; y2: number } | null
  onExportSelection?: (indices: number[]) => void
  onApplyGate?: (gate: Gate, indices: number[]) => void
}

interface PopulationStats {
  count: number
  percentage: number
  xMean: number
  xStd: number
  xMin: number
  xMax: number
  xMedian: number
  yMean: number
  yStd: number
  yMin: number
  yMax: number
  yMedian: number
  diameterMean?: number
  diameterStd?: number
  diameterMin?: number
  diameterMax?: number
  diameterMedian?: number
}

function calculateStats(data: Array<{ x: number; y: number; diameter?: number }>): PopulationStats | null {
  if (!data || data.length === 0) return null

  const xValues = data.map(p => p.x).filter(v => !isNaN(v))
  const yValues = data.map(p => p.y).filter(v => !isNaN(v))
  const diameterValues = data.map(p => p.diameter).filter((v): v is number => v !== undefined && !isNaN(v))

  const mean = (arr: number[]) => arr.reduce((a, b) => a + b, 0) / arr.length
  const std = (arr: number[]) => {
    const m = mean(arr)
    return Math.sqrt(arr.reduce((acc, val) => acc + (val - m) ** 2, 0) / arr.length)
  }
  const median = (arr: number[]) => {
    const sorted = [...arr].sort((a, b) => a - b)
    const mid = Math.floor(sorted.length / 2)
    return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2
  }

  const stats: PopulationStats = {
    count: data.length,
    percentage: 0, // Will be calculated by parent
    xMean: mean(xValues),
    xStd: std(xValues),
    xMin: Math.min(...xValues),
    xMax: Math.max(...xValues),
    xMedian: median(xValues),
    yMean: mean(yValues),
    yStd: std(yValues),
    yMin: Math.min(...yValues),
    yMax: Math.max(...yValues),
    yMedian: median(yValues),
  }

  if (diameterValues.length > 0) {
    stats.diameterMean = mean(diameterValues)
    stats.diameterStd = std(diameterValues)
    stats.diameterMin = Math.min(...diameterValues)
    stats.diameterMax = Math.max(...diameterValues)
    stats.diameterMedian = median(diameterValues)
  }

  return stats
}

function StatRow({ label, value, unit = "" }: { label: string; value: number | undefined; unit?: string }) {
  if (value === undefined) return null
  return (
    <div className="flex justify-between items-center text-xs py-0.5">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono font-medium">
        {typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '-'}
        {unit && <span className="text-muted-foreground ml-1">{unit}</span>}
      </span>
    </div>
  )
}

export function GatedStatisticsPanel({
  scatterData,
  xLabel,
  yLabel,
  selectedIndices,
  sampleId,
  gateCoordinates,
  onExportSelection,
  onApplyGate,
}: GatedStatisticsPanelProps) {
  const { gatingState, clearAllGates, removeGate, setActiveGate, setSelectedIndices, apiConnected } = useAnalysisStore()
  const { analyzeGatedPopulation } = useApi()
  const [isExpanded, setIsExpanded] = useState(true)
  const [serverAnalysis, setServerAnalysis] = useState<{
    statistics: {
      x_channel: { mean: number; median: number; std: number; min: number; max: number; cv: number };
      y_channel: { mean: number; median: number; std: number; min: number; max: number; cv: number };
      diameter: { mean: number; median: number; std: number; min: number; max: number; cv: number } | null;
    };
    percentiles: { D10: number; D50: number; D90: number } | null;
    comparison_to_total: { x_mean_diff_percent: number; y_mean_diff_percent: number } | null;
  } | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisError, setAnalysisError] = useState<string | null>(null)

  // Run server-side gated analysis
  const runServerAnalysis = useCallback(async () => {
    if (!sampleId || !gateCoordinates || selectedIndices.length === 0) return
    
    setIsAnalyzing(true)
    setAnalysisError(null)
    
    try {
      const result = await analyzeGatedPopulation(sampleId, {
        gate_name: "Live Selection",
        gate_type: "rectangle",
        gate_coordinates: {
          x1: gateCoordinates.x1,
          y1: gateCoordinates.y1,
          x2: gateCoordinates.x2,
          y2: gateCoordinates.y2,
        },
        x_channel: xLabel,
        y_channel: yLabel,
        include_diameter_stats: true,
      })
      
      if (result && result.statistics) {
        setServerAnalysis({
          statistics: result.statistics,
          percentiles: result.percentiles,
          comparison_to_total: result.comparison_to_total,
        })
      }
    } catch (error) {
      setAnalysisError("Failed to analyze on server")
    } finally {
      setIsAnalyzing(false)
    }
  }, [sampleId, gateCoordinates, selectedIndices.length, analyzeGatedPopulation, xLabel, yLabel])

  // Apply a saved gate - recalculate which points are inside
  const handleApplyGate = useCallback((gate: Gate) => {
    if (!scatterData || scatterData.length === 0) return

    const indices: number[] = []
    
    scatterData.forEach((point, idx) => {
      const pointIndex = point.index ?? idx
      let isInside = false

      if (gate.shape.type === 'rectangle') {
        const { x1, y1, x2, y2 } = gate.shape
        const minX = Math.min(x1, x2)
        const maxX = Math.max(x1, x2)
        const minY = Math.min(y1, y2)
        const maxY = Math.max(y1, y2)
        isInside = point.x >= minX && point.x <= maxX && point.y >= minY && point.y <= maxY
      } else if (gate.shape.type === 'ellipse') {
        const { cx, cy, rx, ry } = gate.shape
        // Ellipse equation: ((x-h)/a)^2 + ((y-k)/b)^2 <= 1
        const normalizedX = (point.x - cx) / rx
        const normalizedY = (point.y - cy) / ry
        isInside = normalizedX * normalizedX + normalizedY * normalizedY <= 1
      } else if (gate.shape.type === 'polygon') {
        // Point-in-polygon using ray casting algorithm
        const { points } = gate.shape
        let inside = false
        for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
          const xi = points[i].x, yi = points[i].y
          const xj = points[j].x, yj = points[j].y
          
          if (((yi > point.y) !== (yj > point.y)) &&
              (point.x < (xj - xi) * (point.y - yi) / (yj - yi) + xi)) {
            inside = !inside
          }
        }
        isInside = inside
      }

      if (isInside) {
        indices.push(pointIndex)
      }
    })

    // Set the active gate and selected indices
    setActiveGate(gate.id)
    setSelectedIndices(indices)
    
    // Call the callback if provided
    if (onApplyGate) {
      onApplyGate(gate, indices)
    }
  }, [scatterData, setActiveGate, setSelectedIndices, onApplyGate])

  // Calculate statistics for selected population
  const { selectedStats, totalStats } = useMemo(() => {
    if (!scatterData || scatterData.length === 0) {
      return { selectedStats: null, totalStats: null }
    }

    const totalStats = calculateStats(scatterData)

    if (!selectedIndices || selectedIndices.length === 0) {
      return { selectedStats: null, totalStats }
    }

    const selectedSet = new Set(selectedIndices)
    const selectedData = scatterData.filter((p, idx) => {
      const pointIndex = p.index ?? idx
      return selectedSet.has(pointIndex)
    })

    const selectedStats = calculateStats(selectedData)
    if (selectedStats && totalStats) {
      selectedStats.percentage = (selectedData.length / scatterData.length) * 100
    }

    return { selectedStats, totalStats }
  }, [scatterData, selectedIndices])

  const hasSelection = selectedIndices.length > 0
  const hasGates = gatingState.gates.length > 0

  if (!hasSelection && !hasGates) {
    return (
      <Card className="border-dashed border-muted-foreground/30">
        <CardContent className="py-6">
          <div className="flex flex-col items-center justify-center text-center space-y-2">
            <div className="rounded-full bg-muted p-3">
              <Target className="h-6 w-6 text-muted-foreground" />
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-medium">No Population Selected</h4>
              <p className="text-xs text-muted-foreground max-w-[200px]">
                Use Box Select on the scatter plot to select a population region and view statistics
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  const handleExport = () => {
    if (onExportSelection && selectedIndices.length > 0) {
      onExportSelection(selectedIndices)
    }
  }

  return (
    <Card className="overflow-hidden">
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CardHeader className="pb-2 pt-3 px-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-primary" />
              <CardTitle className="text-sm font-semibold">Gated Population Statistics</CardTitle>
            </div>
            <div className="flex items-center gap-1">
              {hasSelection && (
                <Button 
                  variant="ghost" 
                  size="icon" 
                  className="h-7 w-7"
                  onClick={handleExport}
                  title="Export selected data"
                >
                  <Download className="h-3.5 w-3.5" />
                </Button>
              )}
              {hasGates && (
                <Button 
                  variant="ghost" 
                  size="icon" 
                  className="h-7 w-7 text-destructive"
                  onClick={clearAllGates}
                  title="Clear all gates"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              )}
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="icon" className="h-7 w-7">
                  {isExpanded ? (
                    <ChevronUp className="h-3.5 w-3.5" />
                  ) : (
                    <ChevronDown className="h-3.5 w-3.5" />
                  )}
                </Button>
              </CollapsibleTrigger>
            </div>
          </div>
        </CardHeader>

        <CollapsibleContent>
          <CardContent className="pt-0 pb-3 px-4 space-y-4">
            {/* Selection Summary */}
            {hasSelection && selectedStats && (
              <div className="rounded-lg bg-green-500/10 border border-green-500/30 p-3 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-green-600 hover:bg-green-700">
                      <Target className="h-3 w-3 mr-1" />
                      Selected
                    </Badge>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold text-green-600">
                      {selectedStats.count.toLocaleString()}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {selectedStats.percentage.toFixed(2)}% of total
                    </div>
                  </div>
                </div>

                {/* X-axis stats */}
                <div className="space-y-1">
                  <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                    {xLabel}
                  </div>
                  <div className="grid grid-cols-2 gap-x-4">
                    <StatRow label="Mean" value={selectedStats.xMean} />
                    <StatRow label="Median" value={selectedStats.xMedian} />
                    <StatRow label="Std Dev" value={selectedStats.xStd} />
                    <StatRow label="Range" value={selectedStats.xMax - selectedStats.xMin} />
                  </div>
                </div>

                {/* Y-axis stats */}
                <div className="space-y-1">
                  <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-purple-500"></span>
                    {yLabel}
                  </div>
                  <div className="grid grid-cols-2 gap-x-4">
                    <StatRow label="Mean" value={selectedStats.yMean} />
                    <StatRow label="Median" value={selectedStats.yMedian} />
                    <StatRow label="Std Dev" value={selectedStats.yStd} />
                    <StatRow label="Range" value={selectedStats.yMax - selectedStats.yMin} />
                  </div>
                </div>

                {/* Diameter stats if available */}
                {selectedStats.diameterMean !== undefined && (
                  <div className="space-y-1">
                    <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                      Diameter
                    </div>
                    <div className="grid grid-cols-2 gap-x-4">
                      <StatRow label="Mean" value={selectedStats.diameterMean} unit="nm" />
                      <StatRow label="Median" value={selectedStats.diameterMedian} unit="nm" />
                      <StatRow label="Std Dev" value={selectedStats.diameterStd} unit="nm" />
                      <StatRow label="Range" value={(selectedStats.diameterMax ?? 0) - (selectedStats.diameterMin ?? 0)} unit="nm" />
                    </div>
                  </div>
                )}

                {/* Server Analysis Section */}
                {sampleId && gateCoordinates && apiConnected && (
                  <div className="pt-2 border-t border-green-500/20">
                    {!serverAnalysis && !isAnalyzing && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full text-xs"
                        onClick={runServerAnalysis}
                      >
                        <Server className="h-3 w-3 mr-1.5" />
                        Analyze on Server (Mie Theory)
                      </Button>
                    )}
                    
                    {isAnalyzing && (
                      <div className="flex items-center justify-center py-2 text-xs text-muted-foreground">
                        <Loader2 className="h-3 w-3 mr-2 animate-spin" />
                        Computing full population statistics...
                      </div>
                    )}
                    
                    {analysisError && (
                      <Alert variant="destructive" className="py-2">
                        <AlertCircle className="h-3 w-3" />
                        <AlertDescription className="text-xs">{analysisError}</AlertDescription>
                      </Alert>
                    )}
                    
                    {serverAnalysis && serverAnalysis.percentiles && (
                      <div className="space-y-2 mt-2">
                        <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                          <Server className="h-3 w-3 text-blue-500" />
                          Server Analysis (D-Values)
                        </div>
                        <div className="grid grid-cols-3 gap-2">
                          <div className="rounded bg-blue-500/10 p-2 text-center">
                            <div className="text-lg font-bold text-blue-600">
                              {serverAnalysis.percentiles.D10.toFixed(0)}
                            </div>
                            <div className="text-xs text-muted-foreground">D10 nm</div>
                          </div>
                          <div className="rounded bg-green-500/10 p-2 text-center">
                            <div className="text-lg font-bold text-green-600">
                              {serverAnalysis.percentiles.D50.toFixed(0)}
                            </div>
                            <div className="text-xs text-muted-foreground">D50 nm</div>
                          </div>
                          <div className="rounded bg-purple-500/10 p-2 text-center">
                            <div className="text-lg font-bold text-purple-600">
                              {serverAnalysis.percentiles.D90.toFixed(0)}
                            </div>
                            <div className="text-xs text-muted-foreground">D90 nm</div>
                          </div>
                        </div>
                        {serverAnalysis.comparison_to_total && (
                          <div className="text-xs text-muted-foreground text-center pt-1">
                            {serverAnalysis.comparison_to_total.x_mean_diff_percent > 0 ? "+" : ""}
                            {serverAnalysis.comparison_to_total.x_mean_diff_percent.toFixed(1)}% vs total mean
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Total Population Summary */}
            {totalStats && (
              <div className="rounded-lg bg-muted/50 border border-border/50 p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">
                      <Layers className="h-3 w-3 mr-1" />
                      Total Population
                    </Badge>
                  </div>
                  <div className="text-right">
                    <div className="text-base font-semibold">
                      {totalStats.count.toLocaleString()}
                    </div>
                    <div className="text-xs text-muted-foreground">events</div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="space-y-0.5">
                    <div className="text-muted-foreground">{xLabel}</div>
                    <div className="font-mono">
                      {totalStats.xMin.toFixed(0)} - {totalStats.xMax.toFixed(0)}
                    </div>
                  </div>
                  <div className="space-y-0.5">
                    <div className="text-muted-foreground">{yLabel}</div>
                    <div className="font-mono">
                      {totalStats.yMin.toFixed(0)} - {totalStats.yMax.toFixed(0)}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Gate list */}
            {hasGates && gatingState.gates.length > 0 && (
              <div className="space-y-2">
                <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Saved Gates
                </div>
                {gatingState.gates.map((gate) => (
                  <div 
                    key={gate.id}
                    className={cn(
                      "flex items-center justify-between rounded-md border p-2",
                      gate.isActive && "border-primary bg-primary/5"
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <div 
                        className="w-3 h-3 rounded-sm" 
                        style={{ backgroundColor: gate.color }}
                      />
                      <span className="text-sm font-medium">{gate.name}</span>
                      <Badge variant="outline" className="text-xs capitalize">
                        {gate.shape.type}
                      </Badge>
                      {gate.isActive && (
                        <CheckCircle2 className="h-3 w-3 text-green-500" />
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className={cn(
                                "h-6 w-6",
                                gate.isActive 
                                  ? "text-green-500 hover:text-green-600" 
                                  : "text-muted-foreground hover:text-primary"
                              )}
                              onClick={() => handleApplyGate(gate)}
                            >
                              <Play className="h-3 w-3" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Apply gate to select matching events</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6 text-muted-foreground hover:text-destructive"
                              onClick={() => removeGate(gate.id)}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Delete gate</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
