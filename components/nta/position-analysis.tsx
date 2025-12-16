"use client"

import { useMemo, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Slider } from "@/components/ui/slider"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Legend,
  ReferenceArea
} from "recharts"
import { 
  MapPin, 
  Grid3X3, 
  TrendingUp, 
  Layers,
  RotateCcw,
  Download,
  AlertTriangle
} from "lucide-react"
import { cn } from "@/lib/utils"

interface PositionData {
  x: number
  y: number
  size: number
  frame?: number
  intensity?: number
}

interface PositionAnalysisProps {
  data?: PositionData[]
  frameWidth?: number
  frameHeight?: number
  className?: string
}

// Generate mock data for demonstration
function generateMockPositionData(count: number, width: number, height: number): PositionData[] {
  const data: PositionData[] = []
  for (let i = 0; i < count; i++) {
    // Create some clustering patterns
    const cluster = Math.random()
    let x, y
    if (cluster < 0.3) {
      // Cluster 1: center
      x = width/2 + (Math.random() - 0.5) * width * 0.3
      y = height/2 + (Math.random() - 0.5) * height * 0.3
    } else if (cluster < 0.5) {
      // Cluster 2: top right
      x = width * 0.75 + (Math.random() - 0.5) * width * 0.2
      y = height * 0.25 + (Math.random() - 0.5) * height * 0.2
    } else {
      // Random
      x = Math.random() * width
      y = Math.random() * height
    }
    
    data.push({
      x,
      y,
      size: 30 + Math.random() * 170,
      frame: Math.floor(Math.random() * 100),
      intensity: Math.random() * 100,
    })
  }
  return data
}

// Calculate spatial statistics
function calculateSpatialStatistics(data: PositionData[], width: number, height: number) {
  if (data.length === 0) return null
  
  // Divide into quadrants
  const quadrants = [
    { name: "Top-Left", count: 0 },
    { name: "Top-Right", count: 0 },
    { name: "Bottom-Left", count: 0 },
    { name: "Bottom-Right", count: 0 },
  ]
  
  const centerX = width / 2
  const centerY = height / 2
  
  data.forEach(p => {
    if (p.x < centerX && p.y < centerY) quadrants[0].count++
    else if (p.x >= centerX && p.y < centerY) quadrants[1].count++
    else if (p.x < centerX && p.y >= centerY) quadrants[2].count++
    else quadrants[3].count++
  })

  // Calculate mean position
  const meanX = data.reduce((sum, p) => sum + p.x, 0) / data.length
  const meanY = data.reduce((sum, p) => sum + p.y, 0) / data.length

  // Calculate standard deviation
  const stdX = Math.sqrt(data.reduce((sum, p) => sum + Math.pow(p.x - meanX, 2), 0) / data.length)
  const stdY = Math.sqrt(data.reduce((sum, p) => sum + Math.pow(p.y - meanY, 2), 0) / data.length)

  // Calculate nearest neighbor distances for clustering analysis
  let totalNNDist = 0
  data.forEach((p1, i) => {
    let minDist = Infinity
    data.forEach((p2, j) => {
      if (i !== j) {
        const dist = Math.sqrt(Math.pow(p1.x - p2.x, 2) + Math.pow(p1.y - p2.y, 2))
        if (dist < minDist) minDist = dist
      }
    })
    if (minDist < Infinity) totalNNDist += minDist
  })
  const meanNNDist = totalNNDist / data.length

  // Expected random NN distance for CSR (Complete Spatial Randomness)
  const density = data.length / (width * height)
  const expectedNNDist = 0.5 / Math.sqrt(density)
  
  // Hopkins statistic proxy (ratio of observed to expected NN distance)
  const clusteringIndex = meanNNDist / expectedNNDist

  return {
    quadrants,
    meanPosition: { x: meanX, y: meanY },
    spreadX: stdX,
    spreadY: stdY,
    meanNNDist,
    expectedNNDist,
    clusteringIndex,
    isClusteredorRandomOrDispersed: 
      clusteringIndex < 0.8 ? "Clustered" : 
      clusteringIndex > 1.2 ? "Dispersed" : "Random"
  }
}

