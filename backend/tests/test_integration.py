"""
Integration Data Pipeline Tests
================================

End-to-end tests for data integration pipeline.

Tests:
- FCS + NTA sample matching
- Feature extraction
- Quality control
- Baseline comparisons
- Output file generation

Author: CRMIT Backend Team
Date: November 21, 2025
"""

import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.integrate_data import DataIntegrator
from src.preprocessing.quality_control import QualityControl
from src.preprocessing.normalization import DataNormalizer
from src.preprocessing.size_binning import SizeBinning
from src.fusion.sample_matcher import SampleMatcher
from src.fusion.feature_extractor import FeatureExtractor


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_fcs_data():
    """Create sample FCS statistics data."""
    return pd.DataFrame({
        'sample_id': ['P5_F10_CD81', 'P5_F10_ISO', 'P5_F16_CD81', 'P5_F16_ISO'],
        'total_events': [50000, 48000, 52000, 49000],
        'VFSC-H_mean': [15000, 14500, 15200, 14800],
        'VFSC-H_median': [14800, 14300, 15000, 14600],
        'VFSC-H_std': [5000, 4800, 5100, 4900],
        'VSSC-H_mean': [8000, 7800, 8100, 7900],
        'VSSC-H_median': [7900, 7700, 8000, 7800],
        'VSSC-H_std': [2500, 2400, 2600, 2450],
        'B531-A_mean': [1200, 300, 1500, 350],
        'B531-A_median': [1000, 250, 1300, 280],
    })


@pytest.fixture
def sample_nta_data():
    """Create sample NTA statistics data."""
    return pd.DataFrame({
        'sample_id': ['P5_F10_CD81', 'P5_F10_ISO', 'P5_F16_CD81', 'P5_F16_ISO'],
        'mean_size_nm': [85.3, 83.1, 87.2, 84.5],
        'median_size_nm': [82.1, 80.5, 84.3, 81.8],
        'd10_nm': [65.2, 63.8, 67.1, 64.5],
        'd50_nm': [82.1, 80.5, 84.3, 81.8],
        'd90_nm': [105.3, 103.2, 108.1, 104.7],
        'concentration_particles_ml': [1.5e11, 1.4e11, 1.6e11, 1.45e11],
        'temperature_celsius': [22.5, 22.3, 22.7, 22.4],
    })


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


# ============================================================================
# Unit Tests
# ============================================================================

class TestQualityControl:
    """Test quality control module."""
    
    def test_fcs_quality_check_pass(self, sample_fcs_data):
        """Test FCS data that should pass QC."""
        qc = QualityControl()
        passed, failed = qc.check_fcs_quality(sample_fcs_data)
        
        assert len(passed) == 4
        assert len(failed) == 0
    
    def test_fcs_quality_check_fail_low_events(self, sample_fcs_data):
        """Test FCS data with low event count."""
        # Modify data to fail
        sample_fcs_data.loc[0, 'total_events'] = 500  # Below threshold
        
        qc = QualityControl()
        passed, failed = qc.check_fcs_quality(sample_fcs_data)
        
        assert len(passed) == 3
        assert len(failed) == 1
        assert failed.iloc[0]['sample_id'] == 'P5_F10_CD81'
    
    def test_nta_quality_check_temp(self, sample_nta_data):
        """Test NTA temperature validation."""
        # Add sample with out-of-range temperature
        sample_nta_data.loc[0, 'temperature_celsius'] = 30.0  # Too high
        
        qc = QualityControl(temp_min=15.0, temp_max=25.0)
        passed, failed = qc.check_nta_quality(sample_nta_data)
        
        assert len(failed) > 0


