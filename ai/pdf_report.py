"""One-page PDF report (FR-14) styled as a shop receipt, once in Romanian and once in English.

The joke carries the message: every problem is an "item" that costs an attacker nothing, so the
total is 0.00. Each language fits on exactly one A4 page: the receipt is drawn as large as the page
allows with every item on it, and only when even the base size can't hold them do the last ones
become "+ N more". Severity is always written as a word, and the receipt says it is not fiscal.
"""

from __future__ import annotations

import hashlib
import io
import logging
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

from ai.templates import get_template
from ai.assistant import custom_risk_score

logging.getLogger("fontTools").setLevel(logging.ERROR)

_FONT_CANDIDATES = [
    (Path("C:/Windows/Fonts/consola.ttf"), Path("C:/Windows/Fonts/consolab.ttf"), Path("C:/Windows/Fonts/consolai.ttf")),
    (Path("C:/Windows/Fonts/cour.ttf"), Path("C:/Windows/Fonts/courbd.ttf"), Path("C:/Windows/Fonts/couri.ttf")),
    (Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"),
     Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Oblique.ttf")),
]

PAPER = (255, 253, 246)
EDGE = (205, 200, 185)
INK = (30, 30, 30)
FADED = (110, 110, 110)

BASE_W = 120             # mm, receipt width at scale 1 (a wide till roll, so it fills the page)
MAX_W = 172              # mm, widest receipt on A4 (about 19 mm margin each side)
PAD = 7                  # inner padding at scale 1
LINE_H = 4.3             # line height at scale 1
TOP, BOTTOM = 8, 287     # usable vertical space on A4

_SEV_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}
_RO_ASCII = str.maketrans("ăâîșțşţĂÂÎȘȚŞŢ", "aaiststAAISTST")

_SHORT_TITLE = {
    "ro": {
        "TELNET_OPEN": "Acces la distanță necriptat (Telnet)",
        "RDP_EXPOSED": "Desktop la distanță deschis",
        "VNC_EXPOSED": "Partajare de ecran deschisă",
        "DB_EXPOSED": "Bază de date accesibilă din rețea",
        "CAMERA_STREAM_EXPOSED": "Imaginile camerei sunt accesibile",
        "OUTDATED_SERVICE": "Program vechi, cu probleme cunoscute",
        "FTP_CLEARTEXT": "Transfer de fișiere necriptat",
        "HTTP_ADMIN_CLEARTEXT": "Pagină de administrare necriptată",
        "SMB_EXPOSED": "Partajare de fișiere Windows deschisă",
        "MQTT_EXPOSED": "Comenzi smart home fără parolă",
        "UPNP_EXPOSED": "Deschide singur porturi în router",
        "SNMP_EXPOSED": "Setările dispozitivului pot fi citite",
        "PRINTER_RAW_EXPOSED": "Oricine poate trimite la imprimantă",
        "UNKNOWN_DEVICE": "Dispozitiv necunoscut în rețea",
        "SSH_OPEN": "Acces la distanță criptat (informativ)",
    },
    "en": {
        "TELNET_OPEN": "Unencrypted remote login (Telnet)",
        "RDP_EXPOSED": "Remote desktop is reachable",
        "VNC_EXPOSED": "Screen sharing is reachable",
        "DB_EXPOSED": "Database reachable from the network",
        "CAMERA_STREAM_EXPOSED": "Camera video can be watched",
        "OUTDATED_SERVICE": "Old software with known problems",
        "FTP_CLEARTEXT": "Unencrypted file transfer",
        "HTTP_ADMIN_CLEARTEXT": "Admin page without encryption",
        "SMB_EXPOSED": "Windows file sharing is open",
        "MQTT_EXPOSED": "Smart home commands without password",
        "UPNP_EXPOSED": "Can open router ports by itself",
        "SNMP_EXPOSED": "Device settings can be read",
        "PRINTER_RAW_EXPOSED": "Anyone can send jobs to the printer",
        "UNKNOWN_DEVICE": "Unknown device on the network",
        "SSH_OPEN": "Encrypted remote login (for awareness)",
    },
}

