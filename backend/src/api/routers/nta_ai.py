"""
NTA AI Analysis Router — Updated with Full Parameter List
==========================================================

AI-powered analysis layer for NTA (Nanoparticle Tracking Analysis) data.
Uses AWS Bedrock (Mistral) to detect anomalies, compare metadata across
files, and flag parameters the user may have missed.

Updated with full parameter list from BioVaram NTA Module Documentation.

Endpoints:
- POST /ai/nta/analyze          - Analyze NTA data with user context
- POST /ai/nta/compare-metadata - Compare metadata across multiple NTA files
- GET  /ai/nta/health           - Check AWS Bedrock connectivity

Author: BioVaram Dev Team
Date: March 2026
"""

import os
import json
from pathlib import Path
import numpy as np
try:
    import boto3  # type: ignore
except ImportError:  # pragma: no cover
    boto3 = None  # type: ignore
from typing import Optional
from datetime import datetime
try:
    from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ProfileNotFound  # type: ignore
except ImportError:  # pragma: no cover
    NoCredentialsError = Exception  # type: ignore
    PartialCredentialsError = Exception  # type: ignore
    ProfileNotFound = Exception  # type: ignore
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from loguru import logger
from src.api.aws_utils import get_bedrock_runtime_client
from src.api.ai_gateway_client import AIGatewayError, gateway_complete, gateway_health
router = APIRouter()


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
    """Initialize AWS Bedrock client using AWS default credential chain."""
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


def _ai_provider() -> str:
    return (os.getenv("AI_PROVIDER") or "bedrock").strip().lower()


