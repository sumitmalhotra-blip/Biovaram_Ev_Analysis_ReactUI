"""
Size Binning Module - Data Preprocessing Component
==================================================

Purpose: Categorize particles by size ranges for analysis

Architecture Compliance:
- Layer 2: Data Preprocessing
- Component: Size Binning Engine
- Function: Group particles by customer-defined size thresholds (40-80nm, 80-100nm, 100-120nm)

Author: CRMIT Team
Date: November 15, 2025
"""

from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import numpy as np
from loguru import logger


class SizeBinning:
    """
    Bin particles by size ranges.
    
    Default bins (from architecture specification):
    - Small: 40-80 nm
    - Medium: 80-100 nm
    - Large: 100-120 nm
    - Extra-large: >120 nm
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
    
    def __init__(
        self,
        bins: Optional[List[Tuple[float, float]]] = None,
        bin_labels: Optional[List[str]] = None
    ):
        """
        Initialize size binning.
        
        Args:
            bins: List of (min, max) size tuples in nm
            bin_labels: Labels for each bin
        """
        # Default bins from architecture specification
        if bins is None:
            self.bins = [
                (0, 40),      # Sub-exosome
                (40, 80),     # Small exosomes
                (80, 100),    # Medium exosomes
                (100, 120),   # Large exosomes
                (120, 1000),  # Microvesicles
            ]
        else:
            self.bins = bins
        
        if bin_labels is None:
            self.bin_labels = [
                'sub_40nm',
                'small_40_80nm',
                'medium_80_100nm',
                'large_100_120nm',
                'xl_over_120nm'
            ]
        else:
            self.bin_labels = bin_labels
        
        if len(self.bins) != len(self.bin_labels):
            raise ValueError("Number of bins must match number of labels")
    
    def bin_nta_data(self, nta_data: pd.DataFrame) -> pd.DataFrame:
        """
        Bin NTA particle size data.
        
        Args:
            nta_data: NTA statistics with D10, D50, D90
        
        Returns:
            NTA data with size bin assignments
        
        WHAT THIS DOES:
        ----------------
        Takes NTA measurements with percentile size data (D10, D50, D90) and assigns
        each sample to a size bin category (small, medium, large exosomes).
        
        HOW IT WORKS:
        --------------
        1. Primary bin assignment uses D50 (median size) as the representative size
           - Rationale: D50 represents the center of the size distribution
           - Example: If D50 = 85nm → "medium_80_100nm" bin
        
        2. For each size bin, estimates percentage of particles in that range
           - Uses D10, D50, D90 positions to infer distribution shape
           - Example: If D50 falls in 80-100nm bin, estimate ~40% of particles there
        
        WHY THIS DESIGN:
        ----------------
        - NTA outputs percentiles (D10, D50, D90), not individual particle sizes
        - Must estimate bin percentages from limited percentile information
        - D50 is most reliable metric (median is robust to outliers)
        - Full histogram would be ideal but not always available from NTA software
        
        EXAMPLE:
        --------
        Input NTA data:
            sample_id  D10  D50  D90
            Sample1    70   85   105
        
        Output with bins:
            sample_id  size_bin          pct_small_40_80nm  pct_medium_80_100nm
            Sample1    medium_80_100nm   10.0              40.0
        """
        logger.info("📊 Binning NTA particle sizes...")
        
        nta_binned = nta_data.copy()
        
        # Step 1: Assign primary bin based on D50 (median size)
        # -------------------------------------------------------
        # D50 = 50th percentile = median particle size in the distribution
        # This is the most representative single value for the sample
        # Handle both uppercase (D50) and lowercase (d50_nm) column naming conventions
        size_column = None
        if 'D50' in nta_data.columns:
            size_column = 'D50'
        elif 'd50_nm' in nta_data.columns:
            size_column = 'd50_nm'
        elif 'median_size_nm' in nta_data.columns:
            size_column = 'median_size_nm'
        elif 'mean_size' in nta_data.columns:
            size_column = 'mean_size'
        elif 'mean_size_nm' in nta_data.columns:
            size_column = 'mean_size_nm'
        
        if size_column:
            nta_binned['size_bin'] = nta_data[size_column].apply(self._assign_bin)
        else:
            logger.warning("No size column found, cannot bin data")
            return nta_binned
        
        # Normalize column names for percentage calculation
        # Map various naming conventions to standard D10, D50, D90
        calc_data = nta_data.copy()
        col_mapping = {
            'd10_nm': 'D10', 'd50_nm': 'D50', 'd90_nm': 'D90',
            'D10_nm': 'D10', 'D50_nm': 'D50', 'D90_nm': 'D90',
        }
        for old_col, new_col in col_mapping.items():
            if old_col in calc_data.columns and new_col not in calc_data.columns:
                calc_data[new_col] = calc_data[old_col]
        
        # Calculate percentage in each bin (estimated from D10, D50, D90)
        for i, (bin_min, bin_max) in enumerate(self.bins):
            bin_label = self.bin_labels[i]
            nta_binned[f'pct_{bin_label}'] = calc_data.apply(
                lambda row: self._estimate_bin_percentage(row, bin_min, bin_max),
                axis=1
            )
        
        # Log bin distribution
        bin_counts = nta_binned['size_bin'].value_counts()
        logger.info("✅ Size bin distribution:")
        for bin_label, count in bin_counts.items():
            logger.info(f"   - {bin_label}: {count} samples ({count/len(nta_binned)*100:.1f}%)")
        
        return nta_binned
    
    def bin_fcs_data(self, fcs_data: pd.DataFrame, size_calibration: Optional[Dict[str, float]] = None) -> pd.DataFrame:
        """
        Bin FCS data by scatter intensity (proxy for size).
        
        Note: FCS scatter intensity correlates with particle size but requires calibration.
        
        Args:
            fcs_data: FCS statistics
            size_calibration: Mapping from FSC-A values to size (nm)
        
        Returns:
            FCS data with size bin estimates
        
        WHAT THIS DOES:
        ----------------
        Assigns FCS samples to size bins based on forward scatter (FSC-A) intensity,
        which correlates with particle size through Mie scattering theory.
        
        HOW IT WORKS:
        --------------
        Two modes:
        
        A) WITH calibration (preferred):
           - Uses Mie scatter calibration curve to convert FSC-A → size (nm)
           - Formula: size_nm = slope * FSC_A + intercept
           - Then bins by actual calculated size
           - Example: FSC-A=500 → 85nm → "medium_80_100nm" bin
        
        B) WITHOUT calibration (fallback):
           - Uses FSC-A quartiles as rough size proxies
           - Lowest 25% FSC → small bin, highest 25% → large bin
           - Less accurate but provides approximate binning
        
        WHY THIS DESIGN:
        ----------------
        - FCS doesn't directly measure size (unlike NTA)
        - FSC-A intensity is proportional to particle cross-sectional area
        - Mie scattering theory enables FSC-A → size conversion
        - Calibration curve built from NTA+FCS matched samples
        - Without calibration, can still do relative size comparisons
        
        CALIBRATION CURVE EXAMPLE:
        --------------------------
        From validate_fcs_vs_nta.py regression:
            size_nm = 0.15 * FSC_A + 25.0
        
        So: FSC_A=200 → 55nm (small)
            FSC_A=400 → 85nm (medium)
            FSC_A=600 → 115nm (large)
        """
        logger.info("📊 Binning FCS data by scatter intensity...")
        
        fcs_binned = fcs_data.copy()
        
        # Mode A: No calibration - use quartile-based binning
        # ----------------------------------------------------
        # This is a ROUGH approximation when calibration unavailable
        # Lower FSC-A → smaller particles, higher FSC-A → larger particles
        if size_calibration is None:
            logger.warning("No size calibration provided, using FSC-A quartiles as proxy")
            
            # Use quartiles as rough bin boundaries
            # pd.qcut splits data into equal-sized bins
            if 'FSC-A_mean' in fcs_data.columns:
                fcs_binned['size_bin'] = pd.qcut(
                    fcs_data['FSC-A_mean'],
                    q=len(self.bins),
                    labels=self.bin_labels,
                    duplicates='drop'
                )
        else:
            # Convert FSC-A to estimated size using calibration
            if 'FSC-A_mean' in fcs_data.columns:
                fcs_binned['estimated_size_nm'] = fcs_data['FSC-A_mean'].apply(
                    lambda x: self._calibrate_fcs_to_size(x, size_calibration)
                )
                fcs_binned['size_bin'] = fcs_binned['estimated_size_nm'].apply(self._assign_bin)
        
        logger.info("✅ FCS size binning complete")
        
        return fcs_binned
    
    def _assign_bin(self, size: float) -> str:
        """Assign a size value to a bin."""
        if pd.isna(size):
            return 'unknown'
        
        for i, (bin_min, bin_max) in enumerate(self.bins):
            if bin_min <= size < bin_max:
                return self.bin_labels[i]
        
        # If size exceeds all bins
        return self.bin_labels[-1]
    
    def _estimate_bin_percentage(self, row: pd.Series, bin_min: float, bin_max: float) -> float:
        """
        Estimate percentage of particles in a size bin.
        
        Uses D10, D50, D90 to estimate distribution.
        Note: This is a rough approximation. Full histogram would be more accurate.
        
        ESTIMATION STRATEGY:
        --------------------
        Since NTA only provides 3 percentile markers (D10, D50, D90), we must estimate
        the percentage of particles in each size bin.
        
        Logic:
        - If D50 (median) falls in bin → estimate 40% of particles in that bin
        - If D10 (10th percentile) in bin → estimate 10% in that bin
        - If D90 (90th percentile) in bin → estimate 10% in that bin
        - If bin is below D10 → 0% (all particles are larger)
        - If bin is above D90 → 0% (all particles are smaller)
        - Otherwise → rough estimate of 20% (bin partially covered)
        
        LIMITATIONS:
        ------------
        This is a CRUDE approximation because:
        - Real distributions are continuous, not discrete markers
        - Assumes symmetric distribution around D50 (not always true)
        - Doesn't account for distribution shape (normal vs skewed)
        
        BETTER APPROACH:
        ----------------
        If NTA software exports full size histogram → use actual bin counts
        Example: NanoSight exports CSV with size bins and particle counts per bin
        """
        d10 = row.get('D10', np.nan)
        d50 = row.get('D50', np.nan)
        d90 = row.get('D90', np.nan)
        
        # Check for None or NaN
        if d10 is None or d50 is None or d90 is None:
            return np.nan
        
        # Handle scalar vs array pd.isna checks
        try:
            if pd.isna(d10) or pd.isna(d50) or pd.isna(d90):
                return np.nan
        except ValueError:
            # If we have an array, check if all values are NaN
            pass
        
        # Convert to float for safe comparisons
        d10_f = self._safe_float(d10, np.nan)
        d50_f = self._safe_float(d50, np.nan)
        d90_f = self._safe_float(d90, np.nan)
        
        if np.isnan(d10_f) or np.isnan(d50_f) or np.isnan(d90_f):
            return np.nan
        
        # Count how many percentile markers fall in this bin
        markers_in_bin = 0
        markers_total = 3
        
        if bin_min <= d10_f < bin_max:
            markers_in_bin += 1
        if bin_min <= d50_f < bin_max:
            markers_in_bin += 1
        if bin_min <= d90_f < bin_max:
            markers_in_bin += 1
        
        # Rough estimate: if D50 is in bin, assume 40% of particles
        # If D10 is in bin, assume 10%, if D90 assume 10%
        if bin_min <= d50 < bin_max:
            return 40.0
        elif bin_min <= d10 < bin_max:
            return 10.0
        elif bin_min <= d90 < bin_max:
            return 10.0
        elif d10 > bin_max:
            return 0.0  # All particles are larger
        elif d90 < bin_min:
            return 0.0  # All particles are smaller
        else:
            # Bin is partially covered
            return 20.0  # Rough estimate
    
    def _calibrate_fcs_to_size(self, fsc_value: float, calibration: Dict[str, float]) -> float:
        """
        Convert FSC-A value to estimated particle size using calibration curve.
        
        Calibration format: {'slope': m, 'intercept': b} for size = m * FSC + b
        """
        slope = calibration.get('slope', 1.0)
        intercept = calibration.get('intercept', 0.0)
        
        return slope * fsc_value + intercept
    
    def aggregate_by_bin(
        self,
        data: pd.DataFrame,
        value_columns: List[str],
        bin_column: str = 'size_bin'
    ) -> pd.DataFrame:
        """
        Aggregate statistics by size bin.
        
        Args:
            data: Data with size bins assigned
            value_columns: Columns to aggregate
            bin_column: Column containing bin assignments
        
        Returns:
            Aggregated statistics per bin
        """
        logger.info(f"📊 Aggregating {len(value_columns)} columns by size bin...")
        
        if bin_column not in data.columns:
            logger.warning(f"Bin column '{bin_column}' not found")
            return pd.DataFrame()
        
        # Aggregate statistics - use explicit list type for aggregation functions
        agg_funcs: list[str] = ['mean', 'median', 'std', 'count']
        agg_dict: dict[str, list[str]] = {col: agg_funcs for col in value_columns}
        
        binned_stats = data.groupby(bin_column).agg(agg_dict)  # type: ignore[arg-type]
        
        # Flatten multi-level column names
        binned_stats.columns = ['_'.join(col).strip() for col in binned_stats.columns.values]
        binned_stats = binned_stats.reset_index()
        
        logger.info(f"✅ Aggregated statistics for {len(binned_stats)} bins")
        
        return binned_stats
    
    def get_bin_definitions(self) -> pd.DataFrame:
        """Return bin definitions as DataFrame."""
        bin_defs = []
        for i, (bin_min, bin_max) in enumerate(self.bins):
            bin_defs.append({
                'bin_label': self.bin_labels[i],
                'min_size_nm': bin_min,
                'max_size_nm': bin_max,
                'bin_width_nm': bin_max - bin_min
            })
        
        return pd.DataFrame(bin_defs)
