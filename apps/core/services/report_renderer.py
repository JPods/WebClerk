"""
PDF report rendering service for WebClerk3.

Renders the 239 report definitions stored in the ``reports`` table as PDF
documents via WeasyPrint.  Eight built-in HTML templates cover the most
common commerce documents; reports whose ``data.template`` key does not
match a built-in fall back to a generic table layout.

Public API
----------
render_report(report_name, model_name, record_id, filters, fmt)
    → dict  {pdf_bytes, filename, pages}

get_available_reports(model_name)
    → list[dict]

render_report_action(report_name, model_name, record_id, filters, fmt)
    → dict  metadata only (for manage endpoint)
"""
from __future__ import annotations

import io
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.apps import apps as django_apps
from django.db.models import Q

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _money(val) -> str:
    """Format a numeric value as currency string."""
    try:
        v = Decimal(str(val))
        return f"${v:,.2f}"
    except Exception:
        return str(val) if val is not None else ""


def _qty(val) -> str:
    try:
        v = Decimal(str(val))
        if v == int(v):
            return str(int(v))
        return f"{v:,.2f}"
    except Exception:
        return str(val) if val is not None else ""


def _date_str(epoch_ms) -> str:
    """Convert epoch-millisecond int to YYYY-MM-DD string."""
    if not epoch_ms:
        return ""
    try:
        ts = int(epoch_ms) / 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return str(epoch_ms)


def _safe(val, default="") -> str:
    if val is None:
        return default
    return str(val)


def _get_company_info() -> Dict[str, str]:
    """Pull company info from the primary_organization Setting if available."""
    try:
        Setting = django_apps.get_model("core", "Setting")
        qs = Setting.objects.filter(
            Q(name__icontains="primary_organization") | Q(name__icontains="company"),
            is_active=True,
        ).first()
        if qs and hasattr(qs, "data") and isinstance(qs.data, dict):
            return qs.data
    except Exception:
        pass
    return {"name": ""}


def _get_model_class(model_name: str):
    """Resolve a model class from a slug using the wcapi registry."""
    try:
        from apps.core.services.wcapi_registry import get_model
        return get_model(model_name)
    except Exception:
        return None


def _get_line_model(model_name: str):
    """Given 'invoice', return the InvoiceLine model if it exists."""
    line_key = f"{model_name}_line"
    cls = _get_model_class(line_key)
    if cls:
        return cls
    # Try without underscore
    cls = _get_model_class(f"{model_name}line")
    return cls


def _extract_line_fields(line) -> Dict[str, Any]:
    """Pull useful display fields from a transaction line record."""
    item_data = getattr(line, "item", None) or {}
    qty_data = getattr(line, "quantity", None) or {}
    price_data = getattr(line, "price", None) or {}
    cost_data = getattr(line, "cost", None) or {}
    tax_data = getattr(line, "tax", None) or {}
    physical_data = getattr(line, "physical", None) or {}
    commission_data = getattr(line, "commission", None) or {}

    if isinstance(item_data, dict):
        item_name = item_data.get("name", "") or item_data.get("description", "")
        item_number = item_data.get("number", "") or item_data.get("ida", "")
    else:
        item_name = ""
        item_number = ""

    qty_ordered = qty_data.get("ordered", 0) if isinstance(qty_data, dict) else 0
    qty_shipped = qty_data.get("shipped", 0) if isinstance(qty_data, dict) else 0

    unit_price = price_data.get("unit", 0) if isinstance(price_data, dict) else 0
    extended = price_data.get("extended", 0) if isinstance(price_data, dict) else 0
    discount_pct = price_data.get("discount_pct", 0) if isinstance(price_data, dict) else 0

    unit_cost = cost_data.get("unit", 0) if isinstance(cost_data, dict) else 0
    extended_cost = cost_data.get("extended", 0) if isinstance(cost_data, dict) else 0

    tax_amount = tax_data.get("amount", 0) if isinstance(tax_data, dict) else 0

    weight = physical_data.get("weight", "") if isinstance(physical_data, dict) else ""
    country_of_origin = physical_data.get("country_of_origin", "") if isinstance(physical_data, dict) else ""
    hs_code = physical_data.get("hs_code", "") if isinstance(physical_data, dict) else ""

    comm_rate = commission_data.get("rate", 0) if isinstance(commission_data, dict) else 0
    comm_amount = commission_data.get("amount", 0) if isinstance(commission_data, dict) else 0

    bin_location = item_data.get("bin", "") if isinstance(item_data, dict) else ""

    return {
        "line_number": getattr(line, "line_number", ""),
        "item_number": item_number,
        "item_name": item_name,
        "qty_ordered": qty_ordered,
        "qty_shipped": qty_shipped,
        "unit_price": unit_price,
        "extended": extended,
        "discount_pct": discount_pct,
        "unit_cost": unit_cost,
        "extended_cost": extended_cost,
        "tax_amount": tax_amount,
        "weight": weight,
        "country_of_origin": country_of_origin,
        "hs_code": hs_code,
        "comm_rate": comm_rate,
        "comm_amount": comm_amount,
        "bin_location": bin_location,
    }


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def _load_single_record(model_name: str, record_id: int) -> Dict[str, Any]:
    """Load a single record + its lines (if line model exists)."""
    model_cls = _get_model_class(model_name)
    if not model_cls:
        raise ValueError(f"Unknown model: {model_name}")

    record = model_cls.objects.filter(id=record_id).first()
    if not record:
        raise ValueError(f"{model_name} id={record_id} not found")

    data = {
        "record": record,
        "ida": getattr(record, "ida", ""),
        "status": getattr(record, "status", ""),
        "dt_created": _date_str(getattr(record, "dt_created", None)),
        "address_full": getattr(record, "address_full", "") or "",
        "attention": getattr(record, "attention", "") or "",
        "email": getattr(record, "email", "") or "",
        "phone": getattr(record, "phone", "") or "",
        "terms": getattr(record, "terms", "") or "",
        "conditions_description": getattr(record, "conditions_description", "") or "",
        "total": getattr(record, "total", 0) or 0,
        "balance": getattr(record, "balance", 0) or 0,
        "totals": getattr(record, "totals", {}) or {},
        "sell": getattr(record, "sell", {}) or {},
        "cost": getattr(record, "cost", {}) or {},
        "finance": getattr(record, "finance", {}) or {},
        "flow": getattr(record, "flow", {}) or {},
        "source": getattr(record, "source", {}) or {},
        "refs": getattr(record, "refs", {}) or {},
        "metadata": getattr(record, "metadata", {}) or {},
    }

    # Load contact name from refs
    refs = data["refs"]
    if isinstance(refs, dict):
        links = refs.get("links", {})
        if isinstance(links, dict):
            contact_link = links.get("contact", {})
            if isinstance(contact_link, dict):
                data["contact_name"] = contact_link.get("name", "")
            else:
                data["contact_name"] = ""
        else:
            data["contact_name"] = ""
    else:
        data["contact_name"] = ""

    # Load lines
    line_cls = _get_line_model(model_name)
    lines = []
    if line_cls:
        fk_field = f"{model_name}_id"
        filter_kwargs = {fk_field: record_id}
        try:
            line_qs = line_cls.objects.filter(**filter_kwargs).order_by("line_number")
            lines = [_extract_line_fields(ln) for ln in line_qs]
        except Exception as e:
            logger.warning("Failed to load lines for %s/%s: %s", model_name, record_id, e)

    data["lines"] = lines
    return data


