"""
Interactive Plotly Visualization Module
=======================================

Purpose: Provide interactive visualizations for FCS and NTA data analysis

Features:
- Hover tooltips with detailed particle information
- Zoom/pan controls
- Selection tools for gating
- Export to PNG/SVG/PDF
- Dark theme matching the Streamlit UI
- Anomaly highlighting support

Author: CRMIT Team
Date: December 2025
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Optional, List, Dict, Any, Tuple


# =========================================================================
# THEME CONFIGURATION - Matching Streamlit Dark Theme
# =========================================================================

DARK_THEME = {
    'bg_color': '#111827',
    'paper_color': '#111827',
    'grid_color': '#374151',
    'text_color': '#f8fafc',
    'text_secondary': '#94a3b8',
    'primary': '#00b4d8',
    'secondary': '#7c3aed',
    'accent': '#f72585',
    'success': '#10b981',
    'warning': '#f97316',
    'error': '#ef4444',
}

PLOTLY_LAYOUT_TEMPLATE = {
    'plot_bgcolor': DARK_THEME['bg_color'],
    'paper_bgcolor': DARK_THEME['paper_color'],
    'font': {'color': DARK_THEME['text_color'], 'family': 'Inter, sans-serif'},
    'title': {'font': {'size': 16, 'color': DARK_THEME['text_color']}},
    'xaxis': {
        'gridcolor': DARK_THEME['grid_color'],
        'linecolor': DARK_THEME['grid_color'],
        'tickfont': {'color': DARK_THEME['text_secondary']},
        'title': {'font': {'color': DARK_THEME['text_color']}}
    },
    'yaxis': {
        'gridcolor': DARK_THEME['grid_color'],
        'linecolor': DARK_THEME['grid_color'],
        'tickfont': {'color': DARK_THEME['text_secondary']},
        'title': {'font': {'color': DARK_THEME['text_color']}}
    },
    'legend': {
        'bgcolor': 'rgba(31, 41, 55, 0.8)',
        'bordercolor': DARK_THEME['grid_color'],
        'font': {'color': DARK_THEME['text_color']}
    },
    'hoverlabel': {
        'bgcolor': '#1f2937',
        'bordercolor': DARK_THEME['primary'],
        'font': {'color': DARK_THEME['text_color'], 'size': 12}
    }
}


def apply_dark_theme(fig: go.Figure) -> go.Figure:
    """Apply consistent dark theme to a Plotly figure."""
    fig.update_layout(**PLOTLY_LAYOUT_TEMPLATE)
    return fig


# =========================================================================
# SCATTER PLOTS
# =========================================================================

def create_scatter_plot(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    color_col: Optional[str] = None,
    size_col: Optional[str] = None,
    title: str = "Scatter Plot",
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    anomaly_mask: Optional[np.ndarray] = None,
    highlight_anomalies: bool = True,
    max_points: int = 50000,
    opacity: float = 0.6,
    marker_size: int = 5
) -> go.Figure:
    """
    Create an interactive scatter plot with hover details.
    
    Args:
        data: DataFrame with data to plot
        x_col: Column name for X-axis
        y_col: Column name for Y-axis
        color_col: Optional column for color coding
        size_col: Optional column for point sizes
        title: Plot title
        x_label: X-axis label (defaults to column name)
        y_label: Y-axis label (defaults to column name)
        anomaly_mask: Boolean array marking anomalies
        highlight_anomalies: Whether to highlight anomalies in red
        max_points: Maximum points to display (for performance)
        opacity: Point opacity (0-1)
        marker_size: Base marker size
    
    Returns:
        Plotly Figure object
    """
    # Sample data if too large
    if len(data) > max_points:
        sample_idx = np.random.choice(len(data), max_points, replace=False)
        plot_data = data.iloc[sample_idx].copy()
        if anomaly_mask is not None:
            anomaly_mask = anomaly_mask[sample_idx]
        sampled = True
    else:
        plot_data = data.copy()
        sampled = False
    
    fig = go.Figure()
    
    # Build hover template
    hover_cols = [x_col, y_col]
    if 'estimated_diameter_nm' in plot_data.columns:
        hover_cols.append('estimated_diameter_nm')
    if 'measured_ratio' in plot_data.columns:
        hover_cols.append('measured_ratio')
    
    hover_template = "<b>Event Details</b><br>"
    for col in hover_cols:
        if col in plot_data.columns:
            hover_template += f"{col}: %{{customdata[{hover_cols.index(col)}]:.2f}}<br>"
    hover_template += "<extra></extra>"
    
    custom_data = plot_data[hover_cols].values if all(c in plot_data.columns for c in hover_cols) else None
    
    if anomaly_mask is not None and highlight_anomalies:
        # Plot normal points
        normal_mask = ~anomaly_mask
        if normal_mask.sum() > 0:
            fig.add_trace(go.Scattergl(
                x=plot_data.loc[normal_mask, x_col],
                y=plot_data.loc[normal_mask, y_col],
                mode='markers',
                marker=dict(
                    size=marker_size,
                    color=DARK_THEME['secondary'],
                    opacity=opacity
                ),
                name='Normal',
                customdata=custom_data[normal_mask] if custom_data is not None else None,
                hovertemplate=hover_template
            ))
        
        # Plot anomalies
        if anomaly_mask.sum() > 0:
            fig.add_trace(go.Scattergl(
                x=plot_data.loc[anomaly_mask, x_col],
                y=plot_data.loc[anomaly_mask, y_col],
                mode='markers',
                marker=dict(
                    size=marker_size + 3,
                    color=DARK_THEME['error'],
                    symbol='x',
                    line=dict(width=1, color=DARK_THEME['error'])
                ),
                name=f'Anomalies ({anomaly_mask.sum():,})',
                customdata=custom_data[anomaly_mask] if custom_data is not None else None,
                hovertemplate=hover_template
            ))
    else:
        # Single trace without anomaly highlighting
        if color_col and color_col in plot_data.columns:
            fig.add_trace(go.Scattergl(
                x=plot_data[x_col],
                y=plot_data[y_col],
                mode='markers',
                marker=dict(
                    size=marker_size,
                    color=plot_data[color_col],
                    colorscale='Viridis',
                    colorbar=dict(title=color_col),
                    opacity=opacity
                ),
                customdata=custom_data,
                hovertemplate=hover_template
            ))
        else:
            fig.add_trace(go.Scattergl(
                x=plot_data[x_col],
                y=plot_data[y_col],
                mode='markers',
                marker=dict(
                    size=marker_size,
                    color=DARK_THEME['secondary'],
                    opacity=opacity
                ),
                customdata=custom_data,
                hovertemplate=hover_template
            ))
    
    # Update layout
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor='center'),
        xaxis_title=x_label or x_col,
        yaxis_title=y_label or y_col,
        showlegend=anomaly_mask is not None and highlight_anomalies,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99
        ),
        hovermode='closest',
        dragmode='zoom'
    )
    
    # Add annotation if sampled
    if sampled:
        fig.add_annotation(
            text=f"Showing {max_points:,} of {len(data):,} points",
            xref="paper", yref="paper",
            x=0.02, y=0.02,
            showarrow=False,
            font=dict(size=10, color=DARK_THEME['text_secondary']),
            bgcolor='rgba(31, 41, 55, 0.7)'
        )
    
    return apply_dark_theme(fig)


def create_fsc_ssc_scatter(
    data: pd.DataFrame,
    fsc_col: str,
    ssc_col: str,
    anomaly_mask: Optional[np.ndarray] = None,
    highlight_anomalies: bool = True,
    title: str = "FSC vs SSC Scatter Plot"
) -> go.Figure:
    """
    Create FSC vs SSC scatter plot with specialized hover info.
    """
    return create_scatter_plot(
        data=data,
        x_col=fsc_col,
        y_col=ssc_col,
        title=title,
        x_label=f"{fsc_col} (Forward Scatter)",
        y_label=f"{ssc_col} (Side Scatter)",
        anomaly_mask=anomaly_mask,
        highlight_anomalies=highlight_anomalies
    )


def create_size_vs_scatter_plot(
    data: pd.DataFrame,
    scatter_col: str,
    size_col: str = "estimated_diameter_nm",
    anomaly_mask: Optional[np.ndarray] = None,
    highlight_anomalies: bool = True,
    title: str = "Particle Size vs Scatter Intensity"
) -> go.Figure:
    """
    Create size vs scatter intensity plot.
    """
    fig = create_scatter_plot(
        data=data,
        x_col=size_col,
        y_col=scatter_col,
        title=title,
        x_label="Estimated Diameter (nm)",
        y_label=scatter_col,
        anomaly_mask=anomaly_mask,
        highlight_anomalies=highlight_anomalies
    )
    
    # Use green color for normal points
    if anomaly_mask is None or not highlight_anomalies:
        fig.update_traces(marker=dict(color=DARK_THEME['success']))
    else:
        fig.data[0].marker.color = DARK_THEME['success']  # type: ignore[union-attr]
    
    return fig


# =========================================================================
# HISTOGRAMS
# =========================================================================

def create_histogram(
    data: pd.Series,
    title: str = "Distribution",
    x_label: str = "Value",
    y_label: str = "Count",
    nbins: int = 50,
    color: str = None,
    show_stats: bool = True,
    range_x: Optional[Tuple[float, float]] = None
) -> go.Figure:
    """
    Create an interactive histogram with statistics.
    
    Args:
        data: Series of values to plot
        title: Plot title
        x_label: X-axis label
        y_label: Y-axis label
        nbins: Number of bins
        color: Bar color (uses primary theme color if None)
        show_stats: Show mean, median lines
        range_x: Optional x-axis range
    
    Returns:
        Plotly Figure object
    """
    clean_data = data.dropna()
    
    if color is None:
        color = DARK_THEME['primary']
    
    fig = go.Figure()
    
    # Create histogram
    fig.add_trace(go.Histogram(
        x=clean_data,
        nbinsx=nbins,
        marker=dict(
            color=color,
            line=dict(color=DARK_THEME['primary'], width=1)
        ),
        opacity=0.85,
        hovertemplate="Range: %{x}<br>Count: %{y}<extra></extra>"
    ))
    
    # Add statistics lines
    if show_stats and len(clean_data) > 0:
        mean_val = clean_data.mean()
        median_val = clean_data.median()
        
        # Mean line
        fig.add_vline(
            x=mean_val,
            line=dict(color=DARK_THEME['accent'], width=2, dash='dash'),
            annotation=dict(
                text=f"Mean: {mean_val:.1f}",
                font=dict(color=DARK_THEME['accent'], size=11),
                bgcolor='rgba(31, 41, 55, 0.8)'
            )
        )
        
        # Median line
        fig.add_vline(
            x=median_val,
            line=dict(color=DARK_THEME['success'], width=2, dash='dot'),
            annotation=dict(
                text=f"Median: {median_val:.1f}",
                font=dict(color=DARK_THEME['success'], size=11),
                yshift=-20,
                bgcolor='rgba(31, 41, 55, 0.8)'
            )
        )
    
    # Update layout
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor='center'),
        xaxis_title=x_label,
        yaxis_title=y_label,
        bargap=0.05,
        hovermode='x unified'
    )
    
    if range_x:
        fig.update_xaxes(range=range_x)
    
    return apply_dark_theme(fig)


def create_size_distribution_histogram(
    data: pd.DataFrame,
    size_col: str = "estimated_diameter_nm",
    nbins: int = 50,
    title: str = "Particle Size Distribution",
    show_size_ranges: bool = True,
    size_ranges: Optional[List[Dict]] = None
) -> go.Figure:
    """
    Create particle size distribution histogram with optional range highlighting.
    
    Args:
        data: DataFrame with size data
        size_col: Column containing size values
        nbins: Number of histogram bins
        title: Plot title
        show_size_ranges: Whether to show size range annotations
        size_ranges: List of dicts with 'name', 'min', 'max' for each range
    
    Returns:
        Plotly Figure object
    """
    sizes = data[size_col].dropna()
    
    fig = create_histogram(
        data=sizes,
        title=title,
        x_label="Estimated Diameter (nm)",
        y_label="Particle Count",
        nbins=nbins
    )
    
    # Add size range annotations if provided
    if show_size_ranges and size_ranges:
        colors = ['rgba(103, 126, 234, 0.2)', 'rgba(118, 75, 162, 0.2)', 
                  'rgba(249, 115, 22, 0.2)', 'rgba(16, 185, 129, 0.2)']
        
        for i, sr in enumerate(size_ranges[:4]):  # Max 4 ranges
            fig.add_vrect(
                x0=sr['min'],
                x1=sr['max'],
                fillcolor=colors[i % len(colors)],
                layer='below',
                line_width=0,
                annotation=dict(
                    text=sr['name'],
                    font=dict(size=10, color=DARK_THEME['text_secondary']),
                    textangle=-90,
                    yanchor='bottom'
                ),
                annotation_position='top left'
            )
    
    return fig


# =========================================================================
# THEORETICAL VS MEASURED PLOTS
# =========================================================================

def create_theoretical_vs_measured_plot(
    diameters: np.ndarray,
    theoretical_ratios: np.ndarray,
    measured_data: pd.DataFrame,
    diameter_col: str = "estimated_diameter_nm",
    ratio_col: str = "measured_ratio",
    title: str = "Theoretical vs Measured FSC/SSC Ratio"
) -> go.Figure:
    """
    Create plot comparing theoretical Mie scattering curve with measured data.
    
    Args:
        diameters: Array of diameter values for theoretical curve
        theoretical_ratios: Array of theoretical FSC/SSC ratios
        measured_data: DataFrame with measured data
        diameter_col: Column with diameter values
        ratio_col: Column with ratio values
        title: Plot title
    
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    # Theoretical curve
    fig.add_trace(go.Scatter(
        x=diameters,
        y=theoretical_ratios,
        mode='lines',
        name='Theoretical (Mie)',
        line=dict(color=DARK_THEME['primary'], width=3),
        hovertemplate="Diameter: %{x:.1f} nm<br>Ratio: %{y:.4f}<extra>Theoretical</extra>"
    ))
    
    # Measured points
    measured = measured_data.dropna(subset=[diameter_col, ratio_col])
    if not measured.empty:
        # Sample if too many points
        if len(measured) > 10000:
            sample_idx = np.random.choice(len(measured), 10000, replace=False)
            measured = measured.iloc[sample_idx]
        
        fig.add_trace(go.Scattergl(
            x=measured[diameter_col],
            y=measured[ratio_col],
            mode='markers',
            name='Measured Events',
            marker=dict(
                size=5,
                color=DARK_THEME['accent'],
                opacity=0.5
            ),
            hovertemplate="Diameter: %{x:.1f} nm<br>Ratio: %{y:.4f}<extra>Measured</extra>"
        ))
    
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor='center'),
        xaxis_title="Diameter (nm)",
        yaxis_title="FSC/SSC Ratio",
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99
        ),
        hovermode='closest'
    )
    
    return apply_dark_theme(fig)


