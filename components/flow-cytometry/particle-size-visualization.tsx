"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"
import { useAnalysisStore, type SizeRange } from "@/lib/store"
import { useMemo } from "react"
import { type ScatterDataPoint } from "./charts/scatter-plot-with-selection"

interface SizeCategoryData {
  name: string
  range: string
  min: number
  max: number
  count: number
  percentage: number
  color: string
  bgColor: string
  borderColor: string
  description: string
}

interface ParticleSizeVisualizationProps {
  totalEvents: number
  medianSize?: number
  // Scatter data with diameter values for calculating custom bins
  scatterData?: ScatterDataPoint[]
  // Legacy: custom bins from reanalyze endpoint
  customBins?: Record<string, number>
}

// Generate color classes from hex color
function getColorClasses(hexColor: string): { text: string; bg: string; border: string } {
  // Map common colors to Tailwind classes
  const colorMap: Record<string, { text: string; bg: string; border: string }> = {
    "#22c55e": { text: "text-green-400", bg: "bg-green-500/20", border: "border-green-500/50" },
    "#3b82f6": { text: "text-blue-400", bg: "bg-blue-500/20", border: "border-blue-500/50" },
    "#a855f7": { text: "text-purple-400", bg: "bg-purple-500/20", border: "border-purple-500/50" },
    "#f59e0b": { text: "text-amber-400", bg: "bg-amber-500/20", border: "border-amber-500/50" },
    "#ef4444": { text: "text-red-400", bg: "bg-red-500/20", border: "border-red-500/50" },
    "#06b6d4": { text: "text-cyan-400", bg: "bg-cyan-500/20", border: "border-cyan-500/50" },
    "#8b5cf6": { text: "text-violet-400", bg: "bg-violet-500/20", border: "border-violet-500/50" },
    "#ec4899": { text: "text-pink-400", bg: "bg-pink-500/20", border: "border-pink-500/50" },
  }
  
  // Find closest match or use default
  return colorMap[hexColor] || { text: "text-primary", bg: "bg-primary/20", border: "border-primary/50" }
}

// Get description based on size range
function getRangeDescription(min: number, max: number): string {
  if (max <= 50) return "Exomeres, small EVs, protein aggregates"
  if (min >= 30 && max <= 100) return "Small EVs, exomeres"
  if (min >= 50 && max <= 150) return "Small exosomes"
  if (min >= 100 && max <= 200) return "Exosomes, classic EV size range"
  if (min >= 200 && max <= 500) return "Microvesicles, large EVs"
  if (min >= 500) return "Large microvesicles, apoptotic bodies"
  return "Extracellular vesicles"
}

