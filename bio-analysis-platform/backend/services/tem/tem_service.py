from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Optional, Tuple, Any

from .tem_analyzer import analyze_image as analyze_image_rulebased
from .tem_analyzer_voronoi import analyze_image_voronoi
from .tem_analyzer_ai import analyze_image_ai_async
from .tem_analyzer_cnn import analyze_image_cnn

from .shape_classifier import (
    get_shape_classification_rules,
    run_shape_classification_pipeline,
    find_nearest_particle,
    parse_feedback_text,
)

import os
import sys
import uuid
import cv2
import math
import numpy as np

from dotenv import load_dotenv
from urllib.parse import quote_plus
from sqlalchemy import create_engine, Column, String, Text, Float, JSON, text
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path
import logging
from PIL import Image
from io import BytesIO

print("TEM service loaded")

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parents[1]

# In frozen (production) mode Electron sets cwd to app.getPath('userData') — a writable location.
# In dev mode cwd is the backend/ folder, so BACKEND_DIR and cwd agree.
if getattr(sys, 'frozen', False):
    _data_root = Path(os.getcwd())
else:
    _data_root = BACKEND_DIR

# Load .env from the data root (backend/ in dev, userData in production)
load_dotenv(_data_root / ".env")

UPLOAD_DIR = str(_data_root / "uploads" / "tem")
DEFAULT_MIN_NM = 30.0
DEFAULT_NM_PER_PIXEL = 0.5

os.makedirs(UPLOAD_DIR, exist_ok=True)

logger = logging.getLogger(__name__)


def resolve_model_path() -> str:
    """
    Resolve TensorFlow CNN model path with fallback strategy and logging.

    Priority:
      1. MODEL_PATH env var (absolute or relative)
      2. CNN_MODEL_PATH env var (legacy, absolute or relative)
      3. ./models/ev_viability_best_model.h5 (default relative to cwd)

    Returns:
        Absolute path string to model file.

    Raises:
        FileNotFoundError: If model file does not exist at resolved path.
    """
    model_path_env = os.getenv("MODEL_PATH", "")
    cnn_model_path_env = os.getenv("CNN_MODEL_PATH", "")

    if model_path_env:
        model_path = Path(model_path_env).resolve()
        logger.info(f"Using MODEL_PATH env var: {model_path}")
    elif cnn_model_path_env:
        model_path = Path(cnn_model_path_env).resolve()
        logger.info(f"Using CNN_MODEL_PATH env var: {model_path}")
    else:
        default_path = _data_root / "models" / "ev_viability_best_model.h5"
        model_path = default_path.resolve()
        logger.info(f"Using default model path: {model_path}")

    if not model_path.exists():
        error_msg = (
            f"CNN model not found at: {model_path}\n"
            f"Please ensure the TensorFlow model file exists and is readable.\n"
            f"To configure a custom path, set MODEL_PATH or CNN_MODEL_PATH env var."
        )
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    logger.debug(f"✓ Model path resolved and validated: {model_path}")
    return str(model_path)


# Resolve model path at startup; defer failure to first CNN request if missing.
try:
    CNN_MODEL_PATH = resolve_model_path()
except FileNotFoundError:
    logger.warning("CNN model initialization deferred — will fail on first CNN analysis request")
    CNN_MODEL_PATH = None

_pg_host = os.getenv("PGHOST", "localhost")
_pg_port = os.getenv("PGPORT", "5432")
_pg_db   = os.getenv("PGDATABASE", "biolab")
_pg_user = os.getenv("PGUSER", "postgres")
_pg_pass = os.getenv("PGPASSWORD", "postgres")

