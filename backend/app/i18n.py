"""Romanian / English text for every message the API sends to the UI (NFR-09).

The UI sends its language in the Accept-Language header; a middleware stores it for the
request, and t() answers in that language. Without the header (curl, the CLI) it is English.
"""

from __future__ import annotations

from contextvars import ContextVar

_language: ContextVar[str] = ContextVar("language", default="en")


def set_language(header: str | None):
    return _language.set("ro" if (header or "").strip().lower().startswith("ro") else "en")


def reset_language(token) -> None:
    _language.reset(token)


def current() -> str:
    return _language.get()


MESSAGES: dict[str, tuple[str, str]] = {
    # key: (English, Romanian)
    # uploads and scans
    "xml_only": ("Only .xml files are accepted.", "Sunt acceptate doar fisiere .xml."),
    "file_too_large": ("{name}: file is larger than {mb} MB.", "{name}: fisierul e mai mare de {mb} MB."),
    "no_scans": ("No scans yet. Upload an XML file or run a live scan.",
                 "Nu exista inca niciun scan. Incarca un fisier XML sau scaneaza reteaua."),
    "no_snapshot": ("This scan has no stored details. Upload the file again.",
                    "Pentru acest scan nu sunt salvate detaliile. Incarca fisierul din nou."),
    "scan_not_found": ("Scan not found.", "Scanul nu a fost gasit."),
    "scan_id_not_found": ("Scan {id} not found.", "Scanul {id} nu a fost gasit."),
    "diff_mixed_sources": ("Scan {old} is '{old_source}' and scan {new} is '{new_source}': only scans of the same kind can be compared.",
                           "Scanul {old} e de tip '{old_source}', iar scanul {new} de tip '{new_source}': se pot compara doar scanuri de acelasi tip."),
    "unreadable_not_comparable": ("An unreadable file cannot be compared.", "Un fisier care nu poate fi citit nu poate fi comparat."),
    "no_previous": ("No previous scan to compare against.", "Nu exista un scan anterior cu care sa compar."),
    "device_not_found": ("Device {ip} not found in scan.", "Dispozitivul {ip} nu apare in acest scan."),
    # live scan
    "scan_running": ("A live scan is already running.", "Deja ruleaza o scanare."),
    "scan_failed": ("The scan failed.", "Scanarea nu a reusit."),
    "scan_failed_detail": ("The scan failed: {detail}", "Scanarea nu a reusit: {detail}"),
    "scan_timeout": ("The scan took longer than {seconds} seconds and was stopped.",
                     "Scanarea a durat mai mult de {seconds} de secunde si a fost oprita."),
    "nmap_missing": ("nmap is not installed. Install it from https://nmap.org/download.html",
                     "nmap nu este instalat. Instaleaza-l de pe https://nmap.org/download.html"),
    "nmap_unreadable": ("The scan finished but its result could not be read: {detail}",
                        "Scanarea s-a terminat, dar rezultatul nu a putut fi citit: {detail}"),
    # guardrail (FR-02); keys are guard_<code> from guardrails.validate_scan_target / check_ssid
    "guard_ok": ("{shown} is inside your network and confirmed.", "{shown} face parte din reteaua ta si e confirmat."),
    "guard_invalid_target": ("'{target}' is not a valid target. Use an IPv4 address or subnet, e.g. 10.74.130.0/24.",
                             "'{target}' nu este o tinta valida. Foloseste o adresa IPv4 sau o retea, de ex. 10.74.130.0/24."),
    "guard_public_ip": ("{shown} is a public IP address. Only your own private network may be scanned.",
                        "{shown} este o adresa publica. Ai voie sa scanezi doar reteaua ta privata."),
    "guard_no_network": ("Could not detect the network this laptop is connected to, so live scans are refused. Connect to your hotspot and try again.",
                         "Nu am putut afla la ce retea e conectat laptopul, asa ca scanarea e refuzata. Conecteaza-te la hotspot si incearca din nou."),
    "guard_too_large": ("{net} is too large. Scan at most a /{max_prefix} (256 addresses).",
                        "{net} e prea mare. Poti scana cel mult o retea /{max_prefix} (256 de adrese)."),
    "guard_outside_allowlist": ("{shown} is outside your network. Allowed: {allowed}.",
                                "{shown} nu face parte din reteaua ta. Permis: {allowed}."),
    "guard_not_confirmed": ("Live scans need confirmation: add --confirm (or confirm=true).",
                            "Scanarea are nevoie de confirmarea ta."),
    "guard_no_hotspot": ("This laptop is not on a Wi-Fi network named {prefix}... (your team hotspot). Connect only to the hotspot, then scan.",
                         "Laptopul nu e conectat la o retea Wi-Fi care incepe cu {prefix} (hotspot-ul echipei). Conecteaza-te doar la hotspot, apoi scaneaza."),
    "guard_wrong_wifi": ("This laptop is on the Wi-Fi '{ssid}', not on your team hotspot ({prefix}...). Disconnect from it, connect only to the hotspot, then scan.",
                         "Laptopul e conectat la Wi-Fi-ul '{ssid}', nu la hotspot-ul echipei ({prefix}...). Deconecteaza-te, conecteaza-te doar la hotspot, apoi scaneaza."),
    # fixes
    "no_fix_template": ("No fix is available for {code}.", "Nu exista inca o rezolvare pentru {code}."),
    "fix_not_windows": ("Running fixes is only supported on Windows.", "Rezolvarea automata merge doar pe Windows."),
    "fix_launch_failed": ("Windows could not start PowerShell (code {rc}).", "Windows nu a putut porni PowerShell (cod {rc})."),
    "fix_closed_early": ("No result: the PowerShell window was closed before finishing.",
                         "Niciun rezultat: fereastra PowerShell a fost inchisa inainte sa termine."),
    # fix verification
    "verify_no_finding": ("This problem is not in that scan.", "Problema nu exista in acel scan."),
    "verify_no_port": ("This problem has no port to re-check; run a new full scan instead.",
                       "Problema asta nu are un port de verificat; fa o scanare completa noua."),
    "verify_udp_admin": ("Re-checking a UDP port needs administrator rights: start the backend as administrator, or run a new full scan.",
                         "Verificarea unui port UDP are nevoie de drepturi de administrator: porneste aplicatia ca administrator sau fa o scanare completa noua."),
    "verify_failed": ("The re-check scan failed: {detail}", "Scanarea de verificare a esuat: {detail}"),
    "verify_fixed": ("Fixed: port {port} on {ip} no longer shows this problem. Score {old} -> {new}. Saved in history.",
                     "Rezolvat: portul {port} de pe {ip} nu mai are aceasta problema. Scor {old} -> {new}. Salvat in istoric."),
    "verify_still_open": ("Not fixed yet: port {port} on {ip} still shows this problem. Score stays {old}. Saved in history.",
                          "Inca nerezolvat: portul {port} de pe {ip} are in continuare aceasta problema. Scorul ramane {old}. Salvat in istoric."),
    # settings
    "provider_invalid": ("provider must be 'local' or 'groq'", "furnizorul trebuie sa fie 'local' sau 'groq'"),
}


def t(key: str, **params) -> str:
    en, ro = MESSAGES[key]
    return (ro if current() == "ro" else en).format(**params)


def guard_reason(check: dict) -> str:
    """A guardrail decision's reason in the request's language (the English one stays the fallback)."""
    key = f"guard_{check.get('code')}"
    if key in MESSAGES:
        try:
            return t(key, **check.get("params", {}))
        except KeyError:
            pass
    return check.get("reason", "")
