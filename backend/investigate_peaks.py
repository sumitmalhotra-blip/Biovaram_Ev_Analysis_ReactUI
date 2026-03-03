"""
Investigation: Re-examine Low mix peaks and find correct bead-to-peak assignment.

The original detection found 4 peaks, but a coarse histogram found 5 peaks in VSSC1-H.
With 4 beads and 5 peaks, one peak is noise/doublets. We need to find the correct
assignment by checking physical consistency.

Strategy:
  - Detect ALL peaks (>= 4)
  - Try all possible assignments of 4 beads to N peaks
  - Score each assignment by AU/sigma consistency
  - Pick the best one
"""

import numpy as np
import miepython
import flowio
from scipy.signal import find_peaks
from scipy.ndimage import gaussian_filter1d
from itertools import combinations
from pathlib import Path

# ============================================================================
# Constants
# ============================================================================

BEAD_DIAMS = [40, 80, 108, 142]
RI_BEAD = 1.591
RI_MEDIUM = 1.33
WL_VSSC = 405.0
WL_BSSC = 488.0


def mie_sigma_back(d, wl, ri_p, ri_m):
    """Compute Qback * pi*r^2 with CORRECT Mie call (absolute m + n_env)."""
    result = miepython.efficiencies(complex(ri_p, 0), d, wl, n_env=ri_m)
    return float(result[2]) * np.pi * (d / 2) ** 2


def mie_sigma_sca(d, wl, ri_p, ri_m):
    """Compute Qsca * pi*r^2 with CORRECT Mie call."""
    result = miepython.efficiencies(complex(ri_p, 0), d, wl, n_env=ri_m)
    return float(result[1]) * np.pi * (d / 2) ** 2


