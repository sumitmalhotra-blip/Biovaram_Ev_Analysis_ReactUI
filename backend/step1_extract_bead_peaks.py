"""
Step 1: Extract Bead Peak AU Values from FCS Files (v2 - Fixed)
================================================================

Purpose: Parse nanoViS bead FCS files, detect bead population peaks,
         and extract mean AU (Arbitrary Unit) scatter values for each bead size.

Key findings from initial analysis:
  - Low mix (40, 80, 108, 142nm): 4 clear peaks in VSSC1-H and BSSC-H
  - High mix (142, 304, 600, 1020nm): Large beads SATURATE detector
    -> Only 142nm is identifiable; 304/600/1020nm hit ADC ceiling (~5.38M AU)
  - For EV calibration, Low mix alone provides sufficient coverage (40-142nm)

Input:
  - nanoFACS/Nano Vis Low.fcs  (4 beads: 40, 80, 108, 142 nm)
  - nanoFACS/Nano Vis High.fcs (4 beads: 142, 304, 600, 1020 nm)

Output:
  - calibration_data/bead_peaks.json - merged peak data for calibration

Author: CRMIT Backend Team
Date: February 2026
"""

import sys
import json
import numpy as np
from pathlib import Path
from scipy.signal import find_peaks
from scipy.ndimage import gaussian_filter1d

sys.path.insert(0, str(Path(__file__).parent / "src"))
import flowio


# ============================================================================
# Configuration
# ============================================================================

BEAD_FCS_FILES = {
    "nanoViS_Low": {
        "path": "nanoFACS/Nano Vis Low.fcs",
        "expected_diameters_nm": [40, 80, 108, 142],
        "n_peaks": 4,
    },
    "nanoViS_High": {
        "path": "nanoFACS/Nano Vis High.fcs",
        "expected_diameters_nm": [142, 304, 600, 1020],
        "n_peaks": 4,
    },
}

SCATTER_CHANNELS = {
    "VSSC1-H": {"wavelength_nm": 405, "description": "Violet Side Scatter (Height)"},
    "BSSC-H": {"wavelength_nm": 488, "description": "Blue Side Scatter (Height)"},
}

# Saturation threshold - events above this are detector-saturated
SATURATION_THRESHOLD = 5.0e6


# ============================================================================
# FCS Parsing
# ============================================================================

def parse_fcs(fcs_path: str) -> tuple:
    """Parse FCS file -> (data_dict, channel_names, metadata)."""
    fcs = flowio.FlowData(fcs_path)
    ch_count = fcs.channel_count
    events = np.array(fcs.events).reshape(fcs.event_count, ch_count)

    names = []
    for i in range(1, ch_count + 1):
        n = (
            fcs.text.get(f"p{i}s", "") or
            fcs.text.get(f"p{i}n", "") or
            f"Channel_{i}"
        ).strip() or f"Channel_{i}"
        names.append(n)

    data = {name: events[:, idx] for idx, name in enumerate(names)}
    return data, names, fcs.text


# ============================================================================
# Improved Peak Detection
# ============================================================================

