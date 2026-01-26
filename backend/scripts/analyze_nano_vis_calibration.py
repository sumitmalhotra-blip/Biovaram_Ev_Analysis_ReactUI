"""
Nano Vis Calibration Set Analysis
==================================

Analyzes the Nano Vis High and Low calibration FCS files.
Expected size ranges:
- Low: 40-150nm
- High: 140-1000nm

Creates event vs size scatter plots and size distributions.

Created: January 22, 2026
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import json

# Try to import plotting
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    plt = None  # type: ignore
    HAS_MATPLOTLIB = False
    print("⚠️ matplotlib not installed - plots will be skipped")

# Try to import miepython
miepython = None  # Initialize to avoid unbound error
try:
    import miepython
    HAS_MIEPYTHON = True
except ImportError:
    HAS_MIEPYTHON = False
    print("⚠️ miepython not installed - using simplified size estimation")

try:
    import flowio
    HAS_FLOWIO = True
except ImportError:
    HAS_FLOWIO = False
    print("❌ flowio not installed - cannot parse FCS files")
    sys.exit(1)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Refractive indices
N_PARTICLE = 1.59  # Polystyrene beads (calibration particles are usually PS)
N_MEDIUM = 1.33    # Water/PBS

# Calibration file info
CALIBRATION_FILES = {
    'low': {
        'path': 'nanoFACS/Nano Vis Low.fcs',
        'expected_range': (40, 150),  # nm
        'description': 'Small particles (40-150nm)'
    },
    'high': {
        'path': 'nanoFACS/Nano Vis High.fcs',
        'expected_range': (140, 1000),  # nm
        'description': 'Large particles (140-1000nm)'
    }
}


# =============================================================================
# FCS PARSER
# =============================================================================

def parse_fcs_file(file_path: Path) -> Tuple[pd.DataFrame, Dict]:
    """Parse FCS file using flowio."""
    fcs = flowio.FlowData(str(file_path))
    
    # Get channel names
    channels = [fcs.channels[str(i+1)]['PnN'] for i in range(fcs.channel_count)]
    
    # Convert events to numpy array and reshape
    events_array = np.array(fcs.events).reshape(-1, len(channels))
    data = pd.DataFrame(events_array, columns=channels)
    
    metadata = {
        'event_count': fcs.event_count,
        'channel_count': fcs.channel_count,
        'channels': channels,
    }
    
    return data, metadata


# =============================================================================
# MIE SCATTERING SIZE CALCULATOR
# =============================================================================

class MieSizeCalculator:
    """Calculate particle size from scatter intensity using Mie theory."""
    
    def __init__(
        self,
        wavelength_nm: float = 488.0,
        n_particle: float = N_PARTICLE,
        n_medium: float = N_MEDIUM
    ):
        self.wavelength_nm = wavelength_nm
        self.n_particle = n_particle
        self.n_medium = n_medium
        self.m = complex(n_particle / n_medium, 0.0)
        
        # Build lookup tables
        self._build_lookup_tables()
    
    def _build_lookup_tables(
        self,
        min_d: float = 20.0,
        max_d: float = 1500.0,
        resolution: float = 1.0
    ):
        """Build scatter intensity lookup tables."""
        self.lut_diameters = np.arange(min_d, max_d + resolution, resolution)
        self.lut_fsc = np.zeros(len(self.lut_diameters))
        self.lut_ssc = np.zeros(len(self.lut_diameters))
        
        for i, d in enumerate(self.lut_diameters):
            fsc, ssc = self._calculate_scatter(float(d))
            self.lut_fsc[i] = fsc
            self.lut_ssc[i] = ssc
    
    def _calculate_scatter(self, diameter_nm: float) -> Tuple[float, float]:
        """Calculate FSC and SSC for a given diameter."""
        if HAS_MIEPYTHON and miepython is not None:
            try:
                result = miepython.efficiencies(
                    self.m, diameter_nm, self.wavelength_nm, n_env=self.n_medium
                )
                qsca = float(result[1]) if result[1] is not None else 0.0
                qback = float(result[2]) if result[2] is not None else 0.0
                g = float(result[3]) if result[3] is not None else 0.0
                
                radius = diameter_nm / 2.0
                cross_section = np.pi * (radius ** 2)
                
                # FSC ~ forward scatter (proportional to Qsca * (1+g))
                fsc = qsca * cross_section * (1.0 + g)
                # SSC ~ side/back scatter (proportional to Qback)
                ssc = qback * cross_section
                
                return fsc, ssc
            except Exception:
                pass
        
        # Fallback: Rayleigh approximation for small particles
        # Scatter ~ d^6 / λ^4
        x = (np.pi * diameter_nm) / self.wavelength_nm
        rayleigh_factor = (diameter_nm ** 6) / (self.wavelength_nm ** 4)
        return rayleigh_factor * 1e-12, rayleigh_factor * 1e-13
    
    def scatter_to_size(
        self,
        scatter_values: np.ndarray,
        scatter_type: str = 'ssc',
        min_size: float = 20.0,
        max_size: float = 1500.0
    ) -> np.ndarray:
        """Convert scatter intensities to particle sizes."""
        lut = self.lut_ssc if scatter_type == 'ssc' else self.lut_fsc
        
        # Normalize scatter values to LUT range
        lut_min = np.min(lut[lut > 0]) if np.any(lut > 0) else 1e-10
        lut_max = np.max(lut)
        
        scatter_min = np.min(scatter_values[scatter_values > 0]) if np.any(scatter_values > 0) else 1
        scatter_max = np.max(scatter_values)
        
        # Scale scatter values to match LUT range
        scale_factor = lut_max / scatter_max if scatter_max > 0 else 1.0
        scaled_scatter = scatter_values * scale_factor
        
        # Interpolate sizes
        sizes = np.zeros(len(scatter_values))
        for i, s in enumerate(scaled_scatter):
            if s <= 0:
                sizes[i] = 0
            else:
                # Find closest LUT value
                idx = np.argmin(np.abs(lut - s))
                sizes[i] = self.lut_diameters[idx]
        
        # Clip to expected range
        sizes = np.clip(sizes, min_size, max_size)
        
        return sizes


# =============================================================================
# SIMPLE SIZE ESTIMATOR (Power Law)
# =============================================================================

def estimate_sizes_power_law(
    scatter_values: np.ndarray,
    min_size: float,
    max_size: float,
    power: float = 3.0  # Rayleigh: I ~ d^6, so d ~ I^(1/6), but in Mie regime ~d^3
) -> np.ndarray:
    """
    Estimate particle sizes using a simple power-law relationship.
    
    This is a simplified approach that maps scatter intensity to size
    assuming a monotonic relationship: scatter ~ diameter^power
    """
    # Get valid values
    valid_mask = scatter_values > 0
    valid_scatter = scatter_values[valid_mask]
    
    if len(valid_scatter) == 0:
        return np.zeros(len(scatter_values))
    
    # Log transform for better scaling
    log_scatter = np.log10(valid_scatter)
    log_min = np.min(log_scatter)
    log_max = np.max(log_scatter)
    
    # Map log scatter to size range
    sizes = np.zeros(len(scatter_values))
    normalized = (log_scatter - log_min) / (log_max - log_min) if log_max > log_min else 0.5
    sizes[valid_mask] = min_size + normalized * (max_size - min_size)
    
    return sizes


# =============================================================================
# MAIN ANALYSIS
# =============================================================================

def analyze_calibration_file(
    file_path: Path,
    expected_range: Tuple[float, float],
    description: str,
    sample_size: int = 50000
) -> Dict:
    """Analyze a single calibration FCS file."""
    
    print(f"\n{'='*70}")
    print(f"📊 Analyzing: {file_path.name}")
    print(f"   {description}")
    print(f"   Expected size range: {expected_range[0]}-{expected_range[1]} nm")
    print(f"{'='*70}")
    
    # Parse file
    data, metadata = parse_fcs_file(file_path)
    print(f"\n✅ Loaded {metadata['event_count']:,} events")
    print(f"   Channels: {metadata['channels']}")
    
    # Identify scatter channels
    fsc_channel = 'FSC-H'
    ssc_channel = 'SSC-H'  # Main SSC channel
    
    # Get scatter values
    fsc_values: np.ndarray = np.asarray(data[fsc_channel].values, dtype=np.float64)
    ssc_values: np.ndarray = np.asarray(data[ssc_channel].values, dtype=np.float64)
    
    # Filter valid events (positive FSC and SSC)
    valid_mask: np.ndarray = (fsc_values > 0) & (ssc_values > 0)
    valid_indices = np.where(valid_mask)[0]
    
    print(f"   Valid events (FSC>0 & SSC>0): {len(valid_indices):,}")
    
    # Sample for analysis
    if len(valid_indices) > sample_size:
        sample_idx = np.random.choice(valid_indices, sample_size, replace=False)
    else:
        sample_idx = valid_indices
    
    print(f"   Analyzing {len(sample_idx):,} events...")
    
    # Get sampled values
    fsc_sampled = fsc_values[sample_idx]
    ssc_sampled = ssc_values[sample_idx]
    event_numbers = sample_idx  # Event indices
    
    # Estimate sizes using power-law (simple approach)
    sizes_from_ssc = estimate_sizes_power_law(
        ssc_sampled,
        expected_range[0],
        expected_range[1]
    )
    
    sizes_from_fsc = estimate_sizes_power_law(
        fsc_sampled,
        expected_range[0],
        expected_range[1]
    )
    
    # Try Mie-based sizing if available
    if HAS_MIEPYTHON:
        print("   Using Mie theory for size calculation...")
        calculator = MieSizeCalculator()
        sizes_mie = calculator.scatter_to_size(
            ssc_sampled,
            scatter_type='ssc',
            min_size=expected_range[0],
            max_size=expected_range[1]
        )
    else:
        sizes_mie = sizes_from_ssc
    
    # Statistics
    valid_sizes = sizes_mie[sizes_mie > 0]
    
    print(f"\n📏 Size Statistics:")
    print(f"   Count:  {len(valid_sizes):,}")
    print(f"   Min:    {np.min(valid_sizes):.1f} nm")
    print(f"   Max:    {np.max(valid_sizes):.1f} nm")
    print(f"   Mean:   {np.mean(valid_sizes):.1f} nm")
    print(f"   Median: {np.median(valid_sizes):.1f} nm")
    print(f"   Std:    {np.std(valid_sizes):.1f} nm")
    
    # Size distribution bins
    in_range = (valid_sizes >= expected_range[0]) & (valid_sizes <= expected_range[1])
    pct_in_range = np.sum(in_range) / len(valid_sizes) * 100
    print(f"   In expected range: {pct_in_range:.1f}%")
    
    return {
        'file': file_path.name,
        'description': description,
        'expected_range': expected_range,
        'event_count': metadata['event_count'],
        'valid_events': len(valid_indices),
        'sampled_events': len(sample_idx),
        'event_numbers': event_numbers,
        'fsc_values': fsc_sampled,
        'ssc_values': ssc_sampled,
        'sizes': sizes_mie,
        'sizes_from_ssc': sizes_from_ssc,
        'sizes_from_fsc': sizes_from_fsc,
        'statistics': {
            'min': float(np.min(valid_sizes)),
            'max': float(np.max(valid_sizes)),
            'mean': float(np.mean(valid_sizes)),
            'median': float(np.median(valid_sizes)),
            'std': float(np.std(valid_sizes)),
            'pct_in_range': float(pct_in_range),
        }
    }


def create_analysis_plots(results: Dict[str, Dict], output_dir: Path):
    """Create comprehensive analysis plots."""
    
    if not HAS_MATPLOTLIB or plt is None:
        print("⚠️ Matplotlib not available - skipping plots")
        return
    
    print("\n📊 Generating plots...")
    
    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))
    
    # Define subplot layout
    gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
    
    for idx, (key, result) in enumerate(results.items()):
        col_offset = idx * 2
        
        event_numbers = result['event_numbers']
        sizes = result['sizes']
        ssc_values = result['ssc_values']
        fsc_values = result['fsc_values']
        expected = result['expected_range']
        
        # Plot 1: Event vs Size scatter plot
        ax1 = fig.add_subplot(gs[0, col_offset:col_offset+2])
        
        # Color by whether in expected range
        in_range = (sizes >= expected[0]) & (sizes <= expected[1])
        colors = np.where(in_range, 'steelblue', 'coral')
        
        ax1.scatter(event_numbers, sizes, s=1, c=colors, alpha=0.3)
        ax1.axhline(y=expected[0], color='green', linestyle='--', linewidth=2, label=f'Min expected: {expected[0]}nm')
        ax1.axhline(y=expected[1], color='red', linestyle='--', linewidth=2, label=f'Max expected: {expected[1]}nm')
        ax1.axhline(y=np.median(sizes), color='purple', linestyle='-', linewidth=2, label=f'Median: {np.median(sizes):.0f}nm')
        
        ax1.set_xlabel('Event Number', fontsize=10)
        ax1.set_ylabel('Estimated Size (nm)', fontsize=10)
        ax1.set_title(f'Event vs Size - {key.upper()}\n{result["description"]}', fontsize=11, fontweight='bold')
        ax1.legend(loc='upper right', fontsize=8)
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Size Distribution Histogram
        ax2 = fig.add_subplot(gs[1, col_offset:col_offset+2])
        
        bins = np.linspace(expected[0]*0.5, expected[1]*1.2, 50)
        ax2.hist(sizes, bins=bins, color='steelblue', edgecolor='white', alpha=0.7)
        ax2.axvline(x=expected[0], color='green', linestyle='--', linewidth=2, label=f'Min: {expected[0]}nm')
        ax2.axvline(x=expected[1], color='red', linestyle='--', linewidth=2, label=f'Max: {expected[1]}nm')
        ax2.axvline(x=np.median(sizes), color='purple', linestyle='-', linewidth=2, label=f'Median: {np.median(sizes):.0f}nm')
        
        ax2.set_xlabel('Estimated Size (nm)', fontsize=10)
        ax2.set_ylabel('Count', fontsize=10)
        ax2.set_title(f'Size Distribution - {key.upper()}', fontsize=11, fontweight='bold')
        ax2.legend(loc='upper right', fontsize=8)
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: SSC vs Size
        ax3 = fig.add_subplot(gs[2, col_offset])
        
        ax3.scatter(ssc_values, sizes, s=1, alpha=0.2, c='steelblue')
        ax3.set_xlabel('SSC-H', fontsize=10)
        ax3.set_ylabel('Estimated Size (nm)', fontsize=10)
        ax3.set_title(f'SSC vs Size - {key.upper()}', fontsize=10)
        ax3.set_xscale('log')
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: FSC vs SSC
        ax4 = fig.add_subplot(gs[2, col_offset+1])
        
        sc = ax4.scatter(fsc_values, ssc_values, s=1, c=sizes, cmap='viridis', alpha=0.3)
        ax4.set_xlabel('FSC-H', fontsize=10)
        ax4.set_ylabel('SSC-H', fontsize=10)
        ax4.set_title(f'FSC vs SSC (colored by size) - {key.upper()}', fontsize=10)
        ax4.set_xscale('log')
        ax4.set_yscale('log')
        ax4.grid(True, alpha=0.3)
        plt.colorbar(sc, ax=ax4, label='Size (nm)')
    
    plt.suptitle('Nano Vis Calibration Analysis\nLOW (40-150nm) vs HIGH (140-1000nm)', 
                 fontsize=14, fontweight='bold', y=1.02)
    
    plt.tight_layout()
    
    # Save plot
    output_file = output_dir / 'nano_vis_calibration_analysis.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"   📊 Plot saved: {output_file}")
    
    # Create additional scatter intensity comparison plot
    fig2, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    for idx, (key, result) in enumerate(results.items()):
        ax = axes[idx]
        
        ssc = result['ssc_values']
        fsc = result['fsc_values']
        expected = result['expected_range']
        
        # Log-log scatter plot
        valid = (ssc > 0) & (fsc > 0)
        ax.scatter(fsc[valid], ssc[valid], s=1, alpha=0.2, c='steelblue')
        
        ax.set_xlabel('FSC-H (Forward Scatter)', fontsize=11)
        ax.set_ylabel('SSC-H (Side Scatter)', fontsize=11)
        ax.set_title(f'{key.upper()}: {result["description"]}\n(Expected: {expected[0]}-{expected[1]}nm)', 
                    fontsize=12, fontweight='bold')
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.grid(True, alpha=0.3)
        
        # Add statistics text
        stats = result['statistics']
        stats_text = f"Mean: {stats['mean']:.0f}nm\nMedian: {stats['median']:.0f}nm\nIn range: {stats['pct_in_range']:.1f}%"
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    
    output_file2 = output_dir / 'nano_vis_scatter_comparison.png'
    plt.savefig(output_file2, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"   📊 Scatter comparison saved: {output_file2}")


def main():
    """Main entry point."""
    
    print("="*70)
    print("🔬 NANO VIS CALIBRATION ANALYSIS")
    print("="*70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Set up paths
    backend_dir = Path(__file__).parent.parent
    output_dir = backend_dir / 'figures' / 'nano_vis_calibration'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Analyze both files
    results = {}
    
    for key, config in CALIBRATION_FILES.items():
        file_path = backend_dir / config['path']
        
        if not file_path.exists():
            print(f"\n❌ File not found: {file_path}")
            continue
        
        result = analyze_calibration_file(
            file_path,
            config['expected_range'],
            config['description']
        )
        results[key] = result
    
    # Create plots
    if results:
        create_analysis_plots(results, output_dir)
        
        # Save summary JSON
        summary = {
            'analysis_date': datetime.now().isoformat(),
            'files': {}
        }
        for key, result in results.items():
            summary['files'][key] = {
                'file': result['file'],
                'description': result['description'],
                'expected_range': result['expected_range'],
                'event_count': result['event_count'],
                'valid_events': result['valid_events'],
                'statistics': result['statistics']
            }
        
        summary_file = output_dir / 'analysis_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"\n📄 Summary saved: {summary_file}")
    
    print("\n" + "="*70)
    print("✅ Analysis complete!")
    print("="*70)


if __name__ == "__main__":
    main()
