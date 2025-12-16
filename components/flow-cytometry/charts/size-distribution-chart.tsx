"use client"

import { useState } from "react"
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
}

// Generate sample histogram data
const generateHistogramData = () => {
  const data = []
  for (let size = 0; size <= 500; size += 20) {
    let count = 0
    // Small EVs peak around 30-40nm
    count += Math.max(0, 800 * Math.exp(-Math.pow((size - 35) / 20, 2)))
    // Exosomes peak around 100-150nm
    count += Math.max(0, 2000 * Math.exp(-Math.pow((size - 120) / 50, 2)))
    // Large EVs peak around 250-300nm
    count += Math.max(0, 600 * Math.exp(-Math.pow((size - 280) / 80, 2)))

    data.push({
      size,
      smallEV: size <= 50 ? Math.round(count * 0.3) : 0,
      exosomes: size > 50 && size <= 200 ? Math.round(count * 0.8) : 0,
      largeEV: size > 200 ? Math.round(count * 0.4) : 0,
      total: Math.round(count * (0.3 + Math.random() * 0.2)),
    })
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
}: SizeDistributionChartProps) {
  const data = propData || generateHistogramData()
  const [brushDomain, setBrushDomain] = useState<{ startIndex?: number; endIndex?: number }>({})

  return (
    <InteractiveChartWrapper
      title="Size Distribution"
      source="FCS Analysis"
      chartType="histogram"
      showControls={showControls}
      height={320}
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
          <Bar dataKey="smallEV" stackId="a" fill="#00b4d8" name="Small EVs (<50nm)" radius={[0, 0, 0, 0]} />
          <Bar dataKey="exosomes" stackId="a" fill="#8b5cf6" name="Exosomes (50-200nm)" radius={[0, 0, 0, 0]} />
          <Bar dataKey="largeEV" stackId="a" fill="#f59e0b" name="Large EVs (>200nm)" radius={[2, 2, 0, 0]} />

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
