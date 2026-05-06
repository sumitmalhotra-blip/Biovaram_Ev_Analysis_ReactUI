"""
AI Research Chat Router
========================

Desktop-mode chat endpoint that proxies to an LLM API (OpenAI/Anthropic).
Falls back to a helpful offline response when no API key is configured.

Endpoints:
- POST /chat              - Send chat message, get AI response (streaming SSE)
- POST /chat/simple       - Send chat message, get non-streaming JSON response
- GET  /chat/status       - Check if AI chat is configured and available
- POST /chat/context      - Inject sample context for context-aware Q&A

Author: CRMIT Backend Team  
Date: March 3, 2026
"""

import os
import json
import time
import base64
import tempfile
from pathlib import Path
from typing import Optional, Tuple, AsyncIterable, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from loguru import logger

try:
    from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ProfileNotFound  # type: ignore
except ImportError:  # pragma: no cover
    NoCredentialsError = Exception  # type: ignore
    PartialCredentialsError = Exception  # type: ignore
    ProfileNotFound = Exception  # type: ignore

from src.api.aws_utils import get_bedrock_runtime_client
from src.api.ai_gateway_client import AIGatewayError, gateway_chat

router = APIRouter()


UI_MESSAGE_STREAM_HEADERS = {
    "content-type": "text/event-stream",
    "cache-control": "no-cache",
    "connection": "keep-alive",
    "x-vercel-ai-ui-message-stream": "v1",
    "x-accel-buffering": "no",
}


def _sse_data_line(data: str) -> str:
    return f"data: {data}\n\n"


def _sse_json(obj: Any) -> str:
    return _sse_data_line(json.dumps(obj, ensure_ascii=False))


async def _vercel_data_stream_to_ui_message_stream(
    source: AsyncIterable[Any],
    *,
    text_id: str = "text-0",
) -> AsyncIterable[str]:
    """Translate legacy Vercel AI data stream frames (0:/e:/d:) into UI message stream SSE."""

    buffer = ""
    done = False

    try:
        yield _sse_json({"type": "text-start", "id": text_id})

        async for chunk in source:
            if isinstance(chunk, memoryview):
                chunk = chunk.tobytes()
            if isinstance(chunk, (bytes, bytearray)):
                chunk = chunk.decode("utf-8", errors="ignore")
            if not isinstance(chunk, str):
                chunk = str(chunk)

            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.rstrip("\r")
                if not line:
                    continue

                if line.startswith("0:"):
                    payload = line[2:]
                    try:
                        value = json.loads(payload)
                    except Exception:
                        value = payload

                    delta = value if isinstance(value, str) else str(value)
                    if delta:
                        yield _sse_json({"type": "text-delta", "id": text_id, "delta": delta})

                elif line.startswith("e:"):
                    # e: frames are "step finish" events in the Vercel AI data stream
                    # protocol — they carry finishReason/usage metadata, NOT errors.
                    # Only emit an error event when the payload explicitly marks failure.
                    err_payload = line[2:]
                    try:
                        err_obj = json.loads(err_payload)
                        if isinstance(err_obj, dict):
                            finish = err_obj.get("finishReason", "")
                            explicit_err = err_obj.get("error") or err_obj.get("errorText") or err_obj.get("message")
                            if explicit_err:
                                yield _sse_json({"type": "error", "errorText": str(explicit_err)})
                            elif finish and finish not in ("stop", "length", "tool_calls", "end_turn", ""):
                                # Non-standard finish reason — surface as informational error
                                yield _sse_json({"type": "error", "errorText": f"Stream ended with reason: {finish}"})
                            # Normal stop/length finish — consume silently, no error event
                    except Exception:
                        pass  # Unparseable e: frame — ignore

                elif line.startswith("d:"):
                    done = True
                    break

            if done:
                break

    except Exception as e:
        yield _sse_json({"type": "error", "errorText": f"Stream error: {str(e)}"})

    yield _sse_json({"type": "text-end", "id": text_id})
    yield _sse_data_line("[DONE]")


# ============================================================================
# Configuration
# ============================================================================

VALID_ROLES = {"user", "assistant", "system"}
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
DEFAULT_BEDROCK_MODEL = "amazon.nova-lite-v1:0"


