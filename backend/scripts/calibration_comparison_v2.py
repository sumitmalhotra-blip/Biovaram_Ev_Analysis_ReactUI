#!/usr/bin/env python3
"""
Nano Vis Calibration Analysis - REVISED
Compares LOW (40-150nm) and HIGH (140-1000nm) calibration bead samples

KEY FINDINGS:
- HIGH sample has ~19% detector saturation due to larger particles
- LOW sample has virtually no saturation
- Different calibration approach needed for each population

APPROACH: Use percentile-based calibration matching expected size ranges
"""

import flowio
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import json
from scipy.signal import find_peaks

# Setup paths
base_path = Path(__file__).parent.parent
output_dir = base_path / "figures" / "nano_vis_calibration"
output_dir.mkdir(parents=True, exist_ok=True)

# Load both files
files = {
    'Nano Vis Low': (base_path / 'nanoFACS' / 'Nano Vis Low.fcs', (40, 150), 'blue'),
    'Nano Vis High': (base_path / 'nanoFACS' / 'Nano Vis High.fcs', (140, 1000), 'orange')
}

print("=" * 70)
print("LOADING AND PROCESSING FILES")
print("=" * 70)

all_data = {}
for name, (fpath, expected, color) in files.items():
    print(f"\nLoading {name}...")
    fcs = flowio.FlowData(str(fpath))
    channels = [fcs.channels[str(i+1)]['PnN'] for i in range(fcs.channel_count)]
    events = np.array(fcs.events).reshape(-1, len(channels))
    data = pd.DataFrame(events, columns=channels)
    
    # Filter valid events
    valid = (data['FSC-H'] > 0) & (data['SSC-H'] > 0)
    
    # Detect saturation
    ssc_all = np.asarray(data.loc[valid, 'SSC-H'].values)
    sat_threshold = float(np.max(ssc_all) * 0.95)
    n_saturated = np.sum(ssc_all > sat_threshold)
    pct_saturated = 100 * n_saturated / len(ssc_all)
    
    print(f"  Total events: {len(data):,}, Valid: {valid.sum():,}")
    print(f"  Saturated events: {n_saturated:,} ({pct_saturated:.1f}%)")
    
    all_data[name] = {
        'fsc': data.loc[valid, 'FSC-H'].values,
        'ssc': data.loc[valid, 'SSC-H'].values,
        'expected': expected,
        'color': color,
        'pct_saturated': pct_saturated,
        'sat_threshold': sat_threshold
    }

# ============================================================================
# CALIBRATION APPROACH: Use the 10th percentile of each distribution
# This avoids saturation issues and noise floor issues
# ============================================================================

print("\n" + "=" * 70)
print("PERCENTILE-BASED CALIBRATION")
print("=" * 70)

# For each sample, map SSC to size based on expected range
# LOW: 40-150nm, so 10th percentile SSC -> 40nm, 90th percentile SSC -> 150nm
# HIGH: 140-1000nm, so 10th percentile SSC -> 140nm, 90th percentile SSC -> 1000nm

calibration_data = {}
for name, d in all_data.items():
    ssc = d['ssc']
    expected = d['expected']
    
    # Exclude saturated events for HIGH sample
    if d['pct_saturated'] > 5:
        non_sat = ssc[ssc < d['sat_threshold']]
        print(f"\n{name}: Using non-saturated events ({len(non_sat):,} of {len(ssc):,})")
    else:
        non_sat = ssc
        print(f"\n{name}: Using all events ({len(non_sat):,})")
    
    # Get percentiles
    p5, p10, p25, p50, p75, p90, p95 = np.percentile(non_sat, [5, 10, 25, 50, 75, 90, 95])
    
    print(f"  Expected size range: {expected[0]}-{expected[1]}nm")
    print(f"  SSC P10={p10:.0f}, P50={p50:.0f}, P90={p90:.0f}")
    
    # Linear interpolation in log space:
    # log(size) = a * log(SSC) + b
    # At P10: log(expected[0]) = a * log(P10) + b
    # At P90: log(expected[1]) = a * log(P90) + b
    
    log_ssc_10 = np.log10(p10)
    log_ssc_90 = np.log10(p90)
    log_size_10 = np.log10(expected[0])
    log_size_90 = np.log10(expected[1])
    
    # Solve for a (slope) and b (intercept)
    a = (log_size_90 - log_size_10) / (log_ssc_90 - log_ssc_10)
    b = log_size_10 - a * log_ssc_10
    
    print(f"  Calibration: log10(size) = {a:.4f} * log10(SSC) + {b:.4f}")
    
    calibration_data[name] = {
        'a': a,
        'b': b,
        'p10_ssc': p10,
        'p90_ssc': p90,
        'expected': expected,
        'ssc_data': non_sat
    }

