"""Startup script for CRMIT FastAPI backend."""
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(backend_dir))

import uvicorn
from dotenv import load_dotenv

default_env_path = Path(__file__).parent / ".env"
override_env = (os.environ.get("CRMIT_ENV_FILE") or "").strip()
env_path = Path(override_env) if override_env else default_env_path

# Keep this silent; callers may have secrets in env files.
load_dotenv(env_path)
from src.api.main import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False
    )