def _effective_model(provider: str, requested: str | None, default_model: str) -> str:
    requested_model = (requested or "").strip()

    # Frontend defaults to an OpenAI model string; for Bedrock/Gateway we must
    # use a Bedrock model id unless the caller explicitly provided one.
    if provider in {"bedrock", "gateway"}:
        if not requested_model or requested_model in {DEFAULT_OPENAI_MODEL, DEFAULT_ANTHROPIC_MODEL}:
            return (
                (os.environ.get("CRMIT_AI_MODEL") or default_model or DEFAULT_BEDROCK_MODEL).strip()
                or DEFAULT_BEDROCK_MODEL
            )
        return requested_model

    return requested_model or (default_model.strip() if default_model else "")


def _offline_chat_enabled() -> bool:
    """Allow local testing without external AI credentials."""
    env = (os.environ.get("CRMIT_ENV") or "development").strip().lower()
    flag = (os.environ.get("CRMIT_ENABLE_OFFLINE_AI") or "").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    if flag in {"1", "true", "yes", "on"}:
        return True
    return env in {"development", "dev", "local"}


def _resolve_provider_config() -> Tuple[str, str, str]:
    """
    Resolve provider, API key, and default model from environment.

    Rules:
    1) If AI_PROVIDER is set, enforce that provider.
    2) Otherwise prefer Anthropic only when ANTHROPIC_API_KEY is present.
    3) Fallback to OpenAI when OPENAI_API_KEY or CRMIT_AI_API_KEY is present.
    """
    provider_env = (os.environ.get("AI_PROVIDER") or "").strip().lower()

    if provider_env:
        if provider_env not in {"openai", "anthropic", "bedrock", "gateway"}:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Invalid AI_PROVIDER value. Supported values are 'openai', 'anthropic', 'bedrock', or 'gateway'."
                ),
            )

        if provider_env == "gateway":
            return "gateway", os.environ.get("CRMIT_AI_GATEWAY_LICENSE_KEY", ""), os.environ.get("CRMIT_AI_GATEWAY_URL", "")
        if provider_env == "bedrock":
            return "bedrock", "bedrock", "amazon.nova-lite-v1:0"

        if provider_env == "gateway":
            # Hosted gateway mode: proxy Bedrock calls to a server that has IAM/Bedrock access.
            gateway_url = (os.environ.get("CRMIT_AI_GATEWAY_URL") or "").strip()
            if not gateway_url:
                if _offline_chat_enabled():
                    return "offline", "", "offline-local"
                raise HTTPException(
                    status_code=503,
                    detail="Gateway provider selected, but CRMIT_AI_GATEWAY_URL is missing.",
                )
            model = (os.environ.get("CRMIT_AI_MODEL") or "amazon.nova-lite-v1:0").strip()
            return "gateway", "gateway", model
        if provider_env == "anthropic":
            key = (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CRMIT_AI_API_KEY") or "").strip()
            if not key:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Anthropic provider selected, but API key is missing. "
                        "Set ANTHROPIC_API_KEY or CRMIT_AI_API_KEY."
                    ),
                )
            model = (os.environ.get("ANTHROPIC_MODEL") or os.environ.get("CRMIT_AI_MODEL") or DEFAULT_ANTHROPIC_MODEL).strip()
            return "anthropic", key, model

        key = (os.environ.get("OPENAI_API_KEY") or os.environ.get("CRMIT_AI_API_KEY") or "").strip()
        if not key:
            raise HTTPException(
                status_code=503,
                detail=(
                    "OpenAI provider selected, but API key is missing. "
                    "Set OPENAI_API_KEY or CRMIT_AI_API_KEY."
                ),
            )
        model = (os.environ.get("OPENAI_MODEL") or os.environ.get("CRMIT_AI_MODEL") or DEFAULT_OPENAI_MODEL).strip()
        return "openai", key, model

    anthropic_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if anthropic_key:
        model = (os.environ.get("ANTHROPIC_MODEL") or os.environ.get("CRMIT_AI_MODEL") or DEFAULT_ANTHROPIC_MODEL).strip()
        return "anthropic", anthropic_key, model

    openai_key = (os.environ.get("OPENAI_API_KEY") or os.environ.get("CRMIT_AI_API_KEY") or "").strip()
    if openai_key:
        model = (os.environ.get("OPENAI_MODEL") or os.environ.get("CRMIT_AI_MODEL") or DEFAULT_OPENAI_MODEL).strip()
        return "openai", openai_key, model

    if _offline_chat_enabled():
        return "offline", "", "offline-local"

    raise HTTPException(
        status_code=503,
        detail=(
            "AI chat is not configured: no API key found. "
            "Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or CRMIT_AI_API_KEY."
        ),
    )


