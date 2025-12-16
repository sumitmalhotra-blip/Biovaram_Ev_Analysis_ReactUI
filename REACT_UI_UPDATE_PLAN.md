# React UI Complete Update Plan
## Matching Streamlit Functionality - Layout & Feature Parity

**Created:** December 16, 2025  
**Purpose:** Comprehensive plan to update React UI to match Streamlit's functionality and layout exactly  

---

## Executive Summary

After detailed analysis of the Streamlit app (5,316 lines) and the current React implementation, this document outlines a complete update plan organized by **tab/section** to ensure functionality appears in the **same location** as in Streamlit.

---

## Table of Contents

1. [Global Layout Issues](#1-global-layout-issues)
2. [Dashboard Tab Updates](#2-dashboard-tab-updates)
3. [Flow Cytometry Tab Updates](#3-flow-cytometry-tab-updates)
4. [NTA Tab Updates](#4-nta-tab-updates)
5. [Cross-Comparison Tab Updates](#5-cross-comparison-tab-updates)
6. [Backend API Fixes](#6-backend-api-fixes)
7. [Implementation Priority & Timeline](#7-implementation-priority--timeline)

---

## 1. Global Layout Issues

### 1.1 Sidebar Position & Content

| Streamlit | React Current | Action Required |
|-----------|---------------|-----------------|
| Left sidebar always visible | Sidebar exists but content differs per tab | ✅ Keep sidebar, update content per tab |
| Tab-specific sidebar content | Generic sidebar | ❌ **Fix:** Sidebar must change based on active tab |

**Implementation:**
```tsx
// In sidebar.tsx - Add conditional rendering based on active tab
{activeTab === "flow-cytometry" && <FlowCytometrySidebarSettings />}
{activeTab === "nta" && <NTASidebarSettings />}
{activeTab === "cross-compare" && <CrossCompareSidebarSettings />}
{activeTab === "dashboard" && <DashboardSidebar />}
```

### 1.2 Header & Logo

| Streamlit | React Current | Action Required |
|-----------|---------------|-----------------|
| Logo top-right, Title centered | Different header layout | Minor - styling adjustment |
| Subtitle under title | Missing | Add subtitle |

---

## 2. Dashboard Tab Updates

### 2.1 Current State Analysis

| Feature | Streamlit Location | React Status | Priority |
|---------|-------------------|--------------|----------|
| Sample Database sidebar | Left sidebar | ⚠️ Partial | P1 |
| Treatment filter dropdown | Sidebar | ❌ Missing | P2 |
| Status filter dropdown | Sidebar | ❌ Missing | P2 |
| Refresh samples button | Sidebar | ⚠️ Exists differently | P2 |
| Previous projects list | Sidebar (fallback) | ⚠️ Partial | P3 |
| Pinned graphs gallery | Main content left (3/4 width) | ⚠️ Partial (metadata only, no figures) | P1 |
| Saved images gallery | Under pinned graphs | ❌ Missing | P3 |
| File uploader | Right column (1/4 width) | ✅ Exists | - |
| Metadata form | Below uploader (right column) | ⚠️ Partial | P2 |
| Analysis chatbot | Right column bottom | ⚠️ Basic | P2 |

### 2.2 Missing Features - Dashboard

#### A. Sample Database Sidebar (Streamlit lines 1750-1850)
```
Location: Left sidebar when Dashboard tab is active
Features needed:
- Sample list from API
- Treatment filter (dropdown)
- Status filter (dropdown)
- Refresh button
- Expandable sample cards with View Details button
```

#### B. Pinned Charts Gallery (Streamlit lines 1900-1950)
```
Location: Main content, left 3/4 column
Missing:
- Store actual Plotly figure objects, not just metadata
- Render interactive charts in gallery
- Maximize/fullscreen button per chart
- Unpin button per chart
- Clear all pinned button
```

#### C. Metadata Form Enhancement (Streamlit lines 1970-2100)
```
Location: Right column after file uploader
Missing fields:
- Preparation Method (SEC, Centrifugation, etc.)
- Operator name
- Notes textarea
- Validation with error messages
- Session state tracking for new file detection
```

---

## 3. Flow Cytometry Tab Updates

### 3.1 Sidebar Settings (CRITICAL - All Missing in React)

**Streamlit Location:** Left sidebar (lines 2220-2550)

| Setting | Streamlit | React Current | Priority |
|---------|-----------|---------------|----------|
| Laser wavelength input | `st.number_input("Laser wavelength (nm)", value=488.0)` | ✅ Exists in panel | - |
| Particle refractive index | `st.number_input("Particle refractive index", value=1.38)` | ✅ Exists | - |
| Medium refractive index | `st.number_input("Medium refractive index", value=1.33)` | ✅ Exists | - |
| **FSC angle range slider** | `st.slider("FSC angle range (deg)", 0, 30, (1, 15))` | ❌ **Missing** | P0 |
| **SSC angle range slider** | `st.slider("SSC angle range (deg)", 30, 180, (85, 95))` | ❌ **Missing** | P0 |
| Diameter search range | `st.slider("Diameter search range (nm)", 10, 500, (30, 220))` | ⚠️ Partial | P1 |
| Resolution points | `st.number_input("Diameter points (resolution)", value=200)` | ✅ Exists | - |

### 3.2 Custom Size Ranges (Streamlit lines 2370-2500)

**Location in Streamlit:** Left sidebar, under settings

**Current React:** Has `custom-size-ranges.tsx` component but NOT in sidebar

**Required Changes:**
1. Move `CustomSizeRanges` component to sidebar (when FCS tab active)
2. Add preset buttons:
   - "EV Standard (<50, 50-200, >200)"
   - "30-100, 100-150"
   - "40-80, 80-120"
3. Add/Remove range functionality
4. Show current ranges with delete buttons

### 3.3 Anomaly Detection Settings (Streamlit lines 2520-2570)

**Location in Streamlit:** Left sidebar, under Custom Size Ranges

| Setting | Streamlit | React Current | Priority |
|---------|-----------|---------------|----------|
| Enable checkbox | `st.checkbox("Enable Anomaly Detection")` | ⚠️ In settings panel, not sidebar | P1 |
| Method dropdown | `st.selectbox("Detection Method", ["Z-Score", "IQR", "Both"])` | ⚠️ In panel | P1 |
| Z-Score threshold slider | `st.slider("Z-Score Threshold (σ)", 2.0-5.0, default=3.0)` | ⚠️ In panel | P1 |
| IQR factor slider | `st.slider("IQR Factor", 1.0-3.0, default=1.5)` | ⚠️ In panel | P1 |
| Highlight anomalies checkbox | `st.checkbox("Highlight anomalies on scatter plots")` | ⚠️ In panel | P1 |

**Action:** Move these settings to sidebar OR make settings panel always visible in sidebar position

### 3.4 Main Content Area - Flow Cytometry

**Streamlit Layout (lines 2800-3700):**
```
1. Best Practices Guide (collapsible expanders)
2. Experiment Parameters Form (popup-style, required before analysis)
3. Data Preview
4. Column Selection (FSC/SSC dropdowns + Apply button)
5. Theoretical Model Preview (collapsible)
6. Run Analysis / Reset Tab buttons
7. Statistics Cards (4 columns)
8. Size Range Distribution (if custom ranges defined)
9. Results Preview table
10. Download button
11. Interactive Visualizations section
12. Anomaly Detection Results section
13. Scatter plots (FSC vs SSC, Diameter vs SSC)
```

**React Missing:**

| Feature | Status | Component Location |
|---------|--------|-------------------|
| Experiment Parameters Popup | ❌ Missing | New component needed |
| "Preview Theoretical Model" expander | ❌ Missing | Add to FCS tab |
| "Reset Tab" button | ❌ Missing | Add next to Run Analysis |
| Size Range Distribution cards | ⚠️ Exists but layout differs | `size-category-breakdown.tsx` |
| Anomaly size comparison table | ❌ Missing | Add to anomaly results |
| Full Analysis Dashboard (combined view) | ❌ Missing | New collapsible section |

### 3.5 Statistics Cards Fix (CRITICAL - Showing N/A)

**Root Cause:** Backend not returning all required fields

**Required Fields from Backend:**
```json
{
  "particle_size_median_nm": number,
  "particle_size_mean_nm": number,
  "fsc_median": number,
  "ssc_median": number,
  "fsc_mean": number,
  "ssc_mean": number,
  "size_statistics": {
    "d10": number,
    "d50": number,
    "d90": number,
    "std": number
  }
}
```

**Frontend Fix:** Update `statistics-cards.tsx` to:
1. Add console logging for debugging
2. Add fallback display for missing values
3. Check for alternative field names

---

## 4. NTA Tab Updates

### 4.1 Sidebar Settings (Streamlit lines 4000-4080)

**Location:** Left sidebar when NTA tab is active

| Setting | Streamlit | React Current | Priority |
|---------|-----------|---------------|----------|
| Temperature Correction toggle | In sidebar | ⚠️ In collapsible card on main content | P1 |
| Measurement Temperature | In sidebar | ⚠️ In card | P1 |
| Reference Temperature | In sidebar | ⚠️ In card | P1 |
| Medium Type dropdown | In sidebar | ⚠️ In card | P1 |
| Correction factor display | In sidebar | ⚠️ In card | P1 |
| Viscosity Reference Table | In sidebar expander | ⚠️ In card | P2 |

**Action:** Move `NTATemperatureSettings` component to sidebar

### 4.2 Main Content - NTA Tab

**Streamlit Layout (lines 4100-4500):**
```
1. File Uploader
2. Best Practices (collapsible expanders)
3. File upload confirmation
4. Data Preview
5. Column Information expander
6. Key Metrics (4 stat cards)
7. Visualization Tabs:
   - Size Distribution
   - Concentration Profile  
   - Position Analysis
   - Corrected View (with side-by-side histograms)
8. Export Options (4 buttons)
```

**React Missing:**

| Feature | Status | Priority |
|---------|--------|----------|
| Position Analysis tab | ⚠️ Component exists but not all features | P2 |
| Corrected View tab with side-by-side histograms | ❌ Missing | P1 |
| Viscosity reference table display | ⚠️ Partial | P2 |
| Correction reference table export | ❌ Missing | P2 |
| Three size categories (<50, 50-200, >200) pie chart | ❌ Missing | P1 |
| Stokes-Einstein equation display | ❌ Missing | P2 |

### 4.3 Export Options Enhancement

**Streamlit has 4 export buttons (lines 4780-4880):**
1. Download as CSV ✅ Exists in React
2. Download as Parquet ❌ Missing
3. Download Report (Markdown) ❌ Missing
4. Correction Reference CSV ❌ Missing

---

## 5. Cross-Comparison Tab Updates

### 5.1 Sidebar Settings (Streamlit lines 4950-5000)

**Location:** Left sidebar when Cross-Compare tab is active

| Setting | Streamlit | React Current | Priority |
|---------|-----------|---------------|----------|
| Discrepancy Threshold slider | Sidebar | ❌ Missing from sidebar | P1 |
| Normalize Histograms checkbox | Sidebar | ❌ Missing | P1 |
| Bin Size slider | Sidebar | ❌ Missing | P1 |
| Show KDE Overlay checkbox | Sidebar (advanced) | ❌ Missing | P2 |
| Show Statistical Tests checkbox | Sidebar (advanced) | ❌ Missing | P2 |
| Min/Max Size filters | Sidebar (advanced) | ❌ Missing | P2 |

### 5.2 Main Content - Cross-Compare

**Streamlit Layout (lines 5000-5300):**
```
1. Reset button (top right)
2. Sample info cards (2 columns - FCS and NTA)
3. Column selection dropdowns
4. Visualization Tabs:
   - Overlay Histogram
   - KDE Comparison  
   - Statistics (with comparison table)
   - Discrepancy Analysis
5. Export Options (3 buttons)
```

**React Missing:**

| Feature | Status | Priority |
|---------|--------|----------|
| Statistical Tests (KS, Mann-Whitney) | ⚠️ Component exists but needs backend | P0 |
| KDE Comparison chart | ❌ Missing | P1 |
| Correlation Scatter chart | ❌ Missing | P2 |
| Discrepancy threshold visualization | ⚠️ Partial | P1 |
| Export comparison report | ❌ Missing | P2 |
| Combined size data export | ❌ Missing | P2 |

### 5.3 Statistical Tests Implementation

**Streamlit Code (lines 5150-5180):**
```python
from scipy import stats as scipy_stats

# Kolmogorov-Smirnov test
ks_result = scipy_stats.ks_2samp(fcs_sizes, nta_sizes)

# Mann-Whitney U test  
mw_result = scipy_stats.mannwhitneyu(fcs_sizes, nta_sizes, alternative='two-sided')
```

**Backend API Needed:**
```
POST /analysis/statistical-tests
Body: { fcs_sizes: number[], nta_sizes: number[] }
Response: {
  ks_statistic: number,
  ks_pvalue: number,
  mw_statistic: number,
  mw_pvalue: number
}
```

---

## 6. Backend API Fixes

### 6.1 Critical Fixes (P0)

| Issue | Current Behavior | Required Fix |
|-------|-----------------|--------------|
| Sample ID vs Database ID | Returns `sample_id` string, UI uses it for API calls | Return numeric `id` in upload response, use `id` for API calls |
| Size-bins endpoint 404 | Uses string sample_id | Use numeric database ID |
| Statistics all N/A | Fields not populated | Calculate and return FSC/SSC median/mean during upload |

### 6.2 Missing Endpoints

| Endpoint | Purpose | Priority |
|----------|---------|----------|
| `POST /analysis/statistical-tests` | KS and Mann-Whitney tests | P0 |
| `GET /samples/{id}/theoretical-lookup` | Mie scattering lookup table | P2 |
| `POST /analysis/nta-correction` | Apply temperature correction | P2 |
| `GET /samples/{id}/export/parquet` | Parquet file download | P3 |

### 6.3 Response Field Fixes

**FCS Upload Response - Required fields:**
```json
{
  "id": 123,                          // ← CRITICAL: Numeric DB ID
  "sample_id": "L5_F10_CD81",
  "status": "completed",
  "fcs_results": {
    "event_count": 50000,
    "channels": ["VFSC-H", "VSSC1-H", ...],
    "fsc_median": 12345.67,           // ← Currently null
    "fsc_mean": 13000.50,             // ← Currently null
    "ssc_median": 8765.43,            // ← Currently null
    "ssc_mean": 9000.25,              // ← Currently null
    "particle_size_median_nm": 105.3, // ← Currently null
    "size_statistics": {
      "d10": 75.2,
      "d50": 105.3,
      "d90": 145.8,
      "std": 25.4
    }
  }
}
```

---

## 7. Implementation Priority & Timeline

### Phase 1: Critical Fixes (Week 1) - P0

| Task | Effort | Files Affected |
|------|--------|----------------|
| Fix sample ID vs database ID | 2h | `lib/api-client.ts`, backend `upload.py` |
| Fix statistics cards N/A issue | 3h | Backend calculation, `statistics-cards.tsx` |
| Add FSC/SSC angle range sliders to sidebar | 2h | `sidebar.tsx`, `store.ts` |
| Move settings to sidebar per tab | 4h | `sidebar.tsx`, all tab components |
| Implement statistical tests endpoint | 4h | Backend `analysis.py`, `statistical-tests-card.tsx` |

### Phase 2: High Priority (Week 2) - P1

| Task | Effort | Files Affected |
|------|--------|----------------|
| Custom Size Ranges in sidebar | 3h | `sidebar.tsx`, `custom-size-ranges.tsx` |
| Experiment Parameters popup | 4h | New component |
| NTA Corrected View with histograms | 4h | `nta-tab.tsx`, new chart component |
| Three size categories pie chart | 2h | `size-distribution-breakdown.tsx` |
| KDE Comparison chart | 3h | New chart component |
| Cross-compare sidebar settings | 2h | `sidebar.tsx`, `comparison-settings.tsx` |

### Phase 3: Medium Priority (Week 3) - P2

| Task | Effort | Files Affected |
|------|--------|----------------|
| Pinned charts with figure storage | 6h | `pinned-charts.tsx`, `store.ts` |
| Parquet export button | 2h | Backend endpoint, `export-utils.ts` |
| Markdown report generation | 3h | Backend or frontend |
| Position Analysis enhancements | 2h | `position-analysis.tsx` |
| Stokes-Einstein equation display | 1h | `temperature-settings.tsx` |
| Reset Tab buttons for all tabs | 2h | All tab components |

### Phase 4: Low Priority (Week 4+) - P3

| Task | Effort | Files Affected |
|------|--------|----------------|
| Correlation scatter chart | 3h | New chart component |
| Chat history export | 2h | `dashboard-ai-chat.tsx` |
| Saved images gallery | 2h | `dashboard-tab.tsx` |
| Interactive chart zoom/hover improvements | 4h | All chart components |

---

## Appendix A: Component Structure Changes

### Sidebar Content by Tab

```tsx
// sidebar.tsx structure
<Sidebar>
  <Logo />
  <TabNavigation />
  
  {activeTab === "dashboard" && (
    <>
      <SampleDatabaseSection />
      <TreatmentFilter />
      <StatusFilter />
      <RefreshButton />
      <PreviousProjectsList />
    </>
  )}
  
  {activeTab === "flow-cytometry" && (
    <>
      <MieScatteringSettings />
      <FSCAngleRangeSlider />
      <SSCAngleRangeSlider />
      <DiameterSearchRange />
      <CustomSizeRanges />
      <AnomalyDetectionSettings />
      <VisualizationSettings />
    </>
  )}
  
  {activeTab === "nta" && (
    <>
      <NTATemperatureSettings />
      <ViscosityReferenceTable />
    </>
  )}
  
  {activeTab === "cross-compare" && (
    <>
      <DiscrepancyThresholdSlider />
      <HistogramSettings />
      <AdvancedOptions />
    </>
  )}
</Sidebar>
```

### New Components Needed

1. `components/flow-cytometry/experiment-params-popup.tsx`
2. `components/flow-cytometry/sidebar-settings.tsx`
3. `components/nta/corrected-view-tab.tsx`
4. `components/nta/size-categories-pie.tsx`
5. `components/cross-compare/kde-chart.tsx`
6. `components/cross-compare/sidebar-settings.tsx`

---

## Appendix B: Quick Reference - File Mappings

| Streamlit Function | React Equivalent |
|-------------------|------------------|
| `build_theoretical_lookup()` | Backend API call |
| `estimate_diameters_vectorized()` | Backend API |
| `pin_graph_to_dashboard()` | `useAnalysisStore().addPinnedChart()` |
| `AnomalyDetector.detect_outliers_zscore()` | Backend API |
| `create_size_overlay_histogram()` | Recharts component |
| `create_kde_comparison()` | Needs implementation |
| `get_correction_factor()` | `temperature-settings.tsx` |
| `calculate_water_viscosity()` | `temperature-settings.tsx` |

---

## Appendix C: Testing Checklist

### Per-Tab Verification

- [ ] Dashboard: Sample database loads, filters work, pinned charts render
- [ ] FCS: All sidebar settings visible, analysis runs, stats show values
- [ ] NTA: Temperature correction in sidebar, all 4 viz tabs work
- [ ] Cross-Compare: Both data loads, statistical tests run, exports work

### Critical Path Testing

1. Upload FCS file → Stats not N/A
2. Run analysis → Size distribution shows
3. Pin chart → Shows in Dashboard
4. Upload NTA file → Correction applies
5. Cross-compare → Statistical tests execute

---

*This plan provides a complete roadmap to achieve feature parity with the Streamlit application while maintaining the React/Next.js architecture.*
