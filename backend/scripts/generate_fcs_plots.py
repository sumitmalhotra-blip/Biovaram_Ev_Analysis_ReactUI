"""
Batch FCS Plot Generation Script

Processes all FCS Parquet files and generates scatter plots for each sample.

Usage:
    python scripts/generate_fcs_plots.py [--limit N] [--output-dir PATH]

Author: GitHub Copilot
Date: November 14, 2025
Task: 1.3.1 - Batch FCS Visualization
"""

import sys
from pathlib import Path
import argparse
from tqdm import tqdm
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.visualization.fcs_plots import generate_fcs_plots
from loguru import logger


def batch_generate_fcs_plots(
    input_dir: Path,
    output_dir: Path,
    limit: int | None = None
) -> None:
    """
    Generate plots for all FCS Parquet files in a directory.
    
    Args:
        input_dir: Directory containing FCS Parquet files
        output_dir: Directory to save plots
        limit: Maximum number of files to process (None = all)
    
    HOW IT WORKS:
    -------------
    1. Find all .parquet files in input directory
    2. Optionally limit to first N files (for testing)
    3. Loop through files with progress bar
    4. Generate plots for each file (scatter, histograms)
    5. Count successes and failures
    6. Report summary statistics
    
    WHAT PLOTS ARE GENERATED:
    -------------------------
    For each FCS file, generates:
    - FSC vs SSC scatter plot (particle size vs complexity)
    - FSC histogram (size distribution)
    - SSC histogram (granularity distribution)
    - Optional: Fluorescence channels if present
    
    ERROR HANDLING:
    ---------------
    - Individual file failures don't stop the batch
    - Errors are logged but processing continues
    - Final summary shows success/error counts
    """
    # Step 1: Find all FCS Parquet files in input directory
    # ------------------------------------------------------
    # glob("*.parquet") finds all files ending with .parquet
    # Returns a list of Path objects
    fcs_files = list(input_dir.glob("*.parquet"))
    
    # Check if any files were found
    if not fcs_files:
        logger.error(f"No Parquet files found in {input_dir}")
        return  # Exit early if no files
    
    logger.info(f"Found {len(fcs_files)} FCS files")
    
    # Step 2: Limit number of files if specified
    # ------------------------------------------
    # Useful for testing without processing all files
    # Example: --limit 5 will process only first 5 files
    if limit:
        fcs_files = fcs_files[:limit]  # Take only first 'limit' files
        logger.info(f"Processing first {limit} files")
    
    # Step 3: Initialize counters for summary report
    # ----------------------------------------------
    success_count = 0  # How many files processed successfully
    error_count = 0    # How many files failed
    
    # Step 4: Process each file with progress bar
    # -------------------------------------------
    # tqdm() shows a progress bar: [=====>    ] 50/100 files
    # desc= sets the label shown before the progress bar
    for fcs_file in tqdm(fcs_files, desc="Generating FCS plots"):
        try:
            # Call the plot generation function from src.visualization
            # This function handles:
            # - Loading Parquet file into DataFrame
            # - Creating matplotlib figures (scatter, histograms)
            # - Auto-scaling axes based on data distribution
            # - Saving PNG/PDF files to output_dir
            generate_fcs_plots(fcs_file, output_dir=output_dir)
            
            success_count += 1  # Increment success counter
            
        except Exception as e:
            # If any error occurs, log it but continue processing other files
            # Common errors:
            # - FileNotFoundError: Parquet file deleted/moved
            # - KeyError: Missing required columns (FSC-A, SSC-A)
            # - MemoryError: File too large
            # - IOError: Can't write to output directory
            logger.error(f"Failed to process {fcs_file.name}: {e}")
            error_count += 1  # Increment error counter
    
    # Step 5: Report final summary
    # ----------------------------
    # logger.success() prints in green color with checkmark emoji
    # Shows how many files succeeded and how many failed
    logger.success(f"✅ Complete! {success_count} files processed, {error_count} errors")


def main():
    """
    Main entry point for command-line execution.
    
    COMMAND-LINE USAGE:
    -------------------
    # Process all files in default directory
    python scripts/generate_fcs_plots.py
    
    # Process only first 10 files (for testing)
    python scripts/generate_fcs_plots.py --limit 10
    
    # Use custom input/output directories
    python scripts/generate_fcs_plots.py \\
        --input-dir data/parquet/experiment1 \\
        --output-dir figures/experiment1
    """
    # Step 1: Set up argument parser
    # -------------------------------
    # argparse handles command-line arguments like --input-dir, --limit
    parser = argparse.ArgumentParser(
        description="Batch generate FCS scatter plots"
    )
    
    # Argument 1: Input directory containing Parquet files
    # ----------------------------------------------------
    # --input-dir: Long form (user-friendly)
    # type=Path: Convert string argument to Path object
    # default=...: Value used if argument not provided
    # help=...: Description shown in --help output
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/parquet/nanofacs/events"),
        help="Directory containing FCS Parquet files"
    )
    
    # Argument 2: Output directory for saving plots
    # ---------------------------------------------
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("figures/fcs"),
        help="Directory to save plots"
    )
    
    # Argument 3: Limit number of files (optional)
    # -------------------------------------------
    # type=int: Convert to integer
    # default=None: Process all files if not specified
    # Useful for testing without processing hundreds of files
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of files to process"
    )
    
    # Step 2: Parse command-line arguments
    # ------------------------------------
    # Converts sys.argv list into args object
    # Example: ["script.py", "--limit", "5"] → args.limit = 5
    args = parser.parse_args()
    
    # Step 3: Validate input directory exists
    # ---------------------------------------
    # Check if user-specified directory exists before processing
    # Fail fast with clear error message if not found
    if not args.input_dir.exists():
        logger.error(f"Input directory not found: {args.input_dir}")
        sys.exit(1)  # Exit with error code 1 (indicates failure)
    
    # Step 4: Run batch processing
    # ----------------------------
    # Call the main processing function with parsed arguments
    batch_generate_fcs_plots(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        limit=args.limit
    )


if __name__ == "__main__":
    main()
