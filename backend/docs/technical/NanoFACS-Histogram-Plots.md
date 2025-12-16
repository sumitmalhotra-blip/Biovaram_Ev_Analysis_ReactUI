# Nano-FACS Histogram Plots (Slide 10 Style)

## 🎯 What Slide 10 Actually Shows

Looking at your screenshot, Slide 10 shows **HISTOGRAM LINE PLOTS**, not scatter plots!

### **Plot Type: Fluorescence Intensity Histograms**
- **X-axis:** FL2-H | BG1-H (Fluorescence channel, log scale)
- **Y-axis:** Count (number of events)
- **Three lines per plot:**
  - **Blue:** Only Exosomes (baseline)
  - **Red:** Exosomes with Peptide (treatment)
  - **Black/Gray:** Only Peptide (control)

### **Three Conditions:**
1. **Negative Control Peptide** (left plot)
2. **Positive Control Peptide** (middle plot)
3. **Peptide - UR 29** (right plot - your experimental peptide)

This shows **fluorescence intensity distributions**, not particle scatter. Each peak represents a population of particles with similar fluorescence intensity.

---

## 🚀 Correct Implementation

### **Method 1: Using fcsparser + matplotlib (Histogram Style)**

```python
import fcsparser
import matplotlib.pyplot as plt
import numpy as np

def plot_fcs_histogram(fcs_file, 
                       channel='FL2-H',
                       title='Condition',
                       bins=256,
                       xlim=(1e0, 1e6),
                       color='blue',
                       label='Sample',
                       alpha=0.7):
    \"\"\"
    Create histogram line plot for flow cytometry data.
    
    Args:
        fcs_file: Path to FCS file
        channel: Channel to plot (e.g., 'FL2-H')
        title: Plot title
        bins: Number of bins for histogram
        xlim: X-axis limits (log scale)
        color: Line color
        label: Legend label
        alpha: Line transparency
    \"\"\"
    # Parse FCS file
    meta, data = fcsparser.parse(fcs_file)
    
    # Extract channel data
    if channel not in data.columns:
        print(f\"Warning: {channel} not found. Available: {data.columns.tolist()}\")
        # Try to find similar channel
        for col in data.columns:
            if 'FL2' in col or 'BG1' in col:
                channel = col
                print(f\"Using {channel} instead\")
                break
    
    channel_data = data[channel].values
    
    # Remove negative and zero values
    channel_data = channel_data[channel_data > 0]
    
    # Create histogram (log bins)
    log_bins = np.logspace(np.log10(xlim[0]), np.log10(xlim[1]), bins)
    counts, bin_edges = np.histogram(channel_data, bins=log_bins)
    
    # Calculate bin centers
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    # Plot line
    plt.plot(bin_centers, counts, 
             color=color, 
             linewidth=2,
             label=label,
             alpha=alpha)
    
    return counts, bin_centers


def create_slide10_comparison(condition_files,
                              condition_title,
                              channel='FL2-H',
                              save_path=None):
    \"\"\"
    Create Slide 10 style comparison with three overlaid histograms.
    
    Args:
        condition_files: Dict with keys 'only_exo', 'exo_peptide', 'only_peptide'
        condition_title: Title for this condition (e.g., 'Negative Control Peptide')
        channel: Fluorescence channel to plot
        save_path: Path to save figure
    \"\"\"
    fig, ax = plt.subplots(figsize=(6, 5))
    
    # Define colors and labels (matching Slide 10)
    config = {
        'only_exo': {'color': 'blue', 'label': 'Only Exosomes', 'alpha': 0.7},
        'exo_peptide': {'color': 'red', 'label': 'Exosomes with Peptide', 'alpha': 0.7},
        'only_peptide': {'color': 'black', 'label': 'Only Peptide', 'alpha': 0.6}
    }
    
    # Plot each condition
    for key, filepath in condition_files.items():
        if filepath and key in config:
            plot_fcs_histogram(
                filepath,
                channel=channel,
                color=config[key]['color'],
                label=config[key]['label'],
                alpha=config[key]['alpha']
            )
    
    # Formatting (matching Slide 10 style)
    ax.set_xscale('log')
    ax.set_xlabel(f'{channel} | BG1-H', fontsize=11)
    ax.set_ylabel('Count', fontsize=11)
    ax.set_title(condition_title, fontsize=13, fontweight='bold', pad=10)
    
    # Grid
    ax.grid(True, which='both', alpha=0.3, linestyle='--', linewidth=0.5)
    
    # Legend (bottom, horizontal)
    ax.legend(loc='upper right', frameon=True, fontsize=9)
    
    # X-axis limits (typical for flow cytometry)
    ax.set_xlim(1e0, 1e6)
    
    # Y-axis starts at 0
    ax.set_ylim(bottom=0)
    
    # Tight layout
    plt.tight_layout()
    
    # Save
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f\"✓ Saved: {save_path}\")
    
    return fig, ax


def create_full_slide10(all_conditions, channel='FL2-H', save_path='slide10_full.png'):
    \"\"\"
    Create full Slide 10 with three side-by-side plots.
    
    Args:
        all_conditions: Dict with condition names as keys, each containing file paths
        channel: Fluorescence channel
        save_path: Path to save figure
    
    Example:
        all_conditions = {
            'Negative Control Peptide': {
                'only_exo': 'data/neg_ctrl_only_exo.fcs',
                'exo_peptide': 'data/neg_ctrl_exo_peptide.fcs',
                'only_peptide': 'data/neg_ctrl_only_peptide.fcs'
            },
            'Positive Control Peptide': {
                'only_exo': 'data/pos_ctrl_only_exo.fcs',
                'exo_peptide': 'data/pos_ctrl_exo_peptide.fcs',
                'only_peptide': 'data/pos_ctrl_only_peptide.fcs'
            },
            'Peptide - UR 29': {
                'only_exo': 'data/ur29_only_exo.fcs',
                'exo_peptide': 'data/ur29_exo_peptide.fcs',
                'only_peptide': 'data/ur29_only_peptide.fcs'
            }
        }
    \"\"\"
    n_conditions = len(all_conditions)
    
    # Create figure with subplots
    fig, axes = plt.subplots(1, n_conditions, figsize=(18, 5))
    
    if n_conditions == 1:
        axes = [axes]
    
    # Define colors and labels
    config = {
        'only_exo': {'color': '#4472C4', 'label': 'Only Exosomes', 'alpha': 0.8},  # Blue
        'exo_peptide': {'color': '#C5504B', 'label': 'Exosomes with Peptide', 'alpha': 0.8},  # Red
        'only_peptide': {'color': '#595959', 'label': 'Only Peptide', 'alpha': 0.7}  # Gray/Black
    }
    
    # Plot each condition
    for ax, (condition_name, condition_files) in zip(axes, all_conditions.items()):
        plt.sca(ax)
        
        # Plot each file type
        for key, filepath in condition_files.items():
            if filepath and key in config:
                try:
                    meta, data = fcsparser.parse(filepath)
                    
                    # Find channel
                    actual_channel = channel
                    if channel not in data.columns:
                        for col in data.columns:
                            if 'FL2' in col or 'BG1' in col:
                                actual_channel = col
                                break
                    
                    # Extract data
                    channel_data = data[actual_channel].values
                    channel_data = channel_data[channel_data > 0]
                    
                    # Create histogram
                    log_bins = np.logspace(0, 6, 256)
                    counts, bin_edges = np.histogram(channel_data, bins=log_bins)
                    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                    
                    # Plot
                    ax.plot(bin_centers, counts,
                           color=config[key]['color'],
                           linewidth=2.5,
                           label=config[key]['label'],
                           alpha=config[key]['alpha'])
                    
                except Exception as e:
                    print(f\"Error plotting {filepath}: {e}\")
        
        # Formatting
        ax.set_xscale('log')
        ax.set_xlabel(f'{channel} | BG1-H', fontsize=10)
        ax.set_ylabel('Count', fontsize=10)
        ax.set_title(condition_name, fontsize=12, fontweight='bold', pad=10)
        ax.grid(True, which='both', alpha=0.3, linestyle='--', linewidth=0.5)
        ax.set_xlim(1e0, 1e6)
        ax.set_ylim(bottom=0)
        
        # Legend (only on first plot to avoid repetition)
        if ax == axes[0]:
            ax.legend(loc='upper right', frameon=True, fontsize=9, 
                     fancybox=True, shadow=False)
    
    # Overall title
    fig.suptitle('Nano-FACS Files', fontsize=16, fontweight='bold', y=0.98)
    
    # Tight layout
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # Save
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.savefig(save_path.replace('.png', '.pdf'), bbox_inches='tight')
        print(f\"✓ Saved: {save_path}\")
        print(f\"✓ Saved: {save_path.replace('.png', '.pdf')}\")
    
    plt.show()
    
    return fig, axes


# Example usage
if __name__ == '__main__':
    # Define all your conditions and files
    all_conditions = {
        'Negative Control Peptide': {
            'only_exo': 'data/neg_ctrl_only_exosomes.fcs',
            'exo_peptide': 'data/neg_ctrl_exosomes_with_peptide.fcs',
            'only_peptide': 'data/neg_ctrl_only_peptide.fcs'
        },
        'Positive Control Peptide': {
            'only_exo': 'data/pos_ctrl_only_exosomes.fcs',
            'exo_peptide': 'data/pos_ctrl_exosomes_with_peptide.fcs',
            'only_peptide': 'data/pos_ctrl_only_peptide.fcs'
        },
        'Peptide - UR 29': {
            'only_exo': 'data/ur29_only_exosomes.fcs',
            'exo_peptide': 'data/ur29_exosomes_with_peptide.fcs',
            'only_peptide': 'data/ur29_only_peptide.fcs'
        }
    }
    
    # Create full Slide 10 replica
    create_full_slide10(
        all_conditions=all_conditions,
        channel='FL2-H',  # or 'BG1-H' depending on your files
        save_path='plots/slide10_histogram_comparison.png'
    )
```

