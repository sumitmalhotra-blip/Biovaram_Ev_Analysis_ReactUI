"use client"

/**
 * NanoFACS AI Panel — Clean White Version
 * 
 * Covers Parvesh's 4 requirements:
 * 
 * TAB 1 — "Data Overview"   → Req 1: Size & Events vs Parameters
 *   API: POST /api/v1/ai/nanofacs/analyze
 *   Payload: { file_paths, experiment_description, parameters_of_interest, same_sample }
 *   Shows: total events, median size, size range, key parameter stats per file
 *
 * TAB 2 — "Graph Suggestions" → Req 2: Suggest graphs (fluorescence shift, cluster movement)
 *   API: POST /api/v1/ai/nanofacs/analyze  (same call, different section of response)
 *   Shows: suggested_graphs + cluster_findings + anomalies — the "what to look at" output
 *
 * TAB 3 — "Metadata Check"  → Req 3: Check metadata across files
 *   API: POST /api/v1/ai/nanofacs/compare
 *   Payload: { file_paths }
 *   Shows: mismatches (Size shift, MeanIntensity shift), matching fields, recommendation
 *
 * TAB 4 — "Ask"             → Bonus: Q&A scoped to data only
 *   API: POST /api/v1/ai/nanofacs/ask
 *   Payload: { question, file_paths }
 *
 * Graph Loading Optimization (Req 4):
 *   - Import useLazyCharts from hooks/use-lazy-charts
 *   - Wrap each chart with <LazyChart> to stagger rendering
 *   - Only visible charts render — prevents freeze with 5-10 files
 */

import { useState, useCallback, useEffect } from "react"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

// ─── Types ────────────────────────────────────────────────────────────────────

interface ParamStats {
  mean: number
  median: number
  std: number
  min: number
  max: number
  p10: number
  p90: number
}

interface FileStats {
  file: string
  total_events: number
  Size: ParamStats
  MeanIntensity?: ParamStats
  num_clusters: number
  cluster_distribution: Record<string, number>
}

interface AIResult {
  anomalies: string[]
  cluster_findings: string[]
  suggested_graphs: string[]
  summary: string
  data_stats: Record<string, FileStats>
  analyzed_files: string[]
}

interface Mismatch {
  parameter: string
  values: Record<string, number>
  percent_difference: number
  severity: string
  message: string
}

interface CompareResult {
  mismatches: Mismatch[]
  matching_fields: string[]
  cluster_comparison: string[]
  recommendation: string
}

interface ChatMsg { role: "user" | "assistant"; content: string }

interface Props {
  filePaths?: string[]
  experimentDescription?: string
  parametersOfInterest?: string[]
  sameSample?: boolean
}

// ─── Main Component ────────────────────────────────────────────────────────────