def _validate_chat_payload(request: "ChatRequest") -> None:
    """Validate chat payload and return explicit errors for invalid input."""
    if not request.messages:
        raise HTTPException(
            status_code=422,
            detail="Invalid request payload: 'messages' must contain at least one message.",
        )

    for idx, msg in enumerate(request.messages):
        if msg.role not in VALID_ROLES:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Invalid request payload: messages[{idx}].role='{msg.role}' is not supported. "
                    "Allowed roles are user, assistant, and system."
                ),
            )
        if not msg.content or not msg.content.strip():
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Invalid request payload: messages[{idx}].content must be a non-empty string."
                ),
            )


# ============================================================================
# Request / Response Models
# ============================================================================

class ChatMessage(BaseModel):
    @classmethod
    def model_validator(cls, data):
        if isinstance(data.get("content"), list):
            data["content"] = " ".join(
                p.get("text", "") if isinstance(p, dict) else str(p)
                for p in data["content"]
            )
        return data
    @classmethod
    def __get_validators__(cls):
        yield cls.validate_message

    @classmethod
    def validate_message(cls, v):
        return v
    """A single chat message."""
    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message text content")

    @classmethod
    def model_validate(cls, obj, **kwargs):
        if isinstance(obj, dict) and isinstance(obj.get("content"), list):
            obj = dict(obj)
            obj["content"] = " ".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in obj["content"])
        return super().model_validate(obj, **kwargs)


class ChatRequest(BaseModel):
    """Chat request body — matches what the frontend sends."""
    messages: list[ChatMessage] = Field(..., description="Conversation history")
    model: str = Field("gpt-4o-mini", description="Model override (e.g. 'gpt-4o', 'claude-sonnet-4-20250514')")
    temperature: Optional[float] = Field(0.7, description="Sampling temperature")
    max_tokens: Optional[int] = Field(2048, description="Max tokens in response")
    stream: Optional[bool] = Field(True, description="Whether to stream the response")


class ChatResponse(BaseModel):
    """Non-streaming chat response."""
    role: str = "assistant"
    content: str
    model: str
    usage: Optional[dict] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ChatStatusResponse(BaseModel):
    """Chat configuration status."""
    available: bool
    provider: Optional[str] = None
    model: Optional[str] = None
    message: str


# ============================================================================
# System prompt for EV analysis context
# ============================================================================

SYSTEM_PROMPT = """You are a scientific research assistant specializing in extracellular vesicle (EV) analysis, flow cytometry, and nanoparticle tracking analysis (NTA).

You help researchers with:
- Interpreting flow cytometry data (FCS files, scatter plots, gating strategies)
- Extracellular vesicle characterization (size distribution, concentration, markers)
- Nanoparticle Tracking Analysis (NTA) data interpretation
- Mie scattering theory as applied to nanoparticle sizing
- Bead calibration procedures and quality control
- Cross-validation between FCS and NTA measurements
- Statistical analysis of particle populations
- Best practices for EV isolation and characterization (MISEV guidelines)

When discussing data analysis:
- Be precise with numbers and units (nm for size, particles/mL for concentration)
- Reference relevant scientific concepts and equations
- Suggest appropriate statistical tests
- Recommend visualization approaches
- Flag potential quality control issues

Keep responses clear, scientifically accurate, and actionable. When uncertain, acknowledge limitations and suggest references."""


# ============================================================================
# Offline / fallback responses
# ============================================================================

