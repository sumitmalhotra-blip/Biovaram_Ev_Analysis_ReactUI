"use client"

import { useEffect, useState } from "react"
import { FileUploadZone } from "./file-upload-zone"
import { DualFileUploadZone } from "./dual-file-upload-zone"
import { OverlayHistogramChart } from "./overlay-histogram-chart"
import { AnalysisResults } from "./analysis-results"
import { ComparisonAnalysisView } from "./comparison-analysis-view"
import { ColumnMapping } from "./column-mapping"
import { FCSBestPracticesGuide } from "./best-practices-guide"
import { BeadCalibrationPanel } from "./bead-calibration-panel"
import { ExperimentalConditionsDialog, type ExperimentalConditions, type FileMetadata } from "@/components/experimental-conditions-dialog"
import { useAnalysisStore } from "@/lib/store"
import { useApi } from "@/hooks/use-api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { AlertCircle, Loader2, Settings2, Layers, FileText, RotateCcw } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { useToast } from "@/hooks/use-toast"

export function FlowCytometryTab() {
  const { fcsAnalysis, secondaryFcsAnalysis, overlayConfig, apiConnected, setFCSExperimentalConditions, sidebarCollapsed, resetFCSAnalysis } = useAnalysisStore()
  const { checkHealth } = useApi()
  const { toast } = useToast()
  const [showConditionsDialog, setShowConditionsDialog] = useState(false)
  const [justUploadedSampleId, setJustUploadedSampleId] = useState<string | null>(null)
  const [uploadMode, setUploadMode] = useState<"single" | "comparison">("single")

  // Check API connection on mount - PERFORMANCE FIX: Empty deps for mount-only
  useEffect(() => {
    checkHealth()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Show experimental conditions dialog after successful upload
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
      {!apiConnected && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Backend Offline</AlertTitle>
          <AlertDescription>
            Cannot connect to the analysis backend at localhost:8000. Please ensure the FastAPI server is running.
          </AlertDescription>
        </Alert>
      )}

      {/* Best Practices Guide - show before upload to help users prepare */}
      {!hasFile && !hasResults && <FCSBestPracticesGuide />}

      {/* Bead Calibration Panel - always visible for calibration management */}
      <BeadCalibrationPanel />

      {/* Upload Mode Toggle with Reset Button */}
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
              {/* Reset Tab Button - only show when there are results */}
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

      {/* File Upload Zone - based on mode */}
      {uploadMode === "single" ? <FileUploadZone /> : <DualFileUploadZone />}

      {/* Hint about sidebar settings when collapsed */}
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

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Analysis Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {hasFile && !isAnalyzing && !hasResults && <ColumnMapping />}

      {/* Show different views based on mode */}
      {uploadMode === "single" && hasResults && <AnalysisResults />}
      
      {/* Comparison Mode - Show tabbed view with Primary/Comparison/Overlay */}
      {uploadMode === "comparison" && (hasResults || hasSecondaryResults) && (
        <ComparisonAnalysisView />
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
