import { test, expect } from "@playwright/test"
import fs from "node:fs"
import path from "node:path"

function buildMockResult(sampleId: string, medianShift = 0) {
  return {
    id: sampleId,
    sample_id: sampleId,
    total_events: 920000,
    channels: ["FSC-A", "SSC-A", "VSSC1-A", "VSSC2-A"],
    fsc_mean: 1280 + medianShift,
    fsc_median: 1120 + medianShift,
    ssc_mean: 910 + medianShift,
    ssc_median: 860 + medianShift,
    particle_size_median_nm: 118 + medianShift * 0.02,
    particle_size_mean_nm: 124 + medianShift * 0.02,
    debris_pct: 11.8,
    size_statistics: {
      d10: 58,
      d50: 118,
      d90: 194,
      mean: 124,
      std: 22,
    },
    processed_at: new Date().toISOString(),
  }
}

function buildMockScatter(sampleId: string, xOffset = 0, yOffset = 0) {
  const points = Array.from({ length: 5000 }, (_, idx) => {
    const x = 450 + (idx % 900) + xOffset
    const y = 250 + ((idx * 7) % 700) + yOffset
    const diameter = 45 + ((idx * 3) % 260)
    return {
      x,
      y,
      index: idx,
      diameter,
    }
  })

  return {
    sample_id: sampleId,
    total_events: 920000,
    returned_points: points.length,
    data: points,
    channels: {
      fsc: "FSC-A",
      ssc: "SSC-A",
      available: ["FSC-A", "SSC-A", "VSSC1-A", "VSSC2-A"],
    },
    warnings: [],
  }
}

function buildDistributionAnalysis() {
  return {
    sample_id: "S1",
    normality_tests: {
      is_normal: false,
      shapiro_pvalue: 0.0021,
    },
    distribution_fits: {
      best_fit_aic: "lognorm",
      fits: {
        normal: { aic: 901.2, ks_pvalue: 0.0112 },
        lognorm: { aic: 818.4, ks_pvalue: 0.2141 },
        gamma: { aic: 844.1, ks_pvalue: 0.1023 },
      },
    },
    overlays: {
      normal: {
        x: [40, 80, 120, 160, 200, 240, 280],
        y_scaled: [120, 310, 520, 460, 280, 130, 60],
      },
      lognorm: {
        x: [40, 80, 120, 160, 200, 240, 280],
        y_scaled: [90, 340, 600, 470, 240, 110, 50],
      },
      gamma: {
        x: [40, 80, 120, 160, 200, 240, 280],
        y_scaled: [75, 300, 560, 500, 270, 120, 45],
      },
    },
    summary_statistics: {
      skew_interpretation: "right-skewed",
    },
    conclusion: {
      recommended_distribution: "lognorm",
      central_tendency_metric: "median",
      central_tendency: 118.2,
    },
  }
}

function buildFCSValuesResponse() {
  const events = Array.from({ length: 6500 }, (_, idx) => ({
    event_id: idx + 1,
    diameter_nm: 40 + ((idx * 5) % 280),
    valid: true,
    fsc: 500 + (idx % 1800),
    ssc: 350 + ((idx * 3) % 1400),
  }))

  return {
    sample_id: "S1",
    events,
    statistics: {
      d10_nm: 58,
      d50_nm: 118,
      d90_nm: 194,
      mean_nm: 124,
      std_nm: 23,
    },
    data_info: {
      valid_sizes: events.length,
      returned_events: events.length,
    },
  }
}

function buildClusteredScatterResponse() {
  return {
    sample_id: "S1",
    zoom_level: 1,
    total_events: 920000,
    clusters: [
      {
        id: 0,
        cx: 900,
        cy: 720,
        count: 120000,
        radius: 22,
        std_x: 90,
        std_y: 70,
        pct: 13.0,
        avg_diameter: 112.3,
      },
      {
        id: 1,
        cx: 1260,
        cy: 1010,
        count: 180000,
        radius: 28,
        std_x: 120,
        std_y: 95,
        pct: 19.6,
        avg_diameter: 136.8,
      },
    ],
    bounds: {
      x_min: 0,
      x_max: 2400,
      y_min: 0,
      y_max: 2200,
    },
    channels: {
      fsc: "FSC-A",
      ssc: "SSC-A",
    },
    individual_points: null,
  }
}

