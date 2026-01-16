"use client"

import { useMemo, useState } from "react"
import { ComposedChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend } from "recharts"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Eye, EyeOff, Layers } from "lucide-react"
import type { NTAResult } from "@/lib/api-client"

interface NTASizeDistributionChartProps {
  data?: NTAResult
  // Overlay support - secondary NTA results
  secondaryData?: NTAResult
  showOverlayControls?: boolean
}

// Deterministic pseudo-random based on seed (avoids hydration mismatch)
const seededVariation = (seed: number): number => {
  const x = Math.sin(seed * 9999) * 10000
  return (x - Math.floor(x)) * 0.2 + 0.9 // Returns 0.9-1.1
}

// Generate NTA size distribution data from results
const generateData = (results?: NTAResult, label?: string) => {
  const data = []
  const centerSize = results?.median_size_nm || 145
  const spread = (results?.d90_nm && results?.d10_nm) 
    ? (results.d90_nm - results.d10_nm) / 2 
    : 60
  
  for (let size = 0; size <= 500; size += 5) {
    // Single peak distribution centered on median
    const count = Math.max(0, 3000 * Math.exp(-Math.pow((size - centerSize) / spread, 2)))
    const index = size / 5
    data.push({
      size,
      count: Math.round(count * seededVariation(index)),
    })
  }
  return data
}

// Merge primary and secondary data for overlay view
const mergeDataForOverlay = (primaryData: any[], secondaryData: any[]) => {
  return primaryData.map((item, index) => ({
    size: item.size,
    primaryCount: item.count,
    secondaryCount: secondaryData[index]?.count || 0,
  }))
}

// Custom tooltip for overlay mode
function OverlayTooltip({ active, payload, label }: any) {
  if (!active || !payload || !payload.length) return null

  return (
    <div className="bg-background/95 backdrop-blur-sm border border-border rounded-lg p-3 shadow-lg">
      <p className="font-semibold text-sm mb-2 border-b pb-1">{label} nm</p>
      <div className="space-y-1.5">
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center justify-between gap-4 text-xs">
            <span className="flex items-center gap-1.5">
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-muted-foreground">{entry.name}:</span>
            </span>
            <span className="font-medium tabular-nums">{entry.value?.toLocaleString()}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function NTASizeDistributionChart({ 
  data: results, 
  secondaryData: secondaryResults,
  showOverlayControls = true,
}: NTASizeDistributionChartProps) {
  const [showPrimary, setShowPrimary] = useState(true)
  const [showSecondary, setShowSecondary] = useState(true)
  
  const hasOverlay = !!secondaryResults
  
  const primaryData = useMemo(() => generateData(results), [results])
  const secondaryData = useMemo(() => generateData(secondaryResults), [secondaryResults])
  
  // Overlay merged data
  const overlayData = useMemo(() => {
    if (!hasOverlay) return primaryData.map(d => ({ ...d, primaryCount: d.count }))
    return mergeDataForOverlay(primaryData, secondaryData)
  }, [primaryData, secondaryData, hasOverlay])
  
  const d10 = results?.d10_nm || 90
  const d50 = results?.d50_nm || results?.median_size_nm || 145
  const d90 = results?.d90_nm || 200
  
  // Secondary percentiles
  const secondaryD10 = secondaryResults?.d10_nm
  const secondaryD50 = secondaryResults?.d50_nm || secondaryResults?.median_size_nm
  const secondaryD90 = secondaryResults?.d90_nm
  
  return (
    <div className="space-y-3">
      {/* Overlay controls */}
      {hasOverlay && showOverlayControls && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="gap-1 bg-orange-500/20 text-orange-500 border-orange-500/50">
              <Layers className="h-3 w-3" />
              NTA Overlay Active
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant={showPrimary ? "default" : "outline"}
              size="sm"
              onClick={() => setShowPrimary(!showPrimary)}
              className="gap-1.5 h-7 text-xs"
            >
              {showPrimary ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
              <span className="w-2 h-2 rounded-full bg-violet-500" />
              Primary
            </Button>
            <Button
              variant={showSecondary ? "default" : "outline"}
              size="sm"
              onClick={() => setShowSecondary(!showSecondary)}
              className="gap-1.5 h-7 text-xs"
            >
              {showSecondary ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
              <span className="w-2 h-2 rounded-full bg-orange-500" />
              Secondary
            </Button>
          </div>
        </div>
      )}
      
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={hasOverlay ? overlayData : primaryData}>
            <defs>
              <linearGradient id="colorCountPrimary" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.1} />
              </linearGradient>
              <linearGradient id="colorCountSecondary" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f97316" stopOpacity={0.6} />
                <stop offset="95%" stopColor="#f97316" stopOpacity={0.1} />
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
              content={hasOverlay ? <OverlayTooltip /> : undefined}
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
            
            {hasOverlay && <Legend />}
            
            {/* Primary data area */}
            {showPrimary && (
              <Area
                type="monotone"
                dataKey={hasOverlay ? "primaryCount" : "count"}
                name="Primary Sample"
                stroke="#8b5cf6"
                strokeWidth={2}
                fillOpacity={hasOverlay ? 0.5 : 1}
                fill="url(#colorCountPrimary)"
              />
            )}
            
            {/* Secondary data area (only in overlay mode) */}
            {hasOverlay && showSecondary && (
              <Area
                type="monotone"
                dataKey="secondaryCount"
                name="Secondary Sample"
                stroke="#f97316"
                strokeWidth={2}
                fillOpacity={0.5}
                fill="url(#colorCountSecondary)"
              />
            )}

            {/* Primary percentile lines */}
            {showPrimary && (
              <>
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
              </>
            )}
            
            {/* Secondary percentile lines (dashed orange) */}
            {hasOverlay && showSecondary && secondaryD10 && (
              <ReferenceLine
                x={secondaryD10}
                stroke="#f97316"
                strokeDasharray="3 3"
                label={{ value: "D10'", fill: "#f97316", fontSize: 9, position: "bottom" }}
              />
            )}
            {hasOverlay && showSecondary && secondaryD50 && (
              <ReferenceLine
                x={secondaryD50}
                stroke="#f97316"
                strokeDasharray="3 3"
                label={{ value: "D50'", fill: "#f97316", fontSize: 9, position: "bottom" }}
              />
            )}
            {hasOverlay && showSecondary && secondaryD90 && (
              <ReferenceLine
                x={secondaryD90}
                stroke="#f97316"
                strokeDasharray="3 3"
                label={{ value: "D90'", fill: "#f97316", fontSize: 9, position: "bottom" }}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
