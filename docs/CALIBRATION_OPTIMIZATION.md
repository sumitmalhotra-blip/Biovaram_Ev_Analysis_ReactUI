# Mie Theory Optimization via Bead-Based Instrument Calibration

## CAL-001: Production-Grade Calibration System

**Document Version:** 1.0  
**Date:** February 10, 2026  
**Author:** CRMIT Backend Team  
**Status:** Implemented

---

## 1. Executive Summary

This document describes how we optimize extracellular vesicle (EV) sizing on the BioVaram EV Analysis Platform by introducing **bead-based instrument calibration**. This bridges the gap between theoretical Mie scattering models and the practical realities of cytometer optics, resulting in substantially more accurate particle size determinations.

---

## 2. Previous Approach (Raw Mie Theory)

### 2.1 How It Worked

The original sizing pipeline converted raw SSC (side scatter) intensity values directly into particle diameter using a single-solution Mie theory lookup:

```
Raw SSC → Mie theory inversion (n_particle = 1.40) → Diameter (nm)
```

The system computed Mie scattering cross-sections for a range of diameters (30–220 nm), built a lookup table, and used interpolation to map each event's SSC value to a diameter.

### 2.2 Key Assumptions

| Assumption | Reality |
|------------|---------|
| Instrument SSC is proportional to theoretical Mie scattering cross-section | Not true—each instrument has unique detector gains, optical path losses, collection angle variations |
| n_particle = 1.40 for all EVs | Reasonable average, but varies by EV subtype (1.36–1.45) |
| SSC integration from 85°–95° | Actual collection angles vary by instrument model |
| Size range 30–220 nm only | nanoFACS detects particles beyond this range |

### 2.3 Problems Observed

- **D50 = 337 nm** reported for certain EV samples—physically unreasonable for the expected exosome population
- No way to verify whether the instrument was producing consistent sizing over time
- No connection between raw arbitrary scatter units and any NIST-traceable standard
- No accounting for instrument-to-instrument variation
- Hard-coded parameters ignored user settings during upload analysis

---

## 3. New Approach (Bead-Calibrated Transfer Function)

### 3.1 Core Concept

Instead of assuming raw SSC maps directly to Mie theory predictions, we introduce an **instrument transfer function** that maps measured scatter to Mie-predicted scatter using reference bead standards of known size and refractive index.