// Density Heatmap Component
function DensityHeatmap({ 
  data, 
  width, 
  height, 
  gridSize = 8 
}: { 
  data: PositionData[]
  width: number
  height: number
  gridSize?: number
}) {
  const heatmapData = useMemo(() => {
    const cellWidth = width / gridSize
    const cellHeight = height / gridSize
    const grid: number[][] = Array(gridSize).fill(0).map(() => Array(gridSize).fill(0))
    
    // Count particles in each cell
    data.forEach(p => {
      const col = Math.min(Math.floor(p.x / cellWidth), gridSize - 1)
      const row = Math.min(Math.floor(p.y / cellHeight), gridSize - 1)
      if (row >= 0 && row < gridSize && col >= 0 && col < gridSize) {
        grid[row][col]++
      }
    })
    
    // Find max for normalization
    const maxCount = Math.max(...grid.flat())
    
    // Create cell data
    const cells: Array<{ row: number; col: number; count: number; normalized: number }> = []
    for (let r = 0; r < gridSize; r++) {
      for (let c = 0; c < gridSize; c++) {
        cells.push({
          row: r,
          col: c,
          count: grid[r][c],
          normalized: maxCount > 0 ? grid[r][c] / maxCount : 0,
        })
      }
    }
    
    return { cells, maxCount, cellWidth, cellHeight }
  }, [data, width, height, gridSize])

  // Color scale function
  const getHeatColor = (normalized: number) => {
    if (normalized === 0) return "hsl(var(--muted)/0.3)"
    if (normalized < 0.25) return "hsl(142, 76%, 50%)" // Green
    if (normalized < 0.5) return "hsl(60, 90%, 50%)" // Yellow
    if (normalized < 0.75) return "hsl(30, 90%, 50%)" // Orange
    return "hsl(0, 80%, 50%)" // Red
  }

  return (
    <div className="space-y-3">
      <div 
        className="w-full aspect-4/3 rounded-lg overflow-hidden border bg-secondary/20"
        style={{ 
          display: 'grid', 
          gridTemplateColumns: `repeat(${gridSize}, 1fr)`,
          gridTemplateRows: `repeat(${gridSize}, 1fr)`,
          gap: '1px',
        }}
      >
        {heatmapData.cells.map((cell, idx) => (
          <div
            key={idx}
            className="relative group cursor-pointer transition-opacity hover:opacity-80"
            style={{
              backgroundColor: getHeatColor(cell.normalized),
              opacity: 0.3 + cell.normalized * 0.7,
            }}
            title={`Count: ${cell.count}`}
          >
            {cell.count > 0 && cell.normalized > 0.3 && (
              <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-white/90">
                {cell.count}
              </span>
            )}
          </div>
        ))}
      </div>
      
      {/* Legend */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: "hsl(142, 76%, 50%)" }} />
          <span>Low</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: "hsl(60, 90%, 50%)" }} />
          <span>Medium</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: "hsl(30, 90%, 50%)" }} />
          <span>High</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: "hsl(0, 80%, 50%)" }} />
          <span>Max ({heatmapData.maxCount})</span>
        </div>
      </div>
      
      <p className="text-xs text-muted-foreground text-center">
        {gridSize}×{gridSize} grid density visualization • {data.length} particles
      </p>
    </div>
  )
}

