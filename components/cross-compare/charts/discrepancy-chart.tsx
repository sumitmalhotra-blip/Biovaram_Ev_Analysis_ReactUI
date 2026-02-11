"use client"

import { useMemo } from "react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from "recharts"
import { AlertTriangle, CheckCircle } from "lucide-react"

// Note: Mean removed from discrepancy metrics per client request (Surya, Dec 3, 2025)
// "Mean is basically not the real metric... median is something that really existed in the data set"
// Focus on D10, D50 (Median), D90, and Std Dev for comparison

interface DiscrepancyStats {
  d10: number
  d50: number
  d90: number
  std: number
}

interface DiscrepancyChartProps {
  fcsStats?: DiscrepancyStats
  ntaStats?: DiscrepancyStats
  threshold?: number
}

function calcDiscrepancy(fcs: number, nta: number): number {
  if (fcs === 0 && nta === 0) return 0
  return Math.abs((nta - fcs) / ((nta + fcs) / 2)) * 100
}

export function DiscrepancyChart({ fcsStats, ntaStats, threshold = 15 }: DiscrepancyChartProps) {
  const data = useMemo(() => {
    if (!fcsStats || !ntaStats) return null

    return [
      { metric: "D10", discrepancy: parseFloat(calcDiscrepancy(fcsStats.d10, ntaStats.d10).toFixed(1)), fcs: fcsStats.d10, nta: ntaStats.d10 },
      { metric: "D50 (Median)", discrepancy: parseFloat(calcDiscrepancy(fcsStats.d50, ntaStats.d50).toFixed(1)), fcs: fcsStats.d50, nta: ntaStats.d50 },
      { metric: "D90", discrepancy: parseFloat(calcDiscrepancy(fcsStats.d90, ntaStats.d90).toFixed(1)), fcs: fcsStats.d90, nta: ntaStats.d90 },
      { metric: "Std Dev", discrepancy: parseFloat(calcDiscrepancy(fcsStats.std, ntaStats.std).toFixed(1)), fcs: fcsStats.std, nta: ntaStats.std },
    ]
  }, [fcsStats, ntaStats])

  if (!data) {
    return (
      <div className="h-64 flex items-center justify-center text-muted-foreground text-sm">
        <div className="text-center space-y-2">
          <AlertTriangle className="h-8 w-8 mx-auto opacity-50" />
          <p>Select both FCS and NTA samples to view discrepancy analysis</p>
        </div>
      </div>
    )
  }

  const maxDiscrepancy = Math.max(...data.map(d => d.discrepancy), threshold + 5)
  const allBelowThreshold = data.every(d => d.discrepancy <= threshold)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-end gap-2 text-xs">
        {allBelowThreshold ? (
          <span className="flex items-center gap-1 text-emerald-500">
            <CheckCircle className="h-3.5 w-3.5" />
            All metrics within threshold
          </span>
        ) : (
          <span className="flex items-center gap-1 text-red-500">
            <AlertTriangle className="h-3.5 w-3.5" />
            {data.filter(d => d.discrepancy > threshold).length} metric(s) exceed threshold
          </span>
        )}
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
            <XAxis
              type="number"
              stroke="#64748b"
              tick={{ fontSize: 11 }}
              domain={[0, Math.ceil(maxDiscrepancy / 5) * 5]}
              label={{ value: "Discrepancy (%)", position: "bottom", offset: -5, fill: "#64748b", fontSize: 12 }}
            />
            <YAxis type="category" dataKey="metric" stroke="#64748b" tick={{ fontSize: 11 }} width={80} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "8px",
                fontSize: "12px",
                color: "#f8fafc",
              }}
              labelStyle={{ color: "#94a3b8" }}
              formatter={(value: number, _name: string, props: { payload: { fcs: number; nta: number } }) => {
                const { fcs, nta } = props.payload
                return [`${value.toFixed(1)}% (FCS: ${fcs.toFixed(1)}, NTA: ${nta.toFixed(1)})`, "Discrepancy"]
              }}
            />
            <ReferenceLine
              x={threshold}
              stroke="#ef4444"
              strokeDasharray="5 5"
              label={{ value: `${threshold}% Threshold`, fill: "#ef4444", fontSize: 10 }}
            />
            <Bar dataKey="discrepancy" radius={[0, 4, 4, 0]}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.discrepancy > threshold ? "#ef4444" : "#10b981"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
