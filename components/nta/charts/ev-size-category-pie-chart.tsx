"use client"

import { useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts"
import { PieChart as PieChartIcon, Target, Info } from "lucide-react"
import { Tooltip as UITooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import type { NTAResult } from "@/lib/api-client"

interface EVSizeCategoryPieChartProps {
  data: NTAResult
  className?: string
}

// Define the three main EV size categories based on ISEV guidelines
const SIZE_CATEGORIES = [
  {
    name: "Small EVs",
    description: "Exosomes and small microvesicles",
    range: "30-150 nm",
    minNm: 30,
    maxNm: 150,
    color: "#22c55e", // green
    gradient: ["#22c55e", "#16a34a"],
  },
  {
    name: "Medium EVs",
    description: "Microvesicles and larger EVs",
    range: "150-500 nm",
    minNm: 150,
    maxNm: 500,
    color: "#3b82f6", // blue
    gradient: ["#3b82f6", "#2563eb"],
  },
  {
    name: "Large EVs",
    description: "Large microvesicles and apoptotic bodies",
    range: "500+ nm",
    minNm: 500,
    maxNm: Infinity,
    color: "#a855f7", // purple
    gradient: ["#a855f7", "#9333ea"],
  },
]

// Calculate percentage for each category based on NTA results
function calculateCategoryPercentages(results: NTAResult) {
  // Use the bin percentages from NTA results if available
  const bin_50_80 = results.bin_50_80nm_pct || 0
  const bin_80_100 = results.bin_80_100nm_pct || 0
  const bin_100_120 = results.bin_100_120nm_pct || 0
  const bin_120_150 = results.bin_120_150nm_pct || 0
  const bin_150_200 = results.bin_150_200nm_pct || 0
  const bin_200_plus = results.bin_200_plus_pct || 0
  
  // Small EVs: 30-150nm (bins 50-80, 80-100, 100-120, 120-150)
  const smallEVsPct = bin_50_80 + bin_80_100 + bin_100_120 + bin_120_150
  
  // Medium EVs: 150-500nm (bins 150-200, partial 200+)
  // Estimate that about 60% of 200+ falls into 200-500 range
  const mediumEVsPct = bin_150_200 + (bin_200_plus * 0.6)
  
  // Large EVs: 500+nm (remaining of 200+)
  const largeEVsPct = bin_200_plus * 0.4
  
  // If no bin data available, estimate from d10/d50/d90
  if (smallEVsPct === 0 && mediumEVsPct === 0 && largeEVsPct === 0) {
    const median = results.median_size_nm || results.d50_nm || 120
    const d10 = results.d10_nm || median * 0.6
    const d90 = results.d90_nm || median * 1.6
    
    // Estimate distribution based on percentiles
    if (d90 < 150) {
      // All small EVs
      return { smallEVs: 95, mediumEVs: 4, largeEVs: 1 }
    } else if (d10 > 500) {
      // All large EVs
      return { smallEVs: 2, mediumEVs: 18, largeEVs: 80 }
    } else if (median < 150) {
      // Predominantly small EVs
      return { smallEVs: 70, mediumEVs: 25, largeEVs: 5 }
    } else if (median < 300) {
      // Mixed small/medium
      return { smallEVs: 35, mediumEVs: 55, largeEVs: 10 }
    } else {
      // Larger population
      return { smallEVs: 15, mediumEVs: 45, largeEVs: 40 }
    }
  }
  
  // Normalize to 100%
  const total = smallEVsPct + mediumEVsPct + largeEVsPct
  if (total === 0) {
    return { smallEVs: 33.3, mediumEVs: 33.3, largeEVs: 33.4 }
  }
  
  return {
    smallEVs: (smallEVsPct / total) * 100,
    mediumEVs: (mediumEVsPct / total) * 100,
    largeEVs: (largeEVsPct / total) * 100,
  }
}

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{
    name: string
    value: number
    payload: {
      name: string
      value: number
      description: string
      range: string
      count: number
    }
  }>
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null
  
  const data = payload[0].payload
  return (
    <div className="bg-background/95 border rounded-lg shadow-lg p-3 min-w-[180px]">
      <p className="font-semibold text-sm">{data.name}</p>
      <p className="text-xs text-muted-foreground mb-2">{data.description}</p>
      <div className="space-y-1 text-xs">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Size Range:</span>
          <span className="font-medium">{data.range}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Percentage:</span>
          <span className="font-medium">{data.value.toFixed(1)}%</span>
        </div>
        {data.count > 0 && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">Est. Count:</span>
            <span className="font-medium">{data.count.toLocaleString()}</span>
          </div>
        )}
      </div>
    </div>
  )
}

