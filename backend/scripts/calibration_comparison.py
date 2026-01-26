#!/usr/bin/env python3
"""
Nano Vis Calibration Comparison Analysis
Compares LOW (40-150nm) and HIGH (140-1000nm) calibration bead samples

KEY FINDING: HIGH sample has ~19% detector saturation due to larger particles
scattering more light. Calibration must account for this.
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
    
    # Filter valid events (all positive)
    valid = (data['FSC-H'] > 0) & (data['SSC-H'] > 0)
    print(f"  Total events: {len(data):,}, Valid: {valid.sum():,}")
    
    all_data[name] = {
        'fsc': data.loc[valid, 'FSC-H'].values,
        'ssc': data.loc[valid, 'SSC-H'].values,
        'expected': expected,
        'color': color
    }

# Create comparison figure
fig, axes = plt.subplots(2, 3, figsize=(15, 10))

# Row 0, Col 0: Overlaid SSC histograms
ax = axes[0, 0]
for name, d in all_data.items():
    label = f"{name} ({d['expected'][0]}-{d['expected'][1]}nm)"
    ax.hist(np.log10(d['ssc'] + 1), bins=100, alpha=0.5, label=label, color=d['color'])
ax.set_xlabel('log10(SSC-H)')
ax.set_ylabel('Count')
ax.set_title('SSC-H Distribution Comparison')
ax.legend()

# Row 0, Col 1: Overlaid FSC histograms
ax = axes[0, 1]
for name, d in all_data.items():
    label = f"{name} ({d['expected'][0]}-{d['expected'][1]}nm)"
    ax.hist(np.log10(d['fsc'] + 1), bins=100, alpha=0.5, label=label, color=d['color'])
ax.set_xlabel('log10(FSC-H)')
ax.set_ylabel('Count')
ax.set_title('FSC-H Distribution Comparison')
ax.legend()

# Row 0, Col 2: Cumulative distribution of SSC
ax = axes[0, 2]
for name, d in all_data.items():
    sorted_ssc = np.sort(d['ssc'])
    cumulative = np.arange(1, len(sorted_ssc)+1) / len(sorted_ssc)
    # Subsample for plotting
    idx = np.linspace(0, len(sorted_ssc)-1, 1000).astype(int)
    ax.plot(np.log10(sorted_ssc[idx]+1), cumulative[idx], label=name, color=d['color'], linewidth=2)
ax.set_xlabel('log10(SSC-H)')
ax.set_ylabel('Cumulative Fraction')
ax.set_title('SSC-H Cumulative Distribution')
ax.legend()
ax.grid(True, alpha=0.3)

# Row 1, Col 0: Low sample scatter
ax = axes[1, 0]
d = all_data['Nano Vis Low']
idx = np.random.choice(len(d['fsc']), min(10000, len(d['fsc'])), replace=False)
ax.scatter(np.log10(d['fsc'][idx]+1), np.log10(d['ssc'][idx]+1), alpha=0.3, s=1, c='blue')
ax.set_xlabel('log10(FSC-H)')
ax.set_ylabel('log10(SSC-H)')
ax.set_title(f"Nano Vis Low ({d['expected'][0]}-{d['expected'][1]}nm)")

# Row 1, Col 1: High sample scatter
ax = axes[1, 1]
d = all_data['Nano Vis High']
idx = np.random.choice(len(d['fsc']), min(10000, len(d['fsc'])), replace=False)
ax.scatter(np.log10(d['fsc'][idx]+1), np.log10(d['ssc'][idx]+1), alpha=0.3, s=1, c='orange')
ax.set_xlabel('log10(FSC-H)')
ax.set_ylabel('log10(SSC-H)')
ax.set_title(f"Nano Vis High ({d['expected'][0]}-{d['expected'][1]}nm)")

# Row 1, Col 2: Both samples overlaid
ax = axes[1, 2]
for name, d in all_data.items():
    idx = np.random.choice(len(d['fsc']), min(5000, len(d['fsc'])), replace=False)
    ax.scatter(np.log10(d['fsc'][idx]+1), np.log10(d['ssc'][idx]+1), alpha=0.3, s=1, c=d['color'], label=name)
ax.set_xlabel('log10(FSC-H)')
ax.set_ylabel('log10(SSC-H)')
ax.set_title('Both Samples Overlaid')
ax.legend()

plt.tight_layout()
plot_path = output_dir / 'calibration_comparison.png'
plt.savefig(plot_path, dpi=150, bbox_inches='tight')
plt.close()
print(f"\nSaved: {plot_path}")

# Calculate calibration statistics
print("\n" + "=" * 70)
print("CALIBRATION STATISTICS")
print("=" * 70)

# The data shows bimodal distribution - we need to find the PRIMARY peak
# which corresponds to actual particles, not detector saturation or noise
# Approach: Find peaks in histogram and select the one that makes physical sense

from scipy.signal import find_peaks

stats_data = {}
for name, d in all_data.items():
    ssc = d['ssc']
    fsc = d['fsc']
    p10, p25, p50, p75, p90 = np.percentile(ssc, [10, 25, 50, 75, 90])
    
    # Find mode using histogram - look for primary peak, not saturation
    log_ssc = np.log10(ssc + 1)
    hist, bin_edges = np.histogram(log_ssc, bins=100)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    # Find all peaks
    peaks, properties = find_peaks(hist, height=len(ssc)*0.01, prominence=len(ssc)*0.005)
    
    if len(peaks) > 0:
        # Sort peaks by height and take the highest one in the lower half of the range
        # (to avoid saturation peak at high values)
        peak_heights = hist[peaks]
        
        # Filter peaks to those below log10(SSC) = 5 (below saturation)
        valid_peaks = peaks[bin_centers[peaks] < 5]
        if len(valid_peaks) > 0:
            # Take the highest peak among valid peaks
            best_peak_idx = valid_peaks[np.argmax(hist[valid_peaks])]
        else:
            # Fall back to overall maximum in reasonable range
            mask = bin_centers < 5
            if np.any(mask):
                best_peak_idx = np.argmax(hist * mask)
            else:
                best_peak_idx = np.argmax(hist)
        
        mode_log_ssc = bin_centers[best_peak_idx]
        mode_ssc = 10**mode_log_ssc
    else:
        # Fallback: use median
        mode_log_ssc = np.log10(p50 + 1)
        mode_ssc = p50
    
    # Also calculate geometric mean of non-saturated events
    # Filter out saturated events (typically > 5e6)
    non_saturated = ssc[ssc < 5e6]
    if len(non_saturated) > 0:
        geo_mean = np.exp(np.mean(np.log(non_saturated)))
    else:
        geo_mean = np.median(ssc)
    
    print(f"\n{name} ({d['expected'][0]}-{d['expected'][1]}nm):")
    print(f"  SSC percentiles: 10%={p10:.0f}, 25%={p25:.0f}, 50%={p50:.0f}, 75%={p75:.0f}, 90%={p90:.0f}")
    print(f"  SSC primary mode: {mode_ssc:.0f} (log10 = {mode_log_ssc:.2f})")
    print(f"  SSC geometric mean (non-sat): {geo_mean:.0f}")
    print(f"  log10(SSC) range (25-75%): {np.log10(p25):.2f} - {np.log10(p75):.2f}")
    print(f"  All peaks found at log10(SSC): {[f'{bin_centers[p]:.2f}' for p in peaks]}")
    
    stats_data[name] = {
        'expected_nm': d['expected'],
        'ssc_percentiles': {'p10': p10, 'p25': p25, 'p50': p50, 'p75': p75, 'p90': p90},
        'ssc_mode': mode_ssc,
        'ssc_geo_mean': geo_mean,
        'log_ssc_mode': mode_log_ssc,
        'n_events': len(ssc)
    }

# Calculate calibration curve (two-point linear in log space)
print("\n" + "=" * 70)
print("TWO-POINT CALIBRATION CURVE")
print("=" * 70)

low_d = all_data['Nano Vis Low']
high_d = all_data['Nano Vis High']

# Use PRIMARY mode values for calibration points (not saturation peaks)
low_mode = stats_data['Nano Vis Low']['ssc_mode']
high_mode = stats_data['Nano Vis High']['ssc_mode']
low_geo = stats_data['Nano Vis Low']['ssc_geo_mean']
high_geo = stats_data['Nano Vis High']['ssc_geo_mean']

# Midpoint of expected size ranges using geometric mean (better for log-space)
low_size_geo = np.sqrt(40 * 150)  # ~77.5nm
high_size_geo = np.sqrt(140 * 1000)  # ~374nm

print(f"\nUsing PRIMARY SSC mode values (not saturation):")
print(f"  LOW:  SSC mode = {low_mode:.0f} -> Size = {low_size_geo:.0f}nm (geometric mean of 40-150)")
print(f"  HIGH: SSC mode = {high_mode:.0f} -> Size = {high_size_geo:.0f}nm (geometric mean of 140-1000)")

# Fit power law: SSC = k * diameter^n
# log(SSC) = log(k) + n * log(diameter)
log_ssc = np.array([np.log10(low_mode), np.log10(high_mode)])
log_size = np.array([np.log10(low_size_geo), np.log10(high_size_geo)])

# Linear fit
if log_size[1] != log_size[0]:  # Avoid division by zero
    n = (log_ssc[1] - log_ssc[0]) / (log_size[1] - log_size[0])
else:
    n = 2.0  # Default to Mie regime value
log_k = log_ssc[0] - n * log_size[0]
k = 10 ** log_k

print(f"\nPower law fit: SSC = k * diameter^n")
print(f"  n (exponent) = {n:.2f}")
print(f"  k (coefficient) = {k:.4f}")
print(f"\n  Size formula: diameter = (SSC / {k:.4f}) ^ (1/{n:.2f})")

# Alternative: Use geometric mean instead of mode
print(f"\nAlternative using geometric mean:")
log_ssc_geo = np.array([np.log10(low_geo), np.log10(high_geo)])
n_geo = (log_ssc_geo[1] - log_ssc_geo[0]) / (log_size[1] - log_size[0])
log_k_geo = log_ssc_geo[0] - n_geo * log_size[0]
k_geo = 10 ** log_k_geo
print(f"  n (exponent) = {n_geo:.2f}")
print(f"  k (coefficient) = {k_geo:.4f}")

# Check expected theoretical values
print("\nTheoretical reference:")
print("  Rayleigh scattering (d << lambda): n ~ 6")
print("  Mie regime (d ~ lambda): n ~ 2-4")
print("  Geometric regime (d >> lambda): n ~ 2")

# Create calibration curve figure
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# Plot 1: SSC vs Size calibration curve
ax = axes[0]
# Plot data points
ax.scatter([low_size_geo, high_size_geo], [low_mode, high_mode], 
           s=100, c=['blue', 'orange'], zorder=5, edgecolors='black', linewidths=2)
ax.annotate('LOW', (low_size_geo, low_mode), textcoords='offset points', xytext=(10, 10), fontsize=12)
ax.annotate('HIGH', (high_size_geo, high_mode), textcoords='offset points', xytext=(10, 10), fontsize=12)

# Plot fitted curve
size_range = np.linspace(30, 1200, 100)
ssc_fitted = k * (size_range ** n)
ax.plot(size_range, ssc_fitted, 'g--', linewidth=2, label=f'Fit: SSC = {k:.2e} × d^{n:.2f}')

ax.set_xscale('log')
ax.set_yscale('log')
ax.set_xlabel('Diameter (nm)')
ax.set_ylabel('SSC-H (mode)')
ax.set_title('Calibration Curve: SSC vs Size')
ax.legend()
ax.grid(True, alpha=0.3)

# Plot 2: Size calibration applied to LOW sample
ax = axes[1]
d = all_data['Nano Vis Low']
# Apply calibration
calibrated_size = (d['ssc'] / k) ** (1/n)
idx = np.random.choice(len(calibrated_size), min(10000, len(calibrated_size)), replace=False)
ax.hist(calibrated_size[idx], bins=100, alpha=0.7, color='blue')
ax.axvline(40, color='red', linestyle='--', linewidth=2, label='Expected min (40nm)')
ax.axvline(150, color='red', linestyle='--', linewidth=2, label='Expected max (150nm)')
ax.set_xlabel('Calibrated Diameter (nm)')
ax.set_ylabel('Count')
ax.set_title(f"Nano Vis Low - Calibrated Size\nExpected: 40-150nm")
ax.legend()
ax.set_xlim(0, 500)

# Plot 3: Size calibration applied to HIGH sample
ax = axes[2]
d = all_data['Nano Vis High']
# Apply calibration
calibrated_size = (d['ssc'] / k) ** (1/n)
idx = np.random.choice(len(calibrated_size), min(10000, len(calibrated_size)), replace=False)
ax.hist(calibrated_size[idx], bins=100, alpha=0.7, color='orange')
ax.axvline(140, color='red', linestyle='--', linewidth=2, label='Expected min (140nm)')
ax.axvline(1000, color='red', linestyle='--', linewidth=2, label='Expected max (1000nm)')
ax.set_xlabel('Calibrated Diameter (nm)')
ax.set_ylabel('Count')
ax.set_title(f"Nano Vis High - Calibrated Size\nExpected: 140-1000nm")
ax.legend()
ax.set_xlim(0, 1500)

plt.tight_layout()
calibration_plot = output_dir / 'calibration_curve_fit.png'
plt.savefig(calibration_plot, dpi=150, bbox_inches='tight')
plt.close()
print(f"\nSaved: {calibration_plot}")

# Create EVENT vs SIZE scatter plots (requested by user)
print("\n" + "=" * 70)
print("CREATING EVENT VS SIZE SCATTER PLOTS")
print("=" * 70)

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

for idx, (name, d) in enumerate(all_data.items()):
    ax = axes[idx]
    
    # Apply calibration to get sizes
    calibrated_size = (d['ssc'] / k) ** (1/n)
    event_numbers = np.arange(len(calibrated_size))
    
    # Subsample for plotting
    sample_idx = np.random.choice(len(calibrated_size), min(20000, len(calibrated_size)), replace=False)
    sample_idx_sorted = np.sort(sample_idx)  # Keep time order
    
    ax.scatter(event_numbers[sample_idx_sorted], calibrated_size[sample_idx_sorted], 
               alpha=0.3, s=1, c=d['color'])
    
    # Add expected range
    ax.axhline(d['expected'][0], color='red', linestyle='--', linewidth=2, alpha=0.7)
    ax.axhline(d['expected'][1], color='red', linestyle='--', linewidth=2, alpha=0.7)
    ax.fill_between([0, len(calibrated_size)], d['expected'][0], d['expected'][1], 
                    alpha=0.1, color='green', label='Expected range')
    
    ax.set_xlabel('Event Number')
    ax.set_ylabel('Calibrated Size (nm)')
    ax.set_title(f"{name}\nEvent vs Size ({d['expected'][0]}-{d['expected'][1]}nm expected)")
    ax.legend()
    ax.set_ylim(0, 1500)

plt.tight_layout()
event_size_plot = output_dir / 'event_vs_size_scatter.png'
plt.savefig(event_size_plot, dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: {event_size_plot}")

# Save calibration parameters
calibration_params = {
    'power_law_exponent_n': n,
    'coefficient_k': k,
    'formula': f"diameter_nm = (SSC_H / {k:.4f}) ^ (1/{n:.2f})",
    'calibration_points': {
        'low': {'ssc_mode': low_mode, 'size_nm': low_size_geo},
        'high': {'ssc_mode': high_mode, 'size_nm': high_size_geo}
    },
    'sample_statistics': stats_data
}

params_path = output_dir / 'calibration_parameters.json'
with open(params_path, 'w') as f:
    json.dump(calibration_params, f, indent=2, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else x)
print(f"Saved: {params_path}")

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)
print(f"\nOutput files in: {output_dir}")
print("  - calibration_comparison.png")
print("  - calibration_curve_fit.png")
print("  - event_vs_size_scatter.png")
print("  - calibration_parameters.json")
