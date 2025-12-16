"""
Batch FCS Visualization Pipeline
=================================

Processes all FCS samples and generates comprehensive visualizations:
- Scatter plots (density + hexbin)
- Histograms (multi-channel)
- Summary report with thumbnails

Author: CRMIT Analysis Team
Date: November 17, 2025
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
from datetime import datetime
import warnings
import json
from typing import Dict, List, Tuple, Optional
import base64
from io import BytesIO

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.visualization.fcs_plots import FCSPlotter
from src.visualization.auto_axis_selector import AutoAxisSelector

warnings.filterwarnings('ignore')

# Configuration
OUTPUT_DIR = project_root / 'figures' / 'batch_fcs'
REPORTS_DIR = project_root / 'reports'
DATA_DIR = project_root / 'data' / 'processed'
THUMBNAIL_SIZE = (400, 300)
SAMPLE_SIZE = 50000  # Events to plot (for performance)

# Plot types to generate
PLOT_TYPES = {
    'scatter_density': True,
    'scatter_hexbin': True,
    'histogram_grid': True,
}


class FCSBatchVisualizer:
    """Batch visualization pipeline for FCS data."""
    
    def __init__(self, output_dir: Path, sample_size: int = 50000):
        """
        Initialize batch visualizer.
        
        Args:
            output_dir: Directory to save plots
            sample_size: Number of events to plot per sample
        """
        self.output_dir = Path(output_dir)
        self.sample_size = sample_size
        self.plotter = FCSPlotter()
        self.axis_selector = AutoAxisSelector()
        
        # Create output directories
        (self.output_dir / 'scatter_density').mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'scatter_hexbin').mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'histogram_grid').mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'thumbnails').mkdir(parents=True, exist_ok=True)
        
        # Statistics tracking
        self.stats = {
            'total_samples': 0,
            'processed': 0,
            'failed': 0,
            'plots_generated': 0,
            'processing_time': 0,
            'failures': []
        }
    
    def load_fcs_statistics(self, stats_file: Path) -> pd.DataFrame:
        """Load FCS statistics file."""
        print(f"📂 Loading FCS statistics from: {stats_file}")
        df = pd.read_parquet(stats_file)
        print(f"   ✅ Loaded {len(df)} samples")
        return df
    
    def get_sample_data(self, sample_id: str, fcs_file_path: str) -> Optional[pd.DataFrame]:
        """
        Load event data for a specific sample from FCS file.
        
        Args:
            sample_id: Sample identifier
            fcs_file_path: Path to FCS file
            
        Returns:
            DataFrame with event data or None if not found
        """
        try:
            import fcsparser
            
            fcs_path = Path(fcs_file_path)
            if not fcs_path.exists():
                print(f"   ⚠️  FCS file not found: {fcs_path}")
                return None
            
            # Parse FCS file
            print(f"   📂 Reading FCS file: {fcs_path.name}")
            meta, data = fcsparser.parse(str(fcs_path), reformat_meta=True)
            
            # Sample if too many events
            if len(data) > self.sample_size:
                data = data.sample(n=self.sample_size, random_state=42)
            
            return data
        except Exception as e:
            print(f"   ❌ Error loading {sample_id}: {e}")
            return None
    
    def generate_scatter_density(self, sample_id: str, data: pd.DataFrame, 
                                 x_channel: str, y_channel: str) -> Optional[Path]:
        """Generate density scatter plot."""
        try:
            output_file = self.output_dir / 'scatter_density' / f"{sample_id}_density.png"
            
            fig, ax = plt.subplots(figsize=(8, 6))
            
            # Create density plot
            x_data = np.asarray(data[x_channel].values, dtype=np.float64)
            y_data = np.asarray(data[y_channel].values, dtype=np.float64)
            
            # Create a mask for valid data points (both x and y > 0 and < 99th percentile)
            x_valid = (x_data > 0) & (x_data < np.percentile(x_data[x_data > 0], 99))
            y_valid = (y_data > 0) & (y_data < np.percentile(y_data[y_data > 0], 99))
            valid_mask = x_valid & y_valid
            
            x_data = x_data[valid_mask]
            y_data = y_data[valid_mask]
            
            # Plot with log scale
            ax.hexbin(x_data, y_data, gridsize=100, cmap='viridis', 
                     xscale='log', yscale='log', mincnt=1)
            
            ax.set_xlabel(x_channel, fontsize=12)
            ax.set_ylabel(y_channel, fontsize=12)
            ax.set_title(f'{sample_id} - Density Plot', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            plt.close()
            
            return output_file
        except Exception as e:
            print(f"      ❌ Scatter density failed: {e}")
            return None
    
    def generate_scatter_hexbin(self, sample_id: str, data: pd.DataFrame,
                               x_channel: str, y_channel: str) -> Optional[Path]:
        """Generate hexbin scatter plot."""
        try:
            output_file = self.output_dir / 'scatter_hexbin' / f"{sample_id}_hexbin.png"
            
            fig, ax = plt.subplots(figsize=(8, 6))
            
            x_data = np.asarray(data[x_channel].values, dtype=np.float64)
            y_data = np.asarray(data[y_channel].values, dtype=np.float64)
            
            # Create a mask for valid data points
            x_valid = (x_data > 0) & (x_data < np.percentile(x_data[x_data > 0], 99))
            y_valid = (y_data > 0) & (y_data < np.percentile(y_data[y_data > 0], 99))
            valid_mask = x_valid & y_valid
            
            x_data = x_data[valid_mask]
            y_data = y_data[valid_mask]
            
            # Hexbin plot
            hexbin = ax.hexbin(x_data, y_data, gridsize=80, cmap='plasma',
                              xscale='log', yscale='log', mincnt=1, alpha=0.8)
            
            plt.colorbar(hexbin, ax=ax, label='Count')
            
            ax.set_xlabel(x_channel, fontsize=12)
            ax.set_ylabel(y_channel, fontsize=12)
            ax.set_title(f'{sample_id} - Hexbin Plot', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            plt.close()
            
            return output_file
        except Exception as e:
            print(f"      ❌ Scatter hexbin failed: {e}")
            return None
    
    def generate_histogram_grid(self, sample_id: str, data: pd.DataFrame) -> Optional[Path]:
        """Generate multi-channel histogram grid."""
        try:
            output_file = self.output_dir / 'histogram_grid' / f"{sample_id}_histograms.png"
            
            # Select key channels (up to 6)
            channels = [col for col in data.columns if col not in ['Time', 'sample_id']][:6]
            
            n_channels = len(channels)
            n_cols = 3
            n_rows = (n_channels + n_cols - 1) // n_cols
            
            fig, axes_obj = plt.subplots(n_rows, n_cols, figsize=(15, n_rows * 4))
            from matplotlib.axes import Axes
            axes: list[Axes] = list(np.ravel(axes_obj)) if n_channels > 1 else [axes_obj]  # type: ignore[list-item]
            
            for idx, channel in enumerate(channels):
                ax = axes[idx]
                
                # Get data
                channel_data = np.asarray(data[channel].values, dtype=np.float64)
                channel_data = channel_data[channel_data > 0]  # Remove zeros for log scale
                
                if len(channel_data) > 0:
                    # Histogram with log scale
                    ax.hist(channel_data, bins=100, color='steelblue', 
                           alpha=0.7, edgecolor='black')
                    ax.set_xlabel(channel, fontsize=10)
                    ax.set_ylabel('Frequency', fontsize=10)
                    ax.set_title(f'{channel} Distribution', fontsize=11, fontweight='bold')
                    ax.set_xscale('log')
                    ax.grid(True, alpha=0.3)
                    
                    # Add statistics
                    median = float(np.median(channel_data))
                    mean = float(np.mean(channel_data))
                    ax.axvline(median, color='red', linestyle='--', 
                              label=f'Median: {median:.1f}')
                    ax.axvline(mean, color='orange', linestyle='--',
                              label=f'Mean: {mean:.1f}')
                    ax.legend(fontsize=8)
            
            # Hide unused subplots
            for idx in range(n_channels, len(axes)):
                axes[idx].axis('off')
            
            fig.suptitle(f'{sample_id} - Channel Distributions', 
                        fontsize=16, fontweight='bold', y=0.995)
            
            plt.tight_layout()
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            plt.close()
            
            return output_file
        except Exception as e:
            print(f"      ❌ Histogram grid failed: {e}")
            return None
    
    def create_thumbnail(self, image_path: Path) -> Path:
        """Create thumbnail version of plot."""
        try:
            from PIL import Image
            
            img = Image.open(image_path)
            img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            
            thumbnail_path = self.output_dir / 'thumbnails' / image_path.name
            img.save(thumbnail_path, 'PNG', optimize=True)
            
            return thumbnail_path
        except Exception as e:
            print(f"      ⚠️  Thumbnail creation failed: {e}")
            return image_path  # Return original if thumbnail fails
    
    def process_sample(self, row: pd.Series) -> Dict:
        """
        Process a single FCS sample.
        
        Args:
            row: Sample statistics row
            
        Returns:
            Dictionary with processing results
        """
        sample_id = str(row['sample_id'])
        print(f"\n🔬 Processing: {sample_id}")
        
        result = {
            'sample_id': sample_id,
            'success': False,
            'plots': [],
            'error': None,
            'event_count': int(row.get('total_events', 0) or 0),
            'qc_passed': bool(row.get('qc_passed', True))
        }
        
        # Get FCS file path
        fcs_file_path = str(row.get('file_path', ''))
        
        if not fcs_file_path or not Path(fcs_file_path).exists():
            print(f"   ⚠️  FCS file not found for {sample_id}")
            result['error'] = 'FCS file not found'
            self.stats['failed'] += 1
            self.stats['failures'].append({
                'sample_id': sample_id,
                'reason': 'FCS file not found'
            })
            return result
        
        # Load event data from FCS file
        data = self.get_sample_data(sample_id, fcs_file_path)
        if data is None:
            result['error'] = 'Failed to load event data'
            self.stats['failed'] += 1
            return result
        
        print(f"   📊 Loaded {len(data)} events")
        
        # Detect best axes using auto-selector
        try:
            channels = [col for col in data.columns if col not in ['Time', 'sample_id']]
            
            # Use first suitable channel pair, or default to first two
            if 'VFSC-A' in channels and 'VSSC1-A' in channels:
                x_channel, y_channel = 'VFSC-A', 'VSSC1-A'
            elif 'FSC-A' in channels and 'SSC-A' in channels:
                x_channel, y_channel = 'FSC-A', 'SSC-A'
            else:
                x_channel, y_channel = channels[0], channels[1] if len(channels) > 1 else channels[0]
            
            print(f"   📈 Using axes: {x_channel} vs {y_channel}")
        except Exception as e:
            print(f"   ⚠️  Axis selection failed: {e}, using defaults")
            x_channel = str(data.columns[0])
            y_channel = str(data.columns[1])
        
        # Generate plots
        plots_generated = []
        
        if PLOT_TYPES['scatter_density']:
            print(f"   🎨 Generating density plot...")
            plot_path = self.generate_scatter_density(sample_id, data, x_channel, y_channel)
            if plot_path:
                thumb_path = self.create_thumbnail(plot_path)
                plots_generated.append({
                    'type': 'scatter_density',
                    'path': str(plot_path.relative_to(project_root)),
                    'thumbnail': str(thumb_path.relative_to(project_root))
                })
                self.stats['plots_generated'] += 1
        
        if PLOT_TYPES['scatter_hexbin']:
            print(f"   🎨 Generating hexbin plot...")
            plot_path = self.generate_scatter_hexbin(sample_id, data, x_channel, y_channel)
            if plot_path:
                thumb_path = self.create_thumbnail(plot_path)
                plots_generated.append({
                    'type': 'scatter_hexbin',
                    'path': str(plot_path.relative_to(project_root)),
                    'thumbnail': str(thumb_path.relative_to(project_root))
                })
                self.stats['plots_generated'] += 1
        
        if PLOT_TYPES['histogram_grid']:
            print(f"   🎨 Generating histogram grid...")
            plot_path = self.generate_histogram_grid(sample_id, data)
            if plot_path:
                thumb_path = self.create_thumbnail(plot_path)
                plots_generated.append({
                    'type': 'histogram_grid',
                    'path': str(plot_path.relative_to(project_root)),
                    'thumbnail': str(thumb_path.relative_to(project_root))
                })
                self.stats['plots_generated'] += 1
        
        result['plots'] = plots_generated
        result['success'] = len(plots_generated) > 0
        
        if result['success']:
            print(f"   ✅ Generated {len(plots_generated)} plots")
            self.stats['processed'] += 1
        else:
            print(f"   ❌ No plots generated")
            self.stats['failed'] += 1
        
        return result
    
    def generate_html_report(self, results: List[Dict], output_file: Path):
        """Generate HTML summary report with thumbnails."""
        print("\n📄 Generating HTML report...")
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FCS Batch Visualization Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .stat-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .stat-box h3 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: bold;
        }}
        .stat-box p {{
            margin: 10px 0 0 0;
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .sample-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
            margin-top: 20px;
        }}
        .sample-card {{
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
            background: white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .sample-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }}
        .sample-header {{
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
            color: white;
            padding: 15px;
            font-weight: bold;
            font-size: 1.1em;
        }}
        .sample-body {{
            padding: 15px;
        }}
        .plot-thumbnails {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }}
        .thumbnail {{
            position: relative;
            cursor: pointer;
            border-radius: 5px;
            overflow: hidden;
            border: 2px solid #eee;
            transition: border-color 0.2s;
        }}
        .thumbnail:hover {{
            border-color: #3498db;
        }}
        .thumbnail img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        .thumbnail-label {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 5px;
            font-size: 0.8em;
            text-align: center;
        }}
        .sample-info {{
            font-size: 0.9em;
            color: #666;
            margin: 10px 0;
        }}
        .qc-badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: bold;
            margin-left: 10px;
        }}
        .qc-pass {{
            background-color: #27ae60;
            color: white;
        }}
        .qc-fail {{
            background-color: #e74c3c;
            color: white;
        }}
        .error-section {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔬 FCS Batch Visualization Report</h1>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="stats">
            <div class="stat-box">
                <h3>{self.stats['total_samples']}</h3>
                <p>Total Samples</p>
            </div>
            <div class="stat-box">
                <h3>{self.stats['processed']}</h3>
                <p>Successfully Processed</p>
            </div>
            <div class="stat-box">
                <h3>{self.stats['failed']}</h3>
                <p>Failed</p>
            </div>
            <div class="stat-box">
                <h3>{self.stats['plots_generated']}</h3>
                <p>Plots Generated</p>
            </div>
        </div>
        
        <h2>📊 Sample Visualizations</h2>
        <div class="sample-grid">
"""
        
        # Add sample cards
        for result in results:
            if not result['success']:
                continue
            
            sample_id = result['sample_id']
            qc_class = 'qc-pass' if result['qc_passed'] else 'qc-fail'
            qc_text = 'QC PASS' if result['qc_passed'] else 'QC FAIL'
            
            html += f"""
            <div class="sample-card">
                <div class="sample-header">
                    {sample_id}
                    <span class="qc-badge {qc_class}">{qc_text}</span>
                </div>
                <div class="sample-body">
                    <div class="sample-info">
                        <strong>Events:</strong> {result['event_count']:,}<br>
                        <strong>Plots:</strong> {len(result['plots'])}
                    </div>
                    <div class="plot-thumbnails">
"""
            
            for plot in result['plots']:
                plot_type = plot['type'].replace('_', ' ').title()
                html += f"""
                        <div class="thumbnail">
                            <a href="../{plot['path']}" target="_blank">
                                <img src="../{plot['thumbnail']}" alt="{plot_type}">
                                <div class="thumbnail-label">{plot_type}</div>
                            </a>
                        </div>
"""
            
            html += """
                    </div>
                </div>
            </div>
"""
        
        html += """
        </div>
"""
        
        # Add failures section if any
        if self.stats['failures']:
            html += """
        <h2>⚠️ Failed Samples</h2>
        <div class="error-section">
            <ul>
"""
            for failure in self.stats['failures'][:20]:  # Limit to 20
                html += f"<li><strong>{failure['sample_id']}</strong>: {failure['reason']}</li>\n"
            
            if len(self.stats['failures']) > 20:
                html += f"<li><em>... and {len(self.stats['failures']) - 20} more</em></li>\n"
            
            html += """
            </ul>
        </div>
"""
        
        html += f"""
        <div class="footer">
            <p>Generated by CRMIT FCS Batch Visualization Pipeline</p>
            <p>Processing Time: {self.stats['processing_time']:.1f} seconds</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Write HTML file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(html, encoding='utf-8')
        print(f"   ✅ Report saved: {output_file}")
    
    def run(self, stats_file: Path) -> Dict:
        """
        Run batch visualization pipeline.
        
        Args:
            stats_file: Path to FCS statistics parquet file
            
        Returns:
            Dictionary with processing statistics
        """
        start_time = datetime.now()
        
        print("=" * 80)
        print("🔬 FCS BATCH VISUALIZATION PIPELINE")
        print("=" * 80)
        print(f"📅 Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📂 Output directory: {self.output_dir}")
        print(f"📊 Sample size: {self.sample_size:,} events per plot")
        print("=" * 80)
        
        # Load statistics
        df_stats = self.load_fcs_statistics(stats_file)
        self.stats['total_samples'] = len(df_stats)
        
        # Process each sample
        results = []
        for idx, row in df_stats.iterrows():
            result = self.process_sample(row)
            results.append(result)
        
        # Generate HTML report
        report_file = REPORTS_DIR / 'fcs_batch_visualization_report.html'
        self.generate_html_report(results, report_file)
        
        # Calculate timing
        end_time = datetime.now()
        self.stats['processing_time'] = (end_time - start_time).total_seconds()
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 PROCESSING SUMMARY")
        print("=" * 80)
        print(f"✅ Successfully processed: {self.stats['processed']}/{self.stats['total_samples']}")
        print(f"❌ Failed: {self.stats['failed']}/{self.stats['total_samples']}")
        print(f"🎨 Total plots generated: {self.stats['plots_generated']}")
        print(f"⏱️  Processing time: {self.stats['processing_time']:.1f} seconds")
        print(f"📄 HTML report: {report_file}")
        print("=" * 80)
        
        return self.stats


def main():
    """Main execution function."""
    
    # File paths
    stats_file = project_root / 'data' / 'parquet' / 'nanofacs' / 'statistics' / 'fcs_statistics.parquet'
    
    # Check if files exist
    if not stats_file.exists():
        print(f"❌ Statistics file not found: {stats_file}")
        print("   Please ensure FCS statistics have been generated.")
        return 1
    
    # Create visualizer and run
    visualizer = FCSBatchVisualizer(
        output_dir=OUTPUT_DIR,
        sample_size=SAMPLE_SIZE
    )
    
    stats = visualizer.run(stats_file)
    
    # Save statistics
    stats_output = REPORTS_DIR / 'fcs_batch_processing_stats.json'
    with open(stats_output, 'w') as f:
        json.dump(stats, f, indent=2, default=str)
    print(f"\n📊 Statistics saved: {stats_output}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
