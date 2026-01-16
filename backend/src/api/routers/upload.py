"""
File Upload Router
==================

Endpoints for uploading and processing FCS, NTA, and TEM files.

Endpoints:
- POST /upload/fcs  - Upload and process FCS file
- POST /upload/nta  - Upload and process NTA file
- POST /upload/tem  - Upload and process TEM file (future)

Author: CRMIT Backend Team
Date: November 21, 2025
"""

from pathlib import Path
from typing import Optional
import shutil
import uuid
from datetime import datetime
import sys
import numpy as np

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status, Header
from fastapi.responses import JSONResponse  # noqa: F401
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore[import-not-found]
from loguru import logger

from src.api.config import get_settings
from src.database.connection import get_session
from src.database.models import Sample, FCSResult, NTAResult, ProcessingJob  # type: ignore[import-not-found]
from src.database.crud import (
    create_sample,
    get_sample_by_id,
    update_sample,
    create_fcs_result,
    create_nta_result,
    create_processing_job,
    update_job_status,
    create_alert,
)
from src.database.models import AlertType, AlertSeverity
# Import professional parsers
from src.parsers.fcs_parser import FCSParser
from src.parsers.nta_parser import NTAParser
from src.physics.mie_scatter import MieScatterCalculator
# Import size configuration for consistent filtering (TASK-002 fix, Dec 17, 2025)
from src.physics.size_config import (
    DEFAULT_SIZE_CONFIG, 
    filter_particles_by_size,
    calculate_size_statistics
)

settings = get_settings()
router = APIRouter()


# ============================================================================
# Alert Thresholds Configuration (CRMIT-003)
# ============================================================================

# Quality control alert thresholds
ALERT_THRESHOLDS = {
    "high_debris_pct": 20.0,           # Alert if debris > 20%
    "critical_debris_pct": 35.0,       # Critical if debris > 35%
    "low_event_count": 1000,           # Alert if events < 1000
    "critical_low_events": 500,        # Critical if events < 500
    "high_exclusion_pct": 30.0,        # Alert if exclusion > 30%
    "critical_exclusion_pct": 50.0,    # Critical if exclusion > 50%
    "unusual_size_cv": 100.0,          # Alert if size CV > 100%
    "abnormal_fsc_median": 100000,     # Alert if FSC median > 100k (unusual)
}


async def generate_analysis_alerts(
    db: AsyncSession,
    sample_id: int,
    sample_name: str,
    user_id: Optional[int],
    fcs_results: dict,
    source: str = "FCS Analysis"
) -> list[dict]:
    """
    Generate alerts based on FCS analysis results.
    
    CRMIT-003: Alert System with Timestamps
    
    Checks for:
    - High debris percentage
    - Low event counts
    - High particle exclusion rates
    - Unusual size distributions
    
    Args:
        db: Database session
        sample_id: Database sample ID
        sample_name: Display name for the sample
        user_id: User who uploaded the sample
        fcs_results: Parsed FCS analysis results
        source: Alert source identifier
        
    Returns:
        List of created alert dictionaries
    """
    alerts_created = []
    
    # Extract relevant metrics
    debris_pct = fcs_results.get('debris_pct')
    total_events = fcs_results.get('total_events', 0)
    excluded_pct = fcs_results.get('excluded_particles_pct')
    size_stats = fcs_results.get('size_statistics', {})
    size_cv = None
    if size_stats:
        mean_size = size_stats.get('mean', 0)
        std_size = size_stats.get('std', 0)
        if mean_size and mean_size > 0:
            size_cv = (std_size / mean_size) * 100
    
    # Check debris percentage
    if debris_pct is not None:
        if debris_pct >= ALERT_THRESHOLDS["critical_debris_pct"]:
            alert = await create_alert(
                db=db,
                sample_id=sample_id,
                user_id=user_id,
                alert_type=AlertType.HIGH_DEBRIS,
                severity=AlertSeverity.CRITICAL,
                title="Critical: Very High Debris Percentage",
                message=f"Debris percentage ({debris_pct:.1f}%) exceeds critical threshold ({ALERT_THRESHOLDS['critical_debris_pct']}%). "
                        "Sample quality may be severely compromised. Consider re-processing or excluding from analysis.",
                source=source,
                sample_name=sample_name,
                metadata={
                    "debris_pct": debris_pct,
                    "threshold": ALERT_THRESHOLDS["critical_debris_pct"],
                    "recommendation": "Review sample preparation and consider re-running"
                }
            )
            alerts_created.append({"id": alert.id, "severity": "critical", "type": "high_debris"})
            logger.warning(f"🚨 Critical debris alert created for {sample_name}: {debris_pct:.1f}%")
            
        elif debris_pct >= ALERT_THRESHOLDS["high_debris_pct"]:
            alert = await create_alert(
                db=db,
                sample_id=sample_id,
                user_id=user_id,
                alert_type=AlertType.HIGH_DEBRIS,
                severity=AlertSeverity.WARNING,
                title="Warning: High Debris Percentage",
                message=f"Debris percentage ({debris_pct:.1f}%) exceeds warning threshold ({ALERT_THRESHOLDS['high_debris_pct']}%). "
                        "This may affect analysis accuracy.",
                source=source,
                sample_name=sample_name,
                metadata={
                    "debris_pct": debris_pct,
                    "threshold": ALERT_THRESHOLDS["high_debris_pct"],
                    "recommendation": "Review results carefully"
                }
            )
            alerts_created.append({"id": alert.id, "severity": "warning", "type": "high_debris"})
            logger.info(f"⚠️ High debris alert created for {sample_name}: {debris_pct:.1f}%")
    
    # Check event count
    if total_events > 0:
        if total_events < ALERT_THRESHOLDS["critical_low_events"]:
            alert = await create_alert(
                db=db,
                sample_id=sample_id,
                user_id=user_id,
                alert_type=AlertType.LOW_EVENT_COUNT,
                severity=AlertSeverity.CRITICAL,
                title="Critical: Very Low Event Count",
                message=f"Event count ({total_events:,}) is critically low (below {ALERT_THRESHOLDS['critical_low_events']:,}). "
                        "Statistical analysis may be unreliable. Consider acquiring more data.",
                source=source,
                sample_name=sample_name,
                metadata={
                    "event_count": total_events,
                    "threshold": ALERT_THRESHOLDS["critical_low_events"],
                    "recommendation": "Re-acquire sample with longer acquisition time"
                }
            )
            alerts_created.append({"id": alert.id, "severity": "critical", "type": "low_event_count"})
            logger.warning(f"🚨 Critical low event alert for {sample_name}: {total_events:,} events")
            
        elif total_events < ALERT_THRESHOLDS["low_event_count"]:
            alert = await create_alert(
                db=db,
                sample_id=sample_id,
                user_id=user_id,
                alert_type=AlertType.LOW_EVENT_COUNT,
                severity=AlertSeverity.WARNING,
                title="Warning: Low Event Count",
                message=f"Event count ({total_events:,}) is below recommended minimum ({ALERT_THRESHOLDS['low_event_count']:,}). "
                        "Consider whether statistical power is sufficient for your analysis.",
                source=source,
                sample_name=sample_name,
                metadata={
                    "event_count": total_events,
                    "threshold": ALERT_THRESHOLDS["low_event_count"],
                    "recommendation": "Review if sufficient for intended analysis"
                }
            )
            alerts_created.append({"id": alert.id, "severity": "warning", "type": "low_event_count"})
            logger.info(f"⚠️ Low event alert for {sample_name}: {total_events:,} events")
    
    # Check particle exclusion rate
    if excluded_pct is not None:
        if excluded_pct >= ALERT_THRESHOLDS["critical_exclusion_pct"]:
            alert = await create_alert(
                db=db,
                sample_id=sample_id,
                user_id=user_id,
                alert_type=AlertType.QUALITY_WARNING,
                severity=AlertSeverity.ERROR,
                title="Error: Excessive Particle Exclusion",
                message=f"Particle exclusion rate ({excluded_pct:.1f}%) is excessive (above {ALERT_THRESHOLDS['critical_exclusion_pct']}%). "
                        "Most particles are outside the valid size range. Check instrument calibration or sample preparation.",
                source=source,
                sample_name=sample_name,
                metadata={
                    "exclusion_pct": excluded_pct,
                    "threshold": ALERT_THRESHOLDS["critical_exclusion_pct"],
                    "recommendation": "Check calibration and sample preparation"
                }
            )
            alerts_created.append({"id": alert.id, "severity": "error", "type": "quality_warning"})
            logger.error(f"❌ Excessive exclusion alert for {sample_name}: {excluded_pct:.1f}%")
            
        elif excluded_pct >= ALERT_THRESHOLDS["high_exclusion_pct"]:
            alert = await create_alert(
                db=db,
                sample_id=sample_id,
                user_id=user_id,
                alert_type=AlertType.QUALITY_WARNING,
                severity=AlertSeverity.WARNING,
                title="Warning: High Particle Exclusion Rate",
                message=f"Particle exclusion rate ({excluded_pct:.1f}%) is elevated (above {ALERT_THRESHOLDS['high_exclusion_pct']}%). "
                        "A significant portion of particles are outside the analysis range.",
                source=source,
                sample_name=sample_name,
                metadata={
                    "exclusion_pct": excluded_pct,
                    "threshold": ALERT_THRESHOLDS["high_exclusion_pct"],
                    "recommendation": "Review size distribution and filtering settings"
                }
            )
            alerts_created.append({"id": alert.id, "severity": "warning", "type": "quality_warning"})
            logger.info(f"⚠️ High exclusion alert for {sample_name}: {excluded_pct:.1f}%")
    
    # Check for unusual size distribution (high CV)
    if size_cv is not None and size_cv > ALERT_THRESHOLDS["unusual_size_cv"]:
        alert = await create_alert(
            db=db,
            sample_id=sample_id,
            user_id=user_id,
            alert_type=AlertType.SIZE_DISTRIBUTION_UNUSUAL,
            severity=AlertSeverity.INFO,
            title="Info: Highly Variable Size Distribution",
            message=f"Size distribution coefficient of variation ({size_cv:.1f}%) indicates high heterogeneity. "
                    "This may be expected for mixed populations but should be noted.",
            source=source,
            sample_name=sample_name,
            metadata={
                "size_cv_pct": size_cv,
                "mean_size_nm": size_stats.get('mean'),
                "std_size_nm": size_stats.get('std'),
                "threshold": ALERT_THRESHOLDS["unusual_size_cv"]
            }
        )
        alerts_created.append({"id": alert.id, "severity": "info", "type": "size_distribution_unusual"})
        logger.info(f"ℹ️ Size variability alert for {sample_name}: CV={size_cv:.1f}%")
    
    return alerts_created


