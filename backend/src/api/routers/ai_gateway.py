from __future__ import annotations

import json
import os
from typing import Optional

from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ProfileNotFound  # type: ignore
from fastapi import APIRouter, Header, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from src.api.aws_utils import get_bedrock_runtime_client

router = APIRouter()


def _offline_ai_enabled() -> bool:
    return (os.getenv("CRMIT_ENABLE_OFFLINE_AI") or "").strip().lower() in {"1", "true", "yes", "on"}


def _allowed_license_keys() -> list[str]:
    raw = (os.getenv("CRMIT_AI_GATEWAY_LICENSE_KEYS") or "").strip()
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]


def _require_license(x_license_key: Optional[str]) -> None:
    allowed = _allowed_license_keys()
    if not allowed:
        return
    if not x_license_key or x_license_key.strip() not in allowed:
        raise HTTPException(status_code=401, detail="Invalid or missing X-License-Key")


class GatewayChatRequest(BaseModel):
    messages: list[dict] = Field(..., description="Chat messages (role/content)")
    model: str = Field("amazon.nova-lite-v1:0")
    temperature: float = Field(0.7)
    max_tokens: int = Field(2048)


class GatewayCompleteRequest(BaseModel):
    prompt: str
    model: str = Field("amazon.nova-lite-v1:0")
    temperature: float = Field(0.3)
    max_tokens: int = Field(1500)


@router.get("/ai/gateway/health")
async def gateway_health():
    """Health/status endpoint for hosted gateway."""
    return {
        "status": "ok",
        "mode": "gateway",
        "requires_license": bool(_allowed_license_keys()),
        "region": os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1",
        "model": "amazon.nova-lite-v1:0",
    }


@router.post("/ai/gateway/chat")
async def gateway_chat_endpoint(payload: GatewayChatRequest, x_license_key: Optional[str] = Header(default=None)):
    _require_license(x_license_key)

    bedrock = get_bedrock_runtime_client()

    # Convert to Bedrock Nova message format.
    messages = []
    for m in payload.messages:
        role = (m.get("role") or "user")
        content = m.get("content") or ""
        if isinstance(content, list):
            content = " ".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
        messages.append({
            "role": role if role != "system" else "user",
            "content": [{"text": str(content)}],
        })

    body = {
        "messages": messages,
        "inferenceConfig": {
            "maxTokens": int(payload.max_tokens),
            "temperature": float(payload.temperature),
        },
    }

    try:
        response = bedrock.invoke_model(
            modelId=payload.model or "amazon.nova-lite-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        result = json.loads(response["body"].read())
        text = result["output"]["message"]["content"][0]["text"].strip()
        return {
            "content": text,
            "model": payload.model,
            "provider": "bedrock",
        }
    except (NoCredentialsError, PartialCredentialsError, ProfileNotFound) as exc:
        if _offline_ai_enabled():
            return {
                "content": (
                    "Offline AI mode is active for local testing (no AWS credentials configured on gateway). "
                    "Deploy the gateway with an IAM role/credentials to enable real AI."
                ),
                "model": payload.model,
                "provider": "offline_local",
            }
        raise HTTPException(status_code=503, detail=f"AWS credentials not configured on gateway: {exc}")
    except Exception as exc:
        logger.error(f"Gateway chat failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Gateway chat failed: {exc}")


@router.post("/ai/gateway/complete")
async def gateway_complete_endpoint(payload: GatewayCompleteRequest, x_license_key: Optional[str] = Header(default=None)):
    _require_license(x_license_key)

    bedrock = get_bedrock_runtime_client()

    # Use Nova message format with a single user prompt.
    body = {
        "messages": [{"role": "user", "content": [{"text": payload.prompt}]}],
        "inferenceConfig": {
            "maxTokens": int(payload.max_tokens),
            "temperature": float(payload.temperature),
        },
    }

    try:
        response = bedrock.invoke_model(
            modelId=payload.model or "amazon.nova-lite-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        result = json.loads(response["body"].read())
        text = result["output"]["message"]["content"][0]["text"].strip()
        return {
            "text": text,
            "model": payload.model,
            "provider": "bedrock",
        }
    except (NoCredentialsError, PartialCredentialsError, ProfileNotFound) as exc:
        if _offline_ai_enabled():
            return {
                "text": (
                    "Offline AI mode is active for local testing (no AWS credentials configured on gateway). "
                    "Deploy the gateway with an IAM role/credentials to enable real AI."
                ),
                "model": payload.model,
                "provider": "offline_local",
            }
        raise HTTPException(status_code=503, detail=f"AWS credentials not configured on gateway: {exc}")
    except Exception as exc:
        logger.error(f"Gateway completion failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Gateway completion failed: {exc}")
