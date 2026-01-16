# Bio Varam EV Analysis Platform - Master Task Tracker
## Last Updated: December 24, 2025

---

## 📊 Project Status Overview

| Category | Status | Details |
|----------|--------|---------|
| **Backend Core** | ✅ 95% Complete | FCS/NTA parsing, Mie physics, preprocessing |
| **React UI** | ✅ 85% Complete | All main tabs functional (FCS, NTA, Cross-Compare) |
| **PostgreSQL DB** | ✅ Connected | 9 tables, asyncpg driver working |
| **Authentication** | 🔴 Not Started | Required for user data persistence |
| **AI Integration** | 🟡 Partial | Research chat UI exists, needs backend connection |
| **Data Conversion** | ✅ Complete | 95 FCS files → CSV + Parquet |
| **CRMIT Phase 1** | ✅ 100% Complete | FCS + NTA integration per architecture spec |
| **CRMIT Phase 2** | 🔴 Not Started | TEM integration (pending sample data) |
| **CRMIT Phase 3** | 🔴 Not Started | ML components (anomaly detection, clustering) |

---

## 📋 Task Summary (Updated from CRMIT Architecture Analysis)

### Customer-Facing Tasks (Jan 7, 2025 Meeting)

| ID | Task | Assignee | Priority | Status | Due Date |
|----|------|----------|----------|--------|----------|
| T-001 | Fix tooltip visibility on Flow Cytometry graphs | Sumit Malhotra | High | ✅ Completed | Dec 23, 2025 |
| T-002 | Implement graph overlay functionality | Sumit Malhotra | Medium | ✅ Completed | Jan 7, 2025 |
| T-003 | Make previous analysis review functional | Sumit Malhotra | High | 🔴 Not Started | Jan 7, 2025 |
| T-004 | Add authentication system (sign-in/save) | Sumit Malhotra | High | ✅ Completed | Dec 31, 2025 |
| T-005 | Convert FCS/NanoFACS files to CSV & Parquet | Sumit Malhotra | Critical | ✅ Completed | Dec 23, 2025 |
| T-006 | Schedule meeting with Surya for data context | Parvesh Reddy | High | 🔴 Not Started | Dec 24, 2025 |
| T-007 | Inform Jaganser about cell data unsuitability | Parvesh Reddy | Medium | 🔴 Not Started | Dec 24, 2025 |
| T-008 | Add contextual tags to data for AI training | Team | Medium | 🔴 Not Started | TBD |

### CRMIT Architecture Tasks (Pending - from Architecture Analysis)

| ID | Task | Category | Priority | Status | Est. Effort |
|----|------|----------|----------|--------|-------------|
| CRMIT-001 | TEM Image Analysis Module | Phase 2 - Data Ingestion | 🔴 Critical | ⏸️ Deferred | 4-6 weeks |
| CRMIT-002 | Auto Axis Selection for Scatter Plots | Phase 2 - Visualization | 🟡 High | 🔴 Not Started | 2-3 days |
| CRMIT-003 | Alert System with Timestamps | Phase 2 - Reporting | 🟡 High | 🔴 Not Started | 3-5 days |
| CRMIT-004 | Population Shift Detection | Phase 2 - Analysis | 🟡 High | 🔴 Not Started | 2-3 days |
| CRMIT-005 | Excel Export for Reports | Phase 2 - Reporting | 🟢 Medium | 🔴 Not Started | 1 day |
| CRMIT-006 | Workflow Orchestration (Celery) | Infrastructure | 🟢 Medium | 🔴 Not Started | 2-3 days |
| CRMIT-007 | Temporal Analysis (Timestamps) | Phase 2 - Analysis | 🟢 Medium | 🔴 Not Started | 1-2 days |
| CRMIT-008 | Anomaly Highlighting on Plots | Phase 2 - Visualization | 🟡 High | 🔴 Not Started | 2 days |
| CRMIT-009 | K-means/DBSCAN Clustering | Phase 3 - ML | 🟢 Medium | 🔴 Not Started | 3-4 days |
| CRMIT-010 | Autoencoder Anomaly Detection | Phase 3 - ML | 🟢 Medium | 🔴 Not Started | 1 week |
| CRMIT-011 | Western Blot Integration | Phase 4 - Future | ⏳ Planned | ⏸️ Deferred | TBD |
| CRMIT-012 | NTA vs TEM Cross-Validation | Phase 2 - Analysis | 🟡 High | ⏸️ Blocked | Needs TEM |

