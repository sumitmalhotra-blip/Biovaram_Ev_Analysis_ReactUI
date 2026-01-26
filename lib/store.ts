 import { create } from "zustand"
import { persist, createJSONStorage } from "zustand/middleware"
import { useState, useEffect } from "react"
import type { Sample as APISample, FCSResult, NTAResult, ProcessingJob, FileMetadata } from "./api-client"

export type TabType = "dashboard" | "flow-cytometry" | "nta" | "cross-compare" | "research-chat"

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

// FCS Analysis Settings (matches Streamlit app.py)
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
// Client requested: Purple for normal, Red for anomalies (matches Streamlit)
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

// Cross-Comparison Settings
export interface CrossComparisonSettings {
  discrepancyThreshold: number
  normalizeHistograms: boolean
  binSize: number
  showKde: boolean
  showStatistics: boolean
  minSizeFilter: number
  maxSizeFilter: number
}

// NTA Analysis Settings (matches Streamlit app.py)
export interface NTAAnalysisSettings {
  applyTemperatureCorrection: boolean
  measurementTemp: number
  referenceTemp: number
  mediaType: string
  correctionFactor: number
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
  removeSample: (id: string) => void
  clearSamples: () => void

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

  // Processing Jobs
  processingJobs: ProcessingJob[]
  setProcessingJobs: (jobs: ProcessingJob[]) => void
  addProcessingJob: (job: ProcessingJob) => void
  updateProcessingJob: (jobId: string, updates: Partial<ProcessingJob>) => void
  removeProcessingJob: (jobId: string) => void

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
  updateImageMetadata: (id: string, metadata: Partial<SavedImage['metadata']>) => void

  // Cross-Compare Selection
  selectedFCSSample: APISample | null
  setSelectedFCSSample: (sample: APISample | null) => void
  selectedNTASample: APISample | null
  setSelectedNTASample: (sample: APISample | null) => void

  // Analysis Settings
  fcsAnalysisSettings: FCSAnalysisSettings | null
  setFcsAnalysisSettings: (settings: Partial<FCSAnalysisSettings>) => void
  ntaAnalysisSettings: NTAAnalysisSettings | null
  setNtaAnalysisSettings: (settings: NTAAnalysisSettings) => void
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
  setGateDrawing: (isDrawing: boolean) => void
  addDrawingPoint: (point: { x: number; y: number }) => void
  clearDrawingPoints: () => void
  setSelectedIndices: (indices: number[]) => void
  setGatedStatistics: (stats: GatedStatistics | null) => void
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
    { name: "Small EVs", min: 30, max: 100, color: "#22c55e" },
    { name: "Medium EVs", min: 100, max: 200, color: "#3b82f6" },
    { name: "Large EVs", min: 200, max: 500, color: "#a855f7" },
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
  removeSample: (id) =>
    set((state) => ({
      samples: state.samples.filter((s) => s.id !== id),
    })),
  clearSamples: () => set({ samples: [] }),

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
  setOverlayConfig: (config) =>
    set((state) => ({
      overlayConfig: { ...state.overlayConfig, ...config },
    })),
  toggleOverlay: () =>
    set((state) => ({
      overlayConfig: { ...state.overlayConfig, enabled: !state.overlayConfig.enabled },
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

  // Processing Jobs
  processingJobs: [],
  setProcessingJobs: (jobs) => set({ processingJobs: jobs }),
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
  removeProcessingJob: (jobId) =>
    set((state) => ({
      processingJobs: state.processingJobs.filter((job) => job.id !== jobId),
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
  updateImageMetadata: (id, metadata) =>
    set((state) => ({
      savedImages: state.savedImages.map((img) =>
        img.id === id
          ? { ...img, metadata: { ...img.metadata, ...metadata } }
          : img
      ),
    })),

  // Cross-Compare
  selectedFCSSample: null,
  setSelectedFCSSample: (sample) => set({ selectedFCSSample: sample }),
  selectedNTASample: null,
  setSelectedNTASample: (sample) => set({ selectedNTASample: sample }),

  // Analysis Settings
  fcsAnalysisSettings: null,
  setFcsAnalysisSettings: (settings) => set((state) => ({ 
    fcsAnalysisSettings: state.fcsAnalysisSettings 
      ? { ...state.fcsAnalysisSettings, ...settings }
      : settings as FCSAnalysisSettings 
  })),
  ntaAnalysisSettings: null,
  setNtaAnalysisSettings: (settings) => set({ ntaAnalysisSettings: settings }),
  crossComparisonSettings: {
    discrepancyThreshold: 15,
    normalizeHistograms: true,
    binSize: 5,
    showKde: true,
    showStatistics: true,
    minSizeFilter: 0,
    maxSizeFilter: 500,
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
    
  setGateDrawing: (isDrawing) =>
    set((state) => ({
      gatingState: { ...state.gatingState, isDrawing },
    })),
    
  addDrawingPoint: (point) =>
    set((state) => ({
      gatingState: {
        ...state.gatingState,
        drawingPoints: [...state.gatingState.drawingPoints, point],
      },
    })),
    
  clearDrawingPoints: () =>
    set((state) => ({
      gatingState: { ...state.gatingState, drawingPoints: [] },
    })),
    
  setSelectedIndices: (indices) =>
    set((state) => ({
      gatingState: { ...state.gatingState, selectedIndices: indices },
    })),
    
  setGatedStatistics: (stats) =>
    set((state) => ({
      gatingState: { ...state.gatingState, statistics: stats },
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
      name: 'ev-analysis-storage', // unique name for localStorage key
      storage: createJSONStorage(() => localStorage),
      // Selectively persist only important state (not File objects or transient state)
      partialize: (state) => ({
        // UI preferences
        activeTab: state.activeTab,
        sidebarCollapsed: state.sidebarCollapsed,
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
        crossComparisonSettings: state.crossComparisonSettings,
        // Gating state (preserve gates between refreshes)
        gatingState: {
          ...state.gatingState,
          isDrawing: false,
          drawingPoints: [],
        },
        // Chat history
        chatMessages: state.chatMessages,
        // Pinned charts and saved images
        pinnedCharts: state.pinnedCharts,
        savedImages: state.savedImages,
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
