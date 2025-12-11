"use client"

import { useEffect } from "react"
import { Header } from "@/components/header"
import { TabNavigation } from "@/components/tab-navigation"
import { Sidebar } from "@/components/sidebar"
import { DashboardTab } from "@/components/dashboard/dashboard-tab"
import { FlowCytometryTab } from "@/components/flow-cytometry/flow-cytometry-tab"
import { NTATab } from "@/components/nta/nta-tab"
import { CrossCompareTab } from "@/components/cross-compare/cross-compare-tab"
import { ResearchChatTab } from "@/components/research-chat/research-chat-tab"
import { ErrorBoundary } from "@/components/error-boundary"
import { useAnalysisStore } from "@/lib/store"
import { Toaster } from "@/components/ui/toaster"

export default function Home() {
  const { activeTab, isDarkMode } = useAnalysisStore()

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add("dark")
    } else {
      document.documentElement.classList.remove("dark")
    }
  }, [isDarkMode])

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
              {activeTab === "dashboard" && <DashboardTab />}
              {activeTab === "flow-cytometry" && <FlowCytometryTab />}
              {activeTab === "nta" && <NTATab />}
              {activeTab === "cross-compare" && <CrossCompareTab />}
              {activeTab === "research-chat" && <ResearchChatTab />}
            </ErrorBoundary>
          </main>
        </div>

        <Toaster />
      </div>
    </ErrorBoundary>
  )
}
