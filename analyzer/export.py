"""Standard results export (FR-15).

findings.csv: file,ip,port,finding_code,severity
scores.csv:   file,network_score   ("ERROR" when the file cannot be read)
"""

from __future__ import annotations

from pathlib import Path

from .models import ScanResult

FINDINGS_HEADER = ["file", "ip", "port", "finding_code", "severity"]
SCORES_HEADER = ["file", "network_score"]


def write_findings_csv(results: list[ScanResult], path: str | Path) -> None:
    # TODO(A): one row per finding; empty port column when port is None
    raise NotImplementedError


def write_scores_csv(results: list[ScanResult], path: str | Path) -> None:
    # TODO(A): one row per file; "ERROR" when result.error is set
    raise NotImplementedError
