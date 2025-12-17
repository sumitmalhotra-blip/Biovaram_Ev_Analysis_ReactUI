"use client"

import { Card, CardContent } from "@/components/ui/card"
import { 
  FileText, 
  BarChart3, 
  Hash, 
  TrendingUp, 
  Ruler, 
  Activity,
  CheckCircle,
  AlertTriangle
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { FCSResult } from "@/lib/api-client"

interface StatisticsCardsProps {
  results: FCSResult | null
}

export function StatisticsCards({ results }: StatisticsCardsProps) {
  if (!results) {
    return null
  }

  // Extract statistics from results
  // Note: Mean values are NOT displayed per client request (Surya, Dec 3, 2025)
  // "Mean is basically not the real metric... median is something that really existed in the data set"
  const totalEvents = results.total_events || results.event_count || 0
  const medianSize = results.particle_size_median_nm || results.size_statistics?.d50
  const fscMedian = results.fsc_median
  const sscMedian = results.ssc_median
  const debrisPct = results.debris_pct
  const cd81Pct = results.cd81_positive_pct
  // Size standard deviation for display
  const sizeStdDev = results.size_statistics?.std
  
  // TASK-002: Size filtering info (Dec 17, 2025) - particles excluded from analysis
  const excludedPct = results.excluded_particles_pct
  const sizeFiltering = results.size_filtering
  const sizeRange = results.size_range
  
  // TASK-010: VSSC_MAX auto-selection info (Dec 17, 2025)
  // Parvesh: "Create VSSC max... pick whichever the larger one is"
  const vsscMaxUsed = results.vssc_max_used
  const vsscSelection = results.vssc_selection
  const sscChannelUsed = results.ssc_channel_used

  // Determine quality status based on debris and event count
  const qualityStatus = (() => {
    if (totalEvents < 5000) return { label: "Low Count", color: "amber", icon: AlertTriangle }
    if (debrisPct && debrisPct > 20) return { label: "High Debris", color: "destructive", icon: AlertTriangle }
    if (debrisPct && debrisPct > 10) return { label: "Fair", color: "amber", icon: AlertTriangle }
    // Check exclusion rate - warn if too many particles filtered
    if (excludedPct && excludedPct > 30) return { label: "High Exclusion", color: "amber", icon: AlertTriangle }
    return { label: "Good", color: "emerald", icon: CheckCircle }
  })()

  // Note: Mean values are intentionally NOT displayed per client request (Surya, Dec 3, 2025)
  // "Mean is basically not the real metric... median is something that really existed in the data set"
  // Mean is still calculated in backend for ML modeling purposes
  
  const metrics = [
    {
      label: "Total Events",
      value: totalEvents.toLocaleString(),
      icon: FileText,
      gradient: "from-primary/20 to-primary/5",
      description: sizeFiltering 
        ? `${sizeFiltering.valid_count.toLocaleString()} valid (${sizeRange?.valid_min ?? 30}-${sizeRange?.valid_max ?? 220}nm)`
        : "Particles detected",
    },
    {
      label: "Median Size",
      value: medianSize ? `${medianSize.toFixed(1)} nm` : "N/A",
      icon: Ruler,
      gradient: "from-cyan/20 to-cyan/5",
      description: "Particle diameter (D50)",
    },
    {
      label: "FSC Median",
      value: fscMedian ? fscMedian.toLocaleString() : "N/A",
      icon: Hash,
      gradient: "from-purple/20 to-purple/5",
      description: "Forward scatter intensity",
    },
    {
      label: "SSC Median",
      value: sscMedian ? sscMedian.toLocaleString() : "N/A",
      icon: Activity,
      gradient: "from-indigo/20 to-indigo/5",
      // TASK-010: Show VSSC_MAX selection info if used
      description: vsscMaxUsed && vsscSelection
        ? `Auto-selected: ${vsscSelection.vssc1_channel?.split('-')[0] || 'VSSC1'}=${vsscSelection.vssc1_selected_pct?.toFixed(0) || 0}%, ${vsscSelection.vssc2_channel?.split('-')[0] || 'VSSC2'}=${vsscSelection.vssc2_selected_pct?.toFixed(0) || 0}%`
        : sscChannelUsed 
          ? `Using ${sscChannelUsed}` 
          : "Side scatter intensity",
    },
    {
      label: "Size Std Dev",
      value: sizeStdDev ? `±${sizeStdDev.toFixed(1)} nm` : "N/A",
      icon: BarChart3,
      gradient: "from-orange/20 to-orange/5",
      description: "Size distribution spread",
    },
    ...(cd81Pct
      ? [
          {
            label: "CD81 Positive",
            value: `${cd81Pct.toFixed(1)}%`,
            icon: CheckCircle,
            gradient: "from-green/20 to-green/5",
            description: "Marker-positive events",
          },
        ]
      : []),
    {
      label: "Quality",
      value: qualityStatus.label,
      icon: qualityStatus.icon,
      gradient: `from-${qualityStatus.color}/20 to-${qualityStatus.color}/5`,
      description: debrisPct ? `${debrisPct.toFixed(1)}% debris` : "Event count based",
      success: qualityStatus.color === "emerald",
      warning: qualityStatus.color === "amber",
      error: qualityStatus.color === "destructive",
    },
  ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
      {metrics.map((metric) => {
        const Icon = metric.icon
        return (
          <Card key={metric.label} className="card-3d stat-card group overflow-hidden">
            <CardContent className="p-3 md:p-4 relative">
              {/* Gradient background */}
              <div
                className={cn(
                  "absolute inset-0 bg-linear-to-br opacity-50 rounded-xl transition-opacity group-hover:opacity-70",
                  metric.gradient
                )}
              />
              
              {/* Content */}
              <div className="relative flex flex-col gap-2">
                <div className="flex items-center gap-2 md:gap-3">
                  <div
                    className={cn(
                      "p-2 rounded-xl shadow-lg transition-all group-hover:scale-110 group-hover:shadow-xl",
                      metric.error
                        ? "bg-destructive/20 text-destructive"
                        : metric.warning
                          ? "bg-amber/20 text-amber"
                          : metric.success
                            ? "bg-emerald/20 text-emerald"
                            : "bg-primary/20 text-primary"
                    )}
                  >
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs text-muted-foreground truncate">{metric.label}</p>
                    <p className="text-base md:text-lg font-semibold font-mono truncate">
                      {metric.value}
                    </p>
                  </div>
                </div>
                
                {/* Description on hover */}
                <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                  <p className="text-xs text-muted-foreground/80">{metric.description}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
