/**
 * Utility functions for exporting analysis data
 * Includes Excel (XLSX), PDF, CSV, JSON, Markdown exports
 */

import type { AnomalyEvent } from "@/components/flow-cytometry/anomaly-events-table"
import type { AnomalyDetectionResult } from "@/components/flow-cytometry/anomaly-summary-card"
import * as XLSX from 'xlsx'

// =====================================================
// TYPE DEFINITIONS
// =====================================================

export interface FCSExportData {
  sampleId: string
  fileName?: string
  results: {
    total_events?: number
    gated_events?: number
    fsc_mean?: number
    fsc_median?: number
    ssc_mean?: number
    ssc_median?: number
    particle_size_median_nm?: number
    particle_size_mean_nm?: number
    size_statistics?: {
      d10?: number
      d50?: number
      d90?: number
      mean?: number
      std?: number
    }
    fsc_cv_pct?: number
    ssc_cv_pct?: number
    debris_pct?: number
    noise_events_removed?: number
    channels?: string[]
  }
  scatterData?: Array<{ x: number; y: number; index?: number; isAnomaly?: boolean }>
  sizeDistribution?: Array<{ size: number; count: number }>
  anomalyData?: AnomalyDetectionResult
  experimentalConditions?: {
    treatment?: string
    cellLine?: string
    bufferType?: string
    dilutionFactor?: number
    notes?: string
  }
}

export interface NTAExportData {
  sampleId: string
  fileName?: string
  results: {
    median_size_nm?: number
    mean_size_nm?: number
    d10_nm?: number
    d50_nm?: number
    d90_nm?: number
    concentration_particles_ml?: number
    temperature_celsius?: number
    ph?: number
    total_particles?: number
    bin_50_80nm_pct?: number
    bin_80_100nm_pct?: number
    bin_100_120nm_pct?: number
    bin_120_150nm_pct?: number
    bin_150_200nm_pct?: number
    bin_200_plus_pct?: number
  }
  sizeDistribution?: Array<{ size: number; concentration: number }>
}

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

/**
 * Export data to Parquet format via backend API
 */
export async function exportToParquet(
  sampleId: string,
  dataType: "fcs" | "nta",
  options?: {
    includeMetadata?: boolean;
    includeStatistics?: boolean;
    onSuccess?: (filename: string) => void;
    onError?: (error: string) => void;
  }
): Promise<boolean> {
  try {
    const { apiClient } = await import("./api-client");
    
    await apiClient.downloadParquet(sampleId, dataType, {
      includeMetadata: options?.includeMetadata ?? true,
      includeStatistics: options?.includeStatistics ?? true,
    });
    
    options?.onSuccess?.(`${sampleId}_${dataType}_export.parquet`);
    return true;
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("Parquet export failed:", errorMessage);
    options?.onError?.(errorMessage);
    return false;
  }
}

/**
 * Generate a markdown report from analysis results
 */
export function generateMarkdownReport(
  reportData: {
    title: string;
    sampleId: string;
    analysisType: "FCS" | "NTA";
    timestamp: Date;
    results: Record<string, unknown>;
    statistics?: Record<string, number | string>;
    charts?: Array<{ title: string; description: string }>;
    notes?: string;
  }
): string {
  const { title, sampleId, analysisType, timestamp, results, statistics, charts, notes } = reportData;
  
  const sections: string[] = [
    `# ${title}`,
    "",
    `**Sample ID:** ${sampleId}`,
    `**Analysis Type:** ${analysisType}`,
    `**Generated:** ${timestamp.toLocaleString()}`,
    "",
    "---",
    "",
    "## Summary",
    "",
  ];
  
  // Add results section
  if (results) {
    sections.push("### Analysis Results");
    sections.push("");
    sections.push("| Parameter | Value |");
    sections.push("|-----------|-------|");
    
    for (const [key, value] of Object.entries(results)) {
      if (value !== null && value !== undefined) {
        const formattedKey = key.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
        let formattedValue = String(value);
        if (typeof value === "number") {
          formattedValue = value.toLocaleString(undefined, { maximumFractionDigits: 4 });
        }
        sections.push(`| ${formattedKey} | ${formattedValue} |`);
      }
    }
    sections.push("");
  }
  
  // Add statistics section
  if (statistics && Object.keys(statistics).length > 0) {
    sections.push("### Statistics");
    sections.push("");
    sections.push("| Metric | Value |");
    sections.push("|--------|-------|");
    
    for (const [key, value] of Object.entries(statistics)) {
      const formattedKey = key.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
      let formattedValue = String(value);
      if (typeof value === "number") {
        formattedValue = value.toLocaleString(undefined, { maximumFractionDigits: 4 });
      }
      sections.push(`| ${formattedKey} | ${formattedValue} |`);
    }
    sections.push("");
  }
  
  // Add charts section
  if (charts && charts.length > 0) {
    sections.push("### Visualizations");
    sections.push("");
    charts.forEach((chart, index) => {
      sections.push(`${index + 1}. **${chart.title}**: ${chart.description}`);
    });
    sections.push("");
  }
  
  // Add notes section
  if (notes) {
    sections.push("### Notes");
    sections.push("");
    sections.push(notes);
    sections.push("");
  }
  
  // Add footer
  sections.push("---");
  sections.push("");
  sections.push(`*Report generated by BioVaram EV Analysis Platform*`);
  sections.push(`*${new Date().toISOString()}*`);
  
  return sections.join("\n");
}

