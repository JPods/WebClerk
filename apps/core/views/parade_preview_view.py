"""
Parade preview — renders a report with sample data as standalone HTML.

GET /wcapi/parade-preview/?report_id=72

Bypasses WeasyPrint — renders directly from config.sample_data
using the config.form layout definition. Lightweight, fast,
browser-native rendering for the parade onboarding flow.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


def _money(val) -> str:
    try:
        v = Decimal(str(val))
        return f"${v:,.2f}"
    except Exception:
        return str(val) if val is not None else ""


def _qty(val) -> str:
    try:
        v = Decimal(str(val))
        return str(int(v)) if v == int(v) else f"{v:,.2f}"
    except Exception:
        return str(val) if val is not None else ""


def _date(epoch_ms) -> str:
    if not epoch_ms:
        return ""
    try:
        return datetime.fromtimestamp(int(epoch_ms) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return str(epoch_ms)


def _safe(val, default="") -> str:
    return str(val) if val is not None else default


def _resolve(data: dict, field_path: str) -> str:
    """Resolve a dotted field path like 'config.ship_to.company' from nested dict."""
    parts = field_path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return ""
    return _safe(current)


def _render_sample_html(report_name: str, model_name: str, sample: dict, form: dict) -> str:
    """Render sample data using the config.form layout as standalone HTML."""

    # Extract contact name from refs
    refs = sample.get("refs", {})
    if isinstance(refs, dict):
        links = refs.get("links", {})
        if isinstance(links, dict):
            contact = links.get("contact", {})
            if isinstance(contact, dict):
                sample.setdefault("contact_name", contact.get("name", ""))

    title = form.get("title", report_name)
    sections_html = []

    for section in form.get("sections", []):
        stype = section.get("type", "")

        if stype == "company_header":
            sections_html.append(f"""
            <div class="company-header">
                <h1>{title}</h1>
                <div class="meta-label">Sample Data — Report Parade Preview</div>
            </div>""")

        elif stype == "address_blocks":
            cols_html = ""
            for col in section.get("columns", []):
                fields_html = ""
                for f in col.get("fields", []):
                    val = _resolve(sample, f["field"])
                    if val:
                        val_display = val.replace("\n", "<br>")
                        fields_html += f'<div><span class="meta-label">{f.get("label", "")}:</span> {val_display}</div>'
                cols_html += f'<div class="addr-col"><div class="addr-title">{col.get("title", "")}</div>{fields_html}</div>'
            sections_html.append(f'<div class="addr-row">{cols_html}</div>')

        elif stype == "meta_row":
            cells = ""
            for f in section.get("fields", []):
                val = _resolve(sample, f["field"])
                fmt = f.get("format", "")
                if fmt == "date":
                    val = _date(val) if val and str(val).isdigit() else val
                elif fmt == "currency":
                    val = _money(val)
                cells += f'<td><span class="meta-label">{f.get("label", "")}:</span> {val}</td>'
            sections_html.append(f'<table class="meta-table"><tr>{cells}</tr></table>')

        elif stype == "line_items":
            columns = section.get("columns", [])
            thead = "<tr>" + "".join(
                f'<th style="width:{c.get("width","auto")}; text-align:{c.get("align","left")}">{c.get("label","")}</th>'
                for c in columns
            ) + "</tr>"
            rows = ""
            for ln in sample.get("lines", []):
                cells = ""
                for c in columns:
                    val = _resolve(ln, c["field"])
                    fmt = c.get("format", "")
                    if fmt == "currency":
                        val = _money(val)
                    elif fmt == "number":
                        val = _qty(val)
                    elif fmt == "percent":
                        try:
                            val = f"{float(val):.1f}%" if val else ""
                        except (ValueError, TypeError):
                            pass
                    align = c.get("align", "left")
                    cells += f'<td style="text-align:{align}">{val}</td>'
                rows += f"<tr>{cells}</tr>"
            sections_html.append(f"""
            <table class="line-items">
                <thead>{thead}</thead>
                <tbody>{rows}</tbody>
            </table>""")

        elif stype == "comments":
            source = section.get("source", "comments.public")
            val = _resolve(sample, source)
            if val:
                label = section.get("label", "Comments")
                sections_html.append(f'<div class="comments"><strong>{label}:</strong> {val}</div>')

        elif stype == "totals":
            left = section.get("left_text", "")
            rows = ""
            for r in section.get("rows", []):
                val = _resolve(sample, r["field"])
                fmt = r.get("format", "")
                if fmt == "currency":
                    val = _money(val)
                bold = "font-weight:700;" if r.get("bold") or r.get("style") == "bold" else ""
                rows += f'<tr style="{bold}"><td>{r.get("label","")}</td><td class="r">{val}</td></tr>'
            left_html = f'<div class="totals-left">{left}</div>' if left else ""
            sections_html.append(f"""
            <div class="totals-section">
                {left_html}
                <table class="totals">{rows}</table>
            </div>""")

        elif stype == "conditions":
            val = _resolve(sample, section.get("source", "conditions_description"))
            if val:
                sections_html.append(f'<div class="conditions">{val}</div>')

        elif stype == "signature":
            preamble = section.get("preamble", "")
            blocks = ""
            for b in section.get("blocks", []):
                lines = "".join(f'<div class="sig-line">{l}</div>' for l in b.get("lines", []))
                blocks += f'<div class="sig-block"><div class="sig-label">{b.get("label","")}</div>{lines}</div>'
            sections_html.append(f"""
            <div class="signature">
                <p class="sig-preamble">{preamble}</p>
                <div class="sig-blocks">{blocks}</div>
            </div>""")

        elif stype == "footer":
            cells = " | ".join(
                f'{f.get("label","")}: {_resolve(sample, f["field"])}'
                for f in section.get("fields", [])
            )
            sections_html.append(f'<div class="footer">{cells}</div>')

    body = "\n".join(sections_html)

    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>{title} — Parade Preview</title>
<style>
@page {{ size: letter; margin: 0.75in 0.6in; }}
body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; font-size: 11pt;
       color: #222; line-height: 1.5; max-width: 800px; margin: 20px auto; padding: 20px; }}
.company-header {{ border-bottom: 2px solid #333; margin-bottom: 16px; padding-bottom: 8px; }}
.company-header h1 {{ margin: 0; font-size: 22pt; color: #111; }}
.meta-label {{ color: #666; font-size: 9pt; text-transform: uppercase; letter-spacing: 0.5px; }}
.addr-row {{ display: flex; gap: 40px; margin: 16px 0; }}
.addr-col {{ flex: 1; }}
.addr-title {{ font-weight: 700; border-bottom: 1px solid #ccc; margin-bottom: 6px; padding-bottom: 2px; }}
.meta-table {{ width: 100%; margin: 12px 0; background: #f8f8f8; border-radius: 4px; }}
.meta-table td {{ padding: 6px 12px; }}
.line-items {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
.line-items th {{ background: #333; color: #fff; padding: 8px 10px; text-align: left; font-size: 9pt;
                  text-transform: uppercase; letter-spacing: 0.5px; }}
.line-items td {{ padding: 8px 10px; border-bottom: 1px solid #e0e0e0; }}
.line-items tbody tr:hover {{ background: #f5f5f5; }}
.comments {{ margin: 16px 0; padding: 12px; background: #f0f7ff; border-left: 3px solid #2196F3; border-radius: 4px; }}
.totals-section {{ display: flex; justify-content: space-between; align-items: flex-start; margin: 16px 0; }}
.totals-left {{ flex: 1; color: #666; font-style: italic; padding-top: 8px; }}
.totals {{ min-width: 250px; }}
.totals td {{ padding: 4px 12px; }}
.totals .r {{ text-align: right; }}
.conditions {{ margin: 16px 0; padding: 12px; font-size: 9pt; color: #666; border-top: 1px solid #ddd; }}
.signature {{ margin: 24px 0; }}
.sig-preamble {{ font-size: 9pt; color: #666; }}
.sig-blocks {{ display: flex; gap: 40px; margin-top: 16px; }}
.sig-block {{ flex: 1; }}
.sig-label {{ font-weight: 700; margin-bottom: 8px; }}
.sig-line {{ border-bottom: 1px solid #999; padding: 20px 0 4px; font-size: 9pt; color: #888; }}
.footer {{ margin-top: 24px; padding-top: 8px; border-top: 1px solid #333; font-size: 9pt; color: #666; text-align: center; }}
</style>
</head>
<body>
{body}
</body></html>"""


