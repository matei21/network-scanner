"""Q&A assistant grounded only on scan evidence (FR-12, NFR-06).
API key from env ANTHROPIC_API_KEY or LLM_API_KEY, never hard-coded.

Usage:
    from ai.assistant import Assistant

    assistant = Assistant(scan_data)   # scan_data = dict from analyzer
    answer = assistant.ask("Ce e cel mai periculos?")
    print(answer["text"])              # raspunsul
    print(answer["source"])            # "cloud", "local", sau "template"
"""

from __future__ import annotations

import os
from typing import Optional

from ai.ai_service import AIService, Chatbot, build_scan_context
from ai.fingerprint import guess_device_type
from ai.templates import get_template, FINDING_TEMPLATES
from ai.search_service import search_device_guide, format_search_results


class Assistant:
    """Q&A assistant care raspunde la intrebari despre un scan."""

    def __init__(self, scan_data: dict, enable_cloud: bool = False, enable_local: bool = True, groq_api_key: str | None = None):
        self.scan_data = scan_data
        self.ai = AIService(enable_cloud=enable_cloud, enable_local=enable_local, groq_api_key=groq_api_key)
        self.chatbot = Chatbot(self.ai, scan_data)

    def ask(self, question: str, language: str = "ro", expert: bool = False) -> dict:
        """Pune o intrebare despre scan. Returneaza {text, source, agents, ...}."""
        return self.chatbot.ask(question, language, expert)

    def explain(self, finding_code: str, device_info: dict, language: str = "ro") -> dict:
        """Genereaza explicatie personalizata pentru un finding."""
        return self.ai.explain_finding(finding_code, device_info, language)

    def get_fix(self, finding_code: str, device_info: dict, language: str = "ro") -> dict:
        """Genereaza pasi de remediere personalizati."""
        return self.ai.generate_fix_steps(finding_code, device_info, language)

    def get_detailed_fix(self, finding_code: str, device_info: dict, language: str = "ro", expert: bool = False) -> dict:
        """
        Agentic pipeline for detailed fix:
          1. Search Integrator agent filters DuckDuckGo results
          2. Advisor agent combines filtered results + generic advice + template
        Each agent gets a short focused prompt — no hallucination from prompt overload.
        """
        if self.chatbot._orchestrator:
            return self.chatbot._orchestrator.detailed_fix(finding_code, device_info, language, expert)

        # Fallback: old monolithic path (if orchestrator failed to init)
        action = _code_to_action(finding_code)
        generic_advice = _get_generic_advice(finding_code, language)
        template = get_template(finding_code, language)
        template_steps = template["fix_steps"] if template else []
        search_results = search_device_guide(
            device_info.get("vendor", ""), device_info.get("product", ""), action
        )
        result = self.ai.chat(
            f"Scrie maxim 5 pasi de rezolvare pentru {finding_code}.",
            f"{generic_advice}\n{format_search_results(search_results)}",
            finding_code, language,
        )
        result["search_results"] = search_results
        result["generic_advice"] = generic_advice
        result["template_steps"] = template_steps
        return result

    def reset(self):
        """Sterge istoricul conversatiei."""
        self.chatbot.reset()

    @property
    def status(self) -> dict:
        """Returneaza statusul serviciilor AI disponibile."""
        return self.ai.status


def enrich_scan_data(scan_result_dict: dict) -> dict:
    """
    Imbogateste datele unui scan cu informatii AI:
    - device type + icon (fingerprinting)
    - explicatii + fix steps (template-uri)
    - CIS/OWASP mapping

    Primeste dict-ul din analyzer (ScanResult.to_dict) si adauga campuri.
    Aceasta functie NU apeleaza LLM -- doar template-uri si fingerprinting.
    E determinista si rapida.
    """
    if scan_result_dict.get("error"):
        return scan_result_dict

    for device in scan_result_dict.get("devices", []):
        # Fingerprinting
        fp = guess_device_type({
            "vendor": device.get("vendor", ""),
            "hostname": device.get("hostname", ""),
            "services": [
                p.get("service", "")
                for p in device.get("open_ports", [])
            ],
            "is_gateway": device.get("is_gateway", False),
        })
        device["type"] = fp["type"]
        device["icon"] = fp["icon"]
        device["type_label_ro"] = fp["label_ro"]
        device["type_label_en"] = fp["label_en"]

        # Explicatii si fix-uri din template-uri pentru fiecare finding
        for finding in device.get("findings", []):
            code = finding.get("code", "")
            for lang in ("ro", "en"):
                template = get_template(code, lang)
                if template:
                    finding[f"explanation_{lang}"] = template["explanation"]
                    finding[f"metaphor_{lang}"] = template["metaphor"]
                    finding[f"fix_steps_{lang}"] = template["fix_steps"]
                    finding[f"cis_control"] = template["cis_control"]
                    finding[f"owasp_iot"] = template["owasp_iot"]
                finding[f"risk_scenario_{lang}"] = get_risk_scenario(code, lang)

    # Compute custom risk score and attach it
    scan_result_dict["custom_risk_score"] = custom_risk_score(scan_result_dict)

    return scan_result_dict


# ── Custom Risk Score ─────────────────────────────────────────────────
#
# The official score treats every finding the same: 100 - sum(points). The weighted score keeps that as
# its base and adjusts it for context the official formula can't see. Every adjustment is a signed delta
# (negative = riskier), so the rows shown in the UI and the PDF always add up to the final score.

