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
from typing import Optional, Tuple
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from loguru import logger

router = APIRouter()


# ============================================================================
# Configuration
# ============================================================================

VALID_ROLES = {"user", "assistant", "system"}
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"


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
        if provider_env not in {"openai", "anthropic", "bedrock"}:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Invalid AI_PROVIDER value. Supported values are 'openai' or 'anthropic'."
                ),
            )

        if provider_env == "bedrock":
            return "bedrock", "bedrock", "amazon.nova-lite-v1:0"
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
# OpenAI streaming
# ============================================================================


async def _stream_bedrock(messages: list, max_tokens: int, temperature: float):
    """Stream responses from AWS Bedrock Nova."""
    import boto3, json as _json, os as _os
    client = boto3.client(
        service_name="bedrock-runtime",
        region_name=_os.environ.get("AWS_REGION", "us-east-1"),
        aws_access_key_id=_os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=_os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )
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
    except Exception as e:
        yield f'0:{_json.dumps(f"Error: {str(e)}")}\n'

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
    raw = await request.json()
    logger.info(f"RAW CHAT PAYLOAD: {raw}")
    # Normalize messages
    msgs = []
    for m in raw.get("messages", []):
        c = m.get("content", "")
        if isinstance(c, list):
            c = " ".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in c)
        if c.strip():
            msgs.append({"role": m.get("role", "user"), "content": c})
    if not msgs and "query" in raw:
        msgs = [{"role": "user", "content": raw["query"]}]
    if not msgs:
        return {"success": False, "error": "No messages found"}
    # Call bedrock directly
    import boto3, json as _json, os as _os
    client = boto3.client(
        service_name="bedrock-runtime",
        region_name=_os.environ.get("AWS_REGION", "us-east-1"),
        aws_access_key_id=_os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=_os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )
    payload = {
        "messages": [{"role": m["role"] if m["role"] != "system" else "user", "content": [{"text": m["content"]}]} for m in msgs],
        "inferenceConfig": {"maxTokens": 1024, "temperature": 0.7},
    }
    response = client.invoke_model(
        modelId="amazon.nova-lite-v1:0",
        contentType="application/json",
        accept="application/json",
        body=_json.dumps(payload),
    )
    result = _json.loads(response["body"].read())
    text = result["output"]["message"]["content"][0]["text"].strip()
    # Return in Vercel AI SDK streaming format
    from fastapi.responses import StreamingResponse as SR
    async def gen():
        yield f'0:{_json.dumps(text)}\n'
    return SR(gen(), media_type="text/plain; charset=utf-8", headers={"X-Vercel-AI-Data-Stream": "v1"})
    """
    AI Research Chat — streaming SSE endpoint.
    
    Sends messages to the configured LLM (OpenAI or Anthropic) and streams
    the response back in Vercel AI SDK-compatible format for the frontend
    useChat() hook.
    
    If no API key is configured, returns a helpful offline response.
    """
    _validate_chat_payload(request)
    logger.info(f"Chat request: {len(request.messages)} messages, stream={request.stream}")

    provider, api_key, default_model = _resolve_provider_config()
    model = (request.model or default_model).strip()
    temperature = request.temperature or 0.7
    max_tokens = request.max_tokens or 2048
    
    if request.stream is False:
        # Non-streaming response
        return await _chat_simple(request)
    
    # Choose provider
    if provider == "anthropic":
        generator = _stream_anthropic(request.messages, api_key, model, temperature, max_tokens)
    elif provider == "bedrock":
        generator = _stream_bedrock(request.messages, max_tokens, temperature)
    else:
        generator = _stream_openai(request.messages, api_key, model, temperature, max_tokens)
    
    return StreamingResponse(
        generator,
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Vercel-AI-Data-Stream": "v1",
        },
    )


@router.post("/chat/simple", response_model=ChatResponse)
async def _chat_simple(request: ChatRequest):
    """
    Non-streaming chat endpoint — returns complete response as JSON.
    Useful for programmatic access or simpler integrations.
    """
    _validate_chat_payload(request)
    provider, api_key, default_model = _resolve_provider_config()
    model = (request.model or default_model).strip()
    temperature = request.temperature or 0.7
    max_tokens = request.max_tokens or 2048
    
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
            elif provider == "bedrock":
                import boto3, json as _json, os as _os
                bedrock = boto3.client(
                    service_name="bedrock-runtime",
                    region_name=_os.environ.get("AWS_REGION", "us-east-1"),
                    aws_access_key_id=_os.environ.get("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=_os.environ.get("AWS_SECRET_ACCESS_KEY"),
                )
                payload = {
                    "messages": [{"role": m.role if m.role != "system" else "user", "content": [{"text": m.content}]} for m in request.messages],
                    "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
                }
                response = bedrock.invoke_model(
                    modelId="amazon.nova-lite-v1:0",
                    contentType="application/json",
                    accept="application/json",
                    body=_json.dumps(payload),
                )
                result = _json.loads(response["body"].read())
                content = result["output"]["message"]["content"][0]["text"].strip()
                return ChatResponse(content=content, model="amazon.nova-lite-v1:0")
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
