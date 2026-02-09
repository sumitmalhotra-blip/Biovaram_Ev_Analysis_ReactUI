"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { CrossValidationResult } from "@/lib/api-client"
import { 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  ShieldCheck,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  Minus,
  FlaskConical,
  BarChart3
} from "lucide-react"

interface ValidationVerdictCardProps {
  result: CrossValidationResult
  className?: string
}

const VERDICT_CONFIG = {
  PASS: {
    icon: ShieldCheck,
    color: "emerald",
    bgClass: "bg-emerald-500/10 border-emerald-500/30",
    iconBg: "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400",
    badgeBg: "bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 border-emerald-500",
    label: "Validated",
  },
  ACCEPTABLE: {
    icon: CheckCircle2,
    color: "blue",
    bgClass: "bg-blue-500/10 border-blue-500/30",
    iconBg: "bg-blue-500/20 text-blue-600 dark:text-blue-400",
    badgeBg: "bg-blue-500/20 text-blue-700 dark:text-blue-400 border-blue-500",
    label: "Acceptable",
  },
  WARNING: {
    icon: AlertTriangle,
    color: "amber",
    bgClass: "bg-amber-500/10 border-amber-500/30",
    iconBg: "bg-amber-500/20 text-amber-600 dark:text-amber-400",
    badgeBg: "bg-amber-500/20 text-amber-700 dark:text-amber-400 border-amber-500",
    label: "Warning",
  },
  FAIL: {
    icon: XCircle,
    color: "rose",
    bgClass: "bg-rose-500/10 border-rose-500/30",
    iconBg: "bg-rose-500/20 text-rose-600 dark:text-rose-400",
    badgeBg: "bg-rose-500/20 text-rose-700 dark:text-rose-400 border-rose-500",
    label: "Failed",
  },
} as const