_DEVICE_TYPE_WEIGHT = {
    "router": 1.25,     # the gateway protects every other device
    "camera": 1.25,     # privacy: video of the inside of the home
    "server": 1.2,      # holds data / shared files
    "smart_home": 1.15, # can control locks, plugs, heating
    "unknown": 1.1,     # unidentified = not trusted
    "computer": 1.0,
    "phone": 1.0,
    "smart_tv": 0.9,
    "printer": 0.9,
}

# Pairs on the SAME device that make each other worse.
_DANGEROUS_COMBOS = [
    (("HTTP_ADMIN_CLEARTEXT", "TELNET_OPEN"), "cleartext_admin"),     # two plaintext admin channels, same password
    (("OUTDATED_SERVICE", "TELNET_OPEN"), "exploitable_shell"),        # known exploit + remote shell
    (("CAMERA_STREAM_EXPOSED", "HTTP_ADMIN_CLEARTEXT"), "camera_takeover"),  # watch the stream + steal the admin password
    (("RDP_EXPOSED", "SMB_EXPOSED"), "lateral_movement"),              # classic Windows lateral movement pair
    (("DB_EXPOSED", "OUTDATED_SERVICE"), "exploitable_data"),
    (("DB_EXPOSED", "SMB_EXPOSED"), "data_exposure"),
    (("OUTDATED_SERVICE", "VNC_EXPOSED"), "exploitable_shell"),
]

_DENSITY_PER_FINDING = 3      # per finding beyond the 2nd on one device
_DENSITY_CAP = 6              # per device
_COMBO_PENALTY = 8
_COMBO_CAP = 16
_SPREAD_PENALTY = 5           # more than 60% of devices have issues (at least 3 devices)
_GATEWAY_HIGH_PENALTY = 10    # the router itself has a HIGH finding
# The weighted score refines the official one, it doesn't replace it: adjustments are bounded.
_MAX_PENALTY = 30
_MAX_BONUS = 10


def custom_risk_score(scan_data: dict) -> dict:
    """Weighted risk score: official base + context adjustments. See the constants above."""
    devices = scan_data.get("devices", [])
    standard_score = scan_data.get("score")
    base_points = sum(f.get("points", 0) for d in devices for f in d.get("findings", []))
    breakdown: list[dict] = []
    if base_points:
        n = sum(len(d.get("findings", [])) for d in devices)
        breakdown.append({"key": "findings", "delta": -base_points, "detail": str(n)})

    # 1. Device criticality: the same finding matters more on a router than on a printer.
    weight_delta = 0.0
    weighted = []
    for d in devices:
        pts = sum(f.get("points", 0) for f in d.get("findings", []))
        w = _DEVICE_TYPE_WEIGHT.get(d.get("type", "unknown"), 1.0)
        if pts and w != 1.0:
            weight_delta -= pts * (w - 1.0)
            weighted.append(f"{d.get('ip', '?')} x{w:g}")
    if round(weight_delta):
        breakdown.append({"key": "device_weight", "delta": round(weight_delta), "detail": ", ".join(weighted)})

    # 2. Concentration: many issues on one device usually mean it was never configured.
    for d in devices:
        n = len(d.get("findings", []))
        if n >= 3:
            breakdown.append({"key": "density", "delta": -min((n - 2) * _DENSITY_PER_FINDING, _DENSITY_CAP),
                              "detail": f"{d.get('ip', '?')} ({n})"})

    # 3. Dangerous combinations on the same device (capped so one device can't dominate).
    combo_total = 0
    for d in devices:
        codes = {f.get("code", "") for f in d.get("findings", [])}
        for pair, _kind in _DANGEROUS_COMBOS:
            if set(pair) <= codes and combo_total < _COMBO_CAP:
                delta = min(_COMBO_PENALTY, _COMBO_CAP - combo_total)
                combo_total += delta
                breakdown.append({"key": "combo", "delta": -delta, "detail": f"{' + '.join(pair)} @ {d.get('ip', '?')}"})

    # 4. Spread: problems on most devices point to a network-wide habit (default settings everywhere).
    affected = sum(1 for d in devices if d.get("findings"))
    if len(devices) >= 3 and affected / len(devices) > 0.6:
        breakdown.append({"key": "systemic", "delta": -_SPREAD_PENALTY, "detail": f"{affected}/{len(devices)}"})

    # 5. Gateway: a HIGH issue on the router exposes everything behind it.
    gateway = next((d for d in devices if d.get("type") == "router" or d.get("is_gateway")), None)
    if gateway and any(f.get("severity") == "high" for f in gateway.get("findings", [])):
        breakdown.append({"key": "gateway_high", "delta": -_GATEWAY_HIGH_PENALTY, "detail": gateway.get("ip", "?")})

    adjust = sum(item["delta"] for item in breakdown if item["key"] != "findings")
    bounded = max(-_MAX_PENALTY, min(_MAX_BONUS, adjust))
    if bounded != adjust:
        breakdown.append({"key": "cap", "delta": bounded - adjust, "detail": f"{-_MAX_PENALTY}/+{_MAX_BONUS}"})

    raw = 100 + sum(item["delta"] for item in breakdown)
    return {
        "score": max(0, min(100, raw)),
        "standard_score": standard_score,
        "raw": raw,
        "breakdown": breakdown,
        "weights": _DEVICE_TYPE_WEIGHT,
    }


