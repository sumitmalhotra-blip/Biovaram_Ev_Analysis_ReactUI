"""
Quick FCS Plot Generator for Presentation

Directly reads FCS files and generates presentation-ready plots.
No need for pre-processing to Parquet.

Usage:
    python scripts/quick_fcs_plots.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.fcs_parser import FCSParser
from src.visualization.fcs_plots import FCSPlotter
import matplotlib.pyplot as plt
from tqdm import tqdm
from loguru import logger


def main():
    """Generate plots from raw FCS files for presentation."""
    
    # Input and output directories
    input_dir = Path("nanoFACS/10000 exo and cd81")
    output_dir = Path("figures/fcs_presentation")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all FCS files
    fcs_files = list(input_dir.glob("*.fcs"))
    logger.info(f"Found {len(fcs_files)} FCS files")
    
    # Initialize plotter
    plotter = FCSPlotter(output_dir=output_dir)
    
    # Process each file
    for fcs_file in tqdm(fcs_files, desc="Generating plots"):
        try:
            # Parse FCS file
            parser = FCSParser(fcs_file)
            data = parser.parse()
            
            # Skip if no data
            if data is None or len(data) == 0:
                logger.warning(f"No data in {fcs_file.name}")
                continue
            
            # Generate scatter plot (FSC vs SSC)
            sample_name = fcs_file.stem
            
            # FSC vs SSC scatter plot
            plotter.plot_fsc_ssc(
                data=data,
                output_file=Path(f"{sample_name}_FSC_vs_SSC.png")
            )
            
            # If particle_size_nm exists, create Size vs Intensity plot
            if 'particle_size_nm' in data.columns:
                # Find first available fluorescence channel
                fl_channels = [col for col in data.columns if any(x in col for x in ['B', 'R', 'V', 'FL'])]
                if fl_channels:
                    plotter.plot_scatter(
                        data=data,
                        x_channel='particle_size_nm',
                        y_channel=fl_channels[0],
                        title=f"{sample_name} - Size vs Intensity",
                        output_file=Path(f"{sample_name}_Size_vs_Intensity.png"),
                        use_particle_size=True
                    )
            
            plt.close('all')  # Free memory
            
        except Exception as e:
            logger.error(f"Failed to process {fcs_file.name}: {e}")
    
    logger.success(f"✅ Plots saved to {output_dir}")


if __name__ == "__main__":
    main()