# ============================================================================
# APPLY CALIBRATION AND CREATE EVENT VS SIZE SCATTER PLOTS
# ============================================================================

print("\n" + "=" * 70)
print("CREATING EVENT VS SIZE SCATTER PLOTS")
print("=" * 70)

fig, axes = plt.subplots(2, 2, figsize=(14, 12))

for idx, (name, d) in enumerate(all_data.items()):
    row = idx
    cal = calibration_data[name]
    
    # Apply calibration to ALL events (including saturated for visualization)
    log_ssc = np.log10(d['ssc'] + 1)
    log_size = cal['a'] * log_ssc + cal['b']
    size_nm = 10 ** log_size
    
    # Clip unreasonable sizes
    size_nm = np.clip(size_nm, 10, 5000)
    
    event_numbers = np.arange(len(size_nm))
    
    # Left column: Scatter plot
    ax = axes[row, 0]
    
    # Subsample for plotting
    n_plot = min(30000, len(size_nm))
    sample_idx = np.random.choice(len(size_nm), n_plot, replace=False)
    sample_idx_sorted = np.sort(sample_idx)
    
    # Color by saturation status
    ssc_vals = d['ssc'][sample_idx_sorted]
    colors = np.where(ssc_vals > d['sat_threshold'], 'red', d['color'])
    
    ax.scatter(event_numbers[sample_idx_sorted], size_nm[sample_idx_sorted], 
               alpha=0.3, s=1, c=colors)
    
    # Add expected range
    ax.axhline(d['expected'][0], color='green', linestyle='--', linewidth=2, label=f"Expected min ({d['expected'][0]}nm)")
    ax.axhline(d['expected'][1], color='green', linestyle='--', linewidth=2, label=f"Expected max ({d['expected'][1]}nm)")
    ax.fill_between([0, len(size_nm)], d['expected'][0], d['expected'][1], 
                    alpha=0.1, color='green')
    
    ax.set_xlabel('Event Number')
    ax.set_ylabel('Calibrated Size (nm)')
    ax.set_title(f"{name}\nEvent vs Size (red = saturated detector)")
    ax.legend(loc='upper right')
    ax.set_ylim(0, max(d['expected'][1] * 1.5, 500))
    
    # Right column: Size distribution histogram
    ax = axes[row, 1]
    
    # Use non-saturated events only
    non_sat_mask = d['ssc'] < d['sat_threshold']
    size_non_sat = size_nm[non_sat_mask]
    
    ax.hist(size_non_sat, bins=100, alpha=0.7, color=d['color'])
    ax.axvline(d['expected'][0], color='green', linestyle='--', linewidth=2, label=f"Expected min ({d['expected'][0]}nm)")
    ax.axvline(d['expected'][1], color='green', linestyle='--', linewidth=2, label=f"Expected max ({d['expected'][1]}nm)")
    
    # Calculate stats
    in_range = np.sum((size_non_sat >= d['expected'][0]) & (size_non_sat <= d['expected'][1]))
    pct_in_range = 100 * in_range / len(size_non_sat)
    
    ax.set_xlabel('Calibrated Size (nm)')
    ax.set_ylabel('Count')
    ax.set_title(f"{name}\nSize Distribution ({pct_in_range:.1f}% in expected range)")
    ax.legend(loc='upper right')
    ax.set_xlim(0, max(d['expected'][1] * 1.5, 500))

