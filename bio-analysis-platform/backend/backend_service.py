import multiprocessing
multiprocessing.freeze_support()

import sys
import os
import socket
from pathlib import Path

# Fix paths for both normal run and PyInstaller EXE
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
    sys.path.insert(0, str(BASE_DIR))
else:
    BASE_DIR = Path(__file__).resolve().parent

BACKEND_PORT_DEFAULT = 8000


def find_free_port(start_port: int) -> int:
    """Return start_port if free, else scan forward up to 100 ports."""
    port = start_port
    while port < start_port + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                port += 1
    raise RuntimeError(f"No free port found starting from {start_port}")


if __name__ == "__main__":
    multiprocessing.freeze_support()

    backend_port = find_free_port(BACKEND_PORT_DEFAULT)

    # Announce port immediately so Electron knows which port to use.
    # Electron will NOT load the frontend until a /health check passes,
    # so announcing here (before uvicorn finishes starting) is safe.
    print(f"BACKEND_PORT:{backend_port}", flush=True)

    os.environ["MODULE_PROFILE"] = "tem_wb"

    import main
    import uvicorn
    uvicorn.run(main.app, host="127.0.0.1", port=backend_port)