def _load_list_data(model_name: str, filters: Optional[Dict] = None) -> List[Dict]:
    """Load a list of records with optional filters."""
    model_cls = _get_model_class(model_name)
    if not model_cls:
        raise ValueError(f"Unknown model: {model_name}")

    qs = model_cls.objects.filter(is_active=True, is_deleted=False)

    if filters:
        for key, val in filters.items():
            if key.startswith("dt_") and isinstance(val, str):
                # Support date range filters like dt_created__gte
                try:
                    qs = qs.filter(**{key: val})
                except Exception:
                    pass
            else:
                qs = qs.filter(**{key: val})

    return list(qs[:5000])  # Safety cap


# ---------------------------------------------------------------------------
# Base CSS
# ---------------------------------------------------------------------------

_BASE_CSS = """
@page {
    size: letter;
    margin: 0.75in 0.6in;
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 8pt;
        color: #888;
    }
}
body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 10pt;
    color: #222;
    line-height: 1.4;
    margin: 0;
    padding: 0;
}
.header {
    margin-bottom: 18pt;
    border-bottom: 2px solid #333;
    padding-bottom: 8pt;
}
.company-name {
    font-size: 16pt;
    font-weight: bold;
    color: #111;
}
.company-detail {
    font-size: 8pt;
    color: #555;
}
.doc-title {
    font-size: 14pt;
    font-weight: bold;
    margin: 12pt 0 6pt 0;
    color: #333;
}
.doc-number {
    font-size: 11pt;
    color: #555;
    margin-bottom: 10pt;
}
.address-block {
    margin-bottom: 10pt;
    line-height: 1.5;
}
.address-label {
    font-size: 8pt;
    font-weight: bold;
    color: #888;
    text-transform: uppercase;
    margin-bottom: 2pt;
}
.meta-table {
    width: 100%;
    margin-bottom: 12pt;
}
.meta-table td {
    vertical-align: top;
    padding: 2pt 8pt 2pt 0;
}
.meta-label {
    font-weight: bold;
    color: #555;
    font-size: 9pt;
    width: 100pt;
}
table.data-table {
    width: 100%;
    border-collapse: collapse;
    margin: 10pt 0;
}
table.data-table th {
    background: #f0f0f0;
    border-bottom: 2px solid #999;
    padding: 5pt 6pt;
    text-align: left;
    font-size: 9pt;
    font-weight: bold;
    color: #333;
}
table.data-table td {
    border-bottom: 1px solid #ddd;
    padding: 4pt 6pt;
    font-size: 9pt;
}
table.data-table tr:last-child td {
    border-bottom: 2px solid #999;
}
.text-right { text-align: right; }
.text-center { text-align: center; }
.totals-section {
    margin-top: 8pt;
    float: right;
    width: 250pt;
}
.totals-section table {
    width: 100%;
    border-collapse: collapse;
}
.totals-section td {
    padding: 3pt 6pt;
    font-size: 10pt;
}
.totals-section .total-row {
    font-weight: bold;
    font-size: 11pt;
    border-top: 2px solid #333;
}
.footer {
    margin-top: 20pt;
    font-size: 8pt;
    color: #888;
    border-top: 1px solid #ddd;
    padding-top: 6pt;
}
.clearfix::after {
    content: "";
    display: table;
    clear: both;
}
.no-prices .price-col { display: none; }
"""


# ---------------------------------------------------------------------------
# Template: shared header
# ---------------------------------------------------------------------------

def _render_header(company: Dict, doc_title: str, doc_number: str = "",
                   doc_date: str = "") -> str:
    co_name = company.get("name", "") or ""
    co_addr = company.get("address", "") or ""
    co_phone = company.get("phone", "") or ""
    co_email = company.get("email", "") or ""
    detail_parts = [p for p in [co_addr, co_phone, co_email] if p]
    detail_line = " &nbsp;|&nbsp; ".join(detail_parts) if detail_parts else ""

    num_line = ""
    if doc_number:
        num_line = f'<div class="doc-number">#{doc_number}'
        if doc_date:
            num_line += f' &nbsp;&mdash;&nbsp; {doc_date}'
        num_line += '</div>'

    return f"""
    <div class="header">
        <div class="company-name">{co_name}</div>
        <div class="company-detail">{detail_line}</div>
    </div>
    <div class="doc-title">{doc_title}</div>
    {num_line}
    """


# ---------------------------------------------------------------------------
# Template 1: Invoice
# ---------------------------------------------------------------------------

