"""
Statistical Analysis Router
============================

Endpoints for statistical tests between samples.

Endpoints:
- POST /analysis/statistical-tests  - Run statistical tests between sample groups
- POST /analysis/population-shift   - Detect population shifts between samples (CRMIT-004)
- POST /analysis/population-shift/baseline - Compare samples to baseline
- POST /analysis/population-shift/temporal - Temporal drift detection
- POST /analysis/temporal-analysis   - Time-series trend analysis (CRMIT-007)
- POST /analysis/temporal-analysis/multi-metric - Multi-metric temporal analysis

Implements Mann-Whitney U, Kolmogorov-Smirnov, and T-tests using scipy.stats.

Author: CRMIT Backend Team
Date: November 21, 2025
Updated: January 2, 2026 - Added CRMIT-007 Temporal Analysis
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore[import-not-found]
from sqlalchemy import select  # type: ignore[import-not-found]
from pydantic import BaseModel, Field
from loguru import logger
import numpy as np

try:
    from scipy import stats  # type: ignore[import-not-found]
except ImportError:
    stats = None
    logger.warning("scipy not installed - statistical tests will be limited")

from src.database.connection import get_session
from src.database.models import Sample, FCSResult, NTAResult  # type: ignore[import-not-found]
from src.parsers.fcs_parser import FCSParser  # type: ignore[import-not-found]

# Import population shift detection (CRMIT-004)
try:
    from src.analysis.population_shift import (
        PopulationShiftDetector, 
        ComparisonMode,
        ShiftSeverity
    )
    POPULATION_SHIFT_AVAILABLE = True
except ImportError:
    POPULATION_SHIFT_AVAILABLE = False
    PopulationShiftDetector = None  # type: ignore[misc, assignment]
    logger.warning("Population shift module not available")

# Import temporal analysis (CRMIT-007)
try:
    from src.analysis.temporal_analysis import TemporalAnalyzer
    TEMPORAL_ANALYSIS_AVAILABLE = True
except ImportError:
    TEMPORAL_ANALYSIS_AVAILABLE = False
    TemporalAnalyzer = None  # type: ignore[misc, assignment]
    logger.warning("Temporal analysis module not available")


def _safe_get_float(obj: Any, *attrs: str, default: float = 0.0) -> float:
    """Safely get a float value from an ORM object's attributes.
    
    Tries attributes in order, returns first non-None value as float.
    """
    for attr in attrs:
        val = getattr(obj, attr, None)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return default


router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class StatisticalTestRequest(BaseModel):
    """Request model for statistical tests."""
    sample_ids_group_a: List[str] = Field(..., description="Sample IDs for group A")
    sample_ids_group_b: List[str] = Field(..., description="Sample IDs for group B")
    metrics: List[str] = Field(
        default=["fsc_median", "ssc_median", "particle_size_median_nm"],
        description="Metrics to compare"
    )
    test_types: List[str] = Field(
        default=["mann_whitney", "ks_test"],
        description="Statistical tests to run: mann_whitney, ks_test, t_test, welch_t_test"
    )
    alpha: float = Field(default=0.05, ge=0.001, le=0.5, description="Significance level")


class TestResult(BaseModel):
    """Result from a single statistical test."""
    test_name: str
    metric: str
    statistic: float
    p_value: float
    significant: bool
    effect_size: Optional[float] = None
    interpretation: str


class GroupStatistics(BaseModel):
    """Descriptive statistics for a group."""
    group_name: str
    n_samples: int
    mean: float
    std: float
    median: float
    min_val: float
    max_val: float


class MetricComparison(BaseModel):
    """Comparison results for a single metric."""
    metric: str
    group_a_stats: GroupStatistics
    group_b_stats: GroupStatistics
    tests: List[TestResult]


class StatisticalTestResponse(BaseModel):
    """Response model for statistical tests."""
    success: bool
    message: str
    group_a_samples: List[str]
    group_b_samples: List[str]
    comparisons: List[MetricComparison]
    summary: dict


# ============================================================================
# Helper Functions
# ============================================================================

def calculate_effect_size(group_a: np.ndarray, group_b: np.ndarray, test_type: str) -> Optional[float]:
    """Calculate effect size (Cohen's d for t-tests, rank-biserial for Mann-Whitney)."""
    if test_type in ["t_test", "welch_t_test"]:
        # Cohen's d
        pooled_std = np.sqrt(
            ((len(group_a) - 1) * np.std(group_a, ddof=1)**2 + 
             (len(group_b) - 1) * np.std(group_b, ddof=1)**2) /
            (len(group_a) + len(group_b) - 2)
        )
        if pooled_std > 0:
            return float((np.mean(group_a) - np.mean(group_b)) / pooled_std)
    elif test_type == "mann_whitney":
        # Rank-biserial correlation
        n1, n2 = len(group_a), len(group_b)
        if n1 > 0 and n2 > 0 and stats is not None:
            u_stat, _ = stats.mannwhitneyu(group_a, group_b, alternative='two-sided')
            r = 1 - (2 * float(u_stat)) / (n1 * n2)
            return float(r)
    return None


def interpret_effect_size(effect_size: Optional[float], test_type: str) -> str:
    """Interpret effect size magnitude."""
    if effect_size is None:
        return "Effect size not calculated"
    
    abs_effect = abs(effect_size)
    
    if test_type in ["t_test", "welch_t_test"]:
        # Cohen's d thresholds
        if abs_effect < 0.2:
            return "Negligible effect"
        elif abs_effect < 0.5:
            return "Small effect"
        elif abs_effect < 0.8:
            return "Medium effect"
        else:
            return "Large effect"
    else:
        # Rank-biserial correlation thresholds
        if abs_effect < 0.1:
            return "Negligible effect"
        elif abs_effect < 0.3:
            return "Small effect"
        elif abs_effect < 0.5:
            return "Medium effect"
        else:
            return "Large effect"


def run_statistical_test(
    group_a: np.ndarray, 
    group_b: np.ndarray, 
    test_type: str,
    metric: str,
    alpha: float = 0.05
) -> TestResult:
    """Run a single statistical test and return results."""
    
    if stats is None:
        return TestResult(
            test_name=test_type,
            metric=metric,
            statistic=0.0,
            p_value=1.0,
            significant=False,
            interpretation="scipy not installed - statistical tests unavailable"
        )
    
    try:
        if test_type == "mann_whitney":
            result = stats.mannwhitneyu(group_a, group_b, alternative='two-sided')
            statistic_float = float(getattr(result, 'statistic', 0.0))
            p_value_float = float(getattr(result, 'pvalue', 1.0))
            test_name = "Mann-Whitney U Test"
        
        elif test_type == "ks_test":
            result = stats.ks_2samp(group_a, group_b)
            statistic_float = float(getattr(result, 'statistic', 0.0))
            p_value_float = float(getattr(result, 'pvalue', 1.0))
            test_name = "Kolmogorov-Smirnov Test"
        
        elif test_type == "t_test":
            result = stats.ttest_ind(group_a, group_b, equal_var=True)
            statistic_float = float(getattr(result, 'statistic', 0.0))
            p_value_float = float(getattr(result, 'pvalue', 1.0))
            test_name = "Independent T-Test"
        
        elif test_type == "welch_t_test":
            result = stats.ttest_ind(group_a, group_b, equal_var=False)
            statistic_float = float(getattr(result, 'statistic', 0.0))
            p_value_float = float(getattr(result, 'pvalue', 1.0))
            test_name = "Welch's T-Test"
        
        else:
            raise ValueError(f"Unknown test type: {test_type}")
        
        effect_size = calculate_effect_size(group_a, group_b, test_type)
        significant = p_value_float < alpha
        
        # Build interpretation
        if significant:
            effect_interp = interpret_effect_size(effect_size, test_type)
            interpretation = f"Significant difference (p={p_value_float:.4f}). {effect_interp}"
        else:
            interpretation = f"No significant difference (p={p_value_float:.4f})"
        
        return TestResult(
            test_name=test_name,
            metric=metric,
            statistic=statistic_float,
            p_value=p_value_float,
            significant=significant,
            effect_size=effect_size,
            interpretation=interpretation
        )
        
    except Exception as e:
        logger.error(f"Statistical test failed: {e}")
        return TestResult(
            test_name=test_type,
            metric=metric,
            statistic=0.0,
            p_value=1.0,
            significant=False,
            interpretation=f"Test failed: {str(e)}"
        )


# ============================================================================
# Statistical Tests Endpoint
# ============================================================================

@router.post("/statistical-tests", response_model=StatisticalTestResponse)
async def run_statistical_tests(
    request: StatisticalTestRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Run statistical tests comparing two groups of samples.
    
    **Supported Tests:**
    - `mann_whitney`: Mann-Whitney U test (non-parametric, recommended for small samples)
    - `ks_test`: Kolmogorov-Smirnov test (compares distributions)
    - `t_test`: Independent samples t-test (assumes equal variances)
    - `welch_t_test`: Welch's t-test (does not assume equal variances)
    
    **Supported Metrics:**
    - FCS: `fsc_median`, `ssc_median`, `fsc_mean`, `ssc_mean`, `particle_size_median_nm`, `debris_pct`
    - NTA: `mean_size_nm`, `median_size_nm`, `d10_nm`, `d50_nm`, `d90_nm`, `concentration_particles_ml`
    
    **Response:**
    ```json
    {
        "success": true,
        "comparisons": [
            {
                "metric": "particle_size_median_nm",
                "group_a_stats": {"mean": 85.2, "std": 12.3, ...},
                "group_b_stats": {"mean": 102.5, "std": 15.1, ...},
                "tests": [
                    {"test_name": "Mann-Whitney U", "p_value": 0.023, "significant": true, ...}
                ]
            }
        ],
        "summary": {
            "total_tests": 4,
            "significant_tests": 2
        }
    }
    ```
    """
    logger.info(f"📊 Running statistical tests between groups")
    logger.info(f"   Group A: {request.sample_ids_group_a}")
    logger.info(f"   Group B: {request.sample_ids_group_b}")
    logger.info(f"   Metrics: {request.metrics}")
    logger.info(f"   Tests: {request.test_types}")
    
    # Validate inputs
    if len(request.sample_ids_group_a) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group A must have at least 2 samples for statistical analysis"
        )
    
    if len(request.sample_ids_group_b) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group B must have at least 2 samples for statistical analysis"
        )
    
    # Collect data for each group
    group_a_data: dict[str, list] = {metric: [] for metric in request.metrics}
    group_b_data: dict[str, list] = {metric: [] for metric in request.metrics}
    
    async def collect_sample_metrics(sample_id: str, target_dict: dict[str, list]) -> bool:
        """Collect metrics from a sample."""
        # Get sample
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        if not sample:
            logger.warning(f"Sample not found: {sample_id}")
            return False
        
        # Get FCS results
        fcs_result = await db.execute(
            select(FCSResult).where(FCSResult.sample_id == sample.id)
        )
        fcs = fcs_result.scalar_one_or_none()
        
        # Get NTA results
        nta_result = await db.execute(
            select(NTAResult).where(NTAResult.sample_id == sample.id)
        )
        nta = nta_result.scalar_one_or_none()
        
        # Extract metrics
        for metric in request.metrics:
            value = None
            
            # Try FCS results first
            if fcs and hasattr(fcs, metric):
                value = getattr(fcs, metric)
            # Then try NTA results
            elif nta and hasattr(nta, metric):
                value = getattr(nta, metric)
            
            if value is not None:
                target_dict[metric].append(float(value))
        
        return True
    
    # Collect Group A data
    for sample_id in request.sample_ids_group_a:
        await collect_sample_metrics(sample_id, group_a_data)
    
    # Collect Group B data
    for sample_id in request.sample_ids_group_b:
        await collect_sample_metrics(sample_id, group_b_data)
    
    # Run comparisons for each metric
    comparisons: List[MetricComparison] = []
    total_tests = 0
    significant_tests = 0
    
    for metric in request.metrics:
        data_a = np.array(group_a_data.get(metric, []))
        data_b = np.array(group_b_data.get(metric, []))
        
        # Skip if insufficient data
        if len(data_a) < 2 or len(data_b) < 2:
            logger.warning(f"Insufficient data for metric {metric}: A={len(data_a)}, B={len(data_b)}")
            continue
        
        # Calculate group statistics
        group_a_stats = GroupStatistics(
            group_name="Group A",
            n_samples=len(data_a),
            mean=float(np.mean(data_a)),
            std=float(np.std(data_a, ddof=1)) if len(data_a) > 1 else 0.0,
            median=float(np.median(data_a)),
            min_val=float(np.min(data_a)),
            max_val=float(np.max(data_a))
        )
        
        group_b_stats = GroupStatistics(
            group_name="Group B",
            n_samples=len(data_b),
            mean=float(np.mean(data_b)),
            std=float(np.std(data_b, ddof=1)) if len(data_b) > 1 else 0.0,
            median=float(np.median(data_b)),
            min_val=float(np.min(data_b)),
            max_val=float(np.max(data_b))
        )
        
        # Run requested tests
        tests: List[TestResult] = []
        for test_type in request.test_types:
            result = run_statistical_test(data_a, data_b, test_type, metric, request.alpha)
            tests.append(result)
            total_tests += 1
            if result.significant:
                significant_tests += 1
        
        comparisons.append(MetricComparison(
            metric=metric,
            group_a_stats=group_a_stats,
            group_b_stats=group_b_stats,
            tests=tests
        ))
    
    if not comparisons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid comparisons could be made. Ensure samples have the requested metrics."
        )
    
    logger.success(f"✅ Completed {total_tests} statistical tests ({significant_tests} significant)")
    
    return StatisticalTestResponse(
        success=True,
        message=f"Completed {total_tests} statistical tests",
        group_a_samples=request.sample_ids_group_a,
        group_b_samples=request.sample_ids_group_b,
        comparisons=comparisons,
        summary={
            "total_tests": total_tests,
            "significant_tests": significant_tests,
            "significance_level": request.alpha,
            "metrics_compared": len(comparisons)
        }
    )


# ============================================================================
# Distribution Comparison Endpoint
# ============================================================================

@router.post("/distribution-comparison", response_model=dict)
async def compare_distributions(
    sample_id_a: str,
    sample_id_b: str,
    channel: str = "FSC",
    db: AsyncSession = Depends(get_session)
):
    """
    Compare raw data distributions between two samples.
    
    Returns histogram data and KS test results for visualization.
    
    **Use Case:** Detailed comparison of event-level distributions
    for quality control or treatment effect analysis.
    """
    logger.info(f"📊 Comparing distributions: {sample_id_a} vs {sample_id_b} ({channel})")
    
    # Get sample A
    result_a = await db.execute(select(Sample).where(Sample.sample_id == sample_id_a))
    sample_a = result_a.scalar_one_or_none()
    
    if sample_a is None or sample_a.file_path_fcs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample {sample_id_a} not found or has no FCS file"
        )
    
    # Get sample B
    result_b = await db.execute(select(Sample).where(Sample.sample_id == sample_id_b))
    sample_b = result_b.scalar_one_or_none()
    
    if sample_b is None or sample_b.file_path_fcs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample {sample_id_b} not found or has no FCS file"
        )
    
    try:
        # Parse FCS files
        from pathlib import Path as PathLib
        parser_a = FCSParser(PathLib(str(sample_a.file_path_fcs)))
        data_a = parser_a.parse()
        
        parser_b = FCSParser(PathLib(str(sample_b.file_path_fcs)))
        data_b = parser_b.parse()
        
        # Find matching channel - use channel_names attribute after parsing
        channels_a = parser_a.channel_names
        channels_b = parser_b.channel_names
        
        channel_a = None
        channel_b = None
        
        for ch in channels_a:
            if channel.upper() in ch.upper():
                channel_a = ch
                break
        
        for ch in channels_b:
            if channel.upper() in ch.upper():
                channel_b = ch
                break
        
        if not channel_a or not channel_b:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Channel {channel} not found in both samples"
            )
        
        # Extract data - convert to numpy arrays for type safety
        values_a = np.asarray(data_a[channel_a].values)
        values_b = np.asarray(data_b[channel_b].values)
        
        # Create histograms (50 bins)
        all_values = np.concatenate([values_a, values_b])
        bins = np.linspace(float(np.percentile(all_values, 1)), float(np.percentile(all_values, 99)), 51)
        
        hist_a, _ = np.histogram(values_a, bins=bins, density=True)
        hist_b, _ = np.histogram(values_b, bins=bins, density=True)
        
        # KS test
        if stats is not None:
            ks_result = stats.ks_2samp(values_a, values_b)
            ks_stat = float(getattr(ks_result, 'statistic', 0.0))
            ks_pval = float(getattr(ks_result, 'pvalue', 1.0))
        else:
            ks_stat = 0.0
            ks_pval = 1.0
        
        return {
            "success": True,
            "sample_a": {
                "sample_id": sample_id_a,
                "channel": channel_a,
                "n_events": len(values_a),
                "mean": float(np.mean(values_a)),
                "median": float(np.median(values_a)),
                "std": float(np.std(values_a))
            },
            "sample_b": {
                "sample_id": sample_id_b,
                "channel": channel_b,
                "n_events": len(values_b),
                "mean": float(np.mean(values_b)),
                "median": float(np.median(values_b)),
                "std": float(np.std(values_b))
            },
            "histograms": {
                "bins": bins.tolist(),
                "sample_a": hist_a.tolist(),
                "sample_b": hist_b.tolist()
            },
            "ks_test": {
                "statistic": ks_stat,
                "p_value": ks_pval,
                "significant": ks_pval < 0.05
            }
        }
        
    except Exception as e:
        logger.exception(f"Distribution comparison failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare distributions: {str(e)}"
        )


# ============================================================================
# Parquet Export Endpoints
# ============================================================================

class ExportRequest(BaseModel):
    """Request model for data export."""
    sample_id: str = Field(..., description="Sample ID to export")
    data_type: str = Field("fcs", description="Type of data: 'fcs' or 'nta'")
    include_metadata: bool = Field(True, description="Include sample metadata")
    include_statistics: bool = Field(True, description="Include computed statistics")


@router.post("/export/parquet")
async def export_to_parquet(
    request: ExportRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Export sample analysis results to Parquet format.
    
    Returns a base64-encoded Parquet file content that can be decoded and saved
    on the client side.
    
    **Request Body:**
    - sample_id: Sample identifier
    - data_type: "fcs" or "nta"
    - include_metadata: Whether to include sample metadata
    - include_statistics: Whether to include computed statistics
    
    **Response:**
    Returns a JSON with base64-encoded parquet content and metadata.
    """
    try:
        import pandas as pd
        import pyarrow as pa
        import pyarrow.parquet as pq
        import io
        import base64
        from datetime import datetime
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Required packages not installed: {e}. Install pyarrow and pandas."
        )
    
    try:
        # Find sample
        sample_query = select(Sample).where(Sample.sample_id == request.sample_id)
        sample_result = await db.execute(sample_query)
        sample = sample_result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample '{request.sample_id}' not found"
            )
        
        data_frames = []
        export_metadata = {
            "sample_id": request.sample_id,
            "data_type": request.data_type,
            "export_timestamp": datetime.utcnow().isoformat(),
        }
        
        if request.data_type == "fcs":
            # Get FCS results
            fcs_query = select(FCSResult).where(FCSResult.sample_id == sample.id)
            fcs_result = await db.execute(fcs_query)
            fcs_data = fcs_result.scalar_one_or_none()
            
            if not fcs_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No FCS results found for sample '{request.sample_id}'"
                )
            
            # Build FCS export dataframe
            fcs_dict = {
                "sample_id": request.sample_id,
                "total_events": fcs_data.total_events,
                "fsc_median": fcs_data.fsc_median,
                "fsc_mean": fcs_data.fsc_mean,
                "fsc_std": fcs_data.fsc_std,
                "ssc_median": fcs_data.ssc_median,
                "ssc_mean": fcs_data.ssc_mean,
                "ssc_std": fcs_data.ssc_std,
            }
            
            if request.include_statistics:
                fcs_dict.update({
                    "fsc_cv_pct": fcs_data.fsc_cv_pct,
                    "ssc_cv_pct": fcs_data.ssc_cv_pct,
                    "particle_size_median_nm": fcs_data.particle_size_median_nm,
                    "particle_size_mean_nm": fcs_data.particle_size_mean_nm,
                    "noise_events_removed": fcs_data.noise_events_removed,
                    "gated_events": fcs_data.gated_events,
                })
            
            data_frames.append(pd.DataFrame([fcs_dict]))
            export_metadata["fcs_total_events"] = str(fcs_data.total_events)
            
        elif request.data_type == "nta":
            # Get NTA results
            nta_query = select(NTAResult).where(NTAResult.sample_id == sample.id)
            nta_result = await db.execute(nta_query)
            nta_data = nta_result.scalar_one_or_none()
            
            if not nta_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No NTA results found for sample '{request.sample_id}'"
                )
            
            # Build NTA export dataframe
            nta_dict = {
                "sample_id": request.sample_id,
                "total_particles": nta_data.total_particles,
                "mean_size_nm": nta_data.mean_size_nm,
                "median_size_nm": nta_data.median_size_nm,
                "mode_size_nm": nta_data.mode_size_nm,
                "d10_nm": nta_data.d10_nm,
                "d50_nm": nta_data.d50_nm,
                "d90_nm": nta_data.d90_nm,
                "concentration_particles_ml": nta_data.concentration_particles_ml,
            }
            
            if request.include_statistics:
                nta_dict.update({
                    "temperature_celsius": nta_data.temperature_celsius,
                    "viscosity_cp": nta_data.viscosity_cp,
                    "bin_50_80nm_pct": nta_data.bin_50_80nm_pct,
                    "bin_80_100nm_pct": nta_data.bin_80_100nm_pct,
                    "bin_100_120nm_pct": nta_data.bin_100_120nm_pct,
                    "bin_120_150nm_pct": nta_data.bin_120_150nm_pct,
                    "bin_150_200nm_pct": nta_data.bin_150_200nm_pct,
                    "bin_200_plus_pct": nta_data.bin_200_plus_pct,
                })
            
            data_frames.append(pd.DataFrame([nta_dict]))
            export_metadata["nta_total_particles"] = nta_data.total_particles
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid data_type: {request.data_type}. Must be 'fcs' or 'nta'."
            )
        
        # Combine all dataframes
        export_df = pd.concat(data_frames, ignore_index=True) if data_frames else pd.DataFrame()
        
        # Add metadata columns if requested
        if request.include_metadata:
            export_df["treatment"] = sample.treatment
            export_df["operator"] = sample.operator
            export_df["upload_timestamp"] = str(sample.upload_timestamp)
        
        # Convert to Parquet in memory
        buffer = io.BytesIO()
        table = pa.Table.from_pandas(export_df)
        pq.write_table(table, buffer)
        parquet_bytes = buffer.getvalue()
        
        # Encode as base64
        parquet_base64 = base64.b64encode(parquet_bytes).decode('utf-8')
        
        return {
            "success": True,
            "filename": f"{request.sample_id}_{request.data_type}_export.parquet",
            "content_base64": parquet_base64,
            "size_bytes": len(parquet_bytes),
            "metadata": export_metadata,
            "columns": list(export_df.columns),
            "rows": len(export_df)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Parquet export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export to Parquet: {str(e)}"
        )


