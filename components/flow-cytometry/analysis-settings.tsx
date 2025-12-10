"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Settings2, Plus, Trash2, ChevronDown, ChevronUp, Beaker, AlertTriangle, BarChart3, Eye, Sparkles } from "lucide-react"
import { useAnalysisStore } from "@/lib/store"

interface SizeRange {
  name: string
  min: number
  max: number
}

const DEFAULT_SIZE_RANGES: SizeRange[] = [
  { name: "Small EVs", min: 30, max: 100 },
  { name: "Medium EVs", min: 100, max: 150 },
  { name: "Large EVs", min: 150, max: 200 },
]

const EV_STANDARD_PRESET: SizeRange[] = [
  { name: "Small EVs (<50nm)", min: 0, max: 50 },
  { name: "Exosomes (50-200nm)", min: 50, max: 200 },
  { name: "Microvesicles (>200nm)", min: 200, max: 500 },
]

const ISEV_2023_PRESET: SizeRange[] = [
  { name: "Exomeres", min: 0, max: 50 },
  { name: "Small EVs", min: 50, max: 100 },
  { name: "Medium EVs", min: 100, max: 200 },
  { name: "Large EVs", min: 200, max: 500 },
]

export function AnalysisSettings() {
  const { fcsAnalysisSettings, setFcsAnalysisSettings } = useAnalysisStore()
  
  // Initialize with defaults or stored values
  const [laserWavelength, setLaserWavelength] = useState(fcsAnalysisSettings?.laserWavelength ?? 488.0)
  const [particleRI, setParticleRI] = useState(fcsAnalysisSettings?.particleRI ?? 1.38)
  const [mediumRI, setMediumRI] = useState(fcsAnalysisSettings?.mediumRI ?? 1.33)
  const [fscRange, setFscRange] = useState<[number, number]>(fcsAnalysisSettings?.fscRange ?? [1, 15])
  const [sscRange, setSscRange] = useState<[number, number]>(fcsAnalysisSettings?.sscRange ?? [85, 95])
  const [diameterRange, setDiameterRange] = useState<[number, number]>(fcsAnalysisSettings?.diameterRange ?? [40, 180])
  const [diameterPoints, setDiameterPoints] = useState(fcsAnalysisSettings?.diameterPoints ?? 200)
  const [sizeRanges, setSizeRanges] = useState<SizeRange[]>(fcsAnalysisSettings?.sizeRanges ?? DEFAULT_SIZE_RANGES)
  
  // Data Cleaning Options
  const [ignoreNegativeH, setIgnoreNegativeH] = useState(fcsAnalysisSettings?.ignoreNegativeH ?? true)
  const [dropNaRows, setDropNaRows] = useState(fcsAnalysisSettings?.dropNaRows ?? true)
  
  // Anomaly Detection Settings
  const [anomalyDetectionEnabled, setAnomalyDetectionEnabled] = useState(fcsAnalysisSettings?.anomalyDetectionEnabled ?? false)
  const [anomalyMethod, setAnomalyMethod] = useState<"Z-Score" | "IQR" | "Both">(fcsAnalysisSettings?.anomalyMethod ?? "Z-Score")
  const [zscoreThreshold, setZscoreThreshold] = useState(fcsAnalysisSettings?.zscoreThreshold ?? 3.0)
  const [iqrFactor, setIqrFactor] = useState(fcsAnalysisSettings?.iqrFactor ?? 1.5)
  const [highlightAnomalies, setHighlightAnomalies] = useState(fcsAnalysisSettings?.highlightAnomalies ?? true)
  
  // Visualization Settings
  const [useInteractivePlots, setUseInteractivePlots] = useState(fcsAnalysisSettings?.useInteractivePlots ?? true)
  
  const [isOpen, setIsOpen] = useState(false)
  const [newRangeName, setNewRangeName] = useState("")
  const [newRangeMin, setNewRangeMin] = useState(30)
  const [newRangeMax, setNewRangeMax] = useState(100)

  // Update store when settings change
  const updateSettings = () => {
    setFcsAnalysisSettings({
      laserWavelength,
      particleRI,
      mediumRI,
      fscRange,
      sscRange,
      diameterRange,
      diameterPoints,
      sizeRanges,
      ignoreNegativeH,
      dropNaRows,
      anomalyDetectionEnabled,
      anomalyMethod,
      zscoreThreshold,
      iqrFactor,
      highlightAnomalies,
      useInteractivePlots,
    })
  }

  const addSizeRange = () => {
    if (newRangeName.trim() && newRangeMin < newRangeMax) {
      setSizeRanges([...sizeRanges, { name: newRangeName.trim(), min: newRangeMin, max: newRangeMax }])
      setNewRangeName("")
      setNewRangeMin(30)
      setNewRangeMax(100)
    }
  }

  const removeSizeRange = (index: number) => {
    setSizeRanges(sizeRanges.filter((_, i) => i !== index))
  }

  const applyPreset = (preset: SizeRange[]) => {
    setSizeRanges(preset)
  }

  return (
    <Card className="card-3d">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-secondary/30 transition-colors pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-primary/10">
                  <Settings2 className="h-4 w-4 text-primary" />
                </div>
                <CardTitle className="text-base">Analysis Settings</CardTitle>
              </div>
              {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </div>
          </CardHeader>
        </CollapsibleTrigger>
        
        <CollapsibleContent>
          <CardContent className="space-y-6 pt-0">
            <Accordion type="multiple" defaultValue={["optical"]} className="w-full">
              {/* Optical Parameters */}
              <AccordionItem value="optical">
                <AccordionTrigger className="text-sm font-medium">
                  <div className="flex items-center gap-2">
                    <Beaker className="h-4 w-4 text-primary" />
                    Optical Parameters
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                    <div className="space-y-2">
                      <Label htmlFor="wavelength">Laser Wavelength (nm)</Label>
                      <Input
                        id="wavelength"
                        type="number"
                        step="1"
                        value={laserWavelength}
                        onChange={(e) => setLaserWavelength(parseFloat(e.target.value))}
                        onBlur={updateSettings}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="particleRI">Particle Refractive Index</Label>
                      <Input
                        id="particleRI"
                        type="number"
                        step="0.01"
                        value={particleRI}
                        onChange={(e) => setParticleRI(parseFloat(e.target.value))}
                        onBlur={updateSettings}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="mediumRI">Medium Refractive Index</Label>
                      <Input
                        id="mediumRI"
                        type="number"
                        step="0.01"
                        value={mediumRI}
                        onChange={(e) => setMediumRI(parseFloat(e.target.value))}
                        onBlur={updateSettings}
                      />
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Scatter Angle Ranges */}
              <AccordionItem value="scatter">
                <AccordionTrigger className="text-sm font-medium">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-orange-500" />
                    Scatter Angle Ranges
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                    <div className="space-y-3">
                      <div className="flex justify-between text-sm">
                        <Label>FSC Angle Range (deg)</Label>
                        <span className="text-muted-foreground">{fscRange[0]}° - {fscRange[1]}°</span>
                      </div>
                      <Slider
                        value={fscRange}
                        onValueChange={(value) => setFscRange(value as [number, number])}
                        onValueCommit={updateSettings}
                        min={0}
                        max={30}
                        step={1}
                        className="py-2"
                      />
                    </div>
                    
                    <div className="space-y-3">
                      <div className="flex justify-between text-sm">
                        <Label>SSC Angle Range (deg)</Label>
                        <span className="text-muted-foreground">{sscRange[0]}° - {sscRange[1]}°</span>
                      </div>
                      <Slider
                        value={sscRange}
                        onValueChange={(value) => setSscRange(value as [number, number])}
                        onValueCommit={updateSettings}
                        min={30}
                        max={180}
                        step={1}
                        className="py-2"
                      />
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Size Analysis */}
              <AccordionItem value="size">
                <AccordionTrigger className="text-sm font-medium">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-blue-500" />
                    Size Analysis & Ranges
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-4 pt-2">
                    {/* Diameter Search Range */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-3">
                        <div className="flex justify-between text-sm">
                          <Label>Diameter Search Range (nm)</Label>
                          <span className="text-muted-foreground">{diameterRange[0]} - {diameterRange[1]} nm</span>
                        </div>
                        <Slider
                          value={diameterRange}
                          onValueChange={(value) => setDiameterRange(value as [number, number])}
                          onValueCommit={updateSettings}
                          min={10}
                          max={500}
                          step={5}
                          className="py-2"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label htmlFor="diameterPoints">Diameter Points (resolution)</Label>
                        <Input
                          id="diameterPoints"
                          type="number"
                          min={20}
                          max={2000}
                          step={10}
                          value={diameterPoints}
                          onChange={(e) => setDiameterPoints(parseInt(e.target.value))}
                          onBlur={updateSettings}
                        />
                      </div>
                    </div>

                    {/* Custom Size Ranges */}
                    <div className="space-y-3 pt-2">
                      <h5 className="text-sm font-medium">Custom Size Ranges</h5>
                      <p className="text-xs text-muted-foreground">
                        Define custom size categories for particle counting
                      </p>
                      
                      {/* Current ranges */}
                      <div className="space-y-2">
                        {sizeRanges.map((range, i) => (
                          <div key={i} className="flex items-center justify-between p-2 bg-secondary/30 rounded-lg">
                            <div className="flex items-center gap-3">
                              <Badge variant="outline">{range.name}</Badge>
                              <span className="text-sm text-muted-foreground">
                                {range.min} - {range.max} nm
                              </span>
                            </div>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() => removeSizeRange(i)}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        ))}
                      </div>

                      {/* Add new range */}
                      <div className="flex flex-wrap gap-2 items-end p-3 border rounded-lg border-dashed">
                        <div className="flex-1 min-w-[120px]">
                          <Label className="text-xs">Range Name</Label>
                          <Input
                            value={newRangeName}
                            onChange={(e) => setNewRangeName(e.target.value)}
                            placeholder="e.g., Exosomes"
                            className="h-8 text-sm"
                          />
                        </div>
                        <div className="w-20">
                          <Label className="text-xs">Min (nm)</Label>
                          <Input
                            type="number"
                            value={newRangeMin}
                            onChange={(e) => setNewRangeMin(parseInt(e.target.value))}
                            className="h-8 text-sm"
                          />
                        </div>
                        <div className="w-20">
                          <Label className="text-xs">Max (nm)</Label>
                          <Input
                            type="number"
                            value={newRangeMax}
                            onChange={(e) => setNewRangeMax(parseInt(e.target.value))}
                            className="h-8 text-sm"
                          />
                        </div>
                        <Button size="sm" variant="outline" onClick={addSizeRange}>
                          <Plus className="h-3.5 w-3.5 mr-1" />
                          Add
                        </Button>
                      </div>

                      {/* Preset buttons */}
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => applyPreset(EV_STANDARD_PRESET)}
                        >
                          📊 EV Standard
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => applyPreset(ISEV_2023_PRESET)}
                        >
                          🔬 ISEV 2023
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => applyPreset(DEFAULT_SIZE_RANGES)}
                        >
                          ↺ Reset
                        </Button>
                      </div>
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Data Cleaning */}
              <AccordionItem value="cleaning">
                <AccordionTrigger className="text-sm font-medium">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-green-500" />
                    Channels & Cleaning
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-4 pt-2">
                    <p className="text-xs text-muted-foreground">
                      Data cleaning options applied during processing
                    </p>
                    
                    <div className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <Label>Ignore Negative -H Values</Label>
                        <p className="text-xs text-muted-foreground">
                          Replace negative height values with NaN
                        </p>
                      </div>
                      <Switch
                        checked={ignoreNegativeH}
                        onCheckedChange={(checked) => {
                          setIgnoreNegativeH(checked)
                          updateSettings()
                        }}
                      />
                    </div>
                    
                    <div className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <Label>Drop NA Rows</Label>
                        <p className="text-xs text-muted-foreground">
                          Drop rows missing FSC/SSC after cleaning
                        </p>
                      </div>
                      <Switch
                        checked={dropNaRows}
                        onCheckedChange={(checked) => {
                          setDropNaRows(checked)
                          updateSettings()
                        }}
                      />
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Anomaly Detection */}
              <AccordionItem value="anomaly">
                <AccordionTrigger className="text-sm font-medium">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-yellow-500" />
                    Anomaly Detection
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-4 pt-2">
                    <div className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <Label>Enable Anomaly Detection</Label>
                        <p className="text-xs text-muted-foreground">
                          Detect outliers using statistical methods
                        </p>
                      </div>
                      <Switch
                        checked={anomalyDetectionEnabled}
                        onCheckedChange={(checked) => {
                          setAnomalyDetectionEnabled(checked)
                          updateSettings()
                        }}
                      />
                    </div>
                    
                    {anomalyDetectionEnabled && (
                      <>
                        <div className="space-y-2">
                          <Label>Detection Method</Label>
                          <Select
                            value={anomalyMethod}
                            onValueChange={(value: "Z-Score" | "IQR" | "Both") => {
                              setAnomalyMethod(value)
                              updateSettings()
                            }}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="Z-Score">Z-Score (3σ outliers)</SelectItem>
                              <SelectItem value="IQR">IQR (Interquartile range)</SelectItem>
                              <SelectItem value="Both">Both Methods</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        
                        {(anomalyMethod === "Z-Score" || anomalyMethod === "Both") && (
                          <div className="space-y-3">
                            <div className="flex justify-between text-sm">
                              <Label>Z-Score Threshold (σ)</Label>
                              <span className="text-muted-foreground">{zscoreThreshold}</span>
                            </div>
                            <Slider
                              value={[zscoreThreshold]}
                              onValueChange={(value) => setZscoreThreshold(value[0])}
                              onValueCommit={updateSettings}
                              min={2.0}
                              max={5.0}
                              step={0.5}
                              className="py-2"
                            />
                            <p className="text-xs text-muted-foreground">
                              Events beyond this many standard deviations are flagged
                            </p>
                          </div>
                        )}
                        
                        {(anomalyMethod === "IQR" || anomalyMethod === "Both") && (
                          <div className="space-y-3">
                            <div className="flex justify-between text-sm">
                              <Label>IQR Factor</Label>
                              <span className="text-muted-foreground">{iqrFactor}</span>
                            </div>
                            <Slider
                              value={[iqrFactor]}
                              onValueChange={(value) => setIqrFactor(value[0])}
                              onValueCommit={updateSettings}
                              min={1.0}
                              max={3.0}
                              step={0.25}
                              className="py-2"
                            />
                            <p className="text-xs text-muted-foreground">
                              Multiplier for IQR-based outlier detection
                            </p>
                          </div>
                        )}
                        
                        <div className="flex items-center justify-between p-3 border rounded-lg">
                          <div>
                            <Label>Highlight Anomalies</Label>
                            <p className="text-xs text-muted-foreground">
                              Show anomalies as red markers on plots
                            </p>
                          </div>
                          <Switch
                            checked={highlightAnomalies}
                            onCheckedChange={(checked) => {
                              setHighlightAnomalies(checked)
                              updateSettings()
                            }}
                          />
                        </div>
                      </>
                    )}
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Visualization Settings */}
              <AccordionItem value="visualization">
                <AccordionTrigger className="text-sm font-medium">
                  <div className="flex items-center gap-2">
                    <Eye className="h-4 w-4 text-purple-500" />
                    Visualization Settings
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-4 pt-2">
                    <div className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <Label>Use Interactive Plots</Label>
                        <p className="text-xs text-muted-foreground">
                          Enable hover, zoom, and pan on graphs
                        </p>
                      </div>
                      <Switch
                        checked={useInteractivePlots}
                        onCheckedChange={(checked) => {
                          setUseInteractivePlots(checked)
                          updateSettings()
                        }}
                      />
                    </div>
                    {useInteractivePlots && (
                      <p className="text-xs text-muted-foreground px-3">
                        ✨ Hover over points for details, zoom with scroll, pan by dragging
                      </p>
                    )}
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
