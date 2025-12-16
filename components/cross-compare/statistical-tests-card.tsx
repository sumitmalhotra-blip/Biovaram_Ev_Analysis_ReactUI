"use client"

import { useMemo, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table"
import { cn } from "@/lib/utils"
import { 
  TestTube, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle,
  Info,
  ChevronDown,
  ChevronUp,
  BarChart3
} from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

interface StatisticalTestsCardProps {
  fcsData?: number[] // Size distribution data from FCS
  ntaData?: number[] // Size distribution data from NTA
  className?: string
}

interface TestResult {
  name: string
  description: string
  statistic: number | null
  pValue: number | null
  conclusion: "same" | "different" | "insufficient"
  details?: string
}

// Simple implementation of Kolmogorov-Smirnov test
function kolmogorovSmirnovTest(sample1: number[], sample2: number[]): { statistic: number; pValue: number } {
  if (sample1.length < 2 || sample2.length < 2) {
    return { statistic: 0, pValue: 1 }
  }

  // Sort both samples
  const s1 = [...sample1].sort((a, b) => a - b)
  const s2 = [...sample2].sort((a, b) => a - b)

  const n1 = s1.length
  const n2 = s2.length

  // Create combined sorted array of all unique values
  const allValues = [...new Set([...s1, ...s2])].sort((a, b) => a - b)

  // Calculate empirical CDFs
  let maxDiff = 0
  for (const value of allValues) {
    // CDF for sample 1: proportion of values <= value
    const cdf1 = s1.filter(v => v <= value).length / n1
    // CDF for sample 2
    const cdf2 = s2.filter(v => v <= value).length / n2
    
    const diff = Math.abs(cdf1 - cdf2)
    if (diff > maxDiff) {
      maxDiff = diff
    }
  }

  // Approximate p-value using asymptotic formula
  // For large samples, K-S statistic * sqrt(n) follows Kolmogorov distribution
  const n = (n1 * n2) / (n1 + n2)
  const lambda = (Math.sqrt(n) + 0.12 + 0.11 / Math.sqrt(n)) * maxDiff

  // Approximate p-value using series expansion
  let pValue = 0
  for (let k = 1; k <= 100; k++) {
    pValue += 2 * Math.pow(-1, k - 1) * Math.exp(-2 * k * k * lambda * lambda)
  }
  pValue = Math.max(0, Math.min(1, pValue))

  return { statistic: maxDiff, pValue }
}

// Simple implementation of Mann-Whitney U test
function mannWhitneyUTest(sample1: number[], sample2: number[]): { statistic: number; pValue: number } {
  if (sample1.length < 2 || sample2.length < 2) {
    return { statistic: 0, pValue: 1 }
  }

  const n1 = sample1.length
  const n2 = sample2.length

  // Combine and rank
  interface RankedValue {
    value: number
    group: 1 | 2
  }
  
  const combined: RankedValue[] = [
    ...sample1.map(v => ({ value: v, group: 1 as const })),
    ...sample2.map(v => ({ value: v, group: 2 as const }))
  ]
  
  // Sort by value
  combined.sort((a, b) => a.value - b.value)

  // Assign ranks (handling ties by averaging)
  const ranks: number[] = []
  let i = 0
  while (i < combined.length) {
    let j = i
    while (j < combined.length && combined[j].value === combined[i].value) {
      j++
    }
    // Average rank for tied values
    const avgRank = (i + 1 + j) / 2
    for (let k = i; k < j; k++) {
      ranks[k] = avgRank
    }
    i = j
  }

  // Sum ranks for group 1
  let R1 = 0
  for (let k = 0; k < combined.length; k++) {
    if (combined[k].group === 1) {
      R1 += ranks[k]
    }
  }

  // Calculate U statistics
  const U1 = R1 - (n1 * (n1 + 1)) / 2
  const U2 = n1 * n2 - U1
  const U = Math.min(U1, U2)

  // For large samples, U is approximately normal
  const meanU = (n1 * n2) / 2
  const stdU = Math.sqrt((n1 * n2 * (n1 + n2 + 1)) / 12)
  
  // Z-score with continuity correction
  const z = (U - meanU + 0.5) / stdU

  // Two-tailed p-value using normal approximation
  const pValue = 2 * (1 - normalCDF(Math.abs(z)))

  return { statistic: U, pValue: Math.max(0, Math.min(1, pValue)) }
}

// Standard normal CDF approximation
function normalCDF(x: number): number {
  const a1 = 0.254829592
  const a2 = -0.284496736
  const a3 = 1.421413741
  const a4 = -1.453152027
  const a5 = 1.061405429
  const p = 0.3275911

  const sign = x < 0 ? -1 : 1
  x = Math.abs(x) / Math.sqrt(2)

  const t = 1.0 / (1.0 + p * x)
  const y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x)

  return 0.5 * (1.0 + sign * y)
}

