import multiprocessing
multiprocessing.freeze_support()

import sys
import os
import time
import webbrowser
import threading
import http.server
import socketserver
import socket
from pathlib import Path

# Fix paths for both normal run and PyInstaller EXE
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
    sys.path.insert(0, str(BASE_DIR))
else:
    BASE_DIR = Path(__file__).resolve().parent

FRONTEND_DIST = BASE_DIR / "dist"
BACKEND_PORT = 8000
FRONTEND_PORT = 5173


def kill_existing_on_port(port):
    """Kill any process currently using the given port."""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                for conn in proc.connections():
                    if conn.laddr.port == port:
                        if proc.pid != os.getpid():
                            print(f"Killing process {proc.pid} ({proc.name()}) on port {port}")
                            proc.kill()
            except Exception:
                pass
    except ImportError:
        # psutil not available, try via socket check only
        pass


def find_free_port(start_port):
    """Return start_port if free, otherwise find next available port."""
    port = start_port
    while port < start_port + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                port += 1
    raise RuntimeError(f"No free port found starting from {start_port}")


class SPAHandler(http.server.SimpleHTTPRequestHandler):
    """Serve index.html for any path that doesn't match a real file (React Router support)."""
    def do_GET(self):
        path = self.translate_path(self.path)
        if not os.path.exists(path) or os.path.isdir(path) and not os.path.exists(os.path.join(path, 'index.html')):
            self.path = '/index.html'
        return super().do_GET()

    def log_message(self, *_):
        pass  # Suppress request logs


def serve_frontend(port):
    os.chdir(FRONTEND_DIST)
    with socketserver.TCPServer(("", port), SPAHandler) as httpd:
        print(f"Frontend served at http://localhost:{port}")
        httpd.serve_forever()


def open_browser(port):
    time.sleep(3)
    webbrowser.open(f"http://localhost:{port}")


APP_VERSION = "1.2"

if __name__ == "__main__":
    multiprocessing.freeze_support()

    print(f"BioLabSuite v{APP_VERSION} starting...")

    # Kill anything already on our ports
    kill_existing_on_port(BACKEND_PORT)
    kill_existing_on_port(FRONTEND_PORT)

    # Find free ports (fallback if kill didn't work)
    backend_port = find_free_port(BACKEND_PORT)
    frontend_port = find_free_port(FRONTEND_PORT)

    if backend_port != BACKEND_PORT:
        print(f"Port {BACKEND_PORT} still busy, using {backend_port} for backend")
    if frontend_port != FRONTEND_PORT:
        print(f"Port {FRONTEND_PORT} still busy, using {frontend_port} for frontend")

    t1 = threading.Thread(target=serve_frontend, args=(frontend_port,), daemon=True)
    t1.start()

    t2 = threading.Thread(target=open_browser, args=(frontend_port,), daemon=True)
    t2.start()

    os.environ["MODULE_PROFILE"] = "tem_wb"
    import main
    import uvicorn
    uvicorn.run(main.app, host="127.0.0.1", port=backend_port)