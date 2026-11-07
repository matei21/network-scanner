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

from .models import Port


def parse_version(text: str) -> tuple[int, ...]:
    """'7.2p2 Ubuntu' -> (7, 2). Returns () when no number is found."""
    # TODO(A): extract the leading dotted number with a regex
    raise NotImplementedError


def is_outdated(port: Port) -> bool:
    """True when product + version match the outdated list.

    TODO(A): match on port.product (case-insensitive) and port.version.
    Watch out: nmap sometimes reports Samba as a range like '3.X - 4.X'.
    """
    raise NotImplementedError
