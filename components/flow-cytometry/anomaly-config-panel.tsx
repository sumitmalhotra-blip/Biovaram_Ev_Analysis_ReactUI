"use client"

/**
 * Anomaly Detection Configuration Panel
 * CRMIT-008: Configurable thresholds for anomaly detection
 * 
 * Features:
 * - Z-score threshold configuration
 * - IQR factor configuration
 * - Detection method selection
 * - Real-time threshold preview
 * - Preset configurations
 */

import { useState, useCallback } from "react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Separator } from "@/components/ui/separator"
import {
  AlertTriangle,
  Settings2,
  Info,
  Zap,
  RotateCcw,
  Save,
  ChevronDown,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useAnalysisStore } from "@/lib/store"
import { useToast } from "@/hooks/use-toast"

// Anomaly detection configuration interface
export interface AnomalyConfig {
  enabled: boolean
  method: "zscore" | "iqr" | "both"
  zscoreThreshold: number
  iqrFactor: number
  highlightOnScatter: boolean
  highlightOnHistogram: boolean
  showAnomalyBadges: boolean
  autoDetect: boolean
  // Advanced options
  minAnomalyCount: number
  maxAnomalyPercentage: number
}

// Preset configurations
const PRESETS: Record<string, Partial<AnomalyConfig>> = {
  conservative: {
    method: "zscore",
    zscoreThreshold: 4.0,
    iqrFactor: 2.0,
    minAnomalyCount: 10,
    maxAnomalyPercentage: 5,
  },
  standard: {
    method: "zscore",
    zscoreThreshold: 3.0,
    iqrFactor: 1.5,
    minAnomalyCount: 5,
    maxAnomalyPercentage: 10,
  },
  sensitive: {
    method: "both",
    zscoreThreshold: 2.5,
    iqrFactor: 1.25,
    minAnomalyCount: 3,
    maxAnomalyPercentage: 20,
  },
  aggressive: {
    method: "both",
    zscoreThreshold: 2.0,
    iqrFactor: 1.0,
    minAnomalyCount: 1,
    maxAnomalyPercentage: 30,
  },
}

// Default configuration
const DEFAULT_CONFIG: AnomalyConfig = {
  enabled: true,
  method: "zscore",
  zscoreThreshold: 3.0,
  iqrFactor: 1.5,
  highlightOnScatter: true,
  highlightOnHistogram: true,
  showAnomalyBadges: true,
  autoDetect: false,
  minAnomalyCount: 5,
  maxAnomalyPercentage: 10,
}

interface AnomalyConfigPanelProps {
  className?: string
  onConfigChange?: (config: AnomalyConfig) => void
  compact?: boolean
}

