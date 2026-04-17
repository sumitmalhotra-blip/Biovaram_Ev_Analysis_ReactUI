"use client"

import { useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Pin, Trash2, X, Download } from "lucide-react"
import { useAnalysisStore, type PinnedChart } from "@/lib/store"
import { MiniChart } from "./mini-chart"
import { useToast } from "@/hooks/use-toast"
import { captureChartAsImage } from "./saved-images-gallery"

interface PinnedChartsProps {
  charts: PinnedChart[]
}

export function PinnedCharts({ charts }: PinnedChartsProps) {
  const { unpinChart, clearPinnedCharts } = useAnalysisStore()
  const { toast } = useToast()
  const chartContainersRef = useRef<Record<string, HTMLDivElement | null>>({})

  const handleDownloadChartImage = async (chart: PinnedChart) => {
    try {
      const fileName = `${chart.title.replace(/\s+/g, "_").toLowerCase()}_${new Date().toISOString().split("T")[0]}.png`
      const container = chartContainersRef.current[chart.id]
      const captured = container
        ? await captureChartAsImage(container, chart.title, chart.source, chart.type)
        : null

      // Guard against icon-sized captures (e.g., toolbar SVG instead of chart surface).
      const captureLooksValid = Boolean(
        captured?.dataUrl
        && (captured.metadata?.width ?? 0) >= 300
        && (captured.metadata?.height ?? 0) >= 180
      )

      if (captureLooksValid && captured) {
        const link = document.createElement("a")
        link.href = captured.dataUrl
        link.download = fileName
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      } else if (chart.snapshotDataUrl) {
        const link = document.createElement("a")
        link.href = chart.snapshotDataUrl
        link.download = fileName
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      } else {
        toast({
          variant: "destructive",
          title: "Download Failed",
          description: "Unable to capture chart image. Re-pin the chart and try again.",
        })
        return
      }

      toast({
        title: "Chart Downloaded",
        description: `${chart.title} downloaded as PNG image.`,
      })
    } catch {
      toast({
        variant: "destructive",
        title: "Download Failed",
        description: `Could not download ${chart.title} as an image.`,
      })
    }
  }

  return (
    <Card className="card-3d">
      <CardHeader className="flex flex-row items-center justify-between pb-2 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-primary/10">
            <Pin className="h-4 w-4 text-primary" />
          </div>
          <CardTitle className="text-base md:text-lg">Pinned Charts</CardTitle>
          <Badge variant="secondary" className="ml-1">
            {charts.length}
          </Badge>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={clearPinnedCharts}
          className="text-muted-foreground hover:text-destructive"
        >
          <Trash2 className="h-4 w-4 mr-1" />
          <span className="hidden sm:inline">Clear All</span>
        </Button>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {charts.map((chart) => (
            <Card
              key={chart.id}
              className="bg-secondary/30 border-border/50 shadow-md hover:shadow-lg transition-shadow"
            >
              <CardHeader className="pb-2 flex flex-row items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <h4 className="text-sm font-medium truncate">{chart.title}</h4>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    <Badge variant="outline" className="text-xs">
                      From: {chart.source}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {new Date(chart.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <Button 
                    variant="ghost" 
                    size="icon" 
                    className="h-6 w-6"
                    onClick={() => handleDownloadChartImage(chart)}
                    title="Download chart image"
                  >
                    <Download className="h-3 w-3" />
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="icon" 
                    className="h-6 w-6" 
                    onClick={() => unpinChart(chart.id)}
                    title="Remove from pinned"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div ref={(el) => { chartContainersRef.current[chart.id] = el }}>
                  <MiniChart type={chart.type} data={chart.data} config={chart.config} />
                </div>
                {chart.snapshotDataUrl && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-[11px] text-muted-foreground">View captured snapshot</summary>
                    <div className="mt-2 h-40 rounded-md overflow-hidden border border-border/40 bg-background/40">
                      <img
                        src={chart.snapshotDataUrl}
                        alt={`${chart.title} snapshot`}
                        className="w-full h-full object-contain"
                        loading="lazy"
                      />
                    </div>
                  </details>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
