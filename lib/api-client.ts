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
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export types
export type { ApiClient };
