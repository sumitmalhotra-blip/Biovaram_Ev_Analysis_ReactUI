/**
 * API Client for BioVaram EV Analysis Platform
 * Connects to FastAPI backend at localhost:8000
 */

// Get base URL and strip any trailing /api/v1 to prevent double prefix
let API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
// Safety: Remove trailing /api/v1 if present (prevents double prefix bug)
if (API_BASE_URL.endsWith("/api/v1")) {
  API_BASE_URL = API_BASE_URL.replace(/\/api\/v1$/, "");
}
const API_PREFIX = "/api/v1";

// Types matching backend models
export interface Sample {
  id: number;
  sample_id: string;
  biological_sample_id?: string;
  treatment?: string;
  concentration_ug?: number;
  preparation_method?: string;
  passage_number?: number;
  fraction_number?: string;
  qc_status?: string;
  processing_status?: string;
  operator?: string;
  notes?: string;
  upload_timestamp?: string;
  experiment_date?: string;
  files?: {
    fcs?: string;
    nta?: string;
    tem?: string;
  };
  results?: {
    fcs_count?: number;
    nta_count?: number;
    qc_reports_count?: number;
  };
}

export interface FCSResult {
  id?: number;  // Optional - may not be present in all contexts
  total_events: number;
  fsc_mean?: number;
  fsc_median?: number;
  ssc_mean?: number;
  ssc_median?: number;
  particle_size_median_nm?: number;
  particle_size_mean_nm?: number;  // Added for P-002 Excel Export
  cd81_positive_pct?: number;
  debris_pct?: number;
  processed_at?: string;
  channels?: string[];
  event_count?: number;
  sample_id?: string;
  size_distribution?: any;
  size_statistics?: {
    d10: number;
    d50: number;
    d90: number;
    mean: number;
    std: number;
  };
  // TASK-002: Size filtering statistics (Dec 17, 2025)
  size_filtering?: {
    total_input: number;
    valid_count: number;
    display_count: number;
    excluded_below: number;
    excluded_above: number;
    exclusion_pct: number;
  };
  excluded_particles_pct?: number;
  size_range?: {
    valid_min: number;
    valid_max: number;
    display_min: number;
    display_max: number;
  };
  // TASK-010: VSSC_MAX auto-selection statistics (Dec 17, 2025)
  // Parvesh: "Create a new column... VSSC max and let it look at the VSSC 1 H and VSSC 2 H 
  // and pick whichever the larger one is"
  vssc_max_used?: boolean;
  vssc_selection?: {
    vssc1_channel: string;
    vssc2_channel: string;
    vssc1_selected_count: number;
    vssc2_selected_count: number;
    vssc1_selected_pct: number;
    vssc2_selected_pct: number;
  };
  ssc_channel_used?: string;
  // Additional properties for P-002/P-003 Export features
  gated_events?: number;
  fsc_cv_pct?: number;
  ssc_cv_pct?: number;
  noise_events_removed?: number;
  // Multi-solution Mie statistics (returned by upload when VSSC+BSSC channels present)
  multi_solution_mie?: {
    available: boolean;
    used: boolean;
    vssc_channel?: string;
    bssc_channel?: string;
    stats?: {
      events_analyzed: number;
      events_with_1_solution: number;
      events_with_2_solutions: number;
      events_with_3_plus_solutions: number;
      d10?: number;
      d50?: number;
      d90?: number;
    };
  };
}

// Distribution Analysis Response types
export interface DistributionFit {
  name: string;
  params: Record<string, number>;
  aic: number;
  bic: number;
  ks_statistic: number;
  ks_pvalue: number;
  log_likelihood: number;
}

export interface DistributionOverlay {
  x: number[];
  y: number[];
  name: string;
}

export interface DistributionAnalysisResponse {
  sample_id: string;
  n_samples: number;
  normality_tests: {
    tests: Record<string, {
      statistic: number;
      p_value: number;
      is_normal: boolean;
    }>;
    is_normal: boolean;
    conclusion: string;
  };
  distribution_fits: {
    fits: Record<string, DistributionFit>;
    best_fit_aic: string;
    recommendation: string;
    recommendation_reason: string;
  };
  summary_statistics: {
    mean: number;
    median: number;
    d10: number;
    d50: number;
    d90: number;
    skewness: number;
    skew_interpretation: string;
    kurtosis?: number;
  };
  conclusion: {
    is_normal: boolean;
    recommended_distribution: string;
    use_median: boolean;
    central_tendency: number;
    central_tendency_metric: string;
  };
  overlays?: Record<string, DistributionOverlay>;
}

export interface NTAResult {
  id: number;
  mean_size_nm?: number;
  median_size_nm?: number;
  d10_nm?: number;
  d50_nm?: number;
  d90_nm?: number;
  concentration_particles_ml?: number;
  temperature_celsius?: number;
  ph?: number;
  total_particles?: number;
  bin_50_80nm_pct?: number;
  bin_80_100nm_pct?: number;
  bin_100_120nm_pct?: number;
  bin_120_150nm_pct?: number;
  bin_150_200nm_pct?: number;
  bin_200_plus_pct?: number;
  processed_at?: string;
  parquet_file?: string;
  size_distribution?: Array<{ size: number; count?: number; concentration?: number }>;
  size_statistics?: {
    d10: number;
    d50: number;
    d90: number;
    mean: number;
    std: number;
  };
  // TASK-007: PDF-extracted data (Dec 17, 2025)
  // Concentration and dilution from ZetaView PDF report
  pdf_data?: {
    original_concentration: number | null;
    dilution_factor: number | null;
    true_particle_population: number | null;
    mode_size_nm: number | null;
    pdf_file_name: string | null;
    extraction_successful: boolean;
  };
}

/**
 * VAL-001: Cross-Validation Result (FCS vs NTA)
 */
export interface CrossValidationResult {
  fcs_sample_id: string;
  nta_sample_id: string;
  mie_parameters: {
    wavelength_nm: number;
    n_particle: number;
    n_medium: number;
    method: string;
  };
  data_summary: {
    fcs_total_events: number;
    fcs_valid_sizes: number;
    nta_total_bins: number;
    nta_valid_bins: number;
    histogram_bins: number;
    size_range: [number, number];
    normalized: boolean;
  };
  fcs_statistics: {
    d10: number;
    d50: number;
    d90: number;
    mean: number;
    std: number;
    count: number;
  };
  nta_statistics: {
    d10: number;
    d50: number;
    d90: number;
    mean: number;
    std: number;
    count: number;
  };
  comparison: {
    d50_fcs: number;
    d50_nta: number;
    d50_difference_nm: number;
    d50_difference_pct: number;
    d10_difference_pct: number;
    d90_difference_pct: number;
    mean_difference_pct: number;
    verdict: "PASS" | "ACCEPTABLE" | "WARNING" | "FAIL";
    verdict_detail: string;
  };
  statistical_tests: {
    kolmogorov_smirnov: { statistic: number; p_value: number; interpretation: string };
    mann_whitney_u: { statistic: number; p_value: number; interpretation: string };
    bhattacharyya_coefficient: { value: number; interpretation: string };
  } | null;
  distribution: Array<{
    size: number;
    fcs: number;
    nta: number;
    fcs_raw: number;
    nta_raw: number;
  }>;
}

/**
 * TASK-009: Experimental Conditions interface
 * Stores metadata about experiment setup for reproducibility and AI analysis
 */

/**
 * CAL-001: Bead Calibration interfaces
 */
export interface CalibrationStatus {
  status: 'calibrated' | 'not_calibrated' | 'error';
  calibrated: boolean;
  message: string;
  instrument?: string;
  wavelength_nm?: number;
  fit_method?: string;
  r_squared?: number | null;
  n_bead_sizes?: number;
  calibration_range_nm?: [number, number];
  created_at?: string;
  bead_kit?: string;
  bead_lot?: string;
  bead_ri?: number;
  nist_traceable?: boolean;
}

