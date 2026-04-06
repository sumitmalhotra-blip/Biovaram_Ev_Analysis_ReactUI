# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: perf\fcs-compare-controls-verification.spec.ts >> FCS compare controls verification checklist
- Location: tests\perf\fcs-compare-controls-verification.spec.ts:70:5

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: expect.toBeVisible: Target page, context or browser has been closed
```

# Test source

```ts
  120 |           selectedSampleIds: ["S1", "S2"],
  121 |           visibleSampleIds: ["S1", "S2"],
  122 |           primarySampleId: "S1",
  123 |           resultsBySampleId: {},
  124 |           scatterBySampleId: {},
  125 |           loadingBySampleId: {},
  126 |           errorBySampleId: {},
  127 |           maxVisibleOverlays: 8,
  128 |         },
  129 |         overlayConfig: {
  130 |           enabled: true,
  131 |           showBothHistograms: true,
  132 |           showOverlaidScatter: true,
  133 |           showOverlaidTheory: true,
  134 |           showOverlaidDiameter: true,
  135 |           primaryColor: "#7c3aed",
  136 |           secondaryColor: "#f97316",
  137 |           primaryLabel: "Primary",
  138 |           secondaryLabel: "Comparison",
  139 |           primaryOpacity: 0.7,
  140 |           secondaryOpacity: 0.5,
  141 |         },
  142 |       },
  143 |       version: 0,
  144 |     }
  145 | 
  146 |     window.sessionStorage.setItem("ev-analysis-storage-v2", JSON.stringify(seededState))
  147 |   })
  148 | 
  149 |   await page.route("**/health", async (route) => {
  150 |     await route.fulfill({ status: 200, json: { status: "ok", database: "ok", timestamp: new Date().toISOString() } })
  151 |   })
  152 | 
  153 |   await page.route("**/auth/login", async (route) => {
  154 |     await route.fulfill({
  155 |       status: 200,
  156 |       json: {
  157 |         access_token: "mock-token",
  158 |         user: {
  159 |           id: 1,
  160 |           name: "Lab User",
  161 |           email: "lab@biovaram.local",
  162 |           role: "researcher",
  163 |           organization: "BioVaram Lab",
  164 |         },
  165 |       },
  166 |     })
  167 |   })
  168 | 
  169 |   await page.route("**/api/v1/samples/*/fcs", async (route) => {
  170 |     const url = route.request().url()
  171 |     const sampleId = url.split("/samples/")[1]?.split("/")[0] || "S1"
  172 |     await route.fulfill({ status: 200, json: { sample_id: sampleId, results: [buildMockResult(sampleId)] } })
  173 |   })
  174 | 
  175 |   await page.route("**/api/v1/samples/*/scatter-data**", async (route) => {
  176 |     const url = route.request().url()
  177 |     const sampleId = url.split("/samples/")[1]?.split("/")[0] || "S1"
  178 |     await route.fulfill({ status: 200, json: { sample_id: sampleId, ...buildMockScatter() } })
  179 |   })
  180 | 
  181 |   await page.goto("/")
  182 | 
  183 |   await page.getByText("Upload Mode", { exact: false }).waitFor({ timeout: 30000 })
  184 |   const experimentalModal = page.getByRole("dialog", { name: /Experimental Conditions/i })
  185 |   if (await experimentalModal.isVisible({ timeout: 2000 }).catch(() => false)) {
  186 |     await page.keyboard.press("Escape")
  187 | 
  188 |     if (await experimentalModal.isVisible().catch(() => false)) {
  189 |       const closeCandidates = [
  190 |         page.getByRole("button", { name: /^Close$/i }).first(),
  191 |         page.getByRole("button", { name: /^Cancel$/i }).first(),
  192 |         page.getByRole("button", { name: /^Skip$/i }).first(),
  193 |         page.getByRole("button", { name: /^×$/i }).first(),
  194 |         page.locator("[role='dialog'] button").first(),
  195 |       ]
  196 | 
  197 |       for (const candidate of closeCandidates) {
  198 |         if (await candidate.isVisible().catch(() => false)) {
  199 |           await candidate.click({ force: true })
  200 |           if (!(await experimentalModal.isVisible().catch(() => false))) {
  201 |             break
  202 |           }
  203 |         }
  204 |       }
  205 |     }
  206 | 
  207 |     if (await experimentalModal.isVisible().catch(() => false)) {
  208 |       const box = await experimentalModal.boundingBox()
  209 |       if (box) {
  210 |         await page.mouse.click(box.x + box.width - 20, box.y + 20)
  211 |       }
  212 |     }
  213 |   }
  214 | 
  215 |   await page.getByRole("button", { name: /Compare Files/i }).click()
  216 |   const appErrorHeading = page.getByText("Something Went Wrong", { exact: false })
  217 |   if (await appErrorHeading.isVisible().catch(() => false)) {
  218 |     throw new Error("App entered error boundary before overlay interaction")
  219 |   }
