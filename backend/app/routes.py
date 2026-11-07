import csv
import io
import uuid
from pathlib import Path

import aiofiles
from defusedxml import ElementTree as SafeET
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from . import database as db
from .guardrails import detect_network, mask_mac, validate_scan_target
from .models import (
    DeleteResponse,
    DiffResult,
    NetworkInfo,
    ScanHistoryItem,
    ScanRequest,
    ScanResult,
)
from .scanner import run_nmap_scan

router = APIRouter()

SCANS_DIR = Path("scans")
SCANS_DIR.mkdir(exist_ok=True)


def analyze_file(path: str) -> dict:
    """Mock analyzer — Person A will replace this with the real implementation."""
    return {
        "score": 90,
        "findings": [
            {"ip": "192.168.1.1", "port": 80, "finding_code": "HTTP_ADMIN_CLEARTEXT", "severity": "medium"},
        ],
        "devices": [
            {"ip": "192.168.1.1", "mac_masked": "AA:BB:CC:XX:XX:XX", "vendor": "TP-Link", "hostname": "router", "device_type": "router"},
        ],
    }


def _mask_devices(devices: list[dict]) -> list[dict]:
    for d in devices:
        raw_mac = d.get("mac") or d.get("mac_masked") or ""
        d["mac_masked"] = mask_mac(raw_mac) if ":" in raw_mac and "XX" not in raw_mac else raw_mac
        d.pop("mac", None)
    return devices


@router.post("/upload", response_model=ScanResult)
async def upload_xml(file: UploadFile):
    if not file.filename or not file.filename.endswith(".xml"):
        raise HTTPException(400, "Only .xml files are accepted.")

    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    xml_path = SCANS_DIR / safe_name

    content = await file.read()
    try:
        SafeET.fromstring(content)
    except Exception:
        raise HTTPException(400, "Invalid or malicious XML file.")

    async with aiofiles.open(xml_path, "wb") as f:
        await f.write(content)

    result = analyze_file(str(xml_path))
    devices = _mask_devices(result.get("devices", []))
    findings = result.get("findings", [])
    score = result.get("score")

    scan_id = db.save_scan(file.filename, score, str(xml_path))
    if devices:
        db.save_devices(scan_id, devices)
    if findings:
        db.save_findings(scan_id, findings)

    return ScanResult(scan_id=scan_id, score=score, devices=devices, findings=findings)


@router.get("/findings/{scan_id}")
def get_findings(scan_id: int):
    scan = db.get_scan(scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found.")
    return db.get_findings(scan_id)


@router.get("/devices/{scan_id}")
def get_devices(scan_id: int):
    scan = db.get_scan(scan_id)
    if not scan:
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
    scans = db.get_all_scans()
    return [
        ScanHistoryItem(id=s["id"], filename=s["filename"], timestamp=s["timestamp"], network_score=s["network_score"])
        for s in scans
    ]


@router.get("/diff/{old_scan_id}/{new_scan_id}", response_model=DiffResult)
def get_diff(old_scan_id: int, new_scan_id: int):
    if not db.get_scan(old_scan_id):
        raise HTTPException(404, f"Scan {old_scan_id} not found.")
    if not db.get_scan(new_scan_id):
        raise HTTPException(404, f"Scan {new_scan_id} not found.")
    return db.get_diff(old_scan_id, new_scan_id)


@router.post("/scan", response_model=ScanResult)
def live_scan(req: ScanRequest):
    net = detect_network()
    allowlist = [net["subnet"]] if net.get("subnet") else None
    check = validate_scan_target(req.target, allowlist=allowlist, confirmed=req.confirm)
    if not check["allowed"]:
        raise HTTPException(403, check["reason"])

    safe_name = f"{uuid.uuid4().hex}_live.xml"
    output_path = str(SCANS_DIR / safe_name)
    scan_result = run_nmap_scan(req.target, output_path)
    if not scan_result["success"]:
        raise HTTPException(500, scan_result.get("error", "Scan failed."))

    result = analyze_file(output_path)
    devices = _mask_devices(result.get("devices", []))
    findings = result.get("findings", [])
    score = result.get("score")

    scan_id = db.save_scan(f"live_{req.target}", score, output_path)
    if devices:
        db.save_devices(scan_id, devices)
    if findings:
        db.save_findings(scan_id, findings)

    return ScanResult(scan_id=scan_id, score=score, devices=devices, findings=findings)


@router.post("/batch")
async def batch_process(files: list[UploadFile]):
    findings_rows: list[dict] = []
    scores_rows: list[dict] = []

    for file in files:
        if not file.filename or not file.filename.endswith(".xml"):
            scores_rows.append({"file": file.filename or "unknown", "network_score": "ERROR"})
            continue

        content = await file.read()
        try:
            SafeET.fromstring(content)
        except Exception:
            scores_rows.append({"file": file.filename, "network_score": "ERROR"})
            continue

        safe_name = f"{uuid.uuid4().hex}_{file.filename}"
        xml_path = SCANS_DIR / safe_name
        async with aiofiles.open(xml_path, "wb") as f:
            await f.write(content)

        try:
            result = analyze_file(str(xml_path))
        except Exception:
            scores_rows.append({"file": file.filename, "network_score": "ERROR"})
            continue

        devices = _mask_devices(result.get("devices", []))
        findings = result.get("findings", [])
        score = result.get("score")

        scan_id = db.save_scan(file.filename, score, str(xml_path))
        if devices:
            db.save_devices(scan_id, devices)
        if findings:
            db.save_findings(scan_id, findings)

        scores_rows.append({"file": file.filename, "network_score": score})
        for f in findings:
            findings_rows.append({
                "file": file.filename,
                "ip": f["ip"],
                "port": f.get("port", ""),
                "finding_code": f["finding_code"],
                "severity": f["severity"],
            })

    findings_buf = io.StringIO()
    fw = csv.DictWriter(findings_buf, fieldnames=["file", "ip", "port", "finding_code", "severity"])
    fw.writeheader()
    fw.writerows(findings_rows)

    scores_buf = io.StringIO()
    sw = csv.DictWriter(scores_buf, fieldnames=["file", "network_score"])
    sw.writeheader()
    sw.writerows(scores_rows)

    return {
        "processed": len(files),
        "findings_csv": findings_buf.getvalue(),
        "scores_csv": scores_buf.getvalue(),
    }


@router.get("/network-info", response_model=NetworkInfo)
def network_info():
    return detect_network()


@router.delete("/history", response_model=DeleteResponse)
def delete_history():
    count = db.delete_all_history()
    return DeleteResponse(deleted=count, message=f"Deleted {count} scan(s) and all associated data.")
