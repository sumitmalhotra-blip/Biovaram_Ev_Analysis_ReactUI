"""
Population Shift Detection Service
==================================

CRMIT-004: Detect significant population shifts between samples or time points.

This module provides statistical methods to detect when particle populations
have significantly shifted in their characteristics between measurements.

Statistical Tests:
- Kolmogorov-Smirnov (KS) test: Compares full distributions
- Earth Mover's Distance (EMD/Wasserstein): Quantifies distribution difference
- T-test for means: Detects shifts in central tendency
- Levene's test: Detects changes in variance/spread
- Chi-square test: For categorical/binned data

Use Cases:
- Compare before/after treatment samples
- Detect drift over time in control samples
- Quality control: flag unexpected population changes
- Compare samples from different batches

Author: CRMIT Backend Team
Date: January 1, 2026
"""

from typing import List, Dict, Optional, Tuple, Any, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from loguru import logger

# Type stubs for conditional imports
stats: Any = None
wasserstein_distance: Any = None

try:
    from scipy import stats  # type: ignore[import-not-found]
    from scipy.stats import wasserstein_distance  # type: ignore[import-not-found]
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    stats = None
    wasserstein_distance = None
    logger.warning("scipy not installed - population shift detection will be limited")


class ShiftSeverity(str, Enum):
    """Severity classification for detected population shifts."""
    NONE = "none"           # No significant shift detected
    MINOR = "minor"         # Small but statistically significant shift
    MODERATE = "moderate"   # Noticeable shift, warrants attention
    MAJOR = "major"         # Large shift, requires investigation
    CRITICAL = "critical"   # Very large shift, likely different populations


class ComparisonMode(str, Enum):
    """Mode for population comparison."""
    PAIRWISE = "pairwise"       # Compare two specific samples
    BASELINE = "baseline"       # Compare multiple samples to a baseline
    TEMPORAL = "temporal"       # Compare sequential samples over time
    ALL_PAIRS = "all_pairs"     # Compare all combinations


@dataclass
class ShiftTestResult:
    """Result from a single statistical test for population shift."""
    test_name: str
    statistic: float
    p_value: float
    significant: bool
    effect_size: Optional[float] = None
    severity: ShiftSeverity = ShiftSeverity.NONE
    interpretation: str = ""
    confidence_interval: Optional[Tuple[float, float]] = None


@dataclass
class PopulationMetrics:
    """Descriptive metrics for a population/sample."""
    sample_id: str
    sample_name: str
    n_events: int
    mean: float
    median: float
    std: float
    iqr: float  # Interquartile range
    skewness: float
    kurtosis: float
    percentiles: Dict[int, float] = field(default_factory=dict)  # e.g., {10: 45.2, 25: 52.1, ...}


@dataclass
class PopulationShiftResult:
    """Complete result for population shift analysis between two samples."""
    sample_a: PopulationMetrics
    sample_b: PopulationMetrics
    metric_name: str
    tests: List[ShiftTestResult]
    overall_shift_detected: bool
    overall_severity: ShiftSeverity
    summary: str
    recommendations: List[str]


@dataclass
class MultiSampleShiftResult:
    """Result for multi-sample population shift analysis."""
    mode: ComparisonMode
    baseline_sample: Optional[str]
    comparisons: List[PopulationShiftResult]
    global_summary: str
    any_significant_shift: bool
    max_severity: ShiftSeverity


