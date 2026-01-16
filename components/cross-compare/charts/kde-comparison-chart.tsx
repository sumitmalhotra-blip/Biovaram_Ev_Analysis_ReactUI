"use client"

import { useMemo } from "react"
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { TrendingUp } from "lucide-react"

interface KDEComparisonChartProps {
  fcsData?: { size: number; count?: number; concentration?: number }[]
  ntaData?: { size: number; count?: number; concentration?: number }[]
  className?: string
  showLegend?: boolean
  bandwidth?: number
}

// Gaussian kernel function
function gaussianKernel(u: number): number {
  return (1 / Math.sqrt(2 * Math.PI)) * Math.exp(-0.5 * u * u)
}

// Calculate Kernel Density Estimation
function calculateKDE(
  data: number[],
  bandwidth: number,
  minX: number,
  maxX: number,
  points: number = 200
): { x: number; density: number }[] {
  if (data.length === 0) return []

  const step = (maxX - minX) / points
  const result: { x: number; density: number }[] = []

  for (let i = 0; i <= points; i++) {
    const x = minX + i * step
    let density = 0

    for (const xi of data) {
      const u = (x - xi) / bandwidth
      density += gaussianKernel(u)
    }

    density = density / (data.length * bandwidth)
    result.push({ x, density })
  }

  return result
}

// Silverman's rule of thumb for bandwidth selection
function silvermanBandwidth(data: number[]): number {
  const n = data.length
  if (n === 0) return 10

  const mean = data.reduce((sum, v) => sum + v, 0) / n
  const variance = data.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / n
  const std = Math.sqrt(variance)

  // Silverman's rule
  return 1.06 * std * Math.pow(n, -0.2)
}

// Deterministic pseudo-random based on seed (avoids hydration mismatch)
function seededRandom(seed: number): number {
  const x = Math.sin(seed * 9999) * 10000
  return x - Math.floor(x)
}

// Generate demo data if none provided - using deterministic values
function generateDemoData(center: number, spread: number, count: number): number[] {
  const data: number[] = []
  for (let i = 0; i < count; i++) {
    // Normal distribution approximation using seeded random
    const u1 = seededRandom(i * 2) || 0.5
    const u2 = seededRandom(i * 2 + 1)
    const normal = Math.sqrt(-2 * Math.log(Math.max(0.001, u1))) * Math.cos(2 * Math.PI * u2)
    const value = center + normal * spread
    if (value > 0) data.push(value)
  }
  return data
}

