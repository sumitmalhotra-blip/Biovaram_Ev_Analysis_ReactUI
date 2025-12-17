"use client"

import * as React from "react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Thermometer,
  Beaker,
  Droplets,
  Activity,
  Syringe,
  User,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { useApi } from "@/hooks/use-api"

// Experimental conditions interface - TASK-009
// Matches backend ExperimentalConditions model
export interface ExperimentalConditions {
  temperature_celsius?: number
  ph?: number
  substrate_buffer?: string
  custom_buffer?: string
  sample_volume_ul?: number
  dilution_factor?: number
  antibody_used?: string
  antibody_concentration_ug?: number
  incubation_time_min?: number
  sample_type?: string
  filter_size_um?: number
  operator: string
  notes?: string
}

// Common buffer options for EV experiments
const BUFFER_OPTIONS = [
  { value: "PBS", label: "PBS (Phosphate Buffered Saline)" },
  { value: "HEPES", label: "HEPES" },
  { value: "Tris-HCl", label: "Tris-HCl" },
  { value: "DMEM", label: "DMEM" },
  { value: "RPMI", label: "RPMI 1640" },
  { value: "MES", label: "MES" },
  { value: "MOPS", label: "MOPS" },
  { value: "Custom", label: "Custom (specify below)" },
]

interface ExperimentalConditionsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSave: (conditions: ExperimentalConditions) => void
  sampleType: "FCS" | "NTA"
  sampleId?: string
}

