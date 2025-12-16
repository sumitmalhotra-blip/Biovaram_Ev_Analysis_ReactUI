"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { 
  Thermometer, ChevronDown, ChevronUp, Info,
  Droplets, Calculator
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAnalysisStore } from "@/lib/store"

// Media viscosity factors relative to water at 25°C
const MEDIA_VISCOSITY_FACTORS: Record<string, { factor: number; note: string }> = {
  "Water": { factor: 1.0, note: "Pure water reference" },
  "PBS": { factor: 1.02, note: "Phosphate buffered saline" },
  "DPBS": { factor: 1.02, note: "Dulbecco's PBS" },
  "HBSS": { factor: 1.01, note: "Hank's balanced salt solution" },
  "Cell Culture Medium": { factor: 1.05, note: "DMEM, RPMI, etc." },
  "Serum-Free Medium": { factor: 1.03, note: "Without FBS" },
  "10% FBS Medium": { factor: 1.08, note: "With 10% fetal bovine serum" },
  "Plasma": { factor: 1.8, note: "Human/animal plasma" },
  "Serum": { factor: 1.5, note: "Human/animal serum" },
}

// Calculate water viscosity at given temperature (in Pa·s)
function calculateWaterViscosity(tempC: number): number {
  // Vogel equation for water viscosity
  const A = 2.414e-5
  const B = 247.8
  const C = 140.0
  return A * Math.pow(10, B / (tempC + 273.15 - C))
}

// Get correction factor based on temperature and medium
function getCorrectionFactor(
  measurementTemp: number,
  referenceTemp: number,
  mediaType: string
): { factor: number; details: string } {
  const measVisc = calculateWaterViscosity(measurementTemp) * (MEDIA_VISCOSITY_FACTORS[mediaType]?.factor || 1.0)
  const refVisc = calculateWaterViscosity(referenceTemp)
  
  // Stokes-Einstein correction: size_corrected = size_measured * (visc_ref / visc_meas) * (T_meas / T_ref)
  const tempRatio = (measurementTemp + 273.15) / (referenceTemp + 273.15)
  const viscRatio = refVisc / measVisc
  const factor = viscRatio * tempRatio
  
  const details = `Viscosity ratio: ${viscRatio.toFixed(4)}, Temperature ratio: ${tempRatio.toFixed(4)}`
  
  return { factor, details }
}

// Stokes-Einstein Equation Display Component
interface StokesEinsteinEquationProps {
  measurementTemp: number
  referenceTemp: number
  mediaType: string
  correctionFactor: number
}

function StokesEinsteinEquation({ 
  measurementTemp, 
  referenceTemp, 
  mediaType, 
  correctionFactor 
}: StokesEinsteinEquationProps) {
  const measViscosity = calculateWaterViscosity(measurementTemp) * (MEDIA_VISCOSITY_FACTORS[mediaType]?.factor || 1.0)
  const refViscosity = calculateWaterViscosity(referenceTemp)
  const kB = 1.380649e-23 // Boltzmann constant

  return (
    <div className="p-4 rounded-lg border bg-linear-to-br from-primary/5 to-accent/5 space-y-4">
      <h4 className="text-sm font-medium flex items-center gap-2">
        <Calculator className="h-4 w-4 text-primary" />
        Stokes-Einstein Equation
      </h4>
      
      {/* Main Equation Display */}
      <div className="p-4 bg-background/80 rounded-lg text-center space-y-3">
        <div className="text-lg font-mono">
          <span className="text-primary font-bold">D</span>
          <span className="text-muted-foreground"> = </span>
          <span className="inline-flex flex-col items-center mx-1">
            <span className="border-b border-foreground px-2">k<sub>B</sub>T</span>
            <span className="px-2">6πηr</span>
          </span>
        </div>
        
        <p className="text-xs text-muted-foreground">
          Diffusion coefficient relates to hydrodynamic diameter
        </p>
      </div>

      {/* Size Correction Formula */}
      <div className="p-4 bg-background/80 rounded-lg text-center space-y-3">
        <p className="text-xs text-muted-foreground mb-2">Temperature/Viscosity Correction:</p>
        <div className="text-base font-mono">
          <span className="text-emerald-500 font-bold">d<sub>corrected</sub></span>
          <span className="text-muted-foreground"> = d<sub>measured</sub> × </span>
          <span className="inline-flex flex-col items-center mx-1">
            <span className="border-b border-foreground px-2">η<sub>ref</sub></span>
            <span className="px-2">η<sub>meas</sub></span>
          </span>
          <span className="text-muted-foreground"> × </span>
          <span className="inline-flex flex-col items-center mx-1">
            <span className="border-b border-foreground px-2">T<sub>meas</sub></span>
            <span className="px-2">T<sub>ref</sub></span>
          </span>
        </div>
      </div>

      {/* Parameter Explanation */}
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold text-primary">D</span>
            <span className="text-muted-foreground">Diffusion coefficient (m²/s)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold">k<sub>B</sub></span>
            <span className="text-muted-foreground">Boltzmann constant</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold">T</span>
            <span className="text-muted-foreground">Temperature (K)</span>
          </div>
        </div>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold">η</span>
            <span className="text-muted-foreground">Dynamic viscosity (Pa·s)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold">r</span>
            <span className="text-muted-foreground">Hydrodynamic radius (m)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold">d</span>
            <span className="text-muted-foreground">Particle diameter (nm)</span>
          </div>
        </div>
      </div>

      {/* Current Values */}
      <div className="p-3 bg-secondary/30 rounded-lg">
        <p className="text-xs font-medium mb-2">Current Calculation Values:</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs font-mono">
          <div>
            <span className="text-muted-foreground">T<sub>meas</sub> = </span>
            <span className="text-foreground">{(measurementTemp + 273.15).toFixed(2)} K</span>
          </div>
          <div>
            <span className="text-muted-foreground">T<sub>ref</sub> = </span>
            <span className="text-foreground">{(referenceTemp + 273.15).toFixed(2)} K</span>
          </div>
          <div>
            <span className="text-muted-foreground">η<sub>meas</sub> = </span>
            <span className="text-foreground">{(measViscosity * 1000).toFixed(4)} mPa·s</span>
          </div>
          <div>
            <span className="text-muted-foreground">η<sub>ref</sub> = </span>
            <span className="text-foreground">{(refViscosity * 1000).toFixed(4)} mPa·s</span>
          </div>
        </div>
        <div className="mt-2 pt-2 border-t border-border/50">
          <span className="text-muted-foreground">Correction Factor = </span>
          <span className="text-primary font-bold">{correctionFactor.toFixed(6)}</span>
        </div>
      </div>

      {/* Scientific Context */}
      <p className="text-xs text-muted-foreground">
        <strong>Note:</strong> The Stokes-Einstein equation relates Brownian motion to particle size 
        through medium viscosity and temperature. NTA tracks particles to measure their diffusion 
        coefficient, which is then converted to hydrodynamic diameter. Temperature affects both 
        particle diffusion (faster at higher temps) and medium viscosity (lower at higher temps).
      </p>
    </div>
  )
}