```
                    BEAD CALIBRATION PHASE
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  Polystyrene Beads (known d, known RI = 1.591)          │
│         ↓                                               │
│  Run through instrument → Record SSC values             │
│         ↓                                               │
│  For each bead size:                                    │
│    measured_SSC ←→ Mie_theory_predict(d, RI=1.591)      │
│         ↓                                               │
│  Fit transfer function: SSC_meas = a × SSC_Mie^b       │
│                                                         │
└─────────────────────────────────────────────────────────┘

                    SAMPLE ANALYSIS PHASE
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  Unknown EV particle → measured SSC                     │
│         ↓                                               │
│  Transfer function → calibrated_SSC_Mie                 │
│         ↓                                               │
│  Inverse Mie theory (RI = 1.40) → Diameter (nm)        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Why This Works

The transfer function **absorbs all instrument-specific effects** in one mapping:

- Detector quantum efficiency & gain settings
- Optical path efficiency (lenses, mirrors, fiber coupling)
- Collection angle geometry vs. theoretical integration angles
- Signal digitization non-linearities
- Day-to-day instrument drift

Because we calibrate with beads of **known diameter** and **known RI** (NIST-traceable, TEM-measured), the transfer function is anchored to physical reality.

### 3.3 Mathematical Details

**Step 1: Bead Data Collection**

For each bead size $d_i$ (i = 1..N), we measure the mean SSC intensity $\overline{S}_i$ from the instrument.

**Step 2: Mie Theory Prediction**

For each bead, compute the theoretical Mie SSC cross-section:

$$\sigma_{\text{Mie}}(d_i) = \int_{\theta_1}^{\theta_2} \left| S_1(\theta, d_i, n_{\text{bead}}, n_{\text{medium}}, \lambda) \right|^2 + \left| S_2(\theta, d_i, n_{\text{bead}}, n_{\text{medium}}, \lambda) \right|^2 \, d\theta$$

where $n_{\text{bead}} = 1.591$, $n_{\text{medium}} = 1.34$, $\lambda = 405$ nm.

**Step 3: Transfer Function Fit**

Fit a power-law in log-log space:

$$\overline{S}_{\text{measured}} = a \cdot \sigma_{\text{Mie}}^b$$

or equivalently: $\log(\overline{S}) = \log(a) + b \cdot \log(\sigma_{\text{Mie}})$

The fit parameters $a$ and $b$ capture all instrument-specific scaling and non-linearity.

**Step 4: EV Sizing**

For an unknown EV with measured scatter $S$:

1. Invert the transfer function: $\sigma_{\text{calibrated}} = (S / a)^{1/b}$
2. Look up the diameter from the EV Mie table (using RI = 1.40): $d = \text{Mie}^{-1}(\sigma_{\text{calibrated}}, n_{\text{EV}} = 1.40)$

---

## 4. Bead Standards Used

### 4.1 Beckman Coulter nanoViS D03231

| Property | Value |
|----------|-------|
| Part Number | D03231 |
| Lot Number | 4894789 |
| Material | Polystyrene latex |
| Refractive Index | 1.591 at 590 nm, 20°C |
| Sizing Method | Transmission Electron Microscopy (TEM) |
| Traceability | NIST SRM 1963a, SRM 1964 |
| Expiration | 2027-09-15 |

### 4.2 Bead Populations

| Sub-Kit | Label | Diameter (nm) | CV (%) |
|---------|-------|---------------|--------|
| nanoViS Low | Bead 1 | 44 (TEM: 40 nm) | 14.0 |
| nanoViS Low | Bead 2 | 80 | 8.0 |
| nanoViS Low | Bead 3 | 105 (TEM: 108 nm) | 7.0 |
| nanoViS Low | Bead 4 | 144 (TEM: 142 nm) | 5.0 |
| nanoViS High | Bead 5 | 144 (TEM: 142 nm) | 5.0 |
| nanoViS High | Bead 6 | 300 (TEM: 304 nm) | 3.0 |
| nanoViS High | Bead 7 | 600 | 3.0 |
| nanoViS High | Bead 8 | 1000 (TEM: 1020 nm) | 3.0 |

**Unique calibration diameters:** 40, 80, 108, 142, 304, 600, 1020 nm (7 points)

This provides calibration coverage from the small exosome range (40 nm) through microvesicles (1020 nm), spanning the full EV size spectrum.

---

## 5. Implementation Architecture

### 5.1 Three-Tier Sizing Priority

The system now uses a priority cascade for size estimation:

| Priority | Method | When Used |
|----------|--------|-----------|
| 1 (Highest) | Bead-calibrated transfer function | Active calibration exists and is fitted |
| 2 | Multi-solution Mie with VSSC/BSSC ratio | Two scatter channels available, no calibration |
| 3 (Fallback) | Single-solution Mie theory | One scatter channel only |

### 5.2 Backend Components

| Component | File | Purpose |
|-----------|------|---------|
| Bead Datasheet Loader | `bead_calibration.py` | Parse manufacturer JSON datasheets |
| Peak Detection | `bead_calibration.py` | Auto-detect bead populations via KDE + find_peaks |
| Calibration Curve | `bead_calibration.py` | Fit & store transfer function |
| Calibration Router | `calibration.py` | REST API (6 endpoints) |
| Upload Pipeline | `upload.py` | Calibrated sizing path during analysis |
| Scatter Re-analysis | `samples.py` | Apply calibration to existing samples |
| Size Config | `size_config.py` | Extended range: 20–1100 nm |

### 5.3 Frontend Components

| Component | File | Purpose |
|-----------|------|---------|
| Bead Calibration Panel | `bead-calibration-panel.tsx` | Auto-fit, manual entry, curve visualization |
| Sidebar Badge | `sidebar.tsx` | Quick-glance calibration status (R², kit, beads) |
| API Client | `api-client.ts` | TypeScript interfaces & methods for calibration |

### 5.4 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/calibration/status` | Calibration status for sidebar badge |
| GET | `/api/v1/calibration/bead-standards` | List available bead kit datasheets |
| GET | `/api/v1/calibration/active` | Full calibration data + curve for chart |
| POST | `/api/v1/calibration/fit` | Auto-fit from bead FCS file |
| POST | `/api/v1/calibration/fit-manual` | Fit from manually entered scatter values |
| DELETE | `/api/v1/calibration/active` | Remove calibration (archives it) |

---

## 6. Automatic Peak Detection

### 6.1 Algorithm

When a bead FCS file is uploaded for calibration, the system automatically identifies bead populations:

1. **Log-space KDE**: Transform all SSC values to log₁₀ space and compute a Kernel Density Estimate (Gaussian kernel, bandwidth 0.05 in log space)
2. **Gaussian smoothing**: Smooth the KDE with σ = 3 points to reduce noise
3. **Peak finding**: Use `scipy.signal.find_peaks` with configurable minimum distance between peaks (0.15 in log₁₀ space)
4. **Peak ranking**: Sort by KDE height, select top N peaks (matching the number of expected bead sizes from the datasheet)
5. **Peak region extraction**: For each peak, collect events within ±0.1 log₁₀ units, compute mean and standard deviation
6. **Ordered matching**: Sort detected peaks by scatter intensity (ascending), match to datasheet diameters (ascending) — smallest scatter ↔ smallest bead

### 6.2 Why Log-Space?

Scatter intensity spans several orders of magnitude across bead sizes (40 nm → 1020 nm). In linear space, large-bead peaks dominate and small-bead peaks are invisible. Log-space normalizes the visual scale and enables KDE to find peaks at all sizes equally well.

---

## 7. Expected Improvements

### 7.1 Before Calibration