# First fix step with diacritics (the shared templates are written without them).
_FIRST_STEP_RO = {
    "TELNET_OPEN": "Deschide setările routerului în browser (scrie adresa IP în bara de adrese)",
    "RDP_EXPOSED": "Deschide Settings (Setări) pe calculator",
    "VNC_EXPOSED": "Deschide aplicația VNC Server de pe acest dispozitiv",
    "DB_EXPOSED": "Configurează baza de date să accepte conexiuni doar de la adresa 127.0.0.1 (doar local)",
    "CAMERA_STREAM_EXPOSED": "Deschide setările camerei în browser (scrie adresa IP a camerei)",
    "OUTDATED_SERVICE": "Identifică programul și versiunea curentă (vezi detaliile din aplicație)",
    "FTP_CLEARTEXT": "Înlocuiește FTP cu SFTP (versiunea sigură, criptată)",
    "HTTP_ADMIN_CLEARTEXT": "Deschide setările dispozitivului în browser",
    "SMB_EXPOSED": "Deschide Settings (Setări) → Network & Internet → Advanced sharing settings",
    "MQTT_EXPOSED": "Deschide setările broker-ului MQTT (de obicei prin interfața web a hub-ului smart home)",
    "UPNP_EXPOSED": "Deschide setările routerului în browser",
    "SNMP_EXPOSED": "Deschide setările dispozitivului (de obicei routerul)",
    "PRINTER_RAW_EXPOSED": "Deschide setările imprimantei (de obicei prin interfața web, la adresa IP a imprimantei)",
    "UNKNOWN_DEVICE": "Verifică toate dispozitivele tale: telefoane, tablete, laptopuri, televizoare smart",
    "SSH_OPEN": "Verifică dacă folosești o parolă puternică sau autentificare cu chei SSH",
}
_TYPE_RO = {"Camera IP": "Cameră IP", "Imprimanta": "Imprimantă"}

_LABELS = {
    "ro": {
        "shop": "BON DE SECURITATE",
        "tagline": "Secure Networks, Simply Explained",
        "event": "R Systems Hackathon 2026",
        "date": "Data", "receipt_no": "Bon nr.", "cashier": "Casier: Dl. Cartof",
        "devices": "Dispozitive scanate", "problems": "Probleme găsite",
        "official": "Scor oficial", "weighted": "Scor ponderat", "status": "Stare",
        "verdict": {"safe": "REȚEA SIGURĂ", "watch": "ATENȚIE", "at_risk": "REȚEA ÎN PERICOL"},
        "note_title": "*** ATENȚIE ***",
        "note": "Pentru un potențial atacator, toate produsele de mai jos sunt GRATUITE. Închide-le înainte să le ia cineva.",
        "item": "PRODUS", "price": "PREȚ",
        "sev": {"high": "MARE", "medium": "MEDIE", "low": "MICĂ", "info": "INFO"},
        "free": "0,00", "currency": "lei",
        "more": "+ {n} alte produse (vezi aplicația)",
        "empty": "Niciun produs: rețeaua ta nu oferă nimic gratis.",
        "subtotal": "SUBTOTAL", "vat": "TVA 0%", "total": "TOTAL DE PLATĂ",
        "first_step": "PRIMUL PAS:",
        "score_rule": "Scor oficial = 100 - punctele problemelor",
        "privacy": "Adresele MAC sunt mascate.",
        "thanks": "Vă așteptăm la o nouă scanare!",
        "not_fiscal": "NU ESTE BON FISCAL",
        "page": "Pagina",
    },
    "en": {
        "shop": "SECURITY RECEIPT",
        "tagline": "Secure Networks, Simply Explained",
        "event": "R Systems Hackathon 2026",
        "date": "Date", "receipt_no": "Receipt no.", "cashier": "Cashier: Mr. Potato",
        "devices": "Devices scanned", "problems": "Problems found",
        "official": "Official score", "weighted": "Weighted score", "status": "Status",
        "verdict": {"safe": "NETWORK IS SAFE", "watch": "NEEDS ATTENTION", "at_risk": "NETWORK AT RISK"},
        "note_title": "*** NOTE ***",
        "note": "For a potential attacker, every item below is FREE. Close them before someone takes them.",
        "item": "ITEM", "price": "PRICE",
        "sev": {"high": "HIGH", "medium": "MEDIUM", "low": "LOW", "info": "INFO"},
        "free": "0.00", "currency": "EUR",
        "more": "+ {n} more items (see the app)",
        "empty": "No items: your network gives nothing away for free.",
        "subtotal": "SUBTOTAL", "vat": "VAT 0%", "total": "TOTAL DUE",
        "first_step": "FIRST STEP:",
        "score_rule": "Official score = 100 - problem points",
        "privacy": "MAC addresses are masked.",
        "thanks": "See you at the next scan!",
        "not_fiscal": "NOT A FISCAL RECEIPT",
        "page": "Page",
    },
}


