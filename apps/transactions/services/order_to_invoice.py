from __future__ import annotations
from typing import List, Optional, Dict, Any, cast
from datetime import datetime, timezone as dt_timezone
from django.db import transaction
from apps.transactions.models import Order, OrderLine, Invoice, InvoiceLine


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
    """Transfer order lines to a new invoice (atomic).

    Workflow:
      1. Select lines (all or by ID list); skip lines with remaining ≤ 0
      2. Create Invoice header with refs.source.order_id
      3. For each OrderLine:
         a. Convert quantity via _convert_quantity_for_invoice()
         b. Create InvoiceLine with full price/cost/tax/physical
         c. Update source OrderLine: invoiced += remaining, remaining → 0
      4. If all order lines fulfilled → set order.status = 'fulfilled'

    LEGACY KEYS: _convert_quantity_for_invoice() outputs 'packed' instead
    of 'placed', and reads 'invoiced' — these should be migrated to
    placed/actioned/remaining.
    TODO: Does NOT set parent_model/parent_id on the new Invoice.
    See: readmes/topics/transactions/transactions-totals.md §2
    """
    if not order:
        raise OrderToInvoiceTransferError("Order is required")
    if not transfer_all and not line_ids:
        raise OrderToInvoiceTransferError("Must specify line_ids when transfer_all=False")

    lines_to_transfer = (
        OrderLine.objects.filter(order=order)
        if transfer_all
        else OrderLine.objects.filter(order=order, id__in=line_ids)
    )
    if not lines_to_transfer.exists():
        raise OrderToInvoiceTransferError("No lines to transfer")
    if not transfer_all and len(lines_to_transfer) != len(line_ids or []):
        found = set(lines_to_transfer.values_list("id", flat=True))
        missing = set(line_ids or []) - found
        raise OrderToInvoiceTransferError(f"Line IDs not found: {missing}")

    # Create invoice
    invoice = Invoice.objects.create(
        status=invoice_status,
        customer_id=getattr(order, "customer_id", 0) or 0,
        vendor_id=getattr(order, "vendor_id", 0) or 0,
        refs=_prepare_invoice_refs(order, invoice_type),
        prefs=dict(order.prefs or {}),
        metadata=_prepare_invoice_metadata(order, invoice_type),
    )

    line_mapping: Dict[int, int] = {}
    transferred = 0
    for ol in lines_to_transfer:
        q = ol.quantity or {}
        remaining = q.get("remaining", 0)
        if transfer_all and remaining <= 0:
            continue

        il = InvoiceLine.objects.create(
            invoice=invoice,
            status=ol.status or "pending",
            price_level=ol.price_level,
            item=ol.item,
            quantity=_convert_quantity_for_invoice(ol.quantity),
            price=ol.price,
            cost=ol.cost,
            tax=ol.tax,
            physical=ol.physical,
            refs=_prepare_line_refs(ol),
            prefs=dict(ol.prefs or {}),
            metadata=_prepare_line_metadata(ol, order),
        )
        line_mapping[ol.id] = il.id
        transferred += 1

        _update_order_line_quantity(ol, remaining)
    if transfer_all:
        remaining_total = sum(
            (l.quantity or {}).get("remaining", 0) for l in OrderLine.objects.filter(order=order)
        )
        if remaining_total <= 0:
            order.status = "fulfilled"
            order.save(update_fields=["status", "dt_modified", "version"])
        remaining_total = sum((l.quantity or {}).get("remaining", 0) for l in OrderLine.objects.filter(order=order))
        if remaining_total <= 0:
            order.status = "fulfilled"
            order.save(update_fields=["status", "dt_modified", "version"])
    inv_refs = invoice.refs or {}
    inv_refs.setdefault("source", {})["order_id"] = order.id
    transfer_date_value: Any = getattr(invoice, "dt_created", None)
    if getattr(transfer_date_value, "isoformat", None):
        inv_refs["source"]["transfer_date"] = transfer_date_value.isoformat()
    else:
        try:
            inv_refs["source"]["transfer_date"] = datetime.fromtimestamp(float(transfer_date_value), tz=dt_timezone.utc).isoformat()
        except Exception:
            inv_refs["source"]["transfer_date"] = str(transfer_date_value)
    inv_refs["source"]["invoice_type"] = invoice_type
    invoice.refs = inv_refs
    invoice.save(update_fields=["refs", "dt_modified", "version"])
    invoice.save(update_fields=["refs", "dt_modified", "version"])

    return {
        "success": True,
        "invoice_id": invoice.id,
        "order_id": order.id,
        "lines_transferred": transferred,
        "line_mapping": line_mapping,
        "order_preserved": preserve_order,
        "invoice_status": invoice.status,
        "invoice_type": invoice_type,
    }
    
