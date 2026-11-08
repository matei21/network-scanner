"""
Multi-agent system: specialized roles on one shared LLM (Groq if a key is set, else local Qwen).

The orchestrator is plain Python (no LLM). It decides, per question, which agents run and in
what order, and every agent's output is returned separately so the UI can show who said what.

Agents:
  0. Orchestrator      — classifies the question and picks the pipeline (rules, no LLM)
  1. Analyzer          — scan data -> structured conclusions
  2. Explainer         — one finding -> plain-language explanation + metaphor
  3. Web searcher      — DuckDuckGo + reads the top pages (no LLM)
  4. Search Integrator — search results -> only the facts that answer the question
  5. Advisor           — everything above -> numbered steps
  6. Technical expert  — expert mode only: CIS / OWASP IoT mapping, port, service, fix command

Every agent has a deterministic fallback, so an unavailable LLM never produces an unrelated answer.
"""

import re
import logging

from ai.templates import get_template

logger = logging.getLogger(__name__)


# ── Language detection ───────────────────────────────────────────────

_RO_DIACRITICS = re.compile(r'[ăâîșțĂÂÎȘȚ]')
_RO_WORDS = frozenset({
    "este", "sunt", "care", "pentru", "poate", "trebuie", "foarte",
    "acest", "aceasta", "despre", "retea", "reteaua", "problema",
    "probleme", "dispozitiv", "securitate", "periculos", "cum",
    "cate", "cele", "mai", "din", "sau", "daca", "fac", "rezolv",
    "dezactiv", "ce", "de", "la", "pe", "si", "nu", "da", "am",
    "inseamna", "explica", "spune", "opresc", "activez", "schimb",
    "parola", "router", "imprimanta", "camera", "restartez",
})


def detect_language(text: str) -> str:
    """Detect RO vs EN from user input. Checks diacritics first, then keywords."""
    if _RO_DIACRITICS.search(text):
        return "ro"
    words = set(re.findall(r'\w+', text.lower()))
    ro_hits = len(words & _RO_WORDS)
    if ro_hits >= 2 or (ro_hits >= 1 and len(words) <= 5):
        return "ro"
    return "en"


# ── Agent identity (shown in the UI) ─────────────────────────────────

AGENT_INFO = {
    "orchestrator": {"ro": ("Orchestrator", "decide ce agenti lucreaza"), "en": ("Orchestrator", "decides which agents run")},
    "analyzer": {"ro": ("Analistul", "analizeaza scanul"), "en": ("Analyzer", "analyzes the scan")},
    "explainer": {"ro": ("Traducatorul", "explica pe intelesul tuturor"), "en": ("Explainer", "explains in plain words")},
    "searcher": {"ro": ("Cautatorul web", "cauta pe DuckDuckGo si citeste paginile"), "en": ("Web searcher", "searches DuckDuckGo and reads pages")},
    "query_planner": {"ro": ("Planificatorul de cautare", "reformuleaza cautarea cand rezultatele nu ajung"), "en": ("Search planner", "rewrites the search when results fall short")},
    "search_integrator": {"ro": ("Bibliotecarul", "pastreaza doar informatia utila"), "en": ("Search integrator", "keeps only useful information")},
    "advisor": {"ro": ("Tehnicianul", "scrie pasii de urmat"), "en": ("Advisor", "writes the steps to follow")},
    "technical": {"ro": ("Expertul tehnic", "CIS, OWASP, porturi, comenzi"), "en": ("Technical expert", "CIS, OWASP, ports, commands")},
}


def _step(agent: str, lang: str, text: str, source: str, sources: list | None = None) -> dict:
    name, role = AGENT_INFO[agent].get(lang, AGENT_INFO[agent]["ro"])
    return {"agent": agent, "name": name, "role": role, "text": text.strip(), "source": source, "sources": sources or []}


# ── Agent system prompts (short and focused) ─────────────────────────

ANALYZER_PROMPT = {
    "ro": (
        "Esti un analist de securitate pentru retele de casa. Primesti date dintr-un scan. "
        "Raspunde DOAR cu concluzii bazate pe aceste date: cate dispozitive, cate probleme pe severitate, "
        "top 3 riscuri in ordine (high > medium > low > info) si ce inseamna scorul. "
        "NU inventa porturi, servicii sau CVE-uri. Raspunde in romana."
    ),
    "en": (
        "You are a home network security analyst. You receive data from a scan. "
        "Answer ONLY with conclusions from this data: device count, issues per severity, "
        "top 3 risks in order (high > medium > low > info) and what the score means. "
        "Do NOT invent ports, services or CVEs. Answer in English."
    ),
}

EXPLAINER_PROMPT = {
    "ro": (
        "Esti un profesor care explica o problema de securitate. Primesti problema si informatii de referinta. "
        "Raspunde cu: 1) ce inseamna problema, 2) o comparatie din viata reala, 3) de ce conteaza pentru utilizator. "
        "Maxim 4 propozitii. Foloseste DOAR informatiile primite. Raspunde in romana."
    ),
    "en": (
        "You are a teacher explaining a security issue. You receive the issue and reference information. "
        "Answer with: 1) what the issue means, 2) a real-life comparison, 3) why it matters to the user. "
        "Maximum 4 sentences. Use ONLY the information given. Answer in English."
    ),
}

SEARCH_INTEGRATOR_PROMPT = {
    "ro": (
        "Primesti o intrebare si rezultate de cautare de pe internet (fragmente si text din pagini). "
        "Extrage DOAR informatiile care raspund la intrebare: pasi concreti, nume de meniuri, butoane, setari. "
        "Pastreaza-le fidel, nu inventa nimic. Noteaza sursa ca [1], [2]. "
        "Daca nimic nu raspunde la intrebare, scrie DOAR: IRELEVANT. Maxim 6 randuri. Raspunde in romana."
    ),
    "en": (
        "You receive a question and internet search results (snippets and page text). "
        "Extract ONLY the information that answers the question: concrete steps, menu names, buttons, settings. "
        "Keep it faithful, invent nothing. Cite the source as [1], [2]. "
        "If nothing answers the question, write ONLY: IRRELEVANT. Maximum 6 lines. Answer in English."
    ),
}

