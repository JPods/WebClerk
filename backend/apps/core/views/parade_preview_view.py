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


def _get_company_logo_url() -> str:
    """Pull company logo URL from Company Profile Setting."""
    try:
        from django.apps import apps as _apps
        Setting = _apps.get_model("core", "Setting")
        s = Setting.objects.filter(name="Company Profile", is_active=True).first()
        if s and isinstance(s.config, dict):
            logos = s.config.get("logos", {})
            logo = logos.get("primary", "") or logos.get("icon", "")
            if logo:
                # Ensure it starts with /
                return f"/{logo}" if not logo.startswith("/") else logo
    except Exception:
        pass
    return ""


def _fill_tokens(text: str, sample: dict) -> str:
    """Fill {{token}} and {{a.b}} from the sample record. An unknown token is left
    visible as [[token]] rather than blanked — a preview should show the gap."""
    import re as _re

    def one(match):
        path = match.group(1).strip()
        value = sample
        for part in path.split('.'):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return f'[[{path}]]'
        return '' if value is None else str(value)

    return _re.sub(r'\{\{([^}]+)\}\}', one, text or '')


def _render_raw_html(report, config: dict, sample: dict) -> str:
    """The sample data, pretty-printed. What Shift-click shows — the record behind
    the document, whether or not the document has a layout."""
    layout = ("form layout" if config.get("form")
              else "letter text" if config.get("body")
              else f"template pointer \u2192 {config.get('template')}" if config.get("template")
              else "no layout")
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
    <title>{report.name} — sample data</title>
    <style>
      body {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
              margin: 0; padding: 1.5em; background: #1B2631; color: #EAECEE;
              font-size: 12.5px; line-height: 1.55; }}
      h1 {{ font-family: Helvetica, Arial, sans-serif; font-size: 15px;
            margin: 0 0 .2em; color: #FFF; }}
      .meta {{ font-family: Helvetica, Arial, sans-serif; font-size: 12px;
               color: #85929E; margin-bottom: 1.4em; }}
      pre {{ margin: 0; white-space: pre-wrap; word-break: break-word; }}
      .k {{ color: #7FB3D5; }} .s {{ color: #A9DFBF; }} .n {{ color: #F7DC6F; }}
    </style></head><body>
    <h1>{report.name}</h1>
    <div class="meta">{report.model_name or '—'} · {report.category or 'report'} · {layout}</div>
    <pre>{_colorize_json(json.dumps(sample, indent=2))}</pre>
    </body></html>"""


def _colorize_json(text: str) -> str:
    """Keys, strings and numbers in three colors. Escapes first — sample data is
    data, not markup."""
    import html as _html
    import re as _re

    escaped = _html.escape(text)
    escaped = _re.sub(r'&quot;([^&]*?)&quot;(\s*:)', r'<span class="k">&quot;\1&quot;</span>\2', escaped)
    escaped = _re.sub(r'(:\s*)&quot;(.*?)&quot;', r'\1<span class="s">&quot;\2&quot;</span>', escaped)
    escaped = _re.sub(r'(:\s*)(-?\d+\.?\d*)', r'\1<span class="n">\2</span>', escaped)
    return escaped


def _render_letter_html(report, config: dict, sample: dict) -> str:
    """Letters and touch templates: subject + body with the tokens filled."""
    subject = _fill_tokens(config.get('subject') or report.name, sample)
    body = _fill_tokens(config.get('body') or '', sample)
    channel = config.get('channel') or 'letter'
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
    <title>{report.name} — Preview</title>
    <style>
      body {{ font-family: Georgia, serif; max-width: 6.5in; margin: 0 auto;
              padding: 0.75in 0.5in; color: #222; line-height: 1.5; }}
      .kind {{ font-family: Helvetica, sans-serif; font-size: 11px; letter-spacing: .08em;
               text-transform: uppercase; color: #888; margin-bottom: 1.5em; }}
      h1 {{ font-size: 18px; margin: 0 0 1.2em; }}
      .body {{ white-space: pre-wrap; }}
      .gap {{ background: #FDEDEC; }}
    </style></head><body>
    <div class="kind">{channel} · {report.category or 'letter'}</div>
    <h1>{subject}</h1>
    <div class="body">{body}</div>
    </body></html>"""


def _render_no_layout_html(report, config: dict, sample: dict) -> str:
    """No layout of any kind. Say what the record actually has — a dangling
    template name is the finding, and the sample data belongs below the fold,
    not dumped as if it were the document."""
    pointer = config.get('template')
    if pointer:
        what = (f'This report points at a template named '
                f'<code>{pointer}</code>, and nothing defines it. '
                'The layout has not been built yet.')
    elif config.get('action'):
        what = (f'This is an operation (<code>{config.get("action")}</code>), '
                'not a printed document.')
    else:
        what = 'This report has no layout and no template pointer — it is an empty shell.'

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
    <title>{report.name} — No layout</title>
    <style>
      body {{ font-family: Helvetica, Arial, sans-serif; max-width: 42em;
              margin: 0 auto; padding: 2.5em 1.5em; color: #222; }}
      h1 {{ font-size: 20px; margin: 0 0 .25em; }}
      .meta {{ color: #888; font-size: 13px; margin-bottom: 1.5em; }}
      .note {{ background: #FEF9E7; border: 1px solid #F9E79F; border-radius: 6px;
               padding: 1em 1.2em; line-height: 1.55; }}
      code {{ background: #EAECEE; padding: 1px 5px; border-radius: 3px; }}
      details {{ margin-top: 2em; }}
      summary {{ cursor: pointer; color: #555; font-size: 13px; }}
      pre {{ background: #F8F9F9; padding: 1em; overflow-x: auto;
             font-size: 12px; line-height: 1.45; }}
    </style></head><body>
    <h1>{report.name}</h1>
    <div class="meta">{report.model_name or '—'} · {report.category or 'report'}</div>
    <div class="note"><strong>No layout to show.</strong><br>{what}</div>
    <details><summary>Sample data this report would print from</summary>
    <pre>{json.dumps(sample, indent=2)}</pre></details>
    </body></html>"""


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
            logo_url = _get_company_logo_url()
            logo_html = (
                f'<img src="{logo_url}" alt="" style="height:48px; opacity:0.9" onerror="this.style.display=\'none\'">'
                if logo_url else ""
            )
            sections_html.append(f"""
            <div class="company-header">
                <div style="display:flex; justify-content:space-between; align-items:flex-start">
                    <div>
                        <h1>{title}</h1>
                        <div class="meta-label">Sample Data — Report Parade Preview</div>
                    </div>
                    {logo_html}
                </div>
            </div>""")

        elif stype == "address_blocks":
            cols_html = ""
            for col in section.get("columns", []):
                fields_html = ""
                for f in col.get("fields", []):
                    val = _resolve(sample, f["field"])
                    if val:
                        fmt = f.get("format", "")
                        if fmt == "date" and str(val).isdigit():
                            val = _date(val)
                        elif fmt == "currency":
                            val = _money(val)
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

        elif stype == "detail_fields":
            fields_html = ""
            for f in section.get("fields", []):
                val = _resolve(sample, f["field"])
                if val:
                    fields_html += f'<div style="margin:6px 0"><span class="meta-label">{f.get("label", "")}:</span> {val}</div>'
            if fields_html:
                sections_html.append(f'<div class="detail-fields" style="margin:12px 0; padding:12px; background:#fafafa; border-radius:4px">{fields_html}</div>')

        elif stype == "data_table":
            columns = section.get("columns", [])
            thead = "<tr>" + "".join(
                f'<th style="width:{c.get("width","auto")}; text-align:{c.get("align","left")}">{c.get("label","")}</th>'
                for c in columns
            ) + "</tr>"
            # Group by field if specified
            group_by = section.get("group_by", "")
            rows_data = sample.get("lines", [])
            if group_by:
                groups: dict = {}
                for row in rows_data:
                    key = _resolve(row, group_by) or "Other"
                    groups.setdefault(key, []).append(row)
            else:
                groups = {"": rows_data}
            rows = ""
            for group_name, group_rows in groups.items():
                if group_name and section.get("group_label"):
                    rows += f'<tr><td colspan="{len(columns)}" style="background:#e8e8e8; font-weight:700; padding:6px 10px">{section["group_label"]}: {group_name}</td></tr>'
                for ln in group_rows:
                    cells = ""
                    for c in columns:
                        val = _resolve(ln, c["field"])
                        fmt = c.get("format", "")
                        if fmt == "currency":
                            val = _money(val)
                        elif fmt == "number":
                            val = _qty(val)
                        align = c.get("align", "left")
                        cells += f'<td style="text-align:{align}">{val}</td>'
                    rows += f"<tr>{cells}</tr>"
                if group_name and section.get("group_subtotals"):
                    subtotals = ""
                    for c in columns:
                        fmt = c.get("format", "")
                        if fmt == "currency":
                            total = sum(float(_resolve(r, c["field"]) or 0) for r in group_rows)
                            subtotals += f'<td style="text-align:{c.get("align","right")}; font-weight:700; border-top:1px solid #999">{_money(total)}</td>'
                        elif c == columns[0]:
                            subtotals += f'<td style="font-weight:700; border-top:1px solid #999">Subtotal</td>'
                        else:
                            subtotals += '<td style="border-top:1px solid #999"></td>'
                    rows += f"<tr>{subtotals}</tr>"
            # Grand totals
            if section.get("grand_totals") and rows_data:
                grand = ""
                for c in columns:
                    fmt = c.get("format", "")
                    if fmt == "currency":
                        total = sum(float(_resolve(r, c["field"]) or 0) for r in rows_data)
                        grand += f'<td style="text-align:{c.get("align","right")}; font-weight:700; border-top:2px solid #333">{_money(total)}</td>'
                    elif c == columns[0]:
                        grand += f'<td style="font-weight:700; border-top:2px solid #333">Grand Total</td>'
                    else:
                        grand += '<td style="border-top:2px solid #333"></td>'
                rows += f"<tr>{grand}</tr>"
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
.line-items th {{ background: #3355FF; color: #fff; padding: 8px 10px; text-align: left; font-size: 9pt;
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

        # Filesystem fallback — check sample_data/ by model_name and report name
        if not sample:
            from pathlib import Path
            sample_dir = Path(__file__).resolve().parent.parent / "sample_data"
            # Try model_name first, then report name slug
            for candidate in [report.model_name, report.name.lower().replace(" ", "_")]:
                if not candidate:
                    continue
                sample_file = sample_dir / f"{candidate}.json"
                if sample_file.exists():
                    sample = json.loads(sample_file.read_text())
                    sample.pop("_meta", None)
                    break
            # For aging report: model is "customer" but file is "aging.json"
            if not sample and report.name and "aging" in report.name.lower():
                aging_file = sample_dir / "aging.json"
                if aging_file.exists():
                    sample = json.loads(aging_file.read_text())
                    sample.pop("_meta", None)

        if not sample:
            from common.api_responses import api_response
            return api_response(
                success=False, status_code=404,
                message=f"No sample data on report '{report.name}'",
            )

        # Shift-click asks for the data behind the document. Same endpoint, ?raw=1.
        if request.query_params.get("raw") in ("1", "true", "yes"):
            html = _render_raw_html(report, config, sample)
            response = HttpResponse(html, content_type="text/html")
            response["Disposition"] = "inline"
            return response

        body = config.get("body")
        if form:
            html = _render_sample_html(
                report.name, report.model_name or "", sample, form,
            )
        elif body:
            # Letters and touch templates are text with {{tokens}}, not layouts.
            # Filling the tokens from sample data is the real preview.
            html = _render_letter_html(report, config, sample)
        else:
            html = _render_no_layout_html(report, config, sample)

        response = HttpResponse(html, content_type="text/html")
        response["Content-Disposition"] = f'inline; filename="parade-{report.id}.html"'
        return response


class ParadeManifestView(APIView):
    """GET /wcapi/parade-manifest/ — returns the parade manifest for the React UI."""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from apps.core.services.report_parade import build_parade_manifest
        base_url = request.build_absolute_uri('/').rstrip('/')
        manifest = build_parade_manifest(base_url=base_url)
        from common.api_responses import api_response
        return api_response(success=True, data=manifest)


class ParadeFeedbackView(APIView):
    """POST /wcapi/parade-feedback/ — save user feedback on a report."""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        from apps.core.services.report_parade import save_parade_feedback
        report_id = request.data.get("report_id")
        feedback = request.data.get("feedback", "")
        notes = request.data.get("notes", "")
        if not report_id or not feedback:
            from common.api_responses import api_response
            return api_response(success=False, status_code=400, message="report_id and feedback required")
        ok = save_parade_feedback(report_id, feedback, notes, request.user.id)
        from common.api_responses import api_response
        if ok:
            return api_response(success=True, message="Feedback saved")
        return api_response(success=False, status_code=404, message="Report not found")
