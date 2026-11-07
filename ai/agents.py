"""
Multi-agent system: 4 specialized agents on a single Qwen 2.5 3B model.

Each agent has a short, focused system prompt (~80-100 tokens).
The orchestrator (Python, no LLM) routes questions to the right agent
and builds grounded context so the model cannot hallucinate.

Agents:
  1. Analyzer  — scan data → structured conclusions
  2. Explainer — one finding → plain-language explanation + metaphor
  3. Search Integrator — DDG results → filtered relevant info
  4. Advisor   — pre-processed context → numbered fix steps
"""

import re
import logging

from ai.templates import FINDING_TEMPLATES, get_template

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
    "parola", "retea", "router", "imprimanta", "camera",
})


def detect_language(text: str) -> str:
    """Detect RO vs EN from user input. Checks diacritics first, then keywords."""
    if _RO_DIACRITICS.search(text):
        return "ro"
    words = set(re.findall(r'\w+', text.lower()))
    ro_hits = len(words & _RO_WORDS)
    if ro_hits >= 2:
        return "ro"
    if ro_hits >= 1 and len(words) <= 5:
        return "ro"
    return "en"


# ── Agent system prompts (short, focused, ~80-100 tokens each) ──────

ANALYZER_PROMPT = {
    "ro": (
        "Esti un analist de securitate pentru retele de casa. "
        "Primesti date structurate dintr-un scan de retea. "
        "Raspunde DOAR cu concluzii bazate pe datele de mai jos. "
        "NU inventa porturi, servicii, CVE-uri sau informatii care nu sunt in date. "
        "Ordoneaza problemele dupa severitate (high > medium > low > info). "
        "Raspunde scurt si clar, in romana."
    ),
    "en": (
        "You are a home network security analyst. "
        "You receive structured data from a network scan. "
        "Answer ONLY with conclusions based on the data below. "
        "Do NOT invent ports, services, CVEs, or information not in the data. "
        "Order issues by severity (high > medium > low > info). "
        "Answer short and clear, in English."
    ),
}

EXPLAINER_PROMPT = {
    "ro": (
        "Esti un profesor care explica probleme de securitate pentru o persoana de 60 de ani. "
        "Primesti UN SINGUR cod de problema si informatii despre dispozitiv. "
        "Raspunde cu:\n"
        "1. O propozitie: ce inseamna problema\n"
        "2. O comparatie din viata reala\n"
        "Maxim 3 propozitii. NU inventa informatii care nu sunt mai jos. "
        "Raspunde in romana."
    ),
    "en": (
        "You are a teacher explaining security issues to a 60-year-old person. "
        "You receive ONE problem code and device information. "
        "Answer with:\n"
        "1. One sentence: what the problem means\n"
        "2. A real-life comparison\n"
        "Maximum 3 sentences. Do NOT invent information not below. "
        "Answer in English."
    ),
}

SEARCH_INTEGRATOR_PROMPT = {
    "ro": (
        "Primesti rezultate de cautare de pe internet despre un dispozitiv de retea. "
        "Extrage DOAR informatiile utile:\n"
        "- Pasi specifici mentionati pentru acest model/producator\n"
        "- Link-uri oficiale de support\n"
        "Ignora reclamele si continutul irelevant. "
        "Daca rezultatele nu sunt relevante pentru problema specifica, raspunde DOAR cu: IRELEVANT\n"
        "Maxim 3 propozitii. Raspunde in romana."
    ),
    "en": (
        "You receive search results from the internet about a network device. "
        "Extract ONLY useful information:\n"
        "- Steps specific to this model/manufacturer\n"
        "- Official support links\n"
        "Ignore ads and irrelevant content. "
        "If results are not relevant to the specific problem, answer ONLY with: IRRELEVANT\n"
        "Maximum 3 sentences. Answer in English."
    ),
}

ADVISOR_PROMPT = {
    "ro": (
        "Esti un tehnician de retea care da instructiuni pas cu pas. "
        "Primesti: problema, dispozitivul, sfaturi generice, si (optional) instructiuni gasite online. "
        "Scrie maxim 5 pasi numerotati. Include adresa IP cand e nevoie. "
        "Foloseste cuvinte simple, ca pentru o persoana fara cunostinte tehnice. "
        "NU inventa meniuri, butoane sau optiuni care nu sunt in informatiile de mai jos. "
        "Raspunde in romana."
    ),
    "en": (
        "You are a network technician giving step-by-step instructions. "
        "You receive: the problem, device info, generic advice, and (optionally) instructions found online. "
        "Write maximum 5 numbered steps. Include the IP address when needed. "
        "Use simple words, for a person with no technical knowledge. "
        "Do NOT invent menus, buttons, or options not in the information below. "
        "Answer in English."
    ),
}


