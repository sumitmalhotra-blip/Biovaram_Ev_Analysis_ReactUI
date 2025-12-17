"use client"

import type React from "react"

import { useAnalysisStore, type TabType } from "@/lib/store"
import { cn } from "@/lib/utils"
import { LayoutDashboard, Microscope, Atom, GitCompare, MessageCircle } from "lucide-react"

const tabs: { id: TabType; label: string; shortLabel: string; icon: React.ElementType }[] = [
  { id: "dashboard", label: "Dashboard", shortLabel: "Home", icon: LayoutDashboard },
  { id: "flow-cytometry", label: "Flow Cytometry", shortLabel: "Flow", icon: Microscope },
  { id: "nta", label: "NTA", shortLabel: "NTA", icon: Atom },
  { id: "cross-compare", label: "Cross-Compare", shortLabel: "Compare", icon: GitCompare },
  { id: "research-chat", label: "Research Chat", shortLabel: "Chat", icon: MessageCircle },
]

export function TabNavigation() {
  const { activeTab, setActiveTab } = useAnalysisStore()

  return (
    <nav className="h-12 border-b border-border/50 bg-card flex items-center px-2 md:px-4 gap-1 overflow-x-auto shrink-0 scrollbar-none">
      {tabs.map((tab) => {
        const Icon = tab.icon
        return (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center gap-1.5 md:gap-2 px-2.5 md:px-4 py-2 rounded-lg text-xs md:text-sm font-medium transition-all duration-200 whitespace-nowrap shrink-0 group",
              activeTab === tab.id
                ? "bg-gradient-to-r from-primary to-accent text-primary-foreground shadow-lg shadow-primary/30"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/50",
            )}
          >
            <Icon className="h-4 w-4 shrink-0 transition-transform group-hover:scale-110" />
            <span className="hidden sm:block">{tab.label}</span>
            <span className="sm:hidden">{tab.shortLabel}</span>
          </button>
        )
      })}
    </nav>
  )
}
