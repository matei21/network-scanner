"""Clean and check LLM output before it reaches the user.

Small models cut answers mid-sentence when they hit the token limit, leak markdown and chat-template
tokens, repeat themselves, drift into another language (Qwen sometimes switches to Chinese) or answer
in English when Romanian was asked. Anything that fails these checks is rejected, so the caller falls
back to the next model or to the built-in template text (the brief requires that fallback anyway).
"""

from __future__ import annotations

import re

_ARTIFACTS = re.compile(r"<\|[^|>]{1,40}\|>|^\s*(assistant|asistent|user)\s*:\s*", re.I | re.M)
_CJK = re.compile(r"[぀-ヿ㐀-鿿가-힯]")
_SENTENCE_END = re.compile(r"[.!?…»”\")](\s|$)")

_RO_WORDS = frozenset("si este sunt pentru care din sa nu pe la cu sau daca acest aceasta poti trebuie ta tau tale "
                      "de un o in ca mai fara cand dupa apoi".split())
_EN_WORDS = frozenset("the and is are to for you your this with that can not of on it be if then when after "
                      "an or from by".split())

WRITING_RULES = {
    "ro": (
        "\nReguli de scriere: propozitii complete si corecte gramatical, in limba romana. Adreseaza-te cu 'tu' si "
        "foloseste imperativul (ex: 'Deschide', 'Apasa', 'Verifica'). Nu amesteca engleza cu romana; numele exacte "
        "ale butoanelor din meniu le poti pune intre ghilimele. Fara markdown (fara ** sau #). "
        "Termina fiecare propozitie; daca nu ai loc, scrie mai putin."
    ),
    "en": (
        "\nWriting rules: complete, grammatical sentences in English. Address the user as 'you' with imperative "
        "verbs (e.g. 'Open', 'Click', 'Check'). No markdown (no ** or #). Finish every sentence; if space is short, "
        "write less."
    ),
}


def clean_output(text: str) -> str:
    """Remove chat-template tokens and markdown, collapse blank lines and repeated lines."""
    text = _ARTIFACTS.sub("", text or "")
    text = re.sub(r"\*\*|__", "", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    lines, prev = [], None
    for line in text.splitlines():
        stripped = line.rstrip()
        if stripped and stripped == prev:
            continue  # a model stuck in a loop repeats the same line
        lines.append(stripped)
        prev = stripped
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def trim_incomplete(text: str) -> str:
    """For an answer cut by the token limit: keep it up to the last complete sentence or line."""
    text = (text or "").rstrip()
    if not text or _SENTENCE_END.search(text[-2:] + " "):
        return text
    lines = text.splitlines()
    if len(lines) > 1:
        # numbered steps often have no final period: drop only the unfinished last line
        return "\n".join(lines[:-1]).rstrip()
    ends = [m.end() for m in _SENTENCE_END.finditer(text)]
    if ends and ends[-1] >= len(text) * 0.4:
        return text[: ends[-1]].rstrip()
    return text + "..."


def problem(text: str, lang: str | None) -> str | None:
    """Why this answer should not be shown, or None when it is fine."""
    text = (text or "").strip()
    if len(text) < 25:
        return "too short"
    if _CJK.search(text):
        return "switched to another script"
    lines = [ln.strip().lower() for ln in text.splitlines() if ln.strip()]
    if len(lines) >= 4 and len(set(lines)) / len(lines) < 0.6:
        return "repetitive"
    if lang in ("ro", "en"):
        words = re.findall(r"[a-zăâîșț]+", text.lower())
        ro = sum(w in _RO_WORDS for w in words)
        en = sum(w in _EN_WORDS for w in words)
        if lang == "ro" and en >= 6 and en > 2 * ro:
            return "answered in English instead of Romanian"
        if lang == "en" and ro >= 6 and ro > 2 * en:
            return "answered in Romanian instead of English"
    return None
