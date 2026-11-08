"""Scope guardrail (FR-02, mandatory, shown live to the jury).

Rules:
  1. The target must be an IPv4 address or IPv4 subnet (no hostnames, no IPv6).
  2. Public ranges are always refused.
  3. The allowlist defaults to the subnet this laptop is connected to.
     If that subnet cannot be detected, live scans are refused (fail closed).
     Extra entries may come from SCAN_ALLOWLIST (private, /24 or smaller only).
  4. The target must lie inside the allowlist and be at most a /24.
  5. Live scans need an explicit confirmation (--confirm / confirm=true).
  6. The laptop must be on the team hotspot: its Wi-Fi name must start with
     SCAN_SSID_PREFIX (default "RSH", as in RSH-<team-number>). Set it to an
     empty value to switch this check off (e.g. the Docker-only Setup D).
"""

from __future__ import annotations

import ipaddress
import logging
import os
import re
import subprocess
from typing import Any

try:  # optional: the Windows "ipconfig" fallback works without it
    import netifaces
except ImportError:  # pragma: no cover - depends on the machine
    netifaces = None

log = logging.getLogger(__name__)

MAX_PREFIX = 24            # biggest range a live scan may cover: a /24 (256 addresses)
MAX_TARGET_LENGTH = 64     # anything longer is not an IP or subnet

_IPV4_TARGET = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?$")
_IPV4_IN_TEXT = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d{1,3}){3})(?![\d.])")


# --- target parsing ---------------------------------------------------------

def parse_target(target: str) -> ipaddress.IPv4Network | None:
    """'10.74.130.0/24' or '10.74.130.9' -> IPv4Network. Anything else -> None.

    No DNS lookups: hostnames are refused, not resolved (input is untrusted).
    """
    text = (target or "").strip()
    if not text or len(text) > MAX_TARGET_LENGTH or not _IPV4_TARGET.match(text):
        return None
    try:
        return ipaddress.IPv4Network(text, strict=False)
    except ValueError:
        return None


def is_private(target: str) -> bool:
    """True only for a valid IPv4 address/subnet that is entirely private."""
    net = parse_target(target)
    return net is not None and net.is_private


# --- allowlist --------------------------------------------------------------

def build_allowlist(detected_subnet: str | None) -> list[str]:
    """The detected subnet plus valid SCAN_ALLOWLIST entries.

    Returns [] when nothing usable is known -> validate_scan_target refuses.
    """
    allow: list[str] = []
    detected = parse_target(detected_subnet or "")
    if detected is not None and detected.is_private:
        allow.append(str(detected))

    for raw in os.environ.get("SCAN_ALLOWLIST", "").split(","):
        raw = raw.strip()
        if not raw:
            continue
        net = parse_target(raw)
        if net is None or not net.is_private or net.prefixlen < MAX_PREFIX:
            log.warning("SCAN_ALLOWLIST entry %r ignored (must be a private /24 or smaller)", raw)
            continue
        if str(net) not in allow:
            allow.append(str(net))
    return allow


# --- validation -------------------------------------------------------------

def _refuse(code: str, reason: str, **params: Any) -> dict[str, Any]:
    """reason is English (the CLI shows it); code + params let the API answer in Romanian too (i18n.guard_reason)."""
    return {"allowed": False, "code": code, "reason": reason, "params": params}


# --- team hotspot check (Wi-Fi name) -----------------------------------------

_SSID_LINE = re.compile(r"^\s*SSID\s*:\s*(.+?)\s*$")   # not "BSSID": that line starts with B


def wifi_ssid() -> str | None:
    """Name of the Wi-Fi network this laptop is connected to, or None (cable, no Wi-Fi, unknown OS)."""
    try:
        if os.name == "nt":
            out = subprocess.run(["netsh", "wlan", "show", "interfaces"],
                                 capture_output=True, text=True, timeout=5, errors="replace").stdout
            for line in out.splitlines():
                m = _SSID_LINE.match(line)
                if m:
                    return m.group(1)
            return None
        out = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True, timeout=5).stdout.strip()
        return out or None
    except (OSError, subprocess.SubprocessError):
        return None


def check_ssid(ssid: str | None) -> dict[str, Any] | None:
    """A refusal if the laptop is not on the team hotspot, else None."""
    prefix = os.environ.get("SCAN_SSID_PREFIX", "RSH").strip()
    if not prefix:
        return None
    if not ssid:
        return _refuse("no_hotspot",
                       f"This laptop is not on a Wi-Fi network named {prefix}... (your team hotspot). "
                       "Connect only to the hotspot, then scan.", prefix=prefix)
    if not ssid.upper().startswith(prefix.upper()):
        return _refuse("wrong_wifi",
                       f"This laptop is on the Wi-Fi '{ssid}', not on your team hotspot ({prefix}...). "
                       "Disconnect from it, connect only to the hotspot, then scan.", ssid=ssid, prefix=prefix)
    return None