/**
 * Download markdown report as a file
 */
export function downloadMarkdownReport(
  content: string,
  filename: string = "analysis_report.md"
): void {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8;" });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  
  link.setAttribute("href", url);
  link.setAttribute("download", filename);
  link.style.visibility = "hidden";
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// =====================================================
// CHAT HISTORY EXPORT FUNCTIONS
// =====================================================

/**
 * Chat message interface for export
 */
export interface ChatMessageForExport {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: Date;
  parts?: Array<{ type: string; text?: string }>;
}

/**
 * Chat export metadata
 */
export interface ChatExportMetadata {
  exportDate: string;
  source: string;
  totalMessages: number;
  duration?: string;
  context?: Record<string, any>;
}

/**
 * Export chat history to JSON format
 */
export function exportChatToJSON(
  messages: ChatMessageForExport[],
  source: string = "Research Chat",
  metadata?: Record<string, any>
): string {
  const exportData = {
    metadata: {
      exportDate: new Date().toISOString(),
      source,
      totalMessages: messages.length,
      platform: "BioVaram EV Analysis Platform",
      ...metadata,
    },
    messages: messages.map((msg, index) => ({
      id: msg.id || `msg-${index}`,
      role: msg.role,
      content: extractMessageContent(msg),
      timestamp: msg.timestamp?.toISOString() || new Date().toISOString(),
    })),
  };

  return JSON.stringify(exportData, null, 2);
}

/**
 * Export chat history to plain text format
 */
export function exportChatToText(
  messages: ChatMessageForExport[],
  source: string = "Research Chat"
): string {
  const lines: string[] = [];
  
  // Header
  lines.push("=" .repeat(60));
  lines.push(`BioVaram EV Analysis Platform - Chat Export`);
  lines.push(`Source: ${source}`);
  lines.push(`Export Date: ${new Date().toLocaleString()}`);
  lines.push(`Total Messages: ${messages.length}`);
  lines.push("=".repeat(60));
  lines.push("");

  // Messages
  messages.forEach((msg, index) => {
    const role = msg.role === "user" ? "You" : msg.role === "assistant" ? "AI Assistant" : "System";
    const content = extractMessageContent(msg);
    
    lines.push(`[${index + 1}] ${role}:`);
    lines.push("-".repeat(40));
    lines.push(content);
    lines.push("");
  });

  // Footer
  lines.push("=".repeat(60));
  lines.push("End of Chat Export");
  lines.push("=".repeat(60));

  return lines.join("\n");
}

/**
 * Export chat history to Markdown format
 */
export function exportChatToMarkdown(
  messages: ChatMessageForExport[],
  source: string = "Research Chat",
  metadata?: Record<string, any>
): string {
  const lines: string[] = [];

  // Header
  lines.push("# Chat History Export");
  lines.push("");
  lines.push(`**Source:** ${source}`);
  lines.push(`**Export Date:** ${new Date().toLocaleString()}`);
  lines.push(`**Total Messages:** ${messages.length}`);
  
  if (metadata) {
    lines.push("");
    lines.push("## Session Context");
    lines.push("");
    for (const [key, value] of Object.entries(metadata)) {
      lines.push(`- **${key}:** ${value}`);
    }
  }
  
  lines.push("");
  lines.push("---");
  lines.push("");
  lines.push("## Conversation");
  lines.push("");

  // Messages
  messages.forEach((msg) => {
    const role = msg.role === "user" ? "👤 **You**" : msg.role === "assistant" ? "🤖 **AI Assistant**" : "⚙️ **System**";
    const content = extractMessageContent(msg);
    
    lines.push(`### ${role}`);
    lines.push("");
    lines.push(content);
    lines.push("");
  });

  // Footer
  lines.push("---");
  lines.push("");
  lines.push("*Exported from BioVaram EV Analysis Platform*");

  return lines.join("\n");
}

/**
 * Extract content from message (handles different message formats)
 */
function extractMessageContent(msg: ChatMessageForExport): string {
  // If parts exist, extract text from them
  if (msg.parts && msg.parts.length > 0) {
    return msg.parts
      .filter(part => part.type === "text" && part.text)
      .map(part => part.text)
      .join("\n");
  }
  
  // Otherwise use content directly
  return msg.content || "";
}

/**
 * Download chat history as a file
 */
export function downloadChatHistory(
  messages: ChatMessageForExport[],
  format: "json" | "txt" | "md" = "md",
  source: string = "Research Chat",
  metadata?: Record<string, any>
): void {
  let content: string;
  let mimeType: string;
  let extension: string;

  switch (format) {
    case "json":
      content = exportChatToJSON(messages, source, metadata);
      mimeType = "application/json";
      extension = "json";
      break;
    case "txt":
      content = exportChatToText(messages, source);
      mimeType = "text/plain";
      extension = "txt";
      break;
    case "md":
    default:
      content = exportChatToMarkdown(messages, source, metadata);
      mimeType = "text/markdown";
      extension = "md";
      break;
  }

  const blob = new Blob([content], { type: `${mimeType};charset=utf-8;` });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, -5);
  const filename = `chat_export_${source.toLowerCase().replace(/\s+/g, "_")}_${timestamp}.${extension}`;
  
  link.setAttribute("href", url);
  link.setAttribute("download", filename);
  link.style.visibility = "hidden";
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// =====================================================
// EXCEL EXPORT FUNCTIONS (P-002)
// =====================================================

/**
 * Export FCS analysis results to proper Excel format (.xlsx)
 * Includes multiple sheets: Summary, Statistics, Raw Data, Anomalies
 */
export function exportFCSToExcel(data: FCSExportData): void {
  const workbook = XLSX.utils.book_new()
  const timestamp = new Date().toISOString().split('T')[0]
  
  // Sheet 1: Summary
  const summaryData = [
    ['BioVaram EV Analysis Platform - FCS Report'],
    [''],
    ['Sample Information'],
    ['Sample ID', data.sampleId],
    ['File Name', data.fileName || 'N/A'],
    ['Export Date', new Date().toLocaleString()],
    [''],
    ['Analysis Summary'],
    ['Total Events', data.results.total_events || 'N/A'],
    ['Gated Events', data.results.gated_events || 'N/A'],
    ['Debris %', data.results.debris_pct ? `${data.results.debris_pct.toFixed(2)}%` : 'N/A'],
    [''],
    ['Particle Size'],
    ['Median Size (nm)', data.results.particle_size_median_nm?.toFixed(2) || 'N/A'],
    ['Mean Size (nm)', data.results.particle_size_mean_nm?.toFixed(2) || 'N/A'],
    ['D10 (nm)', data.results.size_statistics?.d10?.toFixed(2) || 'N/A'],
    ['D50 (nm)', data.results.size_statistics?.d50?.toFixed(2) || 'N/A'],
    ['D90 (nm)', data.results.size_statistics?.d90?.toFixed(2) || 'N/A'],
    [''],
    ['Scatter Statistics'],
    ['FSC Mean', data.results.fsc_mean?.toFixed(2) || 'N/A'],
    ['FSC Median', data.results.fsc_median?.toFixed(2) || 'N/A'],
    ['FSC CV%', data.results.fsc_cv_pct ? `${data.results.fsc_cv_pct.toFixed(2)}%` : 'N/A'],
    ['SSC Mean', data.results.ssc_mean?.toFixed(2) || 'N/A'],
    ['SSC Median', data.results.ssc_median?.toFixed(2) || 'N/A'],
    ['SSC CV%', data.results.ssc_cv_pct ? `${data.results.ssc_cv_pct.toFixed(2)}%` : 'N/A'],
  ]
  
  // Add experimental conditions if present
  if (data.experimentalConditions) {
    summaryData.push([''])
    summaryData.push(['Experimental Conditions'])
    if (data.experimentalConditions.treatment) {
      summaryData.push(['Treatment', data.experimentalConditions.treatment])
    }
    if (data.experimentalConditions.cellLine) {
      summaryData.push(['Cell Line', data.experimentalConditions.cellLine])
    }
    if (data.experimentalConditions.bufferType) {
      summaryData.push(['Buffer Type', data.experimentalConditions.bufferType])
    }
    if (data.experimentalConditions.dilutionFactor) {
      summaryData.push(['Dilution Factor', `${data.experimentalConditions.dilutionFactor}x`])
    }
    if (data.experimentalConditions.notes) {
      summaryData.push(['Notes', data.experimentalConditions.notes])
    }
  }
  
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryData)
  
  // Style the summary sheet
  summarySheet['!cols'] = [{ wch: 25 }, { wch: 30 }]
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Summary')
  
  // Sheet 2: Size Distribution (if available)
  if (data.sizeDistribution && data.sizeDistribution.length > 0) {
    const sizeData = [
      ['Size Distribution'],
      ['Size (nm)', 'Count'],
      ...data.sizeDistribution.map(d => [d.size, d.count])
    ]
    const sizeSheet = XLSX.utils.aoa_to_sheet(sizeData)
    sizeSheet['!cols'] = [{ wch: 15 }, { wch: 15 }]
    XLSX.utils.book_append_sheet(workbook, sizeSheet, 'Size Distribution')
  }
  
  // Sheet 3: Scatter Data (if available, limited to first 10000 rows for performance)
  if (data.scatterData && data.scatterData.length > 0) {
    const maxRows = Math.min(data.scatterData.length, 10000)
    const scatterExport = data.scatterData.slice(0, maxRows)
    const scatterRows = [
      ['Scatter Plot Data'],
      ['Event Index', 'FSC-H', 'SSC-H', 'Is Anomaly'],
      ...scatterExport.map((d, i) => [
        d.index ?? i,
        d.x.toFixed(4),
        d.y.toFixed(4),
        d.isAnomaly ? 'Yes' : 'No'
      ])
    ]
    const scatterSheet = XLSX.utils.aoa_to_sheet(scatterRows)
    scatterSheet['!cols'] = [{ wch: 12 }, { wch: 15 }, { wch: 15 }, { wch: 12 }]
    XLSX.utils.book_append_sheet(workbook, scatterSheet, 'Scatter Data')
    
    if (data.scatterData.length > maxRows) {
      console.log(`Note: Scatter data truncated to ${maxRows} rows for Excel export`)
    }
  }
  
  // Sheet 4: Anomaly Summary (if available)
  if (data.anomalyData) {
    const anomalyRows = [
      ['Anomaly Detection Results'],
      [''],
      ['Detection Method', data.anomalyData.method],
      ['Total Anomalies', data.anomalyData.total_anomalies],
      ['Anomaly Percentage', `${data.anomalyData.anomaly_percentage.toFixed(2)}%`],
      ['Z-Score Threshold', data.anomalyData.zscore_threshold || 'N/A'],
      ['IQR Factor', data.anomalyData.iqr_factor || 'N/A'],
    ]
    const anomalySheet = XLSX.utils.aoa_to_sheet(anomalyRows)
    anomalySheet['!cols'] = [{ wch: 20 }, { wch: 20 }]
    XLSX.utils.book_append_sheet(workbook, anomalySheet, 'Anomalies')
  }
  
  // Generate filename and download
  const filename = `${data.sampleId}_FCS_Report_${timestamp}.xlsx`
  XLSX.writeFile(workbook, filename)
}