test("single-file visual QA sweep covers scroll, five tabs, overlay toggles, and dev telemetry", async ({ page }) => {
  test.setTimeout(90000)
  const consoleErrors: string[] = []
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      const text = msg.text()
      if (!/favicon|404/.test(text)) {
        consoleErrors.push(text)
      }
    }
  })

  await page.addInitScript(() => {
    const seededState = {
      state: {
        activeTab: "flow-cytometry",
        apiConnected: true,
        isDarkMode: true,
        fcsAnalysis: {
          file: { name: "SingleFile_Reference.fcs" },
          sampleId: "S1",
          results: {
            total_events: 920000,
            channels: ["FSC-A", "SSC-A", "VSSC1-A", "VSSC2-A"],
            fsc_median: 1120,
            ssc_median: 860,
            particle_size_median_nm: 118,
            size_statistics: { d10: 58, d50: 118, d90: 194, mean: 124, std: 22 },
            processed_at: new Date().toISOString(),
          },
          anomalyData: {
            method: "Z-Score",
            total_anomalies: 62,
            anomaly_percentage: 1.24,
            anomalous_indices: [2, 14, 29, 47, 81],
          },
          isAnalyzing: false,
          error: null,
          experimentalConditions: {
            operator: "qa-bot",
            temperature: "22",
            substrateBuffer: "PBS",
            sampleVolume: "100",
            dilutionFactor: "1",
            sampleType: "EV sample",
            notes: "visual qa sweep",
          },
          fileMetadata: null,
          sizeRanges: [
            { name: "Small EVs", min: 30, max: 100, color: "#22c55e" },
            { name: "Exosomes", min: 100, max: 200, color: "#3b82f6" },
            { name: "Large EVs", min: 200, max: 500, color: "#f59e0b" },
          ],
        },
        secondaryFcsAnalysis: {
          file: { name: "SingleFile_Compare.fcs" },
          sampleId: "S2",
          results: {
            total_events: 910000,
            channels: ["FSC-A", "SSC-A", "VSSC1-A", "VSSC2-A"],
            fsc_median: 1148,
            ssc_median: 878,
            particle_size_median_nm: 125,
            size_statistics: { d10: 62, d50: 125, d90: 206, mean: 131, std: 24 },
            processed_at: new Date().toISOString(),
          },
          anomalyData: {
            method: "Z-Score",
            total_anomalies: 59,
            anomaly_percentage: 1.12,
            anomalous_indices: [4, 17, 42, 59, 87],
          },
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
  })

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

  await page.route("**/samples/*/fcs**", async (route) => {
    const url = route.request().url()
    const sampleId = url.split("/samples/")[1]?.split("/")[0] || "S1"
    const shift = sampleId === "S2" ? 25 : 0
    await route.fulfill({ status: 200, json: { sample_id: sampleId, results: [buildMockResult(sampleId, shift)] } })
  })

  await page.route("**/samples/*/scatter-data**", async (route) => {
    const url = route.request().url()
    const sampleId = url.split("/samples/")[1]?.split("/")[0] || "S1"
    const xOffset = sampleId === "S2" ? 70 : 0
    const yOffset = sampleId === "S2" ? 55 : 0
    await route.fulfill({ status: 200, json: buildMockScatter(sampleId, xOffset, yOffset) })
  })

  await page.route("**/samples/*/size-bins**", async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        sample_id: "S1",
        total_events: 920000,
        bins: { small: 3200, medium: 5400, large: 1600 },
        percentages: { small: 31.4, medium: 52.9, large: 15.7 },
        thresholds: { small_max: 100, medium_min: 100, medium_max: 200, large_min: 200 },
      },
    })
  })

  await page.route("**/samples/*/distribution-analysis**", async (route) => {
    await route.fulfill({ status: 200, json: buildDistributionAnalysis() })
  })

  await page.route("**/samples/*/recommend-axes**", async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        sample_id: "S1",
        total_events: 920000,
        recommendations: [
          { rank: 1, x_channel: "FSC-A", y_channel: "SSC-A", score: 0.95, reason: "Best scatter separation", description: "Default scatter pair" },
        ],
        channels: {
          scatter: ["FSC-A", "SSC-A", "VSSC1-A", "VSSC2-A"],
          fluorescence: [],
          all: ["FSC-A", "SSC-A", "VSSC1-A", "VSSC2-A"],
        },
      },
    })
  })

  await page.route("**/samples/*/fcs/values**", async (route) => {
    await route.fulfill({ status: 200, json: buildFCSValuesResponse() })
  })

  await page.route("**/samples/*/clustered-scatter**", async (route) => {
    await route.fulfill({ status: 200, json: buildClusteredScatterResponse() })
  })

  await page.goto("/")

  await page.getByText("Analysis Visualizations", { exact: false }).waitFor({ timeout: 30000 })
  await expect(page.getByText(/Dev Telemetry:/i)).toBeVisible({ timeout: 30000 })

  // Single-file page scroll sweep
  await page.mouse.wheel(0, 1500)
  await page.mouse.wheel(0, -1300)

  // Size Distribution tab + overlay toggle checks
  await page.getByRole("tab", { name: /Size Distribution/i }).click()
  await expect(page.getByText(/Size Distribution/i).first()).toBeVisible({ timeout: 15000 })
  await expect(page.getByText(/SingleFile_Compare\.fcs/i).first()).toBeVisible({ timeout: 15000 })

  // Theory tab + line visibility controls
  await page.getByRole("tab", { name: /Theory vs Measured/i }).click()
  await expect(page.getByText(/Theory vs Measured/i).first()).toBeVisible({ timeout: 15000 })
  await expect(page.getByText(/SingleFile_Compare\.fcs/i).first()).toBeVisible({ timeout: 15000 })

  // FSC vs SSC tab with standard/clustered mode transitions
  await page.getByRole("tab", { name: /^FSC vs SSC$/i }).click()
  await expect(page.getByRole("button", { name: /Clustered/i })).toBeVisible({ timeout: 15000 })
  await page.getByRole("button", { name: /Clustered/i }).click()
  await expect(page.getByText(/Level 1/i)).toBeVisible({ timeout: 20000 })
  await page.getByRole("button", { name: "Standard", exact: true }).click()

  // Diameter tab + overlay toggle checks
  await page.getByRole("tab", { name: /Diameter vs SSC/i }).click()
  await expect(page.getByText(/Mie Theory/i).first()).toBeVisible({ timeout: 15000 })
  await expect(page.getByText(/SingleFile_Compare\.fcs/i).first()).toBeVisible({ timeout: 15000 })

  // Event tab checks
  await page.getByRole("tab", { name: /Event vs Size/i }).click()
  await expect(page.getByText(/Event Index vs Estimated Diameter/i)).toBeVisible({ timeout: 15000 })
  await expect(page.getByText(/sampled points for smooth interaction/i)).toBeVisible({ timeout: 15000 })

  // Overlay off pass (state-driven): disable overlay and verify comparison legend goes away.
  await page.evaluate(() => {
    const raw = window.sessionStorage.getItem("ev-analysis-storage-v2")
    if (!raw) return
    const parsed = JSON.parse(raw)
    if (parsed?.state?.overlayConfig) {
      parsed.state.overlayConfig.enabled = false
      window.sessionStorage.setItem("ev-analysis-storage-v2", JSON.stringify(parsed))
    }
  })
  await page.reload()
  await page.getByText("Analysis Visualizations", { exact: false }).waitFor({ timeout: 30000 })
  await page.getByRole("tab", { name: /Size Distribution/i }).click()
  await expect(page.getByText(/Size Distribution \(Overlay\)/i)).toHaveCount(0)

  const outDir = path.resolve("temp/perf-reports")
  fs.mkdirSync(outDir, { recursive: true })
  await page.screenshot({ path: path.join(outDir, "fcs-single-visual-qa-sweep.png"), fullPage: true })

  fs.writeFileSync(
    path.join(outDir, "fcs-single-visual-qa-sweep-report.json"),
    JSON.stringify(
      {
        timestamp: new Date().toISOString(),
        checks: {
          telemetryBadge: true,
          tabSweep: ["distribution", "theory", "fsc-ssc", "diameter", "event-size"],
          overlayToggleCoverage: "state-driven on/off",
          clusteredModeCoverage: true,
        },
        consoleErrors,
      },
      null,
      2
    ),
    "utf-8"
  )

  expect(consoleErrors).toEqual([])
})