OFFLINE_RESPONSES = {
    "default": (
        "I'm currently running in offline mode without an AI API key configured. "
        "To enable AI-powered responses, set one of these environment variables:\n\n"
        "- `OPENAI_API_KEY` — for GPT-4o responses\n"
        "- `ANTHROPIC_API_KEY` — for Claude responses\n"
        "- `CRMIT_AI_API_KEY` — generic key\n\n"
        "You can set these in your system environment or create a `.env` file in the backend directory.\n\n"
        "**In the meantime, here are some things I can tell you about EV analysis:**\n"
        "- The platform supports FCS file upload and Mie scattering-based particle sizing\n"
        "- Bead calibration uses Megamix Plus FSC/SSC standards\n"
        "- NTA data can be imported from NanoSight or ZetaView instruments\n"
        "- Cross-comparison between FCS and NTA validates sizing accuracy"
    ),
    "gating": (
        "**Flow Cytometry Gating Strategies for EVs:**\n\n"
        "1. **Forward/Side Scatter Gate**: Start with FSC vs SSC to identify the EV region\n"
        "2. **Size Gate**: Use calibration beads to set size boundaries (50-1000 nm)\n"
        "3. **Fluorescence Gate**: Apply marker-specific gates (CD63, CD81, CD9)\n"
        "4. **Doublet Discrimination**: FSC-H vs FSC-A to exclude aggregates\n\n"
        "For your CytoFLEX nano, the VSSC channel provides better resolution below 200 nm."
    ),
    "size": (
        "**EV Size Distribution Interpretation:**\n\n"
        "- **D10**: 10th percentile — captures the smallest detectable EVs\n"
        "- **D50 (median)**: Most representative single size metric\n"
        "- **D90**: 90th percentile — includes larger vesicles/microvesicles\n"
        "- **Mode**: Peak of the distribution — often most biologically relevant\n\n"
        "Typical EV sizes: exosomes (30-150 nm), microvesicles (100-1000 nm), apoptotic bodies (>1000 nm).\n"
        "Your Mie-based sizing should give D50 values within 10-15% of NTA measurements."
    ),
}


def _get_offline_response(messages: list[ChatMessage]) -> str:
    """Generate a helpful offline response based on the question."""
    if not messages:
        return OFFLINE_RESPONSES["default"]
    
    last_msg = messages[-1].content.lower()
    
    if any(word in last_msg for word in ["gate", "gating", "scatter"]):
        return OFFLINE_RESPONSES["gating"]
    elif any(word in last_msg for word in ["size", "distribution", "d50", "d90", "diameter"]):
        return OFFLINE_RESPONSES["size"]
    
    return OFFLINE_RESPONSES["default"]


# ============================================================================
# FCS / CSV file summary extraction for chat context
# ============================================================================

_MAX_FILE_BYTES_FOR_PARSE = 150 * 1024 * 1024  # 150 MB cap


def _extract_fcs_summary_from_bytes(data: bytes, filename: str) -> str:
    """Parse an FCS file from raw bytes and return a compact stats summary."""
    import numpy as np

    try:
        import flowio  # type: ignore
    except ImportError:
        return f"Attached FCS file: {filename} (flowio not installed; cannot extract statistics)"

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".fcs", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        fcs = flowio.FlowData(tmp_path)
        n_channels = fcs.channel_count
        txt = getattr(fcs, "text", {}) or {}

        # Extract channel names using the same logic as the existing FCS parser
        channel_names = []
        for i in range(1, n_channels + 1):
            name = (
                txt.get(f"p{i}s", "") or txt.get(f"p{i}n", "") or
                txt.get(f"$P{i}S", "") or txt.get(f"$P{i}N", "") or
                txt.get(f"P{i}S", "") or txt.get(f"P{i}N", "") or
                f"Channel_{i}"
            )
            channel_names.append(name.strip())

        # Event matrix
        raw = np.array(fcs.events, dtype=float).reshape(-1, n_channels)
        n_events = raw.shape[0]

        # Build per-channel stats (limit to 15 channels to keep prompt concise)
        ch_stats = []
        for i, name in enumerate(channel_names[:15]):
            col = raw[:, i]
            ch_stats.append(
                f"  {name}: mean={col.mean():.1f}, median={np.median(col):.1f}, "
                f"std={col.std():.1f}, min={col.min():.1f}, max={col.max():.1f}"
            )

        # Highlight FSC/SSC scatter parameters
        fsc_idx = next((i for i, n in enumerate(channel_names) if "FSC" in n.upper()), None)
        ssc_idx = next((i for i, n in enumerate(channel_names) if "SSC" in n.upper()), None)
        ev_lines = []
        if fsc_idx is not None:
            fsc = raw[:, fsc_idx]
            ev_lines.append(f"  FSC: median={np.median(fsc):.1f}, mean={fsc.mean():.1f}, std={fsc.std():.1f}")
        if ssc_idx is not None:
            ssc = raw[:, ssc_idx]
            ev_lines.append(f"  SSC: median={np.median(ssc):.1f}, mean={ssc.mean():.1f}, std={ssc.std():.1f}")

        sample_id = (
            txt.get("$SRC") or txt.get("src") or txt.get("$SMNO") or
            txt.get("TUBE NAME") or txt.get("tube name") or filename
        )
        cytometer = txt.get("$CYT") or txt.get("cyt") or txt.get("CYTOMETER") or "Unknown"
        date_str = txt.get("$DATE") or txt.get("date") or "Unknown"

        summary_lines = [
            f"=== FCS File Analysis: {filename} ===",
            f"Sample ID: {sample_id}",
            f"Cytometer: {cytometer}",
            f"Acquisition date: {date_str}",
            f"Total events recorded: {n_events:,}",
            f"Channels ({n_channels}): {', '.join(channel_names)}",
            "",
            "Per-channel statistics:",
        ] + ch_stats

        if ev_lines:
            summary_lines += ["", "Scatter channel summary:"] + ev_lines

        summary_lines += [
            "",
            "Please analyze this FCS data for extracellular vesicle (EV) characterization. "
            "Provide insights on particle distribution, scatter profile, concentration estimates, "
            "size population breakdown, and any notable quality control observations.",
        ]

        return "\n".join(summary_lines)

    except Exception as exc:
        logger.warning(f"FCS parse failed for {filename}: {exc}")
        return f"Attached FCS file: {filename} (could not extract statistics: {exc})"
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass


