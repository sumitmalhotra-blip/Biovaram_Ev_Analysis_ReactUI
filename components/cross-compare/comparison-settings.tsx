"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Input } from "@/components/ui/input"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Settings2, ChevronDown, ChevronUp, BarChart3, TrendingUp } from "lucide-react"
import { useAnalysisStore } from "@/lib/store"
import { useState } from "react"

export function ComparisonSettings() {
  const { crossComparisonSettings, setCrossComparisonSettings } = useAnalysisStore()
  const [isOpen, setIsOpen] = useState(true)
  
  const settings = crossComparisonSettings

  const updateSetting = <K extends keyof typeof settings>(
    key: K,
    value: typeof settings[K]
  ) => {
    setCrossComparisonSettings({
      ...settings,
      [key]: value,
    })
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
                <CardTitle className="text-base">Comparison Settings</CardTitle>
              </div>
              {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </div>
          </CardHeader>
        </CollapsibleTrigger>
        
        <CollapsibleContent>
          <CardContent className="space-y-6 pt-0">
            {/* Discrepancy Threshold */}
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <Label className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-yellow-500" />
                  Discrepancy Threshold (%)
                </Label>
                <span className="text-muted-foreground">{settings.discrepancyThreshold}%</span>
              </div>
              <Slider
                value={[settings.discrepancyThreshold]}
                onValueChange={(value) => updateSetting("discrepancyThreshold", value[0])}
                min={5}
                max={30}
                step={5}
                className="py-2"
              />
              <p className="text-xs text-muted-foreground">
                Highlight measurements that differ by more than this percentage
              </p>
            </div>

            {/* Histogram Settings */}
            <div className="space-y-4">
              <h4 className="text-sm font-medium flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-blue-500" />
                Histogram Settings
              </h4>
              
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <Label>Normalize Distributions</Label>
                  <p className="text-xs text-muted-foreground">
                    Show as probability density
                  </p>
                </div>
                <Switch
                  checked={settings.normalizeHistograms}
                  onCheckedChange={(checked) => updateSetting("normalizeHistograms", checked)}
                />
              </div>
              
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <Label>Bin Size (nm)</Label>
                  <span className="text-muted-foreground">{settings.binSize} nm</span>
                </div>
                <Slider
                  value={[settings.binSize]}
                  onValueChange={(value) => updateSetting("binSize", value[0])}
                  min={2}
                  max={20}
                  step={1}
                  className="py-2"
                />
              </div>
            </div>

            {/* Advanced Options */}
            <div className="space-y-4">
              <h4 className="text-sm font-medium">Advanced Options</h4>
              
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <Label>Show KDE Overlay</Label>
                  <p className="text-xs text-muted-foreground">
                    Kernel Density Estimation curves
                  </p>
                </div>
                <Switch
                  checked={settings.showKde}
                  onCheckedChange={(checked) => updateSetting("showKde", checked)}
                />
              </div>
              
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <Label>Show Statistical Tests</Label>
                  <p className="text-xs text-muted-foreground">
                    KS test, Mann-Whitney U test
                  </p>
                </div>
                <Switch
                  checked={settings.showStatistics}
                  onCheckedChange={(checked) => updateSetting("showStatistics", checked)}
                />
              </div>
              
              {/* Size Filter Range */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Min Size (nm)</Label>
                  <Input
                    type="number"
                    value={settings.minSizeFilter}
                    onChange={(e) => updateSetting("minSizeFilter", parseInt(e.target.value) || 0)}
                    min={0}
                    max={100}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Max Size (nm)</Label>
                  <Input
                    type="number"
                    value={settings.maxSizeFilter}
                    onChange={(e) => updateSetting("maxSizeFilter", parseInt(e.target.value) || 500)}
                    min={100}
                    max={1000}
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