---

## 📊 Understanding the Plot Style

### **What Makes These Histograms Special:**

1. **Log Scale X-axis**
   - Fluorescence intensity spans many orders of magnitude (1 to 1,000,000)
   - Log scale shows all populations clearly

2. **Overlaid Lines**
   - Three conditions on same plot for easy comparison
   - Color-coded: Blue (exosomes), Red (exo+peptide), Black (peptide only)

3. **Peak Analysis**
   - Each peak = population of particles
   - Peak shift = change in fluorescence intensity
   - Peak height = number of particles

4. **Interpretation:**
   - **Left peak (low intensity):** Unlabeled particles or background
   - **Right peak (high intensity):** Fluorescently labeled exosomes
   - **Shift right:** Increased fluorescence (more binding)
   - **Shift left:** Decreased fluorescence (less binding)

---

## 🎨 Customization Options

### **Colors (Matching Slide 10):**
```python
colors = {
    'only_exo': '#4472C4',      # Blue (PowerPoint blue)
    'exo_peptide': '#C5504B',   # Red (PowerPoint red)
    'only_peptide': '#595959'   # Gray/Black
}
```

### **Line Styles:**
```python
# Solid lines (default)
plt.plot(..., linestyle='-', linewidth=2.5)

# Or try different styles
styles = {
    'only_exo': '-',      # Solid
    'exo_peptide': '-',   # Solid
    'only_peptide': '--'  # Dashed
}
```