# ============================================================================
# Population Shift Detection (CRMIT-004)
# ============================================================================

class PopulationShiftRequest(BaseModel):
    """Request model for population shift detection."""
    sample_id_a: str = Field(..., description="First sample ID for comparison")
    sample_id_b: str = Field(..., description="Second sample ID for comparison")
    metric: str = Field(
        default="particle_size",
        description="Metric to compare: particle_size, fsc, ssc, or NTA metrics"
    )
    data_source: str = Field(
        default="fcs",
        description="Data source: 'fcs' or 'nta'"
    )
    tests: List[str] = Field(
        default=["ks", "emd", "mean", "variance"],
        description="Statistical tests to run"
    )
    alpha: float = Field(
        default=0.05,
        ge=0.001,
        le=0.5,
        description="Significance level"
    )


class BaselineComparisonRequest(BaseModel):
    """Request for comparing multiple samples to a baseline."""
    baseline_sample_id: str = Field(..., description="Baseline/reference sample ID")
    sample_ids: List[str] = Field(..., description="Sample IDs to compare against baseline")
    metric: str = Field(default="particle_size", description="Metric to compare")
    data_source: str = Field(default="fcs", description="Data source: 'fcs' or 'nta'")
    tests: List[str] = Field(default=["ks", "emd", "mean", "variance"])
    alpha: float = Field(default=0.05)


