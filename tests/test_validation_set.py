"""Milestone test: the whole Validation Set must match the brief exactly
(24 finding rows, no extra rows, correct scores, V7 = ERROR)."""

import csv

import pytest

from analyzer import export, service
from conftest import TESTS_DIR, VALIDATION_DIR

pytestmark = pytest.mark.skipif(
    not any(VALIDATION_DIR.glob("*.xml")),
    reason="Copy the Validation Set XML files into data/validation/ first",
)


def _rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return sorted(tuple(r) for r in csv.reader(fh))


def test_validation_set_matches_answer_key(tmp_path):
    results = service.analyze_folder(VALIDATION_DIR)
    export.write_findings_csv(results, tmp_path / "findings.csv")
    export.write_scores_csv(results, tmp_path / "scores.csv")

    got = _rows(tmp_path / "findings.csv")
    expected = _rows(TESTS_DIR / "expected_findings.csv")
    missing = set(expected) - set(got)
    extra = set(got) - set(expected)
    assert not missing and not extra, f"missing={sorted(missing)} extra={sorted(extra)}"

    assert _rows(tmp_path / "scores.csv") == _rows(TESTS_DIR / "expected_scores.csv")
