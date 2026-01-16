"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { Skeleton } from "@/components/ui/skeleton"
import { 
  Bell, 
  AlertTriangle, 
  AlertCircle, 
  Info, 
  XCircle,
  Check,
  CheckCheck,
  RefreshCw,
  Filter,
  Trash2,
  Clock,
  ExternalLink,
  ChevronRight,
  Archive
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useApi } from "@/hooks/use-api"
import { formatDistanceToNow, format } from "date-fns"

export interface Alert {
  id: number
  sample_id: number | null
  user_id: number | null
  alert_type: string
  severity: string
  title: string
  message: string
  source: string
  sample_name: string | null
  metadata: Record<string, any> | null
  is_acknowledged: boolean
  acknowledged_by: number | null
  acknowledged_at: string | null
  acknowledgment_notes: string | null
  created_at: string
  updated_at: string
}

export interface AlertCounts {
  total: number
  unacknowledged: number
  acknowledged: number
  by_severity: {
    critical: number
    error: number
    warning: number
    info: number
  }
}

interface AlertPanelProps {
  userId?: number
  compact?: boolean
  maxItems?: number
  showFilters?: boolean
  onAlertClick?: (alert: Alert) => void
  className?: string
}

const severityConfig = {
  critical: {
    icon: XCircle,
    color: "text-red-500",
    bgColor: "bg-red-500/10",
    borderColor: "border-red-500/30",
    badgeVariant: "destructive" as const,
    label: "Critical",
  },
  error: {
    icon: AlertCircle,
    color: "text-orange-500",
    bgColor: "bg-orange-500/10",
    borderColor: "border-orange-500/30",
    badgeVariant: "destructive" as const,
    label: "Error",
  },
  warning: {
    icon: AlertTriangle,
    color: "text-yellow-500",
    bgColor: "bg-yellow-500/10",
    borderColor: "border-yellow-500/30",
    badgeVariant: "secondary" as const,
    label: "Warning",
  },
  info: {
    icon: Info,
    color: "text-blue-500",
    bgColor: "bg-blue-500/10",
    borderColor: "border-blue-500/30",
    badgeVariant: "outline" as const,
    label: "Info",
  },
}

const alertTypeLabels: Record<string, string> = {
  anomaly_detected: "Anomaly Detected",
  quality_warning: "Quality Warning",
  population_shift: "Population Shift",
  size_distribution_unusual: "Unusual Size Distribution",
  high_debris: "High Debris",
  low_event_count: "Low Event Count",
  processing_error: "Processing Error",
  calibration_needed: "Calibration Needed",
}

