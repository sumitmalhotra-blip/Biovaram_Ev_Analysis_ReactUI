"use client"

import { createContext, useContext, useEffect, useState, ReactNode } from "react"

// Context for hydration state
const HydrationContext = createContext<boolean>(false)

interface StoreProviderProps {
  children: ReactNode
}

/**
 * Provider component that handles Zustand store hydration from localStorage.
 * Wrap your app with this to ensure persisted state is properly restored
 * before rendering components that depend on the store.
 */
export function StoreProvider({ children }: StoreProviderProps) {
  const [isHydrated, setIsHydrated] = useState(false)

  useEffect(() => {
    // Zustand persist middleware automatically rehydrates,
    // we just need to signal that client-side rendering is ready
    setIsHydrated(true)
  }, [])

  return (
    <HydrationContext.Provider value={isHydrated}>
      {children}
    </HydrationContext.Provider>
  )
}

/**
 * Hook to check if the store has been hydrated from localStorage
 */
export function useStoreHydration() {
  return useContext(HydrationContext)
}