// Effect size (Cohen's d)
function cohensD(sample1: number[], sample2: number[]): number {
  const mean1 = sample1.reduce((a, b) => a + b, 0) / sample1.length
  const mean2 = sample2.reduce((a, b) => a + b, 0) / sample2.length
  
  const var1 = sample1.reduce((a, b) => a + Math.pow(b - mean1, 2), 0) / (sample1.length - 1)
  const var2 = sample2.reduce((a, b) => a + Math.pow(b - mean2, 2), 0) / (sample2.length - 1)
  
  // Pooled standard deviation
  const pooledStd = Math.sqrt(
    ((sample1.length - 1) * var1 + (sample2.length - 1) * var2) / 
    (sample1.length + sample2.length - 2)
  )
  
  if (pooledStd === 0) return 0
  return (mean1 - mean2) / pooledStd
}

export function StatisticalTestsCard({ fcsData, ntaData, className }: StatisticalTestsCardProps) {
  const [isOpen, setIsOpen] = useState(true)
  const [alpha, setAlpha] = useState(0.05) // Significance level
  const [showDetails, setShowDetails] = useState(false)

  const testResults = useMemo((): TestResult[] => {
    if (!fcsData || !ntaData || fcsData.length < 10 || ntaData.length < 10) {
      return [
        {
          name: "Kolmogorov-Smirnov Test",
          description: "Tests if two samples come from the same distribution",
          statistic: null,
          pValue: null,
          conclusion: "insufficient",
          details: "Insufficient data. Need at least 10 samples from each method."
        },
        {
          name: "Mann-Whitney U Test",
          description: "Non-parametric test comparing two independent samples",
          statistic: null,
          pValue: null,
          conclusion: "insufficient",
          details: "Insufficient data. Need at least 10 samples from each method."
        }
      ]
    }

    // Run K-S test
    const ksResult = kolmogorovSmirnovTest(fcsData, ntaData)
    const ksConclusion = ksResult.pValue < alpha ? "different" : "same"

    // Run Mann-Whitney U test
    const mwResult = mannWhitneyUTest(fcsData, ntaData)
    const mwConclusion = mwResult.pValue < alpha ? "different" : "same"

    // Calculate effect size
    const effectSize = cohensD(fcsData, ntaData)
    const effectInterpretation = Math.abs(effectSize) < 0.2 ? "negligible" :
                                 Math.abs(effectSize) < 0.5 ? "small" :
                                 Math.abs(effectSize) < 0.8 ? "medium" : "large"

    return [
      {
        name: "Kolmogorov-Smirnov Test",
        description: "Tests if two samples come from the same distribution",
        statistic: ksResult.statistic,
        pValue: ksResult.pValue,
        conclusion: ksConclusion,
        details: `D-statistic = ${ksResult.statistic.toFixed(4)}. ` +
                 `${ksConclusion === "same" 
                   ? "Cannot reject null hypothesis: distributions may be identical." 
                   : "Reject null hypothesis: distributions are significantly different."}`
      },
      {
        name: "Mann-Whitney U Test",
        description: "Non-parametric test for difference in medians",
        statistic: mwResult.statistic,
        pValue: mwResult.pValue,
        conclusion: mwConclusion,
        details: `U-statistic = ${mwResult.statistic.toFixed(0)}. ` +
                 `${mwConclusion === "same"
                   ? "Cannot reject null hypothesis: medians may be equal."
                   : "Reject null hypothesis: medians are significantly different."}`
      },
      {
        name: "Cohen's d Effect Size",
        description: "Standardized measure of effect size between groups",
        statistic: effectSize,
        pValue: null,
        conclusion: "same", // Effect size doesn't have same/different conclusion
        details: `Effect size is ${effectInterpretation} (d = ${effectSize.toFixed(3)}). ` +
                 `Interpretation: |d| < 0.2 = negligible, 0.2-0.5 = small, 0.5-0.8 = medium, > 0.8 = large.`
      }
    ]
  }, [fcsData, ntaData, alpha])

  const getStatusIcon = (conclusion: TestResult["conclusion"]) => {
    switch (conclusion) {
      case "same":
        return <CheckCircle2 className="h-4 w-4 text-emerald-500" />
      case "different":
        return <XCircle className="h-4 w-4 text-rose-500" />
      case "insufficient":
        return <AlertTriangle className="h-4 w-4 text-amber-500" />
    }
  }

  const getStatusBadge = (conclusion: TestResult["conclusion"]) => {
    switch (conclusion) {
      case "same":
        return (
          <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 border-emerald-500/30">
            No Significant Difference
          </Badge>
        )
      case "different":
        return (
          <Badge variant="outline" className="bg-rose-500/10 text-rose-600 border-rose-500/30">
            Significant Difference
          </Badge>
        )
      case "insufficient":
        return (
          <Badge variant="outline" className="bg-amber-500/10 text-amber-600 border-amber-500/30">
            Insufficient Data
          </Badge>
        )
    }
  }

  const hasData = fcsData && ntaData && fcsData.length > 0 && ntaData.length > 0

  return (
    <Card className={cn("card-3d", className)}>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CardHeader className="pb-2">
          <CollapsibleTrigger asChild>
            <div className="flex items-center justify-between cursor-pointer group">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-primary/10">
                  <TestTube className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-base md:text-lg">Statistical Tests</CardTitle>
                  <CardDescription className="text-xs">
                    Formal hypothesis tests for distribution comparison
                  </CardDescription>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {hasData && testResults[0].conclusion !== "insufficient" && (
                  <Badge variant="secondary" className="text-xs">
                    α = {alpha}
                  </Badge>
                )}
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  {isOpen ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
          </CollapsibleTrigger>
        </CardHeader>

        <CollapsibleContent>
          <CardContent className="space-y-4">
            {!hasData ? (
              <div className="text-center p-6 text-muted-foreground">
                <BarChart3 className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>Select both FCS and NTA samples to run statistical tests</p>
              </div>
            ) : (
              <>
                {/* Settings */}
                <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/30">
                  <div className="flex items-center gap-2">
                    <Label className="text-sm">Significance Level (α)</Label>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-3 w-3 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="max-w-xs text-xs">
                          Probability threshold for rejecting the null hypothesis. 
                          Common values: 0.05 (5%), 0.01 (1%)
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant={alpha === 0.05 ? "default" : "outline"}
                      className="h-7 text-xs"
                      onClick={() => setAlpha(0.05)}
                    >
                      0.05
                    </Button>
                    <Button
                      size="sm"
                      variant={alpha === 0.01 ? "default" : "outline"}
                      className="h-7 text-xs"
                      onClick={() => setAlpha(0.01)}
                    >
                      0.01
                    </Button>
                  </div>
                </div>

                {/* Sample info */}
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span>FCS: n = {fcsData.length.toLocaleString()}</span>
                  <span>NTA: n = {ntaData.length.toLocaleString()}</span>
                </div>

                {/* Test Results Table */}
                <div className="rounded-lg border overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-secondary/30">
                        <TableHead className="font-semibold">Test</TableHead>
                        <TableHead className="font-semibold text-center">Statistic</TableHead>
                        <TableHead className="font-semibold text-center">p-value</TableHead>
                        <TableHead className="font-semibold text-center">Result</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {testResults.map((test, index) => (
                        <TableRow key={index}>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              {getStatusIcon(test.conclusion)}
                              <div>
                                <div className="font-medium text-sm">{test.name}</div>
                                <div className="text-xs text-muted-foreground">
                                  {test.description}
                                </div>
                              </div>
                            </div>
                          </TableCell>
                          <TableCell className="text-center font-mono text-sm">
                            {test.statistic !== null 
                              ? test.statistic.toFixed(4)
                              : "—"
                            }
                          </TableCell>
                          <TableCell className="text-center">
                            {test.pValue !== null ? (
                              <span className={cn(
                                "font-mono text-sm",
                                test.pValue < alpha && "text-rose-600 font-semibold"
                              )}>
                                {test.pValue < 0.001 
                                  ? "< 0.001"
                                  : test.pValue.toFixed(4)
                                }
                              </span>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </TableCell>
                          <TableCell className="text-center">
                            {test.name !== "Cohen's d Effect Size" 
                              ? getStatusBadge(test.conclusion)
                              : (
                                <Badge variant="outline" className="text-xs">
                                  {test.statistic !== null && (
                                    Math.abs(test.statistic) < 0.2 ? "Negligible" :
                                    Math.abs(test.statistic) < 0.5 ? "Small" :
                                    Math.abs(test.statistic) < 0.8 ? "Medium" : "Large"
                                  )}
                                </Badge>
                              )
                            }
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* Details toggle */}
                <div className="flex items-center gap-2">
                  <Switch
                    id="show-details"
                    checked={showDetails}
                    onCheckedChange={setShowDetails}
                  />
                  <Label htmlFor="show-details" className="text-sm cursor-pointer">
                    Show interpretation details
                  </Label>
                </div>

                {/* Interpretation details */}
                {showDetails && (
                  <div className="space-y-3 pt-2">
                    {testResults.map((test, index) => (
                      <div key={index} className="p-3 rounded-lg bg-secondary/20 text-sm">
                        <div className="font-medium mb-1">{test.name}</div>
                        <p className="text-muted-foreground">{test.details}</p>
                      </div>
                    ))}
                    
                    <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-sm">
                      <div className="flex items-start gap-2">
                        <Info className="h-4 w-4 text-blue-500 mt-0.5" />
                        <div>
                          <div className="font-medium text-blue-600 mb-1">Interpretation Guide</div>
                          <p className="text-muted-foreground text-xs">
                            <strong>Kolmogorov-Smirnov:</strong> Tests overall distribution shape. Sensitive to any difference in distributions.
                            <br />
                            <strong>Mann-Whitney U:</strong> Tests median difference. More robust to outliers than t-test.
                            <br />
                            <strong>Cohen&apos;s d:</strong> Practical significance. Even statistically significant differences may be practically negligible if d is small.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
