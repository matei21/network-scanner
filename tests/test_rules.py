"""One test per trap from the brief. Fill in as rules are implemented."""

from analyzer.models import Device, Port
from analyzer.rules import findings_for_device


def codes(device: Device) -> list[tuple]:
    return sorted((f.port, f.code) for f in findings_for_device("t.xml", device))


def test_https_admin_is_not_a_finding():  # V1 trap
    d = Device(ip="192.168.1.1", vendor="TP-Link", ports=[
        Port(443, "tcp", "open", service="http", tunnel="ssl", http_title="Admin Login"),
    ])
    assert codes(d) == []


def test_http_admin_cleartext():
    d = Device(ip="192.168.1.1", vendor="TP-Link", ports=[
        Port(80, "tcp", "open", service="http", http_title="Router Settings"),
    ])
    assert codes(d) == [(80, "HTTP_ADMIN_CLEARTEXT")]


def test_filtered_port_is_ignored():  # V5 trap
    d = Device(ip="192.168.1.9", vendor="X", ports=[Port(3306, "tcp", "filtered", service="mysql")])
    assert codes(d) == []


def test_telnet_on_nonstandard_port():  # V5 trap
    d = Device(ip="192.168.1.5", vendor="X", ports=[Port(2323, "tcp", "open", service="telnet")])
    assert codes(d) == [(2323, "TELNET_OPEN")]


def test_smb_one_per_device_prefers_445():
    d = Device(ip="192.168.1.20", vendor="X", ports=[
        Port(139, "tcp", "open", service="netbios-ssn"),
        Port(445, "tcp", "open", service="microsoft-ds"),
    ])
    assert codes(d) == [(445, "SMB_EXPOSED")]


def test_upnp_only_on_udp():
    d = Device(ip="192.168.1.1", vendor="X", ports=[
        Port(1900, "udp", "open", service="upnp"),
        Port(5000, "tcp", "open", service="upnp"),
    ])
    assert codes(d) == [(1900, "UPNP_EXPOSED")]


def test_vsftpd_234_gives_two_findings():  # V4 trap
    d = Device(ip="192.168.1.60", vendor="X", ports=[
        Port(21, "tcp", "open", service="ftp", product="vsftpd", version="2.3.4"),
    ])
    assert codes(d) == [(21, "FTP_CLEARTEXT"), (21, "OUTDATED_SERVICE")]


def test_unknown_device_has_no_port():
    d = Device(ip="192.168.1.99", ports=[Port(8000, "tcp", "open", service="unknown")])
    assert codes(d) == [(None, "UNKNOWN_DEVICE")]


def test_ipp_is_not_a_finding():  # V3 trap
    d = Device(ip="192.168.1.10", vendor="HP", ports=[Port(631, "tcp", "open", service="ipp")])
    assert codes(d) == []
