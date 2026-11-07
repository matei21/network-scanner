"""
AI Service cu 3 niveluri de fallback:
  1. Cloud API (Claude/OpenAI) -- cel mai bun, necesita internet + API key
  2. Model local (Qwen 2.5 3B Instruct GGUF) -- offline, decent
  3. Template-uri statice -- instant, basic dar corect

Modelul local se descarca automat la prima utilizare (~2.3 GB).
Nu se pune in git -- e in .gitignore.
"""

import os
import json
import logging
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


class CloudLLM:
    """Client pentru Claude API (Anthropic)."""

    def __init__(self):
        self.client = None
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            try:
                import anthropic

                self.client = anthropic.Anthropic(api_key=api_key)
                logger.info("Cloud LLM (Claude) initializat.")
            except ImportError:
                logger.warning("anthropic nu e instalat. Ruleaza: pip install anthropic")

    @property
    def available(self):
        return self.client is not None

    def chat(self, system_prompt, user_message, max_tokens=512):
        if not self.available:
            return None
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except Exception as e:
            logger.warning("Cloud LLM error: %s", e)
            return None


class LocalLLM:
    """Client pentru model local GGUF via llama-cpp-python."""

    def __init__(self):
        self.llm = None

        if not LOCAL_MODEL_PATH.exists():
            download_local_model()

        if LOCAL_MODEL_PATH.exists():
            try:
                from llama_cpp import Llama

                self.llm = Llama(
                    model_path=str(LOCAL_MODEL_PATH),
                    n_ctx=4096,
                    n_threads=4,
                    verbose=False,
                )
                logger.info("Local LLM (Qwen 2.5 3B) initializat.")
            except ImportError:
                logger.warning(
                    "llama-cpp-python nu e instalat. "
                    "Ruleaza: pip install llama-cpp-python"
                )
            except Exception as e:
                logger.warning("Local LLM error la incarcare: %s", e)

    @property
    def available(self):
        return self.llm is not None

    def chat(self, system_prompt, user_message, max_tokens=512):
        if not self.available:
            return None
        try:
            response = self.llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning("Local LLM error: %s", e)
            return None


class AIService:
    """
    Serviciul principal de AI. Incearca in ordine:
    cloud -> local -> template.
    """

    def __init__(self, enable_cloud=True, enable_local=True):
        self.cloud = CloudLLM() if enable_cloud else None
        self.local = LocalLLM() if enable_local else None

    @property
    def status(self):
        return {
            "cloud": self.cloud.available if self.cloud else False,
            "local": self.local.available if self.local else False,
            "template": True,
        }

    def chat(self, system_prompt, user_message, finding_code=None, language="ro"):
        """
        Trimite un mesaj la LLM. Incearca cloud, apoi local, apoi template.
        Returneaza dict cu 'text' si 'source'.
        """
        # Nivel 1: Cloud
        if self.cloud and self.cloud.available:
            result = self.cloud.chat(system_prompt, user_message)
            if result:
                return {"text": result, "source": "cloud"}

        # Nivel 2: Local
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
    """Chatbot conversational ancorat pe datele unui scan."""

    def __init__(self, ai_service, scan_data):
        self.ai = ai_service
        self.scan_data = scan_data
        self.scan_context = build_scan_context(scan_data)
        self.system_prompt = CHATBOT_SYSTEM_PROMPT.format(
            scan_context=self.scan_context
        )
        self.history = []

    def ask(self, question, language="ro"):
        """Pune o intrebare chatbot-ului. Returneaza dict cu text si source."""
        self.history.append({"role": "user", "content": question})

        full_context = self.system_prompt
        if len(self.history) > 1:
            prev = "\n".join(
                f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
                for m in self.history[-6:]  # ultimele 3 schimburi
            )
            full_context += f"\n\nISTORIC CONVERSATIE:\n{prev}"

        result = self.ai.chat(full_context, question, language=language)
        self.history.append({"role": "assistant", "content": result["text"]})
        return result

    def reset(self):
        """Sterge istoricul conversatiei."""
        self.history = []
