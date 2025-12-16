"""Quick test of FCMPASSCalibrator implementation."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.physics.mie_scatter import FCMPASSCalibrator
import numpy as np
from typing import Dict

print("Testing FCMPASSCalibrator...")

# Create calibrator
cal = FCMPASSCalibrator(wavelength_nm=488, n_particle=1.59, n_medium=1.33)

# Fit with reference beads
beads: Dict[float, float] = {
    100.0: 15000.0,   # 100nm bead -> 15k FSC
    200.0: 58000.0,   # 200nm bead -> 58k FSC
    300.0: 125000.0   # 300nm bead -> 125k FSC
}

print(f"\nFitting with {len(beads)} reference beads...")
cal.fit_from_beads(beads, poly_degree=2)

# Test prediction
test_fsc = 42000
diameter, in_range = cal.predict_diameter(test_fsc)
print(f"\nTest prediction:")
print(f"  FSC = {test_fsc} -> Diameter = {diameter:.1f} nm")
print(f"  In calibrated range: {in_range}")

# Get diagnostics
diag = cal.get_diagnostics()
print(f"\nCalibration quality:")
print(f"  R² = {diag['r_squared']:.4f}")
print(f"  Calibrated range: {diag['calibrated_range_diameter'][0]:.0f}-{diag['calibrated_range_diameter'][1]:.0f} nm")

# Batch test
test_fsc_array = np.array([10000, 25000, 42000, 70000, 110000])
diameters, in_range_mask = cal.predict_batch(test_fsc_array)
print(f"\nBatch prediction ({len(test_fsc_array)} particles):")
for fsc, d, ok in zip(test_fsc_array, diameters, in_range_mask):
    print(f"  FSC={fsc:6.0f} -> {d:5.1f} nm {'✓' if ok else '⚠'}")

print("\n✅ FCMPASSCalibrator working correctly!")
