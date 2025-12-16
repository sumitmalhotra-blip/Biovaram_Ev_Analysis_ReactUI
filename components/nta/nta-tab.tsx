"use client"

import { useState, useCallback, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { 
  Pin, Maximize2, MapPin, Ruler, Microscope, BarChart3, TableIcon, 
  Upload, FileText, Loader2, AlertCircle, RotateCcw, Download, Clock, Beaker
} from "lucide-react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { useAnalysisStore } from "@/lib/store"
import { useToast } from "@/hooks/use-toast"
import { useApi } from "@/hooks/use-api"
import { NTATemperatureSettings } from "./temperature-settings"
import { NTABestPracticesGuide } from "./best-practices-guide"
import { NTAAnalysisResults } from "./nta-analysis-results"
import { ExperimentalConditionsDialog, type ExperimentalConditions } from "@/components/experimental-conditions-dialog"
import { cn } from "@/lib/utils"

export function NTATab() {
  const { ntaAnalysis, apiConnected, apiSamples, resetNTAAnalysis, setNTAExperimentalConditions } = useAnalysisStore()
  const { uploadNTA, checkHealth } = useApi()
  const { pinChart } = useAnalysisStore()
  const { toast } = useToast()

  // Upload form state
  const [isDragging, setIsDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [treatment, setTreatment] = useState("")
  const [temperature, setTemperature] = useState("")
  const [operator, setOperator] = useState("")
  
  // Experimental conditions dialog state
  const [showConditionsDialog, setShowConditionsDialog] = useState(false)
  const [justUploadedSampleId, setJustUploadedSampleId] = useState<string | null>(null)

  // Check API on mount
  useEffect(() => {
    checkHealth()
  }, [checkHealth])

  // Show experimental conditions dialog after successful upload
  useEffect(() => {
    if (ntaAnalysis.results && ntaAnalysis.sampleId && !ntaAnalysis.experimentalConditions) {
      setJustUploadedSampleId(ntaAnalysis.sampleId)
      setShowConditionsDialog(true)
    }
  }, [ntaAnalysis.results, ntaAnalysis.sampleId, ntaAnalysis.experimentalConditions])

  const handleSaveConditions = (conditions: ExperimentalConditions) => {
    setNTAExperimentalConditions(conditions)
    setShowConditionsDialog(false)
  }

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file && (file.name.toLowerCase().endsWith('.txt') || file.name.toLowerCase().endsWith('.csv'))) {
      setSelectedFile(file)
    }
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    await uploadNTA(selectedFile, {
      treatment: treatment || undefined,
      temperature_celsius: temperature ? parseFloat(temperature) : undefined,
      operator: operator || undefined,
    })

    // Reset form
    setSelectedFile(null)
    setTreatment("")
    setTemperature("")
    setOperator("")
  }

  const handlePin = (chartTitle: string, chartType: "histogram" | "bar" | "line") => {
    pinChart({
      id: crypto.randomUUID(),
      title: chartTitle,
      source: "NTA",
      timestamp: new Date(),
      type: chartType,
      data: ntaAnalysis.results,
    })
    toast({
      title: "Pinned to Dashboard",
      description: `${chartTitle} has been pinned.`,
    })
  }

  // Get recent NTA samples
  const recentNTASamples = apiSamples
    .filter(s => s.files?.nta)
    .slice(0, 5)
    .map(s => s.sample_id)

  // Use real results if available
  const results = ntaAnalysis.results
  const hasData = results !== null
  const fileName = ntaAnalysis.file?.name

  // Show loading state
  if (ntaAnalysis.isAnalyzing) {
    return (
      <div className="p-4 md:p-6">
        <Card className="card-3d">
          <CardContent className="p-8 text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
            <p className="text-muted-foreground">Analyzing NTA file...</p>
            <p className="text-sm text-muted-foreground mt-2">
              Parsing size distribution and concentration data
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Show error if any
  if (ntaAnalysis.error) {
    return (
      <div className="p-4 md:p-6 space-y-4">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Analysis Error</AlertTitle>
          <AlertDescription>{ntaAnalysis.error}</AlertDescription>
        </Alert>
        <Button onClick={resetNTAAnalysis} variant="outline">
          <RotateCcw className="h-4 w-4 mr-2" />
          Try Again
        </Button>
      </div>
    )
  }

  // Show analysis results if data is available
  if (hasData && results) {
    return (
      <div className="p-4 md:p-6">
        <NTAAnalysisResults 
          results={results} 
          sampleId={ntaAnalysis.sampleId || undefined}
          fileName={fileName}
        />
        
        {/* Experimental Conditions Dialog */}
        <ExperimentalConditionsDialog
          open={showConditionsDialog}
          onOpenChange={setShowConditionsDialog}
          onSave={handleSaveConditions}
          sampleType="NTA"
          sampleId={justUploadedSampleId || undefined}
        />
      </div>
    )
  }

  // Render upload form if no data
  if (!hasData && !ntaAnalysis.isAnalyzing) {
    return (
      <div className="p-4 md:p-6 space-y-4">
        {!apiConnected && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Backend Offline</AlertTitle>
            <AlertDescription>
              Cannot connect to the analysis backend at localhost:8000. Please ensure the FastAPI server is running.
            </AlertDescription>
          </Alert>
        )}

        {/* Temperature Correction Settings (collapsible) */}
        <NTATemperatureSettings />

        {/* Best Practices Guide */}
        <NTABestPracticesGuide />

        <Card className="card-3d">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary/10">
                <Upload className="h-4 w-4 text-primary" />
              </div>
              <CardTitle className="text-base md:text-lg">Upload NTA File</CardTitle>
              {!apiConnected && (
                <Badge variant="destructive" className="ml-auto">Offline</Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {!selectedFile ? (
              <>
                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  className={cn(
                    "border-2 border-dashed rounded-xl p-8 md:p-10 lg:p-12 text-center transition-all duration-300 cursor-pointer min-h-[180px] md:min-h-[200px] flex items-center justify-center",
                    isDragging
                      ? "border-primary bg-primary/10 scale-[1.02] shadow-lg shadow-primary/20"
                      : "border-border hover:border-primary/50 hover:bg-secondary/30 hover:shadow-md active:scale-[0.98]",
                  )}
                >
                  <input 
                    type="file" 
                    id="nta-upload" 
                    className="hidden" 
                    accept=".txt,.csv" 
                    onChange={handleFileSelect} 
                  />
                  <label htmlFor="nta-upload" className="cursor-pointer w-full">
                    <div className="flex flex-col items-center gap-3 md:gap-4">
                      <div className="p-4 md:p-5 rounded-xl bg-linear-to-br from-primary/20 to-accent/20 shadow-lg touch-manipulation">
                        <Microscope className="h-8 w-8 md:h-10 md:w-10 text-primary" />
                      </div>
                      <p className="text-base md:text-lg font-medium">Drop NTA file here or tap to browse</p>
                      <p className="text-xs md:text-sm text-muted-foreground px-4">Supports ZetaView .txt and .csv formats</p>
                    </div>
                  </label>
                </div>

                {recentNTASamples.length > 0 && (
                  <div>
                    <p className="text-xs text-muted-foreground mb-2">Recent NTA samples:</p>
                    <div className="flex flex-wrap gap-2">
                      {recentNTASamples.map((sampleId) => (
                        <Badge
                          key={sampleId}
                          variant="secondary"
                          className="cursor-pointer hover:bg-primary/20 transition-colors"
                        >
                          {sampleId}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-4 bg-secondary/50 rounded-lg">
                  <FileText className="h-8 w-8 text-primary" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{selectedFile.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {(selectedFile.size / 1024).toFixed(2)} KB
                    </p>
                  </div>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => setSelectedFile(null)}
                  >
                    Change
                  </Button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="treatment">Treatment</Label>
                    <Select value={treatment} onValueChange={setTreatment}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select treatment" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="CD81">CD81</SelectItem>
                        <SelectItem value="CD9">CD9</SelectItem>
                        <SelectItem value="Unstained">Unstained</SelectItem>
                        <SelectItem value="Control">Control</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="temperature">Temperature (°C)</Label>
                    <Input
                      id="temperature"
                      type="number"
                      step="0.1"
                      value={temperature}
                      onChange={(e) => setTemperature(e.target.value)}
                      placeholder="e.g., 22.5"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="operator">Operator</Label>
                    <Input
                      id="operator"
                      value={operator}
                      onChange={(e) => setOperator(e.target.value)}
                      placeholder="Your name"
                    />
                  </div>
                </div>

                <Button 
                  className="w-full" 
                  onClick={handleUpload}
                  disabled={ntaAnalysis.isAnalyzing || !apiConnected}
                >
                  {ntaAnalysis.isAnalyzing ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Uploading & Analyzing...
                    </>
                  ) : (
                    <>
                      <Upload className="h-4 w-4 mr-2" />
                      Upload & Analyze
                    </>
                  )}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    )
  }
}
