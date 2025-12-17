"use client"

import { useState, useMemo } from "react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
  Brush,
} from "recharts"
import { InteractiveChartWrapper, EnhancedChartTooltip } from "@/components/charts/interactive-chart-wrapper"
import { CHART_COLORS } from "@/lib/store"
import { useAnalysisStore, type SizeRange } from "@/lib/store"

interface SizeDistributionChartProps {
  data?: Array<{
    size: number
    smallEV?: number
    exosomes?: number
    largeEV?: number
    total?: number
  }>
  showControls?: boolean
  showBrush?: boolean
  d10?: number
  d50?: number
  d90?: number
  height?: number
  compact?: boolean
  binCount?: number  // TASK-019: Configurable bin count
  // Raw size data for dynamic range calculation
  sizeData?: number[]
}

// Generate sample histogram data with configurable bins and dynamic ranges
// TASK-019: Support configurable histogram bin size
// Now supports dynamic size ranges from store
const generateHistogramData = (
  binCount: number = 20, 
  sizeRanges?: SizeRange[],
  sizeData?: number[]
) => {
  const data = []
  const maxSize = 500
  const binWidth = maxSize / binCount
  
  // Default ranges if none provided
  const ranges = sizeRanges?.length ? sizeRanges : [
    { name: "Small EVs", min: 30, max: 100, color: "#22c55e" },
    { name: "Medium EVs", min: 100, max: 200, color: "#7c3aed" },
    { name: "Large EVs", min: 200, max: 500, color: "#f59e0b" },
  ]
  
  for (let i = 0; i < binCount; i++) {
    const binStart = i * binWidth
    const binEnd = (i + 1) * binWidth
    const size = Math.round(binStart + binWidth / 2)
    
    // If we have actual size data, calculate real counts
    if (sizeData && sizeData.length > 0) {
      const binData: Record<string, number | string> = { size }
      let totalCount = 0
      
      // Count particles in this bin for each size range
      ranges.forEach((range, idx) => {
        const count = sizeData.filter(s => 
          s >= binStart && s < binEnd && s >= range.min && s <= range.max
        ).length
        binData[`range${idx}`] = count
        totalCount += count
      })
      
      binData.total = totalCount
      data.push(binData)
    } else {
      // Generate sample data
      let count = 0
      // Small EVs peak around 30-40nm
      count += Math.max(0, 800 * Math.exp(-Math.pow((size - 35) / 20, 2)))
      // Exosomes peak around 100-150nm
      count += Math.max(0, 2000 * Math.exp(-Math.pow((size - 120) / 50, 2)))
      // Large EVs peak around 250-300nm
      count += Math.max(0, 600 * Math.exp(-Math.pow((size - 280) / 80, 2)))

      const binData: Record<string, number | string> = { size, total: Math.round(count * (0.3 + Math.random() * 0.2)) }
      
      // Distribute count among ranges based on bin position
      ranges.forEach((range, idx) => {
        if (size >= range.min && size <= range.max) {
          binData[`range${idx}`] = Math.round(count * 0.7)
        } else {
          binData[`range${idx}`] = 0
        }
      })
      
      data.push(binData)
    }
  }
  return data
}

// Custom tooltip
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload || !payload.length) return null

  const total = payload.reduce((sum: number, entry: any) => sum + (entry.value || 0), 0)

  return (
    <div className="bg-background/95 backdrop-blur-sm border border-border rounded-lg p-3 shadow-lg">
      <p className="font-semibold text-sm mb-2 border-b pb-1">{label} nm</p>
      <div className="space-y-1.5">
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center justify-between gap-4 text-xs">
            <span className="flex items-center gap-1.5">
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-muted-foreground">{entry.name}:</span>
            </span>
            <span className="font-medium tabular-nums">{entry.value?.toLocaleString()}</span>
          </div>
        ))}
        <div className="flex items-center justify-between gap-4 text-xs border-t pt-1 mt-1">
          <span className="text-muted-foreground">Total:</span>
          <span className="font-bold tabular-nums">{total.toLocaleString()}</span>
        </div>
      </div>
    </div>
  )
}

