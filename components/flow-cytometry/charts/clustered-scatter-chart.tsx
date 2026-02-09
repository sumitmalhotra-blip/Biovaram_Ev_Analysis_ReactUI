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
  Layers,
  Circle,
  Loader2
} from "lucide-react"
import { cn } from "@/lib/utils"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

// Types for clustered data
export interface ClusterData {
  id: number
  cx: number
  cy: number
  count: number
  radius: number
  std_x: number
  std_y: number
  pct: number
  avg_diameter: number | null
}

export interface IndividualPoint {
  x: number
  y: number
  index: number
  diameter?: number
}

export interface ClusteredScatterResponse {
  sample_id: string
  zoom_level: number
  total_events: number
  clusters: ClusterData[] | null
  bounds: {
    x_min: number
    x_max: number
    y_min: number
    y_max: number
  }
  viewport?: {
    x_min: number
    x_max: number
    y_min: number
    y_max: number
  }
  channels: {
    fsc: string
    ssc: string
  }
  individual_points: IndividualPoint[] | null
}

interface ClusteredScatterChartProps {
  sampleId: string
  title?: string
  xLabel?: string
  yLabel?: string
  height?: number
  onClusterClick?: (cluster: ClusterData) => void
  apiBaseUrl?: string
}

// Chart padding/margins
const PADDING = { top: 40, right: 40, bottom: 50, left: 70 }

// Color palette for clusters (colorblind-friendly)
const CLUSTER_COLORS = [
  "#2563eb", // Blue
  "#dc2626", // Red
  "#16a34a", // Green
  "#9333ea", // Purple
  "#ea580c", // Orange
  "#0891b2", // Cyan
  "#ca8a04", // Yellow
  "#be185d", // Pink
  "#4f46e5", // Indigo
  "#059669", // Emerald
]

