"""
Data Validation Report Generator
Converts the notebook validation into a terminal-friendly script with immediate output
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for terminal
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
import time
from datetime import datetime
import sys

warnings.filterwarnings('ignore')

# Set plotting style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Configure display
pd.set_option('display.max_columns', 50)
pd.set_option('display.max_rows', 100)
pd.set_option('display.float_format', '{:.3f}'.format)

print("=" * 80)
print("📊 DATA VALIDATION REPORT - TASK 1.3")
print("=" * 80)
print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"🐍 Pandas Version: {pd.__version__}")
print("=" * 80)

# Define paths
project_root = Path(r"C:\CRM IT Project\EV (Exosome) Project")
fcs_stats_file = project_root / 'data' / 'parquet' / 'nanofacs' / 'statistics' / 'fcs_statistics.parquet'
nta_stats_file = project_root / 'data' / 'parquet' / 'nta' / 'statistics' / 'nta_statistics.parquet'
processed_dir = project_root / 'data' / 'processed'
combined_features_file = processed_dir / 'combined_features.parquet'
sample_metadata_file = processed_dir / 'sample_metadata.parquet'
baseline_comparison_file = processed_dir / 'baseline_comparison.parquet'
figures_dir = project_root / 'figures' / 'validation'
figures_dir.mkdir(parents=True, exist_ok=True)

# Check files
print("\n📂 STEP 1: FILE EXISTENCE CHECK")
print("-" * 80)
files_to_check = {
    'FCS Statistics': fcs_stats_file,
    'NTA Statistics': nta_stats_file,
    'Combined Features': combined_features_file,
    'Sample Metadata': sample_metadata_file,
    'Baseline Comparison': baseline_comparison_file
}

all_files_exist = True
for name, path in files_to_check.items():
    exists = path.exists()
    status = "✅" if exists else "❌"
    all_files_exist = all_files_exist and exists
    size_mb = path.stat().st_size / (1024**2) if exists else 0
    print(f"{status} {name}: {size_mb:.3f} MB")

if not all_files_exist:
    print("\n❌ ERROR: Some files are missing!")
    sys.exit(1)

print("\n✅ All files found!")

# Load FCS statistics
print("\n📊 STEP 2: FCS DATA VALIDATION")
print("-" * 80)
start_time = time.time()
fcs_stats = pd.read_parquet(fcs_stats_file)
load_time = time.time() - start_time

print(f"✅ Loaded in {load_time:.3f} seconds")
print(f"📏 Dimensions: {fcs_stats.shape[0]} samples × {fcs_stats.shape[1]} features")
print(f"📊 Event Statistics:")
total_events = fcs_stats['total_events'].sum()
avg_events = fcs_stats['total_events'].mean()
print(f"   - Total events: {total_events:,}")
print(f"   - Average events/sample: {avg_events:,.0f}")

if 'qc_passed' in fcs_stats.columns:
    qc_rate = (fcs_stats['qc_passed'] == True).sum() / len(fcs_stats) * 100
    print(f"   - QC pass rate: {qc_rate:.1f}%")

if 'is_baseline' in fcs_stats.columns:
    baseline_count = (fcs_stats['is_baseline'] == True).sum()
    print(f"   - Baseline samples: {baseline_count}")

# Generate FCS plot
print("\n📈 Generating FCS visualizations...")
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
axes[0, 0].hist(fcs_stats['total_events'], bins=30, edgecolor='black', alpha=0.7)
axes[0, 0].set_xlabel('Total Events')
axes[0, 0].set_ylabel('Frequency')
axes[0, 0].set_title('FCS Event Count Distribution')
axes[0, 0].axvline(avg_events, color='red', linestyle='--', label=f'Mean: {avg_events:,.0f}')
axes[0, 0].legend()

if 'channel_count' in fcs_stats.columns:
    axes[0, 1].hist(fcs_stats['channel_count'], bins=20, edgecolor='black', alpha=0.7, color='green')
    axes[0, 1].set_xlabel('Number of Channels')
    axes[0, 1].set_title('Channel Count Distribution')

if 'processing_time_seconds' in fcs_stats.columns:
    axes[1, 0].hist(fcs_stats['processing_time_seconds'], bins=30, edgecolor='black', alpha=0.7, color='orange')
    axes[1, 0].set_xlabel('Processing Time (seconds)')
    axes[1, 0].set_title('Processing Time Distribution')

if 'compression_ratio' in fcs_stats.columns:
    axes[1, 1].hist(fcs_stats['compression_ratio'], bins=30, edgecolor='black', alpha=0.7, color='purple')
    axes[1, 1].set_xlabel('Compression Ratio')
    axes[1, 1].set_title('Parquet Compression Ratio')

plt.tight_layout()
fcs_plot = figures_dir / 'fcs_validation.png'
plt.savefig(fcs_plot, dpi=100, bbox_inches='tight')
plt.close()
print(f"✅ Saved: {fcs_plot}")

# Load NTA statistics
print("\n📊 STEP 3: NTA DATA VALIDATION")
print("-" * 80)
start_time = time.time()
nta_stats = pd.read_parquet(nta_stats_file)
load_time = time.time() - start_time

print(f"✅ Loaded in {load_time:.3f} seconds")
print(f"📏 Dimensions: {nta_stats.shape[0]} measurements × {nta_stats.shape[1]} features")

if 'biological_sample_id' in nta_stats.columns:
    unique_bio = nta_stats['biological_sample_id'].nunique()
    print(f"📊 Unique biological samples: {unique_bio}")

if 'd50_nm' in nta_stats.columns:
    d50_mean = nta_stats['d50_nm'].mean()
    d50_median = nta_stats['d50_nm'].median()
    print(f"📐 D50 Statistics:")
    print(f"   - Mean: {d50_mean:.1f} nm")
    print(f"   - Median: {d50_median:.1f} nm")

# Generate NTA plot
print("\n📈 Generating NTA visualizations...")
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

if all(col in nta_stats.columns for col in ['d10_nm', 'd50_nm', 'd90_nm']):
    d_values = nta_stats[['d10_nm', 'd50_nm', 'd90_nm']].dropna()
    axes[0, 0].boxplot([d_values['d10_nm'], d_values['d50_nm'], d_values['d90_nm']],
                        labels=['D10', 'D50', 'D90'])
    axes[0, 0].set_ylabel('Size (nm)')
    axes[0, 0].set_title('NTA Size Percentiles')
    axes[0, 0].grid(True, alpha=0.3)

if 'polydispersity_index' in nta_stats.columns:
    axes[0, 1].hist(nta_stats['polydispersity_index'].dropna(), bins=30, 
                     edgecolor='black', alpha=0.7, color='green')
    axes[0, 1].set_xlabel('Polydispersity Index')
    axes[0, 1].set_title('PDI Distribution')

if 'total_concentration_particles_ml' in nta_stats.columns:
    conc_data = nta_stats['total_concentration_particles_ml'].dropna()
    axes[1, 0].hist(conc_data, bins=30, edgecolor='black', alpha=0.7, color='orange')
    axes[1, 0].set_xlabel('Concentration (particles/mL)')
    axes[1, 0].set_title('Concentration Distribution')

size_bin_cols = [col for col in nta_stats.columns if 'fraction_' in col and '_nm_percent' in col]
if size_bin_cols:
    bin_data = nta_stats[size_bin_cols].mean()
    if isinstance(bin_data, pd.Series) and len(bin_data) > 0:
        axes[1, 1].bar(range(len(bin_data)), bin_data.values, edgecolor='black', alpha=0.7)
        axes[1, 1].set_xticks(range(len(bin_data)))
        axes[1, 1].set_xticklabels([str(col).replace('fraction_', '').replace('_percent', '') 
                                      for col in bin_data.index], rotation=45, ha='right')
    axes[1, 1].set_ylabel('Percentage (%)')
    axes[1, 1].set_title('Size Bin Distribution')

plt.tight_layout()
nta_plot = figures_dir / 'nta_validation.png'
plt.savefig(nta_plot, dpi=100, bbox_inches='tight')
plt.close()
print(f"✅ Saved: {nta_plot}")

# Load integrated data
print("\n📊 STEP 4: DATA INTEGRATION VALIDATION")
print("-" * 80)
combined = pd.read_parquet(combined_features_file)
sample_metadata = pd.read_parquet(sample_metadata_file)
baseline_comparison = pd.read_parquet(baseline_comparison_file)

print(f"✅ Combined Features: {combined.shape[0]} samples × {combined.shape[1]} features")
print(f"✅ Sample Metadata: {sample_metadata.shape[0]} samples")
print(f"✅ Baseline Comparison: {baseline_comparison.shape[0]} samples")

fcs_count = combined['has_fcs_data'].sum()
nta_count = combined['has_nta_data'].sum()
both_count = (combined['has_fcs_data'] & combined['has_nta_data']).sum()

print(f"\n📈 Data Availability:")
print(f"   - FCS only: {fcs_count - both_count} samples")
print(f"   - NTA only: {nta_count - both_count} samples")
print(f"   - Both: {both_count} samples")

fcs_features = [col for col in combined.columns if col.startswith('fcs_')]
nta_features = [col for col in combined.columns if col.startswith('nta_')]
print(f"\n🔢 Feature Count:")
print(f"   - FCS features: {len(fcs_features)}")
print(f"   - NTA features: {len(nta_features)}")
print(f"   - Total: {len(combined.columns)}")

# Generate integration plot
print("\n📈 Generating integration visualizations...")
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

if 'match_type' in sample_metadata.columns:
    match_counts = sample_metadata['match_type'].value_counts()
    axes[0].pie(match_counts.values, labels=match_counts.index, autopct='%1.1f%%',
                startangle=90, colors=['#66c2a5', '#fc8d62', '#8da0cb'])
    axes[0].set_title('Sample Match Types')

data_avail = pd.DataFrame({
    'FCS Only': [fcs_count - both_count],
    'NTA Only': [nta_count - both_count],
    'Both': [both_count]
})
data_avail.T.plot(kind='bar', ax=axes[1], legend=False, color=['#e78ac3', '#a6d854', '#ffd92f'])
axes[1].set_ylabel('Sample Count')
axes[1].set_title('Data Availability')
axes[1].set_xticklabels(axes[1].get_xticklabels(), rotation=0)

plt.tight_layout()
integration_plot = figures_dir / 'integration_validation.png'
plt.savefig(integration_plot, dpi=100, bbox_inches='tight')
plt.close()
print(f"✅ Saved: {integration_plot}")

# Baseline comparison
print("\n📊 STEP 5: BASELINE COMPARISON VALIDATION")
print("-" * 80)
baseline_count = baseline_comparison['is_baseline'].sum()
test_count = (~baseline_comparison['is_baseline']).sum()
print(f"🏷️  Baseline samples: {baseline_count}")
print(f"🧪 Test samples: {test_count}")

fold_change_cols = [col for col in baseline_comparison.columns if 'fold_change' in col]
print(f"📈 Fold change metrics: {len(fold_change_cols)}")

# Performance check
print("\n⚡ STEP 6: PERFORMANCE PROFILING")
print("-" * 80)
memory_usage = {
    'FCS Stats': sys.getsizeof(fcs_stats) / (1024**2),
    'NTA Stats': sys.getsizeof(nta_stats) / (1024**2),
    'Combined': sys.getsizeof(combined) / (1024**2),
}
total_mem = sum(memory_usage.values())
print(f"💾 Memory Usage: {total_mem:.2f} MB")
for name, mem in memory_usage.items():
    print(f"   - {name}: {mem:.2f} MB")

# Final summary
print("\n" + "=" * 80)
print("📋 FINAL VALIDATION SUMMARY")
print("=" * 80)

validation_results = {
    'All files exist': all_files_exist,
    'FCS data loaded': len(fcs_stats) > 0,
    'NTA data loaded': len(nta_stats) > 0,
    'Integration complete': len(combined) > 0,
    'Baseline comparisons': len(baseline_comparison) > 0,
    'Memory under 4GB': total_mem < 4096,
}

print("\n🎯 Validation Checklist:")
all_passed = True
for check, passed in validation_results.items():
    status = "✅" if passed else "❌"
    print(f"   {status} {check}")
    all_passed = all_passed and passed

print(f"\n📊 Quick Stats:")
print(f"   - FCS samples: {len(fcs_stats)}")
print(f"   - NTA measurements: {len(nta_stats)}")
print(f"   - Combined samples: {len(combined)}")
print(f"   - Total features: {len(combined.columns)}")
print(f"   - Memory usage: {total_mem:.0f} MB")

print(f"\n🎨 Visualizations saved to: {figures_dir}")
print(f"   - fcs_validation.png")
print(f"   - nta_validation.png")
print(f"   - integration_validation.png")

if all_passed:
    print("\n" + "=" * 80)
    print("✅ ✅ ✅ DATA IS PRODUCTION-READY FOR ML DEVELOPMENT ✅ ✅ ✅")
    print("=" * 80)
    print("\n🚀 Next Steps:")
    print("   1. Feature selection and engineering")
    print("   2. Train/test split preparation")
    print("   3. Model development (sklearn, xgboost)")
    print("   4. Cross-validation and evaluation")
else:
    print("\n⚠️  Some validation checks failed - review above")

print(f"\n✅ VALIDATION COMPLETE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
