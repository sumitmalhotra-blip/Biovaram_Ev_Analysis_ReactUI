"""
Full Platform Module — All Features
=====================================

Includes all routers — equivalent to the main app.
Used for the full-platform desktop EXE.

Default port: 8000
"""

from modules.base import create_module_app
from src.api.config import get_settings

settings = get_settings()

app = create_module_app(
    module_name="full",
    module_title="EV Analysis Platform",
    module_description="Complete EV Analysis Platform — NanoFACS, NTA, Cross-Compare, Dashboard, AI Chat.",
)

# ---- All routers ----

from src.api.routers import upload, samples, jobs, analysis, alerts, chat, backup

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
    alerts.router,
    prefix=f"{settings.api_prefix}/alerts",
    tags=["Alerts"]
)

app.include_router(
    chat.router,
    prefix=f"{settings.api_prefix}",
    tags=["AI Chat"]
)

app.include_router(
    backup.router,
    prefix=f"{settings.api_prefix}",
    tags=["Database"]
)

# Calibration (optional)
try:
    from src.api.routers import calibration as calibration_router
    app.include_router(
        calibration_router.router,
        prefix=f"{settings.api_prefix}/calibration",
        tags=["Calibration"]
    )
except ImportError:
    pass
