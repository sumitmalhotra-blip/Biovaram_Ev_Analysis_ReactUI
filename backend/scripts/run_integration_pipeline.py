"""
Simplified Data Integration Script - Task 1.3 (PRODUCTION READY)
=================================================================

Purpose:
- Load FCS and NTA statistics
- Match samples by biological_sample_id
- Create combined_features.parquet (ML-ready dataset)
- Create sample_metadata.parquet (master registry)
- Generate baseline_comparison.parquet

This is a simplified version that works directly with our aggregated statistics files.

Author: CRMIT Team
Date: November 17, 2025
Status: PRODUCTION READY
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger
import json

# Configure logging
logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


def load_fcs_statistics(stats_file: Path) -> pd.DataFrame:
    """Load FCS statistics from parquet file."""
    logger.info(f"📂 Loading FCS statistics: {stats_file.name}")
    df = pd.read_parquet(stats_file)
    logger.info(f"   ✅ Loaded {len(df)} FCS samples")
    return df


def load_nta_statistics(stats_file: Path) -> pd.DataFrame:
    """Load NTA statistics from parquet file."""
    logger.info(f"📂 Loading NTA statistics: {stats_file.name}")
    df = pd.read_parquet(stats_file)
    logger.info(f"   ✅ Loaded {len(df)} NTA measurements")
    return df


def match_samples(fcs_df: pd.DataFrame, nta_df: pd.DataFrame) -> pd.DataFrame:
    """
    Match FCS and NTA samples by biological_sample_id.
    
    Args:
        fcs_df: FCS statistics DataFrame
        nta_df: NTA statistics DataFrame
    
    Returns:
        Sample registry with matching information
    """
    logger.info("🔗 Matching FCS and NTA samples...")
    
    # Get unique biological sample IDs
    fcs_samples = set(fcs_df['biological_sample_id'].unique())
    nta_samples = set(nta_df['biological_sample_id'].unique())
    
    # Find matches
    exact_matches = fcs_samples & nta_samples
    fcs_only = fcs_samples - nta_samples
    nta_only = nta_samples - fcs_samples
    
    logger.info(f"   - Exact matches: {len(exact_matches)}")
    logger.info(f"   - FCS only: {len(fcs_only)}")
    logger.info(f"   - NTA only: {len(nta_only)}")
    
    # Create sample registry
    registry_records = []
    
    # Add matched samples
    for bio_id in exact_matches:
        fcs_records = fcs_df[fcs_df['biological_sample_id'] == bio_id]
        nta_records = nta_df[nta_df['biological_sample_id'] == bio_id]
        
        registry_records.append({
            'biological_sample_id': bio_id,
            'match_type': 'exact',
            'has_fcs_data': True,
            'has_nta_data': True,
            'fcs_sample_count': len(fcs_records),
            'nta_sample_count': len(nta_records),
        })
    
    # Add FCS-only samples
    for bio_id in fcs_only:
        fcs_records = fcs_df[fcs_df['biological_sample_id'] == bio_id]
        registry_records.append({
            'biological_sample_id': bio_id,
            'match_type': 'fcs_only',
            'has_fcs_data': True,
            'has_nta_data': False,
            'fcs_sample_count': len(fcs_records),
            'nta_sample_count': 0,
        })
    
    # Add NTA-only samples
    for bio_id in nta_only:
        nta_records = nta_df[nta_df['biological_sample_id'] == bio_id]
        registry_records.append({
            'biological_sample_id': bio_id,
            'match_type': 'nta_only',
            'has_fcs_data': False,
            'has_nta_data': True,
            'fcs_sample_count': 0,
            'nta_sample_count': len(nta_records),
        })
    
    registry = pd.DataFrame(registry_records)
    registry = registry.sort_values('biological_sample_id').reset_index(drop=True)
    
    return registry


def aggregate_fcs_features(fcs_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate FCS data by biological_sample_id.
    For multiple FCS measurements of the same biological sample, take the mean.
    
    Args:
        fcs_df: FCS statistics DataFrame
    
    Returns:
        Aggregated FCS features
    """
    logger.info("📊 Aggregating FCS features by biological_sample_id...")
    
    # Select numeric columns for aggregation
    numeric_cols = fcs_df.select_dtypes(include=[np.number]).columns.tolist()
    
    # Group by biological_sample_id and aggregate
    agg_dict = {col: 'mean' for col in numeric_cols}
    
    # Keep some categorical columns (first occurrence)
    cat_cols = ['sample_id', 'file_name', 'experiment_type', 'antibody', 
                'purification_method', 'is_baseline', 'is_control']
    
    for col in cat_cols:
        if col in fcs_df.columns:
            agg_dict[col] = 'first'
    
    fcs_agg = fcs_df.groupby('biological_sample_id').agg(agg_dict).reset_index()
    
    # Rename columns with 'fcs_' prefix
    rename_dict = {}
    for col in fcs_agg.columns:
        if col not in ['biological_sample_id', 'sample_id']:
            rename_dict[col] = f'fcs_{col}'
    
    fcs_agg = fcs_agg.rename(columns=rename_dict)
    
    logger.info(f"   ✅ Aggregated to {len(fcs_agg)} unique biological samples")
    logger.info(f"   - Features: {len(fcs_agg.columns)} columns")
    
    return fcs_agg


