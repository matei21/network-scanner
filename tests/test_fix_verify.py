"""Fix -> verify loop: re-checking one port stores a new history entry whose score and findings come
from the normal rules, inside the same guardrail as any live scan (FR-02, FR-10)."""

import pytest

IP = "10.74.130.5"


def _xml(ports: str) -> str:
    return f"""<?xml version="1.0"?>
<nmaprun scanner="nmap" args="nmap" start="1" version="7.94" xmloutputversion="1.05">
<host><status state="up"/>
<address addr="{IP}" addrtype="ipv4"/><address addr="AA:BB:CC:DD:EE:FF" addrtype="mac" vendor="Netgear"/>
<hostnames><hostname name="router" type="PTR"/></hostnames>
<ports>{ports}</ports></host></nmaprun>"""


TELNET = '<port protocol="tcp" portid="23"><state state="open"/><service name="telnet" product="BusyBox telnetd"/></port>'
FTP_OLD = '<port protocol="tcp" portid="21"><state state="open"/><service name="ftp" product="vsftpd" version="2.3.4"/></port>'


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
    monkeypatch.delenv("SCAN_SSID_PREFIX", raising=False)
    monkeypatch.setattr(routes, "detect_network", lambda: {"subnet": "10.74.130.0/24", "gateway": "10.74.130.1"})
    monkeypatch.setattr(routes, "wifi_ssid", lambda: "RSH TeMiMaAl")
    return TestClient(app), routes


def _upload(client, ports):
    r = client.post("/api/upload", files={"file": ("before.xml", _xml(ports).encode(), "text/xml")})
    assert r.status_code == 200
    return r.json()


def _fake_scan(routes, monkeypatch, ports_after, calls):
    def fake(ip, port, udp, output):
        calls.append((ip, port, udp))
        output.write_text(_xml(ports_after), encoding="utf-8")
        return {"success": True, "method": "-sT"}
    monkeypatch.setattr(routes, "run_verify_scan", fake)


def test_fixed_port_creates_history_entry_with_higher_score(client, monkeypatch):
    c, routes = client
    before = _upload(c, TELNET + FTP_OLD)
    assert before["score"] == 50  # TELNET 20 + FTP 10 + OUTDATED 20
    calls = []
    _fake_scan(routes, monkeypatch, "", calls)  # telnet port is now closed

    r = c.post("/api/fix/verify", json={"scan_id": before["scan_id"], "finding_code": "TELNET_OPEN",
                                        "ip": IP, "port": 23, "confirm": True})

    body = r.json()
    assert r.status_code == 200 and body["result"] == "fixed"
    assert (body["old_score"], body["new_score"]) == (50, 70)
    assert calls == [(IP, 23, False)]
    codes = {f["code"] for d in body["scan"]["devices"] for f in d["findings"]}
    assert codes == {"FTP_CLEARTEXT", "OUTDATED_SERVICE"}          # other ports untouched
    assert body["scan"]["verification"]["checked"] == "single_port"
    assert [h["score"] for h in body["scan"]["history"]][-2:] == [50, 70]
    diff = c.get(f"/api/diff/{before['scan_id']}/{body['new_scan_id']}").json()
    assert [f["finding_code"] for f in diff["resolved_findings"]] == ["TELNET_OPEN"]


def test_still_open_is_also_saved_with_same_score(client, monkeypatch):
    c, routes = client
    before = _upload(c, TELNET)
    _fake_scan(routes, monkeypatch, TELNET, [])

    body = c.post("/api/fix/verify", json={"scan_id": before["scan_id"], "finding_code": "TELNET_OPEN",
                                           "ip": IP, "port": 23, "confirm": True}).json()

    assert body["result"] == "still_open" and body["new_score"] == body["old_score"] == 80
    assert len(body["scan"]["history"]) == 2


def test_every_rule_on_the_port_is_reevaluated(client, monkeypatch):
    """vsftpd upgraded: OUTDATED_SERVICE goes away, FTP_CLEARTEXT stays (same port 21)."""
    c, routes = client
    before = _upload(c, FTP_OLD)
    new_ftp = FTP_OLD.replace('version="2.3.4"', 'version="3.0.5"')
    _fake_scan(routes, monkeypatch, new_ftp, [])

    body = c.post("/api/fix/verify", json={"scan_id": before["scan_id"], "finding_code": "OUTDATED_SERVICE",
                                           "ip": IP, "port": 21, "confirm": True}).json()

    assert body["result"] == "fixed"
    assert {f["code"] for d in body["scan"]["devices"] for f in d["findings"]} == {"FTP_CLEARTEXT"}


def test_verify_needs_confirmation_and_stays_in_scope(client, monkeypatch):
    c, routes = client
    before = _upload(c, TELNET)
    monkeypatch.setattr(routes, "run_verify_scan", lambda *a, **k: pytest.fail("must not scan"))

    unconfirmed = c.post("/api/fix/verify", json={"scan_id": before["scan_id"], "finding_code": "TELNET_OPEN",
                                                  "ip": IP, "port": 23, "confirm": False})
    assert unconfirmed.status_code == 403

    routes_detect = lambda: {"subnet": "192.168.50.0/24", "gateway": "192.168.50.1"}  # laptop moved networks
    monkeypatch.setattr(routes, "detect_network", routes_detect)
    outside = c.post("/api/fix/verify", json={"scan_id": before["scan_id"], "finding_code": "TELNET_OPEN",
                                              "ip": IP, "port": 23, "confirm": True})
    assert outside.status_code == 403


def test_unknown_finding_is_refused(client):
    c, _ = client
    before = _upload(c, TELNET)
    r = c.post("/api/fix/verify", json={"scan_id": before["scan_id"], "finding_code": "RDP_EXPOSED",
                                        "ip": IP, "port": 3389, "confirm": True})
    assert r.status_code == 404
