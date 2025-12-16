"""
Quality Control Module - Data Preprocessing Component
=====================================================

Purpose: Validate data quality and filter invalid measurements

Architecture Compliance:
- Layer 2: Data Preprocessing
- Component: Quality Control
- Function: Temperature checks, drift detection, invalid reading filters

Author: CRMIT Team
Date: November 15, 2025
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import numpy as np
from loguru import logger


class QualityControl:
    """
    Quality control checks for multi-modal instrument data.
    
    Checks performed:
    - Temperature compliance (NTA requires 15-25°C)
    - Measurement drift detection (time-series analysis)
    - Invalid reading filters (negative values, out-of-range data)
    - Blank/control validation
    """
    
    def __init__(
        self,
        temp_min: float = 15.0,
        temp_max: float = 25.0,
        drift_threshold: float = 0.15
    ):
        """
        Initialize quality control.
        
        Args:
            temp_min: Minimum acceptable temperature (°C)
            temp_max: Maximum acceptable temperature (°C)
            drift_threshold: Maximum acceptable drift (fraction, e.g., 0.15 = 15%)
        """
        self.temp_min = temp_min
        self.temp_max = temp_max
        self.drift_threshold = drift_threshold
        self.qc_report: Dict[str, Any] = {}
        
    def check_fcs_quality(self, fcs_data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Quality control for FCS data - validates data integrity and flags suspicious samples.
        
        Args:
            fcs_data: FCS statistics from Task 1.1
        
        Returns:
            Tuple of (passed_data, failed_data)
        
        QUALITY CHECKS PERFORMED:
        -------------------------
        1. Event count validation (negative/zero counts = instrument error)
        2. Scatter value validation (FSC/SSC must be positive)
        3. Coefficient of variation (CV > 100% = high noise or multiple populations)
        4. Blank detection (very low event counts = possible contamination/failure)
        
        QC STATUS VALUES:
        -----------------
        - 'pass': Sample meets all quality criteria
        - 'warn': Sample has minor issues but may be usable
        - 'fail': Sample fails critical checks, should be excluded
        
        WHY THESE CHECKS MATTER:
        ------------------------
        - Negative counts: Impossible, indicates data corruption
        - Zero/negative scatter: Physical impossibility (particles always scatter light)
        - High CV: Multiple populations, doublets, or instrument drift
        - Low event counts: Failed acquisition or blank sample
        """
        logger.info("🔍 Running FCS quality control checks...")
        
        # Create a copy to avoid modifying original data
        fcs_data = fcs_data.copy()
        
        # Initialize QC columns
        # All samples start as 'pass', then we flag failures
        fcs_data['qc_status'] = 'pass'
        fcs_data['qc_flags'] = ''  # Semicolon-separated list of failed checks
        
        # ============================================================
        # Check 1: Negative or Zero Event Counts
        # ============================================================
        # WHAT: Verify that total_events > 0
        # WHY: Negative counts are impossible (data corruption)
        #      Zero counts mean no acquisition (instrument error)
        # ACTION: Mark as 'fail' - this sample cannot be analyzed
        negative_events = fcs_data['total_events'] <= 0
        fcs_data.loc[negative_events, 'qc_status'] = 'fail'
        fcs_data.loc[negative_events, 'qc_flags'] = fcs_data.loc[negative_events, 'qc_flags'].astype(str) + 'negative_events;'
        
        # ============================================================
        # Check 1b: Minimum Event Count Threshold
        # ============================================================
        # WHAT: Verify that total_events >= MIN_EVENTS_THRESHOLD (1000)
        # WHY: Too few events means:
        #      - Insufficient statistical power for analysis
        #      - Possible acquisition failure or very dilute sample
        #      - Cannot reliably calculate percentages/statistics
        # ACTION: Mark as 'fail' - not enough data for reliable analysis
        MIN_EVENTS_THRESHOLD = 1000  # Minimum viable event count
        low_events = (fcs_data['total_events'] > 0) & (fcs_data['total_events'] < MIN_EVENTS_THRESHOLD)
        fcs_data.loc[low_events, 'qc_status'] = 'fail'
        fcs_data.loc[low_events, 'qc_flags'] = fcs_data.loc[low_events, 'qc_flags'].astype(str) + 'low_event_count;'
        
        # ============================================================
        # Check 2: Invalid Scatter Values
        # ============================================================
        # WHAT: Check FSC-A and SSC-A means are positive
        # WHY: Forward scatter and side scatter must be positive because:
        #      - All particles scatter light when illuminated
        #      - Zero/negative = detector failure or data corruption
        # ACTION: Mark as 'fail' - cannot calculate particle sizes
        for channel in ['FSC-A_mean', 'SSC-A_mean']:
            if channel in fcs_data.columns:
                # Check for: value <= 0 OR value is NaN (missing)
                invalid = (fcs_data[channel] <= 0) | (pd.isna(fcs_data[channel]))
                fcs_data.loc[invalid, 'qc_status'] = 'fail'
                fcs_data.loc[invalid, 'qc_flags'] = fcs_data.loc[invalid, 'qc_flags'].astype(str) + f'{channel}_invalid;'
        
        # ============================================================
        # Check 3: Extreme Coefficient of Variation (CV)
        # ============================================================
        # WHAT: Calculate CV = (std / mean) × 100%
        # WHY: CV > 100% indicates:
        #      - Multiple distinct populations (not single EV population)
        #      - High noise or instrument drift
        #      - Presence of aggregates or debris
        # ACTION: Mark as 'warn' - may still be usable with filtering
        if 'FSC-A_std' in fcs_data.columns and 'FSC-A_mean' in fcs_data.columns:
            # Calculate coefficient of variation for FSC-A
            cv = fcs_data['FSC-A_std'] / fcs_data['FSC-A_mean'] * 100
            
            # Flag samples with CV > 100%
            # Example: mean=1000, std=1200 → CV=120% (very heterogeneous)
            extreme_cv = cv > 100
            fcs_data.loc[extreme_cv, 'qc_status'] = 'warn'
            fcs_data.loc[extreme_cv, 'qc_flags'] = fcs_data.loc[extreme_cv, 'qc_flags'].astype(str) + 'extreme_cv;'
        
        # Check 4: Detect blank/control samples (very low event counts)
        median_events = fcs_data['total_events'].median()
        blank_threshold = median_events * 0.01  # 1% of median
        blanks = fcs_data['total_events'] < blank_threshold
        fcs_data.loc[blanks, 'qc_flags'] = fcs_data.loc[blanks, 'qc_flags'].astype(str) + 'possible_blank;'
        
        passed = fcs_data[fcs_data['qc_status'] == 'pass'].copy()
        failed = fcs_data[fcs_data['qc_status'] == 'fail'].copy()
        
        logger.info(f"✅ FCS QC complete: {len(passed)} passed, {len(failed)} failed")
        
        self.qc_report['fcs'] = {
            'total': len(fcs_data),
            'passed': len(passed),
            'failed': len(failed),
            'pass_rate': len(passed) / len(fcs_data) * 100 if len(fcs_data) > 0 else 0
        }
        
        # Ensure return types are DataFrames with explicit assertion
        assert isinstance(passed, pd.DataFrame)
        assert isinstance(failed, pd.DataFrame)
        
        return passed, failed
    
    def check_nta_quality(self, nta_data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Quality control for NTA data.
        
        Args:
            nta_data: NTA statistics from Task 1.2
        
        Returns:
            Tuple of (passed_data, failed_data)
        """
        logger.info("🔍 Running NTA quality control checks...")
        
        nta_data = nta_data.copy()
        nta_data['qc_status'] = 'pass'
        nta_data['qc_flags'] = ''
        
        # Check 1: Temperature compliance
        # Support both 'temperature' and 'temperature_celsius' column names
        temp_col = None
        if 'temperature_celsius' in nta_data.columns:
            temp_col = 'temperature_celsius'
        elif 'temperature' in nta_data.columns:
            temp_col = 'temperature'
        
        if temp_col is not None:
            temp_out_of_range = (nta_data[temp_col] < self.temp_min) | (nta_data[temp_col] > self.temp_max)
            nta_data.loc[temp_out_of_range, 'qc_status'] = 'fail'
            nta_data.loc[temp_out_of_range, 'qc_flags'] = nta_data.loc[temp_out_of_range, 'qc_flags'].astype(str) + 'temp_out_of_range;'
        
        # Check 2: Invalid size measurements
        if 'mean_size' in nta_data.columns:
            invalid_size = (nta_data['mean_size'] <= 0) | (pd.isna(nta_data['mean_size']))
            nta_data.loc[invalid_size, 'qc_status'] = 'fail'
            nta_data.loc[invalid_size, 'qc_flags'] = nta_data.loc[invalid_size, 'qc_flags'].astype(str) + 'invalid_size;'
        
        # Check 3: Invalid concentration
        if 'concentration' in nta_data.columns:
            invalid_conc = (nta_data['concentration'] < 0) | (pd.isna(nta_data['concentration']))
            nta_data.loc[invalid_conc, 'qc_status'] = 'fail'
            nta_data.loc[invalid_conc, 'qc_flags'] = nta_data.loc[invalid_conc, 'qc_flags'].astype(str) + 'invalid_concentration;'
        
        # Check 4: Unrealistic size distribution (D90/D10 ratio > 10)
        if 'D90' in nta_data.columns and 'D10' in nta_data.columns:
            size_ratio = nta_data['D90'] / nta_data['D10']
            extreme_poly = size_ratio > 10
            nta_data.loc[extreme_poly, 'qc_status'] = 'warn'
            nta_data.loc[extreme_poly, 'qc_flags'] = nta_data.loc[extreme_poly, 'qc_flags'].astype(str) + 'extreme_polydispersity;'
        
        # Check 5: Low particle count (< 100 particles)
        if 'particle_count' in nta_data.columns:
            low_count = nta_data['particle_count'] < 100
            nta_data.loc[low_count, 'qc_status'] = 'warn'
            nta_data.loc[low_count, 'qc_flags'] = nta_data.loc[low_count, 'qc_flags'].astype(str) + 'low_particle_count;'
        
        passed = nta_data[nta_data['qc_status'] == 'pass'].copy()
        failed = nta_data[nta_data['qc_status'] == 'fail'].copy()
        
        logger.info(f"✅ NTA QC complete: {len(passed)} passed, {len(failed)} failed")
        
        self.qc_report['nta'] = {
            'total': len(nta_data),
            'passed': len(passed),
            'failed': len(failed),
            'pass_rate': len(passed) / len(nta_data) * 100 if len(nta_data) > 0 else 0
        }
        
        # Ensure return types are DataFrames with explicit assertion
        assert isinstance(passed, pd.DataFrame)
        assert isinstance(failed, pd.DataFrame)
        
        return passed, failed
    
    def detect_drift(self, data: pd.DataFrame, value_column: str, time_column: str = 'timestamp') -> pd.DataFrame:
        """
        Detect measurement drift over time.
        
        Args:
            data: DataFrame with measurements
            value_column: Column to check for drift
            time_column: Column with timestamp (default: 'timestamp')
        
        Returns:
            DataFrame with drift flags
        """
        if time_column not in data.columns or value_column not in data.columns:
            logger.warning(f"Cannot detect drift: missing {time_column} or {value_column}")
            return data
        
        data = data.copy()
        data = data.sort_values(by=time_column)
        
        # Calculate rolling mean (window = 5 measurements)
        rolling_mean = data[value_column].rolling(window=5, min_periods=1).mean()
        
        # Calculate drift as percentage change from rolling mean
        drift = (data[value_column] - rolling_mean).abs() / rolling_mean
        
        # Flag measurements with excessive drift
        data['drift_detected'] = drift > self.drift_threshold
        data['drift_magnitude'] = drift
        
        drift_count = data['drift_detected'].sum()
        if drift_count > 0:
            logger.warning(f"⚠️ Detected drift in {drift_count} measurements ({value_column})")
        
        return data
    
    def get_qc_report(self) -> Dict[str, Any]:
        """Return quality control report."""
        return self.qc_report
    
    def export_qc_report(self, output_path: Path) -> None:
        """Export QC report to CSV."""
        if not self.qc_report:
            logger.warning("No QC report available")
            return
        
        # Flatten nested dictionary
        rows = []
        for instrument, metrics in self.qc_report.items():
            row = {'instrument': instrument}
            row.update(metrics)
            rows.append(row)
        
        report_df = pd.DataFrame(rows)
        report_df.to_csv(output_path, index=False)
        logger.info(f"QC report saved: {output_path}")
