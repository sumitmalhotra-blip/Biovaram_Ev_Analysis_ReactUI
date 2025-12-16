"""
Samples Query Router
====================

Endpoints for querying sample data.

Endpoints:
- GET /samples           - List all samples with optional filters
- GET /samples/{id}      - Get specific sample details
- GET /samples/{id}/fcs  - Get FCS results for sample
- GET /samples/{id}/nta  - Get NTA results for sample
- DELETE /samples/{id}   - Delete sample and all related data

Author: CRMIT Backend Team
Date: November 21, 2025
"""

from typing import Optional, List  # noqa: F401
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore[import-not-found]
from sqlalchemy import select, func  # type: ignore[import-not-found]
from loguru import logger

from src.database.connection import get_session
from src.database.models import Sample, FCSResult, NTAResult, QCReport, ProcessingJob  # type: ignore[import-not-found]

router = APIRouter()


# ============================================================================
# List Samples Endpoint
# ============================================================================

@router.get("/", response_model=dict)
async def list_samples(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    treatment: Optional[str] = Query(None, description="Filter by treatment"),
    qc_status: Optional[str] = Query(None, description="Filter by QC status (pass/warn/fail)"),
    processing_status: Optional[str] = Query(None, description="Filter by processing status"),
    db: AsyncSession = Depends(get_session)
):
    """
    List all samples with optional filters.
    
    **Query Parameters:**
    - skip: Pagination offset (default: 0)
    - limit: Number of results (default: 100, max: 1000)
    - treatment: Filter by treatment (e.g., "CD81", "ISO")
    - qc_status: Filter by QC status ("pass", "warn", "fail")
    - processing_status: Filter by processing status ("pending", "completed", "failed")
    
    **Response:**
    ```json
    {
        "total": 150,
        "skip": 0,
        "limit": 100,
        "samples": [
            {
                "id": 1,
                "sample_id": "P5_F10_CD81",
                "treatment": "CD81",
                "qc_status": "pass",
                "processing_status": "completed",
                "upload_timestamp": "2025-11-21T12:00:00",
                "has_fcs": true,
                "has_nta": true,
                "has_tem": false
            },
            ...
        ]
    }
    ```
    """
    try:
        # Build query
        query = select(Sample)
        
        # Apply filters
        if treatment:
            query = query.where(Sample.treatment == treatment)
        if qc_status:
            query = query.where(Sample.qc_status == qc_status)
        if processing_status:
            query = query.where(Sample.processing_status == processing_status)
        
        # Get total count
        count_query = select(func.count()).select_from(Sample)
        if treatment:
            count_query = count_query.where(Sample.treatment == treatment)
        if qc_status:
            count_query = count_query.where(Sample.qc_status == qc_status)
        if processing_status:
            count_query = count_query.where(Sample.processing_status == processing_status)
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        samples = result.scalars().all()
        
        # Format response
        samples_data = []
        for sample in samples:
            upload_ts = getattr(sample, 'upload_timestamp', None)
            samples_data.append({
                "id": sample.id,
                "sample_id": sample.sample_id,
                "biological_sample_id": sample.biological_sample_id,
                "treatment": sample.treatment,
                "qc_status": sample.qc_status,
                "processing_status": sample.processing_status,
                "upload_timestamp": upload_ts.isoformat() if upload_ts else None,
                "has_fcs": sample.file_path_fcs is not None,
                "has_nta": sample.file_path_nta is not None,
                "has_tem": sample.file_path_tem is not None,
            })
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "samples": samples_data
        }
        
    except Exception as e:
        logger.exception(f"❌ Failed to list samples: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list samples: {str(e)}"
        )


# ============================================================================
# Get Sample Details Endpoint
# ============================================================================

