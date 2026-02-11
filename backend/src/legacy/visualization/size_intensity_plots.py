"""
Size vs Intensity Plot Helper Module
=====================================

Purpose: Generate biologically meaningful Size vs Intensity scatter plots
         instead of Area vs Area plots (which are not scientifically useful)

Meeting Context (Nov 18, 2025):
Parvesh explained the complete analysis workflow:

1. NTA provides size distribution (40nm, 50nm, etc.)
2. NanoFACS checks if marker exists at expected size
   - Example: CD9 expected at ~80nm scattering blue light (B531)
3. Decision point: If NO marker at expected size → discard sample
4. If marker found → proceed to TEM for viability check
5. Finally → Western Blot for protein confirmation

Key Insight: Scientists look for CLUSTERING at specific size + wavelength combinations
- Size calculated from FSC/SSC (Mie scatter)
- Intensity from fluorescence channels (B531, Y595, etc.)
- Clustering shows which particle sizes have which markers

Example Use Cases:
- "Does CD9 appear at 80nm with blue light scattering?"
- "Are there particles at 120nm with high CD81 signal?"
- "What size range shows strongest marker expression?"

Author: CRMIT Backend Team
Date: November 18, 2025
"""

from typing import Optional, List, Tuple, Dict, Any
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from pathlib import Path
from loguru import logger