class Receipt(FPDF):
    def __init__(self):
        super().__init__(format="A4")
        self.font_name, self.unicode = "Courier", False
        for regular, bold, italic in _FONT_CANDIDATES:
            if regular.exists() and bold.exists() and italic.exists():
                self.add_font("Mono", "", str(regular))
                self.add_font("Mono", "B", str(bold))
                self.add_font("Mono", "I", str(italic))
                self.font_name, self.unicode = "Mono", True
                break
        self.set_auto_page_break(False)
        self.set_margins(0, 0, 0)
        self.set_scale(1.0)

    def set_scale(self, s: float) -> None:
        """Everything on the receipt (width, padding, fonts, line height) grows with s."""
        self.s = s
        self.rw = BASE_W * s
        self.x0 = (self.w - self.rw) / 2
        self.pad = PAD * s
        self.text_w = self.rw - 2 * self.pad
        self.lh = LINE_H * s

    def clean(self, value) -> str:
        value = "" if value is None else str(value)
        if self.unicode:
            return value
        # core Courier has no Romanian letters: fall back to the plain ones instead of "?"
        return value.translate(_RO_ASCII).replace("→", "->").encode("latin-1", "replace").decode("latin-1")

    def font(self, style="", size=9.0):
        self.set_font(self.font_name, style, size * self.s)

    def wrap(self, text, width, style="", size=9.0) -> list[str]:
        self.font(style, size)
        return self.multi_cell(width, self.lh, self.clean(text), dry_run=True, output="LINES") or [""]


# ── A receipt is built as a list of lines first, so its height is known before drawing ──

def _ops_header(pdf: Receipt, t: dict, scan_data: dict, findings: list) -> list:
    score = scan_data.get("score")
    stamp = str(scan_data.get("timestamp") or datetime.now().isoformat())[:16].replace("T", " ")
    weighted = custom_risk_score(scan_data)["score"] if scan_data.get("devices") and score is not None else None
    verdict = "safe" if (score or 0) >= 80 else "watch" if (score or 0) >= 50 else "at_risk"
    no = scan_data.get("scan_id")
    ops = [
        ("center", t["shop"], "B", 13), ("center", t["tagline"], "", 8.5), ("center", t["event"], "", 8.5),
        ("gap", 2), ("sep", "="),
        ("row", f"{t['date']}: {stamp}", f"{t['receipt_no']} {no:04d}" if isinstance(no, int) else "", "", 8.5),
        ("left", t["cashier"], "", 8.5), ("sep", "-"),
        ("row", t["devices"], str(len(scan_data.get("devices", []))), "", 9.5),
        ("row", t["problems"], str(len(findings)), "", 9.5),
        ("row", t["official"], f"{score if score is not None else '-'}/100", "B", 9.5),
    ]
    if weighted is not None:
        ops.append(("row", t["weighted"], f"{weighted}/100", "", 9.5))
    ops += [("row", t["status"], t["verdict"][verdict], "B", 9.5), ("sep", "-"),
            ("center", t["note_title"], "B", 9.5)]
    ops += [("center", line, "", 9) for line in pdf.wrap(t["note"], pdf.text_w, "", 9)]
    ops += [("sep", "-"), ("row", t["item"], t["price"], "B", 9), ("gap", 1)]
    return ops


def _ops_item(pdf: Receipt, t: dict, lang: str, i: int, f: dict) -> list:
    price_w = 14 * pdf.s
    title = f"{i:>2} x {_SHORT_TITLE[lang].get(f['code'], f['code'])}"
    port = f":{f['port']}" if f.get("port") else ""
    detail = f"{f['device_name']} {f['device_ip']}{port} [{t['sev'][f.get('severity', 'info')]}]"
    lines = pdf.wrap(title, pdf.text_w - price_w, "B", 9)[:2]
    ops = [("row", lines[0], t["free"], "B", 9)]
    ops += [("left", "     " + line.strip(), "B", 9) for line in lines[1:]]
    ops += [("left", "     " + line.strip(), "", 8.3, FADED)
            for line in pdf.wrap(detail, pdf.text_w - 9 * pdf.s, "", 8.3)[:2]]
    return ops


