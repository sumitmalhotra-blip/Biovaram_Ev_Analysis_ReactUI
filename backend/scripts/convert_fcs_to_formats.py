#!/usr/bin/env python3
"""
FCS File Batch Converter
========================
Converts all FCS files to Excel and Parquet formats while preserving folder structure.

Task: T-005 from Dec 22, 2025 Meeting
Author: Sumit Malhotra
Date: December 23, 2025
"""

import sys
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import traceback

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pandas as pd
import numpy as np

# Import flowio for FCS parsing (numpy 2.x compatible)
import flowio  # type: ignore


def parse_fcs_file(fcs_path: Path) -> tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Parse an FCS file and return DataFrame with events and metadata dict.
    
    Args:
        fcs_path: Path to FCS file
        
    Returns:
        Tuple of (events DataFrame, metadata dict)
    """
    # Try with ignore_offset_error for files with offset issues
    try:
        fcs_data = flowio.FlowData(str(fcs_path))
    except Exception:
        fcs_data = flowio.FlowData(str(fcs_path), ignore_offset_error=True)
    
    # Get channel names - prefer pXs (short/descriptive name like VFSC-H) over pXn (generic like FSC-H)
    # flowio uses lowercase keys (p1n, p1s) not uppercase ($P1N, $P1S)
    channel_count = fcs_data.channel_count
    channel_names = []
    for i in range(1, channel_count + 1):
        # Priority: pXs (short name with detector info) > pXn (generic name) > fallback
        name = (
            fcs_data.text.get(f'p{i}s', '') or  # VFSC-H, VSSC1-A, B531-H, etc.
            fcs_data.text.get(f'p{i}n', '') or  # FSC-H, SSC-A, FL1-H, etc.
            fcs_data.text.get(f'$P{i}S', '') or 
            fcs_data.text.get(f'$P{i}N', '') or 
            f'Channel_{i}'
        )
        name = name.strip() if name else f'Channel_{i}'
        channel_names.append(name)
    
    # Convert events to DataFrame
    events = np.array(fcs_data.events).reshape(-1, channel_count)
    df = pd.DataFrame(events, columns=channel_names)
    
    # Extract metadata
    metadata = dict(fcs_data.text)
    
    # Add file info columns
    df['_source_file'] = fcs_path.name
    df['_event_index'] = range(len(df))
    
    # Build metadata summary
    meta_summary = {
        'filename': fcs_path.name,
        'filepath': str(fcs_path),
        'num_events': len(df),
        'num_channels': len(channel_names),
        'channels': channel_names,
        'file_size_bytes': fcs_path.stat().st_size,
        'parsed_at': datetime.now().isoformat(),
    }
    
    # Add FCS-specific metadata if available
    for key in ['$FIL', '$DATE', '$BTIM', '$ETIM', '$CYT', '$SRC', '$SYS']:
        if key in metadata:
            meta_summary[key.replace('$', '')] = metadata[key]
    
    return df, meta_summary


def convert_to_excel(df: pd.DataFrame, metadata: Dict[str, Any], output_path: Path) -> None:
    """
    Convert DataFrame to CSV (much faster than Excel for large datasets).
    
    Args:
        df: Events DataFrame
        metadata: Metadata dictionary
        output_path: Path for output .csv file (changed from xlsx for performance)
    """
    # Change extension to csv
    output_path = output_path.with_suffix('.csv')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write events data to CSV
    df.to_csv(output_path, index=False)
    
    # Write metadata to separate JSON file
    meta_path = output_path.with_name(output_path.stem + '_metadata.json')
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2, default=str)


def convert_to_parquet(df: pd.DataFrame, metadata: Dict[str, Any], output_path: Path) -> None:
    """
    Convert DataFrame to Parquet format.
    
    Args:
        df: Events DataFrame
        metadata: Metadata dictionary
        output_path: Path for output .parquet file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Store metadata as parquet file metadata
    df.to_parquet(
        output_path,
        engine='pyarrow',
        compression='snappy',
        index=False
    )
    
    # Also save metadata as separate JSON file
    meta_path = output_path.with_suffix('.metadata.json')
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2, default=str)


