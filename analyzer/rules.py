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

from . import catalog
from .models import Device, Finding, Port


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
    """All findings for one device.

    TODO(A): call each rule helper below and collect results.
    """
    raise NotImplementedError


def findings_for_scan(file: str, devices: list[Device]) -> list[Finding]:
    """All findings for a scan, de-duplicated and sorted deterministically
    (ip numerically, then port, then code)."""
    # TODO(A)
    raise NotImplementedError


# --- rule helpers (TODO(A): implement) -------------------------------------

def _simple_service_findings(file: str, device: Device) -> list[Finding]:
    raise NotImplementedError


def _udp_service_findings(file: str, device: Device) -> list[Finding]:
    raise NotImplementedError


def _http_admin_findings(file: str, device: Device) -> list[Finding]:
    raise NotImplementedError


def _smb_finding(file: str, device: Device) -> list[Finding]:
    raise NotImplementedError


def _outdated_findings(file: str, device: Device) -> list[Finding]:
    raise NotImplementedError


def _unknown_device_finding(file: str, device: Device) -> list[Finding]:
    raise NotImplementedError