def _first_step(code: str, lang: str) -> str:
    if lang == "ro" and code in _FIRST_STEP_RO:
        return _FIRST_STEP_RO[code]
    return ((get_template(code, lang) or {}).get("fix_steps") or [""])[0]


def _ops_footer(pdf: Receipt, t: dict, lang: str, findings: list) -> list:
    ops = [("sep", "-"), ("row", t["subtotal"], t["free"], "", 9), ("row", t["vat"], t["free"], "", 9),
           ("sep", "="), ("row", t["total"], f"{t['free']} {t['currency']}", "B", 12), ("sep", "=")]
    if findings:
        ops += [("left", t["first_step"], "B", 9)]
        ops += [("left", line, "", 9) for line in pdf.wrap(_first_step(findings[0]["code"], lang), pdf.text_w, "", 9)[:3]]
        ops.append(("sep", "-"))
    ops += [("center", t["score_rule"], "", 8), ("center", t["privacy"], "", 8), ("gap", 1.5),
            ("center", t["thanks"], "B", 9), ("gap", 2), ("barcode",), ("gap", 1),
            ("center", t["not_fiscal"], "B", 8.5)]
    return ops


def _height(pdf: Receipt, op) -> float:
    kind = op[0]
    if kind == "gap":
        return op[1] * pdf.s
    if kind == "barcode":
        return 12 * pdf.s
    if (kind == "center" and op[3] >= 12) or (kind == "row" and op[4] >= 12):
        return 6.5 * pdf.s
    return pdf.lh


def _total(pdf: Receipt, ops: list) -> float:
    return sum(_height(pdf, o) for o in ops) + 12 * pdf.s   # + top/bottom padding of the paper


def _layout(pdf: Receipt, t: dict, scan_data: dict, lang: str, findings: list, truncate: bool):
    """Lines for the whole receipt at the current scale. Without truncate every item is included."""
    header = _ops_header(pdf, t, scan_data, findings)
    footer = _ops_footer(pdf, t, lang, findings)
    if not findings:
        items = [("center", line, "", 9) for line in pdf.wrap(t["empty"], pdf.text_w, "", 9)]
        return header + items + footer
    budget = (BOTTOM - TOP) - _total(pdf, header + footer)
    items, used = [], 0.0
    for i, f in enumerate(findings, 1):
        block = _ops_item(pdf, t, lang, i, f) + [("gap", 1.2)]
        block_h = sum(_height(pdf, o) for o in block)
        more_h = pdf.lh if i < len(findings) else 0
        if truncate and used + block_h + more_h > budget:
            items.append(("left", t["more"].format(n=len(findings) - i + 1), "I", 9))
            break
        items += block
        used += block_h
    return header + items + footer


# ── drawing ──

