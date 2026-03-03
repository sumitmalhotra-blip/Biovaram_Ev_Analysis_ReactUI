# -*- mode: python ; coding: utf-8 -*-
"""
BioVaram EV Analysis Platform — PyInstaller Spec File
======================================================

Builds a single-folder distribution containing:
  - BioVaram.exe          (entry point: run_desktop.py)
  - frontend/             (static Next.js build from out/)
  - config/               (bead standards + calibration defaults)
  - All Python dependencies bundled

Build command (run from project root):
    pyinstaller packaging/biovaram.spec --noconfirm

Output will be in: dist/BioVaram/
"""

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# =============================================================================
# Path Configuration
# =============================================================================

# SPECPATH is set by PyInstaller to the directory containing the spec file
# This spec file lives in packaging/, project root is one level up
SPEC_DIR = SPECPATH  # e.g. C:\...\ev-analysis-platform\packaging
PROJECT_ROOT = os.path.dirname(SPEC_DIR)  # e.g. C:\...\ev-analysis-platform
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'backend')
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'out')
CONFIG_DIR = os.path.join(BACKEND_DIR, 'config')

print(f"[BioVaram Build] Project root: {PROJECT_ROOT}")
print(f"[BioVaram Build] Backend dir:  {BACKEND_DIR}")
print(f"[BioVaram Build] Frontend dir: {FRONTEND_DIR}")
print(f"[BioVaram Build] Config dir:   {CONFIG_DIR}")

# =============================================================================
# Hidden Imports
# =============================================================================
# PyInstaller cannot detect dynamic imports used by FastAPI, uvicorn,
# SQLAlchemy async, and scientific libraries. We list them explicitly.

hidden_imports = []

# --- FastAPI / Starlette / Uvicorn ---
hidden_imports += collect_submodules('uvicorn')
hidden_imports += [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.http.httptools_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.wsproto_impl',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'fastapi',
    'fastapi.routing',
    'fastapi.middleware',
    'fastapi.middleware.cors',
    'fastapi.staticfiles',
    'fastapi.responses',
    'fastapi.exceptions',
    'starlette',
    'starlette.routing',
    'starlette.middleware',
    'starlette.staticfiles',
    'starlette.responses',
    'starlette.exceptions',
    'starlette.middleware.gzip',
    'anyio',
    'anyio._backends',
    'anyio._backends._asyncio',
]

# --- Pydantic ---
hidden_imports += [
    'pydantic',
    'pydantic.deprecated',
    'pydantic.deprecated.decorator',
    'pydantic_settings',
    'pydantic_core',
    'annotated_types',
    'email_validator',
]

# --- SQLAlchemy (async + SQLite) ---
hidden_imports += [
    'sqlalchemy',
    'sqlalchemy.ext.asyncio',
    'sqlalchemy.dialects.sqlite',
    'sqlalchemy.dialects.sqlite.aiosqlite',
    'sqlalchemy.pool',
    'aiosqlite',
    'alembic',
]

# --- Scientific / Data Libraries ---
hidden_imports += [
    'numpy',
    'numpy.core',
    'scipy',
    'scipy.special',
    'scipy.special.cython_special',
    'scipy.optimize',
    'scipy.interpolate',
    'scipy.stats',
    'scipy.signal',
    'pandas',
    'pandas.io.formats.style',
    'pyarrow',
    'pyarrow.parquet',
    'miepython',
    'sklearn',
    'sklearn.cluster',
    'sklearn.mixture',
    'sklearn.preprocessing',
]

# --- FCS / Flow Cytometry ---
hidden_imports += [
    'flowio',
    'fcsparser',
]

# --- PDF Parsing ---
hidden_imports += [
    'pdfplumber',
]

# --- Visualization ---
# NOTE: matplotlib, seaborn, plotly are EXCLUDED to save ~25 MB
# They are only used in legacy/ visualization code, not by the desktop API
# All frontend charts use client-side Recharts

# --- Utilities ---
hidden_imports += [
    'loguru',
    'bcrypt',
    'jose',
    'python_jose',
    'colorama',
    'tqdm',
    'dotenv',
    'multipart',
    'requests',
]

