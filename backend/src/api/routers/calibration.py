"""
Calibration Router
==================

Endpoints for bead-based instrument calibration.

Endpoints:
- GET  /calibration/bead-standards     - List available bead kits
- GET  /calibration/status             - Get active calibration status
- GET  /calibration/active             - Get full active calibration details
- POST /calibration/fit                - Fit calibration from bead FCS file
- POST /calibration/fit-manual         - Fit from manually provided scatter values
- DELETE /calibration/active           - Remove active calibration

Author: CRMIT Backend Team
Date: February 10, 2026
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from src.api.auth_middleware import optional_auth
from pydantic import BaseModel, Field
from loguru import logger
from pathlib import Path
import numpy as np

from src.physics.bead_calibration import (
    list_available_bead_standards,
    BeadDatasheet,
    BeadCalibrationCurve,
    calibrate_from_bead_fcs,
    get_active_calibration,
    save_as_active_calibration,
    get_calibration_status,
    CALIBRATION_DIR,
)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class ManualBeadPoint(BaseModel):
    """A single bead calibration point provided manually."""
    diameter_nm: float = Field(..., description="Known bead diameter in nm")
    scatter_mean: float = Field(..., description="Mean scatter intensity for this bead")
    scatter_std: float = Field(0.0, description="Std dev of scatter (optional)")
    cv_pct: float = Field(5.0, description="Diameter CV from manufacturer (%)")


class ManualCalibrationRequest(BaseModel):
    """Request to fit calibration from manually provided bead measurements."""
    bead_points: List[ManualBeadPoint] = Field(..., min_length=2)
    instrument_name: str = Field("CytoFLEX_S")
    wavelength_nm: float = Field(405.0)
    fit_method: str = Field("power")
    bead_kit: Optional[str] = Field(None, description="Bead kit filename (e.g., nanovis_d03231.json)")
    bead_ri: float = Field(1.591, description="Bead refractive index")
    set_as_active: bool = Field(True, description="Set this as the active calibration")


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/bead-standards", response_model=dict)
async def list_bead_standards():
    """
    List all available bead standard datasheets.
    
    Returns list of bead kits loaded from config/bead_standards/*.json
    """
    try:
        standards = list_available_bead_standards()
        return {
            "count": len(standards),
            "standards": standards,
        }
    except Exception as e:
        logger.error(f"Failed to list bead standards: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list bead standards: {str(e)}"
        )


@router.get("/status", response_model=dict)
async def get_status():
    """
    Get the status of the active bead calibration.
    
    Returns calibration info (kit, R², range) or 'not_calibrated' status.
    Used by the frontend sidebar to show calibration badge.
    """
    try:
        return get_calibration_status()
    except Exception as e:
        logger.error(f"Failed to get calibration status: {e}")
        return {
            "status": "error",
            "calibrated": False,
            "message": f"Error: {str(e)}"
        }


@router.get("/active", response_model=dict)
async def get_active():
    """
    Get the full active calibration details including fit parameters,
    bead points, and diagnostics.
    """
    try:
        cal_status = get_calibration_status()
        
        if not cal_status.get('calibrated'):
            return {
                "calibrated": False,
                "calibration": None,
            }
        
        # Load the full calibration data
        active_path = CALIBRATION_DIR / "active_calibration.json"
        import json
        with open(active_path, 'r') as f:
            cal_data = json.load(f)
        
        # Build calibration curve chart data
        bead_points = []
        for d_str, std in cal_data.get('bead_standards', {}).items():
            bead_points.append({
                'diameter_nm': std['diameter_nm'],
                'scatter_mean': std['fsc_mean'],
                'scatter_std': std['fsc_std'],
                'n_events': std['n_events'],
                'cv_pct': std['diameter_cv'],
            })
        
        # Sort by diameter
        bead_points.sort(key=lambda x: x['diameter_nm'])
        
        # Generate fitted curve points for visualization
        fit_params = cal_data.get('fit_params', {})
        curve_points = []
        if fit_params and 'a' in fit_params and 'b' in fit_params:
            a = fit_params['a']
            b = fit_params['b']
            cal_range = cal_data.get('calibration_range_nm', [40, 1020])
            d_min = max(cal_range[0] * 0.8, 20)
            d_max = cal_range[1] * 1.2
            diameters = np.logspace(np.log10(d_min), np.log10(d_max), 100)
            for d in diameters:
                curve_points.append({
                    'diameter_nm': float(d),
                    'scatter_predicted': float(a * d**b),
                })
        
        return {
            "calibrated": True,
            "calibration": {
                "instrument": cal_data.get('instrument_name'),
                "wavelength_nm": cal_data.get('wavelength_nm'),
                "fit_method": cal_data.get('fit_method'),
                "fit_params": fit_params,
                "calibration_range_nm": cal_data.get('calibration_range_nm'),
                "created_at": cal_data.get('created_at'),
                "bead_datasheet_info": cal_data.get('bead_datasheet_info'),
                "bead_points": bead_points,
                "curve_points": curve_points,
                "n_bead_sizes": len(bead_points),
            }
        }
    except Exception as e:
        logger.error(f"Failed to get active calibration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active calibration: {str(e)}"
        )


@router.post("/fit", response_model=dict)
async def fit_calibration_from_fcs(
    sample_id: str = Query(..., description="Sample ID of the bead FCS file to use"),
    scatter_channel: str = Query("VSSC1-H", description="Scatter channel to use"),
    bead_kit: str = Query("nanovis_d03231.json", description="Bead kit JSON filename"),
    subcomponent: Optional[str] = Query(None, description="Subcomponent filter (nanoViS_Low, nanoViS_High)"),
    instrument_name: str = Query("CytoFLEX_S", description="Instrument name"),
    wavelength_nm: float = Query(405.0, description="Laser wavelength for the scatter channel"),
    fit_method: str = Query("power", description="Fit method: power, polynomial, interpolate"),
    set_as_active: bool = Query(True, description="Set as active calibration"),
    current_user: dict | None = Depends(optional_auth),
):
    """
    Fit a bead calibration curve from an uploaded bead FCS file.
    
    1. Loads the specified bead kit datasheet
    2. Parses the FCS file for the given sample
    3. Auto-detects bead population peaks in the scatter channel
    4. Matches peaks to known bead diameters
    5. Fits calibration transfer function
    6. Optionally saves as the active calibration
    """
    from sqlalchemy import select
    from src.database.connection import get_session
    from src.database.models import Sample
    
    try:
        # Find bead datasheet
        bead_standards_dir = Path(__file__).parent.parent / "config" / "bead_standards"
        datasheet_path = bead_standards_dir / bead_kit
        
        if not datasheet_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bead kit datasheet not found: {bead_kit}. "
                       f"Available: {[f.name for f in bead_standards_dir.glob('*.json')]}"
            )
        
        # Find the FCS file path from the database
        # Try direct file lookup first
        fcs_file_path = None
        
        # Check common upload locations
        data_dir = Path(__file__).parent.parent / "data"
        possible_paths = [
            data_dir / "uploads" / f"{sample_id}.fcs",
            data_dir / "uploads" / sample_id,
        ]
        
        # Also search the nanoFACS directory for bead FCS files
        nanofacs_dir = Path(__file__).parent.parent / "nanoFACS"
        if nanofacs_dir.exists():
            for fcs_file in nanofacs_dir.rglob("*.fcs"):
                if sample_id.lower() in fcs_file.stem.lower():
                    possible_paths.append(fcs_file)
        
        for p in possible_paths:
            if p.exists():
                fcs_file_path = str(p)
                break
        
        # Try database lookup
        if fcs_file_path is None:
            try:
                async for session in get_session():
                    result = await session.execute(
                        select(Sample).where(Sample.sample_id == sample_id)
                    )
                    sample_record = result.scalar_one_or_none()
                    if sample_record is not None:
                        fcs_attr = getattr(sample_record, 'file_path_fcs', None)
                        if fcs_attr is not None:
                            fcs_path = Path(str(fcs_attr))
                            if fcs_path.exists():
                                fcs_file_path = str(fcs_path)
            except Exception:
                pass
        
        if fcs_file_path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"FCS file not found for sample '{sample_id}'. "
                       f"Upload the bead FCS file first."
            )
        
        # Run calibration pipeline
        calib, diagnostics = calibrate_from_bead_fcs(
            fcs_file_path=fcs_file_path,
            datasheet_path=str(datasheet_path),
            scatter_channel=scatter_channel,
            instrument_name=instrument_name,
            wavelength_nm=wavelength_nm,
            fit_method=fit_method,
            subcomponent=subcomponent,
        )
        
        # Save as active if requested
        saved_path = None
        if set_as_active:
            saved_path = save_as_active_calibration(calib)
        
        return {
            "success": True,
            "message": f"Calibration fitted with {diagnostics['n_beads_matched']} bead sizes",
            "set_as_active": set_as_active,
            "saved_path": saved_path,
            "diagnostics": diagnostics,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Calibration fitting failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calibration fitting failed: {str(e)}"
        )


@router.post("/fit-manual", response_model=dict)
async def fit_calibration_manual(
    request: ManualCalibrationRequest,
    current_user: dict | None = Depends(optional_auth),
):
    """
    Fit calibration from manually provided bead scatter values.
    
    Use this when you already know the scatter peak values for each bead
    (e.g., from manual gating in FlowJo or CytoFLEX acquisition software).
    """
    try:
        # Load datasheet if specified
        datasheet = None
        if request.bead_kit:
            bead_standards_dir = Path(__file__).parent.parent / "config" / "bead_standards"
            datasheet_path = bead_standards_dir / request.bead_kit
            if datasheet_path.exists():
                datasheet = BeadDatasheet.load(str(datasheet_path))
        
        calib = BeadCalibrationCurve(
            instrument_name=request.instrument_name,
            wavelength_nm=request.wavelength_nm,
            fit_method=request.fit_method,
            bead_datasheet=datasheet,
        )
        
        for point in request.bead_points:
            # Create synthetic events from mean/std
            n_events = 1000
            std = point.scatter_std if point.scatter_std > 0 else point.scatter_mean * 0.05
            events = np.random.normal(point.scatter_mean, std, n_events)
            events = events[events > 0]
            
            calib.add_bead_standard(
                diameter_nm=point.diameter_nm,
                fsc_values=events,
                diameter_cv=point.cv_pct,
                refractive_index=request.bead_ri,
            )
        
        fit_result = calib.fit()
        
        if request.set_as_active:
            save_as_active_calibration(calib)
        
        return {
            "success": True,
            "message": f"Manual calibration fitted with {len(request.bead_points)} bead sizes",
            "set_as_active": request.set_as_active,
            "fit_result": fit_result,
        }
        
    except Exception as e:
        logger.error(f"Manual calibration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Manual calibration failed: {str(e)}"
        )


@router.delete("/active", response_model=dict)
async def remove_active_calibration(
    current_user: dict | None = Depends(optional_auth),
):
    """Remove the active calibration (revert to uncalibrated Mie theory)."""
    try:
        import datetime
        active_path = CALIBRATION_DIR / "active_calibration.json"
        
        if not active_path.exists():
            return {
                "success": True,
                "message": "No active calibration to remove",
            }
        
        # Archive instead of delete
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = CALIBRATION_DIR / f"calibration_removed_{timestamp}.json"
        active_path.rename(archive_path)
        
        return {
            "success": True,
            "message": f"Active calibration removed (archived as {archive_path.name})",
        }
        
    except Exception as e:
        logger.error(f"Failed to remove calibration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove calibration: {str(e)}"
        )
