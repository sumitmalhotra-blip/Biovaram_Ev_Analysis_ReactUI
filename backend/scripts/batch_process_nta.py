"""
Batch NTA File Processor
Processes all NTA files in specified directories and converts to Parquet format
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from loguru import logger

from src.parsers.nta_parser import NTAParser
from src.config.settings import (
    NTA_RAW_DIR,
    NTA_PARQUET_DIR,
    NTA_STATS_DIR,
    LOGS_DIR
)


def setup_logger():
    """Configure logger for batch processing."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"batch_nta_processing_{timestamp}.log"
    
    # Remove default handler
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # Add file handler
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="DEBUG"
    )
    
    logger.info(f"Logging to: {log_file}")
    return log_file


def find_nta_files(base_dir: Path) -> Dict[str, List[Path]]:
    """
    Find all NTA text files in directory.
    
    Args:
        base_dir: Base directory to search
        
    Returns:
        Dictionary mapping file types to file paths
    """
    nta_files = {
        'size': [],
        'prof': [],
        '11pos': [],
        'other': []
    }
    
    # Find all .txt files
    for txt_file in base_dir.rglob('*.txt'):
        filename = txt_file.name.lower()
        
        # Classify by filename pattern
        if '_11pos' in filename:
            nta_files['11pos'].append(txt_file)
        elif '_prof_' in filename:
            nta_files['prof'].append(txt_file)
        elif '_size_' in filename:
            nta_files['size'].append(txt_file)
        else:
            nta_files['other'].append(txt_file)
    
    return nta_files


def process_single_file(file_path: Path, output_dir: Path) -> Dict[str, Any]:
    """
    Process a single NTA file.
    
    Args:
        file_path: Path to NTA file
        output_dir: Output directory for Parquet files
        
    Returns:
        Processing result dictionary
    """
    result = {
        'file_path': str(file_path),
        'file_name': file_path.name,
        'success': False,
        'error': None,
        'num_rows': 0,
        'output_file': None,
        'sample_id': None,
        'measurement_type': None,
        'processing_time_seconds': 0
    }
    
    start_time = datetime.now()
    
    try:
        # Create parser
        parser = NTAParser(file_path)
        
        # Validate file
        if not parser.validate():
            result['error'] = "Validation failed"
            return result
        
        # Parse file
        df = parser.parse()
        
        if df.empty:
            result['error'] = "No data parsed"
            return result
        
        result['num_rows'] = len(df)
        result['sample_id'] = parser.sample_id
        result['measurement_type'] = parser.measurement_type
        
        # Create output filename
        # Format: {sample_id}_{measurement_type}.parquet
        output_filename = f"{parser.sample_id}_{parser.measurement_type}.parquet"
        output_path = output_dir / output_filename
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to Parquet
        parser.to_parquet(output_path, compression='snappy')
        
        result['output_file'] = str(output_path)
        result['success'] = True
        
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Error processing {file_path.name}: {e}")
    
    finally:
        end_time = datetime.now()
        result['processing_time_seconds'] = (end_time - start_time).total_seconds()
    
    return result


def process_batch(
    nta_files: List[Path],
    output_dir: Path,
    max_workers: int | None = None
) -> List[Dict[str, Any]]:
    """
    Process multiple NTA files in parallel.
    
    Args:
        nta_files: List of NTA file paths
        output_dir: Output directory for Parquet files
        max_workers: Maximum number of parallel workers
        
    Returns:
        List of processing results
    """
    results = []
    
    logger.info(f"Processing {len(nta_files)} NTA files...")
    
    # Process files in parallel
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(process_single_file, file_path, output_dir): file_path
            for file_path in nta_files
        }
        
        # Collect results as they complete
        for i, future in enumerate(as_completed(future_to_file), 1):
            file_path = future_to_file[future]
            
            try:
                result = future.result()
                results.append(result)
                
                if result['success']:
                    logger.info(
                        f"[{i}/{len(nta_files)}] Γ£ô {file_path.name}: "
                        f"{result['num_rows']} rows ΓåÆ {Path(result['output_file']).name}"
                    )
                else:
                    logger.warning(
                        f"[{i}/{len(nta_files)}] Γ£ù {file_path.name}: {result['error']}"
                    )
                    
            except Exception as e:
                logger.error(f"[{i}/{len(nta_files)}] Γ£ù {file_path.name}: {e}")
                results.append({
                    'file_path': str(file_path),
                    'file_name': file_path.name,
                    'success': False,
                    'error': str(e)
                })
    
    return results


