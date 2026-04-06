import { test, expect } from "@playwright/test"
import fs from "node:fs"
import path from "node:path"

const PRIMARY_GATE_LIMIT_MS = 1500
const COMPARE_GATE_LIMIT_MS = 3000
const BENCHMARK_SAMPLE_IDS = ["S1", "S2", "S3", "S4", "S5"]

function extractGateMs(text: string | null): number | null {
  if (!text) return null
  const match = text.match(/:\s*(\d+)ms\s*\//i)
  if (!match) return null
  return Number.parseInt(match[1], 10)
}

function buildMockResult(sampleId: string) {
  return {
    id: sampleId,
    sample_id: sampleId,
    total_events: 900000,
    channels: ["FSC-A", "SSC-A", "VSSC1-A", "VSSC2-A"],
    fsc_mean: 1200,
    fsc_median: 1100,
    ssc_mean: 900,
    ssc_median: 850,
    debris_pct: 12.4,
    size_statistics: {
      d10: 55,
      d50: 102,
      d90: 188,
      mean: 112,
      std: 24,
    },
  }
}

function buildMockScatter() {
  const points = Array.from({ length: 3500 }, (_, idx) => ({
    x: 500 + (idx % 700),
    y: 300 + (idx % 500),
    index: idx,
    diameter: 50 + (idx % 200),
  }))

  return {
    total_events: 900000,
    returned_points: points.length,
    data: points,
    channels: {
      fsc: "FSC-A",
      ssc: "SSC-A",
      available: ["FSC-A", "SSC-A", "VSSC1-A", "VSSC2-A"],
    },
  }
}

test("FCS compare gate badges produce reproducible pass/fail evidence", async ({ page }) => {
  await page.addInitScript(({ sampleIds }) => {
    // Enable benchmark mode so compare loader can use 5 sample IDs.
    ;(window as any).__FCS_PERF_COMPARE_SAMPLE_IDS__ = sampleIds

    // Seed persisted store so Flow Cytometry tab has immediate compare context.
    const seededState = {
      state: {
        activeTab: "flow-cytometry",
        isDarkMode: true,
        sidebarCollapsed: false,
        sidebarWidth: 280,
        apiConnected: true,
        fcsAnalysis: {
          file: null,
          sampleId: "S1",
          results: {
            total_events: 900000,
            channels: ["FSC-A", "SSC-A", "VSSC1-A", "VSSC2-A"],
            size_statistics: { d10: 55, d50: 102, d90: 188, mean: 112, std: 24 },
            fsc_median: 1100,
            debris_pct: 12.4,
          },
          anomalyData: null,
          isAnalyzing: false,
          error: null,
          experimentalConditions: {
            operator: "perf-bot",
            temperature: "22",
            substrateBuffer: "PBS",
            customBuffer: "",
            sampleVolume: "100",
            dilutionFactor: "1",
            antibodyUsed: "",
            antibodyConcentration: "",
            incubationTime: "",
            sampleType: "EV sample",
            filterSize: "",
            notes: "seeded for perf automation",
          },
          fileMetadata: null,
          sizeRanges: [
            { name: "Exomeres (0-50nm)", min: 0, max: 50, color: "#22c55e" },
            { name: "Small EVs (51-100nm)", min: 51, max: 100, color: "#3b82f6" },
            { name: "Medium EVs (101-150nm)", min: 101, max: 150, color: "#a855f7" },
            { name: "Large EVs (151-200nm)", min: 151, max: 200, color: "#f59e0b" },
            { name: "Very Large EVs (200+nm)", min: 200, max: 1000, color: "#ef4444" },
          ],
        },
        secondaryFcsAnalysis: {
          file: null,
          sampleId: "S2",
          results: {
            total_events: 900000,
            channels: ["FSC-A", "SSC-A", "VSSC1-A", "VSSC2-A"],
            size_statistics: { d10: 58, d50: 109, d90: 194, mean: 118, std: 25 },
            fsc_median: 1125,
            debris_pct: 11.9,
          },
          anomalyData: null,
          isAnalyzing: false,
          error: null,
          scatterData: [],
          loadingScatter: false,
        },
        overlayConfig: {
          enabled: true,
          showBothHistograms: true,
          showOverlaidScatter: true,
          showOverlaidTheory: true,
          showOverlaidDiameter: true,
          primaryColor: "#7c3aed",
          secondaryColor: "#f97316",
          primaryLabel: "Primary",
          secondaryLabel: "Comparison",
          primaryOpacity: 0.7,
          secondaryOpacity: 0.5,
        },
      },
      version: 0,
    }

    window.sessionStorage.setItem("ev-analysis-storage-v2", JSON.stringify(seededState))
  }, { sampleIds: BENCHMARK_SAMPLE_IDS })

  await page.route("**/health", async (route) => {
    await route.fulfill({ status: 200, json: { status: "ok", database: "ok", timestamp: new Date().toISOString() } })
  })

  await page.route("**/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        access_token: "mock-token",
        user: {
          id: 1,
          name: "Lab User",
          email: "lab@biovaram.local",
          role: "researcher",
          organization: "BioVaram Lab",
        },
      },
    })
  })

  await page.route("**/api/v1/samples/*/fcs", async (route) => {
    const url = route.request().url()
    const sampleId = url.split("/samples/")[1]?.split("/")[0] || "S1"
    await route.fulfill({ status: 200, json: { sample_id: sampleId, results: [buildMockResult(sampleId)] } })
  })

  await page.route("**/api/v1/samples/*/scatter-data**", async (route) => {
    const url = route.request().url()
    const sampleId = url.split("/samples/")[1]?.split("/")[0] || "S1"
    await route.fulfill({ status: 200, json: { sample_id: sampleId, ...buildMockScatter() } })
  })

  await page.goto("/")

  await page.getByText("Upload Mode", { exact: false }).waitFor({ timeout: 30000 })
  await page.getByRole("button", { name: /Compare Files/i }).click()

  const primaryGateBadge = page.getByText(/Primary Gate:/i).first()
  const compareGateBadge = page.getByText(/Compare Gate:/i).first()

  await expect(primaryGateBadge).toBeVisible({ timeout: 30000 })
  await expect(compareGateBadge).toBeVisible({ timeout: 30000 })

  const primaryGateText = await primaryGateBadge.textContent()
  const compareGateText = await compareGateBadge.textContent()

  const primaryGateMs = extractGateMs(primaryGateText)
  const compareGateMs = extractGateMs(compareGateText)

  const result = {
    timestamp: new Date().toISOString(),
    benchmarkSampleIds: BENCHMARK_SAMPLE_IDS,
    thresholds: {
      primaryMs: PRIMARY_GATE_LIMIT_MS,
      compareMs: COMPARE_GATE_LIMIT_MS,
    },
    measured: {
      primaryGateText,
      compareGateText,
      primaryGateMs,
      compareGateMs,
    },
    passFail: {
      primaryPass: primaryGateMs !== null ? primaryGateMs <= PRIMARY_GATE_LIMIT_MS : false,
      comparePass: compareGateMs !== null ? compareGateMs <= COMPARE_GATE_LIMIT_MS : false,
    },
  }

  const outDir = path.resolve("temp/perf-reports")
  fs.mkdirSync(outDir, { recursive: true })
  fs.writeFileSync(path.join(outDir, "fcs-compare-gates-report.json"), JSON.stringify(result, null, 2), "utf-8")

  await page.screenshot({ path: path.join(outDir, "fcs-compare-gates-screenshot.png"), fullPage: true })

  expect(result.measured.primaryGateMs).not.toBeNull()
  expect(result.measured.compareGateMs).not.toBeNull()
  expect(result.passFail.primaryPass).toBeTruthy()
  expect(result.passFail.comparePass).toBeTruthy()
})