| Metric | Value | Problem |
|--------|-------|---------|
| D50 (typical EV sample) | 337 nm | Too high for exosomes |
| Size range | 30–220 nm | Missing large EVs/MVs |
| Traceability | None | No reference standard connection |
| Reproducibility | Unknown | No instrument drift detection |

### 7.2 After Calibration

| Metric | Expected Value | Improvement |
|--------|----------------|-------------|
| D50 (typical EV sample) | 80–150 nm | Matches expected exosome range |
| Size range | 20–1100 nm | Full EV spectrum coverage |
| Traceability | NIST SRM 1963a/1964 | International standard anchored |
| Reproducibility | ±5% (recalibrate to confirm) | Detectable via R² tracking |
| R² of calibration | >0.99 (typical for polystyrene beads) | High-confidence transfer function |

### 7.3 Key Accuracy Gains

1. **Instrument absorption**: Transfer function compensates for all optical path effects, not just theoretical Mie computation
2. **Extended range**: Calibration from 40–1020 nm covers exosomes through large microvesicles
3. **Per-instrument customization**: Each instrument gets its own transfer function; no more one-size-fits-all Mie lookup
4. **Drift monitoring**: Re-running bead calibration periodically detects instrument drift via R² changes
5. **Reproducibility**: Two labs with the same bead kit will converge to comparable sizing results

---

## 8. Workflow

### 8.1 Initial Calibration Setup

```
1. Upload bead FCS file (e.g., "Nano Vis High.fcs")
2. Open Flow Cytometry tab → Bead Calibration Panel → Expand
3. Select bead kit: "nanovis_d03231.json"
4. Select bead sample from uploaded samples
5. Choose scatter channel (default: VSSC1-H)
6. Click "Auto-Fit from FCS"
7. System auto-detects peaks → matches to beads → fits curve → saves active calibration
8. Sidebar badge turns green: "Calibrated | R²=0.9998 | 7 beads"
```

### 8.2 Ongoing Use

Once calibrated, **all subsequent FCS uploads automatically use the calibration** — no user action needed. The upload pipeline checks for an active calibration before falling back to raw Mie.

### 8.3 Manual Mode

If automatic peak detection fails (e.g., noisy data, unusual instrument settings), users can enter bead scatter means manually:

1. Gate bead populations in FlowJo or CytoFLEX software
2. Record mean SSC for each bead size
3. Enter values in the Manual Bead Data Entry form
4. Click "Fit Manual Calibration"

---

## 9. Configuration Files

### 9.1 Bead Datasheet JSON

Location: `backend/config/bead_standards/nanovis_d03231.json`

Structured JSON containing all manufacturer data: part numbers, lot numbers, individual bead specifications (diameter, CV, concentration), NIST traceability info.

### 9.2 Active Calibration JSON

Location: `backend/config/calibration/active_calibration.json`

Saved after fitting, contains:
- Transfer function parameters (a, b, R²)
- All bead point data (diameters, scatter means/stds, n_events)
- Instrument name, wavelength, fit method
- Bead kit reference info
- Timestamp and version

### 9.3 Calibration Archives

When an active calibration is replaced or removed, the previous one is archived (not deleted):
- `calibration_removed_20260210_143000.json`
- `calibration_superseded_20260215_091500.json`

This provides full audit trail for regulatory compliance.

---

## 10. Comparison Summary

| Aspect | Previous (Raw Mie) | Current (Bead-Calibrated) |
|--------|--------------------|-----------------------|
| Sizing Method | SSC → lookup table | SSC → transfer function → calibrated scatter → lookup |
| RI Used | 1.40 (hardcoded) | 1.591 for calibration, 1.40 for EV measurement |
| Range | 30–220 nm | 20–1,100 nm |
| Traceability | None | NIST SRM via polystyrene bead standards |
| Instrument Specific | No | Yes — per-instrument transfer function |
| Peak Detection | N/A | Automatic KDE + peak finding in log space |
| User Interface | None | Full calibration panel + sidebar status badge |
| API Endpoints | 0 | 6 dedicated calibration endpoints |
| Drift Detection | Not possible | Compare R² over time |
| Fallback | Single Mie only | 3-tier: Bead-cal → Multi-Mie → Single-Mie |

---

## 11. Technical References

1. Bohren, C.F. & Huffman, D.R., *Absorption and Scattering of Light by Small Particles*, Wiley (1983)
2. van der Pol, E. et al., "Particle size distribution of exosomes and microvesicles determined by transmission electron microscopy, flow cytometry, nanoparticle tracking analysis, and resistive pulse sensing," *J. Thromb. Haemost.* 12, 1182–1192 (2014)
3. Welsh, J.A. et al., "MIFlowCyt-EV: Minimal information framework for flow cytometry of extracellular vesicles," *Cytometry A* 97, 149–158 (2020)
4. Beckman Coulter, "nanoViS Reference Standards — Lot Datasheet D03231"
5. ISEV 2023 Position Paper on EV Characterization Standards

---

*This document accompanies the CAL-001 implementation in the BioVaram EV Analysis Platform.*
