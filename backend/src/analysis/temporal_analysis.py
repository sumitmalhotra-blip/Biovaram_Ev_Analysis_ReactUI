"""
Temporal Analysis Module
========================

CRMIT-007: Time Correlation Analysis

Purpose: Analyze time-series data from EV samples to detect trends,
correlations, and temporal patterns in measurements.

Features:
- Time-series trend detection (linear, exponential)
- Correlation analysis between samples over time
- Stability assessment (coefficient of variation)
- Drift detection with statistical significance
- Periodicity detection (seasonal patterns)
- Change point detection
- Moving average and smoothing

Architecture:
- Layer 5: Analysis Engine
- Component: Temporal Analysis Module
- Integration: Population Shift Detection (CRMIT-004)

Author: CRMIT Team
Date: January 2026
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import find_peaks, detrend
from scipy.ndimage import uniform_filter1d
from loguru import logger


class TrendType(str, Enum):
    """Types of detected trends."""
    NONE = "none"
    LINEAR_INCREASING = "linear_increasing"
    LINEAR_DECREASING = "linear_decreasing"
    EXPONENTIAL_GROWTH = "exponential_growth"
    EXPONENTIAL_DECAY = "exponential_decay"
    CYCLICAL = "cyclical"
    RANDOM_WALK = "random_walk"


class StabilityLevel(str, Enum):
    """Stability assessment levels."""
    EXCELLENT = "excellent"  # CV < 5%
    GOOD = "good"           # CV 5-10%
    ACCEPTABLE = "acceptable"  # CV 10-15%
    POOR = "poor"           # CV 15-25%
    UNSTABLE = "unstable"   # CV > 25%


class DriftSeverity(str, Enum):
    """Severity of detected drift."""
    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    SIGNIFICANT = "significant"
    CRITICAL = "critical"


@dataclass
class TimeSeriesPoint:
    """Single point in a time series."""
    timestamp: datetime
    value: float
    sample_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrendResult:
    """Result of trend analysis."""
    trend_type: TrendType
    slope: float
    intercept: float
    r_squared: float
    p_value: float
    confidence_interval: Tuple[float, float]
    is_significant: bool
    interpretation: str


@dataclass
class StabilityResult:
    """Result of stability analysis."""
    level: StabilityLevel
    mean: float
    std: float
    cv: float  # Coefficient of variation
    min_value: float
    max_value: float
    range_value: float
    n_samples: int
    interpretation: str


@dataclass
class DriftResult:
    """Result of drift detection."""
    severity: DriftSeverity
    drift_magnitude: float
    drift_direction: str  # "increasing", "decreasing", "stable"
    p_value: float
    is_significant: bool
    change_points: List[int]
    interpretation: str


@dataclass
class CorrelationResult:
    """Result of correlation analysis between metrics."""
    metric_a: str
    metric_b: str
    pearson_r: float
    pearson_p: float
    spearman_rho: float
    spearman_p: float
    is_significant: bool
    correlation_strength: str  # "none", "weak", "moderate", "strong", "very_strong"
    interpretation: str


@dataclass
class TemporalAnalysisResult:
    """Complete temporal analysis result."""
    metric: str
    time_range: Tuple[datetime, datetime]
    n_points: int
    trend: TrendResult
    stability: StabilityResult
    drift: DriftResult
    correlations: List[CorrelationResult]
    moving_average: List[float]
    smoothed_values: List[float]
    summary: str
    recommendations: List[str]


class TemporalAnalyzer:
    """
    Analyze temporal patterns in EV measurement data.
    
    Provides comprehensive time-series analysis including:
    - Trend detection and quantification
    - Stability assessment
    - Drift detection with change point identification
    - Cross-metric correlation analysis
    - Smoothing and filtering
    """
    
    # Stability thresholds (CV percentages)
    STABILITY_THRESHOLDS = {
        StabilityLevel.EXCELLENT: 5.0,
        StabilityLevel.GOOD: 10.0,
        StabilityLevel.ACCEPTABLE: 15.0,
        StabilityLevel.POOR: 25.0,
        # Above 25% is UNSTABLE
    }
    
    # Drift severity thresholds (normalized change per time unit)
    DRIFT_THRESHOLDS = {
        DriftSeverity.MINOR: 0.05,      # 5% change
        DriftSeverity.MODERATE: 0.10,    # 10% change
        DriftSeverity.SIGNIFICANT: 0.20, # 20% change
        DriftSeverity.CRITICAL: 0.35,    # 35% change
    }
    
    # Correlation strength thresholds
    CORRELATION_THRESHOLDS = {
        "none": 0.1,
        "weak": 0.3,
        "moderate": 0.5,
        "strong": 0.7,
        "very_strong": 0.9,
    }
    
    def __init__(
        self,
        alpha: float = 0.05,
        min_samples: int = 3,
        smoothing_window: int = 3,
    ):
        """
        Initialize the temporal analyzer.
        
        Args:
            alpha: Significance level for statistical tests
            min_samples: Minimum samples required for analysis
            smoothing_window: Window size for moving average smoothing
        """
        self.alpha = alpha
        self.min_samples = min_samples
        self.smoothing_window = smoothing_window
        logger.info(f"TemporalAnalyzer initialized: alpha={alpha}, min_samples={min_samples}")
    
    def analyze_time_series(
        self,
        timestamps: List[datetime],
        values: List[float],
        metric_name: str = "value",
        additional_metrics: Optional[Dict[str, List[float]]] = None,
    ) -> TemporalAnalysisResult:
        """
        Perform comprehensive temporal analysis on a time series.
        
        Args:
            timestamps: List of timestamps for each measurement
            values: List of measurement values
            metric_name: Name of the metric being analyzed
            additional_metrics: Optional dict of additional metrics for correlation
            
        Returns:
            TemporalAnalysisResult with all analysis components
        """
        n = len(values)
        
        if n < self.min_samples:
            logger.warning(f"Insufficient samples ({n}) for temporal analysis")
            return self._create_insufficient_data_result(metric_name, timestamps, values)
        
        logger.info(f"Analyzing temporal series: {metric_name} with {n} points")
        
        # Convert to numpy arrays
        values_arr = np.array(values)
        
        # Convert timestamps to numeric (hours from first timestamp)
        time_numeric = self._timestamps_to_numeric(timestamps)
        
        # Perform analyses
        trend_result = self._analyze_trend(time_numeric, values_arr)
        stability_result = self._analyze_stability(values_arr)
        drift_result = self._detect_drift(time_numeric, values_arr)
        
        # Correlation analysis with additional metrics
        correlations = []
        if additional_metrics:
            for other_metric, other_values in additional_metrics.items():
                if len(other_values) == n:
                    corr = self._analyze_correlation(
                        values_arr, 
                        np.array(other_values),
                        metric_name,
                        other_metric
                    )
                    correlations.append(corr)
        
        # Smoothing
        moving_avg = self._moving_average(values_arr, self.smoothing_window)
        smoothed = self._smooth_values(values_arr)
        
        # Generate summary and recommendations
        summary = self._generate_summary(trend_result, stability_result, drift_result)
        recommendations = self._generate_recommendations(
            trend_result, stability_result, drift_result
        )
        
        return TemporalAnalysisResult(
            metric=metric_name,
            time_range=(min(timestamps), max(timestamps)),
            n_points=n,
            trend=trend_result,
            stability=stability_result,
            drift=drift_result,
            correlations=correlations,
            moving_average=moving_avg.tolist(),
            smoothed_values=smoothed.tolist(),
            summary=summary,
            recommendations=recommendations,
        )
    
    def _timestamps_to_numeric(self, timestamps: List[datetime]) -> np.ndarray:
        """Convert timestamps to numeric values (hours from first timestamp)."""
        if not timestamps:
            return np.array([])
        
        base = min(timestamps)
        return np.array([
            (ts - base).total_seconds() / 3600.0  # Hours
            for ts in timestamps
        ])
    
    def _analyze_trend(
        self, 
        time_numeric: np.ndarray, 
        values: np.ndarray
    ) -> TrendResult:
        """Analyze trend in the time series."""
        n = len(values)
        
        # Linear regression - unpack all 5 values explicitly
        result = stats.linregress(time_numeric, values)
        slope = float(result.slope)  # type: ignore[union-attr]
        intercept = float(result.intercept)  # type: ignore[union-attr]
        r_value = float(result.rvalue)  # type: ignore[union-attr]
        p_value = float(result.pvalue)  # type: ignore[union-attr]
        std_err = float(result.stderr)  # type: ignore[union-attr]
        r_squared = r_value ** 2
        
        # Confidence interval for slope (95%)
        t_crit = stats.t.ppf(1 - self.alpha / 2, n - 2)
        ci_margin = t_crit * std_err
        ci = (slope - ci_margin, slope + ci_margin)
        
        # Determine trend type
        is_significant = p_value < self.alpha
        
        if not is_significant:
            trend_type = TrendType.NONE
            interpretation = "No significant trend detected in the data."
        elif slope > 0:
            # Check for exponential growth
            if self._is_exponential(time_numeric, values, increasing=True):
                trend_type = TrendType.EXPONENTIAL_GROWTH
                interpretation = f"Exponential growth detected (R² = {r_squared:.3f})."
            else:
                trend_type = TrendType.LINEAR_INCREASING
                interpretation = f"Linear increasing trend: {slope:.4f} units/hour (R² = {r_squared:.3f})."
        else:
            # Check for exponential decay
            if self._is_exponential(time_numeric, values, increasing=False):
                trend_type = TrendType.EXPONENTIAL_DECAY
                interpretation = f"Exponential decay detected (R² = {r_squared:.3f})."
            else:
                trend_type = TrendType.LINEAR_DECREASING
                interpretation = f"Linear decreasing trend: {slope:.4f} units/hour (R² = {r_squared:.3f})."
        
        return TrendResult(
            trend_type=trend_type,
            slope=slope,
            intercept=intercept,
            r_squared=r_squared,
            p_value=p_value,
            confidence_interval=(float(ci[0]), float(ci[1])),
            is_significant=is_significant,
            interpretation=interpretation,
        )
    
    def _is_exponential(
        self, 
        time: np.ndarray, 
        values: np.ndarray, 
        increasing: bool
    ) -> bool:
        """Check if the trend is better fit by exponential than linear."""
        try:
            # Fit linear
            result_linear = stats.linregress(time, values)
            r_linear = float(result_linear.rvalue)  # type: ignore[union-attr]
            
            # Fit exponential (log-linear)
            if increasing:
                log_values = np.log(np.maximum(values, 1e-10))
            else:
                # For decay, flip values
                max_val = np.max(values)
                log_values = np.log(np.maximum(max_val - values + 1, 1e-10))
            
            result_exp = stats.linregress(time, log_values)
            r_exp = float(result_exp.rvalue)  # type: ignore[union-attr]
            
            # Exponential is better if R² is significantly higher
            return abs(r_exp) > abs(r_linear) + 0.1
        except Exception:
            return False
    
    def _analyze_stability(self, values: np.ndarray) -> StabilityResult:
        """Analyze stability of measurements."""
        mean_val = float(np.mean(values))
        std_val = float(np.std(values))
        min_val = float(np.min(values))
        max_val = float(np.max(values))
        
        # Coefficient of variation (CV)
        cv = (std_val / mean_val * 100) if mean_val != 0 else float('inf')
        
        # Determine stability level
        if cv < self.STABILITY_THRESHOLDS[StabilityLevel.EXCELLENT]:
            level = StabilityLevel.EXCELLENT
            interpretation = f"Excellent stability (CV = {cv:.1f}%). Measurements are highly consistent."
        elif cv < self.STABILITY_THRESHOLDS[StabilityLevel.GOOD]:
            level = StabilityLevel.GOOD
            interpretation = f"Good stability (CV = {cv:.1f}%). Measurements show acceptable variation."
        elif cv < self.STABILITY_THRESHOLDS[StabilityLevel.ACCEPTABLE]:
            level = StabilityLevel.ACCEPTABLE
            interpretation = f"Acceptable stability (CV = {cv:.1f}%). Some variation present."
        elif cv < self.STABILITY_THRESHOLDS[StabilityLevel.POOR]:
            level = StabilityLevel.POOR
            interpretation = f"Poor stability (CV = {cv:.1f}%). Consider investigating sources of variation."
        else:
            level = StabilityLevel.UNSTABLE
            interpretation = f"Unstable measurements (CV = {cv:.1f}%). High variability detected."
        
        return StabilityResult(
            level=level,
            mean=mean_val,
            std=std_val,
            cv=float(cv),
            min_value=min_val,
            max_value=max_val,
            range_value=max_val - min_val,
            n_samples=len(values),
            interpretation=interpretation,
        )
    
    def _detect_drift(
        self, 
        time_numeric: np.ndarray, 
        values: np.ndarray
    ) -> DriftResult:
        """Detect drift in the time series."""
        n = len(values)
        
        # Calculate overall change
        if n < 2:
            return DriftResult(
                severity=DriftSeverity.NONE,
                drift_magnitude=0.0,
                drift_direction="stable",
                p_value=1.0,
                is_significant=False,
                change_points=[],
                interpretation="Insufficient data for drift detection.",
            )
        
        # Calculate drift magnitude (normalized)
        first_half_mean = np.mean(values[:n//2])
        second_half_mean = np.mean(values[n//2:])
        baseline = np.mean(values)
        
        if baseline != 0:
            drift_magnitude = abs(second_half_mean - first_half_mean) / abs(baseline)
        else:
            drift_magnitude = 0.0
        
        # Mann-Whitney U test for drift significance
        try:
            _, p_value = stats.mannwhitneyu(
                values[:n//2], 
                values[n//2:], 
                alternative='two-sided'
            )
        except Exception:
            p_value = 1.0
        
        is_significant = p_value < self.alpha
        
        # Determine drift direction
        if second_half_mean > first_half_mean * 1.02:
            drift_direction = "increasing"
        elif second_half_mean < first_half_mean * 0.98:
            drift_direction = "decreasing"
        else:
            drift_direction = "stable"
        
        # Determine severity
        if not is_significant or drift_magnitude < self.DRIFT_THRESHOLDS[DriftSeverity.MINOR]:
            severity = DriftSeverity.NONE
            interpretation = "No significant drift detected."
        elif drift_magnitude < self.DRIFT_THRESHOLDS[DriftSeverity.MODERATE]:
            severity = DriftSeverity.MINOR
            interpretation = f"Minor drift detected ({drift_magnitude*100:.1f}% change)."
        elif drift_magnitude < self.DRIFT_THRESHOLDS[DriftSeverity.SIGNIFICANT]:
            severity = DriftSeverity.MODERATE
            interpretation = f"Moderate drift detected ({drift_magnitude*100:.1f}% change)."
        elif drift_magnitude < self.DRIFT_THRESHOLDS[DriftSeverity.CRITICAL]:
            severity = DriftSeverity.SIGNIFICANT
            interpretation = f"Significant drift detected ({drift_magnitude*100:.1f}% change). Investigation recommended."
        else:
            severity = DriftSeverity.CRITICAL
            interpretation = f"Critical drift detected ({drift_magnitude*100:.1f}% change). Immediate attention required."
        
        # Detect change points
        change_points = self._detect_change_points(values)
        
        return DriftResult(
            severity=severity,
            drift_magnitude=float(drift_magnitude),
            drift_direction=drift_direction,
            p_value=float(p_value),
            is_significant=is_significant,
            change_points=change_points,
            interpretation=interpretation,
        )
    
    def _detect_change_points(self, values: np.ndarray) -> List[int]:
        """Detect change points in the time series using CUSUM."""
        n = len(values)
        if n < 5:
            return []
        
        # Simple CUSUM change point detection
        mean_val = np.mean(values)
        std_val = np.std(values)
        
        if std_val == 0:
            return []
        
        # Calculate cumulative sum of deviations
        cusum = np.cumsum(values - mean_val) / std_val
        
        # Find peaks in absolute CUSUM
        abs_cusum = np.abs(cusum)
        threshold = np.mean(abs_cusum) + 2 * np.std(abs_cusum)
        
        change_points = []
        for i in range(1, n - 1):
            if abs_cusum[i] > threshold:
                # Check if it's a local maximum
                if abs_cusum[i] > abs_cusum[i-1] and abs_cusum[i] > abs_cusum[i+1]:
                    change_points.append(int(i))
        
        return change_points
    
    def _analyze_correlation(
        self,
        values_a: np.ndarray,
        values_b: np.ndarray,
        metric_a: str,
        metric_b: str,
    ) -> CorrelationResult:
        """Analyze correlation between two metrics."""
        # Pearson correlation
        pearson_result = stats.pearsonr(values_a, values_b)
        pearson_r = float(pearson_result.statistic)  # type: ignore[union-attr]
        pearson_p = float(pearson_result.pvalue)  # type: ignore[union-attr]
        
        # Spearman correlation (rank-based, more robust)
        spearman_result = stats.spearmanr(values_a, values_b)
        spearman_rho = float(spearman_result.statistic)  # type: ignore[union-attr]
        spearman_p = float(spearman_result.pvalue)  # type: ignore[union-attr]
        
        # Determine significance
        is_significant = min(pearson_p, spearman_p) < self.alpha
        
        # Determine correlation strength
        abs_r = abs(pearson_r)
        if abs_r < self.CORRELATION_THRESHOLDS["none"]:
            strength = "none"
        elif abs_r < self.CORRELATION_THRESHOLDS["weak"]:
            strength = "weak"
        elif abs_r < self.CORRELATION_THRESHOLDS["moderate"]:
            strength = "moderate"
        elif abs_r < self.CORRELATION_THRESHOLDS["strong"]:
            strength = "strong"
        else:
            strength = "very_strong"
        
        # Generate interpretation
        direction = "positive" if pearson_r > 0 else "negative"
        if strength == "none":
            interpretation = f"No correlation between {metric_a} and {metric_b}."
        else:
            interpretation = (
                f"{strength.replace('_', ' ').capitalize()} {direction} correlation "
                f"between {metric_a} and {metric_b} (r = {pearson_r:.3f})."
            )
        
        return CorrelationResult(
            metric_a=metric_a,
            metric_b=metric_b,
            pearson_r=pearson_r,
            pearson_p=pearson_p,
            spearman_rho=spearman_rho,
            spearman_p=spearman_p,
            is_significant=is_significant,
            correlation_strength=strength,
            interpretation=interpretation,
        )
    
    def _moving_average(self, values: np.ndarray, window: int) -> np.ndarray:
        """Calculate moving average."""
        if len(values) < window:
            return values.copy()
        
        return uniform_filter1d(values, size=window, mode='nearest')
    
    def _smooth_values(self, values: np.ndarray) -> np.ndarray:
        """Apply smoothing to reduce noise."""
        if len(values) < 3:
            return values.copy()
        
        # Simple exponential smoothing
        alpha = 0.3
        smoothed = np.zeros_like(values)
        smoothed[0] = values[0]
        
        for i in range(1, len(values)):
            smoothed[i] = alpha * values[i] + (1 - alpha) * smoothed[i-1]
        
        return smoothed
    
    def _generate_summary(
        self,
        trend: TrendResult,
        stability: StabilityResult,
        drift: DriftResult,
    ) -> str:
        """Generate a human-readable summary of the analysis."""
        parts = []
        
        # Trend summary
        if trend.is_significant:
            parts.append(f"Trend: {trend.trend_type.value.replace('_', ' ').title()}")
        else:
            parts.append("Trend: Stable")
        
        # Stability summary
        parts.append(f"Stability: {stability.level.value.title()} (CV={stability.cv:.1f}%)")
        
        # Drift summary
        if drift.severity != DriftSeverity.NONE:
            parts.append(f"Drift: {drift.severity.value.title()} ({drift.drift_direction})")
        else:
            parts.append("Drift: None detected")
        
        return " | ".join(parts)
    
    def _generate_recommendations(
        self,
        trend: TrendResult,
        stability: StabilityResult,
        drift: DriftResult,
    ) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        # Trend recommendations
        if trend.trend_type == TrendType.LINEAR_DECREASING:
            recommendations.append(
                "Decreasing trend detected. Check for sample degradation or instrument drift."
            )
        elif trend.trend_type == TrendType.EXPONENTIAL_DECAY:
            recommendations.append(
                "Exponential decay detected. Urgent: Investigate sample stability and storage conditions."
            )
        elif trend.trend_type == TrendType.EXPONENTIAL_GROWTH:
            recommendations.append(
                "Exponential growth detected. Review for potential contamination or aggregation."
            )
        
        # Stability recommendations
        if stability.level in [StabilityLevel.POOR, StabilityLevel.UNSTABLE]:
            recommendations.append(
                f"High measurement variability (CV={stability.cv:.1f}%). "
                "Consider standardizing sample preparation and acquisition parameters."
            )
        
        # Drift recommendations
        if drift.severity == DriftSeverity.CRITICAL:
            recommendations.append(
                "Critical drift detected. Immediate calibration check recommended."
            )
        elif drift.severity == DriftSeverity.SIGNIFICANT:
            recommendations.append(
                "Significant drift detected. Schedule instrument maintenance."
            )
        elif drift.severity == DriftSeverity.MODERATE:
            recommendations.append(
                "Moderate drift detected. Monitor closely and consider recalibration."
            )
        
        # Change point recommendations
        if drift.change_points:
            recommendations.append(
                f"Change points detected at indices: {drift.change_points}. "
                "Review experimental conditions at these time points."
            )
        
        # If everything is good
        if not recommendations:
            recommendations.append(
                "All temporal metrics within acceptable ranges. Continue current protocols."
            )
        
        return recommendations
    
    def _create_insufficient_data_result(
        self,
        metric_name: str,
        timestamps: List[datetime],
        values: List[float],
    ) -> TemporalAnalysisResult:
        """Create a result object for insufficient data cases."""
        n = len(values)
        time_range = (
            min(timestamps) if timestamps else datetime.now(),
            max(timestamps) if timestamps else datetime.now(),
        )
        
        return TemporalAnalysisResult(
            metric=metric_name,
            time_range=time_range,
            n_points=n,
            trend=TrendResult(
                trend_type=TrendType.NONE,
                slope=0.0,
                intercept=float(np.mean(values)) if values else 0.0,
                r_squared=0.0,
                p_value=1.0,
                confidence_interval=(0.0, 0.0),
                is_significant=False,
                interpretation=f"Insufficient data ({n} points) for trend analysis.",
            ),
            stability=StabilityResult(
                level=StabilityLevel.ACCEPTABLE,
                mean=float(np.mean(values)) if values else 0.0,
                std=float(np.std(values)) if values else 0.0,
                cv=0.0,
                min_value=float(min(values)) if values else 0.0,
                max_value=float(max(values)) if values else 0.0,
                range_value=0.0,
                n_samples=n,
                interpretation=f"Insufficient data ({n} points) for stability analysis.",
            ),
            drift=DriftResult(
                severity=DriftSeverity.NONE,
                drift_magnitude=0.0,
                drift_direction="stable",
                p_value=1.0,
                is_significant=False,
                change_points=[],
                interpretation=f"Insufficient data ({n} points) for drift detection.",
            ),
            correlations=[],
            moving_average=values.copy() if values else [],
            smoothed_values=values.copy() if values else [],
            summary=f"Insufficient data ({n} points). Minimum {self.min_samples} required.",
            recommendations=[
                f"Collect at least {self.min_samples} samples for meaningful temporal analysis."
            ],
        )
    
    def compare_sample_series(
        self,
        sample_ids: List[str],
        timestamps: List[datetime],
        metrics: Dict[str, List[float]],
    ) -> Dict[str, Any]:
        """
        Compare multiple samples over time across metrics.
        
        Args:
            sample_ids: List of sample identifiers
            timestamps: Corresponding timestamps
            metrics: Dict mapping metric names to value lists
            
        Returns:
            Comprehensive comparison result
        """
        results = {}
        
        for metric_name, values in metrics.items():
            other_metrics = {k: v for k, v in metrics.items() if k != metric_name}
            
            results[metric_name] = self.analyze_time_series(
                timestamps=timestamps,
                values=values,
                metric_name=metric_name,
                additional_metrics=other_metrics,
            )
        
        # Overall summary
        overall_stability = self._assess_overall_stability(results)
        overall_drift = self._assess_overall_drift(results)
        
        return {
            "sample_ids": sample_ids,
            "n_samples": len(sample_ids),
            "time_range": {
                "start": min(timestamps).isoformat() if timestamps else None,
                "end": max(timestamps).isoformat() if timestamps else None,
            },
            "metrics_analyzed": list(metrics.keys()),
            "individual_results": {
                k: self._result_to_dict(v) for k, v in results.items()
            },
            "overall_stability": overall_stability,
            "overall_drift": overall_drift,
        }
    
    def _assess_overall_stability(
        self, 
        results: Dict[str, TemporalAnalysisResult]
    ) -> Dict[str, Any]:
        """Assess overall stability across all metrics."""
        if not results:
            return {"level": "unknown", "average_cv": 0.0}
        
        cvs = [r.stability.cv for r in results.values()]
        avg_cv = np.mean(cvs)
        
        if avg_cv < 5:
            level = "excellent"
        elif avg_cv < 10:
            level = "good"
        elif avg_cv < 15:
            level = "acceptable"
        elif avg_cv < 25:
            level = "poor"
        else:
            level = "unstable"
        
        return {
            "level": level,
            "average_cv": float(avg_cv),
            "min_cv": float(min(cvs)),
            "max_cv": float(max(cvs)),
        }
    
    def _assess_overall_drift(
        self, 
        results: Dict[str, TemporalAnalysisResult]
    ) -> Dict[str, Any]:
        """Assess overall drift across all metrics."""
        if not results:
            return {"severity": "unknown", "metrics_with_drift": []}
        
        metrics_with_drift = []
        max_severity = DriftSeverity.NONE
        
        severity_order = [
            DriftSeverity.NONE,
            DriftSeverity.MINOR,
            DriftSeverity.MODERATE,
            DriftSeverity.SIGNIFICANT,
            DriftSeverity.CRITICAL,
        ]
        
        for metric, result in results.items():
            if result.drift.severity != DriftSeverity.NONE:
                metrics_with_drift.append({
                    "metric": metric,
                    "severity": result.drift.severity.value,
                    "magnitude": result.drift.drift_magnitude,
                    "direction": result.drift.drift_direction,
                })
                
                if severity_order.index(result.drift.severity) > severity_order.index(max_severity):
                    max_severity = result.drift.severity
        
        return {
            "max_severity": max_severity.value,
            "metrics_with_drift": metrics_with_drift,
            "total_drifting_metrics": len(metrics_with_drift),
        }
    
    def _result_to_dict(self, result: TemporalAnalysisResult) -> Dict[str, Any]:
        """Convert TemporalAnalysisResult to dictionary."""
        return {
            "metric": result.metric,
            "time_range": {
                "start": result.time_range[0].isoformat(),
                "end": result.time_range[1].isoformat(),
            },
            "n_points": result.n_points,
            "trend": {
                "type": result.trend.trend_type.value,
                "slope": result.trend.slope,
                "r_squared": result.trend.r_squared,
                "p_value": result.trend.p_value,
                "is_significant": result.trend.is_significant,
                "interpretation": result.trend.interpretation,
            },
            "stability": {
                "level": result.stability.level.value,
                "mean": result.stability.mean,
                "std": result.stability.std,
                "cv": result.stability.cv,
                "interpretation": result.stability.interpretation,
            },
            "drift": {
                "severity": result.drift.severity.value,
                "magnitude": result.drift.drift_magnitude,
                "direction": result.drift.drift_direction,
                "p_value": result.drift.p_value,
                "is_significant": result.drift.is_significant,
                "change_points": result.drift.change_points,
                "interpretation": result.drift.interpretation,
            },
            "correlations": [
                {
                    "metric_a": c.metric_a,
                    "metric_b": c.metric_b,
                    "pearson_r": c.pearson_r,
                    "spearman_rho": c.spearman_rho,
                    "strength": c.correlation_strength,
                    "is_significant": c.is_significant,
                    "interpretation": c.interpretation,
                }
                for c in result.correlations
            ],
            "summary": result.summary,
            "recommendations": result.recommendations,
        }


# Convenience function
def analyze_temporal_data(
    timestamps: List[datetime],
    values: List[float],
    metric_name: str = "value",
    additional_metrics: Optional[Dict[str, List[float]]] = None,
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """
    Convenience function for temporal analysis.
    
    Args:
        timestamps: List of timestamps
        values: List of measurement values
        metric_name: Name of the primary metric
        additional_metrics: Optional additional metrics for correlation
        alpha: Significance level
        
    Returns:
        Dictionary with analysis results
    """
    analyzer = TemporalAnalyzer(alpha=alpha)
    result = analyzer.analyze_time_series(
        timestamps=timestamps,
        values=values,
        metric_name=metric_name,
        additional_metrics=additional_metrics,
    )
    return analyzer._result_to_dict(result)


if __name__ == "__main__":
    # Example usage
    import random
    from datetime import timedelta
    
    logger.info("Temporal Analysis Module - Running example...")
    
    # Generate sample data with slight trend
    base_time = datetime.now()
    n_samples = 20
    
    timestamps = [base_time + timedelta(hours=i*2) for i in range(n_samples)]
    
    # Values with slight upward trend + noise
    base_values = [100 + i * 0.5 + random.gauss(0, 5) for i in range(n_samples)]
    
    # Additional metric (correlated with noise)
    other_metric = [v * 0.8 + random.gauss(10, 3) for v in base_values]
    
    analyzer = TemporalAnalyzer()
    result = analyzer.analyze_time_series(
        timestamps=timestamps,
        values=base_values,
        metric_name="particle_concentration",
        additional_metrics={"secondary_metric": other_metric},
    )
    
    print(f"\n=== Temporal Analysis Result ===")
    print(f"Metric: {result.metric}")
    print(f"Points: {result.n_points}")
    print(f"\nTrend: {result.trend.trend_type.value}")
    print(f"  Slope: {result.trend.slope:.4f}")
    print(f"  R²: {result.trend.r_squared:.3f}")
    print(f"  Significant: {result.trend.is_significant}")
    print(f"\nStability: {result.stability.level.value}")
    print(f"  CV: {result.stability.cv:.1f}%")
    print(f"  Mean: {result.stability.mean:.2f}")
    print(f"\nDrift: {result.drift.severity.value}")
    print(f"  Magnitude: {result.drift.drift_magnitude*100:.1f}%")
    print(f"  Direction: {result.drift.drift_direction}")
    print(f"\nSummary: {result.summary}")
    print(f"\nRecommendations:")
    for rec in result.recommendations:
        print(f"  - {rec}")
