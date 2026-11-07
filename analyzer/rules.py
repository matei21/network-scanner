"""Detection rules: Device list -> Finding list.

Rules (from the brief):
  - Only ports in state "open".
  - Decide by nmap service name, not by port number.
  - UPNP / SNMP only on UDP.
  - HTTP_ADMIN_CLEARTEXT: service http, no SSL tunnel, title contains a keyword.
  - SMB_EXPOSED: one finding per device (445 if open, else 139).
  - OUTDATED_SERVICE: in addition to the service's own finding.
  - UNKNOWN_DEVICE: no vendor and no hostname, >= 1 open port, port empty.
"""

from __future__ import annotations

import ipaddress

from . import catalog
from .models import Device, Finding, Port
from .outdated import is_outdated


def make_finding(file: str, device: Device, code: str, port: Port | None, evidence: str = "") -> Finding:
    entry = catalog.get(code)
    return Finding(
        file=file,
        ip=device.ip,
        port=port.port if port else None,
        protocol=port.protocol if port else "",
        code=code,
        severity=entry.severity,
        points=entry.points,
        evidence=evidence,
    )


def findings_for_device(file: str, device: Device) -> list[Finding]:
    """All findings for one device."""
    found: list[Finding] = []
    found += _simple_service_findings(file, device)
    found += _udp_service_findings(file, device)
    found += _http_admin_findings(file, device)
    found += _smb_finding(file, device)
    found += _outdated_findings(file, device)
    found += _unknown_device_finding(file, device)
    return found


def findings_for_scan(file: str, devices: list[Device]) -> list[Finding]:
    """All findings for a scan, de-duplicated and sorted deterministically
    (ip numerically, then port, then code)."""
    unique: dict[tuple, Finding] = {}
    for device in devices:
        for f in findings_for_device(file, device):
            unique.setdefault((f.ip, f.port, f.code), f)
    return sorted(unique.values(), key=sort_key)


def sort_key(f: Finding) -> tuple:
    return (_ip_key(f.ip), -1 if f.port is None else f.port, f.code)


def _ip_key(ip: str) -> tuple:
    try:
        return (0, int(ipaddress.ip_address(ip)))
    except ValueError:
        return (1, ip)


def _evidence(p: Port) -> str:
    parts = [f"{p.protocol}/{p.port}", f"service={p.service}"]
    if p.product:
        parts.append(f"product={p.product}")
    if p.version:
        parts.append(f"version={p.version}")
    if p.http_title:
        parts.append(f"title={p.http_title}")
    return ", ".join(parts)


# --- rule helpers -----------------------------------------------------------

def _simple_service_findings(file: str, device: Device) -> list[Finding]:
    """telnet, RDP, VNC, databases, rtsp, ftp, mqtt, jetdirect, ssh - any port."""
    out = []
    for p in device.open_ports:
        code = catalog.SIMPLE_SERVICE_RULES.get(p.service)
        if code:
            out.append(make_finding(file, device, code, p, _evidence(p)))
    return out


def _udp_service_findings(file: str, device: Device) -> list[Finding]:
    """upnp / snmp, only when the port is UDP."""
    out = []
    for p in device.open_ports:
        code = catalog.UDP_SERVICE_RULES.get(p.service)
        if code and p.protocol == "udp":
            out.append(make_finding(file, device, code, p, _evidence(p)))
    return out


def _http_admin_findings(file: str, device: Device) -> list[Finding]:
    """Service http, no SSL tunnel, page title contains an admin keyword."""
    out = []
    for p in device.open_ports:
        if p.service != "http" or p.tunnel == "ssl":
            continue
        title = p.http_title.lower()
        if any(word in title for word in catalog.HTTP_ADMIN_TITLE_KEYWORDS):
            out.append(make_finding(file, device, "HTTP_ADMIN_CLEARTEXT", p, _evidence(p)))
    return out


def _smb_finding(file: str, device: Device) -> list[Finding]:
    """One SMB finding per device: port 445 if open, else 139."""
    smb_ports = [p for p in device.open_ports if p.service in catalog.SMB_SERVICES]
    if not smb_ports:
        return []
    by_number = {p.port: p for p in smb_ports}
    chosen = by_number.get(445) or by_number.get(139) or min(smb_ports, key=lambda p: p.port)
    return [make_finding(file, device, "SMB_EXPOSED", chosen, _evidence(chosen))]


def _outdated_findings(file: str, device: Device) -> list[Finding]:
    """Old version on the outdated list (in addition to the service's own finding)."""
    return [
        make_finding(file, device, "OUTDATED_SERVICE", p, _evidence(p))
        for p in device.open_ports
        if is_outdated(p)
    ]


def _unknown_device_finding(file: str, device: Device) -> list[Finding]:
    """No vendor and no hostname, at least one open port. Port column stays empty."""
    if device.vendor or device.hostname or not device.open_ports:
        return []
    ports = ", ".join(f"{p.protocol}/{p.port}" for p in device.open_ports)
    return [make_finding(file, device, "UNKNOWN_DEVICE", None, f"no vendor, no hostname, open: {ports}")]
