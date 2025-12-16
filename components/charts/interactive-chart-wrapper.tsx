"use client"

import { useState, useRef, useCallback, type ReactNode } from "react"
import {
  ResponsiveContainer,
  Brush,
  ReferenceArea,
} from "recharts"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { 
  ZoomIn, 
  ZoomOut, 
  Move, 
  RotateCcw, 
  Camera,
  Maximize2,
  Download
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useAnalysisStore, type SavedImage } from "@/lib/store"
import { useToast } from "@/hooks/use-toast"
import { captureChartAsImage } from "@/components/dashboard/saved-images-gallery"

interface ZoomState {
  left: number | string
  right: number | string
  top: number | string
  bottom: number | string
  refAreaLeft: number | string
  refAreaRight: number | string
}

interface InteractiveChartWrapperProps {
  children: ReactNode
  className?: string
  title?: string
  source?: string
  chartType?: SavedImage['chartType']
  data?: any[]
  dataKey?: string
  xAxisKey?: string
  yAxisKey?: string
  height?: number | string
  showControls?: boolean
  showBrush?: boolean
  brushDataKey?: string
  onZoom?: (domain: { x?: [number, number]; y?: [number, number] }) => void
  onReset?: () => void
  enableCapture?: boolean
}

const initialZoomState: ZoomState = {
  left: "dataMin",
  right: "dataMax",
  top: "dataMax+5%",
  bottom: "dataMin-5%",
  refAreaLeft: "",
  refAreaRight: "",
}

/**
 * Interactive Chart Wrapper
 * Provides zoom, pan, brush, and capture functionality for Recharts charts
 */
export function InteractiveChartWrapper({
  children,
  className,
  title = "Chart",
  source = "Analysis",
  chartType = "line",
  data,
  dataKey,
  xAxisKey = "x",
  yAxisKey = "y",
  height = 400,
  showControls = true,
  showBrush = false,
  brushDataKey,
  onZoom,
  onReset,
  enableCapture = true,
}: InteractiveChartWrapperProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const { saveImage } = useAnalysisStore()
  const { toast } = useToast()

  const [zoomState, setZoomState] = useState<ZoomState>(initialZoomState)
  const [isSelecting, setIsSelecting] = useState(false)
  const [zoomLevel, setZoomLevel] = useState(1)
  const [isCapturing, setIsCapturing] = useState(false)

  // Handle zoom in
  const handleZoomIn = useCallback(() => {
    setZoomLevel((prev) => Math.min(prev * 1.5, 10))
    toast({
      title: "Zoomed In",
      description: `Zoom level: ${Math.round(Math.min(zoomLevel * 1.5, 10) * 100)}%`,
    })
  }, [zoomLevel, toast])

  // Handle zoom out
  const handleZoomOut = useCallback(() => {
    setZoomLevel((prev) => Math.max(prev / 1.5, 0.5))
    toast({
      title: "Zoomed Out",
      description: `Zoom level: ${Math.round(Math.max(zoomLevel / 1.5, 0.5) * 100)}%`,
    })
  }, [zoomLevel, toast])

  // Handle reset
  const handleReset = useCallback(() => {
    setZoomState(initialZoomState)
    setZoomLevel(1)
    onReset?.()
    toast({
      title: "Chart Reset",
      description: "Zoom and selection have been reset.",
    })
  }, [onReset, toast])

  // Handle mouse down for selection
  const handleMouseDown = useCallback((e: any) => {
    if (e && e.activeLabel) {
      setZoomState((prev) => ({
        ...prev,
        refAreaLeft: e.activeLabel,
      }))
      setIsSelecting(true)
    }
  }, [])

  // Handle mouse move for selection
  const handleMouseMove = useCallback((e: any) => {
    if (isSelecting && e && e.activeLabel) {
      setZoomState((prev) => ({
        ...prev,
        refAreaRight: e.activeLabel,
      }))
    }
  }, [isSelecting])

  // Handle mouse up for selection zoom
  const handleMouseUp = useCallback(() => {
    if (!isSelecting) return
    setIsSelecting(false)

    const { refAreaLeft, refAreaRight } = zoomState
    if (refAreaLeft === refAreaRight || refAreaRight === "") {
      setZoomState((prev) => ({
        ...prev,
        refAreaLeft: "",
        refAreaRight: "",
      }))
      return
    }

    // Ensure left < right
    const [left, right] = refAreaLeft < refAreaRight 
      ? [refAreaLeft, refAreaRight] 
      : [refAreaRight, refAreaLeft]

    setZoomState({
      ...zoomState,
      left,
      right,
      refAreaLeft: "",
      refAreaRight: "",
    })

    onZoom?.({ x: [left as number, right as number] })
  }, [isSelecting, zoomState, onZoom])

  // Handle chart capture
  const handleCapture = useCallback(async () => {
    if (!chartRef.current || isCapturing) return
    
    setIsCapturing(true)
    try {
      const image = await captureChartAsImage(
        chartRef.current,
        title,
        source,
        chartType,
        { format: "png", quality: 0.95 }
      )
      
      if (image) {
        saveImage(image)
        toast({
          title: "Chart Saved",
          description: `${title} has been saved to the gallery.`,
        })
      } else {
        toast({
          title: "Capture Failed",
          description: "Unable to capture the chart. Please try again.",
          variant: "destructive",
        })
      }
    } catch (error) {
      console.error("Chart capture error:", error)
      toast({
        title: "Capture Error",
        description: "An error occurred while capturing the chart.",
        variant: "destructive",
      })
    } finally {
      setIsCapturing(false)
    }
  }, [chartRef, isCapturing, title, source, chartType, saveImage, toast])

  // Handle download
  const handleDownload = useCallback(async () => {
    if (!chartRef.current) return
    
    setIsCapturing(true)
    try {
      const image = await captureChartAsImage(
        chartRef.current,
        title,
        source,
        chartType,
        { format: "png", quality: 0.95 }
      )
      
      if (image) {
        const link = document.createElement("a")
        link.href = image.dataUrl
        link.download = `${title.replace(/\s+/g, "_")}_${new Date().toISOString().slice(0, 10)}.png`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        
        toast({
          title: "Chart Downloaded",
          description: `${title} has been downloaded.`,
        })
      }
    } catch (error) {
      console.error("Download error:", error)
    } finally {
      setIsCapturing(false)
    }
  }, [chartRef, title, source, chartType, toast])

  return (
    <div className={cn("relative", className)}>
      {/* Controls */}
      {showControls && (
        <div className="absolute top-2 right-2 z-10 flex items-center gap-1 bg-background/80 backdrop-blur-sm rounded-lg p-1 border border-border/50">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={handleZoomIn}
                >
                  <ZoomIn className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Zoom In</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={handleZoomOut}
                >
                  <ZoomOut className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Zoom Out</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={handleReset}
                >
                  <RotateCcw className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Reset View</TooltipContent>
            </Tooltip>

            <div className="w-px h-4 bg-border mx-1" />

            {enableCapture && (
              <>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={handleCapture}
                      disabled={isCapturing}
                    >
                      <Camera className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Save to Gallery</TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={handleDownload}
                      disabled={isCapturing}
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Download Image</TooltipContent>
                </Tooltip>
              </>
            )}
          </TooltipProvider>
        </div>
      )}

      {/* Zoom Level Indicator */}
      {zoomLevel !== 1 && (
        <div className="absolute top-2 left-2 z-10 bg-background/80 backdrop-blur-sm rounded-md px-2 py-1 text-xs font-mono border border-border/50">
          {Math.round(zoomLevel * 100)}%
        </div>
      )}

      {/* Chart Container */}
      <div 
        ref={chartRef}
        className="w-full"
        style={{ 
          height: typeof height === "number" ? `${height}px` : height,
          transform: `scale(${zoomLevel})`,
          transformOrigin: "center center",
        }}
      >
        {children}
      </div>

      {/* Selection instructions */}
      {isSelecting && (
        <div className="absolute bottom-2 left-2 bg-primary/90 text-primary-foreground text-xs px-2 py-1 rounded">
          Drag to select zoom area
        </div>
      )}
    </div>
  )
}

