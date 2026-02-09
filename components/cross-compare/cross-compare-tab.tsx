"use client"

import { useEffect, useState, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Pin, Maximize2, CheckCircle, GitCompare, Loader2, AlertCircle, RefreshCw, Download, RotateCcw } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useAnalysisStore } from "@/lib/store"
import { useToast } from "@/hooks/use-toast"
import { useApi } from "@/hooks/use-api"
import { apiClient, type Sample, type FCSResult, type NTAResult, type CrossValidationResult } from "@/lib/api-client"
import { OverlayHistogramChart } from "./charts/overlay-histogram-chart"
import { DiscrepancyChart } from "./charts/discrepancy-chart"
import { KDEComparisonChart } from "./charts/kde-comparison-chart"
import { CorrelationScatterChart } from "./charts/correlation-scatter-chart"
import { StatisticalComparisonTable } from "./statistical-comparison-table"
import { StatisticalTestsCard } from "./statistical-tests-card"
import { MethodComparisonSummary } from "./method-comparison-summary"
import { ValidationVerdictCard } from "./validation-verdict-card"
import * as XLSX from 'xlsx'

export function CrossCompareTab() {
  const { pinChart, apiSamples, fcsAnalysis, ntaAnalysis, apiConnected } = useAnalysisStore()
  const { fetchSamples } = useApi()
  const { toast } = useToast()

  const [selectedFcsSample, setSelectedFcsSample] = useState<string>("")
  const [selectedNtaSample, setSelectedNtaSample] = useState<string>("")
  const [fcsResults, setFcsResults] = useState<FCSResult | null>(null)
  const [ntaResults, setNtaResults] = useState<NTAResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [crossValidation, setCrossValidation] = useState<CrossValidationResult | null>(null)
  const [crossValidating, setCrossValidating] = useState(false)

  // Fetch samples on mount only if API is connected
  useEffect(() => {
    if (apiConnected) {
      fetchSamples()
    }
  }, [fetchSamples, apiConnected])

  // Filter samples by type from API
  const apiFcsSamples = apiSamples.filter(s => s.files?.fcs)
  const apiNtaSamples = apiSamples.filter(s => s.files?.nta)

  // Create virtual samples from current analysis if available
  const currentFcsSample = fcsAnalysis.results ? {
    id: -1,
    sample_id: fcsAnalysis.sampleId || "Current FCS Analysis",
    files: { fcs: "current" }
  } : null

  const currentNtaSample = ntaAnalysis.results ? {
    id: -2,
    sample_id: ntaAnalysis.sampleId || "Current NTA Analysis", 
    files: { nta: "current" }
  } : null

  // Combine API samples with current analysis
  const fcsSamples = [
    ...(currentFcsSample ? [currentFcsSample] : []),
    ...apiFcsSamples
  ]
  const ntaSamples = [
    ...(currentNtaSample ? [currentNtaSample] : []),
    ...apiNtaSamples
  ]

  // Fetch results for selected samples
  const fetchResults = useCallback(async () => {
    if (!selectedFcsSample && !selectedNtaSample) return

    setLoading(true)
    setError(null)

    try {
      const promises: Promise<void>[] = []
      
      // Handle FCS selection
      if (selectedFcsSample) {
        if (selectedFcsSample === "-1" && fcsAnalysis.results) {
          // Use current FCS analysis
          setFcsResults(fcsAnalysis.results)
        } else {
          promises.push(
            apiClient.getFCSResults(selectedFcsSample).then(res => {
              if (res.results?.[0]) setFcsResults(res.results[0])
            })
          )
        }
      }
      
      // Handle NTA selection
      if (selectedNtaSample) {
        if (selectedNtaSample === "-2" && ntaAnalysis.results) {
          // Use current NTA analysis
          setNtaResults(ntaAnalysis.results)
        } else {
          promises.push(
            apiClient.getNTAResults(selectedNtaSample).then(res => {
              if (res.results?.[0]) setNtaResults(res.results[0])
            })
          )
        }
      }

      await Promise.all(promises)
    } catch (err) {
      setError("Failed to fetch comparison data")
    } finally {
      setLoading(false)
    }
  }, [selectedFcsSample, selectedNtaSample, fcsAnalysis.results, ntaAnalysis.results])

  // Auto-fetch when samples are selected
  useEffect(() => {
    if (selectedFcsSample || selectedNtaSample) {
      fetchResults()
    }
  }, [selectedFcsSample, selectedNtaSample, fetchResults])

  // Auto-select current analysis when available
  useEffect(() => {
    if (fcsAnalysis.results && !selectedFcsSample) {
      setSelectedFcsSample("-1")
      setFcsResults(fcsAnalysis.results)
    }
  }, [fcsAnalysis.results, selectedFcsSample])

  useEffect(() => {
    if (ntaAnalysis.results && !selectedNtaSample) {
      setSelectedNtaSample("-2")
      setNtaResults(ntaAnalysis.results)
    }
  }, [ntaAnalysis.results, selectedNtaSample])

  // Run cross-validation when both API samples are selected (not current analysis)
  const runCrossValidation = useCallback(async () => {
    // Cross-validation requires real sample IDs (not current analysis)
    const fcsId = selectedFcsSample && selectedFcsSample !== "-1" 
      ? fcsSamples.find(s => String(s.id) === selectedFcsSample)?.sample_id 
      : fcsAnalysis.sampleId
    const ntaId = selectedNtaSample && selectedNtaSample !== "-2"
      ? ntaSamples.find(s => String(s.id) === selectedNtaSample)?.sample_id
      : ntaAnalysis.sampleId

    if (!fcsId || !ntaId) {
      toast({
        title: "Cannot Cross-Validate",
        description: "Both FCS and NTA samples must be selected",
        variant: "destructive",
      })
      return
    }

    setCrossValidating(true)
    try {
      const result = await apiClient.crossValidate(fcsId, ntaId)
      setCrossValidation(result)
      toast({
        title: `Cross-Validation: ${result.comparison.verdict}`,
        description: `D50 difference: ${result.comparison.d50_difference_pct.toFixed(1)}% — ${result.comparison.verdict_detail}`,
      })
    } catch (err) {
      console.error("Cross-validation failed:", err)
      toast({
        title: "Cross-Validation Failed",
        description: err instanceof Error ? err.message : "Failed to run cross-validation",
        variant: "destructive",
      })
    } finally {
      setCrossValidating(false)
    }
  }, [selectedFcsSample, selectedNtaSample, fcsSamples, ntaSamples, fcsAnalysis.sampleId, ntaAnalysis.sampleId, toast])

  const handlePin = (chartTitle: string, chartType: "histogram" | "bar" | "line") => {
    pinChart({
      id: crypto.randomUUID(),
      title: chartTitle,
      source: "Cross-Compare",
      timestamp: new Date(),
      type: chartType,
      data: null,
    })
    toast({
      title: "Pinned to Dashboard",
      description: `${chartTitle} has been pinned.`,
    })
  }

  // Export comparison report
  const handleExport = async (format: string) => {
    const timestamp = new Date().toISOString().split('T')[0]
    const fcsSampleName = selectedFcsSample || 'FCS_Sample'
    const ntaSampleName = selectedNtaSample || 'NTA_Sample'
    
    // Calculate comparison data
    const comparisonData = {
      fcs: {
        sampleId: fcsSampleName,
        totalEvents: fcsResults?.total_events,
        d10: fcsResults?.size_statistics?.d10 || fcsStats.d10,
        d50: fcsResults?.size_statistics?.d50 || fcsStats.d50,
        d90: fcsResults?.size_statistics?.d90 || fcsStats.d90,
        mean: fcsResults?.size_statistics?.mean || fcsStats.mean,
        std: fcsResults?.size_statistics?.std || fcsStats.std,
        fscMean: fcsResults?.fsc_mean,
        sscMean: fcsResults?.ssc_mean,
      },
      nta: {
        sampleId: ntaSampleName,
        totalParticles: ntaResults?.total_particles,
        d10: ntaResults?.d10_nm || ntaStats.d10,
        d50: ntaResults?.d50_nm || ntaStats.d50,
        d90: ntaResults?.d90_nm || ntaStats.d90,
        mean: ntaResults?.mean_size_nm || ntaStats.mean,
        concentration: ntaResults?.concentration_particles_ml,
        temperature: ntaResults?.temperature_celsius,
      },
    }
    
    try {
      switch (format) {
        case "CSV": {
          const csvContent = [
            "# Cross-Compare Analysis Report",
            `# Export Date: ${new Date().toISOString()}`,
            `# FCS Sample: ${fcsSampleName}`,
            `# NTA Sample: ${ntaSampleName}`,
            "#",
            "Metric,FCS Value,NTA Value,Difference,% Difference",
            `D10 (nm),${comparisonData.fcs.d10?.toFixed(2) || 'N/A'},${comparisonData.nta.d10?.toFixed(2) || 'N/A'},${(comparisonData.nta.d10 && comparisonData.fcs.d10) ? (comparisonData.nta.d10 - comparisonData.fcs.d10).toFixed(2) : 'N/A'},${(comparisonData.nta.d10 && comparisonData.fcs.d10) ? ((comparisonData.nta.d10 - comparisonData.fcs.d10) / comparisonData.fcs.d10 * 100).toFixed(2) + '%' : 'N/A'}`,
            `D50 (nm),${comparisonData.fcs.d50?.toFixed(2) || 'N/A'},${comparisonData.nta.d50?.toFixed(2) || 'N/A'},${(comparisonData.nta.d50 && comparisonData.fcs.d50) ? (comparisonData.nta.d50 - comparisonData.fcs.d50).toFixed(2) : 'N/A'},${(comparisonData.nta.d50 && comparisonData.fcs.d50) ? ((comparisonData.nta.d50 - comparisonData.fcs.d50) / comparisonData.fcs.d50 * 100).toFixed(2) + '%' : 'N/A'}`,
            `D90 (nm),${comparisonData.fcs.d90?.toFixed(2) || 'N/A'},${comparisonData.nta.d90?.toFixed(2) || 'N/A'},${(comparisonData.nta.d90 && comparisonData.fcs.d90) ? (comparisonData.nta.d90 - comparisonData.fcs.d90).toFixed(2) : 'N/A'},${(comparisonData.nta.d90 && comparisonData.fcs.d90) ? ((comparisonData.nta.d90 - comparisonData.fcs.d90) / comparisonData.fcs.d90 * 100).toFixed(2) + '%' : 'N/A'}`,
            `Mean (nm),${comparisonData.fcs.mean?.toFixed(2) || 'N/A'},${comparisonData.nta.mean?.toFixed(2) || 'N/A'},${(comparisonData.nta.mean && comparisonData.fcs.mean) ? (comparisonData.nta.mean - comparisonData.fcs.mean).toFixed(2) : 'N/A'},${(comparisonData.nta.mean && comparisonData.fcs.mean) ? ((comparisonData.nta.mean - comparisonData.fcs.mean) / comparisonData.fcs.mean * 100).toFixed(2) + '%' : 'N/A'}`,
          ].join('\n')
          
          const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
          const url = URL.createObjectURL(blob)
          const link = document.createElement('a')
          link.href = url
          link.download = `CrossCompare_${fcsSampleName}_vs_${ntaSampleName}_${timestamp}.csv`
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
          URL.revokeObjectURL(url)
          
          toast({
            title: "✅ Export Complete",
            description: "CSV comparison report downloaded successfully",
          })
          break
        }
        
        case "Excel": {
          const workbook = XLSX.utils.book_new()
          
          // Summary Sheet
          const summaryData = [
            ['BioVaram EV Analysis Platform - Cross-Compare Report'],
            [''],
            ['Export Date', new Date().toLocaleString()],
            ['FCS Sample', fcsSampleName],
            ['NTA Sample', ntaSampleName],
            [''],
            ['Size Comparison'],
            ['Metric', 'FCS', 'NTA', 'Difference', '% Difference'],
            ['D10 (nm)', comparisonData.fcs.d10?.toFixed(2) || 'N/A', comparisonData.nta.d10?.toFixed(2) || 'N/A', 
              (comparisonData.nta.d10 && comparisonData.fcs.d10) ? (comparisonData.nta.d10 - comparisonData.fcs.d10).toFixed(2) : 'N/A',
              (comparisonData.nta.d10 && comparisonData.fcs.d10) ? ((comparisonData.nta.d10 - comparisonData.fcs.d10) / comparisonData.fcs.d10 * 100).toFixed(2) + '%' : 'N/A'],
            ['D50 (nm)', comparisonData.fcs.d50?.toFixed(2) || 'N/A', comparisonData.nta.d50?.toFixed(2) || 'N/A',
              (comparisonData.nta.d50 && comparisonData.fcs.d50) ? (comparisonData.nta.d50 - comparisonData.fcs.d50).toFixed(2) : 'N/A',
              (comparisonData.nta.d50 && comparisonData.fcs.d50) ? ((comparisonData.nta.d50 - comparisonData.fcs.d50) / comparisonData.fcs.d50 * 100).toFixed(2) + '%' : 'N/A'],
            ['D90 (nm)', comparisonData.fcs.d90?.toFixed(2) || 'N/A', comparisonData.nta.d90?.toFixed(2) || 'N/A',
              (comparisonData.nta.d90 && comparisonData.fcs.d90) ? (comparisonData.nta.d90 - comparisonData.fcs.d90).toFixed(2) : 'N/A',
              (comparisonData.nta.d90 && comparisonData.fcs.d90) ? ((comparisonData.nta.d90 - comparisonData.fcs.d90) / comparisonData.fcs.d90 * 100).toFixed(2) + '%' : 'N/A'],
            ['Mean (nm)', comparisonData.fcs.mean?.toFixed(2) || 'N/A', comparisonData.nta.mean?.toFixed(2) || 'N/A',
              (comparisonData.nta.mean && comparisonData.fcs.mean) ? (comparisonData.nta.mean - comparisonData.fcs.mean).toFixed(2) : 'N/A',
              (comparisonData.nta.mean && comparisonData.fcs.mean) ? ((comparisonData.nta.mean - comparisonData.fcs.mean) / comparisonData.fcs.mean * 100).toFixed(2) + '%' : 'N/A'],
            [''],
            ['FCS Details'],
            ['Total Events', String(comparisonData.fcs.totalEvents || 'N/A')],
            ['FSC Mean', comparisonData.fcs.fscMean?.toFixed(2) || 'N/A'],
            ['SSC Mean', comparisonData.fcs.sscMean?.toFixed(2) || 'N/A'],
            [''],
            ['NTA Details'],
            ['Total Particles', String(comparisonData.nta.totalParticles || 'N/A')],
            ['Concentration (p/mL)', comparisonData.nta.concentration?.toExponential(2) || 'N/A'],
            ['Temperature (°C)', comparisonData.nta.temperature?.toFixed(1) || 'N/A'],
          ]
          
          const summarySheet = XLSX.utils.aoa_to_sheet(summaryData)
          summarySheet['!cols'] = [{ wch: 20 }, { wch: 15 }, { wch: 15 }, { wch: 15 }, { wch: 15 }]
          XLSX.utils.book_append_sheet(workbook, summarySheet, 'Comparison')
          
          XLSX.writeFile(workbook, `CrossCompare_${fcsSampleName}_vs_${ntaSampleName}_${timestamp}.xlsx`)
          
          toast({
            title: "✅ Excel Export Complete",
            description: "Excel comparison report downloaded successfully",
          })
          break
        }
        
        case "JSON": {
          const jsonContent = JSON.stringify({
            export_timestamp: new Date().toISOString(),
            platform: "BioVaram EV Analysis Platform",
            comparison_type: "FCS vs NTA",
            fcs_sample: {
              sample_id: fcsSampleName,
              total_events: comparisonData.fcs.totalEvents,
              size_statistics: {
                d10: comparisonData.fcs.d10,
                d50: comparisonData.fcs.d50,
                d90: comparisonData.fcs.d90,
                mean: comparisonData.fcs.mean,
                std: comparisonData.fcs.std,
              },
              scatter_statistics: {
                fsc_mean: comparisonData.fcs.fscMean,
                ssc_mean: comparisonData.fcs.sscMean,
              },
            },
            nta_sample: {
              sample_id: ntaSampleName,
              total_particles: comparisonData.nta.totalParticles,
              size_statistics: {
                d10: comparisonData.nta.d10,
                d50: comparisonData.nta.d50,
                d90: comparisonData.nta.d90,
                mean: comparisonData.nta.mean,
              },
              concentration_particles_ml: comparisonData.nta.concentration,
              temperature_celsius: comparisonData.nta.temperature,
            },
            size_comparison: {
              d10_difference_nm: (comparisonData.nta.d10 && comparisonData.fcs.d10) ? comparisonData.nta.d10 - comparisonData.fcs.d10 : null,
              d50_difference_nm: (comparisonData.nta.d50 && comparisonData.fcs.d50) ? comparisonData.nta.d50 - comparisonData.fcs.d50 : null,
              d90_difference_nm: (comparisonData.nta.d90 && comparisonData.fcs.d90) ? comparisonData.nta.d90 - comparisonData.fcs.d90 : null,
              mean_difference_nm: (comparisonData.nta.mean && comparisonData.fcs.mean) ? comparisonData.nta.mean - comparisonData.fcs.mean : null,
            },
          }, null, 2)
          
          const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' })
          const url = URL.createObjectURL(blob)
          const link = document.createElement('a')
          link.href = url
          link.download = `CrossCompare_${fcsSampleName}_vs_${ntaSampleName}_${timestamp}.json`
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
          URL.revokeObjectURL(url)
          
          toast({
            title: "✅ JSON Export Complete",
            description: "JSON comparison report downloaded successfully",
          })
          break
        }
        
        case "PDF": {
          toast({
            title: "Generating PDF...",
            description: "Please wait while we create your report",
          })
          
          const { default: jsPDF } = await import('jspdf')
          const { default: autoTable } = await import('jspdf-autotable')
          
          const doc = new jsPDF()
          const pageWidth = doc.internal.pageSize.getWidth()
          
          // Header
          doc.setFontSize(20)
          doc.setTextColor(139, 92, 246)
          doc.text('BioVaram', 14, 20)
          
          doc.setFontSize(12)
          doc.setTextColor(100)
          doc.text('Cross-Compare Analysis Report', 14, 28)
          
          doc.setDrawColor(139, 92, 246)
          doc.setLineWidth(0.5)
          doc.line(14, 32, pageWidth - 14, 32)
          
          // Sample Information
          doc.setFontSize(14)
          doc.setTextColor(0)
          doc.text('Samples Compared', 14, 42)
          
          autoTable(doc, {
            startY: 46,
            head: [['Method', 'Sample ID']],
            body: [
              ['FCS (Flow Cytometry)', fcsSampleName],
              ['NTA (Nanoparticle Tracking)', ntaSampleName],
            ],
            theme: 'striped',
            headStyles: { fillColor: [139, 92, 246] },
            margin: { left: 14, right: 14 },
          })
          
          // Size Comparison
          const sizeStartY = (doc as any).lastAutoTable.finalY + 10
          doc.setFontSize(14)
          doc.text('Size Statistics Comparison', 14, sizeStartY)
          
          autoTable(doc, {
            startY: sizeStartY + 4,
            head: [['Metric', 'FCS', 'NTA', 'Difference']],
            body: [
              ['D10 (nm)', comparisonData.fcs.d10?.toFixed(2) || 'N/A', comparisonData.nta.d10?.toFixed(2) || 'N/A',
                (comparisonData.nta.d10 && comparisonData.fcs.d10) ? (comparisonData.nta.d10 - comparisonData.fcs.d10).toFixed(2) : 'N/A'],
              ['D50 (nm)', comparisonData.fcs.d50?.toFixed(2) || 'N/A', comparisonData.nta.d50?.toFixed(2) || 'N/A',
                (comparisonData.nta.d50 && comparisonData.fcs.d50) ? (comparisonData.nta.d50 - comparisonData.fcs.d50).toFixed(2) : 'N/A'],
              ['D90 (nm)', comparisonData.fcs.d90?.toFixed(2) || 'N/A', comparisonData.nta.d90?.toFixed(2) || 'N/A',
                (comparisonData.nta.d90 && comparisonData.fcs.d90) ? (comparisonData.nta.d90 - comparisonData.fcs.d90).toFixed(2) : 'N/A'],
              ['Mean (nm)', comparisonData.fcs.mean?.toFixed(2) || 'N/A', comparisonData.nta.mean?.toFixed(2) || 'N/A',
                (comparisonData.nta.mean && comparisonData.fcs.mean) ? (comparisonData.nta.mean - comparisonData.fcs.mean).toFixed(2) : 'N/A'],
            ],
            theme: 'striped',
            headStyles: { fillColor: [139, 92, 246] },
            margin: { left: 14, right: 14 },
          })
          
          // Footer
          const pageCount = doc.getNumberOfPages()
          for (let i = 1; i <= pageCount; i++) {
            doc.setPage(i)
            doc.setFontSize(8)
            doc.setTextColor(150)
            doc.text(
              `Page ${i} of ${pageCount} | Generated by BioVaram EV Analysis Platform | ${new Date().toLocaleString()}`,
              pageWidth / 2,
              doc.internal.pageSize.getHeight() - 10,
              { align: 'center' }
            )
          }
          
          doc.save(`CrossCompare_${fcsSampleName}_vs_${ntaSampleName}_${timestamp}.pdf`)
          
          toast({
            title: "✅ PDF Export Complete",
            description: "PDF comparison report downloaded successfully",
          })
          break
        }
        
        default:
          toast({
            title: "Export Not Available",
            description: `${format} export is not supported`,
            variant: "destructive",
          })
      }
    } catch (error) {
      toast({
        title: "Export Failed",
        description: error instanceof Error ? error.message : "Failed to export comparison report",
        variant: "destructive",
      })
    }
  }

  // Calculate stats from cross-validation results (preferred) or individual results
  const fcsStats = crossValidation ? {
    d10: crossValidation.fcs_statistics.d10,
    d50: crossValidation.fcs_statistics.d50,
    d90: crossValidation.fcs_statistics.d90,
    mean: crossValidation.fcs_statistics.mean,
    std: crossValidation.fcs_statistics.std,
    n: crossValidation.data_summary.fcs_valid_sizes,
  } : fcsResults ? {
    d10: fcsResults.size_statistics?.d10 || 0,
    d50: fcsResults.size_statistics?.d50 || fcsResults.particle_size_median_nm || 0,
    d90: fcsResults.size_statistics?.d90 || 0,
    mean: fcsResults.size_statistics?.mean || 0,
    std: fcsResults.size_statistics?.std || 0,
    n: fcsResults.total_events || 0,
  } : { d10: 0, d50: 0, d90: 0, mean: 0, std: 0, n: 0 }

  const ntaStats = crossValidation ? {
    d10: crossValidation.nta_statistics.d10,
    d50: crossValidation.nta_statistics.d50,
    d90: crossValidation.nta_statistics.d90,
    mean: crossValidation.nta_statistics.mean,
    std: crossValidation.nta_statistics.std,
    n: crossValidation.nta_statistics.count,
  } : ntaResults ? {
    d10: ntaResults.d10_nm || ntaResults.size_statistics?.d10 || 0,
    d50: ntaResults.median_size_nm || ntaResults.d50_nm || ntaResults.size_statistics?.d50 || 0,
    d90: ntaResults.d90_nm || ntaResults.size_statistics?.d90 || 0,
    mean: ntaResults.mean_size_nm || ntaResults.size_statistics?.mean || 0,
    std: ntaResults.size_statistics?.std || 0,
    n: ntaResults.total_particles || 0,
  } : { d10: 0, d50: 0, d90: 0, mean: 0, std: 0, n: 0 }

  // Calculate discrepancy - focused on D50 (Median) per client preference (Surya, Dec 3, 2025)
  // "Mean is basically not the real metric... median is something that really existed in the data set"
  const calculateDiscrepancy = (fcs: number, nta: number) => {
    if (fcs === 0 && nta === 0) return 0
    return Math.abs((nta - fcs) / ((nta + fcs) / 2)) * 100
  }

  // Average discrepancy now emphasizes D50 (Median) as the primary metric
  const avgDiscrepancy = (
    calculateDiscrepancy(fcsStats.d50, ntaStats.d50) * 2 +  // Weight D50 (Median) higher
    calculateDiscrepancy(fcsStats.d10, ntaStats.d10) +
    calculateDiscrepancy(fcsStats.d90, ntaStats.d90)
  ) / 4

  const hasData = fcsResults || ntaResults || fcsAnalysis.results || ntaAnalysis.results

  const handleResetTab = () => {
    setSelectedFcsSample("")
    setSelectedNtaSample("")
    setFcsResults(null)
    setNtaResults(null)
    setCrossValidation(null)
    setLoading(false)
    setError(null)
    setCrossValidating(false)
    toast({
      title: "Cross-Compare Reset",
      description: "All sample selections and comparison data have been cleared.",
    })
  }

  return (
    <div className="p-4 md:p-6 space-y-4 md:space-y-6">
      {/* Header with Reset Button */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <GitCompare className="h-6 w-6 text-primary" />
            Cross-Compare Analysis
          </h2>
          <p className="text-sm text-muted-foreground">Compare FCS and NTA size distributions side by side</p>
        </div>
        <Button variant="outline" size="sm" onClick={handleResetTab} className="gap-2">
          <RotateCcw className="h-4 w-4" />
          Reset Tab
        </Button>
      </div>

      {/* Sample Selection Card */}
      <Card className="card-3d">
        <CardHeader className="pb-3">
          <CardTitle className="text-base md:text-lg flex items-center gap-2">
            <GitCompare className="h-5 w-5 text-primary" />
            Select Samples to Compare
          </CardTitle>
          <CardDescription>
            Choose FCS and NTA samples to cross-compare their size distributions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">FCS Sample</label>
              <Select value={selectedFcsSample} onValueChange={setSelectedFcsSample}>
                <SelectTrigger>
                  <SelectValue placeholder="Select FCS sample..." />
                </SelectTrigger>
                <SelectContent>
                  {fcsSamples.length === 0 ? (
                    <SelectItem value="none" disabled>No FCS samples available</SelectItem>
                  ) : (
                    fcsSamples.map(sample => (
                      <SelectItem key={sample.id} value={String(sample.id)}>
                        {sample.sample_id}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">NTA Sample</label>
              <Select value={selectedNtaSample} onValueChange={setSelectedNtaSample}>
                <SelectTrigger>
                  <SelectValue placeholder="Select NTA sample..." />
                </SelectTrigger>
                <SelectContent>
                  {ntaSamples.length === 0 ? (
                    <SelectItem value="none" disabled>No NTA samples available</SelectItem>
                  ) : (
                    ntaSamples.map(sample => (
                      <SelectItem key={sample.id} value={String(sample.id)}>
                        {sample.sample_id}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>
          </div>
          {loading && (
            <div className="flex items-center justify-center mt-4 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              <span className="text-sm">Loading comparison data...</span>
            </div>
          )}
          {error && (
            <div className="flex items-center justify-center mt-4 text-destructive">
              <AlertCircle className="h-4 w-4 mr-2" />
              <span className="text-sm">{error}</span>
              <Button variant="ghost" size="sm" onClick={fetchResults} className="ml-2">
                <RefreshCw className="h-3 w-3" />
              </Button>
            </div>
          )}
          {/* Cross-Validation Button */}
          {(selectedFcsSample || fcsAnalysis.results) && (selectedNtaSample || ntaAnalysis.results) && (
            <div className="mt-4 flex items-center gap-3">
              <Button
                onClick={runCrossValidation}
                disabled={crossValidating}
                className="gap-2"
              >
                {crossValidating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Running Cross-Validation...
                  </>
                ) : (
                  <>
                    <GitCompare className="h-4 w-4" />
                    Run Cross-Validation
                  </>
                )}
              </Button>
              <span className="text-xs text-muted-foreground">
                Computes aligned histograms, D50 comparison, and statistical tests
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* VAL-001: Validation Verdict Card */}
      {crossValidation && (
        <ValidationVerdictCard result={crossValidation} />
      )}

      {/* Method Comparison Summary */}
      {hasData && (
        <MethodComparisonSummary 
          fcsResults={fcsResults} 
          ntaResults={ntaResults} 
        />
      )}

      <Card className="card-3d">
        <CardHeader className="pb-2">
          <CardTitle className="text-base md:text-lg">Comparison Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="overlay" className="space-y-4">
            <TabsList className="bg-secondary/50 w-full justify-start overflow-x-auto flex-nowrap">
              <TabsTrigger value="overlay" className="shrink-0">
                Overlay
              </TabsTrigger>
              <TabsTrigger value="kde" className="shrink-0">
                KDE
              </TabsTrigger>
              <TabsTrigger value="correlation" className="shrink-0">
                Correlation
              </TabsTrigger>
              <TabsTrigger value="statistics" className="shrink-0">
                Statistics
              </TabsTrigger>
              <TabsTrigger value="discrepancy" className="shrink-0">
                Discrepancy
              </TabsTrigger>
            </TabsList>

            <TabsContent value="overlay" className="space-y-4">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge className="bg-primary/80">FCS: {fcsStats.n.toLocaleString()} events</Badge>
                  <Badge className="bg-purple/80">NTA: {ntaStats.n.toLocaleString()} particles</Badge>
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Maximize2 className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => handlePin("Overlay Histogram", "histogram")}
                  >
                    <Pin className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              {hasData || crossValidation ? (
                <OverlayHistogramChart 
                  fcsData={fcsResults?.size_distribution || fcsAnalysis.results?.size_distribution}
                  ntaData={ntaResults?.size_distribution || ntaAnalysis.results?.size_distribution}
                  crossValidationData={crossValidation?.distribution}
                />
              ) : (
                <div className="p-8 text-center text-muted-foreground border rounded-lg bg-secondary/20">
                  <p>Select FCS and NTA samples above to view the overlay comparison</p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="kde" className="space-y-4">
              <KDEComparisonChart
                fcsData={fcsResults?.size_distribution || fcsAnalysis.results?.size_distribution}
                ntaData={ntaResults?.size_distribution || ntaAnalysis.results?.size_distribution}
              />
            </TabsContent>

            <TabsContent value="correlation" className="space-y-4">
              <div className="flex items-center justify-end gap-1">
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <Maximize2 className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => handlePin("Correlation Scatter", "line")}
                >
                  <Pin className="h-4 w-4" />
                </Button>
              </div>
              <CorrelationScatterChart
                fcsValues={[fcsStats.d10, fcsStats.d50, fcsStats.d90, fcsStats.mean, fcsStats.std]}
                ntaValues={[ntaStats.d10, ntaStats.d50, ntaStats.d90, ntaStats.mean, ntaStats.std]}
                metric="Size"
                title="FCS vs NTA Size Correlation"
              />
            </TabsContent>

            <TabsContent value="statistics" className="space-y-4">
              <StatisticalComparisonTable 
                fcsResults={fcsResults} 
                ntaResults={ntaResults} 
              />
              <StatisticalTestsCard
                fcsData={fcsResults?.size_distribution?.map((d: { size: number }) => d.size) || fcsAnalysis.results?.size_distribution?.map((d: { size: number }) => d.size)}
                ntaData={ntaResults?.size_distribution?.map((d: { size: number }) => d.size) || ntaAnalysis.results?.size_distribution?.map((d: { size: number }) => d.size)}
              />
            </TabsContent>

            <TabsContent value="discrepancy" className="space-y-4">
              <div className="flex items-center justify-end gap-1">
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <Maximize2 className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => handlePin("Discrepancy Analysis", "bar")}
                >
                  <Pin className="h-4 w-4" />
                </Button>
              </div>
              <DiscrepancyChart />

              <Card className="bg-secondary/30 shadow-inner">
                <CardContent className="p-4">
                  <p className="text-sm">
                    <span className="font-medium">Interpretation: </span>
                    <span className="text-muted-foreground">
                      {crossValidation
                        ? `D50 discrepancy: ${crossValidation.comparison.d50_difference_pct.toFixed(1)}% (${crossValidation.comparison.d50_difference_nm.toFixed(1)} nm). ${crossValidation.comparison.verdict_detail}. Mie method: ${crossValidation.mie_parameters.method}.`
                        : `The FCS and NTA measurements show ${avgDiscrepancy < 15 ? "good" : avgDiscrepancy < 25 ? "moderate" : "poor"} agreement. D50 discrepancy: ${calculateDiscrepancy(fcsStats.d50, ntaStats.d50).toFixed(1)}%. Run Cross-Validation for detailed statistical analysis.`
                      }
                    </span>
                  </p>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Export Options */}
      {hasData && (
        <Card className="card-3d">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary/10">
                <Download className="h-4 w-4 text-primary" />
              </div>
              <CardTitle className="text-base">Export Comparison Report</CardTitle>
            </div>
            <CardDescription>
              Download comprehensive comparison analysis in various formats
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              <Button variant="outline" size="sm" onClick={() => handleExport("CSV")} className="w-full">
                CSV Data
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExport("Excel")} className="w-full">
                Excel Report
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExport("JSON")} className="w-full">
                JSON
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExport("PDF")} className="w-full">
                PDF Report
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
