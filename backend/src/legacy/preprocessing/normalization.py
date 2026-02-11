"""
Data Normalization Module - Data Preprocessing Component
========================================================

Purpose: Standardize units and scales across different instruments

Architecture Compliance:
- Layer 2: Data Preprocessing
- Component: Normalization
- Function: Unit conversion, scale standardization, baseline normalization

Author: CRMIT Team
Date: November 15, 2025
"""

from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from loguru import logger


class DataNormalizer:
    """
    Normalize data across multiple instruments.
    
    Normalization types:
    - Unit conversion (nm, μm, particles/mL)
    - Z-score normalization
    - Min-max scaling
    - Baseline normalization (control subtraction)
    """
    
    def __init__(self):
        """Initialize normalizer."""
        self.normalization_params: Dict[str, Dict[str, Any]] = {}
        
    def normalize_fcs_data(
        self,
        fcs_data: pd.DataFrame,
        method: str = 'zscore',
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Normalize FCS scatter and fluorescence intensities for cross-sample comparison.
        
        Args:
            fcs_data: FCS statistics
            method: 'zscore', 'minmax', or 'robust'
            columns: Specific columns to normalize (default: all numeric)
        
        Returns:
            Normalized FCS data with '_norm' suffix columns added
        
        WHY NORMALIZE:
        --------------
        Different cytometer runs have variation in:
        - Laser intensity (day-to-day fluctuation)
        - PMT voltage settings (changed between experiments)
        - Sample concentration (dilution differences)
        - Ambient temperature (affects electronics)
        
        Normalization enables:
        - Comparing samples across different days
        - Pooling data from multiple experiments
        - Machine learning (requires same scale)
        - Statistical testing (assumes similar distributions)
        
        NORMALIZATION METHODS:
        ----------------------
        1. Z-Score (default): (x - mean) / std
           - Result: mean=0, std=1
           - Use: When data is roughly normal distribution
           - Sensitive to outliers
        
        2. Min-Max: (x - min) / (max - min)
           - Result: range [0, 1]
           - Use: When need bounded range
           - Very sensitive to outliers
        
        3. Robust: (x - median) / IQR
           - Result: median=0, IQR=1
           - Use: When data has outliers
           - Most robust to extreme values
        
        EXAMPLE:
        --------
        Original FSC-A_mean values: [1000, 1500, 2000, 2500, 3000]
        
        Z-score normalized: [-1.41, -0.71, 0.0, 0.71, 1.41]
        Min-max normalized: [0.0, 0.25, 0.5, 0.75, 1.0]
        Robust normalized:  [-1.0, -0.5, 0.0, 0.5, 1.0]
        """
        logger.info(f"🔧 Normalizing FCS data using {method}...")
        
        # Create copy to avoid modifying original data
        fcs_normalized = fcs_data.copy()
        
        # Step 1: Select columns to normalize
        # -----------------------------------
        # Default: normalize all scatter and fluorescence channels
        # User can override by specifying specific columns
        if columns is None:
            # Standard channel names
            standard_cols = [
                'FSC-A_mean', 'FSC-A_median', 'FSC-H_mean',  # Forward scatter
                'SSC-A_mean', 'SSC-A_median', 'SSC-H_mean',  # Side scatter
                'FL1-A_mean', 'FL2-A_mean', 'FL3-A_mean'     # Fluorescence
            ]
            # Vendor-specific channel names (e.g., ZE5, Cytoflex)
            vendor_cols = [
                'VFSC-A_mean', 'VFSC-H_mean',  # Vendor forward scatter
                'VSSC-A_mean', 'VSSC-H_mean', 'VSSC1-A_mean',  # Vendor side scatter
                'B531-A_mean', 'Y585-A_mean', 'V450-A_mean'  # Vendor fluorescence
            ]
            # Filter to only columns that exist in the data
            columns = [c for c in standard_cols + vendor_cols if c in fcs_data.columns]
            
            # If no predefined columns found, normalize all numeric columns except metadata
            if not columns:
                exclude_cols = ['sample_id', 'file_name', 'total_events', 'qc_status', 'qc_flags']
                numeric_cols = fcs_data.select_dtypes(include=[np.number]).columns.tolist()
                columns = [c for c in numeric_cols if c not in exclude_cols]
        
        # Step 2: Normalize each column using selected method
        # ----------------------------------------------------
        for col in columns:
            # Extract column data as Series
            col_data = pd.Series(fcs_data[col])
            
            # Apply normalization method
            # New column name: original + '_norm' suffix
            # Example: 'FSC-A_mean' → 'FSC-A_mean_norm'
            if method == 'zscore':
                # Z-score: (x - mean) / std
                # Centers data at 0, scales by standard deviation
                fcs_normalized[f'{col}_norm'] = self._zscore_normalize(col_data)
            elif method == 'minmax':
                # Min-Max: (x - min) / (max - min)
                # Scales data to [0, 1] range
                fcs_normalized[f'{col}_norm'] = self._minmax_normalize(col_data)
            elif method == 'robust':
                # Robust: (x - median) / IQR
                # Centers at median, scales by interquartile range
                # Less sensitive to outliers than z-score
                fcs_normalized[f'{col}_norm'] = self._robust_normalize(col_data)
            else:
                raise ValueError(f"Unknown normalization method: {method}")
            
            # Store normalization parameters
            self.normalization_params[col] = {
                'mean': float(col_data.mean()),
                'std': float(col_data.std()),
                'min': float(col_data.min()),
                'max': float(col_data.max()),
                'median': float(col_data.median()),
                'q25': float(col_data.quantile(0.25)),
                'q75': float(col_data.quantile(0.75)),
            }
        
        logger.info(f"✅ Normalized {len(columns)} FCS columns")
        
        return fcs_normalized
    
    def normalize_nta_data(
        self,
        nta_data: pd.DataFrame,
        method: str = 'zscore',
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Normalize NTA size and concentration measurements.
        
        Args:
            nta_data: NTA statistics
            method: 'zscore', 'minmax', or 'robust'
            columns: Specific columns to normalize (default: all numeric)
        
        Returns:
            Normalized NTA data
        """
        logger.info(f"🔧 Normalizing NTA data using {method}...")
        
        nta_normalized = nta_data.copy()
        
        # Select columns to normalize
        if columns is None:
            columns = [
                'D10', 'D50', 'D90', 'mean_size', 'median_size',
                'concentration', 'particle_count'
            ]
            columns = [c for c in columns if c in nta_data.columns]
        
        # Normalize each column
        for col in columns:
            col_data = pd.Series(nta_data[col])
            if method == 'zscore':
                nta_normalized[f'{col}_norm'] = self._zscore_normalize(col_data)
            elif method == 'minmax':
                nta_normalized[f'{col}_norm'] = self._minmax_normalize(col_data)
            elif method == 'robust':
                nta_normalized[f'{col}_norm'] = self._robust_normalize(col_data)
            else:
                raise ValueError(f"Unknown normalization method: {method}")
            
            # Store normalization parameters
            self.normalization_params[col] = {
                'mean': float(col_data.mean()),
                'std': float(col_data.std()),
                'min': float(col_data.min()),
                'max': float(col_data.max()),
                'median': float(col_data.median()),
                'q25': float(col_data.quantile(0.25)),
                'q75': float(col_data.quantile(0.75)),
            }
        
        logger.info(f"✅ Normalized {len(columns)} NTA columns")
        
        return nta_normalized
    
    def _zscore_normalize(self, series: pd.Series) -> pd.Series:
        """Z-score normalization: (x - mean) / std"""
        mean = series.mean()
        std = series.std()
        
        if std == 0:
            logger.warning(f"Zero standard deviation detected, skipping normalization")
            return series
        
        return (series - mean) / std
    
    def _minmax_normalize(self, series: pd.Series) -> pd.Series:
        """Min-max normalization: (x - min) / (max - min)"""
        min_val = series.min()
        max_val = series.max()
        
        if min_val == max_val:
            logger.warning(f"Zero range detected, skipping normalization")
            return series
        
        return (series - min_val) / (max_val - min_val)
    
    def _robust_normalize(self, series: pd.Series) -> pd.Series:
        """Robust normalization using median and IQR: (x - median) / IQR"""
        median = series.median()
        q25 = series.quantile(0.25)
        q75 = series.quantile(0.75)
        iqr = q75 - q25
        
        if iqr == 0:
            logger.warning(f"Zero IQR detected, skipping normalization")
            return series
        
        return (series - median) / iqr
    
    def normalize_to_baseline(
        self,
        data: pd.DataFrame,
        baseline_samples: List[str],
        sample_id_col: str = 'sample_id',
        value_cols: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Normalize data relative to baseline/control samples.
        
        Args:
            data: DataFrame to normalize
            baseline_samples: List of baseline sample IDs
            sample_id_col: Column containing sample IDs
            value_cols: Columns to normalize (default: all numeric)
        
        Returns:
            Data normalized to baseline
        """
        logger.info(f"🔧 Normalizing to baseline: {len(baseline_samples)} control samples...")
        
        # Extract baseline data
        baseline_data = data[data[sample_id_col].isin(baseline_samples)]
        
        if len(baseline_data) == 0:
            logger.warning("No baseline samples found, skipping baseline normalization")
            return data
        
        # Select numeric columns if not specified
        if value_cols is None:
            value_cols = data.select_dtypes(include=[np.number]).columns.tolist()
            if value_cols:
                value_cols = [c for c in value_cols if c != sample_id_col]
        
        if not value_cols:
            logger.warning("No numeric columns to normalize")
            return data
        
        # Calculate baseline means
        baseline_means = baseline_data[value_cols].mean()
        
        # Normalize each column
        data_normalized = data.copy()
        baseline_means_series = pd.Series(baseline_means) if not isinstance(baseline_means, pd.Series) else baseline_means
        for col in value_cols:
            baseline_mean = float(baseline_means_series[col]) if col in baseline_means_series else 0.0
            
            if baseline_mean == 0:
                logger.warning(f"Zero baseline mean for {col}, using fold-change = 1")
                data_normalized[f'{col}_fold_change'] = 1.0
            else:
                # Calculate fold-change relative to baseline
                data_normalized[f'{col}_fold_change'] = data[col] / baseline_mean
                
                # Calculate log2 fold-change
                data_normalized[f'{col}_log2fc'] = np.log2(data_normalized[f'{col}_fold_change'])
        
        logger.info(f"✅ Baseline normalization complete for {len(value_cols)} columns")
        
        return data_normalized
    
    def convert_units(
        self,
        data: pd.DataFrame,
        column: str,
        from_unit: str,
        to_unit: str
    ) -> pd.DataFrame:
        """
        Convert units for a specific column.
        
        Supported conversions:
        - Size: nm ↔ μm ↔ mm
        - Concentration: particles/mL ↔ particles/L
        
        Args:
            data: DataFrame
            column: Column to convert
            from_unit: Current unit
            to_unit: Target unit
        
        Returns:
            Data with converted units
        """
        data = data.copy()
        
        # Define conversion factors
        size_conversions = {
            ('nm', 'μm'): 0.001,
            ('μm', 'nm'): 1000,
            ('nm', 'mm'): 0.000001,
            ('mm', 'nm'): 1000000,
            ('μm', 'mm'): 0.001,
            ('mm', 'μm'): 1000,
        }
        
        concentration_conversions = {
            ('particles/mL', 'particles/L'): 1000,
            ('particles/L', 'particles/mL'): 0.001,
        }
        
        # Attempt conversion
        conversion_key = (from_unit, to_unit)
        
        if conversion_key in size_conversions:
            factor = size_conversions[conversion_key]
            data[column] = data[column] * factor
            logger.info(f"✅ Converted {column}: {from_unit} → {to_unit} (factor: {factor})")
        elif conversion_key in concentration_conversions:
            factor = concentration_conversions[conversion_key]
            data[column] = data[column] * factor
            logger.info(f"✅ Converted {column}: {from_unit} → {to_unit} (factor: {factor})")
        else:
            raise ValueError(f"Unsupported unit conversion: {from_unit} → {to_unit}")
        
        return data
    
    def get_normalization_params(self) -> Dict[str, Dict[str, float]]:
        """Return normalization parameters for all columns."""
        return self.normalization_params
