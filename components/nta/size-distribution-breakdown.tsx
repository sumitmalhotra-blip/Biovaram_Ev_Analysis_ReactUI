"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { NTAResult } from "@/lib/api-client"
import { Beaker, Sparkles, Target } from "lucide-react"

interface SizeDistributionBreakdownProps {
  results: NTAResult
  className?: string
}

export function NTASizeDistributionBreakdown({ results, className }: SizeDistributionBreakdownProps) {
  const totalParticles = results.total_particles || 0

  // Define size bins based on NTA typical ranges
  const sizeBins = [
    {
      name: "50-80 nm",
      range: "Small EVs",
      percentage: results.bin_50_80nm_pct || 0,
      count: Math.round((totalParticles * (results.bin_50_80nm_pct || 0)) / 100),
      color: "cyan" as const,
      description: "Small extracellular vesicles, including exosomes",
      icon: Sparkles
    },
    {
      name: "80-100 nm",
      range: "Standard EVs",
      percentage: results.bin_80_100nm_pct || 0,
      count: Math.round((totalParticles * (results.bin_80_100nm_pct || 0)) / 100),
      color: "blue" as const,
      description: "Typical exosome size range",
      icon: Target
    },
    {
      name: "100-120 nm",
      range: "Large EVs",
      percentage: results.bin_100_120nm_pct || 0,
      count: Math.round((totalParticles * (results.bin_100_120nm_pct || 0)) / 100),
      color: "indigo" as const,
      description: "Larger extracellular vesicles",
      icon: Beaker
    },
    {
      name: "120-150 nm",
      range: "Extended EVs",
      percentage: results.bin_120_150nm_pct || 0,
      count: Math.round((totalParticles * (results.bin_120_150nm_pct || 0)) / 100),
      color: "purple" as const,
      description: "Extended size range vesicles",
      icon: Beaker
    },
    {
      name: "150-200 nm",
      range: "Large Vesicles",
      percentage: results.bin_150_200nm_pct || 0,
      count: Math.round((totalParticles * (results.bin_150_200nm_pct || 0)) / 100),
      color: "fuchsia" as const,
      description: "Larger microvesicles and particles",
      icon: Beaker
    },
    {
      name: "200+ nm",
      range: "Microvesicles",
      percentage: results.bin_200_plus_pct || 0,
      count: Math.round((totalParticles * (results.bin_200_plus_pct || 0)) / 100),
      color: "amber" as const,
      description: "Large microvesicles and cellular debris",
      icon: Beaker
    }
  ]

  // Find dominant population
  const dominantBin = sizeBins.reduce((max, bin) => 
    bin.percentage > max.percentage ? bin : max
  , sizeBins[0])

  return (
    <Card className={cn("card-3d", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-primary/10">
              <Beaker className="h-4 w-4 text-primary" />
            </div>
            <CardTitle className="text-base md:text-lg">Size Distribution Breakdown</CardTitle>
          </div>
          {dominantBin.percentage > 0 && (
            <Badge variant="outline" className="gap-1">
              <Target className="h-3 w-3" />
              {dominantBin.range}
            </Badge>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Particle distribution across size ranges • Total: {totalParticles.toLocaleString()} particles
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {sizeBins.map((bin) => {
          const Icon = bin.icon
          return (
            <div
              key={bin.name}
              className="group relative rounded-lg border bg-card p-4 transition-all hover:shadow-md"
            >
              {/* Gradient background */}
              <div
                className={cn(
                  "absolute inset-0 bg-linear-to-r opacity-5 rounded-lg transition-opacity group-hover:opacity-10",
                  bin.color === "cyan" && "from-cyan-500 to-transparent",
                  bin.color === "blue" && "from-blue-500 to-transparent",
                  bin.color === "indigo" && "from-indigo-500 to-transparent",
                  bin.color === "purple" && "from-purple-500 to-transparent",
                  bin.color === "fuchsia" && "from-fuchsia-500 to-transparent",
                  bin.color === "amber" && "from-amber-500 to-transparent"
                )}
              />

              {/* Content */}
              <div className="relative space-y-3">
                {/* Header */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <div
                        className={cn(
                          "p-1.5 rounded-md transition-transform group-hover:scale-110",
                          bin.color === "cyan" && "bg-cyan-500/20 text-cyan-600 dark:text-cyan-400",
                          bin.color === "blue" && "bg-blue-500/20 text-blue-600 dark:text-blue-400",
                          bin.color === "indigo" && "bg-indigo-500/20 text-indigo-600 dark:text-indigo-400",
                          bin.color === "purple" && "bg-purple-500/20 text-purple-600 dark:text-purple-400",
                          bin.color === "fuchsia" && "bg-fuchsia-500/20 text-fuchsia-600 dark:text-fuchsia-400",
                          bin.color === "amber" && "bg-amber-500/20 text-amber-600 dark:text-amber-400"
                        )}
                      >
                        <Icon className="h-3.5 w-3.5" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold">{bin.name}</h4>
                        <p className="text-xs text-muted-foreground">{bin.range}</p>
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {bin.description}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-lg font-bold font-mono">{bin.percentage.toFixed(1)}%</p>
                    <p className="text-xs text-muted-foreground">
                      {bin.count >= 1e6 
                        ? `${(bin.count / 1e6).toFixed(2)}M`
                        : bin.count >= 1e3
                        ? `${(bin.count / 1e3).toFixed(1)}K`
                        : bin.count.toLocaleString()
                      }
                    </p>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="space-y-1">
                  <Progress 
                    value={bin.percentage} 
                    className={cn(
                      "h-2",
                      bin.color === "cyan" && "[&>div]:bg-cyan-500",
                      bin.color === "blue" && "[&>div]:bg-blue-500",
                      bin.color === "indigo" && "[&>div]:bg-indigo-500",
                      bin.color === "purple" && "[&>div]:bg-purple-500",
                      bin.color === "fuchsia" && "[&>div]:bg-fuchsia-500",
                      bin.color === "amber" && "[&>div]:bg-amber-500"
                    )}
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>0%</span>
                    <span>100%</span>
                  </div>
                </div>

                {/* Dominant indicator */}
                {bin.name === dominantBin.name && bin.percentage > 0 && (
                  <Badge 
                    variant="secondary" 
                    className="text-xs"
                  >
                    Dominant Population
                  </Badge>
                )}
              </div>
            </div>
          )
        })}

        {/* NTA Standards Note */}
        <div className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">
          <p className="font-medium mb-1">NTA Measurement Note</p>
          <p>
            NTA (Nanoparticle Tracking Analysis) provides high-resolution size distribution for particles 
            from 30-1000 nm. Results are influenced by sample concentration, temperature, and camera settings.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
