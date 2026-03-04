"""
Dashboard Module — Administration & Overview
==============================================

Includes:
- Overview stats, recent activity
- Sample management (list, view, delete)
- Job queue monitoring
- Alert management
- User management (auth)
- DB backup/restore

Default port: 8004
"""

from modules.base import create_module_app
from src.api.config import get_settings

settings = get_settings()

app = create_module_app(
    module_name="dashboard",
    module_title="Dashboard",
    module_description="Administration dashboard — sample management, job monitoring, alerts, backups.",
)

# ---- Module-specific routers ----

from src.api.routers import samples, jobs, alerts, backup

# Sample list & management
app.include_router(
    samples.router,
    prefix=f"{settings.api_prefix}/samples",
    tags=["Samples"]
)

# Job queue
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

# DB Backup & Restore
app.include_router(
    backup.router,
    prefix=f"{settings.api_prefix}",
    tags=["Database"]
)
