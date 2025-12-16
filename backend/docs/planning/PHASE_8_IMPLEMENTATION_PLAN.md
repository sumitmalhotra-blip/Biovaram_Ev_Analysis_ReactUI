# Phase 8: Critical Calculation Fixes - Implementation Plan
## December 5-6, 2025

**Meeting Reference**: December 5, 2025 Technical Review with Parvesh and Sumit  
**Priority**: 🔴 CRITICAL  
**Estimated Effort**: 2 working days  
**Target Completion**: December 6, 2025 EOD

---

## Executive Summary

The December 5 meeting with Parvesh identified critical production bugs affecting data accuracy in the CRMIT platform. These bugs cause artificial histogram spikes, skewed statistical calculations, and suboptimal SSC channel selection. This document provides a detailed implementation plan to fix these issues.

### Critical Issues Identified

1. **Size Range Clamping Bug** - Values outside 40-180nm are clamped to boundaries, creating artificial histogram spikes and skewing median calculations
2. **VSSC Channel Selection** - Need explicit row-wise max logic instead of column-level median comparison
3. **Range Sync Issue** - Custom size range controls don't update diameter search parameters
4. **Light Mode Missing** - UI only supports dark theme

---

## Implementation Priorities

| Priority | Task | Impact | Effort | Status |
|----------|------|--------|--------|--------|
| 🔴 CRITICAL | Size Range Calculation Fix | HIGH - Affects all size statistics | 0.5 days | ❌ TODO |
| 🔴 CRITICAL | VSSC_max Column Logic | MEDIUM - Improves channel selection | 0.5 days | ❌ TODO |
| 🟡 MEDIUM | Size Range Filter Sync | LOW - UX improvement | 0.5 days | ❌ TODO |
| 🟢 LOW | Light Mode Theme | LOW - User preference | 0.5 days | ❌ TODO |

---

## Task 1: Size Range Calculation Fix (CRITICAL)

### Problem Statement

**Current Behavior** (INCORRECT):
```python
# In app.py, diameter calculation section
# Values <40nm get clamped to 40nm
# Values >180nm get clamped to 180nm
diameters = np.clip(calculated_diameters, 40, 180)

# This causes:
# 1. Histogram spike at 40nm (all small particles)
# 2. Histogram spike at 180nm (all large particles)
# 3. Median calculation includes clamped values (skewed)
```

**Impact on Production**:
- Size distribution histograms show artificial peaks
- Median size calculations are inaccurate
- D10, D50, D90 percentiles are skewed
- Scientific results not publishable

### Solution Design

**New Approach** (CORRECT):
```python
# Configuration
SEARCH_MIN = 30  # nm - search range start
SEARCH_MAX = 220  # nm - search range end
DISPLAY_MIN = 40  # nm - visualization range start
DISPLAY_MAX = 200  # nm - visualization range end

# Step 1: Calculate diameters with extended range
diameters_raw = calculate_diameter_mie_theory(
    ssc_data=ssc_values,
    wavelength=488,  # Blue laser
    refractive_index=1.39,  # Exosomes
    search_range=(SEARCH_MIN, SEARCH_MAX)
)

# Step 2: FILTER (don't clamp) - exclude invalid particles
mask_valid = (diameters_raw > SEARCH_MIN) & (diameters_raw < SEARCH_MAX)
diameters_filtered = diameters_raw[mask_valid]

# Step 3: Calculate statistics ONLY on filtered data
median_size = np.median(diameters_filtered)  # Excludes outliers
mean_size = np.mean(diameters_filtered)
std_size = np.std(diameters_filtered)
d10 = np.percentile(diameters_filtered, 10)
d50 = np.percentile(diameters_filtered, 50)
d90 = np.percentile(diameters_filtered, 90)

# Step 4: Create display subset (for visualization)
display_mask = (diameters_filtered >= DISPLAY_MIN) & (diameters_filtered <= DISPLAY_MAX)
diameters_display = diameters_filtered[display_mask]

# Step 5: Calculate display statistics
count_small = np.sum(diameters_filtered < DISPLAY_MIN)  # <40nm
count_medium = np.sum(display_mask)  # 40-200nm
count_large = np.sum(diameters_filtered > DISPLAY_MAX)  # >200nm
```