export interface BeadStandard {
  file: string;
  filename: string;
  kit_part_number: string;
  product_name: string;
  lot_number: string;
  manufacturer: string;
  refractive_index: number;
  expiration_date: string;
  n_bead_sizes: number;
  bead_sizes_nm: number[];
}

export interface CalibrationBeadPoint {
  diameter_nm: number;
  scatter_mean: number;
  scatter_std: number;
  n_events: number;
  cv_pct: number;
}

export interface CalibrationCurvePoint {
  diameter_nm: number;
  scatter_predicted: number;
}

export interface ActiveCalibration {
  calibrated: boolean;
  calibration: {
    instrument: string;
    wavelength_nm: number;
    fit_method: string;
    fit_params: {
      a: number;
      b: number;
      r_squared: number;
    };
    calibration_range_nm: [number, number];
    created_at: string;
    bead_datasheet_info: {
      kit_part_number: string | null;
      lot_number: string | null;
      refractive_index: number;
      material: string;
      nist_traceable: boolean;
    };
    bead_points: CalibrationBeadPoint[];
    curve_points: CalibrationCurvePoint[];
    n_bead_sizes: number;
  } | null;
}

export interface CalibrationFitResult {
  success: boolean;
  message: string;
  set_as_active: boolean;
  saved_path?: string;
  diagnostics?: {
    datasheet: {
      kit: string;
      lot: string;
      ri: number;
      material: string;
      nist_traceable: boolean;
    };
    channel: string;
    wavelength_nm: number;
    n_peaks_detected: number;
    n_beads_matched: number;
    n_beads_expected: number;
    fit: Record<string, unknown>;
    bead_points: CalibrationBeadPoint[];
  };
}

export interface ExperimentalConditions {
  id: number;
  sample_id: number;
  operator: string;
  temperature_celsius?: number;
  ph?: number;
  substrate_buffer?: string;
  custom_buffer?: string;
  sample_volume_ul?: number;
  dilution_factor?: number;
  antibody_used?: string;
  antibody_concentration_ug?: number;
  incubation_time_min?: number;
  sample_type?: string;
  filter_size_um?: number;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ProcessingJob {
  id: string;
  job_type: string;
  status: string;
  sample_id?: number;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
}

// Metadata extracted from FCS/NTA files for auto-filling experimental conditions
export interface FileMetadata {
  operator?: string | null;
  acquisition_date?: string | null;
  acquisition_time?: string | null;
  temperature_celsius?: number | string | null;
  ph?: number | string | null;
  dilution_factor?: number | string | null;
  cytometer?: string | null;
  instrument?: string | null;
  sample_name?: string | null;
  specimen?: string | null;
  channels?: string[] | null;
  laser_wavelength_nm?: number | string | null;
  viscosity?: number | string | null;
  conductivity?: number | string | null;
}

export interface UploadResponse {
  success: boolean;
  id: number;
  sample_id: string;
  treatment?: string;
  concentration_ug?: number;
  preparation_method?: string;
  operator?: string;
  notes?: string;
  job_id: string;
  status: string;
  processing_status: string;
  message: string;
  fcs_results?: FCSResult;
  nta_results?: NTAResult;
  file_metadata?: FileMetadata;  // Auto-extracted metadata from file
}

export interface HealthResponse {
  status: string;
  timestamp?: string;
  version?: string;
}

export interface ApiError {
  detail: string;
  status_code?: number;
}

// Custom error class for network errors
export class NetworkError extends Error {
  constructor(message: string = "Network error - backend may be offline") {
    super(message);
    this.name = "NetworkError";
  }
}

class ApiClient {
  private baseUrl: string;
  private isOffline: boolean = false;
  private authToken: string | null = null;

  constructor() {
    // Build base URL, ensuring no double /api/v1 prefix
    let base = API_BASE_URL;
    // Strip any /api/v1 suffix that might have leaked in from env
    if (base.includes("/api/v1")) {
      base = base.replace(/\/api\/v1\/?$/, "");
      console.warn("[API Client] Stripped duplicate /api/v1 from base URL");
    }
    this.baseUrl = `${base}${API_PREFIX}`;
    console.log("[API Client] Base URL:", this.baseUrl);
  }

  // Set JWT auth token (called after login)
  setAuthToken(token: string | null): void {
    this.authToken = token;
  }

  // Get default headers including auth if available
  private getHeaders(contentType: string = "application/json"): Record<string, string> {
    const headers: Record<string, string> = { "Content-Type": contentType };
    if (this.authToken) {
      headers["Authorization"] = `Bearer ${this.authToken}`;
    }
    return headers;
  }

  // Check if the API is currently known to be offline
  get offline(): boolean {
    return this.isOffline;
  }

