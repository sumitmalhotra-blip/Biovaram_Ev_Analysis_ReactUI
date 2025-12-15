"use client"

import { useMemo } from "react"
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts"
import type { NTAResult } from "@/lib/api-client"

interface NTASizeDistributionChartProps {
  data?: NTAResult
}

// Generate NTA size distribution data from results
const generateData = (results?: NTAResult) => {
  const data = []
  const centerSize = results?.median_size_nm || 145
  const spread = (results?.d90_nm && results?.d10_nm) 
    ? (results.d90_nm - results.d10_nm) / 2 
    : 60
  
  for (let size = 0; size <= 500; size += 5) {
    // Single peak distribution centered on median
    const count = Math.max(0, 3000 * Math.exp(-Math.pow((size - centerSize) / spread, 2)))
    data.push({
      size,
      count: Math.round(count * (0.9 + Math.random() * 0.2)),
    })
  }
  return data
}

export function NTASizeDistributionChart({ data: results }: NTASizeDistributionChartProps) {
  const data = useMemo(() => generateData(results), [results])
  
  const d10 = results?.d10_nm || 90
  const d50 = results?.d50_nm || results?.median_size_nm || 145
  const d90 = results?.d90_nm || 200
  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.1} />
            </linearGradient>
          </defs>
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
          <Tooltip
            contentStyle={{
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "8px",
              fontSize: "12px",
            }}
            labelFormatter={(value) => `${value} nm`}
          />
          <Area
            type="monotone"
            dataKey="count"
            stroke="#8b5cf6"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorCount)"
          />

          {/* Percentile lines */}
          <ReferenceLine
            x={d10}
            stroke="#10b981"
            strokeDasharray="5 5"
            label={{ value: "D10", fill: "#10b981", fontSize: 10, position: "top" }}
          />
          <ReferenceLine
            x={d50}
            stroke="#10b981"
            strokeDasharray="5 5"
            label={{ value: "D50", fill: "#10b981", fontSize: 10, position: "top" }}
          />
          <ReferenceLine
            x={d90}
            stroke="#10b981"
            strokeDasharray="5 5"
            label={{ value: "D90", fill: "#10b981", fontSize: 10, position: "top" }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
