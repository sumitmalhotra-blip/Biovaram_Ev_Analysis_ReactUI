import { test, expect } from "@playwright/test"
import fs from "node:fs"
import path from "node:path"

const LONG_TASK_GATE_MS = 50
const RECURRING_LONG_TASK_LIMIT = 1

test("FCS compare long-task gate evidence", async ({ page }) => {
  test.setTimeout(240000)
  let uploadCounter = 0

  await page.addInitScript(() => {
    ;(window as any).__FCS_LONG_TASK_ENTRIES__ = []

    if (typeof PerformanceObserver !== "undefined") {
      try {
        const observer = new PerformanceObserver((list) => {
          const current = (window as any).__FCS_LONG_TASK_ENTRIES__ || []
          for (const entry of list.getEntries()) {
            current.push({
              name: entry.name,
              startTime: Math.round(entry.startTime),
              duration: Math.round(entry.duration * 100) / 100,
            })
          }
          ;(window as any).__FCS_LONG_TASK_ENTRIES__ = current
        })
        observer.observe({ entryTypes: ["longtask"] })
      } catch {
        // Long task API may be unavailable in some environments.
      }
    }

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
            notes: "long-task gate seeded",
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
          scatterData: [],
          loadingScatter: false,
        },
        fcsCompareSession: {
          selectedSampleIds: ["S1", "S2"],
          visibleSampleIds: ["S1", "S2"],
          primarySampleId: "S1",
          compareItemMetaById: {
            S1: { backendSampleId: "S1", sampleLabel: "S1", fileName: "seed-s1.fcs", treatment: "Control", dye: "CFSE", uploadedAt: 1712400000301 },
            S2: { backendSampleId: "S2", sampleLabel: "S2", fileName: "seed-s2.fcs", treatment: "DrugA", dye: "PKH26", uploadedAt: 1712400000302 },
          },
          resultsBySampleId: {},
          scatterBySampleId: {},
          loadingBySampleId: {},
          errorBySampleId: {},
          maxVisibleOverlays: 8,
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

  await page.route("**/upload/fcs**", async (route) => {
    uploadCounter += 1
    const sampleId = uploadCounter === 1 ? "S1" : "S2"
    await route.fulfill({
      status: 200,
      json: {
        success: true,
        id: uploadCounter,
        sample_id: sampleId,
        job_id: `job-${sampleId}`,
        processing_status: "completed",
        fcs_results: {
          sample_id: sampleId,
          total_events: 900000,
          channels: ["FSC-A", "SSC-A", "VSSC1-A", "VSSC2-A"],
          fsc_median: 1100,
          debris_pct: 12,
          size_statistics: { d10: 55, d50: 102, d90: 188, mean: 112, std: 24 },
        },
      },
    })
  })

  await page.route("**/samples/*/fcs**", async (route) => {
    const url = route.request().url()
    const sampleId = url.split("/samples/")[1]?.split("/")[0] || "S1"
    await route.fulfill({
      status: 200,
      json: {
        sample_id: sampleId,
        results: [{
          sample_id: sampleId,
          total_events: 900000,
          channels: ["FSC-A", "SSC-A", "VSSC1-A", "VSSC2-A"],
          fsc_median: 1100,
          debris_pct: 12,
          size_statistics: { d10: 55, d50: 102, d90: 188, mean: 112, std: 24 },
        }],
      },
    })
  })

  await page.route("**/samples/*/scatter-data**", async (route) => {
    const points = Array.from({ length: 2500 }, (_, idx) => ({
      x: 500 + (idx % 700),
      y: 300 + (idx % 500),
      index: idx,
      diameter: 50 + (idx % 200),
    }))
    const url = route.request().url()
    const sampleId = url.split("/samples/")[1]?.split("/")[0] || "S1"
    await route.fulfill({
      status: 200,
      json: {
        sample_id: sampleId,
        total_events: 900000,
        returned_points: points.length,
        data: points,
      },
    })
  })

  await page.goto("/")
  await page.getByText("Upload Mode", { exact: false }).waitFor({ timeout: 30000 })
  await page.getByRole("button", { name: /Compare Files/i }).click()

  const uploadInput = page.locator("#fcs-upload-comparison")
  await uploadInput.setInputFiles([
    { name: "lt-a.fcs", mimeType: "application/octet-stream", buffer: Buffer.from("lt-a") },
    { name: "lt-b.fcs", mimeType: "application/octet-stream", buffer: Buffer.from("lt-b") },
  ])
  await page.getByRole("button", { name: /Upload to Compare Session/i }).click()

  const overlayTab = page.getByRole("tab", { name: /^Overlay/i })
  await expect(overlayTab).toBeEnabled({ timeout: 30000 })
  await overlayTab.click()
  await expect(page.getByText(/Scatter Comparison/i)).toBeVisible({ timeout: 30000 })

  // Reset long-task capture to focus only on interactive compare flows.
  await page.evaluate(() => {
    ;(window as any).__FCS_LONG_TASK_ENTRIES__ = []
  })

  for (let cycle = 0; cycle < 3; cycle += 1) {
    await page.getByRole("button", { name: /Show All/i }).first().dispatchEvent("click")
    await page.getByRole("button", { name: /Reference Only/i }).first().dispatchEvent("click")
    await page.getByRole("button", { name: /Show All/i }).first().dispatchEvent("click")
  }

  const longTaskEntries = await page.evaluate(() => {
    const raw = ((window as any).__FCS_LONG_TASK_ENTRIES__ || []) as Array<{ name?: string; startTime?: number; duration?: number }>
    return raw
      .filter((entry) => Number.isFinite(entry.duration))
      .map((entry) => ({
        name: entry.name || "longtask",
        startTime: Number(entry.startTime || 0),
        duration: Number(entry.duration || 0),
      }))
  })

  const over50 = longTaskEntries.filter((entry) => entry.duration > LONG_TASK_GATE_MS)
  const maxDuration = longTaskEntries.reduce((max, entry) => Math.max(max, entry.duration), 0)

  const evidence = {
    timestamp: new Date().toISOString(),
    gate: {
      thresholdMs: LONG_TASK_GATE_MS,
      recurringLimit: RECURRING_LONG_TASK_LIMIT,
    },
    summary: {
      totalLongTasks: longTaskEntries.length,
      overThresholdCount: over50.length,
      maxDurationMs: Math.round(maxDuration * 100) / 100,
    },
    longTasksOverThreshold: over50,
    passFail: {
      recurringOver50: over50.length > RECURRING_LONG_TASK_LIMIT,
      gatePassed: over50.length <= RECURRING_LONG_TASK_LIMIT,
    },
  }

  const outDir = path.resolve("temp/perf-reports")
  fs.mkdirSync(outDir, { recursive: true })
  fs.writeFileSync(path.join(outDir, "fcs-compare-longtask-gate.json"), JSON.stringify(evidence, null, 2), "utf-8")

  expect(evidence.passFail.gatePassed).toBeTruthy()
})
