"""One-page PDF report (FR-14), once in Romanian and once in English.

Each language gets exactly one A4 page with what a user or their IT supplier needs first:
the official score, the weighted score, the single most urgent problem with its first steps,
and a table of every problem with its first fix. Automatic page breaks are off and the table is
sized to the space left, so the page can never spill over.

Visual style: dark gradient header with soft neon glows, a circular score gauge, rounded cards,
coloured severity pills. Severity is always written as a word too, never shown by colour alone.
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

import logging

from fpdf import FPDF
from fpdf.pattern import LinearGradient

logging.getLogger("fontTools").setLevel(logging.ERROR)

from ai.templates import get_template
from ai.assistant import custom_risk_score

_FONT_CANDIDATES = [
    (Path("C:/Windows/Fonts/segoeui.ttf"), Path("C:/Windows/Fonts/segoeuib.ttf"), Path("C:/Windows/Fonts/segoeuii.ttf")),
    (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf"), Path("C:/Windows/Fonts/ariali.ttf")),
    (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
     Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf")),
]

# Palette
NAVY = (11, 16, 38)
INDIGO = (49, 46, 129)
VIOLET = (124, 58, 237)
CYAN = (6, 182, 212)
PINK = (236, 72, 153)
INK = (15, 23, 42)
MUTED = (100, 116, 139)
LINE = (226, 232, 240)
ZEBRA = (248, 250, 252)
CARD = (245, 243, 255)

_SEV_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}
_SEV_COLORS = {"high": (220, 38, 38), "medium": (217, 119, 6), "low": (37, 99, 235), "info": (100, 116, 139)}
_SEV_TINTS = {"high": (254, 226, 226), "medium": (254, 243, 199), "low": (219, 234, 254), "info": (241, 245, 249)}

_SHORT_TITLE = {
    "ro": {
        "TELNET_OPEN": "Acces la distanta necriptat (Telnet)",
        "RDP_EXPOSED": "Desktop la distanta deschis",
        "VNC_EXPOSED": "Partajare de ecran deschisa",
        "DB_EXPOSED": "Baza de date accesibila din retea",
        "CAMERA_STREAM_EXPOSED": "Imaginile camerei sunt accesibile",
        "OUTDATED_SERVICE": "Program vechi, cu probleme cunoscute",
        "FTP_CLEARTEXT": "Transfer de fisiere necriptat",
        "HTTP_ADMIN_CLEARTEXT": "Pagina de administrare necriptata",
        "SMB_EXPOSED": "Partajare de fisiere Windows deschisa",
        "MQTT_EXPOSED": "Comenzi smart home fara parola",
        "UPNP_EXPOSED": "Deschide singur porturi in router",
        "SNMP_EXPOSED": "Setarile dispozitivului pot fi citite",
        "PRINTER_RAW_EXPOSED": "Oricine poate trimite la imprimanta",
        "UNKNOWN_DEVICE": "Dispozitiv necunoscut in retea",
        "SSH_OPEN": "Acces la distanta criptat (informativ)",
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

_LABELS = {
    "ro": {
        "title": "Raport de securitate a retelei",
        "brand": "SECURE NETWORKS · SIMPLY EXPLAINED",
        "generated": "Generat la", "devices": "dispozitive", "of_100": "din 100",
        "official": "SCOR OFICIAL", "weighted": "Scor ponderat",
        "weighted_note": "Scorul oficial ajustat dupa tipul dispozitivelor si combinatiile de probleme.",
        "verdict": {"safe": "Retea sigura", "watch": "Atentie", "at_risk": "Retea in pericol"},
        "sev": {"high": "Mare", "medium": "Medie", "low": "Mica", "info": "Info"},
        "counts": "PROBLEME PE SEVERITATE",
        "start": "Incepe cu asta",
        "no_findings": "Nu am gasit probleme de securitate. Pastreaza dispozitivele actualizate si scaneaza din nou periodic.",
        "table": "Toate problemele",
        "cols": ("Severitate", "Dispozitiv", "Problema", "Primul pas"),
        "more": "+ {n} alte probleme: vezi lista completa in aplicatie.",
        "footer": ("Scor oficial = 100 minus punctele problemelor (mare 20, medie 10, mica 5). "
                   "Adresele MAC sunt mascate. Pasii completi de rezolvare si istoricul sunt in aplicatie."),
        "page": "Pagina",
    },
    "en": {
        "title": "Network Security Report",
        "brand": "SECURE NETWORKS · SIMPLY EXPLAINED",
        "generated": "Generated", "devices": "devices", "of_100": "out of 100",
        "official": "OFFICIAL SCORE", "weighted": "Weighted score",
        "weighted_note": "The official score adjusted for device type and problem combinations.",
        "verdict": {"safe": "Network is safe", "watch": "Needs attention", "at_risk": "Network at risk"},
        "sev": {"high": "High", "medium": "Medium", "low": "Low", "info": "Info"},
        "counts": "PROBLEMS BY SEVERITY",
        "start": "Start with this",
        "no_findings": "No security problems were found. Keep your devices updated and scan again from time to time.",
        "table": "All problems",
        "cols": ("Severity", "Device", "Problem", "First step"),
        "more": "+ {n} more problems: see the full list in the app.",
        "footer": ("Official score = 100 minus the problems' points (high 20, medium 10, low 5). "
                   "MAC addresses are masked. Full fix steps and history are in the app."),
        "page": "Page",
    },
}


def _hex(rgb) -> str:
    return "#%02x%02x%02x" % tuple(rgb)


class OnePager(FPDF):
    def __init__(self):
        super().__init__(format="A4")
        self.font_name, self.unicode = "Helvetica", False
        for regular, bold, italic in _FONT_CANDIDATES:
            if regular.exists() and bold.exists() and italic.exists():
                self.add_font("Body", "", str(regular))
                self.add_font("Body", "B", str(bold))
                self.add_font("Body", "I", str(italic))
                self.font_name, self.unicode = "Body", True
                break
        self.set_margins(14, 14, 14)
        self.set_auto_page_break(False)
        self.labels = _LABELS["ro"]
        self.page_labels: dict[int, dict] = {}

    # ── text helpers ──
    def clean(self, value) -> str:
        value = "" if value is None else str(value)
        if self.unicode:
            return value
        return value.replace("→", "->").replace("—", "-").replace("·", "-").encode("latin-1", "replace").decode("latin-1")

    def font(self, style: str = "", size: float = 10):
        self.set_font(self.font_name, style, size)

    def fit(self, value, width) -> str:
        value = self.clean(value)
        if self.get_string_width(value) <= width - 1:
            return value
        while value and self.get_string_width(value + "...") > width - 1:
            value = value[:-1]
        return value.rstrip() + "..."

    def wrap(self, text: str, width: float, max_lines: int, line_h: float = 4.6) -> list[str]:
        lines = self.multi_cell(width, line_h, self.clean(text), dry_run=True, output="LINES")
        if len(lines) > max_lines:
            lines = lines[: max_lines - 1] + [self.fit(" ".join(lines[max_lines - 1:]), width)]
        return lines or [""]

    def text_at(self, x, y, w, h, text, style="", size=10, color=INK, align="L"):
        self.font(style, size)
        self.set_text_color(*color)
        self.set_xy(x, y)
        self.cell(w, h, self.clean(text), align=align)

    # ── drawing helpers ──
    def gradient_rect(self, x, y, w, h, colors, vertical=False, radius=0):
        grad = LinearGradient(x, y, x if vertical else x + w, y + h if vertical else y, [_hex(c) for c in colors])
        with self.use_pattern(grad):
            self.rect(x, y, w, h, style="F", round_corners=radius > 0, corner_radius=radius)

    def rounded(self, x, y, w, h, fill, radius=3, border=None):
        self.set_fill_color(*fill)
        if border:
            self.set_draw_color(*border)
            self.set_line_width(0.3)
        self.rect(x, y, w, h, style="DF" if border else "F", round_corners=True, corner_radius=radius)

    def pill(self, x, y, text, fg=(255, 255, 255), bg=VIOLET, size=8.5, h=5.4, pad=2.6) -> float:
        self.font("B", size)
        w = self.get_string_width(self.clean(text)) + 2 * pad
        self.rounded(x, y, w, h, bg, radius=h / 2)
        self.text_at(x, y, w, h, text, "B", size, fg, align="C")
        return w

    def glow(self, cx, cy, r, color, opacity):
        with self.local_context(fill_opacity=opacity):
            self.set_fill_color(*color)
            self.circle(cx, cy, r, style="F")

    def gauge(self, cx, cy, d, score, color):
        """Circular ring filled clockwise from the top in proportion to the score."""
        r = d / 2
        thickness = 4.2
        self.set_fill_color(*LINE)
        self.circle(cx, cy, r, style="F")
        value = max(0, min(100, score if isinstance(score, (int, float)) else 0))
        if value >= 100:
            self.set_fill_color(*color)
            self.circle(cx, cy, r, style="F")
        elif value > 0:
            self.set_fill_color(*color)
            self.solid_arc(cx - r, cy - r, d, -90, -90 + value * 3.6, style="F")
        self.set_fill_color(255, 255, 255)
        self.circle(cx, cy, r - thickness, style="F")

    def footer(self):
        # fpdf draws a footer when the NEXT page starts, so look up the labels of the page being closed.
        labels = self.page_labels.get(self.page_no(), self.labels)
        y = self.h - 15
        # the header glows use transparency; make sure none of it reaches the footer text
        with self.local_context(fill_opacity=1, stroke_opacity=1):
            self.gradient_rect(self.l_margin, y, self.epw, 0.7, [CYAN, VIOLET, PINK])
            self.font("", 7.8)
            self.set_text_color(*MUTED)
            self.set_xy(self.l_margin, y + 2)
            self.multi_cell(self.epw - 26, 3.6, self.clean(labels["footer"]), new_x="LMARGIN", new_y="NEXT", align="L")
            self.pill(self.w - self.r_margin - 22, y + 2.5, f"{labels['page']} {self.page_no()}/{{nb}}",
                      fg=(255, 255, 255), bg=INDIGO, size=7.5, h=5)


def _verdict(score) -> str:
    if not isinstance(score, (int, float)):
        return "at_risk"
    return "safe" if score >= 80 else "watch" if score >= 50 else "at_risk"


def _score_color(score) -> tuple:
    if not isinstance(score, (int, float)):
        return MUTED
    return (239, 68, 68) if score < 50 else (245, 158, 11) if score < 80 else (16, 185, 129)


def _all_findings(devices: list, lang: str) -> list:
    rows = []
    for d in devices:
        label = d.get(f"type_label_{lang}") or d.get("type") or ""
        name = " ".join(x for x in (d.get("vendor") or "", label) if x).strip()
        for f in d.get("findings", []):
            rows.append({**f, "device_name": name or d.get("ip", "?"), "device_ip": d.get("ip", "?")})
    rows.sort(key=lambda f: (_SEV_ORDER.get(f.get("severity", "info"), 9), -(f.get("points") or 0), f["device_ip"]))
    return rows


def _header(pdf: OnePager, t: dict, stamp: str, n_devices: int) -> float:
    h = 36
    pdf.gradient_rect(0, 0, pdf.w, h, [NAVY, INDIGO, VIOLET])
    # soft neon glows
    pdf.glow(pdf.w - 30, 4, 24, CYAN, 0.18)
    pdf.glow(pdf.w - 14, 20, 12, PINK, 0.24)
    pdf.glow(pdf.w - 64, 27, 8, CYAN, 0.14)
    # thin circuit-like accent line
    pdf.gradient_rect(0, h - 1.2, pdf.w, 1.2, [CYAN, VIOLET, PINK])
    pdf.text_at(pdf.l_margin, 8, 150, 5, t["brand"], "B", 7.8, (165, 243, 252))
    pdf.text_at(pdf.l_margin, 13.5, 170, 11, t["title"], "B", 21, (255, 255, 255))
    pdf.text_at(pdf.l_margin, 25.5, 170, 5, f"{t['generated']}: {stamp}   ·   {n_devices} {t['devices']}", "", 9.5,
                (199, 210, 254))
    return h + 7


def _score_block(pdf: OnePager, t: dict, scan_data: dict, findings: list, top: float) -> float:
    score = scan_data.get("score")
    color = _score_color(score)
    x0 = pdf.l_margin
    # Gauge card
    pdf.rounded(x0, top, 62, 58, (255, 255, 255), radius=4, border=LINE)
    cx, cy, d = x0 + 31, top + 23, 34
    pdf.gauge(cx, cy, d, score, color)
    pdf.text_at(cx - 15, cy - 7.5, 30, 10, f"{score if score is not None else '-'}", "B", 25, INK, align="C")
    pdf.text_at(cx - 15, cy + 2.5, 30, 4, t["of_100"], "", 7.8, MUTED, align="C")
    pdf.text_at(x0, top + 42, 62, 4, t["official"], "B", 7.5, MUTED, align="C")
    verdict = t["verdict"][_verdict(score)]
    pdf.font("B", 9)
    vw = pdf.get_string_width(pdf.clean(verdict)) + 6
    pdf.pill(x0 + 31 - vw / 2, top + 47.5, verdict, bg=color, size=9, h=6, pad=3)

    # Right column: weighted score card + severity tiles
    x2 = x0 + 68
    w2 = pdf.epw - 68
    if scan_data.get("devices") and score is not None:
        weighted = custom_risk_score(scan_data)["score"]
        pdf.rounded(x2, top, w2, 24, CARD, radius=4)
        pdf.gradient_rect(x2, top, 2.4, 24, [CYAN, VIOLET], vertical=True)
        pdf.text_at(x2 + 6, top + 3.5, 60, 5, t["weighted"].upper(), "B", 7.5, MUTED)
        pdf.text_at(x2 + 6, top + 8.5, 40, 10, f"{weighted}", "B", 21, _score_color(weighted))
        pdf.font("B", 21)
        num_w = pdf.get_string_width(str(weighted))
        pdf.text_at(x2 + 6 + num_w + 1, top + 11.5, 20, 6, "/100", "B", 10, MUTED)
        pdf.font("", 8.5)
        pdf.set_text_color(*MUTED)
        pdf.set_xy(x2 + 46, top + 6.5)
        pdf.multi_cell(w2 - 50, 4.2, pdf.clean(t["weighted_note"]), align="L", new_x="LMARGIN", new_y="NEXT")

    tiles_top = top + 28
    pdf.text_at(x2, tiles_top, w2, 4, t["counts"], "B", 7.5, MUTED)
    counts = {s: sum(1 for f in findings if f.get("severity") == s) for s in ("high", "medium", "low", "info")}
    gap = 3
    tw = (w2 - 3 * gap) / 4
    for i, sev in enumerate(("high", "medium", "low", "info")):
        tx = x2 + i * (tw + gap)
        pdf.rounded(tx, tiles_top + 5, tw, 25, _SEV_TINTS[sev], radius=3.5)
        pdf.set_fill_color(*_SEV_COLORS[sev])
        pdf.rect(tx + 4, tiles_top + 8, tw - 8, 1, style="F", round_corners=True, corner_radius=0.5)
        pdf.text_at(tx, tiles_top + 10.5, tw, 9, str(counts[sev]), "B", 19, _SEV_COLORS[sev], align="C")
        pdf.text_at(tx, tiles_top + 21, tw, 4, t["sev"][sev], "B", 8.5, _SEV_COLORS[sev], align="C")
    return top + 64


def _start_card(pdf: OnePager, t: dict, lang: str, findings: list, top: float) -> float:
    x = pdf.l_margin
    w = pdf.epw
    pdf.text_at(x, top, w, 7, t["start"], "B", 13.5, INK)
    top += 8.5
    if not findings:
        lines = pdf.wrap(t["no_findings"], w - 12, 3, 5)
        h = 8 + len(lines) * 5
        pdf.rounded(x, top, w, h, (236, 253, 245), radius=4)
        for i, line in enumerate(lines):
            pdf.text_at(x + 6, top + 4 + i * 5, w - 12, 5, line, "", 10.5, (6, 95, 70))
        return top + h + 6

    first = findings[0]
    tmpl = get_template(first["code"], lang) or {}
    sev = first.get("severity", "info")
    inner_x, inner_w = x + 9, w - 15
    head = f"{_SHORT_TITLE[lang].get(first['code'], first['code'])}  ·  {first['device_name']} ({first['device_ip']})"
    pdf.font("B", 11)
    head_lines = pdf.wrap(head, inner_w - 22, 2, 5.4)
    pdf.font("", 10)
    expl_lines = pdf.wrap(tmpl.get("explanation", ""), inner_w, 3, 4.8)
    steps = tmpl.get("fix_steps", [])[:3]
    pdf.font("", 10)
    step_lines = [pdf.wrap(s, inner_w - 9, 2, 4.8) for s in steps]
    h = 6 + len(head_lines) * 5.4 + 2 + len(expl_lines) * 4.8 + 2 + sum(max(1, len(l)) * 4.8 + 1.6 for l in step_lines) + 3

    pdf.rounded(x, top, w, h, CARD, radius=4)
    pdf.gradient_rect(x, top, 3, h, [PINK, VIOLET, CYAN], vertical=True)
    y = top + 4
    pw = pdf.pill(inner_x, y, t["sev"][sev], bg=_SEV_COLORS[sev], size=8.5, h=5.4)
    for i, line in enumerate(head_lines):
        pdf.text_at(inner_x + pw + 3 if i == 0 else inner_x, y + i * 5.4, inner_w, 5.4, line, "B", 11, INK)
    y += len(head_lines) * 5.4 + 2
    for line in expl_lines:
        pdf.text_at(inner_x, y, inner_w, 4.8, line, "", 10, (51, 65, 85))
        y += 4.8
    y += 2
    for i, lines in enumerate(step_lines, 1):
        pdf.set_fill_color(*VIOLET)
        pdf.circle(inner_x + 2.6, y + 2.4, 2.6, style="F")
        pdf.text_at(inner_x, y + 0.1, 5.2, 4.6, str(i), "B", 8, (255, 255, 255), align="C")
        for j, line in enumerate(lines):
            pdf.text_at(inner_x + 8, y + j * 4.8, inner_w - 9, 4.8, line, "", 10, INK)
        y += max(1, len(lines)) * 4.8 + 1.6
    return top + h + 6


def _table(pdf: OnePager, t: dict, lang: str, findings: list, top: float) -> None:
    if not findings:
        return
    x = pdf.l_margin
    widths = [24, 46, 52, pdf.epw - 122]
    pdf.text_at(x, top, pdf.epw, 7, f"{t['table']} ({len(findings)})", "B", 13.5, INK)
    y = top + 9
    # gradient header row
    pdf.gradient_rect(x, y, pdf.epw, 7.5, [NAVY, INDIGO, VIOLET], radius=2.5)
    cx = x
    for wcol, col in zip(widths, t["cols"]):
        pdf.text_at(cx + 2.5, y + 1.5, wcol - 3, 4.6, col, "B", 8.8, (255, 255, 255))
        cx += wcol
    y += 8.5
    bottom = pdf.h - 19
    line_h = 4.4
    for i, f in enumerate(findings):
        sev = f.get("severity", "info")
        tmpl = get_template(f["code"], lang) or {}
        port = f" :{f['port']}" if f.get("port") else ""
        cells = [
            f"{f['device_name']} {f['device_ip']}{port}",
            _SHORT_TITLE[lang].get(f["code"], f["code"]),
            (tmpl.get("fix_steps") or ["-"])[0],
        ]
        pdf.font("", 9)
        wrapped = [pdf.wrap(c, wcol - 4, 3, line_h) for c, wcol in zip(cells, widths[1:])]
        h = max(len(l) for l in wrapped) * line_h + 3.2
        remaining = len(findings) - i
        limit = bottom if remaining == 1 else bottom - 8
        if y + h > limit:
            pdf.rounded(x, y + 0.5, pdf.epw, 6.5, ZEBRA, radius=2)
            pdf.text_at(x + 3, y + 1.3, pdf.epw - 6, 5, t["more"].format(n=remaining), "I", 9, INDIGO)
            return
        if i % 2 == 0:
            pdf.rounded(x, y, pdf.epw, h, ZEBRA, radius=2)
        pdf.pill(x + 2.5, y + (h - 5.2) / 2, t["sev"][sev], bg=_SEV_COLORS[sev], size=8, h=5.2, pad=2.4)
        cx = x + widths[0]
        for lines, wcol in zip(wrapped, widths[1:]):
            for j, line in enumerate(lines):
                pdf.text_at(cx + 2, y + 1.6 + j * line_h, wcol - 4, line_h, line, "", 9, INK)
            cx += wcol
        y += h
        pdf.set_draw_color(*LINE)
        pdf.set_line_width(0.2)
        pdf.line(x + 2, y, x + pdf.epw - 2, y)


def _page(pdf: OnePager, scan_data: dict, lang: str) -> None:
    t = _LABELS[lang]
    pdf.labels = t
    pdf.add_page()
    pdf.page_labels[pdf.page_no()] = t
    devices = scan_data.get("devices", [])
    findings = _all_findings(devices, lang)
    stamp = str(scan_data.get("timestamp") or datetime.now().isoformat())[:16].replace("T", " ")

    y = _header(pdf, t, stamp, len(devices))
    y = _score_block(pdf, t, scan_data, findings, y)
    y = _start_card(pdf, t, lang, findings, y)
    _table(pdf, t, lang, findings, y)
    pdf.set_text_color(0, 0, 0)


def generate_report(scan_data: dict, language: str = "ro") -> bytes:
    """Two pages: one in the requested language, then the same page in the other language."""
    first = "en" if language == "en" else "ro"
    pdf = OnePager()
    pdf.alias_nb_pages()
    for lang in (first, "en" if first == "ro" else "ro"):
        _page(pdf, scan_data, lang)
    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
