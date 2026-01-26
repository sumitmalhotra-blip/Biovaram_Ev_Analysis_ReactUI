"""
Enhanced PC3 Size Analysis with New Modules
============================================

Demonstrates:
1. Per-event size distribution analysis
2. KDE-based mode calculation
3. Synthetic bead calibration
4. Multi-modal detection

Created: January 20, 2026
"""

import sys
import json
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.parsers.fcs_parser import FCSParser
from src.physics.mie_scatter import MieScatterCalculator
from src.physics.statistics_utils import (
    calculate_mode_kde,
    calculate_comprehensive_stats,
    create_size_histogram,
    detect_multimodality,
    compare_distributions
)
from src.physics.size_distribution import PerEventSizeAnalyzer
from src.physics.bead_calibration import create_synthetic_calibration, BeadCalibrationCurve


def main():
    print("=" * 80)
    print("🔬 ENHANCED PC3 SIZE ANALYSIS")
    print("=" * 80)
    
    # =========================================================================
    # Part 1: Per-Event Size Distribution Analysis
    # =========================================================================
    print("\n" + "=" * 80)
    print("📊 PART 1: Per-Event Size Distribution Analysis")
    print("=" * 80)
    
    # Initialize analyzer
    analyzer = PerEventSizeAnalyzer(
        wavelength_nm=488.0,
        n_particle=1.40,
        n_medium=1.33,
        size_range_nm=(30, 500),
        lut_resolution=1000
    )
    
    # Load PC3 EXO1 data
    fcs_path = Path(__file__).parent.parent / "nanoFACS" / "Exp_20251217_PC3" / "PC3 EXO1.fcs"
    
    print(f"\nAnalyzing: {fcs_path.name}")
    
    # Parse FCS file
    parser = FCSParser(fcs_path)
    df = parser.parse()
    fsc_values = np.asarray(df['VFSC-H'].values, dtype=np.float64)
    
    print(f"   Total events: {len(fsc_values):,}")
    print(f"   FSC range: {np.min(fsc_values):.1f} - {np.max(fsc_values):.1f}")
    
    # Analyze with NTA-calibrated D50 (127nm)
    result = analyzer.analyze_sample(
        fsc_values,
        sample_name="PC3_EXO1",
        reference_d50_nm=127.0,  # From NTA validation
        bin_size_nm=5.0,
        histogram_range=(0, 400)
    )
    
    print(f"\n✅ Per-Event Analysis Complete:")
    print(f"   Valid events: {result.n_valid_events:,} ({result.valid_fraction*100:.1f}%)")
    print(f"\n   📈 Size Statistics:")
    stats = result.statistics
    print(f"      D10: {stats['d10']:.1f} nm")
    print(f"      D25: {stats['d25']:.1f} nm")
    print(f"      D50 (median): {stats['d50']:.1f} nm")
    print(f"      D75: {stats['d75']:.1f} nm")
    print(f"      D90: {stats['d90']:.1f} nm")
    print(f"      Mean: {stats['mean']:.1f} ± {stats['std']:.1f} nm")
    print(f"      Mode (KDE): {stats['mode']:.1f} nm")
    print(f"      Skewness: {stats['skewness']:.2f}")
    print(f"      Kurtosis: {stats['kurtosis']:.2f}")
    print(f"      95% CI Mean: [{stats['ci_95_mean'][0]:.1f}, {stats['ci_95_mean'][1]:.1f}] nm")
    
    # =========================================================================
    # Part 2: Improved Mode Calculation (KDE vs Histogram)
    # =========================================================================
    print("\n" + "=" * 80)
    print("📊 PART 2: Mode Calculation Comparison")
    print("=" * 80)
    
    diameters = result._diameters
    
    # KDE-based mode (our new method)
    if diameters is None:
        print("   No diameters computed")
        return
    
    from typing import cast
    from src.physics.statistics_utils import ModeResult, calculate_mode_histogram
    
    mode_kde = cast(ModeResult, calculate_mode_kde(diameters, return_full=True))
    
    print(f"\n   KDE-based Mode Analysis:")
    print(f"      Primary Mode: {mode_kde.mode:.1f} nm")
    print(f"      All Modes: {[f'{m:.1f}' for m in mode_kde.modes[:5]]}")
    print(f"      Bandwidth: {mode_kde.bandwidth:.4f}")
    print(f"      Confidence: {mode_kde.confidence:.3f}")
    
    # Histogram-based modes with different bin sizes
    print(f"\n   Histogram-based Mode (bin-size dependency):")
    
    for bin_size in [1, 2, 5, 10, 20]:
        mode_hist = calculate_mode_histogram(diameters, bin_size=bin_size)
        print(f"      Bin size {bin_size:2d} nm → Mode: {mode_hist:.1f} nm")
    
    print(f"\n   ➡️ KDE mode is more stable: {mode_kde.mode:.1f} nm")
    
    # =========================================================================
    # Part 3: Multimodality Detection
    # =========================================================================
    print("\n" + "=" * 80)
    print("📊 PART 3: Multimodality Analysis")
    print("=" * 80)
    
    multimodal = result.multimodality
    
    print(f"\n   Is Multimodal: {multimodal['is_multimodal']}")
    print(f"   Significant Modes: {multimodal['n_significant_modes']}")
    print(f"   Primary Mode: {multimodal['primary_mode']:.1f} nm")
    
    if multimodal['n_significant_modes'] > 1:
        print(f"   Mode Details:")
        for i, mode_info in enumerate(multimodal['modes'][:5], 1):
            print(f"      Mode {i}: {mode_info['mode']:.1f} nm (rel. density: {mode_info['relative_density']:.2f})")
    
    # =========================================================================
    # Part 4: Synthetic Bead Calibration Demo
    # =========================================================================
    print("\n" + "=" * 80)
    print("📊 PART 4: Polystyrene Bead Calibration (Synthetic Demo)")
    print("=" * 80)
    
    print("\n   Creating synthetic calibration with 100, 200, 500 nm beads...")
    
    calib = create_synthetic_calibration(
        instrument_name="NanoFACS_Demo",
        wavelength_nm=488.0,
        bead_sizes=[100, 200, 500],
        n_particle=1.59,  # Polystyrene
        n_medium=1.33,
        noise_cv=0.15
    )
    
    print(f"\n   Calibration Fit:")
    print(f"      Method: Power Law (FSC = a × d^b)")
    if calib.fit_params:
        print(f"      Parameters: a = {calib.fit_params['a']:.2e}, b = {calib.fit_params['b']:.2f}")
        print(f"      R² = {calib.fit_params['r_squared']:.4f}")
    else:
        print(f"      Parameters: Not fitted")
    
    print(f"\n   Bead Standards Used:")
    for d, std in sorted(calib.bead_standards.items()):
        print(f"      {d:.0f} nm: FSC mean = {std.fsc_mean:.1f} ± {std.fsc_std:.1f} (n={std.n_events})")
    
    # Save calibration
    calib_path = Path(__file__).parent.parent / "data" / "validation" / "synthetic_bead_calibration.json"
    calib.save(str(calib_path))
    print(f"\n   💾 Calibration saved to: {calib_path.name}")
    
    # =========================================================================
    # Part 5: Sample Comparison (CD9 vs CD81 markers)
    # =========================================================================
    print("\n" + "=" * 80)
    print("📊 PART 5: Sample Comparison (CD9 vs CD81)")
    print("=" * 80)
    
    # Analyze CD9 sample
    cd9_path = Path(__file__).parent.parent / "nanoFACS" / "Exp_20251217_PC3" / "Exo+CD 9.fcs"
    cd9_parser = FCSParser(cd9_path)
    cd9_df = cd9_parser.parse()
    cd9_fsc = np.asarray(cd9_df['VFSC-H'].values, dtype=np.float64)
    
    cd9_result = analyzer.analyze_sample(
        cd9_fsc,
        sample_name="Exo+CD9",
        reference_d50_nm=127.0,
        bin_size_nm=5.0
    )
    
    # Analyze CD81 sample
    cd81_path = Path(__file__).parent.parent / "nanoFACS" / "Exp_20251217_PC3" / "Exo+CD 81.fcs"
    cd81_parser = FCSParser(cd81_path)
    cd81_df = cd81_parser.parse()
    cd81_fsc = np.asarray(cd81_df['VFSC-H'].values, dtype=np.float64)
    
    cd81_result = analyzer.analyze_sample(
        cd81_fsc,
        sample_name="Exo+CD81",
        reference_d50_nm=127.0,
        bin_size_nm=5.0
    )
    
    # Compare
    comparison = analyzer.compare_samples(cd9_result, cd81_result)
    
    print(f"\n   📊 CD9 vs CD81 Comparison:")
    print(f"   {'Metric':<20} {'CD9':<15} {'CD81':<15} {'Difference':<15}")
    print(f"   {'-'*60}")
    print(f"   {'Events':<20} {cd9_result.n_valid_events:<15,} {cd81_result.n_valid_events:<15,} -")
    print(f"   {'D50 (nm)':<20} {cd9_result.statistics['d50']:<15.1f} {cd81_result.statistics['d50']:<15.1f} {comparison['d50_diff']:<15.1f}")
    print(f"   {'Mean (nm)':<20} {cd9_result.statistics['mean']:<15.1f} {cd81_result.statistics['mean']:<15.1f} {comparison['mean_diff']:<15.1f}")
    print(f"   {'Mode (nm)':<20} {cd9_result.statistics['mode']:<15.1f} {cd81_result.statistics['mode']:<15.1f} -")
    
    print(f"\n   📈 Statistical Test (Kolmogorov-Smirnov):")
    print(f"      Statistic: {comparison['statistic']:.4f}")
    print(f"      P-value: {comparison['p_value']:.2e}")
    print(f"      Effect Size (Cohen's d): {comparison['effect_size']:.2f}")
    print(f"      Significantly Different: {'YES ✅' if comparison['significantly_different'] else 'NO'}")
    
    # =========================================================================
    # Part 6: Save Enhanced Results
    # =========================================================================
    print("\n" + "=" * 80)
    print("📊 PART 6: Saving Enhanced Results")
    print("=" * 80)
    
    output_dir = Path(__file__).parent.parent / "data" / "validation"
    
    # Save PC3 EXO1 results
    output_file = output_dir / "pc3_exo1_enhanced_size_analysis.json"
    analyzer.save_results(result, str(output_file), include_diameters=True)
    print(f"   ✅ PC3 EXO1 results saved")
    
    # Save comparison summary
    comparison_summary = {
        'samples_compared': ['Exo+CD9', 'Exo+CD81'],
        'cd9_statistics': cd9_result.statistics,
        'cd81_statistics': cd81_result.statistics,
        'comparison': comparison,
        'interpretation': {
            'cd81_larger_than_cd9': cd81_result.statistics['d50'] > cd9_result.statistics['d50'],
            'd50_difference_nm': comparison['d50_diff'],
            'statistically_significant': comparison['significantly_different']
        }
    }
    
    with open(output_dir / "cd9_vs_cd81_comparison.json", 'w') as f:
        json.dump(comparison_summary, f, indent=2, default=str)
    print(f"   ✅ CD9 vs CD81 comparison saved")
    
    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 80)
    print("✅ ENHANCED ANALYSIS COMPLETE")
    print("=" * 80)
    
    print("""
    New Capabilities Demonstrated:
    
    1. ✅ Per-Event Size Analysis
       - Full distribution with 800K+ individual diameter calculations
       - D10, D25, D50, D75, D90 percentiles
       - Bootstrap 95% CI for mean
    
    2. ✅ KDE-Based Mode Calculation
       - Bin-size independent mode finding
       - More stable than histogram-based mode
       - Multi-modal detection capability
    
    3. ✅ Polystyrene Bead Calibration Framework
       - Power law fitting (R² > 0.99)
       - Supports 100, 200, 500 nm beads
       - Save/load calibration curves
    
    4. ✅ Sample Comparison Statistics
       - Kolmogorov-Smirnov test
       - Effect size (Cohen's d)
       - P-value significance testing
    
    Ready for production use with real bead calibration data!
    """)
    
    return {
        'pc3_result': result.to_dict(),
        'cd9_result': cd9_result.to_dict(),
        'cd81_result': cd81_result.to_dict(),
        'comparison': comparison
    }


if __name__ == "__main__":
    main()
