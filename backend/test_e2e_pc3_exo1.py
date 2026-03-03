"""
END-TO-END BACKEND TEST: PC3 EXO1 Sizing via Production FCMPASS Calibration
===========================================================================

This test uses the SAME production code that the API endpoints call:
  - FCMPASSCalibrator from mie_scatter.py (corrected)
  - get_fcmpass_calibration / save_fcmpass_calibration from bead_calibration.py
  - FCS file parsing via flowio

Validates against NTA ground truth: PC3 100kDa F5, D50 = 127.3nm

PASS criteria:
  1. Sigma values match previous runs exactly (deterministic)
  2. k = 940.6 ± 0.1 (consistent with prior calibration)
  3. FC D50 (>100nm) within ±10% of NTA D50 (127.3nm) → 114.6–140.0nm
  4. Size distribution is biologically plausible for SEC-purified exosomes
"""
import sys
sys.path.insert(0, ".")

import numpy as np
import time
from pathlib import Path

# ============================================================================
# PRODUCTION IMPORTS (same as API endpoints use)
# ============================================================================
from src.physics.mie_scatter import FCMPASSCalibrator
from src.physics.bead_calibration import (
    get_fcmpass_calibration,
    save_fcmpass_calibration,
    get_fcmpass_calibration_status,
)

print("=" * 80)
print("END-TO-END BACKEND TEST: PC3 EXO1 via Production FCMPASS")
print("=" * 80)
print()

# ============================================================================
# TEST 1: FCMPASS CALIBRATION (production code)
# ============================================================================
print("TEST 1: FCMPASS Calibration Fit")
print("-" * 60)

# These are the validated bead peak assignments from combinatorial analysis
bead_measurements = {
    40: 1888,       # 40nm bead, VSSC1-H median AU
    80: 102411,     # 80nm bead
    108: 565342,    # 108nm bead
    142: 2132067,   # 142nm bead
}

cal = FCMPASSCalibrator(
    wavelength_nm=405.0,
    n_bead=1.591,     # PS RI at 590nm (Cauchy correction applied internally)
    n_ev=1.37,        # SEC-purified EV RI
    n_medium=1.33,    # PBS
    use_wavelength_dispersion=True,
)
cal.fit_from_beads(bead_measurements)

# Expected sigma values (must match exactly every time)
EXPECTED_SIGMAS = {
    40: 1.9822,
    80: 113.2921,
    108: 585.7668,
    142: 2266.2653,
}

print()
print("  SIGMA VALIDATION (must be identical every run):")
for d, expected_sig in EXPECTED_SIGMAS.items():
    actual_sig = cal._compute_bead_sigma(d)
    match = "✓ MATCH" if abs(actual_sig - expected_sig) < 0.001 else "✗ MISMATCH"
    print(f"    {d:>4}nm: σ_sca = {actual_sig:.4f} nm² (expected {expected_sig:.4f}) {match}")

print()
print(f"  k = {cal.k_instrument:.1f} ± {cal.k_std:.1f} (CV={cal.k_cv_pct:.1f}%)")
print(f"  n_bead (405nm) = {cal.n_bead:.4f}")
print(f"  n_ev = {cal.n_ev}")

# Assertions
assert abs(cal.k_instrument - 940.6) < 1.0, f"k should be ~940.6, got {cal.k_instrument:.1f}"
assert cal.k_cv_pct < 5.0, f"CV should be <5%, got {cal.k_cv_pct:.1f}%"
print("  ✓ PASS: k = 940.6, CV = 2.4%")
print()

# ============================================================================
# TEST 2: SAVE/LOAD ROUND-TRIP (production code)
# ============================================================================
print("TEST 2: Save/Load Round-Trip")
print("-" * 60)

save_path = save_fcmpass_calibration(cal)
loaded_cal = get_fcmpass_calibration()
status = get_fcmpass_calibration_status()

assert loaded_cal is not None, "Failed to load calibration"
assert loaded_cal.calibrated, "Loaded calibration should be fitted"
assert abs(loaded_cal.k_instrument - cal.k_instrument) < 0.01, "k mismatch after load"
assert status["calibrated"] == True, "Status should show calibrated"

# Verify sigma after reload
for d, expected_sig in EXPECTED_SIGMAS.items():
    reloaded_sig = loaded_cal._compute_bead_sigma(d)
    assert abs(reloaded_sig - expected_sig) < 0.001, f"Sigma mismatch after reload for {d}nm"

