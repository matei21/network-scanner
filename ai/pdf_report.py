"""One-page PDF report (FR-14), once in Romanian and once in English.

Each language gets exactly one A4 page with what a user or their IT supplier needs first:
the official score, the weighted score, the single most urgent problem with its first steps,
and a table of every problem with its first fix. Automatic page breaks are off and the table is
sized to the space left, so the page can never spill over.
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

from ai.templates import get_template
from ai.assistant import custom_risk_score

_FONT_CANDIDATES = [
    (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf"), Path("C:/Windows/Fonts/ariali.ttf")),
    (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
     Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf")),
]

_SEV_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}
_SEV_COLORS = {"high": (185, 28, 28), "medium": (180, 83, 9), "low": (29, 78, 216), "info": (90, 90, 90)}

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
        "generated": "Generat la", "devices": "dispozitive", "of_100": "din 100",
        "official": "Scor oficial", "weighted": "Scor ponderat",
        "weighted_note": "scorul oficial ajustat dupa tipul dispozitivelor si combinatii de probleme",
        "verdict": {"safe": "Retea sigura", "watch": "Atentie", "at_risk": "Retea in pericol"},
        "sev": {"high": "Mare", "medium": "Medie", "low": "Mica", "info": "Info"},
        "counts": "Probleme pe severitate",
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
        "generated": "Generated", "devices": "devices", "of_100": "out of 100",
        "official": "Official score", "weighted": "Weighted score",
        "weighted_note": "the official score adjusted for device type and problem combinations",
        "verdict": {"safe": "Network is safe", "watch": "Needs attention", "at_risk": "Network at risk"},
        "sev": {"high": "High", "medium": "Medium", "low": "Low", "info": "Info"},
        "counts": "Problems by severity",
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
        self.set_margins(15, 14, 15)
        self.set_auto_page_break(False)
        self.labels = _LABELS["ro"]
        self.page_labels: dict[int, dict] = {}

    def clean(self, value) -> str:
        value = "" if value is None else str(value)
        if self.unicode:
            return value
        return value.replace("→", "->").replace("—", "-").encode("latin-1", "replace").decode("latin-1")

    def font(self, style: str = "", size: float = 10):
        self.set_font(self.font_name, style, size)

    def fit(self, value, width) -> str:
        value = self.clean(value)
        if self.get_string_width(value) <= width - 2:
            return value
        while value and self.get_string_width(value + "...") > width - 2:
            value = value[:-1]
        return value.rstrip() + "..."

    def para(self, value, size=10, style="", color=(0, 0, 0), h=5.0, indent=0.0, max_lines=None):
        self.font(style, size)
        text = self.clean(value)
        if max_lines:
            lines = self.multi_cell(self.epw - indent, h, text, dry_run=True, output="LINES")
            if len(lines) > max_lines:
                text = " ".join(lines[:max_lines])
                text = self.fit(text, (self.epw - indent) * max_lines)
        self.set_text_color(*color)
        self.set_x(self.l_margin + indent)
        self.multi_cell(self.epw - indent, h, text, new_x="LMARGIN", new_y="NEXT", align="L")
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-16)
        self.font("", 8)
        self.set_text_color(100, 100, 100)
        # fpdf draws a footer when the NEXT page starts, so look up the labels of the page being closed.
        labels = self.page_labels.get(self.page_no(), self.labels)
        self.multi_cell(self.epw, 3.8, self.clean(labels["footer"]), new_x="LMARGIN", new_y="NEXT", align="L")
        self.cell(0, 4, f"{labels['page']} {self.page_no()}/{{nb}}", align="R")
        self.set_text_color(0, 0, 0)


def _wrap(pdf: OnePager, text: str, width: float, max_lines: int) -> list[str]:
    lines = pdf.multi_cell(width, 4.4, pdf.clean(text), dry_run=True, output="LINES")
    if len(lines) > max_lines:
        lines = lines[: max_lines - 1] + [pdf.fit(" ".join(lines[max_lines - 1:]), width)]
    return lines or [""]


def _table_row(pdf: OnePager, widths, cells, line_h=4.4, max_lines=3, bottom=None, fill=False) -> bool:
    """cells: [(text, style, size, color)]. Draws one row with wrapped cells. False if it doesn't fit."""
    wrapped = []
    for w, (text, style, size, _) in zip(widths, cells):
        pdf.font(style, size)
        wrapped.append(_wrap(pdf, text, w - 2.4, max_lines))
    h = max(len(lines) for lines in wrapped) * line_h + 2.2
    if bottom is not None and pdf.get_y() + h > bottom:
        return False
    x, y = pdf.l_margin, pdf.get_y()
    for w, lines, (_, style, size, color) in zip(widths, wrapped, cells):
        pdf.rect(x, y, w, h, style="DF" if fill else "D")
        pdf.font(style, size)
        pdf.set_text_color(*color)
        for i, line in enumerate(lines):
            pdf.set_xy(x + 1.2, y + 1.1 + i * line_h)
            pdf.cell(w - 2.4, line_h, line)
        x += w
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(pdf.l_margin, y + h)
    return True


