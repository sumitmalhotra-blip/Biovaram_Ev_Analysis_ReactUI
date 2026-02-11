"use client"

import { useState, useMemo } from "react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
  Brush,
  ComposedChart,
  Area,
  Line,
} from "recharts"
import { InteractiveChartWrapper, EnhancedChartTooltip } from "@/components/charts/interactive-chart-wrapper"
import { CHART_COLORS } from "@/lib/store"
import { useAnalysisStore, type SizeRange, type ScatterDataPoint } from "@/lib/store"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Eye, EyeOff, Layers, BarChart3, TrendingUp } from "lucide-react"
import type { DistributionAnalysisResponse } from "@/lib/api-client"

interface SizeDistributionChartProps {
  data?: Array<{
    size: number
    smallEV?: number
    exosomes?: number
    largeEV?: number
    total?: number
  }>
  showControls?: boolean
  showBrush?: boolean
  d10?: number
  d50?: number
  d90?: number
  height?: number
  compact?: boolean
  binCount?: number  // TASK-019: Configurable bin count
  // Raw size data for dynamic range calculation
  sizeData?: number[]
  // Overlay support - secondary file data
  secondarySizeData?: number[]
  secondaryD10?: number
  secondaryD50?: number
  secondaryD90?: number
  // Distribution analysis results (normality tests, fits, overlays)
  distributionAnalysis?: DistributionAnalysisResponse | null
  distributionLoading?: boolean
}

// Generate sample histogram data with configurable bins and dynamic ranges
// TASK-019: Support configurable histogram bin size
// Now supports dynamic size ranges from store
const generateHistogramData = (
  binCount: number = 20, 
  sizeRanges?: SizeRange[],
  sizeData?: number[]
) => {
  const data = []
  const maxSize = 500
  const binWidth = maxSize / binCount
  
  // Default ranges if none provided
  const ranges = sizeRanges?.length ? sizeRanges : [
    { name: "Small EVs", min: 30, max: 100, color: "#22c55e" },
    { name: "Medium EVs", min: 100, max: 200, color: "#7c3aed" },
    { name: "Large EVs", min: 200, max: 500, color: "#f59e0b" },
  ]
  
  for (let i = 0; i < binCount; i++) {
    const binStart = i * binWidth
    const binEnd = (i + 1) * binWidth
    const size = Math.round(binStart + binWidth / 2)
    
    // If we have actual size data, calculate real counts
    if (sizeData && sizeData.length > 0) {
      const binData: Record<string, number | string> = { size }
      let totalCount = 0
      
      // Count particles in this bin for each size range
      ranges.forEach((range, idx) => {
        const count = sizeData.filter(s => 
          s >= binStart && s < binEnd && s >= range.min && s <= range.max
        ).length
        binData[`range${idx}`] = count
        totalCount += count
      })
      
      binData.total = totalCount
      data.push(binData)
    } else {
      // Generate sample data
      let count = 0
      // Small EVs peak around 30-40nm
      count += Math.max(0, 800 * Math.exp(-Math.pow((size - 35) / 20, 2)))
      // Exosomes peak around 100-150nm
      count += Math.max(0, 2000 * Math.exp(-Math.pow((size - 120) / 50, 2)))
      // Large EVs peak around 250-300nm
      count += Math.max(0, 600 * Math.exp(-Math.pow((size - 280) / 80, 2)))

      // Use deterministic variation based on index to avoid hydration mismatch
      const variation = 0.3 + ((Math.sin(i * 7) + 1) / 2) * 0.2
      const binData: Record<string, number | string> = { size, total: Math.round(count * variation) }
      
      // Distribute count among ranges based on bin position
      ranges.forEach((range, idx) => {
        if (size >= range.min && size <= range.max) {
          binData[`range${idx}`] = Math.round(count * 0.7)
        } else {
          binData[`range${idx}`] = 0
        }
      })
      
      data.push(binData)
    }
  }
  return data
}