def detect_all_peaks(values, n_bins=2000, smooth_sigma=3.0, min_sep_log=0.12):
    """Detect all significant peaks in log-space histogram."""
    valid = values[values > 0]
    log_vals = np.log10(valid)
    lo, hi = np.percentile(log_vals, [0.1, 99.9])
    edges = np.linspace(lo, hi, n_bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2

    hist, _ = np.histogram(log_vals, bins=edges)
    smooth = gaussian_filter1d(hist.astype(float), sigma=smooth_sigma)

    bin_w = centers[1] - centers[0]
    min_dist = max(int(min_sep_log / bin_w), 5)
    max_h = smooth.max()

    idxs, _ = find_peaks(smooth, distance=min_dist, prominence=max_h * 0.001, height=max_h * 0.005)

    peaks = []
    for idx in idxs:
        pk_log = centers[idx]
        window = 0.1
        mask = (log_vals > pk_log - window) & (log_vals < pk_log + window)
        nearby = valid[mask]
        peaks.append({
            "log10": float(pk_log),
            "au": float(10 ** pk_log),
            "mean_au": float(np.mean(nearby)) if len(nearby) else float(10 ** pk_log),
            "n_events": int(len(nearby)),
            "height": float(smooth[idx]),
        })

    peaks.sort(key=lambda p: p["mean_au"])
    return peaks


def score_assignment(peak_aus, bead_diams, wl, ri_p, ri_m, use_qsca=False):
    """Score a bead-to-peak assignment by AU/sigma consistency."""
    sigmas = []
    for d in bead_diams:
        if use_qsca:
            s = mie_sigma_sca(d, wl, ri_p, ri_m)
        else:
            s = mie_sigma_back(d, wl, ri_p, ri_m)
        sigmas.append(s)

    ratios = [au / s if s > 0 else 1e20 for au, s in zip(peak_aus, sigmas)]
    if min(ratios) <= 0:
        return float('inf'), ratios
    consistency = max(ratios) / min(ratios)
    return consistency, ratios


# ============================================================================
# Main
# ============================================================================

base = Path(__file__).parent

# Load Low mix FCS
fcs = flowio.FlowData(str(base / "nanoFACS/Nano Vis Low.fcs"))
ch_count = fcs.channel_count
events = np.array(fcs.events).reshape(fcs.event_count, ch_count)
names = []
for i in range(1, ch_count + 1):
    n = (fcs.text.get(f"p{i}s", "") or fcs.text.get(f"p{i}n", "") or f"Ch{i}").strip()
    names.append(n)

vssc_idx = names.index("VSSC1-H")
bssc_idx = names.index("BSSC-H")
vssc = events[:, vssc_idx]
bssc = events[:, bssc_idx]

# Detect ALL peaks
print("=" * 70)
print("Low mix VSSC1-H: ALL peaks")
print("=" * 70)
peaks_vssc = detect_all_peaks(vssc)

for i, p in enumerate(peaks_vssc):
    print(f"  Peak {i + 1}: AU={p['mean_au']:>12.0f}  (log={p['log10']:.2f}, N={p['n_events']:,}, height={p['height']:.0f})")

print(f"\nTotal peaks: {len(peaks_vssc)}")

# Try all combinations of 4 peaks from the detected peaks
print(f"\n{'='*70}")
print("Testing all possible bead-to-peak assignments (Qback)")
print(f"{'='*70}")

n_peaks = len(peaks_vssc)
au_list = [p["mean_au"] for p in peaks_vssc]

results = []
for combo in combinations(range(n_peaks), 4):
    selected_aus = [au_list[i] for i in combo]
    consistency, ratios = score_assignment(selected_aus, BEAD_DIAMS, WL_VSSC, RI_BEAD, RI_MEDIUM)
    results.append((consistency, combo, selected_aus, ratios))

results.sort(key=lambda x: x[0])

print(f"\nTop 5 assignments by consistency (lower is better):")
for rank, (consistency, combo, aus, ratios) in enumerate(results[:5]):
    peak_labels = [f"P{i + 1}({au_list[i]:.0f})" for i in combo]
    print(f"\n  #{rank + 1}: consistency = {consistency:.1f}x")
    print(f"     Peaks: {', '.join(peak_labels)}")
    for d, au, r in zip(BEAD_DIAMS, aus, ratios):
        print(f"       d={d:>4d}nm -> AU={au:>12.0f}, AU/sigma={r:>8.1f}")

# Also try Qsca
print(f"\n{'='*70}")
print("Testing all possible assignments (Qsca)")
print(f"{'='*70}")

results_qsca = []
for combo in combinations(range(n_peaks), 4):
    selected_aus = [au_list[i] for i in combo]
    consistency, ratios = score_assignment(selected_aus, BEAD_DIAMS, WL_VSSC, RI_BEAD, RI_MEDIUM, use_qsca=True)
    results_qsca.append((consistency, combo, selected_aus, ratios))

results_qsca.sort(key=lambda x: x[0])

print(f"\nTop 5 assignments by consistency (Qsca, lower is better):")
for rank, (consistency, combo, aus, ratios) in enumerate(results_qsca[:5]):
    peak_labels = [f"P{i + 1}({au_list[i]:.0f})" for i in combo]
    print(f"\n  #{rank + 1}: consistency = {consistency:.1f}x")
    print(f"     Peaks: {', '.join(peak_labels)}")
    for d, au, r in zip(BEAD_DIAMS, aus, ratios):
        print(f"       d={d:>4d}nm -> AU={au:>12.0f}, AU/sigma={r:>8.1f}")

# Cross-check with BSSC ratio for the best assignment
best_combo = results_qsca[0][1]
print(f"\n{'='*70}")
print(f"Cross-check best assignment with VSSC/BSSC ratio")
print(f"{'='*70}")

peaks_bssc = detect_all_peaks(bssc)
print(f"\nBSSC-H peaks:")
for i, p in enumerate(peaks_bssc):
    print(f"  Peak {i + 1}: AU={p['mean_au']:>12.0f}  (log={p['log10']:.2f}, N={p['n_events']:,})")

# Match events for the best VSSC peaks to their BSSC values
print(f"\nBest VSSC assignment: peaks {[i + 1 for i in best_combo]}")
print(f"Checking VSSC/BSSC event-level ratios:")

for peak_idx in best_combo:
    p = peaks_vssc[peak_idx]
    log_au = p["log10"]
    mask = (np.log10(vssc[vssc > 0]) > log_au - 0.1) & (np.log10(vssc[vssc > 0]) < log_au + 0.1)
    valid_vssc = vssc[vssc > 0]
    valid_bssc = bssc[vssc > 0]

    vssc_nearby = valid_vssc[mask]
    bssc_nearby = valid_bssc[mask]
    bssc_nearby = bssc_nearby[bssc_nearby > 0]

    if len(bssc_nearby) > 0:
        ratio = np.median(vssc_nearby[:len(bssc_nearby)]) / np.median(bssc_nearby)
        print(f"  VSSC Peak {peak_idx + 1} (AU={p['mean_au']:.0f}): VSSC/BSSC median ratio = {ratio:.2f}")
