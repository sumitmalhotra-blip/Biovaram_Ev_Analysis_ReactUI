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
  Table2,
  FileSpreadsheet,
  FileJson,
  FileText
} from "lucide-react"
import { useAnalysisStore } from "@/lib/store"
import { useToast } from "@/hooks/use-toast"
import { NTASizeDistributionChart } from "./charts/nta-size-distribution-chart"
import { ConcentrationProfileChart } from "./charts/concentration-profile-chart"
import { TemperatureCorrectedComparison } from "./charts/temperature-corrected-comparison"
import { EVSizeCategoryPieChart } from "./charts/ev-size-category-pie-chart"
import { NTAStatisticsCards } from "./statistics-cards"
import { NTASizeDistributionBreakdown } from "./size-distribution-breakdown"
import { PositionAnalysis } from "./position-analysis"
import { 
  generateMarkdownReport, 
  downloadMarkdownReport,
  exportToParquet
} from "@/lib/export-utils"
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

  const handleExport = async (format: string) => {
    const sampleName = sampleId || fileName?.replace(/\.[^/.]+$/, "") || "nta_sample"
    
    try {
      switch (format) {
        case "CSV": {
          // Create CSV content from NTA results using actual NTAResult properties
          const csvHeaders = [
            "Sample ID",
            "Median Size (nm)",
            "Mean Size (nm)",
            "D10 (nm)",
            "D50 (nm)",
            "D90 (nm)",
            "Concentration (particles/mL)",
            "Temperature (°C)",
            "pH",
            "Total Particles",
            "50-80nm (%)",
            "80-100nm (%)",
            "100-120nm (%)",
            "120-150nm (%)",
            "150-200nm (%)",
            "200+nm (%)"
          ]
          
          const csvData = [
            sampleName,
            results.median_size_nm?.toFixed(2) || "N/A",
            results.mean_size_nm?.toFixed(2) || "N/A",
            results.d10_nm?.toFixed(2) || "N/A",
            results.d50_nm?.toFixed(2) || "N/A",
            results.d90_nm?.toFixed(2) || "N/A",
            results.concentration_particles_ml?.toExponential(2) || "N/A",
            results.temperature_celsius?.toFixed(1) || "N/A",
            results.ph?.toFixed(2) || "N/A",
            results.total_particles?.toString() || "N/A",
            results.bin_50_80nm_pct?.toFixed(2) || "N/A",
            results.bin_80_100nm_pct?.toFixed(2) || "N/A",
            results.bin_100_120nm_pct?.toFixed(2) || "N/A",
            results.bin_120_150nm_pct?.toFixed(2) || "N/A",
            results.bin_150_200nm_pct?.toFixed(2) || "N/A",
            results.bin_200_plus_pct?.toFixed(2) || "N/A"
          ]
          
          const csvContent = csvHeaders.join(",") + "\n" + csvData.join(",") + "\n"
          
          // Create and download the CSV file
          const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
          const url = URL.createObjectURL(blob)
          const link = document.createElement("a")
          link.href = url
          link.download = `${sampleName}_nta_results.csv`
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
          URL.revokeObjectURL(url)
          
          toast({
            title: "Export Complete",
            description: `NTA results exported as CSV successfully.`,
          })
          break
        }
        
        case "Excel": {
          // Export as tab-separated values (TSV) that Excel can open
          const excelHeaders = [
            "Sample ID",
            "Median Size (nm)",
            "Mean Size (nm)",
            "D10 (nm)",
            "D50 (nm)", 
            "D90 (nm)",
            "Concentration (particles/mL)",
            "Temperature (°C)",
            "pH",
            "Total Particles",
            "50-80nm (%)",
            "80-100nm (%)",
            "100-120nm (%)",
            "120-150nm (%)",
            "150-200nm (%)",
            "200+nm (%)"
          ]
          
          const excelData = [
            sampleName,
            results.median_size_nm?.toFixed(2) || "",
            results.mean_size_nm?.toFixed(2) || "",
            results.d10_nm?.toFixed(2) || "",
            results.d50_nm?.toFixed(2) || "",
            results.d90_nm?.toFixed(2) || "",
            results.concentration_particles_ml?.toExponential(2) || "",
            results.temperature_celsius?.toFixed(1) || "",
            results.ph?.toFixed(2) || "",
            results.total_particles?.toString() || "",
            results.bin_50_80nm_pct?.toFixed(2) || "",
            results.bin_80_100nm_pct?.toFixed(2) || "",
            results.bin_100_120nm_pct?.toFixed(2) || "",
            results.bin_120_150nm_pct?.toFixed(2) || "",
            results.bin_150_200nm_pct?.toFixed(2) || "",
            results.bin_200_plus_pct?.toFixed(2) || ""
          ]
          
          const excelContent = excelHeaders.join("\t") + "\n" + excelData.join("\t") + "\n"
          
          // Tab-separated values work well with Excel
          const blob = new Blob([excelContent], { type: "text/tab-separated-values;charset=utf-8;" })
          const url = URL.createObjectURL(blob)
          const link = document.createElement("a")
          link.href = url
          link.download = `${sampleName}_nta_results.xls`
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
          URL.revokeObjectURL(url)
          
          toast({
            title: "Export Complete",
            description: `NTA results exported as Excel file successfully.`,
          })
          break
        }
        
        case "JSON": {
          // Export full results as JSON with all available NTAResult properties
          const jsonContent = JSON.stringify({
            sample_id: sampleName,
            export_timestamp: new Date().toISOString(),
            analysis_type: "NTA",
            results: {
              id: results.id,
              median_size_nm: results.median_size_nm,
              mean_size_nm: results.mean_size_nm,
              d10_nm: results.d10_nm,
              d50_nm: results.d50_nm,
              d90_nm: results.d90_nm,
              concentration_particles_ml: results.concentration_particles_ml,
              temperature_celsius: results.temperature_celsius,
              ph: results.ph,
              total_particles: results.total_particles,
              size_bins: {
                "50-80nm_pct": results.bin_50_80nm_pct,
                "80-100nm_pct": results.bin_80_100nm_pct,
                "100-120nm_pct": results.bin_100_120nm_pct,
                "120-150nm_pct": results.bin_120_150nm_pct,
                "150-200nm_pct": results.bin_150_200nm_pct,
                "200+nm_pct": results.bin_200_plus_pct
              },
              size_statistics: results.size_statistics,
              processed_at: results.processed_at,
              parquet_file: results.parquet_file
            },
            metadata: {
              file_name: fileName
            }
          }, null, 2)
          
          const blob = new Blob([jsonContent], { type: "application/json;charset=utf-8;" })
          const url = URL.createObjectURL(blob)
          const link = document.createElement("a")
          link.href = url
          link.download = `${sampleName}_nta_results.json`
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
          URL.revokeObjectURL(url)
          
          toast({
            title: "Export Complete",
            description: `NTA results exported as JSON successfully.`,
          })
          break
        }
        
        case "PDF Report": {
          // Generate markdown report using the proper generateMarkdownReport signature
          const reportData = {
            title: `NTA Analysis Report - ${sampleName}`,
            sampleId: sampleName,
            analysisType: "NTA" as const,
            timestamp: new Date(),
            results: {
              "Median Size (nm)": results.median_size_nm?.toFixed(2) || "N/A",
              "Mean Size (nm)": results.mean_size_nm?.toFixed(2) || "N/A",
              "D10 (nm)": results.d10_nm?.toFixed(2) || "N/A",
              "D50 (nm)": results.d50_nm?.toFixed(2) || "N/A",
              "D90 (nm)": results.d90_nm?.toFixed(2) || "N/A",
              "Concentration (particles/mL)": results.concentration_particles_ml?.toExponential(2) || "N/A",
              "Temperature (°C)": results.temperature_celsius?.toFixed(1) || "N/A",
              "pH": results.ph?.toFixed(2) || "N/A",
              "Total Particles": results.total_particles?.toLocaleString() || "N/A"
            } as Record<string, unknown>,
            statistics: {
              "50-80nm (%)": results.bin_50_80nm_pct || 0,
              "80-100nm (%)": results.bin_80_100nm_pct || 0,
              "100-120nm (%)": results.bin_100_120nm_pct || 0,
              "120-150nm (%)": results.bin_120_150nm_pct || 0,
              "150-200nm (%)": results.bin_150_200nm_pct || 0,
              "200+nm (%)": results.bin_200_plus_pct || 0
            },
            charts: [
              { title: "Size Distribution", description: "Histogram of particle size distribution" },
              { title: "Concentration Profile", description: "Concentration vs size profile" },
              { title: "EV Category Breakdown", description: "Pie chart of EV size categories" }
            ],
            notes: `File: ${fileName || "N/A"}\nProcessed: ${results.processed_at || new Date().toISOString()}`
          }
          
          const reportContent = generateMarkdownReport(reportData)
          downloadMarkdownReport(reportContent, `${sampleName}_nta_report.md`)
          
          toast({
            title: "Export Complete",
            description: `NTA report exported as Markdown successfully.`,
          })
          break
        }
        
        default:
          toast({
            title: "Export Error",
            description: `Unsupported export format: ${format}`,
            variant: "destructive",
          })
      }
    } catch (error) {
      console.error("Export error:", error)
      toast({
        title: "Export Failed",
        description: `Failed to export NTA results: ${error instanceof Error ? error.message : "Unknown error"}`,
        variant: "destructive",
      })
    }
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

      {/* Size Distribution Breakdown and Pie Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <NTASizeDistributionBreakdown results={results} />
        <EVSizeCategoryPieChart data={results} />
      </div>

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
                <span className="text-muted-foreground">Median Size (D50):</span>
                <span className="font-mono font-medium">
                  {results.median_size_nm ? `${results.median_size_nm.toFixed(1)} nm` : "N/A"}
                </span>
              </div>
              {/* Note: Mean Size removed per client request (Surya, Dec 3, 2025) */}
              {/* "Mean is basically not the real metric... median is what really existed in the data set" */}
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
                    ±{results.size_statistics.std.toFixed(1)} nm
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
                className="w-full gap-1.5"
              >
                <FileSpreadsheet className="h-3.5 w-3.5" />
                CSV
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => handleExport("Excel")} 
                className="w-full gap-1.5"
              >
                <Table2 className="h-3.5 w-3.5" />
                Excel
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => handleExport("JSON")} 
                className="w-full gap-1.5"
              >
                <FileJson className="h-3.5 w-3.5" />
                JSON
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => handleExport("PDF Report")} 
                className="w-full gap-1.5"
              >
                <FileText className="h-3.5 w-3.5" />
                Report
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
              <PositionAnalysis />
            </TabsContent>

            <TabsContent value="corrected" className="space-y-4">
              <TemperatureCorrectedComparison data={results} />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}