/**
 * Export NTA analysis results to proper Excel format (.xlsx)
 */
export function exportNTAToExcel(data: NTAExportData): void {
  const workbook = XLSX.utils.book_new()
  const timestamp = new Date().toISOString().split('T')[0]
  
  // Sheet 1: Summary
  const summaryData = [
    ['BioVaram EV Analysis Platform - NTA Report'],
    [''],
    ['Sample Information'],
    ['Sample ID', data.sampleId],
    ['File Name', data.fileName || 'N/A'],
    ['Export Date', new Date().toLocaleString()],
    [''],
    ['Size Analysis'],
    ['Median Size (nm)', data.results.median_size_nm?.toFixed(2) || 'N/A'],
    ['Mean Size (nm)', data.results.mean_size_nm?.toFixed(2) || 'N/A'],
    ['D10 (nm)', data.results.d10_nm?.toFixed(2) || 'N/A'],
    ['D50 (nm)', data.results.d50_nm?.toFixed(2) || 'N/A'],
    ['D90 (nm)', data.results.d90_nm?.toFixed(2) || 'N/A'],
    [''],
    ['Concentration'],
    ['Particles/mL', data.results.concentration_particles_ml?.toExponential(2) || 'N/A'],
    ['Total Particles', data.results.total_particles || 'N/A'],
    [''],
    ['Measurement Conditions'],
    ['Temperature (°C)', data.results.temperature_celsius?.toFixed(1) || 'N/A'],
    ['pH', data.results.ph?.toFixed(2) || 'N/A'],
    [''],
    ['Size Distribution Bins'],
    ['50-80nm', data.results.bin_50_80nm_pct ? `${data.results.bin_50_80nm_pct.toFixed(2)}%` : 'N/A'],
    ['80-100nm', data.results.bin_80_100nm_pct ? `${data.results.bin_80_100nm_pct.toFixed(2)}%` : 'N/A'],
    ['100-120nm', data.results.bin_100_120nm_pct ? `${data.results.bin_100_120nm_pct.toFixed(2)}%` : 'N/A'],
    ['120-150nm', data.results.bin_120_150nm_pct ? `${data.results.bin_120_150nm_pct.toFixed(2)}%` : 'N/A'],
    ['150-200nm', data.results.bin_150_200nm_pct ? `${data.results.bin_150_200nm_pct.toFixed(2)}%` : 'N/A'],
    ['200+nm', data.results.bin_200_plus_pct ? `${data.results.bin_200_plus_pct.toFixed(2)}%` : 'N/A'],
  ]
  
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryData)
  summarySheet['!cols'] = [{ wch: 25 }, { wch: 30 }]
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Summary')
  
  // Sheet 2: Size Distribution (if available)
  if (data.sizeDistribution && data.sizeDistribution.length > 0) {
    const sizeRows = [
      ['Size Distribution'],
      ['Size (nm)', 'Concentration'],
      ...data.sizeDistribution.map(d => [d.size, d.concentration])
    ]
    const sizeSheet = XLSX.utils.aoa_to_sheet(sizeRows)
    sizeSheet['!cols'] = [{ wch: 15 }, { wch: 20 }]
    XLSX.utils.book_append_sheet(workbook, sizeSheet, 'Size Distribution')
  }
  
  // Generate filename and download
  const filename = `${data.sampleId}_NTA_Report_${timestamp}.xlsx`
  XLSX.writeFile(workbook, filename)
}

