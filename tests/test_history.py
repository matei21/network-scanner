"""History entries carry the fields the UI's HistoryView reads (scan_id, date, score, findings_count)."""

from backend.app import database as db
from backend.app import routes


def test_history_has_the_fields_the_ui_reads(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    before = db.save_scan("scan_01_before.xml", 0, None, "real")
    db.save_findings(before, [
        {"ip": "10.0.0.2", "port": 23, "finding_code": "TELNET_OPEN", "severity": "high"},
        {"ip": "10.0.0.2", "port": 6379, "finding_code": "DB_EXPOSED", "severity": "high"},
    ])
    after = db.save_scan("scan_02_after.xml", 100, None, "real")
    db.save_scan("V1_home_basic.xml", 90, None, "test")

    history = routes._score_history("real")

    assert [h["scan_id"] for h in history] == [before, after]
    assert [h["findings_count"] for h in history] == [2, 0]
    assert [h["score"] for h in history] == [0, 100]
    assert all(len(h["date"]) == len("2026-11-07 20:07") for h in history)
    assert [h["status"] for h in history] == ["ok", "ok"]


def test_unreadable_file_is_listed_as_error(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    db.save_scan("V1_home_basic.xml", 90, None, "test")
    db.save_scan("V7_broken.xml", None, None, "test")

    history = routes._score_history("test")

    assert [(h["file"], h["score"], h["status"]) for h in history] == [
        ("V1_home_basic.xml", 90, "ok"),
        ("V7_broken.xml", None, "error"),
    ]