def _template_invoice(data: Dict, company: Dict) -> str:
    header = _render_header(company, "Invoice", data.get("ida", ""),
                            data.get("dt_created", ""))

    totals = data.get("totals", {}) or {}
    subtotal = totals.get("subtotal", data.get("total", 0))
    tax = totals.get("tax", 0)
    shipping = totals.get("shipping", 0)
    total = totals.get("total", data.get("total", 0))
    balance = data.get("balance", 0)

    addr = data.get("address_full", "").replace("\n", "<br>") if data.get("address_full") else ""

    rows = ""
    for ln in data.get("lines", []):
        rows += f"""<tr>
            <td>{_safe(ln['item_number'])}</td>
            <td>{_safe(ln['item_name'])}</td>
            <td class="text-right">{_qty(ln['qty_ordered'])}</td>
            <td class="text-right">{_money(ln['unit_price'])}</td>
            <td class="text-right">{_money(ln['extended'])}</td>
        </tr>"""

    return f"""<!DOCTYPE html><html><head><style>{_BASE_CSS}</style></head><body>
    {header}
    <table class="meta-table"><tr>
        <td style="width:50%">
            <div class="address-label">Bill To</div>
            <div class="address-block">
                <strong>{_safe(data.get('contact_name'))}</strong><br>
                {_safe(data.get('attention'))}<br>
                {addr}
            </div>
        </td>
        <td>
            <table>
                <tr><td class="meta-label">Terms:</td><td>{_safe(data.get('terms'))}</td></tr>
                <tr><td class="meta-label">Status:</td><td>{_safe(data.get('status'))}</td></tr>
                <tr><td class="meta-label">Phone:</td><td>{_safe(data.get('phone'))}</td></tr>
                <tr><td class="meta-label">Email:</td><td>{_safe(data.get('email'))}</td></tr>
            </table>
        </td>
    </tr></table>

    <table class="data-table">
        <thead><tr>
            <th style="width:15%">Item #</th>
            <th>Description</th>
            <th class="text-right" style="width:10%">Qty</th>
            <th class="text-right" style="width:12%">Unit Price</th>
            <th class="text-right" style="width:14%">Extended</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>

    <div class="clearfix">
        <div class="totals-section">
            <table>
                <tr><td>Subtotal:</td><td class="text-right">{_money(subtotal)}</td></tr>
                <tr><td>Tax:</td><td class="text-right">{_money(tax)}</td></tr>
                <tr><td>Shipping:</td><td class="text-right">{_money(shipping)}</td></tr>
                <tr class="total-row"><td>Total:</td><td class="text-right">{_money(total)}</td></tr>
                <tr><td>Balance Due:</td><td class="text-right">{_money(balance)}</td></tr>
            </table>
        </div>
    </div>

    <div class="footer">
        {_safe(data.get('conditions_description'))}
    </div>
    </body></html>"""


# ---------------------------------------------------------------------------
# Template 2: Pick List
# ---------------------------------------------------------------------------

def _template_pick_list(data: Dict, company: Dict) -> str:
    header = _render_header(company, "Pick / Pull Request", data.get("ida", ""),
                            data.get("dt_created", ""))

    rows = ""
    for ln in data.get("lines", []):
        rows += f"""<tr>
            <td>{_safe(ln['item_number'])}</td>
            <td>{_safe(ln['item_name'])}</td>
            <td>{_safe(ln['bin_location'])}</td>
            <td class="text-right">{_qty(ln['qty_ordered'])}</td>
            <td class="text-center" style="width:60pt">&#9744;</td>
        </tr>"""

    return f"""<!DOCTYPE html><html><head><style>{_BASE_CSS}</style></head><body>
    {header}
    <table class="meta-table"><tr>
        <td><span class="meta-label">Order:</span> {_safe(data.get('ida'))}</td>
        <td><span class="meta-label">Customer:</span> {_safe(data.get('contact_name'))}</td>
        <td><span class="meta-label">Date:</span> {_safe(data.get('dt_created'))}</td>
    </tr></table>

    <table class="data-table">
        <thead><tr>
            <th style="width:15%">Item #</th>
            <th>Description</th>
            <th style="width:12%">Bin</th>
            <th class="text-right" style="width:10%">Qty</th>
            <th class="text-center" style="width:10%">Picked</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>

    <div class="footer">
        <strong>Picked by:</strong> _________________ &nbsp;&nbsp;
        <strong>Date:</strong> _________________ &nbsp;&nbsp;
        <strong>Checked by:</strong> _________________
    </div>
    </body></html>"""


# ---------------------------------------------------------------------------
# Template 3: Packing Slip
# ---------------------------------------------------------------------------

def _template_packing_slip(data: Dict, company: Dict) -> str:
    header = _render_header(company, "Packing Slip", data.get("ida", ""),
                            data.get("dt_created", ""))

    addr = data.get("address_full", "").replace("\n", "<br>") if data.get("address_full") else ""

    rows = ""
    for ln in data.get("lines", []):
        shipped = ln.get("qty_shipped") or ln.get("qty_ordered", 0)
        rows += f"""<tr>
            <td>{_safe(ln['item_number'])}</td>
            <td>{_safe(ln['item_name'])}</td>
            <td class="text-right">{_qty(ln['qty_ordered'])}</td>
            <td class="text-right">{_qty(shipped)}</td>
        </tr>"""

    return f"""<!DOCTYPE html><html><head><style>{_BASE_CSS}</style></head><body>
    {header}
    <table class="meta-table"><tr>
        <td style="width:50%">
            <div class="address-label">Ship To</div>
            <div class="address-block">
                <strong>{_safe(data.get('contact_name'))}</strong><br>
                {_safe(data.get('attention'))}<br>
                {addr}
            </div>
        </td>
        <td>
            <table>
                <tr><td class="meta-label">Order #:</td><td>{_safe(data.get('ida'))}</td></tr>
                <tr><td class="meta-label">Date:</td><td>{_safe(data.get('dt_created'))}</td></tr>
                <tr><td class="meta-label">Status:</td><td>{_safe(data.get('status'))}</td></tr>
            </table>
        </td>
    </tr></table>

    <table class="data-table">
        <thead><tr>
            <th style="width:15%">Item #</th>
            <th>Description</th>
            <th class="text-right" style="width:12%">Ordered</th>
            <th class="text-right" style="width:12%">Shipped</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>

    <div class="footer">
        <strong>Received by:</strong> _________________ &nbsp;&nbsp;
        <strong>Date:</strong> _________________
    </div>
    </body></html>"""


