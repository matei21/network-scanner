"""
Web search integration pentru instructiuni specifice per device.
Foloseste DuckDuckGo (gratuit, fara API key).
"""

import logging

logger = logging.getLogger(__name__)


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
