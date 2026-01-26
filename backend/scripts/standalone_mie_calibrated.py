"""
Calibrated Mie Scattering Multi-Solution Size Calculator
==========================================================

This is the CALIBRATED version of the multi-solution analyzer.
It includes a calibration factor to correct for detector sensitivity differences.

Based on diagnostic analysis:
- Measured VSSC/BSSC ratio = ~4.6
- Theoretical maximum (Rayleigh) = ~2.1
- Implied detector calibration factor = ~2.2x

This means the 405nm detector is ~2.2x more sensitive than expected relative to 488nm.

Usage:
    python standalone_mie_calibrated.py <fcs_file_path> [calibration_factor]
    
Example:
    python standalone_mie_calibrated.py "nanoFACS/Exp_20251217_PC3/PC3 EXO1.fcs" 2.2

Created: January 21, 2026
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import json

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    plt = None  # type: ignore
    HAS_MATPLOTLIB = False

try:
    import miepython
except ImportError:
    print("❌ miepython required: pip install miepython")
    sys.exit(1)


# =============================================================================
# CALIBRATION CONSTANTS
# =============================================================================

# Default calibration factor for VSSC/BSSC ratio
# This corrects for the 405nm detector being more sensitive than expected
DEFAULT_CALIBRATION_FACTOR = 2.2

# Expected EV size range
EV_MIN_SIZE = 30.0   # nm
EV_MAX_SIZE = 300.0  # nm

# Refractive indices
N_PARTICLE = 1.40    # Typical EV
N_MEDIUM = 1.33      # PBS


# =============================================================================
# MIE CALCULATOR CLASS
# =============================================================================

class CalibratedMieCalculator:
    """
    Mie calculator with calibration correction for multi-wavelength data.
    """
    
    def __init__(
        self,
        wavelength_nm: float = 488.0,
        n_particle: float = N_PARTICLE,
        n_medium: float = N_MEDIUM,
        calibration_factor: float = 1.0
    ):
        self.wavelength_nm = wavelength_nm
        self.n_particle = n_particle
        self.n_medium = n_medium
        self.m = complex(n_particle / n_medium, 0.0)
        self.calibration_factor = calibration_factor
        
        # Build lookup table
        self._build_lut()
    
    def _build_lut(self, min_d: float = 10.0, max_d: float = 500.0, resolution: float = 0.5):
        """Build scatter intensity lookup table."""
        self.lut_diameters = np.arange(min_d, max_d + resolution, resolution)
        self.lut_scatter = np.zeros(len(self.lut_diameters))
        
        for i, d in enumerate(self.lut_diameters):
            x = (np.pi * d) / self.wavelength_nm
            try:
                result = miepython.efficiencies(self.m, d, self.wavelength_nm, n_env=self.n_medium)
                qsca = float(result[1]) if result[1] is not None else 0.0
                g = float(result[3]) if result[3] is not None else 0.0
                radius = d / 2.0
                cross_section = np.pi * (radius ** 2)
                self.lut_scatter[i] = qsca * cross_section * (1.0 + g)
            except Exception:
                self.lut_scatter[i] = 0.0
    
    def calculate_scatter(self, diameter_nm: float) -> float:
        """Calculate scatter intensity for a given diameter."""
        x = (np.pi * diameter_nm) / self.wavelength_nm
        try:
            result = miepython.efficiencies(self.m, diameter_nm, self.wavelength_nm, n_env=self.n_medium)
            qsca = float(result[1]) if result[1] is not None else 0.0
            g = float(result[3]) if result[3] is not None else 0.0
            radius = diameter_nm / 2.0
            cross_section = np.pi * (radius ** 2)
            return qsca * cross_section * (1.0 + g)
        except Exception:
            return 0.0
    
    def find_all_solutions(
        self,
        target_scatter: float,
        min_diameter: float = EV_MIN_SIZE,
        max_diameter: float = EV_MAX_SIZE,
        tolerance_pct: float = 15.0
    ) -> List[float]:
        """Find all diameters that could produce the target scatter value."""
        tolerance = abs(target_scatter * tolerance_pct / 100.0)
        
        solutions = []
        in_solution = False
        best_d = 0
        best_error = float('inf')
        
        for i, (d, scatter) in enumerate(zip(self.lut_diameters, self.lut_scatter)):
            if min_diameter <= d <= max_diameter:
                error = abs(scatter - target_scatter)
                
                if error <= tolerance:
                    if not in_solution:
                        in_solution = True
                        best_d = d
                        best_error = error
                    elif error < best_error:
                        best_d = d
                        best_error = error
                else:
                    if in_solution:
                        solutions.append(float(best_d))
                        in_solution = False
                        best_error = float('inf')
        
        # Handle if still in solution at end of range
        if in_solution:
            solutions.append(float(best_d))
        
        return solutions


class MultiWavelengthSizer:
    """
    Size particles using multiple wavelengths with calibration correction.
    """
    
    def __init__(
        self,
        wavelength1_nm: float = 405.0,
        wavelength2_nm: float = 488.0,
        n_particle: float = N_PARTICLE,
        n_medium: float = N_MEDIUM,
        calibration_factor: float = DEFAULT_CALIBRATION_FACTOR
    ):
        self.wavelength1_nm = wavelength1_nm
        self.wavelength2_nm = wavelength2_nm
        self.calibration_factor = calibration_factor
        
        # Create calculators for each wavelength
        self.calc1 = CalibratedMieCalculator(wavelength1_nm, n_particle, n_medium)
        self.calc2 = CalibratedMieCalculator(wavelength2_nm, n_particle, n_medium)
        
        # Build theoretical ratio curve
        self._build_ratio_curve()
    
    def _build_ratio_curve(self, min_d: float = 10.0, max_d: float = 500.0, resolution: float = 1.0):
        """Build theoretical ratio vs diameter curve."""
        self.ratio_diameters = np.arange(min_d, max_d + resolution, resolution)
        self.theoretical_ratios = np.zeros(len(self.ratio_diameters))
        
        for i, d in enumerate(self.ratio_diameters):
            s1 = self.calc1.calculate_scatter(float(d))
            s2 = self.calc2.calculate_scatter(float(d))
            if s2 > 0:
                self.theoretical_ratios[i] = s1 / s2
            else:
                self.theoretical_ratios[i] = float('inf')
    
    def correct_measured_ratio(self, measured_ratio: float) -> float:
        """Apply calibration correction to measured ratio."""
        return measured_ratio / self.calibration_factor
    
    def diameter_from_ratio(
        self,
        measured_ratio: float,
        min_diameter: float = EV_MIN_SIZE,
        max_diameter: float = EV_MAX_SIZE
    ) -> Tuple[List[float], float]:
        """
        Find all possible diameters from a measured SSC ratio.
        
        Returns:
            (list of possible sizes, confidence)
        """
        # Apply calibration correction
        corrected_ratio = self.correct_measured_ratio(measured_ratio)
        
        # Find where theoretical curve matches corrected ratio
        solutions = []
        in_match = False
        best_d = 0
        best_error = float('inf')
        tolerance = 0.2  # Ratio tolerance
        
        for i, (d, theoretical) in enumerate(zip(self.ratio_diameters, self.theoretical_ratios)):
            if min_diameter <= d <= max_diameter:
                error = abs(theoretical - corrected_ratio)
                
                if error <= tolerance:
                    if not in_match:
                        in_match = True
                        best_d = d
                        best_error = error
                    elif error < best_error:
                        best_d = d
                        best_error = error
                else:
                    if in_match:
                        solutions.append(float(best_d))
                        in_match = False
                        best_error = float('inf')
        
        if in_match:
            solutions.append(float(best_d))
        
        # Calculate confidence based on how well it matches
        if solutions:
            best_match_error = min([
                abs(self.theoretical_ratios[
                    np.argmin(np.abs(self.ratio_diameters - s))
                ] - corrected_ratio) 
                for s in solutions
            ])
            confidence = max(0.0, 1.0 - (best_match_error / 2.0))
        else:
            confidence = 0.0
        
        return solutions, confidence
    
    def best_size_estimate(
        self,
        fsc_solutions: List[float],
        measured_ratio: float,
        min_diameter: float = EV_MIN_SIZE,
        max_diameter: float = EV_MAX_SIZE
    ) -> Tuple[float, float, str]:
        """
        Select the best size estimate from multiple FSC solutions using ratio.
        
        Returns:
            (best_size, confidence, method)
        """
        if not fsc_solutions:
            return 0.0, 0.0, 'no-fsc-solution'
        
        if len(fsc_solutions) == 1:
            return fsc_solutions[0], 0.9, 'single-fsc-solution'
        
        # Get ratio-based solutions
        ratio_solutions, ratio_confidence = self.diameter_from_ratio(
            measured_ratio, min_diameter, max_diameter
        )
        
        if not ratio_solutions:
            # No ratio match - use smallest FSC solution (conservative)
            return min(fsc_solutions), 0.3, 'smallest-default'
        
        # Find FSC solution closest to any ratio solution
        best_size = fsc_solutions[0]
        best_distance = float('inf')
        
        for fsc_size in fsc_solutions:
            for ratio_size in ratio_solutions:
                distance = abs(fsc_size - ratio_size)
                if distance < best_distance:
                    best_distance = distance
                    best_size = fsc_size
        
        # Confidence based on how close FSC and ratio solutions are
        confidence = max(0.3, 1.0 - (best_distance / 50.0)) * ratio_confidence
        
        return best_size, confidence, 'ratio-calibrated'


# =============================================================================
# FCS PARSING
# =============================================================================

def parse_fcs(file_path: Path) -> Tuple[pd.DataFrame, Dict]:
    """Parse FCS file."""
    try:
        import fcsparser  # type: ignore[import-not-found]
        meta, data = fcsparser.parse(str(file_path), reformat_meta=True)
        return data, meta
    except ImportError:
        pass
    
    try:
        import flowio
        fcs = flowio.FlowData(str(file_path))
        channels = [fcs.channels[str(i+1)]['PnN'] for i in range(fcs.channel_count)]
        data = pd.DataFrame(fcs.events, columns=channels)
        return data, {'channels': channels}
    except ImportError:
        pass
    
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.parsers.fcs_parser import FCSParser
        parser = FCSParser(file_path)
        if parser.validate():
            return parser.parse(), {}
    except Exception:
        pass
    
    raise ImportError("Install fcsparser or flowio: pip install fcsparser")


# =============================================================================
# MAIN ANALYSIS
# =============================================================================

def analyze_with_calibration(
    fcs_path: Path,
    calibration_factor: float = DEFAULT_CALIBRATION_FACTOR,
    sample_size: int = 5000
) -> Dict:
    """
    Analyze FCS file using calibrated multi-wavelength Mie sizing.
    """
    print("=" * 80)
    print("🔬 CALIBRATED MIE MULTI-SOLUTION ANALYZER")
    print(f"   File: {fcs_path.name}")
    print(f"   Calibration Factor: {calibration_factor}")
    print(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Load data
    print("\n📂 Loading FCS file...")
    data, _ = parse_fcs(fcs_path)
    print(f"   ✅ Loaded {len(data):,} events")
    
    # Identify channels
    vfsc_col = 'VFSC-H'
    vssc_col = 'VSSC1-H'
    bssc_col = 'BSSC-H'
    
    if vfsc_col not in data.columns:
        print(f"❌ Channel {vfsc_col} not found")
        return {}
    
    print(f"\n🎯 Using channels:")
    print(f"   FSC: {vfsc_col} (405nm)")
    print(f"   SSC1: {vssc_col} (405nm)")
    print(f"   SSC2: {bssc_col} (488nm)")
    print(f"   Calibration factor: {calibration_factor} (adjusts VSSC/BSSC ratio)")
    
    # Create sizer
    sizer = MultiWavelengthSizer(
        wavelength1_nm=405.0,
        wavelength2_nm=488.0,
        calibration_factor=calibration_factor
    )
    
    # Create FSC calculator
    fsc_calc = CalibratedMieCalculator(wavelength_nm=405.0)
    
    # Sample data
    vfsc: np.ndarray = np.asarray(data[vfsc_col].values, dtype=np.float64)
    vssc: np.ndarray = np.asarray(data[vssc_col].values, dtype=np.float64)
    bssc: np.ndarray = np.asarray(data[bssc_col].values, dtype=np.float64)
    
    # Valid events
    valid: np.ndarray = (vfsc > 0) & (vssc > 0) & (bssc > 0)
    valid_idx = np.where(valid)[0]
    
    if len(valid_idx) > sample_size:
        sample_idx = np.random.choice(valid_idx, sample_size, replace=False)
    else:
        sample_idx = valid_idx
    
    print(f"\n⏳ Analyzing {len(sample_idx):,} events...")
    
    # Analyze
    results = []
    method_counts = {}
    
    for i, idx in enumerate(sample_idx):
        if (i + 1) % 1000 == 0:
            print(f"   Processed {i+1}/{len(sample_idx)}...")
        
        fsc_val = float(vfsc[idx])
        ratio_val = float(vssc[idx]) / float(bssc[idx])
        
        # Find FSC solutions
        fsc_solutions = fsc_calc.find_all_solutions(fsc_val)
        
        # Get best estimate using calibrated ratio
        best_size, confidence, method = sizer.best_size_estimate(
            fsc_solutions, ratio_val
        )
        
        method_counts[method] = method_counts.get(method, 0) + 1
        
        results.append({
            'index': int(idx),
            'fsc': float(fsc_val),
            'ratio_raw': float(ratio_val),
            'ratio_corrected': float(ratio_val / calibration_factor),
            'fsc_solutions': fsc_solutions,
            'best_size': best_size,
            'confidence': confidence,
            'method': method
        })
    
    print("   ✅ Analysis complete!")
    
    # Statistics
    sizes = np.array([r['best_size'] for r in results])
    confidences = np.array([r['confidence'] for r in results])
    corrected_ratios = np.array([r['ratio_corrected'] for r in results])
    
    valid_sizes = sizes[sizes > 0]
    
    small = np.sum((valid_sizes >= 30) & (valid_sizes < 100))
    medium = np.sum((valid_sizes >= 100) & (valid_sizes < 150))
    large = np.sum(valid_sizes >= 150)
    
    print("\n" + "=" * 80)
    print("📊 RESULTS (CALIBRATED)")
    print("=" * 80)
    
    print(f"""
