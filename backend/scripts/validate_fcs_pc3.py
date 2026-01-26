"""
TASK-FACS-001: Parse and Validate NanoFACS PC3 Data
===================================================
This script parses all FCS files from the PC3 NanoFACS experiment (Dec 17, 2025)
and extracts key statistics for validation.

Created: January 20, 2026
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.fcs_parser import FCSParser
import numpy as np
import pandas as pd
import json
from loguru import logger


def parse_fcs_file(file_path: Path) -> dict:
    """
    Parse a single FCS file and extract key statistics.
    
    Args:
        file_path: Path to FCS file
        
    Returns:
        Dictionary with parsed data and statistics
    """
    # Use Dict[str, Any] type to allow mixed value types
    result: dict = {
        'file': file_path.name,
        'status': 'pending',
    }
    
    try:
        parser = FCSParser(file_path)
        if not parser.validate():
            result['status'] = 'validation_failed'
            return result
        
        data = parser.parse()
        
        result['status'] = 'success'
        result['total_events'] = len(data)
        result['sample_id'] = parser.sample_id
        result['channels'] = [c for c in data.columns if not c.startswith(('sample_', 'biological_', 'measurement_', 'is_', 'file_', 'instrument_', 'parse_'))]
        result['num_channels'] = len(result['channels'])
        
        # Extract scatter channel statistics
        scatter_channels = {
            'VFSC-H': 'Forward Scatter Height',
            'VFSC-A': 'Forward Scatter Area',
            'VSSC1-H': 'Violet Side Scatter Height',
            'VSSC1-A': 'Violet Side Scatter Area',
            'VSSC2-H': 'Side Scatter 2 Height',
            'BSSC-H': 'Blue Side Scatter Height',
        }
        
        result['scatter_stats'] = {}
        for channel, description in scatter_channels.items():
            if channel in data.columns:
                # Convert to numpy array to avoid pandas ArrayLike type issues
                values = np.asarray(data[channel].values, dtype=np.float64)
                # Filter out negative values for meaningful stats
                positive_values = values[values > 0]
                
                result['scatter_stats'][channel] = {
                    'description': description,
                    'min': float(np.min(values)),
                    'max': float(np.max(values)),
                    'mean': float(np.mean(values)),
                    'median': float(np.median(values)),
                    'std': float(np.std(values)),
                    'positive_events': int(len(positive_values)),
                    'positive_pct': round(100 * len(positive_values) / len(values), 2),
                }
        
        # Extract fluorescence channel statistics
        fluor_channels = ['V447-H', 'B531-H', 'Y595-H', 'R670-H', 'R710-H', 'R792-H']
        result['fluorescence_stats'] = {}
        for channel in fluor_channels:
            if channel in data.columns:
                # Convert to numpy array to avoid pandas ArrayLike type issues
                values = np.asarray(data[channel].values, dtype=np.float64)
                positive_values = values[values > 0]
                
                result['fluorescence_stats'][channel] = {
                    'min': float(np.min(values)),
                    'max': float(np.max(values)),
                    'mean': float(np.mean(values)),
                    'median': float(np.median(values)),
                    'positive_events': int(len(positive_values)),
                    'positive_pct': round(100 * len(positive_values) / len(values), 2),
                }
        
        # Store raw data reference for later analysis
        result['data_shape'] = list(data.shape)
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        import traceback
        result['traceback'] = traceback.format_exc()
    
    return result


def parse_all_fcs_files():
    """Parse all FCS files from the PC3 NanoFACS experiment."""
    
    fcs_dir = Path(__file__).parent.parent / 'nanoFACS' / 'Exp_20251217_PC3'
    fcs_files = sorted(fcs_dir.glob('*.fcs'))
    
    print("=" * 80)
    print("🔬 TASK-FACS-001: Parse NanoFACS PC3 FCS Files")
    print("=" * 80)
    print(f"\nFound {len(fcs_files)} FCS files in {fcs_dir}\n")
    
    # Categorize files
    categories = {
        'main_sample': [],
        'markers': [],
        'controls': [],
        'blanks': [],
        'water': [],
    }
    
    for f in fcs_files:
        name = f.name.lower()
        if 'pc3 exo' in name and 'cd' not in name:
            categories['main_sample'].append(f)
        elif 'exo+cd' in name:
            categories['markers'].append(f)
        elif 'cd' in name and 'exo' not in name:
            categories['controls'].append(f)
        elif 'blank' in name:
            categories['blanks'].append(f)
        elif 'water' in name or 'hplc' in name:
            categories['water'].append(f)
        else:
            categories['controls'].append(f)
    
    print("File Categories:")
    for cat, files in categories.items():
        print(f"  {cat}: {len(files)} files")
    
    all_results = []
    
    # Parse each category
    for category, files in categories.items():
        if not files:
            continue
            
        print(f"\n{'='*60}")
        print(f"📁 Category: {category.upper()}")
        print("=" * 60)
        
        for file_path in files:
            print(f"\n📊 {file_path.name}")
            print("-" * 50)
            
            result = parse_fcs_file(file_path)
            result['category'] = category
            all_results.append(result)
            
            if result['status'] == 'success':
                print(f"   ✅ Status: Success")
                print(f"   Total Events: {result['total_events']:,}")
                print(f"   Channels: {result['num_channels']}")
                
                # Print scatter stats for main sample
                if 'scatter_stats' in result and 'VFSC-H' in result['scatter_stats']:
                    stats = result['scatter_stats']['VFSC-H']
                    print(f"   VFSC-H (Forward Scatter):")
                    print(f"      Range: {stats['min']:.0f} - {stats['max']:.0f}")
                    print(f"      Mean: {stats['mean']:.1f}, Median: {stats['median']:.1f}")
                    print(f"      Positive Events: {stats['positive_pct']:.1f}%")
            else:
                print(f"   ❌ Status: {result['status']}")
                if 'error' in result:
                    print(f"   Error: {result['error']}")
    
    return all_results


def analyze_main_sample(results: list):
    """Detailed analysis of the main PC3 EXO1 sample."""
    
    main_samples = [r for r in results if r['category'] == 'main_sample' and r['status'] == 'success']
    
    if not main_samples:
        print("\n⚠️  No main sample found!")
        return
    
    print("\n" + "=" * 80)
    print("📊 DETAILED ANALYSIS: PC3 EXO1 Main Sample")
    print("=" * 80)
    
    sample = main_samples[0]
    
    print(f"\nFile: {sample['file']}")
    print(f"Total Events: {sample['total_events']:,}")
    print(f"Channels: {sample['num_channels']}")
    
    print("\n### Scatter Channels ###")
    print("\n| Channel | Min | Max | Mean | Median | Positive % |")
    print("|---------|-----|-----|------|--------|------------|")
    
    for ch, stats in sample.get('scatter_stats', {}).items():
        print(f"| {ch:8} | {stats['min']:,.0f} | {stats['max']:,.0f} | {stats['mean']:,.1f} | {stats['median']:,.1f} | {stats['positive_pct']:.1f}% |")
    
    print("\n### Fluorescence Channels ###")
    print("\n| Channel | Min | Max | Mean | Positive % |")
    print("|---------|-----|-----|------|------------|")
    
    for ch, stats in sample.get('fluorescence_stats', {}).items():
        print(f"| {ch:8} | {stats['min']:,.0f} | {stats['max']:,.0f} | {stats['mean']:,.1f} | {stats['positive_pct']:.1f}% |")


def compare_samples(results: list):
    """Compare event counts across different sample types."""
    
    print("\n" + "=" * 80)
    print("📈 SAMPLE COMPARISON SUMMARY")
    print("=" * 80)
    
    print("\n| Category | File | Events | VFSC-H Mean | VSSC1-H Mean |")
    print("|----------|------|--------|-------------|--------------|")
    
    for r in sorted(results, key=lambda x: (x['category'], x['file'])):
        if r['status'] != 'success':
            continue
        
        vfsc_mean = r.get('scatter_stats', {}).get('VFSC-H', {}).get('mean', 'N/A')
        vssc_mean = r.get('scatter_stats', {}).get('VSSC1-H', {}).get('mean', 'N/A')
        
        vfsc_str = f"{vfsc_mean:,.1f}" if isinstance(vfsc_mean, (int, float)) else vfsc_mean
        vssc_str = f"{vssc_mean:,.1f}" if isinstance(vssc_mean, (int, float)) else vssc_mean
        
        print(f"| {r['category']:10} | {r['file'][:30]:30} | {r['total_events']:,} | {vfsc_str:>11} | {vssc_str:>12} |")


def save_results(results: list):
    """Save parsing results to JSON."""
    
    output_dir = Path(__file__).parent.parent / 'data' / 'validation'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save full results
    output_file = output_dir / 'fcs_pc3_parsed_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n💾 Results saved to: {output_file}")
    
    # Save summary CSV
    summary_data = []
    for r in results:
        if r['status'] == 'success':
            row = {
                'file': r['file'],
                'category': r['category'],
                'total_events': r['total_events'],
                'num_channels': r['num_channels'],
            }
            # Add scatter stats
            for ch in ['VFSC-H', 'VFSC-A', 'VSSC1-H']:
                if ch in r.get('scatter_stats', {}):
                    row[f'{ch}_mean'] = r['scatter_stats'][ch]['mean']
                    row[f'{ch}_median'] = r['scatter_stats'][ch]['median']
            summary_data.append(row)
    
    if summary_data:
        df = pd.DataFrame(summary_data)
        csv_file = output_dir / 'fcs_pc3_summary.csv'
        df.to_csv(csv_file, index=False)
        print(f"💾 Summary CSV: {csv_file}")


if __name__ == '__main__':
    # Parse all files
    results = parse_all_fcs_files()
    
    # Detailed analysis of main sample
    analyze_main_sample(results)
    
    # Compare samples
    compare_samples(results)
    
    # Save results
    save_results(results)
    
    # Summary
    success_count = sum(1 for r in results if r['status'] == 'success')
    print(f"\n" + "=" * 80)
    print(f"✅ TASK-FACS-001 Complete!")
    print(f"   Successfully parsed: {success_count}/{len(results)} files")
    print("=" * 80)
