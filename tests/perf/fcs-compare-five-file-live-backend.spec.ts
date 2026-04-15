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
      selectedCount: selected.length,
      compareItemMetaCount: Object.keys(meta).length,
      backendSampleIds,
      duplicateBackendSampleIds,
      duplicateBackendCount: duplicateBackendSampleIds.length,
    }
  })

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
    },
    warningGuard: {
      threshold: 4,
      warningTypeCountsByStep,
      maxWarningTypeCount,
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
    "",
    "## Checks",
    `- allFiveLiveUploadsSucceeded: ${evidence.checks.allFiveLiveUploadsSucceeded}`,
    `- fiveCompareItemsRetained: ${evidence.checks.fiveCompareItemsRetained}`,
    `- compareMetaAligned: ${evidence.checks.compareMetaAligned}`,
    `- duplicateBackendIdsObserved: ${evidence.checks.duplicateBackendIdsObserved}`,
    `- normalizationWarningTypesBounded: ${evidence.checks.normalizationWarningTypesBounded}`,
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
})
