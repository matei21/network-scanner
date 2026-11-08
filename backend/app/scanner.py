import re
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Callable

TOP_PORTS_FILE = Path(__file__).parent / "top_ports.txt"
UDP_PORTS = "53,123,161,1900,5353"
SCAN_TIMEOUT = 300  # seconds; NFR-07 asks for a /24 in under 5 minutes

# The Windows installer does not always add nmap to PATH, and the backend's terminal may not have it.
NMAP_DEFAULT_PATHS = [
    Path("C:/Program Files (x86)/Nmap/nmap.exe"),
    Path("C:/Program Files/Nmap/nmap.exe"),
]

NMAP_NOT_FOUND = "nmap not found. Install it from https://nmap.org/download.html"


def find_nmap() -> str | None:
    found = shutil.which("nmap")
    if found:
        return found
    return next((str(p) for p in NMAP_DEFAULT_PATHS if p.is_file()), None)


def tcp_ports() -> list[int]:
    """Top 1000 TCP ports (+ catalog extras) from the committed list, the same on every laptop."""
    lines = TOP_PORTS_FILE.read_text(encoding="utf-8").splitlines()
    return [int(line) for line in lines if line.strip() and not line.startswith("#")]


def port_spec() -> str:
    return f"T:{','.join(map(str, tcp_ports()))},U:{UDP_PORTS}"


def build_command(target: str, output: Path) -> list[str]:
    return [
        find_nmap() or "nmap",
        "-sS", "-sV", "-sU",
        "--script", "http-title",
        "-p", port_spec(),
        "--max-rate", "100",
        "-oX", str(output),
        target,
    ]


def run_nmap_scan(target: str, output_path: str, timeout: int = SCAN_TIMEOUT) -> dict:
    """Blocking scan, used by the command line (python -m backend.scan)."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(build_command(target, output), capture_output=True, text=True, timeout=timeout)
        return {
            "success": result.returncode == 0,
            "output_path": str(output),
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Scan timed out after {timeout}s"}
    except FileNotFoundError:
        return {"success": False, "error": NMAP_NOT_FOUND}


# --- background scan with progress and cancel (the UI scan button) -----------------

# nmap --stats-every prints e.g. "SYN Stealth Scan Timing: About 45.20% done; ETC: 03:12 (0:01:02 remaining)"
_PROGRESS = re.compile(r"^(?P<phase>.+?) Timing: About (?P<pct>[\d.]+)% done(?:; ETC: \S+ \((?P<left>[\d:]+) remaining\))?")

# nmap runs these one after another; each reports its own 0-100%.
PHASES = [
    ("discovery", ("ARP Ping Scan", "Ping Scan", "Parallel DNS")),
    ("tcp", ("SYN Stealth Scan",)),
    ("udp", ("UDP Scan",)),
    ("services", ("Service scan",)),
    ("scripts", ("NSE", "Script scan")),
]


def _phase_key(name: str) -> str | None:
    return next((key for key, names in PHASES if any(name.startswith(n) for n in names)), None)


class ScanJob:
    def __init__(self, target: str, output: Path, on_finish: Callable[[Path], dict], timeout: int = SCAN_TIMEOUT):
        self.id = uuid.uuid4().hex
        self.target = target
        self.output = output
        self.on_finish = on_finish
        self.timeout = timeout
        self.status = "running"          # running | done | error | cancelled
        self.phase = "discovery"
        self.phase_percent = 0.0
        self.remaining = None            # "0:01:02", as nmap prints it
        self.error = None
        self.result = None
        self.started = time.monotonic()
        self._proc = None
        self._stop = None                # "cancel" or "timeout"
        self._lock = threading.Lock()

    def start(self) -> None:
        self.output.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._proc = subprocess.Popen(
                build_command(self.target, self.output) + ["--stats-every", "2s"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace",
            )
        except FileNotFoundError:
            self.status, self.error = "error", NMAP_NOT_FOUND
            return
        threading.Thread(target=self._run, daemon=True).start()
        timer = threading.Timer(self.timeout, self._stop_process, args=("timeout",))
        timer.daemon = True  # never keeps the server alive on shutdown / reload
        timer.start()

    def _run(self) -> None:
        tail = []
        for line in self._proc.stdout:
            tail = (tail + [line.rstrip()])[-5:]
            m = _PROGRESS.match(line.strip())
            if m and _phase_key(m["phase"]):
                with self._lock:
                    self.phase = _phase_key(m["phase"])
                    self.phase_percent = float(m["pct"])
                    self.remaining = m["left"]
        code = self._proc.wait()

        if self._stop == "cancel":
            self.status = "cancelled"
        elif self._stop == "timeout":
            self.status, self.error = "error", f"Scan timed out after {self.timeout}s"
        elif code != 0:
            self.status, self.error = "error", " ".join(tail)[-300:] or "Scan failed."
        else:
            try:
                self.result = self.on_finish(self.output)
                self.status = "done"
            except Exception as e:  # the scan finished but its file could not be stored
                self.status, self.error = "error", str(e)

    def _stop_process(self, reason: str) -> None:
        if self.status != "running" or self._proc is None or self._proc.poll() is not None:
            return
        self._stop = reason
        self._proc.terminate()
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()

    def cancel(self) -> None:
        self._stop_process("cancel")

    def to_dict(self) -> dict:
        with self._lock:
            keys = [k for k, _ in PHASES]
            step = keys.index(self.phase) if self.phase in keys else 0
            overall = 100.0 if self.status == "done" else (step + self.phase_percent / 100) / len(keys) * 100
            return {
                "job_id": self.id,
                "target": self.target,
                "status": self.status,
                "phase": self.phase,
                "phase_percent": round(self.phase_percent, 1),
                "percent": round(min(overall, 100.0), 1),
                "remaining": self.remaining,
                "elapsed": int(time.monotonic() - self.started),
                "error": self.error,
                "result": self.result,
            }


_jobs: dict[str, ScanJob] = {}


def start_scan_job(target: str, output: Path, on_finish: Callable[[Path], dict]) -> ScanJob:
    """Only one live scan at a time: two parallel scans would break the 100 packets/s limit."""
    if any(j.status == "running" for j in _jobs.values()):
        raise RuntimeError("A live scan is already running.")
    job = ScanJob(target, output, on_finish)
    _jobs[job.id] = job
    job.start()
    return job


def get_scan_job(job_id: str) -> ScanJob | None:
    return _jobs.get(job_id)
