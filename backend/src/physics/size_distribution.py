"""
Per-Event Size Distribution Analyzer
=====================================

Calculates particle size for EVERY event in FCS data using:
1. Mie theory lookup table (fast, batch processing)
2. Optional bead calibration (absolute sizing)

Provides comprehensive size distribution analysis including:
- Full distribution histograms
- Percentile calculations (D10, D50, D90)
- KDE-based mode finding
- Multi-modal detection
- Sample comparison

Author: CRMIT Backend Team
Date: January 20, 2026
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import json
from loguru import logger

from .mie_scatter import MieScatterCalculator
from .statistics_utils import (
    calculate_mode_kde, 
    calculate_comprehensive_stats,
    create_size_histogram,
    compare_distributions,
    detect_multimodality,
    DistributionStats
)


@dataclass
class SizeDistributionResult:
    """
    Complete size distribution analysis for a sample.
    
    Attributes:
        sample_name: Name/identifier of the sample
        n_total_events: Total events in sample
        n_valid_events: Events with valid size calculation
        diameters: Array of calculated diameters (nm)
        statistics: Comprehensive statistics
        histogram: Histogram data
        multimodality: Multimodality analysis
        calibration_method: 'mie_theory' or 'bead_calibrated'
    """
    sample_name: str
    n_total_events: int
    n_valid_events: int
    valid_fraction: float
    statistics: Dict[str, Any]
    histogram: Dict[str, Any]
    multimodality: Dict[str, Any]
    calibration_method: str
    mie_parameters: Optional[Dict[str, float]] = None
    
    # Store diameters separately (large array)
    _diameters: Optional[np.ndarray] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without large arrays)."""
        d = {
            'sample_name': self.sample_name,
            'n_total_events': self.n_total_events,
            'n_valid_events': self.n_valid_events,
            'valid_fraction': self.valid_fraction,
            'statistics': self.statistics,
            'histogram': {k: v.tolist() if isinstance(v, np.ndarray) else v 
                         for k, v in self.histogram.items()},
            'multimodality': self.multimodality,
            'calibration_method': self.calibration_method,
            'mie_parameters': self.mie_parameters
        }
        return d