class TemporalComparisonRequest(BaseModel):
    """Request for temporal/sequential comparison."""
    sample_ids: List[str] = Field(
        ..., 
        min_length=2,
        description="Sample IDs in temporal order"
    )
    metric: str = Field(default="particle_size", description="Metric to compare")
    data_source: str = Field(default="fcs", description="Data source: 'fcs' or 'nta'")
    tests: List[str] = Field(default=["ks", "emd", "mean", "variance"])
    alpha: float = Field(default=0.05)


class ShiftTestResultResponse(BaseModel):
    """Single test result in response."""
    test_name: str
    statistic: float
    p_value: float
    significant: bool
    effect_size: Optional[float] = None
    severity: str
    interpretation: str


class PopulationMetricsResponse(BaseModel):
    """Population metrics in response."""
    sample_id: str
    sample_name: str
    n_events: int
    mean: float
    median: float
    std: float
    iqr: float
    skewness: float
    kurtosis: float
    percentiles: Dict[int, float]


class PopulationShiftResponse(BaseModel):
    """Response for population shift detection."""
    success: bool
    sample_a: PopulationMetricsResponse
    sample_b: PopulationMetricsResponse
    metric_name: str
    tests: List[ShiftTestResultResponse]
    overall_shift_detected: bool
    overall_severity: str
    summary: str
    recommendations: List[str]


