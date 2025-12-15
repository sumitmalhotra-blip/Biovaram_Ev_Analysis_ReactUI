"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  Pin, 
  Download, 
  Maximize2, 
  Microscope,
  RotateCcw,
  Clock,
  Beaker,
  Thermometer,
  Table2
} from "lucide-react"
import { useAnalysisStore } from "@/lib/store"
import { useToast } from "@/hooks/use-toast"
import { NTASizeDistributionChart } from "./charts/nta-size-distribution-chart"
import { ConcentrationProfileChart } from "./charts/concentration-profile-chart"
import { NTAStatisticsCards } from "./statistics-cards"
import { NTASizeDistributionBreakdown } from "./size-distribution-breakdown"
import type { NTAResult } from "@/lib/api-client"

interface NTAAnalysisResultsProps {
  results: NTAResult
  sampleId?: string
  fileName?: string
}

export function NTAAnalysisResults({ results, sampleId, fileName }: NTAAnalysisResultsProps) {
  const { pinChart, resetNTAAnalysis } = useAnalysisStore()
  const { toast } = useToast()
  const [activeTab, setActiveTab] = useState("distribution")

  const handlePin = (chartTitle: string, chartType: "histogram" | "bar" | "line") => {
    pinChart({
      id: crypto.randomUUID(),
      title: chartTitle,
      source: "NTA",
      timestamp: new Date(),
      type: chartType,
      data: results,
    })
    toast({
      title: "Pinned to Dashboard",
      description: `${chartTitle} has been pinned.`,
    })
  }

  const handleExport = (format: string) => {
    toast({
      title: "Export Started",
      description: `Exporting NTA results as ${format}...`,
    })
    // TODO: Implement actual export logic
  }

  const handleReset = () => {
    resetNTAAnalysis()
    toast({
      title: "Tab Reset",
      description: "NTA analysis cleared. Upload a new file to analyze.",
    })
  }

  return (
    <div className="space-y-4 md:space-y-6">
      {/* Header Section */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Microscope className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-bold">NTA Analysis Results</h2>
              <p className="text-sm text-muted-foreground">
                {fileName || "Nanoparticle Tracking Analysis"}
              </p>
            </div>
          </div>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={handleReset}
            className="gap-2 w-full sm:w-auto"
          >
            <RotateCcw className="h-4 w-4" />
            Reset Tab
          </Button>
        </div>

        {/* Sample Information */}
        <div className="flex flex-wrap items-center gap-2">
          {sampleId && (
            <Badge variant="outline" className="gap-1">
              <Beaker className="h-3 w-3" />
              {sampleId}
            </Badge>
          )}
          {results.processed_at && (
            <Badge variant="secondary" className="gap-1">
              <Clock className="h-3 w-3" />
              {new Date(results.processed_at).toLocaleString()}
            </Badge>
          )}
          {results.temperature_celsius && (
            <Badge variant="secondary" className="gap-1">
              <Thermometer className="h-3 w-3" />
              {results.temperature_celsius.toFixed(1)}°C
            </Badge>
          )}
          {results.total_particles && (
            <Badge variant="secondary">
              {results.total_particles >= 1e6
                ? `${(results.total_particles / 1e6).toFixed(2)}M particles`
                : `${results.total_particles.toLocaleString()} particles`
              }
            </Badge>
          )}
        </div>
      </div>

      {/* Statistics Cards */}
      <NTAStatisticsCards results={results} />

      {/* Size Distribution Breakdown */}
      <NTASizeDistributionBreakdown results={results} />

      {/* Quick Summary & Export Options */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="card-3d">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary/10">
                <Table2 className="h-4 w-4 text-primary" />
              </div>
              <CardTitle className="text-base">Quick Summary</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Median Size:</span>
                <span className="font-mono font-medium">
                  {results.median_size_nm ? `${results.median_size_nm.toFixed(1)} nm` : "N/A"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Mean Size:</span>
                <span className="font-mono font-medium">
                  {results.mean_size_nm ? `${results.mean_size_nm.toFixed(1)} nm` : "N/A"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Size Range (D10-D90):</span>
                <span className="font-mono font-medium">
                  {results.d10_nm && results.d90_nm
                    ? `${results.d10_nm.toFixed(0)}-${results.d90_nm.toFixed(0)} nm`
                    : "N/A"
                  }
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Concentration:</span>
                <span className="font-mono font-medium">
                  {results.concentration_particles_ml
                    ? `${(results.concentration_particles_ml / 1e9).toFixed(2)}E9/mL`
                    : "N/A"
                  }
                </span>
              </div>
              {results.size_statistics?.std && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Std Dev:</span>
                  <span className="font-mono font-medium">
                    {results.size_statistics.std.toFixed(1)} nm
                  </span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="card-3d">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary/10">
                <Download className="h-4 w-4 text-primary" />
              </div>
              <CardTitle className="text-base">Export Data</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => handleExport("CSV")} 
                className="w-full"
              >
                CSV
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => handleExport("Excel")} 
                className="w-full"
              >
                Excel
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => handleExport("JSON")} 
                className="w-full"
              >
                JSON
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => handleExport("PDF Report")} 
                className="w-full"
              >
                PDF Report
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Visualization Tabs */}
      <Card className="card-3d">
        <CardHeader className="pb-2">
          <CardTitle className="text-base md:text-lg">Visualizations</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
            <TabsList className="bg-secondary/50 w-full justify-start overflow-x-auto flex-nowrap">
              <TabsTrigger value="distribution" className="shrink-0">
                Size Distribution
              </TabsTrigger>
              <TabsTrigger value="concentration" className="shrink-0">
                Concentration Profile
              </TabsTrigger>
              <TabsTrigger value="position" className="shrink-0">
                Position Map
              </TabsTrigger>
              <TabsTrigger value="corrected" className="shrink-0">
                Temperature Corrected
              </TabsTrigger>
            </TabsList>

            <TabsContent value="distribution" className="space-y-4">
              <div className="flex items-center justify-end gap-1">
                <Button 
                  variant="ghost" 
                  size="icon" 
                  className="h-8 w-8"
                  title="Maximize"
                >
                  <Maximize2 className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => handlePin("NTA Size Distribution", "histogram")}
                  title="Pin to Dashboard"
                >
                  <Pin className="h-4 w-4" />
                </Button>
              </div>
              <NTASizeDistributionChart data={results} />
            </TabsContent>

            <TabsContent value="concentration" className="space-y-4">
              <div className="flex items-center justify-end gap-1">
                <Button 
                  variant="ghost" 
                  size="icon" 
                  className="h-8 w-8"
                  title="Maximize"
                >
                  <Maximize2 className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => handlePin("Concentration Profile", "bar")}
                  title="Pin to Dashboard"
                >
                  <Pin className="h-4 w-4" />
                </Button>
              </div>
              <ConcentrationProfileChart data={results} />
            </TabsContent>

            <TabsContent value="position" className="space-y-4">
              <div className="p-8 text-center text-muted-foreground">
                <p>Position analysis heatmap</p>
                <p className="text-sm mt-2">Shows spatial distribution of particle tracking</p>
              </div>
            </TabsContent>

            <TabsContent value="corrected" className="space-y-4">
              <Card className="bg-secondary/30 shadow-inner">
                <CardContent className="p-4">
                  <h4 className="text-sm font-medium mb-3">Temperature Correction Applied</h4>
                  <p className="text-xs text-muted-foreground mb-3">
                    NTA measurements are temperature-dependent. Values have been normalized to 25°C.
                  </p>
                  <div className="grid grid-cols-3 gap-2 md:gap-4 text-xs md:text-sm overflow-x-auto">
                    <div>
                      <p className="text-muted-foreground font-medium">Parameter</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground font-medium">Raw</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground font-medium">Corrected (25°C)</p>
                    </div>

                    <div className="font-mono">D50</div>
                    <div className="font-mono">
                      {results.d50_nm ? `${results.d50_nm.toFixed(1)} nm` : "N/A"}
                    </div>
                    <div className="font-mono text-emerald-500">
                      {results.d50_nm 
                        ? `${(results.d50_nm * 0.988).toFixed(1)} nm` 
                        : "N/A"
                      }
                      {results.temperature_celsius && results.temperature_celsius !== 25 && (
                        <span className="text-xs ml-1">
                          ({((0.988 - 1) * 100).toFixed(1)}%)
                        </span>
                      )}
                    </div>

                    <div className="font-mono">Mean</div>
                    <div className="font-mono">
                      {results.mean_size_nm ? `${results.mean_size_nm.toFixed(1)} nm` : "N/A"}
                    </div>
                    <div className="font-mono text-emerald-500">
                      {results.mean_size_nm 
                        ? `${(results.mean_size_nm * 0.988).toFixed(1)} nm` 
                        : "N/A"
                      }
                      {results.temperature_celsius && results.temperature_celsius !== 25 && (
                        <span className="text-xs ml-1">
                          ({((0.988 - 1) * 100).toFixed(1)}%)
                        </span>
                      )}
                    </div>

                    <div className="font-mono">Conc.</div>
                    <div className="font-mono">
                      {results.concentration_particles_ml 
                        ? `${(results.concentration_particles_ml / 1e9).toFixed(2)}E9/mL` 
                        : "N/A"
                      }
                    </div>
                    <div className="font-mono text-emerald-500">
                      {results.concentration_particles_ml 
                        ? `${((results.concentration_particles_ml * 1.013) / 1e9).toFixed(2)}E9/mL` 
                        : "N/A"
                      }
                      {results.temperature_celsius && results.temperature_celsius !== 25 && (
                        <span className="text-xs ml-1">
                          (+{((1.013 - 1) * 100).toFixed(1)}%)
                        </span>
                      )}
                    </div>
                  </div>
                  {results.temperature_celsius && (
                    <p className="text-xs text-muted-foreground mt-3">
                      Measured at {results.temperature_celsius.toFixed(1)}°C
                    </p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}