/**
 * Export comparison data to Excel
 */
export function exportComparisonToExcel(
  primaryData: FCSExportData | NTAExportData,
  secondaryData: FCSExportData | NTAExportData,
  comparisonType: 'FCS' | 'NTA' | 'Cross'
): void {
  const workbook = XLSX.utils.book_new()
  const timestamp = new Date().toISOString().split('T')[0]
  
  // Sheet 1: Comparison Summary
  const summaryData = [
    ['BioVaram EV Analysis Platform - Comparison Report'],
    [''],
    ['Comparison Type', comparisonType],
    ['Export Date', new Date().toLocaleString()],
    [''],
    ['Samples Compared'],
    ['Primary Sample', primaryData.sampleId],
    ['Secondary Sample', secondaryData.sampleId],
    [''],
    ['Side-by-Side Comparison'],
    ['Metric', 'Primary', 'Secondary', 'Difference'],
  ]
  
  // Add comparison metrics based on type
  if ('fsc_mean' in primaryData.results && 'fsc_mean' in secondaryData.results) {
    // FCS comparison
    const p = primaryData.results as FCSExportData['results']
    const s = secondaryData.results as FCSExportData['results']
    
    if (p.total_events && s.total_events) {
      summaryData.push(['Total Events', String(p.total_events), String(s.total_events), String(s.total_events - p.total_events)])
    }
    if (p.particle_size_median_nm && s.particle_size_median_nm) {
      summaryData.push([
        'Median Size (nm)',
        p.particle_size_median_nm.toFixed(2),
        s.particle_size_median_nm.toFixed(2),
        (s.particle_size_median_nm - p.particle_size_median_nm).toFixed(2)
      ])
    }
    if (p.fsc_mean && s.fsc_mean) {
      summaryData.push([
        'FSC Mean',
        p.fsc_mean.toFixed(2),
        s.fsc_mean.toFixed(2),
        (s.fsc_mean - p.fsc_mean).toFixed(2)
      ])
    }
    if (p.ssc_mean && s.ssc_mean) {
      summaryData.push([
        'SSC Mean',
        p.ssc_mean.toFixed(2),
        s.ssc_mean.toFixed(2),
        (s.ssc_mean - p.ssc_mean).toFixed(2)
      ])
    }
  }
  
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryData)
  summarySheet['!cols'] = [{ wch: 20 }, { wch: 15 }, { wch: 15 }, { wch: 15 }]
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Comparison')
  
  const filename = `Comparison_${primaryData.sampleId}_vs_${secondaryData.sampleId}_${timestamp}.xlsx`
  XLSX.writeFile(workbook, filename)
}

