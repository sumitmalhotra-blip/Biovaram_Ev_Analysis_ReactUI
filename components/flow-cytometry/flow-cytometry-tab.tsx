"use client"

import { useEffect, useState } from "react"
import { FileUploadZone } from "./file-upload-zone"
import { DualFileUploadZone } from "./dual-file-upload-zone"
import { OverlayHistogramChart } from "./overlay-histogram-chart"
import { AnalysisResults } from "./analysis-results"
import { ComparisonAnalysisView } from "./comparison-analysis-view"
import { ColumnMapping } from "./column-mapping"
import { FCSBestPracticesGuide } from "./best-practices-guide"
import { NanoFACSAIPanel } from "./nanofacs-ai-panel"
import { BeadCalibrationPanel } from "./bead-calibration-panel"
import { ExperimentalConditionsDialog, type ExperimentalConditions, type FileMetadata } from "@/components/experimental-conditions-dialog"
import { useAnalysisStore } from "@/lib/store"
import { useShallow } from "zustand/shallow"
import { useApi } from "@/hooks/use-api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { AlertCircle, Loader2, Settings2, Layers, FileText, RotateCcw, FlaskConical, Brain } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { useToast } from "@/hooks/use-toast"

export function FlowCytometryTab() {
  const { fcsAnalysis, secondaryFcsAnalysis, overlayConfig, apiConnected, setFCSExperimentalConditions, sidebarCollapsed, resetFCSAnalysis } = useAnalysisStore(useShallow((s) => ({
    fcsAnalysis: s.fcsAnalysis,
    secondaryFcsAnalysis: s.secondaryFcsAnalysis,
    overlayConfig: s.overlayConfig,
    apiConnected: s.apiConnected,
    setFCSExperimentalConditions: s.setFCSExperimentalConditions,
    sidebarCollapsed: s.sidebarCollapsed,
    resetFCSAnalysis: s.resetFCSAnalysis,
  })))
  const { checkHealth } = useApi()
  const { toast } = useToast()
  const [showConditionsDialog, setShowConditionsDialog] = useState(false)
  const [justUploadedSampleId, setJustUploadedSampleId] = useState<string | null>(null)
  const [uploadMode, setUploadMode] = useState<"single" | "comparison">("single")

  // ── Main inner tab: FCS or NanoFACS AI ──
  const [mainTab, setMainTab] = useState<"fcs" | "ai">("fcs")

  useEffect(() => {
    checkHealth()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (fcsAnalysis.results && fcsAnalysis.sampleId && !fcsAnalysis.experimentalConditions) {
      setJustUploadedSampleId(fcsAnalysis.sampleId)
      setShowConditionsDialog(true)
    }
  }, [fcsAnalysis.results, fcsAnalysis.sampleId, fcsAnalysis.experimentalConditions])

  const handleSaveConditions = (conditions: ExperimentalConditions) => {
    setFCSExperimentalConditions(conditions)
    setShowConditionsDialog(false)
  }

  const handleResetTab = () => {
    resetFCSAnalysis()
    toast({
      title: "Tab Reset",
      description: "Analysis cleared. Upload a new file to start fresh.",
    })
  }

  const hasFile = fcsAnalysis.file !== null
  const isAnalyzing = fcsAnalysis.isAnalyzing || secondaryFcsAnalysis.isAnalyzing
  const hasResults = fcsAnalysis.results !== null
  const hasSecondaryResults = secondaryFcsAnalysis.results !== null
  const error = fcsAnalysis.error || secondaryFcsAnalysis.error

  return (
    <div className="p-4 md:p-6 space-y-4 md:space-y-6">

      {/* ── API offline warning ── */}
      {!apiConnected && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Backend Offline</AlertTitle>
          <AlertDescription>
            Cannot connect to the analysis backend. Please ensure the server is running.
          </AlertDescription>
        </Alert>
      )}

      {/* ══════════════════════════════════════════════════════
          MAIN INNER TABS — FCS Analysis | NanoFACS AI
          ══════════════════════════════════════════════════════ */}
      <div style={{
        display: "flex",
        gap: 0,
        borderBottom: "2px solid #e5e7eb",
        marginBottom: 8,
        background: "#fff",
        borderRadius: "10px 10px 0 0",
        overflow: "hidden",
        boxShadow: "0 1px 3px rgba(0,0,0,0.06)"
      }}>
        <button
          onClick={() => setMainTab("fcs")}
          style={{
            flex: 1,
            padding: "14px 24px",
            border: "none",
            borderBottom: mainTab === "fcs" ? "3px solid #2563eb" : "3px solid transparent",
            background: mainTab === "fcs" ? "#eff6ff" : "#f9fafb",
            cursor: "pointer",
            fontWeight: mainTab === "fcs" ? 700 : 400,
            color: mainTab === "fcs" ? "#2563eb" : "#6b7280",
            fontSize: 14,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            transition: "all 0.15s",
          }}
        >
          <span style={{ fontSize: 18 }}>🔬</span>
          FCS Analysis
          {hasResults && (
            <span style={{ background: "#2563eb", color: "#fff", borderRadius: 20, padding: "1px 8px", fontSize: 11, fontWeight: 700 }}>
              Live
            </span>
          )}
        </button>

        <button
          onClick={() => setMainTab("ai")}
          style={{
            flex: 1,
            padding: "14px 24px",
            border: "none",
            borderBottom: mainTab === "ai" ? "3px solid #7c3aed" : "3px solid transparent",
            background: mainTab === "ai" ? "#faf5ff" : "#f9fafb",
            cursor: "pointer",
            fontWeight: mainTab === "ai" ? 700 : 400,
            color: mainTab === "ai" ? "#7c3aed" : "#6b7280",
            fontSize: 14,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            transition: "all 0.15s",
          }}
        >
          <span style={{ fontSize: 18 }}>🧠</span>
          NanoFACS AI
          <span style={{ background: "#7c3aed", color: "#fff", borderRadius: 20, padding: "1px 8px", fontSize: 11, fontWeight: 700 }}>
            Parquet
          </span>
        </button>
      </div>

      {/* ══════════════════════════════════════════════════════
          TAB: FCS ANALYSIS
          - Upload FCS file
          - Charts: Size Distribution, Diameter vs SSC, etc.
          ══════════════════════════════════════════════════════ */}
      {mainTab === "fcs" && (
        <div className="space-y-4 md:space-y-6">

          {/* Best Practices Guide */}
          {!hasFile && !hasResults && <FCSBestPracticesGuide />}

          {/* Bead Calibration */}
          <BeadCalibrationPanel />

          {/* Upload Mode Toggle */}
          <Card className="card-3d">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <CardTitle className="text-base">Upload Mode</CardTitle>
                <div className="flex gap-2 flex-wrap">
                  <Button
                    variant={uploadMode === "single" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setUploadMode("single")}
                    className="gap-2"
                  >
                    <FileText className="h-4 w-4" />
                    Single File
                  </Button>
                  <Button
                    variant={uploadMode === "comparison" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setUploadMode("comparison")}
                    className="gap-2"
                  >
                    <Layers className="h-4 w-4" />
                    Compare Files
                  </Button>
                  {hasResults && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleResetTab}
                      className="gap-2 text-destructive hover:text-destructive hover:bg-destructive/10"
                    >
                      <RotateCcw className="h-4 w-4" />
                      Reset Tab
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
          </Card>

          {/* File Upload Zone */}
          {uploadMode === "single" ? <FileUploadZone /> : <DualFileUploadZone />}

          {/* Sidebar collapsed hint */}
          {hasFile && !isAnalyzing && sidebarCollapsed && (
            <Alert>
              <Settings2 className="h-4 w-4" />
              <AlertTitle>Analysis Settings</AlertTitle>
              <AlertDescription>
                Expand the sidebar to access analysis settings including optical parameters,
                angular ranges, anomaly detection, and size categories.
              </AlertDescription>
            </Alert>
          )}

          {/* Analyzing spinner */}
          {isAnalyzing && (
            <Card className="card-3d">
              <CardContent className="p-8 text-center">
                <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
                <p className="text-muted-foreground">Analyzing FCS file...</p>
                <p className="text-sm text-muted-foreground mt-2">
                  Parsing events, calculating statistics, and detecting anomalies
                </p>
              </CardContent>
            </Card>
          )}

          {/* Error */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Analysis Error</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {hasFile && !isAnalyzing && !hasResults && <ColumnMapping />}

          {/* Results / Charts */}
          {uploadMode === "single" && hasResults && <AnalysisResults />}
          {uploadMode === "comparison" && (hasResults || hasSecondaryResults) && (
            <ComparisonAnalysisView />
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════
          TAB: NANOFACS AI (PARQUET)
          - Upload .fcs.parquet files
          - Data Overview, Graph Suggestions, Metadata Check, Ask
          ══════════════════════════════════════════════════════ */}
      {mainTab === "ai" && (
        <div>
          <NanoFACSAIPanel
            filePaths={[]}
            experimentDescription="PC3 NanoFACS EV Analysis"
            parametersOfInterest={["Size", "MeanIntensity"]}
            sameSample={true}
          />
        </div>
      )}

      {/* Experimental Conditions Dialog */}
      <ExperimentalConditionsDialog
        open={showConditionsDialog}
        onOpenChange={setShowConditionsDialog}
        onSave={handleSaveConditions}
        sampleType="FCS"
        sampleId={justUploadedSampleId || undefined}
        initialMetadata={fcsAnalysis.fileMetadata}
      />
    </div>
  )
}
