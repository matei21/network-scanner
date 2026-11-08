"""
AI Service cu 2 niveluri de fallback:
  1. Model local (Qwen 2.5 3B Instruct GGUF) -- offline, decent
  2. Template-uri statice -- instant, basic dar corect

Modelul local se descarca automat la prima utilizare (~2.3 GB).
Nu se pune in git -- e in .gitignore.
"""

import json
import logging
import threading
from pathlib import Path

from ai.templates import FINDING_TEMPLATES, get_template

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent.parent / "models"

LOCAL_MODEL_REPO = "Qwen/Qwen2.5-3B-Instruct-GGUF"
LOCAL_MODEL_FILE = "qwen2.5-3b-instruct-q4_k_m.gguf"
LOCAL_MODEL_PATH = MODELS_DIR / LOCAL_MODEL_FILE


def download_local_model():
    """Descarca modelul GGUF de pe HuggingFace daca nu exista."""
    if LOCAL_MODEL_PATH.exists():
        logger.info("Modelul local exista deja: %s", LOCAL_MODEL_PATH)
        return True

    logger.info("Descarc modelul local (%s)...", LOCAL_MODEL_FILE)
    logger.info("Asta dureaza doar prima data (~2.3 GB).")

    try:
        from huggingface_hub import hf_hub_download

        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        hf_hub_download(
            repo_id=LOCAL_MODEL_REPO,
            filename=LOCAL_MODEL_FILE,
            local_dir=str(MODELS_DIR),
        )
        logger.info("Model descarcat cu succes!")
        return True
    except ImportError:
        logger.warning(
            "huggingface_hub nu e instalat. Ruleaza: pip install huggingface-hub"
        )
        return False
    except Exception as e:
        logger.warning("Nu am putut descarca modelul: %s", e)
        return False


class LocalLLM:
    """Client pentru model local GGUF via llama-cpp-python."""

    def __init__(self):
        self._llm = None
        self._lock = threading.Lock()
        # llama.cpp contexts are not safe for concurrent inference.
        self._infer_lock = threading.Lock()

        if not LOCAL_MODEL_PATH.exists():
            logger.warning(
                "Local model not found at %s. AI will use template fallback. "
                "To enable local LLM, run: python -c \"from ai.ai_service import download_local_model; download_local_model()\"",
                LOCAL_MODEL_PATH,
            )
            return

        # Load in a background thread so web requests are never blocked.
        t = threading.Thread(target=self._load_model, daemon=True, name="LocalLLM-loader")
        t.start()

    def _load_model(self):
        try:
            from llama_cpp import Llama
            llm = Llama(model_path=str(LOCAL_MODEL_PATH), n_ctx=4096, n_threads=4, verbose=False)
            with self._lock:
                self._llm = llm
            logger.info("Local LLM (Qwen 2.5 3B) initializat in background.")
        except ImportError:
            logger.warning("llama-cpp-python nu e instalat. Ruleaza: pip install llama-cpp-python")
        except Exception as e:
            logger.warning("Local LLM error la incarcare: %s", e)

    @property
    def available(self):
        with self._lock:
            return self._llm is not None

    def chat(self, system_prompt, user_message, max_tokens=512):
        return self.chat_ex(system_prompt, user_message, max_tokens)[0]

    def chat_ex(self, system_prompt, user_message, max_tokens=512):
        """(text, finish_reason); finish_reason 'length' means the answer was cut by max_tokens."""
        with self._lock:
            llm = self._llm
        if not llm:
            return None, None
        try:
            with self._infer_lock:
                response = llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    max_tokens=max_tokens,
                    temperature=0.2,
                    top_p=0.9,
                    repeat_penalty=1.12,  # small models otherwise loop on the same sentence
                )
            choice = response["choices"][0]
            return choice["message"]["content"], choice.get("finish_reason")
        except Exception as e:
            logger.warning("Local LLM error: %s", e)
            return None, None


_shared_local = None
_shared_local_lock = threading.Lock()


def get_local_llm():
    """One model per process: every assistant shares it instead of loading 2 GB again."""
    global _shared_local
    with _shared_local_lock:
        if _shared_local is None:
            _shared_local = LocalLLM()
        return _shared_local