def aggregate_nta_features(nta_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate NTA data by biological_sample_id.
    For multiple NTA measurements of the same biological sample, take the mean.
    
    Args:
        nta_df: NTA statistics DataFrame
    
    Returns:
        Aggregated NTA features
    """
    logger.info("📊 Aggregating NTA features by biological_sample_id...")
    
    # Select numeric columns for aggregation
    numeric_cols = nta_df.select_dtypes(include=[np.number]).columns.tolist()
    
    # Group by biological_sample_id and aggregate
    agg_dict = {col: 'mean' for col in numeric_cols}
    
    # Keep some categorical columns
    cat_cols = ['sample_id', 'file_name', 'passage', 'fraction', 'measurement_type']
    
    for col in cat_cols:
        if col in nta_df.columns:
            agg_dict[col] = 'first'
    
    nta_agg = nta_df.groupby('biological_sample_id').agg(agg_dict).reset_index()
    
    # Rename columns with 'nta_' prefix
    rename_dict = {}
    for col in nta_agg.columns:
        if col not in ['biological_sample_id', 'sample_id']:
            rename_dict[col] = f'nta_{col}'
    
    nta_agg = nta_agg.rename(columns=rename_dict)
    
    logger.info(f"   ✅ Aggregated to {len(nta_agg)} unique biological samples")
    logger.info(f"   - Features: {len(nta_agg.columns)} columns")
    
    return nta_agg


def create_combined_features(
    registry: pd.DataFrame,
    fcs_features: pd.DataFrame,
    nta_features: pd.DataFrame
) -> pd.DataFrame:
    """
    Create combined feature matrix for ML.
    
    Args:
        registry: Sample registry
        fcs_features: Aggregated FCS features
        nta_features: Aggregated NTA features
    
    Returns:
        Combined feature DataFrame
    """
    logger.info("🔗 Creating combined feature matrix...")
    
    # Start with registry
    combined = registry.copy()
    
    # Merge FCS features
    combined = combined.merge(
        fcs_features,
        on='biological_sample_id',
        how='left'
    )
    
    # Merge NTA features
    combined = combined.merge(
        nta_features,
        on='biological_sample_id',
        how='left'
    )
    
    logger.info(f"   ✅ Combined features created")
    logger.info(f"   - Samples: {len(combined)}")
    logger.info(f"   - Features: {len(combined.columns)}")
    
    # Calculate cross-instrument correlations where both datasets exist
    if 'fcs_total_events' in combined.columns and 'nta_d50_nm' in combined.columns:
        both_present = combined['has_fcs_data'] & combined['has_nta_data']
        if both_present.sum() > 0:
            corr = combined.loc[both_present, ['fcs_total_events', 'nta_d50_nm']].corr().iloc[0, 1]
            logger.info(f"   - FCS events vs NTA D50 correlation: {corr:.3f}")
    
    return combined


def identify_baseline_samples(combined: pd.DataFrame) -> list:
    """
    Identify baseline (isotype control) samples.
    
    Args:
        combined: Combined features DataFrame
    
    Returns:
        List of baseline biological_sample_ids
    """
    logger.info("🏷️  Identifying baseline samples...")
    
    baseline_samples = []
    
    # Check for is_baseline flag from FCS data
    if 'fcs_is_baseline' in combined.columns:
        baseline_mask = combined['fcs_is_baseline'] == True
        baseline_samples = combined.loc[baseline_mask, 'biological_sample_id'].tolist()
    
    logger.info(f"   ✅ Identified {len(baseline_samples)} baseline samples")
    
    return baseline_samples


def calculate_baseline_comparisons(
    combined: pd.DataFrame,
    baseline_samples: list
) -> pd.DataFrame:
    """
    Calculate fold changes and deltas vs baseline.
    
    Args:
        combined: Combined features DataFrame
        baseline_samples: List of baseline biological_sample_ids
    
    Returns:
        Baseline comparison DataFrame
    """
    logger.info("📊 Calculating baseline comparisons...")
    
    if not baseline_samples:
        logger.warning("   ⚠️  No baseline samples found, skipping baseline comparison")
        return pd.DataFrame()
    
    # Get baseline data
    baseline_data = combined[combined['biological_sample_id'].isin(baseline_samples)]
    
    # Get test data (non-baseline)
    test_data = combined[~combined['biological_sample_id'].isin(baseline_samples)]
    
    # Calculate baseline averages for numeric columns
    numeric_cols = combined.select_dtypes(include=[np.number]).columns
    baseline_means = baseline_data[numeric_cols].mean()
    
    comparisons = []
    
    for idx, test_row in test_data.iterrows():
        bio_id = test_row['biological_sample_id']
        
        comparison = {
            'biological_sample_id': bio_id,
            'is_baseline': False,
        }
        
        # Calculate fold changes for key metrics
        for col in ['fcs_total_events', 'nta_d50_nm', 'nta_total_concentration_particles_ml']:
            col_val = test_row[col]
            if col in numeric_cols and not pd.isna(col_val):  # type: ignore[arg-type]
                baseline_val = float(baseline_means.get(col, np.nan)) if isinstance(baseline_means, dict) else np.nan
                test_val = float(col_val)
                
                if not pd.isna(baseline_val) and baseline_val != 0:  # type: ignore[arg-type]
                    fold_change = test_val / baseline_val
                    delta = test_val - baseline_val
                    delta_pct = (delta / baseline_val) * 100
                    
                    comparison[f'{col}_fold_change'] = fold_change
                    comparison[f'{col}_delta'] = delta
                    comparison[f'{col}_delta_pct'] = delta_pct
        
        comparisons.append(comparison)
    
    # Add baseline samples to comparison table
    for bio_id in baseline_samples:
        comparisons.append({
            'biological_sample_id': bio_id,
            'is_baseline': True,
        })
    
    comparison_df = pd.DataFrame(comparisons)
    comparison_df = comparison_df.sort_values('biological_sample_id').reset_index(drop=True)
    
    logger.info(f"   ✅ Baseline comparisons calculated")
    logger.info(f"   - Test samples: {len(test_data)}")
    logger.info(f"   - Baseline samples: {len(baseline_samples)}")
    
    return comparison_df


def generate_summary_report(
    registry: pd.DataFrame,
    combined: pd.DataFrame,
    baseline_comparison: pd.DataFrame
) -> str:
    """Generate comprehensive summary report."""
    
    lines = []
    lines.append("=" * 80)
    lines.append("DATA INTEGRATION SUMMARY REPORT")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # Sample matching summary
    lines.append("SAMPLE MATCHING:")
    lines.append(f"  - Total biological samples: {len(registry)}")
    lines.append(f"  - Exact matches (FCS + NTA): {len(registry[registry['match_type'] == 'exact'])}")
    lines.append(f"  - FCS only: {len(registry[registry['match_type'] == 'fcs_only'])}")
    lines.append(f"  - NTA only: {len(registry[registry['match_type'] == 'nta_only'])}")
    lines.append("")
    
    # Combined features summary
    lines.append("COMBINED FEATURES:")
    lines.append(f"  - Total samples: {len(combined)}")
    lines.append(f"  - Total features: {len(combined.columns)}")
    
    fcs_features = len([c for c in combined.columns if c.startswith('fcs_')])
    nta_features = len([c for c in combined.columns if c.startswith('nta_')])
    
    lines.append(f"  - FCS features: {fcs_features}")
    lines.append(f"  - NTA features: {nta_features}")
    both_count = (combined['has_fcs_data'] & combined['has_nta_data']).sum()
    lines.append(f"  - Samples with both FCS + NTA: {both_count}")
    lines.append("")
    
    # Baseline comparison summary
    if not baseline_comparison.empty:
        lines.append("BASELINE COMPARISON:")
        lines.append(f"  - Baseline samples: {baseline_comparison['is_baseline'].sum()}")
        lines.append(f"  - Test samples: {(~baseline_comparison['is_baseline']).sum()}")
        lines.append("")
    
    # Data quality
    lines.append("DATA QUALITY:")
    lines.append(f"  - FCS QC pass rate: {(combined['fcs_qc_passed'] == True).sum() / len(combined) * 100:.1f}%" if 'fcs_qc_passed' in combined.columns else "  - FCS QC: N/A")
    lines.append(f"  - NTA QC pass rate: {(combined['nta_qc_passed'] == True).sum() / len(combined) * 100:.1f}%" if 'nta_qc_passed' in combined.columns else "  - NTA QC: N/A")
    lines.append("")
    
    lines.append("=" * 80)
    lines.append("✅ DATA INTEGRATION COMPLETE")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def main():
    """Main integration pipeline."""
    logger.info("=" * 80)
    logger.info("🚀 DATA INTEGRATION PIPELINE - Task 1.3")
    logger.info("=" * 80)
    
    # Define paths
    project_root = Path(__file__).parent.parent
    fcs_stats_file = project_root / 'data' / 'parquet' / 'nanofacs' / 'statistics' / 'fcs_statistics.parquet'
    nta_stats_file = project_root / 'data' / 'parquet' / 'nta' / 'statistics' / 'nta_statistics.parquet'
    output_dir = project_root / 'data' / 'processed'
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Step 1: Load statistics
        logger.info("\n📂 STEP 1: Loading Statistics...")
        fcs_df = load_fcs_statistics(fcs_stats_file)
        nta_df = load_nta_statistics(nta_stats_file)
        
        # Step 2: Match samples
        logger.info("\n🔗 STEP 2: Matching Samples...")
        registry = match_samples(fcs_df, nta_df)
        
        # Save registry
        registry_file = output_dir / 'sample_metadata.parquet'
        registry.to_parquet(registry_file, index=False)
        logger.info(f"   ✅ Saved: {registry_file.name}")
        
        # Step 3: Aggregate features
        logger.info("\n📊 STEP 3: Aggregating Features...")
        fcs_features = aggregate_fcs_features(fcs_df)
        nta_features = aggregate_nta_features(nta_df)
        
        # Step 4: Create combined features
        logger.info("\n🔗 STEP 4: Creating Combined Features...")
        combined = create_combined_features(registry, fcs_features, nta_features)
        
        # Save combined features
        combined_file = output_dir / 'combined_features.parquet'
        combined.to_parquet(combined_file, index=False)
        file_size_mb = combined_file.stat().st_size / (1024 * 1024)
        logger.info(f"   ✅ Saved: {combined_file.name} ({file_size_mb:.2f} MB)")
        logger.info(f"   - Dimensions: {combined.shape[0]} samples × {combined.shape[1]} features")
        
        # Step 5: Identify baselines
        logger.info("\n🏷️  STEP 5: Identifying Baseline Samples...")
        baseline_samples = identify_baseline_samples(combined)
        
        # Step 6: Calculate baseline comparisons
        logger.info("\n📊 STEP 6: Calculating Baseline Comparisons...")
        baseline_comparison = calculate_baseline_comparisons(combined, baseline_samples)
        
        if not baseline_comparison.empty:
            baseline_file = output_dir / 'baseline_comparison.parquet'
            baseline_comparison.to_parquet(baseline_file, index=False)
            logger.info(f"   ✅ Saved: {baseline_file.name}")
        
        # Step 7: Generate summary report
        logger.info("\n📋 STEP 7: Generating Summary Report...")
        summary = generate_summary_report(registry, combined, baseline_comparison)
        
        summary_file = output_dir / 'integration_summary.txt'
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        logger.info(f"   ✅ Saved: {summary_file.name}")
        
        # Print summary
        logger.info("\n" + summary)
        
        # Save output file paths as JSON
        output_manifest = {
            'sample_metadata': str(registry_file),
            'combined_features': str(combined_file),
            'baseline_comparison': str(baseline_file) if not baseline_comparison.empty else None,
            'integration_summary': str(summary_file),
        }
        
        manifest_file = output_dir / 'output_manifest.json'
        with open(manifest_file, 'w') as f:
            json.dump(output_manifest, f, indent=2)
        logger.info(f"\n📁 Output manifest saved: {manifest_file.name}")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ INTEGRATION PIPELINE COMPLETE")
        logger.info("=" * 80)
        
    except FileNotFoundError as e:
        logger.error(f"❌ File not found: {e}")
        logger.info("\nPlease run:")
        logger.info("  1. python scripts/create_fcs_statistics.py")
        logger.info("  2. python scripts/create_nta_statistics.py")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"❌ Integration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