@router.get("/{sample_id}", response_model=dict)
async def get_sample(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get detailed information for a specific sample.
    
    **Path Parameters:**
    - sample_id: Sample identifier (e.g., "P5_F10_CD81")
    
    **Response:**
    ```json
    {
        "id": 1,
        "sample_id": "P5_F10_CD81",
        "biological_sample_id": "P5_F10",
        "treatment": "CD81",
        "concentration_ug": 1.0,
        "preparation_method": "SEC",
        "qc_status": "pass",
        "processing_status": "completed",
        "upload_timestamp": "2025-11-21T12:00:00",
        "files": {
            "fcs": "data/uploads/20251121_120000_file.fcs",
            "nta": "data/uploads/20251121_120100_file.txt",
            "tem": null
        },
        "results": {
            "fcs_count": 1,
            "nta_count": 1,
            "qc_reports_count": 2
        }
    }
    ```
    """
    try:
        # Query sample
        query = select(Sample).where(Sample.sample_id == sample_id)
        result = await db.execute(query)
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample not found: {sample_id}"
            )
        
        # Get related results counts
        fcs_query = select(func.count()).select_from(FCSResult).where(FCSResult.sample_id == sample.id)
        fcs_count = (await db.execute(fcs_query)).scalar()
        
        nta_query = select(func.count()).select_from(NTAResult).where(NTAResult.sample_id == sample.id)
        nta_count = (await db.execute(nta_query)).scalar()
        
        qc_query = select(func.count()).select_from(QCReport).where(QCReport.sample_id == sample.id)
        qc_count = (await db.execute(qc_query)).scalar()
        
        upload_ts = getattr(sample, 'upload_timestamp', None)
        exp_date = getattr(sample, 'experiment_date', None)
        
        return {
            "id": sample.id,
            "sample_id": sample.sample_id,
            "biological_sample_id": sample.biological_sample_id,
            "treatment": sample.treatment,
            "concentration_ug": sample.concentration_ug,
            "preparation_method": sample.preparation_method,
            "passage_number": sample.passage_number,
            "fraction_number": sample.fraction_number,
            "qc_status": sample.qc_status,
            "processing_status": sample.processing_status,
            "operator": sample.operator,
            "notes": sample.notes,
            "upload_timestamp": upload_ts.isoformat() if upload_ts else None,
            "experiment_date": exp_date.isoformat() if exp_date else None,
            "files": {
                "fcs": sample.file_path_fcs,
                "nta": sample.file_path_nta,
                "tem": sample.file_path_tem,
            },
            "results": {
                "fcs_count": fcs_count,
                "nta_count": nta_count,
                "qc_reports_count": qc_count,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get sample {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sample: {str(e)}"
        )


# ============================================================================
# Get FCS Results Endpoint
# ============================================================================

@router.get("/{sample_id}/fcs", response_model=dict)
async def get_fcs_results(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get FCS analysis results for a sample.
    
    **Response:**
    ```json
    {
        "sample_id": "P5_F10_CD81",
        "results": [
            {
                "id": 1,
                "total_events": 50000,
                "fsc_median": 15000,
                "ssc_median": 8000,
                "particle_size_median_nm": 82.5,
                "cd81_positive_pct": 45.2,
                "debris_pct": 5.3,
                "processed_at": "2025-11-21T12:05:00"
            }
        ]
    }
    ```
    """
    try:
        # Get sample
        sample_query = select(Sample).where(Sample.sample_id == sample_id)
        sample_result = await db.execute(sample_query)
        sample = sample_result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample not found: {sample_id}"
            )
        
        # Get FCS results
        fcs_query = select(FCSResult).where(FCSResult.sample_id == sample.id)
        fcs_result = await db.execute(fcs_query)
        fcs_results = fcs_result.scalars().all()
        
        results_data = []
        for fcs in fcs_results:
            processed = getattr(fcs, 'processed_at', None)
            results_data.append({
                "id": fcs.id,
                "total_events": fcs.total_events,
                "fsc_mean": fcs.fsc_mean,
                "fsc_median": fcs.fsc_median,
                "ssc_mean": fcs.ssc_mean,
                "ssc_median": fcs.ssc_median,
                "particle_size_mean_nm": fcs.particle_size_mean_nm,
                "particle_size_median_nm": fcs.particle_size_median_nm,
                "cd9_positive_pct": fcs.cd9_positive_pct,
                "cd81_positive_pct": fcs.cd81_positive_pct,
                "cd63_positive_pct": fcs.cd63_positive_pct,
                "debris_pct": fcs.debris_pct,
                "doublets_pct": fcs.doublets_pct,
                "processed_at": processed.isoformat() if processed else None,
                "parquet_file": fcs.parquet_file_path,
            })
        
        return {
            "sample_id": sample_id,
            "results": results_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get FCS results for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get FCS results: {str(e)}"
        )


# ============================================================================
# Get NTA Results Endpoint
# ============================================================================

