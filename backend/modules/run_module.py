"""
Module Runner — Shared Desktop Launch Logic
=============================================

Provides `run_module()` which is called by each module's `run.py`.
Reuses all the infrastructure from run_desktop.py (path setup, port finder,
browser opener, frontend mounting) but with a module-specific FastAPI app.
"""

import sys
import os
import socket
import webbrowser
import threading
import time
import signal
from pathlib import Path


# =============================================================================
# Path Setup (same as run_desktop.py)
# =============================================================================

if getattr(sys, 'frozen', False):
    try:
        _log_dir = Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / 'BioVaram'
        _log_dir.mkdir(parents=True, exist_ok=True)
        _log_file = open(str(_log_dir / 'biovaram.log'), 'w', encoding='utf-8')
        sys.stdout = _log_file
        sys.stderr = _log_file
    except Exception:
        pass

if getattr(sys, 'frozen', False):
    BUNDLE_DIR = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    APP_DIR = Path(sys.executable).parent
else:
    BUNDLE_DIR = Path(__file__).parent
    APP_DIR = BUNDLE_DIR

BACKEND_DIR = BUNDLE_DIR if getattr(sys, 'frozen', False) else BUNDLE_DIR
sys.path.insert(0, str(BACKEND_DIR))

if getattr(sys, 'frozen', False):
    FRONTEND_DIR = BUNDLE_DIR / "frontend"
    if not FRONTEND_DIR.exists():
        FRONTEND_DIR = APP_DIR / "frontend"
else:
    FRONTEND_DIR = BUNDLE_DIR.parent / "out"


# Default ports per module (avoids conflicts if multiple modules run)
MODULE_PORTS = {
    "full_platform": 8000,
    "nanofacs": 8001,
    "nta": 8002,
}


def _load_version() -> tuple[str, str]:
    try:
        import json
        version_file = APP_DIR / "version.json"
        if version_file.exists():
            data = json.loads(version_file.read_text(encoding="utf-8"))
            return data.get("version", "1.0.0"), data.get("build_date", "dev")
    except Exception:
        pass
    return "1.0.0", "dev"


def setup_data_directories() -> Path:
    if getattr(sys, 'frozen', False):
        if sys.platform == 'win32':
            data_root = Path(os.environ.get('APPDATA', '~')) / 'BioVaram'
        elif sys.platform == 'darwin':
            data_root = Path.home() / 'Library' / 'Application Support' / 'BioVaram'
        else:
            data_root = Path.home() / '.biovaram'
    else:
        data_root = BUNDLE_DIR.parent / "data"
    
    (data_root / "uploads").mkdir(parents=True, exist_ok=True)
    (data_root / "parquet").mkdir(parents=True, exist_ok=True)
    (data_root / "temp").mkdir(parents=True, exist_ok=True)
    return data_root


def setup_config_directories() -> Path:
    if getattr(sys, 'frozen', False):
        config_root = Path(os.environ.get('APPDATA', '~')) / 'BioVaram' / 'config'
        config_root.mkdir(parents=True, exist_ok=True)
        bundled_config = BUNDLE_DIR / "config"
        if bundled_config.exists():
            import shutil
            for item in bundled_config.iterdir():
                dest = config_root / item.name
                if not dest.exists():
                    if item.is_dir():
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)
        return config_root
    else:
        config_root = BUNDLE_DIR / "config"
        config_root.mkdir(parents=True, exist_ok=True)
        return config_root


