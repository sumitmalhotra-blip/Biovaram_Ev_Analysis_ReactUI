"use client"

import { useEffect, useState } from "react"
import { FileUploadZone } from "./file-upload-zone"
import { AnalysisResults } from "./analysis-results"
import { ColumnMapping } from "./column-mapping"
import { FCSBestPracticesGuide } from "./best-practices-guide"
import { ExperimentalConditionsDialog, type ExperimentalConditions } from "@/components/experimental-conditions-dialog"
import { useAnalysisStore } from "@/lib/store"
import { useApi } from "@/hooks/use-api"
import { Card, CardContent } from "@/components/ui/card"
import { AlertCircle, Loader2, Settings2 } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

export function FlowCytometryTab() {
  const { fcsAnalysis, apiConnected, setFCSExperimentalConditions, sidebarCollapsed } = useAnalysisStore()
  const { checkHealth } = useApi()
  const [showConditionsDialog, setShowConditionsDialog] = useState(false)
  const [justUploadedSampleId, setJustUploadedSampleId] = useState<string | null>(null)

  // Check API connection on mount
  useEffect(() => {
    checkHealth()
  }, [checkHealth])

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
  const isAnalyzing = fcsAnalysis.isAnalyzing
  const hasResults = fcsAnalysis.results !== null
  const error = fcsAnalysis.error

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

      <FileUploadZone />

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