**Benefits**:
- ✅ No histogram artifacts
- ✅ Accurate median calculations
- ✅ Correct percentile values
- ✅ Transparent filtering logic

### Implementation Steps

#### Step 1.1: Locate Diameter Calculation Logic (15 min)

**Files to Search**:
```bash
# Search for diameter calculation
grep -n "diameter" apps/biovaram_streamlit/app.py
grep -n "np.clip" apps/biovaram_streamlit/app.py
grep -n "calculate_diameter" apps/biovaram_streamlit/app.py
```

**Expected Location**: Lines ~2900-3100

#### Step 1.2: Update Diameter Calculation (30 min)

**File**: `apps/biovaram_streamlit/app.py`

**Find**:
```python
# Current clamping logic (INCORRECT)
diameters = np.clip(calculated_diameters, 40, 180)
```

**Replace With**:
```python
# Configuration (add to top of file)
DIAMETER_SEARCH_MIN = 30  # nm
DIAMETER_SEARCH_MAX = 220  # nm
DIAMETER_DISPLAY_MIN = 40  # nm
DIAMETER_DISPLAY_MAX = 200  # nm

# Extended range calculation
diameters_raw = calculate_diameter_from_ssc(
    ssc_values=ssc_data,
    wavelength=488,
    refractive_index=1.39,
    search_min=DIAMETER_SEARCH_MIN,
    search_max=DIAMETER_SEARCH_MAX
)

# Filter valid particles (don't clamp)
valid_mask = (diameters_raw > DIAMETER_SEARCH_MIN) & (diameters_raw < DIAMETER_SEARCH_MAX)
diameters_filtered = diameters_raw[valid_mask]

# Display subset for visualization
display_mask = (diameters_filtered >= DIAMETER_DISPLAY_MIN) & (diameters_filtered <= DIAMETER_DISPLAY_MAX)
diameters_display = diameters_filtered[display_mask]
```

#### Step 1.3: Update Statistics Calculation (30 min)

**File**: `apps/biovaram_streamlit/app.py`

**Find**:
```python
# Current statistics (uses clamped data)
median_size = np.median(diameters)  # WRONG
d50 = np.percentile(diameters, 50)  # WRONG
```

**Replace With**:
```python
# Calculate statistics on FILTERED data only
statistics = {
    'median_nm': np.median(diameters_filtered),  # Correct
    'mean_nm': np.mean(diameters_filtered),
    'std_nm': np.std(diameters_filtered),
    'd10_nm': np.percentile(diameters_filtered, 10),
    'd50_nm': np.percentile(diameters_filtered, 50),
    'd90_nm': np.percentile(diameters_filtered, 90),
    'count_total': len(diameters_filtered),
    'count_display': len(diameters_display),
    'count_below_range': np.sum(diameters_filtered < DIAMETER_DISPLAY_MIN),
    'count_above_range': np.sum(diameters_filtered > DIAMETER_DISPLAY_MAX)
}

# Display statistics in metrics
col1.metric("Median Size", f"{statistics['median_nm']:.1f} nm")
col2.metric("D10", f"{statistics['d10_nm']:.1f} nm")
col3.metric("D50", f"{statistics['d50_nm']:.1f} nm")
col4.metric("D90", f"{statistics['d90_nm']:.1f} nm")
```

#### Step 1.4: Update Histogram Generation (30 min)

**File**: `apps/biovaram_streamlit/app.py`

**Find**:
```python
# Current histogram (uses all data including clamped)
fig = px.histogram(diameters, nbins=50)
```

