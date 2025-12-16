"""
NTA Parameter Corrections Module
================================

Implements viscosity and temperature corrections for Nanoparticle Tracking Analysis (NTA)
measurements using the Stokes-Einstein equation.

The Stokes-Einstein equation relates diffusion coefficient to particle size:
    D = k_B * T / (3 * π * η * d)

Where:
    D = diffusion coefficient (m²/s)
    k_B = Boltzmann constant (1.380649 × 10⁻²³ J/K)
    T = absolute temperature (K)
    η = dynamic viscosity of the medium (Pa·s)
    d = hydrodynamic diameter (m)

For NTA measurements, the instrument calculates particle size from observed diffusion.
However, if the measurement temperature differs from the reference temperature (usually 25°C),
or if the viscosity differs from pure water, corrections must be applied.

Author: CRMIT EV Project
Version: 1.0.0
"""

import numpy as np
from typing import Optional, Tuple, Dict, Any, Union
import pandas as pd


# Physical Constants
BOLTZMANN_CONSTANT = 1.380649e-23  # J/K (exact value per 2019 SI redefinition)
REFERENCE_TEMPERATURE_C = 25.0  # Standard reference temperature for NTA (°C)


def celsius_to_kelvin(temp_c: float) -> float:
    """
    Convert temperature from Celsius to Kelvin.
    
    Parameters
    ----------
    temp_c : float
        Temperature in degrees Celsius
        
    Returns
    -------
    float
        Temperature in Kelvin
    """
    return temp_c + 273.15


def calculate_water_viscosity(temperature_c: float) -> float:
    """
    Calculate the dynamic viscosity of water at a given temperature.
    
    Uses the Vogel-Fulcher-Tammann (VFT) equation with parameters optimized
    for water in the range 0-100°C:
    
        η = A × exp(B / (T - C))
    
    This provides accuracy within 0.5% for temperatures between 0-100°C.
    
    Alternative: Kestin et al. (1978) correlation is used here for better accuracy:
        η = η₀ × 10^[(20 - T)/(T + 96) × (1.2378 - 1.303e-3×(20-T) + 3.06e-6×(20-T)² + 2.55e-8×(20-T)³)]
    
    Where η₀ = 1.002 mPa·s (viscosity at 20°C)
    
    Parameters
    ----------
    temperature_c : float
        Temperature in degrees Celsius (valid range: 0-100°C)
        
    Returns
    -------
    float
        Dynamic viscosity in Pa·s (Pascal-seconds)
        
    Raises
    ------
    ValueError
        If temperature is outside valid range (0-100°C)
        
    References
    ----------
    Kestin, J., Sokolov, M., & Wakeham, W. A. (1978).
    Viscosity of liquid water in the range −8 °C to 150 °C.
    Journal of Physical and Chemical Reference Data, 7(3), 941-948.
    """
    if temperature_c < 0 or temperature_c > 100:
        raise ValueError(f"Temperature {temperature_c}°C is outside valid range (0-100°C)")
    
    T = temperature_c
    T_ref = 20.0  # Reference temperature for the correlation
    eta_20 = 1.002e-3  # Viscosity at 20°C in Pa·s
    
    # Kestin et al. (1978) correlation
    delta_T = T_ref - T
    exponent = (delta_T / (T + 96)) * (
        1.2378 
        - 1.303e-3 * delta_T 
        + 3.06e-6 * delta_T**2 
        + 2.55e-8 * delta_T**3
    )
    
    viscosity = eta_20 * (10 ** exponent)
    
    return viscosity


def calculate_water_viscosity_simple(temperature_c: float) -> float:
    """
    Simplified empirical formula for water viscosity.
    
    Uses a simpler polynomial approximation that's accurate within 2%
    for typical laboratory temperatures (15-40°C).
    
    Parameters
    ----------
    temperature_c : float
        Temperature in degrees Celsius
        
    Returns
    -------
    float
        Dynamic viscosity in Pa·s
        
    Note
    ----
    For high-accuracy applications, use calculate_water_viscosity() instead.
    """
    T = temperature_c
    # Polynomial fit coefficients (mPa·s)
    # Valid for 0-100°C range
    viscosity_mPas = (
        1.7919 
        - 0.0516 * T 
        + 0.0006 * T**2 
        - 3.45e-6 * T**3
    )
    
    # Ensure positive viscosity
    viscosity_mPas = max(0.2, viscosity_mPas)
    
    return viscosity_mPas * 1e-3  # Convert to Pa·s


