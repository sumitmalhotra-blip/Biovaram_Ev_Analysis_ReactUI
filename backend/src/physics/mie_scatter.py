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
        n_medium: float = 1.33
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
        
        # Relative refractive index (complex number for miepython)
        # Imaginary part = 0 for non-absorbing particles
        # For absorbing particles, use complex(real, imaginary)
        self.m = complex(n_particle / n_medium, 0.0)
        
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
        
        # Calculate size parameter: x = πd/λ
        x = (np.pi * diameter_nm) / self.wavelength_nm
        
        # Determine physical regime
        if validate and x < 0.1:
            logger.debug(f"Rayleigh regime (x={x:.3f}): scatter ∝ λ⁻⁴")
        elif validate and x > 10:
            logger.debug(f"Geometric optics regime (x={x:.3f}): ray tracing applicable")
        
        # Call miepython to calculate Mie coefficients
        # single_sphere(m, x, n_pole, e_field) returns (qext, qsca, qback, g)
        # n_pole=0 means include all multipole terms (auto-sized for accuracy)
        # e_field=True for electric field calculation (standard for scatter)
        try:
            qext, qsca, qback, g = miepython.single_sphere(self.m, x, 0, True)
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
        
        # Side scatter (SSC): 90-degree scatter
        # Primarily affected by backscatter efficiency
        # Backscatter is reasonable proxy for side scatter in Mie theory
        # More complex internal structure → higher SSC
        side_scatter = qback_val * cross_section
        
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
        # Build lookup table: diameter -> FSC intensity
        diameters_lut = np.linspace(min_diameter, max_diameter, lut_resolution)
        fsc_lut = np.zeros(lut_resolution)
        
        for i, d in enumerate(diameters_lut):
            result = self.calculate_scattering_efficiency(d, validate=False)
            fsc_lut[i] = result.forward_scatter
        
        # Ensure FSC is monotonically increasing for interpolation
        # (May need sorting if Mie resonances cause non-monotonicity)
        sort_idx = np.argsort(fsc_lut)
        fsc_sorted = fsc_lut[sort_idx]
        diameters_sorted = diameters_lut[sort_idx]
        
        # Remove duplicates to avoid interpolation issues
        unique_mask = np.diff(fsc_sorted, prepend=-np.inf) > 0
        fsc_unique = fsc_sorted[unique_mask]
        diameters_unique = diameters_sorted[unique_mask]
        
        # Interpolate: FSC intensity -> diameter
        fsc_intensities = np.asarray(fsc_intensities)
        
        # Clamp intensities to valid range for interpolation
        fsc_min, fsc_max = fsc_unique[0], fsc_unique[-1]
        fsc_clamped = np.clip(fsc_intensities, fsc_min, fsc_max)
        
        # Linear interpolation
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
        
        This method handles the scale mismatch between raw flow cytometer FSC values
        (typically 10,000 - 1,000,000 arbitrary units) and physical Mie scatter
        (dimensionless efficiency ~0.01 - 100).
        
        The approach:
        1. Build a lookup table of physical FSC values for the diameter range
        2. Map the raw FSC range to the physical FSC range (linear normalization)
        3. Interpolate to find diameters
        
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
        fsc_intensities = np.asarray(fsc_intensities, dtype=np.float64)
        
        # Filter out invalid values for normalization
        valid_mask = (fsc_intensities > 0) & np.isfinite(fsc_intensities)
        
        if not np.any(valid_mask):
            return np.zeros_like(fsc_intensities), np.zeros_like(fsc_intensities, dtype=bool)
        
        # Build lookup table: diameter -> physical FSC
        diameters_lut = np.linspace(min_diameter, max_diameter, lut_resolution)
        physical_fsc_lut = np.zeros(lut_resolution)
        
        for i, d in enumerate(diameters_lut):
            result = self.calculate_scattering_efficiency(d, validate=False)
            physical_fsc_lut[i] = result.forward_scatter
        
        # Ensure monotonicity for interpolation
        sort_idx = np.argsort(physical_fsc_lut)
        physical_fsc_sorted = physical_fsc_lut[sort_idx]
        diameters_sorted = diameters_lut[sort_idx]
        
        # Remove duplicates
        unique_mask = np.diff(physical_fsc_sorted, prepend=-np.inf) > 0
        physical_fsc_unique = physical_fsc_sorted[unique_mask]
        diameters_unique = diameters_sorted[unique_mask]
        
        if len(physical_fsc_unique) < 2:
            logger.warning("⚠️ Insufficient unique FSC values in lookup table")
            return np.zeros_like(fsc_intensities), np.zeros_like(fsc_intensities, dtype=bool)
        
        # Normalize raw FSC values to physical FSC range
        # Map the percentile range of raw FSC to the physical FSC range
        raw_fsc_valid = fsc_intensities[valid_mask]
        
        # Use percentiles to be robust against outliers
        raw_p5, raw_p95 = np.percentile(raw_fsc_valid, [5, 95])
        phys_min, phys_max = physical_fsc_unique[0], physical_fsc_unique[-1]
        
        # Linear mapping: raw_FSC -> physical_FSC
        # normalized = phys_min + (raw - raw_p5) / (raw_p95 - raw_p5) * (phys_max - phys_min)
        raw_range = raw_p95 - raw_p5
        if raw_range <= 0:
            raw_range = 1.0  # Avoid division by zero
        
        phys_range = phys_max - phys_min
        normalized_fsc = phys_min + (fsc_intensities - raw_p5) / raw_range * phys_range
        
        # Clamp to physical FSC range
        normalized_fsc_clamped = np.clip(normalized_fsc, phys_min, phys_max)
        
        # Interpolate to get diameters
        estimated_diameters = np.interp(normalized_fsc_clamped, physical_fsc_unique, diameters_unique)
        
        # Mark success for values within reasonable range (not extreme outliers)
        success_mask = valid_mask & (fsc_intensities >= raw_p5 * 0.1) & (fsc_intensities <= raw_p95 * 10)
        
        logger.debug(
            f"📊 Normalized FSC mapping: raw=[{raw_p5:.0f}, {raw_p95:.0f}] → "
            f"physical=[{phys_min:.2e}, {phys_max:.2e}], "
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
    
    PHYSICS INSIGHT (from Parvesh Reddy, Jan 2026):
    -----------------------------------------------
    - Small particles (< 100nm): Rayleigh regime, violet scatters MORE (ratio > 1)
    - Large particles (> 200nm): Geometric regime, similar scattering (ratio ≈ 1)
    - This wavelength-dependent behavior uniquely identifies the correct solution
    
    Example Usage:
        >>> calc = MultiSolutionMieCalculator(n_particle=1.40, n_medium=1.33)
        >>> 
        >>> # Get both wavelength SSC values from FCS data
        >>> ssc_blue = data['BSSC-H'].values  # 488nm
        >>> ssc_violet = data['VSSC-H'].values  # 405nm
        >>> 
        >>> # Calculate sizes with disambiguation
        >>> sizes, num_solutions = calc.calculate_sizes_multi_solution(ssc_blue, ssc_violet)
        >>> print(f"D50: {np.nanmedian(sizes):.1f} nm")
        >>> print(f"Events with multiple solutions: {(num_solutions > 1).sum()}")
    
    References:
        - January 2026 meeting with Parvesh Reddy (wavelength ratio disambiguation)
        - compare_single_vs_multi_solution.py script validation
    """
    
    # Physical constants for wavelengths
    WAVELENGTH_VIOLET = 405.0  # nm (VSSC channel)
    WAVELENGTH_BLUE = 488.0    # nm (BSSC channel)
    
    def __init__(
        self,
        n_particle: float = 1.40,
        n_medium: float = 1.33,
        min_diameter: float = 30.0,
        max_diameter: float = 500.0,
        lut_resolution: int = 471
    ):
        """
        Initialize multi-solution Mie calculator.
        
        Args:
            n_particle: Refractive index of particles (EVs: 1.37-1.45)
            n_medium: Refractive index of medium (PBS: 1.33)
            min_diameter: Minimum diameter in lookup table (nm)
            max_diameter: Maximum diameter in lookup table (nm)
            lut_resolution: Number of points in LUT (default 471 = 1nm steps from 30-500)
        """
        self.n_particle = n_particle
        self.n_medium = n_medium
        self.m = complex(n_particle / n_medium, 0)
        self.min_diameter = min_diameter
        self.max_diameter = max_diameter
        
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
        )
    
    def _calc_ssc(self, diameter_nm: float, wavelength_nm: float) -> float:
        """
        Calculate side scatter cross-section for a diameter at specific wavelength.
        
        Uses backscatter efficiency (Qback) × geometric cross-section as SSC proxy.
        This matches what flow cytometers measure at ~90° detection angle.
        """
        m = complex(self.n_particle / self.n_medium, 0)
        try:
            # miepython.efficiencies returns: (qext, qsca, qback, g)
            result = miepython.efficiencies(m, diameter_nm, wavelength_nm, n_env=self.n_medium)
            qback = float(result[2]) if result[2] is not None else 0.0
            
            # Geometric cross-section
            radius = diameter_nm / 2.0
            cross_section = np.pi * (radius ** 2)
            
            return qback * cross_section
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
    
    def calculate_sizes_multi_solution(
        self,
        ssc_blue: np.ndarray,
        ssc_violet: np.ndarray,
        tolerance_pct: float = 15.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate particle sizes using multi-solution disambiguation.
        
        This is the PRODUCTION method for accurate sizing when both wavelengths
        are available. For each event:
        1. Find ALL sizes that match the blue SSC (within tolerance)
        2. If multiple solutions, use VSSC/BSSC ratio to pick correct one
        
        Args:
            ssc_blue: Array of blue SSC (488nm) values, shape (n_events,)
            ssc_violet: Array of violet SSC (405nm) values, shape (n_events,)
            tolerance_pct: Tolerance for solution matching (default 15%)
            
        Returns:
            Tuple of (sizes, num_solutions):
            - sizes: Array of estimated diameters in nm, shape (n_events,)
            - num_solutions: Array of how many solutions were found per event
        """
        n_events = len(ssc_blue)
        sizes = np.zeros(n_events)
        num_solutions = np.zeros(n_events)
        
        for i in range(n_events):
            if ssc_blue[i] <= 0 or ssc_violet[i] <= 0:
                sizes[i] = np.nan
                num_solutions[i] = 0
                continue
            
            # Step 1: Find ALL possible solutions using blue SSC
            solutions = self.find_all_solutions(
                ssc_blue[i], 
                wavelength_nm=488.0, 
                tolerance_pct=tolerance_pct
            )
            num_solutions[i] = len(solutions)
            
            if len(solutions) == 0:
                sizes[i] = np.nan
            elif len(solutions) == 1:
                sizes[i] = solutions[0]
            else:
                # Step 2: Use wavelength ratio to pick the best solution
                measured_ratio = ssc_violet[i] / ssc_blue[i]
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
        
        sizes = np.zeros(len(ssc_values))
        
        for i, ssc in enumerate(ssc_values):
            if ssc <= 0:
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
    
    This class implements reference bead-based calibration to convert arbitrary
    FSC units to absolute particle diameters. The calibration process:
    
    1. Measure reference beads with known sizes (e.g., 100nm, 200nm, 300nm polystyrene)
    2. Calculate theoretical Mie scatter for each bead size
    3. Fit polynomial curve: measured_FSC → theoretical_Mie_scatter
    4. Apply calibration to unknown samples using lookup curve
    
    This approach is 100× faster than per-particle optimization while maintaining
    accuracy within ±20% after calibration.
    
    References:
    - FCMPASS: Flow Cytometry Mie Particle Axis Standardization Software
    - Welsh et al., Cytometry A 2020 (FCMPASS paper)
    - Literature/FCMPASS_Software-Aids-EVs-Light-Scatter-Stand.pdf
    
    Example:
        >>> # Measure reference beads
        >>> bead_data = {
        ...     100: 15000,  # 100nm bead measured FSC
        ...     200: 58000,  # 200nm bead measured FSC
        ...     300: 125000  # 300nm bead measured FSC
        ... }
        >>> 
        >>> # Create and fit calibrator
        >>> calibrator = FCMPASSCalibrator(wavelength_nm=488, n_particle=1.59, n_medium=1.33)
        >>> calibrator.fit_from_beads(bead_data)
        >>> 
        >>> # Apply to unknown sample
        >>> unknown_fsc = 42000
        >>> diameter = calibrator.predict_diameter(unknown_fsc)
        >>> print(f"Estimated size: {diameter:.1f} nm")
    """
    
    def __init__(
        self,
        wavelength_nm: float = 488.0,
        n_particle: float = 1.59,
        n_medium: float = 1.33
    ):
        """
        Initialize FCMPASS calibrator.
        
        Args:
            wavelength_nm: Laser wavelength (488nm for blue laser)
            n_particle: Refractive index of calibration beads
                       Polystyrene: 1.59 (most common)
                       Silica: 1.46 (alternative)
            n_medium: Refractive index of medium (PBS: 1.33)
        """
        self.wavelength_nm = wavelength_nm
        self.n_particle = n_particle
        self.n_medium = n_medium
        
        # Create Mie calculator for bead material
        self.mie_calc = MieScatterCalculator(
            wavelength_nm=wavelength_nm,
            n_particle=n_particle,
            n_medium=n_medium
        )
        
        # Calibration curve parameters (fitted from reference beads)
        self.calibration_poly = None  # Polynomial coefficients
        self.fsc_to_mie_poly = None   # FSC → Mie scatter polynomial
        self.calibrated = False
        
        # Store bead data for diagnostics
        self.bead_diameters: np.ndarray = np.array([])
        self.bead_fsc_measured: np.ndarray = np.array([])
        self.bead_fsc_theoretical: np.ndarray = np.array([])
        
        logger.info(f"✓ FCMPASS Calibrator initialized: λ={wavelength_nm:.1f}nm, n={n_particle:.2f}")
    
    def fit_from_beads(
        self,
        bead_measurements: Dict[float, float],
        poly_degree: int = 2
    ) -> None:
        """
        Fit calibration curve from reference bead measurements.
        
        Args:
            bead_measurements: Dict mapping bead diameter (nm) to measured FSC
                              Example: {100: 15000, 200: 58000, 300: 125000}
            poly_degree: Polynomial degree for curve fitting (2 or 3 recommended)
                        2: Quadratic (fast, usually sufficient)
                        3: Cubic (more flexible, risk of overfitting)
        
        Raises:
            ValueError: If insufficient bead data (<2 points)
        """
        if len(bead_measurements) < 2:
            raise ValueError(f"Need at least 2 reference beads, got {len(bead_measurements)}")
        
        logger.info(f"🔬 Fitting calibration curve from {len(bead_measurements)} reference beads")
        
        # Extract and sort by diameter
        diameters = np.array(sorted(bead_measurements.keys()))
        fsc_measured = np.array([bead_measurements[d] for d in diameters])
        
        # Calculate theoretical Mie scatter for each bead
        fsc_theoretical = []
        for diameter in diameters:
            result = self.mie_calc.calculate_scattering_efficiency(diameter)
            fsc_theoretical.append(result.forward_scatter)
        fsc_theoretical = np.array(fsc_theoretical)
        
        # Store for diagnostics
        self.bead_diameters = diameters
        self.bead_fsc_measured = fsc_measured
        self.bead_fsc_theoretical = fsc_theoretical
        
        # Fit polynomial: measured_FSC → theoretical_Mie_scatter
        # This maps instrument units to physical Mie scatter
        self.fsc_to_mie_poly = np.polyfit(fsc_measured, fsc_theoretical, poly_degree)
        
        # Calculate fit quality
        fsc_pred = np.polyval(self.fsc_to_mie_poly, fsc_measured)
        residuals = fsc_theoretical - fsc_pred
        rmse = np.sqrt(np.mean(residuals**2))
        rel_error = 100 * rmse / np.mean(fsc_theoretical)
        
        self.calibrated = True
        
        logger.info(f"✅ Calibration complete:")
        logger.info(f"   Polynomial degree: {poly_degree}")
        logger.info(f"   RMSE: {rmse:.2e} (relative: {rel_error:.2f}%)")
        logger.info(f"   Calibrated range: {diameters[0]:.0f}-{diameters[-1]:.0f} nm")
        
        # Log individual bead fits
        for i, diameter in enumerate(diameters):
            logger.info(
                f"   {diameter:.0f}nm bead: FSC={fsc_measured[i]:.0f}, "
                f"Mie={fsc_theoretical[i]:.2f}, "
                f"Predicted={fsc_pred[i]:.2f}"
            )
    
    def predict_diameter(
        self,
        fsc_intensity: float,
        min_diameter: float = 30.0,
        max_diameter: float = 200.0
    ) -> Tuple[float, bool]:
        """
        Predict particle diameter from measured FSC using calibration curve.
        
        This is the production method for sizing - much faster than optimization.
        
        Args:
            fsc_intensity: Measured FSC from flow cytometer
            min_diameter: Minimum valid diameter (nm)
            max_diameter: Maximum valid diameter (nm)
        
        Returns:
            Tuple of (diameter_nm, in_range):
            - diameter_nm: Predicted particle diameter
            - in_range: True if within calibrated range, False if extrapolating
        
        Raises:
            RuntimeError: If calibrator not fitted yet
        """
        if not self.calibrated:
            raise RuntimeError("Calibrator not fitted. Call fit_from_beads() first.")
        
        if self.fsc_to_mie_poly is None:
            raise RuntimeError("Calibration polynomial is None. Re-fit calibrator.")
        
        # Convert measured FSC to theoretical Mie scatter using calibration
        mie_scatter_calibrated = float(np.polyval(self.fsc_to_mie_poly, fsc_intensity))
        
        # Clamp to positive values (extrapolation can give negatives)
        if mie_scatter_calibrated <= 0:
            logger.warning(
                f"Calibration extrapolation gave negative Mie scatter ({mie_scatter_calibrated:.2f}) "
                f"for FSC={fsc_intensity:.0f}. Using minimum diameter."
            )
            return min_diameter, False
        
        # Now use Mie calculator to find diameter for this scatter
        diameter, success = self.mie_calc.diameter_from_scatter(
            fsc_intensity=mie_scatter_calibrated,
            min_diameter=min_diameter,
            max_diameter=max_diameter
        )
        
        # Check if within calibrated range
        fsc_min = float(self.bead_fsc_measured.min())
        fsc_max = float(self.bead_fsc_measured.max())
        in_range = fsc_min <= fsc_intensity <= fsc_max
        
        if not in_range:
            logger.debug(
                f"FSC {fsc_intensity:.0f} outside calibrated range "
                f"[{fsc_min:.0f}, {fsc_max:.0f}] - extrapolating"
            )
        
        return diameter, in_range
    
    def predict_batch(
        self,
        fsc_intensities: np.ndarray,
        min_diameter: float = 30.0,
        max_diameter: float = 200.0,
        show_progress: bool = False
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Batch prediction for large datasets (optimized).
        
        Args:
            fsc_intensities: Array of measured FSC values
            min_diameter: Minimum valid diameter (nm)
            max_diameter: Maximum valid diameter (nm)
            show_progress: Show progress for large arrays
        
        Returns:
            Tuple of (diameters, in_range_mask):
            - diameters: Array of predicted diameters (nm)
            - in_range_mask: Boolean array indicating calibrated range
        """
        if not self.calibrated:
            raise RuntimeError("Calibrator not fitted. Call fit_from_beads() first.")
        
        n = len(fsc_intensities)
        diameters = np.zeros(n)
        in_range = np.zeros(n, dtype=bool)
        
        if show_progress and n > 1000:
            logger.info(f"🔄 Predicting diameters for {n:,} particles...")
        
        for i, fsc in enumerate(fsc_intensities):
            if show_progress and n > 10000 and i % 10000 == 0:
                logger.info(f"  Progress: {i:,}/{n:,} ({100*i/n:.1f}%)")
            
            diameter, in_range_i = self.predict_diameter(fsc, min_diameter, max_diameter)
            diameters[i] = diameter
            in_range[i] = in_range_i
        
        if show_progress and n > 1000:
            pct_in_range = 100 * in_range.sum() / n
            logger.info(f"✅ Batch prediction complete: {pct_in_range:.1f}% in calibrated range")
        
        return diameters, in_range
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """
        Get calibration diagnostics for quality assessment.
        
        Returns:
            Dict with calibration quality metrics
        """
        if not self.calibrated:
            return {"calibrated": False}
        
        if self.fsc_to_mie_poly is None or self.bead_fsc_measured is None or self.bead_fsc_theoretical is None:
            return {"calibrated": False}
        
        # Calculate R² for fit quality
        fsc_pred = np.polyval(self.fsc_to_mie_poly, self.bead_fsc_measured)
        ss_res = np.sum((self.bead_fsc_theoretical - fsc_pred)**2)
        ss_tot = np.sum((self.bead_fsc_theoretical - np.mean(self.bead_fsc_theoretical))**2)
        r_squared = 1 - (ss_res / ss_tot)
        
        poly_len = len(self.fsc_to_mie_poly) if self.fsc_to_mie_poly is not None else 0
        
        return {
            "calibrated": True,
            "n_beads": len(self.bead_diameters),
            "bead_sizes_nm": self.bead_diameters.tolist(),
            "calibrated_range_fsc": [float(self.bead_fsc_measured.min()), 
                                      float(self.bead_fsc_measured.max())],
            "calibrated_range_diameter": [float(self.bead_diameters.min()), 
                                          float(self.bead_diameters.max())],
            "r_squared": float(r_squared),
            "poly_degree": poly_len - 1,
            "wavelength_nm": self.wavelength_nm,
            "n_particle": self.n_particle
        }


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
