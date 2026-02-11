import { convertToModelMessages, streamText, tool, type UIMessage } from "ai"
import { z } from "zod"

export const maxDuration = 60

const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || "http://localhost:8000/api/v1"

/**
 * Fetch real sample data from the backend by searching for a filename or sample ID.
 */
async function fetchSampleAnalysis(fileName: string, dataType: string): Promise<{
  found: boolean;
  sampleId?: string;
  dbId?: number;
  fcs?: Record<string, unknown>;
  nta?: Record<string, unknown>;
  alerts?: Array<Record<string, unknown>>;
}> {
  try {
    // Search for sample by name
    const samplesRes = await fetch(`${API_URL}/samples?limit=50`, { method: "GET" })
    if (!samplesRes.ok) return { found: false }
    const samples = await samplesRes.json()

    // Find matching sample (fuzzy match on filename)
    const normalizedName = fileName.toLowerCase().replace(/\.[^.]+$/, "")
    const match = samples.find((s: { sample_id: string }) =>
      s.sample_id.toLowerCase().includes(normalizedName) ||
      normalizedName.includes(s.sample_id.toLowerCase())
    ) || (samples.length > 0 ? samples[0] : null)

    if (!match) return { found: false }

    const result: { found: boolean; sampleId: string; dbId: number; fcs?: Record<string, unknown>; nta?: Record<string, unknown>; alerts?: Array<Record<string, unknown>> } = {
      found: true,
      sampleId: match.sample_id,
      dbId: match.id,
    }

    // Fetch FCS results if applicable
    if (dataType === "fcs" || dataType === "csv") {
      try {
        const fcsRes = await fetch(`${API_URL}/samples/${match.id}/fcs`, { method: "GET" })
        if (fcsRes.ok) result.fcs = await fcsRes.json()
      } catch { /* FCS may not exist */ }
    }

    // Fetch NTA results if applicable
    if (dataType === "nta") {
      try {
        const ntaRes = await fetch(`${API_URL}/samples/${match.id}/nta`, { method: "GET" })
        if (ntaRes.ok) result.nta = await ntaRes.json()
      } catch { /* NTA may not exist */ }
    }

    // Fetch alerts for quality context
    try {
      const alertsRes = await fetch(`${API_URL}/alerts?limit=10`, { method: "GET" })
      if (alertsRes.ok) {
        const alertsData = await alertsRes.json()
        result.alerts = Array.isArray(alertsData) ? alertsData : alertsData.alerts || []
      }
    } catch { /* Alerts may not be available */ }

    return result
  } catch (error) {
    console.error("[Research Chat] Failed to fetch sample data:", error)
    return { found: false }
  }
}

