"""
Reprocess Parquet Files with Mie-Based Particle Sizing
=======================================================

Purpose: Update all FCS parquet files with scientifically accurate particle sizes
         using Mie scattering theory instead of simplified approximation.

Date: November 18, 2025
Status: Production ready

Usage:
    python scripts/reprocess_parquet_with_mie.py --input data/processed --output data/processed_mie
    
    # Dry run (no changes):
    python scripts/reprocess_parquet_with_mie.py --dry-run
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Any
from loguru import logger
import argparse
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.visualization.fcs_plots import calculate_particle_size


def find_parquet_files(directory: Path, recursive: bool = True) -> List[Path]:
    """Find all parquet files in directory."""
    if recursive:
        files = list(directory.rglob("*.parquet"))
    else:
        files = list(directory.glob("*.parquet"))
    
    logger.info(f"Found {len(files)} parquet files in {directory}")
    return files


def reprocess_file(
    input_file: Path,
    output_file: Path,
    use_mie: bool = True,
    calibration_beads: Optional[Dict[float, float]] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Reprocess single parquet file with Mie-based sizing.
    
    Returns:
        Dict with processing statistics
    """
    logger.info(f"Processing: {input_file.name}")
    
    try:
        # Load data
        df = pd.read_parquet(input_file)
        n_events = len(df)
        
        # Check if already has particle_size_nm
        had_old_sizes = 'particle_size_nm' in df.columns
        if had_old_sizes:
            old_sizes = df['particle_size_nm'].copy()
        
        # Calculate new sizes with Mie theory
        df = calculate_particle_size(
            df,
            use_mie_theory=use_mie,
            calibration_beads=calibration_beads
        )
        
        # Statistics
        stats = {
            "file": input_file.name,
            "n_events": n_events,
            "had_old_sizes": had_old_sizes,
            "size_min": float(df['particle_size_nm'].min()),
            "size_max": float(df['particle_size_nm'].max()),
            "size_mean": float(df['particle_size_nm'].mean()),
            "size_median": float(df['particle_size_nm'].median()),
            "pct_in_range": float(100 * df['size_in_calibrated_range'].sum() / n_events) if 'size_in_calibrated_range' in df.columns else 100.0
        }
        
        # Compare old vs new if available
        if had_old_sizes:
            size_change = df['particle_size_nm'] - old_sizes
            stats["mean_size_change"] = float(size_change.mean())
            stats["median_size_change"] = float(size_change.median())
            stats["max_abs_change"] = float(abs(size_change).max())
        
        # Save if not dry run
        if not dry_run:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(output_file, index=False)
            logger.info(f"✅ Saved to: {output_file}")
        else:
            logger.info(f"🔍 DRY RUN - would save to: {output_file}")
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Failed to process {input_file.name}: {e}")
        return {
            "file": input_file.name,
            "error": str(e),
            "n_events": 0
        }


def main():
    parser = argparse.ArgumentParser(description="Reprocess parquet files with Mie-based particle sizing")
    parser.add_argument(
        "--input",
        type=str,
        default="data/processed",
        help="Input directory containing parquet files"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory (default: same as input, overwrites files)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run - don't save files, just show what would change"
    )
    parser.add_argument(
        "--no-mie",
        action="store_true",
        help="Don't use Mie theory (keep old simplified method)"
    )
    parser.add_argument(
        "--wavelength",
        type=float,
        default=488.0,
        help="Laser wavelength in nm (default: 488)"
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        default=True,
        help="Search subdirectories recursively"
    )
    
    args = parser.parse_args()
    
    # Setup paths
    input_dir = Path(args.input)
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return
    
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = input_dir
        logger.warning("⚠️ No output directory specified - will OVERWRITE input files!")
    
    # Configure logging
    log_file = f"logs/reprocess_parquet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    Path("logs").mkdir(exist_ok=True)
    logger.add(log_file, rotation="10 MB")
    
    logger.info("=" * 80)
    logger.info("PARQUET REPROCESSING WITH MIE THEORY")
    logger.info("=" * 80)
    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Use Mie theory: {not args.no_mie}")
    logger.info(f"Wavelength: {args.wavelength} nm")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 80)
    
    # Find files
    files = find_parquet_files(input_dir, recursive=args.recursive)
    
    if len(files) == 0:
        logger.warning("No parquet files found!")
        return
    
    # Process files
    all_stats = []
    for i, input_file in enumerate(files, 1):
        logger.info(f"\n[{i}/{len(files)}] Processing {input_file.name}")
        
        # Determine output path (preserve directory structure)
        rel_path = input_file.relative_to(input_dir)
        output_file = output_dir / rel_path
        
        stats = reprocess_file(
            input_file=input_file,
            output_file=output_file,
            use_mie=not args.no_mie,
            dry_run=args.dry_run
        )
        all_stats.append(stats)
    
    # Summary statistics
    logger.info("\n" + "=" * 80)
    logger.info("PROCESSING SUMMARY")
    logger.info("=" * 80)
    
    successful = [s for s in all_stats if "error" not in s]
    failed = [s for s in all_stats if "error" in s]
    
    logger.info(f"Total files: {len(files)}")
    logger.info(f"✅ Successful: {len(successful)}")
    logger.info(f"❌ Failed: {len(failed)}")
    
    if successful:
        total_events = sum(s["n_events"] for s in successful)
        logger.info(f"\nTotal events processed: {total_events:,}")
        
        # Size statistics
        all_sizes_min = [s["size_min"] for s in successful]
        all_sizes_max = [s["size_max"] for s in successful]
        all_sizes_mean = [s["size_mean"] for s in successful]
        
        logger.info(f"\nParticle size ranges:")
        logger.info(f"  Minimum: {min(all_sizes_min):.1f} nm")
        logger.info(f"  Maximum: {max(all_sizes_max):.1f} nm")
        logger.info(f"  Mean across files: {np.mean(all_sizes_mean):.1f} ± {np.std(all_sizes_mean):.1f} nm")
        
        # Calibration range
        if any("pct_in_range" in s for s in successful):
            in_range_pcts = [s["pct_in_range"] for s in successful if "pct_in_range" in s]
            logger.info(f"\n% events in calibrated range: {np.mean(in_range_pcts):.1f}% ± {np.std(in_range_pcts):.1f}%")
        
        # Size changes (if old sizes existed)
        had_old = [s for s in successful if s.get("had_old_sizes", False)]
        if had_old:
            mean_changes = [s["mean_size_change"] for s in had_old]
            logger.info(f"\nSize change vs old method:")
            logger.info(f"  Mean change: {np.mean(mean_changes):.1f} ± {np.std(mean_changes):.1f} nm")
            logger.info(f"  Max absolute change: {max(s['max_abs_change'] for s in had_old):.1f} nm")
    
    if failed:
        logger.error(f"\n⚠️ Failed files:")
        for s in failed:
            logger.error(f"  - {s['file']}: {s['error']}")
    
    logger.info("\n" + "=" * 80)
    if args.dry_run:
        logger.info("🔍 DRY RUN COMPLETE - No files were modified")
    else:
        logger.info("✅ REPROCESSING COMPLETE")
    logger.info(f"📋 Log saved to: {log_file}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
