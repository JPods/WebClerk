from __future__ import annotations
from typing import List, Optional, Dict, Any, cast
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
    """Transfer order lines to a new invoice (atomic).

    Workflow — collect-then-create pending pattern:
      1. Select lines (all or by ID list); skip lines with remaining ≤ 0
      2. Create Invoice header with refs.source.order_id
      3. For each OrderLine:
         a. Convert quantity via _convert_quantity_for_invoice()
         b. Create InvoiceLine (signal suppressed via _pending_created)
         c. Update source OrderLine (signal suppressed via _pending_created)
         d. Append inventory delta to pending_deltas array
      4. After all saves complete, create Pending records from the array
      5. If all order lines fulfilled → set order.status = 'fulfilled'

    This ensures exactly ONE pending record per invoice line, with correct
    on_in / on_so / on_hand values.  No signal-driven duplicates.

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

    # Create invoice — parent_id/parent_model links back to source order
    invoice = Invoice.objects.create(
        status=invoice_status,
        customer_id=getattr(order, "customer_id", 0) or 0,
        vendor_id=getattr(order, "vendor_id", 0) or 0,
        parent_id=order.id,
        parent_model='order',
        refs=_prepare_invoice_refs(order, invoice_type),
        prefs=dict(order.prefs or {}),
        metadata=_prepare_invoice_metadata(order, invoice_type),
    )

    # ── Build line data for React — NOT saved server-side ────────────
    # Conversion creates the header. React receives line data and populates
    # the form. User reviews, clicks Save.
    # On save: InvoiceLine records created → each fires its own pending.
    # InvoiceLine tells OrderLine to adjust → OrderLine saves → fires its pending.
    lines_for_react = []
    for ol in lines_to_transfer:
        q = ol.quantity or {}
        remaining = q.get("remaining", 0)
        if transfer_all and remaining <= 0:
            continue

        lines_for_react.append({
            'line_number': getattr(ol, 'line_number', 0) or 0,
            'item': ol.item or {},
            'quantity': _convert_quantity_for_invoice(ol.quantity),
            'price': ol.price or {},
            'cost': ol.cost or {},
            'tax': getattr(ol, 'tax', None) or {},
            'price_level': ol.price_level or '',
            'status': ol.status or 'pending',
            'is_active': True,
            'comments': getattr(ol, 'comments', None) or {},
            'config': getattr(ol, 'config', None) or {},
            'commission': getattr(ol, 'commission', None) or {},
            'refs': _prepare_line_refs(ol),
            '_dirty': True,
        })

    # Order lines are NOT modified here. They are only copied.
    # When the user saves the invoice:
    #   1. InvoiceLine records are created → each fires on_hand/on_in pending
    #   2. InvoiceLine tells OrderLine how to adjust → OrderLine saves → fires on_so pending

    return {
        "success": True,
        "invoice_id": invoice.id,
        "order_id": order.id,
        "lines_for_review": len(lines_for_react),
        "lines": lines_for_react,
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
    src = refs.get("source") or {}
    refs["source"] = src
    src["converted_from"] = "order"
    src["original_id"] = order.id
    src["invoice_type"] = invoice_type
    refs.setdefault("links", {})
    if "proposal_id" in src:
        src["original_proposal_id"] = src["proposal_id"]
    return refs

def _prepare_invoice_metadata(order: Order, invoice_type: str) -> Dict[str, Any]:
    md = dict(order.metadata or {})
    conv = md.get("conversion") or {}
    md["conversion"] = conv
    conv["from_order"] = order.id
    conv["transfer_type"] = "order_to_invoice"
    conv["invoice_type"] = invoice_type
    if "from_proposal" in conv:
        conv["original_proposal"] = conv["from_proposal"]
    return md

def _prepare_line_refs(ol: OrderLine) -> Dict[str, Any]:
    refs = dict(ol.refs or {})
    src = refs.get("source") or {}
    refs["source"] = src
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

    Uses canonical staged/active/remaining keys.
    staged = source remaining (qty being transferred to this invoice)
    active = staged (full transfer amount — user can reduce later)
    remaining = active (no grandchildren yet)

    See: readmes/topics/transactions/transactions-totals.md §2
    """
    q = dict(order_quantity or {})
    remaining = q.get("remaining", 0)
    return {
        "staged": remaining,
        "active": remaining,
        "remaining": remaining,
        "precision": q.get("precision", 2),
        "is_fixed": q.get("is_fixed", False),
        "converted_from_order": {
            "active": q.get("active", 0),
            "original_remaining": remaining,
            "converted_from_proposal": q.get("converted_from_proposal"),
        },
    }

