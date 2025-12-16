"""
Generate FCS plots for all datasets (CD9, EXP 6-10-2025, etc.)

Processes all FCS folders and generates presentation-ready plots.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.fcs_parser import FCSParser
from src.visualization.fcs_plots import FCSPlotter
import matplotlib.pyplot as plt
from tqdm import tqdm
from loguru import logger


def process_folder(input_folder: Path, output_folder: Path):
    """Process all FCS files in a folder."""
    
    fcs_files = list(input_folder.glob("*.fcs"))
    if not fcs_files:
        logger.warning(f"No FCS files in {input_folder}")
        return
    
    logger.info(f"Processing {input_folder.name}: {len(fcs_files)} files")
    
    plotter = FCSPlotter(output_dir=output_folder)
    
    for fcs_file in tqdm(fcs_files, desc=f"{input_folder.name}"):
        try:
            parser = FCSParser(fcs_file)
            data = parser.parse()
            
            if data is None or len(data) == 0:
                continue
            
            sample_name = fcs_file.stem
            
            plotter.plot_fsc_ssc(
                data=data,
                output_file=Path(f"{sample_name}_FSC_vs_SSC.png")
            )
            
            plt.close('all')
            
        except Exception as e:
            logger.error(f"Failed {fcs_file.name}: {e}")


def main():
    """Process all FCS folders."""
    
    datasets = [
        ("nanoFACS/CD9 and exosome lots", "figures/fcs_presentation_cd9"),
        ("nanoFACS/EXP 6-10-2025", "figures/fcs_presentation_exp"),
    ]
    
    for input_dir, output_dir in datasets:
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        if input_path.exists():
            process_folder(input_path, output_path)
        else:
            logger.warning(f"Directory not found: {input_path}")
    
    logger.success("✅ All datasets processed!")


if __name__ == "__main__":
    main()
