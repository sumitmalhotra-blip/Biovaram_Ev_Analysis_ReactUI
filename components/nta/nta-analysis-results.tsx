"use client"

import { useState, useCallback, useMemo, useEffect } from "react"
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
  FileText,
  Layers,
  Upload,
  Loader2,
  RefreshCw,
  Eye,
  EyeOff,
  Star,
  MinusCircle
} from "lucide-react"
import { useAnalysisStore } from "@/lib/store"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { NTASizeDistributionChart } from "./charts/nta-size-distribution-chart"
import { ConcentrationProfileChart } from "./charts/concentration-profile-chart"
import { TemperatureCorrectedComparison } from "./charts/temperature-corrected-comparison"
import { EVSizeCategoryBarChart } from "./charts/ev-size-category-bar-chart"
import { NTAStatisticsCards } from "./statistics-cards"
import { NTASizeDistributionBreakdown } from "./size-distribution-breakdown"
import { SupplementaryMetadataTable } from "./supplementary-metadata-table"
import { NTAMetadataCompareTable } from "./nta-metadata-compare-table"
import { captureChartAsImage } from "@/components/dashboard/saved-images-gallery"
import { 
  generateMarkdownReport, 
  downloadMarkdownReport,
  exportToParquet,
  exportNTAToExcel,
  exportNTAToPDF,
  type NTAExportData
} from "@/lib/export-utils"
import type { NTAResult } from "@/lib/api-client"
import { useToast } from "@/hooks/use-toast"
import { NTA_LOCKED_QUALITY_PROFILE_ID } from "@/lib/store"
import { useApi } from "@/hooks/use-api"

interface NTAAnalysisResultsProps {
  results: NTAResult
  sampleId?: string
  fileName?: string
}

