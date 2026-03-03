"""
Mie Scattering Physics Module
==============================

Purpose: Implement Mie scattering theory for accurate particle size determination
         from flow cytometry light scatter data

References:
- Literature/Mie functions_scattering_Abs-V1.pdf
- Literature/Mie functions_scattering_Abs-V2.pdf
- Literature/FCMPASS_Software-Aids-EVs-Light-Scatter-Stand.pdf

Author: CRMIT Backend Team
Date: November 18, 2025
Status: ✅ PRODUCTION READY - Implemented with miepython

Theory:
-------
Mie scattering describes electromagnetic wave scattering by spherical particles.
The key parameters are:
1. Size parameter: x = πd/λ (dimensionless)
2. Relative refractive index: m = n_particle/n_medium (complex number)
3. Scattering efficiency: Q_sca (calculated from Mie series expansion)
4. Asymmetry parameter: g (-1 to 1, measures forward scatter bias)

Physical Regimes:
- x << 1: Rayleigh scattering (λ⁻⁴ wavelength dependence)
- x ~ 1: Resonance regime (full Mie theory required)
- x >> 1: Geometric optics (ray tracing approximation)

Flow Cytometry Application:
- FSC (Forward Scatter): measures particle size, correlates with Q_sca
- SSC (Side Scatter): measures internal complexity, correlates with Q_back
- Multi-wavelength analysis enables particle characterization
"""

from typing import Tuple, Optional, Dict, List, Any
import numpy as np
from loguru import logger
import miepython
from scipy.optimize import minimize_scalar, OptimizeResult
from dataclasses import dataclass


# ============================================================================
# Polystyrene RI Wavelength Dispersion (Cauchy equation)
# ============================================================================
# Coefficients from Sultanova et al. (2009), "Dispersion Properties of Optical
# Polymers". Valid for 400-800nm range.
# n(λ) = A + B/λ² + C/λ⁴ where λ is in micrometers.
# At 590nm: n = 1.591 (matches nanoViS datasheet)
# At 405nm: n = 1.634 (significant increase!)
CAUCHY_PS_A = 1.5718
CAUCHY_PS_B = 0.00885  # μm²
CAUCHY_PS_C = 0.000213  # μm⁴


def polystyrene_ri_at_wavelength(wavelength_nm: float) -> float:
    """
    Calculate polystyrene refractive index at given wavelength using Cauchy equation.
    
    IMPORTANT: Bead datasheets typically report RI at 590nm (1.591).
    At shorter wavelengths (e.g., 405nm VSSC), the RI is significantly higher (1.634).
    Using the datasheet value at 590nm for a 405nm measurement introduces ~3% error in RI
    and ~35% error in calibration constant k.
    
    Args:
        wavelength_nm: Wavelength in nanometers
        
    Returns:
        Polystyrene refractive index at the specified wavelength
    """
    lambda_um = wavelength_nm / 1000.0
    return CAUCHY_PS_A + CAUCHY_PS_B / lambda_um**2 + CAUCHY_PS_C / lambda_um**4

# Import size configuration for consistent range handling
try:
    from .size_config import DEFAULT_SIZE_CONFIG, SizeRangeConfig
except ImportError:
    # Fallback for direct execution
    from size_config import DEFAULT_SIZE_CONFIG, SizeRangeConfig


@dataclass
class MieScatterResult:
    """
    Results from Mie scattering calculation.
    
    Attributes:
        Q_ext: Extinction efficiency (dimensionless, 0-4 typical)
        Q_sca: Scattering efficiency (dimensionless, 0-4 typical)
        Q_back: Backscatter efficiency (dimensionless)
        g: Asymmetry parameter (-1 to 1, 0=isotropic, 1=full forward)
        forward_scatter: Forward scatter intensity proxy (FSC)
        side_scatter: Side scatter intensity proxy (SSC)
        size_parameter_x: Dimensionless size parameter (πd/λ)
    """
    Q_ext: float
    Q_sca: float
    Q_back: float
    g: float
    forward_scatter: float
    side_scatter: float
    size_parameter_x: float