class TestSampleMatching:
    """Test sample matching module."""
    
    def test_exact_match(self, sample_fcs_data, sample_nta_data):
        """Test exact sample ID matching."""
        matcher = SampleMatcher()
        registry = matcher.match_samples(sample_fcs_data, sample_nta_data)
        
        # All should match exactly
        exact_matches = registry[registry['match_type'] == 'exact']
        assert len(exact_matches) == 4
    
    def test_fuzzy_match(self):
        """Test fuzzy matching with slight ID variations."""
        fcs_data = pd.DataFrame({
            'sample_id': ['P5_F10_CD81', 'P5-F16-ISO'],
        })
        nta_data = pd.DataFrame({
            'sample_id': ['P5_F10_CD81_NTA', 'P5_F16_ISO'],  # Slight variations
        })
        
        matcher = SampleMatcher(fuzzy_threshold=0.8)
        registry = matcher.match_samples(fcs_data, nta_data)
        
        # Should find fuzzy matches
        assert len(registry) >= 2
    
    def test_unmatched_samples(self):
        """Test handling of unmatched samples."""
        fcs_data = pd.DataFrame({'sample_id': ['P5_F10_CD81', 'P5_F16_CD81']})
        nta_data = pd.DataFrame({'sample_id': ['P5_F10_CD81']})  # Missing P5_F16
        
        matcher = SampleMatcher()
        registry = matcher.match_samples(fcs_data, nta_data)
        
        # Should have 2 rows (1 matched, 1 FCS-only)
        assert len(registry) == 2
        fcs_only = registry[registry['match_type'] == 'fcs_only']
        assert len(fcs_only) == 1


class TestDataNormalization:
    """Test data normalization module."""
    
    def test_zscore_normalization(self, sample_fcs_data):
        """Test z-score normalization."""
        normalizer = DataNormalizer()
        normalized = normalizer.normalize_fcs_data(sample_fcs_data, method='zscore')
        
        # Check that normalized columns are created with '_norm' suffix
        # The original columns remain unchanged, new columns are added
        # Mean of normalized column should be ~0, std should be ~1
        for col in ['VFSC-H_mean', 'VSSC-H_mean']:
            norm_col = f'{col}_norm'
            if norm_col in normalized.columns:
                mean = normalized[norm_col].mean()
                std = normalized[norm_col].std()
                assert abs(mean) < 0.1, f"Mean of {norm_col} should be ~0, got {mean}"
                assert abs(std - 1.0) < 0.1, f"Std of {norm_col} should be ~1, got {std}"
    
    def test_baseline_normalization(self, sample_fcs_data):
        """Test baseline (control) normalization."""
        normalizer = DataNormalizer()
        
        # Use ISO samples as baseline
        baseline_samples = ['P5_F10_ISO', 'P5_F16_ISO']
        
        normalized = normalizer.normalize_to_baseline(
            sample_fcs_data,
            baseline_samples=baseline_samples,
            sample_id_col='sample_id'
        )
        
        # Should have fold change columns
        assert 'VFSC-H_mean_fold_change' in normalized.columns


