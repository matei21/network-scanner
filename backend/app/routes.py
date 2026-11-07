import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile

from analyzer import export
from analyzer.models import ScanResult
from analyzer.parser import MAX_FILE_BYTES
from analyzer.service import analyze_file, analyze_folder, to_dict

from . import database as db
from .guardrails import detect_network, validate_scan_target
from .models import (
    DeleteResponse,
    DiffResult,
    NetworkInfo,
    ScanHistoryItem,
    ScanRequest,
)
from .scanner import run_nmap_scan

router = APIRouter()

SCANS_DIR = Path("scans")
RESULTS_DIR = Path("results")


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


def _store(result: ScanResult, display_name: str, xml_path: Path) -> dict:
    data = to_dict(result)
    scan_id = db.save_scan(display_name, result.score, str(xml_path))
    db.save_devices(scan_id, [
        {"ip": d["ip"], "mac_masked": d["mac"], "vendor": d["vendor"], "hostname": d["hostname"], "device_type": d["type"]}
        for d in data["devices"]
    ])
    db.save_findings(scan_id, [
        {"ip": f.ip, "port": f.port, "finding_code": f.code, "severity": f.severity}
        for f in result.findings
    ])
    data["scan_id"] = scan_id
    return data


@router.post("/upload")
async def upload_xml(file: UploadFile):
    xml_path = await _save_upload(file, _new_scan_dir())
    result = analyze_file(xml_path)
    if result.error:
        raise HTTPException(422, f"Could not read {result.file}: {result.error}")
    return _store(result, result.file, xml_path)


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
def get_history():
    return [
        ScanHistoryItem(id=s["id"], filename=s["filename"], timestamp=s["timestamp"], network_score=s["network_score"])
        for s in db.get_all_scans()
    ]


@router.get("/diff/{old_scan_id}/{new_scan_id}", response_model=DiffResult)
def get_diff(old_scan_id: int, new_scan_id: int):
    if not db.get_scan(old_scan_id):
        raise HTTPException(404, f"Scan {old_scan_id} not found.")
    if not db.get_scan(new_scan_id):
        raise HTTPException(404, f"Scan {new_scan_id} not found.")
    return db.get_diff(old_scan_id, new_scan_id)


@router.post("/scan")
def live_scan(req: ScanRequest):
    net = detect_network()
    allowlist = [net["subnet"]] if net.get("subnet") else None
    check = validate_scan_target(req.target, allowlist=allowlist, confirmed=req.confirm)
    if not check["allowed"]:
        raise HTTPException(403, check["reason"])

    xml_path = _new_scan_dir() / "live_scan.xml"
    scan_result = run_nmap_scan(req.target, str(xml_path))
    if not scan_result["success"]:
        raise HTTPException(500, scan_result.get("error") or "Scan failed.")

    result = analyze_file(xml_path)
    if result.error:
        raise HTTPException(500, f"nmap output could not be read: {result.error}")
    return _store(result, f"live_{req.target}", xml_path)


@router.post("/batch")
async def batch_process(files: list[UploadFile]):
    folder = _new_scan_dir()
    for file in files:
        await _save_upload(file, folder)

    results = analyze_folder(folder)
    for r in results:
        if r.ok:
            _store(r, r.file, folder / r.file)

    findings_csv = RESULTS_DIR / "findings.csv"
    scores_csv = RESULTS_DIR / "scores.csv"
    export.write_findings_csv(results, findings_csv)
    export.write_scores_csv(results, scores_csv)

    return {
        "processed": len(results),
        "errors": [{"file": r.file, "error": r.error} for r in results if r.error],
        "findings_csv_path": str(findings_csv),
        "scores_csv_path": str(scores_csv),
        "findings_csv": findings_csv.read_text(encoding="utf-8"),
        "scores_csv": scores_csv.read_text(encoding="utf-8"),
    }


@router.get("/network-info", response_model=NetworkInfo)
def network_info():
    return detect_network()


@router.delete("/history", response_model=DeleteResponse)
def delete_history():
    count = db.delete_all_history()
    return DeleteResponse(deleted=count, message=f"Deleted {count} scan(s) and all associated data.")
