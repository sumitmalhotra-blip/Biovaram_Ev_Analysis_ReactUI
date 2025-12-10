"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Pin, Trash2, X } from "lucide-react"
import { useAnalysisStore, type PinnedChart } from "@/lib/store"
import { MiniChart } from "./mini-chart"

interface PinnedChartsProps {
  charts: PinnedChart[]
}

export function PinnedCharts({ charts }: PinnedChartsProps) {
  const { unpinChart, clearPinnedCharts } = useAnalysisStore()

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
                    <span className="text-xs text-muted-foreground">{chart.timestamp.toLocaleTimeString()}</span>
                  </div>
                </div>
                <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0" onClick={() => unpinChart(chart.id)}>
                  <X className="h-3 w-3" />
                </Button>
              </CardHeader>
              <CardContent className="pt-0">
                <MiniChart type={chart.type} data={chart.data} />
              </CardContent>
            </Card>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
