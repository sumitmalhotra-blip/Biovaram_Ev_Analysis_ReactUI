"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { cn } from "@/lib/utils"
import { FCSResult, NTAResult } from "@/lib/api-client"
import { TrendingDown, TrendingUp, Minus, BarChart3 } from "lucide-react"

interface StatisticalComparisonTableProps {
  fcsResults: FCSResult | null
  ntaResults: NTAResult | null
  className?: string
}

export function StatisticalComparisonTable({ fcsResults, ntaResults, className }: StatisticalComparisonTableProps) {
  if (!fcsResults || !ntaResults) {
    return (
      <Card className={cn("card-3d", className)}>
        <CardContent className="p-8 text-center text-muted-foreground">
          <BarChart3 className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>Select both FCS and NTA samples to view statistical comparison</p>
        </CardContent>
      </Card>
    )
  }

  // Calculate discrepancy: |NTA - FCS| / ((NTA + FCS) / 2) * 100
  const calculateDiscrepancy = (ntaValue?: number, fcsValue?: number): number | null => {
    if (!ntaValue || !fcsValue || ntaValue === 0 || fcsValue === 0) return null
    const average = (ntaValue + fcsValue) / 2
    return Math.abs(ntaValue - fcsValue) / average * 100
  }

  // Get discrepancy status
  const getDiscrepancyStatus = (discrepancy: number | null) => {
    if (discrepancy === null) return { label: "N/A", color: "secondary" as const, icon: Minus }
    if (discrepancy < 10) return { label: "Excellent", color: "emerald" as const, icon: TrendingDown }
    if (discrepancy < 20) return { label: "Good", color: "blue" as const, icon: Minus }
    if (discrepancy < 30) return { label: "Fair", color: "amber" as const, icon: TrendingUp }
    return { label: "Poor", color: "rose" as const, icon: TrendingUp }
  }

  // Extract values
  const fcsD10 = fcsResults.size_statistics?.d10
  const fcsD50 = fcsResults.particle_size_median_nm || fcsResults.size_statistics?.d50
  const fcsD90 = fcsResults.size_statistics?.d90
  const fcsMean = fcsResults.size_statistics?.mean
  const fcsStd = fcsResults.size_statistics?.std

  const ntaD10 = ntaResults.d10_nm || ntaResults.size_statistics?.d10
  const ntaD50 = ntaResults.median_size_nm || ntaResults.d50_nm || ntaResults.size_statistics?.d50
  const ntaD90 = ntaResults.d90_nm || ntaResults.size_statistics?.d90
  const ntaMean = ntaResults.mean_size_nm || ntaResults.size_statistics?.mean
  const ntaStd = ntaResults.size_statistics?.std

  // Calculate discrepancies
  const discD10 = calculateDiscrepancy(ntaD10, fcsD10)
  const discD50 = calculateDiscrepancy(ntaD50, fcsD50)
  const discD90 = calculateDiscrepancy(ntaD90, fcsD90)
  const discMean = calculateDiscrepancy(ntaMean, fcsMean)

  // Calculate average discrepancy for overall agreement
  const validDiscrepancies = [discD10, discD50, discD90, discMean].filter(d => d !== null) as number[]
  const avgDiscrepancy = validDiscrepancies.length > 0
    ? validDiscrepancies.reduce((sum, d) => sum + d, 0) / validDiscrepancies.length
    : null

  const metrics = [
    {
      parameter: "D10 (10th %ile)",
      fcs: fcsD10,
      nta: ntaD10,
      discrepancy: discD10,
      description: "Size below which 10% of particles fall"
    },
    {
      parameter: "D50 (Median)",
      fcs: fcsD50,
      nta: ntaD50,
      discrepancy: discD50,
      description: "Median particle size"
    },
    {
      parameter: "D90 (90th %ile)",
      fcs: fcsD90,
      nta: ntaD90,
      discrepancy: discD90,
      description: "Size below which 90% of particles fall"
    },
    {
      parameter: "Mean",
      fcs: fcsMean,
      nta: ntaMean,
      discrepancy: discMean,
      description: "Average particle size"
    },
    {
      parameter: "Std Dev",
      fcs: fcsStd,
      nta: ntaStd,
      discrepancy: null,
      description: "Standard deviation of distribution"
    }
  ]

  const overallStatus = getDiscrepancyStatus(avgDiscrepancy)
  const OverallIcon = overallStatus.icon

  return (
    <Card className={cn("card-3d", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-primary/10">
              <BarChart3 className="h-4 w-4 text-primary" />
            </div>
            <CardTitle className="text-base md:text-lg">Statistical Comparison</CardTitle>
          </div>
          {avgDiscrepancy !== null && (
            <Badge 
              variant="outline" 
              className={cn(
                "gap-1",
                overallStatus.color === "emerald" && "border-emerald-500 text-emerald-600 dark:text-emerald-400",
                overallStatus.color === "blue" && "border-blue-500 text-blue-600 dark:text-blue-400",
                overallStatus.color === "amber" && "border-amber-500 text-amber-600 dark:text-amber-400",
                overallStatus.color === "rose" && "border-rose-500 text-rose-600 dark:text-rose-400"
              )}
            >
              <OverallIcon className="h-3 w-3" />
              {overallStatus.label} Agreement
            </Badge>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Comparing size distribution metrics between FCS and NTA methods
          {avgDiscrepancy !== null && ` • ${avgDiscrepancy.toFixed(1)}% avg discrepancy`}
        </p>
      </CardHeader>
      <CardContent>
        <div className="rounded-lg border overflow-hidden overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-secondary/30">
                <TableHead className="font-semibold min-w-32">Parameter</TableHead>
                <TableHead className="font-semibold text-center min-w-24">
                  <div className="flex items-center justify-center gap-1">
                    <div className="w-2 h-2 rounded-full bg-blue-500" />
                    FCS (nm)
                  </div>
                </TableHead>
                <TableHead className="font-semibold text-center min-w-24">
                  <div className="flex items-center justify-center gap-1">
                    <div className="w-2 h-2 rounded-full bg-purple-500" />
                    NTA (nm)
                  </div>
                </TableHead>
                <TableHead className="font-semibold text-center min-w-24">Difference</TableHead>
                <TableHead className="font-semibold text-center min-w-28">Discrepancy</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {metrics.map((metric, index) => {
                const status = getDiscrepancyStatus(metric.discrepancy)
                const StatusIcon = status.icon
                const difference = metric.fcs && metric.nta ? (metric.nta - metric.fcs) : null

                return (
                  <TableRow 
                    key={metric.parameter} 
                    className={cn(
                      "hover:bg-secondary/20 transition-colors",
                      index % 2 === 0 && "bg-secondary/5"
                    )}
                  >
                    <TableCell className="font-medium">
                      <div>
                        <p>{metric.parameter}</p>
                        <p className="text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
                          {metric.description}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell className="text-center font-mono">
                      {metric.fcs ? metric.fcs.toFixed(1) : "N/A"}
                    </TableCell>
                    <TableCell className="text-center font-mono">
                      {metric.nta ? metric.nta.toFixed(1) : "N/A"}
                    </TableCell>
                    <TableCell className="text-center font-mono">
                      {difference !== null ? (
                        <span className={cn(
                          difference > 0 ? "text-purple-600 dark:text-purple-400" : "text-blue-600 dark:text-blue-400"
                        )}>
                          {difference > 0 ? "+" : ""}{difference.toFixed(1)}
                        </span>
                      ) : (
                        "N/A"
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      {metric.discrepancy !== null ? (
                        <div className="flex items-center justify-center gap-1.5">
                          <Badge 
                            variant="outline"
                            className={cn(
                              "gap-1 font-mono",
                              status.color === "emerald" && "border-emerald-500 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10",
                              status.color === "blue" && "border-blue-500 text-blue-600 dark:text-blue-400 bg-blue-500/10",
                              status.color === "amber" && "border-amber-500 text-amber-600 dark:text-amber-400 bg-amber-500/10",
                              status.color === "rose" && "border-rose-500 text-rose-600 dark:text-rose-400 bg-rose-500/10"
                            )}
                          >
                            <StatusIcon className="h-3 w-3" />
                            {metric.discrepancy.toFixed(1)}%
                          </Badge>
                        </div>
                      ) : (
                        <Badge variant="secondary" className="gap-1">
                          <Minus className="h-3 w-3" />
                          N/A
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>

        {/* Legend */}
        <div className="mt-4 p-3 rounded-lg bg-muted/50 text-xs space-y-2">
          <p className="font-medium">Discrepancy Interpretation:</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-emerald-500" />
              <span>&lt;10% Excellent</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-blue-500" />
              <span>10-20% Good</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-amber-500" />
              <span>20-30% Fair</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-rose-500" />
              <span>&gt;30% Poor</span>
            </div>
          </div>
          <p className="text-muted-foreground pt-1">
            Discrepancy = |NTA - FCS| / ((NTA + FCS) / 2) × 100%
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
