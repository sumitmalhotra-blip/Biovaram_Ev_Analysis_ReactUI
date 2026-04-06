# NTA Multi-File Comparison Strategy (Mar 24, 2026)

## Purpose
This document defines the strategy to implement a true NTA multi-file comparison workflow that supports practical 10-20 sample sessions, user-controlled active subsets, and per-file include/exclude visibility for overlays.

Audience:
- Product
- Frontend
- Backend
- QA

---

## Goals
1. Enable comparison sessions with up to 20 NTA files.
2. Let users select an active subset from available uploaded NTA samples.
3. Add per-file include/exclude controls for chart overlays.
4. Keep charts responsive and readable with larger compare sets.
5. Preserve current single-file and two-file flows during rollout.

---

## Implementation Status (Updated Mar 25, 2026)

### Completed
1. Milestone 1: Session foundation + selection UI is implemented.
2. Milestone 2: Multi-series chart migration is implemented.
3. Milestone 3 core performance items are implemented:
	- Concurrency-limited fetch for compare samples.
	- Computed-series cache structure (`computedSeriesCacheByKey`) with chart-level cache reads/writes.
	- Progressive paint pipeline (primary first, staged overlay render).
	- Debounced recompute path for rapid overlay/profile changes.
	- Downsampling strategy for dense size distributions.

### Pending
1. Full QA matrix closure for 1/2/5/10/20 sample sessions and stress/regression signoff.

### Newly Completed (Mar 25, 2026)
1. Milestone 4 optional backend optimization is now implemented:
	- `POST /analysis/nta/multi-compare` bulk endpoint.
	- Compact bulk payload with metadata, warnings/errors, and pre-aggregated bins.
2. Frontend compare loader now attempts bulk endpoint first and falls back to per-sample batching when needed.

---

## Current System Baseline

### What exists today
1. NTA analysis supports one primary result plus one secondary overlay.
2. Overlay panel in NTA results supports uploading one second file for side-by-side comparison.
3. NTA chart components are designed for primary + single secondary dataset.
4. API client supports per-sample NTA fetch and upload.

### Key limitations
1. Data model is single-secondary, not multi-file.
2. Overlay controls are binary (on/off), not per-file.
3. Chart prop contracts do not accept series arrays.
4. No compare session model for selected vs visible datasets.
5. No performance pipeline for 10-20 files.

---

## Proposed Product Behavior

### Compare session behavior
1. User can select up to 20 NTA samples for one compare session.
2. User can define a visible subset for overlays (recommended max visible 3-5).
3. Each selected file has include/exclude toggle for each chart overlay context.
4. User can set one sample as primary/reference.
5. Hidden samples remain loaded in session but are not rendered.

### UX principles
1. Keep controls simple and explicit (selected count, visible count).
2. Do not force rendering all selected files simultaneously.
3. Prioritize readability over showing all lines/bars at once.
4. Surface loading and failure state per sample, not globally.

---

## Architecture Strategy

### 1) State model: NTA compare session
Add a dedicated compare-session structure in store:
1. selectedSampleIds: string[]
2. visibleSampleIds: string[]
3. primarySampleId: string | null
4. resultsBySampleId: Record<string, NTAResult>
5. loadingBySampleId: Record<string, boolean>
6. errorBySampleId: Record<string, string | null>
7. computedSeriesCacheByKey: Record<string, ChartSeries>
8. filters: size range and optional event/data thresholds
9. maxVisibleOverlays: number (default 4)

Notes:
1. Keep existing single-secondary state during transition for compatibility.
2. Normalize by sample_id to avoid index-coupling bugs.

### 2) Data pipeline
Use a two-stage pipeline:
1. Fetch/store raw NTA results per sample.
2. Build chart-ready series from cached raw data and current settings.

Cache key dimensions:
1. sample_id
2. bucket profile id
3. filter settings
4. y-axis mode

### 3) Chart contract migration
Refactor NTA chart components from single secondary input to multi-series array.

Target series shape:
1. sampleId
2. label
3. color
4. visible
5. data points

Apply to:
1. NTA size distribution chart
2. NTA concentration profile chart

### 4) Overlay visibility rules
1. Selected and visible are separate concepts.
2. Visible overlays capped at 5 for readability/performance.
3. If user selects more than cap, keep loaded but hidden by default.
4. Provide one-click actions: show top 3, hide all, reset visibility.

---

## Frontend Implementation Plan

