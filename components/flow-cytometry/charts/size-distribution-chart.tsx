"use client"

import { useState, useMemo, useRef, useCallback, memo } from "react"
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
import { useShallow } from "zustand/shallow"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Eye, EyeOff, Layers, BarChart3, TrendingUp } from "lucide-react"
import type { DistributionAnalysisResponse } from "@/lib/api-client"
import { computeCursorZoomWindow, computePannedWindow, getPlotRatiosFromMouse, type ZoomWindow } from "./wheel-zoom-utils"

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

// Generate histogram data from actual size data with configurable bins and dynamic ranges
// TASK-019: Support configurable histogram bin size
// Now supports dynamic size ranges from store
const generateHistogramData = (
  binCount: number = 20, 
  sizeRanges?: SizeRange[],
  sizeData?: number[],
  maxSizeOverride?: number
) => {
  // Only generate data if we have actual size data
  if (!sizeData || sizeData.length === 0) return null

  const data = []
  const observedMax = Math.max(...sizeData)
  const maxSize = Math.max(
    500,
    Math.min(5000, maxSizeOverride ?? observedMax * 1.1)
  )
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
  }
  return data
}

const shortLabel = (value: string, maxLen = 24): string => {
  if (!value) return ""
  return value.length > maxLen ? `${value.slice(0, maxLen - 1)}…` : value
}

