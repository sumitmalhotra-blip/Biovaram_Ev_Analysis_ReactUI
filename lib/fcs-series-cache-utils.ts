export type FCSSeriesCacheTask = "scatterSeries" | "overlayHistogram"

export function buildScatterSeriesCacheKey(params: {
  sampleId: string
  pointLimit: number
  axisX?: string
  axisY?: string
}): string {
  const axisX = (params.axisX || "").trim().toUpperCase()
  const axisY = (params.axisY || "").trim().toUpperCase()
  return `scatter:${params.sampleId}:${params.pointLimit}:${axisX}:${axisY}`
}

export function buildOverlayHistogramCacheKey(params: {
  primarySampleId?: string | null
  secondarySampleId?: string | null
  parameter: string
  bins: number
  primaryCount: number
  secondaryCount: number
  primaryMean: number
  primaryStd: number
  secondaryMean: number
  secondaryStd: number
}): string {
  const primaryId = (params.primarySampleId || "none").trim()
  const secondaryId = (params.secondarySampleId || "none").trim()
  const rounded = (value: number) => Number.isFinite(value) ? value.toFixed(3) : "nan"

  return [
    "hist",
    primaryId,
    secondaryId,
    params.parameter.trim().toUpperCase(),
    String(params.bins),
    String(params.primaryCount),
    String(params.secondaryCount),
    rounded(params.primaryMean),
    rounded(params.primaryStd),
    rounded(params.secondaryMean),
    rounded(params.secondaryStd),
  ].join(":")
}

export function estimateSeriesBytes(value: unknown): number {
  try {
    const serialized = JSON.stringify(value)
    return serialized.length * 2
  } catch {
    return 1024
  }
}
