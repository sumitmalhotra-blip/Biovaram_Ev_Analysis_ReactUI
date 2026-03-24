# NTA Module Implementation Plan (Mar 24, 2026)

## Scope and Goal
This plan translates the Mar 23, 2026 session transcript into a concrete implementation roadmap for the NTA module.

Primary outcomes:
1. Capture richer experiment metadata at upload time.
2. Improve NTA comparison workflows (quality-focused and multi-file capable).
3. Keep temperature correction available but default-off and non-intrusive.
4. Make size breakdown/reporting customizable for publication workflows.
5. Improve performance for large/multiple files without breaking current analysis behavior.

## Current State Baseline (What Already Exists)

Existing NTA capabilities already present:
1. Upload and parse NTA files with optional treatment, temperature, operator fields: [components/nta/nta-tab.tsx](components/nta/nta-tab.tsx#L259)
2. Temperature correction UI exists and is toggleable: [components/nta/temperature-settings.tsx](components/nta/temperature-settings.tsx#L256)
3. Temperature correction defaults to OFF in state initialization: [components/nta/temperature-settings.tsx](components/nta/temperature-settings.tsx#L210)
4. NTA size breakdown UI exists with fixed bins: [components/nta/size-distribution-breakdown.tsx](components/nta/size-distribution-breakdown.tsx#L18)
5. Overlay comparison currently supports second file flow: [components/nta/nta-analysis-results.tsx](components/nta/nta-analysis-results.tsx#L554)
6. Supplementary metadata table already exposes sensitivity, shutter, positions, dilution, scattering intensity, etc.: [components/nta/supplementary-metadata-table.tsx](components/nta/supplementary-metadata-table.tsx#L95)
7. Backend upload parses and persists NTA metrics, with alert generation: [backend/src/api/routers/upload.py](backend/src/api/routers/upload.py#L1254)

Implication: this is mostly an enhancement and productization pass, not a greenfield build.

## Transcript-Derived NTA Requirements (Exact Change Intent)

### A) Metadata Capture and Input Flexibility
1. Replace rigid treatment-only semantics with explicit marker context (marker and dye separation).
2. Add separate field/column for dye.
3. Allow custom marker input (not only fixed options).
4. Allow custom dye input.
5. Capture marker concentration distinctly from particle concentration reported by instrument.
6. Keep purification method structured, but allow custom method and freeform notes.

### B) Temperature Correction Behavior
1. Keep temperature correction feature (do not remove).
2. Default it to OFF.
3. When OFF, suppress correction-dependent outputs in comparison/summary sections.
4. Keep it available for users who explicitly enable it.

### C) Size Breakdown and Reporting
1. Keep size breakdown section.
2. Make size ranges/buckets customizable by users.
3. Preserve a quality-safe default bin profile for standardized analysis.
4. Support report-oriented export where presentation can be user-tailored while quality logic remains protected.

### D) Quality Comparison Logic Between Samples
1. Improve quality assessment between two or more samples.
2. Compare metadata consistency, especially:
1. Scattering intensity
2. Measurement time
3. Dilution factor
4. Sensitivity
5. Shutter
6. Number of positions
7. Conductivity
8. pH context
3. Treat detected particles as a variable metric (informative, not strict equal-match gate).
4. Surface a clear quality verdict and mismatch reasons.

### E) Multi-File Comparison and Performance
1. Move beyond two-file compare; support practical multi-file analysis (target 10-20 files).
2. Allow selecting subset of files for active comparison (do not force all uploaded files).
3. Add filtering controls (size/event range) to reduce processing load.
4. Cache computed graph data so axis/switch interactions are quick after first run.
5. Maintain responsive UI even when initial calculations are heavier.

### F) Workflow Structure
1. Separate user-facing workflow into:
1. Analysis
2. Quality
3. Report
2. Keep quality computations deterministic/protected.
3. Keep AI integration optional and phased; rule-based quality remains default until trained AI is ready.

## Implementation Approach

## Workstream 1: Data Model and API Contract (Backend + Client)

### 1.1 Metadata schema extensions
Add optional sample-level metadata fields (NTA + shared metadata profile):
1. marker_name
2. marker_is_custom (bool)
3. dye_name
4. dye_is_custom (bool)
5. marker_concentration_value
6. marker_concentration_unit
7. purification_method
8. purification_method_custom
9. prep_notes

Likely touch points:
1. Sample persistence model and CRUD layer.
2. NTA upload request contract in API client.
3. NTA upload endpoint form parsing in backend.

### 1.2 Comparison API for N-sample quality checks
Introduce a new endpoint (or extend existing compare endpoint) for metadata consistency quality checks:
1. Input: list of sample IDs, optional active parameter set, optional tolerance profile.
2. Output: per-parameter consistency status + aggregate quality verdict + explanation strings.

### 1.3 Size bucket profile API
Add profile-driven bucket support:
1. default_profile (locked for quality)
2. custom_profile (user-defined for report/visualization)

Store and version profiles so reproducibility is preserved.

## Workstream 2: NTA Upload and Metadata UX

### 2.1 Upload form redesign
Update [components/nta/nta-tab.tsx](components/nta/nta-tab.tsx#L328) with:
1. Marker selector + Custom option input.
2. Dye selector + Custom option input.
3. Marker concentration value + unit.
4. Purification method selector + Custom option input.
5. Keep operator and notes.

### 2.2 Validation rules
1. If marker = Custom, require custom marker text.
2. If dye = Custom, require custom dye text.
3. If purification method = Custom, require method text or detailed notes.
4. Marker concentration must be positive numeric when provided.

### 2.3 Backward compatibility
1. Existing samples without new fields remain valid.
2. UI should gracefully display missing metadata as N/A.

## Workstream 3: Temperature Correction Gating

### 3.1 Default-off verification
Ensure default remains OFF and is not auto-enabled by persisted stale state.

### 3.2 Conditional visibility
When OFF:
1. Hide correction-derived comparison visuals.
2. Do not propagate corrected values to summary cards.
3. Keep raw/original values as source of truth in quality checks.

When ON:
1. Explicitly label corrected metrics and correction factors.
2. Keep clear distinction between raw and corrected values.

Existing components to update:
1. [components/nta/temperature-settings.tsx](components/nta/temperature-settings.tsx)
2. [components/nta/charts/temperature-corrected-comparison.tsx](components/nta/charts/temperature-corrected-comparison.tsx)
3. NTA summary cards and report output bindings.

## Workstream 4: Size Breakdown Customization

### 4.1 Configurable bins
Replace hardcoded bins in [components/nta/size-distribution-breakdown.tsx](components/nta/size-distribution-breakdown.tsx#L18) with profile-driven bins:
1. Default standardized profile (locked for quality).
2. User custom profile (editable for analysis/report view).

### 4.2 Profile editor
Create UI to:
1. Add/edit/remove bins.
2. Enforce ordered non-overlapping ranges.
3. Save named profiles.
4. Reset to default profile.

### 4.3 Dual-mode behavior
1. Quality mode uses standardized profile only.
2. Report mode may use custom profile with disclosure label in exports.

## Workstream 5: Quality Comparison Between Multiple Samples

### 5.1 Quality rules engine (deterministic)
Implement metadata consistency checks with classification:
1. Must-match parameters (positions, shutter, sensitivity, dilution where protocol requires).
2. Range/tolerance parameters (measurement time, scattering intensity, conductivity).
3. Informational parameters (detected particles).

### 5.2 UX output
Display:
1. Overall quality verdict.
2. Per-parameter pass/warn/fail.
3. Human-readable mismatch explanations.
4. Suggested action (for example: normalize dilution, exclude run, re-acquire).

### 5.3 AI-ready integration boundary
Return structured JSON with features suitable for future AI enrichment, but keep current verdict deterministic.

## Workstream 6: Multi-File Compare and Performance

### 6.1 Multi-file orchestration
Add compare session model:
1. Uploaded files list.
2. Active selected subset.
3. Cached computed artifacts per file.

### 6.2 Performance tactics
1. Pre-aggregation and caching of histogram/distribution arrays.
2. Async/queued compute for large batches.
3. Progressive rendering (first N files, then stream in remainder).
4. Size/event filters before compute.
5. Debounced chart interactions and memoized selectors.

### 6.3 Practical limits
Define and enforce:
1. Recommended max simultaneous overlay in one chart (for readability), for example 3-5 visible at once.
2. Back-end max batch size for quality processing (target capability 10-20 files in one compare run).

## Workstream 7: Analysis / Quality / Report Experience

### 7.1 Information architecture
Split NTA section into clear modes:
1. Analysis tab: exploratory plots and configurable views.
2. Quality tab: locked quality checks and consistency verdict.
3. Report tab: publication-ready formatted outputs.

### 7.2 Report output
Include:
1. Standardized quality summary block.
2. Selected charts.
3. Metadata table with marker/dye/purification.
4. Explicit statement on whether temperature correction was used.
5. Explicit statement on bin profile used (default/custom).

## Delivery Plan (Phased)

### Phase 1 (High Priority, 3-5 days)
1. Upload metadata enhancements (marker/dye/custom inputs, concentration separation).
2. Temperature correction gating refinement (default OFF + hidden effect when OFF).
3. Quality comparison rules for core metadata pairwise (2 files).

Acceptance criteria:
1. User can input custom marker/dye and save with NTA sample.
2. Temperature correction remains off by default after refresh/new session.
3. Quality tab compares two samples and returns pass/warn/fail reasons.

### Phase 2 (Medium Priority, 4-6 days)
1. Custom size bucket profiles and dual-mode (quality vs report).
2. Multi-file compare backend endpoint (N samples) with parameter-level quality output.
3. UI selection of active files in compare set.

Acceptance criteria:
1. User can define custom bins; quality still uses locked default profile.
2. Compare supports more than two selected files.
3. Quality output includes per-sample and per-parameter mismatch matrix.

### Phase 3 (Performance + Reporting, 4-6 days)
1. Compute caching/pre-aggregation for NTA compare charts.
2. Progressive multi-file rendering and filter controls.
3. Report mode output and export polish.

Acceptance criteria:
1. Re-switching chart axes/parameters after first compute is near-instant.
2. System remains usable with 10-20 files in compare workflow.
3. Report output includes quality verdict, metadata, and chart evidence.

## Technical Risks and Mitigation
1. Risk: UI clutter from too many metadata fields.
Mitigation: progressive disclosure with Advanced Metadata accordion.

2. Risk: Multi-file overlay becomes unreadable.
Mitigation: decouple selection set from visible overlay set; allow show/hide per sample.

3. Risk: Performance regression on large event files.
Mitigation: server-side pre-aggregation, cache keys by file hash + filter profile.

4. Risk: Quality rules ambiguity.
Mitigation: codify parameter-level tolerance profile in config and expose it in UI.

## Open Product Decisions Needed
1. Final controlled vocabulary lists for marker, dye, and purification method.
2. Default tolerance thresholds for quality checks (time/scattering/conductivity).
3. Final report template format (PDF-first vs DOCX-first vs both).
4. Maximum supported files in one compare job for GA release.

## Execution Checklist
1. Finalize data contract and DB migration for marker/dye metadata.
2. Implement NTA upload form enhancements and backend parsing.
3. Build deterministic quality comparator endpoint.
4. Add Analysis/Quality/Report tab split.
5. Implement customizable size profiles with locked default quality profile.
6. Add multi-file compare selection and session cache.
7. Add performance instrumentation and benchmark with 10/15/20 files.
8. Ship report export and QA sign-off.
