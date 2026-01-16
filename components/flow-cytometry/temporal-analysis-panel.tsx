"use client"

/**
 * Temporal Analysis Panel
 * CRMIT-007: Time Correlation Analysis
 * 
 * Features:
 * - Time-series trend visualization
 * - Stability metrics display
 * - Drift detection with change points
 * - Cross-metric correlation matrix
 * - Multi-metric comparison
 * - Interactive time-series chart
 */

import { useState, useCallback, useMemo } from "react"
import { useApi } from "@/hooks/use-api"
import { useAnalysisStore } from "@/lib/store"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
  Area,
  ComposedChart,
} from "recharts"
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  BarChart3,
  Info,
  Loader2,
  XCircle,
  ArrowRight,
} from "lucide-react"
import { cn } from "@/lib/utils"
import type {
  TemporalAnalysisResponse,
  MultiMetricTemporalResponse,
  TrendResult,
  StabilityResult,
  DriftResult,
  TemporalCorrelation,
} from "@/lib/api-client"

// Configuration
const TREND_ICONS = {
  none: Minus,
  linear_increasing: TrendingUp,
  linear_decreasing: TrendingDown,
  exponential_growth: TrendingUp,
  exponential_decay: TrendingDown,
  cyclical: Activity,
  random_walk: Activity,
}

const STABILITY_CONFIG = {
  excellent: { color: "text-emerald-600", bgColor: "bg-emerald-50 dark:bg-emerald-900/20", label: "Excellent" },
  good: { color: "text-green-600", bgColor: "bg-green-50 dark:bg-green-900/20", label: "Good" },
  acceptable: { color: "text-yellow-600", bgColor: "bg-yellow-50 dark:bg-yellow-900/20", label: "Acceptable" },
  poor: { color: "text-orange-600", bgColor: "bg-orange-50 dark:bg-orange-900/20", label: "Poor" },
  unstable: { color: "text-red-600", bgColor: "bg-red-50 dark:bg-red-900/20", label: "Unstable" },
}

const DRIFT_CONFIG = {
  none: { color: "text-emerald-600", bgColor: "bg-emerald-50", variant: "outline" as const, label: "None" },
  minor: { color: "text-blue-600", bgColor: "bg-blue-50", variant: "secondary" as const, label: "Minor" },
  moderate: { color: "text-yellow-600", bgColor: "bg-yellow-50", variant: "default" as const, label: "Moderate" },
  significant: { color: "text-orange-600", bgColor: "bg-orange-50", variant: "default" as const, label: "Significant" },
  critical: { color: "text-red-600", bgColor: "bg-red-50", variant: "destructive" as const, label: "Critical" },
}

interface TemporalAnalysisPanelProps {
  className?: string
}

