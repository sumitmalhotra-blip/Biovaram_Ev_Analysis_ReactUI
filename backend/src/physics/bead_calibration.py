"""
Polystyrene Bead Calibration Module
====================================

Purpose: Provide absolute particle sizing through instrument calibration
         using polystyrene bead standards of known sizes.

Calibration Standards (typical):
- Polystyrene beads: n = 1.59 at 488nm
- Available sizes: 50, 100, 200, 300, 500, 800, 1000 nm
- Suppliers: Spherotech, Bangs Laboratories, Thermo Fisher

Theory:
-------
1. Run known-size beads through the instrument
2. Record their FSC (forward scatter) values
3. Build calibration curve: FSC → diameter
4. Apply curve to unknown samples

This bypasses theoretical Mie calculations and provides
instrument-specific, empirically validated sizing.

Author: CRMIT Backend Team
Date: January 20, 2026
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from scipy.interpolate import interp1d
from scipy.optimize import curve_fit
from loguru import logger
import json
from pathlib import Path


@dataclass
class BeadStandard:
    """
    Represents a polystyrene bead calibration standard.
    
    Attributes:
        diameter_nm: Nominal diameter in nanometers
        diameter_cv: Coefficient of variation (%)
        fsc_values: Measured FSC values for this bead
        fsc_mean: Mean FSC value
        fsc_std: Standard deviation of FSC
        n_events: Number of events measured
        refractive_index: RI of bead material (1.59 for polystyrene at 488nm)
    """
    diameter_nm: float
    diameter_cv: float = 5.0  # Typical CV for commercial beads
    fsc_values: Optional[np.ndarray] = None
    fsc_mean: Optional[float] = None
    fsc_std: Optional[float] = None
    n_events: int = 0
    refractive_index: float = 1.59  # Polystyrene at 488nm
    
    def __post_init__(self):
        if self.fsc_values is not None:
            self.fsc_mean = float(np.mean(self.fsc_values))
            self.fsc_std = float(np.std(self.fsc_values))
            self.n_events = len(self.fsc_values)


@dataclass
class CalibrationResult:
    """
    Results from applying calibration to unknown sample.
    
    Attributes:
        diameters: Array of calculated diameters for each event
        d10, d50, d90: Percentile diameters
        mean, std: Mean and standard deviation
        mode: Mode diameter (KDE-based)
        valid_fraction: Fraction of events within calibration range
    """
    diameters: np.ndarray
    d10: float
    d50: float
    d90: float
    mean: float
    std: float
    mode: float
    valid_fraction: float
    n_events: int
    calibration_range: Tuple[float, float]


class BeadCalibrationCurve:
    """
    Instrument-specific calibration curve using polystyrene bead standards.
    
    This class provides absolute particle sizing by:
    1. Using empirical FSC measurements from known-size beads
    2. Building interpolation/regression model
    3. Applying model to unknown samples
    
    Advantages over pure Mie theory:
    - Accounts for instrument-specific optical characteristics
    - No need to know exact detector geometry or gain
    - Empirically validated against known standards
    
    Example Usage:
        >>> # Create calibration with bead standards
        >>> calib = BeadCalibrationCurve()
        >>> 
        >>> # Add measured beads (diameter_nm, fsc_values)
        >>> calib.add_bead_standard(100, fsc_100nm_data)
        >>> calib.add_bead_standard(200, fsc_200nm_data)
        >>> calib.add_bead_standard(500, fsc_500nm_data)
        >>> 
        >>> # Build calibration curve
        >>> calib.fit()
        >>> 
        >>> # Apply to unknown sample
        >>> result = calib.calculate_sizes(unknown_fsc_data)
        >>> print(f"Median size: {result.d50:.1f} nm")
    """
    
    # Standard polystyrene bead sizes (nm)
    STANDARD_BEAD_SIZES = [50, 100, 200, 300, 500, 800, 1000]
    
    def __init__(
        self,
        instrument_name: str = "Unknown",
        wavelength_nm: float = 488.0,
        fit_method: str = "power"  # 'power', 'polynomial', 'interpolate'
    ):
        """
        Initialize calibration curve builder.
        
        Args:
            instrument_name: Name/ID of the flow cytometer
            wavelength_nm: Laser wavelength used
            fit_method: Method for fitting calibration curve
                       'power': FSC = a * d^b (physics-based)
                       'polynomial': Polynomial fit
                       'interpolate': Direct interpolation
        """
        self.instrument_name = instrument_name
        self.wavelength_nm = wavelength_nm
        self.fit_method = fit_method
        
        self.bead_standards: Dict[float, BeadStandard] = {}
        # Calibration functions can be interp1d or custom callables (lambdas)
        self.calibration_function: Optional[Callable[[Any], Any]] = None
        self.inverse_function: Optional[Callable[[Any], Any]] = None
        self.fit_params: Optional[Dict[str, Any]] = None
        self.is_fitted = False
        
        self._min_diameter: Optional[float] = None
        self._max_diameter: Optional[float] = None
        self._min_fsc: Optional[float] = None
        self._max_fsc: Optional[float] = None
        
        logger.info(
            f"✓ BeadCalibrationCurve initialized: {instrument_name}, "
            f"λ={wavelength_nm}nm, method={fit_method}"
        )
    
    def add_bead_standard(
        self,
        diameter_nm: float,
        fsc_values: np.ndarray,
        diameter_cv: float = 5.0,
        refractive_index: float = 1.59
    ) -> BeadStandard:
        """
        Add a measured bead standard to the calibration set.
        
        Args:
            diameter_nm: Nominal bead diameter in nanometers
            fsc_values: Array of measured FSC values for this bead
            diameter_cv: Coefficient of variation of bead size (%)
            refractive_index: RI of bead material
            
        Returns:
            BeadStandard object with calculated statistics
        """
        fsc_values = np.asarray(fsc_values)
        fsc_values = fsc_values[fsc_values > 0]  # Remove non-positive
        
        if len(fsc_values) < 10:
            logger.warning(f"⚠️ Only {len(fsc_values)} events for {diameter_nm}nm bead")
        
        standard = BeadStandard(
            diameter_nm=diameter_nm,
            diameter_cv=diameter_cv,
            fsc_values=fsc_values,
            refractive_index=refractive_index
        )
        
        self.bead_standards[diameter_nm] = standard
        self.is_fitted = False  # Need to refit
        
        logger.info(
            f"✓ Added {diameter_nm}nm bead standard: "
            f"n={standard.n_events}, FSC mean={standard.fsc_mean:.1f} ± {standard.fsc_std:.1f}"
        )
        
        return standard
    
    def add_bead_from_fcs(
        self,
        diameter_nm: float,
        fcs_file_path: str,
        fsc_channel: str = "VFSC-H",
        gate_percentile: Tuple[float, float] = (5, 95)
    ) -> BeadStandard:
        """
        Add bead standard by parsing an FCS file.
        
        Args:
            diameter_nm: Known bead diameter
            fcs_file_path: Path to FCS file containing bead measurement
            fsc_channel: Name of forward scatter channel
            gate_percentile: Percentile range for gating (removes outliers)
            
        Returns:
            BeadStandard with extracted FSC values
        """
        from ..parsers.fcs_parser import FCSParser
        
        parser = FCSParser(Path(fcs_file_path))
        df = parser.parse()
        
        if fsc_channel not in df.columns:
            raise ValueError(f"Channel {fsc_channel} not found in FCS file")
        
        # Convert to numpy array to ensure compatibility with numpy functions
        fsc_values = np.asarray(df[fsc_channel].values, dtype=np.float64)
        
        # Gate to remove debris and aggregates
        lower = float(np.percentile(fsc_values, gate_percentile[0]))
        upper = float(np.percentile(fsc_values, gate_percentile[1]))
        fsc_gated = fsc_values[(fsc_values >= lower) & (fsc_values <= upper)]
        
        return self.add_bead_standard(diameter_nm, fsc_gated)
    
    def fit(self) -> Dict[str, Any]:
        """
        Fit calibration curve to the bead standards.
        
        Returns:
            Dictionary with fit parameters and quality metrics
        """
        if len(self.bead_standards) < 2:
            raise ValueError("Need at least 2 bead standards for calibration")
        
        # Extract calibration points
        diameters = []
        fsc_means = []
        fsc_stds = []
        
        for d in sorted(self.bead_standards.keys()):
            standard = self.bead_standards[d]
            diameters.append(d)
            fsc_means.append(standard.fsc_mean)
            fsc_stds.append(standard.fsc_std)
        
        diameters = np.array(diameters)
        fsc_means = np.array(fsc_means)
        fsc_stds = np.array(fsc_stds)
        
        self._min_diameter = diameters.min()
        self._max_diameter = diameters.max()
        self._min_fsc = fsc_means.min()
        self._max_fsc = fsc_means.max()
        
        if self.fit_method == "power":
            # Physics-based power law: FSC ∝ d^b (Mie theory predicts b≈2-6)
            def power_law(d, a, b):
                return a * np.power(d, b)
            
            popt, pcov = curve_fit(
                power_law, 
                diameters, 
                fsc_means,
                p0=[1e-6, 4.0],  # Initial guess
                sigma=fsc_stds if np.all(fsc_stds > 0) else None,
                maxfev=10000
            )
            
            self.fit_params = {'a': float(popt[0]), 'b': float(popt[1])}
            
            # Create forward function: diameter -> FSC
            a_val, b_val = float(popt[0]), float(popt[1])
            self.calibration_function = lambda d, a=a_val, b=b_val: a * np.power(d, b)
            
            # Create inverse function: FSC -> diameter
            # d = (FSC/a)^(1/b)
            self.inverse_function = lambda fsc, a=a_val, b=b_val: np.power(fsc / a, 1.0 / b)
            
            # Calculate R²
            predicted = power_law(diameters, *popt)
            ss_res = np.sum((fsc_means - predicted) ** 2)
            ss_tot = np.sum((fsc_means - np.mean(fsc_means)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)
            
            self.fit_params['r_squared'] = r_squared
            
            logger.info(
                f"✓ Power law fit: FSC = {popt[0]:.2e} × d^{popt[1]:.2f}, R²={r_squared:.4f}"
            )
            
        elif self.fit_method == "polynomial":
            # Polynomial fit in log-log space
            log_d = np.log10(diameters)
            log_fsc = np.log10(fsc_means)
            
            coeffs = np.polyfit(log_d, log_fsc, deg=2)
            self.fit_params = {'coeffs': coeffs.tolist()}
            
            # Forward: log(FSC) = c0*log(d)² + c1*log(d) + c2
            coeffs_local = coeffs  # Capture for closure
            self.calibration_function = lambda d, c=coeffs_local: np.power(
                10, np.polyval(c, np.log10(d))
            )
            
            # Inverse requires numerical solution (use interpolation)
            # Build dense lookup table
            min_d = self._min_diameter if self._min_diameter is not None else 50.0
            max_d = self._max_diameter if self._max_diameter is not None else 1000.0
            d_fine = np.linspace(min_d * 0.5, max_d * 1.5, 1000)
            fsc_fine = self.calibration_function(d_fine)
            self.inverse_function = interp1d(
                fsc_fine, d_fine, 
                kind='linear', 
                bounds_error=False,
                fill_value=(d_fine[0], d_fine[-1])  # type: ignore[arg-type]
            )
            
        else:  # interpolate
            # Direct interpolation (most flexible but may not extrapolate well)
            self.calibration_function = interp1d(
                diameters, fsc_means,
                kind='cubic' if len(diameters) >= 4 else 'linear',
                bounds_error=False,
                fill_value='extrapolate'  # type: ignore[arg-type]
            )
            
            self.inverse_function = interp1d(
                fsc_means, diameters,
                kind='cubic' if len(diameters) >= 4 else 'linear',
                bounds_error=False,
                fill_value='extrapolate'  # type: ignore[arg-type]
            )
            
            self.fit_params = {'method': 'interpolation', 'n_points': len(diameters)}
        
        self.is_fitted = True
        
        return {
            'method': self.fit_method,
            'parameters': self.fit_params,
            'calibration_range_nm': (self._min_diameter, self._max_diameter),
            'fsc_range': (self._min_fsc, self._max_fsc),
            'n_standards': len(self.bead_standards)
        }
    
    def diameter_from_fsc(self, fsc_values: np.ndarray) -> np.ndarray:
        """
        Convert FSC values to diameters using calibration.
        
        Args:
            fsc_values: Array of FSC intensity values
            
        Returns:
            Array of calculated diameters in nanometers
        """
        if not self.is_fitted:
            raise RuntimeError("Calibration not fitted. Call fit() first.")
        
        if self.inverse_function is None:
            raise RuntimeError("Inverse function not initialized. Call fit() first.")
        
        fsc_values = np.asarray(fsc_values)
        return self.inverse_function(fsc_values)
    
    def calculate_sizes(
        self,
        fsc_values: np.ndarray,
        filter_range: bool = True
    ) -> CalibrationResult:
        """
        Calculate full size distribution from FSC values.
        
        Args:
            fsc_values: Array of FSC values from unknown sample
            filter_range: If True, mark out-of-range values
            
        Returns:
            CalibrationResult with full statistics
        """
        if not self.is_fitted:
            raise RuntimeError("Calibration not fitted. Call fit() first.")
        
        fsc_values = np.asarray(fsc_values, dtype=np.float64)
        fsc_positive = fsc_values[fsc_values > 0]
        
        # Calculate diameters
        diameters = self.diameter_from_fsc(fsc_positive)
        
        # Get calibration bounds with defaults
        min_d = self._min_diameter if self._min_diameter is not None else 50.0
        max_d = self._max_diameter if self._max_diameter is not None else 1000.0
        
        # Determine valid range (within calibration bounds)
        if filter_range:
            valid_mask = (
                (diameters >= min_d * 0.5) & 
                (diameters <= max_d * 1.5)
            )
            valid_fraction = np.sum(valid_mask) / len(diameters)
        else:
            valid_mask = np.ones(len(diameters), dtype=bool)
            valid_fraction = 1.0
        
        diameters_valid = diameters[valid_mask]
        
        # Calculate statistics
        d10 = float(np.percentile(diameters_valid, 10))
        d50 = float(np.percentile(diameters_valid, 50))
        d90 = float(np.percentile(diameters_valid, 90))
        mean = float(np.mean(diameters_valid))
        std = float(np.std(diameters_valid))
        
        # Calculate mode using KDE
        from .statistics_utils import calculate_mode_kde
        mode_result = calculate_mode_kde(diameters_valid)
        # Handle both float return and ModeResult (from scipy.stats)
        mode = float(mode_result) if not hasattr(mode_result, 'mode') else float(mode_result.mode)  # type: ignore[union-attr]
        
        return CalibrationResult(
            diameters=diameters,
            d10=d10,
            d50=d50,
            d90=d90,
            mean=mean,
            std=std,
            mode=mode,
            valid_fraction=valid_fraction,
            n_events=len(diameters),
            calibration_range=(min_d, max_d)
        )
    
    def save(self, filepath: str) -> None:
        """Save calibration to JSON file."""
        # Get values with defaults for serialization
        min_d = self._min_diameter if self._min_diameter is not None else 0.0
        max_d = self._max_diameter if self._max_diameter is not None else 0.0
        min_fsc = self._min_fsc if self._min_fsc is not None else 0.0
        max_fsc = self._max_fsc if self._max_fsc is not None else 0.0
        
        data = {
            'instrument_name': self.instrument_name,
            'wavelength_nm': self.wavelength_nm,
            'fit_method': self.fit_method,
            'fit_params': {k: float(v) if isinstance(v, (np.floating, np.integer)) else v 
                          for k, v in self.fit_params.items()} if self.fit_params else None,
            'calibration_range_nm': (float(min_d), float(max_d)),
            'fsc_range': (float(min_fsc), float(max_fsc)),
            'bead_standards': {
                str(d): {
                    'diameter_nm': float(s.diameter_nm),
                    'diameter_cv': float(s.diameter_cv),
                    'fsc_mean': float(s.fsc_mean) if s.fsc_mean is not None else 0.0,
                    'fsc_std': float(s.fsc_std) if s.fsc_std is not None else 0.0,
                    'n_events': int(s.n_events),
                    'refractive_index': float(s.refractive_index)
                }
                for d, s in self.bead_standards.items()
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"✓ Calibration saved to {filepath}")
    
    @classmethod
    def load(cls, filepath: str) -> 'BeadCalibrationCurve':
        """Load calibration from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        calib = cls(
            instrument_name=data['instrument_name'],
            wavelength_nm=data['wavelength_nm'],
            fit_method=data['fit_method']
        )
        
        # Reconstruct bead standards (without raw data)
        for d_str, std_data in data['bead_standards'].items():
            d = float(d_str)
            standard = BeadStandard(
                diameter_nm=std_data['diameter_nm'],
                diameter_cv=std_data['diameter_cv'],
                fsc_mean=std_data['fsc_mean'],
                fsc_std=std_data['fsc_std'],
                n_events=std_data['n_events'],
                refractive_index=std_data['refractive_index']
            )
            calib.bead_standards[d] = standard
        
        # Restore fit parameters and rebuild functions
        calib.fit_params = data['fit_params']
        calib._min_diameter, calib._max_diameter = data['calibration_range_nm']
        calib._min_fsc, calib._max_fsc = data['fsc_range']
        
        # Rebuild calibration function
        if calib.fit_method == "power" and calib.fit_params:
            a = float(calib.fit_params['a'])
            b = float(calib.fit_params['b'])
            calib.calibration_function = lambda d, a=a, b=b: a * np.power(d, b)
            calib.inverse_function = lambda fsc, a=a, b=b: np.power(fsc / a, 1.0 / b)
        
        calib.is_fitted = True
        logger.info(f"✓ Calibration loaded from {filepath}")
        
        return calib


