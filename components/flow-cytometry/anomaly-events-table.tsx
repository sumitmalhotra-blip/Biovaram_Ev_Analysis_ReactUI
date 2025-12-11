"use client"

import { useState, useMemo } from "react"
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Download, Search, ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export interface AnomalyEvent {
  index: number
  fsc: number
  ssc: number
  zscore_fsc?: number
  zscore_ssc?: number
  iqr_outlier_fsc?: boolean
  iqr_outlier_ssc?: boolean
  combined?: boolean
}

interface AnomalyEventsTableProps {
  events: AnomalyEvent[]
  onExport?: () => void
  maxHeight?: string
  className?: string
}

type SortField = "index" | "fsc" | "ssc" | "zscore_fsc" | "zscore_ssc"
type SortDirection = "asc" | "desc"

export function AnomalyEventsTable({
  events,
  onExport,
  maxHeight = "400px",
  className = "",
}: AnomalyEventsTableProps) {
  const [searchTerm, setSearchTerm] = useState("")
  const [sortField, setSortField] = useState<SortField>("index")
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc")

  // Filter and sort data
  const processedEvents = useMemo(() => {
    let filtered = events

    // Apply search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase()
      filtered = events.filter(
        (event) =>
          event.index.toString().includes(term) ||
          event.fsc.toString().includes(term) ||
          event.ssc.toString().includes(term)
      )
    }

    // Apply sorting
    const sorted = [...filtered].sort((a, b) => {
      const aVal = a[sortField] ?? 0
      const bVal = b[sortField] ?? 0

      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortDirection === "asc" ? aVal - bVal : bVal - aVal
      }

      return 0
    })

    return sorted
  }, [events, searchTerm, sortField, sortDirection])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc")
    } else {
      setSortField(field)
      setSortDirection("asc")
    }
  }

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <ArrowUpDown className="ml-1 h-3 w-3 text-muted-foreground" />
    }
    return sortDirection === "asc" ? (
      <ArrowUp className="ml-1 h-3 w-3" />
    ) : (
      <ArrowDown className="ml-1 h-3 w-3" />
    )
  }

  if (events.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-base">Anomalous Events</CardTitle>
          <CardDescription>No anomalous events detected</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">Anomalous Events</CardTitle>
            <CardDescription>
              {processedEvents.length} of {events.length} events shown
            </CardDescription>
          </div>
          {onExport && (
            <Button variant="outline" size="sm" onClick={onExport}>
              <Download className="mr-2 h-3 w-3" />
              Export CSV
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by index, FSC, or SSC..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-8"
          />
        </div>

        {/* Table */}
        <div className="rounded-lg border" style={{ maxHeight, overflowY: "auto" }}>
          <Table>
            <TableHeader className="sticky top-0 bg-background z-10">
              <TableRow>
                <TableHead className="w-24">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSort("index")}
                    className="h-8 px-2 font-semibold hover:bg-muted"
                  >
                    Index
                    <SortIcon field="index" />
                  </Button>
                </TableHead>
                <TableHead className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSort("fsc")}
                    className="h-8 px-2 font-semibold hover:bg-muted"
                  >
                    FSC-H
                    <SortIcon field="fsc" />
                  </Button>
                </TableHead>
                <TableHead className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSort("ssc")}
                    className="h-8 px-2 font-semibold hover:bg-muted"
                  >
                    SSC-H
                    <SortIcon field="ssc" />
                  </Button>
                </TableHead>
                <TableHead className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSort("zscore_fsc")}
                    className="h-8 px-2 font-semibold hover:bg-muted"
                  >
                    Z-Score (FSC)
                    <SortIcon field="zscore_fsc" />
                  </Button>
                </TableHead>
                <TableHead className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSort("zscore_ssc")}
                    className="h-8 px-2 font-semibold hover:bg-muted"
                  >
                    Z-Score (SSC)
                    <SortIcon field="zscore_ssc" />
                  </Button>
                </TableHead>
                <TableHead className="text-center w-32">Method</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {processedEvents.map((event) => {
                const methods = []
                if (event.zscore_fsc !== undefined || event.zscore_ssc !== undefined) {
                  methods.push("Z-Score")
                }
                if (event.iqr_outlier_fsc || event.iqr_outlier_ssc) {
                  methods.push("IQR")
                }
                if (event.combined) {
                  methods.push("Combined")
                }

                return (
                  <TableRow key={event.index} className="hover:bg-muted/50">
                    <TableCell className="font-mono text-xs">{event.index}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{event.fsc.toFixed(1)}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{event.ssc.toFixed(1)}</TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {event.zscore_fsc !== undefined ? (
                        <span className={Math.abs(event.zscore_fsc) > 3 ? "text-red-500 font-semibold" : ""}>
                          {event.zscore_fsc.toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {event.zscore_ssc !== undefined ? (
                        <span className={Math.abs(event.zscore_ssc) > 3 ? "text-red-500 font-semibold" : ""}>
                          {event.zscore_ssc.toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      <div className="flex flex-wrap gap-1 justify-center">
                        {methods.length > 0 ? (
                          methods.map((method) => (
                            <Badge key={method} variant="outline" className="text-xs px-1 h-5">
                              {method}
                            </Badge>
                          ))
                        ) : (
                          <span className="text-muted-foreground text-xs">—</span>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
            {processedEvents.length === 0 && (
              <TableCaption className="py-8">No events match your search criteria.</TableCaption>
            )}
          </Table>
        </div>

        {/* Footer Stats */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            Displaying {processedEvents.length} {processedEvents.length === 1 ? "event" : "events"}
          </span>
          {searchTerm && (
            <Button variant="ghost" size="sm" onClick={() => setSearchTerm("")} className="h-7 text-xs">
              Clear Search
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