class MultiSampleShiftResponse(BaseModel):
    """Response for multi-sample shift analysis."""
    success: bool
    mode: str
    baseline_sample: Optional[str]
    comparisons: List[PopulationShiftResponse]
    global_summary: str
    any_significant_shift: bool
    max_severity: str


async def get_sample_data_for_shift(
    db: AsyncSession,
    sample_id: str,
    metric: str,
    data_source: str
) -> tuple[np.ndarray, str]:
    """
    Get sample data for population shift analysis.
    
    Returns:
        Tuple of (data array, sample name)
    """
    # Get sample
    result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
    sample = result.scalar_one_or_none()
    
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample not found: {sample_id}"
        )
    
    sample_name = str(sample.sample_id)
    
    if data_source == "fcs":
        # Get FCS result
        fcs_result = await db.execute(
            select(FCSResult).where(FCSResult.sample_id == sample.id)
        )
        fcs = fcs_result.scalar_one_or_none()
        
        if not fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS data for sample: {sample_id}"
            )
        
        # Try to load raw event data from file
        # Use getattr for safe attribute access (SQLAlchemy type hints issue)
        file_path_fcs_val = getattr(sample, 'file_path_fcs', None)
        file_path_fcs = str(file_path_fcs_val) if file_path_fcs_val else None
        if file_path_fcs:
            try:
                from pathlib import Path
                
                # Handle both absolute and relative paths
                fcs_path = Path(file_path_fcs)
                if not fcs_path.is_absolute():
                    fcs_path = Path.cwd() / fcs_path
                
                if fcs_path.exists():
                    parser = FCSParser(file_path=fcs_path)
                    df = parser.parse()
                    
                    if df is not None and len(df) > 0:
                        # Get appropriate column based on metric
                        if metric == "particle_size" and "Size_nm" in df.columns:
                            data = np.array(df["Size_nm"].dropna().values)
                        elif metric == "fsc":
                            fsc_cols = [c for c in df.columns if "FSC" in c.upper()]
                            if fsc_cols:
                                data = np.array(df[fsc_cols[0]].dropna().values)
                            else:
                                raise ValueError("No FSC channel found")
                        elif metric == "ssc":
                            ssc_cols = [c for c in df.columns if "SSC" in c.upper()]
                            if ssc_cols:
                                data = np.array(df[ssc_cols[0]].dropna().values)
                            else:
                                raise ValueError("No SSC channel found")
                        else:
                            # Try to find column matching metric
                            matching = [c for c in df.columns if metric.lower() in c.lower()]
                            if matching:
                                data = np.array(df[matching[0]].dropna().values)
                            else:
                                raise ValueError(f"Metric '{metric}' not found in data")
                        
                        return data, sample_name
            except Exception as e:
                logger.warning(f"Could not load raw FCS data: {e}")
        
        # Fallback to summary statistics (generate synthetic distribution)
        # This is a limitation - for full shift detection, raw data is preferred
        # Use getattr for safe access to ORM attributes
        median_size_attr = getattr(fcs, 'particle_size_median_nm', None)
        median_size = float(median_size_attr) if median_size_attr is not None else None
        total_events_attr = getattr(fcs, 'total_events', None)
        total_events = int(total_events_attr) if total_events_attr is not None else 1000
        
        if metric == "particle_size" and median_size:
            # Generate approximate distribution from summary stats
            # Estimate std from typical CV (~40% for EVs)
            std = median_size * 0.4
            data = np.random.lognormal(
                mean=np.log(median_size) - 0.5 * (std/median_size)**2,
                sigma=std/median_size,
                size=total_events
            )
            return data, sample_name
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retrieve metric '{metric}' for FCS sample {sample_id}"
        )
    
    elif data_source == "nta":
        # Get NTA result
        nta_result = await db.execute(
            select(NTAResult).where(NTAResult.sample_id == sample.id)
        )
        nta = nta_result.scalar_one_or_none()
        
        if not nta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No NTA data for sample: {sample_id}"
            )
        
        # For NTA, we typically only have summary statistics
        # Generate approximate distribution
        if metric in ["particle_size", "size", "d50"]:
            # Extract values safely with getattr (SQLAlchemy type hints issue)
            d50_attr = getattr(nta, 'd50_nm', None)
            median_size_attr = getattr(nta, 'median_size_nm', None)
            d50_val = float(d50_attr) if d50_attr is not None else None
            median_size_val = float(median_size_attr) if median_size_attr is not None else None
            median = d50_val or median_size_val
            
            if not median:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No size data available for NTA sample"
                )
            
            # Use d10/d90 to estimate distribution width if available
            d10_attr = getattr(nta, 'd10_nm', None)
            d90_attr = getattr(nta, 'd90_nm', None)
            d10_val = float(d10_attr) if d10_attr is not None else None
            d90_val = float(d90_attr) if d90_attr is not None else None
            
            if d10_val and d90_val:
                iqr_estimate = d90_val - d10_val
                std = iqr_estimate / 2.56  # Approximate for normal
            else:
                std = median * 0.3  # Default CV of 30%
            
            # Generate lognormal distribution (typical for EV sizes)
            data = np.random.lognormal(
                mean=np.log(median) - 0.5 * (std/median)**2,
                sigma=std/median,
                size=10000
            )
            return data, sample_name
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retrieve metric '{metric}' for NTA sample {sample_id}"
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data_source: {data_source}. Must be 'fcs' or 'nta'"
        )


