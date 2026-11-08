"""Runs a fix command on THIS computer, only behind a Windows UAC consent prompt.

Safety rules (enforced here, not only in the route):
  - the finding must be on this computer (its IP is one of our own addresses), otherwise nothing runs:
    a command on this laptop cannot fix a router or a camera;
  - the command always comes from our fix templates (never from the request), with a validated port;
  - Windows shows a UAC prompt, so nothing runs without the person clicking "Yes".

The elevated script writes its outcome to a JSON file that the UI polls via /fix/result/{run_id}.
"""

from __future__ import annotations

import json
import re
import tempfile
import time
import uuid
from pathlib import Path

from ai.fix_commands import is_this_pc

RUNS_DIR = Path(tempfile.gettempdir()) / "netscanner_fixes"
_RUN_ID = re.compile(r"^[0-9a-f]{32}$")
_SE_ERR_ACCESSDENIED = 5  # ShellExecute's code when the person answers "No" at the UAC prompt


def _ps_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def _script(command: str, result_path: Path, title: str) -> str:
    return f"""$ErrorActionPreference = 'Stop'
$resultPath = {_ps_quote(str(result_path))}
function Save-Result($ok, $text) {{
    $json = @{{ ok = $ok; output = "$text".Trim(); finished = (Get-Date).ToString('s') }} | ConvertTo-Json -Compress
    [IO.File]::WriteAllText($resultPath, $json, (New-Object System.Text.UTF8Encoding $false))
}}
$Host.UI.RawUI.WindowTitle = {_ps_quote(title)}
Write-Host {_ps_quote(title)} -ForegroundColor Cyan
Write-Host {_ps_quote(command)} -ForegroundColor DarkGray
Write-Host ''
try {{
    $out = & {{ {command} }} 2>&1 | Out-String
    if ($out.Trim()) {{ Write-Host $out }}
    Save-Result $true $out
    Write-Host 'Gata / Done' -ForegroundColor Green
}} catch {{
    $msg = $_ | Out-String
    Save-Result $false $msg
    Write-Host $msg -ForegroundColor Red
}}
Start-Sleep -Seconds 6
"""


def launch_elevated(command: str, ip: str, title: str = "NetScanner fix") -> dict:
    """Start the command in an elevated PowerShell window. Returns {status, run_id?, message?}."""
    if not is_this_pc(ip):
        return {"status": "refused", "message": "target is not this computer"}
    try:
        import ctypes
        shell32 = ctypes.windll.shell32
    except (ImportError, AttributeError):
        return {"status": "error", "code": "fix_not_windows", "message": "Running fixes is only supported on Windows."}

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    script_path = RUNS_DIR / f"{run_id}.ps1"
    result_path = RUNS_DIR / f"{run_id}.json"
    # BOM so Windows PowerShell 5.1 reads the file as UTF-8.
    script_path.write_text(_script(command, result_path, title), encoding="utf-8-sig")

    # -ExecutionPolicy Bypass: the default "Restricted" policy on Windows would refuse to run any .ps1 file.
    rc = shell32.ShellExecuteW(
        None, "runas", "powershell.exe",
        f'-NoProfile -ExecutionPolicy Bypass -File "{script_path}"',
        None, 1,
    )
    if rc == _SE_ERR_ACCESSDENIED:
        script_path.unlink(missing_ok=True)
        return {"status": "denied"}
    if rc <= 32:
        script_path.unlink(missing_ok=True)
        return {"status": "error", "code": "fix_launch_failed", "params": {"rc": rc},
                "message": f"Windows could not start PowerShell (code {rc})."}
    return {"status": "elevated", "run_id": run_id}


def read_result(run_id: str) -> dict:
    """{status: pending|done|unknown, ok?, output?}."""
    if not _RUN_ID.match(run_id or ""):
        return {"status": "unknown"}
    result_path = RUNS_DIR / f"{run_id}.json"
    if not result_path.exists():
        script = RUNS_DIR / f"{run_id}.ps1"
        if not script.exists():
            return {"status": "unknown"}
        # Window never finished (closed early, or UAC prompt left open): give up after 5 minutes.
        if time.time() - script.stat().st_mtime > 300:
            return {"status": "done", "ok": False, "code": "fix_closed_early",
                    "output": "No result: the PowerShell window was closed before finishing."}
        return {"status": "pending"}
    try:
        data = json.loads(result_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {"status": "pending"}
    (RUNS_DIR / f"{run_id}.ps1").unlink(missing_ok=True)
    return {"status": "done", "ok": bool(data.get("ok")), "output": str(data.get("output", ""))[:4000]}
