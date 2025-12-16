"""
Multi-Modal Data Fusion Layer
==============================

Purpose: Link and merge data from multiple lab instruments (FCS, NTA, TEM)

Components:
- sample_matcher.py: Match samples across different instruments by sample ID
- feature_extractor.py: Extract features from each instrument type
- data_aligner.py: Temporal and spatial correlation of measurements

Architecture Component: Layer 4 - Multi-Modal Data Fusion
"""

from .sample_matcher import SampleMatcher
from .feature_extractor import FeatureExtractor

__all__ = ['SampleMatcher', 'FeatureExtractor']
