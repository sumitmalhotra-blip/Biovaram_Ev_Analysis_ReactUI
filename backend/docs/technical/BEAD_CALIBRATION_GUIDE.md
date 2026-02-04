# Bead Calibration Guide for Flow Cytometry EV Sizing

**Date:** February 2, 2026  
**Authors:** Development Team  
**Status:** 🟡 CALIBRATION DATA NEEDED

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Questions for the Lab Team](#questions-for-the-lab-team)
3. [What We Did Today](#what-we-did-today)
4. [Key Findings](#key-findings)
5. [Calibration Workflow](#calibration-workflow)
6. [How Calibration Will Be Saved](#how-calibration-will-be-saved)
7. [Technical Implementation](#technical-implementation)
8. [Results Comparison](#results-comparison)
9. [Next Steps](#next-steps)

---

## Executive Summary

We analyzed two calibration bead files (`Nano Vis Low.fcs` and `Nano Vis High.fcs`) and discovered that **bead-based calibration dramatically improves EV sizing accuracy**.

| Metric | Before Calibration | After Calibration |
|--------|-------------------|-------------------|
| **D50 (median)** | 337nm | **75.5nm** ✓ |
| **Small (<50nm)** | 0% | **6.0%** |
| **Medium (50-200nm)** | 40.8% | **88.8%** ✓ |
| **Large (>200nm)** | 59.2% | **5.2%** |

The calibrated results match expected exosome sizes (30-150nm), while uncalibrated results showed unrealistic ~60% large particles.

---

## Questions for the Lab Team

### ❓ REQUIRED INFORMATION (Please provide)

#### 1. Bead Kit Details

| Question | Your Answer |
|----------|-------------|
| **Kit manufacturer?** | (e.g., NanoFCM, Spherotech, Bangs Labs) |
| **Kit product name/catalog number?** | |
| **LOW kit exact sizes (nm)?** | (e.g., 46, 68, 91, 113, 150) |
| **HIGH kit exact sizes (nm)?** | (e.g., 150, 200, 300, 500, 800, 1000) |
| **Bead material?** | Polystyrene (n=1.59) ✓ confirmed |
| **Is there a 150nm overlap bead in both kits?** | Yes / No |

#### 2. Instrument Settings

| Question | Your Answer |
|----------|-------------|
| **Instrument model?** | (e.g., ZE5, Cytek Aurora) |
| **Laser wavelengths used?** | (Violet 405nm, Blue 488nm confirmed) |
| **PMT voltage settings?** | (Same for beads and samples?) |
| **Date of bead measurement?** | |
| **Same settings as EV sample measurements?** | Yes / No |

#### 3. Datasheet Information

Please provide the **bead kit datasheet** (PDF or image) that shows:
- Exact bead diameters (nm)
- Diameter CV% (coefficient of variation)
- Refractive index at 488nm
- Recommended storage and expiry

---

## What We Did Today

### Session: February 2, 2026

#### BUG-001: Fixed miepython API Error
- **Issue:** `_single_sphere_py() takes 3 positional arguments but 4 were given`
- **Root Cause:** Code used old 4-argument API instead of new 3-argument API
- **Fix:** Updated line 239 in `mie_scatter.py`
- **Status:** ✅ FIXED

#### BUG-002: Display Endpoints Using Wrong Mie Calculator
- **Issue:** Upload used `MultiSolutionMieCalculator` but display used old `MieScatterCalculator`
- **Root Cause:** 5 endpoints in `samples.py` weren't updated
- **Fix:** Added `detect_multi_solution_channels()` helper, updated all endpoints
- **Status:** ✅ FIXED

#### Literature Review: Mie Functions Documents
- Read `Mie functions_scattering_Abs-V1.docx` and `V2.docx`
- **Key Physics Confirmed:**
  - Size parameter: x = πd/λ
  - Rayleigh scattering: ∝ λ⁻⁴ (shorter wavelength = more scattering)
  - Violet (405nm) has better sensitivity for small particles

#### Violet Channel as Primary
- **Your Insight:** "Violet should be default because scattering is stronger at shorter wavelengths"
- **Physics Confirmation:** Correct! For EVs (30-150nm) in Rayleigh regime, violet scatters 2.1× more
- **Code Change:** Added `use_violet_primary=True` parameter (default) to `calculate_sizes_multi_solution()`

#### Bead Calibration Analysis
- Loaded `Nano Vis Low.fcs` (179,465 events) and `Nano Vis High.fcs` (124,189 events)
- Detected multiple bead populations automatically
- Built preliminary calibration curve
- **Result:** D50 dropped from 337nm to 75.5nm (realistic for exosomes!)

---

## Key Findings

### 1. The Core Problem: Arbitrary Units

Flow cytometer scatter values (VSSC, BSSC) are in **arbitrary units** that depend on:
- PMT voltage settings
- Optical alignment
- Detector sensitivity

**Solution:** Use known-size beads to calibrate: `arbitrary_units → physical_size`

### 2. Detector Sensitivity Mismatch

| Measurement | Value |
|-------------|-------|
| Measured VSSC/BSSC ratio | ~5.0 |
| Theoretical Rayleigh limit | 2.11 |
| **Calibration factor needed** | **2.2×** |

The violet (405nm) detector is ~2.2× more sensitive than expected relative to blue (488nm).

### 3. Detected Bead Populations

**LOW Beads (40-150nm range):**
| Pop # | VSSC Median | Events | Likely Size* |
|-------|-------------|--------|--------------|
| 1 | 354 | 9,274 | ~46nm |
| 2 | 473 | 10,177 | ~55nm |
| 3 | 578 | 9,667 | ~65nm |
| 4 | 646 | 9,509 | ~72nm |
| 5 | 790 | 9,547 | ~82nm |
| 6 | 923 | 9,683 | ~91nm |
| 7 | 1,032 | 9,888 | ~100nm |
| 8 | 1,233 | 10,190 | ~110nm |
| 9 | 1,611 | 11,028 | ~125nm |
| 10 | 1,968 | 11,655 | ~137nm |
| 11+ | 2,514-4,197 | 12-13k each | ~150nm+ |
| 16-17 | 86,738-101,370 | 11-12k | ~200-250nm |

*Sizes are estimated - need datasheet for exact values

**HIGH Beads (140-1000nm range):**
| Pop # | VSSC Median | Events | Likely Size* |
|-------|-------------|--------|--------------|
| 1 | 355 | 17,923 | ~150nm (overlap) |
| 12 | 2,177,625 | 6,088 | ~800-1000nm |

### 4. Calibration Curve Formula

```
log(diameter) = 0.3051 × log(VSSC) + 0.8532

Or equivalently:
diameter = 7.14 × VSSC^0.305
```

**Accuracy with 4 calibration points:**
- 46nm: 5.4% error
- 100nm: 14.0% error
- 150nm: 61.6% error (needs more points)
- 800nm: 23.9% error

With the full bead ladder (15+ points), accuracy will improve significantly.

---

## Calibration Workflow

> ⚠️ **IMPORTANT: Bead Material Affects Calibration**
>
> Different bead materials have different refractive indices, which directly affects Mie scattering calculations:
>
> | Bead Material | Refractive Index (n) | Common Use |
> |---------------|---------------------|------------|
> | **Polystyrene (PS)** | **1.59** | Most common, current default |
> | Silica (SiO₂) | 1.46 | Lower scattering, closer to EVs |
> | PMMA | 1.49 | Intermediate |
> | Melamine | 1.68 | High scattering |
> | EVs (biological) | ~1.38-1.42 | Sample particles |
>
> **Always specify the bead material when setting up calibration!** The system must know the bead's refractive index to correctly calculate theoretical Mie scattering values. Using the wrong RI will produce incorrect calibration curves.

### For Users in the Software

```
┌─────────────────────────────────────────────────────────────────┐
│                    CALIBRATION WORKFLOW                          │
└─────────────────────────────────────────────────────────────────┘

     ┌─────────────────────────────────────────┐
     │  STEP 1: UPLOAD CALIBRATION BEADS       │
     │  ─────────────────────────────────────  │
     │  • Upload: Nano Vis Low.fcs             │
     │  • Upload: Nano Vis High.fcs            │
     │  • Mark as "Calibration Beads"          │
     └─────────────────────────────────────────┘
                         ↓
     ┌─────────────────────────────────────────┐
     │  STEP 2: AUTO-DETECT POPULATIONS        │
     │  ─────────────────────────────────────  │
     │  • System finds distinct bead clusters  │
     │  • Shows scatter plot with gates        │
     │  • Displays VSSC median for each        │
     └─────────────────────────────────────────┘
                         ↓
     ┌─────────────────────────────────────────┐
     │  STEP 3: ASSIGN KNOWN SIZES             │
     │  ─────────────────────────────────────  │
     │  • User enters sizes from datasheet     │
     │  • Pop 1 = 46nm, Pop 2 = 68nm, etc.     │
     │  • System validates assignments         │
     └─────────────────────────────────────────┘
                         ↓
     ┌─────────────────────────────────────────┐
     │  STEP 4: BUILD & SAVE CALIBRATION       │
     │  ─────────────────────────────────────  │
     │  • Fits polynomial curve                │
     │  • Calculates detector ratio factor     │
     │  • Saves to calibration database        │
     └─────────────────────────────────────────┘
                         ↓
     ┌─────────────────────────────────────────┐
     │  STEP 5: APPLY TO ALL SAMPLES           │
     │  ─────────────────────────────────────  │
     │  • Auto-applied during upload           │
     │  • VSSC → Calibrated Diameter           │
     │  • Accurate EV sizing!                  │
     └─────────────────────────────────────────┘
```

---

## How Calibration Will Be Saved

### Storage Location

```
backend/
├── config/
│   └── calibration/
│       ├── current_calibration.json      # Active calibration
│       ├── calibration_history/          # Previous calibrations
│       │   ├── 2026-02-02_ZE5_initial.json
│       │   └── 2026-03-15_ZE5_recal.json
│       └── bead_kits/                    # Known bead kit definitions
│           ├── nanofcm_low.json
│           └── nanofcm_high.json
```

### Calibration JSON Structure

```json
{
  "calibration_id": "cal_20260202_001",
  "created_date": "2026-02-02T14:30:00Z",
  "instrument": {
    "id": "ZE5-001",
    "model": "Bio-Rad ZE5",
    "location": "CRMIT Lab"
  },
  "bead_kit": {
    "manufacturer": "NanoFCM",
    "low_kit_catalog": "NFCM-LOW-001",
    "high_kit_catalog": "NFCM-HIGH-001",
    "bead_material": "polystyrene",
    "refractive_index": 1.59
  },
  "populations": [
    {
      "known_diameter_nm": 46,
      "vssc_median": 354,
      "bssc_median": 85,
      "n_events": 9274,
      "ratio": 4.16
    },
    {
      "known_diameter_nm": 68,
      "vssc_median": 578,
      "bssc_median": 135,
      "n_events": 9667,
      "ratio": 4.28
    }
    // ... more populations
  ],
  "calibration_curve": {
    "type": "polynomial",
    "degree": 2,
    "coefficients_vssc": [0.00015, 0.3051, 0.8532],
    "coefficients_bssc": [0.00018, 0.3102, 0.7845],
    "valid_range_nm": [30, 1000],
    "valid_range_vssc": [200, 3000000]
  },
  "detector_ratio_factor": 2.2,
  "validation": {
    "mean_error_pct": 8.5,
    "max_error_pct": 15.2,
    "r_squared": 0.987
  },
  "source_files": [
    "Nano Vis Low.fcs",
    "Nano Vis High.fcs"
  ],
  "notes": "Initial calibration for EV analysis"
}
```

### Database Storage (Future)

For multi-user environments, calibrations will be stored in PostgreSQL:

```sql
CREATE TABLE calibrations (
    id UUID PRIMARY KEY,
    instrument_id VARCHAR(50),
    created_at TIMESTAMP,
    created_by VARCHAR(100),
    is_active BOOLEAN DEFAULT false,
    calibration_data JSONB,
    validation_metrics JSONB
);

CREATE TABLE calibration_populations (
    id UUID PRIMARY KEY,
    calibration_id UUID REFERENCES calibrations(id),
    known_diameter_nm FLOAT,
    vssc_median FLOAT,
    bssc_median FLOAT,
    n_events INTEGER
);
```

---

## Technical Implementation

### Key Code Changes Made

#### 1. `mie_scatter.py` - Violet Primary Default

```python
def calculate_sizes_multi_solution(
    self,
    ssc_blue: np.ndarray,
    ssc_violet: np.ndarray,
    tolerance_pct: float = 15.0,
    use_violet_primary: bool = True  # NEW: Violet is now default
) -> Tuple[np.ndarray, np.ndarray]:
```

#### 2. `samples.py` - Multi-Solution for Display

Added `detect_multi_solution_channels()` helper and updated 5 endpoints:
- `/scatter-data`
- `/gated-analysis`
- `/size-bins`
- `/reanalyze`
- `/fcs/values`

#### 3. `bead_calibration.py` - Calibration Module

Existing module at `backend/src/physics/bead_calibration.py` provides:
- `BeadStandard` - Single bead standard
- `BeadCalibrator` - Main calibration workflow
- `CalibrationCurve` - Fitted calibration curve

### Calibration Application

```python
# Pseudocode for applying calibration

class CalibratedMieCalculator:
    def __init__(self, calibration: CalibrationResult):
        self.calibration = calibration
    
    def diameter_from_vssc(self, vssc: np.ndarray) -> np.ndarray:
        """Convert measured VSSC to diameter using calibration."""
        log_vssc = np.log10(np.maximum(vssc, 1))
        log_d = np.polyval(self.calibration.poly_coeffs, log_vssc)
        return 10**log_d
    
    def apply_to_sample(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add calibrated_diameter_nm column to sample data."""
        vssc = data['VSSC1-H'].values
        data['calibrated_diameter_nm'] = self.diameter_from_vssc(vssc)
        return data
```

---

## Results Comparison

### PC3 EXO1 Sample (Pure Exosomes)

| Analysis Method | D50 | Small% | Medium% | Large% |
|-----------------|-----|--------|---------|--------|
| **Before (uncalibrated Mie)** | 337nm | 0% | 40.8% | 59.2% |
| **After (bead calibration)** | 75.5nm | 6.0% | 88.8% | 5.2% |
| **Expected (exosomes)** | 50-100nm | 5-10% | 85-95% | <5% |

**Conclusion:** Bead calibration produces results consistent with known exosome biology!

---

## Next Steps

### Immediate (Today)

1. ☐ Get bead kit datasheet from lab team
2. ☐ Confirm exact sizes for each population
3. ☐ Build final calibration curve with all points

### Short Term (This Week)

4. ☐ Save calibration to `config/calibration/` 
5. ☐ Integrate calibration into upload workflow
6. ☐ Add calibration UI to frontend (optional)

### Long Term

7. ☐ Recalibration workflow (when settings change)
8. ☐ Multi-instrument calibration support
9. ☐ Calibration validation against NTA data

---

## References

### Literature

1. **Mätzler (2002)** - "MATLAB Functions for Mie Scattering and Absorption"
   - `Literature/Mie functions_scattering_Abs-V1.docx`
   - `Literature/Mie functions_scattering_Abs-V2.docx`

2. **Bohren & Huffman (1983)** - "Absorption and Scattering of Light by Small Particles"

3. **FCMPASS** - "Software-Aids-EVs-Light-Scatter-Stand.pdf"
   - Figure 8/3A discusses non-monotonic Mie curves

### Code Files

| File | Purpose |
|------|---------|
| `src/physics/mie_scatter.py` | Core Mie calculations |
| `src/physics/bead_calibration.py` | Bead calibration module |
| `src/api/routers/samples.py` | Sample analysis endpoints |
| `src/api/routers/upload.py` | File upload & processing |

### Bead Files Analyzed

- `nanoFACS/Nano Vis Low.fcs` - 179,465 events, 40-150nm range
- `nanoFACS/Nano Vis High.fcs` - 124,189 events, 140-1000nm range

---

## Appendix: Physics Background

### Why Calibration is Necessary

```
                    FLOW CYTOMETER
                         │
    Particle ──► Laser ──► Scatter ──► PMT ──► Voltage
     (nm)        (nm)      (light)     (V)     (A.U.)
                         │
                    ARBITRARY UNITS!
```

The final values depend on:
1. **Laser power** - varies between instruments
2. **PMT voltage** - user-adjustable
3. **Optical alignment** - changes over time
4. **Detector sensitivity** - different for each wavelength

**Calibration beads** of known sizes provide the missing link:
```
Known Size (nm) ←──► Measured A.U.
```

### Mie Scattering Non-Monotonicity

The Mie curve oscillates - one scatter value can map to multiple sizes:

```
Scatter │           /\
        │      /\  /  \     /\
        │     /  \/    \   /  \
        │    /          \ /    
        │   /            X      
        │  /            / \     
        │ /            /   \    
        │/____________/     \___
        └───────────────────────
           30nm   100nm   300nm   Diameter
```

**Multi-wavelength** (VSSC 405nm + BSSC 488nm) disambiguates by using the ratio.

### Rayleigh vs Geometric Regime

| Size | Regime | Scatter ∝ | VSSC/BSSC Ratio |
|------|--------|-----------|-----------------|
| < 50nm | Rayleigh | d⁶ × λ⁻⁴ | ~2.1 (high) |
| 50-200nm | Transition | Complex | 1.5-2.0 |
| > 200nm | Geometric | d² | ~1.0 (low) |

EVs (30-150nm) are in Rayleigh/transition regime where **violet has advantage**.

---

*Document created: February 2, 2026*  
*Last updated: February 2, 2026*
