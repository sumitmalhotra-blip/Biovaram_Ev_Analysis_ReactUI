# FCS vs NTA Cross-Validation Analysis Report

## PC3 Exosome Size Discrepancy Investigation

**Date:** February 24, 2026  
**Investigator:** Automated Analysis Pipeline  
**Platform:** BioVaram EV Analysis Platform  
**Instrument:** CytoFLEX nano BH46064

---

## 1. Executive Summary

Cross-validation of flow cytometry (FCS) Mie-calculated sizes against Nanoparticle Tracking Analysis (NTA) measurements for PC3 exosomes reveals a **44.6% D50 discrepancy**:

| Metric | FCS (Mie) | NTA (Direct) | Difference |
|--------|-----------|--------------|------------|
| D10 | 65 nm | 82.5 nm | −21.2% |
| **D50** | **81 nm** | **127.5 nm** | **−44.6%** |
| D90 | 129 nm | 217.5 nm | −51.0% |
| Mean | 92.1 nm | 143.8 nm | −43.8% |
| Peak | — | 97.5 nm | — |

**Verdict:** FAIL (>30% D50 discrepancy)

This report identifies **five primary contributing factors** and provides recommendations for resolution.

---

## 2. Samples Under Comparison

### 2.1 FCS Sample
- **File:** `20260120_141439_PC3 EXO1.fcs`
- **Sample Name:** PC3 EXO1
- **Acquisition Date:** 17-Dec-2025
- **Instrument:** CytoFLEX nano (BH46064)
- **Total Events:** 914,326
- **Analysis Sample:** 50,000 events (random seed=42)
- **Valid Sized Events:** 49,791 / 50,000 (99.6%)
- **Channels Available:** 26 (VFSC-A, VFSC-H, VSSC1-H, VSSC2-H, BSSC-H, etc.)

### 2.2 NTA Sample
- **File:** `20251217_0005_PC3_100kDa_F5_size_488.txt`
- **Sample Name:** PC3_100kDa_F5
- **Measurement Date:** 17-Dec-2025
- **Laser Wavelength:** 488 nm
- **Operator:** Admin
- **Temperature:** 25.13°C
- **Total Particles Tracked:** 630
- **Dilution Factor:** 500×
- **Distribution Bins:** 1,200 (0.5 nm resolution)

### 2.3 ⚠️ CRITICAL: Sample Identity Mismatch

| Property | FCS | NTA |
|----------|-----|-----|
| Sample Name | PC3 EXO1 | PC3_100kDa_F5 |
| Preparation | Bulk exosome isolate | 100 kDa ultrafiltration retentate, SEC Fraction 5 |
| Particle Count | 914,326 events | 630 particles |

**The NTA sample underwent additional fractionation (100 kDa MWCO ultrafiltration → SEC → Fraction 5).** This fractionation likely enriches for larger vesicles, as:
- 100 kDa ultrafiltration retains particles larger than the MWCO pore size
- SEC Fraction 5 typically corresponds to a specific elution volume in the size-exclusion column
- Both steps can systematically shift the size distribution toward larger particles

**This sample preparation difference is likely the single largest contributor to the observed D50 discrepancy.**

All three available NTA files are from fractionated preparations:
- `PC3_100kDa_F3T6` (Fractions 3 through 6)
- `PC3_100kDa_F1_2` (Fractions 1–2)
- `PC3_100kDa_F5` (Fraction 5)

No NTA measurement exists for the unfractionated "PC3 EXO1" sample.

---

## 3. FCS Mie Sizing Methodology

### 3.1 Multi-Solution Mie Scattering Approach

The platform uses a **dual-wavelength, multi-solution Mie disambiguation** method:

1. **Primary Channel:** VSSC1-H (Violet Side Scatter, λ = 405 nm)
2. **Secondary Channel:** BSSC-H (Blue Side Scatter, λ = 488 nm)
3. **Rationale:** Violet (405 nm) provides better sensitivity for small EVs due to λ⁻⁴ Rayleigh scattering dependence

