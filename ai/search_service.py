"""
Web search integration pentru instructiuni specifice per device.
Foloseste DuckDuckGo (gratuit, fara API key).
"""

import html
import logging
import re
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

_MAX_PAGE_BYTES = 400_000
_STOPWORDS = frozenset({
    "cum", "ce", "un", "o", "de", "la", "pe", "si", "in", "cu", "sa", "mai", "este", "care", "pentru",
    "how", "do", "i", "a", "an", "the", "to", "of", "on", "in", "is", "my", "what", "and", "for", "can",
})


# Search engines return little for conversational Romanian, so queries are rewritten as English keywords.
_RO_TO_EN = {
    "restartez": "reboot", "repornesc": "reboot", "restart": "reboot", "resetez": "reset",
    "dezactivez": "disable", "opresc": "disable", "activez": "enable", "pornesc": "enable",
    "schimb": "change", "parola": "password", "parolei": "password", "actualizez": "update",
    "actualizare": "update", "configurez": "configure", "setez": "configure", "setari": "settings",
    "instalez": "install", "securizez": "secure", "conectez": "connect", "imprimanta": "printer",
    "camera": "camera", "retea": "network", "reteaua": "network", "wifi": "wifi", "router": "router",
    "ruterul": "router", "routerul": "router", "actualizez firmware": "firmware update",
}
_QUERY_DROP = _STOPWORDS | {"restartez", "pot", "fac", "imi", "meu", "mea", "tau", "ta", "vreau", "please", "va", "rog"}


def _keyword_query(question):
    words = re.findall(r"[\w.-]+", (question or "").lower())
    out = []
    for w in words:
        if w in _RO_TO_EN:
            out.append(_RO_TO_EN[w])
        elif w not in _QUERY_DROP:
            out.append(w)
    return " ".join(dict.fromkeys(out))


def _ddg(query, max_results):
    from ddgs import DDGS

    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results))


def search_web(query, max_results=4):
    """General DuckDuckGo text search. Tries a keyword rewrite first, then the raw query."""
    query = " ".join((query or "").split())
    if not query:
        return []
    for q in dict.fromkeys([_keyword_query(query), query]):
        if not q:
            continue
        try:
            results = _ddg(q, max_results)
        except Exception as e:
            logger.info("Web search '%s' failed: %s", q, e)
            continue
        if results:
            return [
                {"title": r.get("title", ""), "body": r.get("body", ""), "href": r.get("href", "")}
                for r in results
            ]
    return []


def _keywords(text):
    return [w for w in re.findall(r"[\w-]{3,}", (text or "").lower()) if w not in _STOPWORDS]


def _html_to_text(raw):
    raw = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>|</div>", "\n", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(raw)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if len(line) > 25)


def fetch_page_text(url, question, max_chars=1200):
    """Download a result page and keep only the lines most relevant to the question."""
    if not url or not url.startswith(("http://", "https://")):
        return ""
    try:
        import httpx

        with httpx.Client(timeout=5.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
            r = client.get(url)
        if r.status_code != 200 or "html" not in r.headers.get("content-type", ""):
            return ""
        text = _html_to_text(r.text[:_MAX_PAGE_BYTES])
    except Exception as e:
        logger.info("Page fetch failed for %s: %s", url, e)
        return ""

    kws = _keywords(question)
    scored = []
    for i, line in enumerate(text.splitlines()):
        low = line.lower()
        score = sum(1 for k in kws if k in low)
        if re.match(r"^(step\s*\d|pasul\s*\d|\d+[.)])", low):
            score += 1
        if score:
            scored.append((score, i, line))
    best = sorted(sorted(scored, reverse=True)[:12], key=lambda t: t[1])
    out = "\n".join(line for _, _, line in best)
    return out[:max_chars]


def research(question, max_results=4, pages=2):
    """Search the web and read the top pages. Each result gets a 'page_text' excerpt."""
    results = search_web(question, max_results=max_results)
    if not results:
        return []
    focus = f"{question} {_keyword_query(question)}"
    with ThreadPoolExecutor(max_workers=pages) as pool:
        texts = list(pool.map(lambda r: fetch_page_text(r["href"], focus), results[:pages]))
    for r, t in zip(results, texts):
        r["page_text"] = t
    return results


def search_device_guide(vendor, product, action, max_results=3):
    """
    Cauta pe internet ghiduri specifice pentru un device.

    Args:
        vendor: producatorul (ex: "TP-Link")
        product: produsul/modelul (ex: "Archer C7")
        action: ce vrea sa faca (ex: "disable telnet")
        max_results: cate rezultate sa returneze

    Returns:
        list of dict cu title, body, href
    """
    query = f"{vendor} {product} {action} guide".strip()
    query = " ".join(query.split())  # curata spatii multiple

    try:
        from ddgs import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return [
            {"title": r.get("title", ""), "body": r.get("body", ""), "href": r.get("href", "")}
            for r in results
        ]
    except ImportError:
        logger.warning("duckduckgo-search nu e instalat. Ruleaza: pip install duckduckgo-search")
        return []
    except Exception as e:
        logger.warning("Search error: %s", e)
        return []


def search_cve(software, version, max_results=3):
    """Cauta CVE-uri pentru un software si versiune."""
    query = f"{software} {version} CVE vulnerability"
    return search_device_guide(query, "", "", max_results)


def search_firmware(vendor, product, max_results=3):
    """Cauta firmware updates pentru un device."""
    query = f"{vendor} {product} latest firmware update download"
    return search_device_guide(query, "", "", max_results)


def format_search_results(results):
    """Formateaza rezultatele de search ca text pentru LLM context."""
    if not results:
        return "Nu am gasit rezultate relevante."

    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   {r['body']}")
        if r.get("href"):
            lines.append(f"   Sursa: {r['href']}")
        lines.append("")
    return "\n".join(lines)
