"use client"

import { useMemo } from "react"
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ZAxis, Legend } from "recharts"
import { Badge } from "@/components/ui/badge"
import { CHART_COLORS } from "@/lib/store"

export interface ScatterDataPoint {
  x: number
  y: number
  index?: number
  isAnomaly?: boolean
}

interface ScatterPlotChartProps {
  title: string
  xLabel: string
  yLabel: string
  data?: ScatterDataPoint[]
  anomalousIndices?: number[]
  highlightAnomalies?: boolean
  showLegend?: boolean
  height?: number
}

export function ScatterPlotChart({
  xLabel,
  yLabel,
  data,
  anomalousIndices = [],
  highlightAnomalies = true,
  showLegend = true,
  height = 320,
}: ScatterPlotChartProps) {
  // Deterministic pseudo-random for SSR compatibility
  const seededRandom = (seed: number): number => {
    const x = Math.sin(seed * 9999) * 10000
    return x - Math.floor(x)
  }

  // Process data to separate normal and anomalous points
  const { normalData, anomalyData } = useMemo(() => {
    if (!data || data.length === 0) {
      // Generate sample data for demo using deterministic random
      const normal = []
      const anomalies = []

      for (let i = 0; i < 500; i++) {
        const x = seededRandom(i * 3) * 1000 + 100
        const y = x * (0.8 + seededRandom(i * 3 + 1) * 0.4) + seededRandom(i * 3 + 2) * 200

        if (seededRandom(i * 3 + 3) > 0.95) {
          anomalies.push({ x, y, z: 20, index: i })
        } else {
          normal.push({ x, y, z: 8, index: i })
        }
      }

      return { normalData: normal, anomalyData: anomalies }
    }

    // Real data processing
    const anomalySet = new Set(anomalousIndices)
    const normal: Array<{ x: number; y: number; z: number; index: number }> = []
    const anomalies: Array<{ x: number; y: number; z: number; index: number }> = []

    data.forEach((point, idx) => {
      const pointIndex = point.index ?? idx
      const dataPoint = {
        x: point.x,
        y: point.y,
        z: 8,
        index: pointIndex,
      }

      if (highlightAnomalies && anomalySet.has(pointIndex)) {
        anomalies.push({ ...dataPoint, z: 20 })
      } else {
        normal.push(dataPoint)
      }
    })

    return { normalData: normal, anomalyData: anomalies }
  }, [data, anomalousIndices, highlightAnomalies])

  const totalPoints = normalData.length + anomalyData.length
  const anomalyPercentage = totalPoints > 0 ? ((anomalyData.length / totalPoints) * 100).toFixed(2) : "0.00"

  return (
    <div className="space-y-2">
      {/* Stats Header */}
      {anomalyData.length > 0 && highlightAnomalies && (
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <span>Total Events: {totalPoints.toLocaleString()}</span>
            <span>•</span>
            <span>Normal: {normalData.length.toLocaleString()}</span>
            <span>•</span>
            <span className="flex items-center gap-1">
              Anomalies:{" "}
              <Badge variant="destructive" className="h-5 px-1.5 text-xs">
                {anomalyData.length.toLocaleString()} ({anomalyPercentage}%)
              </Badge>
            </span>
          </div>
        </div>
      )}

      {/* Chart */}
      <div style={{ height: `${height}px` }}>
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="x"
              type="number"
              stroke="#64748b"
              tick={{ fontSize: 11 }}
              label={{ value: xLabel, position: "bottom", offset: -5, fill: "#64748b", fontSize: 12 }}
            />
            <YAxis
              dataKey="y"
              type="number"
              stroke="#64748b"
              tick={{ fontSize: 11 }}
              label={{ value: yLabel, angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 12 }}
            />
            <ZAxis dataKey="z" range={[8, 40]} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "8px",
                fontSize: "12px",
                color: "#f8fafc",
              }}
              labelStyle={{ color: "#94a3b8" }}
              formatter={(value: number) => value.toFixed(1)}
              labelFormatter={(label) => `Event Index: ${label}`}
            />
            {showLegend && (
              <Legend
                wrapperStyle={{ fontSize: "12px" }}
                iconType="circle"
                verticalAlign="top"
                height={36}
              />
            )}
            {/* TASK-018: Use consistent purple color for normal events */}
            <Scatter
              name="Normal Events"
              data={normalData}
              fill={CHART_COLORS.primary}
              fillOpacity={0.6}
              shape="circle"
            />
            {anomalyData.length > 0 && highlightAnomalies && (
              <Scatter
                name="Anomalous Events"
                data={anomalyData}
                fill={CHART_COLORS.anomaly}
                fillOpacity={0.9}
                shape="circle"
              />
            )}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
