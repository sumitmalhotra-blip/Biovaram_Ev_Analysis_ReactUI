# NanoFCS Principles Adoption Master Plan
## Date: March 31, 2026
## Scope: Unified implementation direction for multi-file compare, reliability, performance, and scientific comparability

## 1. Objective
Adopt the agreed principles across the NanoFCS codebase in a controlled way that prioritizes stability first, then performance, then feature completeness.

This plan consolidates:
1. Existing pending NanoFCS/FCS compare work.
2. Parvesh-confirmed operating decisions.
3. Additional actionable principles derived from the PHoNUPS paper.

## 2. Principles To Adopt

### P1. Stability before expansion
1. No silent blank compare charts.
2. Deterministic chart states (loading, error, empty, data).
3. Stale-request protection for async compare loading.

### P2. Performance with scientific transparency
1. Interactive mode uses bounded scatter points.
2. Settled mode increases detail after debounce.
3. Export path remains full-fidelity.

### P3. Session architecture for 5-10 files
1. Selected set (up to 10) and visible set are independent.
2. Default visible overlays are 5.
3. Primary-first progressive paint is mandatory.

### P4. Axis governance
1. Default compare mode is unified axis.
2. Per-file axis is opt-in only.
3. Per-file axis allowed when units differ, with warning badges.
4. Same-column/unit comparisons enforce unified scaling.

### P5. Cross-instrument normalization layer
1. Add a compare adapter that maps multiple FCS exports to one internal chart schema.
2. Preserve native measurement units in labels and metadata.

### P6. Replicate-aware comparison
1. Histogram replicate mode: per-bin averaging.
2. 2D replicate mode: merged/union points.
3. Method must be visible in chart metadata.

### P7. Dense-data visualization fallback
1. Add density/contour fallback for high-overlap scatter views.
2. Keep raw-point rendering optional and capped.

### P8. Tool parity and graph independence
1. Compare graph cards must support axis, pin, duplicate, maximize, export.
2. Duplicated graph config must remain isolated from source graph changes.

## 3. Technical Strategy

### 3.1 Data and state boundaries
1. Persist only lightweight compare controls.
2. Keep heavy result/scatter maps runtime-only.
3. Add bounded in-memory cache with LRU eviction.

### 3.2 Loading and compute pipeline
1. Bounded concurrency for result and scatter loading.
2. Request version token to reject stale responses.
3. Workerized transforms for scatter/histogram series generation.

### 3.3 Rendering pipeline
1. Primary sample render first.
2. Stage remaining overlays progressively.
3. Apply level-of-detail transitions (interactive to settled).

### 3.4 Scientific guardrails
1. Explicit axis mode indicators on all compare charts.
2. Axis mismatch warnings for mixed-unit per-file comparisons.
3. Replicate handling method labels on outputs.

## 4. Multi-File Impacted Code Areas

### Frontend state and data orchestration
1. lib/store.ts
2. hooks/use-api.ts
3. lib/api-client.ts

### Compare and chart UI
1. components/flow-cytometry/comparison-analysis-view.tsx
2. components/flow-cytometry/overlay-histogram-chart.tsx
3. components/flow-cytometry/charts/scatter-axis-selector.tsx
4. components/flow-cytometry/analysis-results.tsx
5. components/flow-cytometry/dual-file-upload-zone.tsx
6. components/flow-cytometry/file-upload-zone.tsx

### Worker and adapter layer (new)
1. lib/workers/fcs-series.worker.ts
2. lib/flow-cytometry/compare-normalization-adapter.ts

### Backend metadata parity
1. backend/src/api/routers/upload.py
2. backend/src/models/* (only if dye persistence schema extension is required)

## 5. Delivery Sequencing

### Phase A (P0): Reliability and deterministic behavior
1. Bounded compare loader.
2. Request versioning and stale-response rejection.
3. Explicit chart state model.
4. Axis fallback and resolution hints.

### Phase B (P0): Core performance foundation
1. Workerized transform pipeline.
2. LRU runtime series cache.
3. Progressive paint and LOD transitions.
4. Point/bin caps with user-visible downsample messaging.

### Phase C (P1): Multi-file UX completion
1. Session-based 10-file compare controls.
2. In-graph axis controls and mode switch.
3. Compare side-panel controls and status badges.

### Phase D (P1): Tool parity and graph duplication
1. Graph instance model.
2. Duplicate graph with axis snapshot isolation.
3. Compare pin, maximize, export parity.

### Phase E (P1): Paper-principle integrations
1. Cross-instrument normalization adapter.
2. Replicate-aware modes.
3. Density/contour high-density fallback.
4. Quick zoom-range presets for interpretation.

### Phase F (P2): Metadata parity and UAT completion
1. Treatment plus dye end-to-end parity.
2. Meeting-requested UX standardization.
3. UAT script and acceptance evidence capture.

## 6. Gates and Exit Criteria
1. Time to first visible chart <= 1.5 seconds (primary).
2. 5-file compare initial render <= 3.0 seconds.
3. No main-thread tasks > 50ms during common interactions.
4. Toggle response <= 150ms.
5. Axis switch fast mode <= 300ms.
6. No silent blank compare chart states.
7. Partial failures do not block successful files.

## 7. Governance and Operating Rules
1. Any new compare feature must declare memory impact and fallback behavior.
2. Axis-related PRs must include same-unit enforcement behavior.
3. Dense-data PRs must include downsample transparency in UI.
4. Replicate logic must state computation method in chart labels/export metadata.
5. Progress tracking uses one source only:
   - docs/NANOFCS_UNIFIED_MULTI_FILE_TASK_TRACKER_MAR31_2026.md

## 8. Out of Scope for this cycle
1. Full long-term IndexedDB durable cache rollout.
2. Advanced publication export templates beyond current chart/export parity.
3. Non-NanoFCS platform-wide backlog items unrelated to compare architecture.

## 9. Immediate Next Actions
1. Start Phase A implementation under the unified tracker.
2. Create PR-sized subtasks from each in-progress item.
3. Enforce the new gates in QA and code review checklists.