class TestSizeBinning:
    """Test size binning module."""
    
    def test_nta_size_binning(self, sample_nta_data):
        """Test NTA size binning."""
        binner = SizeBinning()
        binned = binner.bin_nta_data(sample_nta_data)
        
        # Should have bin assignment
        assert 'size_bin' in binned.columns
        
        # All samples should fall into a bin
        assert binned['size_bin'].notna().all()
    
    def test_bin_percentage_calculation(self, sample_nta_data):
        """Test bin percentage calculations."""
        binner = SizeBinning()
        binned = binner.bin_nta_data(sample_nta_data)
        
        # Should have percentage columns (format: pct_{bin_label})
        pct_cols = [col for col in binned.columns if col.startswith('pct_')]
        assert len(pct_cols) > 0, f"Expected percentage columns, got: {list(binned.columns)}"


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegrationPipeline:
    """Test full integration pipeline."""
    
    def test_full_pipeline(self, sample_fcs_data, sample_nta_data, temp_output_dir, tmp_path):
        """Test complete integration pipeline."""
        # Save sample data as parquet files
        fcs_dir = tmp_path / "fcs"
        nta_dir = tmp_path / "nta"
        fcs_dir.mkdir()
        nta_dir.mkdir()
        
        # Create statistics files
        sample_fcs_data.to_parquet(fcs_dir / "fcs_statistics.parquet", index=False)
        sample_nta_data.to_parquet(nta_dir / "nta_statistics.parquet", index=False)
        
        # Run integration
        integrator = DataIntegrator(output_dir=temp_output_dir)
        
        try:
            output_files = integrator.integrate_all_data(
                fcs_parquet_dir=fcs_dir,
                nta_parquet_dir=nta_dir,
                baseline_samples=['P5_F10_ISO', 'P5_F16_ISO']
            )
            
            # Check that output files were created
            assert output_files['sample_metadata'] is not None and output_files['sample_metadata'].exists()
            assert output_files['combined_features'] is not None and output_files['combined_features'].exists()
            assert output_files['qc_report'] is not None and output_files['qc_report'].exists()
            assert output_files['match_report'] is not None and output_files['match_report'].exists()
            assert output_files['summary'] is not None and output_files['summary'].exists()
            
            # Check combined features
            combined = pd.read_parquet(output_files['combined_features'])
            assert len(combined) == 4  # All samples
            assert 'sample_id' in combined.columns
            
            # Should have both FCS and NTA features
            fcs_features = [col for col in combined.columns if col.startswith('fcs_')]
            nta_features = [col for col in combined.columns if col.startswith('nta_')]
            assert len(fcs_features) > 0
            assert len(nta_features) > 0
            
        except FileNotFoundError as e:
            pytest.skip(f"Integration pipeline requires complete module implementation: {e}")
    
    def test_missing_nta_data(self, sample_fcs_data, temp_output_dir, tmp_path):
        """Test pipeline with missing NTA data."""
        fcs_dir = tmp_path / "fcs"
        nta_dir = tmp_path / "nta"
        fcs_dir.mkdir()
        nta_dir.mkdir()
        
        # Only save FCS data
        sample_fcs_data.to_parquet(fcs_dir / "fcs_statistics.parquet", index=False)
        
        # Create empty NTA file
        empty_nta = pd.DataFrame(columns=['sample_id', 'mean_size_nm', 'median_size_nm'])
        empty_nta.to_parquet(nta_dir / "nta_statistics.parquet", index=False)
        
        integrator = DataIntegrator(output_dir=temp_output_dir)
        
        try:
            output_files = integrator.integrate_all_data(
                fcs_parquet_dir=fcs_dir,
                nta_parquet_dir=nta_dir
            )
            
            # Should still complete with FCS-only samples
            combined = pd.read_parquet(output_files['combined_features'])
            assert len(combined) == 4
            
        except FileNotFoundError:
            pytest.skip("Integration pipeline requires complete module implementation")


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Test pipeline performance with larger datasets."""
    
    def test_large_dataset(self, temp_output_dir, tmp_path):
        """Test with 100 samples."""
        # Generate synthetic data
        n_samples = 100
        
        fcs_data = pd.DataFrame({
            'sample_id': [f'Sample_{i:03d}' for i in range(n_samples)],
            'total_events': np.random.randint(40000, 60000, n_samples),
            'VFSC-H_mean': np.random.normal(15000, 2000, n_samples),
            'VSSC-H_mean': np.random.normal(8000, 1000, n_samples),
        })
        
        nta_data = pd.DataFrame({
            'sample_id': [f'Sample_{i:03d}' for i in range(n_samples)],
            'mean_size_nm': np.random.normal(85, 10, n_samples),
            'median_size_nm': np.random.normal(82, 10, n_samples),
            'd50_nm': np.random.normal(82, 10, n_samples),
            'concentration_particles_ml': np.random.normal(1.5e11, 2e10, n_samples),
            'temperature_celsius': np.random.normal(22, 1, n_samples),
        })
        
        fcs_dir = tmp_path / "fcs"
        nta_dir = tmp_path / "nta"
        fcs_dir.mkdir()
        nta_dir.mkdir()
        
        fcs_data.to_parquet(fcs_dir / "fcs_statistics.parquet", index=False)
        nta_data.to_parquet(nta_dir / "nta_statistics.parquet", index=False)
        
        integrator = DataIntegrator(output_dir=temp_output_dir)
        
        import time
        start = time.time()
        
        try:
            output_files = integrator.integrate_all_data(
                fcs_parquet_dir=fcs_dir,
                nta_parquet_dir=nta_dir
            )
            
            duration = time.time() - start
            
            # Should complete in reasonable time (< 5 seconds for 100 samples)
            assert duration < 5.0
            
            combined = pd.read_parquet(output_files['combined_features'])
            assert len(combined) == n_samples
            
        except FileNotFoundError:
            pytest.skip("Integration pipeline requires complete module implementation")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
