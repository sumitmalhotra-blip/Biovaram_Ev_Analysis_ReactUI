"use client"

import type React from "react"

import { useState, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Upload, FileText, X, Loader2, AlertCircle } from "lucide-react"
import { useAnalysisStore } from "@/lib/store"
import { useApi } from "@/hooks/use-api"
import { cn } from "@/lib/utils"

export function QuickUpload() {
  const [isDragging, setIsDragging] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [treatment, setTreatment] = useState("")
  const [concentration, setConcentration] = useState("")
  const [preparation, setPreparation] = useState("")
  const [operator, setOperator] = useState("")
  const [notes, setNotes] = useState("")
  
  const { apiConnected, addSample } = useAnalysisStore()
  const { uploadFCS, uploadNTA } = useApi()

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
    if (file) {
      setUploadedFile(file)
    }
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setUploadedFile(file)
    }
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!uploadedFile) return

    setIsUploading(true)

    try {
      const fileName = uploadedFile.name.toLowerCase()
      const isFCS = fileName.endsWith('.fcs')
      const isNTA = fileName.endsWith('.txt') || fileName.endsWith('.csv')

      if (isFCS) {
        await uploadFCS(uploadedFile, {
          treatment: treatment || undefined,
          concentration_ug: concentration ? parseFloat(concentration) : undefined,
          preparation_method: preparation || undefined,
          operator: operator || undefined,
          notes: notes || undefined,
        })
      } else if (isNTA) {
        await uploadNTA(uploadedFile, {
          treatment: treatment || undefined,
          operator: operator || undefined,
          notes: notes || undefined,
        })
      } else {
        // Fallback to local sample storage for unsupported formats
        addSample({
          id: crypto.randomUUID(),
          name: uploadedFile.name,
          type: isFCS ? "fcs" : "nta",
          uploadedAt: new Date(),
          treatment: treatment,
          concentration: concentration ? parseFloat(concentration) : undefined,
          operator: operator,
          notes: notes,
        })
      }

      // Reset form
      setUploadedFile(null)
      setTreatment("")
      setConcentration("")
      setPreparation("")
      setOperator("")
      setNotes("")
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <Card className="card-3d">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-primary/10">
            <Upload className="h-4 w-4 text-primary" />
          </div>
          <CardTitle className="text-base md:text-lg">Quick Upload</CardTitle>
          {!apiConnected && (
            <Badge variant="destructive" className="ml-auto text-xs">
              <AlertCircle className="h-3 w-3 mr-1" />
              Offline
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {!uploadedFile ? (
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
              id="file-upload"
              className="hidden"
              accept=".fcs,.csv,.txt,.xlsx,.parquet"
              onChange={handleFileSelect}
            />
            <label htmlFor="file-upload" className="cursor-pointer">
              <div className="flex flex-col items-center gap-2">
                <div className="p-3 rounded-xl bg-gradient-to-br from-primary/20 to-accent/20 shadow-lg">
                  <FileText className="h-6 w-6 text-primary" />
                </div>
                <p className="text-sm font-medium">Drop files here or click to browse</p>
                <p className="text-xs text-muted-foreground">.fcs, .csv, .txt, .xlsx, .parquet</p>
              </div>
            </label>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-secondary/50 rounded-xl shadow-sm">
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <FileText className="h-4 w-4 text-primary shrink-0" />
                <span className="text-sm font-medium truncate">{uploadedFile.name}</span>
                <Badge variant="outline" className="ml-1 text-xs">
                  {uploadedFile.name.toLowerCase().endsWith('.fcs') ? 'FCS' : 'NTA'}
                </Badge>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-6 w-6 shrink-0"
                onClick={() => setUploadedFile(null)}
                disabled={isUploading}
              >
                <X className="h-3 w-3" />
              </Button>
            </div>

            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label className="text-xs">Treatment</Label>
                <Select value={treatment} onValueChange={setTreatment}>
                  <SelectTrigger className="h-9">
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

              <div className="space-y-1.5">
                <Label className="text-xs">Concentration (µg)</Label>
                <Input 
                  type="number" 
                  step="0.01" 
                  placeholder="0.00" 
                  className="h-9" 
                  value={concentration}
                  onChange={(e) => setConcentration(e.target.value)}
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs">Preparation Method</Label>
                <Select value={preparation} onValueChange={setPreparation}>
                  <SelectTrigger className="h-9">
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

              <div className="space-y-1.5">
                <Label className="text-xs">Operator Name</Label>
                <Input 
                  placeholder="Enter name" 
                  className="h-9" 
                  value={operator}
                  onChange={(e) => setOperator(e.target.value)}
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs">Notes</Label>
                <Textarea 
                  placeholder="Additional notes..." 
                  className="h-20 resize-none" 
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </div>
            </div>

            <Button
              type="submit"
              className="w-full shadow-lg shadow-primary/25 hover:shadow-primary/40 transition-shadow"
              disabled={isUploading || !apiConnected}
            >
              {isUploading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                "Upload & Process"
              )}
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  )
}
