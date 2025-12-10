"use client"

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
} from "recharts"

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

const data = generateHistogramData()

export function SizeDistributionChart() {
  return (
    <div className="h-80">
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
          <Tooltip
            contentStyle={{
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "8px",
              fontSize: "12px",
            }}
            labelFormatter={(value) => `${value} nm`}
          />
          <Legend wrapperStyle={{ fontSize: "12px" }} />
          <Bar dataKey="smallEV" stackId="a" fill="#00b4d8" name="Small EVs (<50nm)" radius={[0, 0, 0, 0]} />
          <Bar dataKey="exosomes" stackId="a" fill="#8b5cf6" name="Exosomes (50-200nm)" radius={[0, 0, 0, 0]} />
          <Bar dataKey="largeEV" stackId="a" fill="#f59e0b" name="Large EVs (>200nm)" radius={[2, 2, 0, 0]} />

          {/* Percentile lines */}
          <ReferenceLine
            x={89}
            stroke="#10b981"
            strokeDasharray="5 5"
            label={{ value: "D10", fill: "#10b981", fontSize: 10 }}
          />
          <ReferenceLine
            x={127}
            stroke="#10b981"
            strokeDasharray="5 5"
            label={{ value: "D50", fill: "#10b981", fontSize: 10 }}
          />
          <ReferenceLine
            x={198}
            stroke="#10b981"
            strokeDasharray="5 5"
            label={{ value: "D90", fill: "#10b981", fontSize: 10 }}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
