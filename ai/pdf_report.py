"""PDF report generator for network scan results."""

from __future__ import annotations

import io
from datetime import datetime

from fpdf import FPDF

from ai.templates import get_template
from ai.assistant import get_risk_scenario, narrate_scan


class ScanReport(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "Network Security Report", new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "R Systems Hackathon 2026 - Secure Networks, Simply Explained", new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(3)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def _safe(text: str) -> str:
    if not text:
        return ""
    return text.encode("latin-1", "replace").decode("latin-1")


def generate_report(scan_data: dict, language: str = "ro") -> bytes:
    """Generate a PDF report from scan data. Returns PDF bytes."""
    pdf = ScanReport()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    devices = scan_data.get("devices", [])
    score = scan_data.get("score", "?")
    timestamp = scan_data.get("timestamp", datetime.now().isoformat())

    lbl = {
        "ro": {
            "generated": "Generat la",
            "score": "Scor de securitate",
            "of_100": "din 100",
            "summary": "Rezumat",
            "devices": "Dispozitive",
            "findings": "Probleme de securitate",
            "no_findings": "Nu au fost gasite probleme de securitate.",
            "severity": "Severitate",
            "port": "Port",
            "risk": "Ce s-ar putea intampla",
            "fix": "Cum rezolvi",
            "history": "Istoric scanuri",
        },
        "en": {
            "generated": "Generated at",
            "score": "Security score",
            "of_100": "out of 100",
            "summary": "Summary",
            "devices": "Devices",
            "findings": "Security findings",
            "no_findings": "No security issues were found.",
            "severity": "Severity",
            "port": "Port",
            "risk": "What could happen",
            "fix": "How to fix",
            "history": "Scan history",
        },
    }
    t = lbl.get(language, lbl["ro"])

    # Date
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _safe(f"{t['generated']}: {timestamp[:19]}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Score
    pdf.set_font("Helvetica", "B", 24)
    color = (220, 50, 50) if (isinstance(score, (int, float)) and score < 40) else (220, 160, 0) if (isinstance(score, (int, float)) and score < 70) else (50, 160, 80)
    pdf.set_text_color(*color)
    pdf.cell(0, 14, _safe(f"{score} {t['of_100']}"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, _safe(t["score"]), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    # Narrative summary
    narrative = narrate_scan(scan_data, language)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _safe(t["summary"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, _safe(narrative.get("narrative", "")))
    pdf.ln(5)

    # Devices table
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _safe(f"{t['devices']} ({len(devices)})"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)

    if devices:
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(35, 7, "IP", border=1, fill=True)
        type_label = "Tip" if language == "ro" else "Type"
        pdf.cell(35, 7, _safe(type_label), border=1, fill=True)
        pdf.cell(40, 7, "Vendor", border=1, fill=True)
        pdf.cell(40, 7, "Hostname", border=1, fill=True)
        ports_label = "Porturi" if language == "ro" else "Ports"
        pdf.cell(20, 7, _safe(ports_label), border=1, fill=True)
        issues_label = "Probleme" if language == "ro" else "Issues"
        pdf.cell(20, 7, _safe(issues_label), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)

        for d in devices:
            type_val = d.get("type_label_ro" if language == "ro" else "type_label_en", d.get("type", "?"))
            pdf.cell(35, 6, _safe(d.get("ip", "?")), border=1)
            pdf.cell(35, 6, _safe(str(type_val)[:20]), border=1)
            pdf.cell(40, 6, _safe((d.get("vendor") or "?")[:24]), border=1)
            pdf.cell(40, 6, _safe((d.get("hostname") or "-")[:24]), border=1)
            pdf.cell(20, 6, str(len(d.get("open_ports", []))), border=1)
            pdf.cell(20, 6, str(len(d.get("findings", []))), border=1, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)

    # Findings
    all_findings = []
    for d in devices:
        for f in d.get("findings", []):
            all_findings.append({**f, "device_ip": d.get("ip", "?"), "device_type": d.get("type", "unknown")})

    sev_order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    all_findings.sort(key=lambda f: sev_order.get(f.get("severity", "info"), 9))

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _safe(f"{t['findings']} ({len(all_findings)})"), new_x="LMARGIN", new_y="NEXT")

    if not all_findings:
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 8, _safe(t["no_findings"]), new_x="LMARGIN", new_y="NEXT")
    else:
        for f in all_findings:
            code = f.get("code", "?")
            severity = f.get("severity", "info")
            ip = f.get("device_ip", "?")
            port = f.get("port", "?")

            sev_colors = {"high": (220, 50, 50), "medium": (220, 160, 0), "low": (50, 120, 200), "info": (130, 130, 130)}

            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*sev_colors.get(severity, (0, 0, 0)))
            pdf.cell(0, 7, _safe(f"[{severity.upper()}] {code}"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)

            pdf.set_font("Helvetica", "", 9)
            pdf.cell(0, 5, _safe(f"{ip} - {t['port']} {port}"), new_x="LMARGIN", new_y="NEXT")

            tmpl = get_template(code, language)
            if tmpl:
                pdf.set_font("Helvetica", "", 10)
                pdf.multi_cell(0, 5, _safe(tmpl["explanation"]))

            scenario = get_risk_scenario(code, language)
            if scenario:
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(150, 100, 0)
                pdf.multi_cell(0, 5, _safe(f"{t['risk']}: {scenario}"))
                pdf.set_text_color(0, 0, 0)

            if tmpl and tmpl.get("fix_steps"):
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(0, 5, _safe(f"{t['fix']}:"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 9)
                for i, step in enumerate(tmpl["fix_steps"], 1):
                    pdf.multi_cell(0, 5, _safe(f"  {i}. {step}"))

            pdf.ln(2)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