export function ClusteredScatterChart({
  sampleId,
  title = "Scatter Plot (Clustered View)",
  xLabel = "FSC",
  yLabel = "SSC",
  height = 500,
  onClusterClick,
  apiBaseUrl = "http://localhost:8000/api"
}: ClusteredScatterChartProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  
  // State
  const [zoomLevel, setZoomLevel] = useState(1)
  const [data, setData] = useState<ClusteredScatterResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hoveredCluster, setHoveredCluster] = useState<ClusterData | null>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 })
  
  // Viewport for zoom level 3
  const [viewport, setViewport] = useState<{
    x_min: number
    x_max: number
    y_min: number
    y_max: number
  } | null>(null)

  // Update dimensions on resize
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

  // Fetch clustered data
  const fetchClusteredData = useCallback(async (level: number, vp?: typeof viewport) => {
    setLoading(true)
    setError(null)
    
    try {
      let url = `${apiBaseUrl}/samples/${sampleId}/clustered-scatter?zoom_level=${level}`
      
      if (level === 3 && vp) {
        url += `&viewport_x_min=${vp.x_min}&viewport_x_max=${vp.x_max}`
        url += `&viewport_y_min=${vp.y_min}&viewport_y_max=${vp.y_max}`
      }
      
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch data: ${response.statusText}`)
      }
      
      const result: ClusteredScatterResponse = await response.json()
      setData(result)
      
      // Set initial viewport from bounds if not set
      if (!viewport && result.bounds) {
        setViewport({
          x_min: result.bounds.x_min,
          x_max: result.bounds.x_max,
          y_min: result.bounds.y_min,
          y_max: result.bounds.y_max
        })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [apiBaseUrl, sampleId, viewport])

  // Fetch on mount and zoom change
  useEffect(() => {
    fetchClusteredData(zoomLevel, zoomLevel === 3 ? viewport : undefined)
  }, [zoomLevel, fetchClusteredData])

  // Calculate chart dimensions
  const chartWidth = dimensions.width - PADDING.left - PADDING.right
  const chartHeight = dimensions.height - PADDING.top - PADDING.bottom

  // Scale functions
  const scales = useMemo(() => {
    if (!data?.bounds) return null
    
    const bounds = viewport || data.bounds
    
    const xScale = (value: number) => {
      return PADDING.left + ((value - bounds.x_min) / (bounds.x_max - bounds.x_min)) * chartWidth
    }
    
    const yScale = (value: number) => {
      // Invert Y axis (SVG Y increases downward)
      return PADDING.top + chartHeight - ((value - bounds.y_min) / (bounds.y_max - bounds.y_min)) * chartHeight
    }
    
    const xInverse = (pixel: number) => {
      return bounds.x_min + ((pixel - PADDING.left) / chartWidth) * (bounds.x_max - bounds.x_min)
    }
    
    const yInverse = (pixel: number) => {
      return bounds.y_min + ((PADDING.top + chartHeight - pixel) / chartHeight) * (bounds.y_max - bounds.y_min)
    }
    
    return { xScale, yScale, xInverse, yInverse, bounds }
  }, [data?.bounds, viewport, chartWidth, chartHeight])

  // Handle zoom in on cluster click
  const handleClusterClick = useCallback((cluster: ClusterData) => {
    if (onClusterClick) {
      onClusterClick(cluster)
    }
    
    // Zoom into the cluster region
    if (scales) {
      const newViewport = {
        x_min: cluster.cx - cluster.std_x * 3,
        x_max: cluster.cx + cluster.std_x * 3,
        y_min: cluster.cy - cluster.std_y * 3,
        y_max: cluster.cy + cluster.std_y * 3
      }
      setViewport(newViewport)
      
      // Increase zoom level
      if (zoomLevel < 3) {
        setZoomLevel(prev => Math.min(3, prev + 1))
      } else {
        // At max zoom, just update viewport and refetch
        fetchClusteredData(3, newViewport)
      }
    }
  }, [scales, zoomLevel, onClusterClick, fetchClusteredData])

  // Zoom controls
  const handleZoomIn = useCallback(() => {
    if (zoomLevel < 3) {
      setZoomLevel(prev => prev + 1)
    }
  }, [zoomLevel])

  const handleZoomOut = useCallback(() => {
    if (zoomLevel > 1) {
      setZoomLevel(prev => prev - 1)
      // Reset viewport when zooming out
      if (data?.bounds) {
        setViewport({
          x_min: data.bounds.x_min,
          x_max: data.bounds.x_max,
          y_min: data.bounds.y_min,
          y_max: data.bounds.y_max
        })
      }
    }
  }, [zoomLevel, data?.bounds])

  const handleReset = useCallback(() => {
    setZoomLevel(1)
    if (data?.bounds) {
      setViewport({
        x_min: data.bounds.x_min,
        x_max: data.bounds.x_max,
        y_min: data.bounds.y_min,
        y_max: data.bounds.y_max
      })
    }
    fetchClusteredData(1)
  }, [data?.bounds, fetchClusteredData])

  // Generate axis ticks
  const axisTicks = useMemo(() => {
    if (!scales) return { xTicks: [], yTicks: [] }
    
    const { bounds } = scales
    const numTicks = 5
    
    const xTicks = Array.from({ length: numTicks }, (_, i) => {
      const value = bounds.x_min + (i / (numTicks - 1)) * (bounds.x_max - bounds.x_min)
      return { value, label: formatAxisValue(value) }
    })
    
    const yTicks = Array.from({ length: numTicks }, (_, i) => {
      const value = bounds.y_min + (i / (numTicks - 1)) * (bounds.y_max - bounds.y_min)
      return { value, label: formatAxisValue(value) }
    })
    
    return { xTicks, yTicks }
  }, [scales])

  // Render canvas for individual points (zoom level 3)
  useEffect(() => {
    if (zoomLevel !== 3 || !data?.individual_points || !canvasRef.current || !scales) return
    
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    
    // Set canvas size
    canvas.width = dimensions.width
    canvas.height = dimensions.height
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    
    // Draw points
    ctx.fillStyle = 'rgba(37, 99, 235, 0.6)' // Blue with transparency
    data.individual_points.forEach(point => {
      const x = scales.xScale(point.x)
      const y = scales.yScale(point.y)
      
      ctx.beginPath()
      ctx.arc(x, y, 2, 0, Math.PI * 2)
      ctx.fill()
    })
  }, [zoomLevel, data?.individual_points, scales, dimensions])

  // Render helper for cluster tooltip content
  const renderClusterTooltip = (cluster: ClusterData) => (
    <div className="space-y-1 text-xs">
      <div className="font-semibold">Cluster {cluster.id + 1}</div>
      <div>Events: {cluster.count.toLocaleString()} ({cluster.pct}%)</div>
      <div>Center: ({formatAxisValue(cluster.cx)}, {formatAxisValue(cluster.cy)})</div>
      {cluster.avg_diameter && (
        <div>Avg Diameter: {cluster.avg_diameter.toFixed(1)} nm</div>
      )}
      <div className="text-muted-foreground mt-1">Click to zoom in</div>
    </div>
  )

  return (
    <Card className="w-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-medium">{title}</CardTitle>
          <div className="flex items-center gap-2">
            {/* Zoom Level Indicator */}
            <Badge variant="outline" className="gap-1">
              <Layers className="h-3 w-3" />
              Level {zoomLevel}
            </Badge>
            
            {/* Event Count */}
            {data && (
              <Badge variant="secondary">
                {data.total_events.toLocaleString()} events
              </Badge>
            )}
            
            {/* Zoom Controls */}
            <div className="flex items-center gap-1 ml-2">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-8 w-8"
                      onClick={handleZoomOut}
                      disabled={zoomLevel <= 1 || loading}
                    >
                      <ZoomOut className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Zoom Out</TooltipContent>
                </Tooltip>
              </TooltipProvider>
              
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-8 w-8"
                      onClick={handleZoomIn}
                      disabled={zoomLevel >= 3 || loading}
                    >
                      <ZoomIn className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Zoom In</TooltipContent>
                </Tooltip>
              </TooltipProvider>
              
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-8 w-8"
                      onClick={handleReset}
                      disabled={loading}
                    >
                      <Maximize2 className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Reset View</TooltipContent>
                </Tooltip>
              </TooltipProvider>
              
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => fetchClusteredData(zoomLevel, viewport || undefined)}
                      disabled={loading}
                    >
                      <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Refresh</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </div>
        </div>
        
        {/* Zoom Level Description */}
        <div className="text-xs text-muted-foreground mt-1">
          {zoomLevel === 1 && "Overview: Major population clusters"}
          {zoomLevel === 2 && "Medium: Sub-clusters showing more detail"}
          {zoomLevel === 3 && "Detailed: Individual events in viewport"}
        </div>
      </CardHeader>
      
      <CardContent>
        <div 
          ref={containerRef}
          className="relative"
          style={{ height: `${height}px` }}
        >
          {/* Loading Overlay */}
          {loading && (
            <div className="absolute inset-0 bg-background/80 flex items-center justify-center z-10">
              <div className="flex items-center gap-2">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span className="text-sm">Loading cluster data...</span>
              </div>
            </div>
          )}
          
          {/* Error State */}
          {error && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center text-destructive">
                <p className="font-medium">Error loading data</p>
                <p className="text-sm">{error}</p>
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="mt-2"
                  onClick={() => fetchClusteredData(zoomLevel)}
                >
                  Retry
                </Button>
              </div>
            </div>
          )}
          
          {/* Canvas for individual points (zoom level 3) */}
          {zoomLevel === 3 && (
            <canvas
              ref={canvasRef}
              className="absolute inset-0"
              style={{ pointerEvents: 'none' }}
            />
          )}
          
          {/* SVG for clusters and axes */}
          {scales && data && !error && (
            <svg
              ref={svgRef}
              width={dimensions.width}
              height={dimensions.height}
              className="overflow-visible"
            >
              {/* Grid lines */}
              <g className="grid-lines">
                {axisTicks.xTicks.map(tick => (
                  <line
                    key={`x-grid-${tick.value}`}
                    x1={scales.xScale(tick.value)}
                    y1={PADDING.top}
                    x2={scales.xScale(tick.value)}
                    y2={PADDING.top + chartHeight}
                    stroke="currentColor"
                    strokeOpacity={0.1}
                    strokeWidth={1}
                  />
                ))}
                {axisTicks.yTicks.map(tick => (
                  <line
                    key={`y-grid-${tick.value}`}
                    x1={PADDING.left}
                    y1={scales.yScale(tick.value)}
                    x2={PADDING.left + chartWidth}
                    y2={scales.yScale(tick.value)}
                    stroke="currentColor"
                    strokeOpacity={0.1}
                    strokeWidth={1}
                  />
                ))}
              </g>
              
              {/* X Axis */}
              <g className="x-axis">
                <line
                  x1={PADDING.left}
                  y1={PADDING.top + chartHeight}
                  x2={PADDING.left + chartWidth}
                  y2={PADDING.top + chartHeight}
                  stroke="currentColor"
                  strokeWidth={1}
                />
                {axisTicks.xTicks.map(tick => (
                  <g key={`x-tick-${tick.value}`}>
                    <line
                      x1={scales.xScale(tick.value)}
                      y1={PADDING.top + chartHeight}
                      x2={scales.xScale(tick.value)}
                      y2={PADDING.top + chartHeight + 5}
                      stroke="currentColor"
                      strokeWidth={1}
                    />
                    <text
                      x={scales.xScale(tick.value)}
                      y={PADDING.top + chartHeight + 18}
                      textAnchor="middle"
                      className="fill-muted-foreground text-[10px]"
                    >
                      {tick.label}
                    </text>
                  </g>
                ))}
                {/* X Axis Label */}
                <text
                  x={PADDING.left + chartWidth / 2}
                  y={dimensions.height - 8}
                  textAnchor="middle"
                  className="fill-foreground text-xs font-medium"
                >
                  {xLabel}
                </text>
              </g>
              
              {/* Y Axis */}
              <g className="y-axis">
                <line
                  x1={PADDING.left}
                  y1={PADDING.top}
                  x2={PADDING.left}
                  y2={PADDING.top + chartHeight}
                  stroke="currentColor"
                  strokeWidth={1}
                />
                {axisTicks.yTicks.map(tick => (
                  <g key={`y-tick-${tick.value}`}>
                    <line
                      x1={PADDING.left - 5}
                      y1={scales.yScale(tick.value)}
                      x2={PADDING.left}
                      y2={scales.yScale(tick.value)}
                      stroke="currentColor"
                      strokeWidth={1}
                    />
                    <text
                      x={PADDING.left - 8}
                      y={scales.yScale(tick.value)}
                      textAnchor="end"
                      dominantBaseline="middle"
                      className="fill-muted-foreground text-[10px]"
                    >
                      {tick.label}
                    </text>
                  </g>
                ))}
                {/* Y Axis Label */}
                <text
                  x={15}
                  y={PADDING.top + chartHeight / 2}
                  textAnchor="middle"
                  transform={`rotate(-90, 15, ${PADDING.top + chartHeight / 2})`}
                  className="fill-foreground text-xs font-medium"
                >
                  {yLabel}
                </text>
              </g>
              
              {/* Clusters (zoom levels 1-2) */}
              {data.clusters && zoomLevel < 3 && (
                <g className="clusters">
                  {data.clusters.map((cluster, idx) => (
                    <g key={cluster.id}>
                      {/* Cluster circle */}
                      <circle
                        cx={scales.xScale(cluster.cx)}
                        cy={scales.yScale(cluster.cy)}
                        r={cluster.radius}
                        fill={CLUSTER_COLORS[idx % CLUSTER_COLORS.length]}
                        fillOpacity={0.6}
                        stroke={CLUSTER_COLORS[idx % CLUSTER_COLORS.length]}
                        strokeWidth={2}
                        strokeOpacity={hoveredCluster?.id === cluster.id ? 1 : 0.8}
                        className="cursor-pointer transition-all duration-200"
                        style={{
                          transform: hoveredCluster?.id === cluster.id ? 'scale(1.1)' : 'scale(1)',
                          transformOrigin: `${scales.xScale(cluster.cx)}px ${scales.yScale(cluster.cy)}px`
                        }}
                        onMouseEnter={() => setHoveredCluster(cluster)}
                        onMouseLeave={() => setHoveredCluster(null)}
                        onClick={() => handleClusterClick(cluster)}
                      />
                      
                      {/* Cluster label (count) - show for larger clusters */}
                      {cluster.radius > 15 && (
                        <text
                          x={scales.xScale(cluster.cx)}
                          y={scales.yScale(cluster.cy)}
                          textAnchor="middle"
                          dominantBaseline="middle"
                          className="fill-white text-[9px] font-medium pointer-events-none"
                          style={{ textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}
                        >
                          {formatCount(cluster.count)}
                        </text>
                      )}
                    </g>
                  ))}
                </g>
              )}
            </svg>
          )}
          
          {/* Hover tooltip */}
          {hoveredCluster && scales && (
            <div
              className="absolute z-20 bg-popover border rounded-md shadow-lg p-2 pointer-events-none"
              style={{
                left: scales.xScale(hoveredCluster.cx) + 20,
                top: scales.yScale(hoveredCluster.cy) - 50,
              }}
            >
              {renderClusterTooltip(hoveredCluster)}
            </div>
          )}
        </div>
        
        {/* Legend */}
        {data?.clusters && zoomLevel < 3 && (
          <div className="mt-4 p-3 bg-muted/30 rounded-lg">
            <div className="text-xs font-medium mb-2">Cluster Summary</div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
              {data.clusters.slice(0, 10).map((cluster, idx) => (
                <div
                  key={cluster.id}
                  className="flex items-center gap-2 text-xs cursor-pointer hover:bg-muted/50 rounded p-1"
                  onClick={() => handleClusterClick(cluster)}
                  onMouseEnter={() => setHoveredCluster(cluster)}
                  onMouseLeave={() => setHoveredCluster(null)}
                >
                  <div
                    className="w-3 h-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: CLUSTER_COLORS[idx % CLUSTER_COLORS.length] }}
                  />
                  <span className="truncate">
                    {formatCount(cluster.count)} ({cluster.pct}%)
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Helper functions
function formatAxisValue(value: number): string {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`
  } else if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`
  }
  return value.toFixed(0)
}

function formatCount(count: number): string {
  if (count >= 1000000) {
    return `${(count / 1000000).toFixed(1)}M`
  } else if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K`
  }
  return count.toString()
}

export default ClusteredScatterChart
