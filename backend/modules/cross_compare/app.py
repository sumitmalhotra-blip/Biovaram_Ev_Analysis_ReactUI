"""
Cross-Compare Module — FCS vs NTA Validation
===============================================

Includes:
- Cross-validation of FCS and NTA results
- Overlay histograms, statistical tests
- Distribution comparison, validation verdict
- Sample management (read-only, cross-module data)
- Analysis endpoints (statistical tests)
- Dashboard (read-only overview)

Depends on: NanoFACS + NTA data in the shared database

Default port: 8003
"""

from modules.base import create_module_app
from src.api.config import get_settings

settings = get_settings()

app = create_module_app(
    module_name="cross_compare",
    module_title="Cross-Compare",
    module_description="Cross-validation of FCS vs NTA results — overlay histograms, statistical tests, distribution comparison.",
)

# ---- Module-specific routers ----

from src.api.routers import samples, analysis, jobs, alerts, backup

# Sample endpoints (includes cross-validate, FCS + NTA data access)
app.include_router(
    samples.router,
    prefix=f"{settings.api_prefix}/samples",
    tags=["Samples"]
)

# Analysis endpoints (statistical tests, distribution comparison)
app.include_router(
    analysis.router,
    prefix=f"{settings.api_prefix}/analysis",
    tags=["Analysis"]
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
