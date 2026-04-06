"use client"

import { useEffect, useMemo, useState } from "react"
import { ComposedChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend } from "recharts"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Eye, EyeOff, Layers } from "lucide-react"
import type { NTAResult } from "@/lib/api-client"
import { useAnalysisStore } from "@/lib/store"

interface NTASizeDistributionChartProps {
  data?: NTAResult
  overlaySeries?: Array<{
    sampleId: string
    label: string
    color: string
    visible: boolean
    isPrimary: boolean
    result: NTAResult
  }>
  showOverlayControls?: boolean
}

// Deterministic pseudo-random based on seed (avoids hydration mismatch)
const seededVariation = (seed: number): number => {
  const x = Math.sin(seed * 9999) * 10000
  return (x - Math.floor(x)) * 0.2 + 0.9 // Returns 0.9-1.1
}

// NTA bin definitions for percentage-based fallback
const NTA_BINS = [
  { key: "bin_50_80nm_pct" as const, min: 50, max: 80, label: "50-80nm" },
  { key: "bin_80_100nm_pct" as const, min: 80, max: 100, label: "80-100nm" },
  { key: "bin_100_120nm_pct" as const, min: 100, max: 120, label: "100-120nm" },
  { key: "bin_120_150nm_pct" as const, min: 120, max: 150, label: "120-150nm" },
  { key: "bin_150_200nm_pct" as const, min: 150, max: 200, label: "150-200nm" },
  { key: "bin_200_plus_pct" as const, min: 200, max: 350, label: "200+nm" },
]

const MAX_DISTRIBUTION_POINTS = 260

// Downsample dense curves while preserving visible shape.
const downsampleDistributionData = (data: Array<{ size: number; count: number }>, maxPoints = MAX_DISTRIBUTION_POINTS) => {
  if (data.length <= maxPoints) {
    return data
  }

  const bucketSize = Math.ceil(data.length / maxPoints)
  const sampled: Array<{ size: number; count: number }> = []

  for (let start = 0; start < data.length; start += bucketSize) {
    const bucket = data.slice(start, start + bucketSize)
    if (bucket.length === 0) continue

    const peak = bucket.reduce((max, point) => (point.count > max.count ? point : max), bucket[0])
    sampled.push({ size: peak.size, count: peak.count })
  }

  if (sampled[0]?.size !== data[0]?.size) {
    sampled.unshift(data[0])
  }
  if (sampled[sampled.length - 1]?.size !== data[data.length - 1]?.size) {
    sampled.push(data[data.length - 1])
  }

  return sampled.slice(0, maxPoints)
}

