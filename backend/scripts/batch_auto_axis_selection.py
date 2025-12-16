"""
Batch Auto-Axis Selection for FCS Data

Processes all FCS files and generates optimal scatter plots automatically.
For each file, selects the best 3-5 channel combinations and creates plots.

Features:
- Parallel processing for speed
- Automatic channel pair optimization
- Generates plots + recommendation reports
- Master summary report

Author: GitHub Copilot
Date: November 17, 2025
Task: Complete Auto-Axis Selection at Full Scale
"""

import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple
import pandas as pd
import time
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parsers.fcs_parser import FCSParser
from visualization.auto_axis_selector import AutoAxisSelector
from visualization.fcs_plots import FCSPlotter

# Configure logger
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


def process_single_fcs_file(
    fcs_path: Path,
    output_dir: Path,
    n_recommendations: int = 5,
    n_plots: int = 3
) -> Dict[str, Any]:
    """
    Process a single FCS file with auto-axis selection.
    
    Args:
        fcs_path: Path to FCS file
        output_dir: Directory for output plots and reports
        n_recommendations: Number of recommendations to generate
        n_plots: Number of plots to create
        
    Returns:
        Dictionary with processing results
    """
    result = {
        'file_name': fcs_path.name,
        'status': 'pending',
        'event_count': 0,
        'total_channels': 0,
        'possible_pairs': 0,
        'recommendations': 0,
        'plots_generated': 0,
        'processing_time_seconds': 0,
        'error': None
    }
    
    start_time = time.time()
    
    try:
        # Parse FCS file
        logger.info(f"Parsing: {fcs_path.name}")
        parser = FCSParser(file_path=fcs_path)
        data = parser.parse()
        
        result['event_count'] = len(data)
        result['total_channels'] = len(data.columns)
        
        # Get numeric channels (exclude metadata)
        numeric_channels = data.select_dtypes(include=['number']).columns.tolist()
        exclude_cols = ['sample_id', 'event_id', 'Time', 'time', 'index']
        numeric_channels = [col for col in numeric_channels if col not in exclude_cols]
        
        result['possible_pairs'] = len(numeric_channels) * (len(numeric_channels) - 1) // 2
        
        # Initialize auto-axis selector
        selector = AutoAxisSelector(
            min_variance_threshold=0.1,
            max_correlation_threshold=0.95,
            sample_size=10000
        )
        
        # Generate recommendations
        logger.info(f"  Analyzing {result['possible_pairs']} possible channel pairs...")
        recommendations = selector.generate_recommendations(data, n_recommendations=n_recommendations)
        result['recommendations'] = len(recommendations)
        
        # Create output directories
        plots_dir = output_dir / "plots" / fcs_path.stem
        plots_dir.mkdir(parents=True, exist_ok=True)
        
        reports_dir = output_dir / "recommendations"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Save recommendations to CSV
        rec_file = reports_dir / f"{fcs_path.stem}_recommendations.csv"
        recommendations.to_csv(rec_file, index=False)
        logger.info(f"  ✓ Saved recommendations: {rec_file.name}")
        
        # Generate plots for top N recommendations
        plotter = FCSPlotter(output_dir=plots_dir)
        plots_created = 0
        
        for idx in range(min(n_plots, len(recommendations))):
            rec = recommendations.iloc[idx]
            x_ch = rec['x_channel']
            y_ch = rec['y_channel']
            
            try:
                # Create safe filename (remove special characters)
                safe_x = x_ch.replace('-', '').replace('/', '_')
                safe_y = y_ch.replace('-', '').replace('/', '_')
                plot_filename = f"rank{idx+1}_{safe_x}_vs_{safe_y}.png"
                
                plotter.plot_scatter(
                    data=data,
                    x_channel=x_ch,
                    y_channel=y_ch,
                    title=f"{fcs_path.stem}\n{x_ch} vs {y_ch} (Score: {rec['score']:.3f})",
                    output_file=plot_filename,
                    plot_type="density",
                    sample_size=50000
                )
                plots_created += 1
                
            except Exception as e:
                logger.warning(f"  ⚠️  Failed to create plot {idx+1}: {e}")
        
        result['plots_generated'] = plots_created
        result['status'] = 'success'
        
        processing_time = time.time() - start_time
        result['processing_time_seconds'] = round(processing_time, 2)
        
        logger.success(f"✓ {fcs_path.name}: {plots_created} plots, {len(recommendations)} recommendations ({processing_time:.1f}s)")
        
    except Exception as e:
        result['status'] = 'failed'
        result['error'] = str(e)
        logger.error(f"✗ {fcs_path.name}: {e}")
    
    return result


