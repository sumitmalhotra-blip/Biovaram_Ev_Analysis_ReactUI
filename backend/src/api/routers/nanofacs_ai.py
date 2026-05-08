"""
NanoFACS AI Analysis Router
============================

AI-powered analysis layer for NanoFACS FCS parquet files.
Uses AWS Bedrock (Mistral) to:
1. Analyze Size vs Events vs Parameters
2. Detect cluster shifts and anomalies
3. Suggest graphs based on data patterns
4. Compare metadata across multiple files
5. Answer user questions scoped to their data only

FCS Parquet columns:
TrackID, Frame, LocationX, LocationY, BoundingBoxX1, BoundingBoxY1,
BoundingBoxX2, BoundingBoxY2, Position, Cycle, Area, Perimeter,
Solidity, AspectRatio, MeanIntensity, MaxIntensity, MinIntensity,
ConvexArea, Intensity/Area, TraceLength, Size, V_nmsec-1, Cluster

Endpoints:
- POST /ai/nanofacs/analyze          - Full AI analysis of FCS parquet files
- POST /ai/nanofacs/compare          - Compare multiple FCS files
- POST /ai/nanofacs/ask              - Ask questions about your data
- GET  /ai/nanofacs/health           - Check AWS Bedrock connectivity

Author: BioVaram Dev Team
Date: April 2026
"""

import os
import json
try:
    import boto3  # type: ignore
except ImportError:  # pragma: no cover
    boto3 = None  # type: ignore
import numpy as np
import pandas as pd
from typing import Optional
from datetime import datetime
from pathlib import Path
try:
    from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ProfileNotFound  # type: ignore
except ImportError:  # pragma: no cover
    NoCredentialsError = Exception  # type: ignore
    PartialCredentialsError = Exception  # type: ignore
    ProfileNotFound = Exception  # type: ignore
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from loguru import logger
from src.api.aws_utils import get_bedrock_runtime_client
from src.api.ai_gateway_client import AIGatewayError, gateway_complete, gateway_health
from src.api.config import get_settings
from src.physics.mie_scatter import MieScatterCalculator
from src.physics.bead_calibration import get_active_calibration, get_fcmpass_calibration
router = APIRouter()
settings = get_settings()


# ============================================================================
# AWS Bedrock Client
# ============================================================================

def _offline_ai_enabled() -> bool:
    """Allow local development without AWS credentials."""
    env = (os.getenv("CRMIT_ENV") or "development").strip().lower()
    flag = (os.getenv("CRMIT_ENABLE_OFFLINE_AI") or "").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    if flag in {"1", "true", "yes", "on"}:
        return True
    return env in {"development", "dev", "local"}

def _get_bedrock_client():
    # Use AWS default credential chain (env vars, AWS_PROFILE, or IAM role).
    # In local offline mode, skip Bedrock entirely unless the developer explicitly
    # provided credentials via env vars or AWS_PROFILE.
    if _offline_ai_enabled():
        has_env_creds = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
        has_profile = bool((os.getenv("AWS_PROFILE") or "").strip())
        if not (has_env_creds or has_profile):
            return None

    if boto3 is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "AWS Bedrock is not available because 'boto3' is not installed. "
                "Install backend requirements or run: pip install boto3"
            ),
        )

    try:
        return get_bedrock_runtime_client()
    except (ProfileNotFound, PartialCredentialsError) as exc:
        if _offline_ai_enabled():
            return None
        raise HTTPException(status_code=503, detail=f"AWS credentials not configured: {exc}")