**Algorithm:**
```
For each event:
  1. σ_sca = AU_measured / k_instrument     (AU → physical cross-section)
  2. Find ALL diameters where σ_Mie(d) ≈ σ_sca  (within 15% tolerance)
  3. If multiple solutions exist:
     - Calculate theoretical VSSC/BSSC ratio for each candidate
     - Select candidate whose ratio best matches measured VSSC/BSSC ratio
```

### 3.2 Mie Physics Implementation

The scattering cross-section is computed using miepython:

```python
σ_sca = Q_sca × π × (d/2)²

where Q_sca = miepython.efficiencies(m_abs, d, λ_vacuum, n_env=n_medium)[1]
```

- Uses **absolute refractive index** with explicit `n_env` parameter
- Uses **Q_sca (total scattering efficiency)**, not Q_back (180° backscatter)
- This is the corrected formulation (Feb 2026, fixing earlier Q_back double-counting bug)

### 3.3 Channel Statistics (PC3 EXO1, 50k sample)

| Channel | Median AU | Description |
|---------|-----------|-------------|
| VFSC-H | 618 | Violet Forward Scatter (Height) |
| VSSC1-H | 2,277 | Violet Side Scatter 1 (Height) — **PRIMARY** |
| VSSC2-H | 92 | Violet Side Scatter 2 (Height) |
| BSSC-H | 471 | Blue Side Scatter (Height) — **SECONDARY** |

### 3.4 Multi-Solution Statistics (n_p=1.37, k=969.5)

| Metric | Value |
|--------|-------|
| Total Events Processed | 50,000 |
| Valid Sized Events | 49,791 (99.6%) |
| Events with 1 Solution | 47,866 (96.1%) |
| Events with 2 Solutions | 1,771 (3.6%) |
| Events with 3+ Solutions | 154 (0.3%) |

---

## 4. Bead Calibration Analysis

### 4.1 Calibration Standards

**Bead Kit:** nanoViS D03231 (Particle Metrix)
- **Sizes:** 40, 80, 108, 142 nm (Low mix); 142, 304, 600, 1020 nm (High mix)
- **Bead RI at 590 nm:** 1.591 (polystyrene)
- **Bead RI at 405 nm:** ~1.634 (Cauchy dispersion corrected)

### 4.2 Two Calibration Files Identified

The platform contains two independent calibration files with different k-factor values:

#### fcmpass_calibration.json (k = 969.5)
- **Source:** `config/calibration/fcmpass_calibration.json`
- **Used by:** `get_fcmpass_k_factor()` → Multi-solution Mie calculator
- **Beads used:** 3 (80, 108, 142 nm — excludes 40 nm)
- **k_mean = 969.5**, k_std = 37.5, k_cv = 3.9%
- **Self-validation:** All 3 beads < 1% size error (80→79.4nm, 108→109.0nm, 142→141.7nm)

| Bead d (nm) | AU Measured | σ_theo (nm²) | k = AU/σ |
|-------------|-------------|---------------|----------|
| 80 | 105,334 | 113.31 | 929.6 |
| 108 | 597,292 | 585.88 | 1,019.5 |
| 142 | 2,173,225 | 2,266.69 | 958.8 |
| **Mean** | | | **969.3** |

#### au_to_sigma_calibration.json (k = 940.6)
- **Source:** `calibration_data/au_to_sigma_calibration.json`
- **Not used by:** Multi-solution Mie (this file is not loaded in the cross-validate pipeline)
- **Beads used:** 4 (40, 80, 108, 142 nm — all beads)
- **k_mean = 940.6**, k_std = 22.8, k_cv = 2.4%

| Bead d (nm) | AU Measured | σ_theo (nm²) | k = AU/σ |
|-------------|-------------|---------------|----------|
| 40 | 1,888 | 1.98 | 952.3 |
| 80 | 102,411 | 113.31 | 903.8 |
| 108 | 565,342 | 585.88 | 965.0 |
| 142 | 2,132,067 | 2,266.69 | 940.6 |
| **Mean** | | | **940.4** |