export function AlertPanel({
  userId,
  compact = false,
  maxItems = 10,
  showFilters = true,
  onAlertClick,
  className,
}: AlertPanelProps) {
  const { getAlerts, getAlertCounts, acknowledgeAlert, acknowledgeMultipleAlerts, deleteAlert } = useApi()
  
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [counts, setCounts] = useState<AlertCounts | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedAlerts, setSelectedAlerts] = useState<Set<number>>(new Set())
  const [acknowledgeDialogOpen, setAcknowledgeDialogOpen] = useState(false)
  const [acknowledgeNotes, setAcknowledgeNotes] = useState("")
  const [acknowledging, setAcknowledging] = useState(false)
  
  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>("all")
  const [statusFilter, setStatusFilter] = useState<string>("unacknowledged")
  const [sourceFilter, setSourceFilter] = useState<string>("all")

  // Fetch alerts
  const fetchAlerts = useCallback(async () => {
    setLoading(true)
    try {
      const options: any = {
        limit: maxItems,
        orderBy: "created_at",
        orderDesc: true,
      }
      
      if (userId) options.userId = userId
      if (severityFilter !== "all") options.severity = severityFilter
      if (statusFilter === "unacknowledged") options.isAcknowledged = false
      else if (statusFilter === "acknowledged") options.isAcknowledged = true
      if (sourceFilter !== "all") options.source = sourceFilter
      
      const [alertsResult, countsResult] = await Promise.all([
        getAlerts(options),
        getAlertCounts(userId),
      ])
      
      if (alertsResult) {
        setAlerts(alertsResult.alerts)
      }
      if (countsResult) {
        setCounts(countsResult)
      }
    } catch (error) {
      console.error("Failed to fetch alerts:", error)
    } finally {
      setLoading(false)
    }
  }, [getAlerts, getAlertCounts, userId, maxItems, severityFilter, statusFilter, sourceFilter])

  useEffect(() => {
    fetchAlerts()
  }, [fetchAlerts])

  // Handle selection
  const toggleSelection = (alertId: number) => {
    setSelectedAlerts(prev => {
      const next = new Set(prev)
      if (next.has(alertId)) {
        next.delete(alertId)
      } else {
        next.add(alertId)
      }
      return next
    })
  }

  const selectAll = () => {
    const unacknowledgedIds = alerts.filter(a => !a.is_acknowledged).map(a => a.id)
    setSelectedAlerts(new Set(unacknowledgedIds))
  }

  const clearSelection = () => {
    setSelectedAlerts(new Set())
  }

  // Handle acknowledge
  const handleAcknowledge = async () => {
    if (selectedAlerts.size === 0) return
    
    setAcknowledging(true)
    try {
      if (selectedAlerts.size === 1) {
        const alertId = Array.from(selectedAlerts)[0]
        await acknowledgeAlert(alertId, { notes: acknowledgeNotes || undefined })
      } else {
        await acknowledgeMultipleAlerts(
          Array.from(selectedAlerts),
          { notes: acknowledgeNotes || undefined }
        )
      }
      
      setSelectedAlerts(new Set())
      setAcknowledgeNotes("")
      setAcknowledgeDialogOpen(false)
      await fetchAlerts()
    } catch (error) {
      console.error("Failed to acknowledge alerts:", error)
    } finally {
      setAcknowledging(false)
    }
  }

  // Handle delete
  const handleDelete = async (alertId: number) => {
    try {
      await deleteAlert(alertId)
      await fetchAlerts()
    } catch (error) {
      console.error("Failed to delete alert:", error)
    }
  }

  // Get severity config
  const getSeverity = (severity: string) => {
    return severityConfig[severity as keyof typeof severityConfig] || severityConfig.info
  }

  // Format timestamp
  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return formatDistanceToNow(date, { addSuffix: true })
    } catch {
      return timestamp
    }
  }

  const formatFullTimestamp = (timestamp: string) => {
    try {
      return format(new Date(timestamp), "PPpp")
    } catch {
      return timestamp
    }
  }

  if (compact) {
    // Compact mode for sidebar/header
    return (
      <div className={cn("relative", className)}>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" className="relative">
                <Bell className="h-5 w-5" />
                {counts && counts.unacknowledged > 0 && (
                  <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-red-500 text-[10px] font-bold text-white flex items-center justify-center">
                    {counts.unacknowledged > 99 ? "99+" : counts.unacknowledged}
                  </span>
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom" align="end" className="w-80 p-0">
              <div className="p-3 border-b">
                <h4 className="font-semibold">Alerts</h4>
                {counts && (
                  <p className="text-xs text-muted-foreground mt-1">
                    {counts.unacknowledged} unreviewed alerts
                  </p>
                )}
              </div>
              <ScrollArea className="h-[300px]">
                {loading ? (
                  <div className="p-3 space-y-2">
                    {[1, 2, 3].map(i => (
                      <Skeleton key={i} className="h-16 w-full" />
                    ))}
                  </div>
                ) : alerts.length === 0 ? (
                  <div className="p-6 text-center text-muted-foreground">
                    <Check className="h-8 w-8 mx-auto mb-2 text-green-500" />
                    <p className="text-sm">All caught up!</p>
                    <p className="text-xs">No pending alerts</p>
                  </div>
                ) : (
                  <div className="divide-y">
                    {alerts.slice(0, 5).map(alert => {
                      const severity = getSeverity(alert.severity)
                      const Icon = severity.icon
                      return (
                        <button
                          key={alert.id}
                          className={cn(
                            "w-full p-3 text-left hover:bg-accent/50 transition-colors",
                            !alert.is_acknowledged && severity.bgColor
                          )}
                          onClick={() => onAlertClick?.(alert)}
                        >
                          <div className="flex items-start gap-2">
                            <Icon className={cn("h-4 w-4 mt-0.5 shrink-0", severity.color)} />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium truncate">{alert.title}</p>
                              <p className="text-xs text-muted-foreground truncate">{alert.sample_name || alert.source}</p>
                              <p className="text-[10px] text-muted-foreground mt-1">
                                {formatTimestamp(alert.created_at)}
                              </p>
                            </div>
                          </div>
                        </button>
                      )
                    })}
                  </div>
                )}
              </ScrollArea>
              {alerts.length > 5 && (
                <div className="p-2 border-t bg-muted/30">
                  <Button variant="ghost" size="sm" className="w-full text-xs">
                    View all {counts?.unacknowledged || 0} alerts
                    <ChevronRight className="h-3 w-3 ml-1" />
                  </Button>
                </div>
              )}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    )
  }

  // Full panel mode
  return (
    <Card className={cn("glass-card", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">Alerts</CardTitle>
            {counts && counts.unacknowledged > 0 && (
              <Badge variant="destructive" className="ml-2">
                {counts.unacknowledged} new
              </Badge>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchAlerts}
            disabled={loading}
          >
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
          </Button>
        </div>
        {counts && (
          <div className="flex items-center gap-2 mt-2">
            {Object.entries(counts.by_severity).map(([severity, count]) => {
              if (count === 0) return null
              const config = getSeverity(severity)
              return (
                <Badge key={severity} variant={config.badgeVariant} className="text-xs">
                  {config.label}: {count}
                </Badge>
              )
            })}
          </div>
        )}
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Filters */}
        {showFilters && (
          <div className="flex flex-wrap items-center gap-2">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[140px] h-8 text-xs">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="unacknowledged">Unreviewed</SelectItem>
                <SelectItem value="acknowledged">Reviewed</SelectItem>
              </SelectContent>
            </Select>
            
            <Select value={severityFilter} onValueChange={setSeverityFilter}>
              <SelectTrigger className="w-[130px] h-8 text-xs">
                <SelectValue placeholder="Severity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Severity</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="error">Error</SelectItem>
                <SelectItem value="warning">Warning</SelectItem>
                <SelectItem value="info">Info</SelectItem>
              </SelectContent>
            </Select>
            
            <Select value={sourceFilter} onValueChange={setSourceFilter}>
              <SelectTrigger className="w-[140px] h-8 text-xs">
                <SelectValue placeholder="Source" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Sources</SelectItem>
                <SelectItem value="fcs_analysis">FCS Analysis</SelectItem>
                <SelectItem value="nta_analysis">NTA Analysis</SelectItem>
                <SelectItem value="qc_check">QC Check</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Bulk actions */}
        {selectedAlerts.size > 0 && (
          <div className="flex items-center gap-2 p-2 bg-muted/50 rounded-lg">
            <span className="text-sm text-muted-foreground">
              {selectedAlerts.size} selected
            </span>
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={() => setAcknowledgeDialogOpen(true)}
            >
              <CheckCheck className="h-3 w-3 mr-1" />
              Acknowledge
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs"
              onClick={clearSelection}
            >
              Clear
            </Button>
          </div>
        )}

        {/* Alert list */}
        <ScrollArea className="h-[400px]">
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map(i => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : alerts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <Check className="h-12 w-12 mb-3 text-green-500" />
              <p className="text-lg font-medium">All caught up!</p>
              <p className="text-sm">No alerts matching your filters</p>
            </div>
          ) : (
            <div className="space-y-2">
              {/* Select all */}
              {alerts.some(a => !a.is_acknowledged) && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs mb-2"
                  onClick={selectAll}
                >
                  <Checkbox
                    checked={selectedAlerts.size === alerts.filter(a => !a.is_acknowledged).length}
                    className="mr-2"
                  />
                  Select all unreviewed
                </Button>
              )}
              
              {alerts.map(alert => {
                const severity = getSeverity(alert.severity)
                const Icon = severity.icon
                const isSelected = selectedAlerts.has(alert.id)
                
                return (
                  <div
                    key={alert.id}
                    className={cn(
                      "p-3 rounded-lg border transition-all",
                      !alert.is_acknowledged && severity.bgColor,
                      !alert.is_acknowledged && severity.borderColor,
                      alert.is_acknowledged && "opacity-60",
                      isSelected && "ring-2 ring-primary"
                    )}
                  >
                    <div className="flex items-start gap-3">
                      {!alert.is_acknowledged && (
                        <Checkbox
                          checked={isSelected}
                          onCheckedChange={() => toggleSelection(alert.id)}
                          className="mt-1"
                        />
                      )}
                      
                      <Icon className={cn("h-5 w-5 mt-0.5 shrink-0", severity.color)} />
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <h4 className="font-medium text-sm">{alert.title}</h4>
                            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                              {alert.message}
                            </p>
                          </div>
                          <Badge variant={severity.badgeVariant} className="shrink-0 text-[10px]">
                            {severity.label}
                          </Badge>
                        </div>
                        
                        <div className="flex items-center gap-3 mt-2 text-[10px] text-muted-foreground">
                          {alert.sample_name && (
                            <span className="flex items-center gap-1">
                              <ExternalLink className="h-3 w-3" />
                              {alert.sample_name}
                            </span>
                          )}
                          <span className="flex items-center gap-1">
                            {alertTypeLabels[alert.alert_type] || alert.alert_type}
                          </span>
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                {formatTimestamp(alert.created_at)}
                              </TooltipTrigger>
                              <TooltipContent>
                                {formatFullTimestamp(alert.created_at)}
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </div>
                        
                        {alert.is_acknowledged && (
                          <div className="flex items-center gap-1 mt-2 text-[10px] text-green-600">
                            <Check className="h-3 w-3" />
                            Acknowledged {alert.acknowledged_at && formatTimestamp(alert.acknowledged_at)}
                            {alert.acknowledgment_notes && (
                              <span className="ml-1 text-muted-foreground">
                                - {alert.acknowledgment_notes}
                              </span>
                            )}
                          </div>
                        )}
                        
                        {/* Metadata preview */}
                        {alert.metadata && Object.keys(alert.metadata).length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {Object.entries(alert.metadata).slice(0, 3).map(([key, value]) => (
                              <Badge key={key} variant="outline" className="text-[10px]">
                                {key}: {typeof value === "number" ? value.toFixed(1) : String(value)}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                      
                      {/* Actions */}
                      <div className="flex items-center gap-1 shrink-0">
                        {!alert.is_acknowledged && (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-7 w-7"
                                  onClick={() => {
                                    setSelectedAlerts(new Set([alert.id]))
                                    setAcknowledgeDialogOpen(true)
                                  }}
                                >
                                  <Check className="h-4 w-4" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>Acknowledge</TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        )}
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 text-muted-foreground hover:text-destructive"
                                onClick={() => handleDelete(alert.id)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Delete</TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </ScrollArea>
      </CardContent>

      {/* Acknowledge Dialog */}
      <Dialog open={acknowledgeDialogOpen} onOpenChange={setAcknowledgeDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Acknowledge Alert{selectedAlerts.size > 1 ? "s" : ""}</DialogTitle>
            <DialogDescription>
              Mark {selectedAlerts.size} alert{selectedAlerts.size > 1 ? "s" : ""} as reviewed.
              You can optionally add notes.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Textarea
              placeholder="Add notes (optional)..."
              value={acknowledgeNotes}
              onChange={(e) => setAcknowledgeNotes(e.target.value)}
              className="min-h-[100px]"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAcknowledgeDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleAcknowledge} disabled={acknowledging}>
              {acknowledging && <RefreshCw className="h-4 w-4 mr-2 animate-spin" />}
              Acknowledge
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}

// Badge component for alert count display
export function AlertBadge({ count, className }: { count: number; className?: string }) {
  if (count === 0) return null
  
  return (
    <Badge 
      variant="destructive" 
      className={cn("h-5 min-w-5 px-1 text-[10px] font-bold", className)}
    >
      {count > 99 ? "99+" : count}
    </Badge>
  )
}