// Generate demo secondary histogram data for overlay comparison
// Uses different distribution pattern to show comparison effect
const generateDemoSecondaryHistogramData = (
  binCount: number = 20, 
  sizeRanges?: SizeRange[]
) => {
  const data = []
  const maxSize = 500
  const binWidth = maxSize / binCount
  
  // Default ranges if none provided
  const ranges = sizeRanges?.length ? sizeRanges : [
    { name: "Small EVs", min: 30, max: 100, color: "#22c55e" },
    { name: "Medium EVs", min: 100, max: 200, color: "#7c3aed" },
    { name: "Large EVs", min: 200, max: 500, color: "#f59e0b" },
  ]
  
  for (let i = 0; i < binCount; i++) {
    const binStart = i * binWidth
    const binEnd = (i + 1) * binWidth
    const size = Math.round(binStart + binWidth / 2)
    
    // Generate secondary data with DIFFERENT distribution pattern
    let count = 0
    // Shifted peaks for comparison visibility
    // Small EVs peak around 45nm (shifted from primary's 35nm)
    count += Math.max(0, 700 * Math.exp(-Math.pow((size - 45) / 22, 2)))
    // Exosomes peak around 140nm (shifted from primary's 120nm)
    count += Math.max(0, 1800 * Math.exp(-Math.pow((size - 140) / 55, 2)))
    // Large EVs peak around 300nm (shifted from primary's 280nm)
    count += Math.max(0, 500 * Math.exp(-Math.pow((size - 300) / 85, 2)))

    // Use different deterministic variation pattern
    const variation = 0.35 + ((Math.sin(i * 5 + 2) + 1) / 2) * 0.25
    const binData: Record<string, number | string> = { size, total: Math.round(count * variation) }
    
    // Distribute count among ranges based on bin position
    ranges.forEach((range, idx) => {
      if (size >= range.min && size <= range.max) {
        binData[`range${idx}`] = Math.round(count * 0.65)
      } else {
        binData[`range${idx}`] = 0
      }
    })
    
    data.push(binData)
  }
  return data
}

// Custom tooltip
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload || !payload.length) return null

  const total = payload.reduce((sum: number, entry: any) => sum + (entry.value || 0), 0)

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
        <div className="flex items-center justify-between gap-4 text-xs border-t pt-1 mt-1">
          <span className="text-muted-foreground">Total:</span>
          <span className="font-bold tabular-nums">{total.toLocaleString()}</span>
        </div>
      </div>
    </div>
  )
}