**Replace With**:
```python
# Histogram of DISPLAY data only (no artificial spikes)
fig = px.histogram(
    x=diameters_display,
    nbins=50,
    title=f"Size Distribution ({DIAMETER_DISPLAY_MIN}-{DIAMETER_DISPLAY_MAX} nm)",
    labels={'x': 'Diameter (nm)', 'y': 'Count'}
)

# Add annotation for excluded particles
if statistics['count_below_range'] > 0 or statistics['count_above_range'] > 0:
    fig.add_annotation(
        text=f"Excluded: {statistics['count_below_range']} below range, {statistics['count_above_range']} above range",
        xref="paper", yref="paper",
        x=0.5, y=1.05,
        showarrow=False,
        font=dict(size=10)
    )
```

#### Step 1.5: Update Three Size Categories (15 min)

**File**: `apps/biovaram_streamlit/app.py`

**Find**:
```python
# Current categories (uses clamped data)
small = np.sum(diameters < 50)
medium = np.sum((diameters >= 50) & (diameters <= 200))
large = np.sum(diameters > 200)
```

**Replace With**:
```python
# Categories using FILTERED data
small = np.sum(diameters_filtered < 50)
medium = np.sum((diameters_filtered >= 50) & (diameters_filtered <= 200))
large = np.sum(diameters_filtered > 200)

# Display percentages
total = len(diameters_filtered)
st.write(f"**Small (<50nm):** {small} ({small/total*100:.1f}%)")
st.write(f"**Medium (50-200nm):** {medium} ({medium/total*100:.1f}%)")
st.write(f"**Large (>200nm):** {large} ({large/total*100:.1f}%)")
```

### Testing Protocol

#### Test Case 1: Sample with Small Particles (<40nm)

**Objective**: Verify small particles don't create 40nm spike

**Steps**:
1. Load FCS file known to have particles <40nm (e.g., buffer noise)
2. Check histogram visualization
3. Verify no artificial spike at 40nm
4. Confirm median calculation excludes these particles

**Expected Results**:
- Histogram smooth at lower end
- Median reflects true distribution (not pulled down by clamped values)
- Statistics exclude particles <30nm

#### Test Case 2: Sample with Large Particles (>180nm)

**Objective**: Verify large particles don't create 180nm spike

**Steps**:
1. Load FCS file with large aggregates (>180nm)
2. Check histogram visualization
3. Verify no artificial spike at 180nm
4. Confirm median calculation excludes these particles

**Expected Results**:
- Histogram smooth at upper end
- Median reflects true distribution (not pulled up by clamped values)
- Statistics exclude particles >220nm

#### Test Case 3: Normal EV Sample (40-180nm)

**Objective**: Verify existing samples still process correctly

**Steps**:
1. Load typical exosome sample (50-150nm range)
2. Compare old vs new median values
3. Verify D50 shifts appropriately
4. Check histogram shape

**Expected Results**:
- Median should be similar (±5nm)
- Histogram should be smoother (no boundary artifacts)
- Statistics more accurate

### Success Criteria

- ✅ No histogram spikes at 40nm or 180nm boundaries
- ✅ Median calculation uses only filtered data (30-220nm range)
- ✅ All statistics (D10, D50, D90) calculated on filtered data
- ✅ Display range (40-200nm) subset of calculation range
- ✅ Existing test files still process correctly
- ✅ No type errors or exceptions

---

## Task 2: VSSC_max Column Logic (CRITICAL)

### Problem Statement

**Current Behavior**:
```python
# Column-level median comparison
vssc1_median = df['VSSC-1-H'].median()
vssc2_median = df['VSSC-2-H'].median()
selected_channel = 'VSSC-1-H' if vssc1_median > vssc2_median else 'VSSC-2-H'
```

**Issues**:
- Not explicit (hidden logic)
- Column-level decision, not row-level optimization
- Difficult to debug or explain