const buildRangeLabel = (range: SizeRange): string => {
  const baseName = (range.name || "").trim()
  if (!baseName) return `${range.min}-${range.max}nm`

  // Avoid duplicated range text like "Exomeres (0-50nm) (0-50nm)".
  if (baseName.includes("(") && baseName.includes(")")) return baseName

  return `${baseName} (${range.min}-${range.max}nm)`
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

export const SizeDistributionChart = memo(function SizeDistributionChart({ 
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
  const { fcsAnalysisSettings, fcsAnalysis, secondaryFcsAnalysis, overlayConfig } = useAnalysisStore(useShallow((s) => ({
    fcsAnalysisSettings: s.fcsAnalysisSettings,
    fcsAnalysis: s.fcsAnalysis,
    secondaryFcsAnalysis: s.secondaryFcsAnalysis,
    overlayConfig: s.overlayConfig,
  })))
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

  const sharedHistogramMax = useMemo(() => {
    const allSizes = [
      ...(sizeData ?? []),
      ...(secondarySizeData ?? []),
    ].filter((v) => Number.isFinite(v) && v > 0)

    if (allSizes.length === 0) return undefined
    const observedMax = Math.max(...allSizes)
    return Math.max(500, Math.min(5000, observedMax * 1.1))
  }, [sizeData, secondarySizeData])
  
  // Generate data using dynamic size ranges
  const data = useMemo(() => {
    if (propData) return propData
    return generateHistogramData(binCount, sizeRanges, sizeData, sharedHistogramMax)
  }, [propData, binCount, sizeRanges, sizeData, sharedHistogramMax])
  
  // Generate secondary data for overlay - only use real data
  const secondaryData = useMemo(() => {
    if (!hasOverlay || !hasRealSecondaryData || !secondarySizeData) return null
    return generateHistogramData(binCount, sizeRanges, secondarySizeData, sharedHistogramMax)
  }, [hasOverlay, hasRealSecondaryData, secondarySizeData, binCount, sizeRanges, sharedHistogramMax])
  
  // Merge primary and secondary data for overlay chart
  const overlayData = useMemo(() => {
    if (!data) return data
    if (!hasOverlay) return data

    return data.map((item, index) => ({
      ...item,
      // Always expose overlay keys so Area series can render reliably.
      primaryTotal: Number(item.total || 0),
      secondaryTotal: Number(secondaryData?.[index]?.total || 0),
    }))
  }, [data, secondaryData, hasOverlay])
  
  // Get range colors for bars
  const rangeColors = useMemo(() => {
    if (!sizeRanges?.length) return [CHART_COLORS.smallEV, CHART_COLORS.primary, CHART_COLORS.largeEV]
    return sizeRanges.map(r => r.color || CHART_COLORS.primary)
  }, [sizeRanges])
  
  const rangeNames = useMemo(() => {
    if (!sizeRanges?.length) return ["Small EVs (<100nm)", "Exosomes (100-200nm)", "Large EVs (>200nm)"]
    return sizeRanges.map((r) => buildRangeLabel(r))
  }, [sizeRanges])
  
  const [brushDomain, setBrushDomain] = useState<{ startIndex?: number; endIndex?: number }>({})
  const [zoom, setZoom] = useState<ZoomWindow>({ xMin: null, xMax: null, yMin: null, yMax: null })
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const [isPanning, setIsPanning] = useState(false)
  const [lastPanPoint, setLastPanPoint] = useState<{ x: number; y: number } | null>(null)

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

  // PERFORMANCE FIX: Memoize the fit overlay merge — was previously inline in JSX,
  // running O(bins × fitPoints) on every render and creating new array reference each time
  const mergedChartData = useMemo(() => {
    if (fitOverlayData && showFitOverlay) {
      return data?.map((item) => {
        const fitPoint = fitOverlayData.find(f => f.fitX !== null && Math.abs((f.fitX as number) - (item.size as number)) < 15)
        return { ...item, ...(fitPoint || {}) }
      }) ?? null
    }
    return data
  }, [data, fitOverlayData, showFitOverlay])

  const activeChartData = hasOverlay ? overlayData : mergedChartData

  const chartBounds = useMemo(() => {
    if (!activeChartData || activeChartData.length === 0) {
      return { minX: 0, maxX: 500, minY: 0, maxY: 100 }
    }

    const sizes = activeChartData.map((d: any) => Number(d.size ?? 0))
    const yCandidates = activeChartData.flatMap((d: any) => {
      const values: number[] = []
      if (typeof d.total === "number") values.push(d.total)
      if (typeof d.primaryTotal === "number") values.push(d.primaryTotal)
      if (typeof d.secondaryTotal === "number") values.push(d.secondaryTotal)
      if (sizeRanges?.length) {
        for (let idx = 0; idx < sizeRanges.length; idx++) {
          const key = `range${idx}`
          if (typeof d[key] === "number") values.push(d[key])
        }
      }
      if (showFitOverlay && distributionAnalysis?.overlays) {
        for (const name of Object.keys(distributionAnalysis.overlays)) {
          const fitKey = `fit_${name}`
          if (typeof d[fitKey] === "number") values.push(d[fitKey])
        }
      }
      return values
    })

    const minX = Math.max(0, Math.min(...sizes))
    const maxX = Math.max(minX + 1, Math.max(...sizes))
    const maxY = Math.max(1, ...(yCandidates.length > 0 ? yCandidates : [100]))

    return { minX, maxX, minY: 0, maxY: maxY * 1.05 }
  }, [activeChartData, sizeRanges, showFitOverlay, distributionAnalysis])

  const handleWheelZoom = useCallback((e: React.WheelEvent<HTMLDivElement>) => {
    const container = chartContainerRef.current
    if (!container) return

    const ratios = getPlotRatiosFromMouse(e.clientX, e.clientY, container.getBoundingClientRect(), {
      top: 10,
      right: 16,
      bottom: 22,
      left: 6,
    })

    if (!ratios.inPlot) return

    e.preventDefault()
    setZoom((prev) => computeCursorZoomWindow(prev, chartBounds, ratios, e.deltaY))
  }, [chartBounds])

  const hasActiveZoom = zoom.xMin !== null || zoom.yMin !== null

  const handlePanStart = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!hasActiveZoom) return
    const container = chartContainerRef.current
    if (!container) return

    const ratios = getPlotRatiosFromMouse(e.clientX, e.clientY, container.getBoundingClientRect(), {
      top: 10,
      right: 16,
      bottom: 22,
      left: 6,
    })
    if (!ratios.inPlot) return

    setIsPanning(true)
    setLastPanPoint({ x: e.clientX, y: e.clientY })
  }, [hasActiveZoom])

  const handlePanMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!isPanning || !lastPanPoint) return

    const container = chartContainerRef.current
    if (!container) return

    const rect = container.getBoundingClientRect()
    const plotWidth = rect.width - 6 - 16
    const plotHeight = rect.height - 10 - 22

    setZoom((prev) =>
      computePannedWindow(
        prev,
        chartBounds,
        e.clientX - lastPanPoint.x,
        e.clientY - lastPanPoint.y,
        plotWidth,
        plotHeight
      )
    )
    setLastPanPoint({ x: e.clientX, y: e.clientY })
  }, [isPanning, lastPanPoint, chartBounds])

  const handlePanEnd = useCallback(() => {
    setIsPanning(false)
    setLastPanPoint(null)
  }, [])

  if (!data) {
    return (
      <InteractiveChartWrapper
        title="Size Distribution"
        source="FCS Analysis"
        chartType="histogram"
        showControls={false}
        height={height}
      >
        <div className="h-full flex flex-col items-center justify-center text-muted-foreground border border-dashed border-border rounded-lg bg-muted/10">
          <BarChart3 className="h-10 w-10 mb-3 opacity-40" />
          <p className="text-sm font-medium">No Size Distribution Data</p>
          <p className="text-xs mt-1 max-w-xs text-center">
            Upload and analyze an FCS file to see the particle size distribution.
          </p>
        </div>
      </InteractiveChartWrapper>
    )
  }

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
        <div
          ref={chartContainerRef}
          className="h-full w-full"
          style={{ cursor: hasActiveZoom ? (isPanning ? "grabbing" : "grab") : "default" }}
          onWheel={handleWheelZoom}
          onMouseDown={handlePanStart}
          onMouseMove={handlePanMove}
          onMouseUp={handlePanEnd}
          onMouseLeave={handlePanEnd}
        >
        <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1} debounce={80}>
          <ComposedChart data={overlayData} barCategoryGap={0} margin={{ top: 10, right: 16, left: 6, bottom: 22 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="size"
              type="number"
              stroke="#64748b"
              domain={zoom.xMin !== null && zoom.xMax !== null ? [zoom.xMin, zoom.xMax] : [chartBounds.minX, chartBounds.maxX]}
              allowDataOverflow
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => `${Math.round(v)}`}
              label={{ value: "Diameter (nm)", position: "bottom", offset: 0, fill: "#64748b", fontSize: 12 }}
            />
            <YAxis
              type="number"
              stroke="#64748b"
              tick={{ fontSize: 11 }}
              domain={zoom.yMin !== null && zoom.yMax !== null ? [zoom.yMin, zoom.yMax] : [chartBounds.minY, chartBounds.maxY]}
              allowDataOverflow
              label={{ value: "Event Count", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 12 }}
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
              verticalAlign="bottom"
              height={compact ? 56 : 44}
              wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }}
              formatter={(value) => value === 'primaryTotal' 
                ? shortLabel(fcsAnalysis.file?.name || 'Primary')
                : shortLabel(secondaryFcsAnalysis.file?.name || 'Comparison')
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
                isAnimationActive={false}
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
                isAnimationActive={false}
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
        </div>
      ) : (
        <div
          ref={chartContainerRef}
          className="h-full w-full"
          style={{ cursor: hasActiveZoom ? (isPanning ? "grabbing" : "grab") : "default" }}
          onWheel={handleWheelZoom}
          onMouseDown={handlePanStart}
          onMouseMove={handlePanMove}
          onMouseUp={handlePanEnd}
          onMouseLeave={handlePanEnd}
        >
        <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1} debounce={80}>
          <ComposedChart data={mergedChartData} barCategoryGap={0} margin={{ top: 10, right: 16, left: 6, bottom: 22 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="size"
              type="number"
              stroke="#64748b"
              domain={zoom.xMin !== null && zoom.xMax !== null ? [zoom.xMin, zoom.xMax] : [chartBounds.minX, chartBounds.maxX]}
              allowDataOverflow
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => `${Math.round(v)}`}
              label={{ value: "Diameter (nm)", position: "bottom", offset: 0, fill: "#64748b", fontSize: 12 }}
            />
            <YAxis
              type="number"
              stroke="#64748b"
              tick={{ fontSize: 11 }}
              domain={zoom.yMin !== null && zoom.yMax !== null ? [zoom.yMin, zoom.yMax] : [chartBounds.minY, chartBounds.maxY]}
              allowDataOverflow
              label={{ value: "Event Count", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 12 }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              verticalAlign="bottom"
              height={compact ? 56 : 44}
              wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }}
              formatter={(value) => shortLabel(String(value), compact ? 22 : 28)}
            />
            
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
                  isAnimationActive={false}
                />
              ))
            ) : (
              <>
                {/* Default bars if no custom ranges */}
                <Bar dataKey="range0" stackId="a" fill={CHART_COLORS.smallEV} name="Small EVs (<100nm)" radius={[0, 0, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="range1" stackId="a" fill={CHART_COLORS.primary} name="Exosomes (100-200nm)" radius={[0, 0, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="range2" stackId="a" fill={CHART_COLORS.largeEV} name="Large EVs (>200nm)" radius={[2, 2, 0, 0]} isAnimationActive={false} />
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
                isAnimationActive={false}
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
        </div>
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
})
