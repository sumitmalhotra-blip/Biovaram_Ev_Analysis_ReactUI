"use client"

/**
 * Best Practices Panel Component
 * TASK-016: Display best practices comparison results
 * 
 * Shows warnings, recommendations, and compliance score
 * based on comparison against established EV analysis best practices.
 */

import { useState, useMemo } from "react"
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  Info,
  ChevronDown,
  ChevronUp,
  BookOpen,
  TrendingUp,
  Shield,
  Lightbulb,
} from "lucide-react"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  type BestPracticesCheckResult,
  type BestPracticeViolation,
  type RuleCategory,
  checkBestPractices,
  type ExperimentData,
} from "@/lib/best-practices"

// Category display info
const CATEGORY_INFO: Record<RuleCategory, { label: string; icon: typeof AlertTriangle }> = {
  "sample-prep": { label: "Sample Preparation", icon: BookOpen },
  "antibody": { label: "Antibody Staining", icon: Shield },
  "instrument": { label: "Instrument Settings", icon: TrendingUp },
  "analysis": { label: "Size Analysis", icon: TrendingUp },
  "quality": { label: "Quality Control", icon: Shield },
}

interface ViolationCardProps {
  violation: BestPracticeViolation
}

function ViolationCard({ violation }: ViolationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const getSeverityStyles = () => {
    switch (violation.severity) {
      case "error":
        return {
          bg: "bg-red-50 dark:bg-red-950/20",
          border: "border-red-200 dark:border-red-800",
          icon: <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />,
          badge: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
        }
      case "warning":
        return {
          bg: "bg-amber-50 dark:bg-amber-950/20",
          border: "border-amber-200 dark:border-amber-800",
          icon: <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />,
          badge: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
        }
      case "info":
      default:
        return {
          bg: "bg-blue-50 dark:bg-blue-950/20",
          border: "border-blue-200 dark:border-blue-800",
          icon: <Info className="h-4 w-4 text-blue-600 dark:text-blue-400" />,
          badge: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
        }
    }
  }

  const styles = getSeverityStyles()
  const CategoryIcon = CATEGORY_INFO[violation.rule.category]?.icon || AlertTriangle

  return (
    <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
      <div className={`rounded-lg border ${styles.border} ${styles.bg} overflow-hidden`}>
        <CollapsibleTrigger asChild>
          <button className="w-full p-3 flex items-start gap-3 hover:bg-black/5 dark:hover:bg-white/5 transition-colors text-left">
            <div className="mt-0.5">{styles.icon}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-medium text-sm">{violation.rule.name}</span>
                <Badge variant="outline" className={`text-xs ${styles.badge}`}>
                  {violation.severity}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-1 truncate">
                {violation.message}
              </p>
            </div>
            {isExpanded ? (
              <ChevronUp className="h-4 w-4 text-muted-foreground shrink-0" />
            ) : (
              <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
            )}
          </button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="px-3 pb-3 space-y-2 border-t border-inherit pt-2">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <CategoryIcon className="h-3 w-3" />
              <span>{CATEGORY_INFO[violation.rule.category]?.label}</span>
            </div>
            <div className="bg-background/50 rounded p-2">
              <div className="flex items-start gap-2">
                <Lightbulb className="h-3 w-3 text-amber-500 mt-0.5 shrink-0" />
                <p className="text-xs">{violation.recommendation}</p>
              </div>
            </div>
            {violation.rule.reference && (
              <p className="text-xs text-muted-foreground italic">
                Ref: {violation.rule.reference}
              </p>
            )}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}

interface BestPracticesPanelProps {
  data?: ExperimentData
  result?: BestPracticesCheckResult
  compact?: boolean
}

export function BestPracticesPanel({ data, result: providedResult, compact = false }: BestPracticesPanelProps) {
  const [showAll, setShowAll] = useState(false)

  // Calculate result from data if not provided
  const result = useMemo(() => {
    if (providedResult) return providedResult
    if (data) return checkBestPractices(data)
    return null
  }, [data, providedResult])

  if (!result) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        <Info className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No data available for best practices check</p>
        <p className="text-xs mt-1">Upload and analyze FCS or NTA data to see recommendations</p>
      </div>
    )
  }

  const getScoreColor = () => {
    if (result.score >= 80) return "text-green-600 dark:text-green-400"
    if (result.score >= 60) return "text-amber-600 dark:text-amber-400"
    return "text-red-600 dark:text-red-400"
  }

  const getProgressColor = () => {
    if (result.score >= 80) return "bg-green-500"
    if (result.score >= 60) return "bg-amber-500"
    return "bg-red-500"
  }

  // Sort violations by severity (errors first, then warnings, then info)
  const sortedViolations = [...result.violations].sort((a, b) => {
    const severityOrder = { error: 0, warning: 1, info: 2 }
    return severityOrder[a.severity] - severityOrder[b.severity]
  })

  const displayViolations = showAll ? sortedViolations : sortedViolations.slice(0, 3)
  const hasMore = sortedViolations.length > 3

  if (compact) {
    // Compact view for sidebar
    return (
      <TooltipProvider>
        <div className="space-y-3">
          {/* Score Summary */}
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium">Compliance Score</span>
                <span className={`text-sm font-bold ${getScoreColor()}`}>{result.score}%</span>
              </div>
              <Progress value={result.score} className="h-2" />
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-3 gap-2 text-center">
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="bg-green-50 dark:bg-green-950/30 rounded p-1.5">
                  <CheckCircle className="h-3 w-3 mx-auto text-green-600 dark:text-green-400" />
                  <span className="text-xs font-medium block">{result.passed}</span>
                </div>
              </TooltipTrigger>
              <TooltipContent>Passed checks</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="bg-amber-50 dark:bg-amber-950/30 rounded p-1.5">
                  <AlertTriangle className="h-3 w-3 mx-auto text-amber-600 dark:text-amber-400" />
                  <span className="text-xs font-medium block">{result.warnings}</span>
                </div>
              </TooltipTrigger>
              <TooltipContent>Warnings</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="bg-red-50 dark:bg-red-950/30 rounded p-1.5">
                  <XCircle className="h-3 w-3 mx-auto text-red-600 dark:text-red-400" />
                  <span className="text-xs font-medium block">{result.errors}</span>
                </div>
              </TooltipTrigger>
              <TooltipContent>Errors</TooltipContent>
            </Tooltip>
          </div>

          {/* Top Issues */}
          {sortedViolations.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-xs font-medium text-muted-foreground">Top Issues</span>
              {sortedViolations.slice(0, 2).map((v, i) => (
                <div
                  key={i}
                  className={`text-xs p-2 rounded ${
                    v.severity === "error"
                      ? "bg-red-50 dark:bg-red-950/20 text-red-700 dark:text-red-300"
                      : v.severity === "warning"
                      ? "bg-amber-50 dark:bg-amber-950/20 text-amber-700 dark:text-amber-300"
                      : "bg-blue-50 dark:bg-blue-950/20 text-blue-700 dark:text-blue-300"
                  }`}
                >
                  {v.rule.name}
                </div>
              ))}
              {sortedViolations.length > 2 && (
                <p className="text-xs text-muted-foreground text-center">
                  +{sortedViolations.length - 2} more issues
                </p>
              )}
            </div>
          )}
        </div>
      </TooltipProvider>
    )
  }

  // Full view
  return (
    <div className="space-y-4">
      {/* Header with Score */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Best Practices Check
          </h3>
          <p className="text-sm text-muted-foreground mt-0.5">
            Based on ISEV 2023 guidelines
          </p>
        </div>
        <div className="text-right">
          <div className={`text-3xl font-bold ${getScoreColor()}`}>{result.score}%</div>
          <p className="text-xs text-muted-foreground">Compliance Score</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-1">
        <Progress value={result.score} className="h-3" />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>{result.passed} passed</span>
          <span>{result.warnings} warnings</span>
          <span>{result.errors} errors</span>
        </div>
      </div>

      <Separator />

      {/* Violations List */}
      {sortedViolations.length === 0 ? (
        <div className="py-8 text-center">
          <CheckCircle className="h-12 w-12 mx-auto text-green-500 mb-3" />
          <p className="font-medium text-green-700 dark:text-green-300">
            All checks passed!
          </p>
          <p className="text-sm text-muted-foreground mt-1">
            Your experiment follows best practices
          </p>
        </div>
      ) : (
        <ScrollArea className="h-[300px]">
          <div className="space-y-2 pr-4">
            {displayViolations.map((violation, index) => (
              <ViolationCard key={index} violation={violation} />
            ))}
          </div>
          {hasMore && !showAll && (
            <Button
              variant="ghost"
              className="w-full mt-2"
              onClick={() => setShowAll(true)}
            >
              Show {sortedViolations.length - 3} more issues
              <ChevronDown className="h-4 w-4 ml-1" />
            </Button>
          )}
          {showAll && hasMore && (
            <Button
              variant="ghost"
              className="w-full mt-2"
              onClick={() => setShowAll(false)}
            >
              Show less
              <ChevronUp className="h-4 w-4 ml-1" />
            </Button>
          )}
        </ScrollArea>
      )}

      {/* Recommendations Summary */}
      {result.recommendations.length > 0 && (
        <>
          <Separator />
          <div>
            <h4 className="font-medium text-sm flex items-center gap-2 mb-2">
              <Lightbulb className="h-4 w-4 text-amber-500" />
              Key Recommendations
            </h4>
            <ul className="space-y-1">
              {result.recommendations.slice(0, 3).map((rec, i) => (
                <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                  <span className="text-amber-500 mt-0.5">•</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  )
}

export default BestPracticesPanel