def enrich_findings_list(findings: list[dict]) -> list[dict]:
    """
    Varianta care lucreaza pe o lista flat de findings (nu nested per device).
    Adauga explicatii, fix-uri, CIS/OWASP.
    """
    for finding in findings:
        code = finding.get("code", "")
        for lang in ("ro", "en"):
            template = get_template(code, lang)
            if template:
                finding[f"explanation_{lang}"] = template["explanation"]
                finding[f"metaphor_{lang}"] = template["metaphor"]
                finding[f"fix_steps_{lang}"] = template["fix_steps"]
                finding["cis_control"] = template["cis_control"]
                finding["owasp_iot"] = template["owasp_iot"]
                finding["severity"] = template["severity"]
                finding["points"] = template["points"]
    return findings


def _code_to_action(finding_code: str) -> str:
    """Converteste un finding code in actiune de search."""
    actions = {
        "TELNET_OPEN": "disable telnet",
        "RDP_EXPOSED": "disable remote desktop",
        "VNC_EXPOSED": "disable VNC",
        "DB_EXPOSED": "restrict database access localhost only",
        "CAMERA_STREAM_EXPOSED": "enable RTSP authentication",
        "OUTDATED_SERVICE": "update firmware software",
        "FTP_CLEARTEXT": "disable FTP enable SFTP",
        "HTTP_ADMIN_CLEARTEXT": "enable HTTPS admin",
        "SMB_EXPOSED": "disable file sharing SMB",
        "MQTT_EXPOSED": "enable MQTT authentication",
        "UPNP_EXPOSED": "disable UPnP",
        "SNMP_EXPOSED": "disable SNMP",
        "PRINTER_RAW_EXPOSED": "restrict printer access",
        "UNKNOWN_DEVICE": "identify unknown device network",
        "SSH_OPEN": "secure SSH disable password authentication",
    }
    return actions.get(finding_code, "fix security issue")