DATABASE_URL = f"postgresql://{_pg_user}:{quote_plus(_pg_pass)}@{_pg_host}:{_pg_port}/{_pg_db}"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ImageRecord(Base):
    __tablename__ = "images"

    user_id = Column(String, primary_key=True, index=True)
    image_id = Column(String, primary_key=True, index=True)

    image_url = Column(Text, nullable=False)
    original_image_url = Column(Text, nullable=True)
    display_image_url = Column(Text, nullable=True)

    scale = Column(JSON, nullable=True)
    min_nm = Column(Float, nullable=False, default=DEFAULT_MIN_NM)
    boxes = Column(JSON, nullable=False, default=list)
    analysis_method = Column(String, nullable=False, default="rulebased")


Base.metadata.create_all(bind=engine)


def ensure_extra_columns():
    stmts = [
        "ALTER TABLE images ADD COLUMN IF NOT EXISTS original_image_url TEXT",
        "ALTER TABLE images ADD COLUMN IF NOT EXISTS display_image_url TEXT",
    ]
    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))


ensure_extra_columns()


def db_session():
    return SessionLocal()


class CircleIn(BaseModel):
    number: Optional[int] = None
    x: float
    y: float
    r: float
    diameter_nm: Optional[float] = None
    viability: str = "needs_review"
    intensity: Optional[Dict] = None
    shape: Optional[Dict] = None
    confidence: Optional[float] = None
    votes: Optional[Dict] = None
    vote_summary: Optional[str] = None
    membrane_intact: Optional[bool] = None

    model_config = ConfigDict(extra="ignore")


class ScaleInput(BaseModel):
    scale_pixels: float
    scale_real_value: float
    scale_real_unit: str

    model_config = ConfigDict(extra="ignore")


class MinNmInput(BaseModel):
    min_nm: float

    model_config = ConfigDict(extra="ignore")


class HideFilterInput(BaseModel):
    hide_below_nm: float

    model_config = ConfigDict(extra="ignore")


class DeleteCirclesInput(BaseModel):
    numbers: List[int] = []

    model_config = ConfigDict(extra="ignore")


class LineIntensityRequest(BaseModel):
    image_id: str
    x1: float
    y1: float
    x2: float
    y2: float
    samples: int = Field(default=20, ge=1, le=2000)


class FeedbackItem(BaseModel):
    matched_idx: int
    action: str
    label: Optional[str] = None


class ShapeFeedbackRequest(BaseModel):
    client_instructions: Optional[str] = ""
    feedbacks: List[FeedbackItem] = []
    use_ai_rules: bool = False
    min_area: int = 300
    close_kernel: int = 5
    close_iterations: int = 2


ALLOWED_TYPES = {
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/tif",
    "application/octet-stream",
}

MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_FILES = 5


def validate_image(content):
    try:
        img = Image.open(BytesIO(content))
        img.verify()
        return True
    except Exception:
        return False


def get_display_url(rec: ImageRecord) -> str:
    return rec.display_image_url or rec.image_url


def get_original_url(rec: ImageRecord) -> str:
    return rec.original_image_url or rec.image_url


def image_path_from_url(image_url: str) -> Optional[str]:
    if not image_url:
        return None

    image_url = image_url.replace("\\", "/")

    if image_url.startswith("/uploads/tem/"):
        relative = image_url.replace("/uploads/tem/", "", 1)
        return os.path.join(UPLOAD_DIR, relative)

    if image_url.startswith("/uploads/"):
        relative = image_url.replace("/uploads/", "", 1)
        uploads_root = str(BACKEND_DIR / "uploads")
        return os.path.join(uploads_root, relative)

    return image_url


def get_display_image_path(rec: ImageRecord) -> Optional[str]:
    return image_path_from_url(get_display_url(rec))


def get_original_image_path(rec: ImageRecord) -> Optional[str]:
    return image_path_from_url(get_original_url(rec))


def find_image_by_id_db(image_id: str) -> Optional[Tuple[str, str, ImageRecord]]:
    db = db_session()
    try:
        rec = db.query(ImageRecord).filter(ImageRecord.image_id == image_id).first()
        if not rec:
            return None
        return rec.user_id, rec.image_id, rec
    finally:
        db.close()


