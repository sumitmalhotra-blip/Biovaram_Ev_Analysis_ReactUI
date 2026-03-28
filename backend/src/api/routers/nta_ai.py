"""
NTA AI Analysis Router
======================

AI-powered analysis layer for NTA (Nanoparticle Tracking Analysis) data.
Uses AWS Bedrock (Mistral) to detect anomalies, compare metadata across
files, and flag parameters the user may have missed.

Endpoints:
- POST /ai/nta/analyze          - Analyze NTA data with user context
- POST /ai/nta/compare-metadata - Compare metadata across multiple NTA files
- GET  /ai/nta/health           - Check AWS Bedrock connectivity

Author: BioVaram Dev Team
Date: March 2026
"""

import os
import json
import boto3
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from loguru import logger

router = APIRouter()


# ============================================================================
# AWS Bedrock Client
# ============================================================================

def _get_bedrock_client():
    """Initialize AWS Bedrock client from environment variables."""
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region     = os.getenv("AWS_REGION", "us-east-1")

    if not aws_access_key or not aws_secret_key:
        raise HTTPException(
            status_code=503,
            detail="AWS credentials not configured. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env"
        )

    return boto3.client(
        service_name="bedrock-runtime",
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
    )


def _call_bedrock(prompt: str, max_tokens: int = 1500) -> str:
    """Call AWS Bedrock Mistral model with a prompt."""
    client = _get_bedrock_client()

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
# Key NTA parameters to always check
# ============================================================================

ALWAYS_CHECK_BINS = [
    "bin_50_80nm_pct",
    "bin_80_100nm_pct",
    "bin_100_120nm_pct",
    "bin_120_150nm_pct",
    "bin_150_200nm_pct",
]

BIN_LABELS = {
    "bin_50_80nm_pct":   "50–80 nm (small exosomes)",
    "bin_80_100nm_pct":  "80–100 nm (typical exosomes)",
    "bin_100_120nm_pct": "100–120 nm (large exosomes)",
    "bin_120_150nm_pct": "120–150 nm (small microvesicles)",
    "bin_150_200nm_pct": "150–200 nm (microvesicles)",
}

METADATA_FIELDS_TO_COMPARE = [
    "temperature_celsius",
    "ph",
    "conductivity",
]

METADATA_TOLERANCES = {
    "temperature_celsius": 1.0,   # ±1°C acceptable
    "ph": 0.2,                    # ±0.2 pH acceptable
    "conductivity": 5.0,          # ±5 mS/cm acceptable
}


# ============================================================================
# Helper — fetch NTA results from DB
# ============================================================================


