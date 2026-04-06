# NanoFCS Unified Multi-File Task Tracker
## Date: March 31, 2026
## Single Source of Truth for NanoFCS Compare Delivery

Status legend:
- [ ] Not started
- [~] In progress
- [x] Completed
- [!] Blocked

## 1. Tracker Scope
This tracker consolidates:
1. Previously pending NanoFCS/FCS compare tasks.
2. New principles-adoption tasks (Parvesh decisions + PHoNUPS-aligned additions).
3. Cross-file implementation work spanning frontend and backend.

Reference plan:
- docs/NANOFCS_PRINCIPLES_ADOPTION_MASTER_PLAN_MAR31_2026.md
- docs/NANOFCS_PARQUET_FIRST_EXECUTION_PLAN_APR02_2026.md

## 2. Global Constraints
1. Max selected compare files: 10.
2. Default visible overlays: 5.
3. Default axis mode: unified.
4. Per-file axis: opt-in, guarded by unit-compatibility rules.
5. No silent blank chart states.

## 2.1 Sprint Start Board (Current)
Immediate kickoff items for the active sprint. These items are marked In progress in the detailed tracker below.

| ID | Work Item | Owner | ETA | Status |
|---|---|---|---|---|
| FCS-A1 | Bounded compare loader | Frontend | Apr 1, 2026 | [x] |
| FCS-A2 | Request versioning and stale-response rejection | Frontend | Apr 1, 2026 | [x] |
| FCS-A3 | Deterministic chart state model | Frontend | Apr 1, 2026 | [x] |
| FCS-A4 | Axis fallback resolution | Frontend | Apr 5, 2026 | [x] |
| FCS-A5 | Dev telemetry and guardrails | Frontend | Apr 5, 2026 | [x] |

## 3. Master Workstream Tracker

### WS-A Reliability and Deterministic Loading (P0)

#### A1. Bounded compare loader
- ID: FCS-A1
- Status: [x]
- Owner: Frontend
- ETA: Apr 1, 2026
- Files:
  - hooks/use-api.ts
  - components/flow-cytometry/comparison-analysis-view.tsx
- Checklist:
  - [x] Add concurrency-limited compare loading for results and scatter.
  - [x] Prioritize visible samples before non-visible selected samples.
  - [x] Enforce unique capped sample list (max 10).
- Acceptance:
  - [x] 5-file compare loads without UI freeze.

#### A2. Request versioning and stale-response rejection
- ID: FCS-A2
- Status: [x]
- Owner: Frontend
- ETA: Apr 1, 2026
- Files:
  - hooks/use-api.ts
  - lib/store.ts
- Checklist:
  - [x] Add compare request version token.
  - [x] Ignore outdated async responses.
  - [x] Prevent rollback/flicker from stale writes.
- Acceptance:
  - [x] Rapid axis/toggle changes never show stale data.

#### A3. Deterministic chart state model
- ID: FCS-A3
- Status: [x]
- Owner: Frontend
- ETA: Apr 1, 2026
- Files:
  - components/flow-cytometry/comparison-analysis-view.tsx
  - components/flow-cytometry/overlay-histogram-chart.tsx
- Checklist:
  - [x] Enforce loading/error/empty/data states for every compare chart.
  - [x] Add per-file retry actions.
  - [x] Remove silent blank-state paths.
- Acceptance:
  - [x] Every chart always renders an explicit state.

#### A4. Axis fallback resolution
- ID: FCS-A4
- Status: [x]
- Owner: Frontend
- ETA: Apr 5, 2026
- Files:
  - components/flow-cytometry/analysis-results.tsx
  - components/flow-cytometry/comparison-analysis-view.tsx
- Checklist:
  - [x] Implement channel fallback order for missing axes.
  - [x] Surface fallback hints in UI.
- Acceptance:
  - [x] Mixed-channel files still render and remain interpretable.

#### A5. Dev telemetry and guardrails
- ID: FCS-A5
- Status: [x]
- Owner: Frontend
- ETA: Apr 5, 2026
- Files:
  - components/flow-cytometry/comparison-analysis-view.tsx
  - lib/store.ts
- Checklist:
  - [x] Add compare load timings and queue depth metrics.
  - [x] Add cache hit/miss/evict counters.
