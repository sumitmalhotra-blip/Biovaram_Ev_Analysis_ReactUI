"use client"

import { useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  Cell,
  LabelList,
} from "recharts"
import { BarChart3, Target, Info } from "lucide-react"
import { Tooltip as UITooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import type { NTAResult } from "@/lib/api-client"
import type { NTASizeBin } from "@/lib/store"
import { computeEVCategoryPercentagesFromBins, computeNTABinsForProfile } from "@/lib/nta-size-profiles"

interface EVSizeCategoryBarChartProps {
  data: NTAResult
  bins?: NTASizeBin[]
  className?: string
}

// Define the three main EV size categories based on ISEV guidelines
const SIZE_CATEGORIES = [
  {
    name: "Small EVs",
    shortName: "Small",
    description: "Exosomes & small microvesicles",
    range: "30–150 nm",
    minNm: 30,
    maxNm: 150,
    color: "#22c55e",
  },
  {
    name: "Medium EVs",
    shortName: "Medium",
    description: "Microvesicles & larger EVs",
    range: "150–500 nm",
    minNm: 150,
    maxNm: 500,
    color: "#3b82f6",
  },
  {
    name: "Large EVs",
    shortName: "Large",
    description: "Large microvesicles & apoptotic bodies",
    range: "500+ nm",
    minNm: 500,
    maxNm: Infinity,
    color: "#a855f7",
  },
]

// Calculate percentage for each category based on NTA results
function calculateCategoryPercentages(results: NTAResult) {
  const bin_50_80 = results.bin_50_80nm_pct || 0
  const bin_80_100 = results.bin_80_100nm_pct || 0
  const bin_100_120 = results.bin_100_120nm_pct || 0
  const bin_120_150 = results.bin_120_150nm_pct || 0
  const bin_150_200 = results.bin_150_200nm_pct || 0
  const bin_200_plus = results.bin_200_plus_pct || 0

  // Small EVs: 30-150nm
  const smallEVsPct = bin_50_80 + bin_80_100 + bin_100_120 + bin_120_150

  // Medium EVs: 150-500nm
  const mediumEVsPct = bin_150_200 + bin_200_plus * 0.6

  // Large EVs: 500+nm
  const largeEVsPct = bin_200_plus * 0.4

  // If no bin data, estimate from percentiles
  if (smallEVsPct === 0 && mediumEVsPct === 0 && largeEVsPct === 0) {
    const median = results.median_size_nm || results.d50_nm || 120
    const d90 = results.d90_nm || median * 1.6
    const d10 = results.d10_nm || median * 0.6

    if (d90 < 150) return { smallEVs: 95, mediumEVs: 4, largeEVs: 1 }
    if (d10 > 500) return { smallEVs: 2, mediumEVs: 18, largeEVs: 80 }
    if (median < 150) return { smallEVs: 70, mediumEVs: 25, largeEVs: 5 }
    if (median < 300) return { smallEVs: 35, mediumEVs: 55, largeEVs: 10 }
    return { smallEVs: 15, mediumEVs: 45, largeEVs: 40 }
  }

  const total = smallEVsPct + mediumEVsPct + largeEVsPct
  if (total === 0) return { smallEVs: 33.3, mediumEVs: 33.3, largeEVs: 33.4 }

  return {
    smallEVs: (smallEVsPct / total) * 100,
    mediumEVs: (mediumEVsPct / total) * 100,
    largeEVs: (largeEVsPct / total) * 100,
  }
}

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{
    value: number
    payload: {
      name: string
      value: number
      description: string
      range: string
      count: number
      color: string
    }
  }>
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null

  const d = payload[0].payload
  return (
    <div className="bg-background/95 border rounded-lg shadow-lg p-3 min-w-45">
      <p className="font-semibold text-sm" style={{ color: d.color }}>
        {d.name}
      </p>
      <p className="text-xs text-muted-foreground mb-2">{d.description}</p>
      <div className="space-y-1 text-xs">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Size Range:</span>
          <span className="font-medium">{d.range}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Percentage:</span>
          <span className="font-medium">{d.value.toFixed(1)}%</span>
        </div>
        {d.count > 0 && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">Est. Count:</span>
            <span className="font-medium">{d.count.toLocaleString()}</span>
          </div>
        )}
      </div>
    </div>
  )
}

