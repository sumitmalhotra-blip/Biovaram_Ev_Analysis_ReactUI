"use client"

import { Button } from "@/components/ui/button"
import { Pin, PinOff } from "lucide-react"
import { useAnalysisStore, type PinnedChart } from "@/lib/store"
import { toast } from "sonner"

interface PinButtonProps {
  chartId: string
  chartTitle: string
  chartSource: string
  chartType: "histogram" | "scatter" | "line" | "bar"
  chartData: unknown
  className?: string
}

export function PinButton({
  chartId,
  chartTitle,
  chartSource,
  chartType,
  chartData,
  className = "",
}: PinButtonProps) {
  const { pinnedCharts, pinChart, unpinChart } = useAnalysisStore()

  const isPinned = pinnedCharts.some((chart) => chart.id === chartId)

  const handleTogglePin = () => {
    if (isPinned) {
      unpinChart(chartId)
      toast.info(`Unpinned "${chartTitle}" from Dashboard`)
    } else {
      const newChart: PinnedChart = {
        id: chartId,
        title: chartTitle,
        source: chartSource,
        timestamp: new Date(),
        type: chartType,
        data: chartData,
      }
      pinChart(newChart)
      toast.success(`Pinned "${chartTitle}" to Dashboard`)
    }
  }

  return (
    <Button
      variant={isPinned ? "secondary" : "outline"}
      size="sm"
      className={`gap-2 ${className}`}
      onClick={handleTogglePin}
    >
      {isPinned ? (
        <>
          <PinOff className="h-3.5 w-3.5" />
          Unpin
        </>
      ) : (
        <>
          <Pin className="h-3.5 w-3.5" />
          Pin to Dashboard
        </>
      )}
    </Button>
  )
}