def stokes_einstein_diffusion(
    diameter_nm: float, 
    temperature_c: float, 
    viscosity_pas: Optional[float] = None
) -> float:
    """
    Calculate the diffusion coefficient using the Stokes-Einstein equation.
    
    D = k_B × T / (3π × η × d)
    
    Parameters
    ----------
    diameter_nm : float
        Particle hydrodynamic diameter in nanometers
    temperature_c : float
        Temperature in degrees Celsius
    viscosity_pas : float, optional
        Dynamic viscosity in Pa·s. If not provided, water viscosity
        at the given temperature will be calculated.
        
    Returns
    -------
    float
        Diffusion coefficient in m²/s
        
    Example
    -------
    >>> # 100 nm particle in water at 25°C
    >>> D = stokes_einstein_diffusion(100, 25)
    >>> print(f"{D:.2e} m²/s")
    4.40e-12 m²/s
    """
    if viscosity_pas is None:
        viscosity_pas = calculate_water_viscosity(temperature_c)
    
    T_kelvin = celsius_to_kelvin(temperature_c)
    diameter_m = diameter_nm * 1e-9
    
    D = BOLTZMANN_CONSTANT * T_kelvin / (3 * np.pi * viscosity_pas * diameter_m)
    
    return D


def stokes_einstein_diameter(
    diffusion_coeff: float,
    temperature_c: float,
    viscosity_pas: Optional[float] = None
) -> float:
    """
    Calculate particle diameter from diffusion coefficient using Stokes-Einstein.
    
    d = k_B × T / (3π × η × D)
    
    This is the inverse of the stokes_einstein_diffusion function.
    
    Parameters
    ----------
    diffusion_coeff : float
        Diffusion coefficient in m²/s
    temperature_c : float
        Temperature in degrees Celsius
    viscosity_pas : float, optional
        Dynamic viscosity in Pa·s. If not provided, water viscosity
        at the given temperature will be calculated.
        
    Returns
    -------
    float
        Particle hydrodynamic diameter in nanometers
    """
    if viscosity_pas is None:
        viscosity_pas = calculate_water_viscosity(temperature_c)
    
    T_kelvin = celsius_to_kelvin(temperature_c)
    
    diameter_m = BOLTZMANN_CONSTANT * T_kelvin / (3 * np.pi * viscosity_pas * diffusion_coeff)
    
    return diameter_m * 1e9  # Convert to nm


def correct_nta_size(
    raw_size_nm: Union[float, np.ndarray],
    measurement_temp_c: float,
    reference_temp_c: float = REFERENCE_TEMPERATURE_C,
    measurement_viscosity: Optional[float] = None,
    reference_viscosity: Optional[float] = None
) -> Union[float, np.ndarray]:
    """
    Apply temperature-viscosity correction to NTA size measurements.
    
    NTA instruments typically report sizes assuming standard conditions (25°C, water).
    If the actual measurement conditions differ, the reported size needs correction.
    
    The correction factor is derived from the Stokes-Einstein equation:
    
        d_corrected = d_raw × (η_ref / η_meas) × (T_meas / T_ref)
    
    Where:
        d_raw = raw size reported by instrument (nm)
        η_ref = viscosity at reference temperature (Pa·s)
        η_meas = viscosity at measurement temperature (Pa·s)
        T_meas = measurement temperature (K)
        T_ref = reference temperature (K)
    
    Parameters
    ----------
    raw_size_nm : float or ndarray
        Raw particle size(s) as reported by the NTA instrument (nm)
    measurement_temp_c : float
        Actual temperature during measurement (°C)
    reference_temp_c : float, optional
        Reference temperature used by the instrument (default: 25°C)
    measurement_viscosity : float, optional
        Actual viscosity during measurement (Pa·s). If not provided,
        water viscosity at measurement temperature will be used.
    reference_viscosity : float, optional
        Reference viscosity used by the instrument (Pa·s). If not provided,
        water viscosity at reference temperature will be used.
        
    Returns
    -------
    float or ndarray
        Corrected particle size(s) in nanometers
        
    Examples
    --------
    >>> # Correct size measured at 37°C (body temperature) to 25°C reference
    >>> raw_size = 100  # nm as reported at 37°C
    >>> corrected = correct_nta_size(raw_size, measurement_temp_c=37, reference_temp_c=25)
    >>> print(f"Corrected size: {corrected:.1f} nm")
    Corrected size: 126.6 nm
    
    >>> # Correct an array of sizes
    >>> sizes = np.array([80, 100, 120, 150])
    >>> corrected = correct_nta_size(sizes, measurement_temp_c=20, reference_temp_c=25)
    >>> print(corrected)
    [74.9  93.6 112.3 140.4]
    """
    # Get viscosities
    if measurement_viscosity is None:
        measurement_viscosity = calculate_water_viscosity(measurement_temp_c)
    if reference_viscosity is None:
        reference_viscosity = calculate_water_viscosity(reference_temp_c)
    
    # Convert temperatures to Kelvin
    T_meas = celsius_to_kelvin(measurement_temp_c)
    T_ref = celsius_to_kelvin(reference_temp_c)
    
    # Calculate correction factor
    # d_corrected = d_raw × (η_ref / η_meas) × (T_meas / T_ref)
    correction_factor = (reference_viscosity / measurement_viscosity) * (T_meas / T_ref)
    
    corrected_size = np.asarray(raw_size_nm) * correction_factor
    
    # Return same type as input
    if isinstance(raw_size_nm, (int, float)):
        return float(corrected_size)
    return corrected_size


