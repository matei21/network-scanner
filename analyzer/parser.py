"""Safe nmap XML parser (NFR-03: no external entities, size limit, untrusted text).

Use defusedxml, never xml.etree directly.
"""

from __future__ import annotations

from pathlib import Path

import defusedxml.ElementTree as ET
from defusedxml import DefusedXmlException

from .models import Device, Port, ScanResult

MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB


class ScanParseError(Exception):
    """Raised when a scan file cannot be read (truncated, not XML, too big, ...)."""


def parse_file(path: str | Path) -> ScanResult:
    """Parse one nmap XML file into a ScanResult (devices only, no findings yet).

    Raises ScanParseError on any problem. The caller turns that into
    ScanResult(error=...) / "ERROR" in scores.csv.
    """
    path = Path(path)

    # 1. The file must exist and not be too big.
    try:
        size = path.stat().st_size
    except OSError as e:
        raise ScanParseError(f"cannot open file: {e}") from e
    if size > MAX_FILE_BYTES:
        raise ScanParseError("file is too big")

    # 2. Read the XML safely (defusedxml blocks external entities / XXE).
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, DefusedXmlException) as e:
        raise ScanParseError(f"file is truncated or not valid XML: {e}") from e

    # 3. It must be an nmap scan file.
    if root.tag != "nmaprun":
        raise ScanParseError("not an nmap XML file")

    # 4. Read every host that is "up".
    devices: list[Device] = []
    try:
        for host in root.findall("host"):
            status = host.find("status")
            if status is None or status.get("state") != "up":
                continue
            devices.append(_parse_host(host))
    except ValueError as e:  # e.g. portid="abc"
        raise ScanParseError(f"invalid value in file: {e}") from e

    return ScanResult(file=path.name, devices=devices)


def _parse_host(host_el) -> Device:
    """Read one <host> element into a Device."""
    # 1. IP, MAC and vendor from the <address> tags.
    ip = mac = vendor = ""
    for addr in host_el.findall("address"):
        if addr.get("addrtype") == "ipv4":
            ip = addr.get("addr", "")
        elif addr.get("addrtype") == "mac":
            mac = addr.get("addr", "")
            vendor = addr.get("vendor", "")

    # 2. Hostname from <hostnames><hostname name="...">.
    hostname = ""
    hn = host_el.find("hostnames/hostname")
    if hn is not None:
        hostname = hn.get("name", "")

    # 3. Ports from <ports><port ...> (<extraports> is skipped automatically).
    ports: list[Port] = []
    for p in host_el.findall("ports/port"):
        state_el = p.find("state")
        service_el = p.find("service")
        svc = service_el.attrib if service_el is not None else {}

        title = ""
        for script in p.findall("script"):
            if script.get("id") == "http-title":
                title = script.get("output", "")

        ports.append(Port(
            port=int(p.get("portid", "0")),
            protocol=p.get("protocol", ""),
            state=state_el.get("state", "") if state_el is not None else "",
            service=svc.get("name", ""),
            product=svc.get("product", ""),
            version=svc.get("version", ""),
            tunnel=svc.get("tunnel", ""),
            http_title=title,
        ))

    return Device(ip=ip, mac=mac, vendor=vendor, hostname=hostname, ports=ports)
