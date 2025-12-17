"""
Channel Configuration CLI Tool
==============================

Use this script to configure FSC/SSC channel mappings for your flow cytometer.

Usage:
    # View current configuration
    python configure_channels.py --show
    
    # Set channel mapping for Apogee with generic channel names
    python configure_channels.py --fsc Channel_5 --ssc Channel_6
    
    # List available instruments
    python configure_channels.py --list-instruments
    
    # Switch to a specific instrument
    python configure_channels.py --instrument apogee_26ch

Author: BioVaram Team
"""
import argparse
import sys
sys.path.insert(0, '.')

from src.utils.channel_config import get_channel_config
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Configure FSC/SSC channel mappings for FCS analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python configure_channels.py --show
      Show current channel configuration
      
  python configure_channels.py --fsc Channel_5 --ssc Channel_6
      Set FSC to Channel_5 and SSC to Channel_6
      
  python configure_channels.py --instrument apogee_26ch
      Switch to Apogee 26-channel instrument configuration
      
  python configure_channels.py --list-instruments
      List all available instrument configurations
        """
    )
    
    parser.add_argument('--show', action='store_true',
                        help='Show current channel configuration')
    parser.add_argument('--fsc', type=str, default=None,
                        help='Set the FSC channel name (e.g., Channel_5, VFSC-A)')
    parser.add_argument('--ssc', type=str, default=None,
                        help='Set the SSC channel name (e.g., Channel_6, VSSC-A)')
    parser.add_argument('--instrument', type=str, default=None,
                        help='Set the active instrument configuration')
    parser.add_argument('--list-instruments', action='store_true',
                        help='List available instrument configurations')
    parser.add_argument('--analyze', type=str, default=None,
                        help='Analyze channels in a specific FCS file')
    
    args = parser.parse_args()
    
    config = get_channel_config()
    
    # Show current configuration
    if args.show or (not any([args.fsc, args.ssc, args.instrument, 
                               args.list_instruments, args.analyze])):
        print("\n" + "=" * 70)
        print("CURRENT CHANNEL CONFIGURATION")
        print("=" * 70)
        print(f"\n🔧 Active Instrument: {config.active_instrument}")
        print(f"\n📊 Preferred FSC Channel: {config.get_preferred_channels()[0]}")
        print(f"📊 Preferred SSC Channel: {config.get_preferred_channels()[1]}")
        print(f"\n🔍 FSC Detection Order: {config.get_fsc_channel_names()}")
        print(f"🔍 SSC Detection Order: {config.get_ssc_channel_names()}")
        print("\n" + "-" * 70)
        print("To change configuration:")
        print("  python configure_channels.py --fsc <channel> --ssc <channel>")
        print("=" * 70 + "\n")
        return
    
    # List instruments
    if args.list_instruments:
        print("\n" + "=" * 70)
        print("AVAILABLE INSTRUMENT CONFIGURATIONS")
        print("=" * 70)
        for inst in config.list_instruments():
            marker = "✓" if inst == config.active_instrument else " "
            print(f"  [{marker}] {inst}")
        print("\n" + "-" * 70)
        print("To switch instrument:")
        print("  python configure_channels.py --instrument <name>")
        print("=" * 70 + "\n")
        return
    
    # Set instrument
    if args.instrument:
        if config.set_active_instrument(args.instrument):
            config.save_config()
            print(f"✓ Active instrument set to: {args.instrument}")
            print(f"  FSC channels: {config.get_fsc_channel_names()}")
            print(f"  SSC channels: {config.get_ssc_channel_names()}")
        else:
            print(f"✗ Instrument '{args.instrument}' not found")
            print(f"  Available: {config.list_instruments()}")
            return 1
    
    # Set custom channels
    if args.fsc and args.ssc:
        config.add_custom_channel_mapping(args.fsc, args.ssc)
        config.save_config()
        print("\n" + "=" * 70)
        print("CHANNEL CONFIGURATION UPDATED")
        print("=" * 70)
        print(f"\n✓ FSC Channel: {args.fsc}")
        print(f"✓ SSC Channel: {args.ssc}")
        print(f"\nConfiguration saved to: config/channel_config.json")
        print("\nRestart the API server for changes to take effect.")
        print("=" * 70 + "\n")
    elif args.fsc or args.ssc:
        print("✗ Both --fsc and --ssc must be specified together")
        return 1
    
    # Analyze specific file
    if args.analyze:
        fcs_path = Path(args.analyze)
        if not fcs_path.exists():
            print(f"✗ File not found: {fcs_path}")
            return 1
        
        from src.parsers.fcs_parser import FCSParser
        import numpy as np
        
        print(f"\n" + "=" * 70)
        print(f"ANALYZING: {fcs_path.name}")
        print("=" * 70)
        
        parser = FCSParser(fcs_path)
        parser.parse()
        
        print(f"\nTotal Events: {len(parser.data)}")
        print(f"Total Channels: {len(parser.channel_names)}")
        print("\n" + "-" * 70)
        print(f"{'#':<4} | {'Channel':<25} | {'Mean':>12} | {'Max':>12} | {'StdDev':>10}")
        print("-" * 70)
        
        for i, col in enumerate(parser.channel_names, 1):
            if col in parser.data.columns:
                mean_val = parser.data[col].mean()
                max_val = parser.data[col].max()
                std_val = parser.data[col].std()
                print(f"{i:<4} | {col:<25} | {mean_val:>12.1f} | {max_val:>12.1f} | {std_val:>10.1f}")
        
        # Detect channels
        detected_fsc = config.detect_fsc_channel(parser.channel_names)
        detected_ssc = config.detect_ssc_channel(parser.channel_names)
        
        print("\n" + "-" * 70)
        print("DETECTION RESULTS:")
        if detected_fsc:
            print(f"  ✓ FSC detected: {detected_fsc}")
        else:
            print("  ⚠ FSC not detected - using fallback")
        
        if detected_ssc:
            print(f"  ✓ SSC detected: {detected_ssc}")
        else:
            print("  ⚠ SSC not detected - using fallback")
        
        if not detected_fsc or not detected_ssc:
            print("\n" + "-" * 70)
            print("RECOMMENDATION:")
            print("  Examine the statistics above to identify FSC/SSC channels.")
            print("  FSC typically has high mean values (10,000-1,000,000)")
            print("  Then configure with:")
            print("    python configure_channels.py --fsc <channel> --ssc <channel>")
        
        print("=" * 70 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
