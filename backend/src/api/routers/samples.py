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

from typing import Optional, List, Dict, Any, Tuple  # noqa: F401
from pathlib import Path
import json
import re
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore[import-not-found]
from sqlalchemy import select, func  # type: ignore[import-not-found]
from loguru import logger

from src.database.connection import get_session
from src.database.models import Sample, FCSResult, NTAResult, QCReport, ProcessingJob  # type: ignore[import-not-found]
from src.api.auth_middleware import optional_auth

router = APIRouter()


# ============================================================================
# NTA File Finder Helper
# ============================================================================

def _find_nta_file_by_sample_id(sample_id: str) -> Optional[str]:
    """
    Find an NTA file in the uploads directory by sample_id.
    
    When a sample is not in the database (e.g., DB insert failed during upload),
    we can still find the file on disk by matching the sample_id in the filename.
    
    Files are stored as: {timestamp}_{original_filename}.txt
    e.g., 20260224_145033_20251217_0005_PC3_100kDa_F5_size_488.txt
    
    Returns:
        File path string if found, None otherwise
    """
    from src.api.config import get_settings
    settings = get_settings()
    
    upload_dir = settings.upload_dir
    if not upload_dir.exists():
        return None
    
    sample_id_lower = sample_id.lower()
    
    # Search for .txt and .csv files matching the sample_id
    matches = []
    for ext in ('*.txt', '*.csv'):
        for f in upload_dir.glob(ext):
            # File is stored as {timestamp}_{original_name}.ext
            # The sample_id is derived from the original name (stem)
            stem = f.stem.lower()
            # Strip the leading timestamp (YYYYMMDD_HHMMSS_)
            parts = stem.split('_', 2)
            if len(parts) >= 3:
                # Remove timestamp prefix, check if remaining matches sample_id
                remainder = parts[2]
                if remainder == sample_id_lower:
                    matches.append(f)
            # Also check if sample_id appears anywhere in the filename
            if sample_id_lower in stem and f not in matches:
                matches.append(f)
    
    if matches:
        # Return the most recently modified file
        matches.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return str(matches[0])
    
    return None


# ============================================================================
# Multi-Solution Mie Helper Functions
# ============================================================================

def detect_multi_solution_channels(channels: List[str]) -> Dict[str, Optional[str]]:
    """
    Detect VSSC (Violet SSC 405nm) and BSSC (Blue SSC 488nm) channels for multi-solution Mie.
    
    Returns dict with keys: 'vssc_channel', 'bssc_channel', 'can_use_multi_solution'
    """
    vssc_channel = None
    bssc_channel = None
    
    for ch in channels:
        ch_upper = ch.upper()
        # Detect VSSC (Violet SSC at 405nm) - prefer -H over -A
        if 'VSSC' in ch_upper and '-H' in ch_upper:
            if vssc_channel is None or 'VSSC1' in ch_upper:  # Prefer VSSC1-H
                vssc_channel = ch
        # Detect BSSC (Blue SSC at 488nm)
        if 'BSSC' in ch_upper and '-H' in ch_upper:
            bssc_channel = ch
    
    can_use_multi_solution = vssc_channel is not None and bssc_channel is not None
    
    return {
        'vssc_channel': vssc_channel,
        'bssc_channel': bssc_channel,
        'can_use_multi_solution': can_use_multi_solution
    }


METADATA_OVERRIDE_BEGIN = "[[METADATA_OVERRIDE_JSON]]"
METADATA_OVERRIDE_END = "[[/METADATA_OVERRIDE_JSON]]"


def _extract_metadata_overrides_from_notes(notes: Optional[str]) -> Dict[str, Any]:
    """Extract JSON metadata override block from sample notes."""
    if not notes:
        return {}

    start = notes.find(METADATA_OVERRIDE_BEGIN)
    end = notes.find(METADATA_OVERRIDE_END)
    if start == -1 or end == -1 or end <= start:
        return {}

    payload = notes[start + len(METADATA_OVERRIDE_BEGIN):end].strip()
    if not payload:
        return {}

    try:
        decoded = json.loads(payload)
        return decoded if isinstance(decoded, dict) else {}
    except Exception:
        logger.warning("Failed to parse metadata override JSON block in sample notes")
        return {}


def _upsert_metadata_overrides_in_notes(notes: Optional[str], overrides: Dict[str, Any]) -> str:
    """Insert or replace metadata override JSON block inside sample notes."""
    base_notes = notes or ""
    block = (
        f"{METADATA_OVERRIDE_BEGIN}\n"
        f"{json.dumps(overrides, ensure_ascii=True, indent=2)}\n"
        f"{METADATA_OVERRIDE_END}"
    )

    start = base_notes.find(METADATA_OVERRIDE_BEGIN)
    end = base_notes.find(METADATA_OVERRIDE_END)
    if start != -1 and end != -1 and end > start:
        tail = end + len(METADATA_OVERRIDE_END)
        return f"{base_notes[:start].rstrip()}\n\n{block}\n{base_notes[tail:].lstrip()}".strip()

    if base_notes.strip():
        return f"{base_notes.rstrip()}\n\n{block}"
    return block


