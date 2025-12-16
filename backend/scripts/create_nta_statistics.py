"""
Create NTA Statistics Aggregation - Task 1.3 Subtask 1.3
========================================================

Purpose:
- Read all NTA measurement parquet files
- Extract size distribution statistics (D10, D50, D90, concentration)
- Create comprehensive nta_statistics.parquet file
- Calculate uniformity metrics, temperature compliance

Input:
- data/parquet/nta/measurements/*.parquet (from batch_process_nta.py)

Output:
- data/parquet/nta/statistics/nta_statistics.parquet

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


def load_nta_measurements(measurements_dir: Path) -> list:
    """
    Load all NTA measurement parquet files.
    
    Args:
        measurements_dir: Directory containing NTA parquet files
    
    Returns:
        List of (file_path, DataFrame) tuples
    """
    logger.info(f"📂 Loading NTA measurements from: {measurements_dir}")
    
    parquet_files = list(measurements_dir.glob('*.parquet'))
    
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found in {measurements_dir}")
    
    logger.info(f"   - Found {len(parquet_files)} NTA files")
    
    measurements = []
    for file_path in sorted(parquet_files):
        try:
            df = pd.read_parquet(file_path)
            measurements.append((file_path, df))
        except Exception as e:
            logger.warning(f"   ⚠️  Failed to load {file_path.name}: {e}")
    
    logger.info(f"   ✅ Successfully loaded {len(measurements)} files")
    
    return measurements


def extract_sample_metadata(file_path: Path, df: pd.DataFrame) -> dict:
    """
    Extract sample metadata from NTA file.
    
    Args:
        file_path: Path to NTA file
        df: NTA measurements DataFrame
    
    Returns:
        Dictionary with sample metadata
    """
    filename = file_path.stem
    
    # Parse filename: EV_IP_P1_F7-1000_size
    parts = filename.split('_')
    
    metadata = {
        'file_name': file_path.name,
        'sample_id': filename,
        'file_path': str(file_path),
    }
    
    # Extract passage and fraction
    passage = None
    fraction = None
    dilution = None
    measurement_type = None
    
    for part in parts:
        part_lower = part.lower()
        
        # Passage (P1, P2, P2.1, etc.)
        if part.startswith('P') and len(part) > 1:
            passage = part
        
        # Fraction (F5-1000, F10-1000, etc.)
        if part.startswith('F') and '-' in part:
            frac_parts = part.split('-')
            fraction = frac_parts[0]  # F5, F10, etc.
            if len(frac_parts) > 1:
                dilution_str = frac_parts[1].replace('R1', '').replace('R2', '').replace('R', '')
                try:
                    dilution = int(dilution_str)
                except:
                    pass
        
        # Measurement type (size, prof, 11pos_size)
        if 'size' in part_lower:
            measurement_type = '11pos_size' if '11pos' in part_lower else 'size'
        elif 'prof' in part_lower:
            measurement_type = 'profile'
    
    # Create biological sample ID (e.g., P1_F7)
    if passage and fraction:
        metadata['biological_sample_id'] = f"{passage}_{fraction}"
    else:
        metadata['biological_sample_id'] = filename
    
    metadata['passage'] = str(passage) if passage is not None else ''
    metadata['fraction'] = str(fraction) if fraction is not None else ''
    metadata['dilution_factor'] = str(dilution) if dilution is not None else ''
    metadata['measurement_type'] = str(measurement_type) if measurement_type is not None else ''
    
    # Check for replicate indicators
    is_replicate = any(r in filename for r in ['R1', 'R2', 'R3'])
    metadata['is_replicate'] = str(is_replicate)
    
    # Extract temperature from DataFrame if available
    if 'temperature' in df.columns:
        metadata['temperature_c'] = str(df['temperature'].iloc[0]) if len(df) > 0 else ''
    else:
        metadata['temperature_c'] = ''
    
    return metadata


def calculate_size_statistics(df: pd.DataFrame) -> dict:
    """
    Calculate size distribution statistics from NTA data.
    
    Args:
        df: NTA measurements DataFrame with 'size_nm' and 'concentration' columns
    
    Returns:
        Dictionary with size statistics
    """
    stats = {}
    
    # Check required columns
    if 'size_nm' not in df.columns:
        logger.warning("   ⚠️  'size_nm' column not found")
        return stats
    
    size = df['size_nm']
    
    # Basic size statistics
    stats['min_size_nm'] = float(size.min())
    stats['max_size_nm'] = float(size.max())
    stats['mean_size_nm'] = float(size.mean())
    stats['median_size_nm'] = float(size.median())
    stats['std_size_nm'] = float(size.std())
    
    # Calculate D10, D50, D90 (percentiles)
    if 'concentration' in df.columns:
        # Weighted percentiles by concentration
        concentration = df['concentration']
        total_concentration = concentration.sum()
        
        if total_concentration > 0:
            cumsum = (concentration.cumsum() / total_concentration * 100)
            
            # D10: Size at which 10% of particles are smaller
            d10_idx = (cumsum >= 10).idxmax() if any(cumsum >= 10) else 0
            stats['d10_nm'] = float(df.loc[d10_idx, 'size_nm'])
            
            # D50: Median size (50th percentile)
            d50_idx = (cumsum >= 50).idxmax() if any(cumsum >= 50) else len(df) // 2
            stats['d50_nm'] = float(df.loc[d50_idx, 'size_nm'])
            
            # D90: Size at which 90% of particles are smaller
            d90_idx = (cumsum >= 90).idxmax() if any(cumsum >= 90) else len(df) - 1
            stats['d90_nm'] = float(df.loc[d90_idx, 'size_nm'])
            
            # Mode: Size with highest concentration
            mode_idx = concentration.idxmax()
            stats['mode_size_nm'] = float(df.loc[mode_idx, 'size_nm'])
        else:
            # Fallback to simple percentiles
            stats['d10_nm'] = float(size.quantile(0.1))
            stats['d50_nm'] = float(size.quantile(0.5))
            stats['d90_nm'] = float(size.quantile(0.9))
            mode_values = size.mode()
            stats['mode_size_nm'] = float(mode_values.iloc[0]) if len(mode_values) > 0 else float(size.median())
    else:
        # Simple percentiles without concentration weighting
        stats['d10_nm'] = float(size.quantile(0.1))
        stats['d50_nm'] = float(size.quantile(0.5))
        stats['d90_nm'] = float(size.quantile(0.9))
        mode_values = size.mode()
        stats['mode_size_nm'] = float(mode_values.iloc[0]) if len(mode_values) > 0 else float(size.median())
    
    # Size range metrics
    stats['size_range_nm'] = stats['max_size_nm'] - stats['min_size_nm']
    
    # Polydispersity index (PDI) - measure of size distribution width
    # PDI = (D90 - D10) / D50
    if stats['d50_nm'] > 0:
        stats['polydispersity_index'] = (stats['d90_nm'] - stats['d10_nm']) / stats['d50_nm']
    else:
        stats['polydispersity_index'] = None
    
    # Coefficient of variation
    stats['cv_size_percent'] = (stats['std_size_nm'] / stats['mean_size_nm'] * 100) if stats['mean_size_nm'] > 0 else None
    
    return stats


def calculate_concentration_statistics(df: pd.DataFrame) -> dict:
    """
    Calculate concentration statistics from NTA data.
    
    Args:
        df: NTA measurements DataFrame with 'concentration' column
    
    Returns:
        Dictionary with concentration statistics
    """
    stats = {}
    
    if 'concentration' not in df.columns:
        logger.warning("   ⚠️  'concentration' column not found")
        return stats
    
    concentration = df['concentration']
    
    # Basic concentration statistics
    stats['total_concentration_particles_ml'] = float(concentration.sum())
    stats['peak_concentration_particles_ml'] = float(concentration.max())
    stats['mean_concentration_particles_ml'] = float(concentration.mean())
    stats['median_concentration_particles_ml'] = float(concentration.median())
    stats['std_concentration_particles_ml'] = float(concentration.std())
    
    # Coefficient of variation
    if stats['mean_concentration_particles_ml'] > 0:
        stats['cv_concentration_percent'] = (
            stats['std_concentration_particles_ml'] / 
            stats['mean_concentration_particles_ml'] * 100
        )
    else:
        stats['cv_concentration_percent'] = None
    
    return stats


def calculate_size_bin_fractions(df: pd.DataFrame) -> dict:
    """
    Calculate fraction of particles in standard exosome size bins.
    
    Args:
        df: NTA measurements DataFrame
    
    Returns:
        Dictionary with size bin fractions
    """
    stats = {}
    
    if 'size_nm' not in df.columns or 'concentration' not in df.columns:
        return stats
    
    size = df['size_nm']
    concentration = df['concentration']
    total_concentration = concentration.sum()
    
    if total_concentration == 0:
        return stats
    
    # Standard exosome size bins (from CRMIT architecture)
    bins = {
        'small_exosomes_40_80nm': (40, 80),
        'medium_exosomes_80_100nm': (80, 100),
        'large_exosomes_100_120nm': (100, 120),
        'microvesicles_120_200nm': (120, 200),
        'apoptotic_bodies_200_1000nm': (200, 1000),
    }
    
    for bin_name, (min_size, max_size) in bins.items():
        mask = (size >= min_size) & (size < max_size)
        bin_concentration = concentration[mask].sum()
        fraction = (bin_concentration / total_concentration * 100) if total_concentration > 0 else 0
        stats[f'fraction_{bin_name}_percent'] = float(fraction)
    
    # Exosome-relevant range (30-150 nm)
    exo_mask = (size >= 30) & (size <= 150)
    exo_concentration = concentration[exo_mask].sum()
    stats['fraction_exosome_range_30_150nm_percent'] = float(
        (exo_concentration / total_concentration * 100) if total_concentration > 0 else 0
    )
    
    return stats


def assess_measurement_quality(df: pd.DataFrame, metadata: dict) -> dict:
    """
    Assess quality of NTA measurement.
    
    Args:
        df: NTA measurements DataFrame
        metadata: Sample metadata
    
    Returns:
        Dictionary with quality metrics
    """
    quality = {}
    
    # Check minimum data points
    quality['data_point_count'] = len(df)
    quality['has_sufficient_data'] = len(df) >= 10
    
    # Temperature compliance (standard: 20-30°C)
    if metadata.get('temperature_c') is not None:
        temp = metadata['temperature_c']
        quality['temperature_compliant'] = 20 <= temp <= 30
        quality['temperature_deviation_c'] = abs(temp - 25.0)  # 25°C target
    else:
        quality['temperature_compliant'] = None
        quality['temperature_deviation_c'] = None
    
    # Size distribution quality
    if 'size_nm' in df.columns:
        size = df['size_nm']
        
        # Check for reasonable exosome size range (30-200 nm typical)
        in_range = ((size >= 30) & (size <= 200)).sum()
        quality['fraction_in_exosome_range'] = float(in_range / len(df) * 100) if len(df) > 0 else 0
        quality['size_distribution_reasonable'] = quality['fraction_in_exosome_range'] > 50
    
    # Concentration stability (check for outliers)
    if 'concentration' in df.columns:
        concentration = df['concentration']
        
        # Calculate Z-scores
        mean_conc = concentration.mean()
        std_conc = concentration.std()
        
        if std_conc > 0:
            z_scores = np.abs((concentration - mean_conc) / std_conc)
            outliers = (z_scores > 3).sum()
            quality['concentration_outliers'] = int(outliers)
            quality['concentration_stable'] = outliers < len(df) * 0.1  # Less than 10% outliers
        else:
            quality['concentration_outliers'] = 0
            quality['concentration_stable'] = True
    
    # Overall QC pass
    quality['qc_passed'] = (
        quality.get('has_sufficient_data', False) and
        quality.get('size_distribution_reasonable', False) and
        quality.get('concentration_stable', True)
    )
    
    return quality


def create_nta_statistics(measurements: list) -> pd.DataFrame:
    """
    Create comprehensive NTA statistics DataFrame.
    
    Args:
        measurements: List of (file_path, DataFrame) tuples
    
    Returns:
        Standardized NTA statistics DataFrame
    """
    logger.info("🔧 Creating NTA statistics...")
    
    all_stats = []
    
    for file_path, df in measurements:
        try:
            # Extract metadata
            metadata = extract_sample_metadata(file_path, df)
            
            # Calculate size statistics
            size_stats = calculate_size_statistics(df)
            
            # Calculate concentration statistics
            conc_stats = calculate_concentration_statistics(df)
            
            # Calculate size bin fractions
            bin_stats = calculate_size_bin_fractions(df)
            
            # Assess quality
            quality_stats = assess_measurement_quality(df, metadata)
            
            # Combine all statistics
            sample_stats = {
                **metadata,
                **size_stats,
                **conc_stats,
                **bin_stats,
                **quality_stats,
                'instrument_type': 'nta',
                'has_measurement_data': True,
            }
            
            all_stats.append(sample_stats)
            
        except Exception as e:
            logger.warning(f"   ⚠️  Failed to process {file_path.name}: {e}")
    
    # Create DataFrame
    stats_df = pd.DataFrame(all_stats)
    
    # Sort by biological_sample_id
    stats_df = stats_df.sort_values('biological_sample_id').reset_index(drop=True)
    
    logger.info(f"   ✅ Created statistics for {len(stats_df)} samples")
    
    return stats_df


def generate_summary_statistics(stats: pd.DataFrame) -> dict:
    """
    Generate summary statistics for reporting.
    
    Args:
        stats: NTA statistics DataFrame
    
    Returns:
        Dictionary with summary metrics
    """
    summary = {
        'total_samples': len(stats),
        'unique_biological_samples': stats['biological_sample_id'].nunique(),
        'measurement_types': stats['measurement_type'].value_counts().to_dict(),
        'avg_d50_nm': float(stats['d50_nm'].mean()) if 'd50_nm' in stats.columns else None,
        'avg_concentration_ml': float(stats['total_concentration_particles_ml'].mean()) if 'total_concentration_particles_ml' in stats.columns else None,
        'qc_passed': int(stats['qc_passed'].sum()) if 'qc_passed' in stats.columns else 0,
        'qc_failed': int((~stats['qc_passed']).sum()) if 'qc_passed' in stats.columns else 0,
        'passages': sorted(stats['passage'].dropna().unique().tolist()),
        'fractions': sorted(stats['fraction'].dropna().unique().tolist()),
    }
    
    return summary


def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("🚀 NTA STATISTICS AGGREGATION - Task 1.3 Subtask 1.3")
    logger.info("=" * 80)
    
    # Define paths
    project_root = Path(__file__).parent.parent
    measurements_dir = project_root / 'data' / 'parquet' / 'nta' / 'measurements'
    output_dir = project_root / 'data' / 'parquet' / 'nta' / 'statistics'
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Load measurements
    measurements = load_nta_measurements(measurements_dir)
    
    # Step 2: Create statistics
    stats = create_nta_statistics(measurements)
    
    # Step 3: Generate summary
    logger.info("\n📊 Generating summary statistics...")
    summary = generate_summary_statistics(stats)
    
    logger.info("\n📋 NTA Dataset Summary:")
    logger.info(f"   - Total measurements: {summary['total_samples']}")
    logger.info(f"   - Unique biological samples: {summary['unique_biological_samples']}")
    logger.info(f"   - Measurement types: {summary['measurement_types']}")
    logger.info(f"   - Average D50: {summary['avg_d50_nm']:.1f} nm" if summary['avg_d50_nm'] else "   - Average D50: N/A")
    logger.info(f"   - QC passed: {summary['qc_passed']}/{summary['total_samples']}")
    logger.info(f"   - Passages: {', '.join(summary['passages'])}")
    logger.info(f"   - Fractions analyzed: {len(summary['fractions'])}")
    
    # Step 4: Save statistics
    output_file = output_dir / 'nta_statistics.parquet'
    logger.info(f"\n💾 Saving NTA statistics to: {output_file}")
    
    stats.to_parquet(output_file, index=False, compression='snappy')
    
    file_size_mb = output_file.stat().st_size / (1024 * 1024)
    logger.info(f"   ✅ Saved: {output_file.name} ({file_size_mb:.2f} MB)")
    logger.info(f"   - Dimensions: {stats.shape[0]} samples × {stats.shape[1]} features")
    
    # Save summary as JSON
    import json
    summary_file = output_dir / 'nta_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    logger.info(f"   ✅ Saved summary: {summary_file.name}")
    
    # Save CSV version
    csv_file = output_dir / 'nta_statistics.csv'
    stats.to_csv(csv_file, index=False)
    logger.info(f"   ✅ Saved CSV: {csv_file.name}")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ NTA STATISTICS AGGREGATION COMPLETE")
    logger.info("=" * 80)
    
    return output_file


if __name__ == "__main__":
    main()