QUERY_PLANNER_PROMPT = (
    "You write web search queries. You get a user question (any language), the queries already tried and the "
    "titles they returned, which did NOT answer the question. Write 2 NEW short English search queries "
    "(max 8 words each) that are more likely to find an official guide or a precise answer. Keep brand and model "
    "names exactly. Keep the user's intent EXACTLY: never change the action (e.g. reboot/restart is NOT "
    "factory reset, disable is NOT enable). One query per line, no numbering, no quotes, nothing else."
)

ADVISOR_PROMPT = {
    "ro": (
        "Esti un tehnician de retea care raspunde exact la intrebarea utilizatorului cu pasi de urmat. "
        "Primesti intrebarea si informatii pregatite de alti agenti (din scan, din documentatia noastra sau de pe internet). "
        "Bazeaza-te DOAR pe aceste informatii. NU inventa meniuri, butoane sau optiuni. "
        "ATENTIE: 'restart/repornire' (reboot) NU este 'reset' (revenire la setarile din fabrica, care sterge parola WiFi "
        "si configurarea). Pentru restart nu recomanda tinerea apasata a butonului Reset; daca un pas sterge setarile, "
        "avertizeaza clar. Daca informatiile nu sunt suficiente, spune clar ce nu stii. Raspunde in romana."
    ),
    "en": (
        "You are a network technician who answers the user's exact question with steps to follow. "
        "You receive the question and information prepared by other agents (from the scan, our docs or the internet). "
        "Rely ONLY on this information. Do NOT invent menus, buttons or options. "
        "WARNING: 'restart/reboot' is NOT 'reset' (factory reset, which erases the WiFi password and configuration). "
        "For a restart never recommend holding the Reset button; if a step erases settings, warn clearly. "
        "If the information is not enough, say clearly what you don't know. Answer in English."
    ),
}

# Appended to the final agent's prompt depending on the UI toggle.
# "steps" is for the Advisor; Analyzer/Explainer use "plain" so a summary never turns into fake steps.
STYLE_PLAIN = {
    "simple": {
        "ro": (
            "\nStil: utilizatorul NU este tehnic. Scrie 2-4 propozitii scurte, fara jargon si fara pasi numerotati. "
            "Spune ce inseamna pentru el, nu cum functioneaza tehnic."
        ),
        "en": (
            "\nStyle: the user is NOT technical. Write 2-4 short sentences, no jargon and no numbered steps. "
            "Say what it means for them, not how it works technically."
        ),
    },
    "expert": {
        "ro": (
            "\nStil: utilizatorul este tehnic. Pentru fiecare risc mentioneaza portul si protocolul, vectorul de atac "
            "(ce poate face concret un atacator) si referinta CIS / OWASP IoT din date. Maxim 6 propozitii."
        ),
        "en": (
            "\nStyle: the user is technical. For each risk mention the port and protocol, the attack vector "
            "(what an attacker can concretely do) and the CIS / OWASP IoT reference from the data. Maximum 6 sentences."
        ),
    },
}

STYLE = {
    "simple": {
        "ro": (
            "\nStil: utilizatorul NU este tehnic. Propozitii scurte, fara jargon. "
            "Imparte raspunsul in pasi mici numerotati, cate O SINGURA actiune pe pas "
            "(ex: 'Deschide browserul', 'Scrie 192.168.0.1', 'Apasa Login'). "
            "Daca trebuie sa folosesti un termen tehnic, explica-l in cateva cuvinte. "
            "NU scrie comenzi PowerShell sau de terminal: utilizatorul foloseste butoanele aplicatiei sau panoul dispozitivului. "
            "Maxim 7 pasi."
        ),
        "en": (
            "\nStyle: the user is NOT technical. Short sentences, no jargon. "
            "Split the answer into small numbered steps, ONE action per step "
            "(e.g. 'Open your browser', 'Type 192.168.0.1', 'Click Login'). "
            "If you must use a technical term, explain it in a few words. "
            "Do NOT write PowerShell or terminal commands: the user uses the app's buttons or the device's panel. "
            "Maximum 7 steps."
        ),
    },
    "expert": {
        "ro": (
            "\nStil: utilizatorul este tehnic. Foloseste terminologia corecta (porturi, protocoale, servicii, "
            "firmware) si setarile exacte din informatii. Daca informatiile contin o comanda PowerShell, copiaz-o exact "
            "si spune pe ce dispozitiv se ruleaza: o comanda schimba DOAR calculatorul pe care ruleaza, deci nu "
            "repara un router sau o camera. Incheie cu cum verifici ca problema a disparut (ex: o noua scanare a portului). "
            "Maxim 5 pasi scurti, fara subpasi."
        ),
        "en": (
            "\nStyle: the user is technical. Use correct terminology (ports, protocols, services, firmware) "
            "and the exact settings from the information. If the information contains a PowerShell command, copy it "
            "exactly and say which device it runs on: a command changes ONLY the computer it runs on, so it cannot fix "
            "a router or a camera. End with how to verify the issue is gone (e.g. rescan the port). "
            "Maximum 5 short steps, no sub-steps."
        ),
    },
}


# ── Question classification (Python rules, no LLM) ───────────────────

_ROUTE_PATTERNS = {
    "advisor": [
        "rezolv", "fix", "repar", "cum fac", "cum pot", "cum sa", "cum ", "pasi", "steps", "how to",
        "how do i", "how can", "disable", "dezactiv", "activez", "enable", "schimb",
        "change", "opresc", "stop", "securiz", "secure", "protect", "restart", "reset",
        "protej", "update", "actualiz", "inlocui", "replace", "pornesc", "repornesc",
        "configur", "setez", "set up", "instalez", "install",
    ],
    "explainer": [
        "ce inseamna", "ce este", "ce e ", "explica", "what is", "what does",
        "explain", "de ce", "why", "inseamna", "means", "ce face",
    ],
    "analyzer": [
        "cate", "how many", "scor", "score", "sumar", "summary", "rezumat", "overview",
        "compara", "compare", "cele mai", "most", "top", "worst", "periculos", "dangerous",
        "grav", "urgent", "priorit", "status", "stare", "general", "overall",
    ],
}

# Words that mean "my scanned network" — questions with these are about the scan.
_SCAN_WORDS = (
    "reteaua mea", "retea mea", "reteaua ta", "my network", "scan", "scor", "score", "probleme",
    "problema", "issues", "issue", "findings", "dispozitiv", "device", "periculos", "dangerous",
    "urgent", "rezumat", "summary", "cate", "how many", "risc", "risk",
)

