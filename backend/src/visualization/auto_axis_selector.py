"""
Auto-Axis Selection Module for FCS Data Visualization

Intelligently selects optimal channel pairs for scatter plot visualization based on:
- Variance and spread (information content)
- Correlation between channels
- Dynamic range
- Population separation (multi-modal distributions)
- Standard cytometry best practices

Author: GitHub Copilot
Date: November 16, 2025
Task: Phase 2 - Auto-axis Selection for Optimal Scatter Plots
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Optional
from scipy import stats
from sklearn.preprocessing import StandardScaler
from loguru import logger


class AutoAxisSelector:
    """
    Automatically select optimal channel pairs for FCS scatter plots.
    
    Features:
    - Variance-based ranking (high information content channels)
    - Correlation analysis (avoid redundant channel pairs)
    - Dynamic range assessment
    - Population separation metrics (multi-modal detection)
    - Best practice recommendations (FSC-SSC, marker combinations)
    """
    
    # Standard cytometry channel categories
    SCATTER_CHANNELS = ['FSC', 'SSC', 'FSC-A', 'SSC-A', 'FSC-H', 'SSC-H', 
                        'FSC-W', 'SSC-W', 'VFSC-A', 'VSSC1-A', 'VSSC2-A']
    
    FLUORESCENCE_PREFIXES = ['FL', 'V', 'B', 'R', 'Y', 'G', 'PE', 'APC', 'FITC']
    
    def __init__(
        self,
        min_variance_threshold: float = 0.1,
        max_correlation_threshold: float = 0.95,
        sample_size: int = 10000
    ):
        """
        Initialize auto-axis selector.
        
        Args:
            min_variance_threshold: Minimum normalized variance for channel selection
            max_correlation_threshold: Maximum correlation to avoid redundant pairs
            sample_size: Number of events to analyze (for performance)
        """
        self.min_variance_threshold = min_variance_threshold
        self.max_correlation_threshold = max_correlation_threshold
        self.sample_size = sample_size
        logger.info("Auto-Axis Selector initialized")
    
    def select_best_axes(
        self,
        data: pd.DataFrame,
        n_pairs: int = 5,
        include_scatter: bool = True,
        include_fluorescence: bool = True
    ) -> List[Tuple[str, str, float]]:
        """
        Intelligently select the best channel pairs for scatter plot visualization.
        
        Args:
            data: DataFrame containing FCS event data
            n_pairs: Number of top channel pairs to return
            include_scatter: Include FSC/SSC combinations
            include_fluorescence: Include fluorescence marker combinations
            
        Returns:
            List of tuples: [(x_channel, y_channel, score), ...]
            Sorted by score (higher is better)
        
        HOW IT WORKS:
        -------------
        1. Categorize channels (scatter vs fluorescence)
        2. Calculate metrics for each channel (variance, range, bimodality)
        3. Generate candidate pairs based on best practices
        4. Score each pair using multiple criteria
        5. Return top N pairs sorted by score
        
        SCORING CRITERIA:
        -----------------
        - Variance: High variance = more information
        - Dynamic range: Larger range = better separation
        - Correlation: Low correlation = independent information
        - Bimodality: Two populations = interesting biology
        - Best practices: FSC-SSC always recommended
        
        CHANNEL PAIR PRIORITY:
        ----------------------
        1. FSC vs SSC (standard gating view) - ALWAYS FIRST
           Score boosted by 1.5x because this is cytometry standard
        
        2. Fluorescence vs Scatter (marker positive vs size)
           Example: CD81 vs FSC ("Are larger EVs CD81 positive?")
        
        3. Fluorescence vs Fluorescence (multi-marker analysis)
           Example: CD81 vs CD9 ("Do CD81+ EVs also have CD9?")
           Only include if correlation < 0.95 (avoid redundancy)
        
        4. Scatter vs Scatter (particle characteristics)
           Example: FSC-A vs FSC-H (doublet discrimination)
        
        EXAMPLE OUTPUT:
        ---------------
        [
            ('VFSC-A', 'VSSC1-A', 0.95, 'Standard gating view'),
            ('B531-H', 'VFSC-A', 0.78, 'Fluorescence vs Scatter'),
            ('B531-H', 'R670-H', 0.65, 'Multi-marker analysis'),
            ('VFSC-A', 'VFSC-H', 0.52, 'Scatter comparison'),
            ('Y585-H', 'VSSC1-A', 0.48, 'Fluorescence vs Scatter')
        ]
        """
        logger.info(f"Analyzing {len(data)} events for optimal axis selection...")
        
        # Step 1: Sample data if too large (for performance)
        # --------------------------------------------------
        # Analyzing 1M events is slow
        # 10,000 events is representative and fast
        if len(data) > self.sample_size:
            data_sample = data.sample(n=self.sample_size, random_state=42)
            logger.info(f"Sampled {self.sample_size} events for analysis")
        else:
            data_sample = data
        
        # Step 2: Identify numeric channels (only these can be plotted)
        # -------------------------------------------------------------
        numeric_channels = data_sample.select_dtypes(include=[np.number]).columns.tolist()
        
        # Remove metadata columns that aren't measurement channels
        # These don't represent actual cytometry measurements
        exclude_cols = ['sample_id', 'event_id', 'Time', 'time', 'index']
        numeric_channels = [col for col in numeric_channels if col not in exclude_cols]
        
        # Step 3: Categorize channels by type
        # -----------------------------------
        # Scatter channels: FSC, SSC (particle physical properties)
        # Fluorescence channels: FL, PE, FITC, etc. (marker expression)
        scatter_channels = self._identify_scatter_channels(numeric_channels)
        fluorescence_channels = self._identify_fluorescence_channels(numeric_channels)
        
        logger.info(f"Found {len(scatter_channels)} scatter channels, {len(fluorescence_channels)} fluorescence channels")
        
        # Step 4: Calculate metrics for each channel
        # ------------------------------------------
        # Metrics include: variance, dynamic range, bimodality
        # These help us pick the most informative channels
        channel_data = data_sample[numeric_channels]
        channel_metrics = self._calculate_channel_metrics(channel_data if isinstance(channel_data, pd.DataFrame) else pd.DataFrame(channel_data))
        
        # Step 5: Generate candidate channel pairs
        # ----------------------------------------
        # We'll build a list of (x_channel, y_channel, score, description)
        candidate_pairs = []
        
        # ============================================================
        # Priority 1: FSC vs SSC (Standard Gating View)
        # ============================================================
        # ALWAYS recommend FSC vs SSC as the first plot
        # This is the universal starting point in flow cytometry
        # Used for: Initial gating, doublet discrimination, debris removal
        if include_scatter and scatter_channels:
            # Find FSC channels (forward scatter)
            fsc_candidates = [ch for ch in scatter_channels if 'FSC' in ch.upper() or 'VFSC' in ch.upper()]
            # Find SSC channels (side scatter)
            ssc_candidates = [ch for ch in scatter_channels if 'SSC' in ch.upper() or 'VSSC' in ch.upper()]
            
            if fsc_candidates and ssc_candidates:
                # Use first available FSC and SSC
                # Usually 'VFSC-A' and 'VSSC1-A' or 'FSC-A' and 'SSC-A'
                fsc = fsc_candidates[0]
                ssc = ssc_candidates[0]
                # Calculate score and boost by 1.5x (prioritize standard view)
                score = self._calculate_pair_score(data_sample, fsc, ssc, channel_metrics)
                candidate_pairs.append((fsc, ssc, score * 1.5, "Standard gating view"))
                logger.info(f"Standard view: {fsc} vs {ssc} (score: {score*1.5:.3f})")
        
        # ============================================================
        # Priority 2: Fluorescence vs Scatter
        # ============================================================
        # Example: CD81 vs FSC (marker expression vs particle size)
        # Answers: "What size are the marker-positive EVs?"
        if include_fluorescence and include_scatter:
            for fl_ch in fluorescence_channels[:5]:  # Top 5 fluorescence channels
                for scatter_ch in scatter_channels[:2]:  # Top 2 scatter channels
                    score = self._calculate_pair_score(data_sample, fl_ch, scatter_ch, channel_metrics)
                    if score > 0.3:  # Minimum threshold (avoid noisy/boring channels)
                        candidate_pairs.append((fl_ch, scatter_ch, score, "Fluorescence vs Scatter"))
        
        # ============================================================
        # Priority 3: Fluorescence vs Fluorescence (Multi-Marker)
        # ============================================================
        # Example: CD81 vs CD9 (co-expression analysis)
        # Answers: "Do CD81+ EVs also express CD9?"
        if include_fluorescence and len(fluorescence_channels) >= 2:
            for i, fl_ch1 in enumerate(fluorescence_channels[:8]):
                for fl_ch2 in fluorescence_channels[i+1:8]:
                    # Check correlation to avoid redundant pairs
                    # If two channels are highly correlated (r > 0.95),
                    # they contain the same information (redundant)
                    pair_corr = data_sample[[fl_ch1, fl_ch2]].corr(method='pearson')  # type: ignore[call-arg]
                    corr = float(pair_corr.iloc[0, 1])
                    if abs(corr) < self.max_correlation_threshold:
                        score = self._calculate_pair_score(data_sample, fl_ch1, fl_ch2, channel_metrics)
                        if score > 0.3:
                            candidate_pairs.append((fl_ch1, fl_ch2, score, "Multi-marker analysis"))
        
        # ============================================================
        # Priority 4: Scatter vs Scatter
        # ============================================================
        # Example: FSC-A vs FSC-H (doublet discrimination)
        # Answers: "Are there doublets (stuck-together EVs)?"
        if include_scatter and len(scatter_channels) >= 2:
            for i, sc1 in enumerate(scatter_channels[:4]):
                for sc2 in scatter_channels[i+1:4]:
                    if sc1 != sc2:
                        score = self._calculate_pair_score(data_sample, sc1, sc2, channel_metrics)
                        if score > 0.3:
                            candidate_pairs.append((sc1, sc2, score, "Scatter comparison"))
        
        # Sort by score (descending)
        candidate_pairs.sort(key=lambda x: x[2], reverse=True)
        
        # Remove duplicates (keep highest score)
        seen_pairs = set()
        unique_pairs = []
        for x, y, score, reason in candidate_pairs:
            pair_key = tuple(sorted([x, y]))
            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                unique_pairs.append((x, y, score, reason))
        
        # Return top N pairs
        top_pairs = unique_pairs[:n_pairs]
        
        logger.success(f"Selected {len(top_pairs)} optimal channel pairs")
        for i, (x, y, score, reason) in enumerate(top_pairs, 1):
            logger.info(f"  {i}. {x} vs {y} (score: {score:.3f}) - {reason}")
        
        return [(x, y, score) for x, y, score, _ in top_pairs]
    
    def _identify_scatter_channels(self, channels: List[str]) -> List[str]:
        """Identify forward/side scatter channels."""
        scatter_chs = []
        for ch in channels:
            ch_upper = ch.upper()
            if any(scatter_type in ch_upper for scatter_type in self.SCATTER_CHANNELS):
                scatter_chs.append(ch)
        return scatter_chs
    
    def _identify_fluorescence_channels(self, channels: List[str]) -> List[str]:
        """Identify fluorescence marker channels."""
        fl_chs = []
        for ch in channels:
            ch_upper = ch.upper()
            # Check if it starts with known fluorescence prefixes
            is_fluorescence = any(ch_upper.startswith(prefix) for prefix in self.FLUORESCENCE_PREFIXES)
            # Exclude scatter channels
            is_scatter = any(scatter_type in ch_upper for scatter_type in self.SCATTER_CHANNELS)
            
            if is_fluorescence and not is_scatter:
                fl_chs.append(ch)
        return fl_chs
    
    def _calculate_channel_metrics(self, data: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """
        Calculate quality metrics for each channel.
        
        Returns:
            Dict of channel metrics: {channel: {variance, range, cv, modality}}
        """
        metrics = {}
        
        for channel in data.columns:
            channel_data = data[channel].dropna()
            
            if len(channel_data) < 100:  # Skip channels with insufficient data
                continue
            
            # Variance (normalized)
            variance = np.var(channel_data)
            normalized_variance = variance / (np.mean(channel_data) ** 2 + 1e-10)  # CV squared
            
            # Dynamic range
            data_range = channel_data.max() - channel_data.min()
            
            # Coefficient of variation
            cv = np.std(channel_data) / (np.mean(channel_data) + 1e-10)
            
            # Modality (bimodality coefficient)
            # Higher values suggest multi-modal distributions (interesting populations)
            skewness = stats.skew(channel_data)
            kurtosis = stats.kurtosis(channel_data)
            n = len(channel_data)
            modality_coef = (skewness**2 + 1) / (kurtosis + 3 * ((n-1)**2) / ((n-2)*(n-3)))
            
            metrics[channel] = {
                'variance': variance,
                'normalized_variance': normalized_variance,
                'range': data_range,
                'cv': cv,
                'modality': modality_coef,
                'mean': np.mean(channel_data),
                'std': np.std(channel_data)
            }
        
        return metrics
    
    def _calculate_pair_score(
        self,
        data: pd.DataFrame,
        x_channel: str,
        y_channel: str,
        channel_metrics: Dict[str, Dict[str, float]]
    ) -> float:
        """
        Calculate quality score for a channel pair.
        
        Score components:
        - Variance (information content) - 30%
        - Correlation (avoid redundancy) - 20%
        - Dynamic range - 20%
        - Population separation - 20%
        - Modality (interesting distributions) - 10%
        
        Returns:
            Score between 0 and 1 (higher is better)
        """
        # Get channel data
        pair_data = data[[x_channel, y_channel]].dropna()
        
        if len(pair_data) < 100:
            return 0.0
        
        # Component 1: Variance score (average of both channels)
        x_var = channel_metrics.get(x_channel, {}).get('normalized_variance', 0)
        y_var = channel_metrics.get(y_channel, {}).get('normalized_variance', 0)
        variance_score = np.clip((x_var + y_var) / 2, 0, 1)
        
        # Component 2: Correlation score (lower correlation = higher score)
        pair_corr_matrix = pair_data.corr(method='pearson')  # type: ignore[call-arg]
        correlation = float(abs(pair_corr_matrix.iloc[0, 1]))
        correlation_score = 1.0 - min(correlation, 1.0)
        
        # Component 3: Dynamic range score
        x_range = channel_metrics.get(x_channel, {}).get('range', 0)
        y_range = channel_metrics.get(y_channel, {}).get('range', 0)
        x_mean = channel_metrics.get(x_channel, {}).get('mean', 1)
        y_mean = channel_metrics.get(y_channel, {}).get('mean', 1)
        x_range_norm = x_range / (x_mean + 1e-10)
        y_range_norm = y_range / (y_mean + 1e-10)
        range_score = np.clip((x_range_norm + y_range_norm) / 10, 0, 1)  # Normalize to 0-1
        
        # Component 4: Population separation (using 2D KDE entropy)
        try:
            # Sample for performance
            sample_data = pair_data.sample(n=min(1000, len(pair_data)), random_state=42)
            
            # Standardize data
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(sample_data)
            
            # Calculate 2D histogram entropy (higher = more separated populations)
            hist, _, _ = np.histogram2d(scaled_data[:, 0], scaled_data[:, 1], bins=20)
            hist_norm = hist / (hist.sum() + 1e-10)
            hist_norm = hist_norm[hist_norm > 0]  # Remove zeros
            entropy = -np.sum(hist_norm * np.log2(hist_norm))
            separation_score = np.clip(entropy / 10, 0, 1)  # Normalize
        except:
            separation_score = 0.5  # Default if calculation fails
        
        # Component 5: Modality score (average of both channels)
        x_modality = channel_metrics.get(x_channel, {}).get('modality', 0)
        y_modality = channel_metrics.get(y_channel, {}).get('modality', 0)
        modality_score = np.clip((x_modality + y_modality) / 2, 0, 1)
        
        # Weighted combination
        final_score = (
            0.30 * variance_score +
            0.20 * correlation_score +
            0.20 * range_score +
            0.20 * separation_score +
            0.10 * modality_score
        )
        
        return final_score
    
    def generate_recommendations(
        self,
        data: pd.DataFrame,
        n_recommendations: int = 5
    ) -> pd.DataFrame:
        """
        Generate a detailed report of recommended channel pairs.
        
        Args:
            data: DataFrame containing FCS event data
            n_recommendations: Number of recommendations to generate
            
        Returns:
            DataFrame with columns: rank, x_channel, y_channel, score, reason
        """
        # Get best pairs
        best_pairs = self.select_best_axes(data, n_pairs=n_recommendations)
        
        # Create recommendations DataFrame
        recommendations = []
        for rank, (x, y, score) in enumerate(best_pairs, 1):
            # Determine reason
            if 'FSC' in x.upper() or 'FSC' in y.upper():
                if 'SSC' in x.upper() or 'SSC' in y.upper():
                    reason = "Standard gating view (FSC vs SSC)"
                else:
                    reason = "Fluorescence vs Size"
            elif any(prefix in x.upper() for prefix in self.FLUORESCENCE_PREFIXES):
                if any(prefix in y.upper() for prefix in self.FLUORESCENCE_PREFIXES):
                    reason = "Multi-marker analysis"
                else:
                    reason = "Fluorescence vs Scatter"
            else:
                reason = "Optimal separation"
            
            recommendations.append({
                'rank': rank,
                'x_channel': x,
                'y_channel': y,
                'score': round(score, 3),
                'reason': reason
            })
        
        return pd.DataFrame(recommendations)


def select_optimal_axes(data: pd.DataFrame, n_pairs: int = 5) -> List[Tuple[str, str, float]]:
    """
    Convenience function for auto-axis selection.
    
    Args:
        data: DataFrame containing FCS event data
        n_pairs: Number of top channel pairs to return
        
    Returns:
        List of tuples: [(x_channel, y_channel, score), ...]
    """
    selector = AutoAxisSelector()
    return selector.select_best_axes(data, n_pairs=n_pairs)


if __name__ == "__main__":
    # Example usage
    import sys
    from pathlib import Path
    
    # Add src to path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from parsers.fcs_parser import FCSParser
    
    # Find first FCS file
    fcs_dir = Path("nanoFACS/10000 exo and cd81")
    fcs_files = list(fcs_dir.glob("*.fcs"))
    
    if fcs_files:
        print(f"\n=== Auto-Axis Selection Demo ===\n")
        print(f"Analyzing: {fcs_files[0].name}\n")
        
        # Parse FCS file
        parser = FCSParser(file_path=fcs_files[0])
        data = parser.parse()
        
        # Auto-select best axes
        selector = AutoAxisSelector()
        recommendations = selector.generate_recommendations(data, n_recommendations=5)
        
        print("\n📊 Recommended Channel Pairs:")
        print(recommendations.to_string(index=False))
        
        print("\n✅ Top recommendation:")
        print(f"   Plot {recommendations.iloc[0]['x_channel']} vs {recommendations.iloc[0]['y_channel']}")
        print(f"   Reason: {recommendations.iloc[0]['reason']}")
    else:
        print("No FCS files found!")