### Solution Design

**New Approach**:
```python
# Create explicit VSSC_max column
df['VSSC_max'] = df[['VSSC-1-H', 'VSSC-2-H']].max(axis=1)

# Use VSSC_max for all calculations
ssc_data = df['VSSC_max'].values
```

**Benefits**:
- ✅ Explicit and transparent
- ✅ Row-wise optimization (per event)
- ✅ Easy to debug and export
- ✅ Appears in column dropdown

### Implementation Steps

#### Step 2.1: Locate SSC Column Selection (15 min)

**Files to Search**:
```bash
grep -n "VSSC-1-H" apps/biovaram_streamlit/app.py
grep -n "median" apps/biovaram_streamlit/app.py
grep -n "selected_channel" apps/biovaram_streamlit/app.py
```

**Expected Location**: Lines ~2400-2450

#### Step 2.2: Add VSSC_max Column Creation (30 min)

**File**: `apps/biovaram_streamlit/app.py`

**Find**:
```python
# After loading FCS data
df = parse_fcs_file(file_path)
```

**Add After**:
```python
# Create VSSC_max column (row-wise maximum)
if 'VSSC-1-H' in df.columns and 'VSSC-2-H' in df.columns:
    df['VSSC_max'] = df[['VSSC-1-H', 'VSSC-2-H']].max(axis=1)
    st.info("✅ Created VSSC_max column (max of VSSC-1-H and VSSC-2-H)")
else:
    st.warning("⚠️ VSSC columns not found, cannot create VSSC_max")
```

#### Step 2.3: Update Column Dropdown (15 min)

**File**: `apps/biovaram_streamlit/app.py`

**Find**:
```python
# Column selection dropdown
column_options = df.columns.tolist()
selected_column = st.selectbox("Select SSC Column", column_options)
```

**Replace With**:
```python
# Prioritize VSSC_max in dropdown
column_options = df.columns.tolist()

# Move VSSC_max to top if it exists
if 'VSSC_max' in column_options:
    column_options.remove('VSSC_max')
    column_options.insert(0, 'VSSC_max')  # Put at top
    default_column = 'VSSC_max'
else:
    default_column = column_options[0]

selected_column = st.selectbox(
    "Select SSC Column",
    column_options,
    index=column_options.index(default_column)
)
```

#### Step 2.4: Update Default Selection Logic (15 min)

**File**: `apps/biovaram_streamlit/app.py`

**Find**:
```python
# Old median-based selection
vssc1_median = df['VSSC-1-H'].median()
vssc2_median = df['VSSC-2-H'].median()
selected_channel = 'VSSC-1-H' if vssc1_median > vssc2_median else 'VSSC-2-H'
```

**Replace With**:
```python
# Default to VSSC_max if available
if 'VSSC_max' in df.columns:
    selected_channel = 'VSSC_max'
    st.success("Using VSSC_max (optimal per-event selection)")
else:
    # Fallback to median-based selection
    vssc1_median = df['VSSC-1-H'].median()
    vssc2_median = df['VSSC-2-H'].median()
    selected_channel = 'VSSC-1-H' if vssc1_median > vssc2_median else 'VSSC-2-H'
    st.info(f"Using {selected_channel} (median-based selection)")
```

### Testing Protocol

#### Test Case 1: VSSC_max Creation

**Steps**:
1. Load FCS file with VSSC-1-H and VSSC-2-H columns
2. Check DataFrame for new VSSC_max column
3. Verify values: `assert (df['VSSC_max'] == df[['VSSC-1-H', 'VSSC-2-H']].max(axis=1)).all()`

**Expected Results**:
- VSSC_max column exists
- Values equal row-wise maximum

#### Test Case 2: Column Dropdown Display

**Steps**:
1. Open Flow Cytometry tab
2. Check SSC column dropdown
3. Verify VSSC_max appears at top

