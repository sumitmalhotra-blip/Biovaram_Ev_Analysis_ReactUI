"use client"

import { useEffect, useMemo, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, Microscope, Beaker, Settings, Activity } from "lucide-react"
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

interface NTAMetadataCompareTableProps {
  sampleIds: string[]
  primarySampleId?: string | null
}

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
    ],
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
    ],
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
    ],
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
    ],
  },
]

function getNestedValue(obj: Record<string, any>, path: string): any {
  return path.split(".").reduce((acc, part) => acc && acc[part], obj)
}

function formatValue(value: any, field: { unit?: string; format?: string }): string {
  if (value === null || value === undefined || value === "Unknown") {
    return "N/A"
  }

  if (typeof value === "number") {
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

export function NTAMetadataCompareTable({ sampleIds, primarySampleId }: NTAMetadataCompareTableProps) {
  const effectiveSampleIds = useMemo(
    () => Array.from(new Set(sampleIds)).filter(Boolean).slice(0, 8),
    [sampleIds]
  )

  const [metadataBySampleId, setMetadataBySampleId] = useState<Record<string, NTAMetadataResponse>>({})
  const [errorsBySampleId, setErrorsBySampleId] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (effectiveSampleIds.length < 2) {
      setMetadataBySampleId({})
      setErrorsBySampleId({})
      return
    }

    let isCancelled = false

    const fetchAll = async () => {
      setLoading(true)
      const nextMetadata: Record<string, NTAMetadataResponse> = {}
      const nextErrors: Record<string, string> = {}

      await Promise.all(
        effectiveSampleIds.map(async (sampleId) => {
          try {
            const response = await apiClient.getNTAMetadata(sampleId)
            nextMetadata[sampleId] = response
          } catch (error) {
            nextErrors[sampleId] = error instanceof Error ? error.message : "Failed to load metadata"
          }
        })
      )

      if (isCancelled) return

      setMetadataBySampleId(nextMetadata)
      setErrorsBySampleId(nextErrors)
      setLoading(false)
    }

    fetchAll()

    return () => {
      isCancelled = true
    }
  }, [effectiveSampleIds])

  if (effectiveSampleIds.length < 2) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">
            Select at least two samples in Compare Session to view side-by-side metadata.
          </p>
        </CardContent>
      </Card>
    )
  }

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-5 w-40" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-28 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <Card className="bg-muted/30">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Metadata Comparison</CardTitle>
          <CardDescription>
            Comparing {effectiveSampleIds.length} selected samples.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-2">
          {effectiveSampleIds.map((id) => (
            <Badge key={id} variant={id === primarySampleId ? "default" : "outline"} className="font-mono text-xs">
              {id}
            </Badge>
          ))}
          {Object.entries(errorsBySampleId).map(([id, message]) => (
            <Badge key={id} variant="destructive" className="text-xs" title={message}>
              <AlertCircle className="h-3 w-3 mr-1" />
              {id} metadata unavailable
            </Badge>
          ))}
        </CardContent>
      </Card>

      {CATEGORIES.map((category) => {
        const Icon = category.icon

        return (
          <Card key={category.id} className="card-3d">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-md bg-primary/10">
                  <Icon className="h-4 w-4 text-primary" />
                </div>
                <CardTitle className="text-sm">{category.label}</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full min-w-180 text-xs">
                  <thead>
                    <tr className="border-b border-border/70">
                      <th className="text-left font-medium py-2 pr-2 sticky left-0 bg-background">Parameter</th>
                      {effectiveSampleIds.map((id) => (
                        <th key={id} className="text-left font-medium py-2 px-2">
                          {id}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {category.fields.map((field) => (
                      <tr key={field.key} className="border-b border-border/40 last:border-0">
                        <td className="py-2 pr-2 text-muted-foreground sticky left-0 bg-background">
                          {field.label}
                        </td>
                        {effectiveSampleIds.map((id) => {
                          const metadata = metadataBySampleId[id]
                          const value = metadata ? formatValue(getNestedValue(metadata as unknown as Record<string, any>, field.key), field) : "N/A"
                          const isNA = value === "N/A"
                          return (
                            <td key={`${field.key}-${id}`} className={`py-2 px-2 font-mono ${isNA ? "text-muted-foreground/60" : ""}`}>
                              {value}
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

export default NTAMetadataCompareTable