class PerEventSizeAnalyzer:
    """
    Analyzes particle sizes for every event in flow cytometry data.
    
    This is the most detailed analysis possible, providing:
    - Individual size for each detected particle
    - Full statistical distributions
    - Population substructure detection
    
    Example Usage:
        >>> analyzer = PerEventSizeAnalyzer(
        ...     wavelength_nm=488,
        ...     n_particle=1.40,
        ...     n_medium=1.33
        ... )
        >>> 
        >>> # Analyze a sample
        >>> result = analyzer.analyze_sample(fsc_values, "PC3_Exo")
        >>> print(f"D50: {result.statistics['d50']:.1f} nm")
        >>> print(f"Mode: {result.statistics['mode']:.1f} nm")
    """
    
    def __init__(
        self,
        wavelength_nm: float = 488.0,
        n_particle: float = 1.40,
        n_medium: float = 1.33,
        size_range_nm: Tuple[float, float] = (30, 500),
        lut_resolution: int = 1000,
        calibration_file: Optional[str] = None
    ):
        """
        Initialize the analyzer.
        
        Args:
            wavelength_nm: Laser wavelength
            n_particle: Particle refractive index
            n_medium: Medium refractive index
            size_range_nm: (min, max) diameter range for analysis
            lut_resolution: Number of points in lookup table
            calibration_file: Path to bead calibration file (optional)
        """
        self.wavelength_nm = wavelength_nm
        self.n_particle = n_particle
        self.n_medium = n_medium
        self.size_range_nm = size_range_nm
        self.lut_resolution = lut_resolution
        
        # Initialize Mie calculator
        self.mie_calc = MieScatterCalculator(
            wavelength_nm=wavelength_nm,
            n_particle=n_particle,
            n_medium=n_medium
        )
        
        # Build lookup table for fast conversion
        self._build_lookup_table()
        
        # Load bead calibration if provided
        self.bead_calibration = None
        if calibration_file:
            self._load_calibration(calibration_file)
        
        logger.info(
            f"✓ PerEventSizeAnalyzer initialized: "
            f"λ={wavelength_nm}nm, size_range={size_range_nm}, "
            f"LUT={lut_resolution} points"
        )
    
    def _build_lookup_table(self) -> None:
        """Build FSC → diameter lookup table using Mie theory."""
        diameters = np.linspace(
            self.size_range_nm[0], 
            self.size_range_nm[1], 
            self.lut_resolution
        )
        
        fsc_values = np.zeros(self.lut_resolution)
        
        for i, d in enumerate(diameters):
            result = self.mie_calc.calculate_scattering_efficiency(d, validate=False)
            fsc_values[i] = result.forward_scatter
        
        # Store lookup table
        self._lut_diameters = diameters
        self._lut_fsc = fsc_values
        
        # For interpolation, ensure FSC is monotonically increasing
        # Sort by FSC values
        sort_idx = np.argsort(fsc_values)
        self._lut_fsc_sorted = fsc_values[sort_idx]
        self._lut_diameters_sorted = diameters[sort_idx]
        
        # Remove duplicates for interpolation
        unique_mask = np.diff(self._lut_fsc_sorted, prepend=-np.inf) > 0
        self._lut_fsc_unique = self._lut_fsc_sorted[unique_mask]
        self._lut_diameters_unique = self._lut_diameters_sorted[unique_mask]
        
        logger.debug(f"Built LUT: FSC range [{fsc_values.min():.2e}, {fsc_values.max():.2e}]")
    
    def _load_calibration(self, filepath: str) -> None:
        """Load bead calibration from file."""
        from .bead_calibration import BeadCalibrationCurve
        self.bead_calibration = BeadCalibrationCurve.load(filepath)
        logger.info(f"✓ Loaded bead calibration from {filepath}")
    
    def fsc_to_diameter_mie(
        self,
        fsc_values: np.ndarray,
        scaling_factor: float = 1.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Convert FSC values to diameters using Mie theory LUT.
        
        Args:
            fsc_values: Array of FSC intensity values
            scaling_factor: Factor to convert instrument FSC to theoretical FSC
                          (determined by calibration against known sample)
                          
        Returns:
            Tuple of (diameters, valid_mask)
        """
        fsc_values = np.asarray(fsc_values)
        
        # Apply scaling factor
        fsc_scaled = fsc_values / scaling_factor
        
        # Interpolate to find diameters
        diameters = np.interp(
            fsc_scaled,
            self._lut_fsc_unique,
            self._lut_diameters_unique
        )
        
        # Mark values outside valid FSC range
        fsc_min = self._lut_fsc_unique[0]
        fsc_max = self._lut_fsc_unique[-1]
        valid_mask = (
            (fsc_scaled >= fsc_min * 0.5) & 
            (fsc_scaled <= fsc_max * 2.0) &
            (fsc_values > 0)
        )
        
        return diameters, valid_mask
    
    def estimate_scaling_factor(
        self,
        fsc_values: np.ndarray,
        reference_d50_nm: float
    ) -> float:
        """
        Estimate scaling factor using a known D50 value.
        
        This allows calibration against NTA or other reference measurements.
        
        Args:
            fsc_values: FSC values from sample
            reference_d50_nm: Known D50 from reference measurement (e.g., NTA)
            
        Returns:
            Scaling factor to use with fsc_to_diameter_mie()
        """
        fsc_values = np.asarray(fsc_values)
        fsc_positive = fsc_values[fsc_values > 0]
        fsc_median = np.median(fsc_positive)
        
        # Get theoretical FSC for reference diameter
        result = self.mie_calc.calculate_scattering_efficiency(
            reference_d50_nm, 
            validate=False
        )
        theoretical_fsc = result.forward_scatter
        
        scaling_factor = fsc_median / theoretical_fsc
        
        logger.info(
            f"Estimated scaling factor: {scaling_factor:.2e} "
            f"(FSC median={fsc_median:.1f}, ref D50={reference_d50_nm}nm)"
        )
        
        return float(scaling_factor)
    
    def analyze_sample(
        self,
        fsc_values: np.ndarray,
        sample_name: str,
        scaling_factor: Optional[float] = None,
        reference_d50_nm: Optional[float] = None,
        bin_size_nm: float = 5.0,
        histogram_range: Tuple[float, float] = (0, 500)
    ) -> SizeDistributionResult:
        """
        Perform complete per-event size analysis.
        
        Args:
            fsc_values: Array of FSC values for all events
            sample_name: Name/identifier for the sample
            scaling_factor: Pre-calculated scaling factor
            reference_d50_nm: Reference D50 for auto-calibration
            bin_size_nm: Histogram bin size
            histogram_range: (min, max) for histogram
            
        Returns:
            SizeDistributionResult with complete analysis
        """
        fsc_values = np.asarray(fsc_values)
        n_total = len(fsc_values)
        
        logger.info(f"Analyzing {sample_name}: {n_total:,} events")
        
        # Determine calibration method
        if self.bead_calibration is not None:
            # Use bead calibration
            calibration_method = 'bead_calibrated'
            result = self.bead_calibration.calculate_sizes(fsc_values)
            diameters = result.diameters
            valid_mask = np.isfinite(diameters) & (diameters > 0)
        else:
            # Use Mie theory with scaling factor
            calibration_method = 'mie_theory'
            
            if scaling_factor is None and reference_d50_nm is not None:
                scaling_factor = self.estimate_scaling_factor(fsc_values, reference_d50_nm)
            elif scaling_factor is None:
                # Default: assume 127nm D50 (typical for small EVs)
                scaling_factor = self.estimate_scaling_factor(fsc_values, 127.0)
                logger.warning(f"No calibration provided, using default D50=127nm")
            
            diameters, valid_mask = self.fsc_to_diameter_mie(fsc_values, scaling_factor)
        
        # Filter to valid diameters
        diameters_valid = diameters[valid_mask]
        n_valid = len(diameters_valid)
        valid_fraction = n_valid / n_total if n_total > 0 else 0.0
        
        logger.info(f"  Valid events: {n_valid:,} ({valid_fraction*100:.1f}%)")
        
        # Calculate comprehensive statistics
        if n_valid > 0:
            stats = calculate_comprehensive_stats(diameters_valid)
            stats_dict = asdict(stats)
            
            # Create histogram
            histogram = create_size_histogram(
                diameters_valid,
                bin_size=bin_size_nm,
                range_nm=histogram_range,
                normalize=True
            )
            
            # Check for multimodality
            multimodality = detect_multimodality(diameters_valid)
            
        else:
            stats_dict = {}
            histogram = {}
            multimodality = {'is_multimodal': False, 'n_significant_modes': 0}
        
        # Create result
        result = SizeDistributionResult(
            sample_name=sample_name,
            n_total_events=n_total,
            n_valid_events=n_valid,
            valid_fraction=valid_fraction,
            statistics=stats_dict,
            histogram=histogram,
            multimodality=multimodality,
            calibration_method=calibration_method,
            mie_parameters={
                'wavelength_nm': self.wavelength_nm,
                'n_particle': self.n_particle,
                'n_medium': self.n_medium
            }
        )
        result._diameters = diameters_valid
        
        # Log key results
        if n_valid > 0:
            logger.info(
                f"  D10={stats_dict['d10']:.1f}, "
                f"D50={stats_dict['d50']:.1f}, "
                f"D90={stats_dict['d90']:.1f} nm"
            )
            logger.info(
                f"  Mode={stats_dict['mode']:.1f} nm, "
                f"Mean={stats_dict['mean']:.1f}±{stats_dict['std']:.1f} nm"
            )
        
        return result
    
    def analyze_fcs_file(
        self,
        fcs_path: str,
        fsc_channel: str = "VFSC-H",
        **kwargs
    ) -> SizeDistributionResult:
        """
        Analyze FCS file directly.
        
        Args:
            fcs_path: Path to FCS file
            fsc_channel: Name of forward scatter channel
            **kwargs: Additional arguments for analyze_sample()
            
        Returns:
            SizeDistributionResult
        """
        from ..parsers.fcs_parser import FCSParser
        
        parser = FCSParser(Path(fcs_path))
        df = parser.parse()
        
        if fsc_channel not in df.columns:
            raise ValueError(f"Channel {fsc_channel} not found. Available: {list(df.columns)}")
        
        fsc_values = np.asarray(df[fsc_channel].values, dtype=np.float64)
        sample_name = kwargs.pop('sample_name', Path(fcs_path).stem)
        
        return self.analyze_sample(fsc_values, sample_name, **kwargs)
    
    def compare_samples(
        self,
        result1: SizeDistributionResult,
        result2: SizeDistributionResult
    ) -> Dict[str, Any]:
        """
        Statistical comparison of two samples.
        
        Args:
            result1, result2: SizeDistributionResult objects
            
        Returns:
            Comparison results with statistical tests
        """
        if result1._diameters is None or result2._diameters is None:
            raise ValueError("Diameter arrays not available for comparison")
        
        comparison = compare_distributions(
            result1._diameters,
            result2._diameters,
            test='ks'
        )
        
        comparison['sample1'] = result1.sample_name
        comparison['sample2'] = result2.sample_name
        comparison['d50_diff'] = (
            result1.statistics.get('d50', 0) - 
            result2.statistics.get('d50', 0)
        )
        comparison['mean_diff'] = (
            result1.statistics.get('mean', 0) - 
            result2.statistics.get('mean', 0)
        )
        
        return comparison
    
    def save_results(
        self,
        result: SizeDistributionResult,
        output_path: str,
        include_diameters: bool = False
    ) -> None:
        """
        Save analysis results to JSON.
        
        Args:
            result: SizeDistributionResult to save
            output_path: Output file path
            include_diameters: If True, include full diameter array
        """
        data = result.to_dict()
        
        if include_diameters and result._diameters is not None:
            # Save diameters as separate file to keep JSON manageable
            diameter_path = Path(output_path).with_suffix('.diameters.npy')
            np.save(diameter_path, result._diameters)
            data['diameter_file'] = str(diameter_path)
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"✓ Results saved to {output_path}")


def batch_analyze_fcs_files(
    fcs_files: List[str],
    analyzer: PerEventSizeAnalyzer,
    reference_d50_nm: float = 127.0,
    output_dir: Optional[str] = None
) -> List[SizeDistributionResult]:
    """
    Batch analyze multiple FCS files.
    
    Args:
        fcs_files: List of FCS file paths
        analyzer: Configured PerEventSizeAnalyzer
        reference_d50_nm: Reference D50 for calibration
        output_dir: Directory to save results (optional)
        
    Returns:
        List of SizeDistributionResult objects
    """
    results = []
    
    for fcs_path in fcs_files:
        try:
            result = analyzer.analyze_fcs_file(
                fcs_path,
                reference_d50_nm=reference_d50_nm
            )
            results.append(result)
            
            if output_dir:
                output_path = Path(output_dir) / f"{Path(fcs_path).stem}_size_analysis.json"
                analyzer.save_results(result, str(output_path))
                
        except Exception as e:
            logger.error(f"Failed to analyze {fcs_path}: {e}")
    
    return results