---

## 🏗️ Platform Architecture Status

### Frontend (React/Next.js) - 85% Complete

| Component | Status | Files | Notes |
|-----------|--------|-------|-------|
| **Flow Cytometry Tab** | ✅ Complete | 15 components | Full analysis, charts, settings |
| **NTA Tab** | ✅ Complete | 8 components | Size distribution, position analysis |
| **Cross-Compare Tab** | ✅ Complete | 6 components | Statistical tests, method comparison |
| **Dashboard** | ✅ Complete | 4 components | Summary cards, mini charts |
| **Research Chat** | 🟡 UI Only | 3 components | Needs AI backend integration |
| **Sidebar Navigation** | ✅ Complete | 2 components | Sample list, tab navigation |
| **Authentication** | ✅ Complete | - | Sign-in/sign-up implemented |

### Backend (Python/FastAPI) - 95% Complete

| Module | Status | Files | Lines | Notes |
|--------|--------|-------|-------|-------|
| **FCS Parser** | ✅ Production | 4 files | ~1,100 | Full FCS 2.0/3.0/3.1 support |
| **NTA Parser** | ✅ Production | 2 files | ~500 | NanoSight CSV parsing |
| **Mie Physics** | ✅ Production | 1 file | 825 | Particle sizing (R²=1.0000) |
| **Preprocessing** | ✅ Production | 4 files | ~1,100 | QC, normalization, binning |
| **Data Fusion** | ✅ Production | 2 files | ~600 | FCS↔NTA sample matching |
| **Visualization** | ✅ Production | 6 files | ~1,200 | Auto-scaled plots |
| **REST API** | ✅ Production | 5 files | ~800 | Upload, analysis, samples, jobs |
| **Scripts** | ✅ Production | 34 files | ~6,000 | Batch processing utilities |

### Data Storage

| Location | Type | Count | Status |
|----------|------|-------|--------|
| `backend/nanoFACS/` | Raw FCS | 75 files | ✅ Organized |
| `backend/data/uploads/` | Uploaded FCS | 19 files | ✅ Working |
| `backend/data/converted_fcs/csv/` | Converted CSV | 95 files | ✅ Complete |
| `backend/data/converted_fcs/parquet/` | Converted Parquet | 95 files | ✅ Complete |
| `backend/NTA/` | NTA Data | ~100+ files | ✅ Organized |

---

## ✅ COMPLETED TASKS

### T-001: Fix Tooltip Visibility on Flow Cytometry Graphs
**Completed:** December 23, 2025 | **Assignee:** Sumit Malhotra

**Problem:** Tooltips on charts had dark backgrounds but no text color, making them unreadable.

**Solution:** Added `color: "#f8fafc"` (white text) and `labelStyle: { color: "#94a3b8" }` to all tooltip contentStyle objects.

**Files Modified (12 tooltips across 10 files):**
- `components/flow-cytometry/charts/scatter-plot-chart.tsx`
- `components/flow-cytometry/charts/scatter-plot-with-selection.tsx`
- `components/flow-cytometry/charts/diameter-vs-ssc-chart.tsx`
- `components/flow-cytometry/charts/theory-vs-measured-chart.tsx`
- `components/nta/charts/nta-size-distribution-chart.tsx`
- `components/nta/charts/concentration-profile-chart.tsx`
- `components/nta/charts/temperature-corrected-comparison.tsx` (3 tooltips)
- `components/dashboard/mini-chart.tsx`
- `components/cross-compare/charts/discrepancy-chart.tsx`
- `components/cross-compare/charts/overlay-histogram-chart.tsx`

---

### T-005: Convert FCS/NanoFACS Files to CSV & Parquet Format
**Completed:** December 23, 2025 | **Assignee:** Sumit Malhotra

**Results:**
- **Total Files:** 95 FCS files converted
- **Success Rate:** 100%
- **Formats:** CSV (with metadata JSON) + Parquet

