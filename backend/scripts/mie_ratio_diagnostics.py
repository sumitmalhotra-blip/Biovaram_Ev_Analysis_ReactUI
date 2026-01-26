"""
Mie Scattering Ratio Diagnostic Tool
=====================================

This script performs a detailed diagnostic analysis to understand:
1. What VSSC/BSSC ratios we're ACTUALLY measuring
2. What ratios we EXPECT based on Mie theory for different sizes
3. Why there's a mismatch between measured and theoretical values

This helps identify calibration issues and guide the multi-solution approach.

Created: January 21, 2026
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json

# Import from our standalone script
from standalone_mie_multisolution import (
    StandaloneMieCalculator,
    WavelengthDisambiguator,
    parse_fcs_file_standalone,
    identify_scatter_channels,
    LASER_CONFIGS
)

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    plt = None  # type: ignore
    HAS_MATPLOTLIB = False


def analyze_ratio_diagnostics(fcs_path: Path, sample_size: int = 5000):
    """
    Perform detailed diagnostic analysis of wavelength ratios.
    """
    print("=" * 80)
    print("🔬 RATIO DIAGNOSTIC ANALYSIS")
    print(f"   File: {fcs_path.name}")
    print("=" * 80)
    
    # Load data
    print("\n📂 Loading FCS file...")
    data, meta = parse_fcs_file_standalone(fcs_path)
    print(f"   ✅ Loaded {len(data):,} events")
    
    # Get channels
    scatter_channels = identify_scatter_channels(list(data.columns))
    
    # Extract key channels
    vssc1_col = 'VSSC1-H'
    bssc_col = 'BSSC-H'
    vfsc_col = 'VFSC-H'
    
    # Sample data
    sample_idx = np.random.choice(len(data), min(sample_size, len(data)), replace=False)
    sample = data.iloc[sample_idx]
    
    # Calculate measured ratios
    vssc1: np.ndarray = np.asarray(sample[vssc1_col].values, dtype=np.float64)
    bssc: np.ndarray = np.asarray(sample[bssc_col].values, dtype=np.float64)
    vfsc: np.ndarray = np.asarray(sample[vfsc_col].values, dtype=np.float64)
    
    # Filter positive values only
    valid: np.ndarray = (vssc1 > 0) & (bssc > 0) & (vfsc > 0)
    vssc1 = vssc1[valid]
    bssc = bssc[valid]
    vfsc = vfsc[valid]
    
    measured_ratio: np.ndarray = vssc1 / bssc
    
    print(f"\n📊 MEASURED RATIO STATISTICS (VSSC1-H / BSSC-H):")
    print(f"   N valid events: {len(measured_ratio):,}")
    print(f"   Min:    {np.min(measured_ratio):.3f}")
    print(f"   Max:    {np.max(measured_ratio):.3f}")
    print(f"   Mean:   {np.mean(measured_ratio):.3f}")
    print(f"   Median: {np.median(measured_ratio):.3f}")
    print(f"   Std:    {np.std(measured_ratio):.3f}")
    print(f"   25th percentile: {np.percentile(measured_ratio, 25):.3f}")
    print(f"   75th percentile: {np.percentile(measured_ratio, 75):.3f}")
    
    # Build theoretical ratio curve
    print("\n📐 BUILDING THEORETICAL RATIO CURVE...")
    disambiguator = WavelengthDisambiguator(n_particle=1.40, n_medium=1.33)
    
    diameters = np.arange(30, 305, 5)
    theoretical_ratios = []
    
    for d in diameters:
        r = disambiguator.calculate_theoretical_ratio(float(d), 405, 488)
        theoretical_ratios.append(r)
    
    theoretical_ratios = np.array(theoretical_ratios)
    
    print(f"\n📐 THEORETICAL RATIO VS DIAMETER:")
    print(f"   {'Diameter (nm)':<15} {'VSSC/BSSC Ratio':<20}")
    print(f"   {'-'*35}")
    for d in [30, 50, 80, 100, 120, 150, 200, 250, 300]:
        r = disambiguator.calculate_theoretical_ratio(d, 405, 488)
        print(f"   {d:<15} {r:.3f}")
    
    # Rayleigh expectation
    rayleigh_ratio = (488 / 405) ** 4
    print(f"\n📐 RAYLEIGH LIMIT (λ⁻⁴):")
    print(f"   For very small particles: (488/405)⁴ = {rayleigh_ratio:.3f}")
    
    # Compare measured to theoretical
    print("\n🔍 COMPARISON: MEASURED vs THEORETICAL")
    print("=" * 60)
    
    # What sizes would produce our measured ratios?
    print("\n   For each measured ratio, what size does Mie theory predict?")
    
    # Find where theoretical curve matches measured values
    median_ratio = np.median(measured_ratio)
    p25_ratio = np.percentile(measured_ratio, 25)
    p75_ratio = np.percentile(measured_ratio, 75)
    
    # Find sizes that match these ratios
    def find_size_for_ratio(target_ratio, diameters, ratios):
        """Find diameter(s) where theoretical ratio matches target."""
        sizes = []
        for i in range(len(diameters) - 1):
            if min(ratios[i], ratios[i+1]) <= target_ratio <= max(ratios[i], ratios[i+1]):
                # Linear interpolation
                if ratios[i+1] != ratios[i]:
                    t = (target_ratio - ratios[i]) / (ratios[i+1] - ratios[i])
                    size = diameters[i] + t * (diameters[i+1] - diameters[i])
                    sizes.append(size)
        return sizes
    
    print(f"\n   Median measured ratio: {median_ratio:.3f}")
    median_sizes = find_size_for_ratio(median_ratio, diameters, theoretical_ratios)
    print(f"   → Theoretical sizes matching this ratio: {median_sizes}")
    
    print(f"\n   25th percentile ratio: {p25_ratio:.3f}")
    p25_sizes = find_size_for_ratio(p25_ratio, diameters, theoretical_ratios)
    print(f"   → Theoretical sizes matching this ratio: {p25_sizes}")
    
    print(f"\n   75th percentile ratio: {p75_ratio:.3f}")
    p75_sizes = find_size_for_ratio(p75_ratio, diameters, theoretical_ratios)
    print(f"   → Theoretical sizes matching this ratio: {p75_sizes}")
    
    # Check for calibration offset
    print("\n" + "=" * 60)
    print("📋 CALIBRATION ANALYSIS")
    print("=" * 60)
    
    print("""
    The key question is: Why don't measured ratios match theoretical?
    
    Possible reasons:
    1. Different detector sensitivities at 405nm vs 488nm
    2. Different optical paths / collection efficiencies
    3. Background fluorescence affecting SSC channels
    4. Refractive index assumption is wrong
    5. Non-linear detector response
    
    To calibrate, we need:
    - Reference beads of KNOWN size measured at BOTH wavelengths
    - Calculate: correction_factor = (measured_ratio) / (theoretical_ratio)
    """)
    
    # Calculate what calibration factor would be needed
    # If particles are ~100nm (typical EV), what calibration makes sense?
    theoretical_100nm = disambiguator.calculate_theoretical_ratio(100, 405, 488)
    theoretical_150nm = disambiguator.calculate_theoretical_ratio(150, 405, 488)
    theoretical_200nm = disambiguator.calculate_theoretical_ratio(200, 405, 488)
    
    print(f"\n   If particles were 100nm: theoretical ratio = {theoretical_100nm:.3f}")
    print(f"   Measured median ratio = {median_ratio:.3f}")
    print(f"   Implied calibration factor (100nm assumption) = {median_ratio/theoretical_100nm:.3f}")
    
    print(f"\n   If particles were 150nm: theoretical ratio = {theoretical_150nm:.3f}")
    print(f"   Implied calibration factor (150nm assumption) = {median_ratio/theoretical_150nm:.3f}")
    
    print(f"\n   If particles were 200nm: theoretical ratio = {theoretical_200nm:.3f}")
    print(f"   Implied calibration factor (200nm assumption) = {median_ratio/theoretical_200nm:.3f}")
    
    # Generate plots
    if HAS_MATPLOTLIB and plt is not None:
        print("\n📈 Generating diagnostic plots...")
        
        fig, axes = plt.subplots(2, 3, figsize=(16, 10))
        
        # Plot 1: Histogram of measured ratios
        ax1 = axes[0, 0]
        ax1.hist(measured_ratio, bins=100, color='steelblue', edgecolor='white', alpha=0.7)
        ax1.axvline(median_ratio, color='red', linestyle='--', linewidth=2, 
                   label=f'Median: {median_ratio:.2f}')
        ax1.axvline(rayleigh_ratio, color='green', linestyle=':', linewidth=2,
                   label=f'Rayleigh limit: {rayleigh_ratio:.2f}')
        ax1.set_xlabel('VSSC1-H / BSSC-H Ratio')
        ax1.set_ylabel('Count')
        ax1.set_title('Distribution of Measured Ratios')
        ax1.legend()
        ax1.set_xlim(0, 15)
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Theoretical ratio vs diameter
        ax2 = axes[0, 1]
        ax2.plot(diameters, theoretical_ratios, 'b-', linewidth=2)
        ax2.axhline(median_ratio, color='red', linestyle='--', alpha=0.7,
                   label=f'Measured median: {median_ratio:.2f}')
        ax2.axhline(rayleigh_ratio, color='green', linestyle=':', alpha=0.7,
                   label='Rayleigh limit')
        ax2.fill_between(diameters, p25_ratio, p75_ratio, alpha=0.2, color='red',
                        label='Measured IQR')
        ax2.set_xlabel('Particle Diameter (nm)')
        ax2.set_ylabel('Theoretical VSSC/BSSC Ratio')
        ax2.set_title('Theoretical Ratio vs Particle Size')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(0, 10)
        
        # Plot 3: FSC vs measured ratio (colored by density)
        ax3 = axes[0, 2]
        # Use hexbin for density
        hb = ax3.hexbin(vfsc, measured_ratio, gridsize=50, cmap='viridis', 
                       mincnt=1, yscale='linear')
        ax3.axhline(rayleigh_ratio, color='white', linestyle=':', linewidth=2)
        ax3.set_xlabel('VFSC-H')
        ax3.set_ylabel('VSSC1-H / BSSC-H Ratio')
        ax3.set_title('FSC vs Ratio (Density Plot)')
        ax3.set_ylim(0, 15)
        ax3.set_xscale('log')
        plt.colorbar(hb, ax=ax3, label='Count')
        
        # Plot 4: VSSC vs BSSC scatter
        ax4 = axes[1, 0]
        ax4.scatter(bssc, vssc1, s=1, alpha=0.1, c='blue')
        # Add expected relationship line for different sizes
        bssc_range = np.linspace(1, float(np.percentile(bssc, 99)), 100)
        for d, color, label in [(50, 'green', '50nm'), (100, 'orange', '100nm'), 
                                 (150, 'red', '150nm'), (200, 'purple', '200nm')]:
            r = disambiguator.calculate_theoretical_ratio(float(d), 405, 488)
            ax4.plot(bssc_range, bssc_range * r, color=color, linestyle='--',
                    linewidth=2, label=f'{label} (r={r:.2f})')
        ax4.set_xlabel('BSSC-H (488nm)')
        ax4.set_ylabel('VSSC1-H (405nm)')
        ax4.set_title('VSSC vs BSSC Scatter')
        ax4.legend(fontsize=8)
        ax4.set_xlim(0, float(np.percentile(bssc, 99)))
        ax4.set_ylim(0, float(np.percentile(vssc1, 99)))
        ax4.grid(True, alpha=0.3)
        
        # Plot 5: Check if ratio correlates with FSC (size)
        ax5 = axes[1, 1]
        # Bin by FSC and show ratio distribution
        fsc_bins = np.percentile(vfsc, np.arange(0, 101, 10))
        ratio_medians = []
        ratio_q1 = []
        ratio_q3 = []
        fsc_centers = []
        
        for i in range(len(fsc_bins)-1):
            mask = (vfsc >= fsc_bins[i]) & (vfsc < fsc_bins[i+1])
            if np.sum(mask) > 10:
                fsc_centers.append((fsc_bins[i] + fsc_bins[i+1]) / 2)
                ratio_medians.append(np.median(measured_ratio[mask]))
                ratio_q1.append(np.percentile(measured_ratio[mask], 25))
                ratio_q3.append(np.percentile(measured_ratio[mask], 75))
        
        ax5.errorbar(fsc_centers, ratio_medians, 
                    yerr=[np.array(ratio_medians)-np.array(ratio_q1), 
                          np.array(ratio_q3)-np.array(ratio_medians)],
                    fmt='o-', color='blue', capsize=3)
        ax5.axhline(rayleigh_ratio, color='green', linestyle=':', label='Rayleigh')
        ax5.set_xlabel('VFSC-H (binned)')
        ax5.set_ylabel('Median VSSC/BSSC Ratio')
        ax5.set_title('Does Ratio Depend on FSC? (Should for Mie)')
        ax5.legend()
        ax5.grid(True, alpha=0.3)
        ax5.set_xscale('log')
        
        # Plot 6: What the data suggests
        ax6 = axes[1, 2]
        ax6.text(0.5, 0.95, "KEY OBSERVATIONS", fontsize=14, fontweight='bold',
                transform=ax6.transAxes, ha='center', va='top')
        
        observations = f"""
