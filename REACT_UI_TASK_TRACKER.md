# 📋 React UI Task Tracker
## EV Analysis Platform - Streamlit to React Migration

**Created:** December 16, 2025  
**Last Updated:** December 16, 2025  
**Overall Progress:** 85% Complete

---

## 📊 QUICK STATUS SUMMARY

| Category | Status | Progress | Priority |
|----------|--------|----------|----------|
| **Flow Cytometry Tab** | ✅ Working | 95% | - |
| **NTA Tab** | ⚠️ Partial | 85% | P1 |
| **Cross-Compare Tab** | ✅ Working | 90% | - |
| **Dashboard Tab** | ✅ Working | 90% | - |
| **Sidebar Settings** | ⚠️ Partial | 80% | P1 |
| **Chart Parity** | ⚠️ Partial | 75% | P2 |
| **Backend Connection** | ✅ Working | 95% | - |
| **Export Features** | ⚠️ Partial | 70% | P2 |

---

## 🔴 CRITICAL ISSUES (P0 - Fix Immediately)

### ISSUE-1: NTA Export Buttons Not Functional
- **Status:** ❌ NOT WORKING
- **Location:** `components/nta/nta-analysis-results.tsx` (~line 280)
- **Problem:** Export buttons exist but have `TODO: Implement actual export logic` comment
- **Impact:** Users cannot export NTA data in any format
- **Fix Required:**
```tsx
// Wire up to existing export-utils.ts functions:
import { exportToCSV, exportSizeDistribution, generateMarkdownReport } from "@/lib/export-utils"
```
- **Effort:** 30 minutes
- **Assignee:** TBD

---

## 🟠 HIGH PRIORITY ISSUES (P1 - This Week)

### ISSUE-2: NTA Sidebar Temperature Sliders Not Connected
- **Status:** ⚠️ UI ONLY - Not connected to state
- **Location:** `components/sidebar.tsx` (lines 860-915)
- **Problem:** Temperature sliders use `defaultValue` instead of controlled state
- **Current Code:**
```tsx
<Slider defaultValue={[22]} ... />
```
- **Should Be:**
```tsx
<Slider 
  value={[ntaSettings.measurementTemperature]} 
  onValueChange={(val) => setNtaSettings({ measurementTemperature: val[0] })} 
/>
```
- **Impact:** Temperature changes don't persist when navigating tabs
- **Effort:** 20 minutes
- **Assignee:** TBD

---

### ISSUE-3: Missing "Diameter vs SSC" Scatter Plot
- **Status:** ❌ MISSING
- **Streamlit Location:** Lines 3487-3530
- **React Location:** N/A - Not implemented
- **Description:** Streamlit has "Estimated Diameter vs SSC" scatter plot with anomaly highlighting
- **Required Features:**
  - Scatter plot with size (X) vs SSC intensity (Y)
  - Anomaly points highlighted in red
  - Hover tooltips
  - Pin to dashboard functionality
- **Effort:** 2 hours
- **Assignee:** TBD

---

### ISSUE-4: Missing "Full Analysis Dashboard" Combined View
- **Status:** ❌ MISSING
- **Streamlit Location:** Lines 3546-3557
- **React Location:** N/A
- **Description:** Streamlit has a collapsible "Full Analysis Dashboard" with 2x2 grid of all charts
- **Required:**
  - Theoretical vs Measured
  - Size Distribution
  - FSC vs SSC Scatter
  - Diameter vs SSC Scatter
- **Effort:** 3 hours
- **Assignee:** TBD

---

### ISSUE-5: Missing "Reset Tab" Buttons
- **Status:** ❌ MISSING
- **Streamlit Location:** Lines 3622 (FCS), 3924 (NTA)
- **React Location:** N/A
- **Description:** Streamlit has "Reset Tab" buttons to clear cached analysis and start fresh
- **Impact:** Users cannot easily clear state and re-upload
- **Effort:** 1 hour (add to FCS, NTA, and Cross-Compare tabs)
- **Assignee:** TBD

---

## 🟡 MEDIUM PRIORITY (P2 - Next Sprint)

### ISSUE-6: Chart Visual Differences