// Define analysis tools — connected to real backend data
const tools = {
  analyzeData: tool({
    description:
      "Analyze uploaded data file and provide insights about particle distribution, concentration, and characteristics",
    inputSchema: z.object({
      fileName: z.string(),
      dataType: z.enum(["fcs", "csv", "nta"]),
      query: z.string(),
    }),
    async *execute({ fileName, dataType, query }) {
      yield { state: "analyzing" as const }

      const data = await fetchSampleAnalysis(fileName, dataType)

      if (!data.found) {
        yield {
          state: "complete" as const,
          analysis: `Sample "${fileName}" was not found in the database. Please upload and analyze the file first using the ${dataType === "nta" ? "NTA" : "Flow Cytometry"} tab, then ask me about it again.`,
        }
        return
      }

      let analysis = `Analysis of ${data.sampleId} (${dataType.toUpperCase()}):\n\n`

      if (data.fcs) {
        const fcs = data.fcs as Record<string, number | string | undefined>
        analysis += `**FCS Analysis Results:**\n`
        analysis += `- Total events: ${(fcs.total_events as number)?.toLocaleString() ?? "N/A"}\n`
        analysis += `- Median particle size: ${fcs.particle_size_median_nm ? `${(fcs.particle_size_median_nm as number).toFixed(1)} nm` : "Not calculated"}\n`
        analysis += `- Mean particle size: ${fcs.particle_size_mean_nm ? `${(fcs.particle_size_mean_nm as number).toFixed(1)} nm` : "Not calculated"}\n`
        analysis += `- FSC median: ${fcs.fsc_median ? (fcs.fsc_median as number).toFixed(1) : "N/A"}\n`
        analysis += `- SSC median: ${fcs.ssc_median ? (fcs.ssc_median as number).toFixed(1) : "N/A"}\n`
        analysis += `- Debris: ${fcs.debris_pct ? `${(fcs.debris_pct as number).toFixed(1)}%` : "N/A"}\n`
        analysis += `- CD81+: ${fcs.cd81_positive_pct ? `${(fcs.cd81_positive_pct as number).toFixed(1)}%` : "N/A"}\n\n`

        // Quality assessment
        const events = (fcs.total_events as number) || 0
        const debris = (fcs.debris_pct as number) || 0
        if (events < 5000) analysis += `⚠️ Low event count (${events}) — consider longer acquisition time.\n`
        if (debris > 20) analysis += `⚠️ High debris (${debris.toFixed(1)}%) — check sample preparation.\n`
        if (events >= 5000 && debris <= 10) analysis += `✅ Data quality is excellent.\n`
      }

      if (data.nta) {
        const nta = data.nta as Record<string, number | string | undefined>
        analysis += `**NTA Analysis Results:**\n`
        analysis += `- Median size: ${nta.median_size_nm ? `${(nta.median_size_nm as number).toFixed(1)} nm` : "N/A"}\n`
        analysis += `- Mean size: ${nta.mean_size_nm ? `${(nta.mean_size_nm as number).toFixed(1)} nm` : "N/A"}\n`
        analysis += `- D10: ${nta.d10_nm ? `${(nta.d10_nm as number).toFixed(1)} nm` : "N/A"}\n`
        analysis += `- D50: ${nta.d50_nm ? `${(nta.d50_nm as number).toFixed(1)} nm` : "N/A"}\n`
        analysis += `- D90: ${nta.d90_nm ? `${(nta.d90_nm as number).toFixed(1)} nm` : "N/A"}\n`
        analysis += `- Concentration: ${nta.concentration_particles_ml ? `${(nta.concentration_particles_ml as number).toExponential(2)} particles/mL` : "N/A"}\n`
        analysis += `- Temperature: ${nta.temperature_celsius ? `${(nta.temperature_celsius as number).toFixed(1)}°C` : "N/A"}\n\n`
      }

      analysis += `\nRegarding your question about "${query}": Based on the above data, `
      analysis += data.fcs
        ? `the sample shows ${(data.fcs as Record<string, number>).particle_size_median_nm > 100 ? "larger" : "smaller"} particles typical for this EV preparation type.`
        : `please analyze the sample first to get detailed insights.`

      yield { state: "complete" as const, analysis }
    },
  }),

  generateGraph: tool({
    description: "Generate a visualization graph for the data showing distribution, scatter plots, or other analysis",
    inputSchema: z.object({
      graphType: z.enum(["histogram", "scatter", "line", "distribution"]),
      title: z.string(),
      xAxis: z.string(),
      yAxis: z.string(),
    }),
    async *execute({ graphType, title, xAxis, yAxis }) {
      yield { state: "generating" as const }

      // Try to fetch real sample data for graph generation
      let graphData: Array<{ x: number; y: number }> = []

      try {
        const samplesRes = await fetch(`${API_URL}/samples?limit=1`, { method: "GET" })
        if (samplesRes.ok) {
          const samples = await samplesRes.json()
          if (samples.length > 0) {
            const sampleId = samples[0].id
            // Try to get scatter data for real graph points
            const scatterRes = await fetch(`${API_URL}/samples/${sampleId}/scatter-data?limit=100`, { method: "GET" })
            if (scatterRes.ok) {
              const scatterData = await scatterRes.json()
              if (scatterData.data && Array.isArray(scatterData.data)) {
                graphData = scatterData.data.slice(0, 50).map((p: Record<string, number>) => ({
                  x: p.diameter || p.x || p.fsc || 0,
                  y: p.ssc || p.y || p.intensity || 0,
                }))
              }
            }
          }
        }
      } catch {
        // Fallback: no data available
      }

      if (graphData.length === 0) {
        yield {
          state: "complete" as const,
          graphData: {
            type: graphType,
            title,
            data: [],
            message: "No sample data available. Upload and analyze a file first to generate real visualizations.",
          },
        }
        return
      }

      yield {
        state: "complete" as const,
        graphData: {
          type: graphType,
          title,
          xAxis,
          yAxis,
          data: graphData,
          source: "real_data",
        },
      }
    },
  }),

  guideAnalysis: tool({
    description: "Provide step-by-step guidance on how to analyze data using specific tabs and techniques",
    inputSchema: z.object({
      topic: z.string(),
      currentTab: z.enum(["flow-cytometry", "nta", "cross-compare", "dashboard"]),
    }),
    async *execute({ topic, currentTab }) {
      yield { state: "generating" as const }
      const guidance = {
        "flow-cytometry": `For ${topic}, use the Flow Cytometry tab: 1) Upload your FCS file, 2) Configure Mie scattering parameters (wavelength, RI) in the sidebar, 3) Review scatter plots and size distribution, 4) Apply gating to select populations of interest, 5) Check the anomaly detection results, 6) Export results as CSV/Excel/PDF.`,
        nta: `For ${topic}, use the NTA tab: 1) Upload your NTA CSV or PDF report, 2) Adjust temperature correction settings if needed, 3) Review size distribution and concentration profile, 4) Check the supplementary metadata table, 5) Export results in your preferred format.`,
        "cross-compare": `For ${topic}, use Cross-Compare: 1) Select an FCS sample and an NTA sample from the dropdowns, 2) Click "Run Cross-Validation" for automated statistical comparison, 3) Review the overlay histogram, KDE comparison, and discrepancy charts, 4) Check the validation verdict for publication readiness, 5) Export the comparison report.`,
        dashboard: `For ${topic}, check the Dashboard: 1) Review your pinned charts from previous analyses, 2) Check the quick stats panel for sample counts and API status, 3) View recent activity for upload/analysis history, 4) Use the AI chat for quick questions about your data.`,
      }
      yield {
        state: "complete" as const,
        guidance: guidance[currentTab] || "Use the appropriate tab for your analysis.",
      }
    },
  }),

  validateResults: tool({
    description: "Validate analysis results and check for quality issues or anomalies",
    inputSchema: z.object({
      analysisType: z.string(),
      checkQuality: z.boolean(),
    }),
    async *execute({ analysisType, checkQuality }) {
      yield { state: "validating" as const }

      const issues: string[] = []
      let isValid = true

      if (checkQuality) {
        try {
          // Fetch real alerts from the backend
          const alertsRes = await fetch(`${API_URL}/alerts?limit=20&severity=critical,warning`, { method: "GET" })
          if (alertsRes.ok) {
            const alertsData = await alertsRes.json()
            const alerts = Array.isArray(alertsData) ? alertsData : alertsData.alerts || []

            for (const alert of alerts) {
              issues.push(`[${(alert.severity || "info").toUpperCase()}] ${alert.message || alert.title || "Unknown issue"}`)
              if (alert.severity === "critical") isValid = false
            }
          }

          // Fetch latest sample to check quality metrics
          const samplesRes = await fetch(`${API_URL}/samples?limit=1`, { method: "GET" })
          if (samplesRes.ok) {
            const samples = await samplesRes.json()
            if (samples.length > 0) {
              const sampleId = samples[0].id
              const fcsRes = await fetch(`${API_URL}/samples/${sampleId}/fcs`, { method: "GET" })
              if (fcsRes.ok) {
                const fcs = await fcsRes.json()
                if (fcs.total_events && fcs.total_events < 5000) {
                  issues.push(`Low event count: ${fcs.total_events} (recommended: >5000)`)
                }
                if (fcs.debris_pct && fcs.debris_pct > 20) {
                  issues.push(`High debris percentage: ${fcs.debris_pct.toFixed(1)}% (threshold: <20%)`)
                  isValid = false
                }
                if (fcs.debris_pct && fcs.debris_pct > 10 && fcs.debris_pct <= 20) {
                  issues.push(`Moderate debris: ${fcs.debris_pct.toFixed(1)}% — acceptable but could be improved`)
                }
              }
            }
          }
        } catch (error) {
          issues.push("Could not connect to backend to verify quality metrics")
        }
      }

      if (issues.length === 0) {
        issues.push("No quality issues detected")
      }

      yield {
        state: "complete" as const,
        validation: {
          isValid,
          analysisType,
          issues,
          recommendation: isValid
            ? "Results pass quality checks. Consider running cross-validation (FCS vs NTA) for publication-grade verification."
            : "Critical quality issues detected. Address the issues listed above before proceeding with analysis.",
        },
      }
    },
  }),
}

