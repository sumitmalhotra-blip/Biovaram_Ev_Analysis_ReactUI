from __future__ import annotations

import os
from typing import Any, Optional

import boto3


def get_aws_region(default: str = "us-east-1") -> str:
    return (os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or default).strip() or default


def get_bedrock_runtime_client() -> Any:
    """Create a Bedrock Runtime client using AWS' default credential chain.

    Credential sources (in order, simplified):
    - Env vars (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY)
    - Shared config (~/.aws/credentials) optionally via AWS_PROFILE
    - IAM role credentials (ECS/EC2/Lambda)

    This function intentionally does NOT accept or pass raw keys.
    """

    region = get_aws_region()
    profile = (os.getenv("AWS_PROFILE") or "").strip()

    if profile:
        session = boto3.Session(profile_name=profile)
        return session.client("bedrock-runtime", region_name=region)

    # Default: let boto3 resolve credentials (env vars, instance/task role, etc.)
    return boto3.client("bedrock-runtime", region_name=region)


def is_aws_credential_configured() -> bool:
    """Best-effort check for whether AWS credentials *might* be available.

    This is intentionally conservative: IAM role credentials won't show up in env vars.
    The definitive check is to call Bedrock and handle failures.
    """

    if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
        return True
    if os.getenv("AWS_PROFILE"):
        return True
    # IAM role credentials are dynamic; return False here and rely on call-time behavior.
    return False