_BRANDS = (
    "tp-link", "tplink", "tp link", "archer", "deco", "asus", "netgear", "orbi", "linksys", "d-link",
    "dlink", "huawei", "zte", "xiaomi", "mikrotik", "ubiquiti", "unifi", "cisco", "hikvision",
    "dahua", "synology", "qnap", "canon", "epson", "brother", "samsung", "sonoff", "tuya",
    "philips", "nest", "echo", "alexa", "fritz", "tenda", "eero", "digi", "rds", "upc",
    "vodafone", "orange", "telekom", "windows", "android", "iphone", "macos", "ubuntu",
)

_KEYWORD_TO_CODE = {
    "telnet": "TELNET_OPEN", "rdp": "RDP_EXPOSED", "remote desktop": "RDP_EXPOSED", "vnc": "VNC_EXPOSED",
    "database": "DB_EXPOSED", "baza de date": "DB_EXPOSED", "mysql": "DB_EXPOSED",
    "postgres": "DB_EXPOSED", "redis": "DB_EXPOSED",
    "camera": "CAMERA_STREAM_EXPOSED", "rtsp": "CAMERA_STREAM_EXPOSED",
    "ftp": "FTP_CLEARTEXT",
    "panou de administrare": "HTTP_ADMIN_CLEARTEXT", "admin panel": "HTTP_ADMIN_CLEARTEXT",
    "smb": "SMB_EXPOSED", "partajare": "SMB_EXPOSED", "file sharing": "SMB_EXPOSED", "samba": "SMB_EXPOSED",
    "mqtt": "MQTT_EXPOSED", "smart home": "MQTT_EXPOSED",
    "upnp": "UPNP_EXPOSED",
    "snmp": "SNMP_EXPOSED",
    "printer": "PRINTER_RAW_EXPOSED", "imprimanta": "PRINTER_RAW_EXPOSED", "9100": "PRINTER_RAW_EXPOSED",
    "necunoscut": "UNKNOWN_DEVICE", "unknown device": "UNKNOWN_DEVICE",
    "ssh": "SSH_OPEN",
    "firmware": "OUTDATED_SERVICE", "outdated": "OUTDATED_SERVICE", "invechit": "OUTDATED_SERVICE",
}

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


def route_question(question: str) -> str | None:
    """Intent from keywords: 'advisor', 'explainer', 'analyzer' or None."""
    q = question.lower() + " "
    scores = {agent: sum(1 for kw in kws if kw in q) for agent, kws in _ROUTE_PATTERNS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else None


def _device_info(device: dict, finding: dict) -> dict:
    return {
        "ip": device.get("ip", "?"),
        "vendor": device.get("vendor", ""),
        "type": device.get("type", ""),
        "hostname": device.get("hostname", ""),
        "port": finding.get("port", ""),
        "service": finding.get("service", ""),
        "product": finding.get("product", ""),
        "severity": finding.get("severity", ""),
    }


def _find_scan_reference(question: str, scan_data: dict) -> tuple[str | None, dict]:
    """The finding the question explicitly refers to (code, keyword or device IP), or (None, {})."""
    q = question.lower()
    devices = scan_data.get("devices", [])

    for device in devices:
        for f in device.get("findings", []):
            if f.get("code", "").lower() in q:
                return f["code"], _device_info(device, f)

    for keyword, code in _KEYWORD_TO_CODE.items():
        if re.search(rf"\b{re.escape(keyword)}\b", q):
            for device in devices:
                for f in device.get("findings", []):
                    if f.get("code") == code:
                        return code, _device_info(device, f)

    for device in devices:
        ip = device.get("ip", "")
        if ip and ip in q and device.get("findings"):
            f = min(device["findings"], key=lambda x: _SEVERITY_ORDER.get(x.get("severity", "info"), 9))
            return f["code"], _device_info(device, f)

    return None, {}


def _most_severe(scan_data: dict) -> tuple[str | None, dict]:
    best = (None, 99, {})
    for device in scan_data.get("devices", []):
        for f in device.get("findings", []):
            s = _SEVERITY_ORDER.get(f.get("severity", "info"), 9)
            if s < best[1]:
                best = (f.get("code"), s, _device_info(device, f))
    return best[0], best[2]


def _mentions_product(question: str) -> bool:
    q = question.lower()
    return any(b in q for b in _BRANDS)


def plan_pipeline(question: str, scan_data: dict, expert: bool, allow_web: bool = False) -> dict:
    """Decide which agents run. Pure Python so it is fast, deterministic and debuggable."""
    q = question.lower()
    intent = route_question(question)
    code, device = _find_scan_reference(question, scan_data)
    product = _mentions_product(question)
    about_scan = any(w in q for w in _SCAN_WORDS)

    # "what is most dangerous / fix the worst" — about the scan without naming a finding
    if not code and about_scan and intent in ("advisor", "explainer") and not product:
        code, device = _most_severe(scan_data)

    # FR-12: answers come from the scan. The web is used only after the user clicks "search online".
    offer_web = False
    if code:
        if intent == "advisor":
            agents = (["searcher", "search_integrator"] if product and allow_web else []) + ["advisor"]
            offer_web = product and not allow_web
        else:
            agents = ["explainer"]
        if expert:
            agents.append("technical")
        kind = "scan_finding"
    elif about_scan and not product:
        agents, kind = ["analyzer"], "scan_summary"
    elif allow_web:
        final = "explainer" if intent == "explainer" else "advisor"
        agents, kind = ["searcher", "search_integrator", final], "web"
    else:
        agents, kind, offer_web = [], "not_in_scan", True

    return {"kind": kind, "intent": intent, "code": code, "device": device, "product": product,
            "agents": agents, "offer_web": offer_web}


# ── Context builders (each agent gets ONLY what it needs) ────────────

def _build_analyzer_context(scan_data: dict, expert: bool = False) -> str:
    lines = [f"Scor securitate: {scan_data.get('score', '?')}/100"]
    weighted = (scan_data.get("custom_risk_score") or {}).get("score")
    if expert and weighted is not None:
        lines.append(f"Scor ponderat (tine cont de tipul dispozitivului si combinatii): {weighted}/100")
    devices = scan_data.get("devices", [])
    lines.append(f"Dispozitive gasite: {len(devices)}")
    for d in devices:
        dtype = d.get("type_label_ro", d.get("type", "dispozitiv"))
        lines.append(f"\n  {dtype} ({d.get('ip', '?')}) — {d.get('vendor', 'necunoscut')}")
        if expert and d.get("open_ports"):
            ports = ", ".join(f"{p.get('port')}/{p.get('protocol', 'tcp')} {p.get('service', '')} {p.get('product', '')} {p.get('version', '')}".strip()
                              for p in d["open_ports"])
            lines.append(f"    Porturi deschise: {ports}")
        for f in d.get("findings", []):
            tmpl = get_template(f.get("code", ""), "ro")
            expl = tmpl["explanation"] if tmpl else f.get("code", "?")
            lines.append(f"    [{f.get('severity', '?').upper()}] {f.get('code', '?')} port {f.get('port', '?')} — {expl}")
            if expert and tmpl:
                lines.append(f"      Dovada: {f.get('evidence', '-')}; {tmpl.get('cis_control', '')}; {tmpl.get('owasp_iot', '')}")
    return "\n".join(lines)


def _build_explainer_context(code: str, device: dict, lang: str, expert: bool = False) -> str:
    from ai.fix_commands import FIX_COMMANDS

    template = get_template(code, lang)
    lines = [
        f"Cod problema: {code}",
        f"Dispozitiv: {device.get('vendor', '?')} ({device.get('type', 'dispozitiv')}) la {device.get('ip', '?')}",
        f"Port: {device.get('port', '?')}" + (f", serviciu {device['service']}" if device.get("service") else ""),
    ]
    if template:
        lines.append(f"Explicatie de referinta: {template['explanation']}")
        lines.append(f"Comparatie de referinta: {template['metaphor']}")
        if expert:
            fix = FIX_COMMANDS.get(code, {})
            if fix.get("expert"):
                lines.append(f"Detaliu tehnic: {fix['expert'][lang]}")
            lines.append(f"Referinte: {template.get('cis_control', '')}; {template.get('owasp_iot', '')}")
    return "\n".join(lines)


def _build_search_context(question: str, results: list) -> str:
    lines = [f"Intrebare: {question}", "", "Rezultate:"]
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r.get('title', '')} ({r.get('href', '')})")
        lines.append(f"    Fragment: {r.get('body', '')[:300]}")
        if r.get("page_text"):
            lines.append(f"    Text din pagina:\n{r['page_text'][:1200]}")
    return "\n".join(lines)[:4500]


