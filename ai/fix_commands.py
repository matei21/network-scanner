"""Parameterized fix commands for the 15 official findings.

Each finding has one of three fix types:
  - "powershell": a direct PowerShell command that runs on the local machine
  - "firewall": a Windows Firewall rule blocking the port
  - "portal": cannot be fixed via CMD; opens the device's admin page instead

Commands use {port} and {ip} placeholders, substituted at runtime from scan data.
"""

from __future__ import annotations


FIX_COMMANDS: dict[str, dict] = {
    # ── Group 1: Direct PowerShell commands ───────────────────────────
    "TELNET_OPEN": {
        "type": "powershell",
        "command": "Disable-WindowsOptionalFeature -Online -FeatureName TelnetClient -NoRestart",
        "params_used": [],
        "explanation_ro": "Dezactiveaza componenta Telnet din Windows. Nu necesita restart.",
        "explanation_en": "Disables the Telnet component from Windows. No restart needed.",
        "requires_admin": True,
    },
    "RDP_EXPOSED": {
        "type": "powershell",
        "command": "Set-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server' -Name 'fDenyTSConnections' -Value 1",
        "params_used": [],
        "explanation_ro": "Dezactiveaza Remote Desktop prin registrul Windows.",
        "explanation_en": "Disables Remote Desktop via Windows registry.",
        "requires_admin": True,
    },
    "SMB_EXPOSED": {
        "type": "powershell",
        "command": "Set-SmbServerConfiguration -EnableSMB1Protocol $false -Force; Set-SmbServerConfiguration -EnableSMB2Protocol $false -Force",
        "params_used": [],
        "explanation_ro": "Opreste protocolul de partajare fisiere SMB.",
        "explanation_en": "Disables the SMB file sharing protocol.",
        "requires_admin": True,
    },
    "UPNP_EXPOSED": {
        "type": "powershell",
        "command": "Stop-Service upnphost -Force; Set-Service upnphost -StartupType Disabled",
        "params_used": [],
        "explanation_ro": "Opreste si dezactiveaza serviciul UPnP care permite deschiderea automata a porturilor.",
        "explanation_en": "Stops and disables the UPnP service that allows automatic port opening.",
        "requires_admin": True,
    },
    "SSH_OPEN": {
        "type": "powershell",
        "command": "Stop-Service sshd -Force; Set-Service sshd -StartupType Disabled",
        "params_used": [],
        "explanation_ro": "Opreste si dezactiveaza serverul SSH (OpenSSH) de pe Windows.",
        "explanation_en": "Stops and disables the SSH server (OpenSSH) on Windows.",
        "requires_admin": True,
    },
    "SNMP_EXPOSED": {
        "type": "powershell",
        "command": "Stop-Service SNMP -Force; Set-Service SNMP -StartupType Disabled",
        "params_used": [],
        "explanation_ro": "Opreste protocolul de monitorizare SNMP.",
        "explanation_en": "Stops the SNMP monitoring protocol.",
        "requires_admin": True,
    },

    # ── Group 2: Firewall block commands (parametrized by port) ───────
    "DB_EXPOSED": {
        "type": "firewall",
        "command": "New-NetFirewallRule -DisplayName 'Block DB port {port}' -Direction Inbound -Action Block -Protocol TCP -LocalPort {port}",
        "params_used": ["port"],
        "explanation_ro": "Blocheaza accesul din retea la portul bazei de date ({port}).",
        "explanation_en": "Blocks network access to the database port ({port}).",
        "requires_admin": True,
    },
    "VNC_EXPOSED": {
        "type": "firewall",
        "command": "New-NetFirewallRule -DisplayName 'Block VNC port {port}' -Direction Inbound -Action Block -Protocol TCP -LocalPort {port}",
        "params_used": ["port"],
        "explanation_ro": "Blocheaza accesul la portul VNC ({port}) prin firewall.",
        "explanation_en": "Blocks access to VNC port ({port}) via firewall.",
        "requires_admin": True,
    },
    "FTP_CLEARTEXT": {
        "type": "firewall",
        "command": "New-NetFirewallRule -DisplayName 'Block FTP port {port}' -Direction Inbound -Action Block -Protocol TCP -LocalPort {port}",
        "params_used": ["port"],
        "explanation_ro": "Blocheaza portul FTP ({port}) care transmite date necriptat.",
        "explanation_en": "Blocks FTP port ({port}) which transmits data unencrypted.",
        "requires_admin": True,
    },
    "MQTT_EXPOSED": {
        "type": "firewall",
        "command": "New-NetFirewallRule -DisplayName 'Block MQTT port {port}' -Direction Inbound -Action Block -Protocol TCP -LocalPort {port}",
        "params_used": ["port"],
        "explanation_ro": "Blocheaza portul MQTT ({port}) al broker-ului IoT.",
        "explanation_en": "Blocks MQTT port ({port}) of the IoT broker.",
        "requires_admin": True,
    },

    # ── Group 3: Magic Portal (cannot fix via CMD) ────────────────────
    "HTTP_ADMIN_CLEARTEXT": {
        "type": "portal",
        "portal_url": "http://{ip}:{port}",
        "params_used": ["ip", "port"],
        "explanation_ro": "Deschide panoul de administrare al dispozitivului. Activeaza HTTPS din setari.",
        "explanation_en": "Opens the device admin panel. Enable HTTPS from settings.",
        "requires_admin": False,
    },
    "CAMERA_STREAM_EXPOSED": {
        "type": "portal",
        "portal_url": "http://{ip}",
        "params_used": ["ip"],
        "explanation_ro": "Deschide panoul camerei. Dezactiveaza RTSP deschis sau seteaza o parola.",
        "explanation_en": "Opens the camera panel. Disable open RTSP or set a password.",
        "requires_admin": False,
    },
    "PRINTER_RAW_EXPOSED": {
        "type": "portal",
        "portal_url": "http://{ip}",
        "params_used": ["ip"],
        "explanation_ro": "Deschide setarile imprimantei. Dezactiveaza Raw Printing / portul 9100.",
        "explanation_en": "Opens printer settings. Disable Raw Printing / port 9100.",
        "requires_admin": False,
    },
    "OUTDATED_SERVICE": {
        "type": "portal",
        "portal_url": "http://{ip}",
        "params_used": ["ip"],
        "explanation_ro": "Deschide dispozitivul. Cauta 'System' sau 'Firmware Upgrade' si actualizeaza.",
        "explanation_en": "Opens the device. Look for 'System' or 'Firmware Upgrade' and update.",
        "requires_admin": False,
    },
    "UNKNOWN_DEVICE": {
        "type": "portal",
        "portal_url": "http://{gateway}",
        "params_used": ["gateway"],
        "explanation_ro": "Deschide routerul. Verifica lista DHCP pentru a identifica dispozitivul necunoscut.",
        "explanation_en": "Opens the router. Check the DHCP list to identify the unknown device.",
        "requires_admin": False,
    },
}


