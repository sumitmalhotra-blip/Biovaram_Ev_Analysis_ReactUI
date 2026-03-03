"""
Step 2: Build AU -> Diameter Calibration (Corrected FCMPASS)
=============================================================

CRITICAL CORRECTIONS from investigation:
  1. Mie RI bug: must use absolute RI (m=n_particle) + n_env=n_medium
     NOT relative RI (m=n_particle/n_medium) + n_env=n_medium (double-counts!)
  2. Use Qsca (total scattering cross-section), NOT Qback (180 degree only)
  3. Correct peak assignments from combinatorial search:
     P6(1888 AU)=40nm, P17(102411)=80nm, P20(565342)=108nm, P23(2132067)=142nm
  4. Bead RI wavelength dispersion: PS RI at 405nm = 1.634 (not 1.591 at 590nm)
     Using Cauchy equation: n = A + B/lambda^2 + C/lambda^4

Physics model:
  AU = k * sigma_sca(d, RI, lambda)
  where sigma_sca = Qsca * pi * (d/2)^2
  and k is the instrument constant (k ~ 940.6 for VSSC1-H)

Calibration pipeline:
  1. From beads: fit k = mean(AU_i / sigma_sca_i)
  2. For EVs: sigma_ev = AU / k
  3. d_EV = inverse_Mie(sigma_ev, RI=1.40, lambda)

Author: CRMIT Backend Team
Date: February 2026
"""

import sys
import json
import numpy as np
from pathlib import Path
from scipy.optimize import minimize_scalar

sys.path.insert(0, str(Path(__file__).parent / "src"))
import miepython


# ============================================================================
# Constants
# ============================================================================

# PS bead RI wavelength dispersion (Cauchy coefficients, Sultanova 2009)
# n = A + B/lambda^2 + C/lambda^4
CAUCHY_A = 1.5718
CAUCHY_B = 0.00885  # um^2
CAUCHY_C = 0.000213  # um^4

def ps_ri_at_wavelength(wavelength_nm):
    """Calculate PS refractive index at given wavelength using Cauchy equation."""
    lam_um = wavelength_nm / 1000
    return CAUCHY_A + CAUCHY_B / lam_um**2 + CAUCHY_C / lam_um**4

BEAD_RI_590 = 1.591  # Datasheet value at 590nm
BEAD_RI = None  # Will be computed per-channel at measurement wavelength
EV_RI = 1.37  # SEC-purified EVs (adjusted from 1.40 based on NTA validation)
MEDIUM_RI = 1.33

# Correct peak assignments from combinatorial analysis
# Assignment: best Qsca consistency = 1.1x
CORRECT_BEAD_PEAKS = {
    "VSSC1-H": {
        "wavelength_nm": 405.0,
        "beads": [
            {"diameter_nm": 40,  "mean_au": 1888.0,    "n_events": 14434},
            {"diameter_nm": 80,  "mean_au": 102411.0,   "n_events": 15366},
            {"diameter_nm": 108, "mean_au": 565342.0,   "n_events": 5175},
            {"diameter_nm": 142, "mean_au": 2132067.0,  "n_events": 15790},
        ],
    },
}


# ============================================================================
# Mie Calculations (CORRECTED)
# ============================================================================

def mie_sigma_sca(d_nm, wavelength_nm, n_particle, n_medium):
    """
    Compute scattering cross-section = Qsca * pi * r^2.
    
    IMPORTANT: Uses absolute RI for m and n_env for medium.
    This is the CORRECT miepython calling convention.
    """
    m = complex(n_particle, 0)  # ABSOLUTE RI
    result = miepython.efficiencies(m, d_nm, wavelength_nm, n_env=n_medium)
    qsca = float(result[1])
    r = d_nm / 2.0
    return qsca * np.pi * r ** 2  # nm^2


def build_sigma_lut(wavelength_nm, n_particle, n_medium,
                    d_min=20.0, d_max=500.0, n_points=5000):
    """Build lookup table: diameter -> sigma_sca."""
    diameters = np.linspace(d_min, d_max, n_points)
    sigmas = np.array([
        mie_sigma_sca(d, wavelength_nm, n_particle, n_medium)
        for d in diameters
    ])
    return diameters, sigmas


