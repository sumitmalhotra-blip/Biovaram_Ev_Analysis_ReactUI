"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ComposedChart } from "recharts"
import { useAnalysisStore } from "@/lib/store"
import { Layers, Eye, EyeOff } from "lucide-react"
import { useState, useMemo } from "react"

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

  const primaryResults = fcsAnalysis.results
  const secondaryResults = secondaryFcsAnalysis.results

  // PERFORMANCE FIX: Memoize histogram data generation
  const histogramData = useMemo(() => {
    if (!primaryResults && !secondaryResults) return []

    // Create bins for histogram
    const bins = 50
    const data: Array<{
      bin: string
      binValue: number
      primary: number
      secondary: number
    }> = []

    // Get the statistics from primary or secondary using correct FCSResult fields
    const primaryMean = parameter === "FSC-A" 
      ? (primaryResults?.fsc_mean || primaryResults?.size_statistics?.mean || 100)
      : (primaryResults?.ssc_mean || 50)
    const primaryStd = primaryResults?.size_statistics?.std || primaryMean * 0.3
    
    const secondaryMean = parameter === "FSC-A" 
      ? (secondaryResults?.fsc_mean || secondaryResults?.size_statistics?.mean || 100)
      : (secondaryResults?.ssc_mean || 50)
    const secondaryStd = secondaryResults?.size_statistics?.std || secondaryMean * 0.3

    const minVal = Math.min(
      primaryResults ? primaryMean - 3 * primaryStd : Infinity, 
      secondaryResults ? secondaryMean - 3 * secondaryStd : Infinity
    )
    const maxVal = Math.max(
      primaryResults ? primaryMean + 3 * primaryStd : -Infinity, 
      secondaryResults ? secondaryMean + 3 * secondaryStd : -Infinity
    )
    const binSize = (maxVal - minVal) / bins

    for (let i = 0; i < bins; i++) {
      const binStart = minVal + i * binSize
      const binMid = binStart + binSize / 2

      // Gaussian distribution approximation for visualization
      const primaryValue = primaryResults 
        ? Math.exp(-0.5 * Math.pow((binMid - primaryMean) / primaryStd, 2)) * 100
        : 0
      const secondaryValue = secondaryResults
        ? Math.exp(-0.5 * Math.pow((binMid - secondaryMean) / secondaryStd, 2)) * 100
        : 0

      data.push({
        bin: binMid.toFixed(0),
        binValue: binMid,
        primary: Math.round(primaryValue),
        secondary: Math.round(secondaryValue)
      })
    }

    return data
  }, [primaryResults, secondaryResults, parameter])

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
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={histogramData}>
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
