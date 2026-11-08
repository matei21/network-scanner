import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal

import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from analyzer import export
from analyzer.models import ScanResult
from analyzer.parser import MAX_FILE_BYTES
from analyzer.service import analyze_file, analyze_folder, to_dict

from ai.assistant import Assistant, enrich_scan_data, narrate_scan, suggest_followups, narrate_diff
from ai.fingerprint import guess_device_type, suggest_device_name
from ai.pdf_report import generate_report
from ai.fix_commands import get_fix_command, FIX_COMMANDS

from . import database as db
from .guardrails import build_allowlist, check_ssid, detect_network, parse_target, validate_scan_target, wifi_ssid
from .models import (
    DeleteResponse,
    DiffResult,
    NetworkInfo,
    ScanHistoryItem,
    ScanRequest,
)
from .scanner import get_scan_job, run_nmap_scan, start_scan_job

logger = logging.getLogger(__name__)

router = APIRouter()

SCANS_DIR = Path("scans")
RESULTS_DIR = Path("results")

# "real" = our own network (lab uploads, live scans); "test" = Validation/Test Set files.
Source = Literal["real", "test"]


def _new_scan_dir() -> Path:
    path = SCANS_DIR / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_xml_name(filename: str | None) -> str:
    # Path(...).name drops any directory part, so "../../x.xml" can't escape the scan folder.
    name = Path(filename or "").name
    if not name.lower().endswith(".xml") or name.startswith("."):
        raise HTTPException(400, "Only .xml files are accepted.")
    return name


async def _save_upload(file: UploadFile, folder: Path) -> Path:
    name = _safe_xml_name(file.filename)
    content = await file.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(413, f"{name}: file is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB.")
    path = folder / name
    async with aiofiles.open(path, "wb") as f:
        await f.write(content)
    return path


def _store(result: ScanResult, display_name: str, xml_path: Path, source: Source) -> dict:
    data = to_dict(result)
    if result.ok:
        data = enrich_scan_data(data)
    data["source"] = source
    scan_id = db.save_scan(display_name, result.score, str(xml_path), source)
    db.save_devices(scan_id, [
        {"ip": d["ip"], "mac_masked": d["mac"], "vendor": d["vendor"], "hostname": d["hostname"], "device_type": d["type"]}
        for d in data["devices"]
    ])
    db.save_findings(scan_id, [
        {"ip": f.ip, "port": f.port, "finding_code": f.code, "severity": f.severity}
        for f in result.findings
    ])
    db.save_ports(scan_id, [
        {"ip": d["ip"], **p}
        for d in data["devices"]
        for p in d["open_ports"]
    ])
    data["scan_id"] = scan_id
    # Everything added to `data` before this point (e.g. explanations and fix steps) is kept for re-viewing.
    db.save_snapshot(scan_id, data)
    data["history"] = _score_history(source)
    return data


def _local_date(timestamp: str) -> str:
    """'2026-11-07T18:07:01+00:00' -> '2026-11-07 20:07' in the laptop's time zone."""
    return datetime.fromisoformat(timestamp).astimezone().strftime("%Y-%m-%d %H:%M")


def _score_history(source: str) -> list[dict]:
    """Score trend, oldest first (FR-10). Only scans of the same source, so test files never mix with our network."""
    counts = db.count_findings()
    return [
        {
            "scan_id": s["id"],
            "file": s["filename"],
            "timestamp": s["timestamp"],
            "date": _local_date(s["timestamp"]),
            "score": s["network_score"],
            "findings_count": counts.get(s["id"], 0),
            # A file that could not be read is stored without a score (shown as ERROR, like scores.csv).
            "status": "error" if s["network_score"] is None else "ok",
        }
        for s in reversed(db.get_all_scans(source))
    ]


@router.post("/upload")
async def upload_xml(file: UploadFile, source: Source = "real"):
    xml_path = await _save_upload(file, _new_scan_dir())
    # An unreadable file is a normal result, not a server error: the contract answers
    # status="error" + a clear message, and it is kept in history like in a batch.
    result = analyze_file(xml_path)
    return _store(result, result.file, xml_path, source)


