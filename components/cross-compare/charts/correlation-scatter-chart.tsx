"use client"

import { useMemo } from "react"
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
  ZAxis,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScatterChart as ScatterChartIcon } from "lucide-react"

interface CorrelationScatterChartProps {
  fcsValues: number[]
  ntaValues: number[]
  metric?: string
  title?: string
}

interface ScatterPoint {
  fcs: number
  nta: number
  label?: string
}

// Calculate linear regression
function calculateLinearRegression(points: ScatterPoint[]) {
  const n = points.length
  if (n < 2) return { slope: 1, intercept: 0, r2: 0 }

  let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0

  for (const point of points) {
    sumX += point.fcs
    sumY += point.nta
    sumXY += point.fcs * point.nta
    sumX2 += point.fcs * point.fcs
    sumY2 += point.nta * point.nta
  }

  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX)
  const intercept = (sumY - slope * sumX) / n

  // Calculate R²
  const yMean = sumY / n
  let ssRes = 0, ssTot = 0

  for (const point of points) {
    const predicted = slope * point.fcs + intercept
    ssRes += Math.pow(point.nta - predicted, 2)
    ssTot += Math.pow(point.nta - yMean, 2)
  }

  const r2 = ssTot === 0 ? 1 : 1 - ssRes / ssTot

  return { slope, intercept, r2: Math.max(0, Math.min(1, r2)) }
}

// Custom tooltip component
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload || !payload.length) return null

  const data = payload[0].payload
  return (
    <div className="bg-background/95 backdrop-blur-sm border border-border rounded-lg p-3 shadow-lg">
      {data.label && (
        <p className="font-semibold text-sm mb-1">{data.label}</p>
      )}
      <div className="space-y-1 text-xs">
        <p>
          <span className="text-[hsl(var(--chart-1))]">FCS:</span>{" "}
          <span className="font-medium">{data.fcs.toFixed(2)} nm</span>
        </p>
        <p>
          <span className="text-[hsl(var(--chart-2))]">NTA:</span>{" "}
          <span className="font-medium">{data.nta.toFixed(2)} nm</span>
        </p>
        <p className="text-muted-foreground">
          Δ: {Math.abs(data.nta - data.fcs).toFixed(2)} nm (
          {((Math.abs(data.nta - data.fcs) / ((data.nta + data.fcs) / 2)) * 100).toFixed(1)}%)
        </p>
      </div>
    </div>
  )
}

