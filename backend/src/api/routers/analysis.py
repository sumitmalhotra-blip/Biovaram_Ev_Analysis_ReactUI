"""
Statistical Analysis Router
============================

Endpoints for statistical tests between samples.

Endpoints:
- POST /analysis/statistical-tests  - Run statistical tests between sample groups

Implements Mann-Whitney U, Kolmogorov-Smirnov, and T-tests using scipy.stats.

Author: CRMIT Backend Team
Date: November 21, 2025
"""

from typing import List, Optional
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