plt.tight_layout()
event_size_plot = output_dir / 'event_vs_size_revised.png'
plt.savefig(event_size_plot, dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: {event_size_plot}")

# ============================================================================
# COMBINED CALIBRATION USING BOTH SAMPLES
# ============================================================================

print("\n" + "=" * 70)
print("COMBINED CALIBRATION CURVE")
print("=" * 70)

# Use 4-point calibration:
# Point 1: LOW P10 -> 40nm
# Point 2: LOW P90 -> 150nm
# Point 3: HIGH P10 -> 140nm
# Point 4: HIGH P90 -> 1000nm

calibration_points = []
for name in ['Nano Vis Low', 'Nano Vis High']:
    cal = calibration_data[name]
    calibration_points.append((cal['p10_ssc'], cal['expected'][0]))
    calibration_points.append((cal['p90_ssc'], cal['expected'][1]))

print("\nCalibration points (SSC, Size_nm):")
for ssc, size in calibration_points:
    print(f"  SSC={ssc:.0f} -> Size={size}nm")

# Fit power law to all 4 points
log_ssc_points = np.log10([p[0] for p in calibration_points])
log_size_points = np.log10([p[1] for p in calibration_points])

# Linear regression
coeffs = np.polyfit(log_ssc_points, log_size_points, 1)
a_combined = coeffs[0]
b_combined = coeffs[1]

print(f"\nCombined fit: log10(size) = {a_combined:.4f} * log10(SSC) + {b_combined:.4f}")
print(f"Or: size = 10^{b_combined:.4f} * SSC^{a_combined:.4f}")

# Calculate residuals
predicted = a_combined * log_ssc_points + b_combined
residuals = log_size_points - predicted
rmse = np.sqrt(np.mean(residuals**2))
print(f"RMSE (log10 space): {rmse:.4f}")

# ============================================================================
# FINAL VISUALIZATION
# ============================================================================

fig, axes = plt.subplots(1, 3, figsize=(16, 5))

# Plot 1: Calibration curve with data points
ax = axes[0]
ssc_range = np.logspace(2, 7, 100)
size_predicted = 10 ** (a_combined * np.log10(ssc_range) + b_combined)

ax.plot(ssc_range, size_predicted, 'k-', linewidth=2, label=f'Fit: size ∝ SSC^{a_combined:.2f}')

colors = ['blue', 'blue', 'orange', 'orange']
labels = ['LOW P10 (40nm)', 'LOW P90 (150nm)', 'HIGH P10 (140nm)', 'HIGH P90 (1000nm)']
for i, (ssc, size) in enumerate(calibration_points):
    ax.scatter(ssc, size, s=100, c=colors[i], edgecolors='black', linewidths=2, zorder=5, label=labels[i])

ax.set_xscale('log')
ax.set_yscale('log')
ax.set_xlabel('SSC-H')
ax.set_ylabel('Diameter (nm)')
ax.set_title('Combined Calibration Curve\n(4-point fit)')
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

# Plot 2: LOW sample event vs size
ax = axes[1]
d = all_data['Nano Vis Low']
log_ssc = np.log10(d['ssc'] + 1)
size_nm = 10 ** (a_combined * log_ssc + b_combined)
size_nm = np.clip(size_nm, 10, 5000)
event_numbers = np.arange(len(size_nm))

sample_idx = np.random.choice(len(size_nm), min(20000, len(size_nm)), replace=False)
sample_idx = np.sort(sample_idx)

ax.scatter(event_numbers[sample_idx], size_nm[sample_idx], alpha=0.3, s=1, c='blue')
ax.axhline(40, color='green', linestyle='--', linewidth=2)
ax.axhline(150, color='green', linestyle='--', linewidth=2)
ax.fill_between([0, len(size_nm)], 40, 150, alpha=0.1, color='green')
ax.set_xlabel('Event Number')
ax.set_ylabel('Size (nm)')
ax.set_title(f'Nano Vis Low (40-150nm)\nEvent vs Size')
ax.set_ylim(0, 400)

# Plot 3: HIGH sample event vs size
ax = axes[2]
d = all_data['Nano Vis High']
log_ssc = np.log10(d['ssc'] + 1)
size_nm = 10 ** (a_combined * log_ssc + b_combined)
size_nm = np.clip(size_nm, 10, 5000)
event_numbers = np.arange(len(size_nm))

sample_idx = np.random.choice(len(size_nm), min(20000, len(size_nm)), replace=False)
sample_idx = np.sort(sample_idx)

# Color saturated events
ssc_vals = d['ssc'][sample_idx]
colors = np.where(ssc_vals > d['sat_threshold'], 'red', 'orange')

ax.scatter(event_numbers[sample_idx], size_nm[sample_idx], alpha=0.3, s=1, c=colors)
ax.axhline(140, color='green', linestyle='--', linewidth=2)
ax.axhline(1000, color='green', linestyle='--', linewidth=2)
ax.fill_between([0, len(size_nm)], 140, 1000, alpha=0.1, color='green')
ax.set_xlabel('Event Number')
ax.set_ylabel('Size (nm)')
ax.set_title(f'Nano Vis High (140-1000nm)\nEvent vs Size (red = saturated)')
ax.set_ylim(0, 1500)

plt.tight_layout()
final_plot = output_dir / 'calibration_final.png'
plt.savefig(final_plot, dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: {final_plot}")

# ============================================================================
# SAVE CALIBRATION PARAMETERS
# ============================================================================

calibration_params = {
    'combined_calibration': {
        'formula': f"size_nm = 10^{b_combined:.4f} * SSC^{a_combined:.4f}",
        'log_slope_a': a_combined,
        'log_intercept_b': b_combined,
        'rmse_log': rmse
    },
    'individual_calibrations': {},
    'calibration_points': [{'ssc': float(s), 'size_nm': float(z)} for s, z in calibration_points]
}

for name, cal in calibration_data.items():
    calibration_params['individual_calibrations'][name] = {
        'log_slope_a': cal['a'],
        'log_intercept_b': cal['b'],
        'p10_ssc': float(cal['p10_ssc']),
        'p90_ssc': float(cal['p90_ssc']),
        'expected_range_nm': cal['expected']
    }

params_path = output_dir / 'calibration_params_revised.json'
with open(params_path, 'w') as f:
    json.dump(calibration_params, f, indent=2)
print(f"Saved: {params_path}")

# ============================================================================
# SUMMARY STATISTICS
# ============================================================================

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"\nCombined calibration formula:")
print(f"  size_nm = 10^{b_combined:.4f} × SSC^{a_combined:.4f}")
print(f"  Or: size_nm = {10**b_combined:.4f} × SSC^{a_combined:.4f}")

print(f"\nFor quick reference:")
print(f"  SSC = 1,000 -> Size = {10**(a_combined*3 + b_combined):.0f} nm")
print(f"  SSC = 10,000 -> Size = {10**(a_combined*4 + b_combined):.0f} nm")
print(f"  SSC = 100,000 -> Size = {10**(a_combined*5 + b_combined):.0f} nm")
print(f"  SSC = 1,000,000 -> Size = {10**(a_combined*6 + b_combined):.0f} nm")

print("\n" + "=" * 70)
print("OUTPUT FILES")
print("=" * 70)
print(f"\n{output_dir}/")
print("  ├── event_vs_size_revised.png     (Individual sample calibrations)")
print("  ├── calibration_final.png          (Combined calibration & event plots)")
print("  └── calibration_params_revised.json (Parameters for code)")
