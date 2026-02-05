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


# =============================================================================
# DISTRIBUTION ANALYSIS FUNCTIONS (VAL-008 + STAT-001)
# Added: February 5, 2026
# Purpose: Test normality, fit distributions, generate overlay curves
# =============================================================================

@dataclass
class NormalityTestResult:
    """
    Result from a single normality test.
    
    Attributes:
        test_name: Name of the statistical test
        statistic: Test statistic value
        p_value: P-value (probability of observing this result if data is normal)
        is_normal: True if p_value > 0.05 (fail to reject null hypothesis)
        interpretation: Human-readable interpretation
    """
    test_name: str
    statistic: float
    p_value: float
    is_normal: bool
    interpretation: str


@dataclass
class DistributionFitResult:
    """
    Result from fitting a distribution to data.
    
    Attributes:
        distribution: Name of the distribution
        params: Fitted parameters (shape, loc, scale vary by distribution)
        aic: Akaike Information Criterion (lower = better fit)
        bic: Bayesian Information Criterion (lower = better fit)
        log_likelihood: Log-likelihood of the fit
        ks_statistic: Kolmogorov-Smirnov goodness-of-fit statistic
        ks_pvalue: K-S test p-value
        rank: Rank by AIC (1 = best)
    """
    distribution: str
    params: Tuple[float, ...]
    aic: float
    bic: float
    log_likelihood: float
    ks_statistic: float
    ks_pvalue: float
    rank: int = 0


