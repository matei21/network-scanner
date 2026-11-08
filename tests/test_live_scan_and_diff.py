"""The UI scan button (no target) scans the connected subnet, only on the team hotspot, in the background
with progress and cancel; refusals carry a clear reason; the "changes since last scan" text lists
opened/closed ports and says what it compares with (FR-02, FR-10, FR-13)."""

import pytest

from ai.assistant import narrate_diff
from backend.app import guardrails, scanner


# --- API: scan button ----------------------------------------------------------------

def _client(monkeypatch, tmp_path, ssid="RSH TeMiMaAl"):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from backend.app import database as db
    from backend.app import routes
    from backend.app.main import app

    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    monkeypatch.delenv("SCAN_SSID_PREFIX", raising=False)
    monkeypatch.setattr(routes, "detect_network", lambda: {"subnet": "10.74.130.0/24", "gateway": "10.74.130.53"})
    monkeypatch.setattr(routes, "wifi_ssid", lambda: ssid)
    started = []

    class FakeJob:
        def to_dict(self):
            return {"job_id": "j1", "status": "running", "target": started[-1]}

    monkeypatch.setattr(routes, "start_scan_job", lambda target, out, done: started.append(target) or FakeJob())
    return TestClient(app), started


def test_scan_button_without_target_scans_the_connected_subnet(monkeypatch, tmp_path):
    client, started = _client(monkeypatch, tmp_path)

    r = client.post("/api/scan/live", json={"confirm": True})

    assert r.status_code == 202 and r.json()["job_id"] == "j1"
    assert started == ["10.74.130.0/24"]


def test_preview_shows_target_and_wifi_without_scanning(monkeypatch, tmp_path):
    client, started = _client(monkeypatch, tmp_path)

    p = client.get("/api/scan/live/preview").json()

    assert p["allowed"] is True and p["target"] == "10.74.130.0/24" and p["ssid"] == "RSH TeMiMaAl"
    assert started == []


@pytest.mark.parametrize("ssid", ["UnivBuc Free", None])
def test_not_on_the_team_hotspot_is_refused(monkeypatch, tmp_path, ssid):
    client, started = _client(monkeypatch, tmp_path, ssid=ssid)

    r = client.post("/api/scan/live", json={"confirm": True})

    assert r.status_code == 403 and "hotspot" in r.json()["detail"]
    assert started == []


def test_public_ip_and_missing_confirm_explain_why(monkeypatch, tmp_path):
    client, started = _client(monkeypatch, tmp_path)

    public = client.post("/api/scan/live", json={"target": "8.8.8.8", "confirm": True})
    unconfirmed = client.post("/api/scan/live", json={"confirm": False})

    assert public.status_code == 403 and "public" in public.json()["detail"]
    assert unconfirmed.status_code == 403 and "confirm" in unconfirmed.json()["detail"]
    assert started == []


# --- hotspot check and progress parsing ---------------------------------------------

def test_ssid_prefix_can_be_switched_off(monkeypatch):
    monkeypatch.setenv("SCAN_SSID_PREFIX", "")
    assert guardrails.check_ssid("UnivBuc Free") is None
    monkeypatch.setenv("SCAN_SSID_PREFIX", "RSH")
    assert guardrails.check_ssid("rsh temimaal") is None          # not case-sensitive
    assert guardrails.check_ssid("Hotspot cart")["allowed"] is False


def test_progress_line_from_nmap_is_understood():
    m = scanner._PROGRESS.match("SYN Stealth Scan Timing: About 45.20% done; ETC: 03:12 (0:01:02 remaining)")
    assert m and scanner._phase_key(m["phase"]) == "tcp"
    assert float(m["pct"]) == 45.2 and m["left"] == "0:01:02"


# --- diff text ---------------------------------------------------------------------------

def _diff(**changes):
    base = {"old_score": 0, "new_score": 70, "resolved_findings": [], "new_findings": [],
            "devices_added": [], "devices_removed": [], "ports_opened": [], "ports_closed": []}
    return {**base, **changes}


def test_diff_text_lists_closed_ports_and_what_it_compares_with():
    diff = _diff(
        devices_removed=["10.74.130.9"],
        ports_closed=[
            {"ip": "10.74.130.252", "port": 2323, "protocol": "tcp", "service": "telnet"},
            {"ip": "10.74.130.9", "port": 135, "protocol": "tcp", "service": "tcpwrapped"},
        ],
    )
    text = narrate_diff(diff, "ro", compared_with="scan_01_before.xml")["narrative"]

    assert text.startswith("Comparat cu: scan_01_before.xml")
    assert "1 port inchis" in text and "2323/tcp (telnet) pe 10.74.130.252" in text
    assert "135/tcp" not in text  # that device disappeared: already said in the device line


def test_a_newly_opened_port_is_a_change():
    diff = _diff(old_score=100, new_score=100,
                 ports_opened=[{"ip": "192.168.1.1", "port": 443, "protocol": "tcp", "service": "http"}])
    text = narrate_diff(diff, "en")["narrative"]

    assert "1 opened port" in text and "443/tcp (http) on 192.168.1.1" in text
    assert "No changes" not in text
