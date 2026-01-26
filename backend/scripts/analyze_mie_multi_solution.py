"""
Mie Scattering Multi-Solution Analysis for PC3 EXO1
====================================================

This script analyzes the PC3 EXO1.fcs file to:
1. Extract all available channels and identify SSC wavelengths
2. Show current size distribution using existing Mie implementation
3. Identify potential mis-sizing by finding ALL possible size solutions
4. Calculate scatter ratios for multi-wavelength disambiguation

Created: January 21, 2026
Purpose: Investigate why 70-80% of particles show as "large"
"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from src.parsers.fcs_parser import FCSParser
from src.physics.mie_scatter import MieScatterCalculator
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stdout, format="{time:HH:mm:ss} | {level} | {message}", level="INFO")


# =============================================================================
# Standard Flow Cytometry Laser Wavelengths
# =============================================================================

LASER_WAVELENGTHS = {
    # Channel prefix: (wavelength_nm, laser_color, description)
    'V': (405, 'Violet', 'Violet laser - best for small EV detection'),
    'B': (488, 'Blue', 'Blue/Argon laser - standard'),
    'Y': (561, 'Yellow-Green', 'Yellow-green laser'),
    'R': (633, 'Red', 'Red/HeNe laser'),
    'UV': (355, 'UV', 'Ultraviolet laser'),
}

# Common channel name patterns and their wavelengths
CHANNEL_WAVELENGTH_MAP = {
    'VFSC': 405,   # Violet Forward Scatter
    'VSSC': 405,   # Violet Side Scatter
    'VSSC1': 405,  # Violet Side Scatter 1
    'VSSC2': 405,  # Violet Side Scatter 2
    'BSSC': 488,   # Blue Side Scatter
    'FSC': 488,    # Forward Scatter (typically blue)
    'SSC': 488,    # Side Scatter (typically blue)
    'LALS': 488,   # Large Angle Light Scatter
    'SALS': 488,   # Small Angle Light Scatter
    'V447': 405,   # Violet 447nm detector
    'V525': 405,   # Violet 525nm detector
    'B531': 488,   # Blue 531nm detector
    'Y595': 561,   # Yellow-Green 595nm detector
    'R670': 633,   # Red 670nm detector
    'R710': 633,   # Red 710nm detector
    'R792': 633,   # Red 792nm detector
}


@dataclass
class ChannelInfo:
    """Information about a single FCS channel."""
    name: str
    wavelength_nm: Optional[int]
    laser_color: Optional[str]
    channel_type: str  # 'scatter', 'fluorescence', 'other'
    min_val: float
    max_val: float
    mean_val: float
    median_val: float
    positive_pct: float


def classify_channel(channel_name: str) -> Tuple[Optional[int], Optional[str], str]:
    """
    Classify a channel by wavelength, laser color, and type.
    
    Returns:
        Tuple of (wavelength_nm, laser_color, channel_type)
    """
    name_upper = channel_name.upper()
    
    # Check for scatter channels
    if 'FSC' in name_upper or 'SSC' in name_upper or 'LALS' in name_upper or 'SALS' in name_upper:
        channel_type = 'scatter'
    elif any(x in name_upper for x in ['V4', 'V5', 'B5', 'Y5', 'Y6', 'R6', 'R7']):
        channel_type = 'fluorescence'
    else:
        channel_type = 'other'
    
    # Find wavelength from known patterns
    for pattern, wavelength in CHANNEL_WAVELENGTH_MAP.items():
        if pattern in name_upper:
            laser = None
            for prefix, (wl, color, _) in LASER_WAVELENGTHS.items():
                if wl == wavelength:
                    laser = color
                    break
            return wavelength, laser, channel_type
    
    # Try to infer from first character
    first_char = name_upper[0] if name_upper else ''
    if first_char in LASER_WAVELENGTHS:
        wl, color, _ = LASER_WAVELENGTHS[first_char]
        return wl, color, channel_type
    
    return None, None, channel_type


def analyze_channels(data: pd.DataFrame) -> List[ChannelInfo]:
    """Analyze all channels in the FCS data."""
    channels = []
    
    for col in data.columns:
        # Skip metadata columns
        if col.startswith(('sample_', 'biological_', 'measurement_', 'is_', 'file_', 'instrument_', 'parse_')):
            continue
        
        values: np.ndarray = np.asarray(data[col].values, dtype=np.float64)
        positive_values = values[values > 0]
        
        wavelength, laser, ch_type = classify_channel(col)
        
        channels.append(ChannelInfo(
            name=col,
            wavelength_nm=wavelength,
            laser_color=laser,
            channel_type=ch_type,
            min_val=float(np.min(values)),
            max_val=float(np.max(values)),
            mean_val=float(np.mean(values)),
            median_val=float(np.median(values)),
            positive_pct=100 * len(positive_values) / len(values) if len(values) > 0 else 0
        ))
    
    return channels


def find_all_size_solutions(
    calculator: MieScatterCalculator,
    fsc_intensity: float,
    min_diameter: float = 30.0,
    max_diameter: float = 300.0,
    resolution: float = 1.0,
    tolerance_pct: float = 5.0
) -> List[float]:
    """
    Find ALL particle sizes that could produce the given FSC intensity.
    
    Unlike the standard diameter_from_scatter which returns ONE solution,
    this function returns ALL diameters where the calculated FSC matches
    the measured value within tolerance.
    
    Args:
        calculator: MieScatterCalculator instance
        fsc_intensity: Measured forward scatter intensity
        min_diameter: Minimum diameter to search (nm)
        max_diameter: Maximum diameter to search (nm)
        resolution: Step size for diameter search (nm)
        tolerance_pct: Acceptable error percentage
        
    Returns:
        List of all diameters (nm) that could produce this FSC value
    """
    solutions = []
    tolerance = fsc_intensity * (tolerance_pct / 100.0)
    
    # Scan through all possible diameters
    diameters = np.arange(min_diameter, max_diameter + resolution, resolution)
    
    for d in diameters:
        result = calculator.calculate_scattering_efficiency(float(d), validate=False)
        if abs(result.forward_scatter - fsc_intensity) <= tolerance:
            # Check if this is a new solution (not too close to previous)
            if not solutions or abs(d - solutions[-1]) > 5:  # 5nm minimum gap
                solutions.append(float(d))
    
    return solutions


def calculate_size_distribution_single(
    calculator: MieScatterCalculator,
    fsc_values: np.ndarray,
    min_d: float = 30.0,
    max_d: float = 300.0
) -> np.ndarray:
    """Calculate size distribution using current single-solution approach."""
    sizes = []
    for fsc in fsc_values:
        if fsc > 0:
            diameter, _ = calculator.diameter_from_scatter(fsc, min_d, max_d)
            sizes.append(diameter)
        else:
            sizes.append(np.nan)
    return np.array(sizes)


def calculate_size_distribution_multi(
    calculator: MieScatterCalculator,
    fsc_values: np.ndarray,
    min_d: float = 30.0,
    max_d: float = 300.0,
    sample_size: int = 1000
) -> Dict:
    """
    Calculate size distribution showing ALL possible solutions.
    
    Returns dictionary with:
    - single_solutions: Current approach (one size per particle)
    - multi_solutions: All possible sizes per particle
    - ambiguity_stats: How many particles have multiple solutions
    """
    # Sample for performance (full analysis would be too slow)
    if len(fsc_values) > sample_size:
        indices = np.random.choice(len(fsc_values), sample_size, replace=False)
        fsc_sample = fsc_values[indices]
    else:
        fsc_sample = fsc_values
        indices = np.arange(len(fsc_values))
    
    single_solutions = []
    multi_solutions = []
    ambiguous_count = 0
    
    for i, fsc in enumerate(fsc_sample):
        if fsc <= 0:
            single_solutions.append(np.nan)
            multi_solutions.append([])
            continue
        
        # Single solution (current approach)
        diameter, _ = calculator.diameter_from_scatter(fsc, min_d, max_d)
        single_solutions.append(diameter)
        
        # Multiple solutions (new approach)
        all_solutions = find_all_size_solutions(calculator, fsc, min_d, max_d)
        multi_solutions.append(all_solutions)
        
        if len(all_solutions) > 1:
            ambiguous_count += 1
        
        # Progress logging
        if (i + 1) % 200 == 0:
            logger.info(f"  Processed {i+1}/{len(fsc_sample)} particles...")
    
    return {
        'single_solutions': np.array(single_solutions),
        'multi_solutions': multi_solutions,
        'ambiguous_count': ambiguous_count,
        'ambiguous_pct': 100 * ambiguous_count / len(fsc_sample),
        'total_analyzed': len(fsc_sample)
    }


def analyze_wavelength_ratios(
    data: pd.DataFrame,
    channel_pairs: List[Tuple[str, str]]
) -> Dict:
    """
    Calculate scatter ratios between different wavelength channels.
    
    Small particles: higher ratio (Rayleigh - shorter wavelength scatters more)
    Large particles: ratio ≈ 1 (Geometric - wavelength independent)
    """
    results = {}
    
    for ch1, ch2 in channel_pairs:
        if ch1 not in data.columns or ch2 not in data.columns:
            continue
        
        v1: np.ndarray = np.asarray(data[ch1].values, dtype=np.float64)
        v2: np.ndarray = np.asarray(data[ch2].values, dtype=np.float64)
        
        # Only calculate ratio where both are positive
        valid = (v1 > 0) & (v2 > 0)
        ratios = np.zeros(len(v1))
        ratios[valid] = v1[valid] / v2[valid]
        ratios[~valid] = np.nan
        
        results[f'{ch1}/{ch2}'] = {
            'ratios': ratios,
            'mean_ratio': float(np.nanmean(ratios)),
            'median_ratio': float(np.nanmedian(ratios)),
            'valid_count': int(np.sum(valid)),
            'high_ratio_count': int(np.sum(ratios > 1.5)),  # Likely small particles
            'low_ratio_count': int(np.sum((ratios < 1.5) & (ratios > 0))),  # Likely large
        }
    
    return results


def main():
    """Main analysis function for PC3 EXO1.fcs"""
    
    print("=" * 80)
    print("🔬 MIE SCATTERING MULTI-SOLUTION ANALYSIS")
    print("   File: PC3 EXO1.fcs")
    print("   Date: January 21, 2026")
    print("=" * 80)
    
    # Load the FCS file
    fcs_path = backend_path / 'nanoFACS' / 'Exp_20251217_PC3' / 'PC3 EXO1.fcs'
    
    if not fcs_path.exists():
        logger.error(f"❌ File not found: {fcs_path}")
        return
    
    logger.info(f"\n📂 Loading: {fcs_path.name}")
    
    parser = FCSParser(fcs_path)
    if not parser.validate():
        logger.error("❌ FCS validation failed")
        return
    
    data = parser.parse()
    logger.info(f"✅ Loaded {len(data):,} events")
    
    # ==========================================================================
    # STEP 1: Analyze All Channels
    # ==========================================================================
    print("\n" + "=" * 80)
    print("📊 STEP 1: CHANNEL ANALYSIS")
    print("=" * 80)
    
    channels = analyze_channels(data)
    
    # Group by type
    scatter_channels = [c for c in channels if c.channel_type == 'scatter']
    fluor_channels = [c for c in channels if c.channel_type == 'fluorescence']
    other_channels = [c for c in channels if c.channel_type == 'other']
    
    print(f"\n📡 Scatter Channels ({len(scatter_channels)}):")
    print("-" * 70)
    print(f"{'Channel':<12} {'Wavelength':<12} {'Laser':<10} {'Mean':<12} {'Median':<12} {'Pos%':<8}")
    print("-" * 70)
    for ch in scatter_channels:
        wl_str = f"{ch.wavelength_nm}nm" if ch.wavelength_nm else "Unknown"
        laser_str = ch.laser_color or "?"
        print(f"{ch.name:<12} {wl_str:<12} {laser_str:<10} {ch.mean_val:<12.1f} {ch.median_val:<12.1f} {ch.positive_pct:<8.1f}")
    
    print(f"\n🔬 Fluorescence Channels ({len(fluor_channels)}):")
    print("-" * 70)
    for ch in fluor_channels:
        wl_str = f"{ch.wavelength_nm}nm" if ch.wavelength_nm else "Unknown"
        laser_str = ch.laser_color or "?"
        print(f"{ch.name:<12} {wl_str:<12} {laser_str:<10} {ch.mean_val:<12.1f} {ch.median_val:<12.1f} {ch.positive_pct:<8.1f}")
    
    # ==========================================================================
    # STEP 2: Current Size Distribution (Single Solution)
    # ==========================================================================
    print("\n" + "=" * 80)
    print("📊 STEP 2: CURRENT SIZE DISTRIBUTION (Single Solution Approach)")
    print("=" * 80)
    
    # Find the primary FSC channel
    fsc_channel = None
    for ch in scatter_channels:
        if 'VFSC' in ch.name.upper():
            fsc_channel = ch.name
            break
    if not fsc_channel:
        for ch in scatter_channels:
            if 'FSC' in ch.name.upper():
                fsc_channel = ch.name
                break
    
    if not fsc_channel:
        logger.error("❌ No FSC channel found!")
        return
    
    logger.info(f"\n🎯 Using FSC channel: {fsc_channel}")
    
    # Initialize Mie calculator (405nm for violet laser)
    calculator = MieScatterCalculator(
        wavelength_nm=405.0,  # Violet laser
        n_particle=1.40,      # EV refractive index
        n_medium=1.33         # PBS
    )
    
    fsc_values: np.ndarray = np.asarray(data[fsc_channel].values, dtype=np.float64)
    positive_fsc = fsc_values[fsc_values > 0]
    
    logger.info(f"   Total events: {len(fsc_values):,}")
    logger.info(f"   Positive FSC: {len(positive_fsc):,} ({100*len(positive_fsc)/len(fsc_values):.1f}%)")
    
    # Calculate sizes using current approach (sample for speed)
    sample_size = min(5000, len(positive_fsc))
    sample_indices = np.random.choice(len(positive_fsc), sample_size, replace=False)
    fsc_sample = positive_fsc[sample_indices]
    
    logger.info(f"\n⏳ Calculating sizes for {sample_size:,} particles...")
    sizes_single = calculate_size_distribution_single(calculator, fsc_sample)
    
    # Size distribution statistics
    valid_sizes = sizes_single[~np.isnan(sizes_single)]
    
    print(f"\n📏 Size Distribution (Current Single-Solution Approach):")
    print("-" * 50)
    print(f"   Min:    {np.min(valid_sizes):.1f} nm")
    print(f"   Max:    {np.max(valid_sizes):.1f} nm")
    print(f"   Mean:   {np.mean(valid_sizes):.1f} nm")
    print(f"   Median: {np.median(valid_sizes):.1f} nm")
    print(f"   Std:    {np.std(valid_sizes):.1f} nm")
    
    # Size categories
    small = np.sum((valid_sizes >= 30) & (valid_sizes < 100))
    medium = np.sum((valid_sizes >= 100) & (valid_sizes < 150))
    large = np.sum(valid_sizes >= 150)
    
    print(f"\n📊 Size Categories:")
    print(f"   Small (30-100nm):   {small:,} ({100*small/len(valid_sizes):.1f}%)")
    print(f"   Medium (100-150nm): {medium:,} ({100*medium/len(valid_sizes):.1f}%)")
    print(f"   Large (>150nm):     {large:,} ({100*large/len(valid_sizes):.1f}%)")
    
    # ==========================================================================
    # STEP 3: Multi-Solution Analysis
    # ==========================================================================
    print("\n" + "=" * 80)
    print("📊 STEP 3: MULTI-SOLUTION ANALYSIS (Finding ALL Possible Sizes)")
    print("=" * 80)
    
    # Analyze a smaller sample for multi-solution (computationally intensive)
    multi_sample_size = 500
    logger.info(f"\n⏳ Analyzing {multi_sample_size} particles for multiple solutions...")
    
    multi_results = calculate_size_distribution_multi(
        calculator, 
        fsc_sample[:multi_sample_size],
        min_d=30.0,
        max_d=300.0
    )
    
    print(f"\n🔍 Multi-Solution Results:")
    print("-" * 50)
    print(f"   Particles analyzed: {multi_results['total_analyzed']}")
    print(f"   Ambiguous (multiple solutions): {multi_results['ambiguous_count']} ({multi_results['ambiguous_pct']:.1f}%)")
    
    # Show examples of ambiguous particles
    print(f"\n📋 Examples of Ambiguous Particles:")
    print("-" * 60)
    print(f"{'FSC Value':<15} {'Single Solution':<18} {'All Solutions':<25}")
    print("-" * 60)
    
    example_count = 0
    for i, (single, multi) in enumerate(zip(multi_results['single_solutions'], multi_results['multi_solutions'])):
        if len(multi) > 1 and example_count < 10:
            multi_str = ', '.join([f"{d:.0f}" for d in multi])
            print(f"{fsc_sample[i]:<15.1f} {single:<18.1f} {multi_str:<25}")
            example_count += 1
    
    # ==========================================================================
    # STEP 4: Multi-Wavelength Ratio Analysis
    # ==========================================================================
    print("\n" + "=" * 80)
    print("📊 STEP 4: MULTI-WAVELENGTH RATIO ANALYSIS")
    print("=" * 80)
    
    # Find channel pairs at different wavelengths
    channel_pairs = []
    
    # Look for VSSC vs BSSC pairs
    vssc_channels = [c.name for c in scatter_channels if 'VSSC' in c.name.upper()]
    bssc_channels = [c.name for c in scatter_channels if 'BSSC' in c.name.upper()]
    
    if vssc_channels and bssc_channels:
        for v in vssc_channels:
            for b in bssc_channels:
                channel_pairs.append((v, b))
    
    # Also try VFSC vs FSC if available
    vfsc_channels = [c.name for c in scatter_channels if 'VFSC' in c.name.upper()]
    fsc_channels = [c.name for c in scatter_channels if c.name.upper() in ['FSC-H', 'FSC-A']]
    
    if channel_pairs:
        logger.info(f"\n🔍 Analyzing scatter ratios for {len(channel_pairs)} channel pairs...")
        ratio_results = analyze_wavelength_ratios(data, channel_pairs)
        
        print(f"\n📊 Scatter Ratio Analysis (Violet vs Blue):")
        print("-" * 70)
        print(f"{'Ratio Pair':<20} {'Mean':<10} {'Median':<10} {'High(>1.5)':<12} {'Low(<1.5)':<12}")
        print("-" * 70)
        
        for pair_name, stats in ratio_results.items():
            print(f"{pair_name:<20} {stats['mean_ratio']:<10.3f} {stats['median_ratio']:<10.3f} "
                  f"{stats['high_ratio_count']:<12,} {stats['low_ratio_count']:<12,}")
        
        print("\n💡 Interpretation:")
        print("   - Ratio > 1.5: Indicates SMALLER particles (Rayleigh regime)")
        print("   - Ratio ≈ 1.0: Indicates LARGER particles (Geometric regime)")
    else:
        print("\n⚠️  No suitable channel pairs found for multi-wavelength analysis")
        print("   Available scatter channels:", [c.name for c in scatter_channels])
    
    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    print("\n" + "=" * 80)
    print("📋 ANALYSIS SUMMARY")
    print("=" * 80)
    
    print(f"""