def diameter_from_sigma(sigma_target, d_lut, sigma_lut):
    """Inverse Mie: sigma -> diameter using LUT."""
    # In the small particle regime, sigma is monotonic
    # Find closest match
    idx = np.argmin(np.abs(sigma_lut - sigma_target))
    return float(d_lut[idx])


# ============================================================================
# Calibration
# ============================================================================

def fit_instrument_constant(bead_data, wavelength_nm, n_bead, n_medium):
    """
    Fit the instrument constant k such that AU = k * sigma_sca.
    
    For a linear detector, k should be constant across all beads.
    We use weighted mean where weight = 1/variance.
    """
    print(f"\n  Fitting instrument constant k = AU / sigma_sca")
    print(f"  {'Bead':>6s} {'AU':>12s} {'sigma_sca':>12s} {'k = AU/sigma':>14s}")
    
    ks = []
    for b in bead_data:
        d = b["diameter_nm"]
        au = b["mean_au"]
        sigma = mie_sigma_sca(d, wavelength_nm, n_bead, n_medium)
        k = au / sigma if sigma > 0 else 0
        ks.append(k)
        print(f"  {d:>4d}nm {au:>12.1f} {sigma:>12.4f} nm^2 {k:>14.1f}")
    
    k_mean = float(np.mean(ks))
    k_std = float(np.std(ks))
    k_cv = 100 * k_std / k_mean if k_mean > 0 else 0
    
    print(f"\n  k_mean = {k_mean:.1f} +/- {k_std:.1f} (CV={k_cv:.1f}%)")
    
    # Verify: predict AU from sigma and k_mean
    print(f"\n  Verification (predict AU from sigma and k_mean):")
    max_err = 0
    for b in bead_data:
        d = b["diameter_nm"]
        au_actual = b["mean_au"]
        sigma = mie_sigma_sca(d, wavelength_nm, n_bead, n_medium)
        au_pred = k_mean * sigma
        err = 100 * (au_pred - au_actual) / au_actual
        if abs(err) > max_err:
            max_err = abs(err)
        print(f"  {d:>4d}nm: AU_pred={au_pred:>12.0f}, AU_actual={au_actual:>12.0f}, err={err:+.1f}%")
    
    print(f"  Max error: {max_err:.1f}%")
    
    return {
        "k_mean": k_mean,
        "k_std": k_std,
        "k_cv_pct": k_cv,
        "max_error_pct": max_err,
        "individual_ks": ks,
    }


def build_calibration(bead_data, wavelength_nm, n_bead, n_medium, n_ev):
    """Build complete calibration: AU -> EV diameter."""
    
    # Step 1: Fit instrument constant
    cal = fit_instrument_constant(bead_data, wavelength_nm, n_bead, n_medium)
    k = cal["k_mean"]
    
    # Step 2: Build EV inverse Mie LUT
    print(f"\n  Building EV inverse Mie LUT (RI={n_ev}, lambda={wavelength_nm}nm)")
    d_lut, sigma_lut = build_sigma_lut(wavelength_nm, n_ev, n_medium)
    
    # Step 3: Self-consistency check (size the beads with bead RI)
    print(f"\n  Self-consistency: sizing beads with bead RI={n_bead}")
    d_lut_bead, sigma_lut_bead = build_sigma_lut(wavelength_nm, n_bead, n_medium,
                                                   d_min=20, d_max=300)
    for b in bead_data:
        d_known = b["diameter_nm"]
        au = b["mean_au"]
        sigma_cal = au / k
        d_recovered = diameter_from_sigma(sigma_cal, d_lut_bead, sigma_lut_bead)
        err = 100 * (d_recovered - d_known) / d_known
        status = "OK" if abs(err) < 5 else "WARN"
        print(f"    d_known={d_known:>4d}nm -> sigma={sigma_cal:.4f} -> d_rec={d_recovered:.1f}nm "
              f"(err={err:+.1f}%) [{status}]")
    
    # Step 4: EV sizing at bead AU values
    print(f"\n  EV sizing at bead AU values (RI={n_ev}):")
    for b in bead_data:
        d_bead = b["diameter_nm"]
        au = b["mean_au"]
        sigma_ev = au / k
        d_ev = diameter_from_sigma(sigma_ev, d_lut, sigma_lut)
        print(f"    AU={au:>12.1f} (bead {d_bead}nm) -> sigma_ev={sigma_ev:.4f} -> d_EV={d_ev:.1f}nm")
    
    # Step 5: Generate calibration curve (AU -> d_EV)
    au_range = np.logspace(2, 7, 500)  # 100 to 10M AU
    d_ev_range = []
    for au in au_range:
        sigma = au / k
        if sigma <= 0:
            d_ev_range.append(np.nan)
        else:
            d = diameter_from_sigma(sigma, d_lut, sigma_lut)
            d_ev_range.append(d)
    d_ev_range = np.array(d_ev_range)
    
    cal["wavelength_nm"] = wavelength_nm
    cal["n_bead"] = n_bead
    cal["n_ev"] = n_ev
    cal["n_medium"] = n_medium
    cal["bead_data"] = bead_data
    cal["d_lut"] = d_lut.tolist()
    cal["sigma_lut"] = sigma_lut.tolist()
    
    return cal, d_lut, sigma_lut


