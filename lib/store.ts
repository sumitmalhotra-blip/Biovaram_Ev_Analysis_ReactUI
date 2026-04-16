 import { create } from "zustand"
import { persist, createJSONStorage } from "zustand/middleware"
import { useShallow } from "zustand/shallow"
import { useState, useEffect } from "react"
import type { Sample as APISample, FCSResult, NTAResult, ProcessingJob, FileMetadata } from "./api-client"

export type TabType = "dashboard" | "flow-cytometry" | "nta" | "cross-compare" | "research-chat"

export const DEFAULT_SIDEBAR_WIDTH = 288
export const MIN_SIDEBAR_WIDTH = 240
export const MAX_SIDEBAR_WIDTH = 520

// Enhanced chart data structure for proper figure storage
export interface ChartDataPoint {
  x: number
  y: number
  label?: string
  category?: string
}

export interface PinnedChartConfig {
  xAxisLabel?: string
  yAxisLabel?: string
  color?: string
  secondaryColor?: string
  showGrid?: boolean
  domain?: { x?: [number, number]; y?: [number, number] }
}

export interface PinnedChart {
  id: string
  title: string
  source: string
  timestamp: Date
  type: "histogram" | "scatter" | "line" | "bar"
  data: ChartDataPoint[] | unknown
  config?: PinnedChartConfig
  snapshotDataUrl?: string
  snapshotThumbnailUrl?: string
  chartContext?: string
  // Store the original results for reference
  sourceData?: {
    fcsResults?: FCSResult
    ntaResults?: NTAResult
  }
}

// Local sample type (for UI state before API integration)
export interface LocalSample {
  id: string
  name: string
  type: "fcs" | "nta"
  uploadedAt: Date
  treatment?: string
  concentration?: number
  operator?: string
  notes?: string
  analyzed?: boolean
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
  parts?: Array<{ type: string; text?: string }>
}

// Saved Chart Image for Gallery
export interface SavedImage {
  id: string
  title: string
  source: string // e.g., "FCS Analysis", "NTA Analysis", "Cross-Compare"
  chartType: "histogram" | "scatter" | "line" | "bar" | "heatmap" | "pie"
  dataUrl: string // base64 encoded image
  thumbnailUrl?: string // smaller version for gallery preview
  timestamp: Date
  metadata?: {
    sampleId?: string
    width?: number
    height?: number
    format?: "png" | "jpeg" | "svg"
    notes?: string
  }
}

// Experimental Conditions (captured during analysis)
export interface ExperimentalConditions {
  temperature_celsius?: number
  substrate_buffer?: string
  sample_volume_ul?: number
  ph?: number
  incubation_time_min?: number
  antibody_details?: string
  antibody_concentration_ug?: number
  dilution_factor?: number
  operator: string
  notes?: string
}

// Anomaly Detection Result (from backend)
export interface AnomalyDetectionResult {
  method: "Z-Score" | "IQR" | "Both"
  total_anomalies: number
  anomaly_percentage: number
  zscore_anomalies?: number
  iqr_anomalies?: number
  combined_anomalies?: number
  zscore_threshold?: number
  iqr_factor?: number
  anomalous_indices: number[]
  fsc_outliers?: number[]
  ssc_outliers?: number[]
}

// Size Range type for custom EV size categories
export interface SizeRange {
  name: string
  min: number
  max: number
  color?: string
}

// Current FCS analysis state
export interface FCSAnalysisState {
  file: File | null
  sampleId: string | null
  results: FCSResult | null
  anomalyData: AnomalyDetectionResult | null
  isAnalyzing: boolean
  error: string | null
  experimentalConditions: ExperimentalConditions | null
  sizeRanges: SizeRange[]
  fileMetadata: FileMetadata | null  // Auto-extracted metadata from file
}

// Scatter data point for charts
export interface ScatterDataPoint {
  x: number
  y: number
  index?: number
  isAnomaly?: boolean
  diameter?: number
}

// Secondary FCS analysis state for comparison/overlay
export interface SecondaryFCSAnalysisState {
  file: File | null
  sampleId: string | null
  results: FCSResult | null
  anomalyData: AnomalyDetectionResult | null
  isAnalyzing: boolean
  error: string | null
  scatterData: ScatterDataPoint[]  // Scatter data for overlay charts
  loadingScatter: boolean
}

// Overlay configuration for comparing two files
export interface OverlayConfig {
  enabled: boolean
  showBothHistograms: boolean
  showOverlaidScatter: boolean
  showOverlaidTheory: boolean       // NEW: Theory vs Measured overlay
  showOverlaidDiameter: boolean     // NEW: Diameter vs SSC overlay
  primaryColor: string
  secondaryColor: string
  primaryLabel: string
  secondaryLabel: string
  primaryOpacity: number            // NEW: Opacity for primary data
  secondaryOpacity: number          // NEW: Opacity for secondary data
}

export interface FCSCompareTelemetry {
  totalLoads: number
  totalLoadMs: number
  averageLoadMs: number
  lastLoadMs: number
  lastQueueDepth: number
  maxQueueDepth: number
  cacheHits: number
  cacheMisses: number
  cacheEvictions: number
  lastUpdatedAt: number | null
}

export interface FCSSeriesCacheEntry {
  key: string
  task: "scatterSeries" | "overlayHistogram"
  data: unknown
  approxBytes: number
  version: number
  createdAt: number
  lastAccessedAt: number
}

export interface FCSSeriesCacheState {
  entriesByKey: Record<string, FCSSeriesCacheEntry>
  lruKeys: string[]
  totalBytes: number
  maxEntries: number
  maxBytes: number
  version: number
}

export interface FCSCompareSessionState {
  selectedSampleIds: string[]
  visibleSampleIds: string[]
  primarySampleId: string | null
  compareItemMetaById: Record<string, {
    compareItemId?: string
    backendSampleId: string
    sampleLabel: string
    fileName?: string
    treatment?: string
    dye?: string
    uploadedAt: number
  }>
  resultsBySampleId: Record<string, FCSResult>
  scatterBySampleId: Record<string, ScatterDataPoint[]>
  loadingBySampleId: Record<string, boolean>
  errorBySampleId: Record<string, string | null>
  maxVisibleOverlays: number
}

export interface FCSCompareGraphAxis {
  x: string
  y: string
}

export type FCSCompareScatterDensityMode = "auto" | "raw" | "density"
export type FCSCompareScatterZoomPreset = "auto" | "center-60" | "core-30" | "high-signal"

export interface FCSCompareGraphInstance {
  id: string
  title: string
  axisMode: "unified" | "per-file"
  unifiedAxis: FCSCompareGraphAxis
  primaryAxis: FCSCompareGraphAxis
  comparisonAxis: FCSCompareGraphAxis
  scatterDensityMode: FCSCompareScatterDensityMode
  scatterZoomPreset: FCSCompareScatterZoomPreset
  showRawOverlayInDensity: boolean
  isMaximized: boolean
  createdAt: number
}

// NTA Analysis State
export interface NTAAnalysisState {
  file: File | null
  sampleId: string | null
  results: NTAResult | null
  isAnalyzing: boolean
  error: string | null
  experimentalConditions: ExperimentalConditions | null
  fileMetadata: FileMetadata | null  // Auto-extracted metadata from file
}

// Secondary NTA Analysis State (for overlay comparison)
export interface SecondaryNTAAnalysisState {
  file: File | null
  sampleId: string | null
  results: NTAResult | null
  isAnalyzing: boolean
  error: string | null
}

export interface NTACompareSessionState {
  selectedSampleIds: string[]
  visibleSampleIds: string[]
  primarySampleId: string | null
  resultsBySampleId: Record<string, NTAResult>
  loadingBySampleId: Record<string, boolean>
  errorBySampleId: Record<string, string | null>
  computedSeriesCacheByKey: Record<string, NTAComputedSeriesCacheEntry>
  maxVisibleOverlays: number
}

export interface NTAComputedSeriesCacheEntry {
  cacheKey: string
  chartType: "distribution" | "concentration"
  sampleId: string
  profileId?: string
  points: Array<{ x: number; y: number; label?: string }>
  updatedAt: number
}

// FCS Analysis Settings
export interface FCSAnalysisSettings {
  laserWavelength: number
  particleRI: number
  mediumRI: number
  fscRange: [number, number]
  sscRange: [number, number]
  // Angle Ranges (Mie Scattering integration angles in degrees)
  fscAngleRange: [number, number]  // Forward scatter angle range, default (1, 15)
  sscAngleRange: [number, number]  // Side scatter angle range, default (85, 95)
  diameterRange: [number, number]
  diameterPoints: number
  sizeRanges: Array<{ name: string; min: number; max: number }>
  // Data Cleaning Options
  ignoreNegativeH: boolean
  dropNaRows: boolean
  // Anomaly Detection Settings
  anomalyDetectionEnabled: boolean
  anomalyMethod: "Z-Score" | "IQR" | "Both"
  zscoreThreshold: number
  iqrFactor: number
  highlightAnomalies: boolean
  // Visualization Settings (TASK-019: Histogram bin configuration)
  useInteractivePlots: boolean
  histogramBins: number  // TASK-019: Configurable histogram bin count (10-100)
}

// Chart Color Scheme (TASK-018: Consistent color scheme)
// Client requested: Purple for normal, Red for anomalies
export const CHART_COLORS = {
  primary: "#7c3aed",        // Purple - normal data points
  secondary: "#a855f7",      // Light purple - secondary data
  anomaly: "#ef4444",        // Red - anomalies
  warning: "#f59e0b",        // Amber - warnings
  success: "#22c55e",        // Green - success/valid
  info: "#3b82f6",           // Blue - informational
  muted: "#6b7280",          // Gray - reference lines
  background: "#1f2937",     // Dark background
  // EV Size Category Colors
  smallEV: "#22c55e",        // Green - small EVs
  exosomes: "#7c3aed",       // Purple - exosomes (main)
  largeEV: "#f59e0b",        // Amber - large EVs
  microvesicles: "#ef4444",  // Red - microvesicles
} as const