export function SizeDistributionChart({ 
  data: propData,
  showControls = true,
  showBrush = false,
  d10 = 89,
  d50 = 127,
  d90 = 198,
  height = 320,
  compact = false,
  binCount: propBinCount,
  sizeData,
}: SizeDistributionChartProps) {
  // TASK-019: Get histogram bins from store settings
  // Also get dynamic size ranges from store
  const { fcsAnalysisSettings, fcsAnalysis } = useAnalysisStore()
  const binCount = propBinCount ?? fcsAnalysisSettings?.histogramBins ?? 20
  const sizeRanges = fcsAnalysis.sizeRanges
  
  // Generate data using dynamic size ranges
  const data = useMemo(() => {
    if (propData) return propData
    return generateHistogramData(binCount, sizeRanges, sizeData)
  }, [propData, binCount, sizeRanges, sizeData])
  
  // Get range colors for bars
  const rangeColors = useMemo(() => {
    if (!sizeRanges?.length) return [CHART_COLORS.smallEV, CHART_COLORS.primary, CHART_COLORS.largeEV]
    return sizeRanges.map(r => r.color || CHART_COLORS.primary)
  }, [sizeRanges])
  
  const rangeNames = useMemo(() => {
    if (!sizeRanges?.length) return ["Small EVs (<100nm)", "Exosomes (100-200nm)", "Large EVs (>200nm)"]
    return sizeRanges.map(r => `${r.name} (${r.min}-${r.max}nm)`)
  }, [sizeRanges])
  
  const [brushDomain, setBrushDomain] = useState<{ startIndex?: number; endIndex?: number }>({})

  return (
    <InteractiveChartWrapper
      title="Size Distribution"
      source="FCS Analysis"
      chartType="histogram"
      showControls={showControls && !compact}
      height={height}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} barCategoryGap={0}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="size"
            stroke="#64748b"
            tick={{ fontSize: 11 }}
            label={{ value: "Diameter (nm)", position: "bottom", offset: -5, fill: "#64748b", fontSize: 12 }}
          />
          <YAxis
            stroke="#64748b"
            tick={{ fontSize: 11 }}
            label={{ value: "Count", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 12 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: "12px" }} />
          
          {/* Dynamic bars based on size ranges from store */}
          {sizeRanges?.length ? (
            sizeRanges.map((range, idx) => (
              <Bar 
                key={range.name}
                dataKey={`range${idx}`} 
                stackId="a" 
                fill={range.color || rangeColors[idx]} 
                name={rangeNames[idx]} 
                radius={idx === sizeRanges.length - 1 ? [2, 2, 0, 0] : [0, 0, 0, 0]} 
              />
            ))
          ) : (
            <>
              {/* Default bars if no custom ranges */}
              <Bar dataKey="range0" stackId="a" fill={CHART_COLORS.smallEV} name="Small EVs (<100nm)" radius={[0, 0, 0, 0]} />
              <Bar dataKey="range1" stackId="a" fill={CHART_COLORS.primary} name="Exosomes (100-200nm)" radius={[0, 0, 0, 0]} />
              <Bar dataKey="range2" stackId="a" fill={CHART_COLORS.largeEV} name="Large EVs (>200nm)" radius={[2, 2, 0, 0]} />
            </>
          )}

          {/* Percentile lines */}
          <ReferenceLine
            x={d10}
            stroke="#10b981"
            strokeDasharray="5 5"
            label={{ value: "D10", fill: "#10b981", fontSize: 10 }}
          />
          <ReferenceLine
            x={d50}
            stroke="#10b981"
            strokeDasharray="5 5"
            label={{ value: "D50", fill: "#10b981", fontSize: 10 }}
          />
          <ReferenceLine
            x={d90}
            stroke="#10b981"
            strokeDasharray="5 5"
            label={{ value: "D90", fill: "#10b981", fontSize: 10 }}
          />

          {/* Brush for range selection */}
          {showBrush && (
            <Brush
              dataKey="size"
              height={30}
              stroke="hsl(var(--primary))"
              fill="hsl(var(--primary) / 0.1)"
              tickFormatter={(value) => `${value}nm`}
            />
          )}
        </BarChart>
      </ResponsiveContainer>
    </InteractiveChartWrapper>
  )
}
