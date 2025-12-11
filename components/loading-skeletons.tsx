"use client"

import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

// Chart Skeleton - for any chart visualization
export function ChartSkeleton({ className }: { className?: string }) {
  return (
    <Card className={cn("card-3d", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-5 rounded" />
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-5 w-20 ml-auto" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Chart area */}
        <div className="h-[300px] md:h-[400px] flex items-end gap-2 p-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <Skeleton
              key={i}
              className="flex-1"
              style={{ height: `${Math.random() * 80 + 20}%` }}
            />
          ))}
        </div>
        {/* Legend */}
        <div className="flex gap-4 justify-center">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-24" />
        </div>
      </CardContent>
    </Card>
  )
}

// Statistics Card Skeleton
export function StatisticsCardSkeleton({ className }: { className?: string }) {
  return (
    <Card className={cn("card-3d", className)}>
      <CardContent className="p-6">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-5 rounded" />
            <Skeleton className="h-4 w-24" />
          </div>
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-3 w-full" />
        </div>
      </CardContent>
    </Card>
  )
}

// Statistics Cards Grid Skeleton
export function StatisticsCardsGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <StatisticsCardSkeleton key={i} />
      ))}
    </div>
  )
}

// Table Skeleton
export function TableSkeleton({ rows = 5, className }: { rows?: number; className?: string }) {
  return (
    <Card className={cn("card-3d", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-5 rounded" />
          <Skeleton className="h-5 w-32" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {/* Table header */}
          <div className="flex gap-4 pb-3 border-b">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-4 w-20" />
          </div>
          {/* Table rows */}
          {Array.from({ length: rows }).map((_, i) => (
            <div key={i} className="flex gap-4 py-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-4 w-20" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

// Analysis Results Skeleton (comprehensive)
export function AnalysisResultsSkeleton() {
  return (
    <div className="space-y-6">
      {/* Header skeleton */}
      <Card className="card-3d">
        <CardHeader>
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-2">
              <Skeleton className="h-6 w-48" />
              <div className="flex gap-2">
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-5 w-24" />
                <Skeleton className="h-5 w-28" />
              </div>
            </div>
            <Skeleton className="h-9 w-32" />
          </div>
        </CardHeader>
      </Card>

      {/* Statistics cards */}
      <StatisticsCardsGridSkeleton count={8} />

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>

      {/* Table */}
      <TableSkeleton rows={10} />
    </div>
  )
}

// Upload Zone Skeleton
export function UploadZoneSkeleton() {
  return (
    <Card className="card-3d">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-5 rounded" />
          <Skeleton className="h-5 w-32" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <Skeleton className="h-32 w-full rounded-xl" />
        <div className="grid grid-cols-2 gap-4">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      </CardContent>
    </Card>
  )
}

// Dashboard Skeleton
export function DashboardSkeleton() {
  return (
    <div className="p-4 md:p-6 space-y-6">
      {/* Quick stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <StatisticsCardSkeleton key={i} />
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>

      {/* Recent activity */}
      <TableSkeleton rows={5} />
    </div>
  )
}

// Scatter Plot Skeleton (specialized for FCS)
export function ScatterPlotSkeleton({ className }: { className?: string }) {
  return (
    <Card className={cn("card-3d", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-5 rounded" />
            <Skeleton className="h-5 w-40" />
          </div>
          <Skeleton className="h-8 w-8 rounded" />
        </div>
      </CardHeader>
      <CardContent>
        {/* Scatter plot area */}
        <div className="aspect-square max-h-[400px] bg-secondary/20 rounded-lg flex items-center justify-center">
          <div className="relative w-full h-full p-4">
            {/* Random scatter points */}
            {Array.from({ length: 50 }).map((_, i) => (
              <Skeleton
                key={i}
                className="absolute h-2 w-2 rounded-full"
                style={{
                  left: `${Math.random() * 90 + 5}%`,
                  top: `${Math.random() * 90 + 5}%`,
                }}
              />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// Generic Card Content Skeleton
export function CardContentSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className="h-4 w-full" style={{ width: `${100 - i * 10}%` }} />
      ))}
    </div>
  )
}