def _fix_where(code: str, device: dict, lang: str, expert: bool) -> list[str]:
    """Where the fix happens (this PC vs the device) and, in expert mode, the exact command."""
    from ai.fix_commands import get_fix_command, is_this_pc

    here = is_this_pc(device.get("ip"))
    fix = get_fix_command(code, {"port": device.get("port") or 0}, lang, is_this_pc=here,
                          device_type=device.get("type", ""))
    if not fix:
        return []
    if here:
        lines = ["\nUnde se rezolva: problema e pe ACEST calculator; butonul 'Rezolva automat' din aplicatie ruleaza comanda ca administrator.",
                 f"Ce face reparatia: {fix['local_explanation']}"]
    else:
        lines = [f"\nUnde se rezolva: pe dispozitivul {device.get('ip', '?')} (nu pe acest calculator), din panoul lui sau aplicatia producatorului.",
                 f"Ce trebuie schimbat: {fix['remote_explanation']}",
                 f"Unde se gaseste setarea: {fix['menu_hint']}"]
    if expert:
        lines.append(f"Detaliu tehnic: {fix['explanation_expert']}")
        if fix["command"]:
            target = "pe acest calculator" if here else f"doar daca {device.get('ip', '?')} este un PC Windows, pe acel PC"
            lines.append(f"Comanda PowerShell (admin, ruleaza {target}): {fix['command']}")
    return lines


def _build_advisor_context(question: str, code: str | None, device: dict, generic_advice: str,
                           search_summary: str, template_steps: list, lang: str = "ro", expert: bool = False) -> str:
    lines = [f"Intrebarea utilizatorului: {question}"]
    if code:
        lines += [
            f"\nProblema din scan: {code}",
            f"Dispozitiv: {device.get('vendor', '?')} ({device.get('type', '?')}) la {device.get('ip', '?')}, port {device.get('port', '?')}",
        ]
        lines += _fix_where(code, device, lang, expert)
    if generic_advice:
        lines += ["\nSfaturi generice:", generic_advice]
    if search_summary:
        lines += ["\nInformatii gasite pe internet (de Bibliotecar):", search_summary]
    if template_steps:
        lines.append("\nPasi de baza (documentatia noastra):")
        lines += [f"  - {s}" for s in template_steps]
    return "\n".join(lines)


# ── Technical expert (deterministic: exact references, no hallucination) ─

_OWASP_IOT = {
    1: ("Weak, Guessable, or Hardcoded Passwords", "parole slabe, implicite sau scrise in firmware", "weak, default or hardcoded credentials"),
    2: ("Insecure Network Services", "servicii de retea inutile sau nesigure expuse", "unneeded or insecure network services exposed"),
    3: ("Insecure Ecosystem Interfaces", "interfete web/API/cloud fara autentificare sau criptare corecta", "web/API/cloud interfaces without proper auth or encryption"),
    4: ("Lack of Secure Update Mechanism", "lipsa actualizarilor sigure de firmware", "no secure firmware update mechanism"),
    5: ("Use of Insecure or Outdated Components", "componente software vechi cu vulnerabilitati cunoscute", "old software components with known vulnerabilities"),
    6: ("Insufficient Privacy Protection", "date personale protejate insuficient", "personal data insufficiently protected"),
    7: ("Insecure Data Transfer and Storage", "date transmise sau stocate necriptat", "data sent or stored unencrypted"),
    8: ("Lack of Device Management", "lipsa inventarului si a gestionarii dispozitivelor", "no device inventory or management"),
    9: ("Insecure Default Settings", "setari implicite nesigure lasate active", "insecure default settings left on"),
    10: ("Lack of Physical Hardening", "lipsa protectiei fizice a dispozitivului", "no physical hardening"),
}


