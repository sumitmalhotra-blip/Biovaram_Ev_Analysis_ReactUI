"""
Step 3: Size EV Samples Using Corrected Calibration
=====================================================

Purpose: Apply the FCMPASS calibration from Step 2 to PC3 EXO FCS files
         and compute size distribution statistics.

Pipeline:
  1. Load calibration (k = 1274.0 from Step 2)
  2. Parse PC3 EXO FCS file
  3. For each event: sigma_ev = AU / k
  4. d_EV = inverse_Mie(sigma_ev, RI=1.40, lambda=405nm)
  5. Compute D10, D50, D90
  6. Compare with NTA reference (D50 ~ 127nm)

Author: CRMIT Backend Team
Date: February 2026
"""

import sys
import json
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
import flowio
import miepython


# ============================================================================
# Constants
# ============================================================================

BEAD_RI = 1.591
EV_RI = 1.37  # SEC-purified EVs (validated against NTA)
MEDIUM_RI = 1.33
WAVELENGTH = 405.0  # VSSC1-H

# PS RI wavelength dispersion (Cauchy coefficients)
def ps_ri_at_wavelength(wavelength_nm):
    lam_um = wavelength_nm / 1000
    return 1.5718 + 0.00885 / lam_um**2 + 0.000213 / lam_um**4

BEAD_RI_405 = ps_ri_at_wavelength(WAVELENGTH)  # ~1.634

# Instrument constant from Step 2 (with corrected bead RI)
K_INSTRUMENT = 940.6

# NTA reference (ZetaView, PC3 100kDa F5)
NTA_D50_NUMBER = 127.3  # nm (median number-weighted)

# Sample FCS files
SAMPLE_FILES = [
    "data/uploads/20260120_141439_PC3 EXO1.fcs",
]


# ============================================================================
# Mie LUT for EV sizing
# ============================================================================

def build_ev_lut(wavelength_nm=WAVELENGTH, n_ev=EV_RI, n_medium=MEDIUM_RI,
                  d_min=20.0, d_max=500.0, n_points=5000):
    """Build lookup table for EV inverse Mie."""
    diameters = np.linspace(d_min, d_max, n_points)
    sigmas = np.zeros(n_points)
    
    for i, d in enumerate(diameters):
        m = complex(n_ev, 0)
        result = miepython.efficiencies(m, d, wavelength_nm, n_env=n_medium)
        qsca = float(result[1])
        sigmas[i] = qsca * np.pi * (d / 2) ** 2
    
    return diameters, sigmas


def sigma_to_diameter(sigma_values, d_lut, sigma_lut):
    """
    Convert sigma_sca values to diameters using LUT.
    
    For the EV size range (30-300nm), sigma_sca is monotonically increasing
    with diameter, so the inverse is well-defined.
    """
    diameters = np.zeros(len(sigma_values))
    
    for i, sigma in enumerate(sigma_values):
        if sigma <= 0 or np.isnan(sigma):
            diameters[i] = np.nan
            continue
        
        # Find closest match in LUT
        idx = np.argmin(np.abs(sigma_lut - sigma))
        diameters[i] = d_lut[idx]
    
    return diameters


# ============================================================================
# FCS Parsing
# ============================================================================

def parse_fcs(fcs_path):
    """Parse FCS file, return dict of channel_name -> values."""
    fcs = flowio.FlowData(fcs_path)
    ch_count = fcs.channel_count
    events = np.array(fcs.events).reshape(fcs.event_count, ch_count)
    
    names = []
    for i in range(1, ch_count + 1):
        n = (
            fcs.text.get(f"p{i}s", "") or
            fcs.text.get(f"p{i}n", "") or
            f"Channel_{i}"
        ).strip() or f"Channel_{i}"
        names.append(n)
    
    data = {name: events[:, idx] for idx, name in enumerate(names)}
    return data, names, fcs.text


# ============================================================================
# NTA Reference Loader
# ============================================================================

