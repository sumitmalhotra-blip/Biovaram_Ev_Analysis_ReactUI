import { test, expect } from "@playwright/test"
import fs from "node:fs"
import path from "node:path"

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
  const points = Array.from({ length: 400 }, (_, idx) => ({
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

type PersistedStore = {
  state: {
    fcsCompareGraphInstances?: Array<{
      id: string
      title: string
      axisMode: "unified" | "per-file"
      unifiedAxis: { x: string; y: string }
      primaryAxis: { x: string; y: string }
      comparisonAxis: { x: string; y: string }
      isMaximized: boolean
      createdAt: number
    }>
    activeFCSCompareGraphInstanceId?: string | null
    pinnedCharts?: Array<{ id: string; title: string; data: Array<{ category?: string }> }>
  }
}

async function getPersistedStore(page: import("@playwright/test").Page): Promise<PersistedStore> {
  return page.evaluate(() => {
    const raw = window.sessionStorage.getItem("ev-analysis-storage-v2")
    return raw ? JSON.parse(raw) : { state: {} }
  })
}

test("FCS compare controls verification checklist", async ({ page }) => {
  await page.addInitScript(() => {
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
            operator: "QA Bot",
            notes: "Seeded for automated compare verification",
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
            notes: "Seeded for automated compare verification",
          },
          scatterData: [],
          loadingScatter: false,
        },
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
    await route.fulfill({ status: 200, json: { sample_id: sampleId, ...buildMockScatter() } })
  })

  await page.goto("/")

  await page.getByText("Upload Mode", { exact: false }).waitFor({ timeout: 30000 })
  const experimentalModal = page.getByRole("dialog", { name: /Experimental Conditions/i })
  if (await experimentalModal.isVisible({ timeout: 2000 }).catch(() => false)) {
    await page.keyboard.press("Escape")

    if (await experimentalModal.isVisible().catch(() => false)) {
      const closeCandidates = [
        page.getByRole("button", { name: /^Close$/i }).first(),
        page.getByRole("button", { name: /^Cancel$/i }).first(),
        page.getByRole("button", { name: /^Skip$/i }).first(),
        page.getByRole("button", { name: /^×$/i }).first(),
        page.locator("[role='dialog'] button").first(),
      ]

      for (const candidate of closeCandidates) {
        if (await candidate.isVisible().catch(() => false)) {
          await candidate.click({ force: true })
          if (!(await experimentalModal.isVisible().catch(() => false))) {
            break
          }
        }
      }
    }

    if (await experimentalModal.isVisible().catch(() => false)) {
      const box = await experimentalModal.boundingBox()
      if (box) {
        await page.mouse.click(box.x + box.width - 20, box.y + 20)
      }
    }
  }

  await page.getByRole("button", { name: /Compare Files/i }).click()
  const appErrorHeading = page.getByText("Something Went Wrong", { exact: false })
  if (await appErrorHeading.isVisible().catch(() => false)) {
    throw new Error("App entered error boundary before overlay interaction")
  }
  await expect(page.getByRole("tab", { name: /^Overlay/i })).toBeVisible()
  await page.getByRole("tab", { name: /^Overlay/i }).click()

  await expect(page.getByRole("button", { name: /^New$/i })).toBeVisible({ timeout: 30000 })
  await expect(page.getByRole("button", { name: /^Duplicate$/i })).toBeVisible()
  await expect(page.getByRole("button", { name: /^Pin$/i })).toBeVisible()
  await expect(page.getByRole("button", { name: /^Export$/i })).toBeVisible()

  // D1: new graph instance creates additional independent graph instance.
  await page.getByRole("button", { name: /^New$/i }).click()
  let state = await getPersistedStore(page)
  const countAfterNew = state.state.fcsCompareGraphInstances?.length ?? 0
  expect(countAfterNew).toBeGreaterThanOrEqual(2)

  // D2: duplicate and prove axis isolation via axisMode mutation.
  await page.getByRole("button", { name: /^Duplicate$/i }).click()
  state = await getPersistedStore(page)
  const instancesAfterDuplicate = state.state.fcsCompareGraphInstances ?? []
  expect(instancesAfterDuplicate.length).toBeGreaterThanOrEqual(3)

  const activeId = state.state.activeFCSCompareGraphInstanceId
  const activeInstance = instancesAfterDuplicate.find((instance) => instance.id === activeId)
  expect(activeInstance).toBeTruthy()

  // Change active duplicated graph axis mode.
  await page.getByRole("button", { name: /Per-file Axis/i }).click()
  state = await getPersistedStore(page)
  const afterModeChange = state.state.fcsCompareGraphInstances ?? []
  const changed = afterModeChange.find((instance) => instance.id === activeId)
  expect(changed?.axisMode).toBe("per-file")

  // Select a different graph and verify it stayed unchanged (unified).
  const otherInstance = afterModeChange.find((instance) => instance.id !== activeId)
  expect(otherInstance).toBeTruthy()

  const unchanged = afterModeChange.find((instance) => instance.id === otherInstance!.id)
  expect(unchanged?.axisMode).toBe("unified")

  const finalInstances = afterModeChange

  // D3: pin compare graph and verify payload persisted.
  await page.getByRole("button", { name: /^Pin$/i }).click()
  state = await getPersistedStore(page)
  const pinned = state.state.pinnedCharts ?? []
  expect(pinned.length).toBeGreaterThanOrEqual(1)
  const lastPinned = pinned[pinned.length - 1]
  expect(lastPinned.title).toContain("Scatter Overlay")

  // D4: maximize/restore toggles instance state.
  await page.keyboard.press("Escape").catch(() => {})
  const toggleButton = page.getByRole("button", { name: /^(Maximize|Restore)$/i }).first()
  await expect(toggleButton).toBeVisible({ timeout: 30000 })
  const initialLabel = ((await toggleButton.textContent()) || "").trim().toLowerCase()
  let observedMaximizedState = false

  await toggleButton.click({ force: true })
  state = await getPersistedStore(page)
  const currentActiveId = state.state.activeFCSCompareGraphInstanceId
  const afterFirstToggle = (state.state.fcsCompareGraphInstances ?? []).find((instance) => instance.id === currentActiveId)

  if (initialLabel.includes("maximize")) {
    expect(afterFirstToggle?.isMaximized).toBeTruthy()
    observedMaximizedState = Boolean(afterFirstToggle?.isMaximized)
    await page.getByRole("button", { name: /^Restore$/i }).click({ force: true })
  } else {
    expect(afterFirstToggle?.isMaximized).toBeFalsy()
    await page.getByRole("button", { name: /^Maximize$/i }).click({ force: true })
    state = await getPersistedStore(page)
    const afterSecondToggle = (state.state.fcsCompareGraphInstances ?? []).find((instance) => instance.id === currentActiveId)
    expect(afterSecondToggle?.isMaximized).toBeTruthy()
    observedMaximizedState = Boolean(afterSecondToggle?.isMaximized)
    await page.getByRole("button", { name: /^Restore$/i }).click({ force: true })
  }

  state = await getPersistedStore(page)
  const restored = (state.state.fcsCompareGraphInstances ?? []).find((instance) => instance.id === currentActiveId)
  expect(restored?.isMaximized).toBeFalsy()
  const d4MaximizeRestorePassed = observedMaximizedState && restored?.isMaximized === false

  // D4 export: verify csv download event.
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: /^Export$/i }).click(),
  ])
  const suggestedName = download.suggestedFilename()
  expect(suggestedName).toContain("overlay")

  const outDir = path.resolve("temp/perf-reports")
  fs.mkdirSync(outDir, { recursive: true })

  const checklist = {
    timestamp: new Date().toISOString(),
    checks: {
      d1_graph_instance_created: countAfterNew >= 2,
      d2_duplicate_isolation_axis_mode: Boolean(changed?.axisMode === "per-file" && unchanged?.axisMode === "unified"),
      d3_pin_payload_persisted: pinned.length >= 1,
      d4_maximize_restore: d4MaximizeRestorePassed,
      d4_export_download: suggestedName.toLowerCase().includes("overlay"),
    },
    evidence: {
      graphInstanceCount: finalInstances.length,
      pinnedCount: pinned.length,
      exportedFilename: suggestedName,
    },
  }

  fs.writeFileSync(path.join(outDir, "fcs-compare-controls-verification.json"), JSON.stringify(checklist, null, 2), "utf-8")
  await page.screenshot({ path: path.join(outDir, "fcs-compare-controls-verification.png"), fullPage: true })

  expect(Object.values(checklist.checks).every(Boolean)).toBeTruthy()
})