class AIService:
    """
    Serviciul principal de AI. Incearca in ordine:
    groq (if key) -> local -> template.
    """

    def __init__(self, enable_cloud=False, enable_local=True, groq_api_key=None):
        self.local = get_local_llm() if enable_local else None
        self.groq = None
        if groq_api_key:
            try:
                from ai.groq_client import GroqLLM
                self.groq = GroqLLM(groq_api_key)
            except Exception as e:
                logger.warning("Groq init failed: %s", e)

    @property
    def status(self):
        return {
            "groq": self.groq.available if self.groq else False,
            "local": self.local.available if self.local else False,
            "template": True,
        }

    def chat(self, system_prompt, user_message, finding_code=None, language="ro"):
        """
        Trimite un mesaj la LLM. Incearca groq, local, apoi template.
        Returneaza dict cu 'text' si 'source'.
        """
        # Nivel 0: Groq cloud (if user provided API key)
        if self.groq and self.groq.available:
            result = self.groq.chat(system_prompt, user_message)
            if result:
                return {"text": result, "source": "groq"}

        # Nivel 1: Local
        if self.local and self.local.available:
            result = self.local.chat(system_prompt, user_message)
            if result:
                return {"text": result, "source": "local"}

        # Nivel 3: Template
        if finding_code:
            template = get_template(finding_code, language)
            if template:
                return {
                    "text": template["explanation"],
                    "source": "template",
                }

        return {
            "text": (
                "Nu pot genera un raspuns acum."
                if language == "ro"
                else "Cannot generate a response right now."
            ),
            "source": "unavailable",
        }

    def explain_finding(self, finding_code, device_info, language="ro"):
        """
        Genereaza explicatie personalizata pentru un finding.
        Device_info: dict cu ip, vendor, hostname, type, port, service, version.
        """
        template = get_template(finding_code, language)
        if not template:
            return {"text": "Finding necunoscut.", "source": "error"}

        lang_name = "romana" if language == "ro" else "engleza"

        system_prompt = (
            f"Esti un asistent de securitate pentru retele de casa. "
            f"Raspunde in {lang_name}, simplu, ca pentru o persoana fara cunostinte tehnice. "
            f"Maxim 2 propozitii pentru explicatie. "
            f"NU inventa informatii care nu sunt in datele de mai jos."
        )

        user_msg = (
            f"Explica aceasta problema de securitate:\n\n"
            f"Dispozitiv: {device_info.get('vendor', 'Necunoscut')} "
            f"({device_info.get('type', 'dispozitiv')}) la adresa {device_info.get('ip', '?')}\n"
            f"Hostname: {device_info.get('hostname', 'fara nume')}\n"
            f"Problema: {finding_code}\n"
            f"Port: {device_info.get('port', '?')}\n"
            f"Serviciu: {device_info.get('service', '?')}\n"
            f"Versiune: {device_info.get('version', 'necunoscuta')}\n\n"
            f"Explicatie template (rescrie mai personal): {template['explanation']}"
        )

        result = self.chat(system_prompt, user_msg, finding_code, language)
        result["fix_steps"] = template["fix_steps"]
        result["metaphor"] = template["metaphor"]
        result["cis_control"] = template["cis_control"]
        result["owasp_iot"] = template["owasp_iot"]
        result["severity"] = template["severity"]
        result["points"] = template["points"]
        return result

    def generate_fix_steps(self, finding_code, device_info, language="ro"):
        """Genereaza pasi de remediere personalizati per device."""
        template = get_template(finding_code, language)
        if not template:
            return {"steps": [], "source": "error"}

        lang_name = "romana" if language == "ro" else "engleza"

        system_prompt = (
            f"Esti un asistent de securitate. "
            f"Raspunde in {lang_name}, cu pasi concreti numerotati. "
            f"Scrie ca pentru o persoana fara cunostinte tehnice. "
            f"Maxim 5 pasi. Mentioneaza adresa IP si numele producatorului cand e relevant."
        )

        user_msg = (
            f"Scrie pasii pentru a rezolva aceasta problema:\n\n"
            f"Dispozitiv: {device_info.get('vendor', '?')} la {device_info.get('ip', '?')}\n"
            f"Problema: {finding_code} pe portul {device_info.get('port', '?')}\n"
            f"Serviciu: {device_info.get('service', '?')}\n\n"
            f"Pasi generici (personalizeaza): {json.dumps(template['fix_steps'], ensure_ascii=False)}"
        )

        result = self.chat(system_prompt, user_msg, finding_code, language)
        if result["source"] == "template":
            result["steps"] = template["fix_steps"]
        else:
            result["steps"] = result["text"].split("\n")
        return result


