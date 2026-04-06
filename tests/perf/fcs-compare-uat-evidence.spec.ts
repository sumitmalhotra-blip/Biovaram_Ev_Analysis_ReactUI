import { test, expect } from "@playwright/test"
import fs from "node:fs"
import path from "node:path"

type UATScenario = {
  id: string
  ask: string
  status: "pass" | "fail"
  evidence: string
  note?: string
}

function buildMockResult(sampleId: string) {
  return {
    id: sampleId,
    sample_id: sampleId,
    total_events: 900000,
    channels: ["FSC-A", "SSC-A", "VSSC1-A", "VSSC2-A"],
    fsc_mean: 1200,
    fsc_median: sampleId === "S1" ? 1100 : 1125,
    ssc_mean: 900,
    ssc_median: 850,
    debris_pct: sampleId === "S1" ? 12.4 : 11.9,
    size_statistics: {
      d10: sampleId === "S1" ? 55 : 58,
      d50: sampleId === "S1" ? 102 : 109,
      d90: sampleId === "S1" ? 188 : 194,
      mean: sampleId === "S1" ? 112 : 118,
      std: sampleId === "S1" ? 24 : 25,
    },
  }
}

function buildDenseMockScatter() {
  const points = Array.from({ length: 2600 }, (_, idx) => ({
    x: 500 + ((idx * 13) % 900),
    y: 280 + ((idx * 17) % 680),
    index: idx,
    diameter: 50 + (idx % 180),
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

test("FCS compare UAT evidence pack (8 scenarios)", async ({ page }) => {
  test.setTimeout(180000)

  const outDir = path.resolve("temp/perf-reports")
  fs.mkdirSync(outDir, { recursive: true })

  const scenarios: UATScenario[] = []

  const runScenario = async (id: string, ask: string, run: () => Promise<void>) => {
    const shot = `fcs-uat-${id}.png`
    try {
      await run()
      await page.screenshot({ path: path.join(outDir, shot), fullPage: true })
      scenarios.push({ id, ask, status: "pass", evidence: shot })
    } catch (error) {
      await page.screenshot({ path: path.join(outDir, shot), fullPage: true }).catch(() => {})
      scenarios.push({
        id,
        ask,
        status: "fail",
        evidence: shot,
        note: error instanceof Error ? error.message : "Unknown failure",
      })
    }
  }

  await page.addInitScript(() => {
    const seededState = {
      state: {
        activeTab: "flow-cytometry",
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
            operator: "QA Bot",
            notes: "UAT seeded",
          },
          fileMetadata: null,
          sizeRanges: [],
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
          experimentalConditions: {
            operator: "QA Bot",
            notes: "UAT seeded",
          },
          scatterData: [],
          loadingScatter: false,
        },
        apiSamples: [
          { sample_id: "S1", treatment: "Control", dye: "CFSE" },
          { sample_id: "S2", treatment: "DrugA", dye: "PKH26" },
        ],
        fcsCompareSession: {
          selectedSampleIds: ["S1", "S2"],
          visibleSampleIds: ["S1", "S2"],
          primarySampleId: "S1",
          resultsBySampleId: {},
          scatterBySampleId: {},
          loadingBySampleId: {},
          errorBySampleId: {},
          maxVisibleOverlays: 8,
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

  await page.route("**/api/v1/samples/*/fcs", async (route) => {
    const url = route.request().url()
    const sampleId = url.split("/samples/")[1]?.split("/")[0] || "S1"
    await route.fulfill({ status: 200, json: { sample_id: sampleId, results: [buildMockResult(sampleId)] } })
  })

  await page.route("**/api/v1/samples/*/scatter-data**", async (route) => {
    const url = route.request().url()
    const sampleId = url.split("/samples/")[1]?.split("/")[0] || "S1"
    await route.fulfill({ status: 200, json: { sample_id: sampleId, ...buildDenseMockScatter() } })
  })

  await page.route("**/api/v1/samples**", async (route) => {
    const url = new URL(route.request().url())
    if (!url.pathname.endsWith("/api/v1/samples")) {
      await route.fallback()
      return
    }

    await route.fulfill({
      status: 200,
      json: {
        samples: [
          {
            id: "S1",
            sample_id: "S1",
            treatment: "Control",
            dye: "CFSE",
            files: {
              fcs: "s1.fcs",
              nta: null,
              tem: null,
              western_blot: null,
              all: ["s1.fcs"],
            },
            processing_status: "completed",
            qc_status: "pass",
          },
          {
            id: "S2",
            sample_id: "S2",
            treatment: "DrugA",
            dye: "PKH26",
            files: {
              fcs: "s2.fcs",
              nta: null,
              tem: null,
              western_blot: null,
              all: ["s2.fcs"],
            },
            processing_status: "completed",
            qc_status: "pass",
          },
        ],
      },
    })
  })

  await page.goto("/")
  await page.getByText("Upload Mode", { exact: false }).waitFor({ timeout: 30000 })
  const appErrorHeading = page.getByText("Something Went Wrong", { exact: false })
  if (await appErrorHeading.isVisible().catch(() => false)) {
    throw new Error("App entered error boundary before UAT interactions")
  }

  const experimentalModal = page.getByRole("dialog", { name: /Experimental Conditions/i })
  if (await experimentalModal.isVisible({ timeout: 2000 }).catch(() => false)) {
    await page.keyboard.press("Escape")
  }

  await page.getByRole("button", { name: /Compare Files/i }).click()
  await expect(page.getByRole("tab", { name: /^Overlay/i })).toBeVisible({ timeout: 30000 })
  await page.getByRole("tab", { name: /^Overlay/i }).click()
  await expect(page.getByText(/Scatter Comparison/i)).toBeVisible({ timeout: 30000 })

  await runScenario("01-overlay-access", "Open overlay compare workspace", async () => {
    await expect(page.getByText(/Compare Session/i)).toBeVisible()
    await expect(page.getByRole("button", { name: /^New$/i })).toBeVisible()
  })

  await runScenario("02-graph-instance", "Create and duplicate graph instances", async () => {
    await page.getByRole("button", { name: /^New$/i }).click()
    await page.getByRole("button", { name: /^Duplicate$/i }).click()
    await expect(page.getByRole("button", { name: /Maximize|Restore/i }).first()).toBeVisible()
  })

  await runScenario("03-axis-isolation", "Switch per-file axis mode", async () => {
    await page.getByRole("button", { name: /Per-file Axis/i }).click()
    await expect(page.getByText(/Primary map:/i)).toBeVisible()
    await expect(page.getByText(/Comparison map:/i)).toBeVisible()
  })

  await runScenario("04-density-fallback", "Enable density/contour fallback", async () => {
    const scatterModeTrigger = page.locator("button").filter({ hasText: /^Scatter:/i }).first()
    await scatterModeTrigger.scrollIntoViewIfNeeded()
    await scatterModeTrigger.click()
    await page.getByRole("option", { name: /Scatter: density\/contour/i }).click()
    await expect(page.getByText(/Density fallback active/i)).toBeVisible()
  })

  await runScenario("05-zoom-presets", "Apply focused zoom preset then reset to auto", async () => {
    const zoomPresetTrigger = page.locator("button").filter({ hasText: /^Zoom:/i }).first()
    await zoomPresetTrigger.scrollIntoViewIfNeeded()
    await zoomPresetTrigger.click()
    await page.getByRole("option", { name: /Zoom: core 30%/i }).click()
    await expect(page.getByText(/Zoom preset: core-30/i)).toBeVisible()
    await zoomPresetTrigger.click()
    await page.getByRole("option", { name: /Zoom: auto/i }).click()
    await expect(page.getByText(/Zoom preset: auto/i)).toBeVisible()
  })

  await runScenario("06-metadata-badges", "Show treatment and dye compare badges", async () => {
    await expect(page.getByText(/Tx:/i).first()).toBeVisible()
    await expect(page.getByText(/Dye:/i).first()).toBeVisible()
  })

  await runScenario("07-pin-export", "Pin and export compare overlay", async () => {
    await page.getByRole("button", { name: /^Pin$/i }).click()
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: /^Export$/i }).click(),
    ])
    expect(download.suggestedFilename().toLowerCase()).toContain("overlay")
  })

  await runScenario("08-clear-session", "Run deterministic clear-session action", async () => {
    await page.getByRole("button", { name: /Clear Session/i }).click()
    await expect(page.getByText(/Analysis View/i)).toBeVisible()
  })

  const unresolvedGaps = [
    {
      id: "UAT-GAP-001",
      gap: "Main-thread <=50ms gate is tracked but not automatically asserted in this UAT script.",
      followUp: "Keep dedicated perf gate spec and attach long-task telemetry snapshot in next evidence run.",
    },
  ]

  const evidence = {
    timestamp: new Date().toISOString(),
    scenarios,
    summary: {
      total: scenarios.length,
      passed: scenarios.filter((s) => s.status === "pass").length,
      failed: scenarios.filter((s) => s.status === "fail").length,
    },
    unresolvedGaps,
  }

  fs.writeFileSync(path.join(outDir, "fcs-compare-uat-evidence.json"), JSON.stringify(evidence, null, 2), "utf-8")

  const failed = scenarios.filter((s) => s.status === "fail")
  expect(failed, `Failed UAT scenarios: ${failed.map((s) => s.id).join(", ")}`).toHaveLength(0)
})
