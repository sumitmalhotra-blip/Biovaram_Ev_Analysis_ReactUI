"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { ChevronDown, Columns, Loader2 } from "lucide-react"
import { useState } from "react"
import { useAnalysisStore } from "@/lib/store"
import { useApi } from "@/hooks/use-api"

export function ColumnMapping() {
  const [isOpen, setIsOpen] = useState(true)
  const { fcsAnalysis, apiConnected } = useAnalysisStore()
  const { uploadFCS } = useApi()

  // Get channels from the FCS results if available, otherwise use defaults
  const detectedColumns = fcsAnalysis.results?.channels || [
    "FSC-A",
    "FSC-H",
    "FSC-W",
    "SSC-A",
    "SSC-H",
    "SSC-W",
    "BV421-A",
    "BV510-A",
    "FITC-A",
    "PE-A",
    "APC-A",
    "Time",
  ]

  const handleConfirm = async () => {
    // If file exists but no results yet, trigger analysis
    if (fcsAnalysis.file && !fcsAnalysis.results) {
      await uploadFCS(fcsAnalysis.file)
    }
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <Card className="glass-card">
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-secondary/30 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Columns className="h-4 w-4 text-primary" />
                <CardTitle className="text-lg">Column Mapping</CardTitle>
              </div>
              <ChevronDown className={`h-4 w-4 transition-transform ${isOpen ? "rotate-180" : ""}`} />
            </div>
          </CardHeader>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="space-y-4 pt-0">
            <div className="p-3 bg-secondary/30 rounded-lg">
              <p className="text-xs text-muted-foreground mb-2">
                {fcsAnalysis.results ? "Detected channels from file:" : "Expected channels:"}
              </p>
              <div className="flex flex-wrap gap-1">
                {detectedColumns.map((col) => (
                  <span key={col} className="text-xs px-2 py-0.5 bg-secondary rounded font-mono">
                    {col}
                  </span>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-sm">FSC Column</Label>
                <Select defaultValue="fsc-a">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {detectedColumns
                      .filter((col) => col.toLowerCase().includes("fsc"))
                      .map((col) => (
                        <SelectItem key={col} value={col.toLowerCase()}>
                          {col}
                        </SelectItem>
                      ))}
                    {!detectedColumns.some((col) => col.toLowerCase().includes("fsc")) && (
                      <>
                        <SelectItem value="fsc-a">FSC-A</SelectItem>
                        <SelectItem value="fsc-h">FSC-H</SelectItem>
                      </>
                    )}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-sm">SSC Column</Label>
                <Select defaultValue="ssc-a">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {detectedColumns
                      .filter((col) => col.toLowerCase().includes("ssc"))
                      .map((col) => (
                        <SelectItem key={col} value={col.toLowerCase()}>
                          {col}
                        </SelectItem>
                      ))}
                    {!detectedColumns.some((col) => col.toLowerCase().includes("ssc")) && (
                      <>
                        <SelectItem value="ssc-a">SSC-A</SelectItem>
                        <SelectItem value="ssc-h">SSC-H</SelectItem>
                      </>
                    )}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Button 
              onClick={handleConfirm} 
              className="w-full"
              disabled={fcsAnalysis.isAnalyzing || !apiConnected}
            >
              {fcsAnalysis.isAnalyzing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                "Confirm Mapping & Analyze"
              )}
            </Button>
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  )
}