def normalize_viability(value: Optional[str]) -> str:
    v = str(value or "").strip().lower()
    mapping = {
        "viable": "intact",
        "non_viable": "not_intact",
        "intact": "intact",
        "not_intact": "not_intact",
        "needs_review": "needs_review",
        "green": "intact",
        "red": "not_intact",
        "skip": "needs_review",
        "skipped": "needs_review",
    }
    return mapping.get(v, "needs_review")


def nm_per_pixel_from_scale(scale: Optional[dict]) -> Optional[float]:
    if not scale:
        return None

    try:
        sp = float(scale.get("scale_pixels", 0))
        rv = float(scale.get("scale_real_value", 0))
        unit = str(scale.get("scale_real_unit", "")).lower()
        unit = "um" if unit in ["µm", "micron", "microns"] else unit

        if sp <= 0 or rv <= 0:
            return None

        if unit == "um":
            return (rv * 1000.0) / sp
        if unit == "nm":
            return rv / sp

        return None
    except Exception:
        return None


def get_nm_per_pixel_for_record(rec: Optional[ImageRecord]) -> float:
    if rec:
        npp = nm_per_pixel_from_scale(rec.scale)
        if npp is not None and npp > 0:
            return npp
    return DEFAULT_NM_PER_PIXEL


def get_min_nm_value(min_nm: Optional[float]) -> float:
    try:
        v = float(min_nm if min_nm is not None else DEFAULT_MIN_NM)
        return v if v > 0 else DEFAULT_MIN_NM
    except Exception:
        return DEFAULT_MIN_NM


def calculate_diameter_nm_from_px(r_px: Optional[float], nm_per_pixel: Optional[float]) -> Optional[float]:
    try:
        if r_px is None or nm_per_pixel is None:
            return None
        return round(float(r_px) * 2.0 * float(nm_per_pixel), 2)
    except Exception:
        return None


def get_effective_diameter_nm(box: dict, fallback_nm_per_pixel: float = DEFAULT_NM_PER_PIXEL) -> Optional[float]:
    d = box.get("diameter_nm")
    if d is not None:
        try:
            return float(d)
        except Exception:
            pass

    r = box.get("r")
    if r is not None:
        try:
            return round(float(r) * 2.0 * fallback_nm_per_pixel, 2)
        except Exception:
            pass

    diameter_px = box.get("diameter_px")
    if diameter_px is not None:
        try:
            return round(float(diameter_px) * fallback_nm_per_pixel, 2)
        except Exception:
            pass

    return None


def apply_min_nm_filter(boxes: List[dict], min_nm: float, fallback_nm_per_pixel: float = DEFAULT_NM_PER_PIXEL) -> List[dict]:
    out = []
    for c in (boxes or []):
        d = get_effective_diameter_nm(c, fallback_nm_per_pixel=fallback_nm_per_pixel)
        if d is None:
            out.append(c)
            continue
        try:
            if float(d) >= float(min_nm):
                cc = dict(c)
                if cc.get("diameter_nm") is None:
                    cc["diameter_nm"] = d
                out.append(cc)
        except Exception:
            out.append(c)
    return out


def compute_radial_intensity(img, x, y, r, samples=10):
    h, w = img.shape
    cx, cy, r = int(x), int(y), int(r)

    values = []
    for i in range(samples + 1):
        rr = int((i / samples) * r)
        px = min(max(cx + rr, 0), w - 1)
        py = min(max(cy, 0), h - 1)
        values.append(int(img[py, px]))

    return {
        "center_intensity": values[0] if values else None,
        "edge_intensity": values[-1] if values else None,
        "mean_intensity": round(float(np.mean(values)), 2) if values else None,
        "radial_intensity": values,
    }


