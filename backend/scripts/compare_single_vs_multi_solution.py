"""
Compare Single-Solution vs Multi-Solution Mie Theory Sizing
============================================================

This script demonstrates the difference between:
1. Single-solution: Picks ONE size for each scatter value
2. Multi-solution: Finds ALL possible sizes, then uses wavelength ratio to disambiguate

Created: January 23, 2026
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import libraries
try:
    import miepython
    HAS_MIEPYTHON = True
except ImportError:
    print("❌ miepython not installed")
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

import flowio


# =============================================================================
# PHYSICAL PARAMETERS
# =============================================================================
WAVELENGTH_VIOLET = 405.0  # nm (VSSC channel)
WAVELENGTH_BLUE = 488.0    # nm (BSSC channel)
N_PARTICLE = 1.40          # EV refractive index
N_MEDIUM = 1.33            # PBS refractive index


# =============================================================================
# SINGLE-SOLUTION APPROACH (Current Production Method)
# =============================================================================
class SingleSolutionMie:
    """
    Single-solution approach: For each scatter value, find ONE closest matching size.
    This is what the current production code does.
    """
    
    def __init__(self, wavelength_nm: float = 488.0, n_particle: float = 1.40, n_medium: float = 1.33):
        self.wavelength_nm = wavelength_nm
        self.n_particle = n_particle
        self.n_medium = n_medium
        self.m = complex(n_particle / n_medium, 0)
        
        # Build lookup table
        self.lut_diameters = np.arange(30, 501, 1)  # 30-500 nm
        self.lut_ssc = np.zeros(len(self.lut_diameters))
        
        for i, d in enumerate(self.lut_diameters):
            self.lut_ssc[i] = self._calc_ssc(d)
    
    def _calc_ssc(self, diameter_nm: float) -> float:
        """Calculate SSC for a diameter."""
        try:
            result = miepython.efficiencies(self.m, diameter_nm, self.wavelength_nm, n_env=self.n_medium)
            qback = float(result[2]) if result[2] is not None else 0.0
            radius = diameter_nm / 2.0
            cross_section = np.pi * (radius ** 2)
            return qback * cross_section
        except:
            return 0.0
    
    def ssc_to_size(self, ssc_values: np.ndarray) -> np.ndarray:
        """Convert SSC values to sizes using simple interpolation (SINGLE solution)."""
        sizes = np.zeros(len(ssc_values))
        
        for i, ssc in enumerate(ssc_values):
            if ssc <= 0:
                sizes[i] = np.nan
                continue
            
            # Find closest match - picks FIRST/CLOSEST one only
            errors = np.abs(self.lut_ssc - ssc)
            best_idx = np.argmin(errors)
            sizes[i] = self.lut_diameters[best_idx]
        
        return sizes


# =============================================================================
# MULTI-SOLUTION APPROACH (What Parvesh Described)
# =============================================================================
class MultiSolutionMie:
    """
    Multi-solution approach: 
    1. Find ALL sizes that match the scatter value (within tolerance)
    2. Use wavelength ratio (VSSC/BSSC) to select the correct solution
    """
    
    def __init__(self, n_particle: float = 1.40, n_medium: float = 1.33):
        self.n_particle = n_particle
        self.n_medium = n_medium
        
        # Build lookup tables for BOTH wavelengths
        self.lut_diameters = np.arange(30, 501, 1)  # 30-500 nm
        
        # Violet (405nm) SSC
        self.m_violet = complex(n_particle / n_medium, 0)
        self.lut_ssc_violet = np.array([self._calc_ssc(d, 405.0) for d in self.lut_diameters])
        
        # Blue (488nm) SSC
        self.m_blue = complex(n_particle / n_medium, 0)
        self.lut_ssc_blue = np.array([self._calc_ssc(d, 488.0) for d in self.lut_diameters])
        
        # Pre-compute theoretical ratios
        self.lut_ratio = np.divide(
            self.lut_ssc_violet, 
            self.lut_ssc_blue, 
            out=np.ones_like(self.lut_ssc_violet), 
            where=self.lut_ssc_blue > 0
        )
    
    def _calc_ssc(self, diameter_nm: float, wavelength_nm: float) -> float:
        """Calculate SSC for a diameter at specific wavelength."""
        m = complex(self.n_particle / self.n_medium, 0)
        try:
            result = miepython.efficiencies(m, diameter_nm, wavelength_nm, n_env=self.n_medium)
            qback = float(result[2]) if result[2] is not None else 0.0
            radius = diameter_nm / 2.0
            cross_section = np.pi * (radius ** 2)
            return qback * cross_section
        except:
            return 0.0
    
    def find_all_solutions(self, target_ssc: float, wavelength_nm: float = 488.0, 
                           tolerance_pct: float = 15.0) -> List[float]:
        """Find ALL diameters that could produce this SSC value."""
        if wavelength_nm == 405.0:
            lut_ssc = self.lut_ssc_violet
        else:
            lut_ssc = self.lut_ssc_blue
        
        tolerance = abs(target_ssc * tolerance_pct / 100.0)
        solutions = []
        
        for i, (d, ssc) in enumerate(zip(self.lut_diameters, lut_ssc)):
            if abs(ssc - target_ssc) <= tolerance:
                # Check if this is a new solution (not too close to previous)
                if not solutions or abs(d - solutions[-1]) > 10.0:
                    solutions.append(float(d))
        
        return solutions
    
    def disambiguate_with_ratio(self, possible_sizes: List[float], 
                                measured_ratio: float) -> Tuple[float, List[float]]:
        """
        Select best size using wavelength ratio.
        
        Args:
            possible_sizes: List of candidate sizes
            measured_ratio: Actual VSSC/BSSC ratio from data
            
        Returns:
            (best_size, all_theoretical_ratios)
        """
        if not possible_sizes:
            return np.nan, []
        
        if len(possible_sizes) == 1:
            idx = np.abs(self.lut_diameters - possible_sizes[0]).argmin()
            return possible_sizes[0], [self.lut_ratio[idx]]
        
        best_size = possible_sizes[0]
        best_error = float('inf')
        theoretical_ratios = []
        
        for size in possible_sizes:
            idx = np.abs(self.lut_diameters - size).argmin()
            theoretical_ratio = self.lut_ratio[idx]
            theoretical_ratios.append(theoretical_ratio)
            
            error = abs(theoretical_ratio - measured_ratio)
            if error < best_error:
                best_error = error
                best_size = size
        
        return best_size, theoretical_ratios
    
    def ssc_to_size_multi(self, ssc_blue: np.ndarray, ssc_violet: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Convert SSC values to sizes using MULTI-SOLUTION with wavelength disambiguation.
        
        Returns:
            (sizes, num_solutions_per_event)
        """
        sizes = np.zeros(len(ssc_blue))
        num_solutions = np.zeros(len(ssc_blue))
        
        for i in range(len(ssc_blue)):
            if ssc_blue[i] <= 0 or ssc_violet[i] <= 0:
                sizes[i] = np.nan
                num_solutions[i] = 0
                continue
            
            # Step 1: Find ALL possible solutions using blue SSC
            solutions = self.find_all_solutions(ssc_blue[i], wavelength_nm=488.0)
            num_solutions[i] = len(solutions)
            
            if len(solutions) == 0:
                sizes[i] = np.nan
            elif len(solutions) == 1:
                sizes[i] = solutions[0]
            else:
                # Step 2: Use wavelength ratio to pick the best solution
                measured_ratio = ssc_violet[i] / ssc_blue[i]
                best_size, _ = self.disambiguate_with_ratio(solutions, measured_ratio)
                sizes[i] = best_size
        
        return sizes, num_solutions


