from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone as dt_timezone
from django.db import transaction
from apps.transactions.models import Order, OrderLine, Invoice, InvoiceLine

import logging
logger = logging.getLogger(__name__)


class OrderToInvoiceTransferError(Exception):
    """Custom exception for order-to-invoice transfer errors."""
    pass

@transaction.atomic
def transfer_order_to_invoice(
    order: Order,
    line_ids: Optional[List[int]] = None,
    transfer_all: bool = True,
    invoice_status: str = "pending",
    preserve_order: bool = True,
    invoice_type: str = "standard"
) -> Dict[str, Any]:
    """Create the Invoice header from an order and return its lines for review.

    One converter (Bill, 2026-09-23): this delegates to convert.convert_order_to_invoice,
    as transfer_quote_to_order already does, so the convert-to-invoice button, the bulk
    route and the UI get the same rules. Its own hand-built header dropped the tax setup
    (finance), the document discount, line types, terms and price level — 13 of 20
    order-made invoices in wc_demo carried a 0 tax rate. The result keeps the shape this
    endpoint's callers expect. preserve_order is accepted for caller compatibility; the
    order is never modified here.
    """
    from apps.transactions.services.convert.convert import convert_order_to_invoice as convert_one

    if not order:
        raise OrderToInvoiceTransferError("Order is required")
    if not transfer_all and not line_ids:
        raise OrderToInvoiceTransferError("Must specify line_ids when transfer_all=False")
    lines_to_transfer = (OrderLine.objects.filter(order=order) if transfer_all
                         else OrderLine.objects.filter(order=order, id__in=line_ids))
    if not lines_to_transfer.exists():
        raise OrderToInvoiceTransferError("No lines to transfer")
    if not transfer_all and lines_to_transfer.count() != len(set(line_ids or [])):
        found = set(lines_to_transfer.values_list("id", flat=True))
        raise OrderToInvoiceTransferError(f"Line IDs not found: {set(line_ids or []) - found}")

    try:
        result = convert_one(order.pk, line_ids=None if transfer_all else line_ids)
    except Exception as exc:                       # the converter's refusals are this one's
        raise OrderToInvoiceTransferError(str(exc)) from exc

    invoice = Invoice.objects.get(pk=result.get("invoice_id"))
    invoice.status = invoice_status
    if hasattr(invoice, "invoice_type"):
        invoice.invoice_type = invoice_type
    invoice.refs = _prepare_invoice_refs(order, invoice_type, dict(invoice.refs or {}))
    invoice.metadata = _prepare_invoice_metadata(order, invoice_type, dict(invoice.metadata or {}))
    invoice.save()

    lines = result.get("lines", [])
    return {
        "success": True,
        "invoice_id": invoice.id,
        "order_id": order.id,
        "lines_for_review": len(lines),
        "lines": lines,
    }


def _prepare_invoice_refs(order: Order, invoice_type: str, refs: Dict[str, Any]) -> Dict[str, Any]:
    src = refs.get("source") or {}
    refs["source"] = src
    src["converted_from"] = "order"
    src["original_id"] = order.id
    src["invoice_type"] = invoice_type
    refs.setdefault("links", {})
    if "quote_id" in src:
        src["original_quote_id"] = src["quote_id"]
    return refs

def _prepare_invoice_metadata(order: Order, invoice_type: str, md: Dict[str, Any]) -> Dict[str, Any]:
    conv = md.get("conversion") or {}
    md["conversion"] = conv
    conv["from_order"] = order.id
    conv["transfer_type"] = "order_to_invoice"
    conv["invoice_type"] = invoice_type
    if "from_quote" in conv:
        conv["original_quote"] = conv["from_quote"]
    return md


