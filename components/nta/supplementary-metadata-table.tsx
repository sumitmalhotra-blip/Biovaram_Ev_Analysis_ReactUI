"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { 
  Copy, 
  Check, 
  FileText, 
  Microscope, 
  Beaker, 
  Settings, 
  Activity,
  AlertCircle,
  RefreshCw
} from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { apiClient } from "@/lib/api-client"

interface NTAMetadataResponse {
  sample_id: string
  file_info: {
    file_name: string
    file_size_bytes: number
    measurement_type: string
  }
  sample_info: {
    sample_name: string
    operator: string
    experiment: string
    electrolyte: string
  }
  instrument: {
    instrument_serial: string
    cell_serial: string
    software_version: string
    sop: string
  }
  acquisition: {
    date: string
    time: string
    temperature: number | null
    viscosity: number | null
    ph: number | null
    conductivity: number | null
  }
  measurement_params: {
    num_positions: number | null
    num_traces: number | null
    sensitivity: number | null
    shutter: number | null
    laser_wavelength: number | null
    dilution: number
    conc_correction: number
  }
  quality: {
    cell_check_result: string
    detected_particles: number | null
    scattering_intensity: number | null
  }
}

interface SupplementaryMetadataTableProps {
  sampleId?: string
}

// Category definitions for publication table
const CATEGORIES = [
  {
    id: "instrument",
    label: "Instrument Settings",
    icon: Microscope,
    fields: [
      { key: "instrument.instrument_serial", label: "Instrument Serial" },
      { key: "instrument.cell_serial", label: "Cell Serial" },
      { key: "instrument.software_version", label: "Software Version" },
      { key: "instrument.sop", label: "SOP" },
      { key: "measurement_params.laser_wavelength", label: "Laser Wavelength", unit: "nm" },
    ]
  },
  {
    id: "sample",
    label: "Sample Conditions",
    icon: Beaker,
    fields: [
      { key: "acquisition.temperature", label: "Temperature", unit: "°C" },
      { key: "acquisition.ph", label: "pH" },
      { key: "acquisition.conductivity", label: "Conductivity", unit: "mS/cm" },
      { key: "acquisition.viscosity", label: "Viscosity", unit: "cP" },
      { key: "measurement_params.dilution", label: "Dilution Factor", format: "x" },
    ]
  },
  {
    id: "acquisition",
    label: "Acquisition Parameters",
    icon: Settings,
    fields: [
      { key: "acquisition.date", label: "Measurement Date" },
      { key: "acquisition.time", label: "Measurement Time" },
      { key: "measurement_params.num_positions", label: "Number of Positions" },
      { key: "measurement_params.num_traces", label: "Number of Traces" },
      { key: "measurement_params.sensitivity", label: "Sensitivity" },
      { key: "measurement_params.shutter", label: "Shutter" },
    ]
  },
  {
    id: "quality",
    label: "Quality Metrics",
    icon: Activity,
    fields: [
      { key: "quality.cell_check_result", label: "Cell Check Result" },
      { key: "quality.detected_particles", label: "Detected Particles" },
      { key: "quality.scattering_intensity", label: "Scattering Intensity" },
      { key: "measurement_params.conc_correction", label: "Concentration Correction" },
    ]
  },
]

// Helper to get nested value from object
function getNestedValue(obj: Record<string, any>, path: string): any {
  return path.split('.').reduce((acc, part) => acc && acc[part], obj)
}

// Format value for display
function formatValue(value: any, field: { unit?: string; format?: string }): string {
  if (value === null || value === undefined || value === "Unknown") {
    return "N/A"
  }
  
  if (typeof value === "number") {
    // Format numbers appropriately
    if (field.format === "x") {
      return `${value}x`
    }
    if (field.unit) {
      return `${value.toFixed(field.unit === "°C" || field.unit === "cP" ? 1 : 2)} ${field.unit}`
    }
    return value.toLocaleString()
  }
  
  return String(value)
}

