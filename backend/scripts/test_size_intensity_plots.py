"""
Test Size vs Intensity Plots with Real Parquet Data
===================================================

Purpose: Test the new Size vs Intensity plotting module with actual converted FCS data
         Validates particle size calculations and decision support logic

Author: CRMIT Backend Team
Date: November 18, 2025
"""

import sys
from pathlib import Path
import pandas as pd
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.visualization.size_intensity_plots import SizeIntensityPlotter

# Configure logger
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


def main():
    """Test Size vs Intensity plots with real data."""
    
    logger.info("=" * 80)
    logger.info("🧪 TESTING SIZE VS INTENSITY PLOTS WITH REAL DATA")
    logger.info("=" * 80)
    
    project_root = Path(__file__).parent.parent
    
    # Find converted Parquet files
    parquet_dir = project_root / "data" / "parquet" / "nanofacs" / "events" / "10000 exo and cd81"
    
    if not parquet_dir.exists():
        logger.error(f"❌ Parquet directory not found: {parquet_dir}")
        logger.info("Run convert_fcs_to_parquet.py first!")
        return
    
    # Get CD81 and ISO files
    cd81_files = list(parquet_dir.glob("*CD81*.parquet"))
    iso_files = list(parquet_dir.glob("*ISO*.parquet"))
    
    logger.info(f"📁 Found {len(cd81_files)} CD81 files and {len(iso_files)} ISO files")
    
    if len(cd81_files) == 0:
        logger.error("❌ No CD81 files found!")
        return
    
    # Create output directory
    output_dir = project_root / "figures" / "size_intensity_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 Output: {output_dir}")
    
    # Initialize plotter
    plotter = SizeIntensityPlotter()
    
    # Test 1: Single CD81 sample
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: Size vs Intensity - CD81 Sample")
    logger.info("=" * 80)
    
    test_file = cd81_files[0]
    logger.info(f"📊 Testing: {test_file.name}")
    
    # Load data
    data = pd.read_parquet(test_file)
    logger.info(f"✅ Loaded: {len(data):,} events")
    
    # Check for particle_size_nm
    if 'particle_size_nm' not in data.columns:
        logger.error("❌ particle_size_nm column not found!")
        logger.info("Available columns:")
        logger.info(f"  {', '.join(data.columns[:20])}")
        return
    
    logger.info(f"✅ Particle sizes available: {data['particle_size_nm'].min():.1f} - {data['particle_size_nm'].max():.1f} nm")
    
    # Find fluorescence channel (B531-H for blue light)
    intensity_channel = 'B531-H' if 'B531-H' in data.columns else 'B531-A'
    if intensity_channel not in data.columns:
        logger.error(f"❌ {intensity_channel} not found!")
        return
    
    logger.info(f"✅ Intensity channel: {intensity_channel}")
    
    # Create Size vs Intensity plot
    logger.info("\n📊 Creating Size vs Intensity plot (density)...")
    
    fig = plotter.plot_size_vs_intensity(
        data=data,
        intensity_channel=intensity_channel,
        marker_name='CD81',
        title=f'Size vs Intensity: {test_file.stem}',
        output_file=output_dir / f"{test_file.stem}_size_intensity.png",
        plot_type='density',
        highlight_expected=True
    )
    
    logger.info(f"✅ Plot saved!")
    
    # Test 2: Cluster identification
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Cluster Identification")
    logger.info("=" * 80)
    
    clusters = plotter.identify_size_intensity_clusters(
        data=data,
        intensity_channel=intensity_channel,
        size_bins=[(30, 80), (80, 120), (120, 150)]
    )
    
    logger.info("\n📊 Clusters Found:")
    logger.info(clusters.to_string(index=False))
    
    # Test 3: Decision support
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Decision Support - Proceed to TEM?")
    logger.info("=" * 80)
    
    decision = plotter.decision_support(
        data=data,
        marker_name='CD81',
        intensity_channel=intensity_channel
    )
    
    status_emoji = "✅" if decision['proceed_to_tem'] else "❌"
    logger.info(f"\n{status_emoji} DECISION: {decision['decision']}")
    logger.info(f"📋 REASON: {decision['reason']}")
    logger.info(f"📊 Particles at expected size: {decision.get('particles_at_expected_size', 'N/A')}")
    if 'percent_positive' in decision:
        logger.info(f"📊 Percent positive: {decision['percent_positive']:.1f}%")
    
    # Test 4: Multi-marker comparison (if we have multiple files)
    if len(cd81_files) >= 2:
        logger.info("\n" + "=" * 80)
        logger.info("TEST 4: Multi-Marker Comparison")
        logger.info("=" * 80)
        
        # Load another CD81 file
        test_file2 = cd81_files[1]
        data2 = pd.read_parquet(test_file2)
        
        logger.info(f"📊 Comparing:")
        logger.info(f"  1. {test_file.stem}")
        logger.info(f"  2. {test_file2.stem}")
        
        # Create multi-panel plot
        fig2 = plotter.plot_multi_marker_comparison(
            data=data,
            intensity_channels=['B531-H', 'Y595-H'] if 'Y595-H' in data.columns else ['B531-H'],
            marker_names=['CD81 (Blue)', 'CD81 (Yellow)'] if 'Y595-H' in data.columns else ['CD81'],
            output_file=output_dir / "multi_marker_comparison.png"
        )
        
        logger.info("✅ Multi-marker comparison saved!")
    
    # Test 5: ISO control comparison
    if len(iso_files) > 0:
        logger.info("\n" + "=" * 80)
        logger.info("TEST 5: CD81 vs ISO Control Comparison")
        logger.info("=" * 80)
        
        iso_file = iso_files[0]
        logger.info(f"📊 ISO Control: {iso_file.name}")
        
        iso_data = pd.read_parquet(iso_file)
        
        # Create ISO plot
        fig3 = plotter.plot_size_vs_intensity(
            data=iso_data,
            intensity_channel=intensity_channel,
            marker_name='ISO',
            title=f'Size vs Intensity: {iso_file.stem} (ISO Control)',
            output_file=output_dir / f"{iso_file.stem}_size_intensity.png",
            plot_type='density',
            highlight_expected=False  # No expected range for ISO
        )
        
        logger.info("✅ ISO control plot saved!")
        
        # Compare cluster statistics
        cd81_clusters = plotter.identify_size_intensity_clusters(data, intensity_channel)
        iso_clusters = plotter.identify_size_intensity_clusters(iso_data, intensity_channel)
        
        logger.info("\n📊 CD81 vs ISO Cluster Comparison:")
        logger.info("\nCD81:")
        logger.info(cd81_clusters[['size_range', 'total_events', 'percent_positive']].to_string(index=False))
        logger.info("\nISO Control:")
        logger.info(iso_clusters[['size_range', 'total_events', 'percent_positive']].to_string(index=False))
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("✅ ALL TESTS COMPLETE!")
    logger.info("=" * 80)
    
    plot_files = list(output_dir.glob("*.png"))
    logger.info(f"\n📊 Generated {len(plot_files)} plots:")
    for plot_file in plot_files:
        size_mb = plot_file.stat().st_size / (1024 * 1024)
        logger.info(f"  - {plot_file.name} ({size_mb:.2f} MB)")
    
    logger.info(f"\n📁 Output directory: {output_dir}")
    
    logger.info("\n🎯 KEY FINDINGS:")
    logger.info(f"  1. Particle size range: {data['particle_size_nm'].min():.1f} - {data['particle_size_nm'].max():.1f} nm")
    logger.info(f"  2. Decision for CD81: {decision['decision']}")
    logger.info(f"  3. Proceed to TEM: {'YES ✅' if decision['proceed_to_tem'] else 'NO ❌'}")
    logger.info(f"  4. Clusters identified: {len(clusters)}")
    
    logger.info("\n📋 Next Steps:")
    logger.info("  1. Review plots in figures/size_intensity_test/")
    logger.info("  2. Validate particle size calculations with NTA data")
    logger.info("  3. Integrate with Mohith's UI for decision display")
    logger.info("  4. Test with more samples and different markers (CD9, CD63)")


if __name__ == "__main__":
    main()