class PopulationShiftDetector:
    """
    Detects statistically significant shifts in particle populations.
    
    Uses multiple statistical tests to provide robust detection of
    population changes across different aspects (location, spread, shape).
    """
    
    # Effect size thresholds for severity classification
    SEVERITY_THRESHOLDS = {
        "ks_statistic": {
            "minor": 0.1,
            "moderate": 0.2,
            "major": 0.35,
            "critical": 0.5
        },
        "emd_normalized": {  # EMD normalized by range
            "minor": 0.05,
            "moderate": 0.1,
            "major": 0.2,
            "critical": 0.35
        },
        "cohens_d": {  # Cohen's d for mean shift
            "minor": 0.2,
            "moderate": 0.5,
            "major": 0.8,
            "critical": 1.2
        },
        "variance_ratio": {  # Ratio of variances
            "minor": 1.5,
            "moderate": 2.0,
            "major": 3.0,
            "critical": 5.0
        }
    }
    
    def __init__(self, alpha: float = 0.05):
        """
        Initialize the detector.
        
        Args:
            alpha: Significance level for statistical tests (default 0.05)
        """
        self.alpha = alpha
        
        if not SCIPY_AVAILABLE:
            logger.warning("scipy not available - limited functionality")
    
    def calculate_metrics(
        self, 
        data: np.ndarray, 
        sample_id: str,
        sample_name: str
    ) -> PopulationMetrics:
        """
        Calculate descriptive metrics for a population.
        
        Args:
            data: Array of values (e.g., particle sizes)
            sample_id: Sample identifier
            sample_name: Human-readable sample name
            
        Returns:
            PopulationMetrics with comprehensive statistics
        """
        data = np.asarray(data)
        data = data[~np.isnan(data)]  # Remove NaN values
        
        if len(data) == 0:
            raise ValueError(f"No valid data for sample {sample_id}")
        
        # Calculate percentiles
        percentiles = {
            p: float(np.percentile(data, p)) 
            for p in [5, 10, 25, 50, 75, 90, 95]
        }
        
        # Calculate IQR
        iqr = percentiles[75] - percentiles[25]
        
        # Calculate skewness and kurtosis
        if SCIPY_AVAILABLE and stats is not None and len(data) >= 3:
            skewness = float(stats.skew(data))  # type: ignore[union-attr]
            kurtosis = float(stats.kurtosis(data))  # type: ignore[union-attr]
        else:
            skewness = 0.0
            kurtosis = 0.0
        
        return PopulationMetrics(
            sample_id=sample_id,
            sample_name=sample_name,
            n_events=len(data),
            mean=float(np.mean(data)),
            median=float(np.median(data)),
            std=float(np.std(data, ddof=1)) if len(data) > 1 else 0.0,
            iqr=iqr,
            skewness=skewness,
            kurtosis=kurtosis,
            percentiles=percentiles
        )
    
    def _classify_severity(
        self, 
        effect_size: float, 
        threshold_key: str
    ) -> ShiftSeverity:
        """Classify severity based on effect size and thresholds."""
        thresholds = self.SEVERITY_THRESHOLDS.get(threshold_key, {})
        
        abs_effect = abs(effect_size)
        
        if abs_effect >= thresholds.get("critical", float('inf')):
            return ShiftSeverity.CRITICAL
        elif abs_effect >= thresholds.get("major", float('inf')):
            return ShiftSeverity.MAJOR
        elif abs_effect >= thresholds.get("moderate", float('inf')):
            return ShiftSeverity.MODERATE
        elif abs_effect >= thresholds.get("minor", float('inf')):
            return ShiftSeverity.MINOR
        else:
            return ShiftSeverity.NONE
    
    def ks_test(
        self, 
        data_a: np.ndarray, 
        data_b: np.ndarray
    ) -> ShiftTestResult:
        """
        Kolmogorov-Smirnov test for distribution shift.
        
        Tests whether two samples come from the same distribution.
        Sensitive to differences in location, spread, and shape.
        
        Args:
            data_a: First sample data
            data_b: Second sample data
            
        Returns:
            ShiftTestResult with KS test results
        """
        if not SCIPY_AVAILABLE:
            return ShiftTestResult(
                test_name="Kolmogorov-Smirnov Test",
                statistic=0.0,
                p_value=1.0,
                significant=False,
                interpretation="scipy not available"
            )
        
        try:
            result = stats.ks_2samp(data_a, data_b)  # type: ignore[union-attr]
            statistic = float(getattr(result, 'statistic', 0.0))
            p_value = float(getattr(result, 'pvalue', 1.0))
            significant = p_value < self.alpha
            
            severity = self._classify_severity(statistic, "ks_statistic")
            
            if significant:
                interpretation = (
                    f"Significant distribution difference detected (D={statistic:.3f}, p={p_value:.4f}). "
                    f"The populations have different shapes or locations."
                )
            else:
                interpretation = (
                    f"No significant distribution difference (D={statistic:.3f}, p={p_value:.4f}). "
                    f"Populations appear to come from similar distributions."
                )
            
            return ShiftTestResult(
                test_name="Kolmogorov-Smirnov Test",
                statistic=statistic,
                p_value=p_value,
                significant=significant,
                effect_size=statistic,  # KS statistic is itself an effect size
                severity=severity if significant else ShiftSeverity.NONE,
                interpretation=interpretation
            )
            
        except Exception as e:
            logger.error(f"KS test failed: {e}")
            return ShiftTestResult(
                test_name="Kolmogorov-Smirnov Test",
                statistic=0.0,
                p_value=1.0,
                significant=False,
                interpretation=f"Test failed: {str(e)}"
            )
    
    def earth_movers_distance(
        self, 
        data_a: np.ndarray, 
        data_b: np.ndarray
    ) -> ShiftTestResult:
        """
        Earth Mover's Distance (Wasserstein distance) for distribution shift.
        
        Quantifies the "work" needed to transform one distribution into another.
        More interpretable than KS statistic for practical differences.
        
        Args:
            data_a: First sample data
            data_b: Second sample data
            
        Returns:
            ShiftTestResult with EMD results
        """
        if not SCIPY_AVAILABLE:
            return ShiftTestResult(
                test_name="Earth Mover's Distance",
                statistic=0.0,
                p_value=1.0,
                significant=False,
                interpretation="scipy not available"
            )
        
        try:
            # Calculate EMD (Wasserstein-1 distance)
            if not SCIPY_AVAILABLE or wasserstein_distance is None:
                raise RuntimeError("scipy not available")
            emd = wasserstein_distance(data_a, data_b)  # type: ignore[misc]
            
            # Normalize by the range for interpretability
            combined_range = max(np.max(data_a), np.max(data_b)) - min(np.min(data_a), np.min(data_b))
            normalized_emd = emd / combined_range if combined_range > 0 else 0
            
            # Bootstrap for significance testing
            n_bootstrap = 1000
            bootstrap_emds = []
            combined = np.concatenate([data_a, data_b])
            n_a = len(data_a)
            
            for _ in range(n_bootstrap):
                np.random.shuffle(combined)
                boot_emd = wasserstein_distance(combined[:n_a], combined[n_a:])  # type: ignore[misc]
                bootstrap_emds.append(boot_emd)
            
            # Calculate p-value from bootstrap distribution
            p_value = float(np.mean(np.array(bootstrap_emds) >= emd))
            significant = p_value < self.alpha
            
            severity = self._classify_severity(normalized_emd, "emd_normalized")
            
            # Convert EMD to interpretable units (same as input data)
            interpretation = (
                f"EMD = {emd:.2f} (normalized: {normalized_emd:.3f}). "
                f"This represents the average 'distance' particles would need to move "
                f"to transform distribution A into B."
            )
            if significant:
                interpretation += f" Significant shift detected (p={p_value:.4f})."
            else:
                interpretation += f" No significant shift (p={p_value:.4f})."
            
            return ShiftTestResult(
                test_name="Earth Mover's Distance",
                statistic=emd,
                p_value=p_value,
                significant=significant,
                effect_size=normalized_emd,
                severity=severity if significant else ShiftSeverity.NONE,
                interpretation=interpretation
            )
            
        except Exception as e:
            logger.error(f"EMD calculation failed: {e}")
            return ShiftTestResult(
                test_name="Earth Mover's Distance",
                statistic=0.0,
                p_value=1.0,
                significant=False,
                interpretation=f"Test failed: {str(e)}"
            )
    
    def mean_shift_test(
        self, 
        data_a: np.ndarray, 
        data_b: np.ndarray
    ) -> ShiftTestResult:
        """
        Test for shift in population mean using Welch's t-test.
        
        Detects changes in the central tendency of the population.
        
        Args:
            data_a: First sample data
            data_b: Second sample data
            
        Returns:
            ShiftTestResult with t-test results
        """
        if not SCIPY_AVAILABLE:
            return ShiftTestResult(
                test_name="Mean Shift Test (Welch's t)",
                statistic=0.0,
                p_value=1.0,
                significant=False,
                interpretation="scipy not available"
            )
        
        try:
            result = stats.ttest_ind(data_a, data_b, equal_var=False)  # type: ignore[union-attr]
            statistic = float(getattr(result, 'statistic', 0.0))
            p_value = float(getattr(result, 'pvalue', 1.0))
            significant = p_value < self.alpha
            
            # Calculate Cohen's d
            mean_a, mean_b = np.mean(data_a), np.mean(data_b)
            std_a, std_b = np.std(data_a, ddof=1), np.std(data_b, ddof=1)
            pooled_std = np.sqrt((std_a**2 + std_b**2) / 2)
            cohens_d = (mean_a - mean_b) / pooled_std if pooled_std > 0 else 0
            
            severity = self._classify_severity(cohens_d, "cohens_d")
            
            # Calculate confidence interval for mean difference
            mean_diff = mean_a - mean_b
            se_diff = np.sqrt(std_a**2/len(data_a) + std_b**2/len(data_b))
            ci_margin = stats.t.ppf(1 - self.alpha/2, min(len(data_a), len(data_b)) - 1) * se_diff  # type: ignore[union-attr]
            ci = (mean_diff - ci_margin, mean_diff + ci_margin)
            
            if significant:
                direction = "higher" if mean_a > mean_b else "lower"
                interpretation = (
                    f"Significant mean shift detected (t={statistic:.2f}, p={p_value:.4f}). "
                    f"Sample A mean ({mean_a:.2f}) is {direction} than Sample B ({mean_b:.2f}). "
                    f"Cohen's d = {cohens_d:.2f} ({self._describe_cohens_d(cohens_d)})."
                )
            else:
                interpretation = (
                    f"No significant mean shift (t={statistic:.2f}, p={p_value:.4f}). "
                    f"Means are similar: A={mean_a:.2f}, B={mean_b:.2f}."
                )
            
            return ShiftTestResult(
                test_name="Mean Shift Test (Welch's t)",
                statistic=statistic,
                p_value=p_value,
                significant=significant,
                effect_size=cohens_d,
                severity=severity if significant else ShiftSeverity.NONE,
                interpretation=interpretation,
                confidence_interval=ci
            )
            
        except Exception as e:
            logger.error(f"Mean shift test failed: {e}")
            return ShiftTestResult(
                test_name="Mean Shift Test (Welch's t)",
                statistic=0.0,
                p_value=1.0,
                significant=False,
                interpretation=f"Test failed: {str(e)}"
            )
    
    def variance_shift_test(
        self, 
        data_a: np.ndarray, 
        data_b: np.ndarray
    ) -> ShiftTestResult:
        """
        Test for shift in population variance using Levene's test.
        
        Detects changes in the spread/variability of the population.
        
        Args:
            data_a: First sample data
            data_b: Second sample data
            
        Returns:
            ShiftTestResult with Levene's test results
        """
        if not SCIPY_AVAILABLE:
            return ShiftTestResult(
                test_name="Variance Shift Test (Levene's)",
                statistic=0.0,
                p_value=1.0,
                significant=False,
                interpretation="scipy not available"
            )
        
        try:
            result = stats.levene(data_a, data_b, center='median')  # type: ignore[union-attr]
            statistic = float(result.statistic)
            p_value = float(result.pvalue)
            significant = p_value < self.alpha
            
            # Calculate variance ratio as effect size
            var_a, var_b = np.var(data_a, ddof=1), np.var(data_b, ddof=1)
            var_ratio = float(max(var_a, var_b) / min(var_a, var_b)) if min(var_a, var_b) > 0 else 1.0
            
            severity = self._classify_severity(var_ratio, "variance_ratio")
            
            if significant:
                more_variable = "A" if var_a > var_b else "B"
                interpretation = (
                    f"Significant variance shift detected (W={statistic:.2f}, p={p_value:.4f}). "
                    f"Sample {more_variable} shows greater variability. "
                    f"Variance ratio = {var_ratio:.2f}x."
                )
            else:
                interpretation = (
                    f"No significant variance shift (W={statistic:.2f}, p={p_value:.4f}). "
                    f"Variability is similar between samples."
                )
            
            return ShiftTestResult(
                test_name="Variance Shift Test (Levene's)",
                statistic=statistic,
                p_value=p_value,
                significant=significant,
                effect_size=var_ratio,
                severity=severity if significant else ShiftSeverity.NONE,
                interpretation=interpretation
            )
            
        except Exception as e:
            logger.error(f"Variance shift test failed: {e}")
            return ShiftTestResult(
                test_name="Variance Shift Test (Levene's)",
                statistic=0.0,
                p_value=1.0,
                significant=False,
                interpretation=f"Test failed: {str(e)}"
            )
    
    def _describe_cohens_d(self, d: float) -> str:
        """Get descriptive label for Cohen's d effect size."""
        abs_d = abs(d)
        if abs_d < 0.2:
            return "negligible effect"
        elif abs_d < 0.5:
            return "small effect"
        elif abs_d < 0.8:
            return "medium effect"
        elif abs_d < 1.2:
            return "large effect"
        else:
            return "very large effect"
    
    def detect_shift(
        self,
        data_a: np.ndarray,
        data_b: np.ndarray,
        sample_a_id: str,
        sample_a_name: str,
        sample_b_id: str,
        sample_b_name: str,
        metric_name: str = "particle_size",
        tests: Optional[List[str]] = None
    ) -> PopulationShiftResult:
        """
        Perform comprehensive population shift detection.
        
        Runs multiple statistical tests and provides an overall assessment.
        
        Args:
            data_a: First sample data array
            data_b: Second sample data array
            sample_a_id: ID of first sample
            sample_a_name: Display name of first sample
            sample_b_id: ID of second sample
            sample_b_name: Display name of second sample
            metric_name: Name of the metric being compared
            tests: List of tests to run (default: all)
            
        Returns:
            PopulationShiftResult with comprehensive analysis
        """
        # Default to all tests
        if tests is None:
            tests = ["ks", "emd", "mean", "variance"]
        
        # Clean data
        data_a = np.asarray(data_a)
        data_b = np.asarray(data_b)
        data_a = data_a[~np.isnan(data_a)]
        data_b = data_b[~np.isnan(data_b)]
        
        if len(data_a) < 3 or len(data_b) < 3:
            raise ValueError("Each sample must have at least 3 data points")
        
        # Calculate metrics for both samples
        metrics_a = self.calculate_metrics(data_a, sample_a_id, sample_a_name)
        metrics_b = self.calculate_metrics(data_b, sample_b_id, sample_b_name)
        
        # Run requested tests
        test_results = []
        
        if "ks" in tests:
            test_results.append(self.ks_test(data_a, data_b))
        
        if "emd" in tests:
            test_results.append(self.earth_movers_distance(data_a, data_b))
        
        if "mean" in tests:
            test_results.append(self.mean_shift_test(data_a, data_b))
        
        if "variance" in tests:
            test_results.append(self.variance_shift_test(data_a, data_b))
        
        # Determine overall shift detection
        significant_tests = [t for t in test_results if t.significant]
        any_significant = len(significant_tests) > 0
        
        # Determine overall severity (highest among significant tests)
        severities = [t.severity for t in test_results if t.significant]
        if severities:
            severity_order = [ShiftSeverity.NONE, ShiftSeverity.MINOR, 
                           ShiftSeverity.MODERATE, ShiftSeverity.MAJOR, ShiftSeverity.CRITICAL]
            overall_severity = max(severities, key=lambda s: severity_order.index(s))
        else:
            overall_severity = ShiftSeverity.NONE
        
        # Generate summary
        if any_significant:
            summary = (
                f"Population shift detected between '{sample_a_name}' and '{sample_b_name}' "
                f"for {metric_name}. {len(significant_tests)}/{len(test_results)} tests significant. "
                f"Overall severity: {overall_severity.value.upper()}."
            )
        else:
            summary = (
                f"No significant population shift detected between '{sample_a_name}' and "
                f"'{sample_b_name}' for {metric_name}. Populations appear stable."
            )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            test_results, overall_severity, metrics_a, metrics_b, metric_name
        )
        
        return PopulationShiftResult(
            sample_a=metrics_a,
            sample_b=metrics_b,
            metric_name=metric_name,
            tests=test_results,
            overall_shift_detected=any_significant,
            overall_severity=overall_severity,
            summary=summary,
            recommendations=recommendations
        )
    
    def _generate_recommendations(
        self,
        test_results: List[ShiftTestResult],
        severity: ShiftSeverity,
        metrics_a: PopulationMetrics,
        metrics_b: PopulationMetrics,
        metric_name: str
    ) -> List[str]:
        """Generate actionable recommendations based on shift analysis."""
        recommendations = []
        
        if severity == ShiftSeverity.NONE:
            recommendations.append("✅ No action required - populations are stable.")
            return recommendations
        
        # Check which aspects shifted
        mean_shift = any(t.test_name.startswith("Mean") and t.significant for t in test_results)
        variance_shift = any(t.test_name.startswith("Variance") and t.significant for t in test_results)
        distribution_shift = any(t.test_name in ["Kolmogorov-Smirnov Test", "Earth Mover's Distance"] 
                                and t.significant for t in test_results)
        
        if mean_shift:
            diff = metrics_a.mean - metrics_b.mean
            pct_change = (diff / metrics_b.mean * 100) if metrics_b.mean != 0 else 0
            recommendations.append(
                f"📊 Mean shift of {abs(diff):.2f} ({abs(pct_change):.1f}%) detected. "
                f"Investigate if this represents a real biological change or technical drift."
            )
        
        if variance_shift:
            recommendations.append(
                "📐 Variance change detected. Check for changes in sample preparation "
                "consistency or instrument stability."
            )
        
        if distribution_shift and not (mean_shift or variance_shift):
            recommendations.append(
                "📈 Distribution shape changed without clear mean/variance shift. "
                "This may indicate emergence of subpopulations or changes in population composition."
            )
        
        # Severity-specific recommendations
        if severity == ShiftSeverity.CRITICAL:
            recommendations.append(
                "🚨 CRITICAL: Very large population shift. Verify this is expected. "
                "If unexpected, consider excluding from comparative analysis or re-running samples."
            )
        elif severity == ShiftSeverity.MAJOR:
            recommendations.append(
                "⚠️ Large shift detected. Review experimental conditions and consider "
                "whether samples are comparable for analysis."
            )
        elif severity == ShiftSeverity.MODERATE:
            recommendations.append(
                "ℹ️ Moderate shift detected. Document and consider in interpretation of results."
            )
        
        return recommendations
    
    def compare_to_baseline(
        self,
        baseline_data: np.ndarray,
        baseline_id: str,
        baseline_name: str,
        sample_data_list: List[Tuple[np.ndarray, str, str]],  # (data, id, name)
        metric_name: str = "particle_size",
        tests: Optional[List[str]] = None
    ) -> MultiSampleShiftResult:
        """
        Compare multiple samples against a baseline.
        
        Useful for quality control where you have a reference sample.
        
        Args:
            baseline_data: Reference sample data
            baseline_id: Baseline sample ID
            baseline_name: Baseline sample name
            sample_data_list: List of (data, sample_id, sample_name) tuples
            metric_name: Name of metric being compared
            tests: Tests to run
            
        Returns:
            MultiSampleShiftResult with all comparisons
        """
        comparisons = []
        
        for data, sample_id, sample_name in sample_data_list:
            try:
                result = self.detect_shift(
                    data_a=baseline_data,
                    data_b=data,
                    sample_a_id=baseline_id,
                    sample_a_name=baseline_name,
                    sample_b_id=sample_id,
                    sample_b_name=sample_name,
                    metric_name=metric_name,
                    tests=tests
                )
                comparisons.append(result)
            except Exception as e:
                logger.error(f"Comparison failed for {sample_name}: {e}")
        
        # Determine overall results
        any_significant = any(c.overall_shift_detected for c in comparisons)
        
        severity_order = [ShiftSeverity.NONE, ShiftSeverity.MINOR, 
                        ShiftSeverity.MODERATE, ShiftSeverity.MAJOR, ShiftSeverity.CRITICAL]
        max_severity = max(
            (c.overall_severity for c in comparisons),
            key=lambda s: severity_order.index(s),
            default=ShiftSeverity.NONE
        )
        
        # Generate global summary
        shifted_samples = [c.sample_b.sample_name for c in comparisons if c.overall_shift_detected]
        if shifted_samples:
            global_summary = (
                f"Baseline comparison complete. {len(shifted_samples)}/{len(comparisons)} samples "
                f"show significant shift from baseline. Shifted samples: {', '.join(shifted_samples)}."
            )
        else:
            global_summary = (
                f"Baseline comparison complete. All {len(comparisons)} samples are consistent "
                f"with the baseline."
            )
        
        return MultiSampleShiftResult(
            mode=ComparisonMode.BASELINE,
            baseline_sample=baseline_name,
            comparisons=comparisons,
            global_summary=global_summary,
            any_significant_shift=any_significant,
            max_severity=max_severity
        )
    
    def temporal_comparison(
        self,
        temporal_data: List[Tuple[np.ndarray, str, str]],  # Ordered by time
        metric_name: str = "particle_size",
        tests: Optional[List[str]] = None
    ) -> MultiSampleShiftResult:
        """
        Compare sequential samples to detect drift over time.
        
        Compares each sample to its predecessor in the sequence.
        
        Args:
            temporal_data: Time-ordered list of (data, sample_id, sample_name)
            metric_name: Name of metric being compared
            tests: Tests to run
            
        Returns:
            MultiSampleShiftResult with sequential comparisons
        """
        if len(temporal_data) < 2:
            raise ValueError("Need at least 2 samples for temporal comparison")
        
        comparisons = []
        
        for i in range(1, len(temporal_data)):
            prev_data, prev_id, prev_name = temporal_data[i-1]
            curr_data, curr_id, curr_name = temporal_data[i]
            
            try:
                result = self.detect_shift(
                    data_a=prev_data,
                    data_b=curr_data,
                    sample_a_id=prev_id,
                    sample_a_name=prev_name,
                    sample_b_id=curr_id,
                    sample_b_name=curr_name,
                    metric_name=metric_name,
                    tests=tests
                )
                comparisons.append(result)
            except Exception as e:
                logger.error(f"Temporal comparison failed at step {i}: {e}")
        
        # Detect drift pattern
        any_significant = any(c.overall_shift_detected for c in comparisons)
        
        severity_order = [ShiftSeverity.NONE, ShiftSeverity.MINOR, 
                        ShiftSeverity.MODERATE, ShiftSeverity.MAJOR, ShiftSeverity.CRITICAL]
        max_severity = max(
            (c.overall_severity for c in comparisons),
            key=lambda s: severity_order.index(s),
            default=ShiftSeverity.NONE
        )
        
        # Generate temporal summary
        shift_indices = [i+1 for i, c in enumerate(comparisons) if c.overall_shift_detected]
        if shift_indices:
            global_summary = (
                f"Temporal analysis: {len(shift_indices)}/{len(comparisons)} transitions show "
                f"significant shift. Shifts detected at positions: {shift_indices}. "
                f"Consider investigating drift or batch effects."
            )
        else:
            global_summary = (
                f"Temporal analysis: Population remains stable across all {len(temporal_data)} "
                f"time points. No significant drift detected."
            )
        
        return MultiSampleShiftResult(
            mode=ComparisonMode.TEMPORAL,
            baseline_sample=None,
            comparisons=comparisons,
            global_summary=global_summary,
            any_significant_shift=any_significant,
            max_severity=max_severity
        )


# Convenience function for quick shift detection
def detect_population_shift(
    data_a: np.ndarray,
    data_b: np.ndarray,
    alpha: float = 0.05,
    tests: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Quick function to detect population shift between two data arrays.
    
    Args:
        data_a: First sample data
        data_b: Second sample data
        alpha: Significance level
        tests: Tests to run (default: ["ks", "emd", "mean", "variance"])
        
    Returns:
        Dictionary with shift detection results
    """
    detector = PopulationShiftDetector(alpha=alpha)
    result = detector.detect_shift(
        data_a=data_a,
        data_b=data_b,
        sample_a_id="sample_a",
        sample_a_name="Sample A",
        sample_b_id="sample_b",
        sample_b_name="Sample B",
        metric_name="value",
        tests=tests
    )
    
    return {
        "shift_detected": result.overall_shift_detected,
        "severity": result.overall_severity.value,
        "summary": result.summary,
        "tests": [
            {
                "name": t.test_name,
                "statistic": t.statistic,
                "p_value": t.p_value,
                "significant": t.significant,
                "effect_size": t.effect_size,
                "interpretation": t.interpretation
            }
            for t in result.tests
        ],
        "recommendations": result.recommendations
    }