def find_available_port(preferred: int = 8000, fallbacks: list[int] | None = None) -> int:
    ports_to_try = [preferred] + (fallbacks or [preferred + 10, preferred + 20, preferred + 80])
    for port in ports_to_try:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def mount_frontend(app, frontend_dir: Path = FRONTEND_DIR):
    """Mount the static frontend if available."""
    if frontend_dir.exists() and (frontend_dir / "index.html").exists():
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import FileResponse, HTMLResponse
        from starlette.exceptions import HTTPException as StarletteHTTPException

        # Remove existing "/" route
        app.routes[:] = [r for r in app.routes if not (hasattr(r, 'path') and getattr(r, 'path', None) == "/" and hasattr(r, 'methods'))]

        @app.get("/", include_in_schema=False)
        async def serve_root():
            return FileResponse(str(frontend_dir / "index.html"), media_type="text/html")

        next_static = frontend_dir / "_next"
        if next_static.exists():
            app.mount("/_next", StaticFiles(directory=str(next_static)), name="next-static")

        @app.exception_handler(404)
        async def custom_404_handler(request, exc: StarletteHTTPException):
            path = request.url.path
            if path.startswith(("/api/", "/health", "/docs", "/redoc", "/openapi")):
                return HTMLResponse(
                    content='{"detail":"Not Found"}',
                    status_code=404,
                    media_type="application/json"
                )
            if request.method == "GET":
                file_path = frontend_dir / path.lstrip("/")
                if ".." not in path and file_path.is_file():
                    return FileResponse(str(file_path))
                return FileResponse(str(frontend_dir / "index.html"), media_type="text/html")
            return HTMLResponse(content="Not Found", status_code=404)

        print(f"  Frontend: Serving from {frontend_dir}")
    else:
        print(f"  Frontend: Not found at {frontend_dir}")
        print(f"  The API will still be available at /docs")


def run_module(
    module_name: str,
    module_title: str,
):
    """
    Run a module-specific desktop application.
    
    Args:
        module_name: Module identifier (e.g. "nanofacs", "nta")
        module_title: Human-readable title
    """
    import uvicorn

    version, build_date = _load_version()
    default_port = MODULE_PORTS.get(module_name, 8000)
    
    # Setup environment
    data_root = setup_data_directories()
    setup_config_directories()
    db_path = data_root / "crmit.db"
    
    os.environ.setdefault("CRMIT_ENV", "production")
    os.environ.setdefault("CRMIT_DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    os.environ.setdefault("CRMIT_UPLOAD_DIR", str(data_root / "uploads"))
    os.environ.setdefault("CRMIT_PARQUET_DIR", str(data_root / "parquet"))
    os.environ.setdefault("CRMIT_TEMP_DIR", str(data_root / "temp"))
    os.environ.setdefault("CRMIT_DEBUG", "false")
    
    # Import module app (after env vars are set)
    from importlib import import_module
    mod = import_module(f"modules.{module_name}.app")
    app = mod.app
    
    # Mount frontend
    mount_frontend(app)
    
    # Find port
    port = find_available_port(default_port)
    
    # Banner
    print()
    print("=" * 60)
    print(f"  BioVaram {module_title} — Desktop Edition")
    print(f"  Version {version} | Build {build_date}")
    print("=" * 60)
    print()
    print(f"  Module:      {module_name}")
    print(f"  API Server:  http://localhost:{port}")
    print(f"  API Docs:    http://localhost:{port}/docs")
    print(f"  Application: http://localhost:{port}")
    print()
    if getattr(sys, 'frozen', False):
        print(f"  Data:        {data_root}")
        print(f"  Database:    {data_root / 'crmit.db'}")
    else:
        print(f"  Data:        {BUNDLE_DIR.parent / 'data'}")
        print(f"  Frontend:    {FRONTEND_DIR}")
    print()
    print("  Press Ctrl+C to stop the server")
    print("=" * 60)
    print()
    
    # Open browser
    def _open_browser():
        time.sleep(2.0)
        url = f"http://localhost:{port}"
        print(f"\n  Opening browser: {url}")
        if getattr(sys, 'frozen', False) and sys.platform == 'win32':
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxTimeoutW(  # type: ignore[attr-defined]
                    0,
                    f"BioVaram {module_title} v{version}\n\n"
                    f"Server running on http://localhost:{port}\n"
                    f"Your browser will open automatically.",
                    f"BioVaram {module_title}",
                    0x00000040, 0, 3000,
                )
            except Exception:
                pass
        webbrowser.open(url)
    
    threading.Thread(target=_open_browser, daemon=True).start()
    
    # Graceful shutdown
    shutdown_event = threading.Event()
    def handle_shutdown(signum, frame):
        print("\n  Shutting down gracefully...")
        shutdown_event.set()
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Run
    try:
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning" if getattr(sys, 'frozen', False) else "info",
            access_log=not getattr(sys, 'frozen', False),
        )
        server = uvicorn.Server(config)
        server.run()
    except KeyboardInterrupt:
        pass
    finally:
        print(f"\n  {module_title} stopped. Goodbye!")
