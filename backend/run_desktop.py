"""
BioVaram EV Analysis Platform — Desktop Entry Point
=====================================================

Single-process entry point for desktop deployment.
Serves both the FastAPI backend API and the static Next.js frontend.

Usage:
    python run_desktop.py

This will:
1. Initialize the SQLite database (create tables if first run)
2. Start FastAPI with uvicorn on localhost:8000
3. Serve the static frontend at /
4. Open the default browser to the application
"""
import sys
import os
import socket
import webbrowser
import threading
import time
from pathlib import Path

# =============================================================================
# Path Setup
# =============================================================================

# For frozen windowed mode (console=False), redirect output to a log file
if getattr(sys, 'frozen', False):
    try:
        _log_dir = Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / 'BioVaram'
        _log_dir.mkdir(parents=True, exist_ok=True)
        _log_file = open(str(_log_dir / 'biovaram.log'), 'w', encoding='utf-8')
        sys.stdout = _log_file
        sys.stderr = _log_file
    except Exception:
        pass  # If logging fails, continue anyway

# Determine if we're running from a PyInstaller bundle or source
if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle
    BUNDLE_DIR = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    APP_DIR = Path(sys.executable).parent
else:
    # Running from source
    BUNDLE_DIR = Path(__file__).parent
    APP_DIR = BUNDLE_DIR

# Add backend to Python path
BACKEND_DIR = BUNDLE_DIR if getattr(sys, 'frozen', False) else BUNDLE_DIR
sys.path.insert(0, str(BACKEND_DIR))

# Resolve the static frontend directory
# In source: ../out/ (sibling to backend/)
# In PyInstaller bundle: frontend/ (inside _MEIPASS or next to exe)
if getattr(sys, 'frozen', False):
    FRONTEND_DIR = BUNDLE_DIR / "frontend"
    if not FRONTEND_DIR.exists():
        FRONTEND_DIR = APP_DIR / "frontend"
else:
    FRONTEND_DIR = BUNDLE_DIR.parent / "out"

# =============================================================================
# Data Directory Setup
# =============================================================================

def setup_data_directories() -> Path:
    """
    Create data directories for the desktop app.
    
    In development: uses ./data/ relative to the backend directory
    In production (frozen): uses %APPDATA%/BioVaram/ on Windows
    
    Returns:
        Path to the data root directory
    """
    if getattr(sys, 'frozen', False):
        # Production: use AppData
        if sys.platform == 'win32':
            data_root = Path(os.environ.get('APPDATA', '~')) / 'BioVaram'
        elif sys.platform == 'darwin':
            data_root = Path.home() / 'Library' / 'Application Support' / 'BioVaram'
        else:
            data_root = Path.home() / '.biovaram'
    else:
        # Development: use local data/ directory
        data_root = BUNDLE_DIR.parent / "data"
    
    # Create subdirectories
    (data_root / "uploads").mkdir(parents=True, exist_ok=True)
    (data_root / "parquet").mkdir(parents=True, exist_ok=True)
    (data_root / "temp").mkdir(parents=True, exist_ok=True)
    
    return data_root


def setup_config_directories() -> Path:
    """
    Ensure config directories exist.
    In development: uses backend/config/
    In production: copies defaults to AppData on first run
    """
    if getattr(sys, 'frozen', False):
        config_root = Path(os.environ.get('APPDATA', '~')) / 'BioVaram' / 'config'
        config_root.mkdir(parents=True, exist_ok=True)
        
        # Copy default configs on first run
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


# =============================================================================
# Port Management
# =============================================================================

def find_available_port(preferred: int = 8000, fallbacks: list[int] | None = None) -> int:
    """
    Find an available port, starting with the preferred one.
    
    Args:
        preferred: Preferred port number
        fallbacks: List of fallback ports to try
        
    Returns:
        Available port number
    """
    ports_to_try = [preferred] + (fallbacks or [8010, 8020, 8080])
    
    for port in ports_to_try:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    
    # If all fails, let the OS assign a port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


# =============================================================================
# Application Setup
# =============================================================================

