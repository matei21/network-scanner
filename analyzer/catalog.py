"""Official finding catalog (single source of truth for severity + points).

Copied from the R Systems Hackathon 2026 brief. Do not change values here
without checking the brief.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogEntry:
    code: str
    severity: str
    points: int
    meaning: str


_ENTRIES = [
    CatalogEntry("TELNET_OPEN", "high", 20, "Remote login without encryption"),
    CatalogEntry("RDP_EXPOSED", "high", 20, "Remote desktop reachable"),
    CatalogEntry("VNC_EXPOSED", "high", 20, "Remote screen sharing reachable"),
    CatalogEntry("DB_EXPOSED", "high", 20, "Database reachable from the network"),
    CatalogEntry("CAMERA_STREAM_EXPOSED", "high", 20, "Video stream reachable"),
    CatalogEntry("OUTDATED_SERVICE", "high", 20, "Software version with known security problems"),
    CatalogEntry("FTP_CLEARTEXT", "medium", 10, "File transfer without encryption"),
    CatalogEntry("HTTP_ADMIN_CLEARTEXT", "medium", 10, "Admin page over plain HTTP"),
    CatalogEntry("SMB_EXPOSED", "medium", 10, "Windows file sharing open"),
    CatalogEntry("MQTT_EXPOSED", "medium", 10, "IoT message broker reachable"),
    CatalogEntry("UPNP_EXPOSED", "medium", 10, "Device can open router ports automatically"),
    CatalogEntry("SNMP_EXPOSED", "medium", 10, "Device management protocol reachable"),
    CatalogEntry("PRINTER_RAW_EXPOSED", "low", 5, "Anyone can send jobs to the printer"),
    CatalogEntry("UNKNOWN_DEVICE", "low", 5, "Device that cannot be identified"),
    CatalogEntry("SSH_OPEN", "info", 0, "Encrypted remote login, shown for awareness"),
]

CATALOG: dict[str, CatalogEntry] = {e.code: e for e in _ENTRIES}

# Service-name based rules (nmap service name -> finding code).
# Decide by service name, never by port number alone.
SIMPLE_SERVICE_RULES: dict[str, str] = {
    "telnet": "TELNET_OPEN",
    "ms-wbt-server": "RDP_EXPOSED",
    "vnc": "VNC_EXPOSED",
    "mysql": "DB_EXPOSED",
    "postgresql": "DB_EXPOSED",
    "redis": "DB_EXPOSED",
    "mongodb": "DB_EXPOSED",
    "rtsp": "CAMERA_STREAM_EXPOSED",
    "ftp": "FTP_CLEARTEXT",
    "mqtt": "MQTT_EXPOSED",
    "jetdirect": "PRINTER_RAW_EXPOSED",
    "ssh": "SSH_OPEN",
}

# Only reported when the port protocol is UDP.
UDP_SERVICE_RULES: dict[str, str] = {
    "upnp": "UPNP_EXPOSED",
    "snmp": "SNMP_EXPOSED",
}

SMB_SERVICES = {"microsoft-ds", "netbios-ssn"}

HTTP_ADMIN_TITLE_KEYWORDS = ("login", "admin", "config", "setup", "router", "settings")


def get(code: str) -> CatalogEntry:
    return CATALOG[code]
