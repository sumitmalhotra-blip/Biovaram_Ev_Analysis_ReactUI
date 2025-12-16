# app.py

import streamlit as st
import os
import io
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import base64
import sys

# Add src to path for anomaly detection import
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))

# Import API client
from api_client import get_client, check_api_connection

# Import Anomaly Detection (optional - graceful fallback)
use_anomaly_detection = False
try:
    from visualization.anomaly_detection import AnomalyDetector
    use_anomaly_detection = True
except Exception:
    use_anomaly_detection = False

# Import Interactive Plots (optional - graceful fallback)
use_interactive_plots = False
try:
    from visualization.interactive_plots import (
        create_scatter_plot,
        create_fsc_ssc_scatter,
        create_size_vs_scatter_plot,
        create_histogram,
        create_size_distribution_histogram,
        create_theoretical_vs_measured_plot,
        create_analysis_dashboard,
        get_export_config,
        DARK_THEME,
        # NTA-specific interactive plots
        create_nta_size_distribution,
        create_nta_concentration_profile,
        create_theoretical_curve,
        create_nta_raw_vs_corrected
    )
    use_interactive_plots = True
except Exception as e:
    use_interactive_plots = False

# Import Cross-Comparison Visualization (optional - graceful fallback)
use_cross_comparison = False
try:
    from visualization.cross_comparison import (
        create_size_overlay_histogram,
        create_kde_comparison,
        create_correlation_scatter,
        create_comparison_dashboard,
        create_discrepancy_chart,
        calculate_comparison_stats,
        create_stats_table
    )
    use_cross_comparison = True
except Exception as e:
    use_cross_comparison = False

# Import NTA Corrections Module (optional - graceful fallback)
use_nta_corrections = False
try:
    from physics.nta_corrections import (
        calculate_water_viscosity,
        correct_nta_size,
        get_correction_factor,
        apply_corrections_to_dataframe,
        get_viscosity_temperature_table,
        get_correction_reference_table,
        create_correction_summary,
        get_media_viscosity,
        REFERENCE_TEMPERATURE_C,
        MEDIA_VISCOSITY_FACTORS
    )
    use_nta_corrections = True
except Exception as e:
    use_nta_corrections = False

# Optional libraries
use_pymiescatt = False
try:
    import PyMieScatt as PMS  # type: ignore[import-not-found]
    use_pymiescatt = True
except Exception:
    use_pymiescatt = False

use_fcsparser = False
try:
    import fcsparser  # type: ignore[import-not-found]
    use_fcsparser = True
except Exception:
    use_fcsparser = False

use_pyarrow = False
try:
    import pyarrow as pa  # type: ignore[import-not-found]
    import pyarrow.parquet as pq  # type: ignore[import-not-found]
    use_pyarrow = True
except Exception:
    use_pyarrow = False

