"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { BookOpen, ChevronDown, ChevronUp, Wrench, Beaker, Focus, Thermometer, AlertCircle } from "lucide-react"
import { useState } from "react"

export function NTABestPracticesGuide() {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <Card className="card-3d border-purple-500/20">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-secondary/30 transition-colors pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-purple-500/10">
                  <BookOpen className="h-4 w-4 text-purple-500" />
                </div>
                <CardTitle className="text-base">NTA Best Practices Guide</CardTitle>
              </div>
              {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </div>
          </CardHeader>
        </CollapsibleTrigger>
        
        <CollapsibleContent>
          <CardContent className="pt-0">
            <Accordion type="multiple" className="w-full">
              {/* Machine Calibration */}
              <AccordionItem value="calibration">
                <AccordionTrigger className="text-sm font-medium">
                  <div className="flex items-center gap-2">
                    <Wrench className="h-4 w-4 text-cyan-500" />
                    Machine Calibration
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-3 text-sm text-muted-foreground">
                    <ul className="list-disc list-inside space-y-2">
                      <li>
                        <strong>Maintenance:</strong> Cell cleaning should be performed with <strong>100% acetone weekly</strong>
                      </li>
                      <li>
                        <strong>Alignment:</strong> Verify laser alignment monthly using calibration standards
                      </li>
                      <li>
                        <strong>Camera Focus:</strong> Adjust focus until particles appear as sharp dots with minimal blur
                      </li>
                      <li>
                        <strong>Temperature:</strong> Allow 30 minutes warm-up time for stable temperature readings
                      </li>
                    </ul>
                    <div className="p-3 bg-cyan-500/10 rounded-lg mt-2">
                      <p className="text-xs">
                        🔧 <strong>Tip:</strong> Keep a calibration log to track instrument performance over time
                      </p>
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Sample Preparation */}
              <AccordionItem value="sample-prep">
                <AccordionTrigger className="text-sm font-medium">
                  <div className="flex items-center gap-2">
                    <Beaker className="h-4 w-4 text-green-500" />
                    Sample Preparation
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-3 text-sm text-muted-foreground">
                    <ul className="list-disc list-inside space-y-2">
                      <li>
                        <strong>Filtration:</strong> All samples must be passed through a <strong>0.2 μm filter</strong>
                      </li>
                      <li>
                        <strong>Vortex:</strong> Vortex samples <strong>before dilution</strong> to resuspend particles
                      </li>
                      <li>
                        <strong>Dilution:</strong> Optimal number of particles per frame should be <strong>50-100</strong>
                      </li>
                      <li>
                        <strong>Buffer Options:</strong>
                        <ul className="ml-4 mt-1 space-y-1">
                          <li>1️⃣ PBS pH 7.4 (fresh stock, filtered through 0.02 μm filter)</li>
                          <li>2️⃣ HPLC grade water (filtered through 0.02 μm filter)</li>
                        </ul>
                      </li>
                    </ul>
                    <div className="p-3 bg-green-500/10 rounded-lg mt-2">
                      <p className="text-xs">
                        ⚗️ <strong>Note:</strong> Avoid repeated freeze-thaw cycles which cause particle aggregation
                      </p>
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Capture Strategy */}
              <AccordionItem value="capture">
                <AccordionTrigger className="text-sm font-medium">
                  <div className="flex items-center gap-2">
                    <Focus className="h-4 w-4 text-purple-500" />
                    Capture Strategy
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-3 text-sm text-muted-foreground">
                    <ul className="list-disc list-inside space-y-2">
                      <li>
                        <strong>Cycles:</strong> Minimum of <strong>3 cycles</strong> for statistical accuracy
                      </li>
                      <li>
                        <strong>Positions:</strong> <strong>11 positions</strong> recommended for representative sampling
                      </li>
                      <li>
                        <strong>Frame Rate:</strong> 30 fps is standard; use 60 fps for fast-moving small particles
                      </li>
                      <li>
                        <strong>Duration:</strong> 30-60 seconds per position for adequate particle tracking
                      </li>
                      <li>
                        <strong>Temperature:</strong> Record exact measurement temperature for viscosity correction
                      </li>
                    </ul>
                    <div className="p-3 bg-purple-500/10 rounded-lg mt-2">
                      <p className="text-xs">
                        📹 <strong>Best Practice:</strong> Total analyzed particles should exceed 1000 for reliable statistics
                      </p>
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Temperature Considerations */}
              <AccordionItem value="temperature">
                <AccordionTrigger className="text-sm font-medium">
                  <div className="flex items-center gap-2">
                    <Thermometer className="h-4 w-4 text-orange-500" />
                    Temperature Considerations
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-3 text-sm text-muted-foreground">
                    <p>Temperature affects particle diffusion through viscosity changes:</p>
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      <div className="p-2 bg-secondary/30 rounded-lg text-center">
                        <p className="font-medium text-foreground">22°C</p>
                        <p className="text-xs">Standard lab temp</p>
                      </div>
                      <div className="p-2 bg-secondary/30 rounded-lg text-center">
                        <p className="font-medium text-foreground">25°C</p>
                        <p className="text-xs">Reference standard</p>
                      </div>
                      <div className="p-2 bg-secondary/30 rounded-lg text-center">
                        <p className="font-medium text-foreground">37°C</p>
                        <p className="text-xs">Physiological</p>
                      </div>
                      <div className="p-2 bg-secondary/30 rounded-lg text-center">
                        <p className="font-medium text-foreground">4°C</p>
                        <p className="text-xs">Cold storage</p>
                      </div>
                    </div>
                    <div className="p-3 bg-orange-500/10 rounded-lg mt-3">
                      <p className="text-xs">
                        🌡️ <strong>Important:</strong> Use Stokes-Einstein correction when measurement temp ≠ reference temp (25°C)
                      </p>
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Common Issues */}
              <AccordionItem value="issues">
                <AccordionTrigger className="text-sm font-medium">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-red-500" />
                    Common Issues
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-3 text-sm text-muted-foreground">
                    <div className="space-y-3">
                      <div className="p-3 bg-secondary/50 rounded-lg">
                        <p className="font-medium text-foreground mb-1">🔸 Too Many Particles (&gt;200/frame)</p>
                        <p className="text-xs">Dilute sample further; overlap causes tracking errors</p>
                      </div>
                      <div className="p-3 bg-secondary/50 rounded-lg">
                        <p className="font-medium text-foreground mb-1">🔸 Too Few Particles (&lt;20/frame)</p>
                        <p className="text-xs">Concentrate sample or increase video capture time</p>
                      </div>
                      <div className="p-3 bg-secondary/50 rounded-lg">
                        <p className="font-medium text-foreground mb-1">🔸 Aggregates Present</p>
                        <p className="text-xs">Re-vortex sample, filter again, or sonicate briefly</p>
                      </div>
                      <div className="p-3 bg-secondary/50 rounded-lg">
                        <p className="font-medium text-foreground mb-1">🔸 Drift in Tracking</p>
                        <p className="text-xs">Check for air bubbles, ensure sample chamber is sealed</p>
                      </div>
                      <div className="p-3 bg-secondary/50 rounded-lg">
                        <p className="font-medium text-foreground mb-1">🔸 Bimodal Distribution</p>
                        <p className="text-xs">May indicate heterogeneous sample or aggregation</p>
                      </div>
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