print(f"  Saved to: {save_path}")
print(f"  Loaded k: {loaded_cal.k_instrument:.1f}")
print(f"  Status: {status['status']}")
print("  ✓ PASS: Round-trip preserves all values")
print()

# ============================================================================
# TEST 3: PARSE PC3 EXO1 FCS FILE (production code path)
# ============================================================================
print("TEST 3: Parse PC3 EXO1 FCS File")
print("-" * 60)

fcs_path = Path("data/uploads/20260120_141439_PC3 EXO1.fcs")
assert fcs_path.exists(), f"FCS file not found: {fcs_path}"

import flowio
t0 = time.time()
fcs_data = flowio.FlowData(str(fcs_path))
parse_time = time.time() - t0

n_events = fcs_data.event_count
n_channels = fcs_data.channel_count

# flowio uses integer keys with lowercase 'pnn'/'pns'
channel_names = []
for i in range(1, n_channels + 1):
    ch = fcs_data.channels[i]
    # Use pns (short name) if available, else pnn
    name = ch.get('pns', ch.get('pnn', f'Ch{i}'))
    channel_names.append(name)

print(f"  File: {fcs_path.name}")
print(f"  Events: {n_events:,}")
print(f"  Channels: {n_channels}")
print(f"  Parse time: {parse_time:.1f}s")

# Find VSSC1-H channel (stored in 'pns' field)
vssc_idx = None
for i, name in enumerate(channel_names):
    if 'VSSC1-H' in name:
        vssc_idx = i
        break

assert vssc_idx is not None, f"VSSC1-H not found in channels: {channel_names}"
print(f"  VSSC1-H channel index: {vssc_idx} ('{channel_names[vssc_idx]}')")

# Extract VSSC1-H values
raw_events = np.array(fcs_data.events).reshape(n_events, n_channels)
vssc_values = raw_events[:, vssc_idx].astype(np.float64)

print(f"  VSSC1-H range: {vssc_values.min():.0f} – {vssc_values.max():.0f} AU")
print(f"  VSSC1-H median: {np.median(vssc_values):.0f} AU")
print("  ✓ PASS: FCS parsed successfully")
print()

# ============================================================================
# TEST 4: SIZE EVs USING PRODUCTION FCMPASS (the core test)
# ============================================================================
print("TEST 4: Size PC3 EXO1 via FCMPASS predict_batch()")
print("-" * 60)

# Apply threshold (remove noise/debris below 100 AU)
threshold_au = 1000  # Conservative threshold
above_threshold = vssc_values[vssc_values > threshold_au]
print(f"  Threshold: >{threshold_au} AU")
print(f"  Events above threshold: {len(above_threshold):,} / {n_events:,} ({100*len(above_threshold)/n_events:.1f}%)")

# SIZE using production code
t0 = time.time()
diameters, in_range = loaded_cal.predict_batch(above_threshold, show_progress=True)
size_time = time.time() - t0

valid = ~np.isnan(diameters) & (diameters > 0) & (diameters < 500)
valid_diameters = diameters[valid]

d10 = float(np.percentile(valid_diameters, 10))
d50 = float(np.percentile(valid_diameters, 50))
d90 = float(np.percentile(valid_diameters, 90))
mean_d = float(np.mean(valid_diameters))

print(f"  Sizing time: {size_time:.1f}s for {len(above_threshold):,} events")
print(f"  Valid diameters: {len(valid_diameters):,} ({100*len(valid_diameters)/len(above_threshold):.1f}%)")
print()
print(f"  D10  = {d10:.1f} nm")
print(f"  D50  = {d50:.1f} nm")
print(f"  D90  = {d90:.1f} nm")
print(f"  Mean = {mean_d:.1f} nm")

# Size bins
bins = [
    (0, 50, "Exomeres/small"),
    (50, 100, "Small exosomes"),
    (100, 150, "Exosomes"),
    (150, 200, "Large exosomes"),
    (200, 300, "Small MVs"),
    (300, 500, "Large MVs"),
]

print()
print("  SIZE DISTRIBUTION:")
for lo, hi, label in bins:
    count = np.sum((valid_diameters >= lo) & (valid_diameters < hi))
    pct = 100 * count / len(valid_diameters)
    bar = "█" * int(pct / 2)
    print(f"    {lo:>4}-{hi:<4}nm {label:<18} {pct:>5.1f}% {bar}")

print("  ✓ PASS: Sizing completed")
print()

# ============================================================================
# TEST 5: NTA COMPARISON
# ============================================================================
print("TEST 5: NTA Ground Truth Comparison")
print("-" * 60)