# Streamlit config
st.set_page_config(
    page_title="EV Analysis Tool",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ensure directories
os.makedirs("images", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

# =================================================================================
# ENHANCED CSS STYLING - COMPLETE PROFESSIONAL THEME
# =================================================================================
st.markdown("""
<style>
    /* ========== GOOGLE FONTS ========== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Poppins:wght@600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    /* ========== CSS VARIABLES ========== */
    :root {
        --primary: #00b4d8;
        --primary-dark: #0096c7;
        --primary-light: #48cae4;
        --primary-glow: rgba(0, 180, 216, 0.4);
        --secondary: #7c3aed;
        --secondary-light: #a78bfa;
        --secondary-glow: rgba(124, 58, 237, 0.3);
        --accent: #f72585;
        --accent-light: #ff6b9d;
        --success: #10b981;
        --success-bg: rgba(16, 185, 129, 0.15);
        --warning: #f59e0b;
        --warning-bg: rgba(245, 158, 11, 0.15);
        --error: #ef4444;
        --error-bg: rgba(239, 68, 68, 0.15);
        --info-bg: rgba(0, 180, 216, 0.15);
        --bg-dark: #0a0e17;
        --bg-darker: #060910;
        --bg-card: #111827;
        --bg-card-hover: #1f2937;
        --bg-elevated: #1a2332;
        --text-primary: #f8fafc;
        --text-secondary: #94a3b8;
        --text-muted: #64748b;
        --text-dim: #475569;
        --border-color: rgba(255, 255, 255, 0.08);
        --border-hover: rgba(255, 255, 255, 0.15);
        --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
        --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.4);
        --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.5);
        --shadow-glow: 0 0 40px var(--primary-glow);
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
        --radius-xl: 20px;
        --radius-2xl: 24px;
        --transition-fast: 0.15s ease;
        --transition-normal: 0.25s ease;
        --transition-slow: 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* ========== GLOBAL STYLES ========== */
    .stApp {
        background:
            radial-gradient(ellipse at 20% 0%, rgba(0, 180, 216, 0.08) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 100%, rgba(124, 58, 237, 0.08) 0%, transparent 50%),
            radial-gradient(ellipse at 50% 50%, rgba(0, 0, 0, 0.3) 0%, transparent 70%),
            linear-gradient(180deg, var(--bg-dark) 0%, var(--bg-darker) 100%);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        min-height: 100vh;
    }

    /* Hide default Streamlit elements */
#MainMenu, footer { visibility: hidden; }  /* OK */
header {
    visibility: hidden !important;
    height: 0px !important;
}



    /* Removed top padding to move content to top */
    .main .block-container {
        padding: 0 3rem 4rem !important;
        padding-top: 0 !important;
        max-width: 1500px;
    }
    
    /* Remove ALL default Streamlit top spacing */
    .stApp > header {
        height: 0 !important;
        min-height: 0 !important;
    }
    
    .appview-container {
        padding-top: 0 !important;
    }
    
    section[data-testid="stAppViewContainer"] {
        padding-top: 0 !important;
    }
    
    .stAppViewBlockContainer {
        padding-top: 0 !important;
    }
    
    [data-testid="stAppViewContainer"] > section > div {
        padding-top: 0 !important;
    }
    
    .block-container {
        padding-top: 0 !important;
    }

    /* ========== TYPOGRAPHY ========== */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Poppins', sans-serif !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.02em;
    }

    p, span, div {
        color: var(--text-secondary);
    }

    /* Made title smaller and moved to top */
    .custom-header {
        text-align: center;
        font-size: clamp(18px, 2.5vw, 24px);
        font-weight: 700;
        font-family: 'Poppins', sans-serif;
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 40%, var(--secondary-light) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0 0 4px;
        padding-top: 5px;
        letter-spacing: -1px;
        filter: drop-shadow(0 0 40px var(--primary-glow));
        animation: headerPulse 4s ease-in-out infinite;
    }

    @keyframes headerPulse {
        0%, 100% { filter: drop-shadow(0 0 30px var(--primary-glow)); }
        50% { filter: drop-shadow(0 0 50px var(--secondary-glow)); }
    }

    /* Made subtitle smaller with minimal margins */
    .subtitle {
        text-align: center;
        font-size: 11px;
        color: var(--text-muted);
        margin-bottom: 8px;
        margin-top: 0;
        font-weight: 400;
        letter-spacing: 0.3px;
    }

    /* ========== DIVIDERS ========== */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, var(--primary) 20%, var(--secondary) 80%, transparent 100%);
        margin: 20px 0;
        opacity: 0.4;
    }

    /* ========== TAB STYLING ========== */
    .stTabs {
        background: transparent;
    }

    .stTabs [data-baseweb="tab-list"] {
        background: var(--bg-card);
        border-radius: var(--radius-xl);
        padding: 10px;
        gap: 10px;
        border: 1px solid var(--border-color);
        box-shadow: var(--shadow-lg), inset 0 1px 0 rgba(255,255,255,0.05);
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: var(--radius-md);
        color: #ffffff !important;
        font-weight: 600;
        font-size: 16px;
        padding: 14px 28px;
        transition: all var(--transition-normal);
        border: none;
        position: relative;
        overflow: hidden;
    }

    .stTabs [data-baseweb="tab"]::before {
        content: '';
        position: absolute;
        inset: 0;
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        opacity: 0;
        transition: opacity var(--transition-normal);
        border-radius: var(--radius-md);
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: var(--primary-light) !important;
    }

    .stTabs [data-baseweb="tab"]:hover::before {
        opacity: 0.1;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%) !important;
        color: #0a0e17 !important;
        box-shadow: 0 4px 20px var(--primary-glow), inset 0 1px 0 rgba(255,255,255,0.2);
        font-weight: 700;
    }

    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }

    div[data-baseweb="tab"] button p,
    div[data-testid="stTabs"] button p {
        font-size: 17px !important;
        font-weight: 700 !important;
    }

    .stTabs [aria-selected="true"] p {
        color: #0a0e17 !important;
    }

    /* ========== BUTTON STYLING ========== */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        color: #0a0e17 !important;
        border: none;
        border-radius: var(--radius-md);
        padding: 14px 32px;
        font-weight: 700;
        font-size: 15px;
        font-family: 'Inter', sans-serif;
        letter-spacing: 0.3px;
        transition: all var(--transition-slow);
        box-shadow: 0 4px 20px var(--primary-glow), inset 0 1px 0 rgba(255,255,255,0.2);
        text-transform: uppercase;
        position: relative;
        overflow: hidden;
        text-shadow: none;
    }

    .stButton > button * {
        color: #0a0e17 !important;
    }

    .stButton > button p {
        color: #0a0e17 !important;
        font-weight: 700;
    }

    .stButton > button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
        transition: left 0.5s ease;
    }

    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 30px var(--primary-glow), inset 0 1px 0 rgba(255,255,255,0.3);
        color: #0a0e17 !important;
    }

    .stButton > button:hover::before {
        left: 100%;
    }

    .stButton > button:active {
        transform: translateY(-1px);
        color: #0a0e17 !important;
    }

    .stDownloadButton > button {
        background: linear-gradient(135deg, var(--secondary) 0%, #9333ea 100%);
        box-shadow: 0 4px 20px var(--secondary-glow);
        color: #ffffff !important;
        font-weight: 700;
    }

    .stDownloadButton > button * {
        color: #ffffff !important;
    }

    .stDownloadButton > button:hover {
        color: #ffffff !important;
    }

    /* ========== FILE UPLOADER ========== */
    .stFileUploader {
        background: var(--bg-card);
        border: 2px dashed var(--border-color);
        border-radius: var(--radius-xl);
        padding: 24px;
        transition: all var(--transition-normal);
    }

    .stFileUploader:hover {
        border-color: var(--primary);
        background: var(--info-bg);
        box-shadow: 0 0 30px var(--primary-glow);
    }

    .stFileUploader label {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        font-size: 15px !important;
    }

    .stFileUploader [data-testid="stFileUploaderDropzone"] {
        background: transparent !important;
        border: none !important;
    }

    .stFileUploader small {
        color: var(--text-muted) !important;
    }

    /* ========== INPUT FIELDS ========== */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--radius-md) !important;
        color: var(--text-primary) !important;
        padding: 14px 18px !important;
        font-size: 15px !important;
        font-family: 'Inter', sans-serif !important;
        transition: all var(--transition-normal) !important;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 4px var(--primary-glow) !important;
        outline: none !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: var(--text-dim) !important;
    }

    .stNumberInput [data-baseweb="input"] {
        background: var(--bg-card) !important;
        border-radius: var(--radius-md) !important;
    }

    /* ========== SELECTBOX ========== */
    .stSelectbox > div > div {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--radius-md) !important;
    }

    .stSelectbox [data-baseweb="select"] > div {
        background: var(--bg-card) !important;
        border: none !important;
        color: var(--text-primary) !important;
    }

    /* ========== SLIDER ========== */
    .stSlider > div > div > div > div {
        background: linear-gradient(90deg, var(--primary), var(--secondary)) !important;
        height: 6px !important;
        border-radius: 3px !important;
    }

    .stSlider [data-baseweb="slider"] [data-testid="stThumbValue"] {
        background: var(--primary) !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: var(--radius-sm) !important;
        padding: 4px 8px !important;
    }

    .stSlider [data-testid="stTickBar"] > div {
        background: var(--border-color) !important;
    }

    /* ========== CHECKBOX ========== */
    .stCheckbox label {
        color: var(--text-secondary) !important;
        font-size: 14px !important;
    }

    .stCheckbox > div > div > div {
        background: var(--bg-card) !important;
        border: 2px solid var(--border-color) !important;
        border-radius: 6px !important;
    }

    /* ========== DATAFRAME/TABLE ========== */
    .stDataFrame {
        border-radius: var(--radius-lg) !important;
        overflow: hidden !important;
        border: 1px solid var(--border-color) !important;
        box-shadow: var(--shadow-md) !important;
    }

    .stDataFrame [data-testid="stDataFrameResizable"] {
        background: var(--bg-card) !important;
    }

    .stDataFrame th {
        background: var(--bg-elevated) !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        padding: 12px 16px !important;
    }

    .stDataFrame td {
        color: var(--text-secondary) !important;
        padding: 10px 16px !important;
        border-bottom: 1px solid var(--border-color) !important;
    }

    /* ========== SIDEBAR ========== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1f2e 0%, #0f0a1f 100%) !important;
        border-right: 2px solid var(--primary) !important;
        z-index: 999 !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #1a1f2e 0%, #0f0a1f 100%) !important;
    }

    [data-testid="stSidebar"] .block-container {
        padding: 2rem 1.5rem;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #ffffff !important;
        font-family: 'Poppins', sans-serif !important;
    }

    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span {
        color: #e0e0e0 !important;
    }

/* ==========================================================
   FIX SIDEBAR TOGGLE BUTTON (ICON VISIBLE + NOT OVERLAPPING)
   ========================================================== */

/* ==========================================================
   🔹 FINAL FULLY WORKING CSS FIX FOR SIDEBAR & TOGGLE
   🔹 DO NOT MODIFY ANYTHING INSIDE THIS BLOCK
   ========================================================== */

/* Restore the sidebar container */
[data-testid="stSidebar"] {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    min-width: 300px !important;
    width: 320px !important;
    position: relative !important;
    overflow-x: visible !important;
    overflow-y: auto !important;
    transform: none !important;
    z-index: 1000 !important;
    background: linear-gradient(180deg, #1a1f2e 0%, #0f0a1f 100%) !important;
}

/* Restore and style the sidebar toggle icon */
[data-testid="stSidebarCollapsedControl"] {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    pointer-events: auto !important;
    opacity: 1 !important;
    visibility: visible !important;

    /* Let Streamlit handle positioning */
    position: relative !important;
    top: auto !important;
    left: auto !important;

    /* Icon appearance */
    width: 38px !important;
    height: 38px !important;
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid var(--primary) !important;
    border-radius: 10px !important;
    box-shadow: 0 0 6px var(--primary-glow) !important;
    cursor: pointer !important;
    transition: transform 0.2s ease-in-out;
    z-index: 2000 !important;
}

[data-testid="stSidebarCollapsedControl"]:hover {
    transform: scale(1.07);
    background: var(--primary) !important;
}

[data-testid="stSidebarCollapsedControl"] svg {
    color: var(--primary) !important;
}
[data-testid="stSidebarCollapsedControl"]:hover svg {
    color: #0a0e17 !important;
}

/* Ensure Streamlit doesn't hide our toggle */
[data-testid="collapsedControl"] {
    all: unset !important;
}

/* 🔸 Fix header/menu hiding without affecting sidebar or logo */
#MainMenu, footer {
    visibility: hidden !important;
}
header {
    visibility: hidden !important;
    height: 0 !important;
}

/* Prevent global CSS from collapsing width */
section[data-testid="stSidebar"] > div {
    width: auto !important;
}


/* ================== KEEP DEFAULT BUTTON LOGIC ================== */
[data-testid="collapsedControl"] {
    all: unset !important; /* Remove previous forced styling */
}


    [data-testid="stSidebar"] button[kind="header"],
    [data-testid="stSidebar"] [data-testid="stBaseButton-header"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        color: var(--primary) !important;
        background: rgba(0, 245, 255, 0.1) !important;
        border: 1px solid var(--primary) !important;
        border-radius: 8px !important;
        z-index: 9999 !important;
    }

    [data-testid="stSidebar"] button[kind="header"]:hover,
    [data-testid="stSidebar"] [data-testid="stBaseButton-header"]:hover {
        background: var(--primary) !important;
        color: #0a0e17 !important;
    }

    section[data-testid="stSidebar"] button {
        color: #ffffff !important;
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid var(--border-color) !important;
        pointer-events: auto !important;
    }

    section[data-testid="stSidebar"] button:hover {
        background: rgba(0, 245, 255, 0.1) !important;
        border-color: var(--primary) !important;
    }

    /* ========== GLASS CARD ========== */
    .glass-card {
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-xl);
        padding: 28px;
        box-shadow: var(--shadow-lg), inset 0 1px 0 rgba(255,255,255,0.05);
        transition: all var(--transition-slow);
        position: relative;
        overflow: hidden;
    }

    .glass-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
    }

    .glass-card:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-glow), var(--shadow-lg);
        border-color: var(--primary);
    }

    /* ========== STAT CARDS ========== */
    .stat-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-lg);
        padding: 24px;
        text-align: center;
        transition: all var(--transition-slow);
        position: relative;
        overflow: hidden;
    }

    .stat-card::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--primary), var(--secondary));
        transform: scaleX(0);
        transition: transform var(--transition-slow);
    }

    .stat-card:hover {
        border-color: var(--primary);
        box-shadow: 0 8px 30px var(--primary-glow);
        transform: translateY(-2px);
    }

    .stat-card:hover::after {
        transform: scaleX(1);
    }

    .stat-value {
        font-size: 36px;
        font-weight: 800;
        font-family: 'Poppins', sans-serif;
        background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.2;
    }

    .stat-label {
        color: var(--text-muted);
        font-size: 14px;
        font-weight: 500;
        margin-top: 8px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* ========== SECTION HEADERS ========== */
    .section-header {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 1px solid var(--border-color);
    }

    .section-header h3 {
        margin: 0 !important;
        color: var(--text-primary) !important;
        font-size: 20px !important;
        font-weight: 700 !important;
    }

    .section-icon {
        width: 44px;
        height: 44px;
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        border-radius: var(--radius-md);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        box-shadow: 0 4px 15px var(--primary-glow);
    }

    /* ========== CHAT STYLING ========== */
    .chat-container {
        background: var(--bg-card);
        border-radius: var(--radius-xl);
        padding: 20px;
        border: 1px solid var(--border-color);
        max-height: 350px;
        overflow-y: auto;
        margin-bottom: 16px;
    }

    .chat-message-user {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        color: white;
        padding: 14px 20px;
        border-radius: 20px 20px 6px 20px;
        margin: 10px 0;
        margin-left: 25%;
        font-size: 14px;
        box-shadow: 0 4px 15px var(--primary-glow);
        animation: slideInRight 0.3s ease-out;
        line-height: 1.5;
    }

    .chat-message-bot {
        background: var(--bg-elevated);
        color: var(--text-primary);
        padding: 14px 20px;
        border-radius: 20px 20px 20px 6px;
        margin: 10px 0;
        margin-right: 25%;
        font-size: 14px;
        border: 1px solid var(--border-color);
        animation: slideInLeft 0.3s ease-out;
        line-height: 1.5;
    }

    @keyframes slideInRight {
        from { opacity: 0; transform: translateX(30px); }
        to { opacity: 1; transform: translateX(0); }
    }

    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-30px); }
        to { opacity: 1; transform: translateX(0); }
    }

    /* ========== ALERT MESSAGES ========== */
    .stSuccess {
        background: var(--success-bg) !important;
        border: 1px solid var(--success) !important;
        border-radius: var(--radius-md) !important;
        color: var(--success) !important;
        padding: 14px 18px !important;
    }

    .stInfo {
        background: var(--info-bg) !important;
        border: 1px solid var(--primary) !important;
        border-radius: var(--radius-md) !important;
        color: var(--primary-light) !important;
        padding: 14px 18px !important;
    }

    .stWarning {
        background: var(--warning-bg) !important;
        border: 1px solid var(--warning) !important;
        border-radius: var(--radius-md) !important;
        padding: 14px 18px !important;
    }

    .stError {
        background: var(--error-bg) !important;
        border: 1px solid var(--error) !important;
        border-radius: var(--radius-md) !important;
        padding: 14px 18px !important;
    }

    /* ========== PROGRESS BAR ========== */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--primary), var(--secondary)) !important;
        border-radius: 4px !important;
    }

    .stProgress > div > div {
        background: var(--bg-card) !important;
        border-radius: 4px !important;
    }

    /* ========== SPINNER ========== */
    .stSpinner > div {
        border-top-color: var(--primary) !important;
    }

    /* ========== IMAGE CONTAINER ========== */
    .stImage {
        border-radius: var(--radius-lg);
        overflow: hidden;
        box-shadow: var(--shadow-lg);
        border: 1px solid var(--border-color);
    }

    /* ========== METRICS ========== */
    [data-testid="stMetricValue"] {
        color: var(--primary) !important;
        font-weight: 700 !important;
        font-size: 28px !important;
    }

    [data-testid="stMetricLabel"] {
        color: var(--text-secondary) !important;
    }

    /* ========== EXPANDER ========== */
    .streamlit-expanderHeader {
        background: var(--bg-card) !important;
        border-radius: var(--radius-md) !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        border: 1px solid var(--border-color) !important;
    }

    .streamlit-expanderContent {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-top: none !important;
        border-radius: 0 0 var(--radius-md) var(--radius-md) !important;
    }

    /* ========== CUSTOM SCROLLBAR ========== */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: var(--bg-dark);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, var(--primary), var(--secondary));
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary-light);
    }

    /* ========== COLUMN SPACING ========== */
    [data-testid="column"] {
        padding: 0 10px;
    }

    /* ========== LABELS ========== */
    .stSelectbox label,
    .stTextInput label,
    .stNumberInput label,
    .stSlider label,
    .stFileUploader label {
        color: var(--text-primary) !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        margin-bottom: 8px !important;
    }

    /* ========== CAPTIONS ========== */
    .stCaption {
        color: var(--text-muted) !important;
        font-size: 13px !important;
    }

    /* ========== PROJECT LIST ITEM ========== */
    .project-item {
        padding: 10px 14px;
        background: rgba(0, 180, 216, 0.08);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-sm);
        margin: 6px 0;
        font-size: 13px;
        color: var(--text-secondary);
        transition: all var(--transition-fast);
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .project-item:hover {
        background: rgba(0, 180, 216, 0.15);
        border-color: var(--primary);
        color: var(--text-primary);
    }

    /* ========== TOOLTIP ========== */
    [data-testid="stTooltipIcon"] {
        color: var(--text-muted) !important;
    }

    /* ========== ANIMATIONS ========== */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .fade-in {
        animation: fadeIn 0.4s ease-out;
    }

    /* ========== RESPONSIVE ========== */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 0 1.5rem 4rem !important;
        }

        .custom-header {
            font-size: 20px;
        }

        .subtitle {
            font-size: 10px;
        }

        .stat-value {
            font-size: 28px;
        }
    }
        .glass-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 40px var(--shadow-glow);
        border-color: var(--primary-light);
    }
/* ========== GLASS CARD ========== */
.glass-card {
    background: rgba(17, 24, 39, 0.7);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-xl);
    padding: 28px;
    box-shadow: var(--shadow-lg), inset 0 1px 0 rgba(255,255,255,0.05);
    transition: all var(--transition-slow);
    position: relative;
    overflow: hidden;
}

.glass-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
}

.glass-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 40px var(--primary-glow), inset 0 1px 0 rgba(255,255,255,0.2);
    border-color: var(--primary-light);
}

/* ========== CUSTOM TAB BUTTONS ========== */
/* Style the tab navigation buttons */
div[data-testid="column"] > div > div > button[kind="primary"] {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 12px 20px !important;
    border-radius: var(--radius-md) var(--radius-md) 0 0 !important;
    box-shadow: 0 4px 15px var(--primary-glow) !important;
    position: relative !important;
}

div[data-testid="column"] > div > div > button[kind="primary"]::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--primary-light);
}

div[data-testid="column"] > div > div > button[kind="secondary"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-color) !important;
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    padding: 12px 20px !important;
    border-radius: var(--radius-md) var(--radius-md) 0 0 !important;
    transition: all var(--transition-normal) !important;
}

div[data-testid="column"] > div > div > button[kind="secondary"]:hover {
    background: var(--bg-elevated) !important;
    color: var(--text-primary) !important;
    border-color: var(--primary) !important;
}

</style>
""", unsafe_allow_html=True)


# =================================================================================
# LOGO FUNCTION - Logo is no longer fixed, flows with content
# =================================================================================
def load_logo_top_right():
    logo_path = os.path.join(os.getcwd(), "logo.png")
    if not os.path.exists(logo_path):
        return

    encoded_logo = base64.b64encode(open(logo_path, "rb").read()).decode()

    st.markdown(f"""
    <style>
    .header-container {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 5px 20px 0 20px;
        margin: 0;
        margin-top: 5px;
        padding-top: 5px;
    }}
    
    .logo-container {{
        width: 70px;
        height: auto;
        filter: drop-shadow(0 4px 16px rgba(0, 180, 216, 0.3));
        transition: all 0.3s ease;
    }}

    .logo-container:hover {{
        transform: scale(1.05);
        filter: drop-shadow(0 6px 24px rgba(0, 180, 216, 0.5));
    }}
    </style>

    <div class="header-container">
        <img src="data:image/png;base64,{encoded_logo}" class="logo-container">
    </div>
    """, unsafe_allow_html=True)

# Call the function
load_logo_top_right()

# Header with subtitle - reduced margins
st.markdown("""
    <div class="custom-header">EV Analysis Tool</div>
    <p class="subtitle">Advanced Extracellular Vesicle Analysis & Particle Size Estimation</p>
""", unsafe_allow_html=True)

st.markdown("---")

# =================================================================================
# HELPER FUNCTIONS
# =================================================================================
# These utility functions handle file upload, conversion, and data loading operations.
# They form the foundation for data processing in the Streamlit application.
# =================================================================================

def save_uploadedfile_to_path(uploaded_file, dest_folder="uploads"):
    """
    Save a Streamlit UploadedFile object to disk with collision handling.
    
    WHAT IT DOES:
    -------------
    Takes a Streamlit UploadedFile object (from st.file_uploader) and saves it
    to disk. If a file with the same name already exists, appends a numeric
    suffix to avoid overwriting (file.fcs → file_1.fcs → file_2.fcs, etc.).
    
    WHY THIS IS NEEDED:
    ------------------
    Streamlit's UploadedFile is an in-memory file-like object. To use it with
    file-based libraries (like fcsparser or pandas.read_parquet), we need to
    save it to disk first. The collision handling prevents data loss when users
    upload files with the same name multiple times.
    
    Args:
        uploaded_file: Streamlit UploadedFile object, or a string path if file
                      is already on disk (passthrough case)
        dest_folder: Destination folder for saved files (default: "uploads/")
    
    Returns:
        str: Full path to the saved file on disk
    
    Example:
        >>> uploaded = st.file_uploader("Upload FCS")
        >>> if uploaded:
        ...     path = save_uploadedfile_to_path(uploaded)
        ...     # path = "uploads/sample.fcs" or "uploads/sample_1.fcs" if collision
    """
    # Handle passthrough case: if already a path string, just return it
    if isinstance(uploaded_file, str) and os.path.exists(uploaded_file):
        return uploaded_file
    
    # Build destination path from folder + original filename
    dest_path = os.path.join(dest_folder, uploaded_file.name)  # type: ignore[attr-defined]
    
    # Handle filename collisions by appending numeric suffix
    base, ext = os.path.splitext(dest_path)
    i = 1
    while os.path.exists(dest_path):
        dest_path = f"{base}_{i}{ext}"
        i += 1
    
    # Write file contents to disk
    # getbuffer() returns the file contents as a bytes-like object
    with open(dest_path, "wb") as f:
        f.write(uploaded_file.getbuffer())  # type: ignore[attr-defined]
    
    return dest_path


def convert_anyfile_to_parquet(uploaded_file_or_path):
    """
    Convert uploaded file to Parquet format for efficient processing.
    
    WHAT IT DOES:
    -------------
    Takes any supported file format (FCS, CSV, Excel, JSON, Parquet) and
    converts it to Parquet format for faster downstream processing. Parquet
    is a columnar storage format that offers:
    - 5-10x faster read speeds than CSV
    - 50-90% smaller file sizes with compression
    - Type preservation (no data type inference issues)
    - Column pruning (read only needed columns)
    
    SUPPORTED FORMATS:
    ------------------
    - .fcs: Flow Cytometry Standard (requires fcsparser library)
    - .csv: Comma-Separated Values (pandas.read_csv)
    - .parquet: Already Parquet (passthrough)
    - .xlsx/.xls: Excel files (pandas.read_excel)
    - .json: JSON files (pandas.read_json)
    
    WHY CONVERT TO PARQUET:
    -----------------------
    1. Performance: Parquet is 10x faster to read than CSV for large files
    2. Size: Compressed Parquet is typically 80% smaller than CSV
    3. Types: Preserves data types (float64, int32, etc.) without inference
    4. Compatibility: Works with Dask, Spark, and other big data tools
    
    Args:
        uploaded_file_or_path: Streamlit UploadedFile object or file path string
    
    Returns:
        tuple: (parquet_path, dataframe)
            - parquet_path: Path to converted Parquet file (or None if failed)
            - dataframe: Pandas DataFrame with file contents (or None if failed)
    
    Example:
        >>> parquet_path, df = convert_anyfile_to_parquet(uploaded_fcs_file)
        >>> if df is not None:
        ...     st.dataframe(df.head())
    """
    # Save uploaded file to disk if needed
    if isinstance(uploaded_file_or_path, str) and os.path.exists(uploaded_file_or_path):
        path = uploaded_file_or_path
    else:
        path = save_uploadedfile_to_path(uploaded_file_or_path, dest_folder="uploads")

    lower = path.lower()
    try:
        # FCS files: Flow Cytometry Standard binary format
        # Requires fcsparser library (optional dependency)
        if lower.endswith(".fcs"):
            if not use_fcsparser:
                st.error("fcsparser not installed. Install with: pip install fcsparser")
                return None, None
            # Parse FCS file - returns metadata dict and event DataFrame
            meta, df = fcsparser.parse(path, reformat_meta=True)  # type: ignore[misc]
        
        # CSV files: Standard comma-separated values
        elif lower.endswith(".csv"):
            df = pd.read_csv(path)
        
        # Parquet files: Already in target format, just load and return
        elif lower.endswith(".parquet"):
            df = pd.read_parquet(path)
            return path, df
        
        # Excel files: XLSX (modern) or XLS (legacy)
        elif lower.endswith((".xlsx", ".xls")):
            df = pd.read_excel(path)
        
        # JSON files: JavaScript Object Notation
        elif lower.endswith(".json"):
            df = pd.read_json(path)
        
        else:
            st.error("Unsupported file type for conversion.")
            return None, None

        # Convert to Parquet if pyarrow is available
        # PyArrow provides fast Parquet I/O with good compression
        if use_pyarrow:
            parquet_path = os.path.join("uploads", os.path.basename(path).rsplit(".", 1)[0] + ".parquet")
            try:
                # Convert pandas DataFrame to PyArrow Table, then write as Parquet
                table = pa.Table.from_pandas(df)
                pq.write_table(table, parquet_path)
                return parquet_path, df
            except Exception as e:
                st.warning(f"Parquet conversion failed: {e}. Returning dataframe without parquet.")
                return None, df
        else:
            # Fallback: save as CSV if pyarrow not available
            csv_path = os.path.join("uploads", os.path.basename(path).rsplit(".", 1)[0] + ".csv")
            df.to_csv(csv_path, index=False)
            return csv_path, df
    except Exception as e:
        st.error(f"Failed to convert file: {e}")
        return None, None


def load_dataframe_from_uploaded(uploaded_file_or_path):
    """
    Load a DataFrame from uploaded file, converting to Parquet if needed.
    
    WHAT IT DOES:
    -------------
    This is the main entry point for loading data from uploaded files.
    It handles the full pipeline: upload → save → convert → load.
    
    PIPELINE STEPS:
    ---------------
    1. Save uploaded file to disk (if not already saved)
    2. Convert to Parquet format (if not already Parquet)
    3. Load DataFrame from Parquet (for best performance)
    4. Return DataFrame and source file path
    
    WHY PREFER PARQUET:
    ------------------
    - Faster loading for subsequent operations
    - Type preservation (no re-inferring column types)
    - Smaller memory footprint
    - Works better with large datasets
    
    Args:
        uploaded_file_or_path: Streamlit UploadedFile object or file path string
    
    Returns:
        tuple: (dataframe, source_path)
            - dataframe: Pandas DataFrame with file contents
            - source_path: Path to source file (Parquet if converted, else original)
    
    Example:
        >>> df, path = load_dataframe_from_uploaded(uploaded_file)
        >>> st.write(f"Loaded {len(df)} rows from {path}")
        >>> st.dataframe(df.head())
    """
    # Convert file to Parquet and get DataFrame
    parquet_path, df = convert_anyfile_to_parquet(uploaded_file_or_path)
    
    # If conversion produced a Parquet file, load from it for best performance
    if parquet_path and os.path.exists(parquet_path) and parquet_path.lower().endswith(".parquet"):
        try:
            # Load from Parquet for faster type-safe loading
            df2 = pd.read_parquet(parquet_path)
            return df2, parquet_path
        except Exception:
            # Fall back to the DataFrame from conversion
            return df, parquet_path
    
    return df, parquet_path

# =================================================================================
# MIE SCATTERING THEORY - THEORETICAL LOOKUP TABLE
# =================================================================================
# This section implements Mie scattering theory for particle size estimation.
# Mie theory describes how spherical particles scatter light and is fundamental
# to flow cytometry-based particle sizing.
# =================================================================================

@st.cache_data(show_spinner=False)
def build_theoretical_lookup(lambda_nm, n_particle, n_medium, fsc_range, ssc_range, diameters):  # type: ignore[no-untyped-def]
    """
    Build theoretical FSC/SSC ratio lookup table using Mie scattering theory.
    
    WHAT THIS DOES:
    ---------------
    Creates a mapping table: particle_diameter → expected_FSC/SSC_ratio
    This table is used to convert measured scatter ratios back to particle sizes.
    
    MIE SCATTERING PHYSICS:
    -----------------------
    When light hits a spherical particle, it scatters in all directions.
    The scatter pattern depends on:
    1. Particle size relative to wavelength (size parameter x = πd/λ)
    2. Refractive index contrast (n_particle/n_medium)
    3. Observation angle
    
    Key insight: The ratio of forward scatter (FSC) to side scatter (SSC)
    is a function of particle diameter. By measuring FSC/SSC, we can infer size.
    
    ALGORITHM:
    ----------
    1. Generate angular range [0°, 180°] with 1000 points
    2. For each diameter in the search range:
       a. Calculate full angular scattering function using PyMieScatt
       b. Integrate intensity over FSC angle range (typically 1-15°)
       c. Integrate intensity over SSC angle range (typically 85-95°)
       d. Compute ratio: FSC_integral / SSC_integral
    3. Return lookup table: diameter → ratio
    
    FALLBACK (NO PyMieScatt):
    -------------------------
    If PyMieScatt is not installed, uses a simplified power-law approximation:
        ratio = (A * d^p) / (B + d^q)
    This approximation captures the general trend but is less accurate.
    
    CACHING:
    --------
    Results are cached using @st.cache_data to avoid recomputing for same parameters.
    This makes subsequent analyses with same settings ~100x faster.
    
    Args:
        lambda_nm: Laser wavelength in nanometers (e.g., 488 for blue laser)
        n_particle: Particle refractive index (e.g., 1.38-1.45 for EVs)
        n_medium: Medium refractive index (e.g., 1.33 for PBS/water)
        fsc_range: Tuple of (min_angle, max_angle) for FSC in degrees
        ssc_range: Tuple of (min_angle, max_angle) for SSC in degrees
        diameters: Array of particle diameters (nm) to compute ratios for
    
    Returns:
        tuple: (angles_array, ratios_array)
            - angles: Array of angles used in calculation [0, 180]
            - ratios: Array of FSC/SSC ratios, one per diameter
    
    Performance:
        - With PyMieScatt: ~0.1-1 second for 200 diameter points
        - Without PyMieScatt: ~10 ms for 200 diameter points
    """
    # Generate angular grid: 1000 points from 0° to 180°
    angles = np.linspace(0, 180, 1000)
    
    # Initialize output array
    ratios = np.zeros_like(diameters, dtype=float)
    
    if use_pymiescatt:
        # Full Mie theory calculation using PyMieScatt library
        for i, D in enumerate(diameters):
            try:
                # Calculate angular scattering function
                # Returns: [parallel intensity, perpendicular intensity]
                # We use the total (unpolarized) intensity = sum of both
                intensity = PMS.ScatteringFunction(n_particle / n_medium, D, lambda_nm, angles, nMedium=n_medium)[0]
                
                # Create angular masks for FSC and SSC ranges
                mask_f = (angles >= fsc_range[0]) & (angles <= fsc_range[1])  # Forward scatter
                mask_s = (angles >= ssc_range[0]) & (angles <= ssc_range[1])  # Side scatter
                
                # Integrate intensity over each angular range using trapezoidal rule
                I_FSC = np.trapz(intensity[mask_f], angles[mask_f])  # type: ignore[arg-type]
                I_SSC = np.trapz(intensity[mask_s], angles[mask_s])  # type: ignore[arg-type]
                
                # Compute ratio (avoid division by zero)
                ratios[i] = float(I_FSC) / float(I_SSC) if I_SSC != 0 else np.nan
            except Exception:
                ratios[i] = np.nan
        
        # Handle NaN values in results
        if not np.any(np.isfinite(ratios)):
            # All calculations failed, fall back to zeros
            ratios = np.zeros_like(diameters, dtype=float)
        else:
            # Replace NaN with max valid ratio (prevents lookup errors)
            ratios = np.nan_to_num(ratios, nan=np.nanmax(ratios[np.isfinite(ratios)]))
    else:
        # Fallback: simplified power-law approximation
        # This approximation: ratio ≈ (A*d^5.5) / (B + d^3)
        # Captures general trend that larger particles scatter more forward
        A = 1e-6; p = 5.5; B = 1e-2; q = 3.0
        ratios = (A * diameters**p) / (B + diameters**q)
        
        # Ensure monotonic increasing (required for unique inverse lookup)
        ratios = np.maximum.accumulate(ratios)
    
    return angles, ratios


def estimate_diameters_vectorized(measured_ratios, theoretical_ratios, diameters):
    """
    VECTORIZED PARTICLE SIZE ESTIMATION - CORE ALGORITHM
    
    This is the MAIN function for converting measured FSC/SSC ratios to 
    particle diameters. It uses the theoretical lookup table built by
    build_theoretical_lookup() to find the best-matching size for each event.
    
    WHAT IT DOES:
    -------------
    For each measured FSC/SSC ratio:
    1. Compare to ALL theoretical ratios in lookup table
    2. Find the diameter with the closest matching ratio
    3. Return that diameter as the estimated particle size
    
    WHY VECTORIZED:
    ---------------
    FCS files often have 100,000+ events. Processing each one in a Python loop
    would be extremely slow (minutes to hours). NumPy vectorization processes
    all events simultaneously using optimized C code, reducing time to seconds.
    
    Performance comparison:
    - Python loop: ~100,000 events/second
    - Vectorized: ~10,000,000 events/second (100x faster)
    
    ALGORITHM:
    ----------
    Uses NumPy broadcasting to compute all pairwise differences at once:
    
    1. measured_ratios: shape (N,) - one ratio per event
    2. theoretical_ratios: shape (M,) - one ratio per diameter point
    3. Broadcasting creates: shape (N, M) - all N×M differences
    4. argmin along axis 1 finds best match for each event
    
    MEMORY CONSIDERATION:
    --------------------
    For N=100,000 events and M=200 diameter points:
    - Difference matrix: 100,000 × 200 × 8 bytes = 160 MB
    This is acceptable for typical workloads. For larger N, consider batching.
    
    Args:
        measured_ratios: 1D array of measured FSC/SSC ratios (length N)
        theoretical_ratios: 1D array of theoretical ratios from lookup table (length M)
        diameters: 1D array of diameters corresponding to theoretical_ratios (length M)
    
    Returns:
        tuple: (estimated_diameters, matched_ratios, matched_indices)
            - estimated_diameters: Array of estimated sizes in nm (length N)
            - matched_ratios: The theoretical ratio that was matched (length N)
            - matched_indices: Index into theoretical_ratios for each match (length N)
    
    Example:
        >>> # Measure FSC/SSC ratios from 100,000 events
        >>> ratios = fsc_values / ssc_values
        >>> 
        >>> # Build lookup table (cached)
        >>> _, theoretical = build_theoretical_lookup(488, 1.38, 1.33, ...)
        >>> 
        >>> # Estimate sizes - runs in ~0.5 seconds for 100K events
        >>> sizes, _, _ = estimate_diameters_vectorized(ratios, theoretical, diameters)
        >>> 
        >>> # Result: sizes array with 100,000 diameter estimates
        >>> print(f"Median size: {np.nanmedian(sizes):.1f} nm")
    """
    # Convert to numpy arrays
    measured = np.asarray(measured_ratios)
    theoretical = np.asarray(theoretical_ratios)
    diams = np.asarray(diameters)
    
    # Create output arrays (initialized to NaN)
    n = len(measured)
    estimated_diameters = np.full(n, np.nan)
    matched_ratios = np.full(n, np.nan)
    matched_indices = np.full(n, np.nan)
    
    # Find valid (non-NaN) measurements
    valid_mask = np.isfinite(measured)
    valid_measured = measured[valid_mask]
    
    if len(valid_measured) > 0:
        # VECTORIZED COMPUTATION:
        # Broadcasting creates (n_valid, n_theoretical) matrix of differences
        # This is the key optimization - processes all events simultaneously
        diffs = np.abs(valid_measured[:, np.newaxis] - theoretical[np.newaxis, :])
        
        # Find best match index for each measurement (minimum difference)
        best_indices = np.argmin(diffs, axis=1)
        
        # Assign results using advanced indexing
        estimated_diameters[valid_mask] = diams[best_indices]
        matched_ratios[valid_mask] = theoretical[best_indices]
        matched_indices[valid_mask] = best_indices
    
    return estimated_diameters, matched_ratios, matched_indices


# =================================================================================
# CHATBOT - SIMPLE DATA ANALYSIS ASSISTANT
# =================================================================================
# A lightweight chatbot for quick data exploration and Q&A about uploaded datasets.
# Provides instant access to data statistics without writing code.
# =================================================================================

def analyze_file_for_chat(path_or_uploaded):
    """
    Generate quick statistical summary of uploaded data for chatbot.
    
    WHAT IT DOES:
    -------------
    Loads the uploaded file and generates a pandas describe() summary
    with statistics for all columns (numeric and categorical).
    
    This gives users an instant overview of their data:
    - Count of values per column
    - Mean, std, min/max for numeric columns
    - Top values for categorical columns
    
    Args:
        path_or_uploaded: File path or Streamlit UploadedFile object
    
    Returns:
        str: HTML-formatted table with statistics, or error message
    """
    df, src = load_dataframe_from_uploaded(path_or_uploaded)
    if df is None:
        return "Cannot load file."
    try:
        # Generate comprehensive statistics using pandas describe()
        # include="all" includes non-numeric columns too
        return "Quick Dataset Summary:<br>" + df.describe(include="all").to_html(classes="table table-striped", border=0)
    except Exception as e:
        return f"Error summarizing file: {e}"


def chatbot_ui(uploaded):
    """
    Render the chatbot user interface with message history.
    
    WHAT IT DOES:
    -------------
    Creates a simple chat interface where users can ask questions about their data.
    Supports basic intents:
    - Greetings ("hello", "hi")
    - Data analysis ("analyze", "statistics")
    - General help (catchall response)
    
    ARCHITECTURE:
    -------------
    Uses Streamlit session state to persist chat history across reruns.
    Messages are stored as (sender, text) tuples and rendered as HTML.
    
    WHY SIMPLE:
    -----------
    This is a basic rule-based chatbot, not an LLM. It provides immediate
    value for common queries without the complexity/cost of AI integration.
    For advanced analysis, users should use the specialized analysis tabs.
    
    Args:
        uploaded: Currently uploaded file (to analyze when user asks)
    """
    # Initialize chat history in session state (persists across reruns)
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    st.markdown('<div class="section-header"><div class="section-icon">💬</div><h3>Analysis Chatbot</h3></div>', unsafe_allow_html=True)

    # Build chat messages HTML container
    chat_html = '<div class="chat-container">'
    for sender, text in st.session_state.chat_history:
        if sender == "You":
            chat_html += f'<div class="chat-message-user"><b>{sender}:</b> {text}</div>'
        else:
            chat_html += f'<div class="chat-message-bot"><b>{sender}:</b> {text}</div>'
    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)

    # Input field for new messages
    user_input = st.text_input("Type your message:", key="chat_input", placeholder="Ask about your data...")
    
    if st.button("Send Message", key="send_btn"):
        if user_input.strip():
            # Add user message to history
            st.session_state.chat_history.append(("You", user_input))
            
            # Simple intent matching (case-insensitive)
            m = user_input.lower()
            if "hello" in m or "hi" in m:
                reply = "Hello! How can I assist with your EV analysis today?"
            elif "analy" in m:
                # User wants data analysis - run if file is uploaded
                reply = analyze_file_for_chat(uploaded) if uploaded else "Please upload a file first."
            else:
                # Default help response
                reply = "Try asking about pH, temperature, anomalies, 'analyze data', or 'size'."
            
            # Add bot response to history
            st.session_state.chat_history.append(("Bot", reply))
            
            # Rerun to update UI with new messages
            st.rerun()


# -------------------------
# API Connection Check
# -------------------------
if "api_connection_checked" not in st.session_state:
    st.session_state.api_connection_checked = False
    st.session_state.api_available = False

if not st.session_state.api_connection_checked:
    with st.spinner("🔌 Connecting to backend API..."):
        st.session_state.api_available = check_api_connection()
        st.session_state.api_connection_checked = True
        
if st.session_state.api_available:
    st.success("✅ Connected to backend API at http://localhost:8000", icon="✅")
else:
    st.error("⚠️ Backend API not available. Please start the FastAPI server: `uvicorn src.api.main:app --reload`", icon="⚠️")

# -------------------------
# Tabs with Persistent State
# -------------------------
# Initialize active tab in session state if not exists
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "📊 Dashboard"

# Initialize pinned graphs storage
if "pinned_graphs" not in st.session_state:
    st.session_state.pinned_graphs = []

# Tab names for consistency
TAB_NAMES = ["📊 Dashboard", "🧪 Flow Cytometry", "⚛ Nanoparticle Tracking", "🔬 Cross-Comparison"]


def pin_graph_to_dashboard(graph_id: str, title: str, figure, source_tab: str, graph_type: str = "plotly") -> None:
    """
    Pin a graph to the Dashboard for persistent viewing.
    
    Args:
        graph_id: Unique identifier for the graph
        title: Display title for the pinned graph
        figure: The plotly figure object to pin
        source_tab: Which tab the graph came from
        graph_type: Type of graph ('plotly' or 'matplotlib')
    """
    import datetime
    
    # Check if graph is already pinned
    existing_ids = [g['id'] for g in st.session_state.pinned_graphs]
    if graph_id in existing_ids:
        st.toast(f"📌 '{title}' is already pinned!", icon="ℹ️")
        return
    
    # Add to pinned graphs
    pinned_graph = {
        'id': graph_id,
        'title': title,
        'source_tab': source_tab,
        'figure': figure,
        'graph_type': graph_type,
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    st.session_state.pinned_graphs.append(pinned_graph)
    st.toast(f"📌 Pinned '{title}' to Dashboard!", icon="✅")


def unpin_graph_from_dashboard(graph_id: str) -> None:
    """Remove a graph from the Dashboard."""
    st.session_state.pinned_graphs = [
        g for g in st.session_state.pinned_graphs if g['id'] != graph_id
    ]
    st.toast(f"📌 Graph unpinned from Dashboard", icon="🗑️")


def render_pin_button(graph_id: str, title: str, figure, source_tab: str, key_suffix: str = "") -> None:
    """
    Render a pin button for a graph.
    
    Args:
        graph_id: Unique identifier for the graph
        title: Display title for the pinned graph
        figure: The plotly figure object to pin
        source_tab: Which tab the graph came from
        key_suffix: Additional suffix for unique button key
    """
    is_pinned = graph_id in [g['id'] for g in st.session_state.pinned_graphs]
    button_label = "📌 Pinned" if is_pinned else "📌 Pin to Dashboard"
    button_type = "primary" if is_pinned else "secondary"
    
    if st.button(button_label, key=f"pin_{graph_id}_{key_suffix}", type=button_type, disabled=is_pinned):
        pin_graph_to_dashboard(graph_id, title, figure, source_tab)
        st.rerun()

# Function to handle tab change
def change_tab(tab_name: str):
    """Change the active tab and trigger rerun."""
    st.session_state.active_tab = tab_name

# Create custom tab-like navigation using columns and buttons
tab_cols = st.columns(len(TAB_NAMES))
for i, tab_name in enumerate(TAB_NAMES):
    with tab_cols[i]:
        is_active = st.session_state.active_tab == tab_name
        button_style = "primary" if is_active else "secondary"
        if st.button(
            tab_name,
            key=f"tab_btn_{i}",
            width="stretch",
            type=button_style
        ):
            st.session_state.active_tab = tab_name
            st.rerun()

st.markdown("---")


# -------------------------
# TAB 1: Dashboard + Upload + Chatbot
# -------------------------
if st.session_state.active_tab == "📊 Dashboard":
    with st.sidebar:
        st.markdown('<div class="section-header"><div class="section-icon">🧪</div><h3>Sample Database</h3></div>', unsafe_allow_html=True)
        
        # Sample list from API
        if st.session_state.get("api_available", False):
            try:
                client = get_client()
                
                # Filters
                st.markdown("**Filters**")
                filter_treatment = st.selectbox(
                    "Treatment",
                    options=["All", "CD81", "CD9", "CD63", "Isotype Control", "Other"],
                    key="filter_treatment"
                )
                
                filter_status = st.selectbox(
                    "Status",
                    options=["All", "uploaded", "processing", "completed", "failed"],
                    key="filter_status"
                )
                
                # Fetch samples
                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.button("🔄 Refresh", key="refresh_samples", width="stretch"):
                        st.session_state.samples_last_refresh = time.time()
                with col2:
                    st.caption(f"")
                
                # Get samples with filters
                treatment_filter = None if filter_treatment == "All" else filter_treatment
                status_filter = None if filter_status == "All" else filter_status
                
                samples_response = client.get_samples(
                    skip=0,
                    limit=20,
                    treatment=treatment_filter,
                    status=status_filter
                )
                
                if samples_response and samples_response.get('samples'):
                    samples = samples_response['samples']
                    st.caption(f"Showing {len(samples)} of {samples_response.get('total', len(samples))} samples")
                    
                    # Display samples as cards
                    for sample in samples:
                        with st.expander(f"📋 {sample.get('sample_id', 'Unknown')}", expanded=False):
                            st.markdown(f"**Treatment:** {sample.get('treatment', 'N/A')}")
                            st.markdown(f"**Status:** {sample.get('status', 'N/A')}")
                            st.markdown(f"**Created:** {sample.get('created_at', 'N/A')[:10] if sample.get('created_at') else 'N/A'}")
                            if st.button(f"View Details", key=f"view_{sample.get('id')}"):
                                st.session_state.selected_sample_id = sample.get('id')
                                st.rerun()
                else:
                    st.info("No samples found. Upload a file to get started.")
            
            except Exception as e:
                st.error(f"Error loading samples: {str(e)}")
                st.caption("Check if backend API is running")
        else:
            # Fallback to file list if API not available
            st.markdown('<div class="section-header"><div class="section-icon">📁</div><h3>Previous Projects</h3></div>', unsafe_allow_html=True)
            imgs = [f for f in os.listdir("images") if f.endswith(".png") or f.endswith(".parquet")]
            if imgs:
                for im in imgs:
                    st.markdown(f'<div class="project-item">📄 {im}</div>', unsafe_allow_html=True)
            else:
                st.info("No previous projects yet.")
        
        st.markdown("---")
        st.caption("Expand this sidebar from the top-left arrow.")

    st.markdown('<div class="section-header"><div class="section-icon">📈</div><h3>Generated Graphs & Chat</h3></div>', unsafe_allow_html=True)
    left_col, right_col = st.columns([3, 1])

    with left_col:
        # =====================================================
        # PINNED GRAPHS SECTION
        # =====================================================
        if st.session_state.pinned_graphs:
            st.markdown('<div class="section-header"><div class="section-icon">📌</div><h4>Pinned Graphs</h4></div>', unsafe_allow_html=True)
            st.caption(f"{len(st.session_state.pinned_graphs)} graph(s) pinned to dashboard")
            
            # Display each pinned graph
            for idx, pinned in enumerate(st.session_state.pinned_graphs):
                with st.container():
                    # Graph header with unpin button
                    header_col1, header_col2 = st.columns([4, 1])
                    with header_col1:
                        st.markdown(f"**{pinned['title']}**")
                        st.caption(f"Source: {pinned['source_tab']} | Pinned: {pinned['timestamp']}")
                    with header_col2:
                        if st.button("🗑️ Unpin", key=f"unpin_{pinned['id']}_{idx}", type="secondary"):
                            unpin_graph_from_dashboard(pinned['id'])
                            st.rerun()
                    
                    # Display the graph
                    if pinned['graph_type'] == 'plotly' and pinned['figure'] is not None:
                        try:
                            plotly_config = get_export_config() if use_interactive_plots else {}
                            st.plotly_chart(pinned['figure'], width="stretch", config=plotly_config, key=f"pinned_chart_{pinned['id']}_{idx}")
                        except Exception as e:
                            st.error(f"Error displaying pinned graph: {str(e)}")
                    
                    st.markdown("---")
            
            # Clear all pinned graphs button
            if st.button("🗑️ Clear All Pinned Graphs", key="clear_all_pinned", type="secondary"):
                st.session_state.pinned_graphs = []
                st.toast("All pinned graphs cleared!", icon="🗑️")
                st.rerun()
        
        # =====================================================
        # STATIC IMAGE GRAPHS (LEGACY)
        # =====================================================
        graph_files = [f for f in os.listdir("images") if f.endswith(".png")]
        if graph_files:
            st.markdown('<div class="section-header"><div class="section-icon">🖼️</div><h4>Saved Images</h4></div>', unsafe_allow_html=True)
            for gf in graph_files[:2]:
                st.image(os.path.join("images", gf), caption=gf, width="stretch")
        
        # Show placeholder if no graphs at all
        if not st.session_state.pinned_graphs and not graph_files:
            st.markdown("""
            <div class="glass-card" style="text-align: center; padding: 60px 40px;">
                <div style="font-size: 56px; margin-bottom: 20px;">📊</div>
                <h3 style="color: #f8fafc; margin-bottom: 12px;">No Graphs Generated Yet</h3>
                <p style="color: #94a3b8; margin: 0;">Upload a dataset and run analysis to generate visualizations</p>
                <p style="color: #64748b; margin-top: 10px; font-size: 14px;">💡 Tip: Pin graphs from other tabs using the 📌 button</p>
            </div>
            """, unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="section-header"><div class="section-icon">📥</div><h3>Upload File</h3></div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload project/dataset",
            type=["csv", "xlsx", "json", "fcs", "parquet"],
            help="Supported formats: CSV, Excel, JSON, FCS, Parquet"
        )

        # Metadata Form - Capture sample information
        if uploaded_file:
            # Check if this is a new file upload - reset metadata form if so
            if (
                "last_uploaded_file" not in st.session_state
                or st.session_state.last_uploaded_file != uploaded_file.name
            ):
                st.session_state.last_uploaded_file = uploaded_file.name
                st.session_state.metadata_submitted = False
                st.session_state.chat_history = []
                # Clear previous metadata
                for key in ["sample_id", "treatment", "concentration_ug", "preparation_method", "operator", "notes"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.info("🆕 New dataset detected. Please fill in the metadata form below.")
            
            st.markdown('<div class="section-header" style="margin-top: 20px;"><div class="section-icon">📋</div><h4>Sample Metadata</h4></div>', unsafe_allow_html=True)
            
            with st.form("metadata_form", clear_on_submit=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    sample_id = st.text_input(
                        "Sample ID *",
                        value=st.session_state.get("sample_id", ""),
                        help="Unique identifier for this sample",
                        placeholder="e.g., L5_F10_CD81"
                    )
                    
                    treatment = st.text_input(
                        "Treatment",
                        value=st.session_state.get("treatment", ""),
                        help="Treatment or antibody used",
                        placeholder="e.g., CD81, CD9, Isotype Control"
                    )
                    
                    concentration_ug = st.number_input(
                        "Concentration (μg)",
                        min_value=0.0,
                        max_value=100.0,
                        value=st.session_state.get("concentration_ug", 0.0),
                        step=0.1,
                        help="Antibody or treatment concentration in micrograms"
                    )
                
                with col2:
                    preparation_method = st.selectbox(
                        "Preparation Method",
                        options=["", "SEC", "Centrifugation", "Ultracentrifugation", "Other"],
                        index=0,
                        help="EV isolation method"
                    )
                    
                    operator = st.text_input(
                        "Operator",
                        value=st.session_state.get("operator", ""),
                        help="Person who performed the experiment",
                        placeholder="Enter your name"
                    )
                
                notes = st.text_area(
                    "Notes",
                    value=st.session_state.get("notes", ""),
                    help="Additional observations or comments",
                    placeholder="Enter any relevant notes about this sample...",
                    height=80
                )
                
                submit_metadata = st.form_submit_button("✅ Save Metadata & Process File", width="stretch")
                
                if submit_metadata:
                    # Validation
                    errors = []
                    if not sample_id or not sample_id.strip():  # type: ignore[union-attr]
                        errors.append("❌ Sample ID is required")
                    if concentration_ug < 0:
                        errors.append("❌ Concentration cannot be negative")
                    
                    if errors:
                        for error in errors:
                            st.error(error)
                    else:
                        # Store in session state
                        st.session_state.sample_id = sample_id
                        st.session_state.treatment = treatment
                        st.session_state.concentration_ug = concentration_ug
                        st.session_state.preparation_method = preparation_method
                        st.session_state.operator = operator
                        st.session_state.notes = notes
                        st.session_state.metadata_submitted = True
                        st.success("✅ Metadata saved successfully!")
        
        if uploaded_file and st.session_state.get("metadata_submitted", False):
            # Process file via API
            if st.session_state.api_available:
                with st.spinner("📤 Uploading file to backend API..."):
                    try:
                        # Save uploaded file temporarily
                        temp_path = save_uploadedfile_to_path(uploaded_file, dest_folder="uploads")
                        
                        # Determine file type and upload via API
                        file_ext = uploaded_file.name.split('.')[-1].lower()  # type: ignore[union-attr]
                        
                        client = get_client()
                        
                        if file_ext == 'fcs':
                            # Upload FCS file with metadata
                            response = client.upload_fcs(
                                file_path=temp_path,
                                sample_id=st.session_state.sample_id,
                                treatment=st.session_state.treatment or "",
                                concentration_ug=st.session_state.concentration_ug,
                                preparation_method=st.session_state.preparation_method or "",
                                operator=st.session_state.operator or "",
                                notes=st.session_state.notes or ""
                            )
                        elif file_ext == 'nta' or 'nta' in str(uploaded_file.name).lower():  # type: ignore[union-attr]
                            # Upload NTA file with metadata
                            response = client.upload_nta(
                                file_path=temp_path,
                                sample_id=st.session_state.sample_id,
                                treatment=st.session_state.treatment or "",
                                concentration_ug=st.session_state.concentration_ug,
                                preparation_method=st.session_state.preparation_method or "",
                                operator=st.session_state.operator or "",
                                notes=st.session_state.notes or ""
                            )
                        else:
                            st.warning(f"⚠️ Unsupported file type for API upload: {file_ext}. Processing locally instead.")
                            # Fallback to local processing
                            parquet_path, df_loaded = convert_anyfile_to_parquet(uploaded_file)
                            if df_loaded is not None:
                                st.dataframe(df_loaded.head(), width='stretch')  # type: ignore[union-attr]
                            chatbot_ui(parquet_path if parquet_path else uploaded_file)
                            response = None
                        
                        if response:
                            # Get database ID (numeric primary key) for API calls
                            uploaded_db_id = response.get('id')
                            uploaded_sample_id = response.get('sample_id')
                            
                            # If no database ID returned, use sample_id as fallback
                            if uploaded_db_id is None:
                                st.warning(f"⚠️ No database ID returned, using sample_id as fallback")
                                uploaded_db_id = uploaded_sample_id
                            
                            st.success(f"✅ File uploaded successfully! Sample ID: {uploaded_sample_id}")
                            
                            # Display sample metadata directly from upload response
                            st.markdown("**📋 Sample Information:**")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Sample ID", response.get('sample_id', 'N/A'))
                                st.metric("Treatment", response.get('treatment', 'N/A') or 'N/A')
                            with col2:
                                st.metric("Concentration (μg)", response.get('concentration_ug', 'N/A') or 'N/A')
                                st.metric("Preparation", response.get('preparation_method', 'N/A') or 'N/A')
                            with col3:
                                st.metric("Operator", response.get('operator', 'N/A') or 'N/A')
                                st.metric("Status", response.get('status', 'N/A'))
                            
                            if response.get('notes'):
                                st.info(f"📝 Notes: {response['notes']}")
                            
                            # Display parsed FCS results if available
                            if response.get('fcs_results'):
                                fcs_data = response['fcs_results']
                                st.markdown("**🔬 FCS Analysis Results (Parsed by Professional Parser):**")
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("Total Events", f"{fcs_data.get('event_count', 0):,}")
                                    if fcs_data.get('mean_fsc'):
                                        st.metric("Mean FSC", f"{fcs_data['mean_fsc']:.1f}")
                                with col2:
                                    st.metric("Channels", len(fcs_data.get('channels', [])))
                                    if fcs_data.get('mean_ssc'):
                                        st.metric("Mean SSC", f"{fcs_data['mean_ssc']:.1f}")
                                
                                # Show available channels
                                if fcs_data.get('channels'):
                                    with st.expander("📊 Available Channels"):
                                        st.write(", ".join(fcs_data['channels'][:15]))
                                        if len(fcs_data['channels']) > 15:
                                            st.caption(f"... and {len(fcs_data['channels']) - 15} more channels")
                            else:
                                st.info("ℹ️ File uploaded. Parsing in progress...")
                            
                            # Show upload confirmation
                            st.info(f"ℹ️ Processing job ID: {response.get('job_id', 'N/A')}")
                            st.info(f"ℹ️ File size: {response.get('file_size_mb', 0):.2f} MB")
                            
                            # Store database ID for chatbot context
                            st.session_state.current_sample_id = uploaded_db_id
                            st.session_state.current_sample_name = uploaded_sample_id
                            chatbot_ui(uploaded_db_id)
                    
                    except Exception as e:
                        st.error(f"❌ Error uploading file: {str(e)}")
                        st.info("ℹ️ Falling back to local processing...")
                        # Fallback to local processing
                        parquet_path, df_loaded = convert_anyfile_to_parquet(uploaded_file)
                        if df_loaded is not None:
                            st.dataframe(df_loaded.head(), width='stretch')  # type: ignore[union-attr]
                        chatbot_ui(parquet_path if parquet_path else uploaded_file)
            else:
                # API not available - use local processing
                st.warning("⚠️ Backend API not available. Processing file locally...")
                parquet_path, df_loaded = convert_anyfile_to_parquet(uploaded_file)

                if parquet_path is None and df_loaded is None:
                    st.error("Failed to convert uploaded file.")
                else:
                    try:
                        target = os.path.join("images", os.path.basename(parquet_path)) if parquet_path else None
                        if parquet_path and os.path.exists(parquet_path):
                            os.replace(parquet_path, target)
                            saved_path = target
                        else:
                            if df_loaded is not None and use_pyarrow:
                                target = os.path.join(
                                    "images",
                                    os.path.basename(str(uploaded_file.name).rsplit('.', 1)[0]) + ".parquet"  # type: ignore[union-attr]
                                )
                                pq.write_table(pa.Table.from_pandas(df_loaded), target)  # type: ignore[name-defined]
                                saved_path = target
                            else:
                                target = os.path.join(
                                    "images",
                                    os.path.basename(str(uploaded_file.name).rsplit('.', 1)[0]) + ".csv"  # type: ignore[union-attr]
                                )
                                if df_loaded is not None:
                                    df_loaded.to_csv(target, index=False)  # type: ignore[union-attr]
                                saved_path = target
                    except Exception:
                        saved_path = None

                    st.markdown("**Data Preview:**")
                    if df_loaded is not None:
                        st.dataframe(df_loaded.head(), width='stretch')  # type: ignore[union-attr]

                    if saved_path:
                        st.success(f"Saved: {os.path.basename(saved_path)}")

                    chatbot_ui(saved_path if saved_path else uploaded_file)
        
        elif uploaded_file and not st.session_state.get("metadata_submitted", False):
            st.info("👆 Please fill in the sample metadata form above and click 'Save Metadata & Process File' to continue.")

        else:
            st.markdown("""
            <div class="glass-card" style="text-align: center; padding: 40px;">
                <div style="font-size: 42px; margin-bottom: 16px;">📤</div>
                <p style="color: #94a3b8; margin: 0;">Drag & drop or click to upload</p>
            </div>
            """, unsafe_allow_html=True)
            chatbot_ui(None)

# -------------------------
# TAB 2: Particle Size Analysis
# -------------------------
if st.session_state.active_tab == "🧪 Flow Cytometry":
    with st.sidebar:
        st.markdown('<div class="section-header"><div class="section-icon">⚙️</div><h3>Analysis Settings</h3></div>', unsafe_allow_html=True)
        lambda_nm = st.number_input("Laser wavelength (nm)", value=488.0, step=1.0)
        n_particle = st.number_input("Particle refractive index", value=1.38, step=0.01)
        n_medium = st.number_input("Medium refractive index", value=1.33, step=0.01)
        fsc_range = st.slider("FSC angle range (deg)", 0, 30, (1, 15), step=1)
        ssc_range = st.slider("SSC angle range (deg)", 30, 180, (85, 95), step=1)
        # Extended search range (Dec 5, 2025 - Parvesh requirement)
        # Search wider than display to avoid clamping artifacts
        d_min, d_max = st.slider("Diameter search range (nm)", 10, 500, (30, 220), step=1)
        st.caption("⚠️ Search range extended to 30-220nm to prevent histogram spikes. Display range: 40-200nm")
        n_points = st.number_input("Diameter points (resolution)", value=200, min_value=20, max_value=2000, step=10)
        st.markdown("---")
        
        # =====================================================================
        # USER-DEFINED SIZE RANGES (Nov 27, 2025 - Jaganmohan requirement)
        # Let users choose their own size categories dynamically
        # =====================================================================
        st.markdown('<div class="section-header"><div class="section-icon">📊</div><h4>Size Range Analysis</h4></div>', unsafe_allow_html=True)
        st.caption("Define custom size ranges to count particles. Different scientific applications need different segmentation.")
        
        # Initialize session state for size ranges
        if "custom_size_ranges" not in st.session_state:
            # Default ranges based on common EV categorizations
            st.session_state.custom_size_ranges = [
                {"name": "Small EVs", "min": 30, "max": 100},
                {"name": "Medium EVs", "min": 100, "max": 150},
                {"name": "Large EVs", "min": 150, "max": 200},
            ]
        
        # Show current ranges
        st.markdown("**Current Size Ranges:**")
        ranges_to_remove = []
        for i, r in enumerate(st.session_state.custom_size_ranges):
            col_name, col_range, col_del = st.columns([2, 2, 1])
            with col_name:
                st.text(f"{r['name']}")
            with col_range:
                st.text(f"{r['min']}-{r['max']} nm")
            with col_del:
                if st.button("🗑️", key=f"del_range_{i}", help="Remove this range"):
                    ranges_to_remove.append(i)
        
        # Remove marked ranges
        for idx in sorted(ranges_to_remove, reverse=True):
            st.session_state.custom_size_ranges.pop(idx)
            st.rerun()
        
        # Add new range section
        with st.expander("➕ Add New Size Range", expanded=False):
            new_range_name = st.text_input("Range Name", value="", placeholder="e.g., Small vesicles", key="new_range_name")
            new_range_cols = st.columns(2)
            with new_range_cols[0]:
                new_range_min = st.number_input("Min Size (nm)", min_value=0, max_value=500, value=30, step=5, key="new_range_min")
            with new_range_cols[1]:
                new_range_max = st.number_input("Max Size (nm)", min_value=0, max_value=500, value=100, step=5, key="new_range_max")
            
            if st.button("Add Range", key="add_size_range", width="stretch"):
                if new_range_name.strip() and new_range_min < new_range_max:
                    st.session_state.custom_size_ranges.append({
                        "name": new_range_name.strip(),
                        "min": int(new_range_min),
                        "max": int(new_range_max)
                    })
                    st.success(f"Added: {new_range_name} ({new_range_min}-{new_range_max} nm)")
                    st.rerun()
                elif new_range_min >= new_range_max:
                    st.error("Min size must be less than max size")
                else:
                    st.error("Please enter a range name")
        
        # Quick preset buttons
        st.markdown("**Quick Presets:**")
        
        # EV Standard Categories (3 categories - Meeting Dec 3, 2025)
        if st.button("📊 EV Standard (<50, 50-200, >200)", key="preset_ev_standard", width="stretch", help="Standard EV categorization: Small EVs/Exomeres, Exosomes, Microvesicles"):
            st.session_state.custom_size_ranges = [
                {"name": "Small EVs (<50nm)", "min": 0, "max": 50},
                {"name": "Exosomes (50-200nm)", "min": 50, "max": 200},
                {"name": "Microvesicles (>200nm)", "min": 200, "max": 1000},
            ]
            st.rerun()
        
        preset_cols = st.columns(2)
        with preset_cols[0]:
            if st.button("30-100, 100-150", key="preset_1", width="stretch", help="Standard EV categorization"):
                st.session_state.custom_size_ranges = [
                    {"name": "Small EVs (30-100)", "min": 30, "max": 100},
                    {"name": "Medium EVs (100-150)", "min": 100, "max": 150},
                ]
                st.rerun()
        with preset_cols[1]:
            if st.button("40-80, 80-120", key="preset_2", width="stretch", help="Exosome-focused ranges"):
                st.session_state.custom_size_ranges = [
                    {"name": "Exosomes (40-80)", "min": 40, "max": 80},
                    {"name": "Small MVs (80-120)", "min": 80, "max": 120},
                ]
                st.rerun()
        
        st.markdown("---")
        st.markdown("**Channels & Cleaning**")
        st.caption("Select columns after uploading the file.")
        ignore_negative = st.checkbox("Ignore negative -H values (replace with NaN)", value=True)
        drop_na = st.checkbox("Drop rows missing FSC/SSC after cleaning", value=True)
        
        # =========================================================================
        # ANOMALY DETECTION SETTINGS
        # =========================================================================
        st.markdown("---")
        st.markdown("**🔍 Anomaly Detection**")
        # Initialize default values for anomaly detection parameters
        anomaly_method = "Z-Score"
        zscore_threshold = 3.0
        iqr_factor = 1.5
        highlight_anomalies = False
        
        if use_anomaly_detection:
            enable_anomaly_detection = st.checkbox(
                "Enable Anomaly Detection", 
                value=False,
                help="Detect outliers and anomalies in your data using statistical methods"
            )
            
            if enable_anomaly_detection:
                anomaly_method = st.selectbox(
                    "Detection Method",
                    ["Z-Score", "IQR", "Both"],
                    index=0,
                    help="Z-Score: Statistical outliers (3σ). IQR: Interquartile range method."
                )
                
                if anomaly_method in ["Z-Score", "Both"]:
                    zscore_threshold = st.slider(
                        "Z-Score Threshold (σ)",
                        min_value=2.0,
                        max_value=5.0,
                        value=3.0,
                        step=0.5,
                        help="Events beyond this many standard deviations are flagged as anomalies"
                    )
                else:
                    zscore_threshold = 3.0
                
                if anomaly_method in ["IQR", "Both"]:
                    iqr_factor = st.slider(
                        "IQR Factor",
                        min_value=1.0,
                        max_value=3.0,
                        value=1.5,
                        step=0.25,
                        help="Multiplier for IQR-based outlier detection"
                    )
                else:
                    iqr_factor = 1.5
                
                highlight_anomalies = st.checkbox(
                    "Highlight anomalies on scatter plots",
                    value=True,
                    help="Show anomalies as red markers on plots"
                )
        else:
            st.warning("Anomaly detection module not available")
            enable_anomaly_detection = False
        
        # =========================================================================
        # INTERACTIVE PLOTS SETTINGS
        # =========================================================================
        st.markdown("---")
        st.markdown("**📊 Visualization Settings**")
        if use_interactive_plots:
            use_plotly = st.checkbox(
                "Use Interactive Plots (Plotly)", 
                value=True,
                help="Enable interactive graphs with hover, zoom, and pan. Disable for static matplotlib plots."
            )
            if use_plotly:
                st.caption("✨ Hover over points for details, zoom with scroll, pan by dragging")
        else:
            st.warning("Interactive plots not available - using static matplotlib")
            use_plotly = False
        
        st.markdown("---")
        if use_pymiescatt:
            st.success("PyMieScatt detected - full Mie used")
        else:
            st.warning("PyMieScatt not found - running fallback (approximate)")

    st.markdown('<div class="section-header"><div class="section-icon">🔬</div><h3>Particle Size vs Scatter Intensity Analysis</h3></div>', unsafe_allow_html=True)
    st.markdown("Upload FCS/Parquet/CSV/XLSX file with height channels (VFSC-H, VSSC1-H, etc.) to analyze particle size distribution using Mie scattering theory.")

    file2 = st.file_uploader("Upload dataset for analysis", type=["csv", "xlsx", "json", "fcs", "parquet"], key="analysis_upload")

    # =========================================================================
    # FCS BEST PRACTICES GUIDE - Flow Cytometry Tab
    # Mirrors NTA best practices pattern for consistency
    # =========================================================================
    if file2:
        st.markdown(
            "<div class='animated-section'>"
            "<h4 style='color:#00b4d8;'>🔼 🧠 Flow Cytometry Best Practices</h4>"
            "</div>",
            unsafe_allow_html=True
        )

        with st.expander("🧪 Sample Preparation", expanded=False):
            st.markdown(
                """
                <ul style="line-height:1.8;">
                    <li><b>Dilution:</b> Use <b>1:100 to 1:1000</b> for concentrated samples to avoid swarm detection.</li>
                    <li><b>Temperature:</b> Record and maintain at <b>4°C or RT</b> consistently throughout analysis.</li>
                    <li><b>pH:</b> Maintain between <b>7.2-7.4</b> for most EV samples (PBS buffer recommended).</li>
                    <li><b>Filtration:</b> Filter samples through <b>0.22 μm filter</b> to remove aggregates.</li>
                    <li><b>Fresh Samples:</b> Analyze within <b>4 hours</b> of preparation for best results.</li>
                </ul>
                """,
                unsafe_allow_html=True
            )

        with st.expander("⚙️ Acquisition Settings", expanded=False):
            st.markdown(
                """
                <ul style="line-height:1.8;">
                    <li><b>FSC Threshold:</b> Set above noise floor at approximately <b>200-500</b>.</li>
                    <li><b>Flow Rate:</b> Use <b>Low (10 μL/min)</b> for better resolution of small particles.</li>
                    <li><b>Events:</b> Collect minimum <b>10,000 events</b> per sample for statistical validity.</li>
                    <li><b>Time:</b> Acquire for <b>60-120 seconds</b> to ensure representative sampling.</li>
                    <li><b>Voltage Settings:</b> Optimize PMT voltages using reference beads first.</li>
                </ul>
                """,
                unsafe_allow_html=True
            )

        with st.expander("🔬 Controls & Calibration", expanded=False):
            st.markdown(
                """
                <ul style="line-height:1.8;">
                    <li><b>Isotype Control:</b> Always run <b>matched isotype</b> at same concentration as test antibody.</li>
                    <li><b>FMO Controls:</b> Use <b>Fluorescence Minus One</b> controls for accurate gating.</li>
                    <li><b>Unstained Sample:</b> Run for <b>autofluorescence</b> baseline reference.</li>
                    <li><b>Reference Beads:</b> Run <b>polystyrene calibration beads</b> (100-500nm) daily.</li>
                    <li><b>Water Wash:</b> Should show <b>&lt;100 events</b> if system is clean.</li>
                    <li><b>Blank Media:</b> Characterize background from buffer/media alone.</li>
                </ul>
                """,
                unsafe_allow_html=True
            )

        with st.expander("⚠️ Common Issues & Troubleshooting", expanded=False):
            st.markdown(
                """
                <ul style="line-height:1.8;">
                    <li><b>Swarm Detection:</b> If events cluster abnormally, <b>dilute sample further</b>.</li>
                    <li><b>High Background:</b> Check <b>laser alignment</b> and <b>clean flow cell</b> with bleach.</li>
                    <li><b>Aggregates:</b> Filter through <b>0.22 μm</b> or sonicate briefly (30 sec, low power).</li>
                    <li><b>Inconsistent Counts:</b> Verify <b>stable flow rate</b> - check for air bubbles.</li>
                    <li><b>Dim Signals:</b> Increase PMT voltage or check <b>antibody concentration</b>.</li>
                    <li><b>Carryover:</b> Run <b>3 water washes</b> between different samples.</li>
                </ul>
                """,
                unsafe_allow_html=True
            )

        with st.expander("📏 Size Standards & Reference", expanded=False):
            st.markdown(
                """
                <ul style="line-height:1.8;">
                    <li><b>Polystyrene Beads:</b> Use 100nm, 200nm, 500nm beads for size calibration.</li>
                    <li><b>Silica Beads:</b> Better refractive index match for biological vesicles.</li>
                    <li><b>Expected EV Sizes:</b>
                        <ul>
                            <li>🔹 <b>Exosomes:</b> 30-150 nm</li>
                            <li>🔹 <b>Microvesicles:</b> 100-1000 nm</li>
                            <li>🔹 <b>Apoptotic Bodies:</b> 500-5000 nm</li>
                        </ul>
                    </li>
                    <li><b>Refractive Index:</b> EVs typically have RI of <b>1.37-1.42</b> (lipid bilayer).</li>
                </ul>
                """,
                unsafe_allow_html=True
            )

        st.success("📁 File uploaded successfully! Complete experiment parameters below.")
    else:
        st.info("📤 Upload an FCS/data file to view Flow Cytometry best practices.")

    if "fsc_col_selected" not in st.session_state:
        st.session_state["fsc_col_selected"] = None
    if "ssc_col_selected" not in st.session_state:
        st.session_state["ssc_col_selected"] = None
    if "analysis_df" not in st.session_state:
        st.session_state["analysis_df"] = None
    
    # =========================================================================
    # EXPERIMENT PARAMETERS POPUP - Flow Cytometry Tab
    # Captures: Temperature, Substrate, Volume, pH
    # These parameters are NOT in FCS metadata, so we need user input.
    # This data will be used for AI-based best practices comparison (future)
    # =========================================================================
    if "fcs_experiment_params" not in st.session_state:
        st.session_state["fcs_experiment_params"] = {}
    if "fcs_params_submitted" not in st.session_state:
        st.session_state["fcs_params_submitted"] = False
    
    # Detect new file upload - reset experiment params form
    if file2:
        current_file_name = getattr(file2, 'name', str(file2))
        if st.session_state.get("fcs_last_uploaded_file") != current_file_name:
            st.session_state["fcs_last_uploaded_file"] = current_file_name
            st.session_state["fcs_params_submitted"] = False
            st.session_state["fcs_experiment_params"] = {}
        
        # Show experiment parameters form if not yet submitted
        if not st.session_state.get("fcs_params_submitted", False):
            st.markdown("""
            <div class="glass-card" style="border: 2px solid #00b4d8; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                    <div style="font-size: 28px;">🧪</div>
                    <div>
                        <h4 style="margin: 0; color: #f8fafc;">Experiment Parameters Required</h4>
                        <p style="margin: 0; color: #94a3b8; font-size: 13px;">
                            FCS files don't contain these parameters. Please enter them for analysis.
                        </p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("fcs_experiment_params_form", clear_on_submit=False):
                st.markdown("#### 🌡️ Experimental Conditions")
                st.caption("These parameters are essential for AI-based best practices comparison.")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    exp_temperature = st.number_input(
                        "🌡️ Temperature (°C) *",
                        min_value=-20.0,
                        max_value=100.0,
                        value=st.session_state.get("exp_temperature", 25.0),
                        step=0.5,
                        help="Sample temperature during measurement (typical: 4°C for storage, 20-25°C for room temp)"
                    )
                    
                    exp_substrate = st.selectbox(
                        "🧫 Substrate/Buffer *",
                        options=[
                            "",
                            "PBS (pH 7.4)",
                            "HEPES Buffer",
                            "Tris-HCl Buffer",
                            "Cell Culture Media (DMEM)",
                            "Cell Culture Media (RPMI)",
                            "Saline (0.9% NaCl)",
                            "HPLC Grade Water",
                            "Other"
                        ],
                        index=0,
                        help="Buffer or substrate used for sample preparation"
                    )
                    
                    if exp_substrate == "Other":
                        exp_substrate_other = st.text_input(
                            "Specify Substrate",
                            placeholder="Enter custom substrate name"
                        )
                
                with col2:
                    exp_volume = st.number_input(
                        "💧 Sample Volume (μL) *",
                        min_value=0.0,
                        max_value=10000.0,
                        value=st.session_state.get("exp_volume", 50.0),
                        step=5.0,
                        help="Volume of sample loaded for analysis (typical: 20-100 μL)"
                    )
                    
                    exp_ph = st.number_input(
                        "🧪 pH *",
                        min_value=0.0,
                        max_value=14.0,
                        value=st.session_state.get("exp_ph", 7.4),
                        step=0.1,
                        help="pH of the sample/buffer (physiological: 7.35-7.45)"
                    )
                
                st.markdown("---")
                st.markdown("#### 📋 Additional Information (Optional)")
                
                col3, col4 = st.columns(2)
                with col3:
                    exp_incubation_time = st.number_input(
                        "⏱️ Incubation Time (min)",
                        min_value=0,
                        max_value=1440,
                        value=st.session_state.get("exp_incubation_time", 0),
                        step=5,
                        help="Time sample was incubated before measurement"
                    )
                    
                    exp_staining_protocol = st.selectbox(
                        "🎨 Staining Protocol",
                        options=["", "Direct Staining", "Indirect Staining", "Intracellular Staining", "Surface Staining", "None"],
                        index=0,
                        help="Type of staining protocol used"
                    )
                
                with col4:
                    exp_dilution_factor = st.text_input(
                        "🔬 Dilution Factor",
                        value=st.session_state.get("exp_dilution_factor", ""),
                        placeholder="e.g., 1:100, 1:1000",
                        help="Dilution ratio if sample was diluted"
                    )
                    
                    exp_instrument_settings = st.text_area(
                        "⚙️ Special Instrument Settings",
                        value=st.session_state.get("exp_instrument_settings", ""),
                        placeholder="e.g., Flow rate: Medium, Threshold: 200",
                        height=68,
                        help="Any non-standard instrument settings used"
                    )
                
                exp_notes = st.text_area(
                    "📝 Experiment Notes",
                    value=st.session_state.get("exp_notes", ""),
                    placeholder="Any additional observations or notes about this experiment...",
                    height=80
                )
                
                submit_params = st.form_submit_button("✅ Save Experiment Parameters & Continue", width="stretch")
                
                if submit_params:
                    # Validation
                    errors = []
                    if not exp_substrate:
                        errors.append("❌ Substrate/Buffer is required")
                    if exp_volume <= 0:
                        errors.append("❌ Volume must be greater than 0")
                    if exp_ph < 0 or exp_ph > 14:
                        errors.append("❌ pH must be between 0 and 14")
                    
                    if errors:
                        for error in errors:
                            st.error(error)
                    else:
                        # Store experiment parameters
                        substrate_final = exp_substrate_other if exp_substrate == "Other" and 'exp_substrate_other' in dir() else exp_substrate
                        
                        st.session_state["fcs_experiment_params"] = {
                            "temperature_celsius": exp_temperature,
                            "substrate": substrate_final,
                            "volume_ul": exp_volume,
                            "ph": exp_ph,
                            "incubation_time_min": exp_incubation_time,
                            "staining_protocol": exp_staining_protocol,
                            "dilution_factor": exp_dilution_factor,
                            "instrument_settings": exp_instrument_settings,
                            "notes": exp_notes,
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        st.session_state["fcs_params_submitted"] = True
                        st.success("✅ Experiment parameters saved! Proceeding with analysis...")
                        st.rerun()
            
            # Show info about why these parameters matter
            with st.expander("ℹ️ Why are these parameters important?", expanded=False):
                st.markdown("""
                **These experimental parameters are crucial for:**
                
                🔬 **Quality Control**
                - Temperature affects EV stability and aggregation
                - pH influences surface marker binding efficiency
                - Volume determines event concentration and statistics
                
                🤖 **Future AI Analysis**
                - Compare your parameters with best practices
                - Detect potential issues (e.g., pH too low for antibody binding)
                - Recommend optimal conditions for your sample type
                
                📊 **Reproducibility**
                - Track experimental conditions across runs
                - Identify batch-to-batch variations
                - Enable meta-analysis of multiple experiments
                
                *Note: NTA files typically contain this information in metadata, but FCS files do not.*
                """)
            
            # Stop here until parameters are submitted
            st.info("👆 Please fill in the experiment parameters above to continue with the analysis.")
            st.stop()
        
        else:
            # Show saved parameters in a compact summary
            params = st.session_state.get("fcs_experiment_params", {})
            if params:
                with st.expander("📋 Experiment Parameters (saved)", expanded=False):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("🌡️ Temperature", f"{params.get('temperature_celsius', 'N/A')}°C")
                    with col2:
                        st.metric("🧫 Substrate", params.get('substrate', 'N/A')[:15] + "..." if len(str(params.get('substrate', ''))) > 15 else params.get('substrate', 'N/A'))
                    with col3:
                        st.metric("💧 Volume", f"{params.get('volume_ul', 'N/A')} μL")
                    with col4:
                        st.metric("🧪 pH", params.get('ph', 'N/A'))
                    
                    if st.button("🔄 Edit Parameters", key="edit_fcs_params"):
                        st.session_state["fcs_params_submitted"] = False
                        st.rerun()

    if file2:
        # Option to upload via API
        if st.session_state.get("api_available", False):
            with st.expander("📋 Sample Metadata (Optional - for API upload)", expanded=False):
                st.caption("Fill this form to upload file to backend API and track in database")
                
                col1, col2 = st.columns(2)
                with col1:
                    tab2_sample_id = st.text_input(
                        "Sample ID",
                        value=st.session_state.get("tab2_sample_id", ""),
                        key="tab2_sample_id_input",
                        placeholder="e.g., L5_F10_CD81"
                    )
                    tab2_treatment = st.text_input(
                        "Treatment",
                        value=st.session_state.get("tab2_treatment", ""),
                        key="tab2_treatment_input",
                        placeholder="e.g., CD81, CD9"
                    )
                with col2:
                    tab2_concentration = st.number_input(
                        "Concentration (μg)",
                        min_value=0.0,
                        value=st.session_state.get("tab2_concentration", 0.0),
                        key="tab2_concentration_input"
                    )
                    tab2_method = st.selectbox(
                        "Preparation Method",
                        options=["", "SEC", "Centrifugation", "Ultracentrifugation"],
                        key="tab2_method_input"
                    )
                
                if st.button("📤 Upload to API & Analyze", key="tab2_api_upload"):
                    if tab2_sample_id and tab2_sample_id.strip():
                        try:
                            client = get_client()
                            
                            # Save file temporarily
                            temp_path = save_uploadedfile_to_path(file2, dest_folder="uploads")
                            
                            # Upload to API
                            with st.spinner("📤 Uploading to backend..."):
                                file_ext = str(file2.name).lower().split('.')[-1]  # type: ignore[union-attr]
                                
                                if file_ext == 'fcs':
                                    # Include experiment parameters from the popup form
                                    exp_params = st.session_state.get("fcs_experiment_params", {})
                                    response = client.upload_fcs(
                                        file_path=temp_path,
                                        sample_id=tab2_sample_id,
                                        treatment=tab2_treatment,
                                        concentration_ug=tab2_concentration,
                                        preparation_method=tab2_method,
                                        operator=st.session_state.get("operator", ""),
                                        notes=f"Tab 2 Analysis - {lambda_nm}nm laser",
                                        experiment_params=exp_params  # NEW: Include experiment parameters
                                    )
                                else:
                                    response = client.upload_nta(
                                        file_path=temp_path,
                                        sample_id=tab2_sample_id,
                                        treatment=tab2_treatment,
                                        concentration_ug=tab2_concentration,
                                        preparation_method=tab2_method,
                                        operator=st.session_state.get("operator", ""),
                                        notes=f"Tab 2 Analysis"
                                    )
                                
                                st.success(f"✅ Uploaded to API: Sample ID = {response['sample_id']}")
                                st.session_state.tab2_uploaded_sample_id = response['sample_id']
                        except Exception as e:
                            st.error(f"❌ API upload failed: {str(e)}")
                            st.info("Continuing with local analysis...")
                    else:
                        st.error("Sample ID is required for API upload")
        
        df_raw, parquet_path = load_dataframe_from_uploaded(file2)
        if df_raw is None:
            st.error("Failed to read uploaded file.")
        else:
            # =====================================================================
            # VSSC_max Column Creation (Dec 5, 2025 - Parvesh requirement)
            # Create explicit VSSC_max column with row-wise maximum for optimal
            # per-event SSC channel selection (more transparent than median-based)
            # =====================================================================
            vssc_candidates = [c for c in df_raw.columns if 'vssc' in str(c).lower() and str(c).strip().endswith('-H')]
            if len(vssc_candidates) >= 2:
                # Find VSSC-1-H and VSSC-2-H (or similar naming)
                vssc1 = next((c for c in vssc_candidates if '1' in str(c)), None)
                vssc2 = next((c for c in vssc_candidates if '2' in str(c)), None)
                
                if vssc1 and vssc2:
                    # Create VSSC_max column: row-wise maximum
                    df_raw['VSSC_max'] = df_raw[[vssc1, vssc2]].max(axis=1)
                    st.success(f"✅ Created **VSSC_max** column (max of {vssc1} and {vssc2} per event)")
                    st.info("💡 VSSC_max uses per-event optimization for better accuracy")
            
            st.markdown("**Preview of uploaded data:**")
            st.dataframe(df_raw.head(), width='stretch')

            height_cols = [c for c in df_raw.columns if str(c).strip().endswith("-H")]
            all_cols = list(df_raw.columns)
            if not height_cols:
                st.error("No '-H' height columns found in dataset. Please provide data with channels like VFSC-H, VSSC1-H, etc.")
            else:
                fsc_candidates = [c for c in height_cols if "fsc" in str(c).lower()]
                if len(fsc_candidates) > 1:
                    try:
                        medians = {c: pd.to_numeric(df_raw[c], errors="coerce").median() for c in fsc_candidates}
                        fsc_choice = max(medians, key=medians.get)  # type: ignore[arg-type]
                        st.success(f"Auto-selected FSC column: **{fsc_choice}** (highest median).")
                    except Exception:
                        fsc_choice = fsc_candidates[0]
                elif len(fsc_candidates) == 1:
                    fsc_choice = fsc_candidates[0]
                    st.info(f"Detected single FSC column: {fsc_choice}")
                else:
                    fsc_choice = height_cols[0]
                    st.info(f"No FSC-specific column found; using {fsc_choice} as FSC.")

                ssc_candidates = [c for c in height_cols if "ssc" in str(c).lower()]
                
                # Prioritize VSSC_max if available (Dec 5, 2025 improvement)
                if 'VSSC_max' in all_cols:
                    ssc_choice = 'VSSC_max'
                    st.success(f"Auto-selected SSC column: **{ssc_choice}** (optimal per-event selection)")
                elif len(ssc_candidates) > 1:
                    try:
                        medians = {c: pd.to_numeric(df_raw[c], errors="coerce").median() for c in ssc_candidates}
                        ssc_choice = max(medians, key=medians.get)  # type: ignore[arg-type]
                        st.success(f"Auto-selected SSC column: **{ssc_choice}** (highest median).")
                    except Exception:
                        ssc_choice = ssc_candidates[0]
                elif len(ssc_candidates) == 1:
                    ssc_choice = ssc_candidates[0]
                    st.info(f"Detected single SSC column: {ssc_choice}")
                else:
                    ssc_choice = height_cols[1] if len(height_cols) > 1 else height_cols[0]
                    st.info(f"No SSC-specific column found; using {ssc_choice} as SSC.")

                col1, col2 = st.columns(2)
                with col1:
                    fsc_choice_ui = st.selectbox("FSC column (auto-selected)", options=all_cols, index=all_cols.index(fsc_choice) if fsc_choice in all_cols else 0)
                with col2:
                    ssc_choice_ui = st.selectbox("SSC column (auto-selected)", options=all_cols, index=all_cols.index(ssc_choice) if ssc_choice in all_cols else 0)

                if st.button("Apply Selection", key="apply_selection"):
                    st.session_state["fsc_col_selected"] = fsc_choice_ui
                    st.session_state["ssc_col_selected"] = ssc_choice_ui
                    st.session_state["analysis_df"] = df_raw.copy()
                    st.success(f"Selection applied: FSC='{fsc_choice_ui}' | SSC='{ssc_choice_ui}'")

    else:
        st.markdown("""
        <div class="glass-card" style="text-align: center; padding: 50px;">
            <div style="font-size: 56px; margin-bottom: 20px;">🧬</div>
            <h3 style="color: #f8fafc; margin-bottom: 12px;">Upload Dataset</h3>
            <p style="color: #94a3b8; margin: 0;">Select FSC/SSC columns and run particle size analysis</p>
        </div>
        """, unsafe_allow_html=True)

    # =========================================================================
    # LIVE THEORETICAL CURVE PREVIEW (in collapsible expander)
    # Updates in real-time as user adjusts sidebar parameters
    # Only shown as a reference - NOT actual data
    # =========================================================================
    with st.expander("📐 Preview Theoretical Model (No Data Required)", expanded=False):
        st.warning("⚠️ **This is NOT experimental data!** This is a mathematical model (Mie Scattering Theory) showing the expected FSC/SSC ratio for different particle sizes based on your sidebar settings. Upload a file and run analysis to see your actual data.")
        
        st.markdown("#### Theoretical FSC/SSC Ratio Curve")
        st.caption("Adjust sidebar parameters to see how the theoretical curve changes. This helps you understand the physics before analyzing real data.")
        
        # Build theoretical lookup with current settings
        preview_diameters = np.linspace(int(d_min), int(d_max), int(n_points))
        _, preview_ratios = build_theoretical_lookup(lambda_nm, n_particle, n_medium, fsc_range, ssc_range, preview_diameters)
        
        # Get Plotly config for export buttons
        plotly_config = get_export_config() if use_interactive_plots else {}
        
        # Use interactive Plotly if available
        if use_interactive_plots:
            fig_preview = create_theoretical_curve(
                preview_diameters,
                preview_ratios,
                title="Theoretical FSC/SSC Ratio Curve (Mie Scattering Model)"
            )
            st.plotly_chart(fig_preview, width="stretch", config=plotly_config)
        else:
            # Fallback to matplotlib
            fig_preview_mpl, ax_preview = plt.subplots(figsize=(10, 4))
            fig_preview_mpl.patch.set_facecolor('#111827')  # type: ignore[attr-defined]
            ax_preview.set_facecolor('#111827')
            ax_preview.plot(preview_diameters, preview_ratios, color='#f72585', linewidth=2.5)
            ax_preview.set_xlabel("Diameter (nm)", color='#f8fafc', fontsize=12)
            ax_preview.set_ylabel("FSC/SSC Ratio", color='#f8fafc', fontsize=12)
            ax_preview.set_title("Theoretical FSC/SSC Ratio Curve (Mie Scattering Model)", color='#f8fafc', fontsize=14, fontweight='bold')
            ax_preview.tick_params(colors='#94a3b8')
            for spine in ax_preview.spines.values():
                spine.set_color('#374151')
            ax_preview.grid(True, alpha=0.2, color='#374151')
            st.pyplot(fig_preview_mpl)
            plt.close()
        
        # Show current parameter summary
        st.markdown("**Current Model Parameters:**")
        param_cols = st.columns(5)
        param_cols[0].metric("Wavelength", f"{lambda_nm:.0f} nm")
        param_cols[1].metric("n (particle)", f"{n_particle:.2f}")
        param_cols[2].metric("n (medium)", f"{n_medium:.2f}")
        param_cols[3].metric("Size Range", f"{d_min}-{d_max} nm")
        param_cols[4].metric("Resolution", f"{n_points} pts")

    st.markdown("---")
    run_col1, run_col2, run_col3 = st.columns([1, 2, 1])
    with run_col1:
        run_analysis = st.button("Run Analysis", key="run_analysis", width="stretch")
    with run_col2:
        st.write("")
    with run_col3:
        # Reset Tab button - clears cached analysis results
        if st.button("🔄 Reset Tab", key="reset_fcs_tab", width="stretch", help="Clear cached analysis and start fresh"):
            keys_to_clear = [
                'fcs_analysis_complete', 'fcs_results_df', 'fcs_diameters', 
                'fcs_theoretical_ratios', 'fcs_analysis_params', 'fcs_anomaly_results',
                'fcs_anomaly_mask', 'analysis_df', 'fcs_col_selected', 'ssc_col_selected'
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("Tab reset! Upload a new file or re-run analysis.")
            st.rerun()

    # Check if we have cached analysis results to display
    has_cached_results = st.session_state.get('fcs_analysis_complete', False)
    
    if run_analysis:
        if st.session_state.get("analysis_df") is None:
            st.error("No file applied. Upload file and click 'Apply Selection' first.")
        else:
            df = st.session_state["analysis_df"].copy()
            fsc_col = st.session_state["fsc_col_selected"]
            ssc_col = st.session_state["ssc_col_selected"]

            if fsc_col not in df.columns or ssc_col not in df.columns:
                st.error("Selected columns not present in the uploaded file. Re-apply selection.")
            else:
                with st.spinner("Running particle size analysis..."):
                    st.info(f"Running analysis with FSC='{fsc_col}' and SSC='{ssc_col}'")

                    if ignore_negative:
                        cols_to_clean = [c for c in df.columns if str(c).strip().endswith("-H")]
                        for c in cols_to_clean:
                            df[c] = pd.to_numeric(df[c], errors="coerce")  # type: ignore[assignment]
                            df.loc[df[c] < 0, c] = np.nan  # type: ignore[call-overload]

                    if drop_na:
                        before = len(df)
                        df = df.dropna(subset=[fsc_col, ssc_col])
                        after = len(df)
                        st.write(f"Dropped {before - after} rows missing FSC/SSC. {after} rows remain.")

                    df[fsc_col] = pd.to_numeric(df[fsc_col], errors="coerce")
                    df[ssc_col] = pd.to_numeric(df[ssc_col], errors="coerce")
                    
                    fsc_values = df[fsc_col].values
                    ssc_values = df[ssc_col].values
                    
                    # Vectorized division with proper handling of zeros and NaNs
                    with np.errstate(divide='ignore', invalid='ignore'):
                        measured_ratio = np.where(
                            (np.isfinite(fsc_values)) & (np.isfinite(ssc_values)) & (ssc_values != 0),
                            fsc_values / ssc_values,
                            np.nan
                        )
                    df["measured_ratio"] = measured_ratio

                    diameters = np.linspace(int(d_min), int(d_max), int(n_points))
                    angles, theoretical_ratios = build_theoretical_lookup(lambda_nm, n_particle, n_medium, fsc_range, ssc_range, diameters)

                    total = len(df)
                    t0 = time.time()
                    
                    # Show progress for building lookup (if not cached)
                    prog = st.progress(0, text="Building theoretical lookup...")
                    prog.progress(30, text="Computing particle sizes (vectorized)...")
                    
                    # Vectorized estimation - MUCH faster than row-by-row
                    estimated_diameters, matched_ratios, matched_indices = estimate_diameters_vectorized(
                        df["measured_ratio"].values,
                        theoretical_ratios,
                        diameters
                    )
                    
                    df["estimated_diameter_nm"] = estimated_diameters
                    df["matched_theoretical_ratio"] = matched_ratios
                    df["matched_idx"] = matched_indices
                    
                    prog.progress(100, text="Complete!")
                    elapsed = time.time() - t0

                    st.success(f"Processing complete in {elapsed:.1f}s - processed {total} rows.")

                    # =====================================================================
                    # SIZE RANGE FILTERING (Dec 5, 2025 - Critical Fix)
                    # Filter particles instead of clamping to prevent histogram spikes
                    # Calculate statistics ONLY on filtered data for accuracy
                    # =====================================================================
                    DIAMETER_SEARCH_MIN = float(d_min)  # Extended range (30-220nm typical)
                    DIAMETER_SEARCH_MAX = float(d_max)
                    DIAMETER_DISPLAY_MIN = 40.0  # Display range (40-200nm typical)
                    DIAMETER_DISPLAY_MAX = 200.0
                    
                    # Get all calculated diameters
                    diameters_raw = df['estimated_diameter_nm'].values
                    
                    # Filter valid particles (exclude outliers completely - don't clamp!)
                    valid_mask = (diameters_raw > DIAMETER_SEARCH_MIN) & (diameters_raw < DIAMETER_SEARCH_MAX)
                    diameters_filtered = diameters_raw[valid_mask]
                    
                    # Display subset for visualization
                    display_mask = (diameters_filtered >= DIAMETER_DISPLAY_MIN) & (diameters_filtered <= DIAMETER_DISPLAY_MAX)
                    diameters_display = diameters_filtered[display_mask]
                    
                    # Count particles by category
                    count_total = len(diameters_filtered)
                    count_display = len(diameters_display)
                    count_below = np.sum(diameters_filtered < DIAMETER_DISPLAY_MIN)
                    count_above = np.sum(diameters_filtered > DIAMETER_DISPLAY_MAX)
                    count_excluded = total - len(diameters_filtered)
                    
                    # Calculate statistics ONLY on filtered data (not clamped)
                    median_val = np.median(diameters_filtered) if len(diameters_filtered) > 0 else 0
                    d50_val = np.percentile(diameters_filtered, 50) if len(diameters_filtered) > 0 else 0
                    d10_val = np.percentile(diameters_filtered, 10) if len(diameters_filtered) > 0 else 0
                    d90_val = np.percentile(diameters_filtered, 90) if len(diameters_filtered) > 0 else 0
                    std_val = np.std(diameters_filtered) if len(diameters_filtered) > 0 else 0
                    
                    # Store filtered data for downstream use
                    df['diameter_filtered'] = np.where(valid_mask, df['estimated_diameter_nm'], np.nan)

                    # Display stat cards - Median is primary metric per Surya's feedback (Dec 3, 2025)
                    # Mean is kept for modeling but Median is preferred for display
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.markdown(f"""
                        <div class="stat-card">
                            <div class="stat-value">{median_val:.1f}</div>
                            <div class="stat-label">Median Size (nm)</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"""
                        <div class="stat-card">
                            <div class="stat-value">{d50_val:.1f}</div>
                            <div class="stat-label">D50 (nm)</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col3:
                        st.markdown(f"""
                        <div class="stat-card">
                            <div class="stat-value">{std_val:.1f}</div>
                            <div class="stat-label">Std Dev (nm)</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col4:
                        st.markdown(f"""
                        <div class="stat-card">
                            <div class="stat-value">{count_total:,}</div>
                            <div class="stat-label">Valid Particles</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Show filtering information
                    if count_excluded > 0 or count_below > 0 or count_above > 0:
                        st.info(f"📊 **Filtering Summary:** {count_total:,} valid particles ({count_total/total*100:.1f}%) | "
                               f"Excluded: {count_excluded:,} outside search range | "
                               f"Display range ({DIAMETER_DISPLAY_MIN:.0f}-{DIAMETER_DISPLAY_MAX:.0f}nm): {count_display:,} particles | "
                               f"Below display: {count_below:,} | Above display: {count_above:,}")

                    # =====================================================================
                    # USER-DEFINED SIZE RANGE DISTRIBUTION (Nov 27, 2025 requirement)
                    # Shows particle counts for each user-defined size range
                    # Updated Dec 5, 2025: Use filtered data for accurate counts
                    # =====================================================================
                    if st.session_state.get("custom_size_ranges"):
                        st.markdown("---")
                        st.markdown("### 📊 Size Range Distribution")
                        st.caption("Particle counts based on your custom size ranges defined in the sidebar.")
                        
                        # Use filtered data (not raw) for accurate statistics
                        size_data = pd.Series(diameters_filtered)
                        
                        # Calculate counts for each range
                        range_counts = []
                        for r in st.session_state.custom_size_ranges:
                            count = len(size_data[(size_data >= r['min']) & (size_data <= r['max'])])
                            pct = (count / len(size_data) * 100) if len(size_data) > 0 else 0
                            range_counts.append({
                                "name": r['name'],
                                "range": f"{r['min']}-{r['max']} nm",
                                "count": count,
                                "percentage": pct
                            })
                        
                        # Display as stat cards (dynamic number of columns)
                        num_ranges = len(range_counts)
                        if num_ranges > 0:
                            cols = st.columns(min(num_ranges, 4))  # Max 4 columns per row
                            for i, rc in enumerate(range_counts):
                                col_idx = i % 4
                                with cols[col_idx]:
                                    st.markdown(f"""
                                    <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                                        <div class="stat-value" style="color: white;">{rc['count']:,}</div>
                                        <div class="stat-label" style="color: rgba(255,255,255,0.9);">{rc['name']}</div>
                                        <div style="font-size: 0.8rem; color: rgba(255,255,255,0.7);">{rc['range']} • {rc['percentage']:.1f}%</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                        
                        # Create summary table
                        range_df = pd.DataFrame(range_counts)
                        
                        # Add total row
                        total_counted = sum(rc['count'] for rc in range_counts)
                        uncategorized = len(size_data) - total_counted if total_counted <= len(size_data) else 0
                        
                        # Show a bar chart of size distributions
                        if len(range_counts) > 1:
                            st.markdown("**Distribution by Range:**")
                            chart_data = pd.DataFrame({
                                'Range': [rc['name'] for rc in range_counts],
                                'Count': [rc['count'] for rc in range_counts]
                            })
                            st.bar_chart(chart_data.set_index('Range'))
                        
                        # Show detailed table
                        with st.expander("📋 Detailed Size Range Statistics", expanded=False):
                            range_df_display = range_df.copy()
                            range_df_display.columns = ['Range Name', 'Size Range', 'Particle Count', 'Percentage (%)']
                            range_df_display['Percentage (%)'] = range_df_display['Percentage (%)'].apply(lambda x: f"{x:.2f}%")
                            st.dataframe(range_df_display, width="stretch", hide_index=True)
                            
                            if uncategorized > 0:
                                st.info(f"⚠️ {uncategorized:,} particles ({uncategorized/len(size_data)*100:.1f}%) fall outside defined ranges")
                            
                            # Size range coverage info
                            min_defined = min(r['min'] for r in st.session_state.custom_size_ranges)
                            max_defined = max(r['max'] for r in st.session_state.custom_size_ranges)
                            st.caption(f"Defined ranges cover: {min_defined}-{max_defined} nm | Data range: {size_data.min():.1f}-{size_data.max():.1f} nm")

                    # Results preview
                    preview_cols = [c for c in ["Event/EVs Sl.No", fsc_col, ssc_col, "measured_ratio", "estimated_diameter_nm"] if c in df.columns]
                    st.markdown("**Results Preview:**")
                    st.dataframe(df[preview_cols].head(200), width='stretch')

                    # Save results
                    results_parquet = os.path.join("uploads", "analysis_results.parquet")
                    try:
                        if use_pyarrow:
                            pq.write_table(pa.Table.from_pandas(df), results_parquet)  # type: ignore[name-defined]
                        else:
                            results_parquet = results_parquet.replace(".parquet", ".csv")
                            df.to_csv(results_parquet, index=False)
                    except Exception:
                        results_parquet = os.path.join("uploads", "analysis_results.csv")
                        df.to_csv(results_parquet, index=False)

                    # Download button
                    csv_buffer = io.StringIO()
                    df.to_csv(csv_buffer, index=False)
                    csv_bytes = csv_buffer.getvalue().encode()
                    st.download_button("Download Results CSV", data=csv_bytes, file_name="estimated_sizes.csv", mime="text/csv")

                    measured = df.dropna(subset=["estimated_diameter_nm", "measured_ratio"])

                    # =========================================================================
                    # VISUALIZATION SECTION - Interactive (Plotly) or Static (Matplotlib)
                    # =========================================================================
                    
                    # Get Plotly export config (used throughout)
                    plotly_config = get_export_config() if use_interactive_plots else {}
                    
                    if use_plotly and use_interactive_plots:
                        # =====================================================================
                        # PLOTLY INTERACTIVE PLOTS
                        # =====================================================================
                        st.markdown("---")
                        st.markdown("### 📊 Interactive Visualizations")
                        st.caption("💡 Tip: Hover for details • Scroll to zoom • Drag to pan • Double-click to reset")
                        
                        # Plot 1: Theoretical vs Measured (Plotly)
                        fig1_plotly = create_theoretical_vs_measured_plot(
                            diameters=diameters,
                            theoretical_ratios=theoretical_ratios,
                            measured_data=measured,
                            diameter_col="estimated_diameter_nm",
                            ratio_col="measured_ratio",
                            title="Theoretical vs Measured FSC/SSC Ratio"
                        )
                        st.plotly_chart(fig1_plotly, width="stretch", config=plotly_config)
                        render_pin_button("fcs_theoretical_vs_measured", "FCS: Theoretical vs Measured Ratio", fig1_plotly, "🧪 Flow Cytometry", "fcs1")
                        
                        # Plot 2: Size Distribution Histogram (Plotly)
                        size_ranges_for_plot = st.session_state.get("custom_size_ranges", None)
                        fig2_plotly = create_size_distribution_histogram(
                            data=df,
                            size_col="estimated_diameter_nm",
                            nbins=50,
                            title="Particle Size Distribution",
                            show_size_ranges=bool(size_ranges_for_plot),
                            size_ranges=size_ranges_for_plot
                        )
                        st.plotly_chart(fig2_plotly, width="stretch", config=plotly_config)
                        render_pin_button("fcs_size_distribution", "FCS: Particle Size Distribution", fig2_plotly, "🧪 Flow Cytometry", "fcs2")
                        
                        # Save static version for export (optional - requires kaleido)
                        try:
                            plot_path = os.path.join("images", "particle_size_histogram.png")
                            fig2_plotly.write_image(plot_path, width=1200, height=600, scale=2)
                        except (ValueError, ImportError):
                            pass  # Kaleido not installed - skip image export
                        
                    else:
                        # =====================================================================
                        # MATPLOTLIB STATIC PLOTS (Fallback)
                        # =====================================================================
                        plt.style.use('dark_background')
                        
                        # Plot 1: Theoretical vs Measured
                        fig1, ax1 = plt.subplots(figsize=(10, 5))
                        fig1.patch.set_facecolor('#111827')  # type: ignore[attr-defined]
                        ax1.set_facecolor('#111827')
                        ax1.plot(diameters, theoretical_ratios, color='#00b4d8', linewidth=2, label="Theoretical ratio")
                        if not measured.empty:
                            ax1.scatter(measured["estimated_diameter_nm"], measured["measured_ratio"], s=20, alpha=0.6, c='#f72585', label="Measured events")
                        ax1.set_xlabel("Diameter (nm)", color='#f8fafc', fontsize=12)
                        ax1.set_ylabel("FSC/SSC ratio", color='#f8fafc', fontsize=12)
                        ax1.legend(facecolor='#1f2937', edgecolor='#374151', labelcolor='#f8fafc')
                        ax1.tick_params(colors='#94a3b8')
                        for spine in ax1.spines.values():
                            spine.set_color('#374151')
                        ax1.grid(True, alpha=0.2, color='#374151')
                        st.pyplot(fig1)
                        plt.close()

                        # Plot 2: Histogram
                        fig2, ax2 = plt.subplots(figsize=(10, 5))
                        fig2.patch.set_facecolor('#111827')  # type: ignore[attr-defined]
                        ax2.set_facecolor('#111827')
                        ax2.hist(measured["estimated_diameter_nm"].dropna(), bins=40, color='#00b4d8', edgecolor='#0096c7', alpha=0.85)
                        ax2.set_xlabel("Estimated diameter (nm)", color='#f8fafc', fontsize=12)
                        ax2.set_ylabel("Counts", color='#f8fafc', fontsize=12)
                        ax2.set_title("Particle Size Distribution", color='#f8fafc', fontsize=14, fontweight='bold')
                        ax2.tick_params(colors='#94a3b8')
                        for spine in ax2.spines.values():
                            spine.set_color('#374151')
                        ax2.grid(True, alpha=0.2, color='#374151')

                        plot_path = os.path.join("images", "particle_size_histogram.png")
                        fig2.savefig(plot_path, dpi=150, bbox_inches='tight', facecolor='#111827')
                        st.pyplot(fig2)
                        plt.close()

                    # =========================================================================
                    # ANOMALY DETECTION ANALYSIS
                    # =========================================================================
                    anomaly_mask = None
                    anomaly_results = {}
                    
                    if enable_anomaly_detection and use_anomaly_detection:
                        st.markdown("---")
                        st.markdown("### 🔍 Anomaly Detection Results")
                        
                        try:
                            detector = AnomalyDetector()
                            
                            # Prepare data for anomaly detection
                            analysis_cols = [fsc_col, ssc_col]
                            if "estimated_diameter_nm" in df.columns:
                                analysis_cols.append("estimated_diameter_nm")
                            
                            df_for_anomaly = df[analysis_cols].copy()
                            
                            # Run selected detection methods
                            if anomaly_method in ["Z-Score", "Both"]:
                                df_zscore = detector.detect_outliers_zscore(
                                    df_for_anomaly,
                                    channels=analysis_cols,
                                    threshold=zscore_threshold
                                )
                                zscore_anomalies = df_zscore['is_outlier'].sum()
                                anomaly_results['zscore'] = {
                                    'count': int(zscore_anomalies),
                                    'percentage': float(zscore_anomalies / len(df) * 100),
                                    'mask': df_zscore['is_outlier'].values
                                }
                            
                            if anomaly_method in ["IQR", "Both"]:
                                df_iqr = detector.detect_outliers_iqr(
                                    df_for_anomaly,
                                    channels=analysis_cols,
                                    factor=iqr_factor
                                )
                                iqr_anomalies = df_iqr['is_outlier_iqr'].sum()
                                anomaly_results['iqr'] = {
                                    'count': int(iqr_anomalies),
                                    'percentage': float(iqr_anomalies / len(df) * 100),
                                    'mask': df_iqr['is_outlier_iqr'].values
                                }
                            
                            # Combine masks for visualization
                            if anomaly_method == "Both":
                                anomaly_mask = anomaly_results['zscore']['mask'] | anomaly_results['iqr']['mask']
                                combined_count = anomaly_mask.sum()
                            elif anomaly_method == "Z-Score":
                                anomaly_mask = anomaly_results['zscore']['mask']
                                combined_count = anomaly_results['zscore']['count']
                            else:  # IQR
                                anomaly_mask = anomaly_results['iqr']['mask']
                                combined_count = anomaly_results['iqr']['count']
                            
                            # Display anomaly statistics
                            anom_cols = st.columns(4)
                            
                            with anom_cols[0]:
                                st.markdown(f"""
                                <div class="stat-card" style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);">
                                    <div class="stat-value" style="color: white;">{combined_count:,}</div>
                                    <div class="stat-label" style="color: rgba(255,255,255,0.9);">Anomalies Detected</div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            with anom_cols[1]:
                                pct = (combined_count / len(df)) * 100
                                st.markdown(f"""
                                <div class="stat-card" style="background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);">
                                    <div class="stat-value" style="color: white;">{pct:.2f}%</div>
                                    <div class="stat-label" style="color: rgba(255,255,255,0.9);">Anomaly Rate</div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            with anom_cols[2]:
                                normal_count = len(df) - combined_count
                                st.markdown(f"""
                                <div class="stat-card" style="background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);">
                                    <div class="stat-value" style="color: white;">{normal_count:,}</div>
                                    <div class="stat-label" style="color: rgba(255,255,255,0.9);">Normal Events</div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            with anom_cols[3]:
                                method_display = anomaly_method
                                st.markdown(f"""
                                <div class="stat-card" style="background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);">
                                    <div class="stat-value" style="color: white; font-size: 1.2rem;">{method_display}</div>
                                    <div class="stat-label" style="color: rgba(255,255,255,0.9);">Detection Method</div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Detailed breakdown
                            with st.expander("📊 Detailed Anomaly Breakdown", expanded=False):
                                if 'zscore' in anomaly_results:
                                    st.markdown(f"**Z-Score Method** (threshold: {zscore_threshold}σ)")
                                    st.write(f"- Anomalies: {anomaly_results['zscore']['count']:,} ({anomaly_results['zscore']['percentage']:.2f}%)")
                                
                                if 'iqr' in anomaly_results:
                                    st.markdown(f"**IQR Method** (factor: {iqr_factor})")
                                    st.write(f"- Anomalies: {anomaly_results['iqr']['count']:,} ({anomaly_results['iqr']['percentage']:.2f}%)")
                                
                                if anomaly_method == "Both":
                                    st.markdown("**Combined (Union)**")
                                    st.write(f"- Total unique anomalies: {combined_count:,}")
                                
                                # Show anomaly size statistics if available
                                if "estimated_diameter_nm" in df.columns and anomaly_mask is not None:
                                    anomaly_sizes = df.loc[anomaly_mask, "estimated_diameter_nm"].dropna()
                                    normal_sizes = df.loc[~anomaly_mask, "estimated_diameter_nm"].dropna()
                                    
                                    if len(anomaly_sizes) > 0:
                                        st.markdown("---")
                                        st.markdown("**Size Distribution of Anomalies:**")
                                        size_comparison = pd.DataFrame({
                                            'Metric': ['Mean (nm)', 'Median (nm)', 'Std Dev (nm)', 'Min (nm)', 'Max (nm)'],
                                            'Anomalies': [
                                                f"{anomaly_sizes.mean():.1f}",
                                                f"{anomaly_sizes.median():.1f}",
                                                f"{anomaly_sizes.std():.1f}",
                                                f"{anomaly_sizes.min():.1f}",
                                                f"{anomaly_sizes.max():.1f}"
                                            ],
                                            'Normal': [
                                                f"{normal_sizes.mean():.1f}",
                                                f"{normal_sizes.median():.1f}",
                                                f"{normal_sizes.std():.1f}",
                                                f"{normal_sizes.min():.1f}",
                                                f"{normal_sizes.max():.1f}"
                                            ]
                                        })
                                        st.dataframe(size_comparison, hide_index=True, width="stretch")
                            
                            # Add anomaly flag to dataframe
                            df['is_anomaly'] = anomaly_mask
                            
                            # Interpretation message
                            if pct < 1:
                                st.success(f"✅ Low anomaly rate ({pct:.2f}%) - Data quality looks good!")
                            elif pct < 5:
                                st.info(f"ℹ️ Moderate anomaly rate ({pct:.2f}%) - Review flagged events")
                            else:
                                st.warning(f"⚠️ High anomaly rate ({pct:.2f}%) - Consider investigating sample quality or acquisition settings")
                            
                        except Exception as e:
                            st.error(f"Anomaly detection failed: {str(e)}")
                            anomaly_mask = None

                    # Plot 3: FSC vs SSC scatter (with anomaly highlighting)
                    if fsc_col in df.columns and ssc_col in df.columns:
                        if use_plotly and use_interactive_plots:
                            # Plotly interactive version
                            fig3_plotly = create_fsc_ssc_scatter(
                                data=df,
                                fsc_col=fsc_col,
                                ssc_col=ssc_col,
                                anomaly_mask=anomaly_mask,
                                highlight_anomalies=highlight_anomalies,
                                title="FSC vs SSC Scatter Plot"
                            )
                            st.plotly_chart(fig3_plotly, width="stretch", config=plotly_config)
                            render_pin_button("fcs_fsc_ssc_scatter", "FCS: FSC vs SSC Scatter", fig3_plotly, "🧪 Flow Cytometry", "fcs3")
                        else:
                            # Matplotlib static version
                            fig3, ax3 = plt.subplots(figsize=(8, 6))
                            fig3.patch.set_facecolor('#111827')  # type: ignore[attr-defined]
                            ax3.set_facecolor('#111827')
                            
                            # Plot normal points
                            if anomaly_mask is not None and highlight_anomalies:
                                normal_mask = ~anomaly_mask
                                ax3.scatter(
                                    df.loc[normal_mask, fsc_col], 
                                    df.loc[normal_mask, ssc_col], 
                                    s=8, alpha=0.5, c='#7c3aed', label='Normal'
                                )
                                # Plot anomalies on top with different color
                                ax3.scatter(
                                    df.loc[anomaly_mask, fsc_col], 
                                    df.loc[anomaly_mask, ssc_col], 
                                    s=15, alpha=0.8, c='#ef4444', marker='x', 
                                    linewidths=1, label=f'Anomalies ({anomaly_mask.sum():,})'
                                )
                                ax3.legend(facecolor='#1f2937', edgecolor='#374151', labelcolor='#f8fafc', loc='upper right')
                                title_suffix = " (Anomalies Highlighted)"
                            else:
                                ax3.scatter(df[fsc_col], df[ssc_col], s=8, alpha=0.5, c='#7c3aed')
                                title_suffix = ""
                            
                            ax3.set_xlabel(fsc_col, color='#f8fafc', fontsize=12)
                            ax3.set_ylabel(ssc_col, color='#f8fafc', fontsize=12)
                            ax3.set_title(f"FSC vs SSC{title_suffix}", color='#f8fafc', fontsize=14, fontweight='bold')
                            ax3.tick_params(colors='#94a3b8')
                            for spine in ax3.spines.values():
                                spine.set_color('#374151')
                            ax3.grid(True, alpha=0.2, color='#374151')
                            st.pyplot(fig3)
                            plt.close()

                    # Plot 4: Diameter vs SSC (with anomaly highlighting)
                    if "estimated_diameter_nm" in df.columns and ssc_col in df.columns:
                        if use_plotly and use_interactive_plots:
                            # Plotly interactive version
                            fig4_plotly = create_size_vs_scatter_plot(
                                data=df,
                                scatter_col=ssc_col,
                                size_col="estimated_diameter_nm",
                                anomaly_mask=anomaly_mask,
                                highlight_anomalies=highlight_anomalies,
                                title=f"Estimated Diameter vs {ssc_col}"
                            )
                            st.plotly_chart(fig4_plotly, width="stretch", config=plotly_config)
                            render_pin_button("fcs_diameter_vs_ssc", f"FCS: Diameter vs {ssc_col}", fig4_plotly, "🧪 Flow Cytometry", "fcs4")
                        else:
                            # Matplotlib static version
                            fig4, ax4 = plt.subplots(figsize=(10, 5))
                            fig4.patch.set_facecolor('#111827')  # type: ignore[attr-defined]
                            ax4.set_facecolor('#111827')
                            
                            # Plot with anomaly highlighting if enabled
                            if anomaly_mask is not None and highlight_anomalies:
                                normal_mask = ~anomaly_mask
                                ax4.scatter(
                                    df.loc[normal_mask, "estimated_diameter_nm"], 
                                    df.loc[normal_mask, ssc_col], 
                                    s=8, alpha=0.5, c='#10b981', label='Normal'
                                )
                                ax4.scatter(
                                    df.loc[anomaly_mask, "estimated_diameter_nm"], 
                                    df.loc[anomaly_mask, ssc_col], 
                                    s=15, alpha=0.8, c='#ef4444', marker='x', 
                                    linewidths=1, label=f'Anomalies ({anomaly_mask.sum():,})'
                                )
                                ax4.legend(facecolor='#1f2937', edgecolor='#374151', labelcolor='#f8fafc', loc='upper right')
                                title_suffix = " (Anomalies Highlighted)"
                            else:
                                ax4.scatter(df["estimated_diameter_nm"], df[ssc_col], s=8, alpha=0.5, c='#10b981')
                                title_suffix = ""
                            
                            ax4.set_xlabel("Estimated Diameter (nm)", color='#f8fafc', fontsize=12)
                            ax4.set_ylabel(ssc_col, color='#f8fafc', fontsize=12)
                            ax4.set_title(f"Estimated Diameter vs {ssc_col}{title_suffix}", color='#f8fafc', fontsize=14, fontweight='bold')
                            ax4.tick_params(colors='#94a3b8')
                            for spine in ax4.spines.values():
                                spine.set_color('#374151')
                            ax4.grid(True, alpha=0.2, color='#374151')
                            st.pyplot(fig4)
                            plt.close()
                    
                    # Interactive Dashboard (Plotly only)
                    if use_plotly and use_interactive_plots:
                        with st.expander("📊 Full Analysis Dashboard", expanded=False):
                            st.caption("Combined view of all analyses in one interactive panel")
                            dashboard_fig = create_analysis_dashboard(
                                data=df,
                                fsc_col=fsc_col,
                                ssc_col=ssc_col,
                                size_col="estimated_diameter_nm",
                                anomaly_mask=anomaly_mask,
                                highlight_anomalies=highlight_anomalies
                            )
                            st.plotly_chart(dashboard_fig, width="stretch", config=plotly_config)
                            render_pin_button("fcs_analysis_dashboard", "FCS: Full Analysis Dashboard", dashboard_fig, "🧪 Flow Cytometry", "fcs_dash")

                    # Download anomaly data if available
                    if anomaly_mask is not None and anomaly_mask.sum() > 0:
                        st.markdown("---")
                        st.markdown("### 📥 Export Anomaly Data")
                        
                        export_cols = st.columns(2)
                        with export_cols[0]:
                            # Export anomalies only
                            anomaly_df = df[anomaly_mask].copy()
                            csv_anomalies = anomaly_df.to_csv(index=False).encode()
                            st.download_button(
                                "⬇️ Download Anomalies Only",
                                data=csv_anomalies,
                                file_name="anomalies_only.csv",
                                mime="text/csv",
                                help=f"Download {anomaly_mask.sum():,} anomalous events"
                            )
                        
                        with export_cols[1]:
                            # Export with anomaly flag
                            csv_with_flag = df.to_csv(index=False).encode()
                            st.download_button(
                                "⬇️ Download All Data (with anomaly flag)",
                                data=csv_with_flag,
                                file_name="data_with_anomaly_flags.csv",
                                mime="text/csv",
                                help="Download all data with 'is_anomaly' column"
                            )

                    st.success(f"Histogram saved to: {plot_path}")

                    # =========================================================================
                    # CACHE ALL ANALYSIS RESULTS FOR TAB PERSISTENCE
                    # =========================================================================
                    st.session_state["last_analysis_df"] = df.copy()
                    st.session_state["last_theoretical"] = {"diameters": diameters, "ratios": theoretical_ratios}
                    
                    # Store complete analysis state for tab persistence
                    st.session_state['fcs_analysis_complete'] = True
                    st.session_state['fcs_results_df'] = df.copy()
                    st.session_state['fcs_diameters'] = diameters
                    st.session_state['fcs_theoretical_ratios'] = theoretical_ratios
                    st.session_state['fcs_analysis_params'] = {
                        'fsc_col': fsc_col,
                        'ssc_col': ssc_col,
                        'lambda_nm': lambda_nm,
                        'n_particle': n_particle,
                        'n_medium': n_medium,
                        'fsc_range': fsc_range,
                        'ssc_range': ssc_range,
                        'd_min': d_min,
                        'd_max': d_max,
                        'use_plotly': use_plotly if use_interactive_plots else False,
                        'enable_anomaly': enable_anomaly_detection if use_anomaly_detection else False,
                        'anomaly_method': anomaly_method if use_anomaly_detection else None,
                        'zscore_threshold': zscore_threshold if use_anomaly_detection else None,
                        'iqr_factor': iqr_factor if use_anomaly_detection else None
                    }
                    if anomaly_mask is not None:
                        st.session_state['fcs_anomaly_mask'] = anomaly_mask
                        st.session_state['fcs_anomaly_results'] = anomaly_results
                    
                    # Store FCS data for cross-comparison
                    st.session_state['fcs_data'] = df.copy()
                    fcs_name = getattr(file2, 'name', None) if file2 else None
                    st.session_state['fcs_filename'] = fcs_name if fcs_name else 'FCS Sample'
                    st.session_state['fcs_fsc_col'] = fsc_col
                    st.session_state['fcs_ssc_col'] = ssc_col

    # =========================================================================
    # DISPLAY CACHED RESULTS WHEN TAB IS REVISITED
    # =========================================================================
    elif has_cached_results and not run_analysis:
        # User has cached results and is viewing the tab (not running new analysis)
        st.markdown("---")
        st.markdown("""
        <div style='background: linear-gradient(135deg, #1e3a5f 0%, #1e293b 100%); 
                    padding: 15px 20px; border-radius: 10px; margin-bottom: 20px;
                    border-left: 4px solid #00b4d8;'>
            <div style='display: flex; align-items: center; gap: 10px;'>
                <span style='font-size: 24px;'>📊</span>
                <div>
                    <h4 style='margin: 0; color: #00b4d8;'>Cached Analysis Results</h4>
                    <p style='margin: 0; color: #94a3b8; font-size: 13px;'>
                        Results from your previous analysis are displayed below. Click "Run Analysis" to re-analyze or "Reset Tab" to start fresh.
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Retrieve cached data
        df = st.session_state.get('fcs_results_df')
        diameters = st.session_state.get('fcs_diameters')
        theoretical_ratios = st.session_state.get('fcs_theoretical_ratios')
        params = st.session_state.get('fcs_analysis_params', {})
        anomaly_mask = st.session_state.get('fcs_anomaly_mask')
        anomaly_results = st.session_state.get('fcs_anomaly_results', {})
        
        fsc_col = params.get('fsc_col', 'FSC')
        ssc_col = params.get('ssc_col', 'SSC')
        use_plotly = params.get('use_plotly', False)
        enable_anomaly_detection_cached = params.get('enable_anomaly', False)
        
        if df is not None and len(df) > 0:
            # Display stat cards - Median is primary metric per Surya's feedback (Dec 3, 2025)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                median_val = df['estimated_diameter_nm'].median()
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{median_val:.1f}</div>
                    <div class="stat-label">Median Size (nm)</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                d50_val = np.percentile(df['estimated_diameter_nm'].dropna(), 50)
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{d50_val:.1f}</div>
                    <div class="stat-label">D50 (nm)</div>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                std_val = df['estimated_diameter_nm'].std()
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{std_val:.1f}</div>
                    <div class="stat-label">Std Dev (nm)</div>
                </div>
                """, unsafe_allow_html=True)
            with col4:
                total = len(df)
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{total:,}</div>
                    <div class="stat-label">Total Particles</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Size Range Distribution (if defined)
            if st.session_state.get("custom_size_ranges"):
                st.markdown("---")
                st.markdown("### 📊 Size Range Distribution")
                
                size_data = df['estimated_diameter_nm'].dropna()
                range_counts = []
                for r in st.session_state.custom_size_ranges:
                    count = len(size_data[(size_data >= r['min']) & (size_data <= r['max'])])
                    pct = (count / len(size_data) * 100) if len(size_data) > 0 else 0
                    range_counts.append({"name": r['name'], "range": f"{r['min']}-{r['max']} nm", "count": count, "percentage": pct})
                
                num_ranges = len(range_counts)
                if num_ranges > 0:
                    cols = st.columns(min(num_ranges, 4))
                    for i, rc in enumerate(range_counts):
                        with cols[i % 4]:
                            st.markdown(f"""
                            <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                                <div class="stat-value" style="color: white;">{rc['count']:,}</div>
                                <div class="stat-label" style="color: rgba(255,255,255,0.9);">{rc['name']}</div>
                                <div style="font-size: 0.8rem; color: rgba(255,255,255,0.7);">{rc['range']} • {rc['percentage']:.1f}%</div>
                            </div>
                            """, unsafe_allow_html=True)

            # Results preview
            preview_cols = [c for c in ["Event/EVs Sl.No", fsc_col, ssc_col, "measured_ratio", "estimated_diameter_nm"] if c in df.columns]
            st.markdown("**Results Preview:**")
            st.dataframe(df[preview_cols].head(200), width="stretch")
            
            # Download button
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_bytes = csv_buffer.getvalue().encode()
            st.download_button("Download Results CSV", data=csv_bytes, file_name="estimated_sizes.csv", mime="text/csv")
            
            measured = df.dropna(subset=["estimated_diameter_nm", "measured_ratio"])
            
            # Visualizations
            plotly_config = get_export_config() if use_interactive_plots else {}
            
            if use_plotly and use_interactive_plots:
                st.markdown("---")
                st.markdown("### 📊 Interactive Visualizations (Cached)")
                st.caption("💡 Tip: Hover for details • Scroll to zoom • Drag to pan • Double-click to reset")
                
                # Plot 1: Theoretical vs Measured
                fig1_plotly = create_theoretical_vs_measured_plot(
                    diameters=diameters,
                    theoretical_ratios=theoretical_ratios,
                    measured_data=measured,
                    diameter_col="estimated_diameter_nm",
                    ratio_col="measured_ratio",
                    title="Theoretical vs Measured FSC/SSC Ratio"
                )
                st.plotly_chart(fig1_plotly, width="stretch", config=plotly_config)
                render_pin_button("fcs_cached_theoretical", "FCS: Theoretical vs Measured (Cached)", fig1_plotly, "🧪 Flow Cytometry", "fcs_c1")
                
                # Plot 2: Size Distribution Histogram
                size_ranges_for_plot = st.session_state.get("custom_size_ranges", None)
                fig2_plotly = create_size_distribution_histogram(
                    data=df,
                    size_col="estimated_diameter_nm",
                    nbins=50,
                    title="Particle Size Distribution",
                    show_size_ranges=bool(size_ranges_for_plot),
                    size_ranges=size_ranges_for_plot
                )
                st.plotly_chart(fig2_plotly, width="stretch", config=plotly_config)
                render_pin_button("fcs_cached_size_dist", "FCS: Size Distribution (Cached)", fig2_plotly, "🧪 Flow Cytometry", "fcs_c2")
                
                # Anomaly Detection Results (if available)
                if enable_anomaly_detection_cached and anomaly_mask is not None:
                    st.markdown("---")
                    st.markdown("### 🔍 Anomaly Detection Results (Cached)")
                    
                    combined_count = int(anomaly_mask.sum()) if anomaly_mask is not None else 0
                    
                    anom_cols = st.columns(4)
                    with anom_cols[0]:
                        st.markdown(f"""
                        <div class="stat-card" style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);">
                            <div class="stat-value" style="color: white;">{combined_count:,}</div>
                            <div class="stat-label" style="color: rgba(255,255,255,0.9);">Anomalies Detected</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with anom_cols[1]:
                        pct = (combined_count / len(df)) * 100
                        st.markdown(f"""
                        <div class="stat-card" style="background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);">
                            <div class="stat-value" style="color: white;">{pct:.2f}%</div>
                            <div class="stat-label" style="color: rgba(255,255,255,0.9);">Anomaly Rate</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with anom_cols[2]:
                        normal_count = len(df) - combined_count
                        st.markdown(f"""
                        <div class="stat-card" style="background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);">
                            <div class="stat-value" style="color: white;">{normal_count:,}</div>
                            <div class="stat-label" style="color: rgba(255,255,255,0.9);">Normal Events</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with anom_cols[3]:
                        method_display = params.get('anomaly_method', 'Unknown')
                        st.markdown(f"""
                        <div class="stat-card" style="background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);">
                            <div class="stat-value" style="color: white; font-size: 1.2rem;">{method_display}</div>
                            <div class="stat-label" style="color: rgba(255,255,255,0.9);">Detection Method</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Scatter plots with anomalies
                    if use_interactive_plots:
                        highlight_anomalies = combined_count > 0
                        
                        scatter_cols = st.columns(2)
                        with scatter_cols[0]:
                            fig_fsc_ssc = create_fsc_ssc_scatter(
                                data=df, fsc_col=fsc_col, ssc_col=ssc_col,
                                anomaly_mask=anomaly_mask, highlight_anomalies=highlight_anomalies,
                                title="FSC vs SSC (with Anomalies)"
                            )
                            st.plotly_chart(fig_fsc_ssc, width="stretch", config=plotly_config)
                            render_pin_button("fcs_cached_fsc_ssc", "FCS: FSC vs SSC (Cached)", fig_fsc_ssc, "🧪 Flow Cytometry", "fcs_c3")
                        
                        with scatter_cols[1]:
                            if "estimated_diameter_nm" in df.columns:
                                fig_size_scatter = create_size_vs_scatter_plot(
                                    data=df, size_col="estimated_diameter_nm", scatter_col=ssc_col,
                                    anomaly_mask=anomaly_mask, highlight_anomalies=highlight_anomalies,
                                    title="Diameter vs SSC (with Anomalies)"
                                )
                                st.plotly_chart(fig_size_scatter, width="stretch", config=plotly_config)
                                render_pin_button("fcs_cached_diameter_ssc", "FCS: Diameter vs SSC (Cached)", fig_size_scatter, "🧪 Flow Cytometry", "fcs_c4")
            
            else:
                # Matplotlib static plots (cached)
                st.markdown("---")
                st.markdown("### 📊 Static Visualizations (Cached)")
                
                plt.style.use('dark_background')
                
                fig1, ax1 = plt.subplots(figsize=(10, 5))
                fig1.patch.set_facecolor('#111827')  # type: ignore[attr-defined]
                ax1.set_facecolor('#111827')
                ax1.plot(diameters, theoretical_ratios, color='#00b4d8', linewidth=2, label="Theoretical ratio")
                if not measured.empty:
                    ax1.scatter(measured["estimated_diameter_nm"], measured["measured_ratio"], s=20, alpha=0.6, c='#f72585', label="Measured events")
                ax1.set_xlabel("Diameter (nm)", color='#f8fafc', fontsize=12)
                ax1.set_ylabel("FSC/SSC ratio", color='#f8fafc', fontsize=12)
                ax1.legend(facecolor='#1f2937', edgecolor='#374151', labelcolor='#f8fafc')
                ax1.tick_params(colors='#94a3b8')
                for spine in ax1.spines.values():
                    spine.set_color('#374151')
                ax1.grid(True, alpha=0.2, color='#374151')
                st.pyplot(fig1)
                plt.close()

                fig2, ax2 = plt.subplots(figsize=(10, 5))
                fig2.patch.set_facecolor('#111827')  # type: ignore[attr-defined]
                ax2.set_facecolor('#111827')
                ax2.hist(measured["estimated_diameter_nm"].dropna(), bins=40, color='#00b4d8', edgecolor='#0096c7', alpha=0.85)
                ax2.set_xlabel("Estimated diameter (nm)", color='#f8fafc', fontsize=12)
                ax2.set_ylabel("Counts", color='#f8fafc', fontsize=12)
                ax2.set_title("Particle Size Distribution", color='#f8fafc', fontsize=14, fontweight='bold')
                ax2.tick_params(colors='#94a3b8')
                for spine in ax2.spines.values():
                    spine.set_color('#374151')
                ax2.grid(True, alpha=0.2, color='#374151')
                st.pyplot(fig2)
                plt.close()
    
    # Show message if no analysis has been run yet
    elif not has_cached_results and not run_analysis:
        if st.session_state.get("analysis_df") is not None:
            st.info("📊 File loaded. Click **Run Analysis** to start particle size analysis.")
        # Otherwise the file uploader section above will show its own prompts

# -------------------------
# TAB 3: Nanoparticle Tracking Analysis
# -------------------------

if st.session_state.active_tab == "⚛ Nanoparticle Tracking":
    st.markdown(
        """
        <div style='text-align:center;'>
            <h3 style='color:#00b4d8;'>⚛ Nanoparticle Tracking Analysis</h3>
        </div>
        """,
        unsafe_allow_html=True
    )

    # CSS Animations
    st.markdown(
        """
        <style>
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0px); }
        }
        .animated-section {
            animation: fadeIn 0.7s ease-in-out;
        }
        .tree-ul {
            list-style-type: none;
            margin-left: 1rem;
            line-height: 1.6;
        }
        .tree-ul li::before {
            content: "├── ";
            margin-right: 0.4rem;
        }
        .tree-ul li:last-child::before {
            content: "└── ";
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    uploaded_file_nta = st.file_uploader(
        "📎 Upload NTA Data File",
        type=["txt", "csv", "xlsx", "xls", "json", "parquet", "tsv"],
        help="Supported formats: TXT/TSV (ZetaView), CSV, Excel, JSON, Parquet. If you don't see .txt files, change the file type filter in the dialog to 'All Files'.",
        key="nta_file_uploader"
    )
    
    # Reset Tab button for NTA
    if st.session_state.get('nta_data') is not None:
        reset_cols = st.columns([3, 1])
        with reset_cols[1]:
            if st.button("🔄 Reset Tab", key="reset_nta_tab", width="stretch", help="Clear cached NTA analysis and start fresh"):
                keys_to_clear = [
                    'nta_data', 'nta_raw_data', 'nta_filename', 'nta_correction_enabled',
                    'nta_correction_factor', 'nta_measurement_temp', 'nta_reference_temp',
                    'nta_media_type', 'nta_media_viscosity', 'nta_correction_applied'
                ]
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.success("NTA Tab reset! Upload a new file to analyze.")
                st.rerun()

    # Show Best Practices above upload if file not uploaded yet
    if uploaded_file_nta:
        st.markdown(
            "<div class='animated-section'>"
            "<h4 style='color:#00b4d8;'>🔼 🧠 Best Practices</h4>"
            "</div>",
            unsafe_allow_html=True
        )

        # Optionally show details in expanders
        with st.expander("🛠️ Machine Calibration", expanded=False):
            st.markdown(
                """
                <ul style="line-height:1.8;">
                    <li><b>Maintenance:</b> Cell cleaning should be performed with <b>100% acetone weekly</b>.</li>
                    <li><b>Sample Handling:</b> All samples must be passed through a <b>0.2 μm filter</b> and <b>vortexed before dilution</b>.</li>
                </ul>
                """,
                unsafe_allow_html=True
            )

        with st.expander("🧪 Sample Preparation", expanded=False):
            st.markdown(
                """
                <ul style="line-height:1.8;">
                    <li><b>Dilution:</b> Optimal number of particles per frame should be <b>50–100</b>.</li>
                    <li><b>Buffer Options:</b>
                        <ul>
                            <li>1️⃣ PBS pH 7.4 <em>(fresh stock, filtered through 0.02 μm filter)</em></li>
                            <li>2️⃣ HPLC grade water <em>(filtered through 0.02 μm filter)</em></li>
                        </ul>
                    </li>
                    <li><b>Capture Strategy:</b> Minimum of <b>3 cycles</b> and <b>11 positions</b> for statistical accuracy.</li>
                </ul>
                """,
                unsafe_allow_html=True
            )

        # File upload confirmation
        st.success(f"📁 File uploaded: **{uploaded_file_nta.name}** ({uploaded_file_nta.size / 1024:.1f} KB)")
        
        # =====================================================================
        # TEMPERATURE-VISCOSITY CORRECTION SETTINGS (SIDEBAR)
        # =====================================================================
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 🌡️ Temperature Correction")
            
            if use_nta_corrections:
                # Enable/disable corrections
                apply_corrections = st.toggle(
                    "Apply Temperature Correction",
                    value=False,
                    help="Apply Stokes-Einstein correction for temperature/viscosity differences"
                )
                
                if apply_corrections:
                    st.markdown("##### Measurement Conditions")
                    
                    # Measurement temperature
                    measurement_temp = st.number_input(
                        "Measurement Temperature (°C)",
                        min_value=10.0,
                        max_value=45.0,
                        value=25.0,
                        step=0.5,
                        help="Actual temperature during NTA measurement"
                    )
                    
                    # Reference temperature
                    reference_temp = st.number_input(
                        "Reference Temperature (°C)",
                        min_value=15.0,
                        max_value=40.0,
                        value=25.0,
                        step=0.5,
                        help="Standard reference temperature (typically 25°C)"
                    )
                    
                    # Media type
                    media_options = list(MEDIA_VISCOSITY_FACTORS.keys())
                    media_type = st.selectbox(
                        "Measurement Medium",
                        options=media_options,
                        index=0,
                        help="Select the medium used for NTA measurement"
                    )
                    
                    # Calculate and display correction factor
                    try:
                        media_visc, media_note = get_media_viscosity(media_type, measurement_temp)
                        ref_visc = calculate_water_viscosity(reference_temp)
                        correction_factor, correction_details = get_correction_factor(
                            measurement_temp, 
                            reference_temp,
                            measurement_viscosity=media_visc,
                            reference_viscosity=ref_visc
                        )
                        
                        # Display correction info
                        st.markdown("##### Correction Summary")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(
                                "Correction Factor",
                                f"{correction_factor:.4f}",
                                delta=f"{(correction_factor-1)*100:+.1f}%"
                            )
                        with col2:
                            st.metric(
                                "Medium Viscosity",
                                f"{media_visc*1000:.3f} mPa·s"
                            )
                        
                        st.caption(f"ℹ️ {media_note}")
                        
                        # Store in session state
                        st.session_state['nta_correction_enabled'] = True
                        st.session_state['nta_correction_factor'] = correction_factor
                        st.session_state['nta_measurement_temp'] = measurement_temp
                        st.session_state['nta_reference_temp'] = reference_temp
                        st.session_state['nta_media_type'] = media_type
                        st.session_state['nta_media_viscosity'] = media_visc
                        
                    except Exception as e:
                        st.error(f"Error calculating correction: {str(e)}")
                        st.session_state['nta_correction_enabled'] = False
                else:
                    st.session_state['nta_correction_enabled'] = False
                    st.info("Enable to correct sizes for temperature/viscosity differences")
                    
                # Reference table expander
                with st.expander("📊 Viscosity Reference Table"):
                    if use_nta_corrections:
                        visc_table = get_viscosity_temperature_table(15, 40, 5)
                        st.dataframe(
                            visc_table.style.format({
                                'Viscosity (mPa·s)': '{:.4f}',
                                'Viscosity (Pa·s)': '{:.6f}'
                            }),
                            width="stretch",
                            hide_index=True
                        )
            else:
                st.warning("NTA corrections module not available")
                st.session_state['nta_correction_enabled'] = False
        
        # =====================================================================
        # NTA DATA PARSING AND ANALYSIS
        # =====================================================================
        st.markdown("---")
        st.markdown("### 📊 NTA Data Analysis")
        
        try:
            # Read and parse the NTA file
            file_ext = uploaded_file_nta.name.split('.')[-1].lower()
            
            if file_ext in ['txt', 'tsv']:
                # Parse ZetaView TXT/TSV format
                content = uploaded_file_nta.read().decode('utf-8', errors='ignore')
                lines = content.split('\n')
                
                # Try to find the data section (tab-separated values)
                data_lines = []
                header_found = False
                header_line = None
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check if this looks like a header row
                    if 'Position' in line or 'Mean Int' in line or 'Conc' in line:
                        header_line = line
                        header_found = True
                        continue
                    
                    # If we found header, collect data rows
                    if header_found:
                        # Skip summary rows (Mean, St.Dev., etc.)
                        if line.startswith('Mean') or line.startswith('St.Dev') or line.startswith('Rel.St.Dev'):
                            continue
                        if '\t' in line:
                            data_lines.append(line)
                
                if data_lines and header_line:
                    # Parse into DataFrame
                    from io import StringIO
                    data_text = header_line + '\n' + '\n'.join(data_lines)
                    df_nta = pd.read_csv(StringIO(data_text), sep='\t', engine='python')
                    
                    # Clean column names
                    df_nta.columns = [col.strip() for col in df_nta.columns]
                else:
                    # Fallback: try reading as plain TSV
                    uploaded_file_nta.seek(0)
                    df_nta = pd.read_csv(uploaded_file_nta, sep='\t', engine='python', skiprows=0)
                    
            elif file_ext == 'csv':
                df_nta = pd.read_csv(uploaded_file_nta)
            elif file_ext in ['xlsx', 'xls']:
                df_nta = pd.read_excel(uploaded_file_nta)
            elif file_ext == 'parquet':
                df_nta = pd.read_parquet(uploaded_file_nta)
            elif file_ext == 'json':
                df_nta = pd.read_json(uploaded_file_nta)
            else:
                st.error(f"Unsupported file format: {file_ext}")
                df_nta = None
            
            # Initialize column detection variables (will be populated if data is valid)
            possible_size_cols: list[str] = []
            possible_conc_cols: list[str] = []
            possible_pos_cols: list[str] = []
            
            if df_nta is not None and not df_nta.empty:
                # Display data preview
                st.markdown("#### 📋 Data Preview")
                st.dataframe(df_nta.head(20), width="stretch")
                
                # Show column info
                with st.expander("📊 Column Information", expanded=False):
                    col_info = pd.DataFrame({
                        'Column': df_nta.columns,
                        'Type': df_nta.dtypes.astype(str),
                        'Non-Null': df_nta.count().values,
                        'Sample Value': [str(df_nta[col].iloc[0]) if len(df_nta) > 0 else 'N/A' for col in df_nta.columns]
                    })
                    st.dataframe(col_info, width="stretch")
                
                # =====================================================================
                # KEY METRICS EXTRACTION
                # =====================================================================
                st.markdown("---")
                st.markdown("#### 📈 Key Metrics")
                
                # Check if corrections are enabled
                nta_correction_active = st.session_state.get('nta_correction_enabled', False)
                nta_correction_factor = st.session_state.get('nta_correction_factor', 1.0)
                
                # Show correction status badge
                if nta_correction_active and use_nta_corrections:
                    st.markdown(
                        f"""<div style='background:#1e40af; color:#93c5fd; padding:8px 12px; 
                        border-radius:6px; margin-bottom:10px; display:inline-block;'>
                        🌡️ <b>Temperature Correction Active</b> | 
                        Factor: {nta_correction_factor:.4f} | 
                        {st.session_state.get('nta_measurement_temp', 25):.1f}°C → {st.session_state.get('nta_reference_temp', 25):.1f}°C
                        </div>""",
                        unsafe_allow_html=True
                    )
                
                # Try to identify key columns
                possible_size_cols = [c for c in df_nta.columns if any(x in c.lower() for x in ['x50', 'size', 'diameter', 'd50', 'peak'])]
                possible_conc_cols = [c for c in df_nta.columns if any(x in c.lower() for x in ['conc', 'concentration', 'particles'])]
                possible_pos_cols = [c for c in df_nta.columns if any(x in c.lower() for x in ['position', 'pos'])]
                
                # Display metrics in cards
                metric_cols = st.columns(4)
                
                # Metric 1: Number of positions/measurements
                with metric_cols[0]:
                    n_measurements = len(df_nta)
                    st.metric("📍 Measurements", n_measurements)
                
                # Metric 2: Size (X50/D50) - with correction
                with metric_cols[1]:
                    if possible_size_cols:
                        size_col = possible_size_cols[0]
                        size_data_raw = pd.to_numeric(df_nta[size_col], errors='coerce').dropna()
                        # Filter out invalid values (like 5997.5 which indicates no data)
                        size_data_raw = size_data_raw[size_data_raw < 1000]
                        if len(size_data_raw) > 0:
                            mean_size_raw = size_data_raw.mean()
                            
                            # Apply correction if enabled
                            if nta_correction_active and use_nta_corrections:
                                mean_size_corrected = mean_size_raw * nta_correction_factor
                                delta_pct = (mean_size_corrected - mean_size_raw) / mean_size_raw * 100
                                st.metric(
                                    "📏 Mean Size (nm)", 
                                    f"{mean_size_corrected:.1f}",
                                    delta=f"{delta_pct:+.1f}% corrected"
                                )
                            else:
                                st.metric("📏 Mean Size (nm)", f"{mean_size_raw:.1f}")
                        else:
                            st.metric("📏 Mean Size (nm)", "N/A")
                    else:
                        st.metric("📏 Mean Size (nm)", "N/A")
                
                # Metric 3: Concentration
                with metric_cols[2]:
                    if possible_conc_cols:
                        conc_col = possible_conc_cols[0]
                        conc_data = pd.to_numeric(df_nta[conc_col].astype(str).str.replace('E', 'e'), errors='coerce').dropna()
                        if len(conc_data) > 0:
                            mean_conc = conc_data.mean()
                            st.metric("🔬 Avg Conc (p/mL)", f"{mean_conc:.2e}")
                        else:
                            st.metric("🔬 Avg Conc (p/mL)", "N/A")
                    else:
                        st.metric("🔬 Avg Conc (p/mL)", "N/A")
                
                # Metric 4: Valid positions (with traces)
                with metric_cols[3]:
                    if 'No. of Traces' in df_nta.columns:
                        traces = pd.to_numeric(df_nta['No. of Traces'], errors='coerce')
                        valid_positions = (traces > 0).sum()
                        st.metric("✅ Valid Positions", f"{valid_positions}/{n_measurements}")
                    else:
                        st.metric("✅ Valid Positions", "N/A")
                
                # =====================================================================
                # VISUALIZATION
                # =====================================================================
                st.markdown("---")
                st.markdown("#### 📊 Visualizations")
                st.caption("💡 Tip: Hover for details • Scroll to zoom • Drag to pan • Double-click to reset")
                
                # Get Plotly export config
                plotly_config = get_export_config() if use_interactive_plots else {}
                
                viz_tabs = st.tabs(["📊 Size Distribution", "📈 Concentration Profile", "🔍 Position Analysis", "🌡️ Corrected View"])
                
                with viz_tabs[0]:
                    # Size Distribution Plot (Raw or Corrected based on setting)
                    if possible_size_cols:
                        size_col = possible_size_cols[0]
                        size_data_raw = pd.to_numeric(df_nta[size_col], errors='coerce').dropna()
                        size_data_raw = size_data_raw[(size_data_raw > 0) & (size_data_raw < 1000)]  # Filter valid sizes
                        
                        # Apply correction if enabled
                        if nta_correction_active and use_nta_corrections:
                            size_data = size_data_raw * nta_correction_factor
                            is_corrected = True
                        else:
                            size_data = size_data_raw
                            is_corrected = False
                        
                        if len(size_data) > 0:
                            # Use interactive Plotly plot if available
                            if use_interactive_plots:
                                fig_size = create_nta_size_distribution(
                                    size_data.values,
                                    nbins=20,
                                    title="Particle Size Distribution",
                                    show_percentiles=True,
                                    corrected=is_corrected
                                )
                                st.plotly_chart(fig_size, width="stretch", config=plotly_config)
                                render_pin_button("nta_size_distribution", "NTA: Particle Size Distribution", fig_size, "⚛ Nanoparticle Tracking", "nta1")
                            else:
                                # Fallback to matplotlib
                                fig_size_mpl, ax_size = plt.subplots(figsize=(10, 5))
                                fig_size_mpl.patch.set_facecolor('#111827')  # type: ignore[attr-defined]
                                ax_size.set_facecolor('#111827')
                                ax_size.hist(size_data, bins=20, color='#00b4d8', edgecolor='#0096c7', alpha=0.8)
                                
                                d10 = np.percentile(size_data, 10)
                                d50 = np.percentile(size_data, 50)
                                d90 = np.percentile(size_data, 90)
                                
                                ax_size.axvline(d10, color='#10b981', linestyle='--', linewidth=2, label=f'D10: {d10:.1f} nm')
                                ax_size.axvline(d50, color='#f72585', linestyle='-', linewidth=2, label=f'D50: {d50:.1f} nm')
                                ax_size.axvline(d90, color='#f59e0b', linestyle='--', linewidth=2, label=f'D90: {d90:.1f} nm')
                                
                                title_suffix = " (Corrected)" if is_corrected else ""
                                ax_size.set_xlabel("Particle Size (nm)", color='#f8fafc', fontsize=12)
                                ax_size.set_ylabel("Count", color='#f8fafc', fontsize=12)
                                ax_size.set_title(f"Particle Size Distribution{title_suffix}", color='#f8fafc', fontsize=14, fontweight='bold')
                                ax_size.tick_params(colors='#94a3b8')
                                ax_size.legend(facecolor='#1f2937', edgecolor='#374151', labelcolor='#f8fafc')
                                for spine in ax_size.spines.values():
                                    spine.set_color('#374151')
                                ax_size.grid(True, alpha=0.2, color='#374151')
                                
                                st.pyplot(fig_size_mpl)
                                plt.close()
                            
                            # Show statistics
                            d10 = np.percentile(size_data, 10)
                            d50 = np.percentile(size_data, 50)
                            d90 = np.percentile(size_data, 90)
                            title_suffix = " (Corrected)" if is_corrected else ""
                            
                            st.markdown(f"**Size Statistics{title_suffix}:**")
                            stat_cols = st.columns(5)
                            stat_cols[0].metric("D10", f"{d10:.1f} nm")
                            stat_cols[1].metric("D50 (Median)", f"{d50:.1f} nm")
                            stat_cols[2].metric("D90", f"{d90:.1f} nm")
                            stat_cols[3].metric("Mean", f"{size_data.mean():.1f} nm")
                            stat_cols[4].metric("Std Dev", f"{size_data.std():.1f} nm")
                            
                            # =====================================================
                            # THREE SIZE CATEGORIES (<50nm, 50-200nm, >200nm)
                            # =====================================================
                            st.markdown("---")
                            st.markdown(f"**Particle Size Categories{title_suffix}:**")
                            
                            # Calculate counts for each category
                            small_particles = (size_data < 50).sum()  # <50nm (small EVs, exomeres)
                            medium_particles = ((size_data >= 50) & (size_data <= 200)).sum()  # 50-200nm (exosomes)
                            large_particles = (size_data > 200).sum()  # >200nm (microvesicles)
                            total_particles = len(size_data)
                            
                            # Calculate percentages
                            small_pct = (small_particles / total_particles) * 100 if total_particles > 0 else 0
                            medium_pct = (medium_particles / total_particles) * 100 if total_particles > 0 else 0
                            large_pct = (large_particles / total_particles) * 100 if total_particles > 0 else 0
                            
                            # Display as colorful stat cards
                            cat_cols = st.columns(3)
                            with cat_cols[0]:
                                st.markdown(f"""
                                <div class="stat-card" style="background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);">
                                    <div class="stat-value" style="color: white;">{small_particles:,}</div>
                                    <div class="stat-label" style="color: rgba(255,255,255,0.9);">&lt;50 nm ({small_pct:.1f}%)</div>
                                    <div style="color: rgba(255,255,255,0.7); font-size: 11px; margin-top: 4px;">Small EVs / Exomeres</div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            with cat_cols[1]:
                                st.markdown(f"""
                                <div class="stat-card" style="background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);">
                                    <div class="stat-value" style="color: white;">{medium_particles:,}</div>
                                    <div class="stat-label" style="color: rgba(255,255,255,0.9);">50-200 nm ({medium_pct:.1f}%)</div>
                                    <div style="color: rgba(255,255,255,0.7); font-size: 11px; margin-top: 4px;">Exosomes</div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            with cat_cols[2]:
                                st.markdown(f"""
                                <div class="stat-card" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);">
                                    <div class="stat-value" style="color: white;">{large_particles:,}</div>
                                    <div class="stat-label" style="color: rgba(255,255,255,0.9);">&gt;200 nm ({large_pct:.1f}%)</div>
                                    <div style="color: rgba(255,255,255,0.7); font-size: 11px; margin-top: 4px;">Microvesicles</div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Create a pie chart for size categories
                            if use_interactive_plots:
                                import plotly.graph_objects as go
                                
                                fig_pie = go.Figure(data=[go.Pie(
                                    labels=['<50 nm<br>(Small EVs)', '50-200 nm<br>(Exosomes)', '>200 nm<br>(Microvesicles)'],
                                    values=[small_particles, medium_particles, large_particles],
                                    hole=0.4,
                                    marker=dict(colors=['#06b6d4', '#8b5cf6', '#f59e0b']),
                                    textinfo='percent+value',
                                    textfont=dict(size=12, color='white'),
                                    hovertemplate='<b>%{label}</b><br>Count: %{value:,}<br>Percentage: %{percent}<extra></extra>'
                                )])
                                
                                fig_pie.update_layout(
                                    title=dict(
                                        text=f"Particle Size Distribution by Category{title_suffix}",
                                        font=dict(size=16, color='#f8fafc'),
                                        x=0.5
                                    ),
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color='#f8fafc'),
                                    showlegend=True,
                                    legend=dict(
                                        orientation='h',
                                        yanchor='bottom',
                                        y=-0.15,
                                        xanchor='center',
                                        x=0.5,
                                        font=dict(size=11)
                                    ),
                                    margin=dict(t=60, b=60, l=20, r=20),
                                    annotations=[dict(
                                        text=f'Total<br>{total_particles:,}',
                                        x=0.5, y=0.5,
                                        font=dict(size=14, color='#f8fafc'),
                                        showarrow=False
                                    )]
                                )
                                
                                st.plotly_chart(fig_pie, width="stretch", config=plotly_config)
                                render_pin_button("nta_size_categories", "NTA: Size Category Distribution", fig_pie, "⚛ Nanoparticle Tracking", "nta_cat")
                            
                            # Summary interpretation
                            dominant_category = max([
                                ('<50 nm (Small EVs/Exomeres)', small_pct),
                                ('50-200 nm (Exosomes)', medium_pct),
                                ('>200 nm (Microvesicles)', large_pct)
                            ], key=lambda x: x[1])
                            
                            st.info(f"📊 **Dominant population:** {dominant_category[0]} at {dominant_category[1]:.1f}% of total particles")
                            
                            # If corrections are active, show comparison
                            if nta_correction_active and use_nta_corrections:
                                with st.expander("📊 Raw vs Corrected Comparison", expanded=False):
                                    d10_raw = np.percentile(size_data_raw, 10)
                                    d50_raw = np.percentile(size_data_raw, 50)
                                    d90_raw = np.percentile(size_data_raw, 90)
                                    
                                    comparison_df = pd.DataFrame({
                                        'Metric': ['D10', 'D50 (Median)', 'D90', 'Mean', 'Std Dev'],
                                        'Raw (nm)': [d10_raw, d50_raw, d90_raw, size_data_raw.mean(), size_data_raw.std()],
                                        'Corrected (nm)': [d10, d50, d90, size_data.mean(), size_data.std()],
                                        'Change (%)': [
                                            (d10 - d10_raw) / d10_raw * 100,
                                            (d50 - d50_raw) / d50_raw * 100,
                                            (d90 - d90_raw) / d90_raw * 100,
                                            (size_data.mean() - size_data_raw.mean()) / size_data_raw.mean() * 100,
                                            (size_data.std() - size_data_raw.std()) / size_data_raw.std() * 100
                                        ]
                                    })
                                    
                                    st.dataframe(
                                        comparison_df.style.format({
                                            'Raw (nm)': '{:.1f}',
                                            'Corrected (nm)': '{:.1f}',
                                            'Change (%)': '{:+.2f}'
                                        }).background_gradient(cmap='RdYlGn', subset=['Change (%)']),
                                        width="stretch",
                                        hide_index=True
                                    )
                        else:
                            st.warning("No valid size data found in the file.")
                    else:
                        st.info("No size column detected. Available columns: " + ", ".join(list(df_nta.columns)))
                
                with viz_tabs[1]:
                    # Concentration Profile
                    if possible_conc_cols and possible_pos_cols:
                        conc_col = possible_conc_cols[0]
                        pos_col = possible_pos_cols[0]
                        
                        conc_data = pd.to_numeric(df_nta[conc_col].astype(str).str.replace('E', 'e'), errors='coerce')
                        pos_data = pd.to_numeric(df_nta[pos_col], errors='coerce')
                        
                        valid_mask = conc_data.notna() & pos_data.notna()
                        
                        if valid_mask.sum() > 0:
                            # Use interactive Plotly plot if available
                            if use_interactive_plots:
                                fig_conc = create_nta_concentration_profile(
                                    pos_data[valid_mask].values,
                                    conc_data[valid_mask].values,
                                    title="Concentration by Position"
                                )
                                st.plotly_chart(fig_conc, width="stretch", config=plotly_config)
                                render_pin_button("nta_concentration_profile", "NTA: Concentration by Position", fig_conc, "⚛ Nanoparticle Tracking", "nta2")
                            else:
                                # Fallback to matplotlib
                                fig_conc_mpl, ax_conc = plt.subplots(figsize=(10, 5))
                                fig_conc_mpl.patch.set_facecolor('#111827')  # type: ignore[attr-defined]
                                ax_conc.set_facecolor('#111827')
                                
                                ax_conc.bar(pos_data[valid_mask], conc_data[valid_mask], color='#7c3aed', edgecolor='#a78bfa', alpha=0.8)
                                
                                ax_conc.set_xlabel("Position", color='#f8fafc', fontsize=12)
                                ax_conc.set_ylabel("Concentration (p/mL)", color='#f8fafc', fontsize=12)
                                ax_conc.set_title("Concentration by Position", color='#f8fafc', fontsize=14, fontweight='bold')
                                ax_conc.tick_params(colors='#94a3b8')
                                for spine in ax_conc.spines.values():
                                    spine.set_color('#374151')
                                ax_conc.grid(True, alpha=0.2, color='#374151', axis='y')
                                
                                # Format y-axis for scientific notation
                                ax_conc.ticklabel_format(style='scientific', axis='y', scilimits=(0,0))
                                
                                st.pyplot(fig_conc_mpl)
                                plt.close()
                        else:
                            st.warning("No valid concentration data for plotting.")
                    else:
                        st.info("Concentration or position columns not detected.")
                
                with viz_tabs[2]:
                    # Position Analysis (11-position uniformity)
                    st.markdown("**Position-by-Position Analysis**")
                    
                    # Show all data in a styled table (handle non-unique index/columns)
                    try:
                        # Reset index and ensure unique columns for styling
                        df_display = df_nta.reset_index(drop=True).copy()
                        # Make columns unique if there are duplicates
                        if df_display.columns.duplicated().any():
                            df_display.columns = [f"{col}_{i}" if df_display.columns[:i].tolist().count(col) > 0 else col 
                                                  for i, col in enumerate(df_display.columns)]
                        
                        numeric_cols = [c for c in df_display.columns if df_display[c].dtype in ['float64', 'int64', 'float32', 'int32']]
                        if numeric_cols:
                            st.dataframe(
                                df_display.style.background_gradient(cmap='Blues', subset=numeric_cols),
                                width="stretch"
                            )
                        else:
                            st.dataframe(df_display, width="stretch")
                    except Exception:
                        # Fallback: display without styling if styling fails
                        st.dataframe(df_nta, width="stretch")
                    
                    # Check for uniformity (CV analysis)
                    if possible_conc_cols:
                        conc_col = possible_conc_cols[0]
                        conc_data = pd.to_numeric(df_nta[conc_col].astype(str).str.replace('E', 'e'), errors='coerce').dropna()
                        if len(conc_data) > 1:
                            cv_conc = (conc_data.std() / conc_data.mean()) * 100
                            if cv_conc < 20:
                                st.success(f"✅ Good uniformity! Concentration CV: {cv_conc:.1f}% (< 20%)")
                            elif cv_conc < 30:
                                st.warning(f"⚠️ Moderate uniformity. Concentration CV: {cv_conc:.1f}% (20-30%)")
                            else:
                                st.error(f"❌ Poor uniformity. Concentration CV: {cv_conc:.1f}% (> 30%)")
                
                with viz_tabs[3]:
                    # Corrected View Tab - Detailed temperature correction analysis
                    st.markdown("### 🌡️ Temperature-Viscosity Correction Analysis")
                    
                    if use_nta_corrections:
                        if not nta_correction_active:
                            st.info("💡 Enable temperature correction in the sidebar to see corrected data.")
                            st.markdown("""
                            **Why correct for temperature?**
                            
                            NTA instruments calculate particle size from diffusion coefficients using the Stokes-Einstein equation:
                            
                            $$D = \\frac{k_B T}{3\\pi \\eta d}$$
                            
                            Where:
                            - $D$ = diffusion coefficient
                            - $k_B$ = Boltzmann constant
                            - $T$ = absolute temperature
                            - $\\eta$ = viscosity of the medium
                            - $d$ = hydrodynamic diameter
                            
                            If the measurement temperature differs from the reference temperature (usually 25°C), 
                            or if the medium viscosity differs from water, the calculated size needs correction.
                            """)
                            
                            # Show reference tables
                            st.markdown("#### 📊 Reference Tables")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("**Water Viscosity vs Temperature**")
                                visc_table = get_viscosity_temperature_table(15, 40, 5)
                                st.dataframe(
                                    visc_table[['Temperature (°C)', 'Viscosity (mPa·s)']].style.format({
                                        'Viscosity (mPa·s)': '{:.4f}'
                                    }),
                                    width="stretch",
                                    hide_index=True
                                )
                            
                            with col2:
                                st.markdown("**Correction Factors (ref = 25°C)**")
                                corr_table = get_correction_reference_table([18, 20, 22, 25, 30, 37], 25.0)
                                st.dataframe(
                                    corr_table[['Measurement T (°C)', 'Correction Factor', 'Size Change (%)']].style.format({
                                        'Correction Factor': '{:.4f}',
                                        'Size Change (%)': '{:+.2f}'
                                    }),
                                    width="stretch",
                                    hide_index=True
                                )
                        else:
                            # Correction is active - show detailed analysis
                            st.success(f"✅ Temperature correction active: {st.session_state.get('nta_measurement_temp', 25):.1f}°C → {st.session_state.get('nta_reference_temp', 25):.1f}°C")
                            
                            # Correction details
                            st.markdown("#### 📋 Correction Parameters")
                            param_cols = st.columns(4)
                            
                            with param_cols[0]:
                                st.metric("Measurement Temp", f"{st.session_state.get('nta_measurement_temp', 25):.1f}°C")
                            with param_cols[1]:
                                st.metric("Reference Temp", f"{st.session_state.get('nta_reference_temp', 25):.1f}°C")
                            with param_cols[2]:
                                st.metric("Medium", st.session_state.get('nta_media_type', 'water'))
                            with param_cols[3]:
                                st.metric("Correction Factor", f"{nta_correction_factor:.4f}")
                            
                            # If size data available, show comprehensive comparison
                            if possible_size_cols:
                                size_col = possible_size_cols[0]
                                size_data_raw = pd.to_numeric(df_nta[size_col], errors='coerce').dropna()
                                size_data_raw = size_data_raw[(size_data_raw > 0) & (size_data_raw < 1000)]
                                
                                if len(size_data_raw) > 0:
                                    size_data_corrected = size_data_raw * nta_correction_factor
                                    
                                    st.markdown("#### 📊 Side-by-Side Comparison")
                                    
                                    # Create side-by-side histogram
                                    fig_compare, axes = plt.subplots(1, 2, figsize=(12, 5))
                                    fig_compare.patch.set_facecolor('#111827')  # type: ignore[attr-defined]
                                    
                                    for ax in axes:
                                        ax.set_facecolor('#111827')
                                        for spine in ax.spines.values():
                                            spine.set_color('#374151')
                                        ax.tick_params(colors='#94a3b8')
                                    
                                    # Raw histogram
                                    axes[0].hist(size_data_raw, bins=20, color='#64748b', edgecolor='#94a3b8', alpha=0.8)
                                    raw_d50 = np.percentile(size_data_raw, 50)
                                    axes[0].axvline(raw_d50, color='#f72585', linestyle='--', linewidth=2, label=f'D50: {raw_d50:.1f} nm')
                                    axes[0].set_xlabel("Particle Size (nm)", color='#f8fafc')
                                    axes[0].set_ylabel("Count", color='#f8fafc')
                                    axes[0].set_title("Raw Data", color='#f8fafc', fontweight='bold')
                                    axes[0].legend(facecolor='#1f2937', edgecolor='#374151', labelcolor='#f8fafc')
                                    axes[0].grid(True, alpha=0.2, color='#374151')
                                    
                                    # Corrected histogram
                                    axes[1].hist(size_data_corrected, bins=20, color='#00b4d8', edgecolor='#0096c7', alpha=0.8)
                                    corr_d50 = np.percentile(size_data_corrected, 50)
                                    axes[1].axvline(corr_d50, color='#f72585', linestyle='--', linewidth=2, label=f'D50: {corr_d50:.1f} nm')
                                    axes[1].set_xlabel("Particle Size (nm)", color='#f8fafc')
                                    axes[1].set_ylabel("Count", color='#f8fafc')
                                    axes[1].set_title("Corrected Data", color='#f8fafc', fontweight='bold')
                                    axes[1].legend(facecolor='#1f2937', edgecolor='#374151', labelcolor='#f8fafc')
                                    axes[1].grid(True, alpha=0.2, color='#374151')
                                    
                                    plt.tight_layout()
                                    st.pyplot(fig_compare)
                                    plt.close()
                                    
                                    # Detailed statistics table
                                    st.markdown("#### 📈 Detailed Statistics Comparison")
                                    
                                    stats_comparison = pd.DataFrame({
                                        'Statistic': ['D10', 'D25', 'D50 (Median)', 'D75', 'D90', 'Mean', 'Std Dev', 'CV (%)'],
                                        'Raw (nm)': [
                                            np.percentile(size_data_raw, 10),
                                            np.percentile(size_data_raw, 25),
                                            np.percentile(size_data_raw, 50),
                                            np.percentile(size_data_raw, 75),
                                            np.percentile(size_data_raw, 90),
                                            size_data_raw.mean(),
                                            size_data_raw.std(),
                                            (size_data_raw.std() / size_data_raw.mean()) * 100
                                        ],
                                        'Corrected (nm)': [
                                            np.percentile(size_data_corrected, 10),
                                            np.percentile(size_data_corrected, 25),
                                            np.percentile(size_data_corrected, 50),
                                            np.percentile(size_data_corrected, 75),
                                            np.percentile(size_data_corrected, 90),
                                            size_data_corrected.mean(),
                                            size_data_corrected.std(),
                                            (size_data_corrected.std() / size_data_corrected.mean()) * 100
                                        ],
                                        'Change (%)': [
                                            (np.percentile(size_data_corrected, 10) - np.percentile(size_data_raw, 10)) / np.percentile(size_data_raw, 10) * 100,
                                            (np.percentile(size_data_corrected, 25) - np.percentile(size_data_raw, 25)) / np.percentile(size_data_raw, 25) * 100,
                                            (np.percentile(size_data_corrected, 50) - np.percentile(size_data_raw, 50)) / np.percentile(size_data_raw, 50) * 100,
                                            (np.percentile(size_data_corrected, 75) - np.percentile(size_data_raw, 75)) / np.percentile(size_data_raw, 75) * 100,
                                            (np.percentile(size_data_corrected, 90) - np.percentile(size_data_raw, 90)) / np.percentile(size_data_raw, 90) * 100,
                                            (size_data_corrected.mean() - size_data_raw.mean()) / size_data_raw.mean() * 100,
                                            (size_data_corrected.std() - size_data_raw.std()) / size_data_raw.std() * 100,
                                            0  # CV doesn't change with linear scaling
                                        ]
                                    })
                                    
                                    st.dataframe(
                                        stats_comparison.style.format({
                                            'Raw (nm)': '{:.2f}',
                                            'Corrected (nm)': '{:.2f}',
                                            'Change (%)': '{:+.2f}'
                                        }).background_gradient(cmap='RdYlGn', subset=['Change (%)'], vmin=-10, vmax=10),
                                        width="stretch",
                                        hide_index=True
                                    )
                                    
                                    # Stokes-Einstein explanation
                                    with st.expander("ℹ️ About the Correction"):
                                        st.markdown(f"""
                                        **Stokes-Einstein Correction Applied**
                                        
                                        The correction adjusts particle sizes based on temperature and viscosity differences:
                                        
                                        - **Measurement conditions:** {st.session_state.get('nta_measurement_temp', 25):.1f}°C, {st.session_state.get('nta_media_type', 'water')}
                                        - **Reference conditions:** {st.session_state.get('nta_reference_temp', 25):.1f}°C, water
                                        - **Viscosity at measurement temp:** {st.session_state.get('nta_media_viscosity', 0.001)*1000:.4f} mPa·s
                                        - **Viscosity at reference temp:** {calculate_water_viscosity(st.session_state.get('nta_reference_temp', 25))*1000:.4f} mPa·s
                                        
                                        **Correction formula:**
                                        
                                        $$d_{{corrected}} = d_{{raw}} \\times \\frac{{\\eta_{{ref}}}}{{\\eta_{{meas}}}} \\times \\frac{{T_{{meas}}}}{{T_{{ref}}}}$$
                                        
                                        Where $\\eta$ is viscosity (Pa·s) and $T$ is temperature (K).
                                        """)
                                else:
                                    st.warning("No valid size data available for correction analysis.")
                            else:
                                st.info("No size column detected in the data.")
                    else:
                        st.error("NTA corrections module not available. Please check that `src/physics/nta_corrections.py` exists.")
                
                # =====================================================================
                # EXPORT OPTIONS
                # =====================================================================
                st.markdown("---")
                st.markdown("#### 💾 Export Options")
                
                # Prepare export data with optional corrections
                df_export = df_nta.copy()
                
                # Add corrected columns if corrections are enabled and size column exists
                if nta_correction_active and use_nta_corrections and possible_size_cols:
                    for size_col in possible_size_cols:
                        raw_sizes = pd.to_numeric(df_export[size_col], errors='coerce')
                        df_export[f"{size_col}_corrected"] = raw_sizes * nta_correction_factor
                    
                    # Add correction metadata as attributes (will show in header comment)
                    export_note = f"Corrected at {st.session_state.get('nta_measurement_temp', 25):.1f}°C → {st.session_state.get('nta_reference_temp', 25):.1f}°C (factor: {nta_correction_factor:.4f})"
                else:
                    export_note = "No temperature correction applied"
                
                export_cols = st.columns(4)
                
                with export_cols[0]:
                    # Export as CSV
                    csv_data = df_export.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "⬇️ Download as CSV",
                        data=csv_data,
                        file_name=f"nta_analysis_{uploaded_file_nta.name.replace('.txt', '')}.csv",
                        mime="text/csv",
                        width="stretch"
                    )
                
                with export_cols[1]:
                    # Export as Parquet (if pyarrow available)
                    if use_pyarrow:
                        parquet_buffer = io.BytesIO()
                        df_export.to_parquet(parquet_buffer, index=False)
                        st.download_button(
                            "⬇️ Download as Parquet",
                            data=parquet_buffer.getvalue(),
                            file_name=f"nta_analysis_{uploaded_file_nta.name.replace('.txt', '')}.parquet",
                            mime="application/octet-stream",
                            width="stretch"
                        )
                    else:
                        st.button("⬇️ Parquet (requires pyarrow)", disabled=True, width="stretch")
                
                with export_cols[2]:
                    # Generate summary report (with correction info)
                    summary_text = f"""# NTA Analysis Report
File: {uploaded_file_nta.name}
Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary Statistics
- Total Measurements: {len(df_nta)}
- Temperature Correction: {export_note}
"""
                    if possible_size_cols:
                        size_col = possible_size_cols[0]
                        size_data_raw = pd.to_numeric(df_nta[size_col], errors='coerce').dropna()
                        size_data_raw = size_data_raw[(size_data_raw > 0) & (size_data_raw < 1000)]
                        if len(size_data_raw) > 0:
                            summary_text += f"""
## Size Distribution (Raw)
- D10: {np.percentile(size_data_raw, 10):.1f} nm
- D50 (Median): {np.percentile(size_data_raw, 50):.1f} nm
- D90: {np.percentile(size_data_raw, 90):.1f} nm
- Mean: {size_data_raw.mean():.1f} nm
- Std Dev: {size_data_raw.std():.1f} nm
"""
                            # Add corrected stats if enabled
                            if nta_correction_active and use_nta_corrections:
                                size_data_corr = size_data_raw * nta_correction_factor
                                summary_text += f"""
## Size Distribution (Corrected)
- D10: {np.percentile(size_data_corr, 10):.1f} nm
- D50 (Median): {np.percentile(size_data_corr, 50):.1f} nm
- D90: {np.percentile(size_data_corr, 90):.1f} nm
- Mean: {size_data_corr.mean():.1f} nm
- Std Dev: {size_data_corr.std():.1f} nm

## Correction Parameters
- Measurement Temperature: {st.session_state.get('nta_measurement_temp', 25):.1f}°C
- Reference Temperature: {st.session_state.get('nta_reference_temp', 25):.1f}°C
- Medium: {st.session_state.get('nta_media_type', 'water')}
- Viscosity at Measurement Temp: {st.session_state.get('nta_media_viscosity', 0.001)*1000:.4f} mPa·s
- Correction Factor: {nta_correction_factor:.4f}
"""
                    
                    st.download_button(
                        "📄 Download Report",
                        data=summary_text.encode('utf-8'),
                        file_name=f"nta_report_{uploaded_file_nta.name.replace('.txt', '')}.md",
                        mime="text/markdown",
                        width="stretch"
                    )
                
                with export_cols[3]:
                    # Export correction reference table if corrections module available
                    if use_nta_corrections:
                        ref_table = get_correction_reference_table([18, 20, 22, 25, 30, 37], 25.0)
                        ref_csv = ref_table.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📊 Correction Reference",
                            data=ref_csv,
                            file_name="nta_correction_reference.csv",
                            mime="text/csv",
                            width="stretch"
                        )
                    else:
                        st.button("📊 Correction Reference", disabled=True, width="stretch")
                
                # Store in session state for potential cross-tab analysis
                st.session_state['nta_data'] = df_export
                st.session_state['nta_filename'] = uploaded_file_nta.name
                st.session_state['nta_raw_data'] = df_nta
                if nta_correction_active:
                    st.session_state['nta_correction_applied'] = True
                
            else:
                st.warning("Could not parse the uploaded file. Please check the file format.")
                
        except Exception as e:
            st.error(f"Error processing NTA file: {str(e)}")
            with st.expander("🔍 Error Details", expanded=False):
                import traceback
                st.code(traceback.format_exc())
    else:
        # Show Best Practices collapsed if no file yet
        st.info("📤 Please upload an NTA file to begin analysis.")


# -------------------------
# TAB 4: Cross-Instrument Comparison
# -------------------------
if st.session_state.active_tab == "🔬 Cross-Comparison":
    st.markdown("""
    <div style='text-align: center; padding: 20px;'>
        <h1 style='color: #00b4d8;'>🔬 Cross-Instrument Comparison</h1>
        <p style='color: #94a3b8; font-size: 1.1em;'>
            Compare the same sample across FCS (NanoFACS) and NTA (ZetaView) instruments
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if both FCS and NTA data are available
    has_fcs_data = 'fcs_data' in st.session_state and st.session_state['fcs_data'] is not None
    has_nta_data = 'nta_data' in st.session_state and st.session_state['nta_data'] is not None
    
    # Reset button for Cross-Comparison
    if has_fcs_data or has_nta_data:
        reset_cols = st.columns([4, 1])
        with reset_cols[1]:
            if st.button("🔄 Clear All Data", key="reset_comparison_tab", width="stretch", help="Clear both FCS and NTA data to start fresh"):
                keys_to_clear = [
                    'fcs_data', 'fcs_filename', 'fcs_fsc_col', 'fcs_ssc_col',
                    'fcs_analysis_complete', 'fcs_results_df', 'fcs_diameters',
                    'fcs_theoretical_ratios', 'fcs_analysis_params', 'fcs_anomaly_mask',
                    'nta_data', 'nta_raw_data', 'nta_filename', 'nta_correction_enabled',
                    'nta_correction_factor', 'nta_measurement_temp', 'nta_reference_temp'
                ]
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.success("All comparison data cleared! Go to FCS or NTA tabs to upload new data.")
                st.rerun()
    
    # Sidebar options for comparison
    with st.sidebar:
        st.markdown('<div class="section-header"><div class="section-icon">⚙️</div><h3>Comparison Settings</h3></div>', unsafe_allow_html=True)
        
        # Discrepancy threshold
        discrepancy_threshold = st.slider(
            "Discrepancy Threshold (%)",
            min_value=5,
            max_value=30,
            value=15,
            step=5,
            help="Highlight measurements that differ by more than this percentage"
        )
        
        # Histogram settings
        st.markdown("**Histogram Settings**")
        normalize_histograms = st.checkbox("Normalize Distributions", value=True, help="Show as probability density")
        bin_size = st.slider("Bin Size (nm)", min_value=2, max_value=20, value=5)
        
        # Advanced options
        with st.expander("🔧 Advanced Options", expanded=False):
            show_kde = st.checkbox("Show KDE Overlay", value=True, help="Kernel Density Estimation curves")
            show_statistics = st.checkbox("Show Statistical Tests", value=True, help="KS test, Mann-Whitney U test")
            min_size_filter = st.number_input("Min Size (nm)", value=0, min_value=0, max_value=100)
            max_size_filter = st.number_input("Max Size (nm)", value=500, min_value=100, max_value=1000)
    
    # Main content area
    if has_fcs_data and has_nta_data:
        st.success("✅ Both FCS and NTA data are loaded. Ready for comparison!")
        
        fcs_df = st.session_state['fcs_data']
        nta_df = st.session_state['nta_data']
        
        # Extract file names
        fcs_filename = st.session_state.get('fcs_filename', 'FCS Sample')
        nta_filename = st.session_state.get('nta_filename', 'NTA Sample')
        
        # Sample info cards
        info_cols = st.columns(2)
        with info_cols[0]:
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, rgba(0,180,216,0.2), rgba(0,180,216,0.05)); 
                        border: 1px solid rgba(0,180,216,0.3); border-radius: 12px; padding: 20px;'>
                <h3 style='color: #00b4d8; margin-bottom: 10px;'>🧪 FCS Data</h3>
                <p style='color: #f8fafc; margin: 5px 0;'><strong>File:</strong> {fcs_filename}</p>
                <p style='color: #94a3b8; margin: 5px 0;'>Events: {len(fcs_df):,}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with info_cols[1]:
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, rgba(124,58,237,0.2), rgba(124,58,237,0.05)); 
                        border: 1px solid rgba(124,58,237,0.3); border-radius: 12px; padding: 20px;'>
                <h3 style='color: #7c3aed; margin-bottom: 10px;'>⚛ NTA Data</h3>
                <p style='color: #f8fafc; margin: 5px 0;'><strong>File:</strong> {nta_filename}</p>
                <p style='color: #94a3b8; margin: 5px 0;'>Measurements: {len(nta_df):,}</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Extract size data from FCS
        fcs_sizes = None
        possible_fcs_size_cols = [col for col in fcs_df.columns if any(s in col.lower() for s in ['size', 'diameter', 'fsc', 'forward'])]
        if possible_fcs_size_cols:
            fcs_size_col = st.selectbox("FCS Size Column", options=possible_fcs_size_cols, key="fcs_size_col_select")
            fcs_sizes = pd.to_numeric(fcs_df[fcs_size_col], errors='coerce').dropna().values
            # Apply filters
            fcs_sizes = fcs_sizes[(fcs_sizes >= min_size_filter) & (fcs_sizes <= max_size_filter)]
        
        # Extract size data from NTA
        nta_sizes = None
        possible_nta_size_cols = [col for col in nta_df.columns if any(s in col.lower() for s in ['size', 'diameter', 'mean', 'median', 'mode', 'd50', 'nm'])]
        if possible_nta_size_cols:
            nta_size_col = st.selectbox("NTA Size Column", options=possible_nta_size_cols, key="nta_size_col_select")
            nta_sizes = pd.to_numeric(nta_df[nta_size_col], errors='coerce').dropna().values
            # Apply filters
            nta_sizes = nta_sizes[(nta_sizes >= min_size_filter) & (nta_sizes <= max_size_filter)]
        
        # Comparison Visualizations
        if fcs_sizes is not None and len(fcs_sizes) > 0 and nta_sizes is not None and len(nta_sizes) > 0:
            st.markdown("### 📊 Size Distribution Comparison")
            
            # Visualization tabs
            viz_tabs = st.tabs(["📊 Overlay Histogram", "🌊 KDE Comparison", "📈 Statistics", "📉 Discrepancy Analysis"])
            
            with viz_tabs[0]:
                # Overlay Histogram
                if use_cross_comparison:
                    fig_overlay = create_size_overlay_histogram(
                        fcs_sizes=fcs_sizes,
                        nta_sizes=nta_sizes,
                        fcs_label=f"FCS ({fcs_filename})",
                        nta_label=f"NTA ({nta_filename})",
                        title="Size Distribution Overlay",
                        bin_size=bin_size,
                        normalize=normalize_histograms
                    )
                    st.plotly_chart(fig_overlay, width="stretch")
                    render_pin_button("cross_overlay_histogram", "Cross-Comparison: Size Overlay", fig_overlay, "🔬 Cross-Comparison", "cross1")
                else:
                    # Fallback matplotlib version
                    fig, ax = plt.subplots(figsize=(12, 6))
                    ax.hist(fcs_sizes, bins=50, alpha=0.6, label=f'FCS ({len(fcs_sizes):,} events)', color='#00b4d8')
                    ax.hist(nta_sizes, bins=50, alpha=0.6, label=f'NTA ({len(nta_sizes):,} particles)', color='#7c3aed')
                    ax.set_xlabel('Size (nm)')
                    ax.set_ylabel('Count')
                    ax.set_title('Size Distribution Overlay')
                    ax.legend()
                    ax.set_facecolor('#111827')
                    fig.patch.set_facecolor('#111827')  # type: ignore[attr-defined]
                    ax.tick_params(colors='white')
                    ax.xaxis.label.set_color('white')
                    ax.yaxis.label.set_color('white')
                    ax.title.set_color('white')  # type: ignore[attr-defined]
                    st.pyplot(fig)
                    plt.close()
            
            with viz_tabs[1]:
                # KDE Comparison
                if use_cross_comparison and show_kde:
                    fig_kde = create_kde_comparison(
                        fcs_sizes=fcs_sizes,
                        nta_sizes=nta_sizes,
                        fcs_label=f"FCS ({fcs_filename})",
                        nta_label=f"NTA ({nta_filename})",
                        title="Size Distribution (Kernel Density Estimation)",
                        x_range=(min_size_filter, max_size_filter)
                    )
                    st.plotly_chart(fig_kde, width="stretch")
                    render_pin_button("cross_kde_comparison", "Cross-Comparison: KDE Curves", fig_kde, "🔬 Cross-Comparison", "cross2")
                else:
                    st.info("Enable 'Show KDE Overlay' in sidebar to view Kernel Density Estimation curves.")
            
            with viz_tabs[2]:
                # Statistical Comparison
                st.markdown("#### 📈 Statistical Summary")
                
                # Calculate statistics
                fcs_d10 = np.percentile(fcs_sizes, 10)
                fcs_d50 = np.percentile(fcs_sizes, 50)
                fcs_d90 = np.percentile(fcs_sizes, 90)
                fcs_mean = np.mean(fcs_sizes)
                fcs_std = np.std(fcs_sizes)
                
                nta_d10 = np.percentile(nta_sizes, 10)
                nta_d50 = np.percentile(nta_sizes, 50)
                nta_d90 = np.percentile(nta_sizes, 90)
                nta_mean = np.mean(nta_sizes)
                nta_std = np.std(nta_sizes)
                
                # Create comparison DataFrame
                comparison_df = pd.DataFrame({
                    'Metric': ['D10 (nm)', 'D50 (nm)', 'D90 (nm)', 'Mean (nm)', 'Std Dev (nm)', 'Count'],
                    'FCS': [f"{fcs_d10:.1f}", f"{fcs_d50:.1f}", f"{fcs_d90:.1f}", f"{fcs_mean:.1f}", f"{fcs_std:.1f}", f"{len(fcs_sizes):,}"],
                    'NTA': [f"{nta_d10:.1f}", f"{nta_d50:.1f}", f"{nta_d90:.1f}", f"{nta_mean:.1f}", f"{nta_std:.1f}", f"{len(nta_sizes):,}"],
                    'Difference (%)': [
                        f"{abs(fcs_d10 - nta_d10) / ((fcs_d10 + nta_d10) / 2) * 100:.1f}%",
                        f"{abs(fcs_d50 - nta_d50) / ((fcs_d50 + nta_d50) / 2) * 100:.1f}%",
                        f"{abs(fcs_d90 - nta_d90) / ((fcs_d90 + nta_d90) / 2) * 100:.1f}%",
                        f"{abs(fcs_mean - nta_mean) / ((fcs_mean + nta_mean) / 2) * 100:.1f}%",
                        f"{abs(fcs_std - nta_std) / ((fcs_std + nta_std) / 2) * 100:.1f}%",
                        "-"
                    ]
                })
                
                st.dataframe(comparison_df, width="stretch", hide_index=True)
                
                # Statistical tests
                if show_statistics:
                    st.markdown("#### 🧪 Statistical Tests")
                    
                    from scipy import stats as scipy_stats
                    
                    # Kolmogorov-Smirnov test
                    ks_result = scipy_stats.ks_2samp(fcs_sizes, nta_sizes)
                    ks_stat = float(ks_result[0])  # type: ignore[index]
                    ks_pval = float(ks_result[1])  # type: ignore[index]
                    
                    # Mann-Whitney U test
                    mw_result = scipy_stats.mannwhitneyu(fcs_sizes, nta_sizes, alternative='two-sided')
                    mw_stat = float(mw_result[0])  # type: ignore[index]
                    mw_pval = float(mw_result[1])  # type: ignore[index]
                    
                    test_cols = st.columns(2)
                    with test_cols[0]:
                        ks_color = "#10b981" if ks_pval > 0.05 else "#ef4444"
                        st.markdown(f"""
                        <div style='background: #1f2937; border-radius: 12px; padding: 20px; border: 1px solid {ks_color};'>
                            <h4 style='color: #f8fafc;'>Kolmogorov-Smirnov Test</h4>
                            <p style='color: #94a3b8; margin: 5px 0;'>Tests if distributions are different</p>
                            <p style='color: #f8fafc; font-size: 1.2em;'>Statistic: <strong>{ks_stat:.4f}</strong></p>
                            <p style='color: {ks_color}; font-size: 1.2em;'>p-value: <strong>{ks_pval:.2e}</strong></p>
                            <p style='color: #94a3b8;'>{'✅ Distributions appear similar (p > 0.05)' if ks_pval > 0.05 else '⚠️ Distributions appear different (p ≤ 0.05)'}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with test_cols[1]:
                        mw_color = "#10b981" if mw_pval > 0.05 else "#ef4444"
                        st.markdown(f"""
                        <div style='background: #1f2937; border-radius: 12px; padding: 20px; border: 1px solid {mw_color};'>
                            <h4 style='color: #f8fafc;'>Mann-Whitney U Test</h4>
                            <p style='color: #94a3b8; margin: 5px 0;'>Tests if medians are different</p>
                            <p style='color: #f8fafc; font-size: 1.2em;'>Statistic: <strong>{mw_stat:.0f}</strong></p>
                            <p style='color: {mw_color}; font-size: 1.2em;'>p-value: <strong>{mw_pval:.2e}</strong></p>
                            <p style='color: #94a3b8;'>{'✅ Medians appear similar (p > 0.05)' if mw_pval > 0.05 else '⚠️ Medians appear different (p ≤ 0.05)'}</p>
                        </div>
                        """, unsafe_allow_html=True)
            
            with viz_tabs[3]:
                # Discrepancy Analysis
                st.markdown("#### 📉 Discrepancy Analysis")
                
                # Calculate discrepancies
                discrepancies = {
                    'D10': abs(fcs_d10 - nta_d10) / ((fcs_d10 + nta_d10) / 2) * 100,
                    'D50': abs(fcs_d50 - nta_d50) / ((fcs_d50 + nta_d50) / 2) * 100,
                    'D90': abs(fcs_d90 - nta_d90) / ((fcs_d90 + nta_d90) / 2) * 100,
                    'Mean': abs(fcs_mean - nta_mean) / ((fcs_mean + nta_mean) / 2) * 100,
                }
                
                if use_cross_comparison:
                    fcs_vals = {'D10': fcs_d10, 'D50': fcs_d50, 'D90': fcs_d90, 'Mean': fcs_mean}
                    nta_vals = {'D10': nta_d10, 'D50': nta_d50, 'D90': nta_d90, 'Mean': nta_mean}
                    fig_disc = create_discrepancy_chart(
                        fcs_values=fcs_vals,
                        nta_values=nta_vals,
                        threshold_pct=discrepancy_threshold,
                        title="Measurement Discrepancy Analysis"
                    )
                    st.plotly_chart(fig_disc, width="stretch")
                    render_pin_button("cross_discrepancy", "Cross-Comparison: Discrepancy Analysis", fig_disc, "🔬 Cross-Comparison", "cross3")
                else:
                    # Fallback bar chart
                    fig, ax = plt.subplots(figsize=(10, 5))
                    colors = ['#10b981' if v <= discrepancy_threshold else '#ef4444' for v in discrepancies.values()]
                    ax.bar(discrepancies.keys(), discrepancies.values(), color=colors)
                    ax.axhline(y=discrepancy_threshold, color='#ef4444', linestyle='--', label=f'Threshold ({discrepancy_threshold}%)')
                    ax.set_ylabel('Discrepancy (%)')
                    ax.set_title('Measurement Discrepancy Analysis')
                    ax.legend()
                    ax.set_facecolor('#111827')
                    fig.patch.set_facecolor('#111827')  # type: ignore[attr-defined]
                    ax.tick_params(colors='white')
                    ax.xaxis.label.set_color('white')
                    ax.yaxis.label.set_color('white')
                    ax.title.set_color('white')  # type: ignore[attr-defined]
                    st.pyplot(fig)
                    plt.close()
                
                # Summary assessment
                high_discrepancies = [k for k, v in discrepancies.items() if v > discrepancy_threshold]
                if not high_discrepancies:
                    st.success(f"✅ All measurements are within the {discrepancy_threshold}% threshold. Good agreement between instruments!")
                else:
                    st.warning(f"⚠️ The following metrics exceed the {discrepancy_threshold}% threshold: {', '.join(high_discrepancies)}")
                    st.info("""
                    **Possible reasons for discrepancies:**
                    - Different detection principles (light scatter vs. diffusion)
                    - Sample preparation differences
                    - Concentration effects on NTA accuracy
                    - Refractive index assumptions in FCS
                    """)
            
            # Export options
            st.markdown("---")
            st.markdown("### 💾 Export Comparison Results")
            
            export_cols = st.columns(3)
            
            with export_cols[0]:
                # Export comparison table as CSV
                export_df = comparison_df.copy()
                csv_data = export_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "⬇️ Download Comparison Table",
                    data=csv_data,
                    file_name="cross_instrument_comparison.csv",
                    mime="text/csv",
                    width="stretch"
                )
            
            with export_cols[1]:
                # Export combined size data
                combined_sizes = pd.DataFrame({
                    'FCS_Size_nm': pd.Series(fcs_sizes),
                    'NTA_Size_nm': pd.Series(nta_sizes)
                })
                combined_csv = combined_sizes.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "⬇️ Download Size Data",
                    data=combined_csv,
                    file_name="cross_instrument_sizes.csv",
                    mime="text/csv",
                    width="stretch"
                )
            
            with export_cols[2]:
                # Generate comparison report
                report_text = f"""# Cross-Instrument Comparison Report
Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

## Files Compared
- **FCS:** {fcs_filename}
- **NTA:** {nta_filename}

## Size Distribution Statistics

| Metric | FCS | NTA | Difference |
|--------|-----|-----|------------|
| D10 (nm) | {fcs_d10:.1f} | {nta_d10:.1f} | {discrepancies['D10']:.1f}% |
| D50 (nm) | {fcs_d50:.1f} | {nta_d50:.1f} | {discrepancies['D50']:.1f}% |
| D90 (nm) | {fcs_d90:.1f} | {nta_d90:.1f} | {discrepancies['D90']:.1f}% |
| Mean (nm) | {fcs_mean:.1f} | {nta_mean:.1f} | {discrepancies['Mean']:.1f}% |
| Std Dev (nm) | {fcs_std:.1f} | {nta_std:.1f} | - |
| Count | {len(fcs_sizes):,} | {len(nta_sizes):,} | - |

## Assessment
Threshold: {discrepancy_threshold}%
{'✅ All measurements within threshold' if not high_discrepancies else f"⚠️ Exceeds threshold: {', '.join(high_discrepancies)}"}

## Statistical Tests
- Kolmogorov-Smirnov: stat={ks_stat:.4f}, p={ks_pval:.2e}
- Mann-Whitney U: stat={mw_stat:.0f}, p={mw_pval:.2e}
"""
                st.download_button(
                    "📄 Download Report",
                    data=report_text.encode('utf-8'),
                    file_name="cross_instrument_report.md",
                    mime="text/markdown",
                    width="stretch"
                )
        
        else:
            st.warning("Could not extract size data from the loaded datasets. Please check the column selection.")
    
    elif has_fcs_data and not has_nta_data:
        st.info("""
        📊 **FCS data loaded** - Now upload NTA data to enable comparison.
        
        Go to the **⚛ Nanoparticle Tracking** tab to upload NTA data.
        """)
        
        # Show FCS summary
        if 'fcs_data' in st.session_state:
            fcs_df = st.session_state['fcs_data']
            st.markdown("### 🧪 Current FCS Data Summary")
            st.write(f"- **File:** {st.session_state.get('fcs_filename', 'Unknown')}")
            st.write(f"- **Events:** {len(fcs_df):,}")
            st.write(f"- **Columns:** {', '.join(fcs_df.columns[:5])}...")
    
    elif has_nta_data and not has_fcs_data:
        st.info("""
        ⚛ **NTA data loaded** - Now upload FCS data to enable comparison.
        
        Go to the **🧪 Flow Cytometry** tab to upload FCS data.
        """)
        
        # Show NTA summary
        if 'nta_data' in st.session_state:
            nta_df = st.session_state['nta_data']
            st.markdown("### ⚛ Current NTA Data Summary")
            st.write(f"- **File:** {st.session_state.get('nta_filename', 'Unknown')}")
            st.write(f"- **Measurements:** {len(nta_df):,}")
            st.write(f"- **Columns:** {', '.join(nta_df.columns[:5])}...")
    
    else:
        # No data loaded
        st.markdown("""
        <div style='background: #1f2937; border-radius: 16px; padding: 40px; text-align: center; margin: 40px 0;'>
            <h2 style='color: #f8fafc; margin-bottom: 20px;'>📤 Upload Data to Begin</h2>
            <p style='color: #94a3b8; font-size: 1.1em; margin-bottom: 30px;'>
                To compare FCS and NTA measurements, first upload data from both instruments:
            </p>
            <div style='display: flex; justify-content: center; gap: 40px; flex-wrap: wrap;'>
                <div style='background: rgba(0,180,216,0.1); border: 1px solid rgba(0,180,216,0.3); 
                            border-radius: 12px; padding: 25px; width: 280px;'>
                    <h3 style='color: #00b4d8;'>1️⃣ Flow Cytometry</h3>
                    <p style='color: #94a3b8;'>Go to <strong>🧪 Flow Cytometry</strong> tab</p>
                    <p style='color: #64748b;'>Upload .fcs file</p>
                </div>
                <div style='background: rgba(124,58,237,0.1); border: 1px solid rgba(124,58,237,0.3); 
                            border-radius: 12px; padding: 25px; width: 280px;'>
                    <h3 style='color: #7c3aed;'>2️⃣ Nanoparticle Tracking</h3>
                    <p style='color: #94a3b8;'>Go to <strong>⚛ Nanoparticle Tracking</strong> tab</p>
                    <p style='color: #64748b;'>Upload .txt or .csv file</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Best practices for comparison
        with st.expander("📚 Cross-Instrument Comparison Best Practices", expanded=False):
            st.markdown("""
            ### 🎯 Sample Preparation
            - Use the **same sample aliquot** for both instruments when possible
            - Record dilution factors - concentration affects NTA accuracy
            - Note temperature - affects viscosity and diffusion calculations
            
            ### 🔬 Measurement Considerations
            - **FCS (NanoFACS):** Measures light scatter, affected by refractive index
            - **NTA (ZetaView):** Measures Brownian motion, affected by viscosity
            
            ### 📊 Expected Differences
            - D50 values typically agree within **±15%** for homogeneous samples
            - Polydisperse samples may show larger differences
            - Size range sensitivity differs: NTA better at smaller sizes, FCS handles larger particles
            
            ### ⚠️ Common Issues
            1. **Large discrepancies (>20%)**: Check sample preparation, dilution factors
            2. **Bimodal distributions**: May indicate aggregation or heterogeneous populations
            3. **Concentration mismatch**: NTA requires optimal concentration (~10⁷-10⁹ particles/mL)
            """)