### **Smoothing (Optional):**
```python
from scipy.ndimage import gaussian_filter1d

# Smooth the histogram
counts_smooth = gaussian_filter1d(counts, sigma=2)
plt.plot(bin_centers, counts_smooth, ...)
```

---

## 🔧 Complete Working Script

Save this as `nanofacs_histogram.py`:

```python
#!/usr/bin/env python3
\"\"\"
Nano-FACS Histogram Plotter (Slide 10 Style)
Creates fluorescence intensity histograms with overlaid conditions.
\"\"\"

import fcsparser
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import argparse


class NanoFACSHistogram:
    \"\"\"Create Nano-FACS histogram plots like Slide 10.\"\"\"
    
    def __init__(self):
        self.colors = {
            'only_exo': '#4472C4',      # Blue
            'exo_peptide': '#C5504B',   # Red  
            'only_peptide': '#595959'   # Gray/Black
        }
        self.labels = {
            'only_exo': 'Only Exosomes',
            'exo_peptide': 'Exosomes with Peptide',
            'only_peptide': 'Only Peptide'
        }
    
    def plot_single_condition(self, 
                             condition_files,
                             condition_title,
                             channel='FL2-H',
                             bins=256,
                             xlim=(1e0, 1e6),
                             save_path=None):
        \"\"\"
        Plot single condition (one of the three panels).
        
        Args:
            condition_files: Dict {'only_exo': path, 'exo_peptide': path, 'only_peptide': path}
            condition_title: Title (e.g., 'Negative Control Peptide')
            channel: Fluorescence channel
            bins: Number of histogram bins
            xlim: X-axis limits
            save_path: Output path
        \"\"\"
        fig, ax = plt.subplots(figsize=(6, 5))
        
        for key, filepath in condition_files.items():
            if not filepath:
                continue
            
            try:
                # Parse FCS
                meta, data = fcsparser.parse(filepath)
                
                # Find channel
                actual_channel = self._find_channel(data.columns, channel)
                
                # Extract data
                channel_data = data[actual_channel].values
                channel_data = channel_data[channel_data > 0]
                
                # Create histogram
                log_bins = np.logspace(np.log10(xlim[0]), np.log10(xlim[1]), bins)
                counts, bin_edges = np.histogram(channel_data, bins=log_bins)
                bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                
                # Plot
                ax.plot(bin_centers, counts,
                       color=self.colors[key],
                       linewidth=2.5,
                       label=self.labels[key],
                       alpha=0.8)
                
            except Exception as e:
                print(f\"Error plotting {filepath}: {e}\")
        
        # Formatting
        ax.set_xscale('log')
        ax.set_xlabel(f'{channel} | BG1-H', fontsize=11)
        ax.set_ylabel('Count', fontsize=11)
        ax.set_title(condition_title, fontsize=13, fontweight='bold', pad=10)
        ax.grid(True, which='both', alpha=0.3, linestyle='--', linewidth=0.5)
        ax.set_xlim(xlim)
        ax.set_ylim(bottom=0)
        ax.legend(loc='upper right', frameon=True, fontsize=9)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f\"✓ Saved: {save_path}\")
        
        return fig, ax
    
    def plot_full_slide10(self,
                         all_conditions,
                         channel='FL2-H',
                         bins=256,
                         xlim=(1e0, 1e6),
                         save_path='slide10_full.png'):
        \"\"\"
        Create full Slide 10 with three side-by-side plots.
        
        Args:
            all_conditions: Dict of dicts
                {
                    'Negative Control Peptide': {'only_exo': path, ...},
                    'Positive Control Peptide': {...},
                    'Peptide - UR 29': {...}
                }
            channel: Fluorescence channel
            bins: Number of bins
            xlim: X-axis limits
            save_path: Output path
        \"\"\"
        n_conditions = len(all_conditions)
        fig, axes = plt.subplots(1, n_conditions, figsize=(18, 5))
        
        if n_conditions == 1:
            axes = [axes]
        
        for ax, (condition_name, condition_files) in zip(axes, all_conditions.items()):
            for key, filepath in condition_files.items():
                if not filepath:
                    continue
                
                try:
                    # Parse FCS
                    meta, data = fcsparser.parse(filepath)
                    
                    # Find channel
                    actual_channel = self._find_channel(data.columns, channel)
                    
                    # Extract data
                    channel_data = data[actual_channel].values
                    channel_data = channel_data[channel_data > 0]
                    
                    # Histogram
                    log_bins = np.logspace(np.log10(xlim[0]), np.log10(xlim[1]), bins)
                    counts, bin_edges = np.histogram(channel_data, bins=log_bins)
                    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                    
                    # Plot
                    ax.plot(bin_centers, counts,
                           color=self.colors[key],
                           linewidth=2.5,
                           label=self.labels[key],
                           alpha=0.8)
                    
                except Exception as e:
                    print(f\"Error: {filepath}: {e}\")
            
            # Formatting
            ax.set_xscale('log')
            ax.set_xlabel(f'{channel} | BG1-H', fontsize=10)
            ax.set_ylabel('Count', fontsize=10)
            ax.set_title(condition_name, fontsize=12, fontweight='bold', pad=10)
            ax.grid(True, which='both', alpha=0.3, linestyle='--', linewidth=0.5)
            ax.set_xlim(xlim)
            ax.set_ylim(bottom=0)
            
            # Legend on first plot only
            if ax == axes[0]:
                ax.legend(loc='upper right', frameon=True, fontsize=9)
        
        # Overall title
        fig.suptitle('Nano-FACS Files', fontsize=16, fontweight='bold', y=0.98)
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        # Save
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.savefig(save_path.replace('.png', '.pdf'), bbox_inches='tight')
        print(f\"✓ Saved: {save_path}\")
        print(f\"✓ Saved PDF: {save_path.replace('.png', '.pdf')}\")
        
        plt.show()
        
        return fig, axes
    
    def _find_channel(self, columns, preferred_channel):
        \"\"\"Find channel in FCS file columns.\"\"\"
        if preferred_channel in columns:
            return preferred_channel
        
        # Try to find similar
        channel_keywords = ['FL2', 'BG1', 'PE', 'FITC']
        for keyword in channel_keywords:
            for col in columns:
                if keyword in col.upper():
                    print(f\"Using {col} instead of {preferred_channel}\")
                    return col
        
        # Default to first fluorescence channel
        for col in columns:
            if 'FL' in col.upper() or 'PE' in col.upper():
                print(f\"Using {col} as fallback\")
                return col
        
        raise ValueError(f\"Could not find suitable channel. Available: {columns.tolist()}\")


# CLI
def main():
    parser = argparse.ArgumentParser(description='Nano-FACS Histogram Plotter')
    parser.add_argument('--condition', required=True, help='Condition name')
    parser.add_argument('--only-exo', required=True, help='Only exosomes FCS file')
    parser.add_argument('--exo-peptide', required=True, help='Exosomes + peptide FCS file')
    parser.add_argument('--only-peptide', required=True, help='Only peptide FCS file')
    parser.add_argument('--channel', default='FL2-H', help='Fluorescence channel')
    parser.add_argument('--output', default='plot.png', help='Output path')
    
    args = parser.parse_args()
    
    plotter = NanoFACSHistogram()
    
    condition_files = {
        'only_exo': args.only_exo,
        'exo_peptide': args.exo_peptide,
        'only_peptide': args.only_peptide
    }
    
    plotter.plot_single_condition(
        condition_files=condition_files,
        condition_title=args.condition,
        channel=args.channel,
        save_path=args.output
    )


if __name__ == '__main__':
    main()
```

