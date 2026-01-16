"use client"

import { useState, useEffect, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { 
  ChevronDown, 
  Wand2, 
  Sparkles, 
  RefreshCw, 
  Star,
  ChevronRight,
  Info,
  TrendingUp,
  Layers
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useApi } from "@/hooks/use-api"
import { Skeleton } from "@/components/ui/skeleton"

export interface AxisRecommendation {
  rank: number
  x_channel: string
  y_channel: string
  score: number
  reason: string
  description: string
}

export interface ChannelCategories {
  scatter: string[]
  fluorescence: string[]
  all: string[]
}

interface ScatterAxisSelectorProps {
  sampleId: string
  xChannel: string
  yChannel: string
  onAxisChange: (xChannel: string, yChannel: string) => void
  disabled?: boolean
  compact?: boolean
  className?: string
  // Fallback channels from FCS results if API fails
  availableChannels?: string[]
}

export function ScatterAxisSelector({
  sampleId,
  xChannel,
  yChannel,
  onAxisChange,
  disabled = false,
  compact = false,
  className,
  availableChannels = [],
}: ScatterAxisSelectorProps) {
  const { getRecommendedAxes } = useApi()
  
  const [recommendations, setRecommendations] = useState<AxisRecommendation[]>([])
  const [channels, setChannels] = useState<ChannelCategories>({ scatter: [], fluorescence: [], all: [] })
  const [loading, setLoading] = useState(false)
  const [showRecommendations, setShowRecommendations] = useState(true)  // Default to expanded for better visibility
  const [initialized, setInitialized] = useState(false)

  // Initialize channels from availableChannels prop if API hasn't loaded yet
  useEffect(() => {
    if (channels.all.length === 0 && availableChannels.length > 0) {
      // Categorize channels from fallback list
      const scatter = availableChannels.filter(ch => 
        /FSC|SSC|VFSC|VSSC/i.test(ch)
      )
      const fluorescence = availableChannels.filter(ch => 
        /^(B|R|Y|G|V)\d|FL\d|PE|APC|FITC|CD\d/i.test(ch) && !scatter.includes(ch)
      )
      setChannels({
        scatter,
        fluorescence,
        all: availableChannels
      })
    }
  }, [availableChannels, channels.all.length])

  // Fetch recommendations on mount or when sample changes
  const fetchRecommendations = useCallback(async () => {
    if (!sampleId) return
    
    setLoading(true)
    try {
      const result = await getRecommendedAxes(sampleId, { nRecommendations: 5 })
      if (result) {
        setRecommendations(result.recommendations)
        setChannels(result.channels)
        
        // Auto-apply best recommendation on first load if not already set
        if (!initialized && result.recommendations.length > 0) {
          const best = result.recommendations[0]
          // Only auto-apply if current axes are generic/default
          const currentIsDefault = 
            xChannel === "FSC" || xChannel === "VFSC-A" || !xChannel ||
            yChannel === "SSC" || yChannel === "VSSC1-A" || !yChannel
          
          if (currentIsDefault) {
            onAxisChange(best.x_channel, best.y_channel)
          }
          setInitialized(true)
        }
      }
    } catch (error) {
      console.error("Failed to fetch axis recommendations:", error)
    } finally {
      setLoading(false)
    }
  }, [sampleId, getRecommendedAxes, initialized, xChannel, yChannel, onAxisChange])

  useEffect(() => {
    fetchRecommendations()
  }, [sampleId]) // Only re-fetch when sample changes

  // Apply a recommendation
  const applyRecommendation = (rec: AxisRecommendation) => {
    onAxisChange(rec.x_channel, rec.y_channel)
    setShowRecommendations(false)
  }

  // Get score color based on value
  const getScoreColor = (score: number) => {
    if (score >= 0.8) return "text-green-500"
    if (score >= 0.6) return "text-yellow-500"
    return "text-gray-400"
  }

  // Get badge variant based on reason
  const getReasonBadge = (reason: string) => {
    if (reason.includes("Standard gating")) {
      return <Badge variant="default" className="bg-blue-600 text-[10px]">Standard</Badge>
    }
    if (reason.includes("Fluorescence vs Size")) {
      return <Badge variant="secondary" className="text-[10px]">Marker</Badge>
    }
    if (reason.includes("Multi-marker")) {
      return <Badge variant="outline" className="text-[10px]">Co-expression</Badge>
    }
    return <Badge variant="outline" className="text-[10px]">{reason.slice(0, 15)}</Badge>
  }

  // Check if a recommendation is currently selected
  const isSelected = (rec: AxisRecommendation) => 
    rec.x_channel === xChannel && rec.y_channel === yChannel

  if (compact) {
    // Compact mode: Just a popover with recommendations
    return (
      <Popover open={showRecommendations} onOpenChange={setShowRecommendations}>
        <PopoverTrigger asChild>
          <Button 
            variant="outline" 
            size="sm" 
            disabled={disabled || loading}
            className={cn("gap-2", className)}
          >
            {loading ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Wand2 className="h-3.5 w-3.5" />
            )}
            <span className="hidden sm:inline">Auto-Select Axes</span>
            <span className="sm:hidden">Auto</span>
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-80 p-0" align="start">
          <div className="p-3 border-b">
            <h4 className="font-medium flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-yellow-500" />
              AI-Recommended Axes
            </h4>
            <p className="text-xs text-muted-foreground mt-1">
              Optimal channel pairs based on variance, correlation, and cytometry best practices.
            </p>
          </div>
          <div className="max-h-[300px] overflow-auto">
            {loading ? (
              <div className="p-3 space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Skeleton className="h-6 w-6 rounded-full" />
                    <Skeleton className="h-10 flex-1" />
                  </div>
                ))}
              </div>
            ) : recommendations.length === 0 ? (
              <div className="p-4 text-center text-muted-foreground text-sm">
                No recommendations available
              </div>
            ) : (
              <div className="divide-y">
                {recommendations.map((rec) => (
                  <button
                    key={`${rec.x_channel}-${rec.y_channel}`}
                    className={cn(
                      "w-full p-3 text-left hover:bg-accent/50 transition-colors",
                      isSelected(rec) && "bg-accent"
                    )}
                    onClick={() => applyRecommendation(rec)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className={cn(
                          "flex items-center justify-center h-6 w-6 rounded-full text-xs font-bold",
                          rec.rank === 1 ? "bg-yellow-100 text-yellow-700" :
                          rec.rank === 2 ? "bg-gray-100 text-gray-700" :
                          "bg-orange-100 text-orange-700"
                        )}>
                          {rec.rank}
                        </span>
                        <div>
                          <div className="font-mono text-sm">
                            {rec.x_channel} vs {rec.y_channel}
                          </div>
                          <div className="flex items-center gap-1 mt-0.5">
                            {getReasonBadge(rec.reason)}
                          </div>
                        </div>
                      </div>
                      <div className="flex flex-col items-end">
                        <span className={cn("text-sm font-medium", getScoreColor(rec.score))}>
                          {(rec.score * 100).toFixed(0)}%
                        </span>
                        {isSelected(rec) && (
                          <Badge variant="outline" className="text-[10px] mt-1">
                            Current
                          </Badge>
                        )}
                      </div>
                    </div>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <p className="text-xs text-muted-foreground mt-1 line-clamp-1 cursor-help">
                            {rec.description}
                          </p>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs">
                          <p>{rec.description}</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="p-2 border-t bg-muted/30">
            <Button 
              variant="ghost" 
              size="sm" 
              className="w-full text-xs"
              onClick={fetchRecommendations}
              disabled={loading}
            >
              <RefreshCw className={cn("h-3 w-3 mr-1", loading && "animate-spin")} />
              Refresh Recommendations
            </Button>
          </div>
        </PopoverContent>
      </Popover>
    )
  }

  // Full mode: Expandable card with manual selection + recommendations
  return (
    <Card className={cn("glass-card", className)}>
      <Collapsible open={showRecommendations} onOpenChange={setShowRecommendations}>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-secondary/30 transition-colors py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-primary" />
                <CardTitle className="text-sm font-medium">Axis Selection</CardTitle>
                <Badge variant="outline" className="ml-2 text-xs font-mono">
                  {xChannel} × {yChannel}
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                {recommendations.length > 0 && (
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger>
                        <Badge variant="secondary" className="gap-1">
                          <Sparkles className="h-3 w-3" />
                          {recommendations.length} suggestions
                        </Badge>
                      </TooltipTrigger>
                      <TooltipContent>
                        AI-generated axis recommendations
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                )}
                <ChevronDown className={cn(
                  "h-4 w-4 transition-transform",
                  showRecommendations && "rotate-180"
                )} />
              </div>
            </div>
          </CardHeader>
        </CollapsibleTrigger>
        
        <CollapsibleContent>
          <CardContent className="pt-0 space-y-4">
            {/* Manual Channel Selection */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">X-Axis Channel</label>
                <Select 
                  value={xChannel} 
                  onValueChange={(val) => onAxisChange(val, yChannel)}
                  disabled={disabled || loading}
                >
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue placeholder="Select X channel" />
                  </SelectTrigger>
                  <SelectContent>
                    {channels.scatter.length > 0 && (
                      <>
                        <div className="px-2 py-1 text-xs font-semibold text-muted-foreground bg-muted/50">
                          Scatter
                        </div>
                        {channels.scatter.map((ch) => (
                          <SelectItem key={ch} value={ch} className="text-xs">
                            {ch}
                          </SelectItem>
                        ))}
                      </>
                    )}
                    {channels.fluorescence.length > 0 && (
                      <>
                        <div className="px-2 py-1 text-xs font-semibold text-muted-foreground bg-muted/50 mt-1">
                          Fluorescence
                        </div>
                        {channels.fluorescence.map((ch) => (
                          <SelectItem key={ch} value={ch} className="text-xs">
                            {ch}
                          </SelectItem>
                        ))}
                      </>
                    )}
                    {channels.all.filter(ch => !channels.scatter.includes(ch) && !channels.fluorescence.includes(ch)).length > 0 && (
                      <>
                        <div className="px-2 py-1 text-xs font-semibold text-muted-foreground bg-muted/50 mt-1">
                          Other
                        </div>
                        {channels.all
                          .filter(ch => !channels.scatter.includes(ch) && !channels.fluorescence.includes(ch))
                          .map((ch) => (
                            <SelectItem key={ch} value={ch} className="text-xs">
                              {ch}
                            </SelectItem>
                          ))
                        }
                      </>
                    )}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Y-Axis Channel</label>
                <Select 
                  value={yChannel} 
                  onValueChange={(val) => onAxisChange(xChannel, val)}
                  disabled={disabled || loading}
                >
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue placeholder="Select Y channel" />
                  </SelectTrigger>
                  <SelectContent>
                    {channels.scatter.length > 0 && (
                      <>
                        <div className="px-2 py-1 text-xs font-semibold text-muted-foreground bg-muted/50">
                          Scatter
                        </div>
                        {channels.scatter.map((ch) => (
                          <SelectItem key={ch} value={ch} className="text-xs">
                            {ch}
                          </SelectItem>
                        ))}
                      </>
                    )}
                    {channels.fluorescence.length > 0 && (
                      <>
                        <div className="px-2 py-1 text-xs font-semibold text-muted-foreground bg-muted/50 mt-1">
                          Fluorescence
                        </div>
                        {channels.fluorescence.map((ch) => (
                          <SelectItem key={ch} value={ch} className="text-xs">
                            {ch}
                          </SelectItem>
                        ))}
                      </>
                    )}
                    {channels.all.filter(ch => !channels.scatter.includes(ch) && !channels.fluorescence.includes(ch)).length > 0 && (
                      <>
                        <div className="px-2 py-1 text-xs font-semibold text-muted-foreground bg-muted/50 mt-1">
                          Other
                        </div>
                        {channels.all
                          .filter(ch => !channels.scatter.includes(ch) && !channels.fluorescence.includes(ch))
                          .map((ch) => (
                            <SelectItem key={ch} value={ch} className="text-xs">
                              {ch}
                            </SelectItem>
                          ))
                        }
                      </>
                    )}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* AI Recommendations Section */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-medium flex items-center gap-1.5 text-muted-foreground">
                  <Sparkles className="h-3.5 w-3.5 text-yellow-500" />
                  AI Recommendations
                </h4>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-xs"
                  onClick={fetchRecommendations}
                  disabled={loading}
                >
                  <RefreshCw className={cn("h-3 w-3 mr-1", loading && "animate-spin")} />
                  Refresh
                </Button>
              </div>

              {loading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-14 w-full" />
                  ))}
                </div>
              ) : recommendations.length === 0 ? (
                <div className="p-3 border rounded-md text-center text-muted-foreground text-xs">
                  <Info className="h-4 w-4 mx-auto mb-1" />
                  No recommendations available yet
                </div>
              ) : (
                <div className="space-y-1.5">
                  {recommendations.map((rec) => (
                    <button
                      key={`${rec.x_channel}-${rec.y_channel}`}
                      className={cn(
                        "w-full p-2.5 rounded-md border text-left transition-all",
                        "hover:border-primary/50 hover:bg-accent/30",
                        isSelected(rec) 
                          ? "border-primary bg-primary/10" 
                          : "border-border"
                      )}
                      onClick={() => applyRecommendation(rec)}
                      disabled={disabled}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className={cn(
                            "flex items-center justify-center h-5 w-5 rounded-full text-[10px] font-bold",
                            rec.rank === 1 
                              ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300" 
                              : rec.rank === 2 
                              ? "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300" 
                              : "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300"
                          )}>
                            {rec.rank}
                          </span>
                          <div className="space-y-0.5">
                            <div className="font-mono text-xs font-medium">
                              {rec.x_channel} <span className="text-muted-foreground">vs</span> {rec.y_channel}
                            </div>
                            <div className="flex items-center gap-1">
                              {getReasonBadge(rec.reason)}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="flex flex-col items-end">
                            <div className="flex items-center gap-1">
                              <TrendingUp className={cn("h-3 w-3", getScoreColor(rec.score))} />
                              <span className={cn("text-xs font-semibold", getScoreColor(rec.score))}>
                                {(rec.score * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>
                          {isSelected(rec) && (
                            <Star className="h-3.5 w-3.5 text-primary fill-primary" />
                          )}
                          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                        </div>
                      </div>
                      <p className="text-[10px] text-muted-foreground mt-1 line-clamp-1">
                        {rec.description}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
