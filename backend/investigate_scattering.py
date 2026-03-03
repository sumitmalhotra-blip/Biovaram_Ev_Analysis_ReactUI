"""Quick investigation: Which scattering model best matches the AU data?"""

import numpy as np
import miepython

bead_diameters = [40, 80, 108, 142]
bead_ri = 1.591
medium_ri = 1.33
m = complex(bead_ri / medium_ri, 0)

au_vssc = [374.7, 3504.9, 102188.8, 2128442.2]  # 405nm
au_bssc = [448.5, 662.1, 20626.0, 508261.2]      # 488nm

for wl, au_vals, ch_name in [(405.0, au_vssc, "VSSC1-H"), (488.0, au_bssc, "BSSC-H")]:
    print(f"\n{'='*70}")
    print(f"  {ch_name} ({wl}nm)")
    print(f"{'='*70}")
    
    sigma_back_list = []
    sigma_90_list = []
    sigma_sca_list = []
    
    for d, au in zip(bead_diameters, au_vals):
        r = d / 2.0
        geo = np.pi * r**2
        x = np.pi * d / wl
        
        result = miepython.efficiencies(m, d, wl, n_env=medium_ri)
        qext, qsca, qback, g = result
        
        sigma_back = float(qback * geo)
        sigma_sca = float(qsca * geo)
        
        # 90-degree scattering intensity
        s90 = float(miepython.i_unpolarized(m, x, 0))  # mu=cos(90)=0
        
        sigma_back_list.append(sigma_back)
        sigma_90_list.append(s90)
        sigma_sca_list.append(sigma_sca)
        
        print(f"  d={d:>4d}nm  AU={au:>12.1f}  Qback*A={sigma_back:>10.4f}  S90={s90:>10.6f}  Qsca*A={sigma_sca:>10.4f}")
    
    # Test linearity: AU = k * sigma should have constant k
    print(f"\n  Linearity check (AU / theory):")
    for model_name, theory_vals in [("Qback*A", sigma_back_list), ("S(90)", sigma_90_list), ("Qsca*A", sigma_sca_list)]:
        ratios = [au / t if t > 0 else float('inf') for au, t in zip(au_vals, theory_vals)]
        ratio_range = max(ratios) / min(ratios) if min(ratios) > 0 else float('inf')
        print(f"    {model_name:>8s}: ratios = {', '.join(f'{r:.0f}' for r in ratios)}  (range: {ratio_range:.1f}x)")
    
    # Power law fit: AU = 10^b * d^a  =>  log(AU) = a*log(d) + b
    print(f"\n  Direct power law AU vs d:")
    log_d = np.log10(bead_diameters)
    log_au = np.log10(au_vals)
    coeffs_1 = np.polyfit(log_d, log_au, 1)
    coeffs_2 = np.polyfit(log_d, log_au, 2)
    
    print(f"    Linear: AU = 10^({coeffs_1[1]:.3f}) * d^({coeffs_1[0]:.3f})")
    for d, au in zip(bead_diameters, au_vals):
        pred = 10 ** np.polyval(coeffs_1, np.log10(d))
        print(f"      d={d}nm: pred={pred:.0f}, actual={au:.0f}, err={100*(pred-au)/au:+.1f}%")
    
    print(f"    Quadratic in log-log:")
    for d, au in zip(bead_diameters, au_vals):
        pred = 10 ** np.polyval(coeffs_2, np.log10(d))
        print(f"      d={d}nm: pred={pred:.0f}, actual={au:.0f}, err={100*(pred-au)/au:+.1f}%")
    
    # Cubic (exact fit through 4 points)
    coeffs_3 = np.polyfit(log_d, log_au, 3)
    print(f"    Cubic in log-log (exact for 4 pts):")
    for d, au in zip(bead_diameters, au_vals):
        pred = 10 ** np.polyval(coeffs_3, np.log10(d))
        print(f"      d={d}nm: pred={pred:.0f}, actual={au:.0f}, err={100*(pred-au)/au:+.1f}%")
    
    # --- KEY: Test cubic polynomial d -> AU for inverse Mie ---
    # For AU -> diameter: invert through LUT
    print(f"\n  Inverse test: AU -> diameter using cubic interpolation")
    # Build fine LUT: diameter -> AU (using the cubic log-log fit)
    d_fine = np.linspace(30, 200, 2000)
    au_fine = 10 ** np.polyval(coeffs_3, np.log10(d_fine))
    
    # Test inversion
    for d_true, au in zip(bead_diameters, au_vals):
        best_idx = np.argmin(np.abs(au_fine - au))
        d_recovered = d_fine[best_idx]
        err = 100 * (d_recovered - d_true) / d_true
        print(f"    AU={au:.0f} -> d_recovered={d_recovered:.1f}nm (true={d_true}nm, err={err:+.1f}%)")

print("\n" + "="*70)
print("CONCLUSION: The correct approach is a direct AU -> diameter mapping")
print("using cubic polynomial in log-log space, bypassing sigma entirely.")
print("This avoids the need to model the exact detector geometry.")
print("="*70)
