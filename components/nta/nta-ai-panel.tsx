"use client"

import { useEffect, useMemo, useState } from "react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Checkbox } from "@/components/ui/checkbox"
import { ScrollArea } from "@/components/ui/scroll-area"

import { getApiBaseUrl } from "@/lib/module-config"
import { useAnalysisStore } from "@/lib/store"

type NTAHealthResponse =
  | {
      status: "ok"
      provider: string
      model: string
      region: string
    }
  | {
      status: "error"
      message: string
    }

type NTAAnalyzeResponse = {
  anomalies: string[]
  missed_parameters: string[]
  suggestions: string[]
  summary: string
  analyzed_samples: string[]
  analyzed_at: string
}

type NTAMetadataCompareResponse = {
  mismatches: Array<{
    field: string
    values: Record<string, unknown>
    difference: unknown
    tolerance: unknown
    severity: string
    message: string
  }>
  matching_fields: string[]
  recommendation: string
  compared_samples: string[]
}

let API_BASE = getApiBaseUrl()
if (API_BASE.endsWith("/api/v1")) {
  API_BASE = API_BASE.replace(/\/api\/v1$/, "")
}

export function NTAAIPanel({ sampleId }: { sampleId?: string }) {
  const apiConnected = useAnalysisStore((s) => s.apiConnected)
  const apiSamples = useAnalysisStore((s) => s.apiSamples)

  const availableNtaSampleIds = useMemo(() => {
    return apiSamples.filter((s) => s.files?.nta).map((s) => s.sample_id)
  }, [apiSamples])

  const [bedrockHealth, setBedrockHealth] = useState<NTAHealthResponse | null>(null)

  const [experimentDescription, setExperimentDescription] = useState("NTA EV Analysis")
  const [sameSample, setSameSample] = useState(true)
  const [parametersOfInterestCsv, setParametersOfInterestCsv] = useState("50-80nm, 80-100nm")
  const [additionalNotes, setAdditionalNotes] = useState("")

  const [selectedSampleIds, setSelectedSampleIds] = useState<string[]>(() => (sampleId ? [sampleId] : []))

  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [analysisResult, setAnalysisResult] = useState<NTAAnalyzeResponse | null>(null)

  const [compareLoading, setCompareLoading] = useState(false)
  const [compareError, setCompareError] = useState<string | null>(null)
  const [compareResult, setCompareResult] = useState<NTAMetadataCompareResponse | null>(null)

  useEffect(() => {
    if (!sampleId) return
    setSelectedSampleIds((prev) => {
      if (prev.includes(sampleId)) return prev
      return [sampleId, ...prev].slice(0, 20)
    })
  }, [sampleId])

  useEffect(() => {
    let cancelled = false

    fetch(`${API_BASE}/api/v1/ai/nta/health`)
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return
        setBedrockHealth(data)
      })
      .catch((err) => {
        if (cancelled) return
        setBedrockHealth({ status: "error", message: err instanceof Error ? err.message : "Health check failed" })
      })

    return () => {
      cancelled = true
    }
  }, [])

  const toggleSample = (id: string) => {
    setSelectedSampleIds((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
      // keep at least one selected if possible
      if (next.length === 0 && prev.length > 0) return prev
      return next.slice(0, 20)
    })
  }

  const parametersOfInterest = useMemo(() => {
    return parametersOfInterestCsv
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .slice(0, 20)
  }, [parametersOfInterestCsv])

  const runAnalysis = async () => {
    setAnalysisLoading(true)
    setAnalysisError(null)
    setAnalysisResult(null)

    try {
      const payload = {
        experiment_description: experimentDescription.trim() || "NTA EV Analysis",
        same_sample: sameSample,
        parameters_of_interest: parametersOfInterest,
        sample_ids: selectedSampleIds,
        additional_notes: additionalNotes.trim() || null,
      }

      const r = await fetch(`${API_BASE}/api/v1/ai/nta/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })

      if (!r.ok) {
        const err = await r.json().catch(() => null)
        throw new Error(err?.detail || `Request failed with status ${r.status}`)
      }

      const data = (await r.json()) as NTAAnalyzeResponse
      setAnalysisResult(data)
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : "AI analysis failed")
    } finally {
      setAnalysisLoading(false)
    }
  }

  const runCompare = async () => {
    setCompareLoading(true)
    setCompareError(null)
    setCompareResult(null)

    try {
      if (selectedSampleIds.length < 2) {
        throw new Error("Select at least 2 samples to compare metadata.")
      }

      const r = await fetch(`${API_BASE}/api/v1/ai/nta/compare-metadata`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sample_ids: selectedSampleIds }),
      })

      if (!r.ok) {
        const err = await r.json().catch(() => null)
        throw new Error(err?.detail || `Request failed with status ${r.status}`)
      }

      const data = (await r.json()) as NTAMetadataCompareResponse
      setCompareResult(data)
    } catch (err) {
      setCompareError(err instanceof Error ? err.message : "Metadata compare failed")
    } finally {
      setCompareLoading(false)
    }
  }

  return (
    <Card className="card-3d">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2">
          <div>
            <CardTitle className="text-base md:text-lg">NTA AI</CardTitle>
            <p className="text-sm text-muted-foreground">
              Anomaly detection, missed parameters, and metadata consistency checks.
            </p>
          </div>
          <div className="flex flex-col items-end gap-1">
            {!apiConnected ? (
              <Badge variant="destructive">Offline</Badge>
            ) : bedrockHealth?.status === "ok" ? (
              <Badge variant="secondary">Bedrock: connected</Badge>
            ) : bedrockHealth?.status === "error" ? (
              <Badge variant="outline">Bedrock: not configured</Badge>
            ) : (
              <Badge variant="outline">Bedrock: checking…</Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {!apiConnected && (
          <Alert variant="destructive">
            <AlertTitle>Backend Offline</AlertTitle>
            <AlertDescription>Start the backend to use NTA AI endpoints.</AlertDescription>
          </Alert>
        )}

        <div className="grid gap-3 md:grid-cols-2">
          <div className="space-y-2">
            <Label>Experiment description</Label>
            <Textarea
              value={experimentDescription}
              onChange={(e) => setExperimentDescription(e.target.value)}
              placeholder="e.g., EV from plasma, CD81 marker, focusing on small exosomes"
              rows={3}
            />
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <Label>Same sample across runs</Label>
              <Switch checked={sameSample} onCheckedChange={setSameSample} />
            </div>
            <div className="space-y-2">
              <Label>Parameters of interest (comma-separated)</Label>
              <Input
                value={parametersOfInterestCsv}
                onChange={(e) => setParametersOfInterestCsv(e.target.value)}
                placeholder="50-80nm, 80-100nm"
              />
            </div>
            <div className="space-y-2">
              <Label>Additional notes (optional)</Label>
              <Textarea
                value={additionalNotes}
                onChange={(e) => setAdditionalNotes(e.target.value)}
                placeholder="Any sample prep notes, dilution, constraints…"
                rows={2}
              />
            </div>
          </div>
        </div> 

        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <Label>Select NTA samples (up to 20)</Label>
            {selectedSampleIds.length > 0 && (
              <Badge variant="secondary">Selected: {selectedSampleIds.length}</Badge>
            )}
          </div>

          <ScrollArea className="h-52 rounded-md border border-border/60 bg-background/40 p-2 pr-3">
            <div className="space-y-1">
              {availableNtaSampleIds.length === 0 ? (
                <p className="text-sm text-muted-foreground px-2 py-1">
                  No NTA samples found yet. Upload an NTA file first.
                </p>
              ) : (
                availableNtaSampleIds.map((id) => (
                  <label
                    key={id}
                    className="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-secondary/30 cursor-pointer"
                  >
                    <Checkbox checked={selectedSampleIds.includes(id)} onCheckedChange={() => toggleSample(id)} />
                    <span className="text-sm truncate flex-1">{id}</span>
                    {id === sampleId && <Badge variant="outline">Current</Badge>}
                  </label>
                ))
              )}
            </div>
          </ScrollArea>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button onClick={runAnalysis} disabled={!apiConnected || analysisLoading || selectedSampleIds.length === 0}>
            {analysisLoading ? "Analyzing…" : "Run AI Analysis"}
          </Button>
          <Button
            variant="outline"
            onClick={runCompare}
            disabled={!apiConnected || compareLoading || selectedSampleIds.length < 2}
          >
            {compareLoading ? "Comparing…" : "Compare Metadata"}
          </Button>
        </div>

        {analysisError && (
          <Alert variant="destructive">
            <AlertTitle>AI analysis failed</AlertTitle>
            <AlertDescription>{analysisError}</AlertDescription>
          </Alert>
        )}

        {analysisResult && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">Analyzed: {analysisResult.analyzed_samples?.length || 0}</Badge>
              {analysisResult.analyzed_at && <Badge variant="outline">{new Date(analysisResult.analyzed_at).toLocaleString()}</Badge>}
            </div>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">{analysisResult.summary}</p>
              </CardContent>
            </Card>

            <div className="grid gap-3 md:grid-cols-3">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Anomalies</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1">
                  {analysisResult.anomalies?.length ? (
                    analysisResult.anomalies.map((a, idx) => (
                      <p key={idx} className="text-sm text-muted-foreground">• {a}</p>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">None</p>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Missed parameters</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1">
                  {analysisResult.missed_parameters?.length ? (
                    analysisResult.missed_parameters.map((m, idx) => (
                      <p key={idx} className="text-sm text-muted-foreground">• {m}</p>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">None</p>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Suggestions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1">
                  {analysisResult.suggestions?.length ? (
                    analysisResult.suggestions.map((s, idx) => (
                      <p key={idx} className="text-sm text-muted-foreground">• {s}</p>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">None</p>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        {compareError && (
          <Alert variant="destructive">
            <AlertTitle>Metadata compare failed</AlertTitle>
            <AlertDescription>{compareError}</AlertDescription>
          </Alert>
        )}

        {compareResult && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Metadata compare</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">{compareResult.recommendation}</p>

              {compareResult.mismatches?.length ? (
                <div className="space-y-2">
                  {compareResult.mismatches.map((m, idx) => (
                    <div key={idx} className="rounded-md border border-border/60 p-2">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-medium truncate">{m.field}</p>
                        <Badge variant={m.severity === "high" ? "destructive" : "outline"}>{m.severity}</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1 whitespace-pre-wrap">{m.message}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No mismatches detected.</p>
              )}

              {compareResult.matching_fields?.length ? (
                <p className="text-sm text-muted-foreground">
                  Matching fields: {compareResult.matching_fields.join(", ")}
                </p>
              ) : null}
            </CardContent>
          </Card>
        )}
      </CardContent>
    </Card>
  )
}
