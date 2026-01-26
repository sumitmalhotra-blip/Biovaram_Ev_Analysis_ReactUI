"""
TASK-NTA-001: Parse and Validate NTA PC3 Data
==============================================
This script parses all NTA files from the PC3 experiment (Dec 17, 2025)
and extracts key statistics for validation against machine reports.

Created: January 20, 2026
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.nta_parser import NTAParser
import numpy as np
import pandas as pd
import json

def calculate_nta_statistics(data: pd.DataFrame) -> dict:
    """
    Calculate key NTA statistics from size distribution data.
    
    Args:
        data: DataFrame with size_nm and particle_count columns
        
    Returns:
        Dictionary with calculated statistics
    """
    # Filter to EV-relevant size range (0-1000nm)
    ev_data = data[(data['size_nm'] >= 0) & (data['size_nm'] <= 1000)].copy()
    
    sizes = np.asarray(ev_data['size_nm'].values, dtype=np.float64)
    counts = np.asarray(ev_data['particle_count'].values, dtype=np.float64)
    
    # Only use bins with particles
    mask = counts > 0
    sizes_with_particles = sizes[mask]
    counts_with_particles = counts[mask]
    
    if len(counts_with_particles) == 0:
        return {'error': 'No particles found'}
    
    total_particles = float(np.sum(counts_with_particles))
    
    # Weighted mean
    weighted_mean = np.average(sizes_with_particles, weights=counts_with_particles)
    
    # Weighted median (D50) - cumulative distribution approach
    cumsum = np.cumsum(counts_with_particles)
    median_idx = np.searchsorted(cumsum, total_particles / 2)
    weighted_median = sizes_with_particles[min(median_idx, len(sizes_with_particles)-1)]
    
    # Mode (bin with most particles)
    mode_idx = int(np.argmax(counts_with_particles))
    mode_size = sizes_with_particles[mode_idx]
    
    # Weighted standard deviation
    variance = np.average((sizes_with_particles - weighted_mean)**2, weights=counts_with_particles)
    weighted_std = np.sqrt(variance)
    
    # D10 and D90 (10th and 90th percentile)
    d10_idx = np.searchsorted(cumsum, total_particles * 0.10)
    d90_idx = np.searchsorted(cumsum, total_particles * 0.90)
    d10 = sizes_with_particles[min(d10_idx, len(sizes_with_particles)-1)]
    d90 = sizes_with_particles[min(d90_idx, len(sizes_with_particles)-1)]
    
    return {
        'total_particles': int(total_particles),
        'mean_nm': round(float(weighted_mean), 2),
        'median_d50_nm': round(float(weighted_median), 2),
        'mode_nm': round(float(mode_size), 2),
        'std_nm': round(float(weighted_std), 2),
        'd10_nm': round(float(d10), 2),
        'd90_nm': round(float(d90), 2),
        'min_size_nm': round(float(np.min(sizes_with_particles)), 2),
        'max_size_nm': round(float(np.max(sizes_with_particles)), 2),
        'num_bins_with_particles': int(np.sum(mask))
    }


def parse_all_nta_files():
    """Parse all NTA PC3 files and return results."""
    nta_dir = Path(__file__).parent.parent / 'NTA' / 'PC3'
    nta_files = list(nta_dir.glob('*.txt'))
    
    print(f"Found {len(nta_files)} NTA text files in {nta_dir}\n")
    print("=" * 80)
    
    all_results = []
    
    for file_path in sorted(nta_files):
        print(f"\n📊 Processing: {file_path.name}")
        print("-" * 60)
        
        try:
            parser = NTAParser(file_path)
            if not parser.validate():
                print(f"  ❌ Validation failed!")
                continue
                
            data = parser.parse()
            
            # Extract metadata
            metadata = {
                'sample_name': parser.raw_metadata.get('sample_name', 'N/A'),
                'experiment': parser.raw_metadata.get('experiment', 'N/A'),
                'date': parser.raw_metadata.get('date', 'N/A'),
                'dilution': parser.measurement_params.get('dilution', 'N/A'),
                'laser_wavelength': parser.measurement_params.get('laser_wavelength', 'N/A'),
                'temperature': parser.measurement_params.get('temperature', 'N/A'),
                'viscosity': parser.measurement_params.get('viscosity', 'N/A'),
                'detected_particles': parser.measurement_params.get('detected_particles', 'N/A'),
                'avg_particles_per_frame': parser.measurement_params.get('avg_particles', 'N/A'),
                'num_traces': parser.measurement_params.get('num_traces', 'N/A'),
            }
            
            # Calculate statistics
            stats = calculate_nta_statistics(data)
            
            # Combine
            result = {
                'file': file_path.name,
                **metadata,
                **stats
            }
            all_results.append(result)
            
            # Print results
            print(f"  Sample Name: {metadata['sample_name']}")
            print(f"  Date: {metadata['date']}")
            print(f"  Dilution Factor: {metadata['dilution']}x")
            print(f"  Laser Wavelength: {metadata['laser_wavelength']} nm")
            print(f"  Temperature: {metadata['temperature']}°C")
            print()
            print("  📈 Size Distribution Statistics:")
            print(f"     Total Particles: {stats['total_particles']}")
            print(f"     Mean Size: {stats['mean_nm']} nm")
            print(f"     Median D50: {stats['median_d50_nm']} nm")
            print(f"     Mode: {stats['mode_nm']} nm")
            print(f"     Std Dev: {stats['std_nm']} nm")
            print(f"     D10-D90: {stats['d10_nm']} - {stats['d90_nm']} nm")
            print(f"     Size Range: {stats['min_size_nm']} - {stats['max_size_nm']} nm")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    return all_results


def compare_with_machine_reports(results: list):
    """
    Compare our calculated values with machine-reported values.
    
    Machine report values from the .txt file headers:
    - Median Number (D50): This is the machine's calculated median
    """
    print("\n" + "=" * 80)
    print("📋 COMPARISON WITH MACHINE REPORT VALUES")
    print("=" * 80)
    
    # Machine-reported D50 values (from file headers)
    # These are extracted from "Median Number (D50):" lines in the files
    machine_d50 = {
        'PC3_100kDa_F5': 127.34,  # From 20251217_0005 file
        # Will need to extract others from their respective files
    }
    
    print("\n| Sample | Our D50 (nm) | Machine D50 (nm) | Difference | % Error |")
    print("|--------|--------------|------------------|------------|---------|")
    
    for result in results:
        sample = result['sample_name']
        our_d50 = result['median_d50_nm']
        
        if sample in machine_d50:
            m_d50 = machine_d50[sample]
            diff = our_d50 - m_d50
            pct_error = abs(diff / m_d50) * 100
            status = "✅" if pct_error < 10 else "⚠️"
            print(f"| {sample} | {our_d50} | {m_d50} | {diff:+.2f} | {pct_error:.1f}% {status} |")
        else:
            print(f"| {sample} | {our_d50} | TBD | - | - |")


def save_results(results: list):
    """Save results to JSON file for later comparison."""
    output_dir = Path(__file__).parent.parent / 'data' / 'validation'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'nta_pc3_parsed_results.json'
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    
    # Also save as CSV for easy viewing
    df = pd.DataFrame(results)
    csv_file = output_dir / 'nta_pc3_parsed_results.csv'
    df.to_csv(csv_file, index=False)
    print(f"💾 CSV saved to: {csv_file}")


def extract_machine_d50_from_files():
    """Extract machine-reported D50 values from file headers."""
    import re
    
    nta_dir = Path(__file__).parent.parent / 'NTA' / 'PC3'
    nta_files = list(nta_dir.glob('*.txt'))
    
    print("\n" + "=" * 80)
    print("🔍 EXTRACTING MACHINE-REPORTED D50 VALUES FROM FILES")
    print("=" * 80)
    
    machine_values = {}
    
    for file_path in sorted(nta_files):
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(3000)  # Read header section
        
        # Look for "Median Number (D50):" line
        match = re.search(r'Median Number \(D50\):\s*([\d.]+)', content)
        if match:
            d50 = float(match.group(1))
            
            # Get sample name
            sample_match = re.search(r'Sample:\s*(.+)', content)
            sample_name = sample_match.group(1).strip() if sample_match else file_path.stem
            
            machine_values[sample_name] = d50
            print(f"  {file_path.name}: D50 = {d50} nm (Sample: {sample_name})")
    
    return machine_values


if __name__ == '__main__':
    print("=" * 80)
    print("🔬 TASK-NTA-001: NTA PC3 Data Parsing & Validation")
    print("=" * 80)
    
    # First extract machine D50 values
    machine_d50 = extract_machine_d50_from_files()
    
    # Parse all files
    results = parse_all_nta_files()
    
    # Create comparison table
    print("\n" + "=" * 80)
    print("📋 FINAL COMPARISON: Our Values vs Machine Values")
    print("=" * 80)
    
    print("\n| Sample | Our D50 | Machine D50 | Diff | % Error | Status |")
    print("|--------|---------|-------------|------|---------|--------|")
    
    for result in results:
        sample = result['sample_name']
        our_d50 = result['median_d50_nm']
        
        if sample in machine_d50:
            m_d50 = machine_d50[sample]
            diff = our_d50 - m_d50
            pct_error = abs(diff / m_d50) * 100
            status = "✅ PASS" if pct_error < 10 else "⚠️ CHECK"
            print(f"| {sample:20} | {our_d50:7.2f} | {m_d50:11.2f} | {diff:+6.2f} | {pct_error:6.1f}% | {status} |")
        else:
            print(f"| {sample:20} | {our_d50:7.2f} | {'N/A':>11} | {'N/A':>6} | {'N/A':>6} | - |")
    
    # Save results
    save_results(results)
    
    print("\n✅ TASK-NTA-001 Complete!")
