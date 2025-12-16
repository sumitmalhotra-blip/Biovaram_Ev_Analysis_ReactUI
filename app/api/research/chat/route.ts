import { convertToModelMessages, streamText, tool, type UIMessage } from "ai"
import { z } from "zod"

export const maxDuration = 60

// Define analysis tools
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
      await new Promise((r) => setTimeout(r, 1500))
      yield {
        state: "complete" as const,
        analysis: `Analysis of ${fileName}: The data shows typical EV distribution with median size of 127.4nm. Key findings include ${query}. Concentration levels are within normal range.`,
      }
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
    async *execute({ graphType, title }) {
      yield { state: "generating" as const }
      await new Promise((r) => setTimeout(r, 1000))
      yield {
        state: "complete" as const,
        graphData: {
          type: graphType,
          title,
          data: Array.from({ length: 20 }, (_, i) => ({
            x: i * 10,
            y: Math.random() * 100,
          })),
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
        "flow-cytometry": `For ${topic}, use the Flow Cytometry tab: 1) Upload your FCS file, 2) Set up gating strategy, 3) Analyze populations, 4) Review results.`,
        nta: `For ${topic}, use the NTA tab: 1) Upload NTA data, 2) Set temperature parameters, 3) Review size distribution, 4) Check concentration.`,
        "cross-compare": `For ${topic}, use Cross-Compare: 1) Select multiple files, 2) Define comparison parameters, 3) View overlays, 4) Export results.`,
        dashboard: `For ${topic}, check the Dashboard: 1) Review pinned charts, 2) Check recent activity, 3) Compare samples, 4) Access quick stats.`,
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
      await new Promise((r) => setTimeout(r, 1200))
      yield {
        state: "complete" as const,
        validation: {
          isValid: true,
          issues: checkQuality ? ["Minor noise detected", "Slight compensation drift"] : [],
          recommendation: "Results are ready for publication. Consider repeat measurements for confirmation.",
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