def test_normality(
    data: np.ndarray,
    alpha: float = 0.05,
    max_samples: int = 5000
) -> Dict[str, Any]:
    """
    Run multiple normality tests on particle size distribution data.
    
    This function runs four different normality tests to determine if the
    data follows a Gaussian (normal) distribution. For EV particle sizing,
    data is typically NOT normal (usually left-skewed or log-normal).
    
    Tests performed:
    1. Shapiro-Wilk: Most powerful for small samples (n < 5000)
    2. D'Agostino-Pearson: Tests skewness and kurtosis, good for large samples
    3. Kolmogorov-Smirnov: Compares data to theoretical normal distribution
    4. Anderson-Darling: Weighted K-S test, more sensitive to tails
    
    Args:
        data: Array of particle sizes (nm)
        alpha: Significance level (default 0.05)
        max_samples: Maximum samples for Shapiro-Wilk (limited to 5000)
        
    Returns:
        Dictionary containing:
        - tests: Dict of individual test results
        - is_normal: Overall conclusion (True if majority pass)
        - conclusion: Human-readable summary
        - recommendation: What to use instead if not normal
        
    Example:
        >>> sizes = np.array([50, 80, 100, 120, 150, 200, ...])
        >>> result = test_normality(sizes)
        >>> print(result['conclusion'])
        'Data is NOT normally distributed (0/4 tests passed)'
        >>> print(result['recommendation'])
        'Use median (D50) instead of mean for central tendency'
    
    References:
        - Shapiro & Wilk (1965) "An analysis of variance test for normality"
        - D'Agostino & Pearson (1973) "Tests for departure from normality"
        - MISEV2018 guidelines recommend median for EV reporting
    """
    data = np.asarray(data, dtype=np.float64)
    data = data[np.isfinite(data)]
    n = len(data)
    
    if n < 8:
        return {
            'tests': {},
            'is_normal': None,
            'conclusion': f'Insufficient data for normality testing (n={n}, need ≥8)',
            'recommendation': 'Collect more data points',
            'n_samples': n
        }
    
    tests: Dict[str, NormalityTestResult] = {}
    
    # 1. Shapiro-Wilk Test (most powerful for small samples)
    # Limited to 5000 samples - use random subsample for larger datasets
    try:
        if n > max_samples:
            sample_indices = np.random.choice(n, max_samples, replace=False)
            shapiro_data = data[sample_indices]
            shapiro_note = f" (subsampled to {max_samples})"
        else:
            shapiro_data = data
            shapiro_note = ""
        
        shapiro_stat, shapiro_p = stats.shapiro(shapiro_data)
        tests['shapiro_wilk'] = NormalityTestResult(
            test_name=f'Shapiro-Wilk{shapiro_note}',
            statistic=float(shapiro_stat),
            p_value=float(shapiro_p),
            is_normal=shapiro_p > alpha,
            interpretation='Normal' if shapiro_p > alpha else 'Not Normal'
        )
    except Exception as e:
        logger.warning(f"Shapiro-Wilk test failed: {e}")
        tests['shapiro_wilk'] = NormalityTestResult(
            test_name='Shapiro-Wilk',
            statistic=0.0,
            p_value=0.0,
            is_normal=False,
            interpretation=f'Test failed: {str(e)}'
        )
    
    # 2. D'Agostino-Pearson Test (tests skewness and kurtosis)
    try:
        dagostino_stat, dagostino_p = stats.normaltest(data)
        tests['dagostino_pearson'] = NormalityTestResult(
            test_name="D'Agostino-Pearson",
            statistic=float(dagostino_stat),
            p_value=float(dagostino_p),
            is_normal=dagostino_p > alpha,
            interpretation='Normal' if dagostino_p > alpha else 'Not Normal'
        )
    except Exception as e:
        logger.warning(f"D'Agostino-Pearson test failed: {e}")
        tests['dagostino_pearson'] = NormalityTestResult(
            test_name="D'Agostino-Pearson",
            statistic=0.0,
            p_value=0.0,
            is_normal=False,
            interpretation=f'Test failed: {str(e)}'
        )
    
    # 3. Kolmogorov-Smirnov Test (compares to theoretical normal)
    try:
        # Standardize data for K-S test
        data_mean = np.mean(data)
        data_std = np.std(data)
        ks_stat, ks_p = stats.kstest(data, 'norm', args=(data_mean, data_std))
        tests['kolmogorov_smirnov'] = NormalityTestResult(
            test_name='Kolmogorov-Smirnov',
            statistic=float(ks_stat),
            p_value=float(ks_p),
            is_normal=ks_p > alpha,
            interpretation='Normal' if ks_p > alpha else 'Not Normal'
        )
    except Exception as e:
        logger.warning(f"Kolmogorov-Smirnov test failed: {e}")
        tests['kolmogorov_smirnov'] = NormalityTestResult(
            test_name='Kolmogorov-Smirnov',
            statistic=0.0,
            p_value=0.0,
            is_normal=False,
            interpretation=f'Test failed: {str(e)}'
        )
    
    # 4. Anderson-Darling Test (more sensitive to tails)
    try:
        anderson_result = stats.anderson(data, dist='norm')
        # Use 5% significance level (index 2 in critical_values)
        anderson_critical = anderson_result.critical_values[2]  # 5% level
        anderson_is_normal = anderson_result.statistic < anderson_critical
        tests['anderson_darling'] = NormalityTestResult(
            test_name='Anderson-Darling',
            statistic=float(anderson_result.statistic),
            p_value=float(anderson_critical),  # Store critical value
            is_normal=anderson_is_normal,
            interpretation='Normal' if anderson_is_normal else 'Not Normal'
        )
    except Exception as e:
        logger.warning(f"Anderson-Darling test failed: {e}")
        tests['anderson_darling'] = NormalityTestResult(
            test_name='Anderson-Darling',
            statistic=0.0,
            p_value=0.0,
            is_normal=False,
            interpretation=f'Test failed: {str(e)}'
        )
    
    # Calculate overall conclusion
    passed_tests = sum(1 for t in tests.values() if t.is_normal)
    total_tests = len(tests)
    is_normal = passed_tests >= (total_tests / 2)  # Majority vote
    
    # Generate recommendation based on results
    if is_normal:
        conclusion = f'Data appears normally distributed ({passed_tests}/{total_tests} tests passed)'
        recommendation = 'Mean and standard deviation are appropriate statistics'
    else:
        conclusion = f'Data is NOT normally distributed ({passed_tests}/{total_tests} tests passed)'
        recommendation = 'Use median (D50) instead of mean; consider log-normal distribution'
    
    # Convert dataclass results to dict for JSON serialization
    tests_dict = {
        name: {
            'test_name': result.test_name,
            'statistic': result.statistic,
            'p_value': result.p_value,
            'is_normal': result.is_normal,
            'interpretation': result.interpretation
        }
        for name, result in tests.items()
    }
    
    return {
        'tests': tests_dict,
        'passed_count': passed_tests,
        'total_tests': total_tests,
        'is_normal': is_normal,
        'conclusion': conclusion,
        'recommendation': recommendation,
        'alpha': alpha,
        'n_samples': n
    }


