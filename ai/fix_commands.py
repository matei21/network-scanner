"""Fix guidance for the 15 official findings.

Every finding has two fix paths, because a command only fixes what runs on the machine it runs on:
  - "local":  PowerShell for when the vulnerable service runs on THIS Windows computer. The command is
              built from small parts; each part carries its own explanation (shown in expert mode).
  - "remote": what to change on the other device (router, camera, printer...), where to look in its
              admin panel, and the search phrase used to find model-specific steps online.

Commands are idempotent (safe to run twice), locale independent (firewall groups use their resource
ids, not their English names) and only take a validated integer port.
"""

from __future__ import annotations

import socket


def local_ips() -> set[str]:
    """IP addresses of the computer running this app."""
    ips = {"127.0.0.1", "::1"}
    try:
        ips.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    try:
        # Connecting a UDP socket sends nothing; it only picks the outgoing interface.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    return ips


def is_this_pc(ip: str | None) -> bool:
    return bool(ip) and ip in local_ips()


# ── Command building blocks ──────────────────────────────────────────

def _services(names: list[str], ro: str, en: str) -> dict:
    quoted = ",".join(f"'{n}'" for n in names)
    cmd = (
        f"Get-Service -Name {quoted} -ErrorAction SilentlyContinue | ForEach-Object "
        "{ Stop-Service -Name $_.Name -Force -ErrorAction SilentlyContinue; "
        "Set-Service -Name $_.Name -StartupType Disabled; \"Oprit / stopped: $($_.Name)\" }"
    )
    return {"cmd": cmd, "ro": ro, "en": en}


def _block(proto: str = "TCP") -> dict:
    name = f"NetScanner block {proto} {{port}}"
    cmd = (
        f"Remove-NetFirewallRule -DisplayName '{name}' -ErrorAction SilentlyContinue; "
        f"New-NetFirewallRule -DisplayName '{name}' -Direction Inbound -Protocol {proto} "
        f"-LocalPort {{port}} -Action Block -Profile Any | Out-Null; \"Firewall: blocat / blocked {proto} {{port}}\""
    )
    return {
        "cmd": cmd,
        "ro": f"Creeaza o regula de firewall care blocheaza conexiunile din retea catre portul {proto} {{port}} "
              "(o sterge mai intai pe cea veche, ca sa poti rula comanda de mai multe ori).",
        "en": f"Creates a firewall rule blocking inbound network connections to {proto} port {{port}} "
              "(removes an older copy first, so the command is safe to run twice).",
    }


# Built-in Windows firewall rule groups, by resource id so they work on Romanian/English Windows alike.
_FW_GROUP_RDP = "@FirewallAPI.dll,-28752"
_FW_GROUP_FILE_SHARING = "@FirewallAPI.dll,-28502"


def _listener_report() -> dict:
    cmd = (
        "$c = Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; "
        "if ($c) { $p = Get-Process -Id $c.OwningProcess; "
        "\"Programul de pe portul {port}: $($p.ProcessName) $($p.MainModule.FileVersionInfo.ProductVersion) - $($p.Path)\" } "
        "else { 'Niciun program nu mai asculta pe portul {port}.' }"
    )
    return {
        "cmd": cmd,
        "ro": "Afla ce program asculta pe portul {port} si ce versiune are, ca sa stii exact ce trebuie actualizat.",
        "en": "Finds which program listens on port {port} and its version, so you know exactly what to update.",
    }


# ── The 15 findings ──────────────────────────────────────────────────

