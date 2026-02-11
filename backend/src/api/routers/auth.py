"""
Authentication Router
=====================

Endpoints for user authentication and registration.

Endpoints:
- POST /auth/register          - Register new user
- POST /auth/login             - Login and get token
- GET  /auth/me                - Get current user profile
- PUT  /auth/profile           - Update user profile
- POST /auth/forgot-password   - Request password reset
- POST /auth/reset-password    - Reset password with token
- POST /auth/logout            - Logout (client-side token removal)

Author: CRMIT Backend Team
Date: December 26, 2025
"""

from datetime import datetime
from typing import Optional
import bcrypt
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from src.database.connection import get_session
from src.database.models import User
from src.api.auth_middleware import create_access_token, create_refresh_token

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class UserRegisterRequest(BaseModel):
    """Request body for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    name: str = Field(..., min_length=2, description="User's full name")
    organization: Optional[str] = Field(None, description="Organization name")
    role: Optional[str] = Field("user", description="User role (user, researcher, admin)")


class UserLoginRequest(BaseModel):
    """Request body for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserProfileUpdateRequest(BaseModel):
    """Request body for profile update."""
    name: Optional[str] = Field(None, min_length=2)
    organization: Optional[str] = Field(None)


class UserResponse(BaseModel):
    """User response model (excludes password)."""
    id: int
    email: str
    name: str
    role: str
    organization: Optional[str]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Authentication response with user data and JWT tokens."""
    success: bool
    message: str
    user: Optional[UserResponse] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


# ============================================================================
# Helper Functions
# ============================================================================

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/register", response_model=AuthResponse)
async def register_user(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Register a new user account.
    
    **Request Body:**
    ```json
    {
        "email": "user@example.com",
        "password": "securepassword123",
        "name": "John Doe",
        "organization": "BioVaram Labs"
    }
    ```
    
    **Response:**
    ```json
    {
        "success": true,
        "message": "User registered successfully",
        "user": {
            "id": 1,
            "email": "user@example.com",
            "name": "John Doe",
            "role": "user",
            ...
        }
    }
    ```
    """
    try:
        # Check if email already exists
        result = await db.execute(
            select(User).where(User.email == request.email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        password_hash = hash_password(request.password)
        
        # Validate role (only allow user and researcher for self-registration)
        allowed_roles = ["user", "researcher"]
        user_role = request.role if request.role in allowed_roles else "user"
        
        new_user = User(
            email=request.email,
            password_hash=password_hash,
            name=request.name,
            organization=request.organization,
            role=user_role,
            is_active=True,
            email_verified=False
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        logger.info(f"✅ New user registered: {request.email}")
        
        return AuthResponse(
            success=True,
            message="User registered successfully",
            user=UserResponse.model_validate(new_user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=AuthResponse)
async def login_user(
    request: UserLoginRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Authenticate user and return user data.
    
    **Request Body:**
    ```json
    {
        "email": "user@example.com",
        "password": "securepassword123"
    }
    ```
    
    **Response:**
    ```json
    {
        "success": true,
        "message": "Login successful",
        "user": {
            "id": 1,
            "email": "user@example.com",
            "name": "John Doe",
            "role": "user",
            ...
        }
    }
    ```
    """
    try:
        # Find user by email
        result = await db.execute(
            select(User).where(User.email == request.email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(request.password, str(user.password_hash)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not bool(user.is_active):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        # Update last login
        user.last_login = datetime.utcnow()  # type: ignore[assignment]
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"✅ User logged in: {request.email}")
        
        # Create JWT tokens
        token_data = {
            "sub": str(user.id),
            "email": str(user.email),
            "role": str(user.role or "user"),
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return AuthResponse(
            success=True,
            message="Login successful",
            user=UserResponse.model_validate(user),
            access_token=access_token,
            refresh_token=refresh_token,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/me/{user_id}", response_model=UserResponse)
async def get_current_user(
    user_id: int,
    db: AsyncSession = Depends(get_session)
):
    """
    Get current user profile by ID.
    
    **Path Parameters:**
    - user_id: User ID
    
    **Response:** User profile data
    """
    try:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse.model_validate(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}"
        )


@router.put("/profile/{user_id}", response_model=UserResponse)
async def update_profile(
    user_id: int,
    request: UserProfileUpdateRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Update user profile.
    
    **Path Parameters:**
    - user_id: User ID
    
    **Request Body:**
    ```json
    {
        "name": "New Name",
        "organization": "New Organization"
    }
    ```
    """
    try:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update fields
        if request.name is not None:
            user.name = request.name  # type: ignore[assignment]
        if request.organization is not None:
            user.organization = request.organization  # type: ignore[assignment]
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"✅ Profile updated for user: {user.email}")
        
        return UserResponse.model_validate(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Profile update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile update failed: {str(e)}"
        )


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    """
    List all users (admin only in production).
    
    **Query Parameters:**
    - skip: Number of records to skip
    - limit: Maximum records to return
    """
    try:
        result = await db.execute(
            select(User)
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        users = result.scalars().all()
        
        return [UserResponse.model_validate(user) for user in users]
        
    except Exception as e:
        logger.exception(f"❌ Failed to list users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )


# ============================================================================
# Password Reset Endpoints
# ============================================================================

# In-memory store for password reset tokens (use Redis in production)
_password_reset_tokens: dict[str, dict] = {}


class ForgotPasswordRequest(BaseModel):
    """Request body for forgot password."""
    email: EmailStr = Field(..., description="User email address")


class ResetPasswordRequest(BaseModel):
    """Request body for resetting password."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")


@router.post("/forgot-password", response_model=dict)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Request a password reset. Generates a token and logs it.

    In production, this should send an email with a reset link.
    For now, the token is stored in-memory and returned in server logs.

    **Request Body:**
    ```json
    { "email": "user@example.com" }
    ```

    **Response (always success to prevent email enumeration):**
    ```json
    { "success": true, "message": "If the email exists, a reset link has been sent." }
    ```
    """
    try:
        # Check if user exists (don't reveal whether email is registered)
        result = await db.execute(
            select(User).where(User.email == request.email)
        )
        user = result.scalar_one_or_none()

        if user:
            # Generate a secure reset token
            token = secrets.token_urlsafe(32)
            _password_reset_tokens[token] = {
                "user_id": user.id,
                "email": str(user.email),
                "created_at": datetime.utcnow(),
            }
            logger.info(
                f"🔑 Password reset requested for {request.email} — "
                f"token: {token[:8]}... (full token in debug log)"
            )
            logger.debug(f"🔑 Full reset token for {request.email}: {token}")
        else:
            logger.info(f"🔑 Password reset requested for unknown email: {request.email}")

        # Always return success to prevent email enumeration
        return {
            "success": True,
            "message": "If the email exists, a reset link has been sent.",
        }

    except Exception as e:
        logger.exception(f"❌ Forgot password failed: {e}")
        # Still return success for security
        return {
            "success": True,
            "message": "If the email exists, a reset link has been sent.",
        }


@router.post("/reset-password", response_model=dict)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Reset a user's password using a valid reset token.

    **Request Body:**
    ```json
    { "token": "abc123...", "new_password": "newsecurepassword123" }
    ```
    """
    try:
        token_data = _password_reset_tokens.get(request.token)

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        # Check token age (expire after 1 hour)
        from datetime import timedelta
        age = datetime.utcnow() - token_data["created_at"]
        if age > timedelta(hours=1):
            del _password_reset_tokens[request.token]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired. Please request a new one.",
            )

        # Find user
        result = await db.execute(
            select(User).where(User.id == token_data["user_id"])
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Update password
        new_hash = hash_password(request.new_password)
        user.password_hash = new_hash  # type: ignore[assignment]
        await db.commit()

        # Invalidate token
        del _password_reset_tokens[request.token]

        logger.info(f"✅ Password reset successful for {token_data['email']}")

        return {
            "success": True,
            "message": "Password has been reset successfully. You can now log in.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Password reset failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset failed: {str(e)}",
        )
