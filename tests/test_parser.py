import pytest

from analyzer.parser import ScanParseError, parse_file

MINI_XML = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <status state="up"/>
    <address addr="192.168.1.1" addrtype="ipv4"/>
    <address addr="50:C7:BF:12:34:56" addrtype="mac" vendor="TP-Link"/>
    <hostnames><hostname name="router.lan"/></hostnames>
    <ports>
      <port protocol="tcp" portid="80">
        <state state="open"/>
        <service name="http" product="lighttpd"/>
        <script id="http-title" output="Router Admin Login"/>
      </port>
      <port protocol="tcp" portid="443">
        <state state="open"/>
        <service name="http" tunnel="ssl"/>
      </port>
    </ports>
  </host>
</nmaprun>
"""

XXE_XML = """<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<nmaprun>&xxe;</nmaprun>
"""


def test_parses_basic_host(tmp_path):
    p = tmp_path / "mini.xml"
    p.write_text(MINI_XML, encoding="utf-8")
    result = parse_file(p)
    assert len(result.devices) == 1
    dev = result.devices[0]
    assert dev.ip == "192.168.1.1"
    assert dev.vendor == "TP-Link"
    assert dev.hostname == "router.lan"
    assert [p.port for p in dev.open_ports] == [80, 443]
    assert dev.ports[0].http_title == "Router Admin Login"
    assert dev.ports[1].tunnel == "ssl"


def test_truncated_file_raises(tmp_path):
    p = tmp_path / "broken.xml"
    p.write_text(MINI_XML[:200], encoding="utf-8")
    with pytest.raises(ScanParseError):
        parse_file(p)


def test_xxe_is_rejected(tmp_path):
    p = tmp_path / "xxe.xml"
    p.write_text(XXE_XML, encoding="utf-8")
    with pytest.raises(ScanParseError):
        parse_file(p)