def normalize_particle_box(p: dict, idx: int, nm_per_pixel: Optional[float], img_gray=None) -> dict:
    center = p.get("center")
    x = p.get("x")
    y = p.get("y")

    if (x is None or y is None) and isinstance(center, (list, tuple)) and len(center) >= 2:
        x, y = center[0], center[1]

    diameter_px = p.get("diameter_px")
    r = p.get("r")
    if r is None and diameter_px is not None:
        try:
            r = float(diameter_px) / 2.0
        except Exception:
            r = None

    box = {
        "number": idx,
        "x": round(float(x), 2) if x is not None else 0.0,
        "y": round(float(y), 2) if y is not None else 0.0,
        "r": round(float(r), 2) if r is not None else 0.0,
        "diameter_nm": p.get("diameter_nm"),
        "viability": normalize_viability(p.get("viability") or p.get("classification")),
        "confidence": p.get("confidence"),
        "votes": p.get("votes"),
        "vote_summary": p.get("vote_summary"),
        "shape": {
            "aspect_ratio": p.get("aspect_ratio"),
            "eccentricity": p.get("eccentricity"),
            "solidity": p.get("solidity"),
        },
        "membrane_intact": p.get("membrane_intact"),
        "intensity": p.get("intensity"),
    }

    if box["diameter_nm"] is None:
        box["diameter_nm"] = calculate_diameter_nm_from_px(box["r"], nm_per_pixel)

    if img_gray is not None and box["intensity"] is None and box["r"] and box["x"] is not None and box["y"] is not None:
        box["intensity"] = compute_radial_intensity(img_gray, box["x"], box["y"], box["r"])

    return box


def normalize_boxes(raw_result, nm_per_pixel: Optional[float], img_path: Optional[str] = None) -> List[dict]:
    img_gray = None
    if img_path and os.path.exists(img_path):
        img_gray = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

    if isinstance(raw_result, list):
        normalized = []
        for idx, item in enumerate(raw_result, start=1):
            item = dict(item)
            item["viability"] = normalize_viability(item.get("viability"))
            if item.get("number") is None:
                item["number"] = idx
            if item.get("diameter_nm") is None and item.get("r") is not None:
                item["diameter_nm"] = calculate_diameter_nm_from_px(item.get("r"), nm_per_pixel)
            if img_gray is not None and item.get("intensity") is None and item.get("r") is not None:
                item["intensity"] = compute_radial_intensity(
                    img_gray,
                    item.get("x", 0),
                    item.get("y", 0),
                    item.get("r", 0),
                )
            normalized.append(item)
        return normalized

    if isinstance(raw_result, dict):
        particles = raw_result.get("particles", [])
        return [
            normalize_particle_box(p, idx, nm_per_pixel, img_gray=img_gray)
            for idx, p in enumerate(particles, start=1)
        ]

    return []


def analyze_rulebased_path(image_path: str, nm_per_pixel: Optional[float]) -> List[dict]:
    img = cv2.imread(image_path)
    if img is None:
        raise HTTPException(status_code=400, detail="Failed to read uploaded image")
    result = analyze_image_rulebased(img)
    return normalize_boxes(result, nm_per_pixel=nm_per_pixel, img_path=image_path)


def analyze_cnn_path(image_path: str, nm_per_pixel: Optional[float]) -> List[dict]:
    if not CNN_MODEL_PATH:
        logger.warning(
            "CNN model path not configured. "
            "Set MODEL_PATH or CNN_MODEL_PATH environment variable. "
            "Falling back to rule-based analysis."
        )
        return analyze_rulebased_path(image_path, nm_per_pixel)

    if not os.path.exists(CNN_MODEL_PATH):
        logger.warning("CNN model file does not exist at: %s. Falling back to rule-based analysis.", CNN_MODEL_PATH)
        return analyze_rulebased_path(image_path, nm_per_pixel)

    result = analyze_image_cnn(
        image_path,
        nm_per_pixel=nm_per_pixel or DEFAULT_NM_PER_PIXEL,
        model_path=CNN_MODEL_PATH,
    )
    return normalize_boxes(result, nm_per_pixel=nm_per_pixel, img_path=image_path)


