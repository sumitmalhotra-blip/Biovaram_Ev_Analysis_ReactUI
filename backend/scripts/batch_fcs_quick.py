"""
Optimized Batch FCS Visualization
=================================
Fast processing of all FCS files with progress tracking
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.fcs_parser import FCSParser
from src.visualization.fcs_plots import FCSPlotter
from loguru import logger
import warnings
warnings.filterwarnings('ignore')

def main():
    # Configuration
    input_dir = Path("nanoFACS/10000 exo and cd81")
    output_dir = Path("figures/fcs_batch")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all FCS files
    fcs_files = list(input_dir.glob("*.fcs"))
    logger.info(f"🎯 Found {len(fcs_files)} FCS files to process")
    
    # Initialize plotter
    plotter = FCSPlotter(output_dir=output_dir)
    
    # Process each file
    success = 0
    errors = 0
    plots = 0
    
    for i, fcs_file in enumerate(fcs_files, 1):
        try:
            logger.info(f"[{i}/{len(fcs_files)}] Processing: {fcs_file.name}")
            
            # Parse
            parser = FCSParser(file_path=fcs_file)
            data = parser.parse()
            
            if data is None or len(data) == 0:
                logger.warning(f"  ⚠️  No data")
                errors += 1
                continue
            
            # Detect channels
            if 'VFSC-A' in data.columns and 'VSSC1-A' in data.columns:
                fsc, ssc = 'VFSC-A', 'VSSC1-A'
            elif 'FSC-A' in data.columns and 'SSC-A' in data.columns:
                fsc, ssc = 'FSC-A', 'SSC-A'
            else:
                fsc, ssc = data.columns[0], data.columns[1]
            
            # Create density plot (fastest and best for large datasets)
            sample_id = fcs_file.stem
            plotter.plot_scatter(
                data=data,
                x_channel=str(fsc),
                y_channel=str(ssc),
                title=f'{sample_id}',
                output_file=f"{sample_id}_scatter.png",
                plot_type="density",
                sample_size=50000
            )
            
            # Generate histogram plots for fluorescence markers
            fl_channels = [col for col in data.columns 
                          if (col.startswith(('V4', 'B5', 'Y5', 'R6', 'R7')) 
                              and col.endswith('-A'))]
            
            if fl_channels:
                # Create multi-marker comparison histogram
                plotter.plot_marker_histograms(
                    data=data,
                    marker_channels=fl_channels[:4],
                    output_file=f"{sample_id}_histograms.png",
                    bins=256,
                    log_scale=True
                )
                plots += 1
            
            success += 1
            plots += 1
            logger.info(f"  ✅ Generated plots ({len(data):,} events)")
            
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            errors += 1
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("📊 BATCH FCS VISUALIZATION COMPLETE")
    logger.info("="*60)
    logger.info(f"✅ Success: {success}/{len(fcs_files)} files")
    logger.info(f"❌ Errors: {errors}")
    logger.info(f"📈 Plots generated: {plots}")
    logger.info(f"💾 Output: {output_dir.absolute()}")
    logger.info("="*60)

if __name__ == '__main__':
    main()
