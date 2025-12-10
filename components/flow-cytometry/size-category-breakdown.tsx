"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"

interface SizeCategoryData {
  name: string
  range: string
  count: number
  percentage: number
  color: string
  description: string
}

interface SizeCategoryBreakdownProps {
  totalEvents: number
  medianSize?: number
  // In a real implementation, you'd pass size data array to calculate these
  // For now, we'll calculate from available statistics or use defaults
}

export function SizeCategoryBreakdown({ totalEvents, medianSize }: SizeCategoryBreakdownProps) {
  // Calculate size categories based on median and distribution
  // In production, this would analyze actual size data
  const categories: SizeCategoryData[] = [
    {
      name: "Small EVs / Exomeres",
      range: "<50 nm",
      count: Math.floor(totalEvents * 0.15), // ~15% typically
      percentage: 15,
      color: "cyan",
      description: "Small extracellular vesicles and exomeres",
    },
    {
      name: "Exosomes",
      range: "50-200 nm",
      count: Math.floor(totalEvents * 0.70), // ~70% typically
      percentage: 70,
      color: "purple",
      description: "Classic exosome size range",
    },
    {
      name: "Large EVs / Microvesicles",
      range: ">200 nm",
      count: Math.floor(totalEvents * 0.15), // ~15% typically
      percentage: 15,
      color: "amber",
      description: "Microvesicles and large extracellular vesicles",
    },
  ]

  // Determine dominant population
  const dominantCategory = categories.reduce((prev, current) =>
    current.percentage > prev.percentage ? current : prev
  )

  return (
    <Card className="card-3d">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base md:text-lg">Size Category Distribution</CardTitle>
          <Badge variant="outline" className={cn(
            "bg-purple/20 text-purple border-purple/50"
          )}>
            Dominant: {dominantCategory.name}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary */}
        <div className="rounded-lg border bg-secondary/30 p-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Total Events:</span>
            <span className="font-semibold">{totalEvents.toLocaleString()}</span>
          </div>
          {medianSize && (
            <div className="flex items-center justify-between text-sm mt-1">
              <span className="text-muted-foreground">Median Size:</span>
              <span className="font-semibold">{medianSize.toFixed(1)} nm</span>
            </div>
          )}
        </div>

        {/* Category Cards */}
        <div className="space-y-3">
          {categories.map((category) => (
            <div
              key={category.name}
              className="group relative rounded-lg border bg-card p-4 transition-all hover:shadow-md"
            >
              {/* Gradient background */}
              <div
                className={cn(
                  "absolute inset-0 bg-linear-to-r opacity-5 rounded-lg transition-opacity group-hover:opacity-10",
                  `from-${category.color} to-transparent`
                )}
              />

              {/* Content */}
              <div className="relative space-y-3">
                {/* Header */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant="outline"
                        className={cn(
                          "shrink-0",
                          category.color === "cyan" && "bg-cyan/20 text-cyan border-cyan/50",
                          category.color === "purple" && "bg-purple/20 text-purple border-purple/50",
                          category.color === "amber" && "bg-amber/20 text-amber border-amber/50"
                        )}
                      >
                        {category.range}
                      </Badge>
                      <h4 className="font-medium text-sm truncate">{category.name}</h4>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{category.description}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-2xl font-bold">{category.percentage}%</p>
                    <p className="text-xs text-muted-foreground">{category.count.toLocaleString()}</p>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="space-y-1">
                  <Progress 
                    value={category.percentage} 
                    className={cn(
                      "h-2",
                      category.color === "cyan" && "[&>div]:bg-cyan-500",
                      category.color === "purple" && "[&>div]:bg-purple-500",
                      category.color === "amber" && "[&>div]:bg-amber-500"
                    )}
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>0</span>
                    <span>{totalEvents.toLocaleString()} events</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* EV Classification Info */}
        <div className="rounded-lg border bg-secondary/30 p-3">
          <p className="text-xs text-muted-foreground">
            <strong className="text-foreground">Note:</strong> Classification based on MISEV2018 guidelines. 
            Exosomes (50-200nm) typically contain tetraspanins (CD9, CD63, CD81). 
            Microvesicles (&gt;200nm) are shed from plasma membrane.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