# Sfaturi generice per finding -- fallback cand DuckDuckGo nu gaseste nimic relevant.
# Structura: ce sa caute utilizatorul in meniul dispozitivului, indiferent de marca.
_GENERIC_ADVICE = {
    "ro": {
        "TELNET_OPEN": (
            "Cauta in setarile dispozitivului meniul 'Administrare' sau 'Management'. "
            "Cauta optiunea 'Telnet' si dezactiveaz-o. "
            "Daca nu gasesti Telnet explicit, cauta 'Remote Access' sau 'Acces la distanta' "
            "si dezactiveaza tot ce nu folosesti. "
            "Dupa dezactivare, verifica ca poti accesa dispozitivul prin interfata web (browser)."
        ),
        "RDP_EXPOSED": (
            "Pe calculator, deschide 'Setari' > 'Sistem' > 'Desktop la distanta' si dezactiveaza-l. "
            "Daca ai nevoie de acces de la distanta, activeaza un VPN in loc. "
            "Pe Windows, cauta 'Remote Desktop Settings' in bara de cautare."
        ),
        "VNC_EXPOSED": (
            "Cauta programul VNC Server (ex: RealVNC, TightVNC) in bara de aplicatii (system tray). "
            "Click dreapta pe iconita si opreste serviciul sau seteaza o parola puternica. "
            "Daca nu ai nevoie de control la distanta, dezinstaleaza programul VNC complet."
        ),
        "DB_EXPOSED": (
            "Baza de date nu ar trebui sa fie accesibila din retea. "
            "In fisierul de configurare al bazei de date, seteaza 'bind-address' la '127.0.0.1' "
            "ca sa asculte doar local. "
            "Daca nu stii unde e configurarea, cauta 'my.cnf' (MySQL) sau 'postgresql.conf' (PostgreSQL)."
        ),
        "CAMERA_STREAM_EXPOSED": (
            "Deschide aplicatia camerei sau acceseaz-o prin browser la adresa IP afisata. "
            "Cauta 'Settings' > 'Network' > 'RTSP' sau 'Stream'. "
            "Activeaza 'Authentication' / 'Autentificare' pentru stream. "
            "Seteaza un username si parola puternica. "
            "Daca nu gasesti optiunea, cauta butonul de 'Security' sau 'Securitate'."
        ),
        "OUTDATED_SERVICE": (
            "Verifica versiunea curenta a software-ului sau firmware-ului. "
            "Cauta pe site-ul producatorului sectiunea 'Support' sau 'Downloads'. "
            "Descarca ultima versiune si urmeaza instructiunile de actualizare. "
            "La routere si camere, cauta 'Firmware Update' in setari. "
            "IMPORTANT: Nu intrerupe alimentarea in timpul actualizarii!"
        ),
        "FTP_CLEARTEXT": (
            "Cauta in setarile dispozitivului optiunea 'FTP' si dezactiveaz-o. "
            "Daca ai nevoie de transfer de fisiere, foloseste 'SFTP' sau 'SCP' in loc. "
            "Pe routere, meniul e de obicei la 'USB' > 'FTP Server' sau 'Storage Sharing'."
        ),
        "HTTP_ADMIN_CLEARTEXT": (
            "Deschide setarile dispozitivului in browser. "
            "Cauta 'Administration' > 'Management' sau 'System'. "
            "Activeaza 'HTTPS' / 'SSL' si dezactiveaza 'HTTP' simplu. "
            "Daca nu exista optiunea de HTTPS, schimba cel putin parola de admin cu una puternica. "
            "Cauta si optiunea de a schimba portul de administrare."
        ),
        "SMB_EXPOSED": (
            "Pe router, cauta 'USB' > 'File Sharing' sau 'Samba/SMB' si dezactiveaza-l. "
            "Pe Windows, deschide 'Panou de Control' > 'Programe' > 'Activeaza/Dezactiveaza caracteristici Windows' "
            "si debifati 'SMB 1.0'. "
            "Daca ai nevoie de partajare fisiere, pune o parola pe fiecare folder partajat."
        ),
        "MQTT_EXPOSED": (
            "MQTT e un protocol folosit de dispozitivele smart home. "
            "Deschide configurarea broker-ului MQTT (ex: Mosquitto). "
            "Adauga autentificare cu username si parola. "
            "In fisierul de configurare, adauga 'allow_anonymous false' si creaza un fisier de parole."
        ),
        "UPNP_EXPOSED": (
            "Deschide setarile routerului in browser (de obicei 192.168.1.1 sau 192.168.0.1). "
            "Cauta meniul 'NAT' / 'Forwarding' / 'Advanced'. "
            "Gaseste optiunea 'UPnP' si dezactiveaz-o. "
            "Dispozitivele care aveau nevoie de UPnP pot necesita port forwarding manual."
        ),
        "SNMP_EXPOSED": (
            "SNMP e un protocol de monitorizare a retelei, rar necesar acasa. "
            "In setarile dispozitivului, cauta 'SNMP' si dezactiveaz-o. "
            "La imprimante, cautati in 'Network Settings' > 'SNMP'. "
            "Daca nu gasesti, cauta 'Management' sau 'Monitoring'."
        ),
        "PRINTER_RAW_EXPOSED": (
            "Portul 9100 al imprimantei e deschis fara protectie. "
            "Deschide pagina web a imprimantei (IP-ul afisat, in browser). "
            "Cauta 'Networking' > 'Raw Port' sau 'Port 9100' sau 'JetDirect'. "
            "Daca nu ai nevoie de printare din retea, dezactiveaza portul. "
            "Altfel, adauga o parola de admin pe imprimanta."
        ),
        "UNKNOWN_DEVICE": (
            "Un dispozitiv necunoscut e conectat la reteaua ta. "
            "Verifica adresa MAC pe site-ul producatorului pentru a identifica ce e. "
            "Daca nu il recunosti, schimba parola WiFi pentru a-l deconecta. "
            "In setarile routerului, cauta 'Connected Devices' / 'Client List' si blocheaza MAC-ul."
        ),
        "SSH_OPEN": (
            "Deschide configurarea SSH (de obicei fisierul /etc/ssh/sshd_config). "
            "Seteaza 'PasswordAuthentication no' si foloseste chei SSH in loc. "
            "Schimba portul din 22 in alt numar (ex: 2222). "
            "Daca nu ai nevoie de SSH, dezactiveaz-a complet din setarile dispozitivului."
        ),
    },
    "en": {
        "TELNET_OPEN": (
            "Look in the device settings for 'Administration' or 'Management'. "
            "Find the 'Telnet' option and disable it. "
            "If Telnet isn't listed explicitly, look for 'Remote Access' and disable everything you don't use. "
            "After disabling, verify you can still access the device via its web interface (browser)."
        ),
        "RDP_EXPOSED": (
            "On your computer, open Settings > System > Remote Desktop and turn it off. "
            "If you need remote access, use a VPN instead. "
            "On Windows, search for 'Remote Desktop Settings' in the search bar."
        ),
        "VNC_EXPOSED": (
            "Look for the VNC Server program (e.g., RealVNC, TightVNC) in the system tray. "
            "Right-click its icon and stop the service, or set a strong password. "
            "If you don't need remote control, uninstall the VNC program entirely."
        ),
        "DB_EXPOSED": (
            "The database should not be accessible from the network. "
            "In the database configuration file, set 'bind-address' to '127.0.0.1' to listen locally only. "
            "If unsure where the config is, look for 'my.cnf' (MySQL) or 'postgresql.conf' (PostgreSQL)."
        ),
        "CAMERA_STREAM_EXPOSED": (
            "Open the camera app or access it via browser at the displayed IP address. "
            "Look for Settings > Network > RTSP or Stream. "
            "Enable 'Authentication' for the stream and set a strong username and password. "
            "If you can't find the option, look for a 'Security' button."
        ),
        "OUTDATED_SERVICE": (
            "Check the current software or firmware version. "
            "Visit the manufacturer's website, Support or Downloads section. "
            "Download the latest version and follow the update instructions. "
            "For routers and cameras, look for 'Firmware Update' in settings. "
            "IMPORTANT: Do not interrupt power during the update!"
        ),
        "FTP_CLEARTEXT": (
            "Look in the device settings for 'FTP' and disable it. "
            "If you need file transfers, use 'SFTP' or 'SCP' instead. "
            "On routers, the menu is usually under USB > FTP Server or Storage Sharing."
        ),
        "HTTP_ADMIN_CLEARTEXT": (
            "Open the device settings in your browser. "
            "Look for Administration > Management or System. "
            "Enable 'HTTPS' / 'SSL' and disable plain 'HTTP'. "
            "If HTTPS isn't available, at least change the admin password to a strong one. "
            "Also look for an option to change the admin port."
        ),
        "SMB_EXPOSED": (
            "On the router, look for USB > File Sharing or Samba/SMB and disable it. "
            "On Windows, open Control Panel > Programs > Turn Windows features on or off "
            "and uncheck 'SMB 1.0'. "
            "If you need file sharing, put a password on every shared folder."
        ),
        "MQTT_EXPOSED": (
            "MQTT is a protocol used by smart home devices. "
            "Open the MQTT broker configuration (e.g., Mosquitto). "
            "Add username and password authentication. "
            "In the config file, add 'allow_anonymous false' and create a password file."
        ),
        "UPNP_EXPOSED": (
            "Open the router settings in your browser (usually 192.168.1.1 or 192.168.0.1). "
            "Look for NAT / Forwarding / Advanced menu. "
            "Find the 'UPnP' option and disable it. "
            "Devices that relied on UPnP may need manual port forwarding."
        ),
        "SNMP_EXPOSED": (
            "SNMP is a network monitoring protocol, rarely needed at home. "
            "In the device settings, look for 'SNMP' and disable it. "
            "For printers, check Network Settings > SNMP. "
            "If you can't find it, look under 'Management' or 'Monitoring'."
        ),
        "PRINTER_RAW_EXPOSED": (
            "The printer's port 9100 is open without protection. "
            "Open the printer's web page (the displayed IP, in your browser). "
            "Look for Networking > Raw Port or Port 9100 or JetDirect. "
            "If you don't need network printing, disable the port. "
            "Otherwise, add an admin password to the printer."
        ),
        "UNKNOWN_DEVICE": (
            "An unknown device is connected to your network. "
            "Check the MAC address on the manufacturer's website to identify it. "
            "If you don't recognize it, change your WiFi password to disconnect it. "
            "In the router settings, look for Connected Devices / Client List and block the MAC."
        ),
        "SSH_OPEN": (
            "Open the SSH configuration (usually /etc/ssh/sshd_config). "
            "Set 'PasswordAuthentication no' and use SSH keys instead. "
            "Change the port from 22 to another number (e.g., 2222). "
            "If you don't need SSH, disable it completely in the device settings."
        ),
    },
}