## Milestone 1: Session foundation + selection UI
Scope:
1. Add compare session state and actions in store.
2. Build multi-select compare panel in NTA results.
3. Add selected list with per-file controls:
1. include/exclude visibility
2. set as primary
3. remove from session
4. Add counters: selected, visible, loading, failed.

Acceptance criteria:
1. User can add/remove NTA samples into compare session.
2. User can toggle each file visible/hidden.
3. User can choose primary sample.

## Milestone 2: Multi-series charts
Scope:
1. Migrate distribution chart to series-array input.
2. Migrate concentration chart to series-array input.
3. Stable color assignment per sample.
4. Per-series legend interactions (toggle visibility).

Acceptance criteria:
1. Charts render multiple selected files.
2. Hidden files are excluded from render.
3. Primary sample is visually emphasized.

## Milestone 3: Performance and progressive rendering
Scope:
1. Concurrency-limited fetch (for example, 3 at a time).
2. Computed series cache keyed by sample and settings.
3. Progressive paint:
1. show primary first
2. then add remaining visible overlays
4. Debounced recompute on rapid filter/setting changes.

Acceptance criteria:
1. UI remains responsive with 10-20 selected files.
2. Re-toggling visibility is near-instant after initial load.
3. Switching bin profiles does not trigger unnecessary refetch.

## Milestone 4: Optional backend optimization
Scope:
1. Add optional bulk compare endpoint for NTA sample IDs.
2. Return compact payload with metadata + summary + optional pre-aggregated bins.
3. Keep frontend fallback to per-sample calls.

Acceptance criteria:
1. End-to-end compare latency reduced for large sessions.
2. No behavior regression if bulk endpoint unavailable.

---

## Backend/API Approach

### Phase 1 (reuse current API)
1. Use existing getNTAResults(sample_id) per selected sample.
2. Frontend handles batching, retries, and merge into session state.

### Phase 2 (add bulk endpoint)
Proposed endpoint:
- POST /analysis/nta/multi-compare

Request:
1. sample_ids: string[]
2. filters: optional
3. include_size_distribution: boolean

Response:
1. results_by_sample_id
2. metadata_by_sample_id
3. warnings/errors_by_sample_id
4. optional precomputed distributions

---

## Data and Performance Strategy

### Fetch strategy
1. Queue requests with bounded concurrency.
2. Keep per-sample loading state.
3. Continue on partial failures.

### Caching strategy
1. Raw result cache by sample_id.
2. Computed chart series cache by deterministic key.
3. Invalidate computed cache when profile/filters change.

### Rendering strategy
1. Limit visible overlays by default.
2. Use progressive render for visible list.
3. Downsample dense distributions when needed.

---

## Risks and Mitigation
1. Risk: chart clutter with many overlays.
Solution: selected vs visible split, cap visible overlays, strong legend controls.

2. Risk: long initial load for large sessions.
Solution: concurrency-limited loading + per-sample progress + progressive paint.

3. Risk: recompute lag when bins/filters change.
Solution: computed series cache and debounced updates.

4. Risk: increased state complexity.
Solution: isolate compare-session state and migrate in phases with compatibility path.

5. Risk: user confusion between selected and visible.
Solution: explicit labels and counters with helper text.

---

## QA Test Matrix
1. Select 1, 2, 5, 10, and 20 samples.
2. Toggle visibility rapidly and verify no UI freeze.
3. Change bucket presets and custom bins during active compare session.
4. Ensure hidden samples do not render but remain loaded.
5. Validate behavior with partial API failures.
6. Verify primary sample change updates chart emphasis and labels.
7. Confirm persisted compare session state (if enabled) restores correctly.
8. Confirm no regression to existing single-file NTA workflows.

---

## Delivery Sequence and Estimate
1. Milestone 1: 2-3 days
2. Milestone 2: 2-3 days
3. Milestone 3: 2-4 days
4. Milestone 4 (optional backend): 2-4 days

Total:
- Frontend-first delivery: ~6-10 days
- With backend bulk optimization: ~8-14 days

---

## Proposed Definition of Done
1. Users can compare up to 20 selected NTA files in one session.
2. Users can include/exclude individual files from overlays.
3. Charts remain responsive with large selected sets.
4. Visual output remains readable (visible cap and controls in place).
5. System handles partial failures gracefully.
6. Existing NTA upload and single-analysis workflows remain unaffected.
