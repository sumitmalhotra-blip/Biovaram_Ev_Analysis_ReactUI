"use client"

import type React from "react"

import { useState, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Upload, FileText, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { useApi } from "@/hooks/use-api"
import { useAnalysisStore } from "@/lib/store"

export function FileUploadZone() {
  const [isDragging, setIsDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [treatment, setTreatment] = useState("")
  const [concentration, setConcentration] = useState("")
  const [operator, setOperator] = useState("")
  const [preparationMethod, setPreparationMethod] = useState("")
  
  const { uploadFCS } = useApi()
  const { fcsAnalysis, apiConnected, apiSamples } = useAnalysisStore()
  
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

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file && file.name.toLowerCase().endsWith('.fcs')) {
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

    await uploadFCS(selectedFile, {
      treatment: treatment || undefined,
      concentration_ug: concentration ? parseFloat(concentration) : undefined,
      preparation_method: preparationMethod || undefined,
      operator: operator || undefined,
    })
    
    // Reset form after upload
    setSelectedFile(null)
    setTreatment("")
    setConcentration("")
    setOperator("")
    setPreparationMethod("")
  }

  return (
    <Card className="card-3d">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-primary/10">
            <Upload className="h-4 w-4 text-primary" />
          </div>
          <CardTitle className="text-base md:text-lg">Upload FCS File</CardTitle>
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
              <input type="file" id="fcs-upload" className="hidden" accept=".fcs" onChange={handleFileSelect} />
              <label htmlFor="fcs-upload" className="cursor-pointer w-full">
                <div className="flex flex-col items-center gap-3 md:gap-4">
                  <div className="p-4 md:p-5 rounded-xl bg-gradient-to-br from-primary/20 to-accent/20 shadow-lg touch-manipulation">
                    <FileText className="h-8 w-8 md:h-10 md:w-10 text-primary" />
                  </div>
                  <p className="text-base md:text-lg font-medium">Drop FCS file here or tap to browse</p>
                  <p className="text-xs md:text-sm text-muted-foreground px-4">Supports .fcs format (nanoFACS, ZE5, etc.)</p>
                </div>
              </label>
            </div>

            {recentFiles.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-2">Recent samples:</p>
                <div className="flex flex-wrap gap-2">
                  {recentFiles.map((sampleId) => (
                    <Badge
                      key={sampleId}
                      variant="secondary"
                      className="cursor-pointer hover:bg-primary/20 transition-colors truncate max-w-[150px] md:max-w-none"
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
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
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

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="treatment">Treatment/Antibody</Label>
                <Select value={treatment} onValueChange={setTreatment}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select treatment" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="CD81">CD81</SelectItem>
                    <SelectItem value="CD9">CD9</SelectItem>
                    <SelectItem value="CD63">CD63</SelectItem>
                    <SelectItem value="Isotype">Isotype Control</SelectItem>
                    <SelectItem value="Unstained">Unstained</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="concentration">Concentration (µg)</Label>
                <Input
                  id="concentration"
                  type="number"
                  step="0.1"
                  value={concentration}
                  onChange={(e) => setConcentration(e.target.value)}
                  placeholder="e.g., 0.5"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="method">Preparation Method</Label>
                <Select value={preparationMethod} onValueChange={setPreparationMethod}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select method" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="SEC">SEC</SelectItem>
                    <SelectItem value="Centrifugation">Centrifugation</SelectItem>
                    <SelectItem value="Ultracentrifugation">Ultracentrifugation</SelectItem>
                    <SelectItem value="ExoQuick">ExoQuick</SelectItem>
                  </SelectContent>
                </Select>
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
              disabled={fcsAnalysis.isAnalyzing || !apiConnected}
            >
              {fcsAnalysis.isAnalyzing ? (
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
  )
}
