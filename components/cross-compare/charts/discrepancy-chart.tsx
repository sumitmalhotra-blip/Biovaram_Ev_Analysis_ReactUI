"use client"

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from "recharts"

// Note: Mean removed from discrepancy metrics per client request (Surya, Dec 3, 2025)
// "Mean is basically not the real metric... median is something that really existed in the data set"
// Focus on D10, D50 (Median), D90, and Std Dev for comparison
const data = [
  { metric: "D10", discrepancy: 3.2 },
  { metric: "D50 (Median)", discrepancy: 6.1 },
  { metric: "D90", discrepancy: 1.8 },
  { metric: "Std Dev", discrepancy: 5.3 },
]

const THRESHOLD = 15

export function DiscrepancyChart() {
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
          <XAxis
            type="number"
            stroke="#64748b"
            tick={{ fontSize: 11 }}
            domain={[0, 20]}
            label={{ value: "Discrepancy (%)", position: "bottom", offset: -5, fill: "#64748b", fontSize: 12 }}
          />
          <YAxis type="category" dataKey="metric" stroke="#64748b" tick={{ fontSize: 11 }} width={50} />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "8px",
              fontSize: "12px",
            }}
            formatter={(value: number) => [`${value.toFixed(1)}%`, "Discrepancy"]}
          />
          <ReferenceLine
            x={THRESHOLD}
            stroke="#ef4444"
            strokeDasharray="5 5"
            label={{ value: "Threshold", fill: "#ef4444", fontSize: 10 }}
          />
          <Bar dataKey="discrepancy" radius={[0, 4, 4, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.discrepancy > THRESHOLD ? "#ef4444" : "#10b981"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
