"use client"

import { useMemo } from "react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { CHART_COLORS } from "@/lib/store"
import { BarChart3 } from "lucide-react"

// Support both array format and bins/counts format
type SizeDistributionArray = Array<{ size: number; count?: number; concentration?: number }>
type SizeDistributionBins = { bins: number[]; counts: number[] }
type SizeDistribution = SizeDistributionBins | SizeDistributionArray

// Normalize SizeDistribution to bins/counts format
function normalizeDistribution(data: SizeDistribution): SizeDistributionBins | null {
  if (!data) return null
  
  // If it's already in bins/counts format
  if ('bins' in data && 'counts' in data) {
    return data as SizeDistributionBins
  }
  
  // If it's in array format, convert it
  if (Array.isArray(data)) {
    const bins = data.map(d => d.size)
    const counts = data.map(d => d.count ?? d.concentration ?? 0)
    return { bins, counts }
  }
  
  return null
}

interface OverlayHistogramChartProps {
  fcsData?: SizeDistribution
  ntaData?: SizeDistribution
  crossValidationData?: Array<{ size: number; fcs: number; nta: number; fcs_raw: number; nta_raw: number }>
}

export function OverlayHistogramChart({ fcsData, ntaData, crossValidationData }: OverlayHistogramChartProps) {
  const chartData = useMemo(() => {
    // Prefer cross-validation aligned data when available
    if (crossValidationData && crossValidationData.length > 0) {
      return crossValidationData.map(d => ({
        size: d.size,
        fcs: d.fcs,
        nta: d.nta,
      }))
    }
    
    // Normalize both datasets
    const normalizedFcs = fcsData ? normalizeDistribution(fcsData) : null
    const normalizedNta = ntaData ? normalizeDistribution(ntaData) : null
    
    // If both datasets exist, merge them
    if (normalizedFcs && normalizedNta) {
      const allBins = new Set([...normalizedFcs.bins, ...normalizedNta.bins])
      const sortedBins = Array.from(allBins).sort((a, b) => a - b)
      
      return sortedBins.map((bin: number) => {
        const fcsIndex = normalizedFcs.bins.indexOf(bin)
        const ntaIndex = normalizedNta.bins.indexOf(bin)
        
        return {
          size: bin,
          fcs: fcsIndex >= 0 ? normalizedFcs.counts[fcsIndex] : 0,
          nta: ntaIndex >= 0 ? normalizedNta.counts[ntaIndex] : 0,
        }
      })
    }
    
    // If only FCS data exists
    if (normalizedFcs) {
      return normalizedFcs.bins.map((bin: number, i: number) => ({
        size: bin,
        fcs: normalizedFcs.counts[i],
        nta: 0,
      }))
    }
    
    // If only NTA data exists
    if (normalizedNta) {
      return normalizedNta.bins.map((bin: number, i: number) => ({
        size: bin,
        fcs: 0,
        nta: normalizedNta.counts[i],
      }))
    }
    
    // No data available
    return null
  }, [fcsData, ntaData, crossValidationData])

  if (!chartData) {
    return (
      <div className="h-80 flex flex-col items-center justify-center text-muted-foreground border border-dashed border-border rounded-lg bg-muted/10">
        <BarChart3 className="h-10 w-10 mb-3 opacity-40" />
        <p className="text-sm font-medium">No Overlay Data Available</p>
        <p className="text-xs mt-1 max-w-xs text-center">
          Upload and analyze both FCS and NTA files, then run cross-validation to see this comparison.
        </p>
      </div>
    )
  }

  const yAxisLabel = crossValidationData ? "% of Total" : "Count"

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} barCategoryGap={0}>
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
            label={{ value: yAxisLabel, angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 12 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "8px",
              fontSize: "12px",
              color: "#f8fafc",
            }}
            labelStyle={{ color: "#94a3b8" }}
            labelFormatter={(value) => `${value} nm`}
          />
          <Legend wrapperStyle={{ fontSize: "12px" }} />
          {/* TASK-018: Use consistent purple color scheme */}
          <Bar dataKey="fcs" fill={CHART_COLORS.primary} fillOpacity={0.7} name="FCS" />
          <Bar dataKey="nta" fill={CHART_COLORS.secondary} fillOpacity={0.7} name="NTA" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