# ── Question routing (Python keywords, no LLM) ──────────────────────

_ROUTE_PATTERNS = {
    "advisor": [
        "rezolv", "fix", "repar", "cum fac", "pasi", "steps", "how to",
        "how do i", "disable", "dezactiv", "activ", "enable", "schimb",
        "change", "opresc", "stop", "securiz", "secure", "protect",
        "protej", "update", "actualiz", "inlocui", "replace", "pornesc",
        "configur", "setez", "set up",
    ],
    "explainer": [
        "ce inseamna", "ce este", "explica", "what is", "what does",
        "explain", "de ce e ", "de ce ", "why", "inseamna", "means",
    ],
    "analyzer": [
        "cate", "how many", "scor", "score", "sumar", "summary",
        "rezumat", "overview", "compara", "compare", "cele mai",
        "most", "top", "worst", "periculos", "dangerous", "grav",
        "urgent", "priorit", "status", "stare", "general", "overall",
    ],
}


def route_question(question: str) -> str:
    """Route a question to the right agent using keyword matching."""
    q = question.lower()
    scores = {"advisor": 0, "explainer": 0, "analyzer": 0}
    for agent, keywords in _ROUTE_PATTERNS.items():
        for kw in keywords:
            if kw in q:
                scores[agent] += 1
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "analyzer"
    return best


# ── Context builders (grounding — each agent gets ONLY what it needs) ─

def _build_analyzer_context(scan_data: dict) -> str:
    """Minimal structured context for the analyzer: devices + findings."""
    lines = [f"Scor securitate: {scan_data.get('score', '?')}/100"]
    devices = scan_data.get("devices", [])
    lines.append(f"Dispozitive gasite: {len(devices)}")
    for d in devices:
        dtype = d.get("type_label_ro", d.get("type", "dispozitiv"))
        vendor = d.get("vendor", "necunoscut")
        lines.append(f"\n  {dtype} ({d.get('ip', '?')}) — {vendor}")
        if d.get("hostname"):
            lines.append(f"    Hostname: {d['hostname']}")
        for f in d.get("findings", []):
            sev = f.get("severity", "?").upper()
            tmpl = get_template(f.get("code", ""), "ro")
            expl = tmpl["explanation"] if tmpl else f.get("code", "?")
            lines.append(f"    [{sev}] {f.get('code', '?')} port {f.get('port', '?')} — {expl}")
    return "\n".join(lines)


def _build_explainer_context(finding_code: str, device_info: dict, lang: str) -> str:
    """One finding + device + template reference for the explainer."""
    template = get_template(finding_code, lang)
    lines = [
        f"Cod problema: {finding_code}",
        f"Dispozitiv: {device_info.get('vendor', '?')} ({device_info.get('type', 'dispozitiv')})",
        f"Adresa IP: {device_info.get('ip', '?')}",
        f"Port: {device_info.get('port', '?')}",
        f"Serviciu: {device_info.get('service', '?')}",
    ]
    if template:
        lines.append(f"\nExplicatie de referinta: {template['explanation']}")
        lines.append(f"Comparatie de referinta: {template['metaphor']}")
    return "\n".join(lines)


def _build_search_context(search_results: list, finding_code: str, device_info: dict) -> str:
    """Raw DDG results + what we're looking for, for the search integrator."""
    lines = [
        f"Cautam instructiuni pentru: {finding_code}",
        f"Dispozitiv: {device_info.get('vendor', '')} {device_info.get('product', '')}".strip(),
        "\nRezultate de pe internet:",
    ]
    for i, r in enumerate(search_results[:3], 1):
        lines.append(f"{i}. {r.get('title', '')}")
        body = r.get("body", "")[:200]
        lines.append(f"   {body}")
        if r.get("href"):
            lines.append(f"   Sursa: {r['href']}")
    return "\n".join(lines)


