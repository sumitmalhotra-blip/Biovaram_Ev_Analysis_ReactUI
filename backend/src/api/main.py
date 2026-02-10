"""
FastAPI Main Application
=========================

CRMIT REST API for exosome/EV analysis platform.

Endpoints:
- GET  /               - Root redirect to docs
- GET  /health         - Health check
- GET  /api/v1/status  - System status
- POST /api/v1/upload/fcs  - Upload FCS file
- POST /api/v1/upload/nta  - Upload NTA file
- GET  /api/v1/samples     - List all samples
- GET  /api/v1/samples/{id} - Get sample details
- GET  /api/v1/jobs/{id}   - Get processing job status
- POST /api/v1/process     - Trigger batch processing

Author: CRMIT Backend Team
Date: November 21, 2025
Version: 1.0.0
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger
import time

from src.api.config import get_settings
from src.api.routers import upload, samples, jobs  # type: ignore[import-not-found]
from src.api.routers import analysis  # type: ignore[import-not-found]
from src.api.routers import auth  # type: ignore[import-not-found]
from src.api.routers import alerts  # CRMIT-003: Alert System
try:
    from src.api.routers import calibration as calibration_router  # CAL-001
    _has_calibration_router = True
except ImportError:
    _has_calibration_router = False
from src.database.connection import init_database, close_connections, check_connection

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # type: ignore[misc]
    """
    Lifespan context manager for startup and shutdown events.
    
    Handles:
    - Database connection initialization
    - Logger configuration
    - Cleanup on shutdown
    """
    # Startup
    logger.info("🚀 CRMIT API starting up...")
    logger.info(f"   Environment: {settings.environment}")
    logger.info(f"   Upload directory: {settings.upload_dir}")
    logger.info(f"   Parquet directory: {settings.parquet_dir}")
    
    # Initialize database connection pool
    try:
        await init_database()
        logger.info("   Database: Connection pool initialized")
    except Exception as e:
        logger.warning(f"   Database: Failed to initialize - {e}")
        logger.warning("   API will continue without database (file-based mode)")
    
    logger.success("✅ CRMIT API ready")
    
    yield
    
    # Shutdown
    logger.info("🛑 CRMIT API shutting down...")
    # Close database connections
    try:
        await close_connections()
        logger.info("   Database connections closed")
    except Exception as e:
        logger.warning(f"   Error closing database: {e}")
    logger.success("✅ Cleanup complete")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="REST API for extracellular vesicle (EV) analysis platform",
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    lifespan=lifespan,
)


# ============================================================================
# Middleware
# ============================================================================

# CORS - Allow frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# GZip compression for responses > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing."""
    start_time = time.time()
    
    # Log request
    logger.info(f"⬇️  {request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    duration = (time.time() - start_time) * 1000
    logger.info(
        f"⬆️  {request.method} {request.url.path} "
        f"→ {response.status_code} ({duration:.1f}ms)"
    )
    
    return response


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    
    logger.warning(f"Validation error on {request.url.path}: {errors}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Validation error",
            "details": errors,
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler."""
    logger.exception(f"Unhandled exception on {request.url.path}: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An error occurred",
        }
    )


# ============================================================================
# Root Endpoints
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API documentation."""
    return RedirectResponse(url=settings.docs_url)


@app.api_route("/health", methods=["GET", "OPTIONS"])
@app.api_route(f"{settings.api_prefix}/health", methods=["GET", "OPTIONS"])
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    Handles both GET and OPTIONS (CORS preflight) requests.
    Available at both /health and /api/v1/health for compatibility.
    
    Returns:
        Health status with system info
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get(f"{settings.api_prefix}/status")
async def system_status():
    """
    Detailed system status including database and storage.
    
    Returns:
        System status with diagnostics
    """
    # Check database connection
    try:
        db_connected = await check_connection()
        db_status = "connected" if db_connected else "disconnected"
    except Exception:
        db_status = "error"
    
    # Check storage
    upload_dir_exists = settings.upload_dir.exists()
    parquet_dir_exists = settings.parquet_dir.exists()
    
    return {
        "success": True,
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "database": {
            "status": db_status,
            # "url": settings.database_url.split("@")[-1],  # Hide credentials
        },
        "storage": {
            "upload_dir": str(settings.upload_dir),
            "upload_dir_exists": upload_dir_exists,
            "parquet_dir": str(settings.parquet_dir),
            "parquet_dir_exists": parquet_dir_exists,
        },
        "configuration": {
            "max_upload_size_mb": settings.max_upload_size_mb,
            "max_workers": settings.max_workers,
            "task_timeout_seconds": settings.task_timeout_seconds,
        }
    }


# ============================================================================
# API Routers
# ============================================================================

app.include_router(
    upload.router,
    prefix=f"{settings.api_prefix}/upload",
    tags=["Upload"]
)

app.include_router(
    samples.router,
    prefix=f"{settings.api_prefix}/samples",
    tags=["Samples"]
)

app.include_router(
    jobs.router,
    prefix=f"{settings.api_prefix}/jobs",
    tags=["Jobs"]
)

app.include_router(
    analysis.router,
    prefix=f"{settings.api_prefix}/analysis",
    tags=["Analysis"]
)

app.include_router(
    auth.router,
    prefix=f"{settings.api_prefix}/auth",
    tags=["Authentication"]
)

# CRMIT-003: Alert System
app.include_router(
    alerts.router,
    prefix=f"{settings.api_prefix}/alerts",
    tags=["Alerts"]
)

# CAL-001: Bead Calibration (Feb 10, 2026)
if _has_calibration_router:
    app.include_router(
        calibration_router.router,
        prefix=f"{settings.api_prefix}/calibration",
        tags=["Calibration"]
    )


# ============================================================================
# Main Entry Point (Development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn  # type: ignore[import-not-found]
    
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Docs: http://localhost:8000{settings.docs_url}")
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info",
        access_log=True,
    )
