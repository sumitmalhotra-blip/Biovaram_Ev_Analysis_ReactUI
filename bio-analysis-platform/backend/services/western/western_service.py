"""
western_service.py  –  BioVaram Western / Agarose Gel Analysis
---------------------------------------------------------------
Drop-in replacement for the original rule-based service.

Key improvements over v1
────────────────────────
1. Adaptive preprocessing  – blur kernel and CLAHE scale with image resolution
2. Adaptive lane detection – distance/prominence thresholds scale with image width
   → fixes the "ladder lane missed" and "merged lanes" bugs
3. Adaptive band detection – prominence and distance scale per-lane
   → catches faint bands that were invisible to the fixed 8% threshold
4. Confidence scoring      – every band gets a 0-1 confidence score so the
   frontend can highlight uncertain detections
5. AWS Bedrock / Nova      – optional AI re-check pass that validates bands and
   suggests any the CV pipeline missed (falls back gracefully if Bedrock is
   unavailable)
6. Agarose gel support     – auto-detects EtBr (bright-on-dark) vs stained
   (dark-on-light) and adjusts inversion accordingly
7. All original function signatures are preserved – the router needs zero changes
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import shutil
import sys
import traceback
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from fastapi.responses import JSONResponse
from scipy.signal import find_peaks

# ── optional Bedrock ──────────────────────────────────────────────────────────
try:
    import boto3
    _BOTO3_AVAILABLE = True
except ImportError:
    _BOTO3_AVAILABLE = False

logger = logging.getLogger(__name__)

# ── paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parents[1]

if getattr(sys, "frozen", False):
    _data_root = Path(os.getcwd())
else:
    _data_root = BACKEND_DIR

UPLOAD_FOLDER = str(_data_root / "uploads" / "western")
RESULT_FOLDER  = str(_data_root / "results"  / "western")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER,  exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def safe_filename(filename: str) -> str:
    return filename.replace(" ", "_")


def _is_dark_background(gray: np.ndarray) -> bool:
    """Return True if the image has a dark background (EtBr / fluorescence)."""
    return float(np.median(gray)) < 100


def _adaptive_blur_kernel(width: int) -> int:
    """Return an odd kernel size that scales with image width."""
    k = max(3, int(width * 0.004))
    return k if k % 2 == 1 else k + 1


def _clahe_enhance(gray: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    return clahe.apply(gray)


# ─────────────────────────────────────────────────────────────────────────────
# Preprocessing  (public – same signature as before)
# ─────────────────────────────────────────────────────────────────────────────

def preprocess_image(file_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Returns (original_gray, processed_img).

    processed_img is the image ready for peak-finding:
    - normalised to 0-255
    - inverted so bands are bright (works for both stain types)
    - CLAHE-enhanced
    - Gaussian-blurred with adaptive kernel
    """
    # ── read ──────────────────────────────────────────────────────────────────
    img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        # Try tifffile for multi-page / 16-bit TIFs
        try:
            import tifffile
            raw = tifffile.imread(file_path)
            if raw.ndim == 3:
                img = cv2.cvtColor(raw, cv2.COLOR_RGB2BGR)
            else:
                img = raw
        except Exception:
            raise ValueError(f"Could not read image at path: {file_path}")

    # ── to grayscale ──────────────────────────────────────────────────────────
    if img.ndim == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    # ── normalise to uint8 ────────────────────────────────────────────────────
    gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    # ── invert so bands are always bright ────────────────────────────────────
    dark_bg = _is_dark_background(gray)
    inv = gray if dark_bg else (255 - gray)

    # ── CLAHE to pull up faint bands (stronger for very dark images) ─────────
    median_val = float(np.median(gray))
    clip = 8.0 if median_val < 10 else (4.0 if median_val < 50 else 2.5)
    tile = (4, 4) if median_val < 10 else (8, 8)
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=tile)
    enhanced = clahe.apply(inv)

    # ── adaptive Gaussian blur ────────────────────────────────────────────────
    k = _adaptive_blur_kernel(gray.shape[1])
    blur = cv2.GaussianBlur(enhanced, (k, k), 0)

    return gray, blur


# ─────────────────────────────────────────────────────────────────────────────
# Lane detection  (public – same signature as before)
# ─────────────────────────────────────────────────────────────────────────────