**Output Locations:**
- CSV: `backend/data/converted_fcs/csv/`
- Parquet: `backend/data/converted_fcs/parquet/`
- Summary: `backend/data/converted_fcs/conversion_summary.json`

**Conversion Details:**

| Folder | Files | Events Range | Channels | Channel Names |
|--------|-------|--------------|----------|---------------|
| 10000_exo_and_cd81 | 21 | 0 - 395,386 | 26 | VFSC-H, VSSC1-A, B531-H, etc. |
| CD9_and_exosome_lots | 23 | 37,510 - 100,000 | 26 | Full detector names |
| EV_HEK_TFF_DATA_05Dec25 | 8 | 23 - 581 | 23 | Surya's TFF data |
| EXP_6-10-2025 | 23 | 1,508 - 533,116 | 26 | June experiment |
| uploads | 19 | 1,980 - 199,496 | 26 | User uploads |
| frontend_uploads | 1 | 100,000 | 26 | Test upload |

**Script Created:** `backend/scripts/convert_fcs_to_formats.py`

**Channel Names Preserved:** VFSC-H, VFSC-A, VSSC1-H, VSSC1-A, BSSC-H, V447-H, B531-H, Y595-H, R670-H, etc.

---

## 🔴 PENDING TASKS

### T-002: Implement Graph Overlay Functionality
**Priority:** Medium | **Status:** ✅ Completed | **Completed:** December 24, 2025

**Description:** Customer requested ability to overlay data from multiple files on a single graph for comparison.

**Implementation Summary:**
Scientists can now upload two FCS files and compare them with overlaid graphs.

**Files Created:**
- `components/flow-cytometry/dual-file-upload-zone.tsx` - New dual file upload UI with tabs for primary/comparison files
- `components/flow-cytometry/overlay-histogram-chart.tsx` - Overlay histogram chart with toggle controls
- `components/flow-cytometry/index.ts` - Export file for all flow cytometry components

**Files Modified:**
- `lib/store.ts` - Added `SecondaryFCSAnalysisState`, `OverlayConfig` interfaces and store actions
- `hooks/use-api.ts` - Added `uploadSecondaryFCS` function
- `components/flow-cytometry/flow-cytometry-tab.tsx` - Integrated dual upload mode and overlay charts

