from fastapi import APIRouter, UploadFile, File, Query, HTTPException, Form
from typing import List, Optional
import os
import uuid
import cv2
import json
import numpy as np
from pathlib import Path

from services.tem.tem_service import (
    ImageRecord,
    CircleIn,
    ScaleInput,
    MinNmInput,
    HideFilterInput,
    DeleteCirclesInput,
    LineIntensityRequest,
    ShapeFeedbackRequest,
    db_session,
    validate_image,
    get_display_url,
    get_original_url,
    image_path_from_url,
    get_original_image_path,
    find_image_by_id_db,
    normalize_viability,
    nm_per_pixel_from_scale,
    get_nm_per_pixel_for_record,
    get_min_nm_value,
    apply_min_nm_filter,
    compute_radial_intensity,
    run_analysis,
    safe_int,
    decode_upload_to_bgr,
    save_shape_outputs,
    shape_particles_to_boxes,
    run_shape_pipeline_on_bgr,
    build_table_response,
    find_nearest_particle,
    DEFAULT_MIN_NM,
    DEFAULT_NM_PER_PIXEL,
    ALLOWED_TYPES,
    MAX_FILE_SIZE,
    MAX_FILES,
    UPLOAD_DIR,
)

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/upload-multiple-images/{user_id}")
async def upload_images(
    user_id: str,
    files: List[UploadFile] = File(...),
    method: str = Query("cnn", pattern="^(rulebased|voronoi|ai|cnn)$"),
):
    db = db_session()
    results = []
    nm_per_pixel = DEFAULT_NM_PER_PIXEL

    try:
        if len(files) > MAX_FILES:
            raise HTTPException(status_code=400, detail="Max 5 files allowed")

        os.makedirs(UPLOAD_DIR, exist_ok=True)

        for file in files:
            if file.content_type not in ALLOWED_TYPES:
                raise HTTPException(status_code=400, detail=f"Invalid file type: {file.filename}")

            content = await file.read()

            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail=f"File too large: {file.filename}")

            if not validate_image(content):
                raise HTTPException(status_code=400, detail=f"Invalid image file: {file.filename}")

            image_id = str(uuid.uuid4())
            safe_name = Path(file.filename).name
            filename = f"{image_id}_{safe_name}"
            path = os.path.join(UPLOAD_DIR, filename)

            # IMPORTANT: keep all TEM image URLs under /uploads/tem/
            url = f"/uploads/tem/{filename}"

            with open(path, "wb") as f:
                f.write(content)

            try:
                boxes = await run_analysis(method, path, nm_per_pixel)
            except Exception as e:
                print(f"[ERROR] Analysis failed: {e}")
                raise HTTPException(status_code=500, detail="Analysis failed")

            rec = ImageRecord(
                user_id=user_id,
                image_id=image_id,
                image_url=url,
                original_image_url=url,
                display_image_url=url,
                boxes=boxes,
                scale=None,
                min_nm=DEFAULT_MIN_NM,
                analysis_method=method,
            )

            try:
                db.add(rec)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"[ERROR] DB error: {e}")
                raise HTTPException(status_code=500, detail="DB error")

            results.append(
                {
                    "image_id": image_id,
                    "image_url": url,
                    "boxes": apply_min_nm_filter(
                        boxes,
                        DEFAULT_MIN_NM,
                        fallback_nm_per_pixel=nm_per_pixel,
                    ),
                    "scale": None,
                    "min_nm": DEFAULT_MIN_NM,
                    "analysis_method": method,
                }
            )

        return results
    finally:
        db.close()


@router.get("/images/{user_id}")
def get_user_images(user_id: str):
    db = db_session()
    try:
        rows = db.query(ImageRecord).filter(ImageRecord.user_id == user_id).all()
        out = {}
        for r in rows:
            try:
                min_nm = get_min_nm_value(r.min_nm)
                npp = get_nm_per_pixel_for_record(r)
                out[r.image_id] = {
                    "image_url": get_display_url(r),
                    "original_image_url": get_original_url(r),
                    "scale": r.scale,
                    "min_nm": min_nm,
                    "boxes": apply_min_nm_filter(r.boxes or [], min_nm, fallback_nm_per_pixel=npp),
                    "analysis_method": r.analysis_method,
                }
            except Exception as e:
                print(f"[WARN] Skipping image {r.image_id} due to error: {e}")
        return out
    except Exception as e:
        print(f"[ERROR] get_user_images failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch images")
    finally:
        db.close()


