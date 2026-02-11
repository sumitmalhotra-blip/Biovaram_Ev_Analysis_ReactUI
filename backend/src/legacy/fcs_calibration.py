#!/usr/bin/env python3
"""
FCS Calibration and NTA/FCS Comparison Module
==============================================

This module provides:
1. SSC-to-Size calibration from Nano Vis bead data
2. Dilution correction for NTA/FCS comparison
3. Batch processing of multiple FCS files

Calibration derived from:
- Nano Vis Low: 40-150nm polystyrene beads
- Nano Vis High: 140-1000nm polystyrene beads

Author: BioVaram EV Analysis Platform
Date: January 2026
"""

import flowio
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Union
import json
from dataclasses import dataclass, asdict
import warnings


# =============================================================================
# CALIBRATION PARAMETERS (from Nano Vis analysis)
# =============================================================================

# Combined 4-point calibration from Nano Vis Low/High
# Formula: size_nm = 10^b * SSC^a
# Or: log10(size) = a * log10(SSC) + b
DEFAULT_CALIBRATION = {
    'log_slope_a': 0.1960,
    'log_intercept_b': 1.3537,
    'coefficient_k': 22.5792,  # 10^b
    'description': 'Combined calibration from Nano Vis Low (40-150nm) and High (140-1000nm)'
}