/**
 * Enhanced Tooltip Component for Charts
 * Provides better styling and more information
 */
interface EnhancedTooltipProps {
  active?: boolean
  payload?: any[]
  label?: string | number
  formatter?: (value: number, name: string, props: any) => string
  labelFormatter?: (label: string | number) => string
  unit?: string
  precision?: number
}

export function EnhancedChartTooltip({
  active,
  payload,
  label,
  formatter,
  labelFormatter,
  unit = "",
  precision = 2,
}: EnhancedTooltipProps) {
  if (!active || !payload || !payload.length) return null

  return (
    <div className="bg-background/95 backdrop-blur-sm border border-border rounded-lg p-3 shadow-lg min-w-[150px]">
      {label !== undefined && (
        <p className="font-semibold text-sm mb-2 border-b pb-1">
          {labelFormatter ? labelFormatter(label) : label}
        </p>
      )}
      <div className="space-y-1.5">
        {payload.map((entry, index) => {
          const value = typeof entry.value === "number" 
            ? entry.value.toFixed(precision) 
            : entry.value
          const displayValue = formatter 
            ? formatter(entry.value, entry.name, entry) 
            : `${value}${unit}`

          return (
            <div key={index} className="flex items-center justify-between gap-4 text-xs">
              <span className="flex items-center gap-1.5">
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: entry.color || entry.fill }}
                />
                <span className="text-muted-foreground">{entry.name}:</span>
              </span>
              <span className="font-medium tabular-nums">{displayValue}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/**
 * Brush component for range selection
 * Can be added to any Recharts chart
 */
interface ChartBrushProps {
  dataKey: string
  height?: number
  stroke?: string
  fill?: string
  tickFormatter?: (value: any) => string
}

export function ChartBrush({
  dataKey,
  height = 30,
  stroke = "hsl(var(--primary))",
  fill = "hsl(var(--primary) / 0.1)",
  tickFormatter,
}: ChartBrushProps) {
  return (
    <Brush
      dataKey={dataKey}
      height={height}
      stroke={stroke}
      fill={fill}
      tickFormatter={tickFormatter}
    />
  )
}

/**
 * Reference Area for zoom selection
 */
interface ZoomSelectionAreaProps {
  x1?: number | string
  x2?: number | string
  y1?: number | string
  y2?: number | string
}

export function ZoomSelectionArea({ x1, x2, y1, y2 }: ZoomSelectionAreaProps) {
  if (!x1 || !x2) return null
  
  return (
    <ReferenceArea
      x1={x1}
      x2={x2}
      y1={y1}
      y2={y2}
      strokeOpacity={0.3}
      fill="hsl(var(--primary))"
      fillOpacity={0.1}
    />
  )
}
