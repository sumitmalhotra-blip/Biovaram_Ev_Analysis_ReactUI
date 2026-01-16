"use client"

import { useMemo } from "react"
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  CartesianGrid,
} from "recharts"
import type { ChartDataPoint, PinnedChartConfig } from "@/lib/store"

interface MiniChartProps {
  type: "histogram" | "scatter" | "line" | "bar"
  data: ChartDataPoint[] | unknown
  config?: PinnedChartConfig
}

// Default sample data if no real data provided
const defaultData: ChartDataPoint[] = [
  { x: 50, y: 120 },
  { x: 100, y: 280 },
  { x: 150, y: 420 },
  { x: 200, y: 350 },
  { x: 250, y: 180 },
  { x: 300, y: 90 },
]

// Validate and normalize chart data
function normalizeChartData(data: unknown): ChartDataPoint[] {
  if (!data) return defaultData
  
  if (Array.isArray(data)) {
    // Check if it's already in the right format
    if (data.length > 0 && typeof data[0] === 'object' && 'x' in data[0]) {
      return data as ChartDataPoint[]
    }
    
    // Try to convert from various formats
    if (data.length > 0 && typeof data[0] === 'object') {
      const firstItem = data[0] as Record<string, unknown>
      
      // Handle {size: number, count: number} format
      if ('size' in firstItem && 'count' in firstItem) {
        return data.map((d: Record<string, unknown>) => ({
          x: Number(d.size) || 0,
          y: Number(d.count) || 0,
        }))
      }
      
      // Handle {diameter: number, value: number} format
      if ('diameter' in firstItem) {
        return data.map((d: Record<string, unknown>) => ({
          x: Number(d.diameter) || 0,
          y: Number(d.value || d.count || d.intensity) || 0,
        }))
      }
      
      // Handle generic {name/label: x, value: y} format
      const xKey = Object.keys(firstItem).find(k => 
        ['x', 'size', 'diameter', 'name', 'bin'].includes(k.toLowerCase())
      )
      const yKey = Object.keys(firstItem).find(k => 
        ['y', 'count', 'value', 'frequency', 'intensity'].includes(k.toLowerCase())
      )
      
      if (xKey && yKey) {
        return data.map((d: Record<string, unknown>) => ({
          x: Number(d[xKey]) || 0,
          y: Number(d[yKey]) || 0,
          label: String(d.label || d.name || ''),
        }))
      }
    }
  }
  
  return defaultData
}

export function MiniChart({ type, data, config }: MiniChartProps) {
  const chartData = useMemo(() => normalizeChartData(data), [data])
  
  const primaryColor = config?.color || "#3b82f6"
  const gridColor = "#334155"
  const axisColor = "#64748b"
  
  const tooltipStyle = {
    backgroundColor: "#1e293b",
    border: "1px solid #334155",
    borderRadius: "6px",
    fontSize: "12px",
    color: "#f8fafc",
  }

  return (
    <div className="h-32">
      <ResponsiveContainer width="100%" height="100%">
        {type === "bar" || type === "histogram" ? (
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} opacity={0.3} />
            <XAxis 
              dataKey="x" 
              tick={{ fontSize: 10 }} 
              stroke={axisColor}
              label={config?.xAxisLabel ? { 
                value: config.xAxisLabel, 
                position: 'bottom', 
                fontSize: 9,
                fill: axisColor
              } : undefined}
            />
            <YAxis 
              tick={{ fontSize: 10 }} 
              stroke={axisColor}
              label={config?.yAxisLabel ? { 
                value: config.yAxisLabel, 
                angle: -90, 
                position: 'insideLeft',
                fontSize: 9,
                fill: axisColor
              } : undefined}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value: number) => [value.toLocaleString(), config?.yAxisLabel || 'Count']}
              labelFormatter={(label) => `${config?.xAxisLabel || 'Size'}: ${label}`}
            />
            <Bar dataKey="y" fill={primaryColor} radius={[2, 2, 0, 0]} />
          </BarChart>
        ) : type === "line" ? (
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id={`gradient-${primaryColor.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={primaryColor} stopOpacity={0.3} />
                <stop offset="95%" stopColor={primaryColor} stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} opacity={0.3} />
            <XAxis dataKey="x" tick={{ fontSize: 10 }} stroke={axisColor} />
            <YAxis tick={{ fontSize: 10 }} stroke={axisColor} />
            <Tooltip contentStyle={tooltipStyle} />
            <Area 
              type="monotone" 
              dataKey="y" 
              stroke={primaryColor} 
              strokeWidth={2} 
              fill={`url(#gradient-${primaryColor.replace('#', '')})`}
            />
          </AreaChart>
        ) : (
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} opacity={0.3} />
            <XAxis dataKey="x" tick={{ fontSize: 10 }} stroke={axisColor} />
            <YAxis dataKey="y" tick={{ fontSize: 10 }} stroke={axisColor} />
            <Tooltip contentStyle={tooltipStyle} />
            <Scatter data={chartData} fill={config?.secondaryColor || "#8b5cf6"} />
          </ScatterChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}