// =====================================================
// PDF EXPORT FUNCTIONS (P-003)
// =====================================================

/**
 * Generate PDF report for FCS analysis
 * Uses jsPDF with autoTable for professional reports
 */
export async function exportFCSToPDF(data: FCSExportData): Promise<void> {
  // Dynamic import to avoid SSR issues
  const { default: jsPDF } = await import('jspdf')
  const { default: autoTable } = await import('jspdf-autotable')
  
  const doc = new jsPDF()
  const timestamp = new Date().toLocaleString()
  const pageWidth = doc.internal.pageSize.getWidth()
  
  // Header
  doc.setFontSize(20)
  doc.setTextColor(139, 92, 246) // Purple color
  doc.text('BioVaram', 14, 20)
  
  doc.setFontSize(12)
  doc.setTextColor(100)
  doc.text('EV Analysis Platform - FCS Report', 14, 28)
  
  // Title line
  doc.setDrawColor(139, 92, 246)
  doc.setLineWidth(0.5)
  doc.line(14, 32, pageWidth - 14, 32)
  
  // Sample Information
  doc.setFontSize(14)
  doc.setTextColor(0)
  doc.text('Sample Information', 14, 42)
  
  autoTable(doc, {
    startY: 46,
    head: [['Property', 'Value']],
    body: [
      ['Sample ID', data.sampleId],
      ['File Name', data.fileName || 'N/A'],
      ['Export Date', timestamp],
      ['Total Events', String(data.results.total_events || 'N/A')],
      ['Gated Events', String(data.results.gated_events || 'N/A')],
    ],
    theme: 'striped',
    headStyles: { fillColor: [139, 92, 246] },
    margin: { left: 14, right: 14 },
  })
  
  // Size Statistics
  const sizeStartY = (doc as any).lastAutoTable.finalY + 10
  doc.setFontSize(14)
  doc.text('Particle Size Statistics', 14, sizeStartY)
  
  autoTable(doc, {
    startY: sizeStartY + 4,
    head: [['Metric', 'Value']],
    body: [
      ['Median Size (nm)', data.results.particle_size_median_nm?.toFixed(2) || 'N/A'],
      ['Mean Size (nm)', data.results.particle_size_mean_nm?.toFixed(2) || 'N/A'],
      ['D10 (nm)', data.results.size_statistics?.d10?.toFixed(2) || 'N/A'],
      ['D50 (nm)', data.results.size_statistics?.d50?.toFixed(2) || 'N/A'],
      ['D90 (nm)', data.results.size_statistics?.d90?.toFixed(2) || 'N/A'],
    ],
    theme: 'striped',
    headStyles: { fillColor: [139, 92, 246] },
    margin: { left: 14, right: 14 },
  })
  
  // Scatter Statistics
  const scatterStartY = (doc as any).lastAutoTable.finalY + 10
  doc.setFontSize(14)
  doc.text('Scatter Statistics', 14, scatterStartY)
  
  autoTable(doc, {
    startY: scatterStartY + 4,
    head: [['Parameter', 'Mean', 'Median', 'CV%']],
    body: [
      [
        'FSC',
        data.results.fsc_mean?.toFixed(2) || 'N/A',
        data.results.fsc_median?.toFixed(2) || 'N/A',
        data.results.fsc_cv_pct ? `${data.results.fsc_cv_pct.toFixed(2)}%` : 'N/A'
      ],
      [
        'SSC',
        data.results.ssc_mean?.toFixed(2) || 'N/A',
        data.results.ssc_median?.toFixed(2) || 'N/A',
        data.results.ssc_cv_pct ? `${data.results.ssc_cv_pct.toFixed(2)}%` : 'N/A'
      ],
    ],
    theme: 'striped',
    headStyles: { fillColor: [139, 92, 246] },
    margin: { left: 14, right: 14 },
  })
  
  // Anomaly Detection (if available)
  if (data.anomalyData) {
    const anomalyStartY = (doc as any).lastAutoTable.finalY + 10
    doc.setFontSize(14)
    doc.text('Anomaly Detection', 14, anomalyStartY)
    
    autoTable(doc, {
      startY: anomalyStartY + 4,
      head: [['Property', 'Value']],
      body: [
        ['Detection Method', data.anomalyData.method],
        ['Total Anomalies', String(data.anomalyData.total_anomalies)],
        ['Anomaly %', `${data.anomalyData.anomaly_percentage.toFixed(2)}%`],
        ['Z-Score Threshold', String(data.anomalyData.zscore_threshold || 'N/A')],
      ],
      theme: 'striped',
      headStyles: { fillColor: [249, 115, 22] }, // Orange for anomalies
      margin: { left: 14, right: 14 },
    })
  }
  
  // Experimental Conditions (if available)
  if (data.experimentalConditions) {
    const condStartY = (doc as any).lastAutoTable.finalY + 10
    doc.setFontSize(14)
    doc.text('Experimental Conditions', 14, condStartY)
    
    const condBody: string[][] = []
    if (data.experimentalConditions.treatment) {
      condBody.push(['Treatment', data.experimentalConditions.treatment])
    }
    if (data.experimentalConditions.cellLine) {
      condBody.push(['Cell Line', data.experimentalConditions.cellLine])
    }
    if (data.experimentalConditions.bufferType) {
      condBody.push(['Buffer Type', data.experimentalConditions.bufferType])
    }
    if (data.experimentalConditions.dilutionFactor) {
      condBody.push(['Dilution Factor', `${data.experimentalConditions.dilutionFactor}x`])
    }
    
    if (condBody.length > 0) {
      autoTable(doc, {
        startY: condStartY + 4,
        head: [['Condition', 'Value']],
        body: condBody,
        theme: 'striped',
        headStyles: { fillColor: [16, 185, 129] }, // Green
        margin: { left: 14, right: 14 },
      })
    }
  }
  
  // Footer
  const pageCount = doc.getNumberOfPages()
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i)
    doc.setFontSize(8)
    doc.setTextColor(150)
    doc.text(
      `Page ${i} of ${pageCount} | Generated by BioVaram EV Analysis Platform | ${timestamp}`,
      pageWidth / 2,
      doc.internal.pageSize.getHeight() - 10,
      { align: 'center' }
    )
  }
  
  // Save
  const filename = `${data.sampleId}_FCS_Report_${new Date().toISOString().split('T')[0]}.pdf`
  doc.save(filename)
}

