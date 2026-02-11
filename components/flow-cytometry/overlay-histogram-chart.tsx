"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ComposedChart } from "recharts"
import { useAnalysisStore } from "@/lib/store"
import { apiClient } from "@/lib/api-client"
import { Layers, Eye, EyeOff } from "lucide-react"
import { useState, useMemo, useEffect } from "react"

interface OverlayHistogramChartProps {
  title?: string
  parameter?: string
}

export function OverlayHistogramChart({ 
  title = "Size Distribution Overlay",
  parameter = "FSC-A"
}: OverlayHistogramChartProps) {
  const { fcsAnalysis, secondaryFcsAnalysis, overlayConfig } = useAnalysisStore()
  const [showPrimary, setShowPrimary] = useState(true)
  const [showSecondary, setShowSecondary] = useState(true)

  // Fetch primary scatter data on-demand (not stored in global state)
  const [primaryScatter, setPrimaryScatter] = useState<Array<{ x: number; y: number; diameter?: number }>>([])
  const primarySampleId = fcsAnalysis.sampleId

  useEffect(() => {
    if (!primarySampleId) return
    let cancelled = false
    const fetchPrimaryScatter = async () => {
      try {
        const result = await apiClient.getScatterData(primarySampleId, 10000)
        if (!cancelled && result?.data) {
          setPrimaryScatter(result.data)
        }
      } catch {
        // Scatter data is optional — Gaussian fallback still works
      }
    }
    fetchPrimaryScatter()
    return () => { cancelled = true }
  }, [primarySampleId])

  const primaryResults = fcsAnalysis.results
  const secondaryResults = secondaryFcsAnalysis.results

  // PERFORMANCE FIX: Memoize histogram data generation
  const histogramData = useMemo(() => {
    if (!primaryResults && !secondaryResults) return { data: [], isApproximate: true }

    // Try to use actual scatter data
    const secondaryScatter = secondaryFcsAnalysis.scatterData ?? []

    // Determine the value extractor based on parameter
    const extractValue = (point: { x: number; y: number; diameter?: number }) => {
      if (parameter === "FSC-A") return point.x
      if (parameter === "SSC-A") return point.y
      if (parameter === "size" && point.diameter) return point.diameter
      return point.x
    }

    // Collect real values where available
    const primaryValues = primaryScatter.length > 0
      ? primaryScatter.map(extractValue).filter(v => v != null && isFinite(v))
      : []
    const secondaryValues = secondaryScatter.length > 0
      ? secondaryScatter.map(extractValue).filter(v => v != null && isFinite(v))
      : []

    const hasRealPrimary = primaryValues.length > 0
    const hasRealSecondary = secondaryValues.length > 0
    const hasRealData = hasRealPrimary || hasRealSecondary

    // Calculate summary stats as fallback
    const primaryMean = parameter === "FSC-A"
      ? (primaryResults?.fsc_mean || primaryResults?.size_statistics?.mean || 100)
      : parameter === "SSC-A"
        ? (primaryResults?.ssc_mean || 50)
        : (primaryResults?.size_statistics?.mean || primaryResults?.particle_size_median_nm || 100)
    const primaryStd = primaryResults?.size_statistics?.std || primaryMean * 0.3

    const secondaryMean = parameter === "FSC-A"
      ? (secondaryResults?.fsc_mean || secondaryResults?.size_statistics?.mean || 100)
      : parameter === "SSC-A"
        ? (secondaryResults?.ssc_mean || 50)
        : (secondaryResults?.size_statistics?.mean || secondaryResults?.particle_size_median_nm || 100)
    const secondaryStd = secondaryResults?.size_statistics?.std || secondaryMean * 0.3

    // Determine bin range from all available data
    const allValues = [...primaryValues, ...secondaryValues]
    let minVal: number, maxVal: number
    if (allValues.length > 0) {
      const sorted = [...allValues].sort((a, b) => a - b)
      const q01 = sorted[Math.floor(sorted.length * 0.01)] ?? sorted[0]
      const q99 = sorted[Math.floor(sorted.length * 0.99)] ?? sorted[sorted.length - 1]
      minVal = q01
      maxVal = q99
      // Expand range to include Gaussian tails if needed
      if (!hasRealPrimary && primaryResults) {
        minVal = Math.min(minVal, primaryMean - 3 * primaryStd)
        maxVal = Math.max(maxVal, primaryMean + 3 * primaryStd)
      }
      if (!hasRealSecondary && secondaryResults) {
        minVal = Math.min(minVal, secondaryMean - 3 * secondaryStd)
        maxVal = Math.max(maxVal, secondaryMean + 3 * secondaryStd)
      }
    } else {
      minVal = Math.min(
        primaryResults ? primaryMean - 3 * primaryStd : Infinity,
        secondaryResults ? secondaryMean - 3 * secondaryStd : Infinity
      )
      maxVal = Math.max(
        primaryResults ? primaryMean + 3 * primaryStd : -Infinity,
        secondaryResults ? secondaryMean + 3 * secondaryStd : -Infinity
      )
    }

    const bins = 50
    const binSize = (maxVal - minVal) / bins
    const data: Array<{ bin: string; binValue: number; primary: number; secondary: number }> = []

    for (let i = 0; i < bins; i++) {
      const binStart = minVal + i * binSize
      const binEnd = binStart + binSize
      const binMid = binStart + binSize / 2

      // Primary: Use real scatter data if available, else Gaussian fallback
      let primaryValue: number
      if (hasRealPrimary) {
        primaryValue = primaryValues.filter(v => v >= binStart && v < binEnd).length
      } else {
        primaryValue = primaryResults
          ? Math.exp(-0.5 * Math.pow((binMid - primaryMean) / primaryStd, 2)) * 100
          : 0
      }

      // Secondary: Use real scatter data if available, else Gaussian fallback
      let secondaryValue: number
      if (hasRealSecondary) {
        secondaryValue = secondaryValues.filter(v => v >= binStart && v < binEnd).length
      } else {
        secondaryValue = secondaryResults
          ? Math.exp(-0.5 * Math.pow((binMid - secondaryMean) / secondaryStd, 2)) * 100
          : 0
      }

      data.push({
        bin: binMid.toFixed(0),
        binValue: binMid,
        primary: Math.round(primaryValue),
        secondary: Math.round(secondaryValue)
      })
    }

    // Scale Gaussian side to match event-data side for visual comparison
    if (hasRealPrimary !== hasRealSecondary) {
      const realSide = hasRealPrimary ? "primary" : "secondary"
      const gaussSide = hasRealPrimary ? "secondary" : "primary"
      const maxReal = Math.max(...data.map(d => d[realSide as keyof typeof d] as number), 1)
      const maxGauss = Math.max(...data.map(d => d[gaussSide as keyof typeof d] as number), 1)
      const scale = maxReal / maxGauss
      data.forEach(d => { (d as Record<string, number>)[gaussSide] = Math.round((d[gaussSide as keyof typeof d] as number) * scale) })
    }

    return { data, isApproximate: !hasRealData }
  }, [primaryResults, secondaryResults, primaryScatter, secondaryFcsAnalysis.scatterData, parameter])

  if (!primaryResults) {
    return (
      <Card className="card-3d">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Layers className="h-4 w-4" />
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-[300px] text-muted-foreground">
          Upload a file to view histogram
        </CardContent>
      </Card>
    )
  }

  const hasOverlay = overlayConfig.enabled && secondaryResults
  const { data: chartData, isApproximate } = histogramData

  return (
    <Card className="card-3d">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Layers className="h-4 w-4" />
            {title}
          </CardTitle>
          <div className="flex items-center gap-2">
            {hasOverlay && (
              <>
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
              </>
            )}
            {hasOverlay && (
              <Badge variant="secondary">
                <Layers className="h-3 w-3 mr-1" />
                Overlay
              </Badge>
            )}
            {isApproximate && (
              <Badge variant="outline" className="text-xs text-amber-500 border-amber-500/50">
                Approximated
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis 
                dataKey="bin" 
                tick={{ fontSize: 10 }}
                label={{ value: parameter, position: 'bottom', fontSize: 12 }}
              />
              <YAxis 
                tick={{ fontSize: 10 }}
                label={{ value: 'Count', angle: -90, position: 'insideLeft', fontSize: 12 }}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(0,0,0,0.8)', 
                  border: 'none',
                  borderRadius: '8px',
                  color: 'white'
                }}
                formatter={(value: number, name: string) => [
                  value,
                  name === 'primary' 
                    ? fcsAnalysis.file?.name || 'Primary' 
                    : secondaryFcsAnalysis.file?.name || 'Comparison'
                ]}
              />
              <Legend 
                verticalAlign="top"
                height={36}
                formatter={(value) => value === 'primary' 
                  ? fcsAnalysis.file?.name?.slice(0, 20) || 'Primary' 
                  : secondaryFcsAnalysis.file?.name?.slice(0, 20) || 'Comparison'
                }
              />
              {showPrimary && (
                <Area
                  type="monotone"
                  dataKey="primary"
                  fill={overlayConfig.primaryColor}
                  fillOpacity={hasOverlay ? 0.4 : 0.6}
                  stroke={overlayConfig.primaryColor}
                  strokeWidth={2}
                />
              )}
              {hasOverlay && showSecondary && (
                <Area
                  type="monotone"
                  dataKey="secondary"
                  fill={overlayConfig.secondaryColor}
                  fillOpacity={0.4}
                  stroke={overlayConfig.secondaryColor}
                  strokeWidth={2}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* Statistics comparison */}
        {hasOverlay && (
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="p-3 rounded-lg" style={{ backgroundColor: `${overlayConfig.primaryColor}20` }}>
              <p className="text-xs font-medium mb-2 truncate" title={fcsAnalysis.file?.name}>
                {fcsAnalysis.file?.name?.slice(0, 25) || 'Primary'}
              </p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-muted-foreground">FSC Mean:</span>
                  <span className="ml-1 font-medium">{primaryResults.fsc_mean?.toFixed(2) || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">SSC Mean:</span>
                  <span className="ml-1 font-medium">{primaryResults.ssc_mean?.toFixed(2) || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Events:</span>
                  <span className="ml-1 font-medium">{primaryResults.total_events?.toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Size (D50):</span>
                  <span className="ml-1 font-medium">{primaryResults.size_statistics?.d50?.toFixed(1) || 'N/A'} nm</span>
                </div>
              </div>
            </div>
            <div className="p-3 rounded-lg" style={{ backgroundColor: `${overlayConfig.secondaryColor}20` }}>
              <p className="text-xs font-medium mb-2 truncate" title={secondaryFcsAnalysis.file?.name}>
                {secondaryFcsAnalysis.file?.name?.slice(0, 25) || 'Comparison'}
              </p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-muted-foreground">FSC Mean:</span>
                  <span className="ml-1 font-medium">{secondaryResults?.fsc_mean?.toFixed(2) || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">SSC Mean:</span>
                  <span className="ml-1 font-medium">{secondaryResults?.ssc_mean?.toFixed(2) || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Events:</span>
                  <span className="ml-1 font-medium">{secondaryResults?.total_events?.toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Size (D50):</span>
                  <span className="ml-1 font-medium">{secondaryResults?.size_statistics?.d50?.toFixed(1) || 'N/A'} nm</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
