"""Standard network score: max(0, 100 - sum(points of all findings))."""

from __future__ import annotations

from .models import Finding


def network_score(findings: list[Finding]) -> int:
    return max(0, 100 - sum(f.points for f in findings))