export function TemporalAnalysisPanel({ className }: TemporalAnalysisPanelProps) {
  const { apiSamples } = useAnalysisStore()
  const { analyzeTemporalTrends, analyzeMultiMetricTemporal } = useApi()

  // State
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [activeTab, setActiveTab] = useState<"single" | "multi">("single")
  const [result, setResult] = useState<TemporalAnalysisResponse | null>(null)
  const [multiResult, setMultiResult] = useState<MultiMetricTemporalResponse | null>(null)

  // Single metric options
  const [selectedSamples, setSelectedSamples] = useState<string[]>([])
  const [metric, setMetric] = useState<string>("particle_size")
  const [dataSource, setDataSource] = useState<"fcs" | "nta">("fcs")

  // Multi-metric options
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([
    "particle_size", "concentration", "fsc", "ssc"
  ])

  // Available samples
  const availableSamples = apiSamples.filter(s => 
    dataSource === "fcs" ? s.files?.fcs : s.files?.nta
  )

  // Handle sample selection
  const toggleSample = useCallback((sampleId: string) => {
    setSelectedSamples(prev =>
      prev.includes(sampleId)
        ? prev.filter(s => s !== sampleId)
        : [...prev, sampleId]
    )
  }, [])

  // Handle metric selection for multi-metric mode
  const toggleMetric = useCallback((metricName: string) => {
    setSelectedMetrics(prev =>
      prev.includes(metricName)
        ? prev.filter(m => m !== metricName)
        : [...prev, metricName]
    )
  }, [])

  // Run analysis
  const runAnalysis = useCallback(async () => {
    if (selectedSamples.length < 3) return

    setIsAnalyzing(true)
    setResult(null)
    setMultiResult(null)

    try {
      if (activeTab === "single") {
        const response = await analyzeTemporalTrends({
          sample_ids: selectedSamples,
          metric,
          data_source: dataSource,
          include_correlations: true,
        })
        setResult(response)
      } else {
        const response = await analyzeMultiMetricTemporal({
          sample_ids: selectedSamples,
          metrics: selectedMetrics,
          data_source: dataSource,
        })
        setMultiResult(response)
      }
    } finally {
      setIsAnalyzing(false)
    }
  }, [
    activeTab, selectedSamples, metric, dataSource, selectedMetrics,
    analyzeTemporalTrends, analyzeMultiMetricTemporal
  ])

  // Check if analysis can run
  const canRunAnalysis = selectedSamples.length >= 3

  return (
    <Card className={cn("", className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-primary" />
          Temporal Analysis
        </CardTitle>
        <CardDescription>
          Analyze time-series trends, stability, and drift in sample measurements
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Mode Tabs */}
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "single" | "multi")}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="single" className="flex items-center gap-1">
              <TrendingUp className="h-3 w-3" />
              Single Metric
            </TabsTrigger>
            <TabsTrigger value="multi" className="flex items-center gap-1">
              <BarChart3 className="h-3 w-3" />
              Multi-Metric
            </TabsTrigger>
          </TabsList>

          {/* Single Metric Mode */}
          <TabsContent value="single" className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Metric</Label>
                <Select value={metric} onValueChange={setMetric}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="particle_size">Particle Size (nm)</SelectItem>
                    <SelectItem value="concentration">Concentration</SelectItem>
                    <SelectItem value="fsc">Forward Scatter (FSC)</SelectItem>
                    <SelectItem value="ssc">Side Scatter (SSC)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Data Source</Label>
                <Select value={dataSource} onValueChange={(v) => setDataSource(v as "fcs" | "nta")}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="fcs">Flow Cytometry (FCS)</SelectItem>
                    <SelectItem value="nta">NTA</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </TabsContent>

          {/* Multi-Metric Mode */}
          <TabsContent value="multi" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Metrics to Analyze</Label>
              <div className="flex flex-wrap gap-2">
                {["particle_size", "concentration", "fsc", "ssc"].map(m => (
                  <Button
                    key={m}
                    variant={selectedMetrics.includes(m) ? "default" : "outline"}
                    size="sm"
                    onClick={() => toggleMetric(m)}
                    className="capitalize"
                  >
                    {m.replace("_", " ")}
                  </Button>
                ))}
              </div>
            </div>
          </TabsContent>
        </Tabs>

        <Separator />

        {/* Sample Selection */}
        <div className="space-y-2">
          <Label>Samples in Chronological Order ({selectedSamples.length} selected, minimum 3)</Label>
          <p className="text-xs text-muted-foreground">
            Select at least 3 samples in time order for temporal analysis.
          </p>
          <ScrollArea className="h-40 rounded-md border p-2">
            <div className="space-y-2">
              {availableSamples.map(sample => (
                <div key={sample.sample_id} className="flex items-center gap-2">
                  <Checkbox
                    id={`temporal-${sample.sample_id}`}
                    checked={selectedSamples.includes(sample.sample_id)}
                    onCheckedChange={() => toggleSample(sample.sample_id)}
                  />
                  <label 
                    htmlFor={`temporal-${sample.sample_id}`}
                    className="text-sm cursor-pointer flex-1"
                  >
                    {sample.sample_id}
                  </label>
                  {selectedSamples.includes(sample.sample_id) && (
                    <Badge variant="outline" className="text-xs">
                      #{selectedSamples.indexOf(sample.sample_id) + 1}
                    </Badge>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>

        {/* Run Button */}
        <Button 
          onClick={runAnalysis} 
          disabled={!canRunAnalysis || isAnalyzing}
          className="w-full"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Activity className="mr-2 h-4 w-4" />
              Run Temporal Analysis
            </>
          )}
        </Button>

        {/* Results */}
        {result && activeTab === "single" && (
          <SingleMetricResults result={result} />
        )}

        {multiResult && activeTab === "multi" && (
          <MultiMetricResults result={multiResult} />
        )}
      </CardContent>
    </Card>
  )
}

// Single Metric Results Component
function SingleMetricResults({ result }: { result: TemporalAnalysisResponse }) {
  // Prepare chart data
  const chartData = useMemo(() => {
    return result.moving_average.map((ma, idx) => ({
      index: idx + 1,
      smoothed: result.smoothed_values[idx] || 0,
      moving_avg: ma,
    }))
  }, [result])

  return (
    <div className="space-y-4 mt-4">
      <Separator />
      
      {/* Summary Card */}
      <div className="rounded-lg border bg-muted/30 p-4">
        <h4 className="font-medium text-sm mb-2">Analysis Summary</h4>
        <p className="text-sm text-muted-foreground">{result.summary}</p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-3 gap-4">
        {/* Trend Card */}
        <TrendCard trend={result.trend} />
        
        {/* Stability Card */}
        <StabilityCard stability={result.stability} />
        
        {/* Drift Card */}
        <DriftCard drift={result.drift} />
      </div>

      {/* Time Series Chart */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Time Series Trend</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis 
                  dataKey="index" 
                  stroke="#64748b"
                  tick={{ fontSize: 11 }}
                  label={{ value: "Sample #", position: "bottom", offset: -5, fontSize: 11 }}
                />
                <YAxis 
                  stroke="#64748b"
                  tick={{ fontSize: 11 }}
                  label={{ value: result.metric, angle: -90, position: "insideLeft", fontSize: 11 }}
                />
                <RechartsTooltip
                  contentStyle={{
                    backgroundColor: "#1e293b",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                    fontSize: "12px",
                    color: "#f8fafc",
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="smoothed"
                  name="Values"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  dot={{ fill: "#8b5cf6", r: 4 }}
                />
                <Line
                  type="monotone"
                  dataKey="moving_avg"
                  name="Moving Avg"
                  stroke="#10b981"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                />
                
                {/* Mean reference line */}
                <ReferenceLine 
                  y={result.stability.mean} 
                  stroke="#f59e0b" 
                  strokeDasharray="3 3"
                  label={{ value: "μ", position: "right", fill: "#f59e0b", fontSize: 10 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Correlations */}
      {result.correlations.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Cross-Metric Correlations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {result.correlations.map((corr, idx) => (
                <CorrelationRow key={idx} correlation={corr} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recommendations */}
      {result.recommendations.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Info className="h-4 w-4" />
              Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {result.recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm">
                  <ArrowRight className="h-4 w-4 mt-0.5 text-primary shrink-0" />
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// Multi-Metric Results Component
function MultiMetricResults({ result }: { result: MultiMetricTemporalResponse }) {
  const stabilityConfig = STABILITY_CONFIG[result.overall_stability.level as keyof typeof STABILITY_CONFIG] 
    || STABILITY_CONFIG.acceptable
  const driftConfig = DRIFT_CONFIG[result.overall_drift.max_severity as keyof typeof DRIFT_CONFIG]
    || DRIFT_CONFIG.none

  return (
    <div className="space-y-4 mt-4">
      <Separator />
      
      {/* Overall Summary */}
      <div className="grid grid-cols-2 gap-4">
        <div className={cn("rounded-lg border p-4", stabilityConfig.bgColor)}>
          <h4 className="font-medium text-sm mb-2">Overall Stability</h4>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className={stabilityConfig.color}>
              {stabilityConfig.label}
            </Badge>
            <span className="text-sm text-muted-foreground">
              Avg CV: {result.overall_stability.average_cv.toFixed(1)}%
            </span>
          </div>
        </div>
        
        <div className={cn("rounded-lg border p-4", driftConfig.bgColor)}>
          <h4 className="font-medium text-sm mb-2">Overall Drift</h4>
          <div className="flex items-center gap-2">
            <Badge variant={driftConfig.variant}>
              {driftConfig.label}
            </Badge>
            <span className="text-sm text-muted-foreground">
              {result.overall_drift.total_drifting_metrics} metric(s) drifting
            </span>
          </div>
        </div>
      </div>

      {/* Individual Metric Results */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Metric-by-Metric Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {Object.entries(result.individual_results).map(([metric, data]) => (
              <MetricSummaryRow key={metric} metric={metric} data={data} />
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Drifting Metrics Details */}
      {result.overall_drift.metrics_with_drift.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-500" />
              Metrics with Drift
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {result.overall_drift.metrics_with_drift.map((item, idx) => {
                const config = DRIFT_CONFIG[item.severity as keyof typeof DRIFT_CONFIG] || DRIFT_CONFIG.minor
                return (
                  <div key={idx} className="flex items-center justify-between p-2 rounded-md bg-muted/30">
                    <span className="font-medium text-sm capitalize">{item.metric.replace("_", " ")}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant={config.variant}>{config.label}</Badge>
                      <span className="text-xs text-muted-foreground">
                        {item.direction} ({(item.magnitude * 100).toFixed(1)}%)
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// Trend Card Component
function TrendCard({ trend }: { trend: TrendResult }) {
  const TrendIcon = TREND_ICONS[trend.type] || Minus
  const isPositive = trend.type.includes("increasing") || trend.type.includes("growth")
  const isNegative = trend.type.includes("decreasing") || trend.type.includes("decay")

  return (
    <Card className="p-4">
      <div className="flex items-center gap-2 mb-2">
        <TrendIcon className={cn(
          "h-5 w-5",
          isPositive && "text-green-500",
          isNegative && "text-red-500",
          !isPositive && !isNegative && "text-gray-500"
        )} />
        <span className="font-medium text-sm">Trend</span>
      </div>
      <div className="space-y-1">
        <p className="text-xs capitalize text-muted-foreground">
          {trend.type.replace(/_/g, " ")}
        </p>
        {trend.is_significant && (
          <div className="flex items-center gap-1">
            <span className="text-xs">R²:</span>
            <span className="text-xs font-mono">{trend.r_squared.toFixed(3)}</span>
          </div>
        )}
        <Badge 
          variant={trend.is_significant ? "default" : "outline"} 
          className="text-xs"
        >
          {trend.is_significant ? "Significant" : "Not significant"}
        </Badge>
      </div>
    </Card>
  )
}

// Stability Card Component
function StabilityCard({ stability }: { stability: StabilityResult }) {
  const config = STABILITY_CONFIG[stability.level] || STABILITY_CONFIG.acceptable

  return (
    <Card className={cn("p-4", config.bgColor)}>
      <div className="flex items-center gap-2 mb-2">
        <Activity className={cn("h-5 w-5", config.color)} />
        <span className="font-medium text-sm">Stability</span>
      </div>
      <div className="space-y-1">
        <Badge variant="outline" className={cn("text-xs", config.color)}>
          {config.label}
        </Badge>
        <p className="text-xs text-muted-foreground">
          CV = {stability.cv.toFixed(1)}%
        </p>
        <p className="text-xs text-muted-foreground">
          μ = {stability.mean.toFixed(2)} ± {stability.std.toFixed(2)}
        </p>
      </div>
    </Card>
  )
}

// Drift Card Component
function DriftCard({ drift }: { drift: DriftResult }) {
  const config = DRIFT_CONFIG[drift.severity] || DRIFT_CONFIG.none
  const DirectionIcon = drift.direction === "increasing" ? TrendingUp :
                        drift.direction === "decreasing" ? TrendingDown : Minus

  return (
    <Card className={cn("p-4", drift.severity !== "none" && config.bgColor)}>
      <div className="flex items-center gap-2 mb-2">
        <AlertTriangle className={cn("h-5 w-5", config.color)} />
        <span className="font-medium text-sm">Drift</span>
      </div>
      <div className="space-y-1">
        <Badge variant={config.variant} className="text-xs">
          {config.label}
        </Badge>
        {drift.is_significant && (
          <>
            <div className="flex items-center gap-1">
              <DirectionIcon className="h-3 w-3" />
              <span className="text-xs capitalize">{drift.direction}</span>
            </div>
            <p className="text-xs text-muted-foreground">
              {(drift.magnitude * 100).toFixed(1)}% change
            </p>
          </>
        )}
        {drift.change_points.length > 0 && (
          <p className="text-xs text-muted-foreground">
            Change points: {drift.change_points.join(", ")}
          </p>
        )}
      </div>
    </Card>
  )
}

// Correlation Row Component
function CorrelationRow({ correlation }: { correlation: TemporalCorrelation }) {
  const strengthColors = {
    none: "bg-gray-100 text-gray-600",
    weak: "bg-blue-100 text-blue-600",
    moderate: "bg-yellow-100 text-yellow-600",
    strong: "bg-green-100 text-green-600",
    very_strong: "bg-emerald-100 text-emerald-600",
  }

  return (
    <div className="flex items-center justify-between p-2 rounded-md bg-muted/30">
      <div className="flex items-center gap-2">
        <span className="text-sm capitalize">{correlation.metric_a.replace("_", " ")}</span>
        <ArrowRight className="h-3 w-3 text-muted-foreground" />
        <span className="text-sm capitalize">{correlation.metric_b.replace("_", " ")}</span>
      </div>
      <div className="flex items-center gap-2">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              <Badge className={cn("text-xs", strengthColors[correlation.strength])}>
                r = {correlation.pearson_r.toFixed(3)}
              </Badge>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="text-xs">{correlation.interpretation}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
        {correlation.is_significant && (
          <CheckCircle className="h-4 w-4 text-green-500" />
        )}
      </div>
    </div>
  )
}

// Metric Summary Row Component
function MetricSummaryRow({ metric, data }: { metric: string; data: any }) {
  const stabilityConfig = STABILITY_CONFIG[data.stability?.level as keyof typeof STABILITY_CONFIG] 
    || STABILITY_CONFIG.acceptable
  const driftConfig = DRIFT_CONFIG[data.drift?.severity as keyof typeof DRIFT_CONFIG]
    || DRIFT_CONFIG.none

  return (
    <div className="flex items-center justify-between p-2 rounded-md bg-muted/30">
      <span className="font-medium text-sm capitalize">{metric.replace("_", " ")}</span>
      <div className="flex items-center gap-2">
        <Badge variant="outline" className={cn("text-xs", stabilityConfig.color)}>
          CV: {data.stability?.cv?.toFixed(1) || 0}%
        </Badge>
        {data.trend?.is_significant && (
          <Badge variant="secondary" className="text-xs">
            {data.trend.type.includes("increasing") ? "↑" : 
             data.trend.type.includes("decreasing") ? "↓" : "→"}
          </Badge>
        )}
        {data.drift?.severity !== "none" && (
          <Badge variant={driftConfig.variant} className="text-xs">
            {driftConfig.label}
          </Badge>
        )}
      </div>
    </div>
  )
}

export default TemporalAnalysisPanel