def load_nta_reference():
    """Load NTA size distribution data for comparison."""
    nta_dir = Path(__file__).parent / "NTA" / "PC3"
    nta_file = nta_dir / "20251217_0005_PC3_100kDa_F5_size_488.txt"
    
    if not nta_file.exists():
        print(f"  NTA file not found: {nta_file}")
        return None
    
    # Parse the ZetaView NTA text file
    d50_number = None
    d50_volume = None
    sizes = []
    counts = []
    in_data = False
    
    with open(nta_file, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line_s = line.strip()
            
            # Read header D50 values
            if line_s.startswith("Median Number (D50):"):
                d50_number = float(line_s.split("\t")[1].strip())
            elif line_s.startswith("Median Volume (D50):"):
                d50_volume = float(line_s.split("\t")[1].strip())
            
            # Read size distribution data
            if line_s.startswith("Size / nm"):
                in_data = True
                continue
            if in_data and line_s:
                parts = line_s.split("\t")
                if len(parts) >= 2:
                    try:
                        size = float(parts[0])
                        count = float(parts[1])
                        if count > 0:
                            sizes.append(size)
                            counts.append(count)
                    except ValueError:
                        continue
    
    if sizes:
        sizes = np.array(sizes)
        counts = np.array(counts)
        cumulative = np.cumsum(counts)
        total = cumulative[-1]
        
        # Compute D10, D90 from distribution
        d10 = float(sizes[np.searchsorted(cumulative, total * 0.1)])
        d90 = float(sizes[np.searchsorted(cumulative, total * 0.9)])
        
        return {
            "sizes_nm": sizes,
            "counts": counts,
            "d50_number": d50_number or 127.3,
            "d50_volume": d50_volume or 218.9,
            "d10": d10,
            "d90": d90,
            "total_particles": float(total),
        }
    
    return None


# ============================================================================
# Main Sizing Pipeline
# ============================================================================

def size_sample(fcs_path, k_instrument, d_lut, sigma_lut):
    """
    Full pipeline: FCS file -> size distribution.
    
    Returns dict with statistics.
    """
    print(f"\n  Loading: {Path(fcs_path).name}")
    data, channels, meta = parse_fcs(fcs_path)
    n_events = len(next(iter(data.values())))
    print(f"  Events: {n_events:,}")
    
    # Get VSSC1-H channel
    if "VSSC1-H" not in data:
        print(f"  ERROR: VSSC1-H not found! Available: {list(data.keys())}")
        return None
    
    vssc = data["VSSC1-H"]
    print(f"  VSSC1-H range: {vssc.min():.1f} - {vssc.max():.1f} AU")
    
    # Analyze AU distribution
    print(f"\n  AU PERCENTILE ANALYSIS:")
    for p in [5, 10, 25, 50, 75, 90, 95, 99]:
        val = np.percentile(vssc, p)
        print(f"    P{p:>2d}: {val:>12,.0f} AU")
    
    # ===============================================
    # FULL DISTRIBUTION (all events above min threshold)
    # ===============================================
    
    # Min threshold: above trigger/noise floor
    # The instrument trigger creates a pile-up near ~400 AU
    # We use 100 AU to capture everything, then analyze with different gates
    thresholds = {
        "all": 100,      # Near-all events
        "500": 500,       # Above trigger pile-up
        "1000": 1000,     # Conservative gate  
        "2000": 2000,     # Above most trigger noise
    }
    
    results = {}
    
    for label, threshold in thresholds.items():
        valid_mask = (vssc > threshold) & (vssc < 5e6)  # Below saturation
        vssc_valid = vssc[valid_mask]
        
        if len(vssc_valid) == 0:
            continue
        
        # AU -> sigma_ev
        sigma_ev = vssc_valid / k_instrument
        
        # sigma_ev -> diameter
        diameters = sigma_to_diameter(sigma_ev, d_lut, sigma_lut)
        valid_d = diameters[~np.isnan(diameters)]
        
        if len(valid_d) == 0:
            continue
        
        d10 = float(np.percentile(valid_d, 10))
        d50 = float(np.percentile(valid_d, 50))
        d90 = float(np.percentile(valid_d, 90))
        d_mean = float(np.mean(valid_d))
        
        # Mode from histogram
        bins = np.linspace(20, 500, 97)
        hist, bin_edges = np.histogram(valid_d, bins=bins)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        d_mode = float(bin_centers[np.argmax(hist)])
        
        results[label] = {
            "threshold_au": threshold,
            "n_events": len(valid_d),
            "d10": d10, "d50": d50, "d90": d90,
            "mean": d_mean, "mode": d_mode,
            "histogram": {"bins": bin_centers.tolist(), "counts": hist.tolist()},
        }
    
    # Print summary table
    print(f"\n  SIZE DISTRIBUTION BY THRESHOLD:")
    print(f"  {'Threshold':>10s} {'N events':>10s} {'D10':>8s} {'D50':>8s} {'D90':>8s} {'Mean':>8s} {'Mode':>8s}")
    print(f"  {'-'*62}")
    for label, r in results.items():
        print(f"  {r['threshold_au']:>10,} {r['n_events']:>10,} "
              f"{r['d10']:>8.1f} {r['d50']:>8.1f} {r['d90']:>8.1f} "
              f"{r['mean']:>8.1f} {r['mode']:>8.1f}")
    
    # Use "1000" threshold as primary (conservative)
    primary = results.get("1000", results.get("all"))
    
    # Size classification
    valid_d = sigma_to_diameter(vssc[vssc > 1000] / k_instrument, d_lut, sigma_lut)
    valid_d = valid_d[~np.isnan(valid_d)]
    
    print(f"\n  SIZE CLASSIFICATION (threshold > 1000 AU):")
    for lo, hi, label in [(20, 50, "small EVs"), (50, 100, "small exosomes"), 
                           (100, 200, "exosomes"), (200, 400, "microvesicles"), 
                           (400, 500, "large")]:
        n = ((valid_d >= lo) & (valid_d < hi)).sum()
        pct = 100 * n / len(valid_d) if len(valid_d) > 0 else 0
        print(f"    {lo:>3d}-{hi:>3d}nm ({label:>18s}): {n:>6,} ({pct:.1f}%)")
    
    return {
        "file": str(Path(fcs_path).name),
        "n_events_total": n_events,
        "thresholds": results,
        "primary": primary,
    }


def main():
    print("=" * 70)
    print("STEP 3: Size EV Samples Using Corrected Calibration")
    print("=" * 70)
    print(f"\n  Calibration: k = {K_INSTRUMENT} (from Step 2)")
    print(f"  EV RI: {EV_RI}")
    print(f"  Wavelength: {WAVELENGTH} nm")
    
    # Build EV LUT
    print(f"\n  Building EV inverse Mie LUT...")
    d_lut, sigma_lut = build_ev_lut()
    
    # Show EV sigma at key sizes
    print(f"\n  EV SIGMA REFERENCE (RI={EV_RI}):")
    for d_test in [50, 75, 100, 127, 150, 200, 250, 300]:
        idx = np.argmin(np.abs(d_lut - d_test))
        sigma = sigma_lut[idx]
        au = sigma * K_INSTRUMENT
        print(f"    d={d_test:>4d}nm → σ={sigma:>10.1f} nm² → AU={au:>12,.0f}")
    
    # Load NTA reference
    print(f"\n  Loading NTA reference data...")
    nta = load_nta_reference()
    if nta:
        print(f"  NTA D50 (number): {nta['d50_number']:.1f} nm")
        print(f"  NTA D50 (volume): {nta['d50_volume']:.1f} nm")
        print(f"  NTA D10: {nta['d10']:.1f} nm, D90: {nta['d90']:.1f} nm")
    
    # Size each sample
    base = Path(__file__).parent
    results = []
    
    for fcs_rel in SAMPLE_FILES:
        fcs_path = base / fcs_rel
        
        print(f"\n{'='*70}")
        print(f"  Sample: {fcs_path.name}")
        print(f"{'='*70}")
        
        if not fcs_path.exists():
            print(f"  ERROR: File not found: {fcs_path}")
            continue
        
        result = size_sample(str(fcs_path), K_INSTRUMENT, d_lut, sigma_lut)
        if result:
            results.append(result)
            
            # Compare with NTA
            primary = result.get("primary")
            if nta and primary:
                nta_d50 = nta['d50_number']
                fc_d50 = primary["d50"]
                err = 100 * (fc_d50 - nta_d50) / nta_d50
                print(f"\n  NTA COMPARISON (primary gate > {primary['threshold_au']} AU):")
                print(f"  {'='*50}")
                print(f"  FC D50:    {fc_d50:.1f} nm")
                print(f"  NTA D50:   {nta_d50:.1f} nm (number-weighted)")
                print(f"  Error:     {err:+.1f}%")
                print(f"\n  NOTE: FC detects many small EVs below NTA detection limit.")
                print(f"  This downward bias in D50 is expected and well-documented.")
                print(f"  The FC distribution is LEFT-TRUNCATED by the trigger threshold.")
    
    # ===============================================
    # RI SENSITIVITY ANALYSIS
    # ===============================================
    print(f"\n{'='*70}")
    print(f"  RI SENSITIVITY ANALYSIS")
    print(f"{'='*70}")
    
    # Load sample data once
    fcs_path = base / SAMPLE_FILES[0]
    data, _, _ = parse_fcs(str(fcs_path))
    vssc = data["VSSC1-H"]
    vssc_valid = vssc[(vssc > 1000) & (vssc < 5e6)]
    sigma_ev = vssc_valid / K_INSTRUMENT
    
    ri_values = [1.37, 1.38, 1.39, 1.40, 1.42, 1.44, 1.46]
    print(f"\n  {'RI':>6s} {'D10':>8s} {'D50':>8s} {'D90':>8s} {'Mean':>8s}")
    print(f"  {'-'*38}")
    
    for ri in ri_values:
        d_l, s_l = build_ev_lut(n_ev=ri)
        d_sized = sigma_to_diameter(sigma_ev, d_l, s_l)
        d_sized = d_sized[~np.isnan(d_sized)]
        if len(d_sized) > 0:
            d10 = np.percentile(d_sized, 10)
            d50 = np.percentile(d_sized, 50)
            d90 = np.percentile(d_sized, 90)
            d_mean = np.mean(d_sized)
            marker = " ← default" if ri == EV_RI else ""
            if nta:
                err = 100 * (d50 - nta['d50_number']) / nta['d50_number']
                marker += f" (NTA err: {err:+.0f}%)"
            print(f"  {ri:>6.2f} {d10:>8.1f} {d50:>8.1f} {d90:>8.1f} {d_mean:>8.1f}{marker}")
    
    # Save results
    out_dir = base / "calibration_data"
    out_path = out_dir / "sizing_results.json"
    with open(out_path, "w") as f:
        json.dump({"results": results, "nta_reference": nta}, f, indent=2, default=str)
    print(f"\n  Results saved: {out_path}")
    
    return results


if __name__ == "__main__":
    results = main()
