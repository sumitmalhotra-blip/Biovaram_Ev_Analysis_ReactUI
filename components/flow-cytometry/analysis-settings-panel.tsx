"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"
import {
  Settings2,
  Lightbulb,
  Beaker,
  FlaskConical,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Save,
  Info
} from "lucide-react"
import { useAnalysisStore, type FCSAnalysisSettings } from "@/lib/store"
import { cn } from "@/lib/utils"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface AnalysisSettingsPanelProps {
  className?: string
  onSettingsChange?: (settings: FCSAnalysisSettings) => void
}

// Default settings matching Streamlit app.py
const DEFAULT_SETTINGS: FCSAnalysisSettings = {
  laserWavelength: 405,
  particleRI: 1.40,
  mediumRI: 1.33,
  fscRange: [1, 65535],
  sscRange: [1, 65535],
  diameterRange: [30, 200],
  diameterPoints: 180,
  sizeRanges: [
    { name: "Small EVs", min: 30, max: 100 },
    { name: "Medium EVs", min: 100, max: 200 },
    { name: "Large EVs", min: 200, max: 500 },
  ],
  ignoreNegativeH: true,
  dropNaRows: true,
  anomalyDetectionEnabled: true,
  anomalyMethod: "Both",
  zscoreThreshold: 3.0,
  iqrFactor: 1.5,
  highlightAnomalies: true,
  useInteractivePlots: true,
}

// Common laser wavelengths
const LASER_PRESETS = [
  { value: 405, label: "405 nm (Violet)" },
  { value: 488, label: "488 nm (Blue)" },
  { value: 561, label: "561 nm (Yellow-Green)" },
  { value: 640, label: "640 nm (Red)" },
]

// Refractive index presets
const RI_PRESETS = {
  particles: [
    { value: 1.40, label: "EVs/Exosomes (1.40)" },
    { value: 1.45, label: "Lipid droplets (1.45)" },
    { value: 1.50, label: "Silica beads (1.50)" },
    { value: 1.59, label: "Polystyrene beads (1.59)" },
  ],
  medium: [
    { value: 1.33, label: "Water (1.33)" },
    { value: 1.34, label: "PBS (1.34)" },
    { value: 1.35, label: "DMEM (1.35)" },
  ],
}