  // Get the base URL for the API
  getBaseUrl(): string {
    return this.baseUrl;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        detail: `HTTP error! status: ${response.status}`,
      }));
      throw new Error(errorData.detail || `Request failed with status ${response.status}`);
    }
    return response.json();
  }

  private handleNetworkError(error: unknown): never {
    this.isOffline = true;
    if (error instanceof TypeError && (error.message.includes("fetch") || error.message.includes("network"))) {
      throw new NetworkError();
    }
    throw error;
  }

  // =========================================================================
  // Health & Status
  // =========================================================================

  async checkHealth(): Promise<HealthResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/health`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      this.isOffline = false; // Backend is reachable
      return this.handleResponse<HealthResponse>(response);
    } catch (error) {
      this.isOffline = true;
      // Silently fail for health checks - don't spam console
      throw new NetworkError();
    }
  }

  async getStatus(): Promise<{ status: string; database: string; timestamp: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/status`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Status check failed:", error);
      throw error;
    }
  }

  // =========================================================================
  // File Upload
  // =========================================================================

  async uploadFCS(
    file: File,
    metadata?: {
      treatment?: string;
      concentration_ug?: number;
      preparation_method?: string;
      operator?: string;
      notes?: string;
      user_id?: number;
      wavelength_nm?: number;
      n_particle?: number;
      n_medium?: number;
    }
  ): Promise<UploadResponse> {
    try {
      const formData = new FormData();
      formData.append("file", file);

      if (metadata?.treatment) formData.append("treatment", metadata.treatment);
      if (metadata?.concentration_ug)
        formData.append("concentration_ug", metadata.concentration_ug.toString());
      if (metadata?.preparation_method)
        formData.append("preparation_method", metadata.preparation_method);
      if (metadata?.operator) formData.append("operator", metadata.operator);
      if (metadata?.notes) formData.append("notes", metadata.notes);
      if (metadata?.user_id) formData.append("user_id", metadata.user_id.toString());
      if (metadata?.wavelength_nm) formData.append("wavelength_nm", metadata.wavelength_nm.toString());
      if (metadata?.n_particle) formData.append("n_particle", metadata.n_particle.toString());
      if (metadata?.n_medium) formData.append("n_medium", metadata.n_medium.toString());

      const response = await fetch(`${this.baseUrl}/upload/fcs`, {
        method: "POST",
        body: formData,
      });

      this.isOffline = false;
      return this.handleResponse<UploadResponse>(response);
    } catch (error) {
      this.handleNetworkError(error);
    }
  }

  async uploadNTA(
    file: File,
    metadata?: {
      treatment?: string;
      temperature_celsius?: number;
      operator?: string;
      notes?: string;
      user_id?: number;
    }
  ): Promise<UploadResponse> {
    try {
      const formData = new FormData();
      formData.append("file", file);

      if (metadata?.treatment) formData.append("treatment", metadata.treatment);
      if (metadata?.temperature_celsius)
        formData.append("temperature_celsius", metadata.temperature_celsius.toString());
      if (metadata?.operator) formData.append("operator", metadata.operator);
      if (metadata?.notes) formData.append("notes", metadata.notes);
      if (metadata?.user_id) formData.append("user_id", metadata.user_id.toString());

      const response = await fetch(`${this.baseUrl}/upload/nta`, {
        method: "POST",
        body: formData,
      });

      this.isOffline = false;
      return this.handleResponse<UploadResponse>(response);
    } catch (error) {
      this.handleNetworkError(error);
    }
  }

  /**
   * TASK-007: Upload NTA PDF report to extract concentration and dilution factor
   * 
   * Client Quote (Surya, Dec 3, 2025):
   * "That number is not ever mentioned in a text format... it is always mentioned 
   * only in the PDF file"
   */
  async uploadNtaPdf(
    file: File,
    linkedSampleId?: string
  ): Promise<{
    success: boolean;
    pdf_file: string;
    pdf_data: {
      original_concentration: number | null;
      dilution_factor: number | null;
      true_particle_population: number | null;
      mean_size_nm: number | null;
      mode_size_nm: number | null;
      median_size_nm: number | null;
      d10_nm: number | null;
      d50_nm: number | null;
      d90_nm: number | null;
      sample_name: string | null;
      measurement_date: string | null;
      operator: string | null;
      extraction_successful: boolean;
      extraction_errors: string[];
    };
    linked_sample_id: string | null;
    message: string;
  }> {
    try {
      const formData = new FormData();
      formData.append("file", file);
      
      if (linkedSampleId) {
        formData.append("linked_sample_id", linkedSampleId);
      }

      const response = await fetch(`${this.baseUrl}/upload/nta-pdf`, {
        method: "POST",
        body: formData,
      });

      this.isOffline = false;
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] NTA PDF upload failed:", error);
      this.handleNetworkError(error);
    }
  }

  async uploadBatch(files: File[]): Promise<{
    success: boolean;
    uploaded: number;
    failed: number;
    job_ids: string[];
    details: Array<{ filename: string; sample_id: string; status: string }>;
  }> {
    try {
      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));

      const response = await fetch(`${this.baseUrl}/upload/batch`, {
        method: "POST",
        body: formData,
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Batch upload failed:", error);
      throw error;
    }
  }

  // =========================================================================
  // Samples
  // =========================================================================

  async listSamples(params?: {
    skip?: number;
    limit?: number;
    treatment?: string;
    qc_status?: string;
    processing_status?: string;
    user_id?: number;
  }): Promise<{ samples: Sample[]; total: number; skip: number; limit: number }> {
    try {
      const searchParams = new URLSearchParams();
      if (params?.skip) searchParams.append("skip", params.skip.toString());
      if (params?.limit) searchParams.append("limit", params.limit.toString());
      if (params?.treatment) searchParams.append("treatment", params.treatment);
      if (params?.qc_status) searchParams.append("qc_status", params.qc_status);
      if (params?.processing_status)
        searchParams.append("processing_status", params.processing_status);
      if (params?.user_id) searchParams.append("user_id", params.user_id.toString());

      const url = `${this.baseUrl}/samples${searchParams.toString() ? `?${searchParams}` : ""}`;
      const response = await fetch(url, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      this.isOffline = false;
      return this.handleResponse(response);
    } catch (error) {
      this.handleNetworkError(error);
    }
  }

  async getSample(sampleId: string): Promise<Sample> {
    try {
      const response = await fetch(`${this.baseUrl}/samples/${sampleId}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      this.isOffline = false;
      return this.handleResponse<Sample>(response);
    } catch (error) {
      this.handleNetworkError(error);
    }
  }

  async getFCSResults(sampleId: string): Promise<{ sample_id: string; results: FCSResult[] }> {
    try {
      const response = await fetch(`${this.baseUrl}/samples/${sampleId}/fcs`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      this.isOffline = false;
      return this.handleResponse(response);
    } catch (error) {
      this.handleNetworkError(error);
    }
  }

  async getNTAResults(sampleId: string): Promise<{ sample_id: string; results: NTAResult[] }> {
    try {
      const response = await fetch(`${this.baseUrl}/samples/${sampleId}/nta`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      this.isOffline = false;
      return this.handleResponse(response);
    } catch (error) {
      this.handleNetworkError(error);
    }
  }

  async deleteSample(sampleId: string): Promise<{
    success: boolean;
    message: string;
    deleted_records: {
      fcs_results: number;
      nta_results: number;
      qc_reports: number;
      processing_jobs: number;
    };
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/samples/${sampleId}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Delete sample failed:", error);
      throw error;
    }
  }

  // =========================================================================
  // Channel Configuration
  // =========================================================================

  /**
   * Get current FCS channel configuration (instruments, FSC/SSC channels).
   */
  async getChannelConfig(): Promise<{
    success: boolean;
    active_instrument: string;
    instruments: string[];
    fsc_channels: string[];
    ssc_channels: string[];
    preferred: {
      for_size_analysis: [string, string];
      for_scatter_plot: [string, string];
    };
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/samples/channel-config`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Get channel config failed:", error);
      throw error;
    }
  }

  /**
   * Update FCS channel configuration (active instrument, custom mapping).
   */
  async updateChannelConfig(params: {
    instrument?: string;
    fsc_channel?: string;
    ssc_channel?: string;
    save?: boolean;
  }): Promise<{
    success: boolean;
    message: string;
    active_instrument: string;
    preferred_fsc: string;
    preferred_ssc: string;
    saved: boolean;
  }> {
    try {
      const queryParams = new URLSearchParams();
      if (params.instrument) queryParams.set("instrument", params.instrument);
      if (params.fsc_channel) queryParams.set("fsc_channel", params.fsc_channel);
      if (params.ssc_channel) queryParams.set("ssc_channel", params.ssc_channel);
      if (params.save !== undefined) queryParams.set("save", String(params.save));

      const response = await fetch(`${this.baseUrl}/samples/channel-config?${queryParams}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
      });
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Update channel config failed:", error);
      throw error;
    }
  }

  /**
   * Get available channels for a specific FCS sample.
   */
  async getAvailableChannels(sampleId: string): Promise<{
    success: boolean;
    sample_id: string;
    channels_info: Array<{
      name: string;
      index: number;
      stats: { min: number; max: number; mean: number; std: number };
    }>;
    detected_fsc: string[];
    detected_ssc: string[];
    active_instrument: string;
    recommendation: { fsc: string; ssc: string };
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/samples/${sampleId}/available-channels`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Get available channels failed:", error);
      throw error;
    }
  }

  // =========================================================================
  // User Profile & Management
  // =========================================================================

  /**
   * Get user profile by ID.
   */
  async getUserProfile(userId: number): Promise<{
    id: number;
    email: string;
    name: string;
    role: string;
    organization: string;
    is_active: boolean;
    last_login?: string;
    created_at: string;
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/auth/me/${userId}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Get user profile failed:", error);
      throw error;
    }
  }

  /**
   * Update user profile (name, organization).
   */
  async updateUserProfile(userId: number, data: {
    name?: string;
    organization?: string;
  }): Promise<{
    id: number;
    email: string;
    name: string;
    role: string;
    organization: string;
    is_active: boolean;
    last_login?: string;
    created_at: string;
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/auth/profile/${userId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Update user profile failed:", error);
      throw error;
    }
  }

  /**
   * List all users (admin only).
   */
  async listUsers(skip: number = 0, limit: number = 100): Promise<Array<{
    id: number;
    email: string;
    name: string;
    role: string;
    organization: string;
    is_active: boolean;
    last_login?: string;
    created_at: string;
  }>> {
    try {
      const response = await fetch(`${this.baseUrl}/auth/users?skip=${skip}&limit=${limit}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] List users failed:", error);
      throw error;
    }
  }

  /**
   * Register a new user account.
   */
  async registerUser(data: {
    email: string;
    password: string;
    name: string;
    organization?: string;
    role?: string;
  }): Promise<{
    id: number;
    email: string;
    name: string;
    role: string;
    organization: string;
    is_active: boolean;
    created_at: string;
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Register user failed:", error);
      throw error;
    }
  }

  // =========================================================================
  // Experimental Conditions (TASK-009)
  // =========================================================================

  /**
   * TASK-009: Save experimental conditions for a sample
   * 
   * Client Quote (Parvesh, Dec 5, 2025):
   * "We'd also want a way to be able to log conditions for the experiment"
   * 
   * Store metadata for: temperature, pH, buffer, antibody, operator, etc.
   */
  async saveExperimentalConditions(
    sampleId: string,
    conditions: {
      operator: string;
      temperature_celsius?: number;
      ph?: number;
      substrate_buffer?: string;
      custom_buffer?: string;
      sample_volume_ul?: number;
      dilution_factor?: number;
      antibody_used?: string;
      antibody_concentration_ug?: number;
      incubation_time_min?: number;
      sample_type?: string;
      filter_size_um?: number;
      notes?: string;
    }
  ): Promise<{
    success: boolean;
    conditions_id: number;
    sample_id: string;
    conditions: ExperimentalConditions;
    message: string;
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/samples/${sampleId}/conditions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(conditions),
      });

      this.isOffline = false;
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Save experimental conditions failed:", error);
      this.handleNetworkError(error);
    }
  }

  async getExperimentalConditions(
    sampleId: string
  ): Promise<{
    sample_id: string;
    has_conditions: boolean;
    conditions: ExperimentalConditions | null;
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/samples/${sampleId}/conditions`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      this.isOffline = false;
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Get experimental conditions failed:", error);
      this.handleNetworkError(error);
    }
  }

  async updateExperimentalConditions(
    sampleId: string,
    conditions: Partial<{
      operator: string;
      temperature_celsius: number;
      ph: number;
      substrate_buffer: string;
      custom_buffer: string;
      sample_volume_ul: number;
      dilution_factor: number;
      antibody_used: string;
      antibody_concentration_ug: number;
      incubation_time_min: number;
      sample_type: string;
      filter_size_um: number;
      notes: string;
    }>
  ): Promise<{
    success: boolean;
    sample_id: string;
    conditions: ExperimentalConditions | null;
    message: string;
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/samples/${sampleId}/conditions`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(conditions),
      });

      this.isOffline = false;
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Update experimental conditions failed:", error);
      this.handleNetworkError(error);
    }
  }

  // =========================================================================
  // Processing Jobs
  // =========================================================================

  async listJobs(): Promise<{ jobs: ProcessingJob[]; total: number }> {
    try {
      const response = await fetch(`${this.baseUrl}/jobs`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] List jobs failed:", error);
      throw error;
    }
  }

  async getJob(jobId: string): Promise<ProcessingJob> {
    try {
      const response = await fetch(`${this.baseUrl}/jobs/${jobId}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      return this.handleResponse<ProcessingJob>(response);
    } catch (error) {
      console.error("[API] Get job failed:", error);
      throw error;
    }
  }

  async cancelJob(jobId: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/jobs/${jobId}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Cancel job failed:", error);
      throw error;
    }
  }

  async retryJob(jobId: string): Promise<{ success: boolean; new_job_id: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/jobs/${jobId}/retry`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Retry job failed:", error);
      throw error;
    }
  }

  // =========================================================================
  // Scatter Data & Size Binning
  // =========================================================================

  async getScatterData(
    sampleId: string,
    maxPoints: number = 5000
  ): Promise<{
    sample_id: string;
    total_events: number;
    returned_points: number;
    data: Array<{ x: number; y: number; index: number }>;
    channels: { fsc: string; ssc: string };
  }> {
    try {
      const response = await fetch(
        `${this.baseUrl}/samples/${sampleId}/scatter-data?max_points=${maxPoints}`,
        {
          method: "GET",
          headers: { "Content-Type": "application/json" },
        }
      );

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Get scatter data failed:", error);
      this.handleNetworkError(error);
    }
  }

  /**
   * Get clustered scatter data for progressive-zoom scatter plots.
   * Uses KMeans clustering at zoom levels 1-2 and raw points at zoom level 3.
   */
  async getClusteredScatter(
    sampleId: string,
    options?: {
      zoom_level?: number;
      fsc_channel?: string;
      ssc_channel?: string;
      viewport_x_min?: number;
      viewport_x_max?: number;
      viewport_y_min?: number;
      viewport_y_max?: number;
    }
  ): Promise<{
    sample_id: string;
    zoom_level: number;
    total_events: number;
    clusters: Array<{
      id: number; cx: number; cy: number; count: number;
      radius: number; std_x: number; std_y: number; pct: number;
      avg_diameter: number | null;
    }> | null;
    bounds: { x_min: number; x_max: number; y_min: number; y_max: number };
    viewport?: { x_min: number; x_max: number; y_min: number; y_max: number };
    channels: { fsc: string; ssc: string };
    individual_points: Array<{ x: number; y: number; index: number; diameter?: number }> | null;
  }> {
    try {
      const params = new URLSearchParams();
      if (options?.zoom_level != null) params.set("zoom_level", String(options.zoom_level));
      if (options?.fsc_channel) params.set("fsc_channel", options.fsc_channel);
      if (options?.ssc_channel) params.set("ssc_channel", options.ssc_channel);
      if (options?.viewport_x_min != null) params.set("viewport_x_min", String(options.viewport_x_min));
      if (options?.viewport_x_max != null) params.set("viewport_x_max", String(options.viewport_x_max));
      if (options?.viewport_y_min != null) params.set("viewport_y_min", String(options.viewport_y_min));
      if (options?.viewport_y_max != null) params.set("viewport_y_max", String(options.viewport_y_max));

      const response = await fetch(
        `${this.baseUrl}/samples/${sampleId}/clustered-scatter?${params.toString()}`,
        {
          method: "GET",
          headers: { "Content-Type": "application/json" },
        }
      );

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Get clustered scatter failed:", error);
      this.handleNetworkError(error);
    }
  }

  // =========================================================================
  // Distribution Analysis
  // =========================================================================

  /**
   * Get comprehensive distribution analysis including normality tests,
   * distribution fitting (Normal, Log-normal, Gamma, Weibull), and overlay curves.
   */
  async getDistributionAnalysis(
    sampleId: string,
    options?: {
      wavelength_nm?: number;
      n_particle?: number;
      n_medium?: number;
      include_overlays?: boolean;
    }
  ): Promise<DistributionAnalysisResponse> {
    try {
      const params = new URLSearchParams();
      if (options?.wavelength_nm) params.append("wavelength_nm", options.wavelength_nm.toString());
      if (options?.n_particle) params.append("n_particle", options.n_particle.toString());
      if (options?.n_medium) params.append("n_medium", options.n_medium.toString());
      if (options?.include_overlays !== undefined) params.append("include_overlays", options.include_overlays.toString());

      const queryString = params.toString();
      const url = `${this.baseUrl}/samples/${sampleId}/distribution-analysis${queryString ? `?${queryString}` : ""}`;

      const response = await fetch(url, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Get distribution analysis failed:", error);
      this.handleNetworkError(error);
    }
  }

  // =========================================================================
  // Auto Axis Selection (CRMIT-002)
  // =========================================================================

  /**
   * Get AI-recommended optimal axis pairs for scatter plot visualization.
   * Uses intelligent analysis based on variance, correlation, and cytometry best practices.
   */
  async getRecommendedAxes(
    sampleId: string,
    options?: {
      nRecommendations?: number;
      includeScatter?: boolean;
      includeFluorescence?: boolean;
    }
  ): Promise<{
    sample_id: string;
    total_events: number;
    recommendations: Array<{
      rank: number;
      x_channel: string;
      y_channel: string;
      score: number;
      reason: string;
      description: string;
    }>;
    channels: {
      scatter: string[];
      fluorescence: string[];
      all: string[];
    };
  }> {
    try {
      const params = new URLSearchParams();
      if (options?.nRecommendations) {
        params.append("n_recommendations", options.nRecommendations.toString());
      }
      if (options?.includeScatter !== undefined) {
        params.append("include_scatter", options.includeScatter.toString());
      }
      if (options?.includeFluorescence !== undefined) {
        params.append("include_fluorescence", options.includeFluorescence.toString());
      }

      const queryString = params.toString();
      const url = `${this.baseUrl}/samples/${sampleId}/recommend-axes${queryString ? `?${queryString}` : ""}`;

      const response = await fetch(url, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Get recommended axes failed:", error);
      this.handleNetworkError(error);
    }
  }

  /**
   * Get scatter data with custom axis selection
   */
  async getScatterDataWithAxes(
    sampleId: string,
    xChannel: string,
    yChannel: string,
    maxPoints: number = 5000,
    mieParams?: {
      wavelength_nm?: number;
      n_particle?: number;
      n_medium?: number;
    }
  ): Promise<{
    sample_id: string;
    total_events: number;
    returned_points: number;
    data: Array<{ x: number; y: number; index: number; diameter?: number }>;
    channels: { fsc: string; ssc: string; available: string[] };
  }> {
    try {
      const params = new URLSearchParams({
        max_points: maxPoints.toString(),
        fsc_channel: xChannel,
        ssc_channel: yChannel,
      });
      
      // Add Mie parameters if provided
      if (mieParams?.wavelength_nm) {
        params.append("wavelength_nm", mieParams.wavelength_nm.toString());
      }
      if (mieParams?.n_particle) {
        params.append("n_particle", mieParams.n_particle.toString());
      }
      if (mieParams?.n_medium) {
        params.append("n_medium", mieParams.n_medium.toString());
      }

      const response = await fetch(
        `${this.baseUrl}/samples/${sampleId}/scatter-data?${params.toString()}`,
        {
          method: "GET",
          headers: { "Content-Type": "application/json" },
        }
      );

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Get scatter data with axes failed:", error);
      this.handleNetworkError(error);
    }
  }

  /**
   * Analyze gated (selected) population from scatter plot
   * T-009: Population Gating & Selection Analysis
   */
  async analyzeGatedPopulation(
    sampleId: string,
    gateConfig: {
      gate_name: string;
      gate_type: "rectangle" | "polygon" | "ellipse";
      gate_coordinates: {
        // Rectangle
        x1?: number;
        y1?: number;
        x2?: number;
        y2?: number;
        // Polygon
        points?: Array<{ x: number; y: number }>;
        // Ellipse
        cx?: number;
        cy?: number;
        rx?: number;
        ry?: number;
        rotation?: number;
      };
      x_channel: string;
      y_channel: string;
      include_diameter_stats?: boolean;
      // Mie parameters for size calculations
      wavelength_nm?: number;
      n_particle?: number;
      n_medium?: number;
    }
  ): Promise<{
    sample_id: string;
    gate_name: string;
    gate_type: string;
    gate_coordinates: Record<string, unknown>;
    total_events: number;
    gated_events: number;
    gated_percentage: number;
    gated_indices: number[];
    statistics: {
      x_channel: {
        channel: string;
        count: number;
        mean: number;
        median: number;
        std: number;
        min: number;
        max: number;
        cv: number;
        q25: number;
        q75: number;
        iqr: number;
      };
      y_channel: {
        channel: string;
        count: number;
        mean: number;
        median: number;
        std: number;
        min: number;
        max: number;
        cv: number;
        q25: number;
        q75: number;
        iqr: number;
      };
      diameter: {
        channel: string;
        count: number;
        mean: number;
        median: number;
        std: number;
        min: number;
        max: number;
        cv: number;
        q25: number;
        q75: number;
        iqr: number;
      } | null;
    } | null;
    percentiles: {
      D10: number;
      D50: number;
      D90: number;
      mean: number;
      mode_estimate: number;
    } | null;
    comparison_to_total: {
      x_mean_diff_percent: number;
      y_mean_diff_percent: number;
      enrichment_factor: number;
      total_x_mean: number;
      total_y_mean: number;
      total_x_std: number;
      total_y_std: number;
    } | null;
    message?: string;
  }> {
    try {
      const response = await fetch(
        `${this.baseUrl}/samples/${sampleId}/gated-analysis`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(gateConfig),
        }
      );

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Gated analysis failed:", error);
      this.handleNetworkError(error);
    }
  }

  async getSizeBins(
    sampleId: string,
    mieParams?: {
      wavelength_nm?: number;
      n_particle?: number;
      n_medium?: number;
    }
  ): Promise<{
    sample_id: string;
    total_events: number;
    bins: {
      small: number;
      medium: number;
      large: number;
    };
    percentages: {
      small: number;
      medium: number;
      large: number;
    };
    thresholds: {
      small_max: number;
      medium_min: number;
      medium_max: number;
      large_min: number;
    };
  }> {
    try {
      const params = new URLSearchParams();
      
      // Add Mie parameters if provided
      if (mieParams?.wavelength_nm) {
        params.append("wavelength_nm", mieParams.wavelength_nm.toString());
      }
      if (mieParams?.n_particle) {
        params.append("n_particle", mieParams.n_particle.toString());
      }
      if (mieParams?.n_medium) {
        params.append("n_medium", mieParams.n_medium.toString());
      }
      
      const queryString = params.toString();
      const url = queryString 
        ? `${this.baseUrl}/samples/${sampleId}/size-bins?${queryString}`
        : `${this.baseUrl}/samples/${sampleId}/size-bins`;
      
      const response = await fetch(url, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Get size bins failed:", error);
      this.handleNetworkError(error);
    }
  }

  /**
   * Run anomaly detection on a sample
   */
  async detectAnomalies(
    sampleId: string,
    options?: {
      method?: "zscore" | "iqr" | "both";
      zscore_threshold?: number;
      iqr_factor?: number;
    }
  ): Promise<{
    sample_id: string;
    enabled: boolean;
    method: string;
    total_anomalies: number;
    anomaly_percentage: number;
    anomalous_indices: number[];
    settings: {
      zscore_threshold: number;
      iqr_factor: number;
    };
  }> {
    try {
      const params = new URLSearchParams();
      if (options?.method) params.append("method", options.method);
      if (options?.zscore_threshold) params.append("zscore_threshold", options.zscore_threshold.toString());
      if (options?.iqr_factor) params.append("iqr_factor", options.iqr_factor.toString());

      const queryString = params.toString();
      const url = `${this.baseUrl}/samples/${sampleId}/anomaly-detection${queryString ? `?${queryString}` : ""}`;
      
      const response = await fetch(url, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Anomaly detection failed:", error);
      this.handleNetworkError(error);
    }
  }

  /**
   * Re-analyze a sample with custom settings
   */
  async reanalyzeSample(
    sampleId: string,
    settings: {
      wavelength_nm?: number;
      n_particle?: number;
      n_medium?: number;
      fsc_angle_range?: [number, number];
      ssc_angle_range?: [number, number];
      anomaly_detection?: boolean;
      anomaly_method?: string;
      zscore_threshold?: number;
      iqr_factor?: number;
      size_ranges?: Array<{ name: string; min: number; max: number }>;
    }
  ): Promise<{
    sample_id: string;
    analysis_settings: {
      wavelength_nm: number;
      n_particle: number;
      n_medium: number;
      anomaly_detection: boolean;
      anomaly_method?: string;
    };
    results: {
      total_events: number;
      channels: string[];
      fsc_channel: string | null;
      ssc_channel: string | null;
      fsc_mean: number | null;
      fsc_median: number | null;
      ssc_mean: number | null;
      ssc_median: number | null;
      particle_size_median_nm: number | null;
      size_statistics: {
        d10: number;
        d50: number;
        d90: number;
        mean: number;
        std: number;
      } | null;
      custom_size_bins: Record<string, { count: number; percentage: number }>;
    };
    anomaly_data: {
      enabled: boolean;
      method: string;
      total_anomalies: number;
      anomaly_percentage: number;
      anomalous_indices: number[];
    } | null;
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/samples/${sampleId}/reanalyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Reanalyze sample failed:", error);
      this.handleNetworkError(error);
    }
  }

  // =========================================================================
  // Statistical Analysis
  // =========================================================================

  async runStatisticalTests(
    groupA: string[],
    groupB: string[],
    options?: {
      metrics?: string[];
      testTypes?: string[];
      alpha?: number;
    }
  ): Promise<{
    success: boolean;
    message: string;
    group_a_samples: string[];
    group_b_samples: string[];
    comparisons: Array<{
      metric: string;
      group_a_stats: {
        group_name: string;
        n_samples: number;
        mean: number;
        std: number;
        median: number;
        min_val: number;
        max_val: number;
      };
      group_b_stats: {
        group_name: string;
        n_samples: number;
        mean: number;
        std: number;
        median: number;
        min_val: number;
        max_val: number;
      };
      tests: Array<{
        test_name: string;
        metric: string;
        statistic: number;
        p_value: number;
        significant: boolean;
        effect_size: number | null;
        interpretation: string;
      }>;
    }>;
    summary: {
      total_tests: number;
      significant_tests: number;
      significance_level: number;
      metrics_compared: number;
    };
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/analysis/statistical-tests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sample_ids_group_a: groupA,
          sample_ids_group_b: groupB,
          metrics: options?.metrics || ["fsc_median", "ssc_median", "particle_size_median_nm"],
          test_types: options?.testTypes || ["mann_whitney", "ks_test"],
          alpha: options?.alpha || 0.05,
        }),
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Statistical tests failed:", error);
      this.handleNetworkError(error);
    }
  }

  async compareDistributions(
    sampleIdA: string,
    sampleIdB: string,
    channel: string = "FSC"
  ): Promise<{
    success: boolean;
    sample_a: {
      sample_id: string;
      channel: string;
      n_events: number;
      mean: number;
      median: number;
      std: number;
    };
    sample_b: {
      sample_id: string;
      channel: string;
      n_events: number;
      mean: number;
      median: number;
      std: number;
    };
    histograms: {
      bins: number[];
      sample_a: number[];
      sample_b: number[];
    };
    ks_test: {
      statistic: number;
      p_value: number;
      significant: boolean;
    };
  }> {
    try {
      const response = await fetch(
        `${this.baseUrl}/analysis/distribution-comparison?sample_id_a=${sampleIdA}&sample_id_b=${sampleIdB}&channel=${channel}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        }
      );

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Distribution comparison failed:", error);
      this.handleNetworkError(error);
    }
  }

  // =========================================================================
  // Export Functions
  // =========================================================================

  async exportToParquet(
    sampleId: string,
    dataType: "fcs" | "nta",
    options?: {
      includeMetadata?: boolean;
      includeStatistics?: boolean;
    }
  ): Promise<{
    success: boolean;
    filename: string;
    content_base64: string;
    size_bytes: number;
    metadata: {
      sample_id: string;
      data_type: string;
      export_timestamp: string;
    };
    columns: string[];
    rows: number;
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/analysis/export/parquet`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sample_id: sampleId,
          data_type: dataType,
          include_metadata: options?.includeMetadata ?? true,
          include_statistics: options?.includeStatistics ?? true,
        }),
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Parquet export failed:", error);
      this.handleNetworkError(error);
    }
  }

  // Download the parquet file from base64 response
  async downloadParquet(
    sampleId: string,
    dataType: "fcs" | "nta",
    options?: {
      includeMetadata?: boolean;
      includeStatistics?: boolean;
    }
  ): Promise<void> {
    const result = await this.exportToParquet(sampleId, dataType, options);
    
    if (result.success && result.content_base64) {
      // Decode base64 to binary
      const binaryString = atob(result.content_base64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      
      // Create blob and download
      const blob = new Blob([bytes], { type: 'application/octet-stream' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = result.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  }

  // =========================================================================
  // Alerts API (CRMIT-003)
  // =========================================================================

  /**
   * Alert type definitions
   */
  async getAlerts(options?: {
    userId?: number;
    sampleId?: number;
    severity?: "info" | "warning" | "critical" | "error";
    alertType?: string;
    isAcknowledged?: boolean;
    source?: string;
    limit?: number;
    offset?: number;
    orderBy?: string;
    orderDesc?: boolean;
  }): Promise<{
    alerts: Array<{
      id: number;
      sample_id: number | null;
      user_id: number | null;
      alert_type: string;
      severity: string;
      title: string;
      message: string;
      source: string;
      sample_name: string | null;
      metadata: Record<string, any> | null;
      is_acknowledged: boolean;
      acknowledged_by: number | null;
      acknowledged_at: string | null;
      acknowledgment_notes: string | null;
      created_at: string;
      updated_at: string;
    }>;
    total: number;
    limit: number;
    offset: number;
  }> {
    try {
      const params = new URLSearchParams();
      if (options?.userId) params.append("user_id", options.userId.toString());
      if (options?.sampleId) params.append("sample_id", options.sampleId.toString());
      if (options?.severity) params.append("severity", options.severity);
      if (options?.alertType) params.append("alert_type", options.alertType);
      if (options?.isAcknowledged !== undefined) params.append("is_acknowledged", options.isAcknowledged.toString());
      if (options?.source) params.append("source", options.source);
      if (options?.limit) params.append("limit", options.limit.toString());
      if (options?.offset) params.append("offset", options.offset.toString());
      if (options?.orderBy) params.append("order_by", options.orderBy);
      if (options?.orderDesc !== undefined) params.append("order_desc", options.orderDesc.toString());

      const queryString = params.toString();
      const url = `${this.baseUrl}/alerts${queryString ? `?${queryString}` : ""}`;

      const response = await fetch(url, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Get alerts failed:", error);
      this.handleNetworkError(error);
    }
  }

  async getAlertCounts(userId?: number): Promise<{
    total: number;
    unacknowledged: number;
    acknowledged: number;
    by_severity: {
      critical: number;
      error: number;
      warning: number;
      info: number;
    };
  }> {
    try {
      const params = userId ? `?user_id=${userId}` : "";
      const response = await fetch(`${this.baseUrl}/alerts/counts${params}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Get alert counts failed:", error);
      this.handleNetworkError(error);
    }
  }

  async getAlert(alertId: number): Promise<{
    id: number;
    sample_id: number | null;
    user_id: number | null;
    alert_type: string;
    severity: string;
    title: string;
    message: string;
    source: string;
    sample_name: string | null;
    metadata: Record<string, any> | null;
    is_acknowledged: boolean;
    acknowledged_by: number | null;
    acknowledged_at: string | null;
    acknowledgment_notes: string | null;
    created_at: string;
    updated_at: string;
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/alerts/${alertId}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Get alert failed:", error);
      this.handleNetworkError(error);
    }
  }

  async acknowledgeAlert(
    alertId: number,
    options?: {
      acknowledgedBy?: number;
      notes?: string;
    }
  ): Promise<{
    message: string;
    alert: {
      id: number;
      is_acknowledged: boolean;
      acknowledged_at: string;
      acknowledgment_notes: string | null;
    };
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/alerts/${alertId}/acknowledge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          acknowledged_by: options?.acknowledgedBy,
          notes: options?.notes,
        }),
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Acknowledge alert failed:", error);
      this.handleNetworkError(error);
    }
  }

  async acknowledgeMultipleAlerts(
    alertIds: number[],
    options?: {
      acknowledgedBy?: number;
      notes?: string;
    }
  ): Promise<{
    message: string;
    acknowledged_count: number;
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/alerts/acknowledge-multiple`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          alert_ids: alertIds,
          acknowledged_by: options?.acknowledgedBy,
          notes: options?.notes,
        }),
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Acknowledge multiple alerts failed:", error);
      this.handleNetworkError(error);
    }
  }

  async deleteAlert(alertId: number): Promise<{
    message: string;
    alert_id: number;
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/alerts/${alertId}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Delete alert failed:", error);
      this.handleNetworkError(error);
    }
  }

  // ============================================================================
  // Population Shift Detection (CRMIT-004)
  // ============================================================================

  /**
   * Detect population shift between two samples
   */
  async detectPopulationShift(options: {
    sample_id_a: string;
    sample_id_b: string;
    metric?: string;
    data_source?: "fcs" | "nta";
    tests?: Array<"ks" | "emd" | "mean" | "variance">;
    alpha?: number;
  }): Promise<PopulationShiftResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/analysis/population-shift`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sample_id_a: options.sample_id_a,
          sample_id_b: options.sample_id_b,
          metric: options.metric || "particle_size",
          data_source: options.data_source || "fcs",
          tests: options.tests || ["ks", "emd", "mean", "variance"],
          alpha: options.alpha || 0.05,
        }),
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Population shift detection failed:", error);
      this.handleNetworkError(error);
    }
  }

  /**
   * Compare multiple samples against a baseline
   */
  async compareToBaseline(options: {
    baseline_sample_id: string;
    sample_ids: string[];
    metric?: string;
    data_source?: "fcs" | "nta";
    tests?: Array<"ks" | "emd" | "mean" | "variance">;
    alpha?: number;
  }): Promise<MultiSampleShiftResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/analysis/population-shift/baseline`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          baseline_sample_id: options.baseline_sample_id,
          sample_ids: options.sample_ids,
          metric: options.metric || "particle_size",
          data_source: options.data_source || "fcs",
          tests: options.tests || ["ks", "emd", "mean", "variance"],
          alpha: options.alpha || 0.05,
        }),
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Baseline comparison failed:", error);
      this.handleNetworkError(error);
    }
  }

  /**
   * Temporal/sequential population shift analysis
   */
  async temporalShiftAnalysis(options: {
    sample_ids: string[];
    metric?: string;
    data_source?: "fcs" | "nta";
    tests?: Array<"ks" | "emd" | "mean" | "variance">;
    alpha?: number;
  }): Promise<MultiSampleShiftResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/analysis/population-shift/temporal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sample_ids: options.sample_ids,
          metric: options.metric || "particle_size",
          data_source: options.data_source || "fcs",
          tests: options.tests || ["ks", "emd", "mean", "variance"],
          alpha: options.alpha || 0.05,
        }),
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Temporal shift analysis failed:", error);
      this.handleNetworkError(error);
    }
  }

  // ============================================================================
  // CRMIT-007: Temporal Analysis Methods
  // ============================================================================

  /**
   * Analyze temporal trends for a single metric across samples
   */
  async analyzeTemporalTrends(options: {
    sample_ids: string[];
    metric?: string;
    data_source?: "fcs" | "nta";
    alpha?: number;
    include_correlations?: boolean;
  }): Promise<TemporalAnalysisResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/analysis/temporal-analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sample_ids: options.sample_ids,
          metric: options.metric || "particle_size",
          data_source: options.data_source || "fcs",
          alpha: options.alpha || 0.05,
          include_correlations: options.include_correlations !== false,
        }),
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Temporal analysis failed:", error);
      this.handleNetworkError(error);
    }
  }

  /**
   * Analyze multiple metrics over time
   */
  async analyzeMultiMetricTemporal(options: {
    sample_ids: string[];
    metrics?: string[];
    data_source?: "fcs" | "nta";
    alpha?: number;
  }): Promise<MultiMetricTemporalResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/analysis/temporal-analysis/multi-metric`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sample_ids: options.sample_ids,
          metrics: options.metrics || ["particle_size", "concentration", "fsc", "ssc"],
          data_source: options.data_source || "fcs",
          alpha: options.alpha || 0.05,
        }),
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Multi-metric temporal analysis failed:", error);
      this.handleNetworkError(error);
    }
  }

  // ============================================================================
  // Data Split API: Metadata and Values
  // ============================================================================

  /**
   * Get FCS file metadata only (no event data)
   */
  async getFCSMetadata(sampleId: string): Promise<{
    sample_id: string;
    file_info: {
      file_name: string;
      file_size_bytes: number;
      file_size_mb: number;
    };
    acquisition: {
      date: string;
      time: string;
      cytometer: string;
      operator: string;
      specimen: string;
    };
    data_info: {
      total_events: number;
      parameter_count: number;
      channel_count: number;
      channel_names: string[];
    };
    channels: Record<string, { stain: string; range: string; index: number }>;
    identifiers: {
      sample_id: string;
      biological_sample_id: string;
      measurement_id: string;
      is_baseline: boolean;
    };
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/samples/${sampleId}/fcs/metadata`);
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Get FCS metadata failed:", error);
      this.handleNetworkError(error);
    }
  }

  /**
   * Get FCS per-event size values calculated using Mie theory
   */
  async getFCSValues(
    sampleId: string,
    options?: {
      wavelength_nm?: number;
      n_particle?: number;
      n_medium?: number;
      max_events?: number;
      include_raw_channels?: boolean;
    }
  ): Promise<{
    sample_id: string;
    mie_parameters: {
      wavelength_nm: number;
      n_particle: number;
      n_medium: number;
    };
    data_info: {
      total_events: number;
      returned_events: number;
      valid_sizes: number;
      invalid_sizes: number;
      sampled: boolean;
      fsc_channel: string;
      ssc_channel: string | null;
    };
    statistics: {
      count: number;
      mean_nm: number;
      median_nm: number;
      std_nm: number;
      min_nm: number;
      max_nm: number;
      d10_nm: number;
      d50_nm: number;
      d90_nm: number;
    } | null;
    size_distribution: Record<string, number> | null;
    events: Array<{
      event_id: number;
      diameter_nm: number | null;
      valid: boolean;
      fsc?: number;
      ssc?: number;
    }>;
  }> {
    try {
      const params = new URLSearchParams();
      if (options?.wavelength_nm) params.append("wavelength_nm", options.wavelength_nm.toString());
      if (options?.n_particle) params.append("n_particle", options.n_particle.toString());
      if (options?.n_medium) params.append("n_medium", options.n_medium.toString());
      if (options?.max_events) params.append("max_events", options.max_events.toString());
      if (options?.include_raw_channels) params.append("include_raw_channels", "true");

      const url = `${this.baseUrl}/samples/${sampleId}/fcs/values${params.toString() ? `?${params}` : ""}`;
      const response = await fetch(url);
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Get FCS values failed:", error);
      this.handleNetworkError(error);
    }
  }

  // ===========================================================================
  // VAL-001: Cross-Validation (FCS vs NTA)
  // ===========================================================================

  /**
   * Cross-validate FCS and NTA size distributions.
   * Returns aligned histograms, D50 comparison, statistical tests, and verdict.
   */
  async crossValidate(
    fcsSampleId: string,
    ntaSampleId: string,
    options?: {
      wavelength_nm?: number;
      n_particle?: number;
      n_medium?: number;
      num_bins?: number;
      size_min?: number;
      size_max?: number;
      normalize?: boolean;
    }
  ): Promise<CrossValidationResult> {
    try {
      const params = new URLSearchParams();
      if (options?.wavelength_nm) params.set("wavelength_nm", String(options.wavelength_nm));
      if (options?.n_particle) params.set("n_particle", String(options.n_particle));
      if (options?.n_medium) params.set("n_medium", String(options.n_medium));
      if (options?.num_bins) params.set("num_bins", String(options.num_bins));
      if (options?.size_min) params.set("size_min", String(options.size_min));
      if (options?.size_max) params.set("size_max", String(options.size_max));
      if (options?.normalize !== undefined) params.set("normalize", String(options.normalize));

      const queryString = params.toString();
      const url = `${this.baseUrl}/samples/${fcsSampleId}/cross-validate/${ntaSampleId}${queryString ? `?${queryString}` : ""}`;
      
      const response = await fetch(url, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      
      this.isOffline = false;
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Cross-validation failed:", error);
      this.handleNetworkError(error);
    }
  }

  // ─── Calibration Methods ───────────────────────────────────────────

  /**
   * Get current calibration status (for sidebar badge)
   */
  async getCalibrationStatus(): Promise<CalibrationStatus> {
    try {
      const response = await fetch(`${this.baseUrl}/calibration/status`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      this.isOffline = false;
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Calibration status failed:", error);
      this.handleNetworkError(error);
    }
  }

  /**
   * List available bead standard datasheets
   */
  async getBeadStandards(): Promise<{ count: number; standards: BeadStandard[] }> {
    try {
      const response = await fetch(`${this.baseUrl}/calibration/bead-standards`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      this.isOffline = false;
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Bead standards list failed:", error);
      this.handleNetworkError(error);
    }
  }

  /**
   * Get active calibration details including fitted curve
   */
  async getActiveCalibration(): Promise<ActiveCalibration> {
    try {
      const response = await fetch(`${this.baseUrl}/calibration/active`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      this.isOffline = false;
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Active calibration fetch failed:", error);
      this.handleNetworkError(error);
    }
  }

  /**
   * Auto-fit calibration from a bead FCS file + datasheet
   */
  async fitCalibration(
    beadSampleId: string,
    beadStandardFile: string,
    sscChannel?: string
  ): Promise<CalibrationFitResult> {
    try {
      const params = new URLSearchParams();
      params.append("bead_sample_id", beadSampleId);
      params.append("bead_standard_file", beadStandardFile);
      if (sscChannel) params.append("ssc_channel", sscChannel);

      const response = await fetch(`${this.baseUrl}/calibration/fit`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: params.toString(),
      });
      this.isOffline = false;
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Calibration fit failed:", error);
      this.handleNetworkError(error);
    }
  }

  /**
   * Fit calibration from manually entered bead scatter means
   */
  async fitCalibrationManual(
    points: { diameter_nm: number; mean_ssc: number }[],
    kitName?: string,
    riParticle?: number
  ): Promise<CalibrationFitResult> {
    try {
      const body: Record<string, unknown> = { points };
      if (kitName) body.kit_name = kitName;
      if (riParticle !== undefined) body.ri_particle = riParticle;

      const response = await fetch(`${this.baseUrl}/calibration/fit-manual`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      this.isOffline = false;
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Manual calibration fit failed:", error);
      this.handleNetworkError(error);
    }
  }

  /**
   * Remove (archive) the active calibration
   */
  async removeCalibration(): Promise<{ success: boolean; message: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/calibration/active`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
      });
      this.isOffline = false;
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Remove calibration failed:", error);
      this.handleNetworkError(error);
    }
  }

  /**
   * Get NTA file metadata only (no measurement data)
   */
  async getNTAMetadata(sampleId: string): Promise<{
    sample_id: string;
    file_info: {
      file_name: string;
      file_size_bytes: number;
      measurement_type: string;
    };
    sample_info: {
      sample_name: string;
      operator: string;
      experiment: string;
      electrolyte: string;
    };
    instrument: {
      instrument_serial: string;
      cell_serial: string;
      software_version: string;
      sop: string;
    };
    acquisition: {
      date: string;
      time: string;
      temperature: number | null;
      viscosity: number | null;
      ph: number | null;
      conductivity: number | null;
    };
    measurement_params: {
      num_positions: number | null;
      num_traces: number | null;
      sensitivity: number | null;
      shutter: number | null;
      laser_wavelength: number | null;
      dilution: number;
      conc_correction: number;
    };
    quality: {
      cell_check_result: string;
      detected_particles: number | null;
      scattering_intensity: number | null;
    };
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/samples/${sampleId}/nta/metadata`);
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Get NTA metadata failed:", error);
      this.handleNetworkError(error);
    }
  }

  /**
   * Get NTA size and concentration values
   */
  async getNTAValues(sampleId: string): Promise<{
    sample_id: string;
    measurement_type: string;
    data_info: {
      total_bins: number;
      size_column: string;
      concentration_column: string | null;
    };
    size_statistics: {
      count: number;
      mean_nm: number;
      weighted_mean_nm: number;
      median_nm: number;
      std_nm: number;
      min_nm: number;
      max_nm: number;
      mode_nm: number;
    };
    concentration_statistics: {
      total_particles_ml: number;
      max_concentration: number;
      peak_size_nm: number;
    } | null;
    values: Array<{
      bin_id: number;
      size_nm: number;
      concentration_particles_ml?: number;
    }>;
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/samples/${sampleId}/nta/values`);
      return this.handleResponse(response);
    } catch (error) {
      console.error("[API] Get NTA values failed:", error);
      this.handleNetworkError(error);
    }
  }
}

