"use client"

import { useEffect } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { useAnalysisStore } from "@/lib/store"
import { useApi } from "@/hooks/use-api"
import { FileText, Calendar, Ruler, Wifi, FlaskConical, BarChart3 } from "lucide-react"
import { cn } from "@/lib/utils"

export function QuickStats() {
  const { samples, apiSamples, apiConnected, fcsAnalysis, ntaAnalysis } = useAnalysisStore()
  const { fetchSamples } = useApi()

  // Fetch samples on mount only if API is connected
  // PERFORMANCE FIX: Remove fetchSamples from deps to prevent infinite loop
  useEffect(() => {
    if (apiConnected) {
      fetchSamples()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiConnected])

  const totalSamples = apiSamples.length + samples.length
  const fcsSamples = apiSamples.filter(s => s.files?.fcs).length
  const ntaSamples = apiSamples.filter(s => s.files?.nta).length

  // Get average particle size from latest analysis
  const avgSize = fcsAnalysis.results?.size_statistics?.mean 
    || ntaAnalysis.results?.size_statistics?.mean 
    || null

  const stats = [
    {
      label: "Total Samples",
      value: totalSamples.toString(),
      icon: FileText,
      color: "text-primary",
      gradient: "from-primary/20 to-primary/5",
    },
    {
      label: "FCS Samples",
      value: fcsSamples.toString(),
      icon: FlaskConical,
      color: "text-purple",
      gradient: "from-purple/20 to-purple/5",
    },
    {
      label: "NTA Samples",
      value: ntaSamples.toString(),
      icon: BarChart3,
      color: "text-cyan",
      gradient: "from-cyan/20 to-cyan/5",
    },
    {
      label: "Avg Particle Size",
      value: avgSize ? `${avgSize.toFixed(1)} nm` : "—",
      icon: Ruler,
      color: "text-amber",
      gradient: "from-amber/20 to-amber/5",
    },
    {
      label: "API Status",
      value: apiConnected ? "Connected" : "Offline",
      icon: Wifi,
      color: apiConnected ? "text-emerald" : "text-destructive",
      gradient: apiConnected ? "from-emerald/20 to-emerald/5" : "from-destructive/20 to-destructive/5",
    },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 md:gap-4">
      {stats.map((stat) => {
        const Icon = stat.icon
        return (
          <Card key={stat.label} className="card-3d stat-card group">
            <CardContent className="p-4">
              <div className={cn("absolute inset-0 bg-linear-to-br opacity-50 rounded-xl", stat.gradient)} />
              <div className="relative flex items-center gap-3">
                <div
                  className={cn(
                    "p-2.5 rounded-xl bg-linear-to-br shadow-lg transition-transform group-hover:scale-110",
                    stat.gradient,
                    stat.color,
                  )}
                >
                  <Icon className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-muted-foreground truncate">{stat.label}</p>
                  <p className="text-base md:text-lg font-semibold font-mono truncate">{stat.value}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