🎯 KEY FINDINGS:

1. CURRENT SIZE DISTRIBUTION (Single-Solution):
   - {100*large/len(valid_sizes):.1f}% classified as LARGE (>150nm)
   - {100*small/len(valid_sizes):.1f}% classified as SMALL (30-100nm)
   - This may NOT reflect actual distribution due to Mie ambiguity

2. MULTI-SOLUTION ANALYSIS:
   - {multi_results['ambiguous_pct']:.1f}% of particles have MULTIPLE possible sizes
   - Current algorithm picks ONE solution (likely biased toward larger sizes)
   - Particles marked as 200nm might actually be 60nm or 120nm

3. MULTI-WAVELENGTH DATA:
   - {'Found suitable channel pairs' if channel_pairs else 'No suitable channel pairs found'}
   - {'Can use VSSC/BSSC ratio for disambiguation' if channel_pairs else 'Need to check raw FCS metadata for wavelength info'}

4. RECOMMENDATIONS:
   a) Create multi-solution Mie calculator that returns ALL possible sizes
   b) Use VSSC/BSSC ratios to select correct solution
   c) Validate against NTA data which gives unambiguous sizes
   d) Consider adjusting refractive index (n=1.40 may not be optimal)
""")
    
    # Save results
    output_dir = backend_path / 'data' / 'validation'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save channel info
    channel_df = pd.DataFrame([{
        'name': c.name,
        'wavelength_nm': c.wavelength_nm,
        'laser_color': c.laser_color,
        'type': c.channel_type,
        'mean': c.mean_val,
        'median': c.median_val,
        'positive_pct': c.positive_pct
    } for c in channels])
    
    channel_file = output_dir / 'pc3_exo1_channels.csv'
    channel_df.to_csv(channel_file, index=False)
    logger.info(f"\n💾 Channel info saved to: {channel_file}")
    
    # Save size distribution
    size_df = pd.DataFrame({
        'fsc_value': fsc_sample[:len(sizes_single)],
        'diameter_nm': sizes_single
    })
    size_file = output_dir / 'pc3_exo1_sizes.csv'
    size_df.to_csv(size_file, index=False)
    logger.info(f"💾 Size distribution saved to: {size_file}")
    
    print("\n✅ Analysis complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()
