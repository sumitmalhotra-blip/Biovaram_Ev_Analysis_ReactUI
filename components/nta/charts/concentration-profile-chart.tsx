"use client"

import { useMemo } from "react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts"
import type { NTAResult } from "@/lib/api-client"

interface ConcentrationProfileChartProps {
  data?: NTAResult
}

// Generate concentration profile from size bins
const generateConcentrationData = (results?: NTAResult) => {
  if (!results) {
    // Default mock data
    return [
      { position: 1, concentration: 2.4 },
      { position: 2, concentration: 2.2 },
      { position: 3, concentration: 2.6 },
      { position: 4, concentration: 2.3 },
      { position: 5, concentration: 2.5 },
      { position: 6, concentration: 2.1 },
      { position: 7, concentration: 2.4 },
      { position: 8, concentration: 2.7 },
      { position: 9, concentration: 2.3 },
      { position: 10, concentration: 2.2 },
      { position: 11, concentration: 2.5 },
    ]
  }

  // Use size bins to create concentration profile
  const bins = [
    { range: "50-80nm", value: results.bin_50_80nm_pct || 0 },
    { range: "80-100nm", value: results.bin_80_100nm_pct || 0 },
    { range: "100-120nm", value: results.bin_100_120nm_pct || 0 },
    { range: "120-150nm", value: results.bin_120_150nm_pct || 0 },
    { range: "150-200nm", value: results.bin_150_200nm_pct || 0 },
    { range: "200+nm", value: results.bin_200_plus_pct || 0 },
  ]

  const totalConc = results.concentration_particles_ml || 2.4e9
  
  return bins.map((bin, index) => ({
    position: index + 1,
    range: bin.range,
    concentration: (bin.value / 100) * (totalConc / 1e9),
    percentage: bin.value
  }))
}

export function ConcentrationProfileChart({ data: results }: ConcentrationProfileChartProps) {
  const data = useMemo(() => generateConcentrationData(results), [results])
  const avgConcentration = data.reduce((sum, d) => sum + d.concentration, 0) / data.length

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="position"
            stroke="#64748b"
            tick={{ fontSize: 11 }}
            label={{ value: "Position", position: "bottom", offset: -5, fill: "#64748b", fontSize: 12 }}
          />
          <YAxis
            stroke="#64748b"
            tick={{ fontSize: 11 }}
            label={{
              value: "Concentration (×10⁹ p/mL)",
              angle: -90,
              position: "insideLeft",
              fill: "#64748b",
              fontSize: 12,
            }}
            domain={[0, 3]}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "8px",
              fontSize: "12px",
            }}
            formatter={(value: number, name: string, props: any) => [
              `${value.toFixed(2)}×10⁹ p/mL (${props.payload.percentage?.toFixed(1)}%)`,
              "Concentration"
            ]}
            labelFormatter={(value, payload) => {
              const item = payload?.[0]?.payload
              return item?.range || `Position ${value}`
            }}
          />
          <Bar dataKey="concentration" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={Math.abs(entry.concentration - avgConcentration) > 0.3 ? "#f59e0b" : "#3b82f6"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
