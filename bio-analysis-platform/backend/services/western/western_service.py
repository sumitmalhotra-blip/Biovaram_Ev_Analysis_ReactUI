from fastapi.responses import JSONResponse
import numpy as np
import cv2
import os
import shutil
import pandas as pd
from scipy.signal import find_peaks
import plotly.graph_objects as go
from typing import Optional, List
import json
from pathlib import Path
from services.tem.tem_service import SessionLocal
from services.western.western_model import WesternBlot


import sys

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parents[1]

if getattr(sys, 'frozen', False):
    _data_root = Path(os.getcwd())
else:
    _data_root = BACKEND_DIR

UPLOAD_FOLDER = str(_data_root / "uploads" / "western")
RESULT_FOLDER = str(_data_root / "results" / "western")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)


def safe_filename(filename: str) -> str:
    return filename.replace(" ", "_")


def preprocess_image(file_path: str):
    img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not read image at path: {file_path}")

    img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)
    inv = 255 - img
    blur = cv2.GaussianBlur(inv, (5, 5), 0)
    return img, blur


def detect_lanes(processed_img: np.ndarray):
    vertical_profile = np.sum(processed_img, axis=0)
    lane_peaks, _ = find_peaks(
        vertical_profile,
        distance=35,
        prominence=max(np.max(vertical_profile) * 0.08, 500)
    )
    return lane_peaks


def detect_bands_in_lane(processed_img: np.ndarray, lane_x: int, half_width: int = 20):
    left = max(lane_x - half_width, 0)
    right = min(lane_x + half_width, processed_img.shape[1])

    lane_region = processed_img[:, left:right]
    horizontal_profile = np.sum(lane_region, axis=1)

    if np.max(horizontal_profile) == 0:
        return np.array([]), np.array([]), left, right

    band_peaks, _ = find_peaks(
        horizontal_profile,
        distance=10,
        prominence=max(np.max(horizontal_profile) * 0.08, 80)
    )

    intensities = horizontal_profile[band_peaks] if len(band_peaks) else np.array([])
    return band_peaks, intensities, left, right


def build_kda_mapper(ruler_positions: np.ndarray, ruler_kda_values: List[float]):
    """
    Build a pixel-to-kDa interpolation function from ruler band positions and their kDa values.
    ruler_positions: pixel Y positions of ruler bands (already matched to kda values 1:1)
    ruler_kda_values: corresponding kDa values (must be same length, descending order top→bottom)
    """
    if len(ruler_positions) < 2 or len(ruler_kda_values) < 2:
        raise ValueError("Need at least 2 ruler bands and 2 kDa values")

    min_len = min(len(ruler_positions), len(ruler_kda_values))

    pixel_points = np.array(ruler_positions[:min_len], dtype=float)
    kda_points = np.array(ruler_kda_values[:min_len], dtype=float)

    # Sort by pixel position (top to bottom = ascending Y)
    sorted_pairs = sorted(zip(pixel_points, kda_points), key=lambda x: x[0])
    pixel_points = np.array([p for p, _ in sorted_pairs], dtype=float)
    kda_points = np.array([k for _, k in sorted_pairs], dtype=float)

    # Guard: all kDa must be positive for log interpolation
    if np.any(kda_points <= 0):
        raise ValueError("All kDa values must be positive numbers")

    log_kda_points = np.log10(kda_points)

    def pixel_to_kda(pixel_y: float) -> float:
        interp_value = np.interp(pixel_y, pixel_points, log_kda_points)
        return float(10 ** interp_value)

    return pixel_to_kda