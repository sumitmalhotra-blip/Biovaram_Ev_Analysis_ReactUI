"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle, Download, Info, TrendingUp, AlertTriangle } from "lucide-react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

export interface AnomalyDetectionResult {
  method: "Z-Score" | "IQR" | "Both"
  total_anomalies: number
  anomaly_percentage: number
  zscore_anomalies?: number
  iqr_anomalies?: number
  combined_anomalies?: number
  zscore_threshold?: number
  iqr_factor?: number
  anomalous_indices: number[]
  fsc_outliers?: number[]
  ssc_outliers?: number[]
}

interface AnomalySummaryCardProps {
  anomalyData: AnomalyDetectionResult | null
  totalEvents: number
  onExportAnomalies?: () => void
  onViewDetails?: () => void
  className?: string
}

export function AnomalySummaryCard({
  anomalyData,
  totalEvents,
  onExportAnomalies,
  onViewDetails,
  className = "",
}: AnomalySummaryCardProps) {
  if (!anomalyData) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <AlertCircle className="h-4 w-4" />
            Anomaly Detection
          </CardTitle>
          <CardDescription>No anomaly detection performed</CardDescription>
        </CardHeader>
        <CardContent>
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              Enable anomaly detection in analysis settings to identify outlier events.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  const { method, total_anomalies, anomaly_percentage, zscore_threshold, iqr_factor } = anomalyData

  // Determine severity level
  const getSeverityColor = (percentage: number) => {
    if (percentage < 1) return "text-green-500"
    if (percentage < 5) return "text-yellow-500"
    if (percentage < 10) return "text-orange-500"
    return "text-red-500"
  }

  const getSeverityBadge = (percentage: number) => {
    if (percentage < 1) return { variant: "outline" as const, label: "Low", color: "border-green-500 text-green-500" }
    if (percentage < 5)
      return { variant: "outline" as const, label: "Moderate", color: "border-yellow-500 text-yellow-500" }
    if (percentage < 10)
      return { variant: "outline" as const, label: "High", color: "border-orange-500 text-orange-500" }
    return { variant: "destructive" as const, label: "Critical", color: "" }
  }

  const severityBadge = getSeverityBadge(anomaly_percentage)

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="h-4 w-4 text-yellow-500" />
              Anomaly Detection Results
            </CardTitle>
            <CardDescription>
              Method: <span className="font-semibold text-foreground">{method}</span>
            </CardDescription>
          </div>
          <Badge variant={severityBadge.variant} className={severityBadge.color}>
            {severityBadge.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Main Stats */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Total Anomalies</p>
            <p className={`text-2xl font-bold ${getSeverityColor(anomaly_percentage)}`}>
              {total_anomalies.toLocaleString()}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Percentage</p>
            <div className="flex items-baseline gap-2">
              <p className={`text-2xl font-bold ${getSeverityColor(anomaly_percentage)}`}>
                {anomaly_percentage.toFixed(2)}%
              </p>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-3 w-3 text-muted-foreground" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-xs">
                      {total_anomalies} out of {totalEvents.toLocaleString()} total events
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </div>
        </div>

        {/* Method-Specific Details */}
        <div className="space-y-2 rounded-lg border bg-muted/30 p-3">
          <p className="text-xs font-semibold text-muted-foreground">Detection Parameters</p>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {method === "Z-Score" || method === "Both" ? (
              <>
                <div>
                  <span className="text-muted-foreground">Z-Score Threshold:</span>
                </div>
                <div className="text-right font-mono">{zscore_threshold?.toFixed(1) || "3.0"}</div>
              </>
            ) : null}
            {method === "IQR" || method === "Both" ? (
              <>
                <div>
                  <span className="text-muted-foreground">IQR Factor:</span>
                </div>
                <div className="text-right font-mono">{iqr_factor?.toFixed(1) || "1.5"}</div>
              </>
            ) : null}
          </div>
        </div>

        {/* Method Breakdown (if using "Both") */}
        {method === "Both" && (anomalyData.zscore_anomalies || anomalyData.iqr_anomalies) && (
          <div className="space-y-2 rounded-lg border p-3">
            <p className="text-xs font-semibold text-muted-foreground">Method Breakdown</p>
            <div className="space-y-1.5 text-sm">
              {anomalyData.zscore_anomalies !== undefined && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Z-Score Method:</span>
                  <span className="font-semibold">{anomalyData.zscore_anomalies.toLocaleString()}</span>
                </div>
              )}
              {anomalyData.iqr_anomalies !== undefined && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">IQR Method:</span>
                  <span className="font-semibold">{anomalyData.iqr_anomalies.toLocaleString()}</span>
                </div>
              )}
              {anomalyData.combined_anomalies !== undefined && (
                <div className="flex justify-between border-t pt-1.5">
                  <span className="text-muted-foreground">Combined (Union):</span>
                  <span className="font-semibold">{anomalyData.combined_anomalies.toLocaleString()}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Warning for High Anomaly Rate */}
        {anomaly_percentage > 10 && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="text-xs">
              High anomaly rate (&gt;10%) detected. This may indicate data quality issues or need for parameter
              adjustment.
            </AlertDescription>
          </Alert>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2">
          {onViewDetails && (
            <Button variant="outline" size="sm" className="flex-1" onClick={onViewDetails}>
              <TrendingUp className="mr-2 h-3 w-3" />
              View Details
            </Button>
          )}
          {onExportAnomalies && total_anomalies > 0 && (
            <Button variant="outline" size="sm" className="flex-1" onClick={onExportAnomalies}>
              <Download className="mr-2 h-3 w-3" />
              Export List
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
