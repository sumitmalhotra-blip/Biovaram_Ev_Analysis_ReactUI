"""
Processing Jobs Router
======================

Endpoints for monitoring processing job status.

Endpoints:
- GET /jobs              - List all processing jobs
- GET /jobs/{job_id}     - Get job status and details
- DELETE /jobs/{job_id}  - Cancel a running job

Author: CRMIT Backend Team
Date: November 21, 2025
"""

from pathlib import Path
from typing import Optional
import traceback
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore[import-not-found]
from sqlalchemy import select, func  # type: ignore[import-not-found]
from loguru import logger
import numpy as np
import uuid

from src.database.connection import get_session
from src.database.models import ProcessingJob, Sample  # type: ignore[import-not-found]
from src.database.crud import create_fcs_result, create_nta_result, update_job_status
from src.api.auth_middleware import optional_auth
from src.parsers.fcs_parser import FCSParser
from src.parsers.nta_parser import NTAParser

router = APIRouter()


def _resolve_existing_file_path(raw_path: str) -> Path:
    """Resolve a stored sample path to an existing file on disk."""
    candidate = Path(raw_path)
    if candidate.exists():
        return candidate

    if not candidate.is_absolute():
        cwd_candidate = Path.cwd() / candidate
        if cwd_candidate.exists():
            return cwd_candidate

    raise FileNotFoundError(f"Sample file not found: {raw_path}")


def _calculate_nta_results(parsed_data, fallback_temperature: Optional[float]) -> dict:
    """Rebuild NTA summary metrics using the same weighted logic used on upload."""
    size_col = None
    count_col = None
    conc_col = None

    for col in parsed_data.columns:
        col_lower = col.lower()
        if 'size' in col_lower and size_col is None:
            size_col = col
        if 'particle_count' in col_lower and count_col is None:
            count_col = col
        if 'concentration' in col_lower and 'particles' in col_lower and conc_col is None:
            conc_col = col

    if not size_col and 'size_nm' in parsed_data.columns:
        size_col = 'size_nm'
    if not count_col and 'particle_count' in parsed_data.columns:
        count_col = 'particle_count'
    if not conc_col and 'concentration_particles_ml' in parsed_data.columns:
        conc_col = 'concentration_particles_ml'

    if not size_col:
        raise ValueError("Could not find a size column in NTA data")

    sizes = np.asarray(parsed_data[size_col].values, dtype=np.float64)
    if count_col and count_col in parsed_data.columns:
        counts = np.asarray(parsed_data[count_col].values, dtype=np.float64)
    else:
        counts = np.ones_like(sizes)

    valid_mask = np.isfinite(sizes) & np.isfinite(counts) & (counts > 0)
    sizes_valid = np.asarray(sizes[valid_mask], dtype=np.float64)
    counts_valid = np.asarray(counts[valid_mask], dtype=np.float64)

    if len(sizes_valid) == 0 or float(np.sum(counts_valid)) <= 0:
        raise ValueError("NTA data has no valid size bins for summary calculation")

    sort_idx = np.argsort(sizes_valid)
    sizes_sorted = sizes_valid[sort_idx]
    counts_sorted = counts_valid[sort_idx]
    cumsum = np.cumsum(counts_sorted)
    total_particles = float(cumsum[-1])

    d10 = float(sizes_sorted[min(np.searchsorted(cumsum, total_particles * 0.1), len(sizes_sorted) - 1)])
    d50 = float(sizes_sorted[min(np.searchsorted(cumsum, total_particles * 0.5), len(sizes_sorted) - 1)])
    d90 = float(sizes_sorted[min(np.searchsorted(cumsum, total_particles * 0.9), len(sizes_sorted) - 1)])
    mean_size = float(np.average(sizes_valid, weights=counts_valid))
    weighted_var = float(np.average((sizes_valid - mean_size) ** 2, weights=counts_valid))
    weighted_std = float(np.sqrt(weighted_var))

    total_concentration = None
    if conc_col and conc_col in parsed_data.columns:
        conc_values = parsed_data[conc_col].dropna()
        if len(conc_values) > 0:
            total_concentration = float(conc_values.sum())

    bin_30_50 = float(np.sum(counts_valid[(sizes_valid >= 30) & (sizes_valid < 50)])) / total_particles * 100
    bin_50_80 = float(np.sum(counts_valid[(sizes_valid >= 50) & (sizes_valid < 80)])) / total_particles * 100
    bin_80_100 = float(np.sum(counts_valid[(sizes_valid >= 80) & (sizes_valid < 100)])) / total_particles * 100
    bin_100_120 = float(np.sum(counts_valid[(sizes_valid >= 100) & (sizes_valid < 120)])) / total_particles * 100
    bin_120_150 = float(np.sum(counts_valid[(sizes_valid >= 120) & (sizes_valid < 150)])) / total_particles * 100
    bin_150_200 = float(np.sum(counts_valid[(sizes_valid >= 150) & (sizes_valid < 200)])) / total_particles * 100

    return {
        "mean_size_nm": mean_size,
        "median_size_nm": d50,
        "d10_nm": d10,
        "d50_nm": d50,
        "d90_nm": d90,
        "std_dev_nm": weighted_std,
        "concentration_particles_ml": total_concentration,
        "temperature_celsius": fallback_temperature,
        "total_particles": int(total_particles),
        "bin_30_50nm_pct": bin_30_50,
        "bin_50_80nm_pct": bin_50_80,
        "bin_80_100nm_pct": bin_80_100,
        "bin_100_120nm_pct": bin_100_120,
        "bin_120_150nm_pct": bin_120_150,
        "bin_150_200nm_pct": bin_150_200,
    }


