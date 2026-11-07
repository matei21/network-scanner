"""Public entry points used by the CLI and by the backend (Person B).

Contract: see docs/api_contract.json. Explanations / fix steps are added
later by Person D's ai/ module, not here.
"""

from __future__ import annotations

from pathlib import Path

from .models import ScanResult
from .parser import ScanParseError, parse_file
from .privacy import mask_mac
from .rules import findings_for_scan
from .scoring import network_score


def analyze_file(path: str | Path) -> ScanResult:
    """Parse + rules + score for one file. Never raises for bad input:
    returns ScanResult(error=...) instead (V7_broken.xml must not crash)."""
    name = Path(path).name
    try:
        scan = parse_file(path)
    except ScanParseError as e:
        return ScanResult(file=name, error=str(e))
    except Exception as e:  # never crash on a hostile or strange file
        return ScanResult(file=name, error=f"unexpected error while reading file: {type(e).__name__}")

    scan.findings = findings_for_scan(scan.file, scan.devices)
    scan.score = network_score(scan.findings)
    return scan


def analyze_folder(folder: str | Path) -> list[ScanResult]:
    """Analyze every *.xml in a folder (or one file), sorted by file name."""
    folder = Path(folder)
    if folder.is_file():
        return [analyze_file(folder)]
    if not folder.is_dir():
        raise FileNotFoundError(f"not a file or folder: {folder}")
    files = sorted(
        (p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".xml"),
        key=lambda p: p.name,
    )
    return [analyze_file(p) for p in files]


def to_dict(result: ScanResult) -> dict:
    """Convert a ScanResult to the JSON contract (MACs masked!).

    scan_id and history are filled in by the backend (B);
    type / icon / explanations / fix steps by the AI module (D).
    """
    devices = []
    for d in result.devices:
        devices.append({
            "ip": d.ip,
            "mac": mask_mac(d.mac),
            "vendor": d.vendor,
            "hostname": d.hostname,
            "type": "",
            "icon": "",
            "open_ports": [
                {
                    "port": p.port,
                    "protocol": p.protocol,
                    "service": p.service,
                    "product": p.product,
                    "version": p.version,
                }
                for p in d.open_ports
            ],
            "findings": [
                {
                    "code": f.code,
                    "ip": f.ip,
                    "port": f.port,
                    "protocol": f.protocol,
                    "severity": f.severity,
                    "points": f.points,
                    "evidence": f.evidence,
                }
                for f in result.findings
                if f.ip == d.ip
            ],
        })

    return {
        "scan_id": None,
        "file": result.file,
        "status": "ok" if result.ok else "error",
        "error": result.error,
        "score": result.score,
        "devices": devices,
        "history": [],
    }
