"use client"

import { useMemo, useState } from "react"
import {
  ComposedChart,
  Scatter,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ZAxis,
  Legend,
  ReferenceLine,
} from "recharts"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Info, Eye, EyeOff, Layers } from "lucide-react"
import { Tooltip as UITooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { CHART_COLORS, useAnalysisStore } from "@/lib/store"

export interface DiameterDataPoint {
  diameter: number
  ssc: number
  index?: number
  isAnomaly?: boolean
}

interface DiameterVsSSCChartProps {
  data?: DiameterDataPoint[]
  anomalousIndices?: number[]
  highlightAnomalies?: boolean
  showMieTheory?: boolean
  showLegend?: boolean
  height?: number
  refractiveIndex?: number
  wavelength?: number
  // Overlay support
  secondaryData?: DiameterDataPoint[]
  secondaryAnomalousIndices?: number[]
}

// Generate Mie theory curve for reference
// Simplified Mie scattering approximation for EVs
// SSC ∝ d^α where α ≈ 2-4 depending on size regime
function generateMieTheoryCurve(
  minDiameter: number = 20,
  maxDiameter: number = 500,
  steps: number = 50,
  refractiveIndex: number = 1.38,
  wavelength: number = 488
): Array<{ diameter: number; mieSSC: number }> {
  const curve: Array<{ diameter: number; mieSSC: number }> = []
  const step = (maxDiameter - minDiameter) / steps
  
  // Constants for Mie calculation approximation
  const nMedium = 1.335 // Water
  const m = refractiveIndex / nMedium // Relative refractive index
  const k = (2 * Math.PI * nMedium) / (wavelength / 1000) // Wave number (wavelength in μm)
  
  for (let d = minDiameter; d <= maxDiameter; d += step) {
    const r = d / 2 // Radius in nm
    const x = k * (r / 1000) // Size parameter (r in μm)
    
    // Simplified Mie scattering intensity approximation
    // For small particles (Rayleigh regime): I ∝ d^6
    // For larger particles: I ∝ d^2 to d^4
    // We use a smooth transition
    let sscIntensity: number
    
    if (x < 0.1) {
      // Rayleigh regime: I ∝ d^6
      sscIntensity = Math.pow(d / 100, 6) * 500
    } else if (x < 1) {
      // Transition regime: I ∝ d^4
      const rayleigh = Math.pow(d / 100, 6) * 500
      const mie = Math.pow(d / 100, 4) * 2000
      const t = (x - 0.1) / 0.9 // Transition factor
      sscIntensity = rayleigh * (1 - t) + mie * t
    } else {
      // Mie regime: I ∝ d^2 with oscillations
      const qScat = 2 - (4 / x) * Math.sin(x) + (4 / (x * x)) * (1 - Math.cos(x))
      sscIntensity = qScat * Math.pow(d / 100, 2) * 3000
    }
    
    // Apply refractive index contrast factor
    const contrastFactor = Math.pow((m * m - 1) / (m * m + 2), 2)
    sscIntensity *= contrastFactor * 10
    
    curve.push({
      diameter: Math.round(d),
      mieSSC: Math.max(0, sscIntensity),
    })
  }
  
  return curve
}

// Generate EV size reference lines - TASK-018: Use consistent colors
const EV_SIZE_REFERENCES = [
  { diameter: 50, label: "Small EVs", color: CHART_COLORS.smallEV },
  { diameter: 100, label: "Exosomes upper", color: CHART_COLORS.primary },
  { diameter: 150, label: "Microvesicles", color: CHART_COLORS.largeEV },
  { diameter: 200, label: "Large EVs", color: CHART_COLORS.anomaly },
]

export function DiameterVsSSCChart({
  data,
  anomalousIndices = [],
  highlightAnomalies = true,
  showMieTheory = true,
  showLegend = true,
  height = 400,
  refractiveIndex = 1.38,
  wavelength = 488,
  secondaryData,
  secondaryAnomalousIndices = [],
}: DiameterVsSSCChartProps) {
  const { overlayConfig, fcsAnalysis, secondaryFcsAnalysis } = useAnalysisStore()
  
  // Overlay visibility toggles
  const [showPrimary, setShowPrimary] = useState(true)
  const [showSecondary, setShowSecondary] = useState(true)
  
  // Check if overlay is active - allow demo data generation when enabled
  const hasRealSecondaryData = (secondaryData?.length || 0) > 0
  const hasOverlay = overlayConfig.enabled && secondaryFcsAnalysis.results && overlayConfig.showOverlaidDiameter
  
  // Generate Mie theory reference curve
  const mieTheoryCurve = useMemo(
    () => generateMieTheoryCurve(20, 500, 50, refractiveIndex, wavelength),
    [refractiveIndex, wavelength]
  )

  // PERFORMANCE FIX: Limit max points for display
  const MAX_DISPLAY_POINTS = 1500

  // Process data to separate normal and anomalous points
  // Deterministic pseudo-random for SSR compatibility
  const seededRandom = (seed: number): number => {
    const x = Math.sin(seed * 9999) * 10000
    return x - Math.floor(x)
  }

  const { normalData, anomalyData, stats } = useMemo(() => {
    if (!data || data.length === 0) {
      // Generate demonstration data based on Mie theory with noise
      // PERFORMANCE FIX: Reduced from 800 to 300 points
      const normal: Array<{ diameter: number; ssc: number; z: number; index: number }> = []
      const anomalies: Array<{ diameter: number; ssc: number; z: number; index: number }> = []

      for (let i = 0; i < 300; i++) {
        // Generate diameter with log-normal distribution centered around 120nm
        // Use deterministic seeded random for SSR compatibility
        const logMean = Math.log(120)
        const logStd = 0.5
        const r1 = seededRandom(i * 4)
        const r2 = seededRandom(i * 4 + 1)
        const r3 = seededRandom(i * 4 + 2)
        const diameter = Math.exp(logMean + logStd * (r1 + r2 + r3 - 1.5))
        
        // Calculate expected SSC from Mie theory
        const r = diameter / 2
        const k = (2 * Math.PI * 1.335) / (wavelength / 1000)
        const x = k * (r / 1000)
        let expectedSSC: number
        
        if (x < 0.1) {
          expectedSSC = Math.pow(diameter / 100, 6) * 500
        } else if (x < 1) {
          expectedSSC = Math.pow(diameter / 100, 4) * 2000
        } else {
          const qScat = 2 - (4 / x) * Math.sin(x) + (4 / (x * x)) * (1 - Math.cos(x))
          expectedSSC = qScat * Math.pow(diameter / 100, 2) * 3000
        }
        
        const contrastFactor = Math.pow((refractiveIndex / 1.335) ** 2 - 1, 2) / Math.pow((refractiveIndex / 1.335) ** 2 + 2, 2) * 10
        expectedSSC *= contrastFactor
        
        // Add measurement noise using deterministic random
        const noise = 1 + (seededRandom(i * 4 + 3) - 0.5) * 0.6
        const ssc = Math.max(10, expectedSSC * noise)
        
        const point = {
          diameter: Math.round(diameter * 10) / 10,
          ssc: Math.round(ssc * 10) / 10,
          z: 20,
          index: i,
        }
        
        // Classify as anomaly if deviation from theory is too large
        if (seededRandom(i * 4 + 4) > 0.97 || noise > 1.4 || noise < 0.6) {
          anomalies.push({ ...point, z: 60 })
        } else {
          normal.push(point)
        }
      }

      const allDiameters = [...normal, ...anomalies].map(p => p.diameter)
      return {
        normalData: normal,
        anomalyData: anomalies,
        stats: {
          count: normal.length + anomalies.length,
          minDiameter: Math.min(...allDiameters),
          maxDiameter: Math.max(...allDiameters),
          medianDiameter: allDiameters.sort((a, b) => a - b)[Math.floor(allDiameters.length / 2)],
        },
      }
    }

    // PERFORMANCE FIX: Sample data if too large - use deterministic sampling
    let processedData = data
    if (data.length > MAX_DISPLAY_POINTS) {
      const step = Math.ceil(data.length / MAX_DISPLAY_POINTS)
      processedData = data.filter((_, i) => i % step === 0)
    }

    // Process real data
    const anomalySet = new Set(anomalousIndices)
    const normal: Array<{ diameter: number; ssc: number; z: number; index: number }> = []
    const anomalies: Array<{ diameter: number; ssc: number; z: number; index: number }> = []
    const allDiameters: number[] = []

    processedData.forEach((point, idx) => {
      const pointIndex = point.index ?? idx
      allDiameters.push(point.diameter)
      
      const dataPoint = {
        diameter: point.diameter,
        ssc: point.ssc,
        z: 20,
        index: pointIndex,
      }

      if (highlightAnomalies && (point.isAnomaly || anomalySet.has(pointIndex))) {
        anomalies.push({ ...dataPoint, z: 60 })
      } else {
        normal.push(dataPoint)
      }
    })

    const sortedDiameters = [...allDiameters].sort((a, b) => a - b)
    return {
      normalData: normal,
      anomalyData: anomalies,
      stats: {
        count: data.length,
        minDiameter: Math.min(...allDiameters),
        maxDiameter: Math.max(...allDiameters),
        medianDiameter: sortedDiameters[Math.floor(sortedDiameters.length / 2)],
      },
    }
  }, [data, anomalousIndices, highlightAnomalies, refractiveIndex, wavelength])

  // Process secondary data for overlay - generate demo if no real data
  const { secondaryNormalData, secondaryAnomalyData, secondaryStats } = useMemo(() => {
    if (!hasOverlay) {
      return { 
        secondaryNormalData: [], 
        secondaryAnomalyData: [], 
        secondaryStats: { count: 0, minDiameter: 0, maxDiameter: 0, medianDiameter: 0 } 
      }
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
      const normal: Array<{ diameter: number; ssc: number; z: number; index: number }> = []
      const anomalies: Array<{ diameter: number; ssc: number; z: number; index: number }> = []
      const allDiameters: number[] = []

      processedData.forEach((point, idx) => {
        const pointIndex = point.index ?? idx
        allDiameters.push(point.diameter)
        
        const dataPoint = {
          diameter: point.diameter,
          ssc: point.ssc,
          z: 20,
          index: pointIndex,
        }

        if (highlightAnomalies && (point.isAnomaly || anomalySet.has(pointIndex))) {
          anomalies.push({ ...dataPoint, z: 50 })
        } else {
          normal.push(dataPoint)
        }
      })

      const sortedDiameters = [...allDiameters].sort((a, b) => a - b)
      return {
        secondaryNormalData: normal,
        secondaryAnomalyData: anomalies,
        secondaryStats: {
          count: secondaryData.length,
          minDiameter: allDiameters.length ? Math.min(...allDiameters) : 0,
          maxDiameter: allDiameters.length ? Math.max(...allDiameters) : 0,
          medianDiameter: sortedDiameters.length ? sortedDiameters[Math.floor(sortedDiameters.length / 2)] : 0,
        },
      }
    }
    
    // Generate demo secondary data with shifted distribution
    const normal: Array<{ diameter: number; ssc: number; z: number; index: number }> = []
    const anomalies: Array<{ diameter: number; ssc: number; z: number; index: number }> = []
    const allDiameters: number[] = []
    
    for (let i = 0; i < 300; i++) {
      // Use different seed offset and slightly shifted distribution for comparison
      const logMean = Math.log(140)  // Shifted from 120nm
      const logStd = 0.45
      const r1 = seededRandom(i * 6 + 200)
      const r2 = seededRandom(i * 6 + 201)
      const r3 = seededRandom(i * 6 + 202)
      
      // Box-Muller for log-normal
      const u1 = Math.max(0.0001, r1)
      const u2 = r2
      const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2)
      const diameter = Math.exp(logMean + logStd * z)
      
      if (diameter >= 20 && diameter <= 500) {
        // Use Mie theory approximation for expected SSC
        const sizeParam = (Math.PI * diameter) / wavelength
        const mieSSC = Math.pow(sizeParam, 4) * Math.pow(refractiveIndex - 1.33, 2) * 2e5
        const sscNoise = 1 + (r3 - 0.5) * 0.5  // Different noise pattern
        const ssc = mieSSC * sscNoise
        
        allDiameters.push(diameter)
        const point = { 
          diameter: Math.round(diameter * 10) / 10, 
          ssc, 
          z: 20, 
          index: i + 10000 
        }
        
        if (seededRandom(i * 6 + 203) > 0.96) {
          anomalies.push({ ...point, z: 50 })
        } else {
          normal.push(point)
        }
      }
    }
    
    const sortedDiameters = [...allDiameters].sort((a, b) => a - b)
    return {
      secondaryNormalData: normal,
      secondaryAnomalyData: anomalies,
      secondaryStats: {
        count: normal.length + anomalies.length,
        minDiameter: allDiameters.length ? Math.min(...allDiameters) : 0,
        maxDiameter: allDiameters.length ? Math.max(...allDiameters) : 0,
        medianDiameter: sortedDiameters.length ? sortedDiameters[Math.floor(sortedDiameters.length / 2)] : 0,
      },
    }
  }, [hasOverlay, hasRealSecondaryData, secondaryData, secondaryAnomalousIndices, highlightAnomalies, refractiveIndex, wavelength])

  const totalPoints = normalData.length + anomalyData.length
  const totalSecondaryPoints = secondaryNormalData.length + secondaryAnomalyData.length
  const anomalyPercentage = totalPoints > 0 ? ((anomalyData.length / totalPoints) * 100).toFixed(2) : "0.00"

  return (
    <div className="space-y-3">
      {/* Header with overlay controls */}
      {hasOverlay && (
        <div className="flex items-center gap-2 mb-2">
          <Badge variant="secondary" className="gap-1">
            <Layers className="h-3 w-3" />
            Overlay
          </Badge>
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
        </div>
      )}
      
      {/* Stats Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <div className="flex items-center gap-3">
          <span>Events: {totalPoints.toLocaleString()}</span>
          <span>•</span>
          <span>Diameter: {stats.minDiameter?.toFixed(0)}-{stats.maxDiameter?.toFixed(0)} nm</span>
          <span>•</span>
          <span>Median: {stats.medianDiameter?.toFixed(1)} nm</span>
          {anomalyData.length > 0 && highlightAnomalies && (
            <>
              <span>•</span>
              <Badge variant="destructive" className="h-5 px-1.5 text-xs">
                {anomalyData.length} anomalies ({anomalyPercentage}%)
              </Badge>
            </>
          )}
          {/* Overlay stats */}
          {hasOverlay && totalSecondaryPoints > 0 && (
            <>
              <span>|</span>
              <span style={{ color: overlayConfig.secondaryColor }}>
                Comparison: {totalSecondaryPoints.toLocaleString()} 
                (Median: {secondaryStats.medianDiameter?.toFixed(1)} nm)
              </span>
            </>
          )}
        </div>
        
        <TooltipProvider>
          <UITooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1 cursor-help">
                <Info className="h-3.5 w-3.5" />
                <span className="text-xs">Mie Theory</span>
              </div>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="text-xs">
                <strong>Mie Scattering Theory:</strong> Predicts how light scatters off 
                spherical particles. SSC intensity scales approximately with d² to d⁶ 
                depending on the size regime. The purple line shows theoretical prediction 
                for EVs (n={refractiveIndex}) at λ={wavelength}nm.
              </p>
            </TooltipContent>
          </UITooltip>
        </TooltipProvider>
      </div>

      {/* Chart */}
      <div style={{ height: `${height}px` }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart margin={{ top: 10, right: 30, bottom: 25, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
            
            <XAxis
              dataKey="diameter"
              type="number"
              domain={[0, 500]}
              stroke="#64748b"
              tick={{ fontSize: 11 }}
              tickCount={10}
              label={{ 
                value: "Estimated Diameter (nm)", 
                position: "bottom", 
                offset: 5, 
                fill: "#64748b", 
                fontSize: 12 
              }}
            />
            
            <YAxis
              dataKey="ssc"
              type="number"
              stroke="#64748b"
              tick={{ fontSize: 11 }}
              label={{ 
                value: "SSC-A Intensity", 
                angle: -90, 
                position: "insideLeft", 
                fill: "#64748b", 
                fontSize: 12 
              }}
            />
            
            <ZAxis dataKey="z" range={[15, 80]} />
            
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "8px",
                fontSize: "12px",
                color: "#f8fafc",
              }}
              labelStyle={{ color: "#94a3b8" }}
              formatter={(value: number, name: string) => {
                if (name === "mieSSC") return [value.toFixed(1), "Mie Theory SSC"]
                return [value.toFixed(1), name === "ssc" ? "SSC-A" : name]
              }}
              labelFormatter={(label) => `Diameter: ${label} nm`}
            />
            
            {showLegend && (
              <Legend
                wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }}
                iconType="circle"
                verticalAlign="top"
                height={36}
              />
            )}

            {/* EV size category reference lines */}
            {EV_SIZE_REFERENCES.map((ref) => (
              <ReferenceLine
                key={ref.diameter}
                x={ref.diameter}
                stroke={ref.color}
                strokeDasharray="4 4"
                strokeWidth={1}
                opacity={0.6}
                label={{
                  value: ref.label,
                  position: "top",
                  fill: ref.color,
                  fontSize: 9,
                  offset: 5,
                }}
              />
            ))}

            {/* Mie theory curve - TASK-018: Use consistent purple */}
            {showMieTheory && (
              <Line
                data={mieTheoryCurve}
                type="monotone"
                dataKey="mieSSC"
                stroke={CHART_COLORS.primary}
                strokeWidth={2}
                dot={false}
                name="Mie Theory"
                legendType="line"
              />
            )}

            {/* Primary normal events scatter */}
            {showPrimary && (
              <Scatter
                name={hasOverlay ? (fcsAnalysis.file?.name?.slice(0, 20) || "Primary") : "Normal Events"}
                data={normalData}
                fill={hasOverlay ? overlayConfig.primaryColor : CHART_COLORS.primary}
                fillOpacity={hasOverlay ? overlayConfig.primaryOpacity : 0.5}
                shape="circle"
              />
            )}

            {/* Primary anomalous events scatter */}
            {showPrimary && anomalyData.length > 0 && highlightAnomalies && (
              <Scatter
                name="Anomalous Events"
                data={anomalyData}
                fill={CHART_COLORS.anomaly}
                fillOpacity={0.8}
                shape="diamond"
              />
            )}
            
            {/* Secondary normal events scatter for overlay */}
            {hasOverlay && showSecondary && secondaryNormalData.length > 0 && (
              <Scatter
                name={secondaryFcsAnalysis.file?.name?.slice(0, 20) || "Comparison"}
                data={secondaryNormalData}
                fill={overlayConfig.secondaryColor}
                fillOpacity={overlayConfig.secondaryOpacity}
                shape="circle"
              />
            )}
            
            {/* Secondary anomalous events scatter for overlay */}
            {hasOverlay && showSecondary && secondaryAnomalyData.length > 0 && highlightAnomalies && (
              <Scatter
                name="Comparison Anomalies"
                data={secondaryAnomalyData}
                fill="#f97316"
                fillOpacity={0.7}
                shape="square"
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Legend for size categories */}
      <div className="flex flex-wrap justify-center gap-3 text-xs">
        {EV_SIZE_REFERENCES.map((ref) => (
          <div key={ref.diameter} className="flex items-center gap-1.5">
            <div 
              className="w-3 h-0.5" 
              style={{ backgroundColor: ref.color, opacity: 0.6 }}
            />
            <span className="text-muted-foreground">{ref.label} ({ref.diameter}nm)</span>
          </div>
        ))}
      </div>
    </div>
  )
}
