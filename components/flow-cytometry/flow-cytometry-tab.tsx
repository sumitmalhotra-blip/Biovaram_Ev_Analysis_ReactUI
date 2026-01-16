"use client"

import { useEffect, useState } from "react"
import { FileUploadZone } from "./file-upload-zone"
import { DualFileUploadZone } from "./dual-file-upload-zone"
import { OverlayHistogramChart } from "./overlay-histogram-chart"
import { AnalysisResults } from "./analysis-results"
import { ColumnMapping } from "./column-mapping"
import { FCSBestPracticesGuide } from "./best-practices-guide"
import { ExperimentalConditionsDialog, type ExperimentalConditions } from "@/components/experimental-conditions-dialog"
import { useAnalysisStore } from "@/lib/store"
import { useApi } from "@/hooks/use-api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { AlertCircle, Loader2, Settings2, Layers, FileText } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

export function FlowCytometryTab() {
  const { fcsAnalysis, secondaryFcsAnalysis, overlayConfig, apiConnected, setFCSExperimentalConditions, sidebarCollapsed } = useAnalysisStore()
  const { checkHealth } = useApi()
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
      {!hasFile && <FCSBestPracticesGuide />}

      {/* Upload Mode Toggle */}
      <Card className="card-3d">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Upload Mode</CardTitle>
            <div className="flex gap-2">
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
                <Badge variant="secondary" className="ml-1 text-xs">New</Badge>
              </Button>
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

      {hasResults && <AnalysisResults />}

      {/* Overlay Chart - show when in comparison mode with both files analyzed */}
      {uploadMode === "comparison" && hasResults && hasSecondaryResults && overlayConfig.enabled && (
        <div className="space-y-4">
          <OverlayHistogramChart title="Size Distribution Overlay (FSC-A)" parameter="FSC-A" />
          <OverlayHistogramChart title="Granularity Overlay (SSC-A)" parameter="SSC-A" />
        </div>
      )}

      {/* Experimental Conditions Dialog */}
      <ExperimentalConditionsDialog
        open={showConditionsDialog}
        onOpenChange={setShowConditionsDialog}
        onSave={handleSaveConditions}
        sampleType="FCS"
        sampleId={justUploadedSampleId || undefined}
      />
    </div>
  )
}
