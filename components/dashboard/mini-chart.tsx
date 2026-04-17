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

// Validate and normalize chart data — filter out NaN/Infinity values
function normalizeChartData(data: unknown): ChartDataPoint[] {
  if (!data) return []
  
  if (Array.isArray(data)) {
    if (data.length === 0) return []

    // Check if it's already in the right format
    if (typeof data[0] === 'object' && data[0] !== null && 'x' in data[0]) {
      // Filter out invalid values that would break Recharts
      const valid = (data as ChartDataPoint[]).filter(
        d => Number.isFinite(d.x) && Number.isFinite(d.y)
      )
      return valid
    }
    
    // Try to convert from various formats
    if (data.length > 0 && typeof data[0] === 'object') {
      const firstItem = data[0] as Record<string, unknown>
      
      // Handle {size: number, count: number} format
      if ('size' in firstItem && 'count' in firstItem) {
        return data.map((d: Record<string, unknown>) => ({
          x: Number(d.size) || 0,
          y: Number(d.count) || 0,
        })).filter((d) => Number.isFinite(d.x) && Number.isFinite(d.y))
      }
      
      // Handle {diameter: number, value: number} format
      if ('diameter' in firstItem) {
        return data.map((d: Record<string, unknown>) => ({
          x: Number(d.diameter) || 0,
          y: Number(d.value || d.count || d.intensity) || 0,
        })).filter((d) => Number.isFinite(d.x) && Number.isFinite(d.y))
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
        })).filter((d) => Number.isFinite(d.x) && Number.isFinite(d.y))
      }
    }
  }
  
  return []
}

export function MiniChart({ type, data, config }: MiniChartProps) {
  const chartData = useMemo(() => normalizeChartData(data), [data])
  
  const primaryColor = config?.color || "#3b82f6"
  const gridColor = "#334155"
  const axisColor = "#64748b"
  
  // Check if data points have labels (e.g. bin ranges)
  const hasLabels = chartData.some(d => d.label)
  
  const tooltipStyle = {
    backgroundColor: "#1e293b",
    border: "1px solid #334155",
    borderRadius: "6px",
    fontSize: "12px",
    color: "#f8fafc",
  }

  if (chartData.length === 0) {
    return (
      <div className="h-48 flex items-center justify-center text-muted-foreground text-xs">
        No plottable pinned data available
      </div>
    )
  }

  return (
    <div className="h-48">
      <ResponsiveContainer width="100%" height="100%">
        {type === "bar" || type === "histogram" ? (
          <BarChart data={chartData} margin={{ top: 5, right: 5, left: 0, bottom: 20 }}>
            <defs>
              <linearGradient id={`miniBar-${primaryColor.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={primaryColor} stopOpacity={0.9} />
                <stop offset="95%" stopColor={primaryColor} stopOpacity={0.4} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} opacity={0.3} />
            <XAxis 
              dataKey={hasLabels ? "label" : "x"} 
              tick={{ fontSize: 9, fill: axisColor }} 
              stroke={axisColor}
              label={config?.xAxisLabel ? { 
                value: config.xAxisLabel, 
                position: 'bottom', 
                fontSize: 9,
                fill: axisColor,
                offset: 2,
              } : undefined}
            />
            <YAxis 
              tick={{ fontSize: 9, fill: axisColor }} 
              stroke={axisColor}
              domain={[0, 'auto']}
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
              labelFormatter={(label) => `${config?.xAxisLabel || 'Value'}: ${label}`}
            />
            <Bar 
              dataKey="y" 
              fill={`url(#miniBar-${primaryColor.replace('#', '')})`} 
              radius={[2, 2, 0, 0]} 
            />
          </BarChart>
        ) : type === "line" ? (
          <AreaChart data={chartData} margin={{ top: 5, right: 5, left: 0, bottom: 20 }}>
            <defs>
              <linearGradient id={`miniGrad-${primaryColor.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={primaryColor} stopOpacity={0.4} />
                <stop offset="95%" stopColor={primaryColor} stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} opacity={0.3} />
            <XAxis 
              dataKey="x" 
              tick={{ fontSize: 9, fill: axisColor }} 
              stroke={axisColor}
              label={config?.xAxisLabel ? { 
                value: config.xAxisLabel, 
                position: 'bottom', 
                fontSize: 9,
                fill: axisColor,
                offset: 2,
              } : undefined}
            />
            <YAxis 
              tick={{ fontSize: 9, fill: axisColor }} 
              stroke={axisColor}
              domain={[0, 'auto']}
              label={config?.yAxisLabel ? { 
                value: config.yAxisLabel, 
                angle: -90, 
                position: 'insideLeft',
                fontSize: 9,
                fill: axisColor
              } : undefined}
            />
            <Tooltip contentStyle={tooltipStyle} />
            <Area 
              type="monotone" 
              dataKey="y" 
              stroke={primaryColor} 
              strokeWidth={2} 
              fill={`url(#miniGrad-${primaryColor.replace('#', '')})`}
            />
          </AreaChart>
        ) : (
          <ScatterChart margin={{ top: 5, right: 5, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} opacity={0.3} />
            <XAxis 
              dataKey="x" 
              tick={{ fontSize: 9, fill: axisColor }} 
              stroke={axisColor}
              type="number"
              label={config?.xAxisLabel ? { 
                value: config.xAxisLabel, 
                position: 'bottom', 
                fontSize: 9,
                fill: axisColor,
                offset: 2,
              } : undefined}
            />
            <YAxis 
              dataKey="y" 
              tick={{ fontSize: 9, fill: axisColor }} 
              stroke={axisColor}
              type="number"
              label={config?.yAxisLabel ? { 
                value: config.yAxisLabel, 
                angle: -90, 
                position: 'insideLeft',
                fontSize: 9,
                fill: axisColor
              } : undefined}
            />
            <Tooltip contentStyle={tooltipStyle} />
            <Scatter data={chartData} fill={primaryColor} opacity={0.6} />
          </ScatterChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}