def _find_fcs_sidecar_xml(fcs_path: str) -> Optional[Path]:
    """Find likely XML sidecar files near the FCS file."""
    fcs_file = Path(fcs_path)
    parent = fcs_file.parent
    stem = fcs_file.stem
    candidates = [
        parent / f"{stem}.xml",
        parent / f"{stem}_ExpSummaryForAPI.xml",
        parent / "ExpSummaryForAPI.xml",
        parent / "ExpSummary.xml",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _extract_sidecar_metadata(xml_path: Path) -> Dict[str, Any]:
    """Extract instrument metadata from sidecar XML as best-effort parsing."""
    from xml.etree import ElementTree

    result: Dict[str, Any] = {
        "laser_wavelength_nm": None,
        "instrument_model": None,
    }
    try:
        content = xml_path.read_text(encoding="utf-8", errors="ignore")
        root = ElementTree.fromstring(content)
        text_blob = " ".join([t.strip() for t in root.itertext() if t and t.strip()])

        # Try to infer laser wavelength from full XML text.
        laser_match = re.search(r"(405|488|561|640)\s*nm", text_blob, flags=re.IGNORECASE)
        if laser_match:
            result["laser_wavelength_nm"] = int(laser_match.group(1))

        # Try common instrument model indicators.
        model_match = re.search(
            r"(CytoFLEX\s*[A-Za-z0-9\-]*|Navios\s*[A-Za-z0-9\-]*|FACS\s*[A-Za-z0-9\-]*)",
            text_blob,
            flags=re.IGNORECASE,
        )
        if model_match:
            result["instrument_model"] = model_match.group(1).strip()
    except Exception:
        logger.warning(f"Could not parse sidecar XML metadata from {xml_path}")

    return result


def _extract_laser_wavelength_from_fcs(metadata: Dict[str, Any], channel_names: List[str]) -> Optional[int]:
    """Infer laser wavelength from FCS metadata fields and channel naming conventions."""
    # 1) Direct metadata fields
    text_candidates = [
        str(metadata.get("cytometer", "")),
        str(metadata.get("specimen", "")),
        str(metadata.get("instrument", "")),
    ]
    for text in text_candidates:
        m = re.search(r"(405|488|561|640)\s*nm", text, flags=re.IGNORECASE)
        if m:
            return int(m.group(1))

    # 2) Channel heuristics
    upper_channels = [c.upper() for c in channel_names]
    if any("VSSC" in c or "VFSC" in c or "VIOLET" in c for c in upper_channels):
        return 405
    if any("BSSC" in c or "BFSC" in c or "BLUE" in c for c in upper_channels):
        return 488
    return None


def _resolve_sample_metadata(
    fcs_metadata: Dict[str, Any],
    channel_names: List[str],
    sidecar_data: Dict[str, Any],
    overrides: Dict[str, Any],
    dilution_factor: Optional[int],
) -> Tuple[Dict[str, Any], Dict[str, str], List[str], float]:
    """Resolve metadata values and provenance using deterministic priority."""
    resolved: Dict[str, Any] = {}
    provenance: Dict[str, str] = {}

    # laser_wavelength_nm: manual override > FCS extraction > sidecar > unknown
    override_laser = overrides.get("laser_wavelength_nm")
    if override_laser is not None:
        resolved["laser_wavelength_nm"] = int(override_laser)
        provenance["laser_wavelength_nm"] = "manual"
    else:
        fcs_laser = _extract_laser_wavelength_from_fcs(fcs_metadata, channel_names)
        if fcs_laser is not None:
            resolved["laser_wavelength_nm"] = fcs_laser
            provenance["laser_wavelength_nm"] = "fcs_header"
        elif sidecar_data.get("laser_wavelength_nm") is not None:
            resolved["laser_wavelength_nm"] = int(sidecar_data["laser_wavelength_nm"])
            provenance["laser_wavelength_nm"] = "sidecar_xml"
        else:
            resolved["laser_wavelength_nm"] = None
            provenance["laser_wavelength_nm"] = "missing"

    # instrument_model: manual override > FCS cytometer > sidecar > unknown
    override_instrument = overrides.get("instrument_model")
    if override_instrument:
        resolved["instrument_model"] = str(override_instrument)
        provenance["instrument_model"] = "manual"
    else:
        cytometer = fcs_metadata.get("cytometer")
        if cytometer and cytometer != "Unknown":
            resolved["instrument_model"] = str(cytometer)
            provenance["instrument_model"] = "fcs_header"
        elif sidecar_data.get("instrument_model"):
            resolved["instrument_model"] = str(sidecar_data["instrument_model"])
            provenance["instrument_model"] = "sidecar_xml"
        else:
            resolved["instrument_model"] = None
            provenance["instrument_model"] = "missing"

    # dilution_factor: manual override > experimental_conditions > unknown
    override_dilution = overrides.get("dilution_factor")
    if override_dilution is not None:
        resolved["dilution_factor"] = int(override_dilution)
        provenance["dilution_factor"] = "manual"
    elif dilution_factor is not None and dilution_factor > 0:
        resolved["dilution_factor"] = int(dilution_factor)
        provenance["dilution_factor"] = "experimental_conditions"
    else:
        resolved["dilution_factor"] = None
        provenance["dilution_factor"] = "missing"

    required_fields = ["laser_wavelength_nm", "dilution_factor"]
    missing_required = [field for field in required_fields if resolved.get(field) in (None, "")]
    completeness_score = round((len(required_fields) - len(missing_required)) / len(required_fields), 2)

    return resolved, provenance, missing_required, completeness_score


def _diagnose_multi_solution_event(
    calc: Any,
    ssc_blue_value: float,
    ssc_violet_value: float,
    tolerance_pct: float,
    use_violet_primary: bool,
) -> Dict[str, Any]:
    """Compute multi-solution diagnostics for a single event."""
    sigma_violet = float(calc._au_to_sigma(np.array([ssc_violet_value], dtype=float), 405.0)[0])
    sigma_blue = float(calc._au_to_sigma(np.array([ssc_blue_value], dtype=float), 488.0)[0])

    primary_sigma = sigma_violet if use_violet_primary else sigma_blue
    primary_wavelength = 405.0 if use_violet_primary else 488.0
    primary_lut = calc.lut_ssc_violet if use_violet_primary else calc.lut_ssc_blue

    solutions = calc.find_all_solutions(primary_sigma, wavelength_nm=primary_wavelength, tolerance_pct=tolerance_pct)

    if sigma_blue > 0:
        measured_ratio = sigma_violet / sigma_blue
    else:
        measured_ratio = 1.0

    candidates = []
    for size in solutions:
        idx = int(abs(calc.lut_diameters - size).argmin())
        ratio_theoretical = float(calc.lut_ratio[idx])
        ratio_error = abs(ratio_theoretical - measured_ratio)
        primary_error = abs(float(primary_lut[idx]) - primary_sigma) / max(abs(primary_sigma), 1e-9)
        weighted_score = 0.7 * ratio_error + 0.3 * primary_error
        candidates.append({
            "diameter_nm": float(size),
            "ratio_theoretical": ratio_theoretical,
            "cross_channel_error": float(ratio_error),
            "calibration_fit_error": float(primary_error),
            "weighted_score": float(weighted_score),
        })

    candidates = sorted(candidates, key=lambda c: c["weighted_score"])
    if not candidates:
        return {
            "num_solutions": 0,
            "selected_solution_nm": None,
            "candidate_solutions_nm": [],
            "candidates": [],
            "ambiguity_score": None,
            "selection_reason": "no_valid_solution",
            "measured_ratio": float(measured_ratio),
            "sigma_violet": sigma_violet,
            "sigma_blue": sigma_blue,
        }

    selected = candidates[0]
    if len(candidates) > 1:
        gap = candidates[1]["weighted_score"] - candidates[0]["weighted_score"]
        ambiguity_score = float(max(0.0, min(1.0, 1.0 / (1.0 + (gap * 20.0)))))
    else:
        ambiguity_score = 0.0

    return {
        "num_solutions": len(solutions),
        "selected_solution_nm": float(selected["diameter_nm"]),
        "candidate_solutions_nm": [float(c["diameter_nm"]) for c in candidates],
        "candidates": candidates,
        "ambiguity_score": ambiguity_score,
        "selection_reason": "best_cross_channel_consistency",
        "measured_ratio": float(measured_ratio),
        "sigma_violet": sigma_violet,
        "sigma_blue": sigma_blue,
    }


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
    user_id: Optional[int] = Query(None, description="Filter by user ID (for user-specific samples)"),
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
        if user_id is not None:
            query = query.where(Sample.user_id == user_id)
        if treatment:
            query = query.where(Sample.treatment == treatment)
        if qc_status:
            query = query.where(Sample.qc_status == qc_status)
        if processing_status:
            query = query.where(Sample.processing_status == processing_status)
        
        # Get total count
        count_query = select(func.count()).select_from(Sample)
        if user_id is not None:
            count_query = count_query.where(Sample.user_id == user_id)
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
            overrides = _extract_metadata_overrides_from_notes(sample.notes)
            samples_data.append({
                "id": sample.id,
                "sample_id": sample.sample_id,
                "biological_sample_id": sample.biological_sample_id,
                "treatment": sample.treatment,
                "dye": overrides.get("dye"),
                "qc_status": sample.qc_status,
                "processing_status": sample.processing_status,
                "upload_timestamp": upload_ts.isoformat() if upload_ts else None,
                "has_fcs": sample.file_path_fcs is not None,
                "has_nta": sample.file_path_nta is not None,
                "has_tem": sample.file_path_tem is not None,
                "files": {
                    "fcs": sample.file_path_fcs,
                    "nta": sample.file_path_nta,
                    "tem": getattr(sample, 'file_path_tem', None),
                },
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
# Channel Configuration Endpoints
# (Must be defined BEFORE /{sample_id} to avoid FastAPI matching "channel-config" as a sample_id)
# ============================================================================

@router.get("/channel-config", response_model=dict)
async def get_channel_configuration():
    """
    Get current channel configuration for FCS analysis.
    
    Returns the active instrument settings and all available instrument configurations.
    """
    try:
        from src.utils.channel_config import get_channel_config  # type: ignore[import-not-found]
        
        config = get_channel_config()
        
        return {
            "success": True,
            "active_instrument": config.active_instrument,
            "instruments": list(config.list_instruments()),
            "fsc_channels": config.get_fsc_channel_names(),
            "ssc_channels": config.get_ssc_channel_names(),
            "preferred": {
                "for_size_analysis": config.get_preferred_channels("for_size_analysis"),
                "for_scatter_plot": config.get_preferred_channels("for_scatter_plot")
            }
        }
    except Exception as e:
        logger.exception(f"❌ Failed to get channel config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get channel configuration: {str(e)}"
        )


@router.put("/channel-config", response_model=dict)
async def update_channel_configuration(
    instrument: Optional[str] = Query(None, description="Instrument name to activate"),
    fsc_channel: Optional[str] = Query(None, description="FSC channel name to add/set as preferred"),
    ssc_channel: Optional[str] = Query(None, description="SSC channel name to add/set as preferred"),
    save: bool = Query(True, description="Save configuration to file")
):
    """
    Update channel configuration for FCS analysis.
    
    **Parameters:**
    - instrument: Activate a specific instrument configuration
    - fsc_channel: Set the preferred FSC channel
    - ssc_channel: Set the preferred SSC channel
    - save: Whether to persist changes to file (default: True)
    
    **Example:**
    ```
    PUT /samples/channel-config?fsc_channel=Channel_5&ssc_channel=Channel_6&save=true
    ```
    """
    try:
        from src.utils.channel_config import get_channel_config  # type: ignore[import-not-found]
        
        config = get_channel_config()
        
        # Activate specific instrument if provided
        if instrument:
            if not config.set_active_instrument(instrument):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Instrument '{instrument}' not found. Available: {config.list_instruments()}"
                )
        
        # Add custom channel mapping if both FSC and SSC provided
        if fsc_channel and ssc_channel:
            config.add_custom_channel_mapping(fsc_channel, ssc_channel)
            logger.info(f"✓ Updated channel mapping: FSC={fsc_channel}, SSC={ssc_channel}")
        
        # Save configuration if requested
        if save:
            config.save_config()
        
        return {
            "success": True,
            "message": "Channel configuration updated",
            "active_instrument": config.active_instrument,
            "preferred_fsc": config.get_preferred_channels()[0],
            "preferred_ssc": config.get_preferred_channels()[1],
            "saved": save
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to update channel config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update channel configuration: {str(e)}"
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
        overrides = _extract_metadata_overrides_from_notes(sample.notes)
        
        return {
            "id": sample.id,
            "sample_id": sample.sample_id,
            "biological_sample_id": sample.biological_sample_id,
            "treatment": sample.treatment,
            "dye": overrides.get("dye"),
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
            
            # Calculate size distribution histogram from parquet if available
            size_distribution_histogram = None
            size_stats_computed = None
            parquet_path = getattr(fcs, 'parquet_file_path', None)
            
            if parquet_path:
                try:
                    import numpy as np
                    import pandas as pd
                    from pathlib import Path
                    
                    parquet_file = Path(parquet_path)
                    if parquet_file.exists():
                        df = pd.read_parquet(parquet_file)
                        # Look for pre-calculated diameter column
                        size_col = None
                        for col_name in ['diameter_nm', 'particle_size_nm', 'size_nm']:
                            if col_name in df.columns:
                                size_col = col_name
                                break
                        
                        if size_col:
                            sizes = df[size_col].dropna().values
                            valid = sizes[(sizes > 0) & (sizes < 2000)]
                            
                            if len(valid) > 0:
                                # Create 50-bin histogram from 20-500nm
                                bins = np.linspace(20, 500, 51)
                                centers = (bins[:-1] + bins[1:]) / 2
                                hist, _ = np.histogram(valid, bins=bins)
                                
                                size_distribution_histogram = [
                                    {"size": round(float(c), 1), "count": int(h)}
                                    for c, h in zip(centers, hist) if h > 0
                                ]
                                
                                size_stats_computed = {
                                    "d10": round(float(np.percentile(valid, 10)), 2),
                                    "d50": round(float(np.percentile(valid, 50)), 2),
                                    "d90": round(float(np.percentile(valid, 90)), 2),
                                    "mean": round(float(np.mean(valid)), 2),
                                    "std": round(float(np.std(valid)), 2),
                                }
                except Exception as hist_err:
                    logger.debug(f"Could not compute FCS histogram: {hist_err}")
            
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
                "size_distribution": size_distribution_histogram,
                "size_statistics": size_stats_computed,
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
    current_user: dict | None = Depends(optional_auth),
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
        # Log auth context
        user_info = f"user={current_user.get('sub', 'unknown')}" if current_user else "unauthenticated"
        logger.info(f"🗑️  Delete sample {sample_id} requested by {user_info}")

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
    fsc_channel: Optional[str] = Query(None, description="FSC channel name override (e.g., 'Channel_3')"),
    ssc_channel: Optional[str] = Query(None, description="SSC channel name override (e.g., 'Channel_4')"),
    wavelength_nm: float = Query(405.0, ge=200, le=800, description="Laser wavelength for Mie calculations"),
    n_particle: float = Query(1.37, ge=1.0, le=2.0, description="Particle refractive index"),
    n_medium: float = Query(1.33, ge=1.0, le=2.0, description="Medium refractive index"),
    db: AsyncSession = Depends(get_session)
):
    """Get FSC/SSC scatter plot data for a sample (cached for 2 minutes)."""
    # Check cache first — scatter data is expensive (FCS parse + Mie calculations)
    from src.api.cache import scatter_cache, make_cache_key
    cache_key = f"scatter:{sample_id}:{make_cache_key(max_points, fsc_channel, ssc_channel, wavelength_nm, n_particle, n_medium)}"
    cached = scatter_cache.get(cache_key)
    if cached is not None:
        logger.debug(f"📊 Cache HIT for scatter data: {sample_id}")
        return cached
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
        
        # Parse FCS file to get scatter data (cached)
        from src.utils.fcs_cache import get_cached_fcs_data  # type: ignore[import-not-found]
        from src.utils.channel_config import get_channel_config  # type: ignore[import-not-found]
        import pandas as pd
        import numpy as np
        
        logger.info(f"📊 Loading scatter data for sample: {sample_id}")
        
        parsed_data, channels = get_cached_fcs_data(sample.file_path_fcs)
        
        # Get channel configuration
        channel_config = get_channel_config()
        
        # Use override if provided, otherwise use config-based detection
        fsc_ch = fsc_channel  # From query parameter
        ssc_ch = ssc_channel  # From query parameter
        
        # Validate override channels exist - fallback if not found
        if fsc_ch and fsc_ch not in channels:
            logger.warning(f"⚠️ Requested FSC channel '{fsc_ch}' not found, will auto-detect")
            fsc_ch = None  # Reset to trigger auto-detection
        if ssc_ch and ssc_ch not in channels:
            logger.warning(f"⚠️ Requested SSC channel '{ssc_ch}' not found, will auto-detect")
            ssc_ch = None  # Reset to trigger auto-detection
        
        # Use channel config for detection if not overridden
        if not fsc_ch:
            fsc_ch = channel_config.detect_fsc_channel(channels)
        
        if not ssc_ch:
            ssc_ch = channel_config.detect_ssc_channel(channels)
        
        # Fallback: Use first two channels if detection fails
        if not fsc_ch and len(channels) >= 1:
            fsc_ch = channels[0]
            logger.warning(f"⚠️ FSC channel not found, using first channel: {fsc_ch}")
        
        if not ssc_ch and len(channels) >= 2:
            ssc_ch = channels[1]
            logger.warning(f"⚠️ SSC channel not found, using second channel: {ssc_ch}")
        
        if not fsc_ch or not ssc_ch:
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
            sampled_data = parsed_data.iloc[sampled_indices].reset_index(drop=True)
            logger.info(f"📉 Sampled {max_points} from {total_events} events")
        else:
            sampled_data = parsed_data.reset_index(drop=True)
            sampled_indices = np.arange(total_events)
        
        # Build scatter data array with diameter calculation
        # Note: Use direct column access instead of itertuples() to handle column names with hyphens
        fsc_values = sampled_data[fsc_ch].values
        ssc_values = sampled_data[ssc_ch].values
        
        # Check for active bead calibration (CAL-001, Feb 10, 2026)
        from src.physics.bead_calibration import get_active_calibration, get_fcmpass_calibration
        active_calibration = get_active_calibration()
        fcmpass_calibration = get_fcmpass_calibration()
        
        # Check for multi-solution Mie capability (VSSC + BSSC channels)
        multi_solution_info = detect_multi_solution_channels(channels)
        can_use_multi_solution = (
            multi_solution_info['can_use_multi_solution'] and
            multi_solution_info['vssc_channel'] in sampled_data.columns and
            multi_solution_info['bssc_channel'] in sampled_data.columns
        )
        
        # Calculate diameters using appropriate method
        # Priority: 1. FCMPASS k-based  2. Legacy bead cal  3. Multi-solution Mie  4. Single-solution Mie
        try:
            if fcmpass_calibration and fcmpass_calibration.calibrated:
                # === FCMPASS K-BASED (HIGHEST PRIORITY, VALIDATED) ===
                # If user requested a different EV RI, update the LUT
                if abs(fcmpass_calibration.n_ev - n_particle) > 1e-6:
                    fcmpass_calibration.update_ev_ri(n_particle)
                logger.info(
                    f"🎯 Using FCMPASS k-based sizing: k={fcmpass_calibration.k_instrument:.1f}, "
                    f"CV={fcmpass_calibration.k_cv_pct:.1f}%, RI_ev={fcmpass_calibration.n_ev}"
                )
                cal_scatter = np.asarray(ssc_values, dtype=np.float64)
                pos_mask = cal_scatter > 0
                if np.any(pos_mask):
                    diameters = np.full(len(ssc_values), np.nan)
                    cal_diameters, in_range = fcmpass_calibration.predict_batch(
                        cal_scatter[pos_mask], show_progress=True
                    )
                    diameters[pos_mask] = cal_diameters
                    success_mask = pos_mask & ~np.isnan(diameters) & (diameters > 0)
                    valid_diameter_count = int(np.sum(success_mask))
                    in_range_count = int(np.sum(in_range))
                    logger.info(
                        f"📐 FCMPASS: {valid_diameter_count}/{len(ssc_values)} valid, "
                        f"{in_range_count} in calibrated range"
                    )
                else:
                    diameters = np.zeros(len(ssc_values))
                    success_mask = np.zeros(len(ssc_values), dtype=bool)
                    valid_diameter_count = 0
            elif active_calibration and active_calibration.is_fitted:
                # === LEGACY BEAD-CALIBRATED ===
                logger.info(f"🎯 Using LEGACY bead-calibrated sizing for scatter data")
                cal_scatter = np.asarray(ssc_values, dtype=np.float64)
                cal_positive = cal_scatter[cal_scatter > 0]
                if len(cal_positive) > 0:
                    diameters = np.full(len(ssc_values), np.nan)
                    pos_mask = cal_scatter > 0
                    cal_diameters = active_calibration.diameter_from_fsc(
                        cal_scatter[pos_mask],
                        target_ri=n_particle,  # Phase 5: Apply RI correction
                        medium_ri=n_medium,
                    )
                    diameters[pos_mask] = cal_diameters
                    success_mask = pos_mask & ~np.isnan(diameters) & (diameters > 0)
                    valid_diameter_count = int(np.sum(success_mask))
                    logger.info(f"📐 Calibrated: {valid_diameter_count}/{len(ssc_values)} valid diameters")
                else:
                    diameters = np.zeros(len(ssc_values))
                    success_mask = np.zeros(len(ssc_values), dtype=bool)
                    valid_diameter_count = 0
            elif can_use_multi_solution:
                # === MULTI-SOLUTION MIE (PREFERRED) ===
                from src.physics.mie_scatter import MultiSolutionMieCalculator
                
                vssc_ch = multi_solution_info['vssc_channel']
                bssc_ch = multi_solution_info['bssc_channel']
                
                logger.info(f"🔬 Using MULTI-SOLUTION Mie: VSSC={vssc_ch}, BSSC={bssc_ch}")
                
                # Try to borrow k-factor from FCMPASS calibration if available.
                # The FCMPASS k converts AU→σ on the calibration channel.
                # Even though FCMPASS takes priority in the cascade, we reach
                # here only when FCMPASS is NOT active — but a previous
                # calibration JSON may still exist on disk with a usable k.
                k_violet = None
                k_blue = None
                try:
                    from src.physics.bead_calibration import get_fcmpass_k_factor
                    _k = get_fcmpass_k_factor()
                    if _k:
                        k_violet = _k  # calibrated on VSSC1-H (405nm)
                        logger.info(f"📐 Borrowed k_violet={k_violet:.1f} from FCMPASS calibration")
                except Exception:
                    pass  # no FCMPASS data — use heuristic fallback
                
                multi_mie_calc = MultiSolutionMieCalculator(
                    n_particle=n_particle,
                    n_medium=n_medium,
                    k_violet=k_violet,
                    k_blue=k_blue,
                )
                
                # Get SSC values for both wavelengths
                ssc_violet = np.asarray(sampled_data[vssc_ch].values, dtype=np.float64)
                ssc_blue = np.asarray(sampled_data[bssc_ch].values, dtype=np.float64)
                
                # Calculate sizes with disambiguation
                diameters, num_solutions = multi_mie_calc.calculate_sizes_multi_solution(ssc_blue, ssc_violet)
                success_mask = ~np.isnan(diameters) & (diameters > 0)
                valid_diameter_count = int(np.sum(success_mask))
                
                # Store num_solutions for per-event multi-solution metadata
                multi_solution_num = num_solutions
                
                logger.info(f"📐 Multi-solution: {valid_diameter_count}/{len(ssc_blue)} valid diameters")
            else:
                # === SINGLE-SOLUTION MIE (FALLBACK) ===
                from src.physics.mie_scatter import MieScatterCalculator
                mie_calc = MieScatterCalculator(
                    wavelength_nm=wavelength_nm,
                    n_particle=n_particle,
                    n_medium=n_medium
                )
                logger.info(f"🔬 Using single-solution Mie: λ={wavelength_nm}nm, n_p={n_particle}, n_m={n_medium}")
                
                # Use batch diameter calculation with normalization for performance
                diameters, success_mask = mie_calc.diameters_from_scatter_normalized(
                    fsc_intensities=fsc_values,
                    min_diameter=20.0,
                    max_diameter=500.0
                )
                valid_diameter_count = int(np.sum(success_mask))
                logger.info(f"📐 Single-solution: {valid_diameter_count}/{len(fsc_values)} valid diameters")
        except Exception as e:
            logger.warning(f"⚠️ Mie calculation failed, using fallback: {e}")
            # Fallback: use relative FSC mapping
            diameters = np.zeros(len(fsc_values))
            success_mask = np.zeros(len(fsc_values), dtype=bool)
            valid_diameter_count = 0
        
        scatter_data = []
        sizing_method_used = "none"
        if fcmpass_calibration and fcmpass_calibration.calibrated:
            sizing_method_used = "fcmpass_k_based"
        elif active_calibration and active_calibration.is_fitted:
            sizing_method_used = "bead_calibrated"
        elif can_use_multi_solution:
            sizing_method_used = "multi_solution_mie"
        else:
            sizing_method_used = "single_solution_mie"
        
        for idx, orig_idx in enumerate(sampled_indices):
            fsc_val = float(fsc_values[idx])
            ssc_val = float(ssc_values[idx])
            
            point_data = {
                "x": fsc_val,
                "y": ssc_val,
                "index": int(orig_idx)
            }
            
            # Add diameter if valid
            if success_mask[idx] and diameters[idx] > 0:
                point_data["diameter"] = round(float(diameters[idx]), 1)
            
            # Add num_solutions if multi-solution Mie was used
            if can_use_multi_solution and 'multi_solution_num' in dir():
                point_data["num_solutions"] = int(multi_solution_num[idx])
            
            scatter_data.append(point_data)
        
        logger.success(f"✅ Returned {len(scatter_data)} scatter points ({valid_diameter_count} with diameter) for {sample_id}")
        
        response_data = {
            "sample_id": sample_id,
            "total_events": total_events,
            "returned_points": len(scatter_data),
            "data": scatter_data,
            "channels": {
                "fsc": fsc_ch,
                "ssc": ssc_ch,
                "available": channels  # Include all available channels for UI
            },
            "sizing_method": sizing_method_used,
        }
        
        # Gain mismatch check (Phase 4 - B3)
        if fcmpass_calibration and fcmpass_calibration.calibrated:
            try:
                from src.parsers.fcs_parser import FCSParser
                parser = FCSParser(sample.file_path_fcs)
                sample_gains = parser.extract_channel_gains()
                if sample_gains:
                    from src.physics.bead_calibration import check_gain_mismatch
                    gain_result = check_gain_mismatch(sample_gains)
                    if gain_result.get("checked") and gain_result.get("has_mismatch"):
                        response_data["warnings"] = response_data.get("warnings", [])
                        response_data["warnings"].extend(gain_result.get("warnings", []))
                        response_data["gain_mismatch"] = gain_result
            except Exception as e:
                logger.debug(f"Gain mismatch check skipped: {e}")
        
        # Cache the response for 2 minutes
        scatter_cache.set(cache_key, response_data, 120)
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get scatter data for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scatter data: {str(e)}"
        )


# ============================================================================
# Clustered Scatter Data Endpoint (UI-002: Large Dataset Visualization)
# ============================================================================

@router.get("/{sample_id}/clustered-scatter", response_model=dict)
async def get_clustered_scatter_data(
    sample_id: str,
    zoom_level: int = Query(1, ge=1, le=3, description="Zoom level: 1=overview (few clusters), 2=medium, 3=detailed"),
    n_clusters_base: int = Query(8, ge=3, le=20, description="Base number of clusters at zoom level 1"),
    fsc_channel: Optional[str] = Query(None, description="FSC channel name override"),
    ssc_channel: Optional[str] = Query(None, description="SSC channel name override"),
    viewport_x_min: Optional[float] = Query(None, description="Viewport X minimum (for zoom level 3)"),
    viewport_x_max: Optional[float] = Query(None, description="Viewport X maximum (for zoom level 3)"),
    viewport_y_min: Optional[float] = Query(None, description="Viewport Y minimum (for zoom level 3)"),
    viewport_y_max: Optional[float] = Query(None, description="Viewport Y maximum (for zoom level 3)"),
    db: AsyncSession = Depends(get_session)
):
    """
    Get hierarchical clustered scatter data for efficient large dataset visualization.
    
    This endpoint uses K-means clustering to summarize large datasets (900k+ events)
    into manageable clusters that can be rendered efficiently. As the user zooms in,
    more detail is revealed.
    
    **Zoom Levels:**
    - Level 1 (Overview): ~8-10 clusters showing major population groups
    - Level 2 (Medium): ~40-50 sub-clusters for more detail
    - Level 3 (Detailed): Individual points within viewport (max 2000)
    
    **Response:**
    ```json
    {
        "sample_id": "PC3_EXO1",
        "zoom_level": 1,
        "total_events": 900000,
        "clusters": [
            {
                "id": 0,
                "cx": 25000,
                "cy": 15000,
                "count": 45000,
                "radius": 30,
                "std_x": 5000,
                "std_y": 3000,
                "pct": 5.0,
                "avg_diameter": 95.2
            },
            ...
        ],
        "bounds": {"x_min": 0, "x_max": 262144, "y_min": 0, "y_max": 262144},
        "individual_points": null
    }
    ```
    
    **Performance:** 
    - Level 1-2: Returns clusters (fast, <100ms)
    - Level 3: Returns up to 2000 individual points within viewport
    """
    from sklearn.cluster import KMeans, MiniBatchKMeans
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
        
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        # Parse FCS file (cached to avoid re-parsing on every request)
        from src.utils.fcs_cache import get_cached_fcs_data
        from src.utils.channel_config import get_channel_config
        
        logger.info(f"📊 Loading clustered scatter data for {sample_id} at zoom level {zoom_level}")
        
        parsed_data, channels = get_cached_fcs_data(sample.file_path_fcs)
        
        # Detect channels
        channel_config = get_channel_config()
        fsc_ch = fsc_channel if fsc_channel and fsc_channel in channels else channel_config.detect_fsc_channel(channels)
        ssc_ch = ssc_channel if ssc_channel and ssc_channel in channels else channel_config.detect_ssc_channel(channels)
        
        if not fsc_ch or not ssc_ch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not detect FSC/SSC channels. Available: {channels}"
            )
        
        # Extract data
        fsc_values = parsed_data[fsc_ch].values.astype(np.float64)
        ssc_values = parsed_data[ssc_ch].values.astype(np.float64)
        total_events = len(fsc_values)
        
        # Calculate data bounds
        x_min, x_max = float(np.min(fsc_values)), float(np.max(fsc_values))
        y_min, y_max = float(np.min(ssc_values)), float(np.max(ssc_values))
        
        # Calculate diameters if possible (for cluster statistics)
        try:
            multi_solution_info = detect_multi_solution_channels(channels)
            if multi_solution_info['can_use_multi_solution']:
                from src.physics.mie_scatter import MultiSolutionMieCalculator
                from src.physics.bead_calibration import get_fcmpass_k_factor
                vssc_ch = multi_solution_info['vssc_channel']
                bssc_ch = multi_solution_info['bssc_channel']
                _k = get_fcmpass_k_factor()
                calc = MultiSolutionMieCalculator(n_particle=1.37, n_medium=1.33, k_violet=_k)
                ssc_violet = parsed_data[vssc_ch].values.astype(np.float64)
                ssc_blue = parsed_data[bssc_ch].values.astype(np.float64)
                diameters, _ = calc.calculate_sizes_multi_solution(ssc_blue, ssc_violet)
            else:
                from src.physics.mie_scatter import MieScatterCalculator
                calc = MieScatterCalculator(wavelength_nm=405.0, n_particle=1.37, n_medium=1.33)
                diameters, _ = calc.diameters_from_scatter_normalized(fsc_values, min_diameter=20.0, max_diameter=500.0)
        except Exception as e:
            logger.warning(f"Could not calculate diameters: {e}")
            diameters = np.full(total_events, np.nan)
        
        # Determine number of clusters based on zoom level
        if zoom_level == 1:
            n_clusters = n_clusters_base
        elif zoom_level == 2:
            n_clusters = n_clusters_base * 5  # ~40 clusters
        else:
            # Level 3: Return individual points within viewport
            n_clusters = None
        
        if zoom_level < 3:
            # Use MiniBatchKMeans for large datasets (faster than regular KMeans)
            X = np.column_stack([fsc_values, ssc_values])
            
            # Sample for very large datasets to speed up clustering
            if total_events > 100000:
                sample_size = min(50000, total_events)
                sample_indices = np.random.choice(total_events, sample_size, replace=False)
                X_sample = X[sample_indices]
                diameters_sample = diameters[sample_indices]
            else:
                X_sample = X
                diameters_sample = diameters
                sample_indices = np.arange(total_events)
            
            # Perform clustering
            kmeans = MiniBatchKMeans(
                n_clusters=n_clusters,
                random_state=42,
                batch_size=1024,
                n_init=3
            )
            labels = kmeans.fit_predict(X_sample)
            
            # Build cluster data
            clusters = []
            for i in range(n_clusters):
                mask = labels == i
                cluster_points = X_sample[mask]
                cluster_diameters = diameters_sample[mask]
                
                if len(cluster_points) == 0:
                    continue
                
                # Calculate cluster statistics
                cx = float(np.mean(cluster_points[:, 0]))
                cy = float(np.mean(cluster_points[:, 1]))
                std_x = float(np.std(cluster_points[:, 0]))
                std_y = float(np.std(cluster_points[:, 1]))
                count = int(np.sum(mask))
                
                # Scale count back to full dataset if we sampled
                if total_events > 100000:
                    count = int(count * (total_events / len(sample_indices)))
                
                pct = round(count / total_events * 100, 2)
                
                # Calculate radius based on count (log scale for visual balance)
                # Min radius 8, max radius 50
                radius = max(8, min(50, 8 + 10 * np.log10(max(1, count / 100))))
                
                # Average diameter for cluster
                valid_diameters = cluster_diameters[~np.isnan(cluster_diameters)]
                avg_diameter = float(np.mean(valid_diameters)) if len(valid_diameters) > 0 else None
                
                clusters.append({
                    "id": i,
                    "cx": round(cx, 2),
                    "cy": round(cy, 2),
                    "count": count,
                    "radius": round(radius, 1),
                    "std_x": round(std_x, 2),
                    "std_y": round(std_y, 2),
                    "pct": pct,
                    "avg_diameter": round(avg_diameter, 1) if avg_diameter else None
                })
            
            # Sort by count descending
            clusters.sort(key=lambda c: c["count"], reverse=True)
            
            logger.success(f"✅ Generated {len(clusters)} clusters for {sample_id} at zoom level {zoom_level}")
            
            return {
                "sample_id": sample_id,
                "zoom_level": zoom_level,
                "total_events": total_events,
                "clusters": clusters,
                "bounds": {
                    "x_min": round(x_min, 2),
                    "x_max": round(x_max, 2),
                    "y_min": round(y_min, 2),
                    "y_max": round(y_max, 2)
                },
                "channels": {"fsc": fsc_ch, "ssc": ssc_ch},
                "individual_points": None
            }
        
        else:
            # Zoom level 3: Return individual points within viewport
            if viewport_x_min is None:
                viewport_x_min = x_min
            if viewport_x_max is None:
                viewport_x_max = x_max
            if viewport_y_min is None:
                viewport_y_min = y_min
            if viewport_y_max is None:
                viewport_y_max = y_max
            
            # Filter points within viewport
            mask = (
                (fsc_values >= viewport_x_min) & (fsc_values <= viewport_x_max) &
                (ssc_values >= viewport_y_min) & (ssc_values <= viewport_y_max)
            )
            
            viewport_indices = np.where(mask)[0]
            
            # Limit to 2000 points
            max_points = 2000
            if len(viewport_indices) > max_points:
                viewport_indices = np.random.choice(viewport_indices, max_points, replace=False)
            
            # Build individual points
            points = []
            for idx in viewport_indices:
                point = {
                    "x": float(fsc_values[idx]),
                    "y": float(ssc_values[idx]),
                    "index": int(idx)
                }
                if not np.isnan(diameters[idx]):
                    point["diameter"] = round(float(diameters[idx]), 1)
                points.append(point)
            
            logger.success(f"✅ Returned {len(points)} individual points for {sample_id} at zoom level 3")
            
            return {
                "sample_id": sample_id,
                "zoom_level": zoom_level,
                "total_events": total_events,
                "clusters": None,
                "bounds": {
                    "x_min": round(x_min, 2),
                    "x_max": round(x_max, 2),
                    "y_min": round(y_min, 2),
                    "y_max": round(y_max, 2)
                },
                "viewport": {
                    "x_min": viewport_x_min,
                    "x_max": viewport_x_max,
                    "y_min": viewport_y_min,
                    "y_max": viewport_y_max
                },
                "channels": {"fsc": fsc_ch, "ssc": ssc_ch},
                "individual_points": points,
                "points_in_viewport": len(viewport_indices) if len(viewport_indices) <= max_points else f"{len(viewport_indices)} (sampled to {max_points})"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get clustered scatter data for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get clustered scatter data: {str(e)}"
        )


# ============================================================================
# Gated Analysis Endpoint (T-009: Population Gating)
# ============================================================================

from pydantic import BaseModel, Field
from typing import Literal

class RectangleGateRequest(BaseModel):
    """Rectangle gate coordinates."""
    type: Literal["rectangle"] = "rectangle"
    x1: float = Field(..., description="Left X coordinate")
    y1: float = Field(..., description="Bottom Y coordinate")
    x2: float = Field(..., description="Right X coordinate")
    y2: float = Field(..., description="Top Y coordinate")


class PolygonGateRequest(BaseModel):
    """Polygon gate coordinates."""
    type: Literal["polygon"] = "polygon"
    points: List[Dict[str, float]] = Field(..., description="List of {x, y} points defining polygon vertices")


class EllipseGateRequest(BaseModel):
    """Ellipse gate coordinates."""
    type: Literal["ellipse"] = "ellipse"
    cx: float = Field(..., description="Center X coordinate")
    cy: float = Field(..., description="Center Y coordinate")
    rx: float = Field(..., description="X radius")
    ry: float = Field(..., description="Y radius")
    rotation: float = Field(default=0.0, description="Rotation angle in degrees")


class GatedAnalysisRequest(BaseModel):
    """Request model for gated population analysis."""
    gate_name: str = Field(default="Gate 1", description="Name of the gate")
    gate_type: Literal["rectangle", "polygon", "ellipse"] = Field(default="rectangle", description="Gate shape type")
    gate_coordinates: Dict[str, Any] = Field(..., description="Gate coordinates based on type")
    x_channel: str = Field(..., description="X-axis channel name")
    y_channel: str = Field(..., description="Y-axis channel name")
    include_diameter_stats: bool = Field(default=True, description="Include diameter statistics")
    # Mie parameters for size calculations
    wavelength_nm: float = Field(default=405.0, ge=200, le=800, description="Laser wavelength")
    n_particle: float = Field(default=1.37, ge=1.0, le=2.0, description="Particle refractive index")
    n_medium: float = Field(default=1.33, ge=1.0, le=2.0, description="Medium refractive index")


@router.post("/{sample_id}/gated-analysis", response_model=dict)
async def analyze_gated_population(
    sample_id: str,
    request: GatedAnalysisRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Analyze a gated (selected) population from a scatter plot.
    
    This endpoint performs statistical analysis on a subset of events
    that fall within a user-defined gate region on a scatter plot.
    
    **Supported Gate Types:**
    - Rectangle: `{x1, y1, x2, y2}` - axis-aligned bounding box
    - Polygon: `{points: [{x, y}, ...]}` - arbitrary polygon vertices
    - Ellipse: `{cx, cy, rx, ry, rotation}` - rotated ellipse
    
    **Request Example:**
    ```json
    {
        "gate_name": "EV Population",
        "gate_type": "rectangle",
        "gate_coordinates": {"x1": 100, "y1": 200, "x2": 500, "y2": 800},
        "x_channel": "FSC-A",
        "y_channel": "SSC-A",
        "include_diameter_stats": true
    }
    ```
    
    **Response:**
    ```json
    {
        "sample_id": "P5_F10_CD81",
        "gate_name": "EV Population",
        "total_events": 100000,
        "gated_events": 24500,
        "gated_percentage": 24.5,
        "statistics": {
            "x_channel": {
                "channel": "FSC-A",
                "mean": 350.2,
                "median": 320.5,
                "std": 125.3,
                "min": 100.0,
                "max": 500.0,
                "cv": 35.8
            },
            "y_channel": {...},
            "diameter": {...}
        },
        "percentiles": {
            "D10": 85.2,
            "D50": 120.5,
            "D90": 185.3
        },
        "comparison_to_total": {
            "x_mean_diff_percent": -12.5,
            "y_mean_diff_percent": 8.2,
            "enrichment_factor": 1.85
        }
    }
    ```
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
        
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        # Parse FCS file (cached)
        from src.utils.fcs_cache import get_cached_fcs_data
        from src.utils.channel_config import get_channel_config
        
        logger.info(f"🎯 Running gated analysis for sample: {sample_id}, gate: {request.gate_name}")
        
        parsed_data, _channels = get_cached_fcs_data(sample.file_path_fcs)
        
        # Validate channels exist
        available_channels = list(parsed_data.columns)
        if request.x_channel not in available_channels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"X channel '{request.x_channel}' not found. Available: {available_channels}"
            )
        if request.y_channel not in available_channels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Y channel '{request.y_channel}' not found. Available: {available_channels}"
            )
        
        # Extract channel data
        x_data = parsed_data[request.x_channel].values
        y_data = parsed_data[request.y_channel].values
        total_events = len(x_data)
        
        # Apply gate to find selected points
        gate_coords = request.gate_coordinates
        gate_type = request.gate_type
        
        if gate_type == "rectangle":
            # Rectangle gate: check if points are within bounds
            x1, y1 = gate_coords.get("x1", 0), gate_coords.get("y1", 0)
            x2, y2 = gate_coords.get("x2", 0), gate_coords.get("y2", 0)
            
            # Ensure correct ordering
            x_min, x_max = min(x1, x2), max(x1, x2)
            y_min, y_max = min(y1, y2), max(y1, y2)
            
            mask = (
                (x_data >= x_min) & (x_data <= x_max) &
                (y_data >= y_min) & (y_data <= y_max)
            )
            
        elif gate_type == "polygon":
            # Polygon gate: point-in-polygon test
            points = gate_coords.get("points", [])
            if len(points) < 3:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Polygon gate requires at least 3 points"
                )
            
            # Use matplotlib path for efficient point-in-polygon
            try:
                from matplotlib.path import Path
                polygon_vertices = [(p["x"], p["y"]) for p in points]
                polygon_path = Path(polygon_vertices)
                test_points = np.column_stack((x_data, y_data))
                mask = polygon_path.contains_points(test_points)
            except ImportError:
                # Fallback: simple ray casting algorithm
                mask = np.array([
                    _point_in_polygon(x_data[i], y_data[i], points)
                    for i in range(len(x_data))
                ])
                
        elif gate_type == "ellipse":
            # Ellipse gate: check if points are within ellipse
            cx = gate_coords.get("cx", 0)
            cy = gate_coords.get("cy", 0)
            rx = gate_coords.get("rx", 1)
            ry = gate_coords.get("ry", 1)
            rotation = np.radians(gate_coords.get("rotation", 0))
            
            # Transform points relative to ellipse center
            dx = x_data - cx
            dy = y_data - cy
            
            # Apply rotation
            cos_r, sin_r = np.cos(-rotation), np.sin(-rotation)
            rx_rot = dx * cos_r - dy * sin_r
            ry_rot = dx * sin_r + dy * cos_r
            
            # Check if within ellipse
            mask = ((rx_rot / rx) ** 2 + (ry_rot / ry) ** 2) <= 1.0
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported gate type: {gate_type}"
            )
        
        # Get gated data
        gated_indices = np.where(mask)[0]
        gated_count = len(gated_indices)
        gated_percentage = (gated_count / total_events * 100) if total_events > 0 else 0
        
        if gated_count == 0:
            return {
                "sample_id": sample_id,
                "gate_name": request.gate_name,
                "gate_type": gate_type,
                "total_events": total_events,
                "gated_events": 0,
                "gated_percentage": 0.0,
                "message": "No events found within the gate region",
                "statistics": None,
                "percentiles": None,
                "comparison_to_total": None
            }
        
        # Get gated values
        gated_x = x_data[mask]
        gated_y = y_data[mask]
        
        # Calculate statistics helper function
        def calc_stats(values: np.ndarray, channel_name: str) -> dict:
            """Calculate comprehensive statistics for a channel."""
            return {
                "channel": channel_name,
                "count": len(values),
                "mean": float(np.mean(values)),
                "median": float(np.median(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "cv": float(np.std(values) / np.mean(values) * 100) if np.mean(values) > 0 else 0,
                "q25": float(np.percentile(values, 25)),
                "q75": float(np.percentile(values, 75)),
                "iqr": float(np.percentile(values, 75) - np.percentile(values, 25))
            }
        
        # Calculate gated statistics
        x_stats = calc_stats(gated_x, request.x_channel)
        y_stats = calc_stats(gated_y, request.y_channel)
        
        # Calculate total population statistics for comparison
        total_x_mean = float(np.mean(x_data))
        total_y_mean = float(np.mean(y_data))
        
        # Diameter statistics if requested
        diameter_stats = None
        diameter_percentiles = None
        
        if request.include_diameter_stats:
            try:
                # Check for multi-solution Mie capability
                multi_solution_info = detect_multi_solution_channels(available_channels)
                can_use_multi_solution = (
                    multi_solution_info['can_use_multi_solution'] and
                    multi_solution_info['vssc_channel'] in parsed_data.columns and
                    multi_solution_info['bssc_channel'] in parsed_data.columns
                )
                
                if can_use_multi_solution:
                    # === MULTI-SOLUTION MIE (PREFERRED) ===
                    from src.physics.mie_scatter import MultiSolutionMieCalculator
                    
                    vssc_ch = multi_solution_info['vssc_channel']
                    bssc_ch = multi_solution_info['bssc_channel']
                    
                    logger.info(f"🔬 Gated analysis using MULTI-SOLUTION Mie: VSSC={vssc_ch}, BSSC={bssc_ch}")
                    
                    from src.physics.bead_calibration import get_fcmpass_k_factor
                    _k = get_fcmpass_k_factor()
                    multi_mie_calc = MultiSolutionMieCalculator(
                        n_particle=request.n_particle, 
                        n_medium=request.n_medium,
                        k_violet=_k,
                    )
                    
                    # Get SSC values for gated events
                    gated_vssc = np.asarray(parsed_data[vssc_ch].values[mask], dtype=np.float64)
                    gated_bssc = np.asarray(parsed_data[bssc_ch].values[mask], dtype=np.float64)
                    
                    # Calculate sizes with disambiguation
                    sizes, num_solutions = multi_mie_calc.calculate_sizes_multi_solution(gated_bssc, gated_vssc)
                    diameters = sizes[~np.isnan(sizes) & (sizes > 0)]
                else:
                    # === SINGLE-SOLUTION MIE (FALLBACK) ===
                    from src.physics.mie_scatter import MieScatterCalculator
                    mie_calc = MieScatterCalculator(
                        wavelength_nm=request.wavelength_nm,
                        n_particle=request.n_particle,
                        n_medium=request.n_medium
                    )
                    logger.info(f"🔬 Gated analysis using single-solution Mie: λ={request.wavelength_nm}nm")
                    
                    # Calculate diameters for gated events
                    diameters = []
                    for fsc_val in gated_x:
                        try:
                            d, success = mie_calc.diameter_from_scatter(
                                fsc_intensity=float(fsc_val),
                                min_diameter=20.0,
                                max_diameter=500.0
                            )
                            if success and d > 0:
                                diameters.append(d)
                        except Exception:
                            pass
                    diameters = np.array(diameters) if diameters else np.array([])
                
                if len(diameters) >= 10:  # Need enough data points
                    diameter_stats = calc_stats(diameters, "diameter_nm")
                    diameter_percentiles = {
                        "D10": float(np.percentile(diameters, 10)),
                        "D50": float(np.percentile(diameters, 50)),
                        "D90": float(np.percentile(diameters, 90)),
                        "mean": float(np.mean(diameters)),
                        "mode_estimate": float(np.percentile(diameters, 50))  # Using median as mode estimate
                    }
                    logger.info(f"📏 Calculated diameter for {len(diameters)}/{gated_count} gated events")
            except Exception as e:
                logger.warning(f"⚠️ Failed to calculate diameter stats: {e}")
        
        # Calculate comparison metrics
        comparison = {
            "x_mean_diff_percent": float((x_stats["mean"] - total_x_mean) / total_x_mean * 100) if total_x_mean != 0 else 0,
            "y_mean_diff_percent": float((y_stats["mean"] - total_y_mean) / total_y_mean * 100) if total_y_mean != 0 else 0,
            "enrichment_factor": gated_percentage / 100.0 * total_events / gated_count if gated_count > 0 else 0,
            "total_x_mean": total_x_mean,
            "total_y_mean": total_y_mean,
            "total_x_std": float(np.std(x_data)),
            "total_y_std": float(np.std(y_data))
        }
        
        logger.success(f"✅ Gated analysis complete: {gated_count}/{total_events} events ({gated_percentage:.2f}%)")
        
        return {
            "sample_id": sample_id,
            "gate_name": request.gate_name,
            "gate_type": gate_type,
            "gate_coordinates": gate_coords,
            "total_events": total_events,
            "gated_events": gated_count,
            "gated_percentage": round(gated_percentage, 2),
            "gated_indices": gated_indices.tolist()[:1000],  # Return first 1000 indices for reference
            "statistics": {
                "x_channel": x_stats,
                "y_channel": y_stats,
                "diameter": diameter_stats
            },
            "percentiles": diameter_percentiles,
            "comparison_to_total": comparison
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed gated analysis for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze gated population: {str(e)}"
        )


def _point_in_polygon(x: float, y: float, polygon: List[Dict[str, float]]) -> bool:
    """
    Ray casting algorithm for point-in-polygon test.
    Fallback when matplotlib is not available.
    """
    n = len(polygon)
    inside = False
    
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]["x"], polygon[i]["y"]
        xj, yj = polygon[j]["x"], polygon[j]["y"]
        
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    
    return inside


# ============================================================================
# Auto Axis Selection Endpoint (CRMIT-002)
# ============================================================================

@router.get("/{sample_id}/recommend-axes", response_model=dict)
async def get_recommended_axes(
    sample_id: str,
    n_recommendations: int = Query(5, ge=1, le=10, description="Number of axis pair recommendations"),
    include_scatter: bool = Query(True, description="Include scatter channel combinations"),
    include_fluorescence: bool = Query(True, description="Include fluorescence channel combinations"),
    db: AsyncSession = Depends(get_session)
):
    """
    Get AI-recommended optimal axis pairs for scatter plot visualization.
    
    Uses intelligent analysis to recommend the best channel combinations based on:
    - Variance and spread (information content)
    - Correlation between channels (avoid redundancy)
    - Dynamic range assessment
    - Population separation metrics (multi-modal distributions)
    - Standard cytometry best practices
    
    **Scoring Criteria:**
    - Variance (30%): High variance = more information
    - Correlation (20%): Low correlation = independent information
    - Dynamic Range (20%): Larger range = better separation
    - Population Separation (20%): Multi-population = interesting biology
    - Modality (10%): Bimodal distributions = distinct populations
    
    **Response:**
    ```json
    {
        "sample_id": "P5_F10_CD81",
        "recommendations": [
            {
                "rank": 1,
                "x_channel": "VFSC-A",
                "y_channel": "VSSC1-A",
                "score": 0.95,
                "reason": "Standard gating view (FSC vs SSC)",
                "description": "Universal starting point for flow cytometry. Used for initial gating, doublet discrimination, and debris removal."
            },
            {
                "rank": 2,
                "x_channel": "B531-H",
                "y_channel": "VFSC-A",
                "score": 0.78,
                "reason": "Fluorescence vs Size",
                "description": "Compare marker expression with particle size to identify marker-positive populations."
            }
        ],
        "channels": {
            "scatter": ["VFSC-A", "VFSC-H", "VSSC1-A", "VSSC1-H"],
            "fluorescence": ["B531-H", "R670-H", "Y585-H", "V447-H"],
            "all": ["VFSC-A", "VFSC-H", "VSSC1-A", ...]
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
        
        # Parse FCS file (cached)
        from src.utils.fcs_cache import get_cached_fcs_data
        from src.visualization.auto_axis_selector import AutoAxisSelector
        
        logger.info(f"🎯 Analyzing optimal axes for sample: {sample_id}")
        
        parsed_data, all_channels = get_cached_fcs_data(sample.file_path_fcs)
        
        # Initialize auto-axis selector
        selector = AutoAxisSelector()
        
        # Get channel categories
        scatter_channels = selector._identify_scatter_channels(all_channels)
        fluorescence_channels = selector._identify_fluorescence_channels(all_channels)
        
        # Get recommendations
        best_pairs = selector.select_best_axes(
            parsed_data,
            n_pairs=n_recommendations,
            include_scatter=include_scatter,
            include_fluorescence=include_fluorescence
        )
        
        # Build detailed recommendations
        recommendations = []
        for rank, (x_ch, y_ch, score) in enumerate(best_pairs, 1):
            # Determine reason and description
            x_upper = x_ch.upper()
            y_upper = y_ch.upper()
            
            # Check channel types
            x_is_scatter = any(s in x_upper for s in ['FSC', 'SSC', 'VFSC', 'VSSC'])
            y_is_scatter = any(s in y_upper for s in ['FSC', 'SSC', 'VFSC', 'VSSC'])
            
            if x_is_scatter and y_is_scatter:
                # Both scatter - check if FSC vs SSC
                is_fsc_ssc = (
                    ('FSC' in x_upper or 'VFSC' in x_upper) and 
                    ('SSC' in y_upper or 'VSSC' in y_upper)
                ) or (
                    ('SSC' in x_upper or 'VSSC' in x_upper) and 
                    ('FSC' in y_upper or 'VFSC' in y_upper)
                )
                if is_fsc_ssc:
                    reason = "Standard gating view (FSC vs SSC)"
                    description = "Universal starting point for flow cytometry. Used for initial gating, doublet discrimination, and debris removal."
                else:
                    reason = "Scatter comparison"
                    description = "Compare scatter parameters to identify particle characteristics (e.g., FSC-A vs FSC-H for doublet discrimination)."
            elif x_is_scatter or y_is_scatter:
                reason = "Fluorescence vs Size"
                description = "Compare marker expression with particle size to identify size characteristics of marker-positive populations."
            else:
                reason = "Multi-marker analysis"
                description = "Compare expression of two fluorescence markers to identify co-expression patterns and distinct populations."
            
            recommendations.append({
                "rank": rank,
                "x_channel": x_ch,
                "y_channel": y_ch,
                "score": round(float(score), 3),
                "reason": reason,
                "description": description
            })
        
        logger.success(f"✅ Generated {len(recommendations)} axis recommendations for {sample_id}")
        
        return {
            "sample_id": sample_id,
            "total_events": len(parsed_data),
            "recommendations": recommendations,
            "channels": {
                "scatter": scatter_channels,
                "fluorescence": fluorescence_channels,
                "all": all_channels
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get axis recommendations for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get axis recommendations: {str(e)}"
        )


# ============================================================================
# Particle Size Binning Endpoint
# ============================================================================

@router.get("/{sample_id}/size-bins", response_model=dict)
async def get_size_bins(
    sample_id: str,
    fsc_channel: Optional[str] = Query(None, description="FSC channel name override (e.g., 'Channel_3')"),
    wavelength_nm: float = Query(405.0, ge=200, le=800, description="Laser wavelength for Mie calculations"),
    n_particle: float = Query(1.37, ge=1.0, le=2.0, description="Particle refractive index"),
    n_medium: float = Query(1.33, ge=1.0, le=2.0, description="Medium refractive index"),
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
    # Check cache first
    from src.api.cache import size_bins_cache, make_cache_key
    cache_key = f"bins:{sample_id}:{make_cache_key(fsc_channel, wavelength_nm, n_particle, n_medium)}"
    cached = size_bins_cache.get(cache_key)
    if cached is not None:
        logger.debug(f"📊 Cache HIT for size bins: {sample_id}")
        return cached
    
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
        
        # Parse FCS file (cached)
        from src.utils.fcs_cache import get_cached_fcs_data  # type: ignore[import-not-found]
        import numpy as np
        
        logger.info(f"📏 Calculating size bins for sample: {sample_id}")
        
        parsed_data, channels = get_cached_fcs_data(sample.file_path_fcs)
        
        # Get channel configuration
        from src.utils.channel_config import get_channel_config  # type: ignore[import-not-found]
        channel_config = get_channel_config()
        
        # Use override if provided
        fsc_ch = fsc_channel  # From query parameter
        
        # Validate override channel exists
        if fsc_ch and fsc_ch not in channels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"FSC channel '{fsc_ch}' not found. Available: {', '.join(channels)}"
            )
        
        # Use channel config for detection if not overridden
        if not fsc_ch:
            fsc_ch = channel_config.detect_fsc_channel(channels)
        
        # Fallback: Use first channel if detection fails
        if not fsc_ch and len(channels) >= 1:
            fsc_ch = channels[0]
            logger.warning(f"⚠️ FSC channel not found for size bins, using first channel: {fsc_ch}")
        
        total_events = len(parsed_data)
        
        # Sample for performance (calculate on subset, extrapolate to full dataset)
        sample_size = min(10000, total_events)
        np.random.seed(42)
        sample_indices = np.random.choice(total_events, size=sample_size, replace=False) if total_events > sample_size else np.arange(total_events)
        
        # Check for multi-solution Mie capability
        multi_solution_info = detect_multi_solution_channels(channels)
        can_use_multi_solution = (
            multi_solution_info['can_use_multi_solution'] and
            multi_solution_info['vssc_channel'] in parsed_data.columns and
            multi_solution_info['bssc_channel'] in parsed_data.columns
        )
        
        if can_use_multi_solution:
            # === MULTI-SOLUTION MIE (PREFERRED) ===
            from src.physics.mie_scatter import MultiSolutionMieCalculator
            
            vssc_ch = multi_solution_info['vssc_channel']
            bssc_ch = multi_solution_info['bssc_channel']
            
            logger.info(f"🔬 Size bins using MULTI-SOLUTION Mie: VSSC={vssc_ch}, BSSC={bssc_ch}")
            
            from src.physics.bead_calibration import get_fcmpass_k_factor
            _k = get_fcmpass_k_factor()
            multi_mie_calc = MultiSolutionMieCalculator(n_particle=n_particle, n_medium=n_medium, k_violet=_k)
            
            # Get SSC values for both wavelengths
            ssc_violet = np.asarray(parsed_data[vssc_ch].values[sample_indices], dtype=np.float64)
            ssc_blue = np.asarray(parsed_data[bssc_ch].values[sample_indices], dtype=np.float64)
            
            # Calculate sizes with disambiguation
            sizes_array, num_solutions = multi_mie_calc.calculate_sizes_multi_solution(ssc_blue, ssc_violet)
            sizes_array = sizes_array[~np.isnan(sizes_array) & (sizes_array > 0)]
        else:
            # === SINGLE-SOLUTION MIE (FALLBACK) ===
            from src.physics.mie_scatter import MieScatterCalculator
            mie_calc = MieScatterCalculator(
                wavelength_nm=wavelength_nm,
                n_particle=n_particle,
                n_medium=n_medium
            )
            logger.info(f"🔬 Size bins using single-solution Mie: λ={wavelength_nm}nm, n_p={n_particle}, n_m={n_medium}")
            
            sampled_fsc = parsed_data[fsc_ch].values[sample_indices]
            
            # Use NORMALIZED batch conversion: FSC to size (handles scale mismatch)
            sizes_array, success_mask = mie_calc.diameters_from_scatter_normalized(
                sampled_fsc, min_diameter=10.0, max_diameter=500.0
            )
            sizes_array = sizes_array[success_mask & (sizes_array > 0)]
        
        # Bin sizes into 5 categories (matching frontend)
        exomere_count = np.sum(sizes_array < 50)
        small_count = np.sum((sizes_array >= 51) & (sizes_array <= 100))
        medium_count = np.sum((sizes_array >= 101) & (sizes_array <= 150))
        large_count = np.sum((sizes_array >= 151) & (sizes_array <= 200))
        very_large_count = np.sum(sizes_array > 200)
        
        total_binned = exomere_count + small_count + medium_count + large_count + very_large_count
        
        # Extrapolate to full dataset
        scale_factor = total_events / sample_size if total_binned > 0 else 1.0
        
        exomere_total = int(exomere_count * scale_factor)
        small_total = int(small_count * scale_factor)
        medium_total = int(medium_count * scale_factor)
        large_total = int(large_count * scale_factor)
        very_large_total = int(very_large_count * scale_factor)
        
        # Calculate percentages
        total_categorized = exomere_total + small_total + medium_total + large_total + very_large_total
        exomere_pct = (exomere_total / total_categorized * 100) if total_categorized > 0 else 0
        small_pct = (small_total / total_categorized * 100) if total_categorized > 0 else 0
        medium_pct = (medium_total / total_categorized * 100) if total_categorized > 0 else 0
        large_pct = (large_total / total_categorized * 100) if total_categorized > 0 else 0
        very_large_pct = (very_large_total / total_categorized * 100) if total_categorized > 0 else 0
        
        logger.success(
            f"✅ Size bins for {sample_id}: "
            f"Exomeres={exomere_pct:.1f}%, Small={small_pct:.1f}%, Medium={medium_pct:.1f}%, "
            f"Large={large_pct:.1f}%, VeryLarge={very_large_pct:.1f}%"
        )
        
        response_data = {
            "sample_id": sample_id,
            "total_events": total_events,
            "bins": {
                "exomeres": exomere_total,
                "small": small_total,
                "medium": medium_total,
                "large": large_total,
                "very_large": very_large_total
            },
            "percentages": {
                "exomeres": round(exomere_pct, 2),
                "small": round(small_pct, 2),
                "medium": round(medium_pct, 2),
                "large": round(large_pct, 2),
                "very_large": round(very_large_pct, 2)
            },
            "thresholds": {
                "exomere_max": 50,
                "small_min": 51,
                "small_max": 100,
                "medium_min": 101,
                "medium_max": 150,
                "large_min": 151,
                "large_max": 200,
                "very_large_min": 200
            }
        }
        
        # Cache for 2 minutes
        size_bins_cache.set(cache_key, response_data, 120)
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get size bins for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get size bins: {str(e)}"
        )


# ============================================================================
# Distribution Analysis Endpoint (VAL-008 + STAT-001)
# ============================================================================

@router.get("/{sample_id}/distribution-analysis", response_model=dict)
async def get_distribution_analysis(
    sample_id: str,
    fsc_channel: Optional[str] = Query(None, description="FSC channel name override (e.g., 'Channel_3')"),
    wavelength_nm: float = Query(405.0, ge=200, le=800, description="Laser wavelength for Mie calculations"),
    n_particle: float = Query(1.37, ge=1.0, le=2.0, description="Particle refractive index"),
    n_medium: float = Query(1.33, ge=1.0, le=2.0, description="Medium refractive index"),
    include_overlays: bool = Query(True, description="Include distribution overlay curves for plotting"),
    db: AsyncSession = Depends(get_session)
):
    """
    Perform comprehensive distribution analysis on particle size data.
    
    This endpoint runs multiple normality tests, fits various probability
    distributions (Normal, Log-normal, Gamma, Weibull), and provides
    recommendations for biological interpretation.
    
    **Key Features:**
    - Normality testing: Shapiro-Wilk, D'Agostino-Pearson, K-S, Anderson-Darling
    - Distribution fitting: Normal, Log-normal (recommended), Gamma, Weibull
    - AIC/BIC model comparison for best statistical fit
    - Overlay curves for histogram visualization
    
    **Response:**
    ```json
    {
        "sample_id": "PC3_EXO1",
        "n_samples": 5000,
        "normality_tests": {
            "tests": {...},
            "is_normal": false,
            "conclusion": "Data is NOT normally distributed (0/4 tests passed)"
        },
        "distribution_fits": {
            "fits": {...},
            "best_fit_aic": "weibull_min",
            "recommendation": "lognorm",
            "recommendation_reason": "Log-normal recommended for biological interpretation..."
        },
        "summary_statistics": {
            "mean": 120.5,
            "median": 95.2,
            "d10": 45.0,
            "d50": 95.2,
            "d90": 210.0,
            "skewness": 1.2,
            "skew_interpretation": "right-skewed (positive)"
        },
        "conclusion": {
            "is_normal": false,
            "recommended_distribution": "lognorm",
            "use_median": true,
            "central_tendency": 95.2,
            "central_tendency_metric": "median (D50)"
        },
        "overlays": {...}
    }
    ```
    
    **Notes:**
    - EV size distributions are typically NOT normal (usually right-skewed)
    - Log-normal is biologically appropriate due to multiplicative growth processes
    - Use median (D50) instead of mean for non-normal distributions
    - Per MISEV2018 guidelines: report median with D10/D90 for EV sizing
    """
    from src.physics.statistics_utils import comprehensive_distribution_analysis
    from src.physics.mie_scatter import MieScatterCalculator
    from src.parsers.fcs_parser import FCSParser
    from pathlib import Path
    from src.api.cache import distribution_cache, make_cache_key
    
    # Check cache first — distribution analysis is expensive
    cache_key = f"dist:{sample_id}:{make_cache_key(fsc_channel, wavelength_nm, n_particle, n_medium, include_overlays)}"
    cached = distribution_cache.get(cache_key)
    if cached is not None:
        logger.debug(f"📊 Cache HIT for distribution analysis: {sample_id}")
        return cached
    
    try:
        # Get sample from database
        query = select(Sample).where(Sample.sample_id == sample_id)
        result = await db.execute(query)
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample not found: {sample_id}"
            )
        
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sample has no FCS data for distribution analysis"
            )
        
        # Parse FCS file (cached)
        import os
        if not os.path.exists(sample.file_path_fcs):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"FCS file not found: {sample.file_path_fcs}"
            )
        
        from src.utils.fcs_cache import get_cached_fcs_data
        parsed_data, _channels = get_cached_fcs_data(sample.file_path_fcs)
        if parsed_data.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data in FCS file"
            )
        
        import numpy as np
        available_channels = parsed_data.columns.tolist()
        sizing_method_used = 'heuristic_mie'  # Track which method produced sizes
        sizes_nm = None
        
        # ===================================================================
        # SIZING CASCADE: FCMPASS → Multi-Solution Mie → Heuristic fallback
        # ===================================================================
        
        # --- Priority 1: FCMPASS k-based sizing (most accurate) ---
        try:
            from src.physics.bead_calibration import get_fcmpass_calibration
            fcmpass_cal = get_fcmpass_calibration()
            if fcmpass_cal and fcmpass_cal.calibrated:
                # Update EV RI if user specified different from calibration
                if abs(fcmpass_cal.n_ev - n_particle) > 1e-6:
                    fcmpass_cal.update_ev_ri(n_particle)
                
                # Auto-detect best scatter channel (prefer VSSC1-H for violet-calibrated)
                cal_channel = None
                for ch_name in ['VSSC1-H', 'VSSC-H', 'VSSC1_H', 'SSC-H', 'SSC_H']:
                    if ch_name in available_channels:
                        cal_channel = ch_name
                        break
                if not cal_channel:
                    for ch in available_channels:
                        if 'SSC' in ch.upper():
                            cal_channel = ch
                            break
                
                if cal_channel:
                    scatter_vals = np.asarray(parsed_data[cal_channel].values, dtype=np.float64)
                    pos_mask = np.isfinite(scatter_vals) & (scatter_vals > 0)
                    scatter_pos = scatter_vals[pos_mask]
                    
                    # Sample for efficiency
                    sample_size = min(50000, len(scatter_pos))
                    if len(scatter_pos) > sample_size:
                        np.random.seed(42)
                        scatter_pos = np.random.choice(scatter_pos, size=sample_size, replace=False)
                    
                    if len(scatter_pos) > 100:
                        cal_diameters, in_range = fcmpass_cal.predict_batch(scatter_pos)
                        valid_cal = cal_diameters[~np.isnan(cal_diameters) & (cal_diameters > 0)]
                        if len(valid_cal) > 10:
                            sizes_nm = valid_cal
                            sizing_method_used = 'fcmpass_k_based'
                            logger.info(
                                f"📊 Distribution analysis using FCMPASS k-based sizing: "
                                f"{len(sizes_nm)} valid particles, D50={np.median(sizes_nm):.1f}nm"
                            )
        except Exception as e:
            logger.warning(f"⚠️ FCMPASS sizing failed for distribution analysis: {e}")
        
        # --- Priority 2: Multi-solution Mie with k-factor (if FCMPASS unavailable) ---
        if sizes_nm is None:
            try:
                from src.physics.mie_scatter import MultiSolutionMieCalculator
                from src.physics.bead_calibration import get_fcmpass_k_factor
                
                # Check for multi-wavelength scatter channels
                vssc_ch = None
                bssc_ch = None
                for ch in available_channels:
                    ch_upper = ch.upper()
                    if 'VSSC' in ch_upper and vssc_ch is None:
                        vssc_ch = ch
                    elif 'BSSC' in ch_upper and bssc_ch is None:
                        bssc_ch = ch
                
                if vssc_ch and bssc_ch:
                    k_violet = get_fcmpass_k_factor()
                    multi_mie = MultiSolutionMieCalculator(
                        n_particle=n_particle, n_medium=n_medium, k_violet=k_violet
                    )
                    
                    sample_size = min(50000, len(parsed_data))
                    np.random.seed(42)
                    if len(parsed_data) > sample_size:
                        idx = np.random.choice(len(parsed_data), size=sample_size, replace=False)
                    else:
                        idx = np.arange(len(parsed_data))
                    
                    ssc_v = np.asarray(parsed_data[vssc_ch].values[idx], dtype=np.float64)
                    ssc_b = np.asarray(parsed_data[bssc_ch].values[idx], dtype=np.float64)
                    valid_mask = (ssc_v > 0) & (ssc_b > 0)
                    ssc_v = ssc_v[valid_mask]
                    ssc_b = ssc_b[valid_mask]
                    
                    if len(ssc_v) > 100:
                        computed, num_sols = multi_mie.calculate_sizes_multi_solution(ssc_b, ssc_v)
                        valid = ~np.isnan(computed) & (computed >= 20) & (computed <= 500)
                        if np.sum(valid) > 10:
                            sizes_nm = computed[valid]
                            sizing_method_used = 'multi_solution_mie'
                            logger.info(
                                f"📊 Distribution analysis using multi-solution Mie: "
                                f"{len(sizes_nm)} valid particles, D50={np.median(sizes_nm):.1f}nm"
                            )
            except Exception as e:
                logger.warning(f"⚠️ Multi-solution Mie failed for distribution analysis: {e}")
        
        # --- Priority 3: Heuristic single-solution Mie (fallback) ---
        if sizes_nm is None:
            # Determine FSC channel
            if fsc_channel and fsc_channel in available_channels:
                selected_fsc = fsc_channel
            else:
                fsc_candidates = ['FSC-H', 'FSC-A', 'FSC_H', 'FSC_A', 'BFSC-H', 'BFSC-A']
                selected_fsc = None
                for candidate in fsc_candidates:
                    if candidate in available_channels:
                        selected_fsc = candidate
                        break
                if not selected_fsc:
                    for ch in available_channels:
                        if 'FSC' in ch.upper():
                            selected_fsc = ch
                            break
            
            if not selected_fsc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No FSC/SSC channel found for sizing. Available: {available_channels[:10]}"
                )
            
            fsc_values = parsed_data[selected_fsc].values
            fsc_values = fsc_values[np.isfinite(fsc_values) & (fsc_values > 0)]
            
            if len(fsc_values) < 10:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient valid FSC data (n={len(fsc_values)}, need ≥10)"
                )
            
            mie = MieScatterCalculator(
                wavelength_nm=wavelength_nm,
                n_particle=n_particle,
                n_medium=n_medium
            )
            sizes_all, success_mask = mie.diameters_from_scatter_normalized(
                fsc_intensities=fsc_values[:min(len(fsc_values), 50000)],
                min_diameter=20.0,
                max_diameter=500.0,
                lut_resolution=500
            )
            valid = success_mask & np.isfinite(sizes_all) & (sizes_all > 0) & (sizes_all < 1000)
            sizes_nm = sizes_all[valid]
            sizing_method_used = 'heuristic_mie'
            logger.info(
                f"📊 Distribution analysis using heuristic Mie (fallback): "
                f"{len(sizes_nm)} valid particles, D50={np.median(sizes_nm):.1f}nm"
            )
        
        if sizes_nm is None or len(sizes_nm) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient valid size data after sizing (n={len(sizes_nm) if sizes_nm is not None else 0})"
            )
        
        logger.info(f"📊 Running distribution analysis for {sample_id} with {len(sizes_nm)} particles")
        
        # Run comprehensive distribution analysis
        analysis = comprehensive_distribution_analysis(
            data=sizes_nm,
            include_overlays=include_overlays
        )
        
        # Add metadata to response
        analysis['sample_id'] = sample_id
        analysis['sizing_method'] = sizing_method_used
        analysis['mie_parameters'] = {
            'wavelength_nm': wavelength_nm,
            'n_particle': n_particle,
            'n_medium': n_medium,
            'method': sizing_method_used,
        }
        
        logger.info(
            f"✅ Distribution analysis complete for {sample_id}: "
            f"is_normal={analysis['conclusion']['is_normal']}, "
            f"recommended={analysis['conclusion']['recommended_distribution']}"
        )
        
        # Cache for 2 minutes
        distribution_cache.set(cache_key, analysis, 120)
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to run distribution analysis for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Distribution analysis failed: {str(e)}"
        )


# ============================================================================
# Anomaly Detection Endpoint
# ============================================================================

@router.get("/{sample_id}/anomaly-detection", response_model=dict)
async def detect_anomalies(
    sample_id: str,
    method: str = Query("zscore", description="Anomaly method: zscore, iqr, both"),
    zscore_threshold: float = Query(3.0, ge=1.0, le=10.0, description="Z-score threshold"),
    iqr_factor: float = Query(1.5, ge=1.0, le=5.0, description="IQR factor for outlier detection"),
    fsc_channel: Optional[str] = Query(None, description="FSC channel name override"),
    ssc_channel: Optional[str] = Query(None, description="SSC channel name override"),
    db: AsyncSession = Depends(get_session)
):
    """
    Run anomaly detection on a sample's scatter data.
    
    Uses statistical methods (Z-score and/or IQR) to detect anomalous events.
    
    **Parameters:**
    - method: Detection method - "zscore", "iqr", or "both"
    - zscore_threshold: Z-score threshold (default 3.0)
    - iqr_factor: IQR factor for outlier detection (default 1.5)
    
    **Response:**
    ```json
    {
        "sample_id": "P5_F10_CD81",
        "enabled": true,
        "method": "zscore",
        "total_anomalies": 250,
        "anomaly_percentage": 2.5,
        "anomalous_indices": [123, 456, ...]
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
        
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        # Parse FCS file (cached)
        from src.utils.fcs_cache import get_cached_fcs_data
        from src.utils.channel_config import get_channel_config
        import numpy as np
        
        logger.info(f"🔍 Running anomaly detection for sample: {sample_id}")
        
        parsed_data, channels = get_cached_fcs_data(sample.file_path_fcs)
        channel_config = get_channel_config()
        
        fsc_ch = fsc_channel or channel_config.detect_fsc_channel(channels)
        ssc_ch = ssc_channel or channel_config.detect_ssc_channel(channels)
        
        if not fsc_ch and len(channels) >= 1:
            fsc_ch = channels[0]
        if not ssc_ch and len(channels) >= 2:
            ssc_ch = channels[1]
        
        if not fsc_ch or not ssc_ch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not find FSC/SSC channels. Available: {', '.join(channels)}"
            )
        
        # Run anomaly detection
        fsc_values = parsed_data[fsc_ch].values
        ssc_values = parsed_data[ssc_ch].values
        
        anomalous_indices = set()
        
        if method in ['zscore', 'both']:
            # Z-score based detection
            fsc_mean, fsc_std = np.mean(fsc_values), np.std(fsc_values)
            ssc_mean, ssc_std = np.mean(ssc_values), np.std(ssc_values)
            
            fsc_zscore = np.abs((fsc_values - fsc_mean) / (fsc_std + 1e-10))
            ssc_zscore = np.abs((ssc_values - ssc_mean) / (ssc_std + 1e-10))
            
            zscore_outliers = np.where((fsc_zscore > zscore_threshold) | (ssc_zscore > zscore_threshold))[0]
            anomalous_indices.update(zscore_outliers.tolist())
        
        if method in ['iqr', 'both']:
            # IQR based detection
            fsc_q1, fsc_q3 = np.percentile(fsc_values, [25, 75])
            ssc_q1, ssc_q3 = np.percentile(ssc_values, [25, 75])
            
            fsc_iqr = fsc_q3 - fsc_q1
            ssc_iqr = ssc_q3 - ssc_q1
            
            fsc_lower, fsc_upper = fsc_q1 - iqr_factor * fsc_iqr, fsc_q3 + iqr_factor * fsc_iqr
            ssc_lower, ssc_upper = ssc_q1 - iqr_factor * ssc_iqr, ssc_q3 + iqr_factor * ssc_iqr
            
            iqr_outliers = np.where(
                (fsc_values < fsc_lower) | (fsc_values > fsc_upper) |
                (ssc_values < ssc_lower) | (ssc_values > ssc_upper)
            )[0]
            anomalous_indices.update(iqr_outliers.tolist())
        
        anomalous_list = sorted(list(anomalous_indices))
        total_events = len(parsed_data)
        anomaly_percentage = (len(anomalous_list) / total_events * 100) if total_events > 0 else 0
        
        logger.success(
            f"✅ Anomaly detection for {sample_id}: "
            f"{len(anomalous_list)} anomalies ({anomaly_percentage:.2f}%)"
        )
        
        return {
            "sample_id": sample_id,
            "enabled": True,
            "method": method,
            "total_anomalies": len(anomalous_list),
            "anomaly_percentage": round(anomaly_percentage, 2),
            "anomalous_indices": anomalous_list,
            "settings": {
                "zscore_threshold": zscore_threshold,
                "iqr_factor": iqr_factor
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed anomaly detection for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed anomaly detection: {str(e)}"
        )


# ============================================================================
# Re-analyze Sample Endpoint
# ============================================================================

from pydantic import BaseModel, Field


class ReanalyzeRequest(BaseModel):
    """Request body for re-analyzing a sample with custom settings."""
    wavelength_nm: float = Field(default=405.0, ge=200, le=800, description="Laser wavelength in nm")
    n_particle: float = Field(default=1.37, ge=1.0, le=2.0, description="Particle refractive index")
    n_medium: float = Field(default=1.33, ge=1.0, le=2.0, description="Medium refractive index")
    anomaly_detection: bool = Field(default=False, description="Enable anomaly detection")
    anomaly_method: str = Field(default="zscore", description="Anomaly method: zscore, iqr, both")
    zscore_threshold: float = Field(default=3.0, ge=1.0, le=10.0, description="Z-score threshold")
    iqr_factor: float = Field(default=1.5, ge=1.0, le=5.0, description="IQR factor for outlier detection")
    fsc_angle_range: Optional[list[float]] = Field(
        default=None,
        description="Forward scatter collection angle range in degrees, e.g. [0.5, 15]"
    )
    ssc_angle_range: Optional[list[float]] = Field(
        default=None,
        description="Side scatter collection angle range in degrees, e.g. [15, 150]"
    )
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
        
        # Parse FCS file (cached)
        from src.utils.fcs_cache import get_cached_fcs_data
        import numpy as np
        
        parsed_data, channels = get_cached_fcs_data(sample.file_path_fcs)
        stats = {}  # Statistics computed inline when needed
        
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
        
        # Get statistics for detected channels (computed inline since we use cached parser data)
        def _channel_stats(df, col):
            if col and col in df.columns:
                s = df[col]
                return {'mean': float(s.mean()), 'median': float(s.median()), 'std': float(s.std()), 'min': float(s.min()), 'max': float(s.max())}
            return {}
        fsc_stats = _channel_stats(parsed_data, fsc_channel)
        ssc_stats = _channel_stats(parsed_data, ssc_channel)
        
        # Check for multi-solution Mie capability
        multi_solution_info = detect_multi_solution_channels(channels)
        can_use_multi_solution = (
            multi_solution_info['can_use_multi_solution'] and
            multi_solution_info['vssc_channel'] in parsed_data.columns and
            multi_solution_info['bssc_channel'] in parsed_data.columns
        )
        
        # Calculate particle size and size distribution
        particle_size_median_nm = None
        size_distribution = None
        custom_bins = {}
        sizing_method = None
        
        # === BEAD-CALIBRATED PATH (highest priority, same as upload) ===
        active_calibration = None
        fcmpass_calibration = None
        try:
            from src.physics.bead_calibration import get_active_calibration, get_fcmpass_calibration
            active_calibration = get_active_calibration()
            fcmpass_calibration = get_fcmpass_calibration()
        except Exception:
            pass
        
        if fcmpass_calibration and fcmpass_calibration.calibrated:
            try:
                # If user requested a different EV RI, update the LUT
                if abs(fcmpass_calibration.n_ev - request.n_particle) > 1e-6:
                    fcmpass_calibration.update_ev_ri(request.n_particle)
                logger.info(
                    f"🎯 Re-analyze using FCMPASS k-based sizing: "
                    f"k={fcmpass_calibration.k_instrument:.1f}, RI_ev={fcmpass_calibration.n_ev}"
                )
                sizing_method = "fcmpass_k_based"
                
                cal_channel = ssc_channel
                if multi_solution_info.get('vssc_channel') and multi_solution_info['vssc_channel'] in parsed_data.columns:
                    cal_channel = multi_solution_info['vssc_channel']
                
                sample_size = min(10000, len(parsed_data))
                np.random.seed(42)
                sample_indices = np.random.choice(len(parsed_data), size=sample_size, replace=False)
                scatter_sample = np.asarray(parsed_data[cal_channel].values[sample_indices], dtype=np.float64)
                
                pos_mask = scatter_sample > 0
                if np.sum(pos_mask) > 0:
                    cal_diameters, in_range = fcmpass_calibration.predict_batch(scatter_sample[pos_mask])
                    valid_cal = cal_diameters[~np.isnan(cal_diameters) & (cal_diameters > 0)]
                    
                    if len(valid_cal) > 0:
                        particle_size_median_nm = float(np.median(valid_cal))
                        size_distribution = {
                            'd10': float(np.percentile(valid_cal, 10)),
                            'd50': float(np.percentile(valid_cal, 50)),
                            'd90': float(np.percentile(valid_cal, 90)),
                            'mean': float(np.mean(valid_cal)),
                            'std': float(np.std(valid_cal))
                        }
                        
                        scale_factor = len(parsed_data) / sample_size
                        for range_def in request.size_ranges:
                            name = range_def.get('name', f"{range_def['min']}-{range_def['max']}nm")
                            min_size = range_def.get('min', 0)
                            max_size = range_def.get('max', 1000)
                            count = np.sum((valid_cal >= min_size) & (valid_cal < max_size))
                            custom_bins[name] = {
                                'count': int(count * scale_factor),
                                'percentage': float(count / len(valid_cal) * 100) if len(valid_cal) > 0 else 0
                            }
                        logger.info(f"📐 FCMPASS: {len(valid_cal)} valid diameters, median={particle_size_median_nm:.1f}nm")
            except Exception as fcmpass_err:
                logger.warning(f"⚠️ FCMPASS calibration failed in reanalyze, falling back: {fcmpass_err}")
                fcmpass_calibration = None  # Fall through to legacy bead cal
        
        if particle_size_median_nm is None and active_calibration and active_calibration.is_fitted:
            try:
                logger.info(f"🎯 Re-analyze using LEGACY bead-calibrated sizing")
                sizing_method = "bead_calibrated"
                
                cal_channel = ssc_channel
                # Prefer VSSC for violet-calibrated curves
                if multi_solution_info.get('vssc_channel') and multi_solution_info['vssc_channel'] in parsed_data.columns:
                    cal_channel = multi_solution_info['vssc_channel']
                
                sample_size = min(10000, len(parsed_data))
                np.random.seed(42)
                sample_indices = np.random.choice(len(parsed_data), size=sample_size, replace=False)
                scatter_sample = np.asarray(parsed_data[cal_channel].values[sample_indices], dtype=np.float64)
                
                pos_mask = scatter_sample > 0
                if np.sum(pos_mask) > 0:
                    cal_diameters = active_calibration.diameter_from_fsc(
                        scatter_sample[pos_mask],
                        target_ri=request.n_particle,  # Phase 5: RI correction
                        medium_ri=request.n_medium,
                    )
                    valid_cal = cal_diameters[~np.isnan(cal_diameters) & (cal_diameters > 0)]
                    
                    if len(valid_cal) > 0:
                        particle_size_median_nm = float(np.median(valid_cal))
                        size_distribution = {
                            'd10': float(np.percentile(valid_cal, 10)),
                            'd50': float(np.percentile(valid_cal, 50)),
                            'd90': float(np.percentile(valid_cal, 90)),
                            'mean': float(np.mean(valid_cal)),
                            'std': float(np.std(valid_cal))
                        }
                        
                        scale_factor = len(parsed_data) / sample_size
                        for range_def in request.size_ranges:
                            name = range_def.get('name', f"{range_def['min']}-{range_def['max']}nm")
                            min_size = range_def.get('min', 0)
                            max_size = range_def.get('max', 1000)
                            count = np.sum((valid_cal >= min_size) & (valid_cal < max_size))
                            custom_bins[name] = {
                                'count': int(count * scale_factor),
                                'percentage': float(count / len(valid_cal) * 100) if len(valid_cal) > 0 else 0
                            }
                        logger.info(f"📐 Bead-calibrated: {len(valid_cal)} valid diameters, median={particle_size_median_nm:.1f}nm")
            except Exception as cal_err:
                logger.warning(f"⚠️ Bead calibration failed in reanalyze, falling back: {cal_err}")
                active_calibration = None  # Fall through to Mie methods
        
        if particle_size_median_nm is None and can_use_multi_solution:
            # === MULTI-SOLUTION MIE (PREFERRED) ===
            from src.physics.mie_scatter import MultiSolutionMieCalculator
            
            vssc_ch = multi_solution_info['vssc_channel']
            bssc_ch = multi_solution_info['bssc_channel']
            
            logger.info(f"🔬 Re-analyze using MULTI-SOLUTION Mie: VSSC={vssc_ch}, BSSC={bssc_ch}")
            
            from src.physics.bead_calibration import get_fcmpass_k_factor
            _k = get_fcmpass_k_factor()
            multi_mie_calc = MultiSolutionMieCalculator(
                n_particle=request.n_particle, 
                n_medium=request.n_medium,
                k_violet=_k,
            )
            
            # Sample for performance
            sample_size = min(10000, len(parsed_data))
            np.random.seed(42)
            sample_indices = np.random.choice(len(parsed_data), size=sample_size, replace=False)
            
            # Get SSC values for both wavelengths
            ssc_violet = np.asarray(parsed_data[vssc_ch].values[sample_indices], dtype=np.float64)
            ssc_blue = np.asarray(parsed_data[bssc_ch].values[sample_indices], dtype=np.float64)
            
            # Calculate sizes with disambiguation
            sizes_array, num_solutions = multi_mie_calc.calculate_sizes_multi_solution(ssc_blue, ssc_violet)
            valid_sizes = sizes_array[~np.isnan(sizes_array) & (sizes_array > 0)]
            
            if len(valid_sizes) > 0:
                particle_size_median_nm = float(np.median(valid_sizes))
                size_distribution = {
                    'd10': float(np.percentile(valid_sizes, 10)),
                    'd50': float(np.percentile(valid_sizes, 50)),
                    'd90': float(np.percentile(valid_sizes, 90)),
                    'mean': float(np.mean(valid_sizes)),
                    'std': float(np.std(valid_sizes))
                }
                
                # Calculate custom size range bins
                scale_factor = len(parsed_data) / sample_size
                for range_def in request.size_ranges:
                    name = range_def.get('name', f"{range_def['min']}-{range_def['max']}nm")
                    min_size = range_def.get('min', 0)
                    max_size = range_def.get('max', 1000)
                    count = np.sum((valid_sizes >= min_size) & (valid_sizes < max_size))
                    custom_bins[name] = {
                        'count': int(count * scale_factor),
                        'percentage': float(count / len(valid_sizes) * 100) if len(valid_sizes) > 0 else 0
                    }
        
        if particle_size_median_nm is None and not can_use_multi_solution:
            # === SINGLE-SOLUTION MIE (FALLBACK) ===
            from src.physics.mie_scatter import MieScatterCalculator
            mie_calc = MieScatterCalculator(
                wavelength_nm=request.wavelength_nm,
                n_particle=request.n_particle,
                n_medium=request.n_medium,
                fsc_angle_range=request.fsc_angle_range,
                ssc_angle_range=request.ssc_angle_range
            )
            sizing_method = "single_mie"
            logger.info(f"🔬 Re-analyze using single-solution Mie: λ={request.wavelength_nm}nm")
            
            # Calculate particle size from FSC median
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
            
            # Calculate size distribution using batch operation for performance
            if fsc_channel and fsc_channel in parsed_data.columns:
                try:
                    # Sample for performance
                    sample_size = min(10000, len(parsed_data))
                    sampled_fsc = parsed_data[fsc_channel].sample(n=sample_size, random_state=42).values
                    
                    # Use batch diameter calculation (100-1000× faster than per-event loop)
                    fsc_array = np.asarray(sampled_fsc, dtype=np.float64)
                    sizes_array, success_mask = mie_calc.diameters_from_scatter_normalized(
                        fsc_intensities=fsc_array,
                        min_diameter=10.0,
                        max_diameter=500.0
                    )
                    valid_sizes = sizes_array[success_mask & (sizes_array > 0)]
                    
                    if len(valid_sizes) > 0:
                        particle_size_median_nm = float(np.median(valid_sizes))
                        size_distribution = {
                            'd10': float(np.percentile(valid_sizes, 10)),
                            'd50': float(np.percentile(valid_sizes, 50)),
                            'd90': float(np.percentile(valid_sizes, 90)),
                            'mean': float(np.mean(valid_sizes)),
                            'std': float(np.std(valid_sizes))
                        }
                        
                        # Calculate custom size range bins
                        scale_factor = len(parsed_data) / sample_size
                        for range_def in request.size_ranges:
                            name = range_def.get('name', f"{range_def['min']}-{range_def['max']}nm")
                            min_size = range_def.get('min', 0)
                            max_size = range_def.get('max', 1000)
                            count = np.sum((valid_sizes >= min_size) & (valid_sizes < max_size))
                            custom_bins[name] = {
                                'count': int(count * scale_factor),
                                'percentage': float(count / len(valid_sizes) * 100) if len(valid_sizes) > 0 else 0
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
                'sizing_method': sizing_method or ('multi_mie' if can_use_multi_solution else 'single_mie'),
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


# ============================================================================
# Experimental Conditions Endpoints (TASK-009)
# ============================================================================

from pydantic import BaseModel
from src.database.crud import (
    create_experimental_conditions,
    get_experimental_conditions_by_sample,
    update_experimental_conditions as update_conditions_db,
)


class ExperimentalConditionsCreate(BaseModel):
    """Request model for creating experimental conditions."""
    operator: str
    temperature_celsius: Optional[float] = None
    ph: Optional[float] = None
    substrate_buffer: Optional[str] = None
    custom_buffer: Optional[str] = None
    sample_volume_ul: Optional[float] = None
    dilution_factor: Optional[int] = None
    antibody_used: Optional[str] = None
    antibody_concentration_ug: Optional[float] = None
    incubation_time_min: Optional[float] = None
    sample_type: Optional[str] = None
    filter_size_um: Optional[float] = None
    notes: Optional[str] = None


class ExperimentalConditionsUpdate(BaseModel):
    """Request model for updating experimental conditions."""
    operator: Optional[str] = None
    temperature_celsius: Optional[float] = None
    ph: Optional[float] = None
    substrate_buffer: Optional[str] = None
    custom_buffer: Optional[str] = None
    sample_volume_ul: Optional[float] = None
    dilution_factor: Optional[int] = None
    antibody_used: Optional[str] = None
    antibody_concentration_ug: Optional[float] = None
    incubation_time_min: Optional[float] = None
    sample_type: Optional[str] = None
    filter_size_um: Optional[float] = None
    notes: Optional[str] = None


class ManualMetadataUpsert(BaseModel):
    """Manual metadata fallback payload for FCS metadata resolution."""
    laser_wavelength_nm: Optional[int] = None
    dilution_factor: Optional[int] = None
    instrument_model: Optional[str] = None
    operator_notes: Optional[str] = None


async def _get_sample_dilution_factor(db: AsyncSession, sample_db_id: int) -> Optional[int]:
    """Get dilution factor from experimental conditions for the sample."""
    conditions = await get_experimental_conditions_by_sample(db, sample_db_id)
    if not conditions:
        return None
    dilution = getattr(conditions, "dilution_factor", None)
    if dilution is None:
        return None
    try:
        dilution_i = int(dilution)
        return dilution_i if dilution_i > 0 else None
    except Exception:
        return None


@router.post("/{sample_id}/conditions", response_model=dict)
async def save_experimental_conditions(
    sample_id: str,
    conditions: ExperimentalConditionsCreate,
    db: AsyncSession = Depends(get_session)
):
    """
    Save experimental conditions for a sample.
    
    TASK-009: Store experimental metadata for reproducibility and AI analysis.
    
    **Request Body:**
    ```json
    {
        "operator": "John Doe",
        "temperature_celsius": 22.5,
        "substrate_buffer": "PBS",
        "antibody_used": "CD81",
        "antibody_concentration_ug": 1.0,
        "incubation_time_min": 30,
        "notes": "Standard protocol"
    }
    ```
    
    **Response:**
    ```json
    {
        "success": true,
        "conditions_id": 1,
        "sample_id": "P5_F10_CD81",
        "message": "Experimental conditions saved successfully"
    }
    ```
    """
    logger.info(f"📝 Saving experimental conditions for sample: {sample_id}")
    
    try:
        # Find sample by sample_id string
        query = select(Sample).where(Sample.sample_id == sample_id)
        result = await db.execute(query)
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample not found: {sample_id}"
            )
        
        # Create experimental conditions
        conditions_record = await create_experimental_conditions(
            db=db,
            sample_id=sample.id,  # type: ignore[arg-type]
            operator=conditions.operator,
            temperature_celsius=conditions.temperature_celsius,
            ph=conditions.ph,
            substrate_buffer=conditions.substrate_buffer,
            custom_buffer=conditions.custom_buffer,
            sample_volume_ul=conditions.sample_volume_ul,
            dilution_factor=conditions.dilution_factor,
            antibody_used=conditions.antibody_used,
            antibody_concentration_ug=conditions.antibody_concentration_ug,
            incubation_time_min=conditions.incubation_time_min,
            sample_type=conditions.sample_type,
            filter_size_um=conditions.filter_size_um,
            notes=conditions.notes,
        )
        
        logger.success(f"✅ Saved experimental conditions for sample {sample_id}")
        
        return {
            "success": True,
            "conditions_id": conditions_record.id,
            "sample_id": sample_id,
            "conditions": conditions_record.to_dict(),
            "message": "Experimental conditions saved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to save conditions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save experimental conditions: {str(e)}"
        )


@router.get("/{sample_id}/conditions", response_model=dict)
async def get_experimental_conditions(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get experimental conditions for a sample.
    
    **Response:**
    ```json
    {
        "sample_id": "P5_F10_CD81",
        "conditions": {
            "id": 1,
            "operator": "John Doe",
            "temperature_celsius": 22.5,
            ...
        }
    }
    ```
    """
    try:
        # Find sample by sample_id string
        query = select(Sample).where(Sample.sample_id == sample_id)
        result = await db.execute(query)
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample not found: {sample_id}"
            )
        
        # Get conditions
        conditions = await get_experimental_conditions_by_sample(db, sample.id)  # type: ignore[arg-type]
        
        return {
            "sample_id": sample_id,
            "has_conditions": conditions is not None,
            "conditions": conditions.to_dict() if conditions else None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get conditions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get experimental conditions: {str(e)}"
        )


@router.put("/{sample_id}/conditions", response_model=dict)
async def update_experimental_conditions(
    sample_id: str,
    conditions: ExperimentalConditionsUpdate,
    db: AsyncSession = Depends(get_session)
):
    """
    Update experimental conditions for a sample.
    """
    logger.info(f"📝 Updating experimental conditions for sample: {sample_id}")
    
    try:
        # Find sample
        query = select(Sample).where(Sample.sample_id == sample_id)
        result = await db.execute(query)
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample not found: {sample_id}"
            )
        
        # Get existing conditions
        existing = await get_experimental_conditions_by_sample(db, sample.id)  # type: ignore[arg-type]
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No experimental conditions found for sample: {sample_id}"
            )
        
        # Build update dict (only non-None values)
        update_data = conditions.model_dump(exclude_unset=True)
        
        # Update conditions
        updated = await update_conditions_db(db, existing.id, **update_data)  # type: ignore[arg-type]
        
        return {
            "success": True,
            "sample_id": sample_id,
            "conditions": updated.to_dict() if updated else None,
            "message": "Experimental conditions updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to update conditions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update experimental conditions: {str(e)}"
        )


@router.get("/{sample_id}/available-channels", response_model=dict)
async def get_available_channels(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get available channels for a specific FCS sample.
    
    Returns all channel names from the FCS file with statistics to help identify
    FSC/SSC channels.
    """
    try:
        # Get sample
        result = await db.execute(
            select(Sample).where(Sample.sample_id == sample_id)
        )
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample not found: {sample_id}"
            )
        
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        from src.utils.fcs_cache import get_cached_fcs_data  # type: ignore[import-not-found]
        from src.utils.channel_config import get_channel_config  # type: ignore[import-not-found]
        import numpy as np
        
        parsed_data, _channels = get_cached_fcs_data(sample.file_path_fcs)
        
        config = get_channel_config()
        
        # Build channel info with statistics
        channels_info = []
        for i, col in enumerate(parsed_data.columns):
            if col in ['sample_id', 'biological_sample_id', 'measurement_id', 
                       'is_baseline', 'file_name', 'instrument_type', 'parse_timestamp']:
                continue
            
            mean_val = parsed_data[col].mean()
            max_val = parsed_data[col].max()
            min_val = parsed_data[col].min()
            std_val = parsed_data[col].std()
            
            # Check if this is a detected FSC/SSC channel
            is_fsc = col in config.get_fsc_channel_names()
            is_ssc = col in config.get_ssc_channel_names()
            
            channels_info.append({
                "index": i + 1,
                "name": col,
                "mean": float(mean_val),
                "max": float(max_val),
                "min": float(min_val),
                "std": float(std_val),
                "cv": float(std_val / mean_val * 100) if mean_val > 0 else 0,
                "is_configured_fsc": is_fsc,
                "is_configured_ssc": is_ssc
            })
        
        # Detect channels based on config
        detected_fsc = config.detect_fsc_channel(_channels)
        detected_ssc = config.detect_ssc_channel(_channels)
        
        return {
            "sample_id": sample_id,
            "file_name": sample.file_path_fcs.name if sample.file_path_fcs else None,
            "total_events": len(parsed_data),
            "channels": channels_info,
            "detected_fsc": detected_fsc,
            "detected_ssc": detected_ssc,
            "active_instrument": config.active_instrument,
            "recommendation": (
                f"For accurate EV sizing, configure FSC={detected_fsc or 'Channel_5'} "
                f"and SSC={detected_ssc or 'Channel_6'}"
            ) if not detected_fsc or not detected_ssc else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get available channels: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available channels: {str(e)}"
        )


async def _build_metadata_resolution_payload(db: AsyncSession, sample: Sample) -> Dict[str, Any]:
    """Build resolved metadata payload with provenance for a sample."""
    if not sample.file_path_fcs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No FCS file associated with sample {sample.sample_id}"
        )

    from src.parsers.fcs_parser import FCSParser

    parser = FCSParser(sample.file_path_fcs)
    parser.parse()
    fcs_metadata = parser.extract_metadata()
    channel_names = fcs_metadata.get("channel_names", []) or []

    sidecar_path = _find_fcs_sidecar_xml(str(sample.file_path_fcs))
    sidecar_data = _extract_sidecar_metadata(sidecar_path) if sidecar_path else {
        "laser_wavelength_nm": None,
        "instrument_model": None,
    }

    overrides = _extract_metadata_overrides_from_notes(sample.notes)
    dilution_factor = await _get_sample_dilution_factor(db, sample.id)

    resolved, provenance, missing_required, completeness_score = _resolve_sample_metadata(
        fcs_metadata=fcs_metadata,
        channel_names=channel_names,
        sidecar_data=sidecar_data,
        overrides=overrides,
        dilution_factor=dilution_factor,
    )

    return {
        "sample_id": sample.sample_id,
        "resolved": resolved,
        "provenance": provenance,
        "completeness_score": completeness_score,
        "missing_required": missing_required,
        "sources": {
            "sidecar_xml_path": str(sidecar_path) if sidecar_path else None,
            "has_manual_overrides": bool(overrides),
            "has_experimental_conditions": dilution_factor is not None,
        },
        "fcs_metadata_snapshot": {
            "acquisition_date": fcs_metadata.get("acquisition_date"),
            "acquisition_time": fcs_metadata.get("acquisition_time"),
            "cytometer": fcs_metadata.get("cytometer"),
            "operator": fcs_metadata.get("operator"),
            "channel_count": fcs_metadata.get("channel_count"),
            "channel_names": channel_names,
        }
    }


@router.get("/{sample_id}/metadata-resolution", response_model=dict)
async def get_metadata_resolution(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    VAL-005: Resolve FCS critical metadata with explicit provenance.

    Priority used:
    manual override > FCS header/channel inference > sidecar XML > missing.
    """
    try:
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()

        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample {sample_id} not found"
            )

        return await _build_metadata_resolution_payload(db, sample)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to resolve metadata for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve metadata: {str(e)}"
        )


@router.post("/{sample_id}/metadata/manual", response_model=dict)
async def upsert_manual_metadata(
    sample_id: str,
    payload: ManualMetadataUpsert,
    db: AsyncSession = Depends(get_session)
):
    """
    VAL-005: Persist manual metadata fallback values for a sample.

    - laser_wavelength_nm and instrument_model are saved as sample-level overrides in notes.
    - dilution_factor is persisted in experimental_conditions.
    """
    try:
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()

        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample {sample_id} not found"
            )

        # 1) Persist dilution factor through experimental conditions table.
        if payload.dilution_factor is not None:
            existing_conditions = await get_experimental_conditions_by_sample(db, sample.id)  # type: ignore[arg-type]
            if existing_conditions:
                await update_conditions_db(
                    db,
                    existing_conditions.id,
                    dilution_factor=int(payload.dilution_factor),
                    notes=payload.operator_notes or existing_conditions.notes,
                )
            else:
                await create_experimental_conditions(
                    db=db,
                    sample_id=sample.id,  # type: ignore[arg-type]
                    operator="Manual Metadata Entry",
                    dilution_factor=int(payload.dilution_factor),
                    notes=payload.operator_notes,
                )

        # 2) Persist manual override JSON in sample.notes.
        existing_overrides = _extract_metadata_overrides_from_notes(sample.notes)
        if payload.laser_wavelength_nm is not None:
            existing_overrides["laser_wavelength_nm"] = int(payload.laser_wavelength_nm)
        if payload.instrument_model:
            existing_overrides["instrument_model"] = payload.instrument_model.strip()
        if payload.dilution_factor is not None:
            existing_overrides["dilution_factor"] = int(payload.dilution_factor)

        if existing_overrides:
            sample.notes = _upsert_metadata_overrides_in_notes(sample.notes, existing_overrides)

        await db.commit()

        refreshed = await _build_metadata_resolution_payload(db, sample)
        return {
            "success": True,
            "sample_id": sample_id,
            "message": "Manual metadata saved successfully",
            "metadata_resolution": refreshed,
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"❌ Failed to save manual metadata for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save manual metadata: {str(e)}"
        )


# ============================================================================
# FCS Data Split - Metadata and Values (Per-Event Sizes)
# ============================================================================

@router.get("/{sample_id}/fcs/metadata", response_model=dict)
async def get_fcs_metadata(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get FCS file metadata only (no event data).
    
    Returns instrument settings, channel info, acquisition details.
    """
    try:
        # Get sample from database
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample {sample_id} not found"
            )
        
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        # Parse FCS file (cached) + get metadata
        from src.parsers.fcs_parser import FCSParser
        parser = FCSParser(sample.file_path_fcs)
        parser.parse()  # metadata extraction needs parser instance
        
        # Extract metadata
        metadata = parser.extract_metadata()
        
        # Add file-level info
        import os
        file_stat = os.stat(sample.file_path_fcs)
        
        return {
            "sample_id": sample_id,
            "file_info": {
                "file_name": sample.file_path_fcs.name if hasattr(sample.file_path_fcs, 'name') else str(sample.file_path_fcs).split('/')[-1],
                "file_size_bytes": file_stat.st_size,
                "file_size_mb": round(file_stat.st_size / (1024 * 1024), 2),
            },
            "acquisition": {
                "date": metadata.get('acquisition_date', 'Unknown'),
                "time": metadata.get('acquisition_time', 'Unknown'),
                "cytometer": metadata.get('cytometer', 'Unknown'),
                "operator": metadata.get('operator', 'Unknown'),
                "specimen": metadata.get('specimen', 'Unknown'),
            },
            "data_info": {
                "total_events": metadata.get('total_events', 0),
                "parameter_count": metadata.get('parameters', 0),
                "channel_count": metadata.get('channel_count', 0),
                "channel_names": metadata.get('channel_names', []),
            },
            "channels": metadata.get('channels', {}),
            "identifiers": {
                "sample_id": metadata.get('sample_id'),
                "biological_sample_id": metadata.get('biological_sample_id'),
                "measurement_id": metadata.get('measurement_id'),
                "is_baseline": metadata.get('is_baseline', False),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get FCS metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get FCS metadata: {str(e)}"
        )


@router.get("/{sample_id}/fcs/values", response_model=dict)
async def get_fcs_values(
    sample_id: str,
    wavelength_nm: float = Query(405.0, description="Laser wavelength in nm"),
    n_particle: float = Query(1.37, description="Particle refractive index"),
    n_medium: float = Query(1.33, description="Medium refractive index"),
    max_events: int = Query(50000, ge=1, le=500000, description="Maximum events to return"),
    include_raw_channels: bool = Query(False, description="Include raw FSC/SSC channel values"),
    db: AsyncSession = Depends(get_session)
):
    """
    Get FCS per-event size values calculated using Mie theory.
    
    Returns particle diameter (nm) for each event calculated from FSC using Mie scattering.
    
    **Parameters:**
    - wavelength_nm: Laser wavelength (default: 405nm)
    - n_particle: Particle refractive index (default: 1.37 for EVs)
    - n_medium: Medium refractive index (default: 1.33 for PBS)
    - max_events: Maximum number of events to return (default: 50000)
    - include_raw_channels: If true, include raw FSC/SSC values
    
    **Response:**
    Returns per-event size data and summary statistics.
    """
    try:
        # Get sample from database
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample {sample_id} not found"
            )
        
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        logger.info(f"📊 Getting FCS values for {sample_id} with Mie params: λ={wavelength_nm}nm, n_p={n_particle}, n_m={n_medium}")
        
        # Parse FCS file (cached)
        from src.utils.fcs_cache import get_cached_fcs_data
        from src.utils.channel_config import ChannelConfig
        import numpy as np
        
        parsed_data, channels = get_cached_fcs_data(sample.file_path_fcs)
        
        # Detect FSC channel
        config = ChannelConfig()
        fsc_channel = config.detect_fsc_channel(channels)
        ssc_channel = config.detect_ssc_channel(channels)
        
        if not fsc_channel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No FSC channel detected - cannot calculate particle sizes"
            )
        
        # Sample events if needed
        total_events = len(parsed_data)
        if total_events > max_events:
            np.random.seed(42)
            sample_indices = np.random.choice(total_events, size=max_events, replace=False)
            sampled_data = parsed_data.iloc[sample_indices].reset_index(drop=True)
            sampled = True
        else:
            sampled_data = parsed_data
            sample_indices = np.arange(total_events)
            sampled = False
        
        # Check for multi-solution Mie capability
        multi_solution_info = detect_multi_solution_channels(channels)
        can_use_multi_solution = (
            multi_solution_info['can_use_multi_solution'] and
            multi_solution_info['vssc_channel'] in sampled_data.columns and
            multi_solution_info['bssc_channel'] in sampled_data.columns
        )
        
        # Get FSC values
        fsc_values = sampled_data[fsc_channel].values
        
        if can_use_multi_solution:
            # === MULTI-SOLUTION MIE (PREFERRED) ===
            from src.physics.mie_scatter import MultiSolutionMieCalculator
            
            vssc_ch = multi_solution_info['vssc_channel']
            bssc_ch = multi_solution_info['bssc_channel']
            
            logger.info(f"🔬 FCS values using MULTI-SOLUTION Mie: VSSC={vssc_ch}, BSSC={bssc_ch}")
            
            from src.physics.bead_calibration import get_fcmpass_k_factor
            _k = get_fcmpass_k_factor()
            multi_mie_calc = MultiSolutionMieCalculator(n_particle=n_particle, n_medium=n_medium, k_violet=_k)
            
            # Get SSC values for both wavelengths
            ssc_violet = np.asarray(sampled_data[vssc_ch].values, dtype=np.float64)
            ssc_blue = np.asarray(sampled_data[bssc_ch].values, dtype=np.float64)
            
            # Calculate sizes with disambiguation
            sizes, num_solutions = multi_mie_calc.calculate_sizes_multi_solution(ssc_blue, ssc_violet)
            success_mask = ~np.isnan(sizes) & (sizes > 0)
        else:
            # === SINGLE-SOLUTION MIE (FALLBACK) ===
            from src.physics.mie_scatter import MieScatterCalculator
            mie_calc = MieScatterCalculator(
                wavelength_nm=wavelength_nm,
                n_particle=n_particle,
                n_medium=n_medium
            )
            logger.info(f"🔬 FCS values using single-solution Mie: λ={wavelength_nm}nm")
            
            # Calculate particle sizes using NORMALIZED method
            # This handles the scale mismatch between raw FSC and physical scatter
            sizes, success_mask = mie_calc.diameters_from_scatter_normalized(
                fsc_values, 
                min_diameter=20.0, 
                max_diameter=500.0
            )
        
        # Filter valid sizes
        valid_sizes = sizes[success_mask]
        valid_fsc = fsc_values[success_mask]
        
        # Build response
        event_data = []
        for i, (size, fsc) in enumerate(zip(sizes, fsc_values)):
            event_entry = {
                "event_id": i,
                "diameter_nm": float(size) if success_mask[i] else None,
                "valid": bool(success_mask[i]),
            }
            if include_raw_channels:
                event_entry["fsc"] = float(fsc)
                if ssc_channel:
                    event_entry["ssc"] = float(sampled_data.iloc[i][ssc_channel])
            event_data.append(event_entry)
        
        # Calculate statistics
        if len(valid_sizes) > 0:
            size_stats = {
                "count": int(len(valid_sizes)),
                "mean_nm": float(np.mean(valid_sizes)),
                "median_nm": float(np.median(valid_sizes)),
                "std_nm": float(np.std(valid_sizes)),
                "min_nm": float(np.min(valid_sizes)),
                "max_nm": float(np.max(valid_sizes)),
                "d10_nm": float(np.percentile(valid_sizes, 10)),
                "d50_nm": float(np.percentile(valid_sizes, 50)),
                "d90_nm": float(np.percentile(valid_sizes, 90)),
            }
            
            # Size distribution bins
            bins = [0, 50, 100, 150, 200, 300, 500, 1000]
            bin_labels = ["<50", "50-100", "100-150", "150-200", "200-300", "300-500", ">500"]
            hist, _ = np.histogram(valid_sizes, bins=bins)
            size_distribution = {label: int(count) for label, count in zip(bin_labels, hist)}
        else:
            size_stats = None
            size_distribution = None
        
        return {
            "sample_id": sample_id,
            "mie_parameters": {
                "wavelength_nm": wavelength_nm,
                "n_particle": n_particle,
                "n_medium": n_medium,
            },
            "data_info": {
                "total_events": total_events,
                "returned_events": len(sampled_data),
                "valid_sizes": int(np.sum(success_mask)),
                "invalid_sizes": int(np.sum(~success_mask)),
                "sampled": sampled,
                "fsc_channel": fsc_channel,
                "ssc_channel": ssc_channel,
            },
            "statistics": size_stats,
            "size_distribution": size_distribution,
            "events": event_data,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get FCS values: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get FCS values: {str(e)}"
        )


@router.get("/{sample_id}/multi-solution-events", response_model=dict)
async def get_multi_solution_events(
    sample_id: str,
    max_events: int = Query(200, ge=1, le=2000, description="Max ambiguous events to return"),
    min_solutions: int = Query(2, ge=2, le=10, description="Minimum candidate solutions per event"),
    tolerance_pct: float = Query(15.0, ge=1.0, le=50.0, description="Solution matching tolerance"),
    include_raw_signals: bool = Query(False, description="Include raw SSC values in response"),
    use_violet_primary: bool = Query(True, description="Use 405nm channel as primary solver"),
    db: AsyncSession = Depends(get_session)
):
    """
    VAL-010: Return events with multiple Mie size candidates and selection diagnostics.
    """
    try:
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        if not sample:
            raise HTTPException(status_code=404, detail=f"Sample {sample_id} not found")
        if not sample.file_path_fcs:
            raise HTTPException(status_code=404, detail=f"No FCS file associated with sample {sample_id}")

        from src.utils.fcs_cache import get_cached_fcs_data
        from src.physics.mie_scatter import MultiSolutionMieCalculator
        from src.physics.bead_calibration import get_fcmpass_k_factor

        parsed_data, channels = get_cached_fcs_data(sample.file_path_fcs)
        multi_info = detect_multi_solution_channels(channels)
        if not multi_info["can_use_multi_solution"]:
            raise HTTPException(
                status_code=400,
                detail="Sample does not contain both VSSC and BSSC channels required for multi-solution diagnostics"
            )

        vssc_ch = multi_info["vssc_channel"]
        bssc_ch = multi_info["bssc_channel"]
        if vssc_ch not in parsed_data.columns or bssc_ch not in parsed_data.columns:
            raise HTTPException(status_code=400, detail="Required VSSC/BSSC channels missing from parsed data")

        _k = get_fcmpass_k_factor()
        calc = MultiSolutionMieCalculator(n_particle=1.37, n_medium=1.33, k_violet=_k)

        ssc_violet = np.asarray(parsed_data[vssc_ch].values, dtype=np.float64)
        ssc_blue = np.asarray(parsed_data[bssc_ch].values, dtype=np.float64)
        sizes, num_solutions = calc.calculate_sizes_multi_solution(
            ssc_blue,
            ssc_violet,
            tolerance_pct=tolerance_pct,
            use_violet_primary=use_violet_primary,
        )

        # Find candidate events with ambiguity.
        candidate_indices = np.where(num_solutions >= min_solutions)[0]
        if len(candidate_indices) > max_events:
            # Prioritize events with more competing solutions.
            candidate_indices = sorted(candidate_indices, key=lambda i: num_solutions[i], reverse=True)[:max_events]

        events = []
        for idx in candidate_indices:
            diag = _diagnose_multi_solution_event(
                calc=calc,
                ssc_blue_value=float(ssc_blue[idx]),
                ssc_violet_value=float(ssc_violet[idx]),
                tolerance_pct=tolerance_pct,
                use_violet_primary=use_violet_primary,
            )
            if diag["num_solutions"] < min_solutions:
                continue

            event_data = {
                "event_id": int(idx),
                "candidate_solutions_nm": diag["candidate_solutions_nm"],
                "selected_solution_nm": diag["selected_solution_nm"],
                "selection_reason": diag["selection_reason"],
                "scores": {
                    "cross_channel_error": float(diag["candidates"][0]["cross_channel_error"]),
                    "calibration_fit_error": float(diag["candidates"][0]["calibration_fit_error"]),
                    "final_weighted_score": float(diag["candidates"][0]["weighted_score"]),
                },
                "ambiguity_score": diag["ambiguity_score"],
                "num_solutions": int(diag["num_solutions"]),
                "measured_ratio": float(diag["measured_ratio"]),
            }
            if include_raw_signals:
                event_data["signals"] = {
                    "vssc": float(ssc_violet[idx]),
                    "bssc": float(ssc_blue[idx]),
                }
            events.append(event_data)

        return {
            "sample_id": sample_id,
            "total_events_scanned": int(len(parsed_data)),
            "ambiguous_events_found": int((num_solutions >= min_solutions).sum()),
            "channel_mode_used": "violet_primary" if use_violet_primary else "blue_primary",
            "vssc_channel": vssc_ch,
            "bssc_channel": bssc_ch,
            "events": events,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to compute multi-solution events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute multi-solution events: {str(e)}"
        )


@router.get("/{sample_id}/multi-solution-events/{event_id}", response_model=dict)
async def get_multi_solution_event_details(
    sample_id: str,
    event_id: int,
    tolerance_pct: float = Query(15.0, ge=1.0, le=50.0),
    use_violet_primary: bool = Query(True),
    db: AsyncSession = Depends(get_session)
):
    """VAL-010: Return full candidate diagnostics for a single event."""
    try:
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        if not sample:
            raise HTTPException(status_code=404, detail=f"Sample {sample_id} not found")
        if not sample.file_path_fcs:
            raise HTTPException(status_code=404, detail=f"No FCS file associated with sample {sample_id}")

        from src.utils.fcs_cache import get_cached_fcs_data
        from src.physics.mie_scatter import MultiSolutionMieCalculator
        from src.physics.bead_calibration import get_fcmpass_k_factor

        parsed_data, channels = get_cached_fcs_data(sample.file_path_fcs)
        if event_id < 0 or event_id >= len(parsed_data):
            raise HTTPException(status_code=422, detail=f"event_id out of range: {event_id}")

        multi_info = detect_multi_solution_channels(channels)
        if not multi_info["can_use_multi_solution"]:
            raise HTTPException(status_code=400, detail="Sample does not support multi-solution diagnostics")

        vssc_ch = multi_info["vssc_channel"]
        bssc_ch = multi_info["bssc_channel"]
        ssc_violet_value = float(parsed_data.iloc[event_id][vssc_ch])
        ssc_blue_value = float(parsed_data.iloc[event_id][bssc_ch])

        _k = get_fcmpass_k_factor()
        calc = MultiSolutionMieCalculator(n_particle=1.37, n_medium=1.33, k_violet=_k)

        diag = _diagnose_multi_solution_event(
            calc=calc,
            ssc_blue_value=ssc_blue_value,
            ssc_violet_value=ssc_violet_value,
            tolerance_pct=tolerance_pct,
            use_violet_primary=use_violet_primary,
        )

        return {
            "sample_id": sample_id,
            "event_id": event_id,
            "signals": {
                "vssc": ssc_violet_value,
                "bssc": ssc_blue_value,
                "ratio_vb": float(diag["measured_ratio"]),
            },
            "candidates": diag["candidates"],
            "candidate_solutions_nm": diag["candidate_solutions_nm"],
            "selected_diameter_nm": diag["selected_solution_nm"],
            "selection_reason": diag["selection_reason"],
            "ambiguity_score": diag["ambiguity_score"],
            "num_solutions": diag["num_solutions"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to compute multi-solution event details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute multi-solution event details: {str(e)}"
        )


# ============================================================================
# NTA Data Split - Metadata and Values (Size/Concentration)
# ============================================================================

@router.get("/{sample_id}/nta/metadata", response_model=dict)
async def get_nta_metadata(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get NTA file metadata only (no measurement data).
    
    Returns instrument settings, acquisition parameters, sample info.
    """
    try:
        # Get sample from database
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        nta_file_path = None
        
        if sample and sample.file_path_nta:
            nta_file_path = sample.file_path_nta
        else:
            # Fallback: search uploads directory for the NTA file
            # This handles cases where the DB insert failed during upload
            # but the file was saved to disk
            found_path = _find_nta_file_by_sample_id(sample_id)
            if found_path:
                nta_file_path = found_path
                logger.info(f"📂 Found NTA file on disk (not in DB): {found_path}")
            else:
                detail = f"Sample {sample_id} not found" if not sample else f"No NTA file associated with sample {sample_id}"
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=detail
                )
        
        # Parse NTA file
        from src.parsers.nta_parser import NTAParser
        parser = NTAParser(nta_file_path)
        parser.parse()
        
        # Get raw metadata
        raw_metadata = parser.raw_metadata
        
        # Add file-level info
        import os
        from pathlib import Path as PathLib
        file_stat = os.stat(nta_file_path)
        nta_path_obj = PathLib(nta_file_path)
        
        return {
            "sample_id": sample_id,
            "file_info": {
                "file_name": nta_path_obj.name,
                "file_size_bytes": file_stat.st_size,
                "measurement_type": parser.measurement_type,
            },
            "sample_info": {
                "sample_name": raw_metadata.get('sample_name', 'Unknown'),
                "operator": raw_metadata.get('operator', 'Unknown'),
                "experiment": raw_metadata.get('experiment', 'Unknown'),
                "electrolyte": raw_metadata.get('electrolyte', 'Unknown'),
            },
            "instrument": {
                "instrument_serial": raw_metadata.get('instrument_serial', 'Unknown'),
                "cell_serial": raw_metadata.get('cell_serial', 'Unknown'),
                "software_version": raw_metadata.get('software_version', 'Unknown'),
                "sop": raw_metadata.get('sop', 'Unknown'),
            },
            "acquisition": {
                "date": raw_metadata.get('date', 'Unknown'),
                "time": raw_metadata.get('time', 'Unknown'),
                "temperature": float(raw_metadata.get('temperature', 0)) if raw_metadata.get('temperature') else None,
                "viscosity": float(raw_metadata.get('viscosity', 0)) if raw_metadata.get('viscosity') else None,
                "ph": float(raw_metadata.get('ph', 0)) if raw_metadata.get('ph') else None,
                "conductivity": float(raw_metadata.get('conductivity', 0)) if raw_metadata.get('conductivity') else None,
            },
            "measurement_params": {
                "num_positions": int(raw_metadata.get('num_positions', 0)) if raw_metadata.get('num_positions') else None,
                "num_traces": int(raw_metadata.get('num_traces', 0)) if raw_metadata.get('num_traces') else None,
                "sensitivity": float(raw_metadata.get('sensitivity', 0)) if raw_metadata.get('sensitivity') else None,
                "shutter": float(raw_metadata.get('shutter', 0)) if raw_metadata.get('shutter') else None,
                "laser_wavelength": float(raw_metadata.get('laser_wavelength', 0)) if raw_metadata.get('laser_wavelength') else None,
                "dilution": float(raw_metadata.get('dilution', 1)) if raw_metadata.get('dilution') else 1,
                "conc_correction": float(raw_metadata.get('conc_correction', 1)) if raw_metadata.get('conc_correction') else 1,
            },
            "quality": {
                "cell_check_result": raw_metadata.get('cell_check_result', 'Unknown'),
                "detected_particles": int(raw_metadata.get('detected_particles', 0)) if raw_metadata.get('detected_particles') else None,
                "scattering_intensity": float(raw_metadata.get('scattering_intensity', 0)) if raw_metadata.get('scattering_intensity') else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get NTA metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get NTA metadata: {str(e)}"
        )


@router.get("/{sample_id}/nta/values", response_model=dict)
async def get_nta_values(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get NTA size and concentration values.
    
    Returns size distribution data with size (nm) and concentration (particles/mL).
    
    **Response:**
    Returns per-bin size and concentration data along with summary statistics.
    """
    try:
        # Get sample from database
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        nta_file_path = None
        
        if sample and sample.file_path_nta:
            nta_file_path = sample.file_path_nta
        else:
            # Fallback: search uploads directory for the NTA file
            found_path = _find_nta_file_by_sample_id(sample_id)
            if found_path:
                nta_file_path = found_path
                logger.info(f"📂 Found NTA values file on disk (not in DB): {found_path}")
            else:
                detail = f"Sample {sample_id} not found" if not sample else f"No NTA file associated with sample {sample_id}"
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=detail
                )
        
        logger.info(f"📊 Getting NTA values for {sample_id}")
        
        # Parse NTA file
        from src.parsers.nta_parser import NTAParser
        import numpy as np
        
        parser = NTAParser(nta_file_path)
        parsed_data = parser.parse()
        
        # Extract size and concentration columns
        size_col = None
        conc_col = None
        
        # Find size column
        for col in ['size_nm', 'Size (nm)', 'Diameter', 'diameter_nm']:
            if col in parsed_data.columns:
                size_col = col
                break
        
        # Find concentration column
        for col in ['concentration_particles_ml', 'Concentration (particles/mL)', 'concentration_particles_cm3', 'Conc.']:
            if col in parsed_data.columns:
                conc_col = col
                break
        
        if not size_col:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No size column found in NTA data"
            )
        
        # Get values
        sizes = parsed_data[size_col].values
        concentrations = parsed_data[conc_col].values if conc_col else None
        
        # Build per-bin data
        values_data = []
        for i in range(len(sizes)):
            entry = {
                "bin_id": i,
                "size_nm": float(sizes[i]),
            }
            if concentrations is not None:
                entry["concentration_particles_ml"] = float(concentrations[i])
            values_data.append(entry)
        
        # Calculate statistics
        valid_sizes = sizes[~np.isnan(sizes)]
        if conc_col:
            valid_conc = concentrations[~np.isnan(concentrations)]
            # Weight sizes by concentration for proper mean
            total_particles = np.sum(valid_conc)
            if total_particles > 0:
                weighted_mean = np.sum(valid_sizes * valid_conc) / total_particles
            else:
                weighted_mean = np.mean(valid_sizes)
        else:
            valid_conc = None
            weighted_mean = np.mean(valid_sizes)
        
        size_stats = {
            "count": int(len(valid_sizes)),
            "mean_nm": float(np.mean(valid_sizes)),
            "weighted_mean_nm": float(weighted_mean),
            "median_nm": float(np.median(valid_sizes)),
            "std_nm": float(np.std(valid_sizes)),
            "min_nm": float(np.min(valid_sizes)),
            "max_nm": float(np.max(valid_sizes)),
            "mode_nm": float(valid_sizes[np.argmax(valid_conc)]) if valid_conc is not None and len(valid_conc) > 0 else float(np.median(valid_sizes)),
        }
        
        conc_stats = None
        if valid_conc is not None:
            conc_stats = {
                "total_particles_ml": float(np.sum(valid_conc)),
                "max_concentration": float(np.max(valid_conc)),
                "peak_size_nm": float(valid_sizes[np.argmax(valid_conc)]),
            }
        
        return {
            "sample_id": sample_id,
            "measurement_type": parser.measurement_type,
            "data_info": {
                "total_bins": len(parsed_data),
                "size_column": size_col,
                "concentration_column": conc_col,
            },
            "size_statistics": size_stats,
            "concentration_statistics": conc_stats,
            "values": values_data,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get NTA values: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get NTA values: {str(e)}"
        )


# ============================================================================
# VAL-001: NTA vs FCS Cross-Validation Endpoint
# ============================================================================

@router.get("/{fcs_sample_id}/cross-validate/{nta_sample_id}", response_model=dict)
async def cross_validate_fcs_nta(
    fcs_sample_id: str,
    nta_sample_id: str,
    wavelength_nm: float = Query(405.0, description="Laser wavelength in nm"),
    n_particle: float = Query(1.37, description="Particle refractive index (EVs ≈ 1.37)"),
    n_medium: float = Query(1.33, description="Medium refractive index (PBS ≈ 1.33)"),
    num_bins: int = Query(50, ge=10, le=200, description="Number of histogram bins"),
    size_min: float = Query(20.0, ge=0, description="Minimum size in nm for histogram"),
    size_max: float = Query(500.0, le=2000, description="Maximum size in nm for histogram"),
    normalize: bool = Query(True, description="Normalize distributions to probability density"),
    db: AsyncSession = Depends(get_session)
):
    """
    Cross-validate FCS and NTA size distributions.
    
    Computes aligned histogram bins for both FCS (Mie-calculated) and NTA (measured)
    size distributions and returns comparison statistics.
    
    **Science:** Both methods measure the same EV sample. If Mie calibration is correct,
    D50 values should agree within ~10-15%. Surya (Jan 20 meeting): "bell curves should
    look similar."
    
    **Response:** Aligned size distributions, D50 comparison, statistical tests.
    """
    import numpy as np
    
    try:
        # ===== 1. Load FCS sample and compute Mie-calculated sizes =====
        fcs_result = await db.execute(select(Sample).where(Sample.sample_id == fcs_sample_id))
        fcs_sample = fcs_result.scalar_one_or_none()
        
        if not fcs_sample:
            raise HTTPException(status_code=404, detail=f"FCS sample '{fcs_sample_id}' not found")
        if not fcs_sample.file_path_fcs:
            raise HTTPException(status_code=404, detail=f"No FCS file for sample '{fcs_sample_id}'")
        
        from src.utils.fcs_cache import get_cached_fcs_data
        from src.utils.channel_config import ChannelConfig
        
        fcs_data, fcs_channels = get_cached_fcs_data(fcs_sample.file_path_fcs)
        
        config = ChannelConfig()
        fsc_channel = config.detect_fsc_channel(fcs_channels)
        ssc_channel = config.detect_ssc_channel(fcs_channels)
        
        if not fsc_channel:
            raise HTTPException(status_code=400, detail="No FSC channel detected in FCS file")
        
        # Detect multi-solution capability
        multi_info = detect_multi_solution_channels(fcs_channels)
        
        # Sample for performance (max 50k events)
        sample_size = min(50000, len(fcs_data))
        np.random.seed(42)
        sample_indices = np.random.choice(len(fcs_data), size=sample_size, replace=False)
        
        fsc_values = np.asarray(fcs_data[fsc_channel].values[sample_indices], dtype=np.float64)
        
        if multi_info['can_use_multi_solution'] and multi_info['vssc_channel'] in fcs_data.columns and multi_info['bssc_channel'] in fcs_data.columns:
            # Multi-solution Mie
            from src.physics.mie_scatter import MultiSolutionMieCalculator
            vssc_ch = multi_info['vssc_channel']
            bssc_ch = multi_info['bssc_channel']
            
            ssc_violet = np.asarray(fcs_data[vssc_ch].values[sample_indices], dtype=np.float64)
            ssc_blue = np.asarray(fcs_data[bssc_ch].values[sample_indices], dtype=np.float64)
            
            from src.physics.bead_calibration import get_fcmpass_k_factor
            _k = get_fcmpass_k_factor()
            multi_calc = MultiSolutionMieCalculator(n_particle=n_particle, n_medium=n_medium, k_violet=_k)
            fcs_sizes, _ = multi_calc.calculate_sizes_multi_solution(ssc_blue, ssc_violet)
            mie_method = "multi-solution"
        else:
            # Single-solution Mie
            from src.physics.mie_scatter import MieScatterCalculator
            mie_calc = MieScatterCalculator(
                wavelength_nm=wavelength_nm,
                n_particle=n_particle,
                n_medium=n_medium
            )
            fcs_sizes, success = mie_calc.diameters_from_scatter_normalized(
                fsc_values, min_diameter=20.0, max_diameter=500.0
            )
            fcs_sizes = fcs_sizes[success]
            mie_method = "single-solution"
        
        # Filter valid FCS sizes
        fcs_valid = fcs_sizes[~np.isnan(fcs_sizes) & (fcs_sizes > 0) & (fcs_sizes >= size_min) & (fcs_sizes <= size_max)]
        
        if len(fcs_valid) == 0:
            raise HTTPException(status_code=400, detail="No valid FCS sizes calculated from Mie theory")
        
        logger.info(f"✅ FCS cross-val: {len(fcs_valid)} valid sizes from {len(fcs_data)} events ({mie_method})")
        
        # ===== 2. Load NTA sample and get size distribution =====
        nta_result = await db.execute(select(Sample).where(Sample.sample_id == nta_sample_id))
        nta_sample = nta_result.scalar_one_or_none()
        
        nta_file_path = None
        if nta_sample and nta_sample.file_path_nta:
            nta_file_path = nta_sample.file_path_nta
        else:
            # Fallback: search uploads directory for the NTA file
            found_path = _find_nta_file_by_sample_id(nta_sample_id)
            if found_path:
                nta_file_path = found_path
                logger.info(f"📂 Cross-val: Found NTA file on disk (not in DB): {found_path}")
            else:
                raise HTTPException(status_code=404, detail=f"NTA sample '{nta_sample_id}' not found")
        
        from src.parsers.nta_parser import NTAParser
        
        nta_parser = NTAParser(nta_file_path)
        nta_data = nta_parser.parse()
        
        # Find size and concentration columns
        size_col = None
        conc_col = None
        for col in ['size_nm', 'Size (nm)', 'Diameter', 'diameter_nm']:
            if col in nta_data.columns:
                size_col = col
                break
        for col in ['concentration_particles_ml', 'Concentration (particles/mL)', 'concentration_particles_cm3', 'Conc.']:
            if col in nta_data.columns:
                conc_col = col
                break
        
        if not size_col:
            raise HTTPException(status_code=400, detail="No size column found in NTA data")
        
        nta_sizes_raw = nta_data[size_col].values
        nta_concentrations = nta_data[conc_col].values if conc_col else None

        # Parse NTA metadata (for dilution factor provenance).
        nta_raw_metadata = getattr(nta_parser, "raw_metadata", {}) or {}
        
        # Filter to valid range
        nta_mask = ~np.isnan(nta_sizes_raw) & (nta_sizes_raw >= size_min) & (nta_sizes_raw <= size_max)
        nta_sizes = nta_sizes_raw[nta_mask]
        nta_conc = nta_concentrations[nta_mask] if nta_concentrations is not None else None
        
        if len(nta_sizes) == 0:
            raise HTTPException(status_code=400, detail="No valid NTA sizes in the specified range")
        
        logger.info(f"✅ NTA cross-val: {len(nta_sizes)} size bins from {len(nta_data)} total rows")

        # ===== 2b. Concentration + dilution correction context (VAL-004) =====
        fcs_dilution = await _get_sample_dilution_factor(db, fcs_sample.id)  # type: ignore[arg-type]
        nta_dilution = await _get_sample_dilution_factor(db, nta_sample.id) if nta_sample else None  # type: ignore[arg-type]

        nta_dilution_source = "experimental_conditions"
        if nta_dilution is None:
            nta_meta_dilution = nta_raw_metadata.get("dilution")
            try:
                nta_dilution_candidate = int(float(nta_meta_dilution)) if nta_meta_dilution is not None else None
            except Exception:
                nta_dilution_candidate = None
            if nta_dilution_candidate and nta_dilution_candidate > 0:
                nta_dilution = nta_dilution_candidate
                nta_dilution_source = "metadata"
            else:
                nta_dilution_source = "missing"
        else:
            nta_dilution_source = "experimental_conditions"

        fcs_dilution_source = "experimental_conditions" if fcs_dilution is not None else "missing"

        # Measured concentration estimates.
        nta_measured_conc = float(np.nansum(nta_conc)) if nta_conc is not None and len(nta_conc) > 0 else None

        # FCS measured concentration: use latest stored summary if available; else None.
        fcs_result_row = await db.execute(
            select(FCSResult)
            .where(FCSResult.sample_id == fcs_sample.id)  # type: ignore[arg-type]
            .order_by(FCSResult.id.desc())
            .limit(1)
        )
        fcs_latest = fcs_result_row.scalar_one_or_none()
        fcs_measured_conc = None
        if fcs_latest and isinstance(fcs_latest.fluorescence_stats, dict):
            raw_conc = fcs_latest.fluorescence_stats.get("concentration_particles_ml")
            if raw_conc is not None:
                try:
                    fcs_measured_conc = float(raw_conc)
                except Exception:
                    fcs_measured_conc = None

        nta_corrected_conc = float(nta_measured_conc * nta_dilution) if nta_measured_conc is not None and nta_dilution else None
        fcs_corrected_conc = float(fcs_measured_conc * fcs_dilution) if fcs_measured_conc is not None and fcs_dilution else None

        conc_ratio = None
        conc_pct_diff = None
        if nta_corrected_conc is not None and fcs_corrected_conc is not None and fcs_corrected_conc > 0:
            conc_ratio = float(nta_corrected_conc / fcs_corrected_conc)
            conc_pct_diff = float(abs(nta_corrected_conc - fcs_corrected_conc) / ((nta_corrected_conc + fcs_corrected_conc) / 2) * 100)
        
        # ===== 3. Create aligned histograms =====
        bin_edges = np.linspace(size_min, size_max, num_bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        bin_width = bin_edges[1] - bin_edges[0]
        
        # FCS histogram (event counts)
        fcs_hist, _ = np.histogram(fcs_valid, bins=bin_edges)
        
        # NTA histogram - use concentration weighting if available
        if nta_conc is not None and len(nta_conc) > 0:
            # NTA data is typically binned: size vs concentration
            # Interpolate into our common bins
            nta_hist = np.zeros(num_bins)
            for i, (sz, conc) in enumerate(zip(nta_sizes, nta_conc)):
                bin_idx = int((sz - size_min) / bin_width)
                if 0 <= bin_idx < num_bins:
                    nta_hist[bin_idx] += conc
        else:
            nta_hist, _ = np.histogram(nta_sizes, bins=bin_edges)
        
        # Normalize to probability density if requested
        if normalize:
            fcs_total = np.sum(fcs_hist)
            nta_total = np.sum(nta_hist)
            fcs_density = (fcs_hist / fcs_total * 100) if fcs_total > 0 else fcs_hist
            nta_density = (nta_hist / nta_total * 100) if nta_total > 0 else nta_hist
        else:
            fcs_density = fcs_hist.astype(float)
            nta_density = nta_hist.astype(float)
        
        # ===== 4. Calculate comparative statistics =====
        fcs_d10 = float(np.percentile(fcs_valid, 10))
        fcs_d50 = float(np.percentile(fcs_valid, 50))
        fcs_d90 = float(np.percentile(fcs_valid, 90))
        fcs_mean = float(np.mean(fcs_valid))
        fcs_std = float(np.std(fcs_valid))
        
        # NTA stats - concentration-weighted if available
        if nta_conc is not None and np.sum(nta_conc) > 0:
            nta_cumsum = np.cumsum(nta_conc)
            nta_total_conc = nta_cumsum[-1]
            nta_d10_idx = np.searchsorted(nta_cumsum, 0.10 * nta_total_conc)
            nta_d50_idx = np.searchsorted(nta_cumsum, 0.50 * nta_total_conc)
            nta_d90_idx = np.searchsorted(nta_cumsum, 0.90 * nta_total_conc)
            
            nta_d10 = float(nta_sizes[min(nta_d10_idx, len(nta_sizes) - 1)])
            nta_d50 = float(nta_sizes[min(nta_d50_idx, len(nta_sizes) - 1)])
            nta_d90 = float(nta_sizes[min(nta_d90_idx, len(nta_sizes) - 1)])
            nta_mean = float(np.average(nta_sizes, weights=nta_conc))
            nta_std = float(np.sqrt(np.average((nta_sizes - nta_mean) ** 2, weights=nta_conc)))
        else:
            nta_d10 = float(np.percentile(nta_sizes, 10))
            nta_d50 = float(np.percentile(nta_sizes, 50))
            nta_d90 = float(np.percentile(nta_sizes, 90))
            nta_mean = float(np.mean(nta_sizes))
            nta_std = float(np.std(nta_sizes))
        
        # D50 comparison (the key metric per Surya)
        d50_diff = abs(fcs_d50 - nta_d50)
        d50_avg = (fcs_d50 + nta_d50) / 2
        d50_pct_diff = (d50_diff / d50_avg * 100) if d50_avg > 0 else 0
        
        # Determine validation verdict
        if d50_pct_diff < 10:
            verdict = "PASS"
            verdict_detail = "Excellent agreement — Mie calibration validated"
        elif d50_pct_diff < 20:
            verdict = "ACCEPTABLE"
            verdict_detail = "Acceptable agreement — minor systematic offset"
        elif d50_pct_diff < 30:
            verdict = "WARNING"
            verdict_detail = "Moderate discrepancy — review Mie parameters or sample prep"
        else:
            verdict = "FAIL"
            verdict_detail = "Significant discrepancy — calibration check needed"
        
        # ===== 5. Statistical tests =====
        try:
            from scipy import stats as scipy_stats
            
            # KS test (FCS vs NTA - compare distributions)
            # For NTA with concentration weighting, expand to representative sample
            if nta_conc is not None and np.sum(nta_conc) > 0:
                # Create expanded sample from concentration-weighted bins
                nta_expanded = np.repeat(nta_sizes, (nta_conc / np.min(nta_conc[nta_conc > 0])).astype(int).clip(max=1000))
                if len(nta_expanded) > 50000:
                    nta_expanded = np.random.choice(nta_expanded, 50000, replace=False)
            else:
                nta_expanded = nta_sizes
            
            ks_stat, ks_pval = scipy_stats.ks_2samp(fcs_valid[:50000], nta_expanded[:50000])
            
            # Mann-Whitney U test
            mw_stat, mw_pval = scipy_stats.mannwhitneyu(
                fcs_valid[:50000], nta_expanded[:50000], alternative='two-sided'
            )
            
            # Overlap coefficient (Bhattacharyya)
            fcs_norm = fcs_density / (np.sum(fcs_density) + 1e-10)
            nta_norm = nta_density / (np.sum(nta_density) + 1e-10)
            bhattacharyya_coeff = float(np.sum(np.sqrt(fcs_norm * nta_norm)))
            
            statistical_tests = {
                "kolmogorov_smirnov": {
                    "statistic": float(ks_stat),
                    "p_value": float(ks_pval),
                    "interpretation": "Distributions are similar" if ks_pval > 0.05 else "Distributions differ significantly"
                },
                "mann_whitney_u": {
                    "statistic": float(mw_stat),
                    "p_value": float(mw_pval),
                    "interpretation": "Medians are similar" if mw_pval > 0.05 else "Medians differ significantly"
                },
                "bhattacharyya_coefficient": {
                    "value": bhattacharyya_coeff,
                    "interpretation": "High overlap" if bhattacharyya_coeff > 0.85 else "Moderate overlap" if bhattacharyya_coeff > 0.7 else "Low overlap"
                }
            }
        except ImportError:
            logger.warning("scipy not available — skipping statistical tests")
            statistical_tests = None
        except Exception as stat_err:
            logger.warning(f"Statistical tests failed: {stat_err}")
            statistical_tests = None
        
        # ===== 6. Build aligned distribution data =====
        distribution_data = []
        for i in range(num_bins):
            distribution_data.append({
                "size": round(float(bin_centers[i]), 1),
                "fcs": round(float(fcs_density[i]), 4),
                "nta": round(float(nta_density[i]), 4),
                "fcs_raw": int(fcs_hist[i]),
                "nta_raw": round(float(nta_hist[i]), 2),
            })
        
        response = {
            "fcs_sample_id": fcs_sample_id,
            "nta_sample_id": nta_sample_id,
            "mie_parameters": {
                "wavelength_nm": wavelength_nm,
                "n_particle": n_particle,
                "n_medium": n_medium,
                "method": mie_method,
            },
            "data_summary": {
                "fcs_total_events": len(fcs_data),
                "fcs_valid_sizes": len(fcs_valid),
                "nta_total_bins": len(nta_data),
                "nta_valid_bins": len(nta_sizes),
                "histogram_bins": num_bins,
                "size_range": [size_min, size_max],
                "normalized": normalize,
            },
            "fcs_statistics": {
                "d10": round(fcs_d10, 2),
                "d50": round(fcs_d50, 2),
                "d90": round(fcs_d90, 2),
                "mean": round(fcs_mean, 2),
                "std": round(fcs_std, 2),
                "count": len(fcs_valid),
            },
            "nta_statistics": {
                "d10": round(nta_d10, 2),
                "d50": round(nta_d50, 2),
                "d90": round(nta_d90, 2),
                "mean": round(nta_mean, 2),
                "std": round(nta_std, 2),
                "count": len(nta_sizes),
            },
            "comparison": {
                "d50_fcs": round(fcs_d50, 2),
                "d50_nta": round(nta_d50, 2),
                "d50_difference_nm": round(d50_diff, 2),
                "d50_difference_pct": round(d50_pct_diff, 2),
                "d10_difference_pct": round(abs(fcs_d10 - nta_d10) / ((fcs_d10 + nta_d10) / 2) * 100, 2) if (fcs_d10 + nta_d10) > 0 else 0,
                "d90_difference_pct": round(abs(fcs_d90 - nta_d90) / ((fcs_d90 + nta_d90) / 2) * 100, 2) if (fcs_d90 + nta_d90) > 0 else 0,
                "mean_difference_pct": round(abs(fcs_mean - nta_mean) / ((fcs_mean + nta_mean) / 2) * 100, 2) if (fcs_mean + nta_mean) > 0 else 0,
                "verdict": verdict,
                "verdict_detail": verdict_detail,
            },
            "concentration": {
                "nta": {
                    "measured_per_ml": nta_measured_conc,
                    "dilution_factor": int(nta_dilution) if nta_dilution is not None else None,
                    "corrected_per_ml": nta_corrected_conc,
                    "dilution_source": nta_dilution_source,
                },
                "fcs": {
                    "measured_per_ml": fcs_measured_conc,
                    "dilution_factor": int(fcs_dilution) if fcs_dilution is not None else None,
                    "corrected_per_ml": fcs_corrected_conc,
                    "dilution_source": fcs_dilution_source,
                },
                "comparison": {
                    "ratio_corrected_nta_to_fcs": conc_ratio,
                    "percent_difference_corrected": conc_pct_diff,
                },
            },
            "flags": {
                "missing_dilution_factor": bool(nta_dilution is None or fcs_dilution is None),
                "missing_measured_concentration": bool(nta_measured_conc is None or fcs_measured_conc is None),
            },
            "statistical_tests": statistical_tests,
            "distribution": distribution_data,
        }
        
        logger.success(
            f"✅ Cross-validation complete: FCS D50={fcs_d50:.1f}nm vs NTA D50={nta_d50:.1f}nm "
            f"→ {d50_pct_diff:.1f}% difference → {verdict}"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Cross-validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cross-validation failed: {str(e)}"
        )