def _extract_csv_summary_from_bytes(data: bytes, filename: str) -> str:
    """Parse a CSV/NTA file and return a compact stats summary."""
    import io
    import numpy as np

    try:
        import pandas as pd  # type: ignore
    except ImportError:
        return f"Attached CSV file: {filename} (pandas not installed)"

    try:
        df = pd.read_csv(io.BytesIO(data), nrows=100_000)
        rows, cols = df.shape
        numeric = df.select_dtypes(include=[np.number])
        stats_lines = []
        for col in numeric.columns[:20]:  # cap at 20 columns
            s = numeric[col]
            stats_lines.append(
                f"  {col}: mean={s.mean():.3g}, median={s.median():.3g}, "
                f"std={s.std():.3g}, min={s.min():.3g}, max={s.max():.3g}"
            )
        return "\n".join([
            f"=== CSV/NTA File Analysis: {filename} ===",
            f"Rows: {rows:,}, Columns: {cols}",
            "Numeric column statistics:",
            *stats_lines,
            "",
            "Please analyze this NTA/CSV data for extracellular vesicle characterization.",
        ])
    except Exception as exc:
        logger.warning(f"CSV parse failed for {filename}: {exc}")
        return f"Attached CSV file: {filename} (could not parse: {exc})"


def _summarize_file_part(part: dict) -> str:
    """Extract a statistics summary from a file message part."""
    filename = (part.get("filename") or part.get("name") or "unknown").strip()
    media_type = part.get("mediaType") or part.get("mimeType") or ""
    raw_data = part.get("data") or part.get("url") or ""

    # Decode base64 → bytes
    file_bytes: bytes | None = None
    if isinstance(raw_data, str):
        # Data URLs: "data:<mime>;base64,<payload>"
        if raw_data.startswith("data:"):
            try:
                _, b64 = raw_data.split(",", 1)
                file_bytes = base64.b64decode(b64)
            except Exception:
                pass
        else:
            try:
                file_bytes = base64.b64decode(raw_data)
            except Exception:
                pass

    if file_bytes is None or len(file_bytes) == 0:
        return f"Attached file: {filename}" + (f" ({media_type})" if media_type else "")

    if len(file_bytes) > _MAX_FILE_BYTES_FOR_PARSE:
        return (
            f"Attached file: {filename} ({len(file_bytes) // 1024 / 1024:.1f} MB — "
            "file is too large to parse inline; only metadata was received)"
        )

    fname_lower = filename.lower()
    if fname_lower.endswith(".fcs"):
        return _extract_fcs_summary_from_bytes(file_bytes, filename)
    elif fname_lower.endswith((".csv", ".tsv", ".txt")):
        return _extract_csv_summary_from_bytes(file_bytes, filename)
    else:
        return f"Attached file: {filename}" + (f" ({media_type})" if media_type else "")


# ============================================================================
# OpenAI streaming
# ============================================================================


