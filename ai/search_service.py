"""
Web search integration pentru instructiuni specifice per device.
Foloseste DuckDuckGo (gratuit, fara API key).
"""

import html
import logging
import re
import threading
import time
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


_CACHE_TTL = 1800  # seconds; the same question asked twice shouldn't hit the network again
_cache: dict[str, tuple[float, list]] = {}
_cache_lock = threading.Lock()

# Brand word in the question -> the vendor's own site, searched with "site:" for official guides.
_BRAND_DOMAINS = {
    "tp-link": "tp-link.com", "tplink": "tp-link.com", "archer": "tp-link.com", "deco": "tp-link.com",
    "asus": "asus.com", "netgear": "netgear.com", "orbi": "netgear.com", "linksys": "linksys.com",
    "d-link": "dlink.com", "dlink": "dlink.com", "huawei": "huawei.com", "zte": "zte.com.cn",
    "xiaomi": "mi.com", "mikrotik": "mikrotik.com", "ubiquiti": "ui.com", "unifi": "ui.com",
    "tenda": "tendacn.com", "hikvision": "hikvision.com", "dahua": "dahuasecurity.com",
    "synology": "synology.com", "qnap": "qnap.com", "canon": "canon.com", "epson": "epson.com",
    "brother": "brother.com", "hp ": "hp.com", "windows": "microsoft.com", "microsoft": "microsoft.com",
    "fritz": "avm.de", "eero": "eero.com", "raspberry": "raspberrypi.com",
}
_JUNK_DOMAINS = ("youtube.com", "facebook.com", "pinterest.", "tiktok.com", "instagram.com", "quora.com",
                 "amazon.", "ebay.", "aliexpress.", "emag.ro", "olx.")
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
    "Accept-Language": "en-US,en;q=0.9,ro;q=0.8",
}


def _ddg(query, max_results):
    from ddgs import DDGS

    key = f"{max_results}|{query.lower()}"
    with _cache_lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < _CACHE_TTL:
            return hit[1]
    with DDGS(timeout=6) as ddgs:
        results = [
            {"title": r.get("title", ""), "body": r.get("body", ""), "href": r.get("href", "")}
            for r in ddgs.text(query, max_results=max_results)
        ]
    with _cache_lock:
        _cache[key] = (time.time(), results)
    return results


def _safe_ddg(query, max_results):
    try:
        return _ddg(query, max_results)
    except Exception as e:
        logger.info("Web search '%s' failed: %s", query, e)
        # Remember the failure for 5 minutes so a dead query isn't retried on every question.
        with _cache_lock:
            _cache[f"{max_results}|{query.lower()}"] = (time.time() - _CACHE_TTL + 300, [])
        return []


def brand_domain(text):
    low = f" {(text or '').lower()} "
    return next((d for word, d in _BRAND_DOMAINS.items() if word in low), None)


def query_variants(question):
    """Fast first-round queries: English keywords, plus the vendor's own site when a brand is named."""
    kw = _keyword_query(question) or " ".join((question or "").split())
    queries = [kw]
    domain = brand_domain(question)
    if domain:
        queries.append(f"{kw} site:{domain}")
    return queries


def _host(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return (m.group(1).lower() if m else "").removeprefix("www.")


def _rank(results, question):
    """Most useful first: matches the question's words, official vendor site up, video/shops/social down."""
    kws = set(_keywords(_keyword_query(question) + " " + question))
    domain = brand_domain(question)

    def score(r):
        title, body, host = r.get("title", "").lower(), r.get("body", "").lower(), _host(r.get("href"))
        s = sum(2 for k in kws if k in title) + sum(1 for k in kws if k in body)
        if domain and host.endswith(domain):
            s += 4
        if any(j in host for j in _JUNK_DOMAINS):
            s -= 6
        return s

    return sorted(results, key=score, reverse=True)


def search_web(query, max_results=4):
    """General DuckDuckGo text search (keyword rewrite first, then the raw query)."""
    results, _ = research_with_queries(query, max_results=max_results, pages=0)
    return results


def _keywords(text):
    return [w for w in re.findall(r"[\w-]{3,}", (text or "").lower()) if w not in _STOPWORDS]


def _html_to_text(raw):
    raw = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header|form)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>|</div>|</tr>", "\n", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(raw)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if len(line) > 25)


def fetch_page_text(url, question, max_chars=1400):
    """Download a result page and keep only the lines most relevant to the question."""
    if not url or not url.startswith(("http://", "https://")):
        return ""
    key = f"page|{url}|{question.lower()}"
    with _cache_lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < _CACHE_TTL:
            return hit[1]
    text = _fetch_relevant(url, question, max_chars)
    with _cache_lock:
        _cache[key] = (time.time(), text)
    return text


def _fetch_relevant(url, question, max_chars):
    try:
        import httpx

        with httpx.Client(timeout=4.0, follow_redirects=True, headers=_HEADERS) as client:
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
    best = sorted(sorted(scored, reverse=True)[:14], key=lambda t: t[1])
    return "\n".join(line for _, _, line in best)[:max_chars]


def research_with_queries(question, queries=None, exclude=None, max_results=4, pages=3):
    """Run several queries in parallel, merge and rank the results, then read the top pages.

    Returns (results, queries_used). Each result may carry a 'page_text' excerpt.
    """
    queries = [q for q in (queries or query_variants(question)) if q]
    exclude = set(exclude or ())
    with ThreadPoolExecutor(max_workers=max(1, len(queries))) as pool:
        batches = list(pool.map(lambda q: _safe_ddg(q, max_results + 2), queries))
    raw = " ".join((question or "").split())
    if not any(batches) and raw and raw not in queries:
        queries.append(raw)
        batches.append(_safe_ddg(raw, max_results + 2))

    merged, seen = [], set(exclude)
    for batch in batches:
        for r in batch:
            if r.get("href") and r["href"] not in seen:
                seen.add(r["href"])
                merged.append(r)
    results = _rank(merged, question)[:max_results]

    if pages and results:
        focus = f"{question} {_keyword_query(question)}"
        with ThreadPoolExecutor(max_workers=pages) as pool:
            texts = list(pool.map(lambda r: fetch_page_text(r["href"], focus), results[:pages]))
        for r, t in zip(results, texts):
            r["page_text"] = t
    return results, queries


def research(question, max_results=4, pages=3):
    results, _ = research_with_queries(question, max_results=max_results, pages=pages)
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
