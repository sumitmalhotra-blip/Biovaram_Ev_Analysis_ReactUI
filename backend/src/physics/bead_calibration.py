"""
Polystyrene Bead Calibration Module
====================================

Purpose: Provide absolute particle sizing through instrument calibration
         using polystyrene bead standards of known sizes.

Calibration Standards (Beckman Coulter nanoViS D03231):
- Polystyrene latex beads: n = 1.591 at 590nm (NIST-traceable TEM sizing)
- Low mix:  44nm, 80nm, 105nm, 144nm
- High mix: 144nm, 300nm, 600nm, 1000nm
- Unique sizes: 40, 80, 108, 142, 304, 600, 1020 nm

Theory:
-------
1. Run known-size polystyrene beads through the instrument
2. Record their SSC (side scatter) intensities
3. Compute Mie theory predictions for each bead (RI=1.591, known diameter)
4. Fit transfer function: measured_SSC → Mie_scatter (accounts for instrument response)
5. For unknown EVs: measured_SSC → transfer_function → calibrated_scatter → inverse_Mie(RI=1.40) → diameter

This bridges the gap between arbitrary instrument scatter units and
physical Mie scatter values, enabling accurate absolute sizing.

Author: CRMIT Backend Team
Date: January 20, 2026
Updated: February 10, 2026 - Added bead datasheet support, peak detection
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from scipy.interpolate import interp1d
from scipy.optimize import curve_fit
from scipy.signal import find_peaks
from scipy.ndimage import gaussian_filter1d
from loguru import logger
import json
from pathlib import Path
import datetime


# ============================================================================
# Bead Datasheet Loader
# ============================================================================

@dataclass
class BeadDatasheetEntry:
    """Single bead population from a manufacturer datasheet."""
    label: str
    diameter_nm: float
    spec_min_um: float
    spec_max_um: float
    cv_pct: float
    concentration_particles_per_ml: float
    subcomponent: str  # e.g., "nanoViS_Low" or "nanoViS_High"


@dataclass
class BeadDatasheet:
    """
    Parsed bead calibration datasheet from manufacturer.
    
    Loaded from JSON files in backend/config/bead_standards/
    """
    kit_part_number: str
    product_name: str
    lot_number: str
    manufacturer: str
    refractive_index: float
    ri_wavelength_nm: float
    material: str
    nist_traceable: bool
    expiration_date: str
    unique_diameters_nm: List[float]
    beads: List[BeadDatasheetEntry]
    
    @classmethod
    def load(cls, filepath: Union[str, Path]) -> 'BeadDatasheet':
        """Load bead datasheet from JSON config file."""
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Bead datasheet not found: {filepath}")
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        beads: List[BeadDatasheetEntry] = []
        for sub_name, sub_data in data.get('subcomponents', {}).items():
            for bead in sub_data.get('beads', []):
                beads.append(BeadDatasheetEntry(
                    label=bead['label'],
                    diameter_nm=bead['diameter_nm'],
                    spec_min_um=bead['spec_min_um'],
                    spec_max_um=bead['spec_max_um'],
                    cv_pct=bead['cv_pct'],
                    concentration_particles_per_ml=bead['concentration_particles_per_ml'],
                    subcomponent=sub_name,
                ))
        
        return cls(
            kit_part_number=data['kit_part_number'],
            product_name=data['product_name'],
            lot_number=data['lot_number'],
            manufacturer=data['manufacturer'],
            refractive_index=data['refractive_index'],
            ri_wavelength_nm=data.get('ri_measurement_wavelength_nm', 590),
            material=data.get('material', 'polystyrene_latex'),
            nist_traceable=data.get('nist_traceable', False),
            expiration_date=data.get('expiration_date', ''),
            unique_diameters_nm=data.get('unique_bead_diameters_nm', []),
            beads=beads,
        )
    
    def get_unique_diameters(self) -> List[float]:
        """Get sorted unique bead diameters in nm."""
        if self.unique_diameters_nm:
            return sorted(self.unique_diameters_nm)
        # Deduplicate from bead entries
        return sorted(set(b.diameter_nm for b in self.beads))
    
    def get_diameter_cv_map(self) -> Dict[float, float]:
        """Map of diameter_nm → CV% (uses first occurrence for duplicates)."""
        result: Dict[float, float] = {}
        for b in self.beads:
            if b.diameter_nm not in result:
                result[b.diameter_nm] = b.cv_pct
        return result


def list_available_bead_standards(config_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all available bead standard datasheets.
    
    Returns list of dicts with kit info (part number, name, lot, etc.)
    """
    if config_dir is None:
        config_dir = str(Path(__file__).parent.parent.parent / "config" / "bead_standards")
    
    config_path = Path(config_dir)
    if not config_path.exists():
        return []
    
    standards = []
    for json_file in sorted(config_path.glob("*.json")):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            standards.append({
                'file': str(json_file),
                'filename': json_file.name,
                'kit_part_number': data.get('kit_part_number', ''),
                'product_name': data.get('product_name', ''),
                'lot_number': data.get('lot_number', ''),
                'manufacturer': data.get('manufacturer', ''),
                'refractive_index': data.get('refractive_index', 0),
                'expiration_date': data.get('expiration_date', ''),
                'n_bead_sizes': len(data.get('unique_bead_diameters_nm', [])),
                'bead_sizes_nm': data.get('unique_bead_diameters_nm', []),
            })
        except Exception as e:
            logger.warning(f"Failed to read bead standard {json_file}: {e}")
    
    return standards


