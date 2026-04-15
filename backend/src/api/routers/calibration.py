"""
Calibration Router
==================

Endpoints for bead-based instrument calibration.

Endpoints:
- GET  /calibration/bead-standards     - List available bead kits
- POST /calibration/bead-standards     - Upload a custom bead kit
- DELETE /calibration/bead-standards/{filename} - Delete a custom bead kit
- GET  /calibration/status             - Get active calibration status
- GET  /calibration/active             - Get full active calibration details
- POST /calibration/fit                - Fit calibration from bead FCS file
- POST /calibration/fit-manual         - Fit from manually provided scatter values
- DELETE /calibration/active           - Remove active calibration
- GET  /calibration/fcmpass/list       - List all FCMPASS calibrations (active + archived)
- GET  /calibration/fcmpass/{cal_id}   - Get details for a specific calibration
- PUT  /calibration/fcmpass/{cal_id}/activate - Activate an archived calibration
- DELETE /calibration/fcmpass/{cal_id} - Delete an archived calibration

Author: CRMIT Backend Team
Date: February 10, 2026
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from src.api.auth_middleware import optional_auth
from pydantic import BaseModel, Field, field_validator
from loguru import logger
from pathlib import Path
import numpy as np
import json
import re

from src.physics.bead_calibration import (
    list_available_bead_standards,
    BeadDatasheet,
    BeadCalibrationCurve,
    calibrate_from_bead_fcs,
    get_active_calibration,
    save_as_active_calibration,
    get_calibration_status,
    CALIBRATION_DIR,
    save_fcmpass_calibration,
    get_fcmpass_calibration,
    get_fcmpass_calibration_status,
    list_fcmpass_calibrations,
    get_fcmpass_calibration_by_id,
    activate_fcmpass_calibration,
    delete_fcmpass_calibration_by_id,
    check_gain_mismatch,
    check_bead_kit_expiry,
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


class FitCalibrationRequest(BaseModel):
    """Request to fit calibration from a bead FCS file."""
    sample_id: str = Field(..., description="Sample ID of the bead FCS file to use")
    scatter_channel: str = Field("VSSC1-H", description="Scatter channel to use")
    bead_kit: str = Field("nanovis_d03231.json", description="Bead kit JSON filename")
    subcomponent: Optional[str] = Field(None, description="Subcomponent filter (nanoViS_Low, nanoViS_High)")
    instrument_name: str = Field("CytoFLEX_S", description="Instrument name")
    wavelength_nm: float = Field(405.0, description="Laser wavelength for the scatter channel")
    fit_method: str = Field("power", description="Fit method: power, polynomial, interpolate")
    set_as_active: bool = Field(True, description="Set as active calibration")


class ManualCalibrationRequest(BaseModel):
    """Request to fit calibration from manually provided bead measurements."""
    bead_points: List[ManualBeadPoint] = Field(..., min_length=2)
    instrument_name: str = Field("CytoFLEX_S")
    wavelength_nm: float = Field(405.0)
    fit_method: str = Field("power")
    bead_kit: Optional[str] = Field(None, description="Bead kit filename (e.g., nanovis_d03231.json)")
    bead_ri: float = Field(1.591, description="Bead refractive index")
    set_as_active: bool = Field(True, description="Set this as the active calibration")


class FCMPASSBeadPoint(BaseModel):
    """A single bead measurement for FCMPASS calibration."""
    diameter_nm: float = Field(..., description="Known bead diameter in nm")
    scatter_au: float = Field(..., description="Measured scatter value in AU (e.g., peak median)")


class FCMPASSCalibrationRequest(BaseModel):
    """Request to fit FCMPASS k-based calibration from bead measurements."""
    bead_points: List[FCMPASSBeadPoint] = Field(..., min_length=2, description="Bead measurements")
    wavelength_nm: float = Field(405.0, description="Laser wavelength for scatter channel (nm)")
    n_bead: float = Field(1.591, description="Bead RI at reference wavelength (590nm for PS)")
    n_ev: float = Field(1.37, description="EV refractive index (1.37 for SEC-purified)")
    n_medium: float = Field(1.33, description="Medium RI (PBS=1.33)")
    use_wavelength_dispersion: bool = Field(True, description="Apply Cauchy dispersion for PS beads")
    set_as_active: bool = Field(True, description="Save as active FCMPASS calibration")
    bead_kit_filename: Optional[str] = Field(None, description="Bead kit JSON filename for expiry/metadata tracking")
    detector_gains: Optional[Dict[str, float]] = Field(None, description="Detector voltages/gains from bead FCS ($PnV)")


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


@router.post("/parse-datasheet", response_model=dict)
async def parse_bead_datasheet_endpoint(
    file: UploadFile = File(...),
    current_user: dict | None = Depends(optional_auth),
):
    """
    Parse a bead Certificate of Analysis (PDF or CSV/TSV).
    
    Extracts kit identity, bead populations, refractive index, etc.
    from manufacturer datasheets like Beckman Coulter nanoViS.
    
    Accepts: .pdf, .csv, .tsv, .txt files
    
    Returns parsed datasheet data including all bead populations
    grouped by subcomponent (e.g., nanoViS Low, nanoViS High).
    """
    from src.parsers.bead_datasheet_parser import parse_bead_datasheet
    
    allowed_ext = {".pdf", ".csv", ".tsv", ".txt"}
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()
    
    if ext not in allowed_ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {ext}. Accepted: {', '.join(allowed_ext)}"
        )
    
    try:
        content = await file.read()
        result = parse_bead_datasheet(filename, content=content)
        
        data = result.to_dict()
        data["success"] = len(result.all_beads) > 0
        
        if not result.all_beads:
            warning_msg = result.parse_warnings[0] if result.parse_warnings else "No bead populations found. Check file format."
            data["message"] = warning_msg
        else:
            data["message"] = f"Parsed {len(result.all_beads)} bead populations from {len(result.subcomponents)} subcomponents"
        
        return data
        
    except Exception as e:
        logger.error(f"Failed to parse bead datasheet: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse datasheet: {str(e)}"
        )


@router.post("/upload-bead-fcs", response_model=dict)
async def upload_bead_fcs_files(
    files: list[UploadFile] = File(...),
    current_user: dict | None = Depends(optional_auth),
):
    """
    Upload one or more bead measurement FCS files.
    
    Stores them in the uploads directory and returns sample IDs.
    Supports uploading multiple bead files (e.g., nanoViS Low + High).
    """
    from src.api.config import settings
    import shutil
    from datetime import datetime
    
    results = []
    upload_dir = settings.upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    for f in files:
        fname = f.filename or "unknown.fcs"
        if not fname.lower().endswith(".fcs"):
            results.append({
                "filename": fname,
                "success": False,
                "error": "Not an FCS file"
            })
            continue
        
        try:
            # Generate unique filename with timestamp
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = re.sub(r'[^\w\-.]', '_', fname)
            dest = upload_dir / f"{ts}_{safe_name}"
            
            content = await f.read()
            with open(dest, "wb") as out:
                out.write(content)
            
            # Generate sample ID from filename
            stem = Path(fname).stem
            sample_id = re.sub(r'[^\w\-]', '_', stem)
            
            results.append({
                "filename": fname,
                "success": True,
                "sample_id": sample_id,
                "file_path": str(dest),
                "size_bytes": len(content),
            })
            logger.info(f"Uploaded bead FCS: {fname} -> {dest} (sample_id={sample_id})")
            
        except Exception as e:
            logger.error(f"Failed to upload bead FCS {fname}: {e}")
            results.append({
                "filename": fname,
                "success": False,
                "error": str(e)
            })
    
    successful = [r for r in results if r["success"]]
    return {
        "success": len(successful) > 0,
        "message": f"Uploaded {len(successful)}/{len(results)} bead FCS files",
        "files": results,
        "sample_ids": [r["sample_id"] for r in successful],
    }


@router.post("/auto-calibrate", response_model=dict)
async def auto_calibrate_from_beads(
    sample_ids: str = Form(...),
    scatter_channel: str = Form("VSSC1-H"),
    bead_kit: str = Form("nanovis_d03231.json"),
    wavelength_nm: float = Form(405.0),
    n_bead: float = Form(1.591),
    n_ev: float = Form(1.37),
    n_medium: float = Form(1.33),
    use_wavelength_dispersion: bool = Form(True),
    current_user: dict | None = Depends(optional_auth),
):
    """
    Auto-calibrate from uploaded bead FCS file(s).
    
    1. For each sample_id, detect bead peaks in scatter channel
    2. Match peaks to known bead diameters from datasheet
    3. Combine all bead points
    4. Fit FCMPASS calibration
    
    sample_ids: comma-separated list of sample IDs
    """
    sample_id_list = [s.strip() for s in sample_ids.split(",") if s.strip()]
    
    if not sample_id_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No sample IDs provided"
        )
    
    try:
        backend_root = Path(__file__).parent.parent.parent.parent
        
        # Find bead datasheet
        bead_standards_dir = backend_root / "config" / "bead_standards"
        datasheet_path = bead_standards_dir / bead_kit
        
        if not datasheet_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bead kit datasheet not found: {bead_kit}"
            )
        
        # Load datasheet JSON to get subcomponent names
        with open(datasheet_path) as df:
            datasheet_json = json.load(df)
        
        # Get subcomponent names (e.g., ["nanoViS_Low", "nanoViS_High"])
        subcomponent_names = list(datasheet_json.get("subcomponents", {}).keys())
        logger.info(f"Bead kit subcomponents: {subcomponent_names}")
        
        # Helper: match sample_id to subcomponent by filename keywords
        def _match_subcomponent_by_name(sample_id: str) -> str | None:
            """Match sample_id to a subcomponent by overlapping keywords."""
            sid_tokens = set(re.split(r'[\s_\-]+', sample_id.lower()))
            
            best_match = None
            best_score = 0
            
            for subcomp in subcomponent_names:
                sc_tokens = set(re.split(r'[\s_\-]+', subcomp.lower()))
                overlap = len(sid_tokens & sc_tokens)
                if overlap > best_score:
                    best_score = overlap
                    best_match = subcomp
            
            if best_score > 0:
                logger.info(f"  Filename match: '{sample_id}' → subcomponent '{best_match}' (score={best_score})")
            return best_match if best_score > 0 else None
        
        # Collect all bead points from all FCS files
        # Uses Mie-theory consistent matching: detect many peaks, then find
        # the combination that gives the most consistent k values (lowest CV)
        from itertools import combinations
        from src.physics.bead_calibration import BeadDatasheet, detect_bead_peaks
        from src.physics.mie_scatter import FCMPASSCalibrator
        from src.parsers.fcs_parser import FCSParser
        
        all_bead_points = []
        per_file_results = []
        
        # Load datasheet for subcomponent filtering
        datasheet = BeadDatasheet.load(str(datasheet_path))
        
        # Build a temporary FCMPASSCalibrator to compute σ_sca for beads
        temp_calibrator = FCMPASSCalibrator(
            wavelength_nm=wavelength_nm,
            n_bead=n_bead,
            n_ev=n_ev,
            n_medium=n_medium,
            use_wavelength_dispersion=use_wavelength_dispersion,
        )
        
        for sid in sample_id_list:
            try:
                fcs_path = _find_fcs_file(sid, backend_root)
                
                # Determine subcomponent (which bead diameters to use)
                best_subcomp = _match_subcomponent_by_name(sid) if subcomponent_names else None
                
                if best_subcomp:
                    known_diameters = sorted(set(
                        b.diameter_nm for b in datasheet.beads if b.subcomponent == best_subcomp
                    ))
                    logger.info(f"  Using subcomponent '{best_subcomp}': {known_diameters}")
                else:
                    known_diameters = datasheet.get_unique_diameters()
                    logger.info(f"  Using all diameters: {known_diameters}")
                
                if not known_diameters:
                    raise ValueError(f"No bead diameters found for subcomponent '{best_subcomp}'")
                
                # Compute theoretical σ_sca for each diameter using Mie theory
                sigma_sca = {}
                for d in known_diameters:
                    sigma_sca[d] = temp_calibrator._compute_bead_sigma(d)
                    logger.debug(f"    σ_sca({d}nm) = {sigma_sca[d]:.4f} nm²")
                
                # Parse FCS file
                parser = FCSParser(Path(fcs_path))
                parsed_data = parser.parse()
                scatter_values = np.asarray(
                    parsed_data[scatter_channel].values, dtype=np.float64
                )
                scatter_values = scatter_values[scatter_values > 0]
                logger.info(f"  Loaded {len(scatter_values)} positive events from {scatter_channel}")
                
                # Detect MORE peaks than expected for combinatorial matching
                n_detect = min(len(known_diameters) * 3, 15)
                detected_peaks = detect_bead_peaks(
                    scatter_values,
                    n_expected_peaks=n_detect,
                )
                
                if len(detected_peaks) < len(known_diameters):
                    # Fewer peaks than expected — try matching the peaks we have
                    # to the best subset of bead diameters
                    logger.warning(
                        f"  Only {len(detected_peaks)} peaks found, need {len(known_diameters)}. "
                        f"Trying subset matching."
                    )
                    n_beads = len(detected_peaks)
                    # Try all C(n_diameters, n_peaks) subsets of diameters
                    from itertools import combinations as d_combos
                    sorted_peaks = sorted(detected_peaks, key=lambda p: p['peak_scatter_mean'])
                    
                    best_combo = None
                    best_cv = float('inf')
                    best_k_mean = 0.0
                    
                    for d_subset in d_combos(sorted(known_diameters), n_beads):
                        d_list = list(d_subset)
                        k_values = []
                        pairs = []
                        for peak, diameter in zip(sorted_peaks, d_list):
                            k = peak['peak_scatter_mean'] / sigma_sca[diameter]
                            k_values.append(k)
                            pairs.append((peak, diameter))
                        
                        k_mean = float(np.mean(k_values))
                        k_std = float(np.std(k_values))
                        k_cv = (k_std / k_mean * 100) if k_mean > 0 else 999.0
                        
                        if k_cv < best_cv:
                            best_cv = k_cv
                            best_combo = pairs
                            best_k_mean = k_mean
                    
                    if best_combo and best_cv < 50.0:
                        logger.info(
                            f"  ✓ Subset matching: k≈{best_k_mean:.1f}, CV={best_cv:.1f}%, "
                            f"{n_beads} beads"
                        )
                        for peak, diameter in best_combo:
                            scatter_au = peak['peak_scatter_mean']
                            k_val = scatter_au / sigma_sca[diameter]
                            logger.info(f"    {diameter}nm → AU={scatter_au:.1f}, k={k_val:.1f}")
                            all_bead_points.append({
                                "diameter_nm": diameter,
                                "scatter_au": scatter_au,
                                "source_file": sid,
                                "subcomponent": best_subcomp,
                            })
                        
                        per_file_results.append({
                            "sample_id": sid,
                            "success": True,
                            "n_beads_matched": n_beads,
                            "subcomponent": best_subcomp,
                            "k_estimate": round(best_k_mean, 1),
                            "k_cv_estimate": round(best_cv, 1),
                        })
                        continue
                    else:
                        raise ValueError(
                            f"Only {len(detected_peaks)} peaks found and subset matching "
                            f"gave poor CV ({best_cv:.1f}%)"
                        )
                
                # Combinatorial Mie-theory matching:
                # Try all C(n_peaks, n_beads) combinations, pick the one
                # where k = AU / σ_sca is most consistent (lowest CV)
                n_beads = len(known_diameters)
                sorted_diameters = sorted(known_diameters)
                peak_data = [
                    (i, p['peak_scatter_mean']) for i, p in enumerate(detected_peaks)
                ]
                
                best_combo = None
                best_cv = float('inf')
                best_k_mean = 0.0
                
                for combo in combinations(peak_data, n_beads):
                    # Sort selected peaks by scatter value (ascending)
                    sorted_combo = sorted(combo, key=lambda x: x[1])
                    
                    # Compute k for each (peak, diameter) pair
                    k_values = []
                    for (_, scatter_au), diameter in zip(sorted_combo, sorted_diameters):
                        k = scatter_au / sigma_sca[diameter]
                        k_values.append(k)
                    
                    k_mean = float(np.mean(k_values))
                    k_std = float(np.std(k_values))
                    k_cv = (k_std / k_mean * 100) if k_mean > 0 else 999.0
                    
                    if k_cv < best_cv:
                        best_cv = k_cv
                        best_combo = list(zip(sorted_combo, sorted_diameters))
                        best_k_mean = k_mean
                
                if best_combo is None:
                    raise ValueError("No valid peak combination found")
                
                logger.info(
                    f"  ✓ Best peak matching: k≈{best_k_mean:.1f}, CV={best_cv:.1f}%, "
                    f"{n_beads} beads from {len(detected_peaks)} peaks"
                )
                
                # Add matched bead points
                for (peak_idx, scatter_au), diameter in best_combo:
                    k_val = scatter_au / sigma_sca[diameter]
                    logger.info(f"    {diameter}nm → AU={scatter_au:.1f}, k={k_val:.1f}")
                    all_bead_points.append({
                        "diameter_nm": diameter,
                        "scatter_au": scatter_au,
                        "source_file": sid,
                        "subcomponent": best_subcomp,
                    })
                
                per_file_results.append({
                    "sample_id": sid,
                    "success": True,
                    "n_beads_matched": n_beads,
                    "subcomponent": best_subcomp,
                    "k_estimate": round(best_k_mean, 1),
                    "k_cv_estimate": round(best_cv, 1),
                })
                
            except Exception as e:
                logger.warning(f"Failed to process bead FCS {sid}: {e}")
                per_file_results.append({
                    "sample_id": sid,
                    "success": False,
                    "error": str(e),
                })
        
        if not all_bead_points:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No bead peaks could be detected from any of the uploaded FCS files. "
                       "Check that the correct scatter channel and bead kit are selected."
            )
        
        # Deduplicate: if same diameter from multiple files, keep the one with higher scatter
        deduped = {}
        for bp in all_bead_points:
            d = bp["diameter_nm"]
            if d not in deduped or bp["scatter_au"] > deduped[d]["scatter_au"]:
                deduped[d] = bp
        
        unique_points = sorted(deduped.values(), key=lambda x: x["diameter_nm"])
        
        # Now fit FCMPASS calibration with all collected points
        fcmpass_points = [
            {"diameter_nm": p["diameter_nm"], "scatter_au": p["scatter_au"]}
            for p in unique_points
        ]
        
        from src.physics.bead_calibration import save_fcmpass_calibration
        
        # Outlier rejection: if k CV is too high, iteratively remove
        # the bead with the most inconsistent k value until CV ≤ 10%
        # or only 2 beads remain. This handles noise peaks that slip through.
        working_points = list(fcmpass_points)
        
        while len(working_points) >= 3:
            # Compute trial k values
            trial_k = {}
            for p in working_points:
                d = p["diameter_nm"]
                sigma = temp_calibrator._compute_bead_sigma(d)
                if sigma > 0:
                    trial_k[d] = p["scatter_au"] / sigma
            
            k_values = list(trial_k.values())
            k_mean = float(np.mean(k_values))
            k_std = float(np.std(k_values))
            k_cv = (k_std / k_mean * 100) if k_mean > 0 else 999.0
            
            if k_cv <= 10.0:
                break  # Good enough
            
            # Find the bead with the most deviation from median
            k_median = float(np.median(k_values))
            worst_d = max(trial_k.keys(), key=lambda d: abs(trial_k[d] - k_median))
            worst_k = trial_k[worst_d]
            
            logger.info(
                f"  ⚠️ Outlier rejection: CV={k_cv:.1f}%, removing {worst_d}nm "
                f"(k={worst_k:.1f} vs median={k_median:.1f})"
            )
            working_points = [p for p in working_points if p["diameter_nm"] != worst_d]
        
        if len(working_points) < 2:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Too few consistent bead points after outlier rejection."
            )
        
        # Log final point set
        logger.info(f"  ✓ Final bead set ({len(working_points)} points):")
        for p in working_points:
            sigma = temp_calibrator._compute_bead_sigma(p["diameter_nm"])
            k = p["scatter_au"] / sigma if sigma > 0 else 0
            logger.info(f"    {p['diameter_nm']}nm: AU={p['scatter_au']:.0f}, k={k:.1f}")
        
        calibrator = FCMPASSCalibrator(
            wavelength_nm=wavelength_nm,
            n_bead=n_bead,
            n_ev=n_ev,
            n_medium=n_medium,
            use_wavelength_dispersion=use_wavelength_dispersion,
        )
        
        # Build bead_measurements dict: {diameter_nm: scatter_au}
        bead_measurements = {
            p["diameter_nm"]: p["scatter_au"] for p in working_points
        }
        
        # Fit k from bead points (modifies calibrator in-place)
        calibrator.fit_from_beads(bead_measurements)
        
        if not calibrator.calibrated:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="FCMPASS calibration fitting failed. Check bead data quality."
            )
        
        # Save calibration as active
        save_fcmpass_calibration(
            calibrator,
            bead_kit_name=bead_kit,
        )
        
        diagnostics = calibrator.get_diagnostics()
        
        return {
            "success": True,
            "message": f"Auto-calibration complete: {len(working_points)} bead sizes, k={calibrator.k_instrument:.1f}, CV={calibrator.k_cv_pct:.1f}%",
            "k_instrument": calibrator.k_instrument,
            "k_cv_pct": calibrator.k_cv_pct,
            "n_beads": len(working_points),
            "bead_points": [{"diameter_nm": p["diameter_nm"], "scatter_au": p["scatter_au"]} for p in working_points],
            "per_file_results": per_file_results,
            "diagnostics": diagnostics,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auto-calibration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto-calibration failed: {str(e)}"
        )


def _find_fcs_file(sample_id: str, backend_root: Path) -> str:
    """Find an FCS file by sample_id across all known directories."""
    from src.api.config import settings
    
    upload_dirs = [settings.upload_dir]
    backend_upload = backend_root / "data" / "uploads"
    if backend_upload.resolve() != settings.upload_dir.resolve():
        upload_dirs.append(backend_upload)
    
    for upload_dir in upload_dirs:
        if not upload_dir.exists():
            continue
        
        # Direct match
        for candidate in [
            upload_dir / f"{sample_id}.fcs",
            upload_dir / sample_id,
        ]:
            if candidate.exists():
                return str(candidate)
        
        # Fuzzy match — collect all matches, pick the most recent (by filename timestamp)
        sample_id_lower = sample_id.lower().replace("_", " ")
        matches = []
        for fcs_file in upload_dir.glob("*.fcs"):
            stem = fcs_file.stem.lower()
            parts = stem.split("_", 2)
            if len(parts) >= 3 and len(parts[0]) == 8 and len(parts[1]) == 6:
                name_part = parts[2]
                timestamp_prefix = parts[0] + parts[1]  # YYYYMMDDHHMMSS
            else:
                name_part = stem
                timestamp_prefix = ""
            if sample_id_lower == name_part or sample_id.lower() == name_part.replace(" ", "_"):
                matches.append((timestamp_prefix, fcs_file))
        
        if matches:
            # Sort by timestamp descending → return the most recent file
            matches.sort(key=lambda x: x[0], reverse=True)
            chosen = matches[0][1]
            if len(matches) > 1:
                logger.info(f"  _find_fcs_file: {len(matches)} matches for '{sample_id}', using most recent: {chosen.name}")
            return str(chosen)
    
    # Search nanoFACS directory
    nanofacs_dir = backend_root / "nanoFACS"
    if nanofacs_dir.exists():
        for fcs_file in nanofacs_dir.rglob("*.fcs"):
            if sample_id.lower() in fcs_file.stem.lower():
                return str(fcs_file)
    
    raise FileNotFoundError(f"FCS file not found for sample '{sample_id}'")



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
    request: FitCalibrationRequest,
    current_user: dict | None = Depends(optional_auth),
):
    """
    Fit a bead calibration curve from an uploaded bead FCS file.
    
    Accepts JSON body with: sample_id, scatter_channel, bead_kit, etc.
    
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
    
    # Extract fields from request body
    sample_id = request.sample_id
    scatter_channel = request.scatter_channel
    bead_kit = request.bead_kit
    subcomponent = request.subcomponent
    instrument_name = request.instrument_name
    wavelength_nm = request.wavelength_nm
    fit_method = request.fit_method
    set_as_active = request.set_as_active
    
    try:
        # Find bead datasheet
        backend_root = Path(__file__).parent.parent.parent.parent
        bead_standards_dir = backend_root / "config" / "bead_standards"
        datasheet_path = bead_standards_dir / bead_kit
        
        if not datasheet_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bead kit datasheet not found: {bead_kit}. "
                       f"Available: {[f.name for f in bead_standards_dir.glob('*.json')]}"
            )
        
        # Find the FCS file path
        # Search both settings.upload_dir (relative to CWD) and backend_root/data/uploads
        from src.api.config import settings
        fcs_file_path = None
        
        # Build list of upload directories to search
        upload_dirs = [settings.upload_dir]
        backend_upload = backend_root / "data" / "uploads"
        if backend_upload.resolve() != settings.upload_dir.resolve():
            upload_dirs.append(backend_upload)
        
        for upload_dir in upload_dirs:
            if fcs_file_path:
                break
            if not upload_dir.exists():
                continue
                
            # 1. Direct match: sample_id.fcs or sample_id
            for candidate in [
                upload_dir / f"{sample_id}.fcs",
                upload_dir / sample_id,
            ]:
                if candidate.exists():
                    fcs_file_path = str(candidate)
                    break
            
            # 2. Fuzzy match: files are stored as {timestamp}_{original_name}.fcs
            #    sample_id might be "Nano_Vis_High" while file is "20260122_150433_Nano Vis High.fcs"
            if fcs_file_path is None:
                sample_id_lower = sample_id.lower().replace("_", " ")
                for fcs_file in upload_dir.glob("*.fcs"):
                    stem = fcs_file.stem.lower()
                    # Strip timestamp prefix (YYYYMMDD_HHMMSS_)
                    parts = stem.split("_", 2)
                    if len(parts) >= 3 and len(parts[0]) == 8 and len(parts[1]) == 6:
                        name_part = parts[2]
                    else:
                        name_part = stem
                    if sample_id_lower == name_part or sample_id.lower() == name_part.replace(" ", "_"):
                        fcs_file_path = str(fcs_file)
                        break
        
        # 3. Search nanoFACS directory
        if fcs_file_path is None:
            nanofacs_dir = backend_root / "nanoFACS"
            if nanofacs_dir.exists():
                for fcs_file in nanofacs_dir.rglob("*.fcs"):
                    if sample_id.lower() in fcs_file.stem.lower():
                        fcs_file_path = str(fcs_file)
                        break
        
        # 4. Database lookup
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
        
        # Convert numpy types to native Python for JSON serialization
        def to_native(obj):
            if isinstance(obj, dict):
                return {k: to_native(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [to_native(v) for v in obj]
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.bool_):
                return bool(obj)
            return obj
        
        return to_native({
            "success": True,
            "message": f"Calibration fitted with {diagnostics['n_beads_matched']} bead sizes",
            "set_as_active": set_as_active,
            "saved_path": saved_path,
            "diagnostics": diagnostics,
        })
        
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
            bead_standards_dir = Path(__file__).parent.parent.parent.parent / "config" / "bead_standards"
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


# ============================================================================
# FCMPASS k-based Calibration (Validated Method)
# ============================================================================

@router.post("/fit-fcmpass", response_model=dict)
async def fit_fcmpass_calibration(
    request: FCMPASSCalibrationRequest,
    current_user: dict | None = Depends(optional_auth),
):
    """
    Fit FCMPASS k-based calibration from bead scatter measurements.
    
    This is the validated calibration method that uses the physics-based
    relationship AU = k × σ_sca, where k is an instrument constant.
    
    The instrument constant k should be consistent across all bead sizes
    (CV < 5% indicates good calibration).
    
    **Validated Results (nanoViS, CytoFLEX nano):**
    - k = 940.6 ± 22.8 (CV = 2.4%)
    - Bead self-consistency: < 0.7% error
    - NTA comparison (>100nm): -4.0% error
    
    **Example bead_points:**
    ```json
    [
        {"diameter_nm": 40, "scatter_au": 1888},
        {"diameter_nm": 80, "scatter_au": 102411},
        {"diameter_nm": 108, "scatter_au": 565342},
        {"diameter_nm": 142, "scatter_au": 2132067}
    ]
    ```
    """
    try:
        from src.physics.mie_scatter import FCMPASSCalibrator
        
        # Build bead measurements dict
        bead_measurements = {
            point.diameter_nm: point.scatter_au
            for point in request.bead_points
        }
        
        # Create and fit calibrator
        calibrator = FCMPASSCalibrator(
            wavelength_nm=request.wavelength_nm,
            n_bead=request.n_bead,
            n_ev=request.n_ev,
            n_medium=request.n_medium,
            use_wavelength_dispersion=request.use_wavelength_dispersion,
        )
        calibrator.fit_from_beads(bead_measurements)
        
        # Save if requested (with detector gains and bead kit name)
        saved_path = None
        if request.set_as_active:
            saved_path = save_fcmpass_calibration(
                calibrator,
                detector_gains=request.detector_gains,
                bead_kit_name=request.bead_kit_filename or "",
            )
        
        diagnostics = calibrator.get_diagnostics()
        
        # Check bead kit expiry (Phase 4 - C2)
        expiry_info = None
        if request.bead_kit_filename:
            expiry_info = check_bead_kit_expiry(request.bead_kit_filename)
        
        response = {
            "success": True,
            "message": (
                f"FCMPASS calibration fitted: k={calibrator.k_instrument:.1f} "
                f"(CV={calibrator.k_cv_pct:.1f}%) from {len(request.bead_points)} beads"
            ),
            "set_as_active": request.set_as_active,
            "saved_path": saved_path,
            "diagnostics": diagnostics,
        }
        
        # Add self-validation results to response (Phase 4 - C1)
        if diagnostics.get("self_validation"):
            sv = diagnostics["self_validation"]
            response["self_validation"] = sv
            if not sv.get("all_passed", True):
                response["warnings"] = response.get("warnings", [])
                response["warnings"].append(
                    f"⚠️ Self-validation: {sv.get('n_failed', 0)}/{sv.get('n_beads', 0)} beads "
                    f"exceeded tolerance. Max error: {sv.get('max_error_pct', 0):.1f}%. "
                    f"Review per-bead results before using this calibration."
                )
        
        # Add expiry warnings (Phase 4 - C2)
        if expiry_info and expiry_info.get("warnings"):
            response["warnings"] = response.get("warnings", [])
            response["warnings"].extend(expiry_info["warnings"])
            response["bead_kit_expiry"] = expiry_info
        
        return response
        
    except Exception as e:
        logger.error(f"FCMPASS calibration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"FCMPASS calibration failed: {str(e)}"
        )


@router.get("/fcmpass-status", response_model=dict)
async def get_fcmpass_status():
    """
    Get the status of the active FCMPASS k-based calibration.
    
    Returns calibration info including k, CV%, bead count,
    or 'not_calibrated' status.
    """
    try:
        return get_fcmpass_calibration_status()
    except Exception as e:
        logger.error(f"Failed to get FCMPASS status: {e}")
        return {
            "status": "error",
            "calibrated": False,
            "message": f"Error: {str(e)}",
        }


@router.delete("/fcmpass", response_model=dict)
async def remove_fcmpass_calibration(
    current_user: dict | None = Depends(optional_auth),
):
    """Remove the active FCMPASS calibration."""
    try:
        import datetime
        from src.physics.bead_calibration import FCMPASS_CALIBRATION_FILE
        
        fcmpass_path = CALIBRATION_DIR / FCMPASS_CALIBRATION_FILE
        
        if not fcmpass_path.exists():
            return {
                "success": True,
                "message": "No FCMPASS calibration to remove",
            }
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = CALIBRATION_DIR / f"fcmpass_removed_{timestamp}.json"
        fcmpass_path.rename(archive_path)
        
        return {
            "success": True,
            "message": f"FCMPASS calibration removed (archived as {archive_path.name})",
        }
        
    except Exception as e:
        logger.error(f"Failed to remove FCMPASS calibration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove FCMPASS calibration: {str(e)}"
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


# ============================================================================
# Custom Bead Kit Management
# ============================================================================

class CustomBeadEntry(BaseModel):
    """A single bead population in a custom kit."""
    label: str = Field(..., description="Display label, e.g. '100nm'")
    diameter_nm: float = Field(..., gt=0, le=10000, description="Nominal bead diameter in nm")
    cv_pct: float = Field(5.0, ge=0, le=50, description="Diameter CV from certificate (%)")


class CustomBeadKitRequest(BaseModel):
    """Request to upload a custom bead standard kit."""
    product_name: str = Field(..., min_length=1, max_length=200, description="Kit name (e.g. 'MegaMix-Plus SSC')")
    manufacturer: str = Field("", max_length=200, description="Manufacturer name")
    kit_part_number: str = Field("", max_length=100, description="Catalog / part number")
    lot_number: str = Field("", max_length=100, description="Lot number from certificate")
    material: str = Field("polystyrene_latex", description="Bead material (polystyrene_latex, silica, etc.)")
    refractive_index: float = Field(1.591, ge=1.0, le=2.5, description="Bead RI at reference wavelength")
    ri_measurement_wavelength_nm: float = Field(590.0, ge=200, le=1000, description="Wavelength at which RI was measured")
    nist_traceable: bool = Field(False, description="Whether sizes are NIST-traceable")
    beads: List[CustomBeadEntry] = Field(..., min_length=1, description="Bead populations (at least 1)")
    expiration_date: Optional[str] = Field(None, description="Lot expiration date (YYYY-MM-DD)")
    notes: List[str] = Field(default_factory=list, description="Additional notes")

    @field_validator("product_name")
    @classmethod
    def validate_product_name(cls, v: str) -> str:
        """Ensure product name is safe for filenames."""
        if not v.strip():
            raise ValueError("Product name cannot be empty")
        return v.strip()


def _make_safe_filename(name: str) -> str:
    """Convert product name to a safe JSON filename."""
    # Lowercase, replace spaces/special chars with underscores
    safe = re.sub(r'[^a-z0-9]+', '_', name.lower().strip())
    safe = safe.strip('_')
    if not safe:
        safe = "custom_kit"
    return f"{safe}.json"


@router.post("/bead-standards", response_model=dict)
async def upload_custom_bead_kit(
    request: CustomBeadKitRequest,
    current_user: dict | None = Depends(optional_auth),
):
    """
    Upload a custom bead standard kit.
    
    Creates a JSON datasheet in config/bead_standards/ following the same
    schema as pre-loaded kits. The kit will immediately appear in the
    bead kit selector dropdown.
    """
    try:
        bead_standards_dir = Path(__file__).parent.parent.parent.parent / "config" / "bead_standards"
        bead_standards_dir.mkdir(parents=True, exist_ok=True)

        filename = _make_safe_filename(request.product_name)
        file_path = bead_standards_dir / filename

        # Check for duplicate filename
        if file_path.exists():
            # Append a numeric suffix to avoid overwriting
            base = filename.rsplit('.', 1)[0]
            for i in range(2, 100):
                alt = f"{base}_{i}.json"
                if not (bead_standards_dir / alt).exists():
                    filename = alt
                    file_path = bead_standards_dir / filename
                    break

        # Build bead entries sorted by diameter
        sorted_beads = sorted(request.beads, key=lambda b: b.diameter_nm)
        bead_entries = []
        for b in sorted_beads:
            bead_entries.append({
                "label": b.label,
                "diameter_nm": b.diameter_nm,
                "diameter_um": round(b.diameter_nm / 1000, 4),
                "spec_min_um": round(b.diameter_nm * 0.95 / 1000, 4),
                "spec_max_um": round(b.diameter_nm * 1.05 / 1000, 4),
                "cv_pct": b.cv_pct,
                "target_concentration_ww": None,
                "concentration_particles_per_ml": None,
            })

        # Build the full datasheet JSON
        kit_json = {
            "kit_part_number": request.kit_part_number or "",
            "product_name": request.product_name,
            "lot_number": request.lot_number or "custom",
            "manufacturer": request.manufacturer or "Custom",
            "manufacture_date": None,
            "expiration_date": request.expiration_date,
            "quality_cert_date": None,
            "storage_condition": "2-8°C",
            "material": request.material,
            "refractive_index": request.refractive_index,
            "ri_measurement_wavelength_nm": request.ri_measurement_wavelength_nm,
            "ri_measurement_temperature_c": 20,
            "size_measurement_method": "user-provided",
            "nist_traceable": request.nist_traceable,
            "appearance": None,
            "subcomponents": {
                "Custom": {
                    "sub_lot": request.lot_number or "custom",
                    "description": request.product_name,
                    "overall_refractive_index": request.refractive_index,
                    "overall_appearance": None,
                    "beads": bead_entries,
                }
            },
            "unique_bead_diameters_nm": sorted(set(b.diameter_nm for b in sorted_beads)),
            "is_custom": True,
            "notes": request.notes or [
                f"Custom bead kit uploaded by user",
                f"Material: {request.material}, RI={request.refractive_index}",
            ],
        }

        with open(file_path, 'w') as f:
            json.dump(kit_json, f, indent=2)

        logger.info(f"✅ Custom bead kit saved: {filename} ({len(sorted_beads)} bead sizes)")

        return {
            "success": True,
            "filename": filename,
            "product_name": request.product_name,
            "n_bead_sizes": len(sorted_beads),
            "bead_sizes_nm": sorted(set(b.diameter_nm for b in sorted_beads)),
            "message": f"Custom bead kit '{request.product_name}' saved as {filename}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save custom bead kit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save custom bead kit: {str(e)}"
        )


@router.delete("/bead-standards/{filename}", response_model=dict)
async def delete_bead_standard(
    filename: str,
    current_user: dict | None = Depends(optional_auth),
):
    """
    Delete a custom bead standard kit.
    
    Built-in kits (shipped with the platform) are protected and cannot be deleted.
    Only user-uploaded custom kits can be removed.
    """
    try:
        bead_standards_dir = Path(__file__).parent.parent.parent.parent / "config" / "bead_standards"
        file_path = bead_standards_dir / filename

        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bead standard '{filename}' not found",
            )

        # Safety: Check if it's a custom kit (has "is_custom" flag) 
        # or if we should allow deletion regardless
        try:
            with open(file_path, 'r') as f:
                kit_data = json.load(f)
            if not kit_data.get("is_custom", False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Cannot delete built-in bead standard '{filename}'. Only custom kits can be removed.",
                )
        except json.JSONDecodeError:
            pass  # If we can't parse it, allow deletion

        file_path.unlink()
        logger.info(f"🗑️ Custom bead kit deleted: {filename}")

        return {
            "success": True,
            "filename": filename,
            "message": f"Bead standard '{filename}' deleted",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete bead standard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete bead standard: {str(e)}"
        )


# ============================================================================
# Safety & Validation (Phase 4)
# ============================================================================

class GainCheckRequest(BaseModel):
    """Request to check gain mismatch between calibration and sample."""
    sample_gains: Dict[str, Optional[float]] = Field(
        ..., description="Dict of channel_name → detector voltage from the sample FCS"
    )
    threshold_pct: float = Field(5.0, ge=0.1, le=50.0, description="Mismatch threshold in %")


@router.post("/gain-check", response_model=dict)
async def check_gain_mismatch_endpoint(
    request: GainCheckRequest,
    current_user: dict | None = Depends(optional_auth),
):
    """
    Check detector gain/voltage mismatch between the active calibration
    and a sample FCS file.
    
    Returns per-channel comparison and warning if mismatch > threshold.
    A mismatch means the calibration was run at different instrument settings
    than the sample, so sizing results may be inaccurate.
    """
    try:
        result = check_gain_mismatch(
            sample_gains=request.sample_gains,
            threshold_pct=request.threshold_pct,
        )
        return result
    except Exception as e:
        logger.error(f"Gain mismatch check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gain mismatch check failed: {str(e)}"
        )


@router.get("/bead-kit-expiry", response_model=dict)
async def check_bead_kit_expiry_endpoint(
    filename: Optional[str] = None,
    current_user: dict | None = Depends(optional_auth),
):
    """
    Check expiration status of bead standard kits.
    
    If filename is provided, checks that specific kit.
    Otherwise returns expiry info for all kits.
    
    Returns:
        Status per kit: 'valid', 'expiring_soon' (≤30 days), 'expired', or 'no_expiry_set'
    """
    try:
        result = check_bead_kit_expiry(kit_filename=filename)
        return result
    except Exception as e:
        logger.error(f"Bead kit expiry check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bead kit expiry check failed: {str(e)}"
        )


# ============================================================================
# FCMPASS Calibration Library (Phase 3)
# ============================================================================

@router.get("/fcmpass/list", response_model=dict)
async def list_all_fcmpass_calibrations(
    current_user: dict | None = Depends(optional_auth),
):
    """
    List all FCMPASS calibrations (active + archived).
    
    Returns a list of calibration records with metadata, sorted by date descending.
    Each record includes: id, k_instrument, k_cv_pct, wavelength_nm, n_ev, n_medium,
    n_beads, bead_range_nm, created_at, is_active, status.
    """
    try:
        calibrations = list_fcmpass_calibrations()
        return {
            "calibrations": calibrations,
            "total": len(calibrations),
            "active_count": sum(1 for c in calibrations if c.get("is_active")),
            "archived_count": sum(1 for c in calibrations if not c.get("is_active")),
        }
    except Exception as e:
        logger.error(f"Failed to list FCMPASS calibrations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list FCMPASS calibrations: {str(e)}"
        )


@router.get("/fcmpass/{cal_id}", response_model=dict)
async def get_fcmpass_calibration_detail(
    cal_id: str,
    current_user: dict | None = Depends(optional_auth),
):
    """
    Get full details for a specific FCMPASS calibration by ID.
    
    Args:
        cal_id: Calibration ID (filename stem), e.g. 'fcmpass_calibration' or 'fcmpass_archived_20260217_111046'
    """
    # Sanitize cal_id to prevent path traversal
    if not re.match(r'^[a-zA-Z0-9_-]+$', cal_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid calibration ID format"
        )
    
    data = get_fcmpass_calibration_by_id(cal_id)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calibration '{cal_id}' not found"
        )
    
    return data


@router.put("/fcmpass/{cal_id}/activate", response_model=dict)
async def activate_fcmpass(
    cal_id: str,
    current_user: dict | None = Depends(optional_auth),
):
    """
    Activate an archived FCMPASS calibration.
    
    Swaps the archived calibration into the active slot and archives the
    currently active calibration.
    """
    # Sanitize cal_id to prevent path traversal
    if not re.match(r'^[a-zA-Z0-9_-]+$', cal_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid calibration ID format"
        )
    
    try:
        result = activate_fcmpass_calibration(cal_id)
        return result
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to activate FCMPASS calibration '{cal_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate calibration: {str(e)}"
        )


@router.delete("/fcmpass/{cal_id}", response_model=dict)
async def delete_fcmpass(
    cal_id: str,
    current_user: dict | None = Depends(optional_auth),
):
    """
    Permanently delete an archived FCMPASS calibration.
    
    The active calibration cannot be deleted via this endpoint.
    """
    # Sanitize cal_id
    if not re.match(r'^[a-zA-Z0-9_-]+$', cal_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid calibration ID format"
        )
    
    try:
        result = delete_fcmpass_calibration_by_id(cal_id)
        return result
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delete FCMPASS calibration '{cal_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete calibration: {str(e)}"
        )
