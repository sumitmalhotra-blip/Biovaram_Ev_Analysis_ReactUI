"""
Batch NTA Plot Generation Script

Processes all NTA Parquet files and generates size distribution plots for each sample.

Usage:
    python scripts/generate_nta_plots.py [--limit N] [--output-dir PATH]

Author: GitHub Copilot
Date: November 14, 2025
Task: 1.3.2 - Batch NTA Visualization
"""

import sys
from pathlib import Path
import argparse
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.visualization.nta_plots import generate_nta_plots
from loguru import logger


def batch_generate_nta_plots(
    input_dir: Path,
    output_dir: Path,
    limit: int | None = None
) -> None:
    """
    Generate size distribution plots for all NTA Parquet files.
    
    Args:
        input_dir: Directory containing NTA Parquet files
        output_dir: Directory to save plots
        limit: Maximum number of files to process (None = all)
    
    WHAT NTA PLOTS SHOW:
    --------------------
    NTA (Nanoparticle Tracking Analysis) plots display:
    - Size distribution histogram (particle diameter in nm)
    - Cumulative distribution (D10, D50, D90 percentiles)
    - Concentration by size bin (particles/mL per size range)
    
    NTA vs FCS COMPARISON:
    ----------------------
    NTA:
    - Direct size measurement using light scattering + Brownian motion
    - Accurate for 30-1000nm particles
    - Lower throughput (~1000 particles/measurement)
    - Gold standard for exosome sizing
    
    FCS:
    - Indirect size from FSC intensity (needs calibration)
    - High throughput (10,000+ particles/second)
    - Better for marker analysis (fluorescence)
    
    TYPICAL NTA OUTPUT:
    -------------------
    - Peak size: 80-120nm (exosome range)
    - D50 (median): ~90nm
    - D90/D10 ratio: Polydispersity indicator
    - Concentration: 1e9-1e11 particles/mL
    
    HOW IT WORKS:
    -------------
    1. Find all .parquet files in NTA directory
    2. Loop through files with progress bar
    3. Call generate_nta_plots() for each file
    4. Save histogram + cumulative distribution
    5. Count successes and failures
    6. Report summary
    """
    # Step 1: Find all NTA Parquet files
    # -----------------------------------
    # NTA files are stored as .parquet after conversion from CSV
    nta_files = list(input_dir.glob("*.parquet"))
    
    # Check if directory contains any NTA files
    if not nta_files:
        logger.error(f"No Parquet files found in {input_dir}")
        return  # Exit if no files found
    
    logger.info(f"Found {len(nta_files)} NTA files")
    
    # Step 2: Limit processing if specified
    # -------------------------------------
    # Useful for testing: --limit 5 processes only first 5 files
    if limit:
        nta_files = nta_files[:limit]
        logger.info(f"Processing first {limit} files")
    
    # Step 3: Initialize counters
    # ---------------------------
    success_count = 0  # Successfully generated plots
    error_count = 0    # Failed to generate plots
    
    # Step 4: Process each NTA file
    # -----------------------------
    # tqdm() provides progress bar: [====>  ] 50/100 files
    for nta_file in tqdm(nta_files, desc="Generating NTA plots"):
        try:
            # Generate plots for this NTA measurement
            # This creates:
            # - Size distribution histogram (linear scale)
            # - Size distribution histogram (log scale)
            # - Cumulative distribution curve
            generate_nta_plots(nta_file, output_dir=output_dir)
            success_count += 1
            
        except Exception as e:
            # Log error but continue with next file
            # Common errors:
            # - Invalid data format (corrupted file)
            # - Missing required columns (size, concentration)
            # - Zero particles detected (failed measurement)
            logger.error(f"Failed to process {nta_file.name}: {e}")
            error_count += 1
    
    # Step 5: Report summary statistics
    # ---------------------------------
    logger.success(f"✅ Complete! {success_count} files processed, {error_count} errors")


def main():
    parser = argparse.ArgumentParser(
        description="Batch generate NTA size distribution plots"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/parquet/nta/measurements"),
        help="Directory containing NTA Parquet files"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("figures/nta"),
        help="Directory to save plots"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of files to process"
    )
    
    args = parser.parse_args()
    
    # Validate input directory
    if not args.input_dir.exists():
        logger.error(f"Input directory not found: {args.input_dir}")
        sys.exit(1)
    
    # Run batch processing
    batch_generate_nta_plots(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        limit=args.limit
    )


if __name__ == "__main__":
    main()