def _get_generic_advice(finding_code: str, language: str = "ro") -> str:
    """Returneaza sfaturi generice pentru un finding, indiferent de dispozitiv."""
    lang = language if language in _GENERIC_ADVICE else "ro"
    return _GENERIC_ADVICE[lang].get(
        finding_code,
        "Cauta in setarile dispozitivului optiunea legata de acest serviciu si dezactiveaz-o."
        if lang == "ro"
        else "Look in the device settings for the option related to this service and disable it.",
    )


# ── Risk Scenarios (FR-12 enhancement) ──────────────────────────────
# Concrete attack stories per finding -- makes the demo impactful.

_RISK_SCENARIOS = {
    "ro": {
        "TELNET_OPEN": "Un atacator conectat la reteaua ta WiFi poate intercepta parola de admin a routerului in cateva secunde, deoarece Telnet o trimite necriptat. Odata ce are acces, poate redirectiona tot traficul tau prin serverul lui.",
        "RDP_EXPOSED": "Un atacator poate incerca mii de parole pe minut pentru a ghici accesul la desktopul tau. Odata intrat, vede tot ce ai pe ecran, poate copia fisiere si instala programe.",
        "VNC_EXPOSED": "Un atacator poate vedea in timp real tot ce faci pe ecran -- inclusiv cand tastezi parole sau citesti emailuri. Practic, se uita peste umarul tau digital.",
        "DB_EXPOSED": "Un atacator poate accesa direct baza de date si citi, modifica sau sterge toate informatiile stocate -- conturi de utilizatori, date personale, tot.",
        "CAMERA_STREAM_EXPOSED": "Oricine conectat la reteaua ta WiFi poate vedea live ce filmeaza camera ta de supraveghere. Un vecin sau un vizitator cu parola WiFi poate urmari totul.",
        "OUTDATED_SERVICE": "Versiunea veche a acestui software are vulnerabilitati publice. Un atacator poate gasi exploit-ul pe internet si poate prelua controlul dispozitivului in cateva minute.",
        "FTP_CLEARTEXT": "Cand transferi fisiere prin FTP, un atacator din retea poate vedea continutul fisierelor si parola ta. E ca si cum ai trimite corespondenta fara plic.",
        "HTTP_ADMIN_CLEARTEXT": "Cand te autentifici in panoul de administrare, parola ta circula necriptata prin retea. Un atacator o poate captura si preia controlul dispozitivului.",
        "SMB_EXPOSED": "Un atacator din retea poate naviga prin fisierele partajate de pe acest dispozitiv. Daca nu sunt protejate cu parola, poate copia sau sterge orice.",
        "MQTT_EXPOSED": "Un atacator poate trimite comenzi dispozitivelor tale smart home -- poate aprinde/stinge lumini, deschide incuietori inteligente sau opri alarma.",
        "UPNP_EXPOSED": "Un program malitios de pe orice dispozitiv din retea poate deschide automat porturi pe router, expunand servicii interne catre internet fara sa stii.",
        "SNMP_EXPOSED": "Un atacator poate citi configurarea completa a dispozitivului si, cu acces de scriere, poate schimba setarile routerului -- inclusiv serverele DNS.",
        "PRINTER_RAW_EXPOSED": "Un atacator poate trimite documente la imprimanta ta, poate citi ce printezi sau chiar poate schimba firmware-ul imprimantei.",
        "UNKNOWN_DEVICE": "Un dispozitiv necunoscut pe reteaua ta poate fi al unui vecin care ti-a ghicit parola WiFi sau un dispozitiv compromis care colecteaza date.",
        "SSH_OPEN": "SSH e criptat, dar daca parola e slaba, un atacator poate incerca automat mii de combinatii. Recomandam chei SSH in loc de parola.",
    },
    "en": {
        "TELNET_OPEN": "An attacker on your WiFi can intercept your router's admin password in seconds because Telnet sends it unencrypted. Once they have access, they can redirect all your traffic through their server.",
        "RDP_EXPOSED": "An attacker can try thousands of passwords per minute to guess access to your desktop. Once in, they can see everything on your screen, copy files, and install software.",
        "VNC_EXPOSED": "An attacker can watch in real-time everything you do on screen -- including when you type passwords or read emails. They're essentially looking over your digital shoulder.",
        "DB_EXPOSED": "An attacker can directly access the database and read, modify, or delete all stored information -- user accounts, personal data, everything.",
        "CAMERA_STREAM_EXPOSED": "Anyone connected to your WiFi can watch the live feed from your security camera. A neighbor or guest with the WiFi password can watch everything.",
        "OUTDATED_SERVICE": "This old software version has publicly known vulnerabilities. An attacker can find the exploit online and take control of the device in minutes.",
        "FTP_CLEARTEXT": "When you transfer files via FTP, an attacker on the network can see file contents and your password. It's like sending mail without an envelope.",
        "HTTP_ADMIN_CLEARTEXT": "When you log into the admin panel, your password travels unencrypted across the network. An attacker can capture it and take control of the device.",
        "SMB_EXPOSED": "An attacker on the network can browse files shared from this device. If they're not password-protected, anyone can copy or delete anything.",
        "MQTT_EXPOSED": "An attacker can send commands to your smart home devices -- turning lights on/off, unlocking smart locks, or disabling your alarm.",
        "UPNP_EXPOSED": "Malicious software on any device in your network can automatically open ports on your router, exposing internal services to the internet without you knowing.",
        "SNMP_EXPOSED": "An attacker can read the complete device configuration and, with write access, change router settings -- including DNS servers.",
        "PRINTER_RAW_EXPOSED": "An attacker can send documents to your printer, read what you're printing, or even change the printer's firmware.",
        "UNKNOWN_DEVICE": "An unknown device on your network could be a neighbor who guessed your WiFi password or a compromised device collecting data.",
        "SSH_OPEN": "SSH is encrypted, but if the password is weak, an attacker can automatically try thousands of combinations. We recommend SSH keys instead of passwords.",
    },
}