// ============================================================================
// Population Shift Types (CRMIT-004)
// ============================================================================

export interface ShiftTestResult {
  test_name: string;
  statistic: number;
  p_value: number;
  significant: boolean;
  effect_size?: number;
  severity: "none" | "minor" | "moderate" | "major" | "critical";
  interpretation: string;
}

export interface PopulationMetrics {
  sample_id: string;
  sample_name: string;
  n_events: number;
  mean: number;
  median: number;
  std: number;
  iqr: number;
  skewness: number;
  kurtosis: number;
  percentiles: Record<number, number>;
}

export interface PopulationShiftResponse {
  success: boolean;
  sample_a: PopulationMetrics;
  sample_b: PopulationMetrics;
  metric_name: string;
  tests: ShiftTestResult[];
  overall_shift_detected: boolean;
  overall_severity: "none" | "minor" | "moderate" | "major" | "critical";
  summary: string;
  recommendations: string[];
}

export interface MultiSampleShiftResponse {
  success: boolean;
  mode: "pairwise" | "baseline" | "temporal" | "all_pairs";
  baseline_sample?: string;
  comparisons: PopulationShiftResponse[];
  global_summary: string;
  any_significant_shift: boolean;
  max_severity: "none" | "minor" | "moderate" | "major" | "critical";
}