def _build_advisor_context(finding_code: str, device_info: dict,
                           generic_advice: str, search_summary: str,
                           template_steps: list) -> str:
    """Everything pre-processed for the advisor: device + advice + search + template."""
    lines = [
        f"Problema: {finding_code}",
        f"Dispozitiv: {device_info.get('vendor', '?')} la {device_info.get('ip', '?')}",
        f"Port: {device_info.get('port', '?')}",
        "\nSfaturi generice (valabile pentru orice dispozitiv):",
        generic_advice,
    ]
    is_irrelevant = not search_summary or "IRELEVANT" in search_summary.upper() or "IRRELEVANT" in search_summary.upper()
    if not is_irrelevant:
        lines.append("\nInstructiuni specifice gasite online:")
        lines.append(search_summary)
    if template_steps:
        lines.append("\nPasi de baza (din documentatia noastra):")
        for s in template_steps:
            lines.append(f"  - {s}")
    return "\n".join(lines)


# ── Finding extraction from question ─────────────────────────────────

_KEYWORD_TO_CODE = {
    "telnet": "TELNET_OPEN", "rdp": "RDP_EXPOSED", "vnc": "VNC_EXPOSED",
    "database": "DB_EXPOSED", "baza de date": "DB_EXPOSED", "mysql": "DB_EXPOSED",
    "postgres": "DB_EXPOSED", "redis": "DB_EXPOSED",
    "camera": "CAMERA_STREAM_EXPOSED", "rtsp": "CAMERA_STREAM_EXPOSED",
    "ftp": "FTP_CLEARTEXT",
    "http": "HTTP_ADMIN_CLEARTEXT", "admin": "HTTP_ADMIN_CLEARTEXT", "https": "HTTP_ADMIN_CLEARTEXT",
    "smb": "SMB_EXPOSED", "partajare": "SMB_EXPOSED", "sharing": "SMB_EXPOSED", "samba": "SMB_EXPOSED",
    "mqtt": "MQTT_EXPOSED", "smart home": "MQTT_EXPOSED",
    "upnp": "UPNP_EXPOSED",
    "snmp": "SNMP_EXPOSED",
    "printer": "PRINTER_RAW_EXPOSED", "imprimanta": "PRINTER_RAW_EXPOSED", "9100": "PRINTER_RAW_EXPOSED",
    "necunoscut": "UNKNOWN_DEVICE", "unknown": "UNKNOWN_DEVICE",
    "ssh": "SSH_OPEN",
}

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


def _extract_finding(question: str, scan_data: dict) -> tuple[str | None, dict]:
    """Identify which finding the user is asking about. Returns (code, device_info)."""
    q = question.lower()

    def _device_info(device, finding):
        return {
            "ip": device.get("ip", "?"),
            "vendor": device.get("vendor", ""),
            "type": device.get("type", ""),
            "hostname": device.get("hostname", ""),
            "port": finding.get("port", ""),
            "service": finding.get("service", ""),
            "product": finding.get("product", ""),
        }

    for device in scan_data.get("devices", []):
        for f in device.get("findings", []):
            if f.get("code", "").lower() in q:
                return f["code"], _device_info(device, f)

    for keyword, code in _KEYWORD_TO_CODE.items():
        if keyword in q:
            for device in scan_data.get("devices", []):
                for f in device.get("findings", []):
                    if f.get("code") == code:
                        return code, _device_info(device, f)

    best_code, best_sev, best_info = None, 99, {}
    for device in scan_data.get("devices", []):
        for f in device.get("findings", []):
            s = _SEVERITY_ORDER.get(f.get("severity", "info"), 9)
            if s < best_sev:
                best_sev = s
                best_code = f.get("code")
                best_info = _device_info(device, f)
    return best_code, best_info


# ── Orchestrator ─────────────────────────────────────────────────────