async def _execute_retry_job(db: AsyncSession, new_job: ProcessingJob, sample: Sample) -> dict:
    """Execute retry processing for supported job types and persist result rows."""
    await update_job_status(db=db, job_id=new_job.job_id, status="running")

    if new_job.job_type == "fcs_parse":
        if not sample.file_path_fcs:
            raise ValueError("Sample has no FCS file path to retry")

        file_path = _resolve_existing_file_path(str(sample.file_path_fcs))
        parser = FCSParser(file_path)
        if not parser.validate():
            logger.warning(f"⚠️ FCS validation failed during retry: {file_path}")

        parsed_data = parser.parse()
        stats = parser.get_statistics()
        channels = list(getattr(parser, 'channel_names', []))
        event_count = len(parsed_data)

        fsc_channel = next((ch for ch in channels if "FSC" in ch.upper()), None)
        ssc_channel = next((ch for ch in channels if "SSC" in ch.upper()), None)
        fsc_stats = stats.get(fsc_channel, {}) if fsc_channel else {}
        ssc_stats = stats.get(ssc_channel, {}) if ssc_channel else {}

        result_data = {
            "total_events": event_count,
            "event_count": event_count,
            "channels": channels,
            "fsc_mean": fsc_stats.get("mean"),
            "fsc_median": fsc_stats.get("median"),
            "ssc_mean": ssc_stats.get("mean"),
            "ssc_median": ssc_stats.get("median"),
        }

        await create_fcs_result(
            db=db,
            sample_id=sample.id,  # type: ignore[arg-type]
            total_events=result_data.get("total_events", 0),
            fsc_mean=result_data.get("fsc_mean"),
            fsc_median=result_data.get("fsc_median"),
            ssc_mean=result_data.get("ssc_mean"),
            ssc_median=result_data.get("ssc_median"),
        )

        await update_job_status(db=db, job_id=new_job.job_id, status="completed", result_data=result_data)
        return result_data

    if new_job.job_type == "nta_parse":
        if not sample.file_path_nta:
            raise ValueError("Sample has no NTA file path to retry")

        file_path = _resolve_existing_file_path(str(sample.file_path_nta))
        parser = NTAParser(file_path)
        if not parser.validate():
            logger.warning(f"⚠️ NTA validation failed during retry: {file_path}")

        parsed_data = parser.parse()
        fallback_temperature = getattr(sample, "temperature_celsius", None)
        result_data = _calculate_nta_results(parsed_data, fallback_temperature)

        await create_nta_result(
            db=db,
            sample_id=sample.id,  # type: ignore[arg-type]
            mean_size_nm=result_data.get("mean_size_nm"),
            median_size_nm=result_data.get("median_size_nm"),
            d10_nm=result_data.get("d10_nm"),
            d50_nm=result_data.get("d50_nm"),
            d90_nm=result_data.get("d90_nm"),
            std_dev_nm=result_data.get("std_dev_nm"),
            concentration_particles_ml=result_data.get("concentration_particles_ml"),
            temperature_celsius=result_data.get("temperature_celsius"),
            bin_30_50nm_pct=result_data.get("bin_30_50nm_pct"),
            bin_50_80nm_pct=result_data.get("bin_50_80nm_pct"),
            bin_80_100nm_pct=result_data.get("bin_80_100nm_pct"),
            bin_100_120nm_pct=result_data.get("bin_100_120nm_pct"),
            bin_120_150nm_pct=result_data.get("bin_120_150nm_pct"),
            bin_150_200nm_pct=result_data.get("bin_150_200nm_pct"),
        )

        await update_job_status(db=db, job_id=new_job.job_id, status="completed", result_data=result_data)
        return result_data

    raise ValueError(f"Retry dispatch is not implemented for job type: {new_job.job_type}")