- Acceptance:
  - [x] Dev team can inspect compare performance in one view.

### WS-B Performance Foundation (P0)

#### B1. Workerized series generation
- ID: FCS-B1
- Status: [x]
- Files:
  - lib/workers/fcs-series.worker.ts
  - hooks/use-api.ts
  - components/flow-cytometry/charts/*
- Checklist:
  - [x] Implement scatter and histogram worker message contracts.
  - [x] Correlate responses with request IDs.
  - [x] Gracefully handle worker failures.
- Acceptance:
  - [x] Heavy transforms are removed from main-thread hot paths.

#### B2. Runtime LRU series cache
- ID: FCS-B2
- Status: [x]
- Files:
  - lib/fcs-series-cache-utils.ts
  - lib/store.ts
  - hooks/use-api.ts
  - components/flow-cytometry/overlay-histogram-chart.tsx
  - components/flow-cytometry/charts/*
- Checklist:
  - [x] Add deterministic cache keys.
  - [x] Add entry and memory limits with LRU eviction.
  - [x] Add config/version-driven invalidation.
- Acceptance:
  - [x] Repeated chart navigation reuses cached data with bounded memory.

#### B3. Progressive paint and LOD modes
- ID: FCS-B3
- Status: [x]
- Files:
  - components/flow-cytometry/comparison-analysis-view.tsx
  - components/flow-cytometry/charts/*
- Checklist:
  - [x] Render primary first.
  - [x] Stage overlays progressively.
  - [x] Use interactive-to-settled point cap transition.
- Acceptance:
  - [x] Time-to-first-chart and interaction smoothness improve under 5 files.
  - [x] Automated Playwright gate check recorded in temp/perf-reports/fcs-compare-gates-report.json.

#### B4. Point/bin caps with transparency
- ID: FCS-B4
- Status: [x]
- Files:
  - components/flow-cytometry/overlay-histogram-chart.tsx
  - components/flow-cytometry/charts/*
- Checklist:
  - [x] Enforce fixed bin counts.
  - [x] Enforce scatter point caps.
  - [x] Display high-density/downsample indicator.
- Acceptance:
  - [x] Large files remain usable without hidden approximation behavior.
  - [x] Histogram fixed-bin and downsample indicators verified in automated gate run screenshot.

### WS-C Multi-File Compare UX Completion (P1)

#### C1. Compare session store slice
- ID: FCS-C1
- Status: [x]
- Files:
  - lib/store.ts
- Checklist:
  - [x] Finalize selected/visible/primary/results/scatter/loading/error maps.
  - [x] Keep heavy maps non-persisted.
- Acceptance:
  - [x] Control state persists, heavy payloads do not.

#### C2. Batch compare upload flow
- ID: FCS-C2
- Status: [x]
- Files:
  - components/flow-cytometry/dual-file-upload-zone.tsx
  - hooks/use-api.ts
- Checklist:
  - [x] Replace dual-file upload assumptions with multi-file batch add.
  - [x] Show per-file upload status/errors.
  - [x] Auto-add successful files to compare session.
- Acceptance:
  - [x] Users can add 5-10 files in one compare session.

#### C3. Compare side-panel controls
- ID: FCS-C3
- Status: [x]
- Files:
  - components/flow-cytometry/comparison-analysis-view.tsx
- Checklist:
  - [x] Selected list with status badges.
  - [x] Visible toggles and quick actions.
  - [x] Clear-session behavior remains deterministic.
- Acceptance:
  - [x] Selected and visible subsets are independently manageable.

#### C4. Axis controls inside compare graph cards
- ID: FCS-C4
- Status: [x]
- Files:
  - components/flow-cytometry/charts/scatter-axis-selector.tsx
  - components/flow-cytometry/comparison-analysis-view.tsx
- Checklist:
  - [x] In-graph compact axis selector.
  - [x] Unified and per-file mode support.
- Acceptance:
  - [x] Users can change axis directly at chart context.

### WS-D Graph Tool Parity and Isolation (P1)

#### D1. Graph instance container model
- ID: FCS-D1
- Status: [x]
- Files:
  - components/flow-cytometry/comparison-analysis-view.tsx
  - lib/store.ts
- Checklist:
  - [x] Introduce graphInstances state with independent IDs.
  - [x] Bind chart cards to instance configs.
- Acceptance:
  - [x] Multiple compare graph instances coexist safely.

#### D2. Duplicate graph isolation
- ID: FCS-D2
- Status: [x]
- Files:
  - components/flow-cytometry/comparison-analysis-view.tsx
  - lib/store.ts
- Checklist:
  - [x] Add duplicate action.
  - [x] Snapshot axis/config at duplication time.
  - [x] Keep duplicate independent from source graph edits.
- Acceptance:
  - [x] Editing source axis does not mutate duplicate.

#### D3. Compare pinning parity
- ID: FCS-D3
- Status: [x]
- Files:
  - components/flow-cytometry/comparison-analysis-view.tsx
  - components/flow-cytometry/overlay-histogram-chart.tsx
  - lib/store.ts
- Checklist:
  - [x] Add pin in compare chart toolbars.
  - [x] Persist multi-series pin payload and legend context.
- Acceptance:
  - [x] Pinned compare charts preserve series identity and colors.

#### D4. Maximize and export parity
- ID: FCS-D4
- Status: [x]
- Files:
  - components/flow-cytometry/comparison-analysis-view.tsx
- Checklist:
  - [x] Add maximize/restore action for compare charts.
  - [x] Add compare-context export action.
- Acceptance:
  - [x] Compare tool parity is consistent with single-file mode.

### WS-E Principles Expansion (PHoNUPS-Aligned) (P1)

#### E1. Cross-instrument normalization adapter
- ID: FCS-E1
- Status: [x]
- Files:
  - lib/flow-cytometry/compare-normalization-adapter.ts
  - hooks/use-api.ts
  - components/flow-cytometry/comparison-analysis-view.tsx
- Checklist:
  - [x] Map heterogeneous FCS exports to one internal schema.
  - [x] Preserve native units in metadata labels.
  - [x] Add unsupported-channel warnings.
- Acceptance:
- [x] Mixed instrument exports compare without ad hoc per-component mapping.

#### E2. Replicate-aware compare modes
- ID: FCS-E2
- Status: [x]
- Files:
  - components/flow-cytometry/comparison-analysis-view.tsx
  - components/flow-cytometry/overlay-histogram-chart.tsx
  - hooks/use-api.ts
- Checklist:
- [x] Add replicate-group UI control.
- [x] Implement histogram per-bin averaging mode.
- [x] Implement 2D merged-points mode.
- [x] Show replicate method badges.
- Acceptance:
- [x] Replicate behavior is explicit and reproducible.

#### E3. Density/contour fallback for overplotting
- ID: FCS-E3
- Status: [ ]
- Files:
  - components/flow-cytometry/charts/*
  - lib/workers/fcs-series.worker.ts
- Checklist:
  - [ ] Add density/contour rendering mode trigger for dense scatter.
  - [ ] Keep optional raw-point overlay for low-density cases.
- Acceptance:
  - [ ] Dense views remain readable without frame drops.

#### E4. Quick zoom-range presets
- ID: FCS-E4
- Status: [ ]
- Files:
  - components/flow-cytometry/comparison-analysis-view.tsx
  - components/flow-cytometry/charts/*
- Checklist:
  - [ ] Add predefined axis-range presets for focused interpretation.
  - [ ] Keep reset-to-auto behavior.
- Acceptance:
  - [ ] Users can switch between overview and focused windows quickly.

### WS-F Metadata and Final UAT (P2)

#### F1. Treatment and dye metadata parity
- ID: FCS-F1
- Status: [x]
- Files:
  - components/flow-cytometry/file-upload-zone.tsx
  - components/flow-cytometry/dual-file-upload-zone.tsx
  - hooks/use-api.ts
  - lib/api-client.ts
  - backend/src/api/routers/upload.py
- Checklist:
  - [x] Add dye field to single and batch upload flows.
  - [x] Send dye in upload API contract and payload.
  - [x] Persist and return dye from backend.
  - [x] Display treatment and dye badges in compare contexts.
- Acceptance:
  - [x] Treatment and dye round-trip successfully end-to-end.

#### F2. UAT script and evidence pack
- ID: FCS-F2
- Status: [ ]
- Files:
  - docs/NANOFCS_UNIFIED_MULTI_FILE_TASK_TRACKER_MAR31_2026.md
- Checklist:
  - [ ] Build 8-scenario script mapped to meeting asks.
  - [ ] Record pass/fail with screenshots.
  - [ ] Capture unresolved gaps and follow-up action IDs.
- Acceptance:
  - [ ] Team can run deterministic demo validation.

## 4. Exit Gate Checklist

### Reliability
- [x] No blank-state compare charts.
- [x] No stale-request regressions during rapid interactions.
- [x] Partial-failure rendering works by file.

### Performance
- [x] Primary chart <= 1.5s.
- [x] 5-file compare first render <= 3.0s.
- [ ] Main-thread long tasks remain <= 50ms for common flows.

### Scientific integrity
- [x] Unified-axis enforcement for same units/columns works.
- [x] Per-file mode warns when mixed units are used.
- [x] Replicate method and downsample mode are always visible.

## 5. Operating Rule
Use this file as the only active NanoFCS tracker. Superseded planning trackers are intentionally removed to avoid split status management.

## 6. Alignment Audit (Apr 6, 2026)

### 6.1 Changed-file to tracker mapping

Aligned with completed WS-A to WS-D items:
- hooks/use-api.ts -> FCS-A1, FCS-A2, FCS-B1, FCS-B2, FCS-C2
- lib/store.ts -> FCS-A2, FCS-A5, FCS-B2, FCS-C1, FCS-D1, FCS-D2, FCS-D3
- components/flow-cytometry/comparison-analysis-view.tsx -> FCS-A1, FCS-A3, FCS-A5, FCS-B3, FCS-C3, FCS-C4, FCS-D1, FCS-D2, FCS-D4
- components/flow-cytometry/overlay-histogram-chart.tsx -> FCS-A3, FCS-B2, FCS-B4, FCS-D3
- components/flow-cytometry/charts/scatter-axis-selector.tsx -> FCS-C4
- components/flow-cytometry/analysis-results.tsx -> FCS-A4
- components/flow-cytometry/dual-file-upload-zone.tsx -> FCS-C2 (and partial FCS-F1)
- lib/fcs-series-cache-utils.ts -> FCS-B2
- lib/fcs-series-worker-client.ts -> FCS-B1
- lib/workers/fcs-series.worker.ts -> FCS-B1
- tests/perf/fcs-compare-gates.spec.ts -> FCS-B3, FCS-B4 performance evidence
- temp/perf-reports/fcs-compare-gates-report.json -> FCS-B3, FCS-B4 evidence artifact

Aligned with WS-E in progress:
- lib/flow-cytometry/compare-normalization-adapter.ts -> FCS-E1
- components/flow-cytometry/comparison-analysis-view.tsx -> FCS-E1, FCS-E2
- components/flow-cytometry/overlay-histogram-chart.tsx -> FCS-E2

Out of NanoFCS tracker scope (tracked under separate NTA/backend planning):
- backend/src/api/routers/analysis.py
- components/nta/*
- docs/NTA_MULTI_FILE_COMPARE_STRATEGY_MAR24_2026.md
- backend/scripts/convert_nta_nanofacs_to_parquet.py
- backend/reports/nta_nanofacs_parquet_conversion_report.json
- docs/TEM_WESTERNBLOT_COMBINED_EXE_RUNBOOK_APR03_2026.md

### 6.2 WS-E and WS-F status correction
- FCS-E1 moved from [ ] to [~]. Core adapter plus UI wiring is implemented; validation still needs stable repeatability.
- FCS-E2 moved from [ ] to [~]. Replicate controls and rendering modes are implemented; validation still needs stable repeatability.
- FCS-F1 remains [~] partial. Frontend API payload support includes dye, but full dual upload plus backend round-trip parity is not complete in this change set.
- FCS-F2 remains [ ] not started.

### 6.3 Repeatability snapshot (Apr 6, 2026)
- tests/perf/fcs-compare-gates.spec.ts: passing repeatedly in consecutive reruns; latest gate evidence is within thresholds.
- tests/perf/fcs-compare-controls-verification.spec.ts: passing repeatedly in consecutive reruns after per-test timeout hardening.

### 6.4 Commit gate note
Current code is broadly aligned with NanoFCS workstreams, but compare-controls repeatability is not yet green. If committing all changes together, include this known failure in commit notes.