def batch_auto_axis_selection(
    input_dirs: List[Path],
    output_dir: Path,
    n_recommendations: int = 5,
    n_plots: int = 3,
    max_workers: int = 4
) -> pd.DataFrame:
    """
    Batch process FCS files with auto-axis selection.
    
    Args:
        input_dirs: List of directories containing FCS files
        output_dir: Output directory for plots and reports
        n_recommendations: Number of recommendations per file
        n_plots: Number of plots to generate per file
        max_workers: Number of parallel workers
        
    Returns:
        DataFrame with processing summary
    """
    print("\n" + "="*80)
    print(" "*25 + "BATCH AUTO-AXIS SELECTION")
    print("="*80 + "\n")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all FCS files
    fcs_files = []
    for input_dir in input_dirs:
        if input_dir.exists():
            files = list(input_dir.glob("*.fcs"))
            fcs_files.extend(files)
            logger.info(f"Found {len(files)} FCS files in: {input_dir.name}")
    
    if not fcs_files:
        logger.error("No FCS files found!")
        return pd.DataFrame()
    
    print(f"\n📊 Total FCS files to process: {len(fcs_files)}")
    print(f"📁 Output directory: {output_dir}")
    print(f"⚙️  Parallel workers: {max_workers}")
    print(f"📈 Recommendations per file: {n_recommendations}")
    print(f"🖼️  Plots per file: {n_plots}")
    print(f"🎯 Expected total plots: {len(fcs_files) * n_plots}\n")
    
    print("─"*80)
    print("PROCESSING FILES...")
    print("─"*80 + "\n")
    
    # Process files in parallel
    results = []
    start_time = time.time()
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(
                process_single_fcs_file,
                fcs_path,
                output_dir,
                n_recommendations,
                n_plots
            ): fcs_path
            for fcs_path in fcs_files
        }
        
        # Collect results as they complete
        completed = 0
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1
            
            # Progress indicator
            if completed % 5 == 0 or completed == len(fcs_files):
                print(f"  Progress: {completed}/{len(fcs_files)} files ({100*completed/len(fcs_files):.1f}%)")
    
    total_time = time.time() - start_time
    
    # Create results DataFrame
    results_df = pd.DataFrame(results)
    
    # Generate summary report
    print("\n" + "="*80)
    print("📊 PROCESSING SUMMARY")
    print("="*80 + "\n")
    
    successful = len(results_df[results_df['status'] == 'success'])
    failed = len(results_df[results_df['status'] == 'failed'])
    total_plots = results_df['plots_generated'].sum()
    total_recommendations = results_df['recommendations'].sum()
    avg_time = results_df['processing_time_seconds'].mean()
    
    print(f"✅ Success: {successful}/{len(fcs_files)} files")
    print(f"❌ Failed: {failed}/{len(fcs_files)} files")
    print(f"📈 Total plots generated: {total_plots}")
    print(f"📋 Total recommendations: {total_recommendations}")
    print(f"⏱️  Average processing time: {avg_time:.2f}s per file")
    print(f"⏱️  Total processing time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print(f"🚀 Throughput: {len(fcs_files)/total_time*60:.1f} files/minute")
    
    # Calculate efficiency gain
    if len(results_df) > 0:
        avg_possible_pairs = results_df['possible_pairs'].mean()
        avg_recommendations = results_df['recommendations'].mean()
        reduction = 100 * (1 - avg_recommendations / avg_possible_pairs) if avg_possible_pairs > 0 else 0
        
        print(f"\n💡 Efficiency Gain:")
        print(f"   Average possible pairs per file: {avg_possible_pairs:.0f}")
        print(f"   Average recommendations per file: {avg_recommendations:.1f}")
        print(f"   Reduction: {reduction:.1f}% (saves {reduction/100 * avg_possible_pairs:.0f} unnecessary plots per file)")
    
    # Save master summary report
    summary_file = output_dir / "batch_summary.csv"
    results_df.to_csv(summary_file, index=False)
    logger.success(f"\n✓ Saved batch summary: {summary_file}")
    
    # List failed files if any
    if failed > 0:
        print(f"\n⚠️  FAILED FILES:")
        failed_df = results_df[results_df['status'] == 'failed']
        for idx, row in failed_df.iterrows():
            print(f"   • {row['file_name']}: {row['error']}")
    
    # Generate statistics report
    stats_file = output_dir / "statistics_summary.txt"
    with open(stats_file, 'w') as f:
        f.write("="*80 + "\n")
        f.write(" "*20 + "BATCH AUTO-AXIS SELECTION REPORT\n")
        f.write("="*80 + "\n\n")
        f.write(f"Processing Date: {pd.Timestamp.now()}\n")
        f.write(f"Total Files Processed: {len(fcs_files)}\n")
        f.write(f"Successful: {successful}\n")
        f.write(f"Failed: {failed}\n")
        f.write(f"Total Plots Generated: {total_plots}\n")
        f.write(f"Total Recommendations: {total_recommendations}\n")
        f.write(f"Average Processing Time: {avg_time:.2f}s per file\n")
        f.write(f"Total Processing Time: {total_time:.1f}s\n")
        f.write(f"\n" + "─"*80 + "\n")
        f.write("TOP 10 FILES BY EVENT COUNT:\n")
        f.write("─"*80 + "\n\n")
        top10 = results_df.nlargest(10, 'event_count')[['file_name', 'event_count', 'plots_generated', 'processing_time_seconds']]
        f.write(top10.to_string(index=False))
        f.write(f"\n\n" + "─"*80 + "\n")
        f.write("OVERALL STATISTICS:\n")
        f.write("─"*80 + "\n\n")
        f.write(results_df[['event_count', 'total_channels', 'possible_pairs', 'recommendations', 'plots_generated', 'processing_time_seconds']].describe().to_string())
    
    logger.success(f"✓ Saved statistics report: {stats_file}")
    
    print("\n" + "="*80)
    print("✅ BATCH AUTO-AXIS SELECTION COMPLETE")
    print("="*80 + "\n")
    
    print(f"📂 Output Structure:")
    print(f"   {output_dir}/")
    print(f"   ├── plots/")
    print(f"   │   ├── [file1]/  (3 plots)")
    print(f"   │   ├── [file2]/  (3 plots)")
    print(f"   │   └── ... ({len(fcs_files)} directories)")
    print(f"   ├── recommendations/")
    print(f"   │   └── {len(fcs_files)} CSV files")
    print(f"   ├── batch_summary.csv")
    print(f"   └── statistics_summary.txt\n")
    
    return results_df


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Batch Auto-Axis Selection for FCS Data",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--input-dirs',
        nargs='+',
        type=Path,
        default=[
            Path("nanoFACS/10000 exo and cd81"),
            Path("nanoFACS/CD9 and exosome lots"),
            Path("nanoFACS/EXP 6-10-2025")
        ],
        help='Input directories containing FCS files'
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path("figures/auto_axis_batch"),
        help='Output directory for plots and reports'
    )
    
    parser.add_argument(
        '--recommendations',
        type=int,
        default=5,
        help='Number of recommendations to generate per file (default: 5)'
    )
    
    parser.add_argument(
        '--plots',
        type=int,
        default=3,
        help='Number of plots to generate per file (default: 3)'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of parallel workers (default: 4)'
    )
    
    args = parser.parse_args()
    
    # Run batch processing
    results_df = batch_auto_axis_selection(
        input_dirs=args.input_dirs,
        output_dir=args.output_dir,
        n_recommendations=args.recommendations,
        n_plots=args.plots,
        max_workers=args.workers
    )
    
    return results_df


if __name__ == "__main__":
    main()
