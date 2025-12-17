/**
 * API Client for BioVaram EV Analysis Platform
 * Connects to FastAPI backend at localhost:8000
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
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
  id: number;
  total_events: number;
  fsc_mean?: number;
  fsc_median?: number;
  ssc_mean?: number;
  ssc_median?: number;
  particle_size_median_nm?: number;
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
 * TASK-009: Experimental Conditions interface
 * Stores metadata about experiment setup for reproducibility and AI analysis
 */
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

  constructor() {
    this.baseUrl = `${API_BASE_URL}${API_PREFIX}`;
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
  }): Promise<{ samples: Sample[]; total: number; skip: number; limit: number }> {
    try {
      const searchParams = new URLSearchParams();
      if (params?.skip) searchParams.append("skip", params.skip.toString());
      if (params?.limit) searchParams.append("limit", params.limit.toString());
      if (params?.treatment) searchParams.append("treatment", params.treatment);
      if (params?.qc_status) searchParams.append("qc_status", params.qc_status);
      if (params?.processing_status)
        searchParams.append("processing_status", params.processing_status);

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

  async getSizeBins(sampleId: string): Promise<{
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
      const response = await fetch(`${this.baseUrl}/samples/${sampleId}/size-bins`, {
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
   * Re-analyze a sample with custom settings
   */
  async reanalyzeSample(
    sampleId: string,
    settings: {
      wavelength_nm?: number;
      n_particle?: number;
      n_medium?: number;
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
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export types
export type { ApiClient };
