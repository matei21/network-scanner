"""OUTDATED_SERVICE detection.

Outdated list (from the brief):
  - vsftpd 2.3.4
  - OpenSSH below 7.4
  - Apache httpd 2.2.x or older
  - Microsoft IIS 7.5 or older
  - Samba 3.x or older

Compare versions as integer tuples, never as strings ("10.0" > "7.5").
"""

from __future__ import annotations

import re

from .models import Port

# A dotted number such as "2.3.4", "8.9" (from "8.9p1") or "3" (from "3.X").
_VERSION_RE = re.compile(r"\d+(?:\.\d+)*")


def parse_version(text: str) -> tuple[int, ...]:
    """'7.2p2 Ubuntu' -> (7, 2). Returns () when no number is found."""
    match = _VERSION_RE.search(text or "")
    if not match:
        return ()
    return tuple(int(part) for part in match.group().split("."))


def _all_versions(text: str) -> list[tuple[int, ...]]:
    """Every version in the text: '3.X - 4.X' -> [(3,), (4,)]."""
    return [tuple(int(p) for p in m.split(".")) for m in _VERSION_RE.findall(text or "")]


def is_outdated(port: Port) -> bool:
    """True when product + version match the outdated list.

    No version reported -> never outdated (we only report what the scan proves).
    """
    product = (port.product or "").strip().lower()
    version = parse_version(port.version)
    if not product or not version:
        return False

    if product.startswith("vsftpd"):
        return version[:3] == (2, 3, 4)

    if product.startswith("openssh"):
        return version < (7, 4)

    if product.startswith("apache httpd"):
        return version[:2] <= (2, 2)          # 2.2.x and older; 2.4 is fine

    if "iis" in product:                       # "Microsoft IIS httpd"
        return version[:2] <= (7, 5)

    if product.startswith("samba"):
        # A range like "3.X - 4.X" might be 4, so only flag when every
        # version mentioned is 3 or lower.
        return all(v[0] <= 3 for v in _all_versions(port.version))

    return False
