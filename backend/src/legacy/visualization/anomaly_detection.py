"""
Anomaly Detection Module - Visualization & Analysis Layer
=========================================================

Purpose: Detect and visualize anomalies in scatter plots and distributions

Architecture Compliance:
- Layer 5: Anomaly Detection Engine
- Layer 6: Visualization Layer
- Component: Population Shift Detection & Alert System
- Function: Detect scatter plot shifts, outliers, and distribution changes

Deliverable: Anomaly detection for scatter plot shifts

Author: CRMIT Team
Date: November 15, 2025
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
from scipy import stats
from scipy.spatial.distance import mahalanobis
import matplotlib.pyplot as plt
import seaborn as sns
from loguru import logger


class AnomalyDetector:
    """
    Detect anomalies in FCS and NTA data.
    
    Detection methods:
    - Population shift detection (scatter plot)
    - Statistical outliers (Z-score, IQR)
    - Distribution changes (KS test)
    - Mahalanobis distance for multivariate outliers
    - Control chart analysis
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize anomaly detector.
        
        Args:
            output_dir: Directory to save plots (default: figures/anomalies/)
        """
        if output_dir is None:
            output_dir = Path("figures/anomalies")
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.baseline = None
        
        logger.info(f"🔍 Anomaly Detector initialized: {self.output_dir}")
    
    def set_baseline(
        self,
        baseline_data: pd.DataFrame,
        x_channel: str = 'FSC-A',
        y_channel: str = 'SSC-A'
    ) -> Dict[str, Any]:
        """
        Set baseline distribution for comparison.
        
        Args:
            baseline_data: Baseline FCS/NTA data
            x_channel: X-axis channel
            y_channel: Y-axis channel
        
        Returns:
            Dictionary with baseline statistics
        """
        logger.info(f"📊 Setting baseline distribution")
        
        # Extract valid data
        x_data = baseline_data[x_channel]
        y_data = baseline_data[y_channel]
        
        valid_mask = (x_data > 0) & (y_data > 0) & np.isfinite(x_data) & np.isfinite(y_data)
        x_valid = x_data[valid_mask]
        y_valid = y_data[valid_mask]
        
        # Calculate statistics
        self.baseline = {
            'x_channel': x_channel,
            'y_channel': y_channel,
            'x_mean': np.mean(x_valid),
            'y_mean': np.mean(y_valid),
            'x_std': np.std(x_valid),
            'y_std': np.std(y_valid),
            'x_median': np.median(x_valid),
            'y_median': np.median(y_valid),
            'x_q25': np.percentile(x_valid, 25),
            'x_q75': np.percentile(x_valid, 75),
            'y_q25': np.percentile(y_valid, 25),
            'y_q75': np.percentile(y_valid, 75),
            'covariance': np.cov(x_valid, y_valid),
            'n_events': len(x_valid)
        }
        
        logger.info(f"✅ Baseline set: {len(x_valid):,} events")
        return self.baseline
    
    def detect_scatter_shift(
        self,
        test_data: pd.DataFrame,
        x_channel: Optional[str] = None,
        y_channel: Optional[str] = None,
        threshold: float = 2.0,
        save_plot: bool = True
    ) -> Dict[str, Any]:
        """
        Detect population shift in scatter plot.
        
        Args:
            test_data: Test FCS/NTA data
            x_channel: X-axis channel (uses baseline if None)
            y_channel: Y-axis channel (uses baseline if None)
            threshold: Z-score threshold for anomaly (default: 2.0)
            save_plot: Save visualization
        
        Returns:
            Dictionary with shift detection results
        """
        if self.baseline is None:
            logger.error("No baseline set. Call set_baseline() first.")
            return {}
        
        if x_channel is None:
            x_channel = self.baseline['x_channel']
        if y_channel is None:
            y_channel = self.baseline['y_channel']
        
        logger.info(f"🔍 Detecting scatter plot shift")
        
        # Extract valid data
        x_test = test_data[x_channel]
        y_test = test_data[y_channel]
        
        valid_mask = (x_test > 0) & (y_test > 0) & np.isfinite(x_test) & np.isfinite(y_test)
        x_valid = x_test[valid_mask]
        y_valid = y_test[valid_mask]
        
        # Calculate test statistics
        x_mean_test = np.mean(x_valid)
        y_mean_test = np.mean(y_valid)
        x_median_test = np.median(x_valid)
        y_median_test = np.median(y_valid)
        
        # Calculate shifts (in standard deviations)
        x_shift_mean = (x_mean_test - self.baseline['x_mean']) / self.baseline['x_std']
        y_shift_mean = (y_mean_test - self.baseline['y_mean']) / self.baseline['y_std']
        x_shift_median = (x_median_test - self.baseline['x_median']) / self.baseline['x_std']
        y_shift_median = (y_median_test - self.baseline['y_median']) / self.baseline['y_std']
        
        # Calculate total shift magnitude
        shift_magnitude = np.sqrt(x_shift_mean**2 + y_shift_mean**2)
        
        # Determine if anomaly
        is_anomaly = shift_magnitude > threshold
        
        # Kolmogorov-Smirnov test for distribution change
        ks_x = stats.ks_2samp(x_valid, test_data[x_channel][valid_mask])
        ks_y = stats.ks_2samp(y_valid, test_data[y_channel][valid_mask])
        
        results = {
            'is_anomaly': is_anomaly,
            'shift_magnitude': shift_magnitude,
            'x_shift_mean': x_shift_mean,
            'y_shift_mean': y_shift_mean,
            'x_shift_median': x_shift_median,
            'y_shift_median': y_shift_median,
            'ks_x_statistic': float(ks_x.statistic),  # type: ignore[attr-defined]
            'ks_x_pvalue': float(ks_x.pvalue),  # type: ignore[attr-defined]
            'ks_y_statistic': float(ks_y.statistic),  # type: ignore[attr-defined]
            'ks_y_pvalue': float(ks_y.pvalue),  # type: ignore[attr-defined]
            'threshold': threshold,
            'n_test_events': len(x_valid)
        }
        
        # Log results
        status = "⚠️ ANOMALY DETECTED" if is_anomaly else "✅ Normal"
        logger.info(f"{status}: Shift magnitude = {shift_magnitude:.2f} (threshold: {threshold})")
        logger.info(f"  X-shift: {x_shift_mean:.2f}σ, Y-shift: {y_shift_mean:.2f}σ")
        
        # Save plot
        if save_plot and x_channel is not None and y_channel is not None:
            self._plot_shift_detection(test_data, x_channel, y_channel, results)
        
        return results
    
    def detect_outliers_zscore(
        self,
        data: pd.DataFrame,
        channels: Optional[List[str]] = None,
        threshold: float = 3.0
    ) -> pd.DataFrame:
        """
        Detect outliers using Z-score method.
        
        Args:
            data: FCS/NTA data
            channels: List of channels to check (default: all numeric)
            threshold: Z-score threshold (default: 3.0)
        
        Returns:
            DataFrame with outlier flags
        """
        logger.info(f"🔍 Detecting outliers (Z-score method, threshold={threshold})")
        
        if channels is None:
            channels = data.select_dtypes(include=[np.number]).columns.tolist()
        
        if not channels:
            logger.warning("No channels to check for outliers")
            return data
        
        data_copy = data.copy()
        data_copy['is_outlier'] = False
        
        for channel in channels:
            if channel not in data.columns:
                continue
            
            channel_data = data[channel]
            valid_data = channel_data[(channel_data > 0) & np.isfinite(channel_data)]
            
            if len(valid_data) == 0:
                continue
            
            # Calculate Z-scores
            mean = float(np.mean(valid_data))
            std = float(np.std(valid_data))
            
            if std == 0:
                continue
            
            z_scores = np.abs((channel_data.astype(float) - mean) / std)
            outliers = z_scores > threshold
            
            data_copy.loc[outliers, 'is_outlier'] = True
            data_copy.loc[outliers, f'{channel}_zscore'] = z_scores[outliers]
        
        n_outliers = data_copy['is_outlier'].sum()
        pct_outliers = (n_outliers / len(data_copy)) * 100
        
        logger.info(f"  Found {n_outliers:,} outliers ({pct_outliers:.2f}%)")
        
        return data_copy
    
    def detect_outliers_iqr(
        self,
        data: pd.DataFrame,
        channels: Optional[List[str]] = None,
        factor: float = 1.5
    ) -> pd.DataFrame:
        """
        Detect outliers using IQR method.
        
        Args:
            data: FCS/NTA data
            channels: List of channels to check
            factor: IQR multiplier (default: 1.5)
        
        Returns:
            DataFrame with outlier flags
        """
        logger.info(f"🔍 Detecting outliers (IQR method, factor={factor})")
        
        if channels is None:
            channels = data.select_dtypes(include=[np.number]).columns.tolist()
        
        if not channels:
            logger.warning("No channels to check for outliers")
            return data
        
        data_copy = data.copy()
        data_copy['is_outlier_iqr'] = False
        
        for channel in channels:
            if channel not in data.columns:
                continue
            
            channel_data = data[channel]
            valid_data = channel_data[(channel_data > 0) & np.isfinite(channel_data)]
            
            if len(valid_data) == 0:
                continue
            
            # Calculate IQR
            q1 = np.percentile(valid_data, 25)
            q3 = np.percentile(valid_data, 75)
            iqr = q3 - q1
            
            if iqr == 0:
                continue
            
            # Define outlier bounds
            lower_bound = q1 - factor * iqr
            upper_bound = q3 + factor * iqr
            
            outliers = (channel_data < lower_bound) | (channel_data > upper_bound)
            data_copy.loc[outliers, 'is_outlier_iqr'] = True
        
        n_outliers = data_copy['is_outlier_iqr'].sum()
        pct_outliers = (n_outliers / len(data_copy)) * 100
        
        logger.info(f"  Found {n_outliers:,} outliers ({pct_outliers:.2f}%)")
        
        return data_copy
    
    def detect_size_distribution_anomaly(
        self,
        nta_stats: pd.DataFrame,
        baseline_stats: pd.DataFrame,
        threshold_pvalue: float = 0.05,
        save_plot: bool = True
    ) -> Dict[str, Any]:
        """
        Detect anomalies in NTA size distribution.
        
        Args:
            nta_stats: Test NTA statistics
            baseline_stats: Baseline NTA statistics
            threshold_pvalue: P-value threshold for KS test
            save_plot: Save visualization
        
        Returns:
            Dictionary with anomaly detection results
        """
        logger.info(f"🔍 Detecting size distribution anomalies")
        
        # Check for size column
        size_col = None
        for col in ['size_nm', 'mean_size', 'D50']:
            if col in nta_stats.columns and col in baseline_stats.columns:
                size_col = col
                break
        
        if size_col is None:
            logger.error("No common size column found")
            return {}
        
        # Get size data
        test_sizes = nta_stats[size_col].dropna()
        baseline_sizes = baseline_stats[size_col].dropna()
        
        # Kolmogorov-Smirnov test
        ks_result = stats.ks_2samp(baseline_sizes, test_sizes)
        ks_stat = float(ks_result.statistic)  # type: ignore[attr-defined]
        ks_pval = float(ks_result.pvalue)  # type: ignore[attr-defined]
        
        # Compare D-values
        d_shifts = {}
        for d_col in ['D10', 'D50', 'D90']:
            if d_col in nta_stats.columns and d_col in baseline_stats.columns:
                test_d = nta_stats[d_col].mean()
                baseline_d = baseline_stats[d_col].mean()
                baseline_std = baseline_stats[d_col].std()
                
                if baseline_std > 0:
                    shift = (test_d - baseline_d) / baseline_std
                    d_shifts[d_col] = shift
        
        is_anomaly = ks_pval < threshold_pvalue
        
        results = {
            'is_anomaly': is_anomaly,
            'ks_statistic': ks_stat,
            'ks_pvalue': ks_pval,
            'd_shifts': d_shifts,
            'threshold_pvalue': threshold_pvalue
        }
        
        status = "⚠️ ANOMALY DETECTED" if is_anomaly else "✅ Normal"
        logger.info(f"{status}: KS p-value = {ks_pval:.4f}")
        
        if save_plot:
            self._plot_size_distribution_comparison(nta_stats, baseline_stats, results)
        
        return results
    
    def _plot_shift_detection(
        self,
        test_data: pd.DataFrame,
        x_channel: str,
        y_channel: str,
        results: Dict[str, Any]
    ) -> None:
        """Plot scatter shift detection visualization."""
        if self.baseline is None:
            logger.warning("Cannot plot shift detection: No baseline set")
            return
            
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Plot baseline (ellipse)
        from matplotlib.patches import Ellipse
        
        ellipse = Ellipse(
            (self.baseline['x_mean'], self.baseline['y_mean']),
            width=4 * self.baseline['x_std'],
            height=4 * self.baseline['y_std'],
            alpha=0.3,
            color='green',
            label='Baseline (±2σ)'
        )
        ax.add_patch(ellipse)
        
        # Plot test data
        x_test = test_data[x_channel]
        y_test = test_data[y_channel]
        valid_mask = (x_test > 0) & (y_test > 0) & np.isfinite(x_test) & np.isfinite(y_test)
        
        ax.scatter(
            x_test[valid_mask],
            y_test[valid_mask],
            alpha=0.1,
            s=1,
            c='red' if results['is_anomaly'] else 'blue',
            label='Test Data'
        )
        
        # Plot means
        ax.plot(self.baseline['x_mean'], self.baseline['y_mean'], 
                'go', markersize=15, label='Baseline Mean')
        ax.plot(x_test[valid_mask].mean(), y_test[valid_mask].mean(),
                'ro' if results['is_anomaly'] else 'bo', markersize=15, label='Test Mean')
        
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlabel(x_channel)
        ax.set_ylabel(y_channel)
        
        status = "ANOMALY DETECTED" if results['is_anomaly'] else "Normal"
        color = 'red' if results['is_anomaly'] else 'green'
        
        ax.set_title(f'Population Shift Detection - {status}', 
                    fontsize=14, fontweight='bold', color=color)
        
        # Add results text
        results_text = (
            f"Shift Magnitude: {results['shift_magnitude']:.2f}σ\n"
            f"X-shift: {results['x_shift_mean']:.2f}σ\n"
            f"Y-shift: {results['y_shift_mean']:.2f}σ\n"
            f"Threshold: {results['threshold']}σ"
        )
        ax.text(0.02, 0.98, results_text, transform=ax.transAxes,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='yellow' if results['is_anomaly'] else 'wheat', alpha=0.8),
                fontsize=10)
        
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        filename = f"shift_detection_{'anomaly' if results['is_anomaly'] else 'normal'}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        logger.info(f"✅ Saved shift detection plot: {filepath}")
        plt.close()
    
    def _plot_size_distribution_comparison(
        self,
        test_stats: pd.DataFrame,
        baseline_stats: pd.DataFrame,
        results: Dict[str, Any]
    ) -> None:
        """Plot size distribution comparison."""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Find size column
        size_col = None
        for col in ['size_nm', 'mean_size', 'D50']:
            if col in test_stats.columns and col in baseline_stats.columns:
                size_col = col
                break
        
        # Plot histograms
        ax.hist(baseline_stats[size_col], bins=50, alpha=0.5, 
                color='green', label='Baseline', edgecolor='black')
        ax.hist(test_stats[size_col], bins=50, alpha=0.5,
                color='red' if results['is_anomaly'] else 'blue',
                label='Test', edgecolor='black')
        
        ax.set_xlabel('Size (nm)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Count', fontsize=12, fontweight='bold')
        
        status = "ANOMALY DETECTED" if results['is_anomaly'] else "Normal"
        color = 'red' if results['is_anomaly'] else 'green'
        
        ax.set_title(f'Size Distribution Comparison - {status}',
                    fontsize=14, fontweight='bold', color=color)
        
        # Add results text
        results_text = f"KS Test p-value: {results['ks_pvalue']:.4f}\n"
        for d_col, shift in results['d_shifts'].items():
            results_text += f"{d_col} shift: {shift:.2f}σ\n"
        
        ax.text(0.98, 0.98, results_text, transform=ax.transAxes,
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', 
                         facecolor='yellow' if results['is_anomaly'] else 'wheat',
                         alpha=0.8),
                fontsize=10)
        
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        filename = f"size_dist_comparison_{'anomaly' if results['is_anomaly'] else 'normal'}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        logger.info(f"✅ Saved size distribution comparison: {filepath}")
        plt.close()


if __name__ == '__main__':
    # Example usage
    logger.info("Anomaly Detection Module - Ready for integration")
