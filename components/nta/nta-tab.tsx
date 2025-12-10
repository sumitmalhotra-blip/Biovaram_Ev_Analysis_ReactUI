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
import { NTASizeDistributionChart } from "./charts/nta-size-distribution-chart"
import { ConcentrationProfileChart } from "./charts/concentration-profile-chart"
import { NTATemperatureSettings } from "./temperature-settings"
import { NTABestPracticesGuide } from "./best-practices-guide"
import { NTAStatisticsCards } from "./statistics-cards"
import { NTASizeDistributionBreakdown } from "./size-distribution-breakdown"
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
                    "border-2 border-dashed rounded-xl p-6 md:p-8 text-center transition-all duration-300 cursor-pointer",
                    isDragging
                      ? "border-primary bg-primary/10 scale-[1.02] shadow-lg shadow-primary/20"
                      : "border-border hover:border-primary/50 hover:bg-secondary/30 hover:shadow-md",
                  )}
                >
                  <input 
                    type="file" 
                    id="nta-upload" 
                    className="hidden" 
                    accept=".txt,.csv" 
                    onChange={handleFileSelect} 
                  />
                  <label htmlFor="nta-upload" className="cursor-pointer">
                    <div className="flex flex-col items-center gap-2">
                      <div className="p-3 rounded-xl bg-gradient-to-br from-primary/20 to-accent/20 shadow-lg">
                        <Microscope className="h-6 w-6 text-primary" />
                      </div>
                      <p className="text-sm font-medium">Drop NTA file here or click to browse</p>
                      <p className="text-xs text-muted-foreground">Supports ZetaView .txt and .csv formats</p>
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
      <div className="p-4 md:p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Analysis Error</AlertTitle>
          <AlertDescription>{ntaAnalysis.error}</AlertDescription>
        </Alert>
      </div>
    )
  }

  // Export handlers
  const handleExport = (format: string) => {
    toast({
      title: "Export Started",
      description: `Exporting NTA results as ${format}...`,
    })
    // TODO: Implement actual export logic
  }

  return (
    <div className="p-4 md:p-6 space-y-4 md:space-y-6">
      {/* Header Section */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Microscope className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-bold">NTA Analysis Results</h2>
              <p className="text-sm text-muted-foreground">Nanoparticle Tracking Analysis</p>
            </div>
          </div>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => {
              resetNTAAnalysis()
              toast({
                title: "Tab Reset",
                description: "NTA analysis cleared. Upload a new file to analyze.",
              })
            }}
            className="gap-2 w-full sm:w-auto"
          >
            <RotateCcw className="h-4 w-4" />
            Reset Tab
          </Button>
        </div>

        {/* Sample Information */}
        <div className="flex flex-wrap items-center gap-2">
          {results?.sample_id && (
            <Badge variant="outline" className="gap-1">
              <Beaker className="h-3 w-3" />
              {results.sample_id}
            </Badge>
          )}
          {results?.processed_at && (
            <Badge variant="secondary" className="gap-1">
              <Clock className="h-3 w-3" />
              {new Date(results.processed_at).toLocaleString()}
            </Badge>
          )}
          {results?.temperature_celsius && (
            <Badge variant="secondary">
              {results.temperature_celsius.toFixed(1)}°C
            </Badge>
          )}
        </div>
      </div>

      {/* Statistics Cards */}
      <NTAStatisticsCards results={results} />

      {/* Size Distribution Breakdown */}
      <NTASizeDistributionBreakdown results={results} />

      {/* Export Options */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="card-3d">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary/10">
                <Download className="h-4 w-4 text-primary" />
              </div>
              <CardTitle className="text-base">Export Data</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <Button variant="outline" size="sm" onClick={() => handleExport("CSV")} className="w-full">
                CSV
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExport("Excel")} className="w-full">
                Excel
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExport("JSON")} className="w-full">
                JSON
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExport("PDF Report")} className="w-full">
                PDF Report
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="card-3d">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary/10">
                <TableIcon className="h-4 w-4 text-primary" />
              </div>
              <CardTitle className="text-base">Quick Summary</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Particles:</span>
                <span className="font-mono font-medium">
                  {results.total_particles 
                    ? results.total_particles >= 1e6
                      ? `${(results.total_particles / 1e6).toFixed(2)}M`
                      : results.total_particles.toLocaleString()
                    : "N/A"
                  }
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Size Range:</span>
                <span className="font-mono font-medium">
                  {results.d10_nm && results.d90_nm
                    ? `${results.d10_nm.toFixed(0)}-${results.d90_nm.toFixed(0)} nm`
                    : "N/A"
                  }
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Concentration:</span>
                <span className="font-mono font-medium">
                  {results.concentration_particles_ml
                    ? `${(results.concentration_particles_ml / 1e9).toFixed(2)}E9/mL`
                    : "N/A"
                  }
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Visualization Tabs */}
      <Card className="card-3d">
        <CardHeader className="pb-2">
          <CardTitle className="text-base md:text-lg">Visualizations</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="distribution" className="space-y-4">
            <TabsList className="bg-secondary/50 w-full justify-start overflow-x-auto flex-nowrap">
              <TabsTrigger value="distribution" className="shrink-0">
                Size Distribution
              </TabsTrigger>
              <TabsTrigger value="concentration" className="shrink-0">
                Concentration
              </TabsTrigger>
              <TabsTrigger value="position" className="shrink-0">
                Position
              </TabsTrigger>
              <TabsTrigger value="corrected" className="shrink-0">
                Corrected
              </TabsTrigger>
            </TabsList>

            <TabsContent value="distribution" className="space-y-4">
              <div className="flex items-center justify-end gap-1">
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <Maximize2 className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => handlePin("NTA Size Distribution", "histogram")}
                >
                  <Pin className="h-4 w-4" />
                </Button>
              </div>
              <NTASizeDistributionChart />
            </TabsContent>

            <TabsContent value="concentration" className="space-y-4">
              <div className="flex items-center justify-end gap-1">
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <Maximize2 className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => handlePin("Concentration Profile", "bar")}
                >
                  <Pin className="h-4 w-4" />
                </Button>
              </div>
              <ConcentrationProfileChart />
            </TabsContent>

            <TabsContent value="position" className="space-y-4">
              <div className="p-8 text-center text-muted-foreground">
                <p>Position analysis heatmap would display here</p>
              </div>
            </TabsContent>

            <TabsContent value="corrected" className="space-y-4">
              <Card className="bg-secondary/30 shadow-inner">
                <CardContent className="p-4">
                  <h4 className="text-sm font-medium mb-3">Temperature Correction Applied</h4>
                  <div className="grid grid-cols-3 gap-2 md:gap-4 text-xs md:text-sm overflow-x-auto">
                    <div>
                      <p className="text-muted-foreground">Parameter</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Raw</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Corrected</p>
                    </div>

                    <div className="font-mono">D50</div>
                    <div className="font-mono">142.5 nm</div>
                    <div className="font-mono text-emerald">
                      140.8 nm <span className="text-xs hidden sm:inline">(-1.2%)</span>
                    </div>

                    <div className="font-mono">Mean</div>
                    <div className="font-mono">148.3 nm</div>
                    <div className="font-mono text-emerald">
                      146.5 nm <span className="text-xs hidden sm:inline">(-1.2%)</span>
                    </div>

                    <div className="font-mono">Conc.</div>
                    <div className="font-mono">2.4E+09</div>
                    <div className="font-mono text-emerald">
                      2.43E+09 <span className="text-xs hidden sm:inline">(+1.3%)</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

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
