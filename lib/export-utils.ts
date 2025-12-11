/**
 * Utility functions for exporting analysis data
 */

import type { AnomalyEvent } from "@/components/flow-cytometry/anomaly-events-table"
import type { AnomalyDetectionResult } from "@/components/flow-cytometry/anomaly-summary-card"

/**
 * Export anomaly events to CSV file
 */
export function exportAnomaliesToCSV(
  events: AnomalyEvent[],
  anomalyData: AnomalyDetectionResult,
  sampleId: string = "sample"
) {
  if (events.length === 0) {
    console.warn("No anomaly events to export")
    return
  }

  // CSV Header
  const headers = [
    "Event Index",
    "FSC-H",
    "SSC-H",
    "Z-Score (FSC)",
    "Z-Score (SSC)",
    "IQR Outlier (FSC)",
    "IQR Outlier (SSC)",
    "Detection Method",
  ]

  // CSV Rows
  const rows = events.map((event) => {
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

    return [
      event.index,
      event.fsc.toFixed(4),
      event.ssc.toFixed(4),
      event.zscore_fsc !== undefined ? event.zscore_fsc.toFixed(4) : "N/A",
      event.zscore_ssc !== undefined ? event.zscore_ssc.toFixed(4) : "N/A",
      event.iqr_outlier_fsc ? "Yes" : "No",
      event.iqr_outlier_ssc ? "Yes" : "No",
      methods.join("; "),
    ]
  })

  // Create CSV content
  const csvContent = [
    // Metadata
    `# Anomaly Detection Export`,
    `# Sample ID: ${sampleId}`,
    `# Export Date: ${new Date().toISOString()}`,
    `# Detection Method: ${anomalyData.method}`,
    `# Total Anomalies: ${anomalyData.total_anomalies}`,
    `# Anomaly Percentage: ${anomalyData.anomaly_percentage.toFixed(2)}%`,
    anomalyData.zscore_threshold ? `# Z-Score Threshold: ${anomalyData.zscore_threshold}` : null,
    anomalyData.iqr_factor ? `# IQR Factor: ${anomalyData.iqr_factor}` : null,
    `#`,
    // Data
    headers.join(","),
    ...rows.map((row) => row.join(",")),
  ]
    .filter(Boolean)
    .join("\n")

  // Download file
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
  const link = document.createElement("a")
  const url = URL.createObjectURL(blob)

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, -5)
  link.setAttribute("href", url)
  link.setAttribute("download", `${sampleId}_anomalies_${timestamp}.csv`)
  link.style.visibility = "hidden"

  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Export size distribution data to CSV
 */
export function exportSizeDistributionToCSV(
  data: Array<{ size: number; count: number }>,
  sampleId: string = "sample",
  analysisType: "FCS" | "NTA" = "FCS"
) {
  if (data.length === 0) {
    console.warn("No size distribution data to export")
    return
  }

  // CSV Header
  const headers = ["Size (nm)", "Count"]

  // CSV Rows
  const rows = data.map((point) => [point.size.toFixed(2), point.count])

  // Create CSV content
  const csvContent = [
    `# Size Distribution Export (${analysisType})`,
    `# Sample ID: ${sampleId}`,
    `# Export Date: ${new Date().toISOString()}`,
    `# Total Data Points: ${data.length}`,
    `#`,
    headers.join(","),
    ...rows.map((row) => row.join(",")),
  ].join("\n")

  // Download file
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
  const link = document.createElement("a")
  const url = URL.createObjectURL(blob)

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, -5)
  link.setAttribute("href", url)
  link.setAttribute("download", `${sampleId}_size_distribution_${analysisType}_${timestamp}.csv`)
  link.style.visibility = "hidden"

  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Export scatter plot data to CSV
 */
export function exportScatterDataToCSV(
  data: Array<{ x: number; y: number; index?: number; isAnomaly?: boolean }>,
  sampleId: string = "sample",
  xLabel: string = "FSC-H",
  yLabel: string = "SSC-H"
) {
  if (data.length === 0) {
    console.warn("No scatter data to export")
    return
  }

  // CSV Header
  const headers = ["Event Index", xLabel, yLabel, "Is Anomaly"]

  // CSV Rows
  const rows = data.map((point, idx) => [
    point.index ?? idx,
    point.x.toFixed(4),
    point.y.toFixed(4),
    point.isAnomaly ? "Yes" : "No",
  ])

  // Create CSV content
  const csvContent = [
    `# Scatter Plot Data Export`,
    `# Sample ID: ${sampleId}`,
    `# Export Date: ${new Date().toISOString()}`,
    `# Total Events: ${data.length}`,
    `# X-Axis: ${xLabel}`,
    `# Y-Axis: ${yLabel}`,
    `#`,
    headers.join(","),
    ...rows.map((row) => row.join(",")),
  ].join("\n")

  // Download file
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
  const link = document.createElement("a")
  const url = URL.createObjectURL(blob)

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, -5)
  link.setAttribute("href", url)
  link.setAttribute("download", `${sampleId}_scatter_data_${timestamp}.csv`)
  link.style.visibility = "hidden"

  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 Bytes"

  const k = 1024
  const sizes = ["Bytes", "KB", "MB", "GB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i]
}

/**
 * Validate CSV export filename
 */
export function sanitizeFilename(filename: string): string {
  return filename.replace(/[^a-z0-9_-]/gi, "_").toLowerCase()
}