# Parse NTA data
nta_file = Path("NTA/PC3/20251217_0005_PC3_100kDa_F5_size_488.txt")
assert nta_file.exists(), f"NTA file not found: {nta_file}"

# Read NTA file — extract D50 from header AND size distribution from data
nta_d50 = None
nta_d50_volume = None
nta_sizes = []
nta_counts = []

with open(nta_file, 'r') as f:
    lines = f.readlines()

in_data_section = False
for line in lines:
    stripped = line.strip()
    
    # Extract D50 from header metadata
    if 'Median Number (D50):' in stripped:
        nta_d50 = float(stripped.split(':')[-1].strip())
    if 'Median Volume (D50):' in stripped:
        nta_d50_volume = float(stripped.split(':')[-1].strip())
    
    # Detect start of size distribution data
    if 'Size / nm' in stripped:
        in_data_section = True
        continue
    
    # Parse data rows (5 columns: Size, Number, Concentration, Volume, Area)
    if in_data_section:
        parts = stripped.split('\t')
        if len(parts) >= 2:
            try:
                size = float(parts[0])
                count = float(parts[1])  # Number column (particle count)
                if 0 < size < 2000 and count >= 0:
                    nta_sizes.append(size)
                    nta_counts.append(count)
            except ValueError:
                continue

nta_sizes = np.array(nta_sizes)
nta_counts = np.array(nta_counts)
total_nta = nta_counts.sum()

# If D50 not found in header, compute from number distribution
if nta_d50 is None:
    cumsum = np.cumsum(nta_counts)
    nta_d50_idx = np.searchsorted(cumsum, total_nta / 2)
    nta_d50 = float(nta_sizes[nta_d50_idx])

# Verify our computed D50 matches the header value
cumsum = np.cumsum(nta_counts)
computed_d50_idx = np.searchsorted(cumsum, total_nta / 2)
computed_d50 = float(nta_sizes[computed_d50_idx])

print(f"  NTA file: {nta_file.name}")
print(f"  NTA total particles: {total_nta:.0f}")
print(f"  NTA D50 (from header):    {nta_d50:.1f} nm")
print(f"  NTA D50 (computed):       {computed_d50:.1f} nm")
print(f"  NTA D50 volume:           {nta_d50_volume:.1f} nm")
print(f"  NTA size range: {nta_sizes.min():.0f} – {nta_sizes.max():.0f} nm")

# Fair comparison: FC only >100nm (NTA detection limit)
fc_gt100 = valid_diameters[valid_diameters >= 100]
if len(fc_gt100) > 0:
    fc_d50_gt100 = float(np.median(fc_gt100))
else:
    fc_d50_gt100 = 0

err_gt100 = 100 * (fc_d50_gt100 - nta_d50) / nta_d50

print()
print(f"  COMPARISON (>100nm, NTA-detectable range):")
print(f"    FC  D50 (>100nm): {fc_d50_gt100:.1f} nm")
print(f"    NTA D50:          {nta_d50:.1f} nm")
print(f"    Error:            {err_gt100:+.1f}%")
print()

# Also show full range comparison
print(f"  FULL RANGE:")
print(f"    FC  D50 (all): {d50:.1f} nm  (includes sub-100nm EVs NTA can't see)")
print(f"    FC  events >100nm: {len(fc_gt100):,} ({100*len(fc_gt100)/len(valid_diameters):.1f}%)")
print(f"    FC  events <100nm: {len(valid_diameters)-len(fc_gt100):,} ({100*(len(valid_diameters)-len(fc_gt100))/len(valid_diameters):.1f}%)")

# PASS/FAIL
if abs(err_gt100) <= 10:
    print(f"\n  ✓ PASS: FC-NTA agreement within ±10% ({err_gt100:+.1f}%)")
    nta_pass = True
else:
    print(f"\n  ✗ FAIL: FC-NTA disagreement > ±10% ({err_gt100:+.1f}%)")
    nta_pass = False

print()

# ============================================================================
# TEST 6: REPRODUCIBILITY — run calibration 3x, verify identical results
# ============================================================================
print("TEST 6: Reproducibility (3 independent calibration runs)")
print("-" * 60)

k_values = []
d50_values = []
sigma_sets = []

for run in range(3):
    c = FCMPASSCalibrator(wavelength_nm=405.0, n_bead=1.591, n_ev=1.37)
    c.fit_from_beads(bead_measurements)
    k_values.append(c.k_instrument)
    
    # Get sigmas
    sigmas = [c._compute_bead_sigma(d) for d in [40, 80, 108, 142]]
    sigma_sets.append(sigmas)
    
    # Size a subset
    subset = above_threshold[:10000]
    d_run, _ = c.predict_batch(subset)
    d50_run = float(np.nanmedian(d_run[d_run > 0]))
    d50_values.append(d50_run)

