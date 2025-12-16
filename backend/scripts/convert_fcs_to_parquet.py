"""
Convert FCS Files to Parquet Format with Particle Size Calculation
===================================================================

Purpose: Convert all FCS files to Parquet format with particle size calculations
         Based on November 18, 2025 meeting requirements

Features:
- Parse FCS files from nanoFACS directory
- Calculate particle sizes (30-150nm range)
- Save as Parquet for efficient storage/processing
- Preserve all metadata and channel data
- Generate processing summary

Author: CRMIT Backend Team
Date: November 18, 2025
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from loguru import logger
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.fcs_parser import FCSParser
from src.visualization.fcs_plots import calculate_particle_size

# Configure logger
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


def process_single_fcs(fcs_path: Path, output_dir: Path) -> Dict[str, Any]:
    """
    Process a single FCS file: parse, calculate particle size, save as Parquet.
    
    Args:
        fcs_path: Path to FCS file
        output_dir: Directory to save Parquet file
        
    Returns:
        Dictionary with processing results
    """
    try:
        # Parse FCS
        parser = FCSParser(file_path=fcs_path)
        data = parser.parse()
        
        if data is None or len(data) == 0:
            return {
                'file': fcs_path.name,
                'status': 'FAILED',
                'reason': 'No data parsed',
                'events': 0
            }
        
        # Add sample_id if not present
        if 'sample_id' not in data.columns:
            data['sample_id'] = fcs_path.stem
        
        # Calculate particle size
        try:
            data = calculate_particle_size(data)
            has_particle_size = True
        except Exception as e:
            logger.warning(f"Could not calculate particle size for {fcs_path.name}: {e}")
            has_particle_size = False
        
        # Create output path
        output_file = output_dir / f"{fcs_path.stem}.parquet"
        
        # Save as Parquet
        data.to_parquet(
            output_file,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        
        # Get file sizes
        fcs_size_mb = fcs_path.stat().st_size / (1024 * 1024)
        parquet_size_mb = output_file.stat().st_size / (1024 * 1024)
        compression_ratio = fcs_size_mb / parquet_size_mb if parquet_size_mb > 0 else 0
        
        return {
            'file': fcs_path.name,
            'status': 'SUCCESS',
            'events': len(data),
            'channels': len(data.columns),
            'has_particle_size': has_particle_size,
            'fcs_size_mb': fcs_size_mb,
            'parquet_size_mb': parquet_size_mb,
            'compression_ratio': compression_ratio,
            'output_file': str(output_file)
        }
        
    except Exception as e:
        logger.error(f"Error processing {fcs_path.name}: {e}")
        return {
            'file': fcs_path.name,
            'status': 'FAILED',
            'reason': str(e),
            'events': 0
        }


def convert_fcs_directory(
    fcs_dir: Path,
    output_dir: Path,
    parallel: bool = True,
    max_workers: int = 4
) -> pd.DataFrame:
    """
    Convert all FCS files in a directory to Parquet.
    
    Args:
        fcs_dir: Directory containing FCS files
        output_dir: Output directory for Parquet files
        parallel: Use parallel processing
        max_workers: Number of parallel workers
        
    Returns:
        DataFrame with conversion results
    """
    # Find all FCS files
    fcs_files = list(fcs_dir.rglob("*.fcs"))
    
    # Filter out backup files
    fcs_files = [f for f in fcs_files if 'Backup' not in str(f) and 'backup' not in str(f)]
    
    logger.info(f"Found {len(fcs_files)} FCS files to convert")
    
    if len(fcs_files) == 0:
        logger.warning("No FCS files found!")
        return pd.DataFrame()
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    start_time = time.time()
    
    if parallel and len(fcs_files) > 1:
        # Parallel processing
        logger.info(f"Processing with {max_workers} workers...")
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_single_fcs, fcs_file, output_dir): fcs_file
                for fcs_file in fcs_files
            }
            
            for i, future in enumerate(as_completed(futures), 1):
                result = future.result()
                results.append(result)
                
                if result['status'] == 'SUCCESS':
                    logger.info(f"[{i}/{len(fcs_files)}] ✅ {result['file']}: "
                              f"{result['events']:,} events, "
                              f"{result['compression_ratio']:.1f}x compression")
                else:
                    logger.error(f"[{i}/{len(fcs_files)}] ❌ {result['file']}: {result.get('reason', 'Unknown error')}")
    else:
        # Sequential processing
        for i, fcs_file in enumerate(fcs_files, 1):
            logger.info(f"[{i}/{len(fcs_files)}] Processing: {fcs_file.name}")
            result = process_single_fcs(fcs_file, output_dir)
            results.append(result)
            
            if result['status'] == 'SUCCESS':
                logger.info(f"  ✅ {result['events']:,} events, {result['compression_ratio']:.1f}x compression")
            else:
                logger.error(f"  ❌ {result.get('reason', 'Unknown error')}")
    
    elapsed = time.time() - start_time
    
    # Create results DataFrame
    results_df = pd.DataFrame(results)
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 CONVERSION SUMMARY")
    logger.info("=" * 80)
    
    success_count = (results_df['status'] == 'SUCCESS').sum()
    total_events = results_df[results_df['status'] == 'SUCCESS']['events'].sum()
    total_fcs_size = results_df[results_df['status'] == 'SUCCESS']['fcs_size_mb'].sum()
    total_parquet_size = results_df[results_df['status'] == 'SUCCESS']['parquet_size_mb'].sum()
    avg_compression = total_fcs_size / total_parquet_size if total_parquet_size > 0 else 0
    files_with_size = (results_df['has_particle_size'] == True).sum()
    
    logger.info(f"✅ Success: {success_count}/{len(results_df)} files")
    logger.info(f"📊 Total events: {total_events:,}")
    logger.info(f"🧮 Particle size calculated: {files_with_size}/{success_count} files")
    logger.info(f"💾 FCS size: {total_fcs_size:.2f} MB")
    logger.info(f"💾 Parquet size: {total_parquet_size:.2f} MB")
    logger.info(f"📦 Average compression: {avg_compression:.1f}x")
    logger.info(f"⏱️  Time: {elapsed:.1f}s ({elapsed/len(fcs_files):.2f}s per file)")
    logger.info(f"📁 Output: {output_dir}")
    
    return results_df


def main():
    """Convert all FCS data to Parquet format."""
    
    logger.info("=" * 80)
    logger.info("🚀 FCS TO PARQUET CONVERSION WITH PARTICLE SIZE CALCULATION")
    logger.info("=" * 80)
    
    project_root = Path(__file__).parent.parent
    
    # FCS directories to process
    fcs_directories = [
        project_root / "nanoFACS" / "10000 exo and cd81",
        project_root / "nanoFACS" / "CD9 and exosome lots",
        project_root / "nanoFACS" / "EXP 6-10-2025"
    ]
    
    all_results = []
    
    for fcs_dir in fcs_directories:
        if not fcs_dir.exists():
            logger.warning(f"Directory not found: {fcs_dir}")
            continue
        
        logger.info(f"\n📁 Processing: {fcs_dir.name}")
        logger.info("=" * 80)
        
        # Create output directory based on source
        output_dir = project_root / "data" / "parquet" / "nanofacs" / "events" / fcs_dir.name
        
        # Convert
        results_df = convert_fcs_directory(
            fcs_dir=fcs_dir,
            output_dir=output_dir,
            parallel=True,
            max_workers=4
        )
        
        if len(results_df) > 0:
            all_results.append(results_df)
    
    if all_results:
        # Combine all results
        combined_results = pd.concat(all_results, ignore_index=True)
        
        # Save summary
        summary_dir = project_root / "data" / "parquet" / "nanofacs" / "statistics"
        summary_dir.mkdir(parents=True, exist_ok=True)
        
        summary_file = summary_dir / "fcs_conversion_summary.csv"
        combined_results.to_csv(summary_file, index=False)
        logger.info(f"\n💾 Saved conversion summary: {summary_file}")
        
        # Overall statistics
        logger.info("\n" + "=" * 80)
        logger.info("📊 OVERALL STATISTICS")
        logger.info("=" * 80)
        
        total_success = (combined_results['status'] == 'SUCCESS').sum()
        total_files = len(combined_results)
        total_events = combined_results[combined_results['status'] == 'SUCCESS']['events'].sum()
        total_fcs_mb = combined_results[combined_results['status'] == 'SUCCESS']['fcs_size_mb'].sum()
        total_parquet_mb = combined_results[combined_results['status'] == 'SUCCESS']['parquet_size_mb'].sum()
        
        logger.info(f"📂 Directories processed: {len(fcs_directories)}")
        logger.info(f"✅ Files converted: {total_success}/{total_files}")
        logger.info(f"📊 Total events: {total_events:,}")
        logger.info(f"💾 Total FCS size: {total_fcs_mb:.2f} MB")
        logger.info(f"💾 Total Parquet size: {total_parquet_mb:.2f} MB")
        logger.info(f"📦 Space saved: {(total_fcs_mb - total_parquet_mb):.2f} MB ({((total_fcs_mb - total_parquet_mb) / total_fcs_mb * 100):.1f}%)")
        
        logger.info("\n✅ CONVERSION COMPLETE!")
        logger.info("\nNext steps:")
        logger.info("  1. Test Size vs Intensity plots with new Parquet data")
        logger.info("  2. Validate particle size calculations")
        logger.info("  3. Run batch visualization scripts")
    else:
        logger.error("❌ No files converted!")


if __name__ == "__main__":
    main()