class AgentOrchestrator:
    """Routes questions to specialized agents, all sharing one LLM instance."""

    def __init__(self, llm, scan_data: dict):
        """
        Args:
            llm: a LocalLLM instance (loaded once, shared across agents)
            scan_data: the enriched scan dict (from enrich_scan_data)
        """
        self.llm = llm
        self.scan_data = scan_data
        self.history: list[dict] = []

    def ask(self, question: str, language: str | None = None) -> dict:
        """Route question to the right agent. Always auto-detects language from user text."""
        lang = detect_language(question)
        agent = route_question(question)
        logger.info("Agent routing: %s (lang=%s) for: %s", agent, lang, question[:60])

        self.history.append({"role": "user", "content": question})

        if agent == "analyzer":
            result = self._run_analyzer(question, lang)
        elif agent == "explainer":
            result = self._run_explainer(question, lang)
        elif agent == "advisor":
            result = self._run_advisor(question, lang)
        else:
            result = self._run_analyzer(question, lang)

        self.history.append({"role": "assistant", "content": result["text"]})
        result["agent"] = agent
        result["detected_language"] = lang
        return result

    def detailed_fix(self, finding_code: str, device_info: dict, language: str = "ro") -> dict:
        """Pipeline: DDG → Search Integrator agent → Advisor agent."""
        from ai.search_service import search_device_guide
        from ai.assistant import _code_to_action, _get_generic_advice

        action = _code_to_action(finding_code)
        vendor = device_info.get("vendor", "")
        product = device_info.get("product", "")

        raw_results = search_device_guide(vendor, product, action)

        search_summary = ""
        agents_used = []
        if raw_results:
            ctx = _build_search_context(raw_results, finding_code, device_info)
            integrator = self._call_llm(SEARCH_INTEGRATOR_PROMPT[language], ctx, max_tokens=128, lang=language)
            search_summary = integrator["text"]
            agents_used.append("search_integrator")

        generic_advice = _get_generic_advice(finding_code, language)
        template = get_template(finding_code, language)
        template_steps = template["fix_steps"] if template else []

        advisor_ctx = _build_advisor_context(finding_code, device_info, generic_advice, search_summary, template_steps)
        advisor = self._call_llm(ADVISOR_PROMPT[language], advisor_ctx, max_tokens=256, lang=language)
        agents_used.append("advisor")

        return {
            "text": advisor["text"],
            "source": advisor["source"],
            "search_results": raw_results,
            "search_summary": search_summary,
            "generic_advice": generic_advice,
            "template_steps": template_steps,
            "agents_used": agents_used,
        }

    # ── Agent runners ────────────────────────────────────────────────

    def _run_analyzer(self, question: str, lang: str) -> dict:
        context = _build_analyzer_context(self.scan_data)
        history = self._format_history()
        user_msg = f"{context}\n\n{history}{'Intrebare' if lang == 'ro' else 'Question'}: {question}"
        return self._call_llm(ANALYZER_PROMPT[lang], user_msg, max_tokens=200, lang=lang)

    def _run_explainer(self, question: str, lang: str) -> dict:
        code, device_info = _extract_finding(question, self.scan_data)
        if code:
            context = _build_explainer_context(code, device_info, lang)
        else:
            context = _build_analyzer_context(self.scan_data)
        user_msg = f"{context}\n\n{'Intrebare' if lang == 'ro' else 'Question'}: {question}"
        return self._call_llm(EXPLAINER_PROMPT[lang], user_msg, max_tokens=150, lang=lang)

    def _run_advisor(self, question: str, lang: str) -> dict:
        from ai.assistant import _get_generic_advice

        code, device_info = _extract_finding(question, self.scan_data)
        if code:
            generic = _get_generic_advice(code, lang)
            template = get_template(code, lang)
            steps = template["fix_steps"] if template else []
            context = _build_advisor_context(code, device_info, generic, "", steps)
        else:
            context = _build_analyzer_context(self.scan_data)
        user_msg = f"{context}\n\n{'Intrebare' if lang == 'ro' else 'Question'}: {question}"
        return self._call_llm(ADVISOR_PROMPT[lang], user_msg, max_tokens=256, lang=lang)

    # ── LLM call with template fallback ──────────────────────────────

    def _call_llm(self, system_prompt: str, user_msg: str, max_tokens: int, lang: str) -> dict:
        if self.llm and self.llm.available:
            result = self.llm.chat(system_prompt, user_msg, max_tokens=max_tokens)
            if result:
                return {"text": result, "source": "local"}

        for code in FINDING_TEMPLATES:
            if code.lower() in user_msg.lower():
                template = get_template(code, lang)
                if template:
                    return {"text": template["explanation"], "source": "template"}

        fallback = "Nu pot genera un raspuns acum." if lang == "ro" else "Cannot generate a response right now."
        return {"text": fallback, "source": "unavailable"}

    def _format_history(self) -> str:
        if len(self.history) <= 1:
            return ""
        recent = self.history[-4:]
        lines = [f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}" for m in recent]
        return "Istoric recent:\n" + "\n".join(lines) + "\n\n"

    def reset(self):
        self.history = []