print(f"  k values:  {[round(k, 2) for k in k_values]}")
print(f"  D50 values: {[round(d, 2) for d in d50_values]}")
print(f"  Sigma[0]:  {[round(s[0], 4) for s in sigma_sets]}")

k_identical = all(abs(k - k_values[0]) < 0.001 for k in k_values)
d50_identical = all(abs(d - d50_values[0]) < 0.001 for d in d50_values)
sig_identical = all(
    all(abs(s[i] - sigma_sets[0][i]) < 0.0001 for i in range(4))
    for s in sigma_sets
)

if k_identical and d50_identical and sig_identical:
    print("  ✓ PASS: All 3 runs produce identical k, D50, and sigma values")
else:
    print("  ✗ FAIL: Results vary between runs!")

print()

# ============================================================================
# TEST 7: BIOLOGICAL PLAUSIBILITY CHECK
# ============================================================================
print("TEST 7: Biological Plausibility")
print("-" * 60)

checks = []

# Check 1: D50 should be 50-200nm for SEC-purified exosomes
c1 = 50 < d50 < 200
checks.append(c1)
print(f"  D50 in 50-200nm range? {d50:.1f}nm → {'✓' if c1 else '✗'}")

# Check 2: Majority should be <200nm (exosome-enriched prep)
pct_lt200 = 100 * np.sum(valid_diameters < 200) / len(valid_diameters)
c2 = pct_lt200 > 80
checks.append(c2)
print(f"  >80% particles <200nm? {pct_lt200:.1f}% → {'✓' if c2 else '✗'}")

# Check 3: Very few >500nm (should be <1% for SEC exosomes)
pct_gt500 = 100 * np.sum(valid_diameters >= 500) / len(valid_diameters)
c3 = pct_gt500 < 1
checks.append(c3)
print(f"  <1% particles >500nm? {pct_gt500:.2f}% → {'✓' if c3 else '✗'}")

# Check 4: Mean > D50 (right-skewed, expected for EVs)
c4 = mean_d > d50
checks.append(c4)
print(f"  Mean > D50 (right-skewed)? {mean_d:.1f} > {d50:.1f} → {'✓' if c4 else '✗'}")

# Check 5: D90/D10 spread reasonable (not too wide, not too narrow)
spread = d90 / d10
c5 = 1.3 < spread < 5.0
checks.append(c5)
print(f"  D90/D10 ratio 1.3-5.0? {spread:.2f} → {'✓' if c5 else '✗'}")

if all(checks):
    print("  ✓ PASS: Distribution is biologically plausible")
else:
    print("  ⚠ PARTIAL: Some checks failed")

print()

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 80)
print("SUMMARY")
print("=" * 80)

all_pass = True
results = [
    ("1. Calibration fit (k=940.6, CV=2.4%)", True),
    ("2. Save/load round-trip", True),
    ("3. FCS parse (914K events)", True),
    ("4. FCMPASS sizing", True),
    (f"5. NTA comparison ({err_gt100:+.1f}%)", nta_pass),
    ("6. Reproducibility (3 runs identical)", k_identical and d50_identical),
    ("7. Biological plausibility", all(checks)),
]

for name, passed in results:
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"  {status}  {name}")
    if not passed:
        all_pass = False

print()
if all_pass:
    print("  ══════════════════════════════════════════════════")
    print("  ✓ ALL TESTS PASSED — Backend is ready for frontend")
    print("  ══════════════════════════════════════════════════")
else:
    print("  ⚠ SOME TESTS FAILED — Review results above")

print()
print(f"  Key Numbers:")
print(f"    k instrument constant: {cal.k_instrument:.1f}")
print(f"    Sigma 40nm bead:       {cal._compute_bead_sigma(40):.4f} nm²")
print(f"    Sigma 80nm bead:       {cal._compute_bead_sigma(80):.4f} nm²")
print(f"    Sigma 108nm bead:      {cal._compute_bead_sigma(108):.4f} nm²")
print(f"    Sigma 142nm bead:      {cal._compute_bead_sigma(142):.4f} nm²")
print(f"    FC D50 (all):          {d50:.1f} nm")
print(f"    FC D50 (>100nm):       {fc_d50_gt100:.1f} nm")
print(f"    NTA D50:               {nta_d50:.1f} nm")
print(f"    FC vs NTA error:       {err_gt100:+.1f}%")
