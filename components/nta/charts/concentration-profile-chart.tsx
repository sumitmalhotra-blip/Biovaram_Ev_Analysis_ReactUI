"use client"

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts"

const data = [
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

export function ConcentrationProfileChart() {
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
            formatter={(value: number) => [`${value.toFixed(1)}×10⁹ p/mL`, "Concentration"]}
            labelFormatter={(value) => `Position ${value}`}
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
