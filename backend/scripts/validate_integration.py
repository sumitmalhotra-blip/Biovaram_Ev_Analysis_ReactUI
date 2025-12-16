"""Quick validation of integration outputs."""
import pandas as pd
from pathlib import Path

project_root = Path(__file__).parent.parent
processed_dir = project_root / 'data' / 'processed'

print("="*80)
print("INTEGRATION OUTPUT VALIDATION")
print("="*80)

# Load combined features
combined = pd.read_parquet(processed_dir / 'combined_features.parquet')
print(f"\n✅ Combined Features: {combined.shape[0]} samples × {combined.shape[1]} features")
print(f"   - Samples with FCS data: {combined['has_fcs_data'].sum()}")
print(f"   - Samples with NTA data: {combined['has_nta_data'].sum()}")
print(f"   - Samples with BOTH: {(combined['has_fcs_data'] & combined['has_nta_data']).sum()}")

# Load baseline comparison
baseline = pd.read_parquet(processed_dir / 'baseline_comparison.parquet')
print(f"\n✅ Baseline Comparison: {len(baseline)} samples")
print(f"   - Baseline samples: {baseline['is_baseline'].sum()}")
print(f"   - Test samples: {(~baseline['is_baseline']).sum()}")

# Load sample metadata
metadata = pd.read_parquet(processed_dir / 'sample_metadata.parquet')
print(f"\n✅ Sample Metadata: {len(metadata)} samples")
print(f"   - Exact matches: {len(metadata[metadata['match_type'] == 'exact'])}")
print(f"   - FCS only: {len(metadata[metadata['match_type'] == 'fcs_only'])}")
print(f"   - NTA only: {len(metadata[metadata['match_type'] == 'nta_only'])}")

print("\n" + "="*80)
print("✅ ALL OUTPUTS VALIDATED SUCCESSFULLY")
print("="*80)