def detect_lanes(processed_img: np.ndarray) -> np.ndarray:
    """
    Detect lane centre X-positions using progressive threshold relaxation.
    Works universally across protein gels, agarose gels, high/low contrast images.
    """
    h, w = processed_img.shape
    vertical_profile = np.sum(processed_img, axis=0).astype(float)
    min_distance = max(20, int(w * 0.018))
    profile_max = float(np.max(vertical_profile))

    # Try progressively lower prominence thresholds until we get lanes
    for prom_pct in [0.08, 0.04, 0.02, 0.01]:
        lane_peaks, _ = find_peaks(
            vertical_profile,
            distance=min_distance,
            prominence=max(profile_max * prom_pct, 50),
        )
        if len(lane_peaks) >= 2:
            break

    # Also try tighter distance if still not enough
    if len(lane_peaks) < 2:
        for dist_factor in [0.012, 0.008]:
            lane_peaks, _ = find_peaks(
                vertical_profile,
                distance=max(15, int(w * dist_factor)),
                prominence=max(profile_max * 0.01, 30),
            )
            if len(lane_peaks) >= 2:
                break

    return lane_peaks


# ─────────────────────────────────────────────────────────────────────────────
# Band detection  (public – same signature as before + confidence)
# ─────────────────────────────────────────────────────────────────────────────

def detect_bands_in_lane(
    processed_img: np.ndarray,
    lane_x: int,
    half_width: int = 20,
) -> Tuple[np.ndarray, np.ndarray, int, int]:
    """
    Detect bands (horizontal dark stripes) within one lane.

    Returns (band_peaks_y, intensities, left_x, right_x).

    Improvements vs v1:
    - half_width scales with image width if default 20 is too narrow
    - prominence threshold lowered from 8% → 4% of lane max
    - distance between peaks tightened from 10 → 8 px
    - secondary fallback with even lower thresholds
    """
    h, w = processed_img.shape

    # Scale half-width for high-res images
    effective_half = max(half_width, int(w * 0.015))

    left  = max(lane_x - effective_half, 0)
    right = min(lane_x + effective_half, w)

    lane_region         = processed_img[:, left:right]
    horizontal_profile  = np.sum(lane_region, axis=1).astype(float)

    if np.max(horizontal_profile) == 0:
        return np.array([]), np.array([]), left, right

    peak_max    = float(np.max(horizontal_profile))

    # Progressive threshold relaxation - works for all image types
    band_peaks, props = np.array([]), {"prominences": np.array([])}
    for prom_pct, min_dist in [(0.04, 8), (0.02, 6), (0.01, 5), (0.005, 4)]:
        band_peaks, props = find_peaks(
            horizontal_profile,
            distance=min_dist,
            prominence=max(peak_max * prom_pct, 10),
        )
        if len(band_peaks) >= 2:
            break

    intensities = horizontal_profile[band_peaks] if len(band_peaks) else np.array([])
    return band_peaks, intensities, left, right


def detect_bands_with_confidence(
    processed_img: np.ndarray,
    lane_x: int,
    half_width: int = 20,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, int, int]:
    """
    Like detect_bands_in_lane but also returns a confidence array (0-1).
    Used internally; route handlers call the standard function for compatibility.
    """
    h, w = processed_img.shape
    effective_half = max(half_width, int(w * 0.015))
    left  = max(lane_x - effective_half, 0)
    right = min(lane_x + effective_half, w)

    lane_region        = processed_img[:, left:right]
    hp                 = np.sum(lane_region, axis=1).astype(float)
    peak_max           = float(np.max(hp)) if np.max(hp) > 0 else 1.0

    band_peaks, props = find_peaks(hp, distance=8, prominence=max(peak_max * 0.04, 50))
    if len(band_peaks) == 0:
        band_peaks, props = find_peaks(hp, distance=6, prominence=max(peak_max * 0.02, 20))

    if len(band_peaks) == 0:
        return np.array([]), np.array([]), np.array([]), left, right

    intensities = hp[band_peaks]
    prominences = props["prominences"]

    # Confidence: normalise prominence against lane max; cap at 1.0
    confidence = np.clip(prominences / (peak_max * 0.15), 0.0, 1.0)

    return band_peaks, intensities, confidence, left, right


# ─────────────────────────────────────────────────────────────────────────────
# kDa mapper  (public – identical to v1)
# ─────────────────────────────────────────────────────────────────────────────