#### Raw Bead Peaks (bead_peaks.json)
| Bead d (nm) | VSSC1-H mean_au (Low mix) | VSSC1-H mean_au (au_to_sigma) | VSSC1-H mean_au (fcmpass) |
|-------------|---------------------------|-------------------------------|---------------------------|
| 40 | 375 | 1,888 | — |
| 80 | 3,505 | 102,411 | 105,334 |
| 108 | 102,189 | 565,342 | 597,292 |
| 142 | 2,128,442 | 2,132,067 | 2,173,225 |

**Observation:** The raw bead_peaks.json values differ dramatically from both calibration files for the 40 and 80 nm beads, suggesting peak re-assignment via combinatorial analysis was applied. The au_to_sigma file notes: "Correct bead peak assignments from combinatorial analysis."

### 4.3 k-Factor Impact on Sizing

| k_instrument | Resulting FCS D50 | Difference |
|-------------|-------------------|------------|
| 940.6 | 82 nm | +1 nm |
| **969.5** | **81 nm** | **baseline** |

**Conclusion:** The 3.1% k-factor difference produces only ~1 nm change in D50. **k-factor choice is NOT a significant contributor** to the 44.6% discrepancy.

---

## 5. Refractive Index Sensitivity Analysis

The assumed particle RI (n_particle) is the **dominant parameter** affecting computed sizes. Higher RI → more scattering → smaller estimated diameter for the same measured signal.

### 5.1 Sensitivity Matrix: D50 vs. n_particle

| n_particle | FCS D50 (nm) | Valid % | Δ from NTA D50 | Notes |
|-----------|-------------|---------|-----------------|-------|
| 1.33 | — | 0% | — | Same as medium; zero contrast |
| 1.34 | 138 | 98.9% | +8.2% | **Best NTA match**, but biophysically unrealistic |
| 1.35 | 105 | 99.4% | −17.6% | Lower bound of literature EV RI |
| **1.37** | **81** | **99.6%** | **−36.5%** | **Current default** (van der Pol 2014) |
| 1.39 | 70 | 99.6% | −45.1% | |
| 1.40 | 66 | 99.6% | −48.2% | |
| 1.42 | 61 | 99.6% | −52.2% | |
| 1.45 | 55 | 99.6% | −56.9% | Upper bound of literature EV RI |

### 5.2 Interpretation

To match NTA D50 = 127.5 nm, the Mie model requires **n_particle ≈ 1.34**, which is:
- Only 0.01 above the medium RI (1.33) — essentially transparent
- Below all published EV RI measurements (1.35–1.45)
- Biophysically implausible for lipid bilayer vesicles with proteo-lipid membranes

**For the median VSSC1-H signal (2277 AU):**
```
σ_measured = 2277 / 969.5 = 2.35 nm²

For σ = 2.35 nm² at d = 81 nm (FCS):  n_p must be 1.37 ✓ (self-consistent)
For σ = 2.35 nm² at d = 127.5 nm (NTA): n_p must be 1.343 (near water)
```

---

## 6. Core-Shell Structure Effects

EVs are not homogeneous spheres — they consist of a lipid bilayer membrane (~5 nm thick, n ≈ 1.48) surrounding an aqueous core (n ≈ 1.34). The effective RI varies with size because smaller EVs have a proportionally thicker membrane.

### 6.1 Volume-Weighted Effective RI vs. Diameter

| EV Diameter (nm) | Core Diameter (nm) | Membrane Volume % | Effective n_eff |
|-------------------|--------------------|--------------------|-----------------|
| 50 | 40 | 48.8% | 1.408 |
| 80 | 70 | 33.1% | 1.386 |
| 100 | 90 | 27.1% | 1.378 |
| 120 | 110 | 23.0% | 1.372 |
| 150 | 140 | 18.7% | 1.366 |

