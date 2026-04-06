"use client"

import { useEffect, useMemo, useState } from "react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, Legend } from "recharts"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Eye, EyeOff, Layers, BarChart3 } from "lucide-react"
import type { NTAResult } from "@/lib/api-client"
import type { NTASizeBin } from "@/lib/store"
import { computeNTABinsForProfile } from "@/lib/nta-size-profiles"
import { useAnalysisStore } from "@/lib/store"

interface ConcentrationProfileChartProps {
  data?: NTAResult
  overlaySeries?: Array<{
    sampleId: string
    label: string
    color: string
    visible: boolean
    isPrimary: boolean
    result: NTAResult
  }>
  bins: NTASizeBin[]
  showOverlayControls?: boolean
}

// Generate concentration profile from size bins
const generateConcentrationData = (results: NTAResult | undefined, bins: NTASizeBin[]) => {
  if (!results) {
    return null
  }

  const computed = computeNTABinsForProfile(results, bins)
  return computed.map((bin, index) => ({
    position: index + 1,
    range: `${bin.min}-${bin.max}nm`,
    concentration: bin.concentration,
    percentage: bin.percentage,
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
  overlaySeries = [],
  bins,
  showOverlayControls = true,
}: ConcentrationProfileChartProps) {
  const [visibilityOverrides, setVisibilityOverrides] = useState<Record<string, boolean>>({})
  const [debouncedOverlaySeries, setDebouncedOverlaySeries] = useState(overlaySeries)
  const { ntaCompareSession, setNTACompareComputedSeriesCacheEntry } = useAnalysisStore()
  const profileKey = useMemo(
    () => bins.map((bin) => `${bin.min}-${bin.max}`).join("|"),
    [bins]
  )

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedOverlaySeries(overlaySeries)
    }, 120)
    return () => window.clearTimeout(timer)
  }, [overlaySeries, profileKey])

  const primaryData = useMemo(() => generateConcentrationData(results, bins), [results, bins])

  const preparedSeries = useMemo(() => {
    const visible = debouncedOverlaySeries.filter((series) => visibilityOverrides[series.sampleId] ?? series.visible)
    const sorted = [...visible].sort((a, b) => {
      if (a.isPrimary === b.isPrimary) return 0
      return a.isPrimary ? -1 : 1
    })

    return sorted.map((series, index) => {
      const cacheKey = `conc:${series.sampleId}:${series.result.id ?? "no-result-id"}:${profileKey}`
      const cached = ntaCompareSession.computedSeriesCacheByKey[cacheKey]
      const cachedData = cached?.points?.map((point, pointIndex) => ({
        position: point.x,
        range: point.label || `Bin ${pointIndex + 1}`,
        concentration: point.y,
        percentage: 0,
      }))
      const generated = cachedData && cachedData.length > 0
        ? cachedData
        : generateConcentrationData(series.result, bins)

      return {
        ...series,
        cacheKey,
        shouldCache: !cached,
        chartKey: `series_${index}`,
        data: generated || [],
      }
    })
  }, [debouncedOverlaySeries, bins, profileKey, visibilityOverrides, ntaCompareSession.computedSeriesCacheByKey])

  useEffect(() => {
    preparedSeries.forEach((series) => {
      if (!series.shouldCache) return
      setNTACompareComputedSeriesCacheEntry({
        cacheKey: series.cacheKey,
        chartType: "concentration",
        sampleId: series.sampleId,
        profileId: profileKey,
        points: series.data.map((point) => ({
          x: point.position,
          y: point.concentration,
          label: point.range,
        })),
        updatedAt: Date.now(),
      })
    })
  }, [preparedSeries, profileKey, setNTACompareComputedSeriesCacheEntry])

  const hasOverlay = preparedSeries.length > 1

  const chartData = useMemo(() => {
    if (preparedSeries.length === 0) {
      return primaryData
    }

    const length = Math.max(...preparedSeries.map((series) => series.data.length), 0)
    return Array.from({ length }, (_, index) => {
      const first = preparedSeries[0]?.data[index]
      const row: Record<string, unknown> = {
        position: first?.position ?? index + 1,
        range: first?.range ?? `Bin ${index + 1}`,
      }

      preparedSeries.forEach((series) => {
        row[series.chartKey] = series.data[index]?.concentration || 0
      })

      return row
    })
  }, [preparedSeries, primaryData])
  
  const avgConcentration = primaryData ? primaryData.reduce((sum, d) => sum + d.concentration, 0) / primaryData.length : 0

  if (!primaryData) {
    return (
      <div className="space-y-3">
        <div className="h-80 flex flex-col items-center justify-center text-muted-foreground border border-dashed border-border rounded-lg bg-muted/10">
          <BarChart3 className="h-10 w-10 mb-3 opacity-40" />
          <p className="text-sm font-medium">No Concentration Data Available</p>
          <p className="text-xs mt-1 max-w-xs text-center">
            Upload and analyze an NTA file to see the concentration profile.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Overlay controls */}
      {preparedSeries.length > 0 && showOverlayControls && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="gap-1 bg-orange-500/20 text-orange-500 border-orange-500/50">
              <Layers className="h-3 w-3" />
              {hasOverlay ? "Concentration Multi-Overlay" : "Concentration Primary"}
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
          <BarChart data={chartData || primaryData || []}>
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
            
            {preparedSeries.length > 1 && <Legend />}

            {preparedSeries.map((series) => (
              <Bar
                key={series.sampleId}
                dataKey={series.chartKey}
                name={series.label}
                radius={[4, 4, 0, 0]}
                fill={series.color}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