@router.get("/images/{user_id}/{image_id}")
def get_image(user_id: str, image_id: str):
    db = db_session()
    try:
        rec = (
            db.query(ImageRecord)
            .filter(ImageRecord.user_id == user_id, ImageRecord.image_id == image_id)
            .first()
        )
        if not rec:
            return {"error": "Image not found"}

        min_nm = get_min_nm_value(rec.min_nm)
        npp = get_nm_per_pixel_for_record(rec)
        return {
            "image_url": get_display_url(rec),
            "original_image_url": get_original_url(rec),
            "scale": rec.scale,
            "min_nm": min_nm,
            "boxes": apply_min_nm_filter(rec.boxes or [], min_nm, fallback_nm_per_pixel=npp),
            "analysis_method": rec.analysis_method,
        }
    finally:
        db.close()


@router.post("/images/{user_id}/{image_id}/scale")
def set_scale(user_id: str, image_id: str, scale: ScaleInput):
    db = db_session()
    try:
        rec = (
            db.query(ImageRecord)
            .filter(ImageRecord.user_id == user_id, ImageRecord.image_id == image_id)
            .first()
        )
        if not rec:
            return {"error": "Image not found"}

        rec.scale = scale.model_dump()
        npp = nm_per_pixel_from_scale(rec.scale)
        boxes = rec.boxes or []

        if npp is not None:
            for c in boxes:
                try:
                    rpx = float(c.get("r", 0))
                    c["diameter_nm"] = round((rpx * 2.0) * npp, 2)
                except Exception:
                    pass
            rec.boxes = boxes

        if rec.min_nm is None:
            rec.min_nm = DEFAULT_MIN_NM

        db.commit()
        min_nm = get_min_nm_value(rec.min_nm)

        return {
            "status": "success",
            "scale": rec.scale,
            "min_nm": min_nm,
            "boxes": apply_min_nm_filter(boxes, min_nm, fallback_nm_per_pixel=get_nm_per_pixel_for_record(rec)),
        }
    finally:
        db.close()


@router.get("/images/{user_id}/{image_id}/min_nm")
def get_min_nm_api(user_id: str, image_id: str):
    db = db_session()
    try:
        rec = (
            db.query(ImageRecord)
            .filter(ImageRecord.user_id == user_id, ImageRecord.image_id == image_id)
            .first()
        )
        if not rec:
            return {"error": "Image not found"}
        return {"min_nm": get_min_nm_value(rec.min_nm)}
    finally:
        db.close()


@router.post("/images/{user_id}/{image_id}/min_nm")
def set_min_nm(user_id: str, image_id: str, payload: MinNmInput):
    db = db_session()
    try:
        rec = (
            db.query(ImageRecord)
            .filter(ImageRecord.user_id == user_id, ImageRecord.image_id == image_id)
            .first()
        )
        if not rec:
            return {"error": "Image not found"}

        min_nm = float(payload.min_nm)
        if min_nm < DEFAULT_MIN_NM:
            min_nm = DEFAULT_MIN_NM

        rec.min_nm = min_nm
        db.commit()

        return {
            "status": "success",
            "min_nm": min_nm,
            "boxes": apply_min_nm_filter(rec.boxes or [], min_nm, fallback_nm_per_pixel=get_nm_per_pixel_for_record(rec)),
            "scale": rec.scale,
            "image_url": get_display_url(rec),
        }
    finally:
        db.close()


