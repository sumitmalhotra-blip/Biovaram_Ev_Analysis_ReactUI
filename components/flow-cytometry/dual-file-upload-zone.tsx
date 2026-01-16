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
import { Upload, FileText, Loader2, X, Layers, Plus } from "lucide-react"
import { cn } from "@/lib/utils"
import { useApi } from "@/hooks/use-api"
import { useAnalysisStore } from "@/lib/store"

interface FileMetadata {
  treatment: string
  concentration: string
  operator: string
  preparationMethod: string
}

interface FileUploadState {
  file: File | null
  metadata: FileMetadata
}

export function DualFileUploadZone() {
  const [activeTab, setActiveTab] = useState<"primary" | "comparison">("primary")
  const [primaryUpload, setPrimaryUpload] = useState<FileUploadState>({
    file: null,
    metadata: { treatment: "", concentration: "", operator: "", preparationMethod: "" }
  })
  const [comparisonUpload, setComparisonUpload] = useState<FileUploadState>({
    file: null,
    metadata: { treatment: "", concentration: "", operator: "", preparationMethod: "" }
  })
  const [isDragging, setIsDragging] = useState(false)
  
  const { uploadFCS, uploadSecondaryFCS } = useApi()
  const { 
    fcsAnalysis, 
    secondaryFcsAnalysis, 
    apiConnected, 
    apiSamples,
    overlayConfig,
    setOverlayConfig,
    resetSecondaryFCSAnalysis
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

  const handleDrop = useCallback((e: React.DragEvent, target: "primary" | "comparison") => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file && file.name.toLowerCase().endsWith('.fcs')) {
      if (target === "primary") {
        setPrimaryUpload(prev => ({ ...prev, file }))
      } else {
        setComparisonUpload(prev => ({ ...prev, file }))
      }
    }
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>, target: "primary" | "comparison") => {
    const file = e.target.files?.[0]
    if (file) {
      if (target === "primary") {
        setPrimaryUpload(prev => ({ ...prev, file }))
      } else {
        setComparisonUpload(prev => ({ ...prev, file }))
      }
    }
  }

  const updateMetadata = (target: "primary" | "comparison", field: keyof FileMetadata, value: string) => {
    if (target === "primary") {
      setPrimaryUpload(prev => ({ ...prev, metadata: { ...prev.metadata, [field]: value } }))
    } else {
      setComparisonUpload(prev => ({ ...prev, metadata: { ...prev.metadata, [field]: value } }))
    }
  }

  const handleUploadPrimary = async () => {
    if (!primaryUpload.file) return

    await uploadFCS(primaryUpload.file, {
      treatment: primaryUpload.metadata.treatment || undefined,
      concentration_ug: primaryUpload.metadata.concentration ? parseFloat(primaryUpload.metadata.concentration) : undefined,
      preparation_method: primaryUpload.metadata.preparationMethod || undefined,
      operator: primaryUpload.metadata.operator || undefined,
    })
    
    // Reset form after upload
    setPrimaryUpload({
      file: null,
      metadata: { treatment: "", concentration: "", operator: "", preparationMethod: "" }
    })
  }

  const handleUploadComparison = async () => {
    if (!comparisonUpload.file) return

    await uploadSecondaryFCS(comparisonUpload.file, {
      treatment: comparisonUpload.metadata.treatment || undefined,
      concentration_ug: comparisonUpload.metadata.concentration ? parseFloat(comparisonUpload.metadata.concentration) : undefined,
      preparation_method: comparisonUpload.metadata.preparationMethod || undefined,
      operator: comparisonUpload.metadata.operator || undefined,
    })
    
    // Reset form after upload
    setComparisonUpload({
      file: null,
      metadata: { treatment: "", concentration: "", operator: "", preparationMethod: "" }
    })
  }

  const clearPrimary = () => {
    setPrimaryUpload({
      file: null,
      metadata: { treatment: "", concentration: "", operator: "", preparationMethod: "" }
    })
  }

  const clearComparison = () => {
    setComparisonUpload({
      file: null,
      metadata: { treatment: "", concentration: "", operator: "", preparationMethod: "" }
    })
    resetSecondaryFCSAnalysis()
  }

  const hasPrimaryResults = fcsAnalysis.results !== null
  const hasComparisonResults = secondaryFcsAnalysis.results !== null

  const renderDropZone = (target: "primary" | "comparison") => {
    const upload = target === "primary" ? primaryUpload : comparisonUpload
    const isAnalyzing = target === "primary" ? fcsAnalysis.isAnalyzing : secondaryFcsAnalysis.isAnalyzing
    const handleUpload = target === "primary" ? handleUploadPrimary : handleUploadComparison
    const clearFile = target === "primary" ? clearPrimary : clearComparison
    const updateMeta = (field: keyof FileMetadata, value: string) => updateMetadata(target, field, value)
    const inputId = `fcs-upload-${target}`

    if (!upload.file) {
      return (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={(e) => handleDrop(e, target)}
          className={cn(
            "border-2 border-dashed rounded-xl p-6 md:p-8 text-center transition-all duration-300 cursor-pointer min-h-40 flex items-center justify-center",
            isDragging
              ? "border-primary bg-primary/10 scale-[1.02] shadow-lg shadow-primary/20"
              : "border-border hover:border-primary/50 hover:bg-secondary/30 hover:shadow-md active:scale-[0.98]",
          )}
        >
          <input 
            type="file" 
            id={inputId} 
            className="hidden" 
            accept=".fcs" 
            onChange={(e) => handleFileSelect(e, target)} 
          />
          <label htmlFor={inputId} className="cursor-pointer w-full">
            <div className="flex flex-col items-center gap-3">
              <div className={cn(
                "p-3 rounded-xl shadow-lg",
                target === "primary" 
                  ? "bg-linear-to-br from-primary/20 to-accent/20"
                  : "bg-linear-to-br from-orange-500/20 to-amber-500/20"
              )}>
                {target === "primary" ? (
                  <FileText className="h-6 w-6 md:h-8 md:w-8 text-primary" />
                ) : (
                  <Layers className="h-6 w-6 md:h-8 md:w-8 text-orange-500" />
                )}
              </div>
              <p className="text-sm md:text-base font-medium">
                {target === "primary" ? "Drop primary FCS file" : "Drop comparison FCS file"}
              </p>
              <p className="text-xs text-muted-foreground">
                {target === "primary" ? "Main file for analysis" : "Second file for overlay comparison"}
              </p>
            </div>
          </label>
        </div>
      )
    }

    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3 p-3 bg-secondary/50 rounded-lg">
          <FileText className={cn(
            "h-6 w-6",
            target === "primary" ? "text-primary" : "text-orange-500"
          )} />
          <div className="flex-1 min-w-0">
            <p className="font-medium truncate text-sm">{upload.file.name}</p>
            <p className="text-xs text-muted-foreground">
              {(upload.file.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
          <Button 
            variant="ghost" 
            size="sm"
            onClick={clearFile}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor={`${target}-treatment`} className="text-xs">Treatment</Label>
            <Select value={upload.metadata.treatment} onValueChange={(v) => updateMeta("treatment", v)}>
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
            <Label htmlFor={`${target}-concentration`} className="text-xs">Conc. (µg)</Label>
            <Input
              id={`${target}-concentration`}
              type="number"
              step="0.1"
              value={upload.metadata.concentration}
              onChange={(e) => updateMeta("concentration", e.target.value)}
              placeholder="0.5"
              className="h-8 text-xs"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor={`${target}-method`} className="text-xs">Method</Label>
            <Select value={upload.metadata.preparationMethod} onValueChange={(v) => updateMeta("preparationMethod", v)}>
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
            <Label htmlFor={`${target}-operator`} className="text-xs">Operator</Label>
            <Input
              id={`${target}-operator`}
              value={upload.metadata.operator}
              onChange={(e) => updateMeta("operator", e.target.value)}
              placeholder="Name"
              className="h-8 text-xs"
            />
          </div>
        </div>

        <Button 
          className="w-full" 
          onClick={handleUpload}
          disabled={isAnalyzing || !apiConnected}
          variant={target === "primary" ? "default" : "secondary"}
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Upload className="h-4 w-4 mr-2" />
              {target === "primary" ? "Upload & Analyze" : "Upload for Comparison"}
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
          {hasPrimaryResults && hasComparisonResults && (
            <Badge variant="secondary" className="ml-auto">
              <Layers className="h-3 w-3 mr-1" />
              2 Files Ready
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
            {renderDropZone("primary")}
          </TabsContent>
          
          <TabsContent value="comparison" className="mt-4">
            {!hasPrimaryResults ? (
              <div className="text-center py-8 text-muted-foreground">
                <Layers className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Upload a primary file first</p>
                <p className="text-xs mt-1">Then add a second file for comparison</p>
              </div>
            ) : (
              renderDropZone("comparison")
            )}
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

        {recentFiles.length > 0 && !primaryUpload.file && !comparisonUpload.file && (
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