# =========================================================================
# COMPARISON / OVERLAY PLOTS
# =========================================================================

def create_size_distribution_overlay(
    fcs_sizes: pd.Series,
    nta_sizes: pd.Series,
    fcs_label: str = "NanoFACS",
    nta_label: str = "NTA",
    title: str = "Size Distribution Comparison: FCS vs NTA",
    nbins: int = 50
) -> go.Figure:
    """
    Create overlay comparison of FCS and NTA size distributions.
    
    Args:
        fcs_sizes: Series of FCS particle sizes
        nta_sizes: Series of NTA particle sizes
        fcs_label: Label for FCS data
        nta_label: Label for NTA data
        title: Plot title
        nbins: Number of bins for histograms
    
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    # FCS histogram
    fig.add_trace(go.Histogram(
        x=fcs_sizes.dropna(),
        nbinsx=nbins,
        name=fcs_label,
        marker=dict(color='rgba(0, 180, 216, 0.6)'),
        hovertemplate=f"{fcs_label}<br>Size: %{{x}} nm<br>Count: %{{y}}<extra></extra>"
    ))
    
    # NTA histogram
    fig.add_trace(go.Histogram(
        x=nta_sizes.dropna(),
        nbinsx=nbins,
        name=nta_label,
        marker=dict(color='rgba(16, 185, 129, 0.6)'),
        hovertemplate=f"{nta_label}<br>Size: %{{x}} nm<br>Count: %{{y}}<extra></extra>"
    ))
    
    # Statistics annotations
    fcs_mean = fcs_sizes.mean()
    nta_mean = nta_sizes.mean()
    
    fig.add_annotation(
        text=f"{fcs_label} Mean: {fcs_mean:.1f} nm | {nta_label} Mean: {nta_mean:.1f} nm",
        xref="paper", yref="paper",
        x=0.5, y=1.05,
        showarrow=False,
        font=dict(size=12, color=DARK_THEME['text_color']),
        bgcolor='rgba(31, 41, 55, 0.8)'
    )
    
    fig.update_layout(
        barmode='overlay',
        title=dict(text=title, x=0.5, xanchor='center'),
        xaxis_title="Particle Size (nm)",
        yaxis_title="Count",
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99
        ),
        hovermode='x unified'
    )
    
    return apply_dark_theme(fig)


# =========================================================================
# MULTI-PANEL FIGURES
# =========================================================================

def create_analysis_dashboard(
    data: pd.DataFrame,
    fsc_col: str,
    ssc_col: str,
    size_col: str = "estimated_diameter_nm",
    anomaly_mask: Optional[np.ndarray] = None,
    highlight_anomalies: bool = True
) -> go.Figure:
    """
    Create a multi-panel analysis dashboard.
    
    Args:
        data: DataFrame with analysis data
        fsc_col: FSC column name
        ssc_col: SSC column name
        size_col: Size column name
        anomaly_mask: Boolean array for anomaly highlighting
        highlight_anomalies: Whether to show anomalies
    
    Returns:
        Plotly Figure with 2x2 subplot layout
    """
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "<b>FSC vs SSC Scatter</b>",
            "<b>Size Distribution</b>",
            "<b>Size vs SSC</b>",
            "<b>Size Statistics</b>"
        ),
        specs=[
            [{"type": "scattergl"}, {"type": "histogram"}],
            [{"type": "scattergl"}, {"type": "table"}]
        ],
        vertical_spacing=0.18,
        horizontal_spacing=0.12
    )
    
    # Panel 1: FSC vs SSC
    if anomaly_mask is not None and highlight_anomalies:
        normal_mask = ~anomaly_mask
        fig.add_trace(
            go.Scattergl(
                x=data.loc[normal_mask, fsc_col],
                y=data.loc[normal_mask, ssc_col],
                mode='markers',
                marker=dict(size=3, color=DARK_THEME['secondary'], opacity=0.4),
                name='Normal',
                showlegend=True,
                hovertemplate=f'{fsc_col}: %{{x:.0f}}<br>{ssc_col}: %{{y:.0f}}<extra>Normal</extra>'
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Scattergl(
                x=data.loc[anomaly_mask, fsc_col],
                y=data.loc[anomaly_mask, ssc_col],
                mode='markers',
                marker=dict(size=5, color=DARK_THEME['error'], symbol='x'),
                name='Anomalies',
                showlegend=True,
                hovertemplate=f'{fsc_col}: %{{x:.0f}}<br>{ssc_col}: %{{y:.0f}}<extra>Anomaly</extra>'
            ),
            row=1, col=1
        )
    else:
        fig.add_trace(
            go.Scattergl(
                x=data[fsc_col],
                y=data[ssc_col],
                mode='markers',
                marker=dict(size=3, color=DARK_THEME['secondary'], opacity=0.4),
                showlegend=False,
                hovertemplate=f'{fsc_col}: %{{x:.0f}}<br>{ssc_col}: %{{y:.0f}}<extra></extra>'
            ),
            row=1, col=1
        )
    
    # Panel 2: Size Distribution
    sizes = data[size_col].dropna()
    fig.add_trace(
        go.Histogram(
            x=sizes,
            nbinsx=40,
            marker=dict(color=DARK_THEME['primary'], line=dict(color='#0096c7', width=1)),
            showlegend=False,
            hovertemplate='Size: %{x:.1f} nm<br>Count: %{y}<extra></extra>'
        ),
        row=1, col=2
    )
    
    # Panel 3: Size vs SSC
    if anomaly_mask is not None and highlight_anomalies:
        fig.add_trace(
            go.Scattergl(
                x=data.loc[normal_mask, size_col],
                y=data.loc[normal_mask, ssc_col],
                mode='markers',
                marker=dict(size=3, color=DARK_THEME['success'], opacity=0.4),
                showlegend=False,
                hovertemplate='Size: %{x:.1f} nm<br>SSC: %{y:.0f}<extra></extra>'
            ),
            row=2, col=1
        )
        fig.add_trace(
            go.Scattergl(
                x=data.loc[anomaly_mask, size_col],
                y=data.loc[anomaly_mask, ssc_col],
                mode='markers',
                marker=dict(size=5, color=DARK_THEME['error'], symbol='x'),
                showlegend=False,
                hovertemplate='Size: %{x:.1f} nm<br>SSC: %{y:.0f}<extra>Anomaly</extra>'
            ),
            row=2, col=1
        )
    else:
        fig.add_trace(
            go.Scattergl(
                x=data[size_col],
                y=data[ssc_col],
                mode='markers',
                marker=dict(size=3, color=DARK_THEME['success'], opacity=0.4),
                showlegend=False,
                hovertemplate='Size: %{x:.1f} nm<br>SSC: %{y:.0f}<extra></extra>'
            ),
            row=2, col=1
        )
    
    # Panel 4: Statistics Table - Median is primary metric (per Surya's feedback Dec 2025)
    stats_data = {
        'Metric': ['Count', 'Median (nm)', 'D50 (nm)', 'Std Dev', 'Min (nm)', 'Max (nm)'],
        'Value': [
            f"{len(sizes):,}",
            f"{sizes.median():.1f}",
            f"{np.percentile(sizes, 50):.1f}",
            f"{sizes.std():.1f}",
            f"{sizes.min():.1f}",
            f"{sizes.max():.1f}"
        ]
    }
    
    fig.add_trace(
        go.Table(
            header=dict(
                values=['<b>Metric</b>', '<b>Value</b>'],
                fill_color=DARK_THEME['grid_color'],
                font=dict(color=DARK_THEME['text_color'], size=13),
                align='left',
                height=30
            ),
            cells=dict(
                values=[stats_data['Metric'], stats_data['Value']],
                fill_color=DARK_THEME['bg_color'],
                font=dict(color=DARK_THEME['text_color'], size=12),
                align='left',
                height=28
            )
        ),
        row=2, col=2
    )
    
    # Update axes labels with proper font size
    fig.update_xaxes(title_text=fsc_col, title_font_size=11, row=1, col=1)
    fig.update_yaxes(title_text=ssc_col, title_font_size=11, row=1, col=1)
    fig.update_xaxes(title_text="Diameter (nm)", title_font_size=11, row=1, col=2)
    fig.update_yaxes(title_text="Count", title_font_size=11, row=1, col=2)
    fig.update_xaxes(title_text="Diameter (nm)", title_font_size=11, row=2, col=1)
    fig.update_yaxes(title_text=ssc_col, title_font_size=11, row=2, col=1)
    
    # Update subplot title annotations for better positioning
    annotations = fig.layout.annotations
    if annotations:
        for annotation in annotations:
            annotation.font = dict(size=13, color=DARK_THEME['text_color'])
            if annotation.y is not None:
                annotation.y = annotation.y + 0.02  # Move titles up slightly
    
    fig.update_layout(
        height=800,
        title=dict(
            text="<b>Flow Cytometry Analysis Dashboard</b>",
            x=0.5,
            xanchor='center',
            font=dict(size=18, color=DARK_THEME['text_color'])
        ),
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.45,
            bgcolor='rgba(31, 41, 55, 0.8)',
            bordercolor=DARK_THEME['grid_color'],
            font=dict(size=11)
        ),
        margin=dict(t=80, b=60, l=60, r=60),
        dragmode='zoom',  # Enable zoom by default
        hovermode='closest'
    )
    
    return apply_dark_theme(fig)


# =========================================================================
# UTILITY FUNCTIONS
# =========================================================================

def get_export_config() -> Dict[str, Any]:
    """Get configuration for plot export buttons and interactivity."""
    return {
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'ev_analysis_plot',
            'height': 800,
            'width': 1200,
            'scale': 2
        },
        'displaylogo': False,
        'displayModeBar': True,  # Always show the mode bar
        'scrollZoom': True,  # Enable scroll to zoom
        'modeBarButtonsToAdd': [
            'drawline',
            'drawrect',
            'eraseshape',
            'select2d',
            'lasso2d',
            'zoomIn2d',
            'zoomOut2d',
            'autoScale2d',
            'resetScale2d'
        ],
        'modeBarButtonsToRemove': []
    }


def create_empty_plot_placeholder(
    title: str = "No Data Available",
    message: str = "Upload data to generate visualization"
) -> go.Figure:
    """Create a placeholder figure when no data is available."""
    fig = go.Figure()
    
    fig.add_annotation(
        text=f"<b>{title}</b><br>{message}",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=16, color=DARK_THEME['text_secondary']),
        align='center'
    )
    
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=400
    )
    
    return apply_dark_theme(fig)


# =========================================================================
# NTA (Nanoparticle Tracking Analysis) INTERACTIVE PLOTS
# =========================================================================

def create_nta_size_distribution(
    size_data: np.ndarray,
    nbins: int = 20,
    title: str = "Particle Size Distribution",
    show_percentiles: bool = True,
    corrected: bool = False
) -> go.Figure:
    """
    Create an interactive NTA size distribution histogram with percentile markers.
    
    Args:
        size_data: Array of particle sizes in nm
        nbins: Number of histogram bins
        title: Plot title
        show_percentiles: Whether to show D10, D50, D90 lines
        corrected: Whether this is corrected data (affects title suffix)
    
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    # Add histogram
    fig.add_trace(go.Histogram(
        x=size_data,
        nbinsx=nbins,
        marker=dict(
            color=DARK_THEME['primary'],
            line=dict(color='#0096c7', width=1)
        ),
        opacity=0.85,
        name='Size Distribution',
        hovertemplate='Size: %{x:.1f} nm<br>Count: %{y}<extra></extra>'
    ))
    
    # Add percentile lines
    if show_percentiles and len(size_data) > 0:
        d10 = np.percentile(size_data, 10)
        d50 = np.percentile(size_data, 50)
        d90 = np.percentile(size_data, 90)
        
        fig.add_vline(x=d10, line_dash="dash", line_color=DARK_THEME['success'], 
                      line_width=2, annotation_text=f"D10: {d10:.1f} nm", 
                      annotation_position="top right",
                      annotation_font_color=DARK_THEME['success'])
        
        fig.add_vline(x=d50, line_dash="solid", line_color=DARK_THEME['accent'], 
                      line_width=3, annotation_text=f"D50: {d50:.1f} nm", 
                      annotation_position="top",
                      annotation_font_color=DARK_THEME['accent'])
        
        fig.add_vline(x=d90, line_dash="dash", line_color=DARK_THEME['warning'], 
                      line_width=2, annotation_text=f"D90: {d90:.1f} nm", 
                      annotation_position="top left",
                      annotation_font_color=DARK_THEME['warning'])
    
    title_suffix = " (Corrected)" if corrected else ""
    
    fig.update_layout(
        title=dict(text=f"{title}{title_suffix}", x=0.5, xanchor='center'),
        xaxis_title="Particle Size (nm)",
        yaxis_title="Count",
        height=450,
        bargap=0.05,
        showlegend=False
    )
    
    return apply_dark_theme(fig)


