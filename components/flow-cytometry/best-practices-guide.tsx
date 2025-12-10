"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { BookOpen, ChevronDown, ChevronUp, Beaker, Settings, FlaskConical, AlertTriangle, Ruler } from "lucide-react"
import { useState } from "react"

export function FCSBestPracticesGuide() {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <Card className="card-3d border-blue-500/20">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-secondary/30 transition-colors pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-blue-500/10">
                  <BookOpen className="h-4 w-4 text-blue-500" />
                </div>
                <CardTitle className="text-base">FCS Best Practices Guide</CardTitle>
              </div>
              {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </div>
          </CardHeader>
        </CollapsibleTrigger>
        
        <CollapsibleContent>
          <CardContent className="pt-0">
            <Accordion type="multiple" className="w-full">
              {/* Sample Preparation */}
              <AccordionItem value="sample-prep">
                <AccordionTrigger className="text-sm font-medium">
                  <div className="flex items-center gap-2">
                    <Beaker className="h-4 w-4 text-cyan-500" />
                    Sample Preparation
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-3 text-sm text-muted-foreground">
                    <ul className="list-disc list-inside space-y-2">
                      <li>
                        <strong>Buffer:</strong> Use filtered PBS (0.02 μm) or particle-free sheath fluid
                      </li>
                      <li>
                        <strong>Filtration:</strong> Filter samples through 0.22 μm filters to remove large debris
                      </li>
                      <li>
                        <strong>Dilution:</strong> Optimal event rate is 200-500 events/second to avoid coincidence
                      </li>
                      <li>
                        <strong>Temperature:</strong> Keep samples at 4°C until analysis; equilibrate to room temperature before running
                      </li>
                      <li>
                        <strong>Vortex:</strong> Gently vortex samples before dilution to resuspend aggregates
                      </li>
                    </ul>
                    <div className="p-3 bg-blue-500/10 rounded-lg mt-2">
                      <p className="text-xs">
                        💡 <strong>Tip:</strong> Run buffer-only controls first to establish background noise levels
                      </p>
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Acquisition Settings */}
              <AccordionItem value="acquisition">
                <AccordionTrigger className="text-sm font-medium">
                  <div className="flex items-center gap-2">
                    <Settings className="h-4 w-4 text-green-500" />
                    Acquisition Settings
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-3 text-sm text-muted-foreground">
                    <ul className="list-disc list-inside space-y-2">
                      <li>
                        <strong>Threshold:</strong> Set FSC threshold to minimize background noise while capturing small EVs
                      </li>
                      <li>
                        <strong>Flow Rate:</strong> Use the slowest flow rate available for maximum resolution
                      </li>
                      <li>
                        <strong>Event Count:</strong> Collect minimum 10,000 events for statistical significance
                      </li>
                      <li>
                        <strong>PMT Voltages:</strong> Optimize voltages using calibration beads before sample acquisition
                      </li>
                      <li>
                        <strong>Height vs Area:</strong> Use height channels (-H) for particle sizing analysis
                      </li>
                    </ul>
                    <div className="p-3 bg-green-500/10 rounded-lg mt-2">
                      <p className="text-xs">
                        ⚙️ <strong>Recommended:</strong> Record FSC-H, SSC-H, and all fluorescence height channels
                      </p>
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Controls & Calibration */}
              <AccordionItem value="controls">
                <AccordionTrigger className="text-sm font-medium">
                  <div className="flex items-center gap-2">
                    <FlaskConical className="h-4 w-4 text-purple-500" />
                    Controls & Calibration
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-3 text-sm text-muted-foreground">
                    <ul className="list-disc list-inside space-y-2">
                      <li>
                        <strong>Size Standards:</strong> Use silica or polystyrene beads of known sizes (100, 200, 500 nm)
                      </li>
                      <li>
                        <strong>Daily QC:</strong> Run calibration beads daily to monitor instrument performance
                      </li>
                      <li>
                        <strong>Buffer Control:</strong> Run particle-free buffer to establish noise baseline
                      </li>
                      <li>
                        <strong>Isotype Controls:</strong> Include for fluorescence gating if analyzing labeled EVs
                      </li>
                      <li>
                        <strong>Refractive Index:</strong> Use beads with similar RI to EVs (~1.38) for accurate sizing
                      </li>
                    </ul>
                    <div className="p-3 bg-purple-500/10 rounded-lg mt-2">
                      <p className="text-xs">
                        🔬 <strong>Note:</strong> Polystyrene beads (RI~1.59) will scatter differently than EVs (RI~1.38)
                      </p>
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Common Issues */}
              <AccordionItem value="troubleshooting">
                <AccordionTrigger className="text-sm font-medium">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-yellow-500" />
                    Common Issues & Troubleshooting
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-3 text-sm text-muted-foreground">
                    <div className="space-y-3">
                      <div className="p-3 bg-secondary/50 rounded-lg">
                        <p className="font-medium text-foreground mb-1">🔸 High Background Noise</p>
                        <p className="text-xs">Clean fluidics system, use fresh filtered buffer, check for air bubbles</p>
                      </div>
                      <div className="p-3 bg-secondary/50 rounded-lg">
                        <p className="font-medium text-foreground mb-1">🔸 Low Event Count</p>
                        <p className="text-xs">Increase sample concentration, lower threshold, check for aggregation</p>
                      </div>
                      <div className="p-3 bg-secondary/50 rounded-lg">
                        <p className="font-medium text-foreground mb-1">🔸 Swarm Detection</p>
                        <p className="text-xs">Dilute sample further - high concentration causes coincidence events</p>
                      </div>
                      <div className="p-3 bg-secondary/50 rounded-lg">
                        <p className="font-medium text-foreground mb-1">🔸 Clogging</p>
                        <p className="text-xs">Filter samples, clean sample line, run cleaning solution</p>
                      </div>
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Size Standards */}
              <AccordionItem value="standards">
                <AccordionTrigger className="text-sm font-medium">
                  <div className="flex items-center gap-2">
                    <Ruler className="h-4 w-4 text-orange-500" />
                    Size Standards & Reference
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-3 text-sm text-muted-foreground">
                    <p>Common reference bead sizes for EV characterization:</p>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="p-2 bg-secondary/30 rounded-lg text-center">
                        <p className="font-medium text-foreground">100 nm</p>
                        <p className="text-xs">Exosome reference</p>
                      </div>
                      <div className="p-2 bg-secondary/30 rounded-lg text-center">
                        <p className="font-medium text-foreground">200 nm</p>
                        <p className="text-xs">Small MV reference</p>
                      </div>
                      <div className="p-2 bg-secondary/30 rounded-lg text-center">
                        <p className="font-medium text-foreground">500 nm</p>
                        <p className="text-xs">Large MV reference</p>
                      </div>
                      <div className="p-2 bg-secondary/30 rounded-lg text-center">
                        <p className="font-medium text-foreground">1000 nm</p>
                        <p className="text-xs">Apoptotic body</p>
                      </div>
                    </div>
                    <div className="p-3 bg-orange-500/10 rounded-lg mt-2">
                      <p className="text-xs">
                        📏 <strong>ISEV 2023:</strong> Small EVs &lt;200nm, Medium EVs 200-500nm, Large EVs &gt;500nm
                      </p>
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
