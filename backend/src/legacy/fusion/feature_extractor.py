"""
Feature Extractor - Multi-Modal Data Fusion Component
=====================================================

Purpose: Extract and standardize features from each instrument type

Architecture Compliance:
- Layer 4: Multi-Modal Data Fusion
- Component: Feature Extractor
- Function: Extract FSC/SSC from FCS, D50/concentration from NTA, morphology from TEM

Author: CRMIT Team
Date: November 15, 2025
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from loguru import logger


class FeatureExtractor:
    """
    Extract features from multi-modal instrument data.
    
    Features extracted:
    - FCS: FSC-A, FSC-H, SSC-A, SSC-H, fluorescence channels, event counts
    - NTA: D10, D50, D90, concentration, particle counts, size distribution
    - TEM: Morphology metrics (future)
    """
    
    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        """Safely convert value to float, handling None."""
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
    
    def __init__(self):
        """Initialize feature extractor."""
        self.fcs_features: Optional[pd.DataFrame] = None
        self.nta_features: Optional[pd.DataFrame] = None
        self.tem_features: Optional[pd.DataFrame] = None
        
    def extract_fcs_features(self, fcs_data: pd.DataFrame) -> pd.DataFrame:
        """
        Extract features from FCS data.
        
        Args:
            fcs_data: FCS statistics from Task 1.1 batch processing
        
        Returns:
            DataFrame with FCS features (prefixed with 'fcs_')
        """
        logger.info("📊 Extracting FCS features...")
        
        features = []
        
        for _, row in fcs_data.iterrows():
            feature = {
                'sample_id': row['sample_id'],
                'fcs_file_name': row.get('file_name', row['sample_id']),  # Use sample_id as fallback
                
                # Scatter intensity features
                'fcs_fsc_a_mean': row.get('FSC-A_mean', np.nan),
                'fcs_fsc_a_median': row.get('FSC-A_median', np.nan),
                'fcs_fsc_a_std': row.get('FSC-A_std', np.nan),
                'fcs_fsc_h_mean': row.get('FSC-H_mean', np.nan),
                'fcs_fsc_h_median': row.get('FSC-H_median', np.nan),
                
                'fcs_ssc_a_mean': row.get('SSC-A_mean', np.nan),
                'fcs_ssc_a_median': row.get('SSC-A_median', np.nan),
                'fcs_ssc_a_std': row.get('SSC-A_std', np.nan),
                'fcs_ssc_h_mean': row.get('SSC-H_mean', np.nan),
                'fcs_ssc_h_median': row.get('SSC-H_median', np.nan),
                
                # Event counts
                'fcs_total_events': row.get('total_events', 0),
                
                # Fluorescence channels (if present)
                'fcs_fl1_mean': row.get('FL1-A_mean', np.nan),
                'fcs_fl1_median': row.get('FL1-A_median', np.nan),
                'fcs_fl2_mean': row.get('FL2-A_mean', np.nan),
                'fcs_fl2_median': row.get('FL2-A_median', np.nan),
                'fcs_fl3_mean': row.get('FL3-A_mean', np.nan),
                'fcs_fl3_median': row.get('FL3-A_median', np.nan),
                
                # Derived features
                'fcs_scatter_ratio': (
                    self._safe_float(row.get('FSC-A_mean'), np.nan) / self._safe_float(row.get('SSC-A_mean'), 1.0)
                ) if self._safe_float(row.get('SSC-A_mean'), 0) > 0 else np.nan,
                'fcs_cv_fsc': (
                    self._safe_float(row.get('FSC-A_std'), 0) / self._safe_float(row.get('FSC-A_mean'), 1.0) * 100
                ) if self._safe_float(row.get('FSC-A_mean'), 0) > 0 else np.nan,
                'fcs_cv_ssc': (
                    self._safe_float(row.get('SSC-A_std'), 0) / self._safe_float(row.get('SSC-A_mean'), 1.0) * 100
                ) if self._safe_float(row.get('SSC-A_mean'), 0) > 0 else np.nan,
            }
            
            features.append(feature)
        
        self.fcs_features = pd.DataFrame(features)
        
        logger.info(f"✅ Extracted {len(self.fcs_features)} FCS feature vectors")
        logger.info(f"   - Features per sample: {len([c for c in self.fcs_features.columns if c.startswith('fcs_')])}")
        
        return self.fcs_features
    
    def extract_nta_features(self, nta_data: pd.DataFrame) -> pd.DataFrame:
        """
        Extract features from NTA data.
        
        Args:
            nta_data: NTA statistics from Task 1.2 batch processing
        
        Returns:
            DataFrame with NTA features (prefixed with 'nta_')
        """
        logger.info("📊 Extracting NTA features...")
        
        features = []
        
        for _, row in nta_data.iterrows():
            feature = {
                'sample_id': row['sample_id'],
                'nta_file_name': row.get('file_name', row['sample_id']),  # Use sample_id as fallback
                
                # Size distribution features
                'nta_d10': row.get('D10', np.nan),
                'nta_d50': row.get('D50', np.nan),
                'nta_d90': row.get('D90', np.nan),
                'nta_mean_size': row.get('mean_size', np.nan),
                'nta_median_size': row.get('median_size', np.nan),
                'nta_std_size': row.get('std_size', np.nan),
                'nta_min_size': row.get('min_size', np.nan),
                'nta_max_size': row.get('max_size', np.nan),
                
                # Concentration features
                'nta_concentration': row.get('concentration', np.nan),
                'nta_particle_count': row.get('particle_count', 0),
                
                # Size distribution spread
                'nta_size_range': (
                    self._safe_float(row.get('max_size'), 0) - self._safe_float(row.get('min_size'), 0)
                ) if row.get('max_size') is not None else np.nan,
                'nta_iqr': (
                    self._safe_float(row.get('D90'), 0) - self._safe_float(row.get('D10'), 0)
                ) if row.get('D90') is not None else np.nan,
                'nta_polydispersity': (
                    self._safe_float(row.get('std_size'), 0) / self._safe_float(row.get('mean_size'), 1.0)
                ) if self._safe_float(row.get('mean_size'), 0) > 0 else np.nan,
                
                # Size bin percentages (Architecture requirement)
                'nta_pct_40_80nm': self._calculate_size_bin_pct(row, 40, 80),
                'nta_pct_80_100nm': self._calculate_size_bin_pct(row, 80, 100),
                'nta_pct_100_120nm': self._calculate_size_bin_pct(row, 100, 120),
                'nta_pct_over_120nm': self._calculate_size_bin_pct(row, 120, 1000),
                
                # Derived features
                'nta_cv': (
                    self._safe_float(row.get('std_size'), 0) / self._safe_float(row.get('mean_size'), 1.0) * 100
                ) if self._safe_float(row.get('mean_size'), 0) > 0 else np.nan,
            }
            
            features.append(feature)
        
        self.nta_features = pd.DataFrame(features)
        
        logger.info(f"✅ Extracted {len(self.nta_features)} NTA feature vectors")
        logger.info(f"   - Features per sample: {len([c for c in self.nta_features.columns if c.startswith('nta_')])}")
        
        return self.nta_features
    
    def _calculate_size_bin_pct(self, row: pd.Series, min_size: float, max_size: float) -> float:
        """
        Calculate percentage of particles in size bin.
        
        Note: Requires histogram data from NTA parser. Currently simplified.
        """
        # Placeholder - would use histogram data if available
        # For now, use rough estimate based on D10/D50/D90
        d10 = row.get('D10', np.nan)
        d50 = row.get('D50', np.nan)
        d90 = row.get('D90', np.nan)
        
        # Check for None values
        if d10 is None or d50 is None or d90 is None:
            return np.nan
        
        # Convert to float safely
        d10_f = self._safe_float(d10, np.nan)
        d50_f = self._safe_float(d50, np.nan)
        d90_f = self._safe_float(d90, np.nan)
        
        if np.isnan(d10_f) or np.isnan(d50_f) or np.isnan(d90_f):
            return np.nan
        
        # Rough estimation (should be replaced with histogram-based calculation)
        if d50_f >= min_size and d50_f <= max_size:
            return 50.0  # Median falls in this bin
        elif d10_f >= min_size and d10_f <= max_size:
            return 10.0
        elif d90_f >= min_size and d90_f <= max_size:
            return 90.0
        else:
            return 0.0
    
    def merge_features(
        self,
        sample_registry: pd.DataFrame,
        fcs_features: Optional[pd.DataFrame] = None,
        nta_features: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Merge all features into combined feature matrix.
        
        Args:
            sample_registry: Master sample registry from SampleMatcher
            fcs_features: FCS features (optional, uses cached if None)
            nta_features: NTA features (optional, uses cached if None)
        
        Returns:
            Combined feature matrix (~370 columns as per architecture)
        """
        logger.info("🔗 Merging features across instruments...")
        
        # Use cached features if not provided - handle DataFrame vs None properly
        if fcs_features is None:
            fcs_features = self.fcs_features
        if nta_features is None:
            nta_features = self.nta_features
        
        # Start with sample registry
        combined = sample_registry.copy()
        
        # Merge FCS features
        if fcs_features is not None and len(fcs_features) > 0 and 'sample_id' in fcs_features.columns:
            combined = combined.merge(
                fcs_features,
                left_on='sample_id_fcs',
                right_on='sample_id',
                how='left',
                suffixes=('', '_fcs_dup')
            )
            # Drop duplicate sample_id column
            if 'sample_id_fcs_dup' in combined.columns:
                combined = combined.drop(columns=['sample_id_fcs_dup'])
        
        # Merge NTA features
        if nta_features is not None and len(nta_features) > 0 and 'sample_id' in nta_features.columns:
            combined = combined.merge(
                nta_features,
                left_on='sample_id_nta',
                right_on='sample_id',
                how='left',
                suffixes=('', '_nta_dup')
            )
            # Drop duplicate sample_id column
            if 'sample_id_nta_dup' in combined.columns:
                combined = combined.drop(columns=['sample_id_nta_dup'])
        
        logger.info(f"✅ Combined features: {len(combined)} samples × {len(combined.columns)} features")
        
        # Calculate cross-instrument correlations
        combined = self._add_cross_instrument_features(combined)
        
        return combined
    
    def _add_cross_instrument_features(self, combined: pd.DataFrame) -> pd.DataFrame:
        """
        Add cross-instrument correlation features.
        
        Architecture requirement: "Cross-machine correlation (FSC vs D50 size)"
        """
        logger.info("🔗 Adding cross-instrument correlation features...")
        
        # FSC-A vs NTA D50 correlation (scatter intensity should correlate with particle size)
        if 'fcs_fsc_a_mean' in combined.columns and 'nta_d50' in combined.columns:
            combined['cross_fsc_d50_ratio'] = combined['fcs_fsc_a_mean'] / combined['nta_d50']
            combined['cross_size_scatter_correlation'] = np.where(
                combined['fcs_fsc_a_mean'] > combined['fcs_fsc_a_mean'].median(),
                combined['nta_d50'] > combined['nta_d50'].median(),
                np.nan
            )
        
        # Event count vs particle count correlation
        if 'fcs_total_events' in combined.columns and 'nta_particle_count' in combined.columns:
            combined['cross_event_particle_ratio'] = (
                combined['fcs_total_events'] / combined['nta_particle_count']
            )
        
        # Coefficient of variation comparison (homogeneity check)
        if 'fcs_cv_fsc' in combined.columns and 'nta_cv' in combined.columns:
            combined['cross_cv_diff'] = combined['fcs_cv_fsc'] - combined['nta_cv']
        
        logger.info("✅ Cross-instrument features added")
        
        return combined
    
    def get_feature_summary(self) -> Dict[str, int]:
        """Return summary of extracted features."""
        summary = {}
        
        if self.fcs_features is not None:
            summary['fcs_samples'] = len(self.fcs_features)
            summary['fcs_features'] = len([c for c in self.fcs_features.columns if c.startswith('fcs_')])
        
        if self.nta_features is not None:
            summary['nta_samples'] = len(self.nta_features)
            summary['nta_features'] = len([c for c in self.nta_features.columns if c.startswith('nta_')])
        
        return summary
