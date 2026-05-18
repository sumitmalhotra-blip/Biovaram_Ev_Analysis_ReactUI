"""
western_routes.py – BioVaram Western Blot API Routes
-----------------------------------------------------
Updated to call AWS Bedrock Nova after CV detection.
Reads AWS credentials from .env via python-dotenv.
All original endpoints preserved unchanged.
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse
import os
import shutil
import json
import traceback
import cv2
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import desc
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path

# ── load .env from project root ───────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    # Walk up from backend/ to find .env at charmi_westernblock/
    _env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(dotenv_path=_env_path)
except ImportError:
    pass  # dotenv not installed – will rely on system env vars

from services.western.western_service import (
    safe_filename,
    preprocess_image,
    detect_lanes,
    detect_bands_in_lane,
    detect_bands_with_confidence,
    build_kda_mapper,
    ai_validate_bands,
    annotate_gel_image,
    UPLOAD_FOLDER,
    RESULT_FOLDER,
)

router = APIRouter()

from services.tem.tem_service import SessionLocal
from services.western.western_model import WesternBlot

# ── AWS / Nova config from environment ───────────────────────────────────────
AWS_REGION      = os.environ.get("AWS_REGION", "us-east-1")
BEDROCK_MODEL   = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")
USE_AI          = os.environ.get("AI_PROVIDER", "").lower() == "bedrock"


# ─────────────────────────────────────────────────────────────────────────────
# Upload
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_western(file: UploadFile = File(...)):
    try:
        filename  = safe_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        image_url = f"/uploads/western/{filename}"

        db = SessionLocal()
        record = WesternBlot(
            image_name=filename,
            image_url=image_url,
            lane_count=0,
            band_count=0,
            kda_data=json.dumps([])
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        db.close()

        return {"id": record.id, "image_url": image_url}

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


# ─────────────────────────────────────────────────────────────────────────────
# Gallery / CRUD
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/last")
def get_last_uploaded():
    try:
        db     = SessionLocal()
        record = db.query(WesternBlot).order_by(desc(WesternBlot.id)).first()
        db.close()
        if not record:
            return {"image": None}
        return {"id": record.id, "image_name": record.image_name, "image_url": record.image_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all")
def get_all_images():
    try:
        db      = SessionLocal()
        records = db.query(WesternBlot).order_by(desc(WesternBlot.id)).all()
        db.close()
        images  = [{"id": r.id, "image_name": r.image_name, "image_url": r.image_url} for r in records]
        return {"images": images}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{image_id}")
def delete_image(image_id: int):
    try:
        db     = SessionLocal()
        record = db.query(WesternBlot).filter(WesternBlot.id == image_id).first()
        if not record:
            db.close()
            raise HTTPException(status_code=404, detail="Image not found")
        file_path = os.path.join(UPLOAD_FOLDER, record.image_name)
        if os.path.exists(file_path):
            os.remove(file_path)
        db.delete(record)
        db.commit()
        db.close()
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def root():
    return {"message": "Western blot backend running"}


# ─────────────────────────────────────────────────────────────────────────────
# Detect ruler bands
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/detect-ruler-bands")
async def detect_ruler_bands(
    file: UploadFile = File(...),
    ruler_lane: int = Form(0),
    top_mark_y: float = Form(...),
    bottom_mark_y: float = Form(...),
):
    temp_path = None
    try:
        filename  = safe_filename(file.filename)
        temp_path = os.path.join(UPLOAD_FOLDER, f"temp_{filename}")

        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        original_gray, processed_img = preprocess_image(temp_path)
        img_h, img_w = processed_img.shape

        top_y    = max(0, min(float(top_mark_y), float(bottom_mark_y)))
        bottom_y = min(img_h - 1, max(float(top_mark_y), float(bottom_mark_y)))

        if bottom_y - top_y < 5:
            return JSONResponse(status_code=400, content={
                "error": "Top and bottom marks are too close. Please select a wider range."
            })

        lane_peaks = sorted(detect_lanes(processed_img))

        if len(lane_peaks) == 0:
            return JSONResponse(status_code=400, content={"error": "No lanes detected."})

        if ruler_lane >= len(lane_peaks):
            return JSONResponse(status_code=400, content={
                "error": f"Ruler lane index {ruler_lane} out of range. Only {len(lane_peaks)} lane(s) detected."
            })

        lane_x = int(lane_peaks[ruler_lane])

        band_peaks, intensities, left, right = detect_bands_in_lane(processed_img, lane_x)

        if len(band_peaks) == 0:
            band_peaks, intensities, left, right = detect_bands_in_lane(
                processed_img, lane_x, half_width=35
            )

        if len(band_peaks) == 0:
            return JSONResponse(status_code=400, content={
                "error": "No bands detected in ruler lane. Try adjusting contrast or lane position."
            })

        filtered_positions = [int(p) for p in band_peaks if top_y <= float(p) <= bottom_y]

        if len(filtered_positions) == 0:
            all_positions = [int(p) for p in band_peaks]
            return JSONResponse(status_code=400, content={
                "error": (
                    f"No bands found between y={int(top_y)} and y={int(bottom_y)}. "
                    f"Detected positions: {all_positions}. Try widening your selection."
                )
            })

        if len(filtered_positions) < 2:
            return JSONResponse(status_code=400, content={
                "error": "Only 1 band detected. At least 2 needed for kDa interpolation."
            })

        filtered_positions = sorted(filtered_positions)
        ruler_bands = [
            {"id": idx, "x": lane_x, "y": pos, "kda": "", "concentration": ""}
            for idx, pos in enumerate(filtered_positions, start=1)
        ]

        return {"status": "success", "lane_x": lane_x, "ruler_bands": ruler_bands}

    except ValueError as ve:
        traceback.print_exc()
        return JSONResponse(status_code=400, content={"error": str(ve)})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"Unexpected error: {str(e)}"})
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# Analyze  ← Nova is called here after CV detection
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/analyze")
async def analyze_western_blot(
    file: UploadFile = File(...),
    ruler_lane: int = Form(0),
    volume_loaded: float = Form(10.0),
    reference_intensity: Optional[float] = Form(None),
    reference_concentration: Optional[float] = Form(None),
    ruler_marks: Optional[str] = Form(None),
    use_ai: Optional[bool] = Form(None),   # frontend can override
):
    """
    Full analysis:
    1. CV pipeline detects lanes + bands with confidence scores
    2. kDa mapper built from ruler marks
    3. (Optional) Nova validates CV results and finds missed bands
    4. Annotated image saved with confidence colour coding
    """
    try:
        filename  = safe_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        original_gray, processed_img = preprocess_image(file_path)
        lane_peaks = sorted(detect_lanes(processed_img))

        if len(lane_peaks) == 0:
            return JSONResponse(status_code=400, content={"error": "No lanes detected"})

        # ── Parse ruler marks ─────────────────────────────────────────────
        parsed_ruler_marks = []
        if ruler_marks:
            try:
                parsed_ruler_marks = json.loads(ruler_marks)
            except json.JSONDecodeError:
                return JSONResponse(status_code=400, content={"error": "Invalid ruler_marks JSON"})

        # ── Build kDa mapper ──────────────────────────────────────────────
        if len(parsed_ruler_marks) >= 2:
            try:
                ruler_positions  = [float(m["y"])   for m in parsed_ruler_marks]
                ruler_kda_values = [float(m["kda"]) for m in parsed_ruler_marks]
                if any(v <= 0 for v in ruler_kda_values):
                    return JSONResponse(status_code=400, content={
                        "error": "All kDa values must be positive numbers."
                    })
                pixel_to_kda = build_kda_mapper(ruler_positions, ruler_kda_values)
            except (KeyError, ValueError) as e:
                return JSONResponse(status_code=400, content={
                    "error": f"Invalid ruler mark data: {str(e)}"
                })
        else:
            band_peaks_ruler, _, _, _ = detect_bands_in_lane(
                processed_img, int(lane_peaks[ruler_lane])
            )
            if len(band_peaks_ruler) < 2:
                return JSONResponse(status_code=400, content={
                    "error": "Not enough ruler bands for kDa mapping. Please mark the ruler lane."
                })
            default_kda  = [180, 130, 100, 70, 55, 40, 35, 25, 15, 10]
            pixel_to_kda = build_kda_mapper(band_peaks_ruler, default_kda)

        # ── CV band detection (with confidence) ───────────────────────────
        band_data    = {}
        for lane_index, lane_x in enumerate(lane_peaks):
            band_peaks, intensities, confidence, left, right = detect_bands_with_confidence(
                processed_img, int(lane_x)
            )
            band_data[lane_index] = {
                "lane_x":     int(lane_x),
                "left":       int(left),
                "right":      int(right),
                "positions":  band_peaks,
                "intensities": intensities,
                "confidence": confidence,
            }

        # ── Build frontend band list ──────────────────────────────────────
        frontend_bands = []
        results        = []
        band_counter   = 1

        for lane, data in band_data.items():
            positions   = data["positions"]
            intensities = data["intensities"]
            confidences = data["confidence"] if len(data["confidence"]) == len(positions) else [1.0] * len(positions)

            for pos, intensity, conf in zip(positions, intensities, confidences):
                try:
                    kda_value = pixel_to_kda(float(pos))
                except Exception:
                    kda_value = 0.0

                relative_quantity = (float(intensity) / 100.0) * volume_loaded

                calculated_concentration = None
                if (
                    reference_intensity is not None
                    and reference_concentration is not None
                    and reference_intensity != 0
                ):
                    calculated_concentration = (
                        float(intensity) / float(reference_intensity)
                    ) * float(reference_concentration)

                display_concentration = (
                    round(float(calculated_concentration), 3)
                    if calculated_concentration is not None
                    else round(float(relative_quantity), 3)
                )

                band_label = f"B{band_counter}"

                frontend_bands.append({
                    "id":              band_counter,
                    "name":            band_label,
                    "lane":            int(lane),
                    "x":               int(data["lane_x"]),
                    "y":               int(pos),
                    "w":               50,
                    "h":               12,
                    "molecularWeight": round(float(kda_value), 2),
                    "intensity":       round(float(intensity), 3),
                    "relativeQuantity": round(float(relative_quantity), 3),
                    "concentration":   display_concentration,
                    "confidence":      round(float(conf), 3),   # NEW
                })

                results.append({
                    "Lane":            int(lane),
                    "Band":            band_label,
                    "kDa":             round(float(kda_value), 2),
                    "Intensity":       round(float(intensity), 3),
                    "Relative Quantity": round(float(relative_quantity), 3),
                    "X_Position":      int(data["lane_x"]),
                    "Y_Position":      int(pos),
                    "Confidence":      round(float(conf), 3),   # NEW
                })

                band_counter += 1

        # ── Nova AI validation ────────────────────────────────────────────
        # Runs if: frontend sends use_ai=true, OR AI_PROVIDER=bedrock in .env
        # Nova acts as expert second opinion on top of CV detection
        run_ai      = use_ai if use_ai is not None else USE_AI
        ai_result   = {}
        suggested_bands = []

        if run_ai:
            print(f"[Nova] Running AI validation on {len(frontend_bands)} CV bands...")
            ai_result = ai_validate_bands(
                image_path=file_path,
                cv_bands=frontend_bands,
                lane_count=len(lane_peaks),
                aws_region=AWS_REGION,
                model_id=BEDROCK_MODEL,
            )

            if ai_result.get("ai_used"):
                # Replace band list with Nova-validated version
                frontend_bands  = ai_result.get("validated_bands", frontend_bands)
                suggested_bands = ai_result.get("suggested_bands", [])
                print(f"[Nova] Validated: {len(frontend_bands)} bands, "
                      f"suggested {len(suggested_bands)} new, "
                      f"removed {len(ai_result.get('removed_bands', []))}")
            else:
                print(f"[Nova] Fell back to CV only: {ai_result.get('error', '')}")

        # ── Save CSV ──────────────────────────────────────────────────────
        df       = pd.DataFrame(results)
        csv_path = os.path.join(RESULT_FOLDER, "results.csv")
        df.to_csv(csv_path, index=False)

        # ── Annotate image (confidence-coloured) ──────────────────────────
        annotated      = annotate_gel_image(
            original_gray,
            [int(lx) for lx in lane_peaks],
            frontend_bands,
            suggested_bands=suggested_bands if suggested_bands else None,
        )
        annotated_path = os.path.join(RESULT_FOLDER, "annotated.png")
        cv2.imwrite(annotated_path, annotated)

        # ── 3D intensity surface plot ─────────────────────────────────────
        try:
            step   = max(1, min(original_gray.shape[0], original_gray.shape[1]) // 200)
            z_data = original_gray[::step, ::step].astype(float)
            fig_3d = go.Figure(data=[go.Surface(
                z=z_data, colorscale="Viridis", showscale=True,
                colorbar=dict(title="Intensity"),
            )])
            fig_3d.update_layout(
                title="Western Blot — 3D Intensity Surface",
                scene=dict(xaxis_title="X (pixels)", yaxis_title="Y (pixels)",
                           zaxis_title="Intensity"),
                margin=dict(l=0, r=0, t=40, b=0),
            )
            plot_path = os.path.join(RESULT_FOLDER, "3d_plot.html")
            fig_3d.write_html(plot_path, include_plotlyjs="cdn")
        except Exception as _e:
            print(f"[WARN] 3D plot failed: {_e}")

        return {
            "status":           "success",
            "lanes_detected":   len(lane_peaks),
            "band_count":       len(frontend_bands),
            "annotated_image":  "/results/western/annotated.png",
            "csv_file":         "/results/western/results.csv",
            "plot_url":         "/results/western/3d_plot.html",
            "bands":            frontend_bands,
            "results":          results,
            "image_width":      int(original_gray.shape[1]),
            "image_height":     int(original_gray.shape[0]),
            # Nova metadata
            "ai_used":              ai_result.get("ai_used", False),
            "ai_quality":           ai_result.get("quality", None),
            "ai_summary":           ai_result.get("summary", None),
            "ai_lane_quality":      ai_result.get("lane_quality", []),
            "ai_similar_lanes":     ai_result.get("similar_lanes", []),
            "ai_contamination":     ai_result.get("contamination", False),
            "suggested_bands":      suggested_bands,
        }

    except ValueError as ve:
        traceback.print_exc()
        return JSONResponse(status_code=400, content={"error": str(ve)})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"Unexpected error: {str(e)}"})


# ─────────────────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────────────────

class ReportBandItem(BaseModel):
    id:               int
    name:             str
    lane:             int
    x:                int
    y:                int
    molecularWeight:  float
    intensity:        float
    relativeQuantity: float
    concentration:    float
    confidence:       Optional[float] = 1.0   # NEW – optional for backward compat


class BandReportRequest(BaseModel):
    bands: List[ReportBandItem]


@router.post("/report/band-report")
def generate_band_report(payload: BandReportRequest):
    try:
        if not payload.bands:
            raise HTTPException(status_code=400, detail="No bands provided")

        band_dicts = [b.dict() for b in payload.bands]
        df         = pd.DataFrame(band_dicts)

        summary = {
            "total_bands":     len(df),
            "lanes_covered":   sorted(df["lane"].unique().tolist()),
            "kda_range":       {"min": round(float(df["molecularWeight"].min()), 2),
                                "max": round(float(df["molecularWeight"].max()), 2)},
            "intensity":       {"mean": round(float(df["intensity"].mean()), 3),
                                "min":  round(float(df["intensity"].min()),  3),
                                "max":  round(float(df["intensity"].max()),  3)},
            "relative_quantity": {"mean":  round(float(df["relativeQuantity"].mean()), 3),
                                  "total": round(float(df["relativeQuantity"].sum()),  3)},
            "concentration":   {"mean":  round(float(df["concentration"].mean()), 3),
                                "total": round(float(df["concentration"].sum()),  3)},
            "avg_confidence":  round(float(df["confidence"].mean()), 3) if "confidence" in df else None,
        }

        report_csv = os.path.join(RESULT_FOLDER, "band_report.csv")
        df.rename(columns={
            "molecularWeight": "kDa",
            "relativeQuantity": "Relative Quantity",
        }).to_csv(report_csv, index=False)

        return {
            "status":     "success",
            "report_csv": "/results/western/band_report.csv",
            "summary":    summary,
            "bands":      band_dicts,
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