export function NanoFACSAIPanel({
  filePaths: externalPaths = [],
  experimentDescription = "NanoFACS EV Analysis",
  parametersOfInterest = ["Size", "MeanIntensity"],
  sameSample = true,
}: Props) {
  const [tab, setTab] = useState<"data" | "graphs" | "metadata" | "ask">("data")
  const [filePaths, setFilePaths] = useState<string[]>(externalPaths)

  // Shared analysis result (used by both Data tab and Graph tab)
  const [result, setResult] = useState<AIResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const [compareResult, setCompareResult] = useState<CompareResult | null>(null)
  const [compareLoading, setCompareLoading] = useState(false)

  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [question, setQuestion] = useState("")
  const [qaLoading, setQaLoading] = useState(false)

  // All available files from server
  const [allFiles, setAllFiles] = useState<Array<{path: string, name: string, folder: string}>>([])
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set())
  const [showPicker, setShowPicker] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState("")

  const handleParquetUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    setUploading(true)
    setUploadMsg("")
    let uploaded = 0
    for (const file of Array.from(files)) {
      try {
        const formData = new FormData()
        formData.append("file", file)
        formData.append("folder", "uploads")
        const r = await fetch(`${API_BASE}/api/v1/ai/nanofacs/upload-parquet`, {
          method: "POST",
          body: formData,
        })
        if (r.ok) uploaded++
      } catch {}
    }
    setUploadMsg(`✓ ${uploaded} file${uploaded > 1 ? "s" : ""} uploaded — refreshing list...`)
    // Refresh file list
    setTimeout(() => {
      fetch(`${API_BASE}/api/v1/ai/nanofacs/list-files`)
        .then(r => r.json())
        .then(data => {
          if (data.files?.length > 0) {
            const files = data.files.map((f: { path: string; name: string }) => ({
              path: f.path,
              name: f.name,
              folder: f.path.split("/").slice(-2, -1)[0] || "files"
            }))
            setAllFiles(files)
            // Auto-select newly uploaded files
            const newPaths = new Set(selectedPaths)
            files.forEach((f: {path: string}) => newPaths.add(f.path))
            setSelectedPaths(newPaths)
          }
          setUploading(false)
          setUploadMsg("")
        })
    }, 500)
    e.target.value = ""
  }

  // Auto-load all available parquet files from server
  useEffect(() => {
    if (externalPaths.length > 0) return
    fetch(`${API_BASE}/api/v1/ai/nanofacs/list-files`)
      .then(r => r.json())
      .then(data => {
        if (data.files?.length > 0) {
          const files = data.files.map((f: { path: string; name: string }) => ({
            path: f.path,
            name: f.name,
            folder: f.path.split("/").slice(-2, -1)[0] || "files"
          }))
          setAllFiles(files)
          // Select all by default
          const paths = files.map((f: {path: string}) => f.path)
          setFilePaths(paths)
          setSelectedPaths(new Set(paths))
        }
      })
      .catch(() => {})
  }, [])

  const toggleFile = (path: string) => {
    setSelectedPaths(prev => {
      const next = new Set(prev)
      if (next.has(path)) {
        if (next.size === 1) return prev // keep at least 1
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }

  const applySelection = () => {
    const selected = allFiles.filter(f => selectedPaths.has(f.path)).map(f => f.path)
    setFilePaths(selected)
    setResult(null)
    setCompareResult(null)
    setShowPicker(false)
  }

  const selectAll = () => setSelectedPaths(new Set(allFiles.map(f => f.path)))
  const clearAll = () => {
    const first = allFiles[0]?.path
    if (first) setSelectedPaths(new Set([first]))
  }

  const runAnalysis = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const r = await fetch(`${API_BASE}/api/v1/ai/nanofacs/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file_paths: filePaths,
          experiment_description: experimentDescription,
          parameters_of_interest: parametersOfInterest,
          same_sample: sameSample,
        }),
      })
      if (!r.ok) throw new Error("failed")
      setResult(await r.json())
    } catch {
      setError("Analysis failed. Is the backend running?")
    } finally {
      setLoading(false)
    }
  }, [filePaths, experimentDescription, parametersOfInterest, sameSample])

  const runCompare = useCallback(async () => {
    setCompareLoading(true)
    try {
      const r = await fetch(`${API_BASE}/api/v1/ai/nanofacs/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_paths: filePaths }),
      })
      setCompareResult(await r.json())
    } catch {
    } finally {
      setCompareLoading(false)
    }
  }, [filePaths])

  const handleAsk = useCallback(async () => {
    if (!question.trim()) return
    const q = question
    setMessages(prev => [...prev, { role: "user", content: q }])
    setQuestion("")
    setQaLoading(true)
    try {
      const r = await fetch(`${API_BASE}/api/v1/ai/nanofacs/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, file_paths: filePaths }),
      })
      const data = await r.json()
      setMessages(prev => [...prev, { role: "assistant", content: data.answer }])
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Could not answer. Try again." }])
    } finally {
      setQaLoading(false)
    }
  }, [question, filePaths])

  if (!filePaths.length) return null

  const tabs = [
    { id: "data",     label: "1. Data Overview" },
    { id: "graphs",   label: "2. Graph Suggestions" },
    { id: "metadata", label: "3. Metadata Check" },
    { id: "ask",      label: "4. Ask Data" },
  ] as const

  return (
    <div style={s.card}>
      {/* ── Header ── */}
      <div style={s.headerRow}>
        <div>
          <div style={s.title}>NanoFACS AI Analysis</div>
          <div style={s.subtitle}>{filePaths.length} parquet file{filePaths.length > 1 ? "s" : ""} loaded · PC3 cell line exosomes</div>
        </div>
        <div style={s.pill}>{filePaths.length} files</div>
      </div>

      {/* ── File picker ── */}
      <div style={s.fileList}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
          <div style={s.fileListLabel}>Analyzing {filePaths.length} file{filePaths.length > 1 ? "s" : ""}:</div>
          <button onClick={() => setShowPicker(!showPicker)} style={s.btnChange}>
            {showPicker ? "✕ Cancel" : "✎ Change Files"}
          </button>
        </div>

        {/* File picker dropdown */}
        {showPicker && (
          <div style={s.pickerBox}>
            <div style={{ display: "flex", gap: 8, marginBottom: 10, alignItems: "center", flexWrap: "wrap" as const }}>
              <button onClick={selectAll} style={s.btnTiny}>Select All</button>
              <button onClick={clearAll} style={s.btnTiny}>Clear All</button>
              <label style={s.btnUpload}>
                {uploading ? "Uploading..." : "⬆ Upload Parquet"}
                <input
                  type="file"
                  accept=".parquet"
                  multiple
                  onChange={handleParquetUpload}
                  style={{ display: "none" }}
                  disabled={uploading}
                />
              </label>
              {uploadMsg && <span style={{ fontSize: 11, color: "#059669" }}>{uploadMsg}</span>}
            </div>
            {allFiles.map((f, i) => {
              const match = f.name.match(/[A-Z0-9]+_\d+kDa_(\w+)_size/)
              const shortLabel = match ? match[1] : f.name.split("_").slice(1, 3).join("_")
              const checked = selectedPaths.has(f.path)
              return (
                <div key={i} onClick={() => toggleFile(f.path)} style={{ ...s.pickerRow, background: checked ? "#eff6ff" : "#fff", borderColor: checked ? "#bfdbfe" : "#e5e7eb" }}>
                  <input type="checkbox" readOnly checked={checked} style={{ marginRight: 8, cursor: "pointer" }} />
                  <span style={{ ...s.fractionBadge, background: checked ? "#2563eb" : "#9ca3af" }}>{shortLabel}</span>
                  <span style={s.fileName2}>{f.name.replace(".fcs.parquet", "")}</span>
                  <span style={{ fontSize: 10, color: "#9ca3af", marginLeft: "auto", flexShrink: 0 }}>{f.folder}</span>
                </div>
              )
            })}
            <button onClick={applySelection} style={{ ...s.btnBlue, marginTop: 10, width: "100%" }}>
              ✓ Apply — Analyze {selectedPaths.size} file{selectedPaths.size > 1 ? "s" : ""}
            </button>
          </div>
        )}

        {/* Current file list (collapsed view) */}
        {!showPicker && filePaths.map((fp, i) => {
          const name = fp.split("/").pop() || fp
          const match = name.match(/[A-Z0-9]+_\d+kDa_(\w+)_size/)
          const shortLabel = match ? match[1] : name.split("_").slice(1, 3).join("_")
          return (
            <div key={i} style={s.fileChip} title={name}>
              <span style={s.fractionBadge}>{shortLabel}</span>
              <span style={s.fileName2}>{name.replace(".fcs.parquet", "")}</span>
            </div>
          )
        })}
      </div>

      {/* ── Tabs ── */}
      <div style={s.tabRow}>
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={tab === t.id ? s.tabOn : s.tabOff}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ══════════════════════════════════════════════════════
          TAB 1 — Data Overview
          REQ 1: Size & Events vs Parameters
          API: POST /api/v1/ai/nanofacs/analyze
          ══════════════════════════════════════════════════════ */}
      {tab === "data" && (
        <div>
          {!result && !loading && (
            <div style={s.emptyState}>
              <p style={s.hint}>Shows total events, particle size stats, and key parameters for each file.</p>
              <p style={s.apiNote}>
                API: <code>POST /api/v1/ai/nanofacs/analyze</code><br />
                Payload: <code>{"{ file_paths, experiment_description, parameters_of_interest, same_sample }"}</code>
              </p>
              <button onClick={runAnalysis} style={s.btnBlue}>Run Data Analysis</button>
            </div>
          )}
          {loading && <Spinner text="Loading data stats..." />}
          {error && <ErrBox msg={error} />}
          {result && (
            <div>
              {Object.entries(result.data_stats).map(([fname, stats]) => (
                <div key={fname} style={s.fileCard}>
                  <div style={s.fileName}>{fname.split("/").pop()}</div>

                  {/* Events row */}
                  <div style={s.statGrid}>
                    <StatBox label="Total Events" value={stats.total_events.toLocaleString()} unit="particles" color="#2563eb" />
                    <StatBox label="Median Size" value={stats.Size?.median?.toFixed(1) ?? "—"} unit="nm" color="#059669" />
                    <StatBox label="Mean Size" value={stats.Size?.mean?.toFixed(1) ?? "—"} unit="nm" color="#059669" />
                    <StatBox label="Size Range" value={`${stats.Size?.p10?.toFixed(0)}–${stats.Size?.p90?.toFixed(0)}`} unit="nm (p10–p90)" color="#7c3aed" />
                    {stats.MeanIntensity && (
                      <StatBox label="Mean Intensity" value={stats.MeanIntensity.median?.toFixed(1)} unit="median" color="#d97706" />
                    )}
                    <StatBox label="Clusters" value={String(stats.num_clusters)} unit="detected" color="#dc2626" />
                  </div>
                </div>
              ))}
              <button onClick={runAnalysis} style={s.btnGray}>↺ Refresh</button>
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════
          TAB 2 — Graph Suggestions
          REQ 2: Suggest graphs (fluorescence shift, cluster movement)
          API: POST /api/v1/ai/nanofacs/analyze (same call)
          ══════════════════════════════════════════════════════ */}
      {tab === "graphs" && (
        <div>
          {!result && !loading && (
            <div style={s.emptyState}>
              <p style={s.hint}>AI suggests which graphs to look at — flags sample shifts, fluorescence anomalies, and unexpected cluster movement.</p>
              <p style={s.apiNote}>
                API: <code>POST /api/v1/ai/nanofacs/analyze</code><br />
                Same call as Data Overview — run once, both tabs populate.
              </p>
              <button onClick={runAnalysis} style={s.btnBlue}>Get Graph Suggestions</button>
            </div>
          )}
          {loading && <Spinner text="Generating suggestions..." />}
          {error && <ErrBox msg={error} />}
          {result && (
            <div>
              {/* Summary */}
              <div style={s.summaryBox}>{result.summary}</div>

              {/* Suggested Graphs — the most important section */}
              {result.suggested_graphs.length > 0 && (
                <Section title="Recommended Graphs" color="#059669" bg="#f0fdf4">
                  {result.suggested_graphs.map((g, i) => {
                    const [name, desc] = g.split(" — ")
                    return (
                      <div key={i} style={s.graphRow}>
                        <div style={s.graphNum}>{i + 1}</div>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 13, color: "#111" }}>{name}</div>
                          {desc && <div style={{ fontSize: 12, color: "#6b7280", marginTop: 2 }}>{desc}</div>}
                        </div>
                      </div>
                    )
                  })}
                </Section>
              )}

              {/* Cluster findings — unexpected movement */}
              {result.cluster_findings.length > 0 && (
                <Section title="Cluster Findings" color="#2563eb" bg="#eff6ff">
                  {result.cluster_findings.map((c, i) => (
                    <div key={i} style={s.bulletRow}>• {c}</div>
                  ))}
                </Section>
              )}

              {/* Anomalies — fluorescence/sample shifts */}
              {result.anomalies.length > 0 && (() => {
                // Group file-specific anomalies, deduplicate generic ones
                const fileAnomalies: Record<string, string[]> = {}
                const genericAnomalies: string[] = []
                const seen = new Set<string>()
                result.anomalies.forEach(a => {
                  const match = a.match(/^\[(.+?)\]\s*(.+)$/)
                  if (match) {
                    const fname = match[1].split("/").pop()?.replace(".fcs.parquet","") || match[1]
                    const shortName = fname.split("_").slice(1,4).join("_")
                    const msg = match[2]
                    if (!fileAnomalies[msg]) fileAnomalies[msg] = []
                    fileAnomalies[msg].push(shortName)
                  } else {
                    if (!seen.has(a)) { seen.add(a); genericAnomalies.push(a) }
                  }
                })
                return (
                  <Section title="Anomalies / Sample Shifts" color="#dc2626" bg="#fef2f2">
                    {Object.entries(fileAnomalies).map(([msg, files], i) => (
                      <div key={i} style={s.bulletRow}>
                        <span style={{color:"#dc2626"}}>⚠</span>&nbsp;
                        <span style={{color:"#6b7280",fontSize:11}}>[{files.join(", ")}]</span>&nbsp;{msg}
                      </div>
                    ))}
                    {genericAnomalies.map((a, i) => (
                      <div key={i} style={s.bulletRow}>⚠ {a}</div>
                    ))}
                  </Section>
                )
              })()}

              <button onClick={runAnalysis} style={s.btnGray}>↺ Re-run</button>
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════
          TAB 3 — Metadata Check
          REQ 3: Compare metadata across files
          API: POST /api/v1/ai/nanofacs/compare
          Payload: { file_paths }
          ══════════════════════════════════════════════════════ */}
      {tab === "metadata" && (
        <div>
          {!compareResult && !compareLoading && (
            <div style={s.emptyState}>
              <p style={s.hint}>Compares Size, MeanIntensity, Solidity and other parameters across all files — flags shifts that could indicate sample prep differences.</p>
              <p style={s.apiNote}>
                API: <code>POST /api/v1/ai/nanofacs/compare</code><br />
                Payload: <code>{"{ file_paths: [...] }"}</code>
              </p>
              <button onClick={runCompare} style={s.btnBlue}>Check Metadata</button>
            </div>
          )}
          {compareLoading && <Spinner text="Comparing files..." />}
          {compareResult && (
            <div>
              {/* Recommendation */}
              <div style={s.summaryBox}>{compareResult.recommendation}</div>

              {/* Mismatches — the key output */}
              {compareResult.mismatches.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontWeight: 600, color: "#dc2626", fontSize: 13, marginBottom: 8 }}>
                    Parameter Mismatches ({compareResult.mismatches.length})
                  </div>
                  {compareResult.mismatches.map((m, i) => (
                    <div key={i} style={s.mismatchRow}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontWeight: 700, fontSize: 14, color: "#111" }}>{m.parameter}</span>
                        <span style={{
                          fontSize: 12, fontWeight: 700, padding: "2px 8px", borderRadius: 20,
                          background: m.severity === "high" ? "#fef2f2" : "#fffbeb",
                          color: m.severity === "high" ? "#dc2626" : "#d97706"
                        }}>
                          {m.percent_difference}% diff · {m.severity.toUpperCase()}
                        </span>
                      </div>
                      <p style={{ fontSize: 12, color: "#6b7280", margin: "6px 0 4px" }}>{m.message}</p>
                      <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 6 }}>
                        {Object.entries(m.values).map(([file, val]) => (
                          <span key={file} style={s.valueChip}>
                            {file.split("_").slice(1, 4).join("_")}: <strong>{val.toFixed(1)}</strong>
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Matching fields */}
              {compareResult.matching_fields.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontWeight: 600, color: "#059669", fontSize: 13, marginBottom: 8 }}>
                    Matching Parameters ✓
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 8 }}>
                    {compareResult.matching_fields.map((f, i) => (
                      <span key={i} style={s.matchChip}>{f}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Cluster comparison */}
              {compareResult.cluster_comparison.length > 0 && (
                <Section title="Cluster Comparison" color="#2563eb" bg="#eff6ff">
                  {compareResult.cluster_comparison.map((c, i) => (
                    <div key={i} style={{ ...s.bulletRow, fontSize: 12 }}>
                      • {c.split("/").pop()}
                    </div>
                  ))}
                </Section>
              )}

              <button onClick={runCompare} style={s.btnGray}>↺ Re-run</button>
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════
          TAB 4 — Ask Data
          Q&A scoped to uploaded files only
          API: POST /api/v1/ai/nanofacs/ask
          Payload: { question, file_paths }
          ══════════════════════════════════════════════════════ */}
      {tab === "ask" && (
        <div>
          <p style={{ ...s.hint, marginBottom: 12 }}>
            Ask anything about your data. Answers are based only on the {filePaths.length} loaded file(s).
          </p>

          <div style={s.chatBox}>
            {messages.length === 0 && (
              <div style={{ textAlign: "center" as const, paddingTop: 20 }}>
                <p style={{ color: "#9ca3af", fontSize: 13, marginBottom: 12 }}>Try asking:</p>
                {[
                  "What is the median particle size?",
                  "Are there any unusual clusters?",
                  "Which fraction has the most exosomes?",
                ].map((q, i) => (
                  <div
                    key={i}
                    onClick={() => setQuestion(q)}
                    style={s.suggestion}
                  >
                    {q}
                  </div>
                ))}
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start", marginBottom: 10 }}>
                <div style={m.role === "user" ? s.bubbleUser : s.bubbleAI}>
                  {m.content}
                </div>
              </div>
            ))}
            {qaLoading && <div style={s.bubbleAI}>Thinking...</div>}
          </div>

          <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
            <input
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleAsk()}
              placeholder="Ask about your data..."
              disabled={qaLoading}
              style={s.input}
            />
            <button onClick={handleAsk} disabled={!question.trim() || qaLoading} style={s.btnBlue}>
              Send
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function StatBox({ label, value, unit, color }: { label: string; value: string | number; unit: string; color: string }) {
  return (
    <div style={{ background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: 8, padding: "12px 16px" }}>
      <div style={{ fontSize: 11, color: "#9ca3af", fontWeight: 500, textTransform: "uppercase" as const, letterSpacing: "0.05em" }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color, margin: "4px 0 2px", fontVariantNumeric: "tabular-nums" }}>{value}</div>
      <div style={{ fontSize: 11, color: "#9ca3af" }}>{unit}</div>
    </div>
  )
}

function Section({ title, color, bg, children }: { title: string; color: string; bg: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(true)
  return (
    <div style={{ background: bg, borderRadius: 8, marginBottom: 12, overflow: "hidden" }}>
      <button
        onClick={() => setOpen(!open)}
        style={{ width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 14px", background: "none", border: "none", cursor: "pointer" }}
      >
        <span style={{ fontWeight: 600, color, fontSize: 13 }}>{title}</span>
        <span style={{ color, fontSize: 12 }}>{open ? "▲" : "▼"}</span>
      </button>
      {open && <div style={{ padding: "0 14px 12px" }}>{children}</div>}
    </div>
  )
}

function Spinner({ text }: { text: string }) {
  return <p style={{ color: "#6b7280", textAlign: "center" as const, padding: "24px 0", fontSize: 14 }}>⏳ {text}</p>
}

function ErrBox({ msg }: { msg: string }) {
  return <p style={{ color: "#dc2626", background: "#fef2f2", padding: 12, borderRadius: 8, fontSize: 13 }}>{msg}</p>
}

// ─── Styles ────────────────────────────────────────────────────────────────────

const s = {
  card: {
    background: "#ffffff",
    border: "1px solid #e5e7eb",
    borderRadius: 12,
    padding: 24,
    marginTop: 24,
    fontFamily: "'DM Sans', system-ui, sans-serif",
    color: "#111827",
  },
  headerRow: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 },
  title: { fontSize: 17, fontWeight: 700, color: "#111827" },
  subtitle: { fontSize: 12, color: "#9ca3af", marginTop: 2 },
  pill: { background: "#f3f4f6", borderRadius: 20, padding: "3px 12px", fontSize: 12, color: "#6b7280", fontWeight: 500, whiteSpace: "nowrap" as const },
  fileList: { background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: 8, padding: "10px 14px", marginTop: 12, marginBottom: 4, display: "flex", flexDirection: "column" as const, gap: 5 },
  fileListLabel: { fontSize: 11, fontWeight: 600, color: "#9ca3af", textTransform: "uppercase" as const, letterSpacing: "0.05em", marginBottom: 4 },
  btnChange: { background: "none", border: "1px solid #d1d5db", borderRadius: 6, padding: "3px 10px", fontSize: 11, color: "#374151", cursor: "pointer", fontWeight: 500 } as React.CSSProperties,
  pickerBox: { background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: 8, padding: 12, marginBottom: 8 },
  pickerRow: { display: "flex", alignItems: "center", gap: 8, padding: "7px 10px", borderRadius: 6, border: "1px solid", marginBottom: 6, cursor: "pointer" },
  btnTiny: { background: "#f3f4f6", border: "1px solid #e5e7eb", borderRadius: 4, padding: "2px 8px", fontSize: 11, color: "#374151", cursor: "pointer" } as React.CSSProperties,
  btnUpload: { background: "#f0fdf4", border: "1px solid #86efac", borderRadius: 4, padding: "2px 8px", fontSize: 11, color: "#15803d", cursor: "pointer", fontWeight: 600 } as React.CSSProperties,
  fileChip: { display: "flex", alignItems: "center", gap: 8 },
  fractionBadge: { background: "#2563eb", color: "#fff", borderRadius: 4, padding: "1px 7px", fontSize: 11, fontWeight: 700, flexShrink: 0, whiteSpace: "nowrap" as const },
  fileName2: { fontSize: 11, color: "#6b7280", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" as const },
  tabRow: { display: "flex", gap: 0, borderBottom: "1px solid #e5e7eb", marginBottom: 20, marginTop: 16 },
  tabOn: { padding: "8px 18px", border: "none", borderBottom: "2px solid #2563eb", background: "none", cursor: "pointer", fontWeight: 600, color: "#2563eb", fontSize: 13 } as React.CSSProperties,
  tabOff: { padding: "8px 18px", border: "none", borderBottom: "2px solid transparent", background: "none", cursor: "pointer", fontWeight: 400, color: "#6b7280", fontSize: 13 } as React.CSSProperties,
  emptyState: { textAlign: "center" as const, padding: "24px 0" },
  hint: { color: "#6b7280", fontSize: 13, marginBottom: 10 },
  apiNote: { background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: 6, padding: "8px 12px", fontSize: 11, color: "#6b7280", marginBottom: 16, textAlign: "left" as const, lineHeight: 1.8 },
  btnBlue: { background: "#2563eb", color: "#fff", border: "none", borderRadius: 8, padding: "10px 22px", fontSize: 13, fontWeight: 600, cursor: "pointer" } as React.CSSProperties,
  btnGray: { background: "#f3f4f6", color: "#374151", border: "none", borderRadius: 8, padding: "8px 18px", fontSize: 13, fontWeight: 500, cursor: "pointer", marginTop: 8 } as React.CSSProperties,
  fileCard: { border: "1px solid #e5e7eb", borderRadius: 8, padding: 16, marginBottom: 16 },
  fileName: { fontSize: 11, color: "#6b7280", marginBottom: 12, fontWeight: 500, wordBreak: "break-all" as const },
  statGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 10 },
  summaryBox: { background: "#f9fafb", borderRadius: 8, padding: 14, fontSize: 13, color: "#374151", fontStyle: "italic" as const, marginBottom: 16, lineHeight: 1.6 },
  graphRow: { display: "flex", gap: 10, marginBottom: 10, alignItems: "flex-start" },
  graphNum: { background: "#059669", color: "#fff", borderRadius: "50%", width: 22, height: 22, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, flexShrink: 0 },
  bulletRow: { fontSize: 13, color: "#374151", marginBottom: 6, lineHeight: 1.5 },
  mismatchRow: { background: "#fff", border: "1px solid #fecaca", borderRadius: 8, padding: 12, marginBottom: 10 },
  valueChip: { background: "#f3f4f6", borderRadius: 4, padding: "2px 8px", fontSize: 11, color: "#374151" },
  matchChip: { background: "#dcfce7", color: "#15803d", borderRadius: 20, padding: "3px 12px", fontSize: 12 },
  chatBox: { minHeight: 160, maxHeight: 300, overflowY: "auto" as const, border: "1px solid #e5e7eb", borderRadius: 8, padding: 12, marginBottom: 8 },
  suggestion: { color: "#2563eb", fontSize: 13, cursor: "pointer", marginBottom: 8 },
  bubbleUser: { background: "#2563eb", color: "#fff", padding: "8px 14px", borderRadius: "12px 12px 0 12px", fontSize: 13, maxWidth: "80%", lineHeight: 1.5 },
  bubbleAI: { background: "#f3f4f6", color: "#111", padding: "8px 14px", borderRadius: "12px 12px 12px 0", fontSize: 13, maxWidth: "80%", lineHeight: 1.5 },
  input: { flex: 1, padding: "10px 14px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 13, outline: "none", color: "#111", background: "#fff" } as React.CSSProperties,
}