def _resolve_order_party(order: Order) -> Any:
    for attr in ("party", "customer", "client", "account", "counterparty"):
        if hasattr(order, attr):
            value = getattr(order, attr)
            if value is not None:
                return value
    return None
    
def _prepare_invoice_refs(order: Order, invoice_type: str) -> Dict[str, Any]:
    refs = dict(order.refs or {})
    src = refs.setdefault("source", {})
    src["converted_from"] = "order"
    src["original_id"] = order.id
    src["invoice_type"] = invoice_type
    refs.setdefault("links", {})
    if "proposal_id" in src:
        src["original_proposal_id"] = src["proposal_id"]
    return refs

def _prepare_invoice_metadata(order: Order, invoice_type: str) -> Dict[str, Any]:
    md = dict(order.metadata or {})
    conv = md.setdefault("conversion", {})
    conv["from_order"] = order.id
    conv["transfer_type"] = "order_to_invoice"
    conv["invoice_type"] = invoice_type
    if "from_proposal" in conv:
        conv["original_proposal"] = conv["from_proposal"]
    return md

def _prepare_line_refs(ol: OrderLine) -> Dict[str, Any]:
    refs = dict(ol.refs or {})
    src = refs.setdefault("source", {})
    src["order_line_id"] = ol.id
    if "order_id" not in src:
        src["order_id"] = getattr(ol, "order_id", None)
    if "proposal_line_id" in src:
        src["original_proposal_line_id"] = src["proposal_line_id"]
    return refs

def _prepare_line_metadata(ol: OrderLine, order: Order) -> Dict[str, Any]:
    md = dict(ol.metadata or {})
    conv = md.setdefault("conversion", {})
    conv["from_order_line"] = ol.id
    conv["from_order"] = order.id
    if "from_proposal_line" in conv:
        conv["original_proposal_line"] = conv["from_proposal_line"]
    return md

def _convert_quantity_for_invoice(order_quantity: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert order line quantity to invoice line quantity.

    LEGACY: Uses 'packed' instead of canonical 'placed', and reads 'invoiced'
    instead of 'actioned'.  Should be migrated to:
      placed = remaining, actioned = 0, remaining = remaining

    See: readmes/topics/transactions/transactions-totals.md §2
    """
    q = dict(order_quantity or {})
    remaining = q.get("remaining", 0)
    return {
        "packed": 0,
        "remaining": remaining,
        "precision": q.get("precision", 2),
        "is_fixed": q.get("is_fixed", False),
        "converted_from_order": {
            "invoiced": q.get("invoiced", 0),
            "original_remaining": remaining,
            "converted_from_proposal": q.get("converted_from_proposal"),
        },
    }

def _update_order_line_quantity(ol: OrderLine, invoiced_qty: float) -> None:
    """Decrement source order line after transfer to invoice.

    Updates: invoiced += invoiced_qty, remaining = max(0, remaining - invoiced_qty)

    LEGACY: Uses 'invoiced' instead of canonical 'actioned'.
    Should be: actioned += invoiced_qty, remaining = placed - actioned

    See: readmes/topics/transactions/transactions-totals.md §2
    """
    q = dict(ol.quantity or {})
    q["invoiced"] = q.get("invoiced", 0) + invoiced_qty
    q["remaining"] = max(0, q.get("remaining", 0) - invoiced_qty)
    ol.quantity = cast(Any, q)
    ol.save(update_fields=["quantity", "dt_modified", "version"])