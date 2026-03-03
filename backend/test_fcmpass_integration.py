"""Test FCMPASS calibration integration with API layer."""
import sys
sys.path.insert(0, ".")

from src.physics.bead_calibration import (
    save_fcmpass_calibration, get_fcmpass_calibration, get_fcmpass_calibration_status,
    CALIBRATION_DIR, FCMPASS_CALIBRATION_FILE
)
from src.physics.mie_scatter import FCMPASSCalibrator
import numpy as np

print("=" * 60)
print("FCMPASS Integration Test")
print("=" * 60)

# 1. Create and fit calibrator
print("\n1. Fitting FCMPASS calibrator...")
cal = FCMPASSCalibrator(wavelength_nm=405.0, n_bead=1.591, n_ev=1.37)
cal.fit_from_beads({40: 1888, 80: 102411, 108: 565342, 142: 2132067})
print(f"   k={cal.k_instrument:.1f}, CV={cal.k_cv_pct:.1f}%")
assert cal.calibrated, "Calibrator should be fitted"
assert cal.k_cv_pct < 5.0, f"CV too high: {cal.k_cv_pct:.1f}%"

# 2. Save
print("\n2. Saving to disk...")
path = save_fcmpass_calibration(cal)
print(f"   Saved to: {path}")

# 3. Load
print("\n3. Loading from disk...")
loaded = get_fcmpass_calibration()
assert loaded is not None, "Should load successfully"
assert loaded.calibrated, "Loaded calibrator should be fitted"
print(f"   Loaded: k={loaded.k_instrument:.1f}, CV={loaded.k_cv_pct:.1f}%")

# 4. Status
print("\n4. Getting status...")
status = get_fcmpass_calibration_status()
print(f"   Status: {status['status']}")
print(f"   Message: {status['message']}")
assert status['calibrated'], "Status should show calibrated"

# 5. Self-consistency check (k consistency, NOT diameter recovery)
# NOTE: predict_batch uses EV RI (1.37), NOT bead RI (1.634)
# So bead AU → EV-equivalent diameter, which is different from bead diameter
# The correct self-consistency check is k value consistency (CV < 5%)
print("\n5. k-value consistency check...")
print(f"   k = {loaded.k_instrument:.1f} ± {loaded.k_std:.1f} (CV={loaded.k_cv_pct:.1f}%)")
assert loaded.k_cv_pct < 5.0, f"k CV too high: {loaded.k_cv_pct:.1f}%"
# Also verify bead-specific prediction (AU → EV-equivalent d is monotonic)
bead_au = np.array([1888, 102411, 565342, 2132067])
diameters, in_range = loaded.predict_batch(bead_au)
for au, d in zip(bead_au, diameters):
    print(f"   AU={au:>10.0f} → EV-equivalent d={d:.1f}nm")
assert all(diameters[i] < diameters[i+1] for i in range(len(diameters)-1)), "Diameters must be monotonic"

# 6. Predict EV sample
print("\n6. EV sample sizing test...")
ev_au = np.random.uniform(1000, 500000, 1000)
ev_diameters, ev_in_range = loaded.predict_batch(ev_au)
valid = ~np.isnan(ev_diameters) & (ev_diameters > 0)
print(f"   Valid: {valid.sum()}/{len(ev_au)}")
print(f"   D50: {np.median(ev_diameters[valid]):.1f}nm")
print(f"   Range: {ev_diameters[valid].min():.1f} - {ev_diameters[valid].max():.1f}nm")

# 7. Diagnostics
print("\n7. Diagnostics...")
diag = loaded.get_diagnostics()
print(f"   Method: {diag['method']}")
print(f"   k: {diag['k_instrument']:.1f}")
print(f"   n_bead: {diag['n_bead']:.4f}")
print(f"   n_ev: {diag['n_ev']:.2f}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED!")
print("=" * 60)