@router.post("/population-shift", response_model=PopulationShiftResponse)
async def detect_population_shift(
    request: PopulationShiftRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Detect population shift between two samples.
    
    CRMIT-004: Compares particle populations using multiple statistical tests:
    
    **Tests Available:**
    - `ks`: Kolmogorov-Smirnov test (distribution comparison)
    - `emd`: Earth Mover's Distance (quantitative distribution difference)
    - `mean`: Welch's t-test (mean shift detection)
    - `variance`: Levene's test (variance change detection)
    
    **Metrics:**
    - `particle_size`: Particle size distribution (nm)
    - `fsc`: Forward scatter values
    - `ssc`: Side scatter values
    
    **Response includes:**
    - Statistical test results with p-values and effect sizes
    - Severity classification (none/minor/moderate/major/critical)
    - Actionable recommendations
    
    **Example:**
    ```json
    {
        "sample_id_a": "Control_Sample",
        "sample_id_b": "Treatment_Sample",
        "metric": "particle_size",
        "data_source": "fcs",
        "tests": ["ks", "emd", "mean", "variance"],
        "alpha": 0.05
    }
    ```
    """
    logger.info(f"🔬 Population shift detection: {request.sample_id_a} vs {request.sample_id_b}")
    
    if not POPULATION_SHIFT_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Population shift detection module not available"
        )
    
    try:
        # Get data for both samples
        data_a, name_a = await get_sample_data_for_shift(
            db, request.sample_id_a, request.metric, request.data_source
        )
        data_b, name_b = await get_sample_data_for_shift(
            db, request.sample_id_b, request.metric, request.data_source
        )
        
        # Run shift detection
        if PopulationShiftDetector is None:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Population shift detection module not available"
            )
        detector = PopulationShiftDetector(alpha=request.alpha)
        result = detector.detect_shift(
            data_a=data_a,
            data_b=data_b,
            sample_a_id=request.sample_id_a,
            sample_a_name=name_a,
            sample_b_id=request.sample_id_b,
            sample_b_name=name_b,
            metric_name=request.metric,
            tests=request.tests
        )
        
        # Convert to response format
        return PopulationShiftResponse(
            success=True,
            sample_a=PopulationMetricsResponse(
                sample_id=result.sample_a.sample_id,
                sample_name=result.sample_a.sample_name,
                n_events=result.sample_a.n_events,
                mean=result.sample_a.mean,
                median=result.sample_a.median,
                std=result.sample_a.std,
                iqr=result.sample_a.iqr,
                skewness=result.sample_a.skewness,
                kurtosis=result.sample_a.kurtosis,
                percentiles=result.sample_a.percentiles
            ),
            sample_b=PopulationMetricsResponse(
                sample_id=result.sample_b.sample_id,
                sample_name=result.sample_b.sample_name,
                n_events=result.sample_b.n_events,
                mean=result.sample_b.mean,
                median=result.sample_b.median,
                std=result.sample_b.std,
                iqr=result.sample_b.iqr,
                skewness=result.sample_b.skewness,
                kurtosis=result.sample_b.kurtosis,
                percentiles=result.sample_b.percentiles
            ),
            metric_name=result.metric_name,
            tests=[
                ShiftTestResultResponse(
                    test_name=t.test_name,
                    statistic=t.statistic,
                    p_value=t.p_value,
                    significant=t.significant,
                    effect_size=t.effect_size,
                    severity=t.severity.value,
                    interpretation=t.interpretation
                )
                for t in result.tests
            ],
            overall_shift_detected=result.overall_shift_detected,
            overall_severity=result.overall_severity.value,
            summary=result.summary,
            recommendations=result.recommendations
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Population shift detection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Population shift detection failed: {str(e)}"
        )


@router.post("/population-shift/baseline", response_model=MultiSampleShiftResponse)
async def compare_to_baseline(
    request: BaselineComparisonRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Compare multiple samples against a baseline/reference sample.
    
    Useful for quality control to detect samples that deviate from expected values.
    
    **Example:**
    ```json
    {
        "baseline_sample_id": "QC_Reference",
        "sample_ids": ["Batch1_Sample1", "Batch1_Sample2", "Batch2_Sample1"],
        "metric": "particle_size",
        "data_source": "fcs"
    }
    ```
    """
    logger.info(f"📊 Baseline comparison: {len(request.sample_ids)} samples vs {request.baseline_sample_id}")
    
    if not POPULATION_SHIFT_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Population shift detection module not available"
        )
    
    try:
        # Get baseline data
        baseline_data, baseline_name = await get_sample_data_for_shift(
            db, request.baseline_sample_id, request.metric, request.data_source
        )
        
        # Get data for all comparison samples
        sample_data_list = []
        for sample_id in request.sample_ids:
            try:
                data, name = await get_sample_data_for_shift(
                    db, sample_id, request.metric, request.data_source
                )
                sample_data_list.append((data, sample_id, name))
            except HTTPException as e:
                logger.warning(f"Skipping sample {sample_id}: {e.detail}")
        
        if not sample_data_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid samples to compare"
            )
        
        # Run baseline comparison
        if PopulationShiftDetector is None:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Population shift detection module not available"
            )
        detector = PopulationShiftDetector(alpha=request.alpha)
        result = detector.compare_to_baseline(
            baseline_data=baseline_data,
            baseline_id=request.baseline_sample_id,
            baseline_name=baseline_name,
            sample_data_list=sample_data_list,
            metric_name=request.metric,
            tests=request.tests
        )
        
        # Convert to response format
        comparisons = []
        for comp in result.comparisons:
            comparisons.append(PopulationShiftResponse(
                success=True,
                sample_a=PopulationMetricsResponse(
                    sample_id=comp.sample_a.sample_id,
                    sample_name=comp.sample_a.sample_name,
                    n_events=comp.sample_a.n_events,
                    mean=comp.sample_a.mean,
                    median=comp.sample_a.median,
                    std=comp.sample_a.std,
                    iqr=comp.sample_a.iqr,
                    skewness=comp.sample_a.skewness,
                    kurtosis=comp.sample_a.kurtosis,
                    percentiles=comp.sample_a.percentiles
                ),
                sample_b=PopulationMetricsResponse(
                    sample_id=comp.sample_b.sample_id,
                    sample_name=comp.sample_b.sample_name,
                    n_events=comp.sample_b.n_events,
                    mean=comp.sample_b.mean,
                    median=comp.sample_b.median,
                    std=comp.sample_b.std,
                    iqr=comp.sample_b.iqr,
                    skewness=comp.sample_b.skewness,
                    kurtosis=comp.sample_b.kurtosis,
                    percentiles=comp.sample_b.percentiles
                ),
                metric_name=comp.metric_name,
                tests=[
                    ShiftTestResultResponse(
                        test_name=t.test_name,
                        statistic=t.statistic,
                        p_value=t.p_value,
                        significant=t.significant,
                        effect_size=t.effect_size,
                        severity=t.severity.value,
                        interpretation=t.interpretation
                    )
                    for t in comp.tests
                ],
                overall_shift_detected=comp.overall_shift_detected,
                overall_severity=comp.overall_severity.value,
                summary=comp.summary,
                recommendations=comp.recommendations
            ))
        
        return MultiSampleShiftResponse(
            success=True,
            mode=result.mode.value,
            baseline_sample=result.baseline_sample,
            comparisons=comparisons,
            global_summary=result.global_summary,
            any_significant_shift=result.any_significant_shift,
            max_severity=result.max_severity.value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Baseline comparison failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Baseline comparison failed: {str(e)}"
        )


