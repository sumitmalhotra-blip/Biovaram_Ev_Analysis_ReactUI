"use client"

import { useState, useCallback, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  AlertCircle,
  BarChart3,
  Brain,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Database,
  Loader2,
  MessageCircle,
  Search,
  Send,
  Sparkles,
  XCircle,
} from "lucide-react"
import { useAnalysisStore } from "@/lib/store"
import { useShallow } from "zustand/react/shallow"
import { getApiBaseUrl } from "@/lib/module-config"

const API_BASE = getApiBaseUrl()

// ============================================================================
// Types
// ============================================================================

interface AIAnalysisResult {
  anomalies: string[]
  cluster_findings: string[]
  suggested_graphs: string[]
  missed_parameters: string[]
  suggestions: string[]
  summary: string
  analyzed_files: string[]
  analyzed_at: string
}

interface MetadataCompareResult {
  mismatches: Array<{
    parameter: string
    values: Record<string, number | string>
    percent_difference?: number
    difference?: string | number
    tolerance?: string | number
    severity: string
    message: string
  }>
  matching_fields: string[]
  cluster_comparison?: string[]
  recommendation: string
  compared_files?: string[]
  compared_samples?: string[]
}

interface ChatMsg {
  role: "user" | "assistant"
  content: string
}

// ============================================================================
// Collapsible Section
// ============================================================================

function Section({
  title,
  icon,
  count,
  defaultOpen = true,
  children,
  accent,
}: {
  title: string
  icon: React.ReactNode
  count?: number
  defaultOpen?: boolean
  children: React.ReactNode
  accent?: string
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className={`border rounded-lg overflow-hidden ${accent || ""}`}>
      <button
        className="w-full flex items-center justify-between px-4 py-3 bg-muted/30 hover:bg-muted/50 transition-colors"
        onClick={() => setOpen(!open)}
      >
        <div className="flex items-center gap-2 text-sm font-medium">
          {icon}
          {title}
          {count !== undefined && (
            <Badge variant="outline" className="text-xs ml-1">{count}</Badge>
          )}
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
      </button>
      {open && <div className="px-4 py-3 space-y-2">{children}</div>}
    </div>
  )
}

// ============================================================================
// Main Component
// ============================================================================

