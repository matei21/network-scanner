"""Fix + scan on this laptop: a port blocked by a NetScanner firewall rule shows as resolved."""

import pytest

from backend.app import self_firewall

THIS_PC = "10.74.130.252"
PHONE = "10.74.130.53"

XML = f"""<?xml version="1.0"?>
<nmaprun scanner="nmap" args="nmap -sS -sV 10.74.130.0/24" start="1" version="7.95">
<host><status state="up"/><address addr="{PHONE}" addrtype="ipv4"/>
<ports><port protocol="tcp" portid="5432"><state state="open" reason="syn-ack"/><service name="postgresql"/></port></ports>
</host>
<host><status state="up"/><address addr="{THIS_PC}" addrtype="ipv4"/>
<ports>
<port protocol="tcp" portid="5432"><state state="open" reason="syn-ack"/><service name="postgresql" product="PostgreSQL DB"/></port>
<port protocol="tcp" portid="1521"><state state="open" reason="syn-ack"/><service name="oracle-tns"/></port>
<port protocol="udp" portid="5432"><state state="open|filtered" reason="no-response"/></port>
</ports>
</host>
<runstats><finished time="2" exit="success"/><hosts up="2" down="254" total="256"/></runstats>
</nmaprun>
"""


def _write(tmp_path):
    path = tmp_path / "live_scan.xml"
    path.write_text(XML, encoding="utf-8")
    return path


def test_rule_output_is_parsed():
    out = "TCP 5432\nUDP 1900\nTCP 80 443\nTCP Any\n\nwarning: something\n"
    assert self_firewall.parse_rules(out) == {("tcp", 5432), ("udp", 1900), ("tcp", 80), ("tcp", 443)}


def test_only_blocked_ports_of_this_laptop_change(tmp_path):
    from analyzer.service import analyze_file

    path = _write(tmp_path)
    changed = self_firewall.mark_firewalled_ports(path, {THIS_PC}, {("tcp", 5432)})

    assert changed == 1
    ports = {(d.ip, p.port, p.protocol): p.state for d in analyze_file(path).devices for p in d.ports}
    assert ports[(THIS_PC, 5432, "tcp")] == "filtered"          # blocked by our rule -> resolved
    assert ports[(THIS_PC, 1521, "tcp")] == "open"              # no rule -> still a problem
    assert ports[(PHONE, 5432, "tcp")] == "open"                # another device is never touched
    assert (tmp_path / "live_scan.nmap.xml").read_text(encoding="utf-8") == XML   # nmap's output is kept


def test_nothing_changes_without_rules_or_on_other_devices(tmp_path):
    path = _write(tmp_path)
    assert self_firewall.mark_firewalled_ports(path, {THIS_PC}, set()) == 0
    assert self_firewall.mark_firewalled_ports(path, {"10.0.0.9"}, {("tcp", 5432)}) == 0
    assert path.read_text(encoding="utf-8") == XML
    assert not (tmp_path / "live_scan.nmap.xml").exists()


def test_unreadable_output_is_left_alone(tmp_path):
    path = tmp_path / "live_scan.xml"
    path.write_text("<nmaprun><host>", encoding="utf-8")
    assert self_firewall.mark_firewalled_ports(path, {THIS_PC}, {("tcp", 5432)}) == 0


def test_fix_then_scan_shows_the_problem_resolved(monkeypatch, tmp_path):
    from backend.app import database as db
    from backend.app import routes

    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(routes, "local_ips", lambda: {THIS_PC, "127.0.0.1"})
    db.init_db()

    (tmp_path / "before").mkdir()
    (tmp_path / "after").mkdir()

    monkeypatch.setattr(self_firewall, "blocked_ports", lambda: set())                # before the Fix
    before = routes._store_live(_write(tmp_path / "before"), THIS_PC)

    monkeypatch.setattr(self_firewall, "blocked_ports", lambda: {("tcp", 5432)})      # Fix added the rule
    after = routes._store_live(_write(tmp_path / "after"), THIS_PC)

    def db_findings(data):
        return {(f["ip"], f["port"]) for d in data["devices"] for f in d["findings"] if f["code"] == "DB_EXPOSED"}

    assert (THIS_PC, 5432) in db_findings(before)
    assert (THIS_PC, 5432) not in db_findings(after)
    assert {(p["port"], p["protocol"]) for p in after["changes"]["ports_closed"]} == {(5432, "tcp")}
    assert any(f["port"] == 5432 for f in after["changes"]["resolved_findings"])