# ============================================================================
# List Jobs Endpoint
# ============================================================================

@router.get("/", response_model=dict)
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[str] = Query(None, description="Filter by status (pending/running/completed/failed/cancelled)"),
    job_type: Optional[str] = Query(None, description="Filter by job type (fcs_parse/nta_parse/batch_process)"),
    db: AsyncSession = Depends(get_session)
):
    """
    List all processing jobs with optional filters.
    
    **Query Parameters:**
    - skip: Pagination offset
    - limit: Number of results
    - status_filter: Filter by job status
    - job_type: Filter by job type
    
    **Response:**
    ```json
    {
        "total": 50,
        "skip": 0,
        "limit": 100,
        "jobs": [
            {
                "id": 1,
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "job_type": "fcs_parse",
                "status": "completed",
                "progress_percent": 100,
                "created_at": "2025-11-21T12:00:00",
                "completed_at": "2025-11-21T12:05:00",
                "sample_id": "P5_F10_CD81"
            },
            ...
        ]
    }
    ```
    """
    try:
        # Build query
        query = select(ProcessingJob)
        
        # Apply filters
        if status_filter:
            query = query.where(ProcessingJob.status == status_filter)
        if job_type:
            query = query.where(ProcessingJob.job_type == job_type)
        
        # Get total count
        count_query = select(func.count()).select_from(ProcessingJob)
        if status_filter:
            count_query = count_query.where(ProcessingJob.status == status_filter)
        if job_type:
            count_query = count_query.where(ProcessingJob.job_type == job_type)
        
        total = (await db.execute(count_query)).scalar()
        
        # Apply pagination and ordering
        query = query.order_by(ProcessingJob.created_at.desc()).offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        jobs = result.scalars().all()
        
        # Get sample_id for each job
        jobs_data = []
        for job in jobs:
            sample_id = None
            job_sample_id = getattr(job, 'sample_id', None)
            if job_sample_id is not None:
                sample_query = select(Sample.sample_id).where(Sample.id == job_sample_id)
                sample_result = await db.execute(sample_query)
                sample_id = sample_result.scalar_one_or_none()
            
            job_status = getattr(job, 'status', None)
            job_created = getattr(job, 'created_at', None)
            job_started = getattr(job, 'started_at', None)
            job_completed = getattr(job, 'completed_at', None)
            
            jobs_data.append({
                "id": job.id,
                "job_id": job.job_id,
                "job_type": job.job_type,
                "status": job_status,
                "progress_percent": job.progress_percent,
                "current_step": job.current_step,
                "created_at": job_created.isoformat() if job_created else None,
                "started_at": job_started.isoformat() if job_started else None,
                "completed_at": job_completed.isoformat() if job_completed else None,
                "sample_id": sample_id,
                "error_message": getattr(job, 'error_message', None) if job_status == "failed" else None,
            })
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "jobs": jobs_data
        }
        
    except Exception as e:
        logger.exception(f"❌ Failed to list jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        )


# ============================================================================
# Get Job Status Endpoint
# ============================================================================

@router.get("/{job_id}", response_model=dict)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get detailed status for a specific job.
    
    **Path Parameters:**
    - job_id: Job UUID
    
    **Response:**
    ```json
    {
        "id": 1,
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "job_type": "fcs_parse",
        "status": "running",
        "progress_percent": 65,
        "current_step": "Calculating particle sizes",
        "sample_id": "P5_F10_CD81",
        "created_at": "2025-11-21T12:00:00",
        "started_at": "2025-11-21T12:00:05",
        "completed_at": null,
        "result_data": null,
        "error_message": null
    }
    ```
    
    **Job Statuses:**
    - `pending`: Job queued, not yet started
    - `running`: Job currently processing
    - `completed`: Job finished successfully
    - `failed`: Job encountered an error
    - `cancelled`: Job was cancelled by user
    """
    try:
        # Query job
        query = select(ProcessingJob).where(ProcessingJob.job_id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found: {job_id}"
            )
        
        # Get sample_id
        sample_id = None
        job_sample_id = getattr(job, 'sample_id', None)
        if job_sample_id is not None:
            sample_query = select(Sample.sample_id).where(Sample.id == job_sample_id)
            sample_result = await db.execute(sample_query)
            sample_id = sample_result.scalar_one_or_none()
        
        job_status = getattr(job, 'status', None)
        job_created = getattr(job, 'created_at', None)
        job_started = getattr(job, 'started_at', None)
        job_completed = getattr(job, 'completed_at', None)
        
        return {
            "id": job.id,
            "job_id": job.job_id,
            "job_type": job.job_type,
            "status": job_status,
            "progress_percent": job.progress_percent,
            "current_step": job.current_step,
            "sample_id": sample_id,
            "created_at": job_created.isoformat() if job_created else None,
            "started_at": job_started.isoformat() if job_started else None,
            "completed_at": job_completed.isoformat() if job_completed else None,
            "result_data": job.result_data,
            "error_message": job.error_message,
            "error_traceback": getattr(job, 'error_traceback', None) if job_status == "failed" else None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


# ============================================================================
# Cancel Job Endpoint
# ============================================================================

@router.delete("/{job_id}", response_model=dict)
async def cancel_job(
    job_id: str,
    current_user: dict | None = Depends(optional_auth),
    db: AsyncSession = Depends(get_session)
):
    """
    Cancel a running or pending job.
    
    **Path Parameters:**
    - job_id: Job UUID
    
    **Response:**
    ```json
    {
        "success": true,
        "message": "Job cancelled successfully",
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "previous_status": "running"
    }
    ```
    
    **Notes:**
    - Only jobs with status `pending` or `running` can be cancelled
    - Completed or failed jobs cannot be cancelled
    - Cancellation may not be immediate for running jobs
    """
    try:
        # Query job
        query = select(ProcessingJob).where(ProcessingJob.job_id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found: {job_id}"
            )
        
        # Check if job can be cancelled
        if job.status in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel job with status: {job.status}"
            )
        
        previous_status = getattr(job, 'status', None)
        
        # Update job status using setattr for SQLAlchemy compatibility
        setattr(job, 'status', "cancelled")
        setattr(job, 'current_step', "Cancelled by user")
        await db.commit()
        
        logger.warning(f"🚫 Job cancelled: {job_id} (was: {previous_status})")
        
        return {
            "success": True,
            "message": "Job cancelled successfully",
            "job_id": job_id,
            "previous_status": previous_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to cancel job {job_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}"
        )


# ============================================================================
# Retry Failed Job Endpoint
# ============================================================================

@router.post("/{job_id}/retry", response_model=dict)
async def retry_job(
    job_id: str,
    current_user: dict | None = Depends(optional_auth),
    db: AsyncSession = Depends(get_session)
):
    """
    Retry a failed job.
    
    **Path Parameters:**
    - job_id: Job UUID
    
    **Response:**
    ```json
    {
        "success": true,
        "message": "Job requeued successfully",
        "new_job_id": "660e8400-e29b-41d4-a716-446655440001"
    }
    ```
    
    **Notes:**
    - Only failed jobs can be retried
    - Creates a new job with same parameters
    - Retry is executed immediately with status transitions (running/completed/failed)
    - Original job remains in database with failed status
    """
    try:
        # Query job
        query = select(ProcessingJob).where(ProcessingJob.job_id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found: {job_id}"
            )
        
        # Check if job can be retried
        job_status = getattr(job, 'status', None)
        if job_status != "failed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Can only retry failed jobs. Current status: {job_status}"
            )
        
        # Create a new processing job with same type and sample
        new_job_id = str(uuid.uuid4())
        job_type = str(getattr(job, 'job_type', 'unknown'))
        sample_id = getattr(job, 'sample_id', None)

        new_job = ProcessingJob(
            job_id=new_job_id,
            job_type=job_type,
            sample_id=sample_id,
            status="pending",
            progress_percent=0,
            current_step="Queued for retry",
        )
        if sample_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Retry is only supported for sample-linked jobs"
            )

        sample_result = await db.execute(select(Sample).where(Sample.id == sample_id))
        sample = sample_result.scalar_one_or_none()
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Associated sample not found for retry: {sample_id}"
            )

        db.add(new_job)

        # Mark original job as superseded
        job.current_step = f"Superseded by retry job {new_job_id}"  # type: ignore[assignment]
        await db.commit()

        logger.info(f"🔄 Retrying job: {job_id} → {new_job_id} (type={job_type}, sample={sample_id})")

        try:
            result_data = await _execute_retry_job(db=db, new_job=new_job, sample=sample)
        except Exception as retry_error:
            logger.exception(f"❌ Retry execution failed for job {new_job_id}: {retry_error}")
            await update_job_status(
                db=db,
                job_id=new_job_id,
                status="failed",
                error_message=str(retry_error),
                error_traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Retry execution failed: {str(retry_error)}"
            )

        return {
            "success": True,
            "message": "Job retried successfully",
            "original_job_id": job_id,
            "new_job_id": new_job_id,
            "job_type": job_type,
            "status": "completed",
            "result_data": result_data,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to retry job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry job: {str(e)}"
        )