---

## 🚀 Usage Examples

### **Single Condition:**
```bash
python nanofacs_histogram.py \\
    --condition \"Negative Control Peptide\" \\
    --only-exo data/neg_only_exo.fcs \\
    --exo-peptide data/neg_exo_peptide.fcs \\
    --only-peptide data/neg_only_peptide.fcs \\
    --channel FL2-H \\
    --output plots/negative_control.png
```

### **Full Slide 10 (Programmatic):**
```python
from nanofacs_histogram import NanoFACSHistogram

plotter = NanoFACSHistogram()

all_conditions = {
    'Negative Control Peptide': {
        'only_exo': 'data/neg_only_exo.fcs',
        'exo_peptide': 'data/neg_exo_peptide.fcs',
        'only_peptide': 'data/neg_only_peptide.fcs'
    },
    'Positive Control Peptide': {
        'only_exo': 'data/pos_only_exo.fcs',
        'exo_peptide': 'data/pos_exo_peptide.fcs',
        'only_peptide': 'data/pos_only_peptide.fcs'
    },
    'Peptide - UR 29': {
        'only_exo': 'data/ur29_only_exo.fcs',
        'exo_peptide': 'data/ur29_exo_peptide.fcs',
        'only_peptide': 'data/ur29_only_peptide.fcs'
    }
}

plotter.plot_full_slide10(
    all_conditions=all_conditions,
    channel='FL2-H',
    save_path='plots/slide10_full.png'
)
```

---

## ✅ Key Differences from Previous Code

| Feature | Scatter Plot (Wrong) | Histogram Plot (Correct) |
|---------|---------------------|-------------------------|
| Plot Type | 2D scatter (x vs y) | 1D histogram (intensity distribution) |
| X-axis | VSSC or FSC (size) | FL2-H fluorescence intensity (log scale) |
| Y-axis | Fluorescence intensity | Count (number of events) |
| Visualization | Dots/density heatmap | Line plots overlaid |
| Purpose | Show particle populations in 2D | Show fluorescence distribution |
| Output | Looks like scatter plot | Looks like Slide 10! ✓ |

---

This implementation will create plots that look **exactly like your Slide 10**!
