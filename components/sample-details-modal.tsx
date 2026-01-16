"use client"

import { useEffect, useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  FileText,
  Calendar,
  User,
  Beaker,
  ClipboardList,
  AlertCircle,
  Download,
  ExternalLink,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Microscope,
  FlaskConical,
} from "lucide-react"
import type { Sample, FCSResult, NTAResult } from "@/lib/api-client"

interface SampleDetailsModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sampleId: string | null
  onFetchSample: (sampleId: string) => Promise<Sample | null>
  onFetchFCSResults?: (sampleId: string) => Promise<FCSResult[] | { sample_id: string; results: FCSResult[] } | null>
  onFetchNTAResults?: (sampleId: string) => Promise<NTAResult[] | { sample_id: string; results: NTAResult[] } | null>
  onDelete?: (sampleId: string) => void
  onExport?: (sampleId: string) => void
  onOpenInTab?: (sampleId: string, type: "fcs" | "nta") => void
}

export function SampleDetailsModal({
  open,
  onOpenChange,
  sampleId,
  onFetchSample,
  onFetchFCSResults,
  onFetchNTAResults,
  onDelete,
  onExport,
  onOpenInTab,
}: SampleDetailsModalProps) {
  const [sample, setSample] = useState<Sample | null>(null)
  const [fcsResults, setFcsResults] = useState<FCSResult[]>([])
  const [ntaResults, setNtaResults] = useState<NTAResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open && sampleId) {
      loadSampleDetails()
    }
  }, [open, sampleId])

  const loadSampleDetails = async () => {
    if (!sampleId) return

    setLoading(true)
    setError(null)

    try {
      // Fetch sample details
      const sampleData = await onFetchSample(sampleId)
      if (sampleData) {
        setSample(sampleData)

        // Fetch FCS results if available
        if (onFetchFCSResults && sampleData.files?.fcs) {
          const fcsData = await onFetchFCSResults(sampleId)
          if (fcsData) {
            // Handle both array and object with results property
            const results = Array.isArray(fcsData) ? fcsData : fcsData.results
            setFcsResults(results)
          }
        }

        // Fetch NTA results if available
        if (onFetchNTAResults && sampleData.files?.nta) {
          const ntaData = await onFetchNTAResults(sampleId)
          if (ntaData) {
            // Handle both array and object with results property
            const results = Array.isArray(ntaData) ? ntaData : ntaData.results
            setNtaResults(results)
          }
        }
      } else {
        setError("Failed to load sample details")
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred")
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (status?: string) => {
    if (!status) return null

    const variants: Record<string, { variant: "default" | "secondary" | "destructive" | "outline"; icon: any }> = {
      completed: { variant: "default", icon: CheckCircle2 },
      processing: { variant: "secondary", icon: Clock },
      failed: { variant: "destructive", icon: XCircle },
      pending: { variant: "outline", icon: Clock },
    }

    const config = variants[status.toLowerCase()] || variants.pending
    const Icon = config.icon

    return (
      <Badge variant={config.variant} className="gap-1">
        <Icon className="h-3 w-3" />
        {status}
      </Badge>
    )
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return "N/A"
    return new Date(dateString).toLocaleString()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] md:max-h-[85vh] w-[calc(100%-2rem)] md:w-full">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Sample Details
          </DialogTitle>
          <DialogDescription>
            {sampleId ? `Viewing details for sample ${sampleId}` : "No sample selected"}
          </DialogDescription>
        </DialogHeader>

        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
            <div>
              <p className="font-semibold text-destructive">Error loading sample</p>
              <p className="text-sm text-destructive/80">{error}</p>
            </div>
          </div>
        )}

        {!loading && !error && sample && (
          <ScrollArea className="max-h-[70vh] pr-4">
            <div className="space-y-6">
              {/* Header with Status */}
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <h3 className="text-xl font-semibold">{sample.sample_id}</h3>
                  {sample.biological_sample_id && (
                    <p className="text-sm text-muted-foreground">
                      Biological ID: {sample.biological_sample_id}
                    </p>
                  )}
                </div>
                <div className="flex flex-col gap-2">
                  {getStatusBadge(sample.processing_status)}
                  {getStatusBadge(sample.qc_status)}
                </div>
              </div>

              <Separator />

              {/* Sample Information */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <ClipboardList className="h-4 w-4" />
                    Sample Information
                  </CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-2 gap-4 text-sm">
                  {sample.treatment && (
                    <div>
                      <span className="text-muted-foreground">Treatment:</span>
                      <p className="font-medium">{sample.treatment}</p>
                    </div>
                  )}
                  {sample.concentration_ug !== undefined && (
                    <div>
                      <span className="text-muted-foreground">Concentration:</span>
                      <p className="font-medium">{sample.concentration_ug} µg/mL</p>
                    </div>
                  )}
                  {sample.preparation_method && (
                    <div>
                      <span className="text-muted-foreground">Preparation Method:</span>
                      <p className="font-medium">{sample.preparation_method}</p>
                    </div>
                  )}
                  {sample.passage_number !== undefined && (
                    <div>
                      <span className="text-muted-foreground">Passage Number:</span>
                      <p className="font-medium">{sample.passage_number}</p>
                    </div>
                  )}
                  {sample.fraction_number && (
                    <div>
                      <span className="text-muted-foreground">Fraction Number:</span>
                      <p className="font-medium">{sample.fraction_number}</p>
                    </div>
                  )}
                  {sample.operator && (
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <span className="text-muted-foreground">Operator:</span>
                        <p className="font-medium">{sample.operator}</p>
                      </div>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <span className="text-muted-foreground">Upload Date:</span>
                      <p className="font-medium text-xs">{formatDate(sample.upload_timestamp)}</p>
                    </div>
                  </div>
                  {sample.experiment_date && (
                    <div className="flex items-center gap-2">
                      <Beaker className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <span className="text-muted-foreground">Experiment Date:</span>
                        <p className="font-medium text-xs">{formatDate(sample.experiment_date)}</p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Notes */}
              {sample.notes && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Notes</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground whitespace-pre-wrap">{sample.notes}</p>
                  </CardContent>
                </Card>
              )}

              {/* Results Tabs */}
              {(fcsResults.length > 0 || ntaResults.length > 0) && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Analysis Results</CardTitle>
                    <CardDescription>
                      {sample.results?.fcs_count || 0} FCS results, {sample.results?.nta_count || 0} NTA results
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Tabs defaultValue={fcsResults.length > 0 ? "fcs" : "nta"}>
                      <TabsList className="w-full">
                        {fcsResults.length > 0 && (
                          <TabsTrigger value="fcs" className="flex-1">
                            FCS Results ({fcsResults.length})
                          </TabsTrigger>
                        )}
                        {ntaResults.length > 0 && (
                          <TabsTrigger value="nta" className="flex-1">
                            NTA Results ({ntaResults.length})
                          </TabsTrigger>
                        )}
                      </TabsList>

                      {fcsResults.length > 0 && (
                        <TabsContent value="fcs" className="space-y-3">
                          {fcsResults.map((result, idx) => (
                            <div key={result.id || idx} className="rounded-lg border p-4 space-y-2">
                              <div className="grid grid-cols-2 gap-3 text-sm">
                                <div>
                                  <span className="text-muted-foreground">Total Events:</span>
                                  <p className="font-medium">{result.total_events?.toLocaleString()}</p>
                                </div>
                                {result.particle_size_median_nm && (
                                  <div>
                                    <span className="text-muted-foreground">Median Size:</span>
                                    <p className="font-medium">{result.particle_size_median_nm.toFixed(1)} nm</p>
                                  </div>
                                )}
                                {result.fsc_median && (
                                  <div>
                                    <span className="text-muted-foreground">FSC Median:</span>
                                    <p className="font-medium">{result.fsc_median.toLocaleString()}</p>
                                  </div>
                                )}
                                {result.ssc_median && (
                                  <div>
                                    <span className="text-muted-foreground">SSC Median:</span>
                                    <p className="font-medium">{result.ssc_median.toLocaleString()}</p>
                                  </div>
                                )}
                              </div>
                              {result.processed_at && (
                                <p className="text-xs text-muted-foreground">
                                  Processed: {formatDate(result.processed_at)}
                                </p>
                              )}
                            </div>
                          ))}
                        </TabsContent>
                      )}

                      {ntaResults.length > 0 && (
                        <TabsContent value="nta" className="space-y-3">
                          {ntaResults.map((result, idx) => (
                            <div key={result.id || idx} className="rounded-lg border p-4 space-y-2">
                              <div className="grid grid-cols-2 gap-3 text-sm">
                                {result.mean_size_nm && (
                                  <div>
                                    <span className="text-muted-foreground">Mean Size:</span>
                                    <p className="font-medium">{result.mean_size_nm.toFixed(1)} nm</p>
                                  </div>
                                )}
                                {result.median_size_nm && (
                                  <div>
                                    <span className="text-muted-foreground">Median Size:</span>
                                    <p className="font-medium">{result.median_size_nm.toFixed(1)} nm</p>
                                  </div>
                                )}
                                {result.concentration_particles_ml && (
                                  <div>
                                    <span className="text-muted-foreground">Concentration:</span>
                                    <p className="font-medium">
                                      {result.concentration_particles_ml.toExponential(2)} /mL
                                    </p>
                                  </div>
                                )}
                                {result.temperature_celsius && (
                                  <div>
                                    <span className="text-muted-foreground">Temperature:</span>
                                    <p className="font-medium">{result.temperature_celsius}°C</p>
                                  </div>
                                )}
                              </div>
                              {result.processed_at && (
                                <p className="text-xs text-muted-foreground">
                                  Processed: {formatDate(result.processed_at)}
                                </p>
                              )}
                            </div>
                          ))}
                        </TabsContent>
                      )}
                    </Tabs>
                  </CardContent>
                </Card>
              )}

              {/* Files */}
              {sample.files && Object.keys(sample.files).length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Uploaded Files</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {sample.files.fcs && (
                      <div className="flex items-center justify-between p-2 rounded-lg border">
                        <div className="flex items-center gap-2">
                          <FlaskConical className="h-4 w-4 text-blue-500" />
                          <span className="text-sm font-medium">FCS File</span>
                        </div>
                        <div className="flex items-center gap-1">
                          {onOpenInTab && fcsResults.length > 0 && (
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => {
                                onOpenInTab(sample.sample_id, "fcs")
                                onOpenChange(false)
                              }}
                              className="gap-1"
                            >
                              <ExternalLink className="h-3 w-3" />
                              Open in Tab
                            </Button>
                          )}
                        </div>
                      </div>
                    )}
                    {sample.files.nta && (
                      <div className="flex items-center justify-between p-2 rounded-lg border">
                        <div className="flex items-center gap-2">
                          <Microscope className="h-4 w-4 text-green-500" />
                          <span className="text-sm font-medium">NTA File</span>
                        </div>
                        <div className="flex items-center gap-1">
                          {onOpenInTab && ntaResults.length > 0 && (
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => {
                                onOpenInTab(sample.sample_id, "nta")
                                onOpenChange(false)
                              }}
                              className="gap-1"
                            >
                              <ExternalLink className="h-3 w-3" />
                              Open in Tab
                            </Button>
                          )}
                        </div>
                      </div>
                    )}
                    {sample.files.tem && (
                      <div className="flex items-center justify-between p-2 rounded-lg border">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-purple-500" />
                          <span className="text-sm font-medium">TEM File</span>
                        </div>
                        <Button variant="ghost" size="sm">
                          <ExternalLink className="h-3 w-3" />
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Action Buttons */}
              <div className="flex items-center gap-2 pt-4">
                {onExport && (
                  <Button variant="outline" onClick={() => onExport(sample.sample_id)} className="flex-1">
                    <Download className="mr-2 h-4 w-4" />
                    Export Data
                  </Button>
                )}
                {onDelete && (
                  <Button
                    variant="destructive"
                    onClick={() => {
                      onDelete(sample.sample_id)
                      onOpenChange(false)
                    }}
                    className="flex-1"
                  >
                    Delete Sample
                  </Button>
                )}
              </div>
            </div>
          </ScrollArea>
        )}
      </DialogContent>
    </Dialog>
  )
}
