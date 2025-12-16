"use client"

import { useCallback, useEffect, useRef } from "react"
import { apiClient, NetworkError, type Sample, type FCSResult, type NTAResult } from "@/lib/api-client"
import { useAnalysisStore } from "@/lib/store"
import { useToast } from "@/hooks/use-toast"
import { 
  retryWithBackoff, 
  getUserFriendlyErrorMessage,
  isNetworkError,
  isTimeoutError,
  categorizeError,
} from "@/lib/error-utils"

const HEALTH_CHECK_INTERVAL = 30000 // 30 seconds

export function useApi() {
  const { toast } = useToast()
  const healthCheckRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const {
    setApiConnected,
    setApiChecking,
    setLastHealthCheck,
    setApiSamples,
    setSamplesLoading,
    setSamplesError,
    addApiSample,
    removeApiSample,
    setFCSFile,
    setFCSSampleId,
    setFCSResults,
    setFCSAnalyzing,
    setFCSError,
    setNTAFile,
    setNTASampleId,
    setNTAResults,
    setNTAAnalyzing,
    setNTAError,
    addProcessingJob,
    updateProcessingJob,
    apiConnected,
  } = useAnalysisStore()

  // =========================================================================
  // Health Check
  // =========================================================================

  const checkHealth = useCallback(async () => {
    setApiChecking(true)
    try {
      await retryWithBackoff(() => apiClient.checkHealth(), {
        maxAttempts: 2,
        initialDelay: 500,
        shouldRetry: () => false, // Don't retry health checks
      })
      setApiConnected(true)
      setLastHealthCheck(new Date())
      return true
    } catch {
      // Silently handle - backend is offline
      setApiConnected(false)
      return false
    } finally {
      setApiChecking(false)
    }
  }, [setApiChecking, setApiConnected, setLastHealthCheck])

  // Start periodic health checks
  const startHealthCheck = useCallback(() => {
    // Initial check
    checkHealth()

    // Periodic checks
    healthCheckRef.current = setInterval(() => {
      checkHealth()
    }, HEALTH_CHECK_INTERVAL)

    return () => {
      if (healthCheckRef.current) {
        clearInterval(healthCheckRef.current)
      }
    }
  }, [checkHealth])

  // =========================================================================
  // Samples
  // =========================================================================

  const fetchSamples = useCallback(
    async (params?: { treatment?: string; qc_status?: string; processing_status?: string }) => {
      // Don't fetch if we know the API is offline
      if (apiClient.offline) {
        return []
      }

      setSamplesLoading(true)
      setSamplesError(null)

      try {
        const response = await retryWithBackoff(
          () => apiClient.listSamples(params),
          {
            maxAttempts: 3,
            onRetry: (error, attempt) => {
              console.log(`Retrying sample fetch (attempt ${attempt}):`, error)
            },
          }
        )
        setApiSamples(response.samples)
        return response.samples
      } catch (error) {
        const category = categorizeError(error)
        const message = getUserFriendlyErrorMessage(error)
        
        // Only show toast for non-network errors (don't spam when backend is offline)
        if (category !== "network") {
          setSamplesError(message)
          toast({
            variant: "destructive",
            title: "Failed to fetch samples",
            description: message,
          })
        } else {
          setSamplesError("Backend offline")
        }
        return []
      } finally {
        setSamplesLoading(false)
      }
    },
    [setApiSamples, setSamplesError, setSamplesLoading, toast]
  )

  const getSample = useCallback(
    async (sampleId: string): Promise<Sample | null> => {
      if (apiClient.offline) return null
      
      try {
        return await retryWithBackoff(() => apiClient.getSample(sampleId), {
          maxAttempts: 2,
        })
      } catch (error) {
        const category = categorizeError(error)
        if (category !== "network") {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Failed to fetch sample",
            description: message,
          })
        }
        return null
      }
    },
    [toast]
  )

  const deleteSample = useCallback(
    async (sampleId: string) => {
      try {
        const result = await retryWithBackoff(() => apiClient.deleteSample(sampleId), {
          maxAttempts: 2,
          shouldRetry: (error) => {
            // Only retry on server errors, not client errors (404, 400, etc.)
            return categorizeError(error) === "server"
          },
        })
        if (result.success) {
          removeApiSample(sampleId)
          toast({
            title: "Sample deleted",
            description: result.message,
          })
        }
        return result
      } catch (error) {
        const message = getUserFriendlyErrorMessage(error)
        toast({
          variant: "destructive",
          title: "Failed to delete sample",
          description: message,
        })
        return null
      }
    },
    [removeApiSample, toast]
  )

  // =========================================================================
  // FCS Upload & Analysis
  // =========================================================================

  const uploadFCS = useCallback(
    async (
      file: File,
      metadata?: {
        treatment?: string
        concentration_ug?: number
        preparation_method?: string
        operator?: string
        notes?: string
      }
    ) => {
      // Check if API is offline before attempting upload
      if (apiClient.offline) {
        toast({
          variant: "destructive",
          title: "Backend offline",
          description: "Cannot upload file - backend server is not running",
        })
        return null
      }

      setFCSFile(file)
      setFCSAnalyzing(true)
      setFCSError(null)

      try {
        const response = await retryWithBackoff(
          () => apiClient.uploadFCS(file, metadata),
          {
            maxAttempts: 2,
            initialDelay: 2000,
            shouldRetry: (error) => {
              // Don't retry on client errors (validation, file format issues)
              const category = categorizeError(error)
              return category === "server" || category === "timeout"
            },
            onRetry: (error, attempt) => {
              toast({
                title: "Upload failed, retrying...",
                description: `Attempt ${attempt} of 2`,
              })
            },
          }
        )

        if (response.success) {
          setFCSSampleId(response.sample_id)

          console.log("[uploadFCS] Upload response:", response)
          console.log("[uploadFCS] FCS results:", response.fcs_results)

          if (response.fcs_results) {
            setFCSResults(response.fcs_results)
          }

          // Add to processing jobs
          addProcessingJob({
            id: response.job_id,
            job_type: "fcs_parse",
            status: response.processing_status,
            sample_id: response.id,
          })

          // Refresh samples list
          fetchSamples()

          toast({
            title: "✅ FCS file uploaded",
            description: `${file.name} uploaded successfully. Sample ID: ${response.sample_id}`,
          })

          return response
        }
      } catch (error) {
        const category = categorizeError(error)
        const message = getUserFriendlyErrorMessage(error)
        setFCSError(message)
        toast({
          variant: "destructive",
          title: "Upload failed",
          description: message,
        })
        return null
      } finally {
        setFCSAnalyzing(false)
      }
    },
    [
      setFCSFile,
      setFCSAnalyzing,
      setFCSError,
      setFCSSampleId,
      setFCSResults,
      addProcessingJob,
      fetchSamples,
      toast,
    ]
  )

  const getFCSResults = useCallback(
    async (sampleId: string): Promise<FCSResult[] | null> => {
      if (apiClient.offline) return null
      
      try {
        const response = await apiClient.getFCSResults(sampleId)
        return response.results
      } catch (error) {
        if (!isNetworkError(error)) {
          const message = error instanceof Error ? error.message : "Failed to fetch FCS results"
          toast({
            variant: "destructive",
            title: "Failed to fetch FCS results",
            description: message,
          })
        }
        return null
      }
    },
    [toast]
  )

  // =========================================================================
  // NTA Upload & Analysis
  // =========================================================================

  const uploadNTA = useCallback(
    async (
      file: File,
      metadata?: {
        treatment?: string
        temperature_celsius?: number
        operator?: string
        notes?: string
      }
    ) => {
      // Check if API is offline before attempting upload
      if (apiClient.offline) {
        toast({
          variant: "destructive",
          title: "Backend offline",
          description: "Cannot upload file - backend server is not running",
        })
        return null
      }

      setNTAFile(file)
      setNTAAnalyzing(true)
      setNTAError(null)

      try {
        const response = await retryWithBackoff(
          () => apiClient.uploadNTA(file, metadata),
          {
            maxAttempts: 2,
            initialDelay: 2000,
            shouldRetry: (error) => {
              const category = categorizeError(error)
              return category === "server" || category === "timeout"
            },
            onRetry: (error, attempt) => {
              toast({
                title: "Upload failed, retrying...",
                description: `Attempt ${attempt} of 2`,
              })
            },
          }
        )

        if (response.success) {
          setNTASampleId(response.sample_id)

          if (response.nta_results) {
            setNTAResults(response.nta_results)
          }

          // Add to processing jobs
          addProcessingJob({
            id: response.job_id,
            job_type: "nta_parse",
            status: response.processing_status,
            sample_id: response.id,
          })

          // Refresh samples list
          fetchSamples()

          toast({
            title: "✅ NTA file uploaded",
            description: `${file.name} uploaded successfully. Sample ID: ${response.sample_id}`,
          })

          return response
        }
      } catch (error) {
        const message = getUserFriendlyErrorMessage(error)
        setNTAError(message)
        toast({
          variant: "destructive",
          title: "Upload failed",
          description: message,
        })
        return null
      } finally {
        setNTAAnalyzing(false)
      }
    },
    [
      setNTAFile,
      setNTAAnalyzing,
      setNTAError,
      setNTASampleId,
      setNTAResults,
      addProcessingJob,
      fetchSamples,
      toast,
    ]
  )

  const getNTAResults = useCallback(
    async (sampleId: string): Promise<NTAResult[] | null> => {
      if (apiClient.offline) return null
      
      try {
        const response = await apiClient.getNTAResults(sampleId)
        return response.results
      } catch (error) {
        if (!isNetworkError(error)) {
          const message = error instanceof Error ? error.message : "Failed to fetch NTA results"
          toast({
            variant: "destructive",
            title: "Failed to fetch NTA results",
            description: message,
          })
        }
        return null
      }
    },
    [toast]
  )

  // =========================================================================
  // Batch Upload
  // =========================================================================

  const uploadBatch = useCallback(
    async (files: File[]) => {
      try {
        const response = await apiClient.uploadBatch(files)

        if (response.success) {
          // Add all jobs
          response.job_ids.forEach((jobId, index) => {
            addProcessingJob({
              id: jobId,
              job_type: "batch_upload",
              status: "pending",
            })
          })

          // Refresh samples
          fetchSamples()

          toast({
            title: "Batch upload complete",
            description: `Uploaded ${response.uploaded} files, ${response.failed} failed`,
          })
        }

        return response
      } catch (error) {
        const message = error instanceof Error ? error.message : "Batch upload failed"
        toast({
          variant: "destructive",
          title: "Batch upload failed",
          description: message,
        })
        return null
      }
    },
    [addProcessingJob, fetchSamples, toast]
  )

  // =========================================================================
  // Processing Jobs
  // =========================================================================

  const checkJobStatus = useCallback(
    async (jobId: string) => {
      try {
        const job = await apiClient.getJob(jobId)
        updateProcessingJob(jobId, job)
        return job
      } catch (error) {
        console.error("[API] Failed to check job status:", error)
        return null
      }
    },
    [updateProcessingJob]
  )

  const cancelJob = useCallback(
    async (jobId: string) => {
      try {
        const result = await apiClient.cancelJob(jobId)
        if (result.success) {
          updateProcessingJob(jobId, { status: "cancelled" })
          toast({
            title: "Job cancelled",
            description: result.message,
          })
        }
        return result
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to cancel job"
        toast({
          variant: "destructive",
          title: "Failed to cancel job",
          description: message,
        })
        return null
      }
    },
    [updateProcessingJob, toast]
  )

  const retryJob = useCallback(
    async (jobId: string) => {
      try {
        const result = await apiClient.retryJob(jobId)
        if (result.success) {
          addProcessingJob({
            id: result.new_job_id,
            job_type: "retry",
            status: "pending",
          })
          toast({
            title: "Job retry started",
            description: `New job ID: ${result.new_job_id}`,
          })
        }
        return result
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to retry job"
        toast({
          variant: "destructive",
          title: "Failed to retry job",
          description: message,
        })
        return null
      }
    },
    [addProcessingJob, toast]
  )

  return {
    // Health
    checkHealth,
    startHealthCheck,
    apiConnected,

    // Samples
    fetchSamples,
    getSample,
    deleteSample,

    // FCS
    uploadFCS,
    getFCSResults,

    // NTA
    uploadNTA,
    getNTAResults,

    // Batch
    uploadBatch,

    // Jobs
    checkJobStatus,
    cancelJob,
    retryJob,

    // Scatter Data & Size Binning
    getScatterData: useCallback(
      async (sampleId: string, maxPoints: number = 5000) => {
        if (apiClient.offline) return null
        try {
          return await retryWithBackoff(() => apiClient.getScatterData(sampleId, maxPoints), {
            maxAttempts: 2,
          })
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Failed to fetch scatter data",
            description: message,
          })
          return null
        }
      },
      [toast]
    ),

    getSizeBins: useCallback(
      async (sampleId: string) => {
        if (apiClient.offline) return null
        try {
          return await retryWithBackoff(() => apiClient.getSizeBins(sampleId), {
            maxAttempts: 2,
          })
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Failed to fetch size bins",
            description: message,
          })
          return null
        }
      },
      [toast]
    ),

    // Re-analyze with new settings
    reanalyzeWithSettings: useCallback(
      async (
        sampleId: string,
        settings: {
          anomaly_detection?: boolean
          anomaly_method?: string
          zscore_threshold?: number
          iqr_factor?: number
          wavelength_nm?: number
          n_particle?: number
          n_medium?: number
          size_ranges?: Array<{ name: string; min: number; max: number }>
        }
      ) => {
        if (apiClient.offline) {
          toast({
            variant: "destructive",
            title: "Backend offline",
            description: "Cannot re-analyze - backend server is not running",
          })
          return null
        }

        setFCSAnalyzing(true)
        setFCSError(null)

        try {
          // Call the re-analyze endpoint using the API client
          const response = await apiClient.reanalyzeSample(sampleId, {
            wavelength_nm: settings.wavelength_nm,
            n_particle: settings.n_particle,
            n_medium: settings.n_medium,
            anomaly_detection: settings.anomaly_detection,
            anomaly_method: settings.anomaly_method,
            zscore_threshold: settings.zscore_threshold,
            iqr_factor: settings.iqr_factor,
            size_ranges: settings.size_ranges,
          })

          if (response?.results) {
            // Get existing results ID or use a default
            const existingResults = useAnalysisStore.getState().fcsAnalysis.results
            
            // Update the store with new results
            const updatedResults = {
              id: existingResults?.id || 0,
              total_events: response.results.total_events,
              event_count: response.results.total_events,
              channels: response.results.channels,
              fsc_mean: response.results.fsc_mean ?? undefined,
              fsc_median: response.results.fsc_median ?? undefined,
              ssc_mean: response.results.ssc_mean ?? undefined,
              ssc_median: response.results.ssc_median ?? undefined,
              particle_size_median_nm: response.results.particle_size_median_nm ?? undefined,
              size_statistics: response.results.size_statistics ?? undefined,
              processed_at: new Date().toISOString(),
            }
            setFCSResults(updatedResults)
            
            // Update anomaly data if present
            if (response.anomaly_data && response.anomaly_data.enabled) {
              // Map the method string to the expected type
              const methodMap: Record<string, "Z-Score" | "IQR" | "Both"> = {
                zscore: "Z-Score",
                iqr: "IQR",
                both: "Both",
              }
              
              useAnalysisStore.getState().setFCSAnomalyData({
                method: methodMap[response.anomaly_data.method.toLowerCase()] || "Z-Score",
                total_anomalies: response.anomaly_data.total_anomalies,
                anomaly_percentage: response.anomaly_data.anomaly_percentage,
                anomalous_indices: response.anomaly_data.anomalous_indices,
              })
            }
          }

          toast({
            title: "✅ Re-analysis complete",
            description: `Updated analysis with ${settings.wavelength_nm || 488}nm wavelength, RI=${settings.n_particle || 1.40}`,
          })

          return response
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          setFCSError(message)
          toast({
            variant: "destructive",
            title: "Re-analysis failed",
            description: message,
          })
          return null
        } finally {
          setFCSAnalyzing(false)
        }
      },
      [setFCSAnalyzing, setFCSError, setFCSResults, toast]
    ),

    // =========================================================================
    // Statistical Analysis
    // =========================================================================

    runStatisticalTests: useCallback(
      async (
        groupA: string[],
        groupB: string[],
        options?: {
          metrics?: string[];
          testTypes?: string[];
          alpha?: number;
        }
      ) => {
        if (apiClient.offline) {
          toast({
            variant: "destructive",
            title: "Backend offline",
            description: "Cannot run statistical tests - backend server is not running",
          })
          return null
        }

        try {
          const response = await apiClient.runStatisticalTests(groupA, groupB, options)
          
          toast({
            title: "✅ Statistical tests complete",
            description: `${response.summary.significant_tests}/${response.summary.total_tests} tests showed significant differences`,
          })
          
          return response
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Statistical tests failed",
            description: message,
          })
          return null
        }
      },
      [toast]
    ),

    compareDistributions: useCallback(
      async (sampleIdA: string, sampleIdB: string, channel: string = "FSC") => {
        if (apiClient.offline) {
          toast({
            variant: "destructive",
            title: "Backend offline",
            description: "Cannot compare distributions - backend server is not running",
          })
          return null
        }

        try {
          const response = await apiClient.compareDistributions(sampleIdA, sampleIdB, channel)
          return response
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Distribution comparison failed",
            description: message,
          })
          return null
        }
      },
      [toast]
    ),
  }
}
