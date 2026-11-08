"""FR-13: every upload / live scan says what changed since the previous scan of the same kind."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
VALIDATION = ROOT / "data" / "validation"


@pytest.fixture
def client(monkeypatch, tmp_path):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from backend.app import database as db
    from backend.app import routes
    from backend.app.main import app

    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(routes, "SCANS_DIR", tmp_path / "scans")
    db.init_db()
    return TestClient(app)


def _upload(client, name, source="test"):
    with open(VALIDATION / name, "rb") as fh:
        return client.post(f"/api/upload?source={source}", files={"file": (name, fh, "text/xml")}).json()


def test_first_scan_has_nothing_to_compare(client):
    assert _upload(client, "V6a_before.xml")["changes"] is None


def test_after_scan_lists_what_changed(client):
    _upload(client, "V6a_before.xml")
    changes = _upload(client, "V6b_after.xml")["changes"]

    assert changes["compared_with"] == "V6a_before.xml"
    assert len(changes["resolved_findings"]) == 3
    assert {(p["port"], p["protocol"]) for p in changes["ports_opened"]} == {(443, "tcp")}
    assert {(p["port"], p["protocol"]) for p in changes["ports_closed"]} == {(80, "tcp"), (1900, "udp"), (23, "tcp")}


def test_unreadable_file_is_never_compared(client):
    _upload(client, "V6a_before.xml")
    broken = _upload(client, "V7_broken.xml")
    after = _upload(client, "V6b_after.xml")

    assert broken["status"] == "error" and broken["changes"] is None
    assert after["changes"]["compared_with"] == "V6a_before.xml"   # skips the broken file


def test_real_and_test_scans_are_compared_separately(client):
    _upload(client, "V6a_before.xml", source="test")
    assert _upload(client, "V6b_after.xml", source="real")["changes"] is None


def test_reopened_scan_shows_the_same_changes(client):
    _upload(client, "V6a_before.xml")
    after = _upload(client, "V6b_after.xml")

    again = client.get(f"/api/scan/{after['scan_id']}").json()
    assert again["changes"]["resolved_findings"] == after["changes"]["resolved_findings"]
