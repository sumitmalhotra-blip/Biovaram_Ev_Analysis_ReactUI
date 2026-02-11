"use client"

import { useState, useEffect, useMemo, useCallback } from "react"
import { useAnalysisStore, type SizeRange } from "@/lib/store"
import { useApi } from "@/hooks/use-api"
import { cn } from "@/lib/utils"
import { ChevronLeft, ChevronRight, Filter, Settings, FileText, Beaker, Thermometer, Loader2, RefreshCw, Database, SlidersHorizontal, Play, RotateCcw, Plus, Trash2, FlaskConical, Shield, Target, CheckCircle2, XCircle } from "lucide-react"
import { BestPracticesPanel } from "@/components/best-practices-panel"
import { PreviousAnalyses } from "@/components/previous-analyses"
import type { ExperimentData } from "@/lib/best-practices"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Slider } from "@/components/ui/slider"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/hooks/use-toast"
import { ExperimentalConditionsDialog, type ExperimentalConditions } from "@/components/experimental-conditions-dialog"

interface SidebarProps {
  isMobile?: boolean
}

export function Sidebar({ isMobile = false }: SidebarProps) {
  const { sidebarCollapsed, toggleSidebar, activeTab, samples, apiSamples, samplesLoading, apiConnected } = useAnalysisStore()
  const { fetchSamples, openSampleInTab } = useApi()

  // Fetch samples on mount only if API is connected
  // PERFORMANCE FIX: Remove fetchSamples from deps to prevent infinite loop
  useEffect(() => {
    if (apiConnected) {
      fetchSamples()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiConnected])

  const isCollapsed = isMobile ? false : sidebarCollapsed

  return (
    <aside
      className={cn(
        "border-r border-border bg-sidebar transition-all duration-300 flex flex-col h-full overflow-hidden",
        isMobile ? "w-full" : isCollapsed ? "w-14" : "w-72",
      )}
    >
      {!isMobile && (
        <div className="flex items-center justify-end p-2 border-b border-border shrink-0">
          <Button variant="ghost" size="icon" onClick={toggleSidebar} className="h-8 w-8">
            {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </Button>
        </div>
      )}

      {!isCollapsed && (
        <ScrollArea className="flex-1 overflow-hidden">
          <div className="p-4 space-y-4 overflow-hidden">
            {/* Previous Analyses Section - Visible in all tabs */}
            <PreviousAnalyses 
              compact={activeTab !== "dashboard"} 
              defaultExpanded={activeTab === "dashboard"}
            />

            {/* Tab-specific content */}
            {activeTab === "flow-cytometry" && <FlowCytometrySidebar />}
            {activeTab === "nta" && <NTASidebar />}
            {activeTab === "cross-compare" && <CrossCompareSidebar />}
            {activeTab === "dashboard" && (
              <DashboardSidebar 
                samples={samples} 
                apiSamples={apiSamples} 
                samplesLoading={samplesLoading} 
                fetchSamples={fetchSamples}
                onSampleClick={openSampleInTab}
              />
            )}
          </div>
        </ScrollArea>
      )}

      {isCollapsed && !isMobile && (
        <div className="flex flex-col items-center gap-2 p-2">
          <Button variant="ghost" size="icon" className="h-10 w-10">
            <Filter className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-10 w-10">
            <Settings className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-10 w-10">
            <FileText className="h-4 w-4" />
          </Button>
        </div>
      )}
    </aside>
  )
}

function DashboardSidebar({ 
  samples, 
  apiSamples, 
  samplesLoading,
  fetchSamples,
  onSampleClick,
}: { 
  samples: { id: string; name: string; type: string }[]
  apiSamples: { id: number; sample_id: string; treatment?: string; files?: { fcs?: string; nta?: string } }[]
  samplesLoading: boolean
  fetchSamples: () => void
  onSampleClick?: (sampleId: string, type: "fcs" | "nta") => void
}) {
  const [treatmentFilter, setTreatmentFilter] = useState<string>("all")
  const [statusFilter, setStatusFilter] = useState<string>("all")

  // Get unique treatments from samples
  const treatments = useMemo(() => {
    const uniqueTreatments = new Set<string>()
    apiSamples.forEach(s => {
      if (s.treatment) uniqueTreatments.add(s.treatment)
    })
    return Array.from(uniqueTreatments)
  }, [apiSamples])

  // Filter samples based on selected filters
  const filteredApiSamples = useMemo(() => {
    return apiSamples.filter(sample => {
      // Treatment filter
      if (treatmentFilter !== "all" && sample.treatment !== treatmentFilter) {
        return false
      }
      // Status filter (based on whether they have FCS/NTA files)
      if (statusFilter === "fcs" && !sample.files?.fcs) return false
      if (statusFilter === "nta" && !sample.files?.nta) return false
      if (statusFilter === "both" && (!sample.files?.fcs || !sample.files?.nta)) return false
      return true
    })
  }, [apiSamples, treatmentFilter, statusFilter])

  const totalSamples = filteredApiSamples.length + samples.length

  return (
    <div className="space-y-4">
      {/* Filters Section */}
      <Accordion type="single" collapsible defaultValue="filters">
        <AccordionItem value="filters" className="border rounded-lg px-3">
          <AccordionTrigger className="text-sm font-medium py-3">
            <span className="flex items-center gap-2">
              <SlidersHorizontal className="h-4 w-4 text-primary" />
              Filters
            </span>
          </AccordionTrigger>
          <AccordionContent className="space-y-3 pb-4">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Treatment</Label>
              <Select value={treatmentFilter} onValueChange={setTreatmentFilter}>
                <SelectTrigger className="h-8">
                  <SelectValue placeholder="All treatments" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Treatments</SelectItem>
                  <SelectItem value="CD81">CD81</SelectItem>
                  <SelectItem value="CD9">CD9</SelectItem>
                  <SelectItem value="CD63">CD63</SelectItem>
                  <SelectItem value="Isotype">Isotype Control</SelectItem>
                  <SelectItem value="Unstained">Unstained</SelectItem>
                  {treatments.filter(t => !["CD81", "CD9", "CD63", "Isotype", "Unstained"].includes(t)).map(t => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">File Status</Label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="h-8">
                  <SelectValue placeholder="All files" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Files</SelectItem>
                  <SelectItem value="fcs">FCS Only</SelectItem>
                  <SelectItem value="nta">NTA Only</SelectItem>
                  <SelectItem value="both">Has Both</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {(treatmentFilter !== "all" || statusFilter !== "all") && (
              <Button 
                variant="ghost" 
                size="sm" 
                className="w-full h-7 text-xs"
                onClick={() => {
                  setTreatmentFilter("all")
                  setStatusFilter("all")
                }}
              >
                Clear Filters
              </Button>
            )}
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      {/* Samples List */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium flex items-center gap-2">
            <Database className="h-4 w-4 text-primary" />
            Samples
            {totalSamples > 0 && (
              <Badge variant="secondary" className="text-xs">{totalSamples}</Badge>
            )}
          </h3>
          <Button 
            variant="ghost" 
            size="icon" 
            className="h-6 w-6"
            onClick={() => fetchSamples()}
            disabled={samplesLoading}
          >
            {samplesLoading ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <RefreshCw className="h-3 w-3" />
            )}
          </Button>
        </div>

        {samplesLoading && apiSamples.length === 0 ? (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : totalSamples === 0 ? (
          <p className="text-sm text-muted-foreground">
            {apiSamples.length > 0 ? "No samples match filters" : "No samples uploaded yet"}
          </p>
        ) : (
          <div className="space-y-1 overflow-hidden">
            {/* API Samples */}
            {filteredApiSamples.slice(0, 5).map((sample) => (
              <div 
                key={sample.id} 
                className="text-sm p-2 rounded-md hover:bg-secondary/50 cursor-pointer flex items-center justify-between group overflow-hidden"
              >
                <div className="flex-1 min-w-0 overflow-hidden">
                  <span className="truncate block max-w-[140px]" title={sample.sample_id}>{sample.sample_id}</span>
                  {sample.treatment && (
                    <span className="text-[10px] text-muted-foreground truncate block">{sample.treatment}</span>
                  )}
                </div>
                <div className="flex gap-1 shrink-0">
                  {sample.files?.fcs && (
                    <Badge 
                      variant="outline" 
                      className="text-[10px] px-1 hover:bg-primary hover:text-primary-foreground cursor-pointer transition-colors"
                      onClick={() => onSampleClick?.(sample.sample_id, "fcs")}
                      title="Open in Flow Cytometry tab"
                    >
                      FCS
                    </Badge>
                  )}
                  {sample.files?.nta && (
                    <Badge 
                      variant="outline" 
                      className="text-[10px] px-1 hover:bg-primary hover:text-primary-foreground cursor-pointer transition-colors"
                      onClick={() => onSampleClick?.(sample.sample_id, "nta")}
                      title="Open in NTA tab"
                    >
                      NTA
                    </Badge>
                  )}
                </div>
              </div>
            ))}
            
            {/* Local Samples (fallback) */}
            {samples.slice(0, Math.max(0, 5 - filteredApiSamples.length)).map((sample) => (
              <div 
                key={sample.id} 
                className="text-sm p-2 rounded-md hover:bg-secondary/50 cursor-pointer flex items-center justify-between overflow-hidden"
              >
                <span className="truncate flex-1 max-w-[140px]" title={sample.name}>{sample.name}</span>
                <Badge variant="secondary" className="text-[10px] px-1 shrink-0">
                  {sample.type.toUpperCase()}
                </Badge>
              </div>
            ))}

            {totalSamples > 5 && (
              <p className="text-xs text-muted-foreground text-center pt-2">
                +{totalSamples - 5} more samples
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function FlowCytometrySidebar() {
  const { toast } = useToast()
  const { 
    fcsAnalysisSettings, 
    setFcsAnalysisSettings, 
    fcsAnalysis,
    setFCSSizeRanges,
    setFCSExperimentalConditions,
    apiConnected,
  } = useAnalysisStore()
  const { reanalyzeWithSettings } = useApi()

  // Dialog state
  const [showConditionsDialog, setShowConditionsDialog] = useState(false)

  // Calibration status for badge
  const [calStatus, setCalStatus] = useState<{ calibrated: boolean; kit_name?: string; r_squared?: number; n_beads?: number } | null>(null)

  // Fetch calibration status on mount
  useEffect(() => {
    if (!apiConnected) return
    const fetchCalStatus = async () => {
      try {
        const { apiClient } = await import("@/lib/api-client")
        const status = await apiClient.getCalibrationStatus()
        setCalStatus(status)
      } catch {
        // silently fail
      }
    }
    fetchCalStatus()
  }, [apiConnected])

  // Local state initialized from store (with defaults)
  const [wavelength, setWavelength] = useState(fcsAnalysisSettings?.laserWavelength?.toString() || "488")
  const [medium, setMedium] = useState("pbs")
  const [particleRI, setParticleRI] = useState(fcsAnalysisSettings?.particleRI || 1.40)
  const [anomalyEnabled, setAnomalyEnabled] = useState(fcsAnalysisSettings?.anomalyDetectionEnabled ?? true)
  const [anomalyMethod, setAnomalyMethod] = useState<"Z-Score" | "IQR" | "Both">(fcsAnalysisSettings?.anomalyMethod || "Both")
  const [zscoreThreshold, setZscoreThreshold] = useState(fcsAnalysisSettings?.zscoreThreshold || 3.0)
  const [iqrFactor, setIqrFactor] = useState(fcsAnalysisSettings?.iqrFactor || 1.5)
  const [activePreset, setActivePreset] = useState<"standard" | "exosome" | "isev2023" | "custom">("standard")
  const [hasChanges, setHasChanges] = useState(false)
  // Angle range state for Mie scattering integration
  const [fscAngleRange, setFscAngleRange] = useState<[number, number]>(fcsAnalysisSettings?.fscAngleRange || [1, 15])
  const [sscAngleRange, setSscAngleRange] = useState<[number, number]>(fcsAnalysisSettings?.sscAngleRange || [85, 95])
  // Custom size range editing state
  const [editingRanges, setEditingRanges] = useState(false)
  const [newRangeName, setNewRangeName] = useState("")
  const [newRangeMin, setNewRangeMin] = useState(30)
  const [newRangeMax, setNewRangeMax] = useState(100)

  // Size range presets based on ISEV 2023 guidelines
  const SIZE_PRESETS = {
    standard: [
      { name: "Small EVs (<50nm)", min: 0, max: 50, color: "#22c55e" },
      { name: "Exosomes (50-200nm)", min: 50, max: 200, color: "#3b82f6" },
      { name: "Microvesicles (>200nm)", min: 200, max: 1000, color: "#f59e0b" },
    ],
    exosome: [
      { name: "Exosomes (40-80nm)", min: 40, max: 80, color: "#22c55e" },
      { name: "Small MVs (80-120nm)", min: 80, max: 120, color: "#3b82f6" },
    ],
    isev2023: [
      { name: "Exomeres", min: 0, max: 50, color: "#22c55e" },
      { name: "Small EVs", min: 50, max: 100, color: "#3b82f6" },
      { name: "Medium EVs", min: 100, max: 200, color: "#a855f7" },
      { name: "Large EVs", min: 200, max: 500, color: "#f59e0b" },
    ],
  }

  const currentSizeRanges = fcsAnalysis.sizeRanges || SIZE_PRESETS.standard

  // Medium RI mapping
  const MEDIUM_RI: Record<string, number> = {
    water: 1.33,
    pbs: 1.34,
    culture: 1.35,
  }

  // Sync local state when store changes
  useEffect(() => {
    if (fcsAnalysisSettings) {
      setWavelength(fcsAnalysisSettings.laserWavelength?.toString() || "488")
      setParticleRI(fcsAnalysisSettings.particleRI || 1.40)
      setAnomalyEnabled(fcsAnalysisSettings.anomalyDetectionEnabled ?? true)
      setAnomalyMethod(fcsAnalysisSettings.anomalyMethod || "Both")
      setZscoreThreshold(fcsAnalysisSettings.zscoreThreshold || 3.0)
      setIqrFactor(fcsAnalysisSettings.iqrFactor || 1.5)
      setFscAngleRange(fcsAnalysisSettings.fscAngleRange || [1, 15])
      setSscAngleRange(fcsAnalysisSettings.sscAngleRange || [85, 95])
    }
  }, [fcsAnalysisSettings])

  // Update store when settings change
  const updateSettings = useCallback(() => {
    const newSettings = {
      laserWavelength: parseInt(wavelength),
      particleRI,
      mediumRI: MEDIUM_RI[medium] || 1.33,
      fscRange: fcsAnalysisSettings?.fscRange || [1, 65535] as [number, number],
      sscRange: fcsAnalysisSettings?.sscRange || [1, 65535] as [number, number],
      fscAngleRange,
      sscAngleRange,
      diameterRange: fcsAnalysisSettings?.diameterRange || [30, 200] as [number, number],
      diameterPoints: fcsAnalysisSettings?.diameterPoints || 180,
      sizeRanges: currentSizeRanges,
      ignoreNegativeH: fcsAnalysisSettings?.ignoreNegativeH ?? true,
      dropNaRows: fcsAnalysisSettings?.dropNaRows ?? true,
      anomalyDetectionEnabled: anomalyEnabled,
      anomalyMethod,
      zscoreThreshold,
      iqrFactor,
      highlightAnomalies: fcsAnalysisSettings?.highlightAnomalies ?? true,
      useInteractivePlots: fcsAnalysisSettings?.useInteractivePlots ?? true,
    }
    setFcsAnalysisSettings(newSettings)
    setHasChanges(true)
  }, [wavelength, medium, particleRI, fscAngleRange, sscAngleRange, anomalyEnabled, anomalyMethod, zscoreThreshold, iqrFactor, currentSizeRanges, fcsAnalysisSettings, setFcsAnalysisSettings])

  // Handle preset change
  const handlePresetChange = (preset: "standard" | "exosome" | "isev2023" | "custom") => {
    setActivePreset(preset)
    if (preset !== "custom" && SIZE_PRESETS[preset]) {
      setFCSSizeRanges(SIZE_PRESETS[preset])
      setHasChanges(true)
      setEditingRanges(false)
    } else if (preset === "custom") {
      setEditingRanges(true)
    }
  }

  // Add a new custom size range
  const handleAddRange = () => {
    if (newRangeName.trim() && newRangeMin < newRangeMax) {
      const colors = ["#22c55e", "#3b82f6", "#a855f7", "#f59e0b", "#ef4444", "#06b6d4"]
      const newRange: SizeRange = {
        name: newRangeName.trim(),
        min: newRangeMin,
        max: newRangeMax,
        color: colors[currentSizeRanges.length % colors.length],
      }
      setFCSSizeRanges([...currentSizeRanges, newRange])
      setNewRangeName("")
      setNewRangeMin(30)
      setNewRangeMax(100)
      setHasChanges(true)
    }
  }

  // Remove a size range
  const handleRemoveRange = (index: number) => {
    const updated = currentSizeRanges.filter((_, i) => i !== index)
    setFCSSizeRanges(updated)
    setHasChanges(true)
  }

  // Handle re-analyze
  const handleReanalyze = async () => {
    if (!fcsAnalysis.sampleId) {
      toast({
        title: "No sample loaded",
        description: "Please upload an FCS file first",
        variant: "destructive",
      })
      return
    }

    updateSettings()
    
    // Trigger re-analysis with new settings
    if (reanalyzeWithSettings) {
      toast({
        title: "Re-analyzing...",
        description: "Applying new settings to the analysis",
      })
      
      // Map medium to refractive index
      const mediumRIMap: Record<string, number> = {
        water: 1.33,
        pbs: 1.34,
        culture: 1.35,
      }
      
      await reanalyzeWithSettings(fcsAnalysis.sampleId, {
        // Optical parameters
        wavelength_nm: parseInt(wavelength),
        n_particle: particleRI,
        n_medium: mediumRIMap[medium] || 1.33,
        // Angular parameters for Mie scattering
        fsc_angle_range: fscAngleRange,
        ssc_angle_range: sscAngleRange,
        // Anomaly detection
        anomaly_detection: anomalyEnabled,
        anomaly_method: anomalyMethod.toLowerCase().replace("-", ""),
        zscore_threshold: zscoreThreshold,
        iqr_factor: iqrFactor,
        // Size ranges
        size_ranges: currentSizeRanges.map(r => ({
          name: r.name,
          min: r.min,
          max: r.max,
        })),
      })
      setHasChanges(false)
    } else {
      toast({
        title: "Settings saved",
        description: "Settings will be applied to the next analysis",
      })
      setHasChanges(false)
    }
  }

  // Handle saving experimental conditions
  const handleSaveConditions = (conditions: ExperimentalConditions) => {
    setFCSExperimentalConditions(conditions)
    setShowConditionsDialog(false)
    toast({
      title: "✅ Conditions saved",
      description: `Experimental conditions recorded for ${fcsAnalysis.sampleId || "sample"}`,
    })
  }

  return (
    <>
      {/* Calibration Status Badge */}
      <div className="mb-3 flex items-center gap-2 px-1 py-1.5 rounded-md border bg-muted/30">
        <Target className="h-3.5 w-3.5 text-primary shrink-0" />
        <span className="text-xs truncate flex-1">Bead Calibration</span>
        {calStatus?.calibrated ? (
          <Badge variant="default" className="bg-green-600 hover:bg-green-700 text-[10px] px-1.5 py-0 shrink-0">
            <CheckCircle2 className="h-2.5 w-2.5 mr-0.5" />
            R²={calStatus.r_squared?.toFixed(3)}
          </Badge>
        ) : (
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0 shrink-0">
            <XCircle className="h-2.5 w-2.5 mr-0.5" />
            Not Set
          </Badge>
        )}
      </div>

      {/* Experimental Conditions Button */}
      <div className="mb-3">
        <Button
          variant="outline"
          size="sm"
          className="w-full gap-2 text-xs overflow-hidden"
          onClick={() => setShowConditionsDialog(true)}
        >
          <FlaskConical className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">
            {fcsAnalysis.experimentalConditions ? "Edit Conditions" : "Record Conditions"}
          </span>
          {fcsAnalysis.experimentalConditions && (
            <Badge variant="secondary" className="ml-auto text-[10px] px-1 shrink-0">Saved</Badge>
          )}
        </Button>
      </div>

      <Accordion type="multiple" defaultValue={["params", "angles", "analysis", "categories"]} className="space-y-2">
        <AccordionItem value="params" className="border rounded-lg px-3">
          <AccordionTrigger className="text-sm font-medium py-3">
            <span className="flex items-center gap-2">
              <Beaker className="h-4 w-4 text-primary" />
              Experiment Parameters
            </span>
          </AccordionTrigger>
          <AccordionContent className="space-y-4 pb-4">
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Refractive Index</Label>
              <div className="flex items-center gap-2">
                <Slider 
                  value={[particleRI]} 
                  min={1.35} 
                  max={1.6} 
                  step={0.01} 
                  className="flex-1"
                onValueChange={(v) => {
                  setParticleRI(v[0])
                  setHasChanges(true)
                }}
                onValueCommit={() => updateSettings()}
              />
              <span className="text-sm font-mono w-12">{particleRI.toFixed(2)}</span>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Laser Wavelength</Label>
            <Select 
              value={wavelength} 
              onValueChange={(v) => {
                setWavelength(v)
                setHasChanges(true)
                updateSettings()
              }}
            >
              <SelectTrigger className="h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="405">405nm</SelectItem>
                <SelectItem value="488">488nm</SelectItem>
                <SelectItem value="561">561nm</SelectItem>
                <SelectItem value="640">640nm</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Medium</Label>
            <Select 
              value={medium} 
              onValueChange={(v) => {
                setMedium(v)
                setHasChanges(true)
                updateSettings()
              }}
            >
              <SelectTrigger className="h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="water">Water</SelectItem>
                <SelectItem value="pbs">PBS</SelectItem>
                <SelectItem value="culture">Culture Media</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="angles" className="border rounded-lg px-3">
        <AccordionTrigger className="text-sm font-medium py-3">
          <span className="flex items-center gap-2">
            <SlidersHorizontal className="h-4 w-4 text-primary" />
            Angular Parameters
          </span>
        </AccordionTrigger>
        <AccordionContent className="space-y-4 pb-4">
          <div className="text-xs text-muted-foreground mb-2">
            Mie scattering integration angle ranges for FSC/SSC signal calculation.
          </div>
          
          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">FSC Angle Range (°)</Label>
            <div className="flex items-center gap-2">
              <Slider 
                value={fscAngleRange}
                min={0} 
                max={30} 
                step={1} 
                className="flex-1"
                onValueChange={(v) => {
                  setFscAngleRange([v[0], v[1]])
                  setHasChanges(true)
                }}
                onValueCommit={() => updateSettings()}
              />
              <span className="text-xs font-mono w-14 text-right">{fscAngleRange[0]}–{fscAngleRange[1]}°</span>
            </div>
            <p className="text-[10px] text-muted-foreground">Forward scatter (typical: 1-15°)</p>
          </div>

          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">SSC Angle Range (°)</Label>
            <div className="flex items-center gap-2">
              <Slider 
                value={sscAngleRange}
                min={30} 
                max={180} 
                step={1} 
                className="flex-1"
                onValueChange={(v) => {
                  setSscAngleRange([v[0], v[1]])
                  setHasChanges(true)
                }}
                onValueCommit={() => updateSettings()}
              />
              <span className="text-xs font-mono w-16 text-right">{sscAngleRange[0]}–{sscAngleRange[1]}°</span>
            </div>
            <p className="text-[10px] text-muted-foreground">Side scatter (typical: 85-95°)</p>
          </div>
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="analysis" className="border rounded-lg px-3">
        <AccordionTrigger className="text-sm font-medium py-3">
          <span className="flex items-center gap-2">
            <Settings className="h-4 w-4 text-primary" />
            Analysis Options
          </span>
        </AccordionTrigger>
        <AccordionContent className="space-y-4 pb-4">
          <div className="flex items-center justify-between">
            <Label className="text-xs text-muted-foreground">Enable Anomaly Detection</Label>
            <Switch 
              checked={anomalyEnabled}
              onCheckedChange={(checked) => {
                setAnomalyEnabled(checked)
                setHasChanges(true)
                updateSettings()
              }}
            />
          </div>

          {anomalyEnabled && (
            <>
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Anomaly Method</Label>
                <Select 
                  value={anomalyMethod.toLowerCase().replace("-", "")} 
                  onValueChange={(v) => {
                    const method = v === "zscore" ? "Z-Score" : v === "iqr" ? "IQR" : "Both"
                    setAnomalyMethod(method)
                    setHasChanges(true)
                    updateSettings()
                  }}
                >
                  <SelectTrigger className="h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="zscore">Z-Score</SelectItem>
                    <SelectItem value="iqr">IQR</SelectItem>
                    <SelectItem value="both">Both</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {(anomalyMethod === "Z-Score" || anomalyMethod === "Both") && (
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">Z-Score Threshold</Label>
                  <div className="flex items-center gap-2">
                    <Slider 
                      value={[zscoreThreshold]} 
                      min={2.0} 
                      max={4.0} 
                      step={0.1} 
                      className="flex-1"
                      onValueChange={(v) => {
                        setZscoreThreshold(v[0])
                        setHasChanges(true)
                      }}
                      onValueCommit={() => updateSettings()}
                    />
                    <span className="text-sm font-mono w-10">{zscoreThreshold.toFixed(1)}</span>
                  </div>
                </div>
              )}

              {(anomalyMethod === "IQR" || anomalyMethod === "Both") && (
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">IQR Factor</Label>
                  <div className="flex items-center gap-2">
                    <Slider 
                      value={[iqrFactor]} 
                      min={1.0} 
                      max={3.0} 
                      step={0.1} 
                      className="flex-1"
                      onValueChange={(v) => {
                        setIqrFactor(v[0])
                        setHasChanges(true)
                      }}
                      onValueCommit={() => updateSettings()}
                    />
                    <span className="text-sm font-mono w-10">{iqrFactor.toFixed(1)}</span>
                  </div>
                </div>
              )}
            </>
          )}
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="categories" className="border rounded-lg px-3">
        <AccordionTrigger className="text-sm font-medium py-3">Size Categories</AccordionTrigger>
        <AccordionContent className="space-y-3 pb-4">
          {/* Preset buttons */}
          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Quick Presets</Label>
            <div className="grid grid-cols-2 gap-1">
              <Button 
                variant={activePreset === "standard" ? "secondary" : "outline"} 
                size="sm" 
                className="text-xs h-8"
                onClick={() => handlePresetChange("standard")}
              >
                Standard EV
              </Button>
              <Button 
                variant={activePreset === "exosome" ? "secondary" : "outline"} 
                size="sm" 
                className="text-xs h-8"
                onClick={() => handlePresetChange("exosome")}
              >
                Exosome Focus
              </Button>
              <Button 
                variant={activePreset === "isev2023" ? "secondary" : "outline"} 
                size="sm" 
                className="text-xs h-8"
                onClick={() => handlePresetChange("isev2023")}
              >
                ISEV 2023
              </Button>
              <Button 
                variant={activePreset === "custom" ? "secondary" : "outline"} 
                size="sm" 
                className="text-xs h-8"
                onClick={() => handlePresetChange("custom")}
              >
                Custom
              </Button>
            </div>
          </div>

          {/* Current ranges display */}
          <div className="space-y-2 text-xs">
            <Label className="text-xs text-muted-foreground">Current Ranges</Label>
            <div className="space-y-1 max-h-[180px] overflow-y-auto">
              {currentSizeRanges.map((range, i) => (
                <div key={i} className="flex items-center gap-2 p-1.5 rounded bg-secondary/30 group">
                  <div 
                    className="w-3 h-3 rounded shrink-0" 
                    style={{ backgroundColor: range.color || ["#22c55e", "#3b82f6", "#f59e0b", "#a855f7"][i % 4] }}
                  />
                  <span className="flex-1 truncate text-xs">{range.name}</span>
                  <span className="font-mono text-muted-foreground text-[10px]">{range.min}-{range.max}nm</span>
                  {(activePreset === "custom" || editingRanges) && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => handleRemoveRange(i)}
                    >
                      <Trash2 className="h-3 w-3 text-destructive" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Add new range (when in custom mode) */}
          {(activePreset === "custom" || editingRanges) && (
            <div className="space-y-2 pt-2 border-t">
              <Label className="text-xs text-muted-foreground">Add New Range</Label>
              <div className="space-y-2">
                <Input
                  placeholder="Range name (e.g., Small EVs)"
                  value={newRangeName}
                  onChange={(e) => setNewRangeName(e.target.value)}
                  className="h-8 text-xs"
                />
                <div className="flex gap-2">
                  <div className="flex-1">
                    <Label className="text-[10px] text-muted-foreground">Min (nm)</Label>
                    <Input
                      type="number"
                      value={newRangeMin}
                      onChange={(e) => setNewRangeMin(parseInt(e.target.value) || 0)}
                      min={0}
                      max={500}
                      className="h-8 text-xs font-mono"
                    />
                  </div>
                  <div className="flex-1">
                    <Label className="text-[10px] text-muted-foreground">Max (nm)</Label>
                    <Input
                      type="number"
                      value={newRangeMax}
                      onChange={(e) => setNewRangeMax(parseInt(e.target.value) || 0)}
                      min={0}
                      max={1000}
                      className="h-8 text-xs font-mono"
                    />
                  </div>
                </div>
                <Button 
                  size="sm" 
                  className="w-full h-8 text-xs gap-1"
                  onClick={handleAddRange}
                  disabled={!newRangeName.trim() || newRangeMin >= newRangeMax}
                >
                  <Plus className="h-3 w-3" />
                  Add Range
                </Button>
              </div>
            </div>
          )}
        </AccordionContent>
      </AccordionItem>

      {/* TASK-019: Visualization Settings with Histogram Bin Configuration */}
      <AccordionItem value="visualization" className="border rounded-lg px-3">
        <AccordionTrigger className="text-sm font-medium py-3">
          <span className="flex items-center gap-2">
            <SlidersHorizontal className="h-4 w-4 text-primary" />
            Visualization
          </span>
        </AccordionTrigger>
        <AccordionContent className="space-y-4 pb-4">
          {/* Histogram Bins Slider - TASK-019 */}
          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Histogram Bins</Label>
            <div className="flex items-center gap-2">
              <Slider 
                value={[fcsAnalysisSettings?.histogramBins || 20]} 
                min={10} 
                max={100} 
                step={5} 
                className="flex-1"
                onValueChange={(v) => {
                  setFcsAnalysisSettings({
                    ...fcsAnalysisSettings!,
                    histogramBins: v[0],
                  })
                }}
              />
              <span className="text-sm font-mono w-10">{fcsAnalysisSettings?.histogramBins || 20}</span>
            </div>
            <p className="text-[10px] text-muted-foreground">
              Number of bins for size distribution histogram (10-100)
            </p>
          </div>
        </AccordionContent>
      </AccordionItem>

      {/* TASK-016: Best Practices Comparison Engine */}
      <AccordionItem value="best-practices" className="border rounded-lg px-3">
        <AccordionTrigger className="text-sm font-medium py-3">
          <span className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-primary" />
            Best Practices
          </span>
        </AccordionTrigger>
        <AccordionContent className="pb-4">
          <BestPracticesPanel 
            data={{
              // Experimental conditions from saved data
              antibody_concentration_ug: fcsAnalysis.experimentalConditions?.antibody_concentration_ug,
              dilution_factor: fcsAnalysis.experimentalConditions?.dilution_factor,
              incubation_time_min: fcsAnalysis.experimentalConditions?.incubation_time_min,
              // Size statistics from analysis results
              median_size_nm: fcsAnalysis.results?.size_statistics?.d50,
              d10_nm: fcsAnalysis.results?.size_statistics?.d10,
              d50_nm: fcsAnalysis.results?.size_statistics?.d50,
              d90_nm: fcsAnalysis.results?.size_statistics?.d90,
              // Quality metrics
              total_events: fcsAnalysis.results?.total_events,
              anomaly_pct: fcsAnalysis.anomalyData?.anomaly_percentage,
              valid_events_pct: fcsAnalysis.results?.size_filtering?.valid_count 
                ? (fcsAnalysis.results.size_filtering.valid_count / (fcsAnalysis.results.total_events || 1)) * 100
                : undefined,
            } as ExperimentData} 
            compact={true}
          />
        </AccordionContent>
      </AccordionItem>

      {/* Re-analyze button */}
      {fcsAnalysis.sampleId && (
        <div className="pt-2 space-y-2">
          {hasChanges && (
            <Badge variant="secondary" className="w-full justify-center text-xs py-1">
              Settings changed - Re-analyze to apply
            </Badge>
          )}
          <Button 
            className="w-full gap-2" 
            size="sm"
            onClick={handleReanalyze}
            disabled={!hasChanges && !fcsAnalysis.results}
          >
            <Play className="h-3.5 w-3.5" />
            Re-analyze with Settings
          </Button>
        </div>
      )}
    </Accordion>

      {/* Experimental Conditions Dialog */}
      <ExperimentalConditionsDialog
        open={showConditionsDialog}
        onOpenChange={setShowConditionsDialog}
        onSave={handleSaveConditions}
        sampleType="FCS"
        sampleId={fcsAnalysis.sampleId || undefined}
      />
    </>
  )
}

function NTASidebar() {
  const { ntaAnalysisSettings, setNtaAnalysisSettings } = useAnalysisStore()

  // Compute viscosity correction factor from temperatures
  // Using Stokes-Einstein: D ∝ T/η, so size correction ≈ (η_ref/η_meas) × (T_meas/T_ref)
  const computeCorrectionFactor = (measTemp: number, refTemp: number, mediaType: string) => {
    // PBS viscosity approximation (mPa·s) using Arrhenius model
    const viscosity = (temp: number) => {
      const base = mediaType === "water" ? 1.002 : mediaType === "culture" ? 1.20 : 1.02 // PBS default
      return base * Math.exp(1800 * (1 / (273.15 + temp) - 1 / 293.15))
    }
    const etaMeas = viscosity(measTemp)
    const etaRef = viscosity(refTemp)
    return Number(((etaRef / etaMeas) * ((273.15 + measTemp) / (273.15 + refTemp))).toFixed(4))
  }

  const handleTempChange = (field: "measurementTemp" | "referenceTemp", value: number) => {
    const newMeas = field === "measurementTemp" ? value : ntaAnalysisSettings.measurementTemp
    const newRef = field === "referenceTemp" ? value : ntaAnalysisSettings.referenceTemp
    const correctionFactor = computeCorrectionFactor(newMeas, newRef, ntaAnalysisSettings.mediaType)
    setNtaAnalysisSettings({ [field]: value, correctionFactor })
  }

  const handleMediaChange = (mediaType: string) => {
    const correctionFactor = computeCorrectionFactor(
      ntaAnalysisSettings.measurementTemp, ntaAnalysisSettings.referenceTemp, mediaType
    )
    setNtaAnalysisSettings({ mediaType, correctionFactor })
  }

  return (
    <Accordion type="multiple" defaultValue={["temp", "viz"]} className="space-y-2">
      <AccordionItem value="temp" className="border rounded-lg px-3">
        <AccordionTrigger className="text-sm font-medium py-3">
          <span className="flex items-center gap-2">
            <Thermometer className="h-4 w-4 text-primary" />
            Temperature Correction
          </span>
        </AccordionTrigger>
        <AccordionContent className="space-y-4 pb-4">
          <div className="flex items-center justify-between">
            <Label className="text-xs text-muted-foreground">Enable Correction</Label>
            <Switch
              checked={ntaAnalysisSettings.applyTemperatureCorrection}
              onCheckedChange={(checked) => setNtaAnalysisSettings({ applyTemperatureCorrection: checked })}
            />
          </div>

          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Measurement Temp (°C)</Label>
            <div className="flex items-center gap-2">
              <Slider
                value={[ntaAnalysisSettings.measurementTemp]}
                onValueChange={([v]) => handleTempChange("measurementTemp", v)}
                min={15} max={40} step={0.5} className="flex-1"
              />
              <span className="text-sm font-mono w-12">{ntaAnalysisSettings.measurementTemp}°C</span>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Reference Temp (°C)</Label>
            <div className="flex items-center gap-2">
              <Slider
                value={[ntaAnalysisSettings.referenceTemp]}
                onValueChange={([v]) => handleTempChange("referenceTemp", v)}
                min={15} max={40} step={0.5} className="flex-1"
              />
              <span className="text-sm font-mono w-12">{ntaAnalysisSettings.referenceTemp}°C</span>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Medium Type</Label>
            <Select value={ntaAnalysisSettings.mediaType} onValueChange={handleMediaChange}>
              <SelectTrigger className="h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="water">Water</SelectItem>
                <SelectItem value="pbs">PBS</SelectItem>
                <SelectItem value="culture">Culture Media</SelectItem>
                <SelectItem value="custom">Custom</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="p-2 rounded bg-secondary/50 text-xs">
            <span className="text-muted-foreground">Correction Factor: </span>
            <span className="font-mono text-primary">{ntaAnalysisSettings.correctionFactor}</span>
          </div>
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="viz" className="border rounded-lg px-3">
        <AccordionTrigger className="text-sm font-medium py-3">Visualization Options</AccordionTrigger>
        <AccordionContent className="space-y-4 pb-4">
          <div className="flex items-center justify-between">
            <Label className="text-xs text-muted-foreground">Show Percentile Lines</Label>
            <Switch
              checked={ntaAnalysisSettings.showPercentileLines}
              onCheckedChange={(checked) => setNtaAnalysisSettings({ showPercentileLines: checked })}
            />
          </div>

          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Bin Size</Label>
            <div className="flex items-center gap-2">
              <Slider
                value={[ntaAnalysisSettings.binSize]}
                onValueChange={([v]) => setNtaAnalysisSettings({ binSize: v })}
                min={5} max={50} step={5} className="flex-1"
              />
              <span className="text-sm font-mono w-12">{ntaAnalysisSettings.binSize}nm</span>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Y-Axis</Label>
            <Select
              value={ntaAnalysisSettings.yAxisMode}
              onValueChange={(v) => setNtaAnalysisSettings({ yAxisMode: v as "count" | "normalized" })}
            >
              <SelectTrigger className="h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="count">Count</SelectItem>
                <SelectItem value="normalized">Normalized</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
}

function CrossCompareSidebar() {
  const { crossComparisonSettings, setCrossComparisonSettings, apiSamples } = useAnalysisStore()
  
  // Get available samples for selection
  const fcsSamples = apiSamples.filter(s => s.files?.fcs)
  const ntaSamples = apiSamples.filter(s => s.files?.nta)
  
  const handleSettingChange = <K extends keyof typeof crossComparisonSettings>(
    key: K,
    value: typeof crossComparisonSettings[K]
  ) => {
    setCrossComparisonSettings({
      ...crossComparisonSettings,
      [key]: value,
    })
  }
  
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
          <FileText className="h-4 w-4 text-primary" />
          Data Source Selection
        </h3>
        <div className="space-y-3">
          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">FCS File</Label>
            <Select>
              <SelectTrigger className="h-9">
                <SelectValue placeholder="Select FCS file..." />
              </SelectTrigger>
              <SelectContent>
                {fcsSamples.length > 0 ? (
                  fcsSamples.map((sample) => (
                    <SelectItem key={sample.id} value={String(sample.id)}>
                      {sample.sample_id}
                    </SelectItem>
                  ))
                ) : (
                  <>
                    <SelectItem value="l5_f10_cd81">L5_F10_CD81.fcs</SelectItem>
                    <SelectItem value="sample_cd9">Sample_CD9.fcs</SelectItem>
                  </>
                )}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">NTA File</Label>
            <Select>
              <SelectTrigger className="h-9">
                <SelectValue placeholder="Select NTA file..." />
              </SelectTrigger>
              <SelectContent>
                {ntaSamples.length > 0 ? (
                  ntaSamples.map((sample) => (
                    <SelectItem key={sample.id} value={String(sample.id)}>
                      {sample.sample_id}
                    </SelectItem>
                  ))
                ) : (
                  <>
                    <SelectItem value="ev_ipsc_p1">EV_IPSC_P1_NTA.txt</SelectItem>
                    <SelectItem value="ev_sample2">EV_Sample2.csv</SelectItem>
                  </>
                )}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <div className="border-t border-border pt-4">
        <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
          <Settings className="h-4 w-4 text-primary" />
          Comparison Settings
        </h3>
        <div className="space-y-4">
          {/* Size Range Filter */}
          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Size Range (nm)</Label>
            <div className="flex items-center gap-2">
              <Slider 
                value={[crossComparisonSettings.minSizeFilter, crossComparisonSettings.maxSizeFilter]} 
                min={0} 
                max={1000} 
                step={10}
                onValueChange={([min, max]) => {
                  handleSettingChange("minSizeFilter", min)
                  handleSettingChange("maxSizeFilter", max)
                }}
                className="flex-1" 
              />
            </div>
            <div className="flex justify-between text-xs font-mono text-muted-foreground">
              <span>{crossComparisonSettings.minSizeFilter} nm</span>
              <span>{crossComparisonSettings.maxSizeFilter} nm</span>
            </div>
          </div>

          {/* Bin Size */}
          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Histogram Bin Size (nm)</Label>
            <div className="flex items-center gap-2">
              <Slider 
                value={[crossComparisonSettings.binSize]} 
                min={1} 
                max={20} 
                step={1}
                onValueChange={([value]) => handleSettingChange("binSize", value)}
                className="flex-1" 
              />
              <span className="text-sm font-mono w-12">{crossComparisonSettings.binSize} nm</span>
            </div>
          </div>

          {/* Normalize Distributions */}
          <div className="flex items-center justify-between">
            <div>
              <Label className="text-xs text-muted-foreground">Normalize Distributions</Label>
              <p className="text-[10px] text-muted-foreground/70">Scale to 0-1 for comparison</p>
            </div>
            <Switch 
              checked={crossComparisonSettings.normalizeHistograms}
              onCheckedChange={(checked) => handleSettingChange("normalizeHistograms", checked)}
            />
          </div>

          {/* Show KDE Curves */}
          <div className="flex items-center justify-between">
            <div>
              <Label className="text-xs text-muted-foreground">Show KDE Curves</Label>
              <p className="text-[10px] text-muted-foreground/70">Kernel density estimation</p>
            </div>
            <Switch 
              checked={crossComparisonSettings.showKde}
              onCheckedChange={(checked) => handleSettingChange("showKde", checked)}
            />
          </div>

          {/* Show Statistics */}
          <div className="flex items-center justify-between">
            <div>
              <Label className="text-xs text-muted-foreground">Show Statistics</Label>
              <p className="text-[10px] text-muted-foreground/70">Mann-Whitney, K-S tests</p>
            </div>
            <Switch 
              checked={crossComparisonSettings.showStatistics}
              onCheckedChange={(checked) => handleSettingChange("showStatistics", checked)}
            />
          </div>

          {/* Discrepancy Threshold */}
          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Discrepancy Threshold</Label>
            <p className="text-[10px] text-muted-foreground/70">Highlight bins with difference above threshold</p>
            <div className="flex items-center gap-2">
              <Slider 
                value={[crossComparisonSettings.discrepancyThreshold]} 
                min={5} 
                max={50} 
                step={1}
                onValueChange={([value]) => handleSettingChange("discrepancyThreshold", value)}
                className="flex-1" 
              />
              <span className="text-sm font-mono w-10">{crossComparisonSettings.discrepancyThreshold}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