def create_nta_concentration_profile(
    position_data: np.ndarray,
    concentration_data: np.ndarray,
    title: str = "Concentration by Position"
) -> go.Figure:
    """
    Create an interactive concentration profile bar chart.
    
    Args:
        position_data: Array of position values
        concentration_data: Array of concentration values (p/mL)
        title: Plot title
    
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=position_data,
        y=concentration_data,
        marker=dict(
            color=DARK_THEME['secondary'],
            line=dict(color='#a78bfa', width=1)
        ),
        opacity=0.85,
        name='Concentration',
        hovertemplate='Position: %{x}<br>Concentration: %{y:.2e} p/mL<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor='center'),
        xaxis_title="Position",
        yaxis_title="Concentration (p/mL)",
        height=450,
        yaxis=dict(exponentformat='e')
    )
    
    return apply_dark_theme(fig)


def create_theoretical_curve(
    diameters: np.ndarray,
    theoretical_ratios: np.ndarray,
    title: str = "Theoretical FSC/SSC Ratio Curve"
) -> go.Figure:
    """
    Create an interactive theoretical FSC/SSC ratio curve for Mie scattering.
    
    Args:
        diameters: Array of particle diameters (nm)
        theoretical_ratios: Array of theoretical FSC/SSC ratios
        title: Plot title
    
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=diameters,
        y=theoretical_ratios,
        mode='lines',
        line=dict(color=DARK_THEME['accent'], width=3),
        name='Theoretical Ratio',
        hovertemplate='Diameter: %{x:.1f} nm<br>FSC/SSC: %{y:.4f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor='center'),
        xaxis_title="Diameter (nm)",
        yaxis_title="FSC/SSC Ratio",
        height=400,
        hovermode='x unified'
    )
    
    return apply_dark_theme(fig)