@router.post("/images/{user_id}/{image_id}/hide-filter")
def set_hide_filter(user_id: str, image_id: str, payload: HideFilterInput):
    db = db_session()
    try:
        rec = (
            db.query(ImageRecord)
            .filter(ImageRecord.user_id == user_id, ImageRecord.image_id == image_id)
            .first()
        )
        if not rec:
            return {"error": "Image not found"}

        min_nm = float(payload.hide_below_nm)
        if min_nm <= 0:
            min_nm = DEFAULT_MIN_NM

        rec.min_nm = min_nm
        db.commit()

        return {
            "status": "success",
            "min_nm": min_nm,
            "hide_below_nm": min_nm,
            "boxes": apply_min_nm_filter(rec.boxes or [], min_nm, fallback_nm_per_pixel=get_nm_per_pixel_for_record(rec)),
            "scale": rec.scale,
            "image_url": get_display_url(rec),
        }
    finally:
        db.close()


@router.post("/images/{user_id}/{image_id}/circles")
def update_circles(user_id: str, image_id: str, circles: List[CircleIn], fast: int = Query(1)):
    db = db_session()
    try:
        rec = (
            db.query(ImageRecord)
            .filter(ImageRecord.user_id == user_id, ImageRecord.image_id == image_id)
            .first()
        )
        if not rec:
            return {"error": "Image not found"}

        scale = rec.scale
        npp = nm_per_pixel_from_scale(scale) or DEFAULT_NM_PER_PIXEL
        min_nm = get_min_nm_value(rec.min_nm)

        old_boxes = rec.boxes or []
        old_by_num = {}
        for b in old_boxes:
            try:
                if b.get("number") is not None:
                    old_by_num[int(b["number"])] = b
            except Exception:
                pass

        enriched = []
        for idx, c in enumerate(circles, start=1):
            circle_dict = c.model_dump()
            circle_dict["number"] = idx
            circle_dict["viability"] = normalize_viability(circle_dict.get("viability"))

            old = old_by_num.get(idx)
            if old:
                if circle_dict.get("intensity") is None and old.get("intensity") is not None:
                    circle_dict["intensity"] = old.get("intensity")
                if circle_dict.get("shape") is None and old.get("shape") is not None:
                    circle_dict["shape"] = old.get("shape")
                if circle_dict.get("confidence") is None and old.get("confidence") is not None:
                    circle_dict["confidence"] = old.get("confidence")
                if circle_dict.get("votes") is None and old.get("votes") is not None:
                    circle_dict["votes"] = old.get("votes")
                if circle_dict.get("vote_summary") is None and old.get("vote_summary") is not None:
                    circle_dict["vote_summary"] = old.get("vote_summary")

            try:
                diameter_px = float(circle_dict["r"]) * 2.0
                circle_dict["diameter_nm"] = round(diameter_px * npp, 2)
            except Exception:
                pass

            enriched.append(circle_dict)

        img_gray = None
        img_path = get_original_image_path(rec)
        if img_path and os.path.exists(img_path):
            img_gray = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

        if img_gray is not None:
            for c in enriched:
                if c.get("intensity") is None:
                    c["intensity"] = compute_radial_intensity(img_gray, c["x"], c["y"], c["r"])

        rec.boxes = enriched
        db.commit()

        return {
            "status": "success",
            "boxes": apply_min_nm_filter(enriched, min_nm, fallback_nm_per_pixel=npp),
            "scale": scale,
            "min_nm": min_nm,
            "fast": int(fast),
        }
    finally:
        db.close()


@router.post("/images/{user_id}/{image_id}/circles/delete")
def delete_circles(user_id: str, image_id: str, payload: DeleteCirclesInput):
    db = db_session()
    try:
        rec = (
            db.query(ImageRecord)
            .filter(ImageRecord.user_id == user_id, ImageRecord.image_id == image_id)
            .first()
        )
        if not rec:
            return {"error": "Image not found"}

        min_nm = get_min_nm_value(rec.min_nm)
        to_delete = set(int(x) for x in (payload.numbers or []) if str(x).isdigit())

        old_boxes = rec.boxes or []
        kept = []
        for b in old_boxes:
            try:
                n = b.get("number")
                if n is None:
                    continue
                if int(n) in to_delete:
                    continue
                kept.append(b)
            except Exception:
                kept.append(b)

        renumbered = []
        for idx, b in enumerate(kept, start=1):
            bb = dict(b)
            bb["number"] = idx
            renumbered.append(bb)

        rec.boxes = renumbered
        db.commit()

        return {
            "status": "success",
            "deleted": sorted(list(to_delete)),
            "boxes": apply_min_nm_filter(renumbered, min_nm, fallback_nm_per_pixel=get_nm_per_pixel_for_record(rec)),
            "scale": rec.scale,
            "min_nm": min_nm,
        }
    finally:
        db.close()


