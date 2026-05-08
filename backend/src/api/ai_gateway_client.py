from __future__ import annotations

import os
import time
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


def gateway_post_json(path: str, payload: dict[str, Any], timeout_seconds: float = 60.0, _max_retries: int = 4) -> Any:
    """POST JSON to the gateway with aggressive retry on transient errors.

    The hosted gateway sits behind AWS API Gateway + Lambda + Bedrock. Each of
    these can return transient 5xx / connection errors during cold starts,
    Bedrock throttling, or brief Lambda issues. We retry on:
      - Connection errors (DNS, network, TLS)
      - Read timeouts
      - 500, 502, 503, 504 responses
    Total attempts = _max_retries + 1 (default 5). Backoff is exponential
    starting from 1.5s. Worst-case wait sequence: 1.5s, 3s, 4.5s, 6s = 15s.
    """
    base = get_gateway_base_url()
    url = f"{base}{path}"
    last_exc: AIGatewayError = AIGatewayError("No attempts made")

    retryable_status = {500, 502, 503, 504}

    for attempt in range(_max_retries + 1):
        if attempt > 0:
            wait = 1.5 * attempt
            logger.info(
                f"Gateway retry {attempt}/{_max_retries} after transient error — waiting {wait}s..."
            )
            time.sleep(wait)

        try:
            resp = requests.post(url, json=payload, headers=_build_headers(), timeout=timeout_seconds)
        except requests.exceptions.Timeout as exc:
            last_exc = AIGatewayError(f"Gateway timeout: {exc}")
            logger.warning(f"Gateway timeout on attempt {attempt + 1}, will retry...")
            continue
        except requests.exceptions.ConnectionError as exc:
            last_exc = AIGatewayError(f"Gateway connection error: {exc}")
            logger.warning(f"Gateway connection error on attempt {attempt + 1}, will retry...")
            continue
        except Exception as exc:
            last_exc = AIGatewayError(f"Gateway request failed: {exc}")
            logger.warning(f"Gateway request error on attempt {attempt + 1}: {exc}")
            continue

        if resp.status_code in retryable_status:
            last_exc = AIGatewayError(
                f"Gateway error {resp.status_code}: {resp.text[:300]}"
            )
            logger.warning(
                f"Gateway returned {resp.status_code} on attempt {attempt + 1}/{_max_retries + 1}, will retry..."
            )
            continue

        if resp.status_code >= 400:
            raise AIGatewayError(f"Gateway error {resp.status_code}: {resp.text[:500]}")

        try:
            return resp.json()
        except Exception:
            return resp.text

    logger.error(f"Gateway exhausted all {_max_retries + 1} attempts: {last_exc}")
    raise last_exc


def gateway_health(timeout_seconds: float = 10.0) -> dict[str, Any]:
    try:
        data = gateway_post_json("/api/v1/ai/gateway/health", payload={}, timeout_seconds=timeout_seconds)
        if isinstance(data, dict):
            return data
        return {"status": "ok", "message": str(data)}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def gateway_chat(messages: list[dict[str, str]], model: str, temperature: float, max_tokens: int) -> str:
    # Cap max_tokens at 600 to keep total Lambda execution well under timeout
    # window (the hosted gateway runs on AWS Lambda which has a hard execution
    # limit; large generations can intermittently fail with 500).
    safe_max_tokens = min(max_tokens, 600) if max_tokens > 0 else 600

    payload = {
        "messages": messages,
        "model": model,
        "temperature": temperature,
        "max_tokens": safe_max_tokens,
    }

    data = gateway_post_json("/api/v1/ai/gateway/chat", payload)
    text = _extract_text_from_gateway_response(data)
    if not text.strip():
        logger.warning(f"Gateway chat returned empty response: {data}")
    return text


def gateway_complete(prompt: str, model: str, temperature: float, max_tokens: int) -> str:
    # Use /chat with a single user message — avoids depending on a separate /complete
    # endpoint that may not exist on all gateway deployments.
    return gateway_chat(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
