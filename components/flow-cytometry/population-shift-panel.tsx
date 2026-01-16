"use client"

/**
 * Population Shift Detection Panel
 * CRMIT-004: Detect population shifts between measurements
 * 
 * Features:
 * - Pairwise sample comparison
 * - Baseline comparison mode
 * - Temporal/sequential analysis
 * - Statistical test results visualization
 * - Severity indicators and recommendations
 */

import { useState, useCallback } from "react"
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
  AlertTriangle,
  CheckCircle,
  XCircle,
  ArrowRight,
  BarChart3,
  TrendingUp,
  Target,
  Clock,
  Info,
  Loader2,
  ChevronDown,
  ChevronUp,
} from "lucide-react"
import { cn } from "@/lib/utils"
import type {
  PopulationShiftResponse,
  MultiSampleShiftResponse,
  ShiftTestResult,
  PopulationMetrics,
} from "@/lib/api-client"

// Severity configuration
const SEVERITY_CONFIG = {
  none: {
    icon: CheckCircle,
    color: "text-emerald-600",
    bgColor: "bg-emerald-50 dark:bg-emerald-900/20",
    borderColor: "border-emerald-200 dark:border-emerald-800",
    badgeVariant: "outline" as const,
    label: "No Shift",
  },
  minor: {
    icon: Info,
    color: "text-blue-600",
    bgColor: "bg-blue-50 dark:bg-blue-900/20",
    borderColor: "border-blue-200 dark:border-blue-800",
    badgeVariant: "secondary" as const,
    label: "Minor",
  },
  moderate: {
    icon: AlertTriangle,
    color: "text-yellow-600",
    bgColor: "bg-yellow-50 dark:bg-yellow-900/20",
    borderColor: "border-yellow-200 dark:border-yellow-800",
    badgeVariant: "default" as const,
    label: "Moderate",
  },
  major: {
    icon: AlertTriangle,
    color: "text-orange-600",
    bgColor: "bg-orange-50 dark:bg-orange-900/20",
    borderColor: "border-orange-200 dark:border-orange-800",
    badgeVariant: "default" as const,
    label: "Major",
  },
  critical: {
    icon: XCircle,
    color: "text-red-600",
    bgColor: "bg-red-50 dark:bg-red-900/20",
    borderColor: "border-red-200 dark:border-red-800",
    badgeVariant: "destructive" as const,
    label: "Critical",
  },
}

// Test display names
const TEST_NAMES: Record<string, string> = {
  ks: "Kolmogorov-Smirnov",
  emd: "Earth Mover's Distance",
  mean: "Mean Shift (Welch's t)",
  variance: "Variance Shift (Levene's)",
}

interface PopulationShiftPanelProps {
  className?: string
}