export function NTATemperatureSettings() {
  const { ntaAnalysisSettings, setNtaAnalysisSettings } = useAnalysisStore()
  
  const [isOpen, setIsOpen] = useState(false)
  const [showViscosityTable, setShowViscosityTable] = useState(false)
  
  // Initialize with defaults or stored values
  const [applyCorrection, setApplyCorrection] = useState(
    ntaAnalysisSettings?.applyTemperatureCorrection ?? false
  )
  const [measurementTemp, setMeasurementTemp] = useState(
    ntaAnalysisSettings?.measurementTemp ?? 25.0
  )
  const [referenceTemp, setReferenceTemp] = useState(
    ntaAnalysisSettings?.referenceTemp ?? 25.0
  )
  const [mediaType, setMediaType] = useState(
    ntaAnalysisSettings?.mediaType ?? "Water"
  )

  // Calculate correction factor when settings change
  const { factor: correctionFactor, details: correctionDetails } = getCorrectionFactor(
    measurementTemp,
    referenceTemp,
    mediaType
  )

  // Update store when settings change
  useEffect(() => {
    if (applyCorrection) {
      setNtaAnalysisSettings({
        applyTemperatureCorrection: applyCorrection,
        measurementTemp,
        referenceTemp,
        mediaType,
        correctionFactor,
      })
    } else {
      setNtaAnalysisSettings({
        applyTemperatureCorrection: false,
        measurementTemp: 25,
        referenceTemp: 25,
        mediaType: "Water",
        correctionFactor: 1.0,
      })
    }
  }, [applyCorrection, measurementTemp, referenceTemp, mediaType, correctionFactor, setNtaAnalysisSettings])

  // Generate viscosity reference table
  const viscosityTable = []
  for (let temp = 15; temp <= 40; temp += 5) {
    viscosityTable.push({
      temp,
      viscosity_mPas: (calculateWaterViscosity(temp) * 1000).toFixed(4),
      viscosity_Pas: calculateWaterViscosity(temp).toFixed(6),
    })
  }

  return (
    <Card className="card-3d mb-4">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-secondary/30 transition-colors pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-orange-500/10">
                  <Thermometer className="h-4 w-4 text-orange-500" />
                </div>
                <CardTitle className="text-base">Temperature Correction</CardTitle>
                {applyCorrection && (
                  <Badge variant="outline" className="ml-2 text-xs">
                    Factor: {correctionFactor.toFixed(4)}
                  </Badge>
                )}
              </div>
              {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </div>
          </CardHeader>
        </CollapsibleTrigger>
        
        <CollapsibleContent>
          <CardContent className="space-y-6 pt-0">
            {/* Enable/Disable Toggle */}
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <Label className="font-medium">Apply Temperature Correction</Label>
                <p className="text-xs text-muted-foreground mt-1">
                  Apply Stokes-Einstein correction for temperature/viscosity differences
                </p>
              </div>
              <Switch
                checked={applyCorrection}
                onCheckedChange={setApplyCorrection}
              />
            </div>

            {applyCorrection && (
              <>
                {/* Measurement Conditions */}
                <div className="space-y-4">
                  <h4 className="text-sm font-medium flex items-center gap-2">
                    <Droplets className="h-4 w-4 text-muted-foreground" />
                    Measurement Conditions
                  </h4>
                  
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="measTemp">Measurement Temperature (°C)</Label>
                      <Input
                        id="measTemp"
                        type="number"
                        step="0.5"
                        min={10}
                        max={45}
                        value={measurementTemp}
                        onChange={(e) => setMeasurementTemp(parseFloat(e.target.value))}
                      />
                      <p className="text-xs text-muted-foreground">
                        Actual temperature during NTA measurement
                      </p>
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="refTemp">Reference Temperature (°C)</Label>
                      <Input
                        id="refTemp"
                        type="number"
                        step="0.5"
                        min={15}
                        max={40}
                        value={referenceTemp}
                        onChange={(e) => setReferenceTemp(parseFloat(e.target.value))}
                      />
                      <p className="text-xs text-muted-foreground">
                        Standard reference (typically 25°C)
                      </p>
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="media">Measurement Medium</Label>
                      <Select value={mediaType} onValueChange={setMediaType}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select medium" />
                        </SelectTrigger>
                        <SelectContent>
                          {Object.entries(MEDIA_VISCOSITY_FACTORS).map(([key, { note }]) => (
                            <SelectItem key={key} value={key}>
                              {key}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-muted-foreground">
                        {MEDIA_VISCOSITY_FACTORS[mediaType]?.note || "Select measurement medium"}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Correction Summary */}
                <div className="p-4 bg-secondary/30 rounded-lg space-y-3">
                  <h4 className="text-sm font-medium flex items-center gap-2">
                    <Calculator className="h-4 w-4 text-muted-foreground" />
                    Correction Summary
                  </h4>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-primary">
                        {correctionFactor.toFixed(4)}
                      </div>
                      <div className="text-xs text-muted-foreground">Correction Factor</div>
                    </div>
                    
                    <div className="text-center">
                      <div className="text-lg font-medium">
                        {((correctionFactor - 1) * 100).toFixed(1)}%
                      </div>
                      <div className="text-xs text-muted-foreground">Size Adjustment</div>
                    </div>
                    
                    <div className="text-center">
                      <div className="text-lg font-medium">
                        {(calculateWaterViscosity(measurementTemp) * (MEDIA_VISCOSITY_FACTORS[mediaType]?.factor || 1) * 1000).toFixed(3)}
                      </div>
                      <div className="text-xs text-muted-foreground">Medium Visc. (mPa·s)</div>
                    </div>
                    
                    <div className="text-center">
                      <div className="text-lg font-medium">
                        {MEDIA_VISCOSITY_FACTORS[mediaType]?.factor.toFixed(2) || "1.00"}x
                      </div>
                      <div className="text-xs text-muted-foreground">Media Factor</div>
                    </div>
                  </div>
                  
                  <p className="text-xs text-muted-foreground flex items-center gap-1">
                    <Info className="h-3 w-3" />
                    {correctionDetails}
                  </p>
                </div>

                {/* Viscosity Reference Table */}
                <Collapsible open={showViscosityTable} onOpenChange={setShowViscosityTable}>
                  <CollapsibleTrigger asChild>
                    <button className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                      {showViscosityTable ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                      📊 Viscosity Reference Table
                    </button>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="pt-3">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Temperature (°C)</TableHead>
                          <TableHead>Viscosity (mPa·s)</TableHead>
                          <TableHead>Viscosity (Pa·s)</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {viscosityTable.map((row) => (
                          <TableRow key={row.temp}>
                            <TableCell>{row.temp}</TableCell>
                            <TableCell>{row.viscosity_mPas}</TableCell>
                            <TableCell>{row.viscosity_Pas}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CollapsibleContent>
                </Collapsible>

                {/* Stokes-Einstein Equation Display */}
                <StokesEinsteinEquation 
                  measurementTemp={measurementTemp}
                  referenceTemp={referenceTemp}
                  mediaType={mediaType}
                  correctionFactor={correctionFactor}
                />
              </>
            )}

            {!applyCorrection && (
              <p className="text-sm text-muted-foreground p-3 bg-muted/30 rounded-lg">
                <Info className="h-4 w-4 inline-block mr-2" />
                Enable temperature correction to adjust particle sizes for temperature and viscosity 
                differences between measurement and reference conditions.
              </p>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
