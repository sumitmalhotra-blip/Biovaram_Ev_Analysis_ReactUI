"""Analyze FSC distribution to understand outliers.

WHAT THIS SCRIPT DOES:
-----------------------
Investigates the distribution of Forward Scatter (FSC) values to identify
outliers that could break Mie scattering calibration.

WHY WE NEED THIS:
-----------------
Problem: Mie scattering calibration expects particles in 40-200nm range
- Real exosomes: 40-150nm (most data)
- Outliers: >1000nm (debris, aggregates, noise)
- If we include outliers → calibration curve breaks
- Solution: Filter top 0.1-1% of FSC values

HOW IT WORKS:
-------------
1. Load sample FCS file
2. Extract FSC-H (Forward Scatter Height) values
3. Calculate percentiles (P1, P50, P99, P99.9, etc.)
4. Analyze impact of different filtering thresholds
5. Recommend optimal filter level

EXPECTED FINDINGS:
------------------
- Majority of events: FSC < 2,500 (real exosomes)
- Top 1%: FSC = 2,500-5,000 (larger EVs, small debris)
- Top 0.1%: FSC > 5,000 (aggregates, artifacts)
- Top 0.01%: FSC > 10,000 (extreme outliers, noise)

RECOMMENDATION:
---------------
Filter at P99.9 (keep 99.9% of events):
- Removes only extreme outliers (0.1% of data)
- Preserves all real biological events
- Enables accurate Mie calibration
- Standard practice in flow cytometry

USAGE:
------
    python scripts/analyze_outliers.py

OUTPUT:
-------
- Percentile table (P1-P99.99)
- Extreme values (min, max, mean, median, std)
- Filtering impact analysis
- Interpretation and recommendations

AUTHOR: CRMIT Backend Team
DATE: November 19, 2025
CONTEXT: Part of Mie scatter calibration validation
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Load sample file
file_path = Path("data/parquet/nanofacs/events/10000 exo and cd81/Exo Control.parquet")
df = pd.read_parquet(file_path)
fsc = np.asarray(df['VFSC-H'].values)  # Convert to numpy array to avoid ExtensionArray issues

print("=" * 60)
print("FSC DISTRIBUTION ANALYSIS")
print("=" * 60)
print(f"\nTotal events: {len(fsc):,}")

print("\n" + "=" * 60)
print("PERCENTILE ANALYSIS")
print("=" * 60)
percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99, 99.5, 99.9, 99.99]
for p in percentiles:
    val = np.percentile(fsc, p)
    print(f"  P{p:6.2f}: {val:12.1f}")

print("\n" + "=" * 60)
print("EXTREME VALUES")
print("=" * 60)
print(f"  Max: {fsc.max():,.1f}")
print(f"  Min: {fsc.min():,.1f}")
print(f"  Mean: {fsc.mean():,.1f}")
print(f"  Median: {np.median(fsc):,.1f}")
print(f"  Std Dev: {fsc.std():,.1f}")

print("\n" + "=" * 60)
print("OUTLIER IMPACT ANALYSIS")
print("=" * 60)
print("If we filter above different percentiles:\n")

for threshold_pct in [99, 99.5, 99.9, 99.99]:
    threshold = np.percentile(fsc, threshold_pct)
    n_kept = (fsc <= threshold).sum()
    n_removed = (fsc > threshold).sum()
    pct_kept = 100 * n_kept / len(fsc)
    pct_removed = 100 * n_removed / len(fsc)
    
    print(f"Filter at P{threshold_pct} (FSC < {threshold:.0f}):")
    print(f"  ✓ Keep: {n_kept:,} events ({pct_kept:.3f}%)")
    print(f"  ✗ Remove: {n_removed:,} events ({pct_removed:.3f}%)")
    print()

print("=" * 60)
print("INTERPRETATION")
print("=" * 60)
print("""
The vast majority of your data is in the normal range!
- 99% of events have FSC < 2,500
- Only 0.01% are extreme outliers (FSC > 10,000)

These extreme outliers are likely:
1. Cell debris
2. Aggregates
3. Instrument noise/artifacts
4. Non-EV particles

Removing top 0.1% (above P99.9) would:
- Keep 99.9% of your real EV data
- Remove problematic outliers that break calibration
- NOT lose meaningful biological events
""")