def _call_bedrock(prompt: str, max_tokens: int = 1500) -> str:
    """Call the configured AI provider with a prompt (Bedrock or hosted gateway)."""
    provider = _ai_provider()

    def _gateway_fallback() -> str:
        if "exact JSON format" in prompt:
            return json.dumps(
                {
                    "anomalies": [],
                    "missed_parameters": [],
                    "suggestions": [
                        "Gateway unavailable; using local rule-based NTA analysis fallback.",
                        "Verify CRMIT_AI_GATEWAY_URL and CRMIT_AI_GATEWAY_LICENSE_KEY on the packaged desktop build.",
                    ],
                    "summary": "Gateway request failed, so the app fell back to local NTA analysis without cloud interpretation.",
                }
            )
        return (
            "Gateway request failed, so the app fell back to local NTA analysis without cloud interpretation. "
            "Verify CRMIT_AI_GATEWAY_URL and CRMIT_AI_GATEWAY_LICENSE_KEY on the packaged desktop build."
        )

    if provider == "gateway":
        model = (os.getenv("CRMIT_AI_MODEL") or "amazon.nova-lite-v1:0").strip() or "amazon.nova-lite-v1:0"
        try:
            return gateway_complete(prompt=prompt, model=model, temperature=0.3, max_tokens=max_tokens)
        except AIGatewayError as exc:
            logger.warning(f"Gateway request failed for NTA analysis: {exc}")
            return _gateway_fallback()

    client = _get_bedrock_client()
    if client is None:
        if "exact JSON format" in prompt:
            return json.dumps(
                {
                    "anomalies": ["Offline AI mode enabled: cloud model call skipped for local testing."],
                    "missed_parameters": [],
                    "suggestions": [
                        "Configure AWS credentials before release for full AI interpretation.",
                        "Use rule-based findings to validate the local UI workflow."
                    ],
                    "summary": "Local offline AI mode returned deterministic guidance without Bedrock access."
                }
            )
        return (
            "Offline AI mode is active for local testing, so this answer is based on local rule-based analysis only. "
            "Configure AWS credentials to enable full Bedrock reasoning before release."
        )

    payload = {
        "prompt": f"<s>[INST] {prompt} [/INST]",
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }

    try:
        response = client.invoke_model(
            modelId="mistral.mistral-large-2402-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )
        result = json.loads(response["body"].read())
        return result["outputs"][0]["text"].strip()
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
        raise HTTPException(
            status_code=500,
            detail=f"AI model call failed: {str(e)}"
        )


# ============================================================================
# Request / Response Models
# ============================================================================

class NTAUserContext(BaseModel):
    """Context provided by the user about their experiment."""
    experiment_description: str = Field(
        ...,
        description="What the user is analyzing (e.g. 'CD81 marker on exosomes from plasma')"
    )
    same_sample: bool = Field(
        True,
        description="Whether all uploaded files come from the same sample"
    )
    parameters_of_interest: list[str] = Field(
        default=[],
        description="Size bins or parameters the user is specifically looking at (e.g. ['50-80nm', '80-100nm'])"
    )
    sample_ids: list[str] = Field(
        ...,
        description="List of NTA sample IDs to analyze"
    )
    additional_notes: Optional[str] = Field(
        None,
        description="Any additional context the user wants to provide"
    )


class MetadataCompareRequest(BaseModel):
    """Request to compare metadata across multiple NTA files."""
    sample_ids: list[str] = Field(
        ...,
        description="List of sample IDs to compare (minimum 2)"
    )


class AIAnalysisResponse(BaseModel):
    """Response from the AI analysis."""
    anomalies: list[str]
    missed_parameters: list[str]
    suggestions: list[str]
    summary: str
    analyzed_samples: list[str]
    analyzed_at: str


class MetadataCompareResponse(BaseModel):
    """Response from metadata comparison."""
    mismatches: list[dict]
    matching_fields: list[str]
    recommendation: str
    compared_samples: list[str]


# ============================================================================
# FULL Parameter List (from BioVaram NTA Module Documentation)
# ============================================================================

# Size bins — always check all of these
BIN_LABELS = {
    "bin_50_80nm_pct":   "50–80 nm (small exosomes)",
    "bin_80_100nm_pct":  "80–100 nm (typical exosomes)",
    "bin_100_120nm_pct": "100–120 nm (large exosomes)",
    "bin_120_150nm_pct": "120–150 nm (small microvesicles)",
    "bin_150_200nm_pct": "150–200 nm (microvesicles)",
}

# NTA result parameters — all used in AI analysis
NTA_RESULT_PARAMS = [
    "mean_size_nm",
    "median_size_nm",
    "mode_size_nm",
    "d10_nm",
    "d50_nm",
    "d90_nm",
    "std_dev_nm",
    "concentration_particles_ml",
    "bin_50_80nm_pct",
    "bin_80_100nm_pct",
    "bin_100_120nm_pct",
    "bin_120_150nm_pct",
    "bin_150_200nm_pct",
]

# Metadata fields to compare across files — EXPANDED full list
METADATA_FIELDS_TO_COMPARE = [
    "temperature_celsius",
    "ph",
    "conductivity",
    "viscosity",
    "laser_wavelength_nm",
    "dilution_factor",
    "operator",
    "instrument",
    "sensitivity",
    "shutter",
    "positions",
    "number_of_traces",
]

# Tolerances for numeric metadata fields
# String fields (operator, instrument) use exact match
METADATA_TOLERANCES = {
    "temperature_celsius": 1.0,     # ±1°C acceptable
    "ph":                  0.2,     # ±0.2 pH acceptable
    "conductivity":        5.0,     # ±5 mS/cm acceptable
    "viscosity":           0.05,    # ±0.05 mPa·s acceptable
    "laser_wavelength_nm": 0.0,     # must be identical
    "dilution_factor":     0.0,     # must be identical
    "sensitivity":         2.0,     # ±2 units acceptable
    "shutter":             1.0,     # ±1 unit acceptable
    "positions":           0.0,     # must be identical
    "number_of_traces":    0.0,     # must be identical
}

# String fields — must match exactly
METADATA_STRING_FIELDS = ["operator", "instrument"]


# ============================================================================
# Helper — fetch NTA results from DB
# ============================================================================

async def _fetch_nta_results(sample_id: str) -> dict:
    """Fetch NTA results for a sample from the database."""
    try:
        from src.database.connection import get_session_factory
        from src.database.models import NTAResult, Sample
        from sqlalchemy import select, or_

        from src.parsers.nta_parser import NTAParser

        import os
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))

        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(Sample).where(
                    or_(
                        Sample.sample_id == sample_id,
                        Sample.biological_sample_id == sample_id,
                    )
                )
            )
            sample = result.scalar_one_or_none()

            if not sample:
                logger.warning(f"Sample not found: {sample_id}")
                return {}

            # IMPORTANT: Do not select the full ORM entity here.
            # The deployed DB schema (especially SQLite) may lag behind the SQLAlchemy model.
            # Selecting `NTAResult` would request columns that don't exist and crash.
            nta_row = (
                await session.execute(
                    select(
                        NTAResult.mean_size_nm,
                        NTAResult.median_size_nm,
                        NTAResult.mode_size_nm,
                        NTAResult.d10_nm,
                        NTAResult.d50_nm,
                        NTAResult.d90_nm,
                        NTAResult.std_dev_nm,
                        NTAResult.concentration_particles_ml,
                        NTAResult.bin_50_80nm_pct,
                        NTAResult.bin_80_100nm_pct,
                        NTAResult.bin_100_120nm_pct,
                        NTAResult.bin_120_150nm_pct,
                        NTAResult.bin_150_200nm_pct,
                        NTAResult.temperature_celsius,
                        NTAResult.ph,
                        NTAResult.conductivity,
                        NTAResult.parquet_file_path,
                        NTAResult.measurement_date,
                    ).where(NTAResult.sample_id == sample.id)
                )
            ).first()

            def _resolve_existing_file_path(raw_path: str) -> Path:
                candidate = Path(raw_path)
                if candidate.exists():
                    return candidate

                if not candidate.is_absolute():
                    cwd_candidate = Path.cwd() / candidate
                    if cwd_candidate.exists():
                        return cwd_candidate

                raise FileNotFoundError(f"Sample NTA file not found: {raw_path}")

            def _calculate_nta_results_from_parsed_df(parsed_data) -> dict:
                size_col = None
                count_col = None
                conc_col = None

                for col in parsed_data.columns:
                    col_lower = col.lower()
                    if size_col is None and (col_lower == "size_nm" or ("size" in col_lower and "nm" in col_lower)):
                        size_col = col
                    if count_col is None and (col_lower == "particle_count" or "particle_count" in col_lower):
                        count_col = col
                    if conc_col is None and (col_lower == "concentration_particles_ml" or ("concentration" in col_lower and "particles" in col_lower)):
                        conc_col = col

                if not size_col:
                    raise ValueError("Could not find a size column in NTA parsed data")

                sizes = np.asarray(parsed_data[size_col].values, dtype=np.float64)
                if count_col and count_col in parsed_data.columns:
                    counts = np.asarray(parsed_data[count_col].values, dtype=np.float64)
                else:
                    counts = np.ones_like(sizes)

                valid_mask = np.isfinite(sizes) & np.isfinite(counts) & (counts > 0)
                sizes_valid = np.asarray(sizes[valid_mask], dtype=np.float64)
                counts_valid = np.asarray(counts[valid_mask], dtype=np.float64)

                if len(sizes_valid) == 0 or float(np.sum(counts_valid)) <= 0:
                    raise ValueError("NTA parsed data has no valid size bins")

                sort_idx = np.argsort(sizes_valid)
                sizes_sorted = sizes_valid[sort_idx]
                counts_sorted = counts_valid[sort_idx]
                cumsum = np.cumsum(counts_sorted)
                total_particles = float(cumsum[-1])

                d10 = float(sizes_sorted[min(np.searchsorted(cumsum, total_particles * 0.1), len(sizes_sorted) - 1)])
                d50 = float(sizes_sorted[min(np.searchsorted(cumsum, total_particles * 0.5), len(sizes_sorted) - 1)])
                d90 = float(sizes_sorted[min(np.searchsorted(cumsum, total_particles * 0.9), len(sizes_sorted) - 1)])
                mean_size = float(np.average(sizes_valid, weights=counts_valid))
                weighted_var = float(np.average((sizes_valid - mean_size) ** 2, weights=counts_valid))
                weighted_std = float(np.sqrt(weighted_var))

                total_concentration = None
                if conc_col and conc_col in parsed_data.columns:
                    conc_values = parsed_data[conc_col].dropna()
                    if len(conc_values) > 0:
                        total_concentration = float(conc_values.sum())

                bin_30_50 = float(np.sum(counts_valid[(sizes_valid >= 30) & (sizes_valid < 50)])) / total_particles * 100
                bin_50_80 = float(np.sum(counts_valid[(sizes_valid >= 50) & (sizes_valid < 80)])) / total_particles * 100
                bin_80_100 = float(np.sum(counts_valid[(sizes_valid >= 80) & (sizes_valid < 100)])) / total_particles * 100
                bin_100_120 = float(np.sum(counts_valid[(sizes_valid >= 100) & (sizes_valid < 120)])) / total_particles * 100
                bin_120_150 = float(np.sum(counts_valid[(sizes_valid >= 120) & (sizes_valid < 150)])) / total_particles * 100
                bin_150_200 = float(np.sum(counts_valid[(sizes_valid >= 150) & (sizes_valid < 200)])) / total_particles * 100

                return {
                    "mean_size_nm": mean_size,
                    "median_size_nm": d50,
                    "d10_nm": d10,
                    "d50_nm": d50,
                    "d90_nm": d90,
                    "std_dev_nm": weighted_std,
                    "concentration_particles_ml": total_concentration,
                    "total_particles": int(total_particles),
                    "bin_30_50nm_pct": bin_30_50,
                    "bin_50_80nm_pct": bin_50_80,
                    "bin_80_100nm_pct": bin_80_100,
                    "bin_100_120nm_pct": bin_100_120,
                    "bin_120_150nm_pct": bin_120_150,
                    "bin_150_200nm_pct": bin_150_200,
                }

            def _parse_measurement_datetime(raw_metadata: dict) -> Optional[datetime]:
                date_str = raw_metadata.get("date")
                time_str = raw_metadata.get("time")
                if not date_str:
                    return None
                candidate = date_str.strip() + (f" {time_str.strip()}" if time_str else "")
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                    try:
                        return datetime.strptime(candidate, fmt)
                    except Exception:
                        continue
                return None

            parsed_metadata: dict = {}
            parsed_measurement_params: dict = {}

            if nta_row and getattr(sample, "file_path_nta", None):
                try:
                    nta_file_path = _resolve_existing_file_path(str(getattr(sample, "file_path_nta")))
                    parser = NTAParser(nta_file_path)
                    if not parser.validate():
                        logger.warning(f"NTA validation failed for '{sample_id}' ({nta_file_path})")
                    _ = parser.parse()
                    parsed_metadata = getattr(parser, "raw_metadata", {}) or {}
                    parsed_measurement_params = getattr(parser, "measurement_params", {}) or {}
                except Exception as meta_err:
                    logger.warning(f"Failed to parse NTA metadata for '{sample_id}': {type(meta_err).__name__}: {meta_err}")

            if not nta_row:
                logger.warning(f"No NTA result for sample DB id: {sample.id}; attempting on-demand parse/backfill")

                raw_path = getattr(sample, "file_path_nta", None)
                if not raw_path:
                    return {}

                try:
                    nta_file_path = _resolve_existing_file_path(str(raw_path))
                except Exception as file_err:
                    logger.warning(f"NTA file path could not be resolved for '{sample_id}': {file_err}")
                    return {}

                try:
                    parser = NTAParser(nta_file_path)
                    if not parser.validate():
                        logger.warning(f"NTA validation failed for '{sample_id}' ({nta_file_path})")

                    parsed_df = parser.parse()
                    computed = _calculate_nta_results_from_parsed_df(parsed_df)

                    temperature = parser.measurement_params.get("temperature")
                    measurement_date = _parse_measurement_datetime(getattr(parser, "raw_metadata", {}) or {})

                    # NOTE: We intentionally do NOT write back to the DB here.
                    # In some environments, the SQLite schema may lag behind the SQLAlchemy model,
                    # and ORM INSERTs will reference columns that don't exist. Parsing-on-demand
                    # ensures NTA AI works even when migrations haven't been applied.
                except Exception as parse_err:
                    logger.warning(f"On-demand NTA parse/backfill failed for '{sample_id}': {type(parse_err).__name__}: {parse_err}")
                    return {}

                # Return computed + parsed metadata (even if DB backfill was skipped)
                return {
                    "sample_id": sample_id,

                    "mean_size_nm": computed.get("mean_size_nm"),
                    "median_size_nm": computed.get("median_size_nm"),
                    "mode_size_nm": None,
                    "d10_nm": computed.get("d10_nm"),
                    "d50_nm": computed.get("d50_nm"),
                    "d90_nm": computed.get("d90_nm"),
                    "std_dev_nm": computed.get("std_dev_nm"),
                    "concentration_particles_ml": computed.get("concentration_particles_ml"),

                    "bin_50_80nm_pct": computed.get("bin_50_80nm_pct"),
                    "bin_80_100nm_pct": computed.get("bin_80_100nm_pct"),
                    "bin_100_120nm_pct": computed.get("bin_100_120nm_pct"),
                    "bin_120_150nm_pct": computed.get("bin_120_150nm_pct"),
                    "bin_150_200nm_pct": computed.get("bin_150_200nm_pct"),

                    "temperature_celsius": float(parser.measurement_params.get("temperature")) if parser.measurement_params.get("temperature") is not None else None,
                    "ph": float(parser.measurement_params.get("ph")) if parser.measurement_params.get("ph") is not None else None,
                    "conductivity": float(parser.measurement_params.get("conductivity")) if parser.measurement_params.get("conductivity") is not None else None,
                    "viscosity": float(parser.measurement_params.get("viscosity")) if parser.measurement_params.get("viscosity") is not None else None,
                    "laser_wavelength_nm": float(parser.measurement_params.get("laser_wavelength")) if parser.measurement_params.get("laser_wavelength") is not None else None,
                    "dilution_factor": float(parser.measurement_params.get("dilution")) if parser.measurement_params.get("dilution") is not None else None,
                    "operator": getattr(sample, "operator", None) or (getattr(parser, "raw_metadata", {}) or {}).get("operator"),
                    "instrument": (getattr(parser, "raw_metadata", {}) or {}).get("instrument_serial"),
                    "sensitivity": float(parser.measurement_params.get("sensitivity")) if parser.measurement_params.get("sensitivity") is not None else None,
                    "shutter": float(parser.measurement_params.get("shutter")) if parser.measurement_params.get("shutter") is not None else None,
                    "positions": int(parser.measurement_params.get("num_positions")) if parser.measurement_params.get("num_positions") is not None else None,
                    "number_of_traces": int(parser.measurement_params.get("num_traces")) if parser.measurement_params.get("num_traces") is not None else None,
                }

            (
                mean_size_nm,
                median_size_nm,
                mode_size_nm,
                d10_nm,
                d50_nm,
                d90_nm,
                std_dev_nm,
                concentration_particles_ml,
                bin_50_80nm_pct,
                bin_80_100nm_pct,
                bin_100_120nm_pct,
                bin_120_150nm_pct,
                bin_150_200nm_pct,
                temperature_celsius,
                ph,
                conductivity,
                parquet_file_path,
                measurement_date,
            ) = nta_row

            return {
                "sample_id": sample_id,

                "mean_size_nm": mean_size_nm,
                "median_size_nm": median_size_nm,
                "mode_size_nm": mode_size_nm,
                "d10_nm": d10_nm,
                "d50_nm": d50_nm,
                "d90_nm": d90_nm,
                "std_dev_nm": std_dev_nm,
                "concentration_particles_ml": concentration_particles_ml,

                "bin_50_80nm_pct": bin_50_80nm_pct,
                "bin_80_100nm_pct": bin_80_100nm_pct,
                "bin_100_120nm_pct": bin_100_120nm_pct,
                "bin_120_150nm_pct": bin_120_150nm_pct,
                "bin_150_200nm_pct": bin_150_200nm_pct,

                "temperature_celsius": temperature_celsius,
                "ph": ph,
                "conductivity": conductivity,
                "viscosity": float(parsed_measurement_params.get("viscosity")) if parsed_measurement_params.get("viscosity") is not None else None,
                "laser_wavelength_nm": float(parsed_measurement_params.get("laser_wavelength")) if parsed_measurement_params.get("laser_wavelength") is not None else None,
                "dilution_factor": float(parsed_measurement_params.get("dilution")) if parsed_measurement_params.get("dilution") is not None else None,
                "operator": getattr(sample, "operator", None) or parsed_metadata.get("operator"),
                "instrument": parsed_metadata.get("instrument_serial"),
                "sensitivity": float(parsed_measurement_params.get("sensitivity")) if parsed_measurement_params.get("sensitivity") is not None else None,
                "shutter": float(parsed_measurement_params.get("shutter")) if parsed_measurement_params.get("shutter") is not None else None,
                "positions": int(parsed_measurement_params.get("num_positions")) if parsed_measurement_params.get("num_positions") is not None else None,
                "number_of_traces": int(parsed_measurement_params.get("num_traces")) if parsed_measurement_params.get("num_traces") is not None else None,
                "parquet_file_path": parquet_file_path,
                "measurement_date": measurement_date,
            }

    except Exception as e:
        logger.error(f"Failed to fetch NTA results for {sample_id}: {e}")
        return {}


