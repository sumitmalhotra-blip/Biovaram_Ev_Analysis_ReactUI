# -*- mode: python ; coding: utf-8 -*-
"""
BioVaram Module — Parameterized PyInstaller Spec File
======================================================

This spec file is used by build_modules.ps1 to build individual module EXEs.
It reads the following environment variables:

    BIOVARAM_MODULE_NAME   — e.g. "nanofacs", "nta", "cross_compare", "dashboard", "full_platform"
    BIOVARAM_MODULE_TITLE  — e.g. "NanoFACS Analysis", "NTA Analysis"
    BIOVARAM_EXE_NAME      — e.g. "BioVaram_NanoFACS", "BioVaram_NTA"
    BIOVARAM_FRONTEND_DIR  — path to the module's static frontend (e.g. out_nanofacs/)

Build command (run by build_modules.ps1, not directly):
    $env:BIOVARAM_MODULE_NAME = "nanofacs"
    $env:BIOVARAM_EXE_NAME = "BioVaram_NanoFACS"
    ...
    pyinstaller packaging/biovaram_module.spec --noconfirm
"""

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

# =============================================================================
# Module Configuration (from environment)
# =============================================================================

MODULE_NAME = os.environ.get('BIOVARAM_MODULE_NAME', 'full_platform')
MODULE_TITLE = os.environ.get('BIOVARAM_MODULE_TITLE', 'EV Analysis Platform')
EXE_NAME = os.environ.get('BIOVARAM_EXE_NAME', 'BioVaram')

SPEC_DIR = SPECPATH
PROJECT_ROOT = os.path.dirname(SPEC_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'backend')
CONFIG_DIR = os.path.join(BACKEND_DIR, 'config')

# Frontend: use module-specific output directory if it exists
FRONTEND_DIR = os.environ.get('BIOVARAM_FRONTEND_DIR', '')
if not FRONTEND_DIR:
    # Fall back to out_{module}/ or out/
    module_out = os.path.join(PROJECT_ROOT, f'out_{MODULE_NAME}')
    default_out = os.path.join(PROJECT_ROOT, 'out')
    FRONTEND_DIR = module_out if os.path.isdir(module_out) else default_out

print(f"[Module Build] Module:       {MODULE_NAME}")
print(f"[Module Build] EXE Name:     {EXE_NAME}")
print(f"[Module Build] Project root: {PROJECT_ROOT}")
print(f"[Module Build] Backend dir:  {BACKEND_DIR}")
print(f"[Module Build] Frontend dir: {FRONTEND_DIR}")

# Entry point: modules/<module>/run.py
ENTRY_POINT = os.path.join(BACKEND_DIR, 'modules', MODULE_NAME, 'run.py')
if not os.path.isfile(ENTRY_POINT):
    raise FileNotFoundError(f"Entry point not found: {ENTRY_POINT}")
print(f"[Module Build] Entry point:  {ENTRY_POINT}")

# =============================================================================
# Hidden Imports (shared across all modules)
# =============================================================================
# Using the same imports for all modules keeps builds reliable.
# Unused imports don't significantly affect startup time.

hidden_imports = []

# --- FastAPI / Starlette / Uvicorn ---
hidden_imports += collect_submodules('uvicorn')
hidden_imports += [
    'uvicorn.logging',
    'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.loops.asyncio',
    'uvicorn.protocols', 'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto', 'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.http.httptools_impl',
    'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.wsproto_impl',
    'uvicorn.lifespan', 'uvicorn.lifespan.on', 'uvicorn.lifespan.off',
    'fastapi', 'fastapi.routing', 'fastapi.middleware',
    'fastapi.middleware.cors', 'fastapi.staticfiles',
    'fastapi.responses', 'fastapi.exceptions',
    'starlette', 'starlette.routing', 'starlette.middleware',
    'starlette.staticfiles', 'starlette.responses',
    'starlette.exceptions', 'starlette.middleware.gzip',
    'anyio', 'anyio._backends', 'anyio._backends._asyncio',
]

# --- Pydantic ---
hidden_imports += [
    'pydantic', 'pydantic.deprecated', 'pydantic.deprecated.decorator',
    'pydantic_settings', 'pydantic_core', 'annotated_types', 'email_validator',
]

# --- SQLAlchemy (async + SQLite) ---
hidden_imports += [
    'sqlalchemy', 'sqlalchemy.ext.asyncio',
    'sqlalchemy.dialects.sqlite', 'sqlalchemy.dialects.sqlite.aiosqlite',
    'sqlalchemy.pool', 'aiosqlite', 'alembic',
]

# --- Scientific / Data Libraries ---
hidden_imports += [
    'numpy', 'numpy.core',
    'scipy', 'scipy.special', 'scipy.special.cython_special',
    'scipy.optimize', 'scipy.interpolate', 'scipy.stats', 'scipy.signal',
    'pandas', 'pandas.io.formats.style',
    'pyarrow', 'pyarrow.parquet',
    'miepython',
    'sklearn', 'sklearn.cluster', 'sklearn.mixture', 'sklearn.preprocessing',
]