@router.post("/images/{user_id}/{image_id}/reanalyze")
async def reanalyze_image(
    user_id: str,
    image_id: str,
    method: str = Query("cnn", pattern="^(rulebased|voronoi|ai|cnn)$"),
):
    db = db_session()
    try:
        rec = (
            db.query(ImageRecord)
            .filter(ImageRecord.user_id == user_id, ImageRecord.image_id == image_id)
            .first()
        )
        if not rec:
            raise HTTPException(status_code=404, detail="Image not found")

        img_path = get_original_image_path(rec)
        if not img_path or not os.path.exists(img_path):
            raise HTTPException(status_code=404, detail="Image file not found")

        npp = get_nm_per_pixel_for_record(rec)
        boxes = await run_analysis(method, img_path, npp)

        rec.boxes = boxes
        rec.analysis_method = method
        rec.display_image_url = rec.original_image_url or rec.image_url
        db.commit()

        min_nm = get_min_nm_value(rec.min_nm)

        return {
            "status": "success",
            "analysis_method": method,
            "boxes": apply_min_nm_filter(boxes, min_nm, fallback_nm_per_pixel=npp),
            "scale": rec.scale,
            "min_nm": min_nm,
            "image_url": get_display_url(rec),
        }
    finally:
        db.close()


@router.delete("/images/{user_id}/{image_id}")
def delete_image(user_id: str, image_id: str):
    db = db_session()
    try:
        rec = (
            db.query(ImageRecord)
            .filter(ImageRecord.user_id == user_id, ImageRecord.image_id == image_id)
            .first()
        )
        if not rec:
            return {"error": "Image not found"}

        paths_to_delete = set()
        for url in [rec.image_url, rec.original_image_url, rec.display_image_url]:
            p = image_path_from_url(url) if url else None
            if p:
                paths_to_delete.add(p)

        for file_path in paths_to_delete:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"[WARN] Could not delete file {file_path}: {e}")

        db.delete(rec)
        db.commit()

        return {"status": "image deleted"}
    finally:
        db.close()


@router.delete("/clear-all-images")
def clear_all_images():
    if os.path.exists(UPLOAD_DIR):
        for file in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, file)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass

    db = db_session()
    try:
        db.query(ImageRecord).delete()
        db.commit()
        return {"status": "all images deleted"}
    finally:
        db.close()


@router.get("/images/{image_id}/table/intact")
def get_intact_table(image_id: str, size: Optional[str] = None):
    found = find_image_by_id_db(image_id)
    if not found:
        return {"error": "Image not found"}
    _, _, rec = found
    min_nm = get_min_nm_value(rec.min_nm)
    return build_table_response(rec.boxes or [], "intact", size, min_nm=min_nm)


@router.get("/images/{image_id}/table/not_intact")
def get_not_intact_table(image_id: str, size: Optional[str] = None):
    found = find_image_by_id_db(image_id)
    if not found:
        return {"error": "Image not found"}
    _, _, rec = found
    min_nm = get_min_nm_value(rec.min_nm)
    return build_table_response(rec.boxes or [], "not_intact", size, min_nm=min_nm)


@router.get("/images/{image_id}/table/needs_review")
def get_needs_review_table(image_id: str, size: Optional[str] = None):
    found = find_image_by_id_db(image_id)
    if not found:
        return {"error": "Image not found"}
    _, _, rec = found
    min_nm = get_min_nm_value(rec.min_nm)
    return build_table_response(rec.boxes or [], "needs_review", size, min_nm=min_nm)