export function ExperimentalConditionsDialog({
  open,
  onOpenChange,
  onSave,
  sampleType,
  sampleId,
}: ExperimentalConditionsDialogProps) {
  const { toast } = useToast()
  const { saveExperimentalConditions } = useApi()
  
  // Form state
  const [temperature, setTemperature] = useState<string>("")
  const [buffer, setBuffer] = useState<string>("")
  const [customBuffer, setCustomBuffer] = useState<string>("")
  const [volume, setVolume] = useState<string>("")
  const [ph, setPh] = useState<string>("")
  const [incubationTime, setIncubationTime] = useState<string>("")
  const [antibodyDetails, setAntibodyDetails] = useState<string>("")
  const [operator, setOperator] = useState<string>("")
  const [notes, setNotes] = useState<string>("")
  
  // Saving state (TASK-009)
  const [isSaving, setIsSaving] = useState<boolean>(false)

  // Validation errors
  const [errors, setErrors] = useState<Record<string, string>>({})

  // Validate form
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    // Operator is required
    if (!operator.trim()) {
      newErrors.operator = "Operator name is required"
    }

    // Temperature validation
    if (temperature && (parseFloat(temperature) < -20 || parseFloat(temperature) > 100)) {
      newErrors.temperature = "Temperature must be between -20°C and 100°C"
    }

    // pH validation
    if (ph && (parseFloat(ph) < 0 || parseFloat(ph) > 14)) {
      newErrors.ph = "pH must be between 0 and 14"
    }

    // Volume validation
    if (volume && parseFloat(volume) <= 0) {
      newErrors.volume = "Volume must be greater than 0"
    }

    // Buffer validation
    if (buffer === "Custom" && !customBuffer.trim()) {
      newErrors.customBuffer = "Please specify custom buffer name"
    }

    // Incubation time validation
    if (incubationTime && parseFloat(incubationTime) < 0) {
      newErrors.incubationTime = "Incubation time cannot be negative"
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // Handle save - TASK-009: Save to backend API if sampleId is provided
  const handleSave = async () => {
    if (!validateForm()) {
      toast({
        title: "Validation Error",
        description: "Please fix the errors before saving.",
        variant: "destructive",
      })
      return
    }

    const conditions: ExperimentalConditions = {
      operator: operator.trim(),
    }

    // Add optional fields if provided
    if (temperature) {
      conditions.temperature_celsius = parseFloat(temperature)
    }

    if (buffer) {
      conditions.substrate_buffer = buffer === "Custom" ? customBuffer.trim() : buffer
      if (buffer === "Custom" && customBuffer.trim()) {
        conditions.custom_buffer = customBuffer.trim()
      }
    }

    if (volume) {
      conditions.sample_volume_ul = parseFloat(volume)
    }

    if (ph) {
      conditions.ph = parseFloat(ph)
    }

    if (incubationTime) {
      conditions.incubation_time_min = parseFloat(incubationTime)
    }

    if (antibodyDetails.trim()) {
      // Parse antibody details into used and concentration if possible
      // Format: "CD81 (1.0 µg)" or just "CD81"
      const antibodyMatch = antibodyDetails.match(/^([^(]+)(?:\s*\(\s*([\d.]+)\s*(?:µg|ug|μg)?\s*\))?$/i)
      if (antibodyMatch) {
        conditions.antibody_used = antibodyMatch[1].trim()
        if (antibodyMatch[2]) {
          conditions.antibody_concentration_ug = parseFloat(antibodyMatch[2])
        }
      } else {
        conditions.antibody_used = antibodyDetails.trim()
      }
    }

    if (notes.trim()) {
      conditions.notes = notes.trim()
    }

    // TASK-009: If sampleId is provided, try to save to backend API
    // If API fails (sample not in DB yet), fallback to local save
    if (sampleId) {
      setIsSaving(true)
      try {
        const result = await saveExperimentalConditions(sampleId, {
          operator: conditions.operator,
          temperature_celsius: conditions.temperature_celsius,
          ph: conditions.ph,
          substrate_buffer: conditions.substrate_buffer,
          custom_buffer: conditions.custom_buffer,
          sample_volume_ul: conditions.sample_volume_ul,
          incubation_time_min: conditions.incubation_time_min,
          antibody_used: conditions.antibody_used,
          antibody_concentration_ug: conditions.antibody_concentration_ug,
          notes: conditions.notes,
        })
        
        if (result) {
          // Also call onSave for local state if needed
          onSave(conditions)
          handleReset()
          onOpenChange(false)
        } else {
          // API returned null (failed) - save locally instead
          onSave(conditions)
          toast({
            title: "Conditions Saved Locally",
            description: "Saved to session. Will sync to database when sample is available.",
          })
          handleReset()
          onOpenChange(false)
        }
      } catch {
        // Error toast is shown by the API hook - also save locally as fallback
        onSave(conditions)
        toast({
          title: "Saved Locally",
          description: "Conditions saved to session (database sync failed).",
        })
        handleReset()
        onOpenChange(false)
      } finally {
        setIsSaving(false)
      }
    } else {
      // No sampleId - just use local callback
      onSave(conditions)
      
      toast({
        title: "Conditions Saved",
        description: "Experimental conditions have been saved locally.",
      })

      handleReset()
      onOpenChange(false)
    }
  }

  // Handle skip
  const handleSkip = () => {
    onOpenChange(false)
    handleReset()
    
    toast({
      title: "Skipped",
      description: "You can add experimental conditions later if needed.",
      variant: "default",
    })
  }

  // Reset form
  const handleReset = () => {
    setTemperature("")
    setBuffer("")
    setCustomBuffer("")
    setVolume("")
    setPh("")
    setIncubationTime("")
    setAntibodyDetails("")
    setOperator("")
    setNotes("")
    setErrors({})
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] md:max-h-[85vh] overflow-y-auto w-[calc(100%-2rem)] md:w-full">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <FileText className="h-5 w-5 text-blue-500" />
            Experimental Conditions
          </DialogTitle>
          <DialogDescription>
            Capture important experimental metadata for your {sampleType} analysis.
            This information helps ensure reproducibility and proper interpretation of results.
            {sampleId && (
              <Badge variant="outline" className="mt-2 inline-block">
                Sample: {sampleId}
              </Badge>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Alert for required fields */}
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Fields marked with <span className="text-red-500">*</span> are required.
              All other fields are optional but recommended for complete documentation.
            </AlertDescription>
          </Alert>

          {/* Operator (Required) */}
          <div className="space-y-2">
            <Label htmlFor="operator" className="flex items-center gap-2">
              <User className="h-4 w-4 text-blue-500" />
              Operator Name <span className="text-red-500">*</span>
            </Label>
            <Input
              id="operator"
              placeholder="Enter operator name"
              value={operator}
              onChange={(e) => setOperator(e.target.value)}
              className={errors.operator ? "border-red-500" : ""}
            />
            {errors.operator && (
              <p className="text-sm text-red-500">{errors.operator}</p>
            )}
          </div>

          {/* Temperature */}
          <div className="space-y-2">
            <Label htmlFor="temperature" className="flex items-center gap-2">
              <Thermometer className="h-4 w-4 text-orange-500" />
              Temperature (°C)
            </Label>
            <Input
              id="temperature"
              type="number"
              placeholder="e.g., 4 (storage) or 20-25 (RT)"
              value={temperature}
              onChange={(e) => setTemperature(e.target.value)}
              step="0.1"
              className={errors.temperature ? "border-red-500" : ""}
            />
            {errors.temperature && (
              <p className="text-sm text-red-500">{errors.temperature}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Common: 4°C (storage), 20-25°C (room temperature), 37°C (physiological)
            </p>
          </div>

          {/* Buffer Selection */}
          <div className="space-y-2">
            <Label htmlFor="buffer" className="flex items-center gap-2">
              <Beaker className="h-4 w-4 text-cyan-500" />
              Substrate Buffer
            </Label>
            <Select value={buffer} onValueChange={setBuffer}>
              <SelectTrigger id="buffer">
                <SelectValue placeholder="Select buffer type" />
              </SelectTrigger>
              <SelectContent>
                {BUFFER_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Custom buffer input */}
            {buffer === "Custom" && (
              <div className="mt-2">
                <Input
                  placeholder="Specify custom buffer"
                  value={customBuffer}
                  onChange={(e) => setCustomBuffer(e.target.value)}
                  className={errors.customBuffer ? "border-red-500" : ""}
                />
                {errors.customBuffer && (
                  <p className="text-sm text-red-500">{errors.customBuffer}</p>
                )}
              </div>
            )}
          </div>

          {/* Sample Volume */}
          <div className="space-y-2">
            <Label htmlFor="volume" className="flex items-center gap-2">
              <Droplets className="h-4 w-4 text-blue-500" />
              Sample Volume (μL)
            </Label>
            <Input
              id="volume"
              type="number"
              placeholder="e.g., 20-100"
              value={volume}
              onChange={(e) => setVolume(e.target.value)}
              step="0.1"
              className={errors.volume ? "border-red-500" : ""}
            />
            {errors.volume && (
              <p className="text-sm text-red-500">{errors.volume}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Typical range: 20-100 μL for flow cytometry
            </p>
          </div>

          {/* pH */}
          <div className="space-y-2">
            <Label htmlFor="ph" className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-green-500" />
              pH
            </Label>
            <Input
              id="ph"
              type="number"
              placeholder="e.g., 7.4"
              value={ph}
              onChange={(e) => setPh(e.target.value)}
              step="0.1"
              className={errors.ph ? "border-red-500" : ""}
            />
            {errors.ph && (
              <p className="text-sm text-red-500">{errors.ph}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Physiological pH: 7.35-7.45
            </p>
          </div>

          {/* Incubation Time */}
          <div className="space-y-2">
            <Label htmlFor="incubation" className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-purple-500" />
              Incubation Time (minutes)
            </Label>
            <Input
              id="incubation"
              type="number"
              placeholder="e.g., 30"
              value={incubationTime}
              onChange={(e) => setIncubationTime(e.target.value)}
              step="1"
              className={errors.incubationTime ? "border-red-500" : ""}
            />
            {errors.incubationTime && (
              <p className="text-sm text-red-500">{errors.incubationTime}</p>
            )}
          </div>

          {/* Antibody Details */}
          {sampleType === "FCS" && (
            <div className="space-y-2">
              <Label htmlFor="antibody" className="flex items-center gap-2">
                <Syringe className="h-4 w-4 text-pink-500" />
                Antibody Details
              </Label>
              <Textarea
                id="antibody"
                placeholder="e.g., Anti-CD81-PE (Clone 5A6, 1:100 dilution)"
                value={antibodyDetails}
                onChange={(e) => setAntibodyDetails(e.target.value)}
                rows={2}
              />
              <p className="text-xs text-muted-foreground">
                Include antibody name, clone, fluorophore, and dilution if applicable
              </p>
            </div>
          )}

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes" className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-gray-500" />
              Additional Notes
            </Label>
            <Textarea
              id="notes"
              placeholder="Any additional observations or experimental details..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={handleSkip}
            disabled={isSaving}
          >
            Skip for Now
          </Button>
          <Button
            type="button"
            onClick={handleSave}
            className="gap-2"
            disabled={isSaving}
          >
            {isSaving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4" />
                Save & Continue
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
