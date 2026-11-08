"""Security regressions: the API must not run system commands, and only our own
UI (on this laptop) may call it from a browser."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


# --- Source checks: run everywhere, no backend packages needed -----------------

def test_routes_never_run_system_commands():
    src = (ROOT / "backend" / "app" / "routes.py").read_text(encoding="utf-8")
    # Code that starts programs. (The word "PowerShell" may appear in user-facing text.)
    for forbidden in ("import subprocess", "subprocess.", "Popen(", "os.system(", "os.popen(", "os.startfile("):
        assert forbidden not in src, f"routes.py must not start programs ({forbidden})"


def test_batch_never_writes_the_upload_csvs():
    """/batch must not overwrite results/findings.csv or results/scores.csv (the Test Set upload)."""
    src = (ROOT / "backend" / "app" / "routes.py").read_text(encoding="utf-8")
    compact = src.replace(" ", "")
    assert 'RESULTS_DIR/"findings.csv"' not in compact
    assert 'RESULTS_DIR/"scores.csv"' not in compact


def test_cors_is_not_open_to_every_website():
    src = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    assert 'allow_origins=["*"]' not in src.replace(" ", "")
    assert "allow_credentials=True" not in src.replace(" ", "")
    assert "TrustedHostMiddleware" in src


# --- Live API checks: skipped where the backend cannot be loaded -----------------

def _client():
    pytest.importorskip("httpx")
    try:
        from fastapi.testclient import TestClient
        from backend.app.main import app
    except Exception as exc:  # missing optional packages or Python version
        pytest.skip(f"backend not importable here: {type(exc).__name__}")
    return TestClient(app)


def test_fix_execute_never_runs_anything(monkeypatch):
    import subprocess
    client = _client()
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("a command was executed"))
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("a command was executed"))

    r = client.post("/api/fix/execute", json={"finding_code": "DB_EXPOSED", "ip": "192.168.1.40",
                                              "port": 3306, "language": "en"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "manual" and body["executed"] is False
    assert "3306" in body["command"]
    assert "192.168.1.40" in body["message"]


def test_other_websites_get_no_cors_permission():
    client = _client()
    r = client.options("/api/settings/ai", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "PUT"})
    assert r.headers.get("access-control-allow-origin") is None


def test_our_ui_gets_cors_permission():
    client = _client()
    r = client.options("/api/settings/ai", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "PUT"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_batch_writes_to_its_own_folder(tmp_path, monkeypatch):
    client = _client()
    from backend.app import routes
    monkeypatch.setattr(routes, "RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(routes, "SCANS_DIR", tmp_path / "scans")
    upload = tmp_path / "results" / "findings.csv"
    upload.parent.mkdir(parents=True)
    upload.write_text("prepared for the Test Set upload", encoding="utf-8")

    v1 = ROOT / "data" / "validation" / "V1_home_basic.xml"
    files = [("files", (v1.name, v1.read_bytes(), "text/xml"))]
    first = client.post("/api/batch", files=files).json()
    second = client.post("/api/batch", files=files).json()

    assert upload.read_text(encoding="utf-8") == "prepared for the Test Set upload"
    assert first["output_folder"] != second["output_folder"]
    assert "HTTP_ADMIN_CLEARTEXT" in first["findings_csv"]


def test_requests_for_other_host_names_are_refused():
    client = _client()
    r = client.get("/api/settings/ai", headers={"Host": "attacker.example"})
    assert r.status_code == 400