export function AIAnalysisTab() {
  const {
    fcsAnalysis,
    secondaryFcsAnalysis,
    fcsCompareSession,
    pinnedCharts,
  } = useAnalysisStore(
    useShallow((s) => ({
      fcsAnalysis: s.fcsAnalysis,
      secondaryFcsAnalysis: s.secondaryFcsAnalysis,
      fcsCompareSession: s.fcsCompareSession,
      pinnedCharts: s.pinnedCharts,
    }))
  )

  const [activeTab, setActiveTab] = useState("overview")

  // Data overview state
  const [analysisResult, setAnalysisResult] = useState<AIAnalysisResult | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [analysisError, setAnalysisError] = useState("")
  const [userContext, setUserContext] = useState("")
  const [showContextInput, setShowContextInput] = useState(false)

  // Metadata state
  const [metadataResult, setMetadataResult] = useState<MetadataCompareResult | null>(null)
  const [metadataLoading, setMetadataLoading] = useState(false)

  // Chat state
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [question, setQuestion] = useState("")
  const [qaLoading, setQaLoading] = useState(false)

  // Detect mode
  const isCompareMode = fcsCompareSession.selectedSampleIds.length > 1
  const hasResults = fcsAnalysis.results !== null
  const sampleIds = isCompareMode
    ? fcsCompareSession.selectedSampleIds
    : fcsAnalysis.sampleId
    ? [fcsAnalysis.sampleId]
    : []

  // ── Data Overview / AI Analysis ──
  const runAnalysis = useCallback(async () => {
    if (sampleIds.length === 0) return
    setAnalysisLoading(true)
    setAnalysisError("")
    try {
      // Try NTA endpoint first, fall back to nanofacs
      const endpoint = `${API_BASE}/api/v1/ai/nanofacs/analyze`

      const payload = {
            experiment_description: userContext || "FCS EV analysis",
            parameters_of_interest: ["Size", "MeanIntensity"],
            same_sample: !isCompareMode,
            file_paths: [
              "/Users/abcd/biovaram/backend/data/nanofacs_parquet/PC3/20251217_0005_PC3_100kDa_F5_size_488_1000-010-030-100.0-15-1-0_20251217-102923.fcs.parquet",
              "/Users/abcd/biovaram/backend/data/nanofacs_parquet/PC3/20251217_0016_PC3_100kDa_F1_2_size_488_1000-010-030-100.0-15-1-0_20251217-140115.fcs.parquet"
            ],
          }

      const r = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      if (!r.ok) throw new Error("Analysis failed")
      setAnalysisResult(await r.json())
    } catch {
      setAnalysisError("Analysis failed. Make sure backend is running.")
    } finally {
      setAnalysisLoading(false)
    }
  }, [sampleIds, userContext, isCompareMode, fcsAnalysis.results?.channels])

  // ── Metadata Check ──
  const runMetadataCheck = useCallback(async () => {
    if (sampleIds.length < 2) return
    setMetadataLoading(true)
    try {
      const r = await fetch(`${API_BASE}/api/v1/ai/nta/compare-metadata`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sample_ids: sampleIds }),
      })
      setMetadataResult(await r.json())
    } catch {
    } finally {
      setMetadataLoading(false)
    }
  }, [sampleIds])

  // ── Ask ──
  const handleAsk = useCallback(async () => {
    if (!question.trim()) return
    const q = question
    setMessages(prev => [...prev, { role: "user", content: q }])
    setQuestion("")
    setQaLoading(true)

    try {
      // Build context from pinned charts + current analysis
      const pinnedContext = pinnedCharts.length > 0
        ? `User has ${pinnedCharts.length} pinned charts: ${pinnedCharts.map(c => c.title).join(", ")}.`
        : ""

      const dataContext = fcsAnalysis.results
        ? `Current FCS analysis: ${fcsAnalysis.sampleId}, ${fcsAnalysis.results.total_events?.toLocaleString() || "N/A"} events, median size ${fcsAnalysis.results.median_diameter_nm?.toFixed(1) || "N/A"}nm.`
        : ""

      const systemContext = [pinnedContext, dataContext, userContext].filter(Boolean).join(" ")

      const r = await fetch(`${API_BASE}/api/v1/chat/simple`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [
            {
              role: "system",
              content: `You are an expert in NanoFACS and EV analysis. Answer ONLY questions about the researcher's data. ${systemContext} Do not answer general questions unrelated to this data.`,
            },
            ...messages.map(m => ({ role: m.role, content: m.content })),
            { role: "user", content: q },
          ],
          stream: false,
        }),
      })
      const data = await r.json()
      setMessages(prev => [...prev, { role: "assistant", content: data.content || "Could not answer." }])
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Could not answer. Try again." }])
    } finally {
      setQaLoading(false)
    }
  }, [question, messages, pinnedCharts, fcsAnalysis, userContext])

  if (sampleIds.length === 0) {
    return (
      <Card className="card-3d">
        <CardContent className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <Brain className="h-10 w-10 mb-3 opacity-30" />
          <p className="text-sm">Upload and analyze an FCS file to enable AI insights.</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <Card className="card-3d">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Brain className="h-4 w-4 text-primary" />
              AI Analysis
              {isCompareMode && (
                <Badge variant="outline">
                  Compare Mode — {fcsCompareSession.selectedSampleIds.length} files
                </Badge>
              )}
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowContextInput(!showContextInput)}
              className="gap-2 text-xs"
            >
              <Search className="h-3.5 w-3.5" />
              {userContext ? "Edit Context" : "Add Research Context"}
            </Button>
          </div>

          {showContextInput && (
            <div className="mt-3 space-y-2">
              <textarea
                value={userContext}
                onChange={e => setUserContext(e.target.value)}
                placeholder="e.g. Sample 1 has green fluorescence CD81 marker. Sample 2 is unlabeled control. Looking for EV population shifts due to fluorescence labeling..."
                className="w-full text-sm bg-muted/40 rounded-md px-3 py-2 outline-none focus:ring-1 focus:ring-ring placeholder:text-muted-foreground/50 resize-none"
                rows={3}
              />
              <p className="text-xs text-muted-foreground">
                Give context about fluorescence markers, proteins, experimental conditions. AI uses this to give better recommendations.
              </p>
            </div>
          )}
        </CardHeader>
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="w-full">
          <TabsTrigger value="overview" className="flex-1 gap-2 text-xs">
            <BarChart3 className="h-3.5 w-3.5" />
            Data Overview
          </TabsTrigger>
          <TabsTrigger value="metadata" className="flex-1 gap-2 text-xs" disabled={sampleIds.length < 2}>
            <Database className="h-3.5 w-3.5" />
            Metadata Check
          </TabsTrigger>
          <TabsTrigger value="ask" className="flex-1 gap-2 text-xs">
            <MessageCircle className="h-3.5 w-3.5" />
            Ask Data
          </TabsTrigger>
        </TabsList>

        {/* ── Data Overview Tab ── */}
        <TabsContent value="overview" className="space-y-3 mt-3">

          {/* Current file stats */}
          {fcsAnalysis.results && (
            <Card className="card-3d">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Database className="h-4 w-4" />
                  {isCompareMode ? "Files Loaded" : "Current File"}
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="space-y-1">
                    <p className="text-muted-foreground text-xs">Sample ID</p>
                    <p className="font-medium text-xs truncate">{fcsAnalysis.sampleId || "N/A"}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-muted-foreground text-xs">Total Events</p>
                    <p className="font-medium">{fcsAnalysis.results.total_events?.toLocaleString() || "N/A"}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-muted-foreground text-xs">Median Size</p>
                    <p className="font-medium">{fcsAnalysis.results.median_diameter_nm?.toFixed(1) || "N/A"} nm</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-muted-foreground text-xs">Channels</p>
                    <p className="font-medium">{fcsAnalysis.results.channels?.length || "N/A"}</p>
                  </div>
                  {isCompareMode && (
                    <div className="col-span-2 space-y-1">
                      <p className="text-muted-foreground text-xs">Files in Compare</p>
                      <p className="font-medium">{fcsCompareSession.selectedSampleIds.length} files selected</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* AI Analysis */}
          {!analysisResult && !analysisLoading && (
            <Card className="card-3d">
              <CardContent className="pt-4 pb-4 text-center space-y-3">
                <Sparkles className="h-8 w-8 mx-auto text-primary opacity-60" />
                <p className="text-sm text-muted-foreground">
                  {isCompareMode
                    ? `Run AI analysis on ${sampleIds.length} selected files to detect anomalies, cluster shifts, and get recommendations.`
                    : "Run AI analysis to detect anomalies and get insights on your data."}
                </p>
                <Button onClick={runAnalysis} className="gap-2">
                  <Sparkles className="h-4 w-4" />
                  Run AI Analysis
                </Button>
              </CardContent>
            </Card>
          )}

          {analysisLoading && (
            <Card className="card-3d">
              <CardContent className="flex items-center justify-center py-8 gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm">Analyzing with AWS Bedrock Mistral...</span>
              </CardContent>
            </Card>
          )}

          {analysisError && (
            <Alert variant="destructive">
              <XCircle className="h-4 w-4" />
              <AlertDescription>{analysisError}</AlertDescription>
            </Alert>
          )}

          {analysisResult && (
            <div className="space-y-3">
              {/* Summary */}
              <Card className="card-3d">
                <CardContent className="pt-4 pb-4">
                  <p className="text-sm text-muted-foreground italic">{analysisResult.summary}</p>
                </CardContent>
              </Card>

              {/* Anomalies */}
              {analysisResult.anomalies.length > 0 && (
                <Section
                  title="Anomalies Detected"
                  icon={<AlertCircle className="h-4 w-4 text-destructive" />}
                  count={analysisResult.anomalies.length}
                  accent="border-destructive/30"
                >
                  {analysisResult.anomalies.map((a, i) => (
                    <div key={i} className="flex gap-2 text-sm">
                      <span className="text-destructive mt-0.5 shrink-0">•</span>
                      <span>{a}</span>
                    </div>
                  ))}
                </Section>
              )}

              {/* Cluster Findings */}
              {analysisResult.cluster_findings?.length > 0 && (
                <Section
                  title="Cluster Findings"
                  icon={<BarChart3 className="h-4 w-4 text-blue-500" />}
                  count={analysisResult.cluster_findings.length}
                  defaultOpen={false}
                >
                  {analysisResult.cluster_findings.map((c, i) => (
                    <div key={i} className="flex gap-2 text-sm">
                      <span className="text-blue-500 mt-0.5 shrink-0">•</span>
                      <span>{c}</span>
                    </div>
                  ))}
                </Section>
              )}

              {/* Missed Parameters */}
              {analysisResult.missed_parameters.length > 0 && (
                <Section
                  title="Parameters You May Have Missed"
                  icon={<AlertCircle className="h-4 w-4 text-yellow-500" />}
                  count={analysisResult.missed_parameters.length}
                  defaultOpen={false}
                >
                  {analysisResult.missed_parameters.map((m, i) => (
                    <div key={i} className="flex gap-2 text-sm">
                      <span className="text-yellow-500 mt-0.5 shrink-0">⚠</span>
                      <span>{m}</span>
                    </div>
                  ))}
                </Section>
              )}

              {/* Suggestions */}
              {analysisResult.suggestions.length > 0 && (
                <Section
                  title="Recommendations"
                  icon={<Sparkles className="h-4 w-4 text-primary" />}
                  count={analysisResult.suggestions.length}
                  defaultOpen={false}
                >
                  {analysisResult.suggestions.map((s, i) => (
                    <div key={i} className="flex gap-2 text-sm">
                      <span className="text-primary mt-0.5 shrink-0">💡</span>
                      <span>{s}</span>
                    </div>
                  ))}
                </Section>
              )}

              <Button
                variant="outline"
                size="sm"
                onClick={runAnalysis}
                className="w-full gap-2"
                disabled={analysisLoading}
              >
                <Loader2 className={`h-3.5 w-3.5 ${analysisLoading ? "animate-spin" : ""}`} />
                Re-run Analysis
              </Button>
            </div>
          )}
        </TabsContent>

        {/* ── Metadata Check Tab ── */}
        <TabsContent value="metadata" className="space-y-3 mt-3">
          {sampleIds.length < 2 ? (
            <Card className="card-3d">
              <CardContent className="flex items-center justify-center py-8 text-muted-foreground text-sm">
                Select at least 2 files in Compare Mode to check metadata.
              </CardContent>
            </Card>
          ) : (
            <>
              {!metadataResult && !metadataLoading && (
                <Card className="card-3d">
                  <CardContent className="pt-4 pb-4 text-center space-y-3">
                    <Database className="h-8 w-8 mx-auto text-primary opacity-60" />
                    <p className="text-sm text-muted-foreground">
                      Compare metadata across {sampleIds.length} files — temperature, pH, conductivity, instrument settings and more.
                    </p>
                    <Button onClick={runMetadataCheck} className="gap-2">
                      <Database className="h-4 w-4" />
                      Check Metadata
                    </Button>
                  </CardContent>
                </Card>
              )}

              {metadataLoading && (
                <Card className="card-3d">
                  <CardContent className="flex items-center justify-center py-8 gap-2 text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-sm">Comparing metadata...</span>
                  </CardContent>
                </Card>
              )}

              {metadataResult && (
                <div className="space-y-3">
                  <Card className="card-3d">
                    <CardContent className="pt-4 pb-4">
                      <p className="text-sm text-muted-foreground italic">{metadataResult.recommendation}</p>
                    </CardContent>
                  </Card>

                  {metadataResult.mismatches.length > 0 && (
                    <Section
                      title={`Mismatches (${metadataResult.mismatches.length})`}
                      icon={<XCircle className="h-4 w-4 text-destructive" />}
                      accent="border-destructive/30"
                    >
                      {metadataResult.mismatches.map((m, i) => (
                        <div key={i} className="border rounded-lg p-3 space-y-1.5 bg-background">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium">{m.parameter}</span>
                            <Badge variant={m.severity === "high" ? "destructive" : "secondary"} className="text-xs">
                              {m.severity.toUpperCase()}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground">{m.message}</p>
                        </div>
                      ))}
                    </Section>
                  )}

                  {metadataResult.matching_fields.length > 0 && (
                    <Section
                      title={`Matching Fields (${metadataResult.matching_fields.length})`}
                      icon={<CheckCircle className="h-4 w-4 text-green-500" />}
                      defaultOpen={false}
                    >
                      <div className="flex flex-wrap gap-2">
                        {metadataResult.matching_fields.map((f, i) => (
                          <Badge key={i} variant="outline" className="text-green-600 border-green-300">
                            ✓ {f}
                          </Badge>
                        ))}
                      </div>
                    </Section>
                  )}

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={runMetadataCheck}
                    className="w-full gap-2"
                  >
                    🔄 Re-check
                  </Button>
                </div>
              )}
            </>
          )}
        </TabsContent>

        {/* ── Ask Data Tab ── */}
        <TabsContent value="ask" className="mt-3">
          <Card className="card-3d">
            <CardContent className="p-0">
              <div className="px-4 py-2 border-b bg-muted/20">
                <p className="text-xs text-muted-foreground">
                  Ask questions about your uploaded data.
                  {pinnedCharts.length > 0 && ` AI can also answer about your ${pinnedCharts.length} pinned chart(s).`}
                </p>
              </div>

              {/* Messages */}
              <div className="min-h-[220px] max-h-[380px] overflow-y-auto px-4 py-3 space-y-3">
                {messages.length === 0 && (
                  <div className="text-center py-6 space-y-3">
                    <MessageCircle className="h-8 w-8 mx-auto text-muted-foreground/30" />
                    <p className="text-sm text-muted-foreground">Ask about your data</p>
                    <div className="space-y-2 text-xs">
                      {[
                        "What anomalies do you see in my data?",
                        "How does my sample compare to typical EV size ranges?",
                        "What do my pinned charts tell me?",
                        "Which parameters should I investigate further?",
                      ].map((q, i) => (
                        <div
                          key={i}
                          onClick={() => setQuestion(q)}
                          className="cursor-pointer text-primary/70 hover:text-primary transition-colors"
                        >
                          → {q}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {messages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div
                      className={`max-w-[85%] rounded-lg px-3 py-2 text-sm leading-relaxed ${
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-foreground"
                      }`}
                    >
                      {msg.content}
                    </div>
                  </div>
                ))}

                {qaLoading && (
                  <div className="flex justify-start">
                    <div className="bg-muted rounded-lg px-3 py-2">
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    </div>
                  </div>
                )}
              </div>

              {/* Input */}
              <div className="px-4 py-3 border-t flex gap-2">
                <input
                  type="text"
                  value={question}
                  onChange={e => setQuestion(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && !e.shiftKey && handleAsk()}
                  placeholder="Ask about your data..."
                  disabled={qaLoading}
                  className="flex-1 text-sm bg-muted/40 rounded-md px-3 py-2 outline-none focus:ring-1 focus:ring-ring placeholder:text-muted-foreground/50"
                />
                <Button
                  size="sm"
                  onClick={handleAsk}
                  disabled={!question.trim() || qaLoading}
                  className="px-3"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