class MieScatterCalculator:
    """
    Production-quality Mie scattering calculator for flow cytometry applications.
    
    This class implements rigorous Mie theory using the miepython library to
    convert between particle sizes and light scatter intensities. It handles:
    
    1. Forward calculation: diameter → scatter intensity (FSC/SSC)
    2. Inverse calculation: scatter intensity → diameter (key for sizing)
    3. Multi-wavelength analysis: understand wavelength-dependent scatter
    4. Batch processing: efficient calculation for large datasets
    
    Key Features:
    - Scientifically accurate Mie theory implementation
    - Robust numerical optimization for inverse problem
    - Comprehensive input validation and error handling
    - Production-ready logging and diagnostics
    - Type hints and extensive documentation
    
    Example Usage:
        >>> # Initialize for blue laser (488nm), EVs in PBS
        >>> calc = MieScatterCalculator(wavelength_nm=488, n_particle=1.40, n_medium=1.33)
        >>> 
        >>> # Calculate scatter for 80nm particle
        >>> result = calc.calculate_scattering_efficiency(diameter_nm=80)
        >>> print(f"FSC proxy: {result.forward_scatter:.2f}")
        >>> 
        >>> # Inverse: find size from measured FSC
        >>> diameter, success = calc.diameter_from_scatter(fsc_intensity=15000)
        >>> print(f"Estimated size: {diameter:.1f} nm")
    
    Physics Notes:
    - Forward scatter (FSC) primarily depends on Q_sca and asymmetry g
    - Side scatter (SSC) primarily depends on Q_back (backscatter)
    - Smaller particles scatter blue light more than red (Rayleigh regime)
    - At resonance (x~1), scatter can be strongly wavelength-dependent
    """
    
    def __init__(
        self,
        wavelength_nm: float = 488.0,
        n_particle: float = 1.40,
        n_medium: float = 1.33,
        fsc_angle_range: Optional[list[float]] = None,
        ssc_angle_range: Optional[list[float]] = None
    ):
        """
        Initialize Mie calculator for specific optical configuration.
        
        Args:
            wavelength_nm: Laser wavelength in nanometers
                          ZE5 Bio-Rad options: 405 (violet), 488 (blue), 
                          561 (yellow-green), 633 (red)
            n_particle: Refractive index of particles
                       EVs/exosomes: typically 1.37-1.45 (biological membranes)
                       Polystyrene beads: 1.59 (common calibration standard)
                       Silica beads: 1.46 (alternative standard)
            n_medium: Refractive index of medium
                     PBS/water: 1.33
                     Saline: ~1.33
                     Air: 1.00 (for dry measurements)
        
        Raises:
            ValueError: If any input parameter is invalid
        
        Example:
            >>> # Blue laser, EVs in PBS
            >>> calc = MieScatterCalculator(wavelength_nm=488, n_particle=1.40, n_medium=1.33)
            >>> # Violet laser, polystyrene beads
            >>> calc_beads = MieScatterCalculator(wavelength_nm=405, n_particle=1.59, n_medium=1.33)
        """
        # Input validation
        if wavelength_nm <= 0:
            raise ValueError(f"Wavelength must be positive, got {wavelength_nm}")
        if not (1.0 <= n_particle <= 2.0):
            logger.warning(f"⚠️ Unusual particle refractive index: {n_particle}")
        if not (1.0 <= n_medium <= 1.5):
            logger.warning(f"⚠️ Unusual medium refractive index: {n_medium}")
        if n_particle <= n_medium:
            logger.warning(
                f"⚠️ Particle n ({n_particle}) ≤ medium n ({n_medium}). "
                f"This is unusual and may indicate configuration error."
            )
        
        self.wavelength_nm = wavelength_nm
        self.n_particle = n_particle
        self.n_medium = n_medium
        
        # Detector angle ranges (degrees) for angle-resolved scatter calculations
        # Default: ZE5 Bio-Rad typical geometry
        self.fsc_angle_range = fsc_angle_range or [0.5, 15.0]
        self.ssc_angle_range = ssc_angle_range or [15.0, 150.0]
        
        # Refractive index for miepython
        # CORRECTED (Feb 2026): Use ABSOLUTE RI with n_env parameter in efficiencies()
        # Previous code used relative m = n_particle/n_medium with n_env=n_medium,
        # which double-counted the medium RI. See SIZING_ACCURACY_DIAGNOSIS.md.
        self.m_complex = complex(n_particle, 0.0)  # Absolute RI for efficiencies() API
        
        # Keep relative m for backward compatibility logging
        self.m = complex(n_particle / n_medium, 0.0)
        
        # LUT cache for batch operations (initialized on first use)
        # This avoids rebuilding the lookup table on every batch call
        self._lut_cache: Optional[Dict[str, Any]] = None
        self._lut_cache_key: Optional[str] = None
        
        logger.info(
            f"✓ Mie Calculator initialized: λ={wavelength_nm:.1f}nm, "
            f"n_particle={n_particle:.4f}, n_medium={n_medium:.4f}, m={self.m.real:.4f}"
        )
    
    def calculate_scattering_efficiency(
        self,
        diameter_nm: float,
        validate: bool = True
    ) -> MieScatterResult:
        """
        Calculate scattering parameters using Mie theory.
        
        This is the core forward calculation: given particle diameter,
        calculate how much light it scatters. Uses the rigorous Mie series
        expansion via miepython library.
        
        Args:
            diameter_nm: Particle diameter in nanometers
                        Typical range: 30-200 nm for EVs, 10-1000 nm general
            validate: If True, validate inputs and log warnings for unusual values
                     Set False for batch processing to improve performance
            
        Returns:
            MieScatterResult with complete scattering parameters:
            - Q_ext: Extinction efficiency (absorption + scattering)
            - Q_sca: Scattering efficiency (only scattering, 0-4 typical)
            - Q_back: Backscatter efficiency (scatter at 180°)
            - g: Asymmetry parameter (0=isotropic, 1=forward, -1=backward)
            - forward_scatter: FSC proxy (Q_sca × area × (1+g))
            - side_scatter: SSC proxy (Q_back × area)
            - size_parameter_x: Dimensionless size πd/λ
            
        Raises:
            ValueError: If diameter is invalid
            RuntimeError: If Mie calculation fails
            
        Physical Interpretation:
            - Small Q_sca: particle smaller than wavelength (Rayleigh regime)
            - Large Q_sca: particle comparable to or larger than wavelength
            - High g: forward scattering dominates (typical for larger particles)
            - Low g: more isotropic scattering (typical for small particles)
        
        Example:
            >>> calc = MieScatterCalculator(wavelength_nm=488)
            >>> result = calc.calculate_scattering_efficiency(diameter_nm=80)
            >>> print(f"80nm EV scattering efficiency: Q_sca={result.Q_sca:.4f}")
            >>> print(f"Forward scatter (FSC proxy): {result.forward_scatter:.2f}")
            >>> print(f"Asymmetry (forward bias): g={result.g:.3f}")
        """
        # Input validation
        if validate:
            if diameter_nm <= 0:
                raise ValueError(f"Diameter must be positive, got {diameter_nm}")
            if diameter_nm < 10:
                logger.warning(f"⚠️ Very small particle: {diameter_nm:.1f}nm (below typical detection limit)")
            if diameter_nm > 1000:
                logger.warning(f"⚠️ Large particle: {diameter_nm:.1f}nm (above typical EV range)")
        
        # Calculate size parameter: x = πd/λ (informational only, not used in calculation)
        x = (np.pi * diameter_nm) / self.wavelength_nm
        
        # Determine physical regime
        if validate and x < 0.1:
            logger.debug(f"Rayleigh regime (x={x:.3f}): scatter ∝ λ⁻⁴")
        elif validate and x > 10:
            logger.debug(f"Geometric optics regime (x={x:.3f}): ray tracing applicable")
        
        # Call miepython to calculate Mie efficiencies
        # CORRECTED (Feb 2026): Use efficiencies() with absolute RI + n_env
        # This avoids the RI double-counting bug and handles x computation correctly.
        # Previous code used single_sphere(m_relative, x) with wrong x (missing n_medium factor).
        try:
            qext, qsca, qback, g = miepython.efficiencies(
                self.m_complex, diameter_nm, self.wavelength_nm, n_env=self.n_medium
            )
        except Exception as e:
            logger.error(f"❌ Mie calculation failed for d={diameter_nm:.1f}nm, x={x:.4f}: {e}")
            raise RuntimeError(f"Mie theory calculation failed: {e}") from e
        
        # Calculate scatter intensities for flow cytometry
        # These approximate what the detectors actually measure
        
        # Geometric cross-sectional area
        radius_nm = diameter_nm / 2.0
        cross_section = np.pi * (radius_nm ** 2)  # nm²
        
        # Forward scatter (FSC): small-angle scatter (1-10°)
        # Primarily affected by scattering efficiency and forward bias
        # Higher g means more forward scatter
        # Factor (1+g) empirically matches FSC detector response
        qsca_val = float(qsca) if qsca is not None else 0.0
        g_val = float(g) if g is not None else 0.0
        qback_val = float(qback) if qback is not None else 0.0
        forward_scatter = qsca_val * cross_section * (1.0 + g_val)
        
        # Side scatter (SSC): scatter collected by side-scatter detector
        # CORRECTED (Feb 2026): Use Qsca × cross_section (total scattering cross-section)
        # Previous code used Qback (exact 180° backscatter) which was wrong.
        # Validation against NTA showed Qsca gives consistent results (CV=2.4%)
        # while Qback gave 90x variation across bead sizes.
        # For small particles (x<2), scattering is nearly isotropic,
        # so fraction captured by SSC detector ≈ constant × σ_sca.
        side_scatter = qsca_val * cross_section
        
        # Create result object
        qext_val = float(qext) if qext is not None else 0.0
        result = MieScatterResult(
            Q_ext=qext_val,
            Q_sca=qsca_val,
            Q_back=qback_val,
            g=g_val,
            forward_scatter=float(forward_scatter),
            side_scatter=float(side_scatter),
            size_parameter_x=float(x)
        )
        
        return result
    
    def diameter_from_scatter(
        self,
        fsc_intensity: float,
        min_diameter: Optional[float] = None,
        max_diameter: Optional[float] = None,
        tolerance: float = 1e-6
    ) -> Tuple[float, bool]:
        """
        Inverse Mie problem: Calculate particle diameter from measured FSC intensity.
        
        This is the KEY function for converting flow cytometry data to physical sizes!
        
        The inverse problem is ill-posed and requires numerical optimization. This
        implementation uses bounded scalar minimization (Brent's method) which is
        robust for non-smooth objectives.
        
        IMPORTANT (Dec 17, 2025 - TASK-002 Fix):
        The search range is now EXTENDED (30-220nm) to avoid edge clustering.
        Particles outside valid range should be FILTERED, not clamped to boundaries.
        
        Args:
            fsc_intensity: Measured forward scatter intensity (arbitrary units from flow cytometer)
            min_diameter: Minimum diameter to search (nm). Uses SIZE_CONFIG if None.
            max_diameter: Maximum diameter to search (nm). Uses SIZE_CONFIG if None.
            tolerance: Optimization tolerance (relative). Default 1e-6 (~0.0001 nm precision)
            
        Returns:
            Tuple of (diameter_nm, success):
            - diameter_nm: Calculated particle diameter in nanometers
            - success: True if optimization converged reliably, False if uncertain
            
        Raises:
            ValueError: If fsc_intensity is invalid (≤0)
            
        Algorithm:
            1. Define objective function: |calculated_FSC(d) - measured_FSC|²
            2. Use scipy.optimize.minimize_scalar with Brent's method
            3. Search bounded region [min_diameter, max_diameter]
            4. Validate convergence: residual < 1% of measured intensity
        
        Limitations:
            - Assumes spherical particles (Mie theory requirement)
            - Assumes homogeneous particles (uniform refractive index)
            - Non-unique solution possible for very large particles
            - Calibration recommended for absolute accuracy
        
        Example:
            >>> calc = MieScatterCalculator(wavelength_nm=488, n_particle=1.40)
            >>> # Measured FSC = 15000 (arbitrary units)
            >>> diameter, success = calc.diameter_from_scatter(fsc_intensity=15000)
            >>> if success:
            ...     print(f"Particle diameter: {diameter:.1f} nm")
            ... else:
            ...     print("Warning: optimization uncertain")
        
        Performance:
            - Typical convergence: 10-30 function evaluations
            - Time: ~0.1-1 ms per particle on modern CPU
            - For batch processing, consider using calibration curve
        """
        # Use configuration defaults if not specified
        if min_diameter is None:
            min_diameter = DEFAULT_SIZE_CONFIG.search_min_nm
        if max_diameter is None:
            max_diameter = DEFAULT_SIZE_CONFIG.search_max_nm
        # Input validation
        if fsc_intensity <= 0:
            raise ValueError(f"FSC intensity must be positive, got {fsc_intensity}")
        
        # Define objective function for optimization
        def objective(diameter: float) -> float:
            """
            Squared difference between calculated and observed FSC.
            
            Using squared difference (rather than absolute) gives smoother
            gradients for optimization and emphasizes large deviations.
            """
            try:
                result = self.calculate_scattering_efficiency(diameter, validate=False)
                calculated_fsc = result.forward_scatter
                return (calculated_fsc - fsc_intensity) ** 2
            except Exception:
                # Return large penalty if calculation fails
                # This prevents optimizer from exploring invalid regions
                return 1e12
        
        # Use bounded scalar minimization (Brent's method)
        # Advantages:
        # - No derivatives required (Mie function not analytically differentiable)
        # - Robust to local minima
        # - Guaranteed to stay within bounds
        # - Fast convergence for smooth objectives
        try:
            res: OptimizeResult = minimize_scalar(  # type: ignore[assignment]
                objective,
                bounds=(min_diameter, max_diameter),
                method='bounded',
                options={'xatol': tolerance}
            )
            
            diameter = float(res.x)
            
            # Validate convergence quality
            # Consider successful if residual < 1% of measured intensity
            final_residual = objective(diameter)
            success = bool(res.success) and (final_residual < (fsc_intensity * 0.01) ** 2)
            
            if not success:
                logger.warning(
                    f"⚠️ Inverse Mie optimization uncertain. "
                    f"FSC={fsc_intensity:.1f}, estimated d={diameter:.1f}nm, "
                    f"residual={np.sqrt(final_residual):.2e} "
                    f"({100*np.sqrt(final_residual)/fsc_intensity:.1f}% relative error)"
                )
            
            return diameter, success
            
        except Exception as e:
            logger.error(f"❌ Inverse Mie calculation failed: {e}")
            # Return midpoint of search range as fallback
            fallback_diameter = (min_diameter + max_diameter) / 2.0
            logger.warning(f"Returning fallback diameter: {fallback_diameter:.1f}nm")
            return fallback_diameter, False
    
    def _get_or_build_lut(
        self,
        min_diameter: float = 30.0,
        max_diameter: float = 500.0,
        lut_resolution: int = 500
    ) -> Dict[str, Any]:
        """
        Get cached LUT or build a new one if parameters changed.
        
        LUT APPROACH EXPLANATION (T-011 Documentation):
        ================================================
        
        Why Use a Lookup Table?
        -----------------------
        Mie scattering calculations are computationally expensive (Bessel functions,
        series expansions). For 900k+ events, calculating on-demand would be slow.
        
        Solution: Pre-compute a lookup table (LUT) mapping diameters → SSC values,
        then use fast interpolation to find diameters from measured SSC.
        
        How It Works:
        -------------
        1. Generate diameter grid: [30nm, 30.94nm, 31.88nm, ..., 500nm] (500 points)
        2. For each diameter, calculate theoretical FSC using Mie theory
        3. Sort by FSC value (Mie can be non-monotonic due to resonances)
        4. Remove duplicates for clean interpolation
        5. Cache the result for reuse
        
        For inverse lookup (SSC → diameter):
        - Use numpy.interp() for O(n) interpolation
        - ~1000x faster than calling Mie theory per-event
        
        Cache Key:
        - Includes min_diameter, max_diameter, resolution, wavelength, n_particle, n_medium
        - If any parameter changes, LUT is rebuilt
        
        Args:
            min_diameter: Minimum diameter in LUT (nm)
            max_diameter: Maximum diameter in LUT (nm)
            lut_resolution: Number of points in LUT
            
        Returns:
            Dict with cached LUT arrays (fsc_unique, diameters_unique, fsc_min, fsc_max)
        """
        # Create cache key from all parameters that affect the LUT
        cache_key = f"{min_diameter}_{max_diameter}_{lut_resolution}_{self.wavelength_nm}_{self.n_particle}_{self.n_medium}"
        
        # Return cached LUT if parameters haven't changed
        if self._lut_cache is not None and self._lut_cache_key == cache_key:
            return self._lut_cache
        
        # Build new LUT
        logger.debug(f"Building LUT: {min_diameter}-{max_diameter}nm, {lut_resolution} points")
        
        diameters_lut = np.linspace(min_diameter, max_diameter, lut_resolution)
        fsc_lut = np.zeros(lut_resolution)
        
        for i, d in enumerate(diameters_lut):
            result = self.calculate_scattering_efficiency(d, validate=False)
            fsc_lut[i] = result.forward_scatter
        
        # Sort by FSC (Mie resonances can cause non-monotonicity)
        sort_idx = np.argsort(fsc_lut)
        fsc_sorted = fsc_lut[sort_idx]
        diameters_sorted = diameters_lut[sort_idx]
        
        # Remove duplicates for clean interpolation
        unique_mask = np.diff(fsc_sorted, prepend=-np.inf) > 0
        fsc_unique = fsc_sorted[unique_mask]
        diameters_unique = diameters_sorted[unique_mask]
        
        # Cache the LUT
        self._lut_cache = {
            'fsc_unique': fsc_unique,
            'diameters_unique': diameters_unique,
            'fsc_min': fsc_unique[0],
            'fsc_max': fsc_unique[-1],
            'diameters_lut': diameters_lut,
            'fsc_lut': fsc_lut
        }
        self._lut_cache_key = cache_key
        
        logger.debug(f"LUT built and cached: {len(fsc_unique)} unique points")
        return self._lut_cache
    
    def diameters_from_scatter_batch(
        self,
        fsc_intensities: np.ndarray,
        min_diameter: float = 30.0,
        max_diameter: float = 500.0,
        lut_resolution: int = 500
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        FAST vectorized diameter calculation using lookup table interpolation.
        
        This is 100-1000x faster than calling diameter_from_scatter() in a loop!
        Uses precomputed lookup table (LUT) with linear interpolation.
        
        LUT CACHING (Feb 2026):
        -----------------------
        The lookup table is now cached after first build. Subsequent calls with
        the same parameters reuse the cached LUT, avoiding repeated Mie calculations.
        
        Args:
            fsc_intensities: Array of FSC intensity values
            min_diameter: Minimum diameter in lookup table (nm)
            max_diameter: Maximum diameter in lookup table (nm)
            lut_resolution: Number of points in lookup table (higher = more accurate)
            
        Returns:
            Tuple of (diameters, success_mask):
            - diameters: Array of estimated diameters in nm
            - success_mask: Boolean array indicating valid estimates
        """
        # Get or build cached LUT
        lut = self._get_or_build_lut(min_diameter, max_diameter, lut_resolution)
        
        fsc_unique = lut['fsc_unique']
        diameters_unique = lut['diameters_unique']
        fsc_min = lut['fsc_min']
        fsc_max = lut['fsc_max']
        
        # Interpolate: FSC intensity -> diameter
        fsc_intensities = np.asarray(fsc_intensities)
        
        # Clamp intensities to valid range for interpolation
        fsc_clamped = np.clip(fsc_intensities, fsc_min, fsc_max)
        
        # Linear interpolation (O(n) - very fast)
        estimated_diameters = np.interp(fsc_clamped, fsc_unique, diameters_unique)
        
        # Mark values outside valid FSC range as potentially unreliable
        success_mask = (fsc_intensities >= fsc_min * 0.5) & (fsc_intensities <= fsc_max * 1.5)
        
        return estimated_diameters, success_mask
    
    def diameters_from_scatter_normalized(
        self,
        fsc_intensities: np.ndarray,
        min_diameter: float = 30.0,
        max_diameter: float = 500.0,
        lut_resolution: int = 500
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate particle diameters from FSC intensities with automatic normalization.
        
        .. deprecated::
            This method uses heuristic percentile-based normalization because no
            instrument calibration factor is available.  Results are approximate
            and size-distribution dependent.  For accurate absolute sizing, use
            FCMPASS k-based calibration via ``FCMPASSCalibrator``.
        
        The approach:
        1. Build a LUT of physical scattering cross-sections (σ_sca) for the
           diameter range using Mie theory
        2. Map the raw FSC percentile range to the σ_sca range (affine mapping)
        3. Interpolate to find diameters
        
        Phase 5 improvements (Feb 2026):
        - Uses σ_sca (Qsca × πr²) instead of the FSC proxy (Qsca × πr² × (1+g))
          for consistency with the FCMPASS pipeline
        - Logs a deprecation warning on every call
        - Improved outlier handling (P2/P98 instead of P5/P95)
        
        Args:
            fsc_intensities: Array of raw FSC intensity values from flow cytometer
            min_diameter: Minimum diameter in lookup table (nm)
            max_diameter: Maximum diameter in lookup table (nm)
            lut_resolution: Number of points in lookup table
            
        Returns:
            Tuple of (diameters, success_mask):
            - diameters: Array of estimated diameters in nm
            - success_mask: Boolean array indicating valid estimates
        """
        logger.warning(
            "⚠️ diameters_from_scatter_normalized() uses heuristic normalization. "
            "Results are approximate. For accurate sizing, use FCMPASS calibration."
        )
        
        fsc_intensities = np.asarray(fsc_intensities, dtype=np.float64)
        
        # Filter out invalid values for normalization
        valid_mask = (fsc_intensities > 0) & np.isfinite(fsc_intensities)
        
        if not np.any(valid_mask):
            return np.zeros_like(fsc_intensities), np.zeros_like(fsc_intensities, dtype=bool)
        
        # Build lookup table: diameter -> σ_sca (total scattering cross-section)
        # Phase 5 FIX: Use σ_sca = Qsca × πr² (consistent with FCMPASS)
        # instead of the FSC proxy Qsca × πr² × (1+g) which baked in the
        # asymmetry parameter and caused inconsistencies with the SSC-based
        # sizing used by FCMPASS and multi-solution Mie.
        diameters_lut = np.linspace(min_diameter, max_diameter, lut_resolution)
        sigma_sca_lut = np.zeros(lut_resolution)
        
        for i, d in enumerate(diameters_lut):
            result = self.calculate_scattering_efficiency(d, validate=False)
            # σ_sca = Qsca × πr²  (side_scatter field already stores this)
            sigma_sca_lut[i] = result.side_scatter
        
        # Ensure monotonicity for interpolation
        sort_idx = np.argsort(sigma_sca_lut)
        sigma_sorted = sigma_sca_lut[sort_idx]
        diameters_sorted = diameters_lut[sort_idx]
        
        # Remove duplicates
        unique_mask = np.diff(sigma_sorted, prepend=-np.inf) > 0
        sigma_unique = sigma_sorted[unique_mask]
        diameters_unique = diameters_sorted[unique_mask]
        
        if len(sigma_unique) < 2:
            logger.warning("⚠️ Insufficient unique σ_sca values in lookup table")
            return np.zeros_like(fsc_intensities), np.zeros_like(fsc_intensities, dtype=bool)
        
        # Normalize raw FSC values to σ_sca range
        # Phase 5 FIX: Use P2/P98 instead of P5/P95 for better coverage
        # of the tails, reducing artificial clamping of extreme sizes.
        raw_fsc_valid = fsc_intensities[valid_mask]
        raw_p2, raw_p98 = np.percentile(raw_fsc_valid, [2, 98])
        sigma_min, sigma_max = sigma_unique[0], sigma_unique[-1]
        
        # Affine mapping: raw_FSC -> σ_sca
        raw_range = raw_p98 - raw_p2
        if raw_range <= 0:
            raw_range = 1.0  # Avoid division by zero
        
        sigma_range = sigma_max - sigma_min
        normalized_fsc = sigma_min + (fsc_intensities - raw_p2) / raw_range * sigma_range
        
        # Clamp to σ_sca range
        normalized_fsc_clamped = np.clip(normalized_fsc, sigma_min, sigma_max)
        
        # Interpolate to get diameters
        estimated_diameters = np.interp(normalized_fsc_clamped, sigma_unique, diameters_unique)
        
        # Mark success for values within reasonable range (not extreme outliers)
        success_mask = valid_mask & (fsc_intensities >= raw_p2 * 0.1) & (fsc_intensities <= raw_p98 * 10)
        
        logger.debug(
            f"📊 Normalized FSC mapping: raw=[{raw_p2:.0f}, {raw_p98:.0f}] → "
            f"σ_sca=[{sigma_min:.2e}, {sigma_max:.2e}], "
            f"valid={np.sum(success_mask)}/{len(fsc_intensities)}"
        )
        
        return estimated_diameters, success_mask
    
    def calculate_wavelength_response(
        self,
        diameter_nm: float,
        wavelengths: Optional[List[float]] = None
    ) -> Dict[str, float]:
        """
        Calculate scatter at multiple wavelengths for spectral analysis.
        
        This enables wavelength-dependent particle characterization. Key applications:
        - Identify optimal detection wavelength for specific size range
        - Explain why certain markers work better at specific wavelengths
        - Validate particle size estimates across multiple lasers
        
        Physical Insight:
        - Small particles (d << λ): Rayleigh regime, scatter ∝ λ⁻⁴
          → Blue light scatters much more than red
        - Large particles (d >> λ): Geometric regime, scatter ∝ λ⁰
          → Wavelength-independent scatter
        - Intermediate (d ~ λ): Resonance effects, complex behavior
        
        Args:
            diameter_nm: Particle diameter in nanometers
            wavelengths: List of wavelengths to test (nm)
                        Default: [405, 488, 561, 633] (ZE5 Bio-Rad lasers)
                        Can specify custom list for other instruments
                        
        Returns:
            Dictionary mapping wavelength string to forward scatter intensity
            Format: {'405nm': intensity, '488nm': intensity, ...}
            Higher intensity = stronger scatter at that wavelength
            
        Example:
            >>> calc = MieScatterCalculator(n_particle=1.40, n_medium=1.33)
            >>> # Test 80nm exosome at all ZE5 wavelengths
            >>> response = calc.calculate_wavelength_response(diameter_nm=80)
            >>> print(f"Blue/Red ratio: {response['488nm']/response['633nm']:.2f}")
            >>> # Result: ~2-3x more blue than red for 80nm particles
            >>> 
            >>> # Explain biological observation
            >>> cd9_response = calc.calculate_wavelength_response(diameter_nm=80)
            >>> print(f"Why CD9 (80nm) scatters blue: FSC@488nm = {cd9_response['488nm']:.0f}")
        """
        if wavelengths is None:
            # Default to ZE5 Bio-Rad flow cytometer lasers
            wavelengths = [405, 488, 561, 633]
        
        # Store original configuration
        original_wavelength = self.wavelength_nm
        results = {}
        
        try:
            for wavelength in wavelengths:
                # Temporarily update calculator for this wavelength
                self.wavelength_nm = wavelength
                # Note: Refractive indices are wavelength-dependent in reality
                # For now, assume constant (good approximation for visible range)
                
                # Calculate scatter
                result = self.calculate_scattering_efficiency(diameter_nm, validate=False)
                results[f'{int(wavelength)}nm'] = result.forward_scatter
                
        finally:
            # Always restore original wavelength (even if exception occurs)
            self.wavelength_nm = original_wavelength
        
        return results
    
    def batch_calculate(
        self,
        diameters_nm: np.ndarray,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Calculate FSC for array of diameters (optimized for performance).
        
        For large datasets (>10,000 particles), batch processing is much more
        efficient than individual calculations. This method:
        - Disables per-particle validation (faster)
        - Shows progress for large arrays (user feedback)
        - Returns NumPy array for efficient downstream processing
        
        Args:
            diameters_nm: NumPy array of particle diameters in nanometers
                         Shape: (n_particles,)
            show_progress: If True, log progress every 1000 particles
                          Useful for very large datasets (>10K particles)
            
        Returns:
            NumPy array of forward scatter intensities
            Shape: (n_particles,) matching input
            Units: Same as calculate_scattering_efficiency().forward_scatter
            
        Performance:
            - ~0.1-1 ms per particle (depending on CPU)
            - For 10,000 particles: ~1-10 seconds
            - For 100,000 particles: ~10-100 seconds
        
        Example:
            >>> calc = MieScatterCalculator(wavelength_nm=488, n_particle=1.40)
            >>> # Generate size distribution (50-150nm)
            >>> diameters = np.linspace(50, 150, 1000)
            >>> # Calculate FSC for all particles
            >>> fsc_values = calc.batch_calculate(diameters, show_progress=True)
            >>> # Analyze results
            >>> print(f"FSC range: {fsc_values.min():.1f} - {fsc_values.max():.1f}")
            >>> print(f"Mean FSC: {fsc_values.mean():.1f}")
        """
        n = len(diameters_nm)
        fsc_values = np.zeros(n)
        
        if show_progress and n > 100:
            logger.info(f"🔄 Calculating Mie scatter for {n:,} particles...")
        
        for i, diameter in enumerate(diameters_nm):
            if show_progress and n > 1000 and i % 1000 == 0:
                logger.info(f"  Progress: {i:,}/{n:,} ({100*i/n:.1f}%)")
            
            result = self.calculate_scattering_efficiency(diameter, validate=False)
            fsc_values[i] = result.forward_scatter
        
        if show_progress and n > 100:
            logger.info(f"✅ Batch calculation complete ({n:,} particles)")
        
        return fsc_values


class MultiSolutionMieCalculator:
    """
    Multi-Solution Mie Scattering Calculator with Wavelength Disambiguation.
    
    PROBLEM SOLVED:
    ---------------
    The Mie scattering function is non-monotonic - one scatter value can map to 
    MULTIPLE particle sizes due to resonances (oscillations in the scattering 
    efficiency). The single-solution approach picks the first/closest match, which
    can be wrong by 20-30%.
    
    SOLUTION:
    ---------
    Use two wavelengths (e.g., 405nm violet and 488nm blue) to disambiguate:
    - Find ALL candidate sizes that match the measured scatter value
    - For each candidate, calculate the theoretical VSSC/BSSC ratio
    - Pick the candidate whose theoretical ratio best matches measured ratio
    
    PHYSICS INSIGHT (from Mätzler Mie Functions literature & Parvesh Reddy, Jan 2026):
    ----------------------------------------------------------------------------------
    - Size parameter x = πd/λ → smaller λ gives LARGER x (more signal)
    - Rayleigh scattering ∝ λ⁻⁴ → violet (405nm) scatters MORE for small particles
    - EVs (30-150nm) are in Rayleigh/early-resonance regime
    - **VIOLET (405nm) is now PRIMARY** for better small-particle sensitivity
    
    WAVELENGTH SELECTION RATIONALE (Feb 2026):
    ------------------------------------------
    - Violet (405nm) as PRIMARY: Better sensitivity for small EVs (Rayleigh regime)
    - Blue (488nm) as SECONDARY: Used for ratio-based disambiguation
    - This matches the physics: shorter wavelength → stronger scattering for d << λ
    
    Example Usage:
        >>> calc = MultiSolutionMieCalculator(n_particle=1.40, n_medium=1.33)
        >>> 
        >>> # Get both wavelength SSC values from FCS data
        >>> ssc_blue = data['BSSC-H'].values  # 488nm
        >>> ssc_violet = data['VSSC-H'].values  # 405nm
        >>> 
        >>> # Calculate sizes with disambiguation (violet primary by default)
        >>> sizes, num_solutions = calc.calculate_sizes_multi_solution(ssc_blue, ssc_violet)
        >>> print(f"D50: {np.nanmedian(sizes):.1f} nm")
        >>> print(f"Events with multiple solutions: {(num_solutions > 1).sum()}")
    
    References:
        - Mätzler (2002) "MATLAB Functions for Mie Scattering and Absorption"
        - Bohren & Huffman (1983) "Absorption and Scattering of Light by Small Particles"
        - January 2026 meeting with Parvesh Reddy (wavelength ratio disambiguation)
        - compare_single_vs_multi_solution.py script validation
    """
    
    # Physical constants for wavelengths
    WAVELENGTH_VIOLET = 405.0  # nm (VSSC channel) - PRIMARY for small EVs
    WAVELENGTH_BLUE = 488.0    # nm (BSSC channel) - SECONDARY for disambiguation
    
    def __init__(
        self,
        n_particle: float = 1.40,
        n_medium: float = 1.33,
        min_diameter: float = 30.0,
        max_diameter: float = 500.0,
        lut_resolution: int = 471,
        k_violet: Optional[float] = None,
        k_blue: Optional[float] = None,
    ):
        """
        Initialize multi-solution Mie calculator.
        
        Args:
            n_particle: Refractive index of particles (EVs: 1.37-1.45)
            n_medium: Refractive index of medium (PBS: 1.33)
            min_diameter: Minimum diameter in lookup table (nm)
            max_diameter: Maximum diameter in lookup table (nm)
            lut_resolution: Number of points in LUT (default 471 = 1nm steps from 30-500)
            k_violet: Instrument constant for violet SSC (AU/σ). If provided,
                      enables exact AU→σ conversion instead of heuristic
                      normalization.  Obtain from FCMPASS bead calibration.
            k_blue:   Instrument constant for blue SSC (AU/σ).
        """
        self.n_particle = n_particle
        self.n_medium = n_medium
        self.m = complex(n_particle / n_medium, 0)
        self.min_diameter = min_diameter
        self.max_diameter = max_diameter
        self.k_violet = k_violet
        self.k_blue = k_blue
        
        # Build lookup tables for BOTH wavelengths
        self.lut_diameters = np.linspace(min_diameter, max_diameter, lut_resolution)
        
        # Pre-compute SSC for violet (405nm)
        self.lut_ssc_violet = np.zeros(lut_resolution)
        for i, d in enumerate(self.lut_diameters):
            self.lut_ssc_violet[i] = self._calc_ssc(d, self.WAVELENGTH_VIOLET)
        
        # Pre-compute SSC for blue (488nm)
        self.lut_ssc_blue = np.zeros(lut_resolution)
        for i, d in enumerate(self.lut_diameters):
            self.lut_ssc_blue[i] = self._calc_ssc(d, self.WAVELENGTH_BLUE)
        
        # Pre-compute theoretical VSSC/BSSC ratios
        with np.errstate(divide='ignore', invalid='ignore'):
            self.lut_ratio = np.divide(
                self.lut_ssc_violet, 
                self.lut_ssc_blue, 
                out=np.ones_like(self.lut_ssc_violet), 
                where=self.lut_ssc_blue > 0
            )
        
        logger.info(
            f"✓ MultiSolutionMie initialized: n={n_particle:.2f}, "
            f"range={min_diameter:.0f}-{max_diameter:.0f}nm, "
            f"LUT size={lut_resolution}"
            + (f", k_violet={k_violet:.1f}" if k_violet else "")
            + (f", k_blue={k_blue:.1f}" if k_blue else "")
        )
    
    def _calc_ssc(self, diameter_nm: float, wavelength_nm: float) -> float:
        """
        Calculate side scatter cross-section for a diameter at specific wavelength.
        
        CORRECTED (Feb 2026): Uses Qsca (total scatter) instead of Qback (180° only).
        Uses absolute RI with n_env to avoid double-counting.
        Validated against NTA: CV=2.4% across 4 bead sizes.
        """
        m = complex(self.n_particle, 0)  # ABSOLUTE RI (corrected from relative)
        try:
            # miepython.efficiencies returns: (qext, qsca, qback, g)
            result = miepython.efficiencies(m, diameter_nm, wavelength_nm, n_env=self.n_medium)
            qsca = float(result[1]) if result[1] is not None else 0.0
            
            # Scattering cross-section: σ_sca = Qsca × πr²
            radius = diameter_nm / 2.0
            cross_section = np.pi * (radius ** 2)
            
            return qsca * cross_section
        except Exception:
            return 0.0
    
    def find_all_solutions(
        self, 
        target_ssc: float, 
        wavelength_nm: float = 488.0, 
        tolerance_pct: float = 15.0
    ) -> List[float]:
        """
        Find ALL diameters that could produce the given SSC value.
        
        This is the key difference from single-solution: we find MULTIPLE candidates.
        
        Args:
            target_ssc: Target SSC value to match
            wavelength_nm: Which wavelength LUT to use (405 or 488)
            tolerance_pct: Tolerance for matching (15% default accounts for noise)
            
        Returns:
            List of possible diameters (may be empty, 1, or multiple)
        """
        if wavelength_nm == 405.0:
            lut_ssc = self.lut_ssc_violet
        else:
            lut_ssc = self.lut_ssc_blue
        
        tolerance = abs(target_ssc * tolerance_pct / 100.0)
        solutions: List[float] = []
        
        for i, (d, ssc) in enumerate(zip(self.lut_diameters, lut_ssc)):
            if abs(ssc - target_ssc) <= tolerance:
                # Check if this is a new solution (not too close to previous)
                # Prevents reporting nearby LUT points as separate solutions
                if not solutions or abs(d - solutions[-1]) > 10.0:
                    solutions.append(float(d))
        
        return solutions
    
    def disambiguate_with_ratio(
        self, 
        possible_sizes: List[float], 
        measured_ratio: float
    ) -> Tuple[float, List[float], int]:
        """
        Select best size using wavelength ratio (VSSC/BSSC).
        
        PHYSICS:
        - Small particles: violet scatters more (ratio > 1)
        - Large particles: similar scattering (ratio ≈ 1)
        
        Args:
            possible_sizes: List of candidate sizes from find_all_solutions()
            measured_ratio: Actual VSSC/BSSC ratio from flow cytometry data
            
        Returns:
            Tuple of (best_size, theoretical_ratios, best_index)
        """
        if not possible_sizes:
            return np.nan, [], -1
        
        if len(possible_sizes) == 1:
            idx = np.abs(self.lut_diameters - possible_sizes[0]).argmin()
            return possible_sizes[0], [self.lut_ratio[idx]], 0
        
        best_size = possible_sizes[0]
        best_error = float('inf')
        best_idx = 0
        theoretical_ratios: List[float] = []
        
        for i, size in enumerate(possible_sizes):
            idx = np.abs(self.lut_diameters - size).argmin()
            theoretical_ratio = self.lut_ratio[idx]
            theoretical_ratios.append(float(theoretical_ratio))
            
            error = abs(theoretical_ratio - measured_ratio)
            if error < best_error:
                best_error = error
                best_size = size
                best_idx = i
        
        return best_size, theoretical_ratios, best_idx
    
    def _au_to_sigma(
        self,
        ssc_raw: np.ndarray,
        wavelength_nm: float,
    ) -> np.ndarray:
        """
        Convert raw AU values to physical σ_sca (nm²).
        
        When a k-factor is available (from FCMPASS bead calibration) the
        conversion is exact: σ = AU / k.  Otherwise fall back to affine
        percentile mapping.
        
        Args:
            ssc_raw: Raw AU intensities (positive values only)
            wavelength_nm: 405 or 488 — selects which k-factor / LUT to use
            
        Returns:
            σ_sca array in nm² (same length as ssc_raw)
        """
        k = self.k_violet if wavelength_nm == 405.0 else self.k_blue
        
        if k is not None and k > 0:
            # ── Exact conversion with calibrated k-factor ──
            return ssc_raw / k
        
        # ── Fallback: percentile-based affine mapping ──
        lut = self.lut_ssc_violet if wavelength_nm == 405.0 else self.lut_ssc_blue
        pos = ssc_raw[ssc_raw > 0]
        if len(pos) == 0:
            return ssc_raw  # nothing to normalise
        
        au_p5, au_p95 = np.percentile(pos, [5, 95])
        lut_min, lut_max = float(lut.min()), float(lut.max())
        au_range = au_p95 - au_p5
        if au_range <= 0:
            return ssc_raw
        scale = (lut_max - lut_min) / au_range
        offset = lut_min - au_p5 * scale
        return ssc_raw * scale + offset
    
    def calculate_sizes_multi_solution(
        self,
        ssc_blue: np.ndarray,
        ssc_violet: np.ndarray,
        tolerance_pct: float = 15.0,
        use_violet_primary: bool = True
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate particle sizes using multi-solution disambiguation.
        
        This is the PRODUCTION method for accurate sizing when both wavelengths
        are available. For each event:
        1. Convert AU → σ_sca using k-factor (exact) or percentile map (approx)
        2. Find ALL sizes that match the PRIMARY σ_sca (within tolerance)
        3. If multiple solutions, use σ_violet/σ_blue ratio to pick correct one
        
        When ``k_violet`` and ``k_blue`` are set (from FCMPASS bead calibration),
        the conversion is physics-grounded and accurate.  Without k-factors the
        method uses heuristic percentile normalization and logs a warning.
        
        Args:
            ssc_blue: Array of blue SSC (488nm) AU values, shape (n_events,)
            ssc_violet: Array of violet SSC (405nm) AU values, shape (n_events,)
            tolerance_pct: Tolerance for solution matching (default 15%)
            use_violet_primary: If True (default), use violet 405nm as primary
            
        Returns:
            Tuple of (sizes, num_solutions)
        """
        n_events = len(ssc_blue)
        sizes = np.zeros(n_events)
        num_solutions = np.zeros(n_events)
        
        has_k = (self.k_violet is not None and self.k_violet > 0)
        
        if has_k:
            logger.info(
                f"🎯 Multi-solution Mie using calibrated k-factors: "
                f"k_violet={self.k_violet:.1f}"
                + (f", k_blue={self.k_blue:.1f}" if self.k_blue else "")
            )
        else:
            logger.warning(
                "⚠️ Multi-solution Mie using heuristic AU→σ normalization "
                "(no k-factor available). Results are approximate."
            )
        
        # ── Convert AU → σ_sca for both channels ──
        ssc_blue_arr = np.asarray(ssc_blue, dtype=np.float64)
        ssc_violet_arr = np.asarray(ssc_violet, dtype=np.float64)
        
        sigma_violet = self._au_to_sigma(ssc_violet_arr, 405.0)
        sigma_blue = self._au_to_sigma(ssc_blue_arr, 488.0)
        
        # Select primary channel based on physics
        if use_violet_primary:
            primary_sigma = sigma_violet
            primary_wavelength = 405.0
        else:
            primary_sigma = sigma_blue
            primary_wavelength = 488.0
        
        for i in range(n_events):
            if ssc_blue_arr[i] <= 0 or ssc_violet_arr[i] <= 0:
                sizes[i] = np.nan
                num_solutions[i] = 0
                continue
            
            # Step 1: Find ALL possible solutions using PRIMARY σ_sca
            solutions = self.find_all_solutions(
                primary_sigma[i], 
                wavelength_nm=primary_wavelength, 
                tolerance_pct=tolerance_pct
            )
            num_solutions[i] = len(solutions)
            
            if len(solutions) == 0:
                sizes[i] = np.nan
            elif len(solutions) == 1:
                sizes[i] = solutions[0]
            else:
                # Step 2: Use σ ratio (NOT raw AU ratio) for disambiguation
                # This is correct because the LUT ratio is also σ_violet/σ_blue
                if sigma_blue[i] > 0:
                    measured_ratio = sigma_violet[i] / sigma_blue[i]
                else:
                    measured_ratio = 1.0
                best_size, _, _ = self.disambiguate_with_ratio(solutions, measured_ratio)
                sizes[i] = best_size
        
        return sizes, num_solutions
    
    def calculate_sizes_single_solution(
        self,
        ssc_values: np.ndarray,
        wavelength_nm: float = 488.0
    ) -> np.ndarray:
        """
        Calculate particle sizes using simple single-solution approach (for comparison).
        
        This picks the FIRST/CLOSEST matching size, which can be wrong for ~89%
        of events that have multiple possible solutions.
        
        Args:
            ssc_values: Array of SSC values
            wavelength_nm: Wavelength for lookup table
            
        Returns:
            Array of estimated diameters in nm
        """
        if wavelength_nm == 405.0:
            lut_ssc = self.lut_ssc_violet
        else:
            lut_ssc = self.lut_ssc_blue
        
        ssc_values = np.asarray(ssc_values, dtype=np.float64)
        sizes = np.zeros(len(ssc_values))
        
        # Convert AU → σ_sca using k-factor or percentile fallback
        ssc_sigma = self._au_to_sigma(ssc_values, wavelength_nm)
        
        for i, ssc in enumerate(ssc_sigma):
            if ssc_values[i] <= 0:
                sizes[i] = np.nan
                continue
            
            # Find closest match (picks FIRST/CLOSEST only)
            errors = np.abs(lut_ssc - ssc)
            best_idx = np.argmin(errors)
            sizes[i] = self.lut_diameters[best_idx]
        
        return sizes
    
    def get_multi_solution_stats(
        self,
        ssc_blue: np.ndarray,
        ssc_violet: np.ndarray
    ) -> Dict[str, Any]:
        """
        Get statistics about multi-solution disambiguation.
        
        Useful for understanding how many events had ambiguous sizing.
        """
        sizes, num_solutions = self.calculate_sizes_multi_solution(ssc_blue, ssc_violet)
        
        valid_mask = ~np.isnan(sizes)
        valid_sizes = sizes[valid_mask]
        valid_num_solutions = num_solutions[valid_mask]
        
        return {
            'total_events': len(ssc_blue),
            'valid_events': int(valid_mask.sum()),
            'events_with_1_solution': int((valid_num_solutions == 1).sum()),
            'events_with_2_solutions': int((valid_num_solutions == 2).sum()),
            'events_with_3plus_solutions': int((valid_num_solutions >= 3).sum()),
            'avg_solutions_per_event': float(np.mean(valid_num_solutions)) if len(valid_num_solutions) > 0 else 0,
            'd10': float(np.percentile(valid_sizes, 10)) if len(valid_sizes) > 0 else None,
            'd50': float(np.percentile(valid_sizes, 50)) if len(valid_sizes) > 0 else None,
            'd90': float(np.percentile(valid_sizes, 90)) if len(valid_sizes) > 0 else None,
            'mean': float(np.mean(valid_sizes)) if len(valid_sizes) > 0 else None,
            'std': float(np.std(valid_sizes)) if len(valid_sizes) > 0 else None,
        }


class FCMPASSCalibrator:
    """
    FCMPASS-style calibration for flow cytometry scatter standardization.
    
    CORRECTED (Feb 2026):
    ====================
    Complete rewrite using validated k-based calibration method.
    
    Previous approach: Polynomial FSC→Mie mapping (broken, no physics basis).
    Current approach: Linear AU = k × σ_sca calibration (validated, CV=2.4%).
    
    Calibration process:
    1. Measure reference beads with known sizes
    2. Calculate theoretical σ_sca = Qsca × πr² for each bead at measurement wavelength
       - Uses absolute RI with n_env to avoid double-counting
       - PS bead RI corrected for wavelength dispersion (Cauchy equation)
    3. Compute instrument constant: k = AU / σ_sca (should be constant across beads)
    4. For EVs: σ_ev = AU / k, then d_EV = inverse_Mie(σ_ev, RI_ev)
    
    Validation results (nanoViS beads, CytoFLEX nano):
    - k = 940.6 ± 22.8 (CV=2.4%) — excellent consistency
    - Bead recovery error: < 0.7% for all 4 beads
    - NTA comparison (>100nm): -4.0% error vs NTA D50 of 127.3nm
    
    References:
    - FCMPASS: Flow Cytometry Mie Particle Axis Standardization Software
    - Welsh et al., Cytometry A 2020 (FCMPASS paper)
    - Sultanova et al. (2009) for PS wavelength dispersion
    """
    
    def __init__(
        self,
        wavelength_nm: float = 405.0,
        n_bead: float = 1.591,
        n_ev: float = 1.37,
        n_medium: float = 1.33,
        use_wavelength_dispersion: bool = True
    ):
        """
        Initialize FCMPASS calibrator.
        
        Args:
            wavelength_nm: Laser wavelength (405nm for VSSC1-H, 488nm for BSSC-H)
            n_bead: Refractive index of calibration beads (PS: 1.591 at 590nm)
            n_ev: Refractive index of EVs (1.37 for SEC-purified, 1.40 for general)
            n_medium: Refractive index of medium (PBS: 1.33)
            use_wavelength_dispersion: If True, correct PS bead RI for wavelength
        """
        self.wavelength_nm = wavelength_nm
        self.n_medium = n_medium
        self.n_ev = n_ev
        
        # Apply PS wavelength dispersion if requested
        if use_wavelength_dispersion and abs(n_bead - 1.591) < 0.01:
            self.n_bead = polystyrene_ri_at_wavelength(wavelength_nm)
            logger.info(
                f"PS bead RI corrected: {n_bead:.3f} @ 590nm → "
                f"{self.n_bead:.4f} @ {wavelength_nm:.0f}nm (Cauchy)"
            )
        else:
            self.n_bead = n_bead
        
        # Also support legacy n_particle attribute
        self.n_particle = self.n_bead
        
        # Create Mie calculators
        self.mie_calc = MieScatterCalculator(
            wavelength_nm=wavelength_nm,
            n_particle=self.n_bead,
            n_medium=n_medium
        )
        
        # Calibration state
        self.k_instrument = None  # Instrument constant: AU = k × σ_sca
        self.k_std = None
        self.k_cv_pct = None
        self.calibrated = False
        
        # EV inverse Mie lookup table (built on first use)
        self._ev_lut_diameters = None
        self._ev_lut_sigmas = None
        
        # Legacy attributes for backward compatibility
        self.calibration_poly = None
        self.fsc_to_mie_poly = None
        
        # Store bead data for diagnostics
        self.bead_diameters: np.ndarray = np.array([])
        self.bead_fsc_measured: np.ndarray = np.array([])
        self.bead_fsc_theoretical: np.ndarray = np.array([])
        
        logger.info(
            f"✓ FCMPASS Calibrator initialized: λ={wavelength_nm:.1f}nm, "
            f"n_bead={self.n_bead:.4f}, n_ev={n_ev:.2f}"
        )
    
    def _compute_bead_sigma(self, diameter_nm: float) -> float:
        """Compute scattering cross-section for a bead: σ = Qsca × πr²."""
        m = complex(self.n_bead, 0)  # Absolute RI
        result = miepython.efficiencies(m, diameter_nm, self.wavelength_nm, n_env=self.n_medium)
        qsca = float(result[1])
        return qsca * np.pi * (diameter_nm / 2.0) ** 2
    
    def _build_ev_lut(self, d_min=20.0, d_max=500.0, n_points=5000):
        """Build EV inverse Mie lookup table."""
        if self._ev_lut_diameters is not None:
            return
        
        self._ev_lut_diameters = np.linspace(d_min, d_max, n_points)
        self._ev_lut_sigmas = np.zeros(n_points)
        
        m_ev = complex(self.n_ev, 0)
        for i, d in enumerate(self._ev_lut_diameters):
            result = miepython.efficiencies(m_ev, d, self.wavelength_nm, n_env=self.n_medium)
            self._ev_lut_sigmas[i] = float(result[1]) * np.pi * (d / 2.0) ** 2
        
        logger.debug(f"EV LUT built: {d_min}-{d_max}nm, {n_points} points, RI={self.n_ev}")
    
    def fit_from_beads(
        self,
        bead_measurements: Dict[float, float],
        poly_degree: int = 2
    ) -> None:
        """
        Fit calibration from reference bead measurements.
        
        CORRECTED: Uses k-based method instead of polynomial.
        The k = AU / σ_sca should be constant across all beads for a linear detector.
        
        Args:
            bead_measurements: Dict mapping bead diameter (nm) to measured AU/FSC
                              Example: {40: 1888, 80: 102411, 108: 565342}
            poly_degree: Ignored (kept for backward compatibility)
        """
        if len(bead_measurements) < 2:
            raise ValueError(f"Need at least 2 reference beads, got {len(bead_measurements)}")
        
        logger.info(f"🔬 Fitting k-based calibration from {len(bead_measurements)} reference beads")
        
        # Extract and sort by diameter
        diameters = np.array(sorted(bead_measurements.keys()))
        au_measured = np.array([bead_measurements[d] for d in diameters])
        
        # Calculate theoretical sigma_sca for each bead
        fsc_theoretical = []
        k_values = []
        
        for diameter, au in zip(diameters, au_measured):
            sigma = self._compute_bead_sigma(diameter)
            fsc_theoretical.append(sigma)
            if sigma > 0:
                k_values.append(au / sigma)
            
            logger.info(
                f"  {diameter:.0f}nm: AU={au:.0f}, σ_sca={sigma:.4f} nm², "
                f"k={au/sigma:.1f}" if sigma > 0 else f"  {diameter:.0f}nm: AU={au:.0f}, σ=0"
            )
        
        fsc_theoretical = np.array(fsc_theoretical)
        k_arr = np.array(k_values)
        
        # Compute instrument constant
        self.k_instrument = float(np.mean(k_arr))
        self.k_std = float(np.std(k_arr))
        self.k_cv_pct = float(100 * self.k_std / self.k_instrument) if self.k_instrument > 0 else 0
        
        # Store for diagnostics
        self.bead_diameters = diameters
        self.bead_fsc_measured = au_measured
        self.bead_fsc_theoretical = fsc_theoretical
        self.calibrated = True
        
        # Build EV LUT
        self._build_ev_lut()
        
        logger.info(f"✅ Calibration complete:")
        logger.info(f"   k = {self.k_instrument:.1f} ± {self.k_std:.1f} (CV={self.k_cv_pct:.1f}%)")
        logger.info(f"   Beads: {diameters.tolist()}")
        
        # Verify: self-consistency check
        self._self_validation_results = self.self_validate(bead_measurements)
        
    def self_validate(
        self,
        bead_measurements: Optional[Dict[float, float]] = None,
        cv_map: Optional[Dict[float, float]] = None,
    ) -> Dict[str, Any]:
        """
        Self-validation: verify the k-based calibration round-trips correctly.
        
        Round-trip test for each bead:
            expected_d → σ_bead(d, RI_bead) → AU_predicted = k × σ_bead
            Then compare AU_predicted vs AU_measured.
        
        Also performs an inverse round-trip using a **bead-RI** lookup table
        (NOT the EV LUT — beads have RI≈1.63, EVs have RI≈1.37, so the EV
        LUT would return wrong diameters for beads by design).
        
        A bead passes if: |recovered - expected| ≤ 2 × CV × expected / 100
        
        Args:
            bead_measurements: Dict of diameter_nm → AU (uses stored values if None)
            cv_map: Dict of diameter_nm → CV% (uses 5% default if not provided)
            
        Returns:
            Dict with per_bead results, overall pass/fail, and summary stats
        """
        if not self.calibrated or self.k_instrument is None:
            return {"validated": False, "reason": "Not calibrated"}
        
        if bead_measurements is None:
            bead_measurements = dict(zip(
                self.bead_diameters.tolist(),
                self.bead_fsc_measured.tolist()
            ))
        
        # Build a bead-RI LUT for the inverse round-trip
        # (beads have RI≈1.63, NOT the EV RI of 1.37)
        n_pts = 5000
        bead_lut_diameters = np.linspace(20.0, 500.0, n_pts)
        bead_lut_sigmas = np.zeros(n_pts)
        m_bead = complex(self.n_bead, 0)
        for i, d in enumerate(bead_lut_diameters):
            result = miepython.efficiencies(m_bead, d, self.wavelength_nm, n_env=self.n_medium)
            bead_lut_sigmas[i] = float(result[1]) * np.pi * (d / 2.0) ** 2
        
        per_bead = []
        all_pass = True
        max_error_pct = 0.0
        
        for expected_d, au in sorted(bead_measurements.items()):
            # Forward: expected_d → σ_bead → AU_predicted
            sigma_expected = self._compute_bead_sigma(expected_d)
            au_predicted = self.k_instrument * sigma_expected
            au_error_pct = 100 * abs(au_predicted - au) / au if au > 0 else 0
            
            # Inverse round-trip: AU → σ = AU/k → bead LUT → recovered_d
            sigma_measured = au / self.k_instrument
            idx = np.argmin(np.abs(bead_lut_sigmas - sigma_measured))
            recovered_d = float(bead_lut_diameters[idx])
            
            # Error metrics
            error_nm = recovered_d - expected_d
            error_pct = 100 * abs(error_nm) / expected_d if expected_d > 0 else 0
            max_error_pct = max(max_error_pct, error_pct)
            
            # Get CV for this bead (default 5% if not provided)
            cv = cv_map.get(expected_d, 5.0) if cv_map else 5.0
            tolerance_nm = 2 * cv * expected_d / 100
            passed = abs(error_nm) <= tolerance_nm
            
            if not passed:
                all_pass = False
            
            per_bead.append({
                "expected_nm": expected_d,
                "recovered_nm": round(recovered_d, 1),
                "error_nm": round(error_nm, 1),
                "error_pct": round(error_pct, 2),
                "au_measured": au,
                "au_predicted": round(au_predicted, 1),
                "au_error_pct": round(au_error_pct, 2),
                "cv_pct": cv,
                "tolerance_nm": round(tolerance_nm, 1),
                "passed": passed,
            })
            
            status = "✅" if passed else "❌"
            logger.info(
                f"   {status} {expected_d:.0f}nm: recovered={recovered_d:.1f}nm "
                f"(Δ={error_nm:+.1f}nm, {error_pct:.1f}%), "
                f"tolerance=±{tolerance_nm:.1f}nm"
            )
        
        result = {
            "validated": True,
            "all_passed": all_pass,
            "n_beads": len(per_bead),
            "n_passed": sum(1 for b in per_bead if b["passed"]),
            "n_failed": sum(1 for b in per_bead if not b["passed"]),
            "max_error_pct": round(max_error_pct, 2),
            "per_bead": per_bead,
        }
        
        if all_pass:
            logger.info(f"   ✅ Self-validation PASSED: all {len(per_bead)} beads within tolerance")
        else:
            n_failed = result["n_failed"]
            logger.warning(f"   ⚠️ Self-validation: {n_failed}/{len(per_bead)} beads FAILED tolerance check")
        
        return result
        
    def update_ev_ri(self, n_ev: float) -> None:
        """
        Update the EV refractive index and rebuild the inverse-Mie LUT.
        
        This allows per-request RI override without re-fitting the instrument
        constant k, which depends only on the beads and detector.
        
        Args:
            n_ev: New EV refractive index (e.g. 1.37, 1.40)
        """
        if abs(self.n_ev - n_ev) < 1e-6:
            return  # No change needed
        
        logger.info(f"Updating EV RI: {self.n_ev:.4f} → {n_ev:.4f}, rebuilding LUT")
        self.n_ev = n_ev
        # Invalidate cached LUT so it rebuilds with new RI
        self._ev_lut_diameters = None
        self._ev_lut_sigmas = None
        self._build_ev_lut()
    
    def predict_diameter(
        self,
        fsc_intensity: float,
        min_diameter: float = 20.0,
        max_diameter: float = 500.0
    ) -> Tuple[float, bool]:
        """
        Predict EV diameter from measured AU/FSC using k-based calibration.
        
        Pipeline: AU → σ_ev = AU/k → d_EV = inverse_Mie(σ_ev, RI_ev)
        
        Args:
            fsc_intensity: Measured AU from flow cytometer
            min_diameter: Minimum valid diameter (nm)
            max_diameter: Maximum valid diameter (nm)
        
        Returns:
            Tuple of (diameter_nm, in_range)
        """
        if not self.calibrated or self.k_instrument is None:
            raise RuntimeError("Calibrator not fitted. Call fit_from_beads() first.")
        
        if self._ev_lut_diameters is None:
            self._build_ev_lut()
        
        # AU → σ_ev
        sigma_ev = fsc_intensity / self.k_instrument
        
        if sigma_ev <= 0:
            return min_diameter, False
        
        # σ_ev → d_EV via LUT
        idx = np.argmin(np.abs(self._ev_lut_sigmas - sigma_ev))
        diameter = float(self._ev_lut_diameters[idx])
        
        # Check if within calibrated range
        fsc_min = float(self.bead_fsc_measured.min()) if len(self.bead_fsc_measured) > 0 else 0
        fsc_max = float(self.bead_fsc_measured.max()) if len(self.bead_fsc_measured) > 0 else np.inf
        in_range = fsc_min <= fsc_intensity <= fsc_max
        
        return diameter, in_range
    
    def predict_batch(
        self,
        fsc_intensities: np.ndarray,
        min_diameter: float = 20.0,
        max_diameter: float = 500.0,
        show_progress: bool = False
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Batch prediction for large datasets (vectorized, fast).
        
        Args:
            fsc_intensities: Array of measured AU values
            min_diameter: Minimum valid diameter (nm)
            max_diameter: Maximum valid diameter (nm)
            show_progress: Log progress for large arrays
        
        Returns:
            Tuple of (diameters, in_range_mask)
        """
        if not self.calibrated or self.k_instrument is None:
            raise RuntimeError("Calibrator not fitted. Call fit_from_beads() first.")
        
        if self._ev_lut_diameters is None:
            self._build_ev_lut()
        
        fsc_intensities = np.asarray(fsc_intensities)
        n = len(fsc_intensities)
        
        if show_progress and n > 1000:
            logger.info(f"🔄 Sizing {n:,} particles...")
        
        # Vectorized: AU → σ_ev → d_EV
        sigma_ev = fsc_intensities / self.k_instrument
        
        diameters = np.zeros(n)
        for i, sigma in enumerate(sigma_ev):
            if sigma <= 0 or np.isnan(sigma):
                diameters[i] = np.nan
            else:
                idx = np.argmin(np.abs(self._ev_lut_sigmas - sigma))
                diameters[i] = self._ev_lut_diameters[idx]
        
        # Range check
        fsc_min = float(self.bead_fsc_measured.min()) if len(self.bead_fsc_measured) > 0 else 0
        fsc_max = float(self.bead_fsc_measured.max()) if len(self.bead_fsc_measured) > 0 else np.inf
        in_range = (fsc_intensities >= fsc_min * 0.5) & (fsc_intensities <= fsc_max * 2.0)
        
        if show_progress and n > 1000:
            valid = np.isfinite(diameters)
            logger.info(
                f"✅ Sizing complete: {valid.sum():,} valid, "
                f"D50={np.nanmedian(diameters[valid]):.1f}nm"
            )
        
        return diameters, in_range
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """Get calibration diagnostics for quality assessment."""
        if not self.calibrated:
            return {"calibrated": False}
        
        result = {
            "calibrated": True,
            "method": "k-based (AU = k × σ_sca)",
            "k_instrument": self.k_instrument,
            "k_std": self.k_std,
            "k_cv_pct": self.k_cv_pct,
            "n_beads": len(self.bead_diameters),
            "bead_sizes_nm": self.bead_diameters.tolist() if len(self.bead_diameters) > 0 else [],
            "calibrated_range_fsc": [
                float(self.bead_fsc_measured.min()),
                float(self.bead_fsc_measured.max())
            ] if len(self.bead_fsc_measured) > 0 else [],
            "calibrated_range_diameter": [
                float(self.bead_diameters.min()),
                float(self.bead_diameters.max())
            ] if len(self.bead_diameters) > 0 else [],
            "wavelength_nm": self.wavelength_nm,
            "n_bead": self.n_bead,
            "n_ev": self.n_ev,
            "n_medium": self.n_medium,
        }
        
        # Include self-validation results if available
        if hasattr(self, '_self_validation_results') and self._self_validation_results:
            result["self_validation"] = self._self_validation_results
        
        return result


# Demo and testing
if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("🔬 MIE SCATTERING MODULE - PRODUCTION IMPLEMENTATION")
    logger.info("=" * 80)
    
    # Demo 1: Basic Mie calculator
    logger.info("\n📊 Demo 1: Calculate scatter for 80nm exosome")
    calc = MieScatterCalculator(wavelength_nm=488, n_particle=1.40, n_medium=1.33)
    result = calc.calculate_scattering_efficiency(80)
    logger.info(f"  Q_sca: {result.Q_sca:.4f}")
    logger.info(f"  FSC proxy: {result.forward_scatter:.2f}")
    logger.info(f"  Asymmetry g: {result.g:.4f}")
    
    # Demo 2: Inverse problem
    logger.info("\n🔍 Demo 2: Find size from measured FSC")
    measured_fsc = result.forward_scatter  # Use calculated value
    diameter, success = calc.diameter_from_scatter(measured_fsc)
    logger.info(f"  Input: FSC = {measured_fsc:.2f}")
    logger.info(f"  Output: diameter = {diameter:.1f} nm")
    logger.info(f"  Converged: {success}")
    
    # Demo 3: Wavelength response
    logger.info("\n🌈 Demo 3: Wavelength-dependent scatter (80nm EV)")
    response = calc.calculate_wavelength_response(80)
    for wavelength, intensity in response.items():
        logger.info(f"  {wavelength}: FSC = {intensity:.2f}")
    blue_red_ratio = response['488nm'] / response['633nm']
    logger.info(f"  Blue/Red ratio: {blue_red_ratio:.2f}x")
    
    # Demo 4: Batch processing
    logger.info("\n⚡ Demo 4: Batch calculate (1000 particles)")
    diameters = np.linspace(30, 150, 1000)
    fsc_array = calc.batch_calculate(diameters, show_progress=True)
    logger.info(f"  FSC range: {fsc_array.min():.1f} - {fsc_array.max():.1f}")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ Mie Scattering Module: Production Ready!")
    logger.info("📋 Next: Implement FCMPASSCalibrator (Days 2-3)")
    logger.info("=" * 80)