def get_risk_scenario(finding_code: str, language: str = "ro") -> str:
    lang = language if language in _RISK_SCENARIOS else "ro"
    return _RISK_SCENARIOS[lang].get(finding_code, "")


# ── Scan Narrator (FR-12 enhancement) ───────────────────────────────

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}
_SEVERITY_LABEL = {
    "ro": {"high": "critica", "medium": "medie", "low": "mica", "info": "informativa"},
    "en": {"high": "critical", "medium": "medium", "low": "low", "info": "informational"},
}
_DEVICE_LABEL = {
    "ro": {"router": "router", "camera": "camera de supraveghere", "printer": "imprimanta",
           "smart_home": "dispozitiv smart home", "server": "server", "nas": "NAS",
           "phone": "telefon", "computer": "calculator", "unknown": "dispozitiv necunoscut"},
    "en": {"router": "router", "camera": "security camera", "printer": "printer",
           "smart_home": "smart home device", "server": "server", "nas": "NAS",
           "phone": "phone", "computer": "computer", "unknown": "unknown device"},
}


def narrate_scan(scan_data: dict, language: str = "ro") -> dict:
    """Generate a narrative summary of the scan in plain language."""
    devices = scan_data.get("devices", [])
    score = scan_data.get("score", "?")
    n_devices = len(devices)

    all_findings = []
    for d in devices:
        for f in d.get("findings", []):
            f_copy = dict(f)
            f_copy["device_ip"] = d.get("ip", "?")
            f_copy["device_type"] = d.get("type", "unknown")
            f_copy["device_vendor"] = d.get("vendor", "")
            all_findings.append(f_copy)

    all_findings.sort(key=lambda f: _SEVERITY_ORDER.get(f.get("severity", "info"), 9))
    n_findings = len(all_findings)
    high_count = sum(1 for f in all_findings if f.get("severity") == "high")
    medium_count = sum(1 for f in all_findings if f.get("severity") == "medium")

    dev_labels = _DEVICE_LABEL.get(language, _DEVICE_LABEL["ro"])
    sev_labels = _SEVERITY_LABEL.get(language, _SEVERITY_LABEL["ro"])

    if language == "ro":
        parts = []
        parts.append(f"Reteaua ta are {n_devices} dispozitiv{'e' if n_devices != 1 else ''} si un scor de securitate de {score}/100.")

        if n_findings == 0:
            parts.append("Felicitari! Nu am gasit nicio problema de securitate. Reteaua ta este curata.")
        else:
            parts.append(f"Am gasit {n_findings} problem{'e' if n_findings != 1 else 'a'} de securitate"
                         f"{f' ({high_count} critic{"e" if high_count != 1 else "a"})' if high_count else ''}.")

            if high_count > 0:
                parts.append("\nCele mai grave probleme:")
                for f in all_findings:
                    if f.get("severity") != "high":
                        break
                    dev_type = dev_labels.get(f["device_type"], f["device_type"])
                    tmpl = get_template(f.get("code", ""), language)
                    expl = tmpl["explanation"] if tmpl else f.get("code", "")
                    parts.append(f"  - {dev_type} ({f['device_ip']}): {expl}")

            if medium_count > 0:
                parts.append(f"\nSi {medium_count} problem{'e' if medium_count != 1 else 'a'} de severitate medie.")

            top = all_findings[0]
            parts.append(f"\nRecomandare: incepe cu {top.get('code', '?')} pe {top['device_ip']} -- aceasta e cea mai urgenta.")
    else:
        parts = []
        parts.append(f"Your network has {n_devices} device{'s' if n_devices != 1 else ''} and a security score of {score}/100.")

        if n_findings == 0:
            parts.append("Congratulations! No security issues found. Your network is clean.")
        else:
            parts.append(f"We found {n_findings} security issue{'s' if n_findings != 1 else ''}"
                         f"{f' ({high_count} critical)' if high_count else ''}.")

            if high_count > 0:
                parts.append("\nMost serious issues:")
                for f in all_findings:
                    if f.get("severity") != "high":
                        break
                    dev_type = dev_labels.get(f["device_type"], f["device_type"])
                    tmpl = get_template(f.get("code", ""), language)
                    expl = tmpl["explanation"] if tmpl else f.get("code", "")
                    parts.append(f"  - {dev_type} ({f['device_ip']}): {expl}")

            if medium_count > 0:
                parts.append(f"\nPlus {medium_count} medium-severity issue{'s' if medium_count != 1 else ''}.")

            top = all_findings[0]
            parts.append(f"\nRecommendation: start with {top.get('code', '?')} on {top['device_ip']} -- this is the most urgent.")

    return {
        "narrative": "\n".join(parts),
        "total_devices": n_devices,
        "total_findings": n_findings,
        "high_count": high_count,
        "medium_count": medium_count,
        "score": score,
    }