const areStringArraysEqual = (left: string[], right: string[]) => {
  if (left.length !== right.length) {
    return false
  }

  for (let index = 0; index < left.length; index += 1) {
    if (left[index] !== right[index]) {
      return false
    }
  }

  return true
}

// Cross-Comparison Settings
export interface CrossComparisonSettings {
  discrepancyThreshold: number
  normalizeHistograms: boolean
  binSize: number
  showKde: boolean
  showStatistics: boolean
  minSizeFilter: number
  maxSizeFilter: number
  selectedFcsSampleId: string
  selectedNtaSampleId: string
}

// NTA Analysis Settings
export interface NTAAnalysisSettings {
  applyTemperatureCorrection: boolean
  measurementTemp: number
  referenceTemp: number
  mediaType: string
  correctionFactor: number
  // Visualization options
  showPercentileLines: boolean
  binSize: number
  yAxisMode: "count" | "normalized"
}

// NTA size bin/profile configuration
export interface NTASizeBin {
  id: string
  name: string
  min: number
  max: number
  color?: string
}

export interface NTASizeProfile {
  id: string
  name: string
  locked: boolean
  bins: NTASizeBin[]
  createdAt: string
}

export const NTA_LOCKED_QUALITY_PROFILE_ID = "nta-quality-default"

export const defaultNTAQualityProfile: NTASizeProfile = {
  id: NTA_LOCKED_QUALITY_PROFILE_ID,
  name: "Quality Standard (Locked)",
  locked: true,
  createdAt: new Date().toISOString(),
  bins: [
    { id: "bin-50-80", name: "50-80 nm", min: 50, max: 80, color: "#06b6d4" },
    { id: "bin-80-100", name: "80-100 nm", min: 80, max: 100, color: "#3b82f6" },
    { id: "bin-100-120", name: "100-120 nm", min: 100, max: 120, color: "#6366f1" },
    { id: "bin-120-150", name: "120-150 nm", min: 120, max: 150, color: "#8b5cf6" },
    { id: "bin-150-200", name: "150-200 nm", min: 150, max: 200, color: "#d946ef" },
    { id: "bin-200-plus", name: "200+ nm", min: 200, max: 1000, color: "#f59e0b" },
  ],
}

export const defaultNTAAnalysisProfile: NTASizeProfile = {
  id: "nta-analysis-default",
  name: "Analysis Default",
  locked: false,
  createdAt: new Date().toISOString(),
  bins: defaultNTAQualityProfile.bins.map((b) => ({ ...b })),
}

export const defaultNTAReportProfile: NTASizeProfile = {
  id: "nta-report-default",
  name: "Report Default",
  locked: false,
  createdAt: new Date().toISOString(),
  bins: defaultNTAQualityProfile.bins.map((b) => ({ ...b })),
}

export const defaultNTAAnalysisSettings: NTAAnalysisSettings = {
  applyTemperatureCorrection: false,
  measurementTemp: 22,
  referenceTemp: 25,
  mediaType: "pbs",
  correctionFactor: 0.9876,
  showPercentileLines: true,
  binSize: 10,
  yAxisMode: "count",
}

// ============================================
// GATING SYSTEM TYPES (T-009: Population Gating)
// ============================================

// Gate selection tool types
export type GateToolType = "none" | "rectangle" | "polygon" | "ellipse" | "lasso"

// Rectangle gate coordinates
export interface RectangleGate {
  type: "rectangle"
  x1: number  // top-left x (in data coordinates)
  y1: number  // top-left y
  x2: number  // bottom-right x
  y2: number  // bottom-right y
}

// Polygon gate coordinates
export interface PolygonGate {
  type: "polygon"
  points: Array<{ x: number; y: number }>  // Array of vertices
}

// Ellipse gate coordinates
export interface EllipseGate {
  type: "ellipse"
  cx: number  // center x
  cy: number  // center y
  rx: number  // radius x
  ry: number  // radius y
  rotation?: number  // rotation in degrees
}

// Union type for all gate shapes
export type GateShape = RectangleGate | PolygonGate | EllipseGate

// Individual gate definition
export interface Gate {
  id: string
  name: string
  color: string
  shape: GateShape
  createdAt: Date
  isActive: boolean  // Whether this gate is currently selected/highlighted
  parentGateId?: string  // For nested/hierarchical gates
}

// Statistics for gated population
export interface GatedStatistics {
  gateId: string
  totalEvents: number
  selectedEvents: number
  percentage: number
  fscMean?: number
  fscMedian?: number
  fscStd?: number
  sscMean?: number
  sscMedian?: number
  sscStd?: number
  diameterD10?: number
  diameterD50?: number
  diameterD90?: number
  diameterMean?: number
  diameterStd?: number
}

// Gating state for a sample
export interface GatingState {
  activeTool: GateToolType
  gates: Gate[]
  activeGateId: string | null  // Currently selected gate
  isDrawing: boolean  // Whether user is currently drawing a gate
  drawingPoints: Array<{ x: number; y: number }>  // Temporary points during drawing
  selectedIndices: number[]  // Indices of data points inside active gate(s)
  statistics: GatedStatistics | null  // Stats for current selection
}

// Initial gating state
export const initialGatingState: GatingState = {
  activeTool: "none",
  gates: [],
  activeGateId: null,
  isDrawing: false,
  drawingPoints: [],
  selectedIndices: [],
  statistics: null,
}

// ============================================

export interface AnalysisState {
  // UI State
  activeTab: TabType
  setActiveTab: (tab: TabType) => void
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  sidebarWidth: number
  setSidebarWidth: (width: number) => void
  isDarkMode: boolean
  toggleDarkMode: () => void

  // API Connection
  apiConnected: boolean
  setApiConnected: (connected: boolean) => void
  apiChecking: boolean
  setApiChecking: (checking: boolean) => void
  lastHealthCheck: Date | null
  setLastHealthCheck: (date: Date | null) => void

  // Samples from Backend
  apiSamples: APISample[]
  setApiSamples: (samples: APISample[]) => void
  addApiSample: (sample: APISample) => void
  removeApiSample: (sampleId: string) => void
  samplesLoading: boolean
  setSamplesLoading: (loading: boolean) => void
  samplesError: string | null
  setSamplesError: (error: string | null) => void

  // Local samples (for offline/fallback)
  samples: LocalSample[]
  addSample: (sample: LocalSample) => void

  // FCS Analysis State
  fcsAnalysis: FCSAnalysisState
  setFCSFile: (file: File | null) => void
  setFCSSampleId: (sampleId: string | null) => void
  setFCSResults: (results: FCSResult | null) => void
  setFCSAnomalyData: (anomalyData: AnomalyDetectionResult | null) => void
  setFCSAnalyzing: (analyzing: boolean) => void
  setFCSError: (error: string | null) => void
  setFCSExperimentalConditions: (conditions: ExperimentalConditions | null) => void
  setFCSSizeRanges: (sizeRanges: SizeRange[]) => void
  setFCSFileMetadata: (metadata: FileMetadata | null) => void
  resetFCSAnalysis: () => void

  // Secondary FCS Analysis State (for comparison/overlay)
  secondaryFcsAnalysis: SecondaryFCSAnalysisState
  setSecondaryFCSFile: (file: File | null) => void
  setSecondaryFCSSampleId: (sampleId: string | null) => void
  setSecondaryFCSResults: (results: FCSResult | null) => void
  setSecondaryFCSAnomalyData: (anomalyData: AnomalyDetectionResult | null) => void
  setSecondaryFCSAnalyzing: (analyzing: boolean) => void
  setSecondaryFCSError: (error: string | null) => void
  setSecondaryFCSScatterData: (scatterData: ScatterDataPoint[]) => void  // NEW
  setSecondaryFCSLoadingScatter: (loading: boolean) => void              // NEW
  resetSecondaryFCSAnalysis: () => void

  // Overlay Configuration
  overlayConfig: OverlayConfig
  fcsCompareRequestVersion: number
  fcsCompareTelemetry: FCSCompareTelemetry
  fcsSeriesCache: FCSSeriesCacheState
  fcsCompareSession: FCSCompareSessionState
  fcsCompareGraphInstances: FCSCompareGraphInstance[]
  activeFCSCompareGraphInstanceId: string | null
  incrementFCSCompareRequestVersion: () => number
  resetFCSCompareRequestVersion: () => void
  recordFCSCompareLoadMetrics: (metrics: { durationMs: number; queueDepth: number }) => void
  recordFCSCompareCacheStats: (stats: { hits?: number; misses?: number; evictions?: number }) => void
  resetFCSCompareTelemetry: () => void
  getFCSSeriesCacheEntry: (key: string) => FCSSeriesCacheEntry | null
  setFCSSeriesCacheEntry: (entry: {
    key: string
    task: FCSSeriesCacheEntry["task"]
    data: unknown
    approxBytes?: number
  }) => { evicted: number }
  invalidateFCSSeriesCache: (reason?: string) => void
  setFCSSeriesCacheLimits: (limits: { maxEntries?: number; maxBytes?: number }) => void
  setFCSCompareSelectedSampleIds: (sampleIds: string[]) => void
  setFCSCompareVisibleSampleIds: (sampleIds: string[]) => void
  toggleFCSCompareSampleVisibility: (sampleId: string) => void
  setFCSComparePrimarySampleId: (sampleId: string | null) => void
  setFCSCompareSampleMeta: (sampleId: string, meta: {
    backendSampleId: string
    sampleLabel: string
    fileName?: string
    treatment?: string
    dye?: string
    uploadedAt?: number
  }) => void
  setFCSCompareSampleLoading: (sampleId: string, loading: boolean) => void
  setFCSCompareSampleError: (sampleId: string, error: string | null) => void
  setFCSCompareSampleResult: (sampleId: string, result: FCSResult | null) => void
  setFCSCompareSampleScatter: (sampleId: string, scatter: ScatterDataPoint[] | null) => void
  setFCSCompareMaxVisibleOverlays: (maxVisible: number) => void
  clearFCSCompareSession: () => void
  createFCSCompareGraphInstance: (title?: string) => string
  duplicateFCSCompareGraphInstance: (instanceId: string) => string | null
  removeFCSCompareGraphInstance: (instanceId: string) => void
  setActiveFCSCompareGraphInstance: (instanceId: string) => void
  updateFCSCompareGraphInstance: (instanceId: string, updates: Partial<Omit<FCSCompareGraphInstance, "id" | "createdAt">>) => void
  setOverlayConfig: (config: Partial<OverlayConfig>) => void
  toggleOverlay: () => void