FIX_COMMANDS: dict[str, dict] = {
    "TELNET_OPEN": {
        "local": [
            _services(["TlntSvr"], "Opreste si dezactiveaza serviciul Telnet Server (exista doar pe Windows vechi).",
                      "Stops and disables the Telnet Server service (exists only on older Windows)."),
            _block(),
        ],
        "local_explanation": {
            "ro": "Opreste serverul Telnet de pe acest calculator si blocheaza portul lui in firewall.",
            "en": "Stops the Telnet server on this computer and blocks its port in the firewall.",
        },
        "remote": {
            "ro": "Dezactiveaza Telnet din panoul dispozitivului. Foloseste SSH sau aplicatia oficiala daca ai nevoie de acces.",
            "en": "Turn Telnet off in the device's panel. Use SSH or the official app if you need access.",
        },
        "menu_hint": {
            "ro": "Cauta: Administrare / Management → Acces la distanta / Remote Access → Telnet → Dezactivat",
            "en": "Look for: Administration / Management → Remote Access → Telnet → Off",
        },
        "expert": {
            "ro": "Telnet (TCP 23) transmite sesiunea si parola in clar; oricine din retea le poate intercepta (sniffing) si obtine un shell pe dispozitiv.",
            "en": "Telnet (TCP 23) sends the session and password in cleartext; anyone on the network can sniff them and get a shell on the device.",
        },
        "search": "disable telnet",
    },
    "RDP_EXPOSED": {
        "local": [
            {"cmd": "Set-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server' -Name 'fDenyTSConnections' -Value 1",
             "ro": "Opreste Remote Desktop din registrul Windows (fDenyTSConnections = 1 refuza conexiunile noi).",
             "en": "Turns Remote Desktop off in the Windows registry (fDenyTSConnections = 1 refuses new connections)."},
            {"cmd": f"Disable-NetFirewallRule -Group '{_FW_GROUP_RDP}' -ErrorAction SilentlyContinue",
             "ro": "Dezactiveaza regulile de firewall incorporate pentru Remote Desktop (functioneaza pe orice limba a Windows-ului).",
             "en": "Disables the built-in Remote Desktop firewall rules (works on any Windows language)."},
            _block(),
        ],
        "local_explanation": {
            "ro": "Opreste Remote Desktop pe acest calculator si inchide portul in firewall.",
            "en": "Turns off Remote Desktop on this computer and closes the port in the firewall.",
        },
        "remote": {
            "ro": "Pe calculatorul respectiv: Setari → Sistem → Desktop la distanta → Dezactivat. Daca ai nevoie de el, foloseste un VPN.",
            "en": "On that computer: Settings → System → Remote Desktop → Off. If you need it, use a VPN.",
        },
        "menu_hint": {
            "ro": "Pe acel PC Windows: Setari → Sistem → Desktop la distanta",
            "en": "On that Windows PC: Settings → System → Remote Desktop",
        },
        "expert": {
            "ro": "RDP (TCP 3389) expus e tinta frecventa pentru brute-force pe parole si pentru vulnerabilitati ca BlueKeep (CVE-2019-0708) pe sisteme neactualizate.",
            "en": "Exposed RDP (TCP 3389) is a common target for password brute-force and for flaws like BlueKeep (CVE-2019-0708) on unpatched systems.",
        },
        "search": "disable remote desktop",
    },
    "VNC_EXPOSED": {
        "local": [
            _services(["tvnserver", "uvnc_service", "vncserver", "WinVNC4"],
                      "Opreste serverele VNC cunoscute (TightVNC, UltraVNC, RealVNC) daca sunt instalate.",
                      "Stops the known VNC servers (TightVNC, UltraVNC, RealVNC) if installed."),
            _block(),
        ],
        "local_explanation": {
            "ro": "Opreste serverul VNC de pe acest calculator si blocheaza portul in firewall.",
            "en": "Stops the VNC server on this computer and blocks the port in the firewall.",
        },
        "remote": {
            "ro": "In aplicatia VNC de pe acel dispozitiv: opreste serverul sau pune o parola puternica si accepta doar conexiuni locale.",
            "en": "In the VNC app on that device: stop the server, or set a strong password and accept local connections only.",
        },
        "menu_hint": {
            "ro": "In aplicatia VNC: Options / Security → Password si 'Accept connections only from localhost'",
            "en": "In the VNC app: Options / Security → Password and 'Accept connections only from localhost'",
        },
        "expert": {
            "ro": "VNC (TCP 5900+) are adesea autentificare slaba (parola de 8 caractere, DES) si fara criptare; ecranul si tastatura pot fi controlate de la distanta.",
            "en": "VNC (TCP 5900+) often has weak auth (8-character DES password) and no encryption; screen and keyboard can be controlled remotely.",
        },
        "search": "disable VNC server",
    },
    "DB_EXPOSED": {
        "local": [_block()],
        "local_explanation": {
            "ro": "Blocheaza accesul din retea la baza de date de pe acest calculator (programele locale o pot folosi in continuare).",
            "en": "Blocks network access to the database on this computer (local programs can still use it).",
        },
        "remote": {
            "ro": "Pe serverul respectiv: baza de date sa asculte doar local (bind-address = 127.0.0.1) si sa ceara parola.",
            "en": "On that server: make the database listen locally only (bind-address = 127.0.0.1) and require a password.",
        },
        "menu_hint": {
            "ro": "Fisierul de configurare: MySQL my.cnf → bind-address; PostgreSQL postgresql.conf → listen_addresses; Redis redis.conf → bind + requirepass",
            "en": "Config file: MySQL my.cnf → bind-address; PostgreSQL postgresql.conf → listen_addresses; Redis redis.conf → bind + requirepass",
        },
        "expert": {
            "ro": "O baza de date accesibila din LAN permite exfiltrare sau stergere de date; Redis/MongoDB fara parola pot fi preluate complet in cateva secunde.",
            "en": "A database reachable from the LAN allows data theft or deletion; Redis/MongoDB without a password can be fully taken over in seconds.",
        },
        "search": "restrict database access to localhost",
    },
    "CAMERA_STREAM_EXPOSED": {
        "local": [_block()],
        "local_explanation": {
            "ro": "Blocheaza streamul video (RTSP) de pe acest calculator in firewall.",
            "en": "Blocks the video stream (RTSP) on this computer in the firewall.",
        },
        "remote": {
            "ro": "In panoul camerei: activeaza autentificarea pentru RTSP, schimba parola implicita si actualizeaza firmware-ul.",
            "en": "In the camera panel: enable RTSP authentication, change the default password and update the firmware.",
        },
        "menu_hint": {
            "ro": "Cauta: Configurare → Retea → Setari avansate → RTSP / Autentificare (Digest)",
            "en": "Look for: Configuration → Network → Advanced Settings → RTSP / Authentication (Digest)",
        },
        "expert": {
            "ro": "RTSP (TCP 554) fara autentificare permite oricui din retea sa vada streamul (ex: rtsp://ip:554/stream1 in VLC).",
            "en": "RTSP (TCP 554) without authentication lets anyone on the network watch the stream (e.g. rtsp://ip:554/stream1 in VLC).",
        },
        "search": "enable RTSP authentication",
    },
    "OUTDATED_SERVICE": {
        "local": [_listener_report()],
        "local_explanation": {
            "ro": "Afla ce program vechi ruleaza pe acest calculator, ca sa il poti actualiza (comanda doar citeste, nu schimba nimic).",
            "en": "Finds which old program runs on this computer so you can update it (the command only reads, it changes nothing).",
        },
        "remote": {
            "ro": "Actualizeaza firmware-ul dispozitivului din panoul lui sau din aplicatia producatorului.",
            "en": "Update the device's firmware from its panel or the manufacturer's app.",
        },
        "menu_hint": {
            "ro": "Cauta: Sistem / System Tools → Actualizare firmware / Firmware Upgrade",
            "en": "Look for: System / System Tools → Firmware Upgrade",
        },
        "expert": {
            "ro": "Versiunea raportata de serviciu are vulnerabilitati publice (CVE) cu exploit-uri disponibile; actualizarea elimina vectorul de atac cunoscut.",
            "en": "The service version reported has public vulnerabilities (CVEs) with available exploits; updating removes the known attack vector.",
        },
        "search": "firmware update",
    },
    "FTP_CLEARTEXT": {
        "local": [
            _services(["ftpsvc", "FileZilla Server", "filezilla-server"],
                      "Opreste serverul FTP din Windows (IIS) sau FileZilla Server, daca exista.",
                      "Stops the Windows (IIS) FTP server or FileZilla Server, if present."),
            _block(),
        ],
        "local_explanation": {
            "ro": "Opreste serverul FTP de pe acest calculator si blocheaza portul.",
            "en": "Stops the FTP server on this computer and blocks the port.",
        },
        "remote": {
            "ro": "Dezactiveaza FTP pe dispozitiv (NAS sau router cu stick USB) si foloseste SFTP sau FTPS.",
            "en": "Turn FTP off on the device (NAS or router with a USB drive) and use SFTP or FTPS instead.",
        },
        "menu_hint": {
            "ro": "Cauta: USB / Partajare / File Services → FTP → Dezactivat",
            "en": "Look for: USB / Sharing / File Services → FTP → Off",
        },
        "expert": {
            "ro": "FTP (TCP 21) trimite utilizatorul, parola si fisierele necriptate; SFTP (peste SSH) sau FTPS (TLS) rezolva problema.",
            "en": "FTP (TCP 21) sends username, password and files unencrypted; SFTP (over SSH) or FTPS (TLS) solves it.",
        },
        "search": "disable FTP enable SFTP",
    },
    "HTTP_ADMIN_CLEARTEXT": {
        "local": [_block()],
        "local_explanation": {
            "ro": "Blocheaza din retea pagina web necriptata de pe acest calculator.",
            "en": "Blocks network access to the unencrypted web page on this computer.",
        },
        "remote": {
            "ro": "In panoul dispozitivului: activeaza HTTPS pentru administrare, opreste accesul prin HTTP si schimba parola implicita.",
            "en": "In the device panel: enable HTTPS for administration, turn off HTTP access and change the default password.",
        },
        "menu_hint": {
            "ro": "Cauta: Sistem / Administrare → Management local → HTTPS activ, HTTP dezactivat",
            "en": "Look for: System / Administration → Local Management → HTTPS on, HTTP off",
        },
        "expert": {
            "ro": "Login-ul prin HTTP (fara TLS) trimite parola in clar; un atacator din LAN o poate intercepta prin ARP spoofing.",
            "en": "Logging in over HTTP (no TLS) sends the password in cleartext; a LAN attacker can capture it via ARP spoofing.",
        },
        "search": "enable HTTPS admin disable HTTP",
    },
    "SMB_EXPOSED": {
        "local": [
            {"cmd": "Set-SmbServerConfiguration -EnableSMB1Protocol $false -Force",
             "ro": "Dezactiveaza SMBv1, versiunea veche folosita de WannaCry (SMBv2/3 raman pentru uz local).",
             "en": "Disables SMBv1, the old version abused by WannaCry (SMBv2/3 stay for local use)."},
            {"cmd": f"Disable-NetFirewallRule -Group '{_FW_GROUP_FILE_SHARING}' -ErrorAction SilentlyContinue",
             "ro": "Dezactiveaza regulile de firewall 'Partajare fisiere si imprimante', ca folderele sa nu mai fie vizibile in retea.",
             "en": "Disables the 'File and Printer Sharing' firewall rules so folders are no longer reachable from the network."},
        ],
        "local_explanation": {
            "ro": "Opreste partajarea de fisiere in retea pe acest calculator si dezactiveaza versiunea veche si periculoasa SMBv1.",
            "en": "Stops file sharing over the network on this computer and disables the old, dangerous SMBv1.",
        },
        "remote": {
            "ro": "Pe dispozitiv (NAS/router): dezactiveaza SMBv1, opreste accesul 'guest' si cere utilizator + parola.",
            "en": "On the device (NAS/router): disable SMBv1, turn off guest access and require a username + password.",
        },
        "menu_hint": {
            "ro": "Cauta: File Services / Partajare → SMB → Versiune minima SMB2, Guest dezactivat",
            "en": "Look for: File Services / Sharing → SMB → Minimum version SMB2, Guest off",
        },
        "expert": {
            "ro": "SMB (TCP 445) expus permite enumerarea partajarilor si atacuri ca EternalBlue (MS17-010) pe SMBv1.",
            "en": "Exposed SMB (TCP 445) allows share enumeration and attacks like EternalBlue (MS17-010) on SMBv1.",
        },
        "search": "disable SMB guest access SMBv1",
    },
    "MQTT_EXPOSED": {
        "local": [
            _services(["mosquitto"], "Opreste broker-ul Mosquitto MQTT daca ruleaza pe acest calculator.",
                      "Stops the Mosquitto MQTT broker if it runs on this computer."),
            _block(),
        ],
        "local_explanation": {
            "ro": "Opreste broker-ul MQTT de pe acest calculator si blocheaza portul.",
            "en": "Stops the MQTT broker on this computer and blocks the port.",
        },
        "remote": {
            "ro": "In hub-ul smart home: dezactiveaza accesul anonim, pune utilizator si parola, si foloseste portul criptat 8883 (TLS).",
            "en": "In the smart home hub: turn off anonymous access, set a username and password, and use the encrypted port 8883 (TLS).",
        },
        "menu_hint": {
            "ro": "Mosquitto: in mosquitto.conf seteaza 'allow_anonymous false' si 'password_file'",
            "en": "Mosquitto: in mosquitto.conf set 'allow_anonymous false' and 'password_file'",
        },
        "expert": {
            "ro": "MQTT (TCP 1883) fara autentificare permite abonarea la '#' (toate mesajele) si publicarea de comenzi catre dispozitive.",
            "en": "MQTT (TCP 1883) without auth allows subscribing to '#' (all messages) and publishing commands to devices.",
        },
        "search": "MQTT enable authentication disable anonymous",
    },
    "UPNP_EXPOSED": {
        "local": [
            _services(["upnphost", "SSDPSRV"],
                      "Opreste serviciile UPnP Device Host si SSDP Discovery, care raspund la cererile UPnP pe acest calculator.",
                      "Stops the UPnP Device Host and SSDP Discovery services, which answer UPnP requests on this computer."),
        ],
        "local_explanation": {
            "ro": "Opreste serviciile UPnP de pe acest calculator.",
            "en": "Stops the UPnP services on this computer.",
        },
        "remote": {
            "ro": "Dezactiveaza UPnP din router. Daca o consola sau un joc nu mai merge, deschide manual doar porturile de care are nevoie.",
            "en": "Turn UPnP off in the router. If a console or game stops working, manually forward only the ports it needs.",
        },
        "menu_hint": {
            "ro": "Cauta: Avansat → NAT Forwarding / Redirectionare → UPnP → Dezactivat",
            "en": "Look for: Advanced → NAT Forwarding → UPnP → Off",
        },
        "expert": {
            "ro": "UPnP IGD (SSDP pe UDP 1900) lasa orice program din LAN, inclusiv malware, sa deschida porturi spre internet fara autentificare.",
            "en": "UPnP IGD (SSDP on UDP 1900) lets any program on the LAN, malware included, open ports to the internet without authentication.",
        },
        "search": "disable UPnP",
    },
    "SNMP_EXPOSED": {
        "local": [
            _services(["SNMP"], "Opreste serviciul SNMP din Windows daca este instalat.",
                      "Stops the Windows SNMP service if installed."),
            _block("UDP"),
        ],
        "local_explanation": {
            "ro": "Opreste SNMP pe acest calculator si blocheaza portul UDP.",
            "en": "Stops SNMP on this computer and blocks the UDP port.",
        },
        "remote": {
            "ro": "In panoul dispozitivului: dezactiveaza SNMP sau schimba 'community' din 'public' intr-o parola lunga.",
            "en": "In the device panel: turn SNMP off or change the 'community' from 'public' to a long secret.",
        },
        "menu_hint": {
            "ro": "Cauta: Retea / Management → SNMP → Dezactivat (sau SNMPv3 cu parola)",
            "en": "Look for: Network / Management → SNMP → Off (or SNMPv3 with a password)",
        },
        "expert": {
            "ro": "SNMP v1/v2c (UDP 161) cu community 'public' expune configuratia, interfetele si uneori permite modificari (community 'private').",
            "en": "SNMP v1/v2c (UDP 161) with community 'public' exposes configuration and interfaces, and sometimes allows writes ('private').",
        },
        "search": "disable SNMP change community",
    },
    "PRINTER_RAW_EXPOSED": {
        "local": [_block()],
        "local_explanation": {
            "ro": "Blocheaza portul de imprimare directa (9100) pe acest calculator.",
            "en": "Blocks the raw printing port (9100) on this computer.",
        },
        "remote": {
            "ro": "In panoul imprimantei: dezactiveaza 'Raw / Port 9100 / JetDirect' daca nu il folosesti si pune parola de administrator.",
            "en": "In the printer panel: turn off 'Raw / Port 9100 / JetDirect' if unused and set an admin password.",
        },
        "menu_hint": {
            "ro": "Cauta: Retea → Protocoale → Raw Port / 9100 → Dezactivat",
            "en": "Look for: Network → Protocols → Raw Port / 9100 → Off",
        },
        "expert": {
            "ro": "Portul 9100 (JetDirect/PJL) accepta joburi fara autentificare: oricine poate printa si, prin PJL, citi sau schimba setari.",
            "en": "Port 9100 (JetDirect/PJL) accepts jobs without auth: anyone can print and, via PJL, read or change settings.",
        },
        "search": "disable raw printing port 9100",
    },
    "UNKNOWN_DEVICE": {
        "local": [],
        "local_explanation": {"ro": "", "en": ""},
        "remote": {
            "ro": "Deschide routerul, cauta lista de dispozitive conectate si identifica-l. Daca nu il recunosti, blocheaza-l si schimba parola WiFi.",
            "en": "Open the router, find the list of connected devices and identify it. If you don't recognize it, block it and change the WiFi password.",
        },
        "menu_hint": {
            "ro": "Cauta: DHCP → Lista clienti / Dispozitive conectate; apoi Control acces → Blocheaza",
            "en": "Look for: DHCP → Client List / Connected Devices; then Access Control → Block",
        },
        "expert": {
            "ro": "Un host neidentificat poate fi un dispozitiv strain in retea; compara adresa MAC (OUI) si hostname-ul cu lista DHCP.",
            "en": "An unidentified host may be a foreign device on the network; compare its MAC (OUI) and hostname against the DHCP list.",
        },
        "search": "see connected devices block device",
        "panel_on_gateway": True,
    },
    "SSH_OPEN": {
        "local": [
            _services(["sshd"], "Opreste si dezactiveaza serverul OpenSSH de pe Windows.",
                      "Stops and disables the OpenSSH server on Windows."),
            {"cmd": "Disable-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue",
             "ro": "Dezactiveaza regula de firewall creata la instalarea OpenSSH Server.",
             "en": "Disables the firewall rule created when OpenSSH Server was installed."},
            _block(),
        ],
        "local_explanation": {
            "ro": "Opreste serverul SSH de pe acest calculator si inchide portul.",
            "en": "Stops the SSH server on this computer and closes the port.",
        },
        "remote": {
            "ro": "Daca nu folosesti SSH, dezactiveaza-l. Daca il folosesti: doar chei SSH, fara parole, fara login ca root.",
            "en": "If you don't use SSH, turn it off. If you do: keys only, no passwords, no root login.",
        },
        "menu_hint": {
            "ro": "In /etc/ssh/sshd_config: PasswordAuthentication no, PermitRootLogin no; pe router: Administrare → SSH",
            "en": "In /etc/ssh/sshd_config: PasswordAuthentication no, PermitRootLogin no; on a router: Administration → SSH",
        },
        "expert": {
            "ro": "SSH (TCP 22) e criptat, dar cu login prin parola e expus la brute-force; autentificarea cu chei elimina riscul.",
            "en": "SSH (TCP 22) is encrypted, but password login is exposed to brute-force; key-based auth removes the risk.",
        },
        "search": "disable SSH password authentication",
    },
}