# ============================================================================
# Peak Detection for Bead Populations
# ============================================================================

def detect_bead_peaks(
    scatter_values: np.ndarray,
    n_expected_peaks: int,
    min_peak_distance_log: float = 0.15,
    kde_bandwidth: float = 0.05,
    n_kde_points: int = 2000,
) -> List[Dict[str, Any]]:
    """
    Automatically detect bead population peaks from a mixed-bead scatter histogram.
    
    Uses KDE (Kernel Density Estimation) in log-space followed by peak finding.
    
    Args:
        scatter_values: Raw scatter intensity values (SSC or FSC) from bead FCS file
        n_expected_peaks: Number of bead populations expected
        min_peak_distance_log: Minimum distance between peaks in log10 space
        kde_bandwidth: KDE bandwidth in log10 space (smaller = more peaks)
        n_kde_points: Number of points for KDE evaluation
    
    Returns:
        List of dicts with peak info: {
            'peak_scatter': float,        # Scatter value at peak center
            'peak_log_scatter': float,     # log10(scatter) at peak center
            'peak_height': float,          # KDE density at peak
            'peak_region_mask': np.ndarray, # Boolean mask of events in this peak
            'peak_events': int,            # Number of events in peak region
            'peak_scatter_mean': float,    # Mean scatter of peak region
            'peak_scatter_std': float,     # Std scatter of peak region
        }
    """
    # Work in log space for better peak separation
    positive_scatter = scatter_values[scatter_values > 0]
    if len(positive_scatter) < 100:
        raise ValueError(f"Too few positive scatter events ({len(positive_scatter)}) for peak detection")
    
    log_scatter = np.log10(positive_scatter)
    
    # Build KDE using histogram + Gaussian smoothing (faster than scipy.stats.gaussian_kde)
    log_min, log_max = np.percentile(log_scatter, [0.5, 99.5])
    log_range = log_max - log_min
    log_min -= log_range * 0.05
    log_max += log_range * 0.05
    
    kde_x = np.linspace(log_min, log_max, n_kde_points)
    bin_width = (log_max - log_min) / n_kde_points
    
    # Histogram-based KDE
    hist_counts, hist_edges = np.histogram(log_scatter, bins=n_kde_points, range=(log_min, log_max))
    kde_y = hist_counts.astype(float)
    
    # Smooth with Gaussian kernel
    sigma_bins = kde_bandwidth / bin_width
    sigma_bins = max(sigma_bins, 1.0)  # Minimum 1 bin smoothing
    kde_y = gaussian_filter1d(kde_y, sigma=sigma_bins)
    
    # Normalize
    kde_y = kde_y / (np.sum(kde_y) * bin_width) if np.sum(kde_y) > 0 else kde_y
    
    # Find peaks
    min_distance_bins = max(int(min_peak_distance_log / bin_width), 5)
    peak_indices, peak_props = find_peaks(
        kde_y,
        distance=min_distance_bins,
        prominence=np.max(kde_y) * 0.01,  # At least 1% of max height
        height=np.max(kde_y) * 0.005,     # Minimum absolute height
    )
    
    if len(peak_indices) == 0:
        logger.warning("No peaks found, trying with relaxed parameters")
        peak_indices, peak_props = find_peaks(
            kde_y,
            distance=max(min_distance_bins // 2, 3),
            prominence=np.max(kde_y) * 0.005,
        )
    
    # Sort peaks by height (most prominent first)
    if len(peak_indices) > 0:
        peak_heights = kde_y[peak_indices]
        sorted_idx = np.argsort(-peak_heights)
        peak_indices = peak_indices[sorted_idx]
    
    # Take top N peaks
    if len(peak_indices) > n_expected_peaks:
        # Keep the n_expected_peaks tallest peaks, then sort by position (scatter value)
        top_indices = peak_indices[:n_expected_peaks]
        top_indices = np.sort(top_indices)  # Sort by scatter (left to right)
        peak_indices = top_indices
    
    logger.info(f"🔍 Peak detection: found {len(peak_indices)} peaks (expected {n_expected_peaks})")
    
    # Extract peak information
    peaks = []
    for i, pi in enumerate(peak_indices):
        peak_log = kde_x[pi] if pi < len(kde_x) else kde_x[-1]
        peak_scatter = 10**peak_log
        peak_height = kde_y[pi]
        
        # Define peak region: events within ±0.5 * min_peak_distance of peak center
        half_width = min_peak_distance_log * 0.4
        region_mask = (log_scatter >= peak_log - half_width) & (log_scatter <= peak_log + half_width)
        region_events = positive_scatter[region_mask]
        
        peaks.append({
            'peak_scatter': float(peak_scatter),
            'peak_log_scatter': float(peak_log),
            'peak_height': float(peak_height),
            'peak_events': int(len(region_events)),
            'peak_scatter_mean': float(np.mean(region_events)) if len(region_events) > 0 else float(peak_scatter),
            'peak_scatter_std': float(np.std(region_events)) if len(region_events) > 0 else 0.0,
        })
        
        logger.info(
            f"   Peak {i+1}: scatter={peak_scatter:.1f} (log={peak_log:.3f}), "
            f"n_events={len(region_events)}, mean={peaks[-1]['peak_scatter_mean']:.1f}"
        )
    
    return peaks


def match_peaks_to_beads(
    detected_peaks: List[Dict[str, Any]],
    known_diameters_nm: List[float],
) -> List[Dict[str, Any]]:
    """
    Match detected scatter peaks to known bead diameters.
    
    Assumption: peaks are ordered by scatter intensity, which corresponds
    to ordered bead diameters (larger beads = more scatter, monotonic in 
    polystyrene bead regime).
    
    Args:
        detected_peaks: Output from detect_bead_peaks, sorted by scatter
        known_diameters_nm: Known bead diameters, sorted ascending
    
    Returns:
        List of matched pairs: each dict has peak info + 'matched_diameter_nm'
    """
    if len(detected_peaks) != len(known_diameters_nm):
        logger.warning(
            f"Peak count ({len(detected_peaks)}) != bead count ({len(known_diameters_nm)}). "
            f"Matching by order (smallest scatter → smallest bead)."
        )
    
    # Sort peaks by scatter value (ascending)
    sorted_peaks = sorted(detected_peaks, key=lambda p: p['peak_scatter'])
    sorted_diameters = sorted(known_diameters_nm)
    
    # Match 1:1 by order
    n_match = min(len(sorted_peaks), len(sorted_diameters))
    matched = []
    for i in range(n_match):
        entry = dict(sorted_peaks[i])
        entry['matched_diameter_nm'] = sorted_diameters[i]
        matched.append(entry)
        logger.info(
            f"   Matched: scatter={entry['peak_scatter_mean']:.1f} → "
            f"diameter={sorted_diameters[i]:.0f} nm"
        )
    
    return matched


# ============================================================================
# Bead Standard & Calibration Result Dataclasses
# ============================================================================

@dataclass
class BeadStandard:
    """
    Represents a polystyrene bead calibration standard.
    
    Attributes:
        diameter_nm: Nominal diameter in nanometers (TEM-measured)
        diameter_cv: Coefficient of variation (%) from manufacturer
        fsc_values: Measured FSC/SSC values for this bead
        fsc_mean: Mean scatter value
        fsc_std: Standard deviation of scatter
        n_events: Number of events measured
        refractive_index: RI of bead material (1.591 for polystyrene at 590nm)
    """
    diameter_nm: float
    diameter_cv: float = 5.0  # Typical CV for commercial beads
    fsc_values: Optional[np.ndarray] = None
    fsc_mean: Optional[float] = None
    fsc_std: Optional[float] = None
    n_events: int = 0
    refractive_index: float = 1.591  # Polystyrene at 590nm (Beckman nanoViS)
    
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
    
    # Standard polystyrene bead sizes from nanoViS D03231 datasheet (nm)
    STANDARD_BEAD_SIZES = [40, 80, 108, 142, 304, 600, 1020]
    
    def __init__(
        self,
        instrument_name: str = "Unknown",
        wavelength_nm: float = 488.0,
        fit_method: str = "power",  # 'power', 'polynomial', 'interpolate'
        bead_datasheet: Optional[BeadDatasheet] = None,
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
            bead_datasheet: Optional BeadDatasheet with manufacturer specs
        """
        self.instrument_name = instrument_name
        self.wavelength_nm = wavelength_nm
        self.fit_method = fit_method
        self.bead_datasheet = bead_datasheet
        
        # Update standard sizes from datasheet if provided
        if bead_datasheet:
            self.STANDARD_BEAD_SIZES = bead_datasheet.get_unique_diameters()
        
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
        refractive_index: float = 1.591
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
            'version': '2.0',
            'created_at': datetime.datetime.now().isoformat(),
            'instrument_name': self.instrument_name,
            'wavelength_nm': self.wavelength_nm,
            'fit_method': self.fit_method,
            'fit_params': {k: float(v) if isinstance(v, (np.floating, np.integer)) else v 
                          for k, v in self.fit_params.items()} if self.fit_params else None,
            'calibration_range_nm': (float(min_d), float(max_d)),
            'fsc_range': (float(min_fsc), float(max_fsc)),
            'bead_datasheet_info': {
                'kit_part_number': self.bead_datasheet.kit_part_number if self.bead_datasheet else None,
                'lot_number': self.bead_datasheet.lot_number if self.bead_datasheet else None,
                'refractive_index': self.bead_datasheet.refractive_index if self.bead_datasheet else 1.591,
                'material': self.bead_datasheet.material if self.bead_datasheet else 'polystyrene',
                'nist_traceable': self.bead_datasheet.nist_traceable if self.bead_datasheet else False,
            },
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
    n_particle: float = 1.591,  # Polystyrene (nanoViS datasheet)
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
        instrument_scale = 1e4
        scaled_fsc = theoretical_fsc * instrument_scale
        
        # Simulate N events with noise
        n_events = 5000
        noise = np.random.normal(1.0, noise_cv, n_events)
        simulated_fsc = scaled_fsc * noise
        simulated_fsc = simulated_fsc[simulated_fsc > 0]
        
        calib.add_bead_standard(diameter, simulated_fsc)
    
    calib.fit()
    logger.info(f"✓ Created synthetic calibration with {len(bead_sizes)} bead sizes")
    
    return calib


# ============================================================================
# Full Calibration Pipeline: FCS File + Datasheet → Calibration Curve
# ============================================================================

def calibrate_from_bead_fcs(
    fcs_file_path: str,
    datasheet_path: str,
    scatter_channel: str = "VSSC1-H",
    instrument_name: str = "CytoFLEX_S",
    wavelength_nm: float = 405.0,
    fit_method: str = "power",
    subcomponent: Optional[str] = None,
) -> Tuple[BeadCalibrationCurve, Dict[str, Any]]:
    """
    Full automated calibration pipeline:
    1. Load bead datasheet
    2. Parse bead FCS file
    3. Auto-detect bead peaks
    4. Match peaks to known diameters
    5. Fit calibration curve
    
    Args:
        fcs_file_path: Path to FCS file from bead measurement run
        datasheet_path: Path to bead datasheet JSON
        scatter_channel: SSC channel to use for calibration
        instrument_name: Name of the instrument
        wavelength_nm: Laser wavelength for the scatter channel
        fit_method: Fitting method ('power', 'polynomial', 'interpolate')
        subcomponent: If specified, only use beads from this subcomponent
                     (e.g., 'nanoViS_Low' or 'nanoViS_High')
    
    Returns:
        Tuple of (fitted BeadCalibrationCurve, diagnostics dict)
    """
    from ..parsers.fcs_parser import FCSParser
    
    logger.info(f"🔬 Starting bead calibration pipeline")
    logger.info(f"   FCS: {fcs_file_path}")
    logger.info(f"   Datasheet: {datasheet_path}")
    logger.info(f"   Channel: {scatter_channel}")
    
    # Step 1: Load datasheet
    datasheet = BeadDatasheet.load(datasheet_path)
    logger.info(f"   Kit: {datasheet.product_name} (Lot {datasheet.lot_number})")
    
    # Get bead diameters (optionally filtered by subcomponent)
    if subcomponent:
        known_diameters = sorted(set(
            b.diameter_nm for b in datasheet.beads if b.subcomponent == subcomponent
        ))
        logger.info(f"   Using subcomponent '{subcomponent}': {known_diameters}")
    else:
        known_diameters = datasheet.get_unique_diameters()
        logger.info(f"   Using all unique diameters: {known_diameters}")
    
    cv_map = datasheet.get_diameter_cv_map()
    
    # Step 2: Parse bead FCS file
    parser = FCSParser(Path(fcs_file_path))
    parsed_data = parser.parse()
    
    if scatter_channel not in parsed_data.columns:
        available = list(parsed_data.columns)
        raise ValueError(
            f"Channel '{scatter_channel}' not found. "
            f"Available: {available}"
        )
    
    scatter_values = np.asarray(parsed_data[scatter_channel].values, dtype=np.float64)
    scatter_values = scatter_values[scatter_values > 0]
    logger.info(f"   Loaded {len(scatter_values)} positive events from {scatter_channel}")
    
    # Step 3: Auto-detect peaks
    detected_peaks = detect_bead_peaks(
        scatter_values,
        n_expected_peaks=len(known_diameters),
    )
    
    # Step 4: Match peaks to bead diameters
    matched = match_peaks_to_beads(detected_peaks, known_diameters)
    
    # Step 5: Build calibration curve
    calib = BeadCalibrationCurve(
        instrument_name=instrument_name,
        wavelength_nm=wavelength_nm,
        fit_method=fit_method,
        bead_datasheet=datasheet,
    )
    
    for m in matched:
        diameter = m['matched_diameter_nm']
        scatter_mean = m['peak_scatter_mean']
        scatter_std = m['peak_scatter_std']
        n_events = m['peak_events']
        cv = cv_map.get(diameter, 5.0)
        
        # Create synthetic event array from peak stats (we use mean/std for fitting)
        synthetic_events = np.random.normal(scatter_mean, scatter_std, max(n_events, 100))
        synthetic_events = synthetic_events[synthetic_events > 0]
        
        calib.add_bead_standard(
            diameter_nm=diameter,
            fsc_values=synthetic_events,
            diameter_cv=cv,
            refractive_index=datasheet.refractive_index,
        )
    
    # Fit
    fit_result = calib.fit()
    
    # Build diagnostics
    diagnostics = {
        'datasheet': {
            'kit': datasheet.kit_part_number,
            'lot': datasheet.lot_number,
            'ri': datasheet.refractive_index,
            'material': datasheet.material,
            'nist_traceable': datasheet.nist_traceable,
        },
        'channel': scatter_channel,
        'wavelength_nm': wavelength_nm,
        'n_peaks_detected': len(detected_peaks),
        'n_beads_matched': len(matched),
        'n_beads_expected': len(known_diameters),
        'fit': fit_result,
        'bead_points': [
            {
                'diameter_nm': m['matched_diameter_nm'],
                'scatter_mean': m['peak_scatter_mean'],
                'scatter_std': m['peak_scatter_std'],
                'n_events': m['peak_events'],
            }
            for m in matched
        ],
    }
    
    logger.info(f"✅ Calibration complete: {len(matched)} beads, R²={fit_result.get('parameters', {}).get('r_squared', 'N/A')}")
    
    return calib, diagnostics


# ============================================================================
# Active Calibration Management
# ============================================================================

CALIBRATION_DIR = Path(__file__).parent.parent.parent / "config" / "calibration"


def get_active_calibration() -> Optional[BeadCalibrationCurve]:
    """
    Load the currently active bead calibration curve.
    
    Looks for 'active_calibration.json' in config/calibration/.
    Returns None if no calibration exists.
    """
    active_path = CALIBRATION_DIR / "active_calibration.json"
    if not active_path.exists():
        return None
    
    try:
        calib = BeadCalibrationCurve.load(str(active_path))
        logger.info(f"✓ Active calibration loaded: {calib.instrument_name}")
        return calib
    except Exception as e:
        logger.warning(f"⚠️ Failed to load active calibration: {e}")
        return None


def save_as_active_calibration(calib: BeadCalibrationCurve) -> str:
    """
    Save a calibration curve as the active calibration.
    
    Also archives the previous active calibration with a timestamp.
    
    Returns:
        Path to the saved active calibration file
    """
    CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)
    
    active_path = CALIBRATION_DIR / "active_calibration.json"
    
    # Archive existing if present
    if active_path.exists():
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = CALIBRATION_DIR / f"calibration_archived_{timestamp}.json"
        active_path.rename(archive_path)
        logger.info(f"📦 Archived previous calibration to {archive_path.name}")
    
    calib.save(str(active_path))
    logger.info(f"✅ Active calibration saved: {active_path}")
    
    return str(active_path)


def get_calibration_status() -> Dict[str, Any]:
    """
    Get the status of the current calibration for display in the UI.
    
    Returns dict with calibration info or 'not_calibrated' status.
    """
    active_path = CALIBRATION_DIR / "active_calibration.json"
    
    if not active_path.exists():
        return {
            'status': 'not_calibrated',
            'message': 'No bead calibration has been performed',
            'calibrated': False,
        }
    
    try:
        with open(active_path, 'r') as f:
            data = json.load(f)
        
        datasheet_info = data.get('bead_datasheet_info', {})
        fit_params = data.get('fit_params', {})
        cal_range = data.get('calibration_range_nm', [0, 0])
        n_beads = len(data.get('bead_standards', {}))
        
        return {
            'status': 'calibrated',
            'calibrated': True,
            'instrument': data.get('instrument_name', 'Unknown'),
            'wavelength_nm': data.get('wavelength_nm', 488),
            'fit_method': data.get('fit_method', 'power'),
            'r_squared': fit_params.get('r_squared', None),
            'n_bead_sizes': n_beads,
            'calibration_range_nm': cal_range,
            'created_at': data.get('created_at', None),
            'bead_kit': datasheet_info.get('kit_part_number', None),
            'bead_lot': datasheet_info.get('lot_number', None),
            'bead_ri': datasheet_info.get('refractive_index', 1.591),
            'nist_traceable': datasheet_info.get('nist_traceable', False),
            'message': f"Calibrated with {n_beads} beads ({cal_range[0]:.0f}-{cal_range[1]:.0f} nm)",
        }
    except Exception as e:
        return {
            'status': 'error',
            'calibrated': False,
            'message': f'Failed to read calibration: {str(e)}',
        }