export function CorrelationScatterChart({
  fcsValues,
  ntaValues,
  metric = "Size",
  title = "FCS vs NTA Correlation",
}: CorrelationScatterChartProps) {
  const hasData = fcsValues.length > 0 && ntaValues.length > 0

  const { scatterData, regression, minVal, maxVal } = useMemo(() => {
    if (!hasData) {
      return {
        scatterData: [] as ScatterPoint[],
        regression: { slope: 1, intercept: 0, r2: 0 },
        minVal: 0,
        maxVal: 100,
      }
    }

    // Pair the values
    const len = Math.min(fcsValues.length, ntaValues.length)
    const data = Array.from({ length: len }, (_, i) => ({
      fcs: fcsValues[i],
      nta: ntaValues[i],
    }))

    const reg = calculateLinearRegression(data)

    // Calculate min/max for reference line
    const allValues = [...data.map(d => d.fcs), ...data.map(d => d.nta)]
    const min = Math.min(...allValues) * 0.9
    const max = Math.max(...allValues) * 1.1

    return {
      scatterData: data,
      regression: reg,
      minVal: min,
      maxVal: max,
    }
  }, [fcsValues, ntaValues, hasData])

  // Generate regression line points
  const regressionLine = useMemo(() => {
    return [
      { fcs: minVal, nta: regression.slope * minVal + regression.intercept },
      { fcs: maxVal, nta: regression.slope * maxVal + regression.intercept },
    ]
  }, [regression, minVal, maxVal])

  // Calculate correlation strength label
  const correlationStrength = useMemo(() => {
    const r2 = regression.r2
    if (r2 >= 0.9) return { label: "Excellent", color: "bg-green-500" }
    if (r2 >= 0.7) return { label: "Good", color: "bg-blue-500" }
    if (r2 >= 0.5) return { label: "Moderate", color: "bg-yellow-500" }
    return { label: "Weak", color: "bg-red-500" }
  }, [regression.r2])

  if (!hasData) {
    return (
      <Card className="card-3d">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{title}</CardTitle>
          <CardDescription>
            {metric} measurements comparison between Flow Cytometry and NTA
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-80 flex flex-col items-center justify-center text-muted-foreground border border-dashed border-border rounded-lg bg-muted/10">
            <ScatterChartIcon className="h-10 w-10 mb-3 opacity-40" />
            <p className="text-sm font-medium">No Correlation Data Available</p>
            <p className="text-xs mt-1 max-w-xs text-center">
              Upload and analyze both FCS and NTA files to see the correlation scatter plot.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="card-3d">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">{title}</CardTitle>
            <CardDescription>
              {metric} measurements comparison between Flow Cytometry and NTA
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="font-mono">
              R² = {regression.r2.toFixed(4)}
            </Badge>
            <Badge className={correlationStrength.color}>
              {correlationStrength.label}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                type="number"
                dataKey="fcs"
                name="FCS"
                domain={[minVal, maxVal]}
                tickFormatter={(value) => value.toFixed(0)}
                label={{
                  value: `FCS ${metric} (nm)`,
                  position: "insideBottom",
                  offset: -10,
                  style: { fill: "#94a3b8", fontSize: 12 },
                }}
                stroke="#64748b"
                tick={{ fontSize: 11 }}
              />
              <YAxis
                type="number"
                dataKey="nta"
                name="NTA"
                domain={[minVal, maxVal]}
                tickFormatter={(value) => value.toFixed(0)}
                label={{
                  value: `NTA ${metric} (nm)`,
                  angle: -90,
                  position: "insideLeft",
                  style: { fill: "#94a3b8", fontSize: 12 },
                }}
                stroke="#64748b"
                tick={{ fontSize: 11 }}
              />
              <ZAxis range={[25, 60]} />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                verticalAlign="top"
                height={36}
                formatter={(value) => (
                  <span className="text-sm text-muted-foreground">{value}</span>
                )}
              />

              {/* Identity line (y = x) for reference */}
              <ReferenceLine
                segment={[
                  { x: minVal, y: minVal },
                  { x: maxVal, y: maxVal },
                ]}
                stroke="#64748b"
                strokeDasharray="5 5"
                strokeWidth={1}
              />

              {/* Regression line - use invisible shape to only show line */}
              <Scatter
                name="Regression Line"
                data={regressionLine}
                line={{ stroke: "hsl(var(--chart-3))", strokeWidth: 2 }}
                shape={({ cx, cy }: { cx?: number; cy?: number }) => (
                  <circle cx={cx} cy={cy} r={0} fill="transparent" />
                )}
                legendType="line"
              />

              {/* Data points */}
              <Scatter
                name="Measurements"
                data={scatterData}
                fill="hsl(var(--chart-1))"
                stroke="hsl(var(--chart-1))"
                strokeWidth={2}
                fillOpacity={0.6}
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        {/* Regression Statistics */}
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div className="p-3 rounded-lg bg-secondary/30 border border-border/50">
            <p className="text-xs text-muted-foreground">Slope</p>
            <p className="font-mono font-semibold">{regression.slope.toFixed(4)}</p>
          </div>
          <div className="p-3 rounded-lg bg-secondary/30 border border-border/50">
            <p className="text-xs text-muted-foreground">Intercept</p>
            <p className="font-mono font-semibold">{regression.intercept.toFixed(2)} nm</p>
          </div>
          <div className="p-3 rounded-lg bg-secondary/30 border border-border/50">
            <p className="text-xs text-muted-foreground">R² (Coefficient)</p>
            <p className="font-mono font-semibold">{(regression.r2 * 100).toFixed(2)}%</p>
          </div>
          <div className="p-3 rounded-lg bg-secondary/30 border border-border/50">
            <p className="text-xs text-muted-foreground">Data Points</p>
            <p className="font-mono font-semibold">{scatterData.length}</p>
          </div>
        </div>

        {/* Interpretation */}
        <div className="mt-3 p-3 rounded-lg bg-primary/5 border border-primary/20">
          <p className="text-xs text-muted-foreground">
            <span className="font-medium text-foreground">Interpretation:</span>{" "}
            {regression.slope > 0.95 && regression.slope < 1.05 && regression.r2 > 0.9
              ? "Excellent agreement between FCS and NTA measurements. Both methods show consistent results."
              : regression.r2 > 0.7
                ? `Good correlation with a slope of ${regression.slope.toFixed(2)}. ${regression.slope > 1 ? "NTA tends to measure larger sizes." : "FCS tends to measure larger sizes."}`
                : "Moderate to weak correlation. Consider reviewing measurement conditions or sample preparation."}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
