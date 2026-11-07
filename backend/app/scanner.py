import subprocess
from pathlib import Path


def run_nmap_scan(target: str, output_path: str, timeout: int = 300) -> dict:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "nmap",
        "-sS", "-sV", "-sU",
        "--script", "http-title",
        "-p", "T:1-1000,U:53,123,161,1900,5353",
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
