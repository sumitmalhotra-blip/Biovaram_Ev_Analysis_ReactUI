"""
Create FCS Statistics Aggregation - Task 1.3 Subtask 1.2
=========================================================

Purpose:
- Parse processing_log CSV from batch FCS processing
- Create comprehensive fcs_statistics.parquet file
- Include sample_id, biological_sample_id, QC flags, event counts, channel info

Input:
- logs/processing_log_*.csv (from batch_process_fcs.py)

Output:
- data/parquet/nanofacs/statistics/fcs_statistics.parquet

Author: CRMIT Team
Date: November 17, 2025
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


def parse_fcs_processing_log(log_file: Path) -> pd.DataFrame:
    """
    Parse FCS processing log CSV and extract statistics.
    
    Args:
        log_file: Path to processing_log CSV file
    
    Returns:
        DataFrame with FCS statistics
    """
    logger.info(f"📂 Reading FCS processing log: {log_file}")
    
    # Read processing log
    df = pd.read_csv(log_file)
    
    logger.info(f"   - Found {len(df)} FCS files processed")
    logger.info(f"   - Success: {len(df[df['status'] == 'success'])}")
    logger.info(f"   - Failed: {len(df[df['status'] != 'success'])}")
    
    return df


def create_fcs_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create comprehensive FCS statistics DataFrame.
    
    Args:
        df: Raw processing log DataFrame
    
    Returns:
        Standardized FCS statistics DataFrame
    """
    logger.info("🔧 Creating FCS statistics...")
    
    # Filter successful processing only
    df_success = df[df['status'] == 'success'].copy()
    
    logger.info(f"   - Processing {len(df_success)} successful samples")
    
    # Create statistics DataFrame
    stats = pd.DataFrame()
    
    # Basic identification
    stats['sample_id'] = df_success['sample_id']
    stats['biological_sample_id'] = df_success['biological_sample_id']
    stats['file_name'] = df_success['file_name']
    stats['file_path'] = df_success['file_path']
    
    # Event counts
    stats['total_events'] = df_success['total_events'].astype(int)
    stats['events_parsed'] = df_success['events_parsed'].astype(int)
    
    # Channel information
    stats['channel_count'] = df_success['channel_count'].astype(int)
    stats['channels'] = df_success['channels']
    
    # Quality control flags
    stats['is_baseline'] = df_success['is_baseline'].astype(bool)
    stats['qc_passed'] = df_success['qc_passed'].astype(bool)
    stats['qc_warnings'] = df_success['qc_warnings'].astype(int)
    stats['qc_errors'] = df_success['qc_errors'].astype(int)
    
    # File size metrics
    stats['input_size_mb'] = df_success['input_size_mb'].astype(float)
    stats['output_size_mb'] = df_success['output_size_mb'].astype(float)
    stats['compression_ratio'] = df_success['compression_ratio'].astype(float)
    
    # Processing metadata
    stats['processing_time_seconds'] = df_success['processing_time_seconds'].astype(float)
    stats['output_file'] = df_success['output_file']
    processing_dates = pd.to_datetime(df_success['start_time'])
    stats['processing_date'] = [d.date() for d in processing_dates]
    
    # Add instrument type
    stats['instrument_type'] = 'flow_cytometry'
    
    # Add data availability flag
    stats['has_event_data'] = True
    
    # Calculate derived metrics
    events_per_sec = stats['total_events'] / stats['processing_time_seconds']
    stats['events_per_second'] = events_per_sec.round(0)
    
    # Calculate compression percentage
    comp_ratio = 1 - (stats['output_size_mb'] / stats['input_size_mb'])
    comp_pct = comp_ratio * 100
    stats['compression_percentage'] = pd.Series(comp_pct).round(2)
    
    # Sort by sample_id
    stats = stats.sort_values('sample_id').reset_index(drop=True)
    
    logger.info(f"   ✅ Created statistics for {len(stats)} samples")
    
    return stats