@router.post("/line-intensity")
def line_intensity(data: LineIntensityRequest):
    found = find_image_by_id_db(data.image_id)
    if not found:
        raise HTTPException(status_code=404, detail="Image not found in records")

    _, _, rec = found
    img_path = get_original_image_path(rec)

    if not img_path or not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail="Image file missing on disk")

    image = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise HTTPException(status_code=400, detail="Failed to read image")

    h, w = image.shape[:2]

    n = int(data.samples)
    xs = np.linspace(float(data.x1), float(data.x2), n + 1)
    ys = np.linspace(float(data.y1), float(data.y2), n + 1)

    xi = np.clip(np.rint(xs).astype(int), 0, w - 1)
    yi = np.clip(np.rint(ys).astype(int), 0, h - 1)

    vals = image[yi, xi].astype(int)

    return {
        "image_id": data.image_id,
        "samples": n,
        "num_points": int(vals.size),
        "max_intensity": int(vals.max()) if vals.size else None,
        "min_intensity": int(vals.min()) if vals.size else None,
        "average_intensity": float(vals.mean()) if vals.size else None,
        "intensities": vals.tolist(),
        "points": [
            {"step": i, "x": int(xi[i]), "y": int(yi[i]), "intensity": int(vals[i])}
            for i in range(vals.size)
        ],
    }


