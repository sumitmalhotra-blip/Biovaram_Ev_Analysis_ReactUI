"""
FCS/NanoFACS PDF Report Generator
=================================
Creates professional PDF reports for Flow Cytometry/NanoFACS data.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    Image, PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from io import BytesIO
from typing import Optional

# Import our parsers
try:
    from src.parsers.fcs_parser import FCSParser
    HAS_FCS_PARSER = True
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from src.parsers.fcs_parser import FCSParser
    HAS_FCS_PARSER = False


class NanoFACSStyleReport:
    """Generate PDF reports for NanoFACS flow cytometry data."""
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else Path("reports/fcs_pdf")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Company/Lab info
        self.company_name = "EV Analysis Platform"
        self.company_address = "Extracellular Vesicle Research Laboratory"
        self.operator = "System"
        
        # Colors
        self.primary_color = colors.HexColor('#1E3A5F')  # Dark blue
        self.secondary_color = colors.HexColor('#2E86AB')  # Medium blue
        self.fsc_color = '#2E86AB'  # Blue for FSC
        self.ssc_color = '#A23B72'  # Magenta for SSC
        
    def create_scatter_plot(self, fcs_data: dict, sample_name: str) -> BytesIO:
        """Create FSC vs SSC scatter plot."""
        fig, axes = plt.subplots(1, 3, figsize=(12, 4))
        
        # Get data - try multiple channel naming conventions
        events = fcs_data.get('events', {})
        
        # Initialize labels with defaults
        fsc_label = 'FSC-H'
        ssc_label = 'SSC-H'
        
        # Try different FSC channel names
        fsc = None
        for fsc_name in ['FSC-H', 'FSC-A', 'VFSC-H', 'VFSC-A']:
            if fsc_name in events and len(events[fsc_name]) > 0:
                fsc = np.array(events[fsc_name])
                fsc_label = fsc_name
                break
        
        # Try different SSC channel names
        ssc = None
        for ssc_name in ['SSC-H', 'SSC-A', 'VSSC1-H', 'VSSC1-A', 'BSSC-H']:
            if ssc_name in events and len(events[ssc_name]) > 0:
                ssc = np.array(events[ssc_name])
                ssc_label = ssc_name
                break
        
        # Fallback to empty arrays
        if fsc is None:
            fsc = np.array([])
        if ssc is None:
            ssc = np.array([])
        
        # Subsample if too many events
        max_points = 10000
        if len(fsc) > max_points and len(ssc) > max_points:
            idx = np.random.choice(min(len(fsc), len(ssc)), max_points, replace=False)
            fsc_plot = fsc[idx]
            ssc_plot = ssc[idx]
        else:
            fsc_plot = fsc[:max_points] if len(fsc) > max_points else fsc
            ssc_plot = ssc[:max_points] if len(ssc) > max_points else ssc
        
        # Plot 1: FSC vs SSC scatter
        if len(fsc_plot) > 0 and len(ssc_plot) > 0:
            # Use density coloring for better visualization
            min_len = min(len(fsc_plot), len(ssc_plot))
            axes[0].scatter(fsc_plot[:min_len], ssc_plot[:min_len], s=1, alpha=0.3, c='#2E86AB')
            axes[0].set_xlabel(fsc_label, fontsize=9)
            axes[0].set_ylabel(ssc_label, fontsize=9)
            axes[0].set_title('Forward vs Side Scatter', fontsize=10, fontweight='bold')
            
            # Set reasonable axis limits using percentiles
            fsc_valid = fsc_plot[fsc_plot > 0]
            ssc_valid = ssc_plot[ssc_plot > 0]
            if len(fsc_valid) > 0:
                axes[0].set_xlim(0, np.percentile(fsc_valid, 99) * 1.1)
            if len(ssc_valid) > 0:
                axes[0].set_ylim(0, np.percentile(ssc_valid, 99) * 1.1)
        else:
            axes[0].text(0.5, 0.5, 'No Data', ha='center', va='center', transform=axes[0].transAxes)
            axes[0].set_title('Forward vs Side Scatter', fontsize=10, fontweight='bold')
        
        # Plot 2: FSC histogram
        if len(fsc) > 0:
            fsc_positive = fsc[fsc > 0]
            if len(fsc_positive) > 0:
                axes[1].hist(fsc_positive, bins=100, color=self.fsc_color, alpha=0.7, edgecolor='white', linewidth=0.5)
                axes[1].set_xlabel(fsc_label, fontsize=9)
                axes[1].set_ylabel('Count', fontsize=9)
                axes[1].set_title(f'{fsc_label} Distribution', fontsize=10, fontweight='bold')
                axes[1].set_xlim(0, np.percentile(fsc_positive, 99) * 1.1)
        else:
            axes[1].text(0.5, 0.5, 'No Data', ha='center', va='center', transform=axes[1].transAxes)
            axes[1].set_title('FSC Distribution', fontsize=10, fontweight='bold')
        
        # Plot 3: SSC histogram
        if len(ssc) > 0:
            ssc_positive = ssc[ssc > 0]
            if len(ssc_positive) > 0:
                axes[2].hist(ssc_positive, bins=100, color=self.ssc_color, alpha=0.7, edgecolor='white', linewidth=0.5)
                axes[2].set_xlabel(ssc_label, fontsize=9)
                axes[2].set_ylabel('Count', fontsize=9)
                axes[2].set_title(f'{ssc_label} Distribution', fontsize=10, fontweight='bold')
                axes[2].set_xlim(0, np.percentile(ssc_positive, 99) * 1.1)
        else:
            axes[2].text(0.5, 0.5, 'No Data', ha='center', va='center', transform=axes[2].transAxes)
            axes[2].set_title('SSC Distribution', fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        
        # Save to BytesIO
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        img_buffer.seek(0)
        
        return img_buffer
    
    def create_fluorescence_plot(self, fcs_data: dict) -> BytesIO:
        """Create fluorescence channel plots if available."""
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        
        events = fcs_data.get('events', {})
        channels = fcs_data.get('channels', [])
        
        # Find fluorescence channels
        fl_channels = [ch for ch in channels if 'FL' in ch or 'FITC' in ch or 'PE' in ch or 'APC' in ch]
        
        if len(fl_channels) >= 2:
            fl1 = np.array(events.get(fl_channels[0], []))
            fl2 = np.array(events.get(fl_channels[1], []))
            
            # Subsample
            max_points = 10000
            if len(fl1) > max_points:
                idx = np.random.choice(len(fl1), max_points, replace=False)
                fl1_plot = fl1[idx]
                fl2_plot = fl2[idx]
            else:
                fl1_plot = fl1
                fl2_plot = fl2
            
            # Scatter plot
            if len(fl1_plot) > 0 and len(fl2_plot) > 0:
                axes[0].scatter(fl1_plot, fl2_plot, s=1, alpha=0.3, c='#27AE60')
                axes[0].set_xlabel(fl_channels[0], fontsize=9)
                axes[0].set_ylabel(fl_channels[1], fontsize=9)
                axes[0].set_title(f'{fl_channels[0]} vs {fl_channels[1]}', fontsize=10, fontweight='bold')
        
        elif len(fl_channels) >= 1:
            fl1 = np.array(events.get(fl_channels[0], []))
            if len(fl1) > 0:
                axes[0].hist(fl1[fl1 > 0], bins=100, color='#27AE60', alpha=0.7)
                axes[0].set_xlabel(fl_channels[0], fontsize=9)
                axes[0].set_ylabel('Count', fontsize=9)
                axes[0].set_title(f'{fl_channels[0]} Distribution', fontsize=10, fontweight='bold')
        
        # Event quality
        total_events = fcs_data.get('total_events', 0)
        quality_scores = []
        
        # Simple quality metric based on FSC/SSC ratio
        fsc = np.array(events.get('FSC-H', events.get('FSC-A', [])))
        ssc = np.array(events.get('SSC-H', events.get('SSC-A', [])))
        
        if len(fsc) > 0 and len(ssc) > 0:
            # Calculate coefficient of variation
            fsc_cv = np.std(fsc) / np.mean(fsc) * 100 if np.mean(fsc) > 0 else 0
            ssc_cv = np.std(ssc) / np.mean(ssc) * 100 if np.mean(ssc) > 0 else 0
            
            categories = ['Events', 'FSC CV%', 'SSC CV%']
            values = [total_events / 1000, fsc_cv, ssc_cv]  # Events in thousands
            
            bars = axes[1].barh(categories, values, color=['#2E86AB', '#27AE60', '#A23B72'])
            axes[1].set_xlabel('Value', fontsize=9)
            axes[1].set_title('Data Quality Metrics', fontsize=10, fontweight='bold')
            
            # Add value labels
            for bar, val in zip(bars, values):
                axes[1].text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                           f'{val:.1f}', va='center', fontsize=8)
        
        plt.tight_layout()
        
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        img_buffer.seek(0)
        
        return img_buffer
    
    def generate_report(self, fcs_data: dict, sample_name: Optional[str] = None) -> str:
        """Generate a professional PDF report for FCS data."""
        
        sample_name = sample_name or fcs_data.get('filename', 'Unknown Sample')
        output_path = self.output_dir / f"{sample_name}_report.pdf"
        
        # Create PDF document
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=15*mm
        )
        
        # Styles
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=14,
            textColor=self.primary_color,
            spaceAfter=6,
            alignment=TA_CENTER
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=11,
            textColor=self.primary_color,
            spaceBefore=10,
            spaceAfter=4
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=9,
            spaceAfter=2
        )
        
        small_style = ParagraphStyle(
            'CustomSmall',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.gray
        )
        
        # Build document elements
        elements = []
        
        # === HEADER ===
        header_data = [
            [Paragraph(f"<b>{self.company_name}</b>", title_style)],
            [Paragraph("NanoFACS Flow Cytometry Report", normal_style)],
            [Paragraph("Single Particle Analysis | Light Scattering", small_style)]
        ]
        
        header_table = Table(header_data, colWidths=[180*mm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 5*mm))
        
        elements.append(Paragraph(
            f"<b>Report Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            small_style
        ))
        elements.append(HRFlowable(width="100%", thickness=1, color=self.primary_color))
        elements.append(Spacer(1, 5*mm))
        
        # === SAMPLE INFO ===
        elements.append(Paragraph("Sample Information", header_style))
        
        metadata = fcs_data.get('metadata', {})
        total_events = fcs_data.get('total_events', 0)
        channels = fcs_data.get('channels', [])
        
        sample_params = [
            ['Sample Name:', sample_name, 'Total Events:', f"{total_events:,}"],
            ['Date:', metadata.get('$DATE', datetime.now().strftime('%Y-%m-%d')), 
             'Channels:', str(len(channels))],
            ['Cytometer:', metadata.get('$CYT', 'NanoFACS'), 
             'Mode:', metadata.get('$MODE', 'L')],
            ['Source:', metadata.get('$SRC', 'Unknown'), 
             'Operator:', metadata.get('$OP', self.operator)],
        ]
        
        sample_table = Table(sample_params, colWidths=[35*mm, 55*mm, 35*mm, 55*mm])
        sample_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), self.primary_color),
            ('TEXTCOLOR', (2, 0), (2, -1), self.primary_color),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(sample_table)
        elements.append(Spacer(1, 5*mm))
        
        # === CHANNELS TABLE ===
        elements.append(Paragraph("Available Channels", header_style))
        
        # Split channels into rows of 4
        channel_rows = []
        for i in range(0, len(channels), 4):
            row = channels[i:i+4]
            while len(row) < 4:
                row.append('')
            channel_rows.append(row)
        
        if channel_rows:
            ch_table = Table(channel_rows, colWidths=[45*mm, 45*mm, 45*mm, 45*mm])
            ch_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8F4FD')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(ch_table)
        elements.append(Spacer(1, 8*mm))
        
        # === SCATTER PLOTS ===
        elements.append(Paragraph("Scatter Analysis", header_style))
        
        scatter_buffer = self.create_scatter_plot(fcs_data, sample_name)
        scatter_img = Image(scatter_buffer, width=170*mm, height=55*mm)
        elements.append(scatter_img)
        elements.append(Spacer(1, 5*mm))
        
        # === STATISTICS TABLE ===
        elements.append(Paragraph("Channel Statistics", header_style))
        
        events = fcs_data.get('events', {})
        stats_rows = [['Channel', 'Mean', 'Median', 'Std Dev', 'Min', 'Max']]
        
        # Calculate stats for scatter channels - try multiple naming conventions
        scatter_channels = [
            'VFSC-H', 'VFSC-A', 'VSSC1-H', 'VSSC1-A', 'BSSC-H', 'BSSC-A',
            'FSC-H', 'FSC-A', 'SSC-H', 'SSC-A'
        ]
        
        added_channels = set()
        for ch in scatter_channels:
            if ch in events and ch not in added_channels:
                data = np.array(events[ch])
                data = data[data > 0]  # Filter zeros
                if len(data) > 0:
                    stats_rows.append([
                        ch,
                        f"{np.mean(data):.1f}",
                        f"{np.median(data):.1f}",
                        f"{np.std(data):.1f}",
                        f"{np.min(data):.1f}",
                        f"{np.max(data):.1f}"
                    ])
                    added_channels.add(ch)
                    # Limit to 6 channels for table space
                    if len(added_channels) >= 6:
                        break
        
        if len(stats_rows) > 1:
            stats_table = Table(stats_rows, colWidths=[30*mm, 25*mm, 25*mm, 25*mm, 25*mm, 25*mm])
            stats_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(stats_table)
        elements.append(Spacer(1, 10*mm))
        
        # === FOOTER ===
        elements.append(HRFlowable(width="100%", thickness=1, color=self.primary_color))
        elements.append(Spacer(1, 3*mm))
        
        footer_text = f"""
        <b>Analysis Software:</b> EV Analysis Platform v1.0 | 
        <b>File:</b> {fcs_data.get('filepath', 'N/A')}
        """
        elements.append(Paragraph(footer_text, small_style))
        
        # Build PDF
        doc.build(elements)
        
        print(f"✅ Report generated: {output_path}")
        return str(output_path)


def generate_reports_for_pc3_fcs():
    """Generate PDF reports for PC3 FCS samples."""
    
    # Load validation results
    validation_dir = Path(__file__).parent.parent / "data" / "validation"
    results_file = validation_dir / "fcs_pc3_parsed_results.json"
    
    if not results_file.exists():
        print("❌ FCS validation results not found. Run validate_fcs_pc3.py first.")
        return
    
    with open(results_file, 'r') as f:
        validation_results = json.load(f)
    
    # Initialize report generator
    report_gen = NanoFACSStyleReport(output_dir=str(Path(__file__).parent.parent / "reports" / "fcs_pdf"))
    
    # FCS data directory
    fcs_dir = Path(__file__).parent.parent / "nanoFACS" / "Exp_20251217_PC3"
    
    # Generate reports for a subset (first 5 samples to keep it manageable)
    generated_reports = []
    
    for result in validation_results[:5]:  # First 5 samples
        # Get filename from 'file' key
        filename = result.get('file', result.get('filename', 'Unknown'))
        sample_name = filename.replace('.fcs', '')
        
        # Find the FCS file
        fcs_path = fcs_dir / filename
        
        if fcs_path.exists():
            if not HAS_FCS_PARSER or FCSParser is None:
                print(f"  ⚠️ FCSParser not available - skipping {filename}")
                continue
            parser = FCSParser(fcs_path)
            if parser.validate():
                fcs_data = parser.parse()
                
                if fcs_data is not None:
                    # Build data dict for report
                    report_data = {
                        'success': True,
                        'filename': filename,
                        'filepath': str(fcs_path),
                        'total_events': len(fcs_data) if hasattr(fcs_data, '__len__') else result.get('total_events', 0),
                        'channels': result.get('channels', []),
                        'metadata': {},
                        'events': {}
                    }
                    
                    # Extract events for plotting
                    if hasattr(fcs_data, 'columns'):
                        for col in fcs_data.columns:
                            report_data['events'][col] = fcs_data[col].values
                    
                    try:
                        report_path = report_gen.generate_report(report_data, sample_name)
                        generated_reports.append(report_path)
                    except Exception as e:
                        print(f"❌ Failed to generate report for {sample_name}: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"⚠️ Skipping {sample_name}: Parse returned None")
            else:
                print(f"⚠️ Skipping {sample_name}: Validation failed")
        else:
            print(f"⚠️ Skipping {sample_name}: File not found at {fcs_path}")
    
    print(f"\n{'='*60}")
    print(f"Generated {len(generated_reports)} FCS PDF reports")
    print(f"{'='*60}")
    
    return generated_reports


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate NanoFACS-style FCS PDF reports')
    parser.add_argument('--file', type=str, help='Path to single FCS file to process')
    parser.add_argument('--batch', action='store_true', help='Generate reports for PC3 validation samples')
    parser.add_argument('--output', type=str, help='Output directory for reports')
    
    args = parser.parse_args()
    
    if args.file:
        if not HAS_FCS_PARSER:
            print("❌ FCSParser not available - install from src/parsers")
            sys.exit(1)
        fcs_parser = FCSParser(Path(args.file))
        fcs_data = fcs_parser.parse()
        
        if fcs_data is not None and len(fcs_data) > 0:  # type: ignore[arg-type]
            report_gen = NanoFACSStyleReport(output_dir=args.output)
            sample_name = Path(args.file).stem
            # Convert DataFrame to dict for report
            fcs_dict = fcs_data.to_dict() if hasattr(fcs_data, 'to_dict') else {}  # type: ignore
            output_path = report_gen.generate_report(fcs_dict, sample_name)
            print(f"Report saved to: {output_path}")
        else:
            print(f"❌ Failed to parse FCS file: empty result")
    elif args.batch:
        generate_reports_for_pc3_fcs()
    else:
        # Default: generate for PC3 samples
        generate_reports_for_pc3_fcs()
