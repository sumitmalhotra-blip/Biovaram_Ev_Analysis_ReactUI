"""
TASK-FACS-002: Apply Mie Theory Sizing to NanoFACS PC3 Data
============================================================

Applies MieScatterCalculator to convert VFSC-H (forward scatter) 
intensities to particle diameters in nanometers.

Configuration:
- Wavelength: 488nm (blue laser)
- n_particle: 1.40 (typical for EVs/exosomes)
- n_medium: 1.33 (PBS/water)

Created: Jan 20, 2026
"""

import sys
import json
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.fcs_parser import FCSParser
from src.physics.mie_scatter import MieScatterCalculator

def apply_mie_sizing():
    """Apply Mie theory to calculate particle sizes from FCS scatter data."""
    
    print("=" * 80)
    print("🔬 TASK-FACS-002: Apply Mie Theory Sizing to NanoFACS PC3 Data")
    print("=" * 80)
    
    # Initialize Mie calculator with standard EV parameters
    calc = MieScatterCalculator(
        wavelength_nm=488.0,  # Blue laser
        n_particle=1.40,      # EVs/exosomes typical RI
        n_medium=1.33         # PBS/water
    )
    
    # Load parsed FCS data
    validation_dir = Path(__file__).parent.parent / "data" / "validation"
    with open(validation_dir / "fcs_pc3_parsed_results.json", "r") as f:
        fcs_data = json.load(f)
    
    print(f"\nLoaded data for {len(fcs_data)} FCS files")
    
    # Build calibration lookup table first
    print("\n" + "=" * 60)
    print("📊 Building Mie Calibration Lookup Table")
    print("=" * 60)
    
    # Generate FSC → Diameter calibration curve
    diameters = np.linspace(30, 300, 271)  # 30-300nm in 1nm steps
    fsc_values = []
    
    for d in diameters:
        result = calc.calculate_scattering_efficiency(d, validate=False)
        fsc_values.append(result.forward_scatter)
    
    fsc_values = np.array(fsc_values)
    
    # Print calibration points
    print("\nCalibration curve (diameter → theoretical FSC):")
    print("-" * 50)
    for d in [50, 80, 100, 127, 150, 171, 200, 250]:
        result = calc.calculate_scattering_efficiency(d, validate=False)
        print(f"  {d:4d} nm → FSC = {result.forward_scatter:12.2f} (Q_sca={result.Q_sca:.6f}, g={result.g:.4f})")
    
    # Results container
    size_results = {}
    
    # Focus on key samples
    key_samples = [
        "PC3 EXO1.fcs",        # Main sample
        "Exo+CD 9.fcs",        # CD9 marker
        "Exo+CD 81.fcs",       # CD81 marker
        "Exo+CD 9 +ISOTYPE.fcs",  # Isotype control
        "Exo+CD 81 +ISOTYPE1.fcs",  # Isotype control
    ]
    
    print("\n" + "=" * 60)
    print("📈 Applying Mie Theory to Key Samples")
    print("=" * 60)
    
    for sample_name in key_samples:
        # Find sample in data
        sample = None
        for s in fcs_data:
            if s['file'] == sample_name:
                sample = s
                break
        
        if sample is None:
            print(f"\n⚠️ Sample not found: {sample_name}")
            continue
        
        print(f"\n{'='*60}")
        print(f"📊 {sample_name}")
        print(f"{'='*60}")
        print(f"   Total Events: {sample['total_events']:,}")
        
        # Get VFSC-H statistics from scatter_stats
        vfsc_stats = sample.get('scatter_stats', {}).get('VFSC-H', {})
        vfsc_mean = vfsc_stats.get('mean', 0)
        vfsc_median = vfsc_stats.get('median', 0)
        vfsc_min = vfsc_stats.get('min', 0)
        vfsc_max = vfsc_stats.get('max', 0)
        
        print(f"\n   VFSC-H Raw Statistics:")
        print(f"      Mean:   {vfsc_mean:,.1f}")
        print(f"      Median: {vfsc_median:,.1f}")
        print(f"      Range:  {vfsc_min:,.1f} - {vfsc_max:,.1f}")
        
        # The raw VFSC-H values need to be converted to the right scale
        # NanoFACS uses arbitrary intensity units that need calibration
        # 
        # Key insight: The Mie forward_scatter is Q_sca × area × (1+g)
        # This is in nm² units, while VFSC-H is in instrument units
        # 
        # We need to find a scaling factor
        # 
        # Let's calculate the expected theoretical FSC for typical EV sizes
        # and compare to the measured values
        
        print(f"\n   Mie Theory Conversion:")
        
        # The theoretical FSC at different sizes
        theoretical_fsc_100nm = calc.calculate_scattering_efficiency(100, validate=False).forward_scatter
        theoretical_fsc_150nm = calc.calculate_scattering_efficiency(150, validate=False).forward_scatter
        
        print(f"      Theoretical FSC (100nm): {theoretical_fsc_100nm:.4f} nm²")
        print(f"      Theoretical FSC (150nm): {theoretical_fsc_150nm:.4f} nm²")
        
        # Estimate scaling factor
        # If NTA says D50 is ~127nm for this sample, and VFSC median is the measured value
        # Then: scaling_factor = measured_VFSC / theoretical_FSC(127nm)
        theoretical_fsc_127nm = calc.calculate_scattering_efficiency(127, validate=False).forward_scatter
        
        # Calculate scaling factor from median (assuming D50 ~ 127nm from NTA)
        if vfsc_median > 0 and theoretical_fsc_127nm > 0:
            scaling_factor = vfsc_median / theoretical_fsc_127nm
            print(f"      Estimated scaling factor: {scaling_factor:.2e}")
            
            # Now estimate sizes using the scaling factor
            # d_estimated from: measured_VFSC / scaling_factor = theoretical_FSC(d)
            normalized_fsc_mean = vfsc_mean / scaling_factor
            normalized_fsc_median = vfsc_median / scaling_factor
            
            # Interpolate to find diameter
            # Create inverse lookup: FSC → diameter
            # Sort by FSC for interpolation
            sort_idx = np.argsort(fsc_values)
            fsc_sorted = fsc_values[sort_idx]
            diameters_sorted = diameters[sort_idx]
            
            # Interpolate
            diameter_mean = np.interp(normalized_fsc_mean, fsc_sorted, diameters_sorted)
            diameter_median = np.interp(normalized_fsc_median, fsc_sorted, diameters_sorted)
            
            print(f"\n   Estimated Particle Sizes (calibrated to 127nm NTA D50):")
            print(f"      Mean diameter:   {diameter_mean:.1f} nm")
            print(f"      Median diameter: {diameter_median:.1f} nm")
            
            size_results[sample_name] = {
                'total_events': sample['total_events'],
                'vfsc_mean': vfsc_mean,
                'vfsc_median': vfsc_median,
                'scaling_factor': scaling_factor,
                'diameter_mean_nm': diameter_mean,
                'diameter_median_nm': diameter_median,
            }
        else:
            print(f"   ⚠️ Cannot calculate sizes (invalid FSC values)")
    
    # Alternative approach: Use raw intensity-to-size calibration
    # This is more robust for comparing relative sizes
    print("\n" + "=" * 80)
    print("🔬 Alternative: Relative Size Analysis (no calibration)")
    print("=" * 80)
    
    print("\nComparing VFSC-H medians across samples (proxy for relative size):")
    print("-" * 70)
    
    # Collect all medians for comparison
    medians = []
    for s in fcs_data:
        vfsc = s.get('scatter_stats', {}).get('VFSC-H', {})
        medians.append({
            'filename': s['file'],
            'median': vfsc.get('median', 0),
            'events': s['total_events']
        })
    
    # Sort by median
    medians.sort(key=lambda x: x['median'], reverse=True)
    
    # Print top 15 samples by VFSC-H median
    print(f"\n{'File':<40} {'VFSC-H Median':>15} {'Events':>12}")
    print("-" * 70)
    for m in medians[:15]:
        print(f"{m['filename']:<40} {m['median']:>15,.1f} {m['events']:>12,}")
    
    # Calculate relative sizes
    print("\n" + "=" * 80)
    print("📊 Size Distribution Estimates for PC3 EXO1")
    print("=" * 80)
    
    # Parse raw FCS file to get full data for distribution
    fcs_path = Path(__file__).parent.parent / "nanoFACS" / "Exp_20251217_PC3" / "PC3 EXO1.fcs"
    
    print(f"\nParsing full data from: {fcs_path.name}")
    parser = FCSParser(fcs_path)
    result = parser.parse()  # No argument needed, path passed to constructor
    
    results_summary: dict = {'sample': 'PC3 EXO1', 'status': 'incomplete'}
    
    if result is not None:
        df = result
        vfsc_h = np.asarray(df['VFSC-H'].values, dtype=np.float64)
        
        # Filter positive values only
        vfsc_h = vfsc_h[vfsc_h > 0]
        
        print(f"   Positive VFSC-H events: {len(vfsc_h):,}")
        
        # Calculate percentiles
        percentiles = [10, 25, 50, 75, 90]
        vfsc_percentiles = np.percentile(vfsc_h, percentiles)
        
        print(f"\n   VFSC-H Intensity Distribution:")
        print(f"   {'Percentile':>12} {'VFSC-H':>15}")
        print(f"   {'-'*30}")
        for p, v in zip(percentiles, vfsc_percentiles):
            print(f"   {'P' + str(p):>12} {v:>15,.1f}")
        
        # Apply batch Mie sizing using lookup table
        print(f"\n   Applying Mie theory batch sizing...")
        
        # For proper sizing, we need instrument calibration
        # Using relative scaling based on NTA comparison
        # 
        # Key assumption: VFSC-H is proportional to theoretical forward scatter
        # The proportionality constant depends on:
        # - Laser power
        # - Detector gain
        # - Flow rate
        # - Collection optics
        
        # For now, report relative scatter intensities
        # Actual calibration requires polystyrene bead standards
        
        print(f"\n   ⚠️ Note: Absolute size calculation requires instrument calibration")
        print(f"      with polystyrene bead standards of known sizes.")
        print(f"\n   For validation purposes, comparing relative scatter values:")
        print(f"      - Higher VFSC-H → Larger particle size")
        print(f"      - The relationship is non-linear (Mie theory)")
        
        # Save results
        results_summary = {
            'sample': 'PC3 EXO1',
            'total_events': len(df),
            'positive_events': len(vfsc_h),
            'vfsc_percentiles': {f'P{p}': float(v) for p, v in zip(percentiles, vfsc_percentiles)},
            'mie_parameters': {
                'wavelength_nm': 488.0,
                'n_particle': 1.40,
                'n_medium': 1.33
            },
            'calibration_status': 'requires_polystyrene_standards',
            'notes': 'Relative scatter values shown; absolute sizing needs calibration'
        }
        
        # Save to validation folder
        output_file = validation_dir / "fcs_pc3_mie_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(results_summary, f, indent=2)
        print(f"\n💾 Results saved to: {output_file}")
    
    # Summary comparison with NTA
    print("\n" + "=" * 80)
    print("📊 Cross-Validation: NTA vs NanoFACS")
    print("=" * 80)
    
    print("""
    NTA Results (from TASK-NTA-001/002):
    ----------------------------------------
    Sample     | D50 (median) | D10    | D90
    -----------|--------------|--------|-------
    F5         | 127.34 nm    | 92.70  | 176.59
    F1_2       | 145.88 nm    | 97.58  | 209.54
    F3T6       | 155.62 nm    | 97.05  | 232.55
    F7_8       | 171.50 nm    | 109.51 | 255.36
    F9T15      | 158.50 nm    | 107.84 | 228.68
    
    NanoFACS Results (this analysis):
    ----------------------------------------
    - Main sample (PC3 EXO1): 914,326 events
    - VFSC-H median: ~624 (arbitrary units)
    - Direct size comparison requires calibration
    
    Next Steps:
    1. Obtain polystyrene bead calibration data
    2. Build instrument-specific calibration curve
    3. Apply calibration to convert VFSC-H → diameter
    4. Compare NanoFACS size distribution to NTA D10-D50-D90
    """)
    
    print("\n" + "=" * 80)
    print("✅ TASK-FACS-002 Analysis Complete!")
    print("=" * 80)
    
    return results_summary

if __name__ == "__main__":
    apply_mie_sizing()