  // NTA Analysis State
  ntaAnalysis: NTAAnalysisState
  setNTAFile: (file: File | null) => void
  setNTASampleId: (sampleId: string | null) => void
  setNTAResults: (results: NTAResult | null) => void
  setNTAAnalyzing: (analyzing: boolean) => void
  setNTAError: (error: string | null) => void
  setNTAExperimentalConditions: (conditions: ExperimentalConditions | null) => void
  setNTAFileMetadata: (metadata: FileMetadata | null) => void
  resetNTAAnalysis: () => void

  // Secondary NTA Analysis State (for overlay comparison)
  secondaryNtaAnalysis: SecondaryNTAAnalysisState
  setSecondaryNTAFile: (file: File | null) => void
  setSecondaryNTASampleId: (sampleId: string | null) => void
  setSecondaryNTAResults: (results: NTAResult | null) => void
  setSecondaryNTAAnalyzing: (analyzing: boolean) => void
  setSecondaryNTAError: (error: string | null) => void
  resetSecondaryNTAAnalysis: () => void
  
  // NTA Overlay Configuration
  ntaOverlayEnabled: boolean
  setNtaOverlayEnabled: (enabled: boolean) => void
  ntaCompareSession: NTACompareSessionState
  setNTACompareSelectedSampleIds: (sampleIds: string[]) => void
  setNTACompareVisibleSampleIds: (sampleIds: string[]) => void
  toggleNTACompareSampleVisibility: (sampleId: string) => void
  setNTAComparePrimarySampleId: (sampleId: string | null) => void
  setNTACompareSampleLoading: (sampleId: string, loading: boolean) => void
  setNTACompareSampleError: (sampleId: string, error: string | null) => void
  setNTACompareSampleResult: (sampleId: string, result: NTAResult | null) => void
  setNTACompareComputedSeriesCacheEntry: (entry: NTAComputedSeriesCacheEntry) => void
  clearNTACompareComputedSeriesCache: () => void
  setNTACompareMaxVisibleOverlays: (maxVisible: number) => void
  clearNTACompareSession: () => void

  // Processing Jobs
  processingJobs: ProcessingJob[]
  addProcessingJob: (job: ProcessingJob) => void
  updateProcessingJob: (jobId: string, updates: Partial<ProcessingJob>) => void

  // Pinned Charts
  pinnedCharts: PinnedChart[]
  pinChart: (chart: PinnedChart) => void
  unpinChart: (id: string) => void
  clearPinnedCharts: () => void

  // Chat
  chatMessages: ChatMessage[]
  addChatMessage: (message: ChatMessage) => void
  clearChatMessages: () => void

  // Saved Images Gallery
  savedImages: SavedImage[]
  saveImage: (image: SavedImage) => void
  removeImage: (id: string) => void
  clearSavedImages: () => void

  // Analysis Settings
  fcsAnalysisSettings: FCSAnalysisSettings | null
  setFcsAnalysisSettings: (settings: Partial<FCSAnalysisSettings>) => void
  ntaAnalysisSettings: NTAAnalysisSettings
  setNtaAnalysisSettings: (settings: Partial<NTAAnalysisSettings>) => void
  ntaSizeProfiles: NTASizeProfile[]
  selectedNTAAnalysisProfileId: string
  selectedNTAReportProfileId: string
  ntaLockedBuckets: NTASizeBin[] | null
  setSelectedNTAAnalysisProfileId: (profileId: string) => void
  setSelectedNTAReportProfileId: (profileId: string) => void
  setNTALockedBuckets: (bins: NTASizeBin[] | null) => void
  createNTASizeProfile: (profile: Omit<NTASizeProfile, "createdAt">) => void
  updateNTASizeProfile: (profileId: string, updates: Partial<Omit<NTASizeProfile, "id" | "createdAt" | "locked">>) => void
  deleteNTASizeProfile: (profileId: string) => void
  resetNTASizeProfiles: () => void
  crossComparisonSettings: CrossComparisonSettings
  setCrossComparisonSettings: (settings: CrossComparisonSettings) => void

  // ============================================
  // GATING STATE & ACTIONS (T-009)
  // ============================================
  gatingState: GatingState
  setGateActiveTool: (tool: GateToolType) => void
  addGate: (gate: Gate) => void
  removeGate: (gateId: string) => void
  updateGate: (gateId: string, updates: Partial<Gate>) => void
  setActiveGate: (gateId: string | null) => void
  setSelectedIndices: (indices: number[]) => void
  clearAllGates: () => void
  resetGatingState: () => void
}

const initialFCSAnalysis: FCSAnalysisState = {
  file: null,
  sampleId: null,
  results: null,
  anomalyData: null,
  isAnalyzing: false,
  error: null,
  experimentalConditions: null,
  fileMetadata: null,  // Will be populated from uploaded file
  sizeRanges: [
    { name: "Exomeres (0-50nm)", min: 0, max: 50, color: "#22c55e" },
    { name: "Small EVs (51-100nm)", min: 51, max: 100, color: "#3b82f6" },
    { name: "Medium EVs (101-150nm)", min: 101, max: 150, color: "#a855f7" },
    { name: "Large EVs (151-200nm)", min: 151, max: 200, color: "#f59e0b" },
    { name: "Very Large EVs (200+nm)", min: 200, max: 1000, color: "#ef4444" },
  ],
}

const initialSecondaryFCSAnalysis: SecondaryFCSAnalysisState = {
  file: null,
  sampleId: null,
  results: null,
  anomalyData: null,
  isAnalyzing: false,
  error: null,
  scatterData: [],        // NEW: Empty scatter data
  loadingScatter: false,  // NEW: Loading state
}

const initialOverlayConfig: OverlayConfig = {
  enabled: false,
  showBothHistograms: true,
  showOverlaidScatter: true,
  showOverlaidTheory: true,      // NEW
  showOverlaidDiameter: true,    // NEW
  primaryColor: "#7c3aed",       // Purple
  secondaryColor: "#f97316",     // Orange
  primaryLabel: "Primary",
  secondaryLabel: "Comparison",
  primaryOpacity: 0.7,           // NEW
  secondaryOpacity: 0.5,         // NEW
}

const initialFCSCompareTelemetry: FCSCompareTelemetry = {
  totalLoads: 0,
  totalLoadMs: 0,
  averageLoadMs: 0,
  lastLoadMs: 0,
  lastQueueDepth: 0,
  maxQueueDepth: 0,
  cacheHits: 0,
  cacheMisses: 0,
  cacheEvictions: 0,
  lastUpdatedAt: null,
}

const initialFCSSeriesCache: FCSSeriesCacheState = {
  entriesByKey: {},
  lruKeys: [],
  totalBytes: 0,
  maxEntries: 120,
  maxBytes: 24 * 1024 * 1024,
  version: 1,
}

const initialFCSCompareSession: FCSCompareSessionState = {
  selectedSampleIds: [],
  visibleSampleIds: [],
  primarySampleId: null,
  compareItemMetaById: {},
  resultsBySampleId: {},
  scatterBySampleId: {},
  loadingBySampleId: {},
  errorBySampleId: {},
  maxVisibleOverlays: 8,
}

const FCS_COMPARE_MAX_SELECTED = 10

const normalizeFCSCompareSessionForHydration = (
  session: Partial<FCSCompareSessionState> | undefined
): FCSCompareSessionState => {
  const rawSelected = Array.isArray(session?.selectedSampleIds)
    ? Array.from(new Set(session?.selectedSampleIds.filter(Boolean) ?? [])).slice(0, FCS_COMPARE_MAX_SELECTED)
    : []
  const rawVisible = Array.isArray(session?.visibleSampleIds)
    ? Array.from(new Set(session?.visibleSampleIds.filter(Boolean) ?? []))
    : []
  const rawPrimary = typeof session?.primarySampleId === "string" ? session.primarySampleId : null
  const rawMetaById = session?.compareItemMetaById ?? {}

  const selectedSampleIds: string[] = []
  const originalIdBySelectedId: Record<string, string> = {}

  rawSelected.forEach((selectedId) => {
    let compareItemId = selectedId
    if (!rawMetaById[compareItemId]) {
      const fallbackMetaEntry = Object.entries(rawMetaById).find(([, meta]) => meta?.backendSampleId === selectedId)
      if (fallbackMetaEntry?.[0]) {
        compareItemId = fallbackMetaEntry[0]
      }
    }

    if (!selectedSampleIds.includes(compareItemId)) {
      selectedSampleIds.push(compareItemId)
      originalIdBySelectedId[compareItemId] = selectedId
    }
  })

  const maxVisibleOverlays = Number.isFinite(session?.maxVisibleOverlays)
    ? Math.max(1, Math.min(8, Number(session?.maxVisibleOverlays)))
    : initialFCSCompareSession.maxVisibleOverlays

  const visibleSampleIds = rawVisible
    .map((id) => {
      if (selectedSampleIds.includes(id)) {
        return id
      }
      return selectedSampleIds.find((selectedId) => originalIdBySelectedId[selectedId] === id) ?? null
    })
    .filter((id): id is string => typeof id === "string" && selectedSampleIds.includes(id))
    .slice(0, maxVisibleOverlays)

  const primarySampleId = rawPrimary && selectedSampleIds.includes(rawPrimary)
    ? rawPrimary
    : (
      rawPrimary
        ? (selectedSampleIds.find((id) => originalIdBySelectedId[id] === rawPrimary) ?? selectedSampleIds[0] ?? null)
        : (selectedSampleIds[0] ?? null)
    )

  const normalizeMapBySelected = <T,>(map: Record<string, T> | undefined): Record<string, T> => {
    const source = map ?? {}
    const normalized: Record<string, T> = {}

    selectedSampleIds.forEach((compareItemId) => {
      if (source[compareItemId] !== undefined) {
        normalized[compareItemId] = source[compareItemId]
        return
      }

      const originalId = originalIdBySelectedId[compareItemId]
      if (originalId && source[originalId] !== undefined) {
        normalized[compareItemId] = source[originalId]
      }
    })

    return normalized
  }

  const compareItemMetaById = Object.fromEntries(
    selectedSampleIds.map((compareItemId) => {
      const originalId = originalIdBySelectedId[compareItemId]
      const existingMeta = rawMetaById[compareItemId]
        ?? Object.entries(rawMetaById).find(([metaKey]) => metaKey === originalId)?.[1]

      const fallbackBackendId = originalId ?? compareItemId
      return [
        compareItemId,
        {
          compareItemId,
          backendSampleId: existingMeta?.backendSampleId ?? fallbackBackendId,
          sampleLabel: existingMeta?.sampleLabel ?? existingMeta?.fileName ?? fallbackBackendId,
          fileName: existingMeta?.fileName,
          treatment: existingMeta?.treatment,
          dye: existingMeta?.dye,
          uploadedAt: existingMeta?.uploadedAt ?? Date.now(),
        },
      ]
    })
  )

  return {
    selectedSampleIds,
    visibleSampleIds,
    primarySampleId,
    compareItemMetaById,
    resultsBySampleId: normalizeMapBySelected(session?.resultsBySampleId),
    scatterBySampleId: normalizeMapBySelected(session?.scatterBySampleId),
    loadingBySampleId: normalizeMapBySelected(session?.loadingBySampleId),
    errorBySampleId: normalizeMapBySelected(session?.errorBySampleId),
    maxVisibleOverlays,
  }
}

