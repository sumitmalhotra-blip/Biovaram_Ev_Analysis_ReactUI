"""
Size Range Configuration Module
================================

Purpose: Define size range constants for particle size calculations
         to avoid edge clustering artifacts

Client Requirement (Parvesh, Dec 5, 2025):
"Most of them are in 40 and most of them are in 180. This is actually because 
everything beyond the range is getting set to 40 and 180... we need to have that not do that"

Solution:
- Use EXTENDED calculation range (30-220nm) for Mie optimization
- FILTER OUT particles outside valid range (don't clamp!)
- Only DISPLAY particles in 40-200nm range
- Calculate statistics on filtered data only

Author: CRMIT Team
Date: December 17, 2025
"""

from dataclasses import dataclass
from typing import Tuple, Optional
import numpy as np
from loguru import logger


@dataclass(frozen=True)
class SizeRangeConfig:
    """
    Immutable configuration for particle size ranges.
    
    The key insight is to separate:
    1. SEARCH range - where Mie optimization looks for solutions
    2. VALID range - particles we consider physically valid
    3. DISPLAY range - what we show in histograms/charts
    
    By making the SEARCH range larger than DISPLAY range, we:
    - Avoid artificial clustering at boundaries
    - Can identify and filter outliers properly
    - Calculate accurate statistics on valid data only
    """
    
    # Search range for Mie optimization (wider to avoid edge effects)
    # CAL-001 (Feb 10, 2026): Extended to cover full nanoViS bead range (40-1020nm)
    search_min_nm: float = 20.0   # Smallest size to search
    search_max_nm: float = 1100.0 # Largest size to search (covers 1020nm bead)
    
    # Valid range - particles we consider physically valid EVs
    valid_min_nm: float = 20.0    # Minimum valid EV size
    valid_max_nm: float = 1100.0  # Maximum valid EV size (covers microvesicles)
    
    # Display range - what we show in histograms (can be narrower)
    display_min_nm: float = 30.0  # Display minimum
    display_max_nm: float = 1050.0 # Display maximum
    
    # Histogram bin configuration
    default_bin_count: int = 20
    
    def get_search_bounds(self) -> Tuple[float, float]:
        """Get bounds for Mie optimization search."""
        return (self.search_min_nm, self.search_max_nm)
    
    def get_valid_bounds(self) -> Tuple[float, float]:
        """Get bounds for valid particle filtering."""
        return (self.valid_min_nm, self.valid_max_nm)
    
    def get_display_bounds(self) -> Tuple[float, float]:
        """Get bounds for histogram/chart display."""
        return (self.display_min_nm, self.display_max_nm)
    
    def is_valid(self, diameter: float) -> bool:
        """Check if a diameter is within valid range."""
        return self.valid_min_nm <= diameter <= self.valid_max_nm
    
    def is_displayable(self, diameter: float) -> bool:
        """Check if a diameter is within display range."""
        return self.display_min_nm <= diameter <= self.display_max_nm


# Default configuration - used throughout the application
DEFAULT_SIZE_CONFIG = SizeRangeConfig()


