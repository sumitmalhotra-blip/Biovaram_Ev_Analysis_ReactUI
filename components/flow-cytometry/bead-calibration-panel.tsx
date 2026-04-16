"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Separator } from "@/components/ui/separator"
import { Switch } from "@/components/ui/switch"
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Target,
  CheckCircle2,
  XCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
  Info,
  Trash2,
  RefreshCw,
  Plus,
  Minus,
  Zap,
  Upload,
  Library,
  RotateCcw,
  AlertTriangle,
  Clock,
  ShieldCheck,
  ShieldAlert,
  FileText,
  FileUp,
  FolderUp,
  Check,
} from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { useAnalysisStore } from "@/lib/store"
import { apiClient, type CalibrationStatus, type BeadStandard, type ActiveCalibration, type FCMPASSStatus, type FCMPASSDiagnostics, type CustomBeadKitRequest, type FCMPASSCalibrationListItem, type SelfValidationResult, type BeadKitExpiryResult, type GainMismatchResult, type BeadDatasheetParseResult, type ParsedBeadPopulation, type BeadFcsUploadResult, type AutoCalibrateResult } from "@/lib/api-client"
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Line,
  ComposedChart,
  Legend,
} from "recharts"

// ─── Types ───────────────────────────────────────────────────────────

interface ManualBeadRow {
  id: number
  diameter_nm: string
  mean_ssc: string
}

// ─── Component ───────────────────────────────────────────────────────

