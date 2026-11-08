"""Scanning this laptop itself, after a Fix that added a firewall rule.

A Fix blocks a port with a Windows Firewall rule named "NetScanner block ...".
Other devices on the hotspot then see that port as filtered. But nmap running
on this laptop and scanning its own IP never passes through Windows Firewall,
so the port still looks open and the Fix would never show as resolved.

After a live scan, ports of THIS laptop that one of our own NetScanner rules
blocks are rewritten to what the network sees: state "filtered", reason
"netscanner-firewall". nmap's original output is kept next to the file
(live_scan.nmap.xml). Other devices and other firewall rules are never touched.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

import defusedxml.ElementTree as ET   # parsing is safe; writing uses the plain ElementTree it returns

log = logging.getLogger(__name__)

REASON = "netscanner-firewall"

_LIST_RULES = (
    "Get-NetFirewallRule -DisplayName 'NetScanner block*' -ErrorAction SilentlyContinue | "
    "Where-Object { $_.Enabled -eq 'True' -and $_.Direction -eq 'Inbound' -and $_.Action -eq 'Block' } | "
    "Get-NetFirewallPortFilter | ForEach-Object { \"$($_.Protocol) $($_.LocalPort)\" }"
)


def parse_rules(text: str) -> set[tuple[str, int]]:
    """Lines like "TCP 5432" (or "TCP 80 443") -> {("tcp", 5432)}. Anything else is ignored."""
    ports: set[tuple[str, int]] = set()
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 2 or parts[0].lower() not in ("tcp", "udp"):
            continue
        for port in parts[1:]:
            if port.isdigit():
                ports.add((parts[0].lower(), int(port)))
    return ports


def blocked_ports() -> set[tuple[str, int]]:
    """(protocol, port) blocked by an enabled NetScanner firewall rule on this laptop."""
    if os.name != "nt":
        return set()
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _LIST_RULES],
            capture_output=True, text=True, timeout=30, errors="replace",
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("could not read firewall rules: %s", exc)
        return set()
    return parse_rules(out)


def mark_firewalled_ports(xml_path: Path, this_pc: set[str], blocked: set[tuple[str, int]] | None = None) -> int:
    """Rewrite this laptop's open-but-blocked ports to "filtered". Returns how many ports changed."""
    blocked = blocked_ports() if blocked is None else blocked
    if not blocked:
        return 0
    try:
        tree = ET.parse(xml_path)
    except Exception:   # unreadable output: the analyzer reports it, nothing to fix here
        return 0

    changed = 0
    for host in tree.getroot().iter("host"):
        if not {a.get("addr") for a in host.findall("address")} & this_pc:
            continue
        for port in host.iter("port"):
            portid = port.get("portid", "")
            state = port.find("state")
            if (portid.isdigit() and state is not None and state.get("state") == "open"
                    and (port.get("protocol", "").lower(), int(portid)) in blocked):
                state.set("state", "filtered")
                state.set("reason", REASON)
                changed += 1

    if changed:
        shutil.copyfile(xml_path, xml_path.with_suffix(".nmap.xml"))
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)
    return changed
