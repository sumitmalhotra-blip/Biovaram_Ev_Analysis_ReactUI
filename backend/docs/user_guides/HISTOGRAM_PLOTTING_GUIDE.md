# Histogram Plotting Guide for Flow Cytometry Analysis

## Overview

This guide demonstrates how to create **fluorescence intensity histograms** for marker expression analysis (CD63, CD81, CD9, etc.). Histograms are essential for:

- 📊 **Marker Expression Analysis**: Visualize fluorescence intensity distribution
- 🎯 **Gating**: Determine % positive events with threshold lines
- 📈 **Condition Comparison**: Compare marker expression across samples
- ✅ **Quality Control**: Verify staining and instrument performance

---

## Features

### 1. Single Channel Histogram
- **Purpose**: Analyze individual marker expression
- **Features**:
  - 256-bin resolution (adjustable)
  - Log scale Y-axis for better visualization
  - Mean/median overlay lines
  - Statistical annotations (n, mean, median, min, max)
  - Optional gating threshold with % positive calculation

### 2. Multi-Marker Comparison
- **Purpose**: Compare multiple markers side-by-side
- **Features**:
  - Up to 4 markers in one plot
  - Synchronized scales
  - Individual statistics per marker
  - Color-coded for easy identification
  - Perfect for CD63/CD81/CD9 comparison

---

## Quick Start

### Installation
```bash
# Already included in your environment
pip install matplotlib seaborn pandas numpy
```

### Basic Usage

```python
from pathlib import Path
from src.parsers.fcs_parser import FCSParser
from src.visualization.fcs_plots import FCSPlotter

# Parse FCS file
parser = FCSParser(file_path="path/to/sample.fcs")
data = parser.parse()

# Initialize plotter
plotter = FCSPlotter(output_dir="figures/histograms")

# Single marker histogram
plotter.plot_histogram(
    data=data,
    channel='V447-A',  # CD81 channel
    output_file="cd81_histogram.png",
    bins=256,
    log_scale=True,
    gate_threshold=1000,  # Positive/negative threshold
    show_stats=True
)

# Multi-marker comparison
plotter.plot_marker_histograms(
    data=data,
    marker_channels=['V447-A', 'B531-A', 'Y595-A', 'R670-A'],
    output_file="marker_comparison.png",
    bins=256,
    log_scale=True,
    gate_thresholds={'V447-A': 1000, 'B531-A': 800}
)
```

---

## Method Reference

### `plot_histogram()`

Create single-channel fluorescence histogram.

**Parameters:**
- `data` (DataFrame): FCS event data
- `channel` (str): Channel name (e.g., 'V447-A' for CD81)
- `title` (str, optional): Plot title (auto-generated if None)
- `output_file` (Path, optional): Save path
- `bins` (int): Number of histogram bins (default: 256)
- `log_scale` (bool): Use log scale for Y-axis (default: True)
- `gate_threshold` (float, optional): Threshold for gating
- `show_stats` (bool): Show statistics box (default: True)
- `color` (str): Histogram color (default: 'steelblue')

**Returns:** `matplotlib.Figure`

**Example:**
```python
fig = plotter.plot_histogram(
    data=data,
    channel='V447-A',
    output_file="cd81_histogram.png",
    gate_threshold=1000
)
```

---

### `plot_marker_histograms()`

Create multi-panel comparison plot for 2-4 markers.

**Parameters:**
- `data` (DataFrame): FCS event data
- `marker_channels` (List[str], optional): List of channels (auto-detect if None)
- `output_file` (Path, optional): Save path
- `bins` (int): Number of histogram bins (default: 256)
- `log_scale` (bool): Use log scale (default: True)
- `gate_thresholds` (dict, optional): Dict mapping channels to thresholds

**Returns:** `matplotlib.Figure`

**Example:**
```python
fig = plotter.plot_marker_histograms(
    data=data,
    marker_channels=['V447-A', 'B531-A', 'Y595-A'],
    output_file="cd81_cd63_cd9_comparison.png",
    gate_thresholds={
        'V447-A': 1000,  # CD81 threshold
        'B531-A': 800,   # CD63 threshold
        'Y595-A': 900    # CD9 threshold
    }
)
```

---

## Batch Processing

### Automatic Histogram Generation

The `batch_fcs_quick.py` script now **automatically generates histograms** for all fluorescence channels:

```bash
python scripts/batch_fcs_quick.py
```

**Output per file:**
1. `{sample}_scatter.png` - FSC vs SSC density plot
2. `{sample}_histograms.png` - Multi-marker comparison histogram

**Example output:**
```
figures/fcs_batch/
├── Exo+CD81_scatter.png
├── Exo+CD81_histograms.png
├── Exo+CD63_scatter.png
├── Exo+CD63_histograms.png
└── ...
```

---

## Use Cases

### 1. Determining % Positive Events

```python
# Set gate threshold to distinguish positive from negative
plotter.plot_histogram(
    data=data,
    channel='V447-A',
    gate_threshold=1000,  # Events > 1000 = positive
    output_file="cd81_gating.png"
)
# Displays "Positive: XX.X%" on plot
```

### 2. Comparing Antibody Conditions