/**
 * Generate PDF report for NTA analysis
 */
export async function exportNTAToPDF(data: NTAExportData): Promise<void> {
  const { default: jsPDF } = await import('jspdf')
  const { default: autoTable } = await import('jspdf-autotable')
  
  const doc = new jsPDF()
  const timestamp = new Date().toLocaleString()
  const pageWidth = doc.internal.pageSize.getWidth()
  
  // Header
  doc.setFontSize(20)
  doc.setTextColor(139, 92, 246)
  doc.text('BioVaram', 14, 20)
  
  doc.setFontSize(12)
  doc.setTextColor(100)
  doc.text('EV Analysis Platform - NTA Report', 14, 28)
  
  doc.setDrawColor(139, 92, 246)
  doc.setLineWidth(0.5)
  doc.line(14, 32, pageWidth - 14, 32)
  
  // Sample Information
  doc.setFontSize(14)
  doc.setTextColor(0)
  doc.text('Sample Information', 14, 42)
  
  autoTable(doc, {
    startY: 46,
    head: [['Property', 'Value']],
    body: [
      ['Sample ID', data.sampleId],
      ['File Name', data.fileName || 'N/A'],
      ['Export Date', timestamp],
      ['Total Particles', String(data.results.total_particles || 'N/A')],
      ['Concentration', data.results.concentration_particles_ml?.toExponential(2) || 'N/A'],
    ],
    theme: 'striped',
    headStyles: { fillColor: [16, 185, 129] }, // Green for NTA
    margin: { left: 14, right: 14 },
  })
  
  // Size Statistics
  const sizeStartY = (doc as any).lastAutoTable.finalY + 10
  doc.setFontSize(14)
  doc.text('Size Statistics', 14, sizeStartY)
  
  autoTable(doc, {
    startY: sizeStartY + 4,
    head: [['Metric', 'Value (nm)']],
    body: [
      ['Median Size', data.results.median_size_nm?.toFixed(2) || 'N/A'],
      ['Mean Size', data.results.mean_size_nm?.toFixed(2) || 'N/A'],
      ['D10', data.results.d10_nm?.toFixed(2) || 'N/A'],
      ['D50', data.results.d50_nm?.toFixed(2) || 'N/A'],
      ['D90', data.results.d90_nm?.toFixed(2) || 'N/A'],
    ],
    theme: 'striped',
    headStyles: { fillColor: [16, 185, 129] },
    margin: { left: 14, right: 14 },
  })
  
  // Size Distribution Bins
  const binsStartY = (doc as any).lastAutoTable.finalY + 10
  doc.setFontSize(14)
  doc.text('Size Distribution Bins', 14, binsStartY)
  
  autoTable(doc, {
    startY: binsStartY + 4,
    head: [['Size Range', 'Percentage']],
    body: [
      ['50-80 nm', data.results.bin_50_80nm_pct ? `${data.results.bin_50_80nm_pct.toFixed(2)}%` : 'N/A'],
      ['80-100 nm', data.results.bin_80_100nm_pct ? `${data.results.bin_80_100nm_pct.toFixed(2)}%` : 'N/A'],
      ['100-120 nm', data.results.bin_100_120nm_pct ? `${data.results.bin_100_120nm_pct.toFixed(2)}%` : 'N/A'],
      ['120-150 nm', data.results.bin_150_200nm_pct ? `${data.results.bin_120_150nm_pct?.toFixed(2)}%` : 'N/A'],
      ['150-200 nm', data.results.bin_150_200nm_pct ? `${data.results.bin_150_200nm_pct.toFixed(2)}%` : 'N/A'],
      ['200+ nm', data.results.bin_200_plus_pct ? `${data.results.bin_200_plus_pct.toFixed(2)}%` : 'N/A'],
    ],
    theme: 'striped',
    headStyles: { fillColor: [16, 185, 129] },
    margin: { left: 14, right: 14 },
  })
  
  // Measurement Conditions
  const condStartY = (doc as any).lastAutoTable.finalY + 10
  doc.setFontSize(14)
  doc.text('Measurement Conditions', 14, condStartY)
  
  autoTable(doc, {
    startY: condStartY + 4,
    head: [['Parameter', 'Value']],
    body: [
      ['Temperature', data.results.temperature_celsius ? `${data.results.temperature_celsius.toFixed(1)}°C` : 'N/A'],
      ['pH', data.results.ph?.toFixed(2) || 'N/A'],
    ],
    theme: 'striped',
    headStyles: { fillColor: [16, 185, 129] },
    margin: { left: 14, right: 14 },
  })
  
  // Footer
  const pageCount = doc.getNumberOfPages()
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i)
    doc.setFontSize(8)
    doc.setTextColor(150)
    doc.text(
      `Page ${i} of ${pageCount} | Generated by BioVaram EV Analysis Platform | ${timestamp}`,
      pageWidth / 2,
      doc.internal.pageSize.getHeight() - 10,
      { align: 'center' }
    )
  }
  
  const filename = `${data.sampleId}_NTA_Report_${new Date().toISOString().split('T')[0]}.pdf`
  doc.save(filename)
}

/**
 * Capture a chart element and add to PDF
 * Requires html2canvas
 */
export async function captureChartToPDF(
  chartElement: HTMLElement,
  doc: any,
  startY: number,
  title?: string
): Promise<number> {
  const html2canvas = (await import('html2canvas')).default
  
  const canvas = await html2canvas(chartElement, {
    scale: 2,
    backgroundColor: '#ffffff',
    logging: false,
  })
  
  const imgData = canvas.toDataURL('image/png')
  const pageWidth = doc.internal.pageSize.getWidth()
  const imgWidth = pageWidth - 28
  const imgHeight = (canvas.height * imgWidth) / canvas.width
  
  if (title) {
    doc.setFontSize(14)
    doc.setTextColor(0)
    doc.text(title, 14, startY)
    startY += 6
  }
  
  doc.addImage(imgData, 'PNG', 14, startY, imgWidth, imgHeight)
  
  return startY + imgHeight + 10
}
