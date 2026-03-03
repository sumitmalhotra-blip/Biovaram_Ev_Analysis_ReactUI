"""
Investigation: Find the SSC detector angular model that best explains the AU data.

Goal: Compute integrated Mie scatter over various angular ranges and find which
gives the most consistent AU/sigma ratio across all bead sizes.
"""

import numpy as np
import miepython

# Bead data
bead_d = [40, 80, 108, 142]
ri_bead = 1.591
ri_m = 1.33
wl_vssc = 405.0
wl_bssc = 488.0

# Measured AU (Low mix)
au_vssc = [374.7, 3504.9, 102188.8, 2128442.2]
au_bssc = [448.5, 662.1, 20626.0, 508261.2]

def integrated_scatter(diameter, wavelength, n_particle, n_medium,
                        theta_min_deg, theta_max_deg, n_points=200):
    """
    Compute integrated scattering cross-section over angular range.
    
    sigma_det = integral from theta_min to theta_max of:
        (|S1|^2 + |S2|^2) / (2*k^2) * 2*pi*sin(theta) d(theta)
    
    k = 2*pi*n_medium / lambda_vacuum
    """
    m_abs = complex(n_particle, 0)
    m_rel = complex(n_particle / n_medium, 0)
    
    # Size parameter
    x = np.pi * diameter * n_medium / wavelength
    
    # Wave number
    k = 2 * np.pi * n_medium / wavelength  # nm^-1
    
    # Integration
    thetas = np.linspace(np.radians(theta_min_deg), np.radians(theta_max_deg), n_points)
    mus = np.cos(thetas)
    
    # Get unpolarized intensity at each angle
    # miepython.i_unpolarized(m, x, mu) where m is RELATIVE index
    intensities = np.array([float(miepython.i_unpolarized(m_rel, x, mu)) for mu in mus])
    
    # Integrate: sigma = (1/k^2) * integral of I(theta) * 2*pi*sin(theta) d(theta)
    # Factor: multiply by sin(theta) * d_theta
    sin_thetas = np.sin(thetas)
    integrand = intensities * sin_thetas
    
    # Numerical integration (trapezoidal)
    d_theta = thetas[1] - thetas[0]
    integral = np.trapz(integrand, thetas)
    
    # Convert to cross-section
    sigma = (2 * np.pi / k**2) * integral  # nm^2
    
    return float(sigma)


def compute_consistency(au_vals, sigma_vals):
    """
    Compute consistency metric for AU/sigma ratios.
    Returns: ratio of max/min (1.0 = perfect consistency).
    """
    ratios = [au / s if s > 0 else 1e20 for au, s in zip(au_vals, sigma_vals)]
    if min(ratios) <= 0:
        return float('inf')
    return max(ratios) / min(ratios)


# Test various angular ranges
print("=" * 70)
print("Testing SSC detector angular models")
print("=" * 70)

angle_ranges = [
    (170, 180, "Near-backscatter"),
    (150, 180, "Wide backscatter"),
    (120, 180, "Hemisphere back"),
    (60, 120, "Side scatter ±30°"),
    (70, 110, "Side scatter ±20°"),
    (80, 100, "Side scatter ±10°"),
    (85, 95, "Side scatter ±5°"),
    (0, 180, "Full sphere"),
    (0, 30, "Near-forward"),
    (10, 50, "Forward wide"),
    (15, 150, "CytoFLEX-like wide"),
]

print(f"\n=== VSSC1-H (405nm) ===")
print(f"{'Angular Range':>25s} | {'Consistency':>12s} | {'40nm':>10s} {'80nm':>10s} {'108nm':>10s} {'142nm':>10s}")

best_consistency = float('inf')
best_range = None

for theta_min, theta_max, label in angle_ranges:
    sigmas = []
    for d in bead_d:
        s = integrated_scatter(d, wl_vssc, ri_bead, ri_m, theta_min, theta_max)
        sigmas.append(s)
    
    consistency = compute_consistency(au_vssc, sigmas)
    ratios = [au / s if s > 0 else 0 for au, s in zip(au_vssc, sigmas)]
    
    if consistency < best_consistency:
        best_consistency = consistency
        best_range = (theta_min, theta_max, label)
    
    print(f"{label:>25s} | {consistency:>12.1f}x | " +
          " ".join(f"{r:>10.1f}" for r in ratios))

print(f"\nBest range: {best_range[2]} ({best_range[0]}°-{best_range[1]}°), consistency = {best_consistency:.1f}x")

# Also test BSSC
print(f"\n=== BSSC-H (488nm) ===")
print(f"{'Angular Range':>25s} | {'Consistency':>12s} | {'40nm':>10s} {'80nm':>10s} {'108nm':>10s} {'142nm':>10s}")

for theta_min, theta_max, label in angle_ranges:
    sigmas = []
    for d in bead_d:
        s = integrated_scatter(d, wl_bssc, ri_bead, ri_m, theta_min, theta_max)
        sigmas.append(s)
    
    consistency = compute_consistency(au_bssc, sigmas)
    ratios = [au / s if s > 0 else 0 for au, s in zip(au_bssc, sigmas)]
    
    print(f"{label:>25s} | {consistency:>12.1f}x | " +
          " ".join(f"{r:>10.1f}" for r in ratios))

# Now test WITHOUT the 40nm bead (might be noise)
print(f"\n=== VSSC1-H WITHOUT 40nm (beads: 80, 108, 142nm only) ===")
print(f"{'Angular Range':>25s} | {'Consistency':>12s} | {'80nm':>10s} {'108nm':>10s} {'142nm':>10s}")

best_3 = float('inf')
best_3_range = None

for theta_min, theta_max, label in angle_ranges:
    sigmas = []
    for d in bead_d[1:]:  # Skip 40nm
        s = integrated_scatter(d, wl_vssc, ri_bead, ri_m, theta_min, theta_max)
        sigmas.append(s)
    
    consistency = compute_consistency(au_vssc[1:], sigmas)
    ratios = [au / s if s > 0 else 0 for au, s in zip(au_vssc[1:], sigmas)]
    
    if consistency < best_3:
        best_3 = consistency
        best_3_range = (theta_min, theta_max, label)
    
    print(f"{label:>25s} | {consistency:>12.1f}x | " +
          " ".join(f"{r:>10.1f}" for r in ratios))

print(f"\nBest range (3 beads): {best_3_range[2]} ({best_3_range[0]}°-{best_3_range[1]}°), consistency = {best_3:.1f}x")
