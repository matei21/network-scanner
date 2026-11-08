"""Security regressions: only our own UI (on this laptop) may call the API from a browser,
and fix commands run only for findings on THIS computer, from our templates, behind a UAC prompt."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


# --- Source checks: run everywhere, no backend packages needed -----------------

_PROGRAM_STARTERS = ("import subprocess", "subprocess.", "Popen(", "os.system(", "os.popen(", "os.startfile(")


def test_routes_never_run_system_commands():
    src = (ROOT / "backend" / "app" / "routes.py").read_text(encoding="utf-8")
    # Code that starts programs. (The word "PowerShell" may appear in user-facing text.)
    for forbidden in _PROGRAM_STARTERS + ("ShellExecute",):
        assert forbidden not in src, f"routes.py must not start programs ({forbidden})"


def test_fix_runner_only_starts_programs_through_uac():
    """The one place that starts a program does it via ShellExecute 'runas' (Windows consent prompt)."""
    src = (ROOT / "backend" / "app" / "fix_runner.py").read_text(encoding="utf-8")
    for forbidden in _PROGRAM_STARTERS:
        assert forbidden not in src, f"fix_runner.py must only use the UAC prompt ({forbidden})"
    assert '"runas"' in src
    assert "if not is_this_pc(ip):" in src


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


def test_fix_for_another_device_never_runs_anything(monkeypatch):
    import subprocess
    client = _client()
    from backend.app import fix_runner
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("a command was executed"))
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("a command was executed"))
    monkeypatch.setattr(fix_runner, "launch_elevated", lambda *a, **k: pytest.fail("a command was executed"))
    monkeypatch.setattr(fix_runner, "is_this_pc", lambda ip: False)

    # An IP that is in no stored scan: device type unknown, so it could be a Windows PC.
    r = client.post("/api/fix/execute", json={"finding_code": "DB_EXPOSED", "ip": "192.0.2.40",
                                              "port": 3306, "language": "en"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("remote", "portal") and body["executed"] is False
    assert "3306" in body["command"]          # shown so the user can run it on that machine
    assert "192.0.2.40" in body["message"]


def test_fix_for_this_pc_goes_through_uac_with_template_command(monkeypatch):
    client = _client()
    from backend.app import fix_runner
    calls = []
    monkeypatch.setattr(fix_runner, "is_this_pc", lambda ip: True)
    monkeypatch.setattr(fix_runner, "launch_elevated",
                        lambda command, ip, title="": calls.append((command, ip)) or {"status": "elevated", "run_id": "a" * 32})

    r = client.post("/api/fix/execute", json={"finding_code": "DB_EXPOSED", "ip": "127.0.0.1",
                                              "port": 3306, "language": "en"})
    body = r.json()
    assert body["status"] == "elevated" and body["run_id"] == "a" * 32
    command, ip = calls[0]
    assert ip == "127.0.0.1"
    assert "-LocalPort 3306" in command and "New-NetFirewallRule" in command


def test_fix_runner_refuses_other_devices_even_if_called_directly():
    pytest.importorskip("fastapi")
    from backend.app import fix_runner
    assert fix_runner.launch_elevated("Get-Date", "192.0.2.123")["status"] == "refused"


def test_fix_result_rejects_path_tricks():
    pytest.importorskip("fastapi")
    from backend.app import fix_runner
    assert fix_runner.read_result("../../windows/win.ini")["status"] == "unknown"


def test_port_is_validated_before_it_reaches_a_command():
    from ai.fix_commands import get_fix_command
    fix = get_fix_command("DB_EXPOSED", {"port": "3306; Remove-Item C:\\ -Recurse"}, "en", is_this_pc=True)
    assert "Remove-Item" not in fix["command"] and fix["can_run"] is False


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
