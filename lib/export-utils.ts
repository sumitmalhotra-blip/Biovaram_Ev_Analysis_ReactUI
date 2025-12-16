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
