import subprocess
from pathlib import Path

TOP_PORTS_FILE = Path(__file__).parent / "top_ports.txt"
UDP_PORTS = "53,123,161,1900,5353"


def tcp_ports() -> list[int]:
    """Top 1000 TCP ports (+ catalog extras) from the committed list, the same on every laptop."""
    lines = TOP_PORTS_FILE.read_text(encoding="utf-8").splitlines()
    return [int(line) for line in lines if line.strip() and not line.startswith("#")]


def port_spec() -> str:
    return f"T:{','.join(map(str, tcp_ports()))},U:{UDP_PORTS}"


def run_nmap_scan(target: str, output_path: str, timeout: int = 300) -> dict:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "nmap",
        "-sS", "-sV", "-sU",
        "--script", "http-title",
        "-p", port_spec(),
        "--max-rate", "100",
        "-oX", str(output),
        target,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "success": result.returncode == 0,
            "output_path": str(output),
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Scan timed out after {timeout}s"}
    except FileNotFoundError:
        return {"success": False, "error": "nmap not found. Install nmap and ensure it is in PATH."}