# ---------------------------------------------------------------------------
# Template 4: Purchase Order
# ---------------------------------------------------------------------------

def _template_purchase_order(data: Dict, company: Dict) -> str:
    header = _render_header(company, "Purchase Order", data.get("ida", ""),
                            data.get("dt_created", ""))

    addr = data.get("address_full", "").replace("\n", "<br>") if data.get("address_full") else ""

    # Ship-to from company info
    ship_to = company.get("address", "") or ""

    rows = ""
    total_cost = Decimal("0")
    for ln in data.get("lines", []):
        ext = Decimal(str(ln.get("extended_cost", 0) or 0))
        total_cost += ext
        rows += f"""<tr>
            <td>{_safe(ln['item_number'])}</td>
            <td>{_safe(ln['item_name'])}</td>
            <td class="text-right">{_qty(ln['qty_ordered'])}</td>
            <td class="text-right">{_money(ln['unit_cost'])}</td>
            <td class="text-right">{_money(ext)}</td>
        </tr>"""

    return f"""<!DOCTYPE html><html><head><style>{_BASE_CSS}</style></head><body>
    {header}
    <table class="meta-table"><tr>
        <td style="width:50%">
            <div class="address-label">Vendor</div>
            <div class="address-block">
                <strong>{_safe(data.get('contact_name'))}</strong><br>
                {_safe(data.get('attention'))}<br>
                {addr}
            </div>
        </td>
        <td>
            <div class="address-label">Ship To</div>
            <div class="address-block">
                <strong>{company.get('name', '')}</strong><br>
                {ship_to}
            </div>
            <table>
                <tr><td class="meta-label">Terms:</td><td>{_safe(data.get('terms'))}</td></tr>
            </table>
        </td>
    </tr></table>

    <table class="data-table">
        <thead><tr>
            <th style="width:15%">Item #</th>
            <th>Description</th>
            <th class="text-right" style="width:10%">Qty</th>
            <th class="text-right" style="width:12%">Unit Cost</th>
            <th class="text-right" style="width:14%">Extended</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>

    <div class="clearfix">
        <div class="totals-section">
            <table>
                <tr class="total-row"><td>Total:</td><td class="text-right">{_money(total_cost)}</td></tr>
            </table>
        </div>
    </div>

    <div class="footer">
        {_safe(data.get('conditions_description'))}
    </div>
    </body></html>"""


# ---------------------------------------------------------------------------
# Template 5: Order Confirmation
# ---------------------------------------------------------------------------

def _template_order_confirmation(data: Dict, company: Dict) -> str:
    header = _render_header(company, "Order Confirmation", data.get("ida", ""),
                            data.get("dt_created", ""))

    addr = data.get("address_full", "").replace("\n", "<br>") if data.get("address_full") else ""

    totals = data.get("totals", {}) or {}
    subtotal = totals.get("subtotal", data.get("total", 0))
    tax = totals.get("tax", 0)
    shipping = totals.get("shipping", 0)
    total = totals.get("total", data.get("total", 0))

    rows = ""
    for ln in data.get("lines", []):
        rows += f"""<tr>
            <td>{_safe(ln['item_number'])}</td>
            <td>{_safe(ln['item_name'])}</td>
            <td class="text-right">{_qty(ln['qty_ordered'])}</td>
            <td class="text-right">{_money(ln['unit_price'])}</td>
            <td class="text-right">{_money(ln['extended'])}</td>
        </tr>"""

    return f"""<!DOCTYPE html><html><head><style>{_BASE_CSS}</style></head><body>
    {header}
    <p>Thank you for your order. Please review the details below:</p>

    <table class="meta-table"><tr>
        <td style="width:50%">
            <div class="address-label">Customer</div>
            <div class="address-block">
                <strong>{_safe(data.get('contact_name'))}</strong><br>
                {_safe(data.get('attention'))}<br>
                {addr}
            </div>
        </td>
        <td>
            <table>
                <tr><td class="meta-label">Order #:</td><td>{_safe(data.get('ida'))}</td></tr>
                <tr><td class="meta-label">Date:</td><td>{_safe(data.get('dt_created'))}</td></tr>
                <tr><td class="meta-label">Terms:</td><td>{_safe(data.get('terms'))}</td></tr>
            </table>
        </td>
    </tr></table>

    <table class="data-table">
        <thead><tr>
            <th style="width:15%">Item #</th>
            <th>Description</th>
            <th class="text-right" style="width:10%">Qty</th>
            <th class="text-right" style="width:12%">Unit Price</th>
            <th class="text-right" style="width:14%">Extended</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>

    <div class="clearfix">
        <div class="totals-section">
            <table>
                <tr><td>Subtotal:</td><td class="text-right">{_money(subtotal)}</td></tr>
                <tr><td>Tax:</td><td class="text-right">{_money(tax)}</td></tr>
                <tr><td>Shipping:</td><td class="text-right">{_money(shipping)}</td></tr>
                <tr class="total-row"><td>Total:</td><td class="text-right">{_money(total)}</td></tr>
            </table>
        </div>
    </div>

    <div class="footer">
        {_safe(data.get('conditions_description'))}
    </div>
    </body></html>"""


# ---------------------------------------------------------------------------
# Template 6: Commission Report
# ---------------------------------------------------------------------------