**Features Implemented:**
1. **Upload Mode Toggle:** Switch between "Single File" and "Compare Files" modes
2. **Dual File Upload:** Tabbed interface for primary and comparison file uploads
3. **Overlay Controls:** Enable/disable overlay with visual toggle
4. **Color-Coded Graphs:** 
   - Primary file: Purple (#8b5cf6)
   - Comparison file: Orange (#f97316)
5. **Show/Hide Controls:** Toggle visibility of each dataset independently
6. **Statistics Comparison:** Side-by-side statistics for both files (FSC Mean, SSC Mean, Events, Size D50)
7. **Two Overlay Charts:**
   - Size Distribution Overlay (FSC-A)
   - Granularity Overlay (SSC-A)

**Store State Added:**
```typescript
SecondaryFCSAnalysisState: {
  file, sampleId, results, isAnalyzing, error, experimentalConditions
}
OverlayConfig: {
  enabled, primaryColor, secondaryColor, primaryLabel, secondaryLabel
}
```

---

### T-003: Make Previous Analysis Review Functional
**Priority:** High | **Status:** 🔴 Not Started | **Due:** Jan 7, 2025

**Description:** Sidebar shows previous samples but clicking doesn't load their analysis.

**Requirements:**
- Make sample selection in sidebar clickable
- Load saved analysis results
- Display historical data

**Dependencies:**
- T-004 (Authentication) - need user context to save/retrieve analyses

**Technical Approach:**
- Database storage for analysis results
- Sample-to-analysis mapping
- State management for switching analyses

---

### T-004: Add Authentication System (Sign-in/Save)
**Priority:** High | **Status:** 🔴 Not Started | **Due:** Jan 7, 2025

**Description:** Add user authentication so users can sign in and save their analysis data.

**Requirements:**
- User sign-in/sign-up
- Save analysis data per user
- Load previous analyses on login

**Estimated Effort:** 30 min - 1 hour

**Technical Options:**
1. **NextAuth.js** - Easy integration with Next.js
2. **JWT tokens** - Simple custom auth
3. **OAuth providers** - Google/GitHub login

**Implementation Plan:**
1. Add NextAuth.js with credentials provider
2. Create user table in database
3. Associate analyses with user_id
4. Add login/logout UI in header

---

### T-006: Schedule Meeting with Surya for Data Context
**Priority:** High | **Status:** 🔴 Not Started | **Assignee:** Parvesh Reddy

**Description:** Need Surya to explain technical terms in FCS data files.

**Topics to Discuss:**
- What does "HK 100k DA" mean?
- What does "Permeate 500" refer to?
- Explanation of each experiment/file
- Contextual tags for AI training

**Constraints:**
- Surya off December 25-31
- Charmi available 3-4 PM (not Fridays)
- Meeting AFTER T-005 complete (✅ Done)

---

### T-007: Inform Jaganser About Cell Data Unsuitability
**Priority:** Medium | **Status:** 🔴 Not Started | **Assignee:** Parvesh Reddy

**Key Points:**
- Cell data (micrometer) ≠ Exosome data (nanometer)
- Cell data useful for learning but NOT for training production model
- Need actual exosome data for real model training

---

### T-008: Add Contextual Tags to Data for AI Training
**Priority:** Medium | **Status:** 🔴 Not Started | **Depends On:** T-005 ✅, T-006

**Expected Tags:**
- Experiment description
- Sample type (EV source, cell line)
- Processing stage (BeforeTFF, Wash, Final, Permeate)
- Measurement type (Scatter vs Fluorescence)
- Expected outcomes/normal values

---

## 🔴 CRMIT ARCHITECTURE PENDING TASKS (Detailed)

### CRMIT-001: TEM Image Analysis Module
**Priority:** 🔴 Critical | **Status:** ⏸️ Deferred (Pending Sample Data) | **Est. Effort:** 4-6 weeks

**CRMIT Requirement:** Computer vision on TEM image files for particle analysis.

**Required Components:**
1. **Scale Bar Detection** - Template matching or OCR
2. **Particle Segmentation** - Watershed algorithm, contour detection
3. **Size Measurement** - Pixel calibration using scale bar
4. **Noise Filtering** - Morphological operations

**Technologies:** OpenCV + scikit-image (as CRMIT specified)

**Dependencies:** 
- TEM sample data from client
- Will be implemented when data becomes available

---

### CRMIT-002: Auto Axis Selection for Scatter Plots
**Priority:** 🟡 High | **Status:** 🔴 Not Started | **Est. Effort:** 2-3 days

**CRMIT Requirement:** Automatically select optimal X/Y axis combinations for scatter plots.

**Implementation:**
```python
def select_best_scatter_axes(data: pd.DataFrame) -> Tuple[str, str]:
    """
    Auto-select best axes based on:
    - Variance (spread of data)
    - Correlation (avoid highly correlated axes)
    - Scientific relevance (FSC-A vs SSC-A preferred)
    """
```

**Location:** Add to `src/visualization/` or `components/flow-cytometry/`

---

### CRMIT-003: Alert System with Timestamps
**Priority:** 🟡 High | **Status:** 🔴 Not Started | **Est. Effort:** 3-5 days

**CRMIT Requirement:** Flag specific anomalies with timestamps for researcher review.

**Implementation:**
1. Create `alerts` database table
2. Generate alerts during analysis
3. Dashboard alert panel in React UI
4. Email notifications (optional)

**Schema:**
```sql
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    sample_id INTEGER REFERENCES samples(id),
    alert_type VARCHAR(50),  -- 'anomaly', 'quality_warning', 'threshold_exceeded'
    severity VARCHAR(20),     -- 'low', 'medium', 'high', 'critical'
    message TEXT,
    timestamp TIMESTAMP DEFAULT NOW(),
    acknowledged BOOLEAN DEFAULT FALSE
);
```

---

### CRMIT-004: Population Shift Detection
**Priority:** 🟡 High | **Status:** 🔴 Not Started | **Est. Effort:** 2-3 days

**CRMIT Requirement:** Compare repeat measurements to detect population shifts.

**Implementation:**
- Kolmogorov-Smirnov test for distribution comparison
- Statistical significance thresholds
- Visualization of shifts over time

**Location:** Add to `src/preprocessing/` or statistical analysis module

---

### CRMIT-005: Excel Export for Reports
**Priority:** 🟢 Medium | **Status:** 🔴 Not Started | **Est. Effort:** 1 day

**CRMIT Requirement:** Generate reports in Excel format (in addition to PDF).

**Implementation:**
- Add `openpyxl` or `xlsxwriter` to requirements
- Multi-sheet Excel with summary, raw data, statistics
- Optional: Charts embedded in Excel

---

### CRMIT-006: Workflow Orchestration
**Priority:** 🟢 Medium | **Status:** 🔴 Not Started | **Est. Effort:** 2-3 days

**CRMIT Recommendation:** Apache Airflow or Luigi for pipeline orchestration.

**Our Approach:**
- Use Celery + Celery Beat (already in stack)
- Task scheduling for batch processing
- Retry logic for failed tasks
- Pipeline monitoring dashboard

---

### CRMIT-007: Temporal Analysis
**Priority:** 🟢 Medium | **Status:** 🔴 Not Started | **Est. Effort:** 1-2 days

**CRMIT Requirement:** Analyze data correlation over time (temporal alignment).

**Implementation:**
- Parse experiment timestamps from filenames/metadata
- Temporal trend analysis
- Batch effect detection
- Time-series visualization

---

### CRMIT-008: Anomaly Highlighting on Plots
**Priority:** 🟡 High | **Status:** 🔴 Not Started | **Est. Effort:** 2 days

**CRMIT Requirement:** Highlight anomalies (e.g., red dots for outliers) directly on scatter plots.

**Implementation:**
- Extend Recharts scatter plots to support anomaly coloring
- Configurable threshold for anomaly detection
- Legend for normal vs anomaly points

---

### CRMIT-009: K-means/DBSCAN Clustering
**Priority:** 🟢 Medium | **Status:** 🔴 Not Started | **Est. Effort:** 3-4 days

**CRMIT Requirement:** Unsupervised clustering for pattern recognition.

**Implementation:**
- K-means for known cluster counts
- DBSCAN for density-based clustering
- Silhouette score optimization
- Cluster visualization in UI

---

### CRMIT-010: Autoencoder Anomaly Detection
**Priority:** 🟢 Medium | **Status:** 🔴 Not Started | **Est. Effort:** 1 week

**CRMIT Requirement:** Use autoencoders for anomaly detection.

**Implementation:**
- PyTorch autoencoder model
- Training on "normal" samples
- Reconstruction error as anomaly score
- Threshold tuning

---

### CRMIT-011: Western Blot Integration
**Priority:** ⏳ Planned | **Status:** ⏸️ Deferred | **Est. Effort:** TBD

**CRMIT Requirement:** Future data source integration (early 2025).

**Current Status:** Architecture designed to be extensible. Will implement when data format is defined.

---

### CRMIT-012: NTA vs TEM Cross-Validation
**Priority:** 🟡 High | **Status:** ⏸️ Blocked | **Est. Effort:** 2-3 days

**CRMIT Requirement:** Cross-validate particle sizes between NTA and TEM measurements.

**Dependencies:** 
- CRMIT-001 (TEM module) must be complete first
- Blocked until TEM data available

Based on `backend/docs/technical/CRMIT_ARCHITECTURE_ANALYSIS.md`:

### Layer Implementation Status

| Layer | CRMIT Spec | Our Status | Notes |
|-------|------------|------------|-------|
| **1. Data Ingestion** | FCS, NTA, TEM, Western | ✅ FCS + NTA | TEM/Western deferred |
| **2. Preprocessing** | QC, Normalization, Binning | ✅ Complete | 825+ lines |
| **3. Computer Vision** | TEM segmentation | ⏸️ Deferred | Pending TEM samples |
| **4. Multi-Modal Fusion** | Sample matcher, features | ✅ Complete | 553 lines |
| **5. Anomaly Detection** | Statistical + ML | 🟡 Partial | Stats done, ML pending |
| **6. Visualization** | Interactive plots, dashboards | ✅ Complete | React UI |
| **7. AI/ML Core** | Unsupervised, semi-supervised | 🔴 Not Started | Needs data tags first |

### Phase Completion Summary

| Phase | Scope | Status | Remaining Tasks |
|-------|-------|--------|-----------------|
| **Phase 1** | FCS + NTA Integration | ✅ 100% Complete | None |
| **Phase 2** | Visualization & Analysis Enhancements | 🔴 30% | CRMIT-002,003,004,005,006,007,008 |
| **Phase 3** | AI/ML Components | 🔴 Not Started | CRMIT-009, 010 |
| **Phase 4** | TEM + Western Blot | ⏸️ Pending Data | CRMIT-001, 011, 012 |

### Critical Findings from CRMIT Analysis

| # | Finding | Impact | Task ID |
|---|---------|--------|---------|
| 1 | TEM data not scoped | ❌ Missing component | CRMIT-001 |
| 2 | Auto axis selection missing | ⚠️ Key feature | CRMIT-002 |
| 3 | Alert system not scoped | ⚠️ Core CRMIT feature | CRMIT-003 |
| 4 | Population shift detection missing | ⚠️ Anomaly detection core | CRMIT-004 |
| 5 | Excel export missing | ⚠️ Low effort add | CRMIT-005 |
| 6 | Anomaly highlighting missing | ⚠️ Visualization gap | CRMIT-008 |
| 7 | ML clustering not started | ⚠️ Phase 3 dependency | CRMIT-009, 010 |

---

## 📅 Timeline & Milestones

| Date | Milestone | Status |
|------|-----------|--------|
| Dec 23, 2025 | T-001 Tooltip fix | ✅ Complete |
| Dec 23, 2025 | T-005 FCS conversion | ✅ Complete |
| Dec 24, 2025 | PostgreSQL database connected | ✅ Complete |
| Dec 24-26, 2025 | T-006 Schedule Surya meeting | 🔴 Pending |
| Dec 25-31, 2025 | Holiday period | ⏸️ Reduced work |
| Jan 1, 2025 | Team returns | - |
| Jan 7, 2025 | Customer meeting - UI ready | T-002, T-003, T-004 |
| Mid-Jan 2025 | Deliverable package | Depends on AI integration |
| Post-Jan 2025 | CRMIT Phase 2 tasks | CRMIT-002 to CRMIT-008 |
| Q1 2025 | CRMIT Phase 3 (ML) | CRMIT-009, CRMIT-010 |
| TBD | TEM Integration | CRMIT-001 (when data available) |

---

## 📁 Key Documentation Files

| File | Purpose | Location |
|------|---------|----------|
| **Master Backend Docs** | 54 Python files documented | `backend/docs/technical/MASTER_BACKEND_DOCUMENTATION.md` |
| **CRMIT Architecture** | Architecture analysis | `backend/docs/technical/CRMIT_ARCHITECTURE_ANALYSIS.md` |
| **Mie Physics** | Sizing methods comparison | `backend/docs/technical/MIE_SIZING_METHODS_COMPARISON.md` |
| **Filename Parsing** | Sample ID extraction rules | `backend/docs/technical/FILENAME_PARSING_RULES.md` |
| **README** | Quick start guide | `README.md` |

---

## 📌 Key Decisions from Dec 22 Meeting

1. **AI Training Data**: Cell data (μm) for learning only, NOT for production model. Need real exosome data (nm).

2. **NTA vs FCS Correlation**: Limited to size comparison only. NTA has size; FCS has size + 20 markers.

3. **Deliverable Timeline**: Mid-January (15th-16th) target, dependent on AI integration.

4. **Expected Data**: Jaganser promised 40-50 files + TEM images by end of December.

---

## 📞 Communication Notes

- **Sumit → Parvesh**: ⚠️ WhatsApp when T-005 conversion complete (DONE - NOTIFY NOW!)
- **Parvesh → Jaganser/Surya**: Schedule data context meeting
- **Charmi availability**: 3-4 PM, not Fridays

---

## 📝 Meeting Attendees (Dec 22, 2025)
- Parvesh Reddy
- Sumit Malhotra
- Charmi Dholakia
- (Jaganser - not present)

---

*Last Updated: December 24, 2025*
*Next Review: January 7, 2025 (Customer Meeting)*