# --- Our own source packages ---
hidden_imports += [
    'src',
    'src.api',
    'src.api.config',
    'src.api.main',
    'src.api.cache',
    'src.api.auth_middleware',
    'src.api.routers',
    'src.api.routers.upload',
    'src.api.routers.samples',
    'src.api.routers.jobs',
    'src.api.routers.analysis',
    'src.api.routers.auth',
    'src.api.routers.alerts',
    'src.api.routers.calibration',
    'src.database',
    'src.database.connection',
    'src.database.crud',
    'src.database.models',
    'src.parsers',
    'src.parsers.fcs_parser',
    'src.parsers.nta_parser',
    'src.parsers.nta_pdf_parser',
    'src.parsers.parquet_writer',
    'src.parsers.bead_datasheet_parser',
    'src.parsers.base_parser',
    'src.physics',
    'src.physics.mie_scatter',
    'src.physics.bead_calibration',
    'src.physics.nta_corrections',
    'src.physics.size_config',
    'src.physics.size_distribution',
    'src.physics.statistics_utils',
    'src.analysis',
    'src.analysis.population_shift',
    'src.analysis.temporal_analysis',
    'src.utils',
    'src.utils.channel_config',
    'src.visualization',
    'src.visualization.auto_axis_selector',
    # NOTE: Legacy modules excluded — they import matplotlib/seaborn/plotly
    # which are excluded from the bundle to save ~130 MB. The API never
    # imports from src.legacy, so this is safe.
    'src.api.routers.chat',
    'src.api.routers.backup',
    'httpx',
    'httpx._transports',
    'httpx._transports.default',
    'httpcore',
]

# De-duplicate
hidden_imports = list(set(hidden_imports))

# =============================================================================
# Data Files (non-Python assets to bundle)
# =============================================================================

datas = []

# --- Static frontend (Next.js build output) ---
if os.path.isdir(FRONTEND_DIR):
    datas.append((FRONTEND_DIR, 'frontend'))
    print(f"[BioVaram Build] OK - Frontend directory found: {FRONTEND_DIR}")
else:
    print(f"[BioVaram Build] WARN - Frontend not found at {FRONTEND_DIR}")
    print(f"[BioVaram Build]    Run 'pnpm build' first to generate the static frontend.")

# --- Config files (bead standards, calibration defaults) ---
if os.path.isdir(CONFIG_DIR):
    datas.append((CONFIG_DIR, 'config'))
    print(f"[BioVaram Build] OK - Config directory found: {CONFIG_DIR}")
else:
    print(f"[BioVaram Build] WARN - Config not found at {CONFIG_DIR}")

# --- Backend source (as package data, needed for sys.path resolution) ---
BACKEND_SRC = os.path.join(BACKEND_DIR, 'src')
if os.path.isdir(BACKEND_SRC):
    datas.append((BACKEND_SRC, 'src'))
    print(f"[BioVaram Build] OK - Backend source found: {BACKEND_SRC}")

# --- Alembic migrations (for future database upgrades) ---
ALEMBIC_DIR = os.path.join(BACKEND_DIR, 'alembic')
if os.path.isdir(ALEMBIC_DIR):
    datas.append((ALEMBIC_DIR, 'alembic'))
    datas.append((os.path.join(BACKEND_DIR, 'alembic.ini'), '.'))
    print(f"[BioVaram Build] OK - Alembic migrations found")

# =============================================================================
# Analysis & Build Configuration
# =============================================================================

a = Analysis(
    [os.path.join(BACKEND_DIR, 'run_desktop.py')],
    pathex=[BACKEND_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude packages not needed in desktop mode
        'tkinter',
        'tk',
        '_tkinter',
        # NOTE: Do NOT exclude 'unittest' or 'test' — scipy/numpy.testing need them
        'pytest',
        'pytest_cov',
        'pytest_asyncio',
        'pytest_mock',
        'IPython',
        'jupyter',
        'jupyter_client',
        'jupyter_core',
        'nbformat',
        'notebook',
        'ipykernel',
        # Exclude optional cloud/DB packages
        'boto3',
        'botocore',
        'asyncpg',
        'psycopg2',
        'dask',
        # Exclude dev tools
        'black',
        'ruff',
        'mypy',
        'pylint',
        'flake8',
        # ---- SIZE REDUCTION (~130 MB saved) ----
        # numba/llvmlite: JIT compiler — not used by any of our code (~102 MB)
        'numba',
        'llvmlite',
        # Unused heavy visualization libs (all charts are client-side Recharts)
        # Matplotlib/seaborn/plotly only used in legacy/ visualization code,
        # which is not called by any API endpoint in desktop mode
        'matplotlib',
        'matplotlib.backends',
        'seaborn',
        'plotly',
        # PIL/Pillow — not imported by any backend source code (~13 MB)
        'PIL',
        'Pillow',
    ],
    noarchive=False,
    optimize=0,
)

# =============================================================================
# PYZ (Python archive)
# =============================================================================

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# =============================================================================
# EXE (executable)
# =============================================================================

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # One-folder mode (not one-file)
    name='BioVaram',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Release mode: no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJECT_ROOT, 'packaging', 'biovaram.ico') if os.path.exists(os.path.join(PROJECT_ROOT, 'packaging', 'biovaram.ico')) else None,
)

# =============================================================================
# COLLECT (one-folder bundle)
# =============================================================================

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BioVaram',
)

print("\n[BioVaram Build] Spec file processed successfully!")
print(f"[BioVaram Build] Output will be in: dist/BioVaram/")