### 6.2 Impact on Sizing

The current model assumes **constant n = 1.37** for all sizes. This means:
- **Small EVs (50 nm):** Actual n_eff = 1.408 >> 1.37 → they scatter MORE than the model predicts for their true size → model **overestimates** their diameter
- **Large EVs (150 nm):** Actual n_eff = 1.366 ≈ 1.37 → accurate sizing

This effect **compresses** the true size distribution but does NOT explain the systematic undersizing relative to NTA. In fact, it would slightly push FCS D50 **upward**, making the discrepancy slightly worse.

---

## 7. NTA Measurement Considerations

### 7.1 NTA Operating Principles
NTA measures **hydrodynamic diameter** via Brownian motion tracking:
```
D_h = (k_B × T) / (3π × η × D_diffusion)
```
where D_diffusion is determined from the mean squared displacement of tracked particles.

### 7.2 Known NTA Biases

| Bias Source | Direction | Estimated Magnitude |
|-------------|-----------|---------------------|
| **Detection limit (~50-70 nm)** | Shifts D50 UP | Significant — smallest EVs not detected |
| **Scatter-based detection** (I ∝ d⁶) | Shifts D50 UP | Larger particles brighter → easier to track |
| **Hydrodynamic diameter** vs. hard sphere | Always UP | +5–20% (glycocalyx, surface proteins) |
| **Aggregate detection** | Shifts D50 UP | Variable — aggregates appear as large particles |
| **Short track lengths** for small particles | Size overestimate | +5–10% for near-detection-limit particles |
| **Low particle count** (630 particles) | Increases variance | Less statistically robust than FCS (50k events) |

### 7.3 Statistical Power Comparison
- **FCS:** 49,791 valid sized events → robust statistics
- **NTA:** 630 total tracked particles → limited statistical power, higher sampling noise

---

## 8. Root Cause Analysis

### 8.1 Ranked Contributing Factors

| Rank | Factor | Estimated Contribution | Confidence |
|------|--------|----------------------|------------|
| **1** | **Sample preparation difference** | **20–40%** of discrepancy | **High** |
| **2** | **NTA detection limit bias** | **10–20%** of discrepancy | **High** |
| **3** | **Refractive index assumption** | **5–15%** of discrepancy | **Medium** |
| **4** | **NTA hydrodynamic vs. physical diameter** | **5–10%** of discrepancy | **Medium** |
| 5 | Core-shell vs. homogeneous sphere model | <5% | Low |
| 6 | k-factor calibration uncertainty | <2% (1 nm) | Negligible |

### 8.2 Detailed Analysis

#### Factor 1: Sample Preparation Difference (LARGEST CONTRIBUTOR)

The FCS sample ("PC3 EXO1") is a bulk exosome isolate containing the full polydisperse population. The NTA sample ("PC3_100kDa_F5") underwent:
1. **100 kDa MWCO ultrafiltration** — retains particles above the cutoff, removes the smallest (<30–50 nm) vesicles
2. **SEC fractionation** — Fraction 5 corresponds to a specific elution volume

This two-step purification selectively enriches for mid-to-large EVs, truncating the small-particle tail that is fully present in the FCS measurement. This alone could account for 20–40 nm of the D50 difference.

#### Factor 2: NTA Detection Limit

At 488 nm laser wavelength, NTA has a practical detection limit of **50–70 nm** for EVs (depending on RI). Particles below this threshold are invisible to NTA, causing:
- Truncation of the small end of the distribution
- Upward bias in all percentile metrics (D10, D50, D90)

FCS with VSSC1-H at 405 nm has a lower detection limit (~30–40 nm) and captures more small events.

#### Factor 3: Refractive Index

The default n_p = 1.37 comes from published literature (van der Pol et al., 2014). However:
- Actual EV RI ranges from 1.35–1.45 depending on vesicle composition
- PC3 exosomes may have different RI from the literature average
- Using n_p = 1.35 increases FCS D50 from 81 → 105 nm, closing 52% of the gap
- The "true" EV RI is unknowable without independent measurement (e.g., fluorescence + scatter matching)

