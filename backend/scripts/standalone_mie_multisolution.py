"""
Standalone Mie Scattering Multi-Solution Size Calculator
=========================================================

This is a STANDALONE script for calculating particle sizes from flow cytometry data
using Mie scattering theory with MULTI-SOLUTION detection and WAVELENGTH-BASED disambiguation.

Key Features:
1. Finds ALL possible size solutions (not just one) for each scatter value
2. Uses multi-wavelength SSC data (VSSC vs BSSC) to disambiguate sizes
3. Properly handles the non-monotonic Mie scattering curve
4. Generates diagnostic plots showing the Mie curve and all solutions

Created: January 21, 2026
Author: EV Analysis Platform Team
Status: STANDALONE - Does not modify main project

Usage:
    python standalone_mie_multisolution.py <fcs_file_path>
    
Example:
    python standalone_mie_multisolution.py "nanoFACS/Exp_20251217_PC3/PC3 EXO1.fcs"
"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
import json
from datetime import datetime

# Try to import plotting libraries (optional)
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    plt = None  # type: ignore
    HAS_MATPLOTLIB = False
    print("⚠️ matplotlib not installed - plots will be skipped")

# Try to import miepython
try:
    import miepython
    HAS_MIEPYTHON = True
except ImportError:
    HAS_MIEPYTHON = False
    print("❌ miepython not installed - cannot run Mie calculations")
    print("   Install with: pip install miepython")
    sys.exit(1)


# =============================================================================
# CONFIGURATION: Standard Flow Cytometry Laser Wavelengths
# =============================================================================

@dataclass
class LaserConfig:
    """Configuration for a laser wavelength."""
    wavelength_nm: float
    color: str
    description: str


# Standard laser configurations for flow cytometry
LASER_CONFIGS = {
    'violet': LaserConfig(405, 'Violet', 'Best for small particle detection'),
    'blue': LaserConfig(488, 'Blue', 'Standard detection wavelength'),
    'yellow_green': LaserConfig(561, 'Yellow-Green', 'Common for fluorophores'),
    'red': LaserConfig(633, 'Red', 'Lower scatter, better for large particles'),
}

# Channel name to wavelength mapping
CHANNEL_WAVELENGTHS = {
    'VFSC': 405, 'VSSC': 405, 'VSSC1': 405, 'VSSC2': 405,
    'BFSC': 488, 'BSSC': 488, 'FSC': 488, 'SSC': 488,
    'YFSC': 561, 'YSSC': 561,
    'RFSC': 633, 'RSSC': 633,
    'V447': 405, 'V525': 405,
    'B531': 488,
    'Y595': 561,
    'R670': 633, 'R710': 633, 'R792': 633,
}

# Physical constants
REFRACTIVE_INDICES = {
    'ev_low': 1.37,      # Lower bound for EVs
    'ev_typical': 1.40,  # Typical EV/exosome
    'ev_high': 1.45,     # Upper bound for EVs
    'polystyrene': 1.59, # Calibration beads
    'silica': 1.46,      # Alternative beads
    'pbs': 1.33,         # PBS medium
    'water': 1.33,       # Water
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MieResult:
    """Result from a single Mie calculation."""
    diameter_nm: float
    q_ext: float
    q_sca: float
    q_back: float
    g: float
    forward_scatter: float
    side_scatter: float
    size_parameter_x: float


@dataclass
class SizeSolution:
    """A possible size solution for a measured scatter value."""
    diameter_nm: float
    confidence: float  # 0-1, higher = more confident
    source: str  # 'single', 'multi-wavelength', 'ratio-disambiguated'


@dataclass 
class ParticleSizeResult:
    """Complete size analysis result for a single particle."""
    event_index: int
    fsc_value: float
    ssc_values: Dict[str, float]  # wavelength -> scatter value
    all_solutions: List[float]    # All possible sizes
    best_solution: float          # Most likely size
    confidence: float             # Confidence in best solution
    disambiguation_method: str    # How the best solution was chosen


# =============================================================================
# STANDALONE MIE CALCULATOR
# =============================================================================

class StandaloneMieCalculator:
    """
    Standalone Mie scattering calculator with multi-solution support.
    
    This is independent of the main project's MieScatterCalculator.
    """
    
    def __init__(
        self,
        wavelength_nm: float = 488.0,
        n_particle: float = 1.40,
        n_medium: float = 1.33
    ):
        """
        Initialize the Mie calculator.
        
        Args:
            wavelength_nm: Laser wavelength in nanometers
            n_particle: Refractive index of particles
            n_medium: Refractive index of medium (PBS = 1.33)
        """
        self.wavelength_nm = wavelength_nm
        self.n_particle = n_particle
        self.n_medium = n_medium
        self.m = complex(n_particle / n_medium, 0.0)
        
        # Pre-build lookup table for fast calculations
        self._build_lookup_table()
    
    def _build_lookup_table(
        self,
        min_d: float = 10.0,
        max_d: float = 500.0,
        resolution: float = 0.5
    ):
        """Build lookup table for diameter -> scatter mapping."""
        self.lut_diameters = np.arange(min_d, max_d + resolution, resolution)
        self.lut_fsc = np.zeros(len(self.lut_diameters))
        self.lut_ssc = np.zeros(len(self.lut_diameters))
        
        for i, d in enumerate(self.lut_diameters):
            result = self.calculate_mie(float(d))
            self.lut_fsc[i] = result.forward_scatter
            self.lut_ssc[i] = result.side_scatter
    
    def calculate_mie(self, diameter_nm: float) -> MieResult:
        """
        Calculate Mie scattering parameters for a given diameter.
        
        Args:
            diameter_nm: Particle diameter in nanometers
            
        Returns:
            MieResult with all scattering parameters
        """
        # Size parameter
        x = (np.pi * diameter_nm) / self.wavelength_nm
        
        # Call miepython - use efficiencies which takes diameter and wavelength
        try:
            result = miepython.efficiencies(
                self.m, diameter_nm, self.wavelength_nm, n_env=self.n_medium
            )
            # Unpack result with explicit float conversion
            qext_val: float = float(result[0]) if result[0] is not None else 0.0
            qsca_val: float = float(result[1]) if result[1] is not None else 0.0
            qback_val: float = float(result[2]) if result[2] is not None else 0.0
            g_val: float = float(result[3]) if result[3] is not None else 0.0
        except Exception as e:
            # Return zero values on error
            return MieResult(
                diameter_nm=diameter_nm,
                q_ext=0.0, q_sca=0.0, q_back=0.0, g=0.0,
                forward_scatter=0.0, side_scatter=0.0,
                size_parameter_x=x
            )
        
        # Calculate scatter intensities
        radius_nm = diameter_nm / 2.0
        cross_section = np.pi * (radius_nm ** 2)
        
        forward_scatter = qsca_val * cross_section * (1.0 + g_val)
        side_scatter = qback_val * cross_section
        
        return MieResult(
            diameter_nm=diameter_nm,
            q_ext=qext_val,
            q_sca=qsca_val,
            q_back=qback_val,
            g=g_val,
            forward_scatter=forward_scatter,
            side_scatter=side_scatter,
            size_parameter_x=float(x)
        )
    
    def find_all_solutions(
        self,
        target_scatter: float,
        scatter_type: str = 'fsc',
        min_diameter: float = 30.0,
        max_diameter: float = 300.0,
        tolerance_pct: float = 10.0
    ) -> List[float]:
        """
        Find ALL particle sizes that could produce the given scatter value.
        
        This is the KEY function that differs from single-solution approaches.
        
        Args:
            target_scatter: The measured scatter intensity to match
            scatter_type: 'fsc' for forward scatter, 'ssc' for side scatter
            min_diameter: Minimum diameter to search (nm)
            max_diameter: Maximum diameter to search (nm)
            tolerance_pct: Acceptable match tolerance (% of target)
            
        Returns:
            List of all diameters that could produce this scatter value
        """
        lut = self.lut_fsc if scatter_type == 'fsc' else self.lut_ssc
        tolerance = abs(target_scatter * tolerance_pct / 100.0)
        
        solutions = []
        
        # Find all diameters where scatter matches within tolerance
        for i, (d, scatter) in enumerate(zip(self.lut_diameters, lut)):
            if min_diameter <= d <= max_diameter:
                if abs(scatter - target_scatter) <= tolerance:
                    # Check if this is a new solution (not too close to previous)
                    if not solutions or abs(d - solutions[-1]) > 5.0:
                        solutions.append(float(d))
        
        return solutions
    
    def get_scatter_curve(
        self,
        min_diameter: float = 30.0,
        max_diameter: float = 300.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Get the Mie scatter curve for plotting.
        
        Returns:
            Tuple of (diameters, fsc_values, ssc_values)
        """
        mask = (self.lut_diameters >= min_diameter) & (self.lut_diameters <= max_diameter)
        return (
            self.lut_diameters[mask],
            self.lut_fsc[mask],
            self.lut_ssc[mask]
        )


