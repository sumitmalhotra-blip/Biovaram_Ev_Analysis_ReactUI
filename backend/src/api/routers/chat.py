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
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from loguru import logger

router = APIRouter()


# ============================================================================
# Configuration
# ============================================================================

def _get_api_key() -> Optional[str]:
    """Get AI API key from environment or config."""
    return (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("CRMIT_AI_API_KEY")
    )


def _get_provider() -> str:
    """Determine which AI provider to use."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "openai"  # default


# ============================================================================
# Request / Response Models
# ============================================================================

class ChatMessage(BaseModel):
    """A single chat message."""
    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message text content")


class ChatRequest(BaseModel):
    """Chat request body — matches what the frontend sends."""
    messages: list[ChatMessage] = Field(..., description="Conversation history")
    model: Optional[str] = Field(None, description="Model override (e.g. 'gpt-4o', 'claude-sonnet-4-20250514')")
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

async def _stream_openai(messages: list[ChatMessage], model: str, temperature: float, max_tokens: int):
    """Stream response from OpenAI API in Vercel AI SDK-compatible SSE format."""
    try:
        import httpx
    except ImportError:
        yield f'0:"{OFFLINE_RESPONSES["default"]}"\n'
        yield 'e:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n'
        yield 'd:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n'
        return
    
    api_key = _get_api_key()
    if not api_key:
        yield f'0:"{_get_offline_response(messages)}"\n'
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
                error_msg = f"AI API error ({response.status_code}). Check your API key and try again."
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
        yield '0:"Request timed out. Please try again."\n'
        yield 'e:{"finishReason":"error"}\n'
        yield 'd:{"finishReason":"error"}\n'
    except Exception as e:
        logger.error(f"OpenAI streaming error: {e}")
        yield f'0:"An error occurred: {str(e)}"\n'
        yield 'e:{"finishReason":"error"}\n'
        yield 'd:{"finishReason":"error"}\n'


# ============================================================================
# Anthropic streaming
# ============================================================================

async def _stream_anthropic(messages: list[ChatMessage], model: str, temperature: float, max_tokens: int):
    """Stream response from Anthropic API in Vercel AI SDK-compatible SSE format."""
    try:
        import httpx
    except ImportError:
        yield f'0:"{OFFLINE_RESPONSES["default"]}"\n'
        yield 'e:{"finishReason":"stop"}\n'
        yield 'd:{"finishReason":"stop"}\n'
        return
    
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        yield f'0:"{_get_offline_response(messages)}"\n'
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
                error_msg = f"AI API error ({response.status_code}). Check your API key and try again."
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
        yield '0:"Request timed out. Please try again."\n'
        yield 'e:{"finishReason":"error"}\n'
        yield 'd:{"finishReason":"error"}\n'
    except Exception as e:
        logger.error(f"Anthropic streaming error: {e}")
        yield f'0:"An error occurred: {str(e)}"\n'
        yield 'e:{"finishReason":"error"}\n'
        yield 'd:{"finishReason":"error"}\n'


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    AI Research Chat — streaming SSE endpoint.
    
    Sends messages to the configured LLM (OpenAI or Anthropic) and streams
    the response back in Vercel AI SDK-compatible format for the frontend
    useChat() hook.
    
    If no API key is configured, returns a helpful offline response.
    """
    logger.info(f"Chat request: {len(request.messages)} messages, stream={request.stream}")
    
    provider = _get_provider()
    model = request.model
    temperature = request.temperature or 0.7
    max_tokens = request.max_tokens or 2048
    
    if request.stream is False:
        # Non-streaming response
        return await _chat_simple(request)
    
    # Choose provider
    if provider == "anthropic":
        generator = _stream_anthropic(request.messages, model, temperature, max_tokens)
    else:
        generator = _stream_openai(request.messages, model, temperature, max_tokens)
    
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
    api_key = _get_api_key()
    
    if not api_key:
        return ChatResponse(
            content=_get_offline_response(request.messages),
            model="offline",
        )
    
    provider = _get_provider()
    model = request.model
    temperature = request.temperature or 0.7
    max_tokens = request.max_tokens or 2048
    
    try:
        import httpx
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
                        "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
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
                data = resp.json()
                content = data.get("content", [{}])[0].get("text", "No response")
                return ChatResponse(content=content, model=model or "claude-sonnet-4-20250514")
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
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "No response")
                usage = data.get("usage")
                return ChatResponse(
                    content=content,
                    model=model or "gpt-4o-mini",
                    usage=usage,
                )
    except Exception as e:
        logger.error(f"Chat API error: {e}")
        return ChatResponse(
            content=f"Error communicating with AI service: {str(e)}",
            model="error",
        )


@router.get("/chat/status", response_model=ChatStatusResponse)
async def chat_status():
    """
    Check whether AI chat is configured and available.
    Returns the provider and model information.
    """
    api_key = _get_api_key()
    
    if not api_key:
        return ChatStatusResponse(
            available=False,
            message="No AI API key configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable."
        )
    
    provider = _get_provider()
    default_model = "claude-sonnet-4-20250514" if provider == "anthropic" else "gpt-4o-mini"
    
    return ChatStatusResponse(
        available=True,
        provider=provider,
        model=default_model,
        message=f"AI chat is available via {provider} ({default_model})"
    )
