"use client"

import { useMemo, useState, useEffect } from "react"
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
import { useApi } from "@/hooks/use-api"

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

export function EventVsSizeChart({ sampleId, onPin, title = "Event vs Size" }: EventVsSizeChartProps) {
  const { fcsAnalysisSettings, fcsAnalysis } = useAnalysisStore()
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
  const [zoomDomain, setZoomDomain] = useState<{ min: number; max: number } | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Get size ranges from settings for coloring
  const sizeRanges = fcsAnalysis.sizeRanges || [
    { name: "Small EVs", min: 0, max: 50, color: "#22c55e" },
    { name: "Exosomes", min: 50, max: 200, color: "#3b82f6" },
    { name: "Microvesicles", min: 200, max: 1000, color: "#f59e0b" },
  ]

  // Fetch data when sampleId or settings change
  useEffect(() => {
    if (!sampleId) {
      console.log("[EventVsSizeChart] No sampleId provided, skipping data fetch")
      return
    }

    console.log("[EventVsSizeChart] Fetching data for sampleId:", sampleId)
    let cancelled = false
    setLoading(true)
    setError(null)

    getFCSValues(sampleId, {
      wavelength_nm: fcsAnalysisSettings?.laserWavelength || 488,
      n_particle: fcsAnalysisSettings?.particleRI || 1.40,
      n_medium: fcsAnalysisSettings?.mediumRI || 1.33,
      max_events: 10000, // Sample for performance
      include_raw_channels: true,
    })
      .then((result) => {
        if (cancelled) return

        console.log("[EventVsSizeChart] Received data:", result)

        if (result && result.events) {
          // Transform data for chart
          const chartData: EventSizeDataPoint[] = result.events.map((event) => ({
            eventId: event.event_id,
            size: event.diameter_nm || 0,
            valid: event.valid,
            fsc: event.fsc,
            ssc: event.ssc,
          }))

          console.log("[EventVsSizeChart] Processed", chartData.length, "events, valid sizes:", chartData.filter(d => d.size > 0).length)
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
  }, [sampleId, fcsAnalysisSettings?.laserWavelength, fcsAnalysisSettings?.particleRI, fcsAnalysisSettings?.mediumRI, getFCSValues])

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
    return data
      .filter((d) => d.valid && d.size > 0)
      .map((d) => ({
        ...d,
        fill: getPointColor(d.size),
      }))
  }, [data, sizeRanges])

  // Calculate Y-axis domain
  const yDomain = useMemo(() => {
    if (zoomDomain) return [zoomDomain.min, zoomDomain.max]
    if (processedData.length === 0) return [0, 500]

    const sizes = processedData.map((d) => d.size)
    const min = Math.max(0, Math.min(...sizes) - 10)
    const max = Math.min(1000, Math.max(...sizes) + 10)
    return [min, max]
  }, [processedData, zoomDomain])

  const handleZoomIn = () => {
    const [min, max] = yDomain
    const range = max - min
    const newMin = min + range * 0.1
    const newMax = max - range * 0.1
    setZoomDomain({ min: newMin, max: newMax })
  }

  const handleZoomOut = () => {
    const [min, max] = yDomain
    const range = max - min
    const newMin = Math.max(0, min - range * 0.1)
    const newMax = max + range * 0.1
    setZoomDomain({ min: newMin, max: newMax })
  }

  const handleResetZoom = () => {
    setZoomDomain(null)
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
        <div className="h-[350px] w-full" style={{ minHeight: '350px', minWidth: '300px' }}>
          <ResponsiveContainer width="100%" height={350}>
            <ScatterChart margin={{ top: 10, right: 30, left: 10, bottom: 30 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" opacity={0.3} />
              <XAxis
                dataKey="eventId"
                type="number"
                name="Event #"
                tick={{ fill: "#999", fontSize: 10 }}
                label={{ value: "Event Number", position: "bottom", offset: 10, fill: "#999", fontSize: 11 }}
              />
              <YAxis
                dataKey="size"
                type="number"
                name="Size"
                domain={yDomain}
                tick={{ fill: "#999", fontSize: 10 }}
                label={{ value: "Size (nm)", angle: -90, position: "insideLeft", offset: 10, fill: "#999", fontSize: 11 }}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const d = payload[0].payload as EventSizeDataPoint
                    return (
                      <div className="bg-background/95 border rounded-lg p-2 shadow-lg text-xs">
                        <p className="font-medium">Event #{d.eventId}</p>
                        <p>Size: {d.size.toFixed(1)} nm</p>
                        {d.fsc && <p>FSC: {d.fsc.toFixed(0)}</p>}
                        {d.ssc && <p>SSC: {d.ssc.toFixed(0)}</p>}
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

              <Scatter name="Particles" data={processedData} fill="#3b82f6" opacity={0.6} />

              <Legend
                content={() => (
                  <div className="flex justify-center gap-4 mt-2 text-xs">
                    {sizeRanges.map((range) => (
                      <div key={range.name} className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: range.color }} />
                        <span>{range.name}</span>
                      </div>
                    ))}
                  </div>
                )}
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
