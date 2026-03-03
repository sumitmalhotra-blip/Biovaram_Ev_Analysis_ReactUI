# EV Particle Sizing — Implementation Roadmap & Pending Work

**Created:** February 23, 2026  
**Status:** Active — Tracking all remaining work for sizing pipeline  
**Context:** The FCMPASS physics engine, backend API, and **Phase 1 frontend wiring** are complete and validated (E2E test: D50 error vs NTA = -4.1%). This document tracks what remains for production readiness.

---

## Executive Summary

The core particle sizing engine (FCMPASS k-based calibration) has been fully rewritten, validated, and deployed to the backend. However, the **frontend is completely disconnected** from the new FCMPASS backend — users still see the old, broken calibration UI. Additionally, several features (custom bead kits, multi-calibration, safety warnings) are missing.

| Category | Status | Impact |
|----------|--------|--------|
| Backend physics (4 bug fixes) | ✅ COMPLETE | Sizing now correct: D50 error -4.1% vs NTA |
| Backend API (FCMPASS endpoints) | ✅ COMPLETE | 3 endpoints: fit, status, delete |
| Backend persistence | ✅ COMPLETE | Save/load/archive calibrations |
| Backend sizing cascade | ✅ COMPLETE | FCMPASS → Legacy → Multi-Mie → Single-Mie |
| **Frontend API client** | ✅ COMPLETE | 8 types, 3 methods added (Feb 23, 2026) |
| **Frontend calibration UI** | ✅ COMPLETE | FCMPASS mode toggle, diagnostics panel, per-bead k table |
| **Frontend RI pass-through** | ✅ COMPLETE | EV RI dropdown → backend FCMPASS LUT rebuild |
| Custom bead kit upload | ❌ NOT DONE | Only nanoViS D03231 available |
| Multi-calibration management | ✅ COMPLETE | Calibration library with list/activate/delete |
| Gain mismatch warnings | ✅ COMPLETE | Detector gain mismatch alerts on scatter-data and calibration |
| Bead self-validation | ✅ COMPLETE | Per-bead round-trip validation with pass/fail enforcement |
| Pre-loaded bead kits | ❌ NOT DONE | Only 1 kit ships |

---

## Phase 1: Wire Frontend to FCMPASS Backend ✅ COMPLETE

**Goal:** Users can trigger FCMPASS calibration, see correct results, and adjust EV RI from the UI.  
**Priority:** CRITICAL — without this, the correct sizing engine is inaccessible.  
**Completed:** February 23, 2026

### Task A1: Add FCMPASS Methods to `lib/api-client.ts`

**Problem:** The API client has no methods for the 3 FCMPASS endpoints that already exist on the backend.

**Current state:**
- `fitCalibration()` → calls `POST /calibration/fit` (legacy, wrong approach)
- `fitCalibrationManual()` → calls `POST /calibration/fit-manual` (legacy)
- `getCalibrationStatus()` → calls `GET /calibration/status` (legacy)
- `getActiveCalibration()` → calls `GET /calibration/active` (legacy)
- `removeCalibration()` → calls `DELETE /calibration/active` (legacy)

**Required additions:**
```typescript
fitFcmpassCalibration(params) → POST /calibration/fit-fcmpass
getFcmpassStatus()            → GET  /calibration/fcmpass-status
removeFcmpassCalibration()    → DELETE /calibration/fcmpass
```

**Files:** `lib/api-client.ts`

---

### Task A2: Update `bead-calibration-panel.tsx`

**Problem:** The calibration panel only calls legacy endpoints. Users cannot trigger FCMPASS.

**Required changes:**
1. Add calibration mode toggle: "Legacy" vs "FCMPASS (Recommended)"
2. When FCMPASS mode selected:
   - Add EV RI input field (default 1.37, range 1.35–1.45)
   - Call `apiClient.fitFcmpassCalibration()` on "Calibrate"
   - Display k value, k CV%, per-bead k values on success
3. On component mount, check FCMPASS status via `getFcmpassStatus()`
4. Show active method in header badge

**Files:** `components/flow-cytometry/bead-calibration-panel.tsx`

---

### Task A3: Wire EV RI Pass-Through to FCMPASS Pipeline

**Problem:** When FCMPASS is active, the backend reanalyze endpoint ignores the user's `n_particle` selection from the sidebar. The FCMPASS branch uses the saved `fcmpass_calibration.n_ev` instead.

**Backend fix (samples.py):** In the FCMPASS branch of `/scatter-data` and `/reanalyze`, if the user's `n_particle` differs from calibrator's `n_ev`, rebuild the EV LUT.

**Frontend fix (analysis-settings-panel.tsx):** Ensure the RI dropdown value is passed through API calls that trigger reanalysis.

**Files:** `backend/src/api/routers/samples.py`, `components/flow-cytometry/analysis-settings-panel.tsx`

---

## Phase 2: Custom Bead Kit Support ✅ COMPLETE

**Goal:** Users with any bead kit can upload their datasheet and calibrate.  
**Completed:** February 23, 2026

### Task B1: Upload Custom Bead Kit Endpoint

Add `POST /calibration/bead-standards` — accepts JSON file, validates schema, saves to `config/bead_standards/`.

Add `DELETE /calibration/bead-standards/{name}` — removes a custom kit.

**Files:** `backend/src/api/routers/calibration.py`