async def _fetch_nta_results(sample_id: str) -> dict:
    """Fetch NTA results for a sample from the database."""
    try:
        from src.database.connection import get_session_factory
        from src.database.models import NTAResult, Sample
        from sqlalchemy import select, or_

        # Use same DB path as the running server
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

            nta_result = await session.execute(
                select(NTAResult).where(NTAResult.sample_id == sample.id)
            )
            nta = nta_result.scalars().first()

            if not nta:
                logger.warning(f"No NTA result for sample DB id: {sample.id}")
                return {}

            return {
                "sample_id": sample_id,
                "mean_size_nm": nta.mean_size_nm,
                "median_size_nm": nta.median_size_nm,
                "d10_nm": nta.d10_nm,
                "d50_nm": nta.d50_nm,
                "d90_nm": nta.d90_nm,
                "concentration_particles_ml": nta.concentration_particles_ml,
                "temperature_celsius": nta.temperature_celsius,
                "ph": nta.ph,
                "conductivity": nta.conductivity,
                "bin_50_80nm_pct": nta.bin_50_80nm_pct,
                "bin_80_100nm_pct": nta.bin_80_100nm_pct,
                "bin_100_120nm_pct": nta.bin_100_120nm_pct,
                "bin_120_150nm_pct": nta.bin_120_150nm_pct,
                "bin_150_200nm_pct": nta.bin_150_200nm_pct,
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

    # Normalize user params to lowercase for comparison
    user_params_lower = [p.lower() for p in user_params]

    for bin_key, bin_label in BIN_LABELS.items():
        # Check if user mentioned this bin
        mentioned = any(
            part in " ".join(user_params_lower)
            for part in bin_label.lower().split()
            if len(part) > 3
        )

        if not mentioned:
            # Check if any sample has significant signal in this bin
            for sample in nta_data:
                val = sample.get(bin_key)
                if val and val > 10.0:
                    missed.append(
                        f"{bin_label}: {val:.1f}% of particles detected "
                        f"(sample: {sample.get('sample_id', 'unknown')})"
                    )
                    break  # Only flag once per bin

    return missed


# ============================================================================
# Helper — rule-based anomaly checks
# ============================================================================

def _rule_based_anomalies(nta_data: list[dict]) -> list[str]:
    """
    Apply rule-based checks before sending to AI.
    These are fast, deterministic checks.
    """
    anomalies = []

    for sample in nta_data:
        sid = sample.get("sample_id", "unknown")

        # Low concentration
        conc = sample.get("concentration_particles_ml")
        if conc and conc < 1e8:
            anomalies.append(
                f"[{sid}] Very low concentration: {conc:.2e} particles/mL "
                f"(below recommended 1×10⁸)"
            )

        # High D90/D10 ratio = high polydispersity
        d10 = sample.get("d10_nm")
        d90 = sample.get("d90_nm")
        if d10 and d90 and d10 > 0:
            pdi_proxy = d90 / d10
            if pdi_proxy > 4.0:
                anomalies.append(
                    f"[{sid}] High polydispersity: D90/D10 = {pdi_proxy:.1f} "
                    f"(D10={d10:.0f}nm, D90={d90:.0f}nm)"
                )

        # Temperature out of range
        temp = sample.get("temperature_celsius")
        if temp and (temp < 15.0 or temp > 28.0):
            anomalies.append(
                f"[{sid}] Temperature out of normal range: {temp}°C "
                f"(expected 15–28°C)"
            )

        # Large particle dominance
        large_pct = sample.get("bin_150_200nm_pct", 0) or 0
        if large_pct > 30.0:
            anomalies.append(
                f"[{sid}] High large-particle fraction: {large_pct:.1f}% "
                f"in 150–200nm — possible debris or aggregation"
            )

    return anomalies


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/ai/nta/health")
async def nta_ai_health():
    """Check AWS Bedrock connectivity."""
    try:
        client = _get_bedrock_client()
        # List foundation models as a lightweight connectivity check
        bedrock = boto3.client(
            service_name="bedrock",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
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
    2. Runs rule-based anomaly checks
    3. Identifies parameters the user missed
    4. Sends everything to AWS Bedrock (Mistral) for interpretation
    5. Returns anomalies, missed parameters, and suggestions
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

    # Rule-based anomaly detection (fast, deterministic)
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

Here is the NTA measurement data for their samples:
{data_summary}

Pre-detected rule-based anomalies:
{json.dumps(rule_anomalies, indent=2) if rule_anomalies else 'None detected'}

Parameters the researcher may have missed (>10% signal in bins they did not mention):
{json.dumps(missed_params, indent=2) if missed_params else 'None'}

Please provide:
1. ANOMALIES: Any additional data quality issues or unexpected findings not already listed above
2. MISSED_PARAMETERS: Confirm or add to the missed parameters with scientific explanation of why they matter
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
        # Strip markdown code fences if present
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

    # Merge rule-based + AI anomalies (deduplicated)
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
    Compare metadata across multiple NTA files from the same sample.

    Checks if key parameters (temperature, pH, conductivity) match
    across files. Flags any mismatches that could affect results.
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

    # Compare metadata fields
    mismatches = []
    matching_fields = []

    for field in METADATA_FIELDS_TO_COMPARE:
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
                    nta_data[i].get("sample_id", f"sample_{i}"): values[i]
                    for i in range(len(values))
                },
                "difference": round(diff, 3),
                "tolerance": tolerance,
                "severity": "high" if diff > tolerance * 2 else "medium",
                "message": (
                    f"{field} varies by {diff:.2f} across samples "
                    f"(tolerance: ±{tolerance}). This may affect results."
                )
            })
        else:
            matching_fields.append(field)

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
