"""
Cross-Instrument Comparison Visualization Module
================================================

Purpose: Create visualizations for comparing FCS and NTA data from the same sample

Features:
- Side-by-side size distribution overlays
- Correlation scatter plots
- Discrepancy highlighting
- Statistical comparison tables
- Multi-sample comparison grids

Author: CRMIT Team
Date: December 2025
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Optional, List, Dict, Any, Tuple
from scipy import stats


# =========================================================================
# THEME CONFIGURATION - Matching Streamlit Dark Theme
# =========================================================================

DARK_THEME = {
    'bg_color': '#111827',
    'paper_color': '#111827',
    'grid_color': '#374151',
    'text_color': '#f8fafc',
    'text_secondary': '#94a3b8',
    'primary': '#00b4d8',      # FCS color
    'secondary': '#7c3aed',    # NTA color
    'accent': '#f72585',
    'success': '#10b981',
    'warning': '#f97316',
    'error': '#ef4444',
    'fcs_color': '#00b4d8',    # Cyan for FCS
    'nta_color': '#7c3aed',    # Purple for NTA
}


def apply_dark_theme(fig: go.Figure) -> go.Figure:
    """Apply consistent dark theme to a Plotly figure."""
    fig.update_layout(
        plot_bgcolor=DARK_THEME['bg_color'],
        paper_bgcolor=DARK_THEME['paper_color'],
        font=dict(color=DARK_THEME['text_color'], family='Inter, sans-serif'),
        xaxis=dict(
            gridcolor=DARK_THEME['grid_color'],
            linecolor=DARK_THEME['grid_color'],
            tickfont=dict(color=DARK_THEME['text_secondary']),
            title=dict(font=dict(color=DARK_THEME['text_color']))
        ),
        yaxis=dict(
            gridcolor=DARK_THEME['grid_color'],
            linecolor=DARK_THEME['grid_color'],
            tickfont=dict(color=DARK_THEME['text_secondary']),
            title=dict(font=dict(color=DARK_THEME['text_color']))
        ),
        legend=dict(
            bgcolor='rgba(31, 41, 55, 0.8)',
            bordercolor=DARK_THEME['grid_color'],
            font=dict(color=DARK_THEME['text_color'])
        ),
        hoverlabel=dict(
            bgcolor='#1f2937',
            bordercolor=DARK_THEME['primary'],
            font=dict(color=DARK_THEME['text_color'], size=12)
        )
    )
    return fig


# =========================================================================
# OVERLAY SIZE DISTRIBUTION COMPARISON
# =========================================================================

def create_size_overlay_histogram(
    fcs_sizes: np.ndarray,
    nta_sizes: np.ndarray,
    fcs_label: str = "FCS",
    nta_label: str = "NTA",
    title: str = "Size Distribution Comparison",
    bin_size: float = 5.0,
    normalize: bool = True
) -> go.Figure:
    """
    Create overlaid histogram comparing FCS and NTA size distributions.
    
    Args:
        fcs_sizes: Array of particle sizes from FCS (nm)
        nta_sizes: Array of particle sizes from NTA (nm)
        fcs_label: Label for FCS data
        nta_label: Label for NTA data
        title: Plot title
        bin_size: Histogram bin width in nm
        normalize: If True, show as probability density
    
    Returns:
        Plotly Figure with overlaid histograms
    """
    fig = go.Figure()
    
    # Compute common bin range
    all_sizes = np.concatenate([fcs_sizes, nta_sizes])
    min_size = max(0, np.min(all_sizes) - bin_size)
    max_size = np.max(all_sizes) + bin_size
    nbins = int((max_size - min_size) / bin_size)
    
    histnorm = 'probability density' if normalize else None
    
    # FCS histogram
    fig.add_trace(go.Histogram(
        x=fcs_sizes,
        name=fcs_label,
        marker_color=DARK_THEME['fcs_color'],
        opacity=0.6,
        nbinsx=nbins,
        histnorm=histnorm,
        hovertemplate=(
            f"<b>{fcs_label}</b><br>"
            "Size: %{x:.1f} nm<br>"
            "Count: %{y:.4f}<extra></extra>"
        )
    ))
    
    # NTA histogram
    fig.add_trace(go.Histogram(
        x=nta_sizes,
        name=nta_label,
        marker_color=DARK_THEME['nta_color'],
        opacity=0.6,
        nbinsx=nbins,
        histnorm=histnorm,
        hovertemplate=(
            f"<b>{nta_label}</b><br>"
            "Size: %{x:.1f} nm<br>"
            "Count: %{y:.4f}<extra></extra>"
        )
    ))
    
    # Add vertical lines for medians
    fcs_median = np.median(fcs_sizes)
    nta_median = np.median(nta_sizes)
    
    fig.add_vline(
        x=fcs_median,
        line_dash="dash",
        line_color=DARK_THEME['fcs_color'],
        annotation_text=f"FCS D50: {fcs_median:.1f} nm",
        annotation_position="top"
    )
    
    fig.add_vline(
        x=nta_median,
        line_dash="dash",
        line_color=DARK_THEME['nta_color'],
        annotation_text=f"NTA D50: {nta_median:.1f} nm",
        annotation_position="bottom"
    )
    
    fig.update_layout(
        title=dict(text=title, x=0.5),
        xaxis_title="Particle Size (nm)",
        yaxis_title="Probability Density" if normalize else "Count",
        barmode='overlay',
        legend=dict(x=0.85, y=0.95),
        height=500
    )
    
    return apply_dark_theme(fig)


def create_kde_comparison(
    fcs_sizes: np.ndarray,
    nta_sizes: np.ndarray,
    fcs_label: str = "FCS",
    nta_label: str = "NTA",
    title: str = "Size Distribution (KDE)",
    x_range: Tuple[float, float] = (0, 300)
) -> go.Figure:
    """
    Create KDE (Kernel Density Estimation) comparison plot.
    
    Args:
        fcs_sizes: Array of particle sizes from FCS (nm)
        nta_sizes: Array of particle sizes from NTA (nm)
        fcs_label: Label for FCS data
        nta_label: Label for NTA data
        title: Plot title
        x_range: X-axis range (min, max)
    
    Returns:
        Plotly Figure with KDE curves
    """
    fig = go.Figure()
    
    # Generate KDE for both
    x_eval = np.linspace(x_range[0], x_range[1], 500)
    
    # FCS KDE
    try:
        fcs_kde = stats.gaussian_kde(fcs_sizes)
        fcs_density = fcs_kde(x_eval)
        
        fig.add_trace(go.Scatter(
            x=x_eval,
            y=fcs_density,
            name=fcs_label,
            line=dict(color=DARK_THEME['fcs_color'], width=3),
            fill='tozeroy',
            fillcolor=f"rgba(0, 180, 216, 0.3)",
            hovertemplate=(
                f"<b>{fcs_label}</b><br>"
                "Size: %{x:.1f} nm<br>"
                "Density: %{y:.4f}<extra></extra>"
            )
        ))
    except Exception:
        pass
    
    # NTA KDE
    try:
        nta_kde = stats.gaussian_kde(nta_sizes)
        nta_density = nta_kde(x_eval)
        
        fig.add_trace(go.Scatter(
            x=x_eval,
            y=nta_density,
            name=nta_label,
            line=dict(color=DARK_THEME['nta_color'], width=3),
            fill='tozeroy',
            fillcolor=f"rgba(124, 58, 237, 0.3)",
            hovertemplate=(
                f"<b>{nta_label}</b><br>"
                "Size: %{x:.1f} nm<br>"
                "Density: %{y:.4f}<extra></extra>"
            )
        ))
    except Exception:
        pass
    
    # Add D50 lines
    fcs_d50 = np.median(fcs_sizes)
    nta_d50 = np.median(nta_sizes)
    
    fig.add_vline(
        x=fcs_d50,
        line_dash="dash",
        line_color=DARK_THEME['fcs_color'],
        annotation_text=f"FCS D50: {fcs_d50:.1f} nm"
    )
    
    fig.add_vline(
        x=nta_d50,
        line_dash="dash",
        line_color=DARK_THEME['nta_color'],
        annotation_text=f"NTA D50: {nta_d50:.1f} nm"
    )
    
    fig.update_layout(
        title=dict(text=title, x=0.5),
        xaxis_title="Particle Size (nm)",
        yaxis_title="Density",
        legend=dict(x=0.85, y=0.95),
        height=450
    )
    
    return apply_dark_theme(fig)


# =========================================================================
# CORRELATION SCATTER PLOT
# =========================================================================

def create_correlation_scatter(
    fcs_values: np.ndarray,
    nta_values: np.ndarray,
    sample_labels: Optional[List[str]] = None,
    x_label: str = "FCS Value",
    y_label: str = "NTA Value",
    title: str = "FCS vs NTA Correlation",
    show_regression: bool = True,
    show_identity: bool = True
) -> Tuple[go.Figure, Dict[str, float]]:
    """
    Create correlation scatter plot between FCS and NTA measurements.
    
    Args:
        fcs_values: Array of FCS measurements
        nta_values: Array of NTA measurements
        sample_labels: Optional labels for each point
        x_label: X-axis label
        y_label: Y-axis label
        title: Plot title
        show_regression: Show linear regression line
        show_identity: Show y=x identity line
    
    Returns:
        Tuple of (Plotly Figure, correlation statistics dict)
    """
    fig = go.Figure()
    
    # Calculate correlation statistics
    mask = ~(np.isnan(fcs_values) | np.isnan(nta_values))
    fcs_clean = fcs_values[mask]
    nta_clean = nta_values[mask]
    
    if len(fcs_clean) < 2:
        # Not enough data
        fig.add_annotation(
            text="Insufficient data for correlation",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color=DARK_THEME['warning'])
        )
        return apply_dark_theme(fig), {}
    
    # Pearson correlation
    pearson_result = stats.pearsonr(fcs_clean, nta_clean)
    r_val = float(pearson_result[0])
    p_val = float(pearson_result[1])
    
    # Linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(fcs_clean, nta_clean)
    
    # Calculate % difference
    pct_diff = np.mean(np.abs(fcs_clean - nta_clean) / ((fcs_clean + nta_clean) / 2)) * 100
    
    # Scatter points
    hover_text = sample_labels if sample_labels else [f"Sample {i+1}" for i in range(len(fcs_clean))]
    
    fig.add_trace(go.Scatter(
        x=fcs_clean,
        y=nta_clean,
        mode='markers',
        name='Samples',
        marker=dict(
            size=12,
            color=DARK_THEME['primary'],
            line=dict(width=1, color=DARK_THEME['text_color']),
            opacity=0.8
        ),
        text=hover_text,
        hovertemplate=(
            "<b>%{text}</b><br>"
            f"{x_label}: %{{x:.2f}}<br>"
            f"{y_label}: %{{y:.2f}}<extra></extra>"
        )
    ))
    
    # Identity line (y = x)
    if show_identity:
        min_val = min(fcs_clean.min(), nta_clean.min())
        max_val = max(fcs_clean.max(), nta_clean.max())
        
        fig.add_trace(go.Scatter(
            x=[min_val, max_val],
            y=[min_val, max_val],
            mode='lines',
            name='Identity (y=x)',
            line=dict(color=DARK_THEME['text_secondary'], dash='dot', width=2),
            hoverinfo='skip'
        ))
    
    # Regression line
    if show_regression:
        x_line = np.linspace(fcs_clean.min(), fcs_clean.max(), 100)
        y_line = slope * x_line + intercept
        
        fig.add_trace(go.Scatter(
            x=x_line,
            y=y_line,
            mode='lines',
            name=f'Regression (R²={r_val**2:.3f})',
            line=dict(color=DARK_THEME['accent'], width=2),
            hoverinfo='skip'
        ))
    
    # Add annotation with stats
    stats_text = (
        f"Pearson r = {r_val:.3f}<br>"
        f"R² = {r_val**2:.3f}<br>"
        f"p-value = {p_val:.2e}<br>"
        f"Mean Δ = {pct_diff:.1f}%"
    )
    
    fig.add_annotation(
        x=0.02,
        y=0.98,
        xref='paper',
        yref='paper',
        text=stats_text,
        showarrow=False,
        font=dict(size=12, color=DARK_THEME['text_color']),
        align='left',
        bgcolor='rgba(31, 41, 55, 0.8)',
        bordercolor=DARK_THEME['grid_color'],
        borderwidth=1,
        borderpad=8
    )
    
    fig.update_layout(
        title=dict(text=title, x=0.5),
        xaxis_title=x_label,
        yaxis_title=y_label,
        legend=dict(x=0.7, y=0.15),
        height=500
    )
    
    correlation_stats = {
        'pearson_r': r_val,
        'r_squared': r_val**2,
        'p_value': p_val,
        'slope': slope,
        'intercept': intercept,
        'mean_pct_diff': pct_diff,
        'n_samples': len(fcs_clean)
    }
    
    return apply_dark_theme(fig), correlation_stats


# =========================================================================
# SIDE-BY-SIDE COMPARISON DASHBOARD
# =========================================================================

def create_comparison_dashboard(
    fcs_data: Dict[str, Any],
    nta_data: Dict[str, Any],
    sample_name: str = "Sample"
) -> go.Figure:
    """
    Create a 2x2 dashboard comparing FCS and NTA data.
    
    Args:
        fcs_data: Dictionary with FCS statistics (sizes, mean, median, events)
        nta_data: Dictionary with NTA statistics (sizes, d50, concentration)
        sample_name: Name of the sample being compared
    
    Returns:
        Plotly Figure with 4-panel dashboard
    """
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Size Distribution Overlay",
            "D-Value Comparison",
            "Event/Particle Counts",
            "Size Statistics Comparison"
        ),
        specs=[
            [{"type": "histogram"}, {"type": "bar"}],
            [{"type": "bar"}, {"type": "bar"}]
        ],
        vertical_spacing=0.15,
        horizontal_spacing=0.12
    )
    
    # Panel 1: Size Distribution Overlay
    if 'sizes' in fcs_data and len(fcs_data['sizes']) > 0:
        fig.add_trace(go.Histogram(
            x=fcs_data['sizes'],
            name='FCS Sizes',
            marker_color=DARK_THEME['fcs_color'],
            opacity=0.6,
            nbinsx=50
        ), row=1, col=1)
    
    if 'sizes' in nta_data and len(nta_data['sizes']) > 0:
        fig.add_trace(go.Histogram(
            x=nta_data['sizes'],
            name='NTA Sizes',
            marker_color=DARK_THEME['nta_color'],
            opacity=0.6,
            nbinsx=50
        ), row=1, col=1)
    
    # Panel 2: D-Value Comparison (D10, D50, D90)
    d_values = ['D10', 'D50', 'D90']
    fcs_d_values = [fcs_data.get('d10', 0), fcs_data.get('d50', 0), fcs_data.get('d90', 0)]
    nta_d_values = [nta_data.get('d10', 0), nta_data.get('d50', 0), nta_data.get('d90', 0)]
    
    fig.add_trace(go.Bar(
        x=d_values,
        y=fcs_d_values,
        name='FCS',
        marker_color=DARK_THEME['fcs_color'],
        text=[f"{v:.1f}" for v in fcs_d_values],
        textposition='outside'
    ), row=1, col=2)
    
    fig.add_trace(go.Bar(
        x=d_values,
        y=nta_d_values,
        name='NTA',
        marker_color=DARK_THEME['nta_color'],
        text=[f"{v:.1f}" for v in nta_d_values],
        textposition='outside'
    ), row=1, col=2)
    
    # Panel 3: Event/Particle Counts
    count_categories = ['Events/Particles']
    fcs_counts = [fcs_data.get('total_events', 0)]
    nta_counts = [nta_data.get('particle_count', 0)]
    
    fig.add_trace(go.Bar(
        x=count_categories,
        y=fcs_counts,
        name='FCS Events',
        marker_color=DARK_THEME['fcs_color'],
        text=[f"{v:,.0f}" for v in fcs_counts],
        textposition='outside',
        showlegend=False
    ), row=2, col=1)
    
    fig.add_trace(go.Bar(
        x=count_categories,
        y=nta_counts,
        name='NTA Particles',
        marker_color=DARK_THEME['nta_color'],
        text=[f"{v:,.0f}" for v in nta_counts],
        textposition='outside',
        showlegend=False
    ), row=2, col=1)
    
    # Panel 4: Size Statistics
    stat_categories = ['Mean', 'Median', 'Std Dev']
    fcs_stats = [
        fcs_data.get('mean_size', 0),
        fcs_data.get('median_size', 0),
        fcs_data.get('std_size', 0)
    ]
    nta_stats = [
        nta_data.get('mean_size', 0),
        nta_data.get('median_size', 0),
        nta_data.get('std_size', 0)
    ]
    
    fig.add_trace(go.Bar(
        x=stat_categories,
        y=fcs_stats,
        name='FCS Stats',
        marker_color=DARK_THEME['fcs_color'],
        text=[f"{v:.1f}" for v in fcs_stats],
        textposition='outside',
        showlegend=False
    ), row=2, col=2)
    
    fig.add_trace(go.Bar(
        x=stat_categories,
        y=nta_stats,
        name='NTA Stats',
        marker_color=DARK_THEME['nta_color'],
        text=[f"{v:.1f}" for v in nta_stats],
        textposition='outside',
        showlegend=False
    ), row=2, col=2)
    
    # Update layout
    fig.update_layout(
        title=dict(
            text=f"🔬 Cross-Instrument Comparison: {sample_name}",
            x=0.5,
            font=dict(size=18)
        ),
        barmode='group',
        height=700,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )
    
    # Apply dark theme
    return apply_dark_theme(fig)


# =========================================================================
# DISCREPANCY ANALYSIS
# =========================================================================

def create_discrepancy_chart(
    fcs_values: Dict[str, float],
    nta_values: Dict[str, float],
    threshold_pct: float = 15.0,
    title: str = "Measurement Discrepancy Analysis"
) -> go.Figure:
    """
    Create a chart showing discrepancies between FCS and NTA measurements.
    
    Args:
        fcs_values: Dictionary of FCS measurements {metric: value}
        nta_values: Dictionary of NTA measurements {metric: value}
        threshold_pct: Threshold for highlighting discrepancies (%)
        title: Plot title
    
    Returns:
        Plotly Figure showing discrepancies
    """
    fig = go.Figure()
    
    metrics = []
    pct_diffs = []
    colors = []
    
    for metric in set(fcs_values.keys()) & set(nta_values.keys()):
        fcs_val = fcs_values[metric]
        nta_val = nta_values[metric]
        
        if fcs_val > 0 and nta_val > 0:
            avg_val = (fcs_val + nta_val) / 2
            pct_diff = abs(fcs_val - nta_val) / avg_val * 100
            
            metrics.append(metric)
            pct_diffs.append(pct_diff)
            
            # Color based on threshold
            if pct_diff > threshold_pct:
                colors.append(DARK_THEME['error'])
            elif pct_diff > threshold_pct * 0.5:
                colors.append(DARK_THEME['warning'])
            else:
                colors.append(DARK_THEME['success'])
    
    fig.add_trace(go.Bar(
        x=metrics,
        y=pct_diffs,
        marker_color=colors,
        text=[f"{v:.1f}%" for v in pct_diffs],
        textposition='outside',
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Discrepancy: %{y:.1f}%<extra></extra>"
        )
    ))
    
    # Add threshold line
    fig.add_hline(
        y=threshold_pct,
        line_dash="dash",
        line_color=DARK_THEME['error'],
        annotation_text=f"Threshold: {threshold_pct}%",
        annotation_position="right"
    )
    
    fig.update_layout(
        title=dict(text=title, x=0.5),
        xaxis_title="Measurement",
        yaxis_title="Discrepancy (%)",
        height=400
    )
    
    return apply_dark_theme(fig)


# =========================================================================
# STATISTICAL COMPARISON
# =========================================================================

def calculate_comparison_stats(
    fcs_sizes: np.ndarray,
    nta_sizes: np.ndarray
) -> Dict[str, Any]:
    """
    Calculate comprehensive comparison statistics between FCS and NTA.
    
    Args:
        fcs_sizes: Array of FCS sizes (nm)
        nta_sizes: Array of NTA sizes (nm)
    
    Returns:
        Dictionary with comparison statistics
    """
    # Clean data
    fcs_clean = fcs_sizes[~np.isnan(fcs_sizes)]
    nta_clean = nta_sizes[~np.isnan(nta_sizes)]
    
    # Basic statistics
    fcs_stats = {
        'd10': np.percentile(fcs_clean, 10),
        'd50': np.percentile(fcs_clean, 50),
        'd90': np.percentile(fcs_clean, 90),
        'mean': np.mean(fcs_clean),
        'std': np.std(fcs_clean),
        'n': len(fcs_clean)
    }
    
    nta_stats = {
        'd10': np.percentile(nta_clean, 10),
        'd50': np.percentile(nta_clean, 50),
        'd90': np.percentile(nta_clean, 90),
        'mean': np.mean(nta_clean),
        'std': np.std(nta_clean),
        'n': len(nta_clean)
    }
    
    # Calculate discrepancies
    discrepancies = {}
    for key in ['d10', 'd50', 'd90', 'mean']:
        fcs_val = fcs_stats[key]
        nta_val = nta_stats[key]
        avg_val = (fcs_val + nta_val) / 2
        pct_diff = abs(fcs_val - nta_val) / avg_val * 100 if avg_val > 0 else 0
        discrepancies[key] = {
            'fcs': fcs_val,
            'nta': nta_val,
            'pct_diff': pct_diff,
            'within_15pct': pct_diff <= 15
        }
    
    # Kolmogorov-Smirnov test for distribution similarity
    ks_result = stats.ks_2samp(fcs_clean, nta_clean)
    ks_stat = float(ks_result[0])  # statistic is first element
    ks_pval = float(ks_result[1])  # pvalue is second element
    
    # Mann-Whitney U test
    mw_result = stats.mannwhitneyu(fcs_clean, nta_clean, alternative='two-sided')
    mw_stat = float(mw_result[0])  # statistic is first element
    mw_pval = float(mw_result[1])  # pvalue is second element
    
    return {
        'fcs': fcs_stats,
        'nta': nta_stats,
        'discrepancies': discrepancies,
        'ks_test': {'statistic': ks_stat, 'p_value': ks_pval},
        'mw_test': {'statistic': mw_stat, 'p_value': mw_pval},
        'distributions_similar': ks_pval > 0.05,
        'overall_agreement': all(d['within_15pct'] for d in discrepancies.values())
    }


def create_stats_table(comparison_stats: Dict[str, Any]) -> pd.DataFrame:
    """
    Create a DataFrame for display showing comparison statistics.
    
    Args:
        comparison_stats: Output from calculate_comparison_stats()
    
    Returns:
        DataFrame formatted for display
    """
    rows = []
    
    for metric in ['d10', 'd50', 'd90', 'mean']:
        disc = comparison_stats['discrepancies'][metric]
        rows.append({
            'Metric': metric.upper(),
            'FCS (nm)': f"{disc['fcs']:.1f}",
            'NTA (nm)': f"{disc['nta']:.1f}",
            'Difference (%)': f"{disc['pct_diff']:.1f}%",
            'Status': '✅' if disc['within_15pct'] else '⚠️'
        })
    
    # Add distribution test results
    ks = comparison_stats['ks_test']
    rows.append({
        'Metric': 'KS Test',
        'FCS (nm)': f"stat: {ks['statistic']:.3f}",
        'NTA (nm)': f"p: {ks['p_value']:.3e}",
        'Difference (%)': '-',
        'Status': '✅' if ks['p_value'] > 0.05 else '⚠️'
    })
    
    return pd.DataFrame(rows)