export function SizeDistributionChart({ 
  data: propData,
  showControls = true,
  showBrush = false,
  d10 = 89,
  d50 = 127,
  d90 = 198,
  height = 320,
  compact = false,
  binCount: propBinCount,
  sizeData,
  secondarySizeData,
  secondaryD10,
  secondaryD50,
  secondaryD90,
  distributionAnalysis,
  distributionLoading,
}: SizeDistributionChartProps) {
  // TASK-019: Get histogram bins from store settings
  // Also get dynamic size ranges from store and overlay config
  const { fcsAnalysisSettings, fcsAnalysis, secondaryFcsAnalysis, overlayConfig } = useAnalysisStore()
  const binCount = propBinCount ?? fcsAnalysisSettings?.histogramBins ?? 20
  const sizeRanges = fcsAnalysis.sizeRanges
  
  // Overlay visibility controls
  const [showPrimary, setShowPrimary] = useState(true)
  const [showSecondary, setShowSecondary] = useState(true)
  const [showFitOverlay, setShowFitOverlay] = useState(true)
  
  // Distribution fit color mapping
  const FIT_COLORS: Record<string, string> = {
    normal: "#ef4444",     // Red
    lognorm: "#8b5cf6",    // Purple (recommended for EVs)
    gamma: "#f59e0b",      // Amber
    weibull_min: "#06b6d4", // Cyan
  }
  const FIT_LABELS: Record<string, string> = {
    normal: "Normal",
    lognorm: "Log-Normal",
    gamma: "Gamma",
    weibull_min: "Weibull",
  }

  // Convert distribution overlays to chart data points
  const fitOverlayData = useMemo(() => {
    if (!distributionAnalysis?.overlays || !showFitOverlay) return null
    
    const overlays = distributionAnalysis.overlays
    const bestFit = distributionAnalysis.distribution_fits?.best_fit_aic || "lognorm"
    
    // Merge all overlay x/y_scaled into a single array of data points
    // Each overlay has x[] and y_scaled[] arrays
    const allX = new Set<number>()
    for (const [name, overlay] of Object.entries(overlays)) {
      if (overlay?.x) {
        overlay.x.forEach((v: number) => allX.add(Math.round(v)))
      }
    }
    
    const sortedX = Array.from(allX).sort((a, b) => a - b)
    
    return sortedX.map(xVal => {
      const point: Record<string, number | null> = { fitX: xVal }
      for (const [name, overlay] of Object.entries(overlays)) {
        if (overlay?.x && overlay?.y_scaled) {
          // Find the closest index
          const idx = overlay.x.findIndex((v: number) => Math.round(v) >= xVal)
          if (idx >= 0 && idx < overlay.y_scaled.length) {
            point[`fit_${name}`] = Math.round(overlay.y_scaled[idx])
          } else {
            point[`fit_${name}`] = null
          }
        }
      }
      return point
    })
  }, [distributionAnalysis, showFitOverlay])
  
  // Check if overlay is active - allow demo data generation when no real secondary size data
  const hasRealSecondaryData = (secondarySizeData?.length || 0) > 0
  const hasOverlay = overlayConfig.enabled && secondaryFcsAnalysis.results
  
  // Generate data using dynamic size ranges
  const data = useMemo(() => {
    if (propData) return propData
    return generateHistogramData(binCount, sizeRanges, sizeData)
  }, [propData, binCount, sizeRanges, sizeData])
  
  // Generate secondary data for overlay - use real data if available, otherwise generate demo
  const secondaryData = useMemo(() => {
    if (!hasOverlay) return null
    if (hasRealSecondaryData && secondarySizeData) {
      return generateHistogramData(binCount, sizeRanges, secondarySizeData)
    }
    // Generate demo secondary data with different variation pattern
    return generateDemoSecondaryHistogramData(binCount, sizeRanges)
  }, [hasOverlay, hasRealSecondaryData, secondarySizeData, binCount, sizeRanges])
  
  // Merge primary and secondary data for overlay chart
  const overlayData = useMemo(() => {
    if (!hasOverlay || !secondaryData) return data
    
    return data.map((item, index) => ({
      ...item,
      primaryTotal: item.total || 0,
      secondaryTotal: secondaryData[index]?.total || 0,
    }))
  }, [data, secondaryData, hasOverlay])
  
  // Get range colors for bars
  const rangeColors = useMemo(() => {
    if (!sizeRanges?.length) return [CHART_COLORS.smallEV, CHART_COLORS.primary, CHART_COLORS.largeEV]
    return sizeRanges.map(r => r.color || CHART_COLORS.primary)
  }, [sizeRanges])
  
  const rangeNames = useMemo(() => {
    if (!sizeRanges?.length) return ["Small EVs (<100nm)", "Exosomes (100-200nm)", "Large EVs (>200nm)"]
    return sizeRanges.map(r => `${r.name} (${r.min}-${r.max}nm)`)
  }, [sizeRanges])
  
  const [brushDomain, setBrushDomain] = useState<{ startIndex?: number; endIndex?: number }>({})

  // Overlay header controls
  const overlayControls = hasOverlay ? (
    <div className="flex items-center gap-2 mb-2">
      <Badge variant="secondary" className="gap-1">
        <Layers className="h-3 w-3" />
        Overlay
      </Badge>
      <Button
        variant={showPrimary ? "default" : "outline"}
        size="sm"
        className="h-7 text-xs"
        onClick={() => setShowPrimary(!showPrimary)}
      >
        {showPrimary ? <Eye className="h-3 w-3 mr-1" /> : <EyeOff className="h-3 w-3 mr-1" />}
        Primary
      </Button>
      <Button
        variant={showSecondary ? "secondary" : "outline"}
        size="sm"
        className="h-7 text-xs"
        onClick={() => setShowSecondary(!showSecondary)}
      >
        {showSecondary ? <Eye className="h-3 w-3 mr-1" /> : <EyeOff className="h-3 w-3 mr-1" />}
        Comparison
      </Button>
    </div>
  ) : null

  // Distribution fit controls (shown when analysis data available)
  const fitControls = distributionAnalysis ? (
    <div className="flex items-center gap-2 mb-2">
      <Button
        variant={showFitOverlay ? "default" : "outline"}
        size="sm"
        className="h-7 text-xs gap-1"
        onClick={() => setShowFitOverlay(!showFitOverlay)}
      >
        <TrendingUp className="h-3 w-3" />
        {showFitOverlay ? "Hide Fits" : "Show Fits"}
      </Button>
      {distributionAnalysis.distribution_fits?.best_fit_aic && (
        <Badge variant="outline" className="text-xs" style={{ borderColor: FIT_COLORS[distributionAnalysis.distribution_fits.best_fit_aic] || "#8b5cf6" }}>
          Best: {FIT_LABELS[distributionAnalysis.distribution_fits.best_fit_aic] || distributionAnalysis.distribution_fits.best_fit_aic}
        </Badge>
      )}
      {distributionAnalysis.normality_tests && (
        <Badge variant={distributionAnalysis.normality_tests.is_normal ? "default" : "secondary"} className="text-xs">
          {distributionAnalysis.normality_tests.is_normal ? "Normal" : "Non-Normal"}
        </Badge>
      )}
    </div>
  ) : distributionLoading ? (
    <div className="flex items-center gap-2 mb-2">
      <Badge variant="outline" className="text-xs animate-pulse">Loading distribution fits...</Badge>
    </div>
  ) : null

  return (
    <InteractiveChartWrapper
      title={hasOverlay ? "Size Distribution (Overlay)" : "Size Distribution"}
      source="FCS Analysis"
      chartType="histogram"
      showControls={showControls && !compact}
      height={height}
      headerContent={<>{overlayControls}{fitControls}</>}
    >
      {/* Use ComposedChart for overlay mode, BarChart for single file */}
      {hasOverlay ? (
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={overlayData} barCategoryGap={0}>
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
                backgroundColor: 'rgba(0,0,0,0.9)', 
                border: 'none',
                borderRadius: '8px',
                color: 'white'
              }}
              formatter={(value: number, name: string) => [
                value?.toLocaleString(),
                name === 'primaryTotal' 
                  ? fcsAnalysis.file?.name || 'Primary'
                  : secondaryFcsAnalysis.file?.name || 'Comparison'
              ]}
            />
            <Legend 
              verticalAlign="top"
              height={36}
              formatter={(value) => value === 'primaryTotal' 
                ? (fcsAnalysis.file?.name?.slice(0, 25) || 'Primary')
                : (secondaryFcsAnalysis.file?.name?.slice(0, 25) || 'Comparison')
              }
            />
            
            {/* Primary data as area chart */}
            {showPrimary && (
              <Area
                type="stepAfter"
                dataKey="primaryTotal"
                fill={overlayConfig.primaryColor}
                fillOpacity={overlayConfig.primaryOpacity}
                stroke={overlayConfig.primaryColor}
                strokeWidth={2}
                name="primaryTotal"
              />
            )}
            
            {/* Secondary data as area chart */}
            {showSecondary && (
              <Area
                type="stepAfter"
                dataKey="secondaryTotal"
                fill={overlayConfig.secondaryColor}
                fillOpacity={overlayConfig.secondaryOpacity}
                stroke={overlayConfig.secondaryColor}
                strokeWidth={2}
                name="secondaryTotal"
              />
            )}

            {/* Primary percentile lines */}
            {showPrimary && (
              <>
                <ReferenceLine
                  x={d10}
                  stroke={overlayConfig.primaryColor}
                  strokeDasharray="5 5"
                  label={{ value: "D10", fill: overlayConfig.primaryColor, fontSize: 10 }}
                />
                <ReferenceLine
                  x={d50}
                  stroke={overlayConfig.primaryColor}
                  strokeDasharray="5 5"
                  label={{ value: "D50", fill: overlayConfig.primaryColor, fontSize: 10 }}
                />
                <ReferenceLine
                  x={d90}
                  stroke={overlayConfig.primaryColor}
                  strokeDasharray="5 5"
                  label={{ value: "D90", fill: overlayConfig.primaryColor, fontSize: 10 }}
                />
              </>
            )}
            
            {/* Secondary percentile lines */}
            {showSecondary && secondaryD50 && (
              <>
                {secondaryD10 && (
                  <ReferenceLine
                    x={secondaryD10}
                    stroke={overlayConfig.secondaryColor}
                    strokeDasharray="3 3"
                    label={{ value: "D10'", fill: overlayConfig.secondaryColor, fontSize: 10 }}
                  />
                )}
                <ReferenceLine
                  x={secondaryD50}
                  stroke={overlayConfig.secondaryColor}
                  strokeDasharray="3 3"
                  label={{ value: "D50'", fill: overlayConfig.secondaryColor, fontSize: 10 }}
                />
                {secondaryD90 && (
                  <ReferenceLine
                    x={secondaryD90}
                    stroke={overlayConfig.secondaryColor}
                    strokeDasharray="3 3"
                    label={{ value: "D90'", fill: overlayConfig.secondaryColor, fontSize: 10 }}
                  />
                )}
              </>
            )}
          </ComposedChart>
        </ResponsiveContainer>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={fitOverlayData && showFitOverlay 
            ? data.map((item, idx) => {
                // Merge fit overlay data by matching the size/fitX values
                const fitPoint = fitOverlayData?.find(f => f.fitX !== null && Math.abs((f.fitX as number) - (item.size as number)) < 15)
                return { ...item, ...(fitPoint || {}) }
              })
            : data
          } barCategoryGap={0}>
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
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "12px" }} />
            
            {/* Dynamic bars based on size ranges from store */}
            {sizeRanges?.length ? (
              sizeRanges.map((range, idx) => (
                <Bar 
                  key={range.name}
                  dataKey={`range${idx}`} 
                  stackId="a" 
                  fill={range.color || rangeColors[idx]} 
                  name={rangeNames[idx]} 
                  radius={idx === sizeRanges.length - 1 ? [2, 2, 0, 0] : [0, 0, 0, 0]} 
                />
              ))
            ) : (
              <>
                {/* Default bars if no custom ranges */}
                <Bar dataKey="range0" stackId="a" fill={CHART_COLORS.smallEV} name="Small EVs (<100nm)" radius={[0, 0, 0, 0]} />
                <Bar dataKey="range1" stackId="a" fill={CHART_COLORS.primary} name="Exosomes (100-200nm)" radius={[0, 0, 0, 0]} />
                <Bar dataKey="range2" stackId="a" fill={CHART_COLORS.largeEV} name="Large EVs (>200nm)" radius={[2, 2, 0, 0]} />
              </>
            )}

            {/* Distribution fit overlay lines */}
            {showFitOverlay && distributionAnalysis?.overlays && Object.entries(distributionAnalysis.overlays).map(([name]) => (
              <Line
                key={`fit_${name}`}
                type="monotone"
                dataKey={`fit_${name}`}
                stroke={FIT_COLORS[name] || "#888"}
                strokeWidth={name === distributionAnalysis.distribution_fits?.best_fit_aic ? 3 : 1.5}
                strokeDasharray={name === distributionAnalysis.distribution_fits?.best_fit_aic ? undefined : "4 4"}
                dot={false}
                name={FIT_LABELS[name] || name}
                connectNulls
              />
            ))}

            {/* Percentile lines */}
            <ReferenceLine
              x={d10}
              stroke="#10b981"
              strokeDasharray="5 5"
              label={{ value: "D10", fill: "#10b981", fontSize: 10 }}
            />
            <ReferenceLine
              x={d50}
              stroke="#10b981"
              strokeDasharray="5 5"
              label={{ value: "D50", fill: "#10b981", fontSize: 10 }}
            />
            <ReferenceLine
              x={d90}
              stroke="#10b981"
              strokeDasharray="5 5"
              label={{ value: "D90", fill: "#10b981", fontSize: 10 }}
            />

            {/* Brush for range selection */}
            {showBrush && (
              <Brush
                dataKey="size"
                height={30}
                stroke="hsl(var(--primary))"
                fill="hsl(var(--primary) / 0.1)"
                tickFormatter={(value) => `${value}nm`}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      )}

      {/* Distribution Analysis Summary Panel */}
      {distributionAnalysis && (
        <div className="mt-3 space-y-2">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
            {distributionAnalysis.overlays && Object.entries(distributionAnalysis.overlays).map(([name, overlay]) => {
              const fit = distributionAnalysis.distribution_fits?.fits?.[name]
              const isBest = name === distributionAnalysis.distribution_fits?.best_fit_aic
              return (
                <div
                  key={name}
                  className={`p-2 rounded-lg border ${isBest ? 'border-primary bg-primary/5' : 'border-border'}`}
                >
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: FIT_COLORS[name] || "#888" }} />
                    <span className="font-medium">{FIT_LABELS[name] || name}</span>
                    {isBest && <Badge variant="default" className="text-[10px] px-1 py-0">Best</Badge>}
                  </div>
                  {fit && (
                    <div className="text-muted-foreground space-y-0.5">
                      <div>AIC: {typeof fit.aic === 'number' ? fit.aic.toFixed(1) : fit.aic}</div>
                      {fit.ks_pvalue !== undefined && <div>KS p: {fit.ks_pvalue.toFixed(4)}</div>}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
          {distributionAnalysis.conclusion && (
            <div className="text-xs text-muted-foreground bg-muted/50 rounded-lg p-2">
              <span className="font-medium">Recommendation:</span>{" "}
              {distributionAnalysis.conclusion.recommended_distribution === "lognorm" ? "Log-Normal" : distributionAnalysis.conclusion.recommended_distribution}
              {" "}— Use {distributionAnalysis.conclusion.central_tendency_metric} = {distributionAnalysis.conclusion.central_tendency?.toFixed(1)} nm
              {distributionAnalysis.summary_statistics?.skew_interpretation && (
                <span className="ml-2">({distributionAnalysis.summary_statistics.skew_interpretation})</span>
              )}
            </div>
          )}
        </div>
      )}
    </InteractiveChartWrapper>
  )
}