@router.post("/shape-classify")
async def shape_classify(
    file: UploadFile = File(...),
    client_instructions: str = Form(""),
    use_ai_rules: bool = Form(False),
    min_area: int = Form(300),
    close_kernel: int = Form(5),
    close_iterations: int = Form(2),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image type")

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    if not validate_image(content):
        raise HTTPException(status_code=400, detail="Invalid image file")

    img_bgr = decode_upload_to_bgr(content)
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Failed to decode image")

    shape_result = run_shape_pipeline_on_bgr(
        img_bgr=img_bgr,
        client_instructions=client_instructions,
        use_ai_rules=use_ai_rules,
        feedbacks=[],
        min_area=min_area,
        close_kernel=close_kernel,
        close_iterations=close_iterations,
    )

    result_image_url, clean_mask_url = save_shape_outputs(
        shape_result["overlay"],
        shape_result["clean_mask"],
        suffix_prefix="shape_classified",
    )

    boxes = shape_particles_to_boxes(
        shape_result["particles"],
        nm_per_pixel=DEFAULT_NM_PER_PIXEL,
        image_path=None,
    )

    return {
        "status": "success",
        "rules": shape_result["rules"],
        "result_image_url": result_image_url,
        "clean_mask_url": clean_mask_url,
        "counts": shape_result["counts"],
        "particles": shape_result["particles"],
        "boxes": boxes,
    }


@router.post("/shape-classify-with-feedback")
async def shape_classify_with_feedback(
    file: UploadFile = File(...),
    payload: str = Form("{}"),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image type")

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    if not validate_image(content):
        raise HTTPException(status_code=400, detail="Invalid image file")

    try:
        payload_dict = json.loads(payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload JSON")

    img_bgr = decode_upload_to_bgr(content)
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Failed to decode image")

    shape_result = run_shape_pipeline_on_bgr(
        img_bgr=img_bgr,
        client_instructions=payload_dict.get("client_instructions", ""),
        use_ai_rules=bool(payload_dict.get("use_ai_rules", False)),
        feedbacks=payload_dict.get("feedbacks", []),
        min_area=safe_int(payload_dict.get("min_area", 300), 300),
        close_kernel=safe_int(payload_dict.get("close_kernel", 5), 5),
        close_iterations=safe_int(payload_dict.get("close_iterations", 2), 2),
    )

    result_image_url, clean_mask_url = save_shape_outputs(
        shape_result["overlay"],
        shape_result["clean_mask"],
        suffix_prefix="shape_feedback",
    )

    boxes = shape_particles_to_boxes(
        shape_result["particles"],
        nm_per_pixel=DEFAULT_NM_PER_PIXEL,
        image_path=None,
    )

    return {
        "status": "success",
        "rules": shape_result["rules"],
        "result_image_url": result_image_url,
        "clean_mask_url": clean_mask_url,
        "counts": shape_result["counts"],
        "particles": shape_result["particles"],
        "boxes": boxes,
    }


@router.post("/images/{user_id}/{image_id}/shape-classify")
def shape_classify_existing(
    user_id: str,
    image_id: str,
    client_instructions: str = Query(""),
    use_ai_rules: bool = Query(False),
    min_area: int = Query(300),
    close_kernel: int = Query(5),
    close_iterations: int = Query(2),
):
    db = db_session()
    try:
        rec = (
            db.query(ImageRecord)
            .filter(ImageRecord.user_id == user_id, ImageRecord.image_id == image_id)
            .first()
        )
        if not rec:
            raise HTTPException(status_code=404, detail="Image not found")

        original_path = get_original_image_path(rec)
        if not original_path or not os.path.exists(original_path):
            raise HTTPException(status_code=404, detail="Original image file not found")

        img_bgr = cv2.imread(original_path, cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise HTTPException(status_code=400, detail="Failed to read image")

        shape_result = run_shape_pipeline_on_bgr(
            img_bgr=img_bgr,
            client_instructions=client_instructions,
            use_ai_rules=use_ai_rules,
            feedbacks=[],
            min_area=min_area,
            close_kernel=close_kernel,
            close_iterations=close_iterations,
        )

        result_image_url, clean_mask_url = save_shape_outputs(
            shape_result["overlay"],
            shape_result["clean_mask"],
            suffix_prefix="shape_classified_existing",
        )

        npp = get_nm_per_pixel_for_record(rec)
        boxes = shape_particles_to_boxes(
            shape_result["particles"],
            nm_per_pixel=npp,
            image_path=original_path,
        )

        rec.display_image_url = result_image_url
        rec.boxes = boxes
        rec.analysis_method = "shape"
        db.commit()

        return {
            "status": "success",
            "rules": shape_result["rules"],
            "result_image_url": result_image_url,
            "clean_mask_url": clean_mask_url,
            "counts": shape_result["counts"],
            "particles": shape_result["particles"],
            "boxes": apply_min_nm_filter(
                boxes,
                get_min_nm_value(rec.min_nm),
                fallback_nm_per_pixel=npp,
            ),
        }
    finally:
        db.close()


@router.post("/images/{user_id}/{image_id}/shape-classify-with-feedback")
def shape_classify_existing_with_feedback(
    user_id: str,
    image_id: str,
    payload: ShapeFeedbackRequest,
):
    db = db_session()
    try:
        rec = (
            db.query(ImageRecord)
            .filter(ImageRecord.user_id == user_id, ImageRecord.image_id == image_id)
            .first()
        )
        if not rec:
            raise HTTPException(status_code=404, detail="Image not found")

        original_path = get_original_image_path(rec)
        if not original_path or not os.path.exists(original_path):
            raise HTTPException(status_code=404, detail="Original image file not found")

        img_bgr = cv2.imread(original_path, cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise HTTPException(status_code=400, detail="Failed to read image")

        feedbacks = [f.model_dump() for f in payload.feedbacks]

        shape_result = run_shape_pipeline_on_bgr(
            img_bgr=img_bgr,
            client_instructions=payload.client_instructions or "",
            use_ai_rules=payload.use_ai_rules,
            feedbacks=feedbacks,
            min_area=payload.min_area,
            close_kernel=payload.close_kernel,
            close_iterations=payload.close_iterations,
        )

        result_image_url, clean_mask_url = save_shape_outputs(
            shape_result["overlay"],
            shape_result["clean_mask"],
            suffix_prefix="shape_feedback_existing",
        )

        npp = get_nm_per_pixel_for_record(rec)
        boxes = shape_particles_to_boxes(
            shape_result["particles"],
            nm_per_pixel=npp,
            image_path=original_path,
        )

        rec.display_image_url = result_image_url
        rec.boxes = boxes
        rec.analysis_method = "shape"
        db.commit()

        return {
            "status": "success",
            "rules": shape_result["rules"],
            "result_image_url": result_image_url,
            "clean_mask_url": clean_mask_url,
            "counts": shape_result["counts"],
            "particles": shape_result["particles"],
            "boxes": apply_min_nm_filter(
                boxes,
                get_min_nm_value(rec.min_nm),
                fallback_nm_per_pixel=npp,
            ),
        }
    finally:
        db.close()


@router.post("/shape-find-nearest")
def shape_find_nearest(
    particles: List[dict],
    x: float = Query(...),
    y: float = Query(...),
):
    found = find_nearest_particle(x, y, particles)
    if not found:
        return {"status": "not_found"}
    return {"status": "success", "particle": found}