```python
# Compare different antibody concentrations
samples = {
    '0.25ug': 'Exo + 0.25ug CD81.fcs',
    '1ug': 'Exo + 1ug CD81.fcs',
    '2ug': 'Exo + 2ug CD81.fcs'
}

for label, file in samples.items():
    parser = FCSParser(file_path=file)
    data = parser.parse()
    
    plotter.plot_histogram(
        data=data,
        channel='V447-A',
        title=f'CD81 Expression - {label}',
        output_file=f'cd81_{label}.png',
        gate_threshold=1000
    )
```

### 3. Multi-Marker Phenotyping

```python
# Analyze CD63+/CD81+/CD9+ exosomes
marker_map = {
    'V447-A': 'CD81',
    'B531-A': 'CD63',
    'Y595-A': 'CD9'
}

plotter.plot_marker_histograms(
    data=data,
    marker_channels=list(marker_map.keys()),
    output_file="exosome_phenotype.png",
    gate_thresholds={ch: 1000 for ch in marker_map.keys()}
)
```

### 4. Quality Control Check

```python
# Compare blank vs sample
blank_data = FCSParser(file_path='blank.fcs').parse()
sample_data = FCSParser(file_path='sample.fcs').parse()

# Overlay histograms for QC
for channel in ['V447-A', 'B531-A']:
    # Create individual plots for comparison
    plotter.plot_histogram(blank_data, channel, 
                          output_file=f"{channel}_blank.png")
    plotter.plot_histogram(sample_data, channel,
                          output_file=f"{channel}_sample.png")
```

---

## Interpretation Guide

### Histogram Features

1. **Peak Position**
   - Low intensity peak → Negative/unstained population
   - High intensity peak → Positive/stained population

2. **Peak Width**
   - Narrow peak → Uniform expression
   - Broad peak → Heterogeneous population

3. **Multiple Peaks**
   - Two distinct peaks → Clear positive/negative separation
   - Overlapping peaks → May need gate adjustment

### Statistical Metrics

- **Mean**: Average fluorescence intensity (affected by outliers)
- **Median**: Middle value (robust to outliers) - **preferred**
- **% Positive**: Percentage of events above gate threshold

### Gating Best Practices

1. Use **control samples** (blank, isotype) to set gates
2. Position gate at **valley between populations** (if visible)
3. Use **2-3 standard deviations** above negative peak
4. Aim for **<5% positive in negative control**

---

## Output Specifications

### File Format
- **Format**: PNG (300 DPI)
- **Size**: ~150-300 KB per histogram
- **Resolution**: Publication-quality

### Plot Layout

**Single Histogram:**
- Size: 10" × 6"
- Title: Channel name + sample ID
- X-axis: Fluorescence intensity
- Y-axis: Count (log scale)
- Statistics box: Upper left
- Gate annotation: Upper right (if threshold set)

**Multi-Marker Comparison:**
- Size: 5n" × 5" (n = number of markers)
- Individual panels for each marker
- Shared Y-axis label
- Individual statistics per panel
- Overall title at top

---

## Troubleshooting

### Issue: No fluorescence channels detected
**Solution:** Check channel naming convention. Adjust detection pattern in code:
```python
fl_channels = [col for col in data.columns 
              if col.startswith(('V4', 'B5', 'Y5', 'R6', 'R7'))
              and col.endswith('-A')]
```

### Issue: Histogram looks flat/compressed
**Solution:** Enable log scale:
```python
plotter.plot_histogram(..., log_scale=True)
```

### Issue: Gate threshold not showing % positive
**Solution:** Ensure gate_threshold parameter is set:
```python
plotter.plot_histogram(..., gate_threshold=1000)
```

### Issue: Too many markers in comparison plot
**Solution:** Limit to 4 markers for clean layout:
```python
plotter.plot_marker_histograms(
    marker_channels=fl_channels[:4],  # First 4 only
    ...
)
```

---

## Examples Gallery

### Example 1: CD81 Expression
![CD81 Histogram](../figures/histogram_demo/histogram_V447-A.png)

### Example 2: Multi-Marker Comparison
![Marker Comparison](../figures/histogram_demo/marker_comparison_histograms.png)

---

## Advanced Usage

### Custom Color Schemes
```python
plotter.plot_histogram(
    data=data,
    channel='V447-A',
    color='coral',  # Change histogram color
    output_file="cd81_custom.png"
)
```

### Adjust Bin Resolution
```python
# Higher resolution (more bins)
plotter.plot_histogram(..., bins=512)

# Lower resolution (fewer bins)
plotter.plot_histogram(..., bins=128)
```

### Linear Scale (instead of log)
```python
plotter.plot_histogram(
    data=data,
    channel='V447-A',
    log_scale=False,  # Use linear scale
    output_file="cd81_linear.png"
)
```

---

## Performance Notes

- **Processing time**: ~1-2 seconds per histogram (300K events)
- **Memory usage**: ~50-100 MB per file
- **Batch processing**: ~20 files per minute
- **Recommended**: Use `sample_size` parameter for very large datasets (>1M events)

---

## Related Documentation

- [FCS_PLOTTING_GUIDE.md](FCS_PLOTTING_GUIDE.md) - Scatter plot documentation
- [BATCH_PROCESSING.md](../BATCH_PROCESSING.md) - Batch processing workflows
- [API_REFERENCE.md](../API_REFERENCE.md) - Full API documentation

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review example scripts in `scripts/`
3. Examine test outputs in `figures/histogram_demo/`

---

**Last Updated:** November 15, 2025  
**Version:** 1.0  
**Author:** GitHub Copilot
