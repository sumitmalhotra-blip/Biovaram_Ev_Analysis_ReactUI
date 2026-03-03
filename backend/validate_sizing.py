"""
Sizing Validation Script
=========================
Purpose: Test and validate all sizing methods against known references.

This script runs 4 key tests:
1. Mie Theory Sanity Check - Are theoretical calculations correct?
2. Bead Peak Detection - Can we find peaks in bead FCS files?
3. Multi-Solution Mie Current Behavior - What does the current code actually do?
4. What the CORRECT pipeline should produce

Run from backend directory:
    python validate_sizing.py

Author: Validation for EV Analysis Platform
Date: Feb 16, 2026
"""

import sys
import os
import json
import numpy as np

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
import miepython

# Configure minimal logging
logger.remove()
logger.add(sys.stderr, level="WARNING")


def print_header(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_subheader(title: str):
    print(f"\n  --- {title} ---")


# =============================================================================
# TEST 1: Mie Theory Sanity Check
# =============================================================================
def test_mie_theory():
    print_header("TEST 1: Mie Theory Sanity Check")
    
    n_medium = 1.33  # PBS
    
    # Test with BEAD RI (polystyrene = 1.591) and EV RI (1.40)
    test_particles = [
        ("Polystyrene Bead", 1.591),
        ("EV (typical)", 1.40),
        ("EV (low estimate)", 1.37),
        ("EV (high estimate)", 1.45),
    ]
    
    test_diameters = [40, 80, 108, 142, 200, 304, 600, 1020]  # nm
    wavelengths = [405.0, 488.0]  # violet, blue
    
    print(f"\n  Medium RI: {n_medium}")
    print(f"  Wavelengths: {wavelengths} nm")
    
    for particle_name, n_particle in test_particles:
        print_subheader(f"{particle_name} (RI = {n_particle})")
        m = complex(n_particle / n_medium, 0)
        
        print(f"  {'Diameter':>8s}  {'Qback@405':>12s}  {'Qback@488':>12s}  {'σ_back@405 (nm²)':>18s}  {'σ_back@488 (nm²)':>18s}  {'Ratio V/B':>10s}")
        print(f"  {'--------':>8s}  {'----------':>12s}  {'----------':>12s}  {'-----------------':>18s}  {'-----------------':>18s}  {'---------':>10s}")
        
        for d in test_diameters:
            radius = d / 2.0
            geo_cross = np.pi * radius**2
            
            results = {}
            for wl in wavelengths:
                qext, qsca, qback, g = miepython.efficiencies(m, d, wl, n_env=n_medium)
                sigma_back = qback * geo_cross  # scatter cross-section in nm²
                results[wl] = {'qback': qback, 'sigma': sigma_back}
            
            ratio = results[405.0]['sigma'] / results[488.0]['sigma'] if results[488.0]['sigma'] > 0 else float('inf')
            
            print(f"  {d:>8d}  {results[405.0]['qback']:>12.6f}  {results[488.0]['qback']:>12.6f}  "
                  f"{results[405.0]['sigma']:>18.4f}  {results[488.0]['sigma']:>18.4f}  {ratio:>10.3f}")
    
    # KEY INSIGHT: Show how much MORE a bead scatters vs an EV of same size
    print_subheader("Scatter Ratio: Polystyrene Bead vs EV (same size)")
    m_bead = complex(1.591 / n_medium, 0)
    m_ev = complex(1.40 / n_medium, 0)
    
    print(f"  {'Diameter':>8s}  {'Bead σ@405':>14s}  {'EV σ@405':>14s}  {'Bead/EV Ratio':>15s}")
    print(f"  {'--------':>8s}  {'----------':>14s}  {'--------':>14s}  {'-------------':>15s}")
    
    for d in [80, 108, 142, 200, 304]:
        radius = d / 2.0
        geo = np.pi * radius**2
        
        _, _, qb_bead, _ = miepython.efficiencies(m_bead, d, 405.0, n_env=n_medium)
        _, _, qb_ev, _ = miepython.efficiencies(m_ev, d, 405.0, n_env=n_medium)
        
        sigma_bead = qb_bead * geo
        sigma_ev = qb_ev * geo
        ratio = sigma_bead / sigma_ev if sigma_ev > 0 else float('inf')
        
        print(f"  {d:>8d}  {sigma_bead:>14.4f}  {sigma_ev:>14.4f}  {ratio:>15.1f}x")
    
    print(f"\n  ⚠️  KEY INSIGHT: A polystyrene bead scatters 5-30x MORE than an EV of")
    print(f"     the same size. This is why direct bead calibration gives WRONG EV sizes.")
    print(f"     You MUST account for the RI difference using Mie theory.")


# =============================================================================
# TEST 2: Read Bead FCS Files and Check Peaks
# =============================================================================
def test_bead_peaks():
    print_header("TEST 2: Bead FCS File Analysis")
    
    try:
        import flowio
    except ImportError:
        print("  ❌ flowio not installed. Run: pip install flowio")
        return
    
    # Find bead FCS files  
    bead_files = {
        'Nano Vis Low (nanoFACS)': 'nanoFACS/Nano Vis Low.fcs',
        'Nano Vis High (nanoFACS)': 'nanoFACS/Nano Vis High.fcs',
    }
    
    # Also check uploads for any bead files
    uploads_dir = 'data/uploads'
    if os.path.exists(uploads_dir):
        for f in os.listdir(uploads_dir):
            if 'Nano Vis' in f and f.endswith('.fcs'):
                key = f"Uploaded: {f}"
                bead_files[key] = os.path.join(uploads_dir, f)
    
    for label, fcs_path in bead_files.items():
        if not os.path.exists(fcs_path):
            print(f"\n  ⚠️ {label}: File not found at {fcs_path}")
            continue
        
        print_subheader(f"{label}")
        print(f"  File: {fcs_path}")
        
        try:
            fcs_data = flowio.FlowData(fcs_path)
            n_events = fcs_data.event_count
            n_channels = fcs_data.channel_count
            
            # Get channel names
            channels = []
            for i in range(1, n_channels + 1):
                pnn = fcs_data.channels.get(str(i), {})
                name = pnn.get('PnN', f'Ch{i}')
                channels.append(name)
            
            print(f"  Events: {n_events:,}")
            print(f"  Channels: {n_channels}")
            
            # Extract raw data as numpy array
            raw_events = np.array(fcs_data.events, dtype=np.float64)
            raw_events = raw_events.reshape(n_events, n_channels)
            
            # Find VSSC and BSSC channels  
            vssc_idx = None
            bssc_idx = None
            for i, ch in enumerate(channels):
                if ch in ['VSSC1-H', 'VSSC-H']:
                    vssc_idx = i
                if ch in ['BSSC-H', 'BSSC1-H']:
                    bssc_idx = i
            
            if vssc_idx is not None:
                vssc = raw_events[:, vssc_idx]
                vssc_pos = vssc[vssc > 0]
                print(f"\n  VSSC1-H (405nm, gain=100):")
                print(f"    Range: {vssc_pos.min():.1f} – {vssc_pos.max():.1f} AU")
                print(f"    Median: {np.median(vssc_pos):.1f} AU")
                print(f"    Mean: {np.mean(vssc_pos):.1f} AU")
                
                # Try to find peaks using histogram
                # Use log scale for better peak separation
                log_vssc = np.log10(vssc_pos[vssc_pos > 10])
                if len(log_vssc) > 100:
                    hist, bin_edges = np.histogram(log_vssc, bins=200)
                    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                    
                    # Find local maxima (simple peak detection)
                    peaks = []
                    for i in range(2, len(hist)-2):
                        if (hist[i] > hist[i-1] and hist[i] > hist[i+1] and 
                            hist[i] > hist[i-2] and hist[i] > hist[i+2] and
                            hist[i] > 50):  # minimum peak height
                            peaks.append((bin_centers[i], hist[i]))
                    
                    if peaks:
                        print(f"\n    Detected peaks (log10 VSSC-H):")
                        for j, (peak_pos, peak_height) in enumerate(peaks):
                            au_value = 10**peak_pos
                            print(f"      Peak {j+1}: log10={peak_pos:.2f} → {au_value:.0f} AU (height={peak_height})")
                    else:
                        print(f"    No clear peaks detected (may need different bin size)")
            
            if bssc_idx is not None:
                bssc = raw_events[:, bssc_idx]
                bssc_pos = bssc[bssc > 0]
                print(f"\n  BSSC-H (488nm, gain=70):")
                print(f"    Range: {bssc_pos.min():.1f} – {bssc_pos.max():.1f} AU")
                print(f"    Median: {np.median(bssc_pos):.1f} AU")
                print(f"    Mean: {np.mean(bssc_pos):.1f} AU")
                
        except Exception as e:
            print(f"  ❌ Error reading FCS file: {e}")


# =============================================================================
# TEST 3: Current Multi-Solution Mie Behavior
# =============================================================================
def test_current_multi_mie():
    print_header("TEST 3: Current Multi-Solution Mie Behavior")
    
    from src.physics.mie_scatter import MultiSolutionMieCalculator
    
    calc = MultiSolutionMieCalculator(n_particle=1.40, n_medium=1.33)
    
    print(f"\n  Calculator settings:")
    print(f"    n_particle = {calc.n_particle}")
    print(f"    n_medium = {calc.n_medium}")
    print(f"    Diameter range: {calc.min_diameter}–{calc.max_diameter} nm")
    print(f"    LUT size: {len(calc.lut_diameters)}")
    
    # Show what the LUT actually contains
    print_subheader("LUT Scatter Values (theoretical, in nm²)")
    sample_sizes = [30, 50, 80, 100, 150, 200, 300, 500]
    print(f"  {'Diameter':>8s}  {'VSSC (405nm)':>14s}  {'BSSC (488nm)':>14s}  {'V/B Ratio':>10s}")
    print(f"  {'--------':>8s}  {'------------':>14s}  {'------------':>14s}  {'---------':>10s}")
    
    for d in sample_sizes:
        idx = np.abs(calc.lut_diameters - d).argmin()
        v = calc.lut_ssc_violet[idx]
        b = calc.lut_ssc_blue[idx]
        r = v/b if b > 0 else float('inf')
        print(f"  {d:>8d}  {v:>14.6f}  {b:>14.6f}  {r:>10.3f}")
    
    # Now show what happens when you feed in REAL FCS values
    print_subheader("What happens with real FCS AU values?")
    
    typical_vssc_values = [500, 1000, 5000, 10000, 50000, 100000]
    typical_bssc_values = [200, 400, 2000, 4000, 20000, 40000]
    
    print(f"  Typical FCS data ranges: VSSC=500–100000 AU, BSSC=200–40000 AU")
    print(f"  LUT range: VSSC={calc.lut_ssc_violet.min():.6f}–{calc.lut_ssc_violet.max():.4f} nm²")
    print(f"  LUT range: BSSC={calc.lut_ssc_blue.min():.6f}–{calc.lut_ssc_blue.max():.4f} nm²")
    print()
    print(f"  ⚠️ PROBLEM: FCS values are ~10⁴–10⁵ AU, but LUT values are ~10⁻⁶–10² nm²")
    print(f"     These are COMPLETELY DIFFERENT scales!")
    print(f"     find_all_solutions() compares them directly → GARBAGE results")
    
    # Actually run it to show the problem
    print_subheader("Running calculate_sizes_multi_solution with fake FCS data")
    
    # Simulate 10 events with typical FCS scatter values
    fake_vssc = np.array([500, 1000, 5000, 10000, 20000, 50000, 100000, 150000, 200000, 250000], dtype=np.float64)
    fake_bssc = np.array([200, 400, 2000, 4000, 8000, 20000, 40000, 60000, 80000, 100000], dtype=np.float64)
    
    sizes, num_solutions = calc.calculate_sizes_multi_solution(fake_bssc, fake_vssc)
    
    print(f"  {'VSSC (AU)':>12s}  {'BSSC (AU)':>12s}  {'Solutions':>10s}  {'Size (nm)':>10s}  {'Comment':>20s}")
    print(f"  {'--------':>12s}  {'--------':>12s}  {'---------':>10s}  {'---------':>10s}  {'-------':>20s}")
    
    for i in range(len(fake_vssc)):
        size_str = f"{sizes[i]:.1f}" if not np.isnan(sizes[i]) else "NaN"
        comment = ""
        if np.isnan(sizes[i]):
            comment = "No match found!"
        elif num_solutions[i] == 0:
            comment = "No solutions"
        else:
            comment = f"({int(num_solutions[i])} solution(s))"
        
        print(f"  {fake_vssc[i]:>12.0f}  {fake_bssc[i]:>12.0f}  {int(num_solutions[i]):>10d}  {size_str:>10s}  {comment:>20s}")
    
    valid_sizes = sizes[~np.isnan(sizes)]
    if len(valid_sizes) > 0:
        print(f"\n  Results: D50 = {np.median(valid_sizes):.1f} nm (expected ~150 nm for EVs)")
    else:
        print(f"\n  Results: ALL NaN — the scale mismatch means nothing matches")


# =============================================================================
# TEST 4: What CORRECTED Pipeline Should Give
# =============================================================================
def test_corrected_pipeline():
    print_header("TEST 4: What a CORRECTED Pipeline Would Produce")
    
    n_medium = 1.33
    n_bead = 1.591  # polystyrene
    n_ev = 1.40     # typical EV
    m_bead = complex(n_bead / n_medium, 0)
    m_ev = complex(n_ev / n_medium, 0)
    wavelength = 405.0  # VSSC channel
    
    # Step 1: Calculate theoretical scatter for each bead size
    bead_sizes = [40, 80, 108, 142, 304, 600, 1020]  # from datasheet
    
    print(f"\n  Step 1: Theoretical scatter cross-sections for nanoViS beads")
    print(f"  (RI={n_bead}, wavelength={wavelength}nm)")
    print()
    
    bead_scatter = {}
    print(f"  {'Bead (nm)':>10s}  {'Qback':>12s}  {'σ_back (nm²)':>14s}")
    print(f"  {'---------':>10s}  {'-----':>12s}  {'------------':>14s}")
    
    for d in bead_sizes:
        radius = d / 2.0
        geo = np.pi * radius**2
        _, _, qback, _ = miepython.efficiencies(m_bead, d, wavelength, n_env=n_medium)
        sigma = qback * geo
        bead_scatter[d] = sigma
        print(f"  {d:>10d}  {qback:>12.6f}  {sigma:>14.4f}")
    
    # Step 2: Simulate the calibration 
    # In reality, you'd get AU values from peak detection in bead FCS files
    # For now, let's assume a linear relationship: AU = k × σ_back
    # This is what FCMPASS determines
    
    print_subheader("Step 2: Simulated Instrument Calibration")
    print(f"  Assume instrument response: AU = k × σ_back")
    print(f"  (In reality, k is determined by fitting bead peak AU values vs theoretical σ)")
    
    # Simulate with k = 10000 (arbitrary, would be determined from actual bead data)
    k_sim = 10000.0
    print(f"  Using simulated k = {k_sim:.0f} for demonstration")
    print()
    
    print(f"  {'Bead (nm)':>10s}  {'σ_back (nm²)':>14s}  {'Simulated AU':>14s}")
    print(f"  {'---------':>10s}  {'------------':>14s}  {'------------':>14s}")
    for d in bead_sizes:
        au = bead_scatter[d] * k_sim
        print(f"  {d:>10d}  {bead_scatter[d]:>14.4f}  {au:>14.1f}")
    
    # Step 3: Now size EVs correctly
    print_subheader("Step 3: Size EVs using calibrated Mie theory")
    print(f"  Switch to EV RI = {n_ev}")
    
    # Build EV Mie lookup: diameter → σ_back for EVs
    ev_diameters = np.linspace(20, 500, 4810)  # 0.1nm resolution
    ev_scatter = np.zeros(len(ev_diameters))
    
    for i, d in enumerate(ev_diameters):
        radius = d / 2.0
        geo = np.pi * radius**2
        _, _, qback, _ = miepython.efficiencies(m_ev, d, wavelength, n_env=n_medium)
        ev_scatter[i] = qback * geo
    
    # For a set of "fake measured" AU values, convert AU → σ → diameter
    print(f"\n  Simulated EV sizing (AU → σ_back → diameter):")
    print(f"  {'AU value':>10s}  {'σ_back (nm²)':>14s}  {'EV diameter':>12s}")
    print(f"  {'---------':>10s}  {'------------':>14s}  {'----------':>12s}")
    
    test_au_values = [50, 100, 500, 1000, 5000, 10000, 50000]
    for au in test_au_values:
        # AU → σ_back using calibration
        sigma = au / k_sim
        
        # σ_back → EV diameter using Mie LUT
        idx = np.abs(ev_scatter - sigma).argmin()
        ev_d = ev_diameters[idx]
        
        print(f"  {au:>10d}  {sigma:>14.6f}  {ev_d:>12.1f} nm")
    
    print(f"\n  ✅ KEY POINT: The same AU value gives a LARGER diameter for EVs than")
    print(f"     for beads, because EVs scatter less per unit size (lower RI contrast).")
    
    # Show the NTA comparison expectation
    print_subheader("Expected NTA Comparison")
    print(f"  Your NTA D50 for PC3 100kDa: ~151.7 nm")
    print(f"  After correct calibration, the FC-derived D50 should be")
    print(f"  within ~20% of this value (120–180 nm range).")
    print()
    print(f"  Currently the code gives:")
    print(f"    - Bead cal (direct):    ~42 nm  (WRONG — uses bead RI for EV sizing)")
    print(f"    - Multi-Mie (current):  ~321 nm or NaN (WRONG — AU vs nm² mismatch)")
    print(f"    - Single-Mie:           variable (WRONG — arbitrary normalization)")


# =============================================================================
# TEST 5: Practical next step — read actual bead AU values
# =============================================================================
def test_read_actual_beads():
    print_header("TEST 5: Read Actual Bead Scatter Values from FCS Files")
    
    try:
        import flowio
    except ImportError:
        print("  ❌ flowio not installed. Run: pip install flowio")
        return
    
    for fcs_name, expected_beads in [
        ('nanoFACS/Nano Vis Low.fcs', [40, 80, 108, 142]),
        ('nanoFACS/Nano Vis High.fcs', [142, 304, 600, 1020])
    ]:
        if not os.path.exists(fcs_name):
            print(f"  ❌ File not found: {fcs_name}")
            continue
        
        print_subheader(f"{os.path.basename(fcs_name)} (expected beads: {expected_beads} nm)")
        
        fcs_data = flowio.FlowData(fcs_name)
        n_events = fcs_data.event_count
        n_channels = fcs_data.channel_count
        
        channels = []
        for i in range(1, n_channels + 1):
            pnn = fcs_data.channels.get(str(i), {})
            name = pnn.get('PnN', f'Ch{i}')
            channels.append(name)
        
        raw = np.array(fcs_data.events, dtype=np.float64).reshape(n_events, n_channels)
        
        # Get VSSC1-H and BSSC-H
        for ch_name in ['VSSC1-H', 'BSSC-H']:
            if ch_name not in channels:
                continue
            
            ch_idx = channels.index(ch_name)
            values = raw[:, ch_idx]
            pos_values = values[values > 10]  # filter noise
            
            print(f"\n  Channel: {ch_name}")
            print(f"  Total events: {n_events:,}, positive events: {len(pos_values):,}")
            
            if len(pos_values) < 100:
                continue
            
            # Log-space histogram for peak detection
            log_vals = np.log10(pos_values)
            
            # Use scipy KDE for better peak detection
            try:
                from scipy.signal import find_peaks
                from scipy.stats import gaussian_kde
                
                # KDE on log-transformed data
                kde = gaussian_kde(log_vals, bw_method=0.02)
                x_grid = np.linspace(log_vals.min(), log_vals.max(), 1000)
                kde_values = kde(x_grid)
                
                # Find peaks
                peak_indices, peak_props = find_peaks(
                    kde_values, 
                    height=0.05 * kde_values.max(),
                    distance=30,
                    prominence=0.02 * kde_values.max()
                )
                
                if len(peak_indices) > 0:
                    print(f"  Detected {len(peak_indices)} peaks:")
                    for j, pidx in enumerate(peak_indices):
                        log_pos = x_grid[pidx]
                        au_value = 10**log_pos
                        print(f"    Peak {j+1}: log10={log_pos:.3f} → {au_value:.0f} AU  (KDE height={kde_values[pidx]:.4f})")
                    
                    if len(peak_indices) == len(expected_beads):
                        print(f"\n  ✅ Found {len(peak_indices)} peaks matching {len(expected_beads)} expected beads!")
                        print(f"  Potential mapping:")
                        sorted_peaks = sorted([(x_grid[p], 10**x_grid[p]) for p in peak_indices], key=lambda x: x[1])
                        for (lp, au), bead_d in zip(sorted_peaks, sorted(expected_beads)):
                            print(f"    {bead_d:>6d} nm bead → {au:>10.0f} AU")
                    else:
                        print(f"  ⚠️ Found {len(peak_indices)} peaks but expected {len(expected_beads)}")
                else:
                    print(f"  ⚠️ No peaks found with current parameters")
                    
            except ImportError:
                print(f"  (scipy not available for KDE peak detection)")
                # Fallback to simple histogram
                hist, edges = np.histogram(log_vals, bins=150)
                centers = (edges[:-1] + edges[1:]) / 2
                
                peaks = []
                for i in range(2, len(hist)-2):
                    if (hist[i] > hist[i-1] and hist[i] > hist[i+1] and hist[i] > 30):
                        peaks.append((centers[i], 10**centers[i], hist[i]))
                
                print(f"  Rough peaks (histogram-based):")
                for j, (lp, au, h) in enumerate(peaks):
                    print(f"    Peak {j+1}: {au:.0f} AU (count={h})")


# =============================================================================
# SUMMARY
# =============================================================================
def print_summary():
    print_header("SUMMARY: What Needs to Be Fixed")
    
    print("""
  CURRENT STATE:
  ─────────────
  1. Bead calibration: Uses power law (FSC = a×d^b) with bead RI (1.591)
     to directly size EVs → WRONG (RI mismatch, gives ~42nm instead of ~150nm)
  
  2. Multi-solution Mie: Compares theoretical scatter (nm²) directly to
     raw FCS values (arbitrary units) → COMPLETE MISMATCH, produces garbage
  
  3. Single-solution Mie: Uses percentile normalization to map FCS values
     to physical scatter → sizes are RELATIVE, not absolute
  
  4. FCMPASSCalibrator: EXISTS in the code but is NEVER USED by any API endpoint

  WHAT NEEDS TO HAPPEN:
  ────────────────────
  1. REMOVE direct bead calibration as a sizing method
     (or repurpose it as Step 1 of FCMPASS pipeline)
  
  2. FIX the Multi-Solution Mie calculator:
     a. Add a calibration step that converts AU → scatter cross-section (nm²)
     b. Use bead FCS data for this calibration
     c. THEN use Mie theory with EV RI (1.40) for the actual sizing
  
  3. Wire up the existing FCMPASSCalibrator class to the API endpoints
  
  4. Validate against NTA (D50 should be ~152nm for PC3 100kDa samples)

  RESOURCES YOU HAVE:
  ──────────────────
  ✅ Bead FCS files (Nano Vis Low + High, all 7 sizes)
  ✅ Bead datasheet (40,80,108,142,304,600,1020 nm, RI=1.591)
  ✅ NTA reference data (PC3 100kDa, D50 ~152nm)
  ✅ PC3 EXO sample FCS files (many uploads)
  ✅ miepython library (Mie theory calculations)
  ✅ FCMPASSCalibrator class (already written, just not connected)
  ✅ flowio library (read FCS files)

  PRIORITY ORDER:
  ──────────────
  1. First: Get bead peak AU values from FCS files (Test 5 above)
  2. Second: Build AU → σ calibration curve using Mie theory with bead RI
  3. Third: Fix MultiSolutionMieCalculator to use calibrated values
  4. Fourth: Compare FC sizes vs NTA for PC3 samples
""")


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("  EV SIZING VALIDATION SCRIPT")
    print("  Testing all sizing methods against known physics")
    print("="*70)
    
    # Change to backend directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    test_mie_theory()
    test_bead_peaks()
    test_current_multi_mie()
    test_corrected_pipeline()
    test_read_actual_beads()
    print_summary()
    
    print(f"\n{'='*70}")
    print(f"  DONE. Review results above.")
    print(f"{'='*70}\n")
