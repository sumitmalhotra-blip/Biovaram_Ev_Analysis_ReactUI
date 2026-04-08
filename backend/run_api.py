"""Startup script for CRMIT FastAPI backend."""
import os
import socket
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(backend_dir))

import uvicorn
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")
from src.api.main import app


def _is_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0

if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    if _is_port_in_use("127.0.0.1", port):
        print(f"Port {port} is already in use. API may already be running; skipping duplicate start.")
        sys.exit(0)

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False
    )