export function AnalysisSettingsPanel({ className, onSettingsChange }: AnalysisSettingsPanelProps) {
  const { fcsAnalysisSettings, setFcsAnalysisSettings } = useAnalysisStore()
  const [isOpen, setIsOpen] = useState(false)
  const [localSettings, setLocalSettings] = useState<FCSAnalysisSettings>(
    fcsAnalysisSettings || DEFAULT_SETTINGS
  )
  const [hasChanges, setHasChanges] = useState(false)

  // Sync with store
  useEffect(() => {
    if (fcsAnalysisSettings) {
      setLocalSettings(fcsAnalysisSettings)
    }
  }, [fcsAnalysisSettings])

  const handleSettingChange = <K extends keyof FCSAnalysisSettings>(
    key: K,
    value: FCSAnalysisSettings[K]
  ) => {
    setLocalSettings((prev) => ({ ...prev, [key]: value }))
    setHasChanges(true)
  }

  const handleSaveSettings = () => {
    setFcsAnalysisSettings(localSettings)
    onSettingsChange?.(localSettings)
    setHasChanges(false)
  }

  const handleResetSettings = () => {
    setLocalSettings(DEFAULT_SETTINGS)
    setHasChanges(true)
  }

  return (
    <Card className={cn("card-3d", className)}>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CardHeader className="pb-2">
          <CollapsibleTrigger asChild>
            <div className="flex items-center justify-between cursor-pointer group">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-primary/10">
                  <Settings2 className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-base md:text-lg">Analysis Settings</CardTitle>
                  <CardDescription className="text-xs">
                    Mie scattering parameters & data processing options
                  </CardDescription>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {hasChanges && (
                  <Badge variant="secondary" className="text-xs">
                    Unsaved changes
                  </Badge>
                )}
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  {isOpen ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
          </CollapsibleTrigger>
        </CardHeader>

        <CollapsibleContent>
          <CardContent className="pt-4 space-y-6">
            {/* Mie Scattering Parameters */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Lightbulb className="h-4 w-4 text-amber-500" />
                <h4 className="font-medium text-sm">Mie Scattering Parameters</h4>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Laser Wavelength */}
                <div className="space-y-2">
                  <div className="flex items-center gap-1">
                    <Label className="text-sm">Laser Wavelength (nm)</Label>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-3 w-3 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="max-w-xs text-xs">
                          The wavelength of the excitation laser. Common values: 405nm (violet), 488nm (blue).
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <Select
                    value={String(localSettings.laserWavelength)}
                    onValueChange={(v) => handleSettingChange("laserWavelength", Number(v))}
                  >
                    <SelectTrigger className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {LASER_PRESETS.map((preset) => (
                        <SelectItem key={preset.value} value={String(preset.value)}>
                          {preset.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Particle Refractive Index */}
                <div className="space-y-2">
                  <div className="flex items-center gap-1">
                    <Label className="text-sm">Particle RI</Label>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-3 w-3 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="max-w-xs text-xs">
                          Refractive index of the particles. EVs typically have RI ~1.40.
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <Select
                    value={String(localSettings.particleRI)}
                    onValueChange={(v) => handleSettingChange("particleRI", Number(v))}
                  >
                    <SelectTrigger className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {RI_PRESETS.particles.map((preset) => (
                        <SelectItem key={preset.value} value={String(preset.value)}>
                          {preset.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Medium Refractive Index */}
                <div className="space-y-2">
                  <div className="flex items-center gap-1">
                    <Label className="text-sm">Medium RI</Label>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-3 w-3 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="max-w-xs text-xs">
                          Refractive index of the surrounding medium. Water is ~1.33.
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <Select
                    value={String(localSettings.mediumRI)}
                    onValueChange={(v) => handleSettingChange("mediumRI", Number(v))}
                  >
                    <SelectTrigger className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {RI_PRESETS.medium.map((preset) => (
                        <SelectItem key={preset.value} value={String(preset.value)}>
                          {preset.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {/* Size Analysis Parameters */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Beaker className="h-4 w-4 text-blue-500" />
                <h4 className="font-medium text-sm">Size Analysis Parameters</h4>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Diameter Range */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label className="text-sm">Diameter Range (nm)</Label>
                    <span className="text-xs text-muted-foreground">
                      {localSettings.diameterRange[0]} - {localSettings.diameterRange[1]} nm
                    </span>
                  </div>
                  <div className="pt-2">
                    <Slider
                      value={localSettings.diameterRange}
                      min={10}
                      max={1000}
                      step={10}
                      onValueChange={(v) => handleSettingChange("diameterRange", v as [number, number])}
                      className="w-full"
                    />
                  </div>
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>10 nm</span>
                    <span>1000 nm</span>
                  </div>
                </div>

                {/* Diameter Points */}
                <div className="space-y-2">
                  <div className="flex items-center gap-1">
                    <Label className="text-sm">Resolution Points</Label>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-3 w-3 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="max-w-xs text-xs">
                          Number of diameter points for Mie theory curve calculation. Higher = more precise.
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <Input
                    type="number"
                    value={localSettings.diameterPoints}
                    onChange={(e) => handleSettingChange("diameterPoints", Number(e.target.value))}
                    min={50}
                    max={500}
                    step={10}
                    className="h-9"
                  />
                </div>
              </div>
            </div>

            {/* Data Cleaning Options */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <FlaskConical className="h-4 w-4 text-green-500" />
                <h4 className="font-medium text-sm">Data Cleaning Options</h4>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/30">
                  <div className="space-y-0.5">
                    <Label className="text-sm">Ignore Negative Heights</Label>
                    <p className="text-xs text-muted-foreground">
                      Exclude events with negative height values
                    </p>
                  </div>
                  <Switch
                    checked={localSettings.ignoreNegativeH}
                    onCheckedChange={(v) => handleSettingChange("ignoreNegativeH", v)}
                  />
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/30">
                  <div className="space-y-0.5">
                    <Label className="text-sm">Drop NA Rows</Label>
                    <p className="text-xs text-muted-foreground">
                      Remove rows with missing values
                    </p>
                  </div>
                  <Switch
                    checked={localSettings.dropNaRows}
                    onCheckedChange={(v) => handleSettingChange("dropNaRows", v)}
                  />
                </div>
              </div>
            </div>

            {/* Interactive Visualization */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/30">
              <div className="space-y-0.5">
                <Label className="text-sm">Interactive Plots</Label>
                <p className="text-xs text-muted-foreground">
                  Enable zoom, pan, and hover tooltips on charts
                </p>
              </div>
              <Switch
                checked={localSettings.useInteractivePlots}
                onCheckedChange={(v) => handleSettingChange("useInteractivePlots", v)}
              />
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-end gap-2 pt-4 border-t">
              <Button
                variant="outline"
                size="sm"
                onClick={handleResetSettings}
                className="gap-1"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Reset to Defaults
              </Button>
              <Button
                size="sm"
                onClick={handleSaveSettings}
                disabled={!hasChanges}
                className="gap-1"
              >
                <Save className="h-3.5 w-3.5" />
                Save Settings
              </Button>
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