_CIS_MEANING = {
    "4": ("configuratie sigura: ce nu e necesar se inchide, setarile implicite se schimba",
          "secure configuration: what isn't needed is closed, defaults are changed"),
    "3": ("protectia datelor: datele sensibile se transmit si se stocheaza criptat",
          "data protection: sensitive data is sent and stored encrypted"),
    "1": ("inventarul dispozitivelor: stii ce e conectat la retea",
          "device inventory: you know what is connected to the network"),
    "2": ("inventarul software: stii ce programe si versiuni ruleaza",
          "software inventory: you know which programs and versions run"),
    "5": ("gestionarea conturilor: fara conturi implicite sau partajate",
          "account management: no default or shared accounts"),
    "6": ("controlul accesului: doar cine trebuie are acces",
          "access control: only those who should have access"),
    "7": ("gestionarea vulnerabilitatilor: actualizari la timp",
          "vulnerability management: timely updates"),
    "12": ("infrastructura de retea: echipamentele de retea sunt securizate si actualizate",
           "network infrastructure: network devices are secured and updated"),
    "13": ("monitorizarea retelei: traficul si accesul sunt urmarite",
           "network monitoring: traffic and access are watched"),
}


def _technical_report(code: str, device: dict, lang: str) -> str:
    from ai.fix_commands import get_fix_command, is_this_pc

    t = get_template(code, lang) or {}
    ro = lang == "ro"
    here = is_this_pc(device.get("ip"))
    fix = get_fix_command(code, {"port": device.get("port") or 0}, lang, is_this_pc=here,
                          device_type=device.get("type", "")) or {}

    lines = [
        f"{'Cod' if ro else 'Code'}: {code} · {'severitate' if ro else 'severity'} {str(t.get('severity', '?')).upper()} "
        f"(-{t.get('points', '?')} {'puncte din scor' if ro else 'score points'})",
        f"{'Tinta' if ro else 'Target'}: {device.get('ip', '?')}:{device.get('port', '?')}"
        + (f" ({device.get('service')})" if device.get("service") else "")
        + (f" — {device.get('vendor')}" if device.get("vendor") else ""),
    ]
    if fix.get("explanation_expert"):
        lines.append(f"{'Vector de atac' if ro else 'Attack vector'}: {fix['explanation_expert']}")
    if t.get("cis_control"):
        m = re.search(r"Control\s+(\d+)", t["cis_control"])
        meaning = _CIS_MEANING.get(m.group(1)) if m else None
        lines.append(f"CIS: {t['cis_control']}" + (f" — {meaning[0] if ro else meaning[1]}." if meaning else "."))
    if t.get("owasp_iot"):
        m = re.search(r"[TI](\d+)", t["owasp_iot"])
        info = _OWASP_IOT.get(int(m.group(1))) if m else None
        lines.append(f"OWASP IoT: {t['owasp_iot']}" + (f" — {info[1] if ro else info[2]}." if info else "."))

    if fix.get("command"):
        if here:
            where = ("Problema e pe ACEST calculator: butonul 'Rezolva automat' ruleaza comanda de mai jos ca administrator."
                     if ro else "The issue is on THIS computer: the 'Auto-fix' button runs the command below as administrator.")
        else:
            where = (f"Problema e pe {device.get('ip', '?')}, nu pe acest calculator. Comanda de mai jos ajuta doar daca acel "
                     f"dispozitiv e un PC Windows si o rulezi pe el; pentru router/camera foloseste panoul ({fix.get('menu_hint', '')})."
                     if ro else f"The issue is on {device.get('ip', '?')}, not this computer. The command below only helps if that "
                     f"device is a Windows PC and you run it there; for a router/camera use its panel ({fix.get('menu_hint', '')}).")
        lines.append(where)
        lines.append(f"{'Comanda PowerShell (admin)' if ro else 'PowerShell command (admin)'}:")
        for i, part in enumerate(fix.get("command_parts", []), 1):
            lines.append(f"  {i}) {part['cmd']}\n     → {part['meaning']}")
    elif fix.get("menu_hint"):
        lines.append(f"{'Remediere din panoul dispozitivului' if ro else 'Fix from the device panel'}: {fix['menu_hint']}")
    if device.get("port"):
        lines.append(("Verificare: dupa remediere, ruleaza o scanare noua; portul " if ro else "Verify: after fixing, run a new scan; port ")
                     + f"{device['port']} " + ("nu ar mai trebui sa apara deschis." if ro else "should no longer show as open."))
    return "\n".join(lines)


def _changes_intent(question: str, query: str) -> bool:
    """A rewritten query must not turn a restart question into a factory-reset one."""
    asked_restart = bool(_RESTART_WORDS.search(question)) and "reset" not in question.lower()
    return asked_restart and bool(re.search(r"\b(factory|hard)?\s*reset\b", query, re.I))


_WEB_NOTICE = {
    "ro": "⚠ Acest raspuns NU vine din scanul tau, ci din surse de pe internet. Verifica sursele inainte sa schimbi ceva.",
    "en": "⚠ This answer does NOT come from your scan but from internet sources. Check the sources before changing anything.",
}

_RESTART_WORDS = re.compile(r"\b(restart\w*|repornes\w*|reporni\w*|reboot\w*)\b", re.I)
_RESET_HOLD = re.compile(r"(reset).{0,80}(\d+\s*(secunde|seconds|sec|s)\b)|(\d+\s*(secunde|seconds)).{0,80}(reset)", re.I | re.S)


def _restart_guard(question: str, answer: str, lang: str) -> str:
    """Rule check: a 'restart' answer that tells the user to hold Reset would wipe their router."""
    if not _RESTART_WORDS.search(question) or not _RESET_HOLD.search(answer):
        return answer
    if lang == "ro":
        warn = (
            "⚠ Atentie: tinerea apasata a butonului Reset cateva secunde NU este o repornire — aduce routerul la "
            "setarile din fabrica si sterge parola WiFi si configurarea.\n"
            "Pentru o repornire sigura: 1. Scoate routerul din priza. 2. Asteapta 30 de secunde. "
            "3. Baga-l la loc si asteapta 2 minute sa porneasca. "
            "(Sau, in pagina de administrare a routerului, cauta butonul 'Reboot' / 'Restart'.)"
        )
    else:
        warn = (
            "⚠ Warning: holding the Reset button for several seconds is NOT a restart — it restores factory "
            "settings and erases your WiFi password and configuration.\n"
            "For a safe restart: 1. Unplug the router. 2. Wait 30 seconds. 3. Plug it back in and wait 2 minutes. "
            "(Or, in the router's admin page, look for the 'Reboot' / 'Restart' button.)"
        )
    label = "Pasii gasiti in surse (atentie, unii reseteaza routerul):" if lang == "ro" else "Steps found in the sources (careful, some reset the router):"
    return f"{warn}\n\n{label}\n{answer}"


