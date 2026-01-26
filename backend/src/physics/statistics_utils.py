"""
Advanced Statistics Utilities for EV Analysis
==============================================

Provides improved statistical methods for particle sizing:
1. KDE-based mode calculation (bin-size independent)
2. Multi-modal distribution detection
3. Configurable histogram binning
4. Bootstrap confidence intervals

Author: CRMIT Backend Team
Date: January 20, 2026
"""

import numpy as np
from typing import Tuple, List, Optional, Dict, Any, Union, cast
from scipy import stats
from scipy.signal import find_peaks
from dataclasses import dataclass
from loguru import logger


@dataclass
class ModeResult:
    """
    Result from mode calculation.
    
    Attributes:
        mode: Primary mode value
        modes: All detected modes (for multi-modal distributions)
        method: Method used for calculation
        bandwidth: KDE bandwidth (if applicable)
        confidence: Confidence in mode estimate (0-1)
    """
    mode: float
    modes: List[float]
    method: str
    bandwidth: Optional[float] = None
    confidence: float = 1.0


@dataclass
class DistributionStats:
    """
    Comprehensive distribution statistics.
    """
    n: int
    mean: float
    std: float
    median: float
    mode: float
    modes: List[float]
    d10: float
    d25: float
    d50: float
    d75: float
    d90: float
    iqr: float
    skewness: float
    kurtosis: float
    min: float
    max: float
    ci_95_mean: Tuple[float, float]


def calculate_mode_kde(
    data: np.ndarray,
    bandwidth: Optional[float] = None,
    n_points: int = 1000,
    return_full: bool = False
) -> float | ModeResult:
    """
    Calculate mode using Kernel Density Estimation.
    
    This method is more robust than histogram-based mode because:
    1. No arbitrary bin size selection
    2. Continuous estimation of probability density
    3. Better handling of sparse data
    
    Args:
        data: Array of values
        bandwidth: KDE bandwidth (Scott's rule if None)
        n_points: Number of points for KDE evaluation
        return_full: If True, return ModeResult with details
        
    Returns:
        Mode value, or ModeResult if return_full=True
    """
    data = np.asarray(data)
    data = data[np.isfinite(data)]
    
    if len(data) < 3:
        mode = float(np.median(data)) if len(data) > 0 else 0.0
        if return_full:
            return ModeResult(mode=mode, modes=[mode], method='median_fallback')
        return mode
    
    # Create KDE
    try:
        kde = stats.gaussian_kde(data, bw_method=bandwidth)
    except Exception as e:
        logger.warning(f"KDE failed: {e}, using histogram fallback")
        mode = float(np.median(data))
        if return_full:
            return ModeResult(mode=mode, modes=[mode], method='median_fallback')
        return mode
    
    # Evaluate KDE on fine grid
    data_range = data.max() - data.min()
    margin = data_range * 0.1
    x_grid = np.linspace(data.min() - margin, data.max() + margin, n_points)
    density = kde(x_grid)
    
    # Find primary mode (global maximum)
    mode_idx = np.argmax(density)
    primary_mode = float(x_grid[mode_idx])
    
    if not return_full:
        return primary_mode
    
    # Find all modes (peaks in density)
    peaks, properties = find_peaks(density, prominence=0.01 * density.max())
    
    if len(peaks) == 0:
        modes = [primary_mode]
    else:
        modes = sorted([float(x_grid[p]) for p in peaks], 
                      key=lambda x: -kde([x])[0])
    
    # Estimate confidence based on peak prominence
    if len(peaks) > 0:
        max_density = density.max()
        second_max = np.partition(density[peaks], -min(2, len(peaks)))[-min(2, len(peaks))]
        confidence = float(1.0 - second_max / max_density) if max_density > 0 else 1.0
    else:
        confidence = 1.0
    
    return ModeResult(
        mode=primary_mode,
        modes=modes,
        method='kde',
        bandwidth=float(kde.factor),  # type: ignore[arg-type]
        confidence=confidence
    )