class SizeIntensityPlotter:
    """
    Generate Size vs Intensity scatter plots for FCS data.
    
    CRITICAL: This replaces Area vs Area plotting with biologically meaningful analysis.
    """
    
    def __init__(self):
        self.marker_expectations = {
            'CD9': {'expected_size_nm': 80, 'wavelength': 'blue', 'channel': 'B531'},
            'CD81': {'expected_size_nm': 80, 'wavelength': 'blue', 'channel': 'B531'},
            'CD63': {'expected_size_nm': 80, 'wavelength': 'blue', 'channel': 'B531'},
        }
        
        self.wavelength_channels = {
            'blue': 'B531',
            'yellow': 'Y595',
            'violet': 'V447',
            'red': 'R613'
        }
    
    def plot_size_vs_intensity(
        self,
        data: pd.DataFrame,
        intensity_channel: str,
        marker_name: Optional[str] = None,
        title: Optional[str] = None,
        output_file: Optional[Path] = None,
        plot_type: str = "density",
        highlight_expected: bool = True
    ) -> Figure:
        """
        Create Size vs Intensity scatter plot.
        
        Args:
            data: DataFrame with 'particle_size_nm' and intensity channels
            intensity_channel: Fluorescence channel (e.g., 'B531-H')
            marker_name: Marker being analyzed (e.g., 'CD9') for expected size overlay
            title: Custom title
            output_file: Save location
            plot_type: 'scatter', 'density', or 'hexbin'
            highlight_expected: Draw box around expected size range
            
        Returns:
            matplotlib Figure
        
        WHAT THIS DOES:
        ----------------
        Creates a scientifically meaningful plot showing WHERE particles of different
        SIZES show MARKER EXPRESSION. This answers: "Does CD9 appear at 80nm?"
        
        HOW IT WORKS:
        --------------
        1. X-axis: Particle size (nm) calculated from FSC/SSC using Mie theory
           - Example: 40nm, 80nm, 120nm
        
        2. Y-axis: Fluorescence intensity for specified marker
           - Example: B531-H (blue fluorescence at 531nm wavelength)
           - Higher intensity = more marker expression
        
        3. Plot types:
           - "density": 2D histogram (heat map) - best for >10k events
           - "hexbin": Hexagonal binning - good for medium datasets
           - "scatter": Individual points - only for small datasets
        
        4. Expected marker box (if marker specified):
           - Draws red box around expected size range
           - Example: CD9 expected at 80±10nm
           - Shows WHERE to look for positive signal
        
        WHY THIS IS CRITICAL:
        ---------------------
        Meeting context (Nov 18, 2025 - Parvesh):
        "Scientists look for CLUSTERING at specific size + wavelength combinations"
        
        Workflow:
        1. NTA measures size distribution → "Sample has particles at 80nm"
        2. THIS PLOT checks if marker exists at that size → "Does CD9 appear at 80nm?"
        3. If YES → proceed to TEM for viability check
        4. If NO → discard sample (no point doing TEM)
        
        EXAMPLE INTERPRETATION:
        -----------------------
        Good result:
        - Dense cluster at (80nm, high B531 intensity)
        - Interpretation: CD9 marker present on 80nm exosomes ✅
        
        Bad result:
        - No events at expected size, OR
        - Events at expected size but low intensity
        - Interpretation: Marker not detected → discard sample ❌
        
        COMPARISON TO OLD APPROACH:
        ---------------------------
        OLD: Area vs Area plots (FSC-A vs SSC-A)
        - Not scientifically useful
        - Doesn't show size or marker expression
        - Just shows scatter correlations
        
        NEW: Size vs Intensity plots (THIS)
        - Shows actual biology: size + marker expression
        - Enables decision-making: proceed to TEM?
        - Directly answers research question
        """
        # Step 1: Validate required columns
        # ----------------------------------
        # particle_size_nm must exist (calculated from Mie scatter)
        if 'particle_size_nm' not in data.columns:
            logger.error("❌ particle_size_nm column not found. Run calculate_particle_size() first!")
            raise ValueError("Data must contain 'particle_size_nm' column")
        
        if intensity_channel not in data.columns:
            logger.error(f"❌ Channel {intensity_channel} not found in data")
            raise ValueError(f"Channel {intensity_channel} not in DataFrame")
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Sample for performance if needed
        if len(data) > 10000:
            data_plot = data.sample(n=10000, random_state=42)
        else:
            data_plot = data
        
        # Generate plot
        if plot_type == "density":
            h = ax.hist2d(
                data_plot['particle_size_nm'],
                data_plot[intensity_channel],
                bins=100,
                cmap='viridis',
                cmin=1
            )
            plt.colorbar(h[3], ax=ax, label='Event Count')
        
        elif plot_type == "hexbin":
            hexbin = ax.hexbin(
                data_plot['particle_size_nm'],
                data_plot[intensity_channel],
                gridsize=50,
                cmap='viridis',
                mincnt=1
            )
            plt.colorbar(hexbin, ax=ax, label='Event Count')
        
        elif plot_type == "scatter":
            ax.scatter(
                data_plot['particle_size_nm'],
                data_plot[intensity_channel],
                s=1,
                alpha=0.3,
                c='blue',
                edgecolors='none'
            )
        
        # Highlight expected size range if marker specified
        if highlight_expected and marker_name and marker_name in self.marker_expectations:
            expected = self.marker_expectations[marker_name]
            expected_size = expected['expected_size_nm']
            
            # Draw box around expected region (±10nm)
            ax.axvspan(
                expected_size - 10,
                expected_size + 10,
                alpha=0.2,
                color='red',
                label=f'Expected {marker_name} range ({expected_size}±10nm)'
            )
            
            # Add annotation
            ax.text(
                expected_size,
                ax.get_ylim()[1] * 0.95,
                f'Expected\n{marker_name}\n{expected_size}nm',
                ha='center',
                va='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                fontsize=9
            )
        
        # Labels and title
        ax.set_xlabel('Particle Size (nm)', fontweight='bold', fontsize=12)
        ax.set_ylabel(f'{intensity_channel} Intensity', fontweight='bold', fontsize=12)
        
        if title:
            ax.set_title(title, fontweight='bold', fontsize=14)
        else:
            marker_label = f" - {marker_name}" if marker_name else ""
            ax.set_title(
                f'Size vs Intensity Analysis{marker_label}',
                fontweight='bold',
                fontsize=14
            )
        
        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--')
        
        if highlight_expected and marker_name:
            ax.legend(loc='upper right')
        
        plt.tight_layout()
        
        # Save if requested
        if output_file:
            fig.savefig(output_file, dpi=300, bbox_inches='tight')
            logger.info(f"✅ Saved: {output_file}")
        
        return fig
    
    def plot_multi_marker_comparison(
        self,
        data: pd.DataFrame,
        intensity_channels: List[str],
        marker_names: List[str],
        output_file: Optional[Path] = None
    ) -> Figure:
        """
        Create multi-panel comparison of Size vs Intensity for multiple markers.
        
        Args:
            data: DataFrame with particle_size_nm and intensity channels
            intensity_channels: List of intensity channels to plot
            marker_names: Corresponding marker names
            output_file: Save location
            
        Returns:
            matplotlib Figure with subplots
        """
        n_markers = len(intensity_channels)
        n_cols = 2
        n_rows = (n_markers + 1) // 2
        
        fig, axes_obj = plt.subplots(n_rows, n_cols, figsize=(16, 8 * n_rows))
        from matplotlib.axes import Axes
        import numpy as np
        axes: list[Axes] = list(np.ravel(axes_obj)) if n_markers > 1 else [axes_obj]  # type: ignore[list-item]
        
        for i, (channel, marker) in enumerate(zip(intensity_channels, marker_names)):
            ax = axes[i]
            
            # Plot density
            h = ax.hist2d(
                data['particle_size_nm'],
                data[channel],
                bins=80,
                cmap='viridis',
                cmin=1
            )
            plt.colorbar(h[3], ax=ax, label='Events')
            
            # Highlight expected
            if marker in self.marker_expectations:
                expected_size = self.marker_expectations[marker]['expected_size_nm']
                ax.axvspan(
                    expected_size - 10,
                    expected_size + 10,
                    alpha=0.2,
                    color='red'
                )
            
            ax.set_xlabel('Particle Size (nm)', fontweight='bold')
            ax.set_ylabel(f'{channel} Intensity', fontweight='bold')
            ax.set_title(f'{marker} Analysis', fontweight='bold', fontsize=12)
            ax.grid(True, alpha=0.3)
        
        # Remove extra subplots
        for i in range(n_markers, len(axes)):
            fig.delaxes(axes[i])
        
        plt.tight_layout()
        
        if output_file:
            fig.savefig(output_file, dpi=300, bbox_inches='tight')
            logger.info(f"✅ Saved multi-marker comparison: {output_file}")
        
        return fig
    
    def identify_size_intensity_clusters(
        self,
        data: pd.DataFrame,
        intensity_channel: str,
        size_bins: List[Tuple[float, float]] = [(30, 80), (80, 120), (120, 200)],
        intensity_threshold: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Identify clusters at specific size ranges with high intensity.
        
        This answers: "Are there particles at X nm with high marker signal?"
        
        Args:
            data: DataFrame with particle_size_nm and intensity
            intensity_channel: Channel to analyze
            size_bins: List of (min_size, max_size) tuples
            intensity_threshold: Minimum intensity (auto if None)
            
        Returns:
            DataFrame with cluster statistics per size bin
        """
        if intensity_threshold is None:
            # Use 90th percentile as "positive" threshold
            intensity_threshold = float(data[intensity_channel].quantile(0.9))
        
        results = []
        
        for min_size, max_size in size_bins:
            # Get particles in size range
            mask = (data['particle_size_nm'] >= min_size) & (data['particle_size_nm'] < max_size)
            bin_data = data[mask]
            
            if len(bin_data) == 0:
                continue
            
            # Count positive events
            positive_mask = bin_data[intensity_channel] > intensity_threshold
            n_positive = positive_mask.sum()
            pct_positive = (n_positive / len(bin_data)) * 100
            
            # Statistics
            mean_intensity = bin_data[intensity_channel].mean()
            median_intensity = float(np.median(np.asarray(bin_data[intensity_channel])))
            
            results.append({
                'size_range': f'{min_size}-{max_size}nm',
                'min_size_nm': min_size,
                'max_size_nm': max_size,
                'total_events': len(bin_data),
                'positive_events': n_positive,
                'percent_positive': pct_positive,
                'mean_intensity': mean_intensity,
                'median_intensity': median_intensity,
                'intensity_threshold': intensity_threshold
            })
        
        cluster_df = pd.DataFrame(results)
        
        logger.info(f"✅ Identified {len(cluster_df)} size-intensity clusters")
        return cluster_df
    
    def decision_support(
        self,
        data: pd.DataFrame,
        marker_name: str,
        intensity_channel: str
    ) -> Dict[str, Any]:
        """
        Provide decision support: Should this sample proceed to TEM?
        
        Based on workflow: If marker NOT at expected size → discard
        
        Args:
            data: DataFrame with particle_size_nm
            marker_name: Marker being checked (e.g., 'CD9')
            intensity_channel: Intensity channel for marker
            
        Returns:
            Dictionary with recommendation and reasoning
        
        WHAT THIS DOES:
        ----------------
        Automates the decision: "Should this sample proceed to TEM analysis?"
        Based on whether the expected marker appears at the expected size.
        
        HOW IT WORKS:
        --------------
        Step 1: Check if we know expected size for this marker
        - Lookup in self.marker_expectations
        - Example: CD9 expected at 80nm
        
        Step 2: Count particles at expected size (±15nm tolerance)
        - Example: CD9 at 80nm → check 65-95nm range
        - Require ≥100 particles (statistical significance)
        - Reason: Too few particles → unreliable measurement
        
        Step 3: Check intensity at expected size
        - Calculate 75th percentile intensity as "positive" threshold
        - Count how many particles at expected size exceed threshold
        - Require ≥10% positive rate
        - Reason: Low positivity → marker not really there (background)
        
        Step 4: Make decision
        - PROCEED: Marker detected at expected size with good signal
        - REJECT: Insufficient particles OR low marker expression
        
        WHY THIS IS IMPORTANT:
        ----------------------
        Meeting context (Nov 18, 2025):
        "If marker NOT at expected size → discard sample"
        
        TEM (Transmission Electron Microscopy) is:
        - Time-consuming (hours per sample)
        - Expensive ($100+ per sample)
        - Requires skilled operator
        
        So we MUST filter out bad samples BEFORE TEM:
        - Save time and money
        - Focus TEM on promising samples
        - Avoid wasting researcher effort
        
        DECISION TREE:
        --------------
        Question 1: Are there ≥100 particles at expected size?
        └─ NO → REJECT ("Too few particles at expected CD9 size (80±15nm): 45")
        └─ YES → Continue to Question 2
        
        Question 2: Do ≥10% show positive marker signal?
        └─ NO → REJECT ("Low CD9 signal at expected size: 3.2% positive")
        └─ YES → PROCEED ("CD9 detected at expected size with 15.4% positive")
        
        EXAMPLE OUTPUTS:
        ----------------
        GOOD sample:
        {
            'decision': 'PROCEED',
            'reason': 'CD9 detected at expected size with 18.5% positive',
            'proceed_to_tem': True,
            'particles_at_expected_size': 1523,
            'percent_positive': 18.5
        }
        
        BAD sample:
        {
            'decision': 'REJECT',
            'reason': 'Low CD9 signal at expected size: 4.2% positive',
            'proceed_to_tem': False,
            'particles_at_expected_size': 842,
            'percent_positive': 4.2
        }
        """
        # Step 1: Lookup expected size for this marker
        # ---------------------------------------------
        if marker_name not in self.marker_expectations:
            return {
                'decision': 'UNKNOWN',
                'reason': f'No expected size defined for {marker_name}',
                'proceed_to_tem': None
            }
        
        expected = self.marker_expectations[marker_name]
        expected_size = expected['expected_size_nm']
        
        # Check for signal at expected size (±15nm tolerance)
        size_mask = (
            (data['particle_size_nm'] >= expected_size - 15) &
            (data['particle_size_nm'] <= expected_size + 15)
        )
        
        particles_at_expected = size_mask.sum()
        
        if particles_at_expected < 100:
            return {
                'decision': 'REJECT',
                'reason': f'Too few particles at expected {marker_name} size ({expected_size}±15nm): {particles_at_expected}',
                'proceed_to_tem': False,
                'particles_at_expected_size': particles_at_expected
            }
        
        # Check intensity at expected size
        intensity_at_expected = data[size_mask][intensity_channel]
        threshold = data[intensity_channel].quantile(0.75)
        positive_at_expected = (intensity_at_expected > threshold).sum()
        pct_positive = (positive_at_expected / particles_at_expected) * 100
        
        if pct_positive < 10:
            return {
                'decision': 'REJECT',
                'reason': f'Low {marker_name} signal at expected size: {pct_positive:.1f}% positive',
                'proceed_to_tem': False,
                'particles_at_expected_size': particles_at_expected,
                'percent_positive': pct_positive
            }
        
        return {
            'decision': 'PROCEED',
            'reason': f'{marker_name} detected at expected size with {pct_positive:.1f}% positive',
            'proceed_to_tem': True,
            'particles_at_expected_size': particles_at_expected,
            'percent_positive': pct_positive
        }


# Example usage
if __name__ == "__main__":
    from src.parsers.fcs_parser import FCSParser
    from src.visualization.fcs_plots import calculate_particle_size
    
    # Load sample data
    fcs_file = Path("data/parquet/nanofacs/events/Exo + 0.25ug CD81 SEC.parquet")
    
    if fcs_file.exists():
        data = pd.read_parquet(fcs_file)
        print(f"Loaded {len(data)} events")
        
        # Calculate particle size
        data = calculate_particle_size(data)
        
        # Create plotter
        plotter = SizeIntensityPlotter()
        
        # Generate Size vs Intensity plot
        fig = plotter.plot_size_vs_intensity(
            data=data,
            intensity_channel='B531-H',
            marker_name='CD81',
            output_file=Path('test_size_vs_intensity.png'),
            highlight_expected=True
        )
        
        # Get clusters
        clusters = plotter.identify_size_intensity_clusters(
            data,
            'B531-H'
        )
        print("\nSize-Intensity Clusters:")
        print(clusters)
        
        # Decision support
        decision = plotter.decision_support(data, 'CD81', 'B531-H')
        print(f"\nDecision: {decision['decision']}")
        print(f"Reason: {decision['reason']}")
        print(f"Proceed to TEM? {decision['proceed_to_tem']}")
    else:
        print("Sample FCS file not found!")