**Expected Results**:
- VSSC_max is first option
- VSSC-1-H and VSSC-2-H also available

#### Test Case 3: Size Calculation Accuracy

**Steps**:
1. Select VSSC_max column
2. Calculate particle sizes
3. Compare to manual calculation

**Expected Results**:
- Sizes reasonable (40-180nm range)
- Results similar to or better than single-channel selection

### Success Criteria

- ✅ VSSC_max column created successfully
- ✅ VSSC_max appears in dropdown (first position)
- ✅ Size calculations use VSSC_max by default
- ✅ Manual column selection still works
- ✅ No errors when VSSC columns missing

---

## Task 3: Size Range Filter Sync (MEDIUM PRIORITY)

### Problem Statement

**Current Behavior**:
- User changes size range in sidebar (40-150nm)
- Diameter search range stays at 40-180nm
- Not synchronized

### Solution Design

**New Approach**:
```python
# Sidebar controls
min_size = st.number_input("Min Size (nm)", value=40, min_value=30, max_value=100)
max_size = st.number_input("Max Size (nm)", value=200, min_value=100, max_value=220)

# Auto-update search range (wider than display)
DIAMETER_SEARCH_MIN = max(30, min_size - 10)
DIAMETER_SEARCH_MAX = min(220, max_size + 20)

st.info(f"Search range: {DIAMETER_SEARCH_MIN}-{DIAMETER_SEARCH_MAX} nm (includes buffer)")
```

### Implementation Steps

#### Step 3.1: Add Dynamic Range Inputs (30 min)

**File**: `apps/biovaram_streamlit/app.py`

**Find**:
```python
# Sidebar size range controls (if exists)
st.sidebar.header("Size Range")
```

**Replace/Add**:
```python
st.sidebar.header("🎯 Size Range Configuration")

# Display range controls
col1, col2 = st.sidebar.columns(2)
with col1:
    min_display = st.number_input(
        "Min Display (nm)",
        value=40,
        min_value=30,
        max_value=100,
        step=5
    )
with col2:
    max_display = st.number_input(
        "Max Display (nm)",
        value=200,
        min_value=100,
        max_value=220,
        step=10
    )

# Calculate search range (wider than display)
search_min = max(30, min_display - 10)
search_max = min(220, max_display + 20)

st.sidebar.info(f"""
**Display Range:** {min_display}-{max_display} nm  
**Search Range:** {search_min}-{search_max} nm  
*(Search includes buffer for accurate statistics)*
""")

# Preset buttons
st.sidebar.subheader("Quick Presets")
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("Standard EV"):
        min_display = 40
        max_display = 200
        st.rerun()
with col2:
    if st.button("Exosome Focus"):
        min_display = 40
        max_display = 150
        st.rerun()
```

### Success Criteria

- ✅ Min/max inputs update search range
- ✅ Search range always wider than display range
- ✅ Preset buttons work correctly
- ✅ Edge cases handled (min > max)

---

## Task 4: Light Mode Theme (LOW PRIORITY)

### Problem Statement

**Current**: Only dark theme available  
**Requested**: Light theme option

### Solution Design

```python
# Theme toggle in header
theme = st.toggle("☀️ Light Mode", value=False, key="theme_mode")

if theme:
    # Light theme CSS
    st.markdown("""
    <style>
    .stApp {
        background-color: #ffffff;
        color: #1a1a1a;
    }
    .stMetric {
        background-color: #f5f5f5;
        border: 1px solid #e0e0e0;
    }
    </style>
    """, unsafe_allow_html=True)
```

### Implementation Steps

#### Step 4.1: Add Theme Toggle (30 min)

**File**: `apps/biovaram_streamlit/app.py`

**Find**:
```python
# Header section
st.title("🔬 CRMIT - EV Analysis Platform")
```