def get_fix_command(finding_code: str, params: dict, language: str = "ro") -> dict | None:
    """Build the parameterized fix command for a finding.

    params: {"ip": "192.168.1.40", "port": 554, "gateway": "192.168.1.1"}
    Returns dict with type, command/portal_url, explanation, etc.
    """
    template = FIX_COMMANDS.get(finding_code)
    if not template:
        return None

    result = {
        "finding_code": finding_code,
        "fix_type": template["type"],
        "requires_admin": template.get("requires_admin", False),
        "explanation": template.get(f"explanation_{language}", template.get("explanation_ro", "")),
    }

    safe_params = {}
    for key in template.get("params_used", []):
        val = str(params.get(key, ""))
        if key == "port":
            val = str(int(val)) if val.isdigit() else "0"
        elif key in ("ip", "gateway"):
            val = val.replace(";", "").replace("&", "").replace("|", "").replace("`", "")
        safe_params[key] = val

    if template["type"] in ("powershell", "firewall"):
        cmd = template["command"]
        for k, v in safe_params.items():
            cmd = cmd.replace("{" + k + "}", v)
        result["command"] = cmd
    elif template["type"] == "portal":
        url = template["portal_url"]
        for k, v in safe_params.items():
            url = url.replace("{" + k + "}", v)
        result["portal_url"] = url

    result["explanation"] = result["explanation"].format(**safe_params) if safe_params else result["explanation"]

    return result
