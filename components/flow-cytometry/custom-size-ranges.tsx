"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { 
  Plus, 
  Trash2, 
  Ruler, 
  Sparkles,
  ChevronDown,
  ChevronUp
} from "lucide-react"
import { useAnalysisStore, type SizeRange } from "@/lib/store"
import { cn } from "@/lib/utils"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

interface CustomSizeRangesProps {
  sizeData?: number[] // Actual particle sizes from analysis
  className?: string
}

// Preset configurations
const PRESETS = {
  evStandard: {
    name: "EV Standard",
    description: "<50, 50-200, >200 nm",
    ranges: [
      { name: "Small EVs (<50nm)", min: 0, max: 50, color: "#22c55e" },
      { name: "Exosomes (50-200nm)", min: 50, max: 200, color: "#3b82f6" },
      { name: "Microvesicles (>200nm)", min: 200, max: 1000, color: "#a855f7" },
    ],
  },
  classic: {
    name: "Classic EVs",
    description: "30-100, 100-150, 150-200 nm",
    ranges: [
      { name: "Small EVs", min: 30, max: 100, color: "#22c55e" },
      { name: "Medium EVs", min: 100, max: 150, color: "#3b82f6" },
      { name: "Large EVs", min: 150, max: 200, color: "#a855f7" },
    ],
  },
  exosome: {
    name: "Exosome Focus",
    description: "40-80, 80-120 nm",
    ranges: [
      { name: "Exosomes (40-80nm)", min: 40, max: 80, color: "#22c55e" },
      { name: "Small MVs (80-120nm)", min: 80, max: 120, color: "#3b82f6" },
    ],
  },
  detailed: {
    name: "Detailed",
    description: "50nm bins from 0-300nm",
    ranges: [
      { name: "0-50nm", min: 0, max: 50, color: "#22c55e" },
      { name: "50-100nm", min: 50, max: 100, color: "#3b82f6" },
      { name: "100-150nm", min: 100, max: 150, color: "#a855f7" },
      { name: "150-200nm", min: 150, max: 200, color: "#f59e0b" },
      { name: "200-300nm", min: 200, max: 300, color: "#ef4444" },
    ],
  },
}

