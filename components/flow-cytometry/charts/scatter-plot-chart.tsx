"use client"

import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ZAxis } from "recharts"

interface ScatterPlotChartProps {
  title: string
  xLabel: string
  yLabel: string
}

// Generate sample scatter data
const generateScatterData = () => {
  const normal = []
  const anomalies = []

  for (let i = 0; i < 500; i++) {
    const x = Math.random() * 1000 + 100
    const y = x * (0.8 + Math.random() * 0.4) + Math.random() * 200

    if (Math.random() > 0.95) {
      anomalies.push({ x, y, z: 50 })
    } else {
      normal.push({ x, y, z: 20 })
    }
  }

  return { normal, anomalies }
}

const { normal, anomalies } = generateScatterData()

export function ScatterPlotChart({ xLabel, yLabel }: ScatterPlotChartProps) {
  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart>
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
          <ZAxis dataKey="z" range={[20, 100]} />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "8px",
              fontSize: "12px",
            }}
            formatter={(value: number) => value.toFixed(1)}
          />
          <Scatter name="Normal" data={normal} fill="#3b82f6" fillOpacity={0.6} />
          <Scatter name="Anomalies" data={anomalies} fill="#ef4444" />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
