from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from routers.tem_routes import router as tem_router
from routers.western_routes import router as western_router
from services.western.western_model import WesternBlot
from services.tem.tem_service import Base, engine
import os
import sys
MODULE_PROFILE = os.getenv("MODULE_PROFILE", "tem_wb")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bio Analysis Platform")


@app.get("/health")
def health():
    """Electron polls this endpoint before loading the frontend.
    Returns 200 only after uvicorn is fully started and all routes are mounted."""
    return {"status": "ok"}

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base directory for source files
BASE_DIR = Path(__file__).resolve().parent

# In frozen (EXE) mode Electron sets cwd to app.getPath('userData') — the writable
# location where services save uploads/results. In dev mode cwd == backend/, so
# BASE_DIR and cwd agree. Must match the logic in tem_service.py / western_service.py.
if getattr(sys, 'frozen', False):
    _data_root = Path(os.getcwd())
else:
    _data_root = BASE_DIR

# Ensure directories exist before mounting (first launch may have empty userData)
for _d in ["uploads/tem", "uploads/western", "results/tem", "results/western"]:
    (_data_root / _d).mkdir(parents=True, exist_ok=True)

# Static folders — serve from the writable data root so uploaded files are visible
app.mount(
    "/uploads",
    StaticFiles(directory=_data_root / "uploads"),
    name="uploads"
)

app.mount(
    "/results",
    StaticFiles(directory=_data_root / "results"),
    name="results"
)

# Routers
# Routers — gated by MODULE_PROFILE
if MODULE_PROFILE in ["tem_wb", "full"]:
    app.include_router(tem_router, prefix="/tem", tags=["TEM"])
    app.include_router(western_router, prefix="/western", tags=["Western"])