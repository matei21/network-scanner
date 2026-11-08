"""PDF report generator for network scan results.

Layout rules that keep everything inside the page:
  - paragraphs always use multi_cell with the full printable width and return to the left margin
    (fpdf2's default leaves the cursor at the right edge, which pushed later text off the page);
  - table cells are trimmed by measured text width, not by character count;
  - a Unicode TTF font is used when available so Romanian diacritics and arrows print correctly.
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

from ai.templates import get_template
from ai.assistant import custom_risk_score, get_risk_scenario, narrate_scan
from ai.fix_commands import FIX_COMMANDS

_FONT_CANDIDATES = [
    (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf"), Path("C:/Windows/Fonts/ariali.ttf")),
    (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
     Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf")),
]

_SEV_COLORS = {"high": (200, 40, 40), "medium": (190, 120, 0), "low": (40, 100, 190), "info": (110, 110, 110)}
_SEV_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}

_LABELS = {
    "ro": {
        "title": "Raport de securitate a retelei",
        "subtitle": "R Systems Hackathon 2026 - Secure Networks, Simply Explained",
        "generated": "Generat la", "score": "Scor de securitate (oficial)", "of_100": "din 100",
        "weighted": "Scor ponderat", "weighted_note": "Scorul oficial ajustat dupa context (limitat la -30 / +10 puncte).",
        "start": "Punct de plecare", "official": "= scor oficial", "summary": "Rezumat", "devices": "Dispozitive",
        "findings": "Probleme de securitate", "no_findings": "Nu au fost gasite probleme de securitate.",
        "port": "port", "risk": "Ce s-ar putea intampla", "fix": "Cum rezolvi", "where": "Unde se schimba",
        "evidence": "Dovada", "page": "Pagina",
        "cols": ("IP", "Tip", "Producator", "Nume", "Porturi", "Probleme"),
        "rows": {
            "findings": "Probleme gasite", "device_weight": "Importanta dispozitivelor afectate",
            "density": "Multe probleme pe acelasi dispozitiv", "combo": "Combinatie periculoasa",
            "systemic": "Probleme pe majoritatea dispozitivelor", "gateway_high": "Problema grava pe router",
            "cap": "Limita ajustarilor",
        },
    },
    "en": {
        "title": "Network Security Report",
        "subtitle": "R Systems Hackathon 2026 - Secure Networks, Simply Explained",
        "generated": "Generated at", "score": "Security score (official)", "of_100": "out of 100",
        "weighted": "Weighted score", "weighted_note": "The official score adjusted for context (limited to -30 / +10 points).",
        "start": "Starting point", "official": "= official score", "summary": "Summary", "devices": "Devices",
        "findings": "Security findings", "no_findings": "No security issues were found.",
        "port": "port", "risk": "What could happen", "fix": "How to fix", "where": "Where to change it",
        "evidence": "Evidence", "page": "Page",
        "cols": ("IP", "Type", "Vendor", "Name", "Ports", "Issues"),
        "rows": {
            "findings": "Findings", "device_weight": "Importance of affected devices",
            "density": "Many issues on one device", "combo": "Dangerous combination",
            "systemic": "Issues on most devices", "gateway_high": "Serious issue on the router",
            "cap": "Adjustment limit",
        },
    },
}


class ScanReport(FPDF):
    def __init__(self, labels: dict):
        super().__init__(format="A4")
        self.labels = labels
        self.font_name = "Helvetica"
        self.unicode = False
        for regular, bold, italic in _FONT_CANDIDATES:
            if regular.exists() and bold.exists() and italic.exists():
                self.add_font("Body", "", str(regular))
                self.add_font("Body", "B", str(bold))
                self.add_font("Body", "I", str(italic))
                self.font_name, self.unicode = "Body", True
                break
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=18)

    def clean(self, value) -> str:
        value = "" if value is None else str(value)
        if self.unicode:
            return value
        return value.replace("→", "->").replace("—", "-").encode("latin-1", "replace").decode("latin-1")

    def font(self, style: str = "", size: float = 10):
        self.set_font(self.font_name, style, size)

    def header(self):
        self.font("B", 14)
        self.cell(0, 8, self.clean(self.labels["title"]), new_x="LMARGIN", new_y="NEXT", align="C")
        self.font("", 8.5)
        self.set_text_color(90, 90, 90)
        self.cell(0, 5, self.clean(self.labels["subtitle"]), new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_text_color(0, 0, 0)
        self.set_draw_color(200, 200, 200)
        self.line(self.l_margin, self.get_y() + 2, self.w - self.r_margin, self.get_y() + 2)
        self.ln(6)

    def footer(self):
        self.set_y(-12)
        self.font("I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, f"{self.labels['page']} {self.page_no()}/{{nb}}", align="C")
        self.set_text_color(0, 0, 0)

    # ── layout helpers ──
    def para(self, value, size=10, style="", color=(0, 0, 0), h=5.0, indent=0.0):
        self.font(style, size)
        self.set_text_color(*color)
        self.set_x(self.l_margin + indent)
        self.multi_cell(self.epw - indent, h, self.clean(value), new_x="LMARGIN", new_y="NEXT", align="L")
        self.set_text_color(0, 0, 0)

    def heading(self, value, size=13):
        if self.get_y() > self.h - 40:
            self.add_page()
        self.ln(2)
        self.font("B", size)
        self.cell(0, 8, self.clean(value), new_x="LMARGIN", new_y="NEXT")

    def fit(self, value, width) -> str:
        """Trim text with an ellipsis so it fits in `width` mm at the current font."""
        value = self.clean(value)
        if self.get_string_width(value) <= width - 2:
            return value
        while value and self.get_string_width(value + "...") > width - 2:
            value = value[:-1]
        return value + "..."


def _two_cols(pdf: ScanReport, left: str, right: str, **kw):
    """Label on the left (wraps), number right-aligned; works across page breaks."""
    size = kw.get("size", 9.5)
    pdf.font("B" if kw.get("bold") else "", size)
    right_w = 22.0
    lines = pdf.multi_cell(pdf.epw - right_w, 5, pdf.clean(left), dry_run=True, output="LINES", align="L")
    needed = 5 * max(1, len(lines))
    if pdf.get_y() + needed > pdf.h - pdf.b_margin:
        pdf.add_page()
    y = pdf.get_y()
    pdf.set_text_color(*kw.get("color", (0, 0, 0)))
    pdf.multi_cell(pdf.epw - right_w, 5, pdf.clean(left), new_x="LMARGIN", new_y="NEXT", align="L")
    end_y = pdf.get_y()
    pdf.set_xy(pdf.l_margin + pdf.epw - right_w, y)
    pdf.set_text_color(*kw.get("right_color", kw.get("color", (0, 0, 0))))
    pdf.cell(right_w, 5, pdf.clean(right), align="R")
    pdf.set_xy(pdf.l_margin, end_y)
    pdf.set_text_color(0, 0, 0)


def _score_color(score) -> tuple:
    if not isinstance(score, (int, float)):
        return (90, 90, 90)
    return (200, 40, 40) if score < 40 else (190, 120, 0) if score < 70 else (40, 140, 70)


def generate_report(scan_data: dict, language: str = "ro") -> bytes:
    """Generate a PDF report from scan data. Returns PDF bytes."""
    lang = "en" if language == "en" else "ro"
    t = _LABELS[lang]
    pdf = ScanReport(t)
    pdf.alias_nb_pages()
    pdf.add_page()

    devices = scan_data.get("devices", [])
    score = scan_data.get("score")
    timestamp = str(scan_data.get("timestamp") or datetime.now().isoformat())

    pdf.para(f"{t['generated']}: {timestamp[:19].replace('T', ' ')}", size=9.5, color=(80, 80, 80))
    pdf.ln(2)

    # Official score
    pdf.font("B", 26)
    pdf.set_text_color(*_score_color(score))
    pdf.cell(0, 13, pdf.clean(f"{score if score is not None else '-'} {t['of_100']}"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.font("", 10.5)
    pdf.cell(0, 6, pdf.clean(t["score"]), new_x="LMARGIN", new_y="NEXT", align="C")

    # Weighted score with its breakdown
    if devices and score is not None:
        risk = custom_risk_score(scan_data)
        pdf.heading(f"{t['weighted']}: {risk['score']}/100")
        pdf.para(t["weighted_note"], size=9, color=(80, 80, 80))
        pdf.ln(1)
        _two_cols(pdf, t["start"], "100")
        official = 100
        for item in risk["breakdown"]:
            label = t["rows"].get(item["key"], item["key"])
            if item["key"] == "findings":
                label += f" ({item['detail']})"
            elif item.get("detail") and item["key"] != "cap":
                label += f": {item['detail']}"
            delta = item["delta"]
            color = (200, 40, 40) if delta < 0 else (40, 140, 70)
            _two_cols(pdf, label, f"{delta:+d}", right_color=color)
            if item["key"] == "findings":
                official += delta
                _two_cols(pdf, t["official"], str(max(0, official)), color=(90, 90, 90))
        _two_cols(pdf, t["weighted"], f"{risk['score']}/100", bold=True, right_color=_score_color(risk["score"]))

    # Narrative summary
    pdf.heading(t["summary"])
    pdf.para(narrate_scan(scan_data, lang).get("narrative", ""), size=10)

    # Devices table
    pdf.heading(f"{t['devices']} ({len(devices)})")
    if devices:
        widths = [28, 34, 42, 40, 18, 18]  # = 180 mm, the printable width of A4 with 15 mm margins
        pdf.set_fill_color(235, 240, 235)
        pdf.font("B", 9)
        for w, col in zip(widths, t["cols"]):
            pdf.cell(w, 7, pdf.fit(col, w), border=1, fill=True)
        pdf.ln(7)
        pdf.font("", 9)
        for d in devices:
            if pdf.get_y() > pdf.h - 25:
                pdf.add_page()
            values = [
                d.get("ip", "?"),
                d.get(f"type_label_{lang}") or d.get("type") or "?",
                d.get("vendor") or "?",
                d.get("hostname") or "-",
                str(len(d.get("open_ports", []))),
                str(len(d.get("findings", []))),
            ]
            for w, v in zip(widths, values):
                pdf.cell(w, 6, pdf.fit(v, w), border=1)
            pdf.ln(6)

    # Findings
    all_findings = [
        {**f, "device_ip": d.get("ip", "?"), "device_label": d.get(f"type_label_{lang}") or d.get("type") or ""}
        for d in devices for f in d.get("findings", [])
    ]
    all_findings.sort(key=lambda f: (_SEV_ORDER.get(f.get("severity", "info"), 9), -(f.get("points") or 0)))

    pdf.heading(f"{t['findings']} ({len(all_findings)})")
    if not all_findings:
        pdf.para(t["no_findings"], style="I")
    for f in all_findings:
        code = f.get("code", "?")
        severity = f.get("severity", "info")
        if pdf.get_y() > pdf.h - 50:
            pdf.add_page()
        pdf.ln(2)
        pdf.para(f"[{severity.upper()}] {code}", size=11, style="B", color=_SEV_COLORS.get(severity, (0, 0, 0)), h=6)
        where = f"{f['device_label']} {f['device_ip']}" + (f" - {t['port']} {f['port']}" if f.get("port") else "")
        pdf.para(where, size=9, color=(80, 80, 80))

        tmpl = get_template(code, lang)
        if tmpl:
            pdf.para(tmpl["explanation"], size=10)
        scenario = get_risk_scenario(code, lang)
        if scenario:
            pdf.para(f"{t['risk']}: {scenario}", size=9, style="I", color=(150, 95, 0))
        if f.get("evidence"):
            pdf.para(f"{t['evidence']}: {f['evidence']}", size=8.5, color=(100, 100, 100))
        if tmpl and tmpl.get("fix_steps"):
            pdf.para(f"{t['fix']}:", size=9.5, style="B")
            for i, step in enumerate(tmpl["fix_steps"], 1):
                pdf.para(f"{i}. {step}", size=9.5, indent=4)
        hint = FIX_COMMANDS.get(code, {}).get("menu_hint", {}).get(lang)
        if hint:
            pdf.para(f"{t['where']}: {hint}", size=9, color=(40, 80, 140), indent=4)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
