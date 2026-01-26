#!/usr/bin/env python3
"""
Apply Calibration to All FCS Samples
=====================================

This script applies the Nano Vis calibration to all FCS files
and generates comprehensive reports.

Run: python scripts/apply_calibration_all.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.fcs_calibration import (
    CalibrationParams, DilutionFactors,
    analyze_fcs_file, batch_analyze_fcs, generate_batch_report,
    compare_nta_fcs, load_fcs_file, find_scatter_channels
)
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import json

# Setup paths
base_path = Path(__file__).parent.parent
nanofacs_dir = base_path / "nanoFACS"
output_dir = base_path / "figures" / "calibrated_analysis"
output_dir.mkdir(parents=True, exist_ok=True)

# Initialize calibration
calibration = CalibrationParams()
dilution = DilutionFactors()

print("=" * 70)
print("FCS CALIBRATION APPLICATION")
print("=" * 70)
print(f"\nCalibration formula: size = {calibration.coefficient_k:.2f} × SSC^{calibration.log_slope_a:.4f}")
print(f"Dilution factor: {dilution.total_dilution:.1f}x (NTA to FCS)")

# Define experiment directories
experiments = {
    'PC3 (Dec 17, 2025)': nanofacs_dir / 'Exp_20251217_PC3',
    'Exo CD81 (10000)': nanofacs_dir / '10000 exo and cd81',
    'CD9 Exosome Lots': nanofacs_dir / 'CD9 and exosome lots',
    'HEK TFF': nanofacs_dir / 'EV_HEK_TFF_DATA_05Dec25',
    'EXP 6-10-2025': nanofacs_dir / 'EXP 6-10-2025',
}

# Analyze each experiment
all_results = {}
summary_data = []

for exp_name, exp_dir in experiments.items():
    print(f"\n{'='*70}")
    print(f"Analyzing: {exp_name}")
    print(f"{'='*70}")
    
    if not exp_dir.exists():
        print(f"  Directory not found: {exp_dir}")
        continue
    
    # Get all FCS files
    fcs_files = list(exp_dir.glob("*.fcs"))
    print(f"  Found {len(fcs_files)} FCS files")
    
    # Analyze each file
    exp_results = []
    for fcs_path in sorted(fcs_files):
        try:
            result = analyze_fcs_file(fcs_path, calibration)
            exp_results.append(result)
            
            # Add to summary
            summary_data.append({
                'experiment': exp_name,
                'filename': result.filename,
                'events': result.valid_events,
                'saturated_pct': result.saturation_percent,
                'size_mean': result.size_mean,
                'size_median': result.size_median,
                'size_p10': result.size_p10,
                'size_p90': result.size_p90,
                'ssc_median': result.ssc_median
            })
            
            # Print key samples
            if 'exo' in result.filename.lower() or 'pc3' in result.filename.lower():
                print(f"\n  {result.filename}:")
                print(f"    Events: {result.valid_events:,} ({result.saturation_percent:.1f}% saturated)")
                print(f"    Size: Mean={result.size_mean:.1f}nm, Median={result.size_median:.1f}nm")
                print(f"    Range (P10-P90): {result.size_p10:.0f}-{result.size_p90:.0f}nm")
        
        except Exception as e:
            print(f"  Failed to analyze {fcs_path.name}: {e}")
    
    all_results[exp_name] = exp_results
    
    # Generate experiment report
    if exp_results:
        exp_output = output_dir / exp_name.replace(' ', '_').replace(',', '').replace('(', '').replace(')', '')
        exp_output.mkdir(parents=True, exist_ok=True)
        generate_batch_report(exp_results, exp_output, "analysis")

# Create summary DataFrame
df_summary = pd.DataFrame(summary_data)
df_summary.to_csv(output_dir / "all_samples_summary.csv", index=False)
print(f"\n\nSaved summary to: {output_dir / 'all_samples_summary.csv'}")

# ============================================================================
# SPECIAL ANALYSIS: PC3 Samples with Markers
# ============================================================================

print("\n" + "=" * 70)
print("PC3 SAMPLE ANALYSIS (with marker comparison)")
print("=" * 70)

pc3_dir = nanofacs_dir / 'Exp_20251217_PC3'
if pc3_dir.exists():
    # Group files by sample type
    pc3_samples = {
        'PC3 EXO Control': ['PC3 EXO1.fcs'],
        'CD81 labeled': ['Exo+CD 81.fcs', 'Exo+CD 81 +ISOTYPE1.fcs', 'CD 81 alone.fcs'],
        'CD9 labeled': ['Exo+CD 9.fcs', 'Exo+CD 9 +ISOTYPE.fcs', 'CD 9 alone1.fcs'],
        'Cont 2 treatment': ['Exo+cont 2 1ug.fcs', 'Exo+cont 2 50 uM1.fcs', 'cont 2 1ug alone.fcs'],
        'Cont 4 treatment': ['Exo+cont 4 1ug.fcs', 'Exo+cont 4 50 uM.fcs', 'cont 4 1ug Alone.fcs'],
    }
    
    pc3_comparison = []
    
    for group_name, filenames in pc3_samples.items():
        print(f"\n{group_name}:")
        for fname in filenames:
            fpath = pc3_dir / fname
            if fpath.exists():
                try:
                    result = analyze_fcs_file(fpath, calibration)
                    print(f"  {fname}: {result.valid_events:,} events, Mean={result.size_mean:.1f}nm, Median={result.size_median:.1f}nm")
                    pc3_comparison.append({
                        'group': group_name,
                        'filename': fname,
                        'events': result.valid_events,
                        'mean_size': result.size_mean,
                        'median_size': result.size_median,
                        'p10': result.size_p10,
                        'p90': result.size_p90,
                        'saturated': result.saturation_percent
                    })
                except Exception as e:
                    print(f"  {fname}: Error - {e}")
    
    # Create PC3 comparison plot
    if pc3_comparison:
        df_pc3 = pd.DataFrame(pc3_comparison)
        df_pc3.to_csv(output_dir / "pc3_comparison.csv", index=False)
        
        # Plot
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Size comparison
        ax = axes[0]
        groups = df_pc3['group'].unique()
        cmap = plt.colormaps.get_cmap('tab10')
        colors = cmap(np.linspace(0, 1, len(groups)))
        
        for i, group in enumerate(groups):
            group_data = df_pc3[df_pc3['group'] == group]
            x_pos = [i + 0.3 * j for j in range(len(group_data))]
            ax.bar(x_pos, group_data['mean_size'], width=0.25, 
                   color=colors[i], label=group, alpha=0.7)
            # Add error bars (P10 to P90)
            for j, (_, row) in enumerate(group_data.iterrows()):
                ax.errorbar(x_pos[j], row['mean_size'], 
                           yerr=[[row['mean_size']-row['p10']], [row['p90']-row['mean_size']]],
                           color='black', capsize=3)
        
        ax.set_ylabel('Mean Size (nm)')
        ax.set_title('PC3 Sample Size Comparison')
        ax.set_xticks([i + 0.15 for i in range(len(groups))])
        ax.set_xticklabels(groups, rotation=45, ha='right')
        
        # Event count comparison
        ax = axes[1]
        for i, group in enumerate(groups):
            group_data = df_pc3[df_pc3['group'] == group]
            x_pos = [i + 0.3 * j for j in range(len(group_data))]
            ax.bar(x_pos, group_data['events'], width=0.25, 
                   color=colors[i], label=group, alpha=0.7)
        
        ax.set_ylabel('Event Count')
        ax.set_title('PC3 Sample Event Counts')
        ax.set_xticks([i + 0.15 for i in range(len(groups))])
        ax.set_xticklabels(groups, rotation=45, ha='right')
        ax.set_yscale('log')
        
        plt.tight_layout()
        plt.savefig(output_dir / "pc3_comparison.png", dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\nSaved PC3 comparison plot to: {output_dir / 'pc3_comparison.png'}")

# ============================================================================
# CREATE VISUALIZATION: Size Distribution Overlay
# ============================================================================

print("\n" + "=" * 70)
print("CREATING SIZE DISTRIBUTION OVERLAYS")
print("=" * 70)

# Get a few key samples for overlay visualization
key_samples = [
    ('Nano Vis Low', nanofacs_dir / 'Nano Vis Low.fcs', (40, 150)),
    ('Nano Vis High', nanofacs_dir / 'Nano Vis High.fcs', (140, 1000)),
    ('PC3 EXO', pc3_dir / 'PC3 EXO1.fcs', None),
    ('Exo+CD81', pc3_dir / 'Exo+CD 81.fcs', None),
    ('Exo+CD9', pc3_dir / 'Exo+CD 9.fcs', None),
]

fig, axes = plt.subplots(2, 3, figsize=(15, 10))
axes = axes.flatten()

for i, (name, fpath, expected_range) in enumerate(key_samples):
    if i >= len(axes):
        break
    
    ax = axes[i]
    
    if fpath.exists():
        try:
            data, meta = load_fcs_file(fpath)
            channels = find_scatter_channels(meta['channels'])
            
            if 'ssc' in channels:
                ssc = np.asarray(data[channels['ssc']].values)
                ssc_valid = ssc[ssc > 0]
                
                # Apply calibration
                sizes = calibration.ssc_to_size(ssc_valid)
                sizes = sizes[sizes < 2000]  # Filter extreme values
                
                # Plot histogram
                ax.hist(sizes, bins=50, alpha=0.7, color='steelblue', edgecolor='black')
                
                # Add expected range if provided
                if expected_range:
                    ax.axvline(expected_range[0], color='green', linestyle='--', linewidth=2)
                    ax.axvline(expected_range[1], color='green', linestyle='--', linewidth=2)
                    ax.axvspan(expected_range[0], expected_range[1], alpha=0.1, color='green')
                
                # Add statistics
                mean_size = np.mean(sizes)
                median_size = np.median(sizes)
                ax.axvline(mean_size, color='red', linestyle='-', linewidth=2, label=f'Mean: {mean_size:.0f}nm')
                ax.axvline(median_size, color='orange', linestyle='-', linewidth=2, label=f'Median: {median_size:.0f}nm')
                
                ax.set_xlabel('Size (nm)')
                ax.set_ylabel('Count')
                ax.set_title(name)
                ax.legend(loc='upper right', fontsize=8)
                ax.set_xlim(0, 800)
        except Exception as e:
            ax.text(0.5, 0.5, f"Error: {e}", transform=ax.transAxes, ha='center')
            ax.set_title(name)
    else:
        ax.text(0.5, 0.5, "File not found", transform=ax.transAxes, ha='center')
        ax.set_title(name)

# Hide unused subplot
last_sample_idx = len(key_samples) - 1
for j in range(last_sample_idx + 1, len(axes)):
    axes[j].set_visible(False)

plt.suptitle('Calibrated Size Distributions', fontsize=14)
plt.tight_layout()
plt.savefig(output_dir / "size_distribution_overlay.png", dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved overlay plot to: {output_dir / 'size_distribution_overlay.png'}")

# ============================================================================
# NTA/FCS COMPARISON EXAMPLE
# ============================================================================

print("\n" + "=" * 70)
print("NTA/FCS DILUTION COMPARISON EXAMPLE")
print("=" * 70)

# Example: If NTA showed 5×10^8 particles/mL
nta_example_count = 5e8
fcs_expected = dilution.nta_to_fcs_count(nta_example_count)

print(f"\nExample NTA count: {nta_example_count:.2e} particles/mL")
print(f"Dilution factor: {dilution.total_dilution:.1f}x")
print(f"Expected FCS events: {fcs_expected:.2e}")

# Check actual PC3 sample
if (pc3_dir / 'PC3 EXO1.fcs').exists():
    result = analyze_fcs_file(pc3_dir / 'PC3 EXO1.fcs', calibration)
    print(f"\nActual PC3 EXO1 events: {result.valid_events:,}")
    
    # Back-calculate what NTA count would be
    implied_nta = dilution.fcs_to_nta_count(result.valid_events)
    print(f"Implied NTA count: {implied_nta:.2e} particles/mL")

# ============================================================================
# SAVE CALIBRATION CONFIG
# ============================================================================

calibration_config = {
    'calibration': {
        'log_slope_a': calibration.log_slope_a,
        'log_intercept_b': calibration.log_intercept_b,
        'coefficient_k': calibration.coefficient_k,
        'formula': f"size_nm = {calibration.coefficient_k:.4f} × SSC^{calibration.log_slope_a:.4f}"
    },
    'dilution': {
        'nta_sample_volume_ul': dilution.nta_sample_volume_ul,
        'nanofacs_sample_volume_ul': dilution.nanofacs_sample_volume_ul,
        'nanofacs_final_volume_ul': dilution.nanofacs_final_volume_ul,
        'total_dilution_factor': dilution.total_dilution
    },
    'reference': {
        'low_beads': '40-150nm polystyrene (Nano Vis Low)',
        'high_beads': '140-1000nm polystyrene (Nano Vis High)',
        'source': 'Jan 2026 calibration from Biovaram data'
    }
}

with open(output_dir / 'calibration_config.json', 'w') as f:
    json.dump(calibration_config, f, indent=2)

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)
print(f"\nOutput files saved to: {output_dir}")
print("\nKey files:")
print("  - all_samples_summary.csv (all FCS files analyzed)")
print("  - pc3_comparison.csv/png (PC3 sample comparison)")
print("  - size_distribution_overlay.png (key sample distributions)")
print("  - calibration_config.json (calibration parameters)")
