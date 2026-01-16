"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  FileText, 
  BarChart3, 
  Hash, 
  TrendingUp, 
  Ruler, 
  Activity,
  CheckCircle,
  AlertTriangle,
  Layers
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { FCSResult } from "@/lib/api-client"

interface IndividualFileSummaryProps {
  primaryFile: {
    fileName?: string
    sampleId?: string
    results: FCSResult | null
  }
  secondaryFile?: {
    fileName?: string
    sampleId?: string
    results: FCSResult | null
  }
}

function FileSummaryCard({ 
  fileName, 
  sampleId, 
  results,
  variant = "primary"
}: { 
  fileName?: string
  sampleId?: string
  results: FCSResult | null
  variant?: "primary" | "secondary"
}) {
  if (!results) {
    return (
      <Card className={cn(
        "card-3d",
        variant === "secondary" && "border-orange-500/30"
      )}>
        <CardContent className="p-6 text-center text-muted-foreground">
          No analysis results available
        </CardContent>
      </Card>
    )
  }

  // Extract statistics from results
  const totalEvents = results.total_events || results.event_count || 0
  const medianSize = results.particle_size_median_nm || results.size_statistics?.d50
  const fscMedian = results.fsc_median
  const sscMedian = results.ssc_median
  const debrisPct = results.debris_pct
  const sizeStdDev = results.size_statistics?.std
  const d10 = results.size_statistics?.d10
  const d50 = results.size_statistics?.d50
  const d90 = results.size_statistics?.d90

  // Determine quality status
  const qualityStatus = (() => {
    if (totalEvents < 5000) return { label: "Low Count", color: "amber", icon: AlertTriangle }
    if (debrisPct && debrisPct > 20) return { label: "High Debris", color: "destructive", icon: AlertTriangle }
    if (debrisPct && debrisPct > 10) return { label: "Fair", color: "amber", icon: AlertTriangle }
    return { label: "Good", color: "emerald", icon: CheckCircle }
  })()

  const QualityIcon = qualityStatus.icon

  return (
    <Card className={cn(
      "card-3d",
      variant === "secondary" && "border-orange-500/30"
    )}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={cn(
              "p-2 rounded-xl shadow-lg",
              variant === "primary" 
                ? "bg-linear-to-br from-primary/20 to-accent/20"
                : "bg-linear-to-br from-orange-500/20 to-amber-500/20"
            )}>
              {variant === "primary" ? (
                <FileText className="h-5 w-5 text-primary" />
              ) : (
                <Layers className="h-5 w-5 text-orange-500" />
              )}
            </div>
            <div>
              <CardTitle className="text-base">
                {variant === "primary" ? "Primary File" : "Comparison File"}
              </CardTitle>
              <CardDescription className="text-xs truncate max-w-[200px]">
                {fileName || sampleId || "Unknown file"}
              </CardDescription>
            </div>
          </div>
          <Badge 
            variant="outline" 
            className={cn(
              qualityStatus.color === "emerald" && "bg-emerald/20 text-emerald border-emerald/50",
              qualityStatus.color === "amber" && "bg-amber/20 text-amber border-amber/50",
              qualityStatus.color === "destructive" && "bg-destructive/20 text-destructive border-destructive/50"
            )}
          >
            <QualityIcon className="h-3 w-3 mr-1" />
            {qualityStatus.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="grid grid-cols-2 gap-3">
          {/* Total Events */}
          <div className="p-3 rounded-lg bg-secondary/30">
            <div className="flex items-center gap-2 mb-1">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Total Events</span>
            </div>
            <p className="text-lg font-semibold">{totalEvents.toLocaleString()}</p>
          </div>

          {/* Median Size */}
          <div className="p-3 rounded-lg bg-secondary/30">
            <div className="flex items-center gap-2 mb-1">
              <Ruler className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Median Size</span>
            </div>
            <p className="text-lg font-semibold">
              {medianSize ? `${medianSize.toFixed(1)} nm` : "N/A"}
            </p>
          </div>

          {/* FSC Median */}
          <div className="p-3 rounded-lg bg-secondary/30">
            <div className="flex items-center gap-2 mb-1">
              <Hash className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">FSC Median</span>
            </div>
            <p className="text-lg font-semibold">
              {fscMedian ? fscMedian.toLocaleString() : "N/A"}
            </p>
          </div>

          {/* SSC Median */}
          <div className="p-3 rounded-lg bg-secondary/30">
            <div className="flex items-center gap-2 mb-1">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">SSC Median</span>
            </div>
            <p className="text-lg font-semibold">
              {sscMedian ? sscMedian.toLocaleString() : "N/A"}
            </p>
          </div>

          {/* Size Distribution Stats */}
          <div className="col-span-2 p-3 rounded-lg bg-secondary/30">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Size Distribution</span>
            </div>
            <div className="grid grid-cols-4 gap-2 text-center">
              <div>
                <p className="text-xs text-muted-foreground">D10</p>
                <p className="text-sm font-medium">
                  {d10 ? `${d10.toFixed(0)}` : "N/A"}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">D50</p>
                <p className="text-sm font-medium">
                  {d50 ? `${d50.toFixed(0)}` : "N/A"}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">D90</p>
                <p className="text-sm font-medium">
                  {d90 ? `${d90.toFixed(0)}` : "N/A"}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Std Dev</p>
                <p className="text-sm font-medium">
                  {sizeStdDev ? `±${sizeStdDev.toFixed(0)}` : "N/A"}
                </p>
              </div>
            </div>
          </div>

          {/* Debris if available */}
          {debrisPct !== undefined && (
            <div className="col-span-2 p-3 rounded-lg bg-secondary/30">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">Debris Percentage</span>
                </div>
                <p className="text-sm font-medium">{debrisPct.toFixed(1)}%</p>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export function IndividualFileSummary({ primaryFile, secondaryFile }: IndividualFileSummaryProps) {
  const hasSecondaryFile = secondaryFile?.results !== null

  if (!hasSecondaryFile) {
    // Single file mode - don't show this component
    return null
  }

  return (
    <Card className="card-3d">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-primary/10">
            <Layers className="h-4 w-4 text-primary" />
          </div>
          <div>
            <CardTitle className="text-base">Individual File Analysis</CardTitle>
            <CardDescription className="text-xs">
              Detailed statistics for each uploaded file
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="side-by-side" className="space-y-4">
          <TabsList className="bg-secondary/50">
            <TabsTrigger value="side-by-side">Side by Side</TabsTrigger>
            <TabsTrigger value="primary">Primary Only</TabsTrigger>
            <TabsTrigger value="secondary">Comparison Only</TabsTrigger>
          </TabsList>

          <TabsContent value="side-by-side" className="space-y-0">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FileSummaryCard 
                fileName={primaryFile.fileName}
                sampleId={primaryFile.sampleId}
                results={primaryFile.results}
                variant="primary"
              />
              <FileSummaryCard 
                fileName={secondaryFile?.fileName}
                sampleId={secondaryFile?.sampleId}
                results={secondaryFile?.results ?? null}
                variant="secondary"
              />
            </div>
          </TabsContent>

          <TabsContent value="primary" className="space-y-0">
            <FileSummaryCard 
              fileName={primaryFile.fileName}
              sampleId={primaryFile.sampleId}
              results={primaryFile.results}
              variant="primary"
            />
          </TabsContent>

          <TabsContent value="secondary" className="space-y-0">
            <FileSummaryCard 
              fileName={secondaryFile?.fileName}
              sampleId={secondaryFile?.sampleId}
              results={secondaryFile?.results ?? null}
              variant="secondary"
            />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