export function EVSizeCategoryBarChart({ data: results, bins, className }: EVSizeCategoryBarChartProps) {
  const categoryData = useMemo(() => {
    const percentages = bins && bins.length > 0
      ? computeEVCategoryPercentagesFromBins(computeNTABinsForProfile(results, bins))
      : calculateCategoryPercentages(results)
    const totalParticles = results.total_particles || 0

    return [
      {
        name: SIZE_CATEGORIES[0].name,
        shortName: SIZE_CATEGORIES[0].shortName,
        value: percentages.smallEVs,
        color: SIZE_CATEGORIES[0].color,
        description: SIZE_CATEGORIES[0].description,
        range: SIZE_CATEGORIES[0].range,
        count: Math.round((totalParticles * percentages.smallEVs) / 100),
      },
      {
        name: SIZE_CATEGORIES[1].name,
        shortName: SIZE_CATEGORIES[1].shortName,
        value: percentages.mediumEVs,
        color: SIZE_CATEGORIES[1].color,
        description: SIZE_CATEGORIES[1].description,
        range: SIZE_CATEGORIES[1].range,
        count: Math.round((totalParticles * percentages.mediumEVs) / 100),
      },
      {
        name: SIZE_CATEGORIES[2].name,
        shortName: SIZE_CATEGORIES[2].shortName,
        value: percentages.largeEVs,
        color: SIZE_CATEGORIES[2].color,
        description: SIZE_CATEGORIES[2].description,
        range: SIZE_CATEGORIES[2].range,
        count: Math.round((totalParticles * percentages.largeEVs) / 100),
      },
    ]
  }, [results])

  // Find dominant category
  const dominantCategory = categoryData.reduce(
    (max, cat) => (cat.value > max.value ? cat : max),
    categoryData[0]
  )

  return (
    <Card className={`card-3d ${className || ""}`}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-primary/10">
              <BarChart3 className="h-4 w-4 text-primary" />
            </div>
            <CardTitle className="text-base">EV Size Categories</CardTitle>
            <TooltipProvider>
              <UITooltip>
                <TooltipTrigger asChild>
                  <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                </TooltipTrigger>
                <TooltipContent side="right" className="max-w-xs">
                  <p className="text-xs">
                    Classification based on ISEV 2018 guidelines: Small EVs (30–150nm)
                    include exosomes, Medium EVs (150–500nm) include microvesicles, and
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
        {/* Bar Chart */}
        <div className="h-64 mb-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={categoryData}
              margin={{ top: 20, right: 20, left: 10, bottom: 5 }}
              barCategoryGap="25%"
            >
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                axisLine={{ stroke: "hsl(var(--border))" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `${v}%`}
                domain={[0, "auto"]}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: "hsl(var(--muted))", opacity: 0.3 }} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={80}>
                {categoryData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
                <LabelList
                  dataKey="value"
                  position="top"
                  formatter={((v: unknown) => `${Number(v).toFixed(1)}%`) as never}
                  style={{ fontSize: 12, fontWeight: 600, fill: "hsl(var(--foreground))" }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Category Legend Cards */}
        <div className="grid grid-cols-3 gap-2">
          {SIZE_CATEGORIES.map((cat) => {
            const catData = categoryData.find((d) => d.name === cat.name)
            const percentage = catData?.value || 0
            const count = catData?.count || 0

            return (
              <div
                key={cat.name}
                className="p-2.5 rounded-lg border transition-colors text-center"
                style={{
                  borderColor: `${cat.color}40`,
                  backgroundColor: `${cat.color}10`,
                }}
              >
                <div className="flex items-center justify-center gap-1.5 mb-1">
                  <div
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: cat.color }}
                  />
                  <span className="font-medium text-xs">{cat.shortName}</span>
                </div>
                <div className="text-lg font-bold" style={{ color: cat.color }}>
                  {percentage.toFixed(1)}%
                </div>
                <p className="text-[10px] text-muted-foreground">{cat.range}</p>
                {count > 0 && (
                  <p className="text-[10px] text-muted-foreground font-mono mt-0.5">
                    ~{count.toLocaleString()}
                  </p>
                )}
              </div>
            )
          })}
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
