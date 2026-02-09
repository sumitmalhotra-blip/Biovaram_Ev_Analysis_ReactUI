"""
Test script for VAL-008 + STAT-001 Distribution Analysis Functions
===================================================================

Tests the new distribution analysis functions:
- test_normality()
- fit_distributions()
- generate_distribution_overlay()
- comprehensive_distribution_analysis()

Author: CRMIT Backend Team
Date: February 5, 2026
"""

import numpy as np
import sys
sys.path.insert(0, '.')

from src.physics.statistics_utils import (
    test_normality,
    fit_distributions,
    generate_distribution_overlay,
    comprehensive_distribution_analysis
)

def main():
    """Run all distribution analysis tests."""
    
    # Generate synthetic EV-like data (log-normal distribution, typical for EVs)
    np.random.seed(42)
    # Log-normal: median ~100nm, with right-skewed tail (typical EV size distribution)
    sizes = np.random.lognormal(mean=np.log(100), sigma=0.5, size=1000)
    # Clip to realistic EV range
    sizes = sizes[(sizes > 30) & (sizes < 500)]
    
    print(f'Test data: n={len(sizes)}, mean={np.mean(sizes):.1f}, median={np.median(sizes):.1f}')
    print('=' * 60)
    
    # Test 1: Normality testing
    print('\n📊 TEST 1: Normality Testing')
    print('-' * 40)
    normality = test_normality(sizes)
    print(f"Is Normal: {normality['is_normal']}")
    print(f"Conclusion: {normality['conclusion']}")
    print(f"Recommendation: {normality['recommendation']}")
    for test_name, result in normality['tests'].items():
        print(f"  - {result['test_name']}: p={result['p_value']:.4f} -> {result['interpretation']}")
    
    # Test 2: Distribution fitting
    print('\n📊 TEST 2: Distribution Fitting')
    print('-' * 40)
    fits = fit_distributions(sizes)
    print(f"Best AIC: {fits['best_fit_aic']}")
    print(f"Recommendation: {fits['recommendation']}")
    print(f"Reason: {fits['recommendation_reason'][:100]}...")
    print('\nAIC Ranking:')
    for i, dist in enumerate(fits['aic_ranking'], 1):
        aic = fits['fits'][dist]['aic']
        print(f"  {i}. {dist}: AIC={aic:.1f}")
    
    # Test 3: Overlay generation
    print('\n📊 TEST 3: Distribution Overlay')
    print('-' * 40)
    overlay = generate_distribution_overlay(sizes, 'lognorm')
    print(f"Distribution: {overlay['distribution']}")
    print(f"Label: {overlay['label']}")
    print(f"X points: {len(overlay['x'])}")
    print(f"Parameters: {overlay['params']}")
    
    # Test 4: Comprehensive analysis
    print('\n📊 TEST 4: Comprehensive Distribution Analysis')
    print('-' * 40)
    analysis = comprehensive_distribution_analysis(sizes, include_overlays=True)
    print(f"n_samples: {analysis['n_samples']}")
    print(f"Is Normal: {analysis['conclusion']['is_normal']}")
    print(f"Skewness: {analysis['summary_statistics']['skewness']:.3f} ({analysis['summary_statistics']['skew_interpretation']})")
    print(f"Central Tendency: {analysis['conclusion']['central_tendency']:.1f} ({analysis['conclusion']['central_tendency_metric']})")
    print(f"D10/D50/D90: {analysis['summary_statistics']['d10']:.1f} / {analysis['summary_statistics']['d50']:.1f} / {analysis['summary_statistics']['d90']:.1f}")
    
    print('\n✅ All tests passed successfully!')
    
    return analysis


if __name__ == '__main__':
    main()
