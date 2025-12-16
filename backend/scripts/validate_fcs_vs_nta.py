"""
Cross-Validation: FCS (Mie-based) vs NTA Size Measurements
===========================================================

Purpose: Validate that Mie-based FCS particle sizes correlate with independent
         NTA measurements to ensure scientific accuracy of sizing algorithm.

Date: November 18, 2025
Status: Production ready

Expected Results:
- Correlation coefficient R > 0.8 (strong correlation)
- Absolute error < ±20% (acceptable for biological samples)
- No systematic bias (slope ≈ 1.0, intercept ≈ 0)

Usage:
    python scripts/validate_fcs_vs_nta.py --fcs data/processed_mie --nta data/parquet/nta
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from loguru import logger
import argparse
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_fcs_sizes(fcs_file: Path) -> pd.DataFrame:
    """Load FCS data and extract size statistics."""
    logger.info(f"Loading FCS: {fcs_file.name}")
    df = pd.read_parquet(fcs_file)
    
    if 'particle_size_nm' not in df.columns:
        raise ValueError(f"No particle_size_nm column in {fcs_file.name}")
    
    # Calculate statistics
    sizes = df['particle_size_nm'].dropna()
    
    return pd.DataFrame({
        'file': [fcs_file.stem],
        'source': ['FCS'],
        'n_events': [len(sizes)],
        'mean_nm': [sizes.mean()],
        'median_nm': [sizes.median()],
        'std_nm': [sizes.std()],
        'q25_nm': [sizes.quantile(0.25)],
        'q75_nm': [sizes.quantile(0.75)],
        'min_nm': [sizes.min()],
        'max_nm': [sizes.max()]
    })


def load_nta_sizes(nta_file: Path) -> pd.DataFrame:
    """Load NTA data and extract size statistics."""
    logger.info(f"Loading NTA: {nta_file.name}")
    df = pd.read_parquet(nta_file)
    
    # NTA files have size_nm column with particle sizes
    if 'size_nm' in df.columns:
        sizes = df['size_nm'].dropna()
    elif 'diameter_nm' in df.columns:
        sizes = df['diameter_nm'].dropna()
    else:
        raise ValueError(f"No size column found in {nta_file.name}")
    
    return pd.DataFrame({
        'file': [nta_file.stem],
        'source': ['NTA'],
        'n_events': [len(sizes)],
        'mean_nm': [sizes.mean()],
        'median_nm': [sizes.median()],
        'std_nm': [sizes.std()],
        'q25_nm': [sizes.quantile(0.25)],
        'q75_nm': [sizes.quantile(0.75)],
        'min_nm': [sizes.min()],
        'max_nm': [sizes.max()]
    })


def match_samples(fcs_files: List[Path], nta_files: List[Path]) -> List[Tuple[Path, Path]]:
    """
    Match FCS and NTA files from same samples.
    
    Uses fuzzy matching on filename stems (removes extensions and common suffixes).
    """
    logger.info("Matching FCS and NTA files from same samples...")
    
    def normalize_name(path: Path) -> str:
        """Normalize filename for matching."""
        name = path.stem.lower()
        # Remove common suffixes
        for suffix in ['_fcs', '_nta', '_processed', '_events', '_stats']:
            name = name.replace(suffix, '')
        return name
    
    fcs_dict = {normalize_name(f): f for f in fcs_files}
    nta_dict = {normalize_name(f): f for f in nta_files}
    
    # Find matches
    matches = []
    for name, fcs_file in fcs_dict.items():
        if name in nta_dict:
            nta_file = nta_dict[name]
            matches.append((fcs_file, nta_file))
            logger.info(f"  ✓ Matched: {fcs_file.name} ↔ {nta_file.name}")
    
    logger.info(f"Found {len(matches)} matched sample pairs")
    return matches


def calculate_correlation(fcs_stats: pd.DataFrame, nta_stats: pd.DataFrame) -> Dict[str, float]:  # type: ignore[return-value]
    """Calculate correlation metrics between FCS and NTA measurements.
    
    WHAT THIS DOES:
    ----------------
    Validates that FCS size measurements (calculated from Mie scattering) agree
    with independent NTA size measurements (from Brownian motion tracking).
    
    WHY THIS IS CRITICAL:
    ---------------------
    - FCS sizes are CALCULATED using physics model (Mie scatter theory)
    - NTA sizes are DIRECTLY MEASURED (tracking particle motion)
    - If they DON'T agree → FCS calibration is wrong → don't trust results
    - Strong correlation (R > 0.8) validates the Mie scatter approach
    
    HOW IT WORKS:
    --------------
    1. Pearson correlation (R):
       - Measures LINEAR relationship between FCS and NTA sizes
       - R = 1.0: perfect correlation
       - R > 0.8: excellent (typical for biological data)
       - R < 0.6: poor (check calibration!)
    
    2. Spearman correlation (rho):
       - RANK-BASED correlation (robust to outliers)
       - Good if relationship is monotonic but not linear
    
    3. Linear regression (y = slope*x + intercept):
       - Fits line: FCS_size = slope * NTA_size + intercept
       - Ideal: slope ≈ 1.0, intercept ≈ 0 (perfect agreement)
       - R²: fraction of variance explained (0-1, higher = better)
    
    4. Error metrics:
       - RMSE (Root Mean Square Error): average magnitude of errors (nm)
       - Mean error: systematic bias (FCS - NTA)
       - MAPE (Mean Absolute Percentage Error): relative accuracy (%)
    
    ACCEPTANCE CRITERIA:
    --------------------
    ✅ GOOD validation:
       - Pearson R > 0.8
       - |Mean error| < 10nm
       - MAPE < 20%
       - Slope ≈ 0.8-1.2
    """
    
    # Extract matched measurements
    # Use median size as representative value for each sample
    fcs_median = fcs_stats['median_nm'].values
    nta_median = nta_stats['median_nm'].values
    
    # Pearson correlation
    r_pearson, p_pearson = stats.pearsonr(fcs_median, nta_median)
    
    # Spearman correlation (rank-based, robust to outliers)
    r_spearman, p_spearman = stats.spearmanr(fcs_median, nta_median)
    
    # Linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(nta_median, fcs_median)
    
    # Calculate absolute errors
    errors = np.asarray(fcs_median) - np.asarray(nta_median)
    relative_errors = 100 * errors / np.asarray(nta_median)
    
    # RMSE
    rmse = np.sqrt(np.mean(errors**2))
    
    # Mean absolute percentage error
    mape = np.mean(np.abs(relative_errors))
    
    return {
        'n_samples': len(fcs_median),
        'pearson_r': r_pearson,
        'pearson_p': p_pearson,
        'spearman_r': r_spearman,
        'spearman_p': p_spearman,
        'regression_slope': slope,
        'regression_intercept': intercept,
        'regression_r2': float(r_value**2),  # type: ignore[operator]
        'rmse_nm': rmse,
        'mean_error_nm': np.mean(errors),
        'median_error_nm': np.median(errors),
        'std_error_nm': np.std(errors),
        'mape_pct': mape,
        'max_abs_error_nm': np.max(np.abs(errors))
    }


def plot_validation(
    fcs_stats: pd.DataFrame,
    nta_stats: pd.DataFrame,
    metrics: Dict[str, float],
    output_file: Path
) -> None:
    """Create validation plots comparing FCS and NTA."""
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    fcs_median = fcs_stats['median_nm'].values
    nta_median = nta_stats['median_nm'].values
    errors = np.asarray(fcs_median) - np.asarray(nta_median)
    relative_errors = 100 * errors / np.asarray(nta_median)
    
    # Plot 1: Scatter plot with regression line
    ax1 = axes[0, 0]
    ax1.scatter(nta_median, fcs_median, alpha=0.6, s=100, edgecolors='black')
    
    # Regression line
    x_range = np.array([float(np.min(np.asarray(nta_median))), float(np.max(np.asarray(nta_median)))])
    y_pred = metrics['regression_slope'] * x_range + metrics['regression_intercept']
    ax1.plot(x_range, y_pred, 'r--', linewidth=2, label=f'Fit: y={metrics["regression_slope"]:.2f}x+{metrics["regression_intercept"]:.1f}')
    
    # Identity line
    ax1.plot(x_range, x_range, 'k-', linewidth=1, alpha=0.5, label='Perfect agreement')
    
    ax1.set_xlabel('NTA Median Size (nm)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('FCS Median Size (nm)', fontsize=12, fontweight='bold')
    ax1.set_title(f'FCS vs NTA Correlation (R² = {metrics["regression_r2"]:.3f})', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Bland-Altman plot
    ax2 = axes[0, 1]
    mean_sizes = (np.asarray(fcs_median) + np.asarray(nta_median)) / 2
    ax2.scatter(mean_sizes, errors, alpha=0.6, s=100, edgecolors='black')
    ax2.axhline(np.mean(errors), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(errors):.1f} nm')
    ax2.axhline(np.mean(errors) + 1.96*np.std(errors), color='gray', linestyle=':', linewidth=1.5, label='±1.96 SD')
    ax2.axhline(np.mean(errors) - 1.96*np.std(errors), color='gray', linestyle=':', linewidth=1.5)
    ax2.axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.3)
    
    ax2.set_xlabel('Mean Size (FCS + NTA) / 2 (nm)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Difference (FCS - NTA) (nm)', fontsize=12, fontweight='bold')
    ax2.set_title('Bland-Altman Plot', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Error distribution
    ax3 = axes[1, 0]
    ax3.hist(relative_errors, bins=20, edgecolor='black', alpha=0.7)
    ax3.axvline(0, color='red', linestyle='--', linewidth=2, label='Zero error')
    ax3.axvline(np.mean(relative_errors), color='blue', linestyle='--', linewidth=2, label=f'Mean: {np.mean(relative_errors):.1f}%')
    ax3.set_xlabel('Relative Error (%)', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Frequency', fontsize=12, fontweight='bold')
    ax3.set_title(f'Error Distribution (MAPE = {metrics["mape_pct"]:.1f}%)', fontsize=14, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Plot 4: Summary text
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    summary_text = f"""
    VALIDATION SUMMARY
    ==================
    
    Sample Size: {metrics['n_samples']} matched pairs
    
    Correlation:
      • Pearson R = {metrics['pearson_r']:.3f} (p = {metrics['pearson_p']:.2e})
      • Spearman R = {metrics['spearman_r']:.3f} (p = {metrics['spearman_p']:.2e})
      • R² = {metrics['regression_r2']:.3f}
    
    Regression:
      • Slope = {metrics['regression_slope']:.3f}
      • Intercept = {metrics['regression_intercept']:.1f} nm
    
    Errors:
      • RMSE = {metrics['rmse_nm']:.1f} nm
      • Mean = {metrics['mean_error_nm']:.1f} ± {metrics['std_error_nm']:.1f} nm
      • Median = {metrics['median_error_nm']:.1f} nm
      • MAPE = {metrics['mape_pct']:.1f}%
      • Max absolute = {metrics['max_abs_error_nm']:.1f} nm
    
    Interpretation:
      {'✅ EXCELLENT correlation (R > 0.8)' if metrics['pearson_r'] > 0.8 else '⚠️ Moderate correlation' if metrics['pearson_r'] > 0.6 else '❌ Poor correlation'}
      {'✅ Low systematic bias' if abs(metrics['mean_error_nm']) < 10 else '⚠️ Moderate bias' if abs(metrics['mean_error_nm']) < 20 else '❌ High bias'}
      {'✅ Good accuracy (MAPE < 20%)' if metrics['mape_pct'] < 20 else '⚠️ Moderate accuracy' if metrics['mape_pct'] < 30 else '❌ Poor accuracy'}
    """
    
    ax4.text(0.1, 0.5, summary_text, fontsize=11, family='monospace', verticalalignment='center')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    logger.info(f"📊 Validation plot saved: {output_file}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Cross-validate FCS and NTA size measurements")
    parser.add_argument(
        "--fcs",
        type=str,
        default="data/processed",
        help="Directory containing FCS parquet files"
    )
    parser.add_argument(
        "--nta",
        type=str,
        default="data/parquet/nta",
        help="Directory containing NTA parquet files"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="figures/validation_fcs_vs_nta.png",
        help="Output plot file"
    )
    
    args = parser.parse_args()
    
    # Setup paths
    fcs_dir = Path(args.fcs)
    nta_dir = Path(args.nta)
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    log_file = f"logs/validation_fcs_nta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    Path("logs").mkdir(exist_ok=True)
    logger.add(log_file, rotation="10 MB")
    
    logger.info("=" * 80)
    logger.info("FCS vs NTA SIZE VALIDATION")
    logger.info("=" * 80)
    logger.info(f"FCS directory: {fcs_dir}")
    logger.info(f"NTA directory: {nta_dir}")
    logger.info("=" * 80)
    
    # Find files
    fcs_files = list(fcs_dir.rglob("*.parquet"))
    nta_files = list(nta_dir.rglob("*.parquet"))
    
    logger.info(f"Found {len(fcs_files)} FCS files")
    logger.info(f"Found {len(nta_files)} NTA files")
    
    if len(fcs_files) == 0 or len(nta_files) == 0:
        logger.error("No files found!")
        return
    
    # Match samples
    matches = match_samples(fcs_files, nta_files)
    
    if len(matches) == 0:
        logger.error("No matched samples found!")
        logger.info("FCS files: " + ", ".join(f.stem for f in fcs_files[:5]))
        logger.info("NTA files: " + ", ".join(f.stem for f in nta_files[:5]))
        return
    
    # Load and compare
    fcs_stats_list = []
    nta_stats_list = []
    
    for fcs_file, nta_file in matches:
        try:
            fcs_stats = load_fcs_sizes(fcs_file)
            nta_stats = load_nta_sizes(nta_file)
            
            fcs_stats_list.append(fcs_stats)
            nta_stats_list.append(nta_stats)
            
            logger.info(f"  FCS median: {fcs_stats['median_nm'].iloc[0]:.1f} nm")
            logger.info(f"  NTA median: {nta_stats['median_nm'].iloc[0]:.1f} nm")
            logger.info(f"  Difference: {fcs_stats['median_nm'].iloc[0] - nta_stats['median_nm'].iloc[0]:.1f} nm")
            
        except Exception as e:
            logger.error(f"Failed to process pair: {e}")
    
    if len(fcs_stats_list) == 0:
        logger.error("No valid sample pairs!")
        return
    
    # Combine stats
    fcs_stats = pd.concat(fcs_stats_list, ignore_index=True)
    nta_stats = pd.concat(nta_stats_list, ignore_index=True)
    
    # Calculate correlation
    logger.info("\n" + "=" * 80)
    logger.info("CALCULATING CORRELATION METRICS")
    logger.info("=" * 80)
    
    metrics = calculate_correlation(fcs_stats, nta_stats)
    
    # Print results
    logger.info(f"\n📊 VALIDATION RESULTS:")
    logger.info(f"  Samples: {metrics['n_samples']}")
    logger.info(f"  Pearson R: {metrics['pearson_r']:.3f} (p={metrics['pearson_p']:.2e})")
    logger.info(f"  Spearman R: {metrics['spearman_r']:.3f} (p={metrics['spearman_p']:.2e})")
    logger.info(f"  R²: {metrics['regression_r2']:.3f}")
    logger.info(f"  Regression: y = {metrics['regression_slope']:.3f}x + {metrics['regression_intercept']:.1f}")
    logger.info(f"  RMSE: {metrics['rmse_nm']:.1f} nm")
    logger.info(f"  Mean error: {metrics['mean_error_nm']:.1f} ± {metrics['std_error_nm']:.1f} nm")
    logger.info(f"  MAPE: {metrics['mape_pct']:.1f}%")
    
    # Interpretation
    logger.info(f"\n🎯 INTERPRETATION:")
    if metrics['pearson_r'] > 0.8:
        logger.info("  ✅ EXCELLENT correlation between FCS and NTA")
    elif metrics['pearson_r'] > 0.6:
        logger.info("  ⚠️ Moderate correlation - check calibration")
    else:
        logger.info("  ❌ Poor correlation - review methodology")
    
    if abs(metrics['mean_error_nm']) < 10:
        logger.info("  ✅ Low systematic bias")
    elif abs(metrics['mean_error_nm']) < 20:
        logger.info("  ⚠️ Moderate systematic bias")
    else:
        logger.info("  ❌ High systematic bias - calibration needed")
    
    if metrics['mape_pct'] < 20:
        logger.info("  ✅ Good accuracy (MAPE < 20%)")
    elif metrics['mape_pct'] < 30:
        logger.info("  ⚠️ Moderate accuracy")
    else:
        logger.info("  ❌ Poor accuracy")
    
    # Create plot
    logger.info(f"\n📈 Generating validation plots...")
    plot_validation(fcs_stats, nta_stats, metrics, output_file)
    
    # Save detailed results
    results_csv = output_file.parent / "validation_results.csv"
    combined_stats = pd.merge(
        fcs_stats, nta_stats,
        left_on='file', right_on='file',
        suffixes=('_fcs', '_nta')
    )
    combined_stats['error_nm'] = combined_stats['median_nm_fcs'] - combined_stats['median_nm_nta']
    combined_stats['relative_error_pct'] = 100 * combined_stats['error_nm'] / combined_stats['median_nm_nta']
    combined_stats.to_csv(results_csv, index=False)
    logger.info(f"📋 Detailed results saved: {results_csv}")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ VALIDATION COMPLETE")
    logger.info(f"📋 Log: {log_file}")
    logger.info(f"📊 Plot: {output_file}")
    logger.info(f"📋 Results: {results_csv}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
