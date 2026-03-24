import type { NTAResult } from "@/lib/api-client"
import type { NTASizeBin } from "@/lib/store"

export interface NTABinComputed {
  id: string
  name: string
  min: number
  max: number
  rangeLabel: string
  percentage: number
  concentration: number
  count: number
  color?: string
}

interface LegacyBin {
  min: number
  max: number
  percentage: number
}

function overlapLength(aMin: number, aMax: number, bMin: number, bMax: number): number {
  return Math.max(0, Math.min(aMax, bMax) - Math.max(aMin, bMin))
}

function getLegacyBins(results: NTAResult): LegacyBin[] {
  return [
    { min: 50, max: 80, percentage: results.bin_50_80nm_pct || 0 },
    { min: 80, max: 100, percentage: results.bin_80_100nm_pct || 0 },
    { min: 100, max: 120, percentage: results.bin_100_120nm_pct || 0 },
    { min: 120, max: 150, percentage: results.bin_120_150nm_pct || 0 },
    { min: 150, max: 200, percentage: results.bin_150_200nm_pct || 0 },
    { min: 200, max: 1000, percentage: results.bin_200_plus_pct || 0 },
  ]
}

function fallbackPercentagesFromLegacy(results: NTAResult, bins: NTASizeBin[]): number[] {
  const legacy = getLegacyBins(results)
  return bins.map((targetBin) => {
    const targetWidth = Math.max(targetBin.max - targetBin.min, 1)
    let pct = 0
    for (const l of legacy) {
      const ov = overlapLength(targetBin.min, targetBin.max, l.min, l.max)
      if (ov <= 0) continue
      const legacyWidth = Math.max(l.max - l.min, 1)
      pct += l.percentage * (ov / legacyWidth)
    }
    return (pct * (targetWidth / targetWidth))
  })
}

export function computeNTABinsForProfile(results: NTAResult, bins: NTASizeBin[]): NTABinComputed[] {
  const totalConc = results.concentration_particles_ml || 0
  const totalParticles = results.total_particles || 0

  let percentages: number[] = []

  if (results.size_distribution && results.size_distribution.length > 0) {
    const values = bins.map(() => 0)
    let totalValue = 0

    for (const point of results.size_distribution) {
      const size = point.size
      const rawValue = point.count ?? point.concentration ?? 0
      const value = Number.isFinite(rawValue) ? rawValue : 0
      if (!Number.isFinite(size) || value <= 0) continue

      const idx = bins.findIndex((b) => size >= b.min && size < b.max)
      if (idx >= 0) {
        values[idx] += value
        totalValue += value
      }
    }

    if (totalValue > 0) {
      percentages = values.map((v) => (v / totalValue) * 100)
    } else {
      percentages = fallbackPercentagesFromLegacy(results, bins)
    }
  } else {
    percentages = fallbackPercentagesFromLegacy(results, bins)
  }

  const pctSum = percentages.reduce((s, p) => s + p, 0)
  const normalized = pctSum > 0 ? percentages.map((p) => (p / pctSum) * 100) : percentages

  return bins.map((bin, idx) => {
    const percentage = normalized[idx] || 0
    const concentration = totalConc > 0 ? (percentage / 100) * (totalConc / 1e9) : 0
    const count = totalParticles > 0 ? Math.round((percentage / 100) * totalParticles) : 0
    return {
      id: bin.id,
      name: bin.name,
      min: bin.min,
      max: bin.max,
      rangeLabel: `${bin.min}-${bin.max} nm`,
      percentage,
      concentration,
      count,
      color: bin.color,
    }
  })
}

export function computeEVCategoryPercentagesFromBins(items: NTABinComputed[]): {
  smallEVs: number
  mediumEVs: number
  largeEVs: number
} {
  let small = 0
  let medium = 0
  let large = 0

  for (const item of items) {
    const width = Math.max(item.max - item.min, 1)

    const sOv = overlapLength(item.min, item.max, 30, 150)
    const mOv = overlapLength(item.min, item.max, 150, 500)
    const lOv = overlapLength(item.min, item.max, 500, 1000)

    small += item.percentage * (sOv / width)
    medium += item.percentage * (mOv / width)
    large += item.percentage * (lOv / width)
  }

  const total = small + medium + large
  if (total <= 0) {
    return { smallEVs: 33.3, mediumEVs: 33.3, largeEVs: 33.4 }
  }

  return {
    smallEVs: (small / total) * 100,
    mediumEVs: (medium / total) * 100,
    largeEVs: (large / total) * 100,
  }
}
