"""
Quick script to add Mie-based particle sizes to FCS parquet files.
Uses percentile-based FSC normalization for speed.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from loguru import logger
import argparse
from datetime import datetime

def add_mie_sizes_fast(df: pd.DataFrame, fsc_channel: str = 'VFSC-H') -> pd.DataFrame:
    """
    Fast particle size estimation using percentile-based normalization.
    
    Args:
        df: DataFrame with flow cytometry data
        fsc_channel: Name of forward scatter channel
        
    Returns:
        DataFrame with particle_size_nm added
    """
    if fsc_channel not in df.columns:
        logger.error(f"Channel {fsc_channel} not found!")
        df['particle_size_nm'] = np.nan
        return df
    
    fsc = df[fsc_channel].values
    fsc = np.asarray(fsc)  # Convert to numpy array
    
    # Filter out zeros and extremely low/high values
    fsc_clean = fsc[(fsc > 0) & (fsc < 1e6)]  # type: ignore[operator]
    
    if len(fsc_clean) == 0:
        logger.warning("No valid FSC values found!")
        df['particle_size_nm'] = np.nan
        return df
    
    # Use percentiles for robust normalization (ignores outliers)
    p5 = float(np.percentile(fsc_clean, 5))   # Bottom 5% ~ 30nm
    p50 = float(np.percentile(fsc_clean, 50))  # Median ~ 80nm  
    p95 = float(np.percentile(fsc_clean, 95))  # Top 5% ~ 180nm
    
    logger.info(f"FSC percentiles: P5={p5:.0f}, P50={p50:.0f}, P95={p95:.0f}")
    
    # Linear interpolation between reference points
    # This assumes monotonic relationship between FSC and diameter
    sizes = np.zeros_like(fsc)
    
    # Below P5: extrapolate down to 30nm
    mask_low = (fsc > 0) & (fsc <= p5)  # type: ignore[operator]
    sizes[mask_low] = 30 + (fsc[mask_low] / p5) * 20  # 10-50nm range
    
    # Between P5 and P50
    mask_mid_low = (fsc > p5) & (fsc <= p50)
    sizes[mask_mid_low] = 50 + ((fsc[mask_mid_low] - p5) / (p50 - p5)) * 30  # 50-80nm
    
    # Between P50 and P95
    mask_mid_high = (fsc > p50) & (fsc <= p95)
    sizes[mask_mid_high] = 80 + ((fsc[mask_mid_high] - p50) / (p95 - p50)) * 100  # 80-180nm
    
    # Above P95: extrapolate up
    mask_high = fsc > p95
    sizes[mask_high] = 180 + ((fsc[mask_high] - p95) / p95) * 20  # 180-200nm+
    
    # Cap at reasonable limits
    sizes = np.clip(sizes, 20, 300)
    
    # Mark zeros as NaN
    sizes[fsc <= 0] = np.nan  # type: ignore[operator]
    
    df['particle_size_nm'] = sizes
    df['size_method'] = 'percentile_normalized'
    
    # Statistics
    valid_sizes = sizes[~np.isnan(sizes)]
    logger.info(
        f"Sizes calculated: {valid_sizes.min():.1f}-{valid_sizes.max():.1f} nm "
        f"(median: {np.median(valid_sizes):.1f} nm)"
    )
    
    return df


def process_file(input_path: Path, output_path: Path, dry_run: bool = False):
    """Process single parquet file."""
    logger.info(f"📂 Processing: {input_path.name}")
    
    try:
        # Read file
        df = pd.read_parquet(input_path)
        logger.info(f"  Events: {len(df):,}")
        
        # Find FSC channel
        fsc_channels = [col for col in df.columns if 'FSC' in col and 'H' in col]
        if not fsc_channels:
            logger.error(f"  ❌ No FSC-H channel found!")
            return {"file": input_path.name, "error": "No FSC channel", "n_events": len(df)}
        
        fsc_channel = fsc_channels[0]
        logger.info(f"  Using channel: {fsc_channel}")
        
        # Add sizes
        df = add_mie_sizes_fast(df, fsc_channel=fsc_channel)
        
        # Save
        if not dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(output_path, compression='snappy')
            logger.info(f"  ✅ Saved to: {output_path}")
        else:
            logger.info(f"  📝 DRY RUN - would save to: {output_path}")
        
        return {
            "file": input_path.name,
            "n_events": len(df),
            "size_range": f"{df['particle_size_nm'].min():.1f}-{df['particle_size_nm'].max():.1f} nm",
            "size_median": f"{df['particle_size_nm'].median():.1f} nm"
        }
        
    except Exception as e:
        logger.error(f"  ❌ Error: {e}")
        return {"file": input_path.name, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Quick Mie size addition to FCS parquet files")
    parser.add_argument("--input", type=str, required=True, help="Input directory")
    parser.add_argument("--output", type=str, required=True, help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    args = parser.parse_args()
    
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return
    
    # Setup logging
    log_file = f"logs/quick_mie_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    Path("logs").mkdir(exist_ok=True)
    logger.add(log_file)
    
    logger.info("=" * 80)
    logger.info("QUICK MIE SIZE ADDITION")
    logger.info("=" * 80)
    logger.info(f"Input: {input_dir}")
    logger.info(f"Output: {output_dir}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 80)
    
    # Find files
    files = list(input_dir.rglob("*.parquet"))
    logger.info(f"Found {len(files)} parquet files")
    
    if len(files) == 0:
        logger.warning("No files found!")
        return
    
    # Process files
    results = []
    for i, input_file in enumerate(files, 1):
        logger.info(f"\n[{i}/{len(files)}] Processing...")
        
        # Create output path (preserve subdirectory structure)
        rel_path = input_file.relative_to(input_dir)
        output_file = output_dir / rel_path
        
        result = process_file(input_file, output_file, dry_run=args.dry_run)
        results.append(result)
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    
    successful = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]
    
    logger.info(f"Total files: {len(files)}")
    logger.info(f"Successful: {len(successful)}")
    logger.info(f"Failed: {len(failed)}")
    
    if successful:
        total_events = sum(r['n_events'] for r in successful)
        logger.info(f"Total events processed: {total_events:,}")
    
    if failed:
        logger.warning("\nFailed files:")
        for r in failed:
            logger.warning(f"  - {r['file']}: {r.get('error', 'Unknown error')}")
    
    logger.info(f"\nLog saved to: {log_file}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
