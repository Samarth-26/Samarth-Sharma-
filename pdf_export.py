
from __future__ import annotations

import os
from datetime import datetime


def _safe(value: object) -> str:
    return str(value).encode("latin-1", "replace").decode("latin-1")


def generate_executive_pdf(entities: list[dict], brief: dict, alerts: list[dict], health: dict, output_path: str) -> str | None:
    try:
        from fpdf import FPDF
        pdf = FPDF(format="A4")
        pdf.set_auto_page_break(auto=True, margin=12)
        pdf.add_page()
        pdf.set_fill_color(15, 23, 42); pdf.rect(0, 0, 210, 297, "F")
        pdf.set_text_color(96, 165, 250); pdf.set_font("Helvetica", "B", 18)
        pdf.cell(190, 10, "Executive Daily Brief", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(148, 163, 184); pdf.set_font("Helvetica", size=9)
        pdf.cell(190, 6, _safe(datetime.now().strftime("Generated %d %b %Y, %H:%M")), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        pdf.set_text_color(248, 250, 252); pdf.set_font("Helvetica", "B", 11)
        pdf.cell(190, 7, "Run KPIs", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=10); pdf.multi_cell(190, 6, _safe(f"{len(entities)} extracted mentions | {len(set(e.get('name') for e in entities))} unique people | {health.get('status', 'Unknown')} pipeline"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 11); pdf.cell(190, 8, "Daily brief", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=10); pdf.multi_cell(190, 6, _safe(brief.get("text", "No brief available.")), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 11); pdf.cell(190, 8, "Trending alerts", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=10); pdf.multi_cell(190, 6, _safe("; ".join(f"{item['entity']} - {item['kind']} ({item['count']} mentions)" for item in alerts) or "No material entity anomalies detected."), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 11); pdf.cell(190, 8, "Channel health", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=9)
        for card in health.get("cards", []):
            pdf.multi_cell(190, 5, _safe(f"{card['feed']}: {card['fetched']}/{card['expected']} fetched | success {card['success_rate']}% | uptime {card['uptime']}%"), new_x="LMARGIN", new_y="NEXT")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        pdf.output(output_path)
        return output_path
    except Exception as exc:
        print(f"[PDF] Export unavailable: {exc}")
        return None
