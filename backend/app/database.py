import json
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
            xml_path TEXT,
            result_json TEXT,
            source TEXT NOT NULL DEFAULT 'real'
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
        CREATE TABLE IF NOT EXISTS ports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER NOT NULL,
            ip TEXT NOT NULL,
            port INTEGER NOT NULL,
            protocol TEXT NOT NULL,
            service TEXT,
            product TEXT,
            version TEXT,
            FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS device_names (
            ip TEXT PRIMARY KEY,
            custom_name TEXT NOT NULL,
            suggested_name TEXT
        );
    """)
    # Databases created before these columns existed get them added in place.
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(scans)")}
    if "result_json" not in columns:
        conn.execute("ALTER TABLE scans ADD COLUMN result_json TEXT")
    if "source" not in columns:
        conn.execute("ALTER TABLE scans ADD COLUMN source TEXT NOT NULL DEFAULT 'real'")
    conn.commit()
    conn.close()


def save_scan(filename: str, network_score: float | None, xml_path: str | None, source: str = "real") -> int:
    """source: "real" for our own network (lab uploads, live scans), "test" for Validation/Test Set files."""
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO scans (filename, timestamp, network_score, xml_path, source) VALUES (?, ?, ?, ?, ?)",
        (filename, datetime.now(timezone.utc).isoformat(), network_score, xml_path, source),
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


def save_ports(scan_id: int, ports: list[dict]) -> None:
    conn = _connect()
    conn.executemany(
        "INSERT INTO ports (scan_id, ip, port, protocol, service, product, version) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(scan_id, p["ip"], p["port"], p["protocol"], p.get("service"), p.get("product"), p.get("version")) for p in ports],
    )
    conn.commit()
    conn.close()


def save_snapshot(scan_id: int, result: dict) -> None:
    """The full scan as returned by /upload, so it can be shown again exactly as it was."""
    conn = _connect()
    conn.execute("UPDATE scans SET result_json = ? WHERE id = ?", (json.dumps(result, ensure_ascii=False), scan_id))
    conn.commit()
    conn.close()


def get_snapshot(scan_id: int) -> dict | None:
    conn = _connect()
    row = conn.execute("SELECT result_json FROM scans WHERE id = ?", (scan_id,)).fetchone()
    conn.close()
    return json.loads(row["result_json"]) if row and row["result_json"] else None


def get_ports(scan_id: int) -> list[dict]:
    conn = _connect()
    rows = conn.execute("SELECT * FROM ports WHERE scan_id = ?", (scan_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _scan_row(row: sqlite3.Row) -> dict:
    scan = dict(row)
    scan.pop("result_json", None)
    # The column is REAL in older databases; scores are always whole numbers.
    if scan["network_score"] is not None:
        scan["network_score"] = int(scan["network_score"])
    return scan


def get_scan(scan_id: int) -> dict | None:
    conn = _connect()
    row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    conn.close()
    return _scan_row(row) if row else None


def get_all_scans(source: str | None = None) -> list[dict]:
    """Newest first. source=None returns every scan."""
    conn = _connect()
    if source is None:
        rows = conn.execute("SELECT * FROM scans ORDER BY id DESC").fetchall()
    else:
        rows = conn.execute("SELECT * FROM scans WHERE source = ? ORDER BY id DESC", (source,)).fetchall()
    conn.close()
    return [_scan_row(r) for r in rows]


def count_findings() -> dict[int, int]:
    """scan_id -> number of findings, for every scan that has at least one."""
    conn = _connect()
    rows = conn.execute("SELECT scan_id, COUNT(*) AS n FROM findings GROUP BY scan_id").fetchall()
    conn.close()
    return {r["scan_id"]: r["n"] for r in rows}


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

    old_ports = {(p["ip"], p["port"], p["protocol"]): p["service"] for p in get_ports(old_id)}
    new_ports = {(p["ip"], p["port"], p["protocol"]): p["service"] for p in get_ports(new_id)}

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
        "ports_opened": [
            {"ip": ip, "port": port, "protocol": proto, "service": new_ports[(ip, port, proto)]}
            for ip, port, proto in sorted(new_ports.keys() - old_ports.keys())
        ],
        "ports_closed": [
            {"ip": ip, "port": port, "protocol": proto, "service": old_ports[(ip, port, proto)]}
            for ip, port, proto in sorted(old_ports.keys() - new_ports.keys())
        ],
    }


def get_device_names() -> dict[str, dict]:
    conn = _connect()
    rows = conn.execute("SELECT ip, custom_name, suggested_name FROM device_names").fetchall()
    conn.close()
    return {r["ip"]: {"custom_name": r["custom_name"], "suggested_name": r["suggested_name"]} for r in rows}


def save_device_name(ip: str, custom_name: str, suggested_name: str | None = None) -> None:
    conn = _connect()
    conn.execute(
        "INSERT INTO device_names (ip, custom_name, suggested_name) VALUES (?, ?, ?) "
        "ON CONFLICT(ip) DO UPDATE SET custom_name = excluded.custom_name, suggested_name = excluded.suggested_name",
        (ip, custom_name, suggested_name),
    )
    conn.commit()
    conn.close()


def delete_all_history() -> int:
    conn = _connect()
    count = conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
    conn.execute("DELETE FROM ports")
    conn.execute("DELETE FROM findings")
    conn.execute("DELETE FROM devices")
    conn.execute("DELETE FROM scans")
    conn.commit()
    # DELETE only marks pages free; VACUUM + WAL truncate actually erase hostnames from disk (NFR-02).
    conn.execute("VACUUM")
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()
    return count
