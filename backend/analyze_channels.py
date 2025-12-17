"""
Analyze FCS file channels to help with channel mapping.
Run this script to identify FSC/SSC channels for your instrument.

Usage:
    python analyze_channels.py
"""
import sys
sys.path.insert(0, '.')
from src.parsers.fcs_parser import FCSParser
from src.utils.channel_config import get_channel_config
from pathlib import Path

def analyze_fcs_channels():
    """Analyze all FCS files and show channel information."""
    nta_path = Path('nanoFACS')
    fcs_files = list(nta_path.rglob('*.fcs'))
    
    if not fcs_files:
        print("No FCS files found in nanoFACS directory")
        return
    
    print(f"\n{'='*100}")
    print("FCS CHANNEL ANALYSIS TOOL")
    print("=" * 100)
    print(f"Found {len(fcs_files)} FCS files")
    
    # Get channel config
    config = get_channel_config()
    print(f"\n📋 Active Instrument: {config.active_instrument}")
    print(f"📋 Configured FSC channels: {config.get_fsc_channel_names()}")
    print(f"📋 Configured SSC channels: {config.get_ssc_channel_names()}")
    print("=" * 100)
    
    # Analyze each file (or first few)
    for idx, fcs_path in enumerate(fcs_files[:3]):  # Analyze first 3 files
        print(f"\n{'=' * 100}")
        print(f"FILE {idx + 1}: {fcs_path.name}")
        print(f"Path: {fcs_path}")
        print("=" * 100)
        
        try:
            parser = FCSParser(fcs_path)
            parser.parse()
            
            # Print metadata channel info
            print("\n📋 METADATA CHANNEL PARAMETERS:")
            print("-" * 100)
            
            param_info = {}
            for key, value in sorted(parser.metadata.items()):
                key_str = str(key)
                # Look for $P1N, $P1S, etc.
                if key_str.startswith('$P') and any(c.isdigit() for c in key_str):
                    # Extract parameter number
                    import re
                    match = re.match(r'\$P(\d+)([A-Z])', key_str)
                    if match:
                        param_num = int(match.group(1))
                        param_type = match.group(2)
                        
                        if param_num not in param_info:
                            param_info[param_num] = {}
                        param_info[param_num][param_type] = value
            
            # Print organized parameter info
            print(f"{'#':<4} | {'$PnN (Name)':<25} | {'$PnS (Short)':<20} | {'$PnB (Bits)':<10}")
            print("-" * 100)
            for param_num in sorted(param_info.keys()):
                info = param_info[param_num]
                name = info.get('N', '-')
                short = info.get('S', '-')
                bits = info.get('B', '-')
                print(f"{param_num:<4} | {str(name):<25} | {str(short):<20} | {str(bits):<10}")
            
            # Print data statistics
            print("\n📊 DATA COLUMNS WITH STATISTICS:")
            print("-" * 100)
            print(f"{'#':<4} | {'Column Name':<25} | {'Mean':>15} | {'Max':>15} | {'Min':>15} | {'StdDev':>12}")
            print("-" * 100)
            
            for i, col in enumerate(parser.data.columns, 1):
                mean_val = parser.data[col].mean()
                max_val = parser.data[col].max()
                min_val = parser.data[col].min()
                std_val = parser.data[col].std()
                print(f"{i:<4} | {col:<25} | {mean_val:>15.2f} | {max_val:>15.2f} | {min_val:>15.2f} | {std_val:>12.2f}")
            
            print(f"\nTotal events: {len(parser.data)}")
            
            # Suggest FSC/SSC channels based on characteristics
            print("\n🔍 CHANNEL ANALYSIS (for FSC/SSC identification):")
            print("-" * 100)
            
            # Typically FSC and SSC have:
            # - High event counts
            # - Positive values
            # - Distinct distributions for different particle sizes
            
            candidates = []
            for i, col in enumerate(parser.data.columns, 1):
                mean_val = parser.data[col].mean()
                max_val = parser.data[col].max()
                std_val = parser.data[col].std()
                
                # FSC/SSC typically have high variance and positive means
                if mean_val > 0 and std_val > 100:
                    candidates.append({
                        'num': i,
                        'name': col,
                        'mean': mean_val,
                        'max': max_val,
                        'std': std_val,
                        'cv': (std_val / mean_val * 100) if mean_val > 0 else 0
                    })
            
            # Sort by CV (coefficient of variation) - FSC/SSC typically have moderate CV
            candidates.sort(key=lambda x: x['mean'], reverse=True)
            
            print("\nTop candidate channels for FSC/SSC (high mean, high std):")
            for c in candidates[:10]:
                print(f"  Channel {c['num']}: {c['name']:<20} | Mean: {c['mean']:>12.2f} | StdDev: {c['std']:>10.2f} | CV: {c['cv']:.1f}%")
            
        except Exception as e:
            print(f"Error analyzing {fcs_path}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    analyze_fcs_channels()