def detect_peaks(
    values: np.ndarray,
    n_expected: int,
    saturation_au: float = SATURATION_THRESHOLD,
    min_peak_sep_log: float = 0.15,
    smooth_sigma: float = 3.0,
    n_bins: int = 2000,
) -> dict:
    """
    Detect bead peaks with saturation awareness.

    Returns dict:
      peaks: list of peak dicts (sorted by AU, ascending)
      n_saturated: count of saturated events
      saturation_pct: percent saturated
    """
    n_saturated = int((values >= saturation_au).sum())
    saturation_pct = 100 * n_saturated / len(values) if len(values) > 0 else 0

    # Work with non-saturated, positive values
    valid = values[(values > 0) & (values < saturation_au)]
    if len(valid) == 0:
        return {"peaks": [], "n_saturated": n_saturated, "saturation_pct": saturation_pct}

    log_vals = np.log10(valid)
    lo, hi = np.percentile(log_vals, [0.1, 99.9])
    edges = np.linspace(lo, hi, n_bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2

    hist, _ = np.histogram(log_vals, bins=edges)
    smooth = gaussian_filter1d(hist.astype(float), sigma=smooth_sigma)

    bin_width = centers[1] - centers[0]
    min_dist = max(int(min_peak_sep_log / bin_width), 5)

    # Progressive prominence search
    max_h = smooth.max()
    for prom_frac in [0.02, 0.01, 0.005, 0.003, 0.001]:
        idxs, _ = find_peaks(
            smooth, distance=min_dist,
            prominence=max_h * prom_frac,
            height=max_h * 0.001,
        )
        if len(idxs) >= n_expected:
            break

    # Keep top-N by height if we found too many
    if len(idxs) > n_expected:
        heights = smooth[idxs]
        top = np.argsort(heights)[-n_expected:]
        idxs = np.sort(idxs[top])

    peaks = []
    for idx in idxs:
        pk_log = centers[idx]
        pk_au = 10 ** pk_log
        window = 0.1  # +/- 0.1 log units
        mask = (log_vals > pk_log - window) & (log_vals < pk_log + window)
        nearby = valid[mask]
        peaks.append({
            "peak_log10": float(pk_log),
            "peak_au": float(pk_au),
            "mean_au": float(np.mean(nearby)) if len(nearby) else float(pk_au),
            "median_au": float(np.median(nearby)) if len(nearby) else float(pk_au),
            "std_au": float(np.std(nearby)) if len(nearby) else 0.0,
            "cv_pct": float(100 * np.std(nearby) / np.mean(nearby)) if len(nearby) and np.mean(nearby) > 0 else 0.0,
            "n_events": int(len(nearby)),
        })

    peaks.sort(key=lambda p: p["mean_au"])

    return {
        "peaks": peaks,
        "n_saturated": n_saturated,
        "saturation_pct": float(saturation_pct),
    }


def match_peaks_to_diameters(peaks: list, diameters: list) -> list:
    """
    Match detected peaks to known bead diameters.
    Simple order-based: sorted peaks <-> sorted diameters.
    """
    matched = []
    for pk, d in zip(peaks, diameters):
        matched.append({**pk, "diameter_nm": d})
    return matched


# ============================================================================
# Main
# ============================================================================

def extract_bead_peaks():
    base = Path(__file__).parent
    all_results = {}

    for mix, cfg in BEAD_FCS_FILES.items():
        path = base / cfg["path"]
        diams = cfg["expected_diameters_nm"]
        n_pk = cfg["n_peaks"]

        print(f"\n{'='*70}")
        print(f"  {mix}: {path.name}")
        print(f"  Expected beads: {diams} nm")
        print(f"{'='*70}")

        if not path.exists():
            print(f"  ERROR: file not found: {path}")
            continue

        data, ch_names, meta = parse_fcs(str(path))
        n_ev = len(next(iter(data.values())))
        print(f"  Events: {n_ev:,}")

        mix_result = {
            "file": path.name,
            "n_events": n_ev,
            "expected_diameters_nm": diams,
        }

        for ch, ch_info in SCATTER_CHANNELS.items():
            print(f"\n  --- {ch} ({ch_info['description']}) ---")
            if ch not in data:
                print(f"  Channel not found! Available: {list(data.keys())}")
                continue

            vals = data[ch]
            result = detect_peaks(vals, n_pk)
            peaks = result["peaks"]

            print(f"  Range: {vals.min():.1f} - {vals.max():.1f} AU")
            print(f"  Saturated: {result['n_saturated']:,} ({result['saturation_pct']:.1f}%)")
            print(f"  Peaks found (non-saturated): {len(peaks)}")

            if result["saturation_pct"] > 5:
                print(f"  WARNING: SIGNIFICANT SATURATION - large beads hit detector ceiling")

            # Match peaks to diameters
            if len(peaks) >= n_pk:
                matched = match_peaks_to_diameters(peaks, diams)
            elif len(peaks) > 0:
                # For High mix with saturation, match available peaks to smallest diameters
                matched = match_peaks_to_diameters(peaks, diams[:len(peaks)])
                print(f"  WARNING: Only {len(peaks)} peaks found (expected {n_pk})")
                print(f"  Saturated beads cannot be calibrated at current gain")
            else:
                matched = []

            for m in matched:
                d = m.get("diameter_nm", "?")
                print(f"    d={d:>4} nm -> AU={m['mean_au']:>12.1f} +/- {m['std_au']:>8.1f} "
                      f"(CV={m['cv_pct']:.1f}%, N={m['n_events']:,})")

            mix_result[ch] = {
                "peaks": matched,
                "n_saturated": result["n_saturated"],
                "saturation_pct": result["saturation_pct"],
            }

        all_results[mix] = mix_result

    return all_results


def build_calibration_dataset(results: dict) -> dict:
    """
    Build merged calibration dataset from Low + High mixes.

    Strategy:
      - Low mix: use all 4 beads (40, 80, 108, 142 nm) - primary source
      - High mix: use only non-saturated peaks for cross-validation
      - For shared diameters (142nm): average if both measurements are valid
      - Mark saturated peaks as excluded
    """
    merged = {}

    for ch in SCATTER_CHANNELS:
        bead_map = {}  # diameter -> list of measurements

        for mix in ["nanoViS_Low", "nanoViS_High"]:
            if mix not in results:
                continue
            if ch not in results[mix]:
                continue

            sat_pct = results[mix][ch]["saturation_pct"]
            peaks = results[mix][ch]["peaks"]

            for pk in peaks:
                d = pk.get("diameter_nm")
                if d is None:
                    continue

                # For High mix with significant saturation, cross-check against Low
                if mix == "nanoViS_High" and sat_pct > 5:
                    low_peaks = results.get("nanoViS_Low", {}).get(ch, {}).get("peaks", [])
                    low_match = [p for p in low_peaks if p.get("diameter_nm") == d]
                    if low_match and pk["mean_au"] < low_match[0]["mean_au"] * 0.01:
                        print(f"  Skipping {mix}/{ch} d={d}nm: {pk['mean_au']:.0f} AU "
                              f"<< Low mix {low_match[0]['mean_au']:.0f} AU (noise)")
                        continue

                if d not in bead_map:
                    bead_map[d] = []
                bead_map[d].append({**pk, "source": mix})

        # Merge duplicates
        channel_data = []
        for d in sorted(bead_map):
            measurements = bead_map[d]
            if len(measurements) == 1:
                m = measurements[0]
                channel_data.append({
                    "diameter_nm": d,
                    "mean_au": m["mean_au"],
                    "std_au": m["std_au"],
                    "cv_pct": m["cv_pct"],
                    "n_events": m["n_events"],
                    "source": m["source"],
                })
            else:
                avg_au = float(np.mean([m["mean_au"] for m in measurements]))
                avg_std = float(np.mean([m["std_au"] for m in measurements]))
                total_n = sum(m["n_events"] for m in measurements)
                channel_data.append({
                    "diameter_nm": d,
                    "mean_au": avg_au,
                    "std_au": avg_std,
                    "cv_pct": float(100 * avg_std / avg_au) if avg_au > 0 else 0,
                    "n_events": total_n,
                    "source": "averaged",
                    "note": f"Averaged: {[m['source'] for m in measurements]}",
                })

        merged[ch] = channel_data

    return merged


def main():
    print("=" * 70)
    print("STEP 1: Extract Bead Peak AU Values (v2 - with saturation handling)")
    print("=" * 70)

    results = extract_bead_peaks()

    print(f"\n{'='*70}")
    print("Building calibration dataset (Low mix primary, High mix validation)")
    print(f"{'='*70}")

    merged = build_calibration_dataset(results)

    for ch, beads in merged.items():
        wl = SCATTER_CHANNELS[ch]["wavelength_nm"]
        print(f"\n  {ch} ({wl}nm) - {len(beads)} calibration points:")
        for b in beads:
            src = b.get("source", "")
            print(f"    d={b['diameter_nm']:>4d} nm -> AU={b['mean_au']:>12.1f} "
                  f"+/- {b['std_au']:>8.1f}  [{src}]")

    # Save
    out_dir = Path(__file__).parent / "calibration_data"
    out_dir.mkdir(exist_ok=True)

    output = {
        "description": "Bead peak AU values for FCMPASS calibration",
        "bead_kit": "nanoViS D03231",
        "bead_ri": 1.591,
        "instrument": "CytoFLEX nano BH46064",
        "notes": [
            "Low mix (40-142nm): all 4 peaks detected, primary calibration source",
            "High mix (142-1020nm): large beads saturated at ~5.38M AU",
            "High mix only useful for 142nm cross-validation",
        ],
        "per_mix": {},
        "calibration": {},
    }

    for mix, data in results.items():
        output["per_mix"][mix] = {}
        for ch in SCATTER_CHANNELS:
            if ch in data:
                output["per_mix"][mix][ch] = data[ch]

    for ch, beads in merged.items():
        output["calibration"][ch] = beads

    out_path = out_dir / "bead_peaks.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n  Saved: {out_path}")

    # Verify monotonicity
    print(f"\n{'='*70}")
    print("MONOTONICITY CHECK")
    print(f"{'='*70}")
    for ch, beads in merged.items():
        aus = [b["mean_au"] for b in beads]
        ds = [b["diameter_nm"] for b in beads]
        is_mono = all(aus[i] < aus[i + 1] for i in range(len(aus) - 1))
        status = "PASS" if is_mono else "FAIL (non-monotonic)"
        print(f"  {ch}: {status}")
        if not is_mono:
            for i in range(len(aus) - 1):
                if aus[i] >= aus[i + 1]:
                    print(f"    d={ds[i]}nm ({aus[i]:.0f} AU) >= d={ds[i+1]}nm ({aus[i+1]:.0f} AU)")

    return results, merged


if __name__ == "__main__":
    results, merged = main()
