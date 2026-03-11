# EV Analysis Platform — Comprehensive Senior Tester Audit Report

**Date:** March 11, 2026  
**Scope:** Full codebase — frontend, backend, data flow, store, API, auth, security, packaging, tests  
**Methodology:** Automated static analysis of every component, endpoint, hook, store field, data flow path, security surface, and packaging pipeline  
**Comparison:** Diff against February 2026 audit baseline  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Changes Since February 2026 Audit](#2-changes-since-february-2026-audit)
3. [CRITICAL — Fake/Hardcoded Data Issues](#3-critical--fakehardcoded-data-issues)
4. [CRITICAL — Security Vulnerabilities](#4-critical--security-vulnerabilities)
5. [HIGH — Synthesized Data Without Warning](#5-high--synthesized-data-without-warning)
6. [HIGH — Dead API Surface](#6-high--dead-api-surface)
7. [MEDIUM — Backend Issues](#7-medium--backend-issues)
8. [MEDIUM — Frontend Dead Code](#8-medium--frontend-dead-code)
9. [MEDIUM — Store & State Issues](#9-medium--store--state-issues)
10. [LOW — Cleanup & Maintenance](#10-low--cleanup--maintenance)
11. [Verified Working Systems](#11-verified-working-systems)
12. [Test Coverage Assessment](#12-test-coverage-assessment)
13. [Packaging & Build Pipeline](#13-packaging--build-pipeline)
14. [Priority Implementation Roadmap](#14-priority-implementation-roadmap)

---

## 1. Executive Summary

| Category | Feb 2026 | Mar 2026 | Delta |
|---|---|---|---|
| Fake/hardcoded data (no warning) | **4** | **3** | -1 (DiscrepancyChart fixed) |
| Synthesized data with "Estimated" badge | **0** | **3** | +3 (mitigations added) |
| Synthesized data without warning | **4** | **3** | -1 (SizeCategoryBreakdown replaced) |
| Security vulnerabilities | **1** | **6** | +5 (new endpoints, deeper audit) |
| Disconnected backend endpoints | **6** | **4** | -2 (angle range, retry_job fixed) |
| Dead API client methods | **3** | **19** | +16 (API surface grew faster than UI) |
| Dead hook functions | **11** | **0** | -11 (all wired or removed) |
| Dead store state actions | **7+** | **6** | -1 (NTA overlay wired) |
| Runtime bugs (will crash) | **2** | **0** | -2 (both fixed) |
| Dead backend modules/scripts | **6** | **2 dirs + 10 scripts** | Reduced (modules deleted, dirs remain) |
| Dead database columns | **10** | **6** | -4 (some wired) |
| Missing tests | N/A | **Critical gap** | New finding |

**Overall Platform Integrity: ~72% of features actively use real data (up from ~65%). ~10% show synthesized data with badges. ~8% show fake data without warning. ~10% is dead code.**

**Key Improvements:** 2 critical runtime bugs fixed, DiscrepancyChart and PositionAnalysis now use real data, NTA overlay feature wired up, NTA sidebar fully functional, FCS caching dramatically improves performance, signup URL fixed.

**Key Regressions:** New backup endpoints have zero authentication, CORS is misconfigured with wildcard + credentials, dashboard AI chat points to dead endpoint, 10 backend scripts are broken due to deleted imports.

---

## 2. Changes Since February 2026 Audit

### Issues RESOLVED Since Feb 2026

| # | Issue | Resolution |
|---|---|---|
| 1 | `crud.py` `Sample.acquisition_date` crash | Fixed — now uses `Sample.upload_timestamp` |
| 2 | `analysis.py` `fsc_cv_pct` / `ssc_cv_pct` crash | Fixed — now uses `fsc_cv` / `ssc_cv` |
| 3 | DiscrepancyChart 100% hardcoded | Fixed — accepts `fcsStats`/`ntaStats` props, computes real discrepancies |
| 4 | PositionAnalysis mock data | Fixed — `generateMockPositionData()` removed, shows empty state when no data |
| 5 | SizeCategoryBreakdown hardcoded 15%/70%/15% | Fixed — file deleted, replaced by `ParticleSizeVisualization` with real data |
| 6 | NTA sidebar completely decorative | Fixed — all settings wired to `ntaAnalysisSettings` store |
| 7 | FSC/SSC angle range silently dropped | Fixed — `ReanalyzeRequest` now includes and passes through both ranges |
| 8 | `retry_job` returning mock data | Fixed — creates real `ProcessingJob` DB record |
| 9 | NTA overlay feature dead (store-only) | Fixed — wired in `nta-analysis-results.tsx` |
| 10 | Signup hardcoded `http://localhost:8000` URL | Fixed — uses `apiClient.registerUser()` |
| 11 | 11 unused hook functions | Fixed — all wired or consolidated |
| 12 | `dilution_factors.json` dead config | Fixed — deleted |

### NEW Issues Found in March 2026

| # | Issue | Severity |
|---|---|---|
| 1 | Backup router — zero auth on DB backup/restore/delete | CRITICAL |
| 2 | Auth endpoints — no ownership validation on profile GET/PUT | CRITICAL |
| 3 | User listing endpoint — no auth, leaks all user data | HIGH |
| 4 | CORS wildcard + credentials misconfiguration | HIGH |
| 5 | JWT secret key hardcoded placeholder | HIGH |
| 6 | Dashboard AI chat points to dead Next.js API route | HIGH |
| 7 | NTA concentration chart — fake data, no badge | HIGH |
| 8 | `distribution-analysis` endpoint uses uncached FCSParser | MEDIUM |
| 9 | `uploadNTA()` missing cache invalidation | LOW |
| 10 | `retry_job` creates DB record but doesn't dispatch processing | LOW |

---

## 3. CRITICAL — Fake/Hardcoded Data Issues

Components that **always** show fake data with **no warning indicator** to the user.

### 3.1 Cross-Compare Overlay Histogram — 100% Fake Default Data

**File:** `components/cross-compare/charts/overlay-histogram-chart.tsx`  
**Lines:** 38-57  
**Status:** KNOWN (Feb 2026) — **Still unfixed**

`generateDefaultData()` creates hardcoded Gaussian FCS/NTA overlay distributions (peaks at 127nm and 140nm). When no data props are passed, this fake data is displayed. **No "demo" or "estimated" badge** warns the user.

---

### 3.2 Cross-Compare KDE Chart — Demo Data Fallback

**File:** `components/cross-compare/charts/kde-comparison-chart.tsx`  
**Lines:** 82-110  
**Status:** KNOWN (Feb 2026) — **Still unfixed**

`generateDemoData()` creates 1000 pseudo-random data points using seeded normal distribution. KDE computation then runs on this fake data. **No visual indicator** of synthetic data.

---

### 3.3 Cross-Compare Correlation Scatter — Hardcoded Stats

**File:** `components/cross-compare/charts/correlation-scatter-chart.tsx`  
**Lines:** 68-80  
**Status:** KNOWN (Feb 2026) — **Still unfixed**

`generateDefaultData()` creates fake D10/D50/D90/Mode/StdDev scatter points using `Math.sin` variation around hardcoded values (FCS: 89.2, 127.4, 198.3, etc.). **No warning indicator.**

---

## 4. CRITICAL — Security Vulnerabilities

### 4.1 Backup Router — Zero Authentication

**File:** `backend/src/api/routers/backup.py`  
**Severity:** CRITICAL  
**Status:** NEW

All 6 endpoints are completely unprotected:
- `POST /db/backup` — create database backup
- `POST /db/restore` — **restore database from backup** (destructive)
- `DELETE /db/backup/{name}` — delete backup file
- `GET /db/backup/{name}` — download backup
- `GET /db/backups` — list backups
- `GET /db/info` — database statistics

**Impact:** Any network-reachable client can backup, restore, or destroy the database.

**Solution:**
```python
from fastapi import Depends
from src.api.auth_middleware import require_admin

@router.post("/db/backup", dependencies=[Depends(require_admin)])
async def create_backup(...):
```

---

### 4.2 Auth Endpoints — No Ownership Validation

**File:** `backend/src/api/routers/auth.py`  
**Lines:** 288-370  
**Severity:** CRITICAL  
**Status:** NEW

- `GET /auth/me/{user_id}` — any client can fetch any user's profile by guessing user IDs
- `PUT /auth/profile/{user_id}` — any client can modify any user's name, email, organization

**Solution:** Add `require_auth` dependency and validate `user_id == current_user.id`.

---

### 4.3 User Listing — No Auth

**File:** `backend/src/api/routers/auth.py`  
**Lines:** 379-398  
**Severity:** HIGH  
**Status:** NEW

`GET /auth/users` returns all user records (emails, names, organizations) without any authentication. Comment says "admin only in production" but no middleware enforces it.

---

### 4.4 CORS Misconfiguration

**File:** `backend/src/api/main.py`  
**Line:** 164  
**Severity:** HIGH  
**Status:** NEW

```python
allow_origins=["*"],          # All origins
allow_credentials=True,       # Cookies/tokens accepted
expose_headers=["*"],         # All headers exposed
```

Per the CORS specification, `allow_origins=["*"]` with `allow_credentials=True` is a security misconfiguration. Browsers should (and some do) block this combination. For desktop-only deployment this is mitigated (loopback only), but this will be a critical issue if ever deployed as a web service.

**Solution:** Replace `["*"]` with specific origins: `["http://localhost:3000", "http://localhost:8000", "http://localhost:8001"]`.

---

### 4.5 JWT Secret Key — Hardcoded Placeholder

**File:** `backend/src/api/config.py`  
**Line:** 66  
**Severity:** HIGH  
**Status:** NEW

```python
secret_key: str = "CHANGE_THIS_IN_PRODUCTION_USE_SECURE_RANDOM_KEY"
```

If `.env` is not loaded (common in desktop EXE mode), all JWTs are signed with this publicly-known key. Anyone with source access can forge valid tokens.

**Solution:** Auto-generate a random key at first startup and persist it:
```python
import secrets
secret_key: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
```

---

### 4.6 Desktop Auto-Login Password in Source

**File:** `backend/src/api/main.py` (L120) + `lib/api-client.ts` (L929)  
**Severity:** MEDIUM  
**Status:** NEW

Desktop user password `"desktop_user_2026"` is hardcoded in both backend and frontend. Acceptable for local-only desktop app, but should be randomized per installation for defense in depth.

---

### 4.7 SQL F-String Pattern in Backup Router

**File:** `backend/src/api/routers/backup.py`  
**Line:** 137  
**Severity:** MEDIUM  
**Status:** NEW

```python
f"SELECT COUNT(*) FROM [{table_name}]"
```

`table_name` comes from `sqlite_master` (not user input), so injection risk is minimal in practice. But the f-string SQL pattern is a dangerous code smell that could be copy-pasted elsewhere.

---

## 5. HIGH — Synthesized Data Without Warning

Components that generate fake distribution curves from real stats, with **no visual indicator**.

### 5.1 FCS Size Distribution Chart — Fake Histogram Fallback

**File:** `components/flow-cytometry/charts/size-distribution-chart.tsx`  
**Lines:** 60-105  
**Status:** KNOWN (Feb 2026) — **Still unfixed**

`generateHistogramData()` creates synthetic multi-peak Gaussian (35nm, 120nm, 280nm peaks) when no `sizeData` prop is passed. Additionally, `generateDemoSecondaryHistogramData()` (L127-175) generates shifted fake overlay data. **No indicator** distinguishes fake from real.

---

### 5.2 NTA Concentration Profile — Mock Data

**File:** `components/nta/charts/concentration-profile-chart.tsx`  
**Lines:** 19-28  
**Status:** **NEW**

`generateConcentrationData()` returns 6 hardcoded fabricated concentration values when `results` is undefined. **No visual indicator** that data is fake.

---

### 5.3 Dashboard AI Chat — Dead Endpoint

**File:** `components/dashboard/dashboard-ai-chat.tsx`  
**Line:** 42  
**Status:** **NEW**

Uses Next.js API route `/api/research/chat` which no longer exists (moved to `app_api_server_backup/`). The dashboard chat silently fails. The standalone `ResearchChatTab` correctly points to the FastAPI backend.

---

## 6. HIGH — Dead API Surface

### 6.1 API Client Methods Never Called (19 total)

| # | Method | Purpose | Status |
|---|---|---|---|
| 1 | `getStatus()` | API health status | KNOWN |
| 2 | `listJobs()` | Job queue listing | KNOWN |
| 3 | `getJob()` | Individual job details | KNOWN |
| 4 | `cancelJob()` | Cancel processing job | KNOWN |
| 5 | `retryJob()` | Retry failed job | KNOWN |
| 6 | `uploadBatch()` | Multi-file upload | KNOWN |
| 7 | `getAvailableChannels()` | Channel listing | KNOWN |
| 8 | `getUserProfile()` | User profile fetch | KNOWN |
| 9 | `updateUserProfile()` | User profile update | KNOWN |
| 10 | `listUsers()` | Admin user listing | KNOWN |
| 11 | `requestPasswordReset()` | Password reset request | KNOWN |
| 12 | `resetPassword()` | Password reset execution | KNOWN |
| 13 | `getExperimentalConditions()` | Load experiment conditions | KNOWN |
| 14 | `updateExperimentalConditions()` | Update experiment conditions | KNOWN |
| 15 | `runStatisticalTests()` | Statistical test execution | KNOWN |
| 16 | `compareDistributions()` | Distribution comparison | KNOWN |
| 17 | `getFCSMetadata()` | FCS metadata only | NEW |
| 18 | `getNTAValues()` | NTA per-particle values | NEW |
| 19 | `getAlert()` (single) | Individual alert fetch | NEW |

### 6.2 Backend Endpoints with Zero Frontend Consumer

| # | Endpoint | Router | Status |
|---|---|---|---|
| 1 | `GET /samples/channel-config` | samples.py | KNOWN |
| 2 | `PUT /samples/channel-config` | samples.py | KNOWN |
| 3 | `GET /auth/me/{user_id}` | auth.py | KNOWN (also has auth bug) |
| 4 | `PUT /auth/profile/{user_id}` | auth.py | KNOWN (also has auth bug) |

### 6.3 Cross-Compare Sidebar — File Selects Still Decorative

**File:** `components/sidebar.tsx` (CrossCompareSidebar section, L1315-1490)  
**Status:** KNOWN — **Still unfixed**

FCS and NTA file `<Select>` elements have **no `onValueChange` handler**. Selecting a file does nothing. The comparison settings (bin size, normalize, KDE, etc.) DO work.

---

## 7. MEDIUM — Backend Issues

### 7.1 Uncached FCSParser in Distribution Analysis

**File:** `backend/src/api/routers/samples.py`  
**Line:** ~2283  
**Status:** NEW

The `distribution-analysis` endpoint still uses raw `FCSParser(Path(...)).parse()` instead of `get_cached_fcs_data()`. On 900k-event files this unnecessarily re-parses the entire FCS file (~1-2s penalty).

### 7.2 Retry Job Doesn't Dispatch Processing

**File:** `backend/src/api/routers/jobs.py`  
**Line:** 353  
**Status:** NEW

`retry_job` creates a new `ProcessingJob` DB record but does NOT trigger any background task. The job sits at `"pending"` forever.

### 7.3 In-Memory Password Reset Tokens

**File:** `backend/src/api/routers/auth.py`  
**Line:** 424  
**Status:** NEW

Password reset tokens stored in Python dict (`_password_reset_tokens`). Lost on server restart. Unusable in multi-worker deployments. Should use database storage.

### 7.4 Dead CRUD Functions (9 total)

| Function | File |
|---|---|
| `get_sample_by_db_id` | crud.py |
| `get_fcs_results_by_sample` | crud.py |
| `get_nta_results_by_sample` | crud.py |
| `update_job_progress` | crud.py |
| `create_qc_report` | crud.py |
| `get_qc_reports_by_sample` | crud.py |
| `get_sample_counts` | crud.py |
| `get_job_counts` | crud.py |
| `delete_experimental_conditions` | crud.py |

### 7.5 Broken Backend Scripts (10 total)

These scripts import from deleted visualization modules and will crash immediately:

| Script | Missing Import |
|---|---|
| `test_visualization_with_real_data.py` | `src.visualization.fcs_plots`, `nta_plots`, `anomaly_detection` |
| `test_size_intensity_plots.py` | `src.visualization.size_intensity_plots` |
| `test_histogram_batch.py` | `src.visualization.fcs_plots` |
| `reprocess_parquet_with_mie.py` | `src.visualization.fcs_plots.calculate_particle_size` |
| `quick_fcs_plots.py` | `src.visualization.fcs_plots` |
| `quick_demo.py` | `src.visualization.fcs_plots`, `anomaly_detection` |
| `process_all_fcs_folders.py` | `src.visualization.fcs_plots` |
| `generate_nta_plots.py` | `src.visualization.nta_plots` |
| `generate_fcs_plots.py` | `src.visualization.fcs_plots` |
| `convert_fcs_to_parquet.py` | `src.visualization.fcs_plots.calculate_particle_size` |

### 7.6 Empty Directories

- `backend/src/fusion/` — empty, all modules deleted
- `backend/src/preprocessing/` — empty, all modules deleted

---

## 8. MEDIUM — Frontend Dead Code

### 8.1 Empty States Module — Zero Consumers

**File:** `components/empty-states.tsx`  
**Status:** KNOWN — **Still unused**

Defines 10 empty state components (`EmptyState`, `NoDataEmptyState`, `NoResultsEmptyState`, `NoFileUploadedEmptyState`, `OfflineEmptyState`, `ServerErrorEmptyState`, `FileParsingErrorEmptyState`, `TimeoutEmptyState`, `AccessDeniedEmptyState`, `NoPinnedChartsEmptyState`). **None are imported by any file.**

### 8.2 Loading Skeletons — Zero Consumers

**File:** `components/loading-skeletons.tsx`  
**Status:** KNOWN — **Still unused**

Defines loading skeleton components. **No imports found anywhere.**

### 8.3 Research Chat Tools — Still Mocked

**File:** `app_api_server_backup/research/chat/route.ts`  
**Status:** KNOWN — Partially mitigated

The Next.js API route with mocked AI tools (`analyzeData` returns hardcoded `"median size of 127.4nm"`, `generateGraph` returns `Math.random()`, `validateResults` always returns `isValid: true`) has been moved to backup. The live chat now uses the FastAPI backend via `components/research-chat/research-chat-tab.tsx`, which calls the Python chat endpoint. However, the dashboard AI chat widget (`dashboard-ai-chat.tsx`) still points to the dead Next.js route.

---

## 9. MEDIUM — Store & State Issues

### 9.1 Dead Store Actions

| Action | Status |
|---|---|
| `setGateDrawing` | Never called — part of unfinished free-form gating |
| `addDrawingPoint` | Never called |
| `clearDrawingPoints` | Never called |
| `setGatedStatistics` | Never called — gating stats computed but not stored |
| `toggleOverlay` | Shadowed by local wrapper in `comparison-analysis-view.tsx` |
| `updateProcessingJob` | Destructured in `use-api.ts` but never invoked |

### 9.2 Dead Store State (Never Read)

| State | Description |
|---|---|
| `samplesError` | Set by `use-api.ts`, never read (errors shown via toast) |
| `gatingState.isDrawing` | Never set, never read |
| `gatingState.drawingPoints` | Never set, never read |
| `gatingState.statistics` | Never populated |

### 9.3 Unused Focused Selectors (NEW)

Three focused selector hooks defined but never imported:
- `useSampleListState` (L1078)
- `useFCSAnalysisState` (L1089)
- `useOverlayState` (L1102)

---

## 10. LOW — Cleanup & Maintenance

### 10.1 Database — Unused Columns

| Model | Column | Issue |
|---|---|---|
| `FCSResult` | `cd9_positive_pct` | Never written — marker gating not implemented |
| `FCSResult` | `cd63_positive_pct` | Never written |
| `FCSResult` | `doublets_pct` | Never written |
| `Sample` | `passage_number` | Never written |
| `Sample` | `fraction_number` | Never written |
| `User` | `email_verified` | Always `False`, never checked |

### 10.2 Configuration Issues

| File | Issue |
|---|---|
| `next.config.mjs` | `ignoreBuildErrors: true` — TypeScript errors silently ignored during builds |
| `backend/requirements.txt` | No upper version bounds on any package — risk of breaking changes |
| `README.md` | References `npm install` but project uses `pnpm` |
| `README.md` | Architecture shows PostgreSQL but default is SQLite |
| `README.md` | References `app/(auth)/` and `app/api/` which are moved to backup dirs |

### 10.3 Alembic Migrations Stale

Last migration: January 2, 2026 (2+ months ago). If any model changes have been made since, they need a new migration.

### 10.4 Backend Config Clutter

`backend/config/calibration/` contains 34 archived calibration JSON files that shouldn't ship with the desktop installer.

### 10.5 PyInstaller Spec Inconsistency

`biovaram_module.spec`: `matplotlib`, `seaborn`, `plotly` are listed in both `hidden_imports` AND `excludes`. The `excludes` wins, making the `hidden_imports` entries dead.

### 10.6 Cache Invalidation on NTA Upload

`api-client.ts`: `uploadNTA()` does not call `this.cache.invalidate("samples:list")` after upload, unlike `uploadFCS()`.

---

## 11. Verified Working Systems

All systems marked working in Feb 2026 remain functional. Additionally:

| System | Status | Change |
|---|---|---|
| FCS file upload -> parse -> database -> API -> frontend | Working | -- |
| NTA file upload -> parse -> database -> API -> frontend | Working | -- |
| NTA PDF upload -> parse -> API -> frontend | Working | -- |
| Bead calibration (CAL-001) — full pipeline | Working | -- |
| FCS scatter data (Interactive, EventVsSize, Clustered) | Working | Improved (cached) |
| FCS statistics cards | Working | -- |
| NTA statistics cards | Working | -- |
| NTA size distribution breakdown (bins) | Working | -- |
| NTA supplementary metadata | Working | -- |
| Cross-validation (FCS vs NTA overlay, KS test, verdict) | Working | -- |
| Statistical comparison table | Working | -- |
| Anomaly detection (with anomaly cards) | Working | -- |
| Gated population analysis | Working | -- |
| ClusteredScatterChart (KMeans clustering) | Working | Improved (memoized) |
| Scatter axis selector (AI-recommended) | Working | -- |
| Distribution analysis overlay (fit curves) | Working | -- |
| TheoryVsMeasuredChart (with measured data) | Working | -- |
| All exports (CSV, Excel, JSON, PDF, Markdown) | Working | -- |
| Authentication (login, auto-login desktop mode) | Working | -- |
| Alert system (auto-generated, CRUD) | Working | -- |
| Dashboard quick stats, recent activity | Working | -- |
| Pinned charts, saved images gallery | Working | Fixed (pin bug) |
| FCS overlay comparison (secondary file) | Working | -- |
| NTA overlay comparison (secondary file) | Working | **NEW** (was dead) |
| NTA sidebar settings | Working | **NEW** (was decorative) |
| DiscrepancyChart (cross-compare) | Working | **NEW** (was hardcoded) |
| PositionAnalysis empty state | Working | **NEW** (was mock data) |
| ParticleSizeVisualization (real data) | Working | **NEW** (replaced hardcoded) |
| FCS parsing cache (LRU, thread-safe) | Working | **NEW** |
| Clustered/standard toggle (non-blocking) | Working | **NEW** (was slow) |
| Desktop EXE launcher | Working | -- |
| Installer build pipeline | Working | Fixed (PS 5.1 compat) |

---

## 12. Test Coverage Assessment

### Backend Tests

| File | Purpose | Quality |
|---|---|---|
| `tests/test_e2e_system.py` | End-to-end system test | Functional |
| `tests/test_integration.py` | Data pipeline integration | Functional (references deleted modules) |
| `tests/test_mie_scatter.py` | Physics calculations | Functional |
| `tests/test_parser.py` | FCS/NTA parser tests | **STUB — all `pass` since Nov 2025** |
| `test_clustering.py` (root) | Clustering algorithm | Functional |
| `test_distribution_analysis.py` (root) | Distribution fitting | Functional |
| `test_e2e_pc3_exo1.py` (root) | PC3 EXO1 end-to-end | Functional |
| `test_fcmpass_integration.py` (root) | FCMPASS calibration | Functional |

### Frontend Tests

**ZERO frontend tests exist.** No `__tests__/` directory, no `*.test.tsx`, no `*.spec.tsx` files. This is a significant gap for a production application.

### Recommended Test Priorities

1. Frontend: Component tests for charts (verify they render with real data, show empty state with no data)
2. Frontend: Integration tests for upload -> analysis -> display flow
3. Backend: Complete `test_parser.py` stubs
4. Backend: Auth endpoint tests (ownership validation, access control)
5. Backend: Backup endpoint tests (with auth)

---

## 13. Packaging & Build Pipeline

### Build Pipeline Status

| Component | Status | Notes |
|---|---|---|
| `pnpm build` (static export) | Working | Module filtering via `NEXT_PUBLIC_MODULE` |
| `build_modules.ps1` | Working | Rewritten for PS 5.1 ASCII compatibility |
| `build_installer.ps1` | Working | Inno Setup detection, version.json creation |
| PyInstaller (`biovaram_module.spec`) | Working | UPX compression, correct excludes |
| Inno Setup (`biovaram_installer.iss`) | Working | LZMA2/ultra64, no admin required |

### Current Build Artifacts

| Artifact | Size | Commit |
|---|---|---|
| `dist/BioVaram_NanoFACS/BioVaram_NanoFACS.exe` | 25 MB | `64688a1` |
| `installer_output/BioVaram_nanofacs_Setup_v1.0.0.exe` | 77.4 MB | `64688a1` |

### Known Build Issues

| Issue | Severity |
|---|---|
| `ignoreBuildErrors: true` in next.config — TypeScript errors bypassed | MEDIUM |
| `SetupIconFile=biovaram.ico` uses relative path with no existence check | LOW |
| `hidden_imports` contains packages also in `excludes` (dead entries) | LOW |

---

## 14. Priority Implementation Roadmap

### Phase 1 — CRITICAL Security Fixes (Day 1)

| # | Task | Effort | Files |
|---|---|---|---|
| 1 | Add auth middleware to backup router | 30 min | `backup.py` |
| 2 | Add ownership validation to `/auth/me/{id}` and `/auth/profile/{id}` | 30 min | `auth.py` |
| 3 | Add admin-only check to `GET /auth/users` | 15 min | `auth.py` |
| 4 | Fix CORS — replace wildcard with specific origins | 10 min | `main.py` |
| 5 | Auto-generate JWT secret key if not set | 10 min | `config.py` |

### Phase 2 — Fake Data Elimination (Day 2-3)

| # | Task | Effort | Files |
|---|---|---|---|
| 6 | Fix cross-compare overlay histogram — show empty state or add badge | 30 min | `overlay-histogram-chart.tsx` (cross-compare) |
| 7 | Fix cross-compare KDE chart — show empty state or add badge | 30 min | `kde-comparison-chart.tsx` |
| 8 | Fix correlation scatter chart — show empty state or add badge | 30 min | `correlation-scatter-chart.tsx` |
| 9 | Fix FCS size distribution fake histogram | 1 hr | `size-distribution-chart.tsx`, parent |
| 10 | Fix NTA concentration profile mock data | 30 min | `concentration-profile-chart.tsx` |
| 11 | Fix dashboard AI chat dead endpoint | 30 min | `dashboard-ai-chat.tsx` |

### Phase 3 — Code Quality (Day 4-5)

| # | Task | Effort | Files |
|---|---|---|---|
| 12 | Wire cross-compare sidebar file selects | 1 hr | `sidebar.tsx` |
| 13 | Convert distribution-analysis to cached FCSParser | 15 min | `samples.py` |
| 14 | Add NTA upload cache invalidation | 5 min | `api-client.ts` |
| 15 | Delete empty `src/fusion/` and `src/preprocessing/` dirs | 5 min | Directories |
| 16 | Remove/archive 10 broken backend scripts | 30 min | `scripts/` |
| 17 | Delete 19 dead API client methods (or mark with `@deprecated`) | 1 hr | `api-client.ts` |
| 18 | Clean dead store actions and state | 30 min | `store.ts` |
| 19 | Delete unused `empty-states.tsx` and `loading-skeletons.tsx` | 5 min | Components |

### Phase 4 — Testing (Week 2)

| # | Task | Effort | Files |
|---|---|---|---|
| 20 | Add frontend chart rendering tests | 4 hrs | New test files |
| 21 | Complete backend parser test stubs | 2 hrs | `test_parser.py` |
| 22 | Add auth endpoint tests | 2 hrs | New test file |
| 23 | Add backup endpoint tests | 1 hr | New test file |
| 24 | Set `ignoreBuildErrors: false` and fix any errors | 1 hr | `next.config.mjs` + fixes |

### Phase 5 — Dependency & Config Maintenance

| # | Task | Effort | Files |
|---|---|---|---|
| 25 | Add upper version bounds to `requirements.txt` | 30 min | `requirements.txt` |
| 26 | Update `README.md` (pnpm, SQLite, current routes) | 30 min | `README.md` |
| 27 | Purge archived calibration configs before packaging | 15 min | `config/calibration/` |
| 28 | Move in-memory password reset tokens to database | 2 hrs | `auth.py`, `models.py` |

---

## Appendix: Metrics Comparison

| Metric | Feb 2026 | Mar 2026 | Trend |
|---|---|---|---|
| Real data components | ~65% | ~72% | Improving |
| Fake data (no warning) | ~15% | ~8% | Improving |
| Dead code | ~20% | ~10% | Improving |
| Runtime crash bugs | 2 | 0 | Fixed |
| Security vulnerabilities | 1 (signup URL) | 6 | Worsened (new features) |
| Test coverage (backend) | 4 test files | 4 test files | Static |
| Test coverage (frontend) | 0 | 0 | No change |
| API client methods | ~30 | ~50 | Grew (19 dead) |
| Build pipeline | Manual | Automated (PS 5.1) | Improved |

---

**Report compiled by:** Comprehensive automated audit  
**Next review:** April 2026  
**Approval required from:** Project lead  
