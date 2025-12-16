"""
Sample ID Matcher - Multi-Modal Data Fusion Component
=====================================================

Purpose: Link data from the same biological sample across different instruments

Architecture Compliance:
- Layer 4: Multi-Modal Data Fusion
- Component: Sample ID Matcher
- Function: Match nanoFACS, NTA, and TEM data by sample identifier

Author: CRMIT Team
Date: November 15, 2025
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import numpy as np
from loguru import logger
from difflib import SequenceMatcher


class SampleMatcher:
    """
    Matches samples across multiple instruments using sample IDs.
    
    Handles:
    - Exact sample ID matches
    - Fuzzy matching for inconsistent naming
    - Biological sample grouping (P5_F10 links multiple measurements)
    - Missing data (samples measured by only one instrument)
    """
    
    def __init__(self, fuzzy_threshold: float = 0.85):
        """
        Initialize sample matcher.
        
        Args:
            fuzzy_threshold: Similarity threshold for fuzzy matching (0.0-1.0)
        """
        self.fuzzy_threshold = fuzzy_threshold
        self.match_report: Dict[str, Any] = {}
        
    def match_samples(
        self,
        fcs_metadata: pd.DataFrame,
        nta_metadata: pd.DataFrame,
        tem_metadata: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Match samples across all instruments.
        
        Args:
            fcs_metadata: FCS sample metadata (from Task 1.1)
            nta_metadata: NTA sample metadata (from Task 1.2)
            tem_metadata: TEM sample metadata (optional, future)
        
        Returns:
            Master sample registry with match status
        """
        logger.info("🔍 Starting sample matching across instruments...")
        
        # Step 1: Extract sample IDs from each instrument
        fcs_samples = self._extract_sample_ids(fcs_metadata, 'fcs')
        nta_samples = self._extract_sample_ids(nta_metadata, 'nta')
        
        # Step 2: Perform exact matches
        exact_matches = self._exact_match(fcs_samples, nta_samples)
        
        # Step 3: Fuzzy match remaining samples
        fcs_unmatched = fcs_samples[~fcs_samples['sample_id'].isin(exact_matches['sample_id'])].copy()
        nta_unmatched = nta_samples[~nta_samples['sample_id'].isin(exact_matches['sample_id'])].copy()
        
        # Ensure they are DataFrames
        fcs_unmatched_df = pd.DataFrame(fcs_unmatched)
        nta_unmatched_df = pd.DataFrame(nta_unmatched)
        
        fuzzy_matches = self._fuzzy_match(fcs_unmatched_df, nta_unmatched_df)
        
        # Step 4: Combine all matches
        all_matches = pd.concat([exact_matches, fuzzy_matches], ignore_index=True)
        
        # Step 5: Add unmatched samples
        unmatched_fcs = fcs_samples[~fcs_samples['sample_id'].isin(all_matches['sample_id'])].copy()
        unmatched_nta = nta_samples[~nta_samples['sample_id'].isin(all_matches['sample_id'])].copy()
        
        # Ensure they are DataFrames
        unmatched_fcs_df = pd.DataFrame(unmatched_fcs)
        unmatched_nta_df = pd.DataFrame(unmatched_nta)
        
        # Step 6: Create master registry
        master_registry = self._create_master_registry(
            all_matches, unmatched_fcs_df, unmatched_nta_df
        )
        
        # Generate match report
        self._generate_match_report(master_registry)
        
        logger.info(f"✅ Sample matching complete: {len(master_registry)} samples")
        logger.info(f"   - Exact matches: {len(exact_matches)}")
        logger.info(f"   - Fuzzy matches: {len(fuzzy_matches)}")
        logger.info(f"   - FCS only: {len(unmatched_fcs)}")
        logger.info(f"   - NTA only: {len(unmatched_nta)}")
        
        return master_registry
    
    def _extract_sample_ids(self, metadata: pd.DataFrame, instrument: str) -> pd.DataFrame:
        """Extract standardized sample IDs from metadata."""
        if 'sample_id' not in metadata.columns:
            raise ValueError(f"{instrument} metadata missing 'sample_id' column")
        
        # Handle optional file_name column - use sample_id as fallback
        if 'file_name' in metadata.columns:
            samples = metadata[['sample_id', 'file_name']].copy()
        else:
            samples = metadata[['sample_id']].copy()
            samples['file_name'] = samples['sample_id']  # Use sample_id as fallback
        
        samples['instrument'] = instrument
        samples['original_sample_id'] = samples['sample_id']
        
        # Standardize sample IDs (remove spaces, lowercase, etc.)
        sample_id_series = samples['sample_id']
        if isinstance(sample_id_series, pd.Series):
            samples['sample_id_std'] = sample_id_series.str.lower().str.replace(' ', '_')
        
        # Ensure return type is DataFrame
        return pd.DataFrame(samples)
    
    def _exact_match(self, fcs_samples: pd.DataFrame, nta_samples: pd.DataFrame) -> pd.DataFrame:
        """Find exact sample ID matches between FCS and NTA."""
        merged = pd.merge(
            fcs_samples[['sample_id', 'sample_id_std', 'file_name']],
            nta_samples[['sample_id', 'sample_id_std', 'file_name']],
            on='sample_id_std',
            suffixes=('_fcs', '_nta')
        )
        
        merged['match_type'] = 'exact'
        merged['match_confidence'] = 1.0
        merged['has_fcs'] = True
        merged['has_nta'] = True
        merged['has_tem'] = False
        
        # Use FCS sample_id as primary (arbitrary choice)
        merged['sample_id'] = merged['sample_id_fcs']
        
        return merged
    
    def _fuzzy_match(self, fcs_samples: pd.DataFrame, nta_samples: pd.DataFrame) -> pd.DataFrame:
        """
        Fuzzy match samples with similar but not identical IDs.
        
        Example: "BV_EXO_001" matches "BV-EXO-001"
        """
        matches = []
        
        for _, fcs_row in fcs_samples.iterrows():
            fcs_id = str(fcs_row['sample_id_std'])
            
            best_match = None
            best_score = 0.0
            
            for _, nta_row in nta_samples.iterrows():
                nta_id = str(nta_row['sample_id_std'])
                
                # Calculate similarity
                similarity = SequenceMatcher(None, fcs_id, nta_id).ratio()
                
                if similarity > best_score and similarity >= self.fuzzy_threshold:
                    best_score = similarity
                    best_match = nta_row
            
            if best_match is not None:
                match = {
                    'sample_id': fcs_row['sample_id'],
                    'sample_id_fcs': fcs_row['sample_id'],
                    'sample_id_nta': best_match['sample_id'],
                    'file_name_fcs': fcs_row['file_name'],
                    'file_name_nta': best_match['file_name'],
                    'match_type': 'fuzzy',
                    'match_confidence': best_score,
                    'has_fcs': True,
                    'has_nta': True,
                    'has_tem': False,
                }
                matches.append(match)
        
        return pd.DataFrame(matches) if matches else pd.DataFrame()
    
    def _create_master_registry(
        self,
        matches: pd.DataFrame,
        unmatched_fcs: pd.DataFrame,
        unmatched_nta: pd.DataFrame
    ) -> pd.DataFrame:
        """Create master sample registry including unmatched samples."""
        
        # Add unmatched FCS samples
        for _, row in unmatched_fcs.iterrows():
            match = {
                'sample_id': row['sample_id'],
                'sample_id_fcs': row['sample_id'],
                'sample_id_nta': None,
                'file_name_fcs': row['file_name'],
                'file_name_nta': None,
                'match_type': 'fcs_only',
                'match_confidence': 1.0,
                'has_fcs': True,
                'has_nta': False,
                'has_tem': False,
            }
            matches = pd.concat([matches, pd.DataFrame([match])], ignore_index=True)
        
        # Add unmatched NTA samples
        for _, row in unmatched_nta.iterrows():
            match = {
                'sample_id': row['sample_id'],
                'sample_id_fcs': None,
                'sample_id_nta': row['sample_id'],
                'file_name_fcs': None,
                'file_name_nta': row['file_name'],
                'match_type': 'nta_only',
                'match_confidence': 1.0,
                'has_fcs': False,
                'has_nta': True,
                'has_tem': False,
            }
            matches = pd.concat([matches, pd.DataFrame([match])], ignore_index=True)
        
        return matches.reset_index(drop=True)
    
    def _generate_match_report(self, registry: pd.DataFrame) -> None:
        """Generate detailed match report."""
        self.match_report = {
            'total_samples': len(registry),
            'exact_matches': len(registry[registry['match_type'] == 'exact']),
            'fuzzy_matches': len(registry[registry['match_type'] == 'fuzzy']),
            'fcs_only': len(registry[registry['match_type'] == 'fcs_only']),
            'nta_only': len(registry[registry['match_type'] == 'nta_only']),
            'complete_samples': len(registry[registry['has_fcs'] & registry['has_nta']]),
            'match_rate': len(registry[registry['has_fcs'] & registry['has_nta']]) / len(registry) * 100
        }
    
    def get_match_report(self) -> Dict[str, Any]:
        """Return match report."""
        return self.match_report
    
    def export_match_report(self, output_path: Path) -> None:
        """Export match report to CSV."""
        if not self.match_report:
            logger.warning("No match report available")
            return
        
        report_df = pd.DataFrame([self.match_report])
        report_df.to_csv(output_path, index=False)
        logger.info(f"Match report saved: {output_path}")