async def run_analysis(method: str, image_path: str, nm_per_pixel: Optional[float]) -> List[dict]:
    if method == "voronoi":
        result = analyze_image_voronoi(image_path, nm_per_pixel=nm_per_pixel or DEFAULT_NM_PER_PIXEL)
        return normalize_boxes(result, nm_per_pixel=nm_per_pixel, img_path=image_path)

    if method == "ai":
        result = await analyze_image_ai_async(image_path, nm_per_pixel=nm_per_pixel or DEFAULT_NM_PER_PIXEL)
        return normalize_boxes(result, nm_per_pixel=nm_per_pixel, img_path=image_path)

    if method == "cnn":
        return analyze_cnn_path(image_path, nm_per_pixel)

    return analyze_rulebased_path(image_path, nm_per_pixel)


def ensure_odd_kernel(value: int) -> int:
    try:
        v = int(value)
    except Exception:
        v = 5

    if v < 1:
        v = 1
    if v % 2 == 0:
        v += 1
    return v


def safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def decode_upload_to_bgr(file_content: bytes):
    np_arr = np.frombuffer(file_content, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return img_bgr


def save_shape_outputs(overlay, clean_mask, suffix_prefix: str = "shape"):
    """
    Saves shape output images into uploads/tem and returns public URLs.
    """
    result_id = str(uuid.uuid4())

    out_name = f"{result_id}_{suffix_prefix}.jpg"
    mask_name = f"{result_id}_{suffix_prefix}_mask.jpg"

    out_path = os.path.join(UPLOAD_DIR, out_name)
    mask_path = os.path.join(UPLOAD_DIR, mask_name)

    ok1 = cv2.imwrite(out_path, overlay)
    ok2 = cv2.imwrite(mask_path, clean_mask)

    if not ok1:
        raise HTTPException(status_code=500, detail=f"Failed to save overlay image: {out_path}")
    if not ok2:
        raise HTTPException(status_code=500, detail=f"Failed to save mask image: {mask_path}")

    return f"/uploads/tem/{out_name}", f"/uploads/tem/{mask_name}"


def particle_get_xy(p: dict):
    x = p.get("x")
    y = p.get("y")

    if x is None and p.get("cx") is not None:
        x = p.get("cx")
    if y is None and p.get("cy") is not None:
        y = p.get("cy")

    if (x is None or y is None) and isinstance(p.get("center"), (list, tuple)) and len(p["center"]) >= 2:
        x, y = p["center"][0], p["center"][1]

    if (x is None or y is None) and isinstance(p.get("centroid"), (list, tuple)) and len(p["centroid"]) >= 2:
        x, y = p["centroid"][0], p["centroid"][1]

    if x is None:
        x = p.get("center_x", p.get("centroid_x", 0))
    if y is None:
        y = p.get("center_y", p.get("centroid_y", 0))

    return float(x or 0), float(y or 0)


def particle_get_radius(p: dict):
    if p.get("r") is not None:
        return float(p["r"])

    if p.get("radius") is not None:
        return float(p["radius"])

    if p.get("diameter_px") is not None:
        return float(p["diameter_px"]) / 2.0

    if p.get("equivalent_diameter_px") is not None:
        return float(p["equivalent_diameter_px"]) / 2.0

    bbox = p.get("bbox")
    if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
        bw = float(bbox[2])
        bh = float(bbox[3])
        return max(1.0, min(bw, bh) / 2.0)

    width = p.get("width", p.get("w"))
    height = p.get("height", p.get("h"))
    if width is not None and height is not None:
        return max(1.0, min(float(width), float(height)) / 2.0)

    area = p.get("area")
    if area is not None:
        try:
            return max(1.0, math.sqrt(float(area) / math.pi))
        except Exception:
            pass

    return 10.0


def particle_color_to_viability(color_name: Optional[str]) -> str:
    color_name = str(color_name or "").strip().lower()
    if color_name == "green":
        return "intact"
    if color_name == "red":
        return "not_intact"
    return "needs_review"


def shape_particles_to_boxes(
    particles: List[dict],
    nm_per_pixel: float,
    image_path: Optional[str] = None,
) -> List[dict]:
    img_gray = None
    if image_path and os.path.exists(image_path):
        img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    boxes = []
    for idx, p in enumerate(particles or [], start=1):
        x, y = particle_get_xy(p)
        r = particle_get_radius(p)
        diameter_nm = calculate_diameter_nm_from_px(r, nm_per_pixel)

        box = {
            "number": idx,
            "x": round(float(x), 2),
            "y": round(float(y), 2),
            "r": round(float(r), 2),
            "diameter_nm": diameter_nm,
            "viability": particle_color_to_viability(p.get("color_name")),
            "confidence": p.get("confidence"),
            "votes": None,
            "vote_summary": p.get("label"),
            "shape": {
                "circularity": p.get("circularity"),
                "solidity": p.get("solidity"),
                "convexity": p.get("convexity"),
            },
            "membrane_intact": True if p.get("color_name") == "green" else False if p.get("color_name") == "red" else None,
            "intensity": None,
            "shape_meta": p,
        }

        if img_gray is not None:
            box["intensity"] = compute_radial_intensity(img_gray, x, y, r)

        boxes.append(box)

    return boxes


def run_shape_pipeline_on_bgr(
    img_bgr,
    client_instructions: str = "",
    use_ai_rules: bool = False,
    feedbacks: Optional[List[dict]] = None,
    min_area: int = 300,
    close_kernel: int = 5,
    close_iterations: int = 2,
    nm_per_pixel: float = DEFAULT_NM_PER_PIXEL,
    min_diameter_nm: float = DEFAULT_MIN_NM,
):
    rules = get_shape_classification_rules(client_instructions, use_ai_rules)

    overlay, clean_mask, particles = run_shape_classification_pipeline(
        img_bgr=img_bgr,
        rules=rules,
        feedbacks=feedbacks or [],
        min_area=safe_int(min_area, 300),
        close_kernel=ensure_odd_kernel(close_kernel),
        close_iterations=max(1, safe_int(close_iterations, 2)),
        nm_per_pixel=nm_per_pixel,
        min_diameter_nm=min_diameter_nm,
    )

    green_count = sum(1 for p in particles if p.get("color_name") == "green")
    red_count = sum(1 for p in particles if p.get("color_name") == "red")
    skipped_count = sum(1 for p in particles if p.get("color_name") == "skipped")

    return {
        "rules": rules,
        "overlay": overlay,
        "clean_mask": clean_mask,
        "particles": particles,
        "counts": {
            "total": len(particles),
            "green": green_count,
            "red": red_count,
            "skipped": skipped_count,
        },
    }


def get_size_bin(d):
    if d is None:
        return None
    if d < 30:
        return "below_30"
    if 30 <= d < 50:
        return "30_50"
    if 50 <= d < 100:
        return "50_100"
    if 100 <= d < 200:
        return "100_200"
    return "200_plus"


def build_table_response(boxes, status_filter=None, size_filter=None, min_nm: float = DEFAULT_MIN_NM):
    filtered = []

    for c in boxes or []:
        d = get_effective_diameter_nm(c, fallback_nm_per_pixel=DEFAULT_NM_PER_PIXEL)
        if d is None:
            continue

        try:
            if float(d) < float(min_nm):
                continue
        except Exception:
            continue

        if status_filter and c.get("viability") != status_filter:
            continue

        size_bin = get_size_bin(d)
        if size_filter and size_bin != size_filter:
            continue

        filtered.append(
            {
                "number": c.get("number"),
                "diameter_nm": d,
                "viability": c.get("viability"),
                "confidence": c.get("confidence"),
            }
        )

    filtered = sorted(filtered, key=lambda x: (x["number"] is None, x["number"]))
    return {"total": len(filtered), "circles": filtered}