# ============================================================================
# Helper — detect missed parameters
# ============================================================================

def _find_missed_parameters(
    nta_data: list[dict],
    user_params: list[str]
) -> list[str]:
    """
    Check which size bins the user did NOT mention but have significant signal.
    Threshold: >10% of particles in a bin = significant.
    """
    missed = []
    user_params_lower = [p.lower() for p in user_params]

    for bin_key, bin_label in BIN_LABELS.items():
        mentioned = any(
            part in " ".join(user_params_lower)
            for part in bin_label.lower().split()
            if len(part) > 3
        )

        if not mentioned:
            for sample in nta_data:
                val = sample.get(bin_key)
                if val and val > 10.0:
                    missed.append(
                        f"{bin_label}: {val:.1f}% of particles detected "
                        f"(sample: {sample.get('sample_id', 'unknown')})"
                    )
                    break

    return missed


# ============================================================================
# Helper — rule-based anomaly checks (expanded)
# ============================================================================

def _rule_based_anomalies(nta_data: list[dict]) -> list[str]:
    """
    Apply rule-based checks before sending to AI.
    Expanded to cover all NTA result parameters.
    """
    anomalies = []

    for sample in nta_data:
        sid = sample.get("sample_id", "unknown")

        # 1. Low concentration
        conc = sample.get("concentration_particles_ml")
        if conc and conc < 1e8:
            anomalies.append(
                f"[{sid}] Very low concentration: {conc:.2e} particles/mL "
                f"(below recommended 1×10⁸)"
            )

        # 2. High polydispersity (D90/D10 ratio)
        d10 = sample.get("d10_nm")
        d90 = sample.get("d90_nm")
        if d10 and d90 and d10 > 0:
            pdi_proxy = d90 / d10
            if pdi_proxy > 4.0:
                anomalies.append(
                    f"[{sid}] High polydispersity: D90/D10 = {pdi_proxy:.1f} "
                    f"(D10={d10:.0f}nm, D90={d90:.0f}nm) — possible debris or aggregation"
                )

        # 3. Temperature out of range
        temp = sample.get("temperature_celsius")
        if temp and (temp < 15.0 or temp > 28.0):
            anomalies.append(
                f"[{sid}] Temperature out of normal range: {temp}°C "
                f"(expected 15–28°C) — Stokes-Einstein correction may be needed"
            )

        # 4. Large particle dominance
        large_pct = sample.get("bin_150_200nm_pct", 0) or 0
        if large_pct > 30.0:
            anomalies.append(
                f"[{sid}] High large-particle fraction: {large_pct:.1f}% "
                f"in 150–200nm — possible microvesicle contamination or aggregation"
            )

        # 5. Mean size outside typical exosome range
        mean_size = sample.get("mean_size_nm")
        if mean_size and mean_size > 200:
            anomalies.append(
                f"[{sid}] Mean size {mean_size:.0f}nm is above typical exosome range "
                f"(30–200nm) — sample may contain large microvesicles or debris"
            )

        # 6. D50 vs mean size discrepancy (skewed distribution)
        median_size = sample.get("median_size_nm") or sample.get("d50_nm")
        if mean_size and median_size and abs(mean_size - median_size) > 50:
            anomalies.append(
                f"[{sid}] Large mean-median discrepancy: mean={mean_size:.0f}nm, "
                f"median={median_size:.0f}nm — distribution is heavily skewed"
            )

        # 7. Very high std deviation
        std = sample.get("std_dev_nm")
        if std and mean_size and std > mean_size:
            anomalies.append(
                f"[{sid}] Standard deviation ({std:.0f}nm) exceeds mean size "
                f"({mean_size:.0f}nm) — extremely broad distribution"
            )

        # 8. Unusual pH
        ph = sample.get("ph")
        if ph and (ph < 6.5 or ph > 8.0):
            anomalies.append(
                f"[{sid}] pH {ph} is outside physiological range (6.5–8.0) "
                f"— may affect EV stability"
            )

        # 9. Unusual viscosity
        viscosity = sample.get("viscosity")
        if viscosity and (viscosity < 0.7 or viscosity > 1.5):
            anomalies.append(
                f"[{sid}] Viscosity {viscosity:.3f} mPa·s is outside normal water range "
                f"(0.7–1.5) — check media type and temperature correction"
            )

    return anomalies


