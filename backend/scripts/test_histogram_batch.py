"""
Quick test of histogram batch processing on 3 FCS files
"""

import sys
from pathlib import Path
from loguru import logger

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.parsers.fcs_parser import FCSParser
from src.visualization.fcs_plots import FCSPlotter


def main():
    """Process 3 FCS files with histograms."""
    
    logger.info("=" * 80)
    logger.info("🧪 QUICK HISTOGRAM BATCH TEST (3 FILES)")
    logger.info("=" * 80)
    
    # Find FCS files
    fcs_dir = project_root / "nanoFACS" / "10000 exo and cd81"
    fcs_files = sorted(fcs_dir.glob("*.fcs"))[:3]  # First 3 files
    
    if not fcs_files:
        logger.error("No FCS files found")
        return
    
    logger.info(f"Processing {len(fcs_files)} files...")
    
    # Setup output
    output_dir = project_root / "figures" / "histogram_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    plotter = FCSPlotter(output_dir=output_dir)
    
    success = 0
    
    for i, fcs_file in enumerate(fcs_files, 1):
        logger.info(f"\n[{i}/{len(fcs_files)}] Processing: {fcs_file.name}")
        
        try:
            # Parse
            parser = FCSParser(file_path=fcs_file)
            data = parser.parse()
            
            sample_id = fcs_file.stem
            
            # Get channels
            if 'VFSC-A' in data.columns and 'VSSC1-A' in data.columns:
                fsc, ssc = 'VFSC-A', 'VSSC1-A'
            elif 'FSC-A' in data.columns and 'SSC-A' in data.columns:
                fsc, ssc = 'FSC-A', 'SSC-A'
            else:
                fsc = str(data.columns[0])
                ssc = str(data.columns[1])
            
            # Scatter plot
            plotter.plot_scatter(
                data=data,
                x_channel=fsc,
                y_channel=ssc,
                output_file=f"{sample_id}_scatter.png",
                plot_type="density",
                sample_size=50000
            )
            
            # Find fluorescence channels
            fl_channels = [col for col in data.columns 
                          if (col.startswith(('V4', 'B5', 'Y5', 'R6', 'R7')) 
                              and col.endswith('-A'))]
            
            if fl_channels:
                # Multi-marker histogram
                plotter.plot_marker_histograms(
                    data=data,
                    marker_channels=fl_channels[:4],
                    output_file=f"{sample_id}_histograms.png",
                    bins=256,
                    log_scale=True
                )
                logger.info(f"  ✅ Created scatter + histograms ({len(fl_channels)} markers, {len(data):,} events)")
            else:
                logger.info(f"  ✅ Created scatter plot ({len(data):,} events)")
            
            success += 1
            
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 SUMMARY")
    logger.info("=" * 80)
    logger.info(f"✅ Success: {success}/{len(fcs_files)}")
    logger.info(f"📁 Output: {output_dir}")
    
    png_files = list(output_dir.glob("*.png"))
    total_size = sum(f.stat().st_size for f in png_files) / (1024 * 1024)
    logger.info(f"📈 Plots: {len(png_files)}")
    logger.info(f"💾 Size: {total_size:.2f} MB")


if __name__ == "__main__":
    main()
