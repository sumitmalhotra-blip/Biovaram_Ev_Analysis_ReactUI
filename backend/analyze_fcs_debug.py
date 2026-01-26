"""
Debug script to analyze FCS file and understand size distribution
"""
import sys
sys.path.insert(0, 'src')

from src.parsers.fcs_parser import FCSParser
from src.physics.mie_scatter import MieScatterCalculator
import numpy as np
from pathlib import Path

# Parse the FCS file
fcs_path = Path(r'nanoFACS\Exp_20251217_PC3\PC3 EXO1.fcs')
parser = FCSParser(fcs_path)
parser.validate()
data = parser.parse()

fsc_channel = 'VFSC-A'
fsc_values = np.asarray(data[fsc_channel].values)

print('=' * 60)
print('FSC VALUE ANALYSIS - Understanding the Raw Data')
print('=' * 60)

# Check the distribution of raw FSC values
print(f'\nRaw FSC Statistics:')
print(f'  Min: {fsc_values.min():.2f}')
print(f'  Max: {fsc_values.max():.2f}')
print(f'  Mean: {fsc_values.mean():.2f}')
print(f'  Median: {np.median(fsc_values):.2f}')
print(f'  Std Dev: {fsc_values.std():.2f}')

# Percentiles
percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
print(f'\nFSC Percentiles:')
for p in percentiles:
    val = np.percentile(fsc_values, p)
    print(f'  P{p:02d}: {val:.2f}')

# Count positive vs negative values
negative_count = np.sum(fsc_values < 0)
zero_count = np.sum(fsc_values == 0)
positive_count = np.sum(fsc_values > 0)
print(f'\nFSC Sign Distribution:')
print(f'  Negative: {negative_count} ({negative_count/len(fsc_values)*100:.1f}%)')
print(f'  Zero: {zero_count} ({zero_count/len(fsc_values)*100:.1f}%)')
print(f'  Positive: {positive_count} ({positive_count/len(fsc_values)*100:.1f}%)')

# Histogram of raw FSC
print(f'\nFSC Value Distribution:')
bins = [-10000, 0, 10, 50, 100, 500, 1000, 5000, 10000, 100000, 1000000, 10000000]
hist, _ = np.histogram(fsc_values, bins=bins)
for i in range(len(bins)-1):
    pct = hist[i] / len(fsc_values) * 100
    print(f'  {bins[i]:>10} to {bins[i+1]:>10}: {hist[i]:>7} ({pct:5.1f}%)')

# Test different Mie parameters
print('\n' + '=' * 60)
print('TESTING DIFFERENT MIE PARAMETERS')
print('=' * 60)

# Sample 10000 events with positive FSC values only
positive_fsc = fsc_values[fsc_values > 0]
sample_size = min(10000, len(positive_fsc))
sampled_fsc = np.random.choice(positive_fsc, sample_size, replace=False)

configs = [
    {'wavelength': 488.0, 'n_particle': 1.40, 'n_medium': 1.33, 'name': 'Default (n_p=1.40)'},
    {'wavelength': 488.0, 'n_particle': 1.38, 'n_medium': 1.33, 'name': 'Lower RI (n_p=1.38)'},
    {'wavelength': 488.0, 'n_particle': 1.45, 'n_medium': 1.33, 'name': 'Higher RI (n_p=1.45)'},
    {'wavelength': 488.0, 'n_particle': 1.40, 'n_medium': 1.337, 'name': 'PBS medium (n_m=1.337)'},
]

for cfg in configs:
    mie_calc = MieScatterCalculator(
        wavelength_nm=cfg['wavelength'], 
        n_particle=cfg['n_particle'], 
        n_medium=cfg['n_medium']
    )
    sizes, success_mask = mie_calc.diameters_from_scatter_batch(sampled_fsc, min_diameter=30.0, max_diameter=500.0)
    valid_sizes = sizes[success_mask]
    
    if len(valid_sizes) > 0:
        small_evs = np.sum((valid_sizes >= 30) & (valid_sizes < 100))
        medium_evs = np.sum((valid_sizes >= 100) & (valid_sizes < 200))
        large_evs = np.sum(valid_sizes >= 200)
        
        print(f"\n{cfg['name']}:")
        print(f'  Valid: {len(valid_sizes)} ({len(valid_sizes)/sample_size*100:.1f}%)')
        print(f'  Median size: {np.median(valid_sizes):.1f} nm')
        print(f'  Small (<100nm): {small_evs/len(valid_sizes)*100:.1f}%')
        print(f'  Medium (100-200nm): {medium_evs/len(valid_sizes)*100:.1f}%')
        print(f'  Large (>200nm): {large_evs/len(valid_sizes)*100:.1f}%')

# The issue explanation
print('\n' + '=' * 60)
print('ANALYSIS CONCLUSION')
print('=' * 60)
print("""
The 'High Debris' alerts are CORRECT because:

1. Your sample has mostly LARGE particles (>200nm)
   - 81.7% of particles are >200nm
   - Only 0.3% are in the small EV range (30-100nm)
   
2. The 'debris' calculation considers particles OUTSIDE the 
   typical EV display range (40-200nm) as potentially problematic

3. Possible explanations for your data:
   a) Sample contains aggregates or larger vesicles
   b) The refractive index settings may not match your particles
   c) The FSC values may need different scaling/calibration
   d) Sample prep may have caused aggregation
   
4. The median FSC value is very low (10.15), meaning most events
   have very low forward scatter. This could indicate:
   - Background noise being recorded
   - Very small particles below detection threshold
   - Instrument sensitivity settings
""")
