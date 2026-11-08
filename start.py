"""Set up and start the whole app with one command:

    python start.py                 # install what is missing, start backend + UI, open the browser
    python start.py --with-llm      # also install the optional local AI model (Qwen 2.5 3B, ~2 GB)
    python start.py --no-browser    # don't open the browser
    python start.py --skip-install  # start right away, assume everything is installed

Needs Python 3.11+ and Node.js 18+. nmap is needed only for live scans.
Ctrl+C stops both servers.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / "backend" / "venv"
FRONTEND = ROOT / "frontend"
BACKEND_PORT, FRONTEND_PORT = 8000, 5173
WINDOWS = os.name == "nt"
LLAMA_WHEELS = "https://abetlen.github.io/llama-cpp-python/whl/cpu"  # prebuilt wheels: no C++ compiler needed


def say(msg: str) -> None:
    print(f"[start] {msg}", flush=True)


def fail(msg: str) -> None:
    say(f"ERROR: {msg}")
    sys.exit(1)


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if WINDOWS else "bin/python")


def file_hash(*paths: Path) -> str:
    h = hashlib.sha256()
    for p in paths:
        if p.exists():
            h.update(p.read_bytes())
    return h.hexdigest()


def run(cmd: list, cwd: Path = ROOT) -> None:
    say(" ".join(str(c) for c in cmd))
    if subprocess.run([str(c) for c in cmd], cwd=cwd).returncode != 0:
        fail(f"command failed: {' '.join(str(c) for c in cmd)}")


def port_busy(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def check_prerequisites() -> str:
    if sys.version_info < (3, 11):
        fail(f"Python 3.11+ is needed (this is {sys.version.split()[0]}).")
    npm = shutil.which("npm.cmd" if WINDOWS else "npm") or shutil.which("npm")
    if not npm:
        fail("Node.js (npm) not found. Install Node.js 18+ from https://nodejs.org and run again.")
    nmap = shutil.which("nmap") or any(Path(p).is_file() for p in
                                       ("C:/Program Files (x86)/Nmap/nmap.exe", "C:/Program Files/Nmap/nmap.exe"))
    if not nmap:
        say("note: nmap not found. File analysis works; live scans need nmap (https://nmap.org/download.html).")
    return npm


def install(npm: str, with_llm: bool) -> None:
    # Python packages, in backend/venv (re-installed only when requirements change)
    if not venv_python().exists():
        say("creating the Python environment in backend/venv ...")
        run([sys.executable, "-m", "venv", VENV])
    req_files = [ROOT / "requirements.txt"] + ([ROOT / "requirements-llm.txt"] if with_llm else [])
    marker = VENV / ".installed"
    wanted = file_hash(*req_files)
    if not marker.exists() or marker.read_text() != wanted:
        run([venv_python(), "-m", "pip", "install", "--upgrade", "pip", "-q"])
        run([venv_python(), "-m", "pip", "install", "-r", ROOT / "requirements.txt"])
        if with_llm:
            run([venv_python(), "-m", "pip", "install", "-r", ROOT / "requirements-llm.txt",
                 "--extra-index-url", LLAMA_WHEELS])
        marker.write_text(wanted)
    else:
        say("Python packages already installed.")

    if with_llm:
        say("downloading the local AI model (~2 GB, only the first time) ...")
        run([venv_python(), "-c", "from ai.ai_service import download_local_model; download_local_model()"])

    # UI packages (re-installed only when package-lock.json changes)
    marker = FRONTEND / "node_modules" / ".installed"
    wanted = file_hash(FRONTEND / "package-lock.json", FRONTEND / "package.json")
    if not marker.exists() or marker.read_text() != wanted:
        run([npm, "install"], cwd=FRONTEND)
        marker.write_text(wanted)
    else:
        say("UI packages already installed.")


def wait_for(url: str, seconds: int) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except Exception:
            time.sleep(1)
    return False


def stop(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if WINDOWS:
        # npm starts node as a child process: stop the whole tree
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def main() -> None:
    ap = argparse.ArgumentParser(description="Install what is missing and start backend + UI.")
    ap.add_argument("--with-llm", action="store_true", help="also install the optional local AI model (~2 GB)")
    ap.add_argument("--no-browser", action="store_true", help="don't open the browser")
    ap.add_argument("--skip-install", action="store_true", help="don't check or install dependencies")
    args = ap.parse_args()

    npm = check_prerequisites()
    for port, name in ((BACKEND_PORT, "backend"), (FRONTEND_PORT, "UI")):
        if port_busy(port):
            fail(f"port {port} ({name}) is already in use. Close the program using it (maybe the app is already running).")
    if not args.skip_install:
        install(npm, args.with_llm)
    python = venv_python() if venv_python().exists() else Path(sys.executable)

    group = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if WINDOWS else {"start_new_session": True}
    say(f"starting the backend on http://localhost:{BACKEND_PORT} ...")
    # no --reload: on Windows the auto-reloader can hang and keep serving old code
    backend = subprocess.Popen([str(python), "-m", "uvicorn", "backend.app.main:app", "--port", str(BACKEND_PORT)],
                               cwd=ROOT, **group)
    say(f"starting the UI on http://localhost:{FRONTEND_PORT} ...")
    # VITE_USE_MOCK=0: real data from the backend even without a frontend/.env.local file
    ui = subprocess.Popen([npm, "run", "dev", "--", "--port", str(FRONTEND_PORT), "--strictPort"], cwd=FRONTEND,
                          env={**os.environ, "VITE_USE_MOCK": "0"}, **group)

    try:
        backend_ok = wait_for(f"http://127.0.0.1:{BACKEND_PORT}/api/settings/ai", 90)
        ui_ok = wait_for(f"http://localhost:{FRONTEND_PORT}/", 60)
        if not backend_ok:
            say("the backend did not start; see the messages above.")
        if ui_ok:
            url = f"http://localhost:{FRONTEND_PORT}"
            say(f"ready: {url}   (Ctrl+C to stop)")
            if not args.no_browser:
                webbrowser.open(url)
        while backend.poll() is None and ui.poll() is None:
            time.sleep(1)
        say("a server stopped; shutting down the other one.")
    except KeyboardInterrupt:
        say("stopping ...")
    finally:
        stop(ui)
        stop(backend)


if __name__ == "__main__":
    main()