def create_desktop_app():
    """
    Create the FastAPI application configured for desktop mode.
    Mounts the static frontend and configures desktop-specific settings.
    """
    # Set environment variables before importing the app
    data_root = setup_data_directories()
    config_root = setup_config_directories()
    
    db_path = data_root / "crmit.db"
    
    # Configure environment for the backend
    os.environ.setdefault("CRMIT_ENV", "production")
    os.environ.setdefault("CRMIT_DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    os.environ.setdefault("CRMIT_UPLOAD_DIR", str(data_root / "uploads"))
    os.environ.setdefault("CRMIT_PARQUET_DIR", str(data_root / "parquet"))
    os.environ.setdefault("CRMIT_TEMP_DIR", str(data_root / "temp"))
    os.environ.setdefault("CRMIT_DEBUG", "false")
    
    # Now import the FastAPI app (after env vars are set)
    from src.api.main import app
    
    # Mount static frontend if the directory exists
    if FRONTEND_DIR.exists() and (FRONTEND_DIR / "index.html").exists():
        from fastapi import Request
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import FileResponse, HTMLResponse
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.responses import Response as StarletteResponse
        
        # Override the root redirect to serve index.html
        # Remove existing "/" route that redirects to /docs
        app.routes[:] = [r for r in app.routes if not (hasattr(r, 'path') and r.path == "/" and hasattr(r, 'methods'))]
        
        @app.get("/", include_in_schema=False)
        async def serve_root():
            return FileResponse(str(FRONTEND_DIR / "index.html"), media_type="text/html")
        
        # Serve _next/ static assets
        next_static = FRONTEND_DIR / "_next"
        if next_static.exists():
            app.mount("/_next", StaticFiles(directory=str(next_static)), name="next-static")
        
        # Custom exception handler: when FastAPI returns 404, serve frontend
        from fastapi.exceptions import HTTPException
        from starlette.exceptions import HTTPException as StarletteHTTPException
        
        # Store the original 404 handler so API endpoints that explicitly raise 404 still work
        @app.exception_handler(404)
        async def custom_404_handler(request: Request, exc: StarletteHTTPException):
            """
            For GET requests to non-API routes that return 404, 
            serve the frontend index.html (SPA client-side routing).
            For API routes, return proper JSON 404.
            """
            path = request.url.path
            
            # API routes: return JSON 404 as normal
            if path.startswith(("/api/", "/health", "/docs", "/redoc", "/openapi")):
                return HTMLResponse(
                    content='{"detail":"Not Found"}',
                    status_code=404,
                    media_type="application/json"
                )
            
            # Try to serve exact static file from frontend output
            if request.method == "GET":
                file_path = FRONTEND_DIR / path.lstrip("/")
                if ".." not in path and file_path.is_file():
                    return FileResponse(str(file_path))
                
                # SPA fallback
                return FileResponse(str(FRONTEND_DIR / "index.html"), media_type="text/html")
            
            return HTMLResponse(content="Not Found", status_code=404)
        
        print(f"  Frontend: Serving static files from {FRONTEND_DIR}")
    else:
        print(f"  Frontend: Not found at {FRONTEND_DIR}")
        print(f"  Run 'pnpm build' in the project root to generate the frontend.")
        print(f"  The API will still be available at /docs")
    
    return app


def open_browser(port: int, delay: float = 2.0):
    """Open the default browser after a short delay to let the server start."""
    def _open():
        time.sleep(delay)
        url = f"http://localhost:{port}"
        print(f"\n  Opening browser: {url}")
        
        # Show a Windows notification if running as frozen EXE (no console)
        if getattr(sys, 'frozen', False) and sys.platform == 'win32':
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxTimeoutW(  # type: ignore[attr-defined]
                    0,
                    f"BioVaram EV Analysis Platform v{VERSION}\n\nStarting on http://localhost:{port}\n\nYour browser will open automatically.",
                    "BioVaram Desktop",
                    0x00000040 | 0x00000000,  # MB_ICONINFORMATION | MB_OK
                    0,  # language ID
                    3000,  # timeout in ms (auto-close after 3 seconds)
                )
            except Exception:
                pass  # Fallback: just open browser silently
        
        webbrowser.open(url)
    
    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


# =============================================================================
# Version Info
# =============================================================================

VERSION = "1.0.0"
BUILD_DATE = "2026-03-03"


def print_banner(port: int):
    """Print startup banner."""
    print()
    print("=" * 60)
    print("  BioVaram EV Analysis Platform — Desktop Edition")
    print(f"  Version {VERSION} | Build {BUILD_DATE}")
    print("=" * 60)
    print()
    print(f"  API Server:  http://localhost:{port}")
    print(f"  API Docs:    http://localhost:{port}/docs")
    print(f"  Application: http://localhost:{port}")
    print()
    if getattr(sys, 'frozen', False):
        data_root = Path(os.environ.get('APPDATA', '~')) / 'BioVaram'
        print(f"  Data:        {data_root}")
        print(f"  Database:    {data_root / 'crmit.db'}")
    else:
        print(f"  Data:        {BUNDLE_DIR.parent / 'data'}")
        print(f"  Frontend:    {FRONTEND_DIR}")
    print()
    print("  Press Ctrl+C to stop the server")
    print("=" * 60)
    print()


# =============================================================================
# Main
# =============================================================================

def main():
    """Main entry point for the desktop application."""
    import uvicorn
    
    # Find available port
    port = find_available_port(8000)
    
    # Print banner
    print_banner(port)
    
    # Create the app
    app = create_desktop_app()
    
    # Open browser
    open_browser(port)
    
    # Start server
    try:
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=port,
            log_level="info",
            access_log=False,  # Reduce noise in desktop mode
        )
    except KeyboardInterrupt:
        print("\n  Server stopped.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # In frozen windowed mode, show error via messagebox
        if getattr(sys, 'frozen', False) and sys.platform == 'win32':
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(  # type: ignore[attr-defined]
                    0,
                    f"BioVaram failed to start:\n\n{str(e)}",
                    "BioVaram Error",
                    0x00000010,  # MB_ICONERROR
                )
            except Exception:
                pass
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