export function SupplementaryMetadataTable({ sampleId }: SupplementaryMetadataTableProps) {
  const { toast } = useToast()
  const [metadata, setMetadata] = useState<NTAMetadataResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [copiedSection, setCopiedSection] = useState<string | null>(null)

  // Fetch metadata when sampleId changes
  useEffect(() => {
    if (!sampleId) {
      setMetadata(null)
      return
    }

    const fetchMetadata = async () => {
      setLoading(true)
      setError(null)
      
      try {
        const response = await apiClient.getNTAMetadata(sampleId)
        setMetadata(response)
      } catch (err) {
        console.error("Failed to fetch NTA metadata:", err)
        setError(err instanceof Error ? err.message : "Failed to load metadata")
      } finally {
        setLoading(false)
      }
    }

    fetchMetadata()
  }, [sampleId])

  // Generate plain text table for clipboard (publication format)
  const generatePlainTextTable = (categoryId?: string): string => {
    if (!metadata) return ""

    const categoriesToCopy = categoryId 
      ? CATEGORIES.filter(c => c.id === categoryId)
      : CATEGORIES

    const lines: string[] = []
    
    // Header
    lines.push("=" .repeat(60))
    lines.push("SUPPLEMENTARY TABLE: NTA Measurement Parameters")
    lines.push("=" .repeat(60))
    lines.push(`Sample ID: ${metadata.sample_id}`)
    lines.push(`File: ${metadata.file_info.file_name}`)
    lines.push(`Measurement Type: ${metadata.file_info.measurement_type}`)
    lines.push("-".repeat(60))
    lines.push("")

    categoriesToCopy.forEach(category => {
      lines.push(`### ${category.label}`)
      lines.push("")
      
      // Find max label length for alignment
      const maxLabelLen = Math.max(...category.fields.map(f => f.label.length))
      
      category.fields.forEach(field => {
        const value = getNestedValue(metadata, field.key)
        const formattedValue = formatValue(value, field)
        const paddedLabel = field.label.padEnd(maxLabelLen + 2)
        lines.push(`  ${paddedLabel}: ${formattedValue}`)
      })
      
      lines.push("")
    })

    // Footer
    lines.push("-".repeat(60))
    lines.push(`Generated: ${new Date().toISOString()}`)
    lines.push("Platform: BioVaram EV Analysis Platform")
    
    return lines.join("\n")
  }

  // Generate Markdown table for clipboard
  const generateMarkdownTable = (): string => {
    if (!metadata) return ""

    const lines: string[] = []
    
    lines.push("## Supplementary Table: NTA Measurement Parameters")
    lines.push("")
    lines.push(`**Sample ID:** ${metadata.sample_id}`)
    lines.push(`**File:** ${metadata.file_info.file_name}`)
    lines.push(`**Measurement Type:** ${metadata.file_info.measurement_type}`)
    lines.push("")

    CATEGORIES.forEach(category => {
      lines.push(`### ${category.label}`)
      lines.push("")
      lines.push("| Parameter | Value |")
      lines.push("|-----------|-------|")
      
      category.fields.forEach(field => {
        const value = getNestedValue(metadata, field.key)
        const formattedValue = formatValue(value, field)
        lines.push(`| ${field.label} | ${formattedValue} |`)
      })
      
      lines.push("")
    })

    return lines.join("\n")
  }

  // Copy to clipboard handler
  const handleCopyToClipboard = async (format: "plain" | "markdown", categoryId?: string) => {
    const text = format === "markdown" ? generateMarkdownTable() : generatePlainTextTable(categoryId)
    
    try {
      await navigator.clipboard.writeText(text)
      
      if (categoryId) {
        setCopiedSection(categoryId)
        setTimeout(() => setCopiedSection(null), 2000)
      } else {
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      }
      
      toast({
        title: "Copied to Clipboard",
        description: format === "markdown" 
          ? "Markdown table copied - paste into documents"
          : categoryId 
            ? `${CATEGORIES.find(c => c.id === categoryId)?.label} copied`
            : "Publication-ready table copied",
      })
    } catch (err) {
      toast({
        title: "Copy Failed",
        description: "Failed to copy to clipboard",
        variant: "destructive",
      })
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-4">
          <Skeleton className="h-8 w-8 rounded-lg" />
          <Skeleton className="h-6 w-48" />
        </div>
        {[1, 2, 3, 4].map(i => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-5 w-40" />
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {[1, 2, 3, 4].map(j => (
                  <div key={j} className="flex justify-between">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-4 w-24" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <Card className="border-destructive/50">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center gap-4 text-center">
            <AlertCircle className="h-10 w-10 text-destructive" />
            <div>
              <p className="font-medium text-destructive">Failed to Load Metadata</p>
              <p className="text-sm text-muted-foreground mt-1">{error}</p>
            </div>
            {sampleId && (
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => {
                  setError(null)
                  setLoading(true)
                  apiClient.getNTAMetadata(sampleId)
                    .then(setMetadata)
                    .catch(e => setError(e.message))
                    .finally(() => setLoading(false))
                }}
                className="gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Retry
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    )
  }

  // No sample selected
  if (!sampleId) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center gap-3 text-center py-8">
            <FileText className="h-10 w-10 text-muted-foreground/50" />
            <div>
              <p className="font-medium">No Sample Selected</p>
              <p className="text-sm text-muted-foreground mt-1">
                Upload an NTA file to view metadata
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  // No metadata loaded yet
  if (!metadata) {
    return null
  }

  return (
    <div className="space-y-4">
      {/* Header with copy buttons */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-primary/10">
            <FileText className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h3 className="font-semibold">Supplementary Metadata</h3>
            <p className="text-xs text-muted-foreground">
              Publication-ready parameter table
            </p>
          </div>
        </div>
        
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleCopyToClipboard("plain")}
            className="gap-2"
          >
            {copied ? (
              <>
                <Check className="h-4 w-4 text-green-500" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="h-4 w-4" />
                Copy Table
              </>
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleCopyToClipboard("markdown")}
            className="gap-2"
          >
            <FileText className="h-4 w-4" />
            Copy as Markdown
          </Button>
        </div>
      </div>

      {/* File Info Badge Card */}
      <Card className="bg-muted/30">
        <CardContent className="py-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="font-mono text-xs">
              {metadata.file_info.file_name}
            </Badge>
            <Badge variant="secondary" className="text-xs">
              {metadata.file_info.measurement_type}
            </Badge>
            <Badge variant="secondary" className="text-xs">
              {(metadata.file_info.file_size_bytes / 1024).toFixed(1)} KB
            </Badge>
            {metadata.sample_info.sample_name !== "Unknown" && (
              <Badge variant="outline" className="text-xs">
                {metadata.sample_info.sample_name}
              </Badge>
            )}
            {metadata.sample_info.operator !== "Unknown" && (
              <Badge variant="outline" className="text-xs">
                Operator: {metadata.sample_info.operator}
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Metadata Tables by Category */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {CATEGORIES.map(category => {
          const Icon = category.icon
          
          return (
            <Card key={category.id} className="card-3d">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-md bg-primary/10">
                      <Icon className="h-4 w-4 text-primary" />
                    </div>
                    <CardTitle className="text-sm font-medium">
                      {category.label}
                    </CardTitle>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => handleCopyToClipboard("plain", category.id)}
                    title={`Copy ${category.label}`}
                  >
                    {copiedSection === category.id ? (
                      <Check className="h-3.5 w-3.5 text-green-500" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-1.5">
                  {category.fields.map(field => {
                    const value = getNestedValue(metadata, field.key)
                    const formattedValue = formatValue(value, field)
                    const isNA = formattedValue === "N/A"
                    
                    return (
                      <div 
                        key={field.key} 
                        className="flex justify-between items-center py-1 border-b border-border/50 last:border-0"
                      >
                        <span className="text-xs text-muted-foreground">
                          {field.label}
                        </span>
                        <span className={`text-xs font-mono ${isNA ? "text-muted-foreground/60" : "font-medium"}`}>
                          {formattedValue}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Publication Usage Note */}
      <Card className="bg-blue-500/5 border-blue-500/20">
        <CardContent className="py-3">
          <div className="flex items-start gap-3">
            <div className="p-1.5 rounded-md bg-blue-500/10 mt-0.5">
              <FileText className="h-4 w-4 text-blue-500" />
            </div>
            <div className="text-sm">
              <p className="font-medium text-blue-700 dark:text-blue-400">
                Publication Ready
              </p>
              <p className="text-muted-foreground text-xs mt-1">
                This metadata table follows MISEV2018/2023 guidelines for reporting 
                NTA measurements. Use "Copy Table" to paste directly into your 
                manuscript's supplementary materials section.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default SupplementaryMetadataTable
