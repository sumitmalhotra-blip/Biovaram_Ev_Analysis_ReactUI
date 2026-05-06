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

from services.western.western_service import (
    safe_filename,
    preprocess_image,
    detect_lanes,
    detect_bands_in_lane,
    build_kda_mapper,
    UPLOAD_FOLDER,
    RESULT_FOLDER,
)

router = APIRouter()

from services.tem.tem_service import SessionLocal
from services.western.western_model import WesternBlot


# ─────────────────────────────────────────────────────────────────────────────
# Upload
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_western(file: UploadFile = File(...)):
    try:
        filename = safe_filename(file.filename)
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
        db = SessionLocal()
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
        db = SessionLocal()
        records = db.query(WesternBlot).order_by(desc(WesternBlot.id)).all()
        db.close()
        images = [{"id": r.id, "image_name": r.image_name, "image_url": r.image_url} for r in records]
        return {"images": images}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{image_id}")
def delete_image(image_id: int):
    try:
        db = SessionLocal()
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
# Detect ruler bands  ← main fix here
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/detect-ruler-bands")
async def detect_ruler_bands(
    file: UploadFile = File(...),
    ruler_lane: int = Form(0),
    top_mark_y: float = Form(...),
    bottom_mark_y: float = Form(...),
):
    """
    Detect bands inside the ruler lane that fall between the user-marked
    top_mark_y and bottom_mark_y pixel coordinates.

    The frontend (RulerMarker.tsx) already converts click coordinates to
    natural-image pixels before sending, so no additional scaling is needed.
    """
    temp_path = None
    try:
        filename = safe_filename(file.filename)
        temp_path = os.path.join(UPLOAD_FOLDER, f"temp_{filename}")

        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        original_gray, processed_img = preprocess_image(temp_path)

        img_h, img_w = processed_img.shape

        # ── Validate top/bottom marks are inside image bounds ──────────────
        top_y    = max(0, min(float(top_mark_y),    float(bottom_mark_y)))
        bottom_y = min(img_h - 1, max(float(top_mark_y), float(bottom_mark_y)))

        if bottom_y - top_y < 5:
            return JSONResponse(
                status_code=400,
                content={"error": "Top and bottom marks are too close together. Please select a wider range."}
            )

        # ── Detect lanes ───────────────────────────────────────────────────
        lane_peaks = sorted(detect_lanes(processed_img))

        if len(lane_peaks) == 0:
            return JSONResponse(status_code=400, content={"error": "No lanes detected in the image."})

        if ruler_lane >= len(lane_peaks):
            return JSONResponse(
                status_code=400,
                content={"error": f"Ruler lane index {ruler_lane} is out of range. Only {len(lane_peaks)} lane(s) detected."}
            )

        lane_x = int(lane_peaks[ruler_lane])

        # ── Detect bands in the ruler lane ────────────────────────────────
        band_peaks, intensities, left, right = detect_bands_in_lane(processed_img, lane_x)

        if band_peaks is None or len(band_peaks) == 0:
            # Fallback: try with a wider half-width
            band_peaks, intensities, left, right = detect_bands_in_lane(
                processed_img, lane_x, half_width=35
            )

        if band_peaks is None or len(band_peaks) == 0:
            return JSONResponse(
                status_code=400,
                content={"error": "No bands detected in the ruler lane. Try adjusting the image contrast or lane position."}
            )

        # ── Filter to bands between top and bottom marks ──────────────────
        filtered_positions = [
            int(pos) for pos in band_peaks
            if top_y <= float(pos) <= bottom_y
        ]

        if len(filtered_positions) == 0:
            # Give the user helpful context: how many bands exist vs range
            all_positions = [int(p) for p in band_peaks]
            return JSONResponse(
                status_code=400,
                content={
                    "error": (
                        f"No bands found between y={int(top_y)} and y={int(bottom_y)}. "
                        f"Detected band positions in this lane: {all_positions}. "
                        "Try widening your top/bottom selection range."
                    )
                }
            )

        if len(filtered_positions) < 2:
            return JSONResponse(
                status_code=400,
                content={
                    "error": (
                        f"Only 1 band detected between y={int(top_y)} and y={int(bottom_y)}. "
                        "At least 2 ruler bands are required for kDa interpolation. "
                        "Try widening your selection range."
                    )
                }
            )

        filtered_positions = sorted(filtered_positions)

        ruler_bands = [
            {"id": idx, "x": lane_x, "y": pos, "kda": "", "concentration": ""}
            for idx, pos in enumerate(filtered_positions, start=1)
        ]

        return {
            "status": "success",
            "lane_x": lane_x,
            "ruler_bands": ruler_bands,
        }

    except ValueError as ve:
        # Raised by preprocess_image when the file can't be read
        traceback.print_exc()
        return JSONResponse(status_code=400, content={"error": str(ve)})

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"Unexpected error: {str(e)}"})

    finally:
        # Always clean up the temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# Analyze
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/analyze")
async def analyze_western_blot(
    file: UploadFile = File(...),
    ruler_lane: int = Form(0),
    volume_loaded: float = Form(10.0),
    reference_intensity: Optional[float] = Form(None),
    reference_concentration: Optional[float] = Form(None),
    ruler_marks: Optional[str] = Form(None),
):
    """
    Full analysis endpoint.

    ruler_marks (JSON string) – list of {id, x, y, kda, concentration} objects
    from the frontend. Their y positions (already in natural-image pixels) and
    kda values are used to build the kDa mapper.
    """
    try:
        filename = safe_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        original_gray, processed_img = preprocess_image(file_path)
        lane_peaks = sorted(detect_lanes(processed_img))

        if len(lane_peaks) == 0:
            return JSONResponse(status_code=400, content={"error": "No lanes detected"})

        # ── Parse ruler_marks sent from frontend ──────────────────────────
        parsed_ruler_marks = []
        if ruler_marks:
            try:
                parsed_ruler_marks = json.loads(ruler_marks)
            except json.JSONDecodeError:
                return JSONResponse(status_code=400, content={"error": "Invalid ruler_marks JSON"})

        # ── Build kDa mapper from ruler marks ────────────────────────────
        # Use the ruler marks provided by the user (y position + kda value)
        if len(parsed_ruler_marks) >= 2:
            try:
                ruler_positions = [float(m["y"]) for m in parsed_ruler_marks]
                ruler_kda_values = [float(m["kda"]) for m in parsed_ruler_marks]

                # Validate kDa values are positive
                if any(v <= 0 for v in ruler_kda_values):
                    return JSONResponse(
                        status_code=400,
                        content={"error": "All kDa values must be positive numbers greater than 0."}
                    )

                pixel_to_kda = build_kda_mapper(ruler_positions, ruler_kda_values)

            except (KeyError, ValueError) as e:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Invalid ruler mark data: {str(e)}"}
                )
        else:
            # Fallback: use default ladder values against ruler lane band positions
            band_peaks_ruler, _, _, _ = detect_bands_in_lane(
                processed_img, int(lane_peaks[ruler_lane])
            )
            if len(band_peaks_ruler) < 2:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Not enough ruler bands detected for kDa mapping. Please mark the ruler lane first."}
                )
            default_kda = [180, 130, 100, 70, 55, 40, 35, 25, 15, 10]
            pixel_to_kda = build_kda_mapper(band_peaks_ruler, default_kda)

        # ── Detect bands in all lanes ─────────────────────────────────────
        band_data = {}
        for lane_index, lane_x in enumerate(lane_peaks):
            band_peaks, intensities, left, right = detect_bands_in_lane(
                processed_img, int(lane_x)
            )
            band_data[lane_index] = {
                "lane_x": int(lane_x),
                "left": int(left),
                "right": int(right),
                "positions": band_peaks,
                "intensities": intensities,
            }

        # ── Build results ─────────────────────────────────────────────────
        results = []
        frontend_bands = []
        band_counter = 1

        # Build concentration lookup from ruler marks
        ruler_conc_lookup = {}
        if parsed_ruler_marks:
            for m in parsed_ruler_marks:
                try:
                    ruler_conc_lookup[float(m["y"])] = float(m.get("concentration", 0) or 0)
                except (ValueError, KeyError):
                    pass

        for lane, data in band_data.items():
            for pos, intensity in zip(data["positions"], data["intensities"]):
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
                    "id": band_counter,
                    "name": band_label,
                    "lane": int(lane),
                    "x": int(data["lane_x"]),
                    "y": int(pos),
                    "w": 50,
                    "h": 12,
                    "molecularWeight": round(float(kda_value), 2),
                    "intensity": round(float(intensity), 3),
                    "relativeQuantity": round(float(relative_quantity), 3),
                    "concentration": display_concentration,
                })

                results.append({
                    "Lane": int(lane),
                    "Band": band_label,
                    "kDa": round(float(kda_value), 2),
                    "Intensity": round(float(intensity), 3),
                    "Relative Quantity": round(float(relative_quantity), 3),
                    "X_Position": int(data["lane_x"]),
                    "Y_Position": int(pos),
                })

                band_counter += 1

        # ── Save CSV ──────────────────────────────────────────────────────
        df = pd.DataFrame(results)
        csv_path = os.path.join(RESULT_FOLDER, "results.csv")
        df.to_csv(csv_path, index=False)

        # ── Annotate image ────────────────────────────────────────────────
        annotated = cv2.cvtColor(original_gray, cv2.COLOR_GRAY2BGR)

        for lane, data in band_data.items():
            lane_x = int(data["lane_x"])
            cv2.putText(
                annotated, f"Lane {lane + 1}", (lane_x - 40, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (139, 0, 0), 1, cv2.LINE_AA
            )

        for band in frontend_bands:
            x = int(band["x"])
            y = int(band["y"])
            label = band["name"]
            text_x = x + 12
            text_y = y - 4
            cv2.putText(annotated, label, (text_x, text_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(annotated, label, (text_x, text_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)

        annotated_path = os.path.join(RESULT_FOLDER, "annotated.png")
        cv2.imwrite(annotated_path, annotated)

        # ── Generate 3D intensity surface plot ───────────────────────────
        try:
            step = max(1, min(original_gray.shape[0], original_gray.shape[1]) // 200)
            z_data = original_gray[::step, ::step].astype(float)
            fig_3d = go.Figure(data=[go.Surface(
                z=z_data,
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title="Intensity"),
            )])
            fig_3d.update_layout(
                title="Western Blot — 3D Intensity Surface",
                scene=dict(
                    xaxis_title="X (pixels)",
                    yaxis_title="Y (pixels)",
                    zaxis_title="Intensity",
                ),
                margin=dict(l=0, r=0, t=40, b=0),
            )
            plot_3d_path = os.path.join(RESULT_FOLDER, "3d_plot.html")
            fig_3d.write_html(plot_3d_path, include_plotlyjs="cdn")
        except Exception as _e3d:
            print(f"[WARN] 3D plot generation failed: {_e3d}")

        return {
            "status": "success",
            "lanes_detected": len(lane_peaks),
            "band_count": len(frontend_bands),
            "annotated_image": "/results/western/annotated.png",
            "csv_file": "/results/western/results.csv",
            "plot_url": "/results/western/3d_plot.html",
            "bands": frontend_bands,
            "results": results,
            "image_width": int(original_gray.shape[1]),
            "image_height": int(original_gray.shape[0]),
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
    id: int
    name: str
    lane: int
    x: int
    y: int
    molecularWeight: float
    intensity: float
    relativeQuantity: float
    concentration: float


class BandReportRequest(BaseModel):
    bands: List[ReportBandItem]


@router.post("/report/band-report")
def generate_band_report(payload: BandReportRequest):
    try:
        if not payload.bands:
            raise HTTPException(status_code=400, detail="No bands provided")

        band_dicts = [b.dict() for b in payload.bands]
        df = pd.DataFrame(band_dicts)

        summary = {
            "total_bands": len(df),
            "lanes_covered": sorted(df["lane"].unique().tolist()),
            "kda_range": {
                "min": round(float(df["molecularWeight"].min()), 2),
                "max": round(float(df["molecularWeight"].max()), 2),
            },
            "intensity": {
                "mean": round(float(df["intensity"].mean()), 3),
                "min":  round(float(df["intensity"].min()), 3),
                "max":  round(float(df["intensity"].max()), 3),
            },
            "relative_quantity": {
                "mean":  round(float(df["relativeQuantity"].mean()), 3),
                "total": round(float(df["relativeQuantity"].sum()), 3),
            },
            "concentration": {
                "mean":  round(float(df["concentration"].mean()), 3),
                "total": round(float(df["concentration"].sum()), 3),
            },
        }

        report_csv_path = os.path.join(RESULT_FOLDER, "band_report.csv")
        df.rename(columns={
            "molecularWeight": "kDa",
            "relativeQuantity": "Relative Quantity",
        }).to_csv(report_csv_path, index=False)

        return {
            "status": "success",
            "report_csv": "/results/western/band_report.csv",
            "summary": summary,
            "bands": band_dicts,
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})