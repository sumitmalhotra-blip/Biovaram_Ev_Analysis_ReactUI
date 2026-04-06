"use client"

import type React from "react"

import { useState, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Upload, FileText, Loader2, X, Layers, CheckCircle2, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { useApi } from "@/hooks/use-api"
import { useAnalysisStore } from "@/lib/store"
import { useToast } from "@/hooks/use-toast"

interface FileMetadata {
  treatment: string
  dye: string
  concentration: string
  operator: string
  preparationMethod: string
}

interface FileUploadState {
  file: File | null
  metadata: FileMetadata
}

interface BatchFileUploadState {
  key: string
  file: File
  status: "queued" | "uploading" | "success" | "error"
  sampleId?: string
  error?: string
}

export function DualFileUploadZone() {
  const [activeTab, setActiveTab] = useState<"primary" | "comparison">("primary")
  const [primaryUpload, setPrimaryUpload] = useState<FileUploadState>({
    file: null,
    metadata: { treatment: "", dye: "", concentration: "", operator: "", preparationMethod: "" }
  })
  const [compareBatchFiles, setCompareBatchFiles] = useState<BatchFileUploadState[]>([])
  const [compareBatchMetadata, setCompareBatchMetadata] = useState<FileMetadata>({
    treatment: "",
    dye: "",
    concentration: "",
    operator: "",
    preparationMethod: "",
  })
  const [isDragging, setIsDragging] = useState(false)
  
  const { uploadFCS, uploadFCSCompareBatch } = useApi()
  const { toast } = useToast()
  const { 
    fcsAnalysis, 
    secondaryFcsAnalysis, 
    fcsCompareSession,
    apiConnected, 
    apiSamples,
    overlayConfig,
    setOverlayConfig
  } = useAnalysisStore()
  
  // Get recent FCS files from API samples
  const recentFiles = apiSamples
    .filter(s => s.files?.fcs)
    .slice(0, 5)
    .map(s => s.sample_id)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const enqueueCompareFiles = useCallback((files: File[]) => {
    const valid = files.filter((file) => file.name.toLowerCase().endsWith(".fcs"))
    if (valid.length === 0) {
      return
    }

    setCompareBatchFiles((prev) => {
      const existingKeys = new Set(prev.map((item) => item.key))
      const additions = valid
        .map((file, index) => ({
          key: `${file.name}-${file.lastModified}-${index}`,
          file,
          status: "queued" as const,
        }))
        .filter((item) => !existingKeys.has(item.key))

      return [...prev, ...additions].slice(0, 10)
    })
  }, [])

  const handleDrop = useCallback((e: React.DragEvent, target: "primary" | "comparison") => {
    e.preventDefault()
    setIsDragging(false)
    const droppedFiles = Array.from(e.dataTransfer.files)

    if (target === "primary") {
      const file = droppedFiles[0]
      if (file && file.name.toLowerCase().endsWith(".fcs")) {
        setPrimaryUpload((prev) => ({ ...prev, file }))
      }
      return
    }

    enqueueCompareFiles(droppedFiles)
  }, [enqueueCompareFiles])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>, target: "primary" | "comparison") => {
    const selectedFiles = Array.from(e.target.files || [])
    if (selectedFiles.length > 0) {
      if (target === "primary") {
        setPrimaryUpload((prev) => ({ ...prev, file: selectedFiles[0] }))
      } else {
        enqueueCompareFiles(selectedFiles)
      }
    }
    e.target.value = ""
  }

  const updatePrimaryMetadata = (field: keyof FileMetadata, value: string) => {
    setPrimaryUpload((prev) => ({ ...prev, metadata: { ...prev.metadata, [field]: value } }))
  }

  const updateBatchMetadata = (field: keyof FileMetadata, value: string) => {
    setCompareBatchMetadata((prev) => ({ ...prev, [field]: value }))
  }

  const handleUploadPrimary = async () => {
    if (!primaryUpload.file) return

    await uploadFCS(primaryUpload.file, {
      treatment: primaryUpload.metadata.treatment || undefined,
      dye: primaryUpload.metadata.dye || undefined,
      concentration_ug: primaryUpload.metadata.concentration ? parseFloat(primaryUpload.metadata.concentration) : undefined,
      preparation_method: primaryUpload.metadata.preparationMethod || undefined,
      operator: primaryUpload.metadata.operator || undefined,
    })
    
    // Reset form after upload
    setPrimaryUpload({
      file: null,
      metadata: { treatment: "", dye: "", concentration: "", operator: "", preparationMethod: "" }
    })
  }

  const handleUploadCompareBatch = async () => {
    const queuedFiles = compareBatchFiles
      .filter((item) => item.status === "queued" || item.status === "error")
      .map((item) => ({ key: item.key, file: item.file }))

    if (queuedFiles.length === 0) {
      return
    }

    const summary = await uploadFCSCompareBatch(queuedFiles, {
      metadata: {
        treatment: compareBatchMetadata.treatment || undefined,
        dye: compareBatchMetadata.dye || undefined,
        concentration_ug: compareBatchMetadata.concentration ? parseFloat(compareBatchMetadata.concentration) : undefined,
        preparation_method: compareBatchMetadata.preparationMethod || undefined,
        operator: compareBatchMetadata.operator || undefined,
      },
      onFileStatus: (update) => {
        setCompareBatchFiles((prev) =>
          prev.map((item) => {
            if (item.key !== update.key) return item

            return {
              ...item,
              status: update.status,
              sampleId: update.sampleId,
              error: update.error,
            }
          })
        )
      },
    })

    if (summary.success > 0) {
      toast({
        title: "Compare files uploaded",
        description: `${summary.success} file(s) added to the compare session.${summary.failed > 0 ? ` ${summary.failed} failed.` : ""}`,
      })
    } else {
      toast({
        variant: "destructive",
        title: "Compare upload failed",
        description: "No files were added to the compare session.",
      })
    }
  }

  const clearPrimary = () => {
    setPrimaryUpload({
      file: null,
      metadata: { treatment: "", dye: "", concentration: "", operator: "", preparationMethod: "" }
    })
  }

  const clearCompareBatch = () => {
    setCompareBatchFiles([])
    setCompareBatchMetadata({ treatment: "", dye: "", concentration: "", operator: "", preparationMethod: "" })
  }

  const hasPrimaryResults = fcsAnalysis.results !== null
  const hasComparisonResults = secondaryFcsAnalysis.results !== null || fcsCompareSession.selectedSampleIds.length > 0
  const compareReadyCount = fcsCompareSession.selectedSampleIds.length

  const renderPrimaryDropZone = () => {
    if (!primaryUpload.file) {
      return (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={(e) => handleDrop(e, "primary")}
          className={cn(
            "border-2 border-dashed rounded-xl p-6 md:p-8 text-center transition-all duration-300 cursor-pointer min-h-40 flex items-center justify-center",
            isDragging
              ? "border-primary bg-primary/10 scale-[1.02] shadow-lg shadow-primary/20"
              : "border-border hover:border-primary/50 hover:bg-secondary/30 hover:shadow-md active:scale-[0.98]",
          )}
        >
          <input
            type="file"
            id="fcs-upload-primary"
            className="hidden"
            accept=".fcs"
            onChange={(e) => handleFileSelect(e, "primary")}
          />
          <label htmlFor="fcs-upload-primary" className="cursor-pointer w-full">
            <div className="flex flex-col items-center gap-3">
              <div className="p-3 rounded-xl shadow-lg bg-linear-to-br from-primary/20 to-accent/20">
                <FileText className="h-6 w-6 md:h-8 md:w-8 text-primary" />
              </div>
              <p className="text-sm md:text-base font-medium">Drop primary FCS file</p>
              <p className="text-xs text-muted-foreground">Main file for analysis and baseline compare context</p>
            </div>
          </label>
        </div>
      )
    }

    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3 p-3 bg-secondary/50 rounded-lg">
          <FileText className="h-6 w-6 text-primary" />
          <div className="flex-1 min-w-0">
            <p className="font-medium truncate text-sm">{primaryUpload.file.name}</p>
            <p className="text-xs text-muted-foreground">{(primaryUpload.file.size / 1024 / 1024).toFixed(2)} MB</p>
          </div>
          <Button variant="ghost" size="sm" onClick={clearPrimary}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="primary-treatment" className="text-xs">Treatment</Label>
            <Select value={primaryUpload.metadata.treatment} onValueChange={(v) => updatePrimaryMetadata("treatment", v)}>
              <SelectTrigger className="h-8 text-xs">
                <SelectValue placeholder="Select" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="CD81">CD81</SelectItem>
                <SelectItem value="CD9">CD9</SelectItem>
                <SelectItem value="CD63">CD63</SelectItem>
                <SelectItem value="Isotype">Isotype</SelectItem>
                <SelectItem value="Unstained">Unstained</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="primary-concentration" className="text-xs">Conc. (ug)</Label>
            <Input
              id="primary-concentration"
              type="number"
              step="0.1"
              value={primaryUpload.metadata.concentration}
              onChange={(e) => updatePrimaryMetadata("concentration", e.target.value)}
              placeholder="0.5"
              className="h-8 text-xs"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="primary-dye" className="text-xs">Dye</Label>
            <Select value={primaryUpload.metadata.dye} onValueChange={(v) => updatePrimaryMetadata("dye", v)}>
              <SelectTrigger className="h-8 text-xs">
                <SelectValue placeholder="Select" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="PKH26">PKH26</SelectItem>
                <SelectItem value="PKH67">PKH67</SelectItem>
                <SelectItem value="DiI">DiI</SelectItem>
                <SelectItem value="DiO">DiO</SelectItem>
                <SelectItem value="CFSE">CFSE</SelectItem>
                <SelectItem value="None">None</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="primary-method" className="text-xs">Method</Label>
            <Select value={primaryUpload.metadata.preparationMethod} onValueChange={(v) => updatePrimaryMetadata("preparationMethod", v)}>
              <SelectTrigger className="h-8 text-xs">
                <SelectValue placeholder="Select" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="SEC">SEC</SelectItem>
                <SelectItem value="Centrifugation">Centrifugation</SelectItem>
                <SelectItem value="Ultracentrifugation">Ultracentrifugation</SelectItem>
                <SelectItem value="ExoQuick">ExoQuick</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="primary-operator" className="text-xs">Operator</Label>
            <Input
              id="primary-operator"
              value={primaryUpload.metadata.operator}
              onChange={(e) => updatePrimaryMetadata("operator", e.target.value)}
              placeholder="Name"
              className="h-8 text-xs"
            />
          </div>
        </div>

        <Button className="w-full" onClick={handleUploadPrimary} disabled={fcsAnalysis.isAnalyzing || !apiConnected}>
          {fcsAnalysis.isAnalyzing ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Upload className="h-4 w-4 mr-2" />
              Upload and Analyze
            </>
          )}
        </Button>
      </div>
    )
  }

  return (
    <Card className="card-3d">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-primary/10">
            <Upload className="h-4 w-4 text-primary" />
          </div>
          <CardTitle className="text-base md:text-lg">Upload FCS Files</CardTitle>
          {!apiConnected && (
            <Badge variant="destructive" className="ml-auto">Offline</Badge>
          )}
          {hasComparisonResults && (
            <Badge variant="secondary" className="ml-auto">
              <Layers className="h-3 w-3 mr-1" />
              {compareReadyCount} Compare Samples
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "primary" | "comparison")}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="primary" className="gap-2">
              <FileText className="h-4 w-4" />
              Primary File
              {hasPrimaryResults && <Badge variant="outline" className="ml-1 h-5 text-xs">✓</Badge>}
            </TabsTrigger>
            <TabsTrigger value="comparison" className="gap-2">
              <Layers className="h-4 w-4" />
              Comparison File
              {hasComparisonResults && <Badge variant="outline" className="ml-1 h-5 text-xs">✓</Badge>}
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="primary" className="mt-4">
            {renderPrimaryDropZone()}
          </TabsContent>
          
          <TabsContent value="comparison" className="mt-4">
            <div className="space-y-4">
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, "comparison")}
                className={cn(
                  "border-2 border-dashed rounded-xl p-6 md:p-8 text-center transition-all duration-300 cursor-pointer",
                  isDragging
                    ? "border-orange-500 bg-orange-500/10 scale-[1.02] shadow-lg shadow-orange-500/20"
                    : "border-border hover:border-orange-500/50 hover:bg-secondary/30 hover:shadow-md active:scale-[0.98]",
                )}
              >
                <input
                  type="file"
                  id="fcs-upload-comparison"
                  className="hidden"
                  accept=".fcs"
                  multiple
                  onChange={(e) => handleFileSelect(e, "comparison")}
                />
                <label htmlFor="fcs-upload-comparison" className="cursor-pointer w-full">
                  <div className="flex flex-col items-center gap-3">
                    <div className="p-3 rounded-xl shadow-lg bg-linear-to-br from-orange-500/20 to-amber-500/20">
                      <Layers className="h-6 w-6 md:h-8 md:w-8 text-orange-500" />
                    </div>
                    <p className="text-sm md:text-base font-medium">Drop 5-10 compare FCS files</p>
                    <p className="text-xs text-muted-foreground">Add files in one batch and track per-file upload status</p>
                  </div>
                </label>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="batch-treatment" className="text-xs">Treatment</Label>
                  <Select value={compareBatchMetadata.treatment} onValueChange={(v) => updateBatchMetadata("treatment", v)}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="CD81">CD81</SelectItem>
                      <SelectItem value="CD9">CD9</SelectItem>
                      <SelectItem value="CD63">CD63</SelectItem>
                      <SelectItem value="Isotype">Isotype</SelectItem>
                      <SelectItem value="Unstained">Unstained</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="batch-dye" className="text-xs">Dye</Label>
                  <Select value={compareBatchMetadata.dye} onValueChange={(v) => updateBatchMetadata("dye", v)}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="PKH26">PKH26</SelectItem>
                      <SelectItem value="PKH67">PKH67</SelectItem>
                      <SelectItem value="DiI">DiI</SelectItem>
                      <SelectItem value="DiO">DiO</SelectItem>
                      <SelectItem value="CFSE">CFSE</SelectItem>
                      <SelectItem value="None">None</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="batch-concentration" className="text-xs">Conc. (ug)</Label>
                  <Input
                    id="batch-concentration"
                    type="number"
                    step="0.1"
                    value={compareBatchMetadata.concentration}
                    onChange={(e) => updateBatchMetadata("concentration", e.target.value)}
                    placeholder="0.5"
                    className="h-8 text-xs"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="batch-method" className="text-xs">Method</Label>
                  <Select value={compareBatchMetadata.preparationMethod} onValueChange={(v) => updateBatchMetadata("preparationMethod", v)}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="SEC">SEC</SelectItem>
                      <SelectItem value="Centrifugation">Centrifugation</SelectItem>
                      <SelectItem value="Ultracentrifugation">Ultracentrifugation</SelectItem>
                      <SelectItem value="ExoQuick">ExoQuick</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="batch-operator" className="text-xs">Operator</Label>
                  <Input
                    id="batch-operator"
                    value={compareBatchMetadata.operator}
                    onChange={(e) => updateBatchMetadata("operator", e.target.value)}
                    placeholder="Name"
                    className="h-8 text-xs"
                  />
                </div>
              </div>

              {compareBatchFiles.length > 0 && (
                <div className="space-y-2">
                  {compareBatchFiles.map((item) => (
                    <div key={item.key} className="flex items-center gap-2 rounded-lg border p-2 text-xs">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <span className="flex-1 truncate">{item.file.name}</span>
                      {item.status === "uploading" && (
                        <Badge variant="outline" className="gap-1"><Loader2 className="h-3 w-3 animate-spin" />Uploading</Badge>
                      )}
                      {item.status === "success" && (
                        <Badge variant="secondary" className="gap-1"><CheckCircle2 className="h-3 w-3" />{item.sampleId || "Added"}</Badge>
                      )}
                      {item.status === "error" && (
                        <Badge variant="destructive" className="gap-1" title={item.error}><AlertCircle className="h-3 w-3" />Error</Badge>
                      )}
                      {item.status === "queued" && <Badge variant="outline">Queued</Badge>}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setCompareBatchFiles((prev) => prev.filter((f) => f.key !== item.key))}
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex gap-2">
                <Button
                  className="flex-1"
                  variant="secondary"
                  onClick={handleUploadCompareBatch}
                  disabled={!apiConnected || compareBatchFiles.length === 0 || compareBatchFiles.some((item) => item.status === "uploading")}
                >
                  <Upload className="h-4 w-4 mr-2" />
                  Upload to Compare Session ({compareBatchFiles.length})
                </Button>
                <Button variant="outline" onClick={clearCompareBatch} disabled={compareBatchFiles.length === 0}>
                  Clear
                </Button>
              </div>
            </div>
          </TabsContent>
        </Tabs>

        {/* Overlay Toggle - show when both files have results */}
        {hasPrimaryResults && hasComparisonResults && (
          <div className="pt-2 border-t">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium">Overlay Mode</span>
              </div>
              <Button
                variant={overlayConfig.enabled ? "default" : "outline"}
                size="sm"
                onClick={() => setOverlayConfig({ enabled: !overlayConfig.enabled })}
              >
                {overlayConfig.enabled ? "Enabled" : "Enable Overlay"}
              </Button>
            </div>
            {overlayConfig.enabled && (
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <div className="flex items-center gap-2 p-2 bg-secondary/50 rounded">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: overlayConfig.primaryColor }}
                  />
                  <span className="truncate">{fcsAnalysis.file?.name || "Primary"}</span>
                </div>
                <div className="flex items-center gap-2 p-2 bg-secondary/50 rounded">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: overlayConfig.secondaryColor }}
                  />
                  <span className="truncate">{secondaryFcsAnalysis.file?.name || "Comparison"}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {recentFiles.length > 0 && !primaryUpload.file && compareBatchFiles.length === 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-2">Recent samples:</p>
            <div className="flex flex-wrap gap-2">
              {recentFiles.map((sampleId) => (
                <Badge
                  key={sampleId}
                  variant="secondary"
                  className="cursor-pointer hover:bg-primary/20 transition-colors truncate max-w-[150px]"
                >
                  {sampleId}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