export function BeadCalibrationPanel() {
  const { toast } = useToast()
  const { apiSamples, apiConnected, setApiSamples } = useAnalysisStore()

  // Calibration state
  const [calStatus, setCalStatus] = useState<CalibrationStatus | null>(null)
  const [activeCalibration, setActiveCalibration] = useState<ActiveCalibration | null>(null)
  const [beadStandards, setBeadStandards] = useState<BeadStandard[]>([])
  const [loading, setLoading] = useState(false)
  const [fitting, setFitting] = useState(false)
  const [expanded, setExpanded] = useState(false)

  // Auto-fit form state
  const [selectedSampleId, setSelectedSampleId] = useState("")
  const [selectedKit, setSelectedKit] = useState("")
  const [sscChannel, setSscChannel] = useState("VSSC1-H")

  // Manual fit state
  const [showManual, setShowManual] = useState(false)
  const [manualRows, setManualRows] = useState<ManualBeadRow[]>([
    { id: 1, diameter_nm: "", mean_ssc: "" },
    { id: 2, diameter_nm: "", mean_ssc: "" },
  ])
  const [manualKitName, setManualKitName] = useState("")
  const [manualRI, setManualRI] = useState("1.591")

  // Bead file upload state
  const beadFileInputRef = useRef<HTMLInputElement>(null)
  const beadCsvInputRef = useRef<HTMLInputElement>(null)
  const [beadUploading, setBeadUploading] = useState(false)
  const [showAdvancedPhysics, setShowAdvancedPhysics] = useState(false)

  // FCMPASS state
  const [calibrationMode, setCalibrationMode] = useState<"fcmpass" | "legacy">("fcmpass")
  const [fcmpassStatus, setFcmpassStatus] = useState<FCMPASSStatus | null>(null)
  const [fcmpassDiagnostics, setFcmpassDiagnostics] = useState<FCMPASSDiagnostics | null>(null)
  const [evRI, setEvRI] = useState("1.37")
  const [fcmpassWavelength, setFcmpassWavelength] = useState("405")
  const [fcmpassBeadRI, setFcmpassBeadRI] = useState("1.591")
  const [fcmpassMediumRI, setFcmpassMediumRI] = useState("1.33")
  const [useDispersion, setUseDispersion] = useState(true)

  // Custom bead kit dialog state
  const [showCustomKitDialog, setShowCustomKitDialog] = useState(false)
  const [customKitSaving, setCustomKitSaving] = useState(false)
  const [customKitName, setCustomKitName] = useState("")
  const [customKitManufacturer, setCustomKitManufacturer] = useState("")
  const [customKitPartNumber, setCustomKitPartNumber] = useState("")
  const [customKitLotNumber, setCustomKitLotNumber] = useState("")
  const [customKitMaterial, setCustomKitMaterial] = useState("polystyrene_latex")
  const [customKitRI, setCustomKitRI] = useState("1.591")
  const [customKitNistTraceable, setCustomKitNistTraceable] = useState(false)
  const [customKitBeads, setCustomKitBeads] = useState<Array<{ id: number; label: string; diameter_nm: string; cv_pct: string }>>([
    { id: 1, label: "", diameter_nm: "", cv_pct: "5.0" },
    { id: 2, label: "", diameter_nm: "", cv_pct: "5.0" },
  ])

  // Calibration library state (Phase 3)
  const [showCalLibrary, setShowCalLibrary] = useState(false)
  const [calLibrary, setCalLibrary] = useState<FCMPASSCalibrationListItem[]>([])
  const [calLibraryLoading, setCalLibraryLoading] = useState(false)
  const [calLibraryActivating, setCalLibraryActivating] = useState<string | null>(null)
  const [calLibraryDeleting, setCalLibraryDeleting] = useState<string | null>(null)

  // Phase 4: Safety & Validation state
  const [selfValidation, setSelfValidation] = useState<SelfValidationResult | null>(null)
  const [beadKitExpiry, setBeadKitExpiry] = useState<BeadKitExpiryResult | null>(null)
  const [gainMismatch, setGainMismatch] = useState<GainMismatchResult | null>(null)

  // ─── New Workflow State ────────────────────────────────────────────
  // Uploaded bead FCS files
  const beadFcsInputRef = useRef<HTMLInputElement>(null)
  const beadDatasheetInputRef = useRef<HTMLInputElement>(null)
  const [uploadedBeadFcsFiles, setUploadedBeadFcsFiles] = useState<Array<{
    filename: string;
    sample_id: string;
    size_bytes?: number;
  }>>([])
  const [beadFcsUploading, setBeadFcsUploading] = useState(false)
  
  // Parsed datasheet
  const [parsedDatasheet, setParsedDatasheet] = useState<BeadDatasheetParseResult | null>(null)
  const [datasheetParsing, setDatasheetParsing] = useState(false)
  const [datasheetFilename, setDatasheetFilename] = useState("")
  
  // Auto-calibration
  const [autoCalibrating, setAutoCalibrating] = useState(false)
  const [autoCalResult, setAutoCalResult] = useState<AutoCalibrateResult | null>(null)

  // ─── Data Fetching ─────────────────────────────────────────────────

  const fetchStatus = useCallback(async () => {
    if (!apiConnected) return
    try {
      const status = await apiClient.getCalibrationStatus()
      setCalStatus(status)
    } catch {
      // silently fail - status badge will show unknown
    }
  }, [apiConnected])

  const fetchBeadStandards = useCallback(async () => {
    if (!apiConnected) return
    try {
      const result = await apiClient.getBeadStandards()
      setBeadStandards(result?.standards || [])
      if (result?.standards?.length > 0 && !selectedKit) {
        setSelectedKit(result.standards[0].filename)
      }
    } catch {
      // silently fail
    }
  }, [apiConnected, selectedKit])

  const fetchActiveCalibration = useCallback(async () => {
    if (!apiConnected) return
    try {
      const result = await apiClient.getActiveCalibration()
      setActiveCalibration(result)
    } catch {
      // silently fail
    }
  }, [apiConnected])

  const fetchFcmpassStatus = useCallback(async () => {
    if (!apiConnected) return
    try {
      const status = await apiClient.getFcmpassStatus()
      setFcmpassStatus(status)
    } catch {
      // silently fail
    }
  }, [apiConnected])

  const fetchBeadKitExpiry = useCallback(async () => {
    if (!apiConnected) return
    try {
      const result = await apiClient.checkBeadKitExpiry()
      setBeadKitExpiry(result)
    } catch {
      // silently fail
    }
  }, [apiConnected])

  const fetchCalibrationLibrary = useCallback(async () => {
    if (!apiConnected) return
    setCalLibraryLoading(true)
    try {
      const result = await apiClient.listFcmpassCalibrations()
      setCalLibrary(result?.calibrations || [])
    } catch {
      // silently fail
    } finally {
      setCalLibraryLoading(false)
    }
  }, [apiConnected])

  const handleActivateCalibration = async (calId: string) => {
    setCalLibraryActivating(calId)
    try {
      const result = await apiClient.activateFcmpassCalibration(calId)
      if (result?.success) {
        toast({
          title: "Calibration Activated",
          description: `${result.message} (k=${result.k_instrument?.toFixed(1)})`,
        })
        // Refresh everything
        await Promise.all([fetchCalibrationLibrary(), fetchFcmpassStatus(), fetchStatus()])
      }
    } catch (error: unknown) {
      toast({
        title: "Activation Failed",
        description: error instanceof Error ? error.message : "Failed to activate calibration",
        variant: "destructive",
      })
    } finally {
      setCalLibraryActivating(null)
    }
  }

  const handleDeleteCalibration = async (calId: string) => {
    setCalLibraryDeleting(calId)
    try {
      const result = await apiClient.deleteFcmpassCalibration(calId)
      if (result?.success) {
        toast({
          title: "Calibration Deleted",
          description: result.message,
        })
        await fetchCalibrationLibrary()
      }
    } catch (error: unknown) {
      toast({
        title: "Delete Failed",
        description: error instanceof Error ? error.message : "Failed to delete calibration",
        variant: "destructive",
      })
    } finally {
      setCalLibraryDeleting(null)
    }
  }

  // Fetch on mount
  useEffect(() => {
    fetchStatus()
    fetchBeadStandards()
    fetchFcmpassStatus()
    fetchBeadKitExpiry()
  }, [fetchStatus, fetchBeadStandards, fetchFcmpassStatus, fetchBeadKitExpiry])

  // Load full calibration when expanded
  useEffect(() => {
    if (expanded && calStatus?.calibrated) {
      fetchActiveCalibration()
    }
  }, [expanded, calStatus?.calibrated, fetchActiveCalibration])

  // Load calibration library when section is opened
  useEffect(() => {
    if (showCalLibrary) {
      fetchCalibrationLibrary()
    }
  }, [showCalLibrary, fetchCalibrationLibrary])

  // ─── Auto-Fit Handler ──────────────────────────────────────────────

  const handleAutoFit = async () => {
    if (!selectedSampleId || !selectedKit) {
      toast({
        title: "Missing Selection",
        description: "Please select both a bead FCS sample and a bead standard kit.",
        variant: "destructive",
      })
      return
    }

    setFitting(true)
    try {
      const result = await apiClient.fitCalibration(selectedSampleId, selectedKit, sscChannel)

      if (result?.success) {
        toast({
          title: "Calibration Applied",
          description: result.message || "Bead calibration curve fitted and saved.",
        })
        // Refresh status
        await fetchStatus()
        await fetchActiveCalibration()
      } else {
        toast({
          title: "Calibration Failed",
          description: "The auto-fit could not complete. Try manual mode.",
          variant: "destructive",
        })
      }
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : "Unknown error"
      toast({
        title: "Calibration Error",
        description: msg,
        variant: "destructive",
      })
    } finally {
      setFitting(false)
    }
  }

  // ─── Manual Fit Handler ────────────────────────────────────────────

  const handleManualFit = async () => {
    const validRows = manualRows.filter(
      (r) => r.diameter_nm.trim() !== "" && r.mean_ssc.trim() !== ""
    )
    if (validRows.length < 2) {
      toast({
        title: "Not Enough Points",
        description: "Provide at least 2 bead data points for calibration.",
        variant: "destructive",
      })
      return
    }

    const points = validRows.map((r) => ({
      diameter_nm: parseFloat(r.diameter_nm),
      mean_ssc: parseFloat(r.mean_ssc),
    }))

    // Validate
    for (const p of points) {
      if (isNaN(p.diameter_nm) || isNaN(p.mean_ssc) || p.diameter_nm <= 0 || p.mean_ssc <= 0) {
        toast({
          title: "Invalid Data",
          description: "All diameter and scatter values must be positive numbers.",
          variant: "destructive",
        })
        return
      }
    }

    setFitting(true)
    try {
      const result = await apiClient.fitCalibrationManual(
        points,
        manualKitName || undefined,
        manualRI ? parseFloat(manualRI) : undefined
      )

      if (result?.success) {
        toast({
          title: "Manual Calibration Applied",
          description: result.message || "Calibration curve fitted from manual data.",
        })
        await fetchStatus()
        await fetchActiveCalibration()
        setShowManual(false)
      } else {
        toast({
          title: "Manual Fit Failed",
          description: "Could not fit a calibration curve to the provided data.",
          variant: "destructive",
        })
      }
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : "Unknown error"
      toast({
        title: "Manual Calibration Error",
        description: msg,
        variant: "destructive",
      })
    } finally {
      setFitting(false)
    }
  }

  // ─── Remove Calibration ────────────────────────────────────────────

  const handleRemove = async () => {
    setLoading(true)
    try {
      // Remove both FCMPASS and legacy calibrations
      const results = await Promise.allSettled([
        apiClient.removeFcmpassCalibration(),
        apiClient.removeCalibration(),
      ])
      
      const anySuccess = results.some(
        (r) => r.status === "fulfilled" && r.value?.success
      )
      
      if (anySuccess) {
        toast({
          title: "Calibration Removed",
          description: "All calibrations cleared. Reverted to uncalibrated Mie theory.",
        })
        setCalStatus(null)
        setActiveCalibration(null)
        setFcmpassStatus(null)
        setFcmpassDiagnostics(null)
        await fetchStatus()
        await fetchFcmpassStatus()
      }
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : "Unknown error"
      toast({
        title: "Error",
        description: msg,
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  // ─── FCMPASS Manual Fit Handler ────────────────────────────────────

  const handleFcmpassManualFit = async () => {
    const validRows = manualRows.filter(
      (r) => r.diameter_nm.trim() !== "" && r.mean_ssc.trim() !== ""
    )
    if (validRows.length < 2) {
      toast({
        title: "Not Enough Points",
        description: "Provide at least 2 bead data points for FCMPASS calibration.",
        variant: "destructive",
      })
      return
    }

    const beadPoints = validRows.map((r) => ({
      diameter_nm: parseFloat(r.diameter_nm),
      scatter_au: parseFloat(r.mean_ssc),
    }))

    // Validate
    for (const p of beadPoints) {
      if (isNaN(p.diameter_nm) || isNaN(p.scatter_au) || p.diameter_nm <= 0 || p.scatter_au <= 0) {
        toast({
          title: "Invalid Data",
          description: "All diameter and scatter values must be positive numbers.",
          variant: "destructive",
        })
        return
      }
    }

    setFitting(true)
    try {
      const result = await apiClient.fitFcmpassCalibration({
        bead_points: beadPoints,
        wavelength_nm: parseFloat(fcmpassWavelength) || 405,
        n_bead: parseFloat(fcmpassBeadRI) || 1.591,
        n_ev: parseFloat(evRI) || 1.37,
        n_medium: parseFloat(fcmpassMediumRI) || 1.33,
        use_wavelength_dispersion: useDispersion,
        set_as_active: true,
      })

      if (result?.success) {
        setFcmpassDiagnostics(result.diagnostics)
        
        // Capture self-validation results (Phase 4 - C1)
        if (result.self_validation || result.diagnostics?.self_validation) {
          setSelfValidation(result.self_validation || result.diagnostics?.self_validation || null)
        }
        
        // Capture bead kit expiry info (Phase 4 - C2)
        if (result.bead_kit_expiry) {
          setBeadKitExpiry(result.bead_kit_expiry)
        }
        
        // Show warnings if any (self-validation failures, expiry alerts)
        const warnings = result.warnings
        if (warnings && warnings.length > 0) {
          toast({
            title: "Calibration Warnings",
            description: warnings.join(" "),
            variant: "destructive",
          })
        } else {
          toast({
            title: "FCMPASS Calibration Applied",
            description: result.message || "FCMPASS k-based calibration fitted and saved.",
          })
        }
        
        await fetchStatus()
        await fetchFcmpassStatus()
        await fetchActiveCalibration()
        setShowManual(false)
      } else {
        toast({
          title: "FCMPASS Calibration Failed",
          description: "Could not fit FCMPASS calibration. Check bead data.",
          variant: "destructive",
        })
      }
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : "Unknown error"
      toast({
        title: "FCMPASS Calibration Error",
        description: msg,
        variant: "destructive",
      })
    } finally {
      setFitting(false)
    }
  }

  // ─── Manual Row Helpers ────────────────────────────────────────────

  // ─── Bead File Upload Handler ──────────────────────────────────────

  const handleBeadFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    if (!file.name.toLowerCase().endsWith('.fcs')) {
      toast({
        title: "Invalid File",
        description: "Please select an .fcs file containing bead measurements.",
        variant: "destructive",
      })
      // Reset the input so the same file can be selected again
      if (beadFileInputRef.current) beadFileInputRef.current.value = ""
      return
    }

    setBeadUploading(true)
    try {
      const response = await apiClient.uploadFCS(file, {
        treatment: "bead_calibration",
        notes: "Bead calibration FCS file",
      })

      if (response?.success) {
        toast({
          title: "Bead File Uploaded",
          description: `${file.name} uploaded as ${response.sample_id}`,
        })
        // Auto-select the uploaded sample
        setSelectedSampleId(response.sample_id)
        
        // Refresh samples list so the dropdown updates
        try {
          const samplesResp = await apiClient.listSamples({})
          if (samplesResp?.samples) {
            setApiSamples(samplesResp.samples)
          }
        } catch {
          // silently fail — the sample was still uploaded
        }
      } else {
        toast({
          title: "Upload Failed",
          description: "Could not upload the bead FCS file. Please try again.",
          variant: "destructive",
        })
      }
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : "Upload failed"
      toast({
        title: "Upload Error",
        description: msg,
        variant: "destructive",
      })
    } finally {
      setBeadUploading(false)
      if (beadFileInputRef.current) beadFileInputRef.current.value = ""
    }
  }

  // ─── CSV/TSV Bead Datasheet Upload Handler ─────────────────────────
  // Allows scientists to upload a simple CSV/TSV with columns:
  // diameter_nm, mean_au (or similar names)
  const handleBeadDatasheetUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      const text = await file.text()
      const lines = text.trim().split(/\r?\n/)
      if (lines.length < 2) {
        toast({ title: "Invalid File", description: "File must have a header row and at least 1 data row.", variant: "destructive" })
        return
      }

      // Detect delimiter (tab, comma, or semicolon)
      const delimiter = lines[0].includes('\t') ? '\t' : lines[0].includes(';') ? ';' : ','
      const header = lines[0].split(delimiter).map(h => h.trim().toLowerCase().replace(/['"]/g, ''))

      // Find diameter and AU columns (flexible naming)
      const diameterIdx = header.findIndex(h =>
        h.includes('diameter') || h.includes('size') || h.includes('nm') || h === 'd'
      )
      const auIdx = header.findIndex(h =>
        h.includes('au') || h.includes('mean') || h.includes('scatter') || h.includes('ssc') || h.includes('intensity') || h.includes('signal')
      )

      if (diameterIdx === -1 || auIdx === -1) {
        toast({
          title: "Column Not Found",
          description: "CSV must have columns for diameter (nm) and mean AU/scatter intensity. Expected headers like 'diameter_nm', 'mean_au'.",
          variant: "destructive",
        })
        return
      }

      // Parse data rows
      const newRows: ManualBeadRow[] = []
      for (let i = 1; i < lines.length; i++) {
        const cols = lines[i].split(delimiter).map(c => c.trim().replace(/['"]/g, ''))
        const diam = cols[diameterIdx]
        const au = cols[auIdx]
        if (diam && au && !isNaN(parseFloat(diam)) && !isNaN(parseFloat(au))) {
          newRows.push({ id: i, diameter_nm: diam, mean_ssc: au })
        }
      }

      if (newRows.length < 2) {
        toast({ title: "Insufficient Data", description: "Need at least 2 valid bead data points.", variant: "destructive" })
        return
      }

      setManualRows(newRows)
      toast({
        title: "Datasheet Loaded",
        description: `${newRows.length} bead populations imported from ${file.name}. Click "Fit FCMPASS Calibration" to apply.`,
      })
    } catch {
      toast({ title: "Parse Error", description: "Could not parse the bead datasheet file.", variant: "destructive" })
    } finally {
      if (beadCsvInputRef.current) beadCsvInputRef.current.value = ""
    }
  }

  const addManualRow = () => {
    const nextId = manualRows.length > 0 ? Math.max(...manualRows.map((r) => r.id)) + 1 : 1
    setManualRows([...manualRows, { id: nextId, diameter_nm: "", mean_ssc: "" }])
  }

  const removeManualRow = (id: number) => {
    if (manualRows.length <= 2) return
    setManualRows(manualRows.filter((r) => r.id !== id))
  }

  const updateManualRow = (id: number, field: "diameter_nm" | "mean_ssc", value: string) => {
    setManualRows(manualRows.map((r) => (r.id === id ? { ...r, [field]: value } : r)))
  }

  // Pre-fill manual rows from bead kit datasheet
  const prefillFromKit = (kit: BeadStandard) => {
    if (kit.bead_sizes_nm?.length) {
      const rows: ManualBeadRow[] = kit.bead_sizes_nm.map((d: number, i: number) => ({
        id: i + 1,
        diameter_nm: d.toString(),
        mean_ssc: "",
      }))
      setManualRows(rows)
      setManualKitName(kit.product_name || kit.filename)
      if (kit.refractive_index) setManualRI(kit.refractive_index.toString())
    }
  }

  // ─── Custom Bead Kit Handlers ──────────────────────────────────────

  const resetCustomKitForm = () => {
    setCustomKitName("")
    setCustomKitManufacturer("")
    setCustomKitPartNumber("")
    setCustomKitLotNumber("")
    setCustomKitMaterial("polystyrene_latex")
    setCustomKitRI("1.591")
    setCustomKitNistTraceable(false)
    setCustomKitBeads([
      { id: 1, label: "", diameter_nm: "", cv_pct: "5.0" },
      { id: 2, label: "", diameter_nm: "", cv_pct: "5.0" },
    ])
  }

  const addCustomKitBead = () => {
    const maxId = customKitBeads.reduce((max, b) => Math.max(max, b.id), 0)
    setCustomKitBeads([...customKitBeads, { id: maxId + 1, label: "", diameter_nm: "", cv_pct: "5.0" }])
  }

  const removeCustomKitBead = (id: number) => {
    if (customKitBeads.length <= 1) return
    setCustomKitBeads(customKitBeads.filter(b => b.id !== id))
  }

  const updateCustomKitBead = (id: number, field: string, value: string) => {
    setCustomKitBeads(customKitBeads.map(b => b.id === id ? { ...b, [field]: value } : b))
  }

  const handleSaveCustomKit = async () => {
    if (!customKitName.trim()) {
      toast({ title: "Kit name required", description: "Enter a name for the bead kit.", variant: "destructive" })
      return
    }
    const validBeads = customKitBeads.filter(b => b.diameter_nm && parseFloat(b.diameter_nm) > 0)
    if (validBeads.length < 1) {
      toast({ title: "At least 1 bead size required", description: "Enter at least one bead diameter.", variant: "destructive" })
      return
    }

    setCustomKitSaving(true)
    try {
      const request: CustomBeadKitRequest = {
        product_name: customKitName.trim(),
        manufacturer: customKitManufacturer.trim() || undefined,
        kit_part_number: customKitPartNumber.trim() || undefined,
        lot_number: customKitLotNumber.trim() || undefined,
        material: customKitMaterial,
        refractive_index: parseFloat(customKitRI) || 1.591,
        nist_traceable: customKitNistTraceable,
        beads: validBeads.map(b => ({
          label: b.label.trim() || `${b.diameter_nm}nm`,
          diameter_nm: parseFloat(b.diameter_nm),
          cv_pct: parseFloat(b.cv_pct) || 5.0,
        })),
      }

      const result = await apiClient.uploadCustomBeadKit(request)
      toast({
        title: "Custom Kit Saved",
        description: `${result.product_name} (${result.n_bead_sizes} sizes) saved as ${result.filename}`,
      })
      resetCustomKitForm()
      setShowCustomKitDialog(false)
      // Refresh kit list
      fetchBeadStandards()
    } catch (err) {
      toast({ title: "Save Failed", description: String(err), variant: "destructive" })
    } finally {
      setCustomKitSaving(false)
    }
  }

  const handleDeleteBeadKit = async (filename: string, productName: string) => {
    try {
      await apiClient.deleteBeadStandard(filename)
      toast({ title: "Kit Deleted", description: `${productName} removed.` })
      fetchBeadStandards()
    } catch (err) {
      toast({ title: "Delete Failed", description: String(err), variant: "destructive" })
    }
  }

  // ─── FCS Samples List ──────────────────────────────────────────────

  const fcsSamples = apiSamples.filter((s) => s.files?.fcs)

  // ─── Multi-File Bead FCS Upload Handler ────────────────────────────

  const handleMultiBeadFcsUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files
    if (!fileList || fileList.length === 0) return

    const files: File[] = []
    for (let i = 0; i < fileList.length; i++) {
      const f = fileList[i]
      if (f.name.toLowerCase().endsWith(".fcs")) {
        files.push(f)
      }
    }

    if (files.length === 0) {
      toast({
        title: "No FCS Files",
        description: "Please select .fcs files containing bead measurements.",
        variant: "destructive",
      })
      if (beadFcsInputRef.current) beadFcsInputRef.current.value = ""
      return
    }

    setBeadFcsUploading(true)
    try {
      const result = await apiClient.uploadBeadFcsFiles(files)
      if (result?.success) {
        const uploaded = result.files.filter(f => f.success).map(f => ({
          filename: f.filename,
          sample_id: f.sample_id!,
          size_bytes: f.size_bytes,
        }))
        setUploadedBeadFcsFiles(prev => [...prev, ...uploaded])
        toast({
          title: "Bead FCS Files Uploaded",
          description: `${uploaded.length} file(s) uploaded: ${uploaded.map(f => f.filename).join(", ")}`,
        })
        // Also refresh samples list
        try {
          const samplesResp = await apiClient.listSamples({})
          if (samplesResp?.samples) setApiSamples(samplesResp.samples)
        } catch { /* silent */ }
      } else {
        toast({ title: "Upload Failed", description: result?.message || "Could not upload bead FCS files.", variant: "destructive" })
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Upload failed"
      toast({ title: "Upload Error", description: msg, variant: "destructive" })
    } finally {
      setBeadFcsUploading(false)
      if (beadFcsInputRef.current) beadFcsInputRef.current.value = ""
    }
  }

  // ─── Bead Datasheet Upload Handler (PDF/CSV) ──────────────────────

  const handleDatasheetUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setDatasheetParsing(true)
    setDatasheetFilename(file.name)
    try {
      const result = await apiClient.parseBeadDatasheet(file)
      setParsedDatasheet(result)
      
      if (result?.success && result.all_beads?.length > 0) {
        toast({
          title: "Datasheet Parsed",
          description: `${result.n_beads_total} bead sizes from ${result.n_subcomponents} subcomponents detected in ${file.name}`,
        })
        
        // Auto-fill manual rows with parsed bead data (diameter only, scatter AU from FCS)
        if (result.all_beads.length > 0) {
          const newRows: ManualBeadRow[] = result.all_beads.map((b, i) => ({
            id: i + 1,
            diameter_nm: b.diameter_nm.toString(),
            mean_ssc: "",
          }))
          setManualRows(newRows)
        }
        
        // Update physics params from datasheet
        if (result.refractive_index) {
          setFcmpassBeadRI(result.refractive_index.toString())
        }
      } else {
        const fallbackMessage = selectedKit
          ? `${result?.message || "Could not extract bead data from datasheet."} Continuing with selected bead kit (${selectedKit}).`
          : (result?.message || "Could not extract bead data. Try CSV format.")

        toast({
          title: selectedKit ? "Datasheet Parse Warning" : "Parse Issue",
          description: fallbackMessage,
          variant: selectedKit ? "default" : "destructive",
        })
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Parse failed"
      toast({ title: "Datasheet Error", description: msg, variant: "destructive" })
    } finally {
      setDatasheetParsing(false)
      if (beadDatasheetInputRef.current) beadDatasheetInputRef.current.value = ""
    }
  }

  // ─── Auto-Calibrate Handler ────────────────────────────────────────

  const handleAutoCalibrate = async () => {
    if (uploadedBeadFcsFiles.length === 0) {
      toast({ title: "No Bead Files", description: "Upload bead FCS files first.", variant: "destructive" })
      return
    }

    setAutoCalibrating(true)
    try {
      const result = await apiClient.autoCalibrate({
        sample_ids: uploadedBeadFcsFiles.map(f => f.sample_id),
        scatter_channel: sscChannel,
        bead_kit: selectedKit || "nanovis_d03231.json",
        wavelength_nm: parseFloat(fcmpassWavelength) || 405,
        n_bead: parseFloat(fcmpassBeadRI) || 1.591,
        n_ev: parseFloat(evRI) || 1.37,
        n_medium: parseFloat(fcmpassMediumRI) || 1.33,
        use_wavelength_dispersion: useDispersion,
      })

      setAutoCalResult(result)

      if (result?.success) {
        toast({
          title: "Auto-Calibration Complete",
          description: result.message || `Calibrated with ${result.n_beads} bead sizes. k=${result.k_instrument?.toFixed(1)}`,
        })
        await fetchStatus()
        await fetchFcmpassStatus()
        await fetchActiveCalibration()
      } else {
        toast({ title: "Calibration Failed", description: "Could not auto-calibrate. Try manual entry.", variant: "destructive" })
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Auto-calibration failed"
      toast({ title: "Calibration Error", description: msg, variant: "destructive" })
    } finally {
      setAutoCalibrating(false)
    }
  }

  // ─── Remove uploaded bead file ─────────────────────────────────────
  
  const removeUploadedBeadFile = (idx: number) => {
    setUploadedBeadFcsFiles(prev => prev.filter((_, i) => i !== idx))
  }

  // ─── Clear all uploaded data ───────────────────────────────────────
  
  const clearUploadedData = () => {
    setUploadedBeadFcsFiles([])
    setParsedDatasheet(null)
    setDatasheetFilename("")
    setAutoCalResult(null)
    setManualRows([
      { id: 1, diameter_nm: "", mean_ssc: "" },
      { id: 2, diameter_nm: "", mean_ssc: "" },
    ])
  }

  // ─── Calibration Status Badge ──────────────────────────────────────

  const isFcmpassCalibrated = fcmpassStatus?.calibrated === true
  const isLegacyCalibrated = calStatus?.calibrated === true
  const isCalibrated = isFcmpassCalibrated || isLegacyCalibrated
  const activeMethod = isFcmpassCalibrated ? "FCMPASS" : isLegacyCalibrated ? "Legacy" : null

  // ─── Render ────────────────────────────────────────────────────────

  // Helper: count filled rows
  const filledRows = manualRows.filter(r => r.diameter_nm && r.mean_ssc).length
  const hasBeadFcsFiles = uploadedBeadFcsFiles.length > 0
  const hasDatasheet = parsedDatasheet?.success === true
  const canAutoCalibrate = hasBeadFcsFiles && (hasDatasheet || selectedKit)

  return (
    <Card className="card-3d">
      <Collapsible open={expanded} onOpenChange={setExpanded}>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Target className="h-4 w-4 text-primary" />
                <CardTitle className="text-sm font-medium">Bead Calibration</CardTitle>
                {isCalibrated ? (
                  <Badge variant="default" className="bg-green-600 hover:bg-green-700 text-[10px] px-1.5 py-0">
                    <CheckCircle2 className="h-3 w-3 mr-0.5" />
                    {activeMethod === "FCMPASS" ? "FCMPASS Active" : "Calibrated"}
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                    <XCircle className="h-3 w-3 mr-0.5" />
                    Not Calibrated
                  </Badge>
                )}
              </div>
              {expanded ? (
                <ChevronUp className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
            {isFcmpassCalibrated && fcmpassStatus && (
              <p className="text-[10px] text-muted-foreground mt-1">
                k={fcmpassStatus.k_instrument?.toFixed(1)} | CV={fcmpassStatus.k_cv_pct?.toFixed(1)}% | {fcmpassStatus.n_beads} beads | λ={fcmpassStatus.wavelength_nm}nm
              </p>
            )}
            {!isFcmpassCalibrated && isLegacyCalibrated && calStatus && (
              <p className="text-[10px] text-muted-foreground mt-1">
                {calStatus.bead_kit} | R²={calStatus.r_squared?.toFixed(4)} | {calStatus.n_bead_sizes} beads
              </p>
            )}
          </CardHeader>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <CardContent className="space-y-4 pt-0">

            {/* ════════════════════════════════════════════════════════════
                SECTION 1: CURRENT CALIBRATION STATUS
                ════════════════════════════════════════════════════════════ */}

            {isFcmpassCalibrated && fcmpassStatus && (
              <div className="rounded-lg border border-green-200 bg-green-50/50 dark:bg-green-950/20 dark:border-green-900 p-3 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    <h4 className="text-xs font-semibold">Active Calibration</h4>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 text-[10px] text-destructive hover:text-destructive hover:bg-destructive/10 gap-1"
                    onClick={handleRemove}
                    disabled={loading}
                  >
                    {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
                    Clear
                  </Button>
                </div>
                <div className="grid grid-cols-4 gap-1.5 text-[11px]">
                  <div className="text-center p-1.5 rounded bg-white/60 dark:bg-black/20 border">
                    <div className="text-muted-foreground text-[9px]">Beads</div>
                    <div className="font-bold font-mono">{fcmpassStatus.n_beads}</div>
                  </div>
                  <div className="text-center p-1.5 rounded bg-white/60 dark:bg-black/20 border">
                    <div className="text-muted-foreground text-[9px]">k Value</div>
                    <div className="font-bold font-mono">{fcmpassStatus.k_instrument?.toFixed(1)}</div>
                  </div>
                  <div className="text-center p-1.5 rounded bg-white/60 dark:bg-black/20 border">
                    <div className="text-muted-foreground text-[9px]">CV%</div>
                    <div className={`font-bold font-mono ${(fcmpassStatus.k_cv_pct ?? 0) <= 5 ? "text-green-700" : "text-amber-600"}`}>
                      {fcmpassStatus.k_cv_pct?.toFixed(1)}%
                    </div>
                  </div>
                  <div className="text-center p-1.5 rounded bg-white/60 dark:bg-black/20 border">
                    <div className="text-muted-foreground text-[9px]">Laser</div>
                    <div className="font-bold font-mono">{fcmpassStatus.wavelength_nm}nm</div>
                  </div>
                </div>

                {fcmpassDiagnostics?.per_bead && (
                  <div>
                    <div className="text-[10px] text-muted-foreground mb-1 font-medium">Bead data in use:</div>
                    <div className="rounded border overflow-hidden">
                      <table className="w-full text-[11px]">
                        <thead className="bg-muted/50">
                          <tr>
                            <th className="px-2 py-1 text-left font-medium">Size</th>
                            <th className="px-2 py-1 text-right font-medium">Scatter AU</th>
                            <th className="px-2 py-1 text-right font-medium">k</th>
                            <th className="px-2 py-1 text-right font-medium">Error</th>
                          </tr>
                        </thead>
                        <tbody>
                          {fcmpassDiagnostics.per_bead.map((bead, i) => (
                            <tr key={i} className="border-t border-border/50">
                              <td className="px-2 py-1 font-mono font-medium">{bead.diameter_nm}nm</td>
                              <td className="px-2 py-1 text-right font-mono">{bead.measured_au?.toLocaleString()}</td>
                              <td className="px-2 py-1 text-right font-mono">{bead.k?.toFixed(1)}</td>
                              <td className="px-2 py-1 text-right font-mono">{bead.error_pct?.toFixed(1)}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {selfValidation?.validated && (
                  <div className="flex items-center gap-2 text-[11px]">
                    {selfValidation.all_passed ? (
                      <><ShieldCheck className="h-3.5 w-3.5 text-green-600" /><span className="text-green-700">All {selfValidation.n_beads} beads validated</span></>
                    ) : (
                      <><ShieldAlert className="h-3.5 w-3.5 text-amber-500" /><span className="text-amber-600">{selfValidation.n_failed}/{selfValidation.n_beads} beads failed</span></>
                    )}
                  </div>
                )}
                
                <div className="text-[10px] text-muted-foreground pt-1 border-t">
                  EV RI: {fcmpassStatus.n_ev} | Bead RI: {fcmpassStatus.n_bead} | Method: FCMPASS
                </div>
              </div>
            )}

            {!isFcmpassCalibrated && isLegacyCalibrated && activeCalibration?.calibrated && (
              <div className="rounded-lg border border-blue-200 bg-blue-50/50 dark:bg-blue-950/20 dark:border-blue-900 p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-blue-600" />
                    <h4 className="text-xs font-semibold">Active Calibration (Legacy)</h4>
                  </div>
                  <Button variant="ghost" size="sm" className="h-6 text-[10px] text-destructive hover:text-destructive hover:bg-destructive/10 gap-1" onClick={handleRemove} disabled={loading}>
                    {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
                    Clear
                  </Button>
                </div>
                <div className="text-[11px]">
                  Kit: <span className="font-mono font-medium">{calStatus?.bead_kit}</span> | R²: <span className="font-mono">{activeCalibration.calibration?.fit_params?.r_squared?.toFixed(4)}</span>
                </div>
              </div>
            )}

            {!isCalibrated && (
              <Alert className="border-amber-200 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-900">
                <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                <AlertDescription className="text-xs text-amber-700 dark:text-amber-300">
                  No calibration active. Upload your bead FCS files and datasheet below to calibrate.
                </AlertDescription>
              </Alert>
            )}

            <Separator />

            {/* ════════════════════════════════════════════════════════════
                SECTION 2: UPLOAD BEAD FILES
                Step 1: Upload FCS files + Datasheet → Auto-calibrate
                ════════════════════════════════════════════════════════════ */}

            <div className="space-y-3">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                {isCalibrated ? "Update Calibration" : "Set Up Calibration"}
              </h4>

              <p className="text-[11px] text-muted-foreground">
                Upload your bead FCS measurement files and the manufacturer datasheet (Certificate of Analysis). 
                The system will auto-detect bead peaks and calibrate.
              </p>

              {/* ── STEP 1a: Bead FCS Files ── */}
              <div className="rounded-lg border p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-bold ${hasBeadFcsFiles ? "bg-green-600 text-white" : "bg-muted text-muted-foreground"}`}>
                      {hasBeadFcsFiles ? <Check className="h-3 w-3" /> : "1"}
                    </div>
                    <Label className="text-xs font-medium">Bead FCS Files</Label>
                    {hasBeadFcsFiles && (
                      <Badge variant="secondary" className="text-[10px] px-1 py-0 h-4">{uploadedBeadFcsFiles.length} file{uploadedBeadFcsFiles.length > 1 ? "s" : ""}</Badge>
                    )}
                  </div>
                  {hasBeadFcsFiles && (
                    <Button variant="ghost" size="sm" className="h-5 text-[10px] text-muted-foreground" onClick={() => setUploadedBeadFcsFiles([])}>
                      Clear
                    </Button>
                  )}
                </div>

                {/* Uploaded files list */}
                {uploadedBeadFcsFiles.length > 0 && (
                  <div className="space-y-1">
                    {uploadedBeadFcsFiles.map((f, i) => (
                      <div key={i} className="flex items-center justify-between text-[11px] rounded bg-muted/50 px-2 py-1">
                        <div className="flex items-center gap-1.5">
                          <FileUp className="h-3 w-3 text-green-600 shrink-0" />
                          <span className="font-medium truncate max-w-35">{f.filename}</span>
                          <span className="text-muted-foreground">({f.sample_id})</span>
                        </div>
                        <Button variant="ghost" size="sm" className="h-5 w-5 p-0 shrink-0" onClick={() => removeUploadedBeadFile(i)}>
                          <Minus className="h-2.5 w-2.5" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}

                {/* Upload button */}
                <input
                  ref={beadFcsInputRef}
                  type="file"
                  accept=".fcs"
                  multiple
                  className="hidden"
                  onChange={handleMultiBeadFcsUpload}
                />
                <Button
                  variant="outline"
                  className="w-full h-9 text-xs gap-2"
                  onClick={() => beadFcsInputRef.current?.click()}
                  disabled={beadFcsUploading}
                >
                  {beadFcsUploading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <FolderUp className="h-4 w-4" />
                  )}
                  {beadFcsUploading
                    ? "Uploading..."
                    : uploadedBeadFcsFiles.length > 0
                    ? "Add More FCS Files"
                    : "Upload Bead FCS Files"}
                </Button>
                <p className="text-[10px] text-muted-foreground">
                  Select one or more .fcs files (e.g., nanoViS Low + nanoViS High)
                </p>
              </div>

              {/* ── STEP 1b: Bead Datasheet ── */}
              <div className="rounded-lg border p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-bold ${hasDatasheet ? "bg-green-600 text-white" : "bg-muted text-muted-foreground"}`}>
                      {hasDatasheet ? <Check className="h-3 w-3" /> : "2"}
                    </div>
                    <Label className="text-xs font-medium">Bead Datasheet (Certificate of Analysis)</Label>
                  </div>
                  {hasDatasheet && (
                    <Button variant="ghost" size="sm" className="h-5 text-[10px] text-muted-foreground" onClick={() => { setParsedDatasheet(null); setDatasheetFilename("") }}>
                      Clear
                    </Button>
                  )}
                </div>

                {/* Parsed datasheet summary */}
                {hasDatasheet && parsedDatasheet && (
                  <div className="rounded bg-green-50/50 dark:bg-green-950/20 border border-green-200 dark:border-green-900 p-2 space-y-1.5">
                    <div className="flex items-center gap-1.5 text-[11px]">
                      <CheckCircle2 className="h-3 w-3 text-green-600 shrink-0" />
                      <span className="font-medium">{datasheetFilename}</span>
                    </div>
                    <div className="text-[11px] text-muted-foreground space-y-0.5">
                      <div>Kit: <span className="font-mono font-medium">{parsedDatasheet.product_name || parsedDatasheet.kit_part_number}</span></div>
                      {parsedDatasheet.lot_number && <div>Lot: <span className="font-mono">{parsedDatasheet.lot_number}</span></div>}
                      {parsedDatasheet.manufacturer && <div>Mfr: {parsedDatasheet.manufacturer}</div>}
                      <div>RI: <span className="font-mono">{parsedDatasheet.refractive_index}</span> | NIST: {parsedDatasheet.nist_traceable ? "Yes" : "No"}</div>
                      {parsedDatasheet.expiration_date && <div>Expires: <span className="font-mono">{parsedDatasheet.expiration_date}</span></div>}
                    </div>
                    {/* Subcomponent bead list */}
                    {Object.entries(parsedDatasheet.subcomponents || {}).map(([name, beads]) => (
                      <div key={name} className="text-[11px]">
                        <div className="font-medium text-muted-foreground">{name}:</div>
                        <div className="flex flex-wrap gap-1 mt-0.5">
                          {beads.map((b, i) => (
                            <Badge key={i} variant="outline" className="text-[10px] px-1.5 py-0 h-4 font-mono">
                              {b.diameter_nm}nm
                            </Badge>
                          ))}
                        </div>
                      </div>
                    ))}
                    {parsedDatasheet.parse_warnings?.length > 0 && (
                      <div className="text-[10px] text-amber-600">
                        {parsedDatasheet.parse_warnings.map((w, i) => <div key={i}>⚠ {w}</div>)}
                      </div>
                    )}
                  </div>
                )}

                {/* Upload button */}
                <input
                  ref={beadDatasheetInputRef}
                  type="file"
                  accept=".pdf,.csv,.tsv,.txt"
                  className="hidden"
                  onChange={handleDatasheetUpload}
                />
                <Button
                  variant="outline"
                  className="w-full h-9 text-xs gap-2"
                  onClick={() => beadDatasheetInputRef.current?.click()}
                  disabled={datasheetParsing}
                >
                  {datasheetParsing ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <FileText className="h-4 w-4" />
                  )}
                  {datasheetParsing
                    ? "Parsing..."
                    : hasDatasheet
                    ? "Replace Datasheet"
                    : "Upload Datasheet (PDF or CSV)"}
                </Button>
                <p className="text-[10px] text-muted-foreground">
                  Upload the manufacturer Certificate of Analysis (.pdf or .csv)
                </p>
              </div>

              {/* ── STEP 2: Scatter Channel Selection ── */}
              <div className="rounded-lg border p-3 space-y-2">
                <div className="flex items-center gap-2">
                  <div className={`h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-bold bg-muted text-muted-foreground`}>
                    3
                  </div>
                  <Label className="text-xs font-medium">Settings</Label>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <Label className="text-[10px] text-muted-foreground">Scatter Channel</Label>
                    <Select value={sscChannel} onValueChange={setSscChannel}>
                      <SelectTrigger className="h-7 text-xs font-mono">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="VSSC1-H" className="text-xs">VSSC1-H (Violet)</SelectItem>
                        <SelectItem value="SSC-H" className="text-xs">SSC-H</SelectItem>
                        <SelectItem value="BSSC-H" className="text-xs">BSSC-H (Blue)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[10px] text-muted-foreground">Bead Kit</Label>
                    <Select value={selectedKit || "nanovis_d03231.json"} onValueChange={setSelectedKit}>
                      <SelectTrigger className="h-7 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {beadStandards.map((std) => (
                          <SelectItem key={std.filename} value={std.filename} className="text-xs">
                            {std.product_name || std.filename}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              {/* ── STEP 3: Auto-Calibrate Button ── */}
              <Button
                className="w-full h-10 text-sm gap-2 font-medium"
                onClick={handleAutoCalibrate}
                disabled={autoCalibrating || !hasBeadFcsFiles}
              >
                {autoCalibrating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Zap className="h-4 w-4" />
                )}
                {autoCalibrating
                  ? "Analyzing bead files & calibrating..."
                  : !hasBeadFcsFiles
                  ? "Upload bead FCS files to continue"
                  : `Auto-Calibrate from ${uploadedBeadFcsFiles.length} FCS file${uploadedBeadFcsFiles.length > 1 ? "s" : ""}`}
              </Button>

              {/* Auto-calibrate result summary */}
              {autoCalResult?.success && (
                <div className="rounded border border-green-200 bg-green-50/50 dark:bg-green-950/20 dark:border-green-900 p-2 space-y-1">
                  <div className="flex items-center gap-1.5 text-[11px] font-medium text-green-700">
                    <CheckCircle2 className="h-3 w-3" />
                    {autoCalResult.message}
                  </div>
                  <div className="text-[10px] text-muted-foreground space-y-0.5">
                    <div>
                      Certificate populations: {autoCalResult.calibration_summary?.certificate?.total_populations ?? "-"} (unique diameters: {autoCalResult.calibration_summary?.certificate?.unique_diameters ?? "-"})
                    </div>
                    <div>
                      Candidate beads from run: {autoCalResult.calibration_summary?.selection?.candidate_unique_beads ?? "-"} → Final used: {autoCalResult.calibration_summary?.selection?.final_beads_used ?? autoCalResult.n_beads ?? "-"}
                    </div>
                    <div>
                      Final diameter coverage: {autoCalResult.calibration_summary?.selection?.final_diameter_range_nm?.[0] ?? "-"}nm to {autoCalResult.calibration_summary?.selection?.final_diameter_range_nm?.[1] ?? "-"}nm
                    </div>
                    <div>
                      Run consistency thresholds: file-level CV ≤ {autoCalResult.calibration_summary?.thresholds?.subset_consistency_max_cv_pct ?? "-"}% and final CV ≤ {autoCalResult.calibration_summary?.thresholds?.final_consistency_target_cv_pct ?? "-"}%
                    </div>
                  </div>
                  {!!autoCalResult.calibration_summary?.selection?.coverage_warning && (
                    <div className="text-[10px] text-amber-600">
                      {autoCalResult.calibration_summary.selection.coverage_warning}
                    </div>
                  )}
                  {autoCalResult.per_file_results?.map((r, i) => (
                    <div key={i} className="text-[10px] flex items-center gap-1">
                      {r.success ? (
                        <Check className="h-2.5 w-2.5 text-green-600" />
                      ) : (
                        <XCircle className="h-2.5 w-2.5 text-red-500" />
                      )}
                      <span className="font-mono">{r.sample_id}</span>
                      {r.success ? (
                        <span className="text-muted-foreground">
                          — {r.n_beads_matched} matched
                          {typeof r.expected_beads === "number" ? ` / ${r.expected_beads} expected` : ""}
                          {typeof r.detected_peaks === "number" ? `, ${r.detected_peaks} peaks detected` : ""}
                          {typeof r.run_k_cv_pct === "number" ? `, run CV ${r.run_k_cv_pct.toFixed(1)}%` : ""}
                        </span>
                      ) : (
                        <span className="text-red-500">
                          — {r.error}
                          {typeof r.run_k_cv_pct === "number" ? ` (run CV ${r.run_k_cv_pct.toFixed(1)}% > ${r.subset_consistency_threshold_pct ?? "?"}%)` : ""}
                        </span>
                      )}
                    </div>
                  ))}
                  {!!autoCalResult.calibration_summary?.selection?.outliers_removed?.length && (
                    <div className="text-[10px] text-amber-600 space-y-0.5">
                      {autoCalResult.calibration_summary.selection.outliers_removed.map((o, idx) => (
                        <div key={idx}>
                          Outlier removed: {o.diameter_nm}nm (k={o.run_k_value}, median k={o.k_median})
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {hasBeadFcsFiles && (
                <p className="text-[10px] text-muted-foreground text-center">
                  The system will detect bead peaks in the FCS files, match them to known sizes from the datasheet, and fit FCMPASS calibration automatically.
                </p>
              )}
            </div>

            <Separator />

            {/* ════════════════════════════════════════════════════════════
                SECTION 3: MANUAL ENTRY (Alternative to auto-calibrate)
                ════════════════════════════════════════════════════════════ */}

            <Collapsible>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="sm" className="w-full justify-between text-[11px] text-muted-foreground hover:bg-muted/50 h-7">
                  <span className="flex items-center gap-1.5">
                    <Target className="h-3 w-3" />
                    Manual Bead Data Entry
                  </span>
                  <ChevronDown className="h-3 w-3" />
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="space-y-3 pt-2">
                <p className="text-[10px] text-muted-foreground">
                  If auto-calibration doesn&apos;t work, enter bead diameter and measured scatter AU values manually.
                </p>

                {/* Upload CSV of bead data points */}
                <div className="rounded-md border border-dashed p-2 space-y-1.5">
                  <input
                    ref={beadCsvInputRef}
                    type="file"
                    accept=".csv,.tsv,.txt"
                    className="hidden"
                    onChange={handleBeadDatasheetUpload}
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full h-7 text-[11px] gap-1.5"
                    onClick={() => beadCsvInputRef.current?.click()}
                  >
                    <Upload className="h-3 w-3" />
                    Import from CSV (diameter_nm, mean_au)
                  </Button>
                </div>

                {/* Manual data rows */}
                <div className="space-y-1">
                  <div className="flex items-center gap-1.5 text-[9px] text-muted-foreground font-medium px-0.5">
                    <div className="flex-1">Diameter (nm)</div>
                    <div className="flex-1">Mean Scatter AU</div>
                    <div className="w-7" />
                  </div>
                  {manualRows.map((row) => (
                    <div key={row.id} className="flex items-center gap-1.5">
                      <Input type="number" placeholder="e.g. 100" value={row.diameter_nm}
                        onChange={(e) => updateManualRow(row.id, "diameter_nm", e.target.value)}
                        className="h-7 text-xs flex-1 font-mono" />
                      <Input type="number" placeholder="e.g. 1250" value={row.mean_ssc}
                        onChange={(e) => updateManualRow(row.id, "mean_ssc", e.target.value)}
                        className="h-7 text-xs flex-1 font-mono" />
                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0 shrink-0"
                        onClick={() => removeManualRow(row.id)} disabled={manualRows.length <= 2}>
                        <Minus className="h-3 w-3" />
                      </Button>
                    </div>
                  ))}
                  <Button variant="outline" size="sm" className="h-6 text-[10px] w-full gap-1" onClick={addManualRow}>
                    <Plus className="h-3 w-3" /> Add Row
                  </Button>
                </div>

                <Button className="w-full h-8 text-xs gap-1.5" onClick={handleFcmpassManualFit}
                  disabled={fitting || filledRows < 2}>
                  {fitting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Target className="h-3 w-3" />}
                  {fitting ? "Calibrating..." : filledRows < 2 ? "Enter at least 2 points" : `Apply Manual Calibration (${filledRows} beads)`}
                </Button>
              </CollapsibleContent>
            </Collapsible>

            {/* ════════════════════════════════════════════════════════════
                SECTION 4: ADVANCED OPTIONS (collapsed)
                ════════════════════════════════════════════════════════════ */}

            <Collapsible>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="sm" className="w-full justify-between text-[11px] text-muted-foreground hover:bg-muted/50 h-7">
                  <span className="flex items-center gap-1.5">
                    <Info className="h-3 w-3" />
                    Advanced Options
                  </span>
                  <ChevronDown className="h-3 w-3" />
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="space-y-3 pt-2">

                {/* Physics Parameters */}
                <div className="rounded-md border p-2.5 space-y-2">
                  <Label className="text-[11px] font-medium">Physics Parameters</Label>
                  <p className="text-[10px] text-muted-foreground">
                    Defaults work for PS beads in PBS at 405nm.
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <Label className="text-[10px] text-muted-foreground">EV RI</Label>
                      <Input type="number" step="0.01" value={evRI} onChange={(e) => setEvRI(e.target.value)} className="h-7 text-xs font-mono" />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-[10px] text-muted-foreground">Wavelength</Label>
                      <Select value={fcmpassWavelength} onValueChange={setFcmpassWavelength}>
                        <SelectTrigger className="h-7 text-xs font-mono"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="405" className="text-xs">405 nm (Violet)</SelectItem>
                          <SelectItem value="488" className="text-xs">488 nm (Blue)</SelectItem>
                          <SelectItem value="532" className="text-xs">532 nm (Green)</SelectItem>
                          <SelectItem value="640" className="text-xs">640 nm (Red)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-[10px] text-muted-foreground">Bead RI</Label>
                      <Input type="number" step="0.001" value={fcmpassBeadRI} onChange={(e) => setFcmpassBeadRI(e.target.value)} className="h-7 text-xs font-mono" />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-[10px] text-muted-foreground">Medium RI</Label>
                      <Input type="number" step="0.001" value={fcmpassMediumRI} onChange={(e) => setFcmpassMediumRI(e.target.value)} className="h-7 text-xs font-mono" />
                    </div>
                  </div>
                  <div className="flex items-center gap-2 pt-1">
                    <Switch id="dispersion-toggle" checked={useDispersion} onCheckedChange={setUseDispersion} />
                    <Label htmlFor="dispersion-toggle" className="text-[10px] text-muted-foreground cursor-pointer">
                      Use Cauchy dispersion for bead RI
                    </Label>
                  </div>
                </div>

                {/* Past Calibrations */}
                <Collapsible open={showCalLibrary} onOpenChange={setShowCalLibrary}>
                  <CollapsibleTrigger asChild>
                    <Button variant="ghost" size="sm" className="w-full justify-between text-[11px] font-medium text-muted-foreground hover:bg-muted/50 h-7">
                      <span className="flex items-center gap-1.5">
                        <Library className="h-3 w-3" />
                        Past Calibrations
                        {calLibrary.length > 0 && <Badge variant="secondary" className="text-[10px] px-1 py-0 h-4">{calLibrary.length}</Badge>}
                      </span>
                      {showCalLibrary ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                    </Button>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="space-y-2 pt-1">
                    {calLibraryLoading ? (
                      <div className="flex items-center justify-center py-3"><Loader2 className="h-3 w-3 animate-spin mr-2" /><span className="text-[11px] text-muted-foreground">Loading...</span></div>
                    ) : calLibrary.length === 0 ? (
                      <p className="text-center py-3 text-[11px] text-muted-foreground">No saved calibrations.</p>
                    ) : (
                      <div className="rounded border overflow-hidden">
                        <table className="w-full text-[11px]">
                          <thead className="bg-muted/50">
                            <tr>
                              <th className="px-2 py-1 text-left font-medium">Date</th>
                              <th className="px-2 py-1 text-right font-medium">k</th>
                              <th className="px-2 py-1 text-right font-medium">CV%</th>
                              <th className="px-2 py-1 text-center font-medium">Status</th>
                              <th className="px-2 py-1 text-right font-medium"></th>
                            </tr>
                          </thead>
                          <tbody>
                            {calLibrary.map((cal) => (
                              <tr key={cal.id} className={`border-t border-border/50 ${cal.is_active ? "bg-green-500/5" : ""}`}>
                                <td className="px-2 py-1 font-mono">{cal.created_at ? new Date(cal.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "—"}</td>
                                <td className="px-2 py-1 text-right font-mono">{cal.k_instrument?.toFixed(1)}</td>
                                <td className="px-2 py-1 text-right font-mono">{cal.k_cv_pct?.toFixed(1)}%</td>
                                <td className="px-2 py-1 text-center">
                                  {cal.is_active ? <Badge className="text-[9px] px-1 py-0 h-3.5 bg-green-600/20 text-green-600 border-green-600/30">Active</Badge> : <Badge variant="outline" className="text-[9px] px-1 py-0 h-3.5">Archived</Badge>}
                                </td>
                                <td className="px-2 py-1 text-right">
                                  {!cal.is_active && (
                                    <div className="flex justify-end gap-1">
                                      <Button variant="ghost" size="icon" className="h-5 w-5" disabled={calLibraryActivating === cal.id} onClick={() => handleActivateCalibration(cal.id)}>
                                        {calLibraryActivating === cal.id ? <Loader2 className="h-2.5 w-2.5 animate-spin" /> : <RotateCcw className="h-2.5 w-2.5" />}
                                      </Button>
                                      <Button variant="ghost" size="icon" className="h-5 w-5 text-destructive" disabled={calLibraryDeleting === cal.id} onClick={() => handleDeleteCalibration(cal.id)}>
                                        {calLibraryDeleting === cal.id ? <Loader2 className="h-2.5 w-2.5 animate-spin" /> : <Trash2 className="h-2.5 w-2.5" />}
                                      </Button>
                                    </div>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </CollapsibleContent>
                </Collapsible>

                {/* Custom Bead Kit */}
                <Button variant="ghost" size="sm" className="w-full justify-start text-[11px] text-muted-foreground hover:bg-muted/50 h-7 gap-1.5" onClick={() => setShowCustomKitDialog(true)}>
                  <Plus className="h-3 w-3" /> Define Custom Bead Kit
                </Button>
              </CollapsibleContent>
            </Collapsible>

          </CardContent>
        </CollapsibleContent>
      </Collapsible>

      {/* ── Custom Bead Kit Dialog ── */}
      <Dialog open={showCustomKitDialog} onOpenChange={setShowCustomKitDialog}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-base">Add Custom Bead Kit</DialogTitle>
            <DialogDescription className="text-xs">
              Enter your bead standard datasheet details. The kit will be saved and available
              for calibration in both FCMPASS and legacy modes.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Kit Identity */}
            <div className="space-y-2">
              <Label className="text-xs font-medium">Kit Information</Label>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1 col-span-2">
                  <Label className="text-[11px] text-muted-foreground">Product Name *</Label>
                  <Input
                    placeholder="e.g. MegaMix-Plus SSC"
                    value={customKitName}
                    onChange={(e) => setCustomKitName(e.target.value)}
                    className="h-8 text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-[11px] text-muted-foreground">Manufacturer</Label>
                  <Input
                    placeholder="e.g. Beckman Coulter"
                    value={customKitManufacturer}
                    onChange={(e) => setCustomKitManufacturer(e.target.value)}
                    className="h-8 text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-[11px] text-muted-foreground">Part Number</Label>
                  <Input
                    placeholder="e.g. 7803"
                    value={customKitPartNumber}
                    onChange={(e) => setCustomKitPartNumber(e.target.value)}
                    className="h-8 text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-[11px] text-muted-foreground">Lot Number</Label>
                  <Input
                    placeholder="From certificate"
                    value={customKitLotNumber}
                    onChange={(e) => setCustomKitLotNumber(e.target.value)}
                    className="h-8 text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-[11px] text-muted-foreground">Material</Label>
                  <Select value={customKitMaterial} onValueChange={setCustomKitMaterial}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="polystyrene_latex" className="text-xs">Polystyrene (PS)</SelectItem>
                      <SelectItem value="silica" className="text-xs">Silica (SiO₂)</SelectItem>
                      <SelectItem value="pmma" className="text-xs">PMMA</SelectItem>
                      <SelectItem value="other" className="text-xs">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {/* Optical Properties */}
            <div className="space-y-2">
              <Label className="text-xs font-medium">Optical Properties</Label>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <Label className="text-[11px] text-muted-foreground">Refractive Index</Label>
                  <Input
                    type="number"
                    step="0.001"
                    value={customKitRI}
                    onChange={(e) => setCustomKitRI(e.target.value)}
                    className="h-8 text-xs font-mono"
                  />
                </div>
                <div className="flex items-end gap-2 pb-1">
                  <div className="flex items-center gap-2">
                    <Switch
                      id="nist-toggle"
                      checked={customKitNistTraceable}
                      onCheckedChange={setCustomKitNistTraceable}
                    />
                    <Label htmlFor="nist-toggle" className="text-[11px] text-muted-foreground cursor-pointer">
                      NIST-traceable
                    </Label>
                  </div>
                </div>
              </div>
            </div>

            <Separator />

            {/* Bead Populations */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-xs font-medium">Bead Populations *</Label>
                <span className="text-[10px] text-muted-foreground">{customKitBeads.length} sizes</span>
              </div>

              {/* Header row */}
              <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground font-medium px-0.5">
                <div className="flex-[1.2]">Label</div>
                <div className="flex-1">Diameter (nm)</div>
                <div className="flex-[0.7]">CV%</div>
                <div className="w-7" />
              </div>

              {customKitBeads.map((bead) => (
                <div key={bead.id} className="flex items-center gap-1.5">
                  <Input
                    placeholder="e.g. 100nm"
                    value={bead.label}
                    onChange={(e) => updateCustomKitBead(bead.id, "label", e.target.value)}
                    className="h-7 text-xs flex-[1.2]"
                  />
                  <Input
                    type="number"
                    placeholder="nm"
                    value={bead.diameter_nm}
                    onChange={(e) => updateCustomKitBead(bead.id, "diameter_nm", e.target.value)}
                    className="h-7 text-xs flex-1 font-mono"
                  />
                  <Input
                    type="number"
                    step="0.1"
                    placeholder="%"
                    value={bead.cv_pct}
                    onChange={(e) => updateCustomKitBead(bead.id, "cv_pct", e.target.value)}
                    className="h-7 text-xs flex-[0.7] font-mono"
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0 shrink-0"
                    onClick={() => removeCustomKitBead(bead.id)}
                    disabled={customKitBeads.length <= 1}
                  >
                    <Minus className="h-3 w-3" />
                  </Button>
                </div>
              ))}

              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs w-full gap-1"
                onClick={addCustomKitBead}
              >
                <Plus className="h-3 w-3" /> Add Bead Size
              </Button>
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              className="text-xs"
              onClick={() => { resetCustomKitForm(); setShowCustomKitDialog(false) }}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              className="text-xs gap-1.5"
              onClick={handleSaveCustomKit}
              disabled={customKitSaving || !customKitName.trim()}
            >
              {customKitSaving ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Upload className="h-3 w-3" />
              )}
              {customKitSaving ? "Saving..." : "Save Kit"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