export function ParticleSizeVisualization({
  totalEvents,
  medianSize,
  scatterData,
  customBins,
}: ParticleSizeVisualizationProps) {
  const { fcsAnalysis } = useAnalysisStore()
  
  // Get custom size ranges from the store
  const sizeRanges = fcsAnalysis.sizeRanges
  
  // Calculate bin counts from scatter data (which already has diameter values)
  const calculatedBins = useMemo(() => {
    if (!sizeRanges || sizeRanges.length === 0 || !scatterData || scatterData.length === 0) {
      console.log('[ParticleSizeViz] Missing data:', { 
        sizeRanges: sizeRanges?.length || 0, 
        scatterData: scatterData?.length || 0 
      })
      return {}
    }
    
    // Get valid diameters from scatter data
    const validSizes = scatterData
      .filter((p) => p.diameter !== undefined && p.diameter !== null && p.diameter > 0)
      .map((p) => p.diameter as number)
    
    console.log('[ParticleSizeViz] Valid sizes from scatter data:', {
      totalScatterPoints: scatterData.length,
      validSizeCount: validSizes.length,
      sampleDiameters: validSizes.slice(0, 10),
      sizeRanges: sizeRanges.map(r => `${r.name}: ${r.min}-${r.max}`)
    })
    
    if (validSizes.length === 0) {
      console.log('[ParticleSizeViz] No valid sizes found in scatter data')
      return {}
    }
    
    // Calculate counts for each custom range
    const bins: Record<string, number> = {}
    
    sizeRanges.forEach((range) => {
      const count = validSizes.filter(
        (size) => size >= range.min && size < range.max
      ).length
      bins[range.name] = count
    })
    
    // Scale to full dataset (scatter data is sampled)
    // Use validSizes.length for accurate scaling (not all scatter points have diameters)
    const scaleFactor = totalEvents / Math.max(scatterData.length, 1)
    Object.keys(bins).forEach(key => {
      bins[key] = Math.round(bins[key] * scaleFactor)
    })
    
    console.log('[ParticleSizeViz] Calculated bins:', bins, 'scaleFactor:', scaleFactor)
    
    return bins
  }, [sizeRanges, scatterData, totalEvents])
  
  // Build categories from custom ranges (always use store's sizeRanges)
  const categories: SizeCategoryData[] = useMemo(() => {
    // Default ranges if store doesn't have any
    const ranges = (sizeRanges && sizeRanges.length > 0) ? sizeRanges : [
      { name: "Small EVs", min: 30, max: 100, color: "#22c55e" },
      { name: "Medium EVs", min: 100, max: 200, color: "#3b82f6" },
      { name: "Large EVs", min: 200, max: 500, color: "#a855f7" },
    ]
    
    // Use calculated bins if available
    const bins = Object.keys(calculatedBins).length > 0 ? calculatedBins : customBins || {}
    
    // Calculate total for percentages - use sum of bins or totalEvents
    const totalInBins = Object.values(bins).reduce((sum, count) => sum + count, 0)
    const percentageBase = totalInBins > 0 ? totalInBins : totalEvents
    
    return ranges.map((range) => {
      const count = bins[range.name] || 0
      const colorClasses = getColorClasses(range.color || "#3b82f6")
      
      return {
        name: range.name,
        range: `${range.min}-${range.max} nm`,
        min: range.min,
        max: range.max,
        count: count,
        percentage: percentageBase > 0 ? (count / percentageBase) * 100 : 0,
        color: colorClasses.text,
        bgColor: colorClasses.bg,
        borderColor: colorClasses.border,
        description: getRangeDescription(range.min, range.max),
      }
    })
  }, [sizeRanges, totalEvents, calculatedBins, customBins])

  // Determine dominant population
  const dominantCategory = useMemo(() => {
    return categories.reduce((prev, current) =>
      current.percentage > prev.percentage ? current : prev
    )
  }, [categories])

  // Calculate circle sizes proportionally
  const maxCircleSize = 80
  const minCircleSize = 32
  const maxPercentage = Math.max(...categories.map(c => c.percentage), 1)
  
  const getCircleSize = (percentage: number): number => {
    const ratio = percentage / maxPercentage
    return minCircleSize + (maxCircleSize - minCircleSize) * ratio
  }

  return (
    <Card className="card-3d overflow-hidden">
      <CardHeader className="pb-3 bg-linear-to-r from-primary/5 to-accent/5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-linear-to-br from-primary/20 to-accent/20 flex items-center justify-center">
              <Sparkles className="h-4 w-4 text-primary" />
            </div>
            <CardTitle className="text-base md:text-lg">Particle Size Distribution</CardTitle>
          </div>
          <Badge variant="outline" className={cn("font-semibold", dominantCategory.color, dominantCategory.bgColor)}>
            {dominantCategory.name}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-4 space-y-4">
        {/* Summary Stats */}
        <div className="grid grid-cols-2 gap-3 rounded-lg border bg-secondary/30 p-3">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Total Events</div>
            <div className="text-lg font-bold">{totalEvents.toLocaleString()}</div>
          </div>
          {medianSize && (
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Median Size</div>
              <div className="text-lg font-bold">{medianSize.toFixed(1)} nm</div>
            </div>
          )}
        </div>

        {/* Visual Size Representation */}
        <div className="space-y-2">
          <div className="text-sm font-medium text-muted-foreground mb-3">
            Size Category Breakdown
          </div>

          {/* Show warning if no diameter data available */}
          {Object.keys(calculatedBins).length === 0 && (
            <div className="text-center p-4 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-600 text-sm mb-4">
              <p className="font-medium">Size data not yet calculated</p>
              <p className="text-xs text-muted-foreground mt-1">
                Waiting for Mie theory calculations from FCS data...
              </p>
            </div>
          )}

          {/* Visual Circles showing relative sizes */}
          <div className="flex items-end justify-center gap-4 flex-wrap min-h-32 p-4 rounded-lg bg-linear-to-b from-secondary/50 to-transparent border">
            {categories.map((category) => {
              const size = getCircleSize(category.percentage)
              return (
                <div key={category.name} className="flex flex-col items-center gap-2">
                  <div
                    className={cn(
                      "rounded-full flex items-center justify-center font-bold transition-transform hover:scale-110",
                      category.bgColor,
                      category.borderColor,
                      "border-2"
                    )}
                    style={{
                      width: `${size}px`,
                      height: `${size}px`,
                    }}
                  >
                    <span className={cn("text-xs", category.color)}>
                      {category.percentage.toFixed(0)}%
                    </span>
                  </div>
                  <div className="text-xs text-center">
                    <div className={cn("font-medium", category.color)}>{category.range}</div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Detailed Category Cards */}
        <div className="space-y-3">
          {categories.map((category) => (
            <div
              key={category.name}
              className={cn(
                "group relative rounded-lg border p-4 transition-all hover:shadow-md",
                category.borderColor,
                category.bgColor
              )}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span 
                      className="w-4 h-4 rounded-full" 
                      style={{ backgroundColor: sizeRanges?.find(r => r.name === category.name)?.color || undefined }}
                    />
                    <span className={cn("font-semibold", category.color)}>{category.name}</span>
                    <Badge variant="outline" className="text-xs">
                      {category.range}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">{category.description}</p>
                </div>
                <div className="text-right">
                  <div className={cn("text-2xl font-bold", category.color)}>
                    {category.percentage.toFixed(1)}%
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {category.count.toLocaleString()} events
                  </div>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="space-y-1">
                <Progress value={category.percentage} className={cn("h-2", category.bgColor)} />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>0%</span>
                  <span>100%</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Summary Note */}
        <div className="rounded-lg bg-primary/5 border border-primary/20 p-3 text-xs">
          <p className="text-muted-foreground">
            <strong className="text-foreground">Analysis:</strong> Your sample shows a{" "}
            <span className={cn("font-semibold", dominantCategory.color)}>
              {dominantCategory.name.toLowerCase()}
            </span>{" "}
            dominant profile ({dominantCategory.percentage.toFixed(1)}%). This is{" "}
            {dominantCategory.name.toLowerCase().includes("medium") || dominantCategory.name.toLowerCase().includes("exosome") 
              ? "typical" 
              : "noteworthy"} for EV preparations.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
