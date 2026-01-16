"use client"

/**
 * Enhanced Histogram Chart with Anomaly Highlighting
 * CRMIT-008: Histogram anomaly visualization
 * 
 * Features:
 * - Anomalous bin highlighting
 * - Statistical threshold lines
 * - Interactive bin selection
 * - Anomaly count badges per bin
 * - Configurable highlight colors and styles
 */

import { useMemo, useState } from "react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
  Legend,
  ReferenceArea,
} from "recharts"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Tooltip as UITooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { InteractiveChartWrapper } from "@/components/charts/interactive-chart-wrapper"
import { AlertTriangle, Eye, EyeOff, Info } from "lucide-react"
import { cn } from "@/lib/utils"
import { CHART_COLORS } from "@/lib/store"

// Types
interface HistogramBin {
  binCenter: number
  binStart: number
  binEnd: number
  count: number
  normalCount: number
  anomalyCount: number
  isAnomalous?: boolean  // True if this bin contains anomalous events
  anomalyPercentage?: number
}

interface AnomalyHistogramChartProps {
  // Data props
  data?: number[]
  anomalousIndices?: number[]
  // Configuration
  binCount?: number
  title?: string
  xLabel?: string
  yLabel?: string
  height?: number
  // Anomaly display options
  showAnomalyHighlight?: boolean
  highlightThreshold?: number  // Percentage of anomalies in bin to highlight
  anomalyColor?: string
  normalColor?: string
  // Statistical markers
  showMean?: boolean
  showStdDev?: boolean
  mean?: number
  std?: number
  // Interactive options
  showControls?: boolean
  onBinClick?: (bin: HistogramBin) => void
}

// Custom tooltip for histogram
function HistogramTooltip({ active, payload, label }: any) {
  if (!active || !payload || !payload.length) return null

  const data = payload[0]?.payload as HistogramBin
  if (!data) return null

  const hasAnomalies = data.anomalyCount > 0

  return (
    <div className="bg-background/95 backdrop-blur-sm border border-border rounded-lg p-3 shadow-lg min-w-[180px]">
      <p className="font-semibold text-sm mb-2 border-b pb-1">
        {data.binStart.toFixed(1)} - {data.binEnd.toFixed(1)} nm
      </p>
      <div className="space-y-1.5 text-xs">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Total Count:</span>
          <span className="font-medium">{data.count.toLocaleString()}</span>
        </div>
        <div className="flex justify-between">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-muted-foreground">Normal:</span>
          </span>
          <span className="font-medium">{data.normalCount.toLocaleString()}</span>
        </div>
        {hasAnomalies && (
          <>
            <div className="flex justify-between">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-500" />
                <span className="text-muted-foreground">Anomalous:</span>
              </span>
              <span className="font-medium text-red-400">{data.anomalyCount.toLocaleString()}</span>
            </div>
            <div className="flex justify-between border-t pt-1 mt-1">
              <span className="text-muted-foreground">Anomaly %:</span>
              <Badge variant="destructive" className="h-5 px-1.5">
                {data.anomalyPercentage?.toFixed(1)}%
              </Badge>
            </div>
          </>
        )}
        {data.isAnomalous && (
          <div className="flex items-center gap-1 mt-2 text-yellow-500">
            <AlertTriangle className="h-3 w-3" />
            <span className="text-xs">High anomaly concentration</span>
          </div>
        )}
      </div>
    </div>
  )
}