const DEFAULT_FCS_COMPARE_GRAPH_PROFILES: Array<{
  densityMode: FCSCompareScatterDensityMode
  zoomPreset: FCSCompareScatterZoomPreset
  showRawOverlayInDensity: boolean
}> = [
  { densityMode: "auto", zoomPreset: "auto", showRawOverlayInDensity: false },
  { densityMode: "raw", zoomPreset: "center-60", showRawOverlayInDensity: false },
  { densityMode: "density", zoomPreset: "core-30", showRawOverlayInDensity: true },
  { densityMode: "auto", zoomPreset: "high-signal", showRawOverlayInDensity: true },
]

const getDefaultFCSCompareGraphProfile = (instanceIndex = 0) => {
  return DEFAULT_FCS_COMPARE_GRAPH_PROFILES[Math.abs(instanceIndex) % DEFAULT_FCS_COMPARE_GRAPH_PROFILES.length]
}

const createDefaultFCSCompareGraphInstance = (title = "Overlay Graph 1", instanceIndex = 0): FCSCompareGraphInstance => ({
  id: `compare-graph-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  title,
  axisMode: "unified",
  unifiedAxis: { x: "FSC-A", y: "SSC-A" },
  primaryAxis: { x: "FSC-A", y: "SSC-A" },
  comparisonAxis: { x: "FSC-A", y: "SSC-A" },
  scatterDensityMode: getDefaultFCSCompareGraphProfile(instanceIndex).densityMode,
  scatterZoomPreset: getDefaultFCSCompareGraphProfile(instanceIndex).zoomPreset,
  showRawOverlayInDensity: getDefaultFCSCompareGraphProfile(instanceIndex).showRawOverlayInDensity,
  isMaximized: false,
  createdAt: Date.now(),
})

const initialFCSCompareGraphInstance = createDefaultFCSCompareGraphInstance()

const initialNTAAnalysis: NTAAnalysisState = {
  file: null,
  sampleId: null,
  results: null,
  isAnalyzing: false,
  error: null,
  experimentalConditions: null,
  fileMetadata: null,  // Will be populated from uploaded file
}

const initialSecondaryNTAAnalysis: SecondaryNTAAnalysisState = {
  file: null,
  sampleId: null,
  results: null,
  isAnalyzing: false,
  error: null,
}

const initialNTACompareSession: NTACompareSessionState = {
  selectedSampleIds: [],
  visibleSampleIds: [],
  primarySampleId: null,
  resultsBySampleId: {},
  loadingBySampleId: {},
  errorBySampleId: {},
  computedSeriesCacheByKey: {},
  maxVisibleOverlays: 8,
}

// Hydration state tracking
interface HydrationState {
  _hasHydrated: boolean
}

export const useAnalysisStore = create<AnalysisState & HydrationState>()(
  persist(
    (set) => ({
  // Hydration tracking
  _hasHydrated: false,
  
  // UI State
  activeTab: "dashboard",
  setActiveTab: (tab) => set({ activeTab: tab }),
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  sidebarWidth: DEFAULT_SIDEBAR_WIDTH,
  setSidebarWidth: (width) => set({ sidebarWidth: Math.min(MAX_SIDEBAR_WIDTH, Math.max(MIN_SIDEBAR_WIDTH, width)) }),
  isDarkMode: true,
  toggleDarkMode: () => set((state) => ({ isDarkMode: !state.isDarkMode })),

  // API Connection
  apiConnected: false,
  setApiConnected: (connected) => set({ apiConnected: connected }),
  apiChecking: false,
  setApiChecking: (checking) => set({ apiChecking: checking }),
  lastHealthCheck: null,
  setLastHealthCheck: (date) => set({ lastHealthCheck: date }),

  // Samples from Backend
  apiSamples: [],
  setApiSamples: (samples) => set({ apiSamples: samples }),
  addApiSample: (sample) =>
    set((state) => ({
      apiSamples: [...state.apiSamples, sample],
    })),
  removeApiSample: (sampleId) =>
    set((state) => ({
      apiSamples: state.apiSamples.filter((s) => s.sample_id !== sampleId),
    })),
  samplesLoading: false,
  setSamplesLoading: (loading) => set({ samplesLoading: loading }),
  samplesError: null,
  setSamplesError: (error) => set({ samplesError: error }),

  // Local samples
  samples: [],
  addSample: (sample) =>
    set((state) => ({
      samples: [...state.samples, sample],
    })),

  // FCS Analysis
  fcsAnalysis: initialFCSAnalysis,
  setFCSFile: (file) =>
    set((state) => ({
      fcsAnalysis: { ...state.fcsAnalysis, file },
    })),
  setFCSSampleId: (sampleId) =>
    set((state) => ({
      fcsAnalysis: { ...state.fcsAnalysis, sampleId },
    })),
  setFCSResults: (results) =>
    set((state) => ({
      fcsAnalysis: { ...state.fcsAnalysis, results },
    })),
  setFCSAnomalyData: (anomalyData) =>
    set((state) => ({
      fcsAnalysis: { ...state.fcsAnalysis, anomalyData },
    })),
  setFCSAnalyzing: (analyzing) =>
    set((state) => ({
      fcsAnalysis: { ...state.fcsAnalysis, isAnalyzing: analyzing },
    })),
  setFCSError: (error) =>
    set((state) => ({
      fcsAnalysis: { ...state.fcsAnalysis, error },
    })),
  setFCSExperimentalConditions: (conditions) =>
    set((state) => ({
      fcsAnalysis: { ...state.fcsAnalysis, experimentalConditions: conditions },
    })),
  setFCSSizeRanges: (sizeRanges) =>
    set((state) => ({
      fcsAnalysis: { ...state.fcsAnalysis, sizeRanges },
    })),
  setFCSFileMetadata: (metadata) =>
    set((state) => ({
      fcsAnalysis: { ...state.fcsAnalysis, fileMetadata: metadata },
    })),
  resetFCSAnalysis: () => set({ fcsAnalysis: initialFCSAnalysis }),

  // Secondary FCS Analysis (for comparison/overlay)
  secondaryFcsAnalysis: initialSecondaryFCSAnalysis,
  setSecondaryFCSFile: (file) =>
    set((state) => ({
      secondaryFcsAnalysis: { ...state.secondaryFcsAnalysis, file },
    })),
  setSecondaryFCSSampleId: (sampleId) =>
    set((state) => ({
      secondaryFcsAnalysis: { ...state.secondaryFcsAnalysis, sampleId },
    })),
  setSecondaryFCSResults: (results) =>
    set((state) => ({
      secondaryFcsAnalysis: { ...state.secondaryFcsAnalysis, results },
    })),
  setSecondaryFCSAnomalyData: (anomalyData) =>
    set((state) => ({
      secondaryFcsAnalysis: { ...state.secondaryFcsAnalysis, anomalyData },
    })),
  setSecondaryFCSAnalyzing: (analyzing) =>
    set((state) => ({
      secondaryFcsAnalysis: { ...state.secondaryFcsAnalysis, isAnalyzing: analyzing },
    })),
  setSecondaryFCSError: (error) =>
    set((state) => ({
      secondaryFcsAnalysis: { ...state.secondaryFcsAnalysis, error },
    })),
  setSecondaryFCSScatterData: (scatterData) =>
    set((state) => ({
      secondaryFcsAnalysis: { ...state.secondaryFcsAnalysis, scatterData },
    })),
  setSecondaryFCSLoadingScatter: (loading) =>
    set((state) => ({
      secondaryFcsAnalysis: { ...state.secondaryFcsAnalysis, loadingScatter: loading },
    })),
  resetSecondaryFCSAnalysis: () => set({ secondaryFcsAnalysis: initialSecondaryFCSAnalysis }),

  // Overlay Configuration
  overlayConfig: initialOverlayConfig,
  fcsCompareRequestVersion: 0,
  fcsCompareTelemetry: initialFCSCompareTelemetry,
  fcsSeriesCache: initialFCSSeriesCache,
  fcsCompareSession: initialFCSCompareSession,
  fcsCompareGraphInstances: [initialFCSCompareGraphInstance],
  activeFCSCompareGraphInstanceId: initialFCSCompareGraphInstance.id,
  incrementFCSCompareRequestVersion: () => {
    const nextVersion = useAnalysisStore.getState().fcsCompareRequestVersion + 1
    set({ fcsCompareRequestVersion: nextVersion })
    return nextVersion
  },
  resetFCSCompareRequestVersion: () => set({ fcsCompareRequestVersion: 0 }),
  recordFCSCompareLoadMetrics: ({ durationMs, queueDepth }) =>
    set((state) => {
      const safeDuration = Math.max(0, Math.round(durationMs))
      const safeQueueDepth = Math.max(0, Math.round(queueDepth))
      const totalLoads = state.fcsCompareTelemetry.totalLoads + 1
      const totalLoadMs = state.fcsCompareTelemetry.totalLoadMs + safeDuration

      return {
        fcsCompareTelemetry: {
          ...state.fcsCompareTelemetry,
          totalLoads,
          totalLoadMs,
          averageLoadMs: totalLoads > 0 ? Math.round(totalLoadMs / totalLoads) : 0,
          lastLoadMs: safeDuration,
          lastQueueDepth: safeQueueDepth,
          maxQueueDepth: Math.max(state.fcsCompareTelemetry.maxQueueDepth, safeQueueDepth),
          lastUpdatedAt: Date.now(),
        },
      }
    }),
  recordFCSCompareCacheStats: ({ hits = 0, misses = 0, evictions = 0 }) =>
    set((state) => ({
      fcsCompareTelemetry: {
        ...state.fcsCompareTelemetry,
        cacheHits: state.fcsCompareTelemetry.cacheHits + Math.max(0, Math.round(hits)),
        cacheMisses: state.fcsCompareTelemetry.cacheMisses + Math.max(0, Math.round(misses)),
        cacheEvictions: state.fcsCompareTelemetry.cacheEvictions + Math.max(0, Math.round(evictions)),
        lastUpdatedAt: Date.now(),
      },
    })),
  resetFCSCompareTelemetry: () => set({ fcsCompareTelemetry: initialFCSCompareTelemetry }),
  getFCSSeriesCacheEntry: (key) => {
    const state = useAnalysisStore.getState()
    const cache = state.fcsSeriesCache
    const entry = cache.entriesByKey[key]

    if (!entry || entry.version !== cache.version) {
      return null
    }

    set((currentState) => {
      const currentEntry = currentState.fcsSeriesCache.entriesByKey[key]
      if (!currentEntry) {
        return {}
      }

      return {
        fcsSeriesCache: {
          ...currentState.fcsSeriesCache,
          entriesByKey: {
            ...currentState.fcsSeriesCache.entriesByKey,
            [key]: {
              ...currentEntry,
              lastAccessedAt: Date.now(),
            },
          },
          lruKeys: [
            ...currentState.fcsSeriesCache.lruKeys.filter((cachedKey) => cachedKey !== key),
            key,
          ],
        },
      }
    })

    return entry
  },
  setFCSSeriesCacheEntry: ({ key, task, data, approxBytes }) => {
    let evicted = 0

    set((state) => {
      const cache = state.fcsSeriesCache
      const now = Date.now()
      const previous = cache.entriesByKey[key]
      const nextApproxBytes = Math.max(1, Math.round(approxBytes ?? 1024))

      const nextEntriesByKey: Record<string, FCSSeriesCacheEntry> = {
        ...cache.entriesByKey,
        [key]: {
          key,
          task,
          data,
          approxBytes: nextApproxBytes,
          version: cache.version,
          createdAt: previous?.createdAt ?? now,
          lastAccessedAt: now,
        },
      }

      let nextLruKeys = [...cache.lruKeys.filter((cachedKey) => cachedKey !== key), key]
      let nextTotalBytes = cache.totalBytes - (previous?.approxBytes ?? 0) + nextApproxBytes

      while (
        nextLruKeys.length > cache.maxEntries ||
        nextTotalBytes > cache.maxBytes
      ) {
        const candidateKey = nextLruKeys.shift()
        if (!candidateKey) break

        const candidate = nextEntriesByKey[candidateKey]
        if (!candidate) continue

        delete nextEntriesByKey[candidateKey]
        nextTotalBytes = Math.max(0, nextTotalBytes - candidate.approxBytes)
        evicted += 1
      }

      return {
        fcsSeriesCache: {
          ...cache,
          entriesByKey: nextEntriesByKey,
          lruKeys: nextLruKeys,
          totalBytes: nextTotalBytes,
        },
      }
    })

    return { evicted }
  },
  invalidateFCSSeriesCache: () =>
    set((state) => ({
      fcsSeriesCache: {
        ...initialFCSSeriesCache,
        version: state.fcsSeriesCache.version + 1,
        maxEntries: state.fcsSeriesCache.maxEntries,
        maxBytes: state.fcsSeriesCache.maxBytes,
      },
    })),
  setFCSSeriesCacheLimits: ({ maxEntries, maxBytes }) =>
    set((state) => ({
      fcsSeriesCache: {
        ...state.fcsSeriesCache,
        maxEntries: maxEntries ? Math.max(10, Math.min(1000, Math.round(maxEntries))) : state.fcsSeriesCache.maxEntries,
        maxBytes: maxBytes ? Math.max(1024 * 1024, Math.min(256 * 1024 * 1024, Math.round(maxBytes))) : state.fcsSeriesCache.maxBytes,
      },
    })),
  setFCSCompareSelectedSampleIds: (sampleIds) => set((state) => {
    const selectedSampleIds = Array.from(new Set(sampleIds)).slice(0, FCS_COMPARE_MAX_SELECTED)
    const maxVisible = state.fcsCompareSession.maxVisibleOverlays
    const existingVisible = state.fcsCompareSession.visibleSampleIds
      .filter((id) => selectedSampleIds.includes(id))
      .slice(0, maxVisible)
    const autoVisible = selectedSampleIds
      .filter((id) => !existingVisible.includes(id))
      .slice(0, maxVisible)
    const visibleSampleIds = Array.from(new Set([...existingVisible, ...autoVisible]))
      .slice(0, maxVisible)

    const currentPrimary = state.fcsCompareSession.primarySampleId
    const primarySampleId = currentPrimary && selectedSampleIds.includes(currentPrimary)
      ? currentPrimary
      : (selectedSampleIds[0] ?? null)

    const resultsBySampleId = Object.fromEntries(
      Object.entries(state.fcsCompareSession.resultsBySampleId).filter(([id]) => selectedSampleIds.includes(id))
    )
    const scatterBySampleId = Object.fromEntries(
      Object.entries(state.fcsCompareSession.scatterBySampleId).filter(([id]) => selectedSampleIds.includes(id))
    )
    const loadingBySampleId = Object.fromEntries(
      Object.entries(state.fcsCompareSession.loadingBySampleId).filter(([id]) => selectedSampleIds.includes(id))
    )
    const errorBySampleId = Object.fromEntries(
      Object.entries(state.fcsCompareSession.errorBySampleId).filter(([id]) => selectedSampleIds.includes(id))
    )
    const existingMetaById = state.fcsCompareSession.compareItemMetaById ?? {}
    const compareItemMetaById = Object.fromEntries(
      Object.entries(existingMetaById).filter(([id]) => selectedSampleIds.includes(id))
    )

    const selectedUnchanged = areStringArraysEqual(state.fcsCompareSession.selectedSampleIds, selectedSampleIds)
    const visibleUnchanged = areStringArraysEqual(state.fcsCompareSession.visibleSampleIds, visibleSampleIds)
    const primaryUnchanged = state.fcsCompareSession.primarySampleId === primarySampleId
    const resultsUnchanged = Object.keys(resultsBySampleId).length === Object.keys(state.fcsCompareSession.resultsBySampleId).length
    const scatterUnchanged = Object.keys(scatterBySampleId).length === Object.keys(state.fcsCompareSession.scatterBySampleId).length
    const loadingUnchanged = Object.keys(loadingBySampleId).length === Object.keys(state.fcsCompareSession.loadingBySampleId).length
    const errorUnchanged = Object.keys(errorBySampleId).length === Object.keys(state.fcsCompareSession.errorBySampleId).length
    const metaUnchanged = Object.keys(compareItemMetaById).length === Object.keys(existingMetaById).length

    if (
      selectedUnchanged
      && visibleUnchanged
      && primaryUnchanged
      && resultsUnchanged
      && scatterUnchanged
      && loadingUnchanged
      && errorUnchanged
      && metaUnchanged
    ) {
      return state
    }

    return {
      fcsCompareSession: {
        ...state.fcsCompareSession,
        selectedSampleIds,
        visibleSampleIds,
        primarySampleId,
        compareItemMetaById,
        resultsBySampleId,
        scatterBySampleId,
        loadingBySampleId,
        errorBySampleId,
      },
    }
  }),
  setFCSCompareVisibleSampleIds: (sampleIds) => set((state) => {
    const allowed = new Set(state.fcsCompareSession.selectedSampleIds)
    const visibleSampleIds = Array.from(new Set(sampleIds))
      .filter((id) => allowed.has(id))
      .slice(0, state.fcsCompareSession.maxVisibleOverlays)

    if (areStringArraysEqual(state.fcsCompareSession.visibleSampleIds, visibleSampleIds)) {
      return state
    }

    return {
      fcsCompareSession: {
        ...state.fcsCompareSession,
        visibleSampleIds,
      },
    }
  }),
  toggleFCSCompareSampleVisibility: (sampleId) => set((state) => {
    if (!state.fcsCompareSession.selectedSampleIds.includes(sampleId)) {
      return {}
    }

    const current = state.fcsCompareSession.visibleSampleIds
    const isVisible = current.includes(sampleId)
    const maxVisible = state.fcsCompareSession.maxVisibleOverlays
    const visibleSampleIds = isVisible
      ? current.filter((id) => id !== sampleId)
      : [...current, sampleId].slice(-maxVisible)

    return {
      fcsCompareSession: {
        ...state.fcsCompareSession,
        visibleSampleIds,
      },
    }
  }),
  setFCSComparePrimarySampleId: (sampleId) => set((state) => {
    if (sampleId && !state.fcsCompareSession.selectedSampleIds.includes(sampleId)) {
      return {}
    }
    return {
      fcsCompareSession: {
        ...state.fcsCompareSession,
        primarySampleId: sampleId,
      },
    }
  }),
  setFCSCompareSampleMeta: (sampleId, meta) => set((state) => ({
    fcsCompareSession: {
      ...state.fcsCompareSession,
      compareItemMetaById: {
        ...state.fcsCompareSession.compareItemMetaById,
        [sampleId]: {
          ...state.fcsCompareSession.compareItemMetaById[sampleId],
          compareItemId: sampleId,
          ...meta,
          uploadedAt: meta.uploadedAt ?? Date.now(),
        },
      },
    },
  })),
  setFCSCompareSampleLoading: (sampleId, loading) => set((state) => ({
    fcsCompareSession: {
      ...state.fcsCompareSession,
      loadingBySampleId: {
        ...state.fcsCompareSession.loadingBySampleId,
        [sampleId]: loading,
      },
    },
  })),
  setFCSCompareSampleError: (sampleId, error) => set((state) => ({
    fcsCompareSession: {
      ...state.fcsCompareSession,
      errorBySampleId: {
        ...state.fcsCompareSession.errorBySampleId,
        [sampleId]: error,
      },
    },
  })),
  setFCSCompareSampleResult: (sampleId, result) => set((state) => {
    const nextResults = { ...state.fcsCompareSession.resultsBySampleId }
    if (result) {
      nextResults[sampleId] = result
    } else {
      delete nextResults[sampleId]
    }

    return {
      fcsCompareSession: {
        ...state.fcsCompareSession,
        resultsBySampleId: nextResults,
      },
    }
  }),
  setFCSCompareSampleScatter: (sampleId, scatter) => set((state) => {
    const nextScatter = { ...state.fcsCompareSession.scatterBySampleId }
    if (scatter) {
      nextScatter[sampleId] = scatter
    } else {
      delete nextScatter[sampleId]
    }

    return {
      fcsCompareSession: {
        ...state.fcsCompareSession,
        scatterBySampleId: nextScatter,
      },
    }
  }),
  setFCSCompareMaxVisibleOverlays: (maxVisible) => set((state) => {
    const clamped = Math.max(1, Math.min(8, maxVisible))
    return {
      fcsCompareSession: {
        ...state.fcsCompareSession,
        maxVisibleOverlays: clamped,
        visibleSampleIds: state.fcsCompareSession.visibleSampleIds.slice(0, clamped),
      },
    }
  }),
  clearFCSCompareSession: () => set({ fcsCompareSession: initialFCSCompareSession }),
  createFCSCompareGraphInstance: (title) => {
    const instance = createDefaultFCSCompareGraphInstance(title, useAnalysisStore.getState().fcsCompareGraphInstances.length)
    set((state) => ({
      fcsCompareGraphInstances: [...state.fcsCompareGraphInstances, instance],
      activeFCSCompareGraphInstanceId: instance.id,
    }))
    return instance.id
  },
  duplicateFCSCompareGraphInstance: (instanceId) => {
    const state = useAnalysisStore.getState()
    const source = state.fcsCompareGraphInstances.find((instance) => instance.id === instanceId)
    if (!source) return null

    const duplicate: FCSCompareGraphInstance = {
      ...source,
      id: `compare-graph-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      title: `${source.title} Copy`,
      unifiedAxis: { ...source.unifiedAxis },
      primaryAxis: { ...source.primaryAxis },
      comparisonAxis: { ...source.comparisonAxis },
      isMaximized: false,
      createdAt: Date.now(),
    }

    set((currentState) => ({
      fcsCompareGraphInstances: [...currentState.fcsCompareGraphInstances, duplicate],
      activeFCSCompareGraphInstanceId: duplicate.id,
    }))

    return duplicate.id
  },
  removeFCSCompareGraphInstance: (instanceId) => set((state) => {
    const remaining = state.fcsCompareGraphInstances.filter((instance) => instance.id !== instanceId)
    if (remaining.length === 0) {
      const replacement = createDefaultFCSCompareGraphInstance("Overlay Graph 1")
      return {
        fcsCompareGraphInstances: [replacement],
        activeFCSCompareGraphInstanceId: replacement.id,
      }
    }

    const nextActive = state.activeFCSCompareGraphInstanceId === instanceId
      ? remaining[remaining.length - 1].id
      : state.activeFCSCompareGraphInstanceId

    return {
      fcsCompareGraphInstances: remaining,
      activeFCSCompareGraphInstanceId: nextActive,
    }
  }),
  setActiveFCSCompareGraphInstance: (instanceId) => set((state) => ({
    activeFCSCompareGraphInstanceId: state.fcsCompareGraphInstances.some((instance) => instance.id === instanceId)
      ? instanceId
      : state.activeFCSCompareGraphInstanceId,
  })),
  updateFCSCompareGraphInstance: (instanceId, updates) => set((state) => ({
    fcsCompareGraphInstances: state.fcsCompareGraphInstances.map((instance) =>
      instance.id === instanceId
        ? {
            ...instance,
            ...updates,
            unifiedAxis: updates.unifiedAxis ? { ...instance.unifiedAxis, ...updates.unifiedAxis } : instance.unifiedAxis,
            primaryAxis: updates.primaryAxis ? { ...instance.primaryAxis, ...updates.primaryAxis } : instance.primaryAxis,
            comparisonAxis: updates.comparisonAxis ? { ...instance.comparisonAxis, ...updates.comparisonAxis } : instance.comparisonAxis,
          }
        : instance
    ),
  })),
  setOverlayConfig: (config) =>
    set((state) => ({
      overlayConfig: { ...state.overlayConfig, ...config },
      fcsCompareRequestVersion: state.fcsCompareRequestVersion + 1,
      fcsSeriesCache: {
        ...initialFCSSeriesCache,
        version: state.fcsSeriesCache.version + 1,
        maxEntries: state.fcsSeriesCache.maxEntries,
        maxBytes: state.fcsSeriesCache.maxBytes,
      },
    })),
  toggleOverlay: () =>
    set((state) => ({
      overlayConfig: { ...state.overlayConfig, enabled: !state.overlayConfig.enabled },
      fcsCompareRequestVersion: state.fcsCompareRequestVersion + 1,
      fcsSeriesCache: {
        ...initialFCSSeriesCache,
        version: state.fcsSeriesCache.version + 1,
        maxEntries: state.fcsSeriesCache.maxEntries,
        maxBytes: state.fcsSeriesCache.maxBytes,
      },
    })),

  // NTA Analysis
  ntaAnalysis: initialNTAAnalysis,
  setNTAFile: (file) =>
    set((state) => ({
      ntaAnalysis: { ...state.ntaAnalysis, file },
    })),
  setNTASampleId: (sampleId) =>
    set((state) => ({
      ntaAnalysis: { ...state.ntaAnalysis, sampleId },
    })),
  setNTAResults: (results) =>
    set((state) => ({
      ntaAnalysis: { ...state.ntaAnalysis, results },
    })),
  setNTAAnalyzing: (analyzing) =>
    set((state) => ({
      ntaAnalysis: { ...state.ntaAnalysis, isAnalyzing: analyzing },
    })),
  setNTAError: (error) =>
    set((state) => ({
      ntaAnalysis: { ...state.ntaAnalysis, error },
    })),
  setNTAExperimentalConditions: (conditions) =>
    set((state) => ({
      ntaAnalysis: { ...state.ntaAnalysis, experimentalConditions: conditions },
    })),
  setNTAFileMetadata: (metadata) =>
    set((state) => ({
      ntaAnalysis: { ...state.ntaAnalysis, fileMetadata: metadata },
    })),
  resetNTAAnalysis: () => set({ ntaAnalysis: initialNTAAnalysis }),

  // Secondary NTA Analysis (for overlay comparison)
  secondaryNtaAnalysis: initialSecondaryNTAAnalysis,
  setSecondaryNTAFile: (file) =>
    set((state) => ({
      secondaryNtaAnalysis: { ...state.secondaryNtaAnalysis, file },
    })),
  setSecondaryNTASampleId: (sampleId) =>
    set((state) => ({
      secondaryNtaAnalysis: { ...state.secondaryNtaAnalysis, sampleId },
    })),
  setSecondaryNTAResults: (results) =>
    set((state) => ({
      secondaryNtaAnalysis: { ...state.secondaryNtaAnalysis, results },
    })),
  setSecondaryNTAAnalyzing: (analyzing) =>
    set((state) => ({
      secondaryNtaAnalysis: { ...state.secondaryNtaAnalysis, isAnalyzing: analyzing },
    })),
  setSecondaryNTAError: (error) =>
    set((state) => ({
      secondaryNtaAnalysis: { ...state.secondaryNtaAnalysis, error },
    })),
  resetSecondaryNTAAnalysis: () => set({ secondaryNtaAnalysis: initialSecondaryNTAAnalysis }),
  
  // NTA Overlay
  ntaOverlayEnabled: false,
  setNtaOverlayEnabled: (enabled) => set({ ntaOverlayEnabled: enabled }),
  ntaCompareSession: initialNTACompareSession,
  setNTACompareSelectedSampleIds: (sampleIds) => set((state) => {
    const selectedSampleIds = Array.from(new Set(sampleIds)).slice(0, 20)
    const maxVisible = state.ntaCompareSession.maxVisibleOverlays
    const existingVisible = state.ntaCompareSession.visibleSampleIds
      .filter((id) => selectedSampleIds.includes(id))
      .slice(0, maxVisible)

    const autoVisible = selectedSampleIds
      .filter((id) => !existingVisible.includes(id))
      .slice(0, maxVisible)

    const nextVisible = Array.from(new Set([...existingVisible, ...autoVisible]))
      .slice(0, maxVisible)

    const currentPrimary = state.ntaCompareSession.primarySampleId
    const primarySampleId = currentPrimary && selectedSampleIds.includes(currentPrimary)
      ? currentPrimary
      : (selectedSampleIds[0] ?? null)

    const resultsBySampleId = Object.fromEntries(
      Object.entries(state.ntaCompareSession.resultsBySampleId).filter(([id]) => selectedSampleIds.includes(id))
    )
    const loadingBySampleId = Object.fromEntries(
      Object.entries(state.ntaCompareSession.loadingBySampleId).filter(([id]) => selectedSampleIds.includes(id))
    )
    const errorBySampleId = Object.fromEntries(
      Object.entries(state.ntaCompareSession.errorBySampleId).filter(([id]) => selectedSampleIds.includes(id))
    )
    const computedSeriesCacheByKey = Object.fromEntries(
      Object.entries(state.ntaCompareSession.computedSeriesCacheByKey).filter(([, entry]) =>
        selectedSampleIds.includes(entry.sampleId)
      )
    )

    return {
      ntaCompareSession: {
        ...state.ntaCompareSession,
        selectedSampleIds,
        visibleSampleIds: nextVisible,
        primarySampleId,
        resultsBySampleId,
        loadingBySampleId,
        errorBySampleId,
        computedSeriesCacheByKey,
      },
    }
  }),
  setNTACompareVisibleSampleIds: (sampleIds) => set((state) => {
    const allowed = new Set(state.ntaCompareSession.selectedSampleIds)
    const visibleSampleIds = Array.from(new Set(sampleIds))
      .filter((id) => allowed.has(id))
      .slice(0, state.ntaCompareSession.maxVisibleOverlays)
    return {
      ntaCompareSession: {
        ...state.ntaCompareSession,
        visibleSampleIds,
      },
    }
  }),
  toggleNTACompareSampleVisibility: (sampleId) => set((state) => {
    if (!state.ntaCompareSession.selectedSampleIds.includes(sampleId)) {
      return {}
    }

    const current = state.ntaCompareSession.visibleSampleIds
    const isVisible = current.includes(sampleId)
    const maxVisible = state.ntaCompareSession.maxVisibleOverlays
    const visibleSampleIds = isVisible
      ? current.filter((id) => id !== sampleId)
      : [...current, sampleId].slice(-maxVisible)

    return {
      ntaCompareSession: {
        ...state.ntaCompareSession,
        visibleSampleIds,
      },
    }
  }),
  setNTAComparePrimarySampleId: (sampleId) => set((state) => {
    if (sampleId && !state.ntaCompareSession.selectedSampleIds.includes(sampleId)) {
      return {}
    }
    return {
      ntaCompareSession: {
        ...state.ntaCompareSession,
        primarySampleId: sampleId,
      },
    }
  }),
  setNTACompareSampleLoading: (sampleId, loading) => set((state) => ({
    ntaCompareSession: {
      ...state.ntaCompareSession,
      loadingBySampleId: {
        ...state.ntaCompareSession.loadingBySampleId,
        [sampleId]: loading,
      },
    },
  })),
  setNTACompareSampleError: (sampleId, error) => set((state) => ({
    ntaCompareSession: {
      ...state.ntaCompareSession,
      errorBySampleId: {
        ...state.ntaCompareSession.errorBySampleId,
        [sampleId]: error,
      },
    },
  })),
  setNTACompareSampleResult: (sampleId, result) => set((state) => {
    const nextResults = { ...state.ntaCompareSession.resultsBySampleId }
    if (result) {
      nextResults[sampleId] = result
    } else {
      delete nextResults[sampleId]
    }

    return {
      ntaCompareSession: {
        ...state.ntaCompareSession,
        resultsBySampleId: nextResults,
      },
    }
  }),
  setNTACompareComputedSeriesCacheEntry: (entry) => set((state) => ({
    ntaCompareSession: {
      ...state.ntaCompareSession,
      computedSeriesCacheByKey: {
        ...state.ntaCompareSession.computedSeriesCacheByKey,
        [entry.cacheKey]: entry,
      },
    },
  })),
  clearNTACompareComputedSeriesCache: () => set((state) => ({
    ntaCompareSession: {
      ...state.ntaCompareSession,
      computedSeriesCacheByKey: {},
    },
  })),
  setNTACompareMaxVisibleOverlays: (maxVisible) => set((state) => {
    const clamped = Math.max(1, Math.min(8, maxVisible))
    return {
      ntaCompareSession: {
        ...state.ntaCompareSession,
        maxVisibleOverlays: clamped,
        visibleSampleIds: state.ntaCompareSession.visibleSampleIds.slice(0, clamped),
      },
    }
  }),
  clearNTACompareSession: () => set({ ntaCompareSession: initialNTACompareSession }),

  // Processing Jobs
  processingJobs: [],
  addProcessingJob: (job) =>
    set((state) => ({
      processingJobs: [...state.processingJobs, job],
    })),
  updateProcessingJob: (jobId, updates) =>
    set((state) => ({
      processingJobs: state.processingJobs.map((job) =>
        job.id === jobId ? { ...job, ...updates } : job
      ),
    })),

  // Pinned Charts
  pinnedCharts: [],
  pinChart: (chart) =>
    set((state) => ({
      pinnedCharts: [...state.pinnedCharts, chart],
    })),
  unpinChart: (id) =>
    set((state) => ({
      pinnedCharts: state.pinnedCharts.filter((c) => c.id !== id),
    })),
  clearPinnedCharts: () => set({ pinnedCharts: [] }),

  // Chat
  chatMessages: [],
  addChatMessage: (message) =>
    set((state) => ({
      chatMessages: [...state.chatMessages, message],
    })),
  clearChatMessages: () => set({ chatMessages: [] }),

  // Saved Images Gallery
  savedImages: [],
  saveImage: (image) =>
    set((state) => ({
      savedImages: [...state.savedImages, image],
    })),
  removeImage: (id) =>
    set((state) => ({
      savedImages: state.savedImages.filter((img) => img.id !== id),
    })),
  clearSavedImages: () => set({ savedImages: [] }),

  // Analysis Settings — initialized with correct defaults so API calls
  // send the right params even before the user clicks "Re-Analyze"
  fcsAnalysisSettings: {
    laserWavelength: 405,
    particleRI: 1.37,
    mediumRI: 1.34,
    fscRange: [1, 65535] as [number, number],
    sscRange: [1, 65535] as [number, number],
    fscAngleRange: [1, 15] as [number, number],
    sscAngleRange: [85, 95] as [number, number],
    diameterRange: [30, 200] as [number, number],
    diameterPoints: 180,
    sizeRanges: [
      { name: "Exomeres (0-50nm)", min: 0, max: 50 },
      { name: "Small EVs (51-100nm)", min: 51, max: 100 },
      { name: "Medium EVs (101-150nm)", min: 101, max: 150 },
      { name: "Large EVs (151-200nm)", min: 151, max: 200 },
      { name: "Very Large EVs (200+nm)", min: 200, max: 1000 },
    ],
    ignoreNegativeH: true,
    dropNaRows: false,
    anomalyDetectionEnabled: true,
    anomalyMethod: "Both" as const,
    zscoreThreshold: 3.0,
    iqrFactor: 1.5,
    highlightAnomalies: true,
    useInteractivePlots: false,
    histogramBins: 50,
  },
  setFcsAnalysisSettings: (settings) => set((state) => ({ 
    fcsAnalysisSettings: state.fcsAnalysisSettings 
      ? { ...state.fcsAnalysisSettings, ...settings }
      : settings as FCSAnalysisSettings 
  })),
  ntaAnalysisSettings: defaultNTAAnalysisSettings,
  setNtaAnalysisSettings: (settings) => set((state) => ({
    ntaAnalysisSettings: { ...state.ntaAnalysisSettings, ...settings }
  })),
  ntaSizeProfiles: [defaultNTAQualityProfile, defaultNTAAnalysisProfile, defaultNTAReportProfile],
  selectedNTAAnalysisProfileId: defaultNTAAnalysisProfile.id,
  selectedNTAReportProfileId: defaultNTAReportProfile.id,
  ntaLockedBuckets: null,
  setSelectedNTAAnalysisProfileId: (profileId) => set((state) => {
    const exists = state.ntaSizeProfiles.some((p) => p.id === profileId)
    return exists ? { selectedNTAAnalysisProfileId: profileId } : {}
  }),
  setSelectedNTAReportProfileId: (profileId) => set((state) => {
    const exists = state.ntaSizeProfiles.some((p) => p.id === profileId)
    return exists ? { selectedNTAReportProfileId: profileId } : {}
  }),
  setNTALockedBuckets: (bins) => set({ ntaLockedBuckets: bins ? bins.map((b) => ({ ...b })) : null }),
  createNTASizeProfile: (profile) => set((state) => ({
    ntaSizeProfiles: [
      ...state.ntaSizeProfiles,
      {
        ...profile,
        createdAt: new Date().toISOString(),
      },
    ],
  })),
  updateNTASizeProfile: (profileId, updates) => set((state) => ({
    // Locked profiles are immutable by design for quality safety.
    ntaSizeProfiles: state.ntaSizeProfiles.map((profile) => {
      if (profile.id !== profileId) return profile
      if (profile.locked) return profile
      return {
        ...profile,
        ...updates,
        bins: updates.bins ?? profile.bins,
      }
    }),
  })),
  deleteNTASizeProfile: (profileId) => set((state) => {
    const target = state.ntaSizeProfiles.find((p) => p.id === profileId)
    if (!target || target.locked) {
      return {}
    }

    const nextProfiles = state.ntaSizeProfiles.filter((p) => p.id !== profileId)
    const nextAnalysisId = state.selectedNTAAnalysisProfileId === profileId
      ? defaultNTAAnalysisProfile.id
      : state.selectedNTAAnalysisProfileId
    const nextReportId = state.selectedNTAReportProfileId === profileId
      ? defaultNTAReportProfile.id
      : state.selectedNTAReportProfileId

    return {
      ntaSizeProfiles: nextProfiles,
      selectedNTAAnalysisProfileId: nextAnalysisId,
      selectedNTAReportProfileId: nextReportId,
    }
  }),
  resetNTASizeProfiles: () => set({
    ntaSizeProfiles: [defaultNTAQualityProfile, defaultNTAAnalysisProfile, defaultNTAReportProfile],
    selectedNTAAnalysisProfileId: defaultNTAAnalysisProfile.id,
    selectedNTAReportProfileId: defaultNTAReportProfile.id,
  }),
  crossComparisonSettings: {
    discrepancyThreshold: 15,
    normalizeHistograms: true,
    binSize: 5,
    showKde: true,
    showStatistics: true,
    minSizeFilter: 0,
    maxSizeFilter: 500,
    selectedFcsSampleId: "",
    selectedNtaSampleId: "",
  },
  setCrossComparisonSettings: (settings) => set({ crossComparisonSettings: settings }),

  // ============================================
  // GATING STATE & ACTIONS (T-009)
  // ============================================
  gatingState: initialGatingState,
  
  setGateActiveTool: (tool) =>
    set((state) => ({
      gatingState: { ...state.gatingState, activeTool: tool },
    })),
    
  addGate: (gate) =>
    set((state) => ({
      gatingState: {
        ...state.gatingState,
        gates: [...state.gatingState.gates, gate],
        activeGateId: gate.id,
      },
    })),
    
  removeGate: (gateId) =>
    set((state) => ({
      gatingState: {
        ...state.gatingState,
        gates: state.gatingState.gates.filter((g) => g.id !== gateId),
        activeGateId: state.gatingState.activeGateId === gateId ? null : state.gatingState.activeGateId,
      },
    })),
    
  updateGate: (gateId, updates) =>
    set((state) => ({
      gatingState: {
        ...state.gatingState,
        gates: state.gatingState.gates.map((g) =>
          g.id === gateId ? { ...g, ...updates } : g
        ),
      },
    })),
    
  setActiveGate: (gateId) =>
    set((state) => ({
      gatingState: { ...state.gatingState, activeGateId: gateId },
    })),
    
  setSelectedIndices: (indices) =>
    set((state) => ({
      gatingState: { ...state.gatingState, selectedIndices: indices },
    })),
    
  clearAllGates: () =>
    set((state) => ({
      gatingState: {
        ...state.gatingState,
        gates: [],
        activeGateId: null,
        selectedIndices: [],
        statistics: null,
      },
    })),
    
  resetGatingState: () =>
    set({ gatingState: initialGatingState }),
}),
    {
      name: 'ev-analysis-storage-v2', // rotated key to clear old sessionStorage cache
      // Use sessionStorage - persists on refresh, but clears when browser tab is closed
      storage: createJSONStorage(() => sessionStorage),
      // Selectively persist only important state (not File objects or transient state)
      partialize: (state) => ({
        // UI preferences
        activeTab: state.activeTab,
        sidebarCollapsed: state.sidebarCollapsed,
        sidebarWidth: state.sidebarWidth,
        isDarkMode: state.isDarkMode,
        // Analysis results (excluding File objects which can't be serialized)
        fcsAnalysis: {
          ...state.fcsAnalysis,
          file: null, // Don't persist File objects
          isAnalyzing: false,
        },
        secondaryFcsAnalysis: {
          ...state.secondaryFcsAnalysis,
          file: null,
          isAnalyzing: false,
        },
        ntaAnalysis: {
          ...state.ntaAnalysis,
          file: null,
          isAnalyzing: false,
        },
        secondaryNtaAnalysis: {
          ...state.secondaryNtaAnalysis,
          file: null,
          isAnalyzing: false,
        },
        // Settings
        overlayConfig: state.overlayConfig,
        ntaOverlayEnabled: state.ntaOverlayEnabled,
        fcsAnalysisSettings: state.fcsAnalysisSettings,
        ntaAnalysisSettings: state.ntaAnalysisSettings,
        ntaSizeProfiles: state.ntaSizeProfiles,
        selectedNTAAnalysisProfileId: state.selectedNTAAnalysisProfileId,
        selectedNTAReportProfileId: state.selectedNTAReportProfileId,
        ntaLockedBuckets: state.ntaLockedBuckets,
        fcsCompareSession: {
          ...state.fcsCompareSession,
          resultsBySampleId: {},
          scatterBySampleId: {},
          loadingBySampleId: {},
          errorBySampleId: {},
        },
        fcsCompareGraphInstances: state.fcsCompareGraphInstances,
        activeFCSCompareGraphInstanceId: state.activeFCSCompareGraphInstanceId,
        ntaCompareSession: {
          ...state.ntaCompareSession,
          resultsBySampleId: {},
          loadingBySampleId: {},
          errorBySampleId: {},
          computedSeriesCacheByKey: {},
        },
        crossComparisonSettings: state.crossComparisonSettings,
        // Gating state (preserve gates between refreshes)
        gatingState: {
          ...state.gatingState,
          isDrawing: false,
          drawingPoints: [],
        },
        // Chat history
        chatMessages: state.chatMessages,
        // Pinned charts and saved images (limit to avoid bloating sessionStorage)
        pinnedCharts: state.pinnedCharts.slice(0, 20),
        savedImages: state.savedImages.slice(0, 10),
        // Local samples (not API samples which should be re-fetched)
        samples: state.samples,
      }),
      // Handle date serialization/deserialization and mark hydration complete
      onRehydrateStorage: () => (state, error) => {
        if (error) {
          console.error('Zustand hydration error:', error)
        }
        if (state) {
          // Mark hydration as complete
          state._hasHydrated = true

          if (state.fcsCompareSession) {
            state.fcsCompareSession = normalizeFCSCompareSessionForHydration(state.fcsCompareSession)
          }

          // Migrate older sessions that persisted the previous overlay limit.
          if (state.ntaCompareSession?.maxVisibleOverlays && state.ntaCompareSession.maxVisibleOverlays < 8) {
            state.ntaCompareSession.maxVisibleOverlays = 8
          }

          if (!state.fcsCompareGraphInstances || state.fcsCompareGraphInstances.length === 0) {
            const replacement = createDefaultFCSCompareGraphInstance("Overlay Graph 1")
            state.fcsCompareGraphInstances = [replacement]
            state.activeFCSCompareGraphInstanceId = replacement.id
          } else {
            state.fcsCompareGraphInstances = state.fcsCompareGraphInstances.map((instance, index) => {
              const defaults = getDefaultFCSCompareGraphProfile(index)
              return {
                ...instance,
                scatterDensityMode: instance.scatterDensityMode ?? defaults.densityMode,
                scatterZoomPreset: instance.scatterZoomPreset ?? defaults.zoomPreset,
                showRawOverlayInDensity: instance.showRawOverlayInDensity ?? defaults.showRawOverlayInDensity,
              }
            })
          }

          if (!state.activeFCSCompareGraphInstanceId) {
            state.activeFCSCompareGraphInstanceId = state.fcsCompareGraphInstances[0]?.id ?? null
          }
          
          // Convert date strings back to Date objects
          if (state.chatMessages) {
            state.chatMessages = state.chatMessages.map(msg => ({
              ...msg,
              timestamp: new Date(msg.timestamp)
            }))
          }
          if (state.pinnedCharts) {
            state.pinnedCharts = state.pinnedCharts.map(chart => ({
              ...chart,
              timestamp: new Date(chart.timestamp)
            }))
          }
          if (state.savedImages) {
            state.savedImages = state.savedImages.map(img => ({
              ...img,
              timestamp: new Date(img.timestamp)
            }))
          }
          if (state.gatingState?.gates) {
            state.gatingState.gates = state.gatingState.gates.map(gate => ({
              ...gate,
              createdAt: new Date(gate.createdAt)
            }))
          }
          if (state.samples) {
            state.samples = state.samples.map(sample => ({
              ...sample,
              uploadedAt: new Date(sample.uploadedAt)
            }))
          }
        }
      },
      // Skip hydration on server side
      skipHydration: true,
    }
  )
)