def _fill(text: str, params: dict) -> str:
    for k, v in params.items():
        text = text.replace("{" + k + "}", v)
    return text


def _safe_params(params: dict) -> dict:
    port = str(params.get("port", ""))
    return {"port": str(int(port)) if port.isdigit() and 0 < int(port) < 65536 else "0"}


# Device types where a Windows PowerShell command could apply when run on that device itself.
_MAYBE_WINDOWS = {"computer", "server", "unknown", ""}


def get_fix_command(finding_code: str, params: dict, language: str = "ro",
                    is_this_pc: bool = False, panel_url: str | None = None,
                    device_type: str = "") -> dict | None:
    """Fix guidance for one finding.

    params: {"ip": "192.168.1.40", "port": 554}
    is_this_pc: the finding is on the computer running this app, so the local command fixes it.
    panel_url: the device's web admin page, when the scan shows one.
    """
    template = FIX_COMMANDS.get(finding_code)
    if not template:
        return None
    lang = "en" if language == "en" else "ro"
    safe = _safe_params(params)

    parts = [{"cmd": _fill(p["cmd"], safe), "meaning": _fill(p[lang], safe)} for p in template["local"]]
    command = "; ".join(p["cmd"] for p in parts)
    needs_port = any("{port}" in p["cmd"] for p in template["local"])
    has_local = bool(parts) and (safe["port"] != "0" or not needs_port)
    can_run = is_this_pc and has_local
    show_command = has_local and (is_this_pc or device_type in _MAYBE_WINDOWS)

    if can_run:
        fix_type, explanation = "powershell", _fill(template["local_explanation"][lang], safe)
    elif panel_url:
        fix_type, explanation = "portal", template["remote"][lang]
    else:
        fix_type, explanation = "manual", template["remote"][lang]

    return {
        "finding_code": finding_code,
        "target": "this_pc" if is_this_pc else "remote",
        "fix_type": fix_type,
        "can_run": can_run,
        "requires_admin": has_local,
        "explanation": explanation,
        "explanation_expert": template["expert"][lang],
        "menu_hint": template["menu_hint"][lang],
        "remote_explanation": template["remote"][lang],
        "local_explanation": _fill(template["local_explanation"][lang], safe),
        "command": command if show_command else "",
        "command_parts": parts if show_command else [],
        "portal_url": panel_url or "",
        "search_action": template["search"],
    }
