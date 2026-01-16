"use client"

import { useEffect, useState, Suspense, lazy } from "react"
import { Header } from "@/components/header"
import { TabNavigation } from "@/components/tab-navigation"
import { Sidebar } from "@/components/sidebar"
import { ErrorBoundary } from "@/components/error-boundary"
import { useAnalysisStore } from "@/lib/store"
import { Toaster } from "@/components/ui/toaster"
import { Loader2 } from "lucide-react"

// PERFORMANCE: Lazy load heavy tab components
const DashboardTab = lazy(() => import("@/components/dashboard/dashboard-tab").then(m => ({ default: m.DashboardTab })))
const FlowCytometryTab = lazy(() => import("@/components/flow-cytometry/flow-cytometry-tab").then(m => ({ default: m.FlowCytometryTab })))
const NTATab = lazy(() => import("@/components/nta/nta-tab").then(m => ({ default: m.NTATab })))
const CrossCompareTab = lazy(() => import("@/components/cross-compare/cross-compare-tab").then(m => ({ default: m.CrossCompareTab })))
const ResearchChatTab = lazy(() => import("@/components/research-chat/research-chat-tab").then(m => ({ default: m.ResearchChatTab })))

// Loading fallback component
function TabLoading() {
  return (
    <div className="flex items-center justify-center h-64">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
      <span className="ml-2 text-muted-foreground">Loading...</span>
    </div>
  )
}

// Full page loading for hydration
function HydrationLoading() {
  return (
    <div className="h-screen w-screen flex items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
        <span className="text-muted-foreground">Loading analysis platform...</span>
      </div>
    </div>
  )
}

export default function Home() {
  const { activeTab, isDarkMode } = useAnalysisStore()
  const [hydrated, setHydrated] = useState(false)

  // Handle hydration - wait for client-side state to be restored
  useEffect(() => {
    setHydrated(true)
  }, [])

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add("dark")
    } else {
      document.documentElement.classList.remove("dark")
    }
  }, [isDarkMode])

  // Show loading state until hydration is complete
  if (!hydrated) {
    return <HydrationLoading />
  }

  return (
    <ErrorBoundary>
      <div className="h-screen w-screen flex flex-col bg-background text-foreground overflow-hidden">
        <Header />
        <TabNavigation />

        <div className="flex-1 flex overflow-hidden">
          <div className="hidden md:block shrink-0">
            <Sidebar />
          </div>

          <main className="flex-1 overflow-y-auto overflow-x-hidden">
            <ErrorBoundary>
              {/* PERFORMANCE: Wrap lazy-loaded components in Suspense */}
              <Suspense fallback={<TabLoading />}>
                {activeTab === "dashboard" && <DashboardTab />}
                {activeTab === "flow-cytometry" && <FlowCytometryTab />}
                {activeTab === "nta" && <NTATab />}
                {activeTab === "cross-compare" && <CrossCompareTab />}
                {activeTab === "research-chat" && <ResearchChatTab />}
              </Suspense>
            </ErrorBoundary>
          </main>
        </div>

        <Toaster />
      </div>
    </ErrorBoundary>
  )
}
