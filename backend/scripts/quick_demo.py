"""
Quick Demo: Test visualization modules with real FCS data
========================================================

Purpose: Quickly validate FCS visualization with actual project data
        Uses correct channel names and API signatures

Author: CRMIT Team
Date: November 15, 2025
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.fcs_parser import FCSParser
from src.visualization.fcs_plots import FCSPlotter
from src.visualization.anomaly_detection import AnomalyDetector
from loguru import logger

def main():
    """Quick demo with real data."""
    
    # Setup
    fcs_dir = Path("nanoFACS/10000 exo and cd81")
    output_dir = Path("figures/demo")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("="*80)
    logger.info("🚀 QUICK VISUALIZATION DEMO WITH REAL FCS DATA")
    logger.info("="*80)
    
    # Find FCS files
    fcs_files = sorted(list(fcs_dir.glob("*.fcs")))[:5]
    logger.info(f"📁 Found {len(fcs_files)} FCS files")
    
    if not fcs_files:
        logger.error("❌ No FCS files found!")
        return
    
    # Parse first file
    test_file = fcs_files[0]
    logger.info(f"\n📊 Testing with: {test_file.name}")
    
    try:
        parser = FCSParser(file_path=test_file)
        data = parser.parse()
        logger.info(f"✅ Parsed: {len(data):,} events, {len(data.columns)} channels")
        logger.info(f"   Available channels: {', '.join(data.columns[:15])}")
        
        # Initialize plotter
        plotter = FCSPlotter(output_dir=output_dir)
        
        # Detect which channel naming convention is used
        if 'FSC-A' in data.columns:
            fsc_channel, ssc_channel = 'FSC-A', 'SSC-A'
        elif 'VFSC-A' in data.columns:
            fsc_channel, ssc_channel = 'VFSC-A', 'VSSC1-A'
        else:
            fsc_channel, ssc_channel = data.columns[0], data.columns[1]
        
        logger.info(f"\n📈 Using channels: {fsc_channel} vs {ssc_channel}")
        
        # 1. Scatter plot (density)
        logger.info("\n1️⃣ Creating scatter plot (density)...")
        fig1 = plotter.plot_scatter(
            data=data,
            x_channel=str(fsc_channel),
            y_channel=str(ssc_channel),
            title=f'Demo Scatter (Density): {test_file.stem}',
            output_file=f"demo_scatter_density_{test_file.stem}.png",
            plot_type="density",
            sample_size=50000
        )
        logger.info(f"   ✅ Saved density scatter plot")
        
        # 2. Scatter plot (hexbin)
        logger.info("\n2️⃣ Creating hexbin plot...")
        fig2 = plotter.plot_scatter(
            data=data,
            x_channel=str(fsc_channel),
            y_channel=str(ssc_channel),
            title=f'Demo Scatter (Hexbin): {test_file.stem}',
            output_file=f"demo_scatter_hexbin_{test_file.stem}.png",
            plot_type="hexbin",
            sample_size=50000
        )
        logger.info(f"   ✅ Saved hexbin plot")
        
        # 3. Standard FSC-SSC plot
        logger.info("\n3️⃣ Creating standard FSC-SSC plot...")
        fig3 = plotter.plot_fsc_ssc(
            data=data,
            output_file=Path(f"demo_fsc_ssc_{test_file.stem}.png"),
            plot_type="hexbin"
        )
        logger.info(f"   ✅ Saved multi-channel grid")
        
        # 4. Anomaly detection (if we have 2+ files)
        if len(fcs_files) >= 2:
            logger.info("\n4️⃣ Testing anomaly detection...")
            detector = AnomalyDetector(output_dir=output_dir)
            
            # Set baseline
            baseline_info = detector.set_baseline(
                baseline_data=data,
                x_channel=str(fsc_channel),
                y_channel=str(ssc_channel)
            )
            logger.info(f"   ✅ Baseline set: {baseline_info.get('n_events', 0):,} events")
            
            # Test with second file
            test_file2 = fcs_files[1]
            parser2 = FCSParser(file_path=test_file2)
            data2 = parser2.parse()
            logger.info(f"   📊 Testing: {test_file2.name}")
            
            results = detector.detect_scatter_shift(
                test_data=data2,
                threshold=2.0,
                save_plot=True
            )
            
            if results:
                status = "🚨 ANOMALY" if results['is_anomaly'] else "✅ Normal"
                logger.info(f"   {status}")
                logger.info(f"   Shift magnitude: {results['shift_magnitude']:.2f}σ")
                logger.info(f"   X-shift: {results['x_shift_mean']:.2f}σ")
                logger.info(f"   Y-shift: {results['y_shift_mean']:.2f}σ")
        
        # Summary
        logger.info("\n" + "="*80)
        logger.info("✅ DEMO COMPLETE!")
        logger.info("="*80)
        logger.info(f"📁 Plots saved to: {output_dir}")
        logger.info(f"📊 Generated plots:")
        for plot_file in output_dir.glob("demo_*.png"):
            logger.info(f"   - {plot_file.name}")
        logger.info(f"\n🎉 All visualization modules working correctly!")
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    logger.info("\nNext steps:")
    logger.info("  1. Run: python scripts/batch_visualize_fcs.py")
    logger.info("  2. Process first NTA data to generate statistics")
    logger.info("  3. Run: python scripts/batch_visualize_nta.py")
    logger.info("  4. Review plots and adjust parameters as needed")


if __name__ == '__main__':
    main()
