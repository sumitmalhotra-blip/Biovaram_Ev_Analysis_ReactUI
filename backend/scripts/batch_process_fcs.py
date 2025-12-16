"""
Batch FCS File Processor
========================

PURPOSE:
--------
High-performance batch processing system for converting Flow Cytometry Standard (FCS) files
to efficient Parquet format with comprehensive quality control and metadata extraction.

WHAT IT DOES:
-------------
1. Recursively discovers all .fcs files in input directory
2. Parses FCS binary format and extracts event data
3. Validates file format and data quality
4. Extracts metadata from files (sample IDs, channels, timestamps)
5. Calculates comprehensive statistics per file
6. Converts to compressed Parquet format (10-20× smaller files)
7. Generates processing reports and error logs
8. Tracks quality control metrics across all files

KEY FEATURES:
-------------
- Parallel Processing: Uses multiprocessing to process files simultaneously
- Memory Efficient: Processes files in batches, releases memory after each
- Progress Tracking: Real-time tqdm progress bars for user feedback
- Error Handling: Continues processing even if individual files fail
- Skip Existing: Can resume interrupted batches without reprocessing
- Comprehensive Logging: Detailed logs saved for debugging and auditing
- Quality Reports: Aggregate statistics across all processed files

PERFORMANCE:
------------
- Typical throughput: 10-20 files/minute (depends on file size and CPU)
- Compression ratio: 70-90% (Parquet with Snappy compression)
- Memory usage: ~200-500 MB per worker process
- Recommended: Use MAX_WORKERS = CPU_count - 1

INPUT:
------
- Directory containing .fcs files (can be nested in subdirectories)
- Each FCS file should be FCS 2.0, 3.0, or 3.1 format
- Typical file size: 1-50 MB per file

OUTPUT:
-------
- Parquet files (one per input FCS file) with same name, .parquet extension
- Processing log CSV with per-file statistics
- Error log CSV (if any files failed)
- Summary statistics CSV with aggregate metrics

USAGE EXAMPLE:
--------------
    # Run with default settings
    python scripts/batch_process_fcs.py
    
    # Or import as module
    from scripts.batch_process_fcs import BatchFCSProcessor
    processor = BatchFCSProcessor(input_dir="data/raw/fcs", output_dir="data/parquet")
    results = processor.run(parallel=True)

CONFIGURATION:
--------------
Configured via src/config/settings.py:
- FCS_RAW_DIR: Input directory for .fcs files
- PARQUET_DIR: Output directory for .parquet files
- MAX_WORKERS: Number of parallel processes
- LOGS_DIR: Directory for log files

Author: CRMIT Team
Date: November 14, 2025
Version: 1.0
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import gc
from loguru import logger

# Add src to path to enable imports from project modules
# This allows running script from any directory
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import FCS parser for reading .fcs files
from src.parsers.fcs_parser import FCSParser

# Import configuration settings (paths, processing parameters)
from src.config.settings import (
    PARQUET_DIR,   # Output directory for converted files
    DATA_DIR,      # Root data directory
    LOGS_DIR,      # Directory for processing logs
    FCS_RAW_DIR,   # Input directory with .fcs files
    BATCH_SIZE,    # Number of events to process at once
    MAX_WORKERS    # Number of parallel worker processes
)


class BatchFCSProcessor:
    """
    Production-grade batch processor for Flow Cytometry Standard (FCS) files.
    
    ARCHITECTURE:
    -------------
    This class orchestrates the entire FCS processing pipeline:
    1. File Discovery: Recursive search for .fcs files
    2. Parallel Execution: ProcessPoolExecutor for multi-core processing
    3. Individual Processing: FCSParser for each file
    4. Result Aggregation: Collect statistics from all files
    5. Report Generation: Create comprehensive summary reports
    6. Error Tracking: Log failures without stopping pipeline
    
    WORKFLOW:
    ---------
    find_fcs_files() → process_parallel() → process_single_file() (×N) → 
    generate_summary_report() → save_reports()
    
    STATE MANAGEMENT:
    -----------------
    - self.results: List of all processing results (success + failure)
    - self.errors: List of only failed processing attempts
    - self.input_dir: Source directory for .fcs files
    - self.output_dir: Destination directory for .parquet files
    - self.max_workers: Number of parallel processes
    
    THREAD SAFETY:
    --------------
    Uses ProcessPoolExecutor (not ThreadPoolExecutor) to avoid Python GIL.
    Each file processed in separate process with separate memory space.
    Results collected safely via Future objects.
    
    EXAMPLE:
    --------
    >>> processor = BatchFCSProcessor(
    ...     input_dir=Path("data/raw/fcs"),
    ...     output_dir=Path("data/parquet"),
    ...     max_workers=7,  # For 8-core CPU
    ...     skip_existing=True
    ... )
    >>> results_df = processor.run(parallel=True)
    >>> print(f"Processed {len(results_df)} files")
    """
    
    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        max_workers: int = MAX_WORKERS,
        skip_existing: bool = True
    ):
        """
        Initialize batch processor with configuration and setup logging.
        
        INITIALIZATION SEQUENCE:
        ------------------------
        1. Store configuration parameters
        2. Create output directory structure
        3. Initialize result tracking lists
        4. Configure file-based logging
        5. Log initialization summary
        
        Args:
            input_dir: Path to directory containing .fcs files (searches recursively)
            output_dir: Path to directory for .parquet output files
            max_workers: Number of parallel worker processes
                        Recommended: CPU_count - 1 (leave one core for OS)
                        Set to 1 for sequential processing (debugging)
            skip_existing: If True, skip files that already have .parquet output
                          If False, reprocess all files (overwrite existing)
        
        Creates:
            - output_dir/: Main output directory for parquet files
            - output_dir/../statistics/: Directory for aggregate statistics
            - logs/: Directory for processing logs
        
        Side Effects:
            - Creates directories on filesystem
            - Initializes logger with file output
            - Prints initialization messages to console
        """
        # Store configuration
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.max_workers = max_workers
        self.skip_existing = skip_existing
        
        # Create output directory structure
        # parents=True: create parent directories if needed
        # exist_ok=True: don't fail if directory already exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.stats_dir = self.output_dir.parent / 'statistics'
        self.stats_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure logs directory exists
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Initialize result tracking
        # results: all files (success + failure)
        # errors: only failed files (subset of results)
        self.results: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        
        # Configure logging to file
        # Creates timestamped log file for this processing session
        log_file = LOGS_DIR / f'batch_fcs_processing_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
            level="INFO"
        )
        
        # Log initialization summary
        logger.info(f"Batch FCS Processor initialized")
        logger.info(f"Input directory: {self.input_dir}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Max workers: {self.max_workers}")
    
    def find_fcs_files(self) -> List[Path]:
        """
        Recursively discover all FCS files in input directory.
        
        SEARCH STRATEGY:
        ----------------
        Uses Path.rglob('*.fcs') to recursively search all subdirectories.
        Handles nested folder structures (e.g., organized by experiment date,
        sample type, or operator).
        
        SKIP EXISTING LOGIC:
        --------------------
        If skip_existing=True:
            - For each input.fcs, check if output.parquet exists
            - If exists: skip (log and exclude from processing list)
            - If not exists: include in processing list
        This enables resuming interrupted batch processing without reprocessing.
        
        FILE MATCHING:
        --------------
        Output path: output_dir / "{input_stem}.parquet"
        Example: "sample1.fcs" → "sample1.parquet"
        
        LOGGING:
        --------
        - Logs total files found
        - Logs each skipped file (if skip_existing=True)
        - Logs final count of files needing processing
        
        Returns:
            List[Path]: Paths to .fcs files that need processing
        
        Example:
            >>> processor.input_dir = Path("data/raw/fcs")
            >>> files = processor.find_fcs_files()
            >>> # Found 100 FCS files
            >>> # Skipping sample1.fcs (already processed)
            >>> # ...
            >>> # 85 files need processing
        """
        # Recursively find all .fcs files
        # rglob('*.fcs') searches current directory and all subdirectories
        fcs_files = list(self.input_dir.rglob('*.fcs'))
        logger.info(f"Found {len(fcs_files)} FCS files")
        
        # Filter out already-processed files if requested
        if self.skip_existing:
            # files_to_process will contain only unprocessed files
            files_to_process = []
            for fcs_file in fcs_files:
                # Check if corresponding parquet file exists
                parquet_file = self.output_dir / f"{fcs_file.stem}.parquet"
                if not parquet_file.exists():
                    # No parquet output → needs processing
                    files_to_process.append(fcs_file)
                else:
                    # Parquet exists → skip
                    logger.info(f"Skipping {fcs_file.name} (already processed)")
            
            logger.info(f"{len(files_to_process)} files need processing")
            return files_to_process
        
        # If not skipping, return all found files
        return fcs_files
    
    def process_single_file(self, fcs_path: Path) -> Dict[str, Any]:
        """
        Process a single FCS file through complete pipeline.
        
        PROCESSING PIPELINE:
        --------------------
        1. Initialize FCSParser instance
        2. Validate FCS file format and structure
        3. Parse binary FCS data to DataFrame
        4. Extract metadata (sample IDs, instrument info, etc.)
        5. Calculate comprehensive statistics
        6. Run quality control checks
        7. Save to Parquet format with compression
        8. Calculate performance metrics
        9. Return detailed result dictionary
        
        ERROR HANDLING:
        ---------------
        Uses try-except-finally pattern:
        - Try: Complete processing pipeline
        - Except: Catch any exception, log error, return error result
        - Finally: Force garbage collection (release memory)
        
        This ensures one file's failure doesn't stop the entire batch.
        
        RESULT DICTIONARY STRUCTURE:
        ----------------------------
        Success case:
        {
            'file_name': 'sample1.fcs',
            'file_path': '/path/to/sample1.fcs',
            'status': 'success',
            'start_time': datetime(...),
            'end_time': datetime(...),
            'processing_time_seconds': 2.5,
            'output_file': '/path/to/sample1.parquet',
            'output_size_mb': 1.2,
            'input_size_mb': 10.5,
            'compression_ratio': 0.886,  # 88.6% smaller
            'events_parsed': 150000,
            'channels': 12,
            'sample_id': 'S001',
            'biological_sample_id': 'EXO_L5_F10',
            'is_baseline': False,
            'qc_passed': True,
            'qc_warnings': 0,
            'qc_errors': 0,
            'total_events': 150000,
            'channel_count': 12
        }
        
        Failure case:
        {
            'file_name': 'corrupted.fcs',
            'file_path': '/path/to/corrupted.fcs',
            'status': 'error' or 'validation_failed',
            'start_time': datetime(...),
            'end_time': datetime(...),
            'error': 'Detailed error message'
        }
        
        MEMORY MANAGEMENT:
        ------------------
        After processing each file, explicitly calls gc.collect() to
        release memory. This prevents memory accumulation during large
        batch processing (100s of files).
        
        Args:
            fcs_path: Path to .fcs file to process
            
        Returns:
            Dict[str, Any]: Processing result with status and metrics
        
        Side Effects:
            - Creates .parquet file in output_dir
            - Logs processing progress and results
            - Triggers garbage collection
        """
        # Initialize result dictionary with basic info
        result = {
            'file_name': fcs_path.name,
            'file_path': str(fcs_path),
            'status': 'processing',
            'start_time': datetime.now(),
            'error': None
        }
        
        try:
            # Step 1: Initialize parser
            # FCSParser handles binary FCS format, metadata extraction,
            # and conversion to DataFrame
            parser = FCSParser(fcs_path)
            
            # Step 2: Validate file format
            # Checks FCS header, file structure, required channels
            if not parser.validate():
                result['status'] = 'validation_failed'
                result['error'] = 'File validation failed'
                return result
            
            # Step 3: Parse FCS binary data
            # Returns DataFrame with all events (rows) and channels (columns)
            data = parser.parse()
            
            # Step 4: Extract metadata
            # Gets sample IDs, instrument info, acquisition parameters
            metadata = parser.extract_metadata()
            
            # Step 5: Calculate statistics
            # Computes per-channel statistics: mean, median, std, ranges
            statistics = parser.get_statistics()
            
            # Step 6: Quality validation
            # Checks for anomalies, saturation, low event count, etc.
            qc_results = parser.validate_quality()
            
            # Step 7: Save to Parquet format
            # Uses Snappy compression for good balance of speed/size
            output_path = self.output_dir / f"{fcs_path.stem}.parquet"
            parser.to_parquet(output_path)
            
            # Step 8: Calculate performance metrics
            end_time = datetime.now()
            processing_time = (end_time - result['start_time']).total_seconds()
            output_size_mb = output_path.stat().st_size / (1024 * 1024)
            input_size_mb = fcs_path.stat().st_size / (1024 * 1024)
            compression_ratio = 1 - (output_path.stat().st_size / fcs_path.stat().st_size)
            
            # Step 9: Update result dictionary with all metrics
            result.update({
                'status': 'success',
                'end_time': end_time,
                'processing_time_seconds': processing_time,
                'output_file': str(output_path),
                'output_size_mb': output_size_mb,
                'input_size_mb': input_size_mb,
                'compression_ratio': compression_ratio,
                'events_parsed': len(data),
                'channels': len(parser.channel_names),
                'sample_id': parser.sample_id,
                'biological_sample_id': parser.biological_sample_id,
                'is_baseline': parser.is_baseline,
                'qc_passed': qc_results['passed'],
                'qc_warnings': len(qc_results.get('warnings', [])),
                'qc_errors': len(qc_results.get('errors', []))
            })
            
            # Add statistics summary if available
            if '_summary' in statistics:
                summary = statistics['_summary']
                result['total_events'] = summary['total_events']
                result['channel_count'] = summary['channel_count']
            
            # Log success
            logger.info(f"✅ Processed {fcs_path.name}: {len(data):,} events → {result['output_size_mb']:.2f} MB")
            
        except Exception as e:
            # Handle any error during processing
            result['status'] = 'error'
            result['error'] = str(e)
            result['end_time'] = datetime.now()
            logger.error(f"❌ Failed to process {fcs_path.name}: {e}")
        
        finally:
            # Force garbage collection to release memory
            # Important for batch processing to prevent memory accumulation
            gc.collect()
        
        return result
    
    def process_parallel(self, fcs_files: List[Path]) -> None:
        """
        Process FCS files in parallel.
        
        Args:
            fcs_files: List of FCS files to process
        """
        logger.info(f"Starting parallel processing with {self.max_workers} workers")
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self.process_single_file, fcs_file): fcs_file
                for fcs_file in fcs_files
            }
            
            # Process completed tasks with progress bar
            with tqdm(total=len(fcs_files), desc="Processing FCS files", unit="file") as pbar:
                for future in as_completed(future_to_file):
                    fcs_file = future_to_file[future]
                    try:
                        result = future.result()
                        self.results.append(result)
                        
                        if result['status'] == 'error':
                            self.errors.append(result)
                    
                    except Exception as e:
                        error_result = {
                            'file_name': fcs_file.name,
                            'file_path': str(fcs_file),
                            'status': 'exception',
                            'error': str(e)
                        }
                        self.errors.append(error_result)
                        self.results.append(error_result)
                        logger.error(f"Exception processing {fcs_file.name}: {e}")
                    
                    pbar.update(1)
    
    def process_sequential(self, fcs_files: List[Path]) -> None:
        """
        Process FCS files sequentially (for debugging).
        
        Args:
            fcs_files: List of FCS files to process
        """
        logger.info("Starting sequential processing")
        
        for fcs_file in tqdm(fcs_files, desc="Processing FCS files", unit="file"):
            result = self.process_single_file(fcs_file)
            self.results.append(result)
            
            if result['status'] == 'error':
                self.errors.append(result)
    
    def generate_summary_report(self) -> pd.DataFrame:
        """
        Generate summary statistics from all processed files.
        
        Returns:
            DataFrame with summary statistics
        """
        if not self.results:
            logger.warning("No results to summarize")
            return pd.DataFrame()
        
        # Convert results to DataFrame
        results_df = pd.DataFrame(self.results)
        
        # Summary statistics
        logger.info("\n" + "="*60)
        logger.info("BATCH PROCESSING SUMMARY")
        logger.info("="*60)
        logger.info(f"Total files: {len(self.results)}")
        logger.info(f"Successful: {len(results_df[results_df['status'] == 'success'])}")
        logger.info(f"Failed: {len(self.errors)}")
        
        if len(results_df[results_df['status'] == 'success']) > 0:
            success_df = results_df[results_df['status'] == 'success']
            
            total_events = success_df['events_parsed'].sum()
            total_input_size = success_df['input_size_mb'].sum()
            total_output_size = success_df['output_size_mb'].sum()
            avg_compression = success_df['compression_ratio'].mean() * 100
            total_time = success_df['processing_time_seconds'].sum()
            avg_time = success_df['processing_time_seconds'].mean()
            
            logger.info(f"\nProcessing Statistics:")
            logger.info(f"  Total events parsed: {total_events:,}")
            logger.info(f"  Total input size: {total_input_size:.2f} MB")
            logger.info(f"  Total output size: {total_output_size:.2f} MB")
            logger.info(f"  Average compression: {avg_compression:.1f}%")
            logger.info(f"  Total processing time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
            logger.info(f"  Average time per file: {avg_time:.2f} seconds")
            logger.info(f"  Processing speed: {len(success_df) / (total_time/60):.1f} files/minute")
            
            # QC summary
            qc_passed = len(success_df[success_df['qc_passed'] == True])
            qc_failed = len(success_df[success_df['qc_passed'] == False])
            logger.info(f"\nQuality Control:")
            logger.info(f"  Passed: {qc_passed}")
            logger.info(f"  Failed: {qc_failed}")
            logger.info(f"  Pass rate: {qc_passed/len(success_df)*100:.1f}%")
            
            # Baseline summary
            baseline_count = len(success_df[success_df['is_baseline'] == True])
            test_count = len(success_df[success_df['is_baseline'] == False])
            logger.info(f"\nSample Types:")
            logger.info(f"  Baseline (ISO): {baseline_count}")
            logger.info(f"  Test samples: {test_count}")
        
        if self.errors:
            logger.error(f"\nΓÜá∩╕Å  {len(self.errors)} files failed to process:")
            for error in self.errors[:5]:  # Show first 5 errors
                logger.error(f"  - {error['file_name']}: {error['error']}")
            if len(self.errors) > 5:
                logger.error(f"  ... and {len(self.errors) - 5} more")
        
        logger.info("="*60 + "\n")
        
        return results_df
    
    def save_reports(self) -> None:
        """
        Save processing reports to CSV files.
        """
        if not self.results:
            logger.warning("No results to save")
            return
        
        # Save processing log
        results_df = pd.DataFrame(self.results)
        log_file = LOGS_DIR / f'processing_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        results_df.to_csv(log_file, index=False)
        logger.info(f"Processing log saved: {log_file}")
        
        # Save error log if there are errors
        if self.errors:
            error_df = pd.DataFrame(self.errors)
            error_file = LOGS_DIR / f'errors_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            error_df.to_csv(error_file, index=False)
            logger.error(f"Error log saved: {error_file}")
        
        # Generate aggregate statistics
        success_df = results_df[results_df['status'] == 'success']
        if len(success_df) > 0:
            aggregate_stats = {
                'total_files': len(self.results),
                'successful': len(success_df),
                'failed': len(self.errors),
                'total_events': success_df['events_parsed'].sum(),
                'total_input_mb': success_df['input_size_mb'].sum(),
                'total_output_mb': success_df['output_size_mb'].sum(),
                'avg_compression_pct': success_df['compression_ratio'].mean() * 100,
                'total_processing_seconds': success_df['processing_time_seconds'].sum(),
                'qc_passed_count': len(success_df[success_df['qc_passed'] == True]),
                'baseline_count': len(success_df[success_df['is_baseline'] == True]),
                'test_count': len(success_df[success_df['is_baseline'] == False])
            }
            
            stats_df = pd.DataFrame([aggregate_stats])
            stats_file = self.stats_dir / 'batch_summary.csv'
            stats_df.to_csv(stats_file, index=False)
            logger.info(f"Summary statistics saved: {stats_file}")
    
    def run(self, parallel: bool = True) -> pd.DataFrame:
        """
        Run the batch processing pipeline.
        
        Args:
            parallel: Use parallel processing (True) or sequential (False)
            
        Returns:
            DataFrame with processing results
        """
        start_time = datetime.now()
        
        # Find FCS files
        fcs_files = self.find_fcs_files()
        
        if not fcs_files:
            logger.warning("No FCS files found to process")
            return pd.DataFrame()
        
        # Process files
        if parallel and self.max_workers > 1:
            self.process_parallel(fcs_files)
        else:
            self.process_sequential(fcs_files)
        
        # Generate reports
        results_df = self.generate_summary_report()
        self.save_reports()
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        logger.info(f"Batch processing complete in {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
        
        return results_df


def main():
    """Main entry point for batch FCS processing."""
    
    print("\n" + "="*60)
    print("CRMIT FCS Batch Processor")
    print("="*60 + "\n")
    
    # Configuration
    input_dir = FCS_RAW_DIR
    output_dir = PARQUET_DIR / 'nanofacs' / 'events'
    
    # Check if input directory exists
    if not input_dir.exists():
        print(f"Γ¥î Error: Input directory not found: {input_dir}")
        print(f"Please ensure FCS files are in: {input_dir}")
        return
    
    print(f"≡ƒôü Input directory: {input_dir}")
    print(f"≡ƒôü Output directory: {output_dir}")
    print(f"≡ƒöº Max workers: {MAX_WORKERS}")
    print()
    
    # Initialize processor
    processor = BatchFCSProcessor(
        input_dir=input_dir,
        output_dir=output_dir,
        max_workers=MAX_WORKERS,
        skip_existing=True
    )
    
    # Run processing
    try:
        results = processor.run(parallel=True)
        
        if len(results) > 0:
            print("\nΓ£à Batch processing completed successfully!")
            print(f"≡ƒôè Results saved to: {LOGS_DIR}")
            print(f"≡ƒôª Parquet files saved to: {output_dir}")
        else:
            print("\nΓÜá∩╕Å  No files were processed")
    
    except KeyboardInterrupt:
        print("\n\nΓÜá∩╕Å  Processing interrupted by user")
        logger.warning("Processing interrupted by user")
    
    except Exception as e:
        print(f"\nΓ¥î Error during processing: {e}")
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