export function CustomSizeRanges({ sizeData, className }: CustomSizeRangesProps) {
  const { fcsAnalysis, setFCSSizeRanges } = useAnalysisStore()
  const sizeRanges = fcsAnalysis.sizeRanges || []
  
  const [isOpen, setIsOpen] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const [newRange, setNewRange] = useState({ name: "", min: 0, max: 100 })

  // Calculate counts for each range based on actual size data
  const calculateCounts = (ranges: SizeRange[], data?: number[]) => {
    if (!data || data.length === 0) return ranges.map(() => ({ count: 0, percentage: 0 }))
    
    return ranges.map((range) => {
      const count = data.filter((size) => size >= range.min && size <= range.max).length
      const percentage = (count / data.length) * 100
      return { count, percentage }
    })
  }

  const counts = calculateCounts(sizeRanges, sizeData)
  
  // TASK-006: Validate that new range doesn't overlap with existing ranges
  const checkOverlap = (newMin: number, newMax: number): string | null => {
    for (const range of sizeRanges) {
      // Check if ranges overlap: (A.min <= B.max) AND (A.max >= B.min)
      if (newMin <= range.max && newMax >= range.min) {
        return `Overlaps with "${range.name}" (${range.min}-${range.max}nm)`
      }
    }
    return null
  }
  
  const overlapError = newRange.min < newRange.max ? checkOverlap(newRange.min, newRange.max) : null

  const handleAddRange = () => {
    // TASK-006: Enhanced validation with overlap check
    if (!newRange.name.trim()) return
    if (newRange.min >= newRange.max) return
    if (overlapError) return
    
    const colors = ["#22c55e", "#3b82f6", "#a855f7", "#f59e0b", "#ef4444", "#06b6d4"]
    const newRangeWithColor: SizeRange = {
      ...newRange,
      color: colors[sizeRanges.length % colors.length],
    }
    
    setFCSSizeRanges([...sizeRanges, newRangeWithColor])
    setNewRange({ name: "", min: 0, max: 100 })
    setShowAddForm(false)
  }

  const handleRemoveRange = (index: number) => {
    setFCSSizeRanges(sizeRanges.filter((_, i) => i !== index))
  }

  const handleApplyPreset = (presetKey: keyof typeof PRESETS) => {
    setFCSSizeRanges(PRESETS[presetKey].ranges)
  }

  return (
    <Card className={cn("card-3d", className)}>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CardHeader className="pb-2">
          <CollapsibleTrigger asChild>
            <div className="flex items-center justify-between cursor-pointer group">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-primary/10">
                  <Ruler className="h-4 w-4 text-primary" />
                </div>
                <CardTitle className="text-base md:text-lg">Size Range Analysis</CardTitle>
                {sizeRanges.length > 0 && (
                  <Badge variant="secondary" className="ml-2">
                    {sizeRanges.length} ranges
                  </Badge>
                )}
              </div>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                {isOpen ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </Button>
            </div>
          </CollapsibleTrigger>
        </CardHeader>

        <CollapsibleContent>
          <CardContent className="space-y-4">
            {/* Preset Buttons */}
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Quick Presets</Label>
              <div className="flex flex-wrap gap-2">
                {Object.entries(PRESETS).map(([key, preset]) => (
                  <Button
                    key={key}
                    variant="outline"
                    size="sm"
                    className="text-xs h-8"
                    onClick={() => handleApplyPreset(key as keyof typeof PRESETS)}
                  >
                    <Sparkles className="h-3 w-3 mr-1" />
                    {preset.name}
                  </Button>
                ))}
              </div>
            </div>

            {/* Current Ranges */}
            {sizeRanges.length > 0 && (
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Current Ranges</Label>
                <div className="space-y-2">
                  {sizeRanges.map((range, index) => {
                    const { count, percentage } = counts[index]
                    return (
                      <div
                        key={index}
                        className="flex items-center justify-between p-3 rounded-lg bg-secondary/30 border border-border/50 group"
                      >
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <div
                            className="w-3 h-3 rounded-full shrink-0"
                            style={{ backgroundColor: range.color }}
                          />
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium truncate">{range.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {range.min}-{range.max} nm
                            </p>
                          </div>
                        </div>
                        
                        {sizeData && sizeData.length > 0 && (
                          <div className="text-right mr-3">
                            <p className="text-sm font-mono font-semibold">
                              {count.toLocaleString()}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {percentage.toFixed(1)}%
                            </p>
                          </div>
                        )}
                        
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity text-destructive hover:text-destructive hover:bg-destructive/10"
                          onClick={() => handleRemoveRange(index)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Add Range Form */}
            {showAddForm ? (
              <div className="space-y-3 p-4 rounded-lg border border-border/50 bg-secondary/20">
                <Label className="text-sm">Add New Range</Label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">Name</Label>
                    <Input
                      placeholder="e.g., Small EVs"
                      value={newRange.name}
                      onChange={(e) => setNewRange({ ...newRange, name: e.target.value })}
                      className="h-9"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">Min (nm)</Label>
                    <Input
                      type="number"
                      min={0}
                      max={1000}
                      value={newRange.min}
                      onChange={(e) => setNewRange({ ...newRange, min: Number(e.target.value) })}
                      className="h-9"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">Max (nm)</Label>
                    <Input
                      type="number"
                      min={0}
                      max={1000}
                      value={newRange.max}
                      onChange={(e) => setNewRange({ ...newRange, max: Number(e.target.value) })}
                      className="h-9"
                    />
                  </div>
                </div>
                {/* TASK-006: Validation error display */}
                {newRange.min >= newRange.max && newRange.max > 0 && (
                  <p className="text-xs text-destructive">Min must be less than Max</p>
                )}
                {overlapError && (
                  <p className="text-xs text-destructive">{overlapError}</p>
                )}
                <div className="flex gap-2 justify-end">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setShowAddForm(false)
                      setNewRange({ name: "", min: 0, max: 100 })
                    }}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleAddRange}
                    disabled={!newRange.name.trim() || newRange.min >= newRange.max || !!overlapError}
                  >
                    Add Range
                  </Button>
                </div>
              </div>
            ) : (
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={() => setShowAddForm(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Custom Range
              </Button>
            )}

            {/* Size Range Distribution Chart */}
            {sizeRanges.length > 0 && sizeData && sizeData.length > 0 && (
              <div className="space-y-2 pt-2">
                <Label className="text-xs text-muted-foreground">Distribution</Label>
                <div className="flex gap-1 h-6 rounded-lg overflow-hidden bg-secondary/30">
                  {sizeRanges.map((range, index) => {
                    const { percentage } = counts[index]
                    return (
                      <div
                        key={index}
                        className="h-full transition-all duration-300 flex items-center justify-center text-xs font-medium text-white"
                        style={{
                          width: `${Math.max(percentage, 2)}%`,
                          backgroundColor: range.color,
                        }}
                        title={`${range.name}: ${percentage.toFixed(1)}%`}
                      >
                        {percentage > 10 && `${percentage.toFixed(0)}%`}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Empty state */}
            {sizeRanges.length === 0 && (
              <div className="text-center py-6 text-muted-foreground">
                <Ruler className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No size ranges defined</p>
                <p className="text-xs">Use a preset or add custom ranges</p>
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
