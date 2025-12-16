# EV Analysis Platform: Streamlit vs React UI Feature Comparison Report

**Generated:** December 2024  
**Purpose:** Document missing functionality in React UI compared to Streamlit implementation

---

## Executive Summary

The Streamlit application (5,316 lines) is a comprehensive EV (Extracellular Vesicle) analysis platform with advanced features that need to be replicated in the React/Next.js frontend. This report identifies **all missing features** and provides implementation guidance.

---

## Table of Contents

1. [Critical Missing Features](#1-critical-missing-features)
2. [Flow Cytometry Tab Analysis](#2-flow-cytometry-tab-analysis)
3. [NTA Tab Analysis](#3-nta-tab-analysis)
4. [Cross-Comparison Tab Analysis](#4-cross-comparison-tab-analysis)
5. [Dashboard Features](#5-dashboard-features)
6. [AI Chatbot Features](#6-ai-chatbot-features)
7. [Backend API Gaps](#7-backend-api-gaps)
8. [UI/UX Differences](#8-uiux-differences)
9. [Implementation Priority Matrix](#9-implementation-priority-matrix)

---

## 1. Critical Missing Features

### 🔴 HIGH PRIORITY - Currently Breaking

| Issue | Streamlit Behavior | React Current State | Fix Required |
|-------|-------------------|---------------------|--------------|
| **Statistics showing N/A** | Displays Median Size, FSC Median, SSC Median, FSC Mean, SSC Mean | All showing "N/A" | Backend not returning these values OR frontend not reading correct fields |
| **Sample not found error** | Uses numeric database ID for API calls | Uses string sample_id causing 404 errors | Use `response.id` (numeric) instead of `response.sample_id` |
| **Size bins not loading** | Calculates size categories from estimated diameters | Error: "Sample L5_F10_ISO not found" | Backend endpoint using wrong identifier lookup |

### Root Cause Analysis

**CRITICAL FINDING: Database samples table is EMPTY**

The actual root cause is that **database operations are failing silently** during FCS upload:

1. When you upload an FCS file, the backend tries to create a Sample record
2. If database creation fails (lines 400-402 of `upload.py`), it logs a warning but **continues with the response**
3. The response still returns `success: true` with a generated temp ID
4. When the UI later calls `/samples/{sample_id}/size-bins`, the sample doesn't exist in the database!

**Evidence:**
```sql
-- Running this query shows:
SELECT * FROM samples;
-- Returns: 0 rows (empty table!)
```

**Code that hides the error (upload.py lines 400-405):**
```python
except Exception as db_error:
    logger.warning(f"⚠️ Database operation failed: {db_error}")
    logger.warning("   Continuing with file-based response...")
    db_sample = None  # <-- This causes all future API calls to fail!
```

**Fix Required:**
1. ✅ Restart the backend server with proper venv Python:
   ```powershell
   cd backend
   .\venv\Scripts\python.exe -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```
2. **Re-upload the FCS file** - the previous upload happened when database wasn't configured
3. The sample will now be saved to database and subsequent API calls will work

---

## 2. Flow Cytometry Tab Analysis

### 2.1 Sidebar Settings Panel

#### ✅ Implemented in React
- None of the sidebar settings are implemented

#### ❌ Missing in React (ALL from Streamlit lines 2220-2400)

| Feature | Streamlit Implementation | React Status |
|---------|-------------------------|--------------|
| **Laser wavelength input** | `st.number_input("Laser wavelength (nm)", value=488.0)` | ❌ Missing |
| **Particle refractive index** | `st.number_input("Particle refractive index", value=1.38)` | ❌ Missing |
| **Medium refractive index** | `st.number_input("Medium refractive index", value=1.33)` | ❌ Missing |
| **FSC angle range slider** | `st.slider("FSC angle range (deg)", 0, 30, (1, 15))` | ❌ Missing |
| **SSC angle range slider** | `st.slider("SSC angle range (deg)", 30, 180, (85, 95))` | ❌ Missing |
| **Diameter search range** | `st.slider("Diameter search range (nm)", 10, 500, (30, 220))` | ❌ Missing |
| **Resolution points** | `st.number_input("Diameter points (resolution)", value=200)` | ❌ Missing |

#### 2.2 Custom Size Range Analysis

❌ **COMPLETELY MISSING IN REACT**

Streamlit (lines 2258-2335):
```python
# USER-DEFINED SIZE RANGES - Let users choose their own size categories
if "custom_size_ranges" not in st.session_state:
    st.session_state.custom_size_ranges = [
        {"name": "Small EVs", "min": 30, "max": 100},
        {"name": "Medium EVs", "min": 100, "max": 150},
        {"name": "Large EVs", "min": 150, "max": 200},
    ]

# Add/Remove ranges dynamically
# Quick preset buttons:
# - EV Standard (<50, 50-200, >200)
# - 30-100, 100-150
# - 40-80, 80-120
```

**Required Implementation:**
1. Create `CustomSizeRanges` component with:
   - List of current ranges with delete buttons
   - "Add New Range" form (name, min, max)
   - Preset buttons for common ranges
2. Store in Zustand state
3. Calculate particle counts per range from size data

### 2.3 Mie Scattering Calculations

❌ **BACKEND ONLY - Not exposed to frontend**

Streamlit performs these calculations client-side (lines 1500-1620):
```python
@st.cache_data
def build_theoretical_lookup(lambda_nm, n_particle, n_medium, fsc_range, ssc_range, diameters):
    """Build theoretical FSC/SSC ratio lookup table using Mie scattering theory."""
    # Uses PyMieScatt for full Mie calculation
    for i, D in enumerate(diameters):
        intensity = PMS.ScatteringFunction(n_particle/n_medium, D, lambda_nm, angles)
        # Integrate over FSC and SSC angle ranges
        I_FSC = np.trapz(intensity[mask_f], angles[mask_f])
        I_SSC = np.trapz(intensity[mask_s], angles[mask_s])
        ratios[i] = I_FSC / I_SSC if I_SSC != 0 else np.nan
```

**Current React Status:** Backend performs calculation, frontend just displays results.

### 2.4 Anomaly Detection

#### ✅ Partially Implemented in React
- Anomaly summary card with count/percentage
- Anomaly events table

#### ❌ Missing Features

| Feature | Streamlit | React |
|---------|-----------|-------|
| **Method selection** | Dropdown: Z-Score, IQR, Both | ❌ Missing |
| **Z-Score threshold slider** | 2.0 - 5.0, default 3.0 | ❌ Missing |
| **IQR factor slider** | 1.0 - 3.0, default 1.5 | ❌ Missing |
| **Highlight on scatter plots** | Toggle checkbox | ❌ Missing |
| **Anomaly size statistics comparison** | Table comparing anomaly vs normal sizes | ❌ Missing |

Streamlit anomaly detection (lines 3350-3500):
```python
if enable_anomaly_detection:
    detector = AnomalyDetector()
    df_zscore = detector.detect_outliers_zscore(df, channels, threshold=zscore_threshold)
    df_iqr = detector.detect_outliers_iqr(df, channels, factor=iqr_factor)
    
    # Size comparison table
    size_comparison = pd.DataFrame({
        'Metric': ['Mean (nm)', 'Median (nm)', 'Std Dev (nm)', 'Min (nm)', 'Max (nm)'],
        'Anomalies': [...],
        'Normal': [...]
    })
```

### 2.5 Interactive Visualizations

#### ✅ Implemented in React (Basic)
- Size Distribution Chart (static)
- Theory vs Measured Chart (static)
- FSC vs SSC Scatter (partial)

#### ❌ Missing Features

| Visualization | Streamlit Feature | React Status |
|--------------|-------------------|--------------|
| **Interactive hover** | Plotly with hover details | ❌ Missing (Recharts basic) |
| **Zoom/Pan** | Plotly drag to zoom | ❌ Missing |
| **Anomaly highlighting** | Red markers for outliers | ❌ Missing |
| **Size range overlays** | Colored regions for custom ranges | ❌ Missing |
| **Export to PNG** | Download button per chart | ⚠️ Partial |
| **Pin to Dashboard** | Pin button with Plotly figure storage | ⚠️ Partial (no figure data) |

### 2.6 Statistics Display

#### ❌ Missing Statistics (Currently showing N/A)

From Streamlit (lines 3050-3080):
```python
# Display stat cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"Median Size (nm): {median_val:.1f}")
with col2:
    st.markdown(f"D50 (nm): {d50_val:.1f}")
with col3:
    st.markdown(f"Std Dev (nm): {std_val:.1f}")
with col4:
    st.markdown(f"Valid Particles: {count_total:,}")
```

**React Issue:** The `StatisticsCards` component reads from `results` but backend may not be populating all fields.

**Required Backend Fields:**
- `particle_size_median_nm`
- `particle_size_mean_nm`
- `fsc_median`
- `ssc_median`
- `fsc_mean`
- `ssc_mean`
- `size_statistics.d10`
- `size_statistics.d50`
- `size_statistics.d90`
- `size_statistics.std`

---

## 3. NTA Tab Analysis

### 3.1 Temperature Correction System

#### ✅ Partially Implemented
- `NTATemperatureSettings` component exists

#### ❌ Missing Features

| Feature | Streamlit (lines 3900-4200) | React Status |
|---------|---------------------------|--------------|
| **Viscosity reference table** | `get_viscosity_temperature_table(15, 40, 5)` | ❌ Missing |
| **Correction factor table** | `get_correction_reference_table([18,20,22,25,30,37], 25.0)` | ❌ Missing |
| **Side-by-side histogram** | Raw vs Corrected comparison | ❌ Missing |
| **Stokes-Einstein equation display** | LaTeX formula with explanation | ❌ Missing |
| **Detailed stats comparison** | D10, D25, D50, D75, D90, Mean, Std, CV | ❌ Missing |

Streamlit correction logic (lines 4050-4150):
```python
# Apply temperature correction
size_data_corrected = size_data_raw * nta_correction_factor

# Calculate correction factor
def get_correction_factor(measurement_temp, reference_temp, media_viscosity):
    eta_ref = calculate_water_viscosity(reference_temp)
    T_meas = measurement_temp + 273.15  # Convert to Kelvin
    T_ref = reference_temp + 273.15
    return (eta_ref / media_viscosity) * (T_meas / T_ref)
```

### 3.2 NTA Visualization Tabs

#### ❌ Missing Tabs

Streamlit has 4 visualization tabs (lines 4350-4500):

1. **📊 Size Distribution** - ✅ Implemented
2. **📈 Concentration Profile** - ⚠️ Partial
3. **🗺️ Position Analysis** - ❌ Missing
4. **🌡️ Corrected View** - ❌ Missing

**Position Analysis (11-position uniformity):**
```python
# Check for uniformity (CV analysis)
cv_conc = (conc_data.std() / conc_data.mean()) * 100
if cv_conc < 20:
    st.success("✅ Good uniformity! CV: {cv_conc:.1f}%")
elif cv_conc < 30:
    st.warning("⚠️ Moderate uniformity. CV: {cv_conc:.1f}%")
else:
    st.error("❌ Poor uniformity. CV: {cv_conc:.1f}%")
```

### 3.3 Export Options

#### ❌ Missing Export Features

| Export Type | Streamlit | React |
|-------------|-----------|-------|
| CSV download | ✅ Yes | ⚠️ Basic |
| Parquet download | ✅ Yes | ❌ Missing |
| Markdown report | ✅ Yes | ❌ Missing |
| Correction reference CSV | ✅ Yes | ❌ Missing |

---

## 4. Cross-Comparison Tab Analysis

### 4.1 Sample Selection

#### ✅ Implemented
- Dropdown selection for FCS and NTA samples
- Auto-select current analysis

#### ❌ Missing Features

| Feature | Streamlit | React |
|---------|-----------|-------|
| **Reset button** | Clear all comparison data | ❌ Missing |
| **File info cards** | Shows filename, event count | ⚠️ Basic |

### 4.2 Comparison Visualizations

#### ⚠️ Partially Implemented

| Visualization | Streamlit | React Status |
|--------------|-----------|--------------|
| **Overlay Histogram** | `create_size_overlay_histogram()` | ✅ Implemented |
| **KDE Comparison** | `create_kde_comparison()` | ❌ Missing |
| **Statistical Tests** | KS test, Mann-Whitney U | ❌ Missing |
| **Discrepancy Chart** | `create_discrepancy_chart()` | ✅ Implemented |
| **Correlation Scatter** | `create_correlation_scatter()` | ❌ Missing |

### 4.3 Statistical Tests

#### ❌ MISSING - Critical for Scientific Analysis

Streamlit (lines 5050-5100):
```python
from scipy import stats as scipy_stats

# Kolmogorov-Smirnov test
ks_result = scipy_stats.ks_2samp(fcs_sizes, nta_sizes)
ks_stat = float(ks_result[0])
ks_pval = float(ks_result[1])

# Mann-Whitney U test
mw_result = scipy_stats.mannwhitneyu(fcs_sizes, nta_sizes, alternative='two-sided')
mw_stat = float(mw_result[0])
mw_pval = float(mw_result[1])
```

**Required Implementation:**
- Backend endpoint: `POST /analysis/statistical-tests` 
- Parameters: `fcs_sizes[]`, `nta_sizes[]`
- Returns: KS statistic, KS p-value, MW statistic, MW p-value
- Frontend: `StatisticalTestsCard` component with interpretation

### 4.4 Export Comparison Report

#### ❌ Missing

Streamlit generates markdown report (lines 5200-5250):
```markdown
# Cross-Instrument Comparison Report

## Files Compared
- **FCS:** {fcs_filename}
- **NTA:** {nta_filename}

## Size Distribution Statistics
| Metric | FCS | NTA | Difference |
|--------|-----|-----|------------|
| D10 (nm) | ... | ... | ...% |
...

## Assessment
Threshold: 15%
✅ All measurements within threshold
```

---

## 5. Dashboard Features

### ❌ Missing Features

| Feature | Streamlit | React Status |
|---------|-----------|--------------|
| **Pinned Charts Gallery** | Store actual Plotly figures | ⚠️ Stores metadata only |
| **Chart resize/fullscreen** | Maximize button | ❌ Missing |
| **Recent Activity Feed** | Upload history with timestamps | ⚠️ Basic |
| **Quick Stats Overview** | Summary cards for all analyses | ⚠️ Basic |

---

## 6. AI Chatbot Features

### ✅ Implemented
- Basic chat interface
- File context awareness
- Expandable/collapsible UI

### ❌ Missing Features

| Feature | Streamlit | React Status |
|---------|-----------|--------------|
| **Sample-specific context** | Pass sample data to AI | ⚠️ Basic |
| **Analysis results context** | Include statistics in prompt | ⚠️ Basic |
| **Export chat history** | Download conversation | ❌ Missing |
| **Clear chat** | Reset conversation | ❌ Missing |

---

## 7. Backend API Gaps

### 7.1 Missing Endpoints

| Endpoint | Purpose | Priority |
|----------|---------|----------|
| `GET /samples/{id}/scatter-data` | Get FSC/SSC scatter points | ✅ Implemented |
| `GET /samples/{id}/size-bins` | Get size category counts | ⚠️ Has bug |
| `POST /analysis/statistical-tests` | KS and MW tests | ❌ Missing |
| `GET /samples/{id}/theoretical-lookup` | Mie scattering table | ❌ Missing |
| `POST /analysis/nta-correction` | Apply temperature correction | ❌ Missing |

### 7.2 Response Field Issues

**FCS Results - Missing Fields:**
```json
{
  "fsc_median": null,       // Should be number
  "ssc_median": null,       // Should be number
  "fsc_mean": null,         // Should be number
  "ssc_mean": null,         // Should be number
  "size_statistics": {
    "d10": null,            // Should be number
    "d50": null,            // Should be number
    "d90": null,            // Should be number
    "std": null             // Should be number
  }
}
```

---

## 8. UI/UX Differences

### 8.1 Styling

| Element | Streamlit | React |
|---------|-----------|-------|
| **Glass cards** | Custom CSS with blur effect | ✅ Similar |
| **Stat cards** | Gradient backgrounds | ⚠️ Simpler |
| **Dark theme** | Comprehensive custom CSS | ✅ Implemented |
| **Animations** | fadeIn, hover effects | ⚠️ Basic |

### 8.2 Responsive Design

| Breakpoint | Streamlit | React |
|------------|-----------|-------|
| Mobile (<768px) | CSS media queries | ✅ Tailwind responsive |
| Tablet | Adjusted padding | ✅ Implemented |
| Desktop | Full layout | ✅ Implemented |

### 8.3 Best Practices Guides

| Tab | Streamlit | React |
|-----|-----------|-------|
| **FCS Best Practices** | Expandable sections | ✅ Implemented |
| **NTA Best Practices** | Expandable sections | ✅ Implemented |

---

## 9. Implementation Priority Matrix

### 🔴 P0 - Critical (Fix Immediately)

| Issue | Effort | Impact |
|-------|--------|--------|
| Fix sample ID vs database ID mismatch | 2 hours | Fixes all "not found" errors |
| Populate FSC/SSC median/mean in backend | 2 hours | Fixes N/A statistics |
| Fix size-bins endpoint lookup | 1 hour | Enables size category display |

### 🟠 P1 - High Priority (This Week)

| Feature | Effort | Impact |
|---------|--------|--------|
| Custom size range editor | 4 hours | Matches Streamlit core feature |
| Anomaly detection settings | 3 hours | Enable user control |
| Interactive chart zoom/hover | 4 hours | Better data exploration |
| Statistical tests (KS, MW) | 4 hours | Scientific validation |

### 🟡 P2 - Medium Priority (This Sprint)

| Feature | Effort | Impact |
|---------|--------|--------|
| Mie scattering settings panel | 6 hours | Advanced analysis |
| NTA temperature correction UI | 4 hours | Data correction |
| Position analysis tab | 3 hours | Complete NTA analysis |
| KDE comparison chart | 3 hours | Better visualization |

### 🟢 P3 - Low Priority (Backlog)

| Feature | Effort | Impact |
|---------|--------|--------|
| Parquet export | 2 hours | Alternative format |
| Markdown report generation | 3 hours | Documentation |
| Chat history export | 2 hours | Nice to have |
| Correlation scatter chart | 3 hours | Additional visualization |

---

## Appendix A: File-by-File Changes Required

### Backend Files

1. **`src/api/routers/samples.py`**
   - Fix `size-bins` endpoint to use numeric ID
   - Ensure all statistics fields are populated

2. **`src/api/routers/upload.py`**
   - Verify FSC/SSC median/mean calculation
   - Return database `id` in upload response

3. **NEW: `src/api/routers/analysis.py`**
   - Add statistical tests endpoint
   - Add NTA correction endpoint

### Frontend Files

1. **`components/flow-cytometry/analysis-settings.tsx`**
   - Add Mie scattering parameters
   - Add anomaly detection settings

2. **NEW: `components/flow-cytometry/custom-size-ranges.tsx`**
   - Size range list with CRUD
   - Preset buttons

3. **`components/flow-cytometry/analysis-results.tsx`**
   - Fix statistics field mapping
   - Add size range distribution display

4. **`components/cross-compare/statistical-tests.tsx`**
   - NEW: KS and MW test display

5. **`components/nta/temperature-correction-view.tsx`**
   - NEW: Side-by-side comparison
   - Statistics tables

---

## Appendix B: Quick Fixes Checklist

- [ ] Change `getScatterData(sampleId)` to use numeric ID from `fcsAnalysis.results.id`
- [ ] Change `getSizeBins(sampleId)` to use numeric ID
- [ ] Add null checks for statistics fields with fallback to "N/A"
- [ ] Verify backend populates `fsc_median`, `ssc_median`, `fsc_mean`, `ssc_mean`
- [ ] Add loading spinners for all async data fetches
- [ ] Add error boundaries around chart components

---

*Report generated by analyzing Streamlit app.py (5,316 lines) and React components*
