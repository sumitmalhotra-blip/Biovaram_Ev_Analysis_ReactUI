"""
Quick NTA Batch Visualization
Generates size distribution plots for all parsed NTA files
"""

import sys
from pathlib import Path
import pandas as pd
from loguru import logger
import matplotlib.pyplot as plt

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.visualization.nta_plots import NTAPlotter

def main():
    """Process all NTA parquet files and generate visualizations."""
    
    # Directories
    measurements_dir = project_root / "data" / "parquet" / "nta" / "measurements"
    output_dir = project_root / "figures" / "nta_batch"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 80)
    logger.info("🎨 NTA BATCH VISUALIZATION")
    logger.info("=" * 80)
    
    # Find all parquet files
    parquet_files = sorted(measurements_dir.glob("*.parquet"))
    
    if not parquet_files:
        logger.error(f"No parquet files found in {measurements_dir}")
        return
    
    logger.info(f"Found {len(parquet_files)} NTA parquet files")
    
    # Initialize plotter
    plotter = NTAPlotter(output_dir=output_dir)
    
    # Process each file
    success_count = 0
    error_count = 0
    
    for i, parquet_file in enumerate(parquet_files, 1):
        sample_id = parquet_file.stem  # Remove .parquet extension
        
        try:
            # Load data
            df = pd.read_parquet(parquet_file)
            
            if df.empty:
                logger.warning(f"[{i}/{len(parquet_files)}] ⚠️  {sample_id}: Empty data")
                error_count += 1
                continue
            
            # Check if size distribution data exists
            if 'size_nm' not in df.columns:
                logger.warning(f"[{i}/{len(parquet_files)}] ⚠️  {sample_id}: No size_nm column")
                error_count += 1
                continue
            
            # Generate size distribution plot
            output_path = output_dir / f"{sample_id}_size_distribution.png"
            
            # Create plot
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Plot histogram
            ax.hist(df['size_nm'], bins=50, alpha=0.7, color='steelblue', edgecolor='black')
            ax.set_xlabel('Size (nm)', fontsize=12)
            ax.set_ylabel('Frequency', fontsize=12)
            ax.set_title(f'Size Distribution: {sample_id}', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # Add statistics
            mean_size = df['size_nm'].mean()
            median_size = df['size_nm'].median()
            ax.axvline(float(mean_size), color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_size:.1f} nm')
            ax.axvline(float(median_size), color='green', linestyle='--', linewidth=2, label=f'Median: {median_size:.1f} nm')
            ax.legend()
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"[{i}/{len(parquet_files)}] ✅ {sample_id}: {len(df)} points → {output_path.name}")
            success_count += 1
            
        except Exception as e:
            logger.error(f"[{i}/{len(parquet_files)}] ❌ {sample_id}: {str(e)}")
            error_count += 1
    
    # Summary
    logger.info("=" * 80)
    logger.info("📊 SUMMARY")
    logger.info("=" * 80)
    logger.info(f"✅ Success: {success_count}/{len(parquet_files)}")
    logger.info(f"❌ Errors: {error_count}")
    logger.info(f"💾 Output: {output_dir}")
    
    # Display output stats
    png_files = list(output_dir.glob("*.png"))
    if png_files:
        total_size = sum(f.stat().st_size for f in png_files) / (1024 * 1024)  # MB
        logger.info(f"📈 Plots generated: {len(png_files)}")
        logger.info(f"💿 Total size: {total_size:.2f} MB")

if __name__ == "__main__":
    main()
