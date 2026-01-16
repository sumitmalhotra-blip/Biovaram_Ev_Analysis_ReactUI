"use client"

import { useState, useEffect } from "react"

/**
 * Hook to detect when client-side hydration is complete
 * Use this to prevent hydration mismatches with persisted state
 */
export function useHydration() {
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    // This runs only on the client after hydration
    setHydrated(true)
  }, [])

  return hydrated
}

/**
 * Hook to safely access persisted store values
 * Returns the server-side default until hydration is complete
 */
export function useHydratedStore<T>(
  selector: () => T,
  serverDefault: T
): T {
  const hydrated = useHydration()
  const storeValue = selector()

  return hydrated ? storeValue : serverDefault
}