**Add After**:
```python
# Theme toggle in sidebar
with st.sidebar:
    st.divider()
    theme_mode = st.toggle("☀️ Light Mode", value=False, key="theme_mode")
    st.divider()

# Apply theme CSS
if theme_mode:
    st.markdown("""
    <style>
    .stApp {
        background-color: #ffffff;
        color: #1a1a1a;
    }
    .stMetric {
        background-color: #f5f5f5;
        border: 1px solid #e0e0e0;
    }
    div[data-testid="stMetricValue"] {
        color: #1a1a1a;
    }
    </style>
    """, unsafe_allow_html=True)
```

### Success Criteria

- ✅ Toggle switches themes
- ✅ All text readable in both modes
- ✅ Theme preference persists during session

---

## Implementation Timeline

### Day 1 (December 5 - Afternoon)

**Priority: CRITICAL Tasks Only**

| Time | Task | Deliverable |
|------|------|-------------|
| 2:00-2:30 PM | Read and analyze code (Tasks 1 & 2) | Code location map |
| 2:30-4:00 PM | Implement Task 1.1-1.3 (Size range fix) | Updated diameter calculation |
| 4:00-5:00 PM | Implement Task 1.4-1.5 (Histogram & stats) | Complete size range fix |
| 5:00-6:00 PM | Test Task 1 (All test cases) | Verified fix |

### Day 2 (December 6 - Morning)

**Priority: HIGH + MEDIUM Tasks**

| Time | Task | Deliverable |
|------|------|-------------|
| 9:00-10:00 AM | Implement Task 2 (VSSC_max column) | VSSC_max logic |
| 10:00-11:00 AM | Test Task 2 (Column creation & dropdown) | Verified VSSC_max |
| 11:00-12:00 PM | Implement Task 3 (Range sync) | Synced controls |
| 12:00-1:00 PM | Test Tasks 2 & 3 together | Integration test |

### Day 2 (December 6 - Afternoon)

**Priority: LOW Tasks (Optional)**

| Time | Task | Deliverable |
|------|------|-------------|
| 2:00-3:00 PM | Implement Task 4 (Light mode) | Theme toggle |
| 3:00-4:00 PM | Test light mode | Verified theme |
| 4:00-5:00 PM | Final integration testing | All tasks verified |
| 5:00-6:00 PM | Documentation & commit | GitHub push |

---

## Rollback Plan

### If Size Range Fix Fails

**Symptoms**: Errors in diameter calculation, no histogram display

**Rollback**:
```bash
git revert <commit_hash>
git push origin main
```

**Alternative**: Keep old logic with warning banner:
```python
st.warning("⚠️ Size range fix temporarily disabled. Using legacy clamping.")
```

### If VSSC_max Breaks Column Selection

**Symptoms**: No columns in dropdown, size calculation errors

**Rollback**:
```python
# Disable VSSC_max creation
USE_VSSC_MAX = False  # Feature flag

if USE_VSSC_MAX and 'VSSC-1-H' in df.columns and 'VSSC-2-H' in df.columns:
    df['VSSC_max'] = df[['VSSC-1-H', 'VSSC-2-H']].max(axis=1)
```

---

## Post-Implementation Checklist

### Code Quality
- [ ] No type errors (`mypy apps/biovaram_streamlit/app.py`)
- [ ] No lint warnings (`flake8 apps/biovaram_streamlit/app.py`)
- [ ] All existing tests pass (`pytest tests/`)
- [ ] New tests added for fixes

### Documentation
- [ ] TASK_TRACKER.md updated with completion status
- [ ] CRMIT-Development-Plan.md marked Phase 8 complete
- [ ] Commit messages descriptive and clear
- [ ] Code comments explain "why" not just "what"

### Testing
- [ ] Test Case 1.1 (Small particles) - PASS
- [ ] Test Case 1.2 (Large particles) - PASS
- [ ] Test Case 1.3 (Normal EV sample) - PASS
- [ ] Test Case 2.1 (VSSC_max creation) - PASS
- [ ] Test Case 2.2 (Column dropdown) - PASS
- [ ] Test Case 2.3 (Size calculation) - PASS
- [ ] Integration test (All tasks together) - PASS

