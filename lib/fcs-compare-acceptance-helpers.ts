export type CompareSampleStatus = "loading" | "error" | "empty" | "data"

export type OverlayHistogramRenderState = "loading" | "error" | "empty" | "data"

export function normalizeCompareSampleIds(sampleIds: string[], maxSamples = 10): string[] {
  return Array.from(new Set(sampleIds.map((id) => id.trim()).filter(Boolean))).slice(0, maxSamples)
}

export function normalizeVisibleSampleIds(sampleIds: string[], allowedSampleIds: string[]): string[] {
  const allowed = new Set(allowedSampleIds)
  return Array.from(new Set(sampleIds.map((id) => id.trim()).filter((id) => allowed.has(id))))
}

export function buildScatterPriorityOrder(normalizedSampleIds: string[], visibleSampleIds: string[]): string[] {
  return [
    ...visibleSampleIds,
    ...normalizedSampleIds.filter((id) => !visibleSampleIds.includes(id)),
  ]
}

export function clampCompareLoadConfig(options?: {
  resultConcurrency?: number
  scatterConcurrency?: number
  scatterPointLimit?: number
}): { resultConcurrency: number; scatterConcurrency: number; scatterPointLimit: number } {
  return {
    resultConcurrency: Math.max(1, Math.min(5, options?.resultConcurrency ?? 3)),
    scatterConcurrency: Math.max(1, Math.min(4, options?.scatterConcurrency ?? 2)),
    scatterPointLimit: Math.max(500, Math.min(10000, options?.scatterPointLimit ?? 2000)),
  }
}

export function isCurrentCompareRequestVersion(currentVersion: number, requestVersion: number): boolean {
  return currentVersion === requestVersion
}

export function deriveCompareSampleStatus(params: {
  sampleId?: string | null
  loadingBySampleId: Record<string, boolean>
  errorsBySampleId: Record<string, string>
  hasResults: boolean
}): CompareSampleStatus {
  const sampleId = params.sampleId || null
  if (!sampleId) return "empty"
  if (params.loadingBySampleId[sampleId]) return "loading"
  if (params.errorsBySampleId[sampleId]) return "error"
  return params.hasResults ? "data" : "empty"
}

export function deriveOverlayHistogramRenderState(params: {
  primaryLoading: boolean
  hasPrimaryResults: boolean
  primaryError?: string
  chartDataLength: number
}): OverlayHistogramRenderState {
  if (params.primaryLoading) return "loading"
  if (!params.hasPrimaryResults && params.primaryError) return "error"
  if (!params.hasPrimaryResults) return "empty"
  if (params.chartDataLength === 0) return "empty"
  return "data"
}