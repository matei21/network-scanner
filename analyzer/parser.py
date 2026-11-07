"""Safe nmap XML parser (NFR-03: no external entities, size limit, untrusted text).

Use defusedxml, never xml.etree directly.
"""

from __future__ import annotations

from pathlib import Path

from .models import Device, ScanResult

MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB


class ScanParseError(Exception):
    """Raised when a scan file cannot be read (truncated, not XML, too big, ...)."""


def parse_file(path: str | Path) -> ScanResult:
    """Parse one nmap XML file into a ScanResult (devices only, no findings yet).

    Raises ScanParseError on any problem. The caller turns that into
    ScanResult(error=...) / "ERROR" in scores.csv.
    """
    # TODO(A):
    #  - check file size <= MAX_FILE_BYTES
    #  - defusedxml.ElementTree.parse(path); catch ParseError / DefusedXmlException
    #  - for each <host> with <status state="up">: build a Device via _parse_host
    raise NotImplementedError


def _parse_host(host_el) -> Device:
    """Read one <host> element.

    TODO(A):
      - <address addrtype="ipv4" addr=...>        -> ip
      - <address addrtype="mac" addr=... vendor=...> -> mac, vendor
      - <hostnames><hostname name=...>            -> hostname
      - <ports><port protocol portid>             -> Port(...)
          <state state=...>
          <service name product version tunnel>
          <script id="http-title" output=...>
    """
    raise NotImplementedError