### User Communication
- [ ] Demo to Parvesh (show histogram fixes)
- [ ] Document breaking changes (if any)
- [ ] Update user guide (if needed)

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Size calculation breaks existing samples | MEDIUM | HIGH | Extensive testing, rollback plan |
| VSSC_max column missing for some files | LOW | MEDIUM | Fallback to median selection |
| Performance impact (row-wise max) | LOW | LOW | Numpy vectorized operations |
| Light mode unreadable | LOW | LOW | Test with sample users |

---

## Communication Plan

### Daily Updates (Slack/Email)

**Format**:
```
📅 Date: December 5, 2025
🎯 Focus: Size Range Calculation Fix (Task 1)

✅ Completed:
- Located diameter calculation code (lines 2950-3020)
- Implemented extended search range (30-220nm)
- Updated statistics to use filtered data

🔄 In Progress:
- Testing histogram visualization
- Validating median calculation

❌ Blockers:
- None

📊 Progress: 60% complete
⏰ On track for December 6 EOD
```

### Meeting with Parvesh (December 6, 4 PM)

**Agenda**:
1. Demo size range fix (show before/after histograms)
2. Explain VSSC_max column logic
3. Show light mode toggle
4. Discuss React migration timeline

**Prepare**:
- Screenshots of fixed histograms
- Example median calculation (before vs after)
- Performance metrics (if available)

---

## Success Metrics

### Technical Metrics
- ✅ 0 histogram spikes at boundary values
- ✅ Median accuracy within ±2nm of manual calculation
- ✅ VSSC_max column present in 100% of samples with dual channels
- ✅ All 13 integration tests passing

### User Metrics
- ✅ Parvesh approves histogram fixes
- ✅ No user-reported calculation errors
- ✅ Light mode adopted by >20% users (optional)

### Code Quality Metrics
- ✅ No new type errors
- ✅ Code coverage >80% for new logic
- ✅ Performance <500ms for size calculations

---

## Appendix A: Code Locations

### Key Files
- **Main App**: `apps/biovaram_streamlit/app.py` (5242 lines)
- **Parsers**: `src/parsers/fcs_parser.py` (FCS file reading)
- **Mie Theory**: `src/physics/mie_scatter.py` (diameter calculations)
- **Tests**: `tests/test_parser.py` (integration tests)

### Key Functions
- `calculate_diameter_from_ssc()` - Lines ~2950-3020
- `display_statistics()` - Lines ~4150-4250
- `create_histogram()` - Lines ~3500-3600
- `select_ssc_column()` - Lines ~2400-2450

---

## Appendix B: Test Data Files

### FCS Files for Testing
- **Small particles**: `nanoFACS/10000 exo and cd81/HPLC Water.fcs`
- **Normal EVs**: `nanoFACS/10000 exo and cd81/Exo Control.fcs`
- **Large aggregates**: `nanoFACS/CD9 and exosome lots/L5+F10+CD9.fcs`

### Expected Results
- **Water**: Median <30nm (should be filtered out)
- **Exo Control**: Median 80-120nm
- **Aggregates**: Some particles >200nm (should be filtered)

---

## Conclusion

This implementation plan provides a structured approach to fixing critical calculation bugs identified in the December 5, 2025 meeting. By following this plan, we ensure:

1. **Data Accuracy**: Size calculations reflect true particle distributions
2. **Code Transparency**: VSSC_max logic is explicit and debuggable
3. **User Experience**: Synced controls and theme options
4. **Quality Assurance**: Comprehensive testing before deployment

**Target Completion**: December 6, 2025 EOD  
**Next Review**: December 6, 2025 (4 PM with Parvesh)
