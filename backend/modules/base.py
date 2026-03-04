"""
Module Base — Shared FastAPI App Factory
=========================================

Creates a FastAPI application pre-configured with:
- CORS middleware
- GZip compression
- Request logging
- Exception handlers
- Health endpoint
- Auth router (all modules need auth)
- Database lifespan (init + default user + cleanup)

Each module calls `create_module_app()` and then includes
only the routers it needs.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import sys
import time

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger

from src.api.config import get_settings
from src.database.connection import init_database, close_connections, check_connection

settings = get_settings()


async def _ensure_default_user():
    """Create default desktop user on first run (shared across all modules)."""
    from src.database.connection import get_session_factory
    from src.database.models import User
    from sqlalchemy import select

    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(User).where(User.email == "lab@biovaram.local")
            )
            existing = result.scalar_one_or_none()

            if existing is None:
                import bcrypt
                default_password = bcrypt.hashpw(
                    "desktop_user_2026".encode("utf-8"),
                    bcrypt.gensalt()
                ).decode("utf-8")

                desktop_user = User(
                    email="lab@biovaram.local",
                    password_hash=default_password,
                    name="Lab User",
                    role="researcher",
                    organization="BioVaram Lab",
                    is_active=True,
                    email_verified=True,
                )
                session.add(desktop_user)
                await session.commit()
                logger.info("   Default desktop user created: lab@biovaram.local")
            else:
                logger.info("   Default desktop user exists: lab@biovaram.local")
    except Exception as e:
        logger.warning(f"   Could not create default user: {e}")


def create_module_app(
    module_name: str,
    module_title: str,
    module_description: str = "",
    module_version: str = "1.0.0",
) -> FastAPI:
    """
    Create a FastAPI app for a specific module with shared middleware and lifespan.
    
    Args:
        module_name: Short identifier (e.g. "nanofacs", "nta")
        module_title: Human-readable title for API docs
        module_description: Description shown in /docs
        module_version: Version string
        
    Returns:
        Configured FastAPI application — add module-specific routers after this.
    """
    
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logger.info(f"🚀 BioVaram {module_title} starting up...")
        logger.info(f"   Module: {module_name}")
        logger.info(f"   Environment: {settings.environment}")
        
        try:
            await init_database()
            logger.info("   Database: Connection pool initialized")
            await _ensure_default_user()
        except Exception as e:
            logger.warning(f"   Database: Failed to initialize - {e}")
        
        logger.success(f"✅ BioVaram {module_title} ready")
        yield
        
        logger.info(f"🛑 BioVaram {module_title} shutting down...")
        try:
            await close_connections()
            logger.info("   Database connections closed")
        except Exception as e:
            logger.warning(f"   Error closing database: {e}")
        logger.success("✅ Cleanup complete")
    
    app = FastAPI(
        title=f"BioVaram {module_title}",
        version=module_version,
        description=module_description or f"BioVaram {module_title} — Module API",
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        lifespan=lifespan,
    )
    
    # ---- Middleware ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=3600,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = (time.time() - start_time) * 1000
        logger.info(
            f"  {request.method} {request.url.path} → {response.status_code} ({duration:.1f}ms)"
        )
        return response
    
    # ---- Exception Handlers ----
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            errors.append({
                "field": " -> ".join(str(x) for x in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"success": False, "error": "Validation error", "details": errors}
        )
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception on {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "Internal server error",
                "message": str(exc) if settings.debug else "An error occurred",
            }
        )
    
    # ---- Health Endpoint (all modules) ----
    @app.api_route("/health", methods=["GET", "OPTIONS"])
    @app.api_route(f"{settings.api_prefix}/health", methods=["GET", "OPTIONS"])
    async def health_check():
        return {
            "status": "healthy",
            "service": f"BioVaram {module_title}",
            "module": module_name,
            "version": module_version,
            "environment": settings.environment,
            "desktop_mode": getattr(sys, 'frozen', False),
        }
    
    @app.get(f"{settings.api_prefix}/status")
    async def system_status():
        try:
            db_connected = await check_connection()
            db_status = "connected" if db_connected else "disconnected"
        except Exception:
            db_status = "error"
        return {
            "success": True,
            "service": f"BioVaram {module_title}",
            "module": module_name,
            "version": module_version,
            "database": {"status": db_status},
        }
    
    # ---- Auth Router (all modules need login) ----
    from src.api.routers import auth
    app.include_router(
        auth.router,
        prefix=f"{settings.api_prefix}/auth",
        tags=["Authentication"]
    )
    
    return app
