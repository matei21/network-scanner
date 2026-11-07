"""Public entry points used by the CLI and by the backend (Person B).

Contract: see docs/api_contract.json. Explanations / fix steps are added
later by Person D's ai/ module, not here.
"""

from __future__ import annotations

from pathlib import Path

from .models import ScanResult


def analyze_file(path: str | Path) -> ScanResult:
    """Parse + rules + score for one file. Never raises for bad input:
    returns ScanResult(error=...) instead (V7_broken.xml must not crash)."""
    # TODO(A): parser.parse_file -> rules.findings_for_scan -> scoring.network_score
    raise NotImplementedError


def analyze_folder(folder: str | Path) -> list[ScanResult]:
    """Analyze every *.xml in a folder, sorted by file name."""
    # TODO(A)
    raise NotImplementedError


def to_dict(result: ScanResult) -> dict:
    """Convert a ScanResult to the JSON contract (MACs masked!)."""
    # TODO(A): use privacy.mask_mac for every device MAC
    raise NotImplementedError