# ── Orchestrator ─────────────────────────────────────────────────────

class AgentOrchestrator:
    """Runs the planned agents in sequence on one shared LLM and records each agent's output."""

    def __init__(self, ai_service, scan_data: dict):
        self.ai = ai_service
        self.scan_data = scan_data
        self.history: list[dict] = []

    # Backwards compatible attribute used by older callers.
    @property
    def llm(self):
        return self.ai.local if self.ai else None

    def _llm(self, system_prompt: str, user_msg: str, max_tokens: int,
             lang: str | None = None) -> tuple[str | None, str | None]:
        """Groq first (if selected with a key), then the local model.

        Every answer is cleaned, trimmed back to its last complete sentence when the token limit cut it,
        and rejected if it is too short, repetitive, in the wrong language or in another script; then the
        next model is tried, and finally the caller's built-in template text.
        """
        from ai.text_quality import WRITING_RULES, clean_output, problem, trim_incomplete

        if lang in WRITING_RULES:
            system_prompt += WRITING_RULES[lang]
        for name, client in (("groq", getattr(self.ai, "groq", None)), ("local", getattr(self.ai, "local", None))):
            if not (client and client.available):
                continue
            if hasattr(client, "chat_ex"):
                text, finish = client.chat_ex(system_prompt, user_msg, max_tokens=max_tokens)
            else:
                text, finish = client.chat(system_prompt, user_msg, max_tokens=max_tokens), None
            text = clean_output(text or "")
            if finish == "length":
                text = trim_incomplete(text)
            reason = problem(text, lang)
            if reason:
                logger.info("Rejected %s answer (%s): %r", name, reason, text[:120])
                continue
            return text, name
        return None, None

    def ask(self, question: str, language: str | None = None, expert: bool = False, allow_web: bool = False) -> dict:
        lang = language if language in ("ro", "en") else detect_language(question)
        mode = "expert" if expert else "simple"
        plan = plan_pipeline(question, self.scan_data, expert, allow_web)
        code, device = plan["code"], plan["device"]
        logger.info("Agent plan: %s for: %s", plan["agents"], question[:60])

        steps = [_step("orchestrator", lang, self._describe_plan(plan, lang), "rules")]
        search_results: list = []
        search_summary = ""

        for agent in plan["agents"]:
            if agent == "searcher":
                search_results, search_summary = self._web_research(question, plan, lang, steps)
            elif agent == "search_integrator":
                pass  # runs inside _web_research, which may search a second time
            elif agent == "analyzer":
                self._run_analyzer(question, lang, mode, steps)
            elif agent == "explainer":
                self._run_explainer(question, code, device, search_summary, search_results, lang, mode, steps)
            elif agent == "advisor":
                self._run_advisor(question, code, device, search_summary, search_results, lang, mode, steps)
            elif agent == "technical" and code:
                steps.append(_step("technical", lang, _technical_report(code, device, lang), "rules"))

        if plan["kind"] == "not_in_scan":
            steps.append(_step("orchestrator", lang, self._not_in_scan(lang), "rules"))
        from_web = any(s["agent"] == "searcher" for s in steps)
        final = next((s for s in reversed(steps) if s["agent"] not in ("technical", "orchestrator")), steps[-1])
        if from_web:
            final["text"] = f"{_WEB_NOTICE[lang]}\n\n{final['text']}"
        self.history += [{"role": "user", "content": question}, {"role": "assistant", "content": final["text"]}]
        return {
            "text": final["text"],
            "source": final["source"],
            "agent": final["agent"],
            "agents": steps,
            "offer_web": plan["offer_web"],
            "from_web": from_web,
            "scan_related": plan["kind"] in ("scan_finding", "scan_summary"),
            "finding_code": code,
            "detected_language": lang,
            "search_results": [{"title": r.get("title", ""), "href": r.get("href", "")} for r in search_results],
        }

    def _describe_plan(self, plan: dict, lang: str) -> str:
        names = " → ".join(AGENT_INFO[a][lang][0] for a in plan["agents"])
        if lang == "ro":
            why = {
                "scan_finding": f"Intrebarea e despre problema {plan['code']} din scanul tau.",
                "scan_summary": "Intrebarea e despre starea generala a retelei tale scanate.",
                "web": "Ai cerut o cautare pe internet: raspunsul NU vine din scanul tau.",
                "not_in_scan": "Scanul tau nu contine informatia ceruta, asa ca nu folosesc niciun model AI si nu inventez.",
            }[plan["kind"]]
            if not plan["agents"]:
                return why
            return f"{why} Agenti: {names}."
        why = {
            "scan_finding": f"The question is about {plan['code']} from your scan.",
            "scan_summary": "The question is about the overall state of your scanned network.",
            "web": "You asked for an internet search: the answer does NOT come from your scan.",
            "not_in_scan": "Your scan doesn't contain this information, so no AI model is used and nothing is made up.",
        }[plan["kind"]]
        if not plan["agents"]:
            return why
        return f"{why} Agents: {names}."

    # ── Agent runners (each appends its own step) ───────────────────

    def _not_in_scan(self, lang: str) -> str:
        devices = self.scan_data.get("devices", [])
        n_find = sum(len(d.get("findings", [])) for d in devices)
        if lang == "ro":
            return (
                "Nu pot raspunde la asta din scanul tau. Scanul arata doar ce se vede din retea: "
                f"{len(devices)} dispozitive, porturile lor deschise si {n_find} probleme de securitate. "
                "Nu contine parole, setari din interiorul dispozitivelor sau vulnerabilitati (CVE) care nu au fost detectate.\n"
                "Daca vrei, apasa 'Cauta pe internet'. Raspunsul va fi marcat clar ca NU provine din scanul tau."
            )
        return (
            "I can't answer this from your scan. The scan only shows what is visible on the network: "
            f"{len(devices)} devices, their open ports and {n_find} security issues. "
            "It contains no passwords, settings inside the devices, or vulnerabilities (CVEs) that were not detected.\n"
            "If you want, press 'Search online'. The answer will be clearly marked as NOT coming from your scan."
        )

    def _searcher_step(self, results: list, queries: list, lang: str, steps: list, round_no: int) -> None:
        sources = [{"title": r.get("title", ""), "href": r.get("href", "")} for r in results]
        read = sum(1 for r in results if r.get("page_text"))
        shown = ", ".join(f"«{q}»" for q in queries)
        prefix = (f"Runda {round_no}. " if lang == "ro" else f"Round {round_no}. ") if round_no > 1 else ""
        if results:
            text = (f"{prefix}Am cautat {shown}. Am gasit {len(results)} rezultate si am citit {read} pagini." if lang == "ro"
                    else f"{prefix}Searched {shown}. Found {len(results)} results and read {read} pages.")
        else:
            text = (f"{prefix}Am cautat {shown}, dar nu am gasit rezultate (fara internet sau cautarea a esuat)." if lang == "ro"
                    else f"{prefix}Searched {shown} but found nothing (offline or the search failed).")
        steps.append(_step("searcher", lang, text, "web", sources))

    # Small models often say "the results don't answer this" in prose instead of the IRELEVANT marker.
    _NOT_ANSWERED = re.compile(
        r"nu (ofera|contin|raspund|mentioneaz|exista|am gasit)|nu s-a mentionat|nu sunt relevante|nicio informatie|"
        r"do(es)? not (provide|contain|answer|mention|include)|don't (provide|contain|answer|mention)|"
        r"no (specific|relevant|concrete) (information|steps)|not (relevant|mentioned)",
        re.I,
    )

    @classmethod
    def _enough(cls, summary: str, results: list) -> bool:
        text = (summary or "").strip()
        head = text[:220]  # the verdict is in the first sentence; later "not" phrases may be part of real steps
        return bool(results) and len(text) >= 80 and not cls._NOT_ANSWERED.search(head)

    def _plan_queries(self, question: str, tried: list, results: list, lang: str, steps: list) -> list:
        """Search planner agent: new queries when round 1 didn't answer the question."""
        from ai.search_service import _keyword_query, brand_domain

        tried_low = {t.lower() for t in tried}
        titles = "\n".join(f"- {r.get('title', '')}" for r in results[:5]) or "- (none)"
        user = (f"Question: {question}\nKey words (keep this intent): {_keyword_query(question)}\nQueries tried:\n"
                + "\n".join(f"- {q}" for q in tried)
                + f"\nTitles returned:\n{titles}")
        text, source = self._llm(QUERY_PLANNER_PROMPT, user, 80)
        queries = []
        for line in (text or "").splitlines():
            q = re.sub(r"^[\s\-*\d.)\"']+|[\"']+$", "", line).strip()
            if 3 <= len(q) <= 90 and q.lower() not in tried_low and not _changes_intent(question, q):
                queries.append(q)
        if not queries:
            kw = _keyword_query(question) or question
            domain = brand_domain(question)
            candidates = [f"{kw} how to step by step", f"{kw} official support"]
            if domain:
                candidates.append(f"{kw} manual site:{domain}")
            queries, source = [c for c in candidates if c.lower() not in tried_low], "rules"
        queries = queries[:2]
        if queries:
            msg = ("Rezultatele nu au raspuns la intrebare, asa ca reformulez cautarea: " if lang == "ro"
                   else "The results didn't answer the question, so I'm rewriting the search: ")
            steps.append(_step("query_planner", lang, msg + ", ".join(f"«{q}»" for q in queries), source or "rules"))
        return queries

    def _web_research(self, question: str, plan: dict, lang: str, steps: list) -> tuple[list, str]:
        """Round 1: fast keyword + official-site queries. If the Librarian finds no real answer,
        the Search planner rewrites the queries and round 2 searches pages not seen yet."""
        from ai.search_service import research_with_queries
        from ai.assistant import _code_to_action

        base = f"{question} {_code_to_action(plan['code'])}" if plan.get("code") else question
        results, queries = research_with_queries(base)
        self._searcher_step(results, queries, lang, steps, 1)
        summary = self._run_integrator(question, results, lang, steps)
        if self._enough(summary, results):
            return results, summary

        new_queries = self._plan_queries(question, queries, results, lang, steps)
        if not new_queries:
            return results, summary
        results2, _ = research_with_queries(base, queries=new_queries, exclude={r["href"] for r in results})
        self._searcher_step(results2, new_queries, lang, steps, 2)
        summary2 = self._run_integrator(question, results2, lang, steps) if results2 else ""
        if summary2:
            return results2, summary2
        return results + results2, summary

    def _run_integrator(self, question: str, results: list, lang: str, steps: list) -> str:
        if not results:
            return ""
        text, source = self._llm(SEARCH_INTEGRATOR_PROMPT[lang], _build_search_context(question, results), 450, lang)
        if text:
            # Small models sometimes append the "nothing relevant" marker after a useful answer.
            kept = [ln for ln in text.splitlines() if not re.fullmatch(r"\W*(IRELEVANT|IRRELEVANT)\W*", ln.strip(), re.I)]
            text = "\n".join(kept).strip() or "IRELEVANT"
        if text and re.fullmatch(r"\W*(IRELEVANT|IRRELEVANT)\W*", text.strip(), re.I):
            steps.append(_step("search_integrator", lang,
                               "Rezultatele nu raspund la intrebare." if lang == "ro" else "The results don't answer the question.",
                               source))
            return ""
        if not text:
            text, source = self._snippet_digest(results), "web"
        steps.append(_step("search_integrator", lang, text, source,
                           [{"title": r.get("title", ""), "href": r.get("href", "")} for r in results]))
        return text

    def _run_analyzer(self, question: str, lang: str, mode: str, steps: list) -> None:
        context = _build_analyzer_context(self.scan_data, expert=mode == "expert")
        user_msg = f"{context}\n\n{self._format_history()}{'Intrebare' if lang == 'ro' else 'Question'}: {question}"
        text, source = self._llm(ANALYZER_PROMPT[lang] + STYLE_PLAIN[mode][lang], user_msg, 420, lang)
        if not text:
            from ai.assistant import narrate_scan
            text, source = narrate_scan(self.scan_data, lang).get("narrative", ""), "template"
        steps.append(_step("analyzer", lang, text, source))

    def _run_explainer(self, question, code, device, search_summary, results, lang, mode, steps) -> None:
        if code:
            context = _build_explainer_context(code, device, lang, expert=mode == "expert")
        else:
            context = f"Informatii gasite pe internet:\n{search_summary or self._snippet_digest(results)}"
        user_msg = f"{context}\n\n{'Intrebare' if lang == 'ro' else 'Question'}: {question}"
        text, source = (None, None)
        if code or search_summary or results:
            text, source = self._llm(EXPLAINER_PROMPT[lang] + STYLE_PLAIN[mode][lang], user_msg, 320, lang)
        if not text:
            text, source = self._explainer_fallback(code, search_summary, results, lang)
        steps.append(_step("explainer", lang, text, source))

    def _run_advisor(self, question, code, device, search_summary, results, lang, mode, steps) -> None:
        from ai.assistant import _get_generic_advice

        template = get_template(code, lang) if code else None
        template_steps = template["fix_steps"] if template else []
        generic = _get_generic_advice(code, lang) if code else ""
        if not search_summary and results:
            search_summary = self._snippet_digest(results)

        text, source = (None, None)
        if code or search_summary:
            context = _build_advisor_context(question, code, device, generic, search_summary, template_steps,
                                             lang=lang, expert=mode == "expert")
            text, source = self._llm(ADVISOR_PROMPT[lang] + STYLE[mode][lang], context, 600, lang)
        if not text:
            text, source = self._advisor_fallback(template_steps, generic, search_summary, results, lang)
        steps.append(_step("advisor", lang, _restart_guard(question, text, lang), source))

    # ── Deterministic fallbacks (used only when no LLM answers) ─────

    @staticmethod
    def _snippet_digest(results: list) -> str:
        lines = []
        for i, r in enumerate(results[:4], 1):
            body = (r.get("page_text") or r.get("body") or "").strip().replace("\n", " ")
            lines.append(f"[{i}] {r.get('title', '')}: {body[:280]}")
        return "\n".join(lines)

    def _explainer_fallback(self, code, search_summary, results, lang) -> tuple[str, str]:
        template = get_template(code, lang) if code else None
        if template:
            prefix = "Pe scurt: " if lang == "ro" else "In short: "
            return f"{template['explanation']}\n{prefix}{template['metaphor']}", "template"
        if search_summary or results:
            head = "Iata ce am gasit pe internet:" if lang == "ro" else "Here is what I found online:"
            return f"{head}\n{search_summary or self._snippet_digest(results)}", "web"
        return self._no_info(lang), "unavailable"

    def _advisor_fallback(self, template_steps, generic, search_summary, results, lang) -> tuple[str, str]:
        if template_steps:
            text = "\n".join(f"{i}. {s}" for i, s in enumerate(template_steps, 1))
            if generic:
                text += f"\n\n{generic}"
            return text, "template"
        if search_summary or results:
            head = ("Nu am un model AI pornit, dar iata ce spun sursele gasite:" if lang == "ro"
                    else "No AI model is running, but here is what the sources say:")
            return f"{head}\n{search_summary or self._snippet_digest(results)}", "web"
        return self._no_info(lang), "unavailable"

    @staticmethod
    def _no_info(lang: str) -> str:
        if lang == "ro":
            return ("Nu am gasit informatii despre asta in scan sau pe internet. "
                    "Verifica conexiunea la internet sau seteaza o cheie Groq in Setari AI.")
        return ("I couldn't find information about this in the scan or online. "
                "Check your internet connection or set a Groq key in AI Settings.")

    # ── Detailed fix pipeline (used by /assistant/detailed-fix) ─────

    _SEARCH_DEVICE_WORD = {
        "router": "router", "camera": "ip camera", "printer": "printer", "smart_home": "smart home hub",
        "server": "server", "computer": "windows", "smart_tv": "smart tv", "phone": "phone",
    }
    # Web-server names say nothing about the device model, so they would only pollute the search.
    _GENERIC_PRODUCTS = ("lighttpd", "nginx", "apache", "httpd", "mini_httpd", "boa", "goahead", "openssh", "dropbear")

    def detailed_fix(self, finding_code: str, device_info: dict, language: str = "ro", expert: bool = False) -> dict:
        """Pipeline: Web searcher (DDG + page reading) → Search Integrator → Advisor (+ Technical expert)."""
        from ai.assistant import _code_to_action, _get_generic_advice
        from ai.fix_commands import FIX_COMMANDS

        action = FIX_COMMANDS.get(finding_code, {}).get("search") or _code_to_action(finding_code)
        product = device_info.get("product", "")
        if any(g in product.lower() for g in self._GENERIC_PRODUCTS):
            product = ""
        device_word = self._SEARCH_DEVICE_WORD.get(device_info.get("type", ""), "")
        question = " ".join(x for x in (device_info.get("vendor", ""), product, device_word, action) if x)
        mode = "expert" if expert else "simple"

        steps: list = []
        raw_results, search_summary = self._web_research(question, {"code": None}, language, steps)
        generic_advice = _get_generic_advice(finding_code, language)
        template = get_template(finding_code, language)
        template_steps = template["fix_steps"] if template else []

        self._run_advisor(question, finding_code, device_info, search_summary, raw_results, language, mode, steps)
        advisor = steps[-1]
        if expert:
            steps.append(_step("technical", language, _technical_report(finding_code, device_info, language), "rules"))
        return {
            "text": advisor["text"],
            "source": advisor["source"],
            "search_results": raw_results,
            "search_summary": search_summary,
            "generic_advice": generic_advice,
            "template_steps": template_steps,
            "agents_used": [s["agent"] for s in steps],
            "agents": steps,
        }

    def _format_history(self) -> str:
        if not self.history:
            return ""
        recent = self.history[-4:]
        lines = [f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'][:300]}" for m in recent]
        return "Istoric recent:\n" + "\n".join(lines) + "\n\n"

    def reset(self):
        self.history = []