def sanitize_folder_name(name: str) -> str:
    """Sanitize folder name for filesystem compatibility."""
    return name.replace(' ', '_').replace('+', '_plus_').replace('&', '_and_')


def main():
    """Main conversion function."""
    print("=" * 70)
    print("FCS File Batch Converter - T-005")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Define paths
    base_dir = Path(__file__).parent.parent  # backend/
    output_base = base_dir / 'data' / 'converted_fcs'
    csv_dir = output_base / 'csv'
    parquet_dir = output_base / 'parquet'
    
    # Source folders to process
    source_folders = [
        (base_dir / 'nanoFACS' / '10000 exo and cd81', '10000_exo_and_cd81'),
        (base_dir / 'nanoFACS' / 'CD9 and exosome lots', 'CD9_and_exosome_lots'),
        (base_dir / 'nanoFACS' / 'EV_HEK_TFF_DATA_05Dec25', 'EV_HEK_TFF_DATA_05Dec25'),
        (base_dir / 'nanoFACS' / 'EXP 6-10-2025', 'EXP_6-10-2025'),
        (base_dir / 'data' / 'uploads', 'uploads'),
        (base_dir.parent / 'data' / 'uploads', 'frontend_uploads'),
    ]
    
    # Create output directories
    csv_dir.mkdir(parents=True, exist_ok=True)
    parquet_dir.mkdir(parents=True, exist_ok=True)
    
    # Track results
    results = {
        'total_files': 0,
        'successful': 0,
        'failed': 0,
        'files': [],
        'errors': [],
    }
    
    # Process each source folder
    for source_path, output_folder in source_folders:
        if not source_path.exists():
            print(f"⚠️  Skipping (not found): {source_path}")
            continue
        
        fcs_files = list(source_path.glob('*.fcs'))
        if not fcs_files:
            print(f"⚠️  No FCS files in: {source_path}")
            continue
        
        print(f"\n📁 Processing: {output_folder} ({len(fcs_files)} files)")
        print("-" * 50)
        
        for fcs_file in sorted(fcs_files):
            results['total_files'] += 1
            file_stem = fcs_file.stem.replace(' ', '_').replace('+', '_')
            
            try:
                print(f"  📄 {fcs_file.name}...", end=' ', flush=True)
                
                # Parse FCS file
                df, metadata = parse_fcs_file(fcs_file)
                
                # Convert to CSV
                csv_path = csv_dir / output_folder / f"{file_stem}.csv"
                convert_to_excel(df, metadata, csv_path)
                
                # Convert to Parquet
                parquet_path = parquet_dir / output_folder / f"{file_stem}.parquet"
                convert_to_parquet(df, metadata, parquet_path)
                
                results['successful'] += 1
                results['files'].append({
                    'source': str(fcs_file),
                    'csv': str(csv_path),
                    'parquet': str(parquet_path),
                    'events': metadata['num_events'],
                    'channels': metadata['num_channels'],
                    'channel_names': metadata['channels'],
                })
                
                print(f"✅ ({metadata['num_events']:,} events, {metadata['num_channels']} channels)")
                
            except Exception as e:
                results['failed'] += 1
                error_msg = f"{fcs_file.name}: {str(e)}"
                results['errors'].append(error_msg)
                print(f"❌ Error: {str(e)[:50]}")
                traceback.print_exc()
    
    # Generate summary report
    print("\n" + "=" * 70)
    print("CONVERSION SUMMARY")
    print("=" * 70)
    print(f"Total FCS files found: {results['total_files']}")
    print(f"Successfully converted: {results['successful']}")
    print(f"Failed: {results['failed']}")
    print(f"\nOutput locations:")
    print(f"  CSV:     {csv_dir}")
    print(f"  Parquet: {parquet_dir}")
    
    # Save summary report
    summary_path = output_base / 'conversion_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSummary saved to: {summary_path}")
    
    # Print errors if any
    if results['errors']:
        print(f"\n⚠️  Errors ({len(results['errors'])}):")
        for err in results['errors']:
            print(f"   - {err}")
    
    print(f"\n✅ Conversion complete at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return results


if __name__ == '__main__':
    main()
