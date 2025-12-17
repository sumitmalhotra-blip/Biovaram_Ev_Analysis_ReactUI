"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Sparkles, Circle } from "lucide-react"
import { cn } from "@/lib/utils"

interface SizeCategoryData {
  name: string
  range: string
  count: number
  percentage: number
  color: string
  bgColor: string
  borderColor: string
  description: string
  icon: string
}

interface ParticleSizeVisualizationProps {
  totalEvents: number
  medianSize?: number
  sizeCategories?: {
    small: number
    medium: number
    large: number
  }
}

export function ParticleSizeVisualization({
  totalEvents,
  medianSize,
  sizeCategories,
}: ParticleSizeVisualizationProps) {
  // Use provided data or calculate defaults
  const smallCount = sizeCategories?.small ?? Math.floor(totalEvents * 0.15)
  const mediumCount = sizeCategories?.medium ?? Math.floor(totalEvents * 0.70)
  const largeCount = sizeCategories?.large ?? Math.floor(totalEvents * 0.15)

  const totalCounted = smallCount + mediumCount + largeCount
  const smallPct = (smallCount / totalCounted) * 100
  const mediumPct = (mediumCount / totalCounted) * 100
  const largePct = (largeCount / totalCounted) * 100

  const categories: SizeCategoryData[] = [
    {
      name: "Small Particles",
      range: "< 50 nm",
      count: smallCount,
      percentage: smallPct,
      color: "text-cyan-400",
      bgColor: "bg-cyan-500/20",
      borderColor: "border-cyan-500/50",
      description: "Small EVs, exomeres, protein aggregates",
      icon: "⚫",
    },
    {
      name: "Medium Particles",
      range: "50-200 nm",
      count: mediumCount,
      percentage: mediumPct,
      color: "text-purple-400",
      bgColor: "bg-purple-500/20",
      borderColor: "border-purple-500/50",
      description: "Exosomes, classic EV size range",
      icon: "⚫",
    },
    {
      name: "Large Particles",
      range: "> 200 nm",
      count: largeCount,
      percentage: largePct,
      color: "text-amber-400",
      bgColor: "bg-amber-500/20",
      borderColor: "border-amber-500/50",
      description: "Microvesicles, large EVs, apoptotic bodies",
      icon: "⚫",
    },
  ]

  // Determine dominant population
  const dominantCategory = categories.reduce((prev, current) =>
    current.percentage > prev.percentage ? current : prev
  )

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
          <div className="text-sm font-medium text-muted-foreground mb-3">Size Category Breakdown</div>

          {/* Visual Circles showing relative sizes */}
          <div className="flex items-end justify-center gap-6 h-32 p-4 rounded-lg bg-linear-to-b from-secondary/50 to-transparent border">
            {categories.map((category, idx) => {
              const sizes = [32, 56, 80] // Small, Medium, Large visual sizes
              const size = sizes[idx]
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
                    <span className={cn("text-xs", category.color)}>{category.percentage.toFixed(0)}%</span>
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
                    <span className={cn("text-2xl", category.color)}>{category.icon}</span>
                    <span className={cn("font-semibold", category.color)}>{category.name}</span>
                    <Badge variant="outline" className="text-xs">
                      {category.range}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">{category.description}</p>
                </div>
                <div className="text-right">
                  <div className={cn("text-2xl font-bold", category.color)}>{category.percentage.toFixed(1)}%</div>
                  <div className="text-xs text-muted-foreground">{category.count.toLocaleString()} events</div>
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
            {dominantCategory.name.includes("Medium") ? "typical" : "noteworthy"} for EV preparations.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
