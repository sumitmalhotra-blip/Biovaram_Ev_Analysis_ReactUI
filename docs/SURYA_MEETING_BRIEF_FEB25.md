# Meeting Brief: EV Sizing Pipeline — What We Built, What We See, What We Need

**Prepared for:** Surya & Team Review  
**Date:** February 25, 2026  
**Prepared by:** Sumit / Dev Team  
**Context:** Parvesh reviewed the latest results and wants Surya's input on collection angles and error margins

---

## Part 1: What Did We Build? (The Sizing Pipeline)

### The Big Picture

We take a raw FCS file (flow cytometry scatter data) and convert it into **physical particle diameters in nanometers** using Mie scattering theory. Think of it as: the CytoFLEX nano shines lasers at each particle, measures how much light scatters, and we use physics to work backwards from the scatter signal to figure out the particle's size.

### The 4-Step Pipeline

```
Step 1: BEAD CALIBRATION
   nanoViS beads (known sizes: 40, 80, 108, 142 nm)
   → We know their size, we measure their scatter signal
   → This gives us "k" (the instrument constant that converts AU to physics units)
   → k = 969.5 for our CytoFLEX nano (VSSC1-H channel at 405nm)

Step 2: SIGNAL CONVERSION
   For each EV event: σ_sca = AU_measured / k
   (Raw signal in arbitrary units → physical scattering cross-section in nm²)

Step 3: INVERSE MIE LOOKUP
   We have a pre-computed table: "if a particle is X nm, it scatters Y nm²"
   We flip it: "this event scattered Y nm², so it must be X nm"

Step 4: DUAL-WAVELENGTH DISAMBIGUATION (the clever bit)
   Problem: Mie theory is wavy — one scatter value can match 2-3 different sizes
   Solution: We use TWO channels — Violet SSC (405nm) + Blue SSC (488nm)
   → Find all candidate sizes from violet
   → Check which candidate also matches the violet/blue ratio
   → Pick the one that's consistent across both wavelengths
```

### What Changed Recently (Key Fixes)

| What | Before | After | Why It Matters |
|------|--------|-------|----------------|
| **Mie physics** | Used Q_back (180° backscatter only) | Uses Q_sca (total scatter) | Q_back was wrong for SSC detectors — they collect wide-angle light, not just backscatter |
| **Refractive index handling** | Relative RI (m = n_particle/n_medium) | Absolute RI with explicit n_env | Was double-counting the medium correction — sizes were wrong |
| **Solution method** | Single-solution (pick closest match) | Multi-solution with dual-wavelength | Old method picked wrong size ~30% of the time due to Mie resonances |
| **Primary wavelength** | Blue 488nm | Violet 405nm | Violet gives ~2× better sensitivity for small EVs (Rayleigh scattering ∝ λ⁻⁴) |
| **Calibration** | No bead calibration | Full FCMPASS-style k-factor from nanoViS beads | Without k, we were using heuristic normalization (guessing) |
| **Cross-validation** | Didn't exist | Full FCS vs NTA comparison with statistics | Can now directly compare our Mie-calculated sizes against NTA measurements |

### Bead Calibration Accuracy (This Is Working Well)

We validated our Mie model against known bead sizes:

| Bead Size | What We Calculated | Error |
|-----------|-------------------|-------|
| 80 nm | 79.4 nm | 0.7% |
| 108 nm | 109.0 nm | 0.9% |
| 142 nm | 141.7 nm | 0.2% |

**Max error: under 1%.** The physics and math are solid — when we know the material (polystyrene beads, RI = 1.634 at 405nm), the model recovers the correct size almost perfectly.

---

## Part 2: What Are We Getting? (Cross-Validation Results)

### FCS vs NTA Comparison — PC3 Exosomes

We ran PC3 EXO1 through our pipeline and compared against NTA:

| Metric | FCS (Our Mie) | NTA (Direct Measurement) | Difference |
|--------|---------------|--------------------------|------------|
| D10 | 65 nm | 82.5 nm | −21% |
| **D50** | **81 nm** | **127.5 nm** | **−44.6%** |
| D90 | 129 nm | 217.5 nm | −51% |

**Important caveat:** These are NOT the same sample:
- **FCS:** "PC3 EXO1" — bulk, unfractionated
- **NTA:** "PC3_100kDa_F5" — went through 100kDa ultrafiltration + SEC Fraction 5

The NTA sample was further purified, which removes small particles and enriches for larger ones. This is likely the **biggest single reason** for the gap. No unfractionated NTA measurement exists for a true apples-to-apples comparison.

### What the Platform UI Shows Now

The Cross-Compare tab now produces:
- Overlay histogram (FCS vs NTA distributions side by side)
- D50 comparison with percentage difference
- Validation verdict (PASS / ACCEPTABLE / WARNING / FAIL)
- Statistical tests (KS test, Mann-Whitney, Bhattacharyya overlap)
- Exportable PDF/CSV reports

This matches our E2E test results — the UI is producing the same numbers as the command-line validation.

---

## Part 3: The Error Sensitivity Scale (What Parvesh Asked About)

### The Key Insight: RI Is Everything

We ran a full sensitivity analysis. The refractive index (RI) assumption for EVs is the **single biggest knob** that changes the output:

```
If researcher sets n_EV = 1.35  →  D50 = 105 nm
If researcher sets n_EV = 1.37  →  D50 = 81 nm   ← current default
If researcher sets n_EV = 1.39  →  D50 = 70 nm
If researcher sets n_EV = 1.40  →  D50 = 66 nm
```

**Each 0.02 change in RI shifts D50 by 15-25%.** That's huge.

Meanwhile, the k-factor (calibration constant) barely matters:

```
k = 940.6  →  D50 = 82 nm
k = 969.5  →  D50 = 81 nm   (only 1 nm difference!)
```

### Proposed Error Margin Framework

The idea from Parvesh is: **don't absorb researchers' errors — quantify and show them.** Here's how we can present it:

#### Tier 1: Platform Calibration Error (What WE Control)
These are errors from our physics and calibration. We've validated these:

| Source | Error Magnitude | Status |
|--------|----------------|--------|
| Mie physics implementation | < 1% | ✅ Validated against beads |
| k-factor calibration | ≈ 3% (k CV) | ✅ Validated, impact ~1 nm |
| Multi-solution disambiguation | < 2% | ✅ 96% of events unambiguous |
| Lookup table resolution | < 1 nm | ✅ 1 nm step size |
| **Total platform error** | **≈ 3-5%** | **This is our uncertainty floor** |

#### Tier 2: Researcher-Controlled Parameters (What THEY Control)
These are inputs the researcher provides that dramatically affect output:

| Parameter | If Wrong By | D50 Changes By | Severity |
|-----------|-------------|-----------------|----------|
| **Refractive Index (n_EV)** | ±0.02 | ±15-25% | 🔴 CRITICAL |
| **Refractive Index (n_EV)** | ±0.05 | ±30-50% | 🔴 CRITICAL |
| Medium RI (n_medium) | ±0.01 | ±5-8% | 🟡 MODERATE |
| Bead RI (calibration) | ±0.02 | ±3-5% | 🟢 LOW (we use known value) |

#### Tier 3: Experimental Factors (Sample Prep & Instrument)
Things outside both our and the model's control:

| Factor | Potential Impact | Notes |
|--------|-----------------|-------|
| Sample fractionation | 20-40% size shift | Different prep = different population |
| NTA vs FCS detection limits | 10-20% D50 bias | NTA can't see below ~50-70nm |
| Hydrodynamic vs physical dia. | 5-15% | NTA measures hydrated size |
| Detector collection angles | Unknown (need Surya) | See Part 4 below |

### What This Means for the User

We should show something like this in the UI:

> **Confidence Statement:**  
> "Platform calibration error: ±5%. Your result accuracy depends critically on input parameters — particularly the EV refractive index (default: 1.37). A ±0.02 RI error propagates to ±15-25% size error. Verify your RI assumption matches your sample type."

The philosophy: **We give guidance, we don't hide errors.** If a researcher uses wrong inputs, we tell them the error will accumulate. It's their responsibility to check their experiment. Our job is to make the uncertainty **visible and quantifiable**.

---

## Part 4: What We Need From Surya

### Question 1: SSC Collection Angles for CytoFLEX nano

**The Problem:**  
Our Mie model currently computes Q_sca — the **total** scattering efficiency integrated over all angles (full 4π sphere). But the actual SSC detector on the CytoFLEX nano only collects light within a specific angular range.

```
Current assumption: SSC signal ∝ total scatter (all angles)
Reality:            SSC signal ∝ scatter within detector angular window only
```

For small particles (< 100 nm), this doesn't matter much — their scattering is nearly isotropic (goes in all directions equally). But for larger particles, the scatter pattern becomes very directional (forward-peaked), and the fraction of light hitting the SSC detector changes with size.

**What we need to know:**
- What is the SSC collection angle range on the CytoFLEX nano? (e.g., 15°–150°? or something else?)
- Is it different for violet SSC (VSSC) vs blue SSC (BSSC)?
- Does Beckman Coulter publish the optical geometry specs?

**How would we use it:**  
If we know the angular range, we can compute angle-resolved Mie scattering (integrate only over the detector angles) instead of total Q_sca. This would give a more accurate k-factor and could shift our size estimates by a few percent, especially for particles > 100 nm.

### Question 2: EV Refractive Index Guidance

- What RI should we recommend for PC3 exosomes specifically?
- Literature range for EVs is 1.35–1.45 — but our specific PC3 samples might be different
- Is there a way to independently measure RI? (e.g., CFSE labeling + scatter matching?)
- At n = 1.35, our D50 jumps to 105 nm (much closer to NTA range)

### Question 3: Is 44.6% Discrepancy Expected?

Given that:
- The FCS sample is unfractionated, the NTA sample is fractionated (100kDa + SEC F5)
- NTA has a detection floor that misses small particles
- Literature reports 15-40% FC-NTA discrepancies (Gardiner et al., 2013)

Is this result within the expected range, or should we aim for matching samples first before concluding anything about Mie accuracy?

---

## Part 5: Summary — What's Working, What's Next

### ✅ Working Well
- Mie physics validated to < 1% on calibration beads
- Multi-solution dual-wavelength sizing (96% events with unique solution)
- FCMPASS-style bead calibration (k = 969.5, CV = 3.9%)
- Full cross-validation pipeline (FCS vs NTA comparison with statistics)
- UI showing same results as E2E tests
- Export to PDF/CSV/Excel

### 🔄 In Progress
- Error margin / sensitivity display in the UI
- Documenting the RI sensitivity for researchers

### ❓ Need Input On
- CytoFLEX nano SSC collection angles (from Surya / Beckman Coulter specs)
- Recommended RI for PC3 exosomes
- Whether to run matching samples (same prep → FCS + NTA) for proper validation
- Core-shell Mie model — is it worth implementing for more accurate size-dependent RI?

### 📊 Key Numbers to Remember

| Thing | Number | Meaning |
|-------|--------|---------|
| k_instrument | 969.5 | Our calibration constant (VSSC1-H channel) |
| Bead accuracy | < 1% | Our physics model works for known materials |
| FCS D50 | 81 nm | What our pipeline says for PC3 EXO1 |
| NTA D50 | 127.5 nm | What NTA says for PC3_100kDa_F5 (different prep!) |
| RI sensitivity | ±15-25% per 0.02 RI change | The dominant source of sizing uncertainty |
| Platform error floor | ~3-5% | What we control and have validated |

---

*This document is meant as a conversation guide. The full technical analysis with appendices is in `docs/FCS_NTA_CROSS_VALIDATION_ANALYSIS.md`.*