# Dilution factors from Jan 21, 2026 meeting
DEFAULT_DILUTION_FACTORS = {
    'nta_sample_volume_ul': 1000,     # NTA uses 1 mL
    'nanofacs_sample_volume_ul': 23,   # NanoFACS takes 23 µL
    'nanofacs_final_volume_ul': 150,   # Diluted to 150 µL
    'total_dilution_factor': 283.6     # Total effective dilution
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CalibrationParams:
    """Calibration parameters for SSC-to-Size conversion"""
    log_slope_a: float = 0.1960
    log_intercept_b: float = 1.3537
    
    @property
    def coefficient_k(self) -> float:
        return 10 ** self.log_intercept_b
    
    def ssc_to_size(self, ssc: np.ndarray) -> np.ndarray:
        """Convert SSC values to size in nm"""
        with np.errstate(divide='ignore', invalid='ignore'):
            log_ssc = np.log10(np.maximum(ssc, 1))
            log_size = self.log_slope_a * log_ssc + self.log_intercept_b
            size_nm = 10 ** log_size
        return np.clip(size_nm, 1, 10000)  # Clip to reasonable range
    
    def size_to_ssc(self, size_nm: np.ndarray) -> np.ndarray:
        """Inverse: convert size in nm to expected SSC"""
        log_size = np.log10(np.maximum(size_nm, 1))
        log_ssc = (log_size - self.log_intercept_b) / self.log_slope_a
        return 10 ** log_ssc


@dataclass
class DilutionFactors:
    """Dilution factors for NTA/FCS comparison"""
    nta_sample_volume_ul: float = 1000
    nanofacs_sample_volume_ul: float = 23
    nanofacs_final_volume_ul: float = 150
    
    @property
    def volume_reduction(self) -> float:
        return self.nta_sample_volume_ul / self.nanofacs_sample_volume_ul
    
    @property
    def additional_dilution(self) -> float:
        return self.nanofacs_final_volume_ul / self.nanofacs_sample_volume_ul
    
    @property
    def total_dilution(self) -> float:
        return self.volume_reduction * self.additional_dilution
    
    def nta_to_fcs_count(self, nta_count: float) -> float:
        """Convert NTA particle count to expected FCS count"""
        return nta_count / self.total_dilution
    
    def fcs_to_nta_count(self, fcs_count: float) -> float:
        """Convert FCS particle count to equivalent NTA count"""
        return fcs_count * self.total_dilution


@dataclass
class FCSAnalysisResult:
    """Results from analyzing an FCS file"""
    filename: str
    total_events: int
    valid_events: int
    saturated_events: int
    saturation_percent: float
    
    # Size statistics (in nm)
    size_mean: float
    size_median: float
    size_std: float
    size_p10: float
    size_p25: float
    size_p75: float
    size_p90: float
    
    # SSC statistics
    ssc_mean: float
    ssc_median: float
    
    # Size distribution bins
    size_bins: Optional[List[float]] = None
    size_counts: Optional[List[int]] = None


# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def load_fcs_file(filepath: Union[str, Path]) -> Tuple[pd.DataFrame, Dict]:
    """
    Load an FCS file and return data as DataFrame with metadata
    
    Parameters
    ----------
    filepath : str or Path
        Path to the FCS file
    
    Returns
    -------
    data : pd.DataFrame
        Event data with channel names as columns
    metadata : dict
        FCS file metadata
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"FCS file not found: {filepath}")
    
    fcs = flowio.FlowData(str(filepath))
    
    # Extract channel names
    channels = [fcs.channels[str(i+1)]['PnN'] for i in range(fcs.channel_count)]
    
    # Reshape events
    events = np.array(fcs.events).reshape(-1, len(channels))
    data = pd.DataFrame(events, columns=channels)
    
    # Extract useful metadata
    metadata = {
        'filename': filepath.name,
        'filepath': str(filepath),
        'channel_count': fcs.channel_count,
        'event_count': len(data),
        'channels': channels,
        'text': dict(fcs.text)
    }
    
    return data, metadata


def find_scatter_channels(channels: List[str]) -> Dict[str, str]:
    """
    Find the appropriate scatter channels in an FCS file
    
    Different instruments use different naming conventions:
    - Nano Vis: FSC-H, SSC-H, SSC_1-H, etc.
    - PC3: VSSC1-H, BSSC1-H, etc.
    - HEK TFF (NanoFCM): Has 'Size' column directly (no scatter channels)
    
    Returns dict mapping standard names to actual channel names
    """
    channel_map = {}
    
    # Check if this is NanoFCM format with direct Size measurement
    for ch in channels:
        if ch.upper() == 'SIZE':
            channel_map['size_direct'] = ch
            return channel_map  # No scatter channels needed
    
    # Forward scatter
    for ch in channels:
        if 'FSC-H' in ch.upper() or 'FSC_H' in ch.upper():
            channel_map['fsc'] = ch
            break
    
    # Side scatter - prefer SSC-H, fallback to VSSC or SSC_1
    ssc_candidates = ['SSC-H', 'SSC_H', 'VSSC1-H', 'VSSC-H', 'SSC_1-H']
    for candidate in ssc_candidates:
        for ch in channels:
            if candidate.upper() in ch.upper():
                channel_map['ssc'] = ch
                break
        if 'ssc' in channel_map:
            break
    
    # If no specific match, look for any SSC
    if 'ssc' not in channel_map:
        for ch in channels:
            if 'SSC' in ch.upper() and '-H' in ch.upper():
                channel_map['ssc'] = ch
                break
    
    return channel_map


def analyze_fcs_file(
    filepath: Union[str, Path],
    calibration: Optional[CalibrationParams] = None,
    ssc_channel: Optional[str] = None,
    saturation_threshold: Optional[float] = None
) -> FCSAnalysisResult:
    """
    Analyze an FCS file and return size distribution statistics
    
    Parameters
    ----------
    filepath : str or Path
        Path to the FCS file
    calibration : CalibrationParams, optional
        Calibration parameters. Uses default if not provided.
    ssc_channel : str, optional
        Name of SSC channel to use. Auto-detected if not provided.
    saturation_threshold : float, optional
        SSC value above which events are considered saturated.
        Auto-calculated as 95% of max if not provided.
    
    Returns
    -------
    FCSAnalysisResult
        Analysis results including size statistics
    """
    if calibration is None:
        calibration = CalibrationParams()
    
    # Load data
    data, metadata = load_fcs_file(filepath)
    
    # Find scatter channels
    channel_map = find_scatter_channels(metadata['channels'])
    
    # Check if this is NanoFCM format with direct size
    if 'size_direct' in channel_map:
        # Direct size measurement - no calibration needed
        size_col = channel_map['size_direct']
        sizes: np.ndarray = np.asarray(data[size_col].values)
        sizes = sizes[sizes > 0]  # Filter valid
        
        # No saturation for direct measurement
        n_saturated = 0
        pct_saturated = 0.0
        ssc_mean = 0.0
        ssc_median = 0.0
    else:
        # Standard scatter-based measurement
        if ssc_channel is None:
            if 'ssc' not in channel_map:
                raise ValueError(f"Could not find SSC channel in {filepath}")
            ssc_channel = channel_map['ssc']
        
        # Get SSC values
        ssc: np.ndarray = np.asarray(data[ssc_channel].values)
        
        # Filter valid events (positive SSC)
        valid_mask = ssc > 0
        ssc_valid: np.ndarray = ssc[valid_mask]
        
        # Detect saturation
        if saturation_threshold is None:
            saturation_threshold = float(np.max(ssc_valid) * 0.95)
        
        saturated_mask = ssc_valid > saturation_threshold
        n_saturated = int(np.sum(saturated_mask))
        pct_saturated = 100 * n_saturated / len(ssc_valid) if len(ssc_valid) > 0 else 0
        
        # Apply calibration (exclude saturated for stats)
        ssc_non_sat: np.ndarray = ssc_valid[~saturated_mask]
        if len(ssc_non_sat) == 0:
            ssc_non_sat = ssc_valid  # Fallback if all saturated
        
        sizes = calibration.ssc_to_size(np.asarray(ssc_non_sat))
        ssc_mean = float(np.mean(np.asarray(ssc_non_sat)))
        ssc_median = float(np.median(np.asarray(ssc_non_sat)))
    
    # Calculate statistics
    sizes_arr = np.asarray(sizes)
    size_mean = float(np.mean(sizes_arr))
    size_median = float(np.median(sizes_arr))
    size_std = float(np.std(sizes_arr))
    p10, p25, p75, p90 = np.percentile(sizes_arr, [10, 25, 75, 90])
    
    # Calculate size distribution bins
    size_bins: List[float] = [0.0, 50.0, 100.0, 150.0, 200.0, 300.0, 500.0, 1000.0, 2000.0]
    size_counts: List[int] = []
    for i in range(len(size_bins) - 1):
        count = np.sum((sizes_arr >= size_bins[i]) & (sizes_arr < size_bins[i+1]))
        size_counts.append(int(count))
    
    return FCSAnalysisResult(
        filename=metadata['filename'],
        total_events=len(data),
        valid_events=int(len(sizes)),
        saturated_events=n_saturated,
        saturation_percent=float(pct_saturated),
        size_mean=size_mean,
        size_median=size_median,
        size_std=size_std,
        size_p10=float(p10),
        size_p25=float(p25),
        size_p75=float(p75),
        size_p90=float(p90),
        ssc_mean=ssc_mean,
        ssc_median=ssc_median,
        size_bins=size_bins,
        size_counts=size_counts
    )


def batch_analyze_fcs(
    directory: Union[str, Path],
    pattern: str = "*.fcs",
    calibration: Optional[CalibrationParams] = None,
    exclude_blanks: bool = True
) -> List[FCSAnalysisResult]:
    """
    Batch analyze all FCS files in a directory
    
    Parameters
    ----------
    directory : str or Path
        Directory containing FCS files
    pattern : str
        Glob pattern for file matching
    calibration : CalibrationParams, optional
        Calibration parameters
    exclude_blanks : bool
        Whether to exclude blank/water samples from analysis
    
    Returns
    -------
    List[FCSAnalysisResult]
        Analysis results for each file
    """
    directory = Path(directory)
    results = []
    
    blank_keywords = ['blank', 'water', 'hplc']
    
    for fcs_path in sorted(directory.glob(pattern)):
        # Skip blanks if requested
        if exclude_blanks:
            name_lower = fcs_path.stem.lower()
            if any(kw in name_lower for kw in blank_keywords):
                continue
        
        try:
            result = analyze_fcs_file(fcs_path, calibration)
            results.append(result)
        except Exception as e:
            warnings.warn(f"Failed to analyze {fcs_path.name}: {e}")
    
    return results


def compare_nta_fcs(
    nta_count: float,
    fcs_count: float,
    nta_mean_size: Optional[float] = None,
    fcs_mean_size: Optional[float] = None,
    dilution: Optional[DilutionFactors] = None
) -> Dict:
    """
    Compare NTA and FCS measurements with dilution correction
    
    Parameters
    ----------
    nta_count : float
        Particle count from NTA (per mL)
    fcs_count : float
        Event count from FCS
    nta_mean_size : float, optional
        Mean particle size from NTA (nm)
    fcs_mean_size : float, optional
        Mean particle size from FCS (nm)
    dilution : DilutionFactors, optional
        Dilution factors. Uses default if not provided.
    
    Returns
    -------
    dict
        Comparison results including corrected counts and ratios
    """
    if dilution is None:
        dilution = DilutionFactors()
    
    # Expected FCS count based on NTA with dilution correction
    expected_fcs_count = dilution.nta_to_fcs_count(nta_count)
    
    # Ratio of actual to expected
    count_ratio = fcs_count / expected_fcs_count if expected_fcs_count > 0 else float('inf')
    
    result = {
        'nta_count': nta_count,
        'fcs_count': fcs_count,
        'dilution_factor': dilution.total_dilution,
        'expected_fcs_count': expected_fcs_count,
        'count_ratio': count_ratio,
        'count_match_percent': min(count_ratio, 1/count_ratio) * 100 if count_ratio > 0 else 0
    }
    
    # Size comparison if provided
    if nta_mean_size is not None and fcs_mean_size is not None:
        size_ratio = fcs_mean_size / nta_mean_size if nta_mean_size > 0 else float('inf')
        result['nta_mean_size'] = nta_mean_size
        result['fcs_mean_size'] = fcs_mean_size
        result['size_ratio'] = size_ratio
        # Note: FCS sizes may be larger due to antibody labeling
        result['size_note'] = 'FCS may show larger sizes due to antibody labeling'
    
    return result


# =============================================================================
# VISUALIZATION
# =============================================================================

def plot_size_distribution(
    result: FCSAnalysisResult,
    ax=None,
    title: Optional[str] = None,
    expected_range: Optional[Tuple[float, float]] = None
):
    """
    Plot size distribution from FCS analysis result
    
    Parameters
    ----------
    result : FCSAnalysisResult
        Analysis result to plot
    ax : matplotlib.axes.Axes, optional
        Axes to plot on. Creates new figure if not provided.
    title : str, optional
        Plot title. Uses filename if not provided.
    expected_range : tuple, optional
        Expected size range (min, max) to highlight
    """
    import matplotlib.pyplot as plt
    
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot histogram bars - handle optional types
    bins = result.size_bins if result.size_bins is not None else [0.0, 100.0, 200.0, 500.0]
    counts = result.size_counts if result.size_counts is not None else [0]
    
    bin_centers = [(bins[i] + bins[i+1])/2 for i in range(len(bins)-1)]
    bin_widths = [bins[i+1] - bins[i] for i in range(len(bins)-1)]
    
    ax.bar(bin_centers, counts, width=[w*0.8 for w in bin_widths], 
           alpha=0.7, color='steelblue', edgecolor='black')
    
    # Add expected range if provided
    if expected_range:
        ax.axvline(expected_range[0], color='green', linestyle='--', 
                   linewidth=2, label=f'Expected: {expected_range[0]}-{expected_range[1]}nm')
        ax.axvline(expected_range[1], color='green', linestyle='--', linewidth=2)
        ax.axvspan(expected_range[0], expected_range[1], alpha=0.1, color='green')
    
    # Add statistics annotations
    stats_text = f"Mean: {result.size_mean:.1f}nm\nMedian: {result.size_median:.1f}nm\nP10-P90: {result.size_p10:.0f}-{result.size_p90:.0f}nm"
    ax.text(0.95, 0.95, stats_text, transform=ax.transAxes, 
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    ax.set_xlabel('Size (nm)')
    ax.set_ylabel('Count')
    ax.set_title(title or result.filename)
    ax.set_xlim(0, max(bins) if bins else 500)
    
    if expected_range:
        ax.legend(loc='upper left')
    
    return ax


def generate_batch_report(
    results: List[FCSAnalysisResult],
    output_dir: Union[str, Path],
    report_name: str = "fcs_analysis_report"
):
    """
    Generate a comprehensive report from batch FCS analysis
    
    Parameters
    ----------
    results : List[FCSAnalysisResult]
        List of analysis results
    output_dir : str or Path
        Directory to save report files
    report_name : str
        Base name for report files
    """
    import matplotlib.pyplot as plt
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save JSON summary
    summary_data = {
        'analysis_date': pd.Timestamp.now().isoformat(),
        'calibration': DEFAULT_CALIBRATION,
        'dilution_factors': DEFAULT_DILUTION_FACTORS,
        'results': [asdict(r) for r in results]
    }
    
    with open(output_dir / f"{report_name}.json", 'w') as f:
        json.dump(summary_data, f, indent=2)
    
    # Create comparison DataFrame
    df = pd.DataFrame([asdict(r) for r in results])
    df.to_csv(output_dir / f"{report_name}.csv", index=False)
    
    # Generate plots
    n_samples = len(results)
    if n_samples > 0:
        # Size distribution comparison
        n_cols = min(4, n_samples)
        n_rows = (n_samples + n_cols - 1) // n_cols
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(4*n_cols, 4*n_rows))
        if n_samples == 1:
            axes = [axes]
        else:
            axes = axes.flatten()
        
        for i, result in enumerate(results):
            if i < len(axes):
                plot_size_distribution(result, axes[i])
        
        # Hide unused subplots
        last_idx = len(results) - 1
        for j in range(last_idx + 1, len(axes)):
            axes[j].set_visible(False)
        
        plt.tight_layout()
        plt.savefig(output_dir / f"{report_name}_distributions.png", dpi=150, bbox_inches='tight')
        plt.close()
        
        # Summary comparison plot
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        # Mean sizes
        ax = axes[0]
        ax.barh(range(len(results)), [r.size_mean for r in results], color='steelblue')
        ax.set_yticks(range(len(results)))
        ax.set_yticklabels([r.filename[:20] for r in results], fontsize=8)
        ax.set_xlabel('Mean Size (nm)')
        ax.set_title('Mean Particle Size by Sample')
        
        # Event counts
        ax = axes[1]
        ax.barh(range(len(results)), [r.valid_events for r in results], color='coral')
        ax.set_yticks(range(len(results)))
        ax.set_yticklabels([r.filename[:20] for r in results], fontsize=8)
        ax.set_xlabel('Valid Events')
        ax.set_title('Event Counts by Sample')
        ax.set_xscale('log')
        
        # Saturation percentage
        ax = axes[2]
        ax.barh(range(len(results)), [r.saturation_percent for r in results], color='goldenrod')
        ax.set_yticks(range(len(results)))
        ax.set_yticklabels([r.filename[:20] for r in results], fontsize=8)
        ax.set_xlabel('Saturation %')
        ax.set_title('Detector Saturation by Sample')
        ax.axvline(20, color='red', linestyle='--', alpha=0.5, label='20% threshold')
        ax.legend()
        
        plt.tight_layout()
        plt.savefig(output_dir / f"{report_name}_summary.png", dpi=150, bbox_inches='tight')
        plt.close()
    
    print(f"Report saved to: {output_dir}")
    print(f"  - {report_name}.json")
    print(f"  - {report_name}.csv")
    print(f"  - {report_name}_distributions.png")
    print(f"  - {report_name}_summary.png")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze FCS files with calibration")
    parser.add_argument("path", help="FCS file or directory to analyze")
    parser.add_argument("-o", "--output", default="reports/fcs_analysis",
                        help="Output directory for reports")
    parser.add_argument("--exclude-blanks", action="store_true",
                        help="Exclude blank/water samples from batch analysis")
    
    args = parser.parse_args()
    
    path = Path(args.path)
    calibration = CalibrationParams()
    
    if path.is_file():
        # Single file analysis
        result = analyze_fcs_file(path, calibration)
        print(f"\n{result.filename}")
        print(f"  Events: {result.valid_events:,} ({result.saturation_percent:.1f}% saturated)")
        print(f"  Size: Mean={result.size_mean:.1f}nm, Median={result.size_median:.1f}nm")
        print(f"  P10-P90: {result.size_p10:.0f}-{result.size_p90:.0f}nm")
    
    elif path.is_dir():
        # Batch analysis
        results = batch_analyze_fcs(path, calibration=calibration, 
                                    exclude_blanks=args.exclude_blanks)
        if results:
            generate_batch_report(results, args.output)
        else:
            print("No FCS files found to analyze")
    
    else:
        print(f"Path not found: {path}")