# =============================================================================
# PARSE FCS FILE
# =============================================================================
def parse_fcs(file_path: Path) -> pd.DataFrame:
    """Parse FCS file and return DataFrame."""
    fcs = flowio.FlowData(str(file_path))
    channels = [fcs.channels[str(i+1)]['PnN'] for i in range(fcs.channel_count)]
    # Convert array.array to numpy array, then reshape
    events_array = np.array(fcs.events).reshape(-1, fcs.channel_count)
    data = pd.DataFrame(events_array, columns=channels)
    return data


# =============================================================================
# MAIN COMPARISON
# =============================================================================
def run_comparison(fcs_path: str):
    """Run both approaches and compare results."""
    
    print("=" * 80)
    print("SINGLE-SOLUTION vs MULTI-SOLUTION MIE THEORY COMPARISON")
    print("=" * 80)
    
    # Parse file
    fcs_path = Path(fcs_path)
    print(f"\n📁 Loading: {fcs_path.name}")
    data = parse_fcs(fcs_path)
    print(f"   Total events: {len(data):,}")
    
    # Find channels
    channels = data.columns.tolist()
    print(f"\n📊 Available channels: {channels}")
    
    # Find SSC channels
    ssc_blue_ch = None
    ssc_violet_ch = None
    
    for ch in channels:
        if 'SSC' in ch and ('B' in ch or ch == 'SSC-H'):
            ssc_blue_ch = ch
        if 'VSSC' in ch or ('SSC' in ch and 'V' in ch):
            ssc_violet_ch = ch
    
    # Fallback
    if ssc_blue_ch is None:
        for ch in channels:
            if 'SSC' in ch and 'H' in ch:
                ssc_blue_ch = ch
                break
    
    if ssc_violet_ch is None:
        for ch in channels:
            if 'VSSC' in ch:
                ssc_violet_ch = ch
                break
    
    print(f"\n   Blue SSC channel (488nm): {ssc_blue_ch}")
    print(f"   Violet SSC channel (405nm): {ssc_violet_ch}")
    
    if ssc_blue_ch is None:
        print("❌ No SSC channel found!")
        return
    
    # Get SSC values (filter positive only)
    ssc_blue = np.asarray(data[ssc_blue_ch].values)
    mask = ssc_blue > 0
    
    if ssc_violet_ch:
        ssc_violet = np.asarray(data[ssc_violet_ch].values)
        mask = mask & (ssc_violet > 0)
        ssc_violet = ssc_violet[mask]
    else:
        ssc_violet = None
    
    ssc_blue = ssc_blue[mask]
    print(f"\n   Valid events (positive SSC): {len(ssc_blue):,}")
    
    # Sample for speed (use first 5000 events)
    sample_size = min(5000, len(ssc_blue))
    indices = np.random.choice(len(ssc_blue), sample_size, replace=False)
    ssc_blue_sample = ssc_blue[indices]
    if ssc_violet is not None:
        ssc_violet_sample = ssc_violet[indices]
    else:
        ssc_violet_sample = None
    
    print(f"   Analyzing sample of {sample_size:,} events...")
    
    # ==========================================================================
    # SINGLE SOLUTION APPROACH
    # ==========================================================================
    print("\n" + "=" * 80)
    print("APPROACH 1: SINGLE-SOLUTION (Current Production Method)")
    print("=" * 80)
    
    single_solver = SingleSolutionMie(wavelength_nm=488.0, n_particle=N_PARTICLE, n_medium=N_MEDIUM)
    sizes_single = single_solver.ssc_to_size(ssc_blue_sample)
    
    valid_single = sizes_single[~np.isnan(sizes_single)]
    
    print(f"\n📈 Single-Solution Results:")
    print(f"   Valid sizes: {len(valid_single):,} / {sample_size:,}")
    print(f"   Size Statistics:")
    print(f"     - Median (D50): {np.median(valid_single):.1f} nm")
    print(f"     - Mean: {np.mean(valid_single):.1f} nm")
    print(f"     - D10: {np.percentile(valid_single, 10):.1f} nm")
    print(f"     - D90: {np.percentile(valid_single, 90):.1f} nm")
    print(f"     - Min: {np.min(valid_single):.1f} nm")
    print(f"     - Max: {np.max(valid_single):.1f} nm")
    
    # ==========================================================================
    # MULTI SOLUTION APPROACH
    # ==========================================================================
    print("\n" + "=" * 80)
    print("APPROACH 2: MULTI-SOLUTION with Wavelength Disambiguation")
    print("=" * 80)
    
    if ssc_violet_sample is None:
        print("\n⚠️ No violet SSC channel - cannot demonstrate multi-solution disambiguation")
        print("   (Need both VSSC and BSSC to use wavelength ratio)")
        sizes_multi = sizes_single.copy()  # Fallback
        num_solutions = np.ones(len(sizes_single))
    else:
        multi_solver = MultiSolutionMie(n_particle=N_PARTICLE, n_medium=N_MEDIUM)
        sizes_multi, num_solutions = multi_solver.ssc_to_size_multi(ssc_blue_sample, ssc_violet_sample)
        
        valid_multi = sizes_multi[~np.isnan(sizes_multi)]
        
        print(f"\n📈 Multi-Solution Results:")
        print(f"   Valid sizes: {len(valid_multi):,} / {sample_size:,}")
        print(f"   Size Statistics:")
        print(f"     - Median (D50): {np.median(valid_multi):.1f} nm")
        print(f"     - Mean: {np.mean(valid_multi):.1f} nm")
        print(f"     - D10: {np.percentile(valid_multi, 10):.1f} nm")
        print(f"     - D90: {np.percentile(valid_multi, 90):.1f} nm")
        print(f"     - Min: {np.min(valid_multi):.1f} nm")
        print(f"     - Max: {np.max(valid_multi):.1f} nm")
        
        # Multi-solution statistics
        print(f"\n🔍 Multi-Solution Analysis:")
        print(f"   Events with 1 solution: {np.sum(num_solutions == 1):,} ({np.sum(num_solutions == 1)/sample_size*100:.1f}%)")
        print(f"   Events with 2 solutions: {np.sum(num_solutions == 2):,} ({np.sum(num_solutions == 2)/sample_size*100:.1f}%)")
        print(f"   Events with 3+ solutions: {np.sum(num_solutions >= 3):,} ({np.sum(num_solutions >= 3)/sample_size*100:.1f}%)")
        print(f"   Average solutions per event: {np.mean(num_solutions):.2f}")
    
    # ==========================================================================
    # COMPARISON
    # ==========================================================================
    print("\n" + "=" * 80)
    print("COMPARISON: Single vs Multi Solution")
    print("=" * 80)
    
    valid_single = sizes_single[~np.isnan(sizes_single)]
    valid_multi = sizes_multi[~np.isnan(sizes_multi)]
    
    print(f"\n📊 Side-by-Side Comparison:")
    print(f"   {'Metric':<20} {'Single':<15} {'Multi':<15} {'Difference':<15}")
    print(f"   {'-'*60}")
    
    metrics = [
        ('Median (D50)', np.median(valid_single), np.median(valid_multi)),
        ('Mean', np.mean(valid_single), np.mean(valid_multi)),
        ('D10', np.percentile(valid_single, 10), np.percentile(valid_multi, 10)),
        ('D90', np.percentile(valid_single, 90), np.percentile(valid_multi, 90)),
        ('Std Dev', np.std(valid_single), np.std(valid_multi)),
    ]
    
    for name, single_val, multi_val in metrics:
        diff = multi_val - single_val
        diff_pct = (diff / single_val * 100) if single_val != 0 else 0
        print(f"   {name:<20} {single_val:<15.1f} {multi_val:<15.1f} {diff:+.1f} nm ({diff_pct:+.1f}%)")
    
    # Show specific examples where multi-solution made a difference
    print("\n" + "=" * 80)
    print("EXAMPLE EVENTS: Where Multi-Solution Chose Differently")
    print("=" * 80)
    
    # Find events where solutions differ significantly
    diff = np.abs(sizes_single - sizes_multi)
    big_diff_indices = np.where(diff > 20)[0][:10]  # First 10 with >20nm difference
    
    if len(big_diff_indices) > 0:
        print(f"\n   {'Event':<8} {'SSC-Blue':<12} {'SSC-Violet':<12} {'Ratio':<8} {'Single':<10} {'Multi':<10} {'#Solutions':<10}")
        print(f"   {'-'*70}")
        
        for idx in big_diff_indices:
            if ssc_violet_sample is not None:
                ratio = ssc_violet_sample[idx] / ssc_blue_sample[idx]
                print(f"   {idx:<8} {ssc_blue_sample[idx]:<12.0f} {ssc_violet_sample[idx]:<12.0f} {ratio:<8.2f} {sizes_single[idx]:<10.1f} {sizes_multi[idx]:<10.1f} {int(num_solutions[idx]):<10}")
            else:
                print(f"   {idx:<8} {ssc_blue_sample[idx]:<12.0f} {'N/A':<12} {'N/A':<8} {sizes_single[idx]:<10.1f} {sizes_multi[idx]:<10.1f} {int(num_solutions[idx]):<10}")
    else:
        print("\n   No significant differences found in this sample.")
    
    # ==========================================================================
    # VISUALIZATION
    # ==========================================================================
    if HAS_MATPLOTLIB:
        print("\n📊 Generating comparison plots...")
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f'Single vs Multi-Solution Mie Sizing: {fcs_path.name}', fontsize=14, fontweight='bold')
        
        # Plot 1: Size distributions overlay
        ax1 = axes[0, 0]
        bins = np.arange(30, 350, 10)
        ax1.hist(valid_single, bins=bins, alpha=0.5, label=f'Single Solution (D50={np.median(valid_single):.0f}nm)', color='blue', edgecolor='black')
        ax1.hist(valid_multi, bins=bins, alpha=0.5, label=f'Multi Solution (D50={np.median(valid_multi):.0f}nm)', color='red', edgecolor='black')
        ax1.set_xlabel('Diameter (nm)')
        ax1.set_ylabel('Count')
        ax1.set_title('Size Distribution Comparison')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Scatter plot Single vs Multi
        ax2 = axes[0, 1]
        valid_both = ~np.isnan(sizes_single) & ~np.isnan(sizes_multi)
        ax2.scatter(sizes_single[valid_both], sizes_multi[valid_both], alpha=0.3, s=5)
        ax2.plot([30, 350], [30, 350], 'r--', linewidth=2, label='Perfect agreement')
        ax2.set_xlabel('Single Solution Size (nm)')
        ax2.set_ylabel('Multi Solution Size (nm)')
        ax2.set_title('Single vs Multi Solution Agreement')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(30, 350)
        ax2.set_ylim(30, 350)
        
        # Plot 3: Number of solutions histogram
        ax3 = axes[1, 0]
        solution_counts = num_solutions[num_solutions > 0]
        ax3.hist(solution_counts, bins=np.arange(0.5, 6.5, 1), edgecolor='black', color='green', alpha=0.7)
        ax3.set_xlabel('Number of Solutions Found')
        ax3.set_ylabel('Count')
        ax3.set_title('Distribution of Solution Count per Event')
        ax3.set_xticks([1, 2, 3, 4, 5])
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: Mie scatter curve showing multi-solution nature
        ax4 = axes[1, 1]
        diameters = np.arange(30, 300, 1)
        ssc_theory = []
        for d in diameters:
            m = complex(N_PARTICLE / N_MEDIUM, 0)
            result = miepython.efficiencies(m, d, 488.0, n_env=N_MEDIUM)
            qback = float(result[2]) if result[2] is not None else 0.0
            ssc_theory.append(qback * np.pi * (d/2)**2)
        
        ax4.plot(diameters, ssc_theory, 'b-', linewidth=2)
        ax4.set_xlabel('Diameter (nm)')
        ax4.set_ylabel('Theoretical SSC (arbitrary units)')
        ax4.set_title('Mie Scattering Curve\n(Non-monotonic = Multiple Solutions)')
        ax4.grid(True, alpha=0.3)
        
        # Add horizontal line to show multi-solution
        example_ssc = np.percentile(ssc_theory, 50)
        ax4.axhline(y=example_ssc, color='red', linestyle='--', alpha=0.7, label='Example SSC value')
        ax4.legend()
        
        plt.tight_layout()
        
        output_path = Path(__file__).parent.parent / "figures" / "mie_comparison"
        output_path.mkdir(parents=True, exist_ok=True)
        fig_path = output_path / f"single_vs_multi_{fcs_path.stem}.png"
        plt.savefig(fig_path, dpi=150, bbox_inches='tight')
        print(f"   ✅ Saved: {fig_path}")
        plt.close()
    
    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    print("\n" + "=" * 80)
    print("SUMMARY: Why Multi-Solution Matters")
    print("=" * 80)
    print("""
    The Mie scattering curve is NOT monotonic - it oscillates due to wave interference.
    This means a single scatter value can correspond to MULTIPLE particle sizes.
    
    Example: SSC = 5000 could mean:
      - 65 nm particle (small, in Rayleigh regime)
      - 128 nm particle (resonance regime)
      - 215 nm particle (larger, different interference)
    
    Single-Solution Problem:
      - Just picks the closest match in the lookup table
      - May pick the WRONG solution if the true size is larger/smaller
    
    Multi-Solution Advantage:
      - Finds ALL possible sizes
      - Uses wavelength ratio (VSSC/BSSC) to pick the correct one
      - Small particles scatter violet light MORE than blue (Rayleigh λ⁻⁴)
      - Large particles scatter both wavelengths similarly
    
    The wavelength ratio acts as a "fingerprint" that uniquely identifies the correct size!
    """)
    
    return sizes_single, sizes_multi, num_solutions


# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    # Default to PC3 EXO1 sample
    if len(sys.argv) > 1:
        fcs_file = sys.argv[1]
    else:
        fcs_file = str(Path(__file__).parent.parent / "nanoFACS" / "Exp_20251217_PC3" / "PC3 EXO1.fcs")
    
    run_comparison(fcs_file)