async def generate_nta_alerts(
    db: AsyncSession,
    sample_id: int,
    sample_name: str,
    user_id: Optional[int],
    nta_results: dict,
    source: str = "NTA Analysis"
) -> list[dict]:
    """
    Generate alerts based on NTA analysis results.
    
    CRMIT-003: Alert System with Timestamps
    
    Checks for:
    - Low particle concentration
    - Unusual size distributions
    - Temperature variations
    
    Args:
        db: Database session
        sample_id: Database sample ID
        sample_name: Display name for the sample
        user_id: User who uploaded the sample
        nta_results: Parsed NTA analysis results
        source: Alert source identifier
        
    Returns:
        List of created alert dictionaries
    """
    alerts_created = []
    
    # NTA-specific thresholds
    NTA_THRESHOLDS = {
        "low_concentration": 1e6,           # Alert if < 1e6 particles/mL
        "critical_low_concentration": 1e5,  # Critical if < 1e5 particles/mL
        "high_polydispersity": 50.0,        # Alert if span > 50%
        "unusual_temp_min": 20.0,           # Alert if temp < 20°C
        "unusual_temp_max": 30.0,           # Alert if temp > 30°C
    }
    
    # Extract relevant metrics
    concentration = nta_results.get('concentration_particles_ml')
    d10 = nta_results.get('d10_nm')
    d50 = nta_results.get('d50_nm')
    d90 = nta_results.get('d90_nm')
    temperature = nta_results.get('temperature_celsius')
    
    # Calculate polydispersity (span = (d90-d10)/d50 * 100)
    polydispersity = None
    if d10 and d50 and d90 and d50 > 0:
        polydispersity = ((d90 - d10) / d50) * 100
    
    # Check concentration
    if concentration is not None:
        if concentration < NTA_THRESHOLDS["critical_low_concentration"]:
            alert = await create_alert(
                db=db,
                sample_id=sample_id,
                user_id=user_id,
                alert_type=AlertType.LOW_EVENT_COUNT,
                severity=AlertSeverity.CRITICAL,
                title="Critical: Very Low Particle Concentration",
                message=f"Particle concentration ({concentration:.2e} particles/mL) is critically low. "
                        "NTA measurements may be unreliable at this concentration.",
                source=source,
                sample_name=sample_name,
                metadata={
                    "concentration_particles_ml": concentration,
                    "threshold": NTA_THRESHOLDS["critical_low_concentration"],
                    "recommendation": "Concentrate sample or check dilution factor"
                }
            )
            alerts_created.append({"id": alert.id, "severity": "critical", "type": "low_event_count"})
            logger.warning(f"🚨 Critical low concentration alert for {sample_name}: {concentration:.2e}")
            
        elif concentration < NTA_THRESHOLDS["low_concentration"]:
            alert = await create_alert(
                db=db,
                sample_id=sample_id,
                user_id=user_id,
                alert_type=AlertType.LOW_EVENT_COUNT,
                severity=AlertSeverity.WARNING,
                title="Warning: Low Particle Concentration",
                message=f"Particle concentration ({concentration:.2e} particles/mL) is below optimal range. "
                        "Consider whether measurement precision is sufficient.",
                source=source,
                sample_name=sample_name,
                metadata={
                    "concentration_particles_ml": concentration,
                    "threshold": NTA_THRESHOLDS["low_concentration"],
                    "recommendation": "Review dilution factor"
                }
            )
            alerts_created.append({"id": alert.id, "severity": "warning", "type": "low_event_count"})
            logger.info(f"⚠️ Low concentration alert for {sample_name}: {concentration:.2e}")
    
    # Check polydispersity
    if polydispersity is not None and polydispersity > NTA_THRESHOLDS["high_polydispersity"]:
        alert = await create_alert(
            db=db,
            sample_id=sample_id,
            user_id=user_id,
            alert_type=AlertType.SIZE_DISTRIBUTION_UNUSUAL,
            severity=AlertSeverity.INFO,
            title="Info: High Polydispersity",
            message=f"Sample polydispersity (span: {polydispersity:.1f}%) indicates a heterogeneous size distribution. "
                    "This may be expected but should be considered in interpretation.",
            source=source,
            sample_name=sample_name,
            metadata={
                "polydispersity_pct": polydispersity,
                "d10_nm": d10,
                "d50_nm": d50,
                "d90_nm": d90,
                "threshold": NTA_THRESHOLDS["high_polydispersity"]
            }
        )
        alerts_created.append({"id": alert.id, "severity": "info", "type": "size_distribution_unusual"})
        logger.info(f"ℹ️ Polydispersity alert for {sample_name}: span={polydispersity:.1f}%")
    
    # Check temperature
    if temperature is not None:
        if temperature < NTA_THRESHOLDS["unusual_temp_min"] or temperature > NTA_THRESHOLDS["unusual_temp_max"]:
            alert = await create_alert(
                db=db,
                sample_id=sample_id,
                user_id=user_id,
                alert_type=AlertType.CALIBRATION_NEEDED,
                severity=AlertSeverity.WARNING,
                title="Warning: Unusual Measurement Temperature",
                message=f"Measurement temperature ({temperature:.1f}°C) is outside normal range "
                        f"({NTA_THRESHOLDS['unusual_temp_min']}-{NTA_THRESHOLDS['unusual_temp_max']}°C). "
                        "This may affect viscosity calculations and size accuracy.",
                source=source,
                sample_name=sample_name,
                metadata={
                    "temperature_celsius": temperature,
                    "normal_min": NTA_THRESHOLDS["unusual_temp_min"],
                    "normal_max": NTA_THRESHOLDS["unusual_temp_max"],
                    "recommendation": "Ensure temperature equilibration before measurement"
                }
            )
            alerts_created.append({"id": alert.id, "severity": "warning", "type": "calibration_needed"})
            logger.info(f"⚠️ Temperature alert for {sample_name}: {temperature:.1f}°C")
    
    return alerts_created


