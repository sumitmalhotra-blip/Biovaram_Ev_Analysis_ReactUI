"""
BioVaram EV Analysis Platform - Comprehensive User Manual Generator
Creates a detailed step-by-step PDF guide for platform usage
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, ListFlowable, ListItem, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Rect, Line
from reportlab.graphics.charts.barcharts import VerticalBarChart
from datetime import datetime
import os

# Output path
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports", "client_presentation")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def create_header_footer(canvas, doc):
    """Add header and footer to each page"""
    canvas.saveState()
    
    # Header
    canvas.setFillColor(colors.HexColor("#4F46E5"))  # Primary purple
    canvas.rect(0, A4[1] - 50, A4[0], 50, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(30, A4[1] - 35, "BioVaram EV Analysis Platform - User Manual")
    canvas.setFont("Helvetica", 10)
    canvas.drawRightString(A4[0] - 30, A4[1] - 35, f"Page {doc.page}")
    
    # Footer
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(30, 25, f"© 2026 CRMIT Research Labs | Version 1.0 | Generated: {datetime.now().strftime('%B %d, %Y')}")
    canvas.drawRightString(A4[0] - 30, 25, "Confidential - Internal Use Only")
    
    canvas.restoreState()


def create_user_manual():
    """Generate comprehensive user manual PDF"""
    
    output_path = os.path.join(OUTPUT_DIR, "BIOVARAM_USER_MANUAL.pdf")
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=70,
        bottomMargin=50
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor("#4F46E5"),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor("#1F2937"),
        spaceBefore=25,
        spaceAfter=12,
        borderWidth=0,
        borderColor=colors.HexColor("#4F46E5"),
        borderPadding=5,
        leftIndent=0
    )
    
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor("#4F46E5"),
        spaceBefore=18,
        spaceAfter=8
    )
    
    h3_style = ParagraphStyle(
        'H3',
        parent=styles['Heading3'],
        fontSize=13,
        textColor=colors.HexColor("#6366F1"),
        spaceBefore=12,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor("#374151"),
        spaceBefore=6,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        leading=16
    )
    
    step_style = ParagraphStyle(
        'Step',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor("#1F2937"),
        spaceBefore=4,
        spaceAfter=4,
        leftIndent=20,
        leading=16
    )
    
    tip_style = ParagraphStyle(
        'Tip',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor("#059669"),  # Green
        spaceBefore=8,
        spaceAfter=8,
        leftIndent=15,
        borderWidth=1,
        borderColor=colors.HexColor("#10B981"),
        borderPadding=8,
        backColor=colors.HexColor("#ECFDF5")
    )
    
    warning_style = ParagraphStyle(
        'Warning',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor("#DC2626"),  # Red
        spaceBefore=8,
        spaceAfter=8,
        leftIndent=15,
        borderWidth=1,
        borderColor=colors.HexColor("#F87171"),
        borderPadding=8,
        backColor=colors.HexColor("#FEF2F2")
    )
    
    note_style = ParagraphStyle(
        'Note',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor("#2563EB"),  # Blue
        spaceBefore=8,
        spaceAfter=8,
        leftIndent=15,
        borderWidth=1,
        borderColor=colors.HexColor("#60A5FA"),
        borderPadding=8,
        backColor=colors.HexColor("#EFF6FF")
    )
    
    story = []
    
    # ==================== COVER PAGE ====================
    story.append(Spacer(1, 100))
    story.append(Paragraph("BioVaram", title_style))
    story.append(Paragraph("EV Analysis Platform", ParagraphStyle(
        'Subtitle', parent=styles['Heading2'], fontSize=22, textColor=colors.HexColor("#6B7280"), alignment=TA_CENTER
    )))
    story.append(Spacer(1, 40))
    
    story.append(Paragraph("COMPREHENSIVE USER MANUAL", ParagraphStyle(
        'ManualTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor("#4F46E5"), alignment=TA_CENTER
    )))
    story.append(Spacer(1, 30))
    
    story.append(Paragraph("Complete Guide for Optimal Platform Usage", ParagraphStyle(
        'SubSubtitle', parent=styles['Normal'], fontSize=14, textColor=colors.HexColor("#6B7280"), alignment=TA_CENTER
    )))
    story.append(Spacer(1, 60))
    
    # Document info table
    doc_info = [
        ["Document Version:", "1.0"],
        ["Release Date:", datetime.now().strftime("%B %d, %Y")],
        ["Platform Version:", "2.5.0"],
        ["Prepared By:", "CRMIT Research Labs"],
        ["Classification:", "Internal Use"]
    ]
    
    doc_table = Table(doc_info, colWidths=[150, 200])
    doc_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#374151")),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(doc_table)
    story.append(PageBreak())
    
    # ==================== TABLE OF CONTENTS ====================
    story.append(Paragraph("Table of Contents", h1_style))
    story.append(Spacer(1, 15))
    
    toc_items = [
        ("1. Introduction & Overview", "3"),
        ("2. Getting Started", "4"),
        ("   2.1 System Requirements", "4"),
        ("   2.2 Login & Authentication", "4"),
        ("   2.3 Interface Overview", "5"),
        ("3. Dashboard Tab", "6"),
        ("   3.1 Quick Stats", "6"),
        ("   3.2 Recent Activity", "6"),
        ("   3.3 Quick Upload", "7"),
        ("   3.4 AI Chat Assistant", "7"),
        ("4. Flow Cytometry (FCS) Analysis", "8"),
        ("   4.1 File Upload", "8"),
        ("   4.2 Analysis Settings", "9"),
        ("   4.3 Interpreting Results", "10"),
        ("   4.4 Gating & Selection", "11"),
        ("   4.5 Export Options", "12"),
        ("5. NTA (Nanoparticle Tracking Analysis)", "13"),
        ("   5.1 File Upload", "13"),
        ("   5.2 Temperature Settings", "14"),
        ("   5.3 Interpreting Results", "14"),
        ("   5.4 PDF Report Upload", "15"),
        ("6. Cross-Compare Tab", "16"),
        ("   6.1 Selecting Samples", "16"),
        ("   6.2 Statistical Comparison", "17"),
        ("   6.3 Visualization Options", "17"),
        ("7. Research Chat (AI Assistant)", "18"),
        ("8. Best Practices", "19"),
        ("9. Troubleshooting", "20"),
        ("10. Appendix", "21"),
    ]
    
    toc_data = [[item[0], item[1]] for item in toc_items]
    toc_table = Table(toc_data, colWidths=[400, 50])
    toc_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#374151")),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
    ]))
    story.append(toc_table)
    story.append(PageBreak())
    
    # ==================== 1. INTRODUCTION ====================
    story.append(Paragraph("1. Introduction & Overview", h1_style))
    story.append(Paragraph(
        "The BioVaram EV Analysis Platform is a comprehensive, research-grade software solution designed for "
        "the characterization and analysis of Extracellular Vesicles (EVs). Built specifically for the CRMIT "
        "Research Labs, this platform integrates multiple analysis methodologies including Flow Cytometry (FCS), "
        "Nanoparticle Tracking Analysis (NTA), and provides powerful cross-comparison capabilities.",
        body_style
    ))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("Key Features", h3_style))
    features = [
        "<b>Flow Cytometry Analysis:</b> Process .FCS files from NanoFACS, ZE5, and other instruments",
        "<b>NTA Analysis:</b> Parse ZetaView data files with size distribution and concentration analysis",
        "<b>Cross-Compare:</b> Compare FCS and NTA results with statistical analysis",
        "<b>AI Research Assistant:</b> Get intelligent insights and guidance on your data",
        "<b>PDF Report Generation:</b> Export professional reports for publications",
        "<b>Real-time Alerts:</b> Quality control notifications and anomaly detection",
        "<b>Experimental Conditions:</b> Track temperature, pH, buffer, and other parameters"
    ]
    for feature in features:
        story.append(Paragraph(f"• {feature}", step_style))
    
    story.append(Spacer(1, 15))
    story.append(Paragraph(
        "💡 <b>TIP:</b> This platform is optimized for EV characterization following MISEV2023 guidelines. "
        "All analysis parameters are calibrated for particles in the 30-1000nm range.",
        tip_style
    ))
    story.append(PageBreak())
    
    # ==================== 2. GETTING STARTED ====================
    story.append(Paragraph("2. Getting Started", h1_style))
    
    story.append(Paragraph("2.1 System Requirements", h2_style))
    requirements = [
        ["Component", "Minimum", "Recommended"],
        ["Browser", "Chrome 90+, Firefox 88+", "Chrome 120+ (Latest)"],
        ["Screen Resolution", "1366 x 768", "1920 x 1080 or higher"],
        ["Internet Connection", "Stable connection", "High-speed broadband"],
        ["Backend Server", "localhost:8000", "Production server"],
    ]
    req_table = Table(requirements, colWidths=[120, 150, 180])
    req_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(req_table)
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("2.2 Login & Authentication", h2_style))
    story.append(Paragraph("Follow these steps to access the platform:", body_style))
    
    login_steps = [
        "<b>Step 1:</b> Navigate to the platform URL in your browser",
        "<b>Step 2:</b> Enter your registered email address (e.g., researcher@crmit.com)",
        "<b>Step 3:</b> Enter your password",
        "<b>Step 4:</b> Click 'Sign In' to access the dashboard",
        "<b>Step 5:</b> If you don't have an account, click 'Create Account' to register"
    ]
    for step in login_steps:
        story.append(Paragraph(f"→ {step}", step_style))
    
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "⚠️ <b>WARNING:</b> Keep your credentials secure. Do not share your password with others. "
        "All activities are logged for security and audit purposes.",
        warning_style
    ))
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("2.3 Interface Overview", h2_style))
    story.append(Paragraph(
        "The platform interface consists of the following main components:",
        body_style
    ))
    
    interface_parts = [
        ["Component", "Location", "Purpose"],
        ["Header Bar", "Top", "Logo, dark mode toggle, notifications, user menu"],
        ["Sidebar", "Left", "Previous analyses, settings, filters"],
        ["Tab Navigation", "Below Header", "Dashboard, Flow Cytometry, NTA, Cross-Compare, Research Chat"],
        ["Main Content", "Center", "Current tab's analysis workspace"],
        ["Alert Panel", "Header (bell icon)", "Notifications and quality alerts"],
    ]
    parts_table = Table(interface_parts, colWidths=[100, 80, 270])
    parts_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(parts_table)
    story.append(PageBreak())
    
    # ==================== 3. DASHBOARD TAB ====================
    story.append(Paragraph("3. Dashboard Tab", h1_style))
    story.append(Paragraph(
        "The Dashboard provides an at-a-glance overview of your analysis workspace, including pinned charts, "
        "quick statistics, recent activity, and an AI chat assistant.",
        body_style
    ))
    
    story.append(Paragraph("3.1 Quick Stats", h2_style))
    story.append(Paragraph(
        "Quick Stats displays real-time metrics about your analysis session:",
        body_style
    ))
    quick_stats_items = [
        "Total Samples Analyzed",
        "FCS Files Processed",
        "NTA Files Processed",
        "Active Alerts Count"
    ]
    for item in quick_stats_items:
        story.append(Paragraph(f"• {item}", step_style))
    
    story.append(Paragraph("3.2 Recent Activity", h2_style))
    story.append(Paragraph(
        "The Recent Activity panel shows your latest samples with the following actions:",
        body_style
    ))
    activity_actions = [
        "<b>View:</b> Click to open sample details in a modal",
        "<b>Open in Tab:</b> Load the sample in the appropriate analysis tab",
        "<b>Delete:</b> Remove the sample (requires confirmation)"
    ]
    for action in activity_actions:
        story.append(Paragraph(f"→ {action}", step_style))
    
    story.append(Paragraph("3.3 Quick Upload", h2_style))
    story.append(Paragraph(
        "Upload files directly from the dashboard without switching tabs:",
        body_style
    ))
    upload_steps = [
        "<b>Step 1:</b> Drag and drop a file onto the upload zone",
        "<b>Step 2:</b> Or click to browse and select a file",
        "<b>Step 3:</b> The file type (.fcs or .txt/.csv) is auto-detected",
        "<b>Step 4:</b> Analysis begins automatically after upload"
    ]
    for step in upload_steps:
        story.append(Paragraph(f"→ {step}", step_style))
    
    story.append(Paragraph("3.4 AI Chat Assistant", h2_style))
    story.append(Paragraph(
        "The Dashboard AI Chat provides intelligent assistance for quick questions:",
        body_style
    ))
    story.append(Paragraph(
        "ℹ️ <b>NOTE:</b> The Dashboard AI Chat is a compact version. For full-featured AI assistance with "
        "file upload support and detailed analysis, use the Research Chat tab.",
        note_style
    ))
    story.append(PageBreak())
    
    # ==================== 4. FLOW CYTOMETRY ====================
    story.append(Paragraph("4. Flow Cytometry (FCS) Analysis", h1_style))
    story.append(Paragraph(
        "The Flow Cytometry tab provides comprehensive analysis of .FCS files from nanoFACS, ZE5, and other "
        "flow cytometry instruments. This is the primary module for size-resolved EV characterization.",
        body_style
    ))
    
    story.append(Paragraph("4.1 File Upload", h2_style))
    story.append(Paragraph("<b>Single File Analysis:</b>", body_style))
    single_file_steps = [
        "<b>Step 1:</b> Navigate to the 'Flow Cytometry' tab",
        "<b>Step 2:</b> Select 'Single File' mode (default)",
        "<b>Step 3:</b> Drag and drop your .FCS file into the upload zone",
        "<b>Step 4:</b> Optionally fill in sample metadata:",
        "   • Treatment (e.g., 'Control', 'Drug A 10µg/mL')",
        "   • Concentration (µg)",
        "   • Preparation Method",
        "   • Operator Name",
        "<b>Step 5:</b> Click 'Upload and Analyze'",
        "<b>Step 6:</b> Wait for analysis to complete (typically 5-15 seconds)"
    ]
    for step in single_file_steps:
        story.append(Paragraph(f"→ {step}", step_style))
    
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Comparison Mode (Dual File):</b>", body_style))
    dual_file_steps = [
        "<b>Step 1:</b> Click 'Compare Files' button in the upload mode card",
        "<b>Step 2:</b> Upload the primary file (e.g., Sample A)",
        "<b>Step 3:</b> Upload the secondary file (e.g., Sample B)",
        "<b>Step 4:</b> Both files are analyzed and overlaid automatically"
    ]
    for step in dual_file_steps:
        story.append(Paragraph(f"→ {step}", step_style))
    
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "💡 <b>TIP:</b> Use comparison mode to visualize population shifts between conditions (e.g., before/after treatment, "
        "control vs. treated, different time points).",
        tip_style
    ))
    
    story.append(Paragraph("4.2 Analysis Settings (Sidebar)", h2_style))
    story.append(Paragraph(
        "The sidebar contains important analysis parameters. Expand the sidebar to access:",
        body_style
    ))
    
    settings_items = [
        ["Setting", "Description", "Default"],
        ["Wavelength (nm)", "Laser wavelength for size calculation", "488 nm"],
        ["Refractive Index", "Particle refractive index (n)", "1.40"],
        ["Medium RI", "Buffer/medium refractive index (n0)", "1.335"],
        ["Angular Range", "SSC collection angle range", "15°-135°"],
        ["Size Threshold (nm)", "Minimum particle size to consider", "30 nm"],
        ["Anomaly Detection", "Enable outlier detection", "On"],
        ["IQR Multiplier", "Statistical threshold for anomalies", "1.5"],
    ]
    settings_table = Table(settings_items, colWidths=[120, 230, 80])
    settings_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(settings_table)
    story.append(PageBreak())
    
    story.append(Paragraph("4.3 Interpreting Results", h2_style))
    story.append(Paragraph(
        "After analysis completes, results are displayed in multiple views:",
        body_style
    ))
    
    story.append(Paragraph("<b>Statistics Cards:</b>", h3_style))
    stats_explained = [
        "<b>Total Events:</b> Number of particles detected in the file",
        "<b>D10:</b> 10th percentile size - 10% of particles are smaller than this",
        "<b>D50 (Median):</b> 50th percentile - the 'typical' particle size",
        "<b>D90:</b> 90th percentile size - 90% of particles are smaller than this",
        "<b>Mean Size:</b> Arithmetic mean of all particle diameters",
        "<b>Std Dev:</b> Standard deviation - indicates size distribution spread",
        "<b>Polydispersity:</b> Measure of size heterogeneity (lower = more uniform)"
    ]
    for stat in stats_explained:
        story.append(Paragraph(f"• {stat}", step_style))
    
    story.append(Paragraph("<b>Size Distribution Chart:</b>", h3_style))
    story.append(Paragraph(
        "The histogram shows particle count vs. size (nm). Look for:",
        body_style
    ))
    chart_items = [
        "Peak position = Most common particle size",
        "Peak width = Size heterogeneity",
        "Multiple peaks = Different particle populations",
        "Tail on right = Presence of larger particles/aggregates"
    ]
    for item in chart_items:
        story.append(Paragraph(f"• {item}", step_style))
    
    story.append(Paragraph("<b>Scatter Plot:</b>", h3_style))
    story.append(Paragraph(
        "The interactive scatter plot shows individual particles. Default axes are VFSC-H (size) vs VSSC1-H (granularity). "
        "Use the axis selector to change channels.",
        body_style
    ))
    
    story.append(Paragraph("4.4 Gating & Selection", h2_style))
    story.append(Paragraph(
        "Interactive gating allows you to select specific particle populations:",
        body_style
    ))
    gating_steps = [
        "<b>Step 1:</b> Click and drag on the scatter plot to draw a rectangular gate",
        "<b>Step 2:</b> Release to apply the gate",
        "<b>Step 3:</b> The 'Gated Statistics' panel appears with statistics for selected particles only",
        "<b>Step 4:</b> Click 'Clear Gate' to reset selection"
    ]
    for step in gating_steps:
        story.append(Paragraph(f"→ {step}", step_style))
    
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "💡 <b>TIP:</b> Use gating to isolate specific populations (e.g., small EVs only, or exclude debris). "
        "Gated statistics update in real-time.",
        tip_style
    ))
    
    story.append(Paragraph("4.5 Export Options", h2_style))
    story.append(Paragraph("Multiple export formats are available:", body_style))
    export_formats = [
        "<b>CSV:</b> Raw data export for Excel or other tools",
        "<b>Excel:</b> Formatted spreadsheet with multiple sheets",
        "<b>PDF:</b> Professional report with charts and statistics",
        "<b>Parquet:</b> High-performance columnar format for data science",
        "<b>Markdown:</b> Text-based report for documentation"
    ]
    for fmt in export_formats:
        story.append(Paragraph(f"• {fmt}", step_style))
    
    story.append(Paragraph(
        "To export, click the 'Export' dropdown button in the results area and select your preferred format.",
        body_style
    ))
    story.append(PageBreak())
    
    # ==================== 5. NTA ====================
    story.append(Paragraph("5. NTA (Nanoparticle Tracking Analysis)", h1_style))
    story.append(Paragraph(
        "The NTA tab processes data from ZetaView and other NTA instruments. It provides size distribution, "
        "concentration measurements, and quality metrics.",
        body_style
    ))
    
    story.append(Paragraph("5.1 File Upload", h2_style))
    story.append(Paragraph("Supported file formats:", body_style))
    story.append(Paragraph("• <b>.txt</b> - ZetaView export files", step_style))
    story.append(Paragraph("• <b>.csv</b> - Comma-separated data files", step_style))
    story.append(Spacer(1, 10))
    
    nta_upload_steps = [
        "<b>Step 1:</b> Navigate to the 'NTA' tab",
        "<b>Step 2:</b> Drag and drop your .txt or .csv file into the upload zone",
        "<b>Step 3:</b> Optionally fill in metadata:",
        "   • Treatment description",
        "   • Temperature (°C)",
        "   • Operator name",
        "<b>Step 4:</b> Click 'Upload and Analyze'",
        "<b>Step 5:</b> Review the parsed results"
    ]
    for step in nta_upload_steps:
        story.append(Paragraph(f"→ {step}", step_style))
    
    story.append(Paragraph("5.2 Temperature Settings", h2_style))
    story.append(Paragraph(
        "Temperature affects viscosity calculations which impact size accuracy. The platform includes "
        "temperature correction:",
        body_style
    ))
    temp_notes = [
        "Default temperature: 25°C (room temperature)",
        "Adjust if sample was measured at different temperature",
        "Higher temperature = lower viscosity = smaller apparent size",
        "Temperature correction is applied automatically"
    ]
    for note in temp_notes:
        story.append(Paragraph(f"• {note}", step_style))
    
    story.append(Paragraph("5.3 Interpreting Results", h2_style))
    story.append(Paragraph("<b>Key NTA Metrics:</b>", body_style))
    nta_metrics = [
        "<b>Total Particles:</b> Number of tracked particles across all positions",
        "<b>Concentration:</b> Particles per mL (scientific notation)",
        "<b>D10/D50/D90:</b> Size percentiles (same interpretation as FCS)",
        "<b>Mean Size:</b> Average particle diameter in nm",
        "<b>Mode Size:</b> Most frequently observed size",
        "<b>Positions Analyzed:</b> Number of measurement positions"
    ]
    for metric in nta_metrics:
        story.append(Paragraph(f"• {metric}", step_style))
    
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "ℹ️ <b>NOTE:</b> NTA concentration is typically expressed as 1.23E+10 particles/mL. This represents "
        "1.23 × 10¹⁰ particles per milliliter.",
        note_style
    ))
    
    story.append(Paragraph("5.4 PDF Report Upload", h2_style))
    story.append(Paragraph(
        "You can also upload ZetaView PDF reports for parsing:",
        body_style
    ))
    pdf_steps = [
        "<b>Step 1:</b> Click 'Upload PDF Report' button",
        "<b>Step 2:</b> Select the ZetaView-generated PDF",
        "<b>Step 3:</b> The system extracts tables and charts",
        "<b>Step 4:</b> Review extracted data alongside raw file data"
    ]
    for step in pdf_steps:
        story.append(Paragraph(f"→ {step}", step_style))
    story.append(PageBreak())
    
    # ==================== 6. CROSS-COMPARE ====================
    story.append(Paragraph("6. Cross-Compare Tab", h1_style))
    story.append(Paragraph(
        "The Cross-Compare tab allows you to compare results from different analysis methods (FCS vs NTA) "
        "or different samples within the same method.",
        body_style
    ))
    
    story.append(Paragraph("6.1 Selecting Samples", h2_style))
    compare_steps = [
        "<b>Step 1:</b> Navigate to the 'Cross-Compare' tab",
        "<b>Step 2:</b> Select an FCS sample from the dropdown (or 'Current FCS Analysis' if just analyzed)",
        "<b>Step 3:</b> Select an NTA sample from the dropdown (or 'Current NTA Analysis' if just analyzed)",
        "<b>Step 4:</b> Results load automatically when both samples are selected",
        "<b>Step 5:</b> Click 'Refresh' to reload data if needed"
    ]
    for step in compare_steps:
        story.append(Paragraph(f"→ {step}", step_style))
    
    story.append(Paragraph("6.2 Statistical Comparison", h2_style))
    story.append(Paragraph(
        "The comparison table shows side-by-side metrics:",
        body_style
    ))
    comparison_metrics = [
        ["Metric", "FCS", "NTA", "Difference"],
        ["D10 (nm)", "Calculated from scatter", "From tracking", "Absolute & %"],
        ["D50 (nm)", "Median size", "Median size", "Absolute & %"],
        ["D90 (nm)", "Calculated from scatter", "From tracking", "Absolute & %"],
        ["Mean (nm)", "Arithmetic mean", "Arithmetic mean", "Absolute & %"],
    ]
    comp_table = Table(comparison_metrics, colWidths=[80, 130, 130, 90])
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(comp_table)
    
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "💡 <b>TIP:</b> FCS and NTA may show different D50 values due to their different measurement principles. "
        "FCS measures optical scatter (sensitive to refractive index), while NTA tracks Brownian motion (sensitive to viscosity). "
        "Differences of 10-20% are normal.",
        tip_style
    ))
    
    story.append(Paragraph("6.3 Visualization Options", h2_style))
    story.append(Paragraph("Available charts in Cross-Compare:", body_style))
    viz_options = [
        "<b>Overlay Histogram:</b> Overlaid size distributions from both methods",
        "<b>Discrepancy Chart:</b> Bar chart showing differences in each metric",
        "<b>KDE Comparison:</b> Kernel density estimation comparison",
        "<b>Correlation Scatter:</b> Scatter plot correlating FCS vs NTA values"
    ]
    for viz in viz_options:
        story.append(Paragraph(f"• {viz}", step_style))
    story.append(PageBreak())
    
    # ==================== 7. RESEARCH CHAT ====================
    story.append(Paragraph("7. Research Chat (AI Assistant)", h1_style))
    story.append(Paragraph(
        "The Research Chat tab provides a full-featured AI assistant specialized in EV research and analysis. "
        "It can help you interpret results, suggest experiments, and explain concepts.",
        body_style
    ))
    
    story.append(Paragraph("Getting Started with AI Chat", h2_style))
    chat_steps = [
        "<b>Step 1:</b> Navigate to the 'Research Chat' tab",
        "<b>Step 2:</b> Type your question or request in the input box",
        "<b>Step 3:</b> Press Enter or click Send",
        "<b>Step 4:</b> The AI will respond with relevant information",
        "<b>Step 5:</b> Continue the conversation as needed"
    ]
    for step in chat_steps:
        story.append(Paragraph(f"→ {step}", step_style))
    
    story.append(Paragraph("Suggested Questions", h2_style))
    suggestions = [
        "How do I interpret flow cytometry gating strategies?",
        "What are the key parameters for EV characterization?",
        "Help me analyze my uploaded FCS file",
        "Generate a size distribution graph for my data",
        "Guide me through cross-comparing datasets",
        "What do high polydispersity values indicate?",
        "Explain the difference between D50 and mean size"
    ]
    for suggestion in suggestions:
        story.append(Paragraph(f"• \"{suggestion}\"", step_style))
    
    story.append(Paragraph("File Upload in Chat", h2_style))
    story.append(Paragraph(
        "You can upload files directly in the chat for analysis:",
        body_style
    ))
    story.append(Paragraph("• Click the upload icon in the chat input area", step_style))
    story.append(Paragraph("• Select your .fcs or .txt file", step_style))
    story.append(Paragraph("• The AI will analyze and provide insights", step_style))
    
    story.append(Paragraph("Export Chat History", h2_style))
    story.append(Paragraph(
        "To save your conversation:",
        body_style
    ))
    story.append(Paragraph("• Click 'Export' dropdown", step_style))
    story.append(Paragraph("• Choose format: Markdown, JSON, or Text", step_style))
    story.append(Paragraph("• File downloads automatically", step_style))
    story.append(PageBreak())
    
    # ==================== 8. BEST PRACTICES ====================
    story.append(Paragraph("8. Best Practices", h1_style))
    story.append(Paragraph(
        "Follow these guidelines for optimal results:",
        body_style
    ))
    
    story.append(Paragraph("Data Preparation", h2_style))
    data_prep = [
        "Ensure samples are well-mixed before analysis",
        "Filter samples appropriately (0.22µm or 0.45µm)",
        "Record dilution factors accurately",
        "Note sample storage conditions and time"
    ]
    for item in data_prep:
        story.append(Paragraph(f"✓ {item}", step_style))
    
    story.append(Paragraph("File Naming Convention", h2_style))
    story.append(Paragraph(
        "Use consistent, descriptive file names:",
        body_style
    ))
    naming_examples = [
        "Format: [Project]_[Sample]_[Treatment]_[Date].fcs",
        "Example: PC3_EV_Control_20260120.fcs",
        "Example: HEK_TFF_10kDa_F5_20260120.txt",
        "Avoid spaces - use underscores instead"
    ]
    for example in naming_examples:
        story.append(Paragraph(f"• {example}", step_style))
    
    story.append(Paragraph("Experimental Conditions", h2_style))
    story.append(Paragraph(
        "Always fill in experimental conditions after upload:",
        body_style
    ))
    story.append(Paragraph("• Temperature at measurement", step_style))
    story.append(Paragraph("• Buffer/medium used (PBS, HEPES, etc.)", step_style))
    story.append(Paragraph("• Operator name for traceability", step_style))
    story.append(Paragraph("• Any relevant notes", step_style))
    
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "⚠️ <b>WARNING:</b> Missing experimental conditions may affect data interpretation and "
        "reproducibility. Always document your experimental setup.",
        warning_style
    ))
    
    story.append(Paragraph("Quality Control", h2_style))
    qc_items = [
        "Check for alerts in the notification panel",
        "Review anomaly detection results",
        "Verify D50 values are within expected range (30-500nm for EVs)",
        "Compare results with control samples",
        "Document any unusual observations"
    ]
    for item in qc_items:
        story.append(Paragraph(f"✓ {item}", step_style))
    story.append(PageBreak())
    
    # ==================== 9. TROUBLESHOOTING ====================
    story.append(Paragraph("9. Troubleshooting", h1_style))
    
    story.append(Paragraph("Common Issues and Solutions", h2_style))
    
    issues = [
        ["Issue", "Possible Cause", "Solution"],
        ["'Backend Offline' error", "FastAPI server not running", "Start server with 'python run_api.py'"],
        ["File upload fails", "File format not supported", "Ensure .fcs, .txt, or .csv extension"],
        ["No events detected", "Empty file or wrong channels", "Verify file contains data"],
        ["Very high D50 values", "Aggregation in sample", "Re-filter sample, verify dilution"],
        ["Analysis timeout", "Very large file", "Split file or increase timeout"],
        ["Charts not loading", "Browser cache issue", "Clear cache and refresh (Ctrl+F5)"],
        ["Login fails", "Invalid credentials", "Reset password or contact admin"],
    ]
    issues_table = Table(issues, colWidths=[110, 130, 200])
    issues_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#DC2626")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(issues_table)
    
    story.append(Paragraph("Getting Help", h2_style))
    story.append(Paragraph(
        "If issues persist:",
        body_style
    ))
    help_steps = [
        "Take a screenshot of the error message",
        "Note the steps that led to the issue",
        "Check browser console for errors (F12 → Console)",
        "Contact the development team with details",
        "Use the Research Chat to ask for guidance"
    ]
    for step in help_steps:
        story.append(Paragraph(f"• {step}", step_style))
    story.append(PageBreak())
    
    # ==================== 10. APPENDIX ====================
    story.append(Paragraph("10. Appendix", h1_style))
    
    story.append(Paragraph("A. Keyboard Shortcuts", h2_style))
    shortcuts = [
        ["Shortcut", "Action"],
        ["Ctrl + S", "Save current analysis"],
        ["Ctrl + E", "Open export menu"],
        ["Ctrl + R", "Refresh data"],
        ["Esc", "Close modal/dialog"],
        ["Tab", "Navigate between fields"],
    ]
    shortcuts_table = Table(shortcuts, colWidths=[100, 250])
    shortcuts_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(shortcuts_table)
    
    story.append(Paragraph("B. Glossary", h2_style))
    glossary = [
        "<b>EV (Extracellular Vesicle):</b> Membrane-bound particles released by cells",
        "<b>FCS (Flow Cytometry Standard):</b> Standard file format for flow cytometry data",
        "<b>NTA (Nanoparticle Tracking Analysis):</b> Method to measure particle size and concentration",
        "<b>D10/D50/D90:</b> Size percentiles (10th, 50th, 90th)",
        "<b>FSC (Forward Scatter):</b> Light scattered in forward direction, related to size",
        "<b>SSC (Side Scatter):</b> Light scattered at 90°, related to granularity",
        "<b>Polydispersity:</b> Measure of size distribution width",
        "<b>Gating:</b> Selecting a subset of particles based on scatter properties"
    ]
    for term in glossary:
        story.append(Paragraph(f"• {term}", step_style))
    
    story.append(Paragraph("C. Contact Information", h2_style))
    contact_info = [
        ["Support Type", "Contact"],
        ["Technical Support", "tech@crmit.com"],
        ["Bug Reports", "bugs@crmit.com"],
        ["Feature Requests", "features@crmit.com"],
        ["General Inquiries", "info@crmit.com"],
    ]
    contact_table = Table(contact_info, colWidths=[150, 250])
    contact_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(contact_table)
    
    story.append(Spacer(1, 30))
    story.append(Paragraph(
        "— End of Document —",
        ParagraphStyle('EndDoc', parent=styles['Normal'], fontSize=12, textColor=colors.HexColor("#6B7280"), alignment=TA_CENTER)
    ))
    
    # Build PDF
    doc.build(story, onFirstPage=create_header_footer, onLaterPages=create_header_footer)
    print(f"✅ User Manual generated: {output_path}")
    return output_path


if __name__ == "__main__":
    create_user_manual()
