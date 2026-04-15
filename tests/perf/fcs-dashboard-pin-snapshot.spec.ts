import { test, expect } from "@playwright/test"

function buildMockResult(sampleId: string) {
  return {
    id: sampleId,
    sample_id: sampleId,
    total_events: 920000,
    channels: ["FSC-A", "SSC-A", "VSSC1-A", "VSSC2-A"],
    fsc_mean: 1280,
    fsc_median: 1120,
    ssc_mean: 910,
    ssc_median: 860,
    particle_size_median_nm: 118,
    particle_size_mean_nm: 124,
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

function buildMockScatter(sampleId: string) {
  const points = Array.from({ length: 5000 }, (_, idx) => {
    const x = 450 + (idx % 900)
    const y = 250 + ((idx * 7) % 700)
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

test("pins all five analysis charts and renders snapshot previews on dashboard", async ({ page }) => {
  test.setTimeout(180000)

  await page.addInitScript(() => {
    const seededState = {
      state: {
        activeTab: "flow-cytometry",
        apiConnected: true,
        isDarkMode: true,
        pinnedCharts: [],
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
            notes: "pin snapshot test",
          },
          fileMetadata: null,
          sizeRanges: [
            { name: "Small EVs", min: 30, max: 100, color: "#22c55e" },
            { name: "Exosomes", min: 100, max: 200, color: "#3b82f6" },
            { name: "Large EVs", min: 200, max: 500, color: "#f59e0b" },
          ],
        },
        secondaryFcsAnalysis: {
          file: null,
          sampleId: null,
          results: null,
          anomalyData: null,
          isAnalyzing: false,
          error: null,
          scatterData: [],
          loadingScatter: false,
        },
        overlayConfig: {
          enabled: false,
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
    await route.fulfill({ status: 200, json: { sample_id: sampleId, results: [buildMockResult(sampleId)] } })
  })

  await page.route("**/samples/*/scatter-data**", async (route) => {
    const url = route.request().url()
    const sampleId = url.split("/samples/")[1]?.split("/")[0] || "S1"
    await route.fulfill({ status: 200, json: buildMockScatter(sampleId) })
  })

  await page.route("**/samples/*/fcs/values**", async (route) => {
    await route.fulfill({ status: 200, json: buildFCSValuesResponse() })
  })

  await page.goto("/")

  await page.getByText("Analysis Visualizations", { exact: false }).waitFor({ timeout: 30000 })

  // Pre-warm data-heavy tabs so pinning is not blocked by loading guards.
  await page.getByRole("tab", { name: /FSC vs SSC/i }).click()
  await expect(page.getByText(/Loading scatter data.../i)).toHaveCount(0, { timeout: 30000 })

  await page.getByRole("tab", { name: /Event vs Size/i }).click()
  await expect(page.locator('[data-pin-chart="event-size"]')).toBeVisible({ timeout: 30000 })

  const chartPins = [
    { tab: "Size Distribution", title: "Size Distribution", captureKey: "distribution" },
    { tab: "FSC vs SSC", title: "FSC vs SSC", captureKey: "fsc-ssc" },
    { tab: "Diameter vs SSC", title: "Diameter vs SSC", captureKey: "diameter" },
    { tab: "Theory vs Measured", title: "Theory vs Measured", captureKey: "theory" },
    { tab: "Event vs Size", title: "Event vs Size", captureKey: "event-size" },
  ]

  for (const [index, chart] of chartPins.entries()) {
    await page.getByRole("tab", { name: new RegExp(chart.tab, "i") }).click()
    const chartRegion = page.locator(`[data-pin-chart="${chart.captureKey}"]`).first()
    await expect(chartRegion).toBeVisible({ timeout: 20000 })

    const activePanel = page.locator('[role="tabpanel"][data-state="active"]').first()
    const pinButton = activePanel
      .locator(`[data-pin-chart="${chart.captureKey}"]`)
      .first()
      .locator("xpath=preceding::button[.//*[contains(@class,'lucide-pin')]][1]")

    await expect(pinButton).toBeVisible({ timeout: 10000 })
    await pinButton.click({ force: true })

    await expect.poll(async () => {
      return await page.evaluate(() => {
        const raw = window.sessionStorage.getItem("ev-analysis-storage-v2")
        if (!raw) return 0
        const parsed = JSON.parse(raw)
        const pinned = parsed?.state?.pinnedCharts ?? []
        return pinned.length
      })
    }, { timeout: 30000 }).toBe(index + 1)
  }

  await expect.poll(async () => {
    return await page.evaluate(() => {
      const raw = window.sessionStorage.getItem("ev-analysis-storage-v2")
      if (!raw) return 0
      const parsed = JSON.parse(raw)
      const pinned = parsed?.state?.pinnedCharts ?? []
      return pinned.filter((c: { snapshotDataUrl?: string }) => typeof c.snapshotDataUrl === "string" && c.snapshotDataUrl.startsWith("data:image/")).length
    })
  }, { timeout: 30000 }).toBe(5)

  await page.getByRole("button", { name: /^Dashboard$/i }).click()
  await expect(page.getByText(/Pinned Charts/i)).toBeVisible({ timeout: 15000 })

  const snapshotImages = page.locator('img[alt$="snapshot"]')
  await expect(snapshotImages).toHaveCount(5)

  for (const chart of chartPins) {
    await expect(page.getByText(chart.title, { exact: true })).toBeVisible()
  }
})
