import { test, expect } from "@playwright/test"
import fs from "node:fs"
import path from "node:path"
import { buildNormalizationSummary, normalizeFCSChannels } from "../../lib/flow-cytometry/compare-normalization-adapter"

function toWarningTypeCount(warnings: string[]): number {
  const warningTypes = new Set<string>()
  warnings.forEach((warning) => {
    const separator = warning.indexOf(": ")
    const message = separator > 0 ? warning.slice(separator + 2) : warning
    warningTypes.add(message)
  })
  return warningTypes.size
}

test("FCS compare five-file live-backend checklist", async ({ page, request }) => {
  test.setTimeout(240000)

  const highPath = path.resolve("backend/nanoFACS/Nano Vis High.fcs")
  const lowPath = path.resolve("backend/nanoFACS/Nano Vis Low.fcs")

  expect(fs.existsSync(highPath)).toBeTruthy()
  expect(fs.existsSync(lowPath)).toBeTruthy()

  const highBuffer = fs.readFileSync(highPath)
  const lowBuffer = fs.readFileSync(lowPath)

  const uploadPlan = [
    { fileName: "Nano Vis High.fcs", buffer: highBuffer },
    { fileName: "Nano Vis High.fcs", buffer: highBuffer },
    { fileName: "Nano Vis Low.fcs", buffer: lowBuffer },
    { fileName: "Nano Vis Low.fcs", buffer: lowBuffer },
    { fileName: "Nano Vis High.fcs", buffer: highBuffer },
  ]

  const uploadResponses: Array<{
    index: number
    ok: boolean
    status: number
    sample_id?: string
    id?: number | string
    fcs_results?: Record<string, unknown> | null
    error?: string
  }> = []

  for (let index = 0; index < uploadPlan.length; index += 1) {
    const upload = uploadPlan[index]
    const response = await request.post("http://localhost:8000/api/v1/upload/fcs", {
      multipart: {
        file: {
          name: upload.fileName,
          mimeType: "application/octet-stream",
          buffer: upload.buffer,
        },
        operator: "Playwright",
      },
    })

    let payload: any = null
    try {
      payload = await response.json()
    } catch {
      payload = null
    }

    uploadResponses.push({
      index: index + 1,
      ok: response.ok(),
      status: response.status(),
      sample_id: payload?.sample_id,
      id: payload?.id,
      fcs_results: payload?.fcs_results ?? null,
      error: payload?.detail,
    })
  }

  const successful = uploadResponses.filter((entry) => entry.ok && entry.sample_id)
  expect(successful.length).toBe(5)

  // Guard against warning-count regression: warning types should stay bounded as uploads grow.
  const warningTypeCountsByStep = successful.map((_, stepIndex) => {
    const schemas = successful
      .slice(0, stepIndex + 1)
      .map((entry, idx) => normalizeFCSChannels(`cmp-${idx + 1}`, (entry.fcs_results?.channels as string[] | undefined) ?? []))
    const summary = buildNormalizationSummary(schemas)
    return toWarningTypeCount(summary.warnings)
  })
  const maxWarningTypeCount = warningTypeCountsByStep.length > 0 ? Math.max(...warningTypeCountsByStep) : 0

  const compareItemIds = successful.map((_, idx) => `cmp-${idx + 1}`)
  const selectedSampleIds = [...compareItemIds]
  const visibleSampleIds = [...compareItemIds]

  const compareItemMetaById = successful.reduce<Record<string, any>>((acc, entry, idx) => {
    const compareItemId = compareItemIds[idx]
    acc[compareItemId] = {
      backendSampleId: entry.sample_id,
      sampleLabel: entry.sample_id,
      fileName: uploadPlan[idx].fileName,
      treatment: "CD81",
      dye: "None",
      uploadedAt: Date.now() + idx,
    }
    return acc
  }, {})

  const resultsBySampleId = successful.reduce<Record<string, any>>((acc, entry, idx) => {
    const compareItemId = compareItemIds[idx]
    acc[compareItemId] = entry.fcs_results ?? null
    return acc
  }, {})

  await page.addInitScript(({ selectedSampleIds, visibleSampleIds, compareItemMetaById, resultsBySampleId }) => {
    const seededState = {
      state: {
        activeTab: "flow-cytometry",
        apiConnected: true,
        fcsAnalysis: {
          file: null,
          sampleId: selectedSampleIds[0],
          results: resultsBySampleId[selectedSampleIds[0]] ?? null,
          anomalyData: null,
          isAnalyzing: false,
          error: null,
          experimentalConditions: null,
          fileMetadata: null,
          sizeRanges: [],
        },
        secondaryFcsAnalysis: {
          file: null,
          sampleId: selectedSampleIds[1] ?? null,
          results: resultsBySampleId[selectedSampleIds[1]] ?? null,
          anomalyData: null,
          isAnalyzing: false,
          error: null,
          scatterData: [],
          loadingScatter: false,
        },
        fcsCompareSession: {
          selectedSampleIds,
          visibleSampleIds,
          primarySampleId: selectedSampleIds[0],
          compareItemMetaById,
          resultsBySampleId,
          scatterBySampleId: {},
          loadingBySampleId: {},
          errorBySampleId: {},
          maxVisibleOverlays: 8,
        },
      },
      version: 0,
    }

    window.sessionStorage.setItem("ev-analysis-storage-v2", JSON.stringify(seededState))
  }, { selectedSampleIds, visibleSampleIds, compareItemMetaById, resultsBySampleId })

  await page.goto("/")

  await page.getByText("Upload Mode", { exact: false }).waitFor({ timeout: 30000 })
  const experimentalModal = page.getByRole("dialog", { name: /Experimental Conditions/i })
  if (await experimentalModal.isVisible({ timeout: 1500 }).catch(() => false)) {
    await page.keyboard.press("Escape")
  }

  const compareTriggers = [
    page.getByRole("button", { name: /Compare Files/i }).first(),
    page.getByText(/Compare Files/i).first(),
    page.getByRole("button", { name: /Compare/i }).first(),
  ]
  for (const trigger of compareTriggers) {
    if (await trigger.isVisible().catch(() => false)) {
      await trigger.click({ force: true })
      break
    }
  }

  const snapshot = await page.evaluate(() => {
    const raw = window.sessionStorage.getItem("ev-analysis-storage-v2")
    const parsed = raw ? JSON.parse(raw) : { state: {} }
    const compareSession = parsed.state?.fcsCompareSession || {}

    const selected = Array.isArray(compareSession.selectedSampleIds) ? compareSession.selectedSampleIds : []
    const meta = compareSession.compareItemMetaById || {}

    const backendSampleIds = selected
      .map((compareItemId: string) => meta?.[compareItemId]?.backendSampleId)
      .filter((value: unknown) => typeof value === "string") as string[]

    const duplicateBackendSampleIds = Array.from(
      new Set(backendSampleIds.filter((id, idx) => backendSampleIds.indexOf(id) !== idx)),
    )

    return {
      selectedSampleIds: selected,
      visibleSampleIds: Array.isArray(compareSession.visibleSampleIds) ? compareSession.visibleSampleIds : [],
      primarySampleId: typeof compareSession.primarySampleId === "string" ? compareSession.primarySampleId : null,
      fcsPrimarySampleId: typeof parsed.state?.fcsAnalysis?.sampleId === "string" ? parsed.state.fcsAnalysis.sampleId : null,
      selectedCount: selected.length,
      compareItemMetaCount: Object.keys(meta).length,
      backendSampleIds,
      duplicateBackendSampleIds,
      duplicateBackendCount: duplicateBackendSampleIds.length,
    }
  })

  // Pass-2 guard: multi-overlay must render all visible samples as distinct series.
  const overlayTab = page.getByRole("tab", { name: /^Overlay/i })
  await expect(overlayTab).toBeVisible({ timeout: 30000 })
  await overlayTab.click()

  const multiOverlayActiveBadge = page.getByText(/Multi-overlay Active/i).first()
  if (!(await multiOverlayActiveBadge.isVisible().catch(() => false))) {
    for (let attempt = 0; attempt < 4; attempt += 1) {
      const multiOverlayButton = page.getByRole("button", { name: /Multi-overlay/i }).first()
      if (!(await multiOverlayButton.isVisible().catch(() => false))) {
        continue
      }

      await multiOverlayButton.click({ force: true, timeout: 5000 }).catch(() => {})
      if (await multiOverlayActiveBadge.isVisible().catch(() => false)) {
        break
      }
    }
  }

  const overlaySeriesBadge = page.getByText(/Overlay\s+\d+\s+series/i).first()
  await expect(overlaySeriesBadge).toBeVisible({ timeout: 30000 })
  const overlayBadgeText = (await overlaySeriesBadge.textContent()) || ""
  const overlaySeriesMatch = overlayBadgeText.match(/Overlay\s+(\d+)\s+series/i)
  const overlaySeriesCount = overlaySeriesMatch ? Number(overlaySeriesMatch[1]) : 0
  const expectedVisibleSeriesCount = snapshot.visibleSampleIds.length
    + (snapshot.primarySampleId && !snapshot.visibleSampleIds.includes(snapshot.primarySampleId) ? 1 : 0)

  // Pass-2 guard: pin payload should include all visible sample IDs.
  await page.getByRole("button", { name: /^Pin$/i }).click()
  const pinSnapshot = await page.evaluate(() => {
    const raw = window.sessionStorage.getItem("ev-analysis-storage-v2")
    const parsed = raw ? JSON.parse(raw) : { state: {} }
    const visible = Array.isArray(parsed.state?.fcsCompareSession?.visibleSampleIds)
      ? parsed.state.fcsCompareSession.visibleSampleIds
      : []
    const scatterBySampleId = parsed.state?.fcsCompareSession?.scatterBySampleId || {}
    const visibleWithScatter = visible.filter((sampleId: string) => Array.isArray(scatterBySampleId[sampleId]) && scatterBySampleId[sampleId].length > 0)
    const pinnedCharts = Array.isArray(parsed.state?.pinnedCharts) ? parsed.state.pinnedCharts : []
    const lastPinned = pinnedCharts[pinnedCharts.length - 1]
    const pinnedSampleIds = Array.isArray(lastPinned?.data)
      ? Array.from(new Set(lastPinned.data.map((point: { sampleId?: string }) => point?.sampleId).filter((value: unknown): value is string => typeof value === "string" && value.length > 0)))
      : []
    return {
      visible,
      visibleWithScatter,
      pinnedSampleIds,
    }
  })

  // Pass-2 guard: export payload should include all visible sample IDs.
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: /^Export$/i }).click(),
  ])
  const downloadPath = await download.path()
  let exportedCsv = ""
  if (downloadPath) {
    exportedCsv = fs.readFileSync(downloadPath, "utf-8")
  }
  const exportContainsAllVisible = pinSnapshot.visibleWithScatter.every((sampleId) => exportedCsv.includes(`,${sampleId},`))

  const outDir = path.resolve("temp/perf-reports")
  fs.mkdirSync(outDir, { recursive: true })

  const evidence = {
    timestamp: new Date().toISOString(),
    test: "fcs-compare-five-file-live-backend-checklist",
    mode: "live-backend-non-mocked-uploader",
    uploadResponses,
    snapshot,
    checks: {
      allFiveLiveUploadsSucceeded: successful.length === 5,
      fiveCompareItemsRetained: snapshot.selectedCount === 5,
      compareMetaAligned: snapshot.compareItemMetaCount >= snapshot.selectedCount,
      duplicateBackendIdsObserved: snapshot.duplicateBackendCount > 0,
      normalizationWarningTypesBounded: maxWarningTypeCount <= 4,
      multiOverlaySeriesCountMatchesVisibleSamples: overlaySeriesCount === expectedVisibleSeriesCount,
      pinPayloadContainsAllVisibleSamples: pinSnapshot.visibleWithScatter.every((sampleId) => pinSnapshot.pinnedSampleIds.includes(sampleId)),
      exportContainsAllVisibleSamples: exportContainsAllVisible,
    },
    warningGuard: {
      threshold: 4,
      warningTypeCountsByStep,
      maxWarningTypeCount,
    },
    pass2OverlayGuards: {
      overlaySeriesCount,
      expectedVisibleSeriesCount,
      pinVisibleSampleIds: pinSnapshot.visible,
      pinVisibleWithScatter: pinSnapshot.visibleWithScatter,
      pinPayloadSampleIds: pinSnapshot.pinnedSampleIds,
      exportContainsAllVisible,
    },
  }

  fs.writeFileSync(
    path.join(outDir, "fcs-compare-five-file-live-backend-evidence.json"),
    JSON.stringify(evidence, null, 2),
    "utf-8",
  )

  const markdown = [
    "# FCS Compare Five-File Live Backend Evidence",
    "",
    `- Timestamp: ${evidence.timestamp}`,
    `- Mode: ${evidence.mode}`,
    `- Successful live uploads: ${successful.length}/${uploadResponses.length}`,
    `- Selected compare items: ${snapshot.selectedCount}`,
    `- compareItemMetaById keys: ${snapshot.compareItemMetaCount}`,
    `- Duplicate backend sample_id count: ${snapshot.duplicateBackendCount}`,
    `- Duplicate backend sample_id values: ${snapshot.duplicateBackendSampleIds.join(", ") || "none"}`,
    `- Warning type counts by cumulative upload step: ${evidence.warningGuard.warningTypeCountsByStep.join(" -> ")}`,
    `- Max warning type count observed: ${evidence.warningGuard.maxWarningTypeCount} (threshold ${evidence.warningGuard.threshold})`,
    `- Overlay visible series: ${evidence.pass2OverlayGuards.overlaySeriesCount}/${evidence.pass2OverlayGuards.expectedVisibleSeriesCount}`,
    `- Pin payload sample parity: ${evidence.checks.pinPayloadContainsAllVisibleSamples}`,
    `- Export payload sample parity: ${evidence.checks.exportContainsAllVisibleSamples}`,
    "",
    "## Checks",
    `- allFiveLiveUploadsSucceeded: ${evidence.checks.allFiveLiveUploadsSucceeded}`,
    `- fiveCompareItemsRetained: ${evidence.checks.fiveCompareItemsRetained}`,
    `- compareMetaAligned: ${evidence.checks.compareMetaAligned}`,
    `- duplicateBackendIdsObserved: ${evidence.checks.duplicateBackendIdsObserved}`,
    `- normalizationWarningTypesBounded: ${evidence.checks.normalizationWarningTypesBounded}`,
    `- multiOverlaySeriesCountMatchesVisibleSamples: ${evidence.checks.multiOverlaySeriesCountMatchesVisibleSamples}`,
    `- pinPayloadContainsAllVisibleSamples: ${evidence.checks.pinPayloadContainsAllVisibleSamples}`,
    `- exportContainsAllVisibleSamples: ${evidence.checks.exportContainsAllVisibleSamples}`,
  ].join("\n")

  fs.writeFileSync(path.join(outDir, "fcs-compare-five-file-live-backend-evidence.md"), markdown, "utf-8")
  await page.screenshot({
    path: path.join(outDir, "fcs-compare-five-file-live-backend-evidence.png"),
    fullPage: true,
  })

  expect(evidence.checks.allFiveLiveUploadsSucceeded).toBeTruthy()
  expect(evidence.checks.fiveCompareItemsRetained).toBeTruthy()
  expect(evidence.checks.compareMetaAligned).toBeTruthy()
  expect(evidence.checks.duplicateBackendIdsObserved).toBeTruthy()
  expect(evidence.checks.normalizationWarningTypesBounded).toBeTruthy()
  expect(evidence.checks.multiOverlaySeriesCountMatchesVisibleSamples).toBeTruthy()
  expect(evidence.checks.pinPayloadContainsAllVisibleSamples).toBeTruthy()
  expect(evidence.checks.exportContainsAllVisibleSamples).toBeTruthy()
})