@router.post("/population-shift/temporal", response_model=MultiSampleShiftResponse)
async def temporal_shift_analysis(
    request: TemporalComparisonRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Detect population drift over time by comparing sequential samples.
    
    Compares each sample to its predecessor to detect gradual or sudden changes.
    
    **Example:**
    ```json
    {
        "sample_ids": ["Day1_Sample", "Day2_Sample", "Day3_Sample", "Day4_Sample"],
        "metric": "particle_size",
        "data_source": "fcs"
    }
    ```
    """
    logger.info(f"⏱️ Temporal shift analysis: {len(request.sample_ids)} time points")
    
    if not POPULATION_SHIFT_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Population shift detection module not available"
        )
    
    if len(request.sample_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Need at least 2 samples for temporal analysis"
        )
    
    try:
        # Get data for all samples in order
        temporal_data = []
        for sample_id in request.sample_ids:
            data, name = await get_sample_data_for_shift(
                db, sample_id, request.metric, request.data_source
            )
            temporal_data.append((data, sample_id, name))
        
        # Run temporal comparison
        if PopulationShiftDetector is None:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Population shift detection module not available"
            )
        detector = PopulationShiftDetector(alpha=request.alpha)
        result = detector.temporal_comparison(
            temporal_data=temporal_data,
            metric_name=request.metric,
            tests=request.tests
        )
        
        # Convert to response format
        comparisons = []
        for comp in result.comparisons:
            comparisons.append(PopulationShiftResponse(
                success=True,
                sample_a=PopulationMetricsResponse(
                    sample_id=comp.sample_a.sample_id,
                    sample_name=comp.sample_a.sample_name,
                    n_events=comp.sample_a.n_events,
                    mean=comp.sample_a.mean,
                    median=comp.sample_a.median,
                    std=comp.sample_a.std,
                    iqr=comp.sample_a.iqr,
                    skewness=comp.sample_a.skewness,
                    kurtosis=comp.sample_a.kurtosis,
                    percentiles=comp.sample_a.percentiles
                ),
                sample_b=PopulationMetricsResponse(
                    sample_id=comp.sample_b.sample_id,
                    sample_name=comp.sample_b.sample_name,
                    n_events=comp.sample_b.n_events,
                    mean=comp.sample_b.mean,
                    median=comp.sample_b.median,
                    std=comp.sample_b.std,
                    iqr=comp.sample_b.iqr,
                    skewness=comp.sample_b.skewness,
                    kurtosis=comp.sample_b.kurtosis,
                    percentiles=comp.sample_b.percentiles
                ),
                metric_name=comp.metric_name,
                tests=[
                    ShiftTestResultResponse(
                        test_name=t.test_name,
                        statistic=t.statistic,
                        p_value=t.p_value,
                        significant=t.significant,
                        effect_size=t.effect_size,
                        severity=t.severity.value,
                        interpretation=t.interpretation
                    )
                    for t in comp.tests
                ],
                overall_shift_detected=comp.overall_shift_detected,
                overall_severity=comp.overall_severity.value,
                summary=comp.summary,
                recommendations=comp.recommendations
            ))
        
        return MultiSampleShiftResponse(
            success=True,
            mode=result.mode.value,
            baseline_sample=result.baseline_sample,
            comparisons=comparisons,
            global_summary=result.global_summary,
            any_significant_shift=result.any_significant_shift,
            max_severity=result.max_severity.value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Temporal shift analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Temporal shift analysis failed: {str(e)}"
        )

# ============================================================================
# CRMIT-007: Temporal Analysis Endpoints
# ============================================================================

# Import temporal analysis module
try:
    from src.analysis.temporal_analysis import (
        TemporalAnalyzer,
        analyze_temporal_data,
        TrendType,
        StabilityLevel,
        DriftSeverity as TemporalDriftSeverity,
    )
    TEMPORAL_ANALYSIS_AVAILABLE = True
except ImportError:
    TEMPORAL_ANALYSIS_AVAILABLE = False
    logger.warning("Temporal analysis module not available")


# ---------------------- Temporal Analysis Request/Response Models ----------------------

class TemporalAnalysisRequest(BaseModel):
    """Request for temporal analysis of samples."""
    sample_ids: List[str] = Field(..., min_length=3, description="Sample IDs in chronological order")
    metric: str = Field(default="particle_size", description="Metric to analyze: particle_size, concentration, fsc, ssc")
    data_source: str = Field(default="fcs", description="Data source: fcs, nta")
    alpha: float = Field(default=0.05, ge=0.001, le=0.5, description="Significance level")
    include_correlations: bool = Field(default=True, description="Include cross-metric correlations")


class MultiMetricTemporalRequest(BaseModel):
    """Request for multi-metric temporal analysis."""
    sample_ids: List[str] = Field(..., min_length=3, description="Sample IDs in chronological order")
    metrics: List[str] = Field(
        default=["particle_size", "concentration", "fsc", "ssc"],
        description="Metrics to analyze"
    )
    data_source: str = Field(default="fcs", description="Data source: fcs, nta")
    alpha: float = Field(default=0.05, ge=0.001, le=0.5, description="Significance level")


class TrendResponse(BaseModel):
    """Trend analysis result."""
    type: str
    slope: float
    r_squared: float
    p_value: float
    is_significant: bool
    interpretation: str


class StabilityResponse(BaseModel):
    """Stability analysis result."""
    level: str
    mean: float
    std: float
    cv: float
    min_value: float
    max_value: float
    interpretation: str


class DriftResponse(BaseModel):
    """Drift detection result."""
    severity: str
    magnitude: float
    direction: str
    p_value: float
    is_significant: bool
    change_points: List[int]
    interpretation: str


class CorrelationResponse(BaseModel):
    """Correlation analysis result."""
    metric_a: str
    metric_b: str
    pearson_r: float
    spearman_rho: float
    strength: str
    is_significant: bool
    interpretation: str


class TemporalAnalysisResponse(BaseModel):
    """Response for temporal analysis."""
    success: bool
    metric: str
    n_points: int
    time_range: Dict[str, str]
    trend: TrendResponse
    stability: StabilityResponse
    drift: DriftResponse
    correlations: List[CorrelationResponse]
    moving_average: List[float]
    smoothed_values: List[float]
    summary: str
    recommendations: List[str]


class MultiMetricTemporalResponse(BaseModel):
    """Response for multi-metric temporal analysis."""
    success: bool
    sample_ids: List[str]
    n_samples: int
    time_range: Dict[str, Optional[str]]
    metrics_analyzed: List[str]
    individual_results: Dict[str, Any]
    overall_stability: Dict[str, Any]
    overall_drift: Dict[str, Any]


@router.post("/temporal-analysis", response_model=TemporalAnalysisResponse)
async def analyze_temporal_trends(
    request: TemporalAnalysisRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Perform temporal analysis on a series of samples (CRMIT-007).
    
    Analyzes time-series trends, stability, and drift in measurement data.
    
    **Features:**
    - Trend detection (linear, exponential)
    - Stability assessment (coefficient of variation)
    - Drift detection with change points
    - Cross-metric correlations
    
    **Parameters:**
    - sample_ids: List of sample IDs in chronological order (minimum 3)
    - metric: Metric to analyze (particle_size, concentration, fsc, ssc)
    - data_source: Data source (fcs, nta)
    - alpha: Significance level for statistical tests
    - include_correlations: Include cross-metric correlation analysis
    
    **Returns:**
    - Trend analysis (type, slope, significance)
    - Stability metrics (CV, mean, std)
    - Drift detection (severity, magnitude, change points)
    - Recommendations for action
    """
    if not TEMPORAL_ANALYSIS_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Temporal analysis module not available"
        )
    
    try:
        logger.info(f"🕐 Temporal analysis: {len(request.sample_ids)} samples, metric={request.metric}")
        
        # Collect sample data
        timestamps = []
        values = []
        additional_metrics: Dict[str, List[float]] = {}
        
        for sample_id in request.sample_ids:
            # Get sample
            result = await db.execute(
                select(Sample).where(Sample.sample_id == sample_id)
            )
            sample = result.scalar_one_or_none()
            
            if not sample:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Sample {sample_id} not found"
                )
            
            # Get timestamp (use upload_date or created_at)
            sample_time = sample.upload_date or sample.created_at
            if not sample_time:
                from datetime import datetime
                sample_time = datetime.now()
            timestamps.append(sample_time)
            
            # Get metric value based on data source
            if request.data_source == "fcs":
                fcs_result = await db.execute(
                    select(FCSResult).where(FCSResult.sample_id == sample.id)
                )
                fcs_data = fcs_result.scalar_one_or_none()
                
                if fcs_data:
                    # Get primary metric value with safe type conversion
                    if request.metric == "particle_size":
                        values.append(_safe_get_float(fcs_data, 'median_size_nm', 'mean_size_nm'))
                    elif request.metric == "concentration":
                        values.append(_safe_get_float(fcs_data, 'concentration', 'total_events'))
                    elif request.metric == "fsc":
                        values.append(_safe_get_float(fcs_data, 'fsc_median', 'fsc_mean'))
                    elif request.metric == "ssc":
                        values.append(_safe_get_float(fcs_data, 'ssc_median', 'ssc_mean'))
                    else:
                        values.append(_safe_get_float(fcs_data, 'median_size_nm'))
                    
                    # Collect additional metrics for correlation
                    if request.include_correlations:
                        if "particle_size" not in additional_metrics and request.metric != "particle_size":
                            additional_metrics.setdefault("particle_size", []).append(
                                _safe_get_float(fcs_data, 'median_size_nm', 'mean_size_nm')
                            )
                        if "fsc" not in additional_metrics and request.metric != "fsc":
                            additional_metrics.setdefault("fsc", []).append(
                                _safe_get_float(fcs_data, 'fsc_median', 'fsc_mean')
                            )
                        if "ssc" not in additional_metrics and request.metric != "ssc":
                            additional_metrics.setdefault("ssc", []).append(
                                _safe_get_float(fcs_data, 'ssc_median', 'ssc_mean')
                            )
                else:
                    values.append(0.0)
                    if request.include_correlations:
                        for key in ["particle_size", "fsc", "ssc"]:
                            if key != request.metric:
                                additional_metrics.setdefault(key, []).append(0.0)
            
            elif request.data_source == "nta":
                nta_result = await db.execute(
                    select(NTAResult).where(NTAResult.sample_id == sample.id)
                )
                nta_data = nta_result.scalar_one_or_none()
                
                if nta_data:
                    if request.metric == "particle_size":
                        values.append(_safe_get_float(nta_data, 'median_size_nm', 'mean_size_nm'))
                    elif request.metric == "concentration":
                        values.append(_safe_get_float(nta_data, 'concentration'))
                    else:
                        values.append(_safe_get_float(nta_data, 'median_size_nm'))
                    
                    if request.include_correlations:
                        if "concentration" not in additional_metrics and request.metric != "concentration":
                            additional_metrics.setdefault("concentration", []).append(
                                _safe_get_float(nta_data, 'concentration')
                            )
                else:
                    values.append(0.0)
        
        # Run temporal analysis
        if TemporalAnalyzer is None:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Temporal analysis module not available"
            )
        analyzer = TemporalAnalyzer(alpha=request.alpha)
        result = analyzer.analyze_time_series(
            timestamps=timestamps,
            values=values,
            metric_name=request.metric,
            additional_metrics=additional_metrics if request.include_correlations else None,
        )
        
        logger.success(f"✅ Temporal analysis complete: {result.summary}")
        
        return TemporalAnalysisResponse(
            success=True,
            metric=result.metric,
            n_points=result.n_points,
            time_range={
                "start": result.time_range[0].isoformat(),
                "end": result.time_range[1].isoformat(),
            },
            trend=TrendResponse(
                type=result.trend.trend_type.value,
                slope=result.trend.slope,
                r_squared=result.trend.r_squared,
                p_value=result.trend.p_value,
                is_significant=result.trend.is_significant,
                interpretation=result.trend.interpretation,
            ),
            stability=StabilityResponse(
                level=result.stability.level.value,
                mean=result.stability.mean,
                std=result.stability.std,
                cv=result.stability.cv,
                min_value=result.stability.min_value,
                max_value=result.stability.max_value,
                interpretation=result.stability.interpretation,
            ),
            drift=DriftResponse(
                severity=result.drift.severity.value,
                magnitude=result.drift.drift_magnitude,
                direction=result.drift.drift_direction,
                p_value=result.drift.p_value,
                is_significant=result.drift.is_significant,
                change_points=result.drift.change_points,
                interpretation=result.drift.interpretation,
            ),
            correlations=[
                CorrelationResponse(
                    metric_a=c.metric_a,
                    metric_b=c.metric_b,
                    pearson_r=c.pearson_r,
                    spearman_rho=c.spearman_rho,
                    strength=c.correlation_strength,
                    is_significant=c.is_significant,
                    interpretation=c.interpretation,
                )
                for c in result.correlations
            ],
            moving_average=result.moving_average,
            smoothed_values=result.smoothed_values,
            summary=result.summary,
            recommendations=result.recommendations,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Temporal analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Temporal analysis failed: {str(e)}"
        )