export function AnomalyHistogramChart({
  data = [],
  anomalousIndices = [],
  binCount = 30,
  title = "Size Distribution with Anomalies",
  xLabel = "Size (nm)",
  yLabel = "Count",
  height = 320,
  showAnomalyHighlight = true,
  highlightThreshold = 5,  // Highlight bins with >5% anomalies
  anomalyColor = CHART_COLORS.anomaly,
  normalColor = CHART_COLORS.primary,
  showMean = true,
  showStdDev = true,
  mean,
  std,
  showControls = true,
  onBinClick,
}: AnomalyHistogramChartProps) {
  const [showHighlight, setShowHighlight] = useState(showAnomalyHighlight)
  const [selectedBin, setSelectedBin] = useState<number | null>(null)

  // Create anomaly set for O(1) lookup
  const anomalySet = useMemo(() => new Set(anomalousIndices), [anomalousIndices])

  // Calculate histogram bins with anomaly information
  const histogramData = useMemo(() => {
    if (!data.length) {
      // Generate sample data for demo
      const sampleData: HistogramBin[] = []
      for (let i = 0; i < binCount; i++) {
        const binStart = i * (500 / binCount)
        const binEnd = (i + 1) * (500 / binCount)
        const binCenter = (binStart + binEnd) / 2
        
        // Sample distribution
        const count = Math.round(
          1000 * Math.exp(-Math.pow((binCenter - 120) / 50, 2)) +
          400 * Math.exp(-Math.pow((binCenter - 280) / 80, 2))
        )
        
        // Sample anomalies (higher at tails)
        const anomalyRatio = binCenter < 50 || binCenter > 350 ? 0.15 : 0.02
        const anomalyCount = Math.round(count * anomalyRatio)
        
        sampleData.push({
          binCenter,
          binStart,
          binEnd,
          count,
          normalCount: count - anomalyCount,
          anomalyCount,
          isAnomalous: (anomalyCount / count) * 100 > highlightThreshold,
          anomalyPercentage: (anomalyCount / count) * 100,
        })
      }
      return sampleData
    }

    // Calculate actual histogram with real data
    const minVal = Math.min(...data)
    const maxVal = Math.max(...data)
    const range = maxVal - minVal || 1
    const binWidth = range / binCount

    const bins: HistogramBin[] = []
    
    for (let i = 0; i < binCount; i++) {
      const binStart = minVal + i * binWidth
      const binEnd = minVal + (i + 1) * binWidth
      const binCenter = (binStart + binEnd) / 2
      
      let normalCount = 0
      let anomalyCount = 0
      
      data.forEach((value, idx) => {
        if (value >= binStart && (i === binCount - 1 ? value <= binEnd : value < binEnd)) {
          if (anomalySet.has(idx)) {
            anomalyCount++
          } else {
            normalCount++
          }
        }
      })
      
      const totalCount = normalCount + anomalyCount
      const anomalyPercentage = totalCount > 0 ? (anomalyCount / totalCount) * 100 : 0
      
      bins.push({
        binCenter,
        binStart,
        binEnd,
        count: totalCount,
        normalCount,
        anomalyCount,
        isAnomalous: anomalyPercentage > highlightThreshold && anomalyCount > 0,
        anomalyPercentage,
      })
    }
    
    return bins
  }, [data, anomalySet, binCount, highlightThreshold])

  // Calculate statistics
  const stats = useMemo(() => {
    if (mean !== undefined && std !== undefined) {
      return { mean, std }
    }
    
    if (!data.length) {
      return { mean: 120, std: 50 }  // Sample values
    }
    
    const n = data.length
    const dataMean = data.reduce((a, b) => a + b, 0) / n
    const dataStd = Math.sqrt(
      data.reduce((sum, val) => sum + Math.pow(val - dataMean, 2), 0) / n
    )
    
    return { mean: dataMean, std: dataStd }
  }, [data, mean, std])

  // Total anomaly count
  const totalAnomalies = useMemo(() => {
    return histogramData.reduce((sum, bin) => sum + bin.anomalyCount, 0)
  }, [histogramData])

  const totalEvents = useMemo(() => {
    return histogramData.reduce((sum, bin) => sum + bin.count, 0)
  }, [histogramData])

  const anomalyPercentage = totalEvents > 0 
    ? ((totalAnomalies / totalEvents) * 100).toFixed(2) 
    : "0.00"

  // Bin click handler
  const handleBinClick = (binData: HistogramBin, index: number) => {
    setSelectedBin(selectedBin === index ? null : index)
    onBinClick?.(binData)
  }

  // Header content with anomaly stats
  const headerContent = (
    <div className="flex items-center gap-3 flex-wrap">
      {showControls && (
        <Button
          variant={showHighlight ? "default" : "outline"}
          size="sm"
          className="h-7 text-xs gap-1"
          onClick={() => setShowHighlight(!showHighlight)}
        >
          {showHighlight ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
          Anomalies
        </Button>
      )}
      
      {totalAnomalies > 0 && showHighlight && (
        <Badge variant="destructive" className="gap-1">
          <AlertTriangle className="h-3 w-3" />
          {totalAnomalies.toLocaleString()} ({anomalyPercentage}%)
        </Badge>
      )}
      
      <TooltipProvider>
        <UITooltip>
          <TooltipTrigger asChild>
            <Badge variant="outline" className="gap-1 cursor-help">
              <Info className="h-3 w-3" />
              {binCount} bins
            </Badge>
          </TooltipTrigger>
          <TooltipContent>
            <p className="text-xs">
              Bins with {">"}{highlightThreshold}% anomalies are highlighted
            </p>
          </TooltipContent>
        </UITooltip>
      </TooltipProvider>
    </div>
  )

  return (
    <InteractiveChartWrapper
      title={title}
      source="FCS Analysis"
      chartType="histogram"
      showControls={showControls}
      height={height}
      data={histogramData}
      xAxisKey="binCenter"
      yAxisKey="count"
    >
      {/* Header content as first child inside wrapper */}
      <div className="absolute top-0 right-0 z-10 flex items-center gap-2">
        {headerContent}
      </div>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart 
          data={histogramData} 
          barCategoryGap={0}
          onClick={(e: any) => {
            if (e?.activePayload?.[0]?.payload) {
              const index = histogramData.findIndex(
                b => b.binCenter === e.activePayload![0].payload.binCenter
              )
              handleBinClick(e.activePayload[0].payload, index)
            }
          }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="binCenter"
            stroke="#64748b"
            tick={{ fontSize: 11 }}
            tickFormatter={(value) => value.toFixed(0)}
            label={{ 
              value: xLabel, 
              position: "bottom", 
              offset: -5, 
              fill: "#64748b", 
              fontSize: 12 
            }}
          />
          <YAxis
            stroke="#64748b"
            tick={{ fontSize: 11 }}
            label={{ 
              value: yLabel, 
              angle: -90, 
              position: "insideLeft", 
              fill: "#64748b", 
              fontSize: 12 
            }}
          />
          <Tooltip content={<HistogramTooltip />} />
          <Legend 
            verticalAlign="top" 
            height={36}
            formatter={(value) => {
              if (value === "normalCount") return "Normal Events"
              if (value === "anomalyCount") return "Anomalous Events"
              return value
            }}
          />

          {/* Normal events bar */}
          <Bar 
            dataKey="normalCount" 
            stackId="a" 
            fill={normalColor}
            radius={[0, 0, 0, 0]}
          >
            {histogramData.map((entry, index) => (
              <Cell
                key={`normal-${index}`}
                fill={
                  selectedBin === index 
                    ? "#22c55e" 
                    : entry.isAnomalous && showHighlight 
                      ? "#065f46"  // Darker green for anomalous bins
                      : normalColor
                }
                opacity={selectedBin !== null && selectedBin !== index ? 0.5 : 1}
                cursor="pointer"
              />
            ))}
          </Bar>

          {/* Anomaly events bar (stacked) */}
          {showHighlight && (
            <Bar 
              dataKey="anomalyCount" 
              stackId="a" 
              fill={anomalyColor}
              radius={[2, 2, 0, 0]}
            >
              {histogramData.map((entry, index) => (
                <Cell
                  key={`anomaly-${index}`}
                  fill={
                    selectedBin === index 
                      ? "#f87171" 
                      : entry.isAnomalous 
                        ? "#dc2626"  // Brighter red for highlighted anomalous bins
                        : anomalyColor
                  }
                  opacity={selectedBin !== null && selectedBin !== index ? 0.5 : 1}
                  cursor="pointer"
                />
              ))}
            </Bar>
          )}

          {/* Mean reference line */}
          {showMean && (
            <ReferenceLine
              x={stats.mean}
              stroke="#10b981"
              strokeDasharray="5 5"
              strokeWidth={2}
              label={{
                value: `μ = ${stats.mean.toFixed(1)}`,
                fill: "#10b981",
                fontSize: 10,
                position: "top",
              }}
            />
          )}

          {/* Standard deviation reference areas */}
          {showStdDev && (
            <>
              {/* 1 sigma region */}
              <ReferenceArea
                x1={stats.mean - stats.std}
                x2={stats.mean + stats.std}
                fill="#10b981"
                fillOpacity={0.1}
                label={{
                  value: "±1σ",
                  position: "insideTopRight",
                  fill: "#10b981",
                  fontSize: 9,
                }}
              />
              {/* 2 sigma lines */}
              <ReferenceLine
                x={stats.mean - 2 * stats.std}
                stroke="#f59e0b"
                strokeDasharray="3 3"
                strokeWidth={1}
                label={{
                  value: "-2σ",
                  fill: "#f59e0b",
                  fontSize: 9,
                }}
              />
              <ReferenceLine
                x={stats.mean + 2 * stats.std}
                stroke="#f59e0b"
                strokeDasharray="3 3"
                strokeWidth={1}
                label={{
                  value: "+2σ",
                  fill: "#f59e0b",
                  fontSize: 9,
                }}
              />
            </>
          )}
        </BarChart>
      </ResponsiveContainer>
    </InteractiveChartWrapper>
  )
}

export default AnomalyHistogramChart