export function AnomalyConfigPanel({ 
  className,
  onConfigChange,
  compact = false,
}: AnomalyConfigPanelProps) {
  const { toast } = useToast()
  const { fcsAnalysisSettings, setFcsAnalysisSettings } = useAnalysisStore()
  
  // Initialize config from store or defaults
  // Convert store method format to internal format
  const storeMethodToConfig = (m?: string): AnomalyConfig["method"] => {
    if (m === "Z-Score") return "zscore"
    if (m === "IQR") return "iqr"
    if (m === "Both") return "both"
    return "zscore"
  }
  
  const [config, setConfig] = useState<AnomalyConfig>(() => ({
    ...DEFAULT_CONFIG,
    enabled: fcsAnalysisSettings?.anomalyDetectionEnabled ?? true,
    method: storeMethodToConfig(fcsAnalysisSettings?.anomalyMethod),
    zscoreThreshold: fcsAnalysisSettings?.zscoreThreshold ?? 3.0,
    iqrFactor: fcsAnalysisSettings?.iqrFactor ?? 1.5,
  }))
  
  const [isDirty, setIsDirty] = useState(false)

  // Update config and mark as dirty
  const updateConfig = useCallback(<K extends keyof AnomalyConfig>(
    key: K,
    value: AnomalyConfig[K]
  ) => {
    setConfig(prev => {
      const updated = { ...prev, [key]: value }
      onConfigChange?.(updated)
      return updated
    })
    setIsDirty(true)
  }, [onConfigChange])

  // Apply preset
  const applyPreset = useCallback((presetName: string) => {
    const preset = PRESETS[presetName]
    if (preset) {
      setConfig(prev => {
        const updated = { ...prev, ...preset }
        onConfigChange?.(updated)
        return updated
      })
      setIsDirty(true)
      toast({
        title: "Preset Applied",
        description: `Applied "${presetName}" anomaly detection settings`,
      })
    }
  }, [onConfigChange, toast])

  // Reset to defaults
  const resetToDefaults = useCallback(() => {
    setConfig(DEFAULT_CONFIG)
    onConfigChange?.(DEFAULT_CONFIG)
    setIsDirty(true)
    toast({
      title: "Reset Complete",
      description: "Anomaly detection settings reset to defaults",
    })
  }, [onConfigChange, toast])

  // Convert internal method format to store format
  const configMethodToStore = (m: AnomalyConfig["method"]): "Z-Score" | "IQR" | "Both" => {
    if (m === "zscore") return "Z-Score"
    if (m === "iqr") return "IQR"
    if (m === "both") return "Both"
    return "Z-Score"
  }

  // Save configuration to store
  const saveConfig = useCallback(() => {
    setFcsAnalysisSettings({
      anomalyDetectionEnabled: config.enabled,
      anomalyMethod: configMethodToStore(config.method),
      zscoreThreshold: config.zscoreThreshold,
      iqrFactor: config.iqrFactor,
    })
    setIsDirty(false)
    toast({
      title: "Settings Saved",
      description: "Anomaly detection configuration saved successfully",
    })
  }, [config, setFcsAnalysisSettings, toast])

  // Compact view for embedding in other panels
  if (compact) {
    return (
      <Popover>
        <PopoverTrigger asChild>
          <Button variant="outline" size="sm" className="gap-2">
            <AlertTriangle className="h-4 w-4" />
            Anomaly Settings
            <ChevronDown className="h-3 w-3" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-80" align="end">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-medium">Anomaly Detection</h4>
              <Switch
                checked={config.enabled}
                onCheckedChange={(checked) => updateConfig("enabled", checked)}
              />
            </div>
            
            {config.enabled && (
              <>
                <div className="space-y-2">
                  <Label className="text-xs">Detection Method</Label>
                  <Select
                    value={config.method}
                    onValueChange={(v) => updateConfig("method", v as AnomalyConfig["method"])}
                  >
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="zscore">Z-Score Only</SelectItem>
                      <SelectItem value="iqr">IQR Only</SelectItem>
                      <SelectItem value="both">Both Methods</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                {(config.method === "zscore" || config.method === "both") && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label className="text-xs">Z-Score Threshold</Label>
                      <span className="text-xs font-mono">{config.zscoreThreshold.toFixed(1)}</span>
                    </div>
                    <Slider
                      value={[config.zscoreThreshold]}
                      onValueChange={([v]) => updateConfig("zscoreThreshold", v)}
                      min={1.5}
                      max={5.0}
                      step={0.1}
                      className="w-full"
                    />
                  </div>
                )}
                
                {(config.method === "iqr" || config.method === "both") && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label className="text-xs">IQR Factor</Label>
                      <span className="text-xs font-mono">{config.iqrFactor.toFixed(2)}</span>
                    </div>
                    <Slider
                      value={[config.iqrFactor]}
                      onValueChange={([v]) => updateConfig("iqrFactor", v)}
                      min={1.0}
                      max={3.0}
                      step={0.05}
                      className="w-full"
                    />
                  </div>
                )}
                
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" className="flex-1 text-xs" onClick={resetToDefaults}>
                    Reset
                  </Button>
                  <Button size="sm" className="flex-1 text-xs" onClick={saveConfig} disabled={!isDirty}>
                    Apply
                  </Button>
                </div>
              </>
            )}
          </div>
        </PopoverContent>
      </Popover>
    )
  }

  // Full panel view
  return (
    <Card className={cn("", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Settings2 className="h-4 w-4 text-primary" />
              Anomaly Detection Settings
            </CardTitle>
            <CardDescription className="text-xs mt-1">
              Configure thresholds and methods for anomaly detection
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              checked={config.enabled}
              onCheckedChange={(checked) => updateConfig("enabled", checked)}
            />
            <Badge variant={config.enabled ? "default" : "secondary"}>
              {config.enabled ? "Enabled" : "Disabled"}
            </Badge>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Preset Selection */}
        <div className="space-y-2">
          <Label className="text-sm font-medium flex items-center gap-2">
            <Zap className="h-3 w-3" />
            Quick Presets
          </Label>
          <div className="flex flex-wrap gap-2">
            {Object.entries(PRESETS).map(([name, preset]) => (
              <TooltipProvider key={name}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => applyPreset(name)}
                      className="capitalize"
                    >
                      {name}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-xs">
                      Z-Score: {preset.zscoreThreshold}, IQR: {preset.iqrFactor}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            ))}
          </div>
        </div>

        <Separator />

        {/* Detection Method */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">Detection Method</Label>
          <Select
            value={config.method}
            onValueChange={(v) => updateConfig("method", v as AnomalyConfig["method"])}
            disabled={!config.enabled}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="zscore">
                <div className="flex items-center gap-2">
                  <span>Z-Score Only</span>
                  <Badge variant="outline" className="text-xs">Standard</Badge>
                </div>
              </SelectItem>
              <SelectItem value="iqr">
                <div className="flex items-center gap-2">
                  <span>IQR Only</span>
                  <Badge variant="outline" className="text-xs">Robust</Badge>
                </div>
              </SelectItem>
              <SelectItem value="both">
                <div className="flex items-center gap-2">
                  <span>Both Methods</span>
                  <Badge variant="outline" className="text-xs">Comprehensive</Badge>
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            {config.method === "zscore" && "Detects points more than N standard deviations from mean"}
            {config.method === "iqr" && "Detects points outside the interquartile range bounds"}
            {config.method === "both" && "Uses both methods - flags points detected by either"}
          </p>
        </div>

        {/* Z-Score Threshold */}
        {(config.method === "zscore" || config.method === "both") && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium flex items-center gap-2">
                Z-Score Threshold
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger>
                      <Info className="h-3 w-3 text-muted-foreground" />
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p className="text-xs">
                        Points with |Z-score| greater than this value are flagged as anomalies.
                        Lower values = more sensitive detection.
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </Label>
              <Badge variant="secondary" className="font-mono">
                {config.zscoreThreshold.toFixed(1)}σ
              </Badge>
            </div>
            <Slider
              value={[config.zscoreThreshold]}
              onValueChange={([v]) => updateConfig("zscoreThreshold", v)}
              min={1.5}
              max={5.0}
              step={0.1}
              disabled={!config.enabled}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>More Sensitive (1.5σ)</span>
              <span>Less Sensitive (5.0σ)</span>
            </div>
          </div>
        )}

        {/* IQR Factor */}
        {(config.method === "iqr" || config.method === "both") && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium flex items-center gap-2">
                IQR Factor
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger>
                      <Info className="h-3 w-3 text-muted-foreground" />
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p className="text-xs">
                        Points outside Q1 - (factor × IQR) or Q3 + (factor × IQR) are flagged.
                        Standard is 1.5, lower values = more sensitive.
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </Label>
              <Badge variant="secondary" className="font-mono">
                {config.iqrFactor.toFixed(2)}×
              </Badge>
            </div>
            <Slider
              value={[config.iqrFactor]}
              onValueChange={([v]) => updateConfig("iqrFactor", v)}
              min={1.0}
              max={3.0}
              step={0.05}
              disabled={!config.enabled}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>More Sensitive (1.0×)</span>
              <span>Less Sensitive (3.0×)</span>
            </div>
          </div>
        )}

        <Separator />

        {/* Visualization Options */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">Visualization Options</Label>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-sm text-muted-foreground cursor-pointer" htmlFor="highlight-scatter">
                Highlight on Scatter Plots
              </Label>
              <Switch
                id="highlight-scatter"
                checked={config.highlightOnScatter}
                onCheckedChange={(checked) => updateConfig("highlightOnScatter", checked)}
                disabled={!config.enabled}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label className="text-sm text-muted-foreground cursor-pointer" htmlFor="highlight-histogram">
                Highlight on Histograms
              </Label>
              <Switch
                id="highlight-histogram"
                checked={config.highlightOnHistogram}
                onCheckedChange={(checked) => updateConfig("highlightOnHistogram", checked)}
                disabled={!config.enabled}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label className="text-sm text-muted-foreground cursor-pointer" htmlFor="show-badges">
                Show Anomaly Count Badges
              </Label>
              <Switch
                id="show-badges"
                checked={config.showAnomalyBadges}
                onCheckedChange={(checked) => updateConfig("showAnomalyBadges", checked)}
                disabled={!config.enabled}
              />
            </div>
          </div>
        </div>

        <Separator />

        {/* Action Buttons */}
        <div className="flex items-center justify-between gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={resetToDefaults}
            className="gap-2"
          >
            <RotateCcw className="h-3 w-3" />
            Reset
          </Button>
          <Button
            size="sm"
            onClick={saveConfig}
            disabled={!isDirty}
            className="gap-2"
          >
            <Save className="h-3 w-3" />
            Save Settings
          </Button>
        </div>

        {/* Preview Info */}
        {config.enabled && (
          <div className="rounded-lg border bg-muted/30 p-3 mt-4">
            <h5 className="text-xs font-medium mb-2 flex items-center gap-1">
              <AlertTriangle className="h-3 w-3 text-yellow-500" />
              Detection Preview
            </h5>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-muted-foreground">Method:</span>{" "}
                <span className="font-medium capitalize">{config.method}</span>
              </div>
              {(config.method === "zscore" || config.method === "both") && (
                <div>
                  <span className="text-muted-foreground">Z-Score:</span>{" "}
                  <span className="font-medium">±{config.zscoreThreshold}σ</span>
                </div>
              )}
              {(config.method === "iqr" || config.method === "both") && (
                <div>
                  <span className="text-muted-foreground">IQR Factor:</span>{" "}
                  <span className="font-medium">{config.iqrFactor}×</span>
                </div>
              )}
              <div>
                <span className="text-muted-foreground">Scatter:</span>{" "}
                <span className="font-medium">{config.highlightOnScatter ? "On" : "Off"}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Histogram:</span>{" "}
                <span className="font-medium">{config.highlightOnHistogram ? "On" : "Off"}</span>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default AnomalyConfigPanel
