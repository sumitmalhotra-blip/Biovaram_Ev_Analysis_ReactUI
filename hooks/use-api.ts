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
  }
}
