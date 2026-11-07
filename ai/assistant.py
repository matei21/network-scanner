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

    def __init__(self, scan_data: dict, enable_cloud: bool = True, enable_local: bool = True):
        self.scan_data = scan_data
        self.ai = AIService(enable_cloud=enable_cloud, enable_local=enable_local)
        self.chatbot = Chatbot(self.ai, scan_data)

    def ask(self, question: str, language: str = "ro") -> dict:
        """Pune o intrebare despre scan. Returneaza {text, source}."""
        return self.chatbot.ask(question, language)

    def explain(self, finding_code: str, device_info: dict, language: str = "ro") -> dict:
        """Genereaza explicatie personalizata pentru un finding."""
        return self.ai.explain_finding(finding_code, device_info, language)

    def get_fix(self, finding_code: str, device_info: dict, language: str = "ro") -> dict:
        """Genereaza pasi de remediere personalizati."""
        return self.ai.generate_fix_steps(finding_code, device_info, language)

    def get_detailed_fix(self, finding_code: str, device_info: dict, language: str = "ro") -> dict:
        """Cauta pe internet instructiuni specifice si genereaza fix detaliat."""
        vendor = device_info.get("vendor", "")
        product = device_info.get("product", "")
        action = _code_to_action(finding_code)

        search_results = search_device_guide(vendor, product, action)
        search_text = format_search_results(search_results)

        lang_name = "romana" if language == "ro" else "engleza"
        system_prompt = (
            f"Esti un asistent de securitate. "
            f"Raspunde in {lang_name} cu pasi numerotati, simplu. "
            f"Bazeaza-te pe instructiunile gasite online de mai jos. "
            f"Daca nu sunt relevante, spune-i utilizatorului sa caute "
            f"manualul dispozitivului."
        )

        user_msg = (
            f"Dispozitiv: {vendor} {product} ({device_info.get('ip', '?')})\n"
            f"Problema: {finding_code} pe portul {device_info.get('port', '?')}\n\n"
            f"Instructiuni gasite online:\n{search_text}\n\n"
            f"Scrie pasii de rezolvare."
        )

        result = self.ai.chat(system_prompt, user_msg, finding_code, language)
        result["search_results"] = search_results
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

    return scan_result_dict


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
