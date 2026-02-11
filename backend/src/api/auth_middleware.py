"""
JWT Authentication Middleware
=============================

Provides JWT token creation, verification, and FastAPI dependency
functions for protecting routes.

Usage:
    # Required auth (raises 401 if no valid token)
    @router.delete("/samples/{sample_id}")
    async def delete_sample(
        sample_id: int,
        current_user: dict = Depends(require_auth),
        db: AsyncSession = Depends(get_session)
    ):

    # Optional auth (returns None if no token)
    @router.get("/samples")
    async def list_samples(
        current_user: dict | None = Depends(optional_auth),
        db: AsyncSession = Depends(get_session)
    ):

Author: CRMIT Backend Team
Date: January 2026
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt  # type: ignore[import-untyped]
from loguru import logger

from src.api.config import get_settings

# Security scheme — auto_error=False so optional_auth doesn't raise
_bearer_scheme = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"


# ============================================================================
# Token Creation
# ============================================================================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        data: Claims to encode (should include 'sub' for user ID).
        expires_delta: Custom expiry; defaults to settings.access_token_expire_minutes.

    Returns:
        Encoded JWT string.
    """
    settings = get_settings()
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})

    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a longer-lived refresh token."""
    settings = get_settings()
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(days=settings.refresh_token_expire_days)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"})

    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


# ============================================================================
# Token Verification
# ============================================================================

def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Raises:
        JWTError: If the token is invalid or expired.
    """
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


# ============================================================================
# FastAPI Dependencies
# ============================================================================

async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> dict:
    """
    Dependency that **requires** a valid JWT Bearer token.
    Returns the decoded token payload as a dict.

    Raises 401 if missing or invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[dict]:
    """
    Dependency that **optionally** reads a JWT Bearer token.
    Returns decoded payload if present and valid, or None otherwise.
    """
    if credentials is None:
        return None

    try:
        payload = decode_token(credentials.credentials)
        return payload if payload.get("sub") else None
    except JWTError:
        return None