# --- FCS / Flow Cytometry ---
hidden_imports += ['flowio', 'fcsparser']

# --- PDF Parsing ---
hidden_imports += ['pdfplumber']

# --- Utilities ---
hidden_imports += [
    'loguru', 'bcrypt', 'jose', 'python_jose', 'colorama', 'tqdm',
    'dotenv', 'multipart', 'requests', 'httpx',
    'httpx._transports', 'httpx._transports.default', 'httpcore',
]

# --- Our source packages ---
hidden_imports += [
    'src', 'src.api', 'src.api.config', 'src.api.main',
    'src.api.cache', 'src.api.auth_middleware',
    'src.api.routers', 'src.api.routers.upload', 'src.api.routers.samples',
    'src.api.routers.jobs', 'src.api.routers.analysis',
    'src.api.routers.auth', 'src.api.routers.alerts',
    'src.api.routers.calibration', 'src.api.routers.chat',
    'src.api.routers.backup',
    'src.database', 'src.database.connection', 'src.database.crud',
    'src.database.models',
    'src.parsers', 'src.parsers.fcs_parser', 'src.parsers.nta_parser',
    'src.parsers.nta_pdf_parser', 'src.parsers.parquet_writer',
    'src.parsers.bead_datasheet_parser', 'src.parsers.base_parser',
    'src.physics', 'src.physics.mie_scatter', 'src.physics.bead_calibration',
    'src.physics.nta_corrections', 'src.physics.size_config',
    'src.physics.size_distribution', 'src.physics.statistics_utils',
    'src.analysis', 'src.analysis.population_shift',
    'src.analysis.temporal_analysis',
    'src.utils', 'src.utils.channel_config',
    'src.visualization', 'src.visualization.auto_axis_selector',
]

# --- Module system ---
hidden_imports += [
    'modules', 'modules.base', 'modules.run_module',
    'modules.nanofacs', 'modules.nanofacs.app',
    'modules.nta', 'modules.nta.app',
    'modules.full_platform', 'modules.full_platform.app',
    f'modules.{MODULE_NAME}', f'modules.{MODULE_NAME}.app',
    f'modules.{MODULE_NAME}.run',
]

# De-duplicate
hidden_imports = list(set(hidden_imports))

# =============================================================================
# Data Files
# =============================================================================

datas = []

# --- Static frontend ---
if os.path.isdir(FRONTEND_DIR):
    datas.append((FRONTEND_DIR, 'frontend'))
    print(f"[Module Build] OK - Frontend found: {FRONTEND_DIR}")
else:
    print(f"[Module Build] WARN - Frontend not found at {FRONTEND_DIR}")

# --- Config files ---
if os.path.isdir(CONFIG_DIR):
    datas.append((CONFIG_DIR, 'config'))
    print(f"[Module Build] OK - Config found: {CONFIG_DIR}")

# --- Backend source ---
BACKEND_SRC = os.path.join(BACKEND_DIR, 'src')
if os.path.isdir(BACKEND_SRC):
    datas.append((BACKEND_SRC, 'src'))

# --- Modules directory ---
MODULES_DIR = os.path.join(BACKEND_DIR, 'modules')
if os.path.isdir(MODULES_DIR):
    datas.append((MODULES_DIR, 'modules'))
    print(f"[Module Build] OK - Modules package found: {MODULES_DIR}")

# --- Alembic migrations ---
ALEMBIC_DIR = os.path.join(BACKEND_DIR, 'alembic')
if os.path.isdir(ALEMBIC_DIR):
    datas.append((ALEMBIC_DIR, 'alembic'))
    datas.append((os.path.join(BACKEND_DIR, 'alembic.ini'), '.'))

# =============================================================================
# Analysis
# =============================================================================

a = Analysis(
    [ENTRY_POINT],
    pathex=[BACKEND_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'tk', '_tkinter',
        'pytest', 'pytest_cov', 'pytest_asyncio', 'pytest_mock',
        'IPython', 'jupyter', 'jupyter_client', 'jupyter_core',
        'nbformat', 'notebook', 'ipykernel',
        'boto3', 'botocore', 'asyncpg', 'psycopg2', 'dask',
        'black', 'ruff', 'mypy', 'pylint', 'flake8',
        'numba', 'llvmlite',
        'matplotlib', 'matplotlib.backends', 'seaborn', 'plotly',
        'PIL', 'Pillow',
    ],
    noarchive=False,
    optimize=0,
)

# =============================================================================
# Build
# =============================================================================

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    exclude_binaries=False,
    name=EXE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJECT_ROOT, 'packaging', 'biovaram.ico')
         if os.path.exists(os.path.join(PROJECT_ROOT, 'packaging', 'biovaram.ico'))
         else None,
)

print(f"\n[Module Build] Spec processed — output: dist/{EXE_NAME}.exe")
