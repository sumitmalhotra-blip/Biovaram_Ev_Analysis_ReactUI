"use client"

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts"

interface MiniChartProps {
  type: "histogram" | "scatter" | "line" | "bar"
  data: unknown
}

const sampleData = [
  { x: 50, y: 120 },
  { x: 100, y: 280 },
  { x: 150, y: 420 },
  { x: 200, y: 350 },
  { x: 250, y: 180 },
  { x: 300, y: 90 },
]

export function MiniChart({ type }: MiniChartProps) {
  const chartData = sampleData

  return (
    <div className="h-32">
      <ResponsiveContainer width="100%" height="100%">
        {type === "bar" || type === "histogram" ? (
          <BarChart data={chartData}>
            <XAxis dataKey="x" tick={{ fontSize: 10 }} stroke="#64748b" />
            <YAxis tick={{ fontSize: 10 }} stroke="#64748b" />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "6px",
                fontSize: "12px",
              }}
            />
            <Bar dataKey="y" fill="#3b82f6" radius={[2, 2, 0, 0]} />
          </BarChart>
        ) : type === "line" ? (
          <LineChart data={chartData}>
            <XAxis dataKey="x" tick={{ fontSize: 10 }} stroke="#64748b" />
            <YAxis tick={{ fontSize: 10 }} stroke="#64748b" />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "6px",
                fontSize: "12px",
              }}
            />
            <Line type="monotone" dataKey="y" stroke="#3b82f6" strokeWidth={2} dot={false} />
          </LineChart>
        ) : (
          <ScatterChart>
            <XAxis dataKey="x" tick={{ fontSize: 10 }} stroke="#64748b" />
            <YAxis dataKey="y" tick={{ fontSize: 10 }} stroke="#64748b" />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "6px",
                fontSize: "12px",
              }}
            />
            <Scatter data={chartData} fill="#8b5cf6" />
          </ScatterChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}