// Generate NTA size distribution data from results — uses REAL data when available
const generateData = (results?: NTAResult, _label?: string): { data: Array<{ size: number; count: number }>, isReal: boolean } => {
  if (!results) return { data: [], isReal: false }

  // Strategy 1: Use size_distribution array from NTA instrument (most accurate)
  if (results.size_distribution && Array.isArray(results.size_distribution) && results.size_distribution.length > 0) {
    const data = results.size_distribution
      .filter((d: any) => d.size != null)
      .map((d: any) => ({
        size: d.size,
        count: d.count ?? d.concentration ?? 0,
      }))
      .sort((a: { size: number }, b: { size: number }) => a.size - b.size)
    if (data.length > 0) return { data, isReal: true }
  }

  // Strategy 2: Reconstruct from bin percentages (real summary data)
  const hasBins = NTA_BINS.some(bin => {
    const val = (results as any)[bin.key]
    return val != null && val > 0
  })
  if (hasBins) {
    const totalConc = results.concentration_particles_ml || 1e8  // use concentration or normalize to 1e8
    const data: Array<{ size: number; count: number }> = []
    
    NTA_BINS.forEach(bin => {
      const pct = (results as any)[bin.key] as number | undefined
      if (pct != null && pct > 0) {
        const binWidth = bin.max - bin.min
        const steps = Math.max(1, Math.round(binWidth / 5)) // ~5nm resolution
        const countPerStep = Math.round((pct / 100 * totalConc) / steps)
        for (let s = 0; s < steps; s++) {
          const size = bin.min + (s + 0.5) * (binWidth / steps)
          data.push({ size: Math.round(size), count: countPerStep })
        }
      }
    })
    if (data.length > 0) return { data: data.sort((a, b) => a.size - b.size), isReal: true }
  }

  // Strategy 3: Gaussian fallback from summary stats (estimated, not real)
  const centerSize = results.median_size_nm || 145
  const spread = (results.d90_nm && results.d10_nm)
    ? (results.d90_nm - results.d10_nm) / 2
    : 60
  const data: Array<{ size: number; count: number }> = []
  for (let size = 0; size <= 500; size += 5) {
    const count = Math.max(0, 3000 * Math.exp(-Math.pow((size - centerSize) / spread, 2)))
    const index = size / 5
    data.push({
      size,
      count: Math.round(count * seededVariation(index)),
    })
  }
  return { data, isReal: false }
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
  overlaySeries = [],
  showOverlayControls = true,
}: NTASizeDistributionChartProps) {
  const [visibilityOverrides, setVisibilityOverrides] = useState<Record<string, boolean>>({})
  const [debouncedOverlaySeries, setDebouncedOverlaySeries] = useState(overlaySeries)
  const { ntaCompareSession, setNTACompareComputedSeriesCacheEntry } = useAnalysisStore()

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedOverlaySeries(overlaySeries)
    }, 120)
    return () => window.clearTimeout(timer)
  }, [overlaySeries])

  const { data: primaryGeneratedData, isReal: primaryIsReal } = useMemo(() => generateData(results), [results])
  const primaryData = useMemo(
    () => downsampleDistributionData(primaryGeneratedData),
    [primaryGeneratedData]
  )

  const preparedSeries = useMemo(() => {
    const visible = debouncedOverlaySeries.filter((series) => visibilityOverrides[series.sampleId] ?? series.visible)
    const sorted = [...visible].sort((a, b) => {
      if (a.isPrimary === b.isPrimary) return 0
      return a.isPrimary ? -1 : 1
    })

    return sorted.map((series, index) => {
      const cacheKey = `dist:${series.sampleId}:${series.result.id ?? "no-result-id"}`
      const cached = ntaCompareSession.computedSeriesCacheByKey[cacheKey]
      const cachedData = cached?.points?.map((point) => ({ size: point.x, count: point.y }))
      const generated = cachedData && cachedData.length > 0
        ? { data: cachedData, isReal: true }
        : generateData(series.result, series.label)
      const sampledData = downsampleDistributionData(generated.data)

      return {
        ...series,
        cacheKey,
        shouldCache: !cached,
        chartKey: `series_${index}`,
        data: sampledData,
      }
    })
  }, [debouncedOverlaySeries, visibilityOverrides, ntaCompareSession.computedSeriesCacheByKey])

  useEffect(() => {
    preparedSeries.forEach((series) => {
      if (!series.shouldCache) return
      setNTACompareComputedSeriesCacheEntry({
        cacheKey: series.cacheKey,
        chartType: "distribution",
        sampleId: series.sampleId,
        points: series.data.map((point) => ({ x: point.size, y: point.count })),
        updatedAt: Date.now(),
      })
    })
  }, [preparedSeries, setNTACompareComputedSeriesCacheEntry])

  const hasOverlay = preparedSeries.length > 1

  const chartData = useMemo(() => {
    if (preparedSeries.length === 0) {
      return primaryData.map((item, idx) => ({
        size: item.size,
        [`series_${idx}`]: item.count,
      }))
    }

    const bySize = new Map<number, Record<string, number>>()
    preparedSeries.forEach((series) => {
      series.data.forEach((point) => {
        const existing = bySize.get(point.size) || {}
        existing[series.chartKey] = point.count
        bySize.set(point.size, existing)
      })
    })

    return Array.from(bySize.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([size, values]) => ({ size, ...values }))
  }, [preparedSeries, primaryData])
  
  const primarySeriesResult = useMemo(() => {
    const explicitPrimary = preparedSeries.find((series) => series.isPrimary)
    if (explicitPrimary?.result) return explicitPrimary.result
    if (results) return results
    return preparedSeries[0]?.result
  }, [preparedSeries, results])

  const d10 = primarySeriesResult?.d10_nm || 90
  const d50 = primarySeriesResult?.d50_nm || primarySeriesResult?.median_size_nm || 145
  const d90 = primarySeriesResult?.d90_nm || 200
  
  return (
    <div className="space-y-3">
      {/* Data source indicator */}
      {!primaryIsReal && results && (
        <Badge variant="outline" className="text-xs text-amber-500 border-amber-500/50">
          Estimated from summary statistics
        </Badge>
      )}

      {/* Overlay controls */}
      {preparedSeries.length > 0 && showOverlayControls && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="gap-1 bg-orange-500/20 text-orange-500 border-orange-500/50">
              <Layers className="h-3 w-3" />
              {hasOverlay ? "NTA Multi-Overlay Active" : "Primary Sample Active"}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            {overlaySeries.map((series) => {
              const isVisible = visibilityOverrides[series.sampleId] ?? series.visible
              return (
                <Button
                  key={series.sampleId}
                  variant={isVisible ? "default" : "outline"}
                  size="sm"
                  onClick={() => setVisibilityOverrides((prev) => ({ ...prev, [series.sampleId]: !isVisible }))}
                  className="gap-1.5 h-7 text-xs max-w-36"
                >
                  {isVisible ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: series.color }} />
                  <span className="truncate">{series.label}</span>
                </Button>
              )
            })}
          </div>
        </div>
      )}
      
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData}>
            <defs>
              {preparedSeries.map((series) => (
                <linearGradient key={series.sampleId} id={`color_${series.chartKey}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={series.color} stopOpacity={series.isPrimary ? 0.85 : 0.6} />
                  <stop offset="95%" stopColor={series.color} stopOpacity={0.08} />
                </linearGradient>
              ))}
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
              domain={[0, 'auto']}
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
            
            {preparedSeries.length > 1 && <Legend />}

            {preparedSeries.map((series) => (
              <Area
                key={series.sampleId}
                type="monotone"
                dataKey={series.chartKey}
                name={series.label}
                stroke={series.color}
                strokeWidth={series.isPrimary ? 2.5 : 2}
                fillOpacity={series.isPrimary ? 0.55 : 0.35}
                fill={`url(#color_${series.chartKey})`}
              />
            ))}

            {/* Primary percentile lines */}
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
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
