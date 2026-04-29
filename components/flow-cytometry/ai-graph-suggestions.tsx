"use client"

import { useState, useCallback, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Loader2, Sparkles, ChevronDown, ChevronUp, BarChart3 } from "lucide-react"
import { useAnalysisStore } from "@/lib/store"
import { useShallow } from "zustand/react/shallow"
import { getApiBaseUrl } from "@/lib/module-config"

const API_BASE = getApiBaseUrl()

interface GraphSuggestion {
  title: string
  x_axis: string
  y_axis: string
  description: string
  priority: "high" | "medium" | "low"
  reason: string
}

interface SuggestionsResponse {
  suggestions: GraphSuggestion[]
  context_used: string
  summary: string
}

interface AIGraphSuggestionsProps {
  onSuggestionClick?: (xAxis: string, yAxis: string, title: string) => void
  filePaths?: string[]
}

export function AIGraphSuggestions({ onSuggestionClick, filePaths = [] }: AIGraphSuggestionsProps) {
  const { fcsAnalysis, secondaryFcsAnalysis, fcsCompareSession } = useAnalysisStore(
    useShallow((s) => ({
      fcsAnalysis: s.fcsAnalysis,
      secondaryFcsAnalysis: s.secondaryFcsAnalysis,
      fcsCompareSession: s.fcsCompareSession,
    }))
  )

  const [suggestions, setSuggestions] = useState<GraphSuggestion[]>([])
  const [summary, setSummary] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [context, setContext] = useState("")
  const [showContextInput, setShowContextInput] = useState(false)
  const [expanded, setExpanded] = useState(true)

  // Detect mode
  const isCompareMode = fcsCompareSession.selectedSampleIds.length > 1
  const hasResults = fcsAnalysis.results !== null
  const channels = fcsAnalysis.results?.channels || []

  const fetchSuggestions = useCallback(async () => {
    if (!hasResults && filePaths.length === 0) return

    setLoading(true)
    setError("")

    try {
      // Build payload — use actual channels if available
      const payload = {
        channels: channels.length > 0 ? channels : ["FSC-A", "SSC-A", "Size"],
        context: context || "",
        is_compare_mode: isCompareMode,
        num_files: isCompareMode
          ? fcsCompareSession.selectedSampleIds.length
          : 1,
        file_stats: filePaths.length > 0 ? { file_count: filePaths.length } : null,
      }

      const r = await fetch(`${API_BASE}/api/v1/ai/nanofacs/suggest-graphs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })

      if (!r.ok) throw new Error("Failed to get suggestions")
      const data: SuggestionsResponse = await r.json()
      setSuggestions(data.suggestions || [])
      setSummary(data.summary || "")
    } catch {
      setError("Could not load suggestions. Check backend is running.")
    } finally {
      setLoading(false)
    }
  }, [hasResults, filePaths.length, channels, context, isCompareMode, fcsCompareSession.selectedSampleIds.length])

  // Auto-fetch when results change
  useEffect(() => {
    if (hasResults || filePaths.length > 0) {
      fetchSuggestions()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasResults, isCompareMode])

  const priorityColor = {
    high: "destructive" as const,
    medium: "secondary" as const,
    low: "outline" as const,
  }

  const priorityBg = {
    high: "border-l-red-500",
    medium: "border-l-yellow-500",
    low: "border-l-blue-500",
  }

  if (!hasResults && filePaths.length === 0) return null

  return (
    <Card className="card-3d">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            AI Graph Suggestions
            {isCompareMode && (
              <Badge variant="outline" className="text-xs">
                Compare Mode — {fcsCompareSession.selectedSampleIds.length} files
              </Badge>
            )}
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowContextInput(!showContextInput)}
              className="text-xs gap-1"
            >
              Add Context
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </div>
        </div>

        {/* Context Input */}
        {showContextInput && (
          <div className="mt-3 space-y-2">
            <textarea
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="e.g. Sample 1 has green fluorescence marker CD81, Sample 2 is unlabeled control. Looking for EV population shifts..."
              className="w-full text-sm bg-muted/40 rounded-md px-3 py-2 outline-none focus:ring-1 focus:ring-ring placeholder:text-muted-foreground/50 resize-none"
              rows={3}
            />
            <Button size="sm" onClick={fetchSuggestions} className="gap-2" disabled={loading}>
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
              Get Suggestions
            </Button>
          </div>
        )}
      </CardHeader>

      {expanded && (
        <CardContent className="pt-0 space-y-3">
          {loading && (
            <div className="flex items-center gap-2 text-muted-foreground text-sm py-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Analyzing channels and generating suggestions...
            </div>
          )}

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          {summary && !loading && (
            <p className="text-xs text-muted-foreground italic">{summary}</p>
          )}

          {!loading && suggestions.length > 0 && (
            <div className="space-y-2">
              {suggestions.map((s, i) => (
                <div
                  key={i}
                  className={`border-l-4 ${priorityBg[s.priority]} bg-muted/20 rounded-r-lg p-3 cursor-pointer hover:bg-muted/40 transition-colors`}
                  onClick={() => onSuggestionClick?.(s.x_axis, s.y_axis, s.title)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <BarChart3 className="h-3.5 w-3.5 text-primary shrink-0" />
                        <span className="text-sm font-medium">{s.title}</span>
                        <Badge variant={priorityColor[s.priority]} className="text-xs px-1.5 py-0">
                          {s.priority}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">{s.description}</p>
                      <p className="text-xs text-primary/70 mt-1">💡 {s.reason}</p>
                    </div>
                    <div className="text-xs text-muted-foreground shrink-0 text-right">
                      <div>{s.x_axis}</div>
                      <div>vs</div>
                      <div>{s.y_axis}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {!loading && suggestions.length === 0 && !error && (
            <div className="text-center py-4">
              <p className="text-sm text-muted-foreground mb-3">
                Get AI-powered graph suggestions based on your data.
              </p>
              <Button size="sm" onClick={fetchSuggestions} className="gap-2">
                <Sparkles className="h-3.5 w-3.5" />
                Generate Suggestions
              </Button>
            </div>
          )}

          {suggestions.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={fetchSuggestions}
              className="w-full text-xs gap-1.5 mt-1"
              disabled={loading}
            >
              <Loader2 className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              Refresh Suggestions
            </Button>
          )}
        </CardContent>
      )}
    </Card>
  )
}