@router.post("/temporal-analysis/multi-metric", response_model=MultiMetricTemporalResponse)
async def analyze_multi_metric_temporal(
    request: MultiMetricTemporalRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Perform multi-metric temporal analysis across samples (CRMIT-007).
    
    Analyzes multiple metrics simultaneously and provides overall assessment.
    
    **Features:**
    - Analyzes multiple metrics in parallel
    - Cross-metric correlation analysis
    - Overall stability assessment
    - Aggregate drift detection
    
    **Parameters:**
    - sample_ids: List of sample IDs in chronological order
    - metrics: List of metrics to analyze
    - data_source: Data source (fcs, nta)
    - alpha: Significance level
    
    **Returns:**
    - Individual analysis for each metric
    - Overall stability level
    - Overall drift assessment
    """
    if not TEMPORAL_ANALYSIS_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Temporal analysis module not available"
        )
    
    try:
        logger.info(f"🕐 Multi-metric temporal analysis: {len(request.sample_ids)} samples, {len(request.metrics)} metrics")
        
        # Collect all metric data
        timestamps = []
        metrics_data: Dict[str, List[float]] = {m: [] for m in request.metrics}
        
        for sample_id in request.sample_ids:
            # Get sample
            result = await db.execute(
                select(Sample).where(Sample.sample_id == sample_id)
            )
            sample = result.scalar_one_or_none()
            
            if not sample:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Sample {sample_id} not found"
                )
            
            # Get timestamp
            sample_time = sample.upload_date or sample.created_at
            if not sample_time:
                from datetime import datetime
                sample_time = datetime.now()
            timestamps.append(sample_time)
            
            # Get metric values
            if request.data_source == "fcs":
                fcs_result = await db.execute(
                    select(FCSResult).where(FCSResult.sample_id == sample.id)
                )
                fcs_data = fcs_result.scalar_one_or_none()
                
                for metric in request.metrics:
                    if fcs_data:
                        if metric == "particle_size":
                            metrics_data[metric].append(_safe_get_float(fcs_data, 'median_size_nm', 'mean_size_nm'))
                        elif metric == "concentration":
                            metrics_data[metric].append(_safe_get_float(fcs_data, 'concentration', 'total_events'))
                        elif metric == "fsc":
                            metrics_data[metric].append(_safe_get_float(fcs_data, 'fsc_median', 'fsc_mean'))
                        elif metric == "ssc":
                            metrics_data[metric].append(_safe_get_float(fcs_data, 'ssc_median', 'ssc_mean'))
                        else:
                            metrics_data[metric].append(0.0)
                    else:
                        metrics_data[metric].append(0.0)
            
            elif request.data_source == "nta":
                nta_result = await db.execute(
                    select(NTAResult).where(NTAResult.sample_id == sample.id)
                )
                nta_data = nta_result.scalar_one_or_none()
                
                for metric in request.metrics:
                    if nta_data:
                        if metric == "particle_size":
                            metrics_data[metric].append(_safe_get_float(nta_data, 'median_size_nm', 'mean_size_nm'))
                        elif metric == "concentration":
                            metrics_data[metric].append(_safe_get_float(nta_data, 'concentration'))
                        else:
                            metrics_data[metric].append(0.0)
                    else:
                        metrics_data[metric].append(0.0)
        
        # Run multi-metric analysis
        if TemporalAnalyzer is None:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Temporal analysis module not available"
            )
        analyzer = TemporalAnalyzer(alpha=request.alpha)
        result = analyzer.compare_sample_series(
            sample_ids=request.sample_ids,
            timestamps=timestamps,
            metrics=metrics_data,
        )
        
        logger.success(f"✅ Multi-metric temporal analysis complete")
        
        return MultiMetricTemporalResponse(
            success=True,
            sample_ids=result["sample_ids"],
            n_samples=result["n_samples"],
            time_range=result["time_range"],
            metrics_analyzed=result["metrics_analyzed"],
            individual_results=result["individual_results"],
            overall_stability=result["overall_stability"],
            overall_drift=result["overall_drift"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Multi-metric temporal analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-metric temporal analysis failed: {str(e)}"
        )