def _paper(pdf: Receipt, top: float, height: float) -> None:
    """Receipt paper with zig-zag torn edges at the top and bottom."""
    x0, x1 = pdf.x0, pdf.x0 + pdf.rw
    depth = 1.5 * pdf.s
    n = int(pdf.rw // (3.2 * pdf.s))
    step = pdf.rw / n
    pts = [(x0, top + depth)]
    for k in range(n):
        pts += [(x0 + (k + 0.5) * step, top), (x0 + (k + 1) * step, top + depth)]
    bottom = top + height
    pts.append((x1, bottom - depth))
    for k in range(n):
        pts += [(x1 - (k + 0.5) * step, bottom), (x1 - (k + 1) * step, bottom - depth)]
    pdf.set_fill_color(232, 230, 222)  # soft shadow
    pdf.polygon([(x + 1.4, y + 1.4) for x, y in pts], style="F")
    pdf.set_fill_color(*PAPER)
    pdf.set_draw_color(*EDGE)
    pdf.set_line_width(0.25)
    pdf.polygon(pts, style="DF")


def _barcode(pdf: Receipt, y: float, seed: str) -> None:
    digest = hashlib.sha256(seed.encode()).digest()
    widths = [(0.35 + (b % 4) * 0.3) * pdf.s for b in digest[:26]]
    x = pdf.x0 + (pdf.rw - sum(widths) * 2) / 2
    pdf.set_fill_color(*INK)
    for k, w in enumerate(widths):
        if k % 2 == 0:
            pdf.rect(x, y, w, 9 * pdf.s, style="F")
        x += w * 2
    pdf.font("", 7)
    pdf.set_text_color(*FADED)
    pdf.set_xy(pdf.x0, y + 9.3 * pdf.s)
    pdf.cell(pdf.rw, 3 * pdf.s, digest.hex()[:20].upper(), align="C")


def _draw(pdf: Receipt, ops: list, top: float, seed: str) -> None:
    y = top + 6 * pdf.s
    x = pdf.x0 + pdf.pad
    for op in ops:
        kind = op[0]
        h = _height(pdf, op)
        if kind == "sep":
            pdf.font("", 9)
            pdf.set_text_color(*FADED)
            n = int(pdf.text_w / pdf.get_string_width(op[1]))
            pdf.set_xy(x, y)
            pdf.cell(pdf.text_w, h, op[1] * n, align="C")
        elif kind == "center":
            pdf.font(op[2], op[3])
            pdf.set_text_color(*INK)
            pdf.set_xy(x, y)
            pdf.cell(pdf.text_w, h, pdf.clean(op[1]), align="C")
        elif kind == "left":
            pdf.font(op[2], op[3])
            pdf.set_text_color(*(op[5] if len(op) > 5 else INK))
            pdf.set_xy(x, y)
            pdf.cell(pdf.text_w, h, pdf.clean(op[1]))
        elif kind == "row":
            pdf.font(op[3], op[4])
            pdf.set_text_color(*INK)
            right = pdf.clean(op[2])
            right_w = pdf.get_string_width(right) + 1
            left = pdf.clean(op[1])
            while left and pdf.get_string_width(left) > pdf.text_w - right_w - 2:
                left = left[:-1]
            pdf.set_xy(x, y)
            pdf.cell(pdf.text_w - right_w, h, left)
            pdf.set_xy(x + pdf.text_w - right_w, y)
            pdf.cell(right_w, h, right, align="R")
        elif kind == "barcode":
            _barcode(pdf, y, seed)
        y += h


def _all_findings(devices: list, lang: str) -> list:
    rows = []
    for d in devices:
        label = d.get(f"type_label_{lang}") or d.get("type") or ""
        if lang == "ro":
            label = _TYPE_RO.get(label, label)
        name = " ".join(x for x in (d.get("vendor") or "", label) if x).strip()
        for f in d.get("findings", []):
            rows.append({**f, "device_name": name or d.get("ip", "?"), "device_ip": d.get("ip", "?")})
    rows.sort(key=lambda f: (_SEV_ORDER.get(f.get("severity", "info"), 9), -(f.get("points") or 0), f["device_ip"]))
    return rows


def _page(pdf: Receipt, scan_data: dict, lang: str) -> None:
    t = _LABELS[lang]
    pdf.add_page()
    findings = _all_findings(scan_data.get("devices", []), lang)
    available = BOTTOM - TOP

    # Largest scale at which the whole receipt, with every item, fits on the page.
    ops = None
    s = MAX_W / BASE_W
    while s >= 1.0:
        pdf.set_scale(s)
        candidate = _layout(pdf, t, scan_data, lang, findings, truncate=False)
        if _total(pdf, candidate) <= available:
            ops = candidate
            break
        s = round(s - 0.02, 2)
    if ops is None:  # too many items even at base size: keep base size and cut the list
        pdf.set_scale(1.0)
        ops = _layout(pdf, t, scan_data, lang, findings, truncate=True)

    height = _total(pdf, ops)
    top = TOP + max(0.0, (available - height) / 2)
    _paper(pdf, top, height)
    _draw(pdf, ops, top, f"{scan_data.get('scan_id')}-{scan_data.get('score')}-{len(findings)}")

    pdf.set_scale(1.0)
    pdf.font("", 7.5)
    pdf.set_text_color(*FADED)
    pdf.set_xy(0, 290)
    pdf.cell(pdf.w, 4, f"{t['page']} {pdf.page_no()}/{{nb}}", align="C")


def generate_report(scan_data: dict, language: str = "ro") -> bytes:
    """Two pages: one receipt in the requested language, then the same receipt in the other language."""
    first = "en" if language == "en" else "ro"
    pdf = Receipt()
    pdf.alias_nb_pages()
    for lang in (first, "en" if first == "ro" else "ro"):
        _page(pdf, scan_data, lang)
    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