# ============================================================================
# Helper — compare metadata (expanded to all fields)
# ============================================================================

def _compare_metadata_fields(nta_data: list[dict]) -> tuple[list[dict], list[str]]:
    """
    Compare all metadata fields across samples.
    Returns (mismatches, matching_fields).
    """
    mismatches = []
    matching_fields = []

    # Numeric fields
    for field in METADATA_FIELDS_TO_COMPARE:
        if field in METADATA_STRING_FIELDS:
            continue  # handled separately below

        values = [s.get(field) for s in nta_data if s.get(field) is not None]
        if len(values) < 2:
            continue

        tolerance = METADATA_TOLERANCES.get(field, 0)
        min_val = min(values)
        max_val = max(values)
        diff = max_val - min_val

        if diff > tolerance:
            mismatches.append({
                "field": field,
                "values": {
                    nta_data[i].get("sample_id", f"sample_{i}"): nta_data[i].get(field)
                    for i in range(len(nta_data))
                    if nta_data[i].get(field) is not None
                },
                "difference": round(diff, 4),
                "tolerance": tolerance,
                "severity": "high" if diff > tolerance * 2 else "medium",
                "message": (
                    f"{field} varies by {diff:.3f} across samples "
                    f"(tolerance: ±{tolerance}). This may affect comparability."
                )
            })
        else:
            matching_fields.append(field)

    # String fields — exact match required
    for field in METADATA_STRING_FIELDS:
        values = [s.get(field) for s in nta_data if s.get(field) is not None]
        if len(values) < 2:
            continue

        unique_vals = set(values)
        if len(unique_vals) > 1:
            mismatches.append({
                "field": field,
                "values": {
                    nta_data[i].get("sample_id", f"sample_{i}"): nta_data[i].get(field)
                    for i in range(len(nta_data))
                    if nta_data[i].get(field) is not None
                },
                "difference": "values differ",
                "tolerance": "must match exactly",
                "severity": "medium",
                "message": (
                    f"{field} differs across samples: {unique_vals}. "
                    f"Verify this is intentional."
                )
            })
        else:
            matching_fields.append(field)

    return mismatches, matching_fields


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/ai/nta/health")
async def nta_ai_health():
    """Check AWS Bedrock connectivity."""
    try:
        if _ai_provider() == "gateway":
            health = gateway_health()
            return {
                "status": health.get("status", "error"),
                "provider": "gateway",
                "model": os.getenv("CRMIT_AI_MODEL", "amazon.nova-lite-v1:0"),
                "message": health.get("message"),
                "gateway": {
                    "url": os.getenv("CRMIT_AI_GATEWAY_URL", ""),
                },
            }

        client = _get_bedrock_client()
        if client is None:
            return {
                "status": "ok",
                "provider": "offline_local",
                "model": "offline-local",
                "region": os.getenv("AWS_REGION", "us-east-1"),
                "message": "Offline AI fallback enabled for local testing",
            }
        return {
            "status": "ok",
            "provider": "aws_bedrock",
            "model": "mistral.mistral-large-2402-v1:0",
            "region": os.getenv("AWS_REGION", "us-east-1"),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


@router.post("/ai/nta/analyze", response_model=AIAnalysisResponse)
async def analyze_nta_with_ai(context: NTAUserContext):
    """
    AI-powered NTA analysis.

    1. Fetches NTA results for all provided sample IDs
    2. Runs expanded rule-based anomaly checks (9 checks)
    3. Identifies parameters the user missed across all 5 size bins
    4. Sends everything to AWS Bedrock (Mistral) for interpretation
    5. Returns anomalies, missed parameters, suggestions and summary
    """
    if not context.sample_ids:
        raise HTTPException(status_code=422, detail="At least one sample_id is required")

    logger.info(f"AI NTA analysis requested for samples: {context.sample_ids}")

    # Fetch data for all samples
    nta_data = []
    for sample_id in context.sample_ids:
        data = await _fetch_nta_results(sample_id)
        if data:
            nta_data.append(data)
        else:
            logger.warning(f"No NTA data found for sample: {sample_id}")

    if not nta_data:
        raise HTTPException(
            status_code=404,
            detail="No NTA data found for the provided sample IDs. Please upload NTA files first."
        )

    # Rule-based anomaly detection
    rule_anomalies = _rule_based_anomalies(nta_data)

    # Find missed parameters
    missed_params = _find_missed_parameters(nta_data, context.parameters_of_interest)

    # Build prompt for Bedrock
    data_summary = json.dumps(nta_data, indent=2, default=str)

    prompt = f"""You are an expert in Nanoparticle Tracking Analysis (NTA) and extracellular vesicle (EV) characterization.

A researcher is analyzing NTA data with the following context:
- Experiment: {context.experiment_description}
- Same sample split into multiple runs: {context.same_sample}
- Parameters they are focusing on: {context.parameters_of_interest or 'Not specified'}
- Additional notes: {context.additional_notes or 'None'}

Here is the complete NTA measurement data including all parameters:
{data_summary}

Parameters tracked:
- Size statistics: mean_size_nm, median_size_nm, mode_size_nm, d10_nm, d50_nm, d90_nm, std_dev_nm
- Concentration: concentration_particles_ml
- Size bins: bin_50_80nm_pct, bin_80_100nm_pct, bin_100_120nm_pct, bin_120_150nm_pct, bin_150_200nm_pct
- Metadata: temperature_celsius, ph, conductivity, viscosity, laser_wavelength_nm, dilution_factor, operator, instrument, sensitivity, shutter, positions, number_of_traces

Pre-detected rule-based anomalies:
{json.dumps(rule_anomalies, indent=2) if rule_anomalies else 'None detected'}

Parameters the researcher may have missed (>10% signal in bins they did not mention):
{json.dumps(missed_params, indent=2) if missed_params else 'None'}

Please provide:
1. ANOMALIES: Any additional data quality issues or unexpected findings not already listed above
2. MISSED_PARAMETERS: Confirm or add to the missed parameters with scientific explanation
3. SUGGESTIONS: Specific actionable recommendations for the researcher
4. SUMMARY: A 2-3 sentence overall assessment of the data quality and key findings

Respond in this exact JSON format:
{{
  "anomalies": ["anomaly 1", "anomaly 2"],
  "missed_parameters": ["missed param 1", "missed param 2"],
  "suggestions": ["suggestion 1", "suggestion 2"],
  "summary": "Overall summary here"
}}"""

    # Call Bedrock
    ai_response_text = _call_bedrock(prompt)

    # Parse AI response
    try:
        clean = ai_response_text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        ai_result = json.loads(clean)
    except json.JSONDecodeError:
        logger.warning("AI response was not valid JSON, using raw text")
        ai_result = {
            "anomalies": rule_anomalies,
            "missed_parameters": missed_params,
            "suggestions": ["Please review the data manually — AI parsing failed"],
            "summary": ai_response_text[:500],
        }

    # Merge rule-based + AI results
    all_anomalies = list(set(rule_anomalies + ai_result.get("anomalies", [])))
    all_missed = list(set(missed_params + ai_result.get("missed_parameters", [])))

    return AIAnalysisResponse(
        anomalies=all_anomalies,
        missed_parameters=all_missed,
        suggestions=ai_result.get("suggestions", []),
        summary=ai_result.get("summary", "Analysis complete."),
        analyzed_samples=context.sample_ids,
        analyzed_at=datetime.utcnow().isoformat(),
    )


@router.post("/ai/nta/compare-metadata", response_model=MetadataCompareResponse)
async def compare_nta_metadata(request: MetadataCompareRequest):
    """
    Compare ALL metadata fields across multiple NTA files.

    Expanded from 3 fields (temp, pH, conductivity) to full 12-field list:
    temperature, pH, conductivity, viscosity, laser wavelength, dilution factor,
    operator, instrument, sensitivity, shutter, positions, number of traces.
    """
    if len(request.sample_ids) < 2:
        raise HTTPException(
            status_code=422,
            detail="At least 2 sample IDs are required for comparison"
        )

    logger.info(f"Metadata comparison for: {request.sample_ids}")

    # Fetch all samples
    nta_data = []
    for sample_id in request.sample_ids:
        data = await _fetch_nta_results(sample_id)
        if data:
            nta_data.append(data)

    if len(nta_data) < 2:
        raise HTTPException(
            status_code=404,
            detail="Could not find NTA data for enough samples to compare"
        )

    # Compare all metadata fields
    mismatches, matching_fields = _compare_metadata_fields(nta_data)

    # Generate recommendation
    if mismatches:
        high_severity = [m for m in mismatches if m["severity"] == "high"]
        if high_severity:
            recommendation = (
                f"⚠️ Critical mismatches found in: "
                f"{', '.join(m['field'] for m in high_severity)}. "
                f"These files may not be directly comparable. "
                f"Consider re-running measurements under consistent conditions."
            )
        else:
            recommendation = (
                f"Minor mismatches detected in: "
                f"{', '.join(m['field'] for m in mismatches)}. "
                f"Results should be interpreted with caution."
            )
    else:
        recommendation = (
            "✅ All metadata parameters match within acceptable tolerances. "
            "Files are suitable for direct comparison."
        )

    return MetadataCompareResponse(
        mismatches=mismatches,
        matching_fields=matching_fields,
        recommendation=recommendation,
        compared_samples=request.sample_ids,
    )
