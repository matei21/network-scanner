"""Guardrail (FR-02): every refusal the jury will try, plus network detection."""

import pytest

from backend import scan as scan_cli
from backend.app import guardrails as g

OWN = ["10.74.130.0/24"]


def code(target, allowlist=OWN, confirmed=True):
    return g.validate_scan_target(target, allowlist=allowlist, confirmed=confirmed)["code"]


# --- validate_scan_target ---------------------------------------------------

@pytest.mark.parametrize("target, expected", [
    ("10.74.130.0/24", "ok"),                 # own subnet
    ("10.74.130.9", "ok"),                    # one host in own subnet
    ("10.74.130.0/28", "ok"),                 # part of own subnet
    ("8.8.8.8", "public_ip"),
    ("1.1.1.0/24", "public_ip"),
    ("172.0.0.0/8", "public_ip"),             # partly public range
    ("192.168.1.0/24", "outside_allowlist"),  # e.g. the venue Wi-Fi
    ("10.74.131.0/24", "outside_allowlist"),
    ("10.0.0.0/16", "too_large"),
    ("localhost", "invalid_target"),          # hostnames are refused, never resolved
    ("router.lan", "invalid_target"),
    ("fe80::1", "invalid_target"),            # IPv6 used to crash
    ("10.74.130.1-50", "invalid_target"),     # used to say "public IP"
    ("999.1.1.1", "invalid_target"),
    ("", "invalid_target"),
    ("10.74.130.0/24; rm -rf /", "invalid_target"),
])
def test_targets(target, expected):
    assert code(target) == expected


def test_confirmation_required():
    assert code("10.74.130.0/24", confirmed=False) == "not_confirmed"


@pytest.mark.parametrize("allowlist", [None, [], ["not-a-subnet"]])
def test_fails_closed_when_network_unknown(allowlist):
    assert code("192.168.1.0/24", allowlist=allowlist) == "no_network"


def test_public_refused_even_without_network():
    assert code("8.8.8.8", allowlist=None) == "public_ip"


def test_never_raises_on_odd_input():
    for target in [None, "a" * 10_000, "\x00", "10.74.130.0/33"]:
        assert g.validate_scan_target(target, allowlist=OWN, confirmed=True)["allowed"] is False


# --- build_allowlist --------------------------------------------------------

def test_allowlist_defaults_to_detected_subnet(monkeypatch):
    monkeypatch.delenv("SCAN_ALLOWLIST", raising=False)
    assert g.build_allowlist("10.74.130.0/24") == ["10.74.130.0/24"]
    assert g.build_allowlist(None) == []


def test_allowlist_env_only_private_small(monkeypatch):
    monkeypatch.setenv("SCAN_ALLOWLIST", "172.18.0.0/24, 8.8.8.0/24, 10.0.0.0/8, junk")
    assert g.build_allowlist("10.74.130.0/24") == ["10.74.130.0/24", "172.18.0.0/24"]


# --- Windows ipconfig parsing (adapter order must not matter) ---------------

WSL = """Ethernet adapter vEthernet (WSL (Hyper-V firewall)):

   Connection-specific DNS Suffix  . :
   IPv4 Address. . . . . . . . . . . : 172.28.48.1
   Subnet Mask . . . . . . . . . . . : 255.255.240.0
   Default Gateway . . . . . . . . . :
"""
VBOX = """Ethernet adapter VirtualBox Host-Only Network:

   IPv4 Address. . . . . . . . . . . : 192.168.56.1
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . :
"""
WIFI = """Wireless LAN adapter Wi-Fi:

   Connection-specific DNS Suffix  . :
   Link-local IPv6 Address . . . . . : fe80::1c2d:3e4f:5a6b:7c8d%12
   IPv4 Address. . . . . . . . . . . : 10.74.130.9
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . : fe80::aa:bbff:fecc:dd%12
                                       10.74.130.53
"""
DISCONNECTED = """Ethernet adapter Ethernet:

   Media State . . . . . . . . . . . : Media disconnected
"""
HEADER = "\nWindows IP Configuration\n\n"


@pytest.mark.parametrize("blocks", [
    [DISCONNECTED, WSL, VBOX, WIFI],
    [WIFI, WSL, VBOX],
    [WSL, WIFI, VBOX, DISCONNECTED],
])
def test_ipconfig_picks_adapter_with_gateway(blocks):
    info = g.parse_ipconfig(HEADER + "\n".join(blocks))
    assert info == {"interface": "Wireless LAN adapter Wi-Fi", "gateway": "10.74.130.53",
                    "ip": "10.74.130.9", "subnet": "10.74.130.0/24"}


def test_ipconfig_romanian_labels():
    text = """Adaptor LAN fără fir Wi-Fi:

   Adresă IPv4. . . . . . . . . . . : 172.20.10.4(Preferat)
   Mască subrețea . . . . . . . . . : 255.255.255.240
   Gateway implicit . . . . . . . . : 172.20.10.1
"""
    info = g.parse_ipconfig(text)
    assert info["subnet"] == "172.20.10.0/28" and info["gateway"] == "172.20.10.1"


def test_ipconfig_no_gateway_anywhere():
    assert g.parse_ipconfig(HEADER + WSL + VBOX + DISCONNECTED) is None


# --- CLI: refusals never start nmap ---------------------------------------------

@pytest.fixture
def fake_net(monkeypatch):
    calls = []
    monkeypatch.delenv("SCAN_ALLOWLIST", raising=False)
    monkeypatch.setattr(scan_cli, "detect_network",
                        lambda: {"interface": "Wi-Fi", "gateway": "10.74.130.53", "ip": "10.74.130.9",
                                 "subnet": "10.74.130.0/24"})
    monkeypatch.setattr(scan_cli, "run_nmap_scan", lambda *a, **k: calls.append(a) or {"success": False})
    monkeypatch.setattr(scan_cli, "wifi_ssid", lambda: "RSH-7")  # on the team hotspot, whatever this laptop is on
    return calls


@pytest.mark.parametrize("argv", [
    ["--target", "8.8.8.8", "--confirm"],
    ["--target", "192.168.1.0/24", "--confirm"],
    ["--target", "10.74.130.0/24"],          # no --confirm
    [],                                       # default target, no --confirm
])
def test_cli_refuses_without_running_nmap(fake_net, argv, capsys):
    assert scan_cli.main(argv) == 2
    assert fake_net == []
    assert "REFUSED" in capsys.readouterr().out


def test_cli_confirmed_own_subnet_reaches_nmap(fake_net):
    assert scan_cli.main(["--confirm"]) == 1      # fake nmap "fails", but it was called
    assert fake_net and fake_net[0][0] == "10.74.130.0/24"


def test_cli_refuses_when_network_unknown(monkeypatch, capsys):
    monkeypatch.setattr(scan_cli, "detect_network", lambda: {"subnet": None})
    monkeypatch.setattr(scan_cli, "run_nmap_scan", lambda *a, **k: pytest.fail("nmap must not run"))
    assert scan_cli.main(["--target", "192.168.1.0/24", "--confirm"]) == 2
    assert "Could not detect" in capsys.readouterr().out