async def _stream_bedrock(messages: list, max_tokens: int, temperature: float):
    """Stream responses from AWS Bedrock Nova."""
    import json as _json
    client = get_bedrock_runtime_client()
    payload = {
        "messages": [{"role": m.role if m.role != "system" else "user", "content": [{"text": m.content}]} for m in messages],
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
    }
    try:
        response = client.invoke_model(
            modelId="amazon.nova-lite-v1:0",
            contentType="application/json",
            accept="application/json",
            body=_json.dumps(payload),
        )
        result = _json.loads(response["body"].read())
        text = result["output"]["message"]["content"][0]["text"].strip()
        # Stream in Vercel AI SDK format
        for chunk in [text[i:i+20] for i in range(0, len(text), 20)]:
            yield f'0:{_json.dumps(chunk)}\n'
    except (NoCredentialsError, PartialCredentialsError, ProfileNotFound) as e:
        if _offline_chat_enabled():
            offline = _get_offline_response(messages)
            for chunk in [offline[i:i+20] for i in range(0, len(offline), 20)]:
                yield f'0:{_json.dumps(chunk)}\n'
        else:
            yield f'0:{_json.dumps(f"Error: {str(e)}")}\n'
    except Exception as e:
        yield f'0:{_json.dumps(f"Error: {str(e)}")}\n'


async def _stream_text_as_vercel(text: str):
    import json as _json
    for chunk in [text[i:i+20] for i in range(0, len(text), 20)]:
        yield f'0:{_json.dumps(chunk)}\n'
    yield 'e:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n'
    yield 'd:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n'

async def _stream_openai(messages: list[ChatMessage], api_key: str, model: str, temperature: float, max_tokens: int):
    """Stream response from OpenAI API in Vercel AI SDK-compatible SSE format."""
    try:
        import httpx  # type: ignore[import-untyped]
    except ImportError:
        yield f'0:"{OFFLINE_RESPONSES["default"]}"\n'
        yield 'e:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n'
        yield 'd:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n'
        return
    
    # Build messages with system prompt
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in messages:
        api_messages.append({"role": msg.role, "content": msg.content})
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model or "gpt-4o-mini",
                    "messages": api_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                },
            )
            
            if response.status_code != 200:
                error_body = response.text
                logger.error(f"OpenAI API error {response.status_code}: {error_body}")
                error_msg = (
                    f"OpenAI request failed with status {response.status_code}. "
                    "Please verify provider/API key configuration and try again."
                )
                yield f'0:"{error_msg}"\n'
                yield 'e:{"finishReason":"error"}\n'
                yield 'd:{"finishReason":"error"}\n'
                return
            
            # Stream SSE chunks — convert OpenAI format to Vercel AI SDK format
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        # Escape for Vercel AI SDK text streaming format
                        escaped = json.dumps(content)
                        yield f"0:{escaped}\n"
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue
            
            yield 'e:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n'
            yield 'd:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n'
    
    except httpx.TimeoutException:
        yield '0:"Provider timeout: OpenAI did not respond in time. Please retry in a moment."\n'
        yield 'e:{"finishReason":"error"}\n'
        yield 'd:{"finishReason":"error"}\n'
    except Exception as e:
        logger.error(f"OpenAI streaming error: {e}")
        yield f'0:"OpenAI request failed: {str(e)}"\n'
        yield 'e:{"finishReason":"error"}\n'
        yield 'd:{"finishReason":"error"}\n'


# ============================================================================
# Anthropic streaming
# ============================================================================