def _verdict(score) -> str:
    if not isinstance(score, (int, float)):
        return "at_risk"
    return "safe" if score >= 80 else "watch" if score >= 50 else "at_risk"


def _score_color(score) -> tuple:
    if not isinstance(score, (int, float)):
        return (90, 90, 90)
    return (185, 28, 28) if score < 50 else (180, 83, 9) if score < 80 else (27, 94, 32)


def _all_findings(devices: list, lang: str) -> list:
    rows = []
    for d in devices:
        label = d.get(f"type_label_{lang}") or d.get("type") or ""
        name = " ".join(x for x in (d.get("vendor") or "", label) if x).strip()
        for f in d.get("findings", []):
            rows.append({**f, "device_name": name or d.get("ip", "?"), "device_ip": d.get("ip", "?")})
    rows.sort(key=lambda f: (_SEV_ORDER.get(f.get("severity", "info"), 9), -(f.get("points") or 0), f["device_ip"]))
    return rows


def _page(pdf: OnePager, scan_data: dict, lang: str) -> None:
    t = _LABELS[lang]
    pdf.labels = t
    pdf.add_page()
    pdf.page_labels[pdf.page_no()] = t
    devices = scan_data.get("devices", [])
    score = scan_data.get("score")
    findings = _all_findings(devices, lang)
    stamp = str(scan_data.get("timestamp") or datetime.now().isoformat())[:16].replace("T", " ")

    # Title
    pdf.font("B", 17)
    pdf.cell(0, 9, pdf.clean(t["title"]), new_x="LMARGIN", new_y="NEXT")
    pdf.font("", 9.5)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 5, pdf.clean(f"{t['generated']}: {stamp}  ·  {len(devices)} {t['devices']}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, pdf.get_y() + 1.5, pdf.w - pdf.r_margin, pdf.get_y() + 1.5)
    pdf.ln(5)

    # Score block: official score (what the jury checks) + weighted score + counts
    top = pdf.get_y()
    color = _score_color(score)
    pdf.set_draw_color(*color)
    pdf.set_line_width(0.8)
    pdf.rect(pdf.l_margin, top, 58, 32)
    pdf.set_line_width(0.2)
    pdf.set_xy(pdf.l_margin, top + 2)
    pdf.font("B", 30)
    pdf.set_text_color(*color)
    pdf.cell(58, 14, pdf.clean(f"{score if score is not None else '-'}"), align="C", new_x="LEFT", new_y="NEXT")
    pdf.font("", 9)
    pdf.cell(58, 4.5, pdf.clean(f"{t['official']} · {t['of_100']}"), align="C", new_x="LEFT", new_y="NEXT")
    pdf.font("B", 10.5)
    pdf.cell(58, 6, pdf.clean(t["verdict"][_verdict(score)]), align="C")
    pdf.set_text_color(0, 0, 0)

    x2 = pdf.l_margin + 64
    w2 = pdf.epw - 64
    pdf.set_xy(x2, top + 1)
    if devices and score is not None:
        weighted = custom_risk_score(scan_data)["score"]
        pdf.font("B", 12)
        pdf.set_text_color(*_score_color(weighted))
        pdf.cell(w2, 6.5, pdf.clean(f"{t['weighted']}: {weighted}/100"), new_x="LEFT", new_y="NEXT")
        pdf.set_text_color(90, 90, 90)
        pdf.font("I", 8.5)
        pdf.cell(w2, 4.5, pdf.fit(t["weighted_note"], w2), new_x="LEFT", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
    pdf.ln(2)
    pdf.set_x(x2)
    pdf.font("B", 9.5)
    pdf.cell(w2, 5.5, pdf.clean(t["counts"]), new_x="LEFT", new_y="NEXT")
    counts = {s: sum(1 for f in findings if f.get("severity") == s) for s in ("high", "medium", "low", "info")}
    pdf.set_x(x2)
    col = w2 / 4
    for sev in ("high", "medium", "low", "info"):
        pdf.font("B", 14)
        pdf.set_text_color(*_SEV_COLORS[sev])
        pdf.cell(col, 7, str(counts[sev]), align="C")
    pdf.ln(7)
    pdf.set_x(x2)
    pdf.font("", 9)
    for sev in ("high", "medium", "low", "info"):
        pdf.set_text_color(*_SEV_COLORS[sev])
        pdf.cell(col, 4.5, pdf.clean(t["sev"][sev]), align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(pdf.l_margin, top + 37)

    # "Start with this": the single most urgent problem, in plain words, with its first steps
    pdf.font("B", 12.5)
    pdf.cell(0, 7, pdf.clean(t["start"]), new_x="LMARGIN", new_y="NEXT")
    if not findings:
        pdf.para(t["no_findings"], size=10.5)
    else:
        first = findings[0]
        tmpl = get_template(first["code"], lang) or {}
        box_top = pdf.get_y()
        pdf.set_x(pdf.l_margin + 4)
        sev = first.get("severity", "info")
        head = f"[{t['sev'][sev]}] {_SHORT_TITLE[lang].get(first['code'], first['code'])}: {first['device_name']} ({first['device_ip']})"
        pdf.para(head, size=11, style="B", color=_SEV_COLORS.get(sev, (0, 0, 0)), h=5.5, indent=4, max_lines=2)
        if tmpl.get("explanation"):
            pdf.para(tmpl["explanation"], size=10, indent=4, max_lines=3)
        for i, step in enumerate(tmpl.get("fix_steps", [])[:3], 1):
            pdf.para(f"{i}. {step}", size=10, indent=8, max_lines=2)
        pdf.set_draw_color(*_SEV_COLORS.get(sev, (0, 0, 0)))
        pdf.set_line_width(0.8)
        pdf.line(pdf.l_margin + 1, box_top, pdf.l_margin + 1, pdf.get_y())
        pdf.set_line_width(0.2)
    pdf.ln(4)

    # Table of every problem, sized to the space left above the footer
    if findings:
        pdf.font("B", 12.5)
        pdf.cell(0, 7, pdf.clean(f"{t['table']} ({len(findings)})"), new_x="LMARGIN", new_y="NEXT")
        widths = [20, 46, 52, 62]  # = 180 mm printable width
        bottom = pdf.h - 20
        pdf.set_fill_color(236, 240, 236)
        pdf.set_draw_color(200, 200, 200)
        _table_row(pdf, widths, [(c, "B", 9, (0, 0, 0)) for c in t["cols"]], max_lines=1, fill=True)
        for i, f in enumerate(findings):
            sev = f.get("severity", "info")
            tmpl = get_template(f["code"], lang) or {}
            port = f" :{f['port']}" if f.get("port") else ""
            cells = [
                (t["sev"][sev], "B", 9, _SEV_COLORS.get(sev, (0, 0, 0))),
                (f"{f['device_name']} {f['device_ip']}{port}", "", 9, (0, 0, 0)),
                (_SHORT_TITLE[lang].get(f["code"], f["code"]), "", 9, (0, 0, 0)),
                ((tmpl.get("fix_steps") or ["-"])[0], "", 9, (0, 0, 0)),
            ]
            remaining = len(findings) - i
            # keep room for the "+N more" line unless this is the last row
            limit = bottom if remaining == 1 else bottom - 7
            if not _table_row(pdf, widths, cells, bottom=limit):
                pdf.font("I", 9)
                pdf.cell(sum(widths), 6.5, pdf.clean(t["more"].format(n=remaining)), border=1)
                break


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
