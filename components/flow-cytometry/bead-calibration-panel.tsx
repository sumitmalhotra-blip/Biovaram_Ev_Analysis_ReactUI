"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Separator } from "@/components/ui/separator"
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
} from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { useAnalysisStore } from "@/lib/store"
import { apiClient, type CalibrationStatus, type BeadStandard, type ActiveCalibration } from "@/lib/api-client"
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
  const { apiSamples, apiConnected } = useAnalysisStore()

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

  // Fetch on mount
  useEffect(() => {
    fetchStatus()
    fetchBeadStandards()
  }, [fetchStatus, fetchBeadStandards])

  // Load full calibration when expanded
  useEffect(() => {
    if (expanded && calStatus?.calibrated) {
      fetchActiveCalibration()
    }
  }, [expanded, calStatus?.calibrated, fetchActiveCalibration])

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
      const result = await apiClient.removeCalibration()
      if (result?.success) {
        toast({
          title: "Calibration Removed",
          description: result.message || "Reverted to uncalibrated Mie theory.",
        })
        setCalStatus(null)
        setActiveCalibration(null)
        await fetchStatus()
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

  // ─── Manual Row Helpers ────────────────────────────────────────────

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

  // ─── FCS Samples List ──────────────────────────────────────────────

  const fcsSamples = apiSamples.filter((s) => s.files?.fcs)

  // ─── Calibration Status Badge ──────────────────────────────────────

  const isCalibrated = calStatus?.calibrated === true

  // ─── Render ────────────────────────────────────────────────────────

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
                    Calibrated
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                    <XCircle className="h-3 w-3 mr-0.5" />
                    Not Set
                  </Badge>
                )}
              </div>
              {expanded ? (
                <ChevronUp className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
            {isCalibrated && calStatus && (
              <p className="text-[10px] text-muted-foreground mt-1">
                {calStatus.bead_kit} | R²={calStatus.r_squared?.toFixed(4)} | {calStatus.n_bead_sizes} beads | {calStatus.calibration_range_nm?.[0]}-{calStatus.calibration_range_nm?.[1]}nm
              </p>
            )}
          </CardHeader>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <CardContent className="space-y-4 pt-0">
            {/* Info Alert */}
            <Alert className="border-blue-200 bg-blue-50 dark:bg-blue-950/20 dark:border-blue-900">
              <Info className="h-3.5 w-3.5 text-blue-500" />
              <AlertDescription className="text-xs text-blue-700 dark:text-blue-300">
                Bead calibration creates a transfer function from instrument scatter units
                to physical particle diameter using reference beads with known sizes (NIST-traceable).
                This provides more accurate sizing than raw Mie theory alone.
              </AlertDescription>
            </Alert>

            {/* ── Active Calibration Details ── */}
            {isCalibrated && activeCalibration?.calibrated && activeCalibration.calibration && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Active Calibration
                  </h4>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 text-xs text-destructive hover:text-destructive hover:bg-destructive/10 gap-1"
                    onClick={handleRemove}
                    disabled={loading}
                  >
                    {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
                    Remove
                  </Button>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-md border p-2">
                    <div className="text-muted-foreground">Fit Method</div>
                    <div className="font-medium capitalize">{activeCalibration.calibration.fit_method}</div>
                  </div>
                  <div className="rounded-md border p-2">
                    <div className="text-muted-foreground">Bead Sizes</div>
                    <div className="font-medium">{activeCalibration.calibration.n_bead_sizes}</div>
                  </div>
                  <div className="rounded-md border p-2">
                    <div className="text-muted-foreground">Wavelength</div>
                    <div className="font-medium">{activeCalibration.calibration.wavelength_nm}nm</div>
                  </div>
                  <div className="rounded-md border p-2">
                    <div className="text-muted-foreground">Range</div>
                    <div className="font-medium">
                      {activeCalibration.calibration.calibration_range_nm?.[0]}-{activeCalibration.calibration.calibration_range_nm?.[1]}nm
                    </div>
                  </div>
                </div>

                {/* Fit Parameters */}
                {activeCalibration.calibration.fit_params && (
                  <div className="rounded-md border p-2 text-xs">
                    <div className="text-muted-foreground mb-1">Transfer Function: SSC = a × d^b</div>
                    <div className="font-mono text-[11px]">
                      a = {activeCalibration.calibration.fit_params.a?.toExponential(4)},
                      b = {activeCalibration.calibration.fit_params.b?.toFixed(4)}
                      {activeCalibration.calibration.fit_params.r_squared !== undefined && (
                        <>, R² = {activeCalibration.calibration.fit_params.r_squared?.toFixed(5)}</>
                      )}
                    </div>
                  </div>
                )}

                {/* Calibration Curve Chart */}
                {expanded && activeCalibration.calibration.bead_points &&
                  activeCalibration.calibration.curve_points && (
                    <div className="rounded-md border p-2">
                      <div className="text-xs text-muted-foreground mb-2 font-medium">
                        Calibration Curve (Log-Log)
                      </div>
                      <ResponsiveContainer width="100%" height={200} minWidth={100}>
                        <ComposedChart margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                          <XAxis
                            dataKey="diameter_nm"
                            type="number"
                            scale="log"
                            domain={["auto", "auto"]}
                            tickFormatter={(v: number) => `${Math.round(v)}`}
                            tick={{ fontSize: 10 }}
                            label={{ value: "Diameter (nm)", position: "bottom", offset: -2, style: { fontSize: 10 } }}
                          />
                          <YAxis
                            dataKey="scatter_value"
                            type="number"
                            scale="log"
                            domain={["auto", "auto"]}
                            tick={{ fontSize: 10 }}
                            label={{ value: "SSC", angle: -90, position: "insideLeft", style: { fontSize: 10 } }}
                          />
                          <RechartsTooltip
                            contentStyle={{ fontSize: 11 }}
                            formatter={(value: number, name: string) => [
                              typeof value === "number" ? value.toFixed(1) : value,
                              name,
                            ]}
                          />
                          <Legend wrapperStyle={{ fontSize: 10 }} />
                          {/* Fitted curve line */}
                          <Line
                            data={activeCalibration.calibration.curve_points.map((p) => ({
                              diameter_nm: p.diameter_nm,
                              scatter_value: p.scatter_predicted,
                            }))}
                            dataKey="scatter_value"
                            stroke="hsl(var(--primary))"
                            strokeWidth={2}
                            dot={false}
                            name="Fitted Curve"
                            type="monotone"
                          />
                          {/* Measured bead points */}
                          <Scatter
                            data={activeCalibration.calibration.bead_points.map((p) => ({
                              diameter_nm: p.diameter_nm,
                              scatter_value: p.scatter_mean,
                            }))}
                            dataKey="scatter_value"
                            fill="hsl(var(--chart-1))"
                            name="Bead Standards"
                            shape="circle"
                          />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  )}

                {/* Bead Points Table */}
                {activeCalibration.calibration.bead_points && (
                  <div className="rounded-md border overflow-hidden">
                    <table className="w-full text-[11px]">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="px-2 py-1.5 text-left font-medium">Diameter (nm)</th>
                          <th className="px-2 py-1.5 text-right font-medium">Mean SSC</th>
                          <th className="px-2 py-1.5 text-right font-medium">CV%</th>
                          <th className="px-2 py-1.5 text-right font-medium">Events</th>
                        </tr>
                      </thead>
                      <tbody>
                        {activeCalibration.calibration.bead_points.map((bp, i) => (
                          <tr key={i} className="border-t border-border/50">
                            <td className="px-2 py-1 font-mono">{bp.diameter_nm}</td>
                            <td className="px-2 py-1 text-right font-mono">{bp.scatter_mean?.toFixed(1)}</td>
                            <td className="px-2 py-1 text-right font-mono">{bp.cv_pct?.toFixed(1)}%</td>
                            <td className="px-2 py-1 text-right font-mono">{bp.n_events?.toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                <Separator />
              </div>
            )}

            {/* ── New Calibration Section ── */}
            <div className="space-y-3">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                {isCalibrated ? "Update Calibration" : "Create Calibration"}
              </h4>

              {/* Auto-Fit Mode */}
              {!showManual && (
                <div className="space-y-3">
                  {/* Bead Kit Selection */}
                  <div className="space-y-1.5">
                    <Label className="text-xs">Bead Standard Kit</Label>
                    <Select value={selectedKit} onValueChange={setSelectedKit}>
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="Select bead kit..." />
                      </SelectTrigger>
                      <SelectContent>
                        {beadStandards.map((std) => (
                          <SelectItem key={std.filename} value={std.filename} className="text-xs">
                            {std.product_name || std.filename}
                            {std.n_bead_sizes > 0 && ` (${std.n_bead_sizes} sizes)`}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Bead FCS Sample Selection */}
                  <div className="space-y-1.5">
                    <Label className="text-xs">Bead FCS Sample</Label>
                    {fcsSamples.length === 0 ? (
                      <p className="text-[11px] text-muted-foreground italic">
                        No FCS samples found. Upload a bead measurement FCS file first.
                      </p>
                    ) : (
                      <Select value={selectedSampleId} onValueChange={setSelectedSampleId}>
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue placeholder="Select bead FCS file..." />
                        </SelectTrigger>
                        <SelectContent>
                          {fcsSamples.map((s) => (
                            <SelectItem key={s.sample_id} value={s.sample_id} className="text-xs">
                              {s.sample_id}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  </div>

                  {/* SSC Channel */}
                  <div className="space-y-1.5">
                    <Label className="text-xs">Scatter Channel</Label>
                    <Select value={sscChannel} onValueChange={setSscChannel}>
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="VSSC1-H" className="text-xs">VSSC1-H (Violet SSC)</SelectItem>
                        <SelectItem value="SSC-H" className="text-xs">SSC-H (Side Scatter)</SelectItem>
                        <SelectItem value="BSSC-H" className="text-xs">BSSC-H (Blue SSC)</SelectItem>
                        <SelectItem value="FSC-H" className="text-xs">FSC-H (Forward Scatter)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex gap-2">
                    <Button
                      className="flex-1 h-8 text-xs gap-1.5"
                      onClick={handleAutoFit}
                      disabled={fitting || !selectedSampleId || !selectedKit}
                    >
                      {fitting ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <Zap className="h-3 w-3" />
                      )}
                      Auto-Fit from FCS
                    </Button>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="outline"
                          className="h-8 text-xs"
                          onClick={() => setShowManual(true)}
                        >
                          Manual
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent side="bottom" className="text-xs">
                        Enter bead scatter values manually
                      </TooltipContent>
                    </Tooltip>
                  </div>
                </div>
              )}

              {/* Manual Fit Mode */}
              {showManual && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label className="text-xs font-medium">Manual Bead Data Entry</Label>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 text-xs"
                      onClick={() => setShowManual(false)}
                    >
                      Switch to Auto
                    </Button>
                  </div>

                  {/* Pre-fill from kit */}
                  {beadStandards.length > 0 && (
                    <div className="space-y-1.5">
                      <Label className="text-[11px] text-muted-foreground">Pre-fill diameters from kit</Label>
                      <div className="flex gap-1 flex-wrap">
                        {beadStandards.map((std) => (
                          <Button
                            key={std.filename}
                            variant="outline"
                            size="sm"
                            className="h-6 text-[10px] px-2"
                            onClick={() => prefillFromKit(std)}
                          >
                            {std.product_name || std.filename}
                          </Button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Manual Input Table */}
                  <div className="space-y-1.5">
                    {manualRows.map((row) => (
                      <div key={row.id} className="flex items-center gap-1.5">
                        <Input
                          type="number"
                          placeholder="Diameter (nm)"
                          value={row.diameter_nm}
                          onChange={(e) => updateManualRow(row.id, "diameter_nm", e.target.value)}
                          className="h-7 text-xs flex-1"
                        />
                        <Input
                          type="number"
                          placeholder="Mean SSC"
                          value={row.mean_ssc}
                          onChange={(e) => updateManualRow(row.id, "mean_ssc", e.target.value)}
                          className="h-7 text-xs flex-1"
                        />
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0 shrink-0"
                          onClick={() => removeManualRow(row.id)}
                          disabled={manualRows.length <= 2}
                        >
                          <Minus className="h-3 w-3" />
                        </Button>
                      </div>
                    ))}
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs w-full gap-1"
                      onClick={addManualRow}
                    >
                      <Plus className="h-3 w-3" /> Add Bead Size
                    </Button>
                  </div>

                  {/* RI Input */}
                  <div className="flex gap-2">
                    <div className="space-y-1 flex-1">
                      <Label className="text-[11px] text-muted-foreground">Bead RI</Label>
                      <Input
                        type="number"
                        step="0.001"
                        value={manualRI}
                        onChange={(e) => setManualRI(e.target.value)}
                        className="h-7 text-xs"
                      />
                    </div>
                    <div className="space-y-1 flex-1">
                      <Label className="text-[11px] text-muted-foreground">Kit Name</Label>
                      <Input
                        placeholder="Optional"
                        value={manualKitName}
                        onChange={(e) => setManualKitName(e.target.value)}
                        className="h-7 text-xs"
                      />
                    </div>
                  </div>

                  {/* Manual Fit Button */}
                  <Button
                    className="w-full h-8 text-xs gap-1.5"
                    onClick={handleManualFit}
                    disabled={fitting}
                  >
                    {fitting ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Target className="h-3 w-3" />
                    )}
                    Fit Manual Calibration
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