// ============================================================================
// CRMIT-007: Temporal Analysis Types
// ============================================================================

export interface TrendResult {
  type: "none" | "linear_increasing" | "linear_decreasing" | "exponential_growth" | "exponential_decay" | "cyclical" | "random_walk";
  slope: number;
  r_squared: number;
  p_value: number;
  is_significant: boolean;
  interpretation: string;
}

export interface StabilityResult {
  level: "excellent" | "good" | "acceptable" | "poor" | "unstable";
  mean: number;
  std: number;
  cv: number;
  min_value: number;
  max_value: number;
  interpretation: string;
}

export interface DriftResult {
  severity: "none" | "minor" | "moderate" | "significant" | "critical";
  magnitude: number;
  direction: "increasing" | "decreasing" | "stable";
  p_value: number;
  is_significant: boolean;
  change_points: number[];
  interpretation: string;
}

export interface TemporalCorrelation {
  metric_a: string;
  metric_b: string;
  pearson_r: number;
  spearman_rho: number;
  strength: "none" | "weak" | "moderate" | "strong" | "very_strong";
  is_significant: boolean;
  interpretation: string;
}

export interface TemporalAnalysisResponse {
  success: boolean;
  metric: string;
  n_points: number;
  time_range: {
    start: string;
    end: string;
  };
  trend: TrendResult;
  stability: StabilityResult;
  drift: DriftResult;
  correlations: TemporalCorrelation[];
  moving_average: number[];
  smoothed_values: number[];
  summary: string;
  recommendations: string[];
}

export interface MultiMetricTemporalResponse {
  success: boolean;
  sample_ids: string[];
  n_samples: number;
  time_range: {
    start: string | null;
    end: string | null;
  };
  metrics_analyzed: string[];
  individual_results: Record<string, any>;
  overall_stability: {
    level: string;
    average_cv: number;
    min_cv?: number;
    max_cv?: number;
  };
  overall_drift: {
    max_severity: string;
    metrics_with_drift: Array<{
      metric: string;
      severity: string;
      magnitude: number;
      direction: string;
    }>;
    total_drifting_metrics: number;
  };
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export types
export type { ApiClient };