@router.get("/{sample_id}/nta", response_model=dict)
async def get_nta_results(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get NTA analysis results for a sample.
    
    **Response:**
    ```json
    {
        "sample_id": "P5_F10_CD81",
        "results": [
            {
                "id": 1,
                "mean_size_nm": 85.3,
                "median_size_nm": 82.1,
                "d10_nm": 65.2,
                "d90_nm": 105.3,
                "concentration_particles_ml": 1.5e11,
                "temperature_celsius": 22.5,
                "processed_at": "2025-11-21T12:10:00"
            }
        ]
    }
    ```
    """
    try:
        # Get sample
        sample_query = select(Sample).where(Sample.sample_id == sample_id)
        sample_result = await db.execute(sample_query)
        sample = sample_result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample not found: {sample_id}"
            )
        
        # Get NTA results
        nta_query = select(NTAResult).where(NTAResult.sample_id == sample.id)
        nta_result = await db.execute(nta_query)
        nta_results = nta_result.scalars().all()
        
        results_data = []
        for nta in nta_results:
            processed = getattr(nta, 'processed_at', None)
            results_data.append({
                "id": nta.id,
                "mean_size_nm": nta.mean_size_nm,
                "median_size_nm": nta.median_size_nm,
                "d10_nm": nta.d10_nm,
                "d50_nm": nta.d50_nm,
                "d90_nm": nta.d90_nm,
                "concentration_particles_ml": nta.concentration_particles_ml,
                "temperature_celsius": nta.temperature_celsius,
                "ph": nta.ph,
                "bin_50_80nm_pct": nta.bin_50_80nm_pct,
                "bin_80_100nm_pct": nta.bin_80_100nm_pct,
                "bin_100_120nm_pct": nta.bin_100_120nm_pct,
                "processed_at": processed.isoformat() if processed else None,
                "parquet_file": nta.parquet_file_path,
            })
        
        return {
            "sample_id": sample_id,
            "results": results_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get NTA results for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get NTA results: {str(e)}"
        )


# ============================================================================
# Delete Sample Endpoint
# ============================================================================

@router.delete("/{sample_id}", response_model=dict)
async def delete_sample(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Delete a sample and all related data.
    
    **WARNING:** This will permanently delete:
    - Sample record
    - All FCS results
    - All NTA results
    - All QC reports
    - All processing jobs
    - Audit log will record deletion
    
    **Response:**
    ```json
    {
        "success": true,
        "message": "Sample P5_F10_CD81 deleted successfully",
        "deleted_records": {
            "fcs_results": 1,
            "nta_results": 1,
            "qc_reports": 2,
            "processing_jobs": 3
        }
    }
    ```
    """
    try:
        # Get sample
        query = select(Sample).where(Sample.sample_id == sample_id)
        result = await db.execute(query)
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample not found: {sample_id}"
            )
        
        # Count related records (for response)
        fcs_count = (await db.execute(
            select(func.count()).select_from(FCSResult).where(FCSResult.sample_id == sample.id)
        )).scalar()
        
        nta_count = (await db.execute(
            select(func.count()).select_from(NTAResult).where(NTAResult.sample_id == sample.id)
        )).scalar()
        
        qc_count = (await db.execute(
            select(func.count()).select_from(QCReport).where(QCReport.sample_id == sample.id)
        )).scalar()
        
        job_count = (await db.execute(
            select(func.count()).select_from(ProcessingJob).where(ProcessingJob.sample_id == sample.id)
        )).scalar()
        
        # Delete sample (cascade will delete related records)
        await db.delete(sample)
        await db.commit()
        
        logger.warning(f"🗑️  Deleted sample: {sample_id} (FCS: {fcs_count}, NTA: {nta_count}, QC: {qc_count}, Jobs: {job_count})")
        
        return {
            "success": True,
            "message": f"Sample {sample_id} deleted successfully",
            "deleted_records": {
                "fcs_results": fcs_count,
                "nta_results": nta_count,
                "qc_reports": qc_count,
                "processing_jobs": job_count,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to delete sample {sample_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete sample: {str(e)}"
        )


# ============================================================================
# Scatter Data Endpoint
# ============================================================================

@router.get("/{sample_id}/scatter-data", response_model=dict)
async def get_scatter_data(
    sample_id: str,
    max_points: int = Query(5000, ge=100, le=100000, description="Maximum points to return"),
    db: AsyncSession = Depends(get_session)
):
    """
    Get FSC/SSC scatter plot data for a sample.
    
    Returns actual event-level FSC and SSC values for visualization.
    Samples data if event count exceeds max_points for performance.
    
    **Response:**
    ```json
    {
        "sample_id": "P5_F10_CD81",
        "total_events": 100000,
        "returned_points": 5000,
        "data": [
            {"x": 250000, "y": 150000, "index": 0},
            ...
        ],
        "channels": {
            "fsc": "FSC-A",
            "ssc": "SSC-A"
        }
    }
    ```
    """
    try:
        # Get sample
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample {sample_id} not found"
            )
        
        # Check if FCS file exists
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        # Parse FCS file to get scatter data
        from src.parsers.fcs_parser import FCSParser  # type: ignore[import-not-found]
        import pandas as pd
        import numpy as np
        
        logger.info(f"📊 Loading scatter data for sample: {sample_id}")
        
        parser = FCSParser(sample.file_path_fcs)
        parsed_data = parser.parse()
        
        # Detect FSC and SSC channels - use channel_names attribute after parsing
        channels = parser.channel_names
        fsc_channel = None
        ssc_channel = None
        
        # Look for FSC channel (prefer Area, fallback to Height, then generic)
        for ch in channels:
            ch_upper = ch.upper()
            if 'FSC-A' in ch_upper or 'VFSC-A' in ch_upper:
                fsc_channel = ch
                break
            elif 'FSC-H' in ch_upper and not fsc_channel:
                fsc_channel = ch
            elif 'FSC' in ch_upper and not fsc_channel:
                fsc_channel = ch
        
        # Look for SSC channel
        for ch in channels:
            ch_upper = ch.upper()
            if 'SSC-A' in ch_upper:
                ssc_channel = ch
                break
            elif 'SSC-H' in ch_upper and not ssc_channel:
                ssc_channel = ch
            elif 'SSC' in ch_upper and not ssc_channel:
                ssc_channel = ch
        
        # Fallback: Use first two channels if FSC/SSC not found
        if not fsc_channel and len(channels) >= 1:
            fsc_channel = channels[0]
            logger.warning(f"⚠️ FSC channel not found, using first channel: {fsc_channel}")
        
        if not ssc_channel and len(channels) >= 2:
            ssc_channel = channels[1]
            logger.warning(f"⚠️ SSC channel not found, using second channel: {ssc_channel}")
        
        if not fsc_channel or not ssc_channel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not find FSC/SSC channels in FCS file. Available: {', '.join(channels)}"
            )
        
        # Extract FSC and SSC data
        total_events = len(parsed_data)
        
        # Sample data if too many points
        if total_events > max_points:
            # Use random sampling to maintain distribution
            sampled_indices = np.random.choice(total_events, size=max_points, replace=False)
            sampled_indices.sort()
            sampled_data = parsed_data.iloc[sampled_indices]
            logger.info(f"📉 Sampled {max_points} from {total_events} events")
        else:
            sampled_data = parsed_data
            sampled_indices = np.arange(total_events)
        
        # Build scatter data array
        scatter_data = []
        for idx, (orig_idx, row) in enumerate(zip(sampled_indices, sampled_data.itertuples())):
            scatter_data.append({
                "x": float(getattr(row, fsc_channel)),
                "y": float(getattr(row, ssc_channel)),
                "index": int(orig_idx)
            })
        
        logger.success(f"✅ Returned {len(scatter_data)} scatter points for {sample_id}")
        
        return {
            "sample_id": sample_id,
            "total_events": total_events,
            "returned_points": len(scatter_data),
            "data": scatter_data,
            "channels": {
                "fsc": fsc_channel,
                "ssc": ssc_channel
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get scatter data for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scatter data: {str(e)}"
        )


# ============================================================================
# Particle Size Binning Endpoint
# ============================================================================

@router.get("/{sample_id}/size-bins", response_model=dict)
async def get_size_bins(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get particle size distribution binned into small/medium/large categories.
    
    Uses Mie scattering theory to convert FSC values to particle sizes,
    then bins into standard EV size categories.
    
    **Size Categories:**
    - Small: < 50 nm (exomeres, small EVs)
    - Medium: 50-200 nm (exosomes, classic EVs)
    - Large: > 200 nm (microvesicles, large EVs)
    
    **Response:**
    ```json
    {
        "sample_id": "P5_F10_CD81",
        "total_events": 100000,
        "bins": {
            "small": 15000,
            "medium": 70000,
            "large": 15000
        },
        "percentages": {
            "small": 15.0,
            "medium": 70.0,
            "large": 15.0
        }
    }
    ```
    """
    try:
        # Get sample
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample {sample_id} not found"
            )
        
        # Check if FCS file exists
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        # Parse FCS file and calculate sizes
        from src.parsers.fcs_parser import FCSParser  # type: ignore[import-not-found]
        from src.physics.mie_scatter import MieScatterCalculator  # type: ignore[import-not-found]
        import numpy as np
        
        logger.info(f"📏 Calculating size bins for sample: {sample_id}")
        
        parser = FCSParser(sample.file_path_fcs)
        parsed_data = parser.parse()
        
        # Detect FSC channel - use channel_names attribute after parsing
        channels = parser.channel_names
        fsc_channel = None
        for ch in channels:
            ch_upper = ch.upper()
            if 'FSC-A' in ch_upper or 'VFSC-A' in ch_upper:
                fsc_channel = ch
                break
            elif 'FSC-H' in ch_upper and not fsc_channel:
                fsc_channel = ch
            elif 'FSC' in ch_upper and not fsc_channel:
                fsc_channel = ch
        
        # Fallback: Use first channel if FSC not found
        if not fsc_channel and len(channels) >= 1:
            fsc_channel = channels[0]
            logger.warning(f"⚠️ FSC channel not found for size bins, using first channel: {fsc_channel}")
        
        # Initialize Mie calculator
        mie_calc = MieScatterCalculator(
            wavelength_nm=488.0,
            n_particle=1.40,
            n_medium=1.33
        )
        
        total_events = len(parsed_data)
        
        # Sample for performance (calculate on subset, extrapolate to full dataset)
        sample_size = min(10000, total_events)
        sampled_fsc = parsed_data[fsc_channel].sample(n=sample_size, random_state=42)
        
        # Convert FSC to size for sampled events
        sizes = []
        for fsc_val in sampled_fsc:
            try:
                diameter, success = mie_calc.diameter_from_scatter(
                    fsc_intensity=float(fsc_val),
                    min_diameter=10.0,
                    max_diameter=500.0
                )
                if success and diameter > 0:
                    sizes.append(diameter)
            except:
                pass
        
        sizes_array = np.array(sizes)
        
        # Bin sizes into categories
        small_count = np.sum(sizes_array < 50)
        medium_count = np.sum((sizes_array >= 50) & (sizes_array <= 200))
        large_count = np.sum(sizes_array > 200)
        
        total_binned = small_count + medium_count + large_count
        
        # Extrapolate to full dataset
        scale_factor = total_events / sample_size if total_binned > 0 else 1.0
        
        small_total = int(small_count * scale_factor)
        medium_total = int(medium_count * scale_factor)
        large_total = int(large_count * scale_factor)
        
        # Calculate percentages
        total_categorized = small_total + medium_total + large_total
        small_pct = (small_total / total_categorized * 100) if total_categorized > 0 else 0
        medium_pct = (medium_total / total_categorized * 100) if total_categorized > 0 else 0
        large_pct = (large_total / total_categorized * 100) if total_categorized > 0 else 0
        
        logger.success(
            f"✅ Size bins for {sample_id}: "
            f"Small={small_pct:.1f}%, Medium={medium_pct:.1f}%, Large={large_pct:.1f}%"
        )
        
        return {
            "sample_id": sample_id,
            "total_events": total_events,
            "bins": {
                "small": small_total,
                "medium": medium_total,
                "large": large_total
            },
            "percentages": {
                "small": round(small_pct, 2),
                "medium": round(medium_pct, 2),
                "large": round(large_pct, 2)
            },
            "thresholds": {
                "small_max": 50,
                "medium_min": 50,
                "medium_max": 200,
                "large_min": 200
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get size bins for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get size bins: {str(e)}"
        )


# ============================================================================
# Re-analyze Sample Endpoint
# ============================================================================

from pydantic import BaseModel, Field


class ReanalyzeRequest(BaseModel):
    """Request body for re-analyzing a sample with custom settings."""
    wavelength_nm: float = Field(default=488.0, ge=200, le=800, description="Laser wavelength in nm")
    n_particle: float = Field(default=1.40, ge=1.0, le=2.0, description="Particle refractive index")
    n_medium: float = Field(default=1.33, ge=1.0, le=2.0, description="Medium refractive index")
    anomaly_detection: bool = Field(default=False, description="Enable anomaly detection")
    anomaly_method: str = Field(default="zscore", description="Anomaly method: zscore, iqr, both")
    zscore_threshold: float = Field(default=3.0, ge=1.0, le=10.0, description="Z-score threshold")
    iqr_factor: float = Field(default=1.5, ge=1.0, le=5.0, description="IQR factor for outlier detection")
    size_ranges: list[dict] = Field(
        default=[
            {"name": "Small EVs", "min": 30, "max": 100},
            {"name": "Medium EVs", "min": 100, "max": 200},
            {"name": "Large EVs", "min": 200, "max": 500},
        ],
        description="Custom size ranges for binning"
    )


@router.post("/{sample_id}/reanalyze", response_model=dict)
async def reanalyze_sample(
    sample_id: str,
    request: ReanalyzeRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Re-analyze a sample with custom analysis settings.
    
    This endpoint re-processes the FCS file with user-specified parameters
    and returns updated statistics without modifying the database.
    
    **Use Cases:**
    - Change laser wavelength for Mie calculations
    - Adjust refractive index parameters
    - Enable/disable anomaly detection
    - Apply custom size range binning
    """
    import numpy as np
    
    try:
        # Get sample
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample {sample_id} not found"
            )
        
        # Check if FCS file exists
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        logger.info(f"🔄 Re-analyzing sample {sample_id} with params: λ={request.wavelength_nm}nm, n_p={request.n_particle}, n_m={request.n_medium}")
        
        # Parse FCS file
        from src.parsers.fcs_parser import FCSParser
        from src.physics.mie_scatter import MieScatterCalculator
        
        parser = FCSParser(sample.file_path_fcs)
        parsed_data = parser.parse()
        stats = parser.get_statistics()
        
        # Detect FSC and SSC channels
        channels = list(parsed_data.columns)
        fsc_channel = None
        ssc_channel = None
        
        for ch in channels:
            ch_upper = ch.upper()
            if 'FSC' in ch_upper:
                if '-H' in ch_upper or '_H' in ch_upper:
                    fsc_channel = ch
                elif '-A' in ch_upper or '_A' in ch_upper and fsc_channel is None:
                    fsc_channel = ch
                elif fsc_channel is None:
                    fsc_channel = ch
            elif 'SSC' in ch_upper:
                if '-H' in ch_upper or '_H' in ch_upper:
                    ssc_channel = ch
                elif '-A' in ch_upper or '_A' in ch_upper and ssc_channel is None:
                    ssc_channel = ch
                elif ssc_channel is None:
                    ssc_channel = ch
        
        # Get statistics for detected channels
        fsc_stats = stats.get(fsc_channel, {}) if fsc_channel else {}
        ssc_stats = stats.get(ssc_channel, {}) if ssc_channel else {}
        
        # Initialize Mie calculator with user parameters
        mie_calc = MieScatterCalculator(
            wavelength_nm=request.wavelength_nm,
            n_particle=request.n_particle,
            n_medium=request.n_medium
        )
        
        # Calculate particle size from FSC median
        particle_size_median_nm = None
        if fsc_stats.get('median'):
            try:
                diameter, success = mie_calc.diameter_from_scatter(
                    fsc_intensity=fsc_stats['median'],
                    min_diameter=10.0,
                    max_diameter=500.0
                )
                if success:
                    particle_size_median_nm = float(diameter)
            except Exception as mie_error:
                logger.warning(f"⚠️ Mie calculation failed: {mie_error}")
        
        # Calculate size distribution
        size_distribution = None
        custom_bins = {}
        
        if fsc_channel and fsc_channel in parsed_data.columns:
            try:
                # Sample for performance
                sample_size = min(10000, len(parsed_data))
                sampled_fsc = parsed_data[fsc_channel].sample(n=sample_size, random_state=42)
                
                sizes = []
                for fsc_val in sampled_fsc:
                    size, success = mie_calc.diameter_from_scatter(
                        fsc_intensity=float(fsc_val),
                        min_diameter=10.0,
                        max_diameter=500.0
                    )
                    if success and size > 0:
                        sizes.append(size)
                
                if sizes:
                    sizes_array = np.array(sizes)
                    size_distribution = {
                        'd10': float(np.percentile(sizes_array, 10)),
                        'd50': float(np.percentile(sizes_array, 50)),
                        'd90': float(np.percentile(sizes_array, 90)),
                        'mean': float(np.mean(sizes_array)),
                        'std': float(np.std(sizes_array))
                    }
                    
                    # Calculate custom size range bins
                    scale_factor = len(parsed_data) / sample_size
                    for range_def in request.size_ranges:
                        name = range_def.get('name', f"{range_def['min']}-{range_def['max']}nm")
                        min_size = range_def.get('min', 0)
                        max_size = range_def.get('max', 1000)
                        count = np.sum((sizes_array >= min_size) & (sizes_array < max_size))
                        custom_bins[name] = {
                            'count': int(count * scale_factor),
                            'percentage': float(count / len(sizes_array) * 100) if sizes_array.size > 0 else 0
                        }
                        
            except Exception as size_error:
                logger.warning(f"⚠️ Size distribution calculation failed: {size_error}")
        
        # Anomaly detection
        anomaly_data = None
        if request.anomaly_detection:
            try:
                anomalous_indices = []
                
                if fsc_channel and ssc_channel:
                    fsc_data = parsed_data[fsc_channel].values
                    ssc_data = parsed_data[ssc_channel].values
                    
                    if request.anomaly_method in ['zscore', 'both']:
                        # Z-score method
                        fsc_zscore = np.abs((fsc_data - np.mean(fsc_data)) / np.std(fsc_data))
                        ssc_zscore = np.abs((ssc_data - np.mean(ssc_data)) / np.std(ssc_data))
                        zscore_outliers = np.where((fsc_zscore > request.zscore_threshold) | (ssc_zscore > request.zscore_threshold))[0]
                        anomalous_indices.extend(zscore_outliers.tolist())
                    
                    if request.anomaly_method in ['iqr', 'both']:
                        # IQR method
                        fsc_q1, fsc_q3 = np.percentile(fsc_data, [25, 75])
                        ssc_q1, ssc_q3 = np.percentile(ssc_data, [25, 75])
                        fsc_iqr = fsc_q3 - fsc_q1
                        ssc_iqr = ssc_q3 - ssc_q1
                        fsc_outliers = (fsc_data < fsc_q1 - request.iqr_factor * fsc_iqr) | (fsc_data > fsc_q3 + request.iqr_factor * fsc_iqr)
                        ssc_outliers = (ssc_data < ssc_q1 - request.iqr_factor * ssc_iqr) | (ssc_data > ssc_q3 + request.iqr_factor * ssc_iqr)
                        iqr_outliers = np.where(fsc_outliers | ssc_outliers)[0]
                        anomalous_indices.extend(iqr_outliers.tolist())
                    
                    anomalous_indices = list(set(anomalous_indices))
                    
                    anomaly_data = {
                        'enabled': True,
                        'method': request.anomaly_method,
                        'total_anomalies': len(anomalous_indices),
                        'anomaly_percentage': len(anomalous_indices) / len(parsed_data) * 100,
                        'anomalous_indices': anomalous_indices[:1000]  # Limit for response size
                    }
            except Exception as anomaly_error:
                logger.warning(f"⚠️ Anomaly detection failed: {anomaly_error}")
        
        # Build response
        response = {
            'sample_id': sample_id,
            'analysis_settings': {
                'wavelength_nm': request.wavelength_nm,
                'n_particle': request.n_particle,
                'n_medium': request.n_medium,
                'anomaly_detection': request.anomaly_detection,
                'anomaly_method': request.anomaly_method if request.anomaly_detection else None,
            },
            'results': {
                'total_events': len(parsed_data),
                'channels': channels[:10],  # First 10 channels
                'fsc_channel': fsc_channel,
                'ssc_channel': ssc_channel,
                'fsc_mean': fsc_stats.get('mean'),
                'fsc_median': fsc_stats.get('median'),
                'ssc_mean': ssc_stats.get('mean'),
                'ssc_median': ssc_stats.get('median'),
                'particle_size_median_nm': particle_size_median_nm,
                'size_statistics': size_distribution,
                'custom_size_bins': custom_bins,
            },
            'anomaly_data': anomaly_data,
        }
        
        logger.success(f"✅ Re-analyzed {sample_id}: {len(parsed_data)} events, median size={particle_size_median_nm}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to re-analyze {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to re-analyze sample: {str(e)}"
        )