async def _stream_anthropic(messages: list[ChatMessage], api_key: str, model: str, temperature: float, max_tokens: int):
    """Stream response from Anthropic API in Vercel AI SDK-compatible SSE format."""
    try:
        import httpx  # type: ignore[import-untyped]
    except ImportError:
        yield f'0:"{OFFLINE_RESPONSES["default"]}"\n'
        yield 'e:{"finishReason":"stop"}\n'
        yield 'd:{"finishReason":"stop"}\n'
        return
    
    # Build messages (Anthropic uses system param separately)
    api_messages = []
    for msg in messages:
        if msg.role != "system":
            api_messages.append({"role": msg.role, "content": msg.content})
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model or "claude-sonnet-4-20250514",
                    "system": SYSTEM_PROMPT,
                    "messages": api_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                },
            )
            
            if response.status_code != 200:
                error_body = response.text
                logger.error(f"Anthropic API error {response.status_code}: {error_body}")
                error_msg = (
                    f"Anthropic request failed with status {response.status_code}. "
                    "Please verify provider/API key configuration and try again."
                )
                yield f'0:"{error_msg}"\n'
                yield 'e:{"finishReason":"error"}\n'
                yield 'd:{"finishReason":"error"}\n'
                return
            
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    event_data = json.loads(line[6:])
                    event_type = event_data.get("type", "")
                    
                    if event_type == "content_block_delta":
                        delta = event_data.get("delta", {})
                        text = delta.get("text", "")
                        if text:
                            escaped = json.dumps(text)
                            yield f"0:{escaped}\n"
                    elif event_type == "message_stop":
                        break
                except (json.JSONDecodeError, KeyError):
                    continue
            
            yield 'e:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n'
            yield 'd:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n'
    
    except httpx.TimeoutException:
        yield '0:"Provider timeout: Anthropic did not respond in time. Please retry in a moment."\n'
        yield 'e:{"finishReason":"error"}\n'
        yield 'd:{"finishReason":"error"}\n'
    except Exception as e:
        logger.error(f"Anthropic streaming error: {e}")
        yield f'0:"Anthropic request failed: {str(e)}"\n'
        yield 'e:{"finishReason":"error"}\n'
        yield 'd:{"finishReason":"error"}\n'


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/chat")
async def chat(request: Request):
    """Streaming chat endpoint compatible with the Vercel AI SDK useChat()."""
    raw = await request.json()

    # Normalize payload to ChatRequest shape (frontend sometimes sends content as parts).
    messages: list[ChatMessage] = []
    for m in raw.get("messages", []) or []:
        role = (m.get("role") or "user")
        content = m.get("content", "")
        if isinstance(content, list):
            content = " ".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
            content = combined

        if isinstance(content, str) and content.strip():
            normalized.append(ChatMessage(role=role, content=content))

    if not normalized and isinstance(raw, dict) and isinstance(raw.get("query"), str) and raw.get("query", "").strip():
        normalized = [ChatMessage(role="user", content=raw["query"]) ]

    chat_req = ChatRequest(
        messages=normalized,
        # Leave blank when not provided so we can use provider defaults later.
        model=(raw.get("model") if isinstance(raw, dict) else None) or "",
        temperature=(raw.get("temperature") if isinstance(raw, dict) else None),
        max_tokens=(raw.get("max_tokens") if isinstance(raw, dict) else None),
        stream=(raw.get("stream") if isinstance(raw, dict) else None),
    )
    _validate_chat_payload(chat_req)

    provider, api_key, default_model = _resolve_provider_config()
    model = (chat_req.model or default_model).strip()
    temperature = chat_req.temperature or 0.7
    max_tokens = chat_req.max_tokens or 2048

    if chat_req.stream is False:
        return await _chat_simple(chat_req)

    # Gateway is non-streaming upstream; we wrap it in a one-chunk Vercel stream.
    if provider == "gateway":
        async def gen_gateway():
            try:
                import httpx  # type: ignore[import-untyped]

                gw_url = (os.environ.get("CRMIT_AI_GATEWAY_URL") or "").rstrip("/")
                gw_key = (os.environ.get("CRMIT_AI_GATEWAY_LICENSE_KEY") or "").strip()
                if not gw_url or not gw_key:
                    raise RuntimeError("Gateway is not configured (missing CRMIT_AI_GATEWAY_URL or CRMIT_AI_GATEWAY_LICENSE_KEY).")

                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        f"{gw_url}/api/v1/ai/gateway/chat",
                        headers={"Content-Type": "application/json", "x-license-key": gw_key},
                        json={
                            "messages": [{"role": m.role, "content": m.content} for m in chat_req.messages],
                            "max_tokens": max_tokens,
                            "temperature": temperature,
                            "model": model,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json() if resp.content else {}
                    text = (data.get("content") or "").strip() or "No response"

                yield f"0:{json.dumps(text)}\n"
                yield 'd:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n'
            except Exception as e:
                msg = f"Gateway request failed: {str(e)}"
                yield f"0:{json.dumps(msg)}\n"
                yield 'd:{"finishReason":"error","usage":{"promptTokens":0,"completionTokens":0}}\n'

        return StreamingResponse(
            _vercel_data_stream_to_ui_message_stream(gen_gateway()),
            media_type="text/event-stream",
            headers=UI_MESSAGE_STREAM_HEADERS,
        )

    # Other providers stream directly.
    if provider == "anthropic":
        generator = _stream_anthropic(chat_req.messages, api_key, model, temperature, max_tokens)
    elif provider == "bedrock":
        generator = _stream_bedrock(chat_req.messages, max_tokens, temperature)
    else:
        generator = _stream_openai(chat_req.messages, api_key, model, temperature, max_tokens)

    return StreamingResponse(
        _vercel_data_stream_to_ui_message_stream(generator),
        media_type="text/event-stream",
        headers=UI_MESSAGE_STREAM_HEADERS,
    )


@router.post("/chat/simple", response_model=ChatResponse)
async def _chat_simple(request: ChatRequest):
    """
    Non-streaming chat endpoint — returns complete response as JSON.
    Useful for programmatic access or simpler integrations.
    """
    _validate_chat_payload(request)
    provider, api_key, default_model = _resolve_provider_config()
    if provider == "offline":
        return ChatResponse(content=_get_offline_response(request.messages), model="offline-local")

    # Gateway mode does not require httpx; it proxies to the hosted gateway.
    if provider == "gateway":
        model = _effective_model(provider, request.model, default_model)
        temperature = request.temperature or 0.7
        max_tokens = request.max_tokens or 2048
        try:
            text = await run_in_threadpool(
                gateway_chat,
                [{"role": m.role, "content": m.content} for m in request.messages],
                model or "amazon.nova-lite-v1:0",
                float(temperature),
                int(max_tokens),
            )
            return ChatResponse(content=text, model=model or "amazon.nova-lite-v1:0")
        except AIGatewayError as exc:
            if _offline_chat_enabled():
                return ChatResponse(content=_get_offline_response(request.messages), model="offline-local")
            raise HTTPException(status_code=503, detail=str(exc))

    model = _effective_model(provider, request.model, default_model)
    temperature = request.temperature or 0.7
    max_tokens = request.max_tokens or 2048

    # Bedrock does not require httpx; call directly via boto3.
    if provider == "bedrock":
        import json as _json

        bedrock = get_bedrock_runtime_client()
        payload = {
            "messages": [
                {
                    "role": m.role if m.role != "system" else "user",
                    "content": [{"text": m.content}],
                }
                for m in request.messages
            ],
            "inferenceConfig": {"maxTokens": int(max_tokens), "temperature": float(temperature)},
        }
        try:
            response = bedrock.invoke_model(
                modelId=model or "amazon.nova-lite-v1:0",
                contentType="application/json",
                accept="application/json",
                body=_json.dumps(payload),
            )
            result = _json.loads(response["body"].read())
            content = result["output"]["message"]["content"][0]["text"].strip()
            return ChatResponse(content=content, model=model or "amazon.nova-lite-v1:0")
        except (NoCredentialsError, PartialCredentialsError, ProfileNotFound) as e:
            if _offline_chat_enabled():
                return ChatResponse(content=_get_offline_response(request.messages), model="offline-local")
            raise HTTPException(status_code=503, detail=f"AWS credentials not configured: {e}")
    
    try:
        import httpx  # type: ignore[import-untyped]
    except ImportError:
        return ChatResponse(content=OFFLINE_RESPONSES["default"], model="offline")
    
    # Build messages
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in request.messages:
        api_messages.append({"role": msg.role, "content": msg.content})
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if provider == "anthropic":
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model or "claude-sonnet-4-20250514",
                        "system": SYSTEM_PROMPT,
                        "messages": [{"role": m.role, "content": m.content} for m in request.messages if m.role != "system"],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=(
                            f"Anthropic request failed with status {resp.status_code}. "
                            "Please verify provider/API key configuration and try again."
                        ),
                    )
                data = resp.json()
                content = data.get("content", [{}])[0].get("text", "No response")
                return ChatResponse(content=content, model=model or DEFAULT_ANTHROPIC_MODEL)
            else:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model or "gpt-4o-mini",
                        "messages": api_messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=(
                            f"OpenAI request failed with status {resp.status_code}. "
                            "Please verify provider/API key configuration and try again."
                        ),
                    )
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "No response")
                usage = data.get("usage")
                return ChatResponse(
                    content=content,
                    model=model or DEFAULT_OPENAI_MODEL,
                    usage=usage,
                )
    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Provider timeout: {provider} did not respond in time.",
        )
    except Exception as e:
        logger.error(f"Chat API error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error communicating with AI service: {str(e)}",
        )


@router.get("/chat/status", response_model=ChatStatusResponse)
async def chat_status():
    """
    Check whether AI chat is configured and available.
    Returns the provider and model information.
    """
    try:
        provider, _api_key, default_model = _resolve_provider_config()
        return ChatStatusResponse(
            available=True,
            provider=provider,
            model=default_model,
            message=f"AI chat is available via {provider} ({default_model})"
        )
    except HTTPException as e:
        return ChatStatusResponse(
            available=False,
            provider=None,
            model=None,
            message=str(e.detail),
        )