def identify_sample_groups(stats: pd.DataFrame) -> pd.DataFrame:
    """
    Identify experimental groups based on sample naming patterns.
    
    Args:
        stats: FCS statistics DataFrame
    
    Returns:
        DataFrame with group annotations
    """
    logger.info("🏷️  Identifying experimental groups...")
    
    stats = stats.copy()
    
    # Initialize group columns
    stats['experiment_type'] = 'unknown'
    stats['antibody'] = None
    stats['antibody_concentration_ug'] = None
    stats['purification_method'] = None
    stats['is_control'] = False
    stats['is_water_control'] = False
    stats['is_blank'] = False
    
    for idx, row in stats.iterrows():
        sample_id = str(row['sample_id']).lower()
        
        # Water controls
        if 'water' in sample_id or 'hplc' in sample_id:
            stats.at[idx, 'is_water_control'] = True
            stats.at[idx, 'is_control'] = True
            stats.at[idx, 'experiment_type'] = 'water_control'
        
        # Blank controls
        elif 'blank' in sample_id:
            stats.at[idx, 'is_blank'] = True
            stats.at[idx, 'is_control'] = True
            stats.at[idx, 'experiment_type'] = 'blank_control'
        
        # Isotype controls (baseline)
        elif 'iso' in sample_id:
            stats.at[idx, 'antibody'] = 'isotype_control'
            stats.at[idx, 'experiment_type'] = 'exosome_antibody'
            
            # Extract concentration
            if '0.25' in sample_id:
                stats.at[idx, 'antibody_concentration_ug'] = 0.25
            elif '1ug' in sample_id or '1 ug' in sample_id:
                stats.at[idx, 'antibody_concentration_ug'] = 1.0
            elif '2ug' in sample_id or '2 ug' in sample_id:
                stats.at[idx, 'antibody_concentration_ug'] = 2.0
            
            # Purification method
            if 'sec' in sample_id:
                stats.at[idx, 'purification_method'] = 'SEC'
            elif 'centri' in sample_id:
                stats.at[idx, 'purification_method'] = 'centrifugation'
        
        # CD81 antibody
        elif 'cd81' in sample_id:
            stats.at[idx, 'antibody'] = 'CD81'
            stats.at[idx, 'experiment_type'] = 'exosome_antibody'
            
            # Extract concentration
            if '0.25' in sample_id:
                stats.at[idx, 'antibody_concentration_ug'] = 0.25
            elif '1ug' in sample_id or '1 ug' in sample_id:
                stats.at[idx, 'antibody_concentration_ug'] = 1.0
            elif '2ug' in sample_id or '2 ug' in sample_id:
                stats.at[idx, 'antibody_concentration_ug'] = 2.0
            
            # Purification method
            if 'sec' in sample_id:
                stats.at[idx, 'purification_method'] = 'SEC'
            elif 'centri' in sample_id:
                stats.at[idx, 'purification_method'] = 'centrifugation'
        
        # CD9 antibody
        elif 'cd9' in sample_id:
            stats.at[idx, 'antibody'] = 'CD9'
            stats.at[idx, 'experiment_type'] = 'exosome_antibody'
        
        # CD63 antibody
        elif 'cd63' in sample_id:
            stats.at[idx, 'antibody'] = 'CD63'
            stats.at[idx, 'experiment_type'] = 'exosome_antibody'
        
        # Exosome control
        elif 'exo' in sample_id and 'control' in sample_id:
            stats.at[idx, 'experiment_type'] = 'exosome_control'
            stats.at[idx, 'is_control'] = True
        
        # Media controls
        elif 'media' in sample_id:
            stats.at[idx, 'experiment_type'] = 'media_control'
            stats.at[idx, 'is_control'] = True
    
    # Count experimental groups
    group_counts = stats['experiment_type'].value_counts()
    logger.info("   Experimental groups identified:")
    for exp_type, count in group_counts.items():
        logger.info(f"      - {exp_type}: {count} samples")
    
    baseline_count = stats['is_baseline'].sum()
    logger.info(f"   - Baseline samples (isotype controls): {baseline_count}")
    
    return stats


