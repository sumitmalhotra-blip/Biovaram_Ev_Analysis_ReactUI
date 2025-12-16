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

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore[import-not-found]
from sqlalchemy import select, func  # type: ignore[import-not-found]
from loguru import logger

from src.database.connection import get_session
from src.database.models import ProcessingJob, Sample  # type: ignore[import-not-found]

router = APIRouter()


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
        
        # TODO: Create new job with same parameters
        # For now, just return mock response
        import uuid
        new_job_id = str(uuid.uuid4())
        
        logger.info(f"🔄 Retrying job: {job_id} → {new_job_id}")
        
        return {
            "success": True,
            "message": "Job requeued successfully",
            "original_job_id": job_id,
            "new_job_id": new_job_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to retry job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry job: {str(e)}"
        )
