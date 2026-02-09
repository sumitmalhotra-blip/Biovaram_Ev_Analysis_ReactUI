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
  ReferenceArea,
} from "recharts"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { 
  Download, 
  ZoomIn, 
  ZoomOut, 
  Maximize2, 
  RefreshCw, 
  Box, 
  Eye, 
  EyeOff, 
  Layers, 
  Target,
  Save,
  Trash2
} from "lucide-react"
import { cn } from "@/lib/utils"
import { CHART_COLORS, useAnalysisStore, type Gate, type RectangleGate } from "@/lib/store"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

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
  onSelectionChange?: (selectedIndices: number[], gateCoordinates?: { x1: number; y1: number; x2: number; y2: number }) => void
  // Overlay support
  secondaryData?: ScatterDataPoint[]
  secondaryAnomalousIndices?: number[]
}

interface SelectionBox {
  x1: number
  y1: number
  x2: number
  y2: number
}

// Pixel-based selection for drawing the visual box
interface PixelSelectionBox {
  startX: number
  startY: number
  endX: number
  endY: number
}

// Chart margins - MUST match ScatterChart margin prop exactly (defined outside component)
const CHART_MARGINS = { top: 10, right: 20, bottom: 40, left: 50 }

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
  secondaryData,
  secondaryAnomalousIndices = [],
}: ScatterPlotChartProps) {
  const { 
    overlayConfig, 
    fcsAnalysis, 
    secondaryFcsAnalysis,
    gatingState,
    setGateActiveTool,
    addGate,
    removeGate,
    setSelectedIndices: setStoreSelectedIndices,
    clearAllGates
  } = useAnalysisStore()
  const [selectedPoints, setSelectedPoints] = useState<Set<number>>(new Set())
  const [selectionMode, setSelectionMode] = useState(false)
  const [selectionBox, setSelectionBox] = useState<SelectionBox | null>(null)
  const [pixelSelection, setPixelSelection] = useState<PixelSelectionBox | null>(null)
  const [isSelecting, setIsSelecting] = useState(false)
  const [zoom, setZoom] = useState<{ xMin: number | null; xMax: number | null; yMin: number | null; yMax: number | null }>({ 
    xMin: null, 
    xMax: null, 
    yMin: null, 
    yMax: null 
  })
  const chartRef = useRef<any>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  
  // Gate saving dialog state
  const [showSaveGateDialog, setShowSaveGateDialog] = useState(false)
  const [gateName, setGateName] = useState("")
  const [pendingGateBox, setPendingGateBox] = useState<SelectionBox | null>(null)
  
  // Overlay visibility toggles
  const [showPrimary, setShowPrimary] = useState(true)
  const [showSecondary, setShowSecondary] = useState(true)

  // PERFORMANCE FIX: Limit max points to prevent UI freeze
  const MAX_DISPLAY_POINTS = 1500
  
  // Deterministic pseudo-random for SSR compatibility
  const seededRandom = (seed: number): number => {
    const x = Math.sin(seed * 9999) * 10000
    return x - Math.floor(x)
  }
  
  // Check if overlay is active - allow demo data generation when enabled
  const hasRealSecondaryData = (secondaryData?.length || 0) > 0
  const hasOverlay = overlayConfig.enabled && secondaryFcsAnalysis.results

  // Process data to separate normal, anomalous, and selected points
  const { normalData, anomalyData, selectedData } = useMemo(() => {
    if (!data || data.length === 0) {
      // Generate sample data for demo - reduced from 500 to 200
      const normal = []
      const anomalies = []
      const selected = []

      for (let i = 0; i < 200; i++) {
        const x = seededRandom(i * 3) * 1000 + 100
        const y = x * (0.8 + seededRandom(i * 3 + 1) * 0.4) + seededRandom(i * 3 + 2) * 200

        const point = { x, y, z: 8, index: i }

        if (selectedPoints.has(i)) {
          selected.push({ ...point, z: 25 })
        } else if (seededRandom(i * 3 + 3) > 0.95) {
          anomalies.push({ ...point, z: 20 })
        } else {
          normal.push(point)
        }
      }

      return { normalData: normal, anomalyData: anomalies, selectedData: selected }
    }

    // PERFORMANCE FIX: Sample data if too large - use deterministic sampling
    let processedData = data
    if (data.length > MAX_DISPLAY_POINTS) {
      // Deterministic sampling to keep display responsive and avoid hydration issues
      const step = Math.ceil(data.length / MAX_DISPLAY_POINTS)
      processedData = data.filter((_, i) => i % step === 0)
    }

    // Real data processing
    const anomalySet = new Set(anomalousIndices)
    const normal: Array<{ x: number; y: number; z: number; index: number }> = []
    const anomalies: Array<{ x: number; y: number; z: number; index: number }> = []
    const selected: Array<{ x: number; y: number; z: number; index: number }> = []

    // Use processedData instead of data for performance
    processedData.forEach((point, idx) => {
      const pointIndex = point.index ?? idx
      const dataPoint = {
        x: point.x,
        y: point.y,
        z: 8,
        index: pointIndex,
      }

      if (selectedPoints.has(pointIndex)) {
        selected.push({ ...dataPoint, z: 25 })
      } else if (highlightAnomalies && anomalySet.has(pointIndex)) {
        anomalies.push({ ...dataPoint, z: 20 })
      } else {
        normal.push(dataPoint)
      }
    })

    return { normalData: normal, anomalyData: anomalies, selectedData: selected }
  }, [data, anomalousIndices, highlightAnomalies, selectedPoints])

  // Process secondary data for overlay - generate demo if no real data
  const { secondaryNormalData, secondaryAnomalyData } = useMemo(() => {
    if (!hasOverlay) {
      return { secondaryNormalData: [], secondaryAnomalyData: [] }
    }

    // If we have real secondary data, use it
    if (hasRealSecondaryData && secondaryData && secondaryData.length > 0) {
      // PERFORMANCE FIX: Sample secondary data if too large - use deterministic sampling
      let processedData = secondaryData
      if (secondaryData.length > MAX_DISPLAY_POINTS) {
        const step = Math.ceil(secondaryData.length / MAX_DISPLAY_POINTS)
        processedData = secondaryData.filter((_, i) => i % step === 0)
      }

      const anomalySet = new Set(secondaryAnomalousIndices)
      const normal: Array<{ x: number; y: number; z: number; index: number }> = []
      const anomalies: Array<{ x: number; y: number; z: number; index: number }> = []

      processedData.forEach((point, idx) => {
        const pointIndex = point.index ?? idx
        const dataPoint = {
          x: point.x,
          y: point.y,
          z: 8,
          index: pointIndex,
        }

        if (highlightAnomalies && anomalySet.has(pointIndex)) {
          anomalies.push({ ...dataPoint, z: 18 })
        } else {
          normal.push(dataPoint)
        }
      })

      return { secondaryNormalData: normal, secondaryAnomalyData: anomalies }
    }
    
    // Generate demo secondary data with shifted distribution
    const normal: Array<{ x: number; y: number; z: number; index: number }> = []
    const anomalies: Array<{ x: number; y: number; z: number; index: number }> = []
    
    for (let i = 0; i < 200; i++) {
      // Use different seed offset for secondary data to create visible difference
      const x = seededRandom(i * 5 + 100) * 900 + 150  // Shifted range
      const y = x * (0.75 + seededRandom(i * 5 + 101) * 0.35) + seededRandom(i * 5 + 102) * 180
      
      const point = { x, y, z: 8, index: i + 10000 }  // Offset indices to avoid collision
      
      if (seededRandom(i * 5 + 103) > 0.96) {
        anomalies.push({ ...point, z: 18 })
      } else {
        normal.push(point)
      }
    }
    
    return { secondaryNormalData: normal, secondaryAnomalyData: anomalies }
  }, [hasOverlay, hasRealSecondaryData, secondaryData, secondaryAnomalousIndices, highlightAnomalies])

  const totalPoints = normalData.length + anomalyData.length + selectedData.length
  const totalSecondaryPoints = secondaryNormalData.length + secondaryAnomalyData.length
  const anomalyPercentage = totalPoints > 0 ? ((anomalyData.length / totalPoints) * 100).toFixed(2) : "0.00"
  const selectionPercentage = totalPoints > 0 ? ((selectedData.length / totalPoints) * 100).toFixed(2) : "0.00"

  // Calculate data bounds for coordinate conversion
  const dataBounds = useMemo(() => {
    const allData = [...normalData, ...anomalyData, ...selectedData]
    if (allData.length === 0) {
      return { minX: 0, maxX: 1000, minY: 0, maxY: 1000 }
    }
    const xValues = allData.map(p => p.x)
    const yValues = allData.map(p => p.y)
    return {
      minX: Math.min(...xValues),
      maxX: Math.max(...xValues),
      minY: Math.min(...yValues),
      maxY: Math.max(...yValues),
    }
  }, [normalData, anomalyData, selectedData])

  // Convert pixel coordinates to data coordinates
  const pixelToData = useCallback((pixelX: number, pixelY: number, containerRect: DOMRect) => {
    const chartWidth = containerRect.width - CHART_MARGINS.left - CHART_MARGINS.right
    const chartHeight = containerRect.height - CHART_MARGINS.top - CHART_MARGINS.bottom
    
    // Use zoom bounds if set, otherwise use data bounds
    const xMin = zoom.xMin ?? dataBounds.minX
    const xMax = zoom.xMax ?? dataBounds.maxX
    const yMin = zoom.yMin ?? dataBounds.minY
    const yMax = zoom.yMax ?? dataBounds.maxY
    
    // Convert pixel position relative to chart area
    const chartX = pixelX - CHART_MARGINS.left
    const chartY = pixelY - CHART_MARGINS.top
    
    // Convert to data coordinates (Y is inverted in SVG coordinates)
    const dataX = xMin + (chartX / chartWidth) * (xMax - xMin)
    const dataY = yMax - (chartY / chartHeight) * (yMax - yMin)
    
    return { x: dataX, y: dataY }
  }, [dataBounds, zoom])

  // Check if pixel position is inside chart area
  const isInsideChartArea = useCallback((pixelX: number, pixelY: number, containerRect: DOMRect) => {
    return (
      pixelX >= CHART_MARGINS.left &&
      pixelX <= containerRect.width - CHART_MARGINS.right &&
      pixelY >= CHART_MARGINS.top &&
      pixelY <= containerRect.height - CHART_MARGINS.bottom
    )
  }, [])

  // NOTE: Mouse handlers are defined inline on the container div for direct event binding

  // Handle mouse wheel zoom
  const handleWheel = useCallback((e: React.WheelEvent<HTMLDivElement>) => {
    e.preventDefault()
    const zoomFactor = e.deltaY > 0 ? 1.2 : 0.8 // Scroll down = zoom out, scroll up = zoom in
    
    const currentXMin = zoom.xMin ?? dataBounds.minX
    const currentXMax = zoom.xMax ?? dataBounds.maxX
    const currentYMin = zoom.yMin ?? dataBounds.minY
    const currentYMax = zoom.yMax ?? dataBounds.maxY
    
    const xCenter = (currentXMin + currentXMax) / 2
    const yCenter = (currentYMin + currentYMax) / 2
    const xRange = (currentXMax - currentXMin) * zoomFactor
    const yRange = (currentYMax - currentYMin) * zoomFactor
    
    // Don't zoom out beyond original bounds
    if (zoomFactor > 1) {
      const newXMin = Math.max(dataBounds.minX, xCenter - xRange / 2)
      const newXMax = Math.min(dataBounds.maxX, xCenter + xRange / 2)
      const newYMin = Math.max(dataBounds.minY, yCenter - yRange / 2)
      const newYMax = Math.min(dataBounds.maxY, yCenter + yRange / 2)
      
      // If we've reached original bounds, reset to null
      if (newXMin <= dataBounds.minX && newXMax >= dataBounds.maxX) {
        setZoom({ xMin: null, xMax: null, yMin: null, yMax: null })
      } else {
        setZoom({ xMin: newXMin, xMax: newXMax, yMin: newYMin, yMax: newYMax })
      }
    } else {
      // Zooming in
      setZoom({
        xMin: xCenter - xRange / 2,
        xMax: xCenter + xRange / 2,
        yMin: yCenter - yRange / 2,
        yMax: yCenter + yRange / 2,
      })
    }
  }, [zoom, dataBounds])

  // Save current selection as a named gate
  const handleSaveGate = useCallback(() => {
    if (!pendingGateBox || selectedPoints.size === 0) return
    setShowSaveGateDialog(true)
    setGateName(`Gate ${gatingState.gates.length + 1}`)
  }, [pendingGateBox, selectedPoints.size, gatingState.gates.length])

  const handleConfirmSaveGate = useCallback(() => {
    if (!pendingGateBox || !gateName.trim()) return

    const gateShape: RectangleGate = {
      type: "rectangle",
      x1: pendingGateBox.x1,
      y1: pendingGateBox.y1,
      x2: pendingGateBox.x2,
      y2: pendingGateBox.y2,
    }

    const colors = ["#22c55e", "#3b82f6", "#f59e0b", "#ec4899", "#8b5cf6", "#06b6d4"]
    const gateColor = colors[gatingState.gates.length % colors.length]

    const newGate: Gate = {
      id: `gate-${Date.now()}`,
      name: gateName.trim(),
      color: gateColor,
      shape: gateShape,
      createdAt: new Date(),
      isActive: true,
    }

    addGate(newGate)
    setShowSaveGateDialog(false)
    setGateName("")
  }, [pendingGateBox, gateName, gatingState.gates.length, addGate])

  const handleZoomIn = () => {
    // Zoom to selected area if points are selected
    if (selectedData.length > 0) {
      const xValues = selectedData.map((p) => p.x)
      const yValues = selectedData.map((p) => p.y)
      const xMin = Math.min(...xValues) * 0.9
      const xMax = Math.max(...xValues) * 1.1
      const yMin = Math.min(...yValues) * 0.9
      const yMax = Math.max(...yValues) * 1.1
      setZoom({ xMin, xMax, yMin, yMax })
    }
  }

  const handleZoomOut = () => {
    setZoom({ xMin: null, xMax: null, yMin: null, yMax: null })
  }

  const handleClearSelection = () => {
    setSelectedPoints(new Set())
    setSelectionBox(null)
    setPixelSelection(null)
    setPendingGateBox(null)
    setStoreSelectedIndices([])
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
          <div className="flex items-center gap-2">
            <CardTitle className="text-base md:text-lg">
              {hasOverlay ? `${title} (Overlay)` : title}
            </CardTitle>
            {hasOverlay && (
              <Badge variant="secondary" className="gap-1">
                <Layers className="h-3 w-3" />
                Overlay
              </Badge>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {/* Overlay visibility controls */}
            {hasOverlay && (
              <>
                <Button
                  variant={showPrimary ? "default" : "outline"}
                  size="sm"
                  className="h-8 text-xs"
                  onClick={() => setShowPrimary(!showPrimary)}
                >
                  {showPrimary ? <Eye className="h-3 w-3 mr-1" /> : <EyeOff className="h-3 w-3 mr-1" />}
                  Primary
                </Button>
                <Button
                  variant={showSecondary ? "secondary" : "outline"}
                  size="sm"
                  className="h-8 text-xs"
                  onClick={() => setShowSecondary(!showSecondary)}
                >
                  {showSecondary ? <Eye className="h-3 w-3 mr-1" /> : <EyeOff className="h-3 w-3 mr-1" />}
                  Comparison
                </Button>
                <div className="w-px h-6 bg-border" />
              </>
            )}
            <Button
              size="sm"
              variant={selectionMode ? "default" : "outline"}
              onClick={() => {
                console.log('[ScatterPlot] Box Select clicked, toggling selectionMode from', selectionMode, 'to', !selectionMode)
                setSelectionMode(!selectionMode)
              }}
              className={cn("h-8", selectionMode && "animate-pulse")}
            >
              <Box className="h-3.5 w-3.5 mr-1.5" />
              {selectionMode ? "🎯 Drawing..." : "📦 Select Region"}
            </Button>
            {/* Always visible zoom controls */}
            <div className="flex items-center gap-1 border-l pl-2 ml-1">
              <Button 
                size="sm" 
                variant="outline" 
                onClick={() => {
                  // Zoom in to center 50%
                  const xRange = (dataBounds.maxX - dataBounds.minX) || 1000
                  const yRange = (dataBounds.maxY - dataBounds.minY) || 1000
                  const currentXMin = zoom.xMin ?? dataBounds.minX
                  const currentXMax = zoom.xMax ?? dataBounds.maxX
                  const currentYMin = zoom.yMin ?? dataBounds.minY
                  const currentYMax = zoom.yMax ?? dataBounds.maxY
                  const curXRange = currentXMax - currentXMin
                  const curYRange = currentYMax - currentYMin
                  setZoom({
                    xMin: currentXMin + curXRange * 0.25,
                    xMax: currentXMax - curXRange * 0.25,
                    yMin: currentYMin + curYRange * 0.25,
                    yMax: currentYMax - curYRange * 0.25,
                  })
                }} 
                className="h-8 px-2"
                title="Zoom In"
              >
                <ZoomIn className="h-4 w-4" />
              </Button>
              <Button 
                size="sm" 
                variant="outline" 
                onClick={handleZoomOut} 
                className="h-8 px-2"
                title="Zoom Out / Reset"
              >
                <ZoomOut className="h-4 w-4" />
              </Button>
              <Button 
                size="sm" 
                variant="outline" 
                onClick={() => setZoom({ xMin: null, xMax: null, yMin: null, yMax: null })} 
                className="h-8 px-2"
                title="Reset View"
              >
                <Maximize2 className="h-4 w-4" />
              </Button>
            </div>
            {selectedPoints.size > 0 && (
              <>
                <Button 
                  size="sm" 
                  variant="default" 
                  onClick={handleSaveGate} 
                  className="h-8 bg-green-600 hover:bg-green-700"
                >
                  <Save className="h-3.5 w-3.5 mr-1.5" />
                  Save Gate
                </Button>
                <Button size="sm" variant="outline" onClick={handleZoomIn} className="h-8">
                  <Target className="h-3.5 w-3.5 mr-1.5" />
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
            {gatingState.gates.length > 0 && (
              <Button 
                size="sm" 
                variant="ghost" 
                onClick={clearAllGates} 
                className="h-8 text-destructive"
              >
                <Trash2 className="h-3.5 w-3.5 mr-1.5" />
                Clear Gates ({gatingState.gates.length})
              </Button>
            )}
            {zoom.xMin !== null && (
              <Badge variant="secondary" className="h-6 px-2 text-xs">
                Zoomed
              </Badge>
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
          {/* Saved gates indicator */}
          {gatingState.gates.length > 0 && (
            <>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Target className="h-3 w-3" />
                Gates:
                <Badge variant="outline" className="h-5 px-1.5 text-xs">
                  {gatingState.gates.length}
                </Badge>
              </span>
            </>
          )}
          {/* Overlay stats */}
          {hasOverlay && totalSecondaryPoints > 0 && (
            <>
              <span>|</span>
              <span style={{ color: overlayConfig.secondaryColor }}>
                Comparison: {totalSecondaryPoints.toLocaleString()}
              </span>
            </>
          )}
        </div>

        {selectionMode && (
          <div className="rounded-md bg-blue-500/10 border border-blue-500/30 p-2 text-xs text-blue-600 dark:text-blue-400 mb-2">
            ✏️ <strong>Box Select Mode Active:</strong> Click and drag anywhere on the chart to select particles. Release to complete selection.
          </div>
        )}

        {/* Chart Container with Selection Overlay */}
        <div 
          ref={containerRef}
          style={{ 
            height: `${height}px`, 
            position: 'relative',
            touchAction: 'none', // Prevent touch scrolling during selection
            cursor: selectionMode ? 'crosshair' : 'default',
            userSelect: 'none', // Prevent text selection during drag
          }} 
          className={cn(
            "border rounded-lg overflow-hidden",
            selectionMode && "ring-2 ring-blue-500 ring-opacity-50 bg-blue-500/5"
          )}
          onWheel={handleWheel}
        >
          {/* Transparent interaction layer for selection - sits on top of chart when selection mode is active */}
          {selectionMode && (
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                zIndex: 40,
                cursor: 'crosshair',
                backgroundColor: 'rgba(59, 130, 246, 0.05)', // Slight blue tint to show it's active
              }}
              onMouseDown={(e) => {
                console.log('[ScatterPlot] MouseDown on interaction layer')
                e.preventDefault()
                e.stopPropagation()
                const rect = containerRef.current?.getBoundingClientRect()
                if (!rect) {
                  console.log('[ScatterPlot] No container rect!')
                  return
                }
                const pixelX = e.clientX - rect.left
                const pixelY = e.clientY - rect.top
                console.log('[ScatterPlot] Mouse position:', pixelX, pixelY)
                
                // Only start selection if inside chart area
                if (!isInsideChartArea(pixelX, pixelY, rect)) {
                  console.log('[ScatterPlot] Outside chart area')
                  return
                }
                
                console.log('[ScatterPlot] Starting selection')
                setIsSelecting(true)
                setPixelSelection({ startX: pixelX, startY: pixelY, endX: pixelX, endY: pixelY })
              }}
              onMouseMove={(e) => {
                if (!isSelecting || !pixelSelection) return
                e.preventDefault()
                e.stopPropagation()
                const rect = containerRef.current?.getBoundingClientRect()
                if (!rect) return
                let pixelX = e.clientX - rect.left
                let pixelY = e.clientY - rect.top
                
                // Clamp to chart area bounds
                pixelX = Math.max(CHART_MARGINS.left, Math.min(pixelX, rect.width - CHART_MARGINS.right))
                pixelY = Math.max(CHART_MARGINS.top, Math.min(pixelY, rect.height - CHART_MARGINS.bottom))
                
                setPixelSelection(prev => prev ? { ...prev, endX: pixelX, endY: pixelY } : null)
              }}
              onMouseUp={(e) => {
                if (!isSelecting || !pixelSelection) {
                  setIsSelecting(false)
                  return
                }
                
                e.preventDefault()
                e.stopPropagation()
                setIsSelecting(false)
                
                const rect = containerRef.current?.getBoundingClientRect()
                if (!rect) return
                
                // Convert pixel selection to data coordinates
                const start = pixelToData(pixelSelection.startX, pixelSelection.startY, rect)
                const end = pixelToData(pixelSelection.endX, pixelSelection.endY, rect)
                
                const minX = Math.min(start.x, end.x)
                const maxX = Math.max(start.x, end.x)
                const minY = Math.min(start.y, end.y)
                const maxY = Math.max(start.y, end.y)
                
                // Only process if selection is meaningful (not just a click)
                const selWidth = Math.abs(pixelSelection.endX - pixelSelection.startX)
                const selHeight = Math.abs(pixelSelection.endY - pixelSelection.startY)
                if (selWidth < 5 && selHeight < 5) {
                  setPixelSelection(null)
                  return
                }

                // Select points within the box
                const sourceData = data && data.length > 0 
                  ? data 
                  : normalData.map((p, i) => ({ x: p.x, y: p.y, index: p.index ?? i }))
                const newSelected = new Set<number>()
                
                sourceData.forEach((point, idx) => {
                  const pointIndex = point.index ?? idx
                  if (point.x >= minX && point.x <= maxX && point.y >= minY && point.y <= maxY) {
                    newSelected.add(pointIndex)
                  }
                })

                console.log(`[ScatterPlot] Selected ${newSelected.size} points in region: x=[${minX.toFixed(0)}, ${maxX.toFixed(0)}], y=[${minY.toFixed(0)}, ${maxY.toFixed(0)}]`)
                
                setSelectedPoints(newSelected)
                
                // Store selection box for potential gate saving
                const gateCoords = { x1: minX, y1: minY, x2: maxX, y2: maxY }
                setSelectionBox(gateCoords)
                setPendingGateBox(gateCoords)
                setPixelSelection(null)

                // Update global store with selected indices
                const selectedIndicesArray = Array.from(newSelected)
                setStoreSelectedIndices(selectedIndicesArray)

                // Notify parent component with gate coordinates
                if (onSelectionChange) {
                  onSelectionChange(selectedIndicesArray, gateCoords)
                }
              }}
              onMouseLeave={() => {
                if (isSelecting) {
                  setIsSelecting(false)
                  setPixelSelection(null)
                }
              }}
            />
          )}
          {/* Selection box visual feedback - properly positioned within chart area */}
          {pixelSelection && isSelecting && (
            <div
              style={{
                position: 'absolute',
                left: `${Math.min(pixelSelection.startX, pixelSelection.endX)}px`,
                top: `${Math.min(pixelSelection.startY, pixelSelection.endY)}px`,
                width: `${Math.abs(pixelSelection.endX - pixelSelection.startX)}px`,
                height: `${Math.abs(pixelSelection.endY - pixelSelection.startY)}px`,
                backgroundColor: 'rgba(59, 130, 246, 0.25)',
                border: '2px dashed rgba(59, 130, 246, 1)',
                borderRadius: '4px',
                pointerEvents: 'none',
                zIndex: 100,
                boxShadow: '0 0 10px rgba(59, 130, 246, 0.5)',
              }}
            />
          )}
          
          {/* Instructions overlay when selection mode is active but not selecting */}
          {selectionMode && !isSelecting && selectedPoints.size === 0 && (
            <div
              style={{
                position: 'absolute',
                left: `${CHART_MARGINS.left}px`,
                top: `${CHART_MARGINS.top}px`,
                right: `${CHART_MARGINS.right}px`,
                bottom: `${CHART_MARGINS.bottom}px`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                pointerEvents: 'none',
                zIndex: 30,
              }}
            >
              <div className="bg-blue-500/80 text-white px-4 py-2 rounded-lg text-sm font-medium shadow-lg animate-pulse">
                Click and drag to select particles
              </div>
            </div>
          )}
          
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart
              ref={chartRef}
              margin={{ top: 10, right: 20, bottom: 40, left: 50 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="x"
                type="number"
                stroke="#64748b"
                tick={{ fontSize: 11 }}
                label={{ value: xLabel, position: "bottom", offset: -5, fill: "#64748b", fontSize: 12 }}
                domain={zoom.xMin !== null && zoom.xMax !== null ? [zoom.xMin, zoom.xMax] : ["dataMin", "dataMax"]}
                allowDataOverflow={true}
              />
              <YAxis
                dataKey="y"
                type="number"
                stroke="#64748b"
                tick={{ fontSize: 11 }}
                label={{ value: yLabel, angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 12 }}
                domain={zoom.yMin !== null && zoom.yMax !== null ? [zoom.yMin, zoom.yMax] : ["dataMin", "dataMax"]}
                allowDataOverflow={true}
              />
              <ZAxis dataKey="z" range={[8, 40]} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1e293b",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                  fontSize: "12px",
                  color: "#f8fafc",
                }}
                labelStyle={{ color: "#94a3b8" }}
                formatter={(value: number) => value.toFixed(1)}
                labelFormatter={(label) => `Event: ${label}`}
              />
              {showLegend && (
                <Legend wrapperStyle={{ fontSize: "12px" }} iconType="circle" verticalAlign="top" height={36} />
              )}

              {/* Primary data - Normal Events */}
              {showPrimary && (
                <Scatter 
                  name={hasOverlay ? (fcsAnalysis.file?.name?.slice(0, 20) || "Primary") : "Normal Events"} 
                  data={normalData} 
                  fill={hasOverlay ? overlayConfig.primaryColor : CHART_COLORS.primary} 
                  fillOpacity={hasOverlay ? overlayConfig.primaryOpacity : 0.6} 
                  shape="circle" 
                />
              )}
              
              {/* Primary data - Anomalies */}
              {showPrimary && anomalyData.length > 0 && highlightAnomalies && (
                <Scatter name="Anomalous Events" data={anomalyData} fill="#ef4444" fillOpacity={0.9} shape="circle" />
              )}
              
              {/* Secondary data for overlay */}
              {hasOverlay && showSecondary && secondaryNormalData.length > 0 && (
                <Scatter 
                  name={secondaryFcsAnalysis.file?.name?.slice(0, 20) || "Comparison"} 
                  data={secondaryNormalData} 
                  fill={overlayConfig.secondaryColor} 
                  fillOpacity={overlayConfig.secondaryOpacity} 
                  shape="circle" 
                />
              )}
              
              {/* Secondary data - Anomalies */}
              {hasOverlay && showSecondary && secondaryAnomalyData.length > 0 && highlightAnomalies && (
                <Scatter 
                  name="Comparison Anomalies" 
                  data={secondaryAnomalyData} 
                  fill="#f97316" 
                  fillOpacity={0.8} 
                  shape="diamond" 
                />
              )}
              
              {/* Selected events always on top */}
              {selectedData.length > 0 && (
                <Scatter name="Selected Events" data={selectedData} fill="#22c55e" fillOpacity={0.9} shape="circle" />
              )}

              {/* Render saved gates as ReferenceAreas */}
              {gatingState.gates.map((gate) => {
                if (gate.shape.type === "rectangle") {
                  const rect = gate.shape
                  return (
                    <ReferenceArea
                      key={gate.id}
                      x1={rect.x1}
                      y1={rect.y1}
                      x2={rect.x2}
                      y2={rect.y2}
                      stroke={gate.color}
                      strokeWidth={2}
                      strokeDasharray="5 5"
                      fill={gate.color}
                      fillOpacity={0.1}
                      label={{
                        value: gate.name,
                        position: "insideTopLeft",
                        fill: gate.color,
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                    />
                  )
                }
                return null
              })}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </CardContent>

      {/* Save Gate Dialog */}
      <Dialog open={showSaveGateDialog} onOpenChange={setShowSaveGateDialog}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Target className="h-5 w-5 text-green-600" />
              Save Gate
            </DialogTitle>
            <DialogDescription>
              Save this selection as a named gate for future reference and analysis.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="gateName">Gate Name</Label>
              <Input
                id="gateName"
                value={gateName}
                onChange={(e) => setGateName(e.target.value)}
                placeholder="Enter gate name..."
                autoFocus
              />
            </div>
            {pendingGateBox && (
              <div className="rounded-md bg-muted p-3 space-y-1 text-sm">
                <div className="text-muted-foreground text-xs uppercase tracking-wide mb-2">Gate Region</div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <span className="text-muted-foreground">{xLabel}:</span>{" "}
                    <span className="font-mono">{pendingGateBox.x1.toFixed(1)} - {pendingGateBox.x2.toFixed(1)}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">{yLabel}:</span>{" "}
                    <span className="font-mono">{pendingGateBox.y1.toFixed(1)} - {pendingGateBox.y2.toFixed(1)}</span>
                  </div>
                </div>
                <div className="text-muted-foreground text-xs mt-2">
                  {selectedPoints.size.toLocaleString()} events selected ({selectionPercentage}%)
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSaveGateDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleConfirmSaveGate}
              disabled={!gateName.trim()}
              className="bg-green-600 hover:bg-green-700"
            >
              <Save className="h-4 w-4 mr-2" />
              Save Gate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