def build_kda_mapper(
    ruler_positions: np.ndarray,
    ruler_kda_values: List[float],
) -> Callable[[float], float]:
    """
    Build a pixel-Y → kDa interpolation function.
    Log-linear interpolation on the kDa axis (standard for gel analysis).
    """
    if len(ruler_positions) < 2 or len(ruler_kda_values) < 2:
        raise ValueError("Need at least 2 ruler bands and 2 kDa values")

    min_len = min(len(ruler_positions), len(ruler_kda_values))
    pixel_pts = np.array(ruler_positions[:min_len], dtype=float)
    kda_pts   = np.array(ruler_kda_values[:min_len],  dtype=float)

    sorted_pairs = sorted(zip(pixel_pts, kda_pts), key=lambda x: x[0])
    pixel_pts = np.array([p for p, _ in sorted_pairs])
    kda_pts   = np.array([k for _, k in sorted_pairs])

    if np.any(kda_pts <= 0):
        raise ValueError("All kDa values must be positive numbers")

    log_kda = np.log10(kda_pts)

    def pixel_to_kda(pixel_y: float) -> float:
        return float(10 ** np.interp(pixel_y, pixel_pts, log_kda))

    return pixel_to_kda


# ─────────────────────────────────────────────────────────────────────────────
# AWS Bedrock / Nova AI validation  (optional)
# ─────────────────────────────────────────────────────────────────────────────