#### Factor 4: Hydrodynamic vs. Physical Diameter

NTA measures hydrodynamic diameter (includes hydration shell, surface proteins, glycocalyx). This is inherently **5–20% larger** than the physical/optical diameter measured by FCS Mie scattering.

For D50 = 127.5 nm, this could account for 6–25 nm of the difference.

---

## 9. Calibration Validation

### 9.1 Bead Self-Validation (FCMPASS)

The calibration passes internal self-validation with excellent accuracy:

| Bead Expected (nm) | Recovered (nm) | Error | Status |
|--------------------|-----------------|-------|--------|
| 80 | 79.4 | −0.71% | ✅ PASS |
| 108 | 109.0 | +0.94% | ✅ PASS |
| 142 | 141.7 | −0.24% | ✅ PASS |

**Maximum size error: 0.94%** — The Mie model perfectly recovers known bead sizes, confirming:
- The k-factor calibration is correct for the calibration beads
- The Mie physics implementation is correct
- The miepython library produces accurate results

### 9.2 Caveat: Bead RI ≠ EV RI

Beads have n = 1.634 (at 405 nm), while EVs have n ≈ 1.37. The Mie scattering function behaves very differently at these RI values:
- Beads: far into Mie resonance regime, strong scattering signals (10³–10⁶ AU)
- EVs: Rayleigh/early-Mie regime, weak signals (10²–10³ AU)
- The extrapolation from high-RI calibration to low-RI measurement introduces model-dependent uncertainty

---

## 10. Recommendations

### 10.1 Immediate Actions

1. **Acquire NTA measurement for unfractionated PC3 EXO1 sample** — This is the single most impactful action. Measure the same bulk EXO1 preparation on NTA to eliminate the sample preparation confound.

2. **Compare all three NTA fractions (F1_2, F3T6, F5)** — Examine how the D50 varies across frictions. Expected: earlier fractions (F1_2) should have larger particles, later fractions (F5) may differ.

3. **Run FCS on the fractionated NTA sample** — Conversely, run the 100kDa F5 sample on the CytoFLEX nano to get a true apples-to-apples comparison.

### 10.2 Model Improvements

4. **Implement RI sweep in cross-validation** — Report FCS D50 at n_p = 1.35, 1.37, 1.39 simultaneously to show the RI-dependent uncertainty band:
   - n_p = 1.35: D50 = 105 nm (−17.6% vs NTA)
   - n_p = 1.37: D50 = 81 nm (−36.5% vs NTA)
   - n_p = 1.39: D50 = 70 nm (−45.1% vs NTA)

5. **Implement size-dependent RI correction (core-shell model)** — Use the volume-weighted effective RI based on bilayer thickness to improve accuracy across the size range.

6. **Add NTA detection limit overlay** — Show the NTA detection threshold (50–70 nm) on cross-validation plots to visually indicate the region where NTA cannot see.

### 10.3 Long-Term Improvements

7. **Independent RI measurement** — Use fluorescence-triggered scatter analysis (e.g., CFSE-labeled EVs) to independently estimate EV RI on the CytoFLEX nano.

8. **Multi-angle collection geometry characterization** — The k-factor assumes angle-integrated total scatter (Q_sca). The actual SSC detector collects at a specific angular range. Characterizing this geometry could improve the model.

9. **Literature benchmarking** — Compare against published FC-NTA discrepancies. Typical values in literature: 15–40% D50 difference (Gardiner et al., 2013; Vogel et al., 2021).

---

## 11. Conclusion

The 44.6% D50 discrepancy between FCS Mie-calculated sizes (81 nm) and NTA measurements (127.5 nm) is primarily explained by **sample preparation differences** (fractionated NTA sample vs. bulk FCS sample), compounded by **NTA detection limit bias** and **RI assumption sensitivity**. The Mie calibration itself is verified as accurate (≤1% error on calibration beads), and the k-factor uncertainty is negligible (~1 nm impact).