export function PopulationShiftPanel({ className }: PopulationShiftPanelProps) {
  const { apiSamples } = useAnalysisStore()
  const {
    detectPopulationShift,
    compareToBaseline,
    temporalShiftAnalysis,
  } = useApi()

  // State
  const [activeMode, setActiveMode] = useState<"pairwise" | "baseline" | "temporal">("pairwise")
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [result, setResult] = useState<PopulationShiftResponse | MultiSampleShiftResponse | null>(null)

  // Pairwise mode state
  const [sampleA, setSampleA] = useState<string>("")
  const [sampleB, setSampleB] = useState<string>("")

  // Baseline mode state
  const [baselineSample, setBaselineSample] = useState<string>("")
  const [selectedSamples, setSelectedSamples] = useState<string[]>([])

  // Temporal mode state
  const [temporalSamples, setTemporalSamples] = useState<string[]>([])

  // Common options
  const [metric, setMetric] = useState<string>("particle_size")
  const [dataSource, setDataSource] = useState<"fcs" | "nta">("fcs")
  const [selectedTests, setSelectedTests] = useState<string[]>(["ks", "emd", "mean", "variance"])
  const [alpha, setAlpha] = useState<number>(0.05)

  // Expanded sections
  const [expandedComparison, setExpandedComparison] = useState<number | null>(null)

  // Available samples for selection
  const availableSamples = apiSamples.filter(s => 
    dataSource === "fcs" ? s.files?.fcs : s.files?.nta
  )

  // Handle test toggle
  const toggleTest = useCallback((test: string) => {
    setSelectedTests(prev => 
      prev.includes(test) 
        ? prev.filter(t => t !== test)
        : [...prev, test]
    )
  }, [])

  // Handle sample selection for baseline/temporal modes
  const toggleSampleSelection = useCallback((sampleId: string, mode: "baseline" | "temporal") => {
    if (mode === "baseline") {
      setSelectedSamples(prev =>
        prev.includes(sampleId)
          ? prev.filter(s => s !== sampleId)
          : [...prev, sampleId]
      )
    } else {
      setTemporalSamples(prev =>
        prev.includes(sampleId)
          ? prev.filter(s => s !== sampleId)
          : [...prev, sampleId]
      )
    }
  }, [])

  // Run analysis
  const runAnalysis = useCallback(async () => {
    if (selectedTests.length === 0) return

    setIsAnalyzing(true)
    setResult(null)

    try {
      let response: PopulationShiftResponse | MultiSampleShiftResponse | null = null

      if (activeMode === "pairwise" && sampleA && sampleB) {
        response = await detectPopulationShift({
          sample_id_a: sampleA,
          sample_id_b: sampleB,
          metric,
          data_source: dataSource,
          tests: selectedTests as Array<"ks" | "emd" | "mean" | "variance">,
          alpha,
        })
      } else if (activeMode === "baseline" && baselineSample && selectedSamples.length > 0) {
        response = await compareToBaseline({
          baseline_sample_id: baselineSample,
          sample_ids: selectedSamples,
          metric,
          data_source: dataSource,
          tests: selectedTests as Array<"ks" | "emd" | "mean" | "variance">,
          alpha,
        })
      } else if (activeMode === "temporal" && temporalSamples.length >= 2) {
        response = await temporalShiftAnalysis({
          sample_ids: temporalSamples,
          metric,
          data_source: dataSource,
          tests: selectedTests as Array<"ks" | "emd" | "mean" | "variance">,
          alpha,
        })
      }

      setResult(response)
    } finally {
      setIsAnalyzing(false)
    }
  }, [
    activeMode, sampleA, sampleB, baselineSample, selectedSamples, temporalSamples,
    metric, dataSource, selectedTests, alpha,
    detectPopulationShift, compareToBaseline, temporalShiftAnalysis
  ])

  // Check if analysis can run
  const canRunAnalysis = useCallback(() => {
    if (selectedTests.length === 0) return false
    if (activeMode === "pairwise") return sampleA && sampleB && sampleA !== sampleB
    if (activeMode === "baseline") return baselineSample && selectedSamples.length > 0
    if (activeMode === "temporal") return temporalSamples.length >= 2
    return false
  }, [activeMode, sampleA, sampleB, baselineSample, selectedSamples, temporalSamples, selectedTests])

  return (
    <Card className={cn("", className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-primary" />
          Population Shift Detection
        </CardTitle>
        <CardDescription>
          Compare particle populations between samples to detect statistically significant shifts
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Mode Tabs */}
        <Tabs value={activeMode} onValueChange={(v) => setActiveMode(v as typeof activeMode)}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="pairwise" className="flex items-center gap-1">
              <ArrowRight className="h-3 w-3" />
              Pairwise
            </TabsTrigger>
            <TabsTrigger value="baseline" className="flex items-center gap-1">
              <Target className="h-3 w-3" />
              Baseline
            </TabsTrigger>
            <TabsTrigger value="temporal" className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Temporal
            </TabsTrigger>
          </TabsList>

          {/* Pairwise Mode */}
          <TabsContent value="pairwise" className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Sample A (Reference)</Label>
                <Select value={sampleA} onValueChange={setSampleA}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select sample..." />
                  </SelectTrigger>
                  <SelectContent>
                    {availableSamples.map(sample => (
                      <SelectItem 
                        key={sample.sample_id} 
                        value={sample.sample_id}
                        disabled={sample.sample_id === sampleB}
                      >
                        {sample.sample_id}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Sample B (Comparison)</Label>
                <Select value={sampleB} onValueChange={setSampleB}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select sample..." />
                  </SelectTrigger>
                  <SelectContent>
                    {availableSamples.map(sample => (
                      <SelectItem 
                        key={sample.sample_id} 
                        value={sample.sample_id}
                        disabled={sample.sample_id === sampleA}
                      >
                        {sample.sample_id}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </TabsContent>

          {/* Baseline Mode */}
          <TabsContent value="baseline" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Baseline/Reference Sample</Label>
              <Select value={baselineSample} onValueChange={setBaselineSample}>
                <SelectTrigger>
                  <SelectValue placeholder="Select baseline..." />
                </SelectTrigger>
                <SelectContent>
                  {availableSamples.map(sample => (
                    <SelectItem key={sample.sample_id} value={sample.sample_id}>
                      {sample.sample_id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Samples to Compare ({selectedSamples.length} selected)</Label>
              <ScrollArea className="h-32 rounded-md border p-2">
                <div className="space-y-2">
                  {availableSamples
                    .filter(s => s.sample_id !== baselineSample)
                    .map(sample => (
                      <div key={sample.sample_id} className="flex items-center gap-2">
                        <Checkbox
                          id={`baseline-${sample.sample_id}`}
                          checked={selectedSamples.includes(sample.sample_id)}
                          onCheckedChange={() => toggleSampleSelection(sample.sample_id, "baseline")}
                        />
                        <label 
                          htmlFor={`baseline-${sample.sample_id}`}
                          className="text-sm cursor-pointer"
                        >
                          {sample.sample_id}
                        </label>
                      </div>
                    ))}
                </div>
              </ScrollArea>
            </div>
          </TabsContent>

          {/* Temporal Mode */}
          <TabsContent value="temporal" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Samples in Time Order ({temporalSamples.length} selected, minimum 2)</Label>
              <p className="text-xs text-muted-foreground">
                Select samples in chronological order. Each will be compared to its predecessor.
              </p>
              <ScrollArea className="h-40 rounded-md border p-2">
                <div className="space-y-2">
                  {availableSamples.map(sample => (
                    <div key={sample.sample_id} className="flex items-center gap-2">
                      <Checkbox
                        id={`temporal-${sample.sample_id}`}
                        checked={temporalSamples.includes(sample.sample_id)}
                        onCheckedChange={() => toggleSampleSelection(sample.sample_id, "temporal")}
                      />
                      <label 
                        htmlFor={`temporal-${sample.sample_id}`}
                        className="text-sm cursor-pointer flex-1"
                      >
                        {sample.sample_id}
                      </label>
                      {temporalSamples.includes(sample.sample_id) && (
                        <Badge variant="outline" className="text-xs">
                          #{temporalSamples.indexOf(sample.sample_id) + 1}
                        </Badge>
                      )}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          </TabsContent>
        </Tabs>

        <Separator />

        {/* Analysis Options */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Metric</Label>
            <Select value={metric} onValueChange={setMetric}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="particle_size">Particle Size (nm)</SelectItem>
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

        {/* Statistical Tests */}
        <div className="space-y-2">
          <Label>Statistical Tests</Label>
          <div className="flex flex-wrap gap-2">
            {Object.entries(TEST_NAMES).map(([key, name]) => (
              <TooltipProvider key={key}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant={selectedTests.includes(key) ? "default" : "outline"}
                      size="sm"
                      onClick={() => toggleTest(key)}
                      className="text-xs"
                    >
                      {key.toUpperCase()}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{name}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            ))}
          </div>
        </div>

        {/* Run Button */}
        <Button 
          onClick={runAnalysis} 
          disabled={!canRunAnalysis() || isAnalyzing}
          className="w-full"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <BarChart3 className="mr-2 h-4 w-4" />
              Run Population Shift Analysis
            </>
          )}
        </Button>

        {/* Results */}
        {result && (
          <div className="space-y-4">
            <Separator />
            
            {"comparisons" in result ? (
              // Multi-sample result (baseline or temporal)
              <MultiSampleResultDisplay 
                result={result} 
                expandedIndex={expandedComparison}
                onToggleExpand={setExpandedComparison}
              />
            ) : (
              // Single pairwise result
              <PairwiseResultDisplay result={result} />
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Pairwise result display component
function PairwiseResultDisplay({ result }: { result: PopulationShiftResponse }) {
  const severity = SEVERITY_CONFIG[result.overall_severity]
  const SeverityIcon = severity.icon

  return (
    <div className="space-y-4">
      {/* Overall Result */}
      <div className={cn(
        "p-4 rounded-lg border",
        severity.bgColor,
        severity.borderColor
      )}>
        <div className="flex items-start gap-3">
          <SeverityIcon className={cn("h-5 w-5 mt-0.5", severity.color)} />
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold">{result.overall_shift_detected ? "Shift Detected" : "No Shift"}</span>
              <Badge variant={severity.badgeVariant}>{severity.label}</Badge>
            </div>
            <p className="text-sm text-muted-foreground mt-1">{result.summary}</p>
          </div>
        </div>
      </div>

      {/* Sample Comparison */}
      <div className="grid grid-cols-2 gap-4">
        <MetricsCard title="Sample A" metrics={result.sample_a} />
        <MetricsCard title="Sample B" metrics={result.sample_b} />
      </div>

      {/* Test Results */}
      <div className="space-y-2">
        <h4 className="font-medium text-sm">Statistical Tests</h4>
        <div className="space-y-2">
          {result.tests.map((test, idx) => (
            <TestResultRow key={idx} test={test} />
          ))}
        </div>
      </div>

      {/* Recommendations */}
      {result.recommendations.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-medium text-sm">Recommendations</h4>
          <ul className="space-y-1">
            {result.recommendations.map((rec, idx) => (
              <li key={idx} className="text-sm text-muted-foreground">
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

// Multi-sample result display component
function MultiSampleResultDisplay({ 
  result, 
  expandedIndex,
  onToggleExpand 
}: { 
  result: MultiSampleShiftResponse
  expandedIndex: number | null
  onToggleExpand: (idx: number | null) => void
}) {
  const severity = SEVERITY_CONFIG[result.max_severity]
  const SeverityIcon = severity.icon

  return (
    <div className="space-y-4">
      {/* Global Summary */}
      <div className={cn(
        "p-4 rounded-lg border",
        severity.bgColor,
        severity.borderColor
      )}>
        <div className="flex items-start gap-3">
          <SeverityIcon className={cn("h-5 w-5 mt-0.5", severity.color)} />
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold">
                {result.mode === "baseline" ? "Baseline Comparison" : "Temporal Analysis"}
              </span>
              <Badge variant={severity.badgeVariant}>{severity.label}</Badge>
            </div>
            <p className="text-sm text-muted-foreground mt-1">{result.global_summary}</p>
          </div>
        </div>
      </div>

      {/* Comparison List */}
      <div className="space-y-2">
        <h4 className="font-medium text-sm">
          {result.comparisons.length} Comparison{result.comparisons.length !== 1 ? "s" : ""}
        </h4>
        <div className="space-y-2">
          {result.comparisons.map((comp, idx) => {
            const compSeverity = SEVERITY_CONFIG[comp.overall_severity]
            const CompIcon = compSeverity.icon
            const isExpanded = expandedIndex === idx

            return (
              <div 
                key={idx}
                className={cn(
                  "rounded-lg border",
                  comp.overall_shift_detected ? compSeverity.borderColor : "border-border"
                )}
              >
                <button
                  onClick={() => onToggleExpand(isExpanded ? null : idx)}
                  className="w-full p-3 flex items-center justify-between hover:bg-muted/50 rounded-t-lg"
                >
                  <div className="flex items-center gap-2">
                    <CompIcon className={cn("h-4 w-4", compSeverity.color)} />
                    <span className="text-sm font-medium">
                      {comp.sample_a.sample_name} → {comp.sample_b.sample_name}
                    </span>
                    <Badge variant={compSeverity.badgeVariant} className="text-xs">
                      {compSeverity.label}
                    </Badge>
                  </div>
                  {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </button>
                
                {isExpanded && (
                  <div className="p-3 pt-0 border-t space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <MetricsCard title="Sample A" metrics={comp.sample_a} compact />
                      <MetricsCard title="Sample B" metrics={comp.sample_b} compact />
                    </div>
                    <div className="space-y-1">
                      {comp.tests.map((test, testIdx) => (
                        <TestResultRow key={testIdx} test={test} compact />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// Metrics card component
function MetricsCard({ 
  title, 
  metrics,
  compact = false 
}: { 
  title: string
  metrics: PopulationMetrics
  compact?: boolean 
}) {
  return (
    <div className={cn(
      "rounded-lg border bg-muted/30 p-3",
      compact && "p-2"
    )}>
      <h5 className={cn(
        "font-medium mb-2",
        compact ? "text-xs" : "text-sm"
      )}>
        {metrics.sample_name}
      </h5>
      <div className={cn(
        "grid gap-1",
        compact ? "grid-cols-2 text-xs" : "grid-cols-2 text-sm"
      )}>
        <div>
          <span className="text-muted-foreground">Mean:</span>{" "}
          <span className="font-mono">{metrics.mean.toFixed(2)}</span>
        </div>
        <div>
          <span className="text-muted-foreground">Median:</span>{" "}
          <span className="font-mono">{metrics.median.toFixed(2)}</span>
        </div>
        <div>
          <span className="text-muted-foreground">Std:</span>{" "}
          <span className="font-mono">{metrics.std.toFixed(2)}</span>
        </div>
        <div>
          <span className="text-muted-foreground">N:</span>{" "}
          <span className="font-mono">{metrics.n_events.toLocaleString()}</span>
        </div>
      </div>
    </div>
  )
}

// Test result row component
function TestResultRow({ test, compact = false }: { test: ShiftTestResult; compact?: boolean }) {
  const severity = SEVERITY_CONFIG[test.severity]
  
  return (
    <div className={cn(
      "flex items-center justify-between p-2 rounded-md",
      test.significant ? severity.bgColor : "bg-muted/30",
      compact && "p-1.5"
    )}>
      <div className="flex items-center gap-2">
        {test.significant ? (
          <AlertTriangle className={cn("h-3 w-3", severity.color)} />
        ) : (
          <CheckCircle className="h-3 w-3 text-emerald-600" />
        )}
        <span className={cn("font-medium", compact ? "text-xs" : "text-sm")}>
          {test.test_name}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              <span className={cn(
                "font-mono",
                compact ? "text-xs" : "text-sm",
                test.significant ? "text-foreground" : "text-muted-foreground"
              )}>
                p={test.p_value.toFixed(4)}
              </span>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="text-xs">{test.interpretation}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
        {test.significant && (
          <Badge variant={severity.badgeVariant} className="text-xs">
            {severity.label}
          </Badge>
        )}
      </div>
    </div>
  )
}

export default PopulationShiftPanel