# =============================================================================
# MULTI-WAVELENGTH DISAMBIGUATION
# =============================================================================

class WavelengthDisambiguator:
    """
    Uses scatter ratios at different wavelengths to disambiguate size solutions.
    
    Physics principle:
    - Small particles (Rayleigh regime): Scatter ∝ λ⁻⁴ → blue scatters MORE than red
    - Large particles (Geometric regime): Scatter ≈ constant → wavelength independent
    """
    
    def __init__(self, n_particle: float = 1.40, n_medium: float = 1.33):
        """Initialize calculators for different wavelengths."""
        self.calculators = {}
        self.n_particle = n_particle
        self.n_medium = n_medium
        
        # Create calculator for each standard wavelength
        for name, config in LASER_CONFIGS.items():
            self.calculators[config.wavelength_nm] = StandaloneMieCalculator(
                wavelength_nm=config.wavelength_nm,
                n_particle=n_particle,
                n_medium=n_medium
            )
    
    def calculate_theoretical_ratio(
        self,
        diameter_nm: float,
        wavelength1_nm: float = 405,
        wavelength2_nm: float = 488
    ) -> float:
        """
        Calculate the theoretical scatter ratio for a given particle size.
        
        Args:
            diameter_nm: Particle diameter
            wavelength1_nm: First wavelength (numerator)
            wavelength2_nm: Second wavelength (denominator)
            
        Returns:
            Theoretical scatter ratio
        """
        if wavelength1_nm not in self.calculators:
            self.calculators[wavelength1_nm] = StandaloneMieCalculator(
                wavelength_nm=wavelength1_nm,
                n_particle=self.n_particle,
                n_medium=self.n_medium
            )
        if wavelength2_nm not in self.calculators:
            self.calculators[wavelength2_nm] = StandaloneMieCalculator(
                wavelength_nm=wavelength2_nm,
                n_particle=self.n_particle,
                n_medium=self.n_medium
            )
        
        result1 = self.calculators[wavelength1_nm].calculate_mie(diameter_nm)
        result2 = self.calculators[wavelength2_nm].calculate_mie(diameter_nm)
        
        if result2.side_scatter > 0:
            return result1.side_scatter / result2.side_scatter
        return float('inf')
    
    def disambiguate_solutions(
        self,
        possible_sizes: List[float],
        measured_ratio: float,
        wavelength1_nm: float = 405,
        wavelength2_nm: float = 488
    ) -> Tuple[float, float]:
        """
        Select the most likely size from multiple solutions using wavelength ratio.
        
        Args:
            possible_sizes: List of possible sizes from find_all_solutions()
            measured_ratio: Measured scatter ratio (e.g., VSSC/BSSC)
            wavelength1_nm: Wavelength of numerator channel
            wavelength2_nm: Wavelength of denominator channel
            
        Returns:
            Tuple of (best_size, confidence)
        """
        if not possible_sizes:
            return 0.0, 0.0
        
        if len(possible_sizes) == 1:
            return possible_sizes[0], 1.0
        
        # Calculate theoretical ratio for each possible size
        best_size = possible_sizes[0]
        best_error = float('inf')
        
        for size in possible_sizes:
            theoretical_ratio = self.calculate_theoretical_ratio(
                size, wavelength1_nm, wavelength2_nm
            )
            error = abs(theoretical_ratio - measured_ratio)
            
            if error < best_error:
                best_error = error
                best_size = size
        
        # Calculate confidence based on how well the ratio matches
        # and how separated the solutions are
        max_error = max(1.0, measured_ratio)
        confidence = max(0.0, 1.0 - (best_error / max_error))
        
        return best_size, confidence
    
    def build_ratio_curve(
        self,
        min_diameter: float = 30.0,
        max_diameter: float = 300.0,
        resolution: float = 1.0,
        wavelength1_nm: float = 405,
        wavelength2_nm: float = 488
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Build a curve of theoretical ratios vs diameter.
        
        Returns:
            Tuple of (diameters, ratios)
        """
        diameters = np.arange(min_diameter, max_diameter + resolution, resolution)
        ratios = np.array([
            self.calculate_theoretical_ratio(float(d), wavelength1_nm, wavelength2_nm)
            for d in diameters
        ])
        return diameters, ratios


# =============================================================================
# FCS FILE PARSER (Standalone version)
# =============================================================================

def parse_fcs_file_standalone(file_path: Path) -> Tuple[pd.DataFrame, Dict]:
    """
    Parse an FCS file without using the main project's parser.
    
    Uses fcsparser library if available, otherwise falls back to flowio.
    """
    try:
        import fcsparser  # type: ignore[import-not-found]
        meta, data = fcsparser.parse(str(file_path), reformat_meta=True)
        return data, meta
    except ImportError:
        pass
    
    try:
        import flowio
        fcs = flowio.FlowData(str(file_path))
        # Convert to DataFrame
        channels = [fcs.channels[str(i+1)]['PnN'] for i in range(fcs.channel_count)]
        data = pd.DataFrame(fcs.events, columns=channels)
        return data, {'channels': channels}
    except ImportError:
        pass
    
    # Try using the main project's parser as fallback
    try:
        backend_path = Path(__file__).parent.parent
        sys.path.insert(0, str(backend_path))
        from src.parsers.fcs_parser import FCSParser
        parser = FCSParser(file_path)
        if parser.validate():
            data = parser.parse()
            return data, {'channels': list(data.columns)}
    except Exception:
        pass
    
    raise ImportError(
        "Cannot parse FCS file. Install one of: fcsparser, flowio\n"
        "  pip install fcsparser\n"
        "  pip install flowio"
    )


def identify_scatter_channels(columns: List[str]) -> Dict[str, Dict]:
    """
    Identify scatter channels and their wavelengths from column names.
    
    Returns:
        Dict mapping channel names to their properties
    """
    channels = {}
    
    for col in columns:
        col_upper = col.upper()
        
        # Check if it's a scatter channel
        is_scatter = any(x in col_upper for x in ['FSC', 'SSC', 'LALS', 'SALS'])
        if not is_scatter:
            continue
        
        # Determine wavelength
        wavelength = None
        laser_color = None
        
        for pattern, wl in CHANNEL_WAVELENGTHS.items():
            if pattern in col_upper:
                wavelength = wl
                for name, config in LASER_CONFIGS.items():
                    if config.wavelength_nm == wl:
                        laser_color = config.color
                        break
                break
        
        # Default to blue if not identified
        if wavelength is None:
            wavelength = 488
            laser_color = 'Blue'
        
        channels[col] = {
            'wavelength_nm': wavelength,
            'laser_color': laser_color,
            'is_fsc': 'FSC' in col_upper or 'LALS' in col_upper,
            'is_ssc': 'SSC' in col_upper or 'SALS' in col_upper,
            'is_height': '-H' in col.upper() or col.upper().endswith('H'),
            'is_area': '-A' in col.upper() or col.upper().endswith('A'),
        }
    
    return channels


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def analyze_fcs_multi_solution(
    fcs_path: Path,
    n_particle: float = 1.40,
    n_medium: float = 1.33,
    min_diameter: float = 30.0,
    max_diameter: float = 300.0,
    sample_size: int = 1000,
    output_dir: Optional[Path] = None
) -> Dict:
    """
    Perform full multi-solution Mie analysis on an FCS file.
    
    Args:
        fcs_path: Path to FCS file
        n_particle: Refractive index of particles
        n_medium: Refractive index of medium
        min_diameter: Minimum size to search (nm)
        max_diameter: Maximum size to search (nm)
        sample_size: Number of events to analyze (for speed)
        output_dir: Directory to save results (optional)
        
    Returns:
        Dict with analysis results
    """
    print("=" * 80)
    print("🔬 STANDALONE MIE MULTI-SOLUTION ANALYZER")
    print(f"   File: {fcs_path.name}")
    print(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Parse FCS file
    print("\n📂 Loading FCS file...")
    data, meta = parse_fcs_file_standalone(fcs_path)
    print(f"   ✅ Loaded {len(data):,} events")
    
    # Identify scatter channels
    print("\n📡 Identifying scatter channels...")
    scatter_channels = identify_scatter_channels(list(data.columns))
    
    # Group by wavelength
    channels_by_wavelength = {}
    for ch, props in scatter_channels.items():
        wl = props['wavelength_nm']
        if wl not in channels_by_wavelength:
            channels_by_wavelength[wl] = []
        channels_by_wavelength[wl].append(ch)
    
    print(f"   Found {len(scatter_channels)} scatter channels:")
    for wl, chs in sorted(channels_by_wavelength.items()):
        print(f"   - {wl}nm: {', '.join(chs)}")
    
    # Select primary channels for analysis
    fsc_channel = None
    ssc_channels = {}  # wavelength -> channel name
    
    # Prefer violet FSC for size
    for ch, props in scatter_channels.items():
        if props['is_fsc'] and props['is_height']:
            if props['wavelength_nm'] == 405:
                fsc_channel = ch
                break
    
    # Fallback to any FSC
    if fsc_channel is None:
        for ch, props in scatter_channels.items():
            if props['is_fsc'] and props['is_height']:
                fsc_channel = ch
                break
    
    # Get SSC channels at different wavelengths
    for ch, props in scatter_channels.items():
        if props['is_ssc'] and props['is_height']:
            wl = props['wavelength_nm']
            if wl not in ssc_channels:
                ssc_channels[wl] = ch
    
    print(f"\n🎯 Using channels:")
    fsc_wl = scatter_channels.get(fsc_channel, {}).get('wavelength_nm', '?') if fsc_channel else '?'
    print(f"   FSC: {fsc_channel} ({fsc_wl}nm)")
    for wl, ch in sorted(ssc_channels.items()):
        print(f"   SSC@{wl}nm: {ch}")
    
    if fsc_channel is None:
        print("❌ No FSC channel found!")
        return {'error': 'No FSC channel found'}
    
    # Create Mie calculator
    fsc_wavelength = scatter_channels[fsc_channel]['wavelength_nm']
    calculator = StandaloneMieCalculator(
        wavelength_nm=fsc_wavelength,
        n_particle=n_particle,
        n_medium=n_medium
    )
    
    # Create wavelength disambiguator
    disambiguator = WavelengthDisambiguator(n_particle, n_medium)
    
    # Sample data for analysis
    print(f"\n⏳ Analyzing {sample_size} events...")
    
    # Get valid (positive) FSC values
    fsc_values: np.ndarray = np.asarray(data[fsc_channel].values, dtype=np.float64)
    valid_mask: np.ndarray = fsc_values > 0
    valid_indices = np.where(valid_mask)[0]
    
    if len(valid_indices) > sample_size:
        sample_indices = np.random.choice(valid_indices, sample_size, replace=False)
    else:
        sample_indices = valid_indices
    
    # Analyze each particle
    results = []
    ambiguous_count = 0
    
    # Get wavelength ratio if we have multiple SSC channels
    can_disambiguate = len(ssc_channels) >= 2
    wl1: int = 405  # Default wavelengths
    wl2: int = 488
    if can_disambiguate:
        wl_sorted = sorted(ssc_channels.keys())
        wl1, wl2 = wl_sorted[0], wl_sorted[1]  # Usually 405 and 488
        ssc1_channel = ssc_channels[wl1]
        ssc2_channel = ssc_channels[wl2]
        print(f"   Using {ssc1_channel}/{ssc2_channel} ratio for disambiguation")
    
    for i, idx in enumerate(sample_indices):
        if (i + 1) % 200 == 0:
            print(f"   Processed {i+1}/{len(sample_indices)}...")
        
        fsc = fsc_values[idx]
        
        # Find all possible solutions
        all_solutions = calculator.find_all_solutions(
            float(fsc),
            scatter_type='fsc',
            min_diameter=min_diameter,
            max_diameter=max_diameter,
            tolerance_pct=15.0
        )
        
        # Get SSC values
        ssc_vals = {}
        for wl, ch in ssc_channels.items():
            ssc_vals[wl] = float(data[ch].iloc[idx])
        
        # Disambiguate if multiple solutions
        if len(all_solutions) > 1:
            ambiguous_count += 1
            
            if can_disambiguate and ssc_vals.get(wl2, 0) > 0:
                measured_ratio = ssc_vals.get(wl1, 0) / ssc_vals[wl2]
                best_size, confidence = disambiguator.disambiguate_solutions(
                    all_solutions, measured_ratio, wl1, wl2
                )
                method = 'ratio-disambiguated'
            else:
                # Default to smallest solution (more conservative)
                best_size = min(all_solutions)
                confidence = 0.5
                method = 'smallest-default'
        elif len(all_solutions) == 1:
            best_size = all_solutions[0]
            confidence = 0.9
            method = 'single-solution'
        else:
            # No solution found - try expanding tolerance
            all_solutions = calculator.find_all_solutions(
                float(fsc), 'fsc', min_diameter, max_diameter, tolerance_pct=50.0
            )
            if all_solutions:
                best_size = all_solutions[0]
                confidence = 0.3
                method = 'expanded-tolerance'
            else:
                best_size = max_diameter  # Clamp to max
                confidence = 0.1
                method = 'clamped'
        
        results.append(ParticleSizeResult(
            event_index=int(idx),
            fsc_value=float(fsc),
            ssc_values=ssc_vals,
            all_solutions=all_solutions,
            best_solution=best_size,
            confidence=confidence,
            disambiguation_method=method
        ))
    
    print(f"   ✅ Analysis complete!")
    
    # Calculate statistics
    sizes = np.array([r.best_solution for r in results])
    confidences = np.array([r.confidence for r in results])
    
    small = np.sum((sizes >= 30) & (sizes < 100))
    medium = np.sum((sizes >= 100) & (sizes < 150))
    large = np.sum(sizes >= 150)
    
    # Print results
    print("\n" + "=" * 80)
    print("📊 RESULTS SUMMARY")
    print("=" * 80)
    
    print(f"""
📏 SIZE DISTRIBUTION (Multi-Solution with Disambiguation):
   Min:    {np.min(sizes):.1f} nm
   Max:    {np.max(sizes):.1f} nm
   Mean:   {np.mean(sizes):.1f} nm
   Median: {np.median(sizes):.1f} nm
   Std:    {np.std(sizes):.1f} nm

📊 SIZE CATEGORIES:
   Small (30-100nm):   {small:,} ({100*small/len(sizes):.1f}%)
   Medium (100-150nm): {medium:,} ({100*medium/len(sizes):.1f}%)
   Large (>150nm):     {large:,} ({100*large/len(sizes):.1f}%)

🔍 AMBIGUITY ANALYSIS:
   Particles with multiple solutions: {ambiguous_count} ({100*ambiguous_count/len(results):.1f}%)
   Average confidence: {np.mean(confidences):.2f}
   Low confidence (<0.5): {np.sum(confidences < 0.5)} events
""")
    
    # Method breakdown
    method_counts = {}
    for r in results:
        method_counts[r.disambiguation_method] = method_counts.get(r.disambiguation_method, 0) + 1
    
    print("📋 DISAMBIGUATION METHODS USED:")
    for method, count in sorted(method_counts.items(), key=lambda x: -x[1]):
        print(f"   {method}: {count} ({100*count/len(results):.1f}%)")
    
    # Generate output
    output_data = {
        'file': str(fcs_path),
        'analysis_date': datetime.now().isoformat(),
        'parameters': {
            'n_particle': n_particle,
            'n_medium': n_medium,
            'fsc_channel': fsc_channel,
            'fsc_wavelength_nm': fsc_wavelength,
            'ssc_channels': ssc_channels,
            'min_diameter': min_diameter,
            'max_diameter': max_diameter,
            'sample_size': len(results)
        },
        'statistics': {
            'min_size': float(np.min(sizes)),
            'max_size': float(np.max(sizes)),
            'mean_size': float(np.mean(sizes)),
            'median_size': float(np.median(sizes)),
            'std_size': float(np.std(sizes)),
            'small_count': int(small),
            'medium_count': int(medium),
            'large_count': int(large),
            'ambiguous_count': int(ambiguous_count),
            'avg_confidence': float(np.mean(confidences))
        },
        'method_counts': method_counts
    }
    
    # Save results
    if output_dir is None:
        output_dir = fcs_path.parent / 'mie_analysis'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save JSON summary
    json_file = output_dir / f'{fcs_path.stem}_mie_analysis.json'
    with open(json_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    print(f"\n💾 Summary saved to: {json_file}")
    
    # Save detailed CSV
    csv_data = []
    for r in results:
        csv_data.append({
            'event_index': r.event_index,
            'fsc_value': r.fsc_value,
            'best_size_nm': r.best_solution,
            'all_solutions': ';'.join([f'{s:.1f}' for s in r.all_solutions]),
            'num_solutions': len(r.all_solutions),
            'confidence': r.confidence,
            'method': r.disambiguation_method,
            **{f'ssc_{wl}nm': v for wl, v in r.ssc_values.items()}
        })
    
    csv_file = output_dir / f'{fcs_path.stem}_mie_sizes.csv'
    pd.DataFrame(csv_data).to_csv(csv_file, index=False)
    print(f"💾 Detailed results saved to: {csv_file}")
    
    # Generate plots if matplotlib is available
    if HAS_MATPLOTLIB:
        print("\n📈 Generating plots...")
        generate_analysis_plots(
            calculator, disambiguator, results, sizes, output_dir, fcs_path.stem
        )
    
    return output_data


# =============================================================================
# PLOTTING FUNCTIONS
# =============================================================================

def generate_analysis_plots(
    calculator: StandaloneMieCalculator,
    disambiguator: WavelengthDisambiguator,
    results: List[ParticleSizeResult],
    sizes: np.ndarray,
    output_dir: Path,
    file_stem: str
):
    """Generate diagnostic plots for the analysis."""
    if not HAS_MATPLOTLIB or plt is None:
        print("⚠️ Matplotlib not available - skipping plots")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Plot 1: Mie Scattering Curve (showing non-monotonicity)
    ax1 = axes[0, 0]
    diameters, fsc_curve, ssc_curve = calculator.get_scatter_curve(30, 300)
    ax1.plot(diameters, fsc_curve, 'b-', linewidth=2, label='Forward Scatter')
    ax1.plot(diameters, ssc_curve, 'r-', linewidth=2, label='Side Scatter')
    ax1.set_xlabel('Particle Diameter (nm)')
    ax1.set_ylabel('Scatter Intensity (a.u.)')
    ax1.set_title(f'Mie Scattering Curve (λ={calculator.wavelength_nm}nm)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_yscale('log')
    
    # Plot 2: Size Distribution Histogram
    ax2 = axes[0, 1]
    bins = np.arange(30, 305, 10)
    ax2.hist(sizes, bins=bins, color='steelblue', edgecolor='white', alpha=0.7)
    ax2.axvline(100, color='green', linestyle='--', label='Small/Medium boundary')
    ax2.axvline(150, color='orange', linestyle='--', label='Medium/Large boundary')
    ax2.set_xlabel('Particle Diameter (nm)')
    ax2.set_ylabel('Count')
    ax2.set_title('Size Distribution (Multi-Solution)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Wavelength Ratio Curve
    ax3 = axes[1, 0]
    d_ratio, ratios = disambiguator.build_ratio_curve(30, 300, 1.0, 405, 488)
    ax3.plot(d_ratio, ratios, 'purple', linewidth=2)
    ax3.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5)
    ax3.axhline(y=2.1, color='green', linestyle=':', label='Rayleigh (λ⁻⁴) ratio')
    ax3.set_xlabel('Particle Diameter (nm)')
    ax3.set_ylabel('VSSC/BSSC Ratio (405nm/488nm)')
    ax3.set_title('Wavelength Ratio vs Particle Size')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(0, 10)
    
    # Plot 4: Confidence Distribution
    ax4 = axes[1, 1]
    confidences = [r.confidence for r in results]
    ax4.hist(confidences, bins=20, color='coral', edgecolor='white', alpha=0.7)
    ax4.axvline(np.mean(confidences), color='red', linestyle='--', 
                label=f'Mean: {np.mean(confidences):.2f}')
    ax4.set_xlabel('Confidence Score')
    ax4.set_ylabel('Count')
    ax4.set_title('Size Estimation Confidence')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    plot_file = output_dir / f'{file_stem}_mie_analysis.png'
    plt.savefig(plot_file, dpi=150)
    plt.close()
    print(f"   📊 Plot saved to: {plot_file}")
    
    # Additional plot: Show examples of ambiguous particles
    ambiguous_results = [r for r in results if len(r.all_solutions) > 1][:5]
    
    if ambiguous_results:
        fig2, ax = plt.subplots(figsize=(12, 6))
        
        diameters, fsc_curve, _ = calculator.get_scatter_curve(30, 300)
        ax.plot(diameters, fsc_curve, 'b-', linewidth=2, alpha=0.5, label='Mie Curve')
        
        cmap = plt.colormaps.get_cmap('tab10')  # type: ignore
        colors = cmap(np.linspace(0, 1, len(ambiguous_results)))
        
        for i, r in enumerate(ambiguous_results):
            # Draw horizontal line at measured FSC
            ax.axhline(y=r.fsc_value, color=colors[i], linestyle='--', alpha=0.7)
            
            # Mark all solutions
            for sol in r.all_solutions:
                ax.scatter([sol], [r.fsc_value], s=100, c=[colors[i]], 
                          marker='o', edgecolors='black', zorder=5)
            
            # Mark best solution
            ax.scatter([r.best_solution], [r.fsc_value], s=150, c=[colors[i]], 
                      marker='*', edgecolors='black', zorder=6,
                      label=f'FSC={r.fsc_value:.0f} → {r.best_solution:.0f}nm')
        
        ax.set_xlabel('Particle Diameter (nm)')
        ax.set_ylabel('FSC Intensity')
        ax.set_title('Examples of Ambiguous Particles (Multiple Solutions)')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.set_yscale('log')
        
        plt.tight_layout()
        plot_file2 = output_dir / f'{file_stem}_ambiguous_examples.png'
        plt.savefig(plot_file2, dpi=150)
        plt.close()
        print(f"   📊 Ambiguous examples plot saved to: {plot_file2}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point for command-line usage."""
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        # Default to PC3 EXO1.fcs if no argument provided
        backend_path = Path(__file__).parent.parent
        fcs_path = backend_path / 'nanoFACS' / 'Exp_20251217_PC3' / 'PC3 EXO1.fcs'
        
        if not fcs_path.exists():
            print("Usage: python standalone_mie_multisolution.py <fcs_file_path>")
            print("\nExample:")
            print("  python standalone_mie_multisolution.py nanoFACS/Exp_20251217_PC3/PC3\\ EXO1.fcs")
            sys.exit(1)
    else:
        fcs_path = Path(sys.argv[1])
    
    if not fcs_path.exists():
        print(f"❌ File not found: {fcs_path}")
        sys.exit(1)
    
    # Run analysis
    analyze_fcs_multi_solution(
        fcs_path=fcs_path,
        n_particle=1.40,  # EV refractive index
        n_medium=1.33,    # PBS
        min_diameter=30.0,
        max_diameter=300.0,
        sample_size=2000
    )
    
    print("\n✅ Analysis complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()
