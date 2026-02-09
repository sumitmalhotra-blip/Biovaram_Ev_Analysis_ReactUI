"use client"

import { useState, useMemo, useCallback, useRef, useEffect } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { 
  ZoomIn, 
  ZoomOut, 
  Maximize2, 
  RefreshCw, 
  MousePointer2,
  Move,
  Save,
  Download,
  Target
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
  diameter?: number
}

interface InteractiveScatterChartProps {
  title: string
  xLabel: string
  yLabel: string
  data?: ScatterDataPoint[]
  anomalousIndices?: number[]
  highlightAnomalies?: boolean
  height?: number
  onSelectionChange?: (selectedIndices: number[], gateCoordinates?: { x1: number; y1: number; x2: number; y2: number }) => void
  onGatedAnalysis?: (selectedData: ScatterDataPoint[]) => void
}

// Chart padding/margins
const PADDING = { top: 40, right: 40, bottom: 50, left: 60 }

type InteractionMode = 'select' | 'pan' | 'none'

export function InteractiveScatterChart({
  title,
  xLabel,
  yLabel,
  data = [],
  anomalousIndices = [],
  highlightAnomalies = true,
  height = 400,
  onSelectionChange,
  onGatedAnalysis,
}: InteractiveScatterChartProps) {
  const { 
    gatingState,
    addGate,
    setSelectedIndices: setStoreSelectedIndices,
    clearAllGates
  } = useAnalysisStore()
  
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  
  // Interaction state
  const [mode, setMode] = useState<InteractionMode>('none')
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null)
  const [dragEnd, setDragEnd] = useState<{ x: number; y: number } | null>(null)
  
  // Selection state
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set())
  const [selectionRect, setSelectionRect] = useState<{ x1: number; y1: number; x2: number; y2: number } | null>(null)
  
  // Zoom/Pan state
  const [viewBox, setViewBox] = useState<{ xMin: number; xMax: number; yMin: number; yMax: number } | null>(null)
  
  // Gate dialog
  const [showGateDialog, setShowGateDialog] = useState(false)
  const [gateName, setGateName] = useState("")
  const [pendingGateCoords, setPendingGateCoords] = useState<{ x1: number; y1: number; x2: number; y2: number } | null>(null)

  // Performance: Limit displayed points
  const MAX_POINTS = 2000
  const displayData = useMemo(() => {
    if (data.length <= MAX_POINTS) return data
    const step = Math.ceil(data.length / MAX_POINTS)
    return data.filter((_, i) => i % step === 0)
  }, [data])

  // Type for bounds
  type Bounds = { minX: number; maxX: number; minY: number; maxY: number }

  // Calculate data bounds
  const dataBounds = useMemo((): Bounds => {
    if (displayData.length === 0) {
      return { minX: 0, maxX: 1000, minY: 0, maxY: 100000 }
    }
    const xs = displayData.map(p => p.x)
    const ys = displayData.map(p => p.y)
    const minX = Math.min(...xs)
    const maxX = Math.max(...xs)
    const minY = Math.min(...ys)
    const maxY = Math.max(...ys)
    // Add 5% padding
    const xPad = (maxX - minX) * 0.05 || 100
    const yPad = (maxY - minY) * 0.05 || 1000
    return {
      minX: minX - xPad,
      maxX: maxX + xPad,
      minY: minY - yPad,
      maxY: maxY + yPad
    }
  }, [displayData])

  // Current view bounds (for zoom) - convert viewBox to Bounds format
  const currentBounds: Bounds = useMemo(() => {
    if (!viewBox) return dataBounds
    return {
      minX: viewBox.xMin,
      maxX: viewBox.xMax,
      minY: viewBox.yMin,
      maxY: viewBox.yMax
    }
  }, [viewBox, dataBounds])

  // Container dimensions
  const [dimensions, setDimensions] = useState({ width: 600, height: 400 })
  
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        setDimensions({ width: rect.width, height })
      }
    }
    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [height])

  // Chart area dimensions
  const chartWidth = dimensions.width - PADDING.left - PADDING.right
  const chartHeight = dimensions.height - PADDING.top - PADDING.bottom

  // Scale functions
  const scaleX = useCallback((value: number) => {
    const { minX, maxX } = currentBounds
    return PADDING.left + ((value - minX) / (maxX - minX)) * chartWidth
  }, [currentBounds, chartWidth])

  const scaleY = useCallback((value: number) => {
    const { minY, maxY } = currentBounds
    // SVG Y is inverted
    return PADDING.top + chartHeight - ((value - minY) / (maxY - minY)) * chartHeight
  }, [currentBounds, chartHeight])

  // Inverse scale functions (pixel to data)
  const unscaleX = useCallback((pixel: number) => {
    const { minX, maxX } = currentBounds
    return minX + ((pixel - PADDING.left) / chartWidth) * (maxX - minX)
  }, [currentBounds, chartWidth])

  const unscaleY = useCallback((pixel: number) => {
    const { minY, maxY } = currentBounds
    // SVG Y is inverted
    return maxY - ((pixel - PADDING.top) / chartHeight) * (maxY - minY)
  }, [currentBounds, chartHeight])

  // Get mouse position relative to SVG
  const getMousePos = useCallback((e: React.MouseEvent) => {
    if (!svgRef.current) return { x: 0, y: 0 }
    const rect = svgRef.current.getBoundingClientRect()
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    }
  }, [])

  // Mouse handlers
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (mode === 'none') return
    e.preventDefault()
    const pos = getMousePos(e)
    
    // Check if inside chart area
    if (pos.x < PADDING.left || pos.x > dimensions.width - PADDING.right ||
        pos.y < PADDING.top || pos.y > dimensions.height - PADDING.bottom) {
      return
    }
    
    setIsDragging(true)
    setDragStart(pos)
    setDragEnd(pos)
  }, [mode, getMousePos, dimensions])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging || !dragStart) return
    e.preventDefault()
    const pos = getMousePos(e)
    
    // Clamp to chart area
    const clampedPos = {
      x: Math.max(PADDING.left, Math.min(pos.x, dimensions.width - PADDING.right)),
      y: Math.max(PADDING.top, Math.min(pos.y, dimensions.height - PADDING.bottom))
    }
    
    setDragEnd(clampedPos)
    
    if (mode === 'pan' && dragStart) {
      // Pan the view
      const dx = unscaleX(dragStart.x) - unscaleX(clampedPos.x)
      const dy = unscaleY(dragStart.y) - unscaleY(clampedPos.y)
      
      setViewBox(prev => {
        const xMin = prev ? prev.xMin : dataBounds.minX
        const xMax = prev ? prev.xMax : dataBounds.maxX
        const yMin = prev ? prev.yMin : dataBounds.minY
        const yMax = prev ? prev.yMax : dataBounds.maxY
        return {
          xMin: xMin + dx,
          xMax: xMax + dx,
          yMin: yMin + dy,
          yMax: yMax + dy
        }
      })
      setDragStart(clampedPos)
    }
  }, [isDragging, dragStart, mode, getMousePos, dimensions, unscaleX, unscaleY, dataBounds])

  const handleMouseUp = useCallback((e: React.MouseEvent) => {
    if (!isDragging || !dragStart || !dragEnd) {
      setIsDragging(false)
      return
    }
    
    e.preventDefault()
    
    if (mode === 'select') {
      // Calculate selection rectangle in data coordinates
      const x1 = unscaleX(Math.min(dragStart.x, dragEnd.x))
      const x2 = unscaleX(Math.max(dragStart.x, dragEnd.x))
      const y1 = unscaleY(Math.max(dragStart.y, dragEnd.y)) // Remember Y is inverted
      const y2 = unscaleY(Math.min(dragStart.y, dragEnd.y))
      
      // Only process if selection is meaningful
      const pixelWidth = Math.abs(dragEnd.x - dragStart.x)
      const pixelHeight = Math.abs(dragEnd.y - dragStart.y)
      
      if (pixelWidth > 5 && pixelHeight > 5) {
        // Find points inside selection
        const selected = new Set<number>()
        data.forEach((point, idx) => {
          const pointIndex = point.index ?? idx
          if (point.x >= x1 && point.x <= x2 && point.y >= y1 && point.y <= y2) {
            selected.add(pointIndex)
          }
        })
        
        setSelectedIndices(selected)
        setSelectionRect({ x1, y1, x2, y2 })
        setPendingGateCoords({ x1, y1, x2, y2 })
        
        // Update store
        const selectedArray = Array.from(selected)
        setStoreSelectedIndices(selectedArray)
        
        // Notify parent
        if (onSelectionChange) {
          onSelectionChange(selectedArray, { x1, y1, x2, y2 })
        }
        
        console.log(`[InteractiveScatter] Selected ${selected.size} points in region x=[${x1.toFixed(0)}, ${x2.toFixed(0)}], y=[${y1.toFixed(0)}, ${y2.toFixed(0)}]`)
      }
    }
    
    setIsDragging(false)
    setDragStart(null)
    setDragEnd(null)
  }, [isDragging, dragStart, dragEnd, mode, unscaleX, unscaleY, data, setStoreSelectedIndices, onSelectionChange])

  // Helper to convert viewBox to Bounds format
  const viewBoxToBounds = (vb: { xMin: number; xMax: number; yMin: number; yMax: number }): { minX: number; maxX: number; minY: number; maxY: number } => ({
    minX: vb.xMin,
    maxX: vb.xMax,
    minY: vb.yMin,
    maxY: vb.yMax
  })

  // Zoom functions
  const zoomIn = useCallback(() => {
    setViewBox(prev => {
      const bounds = prev ? viewBoxToBounds(prev) : dataBounds
      const xCenter = (bounds.minX + bounds.maxX) / 2
      const yCenter = (bounds.minY + bounds.maxY) / 2
      const xRange = (bounds.maxX - bounds.minX) * 0.5
      const yRange = (bounds.maxY - bounds.minY) * 0.5
      return {
        xMin: xCenter - xRange / 2,
        xMax: xCenter + xRange / 2,
        yMin: yCenter - yRange / 2,
        yMax: yCenter + yRange / 2
      }
    })
  }, [dataBounds])

  const zoomOut = useCallback(() => {
    setViewBox(prev => {
      if (!prev) return null
      const bounds = viewBoxToBounds(prev)
      const xCenter = (bounds.minX + bounds.maxX) / 2
      const yCenter = (bounds.minY + bounds.maxY) / 2
      const xRange = (bounds.maxX - bounds.minX) * 2
      const yRange = (bounds.maxY - bounds.minY) * 2
      
      // Check if we'd exceed original bounds
      if (xRange >= (dataBounds.maxX - dataBounds.minX) * 1.5) {
        return null // Reset to auto
      }
      
      return {
        xMin: xCenter - xRange / 2,
        xMax: xCenter + xRange / 2,
        yMin: yCenter - yRange / 2,
        yMax: yCenter + yRange / 2
      }
    })
  }, [dataBounds])

  const zoomToSelection = useCallback(() => {
    if (!selectionRect) return
    const padding = 0.1
    const xPad = (selectionRect.x2 - selectionRect.x1) * padding
    const yPad = (selectionRect.y2 - selectionRect.y1) * padding
    setViewBox({
      xMin: selectionRect.x1 - xPad,
      xMax: selectionRect.x2 + xPad,
      yMin: selectionRect.y1 - yPad,
      yMax: selectionRect.y2 + yPad
    })
  }, [selectionRect])

  const resetView = useCallback(() => {
    setViewBox(null)
  }, [])

  const clearSelection = useCallback(() => {
    setSelectedIndices(new Set())
    setSelectionRect(null)
    setPendingGateCoords(null)
    setStoreSelectedIndices([])
    if (onSelectionChange) {
      onSelectionChange([])
    }
  }, [setStoreSelectedIndices, onSelectionChange])

  // Save gate
  const handleSaveGate = useCallback(() => {
    if (!pendingGateCoords || selectedIndices.size === 0) return
    setGateName(`Gate ${gatingState.gates.length + 1}`)
    setShowGateDialog(true)
  }, [pendingGateCoords, selectedIndices.size, gatingState.gates.length])

  const confirmSaveGate = useCallback(() => {
    if (!pendingGateCoords || !gateName.trim()) return
    
    const colors = ["#22c55e", "#3b82f6", "#f59e0b", "#ec4899", "#8b5cf6", "#06b6d4"]
    const gateColor = colors[gatingState.gates.length % colors.length]
    
    const newGate: Gate = {
      id: `gate-${Date.now()}`,
      name: gateName.trim(),
      color: gateColor,
      shape: {
        type: "rectangle",
        x1: pendingGateCoords.x1,
        y1: pendingGateCoords.y1,
        x2: pendingGateCoords.x2,
        y2: pendingGateCoords.y2,
      } as RectangleGate,
      createdAt: new Date(),
      isActive: true,
    }
    
    addGate(newGate)
    setShowGateDialog(false)
    setGateName("")
  }, [pendingGateCoords, gateName, gatingState.gates.length, addGate])

  // Analyze gated population
  const handleAnalyzeGated = useCallback(() => {
    if (selectedIndices.size === 0) return
    const selectedData = data.filter((p, idx) => selectedIndices.has(p.index ?? idx))
    if (onGatedAnalysis) {
      onGatedAnalysis(selectedData)
    }
  }, [selectedIndices, data, onGatedAnalysis])

  // Generate axis ticks
  const xTicks = useMemo(() => {
    const { minX, maxX } = currentBounds
    const count = 6
    const step = (maxX - minX) / count
    return Array.from({ length: count + 1 }, (_, i) => minX + i * step)
  }, [currentBounds])

  const yTicks = useMemo(() => {
    const { minY, maxY } = currentBounds
    const count = 6
    const step = (maxY - minY) / count
    return Array.from({ length: count + 1 }, (_, i) => minY + i * step)
  }, [currentBounds])

  // Anomaly set for quick lookup
  const anomalySet = useMemo(() => new Set(anomalousIndices), [anomalousIndices])

  // Format number for display
  const formatNumber = (n: number) => {
    if (Math.abs(n) >= 1000) return (n / 1000).toFixed(1) + 'k'
    if (Math.abs(n) >= 1) return n.toFixed(0)
    return n.toFixed(2)
  }

  // Stats
  const totalPoints = data.length
  const selectedCount = selectedIndices.size
  const anomalyCount = displayData.filter((_, i) => anomalySet.has(displayData[i].index ?? i)).length

  return (
    <Card className="card-3d">
      <CardHeader className="pb-2">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base md:text-lg">{title}</CardTitle>
            <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
              <span>Total: {totalPoints.toLocaleString()}</span>
              {selectedCount > 0 && (
                <>
                  <span>•</span>
                  <Badge variant="default" className="bg-green-600 text-xs">
                    Selected: {selectedCount.toLocaleString()} ({((selectedCount / totalPoints) * 100).toFixed(1)}%)
                  </Badge>
                </>
              )}
              {highlightAnomalies && anomalyCount > 0 && (
                <>
                  <span>•</span>
                  <Badge variant="destructive" className="text-xs">
                    Anomalies: {anomalyCount}
                  </Badge>
                </>
              )}
            </div>
          </div>
          
          {/* Toolbar */}
          <div className="flex flex-wrap items-center gap-1">
            {/* Mode Selection */}
            <div className="flex items-center border rounded-md p-0.5 mr-2">
              <Button
                size="sm"
                variant={mode === 'select' ? 'default' : 'ghost'}
                onClick={() => setMode(mode === 'select' ? 'none' : 'select')}
                className="h-8 px-3"
                title="Box Select Mode"
              >
                <MousePointer2 className="h-4 w-4 mr-1" />
                Select
              </Button>
              <Button
                size="sm"
                variant={mode === 'pan' ? 'default' : 'ghost'}
                onClick={() => setMode(mode === 'pan' ? 'none' : 'pan')}
                className="h-8 px-3"
                title="Pan Mode"
              >
                <Move className="h-4 w-4 mr-1" />
                Pan
              </Button>
            </div>
            
            {/* Zoom Controls */}
            <Button size="sm" variant="outline" onClick={zoomIn} className="h-8 px-2" title="Zoom In">
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button size="sm" variant="outline" onClick={zoomOut} className="h-8 px-2" title="Zoom Out">
              <ZoomOut className="h-4 w-4" />
            </Button>
            <Button size="sm" variant="outline" onClick={resetView} className="h-8 px-2" title="Reset View">
              <Maximize2 className="h-4 w-4" />
            </Button>
            
            {/* Selection Actions */}
            {selectedCount > 0 && (
              <>
                <div className="w-px h-6 bg-border mx-1" />
                <Button size="sm" variant="outline" onClick={zoomToSelection} className="h-8 px-2" title="Zoom to Selection">
                  <Target className="h-4 w-4" />
                </Button>
                <Button size="sm" variant="default" onClick={handleSaveGate} className="h-8 bg-green-600 hover:bg-green-700">
                  <Save className="h-4 w-4 mr-1" />
                  Save Gate
                </Button>
                <Button size="sm" variant="secondary" onClick={handleAnalyzeGated} className="h-8">
                  Analyze Selection
                </Button>
                <Button size="sm" variant="ghost" onClick={clearSelection} className="h-8 px-2">
                  <RefreshCw className="h-4 w-4" />
                </Button>
              </>
            )}
            
            {/* View indicator */}
            {viewBox && (
              <Badge variant="secondary" className="h-6 text-xs">Zoomed</Badge>
            )}
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        {/* Mode indicator */}
        {mode !== 'none' && (
          <div className={cn(
            "mb-2 px-3 py-1.5 rounded-md text-sm",
            mode === 'select' ? "bg-blue-500/10 border border-blue-500/30 text-blue-600" : "bg-orange-500/10 border border-orange-500/30 text-orange-600"
          )}>
            {mode === 'select' ? '🎯 Click and drag to select a region' : '✋ Click and drag to pan the view'}
          </div>
        )}
        
        {/* SVG Chart */}
        <div 
          ref={containerRef}
          className={cn(
            "border rounded-lg overflow-hidden bg-slate-950",
            mode === 'select' && "ring-2 ring-blue-500/50",
            mode === 'pan' && "ring-2 ring-orange-500/50"
          )}
          style={{ height: `${height}px`, cursor: mode === 'select' ? 'crosshair' : mode === 'pan' ? 'grab' : 'default' }}
        >
          <svg
            ref={svgRef}
            width="100%"
            height="100%"
            viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={() => {
              if (isDragging) {
                setIsDragging(false)
                setDragStart(null)
                setDragEnd(null)
              }
            }}
          >
            {/* Background */}
            <rect width="100%" height="100%" fill="#0f172a" />
            
            {/* Grid lines */}
            <g stroke="#334155" strokeWidth="1">
              {xTicks.map((tick, i) => (
                <line key={`xgrid-${i}`} x1={scaleX(tick)} y1={PADDING.top} x2={scaleX(tick)} y2={dimensions.height - PADDING.bottom} strokeDasharray="3,3" />
              ))}
              {yTicks.map((tick, i) => (
                <line key={`ygrid-${i}`} x1={PADDING.left} y1={scaleY(tick)} x2={dimensions.width - PADDING.right} y2={scaleY(tick)} strokeDasharray="3,3" />
              ))}
            </g>
            
            {/* Chart area border */}
            <rect
              x={PADDING.left}
              y={PADDING.top}
              width={chartWidth}
              height={chartHeight}
              fill="none"
              stroke="#475569"
              strokeWidth="1"
            />
            
            {/* Saved Gates */}
            {gatingState.gates.map(gate => {
              if (gate.shape.type !== 'rectangle') return null
              const rect = gate.shape as RectangleGate
              const x = scaleX(rect.x1)
              const y = scaleY(rect.y2)
              const w = scaleX(rect.x2) - scaleX(rect.x1)
              const h = scaleY(rect.y1) - scaleY(rect.y2)
              return (
                <g key={gate.id}>
                  <rect
                    x={x}
                    y={y}
                    width={w}
                    height={h}
                    fill={gate.color}
                    fillOpacity={0.1}
                    stroke={gate.color}
                    strokeWidth={2}
                    strokeDasharray="5,5"
                  />
                  <text x={x + 4} y={y + 14} fill={gate.color} fontSize={11} fontWeight={600}>
                    {gate.name}
                  </text>
                </g>
              )
            })}
            
            {/* Current selection rectangle (in data coords) */}
            {selectionRect && !isDragging && (
              <rect
                x={scaleX(selectionRect.x1)}
                y={scaleY(selectionRect.y2)}
                width={scaleX(selectionRect.x2) - scaleX(selectionRect.x1)}
                height={scaleY(selectionRect.y1) - scaleY(selectionRect.y2)}
                fill="rgba(34, 197, 94, 0.15)"
                stroke="#22c55e"
                strokeWidth={2}
                strokeDasharray="4,4"
              />
            )}
            
            {/* Drag selection box (pixel coords) */}
            {isDragging && mode === 'select' && dragStart && dragEnd && (
              <rect
                x={Math.min(dragStart.x, dragEnd.x)}
                y={Math.min(dragStart.y, dragEnd.y)}
                width={Math.abs(dragEnd.x - dragStart.x)}
                height={Math.abs(dragEnd.y - dragStart.y)}
                fill="rgba(59, 130, 246, 0.2)"
                stroke="#3b82f6"
                strokeWidth={2}
                strokeDasharray="4,4"
              />
            )}
            
            {/* Data points - render in layers for proper z-ordering */}
            <g>
              {/* Normal points */}
              {displayData.map((point, i) => {
                const pointIndex = point.index ?? i
                const isSelected = selectedIndices.has(pointIndex)
                const isAnomaly = highlightAnomalies && anomalySet.has(pointIndex)
                
                if (isSelected || isAnomaly) return null
                
                const cx = scaleX(point.x)
                const cy = scaleY(point.y)
                
                // Skip if outside visible area
                if (cx < PADDING.left || cx > dimensions.width - PADDING.right ||
                    cy < PADDING.top || cy > dimensions.height - PADDING.bottom) {
                  return null
                }
                
                return (
                  <circle
                    key={`normal-${pointIndex}`}
                    cx={cx}
                    cy={cy}
                    r={2}
                    fill={CHART_COLORS.primary}
                    fillOpacity={0.6}
                  />
                )
              })}
              
              {/* Anomaly points */}
              {highlightAnomalies && displayData.map((point, i) => {
                const pointIndex = point.index ?? i
                if (!anomalySet.has(pointIndex) || selectedIndices.has(pointIndex)) return null
                
                const cx = scaleX(point.x)
                const cy = scaleY(point.y)
                
                if (cx < PADDING.left || cx > dimensions.width - PADDING.right ||
                    cy < PADDING.top || cy > dimensions.height - PADDING.bottom) {
                  return null
                }
                
                return (
                  <circle
                    key={`anomaly-${pointIndex}`}
                    cx={cx}
                    cy={cy}
                    r={3}
                    fill={CHART_COLORS.anomaly}
                    fillOpacity={0.9}
                  />
                )
              })}
              
              {/* Selected points (on top) */}
              {displayData.map((point, i) => {
                const pointIndex = point.index ?? i
                if (!selectedIndices.has(pointIndex)) return null
                
                const cx = scaleX(point.x)
                const cy = scaleY(point.y)
                
                if (cx < PADDING.left || cx > dimensions.width - PADDING.right ||
                    cy < PADDING.top || cy > dimensions.height - PADDING.bottom) {
                  return null
                }
                
                return (
                  <circle
                    key={`selected-${pointIndex}`}
                    cx={cx}
                    cy={cy}
                    r={3}
                    fill="#22c55e"
                    fillOpacity={0.9}
                    stroke="#fff"
                    strokeWidth={1}
                  />
                )
              })}
            </g>
            
            {/* X Axis */}
            <g transform={`translate(0, ${dimensions.height - PADDING.bottom})`}>
              <line x1={PADDING.left} y1={0} x2={dimensions.width - PADDING.right} y2={0} stroke="#64748b" />
              {xTicks.map((tick, i) => (
                <g key={`xtick-${i}`} transform={`translate(${scaleX(tick)}, 0)`}>
                  <line y2={6} stroke="#64748b" />
                  <text y={20} textAnchor="middle" fill="#64748b" fontSize={11}>
                    {formatNumber(tick)}
                  </text>
                </g>
              ))}
              <text x={(PADDING.left + dimensions.width - PADDING.right) / 2} y={40} textAnchor="middle" fill="#94a3b8" fontSize={12}>
                {xLabel}
              </text>
            </g>
            
            {/* Y Axis */}
            <g transform={`translate(${PADDING.left}, 0)`}>
              <line x1={0} y1={PADDING.top} x2={0} y2={dimensions.height - PADDING.bottom} stroke="#64748b" />
              {yTicks.map((tick, i) => (
                <g key={`ytick-${i}`} transform={`translate(0, ${scaleY(tick)})`}>
                  <line x2={-6} stroke="#64748b" />
                  <text x={-10} textAnchor="end" dominantBaseline="middle" fill="#64748b" fontSize={11}>
                    {formatNumber(tick)}
                  </text>
                </g>
              ))}
              <text 
                transform={`translate(-45, ${(PADDING.top + dimensions.height - PADDING.bottom) / 2}) rotate(-90)`}
                textAnchor="middle" 
                fill="#94a3b8" 
                fontSize={12}
              >
                {yLabel}
              </text>
            </g>
            
            {/* Legend */}
            <g transform={`translate(${dimensions.width - PADDING.right - 120}, ${PADDING.top + 10})`}>
              <circle cx={0} cy={0} r={4} fill={CHART_COLORS.primary} fillOpacity={0.6} />
              <text x={10} y={4} fill="#94a3b8" fontSize={11}>Normal Events</text>
              {highlightAnomalies && anomalyCount > 0 && (
                <>
                  <circle cx={0} cy={20} r={4} fill={CHART_COLORS.anomaly} fillOpacity={0.9} />
                  <text x={10} y={24} fill="#94a3b8" fontSize={11}>Anomalies</text>
                </>
              )}
              {selectedCount > 0 && (
                <>
                  <circle cx={0} cy={40} r={4} fill="#22c55e" stroke="#fff" strokeWidth={1} />
                  <text x={10} y={44} fill="#94a3b8" fontSize={11}>Selected</text>
                </>
              )}
            </g>
          </svg>
        </div>
      </CardContent>
      
      {/* Save Gate Dialog */}
      <Dialog open={showGateDialog} onOpenChange={setShowGateDialog}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Target className="h-5 w-5 text-green-600" />
              Save Gate
            </DialogTitle>
            <DialogDescription>
              Save this selection as a named gate for future analysis.
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
            {pendingGateCoords && (
              <div className="rounded-md bg-muted p-3 space-y-1 text-sm">
                <div className="text-muted-foreground text-xs uppercase tracking-wide mb-2">Gate Region</div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <span className="text-muted-foreground">{xLabel}:</span>{" "}
                    <span className="font-mono">{pendingGateCoords.x1.toFixed(1)} - {pendingGateCoords.x2.toFixed(1)}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">{yLabel}:</span>{" "}
                    <span className="font-mono">{pendingGateCoords.y1.toFixed(1)} - {pendingGateCoords.y2.toFixed(1)}</span>
                  </div>
                </div>
                <div className="text-muted-foreground text-xs mt-2">
                  {selectedCount.toLocaleString()} events selected ({((selectedCount / totalPoints) * 100).toFixed(1)}%)
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowGateDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={confirmSaveGate}
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
