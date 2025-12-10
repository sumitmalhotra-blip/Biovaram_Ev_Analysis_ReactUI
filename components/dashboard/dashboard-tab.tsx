"use client"

import { useAnalysisStore } from "@/lib/store"
import { PinnedCharts } from "./pinned-charts"
import { QuickStats } from "./quick-stats"
import { RecentActivity } from "./recent-activity"
import { QuickUpload } from "./quick-upload"

export function DashboardTab() {
  const { pinnedCharts } = useAnalysisStore()

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-4 md:gap-6 p-4 md:p-6">
      <div className="space-y-4 md:space-y-6 min-w-0">
        {pinnedCharts.length > 0 && <PinnedCharts charts={pinnedCharts} />}
        <QuickStats />
        <RecentActivity />
      </div>
      <div className="space-y-4 md:space-y-6">
        <QuickUpload />
      </div>
    </div>
  )
}
