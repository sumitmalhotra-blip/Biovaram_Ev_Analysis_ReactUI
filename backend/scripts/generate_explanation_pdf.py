"""
Convert the NTA and NanoFACS explanation markdown to PDF
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, HRFlowable, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER


def create_explanation_pdf():
    output_path = Path(__file__).parent.parent / "reports" / "client_presentation" / "NTA_AND_NANOFACS_GUIDE.pdf"
    
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, 
                                  textColor=colors.HexColor('#1E3A5F'), alignment=TA_CENTER, spaceAfter=10)
    h1_style = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=14, 
                               textColor=colors.HexColor('#1E3A5F'), spaceBefore=15, spaceAfter=8)
    h2_style = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=12, 
                               textColor=colors.HexColor('#2E86AB'), spaceBefore=10, spaceAfter=6)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, spaceAfter=6)
    small_style = ParagraphStyle('Small', parent=styles['Normal'], fontSize=9, textColor=colors.gray)
    
    primary_color = colors.HexColor('#1E3A5F')
    secondary_color = colors.HexColor('#2E86AB')
    
    elements = []
    
    # Title
    elements.append(Paragraph("Understanding NTA and NanoFACS Reports", title_style))
    elements.append(Paragraph("A Technical Guide for EV Analysis", small_style))
    elements.append(Spacer(1, 10*mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=primary_color))
    elements.append(Spacer(1, 10*mm))
    
    # Section 1: NTA
    elements.append(Paragraph("1. NTA (Nanoparticle Tracking Analysis)", h1_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=secondary_color))
    
    elements.append(Paragraph("<b>What is NTA?</b>", h2_style))
    elements.append(Paragraph(
        "NTA uses a ZetaView instrument that tracks individual particles moving in solution via Brownian motion. "
        "A 488nm laser illuminates the particles, and a high-speed camera records their movement. "
        "Particle size is calculated based on how fast they move - smaller particles move faster.", body_style))
    
    elements.append(Paragraph("<b>Size Statistics (X Values)</b>", h2_style))
    
    nta_stats = [
        ['Metric', 'Example', 'Interpretation'],
        ['D10', '82.5 nm', '10% of particles are smaller than this'],
        ['D50 (Median)', '127.5 nm', 'Half are smaller, half are larger'],
        ['D90', '217.5 nm', '90% of particles are smaller than this'],
        ['Span', '1.1', '(D90-D10)/D50 - polydispersity measure'],
        ['Mean', '143.8 nm', 'Average size (affected by outliers)'],
        ['Mode', '97.5 nm', 'Most frequently occurring size'],
        ['StdDev', '62 nm', 'Spread of sizes around the mean'],
    ]
    
    nta_table = Table(nta_stats, colWidths=[40*mm, 35*mm, 95*mm])
    nta_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(nta_table)
    elements.append(Spacer(1, 5*mm))
    
    elements.append(Paragraph("<b>Size Distribution Charts</b>", h2_style))
    elements.append(Paragraph(
        "<b>Left Chart (Differential):</b> Shows number of particles at each size bin. "
        "Peak indicates most abundant size. Peak width indicates heterogeneity.", body_style))
    elements.append(Paragraph(
        "<b>Right Chart (Cumulative):</b> Running total of particles up to each size. "
        "D50 is where curve reaches 50%. Steeper curve = more uniform population.", body_style))
    
    elements.append(PageBreak())
    
    # Section 2: NanoFACS
    elements.append(Paragraph("2. NanoFACS (Flow Cytometry)", h1_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=secondary_color))
    
    elements.append(Paragraph("<b>What is NanoFACS?</b>", h2_style))
    elements.append(Paragraph(
        "A specialized high-resolution flow cytometer for nanoparticle detection. "
        "Each particle passes through laser beams, generating scatter (size/complexity) "
        "and fluorescence (marker) signals. Can detect particles as small as 50nm.", body_style))
    
    elements.append(Paragraph("<b>Channel Naming Convention</b>", h2_style))
    
    channel_data = [
        ['Channel', 'Full Name', 'Measures'],
        ['VFSC-H', 'Violet Forward Scatter Height', 'Particle SIZE'],
        ['VSSC1-H', 'Violet Side Scatter 1 Height', 'Internal COMPLEXITY'],
        ['BSSC-H', 'Blue Side Scatter Height', 'Granularity'],
        ['V447-H', 'Violet 447nm detector', 'Fluorescence marker'],
        ['B531-H', 'Blue 531nm detector', 'FITC/GFP markers'],
    ]
    
    ch_table = Table(channel_data, colWidths=[30*mm, 65*mm, 75*mm])
    ch_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), secondary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(ch_table)
    elements.append(Spacer(1, 5*mm))
    
    elements.append(Paragraph("<b>Scatter Plot Interpretation</b>", h2_style))
    elements.append(Paragraph(
        "<b>FSC vs SSC Plot:</b> Forward Scatter (X-axis) indicates SIZE. Side Scatter (Y-axis) indicates COMPLEXITY. "
        "Tight cluster = homogeneous population. Multiple clusters = different subtypes.", body_style))
    
    elements.append(Paragraph("<b>Sample Types in Experiment</b>", h2_style))
    
    sample_data = [
        ['Sample', 'Purpose'],
        ['PC3 EXO1.fcs', 'Main exosome preparation from PC3 cancer cells'],
        ['Exo+CD81.fcs', 'EVs stained with anti-CD81 antibody (exosome marker)'],
        ['Exo+CD9.fcs', 'EVs stained with anti-CD9 antibody (exosome marker)'],
        ['+ISOTYPE.fcs', 'Negative control for non-specific binding'],
    ]
    
    sample_table = Table(sample_data, colWidths=[50*mm, 120*mm])
    sample_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(sample_table)
    
    elements.append(PageBreak())
    
    # Section 3: Comparison
    elements.append(Paragraph("3. NTA vs NanoFACS: Complementary Techniques", h1_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=secondary_color))
    
    comparison = [
        ['Aspect', 'NTA (ZetaView)', 'NanoFACS'],
        ['Principle', 'Brownian motion tracking', 'Light scattering + fluorescence'],
        ['Size Range', '10-1000nm', '50-1000nm'],
        ['Throughput', '~1,000 particles', '~1,000,000 particles'],
        ['Markers', 'No (size only)', 'Yes (antibody staining)'],
        ['Concentration', 'Absolute (particles/mL)', 'Relative (events)'],
        ['Best For', 'Size distribution, concentration', 'Phenotyping, marker expression'],
    ]
    
    comp_table = Table(comparison, colWidths=[40*mm, 65*mm, 65*mm])
    comp_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(comp_table)
    elements.append(Spacer(1, 10*mm))
    
    # Section 4: Key Results
    elements.append(Paragraph("4. Key Results for PC3 Exosome Samples", h1_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=secondary_color))
    
    results = [
        ['Metric', 'Result', 'Status'],
        ['NTA D50', '127.5 nm', '✓ Typical exosome size'],
        ['Span', '1.1', '✓ Uniform population'],
        ['Traced particles', '630', '✓ Sufficient for statistics'],
        ['FCS events', '914,326', '✓ High-quality acquisition'],
        ['CD81/CD9 markers', 'Positive', '✓ Confirmed exosome identity'],
    ]
    
    results_table = Table(results, colWidths=[50*mm, 50*mm, 70*mm])
    results_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27AE60')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(results_table)
    elements.append(Spacer(1, 10*mm))
    
    elements.append(Paragraph("<b>Conclusions:</b>", h2_style))
    elements.append(Paragraph("• <b>Size:</b> Particles are in expected exosome range (30-150nm)", body_style))
    elements.append(Paragraph("• <b>Purity:</b> Low span indicates minimal contamination", body_style))
    elements.append(Paragraph("• <b>Identity:</b> CD81/CD9 markers confirm exosome nature", body_style))
    elements.append(Paragraph("• <b>Yield:</b> High particle counts from PC3 cell culture", body_style))
    
    # Footer
    elements.append(Spacer(1, 20*mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=primary_color))
    elements.append(Paragraph(
        f"<i>Document generated by EV Analysis Platform | {datetime.now().strftime('%B %d, %Y')}</i>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.gray, alignment=TA_CENTER)
    ))
    
    doc.build(elements)
    print(f"✅ Guide PDF created: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    create_explanation_pdf()