def _encode_image_for_bedrock(image_path: str) -> Tuple[str, str]:
    """Return (base64_data, media_type) for Bedrock's image block."""
    ext = Path(image_path).suffix.lower()
    media_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                 ".png": "image/png",  ".tif": "image/png", ".tiff": "image/png"}
    mt = media_map.get(ext, "image/png")

    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        try:
            import tifffile
            raw = tifffile.imread(image_path)
            img = cv2.normalize(raw, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            if img.ndim == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        except Exception:
            raise ValueError(f"Cannot read {image_path} for Bedrock")

    _, buf = cv2.imencode(".png", img)
    return base64.b64encode(buf.tobytes()).decode("utf-8"), "image/png"


def ai_validate_bands(
    image_path: str,
    cv_bands: List[Dict],
    lane_count: int,
    aws_region: str = "us-east-1",
    model_id: str = "amazon.nova-pro-v1:0",
) -> Dict:
    """
    Nova AI second-opinion analysis.
    
    Nova acts as an expert biochemist that:
    1. Looks at the actual gel image
    2. Validates CV-detected bands (confirms real vs noise)
    3. Finds bands CV missed (especially faint ones)
    4. Gives plain-English quality assessment
    5. Flags problematic lanes (overloaded, smeared, empty)
    
    Falls back gracefully if Bedrock is unavailable.
    """
    if not _BOTO3_AVAILABLE:
        return {"error": "boto3 not installed", "cv_bands_passed_through": cv_bands}

    try:
        client = boto3.client("bedrock-runtime", region_name=aws_region)
        b64, mt = _encode_image_for_bedrock(image_path)

        band_summary = json.dumps([
            {"lane": b["lane"], "y": b["y"], "kDa": b.get("molecularWeight", "?"),
             "intensity": b.get("intensity", "?")}
            for b in cv_bands
        ], indent=2)

        prompt = f"""You are an expert molecular biology scientist reviewing a gel electrophoresis image.

{lane_count} lanes were detected by computer vision.

CV pipeline detected these bands (lane index 0-based, y-pixel from top, kDa, intensity):
{band_summary}

Carefully examine the gel image and provide a COMPLETE quality control report:

1. VALIDATE: Which CV-detected bands are genuine? (list band IDs)
2. MISSED BANDS: Any visible bands CV missed? (faint, top/bottom edges, overloaded lanes)
3. FALSE POSITIVES: Any CV detections that are noise/smear/artefact? (list IDs)
4. LANE QUALITY: For each lane assess: normal / overloaded / empty / smeared / faint
5. PASS/FAIL: Does each lane pass QC? Fail if: empty, heavily smeared, severely overloaded
6. CONTAMINATION: Any signs of contamination, extra unexpected bands, or cross-contamination between lanes?
7. CONCENTRATION: Which lanes appear to have high/medium/low DNA or protein concentration based on band brightness?
8. SAMPLE COMPARISON: Which lanes look similar to each other? Any notable differences?
9. RECOMMENDATIONS: Specific actionable advice per lane (re-run, dilute, check sample, looks good etc.)
10. OVERALL SUMMARY: 3-4 sentences a lab scientist would find immediately useful

Respond ONLY with valid JSON, no markdown, no extra text:
{{
  "validated_band_ids": [list of integer band IDs confirmed as genuine],
  "suggested_bands": [
    {{"lane": int, "approx_y": int, "estimated_kda": float_or_null, "reason": "string"}}
  ],
  "false_positive_ids": [list of integer band IDs to remove],
  "lane_quality": [
    {{
      "lane": int,
      "status": "normal|overloaded|empty|smeared|faint",
      "pass_fail": "pass|fail",
      "concentration": "high|medium|low|none",
      "contamination": "none|possible|likely",
      "recommendation": "specific actionable advice for this lane",
      "note": "brief observation"
    }}
  ],
  "similar_lanes": [
    {{"lanes": [int, int], "similarity": "high|medium", "note": "string"}}
  ],
  "contamination_detected": false,
  "quality": "good|fair|poor",
  "summary": "3-4 sentences of expert analysis"
}}"""

        # Scale max tokens with number of bands
        max_tokens = min(4096, max(1024, len(cv_bands) * 20))

        body = {
            "schemaVersion": "messages-v1",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": mt.split("/")[1],
                                "source": {"bytes": b64},
                            }
                        },
                        {"text": prompt},
                    ],
                }
            ],
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0.1},
        }

        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        result_text = json.loads(response["body"].read())
        ai_text = result_text["output"]["message"]["content"][0]["text"]

        # Extract JSON from response robustly
        clean = ai_text.strip()
        # Strip markdown fences
        if "```" in clean:
            parts = clean.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    clean = part
                    break
        # Find JSON object boundaries
        start_idx = clean.find("{")
        end_idx = clean.rfind("}") + 1
        if start_idx != -1 and end_idx > start_idx:
            clean = clean[start_idx:end_idx]

        try:
            ai_result = json.loads(clean)
        except json.JSONDecodeError:
            # If still failing, return safe defaults keeping all CV bands
            logger.warning("Nova JSON parse failed, keeping all CV bands")
            return {
                "validated_bands": cv_bands,
                "suggested_bands": [],
                "removed_bands": [],
                "lane_quality": [],
                "quality": "unknown",
                "summary": "AI analysis completed but response parsing failed. CV results retained.",
                "ai_used": True,
            }

        # ── Build final band list ─────────────────────────────────────────
        fp_ids = set(ai_result.get("false_positive_ids", []))
        validated = [b for b in cv_bands if b["id"] not in fp_ids]
        suggested  = ai_result.get("suggested_bands", [])

        return {
            "validated_bands":  validated,
            "suggested_bands":  suggested,
            "removed_bands":    [b for b in cv_bands if b["id"] in fp_ids],
            "lane_quality":     ai_result.get("lane_quality", []),
            "quality":          ai_result.get("quality", "unknown"),
            "summary":          ai_result.get("summary", ""),
            "ai_used":          True,
        }

    except Exception as exc:
        logger.warning("Bedrock AI validation failed: %s", exc)
        return {
            "validated_bands": cv_bands,
            "suggested_bands": [],
            "removed_bands":   [],
            "ai_used":         False,
            "error":           str(exc),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Annotated image helper
# ─────────────────────────────────────────────────────────────────────────────

def annotate_gel_image(
    original_gray: np.ndarray,
    lane_peaks: List[int],
    bands: List[Dict],
    suggested_bands: Optional[List[Dict]] = None,
) -> np.ndarray:
    """Draw lanes, confirmed bands, and AI-suggested bands onto the image."""
    vis = cv2.cvtColor(original_gray, cv2.COLOR_GRAY2BGR)

    # Draw lane lines
    for i, lx in enumerate(lane_peaks):
        cv2.line(vis, (int(lx), 0), (int(lx), vis.shape[0]), (0, 180, 255), 1)
        cv2.putText(vis, f"L{i+1}", (int(lx) - 12, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 180, 255), 1, cv2.LINE_AA)

    # Draw CV-detected bands
    for band in bands:
        x, y = int(band["x"]), int(band["y"])
        conf  = band.get("confidence", 1.0)
        # Green → yellow gradient based on confidence
        g = int(255 * conf)
        r = int(255 * (1 - conf))
        color = (0, g, r)
        cv2.circle(vis, (x, y), 5, color, -1)
        label = band.get("name", "")
        cv2.putText(vis, label, (x + 7, y + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(vis, label, (x + 7, y + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)

    # Draw AI-suggested bands (cyan, dashed-look via cross marker)
    if suggested_bands:
        for sb in suggested_bands:
            # approximate x from lane number
            lane_idx = sb.get("lane", 0)
            sx = int(lane_peaks[lane_idx]) if lane_idx < len(lane_peaks) else 0
            sy = int(sb.get("approx_y", 0))
            cv2.drawMarker(vis, (sx, sy), (255, 255, 0),
                           cv2.MARKER_DIAMOND, 14, 2)
            cv2.putText(vis, "AI?", (sx + 8, sy + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 0), 1, cv2.LINE_AA)

    return vis