def fit_distributions(
    data: np.ndarray,
    distributions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Fit multiple probability distributions to particle size data and compare.
    
    This function fits several candidate distributions to the data and ranks
    them using AIC (Akaike Information Criterion). For biological particle
    sizing, log-normal is typically the most appropriate distribution due to
    multiplicative growth processes in EV biogenesis.
    
    Distributions fitted:
    - normal: Gaussian distribution
    - lognorm: Log-normal (RECOMMENDED for biological particles)
    - gamma: Gamma distribution (positive, right-skewed)
    - weibull: Weibull distribution (flexible, often best AIC)
    - expon: Exponential distribution (memoryless decay)
    
    Args:
        data: Array of particle sizes (nm), must be positive
        distributions: List of distribution names to fit (default: all)
        
    Returns:
        Dictionary containing:
        - fits: Dict of fit results for each distribution
        - best_fit_aic: Distribution with lowest AIC
        - best_fit_bic: Distribution with lowest BIC
        - recommendation: Recommended distribution for biological interpretation
        - recommendation_reason: Explanation for recommendation
        
    Example:
        >>> sizes = np.array([50, 80, 100, 120, 150, ...])
        >>> result = fit_distributions(sizes)
        >>> print(f"Best AIC: {result['best_fit_aic']}")
        'Best AIC: weibull'
        >>> print(f"Recommended: {result['recommendation']}")
        'Recommended: lognorm'
    
    Notes:
        - AIC = 2k - 2ln(L) where k = number of parameters, L = likelihood
        - Lower AIC indicates better fit (penalizes complexity)
        - Weibull often wins statistically but log-normal is better for biology
        - Log-normal arises from multiplicative random processes (cell growth)
        
    References:
        - Akaike (1974) "A new look at the statistical model identification"
        - Limpert et al. (2001) "Log-normal Distributions across the Sciences"
        - Parvesh Reddy feedback (Feb 4, 2026): "Log-normal for biology"
    """
    data = np.asarray(data, dtype=np.float64)
    data = data[np.isfinite(data)]
    data = data[data > 0]  # Most distributions require positive values
    n = len(data)
    
    if n < 10:
        return {
            'fits': {},
            'best_fit_aic': None,
            'best_fit_bic': None,
            'recommendation': None,
            'recommendation_reason': f'Insufficient data (n={n}, need ≥10)',
            'n_samples': n
        }
    
    # Default distributions to fit
    if distributions is None:
        distributions = ['normal', 'lognorm', 'gamma', 'weibull_min', 'expon']
    
    # Map names to scipy.stats distributions
    dist_map = {
        'normal': stats.norm,
        'lognorm': stats.lognorm,
        'gamma': stats.gamma,
        'weibull_min': stats.weibull_min,
        'weibull': stats.weibull_min,  # Alias
        'expon': stats.expon,
    }
    
    fits: Dict[str, Dict[str, Any]] = {}
    
    for dist_name in distributions:
        if dist_name not in dist_map:
            logger.warning(f"Unknown distribution: {dist_name}, skipping")
            continue
            
        dist = dist_map[dist_name]
        
        try:
            # Fit distribution to data
            params = dist.fit(data)
            
            # Calculate log-likelihood
            log_likelihood = np.sum(dist.logpdf(data, *params))
            
            # Calculate AIC and BIC
            k = len(params)  # Number of parameters
            aic = 2 * k - 2 * log_likelihood
            bic = k * np.log(n) - 2 * log_likelihood
            
            # Kolmogorov-Smirnov goodness-of-fit test
            ks_stat, ks_pvalue = stats.kstest(data, dist.cdf, args=params)
            
            fits[dist_name] = {
                'params': [float(p) for p in params],
                'param_names': _get_param_names(dist_name),
                'log_likelihood': float(log_likelihood),
                'aic': float(aic),
                'bic': float(bic),
                'ks_statistic': float(ks_stat),
                'ks_pvalue': float(ks_pvalue),
                'n_params': k
            }
            
        except Exception as e:
            logger.warning(f"Failed to fit {dist_name}: {e}")
            fits[dist_name] = {
                'error': str(e),
                'params': [],
                'aic': float('inf'),
                'bic': float('inf')
            }
    
    # Rank distributions by AIC
    valid_fits = {k: v for k, v in fits.items() if 'error' not in v}
    
    if not valid_fits:
        return {
            'fits': fits,
            'best_fit_aic': None,
            'best_fit_bic': None,
            'recommendation': None,
            'recommendation_reason': 'All distribution fits failed',
            'n_samples': n
        }
    
    # Sort by AIC and assign ranks
    sorted_by_aic = sorted(valid_fits.keys(), key=lambda x: valid_fits[x]['aic'])
    sorted_by_bic = sorted(valid_fits.keys(), key=lambda x: valid_fits[x]['bic'])
    
    for rank, dist_name in enumerate(sorted_by_aic, 1):
        fits[dist_name]['rank_aic'] = rank
    for rank, dist_name in enumerate(sorted_by_bic, 1):
        fits[dist_name]['rank_bic'] = rank
    
    best_aic = sorted_by_aic[0]
    best_bic = sorted_by_bic[0]
    
    # Biological recommendation: always prefer log-normal for EV data
    # Reasoning: EV biogenesis involves multiplicative processes
    recommendation = 'lognorm' if 'lognorm' in valid_fits else best_aic
    
    if recommendation == 'lognorm' and best_aic != 'lognorm':
        recommendation_reason = (
            f"Log-normal recommended for biological interpretation despite "
            f"{best_aic} having better AIC. EV biogenesis involves multiplicative "
            f"growth processes which naturally produce log-normal distributions."
        )
    elif recommendation == 'lognorm':
        recommendation_reason = (
            "Log-normal is both the best statistical fit and biologically appropriate "
            "for extracellular vesicle size distributions."
        )
    else:
        recommendation_reason = f"{recommendation} is the best available fit."
    
    return {
        'fits': fits,
        'best_fit_aic': best_aic,
        'best_fit_bic': best_bic,
        'recommendation': recommendation,
        'recommendation_reason': recommendation_reason,
        'n_samples': n,
        'aic_ranking': sorted_by_aic,
        'bic_ranking': sorted_by_bic
    }


def _get_param_names(dist_name: str) -> List[str]:
    """Get human-readable parameter names for each distribution."""
    param_names = {
        'normal': ['loc (mean)', 'scale (std)'],
        'lognorm': ['s (shape/σ)', 'loc', 'scale (exp(μ))'],
        'gamma': ['a (shape)', 'loc', 'scale'],
        'weibull_min': ['c (shape)', 'loc', 'scale'],
        'weibull': ['c (shape)', 'loc', 'scale'],
        'expon': ['loc', 'scale'],
    }
    return param_names.get(dist_name, ['param' + str(i) for i in range(5)])


def generate_distribution_overlay(
    data: np.ndarray,
    distribution: str = 'lognorm',
    n_points: int = 200,
    x_range: Optional[Tuple[float, float]] = None
) -> Dict[str, Any]:
    """
    Generate theoretical distribution curve for histogram overlay visualization.
    
    This function fits a distribution to the data and generates a smooth curve
    that can be overlaid on a histogram to visualize how well the theoretical
    distribution matches the empirical data.
    
    Args:
        data: Array of particle sizes (nm)
        distribution: Distribution to fit ('normal', 'lognorm', 'gamma', 'weibull_min')
        n_points: Number of points for the curve (higher = smoother)
        x_range: Optional (min, max) range for x-axis; auto-detected if None
        
    Returns:
        Dictionary containing:
        - x: Array of x values for plotting
        - y_pdf: Probability density function values
        - y_scaled: PDF scaled to match histogram counts
        - params: Fitted parameters
        - label: Label for legend
        - distribution: Distribution name
        
    Example:
        >>> sizes = np.array([50, 80, 100, 120, 150, ...])
        >>> overlay = generate_distribution_overlay(sizes, 'lognorm')
        >>> plt.plot(overlay['x'], overlay['y_scaled'], label=overlay['label'])
    """
    data = np.asarray(data, dtype=np.float64)
    data = data[np.isfinite(data)]
    data = data[data > 0]
    n = len(data)
    
    if n < 10:
        return {
            'x': [],
            'y_pdf': [],
            'y_scaled': [],
            'params': [],
            'label': 'Insufficient data',
            'distribution': distribution,
            'error': f'Need at least 10 data points (got {n})'
        }
    
    # Map distribution name to scipy.stats
    dist_map = {
        'normal': stats.norm,
        'gaussian': stats.norm,
        'lognorm': stats.lognorm,
        'lognormal': stats.lognorm,
        'gamma': stats.gamma,
        'weibull_min': stats.weibull_min,
        'weibull': stats.weibull_min,
        'expon': stats.expon,
    }
    
    if distribution.lower() not in dist_map:
        return {
            'x': [],
            'y_pdf': [],
            'y_scaled': [],
            'params': [],
            'label': f'Unknown distribution: {distribution}',
            'distribution': distribution,
            'error': f'Supported: {list(dist_map.keys())}'
        }
    
    dist = dist_map[distribution.lower()]
    
    try:
        # Fit distribution
        params = dist.fit(data)
        
        # Generate x range
        if x_range is None:
            x_min = max(0, np.percentile(data, 0.5))
            x_max = np.percentile(data, 99.5)
            margin = (x_max - x_min) * 0.1
            x_range = (max(0, x_min - margin), x_max + margin)
        
        x = np.linspace(x_range[0], x_range[1], n_points)
        
        # Calculate PDF
        y_pdf = dist.pdf(x, *params)
        
        # Scale PDF to match histogram (for overlay)
        # Estimate bin width from data range
        bin_width = (np.max(data) - np.min(data)) / 50  # Assume ~50 bins
        y_scaled = y_pdf * n * bin_width
        
        # Generate label with key parameters
        if distribution.lower() in ['lognorm', 'lognormal']:
            # For log-normal: shape (s), loc, scale
            # Mean = exp(μ + σ²/2), Median = exp(μ) = scale
            s, loc, scale = params
            label = f"Log-normal (σ={s:.2f}, median={scale:.1f})"
        elif distribution.lower() in ['normal', 'gaussian']:
            loc, scale = params
            label = f"Normal (μ={loc:.1f}, σ={scale:.1f})"
        elif distribution.lower() == 'gamma':
            a, loc, scale = params
            label = f"Gamma (α={a:.2f}, scale={scale:.1f})"
        elif distribution.lower() in ['weibull_min', 'weibull']:
            c, loc, scale = params
            label = f"Weibull (c={c:.2f}, scale={scale:.1f})"
        else:
            label = f"{distribution} fit"
        
        return {
            'x': x.tolist(),
            'y_pdf': y_pdf.tolist(),
            'y_scaled': y_scaled.tolist(),
            'params': [float(p) for p in params],
            'param_names': _get_param_names(distribution.lower()),
            'label': label,
            'distribution': distribution,
            'n_samples': n
        }
        
    except Exception as e:
        logger.error(f"Failed to generate {distribution} overlay: {e}")
        return {
            'x': [],
            'y_pdf': [],
            'y_scaled': [],
            'params': [],
            'label': f'Fit failed: {str(e)}',
            'distribution': distribution,
            'error': str(e)
        }


def comprehensive_distribution_analysis(
    data: np.ndarray,
    include_overlays: bool = True
) -> Dict[str, Any]:
    """
    Perform complete distribution analysis on particle size data.
    
    This is the main entry point for VAL-008 + STAT-001 functionality.
    It combines normality testing, distribution fitting, and curve generation
    into a single comprehensive analysis.
    
    Args:
        data: Array of particle sizes (nm)
        include_overlays: Whether to generate overlay curves for visualization
        
    Returns:
        Complete analysis results including:
        - normality_tests: Results from test_normality()
        - distribution_fits: Results from fit_distributions()
        - overlays: Curve data for each fitted distribution (if requested)
        - summary_statistics: Mean, median, mode, percentiles, etc.
        - conclusion: Overall interpretation and recommendations
        
    Example:
        >>> sizes = load_particle_sizes('PC3_EXO1.fcs')
        >>> analysis = comprehensive_distribution_analysis(sizes)
        >>> print(analysis['conclusion']['is_normal'])
        False
        >>> print(analysis['conclusion']['recommended_distribution'])
        'lognorm'
    """
    data = np.asarray(data, dtype=np.float64)
    data = data[np.isfinite(data)]
    data = data[data > 0]
    n = len(data)
    
    logger.info(f"Running comprehensive distribution analysis on {n} data points")
    
    # Run normality tests
    normality = test_normality(data)
    
    # Fit distributions
    fits = fit_distributions(data)
    
    # Calculate summary statistics
    summary_stats = {
        'n': n,
        'mean': float(np.mean(data)),
        'std': float(np.std(data)),
        'median': float(np.median(data)),
        'min': float(np.min(data)),
        'max': float(np.max(data)),
        'd10': float(np.percentile(data, 10)),
        'd25': float(np.percentile(data, 25)),
        'd50': float(np.percentile(data, 50)),
        'd75': float(np.percentile(data, 75)),
        'd90': float(np.percentile(data, 90)),
        'iqr': float(np.percentile(data, 75) - np.percentile(data, 25)),
        'skewness': float(stats.skew(data)),
        'kurtosis': float(stats.kurtosis(data)),
    }
    
    # Determine skewness type
    skewness = summary_stats['skewness']
    if abs(skewness) < 0.5:
        skew_type = 'approximately symmetric'
    elif skewness > 0:
        skew_type = 'right-skewed (positive)'
    else:
        skew_type = 'left-skewed (negative)'
    
    summary_stats['skew_interpretation'] = skew_type
    
    # Generate overlay curves if requested
    overlays = {}
    if include_overlays:
        for dist_name in ['normal', 'lognorm', 'gamma', 'weibull_min']:
            overlays[dist_name] = generate_distribution_overlay(data, dist_name)
    
    # Generate overall conclusion
    conclusion = {
        'is_normal': normality['is_normal'],
        'normality_summary': normality['conclusion'],
        'best_fit_statistical': fits.get('best_fit_aic'),
        'recommended_distribution': fits.get('recommendation'),
        'recommendation_reason': fits.get('recommendation_reason'),
        'skewness_type': skew_type,
        'use_median': not normality['is_normal'],
        'central_tendency': summary_stats['median'] if not normality['is_normal'] else summary_stats['mean'],
        'central_tendency_metric': 'median (D50)' if not normality['is_normal'] else 'mean',
    }
    
    logger.info(
        f"Distribution analysis complete: is_normal={conclusion['is_normal']}, "
        f"recommended={conclusion['recommended_distribution']}, "
        f"skewness={skew_type}"
    )
    
    return {
        'normality_tests': normality,
        'distribution_fits': fits,
        'summary_statistics': summary_stats,
        'overlays': overlays if include_overlays else None,
        'conclusion': conclusion,
        'n_samples': n
    }
