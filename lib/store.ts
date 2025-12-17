import { create } from "zustand"
import type { Sample as APISample, FCSResult, NTAResult, ProcessingJob } from "./api-client"

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
}

// NTA Analysis State
export interface NTAAnalysisState {
  file: File | null
  sampleId: string | null
  results: NTAResult | null
  isAnalyzing: boolean
  error: string | null
  experimentalConditions: ExperimentalConditions | null
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
  resetFCSAnalysis: () => void

  // NTA Analysis State
  ntaAnalysis: NTAAnalysisState
  setNTAFile: (file: File | null) => void
  setNTASampleId: (sampleId: string | null) => void
  setNTAResults: (results: NTAResult | null) => void
  setNTAAnalyzing: (analyzing: boolean) => void
  setNTAError: (error: string | null) => void
  setNTAExperimentalConditions: (conditions: ExperimentalConditions | null) => void
  resetNTAAnalysis: () => void

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
  setFcsAnalysisSettings: (settings: FCSAnalysisSettings) => void
  ntaAnalysisSettings: NTAAnalysisSettings | null
  setNtaAnalysisSettings: (settings: NTAAnalysisSettings) => void
  crossComparisonSettings: CrossComparisonSettings
  setCrossComparisonSettings: (settings: CrossComparisonSettings) => void
}

const initialFCSAnalysis: FCSAnalysisState = {
  file: null,
  sampleId: null,
  results: null,
  anomalyData: null,
  isAnalyzing: false,
  error: null,
  experimentalConditions: null,
  sizeRanges: [
    { name: "Small EVs", min: 30, max: 100, color: "#22c55e" },
    { name: "Medium EVs", min: 100, max: 200, color: "#3b82f6" },
    { name: "Large EVs", min: 200, max: 500, color: "#a855f7" },
  ],
}

const initialNTAAnalysis: NTAAnalysisState = {
  file: null,
  sampleId: null,
  results: null,
  isAnalyzing: false,
  error: null,
  experimentalConditions: null,
}

export const useAnalysisStore = create<AnalysisState>((set) => ({
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
  resetFCSAnalysis: () => set({ fcsAnalysis: initialFCSAnalysis }),

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
  resetNTAAnalysis: () => set({ ntaAnalysis: initialNTAAnalysis }),

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
  setFcsAnalysisSettings: (settings) => set({ fcsAnalysisSettings: settings }),
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
}))