export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json()

  const systemPrompt = `You are an expert AI research assistant for the BioVaram EV Analysis Platform. Your role is to:

1. **Data Analysis Expert**: Analyze FCS (Flow Cytometry) and NTA (Nanoparticle Tracking Analysis) data, providing insights about:
   - Particle size distribution (median, D10, D50, D90)
   - Forward Scatter (FSC) and Side Scatter (SSC) characteristics
   - Event counts, debris percentage, quality metrics
   - Marker expression (CD81, CD9, CD63 positivity)
   - Concentration measurements

2. **Visualization Guide**: Help users understand and create:
   - Size distribution histograms
   - Scatter plots (FSC vs SSC)
   - Concentration profiles
   - Overlay comparisons between FCS and NTA
   - Quality control charts

3. **Workflow Assistant**: Guide users through:
   - Flow Cytometry tab: File upload, gating, analysis, statistics
   - NTA tab: Data upload, size distribution, concentration
   - Cross-Compare tab: Multi-method comparison, discrepancy analysis
   - Dashboard: Pinned charts, quick stats, recent activity

4. **Scientific Interpreter**: Explain:
   - What FSC/SSC values mean for particle size and complexity
   - How Mie scattering theory converts FSC to diameter
   - Quality indicators (debris %, event count thresholds)
   - Significance of size distribution metrics
   - Best practices for EV characterization

5. **Problem Solver**: Identify and help resolve:
   - Quality issues (high debris, low event count)
   - Data anomalies and outliers
   - Discrepancies between FCS and NTA measurements
   - Experimental design questions

**Key Knowledge**:
- EV size range: typically 30-200nm (small EVs), 50-500nm (total range)
- Debris: particles <50nm or >500nm are flagged
- Quality thresholds: >5000 events (good), debris <10% (excellent), <20% (acceptable)
- FSC primarily measures size, SSC measures internal complexity
- Common markers: CD81, CD9, CD63 (tetraspanins)

When users provide context about their data (like FCS results or pinned charts), analyze those specific values and provide actionable insights. Always offer concrete next steps.

Be conversational, clear, and scientifically accurate. Use bullet points for clarity when listing insights.`

  const prompt = convertToModelMessages(messages)

  const result = streamText({
    model: "groq/mixtral-8x7b-32768",
    messages: prompt,
    system: systemPrompt,
    tools,
    maxOutputTokens: 2000,
    temperature: 0.7,
  })

  return result.toUIMessageStreamResponse()
}