def validate_scan_target(target: str, allowlist: list[str] | None = None, confirmed: bool = False) -> dict[str, Any]:
    """Decide whether a live scan of `target` may run. Never raises."""
    net = parse_target(target)
    if net is None:
        shown_target = (target or '')[:MAX_TARGET_LENGTH]
        return _refuse("invalid_target",
                       f"'{shown_target}' is not a valid target. "
                       "Use an IPv4 address or subnet, e.g. 10.74.130.0/24.", target=shown_target)

    shown = str(net.network_address) if net.prefixlen == 32 else str(net)   # "8.8.8.8", not "8.8.8.8/32"

    if not net.is_private:
        return _refuse("public_ip", f"{shown} is a public IP address. Only your own private network may be scanned.",
                       shown=shown)

    allowed_nets = [n for n in (parse_target(a) for a in (allowlist or [])) if n is not None]
    if not allowed_nets:
        return _refuse("no_network",
                       "Could not detect the network this laptop is connected to, so live scans are refused. "
                       "Connect to your hotspot and try again.")

    if net.prefixlen < MAX_PREFIX:
        return _refuse("too_large", f"{net} is too large. Scan at most a /{MAX_PREFIX} (256 addresses).",
                       net=str(net), max_prefix=MAX_PREFIX)

    if not any(net.subnet_of(a) for a in allowed_nets):
        allowed = ", ".join(str(a) for a in allowed_nets)
        return _refuse("outside_allowlist", f"{shown} is outside your network. Allowed: {allowed}.",
                       shown=shown, allowed=allowed)

    if not confirmed:
        return _refuse("not_confirmed", "Live scans need confirmation: add --confirm (or confirm=true).")

    return {"allowed": True, "code": "ok", "reason": f"{shown} is inside your network and confirmed.",
            "params": {"shown": shown}}


# --- network detection (FR-01) ----------------------------------------------

def _detect_via_netifaces() -> dict[str, Any] | None:
    if netifaces is None:
        return None
    try:
        default_gw = netifaces.gateways().get("default", {}).get(netifaces.AF_INET)
        if not default_gw:
            return None
        gateway_ip, iface_name = default_gw[0], default_gw[1]
        addrs = netifaces.ifaddresses(iface_name).get(netifaces.AF_INET, [])
        if not addrs:
            return None
        ip_addr = addrs[0]["addr"]
        netmask = addrs[0].get("netmask") or "255.255.255.0"
        network = ipaddress.IPv4Network(f"{ip_addr}/{netmask}", strict=False)
        return {"interface": str(iface_name), "gateway": gateway_ip, "ip": ip_addr, "subnet": str(network)}
    except Exception:
        return None


def _is_netmask(value: str) -> bool:
    try:
        return value.startswith("255.") and ipaddress.IPv4Network(f"0.0.0.0/{value}").prefixlen > 0
    except ValueError:
        return False


def parse_ipconfig(text: str) -> dict[str, Any] | None:
    """Pick the active adapter from Windows `ipconfig` output.

    Works adapter by adapter, so the IP, mask and gateway always come from the
    same adapter, whatever order Windows lists them in. Only an adapter with an
    IPv4 default gateway counts (WSL / VirtualBox / Docker adapters have none).
    """
    adapters: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        if line.strip() and not line[0].isspace() and line.rstrip().endswith(":"):
            adapters.append((line.strip().rstrip(":").strip(), []))
        elif adapters:
            adapters[-1][1].append(line)

    for name, lines in adapters:
        ip_addr = netmask = gateway = None
        in_gateway = False
        for line in lines:
            key, sep, value = line.partition(":")
            if sep and not key.strip().startswith(("fe80", "::")) and "." in key:
                # a "Key . . . : value" line
                in_gateway = "ateway" in key or "Passerelle" in key
                found = _IPV4_IN_TEXT.findall(value)
                if "IPv4" in key and found:
                    ip_addr = found[0]
                elif found and _is_netmask(found[0]):
                    netmask = found[0]
                elif in_gateway and found:
                    gateway = found[0]
            elif in_gateway and line.strip():
                # gateway continued on the next line (often IPv6 first, then IPv4)
                found = _IPV4_IN_TEXT.findall(line)
                if found and gateway is None:
                    gateway = found[0]
            else:
                in_gateway = False

        if ip_addr and gateway:
            try:
                network = ipaddress.IPv4Network(f"{ip_addr}/{netmask or '255.255.255.0'}", strict=False)
            except ValueError:
                continue
            return {"interface": name, "gateway": gateway, "ip": ip_addr, "subnet": str(network)}
    return None


def _detect_via_ipconfig() -> dict[str, Any] | None:
    try:
        result = subprocess.run(["ipconfig"], capture_output=True, text=True, errors="replace", timeout=5)
    except Exception:
        return None
    return parse_ipconfig(result.stdout or "")


def detect_network() -> dict[str, Any]:
    """Active interface, IP, subnet and gateway, without manual input."""
    for detect in (_detect_via_netifaces, _detect_via_ipconfig):
        result = detect()
        if result:
            return result
    return {"error": "Could not detect network", "interface": None, "gateway": None, "ip": None, "subnet": None}
