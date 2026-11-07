"""FR-04: live scans cover nmap's top 1000 TCP ports (not 1-1000) plus the catalog ports."""

from backend.app import scanner

CATALOG_PORTS = {21, 22, 23, 139, 445, 554, 1883, 2323, 3306, 3389, 5432, 5900, 6379, 8080, 8081, 9100, 27017}


def test_list_is_top_1000_plus_catalog_extras():
    ports = scanner.tcp_ports()
    assert len(ports) == 1003
    assert ports == sorted(set(ports))


def test_catalog_ports_are_scanned():
    assert CATALOG_PORTS <= set(scanner.tcp_ports())


def test_nmap_command_uses_the_list(monkeypatch, tmp_path):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        raise FileNotFoundError

    monkeypatch.setattr(scanner.subprocess, "run", fake_run)
    scanner.run_nmap_scan("192.168.1.0/24", str(tmp_path / "out.xml"))

    spec = seen["cmd"][seen["cmd"].index("-p") + 1]
    assert spec.startswith("T:") and spec.endswith(",U:53,123,161,1900,5353")
    assert "T:1-1000" not in spec
    assert "3389" in spec.split(",")
