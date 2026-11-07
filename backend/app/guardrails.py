import ipaddress
import re
import socket
import subprocess
from typing import Any

import netifaces


def is_private(target: str) -> bool:
    try:
        addr = ipaddress.ip_address(target)
        return addr.is_private
    except ValueError:
        pass
    try:
        net = ipaddress.ip_network(target, strict=False)
        return net.is_private
    except ValueError:
        pass
    try:
        resolved = socket.gethostbyname(target)
        return ipaddress.ip_address(resolved).is_private
    except (socket.gaierror, ValueError):
        return False


def _detect_via_netifaces() -> dict[str, Any] | None:
    try:
        gateways = netifaces.gateways()
        default_gw = gateways.get("default", {}).get(netifaces.AF_INET)
        if not default_gw:
            return None
        gateway_ip, iface_name = default_gw[0], default_gw[1]
        addrs = netifaces.ifaddresses(iface_name).get(netifaces.AF_INET, [])
        if not addrs:
            return None
        ip_addr = addrs[0]["addr"]
        netmask = addrs[0].get("netmask", "255.255.255.0")
        network = ipaddress.IPv4Network(f"{ip_addr}/{netmask}", strict=False)
        return {"interface": iface_name, "gateway": gateway_ip, "ip": ip_addr, "subnet": str(network)}
    except (NotImplementedError, Exception):
        return None


def _detect_via_ipconfig() -> dict[str, Any] | None:
    try:
        result = subprocess.run(["ipconfig"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.split("\n")
        ip_addr = gateway = adapter = None
        netmask = "255.255.255.0"
        for line in lines:
            stripped = line.strip()
            if line and not line[0].isspace() and ":" in line:
                adapter = stripped.rstrip(":").strip()
            m = re.search(r"IPv4.*?:\s*([\d.]+)", stripped)
            if m:
                ip_addr = m.group(1)
            m = re.search(r"Subnet Mask.*?:\s*([\d.]+)", stripped)
            if m:
                netmask = m.group(1)
            m = re.search(r"Default Gateway.*?:\s*([\d.]+)", stripped)
            if m:
                gateway = m.group(1)
        if ip_addr:
            network = ipaddress.IPv4Network(f"{ip_addr}/{netmask}", strict=False)
            return {"interface": adapter, "gateway": gateway, "ip": ip_addr, "subnet": str(network)}
    except Exception:
        pass
    return None


def detect_network() -> dict[str, Any]:
    result = _detect_via_netifaces()
    if result:
        return result
    result = _detect_via_ipconfig()
    if result:
        return result
    return {"error": "Could not detect network", "interface": None, "gateway": None, "ip": None, "subnet": None}


def validate_scan_target(target: str, allowlist: list[str] | None = None, confirmed: bool = False) -> dict[str, Any]:
    if not is_private(target):
        return {"allowed": False, "reason": f"Target '{target}' is a public IP. Only private/RFC1918 ranges are allowed."}

    if allowlist:
        target_net = ipaddress.ip_network(target, strict=False)
        allowed = False
        for entry in allowlist:
            try:
                allow_net = ipaddress.ip_network(entry, strict=False)
                if target_net.subnet_of(allow_net) or target_net == allow_net:
                    allowed = True
                    break
            except ValueError:
                continue
        if not allowed:
            return {"allowed": False, "reason": f"Target '{target}' is not in the allowlist: {allowlist}"}

    if not confirmed:
        return {"allowed": False, "reason": "Live scans require confirm=true (--confirm flag)."}

    return {"allowed": True, "reason": "Target validated."}
