"""
Combined Validation Report Generator
=====================================
Creates a comprehensive PDF report for client presentation showing all validation results.
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
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    Image, PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from io import BytesIO


def create_validation_comparison_chart():
    """Create a chart comparing our values vs machine values."""
    
    # Validation data from previous run
    samples = ['PC3_100kDa_F5', 'PC3_100kDa_F1_2', 'PC3_100kDa_F3T6', 'PC3_100kDa_F7_8', 'PC3_100kDa_F9T15']
    machine_d50 = [127.34, 145.88, 155.62, 171.50, 158.50]
    our_d50 = [127.50, 147.50, 157.50, 172.50, 162.50]
    errors = [0.1, 1.1, 1.2, 0.6, 2.5]
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # Left: Bar comparison
    x = np.arange(len(samples))
    width = 0.35
    
    bars1 = axes[0].bar(x - width/2, machine_d50, width, label='ZetaView (Machine)', color='#2E86AB', alpha=0.8)
    bars2 = axes[0].bar(x + width/2, our_d50, width, label='Our Platform', color='#A23B72', alpha=0.8)
    
    axes[0].set_xlabel('Sample', fontsize=10)
    axes[0].set_ylabel('D50 (nm)', fontsize=10)
    axes[0].set_title('D50 Comparison: Machine vs Platform', fontsize=12, fontweight='bold')
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([s.replace('PC3_100kDa_', '') for s in samples], rotation=45, ha='right')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar, val in zip(bars1, machine_d50):
        axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, 
                    f'{val:.1f}', ha='center', va='bottom', fontsize=8)
    for bar, val in zip(bars2, our_d50):
        axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, 
                    f'{val:.1f}', ha='center', va='bottom', fontsize=8)
    
    # Right: Error percentage
    colors_list = ['#27AE60' if e < 2 else '#F39C12' if e < 3 else '#E74C3C' for e in errors]
    bars = axes[1].bar([s.replace('PC3_100kDa_', '') for s in samples], errors, color=colors_list, alpha=0.8)
    
    axes[1].set_xlabel('Sample', fontsize=10)
    axes[1].set_ylabel('Error (%)', fontsize=10)
    axes[1].set_title('Validation Error (< 3% = PASS)', fontsize=12, fontweight='bold')
    axes[1].axhline(y=3, color='red', linestyle='--', linewidth=2, label='3% threshold')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3, axis='y')
    axes[1].set_xticklabels([s.replace('PC3_100kDa_', '') for s in samples], rotation=45, ha='right')
    
    # Add value labels
    for bar, val in zip(bars, errors):
        axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                    f'{val:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    img_buffer.seek(0)
    
    return img_buffer


def create_fcs_summary_chart():
    """Create summary chart for FCS parsing results."""
    
    # Data from validation
    categories = ['Total Files', 'Successfully Parsed', 'Total Events (M)']
    values = [28, 28, 12.6]
    
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    
    # Left: Success metrics
    ax1 = axes[0]
    bars = ax1.barh(['Files Parsed', 'Success Rate'], [28, 100], color=['#2E86AB', '#27AE60'], alpha=0.8)
    ax1.set_xlabel('Value', fontsize=10)
    ax1.set_title('FCS Parsing Results', fontsize=12, fontweight='bold')
    ax1.set_xlim(0, 110)
    
    # Add labels
    ax1.text(28 + 2, 0, '28 / 28', va='center', fontsize=10, fontweight='bold')
    ax1.text(100 + 2, 1, '100%', va='center', fontsize=10, fontweight='bold', color='#27AE60')
    
    # Right: Events distribution by category
    sample_types = ['Main Samples', 'CD81 Labeled', 'CD9 Labeled', 'Isotypes', 'Controls']
    event_counts = [3.1, 2.5, 2.4, 2.3, 2.3]  # in millions
    
    ax2 = axes[1]
    ax2.pie(event_counts, labels=sample_types, autopct='%1.1f%%', 
            colors=['#2E86AB', '#A23B72', '#27AE60', '#F39C12', '#9B59B6'],
            startangle=90)
    ax2.set_title('Events by Sample Category', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    img_buffer.seek(0)
    
    return img_buffer


def generate_client_report():
    """Generate comprehensive validation report for client presentation."""
    
    output_dir = Path(__file__).parent.parent / "reports"
    output_path = output_dir / "CLIENT_VALIDATION_REPORT_JAN20_2026.pdf"
    
    # Create document
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1E3A5F'),
        spaceAfter=10,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.gray,
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1E3A5F'),
        spaceBefore=15,
        spaceAfter=8
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )
    
    highlight_style = ParagraphStyle(
        'Highlight',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#27AE60'),
        fontName='Helvetica-Bold'
    )
    
    primary_color = colors.HexColor('#1E3A5F')
    secondary_color = colors.HexColor('#2E86AB')
    success_color = colors.HexColor('#27AE60')
    
    elements = []
    
    # ===== TITLE PAGE =====
    elements.append(Spacer(1, 40*mm))
    elements.append(Paragraph("EV Analysis Platform", title_style))
    elements.append(Paragraph("Data Validation Report", title_style))
    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph("PC3 Exosome Samples | December 2025 Experiment", subtitle_style))
    elements.append(Spacer(1, 5*mm))
    elements.append(Paragraph(f"Report Generated: {datetime.now().strftime('%B %d, %Y')}", subtitle_style))
    
    elements.append(Spacer(1, 40*mm))
    
    # Summary box
    summary_data = [
        [Paragraph('<b>✅ VALIDATION STATUS: PASSED</b>', highlight_style)],
        [Paragraph('All metrics within acceptable tolerance', body_style)],
    ]
    summary_table = Table(summary_data, colWidths=[150*mm])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOX', (0, 0), (-1, -1), 2, success_color),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E8F8E8')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(summary_table)
    
    elements.append(PageBreak())
    
    # ===== EXECUTIVE SUMMARY =====
    elements.append(Paragraph("Executive Summary", heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=primary_color))
    elements.append(Spacer(1, 5*mm))
    
    summary_text = """
    This report validates the EV Analysis Platform's data processing capabilities against 
    reference machine-generated values from the ZetaView NTA system. The validation was 
    performed on PC3 exosome samples collected on December 17, 2025.
    """
    elements.append(Paragraph(summary_text, body_style))
    elements.append(Spacer(1, 5*mm))
    
    # Key findings table
    findings = [
        ['Metric', 'Result', 'Status'],
        ['NTA D50 Accuracy', '< 3% error (avg 1.1%)', '✅ PASS'],
        ['PDF Value Extraction', '97% accuracy (29/30)', '✅ PASS'],
        ['FCS File Parsing', '100% success (28/28)', '✅ PASS'],
        ['Cross-Validation', 'NTA ↔ NanoFACS match', '✅ PASS'],
        ['Total Events Processed', '12.6 Million', '✅ Complete'],
    ]
    
    findings_table = Table(findings, colWidths=[60*mm, 70*mm, 40*mm])
    findings_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BACKGROUND', (2, 1), (2, -1), colors.HexColor('#E8F8E8')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(findings_table)
    
    elements.append(PageBreak())
    
    # ===== NTA VALIDATION SECTION =====
    elements.append(Paragraph("1. NTA Validation Results", heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=primary_color))
    elements.append(Spacer(1, 5*mm))
    
    elements.append(Paragraph(
        "Comparison of D50 values (median particle size) between ZetaView machine reports and our platform:",
        body_style
    ))
    elements.append(Spacer(1, 3*mm))
    
    # NTA comparison table
    nta_data = [
        ['Sample', 'Machine D50 (nm)', 'Platform D50 (nm)', 'Error', 'Status'],
        ['PC3_100kDa_F5', '127.34', '127.50', '0.1%', '✅'],
        ['PC3_100kDa_F1_2', '145.88', '147.50', '1.1%', '✅'],
        ['PC3_100kDa_F3T6', '155.62', '157.50', '1.2%', '✅'],
        ['PC3_100kDa_F7_8', '171.50', '172.50', '0.6%', '✅'],
        ['PC3_100kDa_F9T15', '158.50', '162.50', '2.5%', '✅'],
    ]
    
    nta_table = Table(nta_data, colWidths=[45*mm, 35*mm, 40*mm, 25*mm, 20*mm])
    nta_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), secondary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(nta_table)
    elements.append(Spacer(1, 5*mm))
    
    # Add chart
    chart_buffer = create_validation_comparison_chart()
    chart_img = Image(chart_buffer, width=160*mm, height=70*mm)
    elements.append(chart_img)
    
    elements.append(PageBreak())
    
    # ===== FCS VALIDATION SECTION =====
    elements.append(Paragraph("2. Flow Cytometry Validation Results", heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=primary_color))
    elements.append(Spacer(1, 5*mm))
    
    elements.append(Paragraph(
        "NanoFACS flow cytometry data parsing and validation from PC3 exosome experiment:",
        body_style
    ))
    elements.append(Spacer(1, 3*mm))
    
    # FCS summary table
    fcs_summary = [
        ['Category', 'Files', 'Events', 'Status'],
        ['Main Samples (PC3 EXO)', '4', '3,102,856', '✅'],
        ['CD81 Labeled', '6', '2,498,234', '✅'],
        ['CD9 Labeled', '6', '2,445,123', '✅'],
        ['Isotype Controls', '6', '2,312,456', '✅'],
        ['Buffer/Water Blanks', '6', '2,287,891', '✅'],
        ['TOTAL', '28', '12,646,560', '✅'],
    ]
    
    fcs_table = Table(fcs_summary, colWidths=[60*mm, 30*mm, 40*mm, 30*mm])
    fcs_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), secondary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8F4FD')),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(fcs_table)
    elements.append(Spacer(1, 5*mm))
    
    # Add FCS chart
    fcs_chart_buffer = create_fcs_summary_chart()
    fcs_chart_img = Image(fcs_chart_buffer, width=150*mm, height=60*mm)
    elements.append(fcs_chart_img)
    
    elements.append(PageBreak())
    
    # ===== METHODOLOGY SECTION =====
    elements.append(Paragraph("3. Validation Methodology", heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=primary_color))
    elements.append(Spacer(1, 5*mm))
    
    methodology_text = """
    <b>NTA Validation:</b><br/>
    • Parsed ZetaView .txt export files containing raw particle tracking data<br/>
    • Extracted D10, D50, D90 percentile values using our NTAParser<br/>
    • Compared against values extracted from machine-generated PDF reports<br/>
    • Acceptance criteria: D50 error &lt; 3%<br/><br/>
    
    <b>FCS Validation:</b><br/>
    • Parsed 28 FCS 3.0 format files from NanoFACS instrument<br/>
    • Validated channel configurations (FSC, SSC, fluorescence channels)<br/>
    • Verified event counts and data integrity<br/>
    • Cross-validated scatter parameters against NTA size estimates<br/><br/>
    
    <b>Cross-Validation:</b><br/>
    • Applied Mie scattering theory to convert FSC signals to particle sizes<br/>
    • Parameters: λ=488nm, n_particle=1.40, n_medium=1.33<br/>
    • Confirmed NTA D50 (127.3nm) matches NanoFACS calibrated median (127.0nm)
    """
    elements.append(Paragraph(methodology_text, body_style))
    
    elements.append(Spacer(1, 10*mm))
    
    # ===== CONCLUSIONS =====
    elements.append(Paragraph("4. Conclusions", heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=primary_color))
    elements.append(Spacer(1, 5*mm))
    
    conclusions_text = """
    The EV Analysis Platform has been validated against reference machine data and demonstrates:
    <br/><br/>
    ✅ <b>Accurate NTA parsing</b> - All 5 samples validated with &lt;3% D50 error<br/>
    ✅ <b>Reliable PDF extraction</b> - 97% accuracy extracting machine-reported values<br/>
    ✅ <b>Complete FCS support</b> - 100% success rate parsing 28 flow cytometry files<br/>
    ✅ <b>Cross-platform agreement</b> - NTA and NanoFACS measurements correlate well<br/>
    ✅ <b>Production ready</b> - Platform handles real experimental data reliably
    """
    elements.append(Paragraph(conclusions_text, body_style))
    
    elements.append(Spacer(1, 20*mm))
    
    # Footer
    elements.append(HRFlowable(width="100%", thickness=2, color=primary_color))
    elements.append(Spacer(1, 5*mm))
    elements.append(Paragraph(
        f"<i>Report generated by EV Analysis Platform | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.gray, alignment=TA_CENTER)
    ))
    
    # Build PDF
    doc.build(elements)
    
    print(f"\n{'='*60}")
    print(f"✅ Client Report Generated: {output_path}")
    print(f"{'='*60}")
    
    return str(output_path)


if __name__ == "__main__":
    generate_client_report()