### Task B2: Frontend — "Add Custom Bead Kit" UI

Add button + form (or JSON upload) in the calibration panel. Fields: manufacturer, material, RI, bead sizes/CVs.

**Files:** `components/flow-cytometry/bead-calibration-panel.tsx`

### Task D1: Ship Pre-loaded Popular Kits

Create JSON datasheets for:
- MegaMix-Plus FSC (100, 160, 240, 500, 900nm; Polystyrene)
- Apogee Mix (110, 180, 240, 300, 500, 590, 880, 1300nm; Silica+PS)
- Spherotech NIST (common sizes; Polystyrene)

**Files:** `backend/config/bead_standards/`

---

## Phase 3: Multi-Calibration Management (MEDIUM)

**Goal:** Support multiple saved calibrations for different instruments/gains/experiments.  
**Estimated effort:** 4–6 hours  

### Task B2: Backend — Calibration Library

New endpoints:
```
GET  /calibration/fcmpass/list          → List all saved FCMPASS calibrations
PUT  /calibration/fcmpass/{id}/activate → Re-activate an archived calibration
GET  /calibration/fcmpass/{id}          → Get details of specific calibration
```

Storage: Index archived calibrations in `config/calibration/fcmpass_archive/` with metadata (instrument, gain, date, bead kit, creator).

### Task B2-FE: Frontend — Calibration Library UI

Table: Date, Bead Kit, k, CV%, Instrument, Status (Active/Archived). Activate/Delete buttons per row.

---

## Phase 4: Safety & Validation (MEDIUM)

**Goal:** Warn users about misconfigured calibrations and enforce quality thresholds.  
**Estimated effort:** 3–4 hours  

### Task B3: Gain Mismatch Warning

Extract gain/voltage from FCS metadata (`$PnV` parameter). Compare bead FCS gain vs sample FCS gain. Return warning in API response if >5% mismatch.

### Task C1: Formal Bead Self-Validation

After `fit_from_beads()`, size each bead through the full pipeline. Check recovered diameter vs datasheet within 2× CV. Return pass/fail per bead in the API response. Reject calibration if any bead fails.

### Task C2: Calibration Expiry Alerts

Read `expiration_date` from bead kit JSON. Warn if calibration uses expired lot.

---

## Phase 5: Legacy Bug Cleanup (LOW) ✅ COMPLETE

**Goal:** Fix the fallback sizing methods (currently bypassed by FCMPASS).  
**Completed:** February 23, 2026  

| Bug | Location | Fix Applied |
|-----|----------|-------------|
| Multi-Solution Mie scale mismatch (AU vs nm²) | `mie_scatter.py` `calculate_sizes_multi_solution()` | ✅ Affine AU→σ_sca normalization before LUT matching |
| Single-Solution P5-P95 normalization | `mie_scatter.py` `diameters_from_scatter_normalized()` | ✅ Uses σ_sca (Qsca×πr²) instead of FSC proxy; P2/P98 range; deprecation warning |
| Legacy bead cal wrong RI | `bead_calibration.py` `diameter_from_fsc()` | ✅ Rayleigh RI correction factor via `target_ri` param; deprecation warning |

All three methods now log deprecation warnings recommending FCMPASS calibration.

---

## Completion Tracking

| Phase | Task | Status | Completed Date |
|-------|------|--------|----------------|
| 1 | A1: FCMPASS methods in api-client.ts | ✅ | Feb 23, 2026 |
| 1 | A2: Update bead-calibration-panel.tsx | ✅ | Feb 23, 2026 |
| 1 | A3: RI pass-through (backend) | ✅ | Feb 23, 2026 |
| 1 | A3: RI pass-through (frontend) | ✅ | Feb 23, 2026 |
| 2 | B1: Custom bead kit upload endpoint | ✅ | Feb 23, 2026 |
| 2 | B2-FE: Custom bead kit UI | ✅ | Feb 23, 2026 |
| 2 | D1: Pre-loaded bead kit JSONs | ✅ | Feb 23, 2026 |
| 3 | B2: Calibration library backend | ✅ | Feb 23, 2026 |
| 3 | B2-FE: Calibration library UI | ✅ | Feb 23, 2026 |
| 4 | B3: Gain mismatch warnings | ✅ | Feb 23, 2026 |
| 4 | C1: Bead self-validation | ✅ | Feb 23, 2026 |
| 4 | C2: Calibration expiry alerts | ✅ | Feb 23, 2026 |
| 5 | Legacy bug cleanup | ✅ | Feb 23, 2026 |

---

## References

| Document | Purpose |
|----------|---------|
| `docs/COMPLETE_SIZING_REPORT_FOR_PARVESH.md` | Full technical report (4 bugs, FCMPASS method, E2E results) |
| `docs/SIZING_COMPLETE_GUIDE.md` | Architecture, gaps, roadmap, testing procedures |
| `docs/SIZING_ACCURACY_DIAGNOSIS.md` | Original diagnosis of sizing errors |
| `docs/CALIBRATION_RESULTS_REPORT.md` | Calibration numbers and validation |
| `docs/E2E_TEST_METRICS_REPORT.md` | Frontend metrics with FC vs NTA values |
| `backend/test_e2e_pc3_exo1.py` | Reproducible E2E test (7/7 pass) |

---

*Last updated: February 23, 2026 — All 5 phases completed*
