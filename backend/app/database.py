import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", "db/scanner.db")


def _get_db_path() -> Path:
    path = Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_get_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            network_score REAL,
            xml_path TEXT
        );
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER NOT NULL,
            ip TEXT NOT NULL,
            mac_masked TEXT,
            vendor TEXT,
            hostname TEXT,
            device_type TEXT,
            FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER NOT NULL,
            ip TEXT NOT NULL,
            port INTEGER,
            finding_code TEXT NOT NULL,
            severity TEXT NOT NULL,
            FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


def save_scan(filename: str, network_score: float | None, xml_path: str | None) -> int:
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO scans (filename, timestamp, network_score, xml_path) VALUES (?, ?, ?, ?)",
        (filename, datetime.now(timezone.utc).isoformat(), network_score, xml_path),
    )
    scan_id = cur.lastrowid
    conn.commit()
    conn.close()
    return scan_id


def save_devices(scan_id: int, devices: list[dict]) -> None:
    conn = _connect()
    conn.executemany(
        "INSERT INTO devices (scan_id, ip, mac_masked, vendor, hostname, device_type) VALUES (?, ?, ?, ?, ?, ?)",
        [(scan_id, d["ip"], d.get("mac_masked"), d.get("vendor"), d.get("hostname"), d.get("device_type")) for d in devices],
    )
    conn.commit()
    conn.close()


def save_findings(scan_id: int, findings: list[dict]) -> None:
    conn = _connect()
    conn.executemany(
        "INSERT INTO findings (scan_id, ip, port, finding_code, severity) VALUES (?, ?, ?, ?, ?)",
        [(scan_id, f["ip"], f.get("port"), f["finding_code"], f["severity"]) for f in findings],
    )
    conn.commit()
    conn.close()


def get_scan(scan_id: int) -> dict | None:
    conn = _connect()
    row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_scans() -> list[dict]:
    conn = _connect()
    rows = conn.execute("SELECT * FROM scans ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_findings(scan_id: int) -> list[dict]:
    conn = _connect()
    rows = conn.execute("SELECT * FROM findings WHERE scan_id = ?", (scan_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_devices(scan_id: int) -> list[dict]:
    conn = _connect()
    rows = conn.execute("SELECT * FROM devices WHERE scan_id = ?", (scan_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_diff(old_id: int, new_id: int) -> dict:
    old_findings = {(f["ip"], f["port"], f["finding_code"]) for f in get_findings(old_id)}
    new_findings = {(f["ip"], f["port"], f["finding_code"]) for f in get_findings(new_id)}

    old_devices = {d["ip"] for d in get_devices(old_id)}
    new_devices = {d["ip"] for d in get_devices(new_id)}

    old_scan = get_scan(old_id)
    new_scan = get_scan(new_id)

    return {
        "old_scan_id": old_id,
        "new_scan_id": new_id,
        "old_score": old_scan["network_score"] if old_scan else None,
        "new_score": new_scan["network_score"] if new_scan else None,
        "resolved_findings": [
            {"ip": ip, "port": port, "finding_code": code}
            for ip, port, code in old_findings - new_findings
        ],
        "new_findings": [
            {"ip": ip, "port": port, "finding_code": code}
            for ip, port, code in new_findings - old_findings
        ],
        "devices_added": list(new_devices - old_devices),
        "devices_removed": list(old_devices - new_devices),
    }


def delete_all_history() -> int:
    conn = _connect()
    count = conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
    conn.execute("DELETE FROM findings")
    conn.execute("DELETE FROM devices")
    conn.execute("DELETE FROM scans")
    conn.commit()
    # DELETE only marks pages free; VACUUM + WAL truncate actually erase hostnames from disk (NFR-02).
    conn.execute("VACUUM")
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()
    return count
