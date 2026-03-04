"""
NanoFACS Module — Flow Cytometry Analysis
==========================================

Includes:
- FCS file upload & processing
- Scatter plots, size distribution, anomaly detection
- Bead calibration (Mie theory sizing)
- Population shift analysis
- Sample management (FCS-related)
- Dashboard (read-only overview)

Default port: 8001
"""

from modules.base import create_module_app
from src.api.config import get_settings

settings = get_settings()

app = create_module_app(
    module_name="nanofacs",
    module_title="NanoFACS",
    module_description="Flow Cytometry EV Analysis — Upload FCS files, run Mie sizing, view scatter plots and size distributions.",
)

# ---- Module-specific routers ----

from src.api.routers import upload, samples, jobs, alerts, backup

# FCS upload (the upload router handles both FCS and NTA; only FCS will be
# called from the NanoFACS frontend build, but including the full router
# is harmless and avoids risky code splitting)
app.include_router(
    upload.router,
    prefix=f"{settings.api_prefix}/upload",
    tags=["Upload"]
)

# Sample endpoints (includes FCS scatter-data, size-bins, distribution, etc.)
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

# Calibration (optional — may not be installed in all environments)
try:
    from src.api.routers import calibration as calibration_router
    app.include_router(
        calibration_router.router,
        prefix=f"{settings.api_prefix}/calibration",
        tags=["Calibration"]
    )
except ImportError:
    pass
