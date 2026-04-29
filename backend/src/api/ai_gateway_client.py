from __future__ import annotations

import os
from typing import Any, Optional

import requests
from loguru import logger


class AIGatewayError(RuntimeError):
    pass


def _strip_trailing_slash(url: str) -> str:
    return url[:-1] if url.endswith("/") else url


def get_gateway_base_url() -> str:
    base = (os.getenv("CRMIT_AI_GATEWAY_URL") or "").strip()
    if not base:
        raise AIGatewayError("CRMIT_AI_GATEWAY_URL is not set")
    return _strip_trailing_slash(base)


def get_gateway_license_key() -> str:
    return (os.getenv("CRMIT_AI_GATEWAY_LICENSE_KEY") or os.getenv("CRMIT_LICENSE_KEY") or "").strip()


def _extract_text_from_gateway_response(data: Any) -> str:
    """Best-effort extraction from common response shapes."""
    if isinstance(data, str):
        return data

    if not isinstance(data, dict):
        return str(data)

    for key in ("content", "text", "message", "answer", "output"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    # OpenAI-like
    try:
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message")
            if isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
    except Exception:
        pass

    # Bedrock Nova-like
    try:
        output = data.get("output")
        if isinstance(output, dict):
            message = output.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, list) and content:
                    text = content[0].get("text")
                    if isinstance(text, str) and text.strip():
                        return text.strip()
    except Exception:
        pass

    return str(data)


def _build_headers() -> dict[str, str]:
    headers: dict[str, str] = {
        "Content-Type": "application/json",
    }
    license_key = get_gateway_license_key()
    if license_key:
        headers["X-License-Key"] = license_key
    return headers


def gateway_post_json(path: str, payload: dict[str, Any], timeout_seconds: float = 60.0) -> Any:
    base = get_gateway_base_url()
    url = f"{base}{path}"
    try:
        resp = requests.post(url, json=payload, headers=_build_headers(), timeout=timeout_seconds)
    except Exception as exc:
        raise AIGatewayError(f"Gateway request failed: {exc}") from exc

    if resp.status_code >= 400:
        raise AIGatewayError(f"Gateway error {resp.status_code}: {resp.text[:500]}")

    try:
        return resp.json()
    except Exception:
        return resp.text


def gateway_health(timeout_seconds: float = 10.0) -> dict[str, Any]:
    try:
        data = gateway_post_json("/api/v1/ai/gateway/health", payload={}, timeout_seconds=timeout_seconds)
        if isinstance(data, dict):
            return data
        return {"status": "ok", "message": str(data)}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def gateway_chat(messages: list[dict[str, str]], model: str, temperature: float, max_tokens: int) -> str:
    payload = {
        "messages": messages,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    data = gateway_post_json("/api/v1/ai/gateway/chat", payload)
    text = _extract_text_from_gateway_response(data)
    if not text.strip():
        logger.warning(f"Gateway chat returned empty response: {data}")
    return text


def gateway_complete(prompt: str, model: str, temperature: float, max_tokens: int) -> str:
    payload = {
        "prompt": prompt,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    data = gateway_post_json("/api/v1/ai/gateway/complete", payload)
    text = _extract_text_from_gateway_response(data)
    if not text.strip():
        logger.warning(f"Gateway completion returned empty response: {data}")
    return text
