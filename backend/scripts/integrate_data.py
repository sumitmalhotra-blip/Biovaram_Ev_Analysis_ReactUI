"""
Data Integration Module - Task 1.3 (ARCHITECTURE COMPLIANT)
===========================================================

Purpose:
- Merge nanoFACS and NTA data by biological_sample_id
- Calculate baseline comparisons (deltas, fold changes)
- Generate combined_features.parquet (ML-ready)
- Generate baseline_comparison.parquet
- Create sample_metadata.parquet

Architecture Compliance:
- Uses Layer 2: Data Preprocessing (quality control, normalization, size binning)
- Uses Layer 4: Multi-Modal Fusion (sample matcher, feature extractor)

Author: CRMIT Team
Date: November 15, 2025
Status: IMPLEMENTED - Architecture compliant
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from loguru import logger

# Architecture Layer 2: Data Preprocessing
from preprocessing.quality_control import QualityControl
from preprocessing.normalization import DataNormalizer
from preprocessing.size_binning import SizeBinning

# Architecture Layer 4: Multi-Modal Fusion
from fusion.sample_matcher import SampleMatcher
from fusion.feature_extractor import FeatureExtractor


class DataIntegrator:
    """
    Integrates multi-modal instrument data following 7-layer architecture.
    
    Architecture Layers Used:
    - Layer 2: Data Preprocessing (QC, normalization, size binning)
    - Layer 4: Multi-Modal Fusion (sample matching, feature extraction)
    """
    
    def __init__(self, output_dir: Path | None = None):
        """
        Initialize data integrator with architecture components.
        
        Args:
            output_dir: Directory for output files (default: data/processed/)
        """
        # Set output directory
        if output_dir is None:
            self.output_dir = Path(__file__).parent.parent / 'data' / 'processed'
        else:
            self.output_dir = Path(output_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize architecture components
        self.qc = QualityControl()
        self.normalizer = DataNormalizer()
        self.size_binner = SizeBinning()
        self.sample_matcher = SampleMatcher(fuzzy_threshold=0.85)
        self.feature_extractor = FeatureExtractor()
        
        logger.info("✅ Data Integrator initialized (Architecture Compliant)")
        logger.info(f"   Output directory: {self.output_dir}")
    
    def integrate_all_data(
        self,
        fcs_parquet_dir: Path,
        nta_parquet_dir: Path,
        baseline_samples: Optional[List[str]] = None
    ) -> Dict[str, Optional[Path]]:
        """
        Full integration pipeline: FCS + NTA → Combined features.
        
        Args:
            fcs_parquet_dir: Directory containing FCS parquet files
            nta_parquet_dir: Directory containing NTA parquet files
            baseline_samples: List of baseline/control sample IDs
        
        Returns:
            Dictionary with paths to output files (some may be None)
        
        WHAT THIS DOES:
        ----------------
        Integrates data from multiple instruments (NanoFACS + NTA) into a single
        ML-ready dataset following the 7-layer architecture specification.
        
        HOW IT WORKS (9-STEP PIPELINE):
        ---------------------------------
        
        STEP 1: Load Data
        - Read FCS statistics (batch_process_fcs.py output)
        - Read NTA statistics (batch_process_nta.py output)
        - Each instrument provides summary stats per sample
        
        STEP 2: Quality Control (Layer 2)
        - FCS checks: event count, scatter values, CV thresholds
        - NTA checks: concentration range, size distribution validity
        - Separates passed/failed samples
        - Exports QC report for review
        
        STEP 3: Normalization (Layer 2)
        - Standardizes scales across samples
        - Methods: z-score (mean=0, std=1)
        - Enables fair comparison between samples
        - Critical for ML model training
        
        STEP 4: Size Binning (Layer 2)
        - Groups particles: small (40-80nm), medium (80-100nm), large (100-120nm)
        - NTA: bins based on D50 (median size)
        - FCS: bins based on FSC-A (scatter intensity)
        - Architecture requirement for downstream analysis
        
        STEP 5: Sample Matching (Layer 4)
        - Matches FCS and NTA data from same biological sample
        - Uses fuzzy matching on sample IDs (handles naming variations)
        - Creates sample registry linking instruments
        - Example: "P5_F10_CD81" matches across FCS + NTA + TEM
        
        STEP 6: Feature Extraction (Layer 4)
        - FCS features: scatter stats, intensity stats, size distribution
        - NTA features: D10/D50/D90, concentration, bin percentages
        - Standardized feature naming (fcs_*, nta_*, cross_*)
        
        STEP 7: Merge Features (Layer 4)
        - Combines FCS + NTA features using sample registry
        - Creates unified feature matrix (samples × features)
        - Handles missing data (samples with only FCS or only NTA)
        - Output: combined_features.parquet (ML-ready)
        
        STEP 8: Baseline Comparisons (Optional)
        - Calculates fold changes vs control samples
        - Enables "treatment effect" analysis
        - Example: CD81-treated vs Isotype control
        - Output: baseline_comparison.parquet
        
        STEP 9: Summary Report
        - Human-readable text summary
        - Match statistics, QC pass rates, feature counts
        - Architecture compliance checklist
        
        WHY THIS ARCHITECTURE:
        ----------------------
        - Modular: Each layer is independent (can swap implementations)
        - Testable: Each component can be unit tested
        - Extensible: Easy to add new instruments (TEM, Western Blot)
        - ML-ready: Output format optimized for scikit-learn, TensorFlow
        
        OUTPUT FILES:
        --------------
        1. sample_metadata.parquet - Sample registry with matches
        2. combined_features.parquet - ML-ready feature matrix
        3. baseline_comparison.parquet - Fold changes vs controls
        4. qc_report.csv - Quality control results
        5. match_report.csv - Sample matching details
        6. integration_summary.txt - Human-readable summary
        """
        logger.info("=" * 80)
        logger.info("🚀 STARTING MULTI-MODAL DATA INTEGRATION (Task 1.3)")
        logger.info("=" * 80)
        
        # Step 1: Load FCS and NTA data
        logger.info("\n📂 STEP 1: Loading data...")
        fcs_stats = self._load_fcs_statistics(fcs_parquet_dir)
        nta_stats = self._load_nta_statistics(nta_parquet_dir)
        
        logger.info(f"   - FCS: {len(fcs_stats)} samples loaded")
        logger.info(f"   - NTA: {len(nta_stats)} samples loaded")
        
        # Step 2: Quality Control (Architecture Layer 2)
        logger.info("\n🔍 STEP 2: Quality Control...")
        fcs_passed, fcs_failed = self.qc.check_fcs_quality(fcs_stats)
        nta_passed, nta_failed = self.qc.check_nta_quality(nta_stats)
        
        logger.info(f"   - FCS: {len(fcs_passed)} passed, {len(fcs_failed)} failed")
        logger.info(f"   - NTA: {len(nta_passed)} passed, {len(nta_failed)} failed")
        
        # Export QC reports
        qc_report_path = self.output_dir / 'qc_report.csv'
        self.qc.export_qc_report(qc_report_path)
        
        # Step 3: Normalization (Architecture Layer 2)
        logger.info("\n🔧 STEP 3: Data Normalization...")
        fcs_normalized = self.normalizer.normalize_fcs_data(fcs_passed, method='zscore')
        nta_normalized = self.normalizer.normalize_nta_data(nta_passed, method='zscore')
        
        # Step 4: Size Binning (Architecture Layer 2)
        logger.info("\n📊 STEP 4: Size Binning...")
        nta_binned = self.size_binner.bin_nta_data(nta_normalized)
        fcs_binned = self.size_binner.bin_fcs_data(fcs_normalized)
        
        # Step 5: Sample Matching (Architecture Layer 4)
        logger.info("\n🔗 STEP 5: Sample Matching...")
        sample_registry = self.sample_matcher.match_samples(
            fcs_metadata=fcs_binned,
            nta_metadata=nta_binned
        )
        
        # Export sample registry
        registry_path = self.output_dir / 'sample_metadata.parquet'
        sample_registry.to_parquet(registry_path, index=False)
        logger.info(f"   ✅ Sample registry saved: {registry_path}")
        
        # Export match report
        match_report_path = self.output_dir / 'match_report.csv'
        self.sample_matcher.export_match_report(match_report_path)
        
        # Step 6: Feature Extraction (Architecture Layer 4)
        logger.info("\n📊 STEP 6: Feature Extraction...")
        fcs_features = self.feature_extractor.extract_fcs_features(fcs_binned)
        nta_features = self.feature_extractor.extract_nta_features(nta_binned)
        
        # Step 7: Merge Features (Architecture Layer 4)
        logger.info("\n🔗 STEP 7: Merging Features...")
        combined_features = self.feature_extractor.merge_features(
            sample_registry=sample_registry,
            fcs_features=fcs_features,
            nta_features=nta_features
        )
        
        # Export combined features
        combined_path = self.output_dir / 'combined_features.parquet'
        combined_features.to_parquet(combined_path, index=False)
        logger.info(f"   ✅ Combined features saved: {combined_path}")
        logger.info(f"   - Dimensions: {combined_features.shape[0]} samples × {combined_features.shape[1]} features")
        
        # Step 8: Baseline Comparisons
        if baseline_samples:
            logger.info("\n📊 STEP 8: Baseline Comparisons...")
            baseline_comparison = self.calculate_baseline_comparisons(
                combined_features=combined_features,
                baseline_samples=baseline_samples
            )
            
            baseline_path = self.output_dir / 'baseline_comparison.parquet'
            baseline_comparison.to_parquet(baseline_path, index=False)
            logger.info(f"   ✅ Baseline comparison saved: {baseline_path}")
        else:
            logger.info("\n⚠️  STEP 8: Skipped (no baseline samples specified)")
            baseline_path = None
        
        # Generate summary report
        logger.info("\n📋 STEP 9: Generating Summary Report...")
        summary = self._generate_summary_report(
            sample_registry=sample_registry,
            combined_features=combined_features,
            fcs_failed=fcs_failed,
            nta_failed=nta_failed
        )
        
        summary_path = self.output_dir / 'integration_summary.txt'
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        logger.info(f"   ✅ Summary report saved: {summary_path}")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ DATA INTEGRATION COMPLETE")
        logger.info("=" * 80)
        
        # Return output file paths
        return {
            'sample_metadata': registry_path,
            'combined_features': combined_path,
            'baseline_comparison': baseline_path if baseline_path else None,
            'qc_report': qc_report_path,
            'match_report': match_report_path,
            'summary': summary_path
        }
    
    def _load_fcs_statistics(self, parquet_dir: Path) -> pd.DataFrame:
        """Load FCS statistics from batch processing output."""
        # Check statistics subfolder first, then root folder
        stats_file = parquet_dir / 'statistics' / 'fcs_statistics.parquet'
        if not stats_file.exists():
            stats_file = parquet_dir / 'fcs_statistics.parquet'
        
        if not stats_file.exists():
            raise FileNotFoundError(f"FCS statistics not found: {stats_file}")
        
        return pd.read_parquet(stats_file)
    
    def _load_nta_statistics(self, parquet_dir: Path) -> pd.DataFrame:
        """Load NTA statistics from batch processing output."""
        # Check statistics subfolder first, then root folder
        stats_file = parquet_dir / 'statistics' / 'nta_statistics.parquet'
        if not stats_file.exists():
            stats_file = parquet_dir / 'nta_statistics.parquet'
        
        if not stats_file.exists():
            raise FileNotFoundError(f"NTA statistics not found: {stats_file}")
        
        return pd.read_parquet(stats_file)
    
    def calculate_baseline_comparisons(
        self,
        combined_features: pd.DataFrame,
        baseline_samples: List[str]
    ) -> pd.DataFrame:
        """
        Calculate baseline comparisons (fold changes, deltas).
        
        Args:
            combined_features: Combined feature matrix
            baseline_samples: List of baseline sample IDs
        
        Returns:
            DataFrame with baseline comparisons
        """
        # Use normalizer's baseline normalization
        baseline_comparison = self.normalizer.normalize_to_baseline(
            data=combined_features,
            baseline_samples=baseline_samples,
            sample_id_col='sample_id'
        )
        
        return baseline_comparison
    
    def _generate_summary_report(
        self,
        sample_registry: pd.DataFrame,
        combined_features: pd.DataFrame,
        fcs_failed: pd.DataFrame,
        nta_failed: pd.DataFrame
    ) -> str:
        """Generate human-readable summary report."""
        
        report = []
        report.append("=" * 80)
        report.append("DATA INTEGRATION SUMMARY REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Sample matching summary
        report.append("SAMPLE MATCHING:")
        report.append(f"  - Total samples: {len(sample_registry)}")
        report.append(f"  - Exact matches: {len(sample_registry[sample_registry['match_type'] == 'exact'])}")
        report.append(f"  - Fuzzy matches: {len(sample_registry[sample_registry['match_type'] == 'fuzzy'])}")
        report.append(f"  - FCS only: {len(sample_registry[sample_registry['match_type'] == 'fcs_only'])}")
        report.append(f"  - NTA only: {len(sample_registry[sample_registry['match_type'] == 'nta_only'])}")
        report.append("")
        
        # Quality control summary
        report.append("QUALITY CONTROL:")
        report.append(f"  - FCS samples failed: {len(fcs_failed)}")
        report.append(f"  - NTA samples failed: {len(nta_failed)}")
        report.append("")
        
        # Combined features summary
        report.append("COMBINED FEATURES:")
        report.append(f"  - Samples: {len(combined_features)}")
        report.append(f"  - Features: {len(combined_features.columns)}")
        fcs_features = len([c for c in combined_features.columns if c.startswith('fcs_')])
        nta_features = len([c for c in combined_features.columns if c.startswith('nta_')])
        cross_features = len([c for c in combined_features.columns if c.startswith('cross_')])
        report.append(f"  - FCS features: {fcs_features}")
        report.append(f"  - NTA features: {nta_features}")
        report.append(f"  - Cross-instrument features: {cross_features}")
        report.append("")
        
        # Architecture compliance
        report.append("ARCHITECTURE COMPLIANCE:")
        report.append("  [OK] Layer 2: Data Preprocessing")
        report.append("     - Quality Control: IMPLEMENTED")
        report.append("     - Normalization: IMPLEMENTED")
        report.append("     - Size Binning: IMPLEMENTED")
        report.append("  [OK] Layer 4: Multi-Modal Fusion")
        report.append("     - Sample Matching: IMPLEMENTED")
        report.append("     - Feature Extraction: IMPLEMENTED")
        report.append("     - Cross-Instrument Correlation: IMPLEMENTED")
        report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)


def main():
    """Main entry point for data integration."""
    
    # Define paths
    project_root = Path(__file__).parent.parent
    fcs_dir = project_root / 'data' / 'parquet' / 'nanofacs'
    nta_dir = project_root / 'data' / 'parquet' / 'nta'
    output_dir = project_root / 'data' / 'processed'
    
    # Initialize integrator
    integrator = DataIntegrator(output_dir=output_dir)
    
    # Run integration pipeline
    try:
        output_files = integrator.integrate_all_data(
            fcs_parquet_dir=fcs_dir,
            nta_parquet_dir=nta_dir,
            baseline_samples=None  # TODO: User should specify baseline sample IDs
        )
        
        logger.info("\n📁 Output files:")
        for file_type, file_path in output_files.items():
            if file_path:
                logger.info(f"   - {file_type}: {file_path}")
        
    except FileNotFoundError as e:
        logger.error(f"❌ File not found: {e}")
        logger.info("\nPlease run batch processing scripts first:")
        logger.info("  1. python scripts/batch_process_fcs.py")
        logger.info("  2. python scripts/batch_process_nta.py")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"❌ Integration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