> 220 |   await expect(page.getByRole("tab", { name: /^Overlay/i })).toBeVisible()
      |                                                              ^ Error: expect.toBeVisible: Target page, context or browser has been closed
  221 |   await page.getByRole("tab", { name: /^Overlay/i }).click()
  222 | 
  223 |   await expect(page.getByRole("button", { name: /^New$/i })).toBeVisible({ timeout: 30000 })
  224 |   await expect(page.getByRole("button", { name: /^Duplicate$/i })).toBeVisible()
  225 |   await expect(page.getByRole("button", { name: /^Pin$/i })).toBeVisible()
  226 |   await expect(page.getByRole("button", { name: /^Export$/i })).toBeVisible()
  227 | 
  228 |   // D1: new graph instance creates additional independent graph instance.
  229 |   await page.getByRole("button", { name: /^New$/i }).click()
  230 |   let state = await getPersistedStore(page)
  231 |   const countAfterNew = state.state.fcsCompareGraphInstances?.length ?? 0
  232 |   expect(countAfterNew).toBeGreaterThanOrEqual(2)
  233 | 
  234 |   // D2: duplicate and prove axis isolation via axisMode mutation.
  235 |   await page.getByRole("button", { name: /^Duplicate$/i }).click()
  236 |   state = await getPersistedStore(page)
  237 |   const instancesAfterDuplicate = state.state.fcsCompareGraphInstances ?? []
  238 |   expect(instancesAfterDuplicate.length).toBeGreaterThanOrEqual(3)
  239 | 
  240 |   const activeId = state.state.activeFCSCompareGraphInstanceId
  241 |   const activeInstance = instancesAfterDuplicate.find((instance) => instance.id === activeId)
  242 |   expect(activeInstance).toBeTruthy()
  243 | 
  244 |   // Change active duplicated graph axis mode.
  245 |   await page.getByRole("button", { name: /Per-file Axis/i }).click()
  246 |   state = await getPersistedStore(page)
  247 |   const afterModeChange = state.state.fcsCompareGraphInstances ?? []
  248 |   const changed = afterModeChange.find((instance) => instance.id === activeId)
  249 |   expect(changed?.axisMode).toBe("per-file")
  250 | 
  251 |   // Select a different graph and verify it stayed unchanged (unified).
  252 |   const otherInstance = afterModeChange.find((instance) => instance.id !== activeId)
  253 |   expect(otherInstance).toBeTruthy()
  254 | 
  255 |   const unchanged = afterModeChange.find((instance) => instance.id === otherInstance!.id)
  256 |   expect(unchanged?.axisMode).toBe("unified")
  257 | 
  258 |   const finalInstances = afterModeChange
  259 | 
  260 |   // D3: pin compare graph and verify payload persisted.
  261 |   await page.getByRole("button", { name: /^Pin$/i }).click()
  262 |   state = await getPersistedStore(page)
  263 |   const pinned = state.state.pinnedCharts ?? []
  264 |   expect(pinned.length).toBeGreaterThanOrEqual(1)
  265 |   const lastPinned = pinned[pinned.length - 1]
  266 |   expect(lastPinned.title).toContain("Scatter Overlay")
  267 | 
  268 |   // D4: maximize/restore toggles instance state.
  269 |   await page.keyboard.press("Escape").catch(() => {})
  270 |   const toggleButton = page.getByRole("button", { name: /^(Maximize|Restore)$/i }).first()
  271 |   await expect(toggleButton).toBeVisible({ timeout: 30000 })
  272 |   const initialLabel = ((await toggleButton.textContent()) || "").trim().toLowerCase()
  273 |   let observedMaximizedState = false
  274 | 
  275 |   await toggleButton.click({ force: true })
  276 |   state = await getPersistedStore(page)
  277 |   const currentActiveId = state.state.activeFCSCompareGraphInstanceId
  278 |   const afterFirstToggle = (state.state.fcsCompareGraphInstances ?? []).find((instance) => instance.id === currentActiveId)
  279 | 
  280 |   if (initialLabel.includes("maximize")) {
  281 |     expect(afterFirstToggle?.isMaximized).toBeTruthy()
  282 |     observedMaximizedState = Boolean(afterFirstToggle?.isMaximized)
  283 |     await page.getByRole("button", { name: /^Restore$/i }).click({ force: true })
  284 |   } else {
  285 |     expect(afterFirstToggle?.isMaximized).toBeFalsy()
  286 |     await page.getByRole("button", { name: /^Maximize$/i }).click({ force: true })
  287 |     state = await getPersistedStore(page)
  288 |     const afterSecondToggle = (state.state.fcsCompareGraphInstances ?? []).find((instance) => instance.id === currentActiveId)
  289 |     expect(afterSecondToggle?.isMaximized).toBeTruthy()
  290 |     observedMaximizedState = Boolean(afterSecondToggle?.isMaximized)
  291 |     await page.getByRole("button", { name: /^Restore$/i }).click({ force: true })
  292 |   }
  293 | 
  294 |   state = await getPersistedStore(page)
  295 |   const restored = (state.state.fcsCompareGraphInstances ?? []).find((instance) => instance.id === currentActiveId)
  296 |   expect(restored?.isMaximized).toBeFalsy()
  297 |   const d4MaximizeRestorePassed = observedMaximizedState && restored?.isMaximized === false
  298 | 
  299 |   // D4 export: verify csv download event.
  300 |   const [download] = await Promise.all([
  301 |     page.waitForEvent("download"),
  302 |     page.getByRole("button", { name: /^Export$/i }).click(),
  303 |   ])
  304 |   const suggestedName = download.suggestedFilename()
  305 |   expect(suggestedName).toContain("overlay")
  306 | 
  307 |   const outDir = path.resolve("temp/perf-reports")
  308 |   fs.mkdirSync(outDir, { recursive: true })
  309 | 
  310 |   const checklist = {
  311 |     timestamp: new Date().toISOString(),
  312 |     checks: {
  313 |       d1_graph_instance_created: countAfterNew >= 2,
  314 |       d2_duplicate_isolation_axis_mode: Boolean(changed?.axisMode === "per-file" && unchanged?.axisMode === "unified"),
  315 |       d3_pin_payload_persisted: pinned.length >= 1,
  316 |       d4_maximize_restore: d4MaximizeRestorePassed,
  317 |       d4_export_download: suggestedName.toLowerCase().includes("overlay"),
  318 |     },
  319 |     evidence: {
  320 |       graphInstanceCount: finalInstances.length,
```