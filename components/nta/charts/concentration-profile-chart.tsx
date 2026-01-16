"use client"

import { useMemo, useState } from "react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, Legend } from "recharts"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Eye, EyeOff, Layers } from "lucide-react"
import type { NTAResult } from "@/lib/api-client"

interface ConcentrationProfileChartProps {
  data?: NTAResult
  secondaryData?: NTAResult
  showOverlayControls?: boolean
}

// Generate concentration profile from size bins
const generateConcentrationData = (results?: NTAResult, label?: string) => {
  if (!results) {
    // Default mock data
    return [
      { position: 1, range: "50-80nm", concentration: 2.4, percentage: 15 },
      { position: 2, range: "80-100nm", concentration: 2.2, percentage: 13 },
      { position: 3, range: "100-120nm", concentration: 2.6, percentage: 16 },
      { position: 4, range: "120-150nm", concentration: 2.3, percentage: 14 },
      { position: 5, range: "150-200nm", concentration: 2.5, percentage: 15 },
      { position: 6, range: "200+nm", concentration: 2.1, percentage: 12 },
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

// Merge data for overlay
const mergeDataForOverlay = (primaryData: any[], secondaryData: any[]) => {
  return primaryData.map((item, index) => ({
    ...item,
    primaryConcentration: item.concentration,
    secondaryConcentration: secondaryData[index]?.concentration || 0,
    primaryPercentage: item.percentage,
    secondaryPercentage: secondaryData[index]?.percentage || 0,
  }))
}

// Custom tooltip for overlay mode
function OverlayTooltip({ active, payload, label }: any) {
  if (!active || !payload || !payload.length) return null

  const item = payload[0]?.payload

  return (
    <div className="bg-background/95 backdrop-blur-sm border border-border rounded-lg p-3 shadow-lg">
      <p className="font-semibold text-sm mb-2 border-b pb-1">{item?.range || `Position ${label}`}</p>
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
            <span className="font-medium tabular-nums">{entry.value?.toFixed(2)}×10⁹ p/mL</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function ConcentrationProfileChart({ 
  data: results,
  secondaryData: secondaryResults,
  showOverlayControls = true,
}: ConcentrationProfileChartProps) {
  const [showPrimary, setShowPrimary] = useState(true)
  const [showSecondary, setShowSecondary] = useState(true)
  
  const hasOverlay = !!secondaryResults
  
  const primaryData = useMemo(() => generateConcentrationData(results), [results])
  const secondaryData = useMemo(() => generateConcentrationData(secondaryResults), [secondaryResults])
  
  const overlayData = useMemo(() => {
    if (!hasOverlay) return primaryData
    return mergeDataForOverlay(primaryData, secondaryData)
  }, [primaryData, secondaryData, hasOverlay])
  
  const avgConcentration = primaryData.reduce((sum, d) => sum + d.concentration, 0) / primaryData.length

  return (
    <div className="space-y-3">
      {/* Overlay controls */}
      {hasOverlay && showOverlayControls && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="gap-1 bg-orange-500/20 text-orange-500 border-orange-500/50">
              <Layers className="h-3 w-3" />
              Concentration Overlay
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
              <span className="w-2 h-2 rounded-full bg-blue-500" />
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
          <BarChart data={hasOverlay ? overlayData : primaryData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="range"
              stroke="#64748b"
              tick={{ fontSize: 10 }}
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
              domain={[0, "auto"]}
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
              formatter={(value: number, name: string, props: any) => [
                `${value.toFixed(2)}×10⁹ p/mL (${props.payload.percentage?.toFixed(1)}%)`,
                "Concentration"
              ]}
              labelFormatter={(value, payload) => {
                const item = payload?.[0]?.payload
                return item?.range || `Position ${value}`
              }}
            />
            
            {hasOverlay && <Legend />}
            
            {/* Primary data bars */}
            {showPrimary && (
              <Bar 
                dataKey={hasOverlay ? "primaryConcentration" : "concentration"} 
                name="Primary Sample"
                radius={[4, 4, 0, 0]}
                fill="#3b82f6"
              />
            )}
            
            {/* Secondary data bars (only in overlay mode) */}
            {hasOverlay && showSecondary && (
              <Bar 
                dataKey="secondaryConcentration" 
                name="Secondary Sample"
                radius={[4, 4, 0, 0]}
                fill="#f97316"
              />
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
