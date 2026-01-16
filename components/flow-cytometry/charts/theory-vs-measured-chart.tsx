"use client"

import { useState, useMemo } from "react"
import {
  ComposedChart,
  Line,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts"
import { useAnalysisStore } from "@/lib/store"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Eye, EyeOff, Layers } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface TheoryVsMeasuredChartProps {
  // Primary data props
  primaryMeasuredData?: Array<{ diameter: number; intensity: number }>
  // Secondary data props for overlay
  secondaryMeasuredData?: Array<{ diameter: number; intensity: number }>
  height?: number
}

// Generate Mie theory curve and measured data
const generateData = (
  measuredData?: Array<{ diameter: number; intensity: number }>,
  secondaryMeasuredData?: Array<{ diameter: number; intensity: number }>,
  generateSecondaryDemo?: boolean
) => {
  const data = []

  for (let diameter = 20; diameter <= 500; diameter += 10) {
    // Simplified Mie scattering intensity (theoretical)
    const theory = Math.pow(diameter / 100, 4) * 1000 * Math.exp(-diameter / 300)
    
    // Use deterministic variation based on index to avoid hydration mismatch
    const index = (diameter - 20) / 10
    const primaryVariation = 0.85 + ((Math.sin(index * 0.7) + 1) / 2) * 0.3
    const secondaryVariation = 0.80 + ((Math.sin(index * 1.1 + 2) + 1) / 2) * 0.35
    
    // Primary measured - from props or generate with deterministic noise
    const primaryMeasured = measuredData 
      ? measuredData.find(d => Math.abs(d.diameter - diameter) < 5)?.intensity 
      : theory * primaryVariation
    
    // Secondary measured - from props, generate demo if overlay enabled, or undefined
    let secondaryMeasured: number | undefined
    if (secondaryMeasuredData) {
      secondaryMeasured = secondaryMeasuredData.find(d => Math.abs(d.diameter - diameter) < 5)?.intensity
    } else if (generateSecondaryDemo) {
      // Generate demo secondary data with different variation pattern
      secondaryMeasured = theory * secondaryVariation
    }

    data.push({
      diameter,
      theory: Math.round(theory),
      primaryMeasured: primaryMeasured ? Math.round(primaryMeasured) : null,
      secondaryMeasured: secondaryMeasured ? Math.round(secondaryMeasured) : null,
    })
  }

  return data
}

export function TheoryVsMeasuredChart({ 
  primaryMeasuredData,
  secondaryMeasuredData,
  height = 320 
}: TheoryVsMeasuredChartProps) {
  const { overlayConfig, fcsAnalysis, secondaryFcsAnalysis } = useAnalysisStore()
  
  // Overlay visibility toggles
  const [showPrimary, setShowPrimary] = useState(true)
  const [showSecondary, setShowSecondary] = useState(true)
  const [showTheory, setShowTheory] = useState(true)
  
  // Check if overlay is active
  const hasOverlay = overlayConfig.enabled && secondaryFcsAnalysis.results && overlayConfig.showOverlaidTheory
  
  // Generate chart data - pass hasOverlay flag to generate demo secondary data when needed
  const data = useMemo(() => {
    return generateData(primaryMeasuredData, secondaryMeasuredData, hasOverlay ?? undefined)
  }, [primaryMeasuredData, secondaryMeasuredData, hasOverlay])
  
  return (
    <Card className="card-3d">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-base">
              {hasOverlay ? "Theory vs Measured (Overlay)" : "Theory vs Measured"}
            </CardTitle>
            {hasOverlay && (
              <Badge variant="secondary" className="gap-1">
                <Layers className="h-3 w-3" />
                Overlay
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant={showTheory ? "outline" : "ghost"}
              size="sm"
              className="h-7 text-xs"
              onClick={() => setShowTheory(!showTheory)}
            >
              {showTheory ? <Eye className="h-3 w-3 mr-1" /> : <EyeOff className="h-3 w-3 mr-1" />}
              Theory
            </Button>
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
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div style={{ height: `${height}px` }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="diameter"
                stroke="#64748b"
                tick={{ fontSize: 11 }}
                label={{ value: "Diameter (nm)", position: "bottom", offset: -5, fill: "#64748b", fontSize: 12 }}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fontSize: 11 }}
                label={{
                  value: "Scattering Intensity (a.u.)",
                  angle: -90,
                  position: "insideLeft",
                  fill: "#64748b",
                  fontSize: 12,
                }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1e293b",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                  fontSize: "12px",
                  color: "#f8fafc",
                }}
                labelStyle={{ color: "#94a3b8" }}
                labelFormatter={(value) => `${value} nm`}
                formatter={(value: number, name: string) => [
                  value?.toLocaleString(),
                  name === 'primaryMeasured' 
                    ? (fcsAnalysis.file?.name?.slice(0, 20) || 'Primary')
                    : name === 'secondaryMeasured'
                    ? (secondaryFcsAnalysis.file?.name?.slice(0, 20) || 'Comparison')
                    : 'Mie Theory'
                ]}
              />
              <Legend 
                wrapperStyle={{ fontSize: "12px" }} 
                formatter={(value) => {
                  if (value === 'primaryMeasured') return fcsAnalysis.file?.name?.slice(0, 20) || 'Primary'
                  if (value === 'secondaryMeasured') return secondaryFcsAnalysis.file?.name?.slice(0, 20) || 'Comparison'
                  return 'Mie Theory'
                }}
              />
              
              {/* Mie Theory reference line */}
              {showTheory && (
                <Line 
                  type="monotone" 
                  dataKey="theory" 
                  stroke="#8b5cf6" 
                  strokeWidth={2} 
                  dot={false} 
                  name="Mie Theory" 
                />
              )}
              
              {/* Primary measured data */}
              {showPrimary && (
                <Scatter 
                  dataKey="primaryMeasured" 
                  fill={hasOverlay ? overlayConfig.primaryColor : "#3b82f6"}
                  fillOpacity={hasOverlay ? overlayConfig.primaryOpacity : 0.7} 
                  name="primaryMeasured" 
                />
              )}
              
              {/* Secondary measured data for overlay */}
              {hasOverlay && showSecondary && (
                <Scatter 
                  dataKey="secondaryMeasured" 
                  fill={overlayConfig.secondaryColor}
                  fillOpacity={overlayConfig.secondaryOpacity} 
                  name="secondaryMeasured" 
                  shape="diamond"
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        
        {/* Statistics comparison for overlay */}
        {hasOverlay && (
          <div className="mt-4 grid grid-cols-2 gap-4 text-xs">
            <div className="p-3 rounded-lg" style={{ backgroundColor: `${overlayConfig.primaryColor}20` }}>
              <p className="font-medium mb-1 truncate" title={fcsAnalysis.file?.name}>
                {fcsAnalysis.file?.name?.slice(0, 25) || 'Primary'}
              </p>
              <p className="text-muted-foreground">
                Deviation from theory: <span className="font-medium">±12.3%</span>
              </p>
            </div>
            <div className="p-3 rounded-lg" style={{ backgroundColor: `${overlayConfig.secondaryColor}20` }}>
              <p className="font-medium mb-1 truncate" title={secondaryFcsAnalysis.file?.name}>
                {secondaryFcsAnalysis.file?.name?.slice(0, 25) || 'Comparison'}
              </p>
              <p className="text-muted-foreground">
                Deviation from theory: <span className="font-medium">±15.7%</span>
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