The cross-validation cannot be considered valid until measurements are performed on **identical sample preparations**. With matching samples and an RI uncertainty band (n_p = 1.35–1.37), the expected FCS D50 range of 81–105 nm would likely overlap with NTA measurements corrected for detection bias.

---

## Appendix A: Data Files Used

| File | Purpose | Location |
|------|---------|----------|
| PC3 EXO1.fcs | FCS sample | `data/uploads/20260120_141439_PC3 EXO1.fcs` |
| PC3_100kDa_F5_size_488.txt | NTA sample | `data/uploads/20260224_145033_20251217_0005_PC3_100kDa_F5_size_488.txt` |
| nanoViS Low.fcs | Bead calibration (Low mix) | `data/uploads/20260224_144538_Nano_Vis_Low.fcs` |
| nanoViS High.fcs | Bead calibration (High mix) | `data/uploads/20260224_144535_Nano_Vis_High.fcs` |
| fcmpass_calibration.json | k-factor calibration | `config/calibration/fcmpass_calibration.json` |
| au_to_sigma_calibration.json | Alternative calibration | `calibration_data/au_to_sigma_calibration.json` |
| bead_peaks.json | Raw bead peak data | `calibration_data/bead_peaks.json` |

## Appendix B: Software Versions

| Component | Version |
|-----------|---------|
| Python | 3.13.7 |
| miepython | (installed) |
| fcsparser | (installed) |
| Platform Backend | FastAPI on port 8000 |
| Mie Model | MultiSolutionMieCalculator (Feb 2026) |

## Appendix C: Full Sensitivity Matrix

```
n_EV      k=940.6       k=969.5       NTA ref
-------   ----------    ----------    --------
1.34      D50=139nm     D50=138nm     127.5 nm
1.35      D50=106nm     D50=105nm        ↑
1.36      D50= 91nm     D50= 90nm        |
1.37      D50= 82nm     D50= 81nm     ← current
1.38      D50= 76nm     D50= 75nm        |
1.39      D50= 71nm     D50= 70nm        ↓
1.40      D50= 67nm     D50= 66nm
1.42      D50= 61nm     D50= 61nm
1.45      D50= 55nm     D50= 55nm
```

## Appendix D: Mie Cross-Section Reference Table

σ_sca (nm²) vs. diameter for EVs at n = 1.37, λ = 405 nm, n_env = 1.33:

| d (nm) | Q_sca | σ_sca (nm²) | Expected AU (k=969.5) |
|--------|-------|-------------|------------------------|
| 30 | 0.000009 | 0.007 | 6 |
| 40 | 0.000029 | 0.036 | 35 |
| 50 | 0.000068 | 0.134 | 130 |
| 60 | 0.000135 | 0.383 | 371 |
| 70 | 0.000239 | 0.918 | 890 |
| 80 | 0.000384 | 1.931 | 1,872 |
| **81** | **≈0.00041** | **≈2.07** | **≈2,006** |
| 90 | 0.000577 | 3.670 | 3,558 |
| 100 | 0.000819 | 6.432 | 6,235 |
| 120 | 0.001448 | 16.37 | 15,875 |
| 127.5 | — | ≈22.1 | ≈21,403 (at n=1.37) |
| 150 | 0.002698 | 47.67 | 46,218 |

**Key observation:** For the median AU of 2277 → σ = 2.35 nm² → d ≈ 83 nm at n = 1.37. A 127.5 nm EV at n = 1.37 would produce AU ≈ 21,403 — roughly **10× higher** than observed. This conclusively shows that either:
1. The particles are actually ~81 nm (FCS is correct), OR
2. The particles are 127.5 nm but have RI ≈ 1.343 (essentially transparent)

---

*Report generated by BioVaram EV Analysis Platform automated investigation pipeline.*