def create_nta_raw_vs_corrected(
    raw_sizes: np.ndarray,
    corrected_sizes: np.ndarray,
    nbins: int = 30,
    title: str = "Raw vs Corrected Size Distribution"
) -> go.Figure:
    """
    Create an interactive overlay of raw and corrected NTA size distributions.
    
    Args:
        raw_sizes: Array of raw (uncorrected) particle sizes
        corrected_sizes: Array of corrected particle sizes
        nbins: Number of histogram bins
        title: Plot title
    
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    # Raw distribution
    fig.add_trace(go.Histogram(
        x=raw_sizes,
        nbinsx=nbins,
        marker=dict(color=DARK_THEME['text_secondary'], line=dict(width=1)),
        opacity=0.5,
        name='Raw Sizes',
        hovertemplate='Size: %{x:.1f} nm<br>Count: %{y}<extra>Raw</extra>'
    ))
    
    # Corrected distribution
    fig.add_trace(go.Histogram(
        x=corrected_sizes,
        nbinsx=nbins,
        marker=dict(color=DARK_THEME['primary'], line=dict(width=1)),
        opacity=0.7,
        name='Corrected Sizes',
        hovertemplate='Size: %{x:.1f} nm<br>Count: %{y}<extra>Corrected</extra>'
    ))
    
    # Add median lines
    raw_median = np.median(raw_sizes)
    corr_median = np.median(corrected_sizes)
    
    fig.add_vline(x=raw_median, line_dash="dash", line_color=DARK_THEME['text_secondary'], 
                  line_width=2, annotation_text=f"Raw D50: {raw_median:.1f}", 
                  annotation_position="top left")
    
    fig.add_vline(x=corr_median, line_dash="dash", line_color=DARK_THEME['accent'], 
                  line_width=2, annotation_text=f"Corrected D50: {corr_median:.1f}", 
                  annotation_position="top right")
    
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor='center'),
        xaxis_title="Particle Size (nm)",
        yaxis_title="Count",
        height=450,
        barmode='overlay',
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
    )
    
    return apply_dark_theme(fig)
