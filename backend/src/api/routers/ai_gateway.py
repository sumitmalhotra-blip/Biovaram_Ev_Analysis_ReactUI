"""AI Gateway Router
=================

Hosted AI Gateway endpoints.

This router is used when deploying a hosted gateway service that desktop
clients can call using a license key (so AWS/provider credentials never
ship in the desktop app).

Notes:
- This module is intentionally dependency-light so the main API can boot
  even if optional provider SDKs (e.g., boto3) are not installed.
- The desktop/local app does not need to call these endpoints.

Endpoints:
- GET  /ai/gateway/health
- POST /ai/gateway/chat

"""

from __future__ import annotations

import os
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from loguru import logger

router = APIRouter()


VALID_ROLES = {"user", "assistant", "system"}
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"


class GatewayMessage(BaseModel):
    role: str = Field(...)
    content: str = Field(...)


class GatewayChatRequest(BaseModel):
    messages: list[GatewayMessage]
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048


class GatewayChatResponse(BaseModel):
    content: str
    model: str
    provider: str


def _require_license(x_license_key: Optional[str]) -> None:
    expected = (os.environ.get("CRMIT_AI_GATEWAY_LICENSE_KEY") or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Gateway is not configured (missing CRMIT_AI_GATEWAY_LICENSE_KEY).",
        )
    if not x_license_key or x_license_key.strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing license key.")


def _resolve_provider() -> tuple[str, str, str]:
    """Return (provider, api_key, default_model)."""

    provider_env = (os.environ.get("AI_PROVIDER") or "").strip().lower()
    if provider_env in {"openai", "anthropic", "bedrock"}:
        provider = provider_env
    else:
        # Prefer Anthropic if present, else OpenAI.
        provider = "anthropic" if (os.environ.get("ANTHROPIC_API_KEY") or "").strip() else "openai"

    if provider == "anthropic":
        key = (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CRMIT_AI_API_KEY") or "").strip()
        if not key:
            raise HTTPException(status_code=503, detail="Anthropic API key missing.")
        model = (os.environ.get("ANTHROPIC_MODEL") or os.environ.get("CRMIT_AI_MODEL") or DEFAULT_ANTHROPIC_MODEL).strip()
        return provider, key, model

    if provider == "bedrock":
        # Optional dependency. Only used in hosted gateway deployments.
        try:
            import boto3  # type: ignore
        except ImportError as e:
            raise HTTPException(status_code=503, detail="Bedrock provider requires boto3.") from e

        # Bedrock does not use an API key in the same way.
        return provider, "bedrock", (os.environ.get("BEDROCK_MODEL") or "amazon.nova-lite-v1:0").strip()

    # OpenAI
    key = (os.environ.get("OPENAI_API_KEY") or os.environ.get("CRMIT_AI_API_KEY") or "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="OpenAI API key missing.")
    model = (os.environ.get("OPENAI_MODEL") or os.environ.get("CRMIT_AI_MODEL") or DEFAULT_OPENAI_MODEL).strip()
    return "openai", key, model


@router.get("/ai/gateway/health")
async def health():
    """Basic health check for the hosted gateway router."""
    return {"ok": True}


@router.post("/ai/gateway/chat", response_model=GatewayChatResponse)
async def gateway_chat(
    request: GatewayChatRequest,
    x_license_key: Optional[str] = Header(default=None, alias="x-license-key"),
):
    _require_license(x_license_key)

    if not request.messages:
        raise HTTPException(status_code=422, detail="'messages' must not be empty.")

    for idx, m in enumerate(request.messages):
        if m.role not in VALID_ROLES:
            raise HTTPException(status_code=422, detail=f"messages[{idx}].role is invalid")
        if not m.content or not m.content.strip():
            raise HTTPException(status_code=422, detail=f"messages[{idx}].content must be non-empty")

    provider, api_key, default_model = _resolve_provider()
    model = (request.model or default_model).strip() or default_model
    temperature = 0.7 if request.temperature is None else float(request.temperature)
    max_tokens = 2048 if request.max_tokens is None else int(request.max_tokens)

    try:
        import httpx  # type: ignore[import-not-found]
    except ImportError as e:
        raise HTTPException(status_code=503, detail="httpx is required for gateway providers.") from e

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
                        "model": model,
                        "messages": [{"role": m.role, "content": m.content} for m in request.messages if m.role != "system"],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                if resp.status_code != 200:
                    raise HTTPException(status_code=resp.status_code, detail=resp.text)
                data = resp.json()
                text = (data.get("content") or [{}])[0].get("text") or ""
                return GatewayChatResponse(content=text, model=model, provider=provider)

            if provider == "bedrock":
                # Keep this minimal; hosted deployment should ensure boto3 + AWS creds.
                import boto3  # type: ignore

                bedrock = boto3.client(
                    "bedrock-runtime",
                    region_name=os.environ.get("AWS_REGION", "us-east-1"),
                )
                payload = {
                    "messages": [
                        {
                            "role": (m.role if m.role != "system" else "user"),
                            "content": [{"text": m.content}],
                        }
                        for m in request.messages
                    ],
                    "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
                }
                response = bedrock.invoke_model(
                    modelId=model,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(payload),
                )
                result = json.loads(response["body"].read())
                text = result["output"]["message"]["content"][0]["text"].strip()
                return GatewayChatResponse(content=text, model=model, provider=provider)

            # OpenAI
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": m.role, "content": m.content} for m in request.messages],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            data = resp.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return GatewayChatResponse(content=text, model=model, provider=provider)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Gateway chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Gateway error: {str(e)}")