def calculate_mode_histogram(
    data: np.ndarray,
    bin_size: Optional[float] = None,
    n_bins: Optional[int] = None,
    method: str = 'auto'
) -> float:
    """
    Calculate mode using histogram method with configurable binning.
    
    Args:
        data: Array of values
        bin_size: Fixed bin size in data units
        n_bins: Number of bins (overrides bin_size)
        method: Binning method if neither specified:
               'auto', 'fd' (Freedman-Diaconis), 'scott', 'sturges'
               
    Returns:
        Mode value (center of most populated bin)
    """
    data = np.asarray(data)
    data = data[np.isfinite(data)]
    
    if len(data) < 3:
        return float(np.median(data)) if len(data) > 0 else 0.0
    
    # Determine bins
    if n_bins is not None:
        bins = n_bins
    elif bin_size is not None:
        data_range = data.max() - data.min()
        bins = max(1, int(np.ceil(data_range / bin_size)))
    else:
        bins = method
    
    # Create histogram
    counts, bin_edges = np.histogram(data, bins=bins)
    
    # Find mode (most populated bin center)
    max_idx = np.argmax(counts)
    mode = (bin_edges[max_idx] + bin_edges[max_idx + 1]) / 2.0
    
    return float(mode)


def calculate_comprehensive_stats(
    data: np.ndarray,
    bootstrap_ci: bool = True,
    n_bootstrap: int = 1000
) -> DistributionStats:
    """
    Calculate comprehensive distribution statistics.
    
    Args:
        data: Array of values
        bootstrap_ci: Calculate bootstrap confidence intervals
        n_bootstrap: Number of bootstrap samples
        
    Returns:
        DistributionStats with all statistics
    """
    data = np.asarray(data)
    data = data[np.isfinite(data)]
    n = len(data)
    
    if n == 0:
        raise ValueError("No valid data points")
    
    # Basic statistics
    mean = float(np.mean(data))
    std = float(np.std(data, ddof=1)) if n > 1 else 0.0
    median = float(np.median(data))
    
    # Mode using KDE
    mode_full = cast(ModeResult, calculate_mode_kde(data, return_full=True))
    mode = mode_full.mode
    modes = mode_full.modes
    
    # Percentiles
    percentiles = np.percentile(data, [10, 25, 50, 75, 90])
    d10, d25, d50, d75, d90 = [float(p) for p in percentiles]
    iqr = d75 - d25
    
    # Higher moments
    if n > 3:
        skewness = float(stats.skew(data))
        kurtosis = float(stats.kurtosis(data))
    else:
        skewness = 0.0
        kurtosis = 0.0
    
    # Bootstrap confidence interval for mean
    if bootstrap_ci and n > 10:
        bootstrap_means = []
        for _ in range(n_bootstrap):
            sample = np.random.choice(data, size=n, replace=True)
            bootstrap_means.append(np.mean(sample))
        ci_95_mean = (
            float(np.percentile(bootstrap_means, 2.5)),
            float(np.percentile(bootstrap_means, 97.5))
        )
    else:
        # Use t-distribution approximation
        se = std / np.sqrt(n) if n > 1 else 0
        t_crit = stats.t.ppf(0.975, df=n-1) if n > 1 else 2.0
        ci_95_mean = (mean - t_crit * se, mean + t_crit * se)
    
    return DistributionStats(
        n=n,
        mean=mean,
        std=std,
        median=median,
        mode=mode,
        modes=modes,
        d10=d10,
        d25=d25,
        d50=d50,
        d75=d75,
        d90=d90,
        iqr=iqr,
        skewness=skewness,
        kurtosis=kurtosis,
        min=float(data.min()),
        max=float(data.max()),
        ci_95_mean=(float(ci_95_mean[0]), float(ci_95_mean[1])),
    )