def _template_commission_report(data: Dict, company: Dict) -> str:
    header = _render_header(company, "Commission Report", "", "")

    # For commission reports, data['records'] is a list of invoices with commission lines
    records = data.get("records", [])
    filters = data.get("filters", {}) or {}
    period_start = filters.get("period_start", "")
    period_end = filters.get("period_end", "")
    rep_name = filters.get("rep_name", "All Reps")

    rows = ""
    total_sales = Decimal("0")
    total_comm = Decimal("0")

    for rec in records:
        inv_ida = getattr(rec, "ida", "") if hasattr(rec, "ida") else rec.get("ida", "")
        inv_date = _date_str(getattr(rec, "dt_created", None) if hasattr(rec, "dt_created") else rec.get("dt_created"))
        inv_total = Decimal(str(getattr(rec, "total", 0) if hasattr(rec, "total") else rec.get("total", 0) or 0))
        customer = ""
        refs = getattr(rec, "refs", {}) if hasattr(rec, "refs") else rec.get("refs", {})
        if isinstance(refs, dict):
            links = refs.get("links", {})
            if isinstance(links, dict):
                c = links.get("contact", {})
                if isinstance(c, dict):
                    customer = c.get("name", "")

        # Commission data may be in metadata or finance
        finance = getattr(rec, "finance", {}) if hasattr(rec, "finance") else rec.get("finance", {})
        if isinstance(finance, dict):
            comm_amt = Decimal(str(finance.get("commission", 0) or 0))
        else:
            comm_amt = Decimal("0")

        total_sales += inv_total
        total_comm += comm_amt

        rows += f"""<tr>
            <td>{inv_ida}</td>
            <td>{inv_date}</td>
            <td>{customer}</td>
            <td class="text-right">{_money(inv_total)}</td>
            <td class="text-right">{_money(comm_amt)}</td>
        </tr>"""

    eff_rate = (total_comm / total_sales * 100) if total_sales else Decimal("0")

    return f"""<!DOCTYPE html><html><head><style>{_BASE_CSS}</style></head><body>
    {header}
    <table class="meta-table"><tr>
        <td><span class="meta-label">Rep:</span> {rep_name}</td>
        <td><span class="meta-label">Period:</span> {period_start} &mdash; {period_end}</td>
    </tr></table>

    <table class="data-table">
        <thead><tr>
            <th style="width:12%">Invoice #</th>
            <th style="width:12%">Date</th>
            <th>Customer</th>
            <th class="text-right" style="width:14%">Sales</th>
            <th class="text-right" style="width:14%">Commission</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>

    <div class="clearfix">
        <div class="totals-section">
            <table>
                <tr><td>Total Sales:</td><td class="text-right">{_money(total_sales)}</td></tr>
                <tr><td>Total Commission:</td><td class="text-right">{_money(total_comm)}</td></tr>
                <tr class="total-row"><td>Effective Rate:</td><td class="text-right">{eff_rate:.2f}%</td></tr>
            </table>
        </div>
    </div>
    </body></html>"""


# ---------------------------------------------------------------------------
# Template 7: Statement
# ---------------------------------------------------------------------------