def create_synthetic_calibration(
    instrument_name: str = "NanoFACS_Simulated",
    wavelength_nm: float = 488.0,
    bead_sizes: List[float] = [100, 200, 500],
    n_particle: float = 1.59,  # Polystyrene
    n_medium: float = 1.33,
    noise_cv: float = 0.15
) -> BeadCalibrationCurve:
    """
    Create a synthetic calibration using Mie theory predictions.
    
    Useful for testing when real bead data is not available.
    Adds realistic measurement noise to Mie predictions.
    
    Args:
        instrument_name: Name for the calibration
        wavelength_nm: Laser wavelength
        bead_sizes: List of bead diameters to simulate
        n_particle: Refractive index of beads
        n_medium: Refractive index of medium
        noise_cv: Coefficient of variation for simulated noise
        
    Returns:
        Fitted BeadCalibrationCurve
    """
    from .mie_scatter import MieScatterCalculator
    
    # Create Mie calculator for polystyrene beads
    calc = MieScatterCalculator(
        wavelength_nm=wavelength_nm,
        n_particle=n_particle,
        n_medium=n_medium
    )
    
    calib = BeadCalibrationCurve(
        instrument_name=instrument_name,
        wavelength_nm=wavelength_nm,
        fit_method="power"
    )
    
    # Simulate bead measurements
    for diameter in bead_sizes:
        # Calculate theoretical FSC
        result = calc.calculate_scattering_efficiency(diameter, validate=False)
        theoretical_fsc = result.forward_scatter
        
        # Add instrument scaling factor (arbitrary units)
        # This simulates the real-world case where FSC values are in
        # instrument-specific units, not absolute physical units
        instrument_scale = 1e4  # Typical scale factor
        scaled_fsc = theoretical_fsc * instrument_scale
        
        # Simulate N events with noise
        n_events = 5000
        noise = np.random.normal(1.0, noise_cv, n_events)
        simulated_fsc = scaled_fsc * noise
        simulated_fsc = simulated_fsc[simulated_fsc > 0]  # Remove negatives
        
        calib.add_bead_standard(diameter, simulated_fsc)
    
    # Fit the calibration
    calib.fit()
    
    logger.info(f"✓ Created synthetic calibration with {len(bead_sizes)} bead sizes")
    
    return calib
