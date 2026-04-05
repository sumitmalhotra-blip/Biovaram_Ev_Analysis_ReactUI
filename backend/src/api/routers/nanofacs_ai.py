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
import boto3
import numpy as np
import pandas as pd
from typing import Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from loguru import logger

router = APIRouter()


# ============================================================================
# AWS Bedrock Client
# ============================================================================

def _get_bedrock_client():
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region     = os.getenv("AWS_REGION", "us-east-1")

    if not aws_access_key or not aws_secret_key:
        raise HTTPException(
            status_code=503,
            detail="AWS credentials not configured."
        )

    return boto3.client(
        service_name="bedrock-runtime",
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
    )


def _call_bedrock(prompt: str, max_tokens: int = 1500) -> str:
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


# ============================================================================
# Helper — compute per-file statistics
# ============================================================================

def _compute_fcs_stats(df: pd.DataFrame, file_name: str) -> dict:
    """Compute key statistics from FCS DataFrame."""
    if df.empty:
        return {}

    stats = {"file": file_name, "total_events": len(df)}

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
        "Size Distribution Histogram — plot Size on X axis, event count on Y axis "
        "to see the full particle size distribution"
    )
    suggestions.append(
        "Size vs MeanIntensity Scatter Plot — identifies if larger particles "
        "have higher fluorescence (possible debris) or uniform intensity (EVs)"
    )
    suggestions.append(
        "Cluster Map (LocationX vs LocationY colored by Cluster) — visualize "
        "spatial distribution of particle clusters in the measurement cell"
    )

    # Check for multiple clusters
    for stats in stats_list:
        num_clusters = stats.get("num_clusters", 0)
        if num_clusters > 3:
            suggestions.append(
                f"Cluster Size Distribution — compare Size distributions across "
                f"{num_clusters} clusters to identify if clusters represent "
                f"different EV subpopulations"
            )
            break

    # Check for high intensity variation
    for stats in stats_list:
        intensity = stats.get("MeanIntensity", {})
        if intensity and intensity.get("std", 0) > intensity.get("mean", 1) * 0.5:
            suggestions.append(
                "Intensity/Area vs Size Scatter — high intensity variation detected, "
                "plot to identify bright outliers that may be debris or aggregates"
            )
            break

    # Check for position variation
    for stats in stats_list:
        pos_dist = stats.get("position_distribution", {})
        if pos_dist and len(pos_dist) > 1:
            suggestions.append(
                "Position vs Event Count Bar Chart — check uniformity across "
                "measurement positions to validate sample homogeneity"
            )
            break

    # If user mentioned specific params
    for param in user_params:
        param_lower = param.lower()
        if "velocity" in param_lower or "v_nm" in param_lower:
            suggestions.append(
                "Velocity (V_nmsec-1) vs Size Scatter — compare measured velocity "
                "with Stokes-Einstein predicted velocity to validate size measurements"
            )
        if "intensity" in param_lower:
            suggestions.append(
                "MaxIntensity vs MinIntensity Scatter — identify particles with "
                "high dynamic range which may indicate non-uniform labeling"
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
        _get_bedrock_client()
        return {
            "status": "ok",
            "provider": "aws_bedrock",
            "model": "mistral.mistral-large-2402-v1:0",
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

    # Build prompt for Bedrock
    stats_summary = json.dumps(all_stats, indent=2, default=str)

    prompt = f"""You are an expert in NanoFACS (Nano Flow Cytometry) and extracellular vesicle (EV) characterization.

A researcher is analyzing NanoFACS FCS data with the following context:
- Experiment: {request.experiment_description}
- Same biological sample across files: {request.same_sample}
- Parameters they are focusing on: {request.parameters_of_interest or 'Not specified'}
- Additional notes: {request.additional_notes or 'None'}

Here are the computed statistics from their FCS parquet files:
{stats_summary}

Available parameters per particle: TrackID, Frame, LocationX, LocationY, Area, Perimeter,
Solidity, AspectRatio, MeanIntensity, MaxIntensity, MinIntensity, ConvexArea,
Intensity/Area, TraceLength, Size, V_nmsec-1, Cluster

Pre-detected rule-based anomalies:
{json.dumps(rule_anomalies, indent=2) if rule_anomalies else 'None detected'}

Parameters the researcher may have missed (high variability detected):
{json.dumps(missed_params, indent=2) if missed_params else 'None'}

Please provide:
1. ANOMALIES: Additional data quality issues or unexpected findings beyond rule-based ones
2. CLUSTER_FINDINGS: What do the cluster distributions suggest about EV subpopulations
3. MISSED_PARAMETERS: Important parameters worth investigating with scientific explanation
4. SUGGESTIONS: Specific actionable recommendations for this experiment
5. SUMMARY: 2-3 sentence overall assessment

Respond in this exact JSON format:
{{
  "anomalies": ["anomaly 1", "anomaly 2"],
  "cluster_findings": ["finding 1", "finding 2"],
  "missed_parameters": ["param 1", "param 2"],
  "suggestions": ["suggestion 1", "suggestion 2"],
  "summary": "Overall summary here"
}}"""

    ai_response_text = _call_bedrock(prompt, max_tokens=2000)

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

    data_context = json.dumps(all_stats, indent=2, default=str)

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
    import glob
    base_dir = Path(__file__).parent.parent.parent.parent / "data" / "nanofacs_parquet"
    
    files = []
    if base_dir.exists():
        for f in base_dir.rglob("*.fcs.parquet"):
            files.append({
                "path": str(f),
                "name": f.name,
                "folder": f.parent.name,
                "size_kb": round(f.stat().st_size / 1024, 1)
            })
    
    return {
        "files": sorted(files, key=lambda x: x["name"]),
        "total": len(files),
        "base_dir": str(base_dir)
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
