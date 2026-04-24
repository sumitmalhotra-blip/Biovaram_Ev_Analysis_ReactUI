"use client"

/**
 * useLazyCharts — optimized chart loading for 5-10 FCS files
 *
 * Problem: When 5-10 FCS files are uploaded, all charts render simultaneously
 * causing the UI to freeze. This hook staggers chart rendering using
 * IntersectionObserver so only visible charts load, and defers heavy
 * computations to idle time.
 *
 * Usage:
 *   const { visibleCharts, registerChart, isChartVisible } = useLazyCharts()
 *
 *   // In your chart component:
 *   const ref = useRef<HTMLDivElement>(null)
 *   useEffect(() => registerChart("size-dist", ref), [])
 *   if (!isChartVisible("size-dist")) return <ChartSkeleton />
 *   return <ActualChart />
 */

import { useCallback, useEffect, useRef, useState } from "react"

// ============================================================================
// Types
// ============================================================================

interface ChartEntry {
  id: string
  ref: React.RefObject<HTMLElement>
  priority: number  // lower = loads first
}

interface UseLazyChartsReturn {
  visibleCharts: Set<string>
  registerChart: (id: string, ref: React.RefObject<HTMLElement>, priority?: number) => void
  isChartVisible: (id: string) => boolean
  loadedCount: number
  totalCount: number
}

// ============================================================================
// Hook
// ============================================================================

export function useLazyCharts(batchSize = 2): UseLazyChartsReturn {
  const [visibleCharts, setVisibleCharts] = useState<Set<string>>(new Set())
  const chartRegistry = useRef<Map<string, ChartEntry>>(new Map())
  const observerRef = useRef<IntersectionObserver | null>(null)
  const loadQueueRef = useRef<string[]>([])
  const isProcessingRef = useRef(false)

  // Process load queue in batches — prevents all charts rendering at once
  const processQueue = useCallback(() => {
    if (isProcessingRef.current || loadQueueRef.current.length === 0) return
    isProcessingRef.current = true

    const batch = loadQueueRef.current.splice(0, batchSize)

    // Use requestIdleCallback if available, fallback to setTimeout
    const schedule = (cb: () => void) => {
      if (typeof window !== "undefined" && "requestIdleCallback" in window) {
        (window as Window & { requestIdleCallback: (cb: () => void) => void })
          .requestIdleCallback(cb)
      } else {
        setTimeout(cb, 16) // ~1 frame
      }
    }

    schedule(() => {
      setVisibleCharts((prev) => {
        const next = new Set(prev)
        batch.forEach((id) => next.add(id))
        return next
      })
      isProcessingRef.current = false

      // Process next batch after a small delay
      if (loadQueueRef.current.length > 0) {
        setTimeout(processQueue, 50)
      }
    })
  }, [batchSize])

  // Set up IntersectionObserver
  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const id = entry.target.getAttribute("data-chart-id")
            if (id && !visibleCharts.has(id)) {
              loadQueueRef.current.push(id)
              observerRef.current?.unobserve(entry.target)
            }
          }
        })
        processQueue()
      },
      {
        rootMargin: "100px",  // start loading 100px before visible
        threshold: 0.1,
      }
    )

    return () => observerRef.current?.disconnect()
  }, [processQueue, visibleCharts])

  // Load high-priority charts immediately (priority 0)
  useEffect(() => {
    chartRegistry.current.forEach((entry) => {
      if (entry.priority === 0 && !visibleCharts.has(entry.id)) {
        loadQueueRef.current.unshift(entry.id)
      }
    })
    processQueue()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const registerChart = useCallback(
    (
      id: string,
      ref: React.RefObject<HTMLElement>,
      priority = 1
    ) => {
      chartRegistry.current.set(id, { id, ref, priority })

      // High priority charts load immediately
      if (priority === 0) {
        loadQueueRef.current.unshift(id)
        processQueue()
        return
      }

      // Others observed via IntersectionObserver
      if (ref.current) {
        ref.current.setAttribute("data-chart-id", id)
        observerRef.current?.observe(ref.current)
      }
    },
    [processQueue]
  )

  const isChartVisible = useCallback(
    (id: string) => visibleCharts.has(id),
    [visibleCharts]
  )

  return {
    visibleCharts,
    registerChart,
    isChartVisible,
    loadedCount: visibleCharts.size,
    totalCount: chartRegistry.current.size,
  }
}


// ============================================================================
// ChartSkeleton — shown while chart is loading
// ============================================================================

export function ChartSkeleton({
  height = 300,
  label,
}: {
  height?: number
  label?: string
}) {
  return (
    <div
      className="flex flex-col items-center justify-center bg-muted/20 rounded-lg border border-dashed animate-pulse"
      style={{ height }}
    >
      <div className="space-y-2 text-center">
        <div className="h-3 w-24 bg-muted rounded mx-auto" />
        <div className="h-2 w-16 bg-muted/60 rounded mx-auto" />
        {label && (
          <p className="text-xs text-muted-foreground mt-2">{label}</p>
        )}
      </div>
    </div>
  )
}


// ============================================================================
// LazyChart wrapper — wraps any chart with lazy loading
// ============================================================================

interface LazyChartProps {
  id: string
  height?: number
  priority?: number
  label?: string
  registerChart: (
    id: string,
    ref: React.RefObject<HTMLElement>,
    priority?: number
  ) => void
  isChartVisible: (id: string) => boolean
  children: React.ReactNode
}

export function LazyChart({
  id,
  height = 300,
  priority = 1,
  label,
  registerChart,
  isChartVisible,
  children,
}: LazyChartProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    registerChart(id, ref as React.RefObject<HTMLElement>, priority)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  return (
    <div ref={ref} style={{ minHeight: height }}>
      {isChartVisible(id) ? children : <ChartSkeleton height={height} label={label} />}
    </div>
  )
}


// ============================================================================
// FCSChartLoadingProgress — shows how many charts have loaded
// ============================================================================

export function FCSChartLoadingProgress({
  loadedCount,
  totalCount,
}: {
  loadedCount: number
  totalCount: number
}) {
  if (loadedCount >= totalCount || totalCount === 0) return null

  const pct = Math.round((loadedCount / totalCount) * 100)

  return (
    <div className="flex items-center gap-3 text-xs text-muted-foreground px-1">
      <div className="flex-1 bg-muted rounded-full h-1.5 overflow-hidden">
        <div
          className="h-full bg-primary rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span>
        Loading charts {loadedCount}/{totalCount}
      </span>
    </div>
  )
}
