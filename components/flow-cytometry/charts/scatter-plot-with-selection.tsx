"use client"

import { useState, useMemo, useCallback, useRef } from "react"
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ZAxis,
  Legend,
  Brush,
  ReferenceArea,
} from "recharts"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Download, ZoomIn, ZoomOut, Maximize2, RefreshCw, Box } from "lucide-react"
import { cn } from "@/lib/utils"

export interface ScatterDataPoint {
  x: number
  y: number
  index?: number
  isAnomaly?: boolean
  isSelected?: boolean
  diameter?: number  // Estimated particle diameter in nm
}

interface ScatterPlotChartProps {
  title: string
  xLabel: string
  yLabel: string
  data?: ScatterDataPoint[]
  anomalousIndices?: number[]
  highlightAnomalies?: boolean
  showLegend?: boolean
  height?: number
  onSelectionChange?: (selectedIndices: number[]) => void
}

interface SelectionBox {
  x1: number
  y1: number
  x2: number
  y2: number
}

export function ScatterPlotChart({
  title,
  xLabel,
  yLabel,
  data,
  anomalousIndices = [],
  highlightAnomalies = true,
  showLegend = true,
  height = 320,
  onSelectionChange,
}: ScatterPlotChartProps) {
  const [selectedPoints, setSelectedPoints] = useState<Set<number>>(new Set())
  const [selectionMode, setSelectionMode] = useState(false)
  const [selectionBox, setSelectionBox] = useState<SelectionBox | null>(null)
  const [isSelecting, setIsSelecting] = useState(false)
  const [zoom, setZoom] = useState({ xMin: null, xMax: null, yMin: null, yMax: null })
  const chartRef = useRef<any>(null)

  // Process data to separate normal, anomalous, and selected points
  const { normalData, anomalyData, selectedData } = useMemo(() => {
    if (!data || data.length === 0) {
      // Generate sample data for demo
      const normal = []
      const anomalies = []
      const selected = []

      for (let i = 0; i < 500; i++) {
        const x = Math.random() * 1000 + 100
        const y = x * (0.8 + Math.random() * 0.4) + Math.random() * 200

        const point = { x, y, z: 20, index: i }

        if (selectedPoints.has(i)) {
          selected.push({ ...point, z: 50 })
        } else if (Math.random() > 0.95) {
          anomalies.push({ ...point, z: 50 })
        } else {
          normal.push(point)
        }
      }

      return { normalData: normal, anomalyData: anomalies, selectedData: selected }
    }

    // Real data processing
    const anomalySet = new Set(anomalousIndices)
    const normal: Array<{ x: number; y: number; z: number; index: number }> = []
    const anomalies: Array<{ x: number; y: number; z: number; index: number }> = []
    const selected: Array<{ x: number; y: number; z: number; index: number }> = []

    data.forEach((point, idx) => {
      const pointIndex = point.index ?? idx
      const dataPoint = {
        x: point.x,
        y: point.y,
        z: 20,
        index: pointIndex,
      }

      if (selectedPoints.has(pointIndex)) {
        selected.push({ ...dataPoint, z: 60 })
      } else if (highlightAnomalies && anomalySet.has(pointIndex)) {
        anomalies.push({ ...dataPoint, z: 50 })
      } else {
        normal.push(dataPoint)
      }
    })

    return { normalData: normal, anomalyData: anomalies, selectedData: selected }
  }, [data, anomalousIndices, highlightAnomalies, selectedPoints])

  const totalPoints = normalData.length + anomalyData.length + selectedData.length
  const anomalyPercentage = totalPoints > 0 ? ((anomalyData.length / totalPoints) * 100).toFixed(2) : "0.00"
  const selectionPercentage = totalPoints > 0 ? ((selectedData.length / totalPoints) * 100).toFixed(2) : "0.00"

  // Box selection handlers
  const handleMouseDown = useCallback(
    (e: any) => {
      if (!selectionMode || !e) return

      const { chartX, chartY } = e
      if (chartX && chartY) {
        setIsSelecting(true)
        setSelectionBox({ x1: chartX, y1: chartY, x2: chartX, y2: chartY })
      }
    },
    [selectionMode]
  )

  const handleMouseMove = useCallback(
    (e: any) => {
      if (!isSelecting || !selectionBox || !selectionMode || !e) return

      const { chartX, chartY } = e
      if (chartX && chartY) {
        setSelectionBox({ ...selectionBox, x2: chartX, y2: chartY })
      }
    },
    [isSelecting, selectionBox, selectionMode]
  )

  const handleMouseUp = useCallback(() => {
    if (!isSelecting || !selectionBox || !data) return

    setIsSelecting(false)

    const { x1, y1, x2, y2 } = selectionBox
    const minX = Math.min(x1, x2)
    const maxX = Math.max(x1, x2)
    const minY = Math.min(y1, y2)
    const maxY = Math.max(y1, y2)

    // Select points within the box
    const newSelected = new Set<number>()
    data.forEach((point, idx) => {
      const pointIndex = point.index ?? idx
      if (point.x >= minX && point.x <= maxX && point.y >= minY && point.y <= maxY) {
        newSelected.add(pointIndex)
      }
    })

    setSelectedPoints(newSelected)
    setSelectionBox(null)

    // Notify parent component
    if (onSelectionChange) {
      onSelectionChange(Array.from(newSelected))
    }
  }, [isSelecting, selectionBox, data, onSelectionChange])

  const handleZoomIn = () => {
    // Zoom to selected area if points are selected
    if (selectedData.length > 0) {
      const xValues = selectedData.map((p) => p.x)
      const yValues = selectedData.map((p) => p.y)
      const xMin = Math.min(...xValues) * 0.9
      const xMax = Math.max(...xValues) * 1.1
      const yMin = Math.min(...yValues) * 0.9
      const yMax = Math.max(...yValues) * 1.1
      setZoom({ xMin, xMax, yMin, yMax } as any)
    }
  }

  const handleZoomOut = () => {
    setZoom({ xMin: null, xMax: null, yMin: null, yMax: null })
  }

  const handleClearSelection = () => {
    setSelectedPoints(new Set())
    setSelectionBox(null)
    if (onSelectionChange) {
      onSelectionChange([])
    }
  }

  const handleExportSelection = () => {
    if (selectedPoints.size === 0 || !data) return

    const selectedData = Array.from(selectedPoints)
      .map((idx) => data.find((p) => (p.index ?? data.indexOf(p)) === idx))
      .filter(Boolean)

    const csv = [
      ["Index", xLabel, yLabel],
      ...selectedData.map((p) => [p!.index, p!.x, p!.y]),
    ]
      .map((row) => row.join(","))
      .join("\n")

    const blob = new Blob([csv], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `scatter_selection_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <Card className="card-3d">
      <CardHeader className="pb-3">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <CardTitle className="text-base md:text-lg">{title}</CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant={selectionMode ? "default" : "outline"}
              onClick={() => setSelectionMode(!selectionMode)}
              className="h-8"
            >
              <Box className="h-3.5 w-3.5 mr-1.5" />
              {selectionMode ? "Selecting..." : "Box Select"}
            </Button>
            {selectedPoints.size > 0 && (
              <>
                <Button size="sm" variant="outline" onClick={handleZoomIn} className="h-8">
                  <ZoomIn className="h-3.5 w-3.5 mr-1.5" />
                  Zoom to Selection
                </Button>
                <Button size="sm" variant="outline" onClick={handleExportSelection} className="h-8">
                  <Download className="h-3.5 w-3.5 mr-1.5" />
                  Export ({selectedPoints.size})
                </Button>
                <Button size="sm" variant="ghost" onClick={handleClearSelection} className="h-8">
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                  Clear
                </Button>
              </>
            )}
            {zoom.xMin && (
              <Button size="sm" variant="outline" onClick={handleZoomOut} className="h-8">
                <ZoomOut className="h-3.5 w-3.5 mr-1.5" />
                Reset Zoom
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {/* Stats Header */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
          <span>Total: {totalPoints.toLocaleString()}</span>
          <span>•</span>
          <span>Normal: {normalData.length.toLocaleString()}</span>
          {anomalyData.length > 0 && highlightAnomalies && (
            <>
              <span>•</span>
              <span className="flex items-center gap-1">
                Anomalies:
                <Badge variant="destructive" className="h-5 px-1.5 text-xs">
                  {anomalyData.length.toLocaleString()} ({anomalyPercentage}%)
                </Badge>
              </span>
            </>
          )}
          {selectedData.length > 0 && (
            <>
              <span>•</span>
              <span className="flex items-center gap-1">
                Selected:
                <Badge variant="default" className="h-5 px-1.5 text-xs bg-green-600">
                  {selectedData.length.toLocaleString()} ({selectionPercentage}%)
                </Badge>
              </span>
            </>
          )}
        </div>

        {selectionMode && (
          <div className="rounded-md bg-blue-500/10 border border-blue-500/30 p-2 text-xs text-blue-600 dark:text-blue-400">
            ℹ️ Click and drag on the chart to select a region
          </div>
        )}

        {/* Chart */}
        <div style={{ height: `${height}px` }} className={cn(selectionMode && "cursor-crosshair")}>
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart
              ref={chartRef}
              margin={{ top: 10, right: 20, bottom: 20, left: 10 }}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="x"
                type="number"
                stroke="#64748b"
                tick={{ fontSize: 11 }}
                label={{ value: xLabel, position: "bottom", offset: -5, fill: "#64748b", fontSize: 12 }}
                domain={zoom.xMin ? [zoom.xMin, zoom.xMax] : ["auto", "auto"]}
              />
              <YAxis
                dataKey="y"
                type="number"
                stroke="#64748b"
                tick={{ fontSize: 11 }}
                label={{ value: yLabel, angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 12 }}
                domain={zoom.yMin ? [zoom.yMin, zoom.yMax] : ["auto", "auto"]}
              />
              <ZAxis dataKey="z" range={[20, 100]} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1e293b",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
                formatter={(value: number) => value.toFixed(1)}
                labelFormatter={(label) => `Event: ${label}`}
              />
              {showLegend && (
                <Legend wrapperStyle={{ fontSize: "12px" }} iconType="circle" verticalAlign="top" height={36} />
              )}

              {/* Selection box overlay */}
              {selectionBox && isSelecting && (
                <ReferenceArea
                  x1={selectionBox.x1}
                  y1={selectionBox.y1}
                  x2={selectionBox.x2}
                  y2={selectionBox.y2}
                  strokeOpacity={0.3}
                  fillOpacity={0.1}
                  fill="#3b82f6"
                  stroke="#3b82f6"
                />
              )}

              <Scatter name="Normal Events" data={normalData} fill="#3b82f6" fillOpacity={0.6} shape="circle" />
              {anomalyData.length > 0 && highlightAnomalies && (
                <Scatter name="Anomalous Events" data={anomalyData} fill="#ef4444" fillOpacity={0.9} shape="circle" />
              )}
              {selectedData.length > 0 && (
                <Scatter name="Selected Events" data={selectedData} fill="#22c55e" fillOpacity={0.9} shape="circle" />
              )}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
