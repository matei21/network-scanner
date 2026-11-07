"""Standard results export (FR-15).

findings.csv: file,ip,port,finding_code,severity
scores.csv:   file,network_score   ("ERROR" when the file cannot be read)
"""

from __future__ import annotations

import csv
from pathlib import Path

from .models import ScanResult

FINDINGS_HEADER = ["file", "ip", "port", "finding_code", "severity"]
SCORES_HEADER = ["file", "network_score"]


def write_findings_csv(results: list[ScanResult], path: str | Path) -> None:
    """One row per finding; empty port column when port is None (UNKNOWN_DEVICE)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\r\n")  # same as the official answer key
        writer.writerow(FINDINGS_HEADER)
        for result in results:
            for f in result.findings:
                writer.writerow([f.file, f.ip, "" if f.port is None else f.port, f.code, f.severity])


def write_scores_csv(results: list[ScanResult], path: str | Path) -> None:
    """One row per file; "ERROR" when the file could not be read."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\r\n")
        writer.writerow(SCORES_HEADER)
        for result in results:
            writer.writerow([result.file, "ERROR" if result.error else result.score])
