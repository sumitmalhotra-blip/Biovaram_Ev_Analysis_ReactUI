# Particle Sizing Accuracy Diagnosis Report

**Date:** February 12, 2026  
**Authors:** CRMIT Engineering Team  
**Status:** Root Cause Identified — Pending Resolution  
**Severity:** Critical (sizing output 3× too low or 2× too high vs NTA ground truth)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [The Problem Statement](#2-the-problem-statement)
3. [NTA Ground Truth Reference Data](#3-nta-ground-truth-reference-data)
4. [How We Discovered the Issue](#4-how-we-discovered-the-issue)
5. [Root Cause Analysis — Bead Calibration](#5-root-cause-analysis--bead-calibration)
6. [Root Cause Analysis — Multi-Solution Mie](#6-root-cause-analysis--multi-solution-mie)
7. [Root Cause Analysis — Single-Solution Mie](#7-root-cause-analysis--single-solution-mie)
8. [Affected Components (Full Codebase Map)](#8-affected-components-full-codebase-map)
9. [What We Already Have Available](#9-what-we-already-have-available)
10. [What We Need From the Team](#10-what-we-need-from-the-team)
11. [Proposed Solutions (Ranked)](#11-proposed-solutions-ranked)
12. [Implementation Roadmap](#12-implementation-roadmap)
13. [Appendix: Mathematical Verification](#13-appendix-mathematical-verification)

---

## 1. Executive Summary

The platform has **three independent particle sizing methods**, and **all three produce incorrect results** when compared against NTA (Nanoparticle Tracking Analysis) ground truth data from the same PC3 EXO1 sample:

| Sizing Method | Median (nm) | Error vs NTA | Direction |
|---|---|---|---|
| **NTA Ground Truth (ZetaView)** | **127–172** | — | Reference |
| Bead Calibration (active, shown on frontend) | 42–47 | **3× too low** | Under-estimates |
| Multi-Solution Mie (`/fcs/values` endpoint) | ~321 | **2× too high** | Over-estimates |
| Single-Solution Mie (`/distribution-analysis`) | Variable | **Unreliable** | Scale-dependent |

**Impact:** Every particle size number shown on the platform is wrong. The median shown in the Statistics Cards, the donut chart in Particle Size Visualization, the D10/D50/D90 percentiles, and the size-bin categorizations (small/medium/large EVs) are all derived from fundamentally flawed sizing.

---

## 2. The Problem Statement

### What users see

When a user uploads an FCS file (e.g., `20260212_145801_PC3 EXO1.fcs`, 914,326 events from a CytoFLEX S), the platform reports:

- **Median particle size:** ~42–47 nm (from bead calibration)
- **Size category:** Almost all particles classified as "Small EVs" (<50 nm)
- **D10/D50/D90:** Compressed into a narrow 35–71 nm band

### What the sizes should actually be

The same PC3 100kDa sample measured via NTA (ZetaView, 488nm laser) across 5 independent measurements shows:

- **Median size (D50):** 127–172 nm
- **Expected dominant category:** "Medium EVs" (100–200 nm range)
- **Expected distribution:** Centered around ~150 nm with a log-normal spread

### The discrepancy

The bead calibration reports sizes **3× smaller** than reality. The multi-solution Mie reports sizes **2× larger** than reality. Neither method is even approximately correct.

---

## 3. NTA Ground Truth Reference Data

Five independent NTA measurements from `backend/NTA/PC3/` using a ZetaView instrument (S/N 24-1152, SOP: EV_488, 488nm laser, 25°C):

| File | Sample | D50 Median (nm) |
|---|---|---|
| `20251217_0005_PC3_100kDa_F5_size_488.txt` | PC3 100kDa Fraction 5 | 127.3 |
| `20251217_0016_PC3_100kDa_F1_2_size_488.txt` | PC3 100kDa Fraction 1-2 | 145.9 |
| `20251217_0017_PC3_100kDa_F3T6_size_488.txt` | PC3 100kDa Fraction 3-6 | 155.6 |
| `20251217_0018_PC3_100kDa_F7_8_size_488.txt` | PC3 100kDa Fraction 7-8 | 171.5 |
| `20251217_0019_PC3_100kDa_F9T15_size_488.txt` | PC3 100kDa Fraction 9-15 | 158.5 |

**NTA Average D50: ~151.7 nm**

These measurements are from the same PC3 100kDa exosome preparation. The FCS files were acquired on the same or closely related samples. NTA is an orthogonal technique with well-established accuracy for this size range (50–500 nm), making it a reliable ground truth reference.

**Additional NTA data available in the workspace** (not yet analyzed):
- `backend/NTA/EV_HEK_TFF_DATA_05Dec25/` — HEK293 TFF EV preparations
- `backend/NTA/EV_IPSC_P1_19_2_25_NTA/` — iPSC-derived EVs, Passage 1
- `backend/NTA/EV_IPSC_P2_27_2_25_NTA/` — iPSC-derived EVs, Passage 2
- `backend/NTA/EV_IPSC_P2.1_28_2_25_NTA/` — iPSC-derived EVs, Passage 2.1

---

## 4. How We Discovered the Issue

### Step 1: Visual inspection of the platform UI

The platform showed a median size of ~42 nm for PC3 EXO1 — a preparation of 100 kDa ultracentrifugation-enriched exosomes. This is physically implausible:
- 100 kDa cutoff enriches for vesicles >80 nm
- PC3-derived exosomes are typically 80–200 nm in literature
- 42 nm is in the exomere/protein aggregate range, not EV range

### Step 2: Cross-referencing NTA data

We found 5 ZetaView NTA measurements in `backend/NTA/PC3/` for the same sample preparation. All showed D50 in the 127–172 nm range — **3× larger** than what the platform reported.

### Step 3: Checking all three sizing backends

We traced the data flow through the API endpoints and discovered that the platform has three sizing paths, each producing different (and incorrect) results:

1. **`GET /scatter-data`** and **`POST /reanalyze`** use bead calibration → **42 nm median** (shown to user)
2. **`GET /fcs/values`** uses multi-solution Mie → **321 nm median** (used for per-event values)
3. **`GET /distribution-analysis`** uses single-solution Mie → **variable** (used for distribution fitting)

### Step 4: Mathematical verification of the bead calibration

We extracted the active calibration parameters from `config/calibration/active_calibration.json` and verified the math:

```
Power law: FSC = 1.547e-13 × d^9.61
Inverse:   d = (FSC / 1.547e-13)^(1/9.61) = (FSC / 1.547e-13)^0.1041
```

We then computed expected diameters for representative VSSC values:
- VSSC = 100 → d = 34.8 nm
- VSSC = 1,000 → d = 44.2 nm
- VSSC = 10,000 → d = 56.1 nm
- VSSC = 100,000 → d = 71.3 nm
- VSSC = 1,000,000 → d = 90.5 nm

**The entire dynamic range of VSSC (100 to 100,000) maps to just 35–71 nm.** This is the compression artifact.

### Step 5: Analyzing why the multi-solution Mie over-estimates

We compared theoretical SSC cross-sections with instrument SSC values:

| Diameter | Theory SSC (nm²) | Instrument VSSC (arb. units) | Scale Factor |
|---|---|---|---|
| 40 nm | 2.49 | 372 | ~149× |
| 80 nm | 95.97 | 2,156,170 | ~22,466× |
| 108 nm | 335.55 | 5,376,525 | ~16,023× |

The scale factor varies by **150×** (from 149× to 22,466×). The multi-solution Mie directly compares raw instrument units against theoretical nm² values — there is no normalization bridge.

---

## 5. Root Cause Analysis — Bead Calibration

### What the bead calibration does

**File:** `backend/src/physics/bead_calibration.py` (1,144 lines)  
**Active config:** `backend/config/calibration/active_calibration.json`

The `BeadCalibrationCurve` class:
1. Takes measured scatter values from known-size bead FCS files
2. Fits a power law `FSC = a × d^b` using `scipy.optimize.curve_fit`
3. Inverts to get `d = (FSC/a)^(1/b)` for unknown samples

### The three root causes

#### Root Cause 5.1: Only 3 of 7 bead sizes were matched

The nanoViS D03231 kit has **7 unique bead sizes**: 40, 80, 108, 142, 304, 600, 1020 nm. But the active calibration only used **3 beads** (40, 80, 108 nm):

```json
"bead_standards": {
  "40":  { "fsc_mean": 372.3,       "n_events": 15898 },
  "80":  { "fsc_mean": 2156169.6,   "n_events": 4708  },
  "108": { "fsc_mean": 5376524.8,   "n_events": 23215 }
}
```

**Why only 3?** The `detect_bead_peaks()` function in `bead_calibration.py` (lines 189–277) uses KDE-based peak detection. When the nanoViS High FCS file (`Nano_Vis_High.fcs`) was processed, the `calibrate_from_bead_fcs()` pipeline (line 912) asks `detect_bead_peaks()` for peaks matching all 7 expected bead sizes. But only 3 peaks were successfully detected — likely because:

- The High mix beads (142, 304, 600, 1020 nm) may not have been present in the FCS file used for calibration
- The nanoViS Low and High are **separate vials** — the Low FCS file only has 40/80/108/142 nm beads, and the High FCS file only has 142/304/600/1020 nm
- The auto-fit endpoint (`/calibration/fit`) was called with `sample_id=Nano_Vis_High`, but the peak matching defaulted to all 7 diameters, causing misalignment
- Alternatively, the `subcomponent` parameter was not set, so all 7 diameters were expected but only the subset in one vial was present

**The match function (`match_peaks_to_beads`, line 303)** assigns peaks to diameters by **sorted order** — smallest scatter → smallest diameter. If only 3 peaks were found from a High mix sample containing 142/304/600/1020 nm beads, but matched against the full list [40, 80, 108, 142, 304, 600, 1020], the 3 peaks would be assigned to the first 3 diameters (40, 80, 108 nm) regardless of whether those beads were actually present. This is a critical flaw in the matching logic.

#### Root Cause 5.2: Power law exponent b = 9.61 is physically impossible

Mie theory predicts that for polystyrene beads in the Rayleigh-to-resonance regime:
- **Rayleigh regime** (d << λ): Scatter ∝ d⁶ (b ≈ 6)
- **Resonance regime** (d ~ λ): b decreases due to oscillations
- **Geometric regime** (d >> λ): Scatter ∝ d² (b ≈ 2)

For beads spanning 40–1020 nm measured at 405 nm laser, the expected exponent is b ≈ 2–6. The fitted value of **b = 9.61** is anomalously high. This happens because:

1. Only 3 calibration points forces a steep fit
2. The 40 nm → 80 nm → 108 nm scatter jump is enormous (372 → 2.1M → 5.4M) — a factor of ~5,787× from 40 to 80 nm, but only 2.7× from 80 to 108 nm
3. This extreme jump at the low end drives the exponent up to "explain" the steep rise
4. With more bead points (especially 142, 304, 600, 1020 nm), the curve would flatten out

#### Root Cause 5.3: R² = 0.765 is too low for a valid calibration

An R² of 0.765 means the power law explains only 76.5% of the variance. For a calibration curve with only 3 points, this indicates a poor fit. With 3 points and 2 free parameters (a, b), there's essentially 1 degree of freedom — R² should be ≥0.99 for a valid physical model. The low R² signals that either:
- The model (power law) is wrong for this data
- The data points are mismatched (wrong bead→scatter assignments)
- Or both

### The inverse function compression effect

The inverse exponent is `1/b = 1/9.61 = 0.1041`. This means when FSC changes by a factor of 10, the diameter only changes by `10^0.1041 = 1.27×`. Practically:

```
FSC=100     → d = (100/1.547e-13)^0.1041      = 34.8 nm
FSC=10,000  → d = (10000/1.547e-13)^0.1041    = 56.1 nm
FSC=1M      → d = (1000000/1.547e-13)^0.1041  = 90.5 nm
```

**The entire 4-order-of-magnitude FSC dynamic range compresses into a 35–90 nm diameter band.** This explains why all particles appear to be ~42 nm regardless of their true size.

---

## 6. Root Cause Analysis — Multi-Solution Mie

### What multi-solution Mie does

**File:** `backend/src/physics/mie_scatter.py`, class `MultiSolutionMieCalculator` (line 772)

This is theoretically the most sophisticated sizing method:
1. Pre-computes lookup tables (LUTs) of theoretical SSC cross-sections for both violet (405 nm) and blue (488 nm) laser wavelengths
2. For each event, finds ALL diameters whose theoretical SSC matches the measured VSSC value within 15% tolerance
3. If multiple solutions exist, uses the VSSC/BSSC ratio to disambiguate

### The critical flaw: No instrument-to-theory normalization bridge

The `_calc_ssc()` method (line 883) computes:

```python
def _calc_ssc(self, diameter_nm, wavelength_nm):
    result = miepython.efficiencies(m, diameter_nm, wavelength_nm, n_env=self.n_medium)
    qback = result[2]
    cross_section = π × (diameter_nm/2)²
    return qback × cross_section  # Returns nm² units!
```

This returns a **theoretical backscatter cross-section in nm²**. Typical values:

| Diameter | Theory SSC (nm²) |
|---|---|
| 40 nm | 2.49 |
| 80 nm | 95.97 |
| 100 nm | 251.43 |
| 150 nm | 784.87 |
| 200 nm | 763.05 |
| 300 nm | 496.27 |

The `find_all_solutions()` method (line 907) then directly compares this against the **raw instrument VSSC value** (in arbitrary digitizer units):

```python
for i, (d, ssc) in enumerate(zip(self.lut_diameters, lut_ssc)):
    if abs(ssc - target_ssc) <= tolerance:  # ← comparing nm² with arbitrary units!
        solutions.append(d)
```

**The instrument SSC values (100–10,000,000 arbitrary units) are directly compared against theoretical cross-sections (0.1–1000 nm²).** Since instrument values are typically 10,000–1,000,000× larger than theoretical values, the algorithm matches instrument values against the LARGEST theoretical SSC values in the LUT, which correspond to sizes in the 200–350 nm range. This is why the median comes out at ~321 nm.

### Why the scale factor varies non-linearly

If the scale factor were constant (instrument_SSC = K × theory_SSC), we could apply a simple multiplicative correction. But the scale factor **varies by more than 100× across the bead size range** (see table in Section 4, Step 5). This variation comes from:

1. **Non-linear detector response** — PMT/APD gain is not perfectly linear across 4+ decades
2. **Electronic amplification** — log/linear amplifier nonlinearities
3. **Optical collection efficiency** — angle-dependent sensitivity that varies with particle size
4. **Background subtraction** — may shift the baseline differently at different intensity levels

This means a simple normalization constant won't work. A proper calibration curve (transfer function) is needed.

### The Mie non-monotonicity problem

Looking at the theoretical SSC values, there's a critical issue: **SSC is not monotonic with diameter**. The SSC peaks around 150 nm then decreases for larger particles due to Mie resonance effects:

```
d=100nm: SSC=251.4 nm²
d=150nm: SSC=784.9 nm²  ← peak
d=200nm: SSC=763.0 nm²  ← decreasing
d=300nm: SSC=496.3 nm²  ← further decrease
```

This means a given SSC value can map to **two or more** diameters (one below and one above the peak). The multi-solution Mie handles this via the VSSC/BSSC ratio disambiguation, but that only works if the SSC scale is correctly matched to theory — which it isn't.

---

## 7. Root Cause Analysis — Single-Solution Mie

### What single-solution Mie does

**File:** `backend/src/physics/mie_scatter.py`, class `MieScatterCalculator`

Used in the `/distribution-analysis` endpoint via `diameters_from_scatter_normalized()` (line 564). This method:

1. Builds a theoretical FSC LUT (diameter → forward scatter)
2. **Normalizes** raw FSC values by mapping the 5th–95th percentile of measured values to the theoretical FSC range
3. Interpolates to find diameters

### Why normalization helps but isn't reliable

The `diameters_from_scatter_normalized()` method (line 564) does attempt normalization:

```python
raw_p5, raw_p95 = np.percentile(raw_fsc_valid, [5, 95])
phys_min, phys_max = physical_fsc_unique[0], physical_fsc_unique[-1]
normalized_fsc = phys_min + (raw - raw_p5) / (raw_p95 - raw_p5) * (phys_max - phys_min)
```

This linearly maps the measurement range to the theoretical range. Problems:

1. **Assumes linear detector response** — not valid for PMT/APD detectors across wide dynamic range
2. **The mapping is sample-dependent** — different samples with different event distributions will produce different normalizations, making results inconsistent across samples
3. **Uses FSC (forward scatter) not SSC** — for small EVs, FSC is dominated by the asymmetry parameter g, which doesn't map cleanly to size
4. **Percentile-based normalization is circular** — it assumes the sample's size distribution spans the full theoretical range, which may not be true

### Where it's used

Only in the `/distribution-analysis` endpoint (line 2172 of `samples.py`). It feeds into `comprehensive_distribution_analysis()` for normality tests and distribution fitting (lognormal, gamma, Weibull). The distribution shape may be preserved even if the absolute scale is wrong, but the reported D10/D50/D90 values will be incorrect.

---

## 8. Affected Components (Full Codebase Map)

### Backend — Sizing Engines

| File | Component | Lines | Issue |
|---|---|---|---|
| `backend/src/physics/bead_calibration.py` | `BeadCalibrationCurve.fit()` | 565–644 | Power law `FSC = a × d^b` with b=9.61 from only 3 bead points |
| `backend/src/physics/bead_calibration.py` | `BeadCalibrationCurve.diameter_from_fsc()` | 669–684 | Inverse `d = (FSC/a)^(1/b)` compresses dynamic range |
| `backend/src/physics/bead_calibration.py` | `detect_bead_peaks()` | 189–277 | Peak detection may fail for beads outside the primary sensitivity range |
| `backend/src/physics/bead_calibration.py` | `match_peaks_to_beads()` | 303–332 | Order-based matching assigns wrong diameters if peak count ≠ bead count |
| `backend/src/physics/bead_calibration.py` | `calibrate_from_bead_fcs()` | 912–1052 | Full pipeline doesn't validate subcomponent match (Low vs High mix) |
| `backend/src/physics/mie_scatter.py` | `MultiSolutionMieCalculator._calc_ssc()` | 883–901 | Returns theoretical nm² without any normalization |
| `backend/src/physics/mie_scatter.py` | `MultiSolutionMieCalculator.find_all_solutions()` | 907–934 | Compares raw instrument units directly against nm² |
| `backend/src/physics/mie_scatter.py` | `MieScatterCalculator.diameters_from_scatter_normalized()` | 564–640 | Linear percentile normalization is sample-dependent and assumes linear detector |
| `backend/config/calibration/active_calibration.json` | Active calibration | — | Contains the flawed a=1.547e-13, b=9.61, R²=0.765 calibration |

### Backend — API Endpoints (8 endpoints affected)

| Endpoint | File:Line | Sizing Method | Bead Cal? | Multi-Mie? | Single-Mie? |
|---|---|---|---|---|---|
| `GET /{id}/fcs/results` | `samples.py:447` | Pre-stored Parquet column | — | — | — |
| `GET /{id}/scatter-data` | `samples.py:819` | Priority cascade | ✅ (1st) | ✅ (2nd) | ✅ (3rd) |
| `GET /{id}/clustered-scatter` | `samples.py:1062` | No bead cal | ❌ | ✅ | ✅ |
| `POST /{id}/gated-analysis` | `samples.py:1520` | No bead cal | ❌ | ✅ | ✅ (per-event loop, slow) |
| `GET /{id}/size-bins` | `samples.py:1824` | No bead cal | ❌ | ✅ | ✅ |
| `GET /{id}/distribution-analysis` | `samples.py:2026` | Single Mie only | ❌ | ❌ | ✅ |
| `POST /{id}/reanalyze` | `samples.py:2410` | Priority cascade | ✅ (1st) | ✅ (2nd) | ✅ (3rd) |
| `GET /{id}/fcs/values` | `samples.py:3163` | No bead cal | ❌ | ✅ | ✅ |

**Key observation:** Only 2 of 8 endpoints use bead calibration. The other 6 use multi-solution or single-solution Mie directly, meaning **even fixing the bead calibration won't fix all endpoints.**

### Backend — Inconsistencies Between Endpoints

1. **Hardcoded vs configurable RI:** `clustered-scatter` hardcodes `n_particle=1.40`, while `reanalyze` takes it from request parameters
2. **Different min_diameter defaults:** `size-bins` uses `min_diameter=10.0` while others use `20.0`
3. **Per-event vs batch:** `gated-analysis` uses `diameter_from_scatter()` per-event (slow), while others use batch methods
4. **No unified sizing pipeline:** Each endpoint independently initializes its own Mie calculators with potentially different parameters

### Frontend — Display Components

| Component | File | Data Source | Affected? |
|---|---|---|---|
| `StatisticsCards` | `components/flow-cytometry/statistics-cards.tsx` | `particle_size_median_nm`, `size_statistics.d50` | ✅ Shows wrong median |
| `ParticleSizeVisualization` | `components/flow-cytometry/particle-size-visualization.tsx` | `scatterData[].diameter` from `scatter-data` API | ✅ Wrong bin categorization |
| `IndividualFileSummary` | `components/flow-cytometry/individual-file-summary.tsx` | `size_statistics.d10/d50/d90` | ✅ Wrong percentiles |
| `OverlayHistogramChart` | `components/flow-cytometry/overlay-histogram-chart.tsx` | `particle_size_median_nm` | ✅ Wrong histogram scale |
| `PopulationShiftPanel` | `components/flow-cytometry/population-shift-panel.tsx` | Particle size metric | ✅ Wrong shift analysis |
| `FullAnalysisDashboard` | `components/flow-cytometry/full-analysis-dashboard.tsx` | `particle_size_median_nm` | ✅ Wrong summary |
| Zustand Store | `lib/store.ts` | Default `sizeRanges` (30-100, 100-200, 200-500 nm) | ⚠️ Ranges are OK, but reported data is wrong |

### Config Files

| File | Status |
|---|---|
| `backend/config/bead_standards/nanovis_d03231.json` | ✅ Correct — all 7 bead sizes with accurate TEM-measured diameters |
| `backend/config/calibration/active_calibration.json` | ❌ Flawed — only 3 beads, b=9.61, R²=0.765 |
| `backend/config/calibration/calibration_archived_*.json` | — Archive of previous (also flawed) calibrations |

---

## 9. What We Already Have Available

### ✅ Available in the codebase

1. **Complete bead datasheet** (`nanovis_d03231.json`) with all 7 bead sizes (40, 80, 108, 142, 304, 600, 1020 nm), CVs, and concentrations
2. **Bead FCS files** in `backend/data/uploads/`:
   - `20260122_145130_Nano Vis Low.fcs` (44/80/105/144 nm beads)
   - `20260122_145749_Nano Vis Low.fcs` (duplicate)
   - `20260122_150433_Nano Vis High.fcs` (144/300/600/1000 nm beads)
   - `20260122_150804_Nano Vis High.fcs` (duplicate)
   - `20260122_150820_Nano Vis Low.fcs` (duplicate)
3. **miepython library** — already installed, correctly calculates Mie efficiencies
4. **NTA reference data** — 5 PC3 measurements with D50 values for cross-validation (plus HEK, iPSC data also available)
5. **FCMPASSCalibrator class** (`mie_scatter.py`, lines 1130–1442) — already implements a Mie-theory-bridged calibration approach (bead measurements → transfer function → calibrated scatter → Mie inverse). **This is essentially the correct approach but is not wired into any API endpoint.**
6. **`subcomponent` parameter** in `calibrate_from_bead_fcs()` — already supports filtering beads by Low vs High mix, just not being used
7. **Multiple fit methods** — `BeadCalibrationCurve` supports `'power'`, `'polynomial'`, and `'interpolate'` fitting (only `'power'` is currently used)

### ⚠️ Partially available

1. **Peak detection** — Works for well-separated peaks but may fail for overlapping or low-count bead populations. Has adjustable parameters (`min_peak_distance_log`, `kde_bandwidth`) that haven't been optimized.
2. **Multi-fit method support** — The `fit_method` parameter supports `'polynomial'` and `'interpolate'` which might give better results than `'power'` for the full 7-bead range, but haven't been tested.

### ❌ Not available

1. **Proper bead calibration with all 7 sizes** — The Low and High FCS files haven't been processed together into a single calibration
2. **Transfer function (instrument units → theoretical Mie units)** — The key missing piece that would make multi-solution Mie work correctly
3. **Instrument-specific gain/sensitivity documentation** — We don't have the CytoFLEX S PMT voltage settings or gain parameters used during acquisition
4. **NTA + FCS co-registered validation** — The NTA and FCS measurements use different sample preparations; we don't have NTA and FCS from the exact same vial at the exact same time for rigorous validation
5. **Multi-sample calibration validation** — The calibration has only been tested against PC3 EXO1; we haven't verified against HEK EVs, iPSC EVs, or other sample types

---

## 10. What We Need From the Team

### Critical (blocking — needed for any fix)

1. **Confirm which bead FCS files to use:** Are `Nano_Vis_Low.fcs` and `Nano_Vis_High.fcs` from the same instrument session with the same PMT settings as the PC3 EXO1 measurements? Calibration is only valid if beads and samples were measured on the same instrument with the same settings.

2. **Instrument settings documentation:** What were the VSSC1-H and BSSC-H PMT voltages/gains during the bead measurement runs? Were they the same during the PC3 EXO1 runs? If different gain settings were used, the calibration won't transfer.

3. **Subcomponent confirmation:** When running auto-fit, should we process `Nano_Vis_Low.fcs` and `Nano_Vis_High.fcs` separately (each with its own 4 beads), then merge? Or should we look for a combined run FCS file?

### Important (for validation)

4. **Do we have FCS runs from the ZetaView?** The `backend/NTA/PC3/` directory contains `.fcs` files alongside the NTA `.txt` files (e.g., `20251217_0005_PC3_100kDa_F5_size_488_1000-010-030-100.0-15-1-0_20251217-102923.fcs`). Are these ZetaView scatter data that could be used for cross-validation?

5. **Refractive index for PC3 exosomes:** We're using n=1.40 for EVs. Has the team measured or estimated the RI for PC3-derived exosomes specifically? Values from 1.37–1.45 have been reported in literature. This affects Mie calculations by ±15%.

6. **Do other sample types (HEK, iPSC) show the same sizing issue?** If so, this confirms a systematic calibration error rather than a sample-specific anomaly.

### Nice to have

7. **Silica bead FCS data:** Silica beads (RI ~1.46, closer to EVs than polystyrene RI ~1.59) would improve calibration accuracy. Does the lab have silica bead standards?

8. **FCMPASS validation data:** The FCMPASS paper (Welsh et al., Cytometry A 2020) provides reference datasets. Could we compare our implementation against their published results?

---

## 11. Proposed Solutions (Ranked)

### Solution A: FCMPASS-Style Transfer Function Calibration (Recommended)

**Concept:** Use bead measurements to build a **transfer function** that maps instrument scatter units to physical Mie scatter cross-sections, then apply the Mie inverse function to get diameters.

**Why this is the best approach:**
- It's the standard approach in the field (Welsh et al., 2020; FCMPASS software)
- Accounts for instrument-specific detector response
- Handles non-linear gain across the dynamic range
- The `FCMPASSCalibrator` class already exists in our codebase (line 1130)
- Can be validated against published reference data

**Implementation steps:**
1. Process BOTH `Nano_Vis_Low.fcs` AND `Nano_Vis_High.fcs` to get scatter values for all 7 bead sizes
2. Calculate theoretical Mie scatter (Qback × cross-section) for each bead diameter (using polystyrene RI=1.591)
3. Fit a polynomial transfer function: `measured_SSC → theoretical_Mie_SSC`
4. For unknown EVs: `measured_SSC → transfer_function → Mie_SSC → inverse_Mie(RI=1.40) → diameter`
5. Wire `FCMPASSCalibrator` into all 8 API endpoints consistently

**Effort:** 3–5 days  
**Risk:** Low — standard approach, most code already exists  
**Accuracy:** Expected ±20% based on FCMPASS literature

### Solution B: Improved Bead Calibration with All 7 Sizes

**Concept:** Fix the current bead calibration to use all 7 bead sizes instead of just 3, and use a more appropriate fitting function.

**Why this might work:**
- With 7 points spanning 40–1020 nm, the power law exponent should be more physically reasonable
- Could use piecewise or spline fitting instead of single power law
- Simpler to implement than FCMPASS — just fix the peak matching

**Implementation steps:**
1. Process `Nano_Vis_Low.fcs` with `subcomponent='nanoViS_Low'` to get beads 40/80/108/142
2. Process `Nano_Vis_High.fcs` with `subcomponent='nanoViS_High'` to get beads 142/304/600/1020
3. Merge the bead standards (using 142 nm as an overlap validation point)
4. Fit with `fit_method='interpolate'` (cubic spline over 7 points)
5. Validate against NTA D50 values

**Effort:** 2–3 days  
**Risk:** Medium — direct instrument-to-diameter mapping doesn't account for the RI difference between beads (1.591) and EVs (1.40)  
**Accuracy:** Will be better but still limited by the RI discrepancy

**Key limitation:** Polystyrene beads scatter MUCH MORE than EVs of the same diameter because polystyrene has higher RI (1.591 vs ~1.40). A 100 nm polystyrene bead produces ~3× more scatter than a 100 nm EV. The direct bead calibration doesn't account for this — it maps "bead-equivalent sizes" not "true EV sizes."

### Solution C: Hybrid Approach — Bead-Calibrated Multi-Solution Mie

**Concept:** Use bead calibration to normalize instrument values, then feed the calibrated values into the multi-solution Mie calculator.

**Implementation steps:**
1. Build bead calibration with all 7 sizes (Solution B steps 1–3)
2. Derive the transfer function: `measured_SSC → calibrated_cross_section_nm²`
3. Feed calibrated cross-sections into `MultiSolutionMieCalculator.find_all_solutions()`
4. Use the dual-wavelength ratio disambiguation on properly scaled values

**Effort:** 4–6 days  
**Risk:** Medium — more complex, but gives best theoretical accuracy  
**Accuracy:** Expected ±10-15% — combines instrument calibration with physics-based disambiguation

### Solution D: NTA-Anchored Normalization (Quick Fix)

**Concept:** Use the known NTA median (151.7 nm) to derive a single normalization factor for the current Mie calculations.

**Implementation steps:**
1. Calculate what the multi-solution Mie predicts for the same sample (321 nm median)
2. Derive correction factor: 151.7/321 ≈ 0.473
3. Apply correction factor to all multi-solution Mie outputs

**Effort:** 0.5 day  
**Risk:** High — only valid for PC3 EXO1 sample; won't generalize to other samples  
**Accuracy:** Perfect for PC3, but will be wrong for different cell lines, EV isolation methods, or instrument settings

---

## 12. Implementation Roadmap

### Phase 1: Fix Bead Calibration (Immediately actionable)

```
Week 1, Days 1-2:
├── Process Nano_Vis_Low.fcs with subcomponent='nanoViS_Low' filter
├── Process Nano_Vis_High.fcs with subcomponent='nanoViS_High' filter
├── Merge bead data with 142nm overlap validation
├── Fit with interpolation (not power law) over 7 points
├── Validate R² > 0.99
└── Compare against NTA D50 — expected improvement from 42nm → closer to 150nm
```

### Phase 2: Wire FCMPASS Calibration (1 week)

```
Week 1, Days 3-5:
├── Wire FCMPASSCalibrator into the calibration API endpoint
├── Create new endpoint: POST /calibration/fcmpass-fit
├── Build transfer function from 7 bead points
├── Apply calibrated Mie inverse to scatter-data endpoint
├── Update all 8 sizing endpoints to use unified pipeline
└── Cross-validate against NTA for PC3, HEK, iPSC samples
```

### Phase 3: Unify Sizing Pipeline (1 week)

```
Week 2:
├── Create a centralized SizingService class
├── Replace per-endpoint Mie calculator initialization
├── Ensure consistent RI/wavelength/angle parameters across all endpoints
├── Add 'sizing_method' to all API responses for UI transparency
├── Add calibration quality warnings to UI
├── Frontend: display 'sizing_method' and 'calibration_r_squared' to user
└── Comprehensive testing with all available NTA reference data
```

### Phase 4: Validation & Documentation (ongoing)

```
Week 3+:
├── Process all NTA datasets (HEK, iPSC P1, P2, P2.1)
├── Cross-validate sizing against each NTA dataset
├── Publish internal calibration report with accuracy metrics
├── Add automated calibration quality checks
└── Update user documentation
```

---

## 13. Appendix: Mathematical Verification

### A. Current Bead Calibration Math

```
Active fit parameters:
  a = 1.5473138208580926e-13
  b = 9.60988502676712
  R² = 0.764830624903308

Forward:  FSC = 1.547e-13 × d^9.61
Inverse:  d = (FSC / 1.547e-13)^(1/9.61)
          d = (FSC / 1.547e-13)^0.1041

Verification with bead data:
  40nm bead:  FSC_pred = 1.547e-13 × 40^9.61 = 6.03e2    (actual: 372.3)
  80nm bead:  FSC_pred = 1.547e-13 × 80^9.61 = 4.70e5    (actual: 2,156,170)
  108nm bead: FSC_pred = 1.547e-13 × 108^9.61 = 5.01e6   (actual: 5,376,525)

Inverse applied to EV VSSC values:
  VSSC=100     → d = 34.8 nm   (expected: ~120-170 nm from NTA)
  VSSC=1000    → d = 44.2 nm   (expected: ~120-170 nm)
  VSSC=10000   → d = 56.1 nm   (expected: ~120-170 nm)
  VSSC=100000  → d = 71.3 nm   (expected: ~120-170 nm)
  VSSC=1000000 → d = 90.5 nm   (expected: ~120-170 nm)
```

### B. Theoretical Mie Cross-Sections vs Instrument Values

EV refractive index = 1.40, medium = 1.33, wavelength = 405 nm:

```
Diameter (nm) | Qback      | Area (nm²)   | Theory SSC (nm²) | Instrument VSSC (arb.)
40            | 0.001979   | 1,256.6      | 2.49              | 372
80            | 0.019093   | 5,026.5      | 95.97             | 2,156,170
100           | 0.032013   | 7,854.0      | 251.43            | ~
108           | 0.036628   | 9,160.9      | 335.55            | 5,376,525
150           | 0.044415   | 17,671.5     | 784.87            | ~
200           | 0.024289   | 31,415.9     | 763.05            | ~
300           | 0.007021   | 70,685.8     | 496.27            | ~
```

Note: Instrument VSSC values are for polystyrene beads (RI=1.591), while theory SSC values above are for EVs (RI=1.40). The RI difference means beads scatter 2-5× more than EVs of the same size. A proper calibration (Solution A) accounts for this by:
1. Computing bead Mie theory with RI=1.591
2. Fitting: instrument_SSC → bead_Mie_SSC (transfer function)
3. Computing EV Mie theory with RI=1.40
4. Applying transfer function then EV Mie inverse

### C. NTA Reference Statistics

```
Sample: PC3 100kDa exosomes
Instrument: ZetaView (S/N 24-1152)
Laser: 488 nm scatter mode
Temperature: 25°C
SOP: EV_488

Measurement D50 values (nm): 127.3, 145.9, 155.6, 171.5, 158.5
Mean D50: 151.7 nm
Std of D50s: 16.2 nm
CV of D50s: 10.7%

Inter-measurement variability of 10.7% is typical for NTA on heterogeneous
biological EV samples. This establishes the ground truth range for validation.
```

### D. Summary Comparison Table

```
Method               | D50 (nm) | Expected D50 | % Error  | Root Cause
---------------------|----------|-------------|----------|----------------------------
NTA (ZetaView)       | 151.7    | —           | —        | Ground truth
Bead Calibration     | 42-47    | ~150        | -70%     | b=9.61/ 3 beads / R²=0.76
Multi-Solution Mie   | ~321     | ~150        | +112%    | No normalization bridge
Single-Solution Mie  | Variable | ~150        | Variable | Sample-dependent scaling
FCMPASS (not wired)  | N/A      | ~150        | —        | Not yet connected to API
```

---

## Document History

| Date | Author | Change |
|---|---|---|
| 2026-02-12 | CRMIT Engineering | Initial diagnosis report |
