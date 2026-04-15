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
import {
  buildScatterPriorityOrder,
  clampCompareLoadConfig,
  isCurrentCompareRequestVersion,
  normalizeCompareSampleIds,
  normalizeVisibleSampleIds,
} from "@/lib/fcs-compare-acceptance-helpers"
import { runScatterSeriesWorker } from "@/lib/fcs-series-worker-client"
import { buildScatterSeriesCacheKey, estimateSeriesBytes } from "@/lib/fcs-series-cache-utils"

const HEALTH_CHECK_INTERVAL = 30000 // 30 seconds when connected
const HEALTH_CHECK_INTERVAL_DISCONNECTED = 5000 // 5 seconds when disconnected (faster recovery)

export function useApi() {
  const { toast } = useToast()
  // DESKTOP MODE: No session needed — always authenticated locally
  const healthCheckRef = useRef<ReturnType<typeof setTimeout> | null>(null)

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
    setFCSFileMetadata,
    setSecondaryFCSFile,
    setSecondaryFCSSampleId,
    setSecondaryFCSResults,
    setSecondaryFCSAnalyzing,
    setSecondaryFCSError,
    setSecondaryFCSScatterData,
    setFCSCompareSelectedSampleIds,
    setFCSCompareVisibleSampleIds,
    setFCSComparePrimarySampleId,
    setFCSCompareSampleMeta,
    setFCSCompareSampleLoading,
    setFCSCompareSampleError,
    setFCSCompareSampleResult,
    setFCSCompareSampleScatter,
    incrementFCSCompareRequestVersion,
    getFCSSeriesCacheEntry,
    setFCSSeriesCacheEntry,
    setOverlayConfig,
    setNTAFile,
    setNTASampleId,
    setNTAResults,
    setNTAAnalyzing,
    setNTAError,
    setNTAFileMetadata,
    setNTACompareSampleLoading,
    setNTACompareSampleError,
    setNTACompareSampleResult,
    addProcessingJob,
    updateProcessingJob,
    apiConnected,
    setActiveTab,
  } = useAnalysisStore()

  const isCurrentFCSCompareRequest = useCallback((requestVersion: number) => {
    return isCurrentCompareRequestVersion(useAnalysisStore.getState().fcsCompareRequestVersion, requestVersion)
  }, [])

  const buildCompareItemId = useCallback((seed: string, fallbackIndex: number) => {
    const normalizedSeed = String(seed || fallbackIndex).replace(/[^a-zA-Z0-9_-]/g, "")
    return `cmp_${Date.now()}_${fallbackIndex}_${normalizedSeed}`
  }, [])

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

  // Start periodic health checks — adaptive: faster when disconnected, slower when connected
  const startHealthCheck = useCallback(() => {
    // Initial check
    checkHealth()

    // Adaptive periodic checks — poll faster when disconnected
    const scheduleNext = () => {
      const interval = apiConnected ? HEALTH_CHECK_INTERVAL : HEALTH_CHECK_INTERVAL_DISCONNECTED
      healthCheckRef.current = setTimeout(() => {
        checkHealth()
        scheduleNext()
      }, interval)
    }
    scheduleNext()

    return () => {
      if (healthCheckRef.current) {
        clearTimeout(healthCheckRef.current)
      }
    }
  }, [checkHealth, apiConnected])

  // =========================================================================
  // Samples
  // =========================================================================

  // Get user ID from session for filtering samples by owner
  // DESKTOP MODE: No user filtering — all samples belong to local user
  const userId = undefined

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
      const requestVersion = type === "fcs" ? incrementFCSCompareRequestVersion() : null

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

        if (requestVersion !== null && !isCurrentFCSCompareRequest(requestVersion)) {
          return false
        }
        
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

          if (!isCurrentFCSCompareRequest(requestVersion!)) {
            return false
          }
          
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
        if (requestVersion !== null && !isCurrentFCSCompareRequest(requestVersion)) {
          return false
        }

        const message = getUserFriendlyErrorMessage(error)
        toast({
          variant: "destructive",
          title: "Failed to load sample",
          description: message,
        })
        return false
      }
    },
    [
      toast,
      setFCSSampleId,
      setFCSResults,
      setNTASampleId,
      setNTAResults,
      setActiveTab,
      incrementFCSCompareRequestVersion,
      isCurrentFCSCompareRequest,
    ]
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
        dye?: string
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

      const requestVersion = incrementFCSCompareRequestVersion()

      setFCSFile(file)
      setFCSAnalyzing(true)
      setFCSError(null)

      try {
        // Include user_id and Mie settings in metadata for ownership and physics
        const fcsSettings = useAnalysisStore.getState().fcsAnalysisSettings
        const uploadMetadata = { 
          ...metadata, 
          user_id: userId,
          wavelength_nm: fcsSettings?.laserWavelength,
          n_particle: fcsSettings?.particleRI,
          n_medium: fcsSettings?.mediumRI,
        }
        
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

        if (!isCurrentFCSCompareRequest(requestVersion)) {
          return null
        }

        if (response.success) {
          setFCSSampleId(response.sample_id)

          console.log("[uploadFCS] Upload response:", response)
          console.log("[uploadFCS] FCS results:", response.fcs_results)
          console.log("[uploadFCS] File metadata:", response.file_metadata)

          if (response.fcs_results) {
            setFCSResults(response.fcs_results)
          }
          
          // Store extracted file metadata for auto-filling experimental conditions
          if (response.file_metadata) {
            setFCSFileMetadata(response.file_metadata)
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
        if (!isCurrentFCSCompareRequest(requestVersion)) {
          return null
        }

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
        if (isCurrentFCSCompareRequest(requestVersion)) {
          setFCSAnalyzing(false)
        }
      }
    },
    [
      setFCSFile,
      setFCSAnalyzing,
      setFCSError,
      setFCSSampleId,
      setFCSResults,
      setFCSFileMetadata,
      addProcessingJob,
      fetchSamples,
      toast,
      userId,
      incrementFCSCompareRequestVersion,
      isCurrentFCSCompareRequest,
    ]
  )

  // Upload secondary FCS file for comparison/overlay
  const uploadSecondaryFCS = useCallback(
    async (
      file: File,
      metadata?: {
        treatment?: string
        dye?: string
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

      const requestVersion = incrementFCSCompareRequestVersion()

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

        if (!isCurrentFCSCompareRequest(requestVersion)) {
          return null
        }

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

          toast({
            title: "✅ Comparison file uploaded",
            description: `${file.name} uploaded for comparison. Sample ID: ${response.sample_id}`,
          })

          return response
        }
      } catch (error) {
        if (!isCurrentFCSCompareRequest(requestVersion)) {
          return null
        }

        const message = getUserFriendlyErrorMessage(error)
        setSecondaryFCSError(message)
        toast({
          variant: "destructive",
          title: "Upload failed",
          description: message,
        })
        return null
      } finally {
        if (isCurrentFCSCompareRequest(requestVersion)) {
          setSecondaryFCSAnalyzing(false)
        }
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
      incrementFCSCompareRequestVersion,
      isCurrentFCSCompareRequest,
    ]
  )

  const uploadFCSCompareBatch = useCallback(
    async (
      files: Array<File | { key: string; file: File }>,
      options?: {
        metadata?: {
          treatment?: string
          dye?: string
          concentration_ug?: number
          preparation_method?: string
          operator?: string
          notes?: string
        }
        onFileStatus?: (update: {
          key: string
          fileName: string
          status: "uploading" | "uploaded" | "session_added" | "upload_failed" | "session_add_failed"
          sampleId?: string
          compareItemId?: string
          error?: string
        }) => void
      }
    ): Promise<{
      total: number
      success: number
      failed: number
      successfulSampleIds: string[]
      failedByFileKey: Record<string, string>
      ingestLog: Array<{
        fileKey: string
        fileName: string
        backendId: number | string | null
        sampleId: string | null
        compareItemId: string | null
        uploadOutcome: "success" | "failed"
        sessionAddOutcome: "added" | "failed" | "skipped"
        reason?: string
      }>
    }> => {
      const cappedFiles = files.slice(0, 10).map((entry, index) => {
        if (entry instanceof File) {
          return {
            key: `${entry.name}-${entry.lastModified}-${index}`,
            file: entry,
          }
        }
        return entry
      })

      if (cappedFiles.length === 0) {
        return { total: 0, success: 0, failed: 0, successfulSampleIds: [], failedByFileKey: {}, ingestLog: [] }
      }

      const currentState = useAnalysisStore.getState()
      const existingSelected = currentState.fcsCompareSession.selectedSampleIds
      const uploadedCompareItemIds: string[] = []
      const failedByFileKey: Record<string, string> = {}
      const ingestLog: Array<{
        fileKey: string
        fileName: string
        backendId: number | string | null
        sampleId: string | null
        compareItemId: string | null
        uploadOutcome: "success" | "failed"
        sessionAddOutcome: "added" | "failed" | "skipped"
        reason?: string
      }> = []

      const fcsSettings = useAnalysisStore.getState().fcsAnalysisSettings

      for (let index = 0; index < cappedFiles.length; index += 1) {
        const { file, key } = cappedFiles[index]

        options?.onFileStatus?.({ key, fileName: file.name, status: "uploading" })

        try {
          const response = await retryWithBackoff(
            () => apiClient.uploadFCS(file, {
              ...options?.metadata,
              user_id: userId,
              wavelength_nm: fcsSettings?.laserWavelength,
              n_particle: fcsSettings?.particleRI,
              n_medium: fcsSettings?.mediumRI,
            }),
            {
              maxAttempts: 2,
              initialDelay: 1500,
              shouldRetry: (error) => {
                const category = categorizeError(error)
                return category === "server" || category === "timeout"
              },
            }
          )

          const compareItemId = buildCompareItemId(String(response.id ?? response.sample_id), index)

          uploadedCompareItemIds.push(compareItemId)
          setFCSCompareSampleMeta(compareItemId, {
            backendSampleId: response.sample_id,
            sampleLabel: response.sample_id,
            fileName: file.name,
            treatment: options?.metadata?.treatment,
            dye: options?.metadata?.dye,
          })
          setFCSCompareSampleResult(compareItemId, response.fcs_results ?? null)
          setFCSCompareSampleError(compareItemId, null)
          setFCSCompareSampleLoading(compareItemId, false)

          ingestLog.push({
            fileKey: key,
            fileName: file.name,
            backendId: response.id ?? null,
            sampleId: response.sample_id ?? null,
            compareItemId,
            uploadOutcome: "success",
            sessionAddOutcome: "skipped",
          })

          addProcessingJob({
            id: `${response.job_id}_compare_${index}`,
            job_type: "fcs_parse",
            status: response.processing_status,
            sample_id: response.id,
          })

          options?.onFileStatus?.({
            key,
            fileName: file.name,
            status: "uploaded",
            sampleId: response.sample_id,
            compareItemId,
          })
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          failedByFileKey[key] = message
          ingestLog.push({
            fileKey: key,
            fileName: file.name,
            backendId: null,
            sampleId: null,
            compareItemId: null,
            uploadOutcome: "failed",
            sessionAddOutcome: "skipped",
            reason: message,
          })
          options?.onFileStatus?.({
            key,
            fileName: file.name,
            status: "upload_failed",
            error: message,
          })
        }
      }

      let successfulSampleIds: string[] = []

      if (uploadedCompareItemIds.length > 0) {
        const mergedSelected = Array.from(new Set([...existingSelected, ...uploadedCompareItemIds])).slice(0, 10)
        setFCSCompareSelectedSampleIds(mergedSelected)
        setFCSCompareVisibleSampleIds(mergedSelected)

        const latestState = useAnalysisStore.getState()
        if (!latestState.fcsCompareSession.primarySampleId) {
          setFCSComparePrimarySampleId(uploadedCompareItemIds[0])
        }

        const selectedAfterMerge = useAnalysisStore.getState().fcsCompareSession.selectedSampleIds
        successfulSampleIds = uploadedCompareItemIds.filter((id) => selectedAfterMerge.includes(id))
        const failedSessionAdds = uploadedCompareItemIds.filter((id) => !selectedAfterMerge.includes(id))

        ingestLog.forEach((entry) => {
          if (!entry.compareItemId || entry.uploadOutcome !== "success") {
            return
          }
          if (successfulSampleIds.includes(entry.compareItemId)) {
            entry.sessionAddOutcome = "added"
            options?.onFileStatus?.({
              key: entry.fileKey,
              fileName: entry.fileName,
              status: "session_added",
              sampleId: entry.sampleId ?? undefined,
              compareItemId: entry.compareItemId,
            })
          } else {
            const reason = "Uploaded successfully but could not be added to compare session (selection limit reached)."
            entry.sessionAddOutcome = "failed"
            entry.reason = reason
            failedByFileKey[entry.fileKey] = reason
            options?.onFileStatus?.({
              key: entry.fileKey,
              fileName: entry.fileName,
              status: "session_add_failed",
              sampleId: entry.sampleId ?? undefined,
              compareItemId: entry.compareItemId,
              error: reason,
            })
          }
        })

        // Preserve current two-file compare behavior while adding multi-file session support.
        if (!latestState.fcsAnalysis.sampleId) {
          const firstId = successfulSampleIds[0]
          const firstResult = latestState.fcsCompareSession.resultsBySampleId[firstId] ?? null
          setFCSFile(cappedFiles[0].file)
          setFCSSampleId(firstId)
          setFCSResults(firstResult)
        }

        if (!latestState.secondaryFcsAnalysis.sampleId && successfulSampleIds.length > 1) {
          const secondId = successfulSampleIds[1]
          const secondResult = latestState.fcsCompareSession.resultsBySampleId[secondId] ?? null
          setSecondaryFCSFile(cappedFiles[1]?.file ?? null)
          setSecondaryFCSSampleId(secondId)
          setSecondaryFCSResults(secondResult)
        }

        if (successfulSampleIds.length > 0) {
          fetchSamples()
        }
      }

      if (ingestLog.length > 0) {
        console.info("[FCS_COMPARE_INGEST_LOG]", ingestLog)
      }

      return {
        total: cappedFiles.length,
        success: successfulSampleIds.length,
        failed: cappedFiles.length - successfulSampleIds.length,
        successfulSampleIds,
        failedByFileKey,
        ingestLog,
      }
    },
    [
      userId,
      buildCompareItemId,
      setFCSCompareSampleMeta,
      setFCSCompareSampleResult,
      setFCSCompareSampleError,
      setFCSCompareSampleLoading,
      addProcessingJob,
      setFCSCompareSelectedSampleIds,
      setFCSCompareVisibleSampleIds,
      setFCSComparePrimarySampleId,
      setFCSFile,
      setFCSSampleId,
      setFCSResults,
      setSecondaryFCSFile,
      setSecondaryFCSSampleId,
      setSecondaryFCSResults,
      setOverlayConfig,
      fetchSamples,
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

  const loadFCSCompareSamples = useCallback(
    async (
      sampleIds: string[],
      options?: {
        visibleSampleIds?: string[]
        resultConcurrency?: number
        scatterConcurrency?: number
        scatterPointLimit?: number
        preserveSessionSelection?: boolean
      }
    ): Promise<{
      total: number
      loadedResults: number
      loadedScatter: number
      failed: number
      resultsBySampleId: Record<string, FCSResult | null>
      scatterBySampleId: Record<string, Array<{ x: number; y: number; index: number; diameter?: number }> | null>
      errorsBySampleId: Record<string, string>
      cacheStats: { hits: number; misses: number; evictions: number }
      cancelled: boolean
    }> => {
      const normalizedSampleIds = normalizeCompareSampleIds(sampleIds, 10)

      if (normalizedSampleIds.length === 0) {
        return {
          total: 0,
          loadedResults: 0,
          loadedScatter: 0,
          failed: 0,
          resultsBySampleId: {},
          scatterBySampleId: {},
          errorsBySampleId: {},
          cacheStats: { hits: 0, misses: 0, evictions: 0 },
          cancelled: false,
        }
      }

      const requestVersion = incrementFCSCompareRequestVersion()
      const isStale = () => !isCurrentFCSCompareRequest(requestVersion)

      const { resultConcurrency, scatterConcurrency, scatterPointLimit } = clampCompareLoadConfig(options)
      const adaptiveScatterConcurrency = normalizedSampleIds.length >= 5
        ? 1
        : scatterConcurrency
      const adaptiveScatterPointLimit = normalizedSampleIds.length >= 5
        ? Math.min(scatterPointLimit, 1200)
        : scatterPointLimit
      const normalizedVisible = normalizeVisibleSampleIds(options?.visibleSampleIds ?? [], normalizedSampleIds)
      const scatterPriorityOrder = buildScatterPriorityOrder(normalizedSampleIds, normalizedVisible)

      if (!options?.preserveSessionSelection) {
        setFCSCompareSelectedSampleIds(normalizedSampleIds)
        setFCSCompareVisibleSampleIds(normalizedVisible)
      }

      const state = useAnalysisStore.getState()
      const compareMetaById = state.fcsCompareSession.compareItemMetaById ?? {}
      const primarySampleId = state.fcsAnalysis.sampleId
      const secondarySampleId = state.secondaryFcsAnalysis.sampleId
      const preferredPrimary = state.fcsCompareSession.primarySampleId
      const resolvedPrimary = preferredPrimary && normalizedSampleIds.includes(preferredPrimary)
        ? preferredPrimary
        : (normalizedSampleIds[0] ?? null)

      if (!options?.preserveSessionSelection) {
        setFCSComparePrimarySampleId(resolvedPrimary)
      }

      normalizedSampleIds.forEach((sampleId) => {
        setFCSCompareSampleLoading(sampleId, true)
        setFCSCompareSampleError(sampleId, null)
      })

      if (apiClient.offline) {
        return {
          total: normalizedSampleIds.length,
          loadedResults: 0,
          loadedScatter: 0,
          failed: normalizedSampleIds.length,
          resultsBySampleId: Object.fromEntries(normalizedSampleIds.map((id) => [id, null])),
          scatterBySampleId: Object.fromEntries(normalizedSampleIds.map((id) => [id, null])),
          errorsBySampleId: Object.fromEntries(normalizedSampleIds.map((id) => [id, "Backend offline"])),
          cacheStats: { hits: 0, misses: 0, evictions: 0 },
          cancelled: false,
        }
      }

      const resultsBySampleId: Record<string, FCSResult | null> = {}
      const scatterBySampleId: Record<string, Array<{ x: number; y: number; index: number; diameter?: number }> | null> = {}
      const errorsBySampleId: Record<string, string> = {}
      let loadedResults = 0
      let loadedScatter = 0
      let failed = 0
      let cacheHits = 0
      let cacheMisses = 0
      let cacheEvictions = 0

      try {
        let resultCursor = 0
        const resultWorker = async () => {
          while (true) {
            const currentIndex = resultCursor
            resultCursor += 1

            const compareItemId = normalizedSampleIds[currentIndex]
            if (!compareItemId) {
              return
            }

            const backendSampleId = compareMetaById[compareItemId]?.backendSampleId || compareItemId

            if (isStale()) {
              return
            }

            try {
              const response = await apiClient.getFCSResults(backendSampleId)

              if (isStale()) {
                return
              }

              const latestResult = response?.results?.[0] || null
              resultsBySampleId[compareItemId] = latestResult
              setFCSCompareSampleResult(compareItemId, latestResult)

              if (latestResult) {
                loadedResults += 1

                if (compareItemId === primarySampleId) {
                  setFCSResults(latestResult)
                }
                if (compareItemId === secondarySampleId) {
                  setSecondaryFCSResults(latestResult)
                }
              } else {
                failed += 1
                errorsBySampleId[compareItemId] = "No FCS results found"
                setFCSCompareSampleError(compareItemId, "No FCS results found")
              }
            } catch (error) {
              if (isStale()) {
                return
              }

              failed += 1
              const message = getUserFriendlyErrorMessage(error)
              resultsBySampleId[compareItemId] = null
              errorsBySampleId[compareItemId] = message
              setFCSCompareSampleResult(compareItemId, null)
              setFCSCompareSampleError(compareItemId, message)
            }
          }
        }

        await Promise.all(
          Array.from({ length: Math.min(resultConcurrency, normalizedSampleIds.length) }, () => resultWorker())
        )

        if (isStale()) {
          return {
            total: normalizedSampleIds.length,
            loadedResults,
            loadedScatter,
            failed,
            resultsBySampleId,
            scatterBySampleId,
            errorsBySampleId,
            cacheStats: { hits: cacheHits, misses: cacheMisses, evictions: cacheEvictions },
            cancelled: true,
          }
        }

        let scatterCursor = 0
        const scatterWorker = async () => {
          while (true) {
            const currentIndex = scatterCursor
            scatterCursor += 1

            const compareItemId = scatterPriorityOrder[currentIndex]
            if (!compareItemId) {
              return
            }

            const backendSampleId = compareMetaById[compareItemId]?.backendSampleId || compareItemId

            if (isStale()) {
              return
            }

            try {
              const scatterResponse = await apiClient.getScatterData(backendSampleId, adaptiveScatterPointLimit)

              if (isStale()) {
                return
              }

              const rawScatterData = (scatterResponse?.data ?? []) as Array<{ x: number; y: number; index: number; diameter?: number }>
              let scatterData: Array<{ x: number; y: number; index: number; diameter?: number }> | null = null

              if (rawScatterData.length > 0) {
                const scatterCacheKey = buildScatterSeriesCacheKey({
                  sampleId: compareItemId,
                  pointLimit: adaptiveScatterPointLimit,
                })

                const cachedEntry = getFCSSeriesCacheEntry(scatterCacheKey)
                if (cachedEntry && cachedEntry.task === "scatterSeries") {
                  const cachedPayload = cachedEntry.data as { points?: Array<{ x: number; y: number; index: number; diameter?: number }> }
                  if (cachedPayload.points && cachedPayload.points.length > 0) {
                    scatterData = cachedPayload.points
                    cacheHits += 1
                  }
                }

                if (!scatterData) {
                  cacheMisses += 1
                }

                try {
                  if (!scatterData) {
                    const scatterWorkerPayload = await runScatterSeriesWorker(requestVersion * 1000 + currentIndex, {
                      points: rawScatterData,
                      maxPoints: adaptiveScatterPointLimit,
                    })

                    scatterData = scatterWorkerPayload.points.map((point, pointIndex) => ({
                      x: point.x,
                      y: point.y,
                      index: Number.isFinite(point.index) ? point.index : pointIndex,
                      diameter: Number.isFinite(point.diameter) ? point.diameter : undefined,
                    }))
                    const cacheResult = setFCSSeriesCacheEntry({
                      key: scatterCacheKey,
                      task: "scatterSeries",
                      data: scatterWorkerPayload,
                      approxBytes: estimateSeriesBytes(scatterWorkerPayload),
                    })
                    cacheEvictions += cacheResult.evicted
                  }

                  if (isStale()) {
                    return
                  }
                } catch {
                  // Worker failures should not block compare rendering; fall back to local transform.
                  if (!scatterData) {
                    scatterData = rawScatterData
                      .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y))
                      .map((point, index) => ({
                        x: point.x,
                        y: point.y,
                        index: Number.isFinite(point.index) ? point.index : index,
                        diameter: Number.isFinite(point.diameter) ? point.diameter : undefined,
                      }))
                  }
                }
              }

              scatterBySampleId[compareItemId] = scatterData
              setFCSCompareSampleScatter(compareItemId, scatterData)

              if (scatterData && scatterData.length > 0) {
                loadedScatter += 1

                if (compareItemId === secondarySampleId) {
                  setSecondaryFCSScatterData(scatterData)
                }
              } else {
                if (!errorsBySampleId[compareItemId]) {
                  errorsBySampleId[compareItemId] = "No scatter data found"
                  setFCSCompareSampleError(compareItemId, "No scatter data found")
                }
              }
            } catch (error) {
              if (isStale()) {
                return
              }

              const message = getUserFriendlyErrorMessage(error)
              scatterBySampleId[compareItemId] = null
              setFCSCompareSampleScatter(compareItemId, null)
              if (!errorsBySampleId[compareItemId]) {
                errorsBySampleId[compareItemId] = message
                setFCSCompareSampleError(compareItemId, message)
              }
            }
          }
        }

        await Promise.all(
          Array.from({ length: Math.min(adaptiveScatterConcurrency, scatterPriorityOrder.length) }, () => scatterWorker())
        )

        return {
          total: normalizedSampleIds.length,
          loadedResults,
          loadedScatter,
          failed,
          resultsBySampleId,
          scatterBySampleId,
          errorsBySampleId,
          cacheStats: { hits: cacheHits, misses: cacheMisses, evictions: cacheEvictions },
          cancelled: isStale(),
        }
      } finally {
        normalizedSampleIds.forEach((sampleId) => {
          setFCSCompareSampleLoading(sampleId, false)
        })
      }
    },
    [
      incrementFCSCompareRequestVersion,
      isCurrentFCSCompareRequest,
      setFCSCompareSelectedSampleIds,
      setFCSCompareVisibleSampleIds,
      setFCSComparePrimarySampleId,
      setFCSCompareSampleMeta,
      setFCSCompareSampleLoading,
      setFCSCompareSampleError,
      setFCSCompareSampleResult,
      setFCSCompareSampleScatter,
      getFCSSeriesCacheEntry,
      setFCSSeriesCacheEntry,
      setFCSResults,
      setSecondaryFCSResults,
      setSecondaryFCSScatterData,
    ]
  )

  // =========================================================================
  // NTA Upload & Analysis
  // =========================================================================

  const uploadNTA = useCallback(
    async (
      file: File,
      metadata?: {
        treatment?: string
        marker?: string
        dye?: string
        marker_concentration?: number
        marker_concentration_unit?: string
        preparation_method?: string
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

          console.log("[uploadNTA] Upload response:", response)
          console.log("[uploadNTA] File metadata:", response.file_metadata)

          if (response.nta_results) {
            setNTAResults(response.nta_results)
          }
          
          // Store extracted file metadata for auto-filling experimental conditions
          if (response.file_metadata) {
            setNTAFileMetadata(response.file_metadata)
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
      setNTAFileMetadata,
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

  const loadNTACompareSamples = useCallback(
    async (
      sampleIds: string[],
      options?: { concurrency?: number }
    ): Promise<{ total: number; loaded: number; failed: number }> => {
      const normalizedSampleIds = Array.from(new Set(sampleIds)).slice(0, 20)

      if (normalizedSampleIds.length === 0) {
        return { total: 0, loaded: 0, failed: 0 }
      }

      if (apiClient.offline) {
        normalizedSampleIds.forEach((sampleId) => {
          setNTACompareSampleLoading(sampleId, false)
          setNTACompareSampleError(sampleId, "Backend offline")
        })
        return { total: normalizedSampleIds.length, loaded: 0, failed: normalizedSampleIds.length }
      }

      normalizedSampleIds.forEach((sampleId) => {
        setNTACompareSampleLoading(sampleId, true)
        setNTACompareSampleError(sampleId, null)
      })

      // Phase 2 path: attempt bulk endpoint first; fallback to per-sample fetch if unavailable.
      try {
        const bulk = await apiClient.getNTAMultiCompare({
          sample_ids: normalizedSampleIds,
          include_size_distribution: true,
        })

        let loaded = 0
        let failed = 0

        normalizedSampleIds.forEach((sampleId) => {
          const result = bulk.results_by_sample_id?.[sampleId]
          const error = bulk.errors_by_sample_id?.[sampleId]

          if (result) {
            const normalizedResult = {
              ...(result as Partial<NTAResult>),
              id: Number(result.id ?? 0),
            } as NTAResult
            setNTACompareSampleResult(sampleId, normalizedResult)
            setNTACompareSampleError(sampleId, bulk.warnings_by_sample_id?.[sampleId] || null)
            loaded += 1
          } else {
            setNTACompareSampleResult(sampleId, null)
            setNTACompareSampleError(sampleId, error || "No NTA results found")
            failed += 1
          }

          setNTACompareSampleLoading(sampleId, false)
        })

        return {
          total: normalizedSampleIds.length,
          loaded,
          failed,
        }
      } catch {
        // Fallback handled below.
      }

      let cursor = 0
      let loaded = 0
      let failed = 0
      const concurrency = Math.max(1, Math.min(5, options?.concurrency ?? 3))

      const worker = async () => {
        while (true) {
          const currentIndex = cursor
          cursor += 1

          const sampleId = normalizedSampleIds[currentIndex]
          if (!sampleId) {
            return
          }

          try {
            const response = await apiClient.getNTAResults(sampleId)
            const latestResult = response.results?.[0] || null

            if (latestResult) {
              setNTACompareSampleResult(sampleId, latestResult)
              setNTACompareSampleError(sampleId, null)
              loaded += 1
            } else {
              setNTACompareSampleResult(sampleId, null)
              setNTACompareSampleError(sampleId, "No NTA results found")
              failed += 1
            }
          } catch (error) {
            setNTACompareSampleResult(sampleId, null)
            setNTACompareSampleError(sampleId, getUserFriendlyErrorMessage(error))
            failed += 1
          } finally {
            setNTACompareSampleLoading(sampleId, false)
          }
        }
      }

      await Promise.all(
        Array.from(
          { length: Math.min(concurrency, normalizedSampleIds.length) },
          () => worker()
        )
      )

      return {
        total: normalizedSampleIds.length,
        loaded,
        failed,
      }
    },
    [
      setNTACompareSampleLoading,
      setNTACompareSampleError,
      setNTACompareSampleResult,
    ]
  )

  return {
    // Health
    checkHealth,
    startHealthCheck,

    // Samples
    fetchSamples,
    getSample,
    deleteSample,
    openSampleInTab,

    // FCS
    beginFCSCompareRequestVersion: incrementFCSCompareRequestVersion,
    isFCSCompareRequestCurrent: isCurrentFCSCompareRequest,
    loadFCSCompareSamples,
    uploadFCS,
    uploadFCSCompareBatch,
    uploadSecondaryFCS,  // T-002: Secondary file upload for comparison/overlay
    getFCSResults,

    // NTA
    uploadNTA,
    uploadNtaPdf,  // TASK-007: PDF parsing for concentration/dilution
    getNTAResults,
    loadNTACompareSamples,

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
          // Get Mie parameters from store settings
          const fcsSettings = useAnalysisStore.getState().fcsAnalysisSettings
          const mieParams = fcsSettings ? {
            wavelength_nm: fcsSettings.laserWavelength,
            n_particle: fcsSettings.particleRI,
            n_medium: fcsSettings.mediumRI,
          } : undefined
          
          return await retryWithBackoff(
            () => apiClient.getScatterDataWithAxes(sampleId, xChannel, yChannel, maxPoints, mieParams),
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
          // Get Mie parameters from store settings
          const fcsSettings = useAnalysisStore.getState().fcsAnalysisSettings
          const mieParams = fcsSettings ? {
            wavelength_nm: fcsSettings.laserWavelength,
            n_particle: fcsSettings.particleRI,
            n_medium: fcsSettings.mediumRI,
          } : undefined
          
          return await retryWithBackoff(() => apiClient.getSizeBins(sampleId, mieParams), {
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
          // Get Mie parameters from store settings
          const fcsSettings = useAnalysisStore.getState().fcsAnalysisSettings
          const mieParams = fcsSettings ? {
            wavelength_nm: fcsSettings.laserWavelength,
            n_particle: fcsSettings.particleRI,
            n_medium: fcsSettings.mediumRI,
          } : undefined
          
          // Merge Mie params into gate config
          const gateConfigWithMie = {
            ...gateConfig,
            ...mieParams,
          }
          
          const result = await retryWithBackoff(
            () => apiClient.analyzeGatedPopulation(sampleId, gateConfigWithMie),
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

    // =========================================================================
    // Data Split API: Values
    // =========================================================================

    /**
     * Get FCS per-event size values with Mie calculation
     */
    getFCSValues: useCallback(
      async (
        sampleId: string,
        options?: {
          wavelength_nm?: number;
          n_particle?: number;
          n_medium?: number;
          max_events?: number;
          include_raw_channels?: boolean;
        }
      ) => {
        if (apiClient.offline) return null
        try {
          // Get Mie parameters from store if not provided
          const fcsSettings = useAnalysisStore.getState().fcsAnalysisSettings
          const mergedOptions = {
            wavelength_nm: options?.wavelength_nm ?? fcsSettings?.laserWavelength ?? 488,
            n_particle: options?.n_particle ?? fcsSettings?.particleRI ?? 1.40,
            n_medium: options?.n_medium ?? fcsSettings?.mediumRI ?? 1.33,
            max_events: options?.max_events ?? 50000,
            include_raw_channels: options?.include_raw_channels ?? false,
          }
          
          const result = await retryWithBackoff(
            () => apiClient.getFCSValues(sampleId, mergedOptions),
            { maxAttempts: 2 }
          )
          
          if (result) {
            toast({
              title: "✅ FCS Values Loaded",
              description: `${result.data_info.valid_sizes.toLocaleString()} valid sizes from ${result.data_info.returned_events.toLocaleString()} events`,
            })
          }
          
          return result
        } catch (error) {
          const message = getUserFriendlyErrorMessage(error)
          toast({
            variant: "destructive",
            title: "Failed to fetch FCS values",
            description: message,
          })
          return null
        }
      },
      [toast]
    ),
  }
}