def generate_summary_statistics(stats: pd.DataFrame) -> dict:
    """
    Generate summary statistics for reporting.
    
    Args:
        stats: FCS statistics DataFrame
    
    Returns:
        Dictionary with summary metrics
    """
    summary = {
        'total_samples': len(stats),
        'total_events': int(stats['total_events'].sum()),
        'avg_events_per_sample': int(stats['total_events'].mean()),
        'min_events': int(stats['total_events'].min()),
        'max_events': int(stats['total_events'].max()),
        'total_channels': int(stats['channel_count'].iloc[0]) if len(stats) > 0 else 0,
        'qc_passed': int(stats['qc_passed'].sum()),
        'qc_failed': int((~stats['qc_passed']).sum()),
        'baseline_samples': int(stats['is_baseline'].sum()),
        'test_samples': int((~stats['is_baseline']).sum()),
        'total_size_gb': float((stats['output_size_mb'].sum() / 1024).round(3)),
        'avg_compression_pct': round(float(stats['compression_percentage'].mean()), 2),
    }
    
    return summary


def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("🚀 FCS STATISTICS AGGREGATION - Task 1.3 Subtask 1.2")
    logger.info("=" * 80)
    
    # Define paths
    project_root = Path(__file__).parent.parent
    logs_dir = project_root / 'logs'
    output_dir = project_root / 'data' / 'parquet' / 'nanofacs' / 'statistics'
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find processing log (most recent)
    log_files = sorted(logs_dir.glob('processing_log_*.csv'), reverse=True)
    
    if not log_files:
        logger.error("❌ No processing log files found!")
        logger.info("   Please run: python scripts/batch_process_fcs.py")
        sys.exit(1)
    
    log_file = log_files[0]
    logger.info(f"📂 Using log file: {log_file.name}")
    
    # Step 1: Parse processing log
    df = parse_fcs_processing_log(log_file)
    
    # Step 2: Create statistics
    stats = create_fcs_statistics(df)
    
    # Step 3: Identify experimental groups
    stats = identify_sample_groups(stats)
    
    # Step 4: Generate summary
    logger.info("\n📊 Generating summary statistics...")
    summary = generate_summary_statistics(stats)
    
    logger.info("\n📋 FCS Dataset Summary:")
    logger.info(f"   - Total samples: {summary['total_samples']}")
    logger.info(f"   - Total events: {summary['total_events']:,}")
    logger.info(f"   - Average events/sample: {summary['avg_events_per_sample']:,}")
    logger.info(f"   - Event range: {summary['min_events']:,} - {summary['max_events']:,}")
    logger.info(f"   - QC passed: {summary['qc_passed']}/{summary['total_samples']}")
    logger.info(f"   - Baseline samples: {summary['baseline_samples']}")
    logger.info(f"   - Total data size: {summary['total_size_gb']} GB")
    logger.info(f"   - Average compression: {summary['avg_compression_pct']}%")
    
    # Step 5: Save statistics
    output_file = output_dir / 'fcs_statistics.parquet'
    logger.info(f"\n💾 Saving FCS statistics to: {output_file}")
    
    stats.to_parquet(output_file, index=False, compression='snappy')
    
    file_size_mb = output_file.stat().st_size / (1024 * 1024)
    logger.info(f"   ✅ Saved: {output_file.name} ({file_size_mb:.2f} MB)")
    logger.info(f"   - Dimensions: {stats.shape[0]} samples × {stats.shape[1]} features")
    
    # Also save summary as JSON
    import json
    summary_file = output_dir / 'fcs_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    logger.info(f"   ✅ Saved summary: {summary_file.name}")
    
    # Save CSV version for easy viewing
    csv_file = output_dir / 'fcs_statistics.csv'
    stats.to_csv(csv_file, index=False)
    logger.info(f"   ✅ Saved CSV: {csv_file.name}")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ FCS STATISTICS AGGREGATION COMPLETE")
    logger.info("=" * 80)
    
    return output_file


if __name__ == "__main__":
    main()