# ── Smart Follow-ups (FR-12 enhancement) ────────────────────────────

_FOLLOWUP_TEMPLATES = {
    "ro": {
        "TELNET_OPEN": [
            "Cum dezactivez Telnet pe {vendor}?",
            "Ce alternativa sigura am in loc de Telnet?",
        ],
        "RDP_EXPOSED": [
            "Cum dezactivez Remote Desktop pe {ip}?",
            "Ce e un VPN si cum ma ajuta?",
        ],
        "VNC_EXPOSED": [
            "Cum opresc VNC pe {ip}?",
            "Cum setez o parola puternica pe VNC?",
        ],
        "DB_EXPOSED": [
            "Cum restricionez accesul la baza de date doar local?",
            "Ce date sunt stocate in aceasta baza de date?",
        ],
        "CAMERA_STREAM_EXPOSED": [
            "Cum pun parola pe camera {vendor}?",
            "Poate cineva vedea camera mea de pe internet?",
        ],
        "OUTDATED_SERVICE": [
            "Cum actualizez firmware-ul pe {vendor}?",
            "Ce riscuri am daca nu actualizez?",
        ],
        "FTP_CLEARTEXT": [
            "Cum inlocuiesc FTP cu SFTP?",
            "Cum dezactivez FTP pe {vendor}?",
        ],
        "HTTP_ADMIN_CLEARTEXT": [
            "Cum activez HTTPS pe {vendor}?",
            "Ce parola ar trebui sa pun pe router?",
        ],
        "SMB_EXPOSED": [
            "Cum dezactivez partajarea de fisiere pe {ip}?",
            "Cum verific ce foldere sunt partajate?",
        ],
        "MQTT_EXPOSED": [
            "Cum pun parola pe MQTT?",
            "Ce dispozitive smart home folosesc MQTT?",
        ],
        "UPNP_EXPOSED": [
            "Cum dezactivez UPnP pe router?",
            "Ce se strica daca opresc UPnP?",
        ],
        "SNMP_EXPOSED": [
            "Cum dezactivez SNMP pe {vendor}?",
            "Ce informatii expune SNMP?",
        ],
        "PRINTER_RAW_EXPOSED": [
            "Cum securizez imprimanta {vendor}?",
            "Poate cineva printa pe imprimanta mea fara permisiune?",
        ],
        "UNKNOWN_DEVICE": [
            "Cum aflu ce este acest dispozitiv necunoscut?",
            "Cum schimb parola WiFi ca sa il deconectez?",
        ],
        "SSH_OPEN": [
            "Cum trec de la parola la chei SSH?",
            "Trebuie sa am SSH activ pe {ip}?",
        ],
    },
    "en": {
        "TELNET_OPEN": [
            "How do I disable Telnet on {vendor}?",
            "What secure alternative can I use instead of Telnet?",
        ],
        "RDP_EXPOSED": [
            "How do I disable Remote Desktop on {ip}?",
            "What is a VPN and how does it help?",
        ],
        "VNC_EXPOSED": [
            "How do I stop VNC on {ip}?",
            "How do I set a strong VNC password?",
        ],
        "DB_EXPOSED": [
            "How do I restrict database access to localhost only?",
            "What data is stored in this database?",
        ],
        "CAMERA_STREAM_EXPOSED": [
            "How do I set a password on my {vendor} camera?",
            "Can someone see my camera from the internet?",
        ],
        "OUTDATED_SERVICE": [
            "How do I update the firmware on {vendor}?",
            "What are the risks if I don't update?",
        ],
        "FTP_CLEARTEXT": [
            "How do I replace FTP with SFTP?",
            "How do I disable FTP on {vendor}?",
        ],
        "HTTP_ADMIN_CLEARTEXT": [
            "How do I enable HTTPS on {vendor}?",
            "What password should I use for my router?",
        ],
        "SMB_EXPOSED": [
            "How do I disable file sharing on {ip}?",
            "How do I check which folders are shared?",
        ],
        "MQTT_EXPOSED": [
            "How do I add a password to MQTT?",
            "Which smart home devices use MQTT?",
        ],
        "UPNP_EXPOSED": [
            "How do I disable UPnP on my router?",
            "What breaks if I turn off UPnP?",
        ],
        "SNMP_EXPOSED": [
            "How do I disable SNMP on {vendor}?",
            "What information does SNMP expose?",
        ],
        "PRINTER_RAW_EXPOSED": [
            "How do I secure my {vendor} printer?",
            "Can someone print on my printer without permission?",
        ],
        "UNKNOWN_DEVICE": [
            "How do I find out what this unknown device is?",
            "How do I change my WiFi password to disconnect it?",
        ],
        "SSH_OPEN": [
            "How do I switch from password to SSH keys?",
            "Do I need SSH active on {ip}?",
        ],
    },
}