export function ValidationVerdictCard({ result, className }: ValidationVerdictCardProps) {
  const config = VERDICT_CONFIG[result.comparison.verdict]
  const VerdictIcon = config.icon

  const metrics = [
    {
      label: "D10",
      fcs: result.fcs_statistics.d10,
      nta: result.nta_statistics.d10,
      diff: result.comparison.d10_difference_pct,
    },
    {
      label: "D50 (Median)",
      fcs: result.fcs_statistics.d50,
      nta: result.nta_statistics.d50,
      diff: result.comparison.d50_difference_pct,
      primary: true,
    },
    {
      label: "D90",
      fcs: result.fcs_statistics.d90,
      nta: result.nta_statistics.d90,
      diff: result.comparison.d90_difference_pct,
    },
    {
      label: "Mean",
      fcs: result.fcs_statistics.mean,
      nta: result.nta_statistics.mean,
      diff: result.comparison.mean_difference_pct,
    },
  ]

  const getDiffIcon = (diff: number) => {
    if (diff < 5) return <Minus className="h-3 w-3 text-emerald-500" />
    if (diff < 15) return <TrendingUp className="h-3 w-3 text-amber-500" />
    return <TrendingDown className="h-3 w-3 text-rose-500" />
  }

  const getDiffColor = (diff: number) => {
    if (diff < 10) return "text-emerald-600 dark:text-emerald-400"
    if (diff < 20) return "text-amber-600 dark:text-amber-400"
    return "text-rose-600 dark:text-rose-400"
  }

  return (
    <Card className={cn("card-3d overflow-hidden border-2", config.bgClass, className)}>
      <CardContent className="p-0">
        {/* Verdict Header */}
        <div className="p-4 md:p-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className={cn("p-3 rounded-xl shadow-lg", config.iconBg)}>
                <VerdictIcon className="h-7 w-7" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-bold">Mie Calibration</h3>
                  <Badge variant="outline" className={cn("font-bold text-sm px-3", config.badgeBg)}>
                    {config.label}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground mt-0.5">
                  {result.comparison.verdict_detail}
                </p>
              </div>
            </div>
          </div>

          {/* D50 Hero Comparison */}
          <div className="mt-5 p-4 rounded-xl bg-background/50 border">
            <div className="text-xs text-muted-foreground uppercase tracking-wider font-medium mb-3">
              Primary Metric: D50 (Median Diameter)
            </div>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <div className="text-center">
                <div className="flex items-center gap-1.5 mb-1">
                  <FlaskConical className="h-4 w-4 text-blue-500" />
                  <span className="text-xs text-muted-foreground font-medium">FCS (Mie)</span>
                </div>
                <span className="text-3xl font-bold font-mono text-blue-600 dark:text-blue-400">
                  {result.comparison.d50_fcs.toFixed(1)}
                </span>
                <span className="text-sm text-muted-foreground ml-1">nm</span>
              </div>
              
              <div className="flex flex-col items-center gap-1">
                <ArrowRight className="h-5 w-5 text-muted-foreground" />
                <Badge variant="outline" className={cn("font-mono text-xs", getDiffColor(result.comparison.d50_difference_pct))}>
                  {result.comparison.d50_difference_pct.toFixed(1)}%
                </Badge>
              </div>
              
              <div className="text-center">
                <div className="flex items-center gap-1.5 mb-1">
                  <BarChart3 className="h-4 w-4 text-purple-500" />
                  <span className="text-xs text-muted-foreground font-medium">NTA (Measured)</span>
                </div>
                <span className="text-3xl font-bold font-mono text-purple-600 dark:text-purple-400">
                  {result.comparison.d50_nta.toFixed(1)}
                </span>
                <span className="text-sm text-muted-foreground ml-1">nm</span>
              </div>
            </div>
            <div className="text-center mt-2">
              <span className="text-xs text-muted-foreground">
                Absolute difference: {result.comparison.d50_difference_nm.toFixed(1)} nm
              </span>
            </div>
          </div>
        </div>

        {/* Detailed Metrics */}
        <div className="border-t p-4 md:px-6">
          <div className="text-xs text-muted-foreground uppercase tracking-wider font-medium mb-3">
            Size Percentile Comparison
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {metrics.map((m) => (
              <div
                key={m.label}
                className={cn(
                  "flex items-center justify-between p-3 rounded-lg transition-colors",
                  m.primary ? "bg-primary/5 border border-primary/20" : "bg-secondary/30"
                )}
              >
                <div className="flex items-center gap-2">
                  {getDiffIcon(m.diff)}
                  <span className={cn("text-sm", m.primary ? "font-semibold" : "font-medium")}>
                    {m.label}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-sm font-mono">
                  <span className="text-blue-600 dark:text-blue-400">{m.fcs.toFixed(1)}</span>
                  <span className="text-muted-foreground text-xs">vs</span>
                  <span className="text-purple-600 dark:text-purple-400">{m.nta.toFixed(1)}</span>
                  <Badge variant="secondary" className={cn("text-xs ml-1", getDiffColor(m.diff))}>
                    {m.diff.toFixed(1)}%
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Statistical Tests */}
        {result.statistical_tests && (
          <div className="border-t p-4 md:px-6">
            <div className="text-xs text-muted-foreground uppercase tracking-wider font-medium mb-3">
              Statistical Tests
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <div className="p-3 rounded-lg bg-secondary/30">
                <div className="text-xs text-muted-foreground">KS Test</div>
                <div className="font-mono text-sm font-medium mt-1">
                  p = {result.statistical_tests.kolmogorov_smirnov.p_value.toExponential(2)}
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  {result.statistical_tests.kolmogorov_smirnov.interpretation}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-secondary/30">
                <div className="text-xs text-muted-foreground">Mann-Whitney U</div>
                <div className="font-mono text-sm font-medium mt-1">
                  p = {result.statistical_tests.mann_whitney_u.p_value.toExponential(2)}
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  {result.statistical_tests.mann_whitney_u.interpretation}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-secondary/30">
                <div className="text-xs text-muted-foreground">Bhattacharyya</div>
                <div className="font-mono text-sm font-medium mt-1">
                  {result.statistical_tests.bhattacharyya_coefficient.value.toFixed(3)}
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  {result.statistical_tests.bhattacharyya_coefficient.interpretation}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Mie Parameters & Data Summary */}
        <div className="border-t p-4 md:px-6 bg-muted/20">
          <div className="flex flex-wrap gap-2 text-xs">
            <Badge variant="outline" className="font-mono">
              Mie: {result.mie_parameters.method}
            </Badge>
            <Badge variant="outline" className="font-mono">
              λ = {result.mie_parameters.wavelength_nm}nm
            </Badge>
            <Badge variant="outline" className="font-mono">
              n_p = {result.mie_parameters.n_particle}
            </Badge>
            <Badge variant="outline" className="font-mono">
              FCS: {result.data_summary.fcs_valid_sizes.toLocaleString()} events
            </Badge>
            <Badge variant="outline" className="font-mono">
              NTA: {result.data_summary.nta_valid_bins.toLocaleString()} bins
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default ValidationVerdictCard