def filter_particles_by_size(
    diameters: np.ndarray,
    config: Optional[SizeRangeConfig] = None
) -> Tuple[np.ndarray, dict]:
    """
    Filter particles by size range - EXCLUDE outliers, don't clamp!
    
    This is the key function to prevent edge clustering.
    
    Args:
        diameters: Array of particle diameters in nm
        config: Size range configuration (uses DEFAULT_SIZE_CONFIG if None)
    
    Returns:
        Tuple of (filtered_diameters, statistics_dict)
        
        statistics_dict contains:
        - total_input: Total particles before filtering
        - valid_count: Particles within valid range
        - display_count: Particles within display range  
        - excluded_below: Count below valid minimum
        - excluded_above: Count above valid maximum
        - exclusion_pct: Percentage excluded
    """
    if config is None:
        config = DEFAULT_SIZE_CONFIG
    
    if len(diameters) == 0:
        return np.array([]), {
            'total_input': 0,
            'valid_count': 0,
            'display_count': 0,
            'excluded_below': 0,
            'excluded_above': 0,
            'exclusion_pct': 0.0
        }
    
    total_input = len(diameters)
    
    # Step 1: Filter to valid range (EXCLUDE, don't clamp!)
    valid_mask = (
        (diameters >= config.valid_min_nm) & 
        (diameters <= config.valid_max_nm)
    )
    valid_diameters = diameters[valid_mask]
    valid_count = len(valid_diameters)
    
    # Step 2: Count display-range particles
    display_mask = (
        (valid_diameters >= config.display_min_nm) & 
        (valid_diameters <= config.display_max_nm)
    )
    display_count = np.sum(display_mask)
    
    # Step 3: Count exclusions by category
    excluded_below = np.sum(diameters < config.valid_min_nm)
    excluded_above = np.sum(diameters > config.valid_max_nm)
    total_excluded = excluded_below + excluded_above
    exclusion_pct = (total_excluded / total_input * 100) if total_input > 0 else 0.0
    
    # Log if significant exclusions
    if exclusion_pct > 5:
        logger.warning(
            f"⚠️ Size filtering excluded {exclusion_pct:.1f}% of particles: "
            f"{excluded_below} below {config.valid_min_nm}nm, "
            f"{excluded_above} above {config.valid_max_nm}nm"
        )
    
    stats = {
        'total_input': total_input,
        'valid_count': valid_count,
        'display_count': int(display_count),
        'excluded_below': int(excluded_below),
        'excluded_above': int(excluded_above),
        'exclusion_pct': float(exclusion_pct)
    }
    
    return valid_diameters, stats


def calculate_size_statistics(
    diameters: np.ndarray,
    config: Optional[SizeRangeConfig] = None
) -> dict:
    """
    Calculate size statistics on FILTERED data.
    
    Args:
        diameters: Array of particle diameters (should already be filtered)
        config: Size range configuration
    
    Returns:
        Dictionary with statistical metrics (Median, D10, D50, D90, Std Dev)
    """
    if config is None:
        config = DEFAULT_SIZE_CONFIG
    
    if len(diameters) == 0:
        return {
            'median': None,
            'd10': None,
            'd50': None,
            'd90': None,
            'std': None,
            'count': 0,
            'min': None,
            'max': None
        }
    
    return {
        'median': float(np.median(diameters)),
        'd10': float(np.percentile(diameters, 10)),
        'd50': float(np.percentile(diameters, 50)),
        'd90': float(np.percentile(diameters, 90)),
        'std': float(np.std(diameters)),
        'count': len(diameters),
        'min': float(np.min(diameters)),
        'max': float(np.max(diameters))
    }


def get_histogram_bins(
    config: Optional[SizeRangeConfig] = None,
    bin_count: Optional[int] = None
) -> np.ndarray:
    """
    Generate histogram bin edges based on display range.
    
    Args:
        config: Size range configuration
        bin_count: Number of bins (uses config default if None)
    
    Returns:
        Array of bin edges
    """
    if config is None:
        config = DEFAULT_SIZE_CONFIG
    
    if bin_count is None:
        bin_count = config.default_bin_count
    
    return np.linspace(
        config.display_min_nm,
        config.display_max_nm,
        bin_count + 1
    )


# Quick validation on import
if __name__ == "__main__":
    logger.info("Size Configuration Module Loaded")
    logger.info(f"  Search range: {DEFAULT_SIZE_CONFIG.search_min_nm}-{DEFAULT_SIZE_CONFIG.search_max_nm} nm")
    logger.info(f"  Valid range: {DEFAULT_SIZE_CONFIG.valid_min_nm}-{DEFAULT_SIZE_CONFIG.valid_max_nm} nm")
    logger.info(f"  Display range: {DEFAULT_SIZE_CONFIG.display_min_nm}-{DEFAULT_SIZE_CONFIG.display_max_nm} nm")