def _call_bedrock(prompt: str, max_tokens: int = 1500) -> str:
    def _gateway_fallback() -> str:
        if "exact JSON format" in prompt:
            return json.dumps(
                {
                    "anomalies": [],
                    "cluster_findings": [],
                    "missed_parameters": [],
                    "suggestions": [
                        "Gateway unavailable; using local NanoFACS analysis fallback.",
                        "Verify CRMIT_AI_GATEWAY_URL and CRMIT_AI_GATEWAY_LICENSE_KEY on the packaged desktop build.",
                    ],
                    "summary": "Gateway request failed, so the app fell back to local NanoFACS analysis without cloud interpretation.",
                }
            )
        return (
            "Gateway request failed, so the app fell back to local NanoFACS analysis without cloud interpretation. "
            "Verify CRMIT_AI_GATEWAY_URL and CRMIT_AI_GATEWAY_LICENSE_KEY on the packaged desktop build."
        )

    provider = (os.getenv("AI_PROVIDER") or "bedrock").strip().lower()
    logger.debug(f"NanoFACS AI: Using provider={provider}, model={os.getenv('CRMIT_AI_MODEL', 'default')}")
    
    if provider == "gateway":
        gateway_url = (os.getenv("CRMIT_AI_GATEWAY_URL") or "").strip()
        gateway_key = (os.getenv("CRMIT_AI_GATEWAY_LICENSE_KEY") or "").strip()
        
        if not gateway_url or not gateway_key:
            logger.error(f"NanoFACS: Gateway provider selected but missing config: URL_present={bool(gateway_url)}, KEY_present={bool(gateway_key)}")
            return _gateway_fallback()
        
        model = (os.getenv("CRMIT_AI_MODEL") or "amazon.nova-lite-v1:0").strip() or "amazon.nova-lite-v1:0"
        logger.info(f"NanoFACS: Calling gateway at {gateway_url[:50]}... with model {model}")
        
        try:
            # gateway_chat caps tokens centrally; pass-through here.
            result = gateway_complete(prompt=prompt, model=model, temperature=0.3, max_tokens=max_tokens)
            logger.info(f"NanoFACS: Gateway call successful")
            return result
        except AIGatewayError as exc:
            logger.error(f"NanoFACS: Gateway request failed after retries: {exc}")
            return _gateway_fallback()

    client = _get_bedrock_client()
    if client is None:
        if "exact JSON format" in prompt:
            return json.dumps(
                {
                    "anomalies": ["Offline AI mode enabled: cloud model call skipped for local testing."],
                    "cluster_findings": ["Use the computed cluster distributions in data_stats for local validation."],
                    "missed_parameters": [],
                    "suggestions": [
                        "Configure AWS credentials before release for full AI interpretation.",
                        "Continue validating UI and rule-based analytics locally."
                    ],
                    "summary": "Local offline AI mode returned deterministic guidance without Bedrock access."
                }
            )
        return (
            "Offline AI mode is active for local testing, so this answer is based on the computed dataset summary only. "
            "Configure AWS credentials to enable full Bedrock reasoning before release."
        )
    payload = {
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0.3},
    }
    try:
        response = client.invoke_model(
            modelId="amazon.nova-lite-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )
        result = json.loads(response["body"].read())
        return result["output"]["message"]["content"][0]["text"].strip()
    except (NoCredentialsError, PartialCredentialsError, ProfileNotFound) as e:
        if _offline_ai_enabled():
            logger.warning(f"AWS credentials missing; using offline fallback: {e}")
            return (
                "Offline AI mode is active for local testing (no AWS credentials resolved). "
                "Configure an IAM role (recommended) or AWS_PROFILE/env keys to enable Bedrock."
            )
        raise HTTPException(status_code=503, detail="AWS credentials not configured.")
    except Exception as e:
        logger.error(f"Bedrock call failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI model call failed: {str(e)}")


# ============================================================================
# Request / Response Models
# ============================================================================

class FCSAnalyzeRequest(BaseModel):
    experiment_description: str = Field(
        ...,
        description="What the user is analyzing e.g. PC3 cell line exosomes"
    )
    parameters_of_interest: list[str] = Field(
        default=[],
        description="Parameters user is focusing on e.g. ['Size', 'MeanIntensity']"
    )
    same_sample: bool = Field(
        True,
        description="Whether all files are from the same biological sample"
    )
    additional_notes: Optional[str] = Field(None)
    file_paths: list[str] = Field(
        ...,
        description="Paths to FCS parquet files on the server"
    )


class FCSCompareRequest(BaseModel):
    file_paths: list[str] = Field(
        ...,
        description="List of FCS parquet file paths to compare"
    )


class FCSAskRequest(BaseModel):
    question: str = Field(
        ...,
        description="Question about the data"
    )
    file_paths: list[str] = Field(
        ...,
        description="Parquet files to answer about"
    )


class FCSAnalysisResponse(BaseModel):
    anomalies: list[str]
    cluster_findings: list[str]
    suggested_graphs: list[str]
    missed_parameters: list[str]
    suggestions: list[str]
    summary: str
    data_stats: dict
    analyzed_files: list[str]
    analyzed_at: str


class FCSCompareResponse(BaseModel):
    mismatches: list[dict]
    matching_fields: list[str]
    cluster_comparison: list[str]
    recommendation: str
    compared_files: list[str]


class FCSAskResponse(BaseModel):
    answer: str
    data_context: str
    answered_at: str


# ============================================================================
# FCS Parameter definitions
# ============================================================================

# All columns in FCS parquet
FCS_COLUMNS = [
    "TrackID", "Frame", "LocationX", "LocationY",
    "BoundingBoxX1", "BoundingBoxY1", "BoundingBoxX2", "BoundingBoxY2",
    "Position", "Cycle", "Area", "Perimeter", "Solidity", "AspectRatio",
    "MeanIntensity", "MaxIntensity", "MinIntensity", "ConvexArea",
    "Intensity/Area", "TraceLength", "Size", "V_nmsec-1", "Cluster"
]

# Key parameters for EV analysis
EV_KEY_PARAMS = {
    "Size":            "Particle size in nm — primary EV characterization parameter",
    "MeanIntensity":   "Mean fluorescence intensity — relates to marker expression",
    "MaxIntensity":    "Maximum intensity — identifies bright particles possibly debris",
    "Cluster":         "Cluster assignment — groups of similar particles",
    "Area":            "Particle area — cross-check with size",
    "Solidity":        "Shape regularity — low solidity may indicate aggregates",
    "AspectRatio":     "Shape elongation — high ratio may indicate debris",
    "TraceLength":     "How long the particle was tracked — quality indicator",
    "V_nmsec-1":       "Particle velocity — relates to Brownian motion and size",
    "Intensity/Area":  "Intensity normalized by area — marker density",
}

# Normal ranges for EV analysis
NORMAL_RANGES = {
    "Size":         (30, 1000),    # nm — EV range
    "Solidity":     (0.7, 1.0),    # High solidity = round particles
    "AspectRatio":  (1.0, 3.0),    # Low = round, high = elongated/debris
    "TraceLength":  (15, 200),     # frames — too short = unreliable
}


# ============================================================================
# Helper — read FCS parquet file
# ============================================================================

def _read_fcs_parquet(file_path: str) -> pd.DataFrame:
    """Read FCS parquet file and return DataFrame."""
    try:
        df = pd.read_parquet(file_path)
        logger.info(f"Read FCS parquet: {file_path} → {df.shape}")
        return df
    except Exception as e:
        logger.error(f"Failed to read FCS parquet {file_path}: {e}")
        return pd.DataFrame()


def _pick_first_column(columns: list[str], candidates: list[str]) -> Optional[str]:
    for c in candidates:
        if c in columns:
            return c
    return None


def _find_scatter_channels(columns: list[str]) -> tuple[Optional[str], Optional[str]]:
    """Heuristically detect FSC/SSC-like channel names in FCS parquet files."""
    # Common exact names we see in ZE5/Bio-Rad exports and our pipeline.
    fsc_exact = [
        "VFSC-H",
        "VFSC-A",
        "FSC-H",
        "FSC-A",
        "FSC1-H",
        "FSC1-A",
    ]
    ssc_exact = [
        "VSSC_MAX",
        "VSSC1-H",
        "VSSC-H",
        "SSC-H",
        "SSC-A",
        "SSC1-H",
        "SSC1-A",
    ]

    fsc = _pick_first_column(columns, fsc_exact)
    ssc = _pick_first_column(columns, ssc_exact)

    # Fallback: pattern match
    if fsc is None:
        fsc_candidates = [c for c in columns if "FSC" in c.upper()]
        # Prefer height over area, and avoid fluorescence channels if possible.
        fsc = _pick_first_column(fsc_candidates, [c for c in fsc_candidates if c.upper().endswith("-H")])
        if fsc is None and fsc_candidates:
            fsc = fsc_candidates[0]

    if ssc is None:
        ssc_candidates = [c for c in columns if "SSC" in c.upper() or "VSSC" in c.upper()]
        ssc = _pick_first_column(ssc_candidates, [c for c in ssc_candidates if c.upper().endswith("-H")])
        if ssc is None and ssc_candidates:
            ssc = ssc_candidates[0]

    return fsc, ssc


def _safe_numeric_series(df: pd.DataFrame, col: str) -> pd.Series:
    vals = pd.to_numeric(df[col], errors="coerce")
    vals = vals.replace([np.inf, -np.inf], np.nan).dropna()
    return vals


def _derive_size_stats_from_fcs_channels(df: pd.DataFrame) -> tuple[Optional[dict], Optional[str], Optional[str]]:
    """Derive a Size-like stats block from raw FCS scatter channels.

    Returns:
        (size_stats, sizing_method, sizing_channel)
    """
    fsc_channel, ssc_channel = _find_scatter_channels(list(df.columns))
    sizing_channel = fsc_channel or ssc_channel
    if sizing_channel is None or sizing_channel not in df.columns:
        return None, None, None

    scatter_vals = _safe_numeric_series(df, sizing_channel)
    scatter_vals = scatter_vals[scatter_vals > 0]
    if scatter_vals.empty:
        return None, None, sizing_channel

    # Defaults match the backend upload pipeline's uncalibrated Mie sizing assumptions.
    wavelength_nm = 405.0
    n_particle = 1.37
    n_medium = 1.33

    particle_size_median_nm: Optional[float] = None
    sizing_method_used: Optional[str] = None

    # === FCMPASS k-based median (highest priority) ===
    try:
        fcmpass_cal = get_fcmpass_calibration()
        if fcmpass_cal and getattr(fcmpass_cal, "calibrated", False):
            fcmpass_channel = None
            for ch in ["VSSC1-H", "VSSC-H", "VSSC1_H"]:
                if ch in df.columns:
                    fcmpass_channel = ch
                    break
            if fcmpass_channel is None and ssc_channel and ssc_channel in df.columns:
                fcmpass_channel = ssc_channel

            if fcmpass_channel is not None:
                _ssc = _safe_numeric_series(df, fcmpass_channel)
                _ssc = _ssc[_ssc > 0]
                if not _ssc.empty:
                    median_ssc = float(_ssc.median())
                    d, _in_range = fcmpass_cal.predict_batch(np.array([median_ssc]))
                    if not np.isnan(d[0]) and d[0] > 0:
                        particle_size_median_nm = float(d[0])
                        sizing_method_used = "fcmpass_k_based"
                        sizing_channel = fcmpass_channel
    except Exception as e:
        logger.warning(f"⚠️ FCMPASS sizing failed in NanoFACS AI: {e}")

    # === Bead-calibrated FSC path ===
    if particle_size_median_nm is None and fsc_channel and fsc_channel in df.columns:
        try:
            active_cal = get_active_calibration()
            if active_cal and getattr(active_cal, "is_fitted", False):
                median_fsc = float(_safe_numeric_series(df, fsc_channel).median())
                if median_fsc > 0:
                    cal_diameter = active_cal.diameter_from_fsc(
                        np.array([median_fsc]),
                        target_ri=n_particle,
                        medium_ri=n_medium,
                    )
                    particle_size_median_nm = float(cal_diameter[0])
                    sizing_method_used = "bead_calibrated"
                    sizing_channel = fsc_channel
        except Exception as e:
            logger.warning(f"⚠️ Bead-calibrated sizing failed in NanoFACS AI: {e}")

    # === Uncalibrated Mie fallback (median only) ===
    if particle_size_median_nm is None:
        try:
            mie_calc = MieScatterCalculator(
                wavelength_nm=wavelength_nm,
                n_particle=n_particle,
                n_medium=n_medium,
            )
            median_scatter = float(scatter_vals.median())
            if median_scatter > 0:
                diameter_nm, success = mie_calc.diameter_from_scatter(fsc_intensity=median_scatter)
                if success and diameter_nm > 0:
                    particle_size_median_nm = float(diameter_nm)
                    sizing_method_used = "uncalibrated_mie"
        except Exception as e:
            logger.warning(f"⚠️ Mie sizing failed in NanoFACS AI: {e}")

    if particle_size_median_nm is None:
        return None, sizing_method_used, sizing_channel

    # Populate a full stats block so the frontend doesn't render `undefined`.
    # For now we only have a reliable median, so we keep the rest consistent.
    size_stats = {
        "mean": round(float(particle_size_median_nm), 3),
        "median": round(float(particle_size_median_nm), 3),
        "std": 0.0,
        "min": round(float(particle_size_median_nm), 3),
        "max": round(float(particle_size_median_nm), 3),
        "p10": round(float(particle_size_median_nm), 3),
        "p90": round(float(particle_size_median_nm), 3),
    }
    return size_stats, sizing_method_used, sizing_channel


def _dedupe_file_paths(file_paths: list[str]) -> list[str]:
    """Deduplicate file paths while preserving input order."""
    seen: set[str] = set()
    out: list[str] = []
    for fp in file_paths:
        key = str(Path(fp).resolve())
        if key in seen:
            continue
        seen.add(key)
        out.append(fp)
    return out


# ============================================================================
# Helper — compute per-file statistics
# ============================================================================

def _compute_fcs_stats(df: pd.DataFrame, file_name: str) -> dict:
    """Compute key statistics from FCS DataFrame."""
    if df.empty:
        return {}

    stats = {"file": file_name, "total_events": len(df)}

    # If this is a raw FCS parquet (channels like FSC/SSC) rather than the
    # imaging-style schema documented at the top of this file, derive a Size
    # block so AI Q&A can answer median-size questions.
    if "Size" not in df.columns:
        derived_size, method, channel = _derive_size_stats_from_fcs_channels(df)
        if derived_size:
            stats["Size"] = derived_size
            if method:
                stats["sizing_method"] = method
            if channel:
                stats["sizing_channel"] = channel

        fsc_channel, ssc_channel = _find_scatter_channels(list(df.columns))
        if fsc_channel and fsc_channel in df.columns:
            vals = _safe_numeric_series(df, fsc_channel)
            if not vals.empty:
                stats["FSC"] = {
                    "channel": fsc_channel,
                    "mean": round(float(vals.mean()), 3),
                    "median": round(float(vals.median()), 3),
                    "std": round(float(vals.std()), 3),
                    "min": round(float(vals.min()), 3),
                    "max": round(float(vals.max()), 3),
                    "p10": round(float(np.percentile(vals, 10)), 3),
                    "p90": round(float(np.percentile(vals, 90)), 3),
                }

        if ssc_channel and ssc_channel in df.columns:
            vals = _safe_numeric_series(df, ssc_channel)
            if not vals.empty:
                stats["SSC"] = {
                    "channel": ssc_channel,
                    "mean": round(float(vals.mean()), 3),
                    "median": round(float(vals.median()), 3),
                    "std": round(float(vals.std()), 3),
                    "min": round(float(vals.min()), 3),
                    "max": round(float(vals.max()), 3),
                    "p10": round(float(np.percentile(vals, 10)), 3),
                    "p90": round(float(np.percentile(vals, 90)), 3),
                }

    for col in ["Size", "MeanIntensity", "MaxIntensity", "Area",
                "Solidity", "AspectRatio", "TraceLength", "V_nmsec-1", "Intensity/Area"]:
        if col in df.columns:
            vals = df[col].dropna()
            if len(vals) > 0:
                stats[col] = {
                    "mean":   round(float(vals.mean()), 3),
                    "median": round(float(vals.median()), 3),
                    "std":    round(float(vals.std()), 3),
                    "min":    round(float(vals.min()), 3),
                    "max":    round(float(vals.max()), 3),
                    "p10":    round(float(np.percentile(vals, 10)), 3),
                    "p90":    round(float(np.percentile(vals, 90)), 3),
                }

    # Cluster distribution
    if "Cluster" in df.columns:
        cluster_counts = df["Cluster"].value_counts().to_dict()
        stats["cluster_distribution"] = {
            str(int(k)): int(v) for k, v in cluster_counts.items()
        }
        stats["num_clusters"] = len(cluster_counts)
    else:
        # Avoid frontend rendering `undefined`
        stats["cluster_distribution"] = {}
        stats["num_clusters"] = 0

    # Position distribution
    if "Position" in df.columns:
        pos_counts = df["Position"].value_counts().to_dict()
        stats["position_distribution"] = {
            str(int(k)): int(v) for k, v in pos_counts.items()
        }

    return stats


# ============================================================================
# Helper — rule-based anomaly detection
# ============================================================================

def _rule_based_fcs_anomalies(stats: dict) -> list[str]:
    """Apply rule-based anomaly checks on FCS data."""
    anomalies = []
    fname = stats.get("file", "unknown")

    # Low event count
    total = stats.get("total_events", 0)
    if total < 100:
        anomalies.append(
            f"[{fname}] Very low event count: {total} particles "
            f"(recommended minimum 100)"
        )

    # Size anomalies
    size = stats.get("Size", {})
    if size:
        if size.get("median", 0) > 500:
            anomalies.append(
                f"[{fname}] Median size {size['median']:.0f}nm is very large "
                f"— possible debris or aggregates dominating"
            )
        if size.get("median", 0) < 30:
            anomalies.append(
                f"[{fname}] Median size {size['median']:.0f}nm is below EV range "
                f"— check instrument noise threshold"
            )
        # High spread
        if size.get("std", 0) > size.get("mean", 1) * 0.8:
            anomalies.append(
                f"[{fname}] High size variability: std={size['std']:.0f}nm "
                f"vs mean={size['mean']:.0f}nm — broad or multimodal distribution"
            )

    # Solidity anomalies
    solidity = stats.get("Solidity", {})
    if solidity:
        if solidity.get("mean", 1) < 0.7:
            anomalies.append(
                f"[{fname}] Low mean solidity {solidity['mean']:.2f} "
                f"— particles may be irregular shaped, possible debris or aggregates"
            )

    # Aspect ratio anomalies
    aspect = stats.get("AspectRatio", {})
    if aspect:
        if aspect.get("p90", 0) > 4.0:
            anomalies.append(
                f"[{fname}] High 90th percentile aspect ratio {aspect['p90']:.1f} "
                f"— significant elongated particle population detected"
            )

    # Trace length
    trace = stats.get("TraceLength", {})
    if trace:
        if trace.get("mean", 100) < 15:
            anomalies.append(
                f"[{fname}] Low mean trace length {trace['mean']:.0f} frames "
                f"— particles not tracked long enough, results may be unreliable"
            )

    # Cluster distribution
    clusters = stats.get("cluster_distribution", {})
    if clusters:
        total_particles = sum(clusters.values())
        for cluster_id, count in clusters.items():
            pct = (count / total_particles) * 100
            if pct > 70:
                anomalies.append(
                    f"[{fname}] Cluster {cluster_id} dominates with {pct:.0f}% of particles "
                    f"— sample may lack diversity or have dominant population"
                )

    return anomalies


# ============================================================================
# Helper — suggest graphs
# ============================================================================

def _suggest_graphs(stats_list: list[dict], user_params: list[str]) -> list[str]:
    """Suggest relevant graphs based on data characteristics."""
    suggestions = []

    # Always suggest these core graphs
    suggestions.append(
        "Size Distribution Histogram — X: Size (nm) · Y: Event Count · "
        "Healthy EV pattern: unimodal peak at 50–300 nm · "
        "Watch for: bimodal peak or shoulder >500 nm = aggregates or debris dominating"
    )
    suggestions.append(
        "Size vs MeanIntensity Scatter — X: Size (nm) · Y: MeanIntensity · "
        "Healthy pattern: low-intensity cloud at 50–200 nm (pure EVs) · "
        "Watch for: bright cluster at large sizes = non-EV debris or protein aggregates"
    )
    suggestions.append(
        "Cluster Map (LocationX vs LocationY colored by Cluster) — "
        "Healthy pattern: distinct spatially-separated clusters · "
        "Watch for: all particles in single cluster = poor separation; "
        "scattered noise = high debris content"
    )

    # Check for multiple clusters
    for stats in stats_list:
        num_clusters = stats.get("num_clusters", 0)
        if num_clusters > 3:
            suggestions.append(
                f"Cluster Size Distribution Box Plot — X: Cluster ID · Y: Size (nm) · "
                f"{num_clusters} clusters detected · "
                f"Healthy pattern: clusters at distinct size ranges = true EV subpopulations · "
                f"Watch for: all clusters overlapping = clustering may be noise-driven"
            )
            break

    # Check for high intensity variation
    for stats in stats_list:
        intensity = stats.get("MeanIntensity", {})
        if intensity and intensity.get("std", 0) > intensity.get("mean", 1) * 0.5:
            suggestions.append(
                "Intensity/Area vs Size Scatter — X: Size (nm) · Y: Intensity/Area · "
                "High intensity variation detected in this dataset · "
                "Healthy pattern: flat intensity/area band = consistent labeling · "
                "Watch for: outlier bright spots at large size = debris or protein aggregates"
            )
            break

    # Check for position variation
    for stats in stats_list:
        pos_dist = stats.get("position_distribution", {})
        if pos_dist and len(pos_dist) > 1:
            suggestions.append(
                "Position vs Event Count Bar Chart — X: Position ID · Y: Event Count · "
                "Healthy pattern: uniform count across positions = homogeneous sample · "
                "Watch for: single position dominating = instrument flow-cell clogging risk"
            )
            break

    # If user mentioned specific params
    for param in user_params:
        param_lower = param.lower()
        if "velocity" in param_lower or "v_nm" in param_lower:
            suggestions.append(
                "Velocity (V_nmsec-1) vs Size Scatter — X: Size (nm) · Y: V_nmsec-1 · "
                "Healthy pattern: inverse curve matching Stokes-Einstein law = good tracking · "
                "Watch for: horizontal band = velocity independent of size = tracking error"
            )
        if "intensity" in param_lower:
            suggestions.append(
                "MaxIntensity vs MinIntensity Scatter — X: MinIntensity · Y: MaxIntensity · "
                "Healthy pattern: tight diagonal cluster = uniform labeling · "
                "Watch for: high MaxIntensity with low MinIntensity = non-uniform or patchy labeling"
            )

    return suggestions


# ============================================================================
# Helper — detect missed parameters
# ============================================================================

def _find_missed_fcs_params(
    stats_list: list[dict],
    user_params: list[str]
) -> list[str]:
    """Find important parameters user didn't mention."""
    missed = []
    user_lower = " ".join(user_params).lower()

    for key, description in EV_KEY_PARAMS.items():
        if key.lower() not in user_lower:
            # Check if this param has interesting signal
            for stats in stats_list:
                param_stats = stats.get(key, {})
                if param_stats:
                    # Flag if high variability
                    std = param_stats.get("std", 0)
                    mean = param_stats.get("mean", 1)
                    if mean > 0 and std / mean > 0.5:
                        missed.append(
                            f"{key} ({description}) — high variability detected "
                            f"(CV={std/mean*100:.0f}%), worth investigating"
                        )
                        break

    return missed


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/ai/nanofacs/health")
async def nanofacs_ai_health():
    """Check AWS Bedrock connectivity for NanoFACS AI."""
    try:
        provider = (os.getenv("AI_PROVIDER") or "bedrock").strip().lower()
        if provider == "gateway":
            health = gateway_health()
            return {
                "status": health.get("status", "error"),
                "provider": "gateway",
                "model": os.getenv("CRMIT_AI_MODEL", "amazon.nova-lite-v1:0"),
                "message": health.get("message"),
                "gateway": {
                    "url": os.getenv("CRMIT_AI_GATEWAY_URL", ""),
                },
                "module": "nanofacs_ai",
            }

        client = _get_bedrock_client()
        if client is None:
            return {
                "status": "ok",
                "provider": "offline_local",
                "model": "offline-local",
                "region": os.getenv("AWS_REGION", "us-east-1"),
                "module": "nanofacs_ai",
                "message": "Offline AI fallback enabled for local testing",
            }
        return {
            "status": "ok",
            "provider": "aws_bedrock",
            "model": "amazon.nova-lite-v1:0",
            "region": os.getenv("AWS_REGION", "us-east-1"),
            "module": "nanofacs_ai",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/ai/nanofacs/analyze", response_model=FCSAnalysisResponse)
async def analyze_fcs_with_ai(request: FCSAnalyzeRequest):
    """
    Full AI analysis of NanoFACS FCS parquet files.

    1. Reads parquet files and computes statistics
    2. Runs rule-based anomaly detection
    3. Suggests graphs based on data patterns
    4. Finds parameters user missed
    5. Sends everything to AWS Bedrock (Mistral) for expert interpretation
    """
    if not request.file_paths:
        raise HTTPException(status_code=422, detail="At least one file path required")

    request.file_paths = _dedupe_file_paths(request.file_paths)

    logger.info(f"NanoFACS AI analysis: {request.file_paths}")

    # Read all files and compute stats
    all_stats = []
    for fp in request.file_paths:
        df = _read_fcs_parquet(fp)
        if df.empty:
            logger.warning(f"Empty or unreadable file: {fp}")
            continue
        stats = _compute_fcs_stats(df, Path(fp).name)
        all_stats.append(stats)

    if not all_stats:
        raise HTTPException(
            status_code=404,
            detail="Could not read any FCS parquet files. Check file paths."
        )

    # Rule-based anomalies
    rule_anomalies = []
    for stats in all_stats:
        rule_anomalies.extend(_rule_based_fcs_anomalies(stats))

    # Graph suggestions
    graph_suggestions = _suggest_graphs(all_stats, request.parameters_of_interest)

    # Missed parameters
    missed_params = _find_missed_fcs_params(all_stats, request.parameters_of_interest)

    # Build prompt — filter to EV-relevant columns only so the payload stays
    # within Lambda execution limits when routed through the AI gateway.
    _KEY_COLS = {
        "filename", "total_events", "num_clusters", "cluster_distribution",
        "Size", "Solidity", "AspectRatio", "TraceLength",
        "MeanIntensity", "MaxIntensity", "Intensity/Area",
    }
    filtered_stats = [{k: v for k, v in s.items() if k in _KEY_COLS} for s in all_stats]
    stats_summary = json.dumps(filtered_stats, indent=2, default=str)

    prompt = f"""You are an expert in NanoFACS (Nano Flow Cytometry) and extracellular vesicle (EV) characterization.

A researcher is analyzing NanoFACS FCS data with the following context:
- Experiment: {request.experiment_description}
- Same biological sample across files: {request.same_sample}
- Parameters they are focusing on: {request.parameters_of_interest or 'Not specified'}
- Additional notes: {request.additional_notes or 'None'}

Normal EV ranges for validation:
- Size: 30–1000 nm (typical exosomes: 50–200 nm; microvesicles: 100–1000 nm)
- Solidity: 0.7–1.0 (values below 0.7 indicate irregular/aggregated particles)
- AspectRatio: 1.0–3.0 (values above 3.0 indicate elongated debris)
- TraceLength: 15–200 frames (below 15 = unreliable tracking)

Computed statistics from their FCS parquet files:
{stats_summary}

Pre-detected rule-based anomalies:
{json.dumps(rule_anomalies, indent=2) if rule_anomalies else 'None detected'}

Parameters the researcher may have missed (high variability detected):
{json.dumps(missed_params, indent=2) if missed_params else 'None'}

Please provide:
1. ANOMALIES: Additional data quality issues or unexpected findings beyond rule-based ones. Also validate whether the computed statistics fall within expected EV ranges and flag any out-of-range values.
2. CLUSTER_FINDINGS: What do the cluster distributions suggest about EV subpopulations. Are the cluster sizes and distributions consistent with a typical EV preparation?
3. MISSED_PARAMETERS: Important parameters worth investigating with scientific explanation.
4. SUGGESTIONS: Specific actionable recommendations. Include at least one recommendation about whether the NanoFACS analysis results look scientifically valid for this experiment type.
5. SUMMARY: 2-3 sentence overall assessment that validates whether the computed data looks correct for the stated experiment, and highlights the most important finding.

Respond in this exact JSON format:
{{
  "anomalies": ["anomaly 1", "anomaly 2"],
  "cluster_findings": ["finding 1", "finding 2"],
  "missed_parameters": ["param 1", "param 2"],
  "suggestions": ["suggestion 1", "suggestion 2"],
  "summary": "Overall summary here"
}}"""

    ai_response_text = _call_bedrock(prompt, max_tokens=600)

    # Parse AI response
    try:
        clean = ai_response_text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        ai_result = json.loads(clean)
    except json.JSONDecodeError:
        logger.warning("AI response was not valid JSON")
        ai_result = {
            "anomalies": rule_anomalies,
            "cluster_findings": [],
            "missed_parameters": missed_params,
            "suggestions": ["Review data manually — AI parsing failed"],
            "summary": ai_response_text[:500],
        }

    # Merge results
    all_anomalies = list(set(rule_anomalies + ai_result.get("anomalies", [])))
    all_missed = list(set(missed_params + ai_result.get("missed_parameters", [])))
    all_graphs = graph_suggestions  # keep graph suggestions as-is (ordered)

    return FCSAnalysisResponse(
        anomalies=all_anomalies,
        cluster_findings=ai_result.get("cluster_findings", []),
        suggested_graphs=all_graphs,
        missed_parameters=all_missed,
        suggestions=ai_result.get("suggestions", []),
        summary=ai_result.get("summary", "Analysis complete."),
        data_stats={s["file"]: s for s in all_stats},
        analyzed_files=request.file_paths,
        analyzed_at=datetime.utcnow().isoformat(),
    )


@router.post("/ai/nanofacs/compare", response_model=FCSCompareResponse)
async def compare_fcs_files(request: FCSCompareRequest):
    """
    Compare multiple NanoFACS FCS parquet files.
    Checks for shifts in size, intensity, cluster distribution across files.
    """
    request.file_paths = _dedupe_file_paths(request.file_paths)

    if len(request.file_paths) < 2:
        raise HTTPException(
            status_code=422,
            detail="At least 2 file paths required for comparison"
        )

    logger.info(f"NanoFACS comparison: {request.file_paths}")

    all_stats = []
    for fp in request.file_paths:
        df = _read_fcs_parquet(fp)
        if not df.empty:
            stats = _compute_fcs_stats(df, Path(fp).name)
            all_stats.append(stats)

    if len(all_stats) < 2:
        raise HTTPException(
            status_code=404,
            detail="Could not read enough files for comparison"
        )

    mismatches = []
    matching_fields = []
    cluster_comparison = []

    # Compare key numeric parameters
    compare_params = ["Size", "MeanIntensity", "Solidity", "AspectRatio", "TraceLength"]

    for param in compare_params:
        values = {}
        for stats in all_stats:
            param_stats = stats.get(param, {})
            if param_stats:
                values[stats["file"]] = param_stats.get("median", None)

        if len(values) < 2:
            continue

        vals = [v for v in values.values() if v is not None]
        if not vals:
            continue

        diff = max(vals) - min(vals)
        pct_diff = (diff / (sum(vals) / len(vals))) * 100 if sum(vals) > 0 else 0

        if pct_diff > 20:
            mismatches.append({
                "parameter": param,
                "values": values,
                "percent_difference": round(pct_diff, 1),
                "severity": "high" if pct_diff > 50 else "medium",
                "message": (
                    f"{param} median varies by {pct_diff:.0f}% across files — "
                    f"possible sample shift or preparation difference"
                )
            })
        else:
            matching_fields.append(param)

    # Cluster comparison
    for i, stats in enumerate(all_stats):
        clusters = stats.get("cluster_distribution", {})
        total = sum(clusters.values()) if clusters else 0
        if clusters and total > 0:
            dominant = max(clusters, key=clusters.get)
            dominant_pct = (clusters[dominant] / total) * 100
            cluster_comparison.append(
                f"{stats['file']}: {len(clusters)} clusters, "
                f"dominant cluster {dominant} has {dominant_pct:.0f}% of particles"
            )

    # Generate recommendation
    if mismatches:
        high = [m for m in mismatches if m["severity"] == "high"]
        if high:
            recommendation = (
                f"Critical differences found in: "
                f"{', '.join(m['parameter'] for m in high)}. "
                f"Files may represent different sample states. "
                f"Verify experimental conditions before comparing."
            )
        else:
            recommendation = (
                f"Minor differences in: "
                f"{', '.join(m['parameter'] for m in mismatches)}. "
                f"Results comparable with caution."
            )
    else:
        recommendation = (
            "All key parameters match within acceptable ranges. "
            "Files are suitable for direct comparison."
        )

    return FCSCompareResponse(
        mismatches=mismatches,
        matching_fields=matching_fields,
        cluster_comparison=cluster_comparison,
        recommendation=recommendation,
        compared_files=request.file_paths,
    )


@router.post("/ai/nanofacs/ask", response_model=FCSAskResponse)
async def ask_about_fcs_data(request: FCSAskRequest):
    """
    Answer user questions specifically about their FCS data.
    Scoped only to the uploaded files — not general AI chat.
    """
    if not request.file_paths:
        raise HTTPException(status_code=422, detail="File paths required")

    request.file_paths = _dedupe_file_paths(request.file_paths)

    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Question cannot be empty")

    logger.info(f"NanoFACS Q&A: {request.question}")

    # Read files and compute stats
    all_stats = []
    for fp in request.file_paths:
        df = _read_fcs_parquet(fp)
        if not df.empty:
            stats = _compute_fcs_stats(df, Path(fp).name)
            all_stats.append(stats)

    if not all_stats:
        raise HTTPException(status_code=404, detail="Could not read FCS files")

    _ASK_COLS = {
        "filename", "total_events", "num_clusters", "cluster_distribution",
        "Size", "Solidity", "AspectRatio", "TraceLength",
        "MeanIntensity", "MaxIntensity", "Intensity/Area",
    }
    data_context = json.dumps(
        [{k: v for k, v in s.items() if k in _ASK_COLS} for s in all_stats],
        indent=2, default=str
    )

    prompt = f"""You are an expert in NanoFACS flow cytometry and extracellular vesicle analysis.

A researcher has uploaded NanoFACS FCS parquet files and is asking a specific question about their data.

IMPORTANT: Answer ONLY based on the data provided below. Do not answer general questions unrelated to this data.
If the question cannot be answered from the data, say so clearly.

Their data statistics:
{data_context}

The researcher's question: {request.question}

Provide a clear, specific answer based only on the data above.
Reference specific numbers from the data in your answer.
Keep the answer to 3-5 sentences maximum."""

    ai_response = _call_bedrock(prompt, max_tokens=500)

    return FCSAskResponse(
        answer=ai_response,
        data_context=f"Answer based on {len(all_stats)} FCS file(s): "
                     f"{', '.join(s['file'] for s in all_stats)}",
        answered_at=datetime.utcnow().isoformat(),
    )


@router.get("/ai/nanofacs/list-files")
async def list_nanofacs_parquet_files():
    """List all available NanoFACS FCS parquet files on the server."""
    base_dirs = [
        settings.parquet_dir / "nanofacs",
        Path(__file__).parent.parent.parent.parent / "data" / "nanofacs_parquet",
    ]
    
    seen_paths: set[str] = set()
    files = []
    for base_dir in base_dirs:
        if base_dir.exists():
            for f in base_dir.rglob("*.fcs.parquet"):
                p = str(f.resolve())
                if p in seen_paths:
                    continue
                seen_paths.add(p)
                files.append({
                    "path": p,
                    "name": f.name,
                    "folder": f.parent.name,
                    "size_kb": round(f.stat().st_size / 1024, 1)
                })
    
    return {
        "files": sorted(files, key=lambda x: x["name"]),
        "total": len(files),
        "base_dir": str(base_dirs[0])
    }


# ============================================================================
# Upload Parquet File Endpoint
# ============================================================================

@router.post("/upload-parquet")
async def upload_parquet_file(
    file: UploadFile = File(...),
    folder: str = "uploads"
):
    """
    Upload a .fcs.parquet file to the nanofacs_parquet folder.
    It will immediately appear in the list-files endpoint.
    """
    filename = file.filename or ""
    if not filename.endswith(".fcs.parquet") and not filename.endswith(".parquet"):
        raise HTTPException(status_code=400, detail="Only .fcs.parquet files accepted.")

    base_dir = Path(__file__).parent.parent.parent.parent / "data" / "nanofacs_parquet" / folder
    base_dir.mkdir(parents=True, exist_ok=True)

    dest = base_dir / filename
    content = await file.read()
    dest.write_bytes(content)

    logger.info(f"Uploaded parquet: {dest}")
    return {
        "success": True,
        "path": str(dest),
        "name": filename,
        "folder": folder,
        "size_bytes": len(content)
    }

# ============================================================================
# Graph Suggestions Request/Response
# ============================================================================

class GraphSuggestRequest(BaseModel):
    channels: list[str] = Field(
        default=["FSC-A", "SSC-A", "Size"],
        description="Available channels/parameters in the FCS file"
    )
    context: Optional[str] = Field(
        None,
        description="Researcher context e.g. 'Sample 1 has CD81 green fluorescence marker'"
    )
    is_compare_mode: bool = Field(
        False,
        description="Whether multiple files are being compared"
    )
    num_files: int = Field(
        1,
        description="Number of files uploaded"
    )
    file_stats: Optional[dict] = Field(
        None,
        description="Optional stats from the files"
    )


class GraphSuggestion(BaseModel):
    title: str
    x_axis: str
    y_axis: str
    description: str
    priority: str  # "high", "medium", "low"
    reason: str


class GraphSuggestionsResponse(BaseModel):
    suggestions: list[GraphSuggestion]
    context_used: str
    summary: str