class ParadePreviewView(APIView):
    """Render a report with its sample data as standalone HTML for the parade."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from apps.core.models import Report

        report_id = request.query_params.get("report_id")
        if not report_id:
            from common.api_responses import api_response
            return api_response(
                success=False, status_code=400,
                message="'report_id' query parameter is required",
            )

        try:
            report_id = int(report_id)
        except (ValueError, TypeError):
            from common.api_responses import api_response
            return api_response(
                success=False, status_code=400,
                message="'report_id' must be an integer",
            )

        report = Report.objects.filter(
            id=report_id, is_active=True, is_deleted=False,
        ).first()
        if not report:
            from common.api_responses import api_response
            return api_response(
                success=False, status_code=404,
                message=f"Report id={report_id} not found",
            )

        config = report.config or {}
        sample = config.get("sample_data")
        form = config.get("form")

        if not sample:
            from common.api_responses import api_response
            return api_response(
                success=False, status_code=404,
                message=f"No sample data on report '{report.name}'",
            )

        if not form:
            # No form layout — render a simple data dump
            html = f"""<!DOCTYPE html><html><head>
            <meta charset="utf-8"><title>{report.name} — Sample Data</title>
            <style>body {{ font-family: monospace; padding: 20px; }} pre {{ white-space: pre-wrap; }}</style>
            </head><body>
            <h2>{report.name}</h2>
            <p>Model: {report.model_name} | Category: {report.category or 'report'}</p>
            <p><em>No form layout defined — showing raw sample data:</em></p>
            <pre>{json.dumps(sample, indent=2)}</pre>
            </body></html>"""
        else:
            html = _render_sample_html(
                report.name, report.model_name or "", sample, form,
            )

        response = HttpResponse(html, content_type="text/html")
        response["Content-Disposition"] = f'inline; filename="parade-{report.id}.html"'
        return response