| Chart | Streamlit | React | Gap |
|-------|-----------|-------|-----|
| **Scatter Plot Colors** | Purple (#7c3aed) for normal, Red for anomalies | Blue (#3b82f6) for normal | Different color scheme |
| **Histogram Bins** | Configurable bin size | Fixed 20 bins | No bin size control |
| **Reference Lines** | D10/D50/D90 with labels | Reference lines exist but styling differs | Minor styling |
| **Legend Position** | Top-right inside chart | Top-center outside | Minor layout |
| **Dark Theme** | #111827 background | Tailwind dark mode | Slightly different grays |

**Fix Required:** Update React charts to match Streamlit color scheme for consistency
- **Effort:** 2 hours
- **Assignee:** TBD

---

### ISSUE-7: Missing NTA "Corrected View" Side-by-Side Histograms
- **Status:** ⚠️ PARTIAL
- **Streamlit Location:** Lines 4336-4500 (viz_tabs[3])
- **React Location:** `components/nta/charts/temperature-corrected-comparison.tsx` (exists)
- **Gap:** React has the component but may not show true side-by-side histograms
- **Required:** Verify and fix side-by-side raw vs corrected histograms
- **Effort:** 1-2 hours
- **Assignee:** TBD

---

### ISSUE-8: Missing Parquet Export Button
- **Status:** ❌ MISSING in UI
- **Backend:** ✅ Endpoint exists (`POST /api/v1/analysis/export/parquet`)
- **Streamlit Location:** Lines 4780-4880 (4 export buttons: CSV, Parquet, Report, Correction Reference)
- **React Current:** Only CSV export visible
- **Fix Required:** Add Parquet and Markdown report download buttons
- **Effort:** 1 hour
- **Assignee:** TBD

---

### ISSUE-9: Missing Markdown Report Generation for All Tabs
- **Status:** ⚠️ PARTIAL
- **Location:** `lib/export-utils.ts` - function exists but not exposed in all tabs
- **Required:** Add "Download Report" button to FCS, NTA, and Cross-Compare tabs
- **Effort:** 1 hour
- **Assignee:** TBD

---

### ISSUE-10: Cross-Compare Sidebar Settings Not in Sidebar
- **Status:** ⚠️ WORKS but in wrong location
- **Streamlit Location:** Left sidebar when Cross-Compare tab active (lines 4950-5000)
- **React Current:** Settings are in main content area, not sidebar
- **Settings Needed in Sidebar:**
  - Discrepancy Threshold slider
  - Normalize Histograms checkbox
  - Bin Size slider
  - Show KDE checkbox
  - Min/Max Size filters
- **Effort:** 1-2 hours (move existing component to sidebar)
- **Assignee:** TBD

---

## 🟢 LOW PRIORITY (P3 - Backlog)

### ISSUE-11: Graph Annotation Tools
- **Status:** ❌ NOT STARTED
- **From Planning Docs:** GAP-6 - "Effort: HIGH (5-7 days)"
- **Features Needed:**
  - Plotly drawing mode for annotations
  - ROI (Region of Interest) selection tool
  - Annotation storage in database
  - Export annotations with graphs
- **Effort:** 5-7 days
- **Assignee:** TBD

---

### ISSUE-12: Persistent Chat History
- **Status:** ⚠️ SESSION ONLY
- **From Planning Docs:** GAP-7 - "PARTIAL (Session only, not database)"
- **Features Needed:**
  - ChatHistory model in database
  - Save messages on send
  - Load history on session start
  - "Load Previous Session" option
- **Effort:** 2-3 days
- **Assignee:** TBD

---

### ISSUE-13: Correlation Scatter Chart Enhancement
- **Status:** ⚠️ BASIC
- **React Location:** `components/cross-compare/charts/correlation-scatter-chart.tsx`
- **Streamlit:** Has regression line, R² value, and confidence intervals
- **React Current:** Basic scatter only
- **Fix Required:** Add linear regression, R² display, and confidence bands
- **Effort:** 2-3 hours
- **Assignee:** TBD

---

### ISSUE-14: AI/ML Integration (Phase 3)
- **Status:** ⏳ BLOCKED
- **Blocker:** Waiting for AI/Data Cloud credentials from client
- **From Planning Docs:** "Phase 3: AI/ML Integration - 0% - Waiting for credentials"
- **Features Pending:**
  - Anomaly detection using trained models
  - AI-powered sample quality assessment
  - Proactive anomaly alerts
- **Effort:** 2-3 weeks (after unblock)
- **Assignee:** TBD

---

### ISSUE-15: TEM Integration (Phase 4)
- **Status:** ⏳ BLOCKED
- **Blocker:** Waiting for TEM image data from client
- **From Planning Docs:** "Phase 4: TEM Integration - ⏳ PENDING - 0%"
- **Effort:** 1-2 weeks (after data received)
- **Assignee:** TBD

---

### ISSUE-16: Western Blot Integration (Phase 5)
- **Status:** ⏳ BLOCKED
- **Blocker:** Waiting for Western Blot data from client
- **From Planning Docs:** "Phase 5: Western Blot - ⏳ PENDING - 0%"
- **Effort:** 1-2 weeks (after data received)
- **Assignee:** TBD

---

### ISSUE-17: NTA PDF Parsing
- **Status:** ⏳ BLOCKED
- **Blocker:** Waiting for sample PDF files from Surya
- **From Planning Docs:** "⏳ Waiting for PDF files from Surya"
- **Purpose:** Extract "Original Concentration" from NTA machine PDFs
- **Effort:** 2-3 days (after PDFs received)
- **Assignee:** TBD

---

## 📈 CHART PARITY COMPARISON

### Flow Cytometry Charts

| Chart | Streamlit | React | Match |
|-------|-----------|-------|-------|
| Theoretical vs Measured (FSC/SSC ratio) | ✅ Plotly | ✅ Recharts | ✅ Functional |
| Size Distribution Histogram | ✅ Plotly with D10/D50/D90 | ✅ Recharts with D10/D50/D90 | ✅ Good |
| FSC vs SSC Scatter | ✅ Plotly with anomaly highlight | ✅ Recharts with anomaly | ✅ Good |
| Diameter vs SSC Scatter | ✅ Plotly with anomaly highlight | ❌ MISSING | ❌ Gap |
| Full Analysis Dashboard (2x2) | ✅ Collapsible Plotly | ❌ MISSING | ❌ Gap |
| Size Range Distribution Bar | ✅ st.bar_chart | ✅ Recharts | ✅ Good |

### NTA Charts

| Chart | Streamlit | React | Match |
|-------|-----------|-------|-------|
| Size Distribution Histogram | ✅ Plotly with D10/D50/D90 | ✅ Recharts | ✅ Good |
| Concentration Profile | ✅ Plotly | ✅ Recharts | ✅ Good |
| Position Analysis | ✅ Multiple metrics | ✅ Recharts | ✅ Good |
| Three Size Categories Pie | ✅ Plotly pie chart | ✅ Recharts pie | ✅ Good |
| Corrected View (side-by-side) | ✅ Raw vs Corrected histograms | ⚠️ Exists but needs verification | ⚠️ Verify |

### Cross-Compare Charts

| Chart | Streamlit | React | Match |
|-------|-----------|-------|-------|
| Overlay Histogram | ✅ Plotly | ✅ Recharts | ✅ Good |
| KDE Comparison | ✅ Plotly | ✅ Recharts | ✅ Good |
| Discrepancy Bar Chart | ✅ Plotly with threshold line | ✅ Recharts | ✅ Good |
| Statistical Tests Cards | ✅ KS, Mann-Whitney | ✅ Client-side implementation | ✅ Good |
| Correlation Scatter | ✅ With regression, R² | ⚠️ Basic only | ⚠️ Needs enhancement |

---

## ✅ COMPLETED ITEMS (For Reference)

| Item | Date Completed | Notes |
|------|---------------|-------|
| FCS Upload & Parse | Dec 2025 | Working with fallback for generic channels |
| NTA Upload & Parse | Dec 2025 | Working with ZetaView format |
| FCS Statistics Cards | Dec 2025 | Shows D10/D50/D90/Mean/StdDev |
| Mie Scattering Settings in Sidebar | Dec 2025 | Wavelength, RI, angle ranges |
| Custom Size Ranges | Dec 2025 | With presets and add/remove |
| Anomaly Detection Toggle | Dec 2025 | Z-Score, IQR methods |
| Pinned Charts | Dec 2025 | With MiniChart rendering |
| Saved Images Gallery | Dec 2025 | With search and grid/list views |
| AI Chat Component | Dec 2025 | Context-aware, functional UI |
| Sample Database in Sidebar | Dec 2025 | Working list with filters |
| Re-analyze with New Parameters | Dec 2025 | Backend + Frontend connected |
| html2canvas Installation | Dec 2025 | Chart export to image |
| manifest.json Icons Fixed | Dec 2025 | Using existing icons |
| Database parquet_file_path Nullable | Dec 2025 | Schema fix applied |
| requirements.txt Updated | Dec 2025 | All dependencies listed |
| README.md Setup Instructions | Dec 2025 | Comprehensive guide |

---

## 🛠️ IMPLEMENTATION SCHEDULE

### Week 1 (Current Sprint)

| Day | Task | Priority | Effort | Status |
|-----|------|----------|--------|--------|
| Mon | ISSUE-1: NTA Export Buttons | P0 | 30 min | ⬜ TODO |
| Mon | ISSUE-2: NTA Temperature Sliders | P1 | 20 min | ⬜ TODO |
| Tue | ISSUE-3: Diameter vs SSC Scatter | P1 | 2 hrs | ⬜ TODO |
| Wed | ISSUE-5: Reset Tab Buttons | P1 | 1 hr | ⬜ TODO |
| Thu | ISSUE-4: Full Analysis Dashboard | P1 | 3 hrs | ⬜ TODO |
| Fri | Testing & Bug Fixes | - | 2 hrs | ⬜ TODO |

### Week 2

| Task | Priority | Effort |
|------|----------|--------|
| ISSUE-6: Chart Color Parity | P2 | 2 hrs |
| ISSUE-7: NTA Corrected View | P2 | 2 hrs |
| ISSUE-8: Parquet Export Button | P2 | 1 hr |
| ISSUE-9: Markdown Report All Tabs | P2 | 1 hr |
| ISSUE-10: Cross-Compare Sidebar | P2 | 2 hrs |

### Week 3+

| Task | Priority | Effort | Blocker |
|------|----------|--------|---------|
| ISSUE-11: Graph Annotations | P3 | 5-7 days | None |
| ISSUE-12: Persistent Chat | P3 | 2-3 days | None |
| ISSUE-13: Correlation Chart Enhance | P3 | 2-3 hrs | None |
| ISSUE-14: AI/ML Integration | P3 | 2-3 weeks | Credentials |
| ISSUE-15: TEM Integration | P3 | 1-2 weeks | TEM data |
| ISSUE-16: Western Blot | P3 | 1-2 weeks | WB data |
| ISSUE-17: NTA PDF Parsing | P3 | 2-3 days | PDF samples |

---

## 📝 NOTES

### Color Scheme Reference (Streamlit)
```css
--primary: #00b4d8;      /* Cyan - primary actions */
--secondary: #7c3aed;    /* Purple - scatter points */
--accent: #f72585;       /* Pink - highlights */
--success: #10b981;      /* Green - success states */
--warning: #f59e0b;      /* Orange - warnings */
--error: #ef4444;        /* Red - errors, anomalies */
--bg-card: #111827;      /* Dark card background */
```

### Recharts vs Plotly
- React uses **Recharts** (React-native, declarative)
- Streamlit uses **Plotly** (more interactive, larger bundle)
- Key difference: Recharts doesn't have built-in density plots
- KDE in React: Uses custom Gaussian kernel calculation

### API Endpoints Fully Connected
- All sample CRUD operations
- Upload (FCS, NTA, batch)
- Scatter data & size bins
- Statistical tests
- Re-analyze with parameters
- Export to Parquet

---

## 📞 CONTACTS

| Role | Name | Responsibility |
|------|------|---------------|
| Developer | Sumit Malhotra | Full-stack development |
| Client Lead | Parvesh | Technical review |
| Science Lead | Surya | NTA/FCS expertise |
| Project Manager | Charmi | Coordination |

---

*Last updated by: GitHub Copilot*
*Next review: End of Week 1*