• Measured VSSC/BSSC ratio: {median_ratio:.2f} (median)
• Rayleigh limit (405/488)⁴: {rayleigh_ratio:.2f}
• Measured ratio > Rayleigh suggests:
  - Particles are small (Rayleigh regime)
  - OR detector calibration differs

• If particles are truly ~100nm (typical EVs):
  - Expected ratio: {theoretical_100nm:.2f}
  - Measured/Expected: {median_ratio/theoretical_100nm:.2f}x

• Calibration factor needed:
  - ~{median_ratio/theoretical_100nm:.1f}x for 100nm assumption
  - ~{median_ratio/theoretical_200nm:.1f}x for 200nm assumption

• Does ratio correlate with FSC?
  - Strong correlation → Mie working
  - Weak correlation → Calibration issue
"""
        ax6.text(0.5, 0.85, observations, fontsize=10, family='monospace',
                transform=ax6.transAxes, ha='center', va='top')
        ax6.axis('off')
        
        plt.tight_layout()
        
        output_dir = fcs_path.parent / 'mie_analysis'
        output_dir.mkdir(parents=True, exist_ok=True)
        plot_file = output_dir / f'{fcs_path.stem}_ratio_diagnostics.png'
        plt.savefig(plot_file, dpi=150)
        plt.close()
        print(f"   📊 Diagnostic plot saved to: {plot_file}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 DIAGNOSTIC SUMMARY")
    print("=" * 80)
    print(f"""
    The measured VSSC/BSSC ratio of {median_ratio:.2f} is:
    
    • {median_ratio/rayleigh_ratio:.1f}x higher than Rayleigh limit ({rayleigh_ratio:.2f})
    
    This could mean:
    1. Particles are in the Rayleigh regime (very small, <100nm)
       → But FSC values don't support this (they suggest larger particles)
       
    2. The 405nm detector is more sensitive than theoretical
       → This is common! Violet SSC is often boosted for small particle detection
       
    3. There's wavelength-dependent background/noise
       → Check if noise floor differs between VSSC and BSSC
    
    RECOMMENDATION:
    → Use bead calibration data to determine the actual calibration factor
    → Apply: corrected_ratio = measured_ratio / calibration_factor
    → Then use corrected ratio for size disambiguation
    """)
    
    return {
        'median_ratio': float(median_ratio),
        'rayleigh_ratio': float(rayleigh_ratio),
        'ratio_iqr': (float(p25_ratio), float(p75_ratio)),
        'theoretical_100nm': float(theoretical_100nm),
        'theoretical_150nm': float(theoretical_150nm),
        'theoretical_200nm': float(theoretical_200nm)
    }


if __name__ == '__main__':
    backend_path = Path(__file__).parent.parent
    fcs_path = backend_path / 'nanoFACS' / 'Exp_20251217_PC3' / 'PC3 EXO1.fcs'
    
    if not fcs_path.exists():
        print(f"❌ File not found: {fcs_path}")
        sys.exit(1)
    
    analyze_ratio_diagnostics(fcs_path)
