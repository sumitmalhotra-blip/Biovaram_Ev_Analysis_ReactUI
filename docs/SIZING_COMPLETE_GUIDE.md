# EV Sizing: Complete Technical Guide
## How Particle Sizing Works, What's Broken, and How to Fix It

**Date:** February 16, 2026  
**For:** Development Team  
**Status:** Living Document — covers physics, architecture, bugs, and roadmap  

---

## Table of Contents

1. [The Fundamental Problem: What Does a Flow Cytometer Actually Measure?](#1-what-does-a-flow-cytometer-measure)
2. [Why Beads Are Needed — And What They Actually Do](#2-why-beads-are-needed)
3. [The AU → nm Conversion: Step by Step with Real Numbers](#3-au-to-nm-conversion)
4. [What's Currently Broken in Our Code](#4-whats-broken)
5. [Different Bead Kits, Different Instruments — How to Handle Them All](#5-different-beads-and-instruments)
6. [Current System: What Exists Today](#6-current-system)
7. [What's Missing: Gaps in the Current System](#7-whats-missing)
8. [Architecture for a Flexible, Future-Proof System](#8-future-proof-architecture)
9. [How to Test If the Code Is Working Correctly](#9-how-to-test)
10. [Implementation Roadmap](#10-roadmap)
11. [Glossary](#11-glossary)

---

## 1. What Does a Flow Cytometer Actually Measure? <a name="1-what-does-a-flow-cytometer-measure"></a>

A flow cytometer does **NOT** measure particle size directly. Here's what actually happens:

```
Particle enters laser beam
        ↓
Laser light hits particle → light scatters in all directions
        ↓
Detectors at specific angles collect scattered light:
  • FSC detector (forward, ~0-10°) → related to size
  • SSC detectors (side, ~90°) → related to size + internal complexity
  • VSSC (405nm violet laser)
  • BSSC (488nm blue laser)
  • YSSC (561nm yellow laser)
  • RSSC (638nm red laser)
        ↓
Photodetector converts photons → electrical signal
        ↓
ADC converts electrical signal → digital number (ARBITRARY UNITS)
        ↓
Stored in FCS file as: "VSSC1-H = 15,247"
```

### The Key Insight

That number **15,247** depends on:

| Factor | Effect |
|--------|--------|
| Particle size | Larger → more scatter |
| Particle refractive index (RI) | Higher RI contrast → more scatter |
| Laser power | More power → more photons → higher number |
| Detector gain | Higher gain → amplifies signal → higher number |
| Optical alignment | Better alignment → more photons collected |
| Collection angle | Different angles → different scattering physics |
| ADC resolution | 16-bit vs 20-bit → different numeric range |
| Wavelength | Different λ → different Mie resonances |

**The SAME 100nm EV will give DIFFERENT AU values on:**
- Different instruments (Beckman CytoFLEX vs BD FACSymphony)
- The same instrument on different days (if laser degrades)
- The same instrument with different gain settings

**This is why you cannot just take the AU number and convert it to nm.** You need a calibration reference — something with a KNOWN size — to establish the mapping between AU and physical scatter cross-section.

---

## 2. Why Beads Are Needed — And What They Actually Do <a name="2-why-beads-are-needed"></a>

### Common Misconception

> "Beads are just for QC — to check if the machine is working"

**This is partially true but misses the critical point.** Beads serve TWO purposes:

### Purpose 1: Quality Control (QC) ✅
- Run beads periodically
- Check if peak positions are stable over time
- If peaks shift → laser degrading, alignment off, PMT aging
- This is what most labs use beads for

### Purpose 2: Instrument Calibration (Sizing) ✅
- Run beads with KNOWN sizes and KNOWN refractive index
- Measure their scatter in AU
- Use Mie theory to calculate their THEORETICAL scatter cross-section (in nm²)
- Fit a curve: AU = f(nm²)
- This curve IS the calibration — it converts arbitrary units to physics
- **This is what we need for accurate EV sizing**

### The Two-Step Process Explained Simply

```
STEP 1: "Teach the machine" (done once per instrument/settings)
═══════════════════════════════════════════════════════════════

  You know:  Bead is 100nm, RI = 1.591
  Mie theory says: 100nm bead at 405nm → σ_back = 251.4 nm²
  Machine says:    VSSC1-H = 35,000 AU

  You know:  Bead is 200nm, RI = 1.591  
  Mie theory says: 200nm bead at 405nm → σ_back = 103.1 nm²
  Machine says:    VSSC1-H = 14,800 AU

  ... (repeat for all bead sizes) ...

  FIT: You now have a curve that says:
       35,000 AU → 251.4 nm²
       14,800 AU → 103.1 nm²
       etc.

  This curve converts ANY AU value to physical scatter cross-section.


STEP 2: "Size the EVs" (done for every sample)
═══════════════════════════════════════════════

  Machine says:    EV particle VSSC1-H = 8,500 AU
  
  Calibration curve (from Step 1): 8,500 AU → 47.3 nm²

  Now use Mie theory with EV RI (1.40, NOT bead RI!):
  "What EV diameter gives σ_back = 47.3 nm² at 405nm?"
  Answer: ~95 nm

  THAT is the correct EV diameter.
```

### Why You Can't Skip the Beads

If you skip Step 1 (no bead calibration), you're stuck with AU values. The code currently tries two workarounds, both wrong:

| Method | What It Does | Why It Fails |
|--------|-------------|-------------|
| Direct bead cal | Fits `FSC = a × d^b` using bead RI, applies to EVs | Uses bead RI for EV sizing — wrong physics (bead scatter ≠ EV scatter for same size) |
| Percentile normalization | Maps P5→P95 of AU to physical scatter range | Makes sizes RELATIVE (D50 always ≈ middle of range), not absolute |
| Multi-Mie (current) | Compares theoretical nm² directly to AU values | nm² and AU are completely different scales — apples to oranges |

---

## 3. The AU → nm Conversion: Step by Step with Real Numbers <a name="3-au-to-nm-conversion"></a>

Let me walk through the complete process with actual data from your instrument.

### Step 1: Theoretical Mie Scatter for Beads

Using `miepython` with bead parameters (RI=1.591, medium=1.33, λ=405nm):

| Bead Size (nm) | Qback | Geometric Area (nm²) | σ_back = Qback × Area (nm²) |
|:-:|:-:|:-:|:-:|
| 40 | 0.000460 | 1,257 | **0.578** |
| 80 | 0.004619 | 5,027 | **23.22** |
| 108 | 0.009065 | 9,161 | **83.04** |
| 142 | 0.011029 | 15,837 | **174.67** |
| 304 | 0.006266 | 72,583 | **454.81** |
| 600 | 0.000350 | 282,743 | **98.83** |
| 1020 | 0.007188 | 817,283 | **5,873.43** |

> **Notice:** σ_back is NOT monotonically increasing with diameter! The 600nm bead has LESS backscatter than the 304nm bead at 405nm. This is because of Mie resonances — the scattering efficiency oscillates. This non-monotonicity is exactly why single-solution approaches fail and why the multi-solution approach was invented.

### Step 2: Get AU Values from Bead FCS File

When you run Nano Vis Low beads through the CytoFLEX nano, you get a histogram with 4 peaks. Each peak corresponds to one bead size. The peak position (median AU) is what the machine "says" that bead size scatters at.

For example (these are hypothetical — we need to actually extract them):
```
40nm bead peak:  VSSC1-H median ≈ 450 AU
80nm bead peak:  VSSC1-H median ≈ 2,800 AU
108nm bead peak: VSSC1-H median ≈ 8,200 AU
142nm bead peak: VSSC1-H median ≈ 18,500 AU
```

### Step 3: Build Calibration Curve

Now you have pairs: (AU, σ_back in nm²)

```
(450 AU,    0.578 nm²)
(2800 AU,   23.22 nm²)
(8200 AU,   83.04 nm²)
(18500 AU,  174.67 nm²)
```

Fit a polynomial or power law: `σ_back = f(AU)`

This is your **instrument transfer function**. It's specific to:
- This instrument (CytoFLEX nano BH46064)
- These settings (VSSC1 gain=100)
- This wavelength (405nm)

### Step 4: Apply to EV Sample

```
EV particle measured at VSSC1-H = 5,000 AU

Step 4a: AU → σ_back using calibration curve
  σ_back = f(5000) = 45.2 nm²  (hypothetical)

Step 4b: σ_back → EV diameter using Mie theory with EV RI
  Using n_particle=1.40, n_medium=1.33, λ=405nm:
  Search for diameter where Mie_σ_back(d) = 45.2 nm²
  
  Answer: d ≈ 93 nm  ← THIS is the EV diameter
```

### Why This Is Different from Direct Bead Calibration

Direct bead calibration says: "This AU value came from a 80nm bead, so this AU = 80nm."

But that's wrong for EVs because a 80nm EV scatters DIFFERENTLY than a 80nm bead:

| Particle | Size | RI | σ_back @405nm |
|----------|------|----|---------------|
| Polystyrene bead | 80nm | 1.591 | 23.22 nm² |
| EV | 80nm | 1.40 | 95.97 nm² |

An 80nm EV scatters ~4x MORE than an 80nm bead at 405nm (in the backscatter direction). So if you apply a bead calibration curve directly, you get wildly wrong answers.

> **Important note on the scatter comparison:** The reason EVs scatter MORE than beads per same size at 405nm backscatter is a Mie resonance effect at these specific parameters. This is NOT intuitive ("shouldn't higher RI = more scatter?") — Mie scattering is highly non-linear and depends on the size parameter x = πd/λ and the specific angular collection geometry. Different wavelengths and angles can reverse this relationship. This is precisely why you need Mie theory rather than simple assumptions.

---

## 4. What's Currently Broken in Our Code <a name="4-whats-broken"></a>

### Bug 1: Multi-Solution Mie — Scale Mismatch

**File:** `backend/src/physics/mie_scatter.py`, `find_all_solutions()` method (line ~907)

**What happens:**
```python
# LUT built from Mie theory → values in nm² (0.5 to 5,000)
self.lut_ssc_violet[i] = self._calc_ssc(d, WAVELENGTH_VIOLET)

# But target_ssc comes from FCS file → values in AU (500 to 260,000)
for i, (d, ssc) in enumerate(zip(self.lut_diameters, lut_ssc)):
    if abs(ssc - target_ssc) <= tolerance:  # COMPARING nm² TO AU!
```

**Result:** For any VSSC AU value above ~4,000, there are ZERO matches in the LUT, so the result is NaN. The few events that accidentally fall in the LUT range get random garbage sizes.

Validation script output:
```
  VSSC (AU)   Solutions   Size (nm)
        500          7       116.0      ← accidental match, wrong
       1000          5       314.0      ← accidental match, wrong
       5000          0         NaN      ← no match (AU >> LUT range)
      10000          0         NaN
     100000          0         NaN
```

### Bug 2: Single-Solution Mie — Arbitrary Normalization

**File:** `backend/src/physics/mie_scatter.py`, `diameters_from_scatter_normalized()` (line ~560)

**What happens:**
```python
# Maps the P5-P95 range of raw data to the physical FSC range
raw_p5, raw_p95 = np.percentile(raw_fsc_valid, [5, 95])
phys_min, phys_max = physical_fsc_unique[0], physical_fsc_unique[-1]
normalized_fsc = phys_min + (fsc - raw_p5) / (raw_p95 - raw_p5) * (phys_max - phys_min)
```

**Result:** The size distribution is entirely **relative**. The D50 is always approximately the middle of the LUT range (30-500nm → D50 ≈ 150nm), regardless of what the actual particle sizes are. It cannot distinguish a sample of 50nm EVs from a sample of 300nm EVs.

### Bug 3: Direct Bead Calibration — Wrong RI

**File:** `backend/src/physics/bead_calibration.py`, `diameter_from_fsc()` (line ~669)

**What happens:**
```python
# Fits: FSC = a * d^b  (using bead sizes and their AU values)
# Then inverts: d = (FSC/a)^(1/b)
# BUT: this assumes the sample has the SAME RI as beads (1.591)
# EVs have RI = 1.40 → completely different scatter-to-size relationship
```

**Result:** Gives D50 ≈ 42nm for PC3 100kDa EVs (should be ~152nm). Factor of ~3.6× too small.

### Bug 4: FCMPASSCalibrator Exists But Never Used

**File:** `backend/src/physics/mie_scatter.py`, lines 1130-1442

The `FCMPASSCalibrator` class actually does the correct thing — it:
1. Takes bead measurements (known size → measured AU)
2. Calculates theoretical Mie scatter for beads (known RI)
3. Fits polynomial: AU → theoretical Mie scatter
4. For unknown particles: AU → calibrated scatter → inverse Mie → diameter

But this class is **never imported or called** by any API endpoint. It sits unused.

---

## 5. Different Bead Kits, Different Instruments — How to Handle Them All <a name="5-different-beads-and-instruments"></a>

### What Changes Between Experiments

| What | Can Change? | Impact on Calibration |
|------|------------|----------------------|
| **Bead kit** | Yes — Beckman nanoViS, Thermo APC, Spherotech, NIST SRM | Different sizes, different RI, different CV |
| **Bead RI** | Yes — Polystyrene=1.59, Silica=1.46, Melamine=1.68 | Changes Mie calculation completely |
| **Bead sizes** | Yes — each kit has different size set | Different calibration points |
| **Instrument** | Yes — CytoFLEX, FACSymphony, ZE5, etc. | Different detectors, different gain ranges |
| **Gain settings** | Yes — user adjusts per experiment | Scales AU values, must recalibrate |
| **Laser wavelength** | Usually fixed per instrument | Determines which Mie table to use |
| **Sample RI** | Yes — EVs=1.37-1.45, lipid nanoparticles=1.47 | Changes Step 2 of the sizing |
| **Medium RI** | Usually 1.33 (PBS) but can vary | Affects Mie calculation |

### Current System Limitations

Right now, the system:

1. **Only ships with nanoViS D03231** — one bead kit JSON in `config/bead_standards/`
2. **Hard-codes bead RI = 1.591** — no way to specify silica beads
3. **Has no concept of "instrument profiles"** — each gain setting needs its own calibration but there's only a single `active_calibration.json`
4. **Cannot store multiple calibrations** — one active calibration for all samples
5. **Doesn't validate bead/sample gain match** — if beads were run at gain=100 but sample at gain=150, calibration is invalid
6. **No UI to add custom bead kits** — user must manually create JSON files

### What a Real Lab Scenario Looks Like

```
Week 1:
  Monday:    Run nanoViS Low beads → calibrate
  Monday:    Run PC3 EVs at gain=100 → size using Monday's calibration
  Wednesday: Run PC3 EVs at gain=100 → SAME calibration is fine
  
Week 2:
  Monday:    Adjusted gain to 150 (better signal) → MUST recalibrate
  Monday:    Run nanoViS Low beads at new gain → NEW calibration
  Monday:    Run HEK293 EVs at gain=150 → use new calibration

Different lab:
  Uses Spherotech NIST-traceable beads (different sizes, different RI)
  Uses BD FACSymphony (completely different instrument)
  Needs: custom bead datasheet JSON + new calibration
```

### How Other Labs Use Different Beads

Common bead kits in the EV field:

| Kit | Manufacturer | Sizes (nm) | Material | RI |
|-----|-------------|-----------|----------|-----|
| nanoViS D03231 | Beckman Coulter | 40, 80, 108, 142, 304, 600, 1020 | Polystyrene | 1.591 |
| MegaMix-Plus FSC | Stain Buffer | 100, 160, 240, 500, 900 | Polystyrene/PMMA | ~1.59 |
| Apogee Mix | Apogee Flow | 110, 180, 240, 300, 500, 590, 880, 1300 | Silica/Polystyrene | 1.43/1.59 |
| Spherotech NIST | Spherotech | custom sizes | Polystyrene | ~1.59 |
| FCMPASS reference | Various | user-defined | Any | User-specified |

Each of these needs its own JSON datasheet with: sizes, RI, CVs, material.

---

## 6. Current System: What Exists Today <a name="6-current-system"></a>

### Backend Components

| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| `BeadDatasheet` class | `bead_calibration.py:60` | Load bead JSON config | ✅ Works |
| `list_available_bead_standards()` | `bead_calibration.py:131` | Scan `config/bead_standards/` | ✅ Works |
| `detect_bead_peaks()` | `bead_calibration.py:189` | KDE peak detection in scatter histograms | ⚠️ Untested with real data |
| `match_peaks_to_beads()` | `bead_calibration.py:303` | Match peaks to known sizes | ⚠️ Order-based (fragile) |
| `BeadCalibrationCurve` class | `bead_calibration.py:400+` | Power law / poly fit | ❌ Wrong approach (direct sizing) |
| `calibrate_from_bead_fcs()` | `bead_calibration.py:909` | Full auto pipeline | ❌ Uses wrong approach |
| `FCMPASSCalibrator` class | `mie_scatter.py:1130` | Correct AU→σ→diameter pipeline | ✅ Exists but ❌ Not connected |
| `MultiSolutionMieCalculator` | `mie_scatter.py:772` | Dual-wavelength sizing | ❌ Scale mismatch bug |
| `MieScatterCalculator` | `mie_scatter.py:80` | Single-wavelength Mie | ⚠️ Works mathematically but not calibrated |

### API Endpoints

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `GET /calibration/bead-standards` | List bead kits from config | ✅ Works |
| `GET /calibration/status` | Active calibration status | ✅ Works |
| `GET /calibration/active` | Full calibration details | ✅ Works |
| `POST /calibration/fit` | Auto-fit from bead FCS | ❌ Uses wrong approach |
| `POST /calibration/fit-manual` | Manual bead points | ❌ Uses wrong approach |
| `DELETE /calibration/active` | Remove calibration | ✅ Works |
| Missing: Upload custom bead datasheet | - | ❌ Does not exist |
| Missing: Select EV RI for sizing | - | ❌ Not exposed |

### Frontend Components

| Component | Location | What It Does | Status |
|-----------|----------|-------------|--------|
| `BeadCalibrationPanel` | `bead-calibration-panel.tsx` | Full calibration UI (auto + manual) | ✅ UI works, ❌ backend logic wrong |
| `AnalysisSettingsPanel` | `analysis-settings-panel.tsx` | Has RI dropdown (1.37-1.59) | ✅ Exists but ❌ not used for FCMPASS |
| Sidebar calibration badge | `sidebar.tsx:579` | Shows calibration status | ✅ Works |

### Config Files

| File | Location | Content | Status |
|------|----------|---------|--------|
| `nanovis_d03231.json` | `config/bead_standards/` | All 7 nanoViS bead sizes | ✅ Complete |
| `active_calibration.json` | `config/calibration/` | Current calibration | ❌ Currently removed |
| `channel_config.json` | `config/` | Channel definitions | ✅ Works |

---

## 7. What's Missing: Gaps in the Current System <a name="7-whats-missing"></a>

### Gap 1: No Way to Add Custom Bead Kits

**Problem:** Only nanoViS D03231 is available. If a user has Apogee Mix or Spherotech beads, they can't use the system.

**Solution needed:** 
- API endpoint: `POST /calibration/bead-standards/upload` — accept JSON file
- UI: "Add Custom Bead Kit" button with form fields (or JSON file upload)
- Validation: check required fields (sizes, RI, material)

### Gap 2: No FCMPASS-Style Calibration in the Pipeline

**Problem:** The calibration pipeline does `AU → diameter` directly (wrong). It should do `AU → σ → diameter` (correct).

**Solution needed:**
- Wire `FCMPASSCalibrator` into the calibration endpoints
- The calibration curve should map AU → σ_back (in nm²), NOT AU → diameter
- The sizing step should use Mie theory with EV RI (1.40) to convert σ → diameter

### Gap 3: No Multi-Calibration Support

**Problem:** Only one `active_calibration.json` exists. Different gain settings or instruments need different calibrations.

**Solution needed:**
- Store calibrations with metadata (instrument, gain settings, date, bead kit used)
- Allow multiple saved calibrations
- Auto-match calibration to sample based on instrument/gain metadata from FCS file
- UI to select which calibration to use per sample

### Gap 4: Gain/Settings Validation

**Problem:** If beads were run at gain=100 and sample at gain=150, the calibration is invalid. Nothing warns the user.

**Solution needed:**
- Extract gain settings from both bead FCS and sample FCS metadata
- Compare and warn if they don't match
- Store expected gain settings in calibration metadata

### Gap 5: EV RI Selection Not Connected to Sizing

**Problem:** The `AnalysisSettingsPanel` has an RI dropdown (1.37-1.45 for EVs, 1.50 for silica, 1.59 for beads) but it's only used for Mie calculations, not for the FCMPASS pipeline.

**Solution needed:**
- Pass user-selected EV RI through to the sizing step
- Different EVs have different RIs (exosomes ~1.37, microvesicles ~1.40, apoptotic bodies ~1.42)
- Store EV RI assumption with each analysis result

### Gap 6: No Bead Self-Validation

**Problem:** After calibration, there's no check that the calibration actually works.

**Solution needed:**
- After fitting calibration, size the bead file THROUGH the full pipeline
- Check if recovered sizes match datasheet sizes within CVs
- Report: "40nm bead → recovered 42.3nm (within 11.5% CV ✅)"
- Reject calibration if any bead is >2× CV away from expected

---

## 8. Architecture for a Flexible, Future-Proof System <a name="8-future-proof-architecture"></a>

### Proposed System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ Bead Kit Manager │  │ Calibration Panel│  │ Sample Analysis  │  │
│  │                  │  │                  │  │                  │  │
│  │ • List kits      │  │ • Upload bead FCS│  │ • Upload FCS     │  │
│  │ • Add custom kit │  │ • Select kit     │  │ • Select RI      │  │
│  │ • Edit/delete    │  │ • Auto/manual fit│  │ • View sizes     │  │
│  │ • View datasheet │  │ • Validate cal   │  │ • Compare NTA    │  │
│  │                  │  │ • Save/load cals │  │                  │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
│           │                     │                     │             │
├───────────┼─────────────────────┼─────────────────────┼─────────────┤
│           │              API LAYER                    │             │
│           ▼                     ▼                     ▼             │
│  GET /bead-standards     POST /calibration/fit   POST /samples/    │
│  POST /bead-standards    GET /calibrations       ...scatter-data   │
│  DELETE /bead-standards  PUT /calibrations/:id                     │
│                          POST /calibration/                        │
│                               validate                             │
├─────────────────────────────────────────────────────────────────────┤
│                        PHYSICS LAYER                                │
│                                                                     │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │ Mie Theory   │  │ FCMPASS          │  │ Multi-Solution       │  │
│  │ Engine       │  │ Calibrator       │  │ Mie Calculator       │  │
│  │              │  │                  │  │ (+ calibration)      │  │
│  │ miepython    │  │ Step 1: AU → σ   │  │                      │  │
│  │ Q_ext, Q_sca │  │ Step 2: σ → d    │  │ Uses CALIBRATED σ    │  │
│  │ Q_back, g    │  │ (with EV RI)     │  │ not raw AU           │  │
│  └──────────────┘  └──────────────────┘  └──────────────────────┘  │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                        DATA LAYER                                   │
│                                                                     │
│  config/bead_standards/        config/calibrations/                 │
│  ├── nanovis_d03231.json       ├── cal_20260216_gain100.json       │
│  ├── megamix_plus.json         ├── cal_20260216_gain150.json       │
│  ├── apogee_mix.json           └── active_calibration.json         │
│  └── custom_user_kit.json          (symlink → current active)      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow: Full Corrected Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                    COMPLETE SIZING PIPELINE                          │
│                                                                     │
│   CALIBRATION PHASE (done once per instrument/gain/experiment)      │
│   ════════════════════════════════════════════════════════════       │
│                                                                     │
│   INPUT: Bead FCS file + Bead datasheet JSON                       │
│                                                                     │
│   1. Load bead datasheet                                            │
│      └─ Sizes: [40, 80, 108, 142, 304, 600, 1020] nm              │
│      └─ Bead RI: 1.591 (polystyrene)                               │
│      └─ CVs: [11.5, 6.9, 5.2, 3.8, 4.9, 2.2, 2.6] %              │
│                                                                     │
│   2. Parse bead FCS → detect peaks → get AU values                 │
│      └─ Peak 1: 450 AU   (matches 40nm bead)                      │
│      └─ Peak 2: 2,800 AU (matches 80nm bead)                      │
│      └─ Peak 3: 8,200 AU (matches 108nm bead)                     │
│      └─ ... etc                                                     │
│                                                                     │
│   3. For each bead, calculate theoretical Mie scatter               │
│      └─ Mie(d=40, RI=1.591, λ=405, medium=1.33) → σ = 0.578 nm²  │
│      └─ Mie(d=80, RI=1.591, λ=405, medium=1.33) → σ = 23.22 nm²  │
│      └─ ... etc                                                     │
│                                                                     │
│   4. FIT: measured_AU → theoretical_σ  (polynomial or power law)   │
│      └─ This IS the calibration curve                               │
│      └─ Stored as: coefficients + metadata                         │
│                                                                     │
│   5. VALIDATE: Size the beads themselves through full pipeline     │
│      └─ 40nm bead → pipeline → 42.3nm? Within 11.5% CV? ✅        │
│      └─ 80nm bead → pipeline → 78.1nm? Within 6.9% CV? ✅         │
│      └─ Report quality metrics                                     │
│                                                                     │
│                                                                     │
│   SIZING PHASE (done for every EV sample)                          │
│   ═══════════════════════════════════════                           │
│                                                                     │
│   INPUT: Sample FCS file + Active calibration + EV RI assumption   │
│                                                                     │
│   6. Read VSSC1-H values from sample FCS (in AU)                  │
│                                                                     │
│   7. Apply calibration: AU → σ_back (nm²)                         │
│      └─ Uses polynomial from Step 4                                │
│                                                                     │
│   8. Find EV diameter via Mie theory:                              │
│      └─ For each event, find d where:                               │
│         Mie(d, RI=1.40, λ=405, medium=1.33).σ_back = σ_calibrated │
│      └─ If multi-solution: use VSSC/BSSC ratio to disambiguate    │
│                                                                     │
│   9. OUTPUT: Array of EV diameters (nm)                            │
│      └─ Calculate D10, D50, D90                                    │
│      └─ Compare with NTA if available                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Bead Kit JSON Schema (for any bead kit)

Any bead kit that a user wants to add must follow this schema:

```json
{
  "kit_part_number": "REQUIRED - manufacturer part number",
  "product_name": "REQUIRED - human-readable name",
  "lot_number": "REQUIRED - for traceability",
  "manufacturer": "REQUIRED",
  "material": "polystyrene_latex | silica | melamine | pmma",
  "refractive_index": 1.591,
  "ri_measurement_wavelength_nm": 590,
  "nist_traceable": true,
  "expiration_date": "2026-08-14",
  
  "subcomponents": {
    "mix_name_1": {
      "description": "Human-readable description",
      "beads": [
        {
          "label": "100nm",
          "diameter_nm": 100,
          "cv_pct": 5.0,
          "concentration_particles_per_ml": 1e8,
          "spec_min_um": 0.095,
          "spec_max_um": 0.105
        }
      ]
    }
  },
  
  "unique_bead_diameters_nm": [100, 200, 300]
}
```

### How a User Adds a Custom Bead Kit

**Option A: JSON file upload (for advanced users)**
1. Create JSON following the schema above
2. Upload via new API endpoint: `POST /calibration/bead-standards`
3. File saved to `config/bead_standards/`
4. Immediately available in kit dropdown

**Option B: Form-based entry (for everyone)**
1. Click "Add Custom Bead Kit" in UI
2. Fill in: manufacturer, material, RI, number of beads
3. For each bead: diameter, CV%, concentration
4. System generates and saves JSON
5. Available in kit dropdown

**Option C: Pre-loaded popular kits**
Ship with JSON files for common kits:
- nanoViS D03231 (already exists)
- MegaMix-Plus FSC
- Apogee Mix (silica + polystyrene)
- Spherotech NIST-traceable

---

## 9. How to Test If the Code Is Working Correctly <a name="9-how-to-test"></a>

### Test 1: Bead Self-Consistency (Most Important)

**What:** Run bead FCS file through the full pipeline and check if you get the datasheet sizes back.

**How:**
```
1. Upload Nano Vis Low.fcs
2. Calibrate using nanoViS D03231 datasheet
3. Now size the SAME bead file through the pipeline
4. Check results:
   - 40nm bead peak → should give ~40nm (±11.5% CV = 35-46nm)
   - 80nm bead peak → should give ~80nm (±6.9% CV = 74-86nm)
   - 108nm bead peak → should give ~108nm (±5.2% CV = 102-114nm)
   - 142nm bead peak → should give ~142nm (±3.8% CV = 137-147nm)
```

**Pass criteria:** All recovered sizes within 2× the datasheet CV of the known size.

### Test 2: NTA Cross-Validation

**What:** Compare FC-derived sizes against NTA ground truth for the same sample.

**How:**
```
1. Calibrate with beads (if not already done)
2. Upload PC3 EXO1.fcs (a PC3 100kDa sample)
3. Get FC-derived size distribution: D10, D50, D90
4. Compare with NTA data from backend/NTA/PC3/:
   - NTA D50 ≈ 151.7nm (from ZetaView measurements)
   - NTA D10 ≈ 100-110nm
   - NTA D90 ≈ 200-220nm
```

**Pass criteria:** FC D50 within ±30% of NTA D50 (i.e., 106-197nm).

> **Note:** Perfect agreement isn't expected. FC and NTA measure different physical properties (scatter vs Brownian motion), and there's inherent selection bias in flow cytometry (small particles below detection threshold are missed). A ±20-30% agreement is considered excellent in the field.

### Test 3: Known Size Sensitivity

**What:** Check that the system can distinguish different-sized samples.

**How:**
```
1. Using SAME calibration:
   - Size a Nano Vis Low bead file → D50 should be ~100nm
   - Size a Nano Vis High bead file → D50 should be ~400nm
   - Size a PC3 EXO sample → D50 should be ~150nm
2. All three should give DIFFERENT D50 values
3. If they're all similar → normalization is still forcing relative sizing
```

### Test 4: Gain Sensitivity Check

**What:** Verify that the same sample gives the same size with different gain calibrations.

**How:**
```
1. If you have bead files at two different gains:
   - Calibrate with gain=100 beads
   - Size a sample (VSSC1-H values at gain=100)
   - Calibrate with gain=150 beads (if available)
   - Size the same sample at gain=150
   → Both should give similar D50 (within 10%)
```

### Test 5: Validation Script

Run the previously created script:
```powershell
cd backend
python validate_sizing.py
```

This checks:
- Mie theory calculations for multiple RIs
- Current multi-solution Mie behavior (shows the scale mismatch)
- Bead peak detection on FCS files
- What corrected pipeline should produce

### Test 6: Manual Sanity Check

Calculate a single particle by hand to verify:
```python
import miepython
import numpy as np

# For a 150nm EV at 405nm in PBS
d = 150  # nm
ri_ev = 1.40
ri_medium = 1.33
wavelength = 405  # nm

m = complex(ri_ev / ri_medium, 0)
qext, qsca, qback, g = miepython.efficiencies(m, d, wavelength, n_env=ri_medium)

sigma_back = qback * np.pi * (d/2)**2  # nm²
print(f"150nm EV at 405nm:")
print(f"  Qback = {qback:.6f}")
print(f"  σ_back = {sigma_back:.2f} nm²")
print(f"  This is the scatter cross-section the pipeline should recover")
```

---

## 10. Implementation Roadmap <a name="10-roadmap"></a>

### Phase 1: Fix the Core Sizing (Highest Priority)

**Goal:** Make the multi-solution Mie calculator produce correct sizes.

| Task | Description | Effort |
|------|-------------|--------|
| 1.1 | Add calibration step to `MultiSolutionMieCalculator`: accept a `calibration_curve` function that converts AU → σ | Medium |
| 1.2 | Wire `FCMPASSCalibrator.predict_diameter()` into the sizing pipeline | Medium |
| 1.3 | Modify `calibrate_from_bead_fcs()` to fit AU → σ_back (not AU → diameter) | Medium |
| 1.4 | Update sizing priority cascade in `samples.py`: remove direct bead cal, use FCMPASS | Medium |
| 1.5 | Run validation tests (bead self-consistency, NTA comparison) | Low |

### Phase 2: Add Custom Bead Kit Support

**Goal:** Let users upload any bead kit datasheet.

| Task | Description | Effort |
|------|-------------|--------|
| 2.1 | Add `POST /calibration/bead-standards` endpoint (upload JSON) | Low |
| 2.2 | Add JSON schema validation for bead datasheets | Low |
| 2.3 | Add "Add Custom Bead Kit" button to UI with form | Medium |
| 2.4 | Ship pre-loaded JSON for MegaMix-Plus, Apogee Mix | Low |
| 2.5 | Add `DELETE /calibration/bead-standards/:name` | Low |

### Phase 3: Multi-Calibration Management

**Goal:** Support different calibrations for different instruments/settings.

| Task | Description | Effort |
|------|-------------|--------|
| 3.1 | Store calibrations with metadata (instrument, gain, date, bead kit) | Medium |
| 3.2 | `GET /calibrations` — list all saved calibrations | Low |
| 3.3 | `PUT /calibrations/:id/activate` — switch active calibration | Low |
| 3.4 | Auto-detect gain from FCS metadata, warn on mismatch | Medium |
| 3.5 | UI: Calibration Library page | High |

### Phase 4: Robustness & Validation

**Goal:** Make the system reliable and self-checking.

| Task | Description | Effort |
|------|-------------|--------|
| 4.1 | Bead self-validation after calibration (size beads, check vs datasheet) | Medium |
| 4.2 | Gain mismatch warnings | Medium |
| 4.3 | Calibration expiry alerts (bead lots expire) | Low |
| 4.4 | NTA comparison endpoint (upload NTA + FCS, compute agreement) | High |
| 4.5 | Uncertainty propagation (report size ± error) | High |

---

## 11. Glossary <a name="11-glossary"></a>

| Term | Meaning |
|------|---------|
| **AU** | Arbitrary Units — the raw digital number from a flow cytometer detector |
| **Qback** | Backscatter efficiency — dimensionless Mie theory output (0-4 typical) |
| **σ_back** | Backscatter cross-section = Qback × geometric area (in nm²) — physical quantity |
| **RI** | Refractive Index — how much light bends in a material. Higher RI → more contrast → more scatter (generally) |
| **FSC** | Forward Scatter — detector at 0-10° angle, mainly measures size |
| **SSC / VSSC / BSSC** | Side Scatter — detectors at ~90° angle, at specific laser wavelengths |
| **Mie theory** | Exact electromagnetic theory for scattering by spheres — computes Q_ext, Q_sca, Q_back, g |
| **LUT** | Lookup Table — pre-computed array mapping diameter → scatter or vice versa |
| **FCMPASS** | Flow Cytometry Mie-based Particle Axis Standardization Software — published method for correct FC sizing |
| **NTA** | Nanoparticle Tracking Analysis — measures size via Brownian motion, independent of RI |
| **D50** | Median diameter of size distribution (50th percentile) |
| **CV** | Coefficient of Variation — std/mean × 100%, measures peak width |
| **KDE** | Kernel Density Estimation — smooth histogram for peak finding |
| **Non-monotonic** | Not always increasing — Mie scatter oscillates, so one scatter value → multiple possible sizes |
| **Power law** | Mathematical function: y = a × x^b — used for FSC-size relationships |
| **Transfer function** | The mapping between what the detector measures (AU) and physical reality (nm²) |
| **Calibration curve** | The fitted transfer function — converts AU to physical scatter cross-section |

---

## Appendix A: Quick Reference — When to Recalibrate

| Event | Need to Recalibrate? | Why |
|-------|---------------------|-----|
| Changed detector gain | **YES** | AU values change proportionally |
| Changed laser power | **YES** | AU values change proportionally |
| Different instrument | **YES** | Completely different transfer function |
| New bead lot (same kit) | Recommended | Slight size differences between lots |
| Different day, same settings | Only if QC fails | Should be stable if settings locked |
| Different sample type (EVs → lipid NPs) | **NO** (cal is same) | But change the sample RI parameter |
| Different medium (PBS → culture media) | **YES** if RI differs | Affects Mie calculation |

## Appendix B: Refractive Index Reference

| Material | RI | Use Case |
|----------|----|----------|
| PBS (medium) | 1.33 | Default medium |
| Water | 1.33 | Same as PBS |
| Cell culture media | 1.335-1.34 | Slight difference from PBS |
| Exosomes (small EVs) | 1.37-1.40 | Most small EVs |
| Microvesicles | 1.38-1.42 | Larger EVs |
| Apoptotic bodies | 1.40-1.45 | Largest EVs |
| Lipid nanoparticles | 1.45-1.48 | Synthetic particles |
| Silica beads | 1.43-1.46 | Calibration beads |
| Polystyrene beads | 1.59 | Most common calibration beads |
| Melamine beads | 1.68 | High-RI calibration beads |

## Appendix C: Files Referenced in This Document

| File | Purpose |
|------|---------|
| `backend/src/physics/mie_scatter.py` | Mie theory calculations, MultiSolutionMieCalculator, FCMPASSCalibrator |
| `backend/src/physics/bead_calibration.py` | Bead datasheet loading, peak detection, calibration fitting |
| `backend/src/api/routers/calibration.py` | API endpoints for calibration |
| `backend/src/api/routers/samples.py` | Sample upload/analysis endpoints (uses calibration) |
| `backend/config/bead_standards/nanovis_d03231.json` | nanoViS bead datasheet |
| `backend/config/calibration/active_calibration.json` | Active calibration (when set) |
| `components/flow-cytometry/bead-calibration-panel.tsx` | Frontend calibration UI |
| `components/flow-cytometry/analysis-settings-panel.tsx` | RI selection dropdown |
| `lib/api-client.ts` | Frontend API client (calibration methods) |
| `backend/validate_sizing.py` | Validation script |
| `backend/nanoFACS/Nano Vis Low.fcs` | Bead FCS file (40, 80, 108, 142nm) |
| `backend/nanoFACS/Nano Vis High.fcs` | Bead FCS file (142, 304, 600, 1020nm) |

---

*Last updated: February 16, 2026*