export function KDEComparisonChart({
  fcsData,
  ntaData,
  className,
  showLegend = true,
  bandwidth: customBandwidth,
}: KDEComparisonChartProps) {
  const chartData = useMemo(() => {
    // Extract size values or generate demo data
    const fcsValues = fcsData && fcsData.length > 0
      ? fcsData.flatMap(d => Array(d.count || 1).fill(d.size))
      : generateDemoData(120, 35, 1000)
    
    const ntaValues = ntaData && ntaData.length > 0
      ? ntaData.flatMap(d => Array(d.count || 1).fill(d.size))
      : generateDemoData(135, 40, 1000)

    // Determine common range
    const allValues = [...fcsValues, ...ntaValues]
    const minX = Math.max(0, Math.min(...allValues) - 20)
    const maxX = Math.max(...allValues) + 20

    // Calculate bandwidth (use custom or auto-select)
    const fcsBandwidth = customBandwidth || silvermanBandwidth(fcsValues)
    const ntaBandwidth = customBandwidth || silvermanBandwidth(ntaValues)

    // Calculate KDEs
    const fcsKDE = calculateKDE(fcsValues, fcsBandwidth, minX, maxX)
    const ntaKDE = calculateKDE(ntaValues, ntaBandwidth, minX, maxX)

    // Find peaks (mode)
    const fcsMode = fcsKDE.reduce((max, d) => d.density > max.density ? d : max, fcsKDE[0])
    const ntaMode = ntaKDE.reduce((max, d) => d.density > max.density ? d : max, ntaKDE[0])

    // Merge into single dataset
    const merged = fcsKDE.map((fd, i) => ({
      size: fd.x,
      fcs: fd.density,
      nta: ntaKDE[i]?.density || 0,
    }))

    // Normalize so max is 1 for easier comparison
    const maxDensity = Math.max(
      ...merged.map(d => Math.max(d.fcs, d.nta))
    )

    const normalized = merged.map(d => ({
      size: d.size,
      fcs: d.fcs / maxDensity,
      nta: d.nta / maxDensity,
    }))

    return {
      data: normalized,
      fcsMode: fcsMode.x,
      ntaMode: ntaMode.x,
      fcsBandwidth,
      ntaBandwidth,
    }
  }, [fcsData, ntaData, customBandwidth])

  const modeDifference = Math.abs(chartData.fcsMode - chartData.ntaMode)
  const modeAgreement = modeDifference < 10 ? "Excellent" :
                        modeDifference < 20 ? "Good" :
                        modeDifference < 30 ? "Fair" : "Poor"

  return (
    <Card className={cn("card-3d", className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-primary/10">
              <TrendingUp className="h-4 w-4 text-primary" />
            </div>
            <div>
              <CardTitle className="text-base md:text-lg">KDE Distribution Comparison</CardTitle>
              <CardDescription className="text-xs">
                Kernel Density Estimation overlay of FCS and NTA size distributions
              </CardDescription>
            </div>
          </div>
          <Badge 
            variant="outline"
            className={cn(
              "text-xs",
              modeAgreement === "Excellent" && "bg-emerald-500/10 text-emerald-600 border-emerald-500/30",
              modeAgreement === "Good" && "bg-blue-500/10 text-blue-600 border-blue-500/30",
              modeAgreement === "Fair" && "bg-amber-500/10 text-amber-600 border-amber-500/30",
              modeAgreement === "Poor" && "bg-rose-500/10 text-rose-600 border-rose-500/30"
            )}
          >
            {modeAgreement} Mode Agreement
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full">
          <ResponsiveContainer>
            <AreaChart
              data={chartData.data}
              margin={{ top: 10, right: 30, left: 0, bottom: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis
                dataKey="size"
                type="number"
                domain={["auto", "auto"]}
                tickFormatter={(v) => `${v.toFixed(0)}`}
                tick={{ fontSize: 11 }}
                label={{ 
                  value: "Particle Size (nm)", 
                  position: "bottom",
                  offset: 5,
                  style: { fontSize: 11 }
                }}
              />
              <YAxis
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => v.toFixed(2)}
                label={{ 
                  value: "Normalized Density", 
                  angle: -90, 
                  position: "insideLeft",
                  style: { fontSize: 11 }
                }}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="bg-popover border rounded-lg p-2 shadow-lg text-sm">
                        <div className="font-medium mb-1">Size: {Number(label).toFixed(1)} nm</div>
                        {payload.map((entry, index) => (
                          <div 
                            key={index}
                            className="flex items-center gap-2"
                            style={{ color: entry.color }}
                          >
                            <div 
                              className="w-2 h-2 rounded-full"
                              style={{ background: entry.color }}
                            />
                            <span>{entry.name}: {Number(entry.value).toFixed(3)}</span>
                          </div>
                        ))}
                      </div>
                    )
                  }
                  return null
                }}
              />
              {showLegend && (
                <Legend 
                  verticalAlign="top"
                  height={36}
                />
              )}
              <ReferenceLine 
                x={chartData.fcsMode} 
                stroke="hsl(221, 83%, 53%)" 
                strokeDasharray="3 3"
                strokeOpacity={0.7}
              />
              <ReferenceLine 
                x={chartData.ntaMode} 
                stroke="hsl(270, 76%, 58%)" 
                strokeDasharray="3 3"
                strokeOpacity={0.7}
              />
              <Area
                type="monotone"
                dataKey="fcs"
                name="FCS"
                stroke="hsl(221, 83%, 53%)"
                fill="hsl(221, 83%, 53%)"
                fillOpacity={0.3}
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="nta"
                name="NTA"
                stroke="hsl(270, 76%, 58%)"
                fill="hsl(270, 76%, 58%)"
                fillOpacity={0.3}
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Summary stats */}
        <div className="flex flex-wrap items-center justify-center gap-4 mt-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[hsl(221,83%,53%)]" />
            <span>FCS Mode: <strong>{chartData.fcsMode.toFixed(1)} nm</strong></span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[hsl(270,76%,58%)]" />
            <span>NTA Mode: <strong>{chartData.ntaMode.toFixed(1)} nm</strong></span>
          </div>
          <div className="text-muted-foreground">
            Δ Mode: <strong>{modeDifference.toFixed(1)} nm</strong>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
