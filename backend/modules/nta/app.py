"""
NTA Module — Nanoparticle Tracking Analysis
=============================================

Includes:
- NTA text/PDF file upload & processing
- Size distribution, concentration profiles
- Temperature/viscosity corrections (Stokes-Einstein)
- NTA metadata display
- Sample management (NTA-related)
- Dashboard (read-only overview)

Default port: 8002
"""

from modules.base import create_module_app
from src.api.config import get_settings

settings = get_settings()

app = create_module_app(
    module_name="nta",
    module_title="NTA Analysis",
    module_description="Nanoparticle Tracking Analysis — Upload NTA text/PDF files, view size distributions and concentration profiles.",
)

# ---- Module-specific routers ----

from src.api.routers import upload, samples, jobs, alerts, backup

# NTA upload
app.include_router(
    upload.router,
    prefix=f"{settings.api_prefix}/upload",
    tags=["Upload"]
)

# Sample endpoints (includes NTA metadata, NTA values, etc.)
app.include_router(
    samples.router,
    prefix=f"{settings.api_prefix}/samples",
    tags=["Samples"]
)

# Processing jobs
app.include_router(
    jobs.router,
    prefix=f"{settings.api_prefix}/jobs",
    tags=["Jobs"]
)

# Alerts
app.include_router(
    alerts.router,
    prefix=f"{settings.api_prefix}/alerts",
    tags=["Alerts"]
)

# DB Backup
app.include_router(
    backup.router,
    prefix=f"{settings.api_prefix}",
    tags=["Database"]
)
