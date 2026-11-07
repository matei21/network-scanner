import pytest

from analyzer.models import Port
from analyzer.outdated import is_outdated, parse_version


def _port(product: str, version: str) -> Port:
    return Port(21, "tcp", "open", service="x", product=product, version=version)


@pytest.mark.parametrize("text, expected", [
    ("2.3.4", (2, 3, 4)),
    ("8.9p1", (8, 9)),
    ("8.4p1 Debian 5+deb11u3", (8, 4)),
    ("10.0", (10, 0)),
    ("", ()),
    ("unknown", ()),
])
def test_parse_version(text, expected):
    assert parse_version(text) == expected


@pytest.mark.parametrize("product, version, expected", [
    # vsftpd: only exactly 2.3.4
    ("vsftpd", "2.3.4", True),          # V4
    ("vsftpd", "3.0.5", False),
    ("vsftpd", "2.3.5", False),
    # OpenSSH: below 7.4
    ("OpenSSH", "7.2p2 Ubuntu 4", True),
    ("OpenSSH", "6.6.1p1", True),
    ("OpenSSH", "7.4", False),
    ("OpenSSH", "8.9p1", False),        # V3
    # Apache httpd: 2.2.x or older
    ("Apache httpd", "2.2.34", True),
    ("Apache httpd", "2.0.64", True),
    ("Apache httpd", "2.4.57", False),
    # Microsoft IIS: 7.5 or older
    ("Microsoft IIS httpd", "7.5", True),
    ("Microsoft IIS httpd", "6.0", True),
    ("Microsoft IIS httpd", "10.0", False),   # string compare would get this wrong
    # Samba: 3.x or older
    ("Samba smbd", "3.6.25", True),
    ("Samba smbd", "4.15", False),      # V3
    ("Samba smbd", "3.X - 4.X", False), # might be 4 -> not proven
    ("Samba smbd", "3.X", True),
    # no version / unrelated product
    ("vsftpd", "", False),
    ("nginx", "1.0", False),
    ("", "2.3.4", False),
])
def test_is_outdated(product, version, expected):
    assert is_outdated(_port(product, version)) is expected
