"use client"

import { useState, useEffect, useMemo } from "react"
import { useAnalysisStore } from "@/lib/store"
import { useApi } from "@/hooks/use-api"
import { cn } from "@/lib/utils"
import { ChevronLeft, ChevronRight, Filter, Settings, FileText, Beaker, Thermometer, Loader2, RefreshCw, Database, SlidersHorizontal } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Slider } from "@/components/ui/slider"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Badge } from "@/components/ui/badge"

interface SidebarProps {
  isMobile?: boolean
}

export function Sidebar({ isMobile = false }: SidebarProps) {
  const { sidebarCollapsed, toggleSidebar, activeTab, samples, apiSamples, samplesLoading, apiConnected } = useAnalysisStore()
  const { fetchSamples } = useApi()

  // Fetch samples on mount only if API is connected
  useEffect(() => {
    if (apiConnected) {
      fetchSamples()
    }
  }, [fetchSamples, apiConnected])

  const isCollapsed = isMobile ? false : sidebarCollapsed

  return (
    <aside
      className={cn(
        "border-r border-border bg-sidebar transition-all duration-300 flex flex-col h-full",
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
        <ScrollArea className="flex-1 overflow-y-auto custom-scrollbar">
          <div className="p-4 space-y-4">
            {activeTab === "flow-cytometry" && <FlowCytometrySidebar />}
            {activeTab === "nta" && <NTASidebar />}
            {activeTab === "cross-compare" && <CrossCompareSidebar />}
            {activeTab === "dashboard" && <DashboardSidebar samples={samples} apiSamples={apiSamples} samplesLoading={samplesLoading} fetchSamples={fetchSamples} />}
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
  fetchSamples 
}: { 
  samples: { id: string; name: string; type: string }[]
  apiSamples: { id: number; sample_id: string; treatment?: string; files?: { fcs?: string; nta?: string } }[]
  samplesLoading: boolean
  fetchSamples: () => void
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
          <div className="space-y-1">
            {/* API Samples */}
            {filteredApiSamples.slice(0, 5).map((sample) => (
              <div 
                key={sample.id} 
                className="text-sm p-2 rounded-md hover:bg-secondary/50 cursor-pointer flex items-center justify-between"
              >
                <div className="flex-1 min-w-0">
                  <span className="truncate block">{sample.sample_id}</span>
                  {sample.treatment && (
                    <span className="text-[10px] text-muted-foreground">{sample.treatment}</span>
                  )}
                </div>
                <div className="flex gap-1">
                  {sample.files?.fcs && (
                    <Badge variant="outline" className="text-[10px] px-1">FCS</Badge>
                  )}
                  {sample.files?.nta && (
                    <Badge variant="outline" className="text-[10px] px-1">NTA</Badge>
                  )}
                </div>
              </div>
            ))}
            
            {/* Local Samples (fallback) */}
            {samples.slice(0, Math.max(0, 5 - filteredApiSamples.length)).map((sample) => (
              <div 
                key={sample.id} 
                className="text-sm p-2 rounded-md hover:bg-secondary/50 cursor-pointer flex items-center justify-between"
              >
                <span className="truncate flex-1">{sample.name}</span>
                <Badge variant="secondary" className="text-[10px] px-1">
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
  return (
    <Accordion type="multiple" defaultValue={["params", "analysis", "categories"]} className="space-y-2">
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
              <Slider defaultValue={[1.4]} min={1.35} max={1.6} step={0.01} className="flex-1" />
              <span className="text-sm font-mono w-12">1.40</span>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Laser Wavelength</Label>
            <Select defaultValue="488">
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
            <Select defaultValue="pbs">
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
            <Switch defaultChecked />
          </div>

          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Anomaly Method</Label>
            <Select defaultValue="both">
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

          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Z-Score Threshold</Label>
            <div className="flex items-center gap-2">
              <Slider defaultValue={[3.0]} min={2.0} max={4.0} step={0.1} className="flex-1" />
              <span className="text-sm font-mono w-10">3.0</span>
            </div>
          </div>
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="categories" className="border rounded-lg px-3">
        <AccordionTrigger className="text-sm font-medium py-3">Size Categories</AccordionTrigger>
        <AccordionContent className="space-y-3 pb-4">
          <div className="flex flex-wrap gap-1">
            <Button variant="outline" size="sm" className="flex-1 text-xs h-8 bg-transparent min-w-[70px]">
              Standard EV
            </Button>
            <Button variant="outline" size="sm" className="flex-1 text-xs h-8 bg-transparent min-w-[70px]">
              Exosome
            </Button>
            <Button variant="secondary" size="sm" className="flex-1 text-xs h-8 min-w-[70px]">
              Custom
            </Button>
          </div>

          <div className="space-y-2 text-xs overflow-x-auto">
            <div className="grid grid-cols-4 gap-2 text-muted-foreground font-medium min-w-[200px]">
              <span>Category</span>
              <span>Min</span>
              <span>Max</span>
              <span>Color</span>
            </div>
            <div className="grid grid-cols-4 gap-2 items-center min-w-[200px]">
              <span className="truncate">Small EVs</span>
              <span className="font-mono">0</span>
              <span className="font-mono">50</span>
              <div className="w-4 h-4 rounded bg-cyan" />
            </div>
            <div className="grid grid-cols-4 gap-2 items-center min-w-[200px]">
              <span className="truncate">Exosomes</span>
              <span className="font-mono">50</span>
              <span className="font-mono">200</span>
              <div className="w-4 h-4 rounded bg-purple" />
            </div>
            <div className="grid grid-cols-4 gap-2 items-center min-w-[200px]">
              <span className="truncate">Large EVs</span>
              <span className="font-mono">200</span>
              <span className="font-mono">1000</span>
              <div className="w-4 h-4 rounded bg-amber" />
            </div>
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
}

function NTASidebar() {
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
            <Switch defaultChecked />
          </div>

          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Measurement Temp (°C)</Label>
            <div className="flex items-center gap-2">
              <Slider defaultValue={[22]} min={15} max={40} step={0.5} className="flex-1" />
              <span className="text-sm font-mono w-12">22°C</span>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Reference Temp (°C)</Label>
            <div className="flex items-center gap-2">
              <Slider defaultValue={[25]} min={15} max={40} step={0.5} className="flex-1" />
              <span className="text-sm font-mono w-12">25°C</span>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Medium Type</Label>
            <Select defaultValue="pbs">
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
            <span className="font-mono text-primary">0.9876</span>
          </div>
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="viz" className="border rounded-lg px-3">
        <AccordionTrigger className="text-sm font-medium py-3">Visualization Options</AccordionTrigger>
        <AccordionContent className="space-y-4 pb-4">
          <div className="flex items-center justify-between">
            <Label className="text-xs text-muted-foreground">Show Percentile Lines</Label>
            <Switch defaultChecked />
          </div>

          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Bin Size</Label>
            <div className="flex items-center gap-2">
              <Slider defaultValue={[10]} min={5} max={50} step={5} className="flex-1" />
              <span className="text-sm font-mono w-12">10nm</span>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Y-Axis</Label>
            <Select defaultValue="count">
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
                <SelectItem value="l5_f10_cd81">L5_F10_CD81.fcs</SelectItem>
                <SelectItem value="sample_cd9">Sample_CD9.fcs</SelectItem>
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
                <SelectItem value="ev_ipsc_p1">EV_IPSC_P1_NTA.txt</SelectItem>
                <SelectItem value="ev_sample2">EV_Sample2.csv</SelectItem>
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
          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Size Range (nm)</Label>
            <div className="flex items-center gap-2">
              <Slider defaultValue={[0, 500]} min={0} max={1000} step={10} className="flex-1" />
            </div>
            <div className="flex justify-between text-xs font-mono text-muted-foreground">
              <span>0</span>
              <span>500</span>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <Label className="text-xs text-muted-foreground">Normalize Distributions</Label>
            <Switch defaultChecked />
          </div>

          <div className="flex items-center justify-between">
            <Label className="text-xs text-muted-foreground">Show KDE Curves</Label>
            <Switch defaultChecked />
          </div>

          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Discrepancy Threshold</Label>
            <div className="flex items-center gap-2">
              <Slider defaultValue={[15]} min={5} max={30} step={1} className="flex-1" />
              <span className="text-sm font-mono w-10">15%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
