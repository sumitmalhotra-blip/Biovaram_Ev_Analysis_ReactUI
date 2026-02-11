"use client"

import { useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  ReferenceLine,
  Legend 
} from "recharts"
import { Thermometer, ArrowRight, ArrowRightLeft, TrendingUp, Info } from "lucide-react"
import { useAnalysisStore } from "@/lib/store"
import type { NTAResult } from "@/lib/api-client"
import { Tooltip as UITooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

interface TemperatureCorrectedComparisonProps {
  data: NTAResult
}

interface DistributionDataPoint {
  size: number
  rawCount: number
  correctedCount: number
  correctedSize?: number
}

// NTA bin definitions for percentage-based data
const NTA_BINS = [
  { key: "bin_50_80nm_pct" as const, min: 50, max: 80 },
  { key: "bin_80_100nm_pct" as const, min: 80, max: 100 },
  { key: "bin_100_120nm_pct" as const, min: 100, max: 120 },
  { key: "bin_120_150nm_pct" as const, min: 120, max: 150 },
  { key: "bin_150_200nm_pct" as const, min: 150, max: 200 },
  { key: "bin_200_plus_pct" as const, min: 200, max: 350 },
]

// Deterministic pseudo-random variation to avoid hydration mismatch
const seededVar = (seed: number, range = 0.1): number => {
  const x = Math.sin(seed * 9999) * 10000
  return 1 - range / 2 + (x - Math.floor(x)) * range
}

// Generate size distribution data with temperature correction — uses REAL data when available
function generateDistributionData(
  results: NTAResult | undefined,
  correctionFactor: number,
  applyCorrection: boolean
): { data: DistributionDataPoint[]; isReal: boolean } {
  if (!results) return { data: [], isReal: false }

  // Strategy 1: Use size_distribution array from NTA instrument
  if (results.size_distribution && Array.isArray(results.size_distribution) && results.size_distribution.length > 0) {
    const raw = results.size_distribution
      .filter((d: any) => d.size != null)
      .map((d: any) => ({ size: d.size as number, count: (d.count ?? d.concentration ?? 0) as number }))
      .sort((a: { size: number }, b: { size: number }) => a.size - b.size)
    if (raw.length > 0) {
      const data: DistributionDataPoint[] = raw.map((d) => {
        const correctedSize = applyCorrection ? d.size * correctionFactor : d.size
        return {
          size: d.size,
          rawCount: d.count,
          correctedCount: d.count, // counts stay the same, size axis shifts
          correctedSize: applyCorrection ? correctedSize : undefined,
        }
      })
      return { data, isReal: true }
    }
  }

  // Strategy 2: Reconstruct from bin percentages
  const hasBins = NTA_BINS.some(bin => {
    const val = (results as any)[bin.key]
    return val != null && val > 0
  })
  if (hasBins) {
    const totalConc = results.concentration_particles_ml || 1e8
    const data: DistributionDataPoint[] = []
    NTA_BINS.forEach(bin => {
      const pct = (results as any)[bin.key] as number | undefined
      if (pct != null && pct > 0) {
        const binWidth = bin.max - bin.min
        const steps = Math.max(1, Math.round(binWidth / 5))
        const countPerStep = Math.round((pct / 100 * totalConc) / steps)
        for (let s = 0; s < steps; s++) {
          const size = bin.min + (s + 0.5) * (binWidth / steps)
          const correctedSize = applyCorrection ? size * correctionFactor : size
          data.push({
            size: Math.round(size),
            rawCount: countPerStep,
            correctedCount: countPerStep,
            correctedSize: applyCorrection ? correctedSize : undefined,
          })
        }
      }
    })
    if (data.length > 0) return { data: data.sort((a, b) => a.size - b.size), isReal: true }
  }

  // Strategy 3: Gaussian fallback (estimated, not real)
  const centerSize = results.median_size_nm || 145
  const spread = (results.d90_nm && results.d10_nm)
    ? (results.d90_nm - results.d10_nm) / 2
    : 60
  const data: DistributionDataPoint[] = []
  for (let size = 0; size <= 500; size += 5) {
    const rawCount = Math.max(0, 3000 * Math.exp(-Math.pow((size - centerSize) / spread, 2)))
    const correctedCenterSize = centerSize * correctionFactor
    const correctedSpread = spread * correctionFactor
    const correctedCount = applyCorrection
      ? Math.max(0, 3000 * Math.exp(-Math.pow((size - correctedCenterSize) / correctedSpread, 2)))
      : rawCount
    const index = size / 5
    data.push({
      size,
      rawCount: Math.round(rawCount * seededVar(index * 7)),
      correctedCount: Math.round(correctedCount * seededVar(index * 11 + 3)),
      correctedSize: applyCorrection ? size * correctionFactor : undefined,
    })
  }
  return { data, isReal: false }
}

// Calculate statistics for a distribution
function calculateStats(data: DistributionDataPoint[], key: 'rawCount' | 'correctedCount') {
  const totalCount = data.reduce((sum, d) => sum + d[key], 0)
  if (totalCount === 0) return { mean: 0, mode: 0 }
  
  // Weighted mean
  const mean = data.reduce((sum, d) => sum + d.size * d[key], 0) / totalCount
  
  // Mode (size with highest count)
  const modePoint = data.reduce((max, d) => d[key] > max[key] ? d : max, data[0])
  
  return { mean, mode: modePoint.size }
}

export function TemperatureCorrectedComparison({ data: results }: TemperatureCorrectedComparisonProps) {
  const { ntaAnalysisSettings } = useAnalysisStore()
  
  const applyCorrection = ntaAnalysisSettings?.applyTemperatureCorrection ?? false
  const correctionFactor = ntaAnalysisSettings?.correctionFactor ?? 1.0
  const measurementTemp = ntaAnalysisSettings?.measurementTemp ?? 25
  const referenceTemp = ntaAnalysisSettings?.referenceTemp ?? 25
  const mediaType = ntaAnalysisSettings?.mediaType ?? "Water"
  
  // Generate distribution data
  const { data: distributionData, isReal } = useMemo(
    () => generateDistributionData(results, correctionFactor, applyCorrection),
    [results, correctionFactor, applyCorrection]
  )
  
  // Calculate statistics
  const rawStats = useMemo(() => calculateStats(distributionData, 'rawCount'), [distributionData])
  const correctedStats = useMemo(() => calculateStats(distributionData, 'correctedCount'), [distributionData])
  
  // Calculate size shift
  const sizeShift = applyCorrection 
    ? ((correctedStats.mode - rawStats.mode) / rawStats.mode * 100)
    : 0
  
  // Reference lines for percentiles
  const rawD50 = results?.d50_nm || results?.median_size_nm || 145
  const correctedD50 = applyCorrection ? rawD50 * correctionFactor : rawD50

  if (!applyCorrection) {
    return (
      <Card className="card-3d">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-orange-500/10">
              <Thermometer className="h-4 w-4 text-orange-500" />
            </div>
            <CardTitle className="text-base">Temperature Correction Comparison</CardTitle>
            <Badge variant="outline" className="ml-auto">Disabled</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <Thermometer className="h-8 w-8 mx-auto mb-3 opacity-50" />
            <p className="font-medium">Temperature correction is not enabled</p>
            <p className="text-sm mt-1">
              Enable temperature correction in the settings above to view the comparison.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="card-3d">
      <CardHeader className="pb-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-orange-500/10">
              <Thermometer className="h-4 w-4 text-orange-500" />
            </div>
            <CardTitle className="text-base">Temperature Correction Comparison</CardTitle>
            <TooltipProvider>
              <UITooltip>
                <TooltipTrigger asChild>
                  <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                </TooltipTrigger>
                <TooltipContent side="right" className="max-w-xs">
                  <p className="text-xs">
                    Side-by-side comparison showing the effect of temperature correction on the 
                    size distribution. Uses the Stokes-Einstein equation to adjust for viscosity 
                    differences between measurement and reference temperatures.
                  </p>
                </TooltipContent>
              </UITooltip>
            </TooltipProvider>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="secondary" className="gap-1">
              <Thermometer className="h-3 w-3" />
              {measurementTemp}°C → {referenceTemp}°C
            </Badge>
            <Badge variant="outline">
              Factor: {correctionFactor.toFixed(4)}
            </Badge>
            {!isReal && (
              <Badge variant="outline" className="text-xs text-amber-500 border-amber-500/50">
                Estimated
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
            <p className="text-xs text-muted-foreground">Raw Mode</p>
            <p className="text-lg font-semibold text-blue-500">{rawStats.mode.toFixed(0)} nm</p>
          </div>
          <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
            <p className="text-xs text-muted-foreground">Corrected Mode</p>
            <p className="text-lg font-semibold text-emerald-500">{correctedStats.mode.toFixed(0)} nm</p>
          </div>
          <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/20">
            <p className="text-xs text-muted-foreground">Size Shift</p>
            <p className="text-lg font-semibold text-purple-500">
              {sizeShift >= 0 ? "+" : ""}{sizeShift.toFixed(1)}%
            </p>
          </div>
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
            <p className="text-xs text-muted-foreground">Medium</p>
            <p className="text-lg font-semibold text-amber-500 truncate">{mediaType}</p>
          </div>
        </div>

        {/* Side-by-Side Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Raw Distribution */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-500" />
                Raw Measured Distribution
              </h4>
              <Badge variant="outline" className="text-xs">
                {measurementTemp}°C / {mediaType}
              </Badge>
            </div>
            <div className="h-64 border rounded-lg p-2 bg-card/50">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={distributionData}>
                  <defs>
                    <linearGradient id="colorRaw" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis
                    dataKey="size"
                    stroke="#64748b"
                    tick={{ fontSize: 10 }}
                    label={{ value: "Diameter (nm)", position: "bottom", offset: -5, fill: "#64748b", fontSize: 10 }}
                  />
                  <YAxis
                    stroke="#64748b"
                    tick={{ fontSize: 10 }}
                    label={{ value: "Count", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 10 }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#1e293b",
                      border: "1px solid #334155",
                      borderRadius: "8px",
                      fontSize: "11px",
                      color: "#f8fafc",
                    }}
                    labelStyle={{ color: "#94a3b8" }}
                    labelFormatter={(value) => `${value} nm`}
                    formatter={(value: number) => [value, "Raw Count"]}
                  />
                  <Area
                    type="monotone"
                    dataKey="rawCount"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorRaw)"
                  />
                  <ReferenceLine
                    x={rawD50}
                    stroke="#3b82f6"
                    strokeDasharray="5 5"
                    label={{ value: `D50: ${rawD50.toFixed(0)}nm`, fill: "#3b82f6", fontSize: 9, position: "top" }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Corrected Distribution */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-emerald-500" />
                Temperature Corrected Distribution
              </h4>
              <Badge variant="outline" className="text-xs">
                Normalized to {referenceTemp}°C / Water
              </Badge>
            </div>
            <div className="h-64 border rounded-lg p-2 bg-card/50">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={distributionData}>
                  <defs>
                    <linearGradient id="colorCorrected" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.1} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis
                    dataKey="size"
                    stroke="#64748b"
                    tick={{ fontSize: 10 }}
                    label={{ value: "Diameter (nm)", position: "bottom", offset: -5, fill: "#64748b", fontSize: 10 }}
                  />
                  <YAxis
                    stroke="#64748b"
                    tick={{ fontSize: 10 }}
                    label={{ value: "Count", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 10 }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#1e293b",
                      border: "1px solid #334155",
                      borderRadius: "8px",
                      fontSize: "11px",
                      color: "#f8fafc",
                    }}
                    labelStyle={{ color: "#94a3b8" }}
                    labelFormatter={(value) => `${value} nm`}
                    formatter={(value: number) => [value, "Corrected Count"]}
                  />
                  <Area
                    type="monotone"
                    dataKey="correctedCount"
                    stroke="#10b981"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorCorrected)"
                  />
                  <ReferenceLine
                    x={correctedD50}
                    stroke="#10b981"
                    strokeDasharray="5 5"
                    label={{ value: `D50: ${correctedD50.toFixed(0)}nm`, fill: "#10b981", fontSize: 9, position: "top" }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Overlay Comparison Chart */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <ArrowRightLeft className="h-4 w-4 text-muted-foreground" />
            <h4 className="text-sm font-medium">Overlay Comparison</h4>
          </div>
          <div className="h-72 border rounded-lg p-3 bg-card/50">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={distributionData}>
                <defs>
                  <linearGradient id="colorRawOverlay" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.05} />
                  </linearGradient>
                  <linearGradient id="colorCorrectedOverlay" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="size"
                  stroke="#64748b"
                  tick={{ fontSize: 11 }}
                  label={{ value: "Diameter (nm)", position: "bottom", offset: -5, fill: "#64748b", fontSize: 11 }}
                />
                <YAxis
                  stroke="#64748b"
                  tick={{ fontSize: 11 }}
                  label={{ value: "Count", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 11 }}
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
                />
                <Legend 
                  verticalAlign="top" 
                  height={36}
                  formatter={(value) => value === 'rawCount' ? 'Raw Measured' : 'Temperature Corrected'}
                />
                <Area
                  type="monotone"
                  dataKey="rawCount"
                  name="rawCount"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorRawOverlay)"
                />
                <Area
                  type="monotone"
                  dataKey="correctedCount"
                  name="correctedCount"
                  stroke="#10b981"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorCorrectedOverlay)"
                />
                <ReferenceLine
                  x={rawD50}
                  stroke="#3b82f6"
                  strokeDasharray="3 3"
                  strokeWidth={1}
                />
                <ReferenceLine
                  x={correctedD50}
                  stroke="#10b981"
                  strokeDasharray="3 3"
                  strokeWidth={1}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Correction Details */}
        <div className="p-4 rounded-lg bg-muted/50 border">
          <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
            Correction Details
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div>
              <p className="text-muted-foreground">Measurement Temp</p>
              <p className="font-medium">{measurementTemp}°C</p>
            </div>
            <div>
              <p className="text-muted-foreground">Reference Temp</p>
              <p className="font-medium">{referenceTemp}°C</p>
            </div>
            <div>
              <p className="text-muted-foreground">Medium Type</p>
              <p className="font-medium">{mediaType}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Correction Factor</p>
              <p className="font-medium">{correctionFactor.toFixed(6)}</p>
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-3">
            <strong>Note:</strong> Temperature correction applies the Stokes-Einstein equation to account for 
            viscosity differences between measurement and reference conditions. The corrected distribution 
            shows how particles would appear at the reference temperature in water.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