def _template_statement(data: Dict, company: Dict) -> str:
    header = _render_header(company, "Statement of Account", "", "")

    contact_name = data.get("contact_name", "")
    addr = data.get("address_full", "").replace("\n", "<br>") if data.get("address_full") else ""
    as_of = data.get("as_of_date", datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"))

    # For statements, data['invoices'] is a list of open invoices
    invoices = data.get("invoices", [])
    payments = data.get("payments", [])

    inv_rows = ""
    total_balance = Decimal("0")
    current = Decimal("0")
    over_30 = Decimal("0")
    over_60 = Decimal("0")
    over_90 = Decimal("0")

    for inv in invoices:
        inv_ida = getattr(inv, "ida", "") if hasattr(inv, "ida") else inv.get("ida", "")
        inv_date = _date_str(getattr(inv, "dt_created", None) if hasattr(inv, "dt_created") else inv.get("dt_created"))
        inv_total = Decimal(str(getattr(inv, "total", 0) if hasattr(inv, "total") else inv.get("total", 0) or 0))
        inv_balance = Decimal(str(getattr(inv, "balance", 0) if hasattr(inv, "balance") else inv.get("balance", 0) or 0))
        inv_terms = getattr(inv, "terms", "") if hasattr(inv, "terms") else inv.get("terms", "")

        total_balance += inv_balance

        # Aging bucket (simple: based on dt_created)
        age_days = 0
        dt_c = getattr(inv, "dt_created", None) if hasattr(inv, "dt_created") else inv.get("dt_created")
        if dt_c:
            try:
                created = datetime.fromtimestamp(int(dt_c) / 1000, tz=timezone.utc)
                age_days = (datetime.now(tz=timezone.utc) - created).days
            except Exception:
                pass

        if age_days > 90:
            over_90 += inv_balance
            bucket = ">90"
        elif age_days > 60:
            over_60 += inv_balance
            bucket = "61-90"
        elif age_days > 30:
            over_30 += inv_balance
            bucket = "31-60"
        else:
            current += inv_balance
            bucket = "Current"

        inv_rows += f"""<tr>
            <td>{inv_ida}</td>
            <td>{inv_date}</td>
            <td>{inv_terms}</td>
            <td class="text-right">{_money(inv_total)}</td>
            <td class="text-right">{_money(inv_balance)}</td>
            <td class="text-center">{bucket}</td>
        </tr>"""

    pmt_rows = ""
    for pmt in payments:
        pmt_ida = getattr(pmt, "ida", "") if hasattr(pmt, "ida") else pmt.get("ida", "")
        pmt_date = _date_str(getattr(pmt, "dt_created", None) if hasattr(pmt, "dt_created") else pmt.get("dt_created"))
        pmt_total = Decimal(str(getattr(pmt, "total", 0) if hasattr(pmt, "total") else pmt.get("total", 0) or 0))
        pmt_rows += f"""<tr>
            <td>{pmt_ida}</td>
            <td>{pmt_date}</td>
            <td class="text-right">{_money(pmt_total)}</td>
        </tr>"""

    payments_section = ""
    if pmt_rows:
        payments_section = f"""
        <div class="doc-title" style="font-size:11pt; margin-top:14pt">Recent Payments</div>
        <table class="data-table">
            <thead><tr>
                <th>Payment #</th>
                <th>Date</th>
                <th class="text-right">Amount</th>
            </tr></thead>
            <tbody>{pmt_rows}</tbody>
        </table>
        """

    return f"""<!DOCTYPE html><html><head><style>{_BASE_CSS}</style></head><body>
    {header}
    <table class="meta-table"><tr>
        <td style="width:50%">
            <div class="address-block">
                <strong>{contact_name}</strong><br>
                {addr}
            </div>
        </td>
        <td>
            <table>
                <tr><td class="meta-label">As of:</td><td>{as_of}</td></tr>
                <tr><td class="meta-label">Balance:</td><td><strong>{_money(total_balance)}</strong></td></tr>
            </table>
        </td>
    </tr></table>

    <table class="data-table">
        <thead><tr>
            <th style="width:12%">Invoice #</th>
            <th style="width:12%">Date</th>
            <th style="width:10%">Terms</th>
            <th class="text-right" style="width:14%">Total</th>
            <th class="text-right" style="width:14%">Balance</th>
            <th class="text-center" style="width:10%">Aging</th>
        </tr></thead>
        <tbody>{inv_rows}</tbody>
    </table>

    {payments_section}

    <div class="clearfix">
        <div class="totals-section" style="width: 300pt">
            <table>
                <tr><td>Current:</td><td class="text-right">{_money(current)}</td></tr>
                <tr><td>31-60 Days:</td><td class="text-right">{_money(over_30)}</td></tr>
                <tr><td>61-90 Days:</td><td class="text-right">{_money(over_60)}</td></tr>
                <tr><td>Over 90 Days:</td><td class="text-right">{_money(over_90)}</td></tr>
                <tr class="total-row"><td>Total Due:</td><td class="text-right">{_money(total_balance)}</td></tr>
            </table>
        </div>
    </div>
    </body></html>"""


# ---------------------------------------------------------------------------
# Template 8: Customs Proforma
# ---------------------------------------------------------------------------

def _template_customs_proforma(data: Dict, company: Dict) -> str:
    header = _render_header(company, "Proforma Invoice / Customs Declaration",
                            data.get("ida", ""), data.get("dt_created", ""))

    addr = data.get("address_full", "").replace("\n", "<br>") if data.get("address_full") else ""

    rows = ""
    total_value = Decimal("0")
    total_weight = Decimal("0")

    for ln in data.get("lines", []):
        ext = Decimal(str(ln.get("extended", 0) or 0))
        total_value += ext
        w = ln.get("weight", 0) or 0
        try:
            total_weight += Decimal(str(w))
        except Exception:
            pass

        rows += f"""<tr>
            <td>{_safe(ln['item_number'])}</td>
            <td>{_safe(ln['item_name'])}</td>
            <td class="text-center">{_safe(ln['hs_code'])}</td>
            <td class="text-center">{_safe(ln['country_of_origin'])}</td>
            <td class="text-right">{_qty(ln['qty_ordered'])}</td>
            <td class="text-right">{_safe(ln['weight'])}</td>
            <td class="text-right">{_money(ln['unit_price'])}</td>
            <td class="text-right">{_money(ext)}</td>
        </tr>"""

    return f"""<!DOCTYPE html><html><head><style>{_BASE_CSS}
        table.data-table th, table.data-table td {{ font-size: 8pt; padding: 3pt 4pt; }}
    </style></head><body>
    {header}
    <table class="meta-table"><tr>
        <td style="width:50%">
            <div class="address-label">Consignee</div>
            <div class="address-block">
                <strong>{_safe(data.get('contact_name'))}</strong><br>
                {_safe(data.get('attention'))}<br>
                {addr}
            </div>
        </td>
        <td>
            <div class="address-label">Shipper</div>
            <div class="address-block">
                <strong>{company.get('name', '')}</strong><br>
                {company.get('address', '')}
            </div>
            <table>
                <tr><td class="meta-label">Terms:</td><td>{_safe(data.get('terms'))}</td></tr>
                <tr><td class="meta-label">Currency:</td><td>USD</td></tr>
            </table>
        </td>
    </tr></table>

    <table class="data-table">
        <thead><tr>
            <th style="width:10%">Item #</th>
            <th>Description</th>
            <th class="text-center" style="width:10%">HS Code</th>
            <th class="text-center" style="width:8%">Origin</th>
            <th class="text-right" style="width:7%">Qty</th>
            <th class="text-right" style="width:8%">Weight</th>
            <th class="text-right" style="width:10%">Unit Value</th>
            <th class="text-right" style="width:12%">Extended</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>

    <div class="clearfix">
        <div class="totals-section">
            <table>
                <tr><td>Total Weight:</td><td class="text-right">{total_weight}</td></tr>
                <tr class="total-row"><td>Total Value:</td><td class="text-right">{_money(total_value)}</td></tr>
            </table>
        </div>
    </div>

    <div class="footer">
        I declare that the information on this proforma invoice is true and correct
        to the best of my knowledge.<br><br>
        <strong>Signature:</strong> _________________ &nbsp;&nbsp;
        <strong>Date:</strong> _________________
    </div>
    </body></html>"""


# ---------------------------------------------------------------------------
# Generic fallback template (table of model fields)
# ---------------------------------------------------------------------------

def _template_generic(data: Dict, company: Dict, report_name: str) -> str:
    header = _render_header(company, report_name, data.get("ida", ""),
                            data.get("dt_created", ""))

    # Single record with lines
    if data.get("lines"):
        meta_rows = ""
        for key in ["ida", "status", "dt_created", "contact_name", "terms",
                     "total", "balance"]:
            val = data.get(key)
            if val:
                meta_rows += f'<tr><td class="meta-label">{key.replace("_", " ").title()}:</td><td>{_safe(val)}</td></tr>'

        line_rows = ""
        for ln in data["lines"]:
            line_rows += f"""<tr>
                <td>{_safe(ln.get('line_number'))}</td>
                <td>{_safe(ln.get('item_number'))}</td>
                <td>{_safe(ln.get('item_name'))}</td>
                <td class="text-right">{_qty(ln.get('qty_ordered'))}</td>
                <td class="text-right">{_money(ln.get('unit_price'))}</td>
                <td class="text-right">{_money(ln.get('extended'))}</td>
            </tr>"""

        return f"""<!DOCTYPE html><html><head><style>{_BASE_CSS}</style></head><body>
        {header}
        <table class="meta-table">{meta_rows}</table>
        <table class="data-table">
            <thead><tr>
                <th>#</th><th>Item #</th><th>Description</th>
                <th class="text-right">Qty</th>
                <th class="text-right">Unit Price</th>
                <th class="text-right">Extended</th>
            </tr></thead>
            <tbody>{line_rows}</tbody>
        </table>
        </body></html>"""

    # List of records
    records = data.get("records", [])
    if records:
        sample = records[0] if records else None
        # Get field names from the first record
        if sample and hasattr(sample, '_meta'):
            field_names = ["ida"]
            for f in sample._meta.get_fields():
                if f.name in ("ida", "id", "uuid", "metadata", "refs", "prefs",
                              "actions", "comments", "is_deleted", "is_archived",
                              "dt_modified", "version", "security_level",
                              "health_rating"):
                    continue
                if hasattr(f, "column"):
                    field_names.append(f.name)
            field_names = field_names[:8]  # Cap columns
        else:
            field_names = ["ida", "name", "status"]

        th_row = "".join(f"<th>{fn.replace('_', ' ').title()}</th>" for fn in field_names)
        body_rows = ""
        for rec in records[:500]:
            cells = ""
            for fn in field_names:
                val = getattr(rec, fn, "") if hasattr(rec, fn) else rec.get(fn, "")
                if fn == "dt_created":
                    val = _date_str(val)
                elif isinstance(val, (dict, list)):
                    val = ""
                cells += f"<td>{_safe(val)}</td>"
            body_rows += f"<tr>{cells}</tr>"

        return f"""<!DOCTYPE html><html><head><style>{_BASE_CSS}</style></head><body>
        {header}
        <table class="data-table">
            <thead><tr>{th_row}</tr></thead>
            <tbody>{body_rows}</tbody>
        </table>
        <div class="footer">{len(records)} record(s)</div>
        </body></html>"""

    # Empty
    return f"""<!DOCTYPE html><html><head><style>{_BASE_CSS}</style></head><body>
    {header}
    <p>No data available for this report.</p>
    </body></html>"""


# ---------------------------------------------------------------------------
# Template dispatcher
# ---------------------------------------------------------------------------

_TEMPLATE_MAP = {
    "invoice": _template_invoice,
    "invoice_standard": _template_invoice,
    "invoice_shipping": _template_invoice,
    "invoice_pp_ship": _template_invoice,
    "invoice_pp_standard": _template_invoice,
    "invoice_foreign": _template_invoice,
    "credit_memo": _template_invoice,
    "net_invoice": _template_invoice,
    "pick_list": _template_pick_list,
    "pick_request": _template_pick_list,
    "pick_pull_request": _template_pick_list,
    "packing_slip": _template_packing_slip,
    "packing_list": _template_packing_slip,
    "purchase_order": _template_purchase_order,
    "order_confirmation": _template_order_confirmation,
    "proforma_invoice": _template_customs_proforma,
    "customs_proforma": _template_customs_proforma,
    "commission_report": _template_commission_report,
    "broker_commission_report": _template_commission_report,
    "statement": _template_statement,
    "past_due_notice": _template_statement,
}


def _resolve_template_key(report_name: str, report_data: Dict,
                          category: str) -> str:
    """Determine which built-in template to use."""
    # 1) Explicit template in report.data
    explicit = report_data.get("template", "") if isinstance(report_data, dict) else ""
    if explicit:
        key = re.sub(r'[^a-z0-9]+', '_', explicit.lower()).strip('_')
        if key in _TEMPLATE_MAP:
            return key

    # 2) Derive from report name
    key = re.sub(r'[^a-z0-9]+', '_', report_name.lower()).strip('_')
    if key in _TEMPLATE_MAP:
        return key

    # 3) Partial matches
    name_lower = report_name.lower()
    if "pick" in name_lower or "pull" in name_lower:
        return "pick_list"
    if "packing" in name_lower:
        return "packing_slip"
    if "purchase" in name_lower:
        return "purchase_order"
    if "proforma" in name_lower or "customs" in name_lower:
        return "customs_proforma"
    if "commission" in name_lower:
        return "commission_report"
    if "statement" in name_lower or "past due" in name_lower:
        return "statement"
    if "confirmation" in name_lower:
        return "order_confirmation"
    if "invoice" in name_lower or "credit memo" in name_lower:
        return "invoice"

    # 4) Category fallback
    if category == "statement":
        return "statement"

    return ""  # Will use generic


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_report(
    report_name: str,
    model_name: str,
    record_id: Optional[int] = None,
    filters: Optional[Dict] = None,
    fmt: str = "pdf",
) -> Dict[str, Any]:
    """
    Render a report to PDF (or HTML).

    Returns
    -------
    dict with keys:
        pdf_bytes : bytes (PDF content) or html : str (if fmt='html')
        filename  : str
        pages     : int (PDF only)
    """
    import weasyprint

    # 1) Look up report definition
    Report = django_apps.get_model("core", "Report")
    report_qs = Report.objects.filter(
        name=report_name,
        is_active=True,
        is_deleted=False,
    )
    if model_name:
        report_qs = report_qs.filter(
            Q(model_name=model_name) | Q(model_name="system") | Q(model_name="")
        )
    report_def = report_qs.first()

    if not report_def:
        raise ValueError(f"Report '{report_name}' not found for model '{model_name}'")

    effective_model = report_def.model_name or model_name
    report_data = report_def.data or {}
    category = report_def.category or "report"
    company = _get_company_info()

    # 2) Load data
    template_key = _resolve_template_key(report_name, report_data, category)

    # Statement is a special case: load customer's open invoices
    if template_key == "statement" and record_id:
        data = _load_statement_data(effective_model, record_id)
    elif template_key == "commission_report":
        data = _load_commission_data(effective_model, record_id, filters)
    elif record_id:
        data = _load_single_record(effective_model, record_id)
    else:
        records = _load_list_data(effective_model, filters)
        data = {
            "records": records,
            "filters": filters or {},
        }

    # 3) Render HTML
    if template_key and template_key in _TEMPLATE_MAP:
        html = _TEMPLATE_MAP[template_key](data, company)
    else:
        html = _template_generic(data, company, report_name)

    if fmt == "html":
        return {"html": html, "filename": _make_filename(report_name, record_id, "html"), "pages": 0}

    # 4) Convert to PDF
    doc = weasyprint.HTML(string=html).render()
    pdf_bytes = doc.write_pdf()
    page_count = len(doc.pages)

    filename = _make_filename(report_name, record_id, "pdf")

    return {
        "pdf_bytes": pdf_bytes,
        "filename": filename,
        "pages": page_count,
    }


def _load_statement_data(model_name: str, record_id: int) -> Dict[str, Any]:
    """Load customer info + open invoices + recent payments for a statement."""
    # Load the customer/contact
    model_cls = _get_model_class(model_name)
    if not model_cls:
        raise ValueError(f"Unknown model: {model_name}")
    record = model_cls.objects.filter(id=record_id).first()
    if not record:
        raise ValueError(f"{model_name} id={record_id} not found")

    contact_name = getattr(record, "name", "") or getattr(record, "ida", "")
    addr = getattr(record, "address_full", "") or ""

    # Load open invoices for this customer
    Invoice = _get_model_class("invoice")
    invoices = []
    if Invoice:
        invoices = list(
            Invoice.objects.filter(
                contact_id=record_id,
                is_active=True,
                is_deleted=False,
            ).exclude(balance=0).exclude(balance=None).order_by("dt_created")[:500]
        )

    # Load recent payments
    Payment = _get_model_class("payment")
    payments = []
    if Payment:
        try:
            payments = list(
                Payment.objects.filter(
                    contact_id=record_id,
                    is_active=True,
                    is_deleted=False,
                ).order_by("-dt_created")[:20]
            )
        except Exception:
            pass

    return {
        "contact_name": contact_name,
        "address_full": addr,
        "invoices": invoices,
        "payments": payments,
        "as_of_date": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
    }


def _load_commission_data(model_name: str, record_id: Optional[int],
                          filters: Optional[Dict]) -> Dict[str, Any]:
    """Load invoices with commission data."""
    Invoice = _get_model_class("invoice")
    if not Invoice:
        raise ValueError("Invoice model not found")

    qs = Invoice.objects.filter(is_active=True, is_deleted=False)
    filters = filters or {}

    if record_id:
        # Single rep
        qs = qs.filter(
            Q(refs__links__rep__id=record_id) |
            Q(refs__links__rep__id=str(record_id))
        )

    if filters.get("dt_created__gte"):
        qs = qs.filter(dt_created__gte=filters["dt_created__gte"])
    if filters.get("dt_created__lte"):
        qs = qs.filter(dt_created__lte=filters["dt_created__lte"])

    records = list(qs.order_by("dt_created")[:2000])

    return {
        "records": records,
        "filters": {
            "rep_name": filters.get("rep_name", "All Reps"),
            "period_start": filters.get("period_start", ""),
            "period_end": filters.get("period_end", ""),
        },
    }


def _make_filename(report_name: str, record_id: Optional[int], ext: str) -> str:
    """Generate a clean filename."""
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', report_name).strip('_').lower()
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    if record_id:
        return f"{slug}_{record_id}_{ts}.{ext}"
    return f"{slug}_{ts}.{ext}"


def get_available_reports(model_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """List available reports, optionally filtered by model."""
    Report = django_apps.get_model("core", "Report")
    qs = Report.objects.filter(is_active=True, is_deleted=False)
    if model_name:
        qs = qs.filter(Q(model_name=model_name) | Q(model_name="system") | Q(model_name=""))
    qs = qs.order_by("model_name", "sort_order", "name")

    return [
        {
            "id": r.id,
            "name": r.name,
            "model_name": r.model_name or "",
            "category": r.category or "",
            "description": r.description or r.purpose or "",
            "output_type": r.output_type or "print",
        }
        for r in qs
    ]


def render_report_action(
    report_name: str,
    model_name: str,
    record_id: Optional[int] = None,
    filters: Optional[Dict] = None,
    fmt: str = "pdf",
) -> Dict[str, Any]:
    """
    Manage-endpoint wrapper — returns metadata, not bytes.

    The actual PDF download goes through the report view endpoint.
    """
    result = render_report(report_name, model_name, record_id, filters, fmt)

    if fmt == "html":
        return {
            "filename": result["filename"],
            "pages": 0,
            "size_bytes": len(result.get("html", "")),
            "format": "html",
            "download_url": (
                f"/wcapi/report/?report={report_name}&model={model_name}"
                + (f"&id={record_id}" if record_id else "")
                + "&format=html"
            ),
        }

    pdf_bytes = result.get("pdf_bytes", b"")
    return {
        "filename": result["filename"],
        "pages": result["pages"],
        "size_bytes": len(pdf_bytes),
        "format": "pdf",
        "download_url": (
            f"/wcapi/report/?report={report_name}&model={model_name}"
            + (f"&id={record_id}" if record_id else "")
        ),
    }