def suggest_followups(scan_data: dict, answer_text: str, language: str = "ro") -> list[str]:
    """Suggest 2-3 follow-up questions based on findings mentioned in the answer."""
    lang = language if language in _FOLLOWUP_TEMPLATES else "ro"
    templates = _FOLLOWUP_TEMPLATES[lang]
    suggestions = []

    mentioned = []
    for device in scan_data.get("devices", []):
        for finding in device.get("findings", []):
            code = finding.get("code", "")
            if code and code.lower() in answer_text.lower():
                mentioned.append((code, device.get("ip", "?"), device.get("vendor", "")))

    if not mentioned:
        for device in scan_data.get("devices", []):
            for finding in device.get("findings", []):
                code = finding.get("code", "")
                if code:
                    mentioned.append((code, device.get("ip", "?"), device.get("vendor", "")))

    seen_codes = set()
    for code, ip, vendor in mentioned:
        if code in seen_codes:
            continue
        seen_codes.add(code)
        if code in templates:
            for tmpl in templates[code]:
                q = tmpl.format(ip=ip, vendor=vendor or "dispozitiv" if lang == "ro" else vendor or "device")
                suggestions.append(q)
        if len(suggestions) >= 3:
            break

    general = {
        "ro": "Care e cea mai urgenta problema de rezolvat?",
        "en": "What is the most urgent issue to fix?",
    }
    if len(suggestions) < 2:
        suggestions.append(general[lang])

    return suggestions[:3]


# ── Scan Diff Narration ───────────────────────────────────────────────

def narrate_diff(diff_data: dict, language: str = "ro") -> dict:
    """Generate a narrative summary comparing two scans."""
    old_score = diff_data.get("old_score")
    new_score = diff_data.get("new_score")
    resolved = diff_data.get("resolved_findings", [])
    new_findings = diff_data.get("new_findings", [])
    added = diff_data.get("devices_added", [])
    removed = diff_data.get("devices_removed", [])

    if language == "ro":
        parts = []
        if old_score is not None and new_score is not None:
            delta = new_score - old_score
            if delta > 0:
                parts.append(f"Scorul de securitate a crescut de la {old_score} la {new_score} (+{delta} puncte).")
            elif delta < 0:
                parts.append(f"Scorul de securitate a scazut de la {old_score} la {new_score} ({delta} puncte).")
            else:
                parts.append(f"Scorul de securitate a ramas {new_score}.")

        if resolved:
            parts.append(f"\n{len(resolved)} problem{'e rezolvate' if len(resolved) != 1 else 'a rezolvata'}:")
            for f in resolved:
                parts.append(f"  - {f['finding_code']} pe {f['ip']} (port {f['port']})")

        if new_findings:
            parts.append(f"\n{len(new_findings)} problem{'e noi' if len(new_findings) != 1 else 'a noua'}:")
            for f in new_findings:
                parts.append(f"  - {f['finding_code']} pe {f['ip']} (port {f['port']})")

        if added:
            parts.append(f"\n{len(added)} dispozitiv{'e noi' if len(added) != 1 else ' nou'}: {', '.join(added)}")
        if removed:
            parts.append(f"\n{len(removed)} dispozitiv{'e disparute' if len(removed) != 1 else ' disparut'}: {', '.join(removed)}")

        if not resolved and not new_findings and not added and not removed:
            parts.append("Nicio schimbare detectata fata de scanul anterior.")
    else:
        parts = []
        if old_score is not None and new_score is not None:
            delta = new_score - old_score
            if delta > 0:
                parts.append(f"Security score improved from {old_score} to {new_score} (+{delta} points).")
            elif delta < 0:
                parts.append(f"Security score dropped from {old_score} to {new_score} ({delta} points).")
            else:
                parts.append(f"Security score remained at {new_score}.")

        if resolved:
            parts.append(f"\n{len(resolved)} resolved issue{'s' if len(resolved) != 1 else ''}:")
            for f in resolved:
                parts.append(f"  - {f['finding_code']} on {f['ip']} (port {f['port']})")

        if new_findings:
            parts.append(f"\n{len(new_findings)} new issue{'s' if len(new_findings) != 1 else ''}:")
            for f in new_findings:
                parts.append(f"  - {f['finding_code']} on {f['ip']} (port {f['port']})")

        if added:
            parts.append(f"\n{len(added)} new device{'s' if len(added) != 1 else ''}: {', '.join(added)}")
        if removed:
            parts.append(f"\n{len(removed)} removed device{'s' if len(removed) != 1 else ''}: {', '.join(removed)}")

        if not resolved and not new_findings and not added and not removed:
            parts.append("No changes detected compared to the previous scan.")

    return {
        "narrative": "\n".join(parts),
        "old_score": old_score,
        "new_score": new_score,
        "resolved_count": len(resolved),
        "new_count": len(new_findings),
        "devices_added_count": len(added),
        "devices_removed_count": len(removed),
    }