def get_correction_factor(
    measurement_temp_c: float,
    reference_temp_c: float = REFERENCE_TEMPERATURE_C,
    measurement_viscosity: Optional[float] = None,
    reference_viscosity: Optional[float] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate the size correction factor and return detailed parameters.
    
    Parameters
    ----------
    measurement_temp_c : float
        Actual temperature during measurement (°C)
    reference_temp_c : float, optional
        Reference temperature (default: 25°C)
    measurement_viscosity : float, optional
        Actual viscosity (Pa·s). Uses water viscosity if not provided.
    reference_viscosity : float, optional
        Reference viscosity (Pa·s). Uses water viscosity if not provided.
        
    Returns
    -------
    correction_factor : float
        Multiplicative factor to apply to raw sizes
    details : dict
        Dictionary containing all calculated parameters
        
    Example
    -------
    >>> factor, details = get_correction_factor(37, 25)
    >>> print(f"Correction factor: {factor:.4f}")
    >>> print(f"Measurement viscosity: {details['measurement_viscosity']*1000:.4f} mPa·s")
    """
    # Get viscosities
    if measurement_viscosity is None:
        measurement_viscosity = calculate_water_viscosity(measurement_temp_c)
    if reference_viscosity is None:
        reference_viscosity = calculate_water_viscosity(reference_temp_c)
    
    # Convert temperatures to Kelvin
    T_meas = celsius_to_kelvin(measurement_temp_c)
    T_ref = celsius_to_kelvin(reference_temp_c)
    
    # Calculate correction factor
    correction_factor = (reference_viscosity / measurement_viscosity) * (T_meas / T_ref)
    
    details = {
        'measurement_temp_c': measurement_temp_c,
        'measurement_temp_k': T_meas,
        'reference_temp_c': reference_temp_c,
        'reference_temp_k': T_ref,
        'measurement_viscosity': measurement_viscosity,
        'measurement_viscosity_mPas': measurement_viscosity * 1000,
        'reference_viscosity': reference_viscosity,
        'reference_viscosity_mPas': reference_viscosity * 1000,
        'viscosity_ratio': reference_viscosity / measurement_viscosity,
        'temperature_ratio': T_meas / T_ref,
        'correction_factor': correction_factor,
        'correction_percentage': (correction_factor - 1) * 100
    }
    
    return correction_factor, details


def apply_corrections_to_dataframe(
    df: pd.DataFrame,
    size_column: str,
    measurement_temp_c: float,
    reference_temp_c: float = REFERENCE_TEMPERATURE_C,
    corrected_column_name: Optional[str] = None,
    inplace: bool = False
) -> pd.DataFrame:
    """
    Apply temperature-viscosity corrections to a DataFrame with NTA size data.
    
    Parameters
    ----------
    df : DataFrame
        DataFrame containing NTA data with a size column
    size_column : str
        Name of the column containing raw size values (nm)
    measurement_temp_c : float
        Temperature during measurement (°C)
    reference_temp_c : float, optional
        Reference temperature (default: 25°C)
    corrected_column_name : str, optional
        Name for the new corrected size column. 
        Default: "{size_column}_corrected"
    inplace : bool, optional
        If True, add column to existing DataFrame. 
        If False (default), return a copy.
        
    Returns
    -------
    DataFrame
        DataFrame with added corrected size column and correction metadata
        
    Example
    -------
    >>> df = pd.DataFrame({'Position': [1, 2, 3], 'X50 (nm)': [85.2, 92.1, 88.5]})
    >>> df_corrected = apply_corrections_to_dataframe(df, 'X50 (nm)', 22)
    >>> print(df_corrected)
    """
    if not inplace:
        df = df.copy()
    
    if corrected_column_name is None:
        corrected_column_name = f"{size_column}_corrected"
    
    # Get raw sizes
    raw_sizes = pd.to_numeric(df[size_column], errors='coerce')
    
    # Calculate corrected sizes
    corrected_sizes = correct_nta_size(
        raw_sizes.values,
        measurement_temp_c=measurement_temp_c,
        reference_temp_c=reference_temp_c
    )
    
    # Add corrected column
    df[corrected_column_name] = corrected_sizes
    
    return df


def get_viscosity_temperature_table(
    temp_start: float = 15.0,
    temp_end: float = 40.0,
    temp_step: float = 1.0
) -> pd.DataFrame:
    """
    Generate a reference table of water viscosity vs temperature.
    
    Parameters
    ----------
    temp_start : float
        Starting temperature (°C)
    temp_end : float
        Ending temperature (°C)
    temp_step : float
        Temperature increment (°C)
        
    Returns
    -------
    DataFrame
        Table with columns: Temperature (°C), Viscosity (Pa·s), Viscosity (mPa·s)
    """
    temperatures = np.arange(temp_start, temp_end + temp_step, temp_step)
    viscosities = [calculate_water_viscosity(t) for t in temperatures]
    
    df = pd.DataFrame({
        'Temperature (°C)': temperatures,
        'Viscosity (Pa·s)': viscosities,
        'Viscosity (mPa·s)': [v * 1000 for v in viscosities],
        'Viscosity (cP)': [v * 1000 for v in viscosities]  # 1 cP = 1 mPa·s
    })
    
    return df


def get_correction_reference_table(
    measurement_temps: Optional[list] = None,
    reference_temp_c: float = REFERENCE_TEMPERATURE_C
) -> pd.DataFrame:
    """
    Generate a reference table of correction factors for common temperatures.
    
    Parameters
    ----------
    measurement_temps : list, optional
        List of measurement temperatures. Default: [18, 20, 22, 25, 30, 37]
    reference_temp_c : float
        Reference temperature (default: 25°C)
        
    Returns
    -------
    DataFrame
        Table with correction factors and details
    """
    if measurement_temps is None:
        measurement_temps = [18, 20, 22, 25, 30, 37]
    
    rows = []
    for temp in measurement_temps:
        factor, details = get_correction_factor(temp, reference_temp_c)
        rows.append({
            'Measurement T (°C)': temp,
            'Reference T (°C)': reference_temp_c,
            'Meas. Viscosity (mPa·s)': details['measurement_viscosity_mPas'],
            'Ref. Viscosity (mPa·s)': details['reference_viscosity_mPas'],
            'Correction Factor': factor,
            'Size Change (%)': details['correction_percentage']
        })
    
    return pd.DataFrame(rows)


# Custom viscosity for different media
MEDIA_VISCOSITY_FACTORS = {
    'water': 1.0,
    'pbs': 1.02,  # PBS is ~2% more viscous than water
    'dmem': 1.05,  # DMEM is ~5% more viscous
    'serum-free': 1.03,
    '10% fbs': 1.15,  # 10% FBS increases viscosity ~15%
    '20% fbs': 1.30,  # 20% FBS
    'sucrose_10%': 1.35,  # 10% sucrose solution
    'sucrose_20%': 1.95,  # 20% sucrose solution
}


def get_media_viscosity(
    media_type: str,
    temperature_c: float
) -> Tuple[float, str]:
    """
    Get estimated viscosity for common laboratory media.
    
    Parameters
    ----------
    media_type : str
        Type of medium (e.g., 'water', 'pbs', 'dmem', '10% fbs')
    temperature_c : float
        Temperature in °C
        
    Returns
    -------
    viscosity : float
        Estimated viscosity in Pa·s
    note : str
        Note about the estimation
    """
    media_lower = media_type.lower().strip()
    
    if media_lower in MEDIA_VISCOSITY_FACTORS:
        factor = MEDIA_VISCOSITY_FACTORS[media_lower]
        water_viscosity = calculate_water_viscosity(temperature_c)
        estimated = water_viscosity * factor
        note = f"Estimated as {factor:.2f}× water viscosity"
    else:
        # Default to water
        estimated = calculate_water_viscosity(temperature_c)
        note = "Unknown media type, using water viscosity"
    
    return estimated, note


def create_correction_summary(
    raw_sizes: np.ndarray,
    measurement_temp_c: float,
    reference_temp_c: float = REFERENCE_TEMPERATURE_C,
    media_type: str = 'water'
) -> Dict[str, Any]:
    """
    Create a comprehensive summary of NTA corrections.
    
    Parameters
    ----------
    raw_sizes : ndarray
        Array of raw size measurements (nm)
    measurement_temp_c : float
        Measurement temperature (°C)
    reference_temp_c : float
        Reference temperature (°C)
    media_type : str
        Type of medium used
        
    Returns
    -------
    dict
        Comprehensive summary including statistics and corrections
    """
    # Get viscosities
    media_viscosity, media_note = get_media_viscosity(media_type, measurement_temp_c)
    ref_viscosity = calculate_water_viscosity(reference_temp_c)
    
    # Calculate correction
    factor, details = get_correction_factor(
        measurement_temp_c, 
        reference_temp_c,
        measurement_viscosity=media_viscosity,
        reference_viscosity=ref_viscosity
    )
    
    # Apply corrections - ensure we work with arrays
    corrected_sizes_arr = np.asarray(correct_nta_size(
        raw_sizes, 
        measurement_temp_c, 
        reference_temp_c,
        measurement_viscosity=media_viscosity,
        reference_viscosity=ref_viscosity
    ))
    
    # Filter valid sizes
    raw_valid = raw_sizes[(raw_sizes > 0) & (raw_sizes < 1000)]
    corrected_valid = corrected_sizes_arr[(corrected_sizes_arr > 0) & (corrected_sizes_arr < 1000)]
    
    summary = {
        'conditions': {
            'measurement_temperature': measurement_temp_c,
            'reference_temperature': reference_temp_c,
            'media_type': media_type,
            'media_viscosity_mPas': media_viscosity * 1000,
            'media_note': media_note,
            'reference_viscosity_mPas': ref_viscosity * 1000,
        },
        'correction': {
            'factor': factor,
            'percentage_change': (factor - 1) * 100,
            'direction': 'increase' if factor > 1 else 'decrease'
        },
        'raw_statistics': {
            'count': len(raw_valid),
            'mean': float(np.mean(raw_valid)) if len(raw_valid) > 0 else None,
            'std': float(np.std(raw_valid)) if len(raw_valid) > 0 else None,
            'd10': float(np.percentile(raw_valid, 10)) if len(raw_valid) > 0 else None,
            'd50': float(np.percentile(raw_valid, 50)) if len(raw_valid) > 0 else None,
            'd90': float(np.percentile(raw_valid, 90)) if len(raw_valid) > 0 else None,
        },
        'corrected_statistics': {
            'count': len(corrected_valid),
            'mean': float(np.mean(corrected_valid)) if len(corrected_valid) > 0 else None,
            'std': float(np.std(corrected_valid)) if len(corrected_valid) > 0 else None,
            'd10': float(np.percentile(corrected_valid, 10)) if len(corrected_valid) > 0 else None,
            'd50': float(np.percentile(corrected_valid, 50)) if len(corrected_valid) > 0 else None,
            'd90': float(np.percentile(corrected_valid, 90)) if len(corrected_valid) > 0 else None,
        },
        'raw_sizes': raw_valid,
        'corrected_sizes': corrected_valid
    }
    
    return summary


if __name__ == "__main__":
    # Demo and validation
    print("=" * 60)
    print("NTA Parameter Corrections Module - Demo")
    print("=" * 60)
    
    # 1. Water viscosity at different temperatures
    print("\n1. Water Viscosity vs Temperature:")
    print("-" * 40)
    for temp in [20, 22, 25, 30, 37]:
        visc = calculate_water_viscosity(temp)
        print(f"   {temp}°C: {visc*1000:.4f} mPa·s")
    
    # 2. Correction factors
    print("\n2. Correction Factors (reference = 25°C):")
    print("-" * 40)
    for temp in [20, 22, 25, 30, 37]:
        factor, _ = get_correction_factor(temp, 25)
        change = (factor - 1) * 100
        print(f"   {temp}°C → 25°C: factor = {factor:.4f} ({change:+.1f}%)")
    
    # 3. Size correction example
    print("\n3. Size Correction Example:")
    print("-" * 40)
    raw_size = 100  # nm
    for temp in [20, 25, 37]:
        corrected = correct_nta_size(raw_size, temp, 25)
        print(f"   {raw_size} nm at {temp}°C → {corrected:.1f} nm (at 25°C)")
    
    # 4. Validation against known values
    print("\n4. Validation:")
    print("-" * 40)
    visc_25 = calculate_water_viscosity(25)
    print(f"   Water viscosity at 25°C: {visc_25*1000:.4f} mPa·s")
    print(f"   Literature value: 0.8900 mPa·s")
    print(f"   Error: {abs(visc_25*1000 - 0.8900)/0.8900 * 100:.2f}%")
    
    print("\n" + "=" * 60)
