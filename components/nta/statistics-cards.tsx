"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { 
  Droplets, 
  Ruler, 
  BarChart3, 
  TrendingUp,
  Thermometer,
  FlaskConical,
  Target,
  Activity
} from "lucide-react"
import { cn } from "@/lib/utils"
import { NTAResult } from "@/lib/api-client"

interface StatisticsCardsProps {
  results: NTAResult
  className?: string
}

export function NTAStatisticsCards({ results, className }: StatisticsCardsProps) {
  // Calculate quality status based on NTA data
  const getQualityStatus = () => {
    const concentration = results.concentration_particles_ml || 0
    const meanSize = results.mean_size_nm || 0
    const stdDev = results.size_statistics?.std || 0
    
    // Quality indicators for NTA
    const hasGoodConcentration = concentration >= 1e7 && concentration <= 1e10
    const hasValidSize = meanSize >= 30 && meanSize <= 500
    const hasLowVariability = stdDev < 50
    
    if (hasGoodConcentration && hasValidSize && hasLowVariability) {
      return { label: "Excellent", color: "emerald" as const, description: "High quality measurement" }
    } else if (hasGoodConcentration && hasValidSize) {
      return { label: "Good", color: "blue" as const, description: "Acceptable measurement quality" }
    } else if (concentration < 1e7) {
      return { label: "Low Concentration", color: "amber" as const, description: "Sample concentration below optimal range" }
    } else if (concentration > 1e10) {
      return { label: "High Concentration", color: "rose" as const, description: "May require dilution" }
    } else {
      return { label: "Needs Review", color: "amber" as const, description: "Check measurement parameters" }
    }
  }

  const qualityStatus = getQualityStatus()

  // Define metrics with proper typing
  const metrics: Array<{
    label: string
    value: string
    icon: typeof Droplets
    color: "blue" | "purple" | "emerald" | "amber" | "cyan" | "rose" | "indigo"
    gradient: string
    description: string
  }> = [
    {
      label: "Total Particles",
      value: results.total_particles 
        ? results.total_particles >= 1e6 
          ? `${(results.total_particles / 1e6).toFixed(2)}M`
          : results.total_particles.toLocaleString()
        : "N/A",
      icon: Target,
      color: "blue",
      gradient: "from-blue-500/20 via-cyan-500/20 to-blue-600/20",
      description: "Total number of particles detected"
    },
    {
      label: "Concentration",
      value: results.concentration_particles_ml
        ? `${(results.concentration_particles_ml / 1e9).toFixed(2)}E9/mL`
        : "N/A",
      icon: Droplets,
      color: "cyan",
      gradient: "from-cyan-500/20 via-blue-500/20 to-cyan-600/20",
      description: "Particle concentration per milliliter"
    },
    {
      label: "Mean Size",
      value: results.mean_size_nm ? `${results.mean_size_nm.toFixed(1)} nm` : "N/A",
      icon: Ruler,
      color: "purple",
      gradient: "from-purple-500/20 via-fuchsia-500/20 to-purple-600/20",
      description: "Average particle diameter"
    },
    {
      label: "Median Size (D50)",
      value: results.median_size_nm 
        ? `${results.median_size_nm.toFixed(1)} nm`
        : results.d50_nm 
        ? `${results.d50_nm.toFixed(1)} nm`
        : "N/A",
      icon: BarChart3,
      color: "indigo",
      gradient: "from-indigo-500/20 via-purple-500/20 to-indigo-600/20",
      description: "50th percentile of size distribution"
    },
    {
      label: "D10",
      value: results.d10_nm 
        ? `${results.d10_nm.toFixed(1)} nm`
        : results.size_statistics?.d10
        ? `${results.size_statistics.d10.toFixed(1)} nm`
        : "N/A",
      icon: TrendingUp,
      color: "emerald",
      gradient: "from-emerald-500/20 via-teal-500/20 to-emerald-600/20",
      description: "10th percentile - smallest 10% of particles"
    },
    {
      label: "D90",
      value: results.d90_nm 
        ? `${results.d90_nm.toFixed(1)} nm`
        : results.size_statistics?.d90
        ? `${results.size_statistics.d90.toFixed(1)} nm`
        : "N/A",
      icon: TrendingUp,
      color: "purple",
      gradient: "from-purple-500/20 via-pink-500/20 to-purple-600/20",
      description: "90th percentile - 90% of particles are smaller"
    },
    {
      label: "Temperature",
      value: results.temperature_celsius ? `${results.temperature_celsius.toFixed(1)}°C` : "N/A",
      icon: Thermometer,
      color: "amber",
      gradient: "from-amber-500/20 via-orange-500/20 to-amber-600/20",
      description: "Measurement temperature"
    },
    {
      label: "Quality",
      value: qualityStatus.label,
      icon: Activity,
      color: qualityStatus.color,
      gradient: qualityStatus.color === "emerald" 
        ? "from-emerald-500/20 via-green-500/20 to-emerald-600/20"
        : qualityStatus.color === "blue"
        ? "from-blue-500/20 via-sky-500/20 to-blue-600/20"
        : qualityStatus.color === "amber"
        ? "from-amber-500/20 via-yellow-500/20 to-amber-600/20"
        : "from-rose-500/20 via-red-500/20 to-rose-600/20",
      description: qualityStatus.description
    }
  ]

  return (
    <div className={cn("grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4", className)}>
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
                      "p-2 rounded-xl shadow-lg transition-transform group-hover:scale-110 duration-200",
                      metric.color === "blue" && "bg-blue-500/20 text-blue-600 dark:text-blue-400",
                      metric.color === "purple" && "bg-purple-500/20 text-purple-600 dark:text-purple-400",
                      metric.color === "emerald" && "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400",
                      metric.color === "amber" && "bg-amber-500/20 text-amber-600 dark:text-amber-400",
                      metric.color === "cyan" && "bg-cyan-500/20 text-cyan-600 dark:text-cyan-400",
                      metric.color === "rose" && "bg-rose-500/20 text-rose-600 dark:text-rose-400",
                      metric.color === "indigo" && "bg-indigo-500/20 text-indigo-600 dark:text-indigo-400"
                    )}
                  >
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs text-muted-foreground truncate">{metric.label}</p>
                    {metric.label === "Quality" ? (
                      <Badge 
                        variant="outline" 
                        className={cn(
                          "font-semibold text-xs mt-1",
                          qualityStatus.color === "emerald" && "border-emerald-500 text-emerald-600 dark:text-emerald-400",
                          qualityStatus.color === "blue" && "border-blue-500 text-blue-600 dark:text-blue-400",
                          qualityStatus.color === "amber" && "border-amber-500 text-amber-600 dark:text-amber-400",
                          qualityStatus.color === "rose" && "border-rose-500 text-rose-600 dark:text-rose-400"
                        )}
                      >
                        {metric.value}
                      </Badge>
                    ) : (
                      <p className="text-base md:text-lg font-semibold font-mono truncate">
                        {metric.value}
                      </p>
                    )}
                  </div>
                </div>
                
                {/* Hover description */}
                <p className="text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity duration-200 line-clamp-2">
                  {metric.description}
                </p>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
