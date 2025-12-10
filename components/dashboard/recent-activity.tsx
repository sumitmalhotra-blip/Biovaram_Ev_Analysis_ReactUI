"use client"

import { useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useAnalysisStore } from "@/lib/store"
import { Clock, FileUp, BarChart3, AlertTriangle, FlaskConical, Microscope, CheckCircle } from "lucide-react"
import { formatDistanceToNow } from "date-fns"

interface Activity {
  id: string
  type: "upload" | "analysis" | "warning" | "job"
  message: string
  time: string
  icon: typeof FileUp
}

export function RecentActivity() {
  const { apiSamples, processingJobs, fcsAnalysis, ntaAnalysis } = useAnalysisStore()

  const activities = useMemo(() => {
    const items: Activity[] = []

    // Add activities from API samples
    apiSamples.slice(0, 3).forEach((sample, index) => {
      if (sample.files?.fcs) {
        items.push({
          id: `fcs-${sample.id}`,
          type: "upload",
          message: `${sample.sample_id} (FCS) uploaded`,
          time: sample.created_at 
            ? formatDistanceToNow(new Date(sample.created_at), { addSuffix: true })
            : `${(index + 1) * 5} minutes ago`,
          icon: FlaskConical,
        })
      }
      if (sample.files?.nta) {
        items.push({
          id: `nta-${sample.id}`,
          type: "upload",
          message: `${sample.sample_id} (NTA) uploaded`,
          time: sample.created_at 
            ? formatDistanceToNow(new Date(sample.created_at), { addSuffix: true })
            : `${(index + 1) * 5} minutes ago`,
          icon: Microscope,
        })
      }
    })

    // Add FCS analysis activity
    if (fcsAnalysis.results) {
      items.push({
        id: "fcs-analysis",
        type: "analysis",
        message: `FCS analysis completed - ${fcsAnalysis.results.total_events?.toLocaleString() || 'N/A'} events`,
        time: "Recently",
        icon: BarChart3,
      })
    }

    // Add NTA analysis activity
    if (ntaAnalysis.results) {
      items.push({
        id: "nta-analysis",
        type: "analysis",
        message: `NTA analysis completed - ${ntaAnalysis.results.total_particles?.toLocaleString() || 'N/A'} particles`,
        time: "Recently",
        icon: BarChart3,
      })
    }

    // Add processing jobs
    processingJobs.slice(0, 2).forEach(job => {
      items.push({
        id: job.id,
        type: "job",
        message: `Job ${job.status}: ${job.sample_id}`,
        time: job.created_at 
          ? formatDistanceToNow(new Date(job.created_at), { addSuffix: true })
          : "Recently",
        icon: job.status === "completed" ? CheckCircle : job.status === "failed" ? AlertTriangle : FileUp,
      })
    })

    // Default activities if no real data
    if (items.length === 0) {
      return [
        {
          id: "demo-1",
          type: "upload" as const,
          message: "No recent activity",
          time: "Upload a file to get started",
          icon: FileUp,
        },
      ]
    }

    return items.slice(0, 5)
  }, [apiSamples, processingJobs, fcsAnalysis.results, ntaAnalysis.results])

  return (
    <Card className="card-3d">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-primary/10">
            <Clock className="h-4 w-4 text-primary" />
          </div>
          <CardTitle className="text-base md:text-lg">Recent Activity</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3 md:space-y-4">
          {activities.map((activity) => {
            const Icon = activity.icon
            return (
              <div
                key={activity.id}
                className="flex items-start gap-3 p-2 rounded-lg hover:bg-secondary/30 transition-colors"
              >
                <div
                  className={`p-1.5 rounded-lg shadow-sm ${
                    activity.type === "warning"
                      ? "bg-amber/20 text-amber"
                      : activity.type === "analysis"
                        ? "bg-emerald/20 text-emerald"
                        : activity.type === "job"
                          ? "bg-cyan/20 text-cyan"
                          : "bg-primary/20 text-primary"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm truncate">{activity.message}</p>
                  <p className="text-xs text-muted-foreground">{activity.time}</p>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