def detect_multimodality(
    data: np.ndarray,
    significance: float = 0.05
) -> Dict[str, Any]:
    """
    Test for multimodality in the distribution.
    
    Uses Hartigan's dip test and visual inspection of KDE.
    
    Args:
        data: Array of values
        significance: Significance level for tests
        
    Returns:
        Dictionary with multimodality analysis results
    """
    data = np.asarray(data)
    data = data[np.isfinite(data)]
    
    # Get KDE-based modes
    mode_full = cast(ModeResult, calculate_mode_kde(data, return_full=True))
    n_modes = len(mode_full.modes)
    
    # Silverman's test for multimodality
    # Compare bandwidth for unimodal vs current fit
    try:
        kde = stats.gaussian_kde(data)
        bandwidth = kde.factor
    except:
        bandwidth = None
    
    # Simple heuristic: check if secondary modes have significant density
    significant_modes = []
    if n_modes > 1 and bandwidth:
        kde = stats.gaussian_kde(data)
        primary_density = kde([mode_full.mode])[0]
        
        for m in mode_full.modes:
            density = kde([m])[0]
            if density >= 0.3 * primary_density:  # At least 30% of primary
                significant_modes.append({
                    'mode': m,
                    'relative_density': density / primary_density
                })
    else:
        significant_modes = [{'mode': mode_full.mode, 'relative_density': 1.0}]
    
    is_multimodal = len(significant_modes) > 1
    
    return {
        'is_multimodal': is_multimodal,
        'n_significant_modes': len(significant_modes),
        'modes': significant_modes,
        'primary_mode': mode_full.mode,
        'kde_bandwidth': bandwidth,
        'confidence': mode_full.confidence
    }


def create_size_histogram(
    data: np.ndarray,
    bin_edges: Optional[np.ndarray] = None,
    bin_size: float = 5.0,
    range_nm: Tuple[float, float] = (0, 500),
    normalize: bool = True
) -> Dict[str, Any]:
    """
    Create size distribution histogram with configurable parameters.
    
    Args:
        data: Array of diameter values in nm
        bin_edges: Custom bin edges (overrides bin_size)
        bin_size: Bin width in nm
        range_nm: (min, max) range for histogram
        normalize: If True, normalize to probability density
        
    Returns:
        Dictionary with histogram data
    """
    data = np.asarray(data)
    data = data[np.isfinite(data)]
    
    if bin_edges is not None:
        bins = bin_edges
    else:
        bins = np.arange(range_nm[0], range_nm[1] + bin_size, bin_size)
    
    counts, edges = np.histogram(data, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2
    
    if normalize:
        # Convert to probability density
        total = np.sum(counts)
        bin_widths = np.diff(edges)
        density = counts / (total * bin_widths) if total > 0 else counts
    else:
        density = counts
    
    return {
        'bin_centers': centers,
        'bin_edges': edges,
        'counts': counts,
        'density': density,
        'bin_size': float(np.median(np.diff(edges))),
        'total_counts': int(np.sum(counts)),
        'n_bins': len(counts)
    }


def compare_distributions(
    data1: np.ndarray,
    data2: np.ndarray,
    test: str = 'ks'
) -> Dict[str, Any]:
    """
    Statistical comparison of two size distributions.
    
    Args:
        data1, data2: Arrays to compare
        test: Statistical test to use:
              'ks': Kolmogorov-Smirnov
              'mw': Mann-Whitney U
              'ttest': Welch's t-test
              
    Returns:
        Dictionary with test results
    """
    data1 = np.asarray(data1)[np.isfinite(data1)]
    data2 = np.asarray(data2)[np.isfinite(data2)]
    
    results = {
        'n1': len(data1),
        'n2': len(data2),
        'mean1': float(np.mean(data1)),
        'mean2': float(np.mean(data2)),
        'median1': float(np.median(data1)),
        'median2': float(np.median(data2)),
    }
    
    if test == 'ks':
        ks_result = stats.ks_2samp(data1, data2)
        results['test'] = 'Kolmogorov-Smirnov'
        results['statistic'] = float(cast(float, ks_result[0]))  # statistic
        results['p_value'] = float(cast(float, ks_result[1]))  # pvalue
        
    elif test == 'mw':
        mw_result = stats.mannwhitneyu(data1, data2, alternative='two-sided')
        results['test'] = 'Mann-Whitney U'
        results['statistic'] = float(cast(float, mw_result[0]))  # statistic
        results['p_value'] = float(cast(float, mw_result[1]))  # pvalue
        
    elif test == 'ttest':
        tt_result = stats.ttest_ind(data1, data2, equal_var=False)
        results['test'] = "Welch's t-test"
        results['statistic'] = float(cast(float, tt_result[0]))  # statistic
        results['p_value'] = float(cast(float, tt_result[1]))  # pvalue
    
    results['significantly_different'] = results['p_value'] < 0.05
    results['effect_size'] = abs(results['mean1'] - results['mean2']) / \
                            np.sqrt((np.var(data1) + np.var(data2)) / 2)  # Cohen's d
    
    return results