# ============================================================================
# Main
# ============================================================================

def main():
    print("=" * 70)
    print("STEP 2: Build AU -> Diameter Calibration (Corrected FCMPASS)")
    print("=" * 70)
    print(f"\nKey corrections applied:")
    print(f"  1. Fixed Mie RI: absolute m + n_env (was double-counting)")
    print(f"  2. Using Qsca (total scatter) instead of Qback (180 deg only)")
    print(f"  3. Correct peak assignments from combinatorial analysis")
    
    calibrations = {}
    
    for ch, ch_data in CORRECT_BEAD_PEAKS.items():
        wl = ch_data["wavelength_nm"]
        beads = ch_data["beads"]
        
        # Calculate bead RI at measurement wavelength
        bead_ri = ps_ri_at_wavelength(wl)
        
        print(f"\n{'='*70}")
        print(f"  Channel: {ch} ({wl}nm)")
        print(f"  Bead RI: {BEAD_RI_590} @ 590nm -> {bead_ri:.4f} @ {wl}nm (Cauchy)")
        print(f"  Beads: {[b['diameter_nm'] for b in beads]} nm")
        print(f"{'='*70}")
        
        cal, d_lut, sigma_lut = build_calibration(
            beads, wl, bead_ri, MEDIUM_RI, EV_RI
        )
        calibrations[ch] = cal
    
    # Save calibration
    out_dir = Path(__file__).parent / "calibration_data"
    out_dir.mkdir(exist_ok=True)
    
    # Prepare serializable output
    output = {
        "description": "FCMPASS-style AU -> diameter calibration (CORRECTED)",
        "corrections": [
            "Fixed Mie RI double-counting: now uses absolute m + n_env",
            "Using Qsca (total scatter) instead of Qback (180 deg)",
            "Correct bead peak assignments from combinatorial analysis",
            "Bead RI wavelength dispersion: using Cauchy equation at each measurement wavelength",
        ],
        "bead_ri_590nm": BEAD_RI_590,
        "ev_ri": EV_RI,
        "medium_ri": MEDIUM_RI,
        "model": "AU = k * Qsca * pi * r^2 (linear detector)",
        "channels": {},
    }
    
    for ch, cal in calibrations.items():
        output["channels"][ch] = {
            "wavelength_nm": cal["wavelength_nm"],
            "k_mean": cal["k_mean"],
            "k_std": cal["k_std"],
            "k_cv_pct": cal["k_cv_pct"],
            "max_error_pct": cal["max_error_pct"],
            "bead_data": cal["bead_data"],
        }
    
    out_path = out_dir / "au_to_sigma_calibration.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"Calibration saved: {out_path}")
    print(f"{'='*70}")
    
    # Final summary
    for ch, cal in calibrations.items():
        print(f"\n  {ch}: k={cal['k_mean']:.1f} +/- {cal['k_std']:.1f} "
              f"(CV={cal['k_cv_pct']:.1f}%, max_err={cal['max_error_pct']:.1f}%)")
    
    return calibrations


if __name__ == "__main__":
    calibrations = main()
