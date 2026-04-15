"use client"

import { useMemo, useState, useEffect, useRef, useCallback, memo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Loader2, Download, Pin, ZoomIn, ZoomOut, RotateCcw } from "lucide-react"
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
} from "recharts"
import { useAnalysisStore } from "@/lib/store"
import { useShallow } from "zustand/shallow"
import { useApi } from "@/hooks/use-api"
import { computeCursorZoomWindow, computePannedWindow, getPlotRatiosFromMouse, type ZoomWindow } from "./wheel-zoom-utils"

interface EventSizeDataPoint {
  eventId: number
  size: number
  valid: boolean
  fsc?: number
  ssc?: number
}

interface EventVsSizeChartProps {
  sampleId: string
  onPin?: () => void
  title?: string
}

const buildRangeLabel = (name: string, min: number, max: number) => {
  const baseName = (name || "").trim()
  if (!baseName) return `${min}-${max}nm`
  if (baseName.includes("(") && baseName.includes(")")) return baseName
  return `${baseName} (${min}-${max}nm)`
}

export const EventVsSizeChart = memo(function EventVsSizeChart({ sampleId, onPin, title = "Event vs Size" }: EventVsSizeChartProps) {
  const { fcsAnalysisSettings, fcsAnalysis } = useAnalysisStore(useShallow((s) => ({
    fcsAnalysisSettings: s.fcsAnalysisSettings,
    fcsAnalysis: s.fcsAnalysis,
  })))
  const { getFCSValues } = useApi()

  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<EventSizeDataPoint[]>([])
  const [statistics, setStatistics] = useState<{
    d10: number
    d50: number
    d90: number
    mean: number
    std: number
    validCount: number
    totalCount: number
  } | null>(null)
  const [zoom, setZoom] = useState<ZoomWindow>({ xMin: null, xMax: null, yMin: null, yMax: null })
  const [error, setError] = useState<string | null>(null)
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const [isPanning, setIsPanning] = useState(false)
  const [lastPanPoint, setLastPanPoint] = useState<{ x: number; y: number } | null>(null)

  // Get size ranges from settings for coloring — stabilize reference with useMemo
  const sizeRanges = useMemo(() => fcsAnalysis.sizeRanges || [
    { name: "Small EVs", min: 0, max: 50, color: "#22c55e" },
    { name: "Exosomes", min: 50, max: 200, color: "#3b82f6" },
    { name: "Microvesicles", min: 200, max: 1000, color: "#f59e0b" },
  ], [fcsAnalysis.sizeRanges])

  // Fetch data when sampleId or settings change
  useEffect(() => {
    if (!sampleId) {
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)

    getFCSValues(sampleId, {
      wavelength_nm: fcsAnalysisSettings?.laserWavelength || 488,
      n_particle: fcsAnalysisSettings?.particleRI || 1.40,
      n_medium: fcsAnalysisSettings?.mediumRI || 1.33,
      max_events: 7000,
      include_raw_channels: true,
    })
      .then((result) => {
        if (cancelled) return

        if (result && result.events) {
          // Transform data for chart
          const chartData: EventSizeDataPoint[] = result.events.map((event) => ({
            eventId: event.event_id,
            size: event.diameter_nm || 0,
            valid: event.valid,
            fsc: event.fsc,
            ssc: event.ssc,
          }))

          setData(chartData)

          // Set statistics
          if (result.statistics) {
            setStatistics({
              d10: result.statistics.d10_nm,
              d50: result.statistics.d50_nm,
              d90: result.statistics.d90_nm,
              mean: result.statistics.mean_nm,
              std: result.statistics.std_nm,
              validCount: result.data_info.valid_sizes,
              totalCount: result.data_info.returned_events,
            })
          }
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load data")
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sampleId, fcsAnalysisSettings?.laserWavelength, fcsAnalysisSettings?.particleRI, fcsAnalysisSettings?.mediumRI])

  // Color function based on size ranges
  const getPointColor = (size: number): string => {
    for (const range of sizeRanges) {
      if (size >= range.min && size < range.max) {
        return range.color || "#3b82f6"
      }
    }
    return "#6b7280" // Gray for out-of-range
  }

  // Process data with colors
  const processedData = useMemo(() => {
    const filtered = data
      .filter((d) => d.valid && d.size > 0)
      .map((d) => ({
        ...d,
        fill: getPointColor(d.size),
      }))

    const maxDisplayPoints = 2500
    if (filtered.length <= maxDisplayPoints) return filtered

    const step = Math.ceil(filtered.length / maxDisplayPoints)
    return filtered.filter((_, i) => i % step === 0)
  }, [data, sizeRanges])

  const chartBounds = useMemo(() => {
    if (processedData.length === 0) {
      return { minX: 0, maxX: 1, minY: 0, maxY: 500 }
    }

    const eventIds = processedData.map((d) => d.eventId)
    const sizes = processedData.map((d) => d.size)

    return {
      minX: Math.min(...eventIds),
      maxX: Math.max(...eventIds),
      minY: Math.max(0, Math.min(...sizes) - 10),
      maxY: Math.min(1000, Math.max(...sizes) + 10),
    }
  }, [processedData])

  const xDomain = useMemo<[number, number]>(() => {
    if (zoom.xMin !== null && zoom.xMax !== null) return [zoom.xMin, zoom.xMax]
    return [chartBounds.minX, chartBounds.maxX]
  }, [zoom.xMin, zoom.xMax, chartBounds])

  const yDomain = useMemo<[number, number]>(() => {
    if (zoom.yMin !== null && zoom.yMax !== null) return [zoom.yMin, zoom.yMax]
    return [chartBounds.minY, chartBounds.maxY]
  }, [zoom.yMin, zoom.yMax, chartBounds])

  const handleWheelZoom = useCallback((e: React.WheelEvent<HTMLDivElement>) => {
    const container = chartContainerRef.current
    if (!container) return

    const ratios = getPlotRatiosFromMouse(e.clientX, e.clientY, container.getBoundingClientRect(), {
      top: 10,
      right: 30,
      bottom: 30,
      left: 10,
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
      right: 30,
      bottom: 30,
      left: 10,
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
    const plotWidth = rect.width - 10 - 30
    const plotHeight = rect.height - 10 - 30

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

  const handleZoomIn = () => {
    setZoom((prev) => computeCursorZoomWindow(prev, chartBounds, { xRatio: 0.5, yRatio: 0.5 }, -1))
  }

  const handleZoomOut = () => {
    setZoom((prev) => computeCursorZoomWindow(prev, chartBounds, { xRatio: 0.5, yRatio: 0.5 }, 1))
  }

  const handleResetZoom = () => {
    setZoom({ xMin: null, xMax: null, yMin: null, yMax: null })
  }

  const handleExport = () => {
    // Export as CSV
    const csv = [
      "Event ID,Size (nm),Valid,FSC,SSC",
      ...data.map((d) => `${d.eventId},${d.size.toFixed(1)},${d.valid},${d.fsc || ""},${d.ssc || ""}`),
    ].join("\n")

    const blob = new Blob([csv], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${sampleId}_event_vs_size.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return (
      <Card className="card-3d">
        <CardContent className="flex items-center justify-center h-[400px]">
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <span className="text-muted-foreground">Loading per-event sizes...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="card-3d">
        <CardContent className="flex items-center justify-center h-[400px]">
          <div className="text-center">
            <p className="text-destructive font-medium">Failed to load data</p>
            <p className="text-sm text-muted-foreground">{error}</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Show empty state if no data after loading
  if (!loading && processedData.length === 0) {
    return (
      <Card className="card-3d">
        <CardContent className="flex items-center justify-center h-[400px]">
          <div className="text-center">
            <p className="text-muted-foreground font-medium">No size data available</p>
            <p className="text-sm text-muted-foreground">
              {data.length === 0 
                ? "Upload a sample to see per-event sizes" 
                : `${data.length} events, but no valid diameter calculations`}
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="card-3d">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <CardTitle className="text-base">{title}</CardTitle>
            {statistics && (
              <Badge variant="outline" className="text-xs">
                {statistics.validCount.toLocaleString()} / {statistics.totalCount.toLocaleString()} valid
              </Badge>
            )}
          </div>
          <div className="flex gap-1">
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleZoomIn} title="Zoom In">
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleZoomOut} title="Zoom Out">
              <ZoomOut className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleResetZoom} title="Reset Zoom">
              <RotateCcw className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleExport} title="Export CSV">
              <Download className="h-4 w-4" />
            </Button>
            {onPin && (
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onPin} title="Pin to Dashboard">
                <Pin className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>

        {/* Statistics row */}
        {statistics && (
          <div className="flex flex-wrap gap-4 text-xs text-muted-foreground mt-2">
            <span>
              <strong>D10:</strong> {statistics.d10.toFixed(1)} nm
            </span>
            <span>
              <strong>D50:</strong> {statistics.d50.toFixed(1)} nm
            </span>
            <span>
              <strong>D90:</strong> {statistics.d90.toFixed(1)} nm
            </span>
            <span>
              <strong>Mean:</strong> {statistics.mean.toFixed(1)} ± {statistics.std.toFixed(1)} nm
            </span>
          </div>
        )}
      </CardHeader>

      <CardContent>
        <div
          ref={chartContainerRef}
          className="h-[350px] w-full"
          style={{ minHeight: '350px', minWidth: '300px', cursor: hasActiveZoom ? (isPanning ? "grabbing" : "grab") : "default" }}
          onWheel={handleWheelZoom}
          onMouseDown={handlePanStart}
          onMouseMove={handlePanMove}
          onMouseUp={handlePanEnd}
          onMouseLeave={handlePanEnd}
        >
          <ResponsiveContainer width="100%" height={350} minWidth={1} minHeight={1} debounce={80}>
            <ScatterChart margin={{ top: 10, right: 30, left: 10, bottom: 30 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" opacity={0.3} />
              <XAxis
                dataKey="eventId"
                type="number"
                name="Event #"
                domain={xDomain}
                allowDataOverflow
                tick={{ fill: "#999", fontSize: 10 }}
                tickFormatter={(v) => Number(v).toLocaleString()}
                label={{ value: "Event Index", position: "bottom", offset: 10, fill: "#999", fontSize: 11 }}
              />
              <YAxis
                dataKey="size"
                type="number"
                name="Size"
                domain={yDomain}
                allowDataOverflow
                tick={{ fill: "#999", fontSize: 10 }}
                label={{ value: "Estimated Diameter (nm)", angle: -90, position: "insideLeft", offset: 10, fill: "#999", fontSize: 11 }}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const d = payload[0].payload as EventSizeDataPoint
                    return (
                      <div className="bg-background/95 border rounded-lg p-2 shadow-lg text-xs">
                        <p className="font-medium">Event #{d.eventId}</p>
                        <p>Size: {d.size.toFixed(1)} nm</p>
                        {d.fsc && <p>FSC: {d.fsc.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>}
                        {d.ssc && <p>SSC: {d.ssc.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>}
                      </div>
                    )
                  }
                  return null
                }}
              />

              {/* Reference lines for D10, D50, D90 */}
              {statistics && (
                <>
                  <ReferenceLine y={statistics.d10} stroke="#22c55e" strokeDasharray="5 5" label={{ value: "D10", position: "right", fill: "#22c55e", fontSize: 10 }} />
                  <ReferenceLine y={statistics.d50} stroke="#3b82f6" strokeWidth={2} label={{ value: "D50", position: "right", fill: "#3b82f6", fontSize: 10 }} />
                  <ReferenceLine y={statistics.d90} stroke="#f59e0b" strokeDasharray="5 5" label={{ value: "D90", position: "right", fill: "#f59e0b", fontSize: 10 }} />
                </>
              )}

              <Scatter name="Particles" data={processedData} fill="#3b82f6" opacity={0.6} isAnimationActive={false} />

              <Legend
                content={() => (
                  <div className="flex justify-center flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-muted-foreground px-2">
                    {sizeRanges.map((range) => (
                      <div key={range.name} className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: range.color }} />
                        <span>{buildRangeLabel(range.name, range.min, range.max)}</span>
                      </div>
                    ))}
                  </div>
                )}
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-2 text-xs text-muted-foreground text-center">
          Displaying {processedData.length.toLocaleString()} sampled points for smooth interaction.
        </p>
      </CardContent>
    </Card>
  )
})
