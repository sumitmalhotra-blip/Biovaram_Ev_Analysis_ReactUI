# Sizing Calibration Implementation Plan

## Reference: `docs/SIZING_COMPLETE_GUIDE.md`

---

## Problem Summary

Three sizing methods exist — all three are broken:

| Method | Bug | Impact |
|--------|-----|--------|
| Multi-solution Mie | AU vs nm² scale mismatch | ~80% events → NaN |
| Single-solution Mie | P5–P95 percentile normalization | Relative sizes only |
| Direct bead calibration | Bead RI applied to EVs | 3.6× error (42nm vs 152nm) |

**The fix**: FCMPASS-style calibration that decouples bead RI from EV RI.

---

## Correct Physics Pipeline (FCMPASS Approach)

```
Step 1 — Bead Calibration (bead RI = 1.591):
  For each bead size dᵢ:
    σ_theory(dᵢ) = Qback(dᵢ, RI=1.591, λ) × π(dᵢ/2)²   [Mie theory, nm²]
    AU_measured(dᵢ) = peak mean from bead FCS                [instrument units]
  Fit:  AU → σ_theory  (polynomial or power law in log-log space)
  Result: Transfer function  f(AU) → σ_back  [nm²]

Step 2 — Sample Sizing (EV RI = 1.40):
  For each EV event:
    σ_calibrated = f(AU_measured)           [nm² from Step 1]
    d_EV = inverse_Mie(σ_calibrated, RI=1.40, λ)  [diameter in nm]
  Result: True EV diameter accounting for correct RI
```

---

## Implementation Phases

### Phase 1: Backend Scripts (standalone, testable)

| Script | Purpose | Validates |
|--------|---------|-----------|
| `step1_extract_bead_peaks.py` | Parse bead FCS, detect peaks, extract AU values | Peak detection works, correct #peaks found |
| `step2_build_calibration.py` | Build AU→σ transfer function using FCMPASS | Transfer function is physically correct |
| `step3_size_ev_samples.py` | Apply calibration to PC3 EXO samples | D50 ≈ 127–152nm (matching NTA) |
| `step4_validate_results.py` | Self-consistency checks + NTA comparison | All validations pass |

### Phase 2: Integration (only after Phase 1 succeeds)
- Wire FCMPASSCalibrator into `calibration.py` router
- Fix MultiSolutionMieCalculator to accept calibrated σ values
- Update `samples.py` sizing cascade
- Update frontend bead-calibration-panel

---

## Script Details

### Script 1: `step1_extract_bead_peaks.py`
- Load `nanoFACS/Nano Vis Low.fcs` (4 beads: 40, 80, 108, 142 nm)
- Load `nanoFACS/Nano Vis High.fcs` (4 beads: 142, 304, 600, 1020 nm)
- Channels: `VSSC1-H` (405nm) and `BSSC-H` (488nm)
- Detect 4 peaks per file using KDE + find_peaks
- Output: `{diameter_nm: mean_AU}` for each channel
- Validation: Check we get exactly 4 peaks per file, ordered sensibly

### Script 2: `step2_build_calibration.py`
- Input: bead peak AU values from Script 1
- For each bead size, compute Mie theory σ_back (RI=1.591, λ=405nm and 488nm)
- Fit polynomial: log10(AU) → log10(σ_back)
- Output: Calibration coefficients, R², residuals plot
- Validation: R² > 0.99; residuals < 5%

### Script 3: `step3_size_ev_samples.py`
- Load a PC3 EXO FCS file from `data/uploads/`
- Apply calibration from Script 2: AU → σ → diameter
- Use EV RI = 1.40 for inverse Mie
- Compute D10, D50, D90 statistics
- Reference: NTA D50 ≈ 127nm (Number), 152nm (approx)
- Validation: D50 within 20% of NTA value

### Script 4: `step4_validate_results.py`
- Bead self-consistency: calibrate with beads, then "size" beads → should recover known diameters
- Cross-wavelength: calibrate at 405nm, verify 488nm gives same sizes
- Compare to NTA distribution shape (mode, width)
- Sensitivity analysis: vary EV RI from 1.37 to 1.45, show range

---

## Success Criteria

1. **Bead peaks detected correctly** — 4 peaks per file, ordered by diameter
2. **Calibration R² > 0.99** — AU→σ fit is excellent
3. **Bead self-consistency < 5%** — sizing beads recovers known diameters within 5%
4. **EV D50 matches NTA within 20%** — FC D50 vs NTA D50 ≈ 127-152nm
5. **No NaN events** — calibrated pipeline produces valid sizes for >95% of events

---

## Key Constants

| Parameter | Value | Source |
|-----------|-------|--------|
| Bead RI | 1.591 @ 590nm | nanoViS D03231 datasheet |
| EV RI | 1.40 | Literature consensus (Welsh 2020) |
| Medium RI | 1.33 | PBS (sheath fluid) |
| Violet laser λ | 405 nm | CytoFLEX nano spec |
| Blue laser λ | 488 nm | CytoFLEX nano spec |
| VSSC1-H gain | 100 | FCS metadata |
| BSSC-H gain | 70 | FCS metadata |
| NTA D50 (Number) | 127.3 nm | ZetaView F5 measurement |
| Bead sizes (Low) | 40, 80, 108, 142 nm | Datasheet |
| Bead sizes (High) | 142, 304, 600, 1020 nm | Datasheet |
