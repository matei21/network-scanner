"""Data classes shared by parser, rules, scoring and export."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Port:
    port: int
    protocol: str                 # "tcp" | "udp"
    state: str                    # "open", "filtered", "open|filtered", ...
    service: str = ""             # nmap service name, e.g. "http", "ms-wbt-server"
    product: str = ""             # e.g. "vsftpd", "OpenSSH"
    version: str = ""             # e.g. "2.3.4"
    tunnel: str = ""              # "ssl" when nmap detected TLS
    http_title: str = ""          # output of the http-title script, if any

    @property
    def is_open(self) -> bool:
        # Only the exact state "open" counts ("open|filtered" does not).
        return self.state == "open"


@dataclass
class Device:
    ip: str
    mac: str = ""                 # raw MAC; mask with privacy.mask_mac before output
    vendor: str = ""
    hostname: str = ""
    ports: list[Port] = field(default_factory=list)

    @property
    def open_ports(self) -> list[Port]:
        return [p for p in self.ports if p.is_open]


@dataclass
class Finding:
    file: str
    ip: str
    port: Optional[int]           # None for UNKNOWN_DEVICE (empty port column)
    code: str
    severity: str                 # "high" | "medium" | "low" | "info"
    points: int
    protocol: str = ""
    evidence: str = ""            # short, untrusted text from the scan (escape in UI)


@dataclass
class ScanResult:
    file: str
    devices: list[Device] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    score: Optional[int] = None   # None when error is set
    error: Optional[str] = None   # set when the file cannot be read -> "ERROR"

    @property
    def ok(self) -> bool:
        return self.error is None