export function PositionAnalysis({ 
  data, 
  frameWidth = 1024, 
  frameHeight = 768,
  className 
}: PositionAnalysisProps) {
  const [sizeRange, setSizeRange] = useState<[number, number]>([0, 300])
  const [colorBySize, setColorBySize] = useState(true)
  const [showGrid, setShowGrid] = useState(true)
  const [showStats, setShowStats] = useState(true)

  // Use provided data or generate mock data
  const positionData = useMemo(() => {
    if (data && data.length > 0) return data
    return generateMockPositionData(150, frameWidth, frameHeight)
  }, [data, frameWidth, frameHeight])

  // Filter by size range
  const filteredData = useMemo(() => {
    return positionData.filter(p => p.size >= sizeRange[0] && p.size <= sizeRange[1])
  }, [positionData, sizeRange])

  // Calculate statistics
  const stats = useMemo(() => {
    return calculateSpatialStatistics(filteredData, frameWidth, frameHeight)
  }, [filteredData, frameWidth, frameHeight])

  // Color scale based on size
  const getColor = (size: number) => {
    if (!colorBySize) return "hsl(var(--primary))"
    const normalized = (size - 30) / 170
    // Green -> Blue -> Purple gradient
    if (normalized < 0.33) return `hsl(142, 76%, ${50 + normalized * 20}%)`
    if (normalized < 0.66) return `hsl(221, 83%, ${50 + (normalized - 0.33) * 20}%)`
    return `hsl(270, 76%, ${50 + (normalized - 0.66) * 20}%)`
  }

  const handleExport = () => {
    // Create CSV
    const headers = ["x", "y", "size", "frame", "intensity"]
    const rows = filteredData.map(p => 
      [p.x.toFixed(2), p.y.toFixed(2), p.size.toFixed(1), p.frame || "", p.intensity?.toFixed(1) || ""]
    )
    const csv = [headers.join(","), ...rows.map(r => r.join(","))].join("\n")
    
    const blob = new Blob([csv], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "nta_position_data.csv"
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Card className={cn("card-3d", className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-primary/10">
              <MapPin className="h-4 w-4 text-primary" />
            </div>
            <div>
              <CardTitle className="text-base md:text-lg">Position Analysis</CardTitle>
              <CardDescription className="text-xs">
                Spatial distribution of detected particles
              </CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">
              {filteredData.length} particles
            </Badge>
            <Button variant="outline" size="sm" onClick={handleExport} className="gap-1">
              <Download className="h-3.5 w-3.5" />
              Export
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Controls */}
        <div className="flex flex-wrap items-center gap-4 p-3 rounded-lg bg-secondary/30">
          <div className="flex-1 min-w-[200px] space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm">Size Filter (nm)</Label>
              <span className="text-xs text-muted-foreground">
                {sizeRange[0]} - {sizeRange[1]} nm
              </span>
            </div>
            <Slider
              value={sizeRange}
              min={0}
              max={300}
              step={10}
              onValueChange={(v) => setSizeRange(v as [number, number])}
            />
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Switch
                id="colorBySize"
                checked={colorBySize}
                onCheckedChange={setColorBySize}
              />
              <Label htmlFor="colorBySize" className="text-sm cursor-pointer">
                Color by size
              </Label>
            </div>
            
            <div className="flex items-center gap-2">
              <Switch
                id="showGrid"
                checked={showGrid}
                onCheckedChange={setShowGrid}
              />
              <Label htmlFor="showGrid" className="text-sm cursor-pointer">
                Grid
              </Label>
            </div>
          </div>
        </div>

        <Tabs defaultValue="scatter" className="space-y-4">
          <TabsList className="bg-secondary/50">
            <TabsTrigger value="scatter" className="gap-1">
              <MapPin className="h-3.5 w-3.5" />
              Scatter
            </TabsTrigger>
            <TabsTrigger value="heatmap" className="gap-1">
              <Grid3X3 className="h-3.5 w-3.5" />
              Density
            </TabsTrigger>
            <TabsTrigger value="stats" className="gap-1">
              <TrendingUp className="h-3.5 w-3.5" />
              Statistics
            </TabsTrigger>
          </TabsList>

          <TabsContent value="scatter" className="mt-4">
            <div className="h-[400px] w-full">
              <ResponsiveContainer>
                <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                  {showGrid && <CartesianGrid strokeDasharray="3 3" opacity={0.3} />}
                  <XAxis 
                    type="number" 
                    dataKey="x" 
                    domain={[0, frameWidth]}
                    name="X Position"
                    unit="px"
                    tick={{ fontSize: 10 }}
                  />
                  <YAxis 
                    type="number" 
                    dataKey="y" 
                    domain={[0, frameHeight]}
                    name="Y Position"
                    unit="px"
                    tick={{ fontSize: 10 }}
                  />
                  <ZAxis 
                    type="number" 
                    dataKey="size" 
                    range={[20, 100]} 
                    name="Size" 
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload as PositionData
                        return (
                          <div className="bg-popover border rounded-lg p-2 shadow-lg text-sm">
                            <div>X: {data.x.toFixed(1)} px</div>
                            <div>Y: {data.y.toFixed(1)} px</div>
                            <div>Size: {data.size.toFixed(1)} nm</div>
                            {data.frame !== undefined && <div>Frame: {data.frame}</div>}
                          </div>
                        )
                      }
                      return null
                    }}
                  />
                  <Scatter data={filteredData} fill="hsl(var(--primary))">
                    {filteredData.map((entry, index) => (
                      <Cell key={index} fill={getColor(entry.size)} fillOpacity={0.7} />
                    ))}
                  </Scatter>
                  {/* Reference areas for quadrants */}
                  {showGrid && (
                    <>
                      <ReferenceArea 
                        x1={0} x2={frameWidth/2} 
                        y1={0} y2={frameHeight/2}
                        fill="hsl(var(--muted))"
                        fillOpacity={0.1}
                      />
                      <ReferenceArea 
                        x1={frameWidth/2} x2={frameWidth} 
                        y1={frameHeight/2} y2={frameHeight}
                        fill="hsl(var(--muted))"
                        fillOpacity={0.1}
                      />
                    </>
                  )}
                </ScatterChart>
              </ResponsiveContainer>
            </div>

            {/* Size legend */}
            {colorBySize && (
              <div className="flex items-center justify-center gap-4 mt-2">
                <div className="flex items-center gap-1.5 text-xs">
                  <div className="w-3 h-3 rounded-full" style={{ background: "hsl(142, 76%, 50%)" }} />
                  <span>Small (&lt;80nm)</span>
                </div>
                <div className="flex items-center gap-1.5 text-xs">
                  <div className="w-3 h-3 rounded-full" style={{ background: "hsl(221, 83%, 55%)" }} />
                  <span>Medium (80-150nm)</span>
                </div>
                <div className="flex items-center gap-1.5 text-xs">
                  <div className="w-3 h-3 rounded-full" style={{ background: "hsl(270, 76%, 55%)" }} />
                  <span>Large (&gt;150nm)</span>
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="heatmap" className="mt-4">
            <DensityHeatmap 
              data={filteredData}
              width={frameWidth}
              height={frameHeight}
              gridSize={8}
            />
          </TabsContent>

          <TabsContent value="stats" className="mt-4">
            {stats && (
              <div className="space-y-4">
                {/* Quadrant Distribution */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {stats.quadrants.map((q, i) => (
                    <div 
                      key={i} 
                      className="p-3 rounded-lg bg-secondary/30 text-center"
                    >
                      <div className="text-lg font-bold">{q.count}</div>
                      <div className="text-xs text-muted-foreground">{q.name}</div>
                      <div className="text-xs text-muted-foreground">
                        ({((q.count / filteredData.length) * 100).toFixed(1)}%)
                      </div>
                    </div>
                  ))}
                </div>

                {/* Spatial Statistics */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  <div className="p-3 rounded-lg bg-secondary/30 text-center">
                    <div className="text-lg font-bold">
                      ({stats.meanPosition.x.toFixed(0)}, {stats.meanPosition.y.toFixed(0)})
                    </div>
                    <div className="text-xs text-muted-foreground">Mean Position (px)</div>
                  </div>
                  
                  <div className="p-3 rounded-lg bg-secondary/30 text-center">
                    <div className="text-lg font-bold">
                      {stats.spreadX.toFixed(1)} × {stats.spreadY.toFixed(1)}
                    </div>
                    <div className="text-xs text-muted-foreground">Spread (σ px)</div>
                  </div>

                  <div className="p-3 rounded-lg bg-secondary/30 text-center">
                    <div className="text-lg font-bold">{stats.meanNNDist.toFixed(1)} px</div>
                    <div className="text-xs text-muted-foreground">Mean NN Distance</div>
                  </div>
                </div>

                {/* Clustering Analysis */}
                <div className="p-4 rounded-lg border">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">Spatial Distribution Pattern</div>
                      <div className="text-sm text-muted-foreground">
                        Clustering Index: {stats.clusteringIndex.toFixed(3)}
                      </div>
                    </div>
                    <Badge 
                      variant="outline"
                      className={cn(
                        stats.isClusteredorRandomOrDispersed === "Clustered" && "bg-amber-500/10 text-amber-600 border-amber-500/30",
                        stats.isClusteredorRandomOrDispersed === "Random" && "bg-emerald-500/10 text-emerald-600 border-emerald-500/30",
                        stats.isClusteredorRandomOrDispersed === "Dispersed" && "bg-blue-500/10 text-blue-600 border-blue-500/30"
                      )}
                    >
                      {stats.isClusteredorRandomOrDispersed}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    Index &lt; 0.8 indicates clustering, 0.8-1.2 is random, &gt;1.2 is dispersed pattern
                  </p>
                </div>

                {/* Warning if clustered */}
                {stats.isClusteredorRandomOrDispersed === "Clustered" && (
                  <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-sm">
                    <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5" />
                    <div>
                      <div className="font-medium text-amber-600">Potential Aggregation Detected</div>
                      <p className="text-muted-foreground text-xs mt-1">
                        Particles appear clustered. This could indicate aggregation or non-uniform sample distribution.
                        Consider verifying sample preparation or adjusting dilution.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
