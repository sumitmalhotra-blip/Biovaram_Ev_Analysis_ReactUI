"use client"

import { useMemo } from "react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"

interface SizeDistribution {
  bins: number[]
  counts: number[]
}

interface OverlayHistogramChartProps {
  fcsData?: SizeDistribution
  ntaData?: SizeDistribution
}

// Generate default overlay histogram data
const generateDefaultData = () => {
  const data = []
  for (let size = 0; size <= 500; size += 20) {
    // FCS distribution
    const fcs = Math.max(0, 2000 * Math.exp(-Math.pow((size - 127) / 55, 2)))
    // NTA distribution (slightly shifted)
    const nta = Math.max(0, 1500 * Math.exp(-Math.pow((size - 140) / 50, 2)))

    data.push({
      size,
      fcs: Math.round(fcs * (0.9 + Math.random() * 0.2)),
      nta: Math.round(nta * (0.9 + Math.random() * 0.2)),
    })
  }
  return data
}

export function OverlayHistogramChart({ fcsData, ntaData }: OverlayHistogramChartProps) {
  const chartData = useMemo(() => {
    // If both datasets exist, merge them
    if (fcsData && ntaData) {
      const allBins = new Set([...fcsData.bins, ...ntaData.bins])
      const sortedBins = Array.from(allBins).sort((a, b) => a - b)
      
      return sortedBins.map(bin => {
        const fcsIndex = fcsData.bins.indexOf(bin)
        const ntaIndex = ntaData.bins.indexOf(bin)
        
        return {
          size: bin,
          fcs: fcsIndex >= 0 ? fcsData.counts[fcsIndex] : 0,
          nta: ntaIndex >= 0 ? ntaData.counts[ntaIndex] : 0,
        }
      })
    }
    
    // If only FCS data exists
    if (fcsData) {
      return fcsData.bins.map((bin, i) => ({
        size: bin,
        fcs: fcsData.counts[i],
        nta: 0,
      }))
    }
    
    // If only NTA data exists
    if (ntaData) {
      return ntaData.bins.map((bin, i) => ({
        size: bin,
        fcs: 0,
        nta: ntaData.counts[i],
      }))
    }
    
    // Default data for demo
    return generateDefaultData()
  }, [fcsData, ntaData])

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
          <Bar dataKey="fcs" fill="#3b82f6" fillOpacity={0.7} name="FCS" />
          <Bar dataKey="nta" fill="#8b5cf6" fillOpacity={0.7} name="NTA" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