export function EVSizeCategoryPieChart({ data: results, className }: EVSizeCategoryPieChartProps) {
  const categoryData = useMemo(() => {
    const percentages = calculateCategoryPercentages(results)
    const totalParticles = results.total_particles || 0
    
    return [
      {
        name: SIZE_CATEGORIES[0].name,
        value: percentages.smallEVs,
        color: SIZE_CATEGORIES[0].color,
        description: SIZE_CATEGORIES[0].description,
        range: SIZE_CATEGORIES[0].range,
        count: Math.round(totalParticles * percentages.smallEVs / 100),
      },
      {
        name: SIZE_CATEGORIES[1].name,
        value: percentages.mediumEVs,
        color: SIZE_CATEGORIES[1].color,
        description: SIZE_CATEGORIES[1].description,
        range: SIZE_CATEGORIES[1].range,
        count: Math.round(totalParticles * percentages.mediumEVs / 100),
      },
      {
        name: SIZE_CATEGORIES[2].name,
        value: percentages.largeEVs,
        color: SIZE_CATEGORIES[2].color,
        description: SIZE_CATEGORIES[2].description,
        range: SIZE_CATEGORIES[2].range,
        count: Math.round(totalParticles * percentages.largeEVs / 100),
      },
    ].filter(d => d.value > 0.5) // Filter out very small slices
  }, [results])
  
  // Find dominant category
  const dominantCategory = categoryData.reduce((max, cat) => 
    cat.value > max.value ? cat : max
  , categoryData[0])

  return (
    <Card className={`card-3d ${className || ""}`}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-primary/10">
              <PieChartIcon className="h-4 w-4 text-primary" />
            </div>
            <CardTitle className="text-base">EV Size Categories</CardTitle>
            <TooltipProvider>
              <UITooltip>
                <TooltipTrigger asChild>
                  <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                </TooltipTrigger>
                <TooltipContent side="right" className="max-w-xs">
                  <p className="text-xs">
                    Classification based on ISEV 2018 guidelines: Small EVs (30-150nm) 
                    include exosomes, Medium EVs (150-500nm) include microvesicles, and 
                    Large EVs (500nm+) include apoptotic bodies.
                  </p>
                </TooltipContent>
              </UITooltip>
            </TooltipProvider>
          </div>
          <Badge variant="outline" className="gap-1">
            <Target className="h-3 w-3" />
            {dominantCategory.name}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground">
          Distribution by EV size classification (ISEV 2018)
        </p>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Pie Chart */}
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={3}
                  dataKey="value"
                  labelLine={false}
                  label={({ name, value }) => value > 5 ? `${value.toFixed(0)}%` : ''}
                >
                  {categoryData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={entry.color}
                      stroke={entry.color}
                      strokeWidth={2}
                    />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend 
                  verticalAlign="bottom"
                  height={36}
                  formatter={(value) => <span className="text-xs">{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          
          {/* Category Details */}
          <div className="space-y-3">
            {SIZE_CATEGORIES.map((cat, index) => {
              const catData = categoryData.find(d => d.name === cat.name)
              const percentage = catData?.value || 0
              const count = catData?.count || 0
              
              return (
                <div 
                  key={cat.name}
                  className="p-3 rounded-lg border transition-colors"
                  style={{ 
                    borderColor: `${cat.color}40`,
                    backgroundColor: `${cat.color}10`,
                  }}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <div 
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: cat.color }}
                      />
                      <span className="font-medium text-sm">{cat.name}</span>
                    </div>
                    <Badge variant="secondary" className="text-xs">
                      {percentage.toFixed(1)}%
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mb-2">{cat.description}</p>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Range:</span>
                    <span className="font-mono">{cat.range}</span>
                  </div>
                  {count > 0 && (
                    <div className="flex justify-between text-xs mt-1">
                      <span className="text-muted-foreground">Count:</span>
                      <span className="font-mono">{count.toLocaleString()}</span>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
        
        {/* Summary Footer */}
        <div className="mt-4 pt-3 border-t text-xs text-muted-foreground">
          <strong>Interpretation:</strong> The dominant population is{" "}
          <span className="font-medium" style={{ color: dominantCategory.color }}>
            {dominantCategory.name}
          </span>{" "}
          ({dominantCategory.value.toFixed(1)}%), which corresponds to{" "}
          {dominantCategory.name === "Small EVs" && "exosomes and small microvesicles"}
          {dominantCategory.name === "Medium EVs" && "microvesicles and larger extracellular vesicles"}
          {dominantCategory.name === "Large EVs" && "large microvesicles and apoptotic bodies"}.
        </div>
      </CardContent>
    </Card>
  )
}