@router.get("/scan/latest")
def get_latest_scan():
    """Return the most recently uploaded/scanned result (what the UI loads on open)."""
    scans = db.get_all_scans(None)
    if not scans:
        raise HTTPException(404, "No scans yet. Upload an XML file or run a live scan.")
    # Prefer the newest readable scan, so a broken file from a batch is not what the UI opens on.
    latest = next((s for s in scans if s["network_score"] is not None), scans[0])
    data = db.get_snapshot(latest["id"])
    if data is None:
        raise HTTPException(404, "Latest scan has no stored snapshot.")
    data["scan_id"] = latest["id"]
    data["timestamp"] = latest["timestamp"]
    data["source"] = latest["source"]
    data["history"] = _score_history(latest["source"])
    return data


@router.get("/scan/{scan_id}")
def get_full_scan(scan_id: int):
    """A past scan in the same format as /upload, so the UI can show it as if it was just scanned."""
    scan = db.get_scan(scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found.")
    data = db.get_snapshot(scan_id)
    if data is None:
        raise HTTPException(404, "This scan was saved before full details were stored. Upload the file again.")
    data["timestamp"] = scan["timestamp"]
    data["source"] = scan["source"]
    data["history"] = _score_history(scan["source"])
    return data


@router.get("/findings/{scan_id}")
def get_findings(scan_id: int):
    if not db.get_scan(scan_id):
        raise HTTPException(404, "Scan not found.")
    return db.get_findings(scan_id)


@router.get("/devices/{scan_id}")
def get_devices(scan_id: int):
    if not db.get_scan(scan_id):
        raise HTTPException(404, "Scan not found.")
    return db.get_devices(scan_id)


@router.get("/score/{scan_id}")
def get_score(scan_id: int):
    scan = db.get_scan(scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found.")
    return {"scan_id": scan_id, "score": scan["network_score"]}


@router.get("/history", response_model=list[ScanHistoryItem])
def get_history(source: Literal["real", "test", "all"] = "real"):
    return [
        ScanHistoryItem(id=s["id"], filename=s["filename"], timestamp=s["timestamp"], network_score=s["network_score"], source=s["source"])
        for s in db.get_all_scans(None if source == "all" else source)
    ]


@router.get("/diff/{old_scan_id}/{new_scan_id}", response_model=DiffResult)
def get_diff(old_scan_id: int, new_scan_id: int):
    old, new = db.get_scan(old_scan_id), db.get_scan(new_scan_id)
    if not old:
        raise HTTPException(404, f"Scan {old_scan_id} not found.")
    if not new:
        raise HTTPException(404, f"Scan {new_scan_id} not found.")
    if old["source"] != new["source"]:
        raise HTTPException(400, f"Scan {old_scan_id} is '{old['source']}' and scan {new_scan_id} is '{new['source']}': only scans of the same kind can be compared.")
    return db.get_diff(old_scan_id, new_scan_id)


def _live_check(requested_target: str | None, confirmed: bool) -> dict:
    """Every guardrail a live scan must pass. Same answer for the preview, the button and POST /scan."""
    net = detect_network()
    # No target from the UI button = scan the network we are connected to, like `python -m backend.scan --confirm`.
    target = (requested_target or net.get("subnet") or "").strip()
    # Empty allowlist (network not detected) -> validate_scan_target refuses (fail closed).
    check = validate_scan_target(target, allowlist=build_allowlist(net.get("subnet")), confirmed=confirmed)
    ssid = wifi_ssid()
    if check["allowed"] or check.get("code") == "not_confirmed":
        check = check_ssid(ssid) or check
    if check["allowed"]:
        net_ = parse_target(target)  # canonical form, the only thing nmap ever receives
        target = str(net_.network_address) if net_.prefixlen == 32 else str(net_)
    return {**check, "target": target, "ssid": ssid, "subnet": net.get("subnet")}


def _store_live(xml_path: Path, target: str) -> dict:
    result = analyze_file(xml_path)
    if result.error:
        raise ValueError(f"nmap output could not be read: {result.error}")
    return _store(result, f"live_{target}", xml_path, "real")


@router.get("/scan/live/preview")
def live_scan_preview(target: str | None = None):
    """What the scan button would scan and on which Wi-Fi; never scans."""
    return _live_check(target, confirmed=True)


@router.post("/scan/live", status_code=202)
def start_live_scan(req: ScanRequest):
    """Start a live scan in the background; poll GET /scan/live/{job_id} for progress."""
    check = _live_check(req.target, req.confirm)
    if not check["allowed"]:
        raise HTTPException(403, check["reason"])
    try:
        target = check["target"]
        job = start_scan_job(target, _new_scan_dir() / "live_scan.xml", lambda path: _store_live(path, target))
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    return job.to_dict()


@router.get("/scan/live/{job_id}")
def live_scan_status(job_id: str):
    job = get_scan_job(job_id)
    if not job:
        raise HTTPException(404, "Scan not found.")
    return job.to_dict()


@router.post("/scan/live/{job_id}/cancel")
def cancel_live_scan(job_id: str):
    job = get_scan_job(job_id)
    if not job:
        raise HTTPException(404, "Scan not found.")
    job.cancel()
    return job.to_dict()


@router.post("/scan")
def live_scan(req: ScanRequest):
    """Blocking live scan (kept for scripts); the UI uses /scan/live."""
    check = _live_check(req.target, req.confirm)
    if not check["allowed"]:
        raise HTTPException(403, check["reason"])
    target = check["target"]

    xml_path = _new_scan_dir() / "live_scan.xml"
    scan_result = run_nmap_scan(target, str(xml_path))
    if not scan_result["success"]:
        detail = scan_result.get("error") or (scan_result.get("stderr") or "").strip()[:300]
        raise HTTPException(500, detail or "Scan failed.")

    result = analyze_file(xml_path)
    if result.error:
        raise HTTPException(500, f"nmap output could not be read: {result.error}")
    return _store(result, f"live_{target}", xml_path, "real")


def _new_batch_dir() -> Path:
    """results/batch_<date_time>_<id>/ : a new folder for every /batch call."""
    path = RESULTS_DIR / f"batch_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"
    path.mkdir(parents=True, exist_ok=False)
    return path


@router.post("/batch")
async def batch_process(files: list[UploadFile], source: Source = "test"):
    folder = _new_scan_dir()
    for file in files:
        await _save_upload(file, folder)

    results = analyze_folder(folder)
    # Unreadable files are stored too, so the UI shows the same ERROR rows as scores.csv.
    for r in results:
        _store(r, r.file, folder / r.file, source)

    # Each batch gets its own folder, so the API can never overwrite
    # results/findings.csv and results/scores.csv, the files made with
    # "python -m analyzer <folder> --out results/" for the Test Set upload.
    out_dir = _new_batch_dir()
    findings_csv = out_dir / "findings.csv"
    scores_csv = out_dir / "scores.csv"
    export.write_findings_csv(results, findings_csv)
    export.write_scores_csv(results, scores_csv)

    return {
        "processed": len(results),
        "errors": [{"file": r.file, "error": r.error} for r in results if r.error],
        "output_folder": str(out_dir),
        "findings_csv_path": str(findings_csv),
        "scores_csv_path": str(scores_csv),
        "findings_csv": findings_csv.read_text(encoding="utf-8"),
        "scores_csv": scores_csv.read_text(encoding="utf-8"),
    }


@router.get("/network-info", response_model=NetworkInfo)
def network_info():
    return {**detect_network(), "ssid": wifi_ssid()}


@router.delete("/history", response_model=DeleteResponse)
@router.delete("/scans/history", response_model=DeleteResponse)
def delete_history():
    count = db.delete_all_history()
    # Raw nmap XML holds unmasked MACs and hostnames, so it must go too (NFR-02).
    files = 0
    if SCANS_DIR.is_dir():
        for entry in SCANS_DIR.iterdir():
            if entry.is_dir():
                files += sum(1 for p in entry.rglob("*") if p.is_file())
                shutil.rmtree(entry)
            else:
                files += 1
                entry.unlink()
    return DeleteResponse(deleted=count, message=f"Deleted {count} scan(s), {files} scan file(s) and all associated data.")


# ── Frontend-compatible aliases ─────────────────────────────────────
# Frontend api.js expects these paths; the routes above use shorter names.

@router.post("/scan/upload")
async def upload_xml_alias(file: UploadFile, source: Source = "real"):
    return await upload_xml(file, source)


@router.get("/scans/history")
def get_history_alias(source: Literal["real", "test", "all"] = "real"):
    return get_history(source)


# ── AI Assistant endpoint (FR-12) ──────────────────────────────────

class AskRequest(BaseModel):
    question: str
    scan_id: int | None = None
    language: str = "ro"


class DetailedFixRequest(BaseModel):
    finding_code: str
    device_ip: str
    scan_id: int | None = None
    language: str = "ro"


# Keep one Assistant per scan to preserve conversation history within a session.
_assistants: dict[int, Assistant] = {}


def _get_assistant(scan_id: int) -> Assistant:
    if scan_id in _assistants:
        return _assistants[scan_id]
    data = db.get_snapshot(scan_id)
    if data is None:
        raise HTTPException(404, "Scan not found or has no snapshot.")
    assistant = Assistant(data, enable_cloud=False, enable_local=True, groq_api_key=_ai_settings.get("groq_api_key"))
    _assistants[scan_id] = assistant
    if len(_assistants) > 20:
        oldest = next(iter(_assistants))
        del _assistants[oldest]
    return assistant


@router.post("/assistant/ask")
def assistant_ask(req: AskRequest):
    scan_id = req.scan_id
    if scan_id is None:
        scans = db.get_all_scans(None)
        if not scans:
            raise HTTPException(404, "No scans available.")
        scan_id = scans[0]["id"]

    assistant = _get_assistant(scan_id)
    result = assistant.ask(req.question, req.language)

    # Extract cited findings from the scan data for grounding display (NFR-06)
    cites = []
    scan_data = db.get_snapshot(scan_id) or {}
    for device in scan_data.get("devices", []):
        for finding in device.get("findings", []):
            code = finding.get("code", "")
            if code and code.lower() in result["text"].lower():
                cites.append({
                    "ip": finding.get("ip", device.get("ip")),
                    "port": finding.get("port"),
                    "code": code,
                })

    detected_lang = result.get("detected_language", req.language)
    followups = suggest_followups(scan_data, result["text"], detected_lang)

    return {
        "answer": result["text"],
        "source": result["source"],
        "agent": result.get("agent", "monolithic"),
        "detected_language": detected_lang,
        "cites": cites,
        "followups": followups,
    }


@router.post("/assistant/detailed-fix")
def assistant_detailed_fix(req: DetailedFixRequest):
    """Get DuckDuckGo-enriched fix instructions for a specific finding on a device."""
    scan_id = req.scan_id
    if scan_id is None:
        scans = db.get_all_scans(None)
        if not scans:
            raise HTTPException(404, "No scans available.")
        scan_id = scans[0]["id"]

    scan_data = db.get_snapshot(scan_id)
    if scan_data is None:
        raise HTTPException(404, "Scan not found or has no snapshot.")

    device_info = {}
    for device in scan_data.get("devices", []):
        if device.get("ip") == req.device_ip:
            device_info = {"ip": device.get("ip"), "vendor": device.get("vendor", ""), "hostname": device.get("hostname", ""), "type": device.get("type", "")}
            for finding in device.get("findings", []):
                if finding.get("code") == req.finding_code:
                    device_info["port"] = finding.get("port", "")
                    device_info["service"] = finding.get("service", "")
                    device_info["product"] = finding.get("product", "")
                    break
            break

    if not device_info:
        raise HTTPException(404, f"Device {req.device_ip} not found in scan.")

    assistant = _get_assistant(scan_id)
    result = assistant.get_detailed_fix(req.finding_code, device_info, req.language)

    return {
        "fix_text": result.get("text", ""),
        "source": result.get("source", "template"),
        "search_results": result.get("search_results", []),
        "generic_advice": result.get("generic_advice", ""),
        "template_steps": result.get("template_steps", []),
    }


@router.get("/assistant/narrate/{scan_id}")
def assistant_narrate(scan_id: int, language: str = "ro"):
    """Generate a narrative summary of a scan (Scan Narrator feature)."""
    data = db.get_snapshot(scan_id)
    if data is None:
        raise HTTPException(404, "Scan not found or has no snapshot.")
    return narrate_scan(data, language)


@router.get("/assistant/narrate")
def assistant_narrate_latest(language: str = "ro"):
    """Narrate the most recent scan."""
    scans = db.get_all_scans(None)
    if not scans:
        raise HTTPException(404, "No scans available.")
    data = db.get_snapshot(scans[0]["id"])
    if data is None:
        raise HTTPException(404, "Latest scan has no snapshot.")
    return narrate_scan(data, language)


# ── Scan Diff Narration ───────────────────────────────────────────────

@router.get("/assistant/narrate-diff/{old_scan_id}/{new_scan_id}")
def assistant_narrate_diff(old_scan_id: int, new_scan_id: int, language: str = "ro"):
    """Generate a narrative comparing two scans."""
    old, new = db.get_scan(old_scan_id), db.get_scan(new_scan_id)
    if not old:
        raise HTTPException(404, f"Scan {old_scan_id} not found.")
    if not new:
        raise HTTPException(404, f"Scan {new_scan_id} not found.")
    diff_data = db.get_diff(old_scan_id, new_scan_id)
    return narrate_diff(diff_data, language, compared_with=old["filename"])


@router.get("/assistant/narrate-diff-latest/{scan_id}")
def assistant_narrate_diff_vs_previous(scan_id: int, language: str = "ro"):
    """Compare a scan with the most recent previous scan of the same source."""
    scan = db.get_scan(scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found.")
    # An unreadable file has nothing to compare, and is never used as the "before" either.
    if scan["network_score"] is None:
        raise HTTPException(404, "An unreadable file cannot be compared.")
    all_scans = db.get_all_scans(scan["source"])
    prev = next((s for s in all_scans if s["id"] < scan_id and s["network_score"] is not None), None)
    if not prev:
        raise HTTPException(404, "No previous scan to compare against.")
    diff_data = db.get_diff(prev["id"], scan_id)
    return narrate_diff(diff_data, language, compared_with=prev["filename"])


# ── Device Naming ─────────────────────────────────────────────────────

class DeviceNameRequest(BaseModel):
    ip: str
    custom_name: str
    suggested_name: str | None = None


@router.get("/device-names")
def get_device_names():
    """Get all custom device names."""
    return db.get_device_names()


@router.put("/device-names")
def save_device_name(req: DeviceNameRequest):
    """Save a custom name for a device (e.g. 'Telefonul lui Andrei')."""
    db.save_device_name(req.ip, req.custom_name, req.suggested_name)
    return {"ok": True, "ip": req.ip, "custom_name": req.custom_name}


@router.get("/device-names/suggest/{scan_id}")
def suggest_device_names(scan_id: int, language: str = "ro"):
    """Auto-suggest friendly names for all devices in a scan."""
    data = db.get_snapshot(scan_id)
    if data is None:
        raise HTTPException(404, "Scan not found or has no snapshot.")
    suggestions = {}
    for device in data.get("devices", []):
        ip = device.get("ip", "")
        if ip:
            suggestions[ip] = suggest_device_name(device, language)
    return suggestions


# ── PDF Report ────────────────────────────────────────────────────────

@router.get("/report/pdf/{scan_id}")
def download_pdf_report(scan_id: int, language: str = "ro"):
    """Generate and download a PDF report for a scan."""
    data = db.get_snapshot(scan_id)
    if data is None:
        raise HTTPException(404, "Scan not found or has no snapshot.")
    scan = db.get_scan(scan_id)
    if scan:
        data["timestamp"] = scan["timestamp"]
    pdf_bytes = generate_report(data, language)
    filename = f"network_report_{scan_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/report/pdf")
def download_pdf_report_latest(language: str = "ro"):
    """Generate PDF report for the latest scan."""
    scans = db.get_all_scans(None)
    if not scans:
        raise HTTPException(404, "No scans available.")
    return download_pdf_report(scans[0]["id"], language)


# ── AI Settings ───────────────────────────────────────────────────────

class AISettingsRequest(BaseModel):
    provider: str = "local"
    groq_api_key: str | None = None

_ai_settings: dict = {"provider": "local", "groq_api_key": None}


@router.get("/settings/ai")
def get_ai_settings():
    return {"provider": _ai_settings["provider"], "has_groq_key": bool(_ai_settings.get("groq_api_key"))}


@router.put("/settings/ai")
def update_ai_settings(req: AISettingsRequest):
    _ai_settings["provider"] = req.provider
    if req.groq_api_key is not None:
        _ai_settings["groq_api_key"] = req.groq_api_key
    _assistants.clear()
    return {"provider": _ai_settings["provider"], "has_groq_key": bool(_ai_settings.get("groq_api_key"))}


# ── Fix Commands & Magic Portal ───────────────────────────────────────

class FixRequest(BaseModel):
    finding_code: str
    ip: str
    port: int | None = None
    gateway: str | None = None
    language: str = "ro"


@router.post("/fix/info")
def get_fix_info(req: FixRequest):
    """Get the fix command/portal info for a finding (without executing)."""
    params = {"ip": req.ip, "port": str(req.port or 0), "gateway": req.gateway or "192.168.1.1"}
    result = get_fix_command(req.finding_code, params, req.language)
    if not result:
        raise HTTPException(404, f"No fix template for {req.finding_code}")
    return result


_MANUAL_FIX_MESSAGE = {
    "ro": ("Din motive de siguranta, aplicatia nu ruleaza comenzi pe calculatorul tau. "
           "Copiaza comanda si ruleaz-o tu, in PowerShell ca administrator, pe dispozitivul {ip}."),
    "en": ("For your safety, the app never runs commands on your computer. "
           "Copy the command and run it yourself, in PowerShell as administrator, on the device {ip}."),
}


@router.post("/fix/execute")
def execute_fix(req: FixRequest):
    """Show-only: never runs anything (security fix).

    Running admin PowerShell from a web API let any caller change this laptop's
    system settings, and the commands acted on this laptop even when the finding
    was on another device. The brief asks for steps a person follows (FR-08) and
    admin rights only for the live scan (NFR-04), so the command is returned for
    the user to run themselves on the right device.
    """
    params = {"ip": req.ip, "port": str(req.port or 0), "gateway": req.gateway or "192.168.1.1"}
    fix = get_fix_command(req.finding_code, params, req.language)
    if not fix:
        raise HTTPException(404, f"No fix template for {req.finding_code}")

    if fix["fix_type"] == "portal":
        return {"status": "portal", "portal_url": fix.get("portal_url", ""), "message": fix["explanation"]}

    lang = "ro" if req.language == "ro" else "en"
    return {
        "status": "manual",
        "executed": False,
        "command": fix.get("command", ""),
        "requires_admin": fix.get("requires_admin", False),
        "explanation": fix["explanation"],
        "message": _MANUAL_FIX_MESSAGE[lang].format(ip=req.ip),
    }