📏 SIZE DISTRIBUTION (with calibration factor {calibration_factor}):
   Valid events: {len(valid_sizes):,} / {len(sizes):,}
   Min:    {np.min(valid_sizes):.1f} nm
   Max:    {np.max(valid_sizes):.1f} nm
   Mean:   {np.mean(valid_sizes):.1f} nm
   Median: {np.median(valid_sizes):.1f} nm
   Std:    {np.std(valid_sizes):.1f} nm

📊 SIZE CATEGORIES:
   Small (30-100nm):   {small:,} ({100*small/len(valid_sizes):.1f}%)
   Medium (100-150nm): {medium:,} ({100*medium/len(valid_sizes):.1f}%)
   Large (>150nm):     {large:,} ({100*large/len(valid_sizes):.1f}%)

📐 CORRECTED RATIO STATISTICS:
   Before calibration: {np.mean([r['ratio_raw'] for r in results]):.2f} (mean)
   After calibration:  {np.mean(corrected_ratios):.2f} (mean)
   Theoretical range:  0.2 - 2.1 (Mie curve)

📋 DISAMBIGUATION METHODS:
""")
    for method, count in sorted(method_counts.items(), key=lambda x: -x[1]):
        print(f"   {method}: {count} ({100*count/len(results):.1f}%)")
    
    print(f"""