def build_scan_context(scan_data):
    """
    Construieste contextul scanului pentru system prompt-ul chatbot-ului.
    scan_data: dict cu devices, findings, score etc. (din analyzer).
    """
    lines = []
    lines.append(f"Retea scanata: {scan_data.get('subnet', 'necunoscut')}")
    lines.append(f"Scor securitate: {scan_data.get('score', '?')}/100")
    lines.append(f"Data scan: {scan_data.get('scan_date', 'necunoscut')}")
    lines.append("")
    lines.append("DISPOZITIVE GASITE:")
    for device in scan_data.get("devices", []):
        mac_display = device.get("mac_masked", "necunoscut")
        lines.append(
            f"  - {device.get('type_label', 'Dispozitiv')} "
            f"({device.get('ip', '?')})"
        )
        lines.append(f"    Producator: {device.get('vendor', 'necunoscut')}")
        lines.append(f"    Nume: {device.get('hostname', 'fara nume')}")
        lines.append(f"    MAC: {mac_display}")
        ports = device.get("open_ports", [])
        if ports:
            lines.append(f"    Porturi deschise: {', '.join(str(p) for p in ports)}")
        else:
            lines.append("    Porturi deschise: niciun port deschis")
        lines.append("")

    lines.append("PROBLEME GASITE:")
    findings = scan_data.get("findings", [])
    if not findings:
        lines.append("  Nicio problema gasita! Reteaua e curata.")
    for f in findings:
        template = get_template(f["code"])
        explanation = template["explanation"] if template else f["code"]
        lines.append(
            f"  - [{f.get('severity', '?').upper()}] {f['code']} "
            f"pe {f.get('ip', '?')}:{f.get('port', '?')}"
        )
        lines.append(f"    {explanation}")
        lines.append("")

    return "\n".join(lines)


CHATBOT_SYSTEM_PROMPT = """\
Esti un asistent prietenos de securitate pentru retele de casa.
Raspunzi la intrebari despre reteaua utilizatorului DOAR pe baza datelor din scan.

REGULI STRICTE:
- Raspunde DOAR cu informatii din datele scanului de mai jos.
- Daca scanul nu contine informatia necesara, spune clar: "Nu pot raspunde la asta din datele scanului."
- NU inventa porturi, servicii, CVE-uri, numere de telefon sau link-uri.
- Vorbeste simplu, ca si cum ai explica unei persoane de 60 de ani.
- Cand recomanzi o actiune, da pasi concreti.
- Cand utilizatorul intreaba "ce e cel mai periculos", ordoneaza dupa severitate (high > medium > low > info).
- Raspunde in limba in care ti se pune intrebarea (romana sau engleza).

DATELE SCANULUI:
{scan_context}
"""


class Chatbot:
    """Chatbot conversational ancorat pe datele unui scan.

    Uses AgentOrchestrator internally: routes each question to a specialized
    agent (analyzer, explainer, advisor) with a short focused prompt, instead
    of one monolithic prompt.  Falls back to the old single-prompt path if
    the orchestrator import fails.
    """

    def __init__(self, ai_service, scan_data):
        self.ai = ai_service
        self.scan_data = scan_data
        self._orchestrator = None
        try:
            from ai.agents import AgentOrchestrator
            self._orchestrator = AgentOrchestrator(ai_service, scan_data)
        except Exception as e:
            logger.warning("AgentOrchestrator init failed, falling back to monolithic: %s", e)

        # Monolithic fallback (kept for safety)
        self.scan_context = build_scan_context(scan_data)
        self.system_prompt = CHATBOT_SYSTEM_PROMPT.format(
            scan_context=self.scan_context
        )
        self.history = []

    def ask(self, question, language="ro", expert=False, allow_web=False):
        """Pune o intrebare chatbot-ului. Returneaza dict cu text si source."""
        if self._orchestrator:
            return self._orchestrator.ask(question, language, expert, allow_web)

        # Monolithic fallback
        self.history.append({"role": "user", "content": question})
        full_context = self.system_prompt
        if len(self.history) > 1:
            prev = "\n".join(
                f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
                for m in self.history[-6:]
            )
            full_context += f"\n\nISTORIC CONVERSATIE:\n{prev}"
        result = self.ai.chat(full_context, question, language=language)
        self.history.append({"role": "assistant", "content": result["text"]})
        return result

    def reset(self):
        """Sterge istoricul conversatiei."""
        self.history = []
        if self._orchestrator:
            self._orchestrator.reset()
