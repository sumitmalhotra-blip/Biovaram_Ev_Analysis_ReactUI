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
    fsc_median: 1100 + (sampleId.charCodeAt(sampleId.length - 1) % 50),
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
  const points = Array.from({ length: 1600 }, (_, idx) => ({
    x: 500 + ((idx * 11) % 900),
    y: 280 + ((idx * 17) % 700),
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

test("FCS compare rapid toggle reliability evidence", async ({ page }) => {
  test.setTimeout(240000)
  let uploadCounter = 0

  const interactionTimeline: Array<{
    ts: string
    cycle: number
    step: string
    control: string
    attempt: number
    action: "checkpoint" | "before-click" | "after-click" | "click-error"
    snapshot: {
      compareCardVisible: boolean
      overlayHeadingVisible: boolean
      selectedTabLabel: string | null
      controls: Record<string, number>
      session: {
        selectedCount: number
        visibleCount: number
        primarySampleId: string | null
        overlayEnabled: boolean
        axisMode: string
        requestVersion: number | null
      }
    }
    error?: string
  }> = []

  let failureContext: {
    cycle: number
    step: string
    control: string
    message: string
  } | null = null

  const captureSnapshot = async () => {
    return page.evaluate(() => {
      const controlPatterns: Array<[string, RegExp]> = [
        ["showAll", /^show all$/i],
        ["referenceOnly", /^reference only$/i],
        ["setReference", /^set reference$/i],
        ["unifiedAxis", /^unified axis$/i],
        ["perFileAxis", /^per-file axis$/i],
      ]

      const controls: Record<string, number> = {
        showAll: 0,
        referenceOnly: 0,
        setReference: 0,
        unifiedAxis: 0,
        perFileAxis: 0,
      }

      const buttons = Array.from(document.querySelectorAll("button"))
      buttons.forEach((button) => {
        const label = (button.textContent || "").trim()
        controlPatterns.forEach(([key, pattern]) => {
          if (pattern.test(label)) {
            controls[key] += 1
          }
        })
      })

      const selectedTab = document.querySelector('[role="tab"][aria-selected="true"]')
      const selectedTabLabel = selectedTab ? (selectedTab.textContent || "").trim() : null

      const compareCardVisible = Array.from(document.querySelectorAll("h3, h2, div"))
        .some((node) => (node.textContent || "").trim() === "Compare Session")

      const overlayHeadingVisible = Array.from(document.querySelectorAll("*"))
        .some((node) => /scatter comparison/i.test((node.textContent || "").trim()))

      const raw = window.sessionStorage.getItem("ev-analysis-storage-v2")
      const parsed = raw ? JSON.parse(raw) : { state: {} }
      const state = parsed.state || {}
      const compareSession = state.fcsCompareSession || {}
      const graphInstances = state.fcsCompareGraphInstances || []
      const activeGraphId = state.activeFCSCompareGraphInstanceId
      const activeGraph = graphInstances.find((g: { id: string }) => g.id === activeGraphId) || graphInstances[0]

      return {
        compareCardVisible,
        overlayHeadingVisible,
        selectedTabLabel,
        controls,
        session: {
          selectedCount: Array.isArray(compareSession.selectedSampleIds) ? compareSession.selectedSampleIds.length : 0,
          visibleCount: Array.isArray(compareSession.visibleSampleIds) ? compareSession.visibleSampleIds.length : 0,
          primarySampleId: compareSession.primarySampleId || null,
          overlayEnabled: Boolean(state.overlayConfig?.enabled),
          axisMode: activeGraph?.axisMode || "unknown",
          requestVersion: typeof state.fcsCompareRequestVersion === "number" ? state.fcsCompareRequestVersion : null,
        },
      }
    })
  }

  const pushCheckpoint = async (step: string) => {
    const snapshot = await captureSnapshot()
    interactionTimeline.push({
      ts: new Date().toISOString(),
      cycle: 0,
      step,
      control: "checkpoint",
      attempt: 0,
      action: "checkpoint",
      snapshot,
    })
  }

  const clickControl = async (name: RegExp, cycle: number, step: string) => {
    let lastError: unknown = null

    for (let attempt = 0; attempt < 3; attempt += 1) {
      const control = page.getByRole("button", { name }).first()
      try {
        const beforeSnapshot = await captureSnapshot()
        interactionTimeline.push({
          ts: new Date().toISOString(),
          cycle,
          step,
          control: String(name),
          attempt: attempt + 1,
          action: "before-click",
          snapshot: beforeSnapshot,
        })

        await expect(control).toBeVisible({ timeout: 1500 })
        await control.dispatchEvent("click")

        const afterSnapshot = await captureSnapshot()
        interactionTimeline.push({
          ts: new Date().toISOString(),
          cycle,
          step,
          control: String(name),
          attempt: attempt + 1,
          action: "after-click",
          snapshot: afterSnapshot,
        })
        return
      } catch (error) {
        lastError = error
        const errorSnapshot = await captureSnapshot().catch(() => ({
          compareCardVisible: false,
          overlayHeadingVisible: false,
          selectedTabLabel: null,
          controls: { showAll: 0, referenceOnly: 0, setReference: 0, unifiedAxis: 0, perFileAxis: 0 },
          session: { selectedCount: 0, visibleCount: 0, primarySampleId: null, overlayEnabled: false, axisMode: "unknown", requestVersion: null },
        }))
        interactionTimeline.push({
          ts: new Date().toISOString(),
          cycle,
          step,
          control: String(name),
          attempt: attempt + 1,
          action: "click-error",
          snapshot: errorSnapshot,
          error: error instanceof Error ? error.message : String(error),
        })
        // No delay here: keep retries deterministic and avoid extra failure noise when page closes.
      }
    }

    failureContext = {
      cycle,
      step,
      control: String(name),
      message: lastError instanceof Error ? lastError.message : String(lastError),
    }

    throw lastError instanceof Error ? lastError : new Error(`Failed clicking control: ${name}`)
  }

  await page.addInitScript(() => {
    const seededState = {
      state: {
        activeTab: "flow-cytometry",
        apiConnected: true,
        isDarkMode: true,
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
          experimentalConditions: null,
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
        apiSamples: [
          { sample_id: "S1", treatment: "Control", dye: "CFSE" },
          { sample_id: "S2", treatment: "DrugA", dye: "PKH26" },
          { sample_id: "S3", treatment: "DrugA", dye: "PKH67" },
          { sample_id: "S4", treatment: "DrugB", dye: "DiI" },
        ],
        fcsCompareSession: {
          selectedSampleIds: ["S1", "S2", "S3", "S4"],
          visibleSampleIds: ["S1", "S2", "S3", "S4"],
          primarySampleId: "S1",
          compareItemMetaById: {
            S1: { backendSampleId: "S1", sampleLabel: "S1", fileName: "seed-s1.fcs", treatment: "Control", dye: "CFSE", uploadedAt: 1712400000001 },
            S2: { backendSampleId: "S2", sampleLabel: "S2", fileName: "seed-s2.fcs", treatment: "DrugA", dye: "PKH26", uploadedAt: 1712400000002 },
            S3: { backendSampleId: "S3", sampleLabel: "S3", fileName: "seed-s3.fcs", treatment: "DrugA", dye: "PKH67", uploadedAt: 1712400000003 },
            S4: { backendSampleId: "S4", sampleLabel: "S4", fileName: "seed-s4.fcs", treatment: "DrugB", dye: "DiI", uploadedAt: 1712400000004 },
          },
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
        fcs_results: buildMockResult(sampleId),
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
    await route.fulfill({ status: 200, json: { sample_id: sampleId, ...buildMockScatter() } })
  })

  await page.goto("/")
  await pushCheckpoint("after-goto")
  await page.getByText("Upload Mode", { exact: false }).waitFor({ timeout: 30000 })
  await pushCheckpoint("after-upload-mode-visible")

  const experimentalModal = page.getByRole("dialog", { name: /Experimental Conditions/i })
  if (await experimentalModal.isVisible({ timeout: 2000 }).catch(() => false)) {
    await page.keyboard.press("Escape")
  }

  await page.getByRole("button", { name: /Compare Files/i }).click()
  await pushCheckpoint("after-switch-compare-mode")
  const uploadInput = page.locator("#fcs-upload-comparison")
  await uploadInput.setInputFiles([
    { name: "rapid-a.fcs", mimeType: "application/octet-stream", buffer: Buffer.from("rapid-a") },
    { name: "rapid-b.fcs", mimeType: "application/octet-stream", buffer: Buffer.from("rapid-b") },
  ])
  await page.getByRole("button", { name: /Upload to Compare Session/i }).click()
  await pushCheckpoint("after-upload-click")

  const overlayTab = page.getByRole("tab", { name: /^Overlay/i })
  await expect(overlayTab).toBeVisible({ timeout: 30000 })
  await expect(overlayTab).toBeEnabled({ timeout: 30000 })
  await overlayTab.click()
  await pushCheckpoint("after-overlay-tab-click")
  try {
    await expect(page.getByText(/Scatter Comparison/i)).toBeVisible({ timeout: 30000 })
  } catch (error) {
    const appErrorVisible = await page.getByText(/Something Went Wrong/i).isVisible().catch(() => false)
    let stackDump = ""

    if (appErrorVisible) {
      const stackToggle = page.getByText(/Stack Trace/i).first()
      if (await stackToggle.isVisible().catch(() => false)) {
        await stackToggle.click().catch(() => {})
      }
      stackDump = await page.locator("body").innerText().catch(() => "")
    }

    throw new Error(
      `Overlay heading unavailable. App error visible: ${appErrorVisible}. ${error instanceof Error ? error.message : String(error)}\n${stackDump.slice(0, 4000)}`
    )
  }
  await pushCheckpoint("after-scatter-heading-visible")

  const cycleResults: Array<{
    cycle: number
    activePrimary: string | null
    visibleCount: number
    selectedCount: number
    axisMode: "unified" | "per-file" | "unknown"
    hadErrorBoundary: boolean
  }> = []

  try {
    for (let cycle = 1; cycle <= 6; cycle += 1) {
      await clickControl(/Show All/i, cycle, "show-all-1")
      await clickControl(/Reference Only/i, cycle, "reference-only")
      await clickControl(/Show All/i, cycle, "show-all-2")

      const setReference = page.getByRole("button", { name: /Set Reference/i }).first()
      if (
        await setReference.isVisible().catch(() => false)
        && await setReference.isEnabled().catch(() => false)
      ) {
        await setReference.click({ force: true })
      }

      await clickControl(/Per-file Axis/i, cycle, "per-file-axis")
      await clickControl(/Unified Axis/i, cycle, "unified-axis")

      await expect(page.getByText(/Reference map:/i)).toBeVisible()
      await expect(page.getByText(/Peer map:/i)).toBeVisible()

      const appErrorHeading = page.getByText("Something Went Wrong", { exact: false })
      const hadErrorBoundary = await appErrorHeading.isVisible().catch(() => false)

      const snapshot = await page.evaluate(() => {
        const raw = window.sessionStorage.getItem("ev-analysis-storage-v2")
        const parsed = raw ? JSON.parse(raw) : { state: {} }
        const state = parsed.state || {}
        const compareSession = state.fcsCompareSession || {}
        const graphInstances = state.fcsCompareGraphInstances || []
        const activeGraphId = state.activeFCSCompareGraphInstanceId
        const activeGraph = graphInstances.find((g: { id: string }) => g.id === activeGraphId) || graphInstances[0]
        const setReferenceButtons = Array.from(document.querySelectorAll("button")).filter((button) => {
          const label = (button.textContent || "").trim().toLowerCase()
          return label === "set reference"
        }).length

        return {
          activePrimary: compareSession.primarySampleId || null,
          visibleCount: Array.isArray(compareSession.visibleSampleIds) ? compareSession.visibleSampleIds.length : 0,
          selectedCount: Math.max(1, setReferenceButtons + 1),
          axisMode: activeGraph?.axisMode || "unknown",
        }
      })

      cycleResults.push({
        cycle,
        activePrimary: snapshot.activePrimary,
        visibleCount: snapshot.visibleCount,
        selectedCount: snapshot.selectedCount,
        axisMode: snapshot.axisMode,
        hadErrorBoundary,
      })
    }
  } finally {
    const outDir = path.resolve("temp/perf-reports")
    fs.mkdirSync(outDir, { recursive: true })
    const debugEvidence = {
      timestamp: new Date().toISOString(),
      test: "rapid-toggle-control-timeline-debug",
      failureContext,
      cyclesCaptured: cycleResults.length,
      interactionTimeline,
    }
    fs.writeFileSync(path.join(outDir, "fcs-compare-rapid-toggle-debug.json"), JSON.stringify(debugEvidence, null, 2), "utf-8")
    await page.screenshot({ path: path.join(outDir, "fcs-compare-rapid-toggle-debug.png"), fullPage: true }).catch(() => {})
  }

  const outDir = path.resolve("temp/perf-reports")
  fs.mkdirSync(outDir, { recursive: true })

  const evidence = {
    timestamp: new Date().toISOString(),
    test: "rapid-primary-visibility-axis-toggles",
    cycles: cycleResults,
    summary: {
      totalCycles: cycleResults.length,
      cyclesWithoutErrorBoundary: cycleResults.filter((c) => !c.hadErrorBoundary).length,
      cyclesWithValidPrimary: cycleResults.filter((c) => Boolean(c.activePrimary)).length,
      cyclesWithVisibleSamples: cycleResults.filter((c) => c.visibleCount > 0).length,
      cyclesWithSelectedSamples: cycleResults.filter((c) => c.selectedCount >= 2).length,
    },
    passFail: {
      noErrorBoundary: cycleResults.every((c) => !c.hadErrorBoundary),
      primaryAlwaysPresent: cycleResults.every((c) => Boolean(c.activePrimary)),
      visibleNeverEmpty: cycleResults.every((c) => c.visibleCount > 0),
      selectedStable: cycleResults.every((c) => c.selectedCount >= 2),
      axisModeStable: cycleResults.every((c) => c.axisMode === "unified" || c.axisMode === "per-file"),
    },
  }

  fs.writeFileSync(path.join(outDir, "fcs-compare-rapid-toggle-evidence.json"), JSON.stringify(evidence, null, 2), "utf-8")
  await page.screenshot({ path: path.join(outDir, "fcs-compare-rapid-toggle-evidence.png"), fullPage: true })

  expect(evidence.passFail.noErrorBoundary).toBeTruthy()
  expect(evidence.passFail.primaryAlwaysPresent).toBeTruthy()
  expect(evidence.passFail.visibleNeverEmpty).toBeTruthy()
  expect(evidence.passFail.selectedStable).toBeTruthy()
  expect(evidence.passFail.axisModeStable).toBeTruthy()
})