🎯 CONFIDENCE:
   Mean: {np.mean(confidences):.2f}
   Low (<0.3): {np.sum(confidences < 0.3)} events
   High (>0.7): {np.sum(confidences > 0.7)} events
""")
    
    # Save results
    output_dir = fcs_path.parent / 'mie_analysis'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Summary JSON
    summary = {
        'file': str(fcs_path),
        'calibration_factor': calibration_factor,
        'analysis_date': datetime.now().isoformat(),
        'statistics': {
            'n_events': len(valid_sizes),
            'mean_size': float(np.mean(valid_sizes)),
            'median_size': float(np.median(valid_sizes)),
            'std_size': float(np.std(valid_sizes)),
            'small_count': int(small),
            'medium_count': int(medium),
            'large_count': int(large),
            'mean_confidence': float(np.mean(confidences))
        },
        'method_counts': method_counts
    }
    
    json_file = output_dir / f'{fcs_path.stem}_calibrated_analysis.json'
    with open(json_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"💾 Summary saved: {json_file}")
    
    # CSV with details
    csv_file = output_dir / f'{fcs_path.stem}_calibrated_sizes.csv'
    df_results = pd.DataFrame([{
        'event_index': r['index'],
        'fsc': r['fsc'],
        'ratio_raw': r['ratio_raw'],
        'ratio_corrected': r['ratio_corrected'],
        'num_fsc_solutions': len(r['fsc_solutions']),
        'fsc_solutions': ';'.join([f'{s:.1f}' for s in r['fsc_solutions']]),
        'best_size_nm': r['best_size'],
        'confidence': r['confidence'],
        'method': r['method']
    } for r in results])
    df_results.to_csv(csv_file, index=False)
    print(f"💾 Details saved: {csv_file}")
    
    # Plots
    if HAS_MATPLOTLIB:
        print("\n📈 Generating plots...")
        generate_calibrated_plots(
            sizer, results, valid_sizes, output_dir, fcs_path.stem, calibration_factor
        )
    
    return summary


def generate_calibrated_plots(
    sizer: MultiWavelengthSizer,
    results: List[Dict],
    sizes: np.ndarray,
    output_dir: Path,
    file_stem: str,
    calibration_factor: float
):
    """Generate analysis plots."""
    if not HAS_MATPLOTLIB or plt is None:
        print("⚠️ Matplotlib not available - skipping plots")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Plot 1: Size distribution
    ax1 = axes[0, 0]
    bins = np.arange(30, 305, 10)
    ax1.hist(sizes, bins=bins, color='steelblue', edgecolor='white', alpha=0.7)
    ax1.axvline(np.median(sizes), color='red', linestyle='--', linewidth=2,
               label=f'Median: {np.median(sizes):.0f}nm')
    ax1.axvline(100, color='green', linestyle=':', alpha=0.7)
    ax1.axvline(150, color='orange', linestyle=':', alpha=0.7)
    ax1.set_xlabel('Particle Diameter (nm)')
    ax1.set_ylabel('Count')
    ax1.set_title(f'Size Distribution (Calibrated, factor={calibration_factor})')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Raw vs Corrected ratios
    ax2 = axes[0, 1]
    raw_ratios = [r['ratio_raw'] for r in results]
    corrected_ratios = [r['ratio_corrected'] for r in results]
    
    ax2.hist(raw_ratios, bins=50, alpha=0.5, label=f'Raw (mean={np.mean(raw_ratios):.2f})', color='red')
    ax2.hist(corrected_ratios, bins=50, alpha=0.5, label=f'Corrected (mean={np.mean(corrected_ratios):.2f})', color='blue')
    ax2.axvline(2.1, color='green', linestyle=':', linewidth=2, label='Rayleigh limit')
    ax2.set_xlabel('VSSC/BSSC Ratio')
    ax2.set_ylabel('Count')
    ax2.set_title('Raw vs Calibration-Corrected Ratios')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0, 10)
    
    # Plot 3: Theoretical ratio curve with corrected measurements
    ax3 = axes[1, 0]
    ax3.plot(sizer.ratio_diameters, sizer.theoretical_ratios, 'b-', linewidth=2, 
            label='Theoretical')
    
    # Add histogram of sizes colored by corrected ratio
    scatter_sizes = [r['best_size'] for r in results if r['best_size'] > 0]
    scatter_ratios = [r['ratio_corrected'] for r in results if r['best_size'] > 0]
    
    ax3.scatter(scatter_sizes, scatter_ratios, s=1, alpha=0.1, c='red', label='Measured (corrected)')
    ax3.set_xlabel('Particle Diameter (nm)')
    ax3.set_ylabel('VSSC/BSSC Ratio')
    ax3.set_title('Theoretical Curve vs Measured Data (Corrected)')
    ax3.set_xlim(30, 300)
    ax3.set_ylim(0, 4)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Confidence distribution
    ax4 = axes[1, 1]
    confidences = [r['confidence'] for r in results]
    ax4.hist(confidences, bins=20, color='coral', edgecolor='white', alpha=0.7)
    ax4.axvline(np.mean(confidences), color='red', linestyle='--',
               label=f'Mean: {np.mean(confidences):.2f}')
    ax4.set_xlabel('Confidence Score')
    ax4.set_ylabel('Count')
    ax4.set_title('Size Estimation Confidence')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    plot_file = output_dir / f'{file_stem}_calibrated_analysis.png'
    plt.savefig(plot_file, dpi=150)
    plt.close()
    print(f"   📊 Plot saved: {plot_file}")


# =============================================================================
# CALIBRATION EXPLORATION
# =============================================================================

def explore_calibration_factors(fcs_path: Path, factors: Optional[List[float]] = None):
    """
    Run analysis with different calibration factors to find optimal.
    """
    if factors is None:
        factors = [1.0, 1.5, 2.0, 2.2, 2.5, 3.0]
    
    print("=" * 80)
    print("🔍 CALIBRATION FACTOR EXPLORATION")
    print("=" * 80)
    
    results_comparison = []
    
    for factor in factors:
        print(f"\n--- Testing calibration factor: {factor} ---")
        result = analyze_with_calibration(fcs_path, factor, sample_size=2000)
        
        if result:
            results_comparison.append({
                'factor': factor,
                'mean_size': result['statistics']['mean_size'],
                'median_size': result['statistics']['median_size'],
                'small_pct': 100 * result['statistics']['small_count'] / result['statistics']['n_events'],
                'medium_pct': 100 * result['statistics']['medium_count'] / result['statistics']['n_events'],
                'large_pct': 100 * result['statistics']['large_count'] / result['statistics']['n_events'],
                'confidence': result['statistics']['mean_confidence']
            })
    
    print("\n" + "=" * 80)
    print("📊 CALIBRATION COMPARISON SUMMARY")
    print("=" * 80)
    print(f"\n{'Factor':<10} {'Mean (nm)':<12} {'Median':<10} {'Small %':<10} {'Medium %':<10} {'Large %':<10} {'Confidence':<10}")
    print("-" * 80)
    
    for r in results_comparison:
        print(f"{r['factor']:<10.1f} {r['mean_size']:<12.1f} {r['median_size']:<10.1f} "
              f"{r['small_pct']:<10.1f} {r['medium_pct']:<10.1f} {r['large_pct']:<10.1f} "
              f"{r['confidence']:<10.3f}")
    
    # Find best factor (highest confidence, reasonable size distribution)
    best = max(results_comparison, key=lambda x: x['confidence'])
    print(f"\n🎯 Best calibration factor: {best['factor']} (confidence: {best['confidence']:.3f})")
    
    return results_comparison


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point."""
    
    if len(sys.argv) < 2:
        backend_path = Path(__file__).parent.parent
        fcs_path = backend_path / 'nanoFACS' / 'Exp_20251217_PC3' / 'PC3 EXO1.fcs'
        calibration_factor = DEFAULT_CALIBRATION_FACTOR
    else:
        fcs_path = Path(sys.argv[1])
        calibration_factor = float(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_CALIBRATION_FACTOR
    
    if not fcs_path.exists():
        print(f"❌ File not found: {fcs_path}")
        sys.exit(1)
    
    # Check if exploring calibration
    if '--explore' in sys.argv:
        explore_calibration_factors(fcs_path)
    else:
        analyze_with_calibration(fcs_path, calibration_factor, sample_size=5000)
    
    print("\n✅ Analysis complete!")


if __name__ == '__main__':
    main()
