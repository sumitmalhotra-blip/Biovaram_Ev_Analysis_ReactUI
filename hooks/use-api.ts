"use client"

import { useCallback, useEffect, useRef } from "react"
import { useSession } from "next-auth/react"
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
  const { data: session } = useSession()
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
    setSecondaryFCSFile,
    setSecondaryFCSSampleId,
    setSecondaryFCSResults,
    setSecondaryFCSAnalyzing,
    setSecondaryFCSError,
    setOverlayConfig,
    setNTAFile,
    setNTASampleId,
    setNTAResults,
    setNTAAnalyzing,
    setNTAError,
    addProcessingJob,
    updateProcessingJob,
    apiConnected,
    setActiveTab,
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

  // Get user ID from session for filtering samples by owner
  const userId = session?.user?.id ? Number(session.user.id) : undefined

  const fetchSamples = useCallback(
    async (params?: { treatment?: string; qc_status?: string; processing_status?: string }) => {
      // Don't fetch if we know the API is offline
      if (apiClient.offline) {
        return []
      }

      setSamplesLoading(true)
      setSamplesError(null)

      try {
        // Include user_id to only fetch samples owned by the current user
        const response = await retryWithBackoff(
          () => apiClient.listSamples({ ...params, user_id: userId }),
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
    [setApiSamples, setSamplesError, setSamplesLoading, toast, userId]
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

  /**
   * Open a sample in its respective analysis tab with loaded results
   * T-003: Previous Analysis Review - Load saved analysis data when clicking a sample
   * 
   * Flow:
   * 1. Get sample details to verify file exists
   * 2. Load saved analysis results from database
   * 3. If results exist, populate the analysis state
   * 4. If no results but file exists, set sampleId so scatter data loads from file
   * 5. Navigate to the appropriate tab
   */
  const openSampleInTab = useCallback(
    async (sampleId: string, type: "fcs" | "nta"): Promise<boolean> => {
      if (apiClient.offline) {
        toast({
          variant: "destructive",
          title: "Backend offline",
          description: "Cannot load sample - backend server is not running",
        })
        return false
      }

      try {
        // First, get sample details to verify the file exists
        const sample = await apiClient.getSample(sampleId)
        
        if (!sample) {
          toast({
            variant: "destructive",
            title: "Sample not found",
            description: `Could not find sample: ${sampleId}`,
          })
          return false
        }

        if (type === "fcs") {
          // Check if FCS file exists
          if (!sample.files?.fcs) {
            toast({
              variant: "destructive",
              title: "No FCS file",
              description: `Sample ${sampleId} does not have an FCS file`,
            })
            return false
          }

          // Try to load saved FCS results
          const response = await apiClient.getFCSResults(sampleId)
          
          if (response && response.results.length > 0) {
            // Set the most recent result
            const latestResult = response.results[0]
            setFCSSampleId(sampleId)
            setFCSResults(latestResult)
            setActiveTab("flow-cytometry")
            toast({
              title: "Analysis loaded",
              description: `FCS analysis for ${sampleId} loaded successfully`,
            })
            return true
          } else {
            // No saved results, but file exists - set sampleId so scatter data can load
            setFCSSampleId(sampleId)
            // Create a minimal result object to trigger scatter data loading
            setFCSResults({
              id: 0,
              total_events: 0,
              sample_id: sampleId,
            })
            setActiveTab("flow-cytometry")
            toast({
              title: "Sample loaded",
              description: `Loading FCS data from file for ${sampleId}...`,
            })
            return true
          }
        } else if (type === "nta") {
          // Check if NTA file exists
          if (!sample.files?.nta) {
            toast({
              variant: "destructive",
              title: "No NTA file",
              description: `Sample ${sampleId} does not have an NTA file`,
            })
            return false
          }

          // Try to load saved NTA results
          const response = await apiClient.getNTAResults(sampleId)
          
          if (response && response.results.length > 0) {
            // Set the most recent result
            const latestResult = response.results[0]
            setNTASampleId(sampleId)
            setNTAResults(latestResult)
            setActiveTab("nta")
            toast({
              title: "Analysis loaded",
              description: `NTA analysis for ${sampleId} loaded successfully`,
            })
            return true
          } else {
            // No saved results, but file exists - set sampleId so data can load
            setNTASampleId(sampleId)
            setNTAResults({
              id: 0,
            })
            setActiveTab("nta")
            toast({
              title: "Sample loaded",
              description: `Loading NTA data from file for ${sampleId}...`,
            })
            return true
          }
        }
        return false
      } catch (error) {
        const message = getUserFriendlyErrorMessage(error)
        toast({
          variant: "destructive",
          title: "Failed to load sample",
          description: message,
        })
        return false
      }
    },
    [toast, setFCSSampleId, setFCSResults, setNTASampleId, setNTAResults, setActiveTab]
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
        // Include user_id in metadata for ownership
        const uploadMetadata = { ...metadata, user_id: userId }
        
        const response = await retryWithBackoff(
          () => apiClient.uploadFCS(file, uploadMetadata),
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
      userId,
    ]
  )

  // Upload secondary FCS file for comparison/overlay
  const uploadSecondaryFCS = useCallback(
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
      if (apiClient.offline) {
        toast({
          variant: "destructive",
          title: "Backend offline",
          description: "Cannot upload file - backend server is not running",
        })
        return null
      }

      setSecondaryFCSFile(file)
      setSecondaryFCSAnalyzing(true)
      setSecondaryFCSError(null)

      try {
        // Include user_id in metadata for ownership
        const uploadMetadata = { ...metadata, user_id: userId }
        
        const response = await retryWithBackoff(
          () => apiClient.uploadFCS(file, uploadMetadata),
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
          setSecondaryFCSSampleId(response.sample_id)

          if (response.fcs_results) {
            setSecondaryFCSResults(response.fcs_results)
          }

          // Add to processing jobs
          addProcessingJob({
            id: response.job_id + "_secondary",
            job_type: "fcs_parse",
            status: response.processing_status,
            sample_id: response.id,
          })

          // Refresh samples list
          fetchSamples()

          // Auto-enable overlay mode when secondary file is uploaded
          setOverlayConfig({ enabled: true })

          toast({
            title: "✅ Comparison file uploaded",
            description: `${file.name} uploaded for comparison. Sample ID: ${response.sample_id}`,
          })

          return response
        }
      } catch (error) {
        const message = getUserFriendlyErrorMessage(error)
        setSecondaryFCSError(message)
        toast({
          variant: "destructive",
          title: "Upload failed",
          description: message,
        })
        return null
      } finally {
        setSecondaryFCSAnalyzing(false)
      }
    },
    [
      setSecondaryFCSFile,
      setSecondaryFCSAnalyzing,
      setSecondaryFCSError,
      setSecondaryFCSSampleId,
      setSecondaryFCSResults,
      setOverlayConfig,
      addProcessingJob,
      fetchSamples,
      toast,
      userId,
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
        // Include user_id in metadata for ownership
        const uploadMetadata = { ...metadata, user_id: userId }
        
        const response = await retryWithBackoff(
          () => apiClient.uploadNTA(file, uploadMetadata),
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
      userId,
    ]
  )

  // =========================================================================
  // NTA PDF Upload (TASK-007)
  // Surya (Dec 3): "That number is not ever mentioned in a text format... 
  // it is always mentioned only in the PDF file"
  // =========================================================================

  const uploadNtaPdf = useCallback(
    async (file: File, linkedSampleId?: string) => {
      // Check if API is offline before attempting upload
      if (apiClient.offline) {
        toast({
          variant: "destructive",
          title: "Backend offline",
          description: "Cannot upload PDF - backend server is not running",
        })
        return null
      }

      try {
        const response = await apiClient.uploadNtaPdf(file, linkedSampleId)

        if (response.success) {
          const pdfData = response.pdf_data
          
          if (pdfData.extraction_successful) {
            toast({
              title: "✅ PDF parsed successfully",
              description: pdfData.original_concentration 
                ? `Original concentration: ${pdfData.original_concentration.toExponential(2)} particles/mL`
                : "Extracted size statistics from PDF",
            })
          } else {
            toast({
              variant: "default",
              title: "⚠️ PDF parsed with warnings",
              description: `Some data could not be extracted: ${pdfData.extraction_errors?.join(", ")}`,
            })
          }

          return response
        }
      } catch (error) {
        const message = getUserFriendlyErrorMessage(error)
        toast({
          variant: "destructive",
          title: "PDF upload failed",
          description: message,
        })
        return null
      }
    },
    [toast]
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
    openSampleInTab,

    // FCS
    uploadFCS,
    uploadSecondaryFCS,  // T-002: Secondary file upload for comparison/overlay
    getFCSResults,

    // NTA
    uploadNTA,
    uploadNtaPdf,  // TASK-007: PDF parsing for concentration/dilution
    getNTAResults,

    // Experimental Conditions (TASK-009)
    // Parvesh (Dec 5): "We'd also want a way to be able to log conditions for the experiment"
    saveExperimentalConditions: useCallback(
      async (
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
      ) => {
        if (apiClient.offline) {
          toast({
            variant: "destructive",
            title: "Backend offline",
            description: "Cannot save conditions - backend server is not running",
          })
          return null
        }

        try {
          const response = await apiClient.saveExperimentalConditions(sampleId, conditions)
          
          if (response.success) {
            toast({
              title: "✅ Conditions saved",
              description: `Experimental conditions logged for ${sampleId}`,
            })
          }
          
          return response
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Failed to save conditions",
            description: message,
          })
          return null
        }
      },
      [toast]
    ),

    getExperimentalConditions: useCallback(
      async (sampleId: string) => {
        if (apiClient.offline) return null
        
        try {
          return await apiClient.getExperimentalConditions(sampleId)
        } catch (error) {
          if (!isNetworkError(error)) {
            const message = getUserFriendlyErrorMessage(error)
            toast({
              variant: "destructive",
              title: "Failed to fetch conditions",
              description: message,
            })
          }
          return null
        }
      },
      [toast]
    ),

    updateExperimentalConditions: useCallback(
      async (
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
      ) => {
        if (apiClient.offline) {
          toast({
            variant: "destructive",
            title: "Backend offline",
            description: "Cannot update conditions - backend server is not running",
          })
          return null
        }

        try {
          const response = await apiClient.updateExperimentalConditions(sampleId, conditions)
          
          if (response.success) {
            toast({
              title: "✅ Conditions updated",
              description: `Experimental conditions updated for ${sampleId}`,
            })
          }
          
          return response
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Failed to update conditions",
            description: message,
          })
          return null
        }
      },
      [toast]
    ),

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

    // Auto Axis Selection (CRMIT-002)
    getRecommendedAxes: useCallback(
      async (
        sampleId: string,
        options?: {
          nRecommendations?: number
          includeScatter?: boolean
          includeFluorescence?: boolean
        }
      ) => {
        if (apiClient.offline) return null
        try {
          return await retryWithBackoff(
            () => apiClient.getRecommendedAxes(sampleId, options),
            { maxAttempts: 2 }
          )
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Failed to get axis recommendations",
            description: message,
          })
          return null
        }
      },
      [toast]
    ),

    getScatterDataWithAxes: useCallback(
      async (
        sampleId: string,
        xChannel: string,
        yChannel: string,
        maxPoints: number = 5000
      ) => {
        if (apiClient.offline) return null
        try {
          return await retryWithBackoff(
            () => apiClient.getScatterDataWithAxes(sampleId, xChannel, yChannel, maxPoints),
            { maxAttempts: 2 }
          )
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

    /**
     * Analyze gated (selected) population from scatter plot
     * T-009: Population Gating & Selection Analysis
     */
    analyzeGatedPopulation: useCallback(
      async (
        sampleId: string,
        gateConfig: {
          gate_name: string;
          gate_type: "rectangle" | "polygon" | "ellipse";
          gate_coordinates: {
            x1?: number;
            y1?: number;
            x2?: number;
            y2?: number;
            points?: Array<{ x: number; y: number }>;
            cx?: number;
            cy?: number;
            rx?: number;
            ry?: number;
            rotation?: number;
          };
          x_channel: string;
          y_channel: string;
          include_diameter_stats?: boolean;
        }
      ) => {
        if (apiClient.offline) {
          toast({
            variant: "destructive",
            title: "Backend offline",
            description: "Cannot run gated analysis - backend server is not running",
          })
          return null
        }

        try {
          const result = await retryWithBackoff(
            () => apiClient.analyzeGatedPopulation(sampleId, gateConfig),
            { maxAttempts: 2 }
          )
          
          if (result.gated_events === 0) {
            toast({
              variant: "default",
              title: "No events in gate",
              description: "The selected region contains no events",
            })
          } else {
            toast({
              title: `✅ Gate Analysis Complete`,
              description: `${result.gated_events.toLocaleString()} events (${result.gated_percentage.toFixed(1)}%) in "${gateConfig.gate_name}"`,
            })
          }
          
          return result
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Gated analysis failed",
            description: message,
          })
          return null
        }
      },
      [toast]
    ),

    // Anomaly Detection for any sample (including secondary)
    detectAnomalies: useCallback(
      async (
        sampleId: string,
        options?: {
          method?: "zscore" | "iqr" | "both"
          zscore_threshold?: number
          iqr_factor?: number
        }
      ) => {
        if (apiClient.offline) return null
        try {
          return await retryWithBackoff(
            () => apiClient.detectAnomalies(sampleId, options),
            { maxAttempts: 2 }
          )
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Failed to run anomaly detection",
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
          fsc_angle_range?: [number, number]
          ssc_angle_range?: [number, number]
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
            fsc_angle_range: settings.fsc_angle_range,
            ssc_angle_range: settings.ssc_angle_range,
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

    // =========================================================================
    // Alerts API (CRMIT-003)
    // =========================================================================

    getAlerts: useCallback(
      async (options?: {
        userId?: number
        sampleId?: number
        severity?: "info" | "warning" | "critical" | "error"
        alertType?: string
        isAcknowledged?: boolean
        source?: string
        limit?: number
        offset?: number
      }) => {
        if (apiClient.offline) return null
        try {
          return await retryWithBackoff(() => apiClient.getAlerts(options), {
            maxAttempts: 2,
          })
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Failed to fetch alerts",
            description: message,
          })
          return null
        }
      },
      [toast]
    ),

    getAlertCounts: useCallback(
      async (userId?: number) => {
        if (apiClient.offline) return null
        try {
          return await retryWithBackoff(() => apiClient.getAlertCounts(userId), {
            maxAttempts: 2,
          })
        } catch (error) {
          // Silent fail for counts - they're non-critical
          console.error("Failed to fetch alert counts:", error)
          return null
        }
      },
      []
    ),

    acknowledgeAlert: useCallback(
      async (
        alertId: number,
        options?: {
          acknowledgedBy?: number
          notes?: string
        }
      ) => {
        if (apiClient.offline) {
          toast({
            variant: "destructive",
            title: "Backend offline",
            description: "Cannot acknowledge alert - backend server is not running",
          })
          return null
        }

        try {
          const response = await apiClient.acknowledgeAlert(alertId, options)
          toast({
            title: "✅ Alert acknowledged",
            description: "The alert has been marked as reviewed",
          })
          return response
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Failed to acknowledge alert",
            description: message,
          })
          return null
        }
      },
      [toast]
    ),

    acknowledgeMultipleAlerts: useCallback(
      async (
        alertIds: number[],
        options?: {
          acknowledgedBy?: number
          notes?: string
        }
      ) => {
        if (apiClient.offline) {
          toast({
            variant: "destructive",
            title: "Backend offline",
            description: "Cannot acknowledge alerts - backend server is not running",
          })
          return null
        }

        try {
          const response = await apiClient.acknowledgeMultipleAlerts(alertIds, options)
          toast({
            title: "✅ Alerts acknowledged",
            description: `${response.acknowledged_count} alerts have been marked as reviewed`,
          })
          return response
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Failed to acknowledge alerts",
            description: message,
          })
          return null
        }
      },
      [toast]
    ),

    deleteAlert: useCallback(
      async (alertId: number) => {
        if (apiClient.offline) {
          toast({
            variant: "destructive",
            title: "Backend offline",
            description: "Cannot delete alert - backend server is not running",
          })
          return null
        }

        try {
          const response = await apiClient.deleteAlert(alertId)
          toast({
            title: "✅ Alert deleted",
            description: "The alert has been removed",
          })
          return response
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Failed to delete alert",
            description: message,
          })
          return null
        }
      },
      [toast]
    ),

    // =========================================================================
    // Population Shift Detection (CRMIT-004)
    // =========================================================================

    /**
     * Detect population shift between two samples
     */
    detectPopulationShift: useCallback(
      async (options: {
        sample_id_a: string;
        sample_id_b: string;
        metric?: string;
        data_source?: "fcs" | "nta";
        tests?: Array<"ks" | "emd" | "mean" | "variance">;
        alpha?: number;
      }) => {
        if (apiClient.offline) {
          toast({
            variant: "destructive",
            title: "Backend offline",
            description: "Cannot run population shift detection - backend server is not running",
          })
          return null
        }

        try {
          const response = await apiClient.detectPopulationShift(options)
          
          if (response.overall_shift_detected) {
            toast({
              variant: "default",
              title: `⚠️ Population Shift Detected`,
              description: `${response.overall_severity.toUpperCase()} shift between samples. ${response.tests.filter(t => t.significant).length}/${response.tests.length} tests significant.`,
            })
          } else {
            toast({
              title: "✅ No Shift Detected",
              description: "Populations appear stable between samples",
            })
          }
          
          return response
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Population shift analysis failed",
            description: message,
          })
          return null
        }
      },
      [toast]
    ),

    /**
     * Compare multiple samples against a baseline
     */
    compareToBaseline: useCallback(
      async (options: {
        baseline_sample_id: string;
        sample_ids: string[];
        metric?: string;
        data_source?: "fcs" | "nta";
        tests?: Array<"ks" | "emd" | "mean" | "variance">;
        alpha?: number;
      }) => {
        if (apiClient.offline) {
          toast({
            variant: "destructive",
            title: "Backend offline",
            description: "Cannot run baseline comparison - backend server is not running",
          })
          return null
        }

        try {
          const response = await apiClient.compareToBaseline(options)
          
          const shiftedCount = response.comparisons.filter(c => c.overall_shift_detected).length
          if (shiftedCount > 0) {
            toast({
              variant: "default",
              title: `⚠️ Baseline Deviations Found`,
              description: `${shiftedCount}/${response.comparisons.length} samples differ from baseline`,
            })
          } else {
            toast({
              title: "✅ All Samples Match Baseline",
              description: "No significant deviations from baseline detected",
            })
          }
          
          return response
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Baseline comparison failed",
            description: message,
          })
          return null
        }
      },
      [toast]
    ),

    /**
     * Temporal/sequential population shift analysis
     */
    temporalShiftAnalysis: useCallback(
      async (options: {
        sample_ids: string[];
        metric?: string;
        data_source?: "fcs" | "nta";
        tests?: Array<"ks" | "emd" | "mean" | "variance">;
        alpha?: number;
      }) => {
        if (apiClient.offline) {
          toast({
            variant: "destructive",
            title: "Backend offline",
            description: "Cannot run temporal analysis - backend server is not running",
          })
          return null
        }

        try {
          const response = await apiClient.temporalShiftAnalysis(options)
          
          if (response.any_significant_shift) {
            const driftPoints = response.comparisons.filter(c => c.overall_shift_detected).length
            toast({
              variant: "default",
              title: `⚠️ Temporal Drift Detected`,
              description: `${driftPoints} transition point(s) show significant shift`,
            })
          } else {
            toast({
              title: "✅ No Temporal Drift",
              description: "Population stable across all time points",
            })
          }
          
          return response
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Temporal analysis failed",
            description: message,
          })
          return null
        }
      },
      [toast]
    ),

    // ========================================================================
    // CRMIT-007: Temporal Analysis Hooks
    // ========================================================================

    /**
     * Analyze temporal trends (trend, stability, drift) for samples
     */
    analyzeTemporalTrends: useCallback(
      async (options: {
        sample_ids: string[];
        metric?: string;
        data_source?: "fcs" | "nta";
        alpha?: number;
        include_correlations?: boolean;
      }) => {
        if (apiClient.offline) {
          toast({
            variant: "destructive",
            title: "Backend offline",
            description: "Cannot run temporal analysis - backend server is not running",
          })
          return null
        }

        try {
          const response = await apiClient.analyzeTemporalTrends(options)
          
          // Show toast based on results
          const { stability, drift, trend } = response
          
          if (drift.severity !== "none" && drift.is_significant) {
            toast({
              variant: drift.severity === "critical" || drift.severity === "significant" 
                ? "destructive" 
                : "default",
              title: `⚠️ Drift Detected (${drift.severity})`,
              description: drift.interpretation,
            })
          } else if (stability.level === "poor" || stability.level === "unstable") {
            toast({
              variant: "default",
              title: `📊 ${stability.level === "unstable" ? "Unstable" : "Variable"} Measurements`,
              description: `CV = ${stability.cv.toFixed(1)}% - ${stability.interpretation}`,
            })
          } else if (trend.is_significant) {
            toast({
              title: `📈 Trend Detected`,
              description: trend.interpretation,
            })
          } else {
            toast({
              title: "✅ Stable Time Series",
              description: response.summary,
            })
          }
          
          return response
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Temporal analysis failed",
            description: message,
          })
          return null
        }
      },
      [toast]
    ),

    /**
     * Analyze multiple metrics over time
     */
    analyzeMultiMetricTemporal: useCallback(
      async (options: {
        sample_ids: string[];
        metrics?: string[];
        data_source?: "fcs" | "nta";
        alpha?: number;
      }) => {
        if (apiClient.offline) {
          toast({
            variant: "destructive",
            title: "Backend offline",
            description: "Cannot run temporal analysis - backend server is not running",
          })
          return null
        }

        try {
          const response = await apiClient.analyzeMultiMetricTemporal(options)
          
          // Show summary toast
          const { overall_stability, overall_drift } = response
          const driftingCount = overall_drift.total_drifting_metrics
          
          if (driftingCount > 0) {
            toast({
              variant: overall_drift.max_severity === "critical" || overall_drift.max_severity === "significant"
                ? "destructive"
                : "default",
              title: `⚠️ ${driftingCount} Metric(s) Show Drift`,
              description: `Max severity: ${overall_drift.max_severity}`,
            })
          } else {
            toast({
              title: `✅ Temporal Analysis Complete`,
              description: `${response.metrics_analyzed.length} metrics analyzed - Overall stability: ${overall_stability.level}`,
            })
          }
          
          return response
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Multi-metric temporal analysis failed",
            description: message,
          })
          return null
        }
      },
      [toast]
    ),
  }
}