def _update_order_line_quantity(ol: OrderLine, invoiced_qty: float, child_line_id: int = 0) -> None:
    """Update source order line after transfer to invoice.

    Tracks child invoice lines in children_active and recomputes:
      remaining = active − children_active.sum
    Does NOT modify active (that is user input).
    Sets _pending_created to suppress the post_save signal —
    pending records are created later by _create_pending_records().

    Uses canonical staged/active/remaining keys.
    See: readmes/topics/transactions/transactions-totals.md §2
    """
    q = dict(ol.quantity or {})
    
    # Update children_active tracker
    children = q.get("children_active", {"sum": 0, "lines": []})
    if not isinstance(children, dict):
        children = {"sum": 0, "lines": []}
    if not isinstance(children.get("lines"), list):
        children["lines"] = []
    children["lines"].append({"id": child_line_id, "active": invoiced_qty})
    children["sum"] = sum(c.get("active", 0) for c in children["lines"])
    q["children_active"] = children
    
    # remaining = active − children_active.sum
    active = q.get("active", 0)
    q["remaining"] = max(0, active - children["sum"])
    
    ol.quantity = cast(Any, q)
    ol._pending_created = True  # suppress signal — pending created later
    ol.save(update_fields=["quantity", "dt_modified", "version"])


def _create_pending_records(
    invoice: Invoice,
    order: Order,
    pending_deltas: List[Dict[str, Any]],
) -> List:
    """Create ONE Pending record per transferred line from the collected deltas.

    Each pending records:
      on_in  = +quantity   (invoice commitment)
      on_so  = -quantity   (release order commitment)
      on_hand = -quantity  (goods shipped)

    Called after all lines are saved so IDs are stable.
    """
    from apps.core.models import Pending

    created = []
    for delta in pending_deltas:
        item_id = delta['item_id']
        qty = delta['quantity']
        pending_data = {
            'type_id': 'IN',
            'item_num': delta['item_ida'],
            'item_id': item_id,
            'doc_id': getattr(invoice, 'ida', '') or str(invoice.pk),
            'doc_pk': invoice.pk,
            'line_id': delta['invoice_line_id'],
            'line_num': 0,

            # Release source bucket only — invoice line save handles on_hand/on_in
            'on_so': -qty,

            # Pricing snapshot
            'unit_cost': delta['unit_cost'],
            'unit_price': delta['unit_price'],

            # Audit
            'reason': 'in line add (releases so, deducts on_hand)',
            'take_action': 1,
            'changed_by': '',

            # Transaction reference
            'transaction_type': 'invoice',
            'transaction_model': 'invoice',

            # Parent links
            'links': {
                'order': {
                    'parent_id': order.pk,
                    'order_line_id': delta['order_line_id'],
                },
            },
        }

        pending = Pending.objects.create(
            model_name='item',
            record_id=str(item_id),
            purpose='inventory_line_add',
            name=f'IN Line Add: {delta["item_ida"]}',
            changes=pending_data,
        )
        created.append(pending)
        logger.debug(
            f"Created pending {pending.pk} for invoice line {delta['invoice_line_id']}, "
            f"item {item_id}, qty={qty} (on_in=+{qty}, on_so=-{qty}, on_hand=-{qty})"
        )

    return created