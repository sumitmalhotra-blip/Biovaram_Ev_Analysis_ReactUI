"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"
import { FCSResult, NTAResult } from "@/lib/api-client"
import { 
  CheckCircle2, 
  AlertCircle, 
  XCircle, 
  GitCompare,
  TrendingUp,
  Activity
} from "lucide-react"

interface MethodComparisonSummaryProps {
  fcsResults: FCSResult | null
  ntaResults: NTAResult | null
  className?: string
}

export function MethodComparisonSummary({ fcsResults, ntaResults, className }: MethodComparisonSummaryProps) {
  if (!fcsResults || !ntaResults) {
    return null
  }

  // Calculate discrepancy helper
  const calculateDiscrepancy = (ntaValue?: number, fcsValue?: number): number | null => {
    if (!ntaValue || !fcsValue || ntaValue === 0 || fcsValue === 0) return null
    const average = (ntaValue + fcsValue) / 2
    return Math.abs(ntaValue - fcsValue) / average * 100
  }

  // Extract values
  const fcsD10 = fcsResults.size_statistics?.d10
  const fcsD50 = fcsResults.particle_size_median_nm || fcsResults.size_statistics?.d50
  const fcsD90 = fcsResults.size_statistics?.d90
  const fcsMean = fcsResults.size_statistics?.mean

  const ntaD10 = ntaResults.d10_nm || ntaResults.size_statistics?.d10
  const ntaD50 = ntaResults.median_size_nm || ntaResults.d50_nm || ntaResults.size_statistics?.d50
  const ntaD90 = ntaResults.d90_nm || ntaResults.size_statistics?.d90
  const ntaMean = ntaResults.mean_size_nm || ntaResults.size_statistics?.mean

  // Calculate discrepancies
  const discD10 = calculateDiscrepancy(ntaD10, fcsD10)
  const discD50 = calculateDiscrepancy(ntaD50, fcsD50)
  const discD90 = calculateDiscrepancy(ntaD90, fcsD90)
  const discMean = calculateDiscrepancy(ntaMean, fcsMean)

  // Calculate average discrepancy
  const validDiscrepancies = [discD10, discD50, discD90, discMean].filter(d => d !== null) as number[]
  const avgDiscrepancy = validDiscrepancies.length > 0
    ? validDiscrepancies.reduce((sum, d) => sum + d, 0) / validDiscrepancies.length
    : 0

  // Determine overall agreement
  const getAgreementLevel = (disc: number) => {
    if (disc < 10) return { label: "Excellent", color: "emerald" as const, icon: CheckCircle2, score: 95 }
    if (disc < 20) return { label: "Good", color: "blue" as const, icon: CheckCircle2, score: 80 }
    if (disc < 30) return { label: "Moderate", color: "amber" as const, icon: AlertCircle, score: 60 }
    return { label: "Poor", color: "rose" as const, icon: XCircle, score: 40 }
  }

  const agreement = getAgreementLevel(avgDiscrepancy)
  const AgreementIcon = agreement.icon

  // Method characteristics comparison
  const methodComparison = [
    {
      characteristic: "Sample Count",
      fcs: fcsResults.total_events?.toLocaleString() || "N/A",
      nta: ntaResults.total_particles 
        ? ntaResults.total_particles >= 1e6
          ? `${(ntaResults.total_particles / 1e6).toFixed(2)}M`
          : ntaResults.total_particles.toLocaleString()
        : "N/A",
      icon: Activity
    },
    {
      characteristic: "Median Size",
      fcs: fcsD50 ? `${fcsD50.toFixed(1)} nm` : "N/A",
      nta: ntaD50 ? `${ntaD50.toFixed(1)} nm` : "N/A",
      icon: TrendingUp
    },
    {
      characteristic: "Size Range",
      fcs: fcsD10 && fcsD90 ? `${fcsD10.toFixed(0)}-${fcsD90.toFixed(0)} nm` : "N/A",
      nta: ntaD10 && ntaD90 ? `${ntaD10.toFixed(0)}-${ntaD90.toFixed(0)} nm` : "N/A",
      icon: GitCompare
    }
  ]

  return (
    <Card className={cn("card-3d overflow-hidden", className)}>
      <CardContent className="p-0">
        {/* Header Section with Agreement Score */}
        <div className={cn(
          "p-4 md:p-6 relative overflow-hidden",
          agreement.color === "emerald" && "bg-emerald-500/10",
          agreement.color === "blue" && "bg-blue-500/10",
          agreement.color === "amber" && "bg-amber-500/10",
          agreement.color === "rose" && "bg-rose-500/10"
        )}>
          <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className={cn(
                "p-3 rounded-xl shadow-lg",
                agreement.color === "emerald" && "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400",
                agreement.color === "blue" && "bg-blue-500/20 text-blue-600 dark:text-blue-400",
                agreement.color === "amber" && "bg-amber-500/20 text-amber-600 dark:text-amber-400",
                agreement.color === "rose" && "bg-rose-500/20 text-rose-600 dark:text-rose-400"
              )}>
                <AgreementIcon className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-lg font-semibold">Method Agreement</h3>
                <p className="text-sm text-muted-foreground">FCS vs NTA Comparison</p>
              </div>
            </div>
            <div className="flex flex-col items-start md:items-end gap-2">
              <Badge 
                variant="outline"
                className={cn(
                  "text-base font-semibold px-3 py-1",
                  agreement.color === "emerald" && "border-emerald-500 text-emerald-600 dark:text-emerald-400 bg-emerald-500/20",
                  agreement.color === "blue" && "border-blue-500 text-blue-600 dark:text-blue-400 bg-blue-500/20",
                  agreement.color === "amber" && "border-amber-500 text-amber-600 dark:text-amber-400 bg-amber-500/20",
                  agreement.color === "rose" && "border-rose-500 text-rose-600 dark:text-rose-400 bg-rose-500/20"
                )}
              >
                {agreement.label}
              </Badge>
              <p className="text-sm text-muted-foreground">
                {avgDiscrepancy.toFixed(1)}% average discrepancy
              </p>
            </div>
          </div>
          
          {/* Agreement Score Bar */}
          <div className="mt-4 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Agreement Score</span>
              <span className="font-semibold">{agreement.score}%</span>
            </div>
            <Progress 
              value={agreement.score} 
              className={cn(
                "h-2",
                agreement.color === "emerald" && "[&>div]:bg-emerald-500",
                agreement.color === "blue" && "[&>div]:bg-blue-500",
                agreement.color === "amber" && "[&>div]:bg-amber-500",
                agreement.color === "rose" && "[&>div]:bg-rose-500"
              )}
            />
          </div>
        </div>

        {/* Method Comparison Grid */}
        <div className="p-4 md:p-6 border-t space-y-3">
          {methodComparison.map((item) => {
            const Icon = item.icon
            return (
              <div 
                key={item.characteristic}
                className="flex items-center justify-between p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary/10">
                    <Icon className="h-4 w-4 text-primary" />
                  </div>
                  <span className="font-medium text-sm">{item.characteristic}</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <div className="text-right">
                    <div className="flex items-center gap-1.5">
                      <div className="w-2 h-2 rounded-full bg-blue-500" />
                      <span className="font-mono">{item.fcs}</span>
                    </div>
                  </div>
                  <span className="text-muted-foreground">vs</span>
                  <div className="text-right">
                    <div className="flex items-center gap-1.5">
                      <div className="w-2 h-2 rounded-full bg-purple-500" />
                      <span className="font-mono">{item.nta}</span>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Interpretation Guide */}
        <div className="p-4 md:p-6 border-t bg-muted/20">
          <p className="text-xs text-muted-foreground mb-2 font-medium">Interpretation Guidelines:</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-muted-foreground">
            <div className="flex items-start gap-2">
              <CheckCircle2 className="h-3 w-3 text-emerald-500 mt-0.5 shrink-0" />
              <span><strong>Excellent (&lt;10%):</strong> Methods show high correlation and can be used interchangeably</span>
            </div>
            <div className="flex items-start gap-2">
              <CheckCircle2 className="h-3 w-3 text-blue-500 mt-0.5 shrink-0" />
              <span><strong>Good (10-20%):</strong> Acceptable agreement with minor systematic differences</span>
            </div>
            <div className="flex items-start gap-2">
              <AlertCircle className="h-3 w-3 text-amber-500 mt-0.5 shrink-0" />
              <span><strong>Moderate (20-30%):</strong> Noticeable differences, investigate sample preparation</span>
            </div>
            <div className="flex items-start gap-2">
              <XCircle className="h-3 w-3 text-rose-500 mt-0.5 shrink-0" />
              <span><strong>Poor (&gt;30%):</strong> Significant discrepancy, review methodology and calibration</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
