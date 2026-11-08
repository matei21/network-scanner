"""NFR-09: every message the API sends to the UI exists in Romanian and English, in the UI's language."""

import re
import string

import pytest

from backend.app import guardrails, i18n

PLACEHOLDERS = lambda text: {name for _, name, _, _ in string.Formatter().parse(text) if name}


@pytest.mark.parametrize("key", sorted(i18n.MESSAGES))
def test_every_message_has_both_languages_with_the_same_placeholders(key):
    en, ro = i18n.MESSAGES[key]
    assert en.strip() and ro.strip()
    assert PLACEHOLDERS(en) == PLACEHOLDERS(ro), key


ALLOW = ["10.74.130.0/24"]
GUARD_CASES = [
    guardrails.validate_scan_target("not-an-ip", ALLOW, True),
    guardrails.validate_scan_target("8.8.8.8", ALLOW, True),
    guardrails.validate_scan_target("10.74.130.0/24", [], True),
    guardrails.validate_scan_target("10.0.0.0/16", ["10.0.0.0/8"], True),
    guardrails.validate_scan_target("192.168.1.0/24", ALLOW, True),
    guardrails.validate_scan_target("10.74.130.0/24", ALLOW, False),
    guardrails.validate_scan_target("10.74.130.0/24", ALLOW, True),
]


@pytest.mark.parametrize("check", GUARD_CASES, ids=lambda c: c["code"])
def test_every_guardrail_decision_is_translated(monkeypatch, check):
    token = i18n.set_language("ro")
    try:
        ro = i18n.guard_reason(check)
    finally:
        i18n.reset_language(token)
    assert f"guard_{check['code']}" in i18n.MESSAGES
    assert ro and ro != check["reason"]          # really Romanian, not the English fallback


def test_hotspot_refusals_are_translated(monkeypatch):
    monkeypatch.setenv("SCAN_SSID_PREFIX", "RSH")
    token = i18n.set_language("ro")
    try:
        for check in (guardrails.check_ssid(None), guardrails.check_ssid("UnivBuc Free")):
            assert i18n.guard_reason(check) != check["reason"]
    finally:
        i18n.reset_language(token)


@pytest.fixture
def client(monkeypatch, tmp_path):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from backend.app import database as db
    from backend.app import routes
    from backend.app.main import app

    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(routes, "SCANS_DIR", tmp_path / "scans")
    monkeypatch.setattr(routes, "detect_network", lambda: {"subnet": "10.74.130.0/24"})
    monkeypatch.setattr(routes, "wifi_ssid", lambda: "RSH TeMiMaAl")
    db.init_db()
    return TestClient(app)


def test_api_answers_in_the_language_the_ui_asks_for(client):
    bad_file = {"file": ("notes.txt", b"hello", "text/plain")}
    ro = client.post("/api/upload", files=bad_file, headers={"Accept-Language": "ro"})
    en = client.post("/api/upload", files=bad_file, headers={"Accept-Language": "en"})
    plain = client.post("/api/upload", files=bad_file)

    assert ro.json()["detail"] == "Sunt acceptate doar fisiere .xml."
    assert en.json()["detail"] == plain.json()["detail"] == "Only .xml files are accepted."


def test_scan_refusal_and_preview_follow_the_language(client):
    ro = {"Accept-Language": "ro"}
    refused = client.post("/api/scan/live", json={"target": "8.8.8.8", "confirm": True}, headers=ro)
    preview = client.get("/api/scan/live/preview", headers=ro).json()

    assert refused.status_code == 403 and "adresa publica" in refused.json()["detail"]
    assert preview["allowed"] and "face parte din reteaua ta" in preview["reason"]


def test_unreadable_upload_is_marked_for_the_ui_to_explain(client):
    broken = {"file": ("V7_broken.xml", b"<?xml version='1.0'?><nmaprun><host>", "text/xml")}
    data = client.post("/api/upload", files=broken, headers={"Accept-Language": "ro"}).json()

    assert data["status"] == "error" and data["error_code"] == "unreadable" and data["error"]