def generate_summary(results: List[Dict[str, Any]], log_file: Path) -> pd.DataFrame:
    """
    Generate summary statistics from processing results.
    
    Args:
        results: List of processing results
        log_file: Path to log file
        
    Returns:
        Summary DataFrame
    """
    # Convert to DataFrame
    df_results = pd.DataFrame(results)
    
    # Calculate statistics
    total_files = len(results)
    successful = df_results['success'].sum()
    failed = total_files - successful
    success_rate = (successful / total_files * 100) if total_files > 0 else 0
    
    total_rows = df_results[df_results['success']]['num_rows'].sum()
    avg_processing_time = df_results[df_results['success']]['processing_time_seconds'].mean()
    
    # Print summary
    logger.info("\n" + "="*80)
    logger.info("BATCH PROCESSING SUMMARY")
    logger.info("="*80)
    logger.info(f"Total files processed:    {total_files}")
    logger.info(f"Successful:               {successful} ({success_rate:.1f}%)")
    logger.info(f"Failed:                   {failed}")
    logger.info(f"Total data rows:          {total_rows:,}")
    logger.info(f"Avg processing time:      {avg_processing_time:.3f}s")
    logger.info(f"Log file:                 {log_file}")
    logger.info("="*80 + "\n")
    
    # Group by measurement type
    if successful > 0:
        logger.info("Files by measurement type:")
        type_counts = df_results[df_results['success']].groupby('measurement_type').size()
        for mtype, count in type_counts.items():
            logger.info(f"  {mtype}: {count} files")
        logger.info("")
    
    # Show failed files if any
    if failed > 0:
        logger.warning(f"\nFailed files ({failed}):")
        failed_df = df_results[~df_results['success']]
        for idx, row in failed_df.iterrows():
            logger.warning(f"  {row['file_name']}: {row['error']}")
        logger.info("")
    
    return df_results


def main():
    """Main batch processing function."""
    # Setup logging
    log_file = setup_logger()
    
    logger.info("Starting NTA Batch Processing")
    logger.info(f"Input directory:  {NTA_RAW_DIR}")
    logger.info(f"Output directory: {NTA_PARQUET_DIR}\n")
    
    # Find all NTA files
    nta_files_by_type = find_nta_files(NTA_RAW_DIR)
    
    total_files = sum(len(files) for files in nta_files_by_type.values())
    logger.info(f"Found {total_files} NTA files:")
    for file_type, files in nta_files_by_type.items():
        if files:
            logger.info(f"  {file_type}: {len(files)} files")
    logger.info("")
    
    # Collect all files to process
    all_files = []
    for file_type, files in nta_files_by_type.items():
        all_files.extend(files)
    
    if not all_files:
        logger.error("No NTA files found!")
        return
    
    # Process all files
    start_time = datetime.now()
    results = process_batch(all_files, NTA_PARQUET_DIR, max_workers=8)
    end_time = datetime.now()
    
    # Generate summary
    df_results = generate_summary(results, log_file)
    
    # Save processing log
    log_csv = NTA_STATS_DIR / f"processing_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    NTA_STATS_DIR.mkdir(parents=True, exist_ok=True)
    df_results.to_csv(log_csv, index=False)
    logger.info(f"Processing log saved to: {log_csv}")
    
    # Calculate total time
    total_time = (end_time - start_time).total_seconds()
    logger.info(f"\nTotal processing time: {total_time:.2f}s ({total_time/60:.2f} minutes)")
    logger.info(f"Files per minute: {len(all_files) / (total_time/60):.1f}")
    
    logger.info("\nΓ£ô Batch processing complete!")


if __name__ == "__main__":
    main()