// Helper hook for hydration status
export const useHasHydrated = () => {
  const [hasHydrated, setHasHydrated] = useState(false)
  
  useEffect(() => {
    // Manually trigger rehydration on client
    useAnalysisStore.persist.rehydrate()
    
    // Check hydration status
    const unsubFinishHydration = useAnalysisStore.persist.onFinishHydration(() => {
      setHasHydrated(true)
    })
    
    // If already hydrated (e.g., fast reload)
    if (useAnalysisStore.persist.hasHydrated()) {
      setHasHydrated(true)
    }
    
    return () => {
      unsubFinishHydration()
    }
  }, [])
  
  return hasHydrated
}

// ============================================================================
// PERFORMANCE: Focused selectors to prevent unnecessary re-renders.
// Use these instead of destructuring the full store in components.
// Each selector only triggers re-renders when its specific slice changes.
// ============================================================================

/** UI state only — doesn't re-render on data changes */
export const useUIState = () => useAnalysisStore(useShallow((s) => ({
  activeTab: s.activeTab,
  setActiveTab: s.setActiveTab,
  sidebarCollapsed: s.sidebarCollapsed,
  toggleSidebar: s.toggleSidebar,
  isDarkMode: s.isDarkMode,
  toggleDarkMode: s.toggleDarkMode,
})))

/** API connection state only */
export const useApiConnectionState = () => useAnalysisStore(useShallow((s) => ({
  apiConnected: s.apiConnected,
  setApiConnected: s.setApiConnected,
  apiChecking: s.apiChecking,
  setApiChecking: s.setApiChecking,
  lastHealthCheck: s.lastHealthCheck,
  setLastHealthCheck: s.setLastHealthCheck,
})))


