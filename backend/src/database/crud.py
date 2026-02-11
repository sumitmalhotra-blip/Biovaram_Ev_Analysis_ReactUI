"""
CRUD Operations Module
======================

Database CRUD operations for all models.

Provides async database operations:
- Sample CRUD (create, read, update, delete)
- FCS Result CRUD
- NTA Result CRUD
- Processing Job CRUD
- QC Report CRUD

Author: CRMIT Backend Team
Date: November 21, 2025
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore[import-not-found]
from sqlalchemy import select, func, delete  # type: ignore[import-not-found]
from loguru import logger

from src.database.models import (  # type: ignore[import-not-found]
    Sample,
    FCSResult,
    NTAResult,
    ProcessingJob,
    QCReport,
    ExperimentalConditions,
    Alert,
    ProcessingStatus,
    QCStatus,
    AlertSeverity,
    AlertType,
)


# ============================================================================
# Sample CRUD Operations
# ============================================================================

async def create_sample(
    db: AsyncSession,
    sample_id: str,
    biological_sample_id: Optional[str] = None,
    treatment: Optional[str] = None,
    concentration_ug: Optional[float] = None,
    preparation_method: Optional[str] = None,
    file_path_fcs: Optional[str] = None,
    file_path_nta: Optional[str] = None,
    file_path_tem: Optional[str] = None,
    operator: Optional[str] = None,
    notes: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Sample:
    """
    Create a new sample record.
    
    Args:
        db: Database session
        sample_id: Unique sample identifier (e.g., "P5_F10_CD81")
        biological_sample_id: Biological sample ID (e.g., "P5_F10")
        treatment: Treatment/condition name
        concentration_ug: Concentration in µg
        preparation_method: Preparation method (SEC, centrifugation, etc.)
        file_path_fcs: Path to FCS file
        file_path_nta: Path to NTA file
        file_path_tem: Path to TEM file
        operator: Person who performed the experiment
        notes: Additional notes
        user_id: ID of the user who owns this sample
        
    Returns:
        Created Sample object
    """
    try:
        # Use sample_id as biological_sample_id if not provided
        bio_sample_id = biological_sample_id or sample_id
        # Use "Unknown" as treatment if not provided (required field)
        sample_treatment = treatment or "Unknown"
        
        sample = Sample(
            sample_id=sample_id,
            biological_sample_id=bio_sample_id,
            treatment=sample_treatment,
            concentration_ug=concentration_ug,
            preparation_method=preparation_method,
            file_path_fcs=file_path_fcs,
            file_path_nta=file_path_nta,
            file_path_tem=file_path_tem,
            operator=operator,
            notes=notes,
            user_id=user_id,
            processing_status=ProcessingStatus.PENDING,
            qc_status=QCStatus.PENDING,
        )
        
        db.add(sample)
        await db.commit()
        await db.refresh(sample)
        
        logger.success(f"✅ Created sample: {sample_id} (DB ID: {sample.id})")  # type: ignore[attr-defined]
        return sample
        
    except Exception as e:
        await db.rollback()
        logger.exception(f"❌ Failed to create sample {sample_id}: {e}")
        raise


async def get_sample_by_id(db: AsyncSession, sample_id: str) -> Optional[Sample]:
    """
    Get sample by sample_id.
    
    Args:
        db: Database session
        sample_id: Sample identifier
        
    Returns:
        Sample object or None if not found
    """
    query = select(Sample).where(Sample.sample_id == sample_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_sample_by_db_id(db: AsyncSession, id: int) -> Optional[Sample]:
    """
    Get sample by database ID.
    
    Args:
        db: Database session
        id: Database primary key
        
    Returns:
        Sample object or None if not found
    """
    query = select(Sample).where(Sample.id == id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_samples(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    treatment: Optional[str] = None,
    qc_status: Optional[str] = None,
    processing_status: Optional[str] = None,
) -> List[Sample]:
    """
    Get list of samples with optional filters.
    
    Args:
        db: Database session
        skip: Pagination offset
        limit: Number of results
        treatment: Filter by treatment
        qc_status: Filter by QC status
        processing_status: Filter by processing status
        
    Returns:
        List of Sample objects
    """
    query = select(Sample)
    
    # Apply filters
    if treatment:
        query = query.where(Sample.treatment == treatment)
    if qc_status:
        query = query.where(Sample.qc_status == qc_status)
    if processing_status:
        query = query.where(Sample.processing_status == processing_status)
    
    # Apply pagination and ordering
    query = query.order_by(Sample.upload_timestamp.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_sample(
    db: AsyncSession,
    sample_id: str,
    **kwargs
) -> Optional[Sample]:
    """
    Update sample fields.
    
    Args:
        db: Database session
        sample_id: Sample identifier
        **kwargs: Fields to update (None values are skipped to preserve existing data)
        
    Returns:
        Updated Sample object or None if not found
    """
    try:
        sample = await get_sample_by_id(db, sample_id)
        if not sample:
            logger.warning(f"⚠️ Sample not found for update: {sample_id}")
            return None
        
        # Update fields - skip None values to preserve existing data
        for key, value in kwargs.items():
            if hasattr(sample, key) and value is not None:
                setattr(sample, key, value)
        
        await db.commit()
        await db.refresh(sample)
        
        logger.info(f"📝 Updated sample: {sample_id}")
        return sample
        
    except Exception as e:
        await db.rollback()
        logger.exception(f"❌ Failed to update sample {sample_id}: {e}")
        raise


async def delete_sample(db: AsyncSession, sample_id: str) -> bool:
    """
    Delete sample and related records (cascade).
    
    Args:
        db: Database session
        sample_id: Sample identifier
        
    Returns:
        True if deleted, False if not found
    """
    try:
        sample = await get_sample_by_id(db, sample_id)
        if not sample:
            logger.warning(f"⚠️ Sample not found for deletion: {sample_id}")
            return False
        
        # Clean up associated alerts to prevent orphaned records
        try:
            if sample.id:
                await delete_alerts_for_sample(db, sample.id)
        except Exception as alert_err:
            logger.warning(f"⚠️ Failed to clean up alerts for sample {sample_id}: {alert_err}")
        
        await db.delete(sample)
        await db.commit()
        
        logger.warning(f"🗑️ Deleted sample: {sample_id}")
        return True
        
    except Exception as e:
        await db.rollback()
        logger.exception(f"❌ Failed to delete sample {sample_id}: {e}")
        raise


# ============================================================================
# FCS Result CRUD Operations
# ============================================================================

async def create_fcs_result(
    db: AsyncSession,
    sample_id: int,
    **kwargs
) -> FCSResult:
    """
    Create FCS analysis result.
    
    Args:
        db: Database session
        sample_id: Database ID of parent sample
        **kwargs: FCS result fields (total_events, fsc_mean, etc.)
        
    Returns:
        Created FCSResult object
    """
    try:
        fcs_result = FCSResult(sample_id=sample_id, **kwargs)
        
        db.add(fcs_result)
        await db.commit()
        await db.refresh(fcs_result)
        
        logger.success(f"✅ Created FCS result for sample ID {sample_id}")
        return fcs_result
        
    except Exception as e:
        await db.rollback()
        logger.exception(f"❌ Failed to create FCS result: {e}")
        raise


async def get_fcs_results_by_sample(
    db: AsyncSession,
    sample_id: int
) -> List[FCSResult]:
    """
    Get all FCS results for a sample.
    
    Args:
        db: Database session
        sample_id: Database ID of sample
        
    Returns:
        List of FCSResult objects
    """
    query = select(FCSResult).where(FCSResult.sample_id == sample_id)
    result = await db.execute(query)
    return list(result.scalars().all())


# ============================================================================
# NTA Result CRUD Operations
# ============================================================================

async def create_nta_result(
    db: AsyncSession,
    sample_id: int,
    **kwargs
) -> NTAResult:
    """
    Create NTA analysis result.
    
    Args:
        db: Database session
        sample_id: Database ID of parent sample
        **kwargs: NTA result fields (mean_nm, concentration, etc.)
        
    Returns:
        Created NTAResult object
    """
    try:
        nta_result = NTAResult(sample_id=sample_id, **kwargs)
        
        db.add(nta_result)
        await db.commit()
        await db.refresh(nta_result)
        
        logger.success(f"✅ Created NTA result for sample ID {sample_id}")
        return nta_result
        
    except Exception as e:
        await db.rollback()
        logger.exception(f"❌ Failed to create NTA result: {e}")
        raise


async def get_nta_results_by_sample(
    db: AsyncSession,
    sample_id: int
) -> List[NTAResult]:
    """
    Get all NTA results for a sample.
    
    Args:
        db: Database session
        sample_id: Database ID of sample
        
    Returns:
        List of NTAResult objects
    """
    query = select(NTAResult).where(NTAResult.sample_id == sample_id)
    result = await db.execute(query)
    return list(result.scalars().all())
# ============================================================================
# Processing Job CRUD Operations
# ============================================================================

async def create_processing_job(
    db: AsyncSession,
    job_id: str,
    job_type: str,
    sample_id: Optional[int] = None,
) -> ProcessingJob:
    """
    Create a new processing job.
    
    Args:
        db: Database session
        job_id: UUID for the job
        job_type: Type of job (fcs_parse, nta_parse, batch_process)
        sample_id: Database ID of associated sample (optional)
        
    Returns:
        Created ProcessingJob object
    """
    try:
        job = ProcessingJob(
            job_id=job_id,
            job_type=job_type,
            sample_id=sample_id,
            status="pending",
            progress_percent=0,
        )
        
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        logger.success(f"✅ Created processing job: {job_id} (type: {job_type})")
        return job
        
    except Exception as e:
        await db.rollback()
        logger.exception(f"❌ Failed to create processing job: {e}")
        raise


async def get_job_by_id(db: AsyncSession, job_id: str) -> Optional[ProcessingJob]:
    """
    Get processing job by UUID.
    
    Args:
        db: Database session
        job_id: Job UUID
        
    Returns:
        ProcessingJob object or None if not found
    """
    query = select(ProcessingJob).where(ProcessingJob.job_id == job_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def update_job_progress(
    db: AsyncSession,
    job_id: str,
    progress_percent: int,
    current_step: Optional[str] = None,
) -> Optional[ProcessingJob]:
    """
    Update job progress.
    
    Args:
        db: Database session
        job_id: Job UUID
        progress_percent: Progress percentage (0-100)
        current_step: Description of current step
        
    Returns:
        Updated ProcessingJob object or None if not found
    """
    try:
        job = await get_job_by_id(db, job_id)
        if not job:
            logger.warning(f"⚠️ Job not found for progress update: {job_id}")
            return None
        
        setattr(job, 'progress_percent', progress_percent)
        if current_step:
            setattr(job, 'current_step', current_step)
        
        # Set started_at if not already set
        job_status = getattr(job, 'status', None)
        if job_status == "pending":
            setattr(job, 'status', "running")
            setattr(job, 'started_at', datetime.utcnow())
        
        await db.commit()
        await db.refresh(job)
        
        logger.info(f"📊 Job progress: {job_id} → {progress_percent}%")
        return job
        
    except Exception as e:
        await db.rollback()
        logger.exception(f"❌ Failed to update job progress: {e}")
        raise


async def update_job_status(
    db: AsyncSession,
    job_id: str,
    status: str,
    result_data: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    error_traceback: Optional[str] = None,
) -> Optional[ProcessingJob]:
    """
    Update job status.
    
    Args:
        db: Database session
        job_id: Job UUID
        status: New status (pending/running/completed/failed/cancelled)
        result_data: Result data (for completed jobs)
        error_message: Error message (for failed jobs)
        error_traceback: Full error traceback (for failed jobs)
        
    Returns:
        Updated ProcessingJob object or None if not found
    """
    try:
        job = await get_job_by_id(db, job_id)
        if not job:
            logger.warning(f"⚠️ Job not found for status update: {job_id}")
            return None
        
        old_status = getattr(job, 'status', None)
        setattr(job, 'status', status)
        
        # Set started_at if transitioning to running
        job_started = getattr(job, 'started_at', None)
        if status == "running" and job_started is None:
            setattr(job, 'started_at', datetime.utcnow())
        
        # Set completed_at if transitioning to terminal state
        job_completed = getattr(job, 'completed_at', None)
        if status in ["completed", "failed", "cancelled"] and job_completed is None:
            setattr(job, 'completed_at', datetime.utcnow())
            if status == "completed":
                setattr(job, 'progress_percent', 100)
        
        # Set result or error data
        if result_data:
            setattr(job, 'result_data', result_data)
        if error_message:
            setattr(job, 'error_message', error_message)
        if error_traceback:
            setattr(job, 'error_traceback', error_traceback)
        
        await db.commit()
        await db.refresh(job)
        
        logger.info(f"🔄 Job status: {job_id} → {old_status} → {status}")
        return job
        
    except Exception as e:
        await db.rollback()
        logger.exception(f"❌ Failed to update job status: {e}")
        raise


async def get_jobs_by_sample(
    db: AsyncSession,
    sample_id: int
) -> List[ProcessingJob]:
    """
    Get all processing jobs for a sample.
    
    Args:
        db: Database session
        sample_id: Database ID of sample
        
    Returns:
        List of ProcessingJob objects
    """
    query = select(ProcessingJob).where(ProcessingJob.sample_id == sample_id).order_by(
        ProcessingJob.created_at.desc()
    )
    result = await db.execute(query)
    return list(result.scalars().all())


# ============================================================================
# QC Report CRUD Operations
# ============================================================================

async def create_qc_report(
    db: AsyncSession,
    sample_id: int,
    qc_status: str,
    checks_performed: Dict[str, Any],
    **kwargs
) -> QCReport:
    """
    Create QC report.
    
    Args:
        db: Database session
        sample_id: Database ID of parent sample
        qc_status: QC status (pass/warning/fail)
        checks_performed: Dictionary of QC checks and results
        **kwargs: Additional fields (warnings_count, errors_count, etc.)
        
    Returns:
        Created QCReport object
    """
    try:
        qc_report = QCReport(
            sample_id=sample_id,
            qc_status=qc_status,
            checks_performed=checks_performed,
            **kwargs
        )
        
        db.add(qc_report)
        await db.commit()
        await db.refresh(qc_report)
        
        logger.success(f"✅ Created QC report for sample ID {sample_id}: {qc_status}")
        return qc_report
        
    except Exception as e:
        await db.rollback()
        logger.exception(f"❌ Failed to create QC report: {e}")
        raise


async def get_qc_reports_by_sample(
    db: AsyncSession,
    sample_id: int
) -> List[QCReport]:
    """
    Get all QC reports for a sample.
    
    Args:
        db: Database session
        sample_id: Database ID of sample
        
    Returns:
        List of QCReport objects
    """
    query = select(QCReport).where(QCReport.sample_id == sample_id).order_by(
        QCReport.created_at.desc()
    )
    result = await db.execute(query)
    return list(result.scalars().all())


# ============================================================================
# Utility Functions
# ============================================================================

async def get_sample_counts(db: AsyncSession) -> Dict[str, int]:
    """
    Get counts of samples by status.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with counts
    """
    # Total samples
    total_query = select(func.count()).select_from(Sample)
    total = (await db.execute(total_query)).scalar() or 0
    
    # By processing status
    pending_query = select(func.count()).select_from(Sample).where(  # type: ignore[arg-type]
        Sample.processing_status == ProcessingStatus.PENDING
    )
    pending = (await db.execute(pending_query)).scalar() or 0
    
    processing_query = select(func.count()).select_from(Sample).where(  # type: ignore[arg-type]
        Sample.processing_status == ProcessingStatus.RUNNING
    )
    processing = (await db.execute(processing_query)).scalar() or 0
    
    completed_query = select(func.count()).select_from(Sample).where(  # type: ignore[arg-type]
        Sample.processing_status == ProcessingStatus.COMPLETED
    )
    completed = (await db.execute(completed_query)).scalar() or 0
    
    failed_query = select(func.count()).select_from(Sample).where(
        Sample.processing_status == ProcessingStatus.FAILED
    )
    failed = (await db.execute(failed_query)).scalar() or 0
    
    return {
        "total": total,
        "pending": pending,
        "processing": processing,
        "completed": completed,
        "failed": failed,
    }


async def get_job_counts(db: AsyncSession) -> Dict[str, int]:
    """
    Get counts of jobs by status.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with counts
    """
    # Total jobs
    total_query = select(func.count()).select_from(ProcessingJob)
    total = (await db.execute(total_query)).scalar() or 0
    
    # By status
    pending_query = select(func.count()).select_from(ProcessingJob).where(
        ProcessingJob.status == "pending"
    )
    pending = (await db.execute(pending_query)).scalar() or 0
    
    running_query = select(func.count()).select_from(ProcessingJob).where(
        ProcessingJob.status == "running"
    )
    running = (await db.execute(running_query)).scalar() or 0
    
    completed_query = select(func.count()).select_from(ProcessingJob).where(
        ProcessingJob.status == "completed"
    )
    completed = (await db.execute(completed_query)).scalar() or 0
    
    failed_query = select(func.count()).select_from(ProcessingJob).where(
        ProcessingJob.status == "failed"
    )
    failed = (await db.execute(failed_query)).scalar() or 0
    
    return {
        "total": total,
        "pending": pending,
        "running": running,
        "completed": completed,
        "failed": failed,
    }


# ============================================================================
# Experimental Conditions CRUD Operations (TASK-009)
# ============================================================================

async def create_experimental_conditions(
    db: AsyncSession,
    sample_id: int,
    operator: str,
    temperature_celsius: Optional[float] = None,
    ph: Optional[float] = None,
    substrate_buffer: Optional[str] = None,
    custom_buffer: Optional[str] = None,
    sample_volume_ul: Optional[float] = None,
    dilution_factor: Optional[int] = None,
    antibody_used: Optional[str] = None,
    antibody_concentration_ug: Optional[float] = None,
    incubation_time_min: Optional[float] = None,
    sample_type: Optional[str] = None,
    filter_size_um: Optional[float] = None,
    notes: Optional[str] = None,
) -> ExperimentalConditions:
    """
    Create experimental conditions record for a sample.
    
    TASK-009: Save experimental conditions to database for reproducibility.
    
    Args:
        db: Database session
        sample_id: Database ID of the sample
        operator: Name of the operator (required)
        temperature_celsius: Temperature in Celsius
        ph: pH value
        substrate_buffer: Buffer used (PBS, HEPES, etc.)
        custom_buffer: Custom buffer name if substrate_buffer is "Custom"
        sample_volume_ul: Sample volume in microliters
        dilution_factor: Dilution factor (100, 500, 1000, etc.)
        antibody_used: Antibody type (CD81, CD9, CD63, etc.)
        antibody_concentration_ug: Antibody concentration in µg
        incubation_time_min: Incubation time in minutes
        sample_type: Sample preparation method
        filter_size_um: Filter size in micrometers
        notes: Free-text notes
        
    Returns:
        Created ExperimentalConditions object
    """
    try:
        conditions = ExperimentalConditions(
            sample_id=sample_id,
            operator=operator,
            temperature_celsius=temperature_celsius,
            ph=ph,
            substrate_buffer=substrate_buffer,
            custom_buffer=custom_buffer,
            sample_volume_ul=sample_volume_ul,
            dilution_factor=dilution_factor,
            antibody_used=antibody_used,
            antibody_concentration_ug=antibody_concentration_ug,
            incubation_time_min=incubation_time_min,
            sample_type=sample_type,
            filter_size_um=filter_size_um,
            notes=notes,
        )
        
        db.add(conditions)
        await db.commit()
        await db.refresh(conditions)
        
        logger.success(f"✅ Created experimental conditions for sample {sample_id} (ID: {conditions.id})")
        return conditions
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to create experimental conditions: {e}")
        raise


async def get_experimental_conditions_by_sample(
    db: AsyncSession,
    sample_id: int
) -> Optional[ExperimentalConditions]:
    """
    Get experimental conditions for a sample.
    
    Args:
        db: Database session
        sample_id: Database ID of the sample
        
    Returns:
        ExperimentalConditions object or None
    """
    query = select(ExperimentalConditions).where(
        ExperimentalConditions.sample_id == sample_id
    ).order_by(ExperimentalConditions.created_at.desc())
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def update_experimental_conditions(
    db: AsyncSession,
    conditions_id: int,
    **kwargs
) -> Optional[ExperimentalConditions]:
    """
    Update experimental conditions.
    
    Args:
        db: Database session
        conditions_id: ID of the conditions record
        **kwargs: Fields to update
        
    Returns:
        Updated ExperimentalConditions object or None
    """
    try:
        query = select(ExperimentalConditions).where(
            ExperimentalConditions.id == conditions_id
        )
        result = await db.execute(query)
        conditions = result.scalar_one_or_none()
        
        if not conditions:
            logger.warning(f"⚠️ Experimental conditions not found: {conditions_id}")
            return None
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(conditions, key) and value is not None:
                setattr(conditions, key, value)
        
        await db.commit()
        await db.refresh(conditions)
        
        logger.success(f"✅ Updated experimental conditions: {conditions_id}")
        return conditions
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to update experimental conditions: {e}")
        raise


async def delete_experimental_conditions(
    db: AsyncSession,
    conditions_id: int
) -> bool:
    """
    Delete experimental conditions.
    
    Args:
        db: Database session
        conditions_id: ID of the conditions record
        
    Returns:
        True if deleted, False if not found
    """
    try:
        query = delete(ExperimentalConditions).where(
            ExperimentalConditions.id == conditions_id
        )
        result = await db.execute(query)
        await db.commit()
        
        deleted = result.rowcount > 0
        if deleted:
            logger.success(f"✅ Deleted experimental conditions: {conditions_id}")
        else:
            logger.warning(f"⚠️ Experimental conditions not found for deletion: {conditions_id}")
        
        return deleted
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to delete experimental conditions: {e}")
        raise


# ============================================================================
# Alert CRUD Operations (CRMIT-003)
# ============================================================================

async def create_alert(
    db: AsyncSession,
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    source: str,
    sample_id: Optional[int] = None,
    user_id: Optional[int] = None,
    sample_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Alert:
    """
    Create a new alert.
    
    Args:
        db: Database session
        alert_type: Type of alert (AlertType enum value)
        severity: Severity level (AlertSeverity enum value)
        title: Short alert title
        message: Detailed alert message
        source: Source of alert (e.g., "fcs_analysis", "nta_analysis")
        sample_id: Optional linked sample ID
        user_id: Optional user ID (owner of the sample)
        sample_name: Optional sample name for quick display
        metadata: Optional additional context data
        
    Returns:
        Created Alert object
    """
    try:
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            source=source,
            sample_id=sample_id,
            user_id=user_id,
            sample_name=sample_name,
            alert_data=metadata,  # DB column is 'alert_data', param is 'metadata' for API compat
            is_acknowledged=False,
        )
        
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
        
        logger.info(f"🔔 Created alert: [{severity.upper()}] {title}")
        return alert
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to create alert: {e}")
        raise


async def get_alert_by_id(
    db: AsyncSession,
    alert_id: int
) -> Optional[Alert]:
    """Get alert by ID."""
    try:
        result = await db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"❌ Failed to get alert {alert_id}: {e}")
        raise


async def get_alerts(
    db: AsyncSession,
    user_id: Optional[int] = None,
    sample_id: Optional[int] = None,
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    is_acknowledged: Optional[bool] = None,
    source: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    order_by: str = "created_at",
    order_desc: bool = True,
) -> List[Alert]:
    """
    Get alerts with filtering and pagination.
    
    Args:
        db: Database session
        user_id: Filter by user ID
        sample_id: Filter by sample ID
        severity: Filter by severity level
        alert_type: Filter by alert type
        is_acknowledged: Filter by acknowledgment status
        source: Filter by source
        limit: Maximum number of results
        offset: Offset for pagination
        order_by: Field to order by
        order_desc: Whether to order descending
        
    Returns:
        List of Alert objects
    """
    try:
        query = select(Alert)
        
        # Apply filters
        if user_id is not None:
            query = query.where(Alert.user_id == user_id)
        if sample_id is not None:
            query = query.where(Alert.sample_id == sample_id)
        if severity is not None:
            query = query.where(Alert.severity == severity)
        if alert_type is not None:
            query = query.where(Alert.alert_type == alert_type)
        if is_acknowledged is not None:
            query = query.where(Alert.is_acknowledged == is_acknowledged)
        if source is not None:
            query = query.where(Alert.source == source)
        
        # Apply ordering
        order_column = getattr(Alert, order_by, Alert.created_at)
        if order_desc:
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        return list(result.scalars().all())
        
    except Exception as e:
        logger.error(f"❌ Failed to get alerts: {e}")
        raise


async def get_alert_counts(
    db: AsyncSession,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get alert counts grouped by severity and acknowledgment status.
    
    Args:
        db: Database session
        user_id: Optional user ID filter
        
    Returns:
        Dictionary with counts
    """
    try:
        # Base query
        base_filter = Alert.user_id == user_id if user_id else True
        
        # Total unacknowledged
        unack_query = select(func.count(Alert.id)).where(
            base_filter,
            Alert.is_acknowledged == False  # noqa: E712
        )
        unack_result = await db.execute(unack_query)
        total_unacknowledged = unack_result.scalar() or 0
        
        # Total acknowledged
        ack_query = select(func.count(Alert.id)).where(
            base_filter,
            Alert.is_acknowledged == True  # noqa: E712
        )
        ack_result = await db.execute(ack_query)
        total_acknowledged = ack_result.scalar() or 0
        
        # Count by severity (unacknowledged only)
        severity_counts = {}
        for sev in ["critical", "error", "warning", "info"]:
            sev_query = select(func.count(Alert.id)).where(
                base_filter,
                Alert.severity == sev,
                Alert.is_acknowledged == False  # noqa: E712
            )
            sev_result = await db.execute(sev_query)
            severity_counts[sev] = sev_result.scalar() or 0
        
        return {
            "total": total_unacknowledged + total_acknowledged,
            "unacknowledged": total_unacknowledged,
            "acknowledged": total_acknowledged,
            "by_severity": severity_counts,
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get alert counts: {e}")
        raise


async def acknowledge_alert(
    db: AsyncSession,
    alert_id: int,
    acknowledged_by: Optional[int] = None,
    notes: Optional[str] = None,
) -> Optional[Alert]:
    """
    Acknowledge an alert.
    
    Args:
        db: Database session
        alert_id: ID of the alert to acknowledge
        acknowledged_by: User ID of acknowledger
        notes: Optional acknowledgment notes
        
    Returns:
        Updated Alert object or None if not found
    """
    try:
        result = await db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        alert = result.scalar_one_or_none()
        
        if not alert:
            logger.warning(f"⚠️ Alert not found: {alert_id}")
            return None
        
        alert.is_acknowledged = True
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledgment_notes = notes
        
        await db.commit()
        await db.refresh(alert)
        
        logger.success(f"✅ Acknowledged alert: {alert_id}")
        return alert
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to acknowledge alert: {e}")
        raise


async def acknowledge_multiple_alerts(
    db: AsyncSession,
    alert_ids: List[int],
    acknowledged_by: Optional[int] = None,
    notes: Optional[str] = None,
) -> int:
    """
    Acknowledge multiple alerts at once.
    
    Args:
        db: Database session
        alert_ids: List of alert IDs to acknowledge
        acknowledged_by: User ID of acknowledger
        notes: Optional acknowledgment notes
        
    Returns:
        Number of alerts acknowledged
    """
    try:
        count = 0
        for alert_id in alert_ids:
            result = await acknowledge_alert(db, alert_id, acknowledged_by, notes)
            if result:
                count += 1
        
        logger.success(f"✅ Acknowledged {count} alerts")
        return count
        
    except Exception as e:
        logger.error(f"❌ Failed to acknowledge multiple alerts: {e}")
        raise


async def delete_alert(
    db: AsyncSession,
    alert_id: int
) -> bool:
    """
    Delete an alert.
    
    Args:
        db: Database session
        alert_id: ID of the alert to delete
        
    Returns:
        True if deleted, False if not found
    """
    try:
        query = delete(Alert).where(Alert.id == alert_id)
        result = await db.execute(query)
        await db.commit()
        
        deleted = result.rowcount > 0
        if deleted:
            logger.success(f"✅ Deleted alert: {alert_id}")
        else:
            logger.warning(f"⚠️ Alert not found for deletion: {alert_id}")
        
        return deleted
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to delete alert: {e}")
        raise


async def delete_alerts_for_sample(
    db: AsyncSession,
    sample_id: int
) -> int:
    """
    Delete all alerts for a sample.
    
    Args:
        db: Database session
        sample_id: Sample ID
        
    Returns:
        Number of alerts deleted
    """
    try:
        query = delete(Alert).where(Alert.sample_id == sample_id)
        result = await db.execute(query)
        await db.commit()
        
        deleted_count = result.rowcount
        logger.success(f"✅ Deleted {deleted_count} alerts for sample {sample_id}")
        return deleted_count
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to delete alerts for sample: {e}")
        raise
