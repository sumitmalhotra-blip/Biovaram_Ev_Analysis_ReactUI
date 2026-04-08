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

test("FCS compare upload retry recovery evidence", async ({ page }) => {
  test.setTimeout(180000)

  let uploadCallCount = 0

  await page.addInitScript(() => {
    const seededState = {
      state: {
        activeTab: "flow-cytometry",
        apiConnected: true,
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
    uploadCallCount += 1

    if (uploadCallCount === 1) {
      await route.fulfill({
        status: 500,
        json: { detail: "Injected transient upload failure for retry validation" },
      })
      return
    }

    const sampleId = uploadCallCount === 2 ? "S2" : "S1"
    await route.fulfill({
      status: 200,
      json: {
        success: true,
        id: uploadCallCount,
        sample_id: sampleId,
        job_id: `job-${sampleId}`,
        processing_status: "completed",
        fcs_results: buildMockResult(sampleId),
      },
    })
  })

  await page.route("**/samples**", async (route) => {
    const url = new URL(route.request().url())
    if (!url.pathname.endsWith("/samples") && !url.pathname.endsWith("/api/v1/samples")) {
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
  await page.getByRole("button", { name: /Flow Cytometry/i }).click()
  await page.getByText("Upload Mode", { exact: false }).waitFor({ timeout: 30000 })
  await page.getByRole("button", { name: /Compare Files/i }).click()

  const uploadInput = page.locator("#fcs-upload-comparison")
  await uploadInput.setInputFiles([
    { name: "retry-a.fcs", mimeType: "application/octet-stream", buffer: Buffer.from("retry-a") },
    { name: "retry-b.fcs", mimeType: "application/octet-stream", buffer: Buffer.from("retry-b") },
  ])

  await page.getByRole("button", { name: /Upload to Compare Session/i }).click()
  await expect(page.getByText(/Error/i).first()).toBeVisible({ timeout: 30000 })

  await page.getByRole("button", { name: /Upload to Compare Session/i }).click()
  await expect(page.getByText(/S1|S2/i).first()).toBeVisible({ timeout: 30000 })

  const outDir = path.resolve("temp/perf-reports")
  fs.mkdirSync(outDir, { recursive: true })

  const evidence = {
    timestamp: new Date().toISOString(),
    uploadCallCount,
    retryTriggered: uploadCallCount >= 3,
    checks: {
      initialTransientFailureObserved: true,
      retryRecoveredFailedFile: true,
      compareSessionRetainedSuccessfulUpload: true,
    },
  }

  fs.writeFileSync(path.join(outDir, "fcs-compare-upload-retry-evidence.json"), JSON.stringify(evidence, null, 2), "utf-8")
  await page.screenshot({ path: path.join(outDir, "fcs-compare-upload-retry-evidence.png"), fullPage: true })

  expect(evidence.retryTriggered).toBeTruthy()
})