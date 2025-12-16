"""
Batch NTA Visualization Script - Integrated Pipeline
===================================================

Purpose: Generate visualizations for all NTA data in batch processing pipeline

Integration: Extends batch_process_nta.py with visualization capabilities

Author: CRMIT Team
Date: November 15, 2025
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.nta_parser import NTAParser
from src.visualization.nta_plots import NTAPlotter


def batch_visualize_nta(
    input_dir: Path,
    output_dir: Path,
    stats_file: Path,
    plot_types: list = ['size_distribution', 'concentration'],
    max_dirs: int | None = None
):
    """
    Generate visualizations for all processed NTA data.
    
    Args:
        input_dir: Directory with NTA subdirectories
        output_dir: Directory for plots
        stats_file: Path to NTA statistics parquet file
        plot_types: List of plot types to generate
        max_dirs: Maximum directories to process (None = all)
    """
    logger.info("=" * 80)
    logger.info("🎨 NTA BATCH VISUALIZATION PIPELINE")
    logger.info("=" * 80)
    
    # Initialize
    plotter = NTAPlotter(output_dir=output_dir)
    
    # Load statistics
    stats_df = None
    if stats_file.exists():
        stats_df = pd.read_parquet(stats_file)
        logger.info(f"📊 Loaded statistics: {len(stats_df)} samples")
    else:
        logger.warning(f"⚠️  Statistics file not found: {stats_file}")
        return 0, 0, 0
    
    # Find NTA directories
    nta_dirs = [d for d in input_dir.iterdir() if d.is_dir()]
    
    if max_dirs:
        nta_dirs = nta_dirs[:max_dirs]
    
    logger.info(f"📁 Found {len(nta_dirs)} NTA directories")
    logger.info(f"📊 Plot types: {', '.join(plot_types)}")
    logger.info(f"💾 Output: {output_dir}")
    
    # Process each directory
    success_count = 0
    error_count = 0
    plot_count = 0
    
    for nta_dir in tqdm(nta_dirs, desc="Generating plots"):
        try:
            sample_id = nta_dir.name
            
            # Get stats for this sample
            sample_stats = stats_df[stats_df['sample_id'] == sample_id]
            
            if len(sample_stats) == 0:
                logger.warning(f"⚠️  No stats for: {sample_id}")
                error_count += 1
                continue
            
            # Generate size distribution plot
            if 'size_distribution' in plot_types:
                # Ensure data is a DataFrame
                if isinstance(sample_stats, pd.Series):
                    sample_data = pd.DataFrame([sample_stats])
                else:
                    sample_data = sample_stats
                    
                dist_path = plotter.plot_size_distribution(
                    data=sample_data,
                    title=f'Size Distribution - {sample_id}',
                    output_file=Path(f"{sample_id}_size_distribution.png"),
                    show_stats=True
                )
                if dist_path:
                    plot_count += 1
            
            success_count += 1
            
        except Exception as e:
            logger.error(f"❌ Error processing {nta_dir.name}: {e}")
            error_count += 1
    
    # Generate comparison plots if we have multiple samples
    if len(stats_df) >= 2:
        logger.info("\n📊 Generating comparison plots...")
        
        try:
            # Cumulative distribution comparison
            if 'concentration' in plot_types:
                plotter.plot_cumulative_distribution(
                    data=stats_df.head(10),
                    output_file=Path("cumulative_comparison.png")
                )
                plot_count += 1
                logger.info("  ✅ Cumulative distribution")
            
            # Concentration profile
            plotter.plot_concentration_profile(
                data=stats_df.head(10),
                output_file=Path("concentration_profile.png")
            )
            plot_count += 1
            logger.info("  ✅ Concentration profile")
                
        except Exception as e:
            logger.error(f"❌ Error generating comparison plots: {e}")
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 BATCH VISUALIZATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"✅ Successful: {success_count} samples")
    logger.info(f"❌ Errors: {error_count} samples")
    logger.info(f"📈 Total plots generated: {plot_count}")
    logger.info(f"💾 Plots saved to: {output_dir}")
    
    return success_count, error_count, plot_count


def main():
    """Main execution."""
    # Configuration
    INPUT_DIR = Path("NTA")
    OUTPUT_DIR = Path("figures/nta_batch")
    STATS_FILE = Path("data/processed/nta_statistics.parquet")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Run batch visualization
    batch_visualize_nta(
        input_dir=INPUT_DIR,
        output_dir=OUTPUT_DIR,
        stats_file=STATS_FILE,
        plot_types=['size_distribution', 'concentration'],
        max_dirs=10  # Limit for demo, set to None for all
    )


if __name__ == '__main__':
    main()