export function NTAAnalysisResults({ results, sampleId, fileName }: NTAAnalysisResultsProps) {
  const {
    pinChart,
    resetNTAAnalysis,
    apiSamples,
    ntaCompareSession,
    setNTACompareSelectedSampleIds,
    setNTACompareVisibleSampleIds,
    toggleNTACompareSampleVisibility,
    setNTAComparePrimarySampleId,
    setNTACompareSampleResult,
    setNTACompareMaxVisibleOverlays,
    clearNTACompareComputedSeriesCache,
    clearNTACompareSession,
    ntaAnalysisSettings,
    ntaSizeProfiles,
    selectedNTAAnalysisProfileId,
    ntaLockedBuckets,
  } = useAnalysisStore()
  const { toast } = useToast()
  const { loadNTACompareSamples, fetchSamples } = useApi()
  const [activeTab, setActiveTab] = useState("distribution")
  const [compareUploadLoading, setCompareUploadLoading] = useState(false)
  const [compareUploadProgress, setCompareUploadProgress] = useState<{ total: number; completed: number; failed: number } | null>(null)
  const [showHistoricalSamples, setShowHistoricalSamples] = useState(false)
  const [sessionSampleIds, setSessionSampleIds] = useState<string[]>(sampleId ? [sampleId] : [])
  const [clearedSeedSampleId, setClearedSeedSampleId] = useState<string | null>(null)
  const [debouncedOverlaySeries, setDebouncedOverlaySeries] = useState<Array<{
    sampleId: string
    label: string
    color: string
    visible: boolean
    isPrimary: boolean
    result: NTAResult
  }>>([])
  const [stagedVisibleSampleIds, setStagedVisibleSampleIds] = useState<string[]>([])
  const showTemperatureCorrection = !!ntaAnalysisSettings?.applyTemperatureCorrection
  const OVERLAY_COLORS = ["#8b5cf6", "#f97316", "#3b82f6", "#22c55e", "#ef4444", "#eab308", "#14b8a6", "#a855f7"]

  const analysisProfile = ntaSizeProfiles.find((p) => p.id === selectedNTAAnalysisProfileId) || ntaSizeProfiles[0]
  const qualityProfile = ntaSizeProfiles.find((p) => p.id === NTA_LOCKED_QUALITY_PROFILE_ID) || analysisProfile

  const availableNtaSamples = useMemo(
    () => apiSamples.filter((s) => s.files?.nta),
    [apiSamples]
  )

  const sessionSelectableSampleIds = useMemo(() => {
    const ids = [
      ...sessionSampleIds,
      ...ntaCompareSession.selectedSampleIds,
      ...ntaCompareSession.visibleSampleIds,
      ...Object.keys(ntaCompareSession.resultsBySampleId),
      ...(sampleId ? [sampleId] : []),
    ]
    return Array.from(new Set(ids)).filter(Boolean).slice(0, 50)
  }, [
    sampleId,
    sessionSampleIds,
    ntaCompareSession.selectedSampleIds,
    ntaCompareSession.visibleSampleIds,
    ntaCompareSession.resultsBySampleId,
  ])

  const selectableSampleIds = useMemo(() => {
    if (!showHistoricalSamples) {
      return sessionSelectableSampleIds
    }

    const historical = availableNtaSamples.map((s) => s.sample_id)
    return Array.from(new Set([...sessionSelectableSampleIds, ...historical])).slice(0, 200)
  }, [availableNtaSamples, sessionSelectableSampleIds, showHistoricalSamples])

  useEffect(() => {
    if (!sampleId) return
    setSessionSampleIds((prev) => (prev.includes(sampleId) ? prev : [sampleId, ...prev].slice(0, 50)))
  }, [sampleId])

  const sampleLabelById = useMemo(() => {
    const map: Record<string, string> = {}
    availableNtaSamples.forEach((sample) => {
      map[sample.sample_id] = sample.sample_id
    })
    if (sampleId) {
      map[sampleId] = sampleId
    }
    return map
  }, [availableNtaSamples, sampleId])

  const selectedSampleIds = ntaCompareSession.selectedSampleIds
  const visibleSampleIds = ntaCompareSession.visibleSampleIds
  const primarySampleId = ntaCompareSession.primarySampleId || sampleId || null
  const compareResultForCurrentSample = sampleId ? ntaCompareSession.resultsBySampleId[sampleId] : undefined

  useEffect(() => {
    if (ntaCompareSession.maxVisibleOverlays < 8) {
      setNTACompareMaxVisibleOverlays(8)
    }
  }, [ntaCompareSession.maxVisibleOverlays, setNTACompareMaxVisibleOverlays])

  useEffect(() => {
    if (!sampleId) return

    const shouldSkipAutoSeed =
      selectedSampleIds.length === 0 &&
      visibleSampleIds.length === 0 &&
      clearedSeedSampleId === sampleId

    if (shouldSkipAutoSeed) {
      return
    }

    const updates: Array<() => void> = []

    if (!selectedSampleIds.includes(sampleId)) {
      updates.push(() => {
        const nextSelected = [sampleId, ...selectedSampleIds.filter((id) => id !== sampleId)].slice(0, 20)
        setNTACompareSelectedSampleIds(nextSelected)
      })
    }

    if (!visibleSampleIds.includes(sampleId)) {
      updates.push(() => {
        const nextVisible = [sampleId, ...visibleSampleIds.filter((id) => id !== sampleId)]
          .slice(0, ntaCompareSession.maxVisibleOverlays)
        setNTACompareVisibleSampleIds(nextVisible)
      })
    }

    if (!ntaCompareSession.primarySampleId) {
      updates.push(() => setNTAComparePrimarySampleId(sampleId))
    }

    const currentId = compareResultForCurrentSample?.id
    const incomingId = results?.id
    const shouldSyncResult = !compareResultForCurrentSample || currentId !== incomingId
    if (shouldSyncResult) {
      updates.push(() => setNTACompareSampleResult(sampleId, results))
    }

    updates.forEach((applyUpdate) => applyUpdate())
  }, [
    sampleId,
    results,
    compareResultForCurrentSample,
    selectedSampleIds,
    visibleSampleIds,
    clearedSeedSampleId,
    ntaCompareSession.maxVisibleOverlays,
    ntaCompareSession.primarySampleId,
    setNTACompareMaxVisibleOverlays,
    setNTAComparePrimarySampleId,
    setNTACompareSampleResult,
    setNTACompareSelectedSampleIds,
    setNTACompareVisibleSampleIds,
  ])

  const applySelectedSamples = useCallback(async (nextSelected: string[]) => {
    const normalized = Array.from(new Set(nextSelected)).slice(0, 20)
    setNTACompareSelectedSampleIds(normalized)
    setSessionSampleIds((prev) => Array.from(new Set([...prev, ...normalized])).slice(0, 50))
    setClearedSeedSampleId(null)

    const toFetch = normalized.filter((id) => id !== sampleId)
    if (toFetch.length > 0) {
      await loadNTACompareSamples(toFetch)
    }
  }, [loadNTACompareSamples, sampleId, setNTACompareSelectedSampleIds])

  const handleSampleSelection = useCallback((sampleIdentifier: string, checked: boolean) => {
    const nextSelected = checked
      ? [...selectedSampleIds, sampleIdentifier]
      : selectedSampleIds.filter((id) => id !== sampleIdentifier)

    applySelectedSamples(nextSelected)
  }, [applySelectedSamples, selectedSampleIds])

  const handleRemoveSelectedSample = useCallback((sampleIdentifier: string) => {
    const nextSelected = selectedSampleIds.filter((id) => id !== sampleIdentifier)
    const nextVisible = visibleSampleIds.filter((id) => id !== sampleIdentifier)
    setNTACompareVisibleSampleIds(nextVisible)

    if (primarySampleId === sampleIdentifier) {
      setNTAComparePrimarySampleId(nextSelected[0] || null)
    }

    applySelectedSamples(nextSelected)
  }, [
    applySelectedSamples,
    primarySampleId,
    selectedSampleIds,
    setNTAComparePrimarySampleId,
    setNTACompareVisibleSampleIds,
    visibleSampleIds,
  ])

  const handleComparisonUploads = useCallback(async (filesInput: FileList | File[]) => {
    const files = Array.from(filesInput)
    if (files.length === 0) return

    setCompareUploadLoading(true)
    setCompareUploadProgress({ total: files.length, completed: 0, failed: 0 })

    try {
      const { apiClient } = await import("@/lib/api-client")
      const selectedSet = new Set(selectedSampleIds)
      const visibleSet = new Set(visibleSampleIds)
      const toFetch: string[] = []

      let completed = 0
      let failed = 0

      for (const file of files) {
        try {
          const response = await apiClient.uploadNTA(file)
          if (!response?.success) {
            throw new Error("Comparison upload failed")
          }

          const uploadedSampleId = response.sample_id || file.name
          selectedSet.add(uploadedSampleId)
          visibleSet.add(uploadedSampleId)

          if (response.nta_results) {
            setNTACompareSampleResult(uploadedSampleId, response.nta_results)
          } else {
            toFetch.push(uploadedSampleId)
          }

          completed += 1
          setCompareUploadProgress({ total: files.length, completed, failed })
        } catch (error) {
          failed += 1
          setCompareUploadProgress({ total: files.length, completed, failed })
          toast({
            variant: "destructive",
            title: `Upload failed: ${file.name}`,
            description: error instanceof Error ? error.message : "Failed to upload comparison file",
          })
        }
      }

      const nextSelected = Array.from(selectedSet).slice(0, 20)
      const nextVisible = Array.from(visibleSet)
        .filter((id) => nextSelected.includes(id))
        .slice(0, ntaCompareSession.maxVisibleOverlays)

      setNTACompareSelectedSampleIds(nextSelected)
      setNTACompareVisibleSampleIds(nextVisible)
      setSessionSampleIds((prev) => Array.from(new Set([...prev, ...nextSelected])).slice(0, 50))
      setClearedSeedSampleId(null)

      if (!primarySampleId && nextSelected.length > 0) {
        setNTAComparePrimarySampleId(nextSelected[0])
      }

      if (toFetch.length > 0) {
        await loadNTACompareSamples(toFetch)
      }

      await fetchSamples()

      toast({
        title: "Comparison upload complete",
        description: `${completed} uploaded, ${failed} failed.`,
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to upload comparison file"
      toast({
        variant: "destructive",
        title: "Comparison upload failed",
        description: message,
      })
    } finally {
      setCompareUploadLoading(false)
      window.setTimeout(() => setCompareUploadProgress(null), 1800)
    }
  }, [
    fetchSamples,
    loadNTACompareSamples,
    ntaCompareSession.maxVisibleOverlays,
    primarySampleId,
    selectedSampleIds,
    setNTAComparePrimarySampleId,
    setNTACompareSampleResult,
    setNTACompareSelectedSampleIds,
    setNTACompareVisibleSampleIds,
    toast,
    visibleSampleIds,
  ])

  const handleClearCompareSession = useCallback(() => {
    clearNTACompareSession()
    setSessionSampleIds(sampleId ? [sampleId] : [])
    setClearedSeedSampleId(sampleId || null)
    setCompareUploadProgress(null)
  }, [clearNTACompareSession, sampleId])

  const overlaySeries = useMemo(() => {
    const visibleSet = new Set(visibleSampleIds)
    return selectedSampleIds
      .map((id, index) => {
        const resultForSample = id === sampleId ? results : ntaCompareSession.resultsBySampleId[id]
        if (!resultForSample) return null

        return {
          sampleId: id,
          label: sampleLabelById[id] || id,
          color: OVERLAY_COLORS[index % OVERLAY_COLORS.length],
          visible: visibleSet.has(id),
          isPrimary: id === primarySampleId,
          result: resultForSample,
        }
      })
      .filter((item): item is { sampleId: string; label: string; color: string; visible: boolean; isPrimary: boolean; result: NTAResult } => !!item)
  }, [selectedSampleIds, sampleId, results, ntaCompareSession.resultsBySampleId, visibleSampleIds, sampleLabelById, primarySampleId])

  // Debounce overlay-series updates to avoid expensive recomputation bursts.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedOverlaySeries(overlaySeries)
    }, 120)
    return () => window.clearTimeout(timer)
  }, [overlaySeries, analysisProfile?.id, ntaAnalysisSettings?.yAxisMode])

  // Progressive paint: render primary first, then stage remaining visible overlays.
  useEffect(() => {
    const visible = debouncedOverlaySeries.filter((series) => series.visible)
    if (visible.length === 0) {
      setStagedVisibleSampleIds([])
      return
    }

    const first = visible.find((series) => series.isPrimary) || visible[0]
    const queue = visible.filter((series) => series.sampleId !== first.sampleId)
    setStagedVisibleSampleIds([first.sampleId])

    const timers = queue.map((series, index) => window.setTimeout(() => {
      setStagedVisibleSampleIds((prev) => (prev.includes(series.sampleId) ? prev : [...prev, series.sampleId]))
    }, 90 * (index + 1)))

    return () => timers.forEach((timer) => window.clearTimeout(timer))
  }, [debouncedOverlaySeries])

  // Clear computed chart cache whenever profile/axis settings shift.
  useEffect(() => {
    clearNTACompareComputedSeriesCache()
  }, [analysisProfile?.id, ntaAnalysisSettings?.yAxisMode, clearNTACompareComputedSeriesCache])

  const stagedOverlaySeries = useMemo(() => {
    const stagedSet = new Set(stagedVisibleSampleIds)
    return debouncedOverlaySeries.map((series) => ({
      ...series,
      visible: series.visible && stagedSet.has(series.sampleId),
    }))
  }, [debouncedOverlaySeries, stagedVisibleSampleIds])

  const handlePin = (chartTitle: string, chartType: "histogram" | "bar" | "line") => {
    let pinData: Array<{ x: number; y: number; label?: string }> = []
    let pinConfig: { xAxisLabel?: string; yAxisLabel?: string; color?: string } = {}

    if (chartTitle === "NTA Size Distribution") {
      // Extract distribution data from NTA results
      if (results.size_distribution && Array.isArray(results.size_distribution) && results.size_distribution.length > 0) {
        pinData = results.size_distribution
          .filter((d: any) => d.size != null)
          .map((d: any) => ({ x: d.size, y: d.count ?? d.concentration ?? 0 }))
          .sort((a: { x: number }, b: { x: number }) => a.x - b.x)
      } else {
        // Reconstruct from bin percentages
        const bins = [
          { key: "bin_50_80nm_pct" as const, min: 50, max: 80, label: "50-80nm" },
          { key: "bin_80_100nm_pct" as const, min: 80, max: 100, label: "80-100nm" },
          { key: "bin_100_120nm_pct" as const, min: 100, max: 120, label: "100-120nm" },
          { key: "bin_120_150nm_pct" as const, min: 120, max: 150, label: "120-150nm" },
          { key: "bin_150_200nm_pct" as const, min: 150, max: 200, label: "150-200nm" },
          { key: "bin_200_plus_pct" as const, min: 200, max: 350, label: "200+nm" },
        ]
        const totalConc = results.concentration_particles_ml || 1e8
        bins.forEach(bin => {
          const pct = (results as any)[bin.key] as number | undefined
          if (pct != null && pct > 0) {
            const mid = Math.round((bin.min + bin.max) / 2)
            pinData.push({ x: mid, y: Math.round(pct / 100 * totalConc), label: bin.label })
          }
        })
      }
      pinConfig = { xAxisLabel: "Diameter (nm)", yAxisLabel: "Count", color: "#8b5cf6" }
    } else if (chartTitle === "Concentration Profile") {
      const bins = [
        { key: "bin_50_80nm_pct" as const, label: "50-80nm" },
        { key: "bin_80_100nm_pct" as const, label: "80-100nm" },
        { key: "bin_100_120nm_pct" as const, label: "100-120nm" },
        { key: "bin_120_150nm_pct" as const, label: "120-150nm" },
        { key: "bin_150_200nm_pct" as const, label: "150-200nm" },
        { key: "bin_200_plus_pct" as const, label: "200+nm" },
      ]
      const totalConc = results.concentration_particles_ml || 2.4e9
      pinData = bins.map((bin, i) => {
        const pct = (results as any)[bin.key] || 0
        return { x: i + 1, y: parseFloat(((pct / 100) * (totalConc / 1e9)).toFixed(2)), label: bin.label }
      })
      pinConfig = { xAxisLabel: "Size Range", yAxisLabel: "Conc (×10⁹ p/mL)", color: "#3b82f6" }
    }

    pinChart({
      id: crypto.randomUUID(),
      title: chartTitle,
      source: "NTA",
      timestamp: new Date(),
      type: chartType,
      data: pinData.length > 0 ? pinData : [],
      config: pinConfig,
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
          // NEW: Real Excel export using xlsx library (P-002)
          try {
            const exportData: NTAExportData = {
              sampleId: sampleName,
              fileName: fileName || undefined,
              results: {
                median_size_nm: results.median_size_nm,
                mean_size_nm: results.mean_size_nm,
                d10_nm: results.d10_nm,
                d50_nm: results.d50_nm,
                d90_nm: results.d90_nm,
                concentration_particles_ml: results.concentration_particles_ml,
                temperature_celsius: results.temperature_celsius,
                ph: results.ph,
                total_particles: results.total_particles,
                bin_50_80nm_pct: results.bin_50_80nm_pct,
                bin_80_100nm_pct: results.bin_80_100nm_pct,
                bin_100_120nm_pct: results.bin_100_120nm_pct,
                bin_120_150nm_pct: results.bin_120_150nm_pct,
                bin_150_200nm_pct: results.bin_150_200nm_pct,
                bin_200_plus_pct: results.bin_200_plus_pct,
              },
              sizeDistribution: (results as any).size_distribution?.map((d: any) => ({
                size: d.size || d.diameter,
                concentration: d.concentration || d.count
              })),
            }
            
            exportNTAToExcel(exportData)
            
            toast({
              title: "✅ Excel Export Complete",
              description: `${sampleName}_NTA_Report.xlsx downloaded successfully`,
            })
          } catch (error) {
            toast({
              title: "Export Failed",
              description: error instanceof Error ? error.message : "Failed to export Excel file",
              variant: "destructive",
            })
          }
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
          // NEW: Real PDF export using jsPDF (P-003)
          try {
            toast({
              title: "Generating PDF...",
              description: "Please wait while we create your report",
            })

            const reportChartPlan: Array<{
              selector: string
              title: string
              type: "histogram" | "bar" | "line"
              tab?: "distribution" | "concentration" | "corrected"
            }> = [
              { selector: '[data-report-chart="nta-size-categories"]', title: "EV Size Category Distribution", type: "bar" },
              { selector: '[data-report-chart="nta-distribution"]', title: "NTA Size Distribution", type: "histogram", tab: "distribution" },
              { selector: '[data-report-chart="nta-concentration"]', title: "Concentration Profile", type: "bar", tab: "concentration" },
              { selector: '[data-report-chart="nta-temperature-corrected"]', title: "Temperature Corrected Comparison", type: "line", tab: "corrected" },
            ]

            const reportCharts: NonNullable<NTAExportData["reportCharts"]> = []
            const previousTab = activeTab
            let currentTab = activeTab
            try {
              for (const chart of reportChartPlan) {
                if (chart.tab && currentTab !== chart.tab) {
                  setActiveTab(chart.tab)
                  await new Promise<void>((resolve) => {
                    window.setTimeout(() => resolve(), 150)
                  })
                  currentTab = chart.tab
                }

                const chartElement = document.querySelector(chart.selector) as HTMLElement | null
                if (!chartElement) {
                  continue
                }

                const captured = await captureChartAsImage(chartElement, chart.title, "NTA Analysis", chart.type)
                if (!captured) {
                  continue
                }

                reportCharts.push({
                  title: chart.title,
                  dataUrl: captured.dataUrl,
                  width: captured.metadata?.width,
                  height: captured.metadata?.height,
                })
              }
            } finally {
              if (currentTab !== previousTab) {
                setActiveTab(previousTab)
              }
            }
            
            const exportData: NTAExportData = {
              sampleId: sampleName,
              fileName: fileName || undefined,
              results: {
                median_size_nm: results.median_size_nm,
                mean_size_nm: results.mean_size_nm,
                d10_nm: results.d10_nm,
                d50_nm: results.d50_nm,
                d90_nm: results.d90_nm,
                concentration_particles_ml: results.concentration_particles_ml,
                temperature_celsius: results.temperature_celsius,
                ph: results.ph,
                total_particles: results.total_particles,
                bin_50_80nm_pct: results.bin_50_80nm_pct,
                bin_80_100nm_pct: results.bin_80_100nm_pct,
                bin_100_120nm_pct: results.bin_100_120nm_pct,
                bin_120_150nm_pct: results.bin_120_150nm_pct,
                bin_150_200nm_pct: results.bin_150_200nm_pct,
                bin_200_plus_pct: results.bin_200_plus_pct,
              },
              reportCharts,
            }
            
            await exportNTAToPDF(exportData)
            
            toast({
              title: "✅ PDF Export Complete",
              description: `${sampleName}_NTA_Report.pdf downloaded successfully`,
            })
          } catch (error) {
            toast({
              title: "Export Failed",
              description: error instanceof Error ? error.message : "Failed to export PDF file",
              variant: "destructive",
            })
          }
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

      {/* Size Distribution Breakdown and Bar Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <NTASizeDistributionBreakdown results={results} bins={analysisProfile?.bins || []} />
        {ntaLockedBuckets ? (
          <NTASizeDistributionBreakdown results={results} bins={ntaLockedBuckets} />
        ) : (
          <div data-report-chart="nta-size-categories">
            <EVSizeCategoryBarChart data={results} bins={qualityProfile?.bins || []} />
          </div>
        )}
      </div>

      {ntaLockedBuckets && (
        <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs text-muted-foreground">
          Side-by-side mode active: left panel shows current bucket ranges, right panel shows locked snapshot.
        </div>
      )}

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

      {/* Comparison Overlay Panel */}
      <Card className="card-3d">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-purple-500/10">
                <Layers className="h-4 w-4 text-purple-500" />
              </div>
              <CardTitle className="text-base">Compare Session Overlay</CardTitle>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-xs">
                Selected: {selectedSampleIds.length}
              </Badge>
              <Badge variant="outline" className="text-xs">
                Visible: {visibleSampleIds.length}
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="space-y-1.5 rounded-md border border-border/60 p-2.5">
              <Label className="text-xs text-muted-foreground">Upload Comparison File</Label>
              <div className="flex items-center gap-2">
                <Input
                  type="file"
                  accept=".txt,.csv"
                  multiple
                  className="h-8 text-xs"
                  disabled={compareUploadLoading}
                  onChange={(event) => {
                    const files = event.target.files
                    if (files && files.length > 0) {
                      handleComparisonUploads(files)
                    }
                    event.currentTarget.value = ""
                  }}
                />
                {compareUploadLoading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
              </div>
              <p className="text-[11px] text-muted-foreground flex items-center gap-1">
                <Upload className="h-3 w-3" />
                Upload one or many files and auto-add to this compare session.
              </p>
              {compareUploadProgress && (
                <p className="text-[11px] text-muted-foreground">
                  Uploaded {compareUploadProgress.completed}/{compareUploadProgress.total}
                  {compareUploadProgress.failed > 0 ? `, failed ${compareUploadProgress.failed}` : ""}
                </p>
              )}
            </div>

            <div className="flex items-center justify-between gap-2">
              <Label className="text-xs text-muted-foreground">Select Samples (up to 20)</Label>
              <div className="flex gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => setNTACompareVisibleSampleIds(selectedSampleIds.slice(0, 3))}
                  disabled={selectedSampleIds.length === 0}
                >
                  Show Top 3
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => setNTACompareVisibleSampleIds([])}
                  disabled={visibleSampleIds.length === 0}
                >
                  Hide All
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => loadNTACompareSamples(selectedSampleIds)}
                  disabled={selectedSampleIds.length === 0}
                >
                  <RefreshCw className="h-3 w-3 mr-1" />
                  Refresh
                </Button>
              </div>
            </div>

            <div className="flex items-center justify-between rounded-md border border-border/60 p-2">
              <Label className="text-xs text-muted-foreground" htmlFor="historical-samples-toggle">
                Show Historical Database Samples
              </Label>
              <Switch
                id="historical-samples-toggle"
                checked={showHistoricalSamples}
                onCheckedChange={setShowHistoricalSamples}
              />
            </div>

            <ScrollArea className="max-h-45 pr-1">
              <div className="space-y-1">
                {selectableSampleIds.map((sampleIdentifier) => {
                  const isSelected = selectedSampleIds.includes(sampleIdentifier)
                  return (
                    <label
                      key={sampleIdentifier}
                      className="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-secondary/30 cursor-pointer"
                    >
                      <Checkbox
                        checked={isSelected}
                        onCheckedChange={(checked) => handleSampleSelection(sampleIdentifier, checked === true)}
                      />
                      <span className="text-xs truncate flex-1">{sampleLabelById[sampleIdentifier] || sampleIdentifier}</span>
                    </label>
                  )
                })}
                {selectableSampleIds.length === 0 && (
                  <p className="px-2 py-3 text-xs text-muted-foreground">
                    No session samples yet. Upload files or enable historical samples.
                  </p>
                )}
              </div>
            </ScrollArea>

            {selectedSampleIds.length > 0 && (
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Selected Samples</Label>
                <div className="space-y-1 max-h-52 overflow-y-auto pr-1">
                  {selectedSampleIds.map((id) => {
                    const isVisible = visibleSampleIds.includes(id)
                    const isPrimary = id === primarySampleId
                    const loading = ntaCompareSession.loadingBySampleId[id]
                    const error = ntaCompareSession.errorBySampleId[id]
                    const resultForSample = id === sampleId ? results : ntaCompareSession.resultsBySampleId[id]

                    return (
                      <div key={id} className="rounded-md border border-border/60 p-2 space-y-1.5">
                        <div className="flex items-center justify-between gap-2">
                          <div className="min-w-0">
                            <p className="text-xs font-medium truncate">{sampleLabelById[id] || id}</p>
                            <p className="text-[11px] text-muted-foreground">
                              {loading ? "Loading..." : error ? "Failed" : resultForSample ? "Ready" : "Pending"}
                            </p>
                          </div>
                          <div className="flex items-center gap-1">
                            <Button
                              variant={isPrimary ? "secondary" : "outline"}
                              size="sm"
                              className="h-6 px-2 text-[10px]"
                              onClick={() => setNTAComparePrimarySampleId(id)}
                            >
                              <Star className="h-3 w-3 mr-1" />
                              Primary
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6"
                              onClick={() => handleRemoveSelectedSample(id)}
                            >
                              <MinusCircle className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </div>

                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={isVisible}
                              onCheckedChange={() => toggleNTACompareSampleVisibility(id)}
                            />
                            <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                              {isVisible ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
                              {isVisible ? "Visible in overlays" : "Hidden from overlays"}
                            </span>
                          </div>
                          {resultForSample?.median_size_nm && (
                            <Badge variant="outline" className="text-[10px]">
                              D50: {resultForSample.median_size_nm.toFixed(1)}nm
                            </Badge>
                          )}
                        </div>

                        {error && <p className="text-[11px] text-destructive">{error}</p>}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            <div className="flex justify-end">
              <Button
                variant="ghost"
                size="sm"
                className="text-xs"
                onClick={handleClearCompareSession}
                disabled={selectedSampleIds.length === 0}
              >
                Clear Compare Session
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

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
              {showTemperatureCorrection && (
                <TabsTrigger value="corrected" className="shrink-0">
                  Temperature Corrected
                </TabsTrigger>
              )}
              <TabsTrigger value="metadata" className="shrink-0">
                📋 Metadata
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
              <div data-report-chart="nta-distribution">
                <NTASizeDistributionChart 
                  data={results} 
                  overlaySeries={stagedOverlaySeries}
                />
              </div>
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
              <div data-report-chart="nta-concentration">
                <ConcentrationProfileChart 
                  data={results} 
                  overlaySeries={stagedOverlaySeries}
                  bins={analysisProfile?.bins || []}
                />
              </div>
            </TabsContent>

            {showTemperatureCorrection && (
              <TabsContent value="corrected" className="space-y-4">
                <div data-report-chart="nta-temperature-corrected">
                  <TemperatureCorrectedComparison data={results} />
                </div>
              </TabsContent>
            )}

            <TabsContent value="metadata" className="space-y-4">
              {selectedSampleIds.length > 1 ? (
                <NTAMetadataCompareTable sampleIds={selectedSampleIds} primarySampleId={primarySampleId} />
              ) : (
                <SupplementaryMetadataTable sampleId={sampleId} />
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}
