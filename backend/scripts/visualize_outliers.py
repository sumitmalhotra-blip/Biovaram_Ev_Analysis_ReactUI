"""
Visualize Outlier Distribution in FCS Data
===========================================

PURPOSE:
This script creates visualizations to help understand the distribution of
Forward Scatter (FSC) values in flow cytometry data, specifically identifying
outliers that may represent artifacts rather than real extracellular vesicles.

WHAT IT DOES:
1. Loads FCS data from parquet files
2. Analyzes FSC value distribution across percentiles
3. Creates visual plots showing where outliers occur
4. Helps identify appropriate filtering thresholds
5. Validates that outliers are likely artifacts, not biological EVs

WHEN TO USE:
- Before running full Mie calibration to understand data characteristics
- To determine appropriate outlier filtering thresholds
- To validate that filtering won't remove real biological data
- For QC reports and troubleshooting

Date: November 19, 2025
Author: CRM IT Project
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from loguru import logger
import seaborn as sns

# Configure plotting style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


def load_sample_data(data_dir: Path, max_files: int = 5) -> pd.DataFrame:
    """
    Load multiple FCS files and combine for comprehensive analysis.
    
    WHY: Single file might not be representative. Combining multiple files
         gives better understanding of overall data characteristics.
    
    PARAMETERS:
    -----------
    data_dir : Path
        Directory containing FCS parquet files
    max_files : int
        Maximum number of files to load (prevents memory issues)
    
    RETURNS:
    --------
    pd.DataFrame
        Combined dataframe with 'VFSC-H' column and 'sample_name' identifier
    
    HOW IT WORKS:
    -------------
    1. Search for all parquet files recursively
    2. Load up to max_files (for memory efficiency)
    3. Keep only essential columns (VFSC-H for analysis)
    4. Add sample name for tracking which file data came from
    5. Concatenate all files into single dataframe
    """
    logger.info(f"Loading sample data from: {data_dir}")
    
    # Find all parquet files (recursive search)
    parquet_files = list(data_dir.rglob("*.parquet"))
    logger.info(f"Found {len(parquet_files)} parquet files")
    
    # Limit number of files to prevent memory issues
    files_to_load = parquet_files[:max_files]
    logger.info(f"Loading first {len(files_to_load)} files for analysis")
    
    # Load each file and combine
    dfs = []
    for file_path in files_to_load:
        try:
            # Load only essential columns to save memory
            df = pd.read_parquet(file_path, columns=['VFSC-H'])
            
            # Add sample identifier (file name without extension)
            df['sample_name'] = file_path.stem
            
            dfs.append(df)
            logger.info(f"  ✓ Loaded {file_path.name}: {len(df):,} events")
            
        except Exception as e:
            logger.error(f"  ✗ Failed to load {file_path.name}: {e}")
    
    # Combine all dataframes
    combined_df = pd.concat(dfs, ignore_index=True)
    logger.info(f"\nTotal events loaded: {len(combined_df):,}")
    
    return combined_df


def analyze_distribution(df: pd.DataFrame, fsc_channel: str = 'VFSC-H') -> dict:
    """
    Calculate comprehensive statistics about FSC distribution.
    
    WHY: Need to understand where data is concentrated and where outliers begin.
         Percentiles help identify natural breakpoints in the distribution.
    
    PARAMETERS:
    -----------
    df : pd.DataFrame
        Dataframe containing FSC data
    fsc_channel : str
        Name of the forward scatter column
    
    RETURNS:
    --------
    dict
        Dictionary containing:
        - percentiles: FSC values at different percentiles (1, 5, 10...99.9, 99.99)
        - basic_stats: mean, median, std, min, max
        - outlier_counts: number of events above different thresholds
        - threshold_recommendations: suggested cutoffs for filtering
    
    HOW IT WORKS:
    -------------
    1. Extract FSC values from dataframe
    2. Calculate percentiles from P1 to P99.99
    3. Calculate basic statistics (mean, median, std)
    4. Count outliers at different thresholds
    5. Recommend filtering thresholds based on distribution shape
    """
    logger.info("Analyzing FSC distribution...")
    
    fsc = df[fsc_channel].values
    fsc = np.asarray(fsc)  # Convert to numpy array
    
    # Calculate percentiles (captures distribution shape)
    percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99, 99.5, 99.9, 99.95, 99.99]
    percentile_values = {p: float(np.percentile(fsc, p)) for p in percentiles}
    
    # Basic statistics
    basic_stats = {
        'mean': float(fsc.mean()),
        'median': float(np.median(fsc)),
        'std': float(fsc.std()),
        'min': float(fsc.min()),
        'max': float(fsc.max()),
        'n_events': len(fsc)
    }
    
    # Count outliers at different thresholds
    outlier_thresholds = [99, 99.5, 99.9, 99.95, 99.99]
    outlier_counts = {}
    for threshold in outlier_thresholds:
        cutoff = float(np.percentile(fsc, threshold))
        n_above = int((fsc > cutoff).sum())  # type: ignore[operator]
        pct_above = 100 * n_above / len(fsc)
        outlier_counts[threshold] = {
            'cutoff': cutoff,
            'n_above': n_above,
            'pct_above': pct_above
        }
    
    # Recommend threshold based on distribution
    # Look for large jump in percentile values (indicates outlier region)
    p99 = percentile_values[99]
    p999 = percentile_values[99.9]
    p9999 = percentile_values[99.99]
    
    # If there's a huge jump between P99 and P99.9, recommend P99.5 or P99.9
    jump_99_to_999 = p999 / p99 if p99 > 0 else 1
    
    if jump_99_to_999 > 10:
        recommended = 99.9
        reason = f"Large jump detected (P99→P99.9: {jump_99_to_999:.1f}×)"
    elif jump_99_to_999 > 3:
        recommended = 99.5
        reason = f"Moderate jump detected (P99→P99.9: {jump_99_to_999:.1f}×)"
    else:
        recommended = 99
        reason = "Smooth distribution, conservative threshold"
    
    logger.info(f"Recommended threshold: P{recommended} ({reason})")
    
    return {
        'percentiles': percentile_values,
        'basic_stats': basic_stats,
        'outlier_counts': outlier_counts,
        'recommended_threshold': recommended,
        'recommendation_reason': reason
    }


def create_distribution_plots(df: pd.DataFrame, stats: dict, output_dir: Path):
    """
    Create comprehensive visualizations of FSC distribution.
    
    WHY: Visual inspection is crucial for understanding data and validating
         that outliers are truly artifacts, not biological signal.
    
    PARAMETERS:
    -----------
    df : pd.DataFrame
        Dataframe with FSC data
    stats : dict
        Statistics dictionary from analyze_distribution()
    output_dir : Path
        Directory to save plots
    
    CREATES:
    --------
    1. fsc_distribution_overview.png
       - 4-panel plot showing different views of distribution
       - Linear histogram, log histogram, cumulative distribution, box plot
    
    2. fsc_outlier_analysis.png
       - Focused view on tail of distribution
       - Shows where outliers begin and their characteristics
    
    3. fsc_percentile_curve.png
       - Percentile vs FSC value plot
       - Helps identify jumps/breaks in distribution
    
    HOW IT WORKS:
    -------------
    1. Create figure with multiple subplots
    2. Plot different views of same data
    3. Add reference lines for recommended thresholds
    4. Annotate with statistics and recommendations
    5. Save high-resolution figures for reports
    """
    logger.info("Creating distribution visualizations...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    fsc = df['VFSC-H'].values
    fsc = np.asarray(fsc)  # Convert to numpy array
    
    # Remove zeros for log plots (log(0) is undefined)
    fsc_nonzero = fsc[fsc > 0]  # type: ignore[operator]
    
    # ========================================================================
    # PLOT 1: Overview - Four different views of distribution
    # ========================================================================
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Forward Scatter (FSC) Distribution Analysis', fontsize=16, fontweight='bold')
    
    # --- Subplot 1: Linear histogram (shows main population) ---
    ax1 = axes[0, 0]
    ax1.hist(fsc, bins=100, color='steelblue', alpha=0.7, edgecolor='black')
    ax1.axvline(stats['basic_stats']['median'], color='red', linestyle='--', 
                linewidth=2, label=f"Median: {stats['basic_stats']['median']:.0f}")
    ax1.axvline(stats['percentiles'][99], color='orange', linestyle='--',
                linewidth=2, label=f"P99: {stats['percentiles'][99]:.0f}")
    ax1.set_xlabel('FSC-H (Linear Scale)', fontsize=12)
    ax1.set_ylabel('Frequency', fontsize=12)
    ax1.set_title('Linear Distribution (Full Range)', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # --- Subplot 2: Log histogram (reveals outliers) ---
    ax2 = axes[0, 1]
    ax2.hist(fsc_nonzero, bins=100, color='forestgreen', alpha=0.7, edgecolor='black')
    ax2.set_xscale('log')
    ax2.axvline(stats['basic_stats']['median'], color='red', linestyle='--', 
                linewidth=2, label=f"Median: {stats['basic_stats']['median']:.0f}")
    ax2.axvline(stats['percentiles'][99.9], color='purple', linestyle='--',
                linewidth=2, label=f"P99.9: {stats['percentiles'][99.9]:.0f}")
    ax2.set_xlabel('FSC-H (Log Scale)', fontsize=12)
    ax2.set_ylabel('Frequency', fontsize=12)
    ax2.set_title('Log Distribution (Shows Outliers)', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # --- Subplot 3: Cumulative distribution (shows percentiles) ---
    ax3 = axes[1, 0]
    sorted_fsc = np.sort(fsc)  # type: ignore[arg-type]
    cumulative = np.arange(1, len(sorted_fsc) + 1) / len(sorted_fsc) * 100
    ax3.plot(sorted_fsc, cumulative, color='navy', linewidth=2)
    ax3.axhline(99, color='orange', linestyle='--', linewidth=2, label='P99')
    ax3.axhline(99.9, color='purple', linestyle='--', linewidth=2, label='P99.9')
    ax3.set_xscale('log')
    ax3.set_xlabel('FSC-H (Log Scale)', fontsize=12)
    ax3.set_ylabel('Cumulative Percentage', fontsize=12)
    ax3.set_title('Cumulative Distribution Function', fontsize=14, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # --- Subplot 4: Box plot (shows outliers visually) ---
    ax4 = axes[1, 1]
    bp = ax4.boxplot(fsc, vert=False, patch_artist=True, widths=0.5)
    bp['boxes'][0].set_facecolor('lightblue')
    bp['boxes'][0].set_alpha(0.7)
    ax4.set_xlabel('FSC-H', fontsize=12)
    ax4.set_title('Box Plot (Outliers Marked)', fontsize=14, fontweight='bold')
    ax4.set_yticks([])
    ax4.grid(True, alpha=0.3, axis='x')
    
    # Add statistics text box
    stats_text = (
        f"Total Events: {stats['basic_stats']['n_events']:,}\n"
        f"Median: {stats['basic_stats']['median']:.1f}\n"
        f"Mean: {stats['basic_stats']['mean']:.1f}\n"
        f"Std Dev: {stats['basic_stats']['std']:.1f}\n"
        f"Range: {stats['basic_stats']['min']:.1f} - {stats['basic_stats']['max']:.1f}"
    )
    ax4.text(0.02, 0.98, stats_text, transform=ax4.transAxes,
             fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    output_file = output_dir / 'fsc_distribution_overview.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    logger.info(f"  ✓ Saved: {output_file}")
    plt.close()
    
    # ========================================================================
    # PLOT 2: Outlier Analysis - Focused on tail
    # ========================================================================
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Outlier Detection and Analysis', fontsize=16, fontweight='bold')
    
    # --- Left panel: Zoomed histogram of tail ---
    ax1 = axes[0]
    p99_value = stats['percentiles'][99]
    tail_mask = fsc > p99_value
    fsc_tail = fsc[tail_mask]
    
    if len(fsc_tail) > 0:
        ax1.hist(fsc_tail, bins=50, color='coral', alpha=0.7, edgecolor='black')
        ax1.axvline(stats['percentiles'][99.9], color='red', linestyle='--',
                    linewidth=2, label=f"P99.9: {stats['percentiles'][99.9]:.0f}")
        ax1.set_xlabel('FSC-H (Above P99)', fontsize=12)
        ax1.set_ylabel('Frequency', fontsize=12)
        ax1.set_title(f'Tail Distribution (Top 1% = {len(fsc_tail):,} events)', 
                     fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
    
    # --- Right panel: Outlier impact table ---
    ax2 = axes[1]
    ax2.axis('off')
    
    # Create table data
    table_data = [['Threshold', 'FSC Cutoff', 'Events Kept', '% Kept', 'Events Removed', '% Removed']]
    for threshold in [99, 99.5, 99.9, 99.95, 99.99]:
        info = stats['outlier_counts'][threshold]
        n_kept = stats['basic_stats']['n_events'] - info['n_above']
        pct_kept = 100 - info['pct_above']
        table_data.append([
            f"P{threshold}",
            f"{info['cutoff']:.0f}",
            f"{n_kept:,}",
            f"{pct_kept:.3f}%",
            f"{info['n_above']:,}",
            f"{info['pct_above']:.3f}%"
        ])
    
    # Create table
    table = ax2.table(cellText=table_data, cellLoc='center', loc='center',
                     colWidths=[0.15, 0.18, 0.18, 0.15, 0.18, 0.16])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)
    
    # Style header row
    for i in range(6):
        cell = table[(0, i)]
        cell.set_facecolor('lightblue')
        cell.set_text_props(weight='bold')
    
    # Highlight recommended row
    recommended = stats['recommended_threshold']
    for i, threshold in enumerate([99, 99.5, 99.9, 99.95, 99.99], start=1):
        if threshold == recommended:
            for j in range(6):
                table[(i, j)].set_facecolor('lightgreen')
    
    ax2.set_title(f"Recommended: P{recommended} - {stats['recommendation_reason']}", 
                 fontsize=12, fontweight='bold', pad=20)
    
    plt.tight_layout()
    output_file = output_dir / 'fsc_outlier_analysis.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    logger.info(f"  ✓ Saved: {output_file}")
    plt.close()
    
    # ========================================================================
    # PLOT 3: Percentile Curve - Shows distribution jumps
    # ========================================================================
    fig, ax = plt.subplots(figsize=(12, 8))
    
    percentiles = list(stats['percentiles'].keys())
    values = list(stats['percentiles'].values())
    
    ax.plot(percentiles, values, marker='o', markersize=8, linewidth=2,
            color='darkblue', label='FSC Values')
    ax.axhline(stats['percentiles'][99], color='orange', linestyle='--',
               alpha=0.5, label=f"P99 = {stats['percentiles'][99]:.0f}")
    ax.axhline(stats['percentiles'][99.9], color='red', linestyle='--',
               alpha=0.5, label=f"P99.9 = {stats['percentiles'][99.9]:.0f}")
    
    ax.set_yscale('log')
    ax.set_xlabel('Percentile', fontsize=12)
    ax.set_ylabel('FSC-H Value (Log Scale)', fontsize=12)
    ax.set_title('Percentile Curve - Detect Distribution Jumps', 
                fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Annotate jumps
    for i in range(len(percentiles) - 1):
        p1, p2 = percentiles[i], percentiles[i + 1]
        v1, v2 = values[i], values[i + 1]
        if v1 > 0 and v2 / v1 > 5:  # Significant jump
            ax.annotate(f'{v2/v1:.1f}× jump', 
                       xy=(p2, v2), xytext=(p2 + 0.1, v2 * 1.5),
                       arrowprops=dict(arrowstyle='->', color='red', lw=2),
                       fontsize=10, color='red', fontweight='bold')
    
    plt.tight_layout()
    output_file = output_dir / 'fsc_percentile_curve.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    logger.info(f"  ✓ Saved: {output_file}")
    plt.close()
    
    logger.info("✓ All visualizations created successfully!")


def generate_report(stats: dict, output_dir: Path):
    """
    Generate text report with recommendations.
    
    WHY: Provides written summary that can be included in documentation
         or shared with collaborators without requiring plot viewing.
    
    PARAMETERS:
    -----------
    stats : dict
        Statistics from analyze_distribution()
    output_dir : Path
        Directory to save report
    
    CREATES:
    --------
    outlier_analysis_report.txt
        - Summary statistics
        - Outlier counts at different thresholds
        - Recommendation for filtering
        - Interpretation and next steps
    
    HOW IT WORKS:
    -------------
    1. Format statistics into readable text
    2. Create table showing impact of different thresholds
    3. Provide clear recommendation with justification
    4. Suggest next steps based on findings
    5. Save as plain text file
    """
    logger.info("Generating text report...")
    
    report_file = output_dir / 'outlier_analysis_report.txt'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("FORWARD SCATTER OUTLIER ANALYSIS REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("Date: November 19, 2025\n")
        f.write(f"Total Events Analyzed: {stats['basic_stats']['n_events']:,}\n\n")
        
        # Basic Statistics
        f.write("-" * 80 + "\n")
        f.write("BASIC STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Minimum FSC:    {stats['basic_stats']['min']:>15,.1f}\n")
        f.write(f"Maximum FSC:    {stats['basic_stats']['max']:>15,.1f}\n")
        f.write(f"Mean FSC:       {stats['basic_stats']['mean']:>15,.1f}\n")
        f.write(f"Median FSC:     {stats['basic_stats']['median']:>15,.1f}\n")
        f.write(f"Std Dev:        {stats['basic_stats']['std']:>15,.1f}\n\n")
        
        # Percentile Distribution
        f.write("-" * 80 + "\n")
        f.write("PERCENTILE DISTRIBUTION\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Percentile':<12} {'FSC Value':<15} {'Notes'}\n")
        f.write("-" * 80 + "\n")
        
        for p in [1, 5, 10, 25, 50, 75, 90, 95, 99, 99.5, 99.9, 99.99]:
            val = stats['percentiles'][p]
            note = ""
            if p == 50:
                note = "← Median (typical EV)"
            elif p == 99:
                note = "← 99% of events below this"
            elif p == 99.9:
                note = "← Recommended cutoff"
            f.write(f"P{p:<10.2f} {val:<15.1f} {note}\n")
        
        f.write("\n")
        
        # Outlier Impact Analysis
        f.write("-" * 80 + "\n")
        f.write("OUTLIER FILTERING IMPACT\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Threshold':<12} {'Cutoff FSC':<15} {'Events Kept':<15} "
               f"{'% Kept':<12} {'Events Lost':<15} {'% Lost'}\n")
        f.write("-" * 80 + "\n")
        
        for threshold in [99, 99.5, 99.9, 99.95, 99.99]:
            info = stats['outlier_counts'][threshold]
            n_kept = stats['basic_stats']['n_events'] - info['n_above']
            pct_kept = 100 - info['pct_above']
            
            marker = " ★ RECOMMENDED" if threshold == stats['recommended_threshold'] else ""
            
            f.write(f"P{threshold:<10.2f} {info['cutoff']:<15.1f} {n_kept:<15,} "
                   f"{pct_kept:<12.3f}% {info['n_above']:<15,} "
                   f"{info['pct_above']:.3f}%{marker}\n")
        
        f.write("\n")
        
        # Recommendation
        f.write("=" * 80 + "\n")
        f.write("RECOMMENDATION\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Recommended Threshold: P{stats['recommended_threshold']}\n")
        f.write(f"Reason: {stats['recommendation_reason']}\n\n")
        
        recommended_info = stats['outlier_counts'][stats['recommended_threshold']]
        f.write("Impact of Applying This Filter:\n")
        f.write(f"  • Keep:   {stats['basic_stats']['n_events'] - recommended_info['n_above']:,} events "
               f"({100 - recommended_info['pct_above']:.3f}%)\n")
        f.write(f"  • Remove: {recommended_info['n_above']:,} events "
               f"({recommended_info['pct_above']:.3f}%)\n")
        f.write(f"  • Cutoff FSC: {recommended_info['cutoff']:.1f}\n\n")
        
        # Interpretation
        f.write("-" * 80 + "\n")
        f.write("INTERPRETATION\n")
        f.write("-" * 80 + "\n\n")
        
        pct_lost = recommended_info['pct_above']
        if pct_lost < 0.1:
            f.write("✓ EXCELLENT: Less than 0.1% of events would be filtered.\n")
            f.write("  These extreme outliers are almost certainly artifacts, not EVs.\n\n")
        elif pct_lost < 0.5:
            f.write("✓ GOOD: Less than 0.5% of events would be filtered.\n")
            f.write("  Most outliers are likely artifacts (debris, aggregates).\n\n")
        elif pct_lost < 1.0:
            f.write("⚠ CAUTION: ~1% of events would be filtered.\n")
            f.write("  Review scatter plots to ensure outliers aren't a real population.\n\n")
        else:
            f.write("⚠ WARNING: More than 1% would be filtered.\n")
            f.write("  Consider if this represents a real biological population.\n\n")
        
        # Expected EV characteristics
        f.write("Expected Extracellular Vesicle Characteristics:\n")
        f.write("  • Exosomes:         30-150 nm (FSC typically 100-2000)\n")
        f.write("  • Microvesicles:    100-1000 nm (FSC typically 500-5000)\n")
        f.write("  • Apoptotic bodies: 500-5000 nm (FSC typically >5000)\n\n")
        
        max_fsc = stats['basic_stats']['max']
        median_fsc = stats['basic_stats']['median']
        if max_fsc > median_fsc * 100:
            f.write(f"⚠ Note: Your max FSC ({max_fsc:.0f}) is {max_fsc/median_fsc:.0f}× larger than median.\n")
            f.write("  This extreme ratio strongly suggests artifacts, not biological particles.\n\n")
        
        # Next Steps
        f.write("=" * 80 + "\n")
        f.write("RECOMMENDED NEXT STEPS\n")
        f.write("=" * 80 + "\n\n")
        f.write("1. Review the generated plots:\n")
        f.write("   • fsc_distribution_overview.png - Overall distribution\n")
        f.write("   • fsc_outlier_analysis.png - Outlier characteristics\n")
        f.write("   • fsc_percentile_curve.png - Distribution jumps\n\n")
        
        f.write("2. Validate filtering decision:\n")
        f.write("   • Confirm outliers don't represent real biological population\n")
        f.write("   • Check if other markers (SSC, fluorescence) also extreme\n")
        f.write("   • Compare to NTA size distribution if available\n\n")
        
        f.write("3. Apply filtering in processing pipeline:\n")
        f.write(f"   • Filter FSC > {recommended_info['cutoff']:.0f} before Mie calibration\n")
        f.write("   • Document filtering in methods section\n")
        f.write("   • Report % events filtered in results\n\n")
        
        f.write("4. Monitor quality:\n")
        f.write("   • Track outlier percentage across batches\n")
        f.write("   • Investigate if outliers increase (sample prep issue?)\n")
        f.write("   • Validate with orthogonal methods (NTA, TEM)\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")
    
    logger.info(f"  ✓ Report saved: {report_file}")


def main():
    """
    Main execution function - orchestrates the entire analysis.
    
    WORKFLOW:
    ---------
    1. Set up paths and configuration
    2. Load sample FCS data (multiple files for robustness)
    3. Analyze FSC distribution and calculate statistics
    4. Create visualizations (3 comprehensive plots)
    5. Generate text report with recommendations
    6. Log summary to console
    
    OUTPUT DIRECTORY STRUCTURE:
    ---------------------------
    figures/outlier_analysis/
        ├── fsc_distribution_overview.png    (4-panel overview)
        ├── fsc_outlier_analysis.png         (outlier focus + table)
        ├── fsc_percentile_curve.png         (percentile plot)
        └── outlier_analysis_report.txt      (text summary)
    
    USAGE:
    ------
    python scripts/visualize_outliers.py
    
    No arguments needed - uses default paths from project structure.
    Modify paths in main() if your data is in different location.
    """
    logger.info("=" * 80)
    logger.info("OUTLIER VISUALIZATION AND ANALYSIS")
    logger.info("=" * 80)
    logger.info("")
    
    # Configuration
    data_dir = Path("data/parquet/nanofacs/events")
    output_dir = Path("figures/outlier_analysis")
    max_files = 5  # Load 5 files for representative sample
    
    logger.info(f"Configuration:")
    logger.info(f"  Data directory: {data_dir}")
    logger.info(f"  Output directory: {output_dir}")
    logger.info(f"  Max files to analyze: {max_files}")
    logger.info("")
    
    # Step 1: Load data
    logger.info("STEP 1: Loading FCS data...")
    df = load_sample_data(data_dir, max_files=max_files)
    logger.info("")
    
    # Step 2: Analyze distribution
    logger.info("STEP 2: Analyzing distribution...")
    stats = analyze_distribution(df)
    logger.info("")
    
    # Step 3: Create plots
    logger.info("STEP 3: Creating visualizations...")
    create_distribution_plots(df, stats, output_dir)
    logger.info("")
    
    # Step 4: Generate report
    logger.info("STEP 4: Generating report...")
    generate_report(stats, output_dir)
    logger.info("")
    
    # Summary
    logger.info("=" * 80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("=" * 80)
    logger.info(f"\nAnalyzed {stats['basic_stats']['n_events']:,} events from {max_files} files")
    logger.info(f"Recommended threshold: P{stats['recommended_threshold']}")
    logger.info(f"  • Cutoff FSC: {stats['outlier_counts'][stats['recommended_threshold']]['cutoff']:.1f}")
    logger.info(f"  • Events to keep: {stats['basic_stats']['n_events'] - stats['outlier_counts'][stats['recommended_threshold']]['n_above']:,} "
               f"({100 - stats['outlier_counts'][stats['recommended_threshold']]['pct_above']:.3f}%)")
    logger.info(f"  • Events to filter: {stats['outlier_counts'][stats['recommended_threshold']]['n_above']:,} "
               f"({stats['outlier_counts'][stats['recommended_threshold']]['pct_above']:.3f}%)")
    logger.info(f"\nOutputs saved to: {output_dir}/")
    logger.info("  • 3 PNG plots (300 DPI)")
    logger.info("  • 1 text report")
    logger.info("\nNext: Review plots and report, then apply filtering in processing pipeline")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
