"use client"

import { useState, useMemo, useCallback, useEffect } from "react"
import { useAnalysisStore } from "@/lib/store"
import { useApi } from "@/hooks/use-api"
import { cn } from "@/lib/utils"
import {
  History,
  Search,
  Filter,
  Loader2,
  RefreshCw,
  ChevronRight,
  FileText,
  Beaker,
  Check,
  X,
  AlertCircle,
  Clock,
  User,
  Folder,
  ChevronDown,
  ChevronUp,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { Skeleton } from "@/components/ui/skeleton"
import { useToast } from "@/hooks/use-toast"

interface PreviousAnalysesProps {
  className?: string
  compact?: boolean
  defaultExpanded?: boolean
}

export function PreviousAnalyses({
  className,
  compact = false,
  defaultExpanded = true,
}: PreviousAnalysesProps) {
  const { toast } = useToast()
  const {
    apiSamples,
    samplesLoading,
    fcsAnalysis,
    ntaAnalysis,
    activeTab,
    setActiveTab,
  } = useAnalysisStore()
  const { fetchSamples, openSampleInTab } = useApi()

  // Local state
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)
  const [searchQuery, setSearchQuery] = useState("")
  const [treatmentFilter, setTreatmentFilter] = useState<string>("all")
  const [typeFilter, setTypeFilter] = useState<string>("all")
  const [loadingSampleId, setLoadingSampleId] = useState<string | null>(null)

  // Get unique treatments from samples
  const treatments = useMemo(() => {
    const uniqueTreatments = new Set<string>()
    apiSamples.forEach((s) => {
      if (s.treatment) uniqueTreatments.add(s.treatment)
    })
    return Array.from(uniqueTreatments).sort()
  }, [apiSamples])

  // Filter and search samples
  const filteredSamples = useMemo(() => {
    return apiSamples.filter((sample) => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        const matchesId = sample.sample_id.toLowerCase().includes(query)
        const matchesTreatment = sample.treatment?.toLowerCase().includes(query)
        if (!matchesId && !matchesTreatment) return false
      }

      // Treatment filter
      if (treatmentFilter !== "all" && sample.treatment !== treatmentFilter) {
        return false
      }

      // Type filter (FCS/NTA)
      if (typeFilter === "fcs" && !sample.files?.fcs) return false
      if (typeFilter === "nta" && !sample.files?.nta) return false
      if (typeFilter === "both" && (!sample.files?.fcs || !sample.files?.nta))
        return false

      return true
    })
  }, [apiSamples, searchQuery, treatmentFilter, typeFilter])

  // Check if a sample is currently active
  const isActiveSample = useCallback(
    (sampleId: string) => {
      return (
        fcsAnalysis.sampleId === sampleId || ntaAnalysis.sampleId === sampleId
      )
    },
    [fcsAnalysis.sampleId, ntaAnalysis.sampleId]
  )

  // Handle sample click
  const handleSampleClick = useCallback(
    async (sampleId: string, type: "fcs" | "nta") => {
      setLoadingSampleId(sampleId)
      try {
        const success = await openSampleInTab(sampleId, type)
        if (success) {
          toast({
            title: "Analysis loaded",
            description: `Loaded ${type.toUpperCase()} analysis for ${sampleId}`,
          })
        }
      } catch (error) {
        toast({
          variant: "destructive",
          title: "Failed to load analysis",
          description: `Could not load ${type.toUpperCase()} data for ${sampleId}`,
        })
      } finally {
        setLoadingSampleId(null)
      }
    },
    [openSampleInTab, toast]
  )

  // Format date for display
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return null
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    } catch {
      return null
    }
  }

  // Refresh samples
  const handleRefresh = useCallback(() => {
    fetchSamples()
  }, [fetchSamples])

  // Clear filters
  const clearFilters = useCallback(() => {
    setSearchQuery("")
    setTreatmentFilter("all")
    setTypeFilter("all")
  }, [])

  const hasActiveFilters =
    searchQuery || treatmentFilter !== "all" || typeFilter !== "all"

  return (
    <Collapsible
      open={isExpanded}
      onOpenChange={setIsExpanded}
      className={cn("border rounded-lg bg-card overflow-hidden", className)}
    >
      <CollapsibleTrigger asChild>
        <div className="flex items-center justify-between p-3 cursor-pointer hover:bg-secondary/30 transition-colors">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-primary" />
            <span className="font-medium text-sm">Previous Analyses</span>
            {apiSamples.length > 0 && (
              <Badge variant="secondary" className="text-xs">
                {apiSamples.length}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-1">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleRefresh()
                    }}
                    disabled={samplesLoading}
                  >
                    {samplesLoading ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <RefreshCw className="h-3 w-3" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="text-xs">Refresh samples</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            {isExpanded ? (
              <ChevronUp className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            )}
          </div>
        </div>
      </CollapsibleTrigger>

      <CollapsibleContent>
        <div className="px-3 pb-3 space-y-3">
          {/* Search and Filters */}
          <div className="space-y-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <Input
                placeholder="Search samples..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-8 pl-8 text-sm"
              />
              {searchQuery && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6"
                  onClick={() => setSearchQuery("")}
                >
                  <X className="h-3 w-3" />
                </Button>
              )}
            </div>

            {!compact && (
              <div className="flex gap-2">
                <Select value={treatmentFilter} onValueChange={setTreatmentFilter}>
                  <SelectTrigger className="h-8 text-xs flex-1">
                    <SelectValue placeholder="Treatment" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Treatments</SelectItem>
                    {treatments.map((t) => (
                      <SelectItem key={t} value={t}>
                        {t}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={typeFilter} onValueChange={setTypeFilter}>
                  <SelectTrigger className="h-8 text-xs flex-1">
                    <SelectValue placeholder="Type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Types</SelectItem>
                    <SelectItem value="fcs">FCS Only</SelectItem>
                    <SelectItem value="nta">NTA Only</SelectItem>
                    <SelectItem value="both">FCS + NTA</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-xs w-full"
                onClick={clearFilters}
              >
                Clear filters
              </Button>
            )}
          </div>

          {/* Sample List */}
          <ScrollArea className="max-h-[300px]">
            {samplesLoading && apiSamples.length === 0 ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-14 w-full" />
                ))}
              </div>
            ) : filteredSamples.length === 0 ? (
              <div className="text-center py-6">
                <AlertCircle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">
                  {apiSamples.length === 0
                    ? "No samples uploaded yet"
                    : "No samples match your filters"}
                </p>
                {hasActiveFilters && (
                  <Button
                    variant="link"
                    size="sm"
                    className="mt-2"
                    onClick={clearFilters}
                  >
                    Clear filters
                  </Button>
                )}
              </div>
            ) : (
              <div className="space-y-1">
                {filteredSamples.map((sample) => {
                  const isActive = isActiveSample(sample.sample_id)
                  const isLoading = loadingSampleId === sample.sample_id
                  const hasFcs = !!sample.files?.fcs
                  const hasNta = !!sample.files?.nta
                  const uploadDate = formatDate(sample.upload_timestamp)

                  return (
                    <div
                      key={sample.id}
                      className={cn(
                        "p-2.5 rounded-lg border transition-all",
                        isActive
                          ? "bg-primary/10 border-primary/30"
                          : "bg-secondary/30 border-transparent hover:border-border hover:bg-secondary/50",
                        isLoading && "opacity-70"
                      )}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 max-w-full overflow-hidden">
                            {isActive && (
                              <Check className="h-3 w-3 text-primary shrink-0" />
                            )}
                            <span
                              className={cn(
                                "font-medium text-sm truncate block max-w-[120px]",
                                isActive && "text-primary"
                              )}
                              title={sample.sample_id}
                            >
                              {sample.sample_id}
                            </span>
                          </div>
                          {sample.treatment && (
                            <div className="flex items-center gap-1 mt-0.5 max-w-full overflow-hidden">
                              <Beaker className="h-3 w-3 text-muted-foreground shrink-0" />
                              <span className="text-xs text-muted-foreground truncate max-w-[100px]" title={sample.treatment}>
                                {sample.treatment}
                              </span>
                            </div>
                          )}
                          {uploadDate && (
                            <div className="flex items-center gap-1 mt-0.5">
                              <Clock className="h-3 w-3 text-muted-foreground" />
                              <span className="text-[10px] text-muted-foreground">
                                {uploadDate}
                              </span>
                            </div>
                          )}
                        </div>

                        <div className="flex flex-col gap-1">
                          {hasFcs && (
                            <Button
                              variant={
                                isActive && activeTab === "flow-cytometry"
                                  ? "default"
                                  : "outline"
                              }
                              size="sm"
                              className="h-6 px-2 text-xs"
                              onClick={() =>
                                handleSampleClick(sample.sample_id, "fcs")
                              }
                              disabled={isLoading}
                            >
                              {isLoading ? (
                                <Loader2 className="h-3 w-3 animate-spin" />
                              ) : (
                                <>
                                  <FileText className="h-3 w-3 mr-1" />
                                  FCS
                                </>
                              )}
                            </Button>
                          )}
                          {hasNta && (
                            <Button
                              variant={
                                isActive && activeTab === "nta"
                                  ? "default"
                                  : "outline"
                              }
                              size="sm"
                              className="h-6 px-2 text-xs"
                              onClick={() =>
                                handleSampleClick(sample.sample_id, "nta")
                              }
                              disabled={isLoading}
                            >
                              {isLoading ? (
                                <Loader2 className="h-3 w-3 animate-spin" />
                              ) : (
                                <>
                                  <Beaker className="h-3 w-3 mr-1" />
                                  NTA
                                </>
                              )}
                            </Button>
                          )}
                          {!hasFcs && !hasNta && (
                            <Badge
                              variant="secondary"
                              className="text-[10px] px-1.5"
                            >
                              No files
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </ScrollArea>

          {/* Footer - Show count */}
          {filteredSamples.length > 0 && (
            <div className="text-center text-xs text-muted-foreground pt-1 border-t">
              Showing {filteredSamples.length} of {apiSamples.length} samples
            </div>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