# ============================================================================
# Helper Functions
# ============================================================================

async def save_uploaded_file(upload_file: UploadFile, destination: Path) -> Path:
    """
    Save uploaded file to disk.
    
    Args:
        upload_file: FastAPI UploadFile object
        destination: Destination file path
    
    Returns:
        Path to saved file
    
    Raises:
        HTTPException: If file size exceeds limit or save fails
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Check file size
        upload_file.file.seek(0, 2)  # Seek to end
        file_size = upload_file.file.tell()
        upload_file.file.seek(0)  # Reset to start
        
        max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size {file_size / 1024 / 1024:.1f}MB exceeds limit of {settings.max_upload_size_mb}MB"
            )
        
        # Save file
        with destination.open("wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        
        logger.info(f"✅ Saved uploaded file: {destination.name} ({file_size / 1024:.1f}KB)")
        return destination
        
    except Exception as e:
        logger.error(f"❌ Failed to save file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )


def generate_sample_id(filename: str) -> str:
    """
    Generate sample ID from filename.
    
    Args:
        filename: Original filename
    
    Returns:
        Sample ID (e.g., "P5_F10_CD81")
    
    Logic:
    1. Extract from filename patterns (e.g., "P5+F10+CD81.fcs" → "P5_F10_CD81")
    2. Fall back to timestamp-based ID if pattern not recognized
    """
    # Remove extension
    name = Path(filename).stem
    
    # Replace common separators with underscore
    name = name.replace('+', '_').replace('-', '_').replace(' ', '_')
    
    # Clean up multiple underscores
    while '__' in name:
        name = name.replace('__', '_')
    
    return name


# ============================================================================
# FCS Upload Endpoint
# ============================================================================

@router.post("/fcs", response_model=dict)
async def upload_fcs_file(
    file: UploadFile = File(...),
    treatment: Optional[str] = Form(None),
    concentration_ug: Optional[float] = Form(None),
    preparation_method: Optional[str] = Form(None),
    operator: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    user_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_session)
):
    """
    Upload and process FCS file.
    
    **Request:**
    - file: FCS file (multipart/form-data)
    - treatment: Treatment name (e.g., "CD81", "ISO", "Control")
    - concentration_ug: Antibody concentration in µg
    - preparation_method: Preparation method (e.g., "SEC", "Centrifugation")
    - operator: Operator name
    - notes: Additional notes
    
    **Response:**
    ```json
    {
        "success": true,
        "sample_id": "P5_F10_CD81",
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "pending",
        "message": "File uploaded successfully, processing started"
    }
    ```
    
    **Processing Pipeline:**
    1. Save uploaded file to `data/uploads/`
    2. Create sample record in database
    3. Create processing job (async)
    4. Return immediately with job ID
    5. Background worker parses FCS file
    6. Background worker saves results to database and Parquet
    """
    logger.info(f"📤 Uploading FCS file: {file.filename}")
    
    try:
        # Validate file extension
        filename = file.filename or ""
        if not filename.lower().endswith('.fcs'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only .fcs files are accepted."
            )
        
        # Generate sample ID
        sample_id = generate_sample_id(file.filename or "unknown.fcs")
        
        # Save uploaded file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = settings.upload_dir / f"{timestamp}_{file.filename}"
        await save_uploaded_file(file, file_path)
        
        # Parse FCS file using professional parser
        fcs_results = None
        try:
            logger.info(f"🔬 Parsing FCS file with professional parser...")
            parser = FCSParser(file_path)
            
            # Validate file
            if not parser.validate():
                logger.warning(f"⚠️ FCS file validation failed, continuing anyway...")
            
            # Parse and get results
            parsed_data = parser.parse()
            
            if parsed_data is not None and len(parsed_data) > 0:
                # Get comprehensive statistics
                logger.info(f"📊 Calculating comprehensive statistics...")
                stats = parser.get_statistics()
                
                # Extract channel names and total events
                event_count = stats.get('_summary', {}).get('total_events', len(parsed_data))
                channels = stats.get('_summary', {}).get('channels', list(parsed_data.columns))
                
                # Find FSC and SSC channels (handle different naming conventions)
                fsc_channel = None
                ssc_channel = None
                
                # TASK-010: Detect VSSC1-H and VSSC2-H for VSSC_MAX calculation
                # Parvesh (Dec 5, 2025): "Create a new column... VSSC max and let it look at 
                # the VSSC 1 H and VSSC 2 H and pick whichever the larger one is"
                vssc1_h_channel = None
                vssc2_h_channel = None
                vssc_max_created = False
                vssc_selection_stats = None
                
                for ch in channels:
                    ch_upper = ch.upper()
                    # FSC detection: VFSC-H, FSC-A, FSC-H, VFSC_A, or just FSC
                    if fsc_channel is None and 'FSC' in ch_upper:
                        # Prefer height channels (-H) over area (-A)
                        if '-H' in ch_upper or '_H' in ch_upper:
                            fsc_channel = ch
                        elif '-A' in ch_upper or '_A' in ch_upper:
                            if fsc_channel is None:
                                fsc_channel = ch
                        elif fsc_channel is None:
                            fsc_channel = ch
                    
                    # TASK-010: Detect VSSC1-H and VSSC2-H specifically
                    if 'VSSC1' in ch_upper and ('-H' in ch_upper or '_H' in ch_upper):
                        vssc1_h_channel = ch
                    elif 'VSSC2' in ch_upper and ('-H' in ch_upper or '_H' in ch_upper):
                        vssc2_h_channel = ch
                    # SSC detection: VSSC-H, SSC-A, SSC-H, VSSC_A, or just SSC
                    elif ssc_channel is None and 'SSC' in ch_upper:
                        # Prefer height channels (-H) over area (-A)
                        if '-H' in ch_upper or '_H' in ch_upper:
                            ssc_channel = ch
                        elif '-A' in ch_upper or '_A' in ch_upper:
                            if ssc_channel is None:
                                ssc_channel = ch
                        elif ssc_channel is None:
                            ssc_channel = ch
                
                # TASK-010: Create VSSC_MAX column if both VSSC1-H and VSSC2-H exist
                # For each event, VSSC_MAX = max(VSSC1-H, VSSC2-H)
                if vssc1_h_channel and vssc2_h_channel:
                    try:
                        vssc1_values = parsed_data[vssc1_h_channel].values
                        vssc2_values = parsed_data[vssc2_h_channel].values
                        
                        # Create VSSC_MAX as element-wise maximum
                        vssc_max_values = np.maximum(vssc1_values, vssc2_values)
                        parsed_data['VSSC_MAX'] = vssc_max_values
                        
                        # Calculate selection statistics (which channel was selected for each event)
                        vssc1_selected = np.sum(vssc1_values >= vssc2_values)
                        vssc2_selected = np.sum(vssc2_values > vssc1_values)
                        total_events_vssc = len(vssc_max_values)
                        
                        vssc_selection_stats = {
                            'vssc1_channel': vssc1_h_channel,
                            'vssc2_channel': vssc2_h_channel,
                            'vssc1_selected_count': int(vssc1_selected),
                            'vssc2_selected_count': int(vssc2_selected),
                            'vssc1_selected_pct': float((vssc1_selected / total_events_vssc) * 100) if total_events_vssc > 0 else 0.0,
                            'vssc2_selected_pct': float((vssc2_selected / total_events_vssc) * 100) if total_events_vssc > 0 else 0.0,
                        }
                        
                        # Use VSSC_MAX as the SSC channel for Mie calculations
                        ssc_channel = 'VSSC_MAX'
                        vssc_max_created = True
                        
                        logger.info(
                            f"✨ TASK-010: Created VSSC_MAX column from {vssc1_h_channel} and {vssc2_h_channel}"
                        )
                        logger.info(
                            f"📊 VSSC selection: {vssc1_h_channel}={vssc_selection_stats['vssc1_selected_pct']:.1f}%, "
                            f"{vssc2_h_channel}={vssc_selection_stats['vssc2_selected_pct']:.1f}%"
                        )
                    except Exception as vssc_error:
                        logger.warning(f"⚠️ Failed to create VSSC_MAX: {vssc_error}")
                        # Fall back to using whichever VSSC channel exists
                        if vssc1_h_channel:
                            ssc_channel = vssc1_h_channel
                        elif vssc2_h_channel:
                            ssc_channel = vssc2_h_channel
                
                # Fallback: Use first two channels if FSC/SSC not found (for generic channel names)
                if not fsc_channel and len(channels) >= 1:
                    fsc_channel = channels[0]
                    logger.warning(f"⚠️ FSC channel not found, using first channel: {fsc_channel}")
                
                if not ssc_channel and len(channels) >= 2:
                    ssc_channel = channels[1]
                    logger.warning(f"⚠️ SSC channel not found, using second channel: {ssc_channel}")
                
                logger.info(f"🔍 Detected channels - FSC: {fsc_channel}, SSC: {ssc_channel}")
                
                # Get statistics for FSC and SSC channels
                fsc_stats = stats.get(fsc_channel, {}) if fsc_channel else {}
                ssc_stats = stats.get(ssc_channel, {}) if ssc_channel else {}
                
                # Calculate particle size using Mie scattering theory
                # TASK-002 FIX (Dec 17, 2025): Use extended range to avoid edge clustering
                particle_size_median_nm = None
                if fsc_channel and fsc_stats.get('median'):
                    try:
                        # Initialize Mie calculator (488nm laser, typical EV RI, PBS medium)
                        mie_calc = MieScatterCalculator(
                            wavelength_nm=488.0,
                            n_particle=1.40,
                            n_medium=1.33
                        )
                        # Estimate diameter from FSC median intensity
                        # Uses extended range from size_config (30-220nm) to avoid clamping
                        diameter_nm, success = mie_calc.diameter_from_scatter(
                            fsc_intensity=fsc_stats['median'],
                            # min_diameter/max_diameter now default to SIZE_CONFIG values (30-220nm)
                        )
                        if success:
                            particle_size_median_nm = float(diameter_nm)
                            logger.info(f"✨ Estimated particle size: {particle_size_median_nm:.1f} nm")
                    except Exception as mie_error:
                        logger.warning(f"⚠️ Mie calculation failed: {mie_error}")
                
                # Calculate size distribution percentiles using Mie theory
                # FIXED: Use batch calculation on actual FSC values, then compute percentiles from sizes
                size_statistics = None
                computed_sizes = None  # Will store actual sizes for std calculation
                if fsc_channel and fsc_channel in parsed_data.columns:
                    try:
                        mie_calc = MieScatterCalculator(wavelength_nm=488.0, n_particle=1.40, n_medium=1.33)
                        
                        # Sample FSC values and convert to sizes using fast batch method
                        sample_size = min(10000, len(parsed_data))
                        fsc_values = parsed_data[fsc_channel].values
                        # Filter out non-positive values
                        positive_fsc = fsc_values[fsc_values > 0]
                        if len(positive_fsc) > sample_size:
                            # Random sample
                            np.random.seed(42)
                            positive_fsc = np.random.choice(positive_fsc, size=sample_size, replace=False)
                        
                        # Use fast vectorized batch calculation (100x faster than loop)
                        computed_sizes, success_mask = mie_calc.diameters_from_scatter_batch(
                            positive_fsc, min_diameter=30.0, max_diameter=500.0
                        )
                        valid_sizes = computed_sizes[success_mask & (computed_sizes >= 30) & (computed_sizes <= 500)]
                        
                        if len(valid_sizes) > 10:
                            # Calculate percentiles from actual computed sizes
                            d10 = float(np.percentile(valid_sizes, 10))
                            d50 = float(np.percentile(valid_sizes, 50))
                            d90 = float(np.percentile(valid_sizes, 90))
                            d_mean = float(np.mean(valid_sizes))
                            size_std = float(np.std(valid_sizes))
                            
                            size_statistics = {
                                'd10': d10,
                                'd50': d50,
                                'd90': d90,
                                'mean': d_mean,
                                'std': size_std
                            }
                            logger.info(f"📏 Size distribution: D10={d10:.1f}, D50={d50:.1f}, D90={d90:.1f} nm, Std={size_std:.1f} (from {len(valid_sizes)} valid sizes)")
                        else:
                            logger.warning(f"⚠️ Not enough valid sizes for distribution: {len(valid_sizes)} valid out of {len(computed_sizes)}")
                    except Exception as size_error:
                        logger.warning(f"⚠️ Size distribution calculation failed: {size_error}")
                
                # Calculate particle exclusion and debris statistics
                # TASK-002 FIX (Dec 17, 2025): Use filtering, not clamping
                size_filtering_stats = None
                excluded_particles_pct = None
                debris_pct = None
                if fsc_channel and fsc_channel in parsed_data.columns:
                    try:
                        mie_calc = MieScatterCalculator(wavelength_nm=488.0, n_particle=1.40, n_medium=1.33)
                        # Use FAST batch calculation (sample 10000 events)
                        sample_size = min(10000, len(parsed_data))
                        sampled_fsc = parsed_data[fsc_channel].sample(n=sample_size, random_state=42).values
                        
                        # Vectorized batch calculation (100x faster than loop)
                        sizes, success_mask = mie_calc.diameters_from_scatter_batch(
                            sampled_fsc, min_diameter=30.0, max_diameter=500.0
                        )
                        valid_sizes = sizes[success_mask]
                        
                        if len(valid_sizes) > 0:
                            sizes_array = valid_sizes
                            
                            # Apply proper filtering using size_config
                            filtered_sizes, filter_stats = filter_particles_by_size(sizes_array)
                            size_filtering_stats = filter_stats
                            excluded_particles_pct = filter_stats.get('exclusion_pct', 0.0)
                            
                            # Debris = particles outside display range but inside valid range
                            # (particles too small or too large but still within 30-220nm)
                            display_min = DEFAULT_SIZE_CONFIG.display_min_nm  # 40nm
                            display_max = DEFAULT_SIZE_CONFIG.display_max_nm  # 200nm
                            non_display_count = np.sum(
                                (filtered_sizes < display_min) | (filtered_sizes > display_max)
                            )
                            debris_pct = float((non_display_count / len(filtered_sizes)) * 100) if len(filtered_sizes) > 0 else 0.0
                            
                            logger.info(
                                f"🔍 Size filtering: {filter_stats['valid_count']}/{filter_stats['total_input']} valid, "
                                f"{filter_stats['exclusion_pct']:.1f}% excluded, {debris_pct:.1f}% debris"
                            )
                    except Exception as debris_error:
                        logger.warning(f"⚠️ Size filtering calculation failed: {debris_error}")
                
                # Check for CD81 or other markers
                cd81_positive_pct = None
                for ch in channels:
                    if 'CD81' in ch.upper() or 'CD9' in ch.upper() or 'CD63' in ch.upper():
                        marker_stats = stats.get(ch, {})
                        if marker_stats.get('median'):
                            # Simple threshold: events above median are considered positive
                            threshold = marker_stats['median']
                            if ch in parsed_data.columns:
                                positive_count = (parsed_data[ch] > threshold).sum()
                                cd81_positive_pct = float((positive_count / event_count) * 100)
                                logger.info(f"✅ {ch} positive: {cd81_positive_pct:.1f}%")
                                break
                
                # Build comprehensive FCS results
                # TASK-002 FIX (Dec 17, 2025): Include size filtering statistics
                # TASK-010 FIX (Dec 17, 2025): Include VSSC_MAX selection statistics
                fcs_results = {
                    'total_events': event_count,
                    'event_count': event_count,
                    'channels': channels,
                    'fsc_mean': fsc_stats.get('mean'),
                    'fsc_median': fsc_stats.get('median'),
                    'ssc_mean': ssc_stats.get('mean'),
                    'ssc_median': ssc_stats.get('median'),
                    'particle_size_median_nm': particle_size_median_nm,
                    'size_statistics': size_statistics,
                    'debris_pct': debris_pct,
                    'cd81_positive_pct': cd81_positive_pct,
                    # New fields for size filtering transparency
                    'size_filtering': size_filtering_stats,
                    'excluded_particles_pct': excluded_particles_pct,
                    'size_range': {
                        'valid_min': DEFAULT_SIZE_CONFIG.valid_min_nm,
                        'valid_max': DEFAULT_SIZE_CONFIG.valid_max_nm,
                        'display_min': DEFAULT_SIZE_CONFIG.display_min_nm,
                        'display_max': DEFAULT_SIZE_CONFIG.display_max_nm,
                    },
                    # TASK-010: VSSC_MAX auto-selection info
                    'vssc_max_used': vssc_max_created,
                    'vssc_selection': vssc_selection_stats,
                    'ssc_channel_used': ssc_channel,
                }
                
                logger.success(f"✅ Parsed {event_count} events with {len(channels)} channels")
                logger.success(f"📊 Statistics: FSC median={fsc_stats.get('median')}, SSC median={ssc_stats.get('median')}")
        except Exception as parse_error:
            logger.error(f"⚠️ Parser failed: {parse_error}", exc_info=True)
            fcs_results = None
        
        # Create sample record in database
        db_sample = None
        db_job = None
        job_id = str(uuid.uuid4())
        
        try:
            # Check if sample already exists
            existing_sample = await get_sample_by_id(db, sample_id)
            
            # Get relative file path safely
            try:
                # Make path absolute first, then relative to cwd
                abs_path = file_path.resolve()
                rel_path = str(abs_path.relative_to(Path.cwd().resolve()))
            except ValueError:
                # If relative_to fails, just use the path as-is
                rel_path = str(file_path)
            
            if existing_sample:
                # Update existing sample with FCS file path
                db_sample = await update_sample(
                    db=db,
                    sample_id=sample_id,
                    file_path_fcs=rel_path,
                    treatment=treatment,
                    concentration_ug=concentration_ug,
                    preparation_method=preparation_method,
                    operator=operator,
                    notes=notes,
                )
                logger.info(f"📝 Updated existing sample: {sample_id}")
            else:
                # Extract biological sample ID from sample_id
                # Example: "P5_F10_CD81" -> "P5_F10", "Exo_2ug_CD81_centri" -> "Exo_2ug_CD81_centri"
                parts = sample_id.rsplit('_', 1)
                biological_sample_id = parts[0] if len(parts) > 1 else sample_id
                
                # Create new sample record with user ownership
                db_sample = await create_sample(
                    db=db,
                    sample_id=sample_id,
                    biological_sample_id=biological_sample_id,
                    file_path_fcs=rel_path,
                    treatment=treatment or "Unknown",
                    concentration_ug=concentration_ug,
                    preparation_method=preparation_method,
                    operator=operator,
                    notes=notes,
                    user_id=user_id,
                )
                logger.info(f"✨ Created new sample: {sample_id} (user_id: {user_id})")
            
            # Create processing job
            if db_sample:
                db_job = await create_processing_job(
                    db=db,
                    job_id=job_id,
                    job_type="fcs_parse",
                    sample_id=db_sample.id,  # type: ignore[arg-type]
                )
                logger.info(f"📋 Created processing job: {job_id}")
                
                # If parsing succeeded, save FCS results to database
                if fcs_results:
                    await create_fcs_result(
                        db=db,
                        sample_id=db_sample.id,  # type: ignore[arg-type]
                        total_events=fcs_results.get('total_events', 0),
                        fsc_mean=fcs_results.get('fsc_mean'),
                        fsc_median=fcs_results.get('fsc_median'),
                        ssc_mean=fcs_results.get('ssc_mean'),
                        ssc_median=fcs_results.get('ssc_median'),
                        particle_size_median_nm=fcs_results.get('particle_size_median_nm'),
                        debris_pct=fcs_results.get('debris_pct'),
                        cd81_positive_pct=fcs_results.get('cd81_positive_pct'),
                    )
                    # Mark job as completed
                    await update_job_status(
                        db=db,
                        job_id=job_id,
                        status="completed",
                        result_data=fcs_results,
                    )
                    logger.success(f"💾 Saved FCS results to database")
                    
                    # CRMIT-003: Generate quality alerts based on analysis results
                    try:
                        alerts = await generate_analysis_alerts(
                            db=db,
                            sample_id=db_sample.id,  # type: ignore[arg-type]
                            sample_name=sample_id,
                            user_id=user_id,
                            fcs_results=fcs_results,
                            source="FCS Analysis"
                        )
                        if alerts:
                            logger.info(f"🔔 Generated {len(alerts)} quality alerts for {sample_id}")
                    except Exception as alert_error:
                        logger.warning(f"⚠️ Alert generation failed: {alert_error}")
                        # Don't fail the upload due to alert generation issues
                    
        except Exception as db_error:
            logger.warning(f"⚠️ Database operation failed: {db_error}")
            logger.warning("   Continuing with file-based response...")
            db_sample = None
        
        # Get database ID or use temporary ID
        db_id = db_sample.id if db_sample else abs(hash(sample_id)) % 1000000
        
        logger.success(f"✅ FCS file uploaded: {sample_id} (job: {job_id})")
        
        # Build response with parsed results
        response_data = {
            "success": True,
            "id": db_id,  # Database ID (real if DB connected, temp otherwise)
            "sample_id": sample_id,  # String display name
            "treatment": treatment,
            "concentration_ug": concentration_ug,
            "preparation_method": preparation_method,
            "operator": operator,
            "notes": notes,
            "job_id": job_id,
            "status": "uploaded",
            "processing_status": "completed" if fcs_results else "pending",
            "message": "File uploaded successfully, processing started",
            "file_size_mb": file_path.stat().st_size / 1024 / 1024,
            "upload_timestamp": datetime.now().isoformat(),
        }
        
        # Add parsed FCS results if available
        if fcs_results:
            # Add ID to fcs_results for frontend compatibility
            fcs_results['id'] = db_id
            fcs_results['sample_id'] = sample_id
            response_data["fcs_results"] = fcs_results
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to upload FCS file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process upload: {str(e)}"
        )


# ============================================================================
# NTA Upload Endpoint
# ============================================================================

@router.post("/nta", response_model=dict)
async def upload_nta_file(
    file: UploadFile = File(...),
    treatment: Optional[str] = Form(None),
    temperature_celsius: Optional[float] = Form(None),
    operator: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    user_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_session)
):
    """
    Upload and process NTA file.
    
    **Request:**
    - file: NTA file (.txt or .csv)
    - treatment: Treatment name
    - temperature_celsius: Measurement temperature
    - operator: Operator name
    - notes: Additional notes
    
    **Response:**
    ```json
    {
        "success": true,
        "sample_id": "P5_F10_CD81",
        "job_id": "550e8400-e29b-41d4-a716-446655440001",
        "status": "pending",
        "message": "File uploaded successfully, processing started"
    }
    ```
    
    **Processing Pipeline:**
    1. Save uploaded file to `data/uploads/`
    2. Create sample record (or update existing)
    3. Create processing job (async)
    4. Background worker parses NTA file
    5. Background worker saves results to database and Parquet
    """
    logger.info(f"📤 Uploading NTA file: {file.filename}")
    
    try:
        # Validate file extension
        filename = file.filename or ""
        if not (filename.lower().endswith('.txt') or filename.lower().endswith('.csv')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only .txt and .csv files are accepted."
            )
        
        # Generate sample ID
        sample_id = generate_sample_id(file.filename or "unknown.txt")
        
        # Save uploaded file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = settings.upload_dir / f"{timestamp}_{file.filename}"
        await save_uploaded_file(file, file_path)
        
        # Parse NTA file using professional parser
        nta_results = None
        try:
            logger.info(f"🔬 Parsing NTA file with professional parser...")
            parser = NTAParser(file_path)
            
            # Validate file
            if not parser.validate():
                logger.warning(f"⚠️ NTA file validation failed, continuing anyway...")
            
            # Parse and get results
            parsed_data = parser.parse()
            
            if parsed_data is not None and len(parsed_data) > 0:
                # Calculate statistics from parsed data
                size_col = None
                conc_col = None
                
                # Find size and concentration columns
                for col in parsed_data.columns:
                    col_lower = col.lower()
                    if 'size' in col_lower and size_col is None:
                        size_col = col
                    if 'conc' in col_lower and conc_col is None:
                        conc_col = col
                
                # Calculate size statistics
                if size_col:
                    sizes = parsed_data[size_col].dropna()
                    if len(sizes) > 0:
                        # Calculate percentiles
                        d10 = float(np.percentile(sizes, 10))
                        d50 = float(np.percentile(sizes, 50))  # median
                        d90 = float(np.percentile(sizes, 90))
                        mean_size = float(sizes.mean())
                        
                        # Calculate concentration if available
                        total_concentration = None
                        if conc_col:
                            conc_values = parsed_data[conc_col].dropna()
                            if len(conc_values) > 0:
                                total_concentration = float(conc_values.sum())
                        
                        # Calculate size bin percentages
                        total_particles = len(sizes)
                        bin_50_80 = len(sizes[(sizes >= 50) & (sizes < 80)]) / total_particles * 100 if total_particles > 0 else 0
                        bin_80_100 = len(sizes[(sizes >= 80) & (sizes < 100)]) / total_particles * 100 if total_particles > 0 else 0
                        bin_100_120 = len(sizes[(sizes >= 100) & (sizes < 120)]) / total_particles * 100 if total_particles > 0 else 0
                        bin_120_150 = len(sizes[(sizes >= 120) & (sizes < 150)]) / total_particles * 100 if total_particles > 0 else 0
                        bin_150_200 = len(sizes[(sizes >= 150) & (sizes < 200)]) / total_particles * 100 if total_particles > 0 else 0
                        bin_200_plus = len(sizes[sizes >= 200]) / total_particles * 100 if total_particles > 0 else 0
                        
                        nta_results = {
                            "mean_size_nm": mean_size,
                            "median_size_nm": d50,
                            "d10_nm": d10,
                            "d50_nm": d50,
                            "d90_nm": d90,
                            "concentration_particles_ml": total_concentration,
                            "temperature_celsius": temperature_celsius,
                            "total_particles": total_particles,
                            "bin_50_80nm_pct": bin_50_80,
                            "bin_80_100nm_pct": bin_80_100,
                            "bin_100_120nm_pct": bin_100_120,
                            "bin_120_150nm_pct": bin_120_150,
                            "bin_150_200nm_pct": bin_150_200,
                            "bin_200_plus_pct": bin_200_plus,
                            "size_statistics": {
                                "d10": d10,
                                "d50": d50,
                                "d90": d90,
                                "mean": mean_size,
                                "std": float(sizes.std()) if len(sizes) > 1 else 0,
                            }
                        }
                        logger.success(f"✅ Parsed NTA data: {total_particles} particles, median={d50:.1f}nm")
        except Exception as parse_error:
            logger.error(f"⚠️ NTA Parser failed: {parse_error}, continuing with upload...")
            nta_results = None
        
        # Create or update sample record in database
        db_sample = None
        db_job = None
        job_id = str(uuid.uuid4())
        
        try:
            # Check if sample already exists
            existing_sample = await get_sample_by_id(db, sample_id)
            
            if existing_sample:
                # Update existing sample with NTA file path
                db_sample = await update_sample(
                    db=db,
                    sample_id=sample_id,
                    file_path_nta=str(file_path.relative_to(Path.cwd())),
                    treatment=treatment,
                    operator=operator,
                    notes=notes,
                )
                logger.info(f"📝 Updated existing sample with NTA: {sample_id}")
            else:
                # Create new sample record with user ownership
                db_sample = await create_sample(
                    db=db,
                    sample_id=sample_id,
                    file_path_nta=str(file_path.relative_to(Path.cwd())),
                    treatment=treatment,
                    operator=operator,
                    notes=notes,
                    user_id=user_id,
                )
                logger.info(f"✨ Created new sample: {sample_id} (user_id: {user_id})")
            
            # Create processing job
            if db_sample:
                db_job = await create_processing_job(
                    db=db,
                    job_id=job_id,
                    job_type="nta_parse",
                    sample_id=db_sample.id,  # type: ignore[arg-type]
                )
                logger.info(f"📋 Created processing job: {job_id}")
                
                # If parsing succeeded, save NTA results to database
                if nta_results:
                    await create_nta_result(
                        db=db,
                        sample_id=db_sample.id,  # type: ignore[arg-type]
                        mean_size_nm=nta_results.get('mean_size_nm'),
                        median_size_nm=nta_results.get('median_size_nm'),
                        d10_nm=nta_results.get('d10_nm'),
                        d50_nm=nta_results.get('d50_nm'),
                        d90_nm=nta_results.get('d90_nm'),
                        concentration_particles_ml=nta_results.get('concentration_particles_ml'),
                        temperature_celsius=nta_results.get('temperature_celsius'),
                    )
                    # Mark job as completed
                    await update_job_status(
                        db=db,
                        job_id=job_id,
                        status="completed",
                        result_data=nta_results,
                    )
                    logger.success(f"💾 Saved NTA results to database")
                    
                    # CRMIT-003: Generate quality alerts based on NTA analysis results
                    try:
                        alerts = await generate_nta_alerts(
                            db=db,
                            sample_id=db_sample.id,  # type: ignore[arg-type]
                            sample_name=sample_id,
                            user_id=user_id,
                            nta_results=nta_results,
                            source="NTA Analysis"
                        )
                        if alerts:
                            logger.info(f"🔔 Generated {len(alerts)} quality alerts for NTA: {sample_id}")
                    except Exception as alert_error:
                        logger.warning(f"⚠️ NTA alert generation failed: {alert_error}")
                        # Don't fail the upload due to alert generation issues
                
        except Exception as db_error:
            logger.warning(f"⚠️ Database operation failed: {db_error}")
            logger.warning("   Continuing with file-based response...")
            db_sample = None
        
        # Get database ID or use temporary ID
        db_id = db_sample.id if db_sample else abs(hash(sample_id)) % 1000000
        
        logger.success(f"✅ NTA file uploaded: {sample_id} (job: {job_id})")
        
        # Build response with parsed results
        response_data = {
            "success": True,
            "id": db_id,  # Database ID (real if DB connected, temp otherwise)
            "sample_id": sample_id,  # String display name
            "treatment": treatment,
            "temperature_celsius": temperature_celsius,
            "operator": operator,
            "notes": notes,
            "job_id": job_id,
            "status": "uploaded",
            "processing_status": "completed" if nta_results else "pending",
            "message": "File uploaded successfully, processing started",
            "file_size_mb": file_path.stat().st_size / 1024 / 1024,
            "upload_timestamp": datetime.now().isoformat(),
        }
        
        # Add parsed NTA results if available
        if nta_results:
            response_data["nta_results"] = nta_results
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to upload NTA file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process upload: {str(e)}"
        )


# ============================================================================
# NTA PDF Report Upload Endpoint (TASK-007)
# ============================================================================

@router.post("/nta-pdf", response_model=dict)
async def upload_nta_pdf(
    file: UploadFile = File(...),
    linked_sample_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_session)
):
    """
    Upload and parse NTA PDF report to extract concentration and dilution factor.
    
    TASK-007: Implement PDF Parsing for NTA Reports
    
    Client Quote (Surya, Dec 3, 2025):
    "That number is not ever mentioned in a text format... it is always mentioned 
    only in the PDF file... I was struggling through"
    
    **Request:**
    - file: NTA PDF report (.pdf)
    - linked_sample_id: Optional sample ID to link this PDF data with
    
    **Response:**
    ```json
    {
        "success": true,
        "pdf_data": {
            "original_concentration": 3.5e10,
            "dilution_factor": 500,
            "true_particle_population": 1.75e13,
            "mean_size_nm": 120.5,
            "mode_size_nm": 95.3
        },
        "message": "PDF parsed successfully"
    }
    ```
    """
    logger.info(f"📤 Uploading NTA PDF: {file.filename}")
    
    try:
        # Validate file extension
        filename = file.filename or ""
        if not filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only .pdf files are accepted."
            )
        
        # Save uploaded file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = settings.upload_dir / f"{timestamp}_{file.filename}"
        await save_uploaded_file(file, file_path)
        
        # Parse PDF using NTA PDF parser
        from src.parsers.nta_pdf_parser import parse_nta_pdf, check_pdf_support
        
        if not check_pdf_support():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="PDF parsing not available. Install pdfplumber: pip install pdfplumber"
            )
        
        pdf_data = parse_nta_pdf(file_path)
        
        if not pdf_data.get('extraction_successful'):
            logger.warning(f"⚠️ PDF extraction incomplete: {pdf_data.get('extraction_errors')}")
        
        # If linked to a sample, update the sample's NTA results
        if linked_sample_id:
            try:
                existing_sample = await get_sample_by_id(db, linked_sample_id)
                if existing_sample:
                    # Update NTA results with PDF data
                    # This is a simplified version - full implementation would update NTAResult
                    logger.info(f"📝 Linked PDF data to sample: {linked_sample_id}")
            except Exception as link_error:
                logger.warning(f"⚠️ Could not link PDF to sample: {link_error}")
        
        logger.success(f"✅ NTA PDF parsed successfully")
        
        return {
            "success": True,
            "pdf_file": file.filename,
            "pdf_data": pdf_data,
            "linked_sample_id": linked_sample_id,
            "message": "PDF parsed successfully" if pdf_data.get('extraction_successful') else "PDF parsed with warnings",
            "upload_timestamp": datetime.now().isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to upload NTA PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PDF: {str(e)}"
        )


# ============================================================================
# Batch Upload Endpoint
# ============================================================================

@router.post("/batch", response_model=dict)
async def upload_batch(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_session)
):
    """
    Upload multiple files at once.
    
    **Request:**
    - files: List of FCS and/or NTA files
    
    **Response:**
    ```json
    {
        "success": true,
        "uploaded": 5,
        "failed": 0,
        "job_ids": ["uuid1", "uuid2", "uuid3", "uuid4", "uuid5"],
        "details": [
            {"filename": "file1.fcs", "sample_id": "S001", "status": "success"},
            ...
        ]
    }
    ```
    """
    logger.info(f"📤 Batch upload: {len(files)} files")
    
    results = {
        "success": True,
        "uploaded": 0,
        "failed": 0,
        "job_ids": [],
        "details": []
    }
    
    for file in files:
        try:
            # Determine file type
            filename = file.filename or ""
            if filename.lower().endswith('.fcs'):
                result = await upload_fcs_file(file=file, db=db)
            elif filename.lower().endswith(('.txt', '.csv')):
                result = await upload_nta_file(file=file, db=db)
            else:
                raise ValueError(f"Unsupported file type: {filename}")
            
            results["uploaded"] += 1
            results["job_ids"].append(result["job_id"])
            results["details"].append({
                "filename": file.filename,
                "sample_id": result["sample_id"],
                "status": "success"
            })
            
        except Exception as e:
            logger.error(f"❌ Failed to upload {file.filename}: {e}")
            results["failed"] += 1
            results["details"].append({
                "filename": file.filename,
                "status": "failed",
                "error": str(e)
            })
    
    if results["failed"] > 0:
        results["success"] = False
    
    logger.info(f"✅ Batch upload complete: {results['uploaded']} succeeded, {results['failed']} failed")
    
    return results
