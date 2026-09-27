from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone as _tz
from decimal import Decimal
from typing import Optional, Sequence


def _now_ms() -> int:
    """UTC epoch ms — every stored datetime in WC3 (Axiom 14)."""
    return int(datetime.now(_tz.utc).timestamp() * 1000)

from django.db import transaction
from django.core.exceptions import ValidationError

from apps.transactions.models import (
    Quote, QuoteLine,
    Order, OrderLine,
    Invoice, InvoiceLine,
    Purchase, PurchaseLine,
    WorkOrder, WorkOrderLine
)
# NOTE: Linkage functionality removed - use LinkageEntry if needed
# from apps.docs.models.linkage_entry import LinkageEntry
from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse
from apps.products.models.inventory_layer import InventoryLayer

# ---------------------------------------------------------------------------
# Central review list of JSON-esque line attributes we expect to deep-copy
# when creating a new transactional line from another (quote -> order,
# order -> invoice, PO -> receipt derived lines, etc.).
#
# IMPORTANT (review process):
# 1. If you add a new JSONField to BaseLineModel (or concrete line models),
#    append its name here AND add a sample value in the line copy parity test.
# 2. The test `tests/test_line_copy_field_parity.py` will fail if a JSONField
#    exists on a representative line model (OrderLine) that's not listed.
# 3. Fields that are scalar (status, type_sale, probability) are handled
#    explicitly below and are not part of this list.
# 4. Missing attributes are skipped safely so forward additions won't break
#    runtime before migrations / code sync complete.
#
# Header-only JSON (if ever) should NOT be added here (those belong to parent
# transaction models, not lines). Keep this strictly for line-level fields.
# ---------------------------------------------------------------------------
LINE_JSON_FIELDS_TO_COPY = (
    'item', 'quantity', 'cost', 'price', 'tax',
    'actions', 'physical',
    # Results: copied as they are, then recomputed by the totals engine on the new document.
    'totals',
    # Extended / newer additions (may be no-ops until fields are present):
    'metadata', 'refs', 'prefs', 'comments',
    # Carried forward by the convert services (convert.py, convert_quote_to_order.py,
    # convert_order_to_invoice.py) into lines returned for review.
    'commission', 'config',
)


@dataclass
class ReceiveLine:
    po_line_id: int
    qty: Decimal | float | int
    warehouse_code: str
    unit_cost: float | int | Decimal | None = None
    lot: str | None = None
    serial_batch: str | None = None


# ---------------------------------------------------------------------------
# Linkage helpers (DISABLED - use LinkageEntry if needed)
# ---------------------------------------------------------------------------
def _resolve_item_id_from_line(line: PurchaseLine | OrderLine | QuoteLine | WorkOrderLine) -> Optional[int]:
    item = getattr(line, 'item', {}) or {}
    # Prefer id_num, fallback: try 'id' or 'item_id' if present
    return item.get('id_num') or item.get('id') or item.get('item_id')


@transaction.atomic
def receive_purchase(po: Purchase,
                           receipt_id: str,
                           lines: Sequence[ReceiveLine]) -> dict:
    """Post a receipt for a PO, create inventory stacks, and inventory deltas.

    When goods are received:
    - Increases quantity_on_hand
    - Decreases quantity_on_po
    - Creates inventory layer stacks for warehouse tracking

    Args:
        po: The Purchase order being received against
        receipt_id: Client-provided receipt identifier (stored in ida field)
        lines: Sequence of ReceiveLine objects with qty, warehouse, etc.

    Returns a summary dict with created receipt id, stack ids, and deltas created.

    See also:
        - Building items is a production workorder: expand, then complete (workorder_bom)
        - Counts and corrections are a count workorder saved through the door (plan §16b)
    """
    from apps.transactions.models.receipt import Receipt
    from apps.transactions.models.receipt_line import ReceiptLine

    if not receipt_id:
        raise ValidationError({'receipt_id': 'Required'})

    receipt = Receipt.objects.create(
        ida=receipt_id,
        source_type=Receipt.SOURCE_PURCHASE,
        parent_id=po.pk,
        parent_model='purchase',
    )   # vendor, contact and terms are inherited from the purchase on save
    created_stack_ids: list[int] = []
    created_receipt_line_ids: list[int] = []
    deltas_created = 0

    for rl in lines:
        try:
            pol = PurchaseLine.objects.select_related('purchase').get(pk=rl.po_line_id, purchase=po)
        except PurchaseLine.DoesNotExist:
            raise ValidationError({'lines': f'po_line_id {rl.po_line_id} not found for this PO'})
        item_id = _resolve_item_id_from_line(pol)
        if not item_id:
            raise ValidationError({'lines': f'po_line_id {rl.po_line_id} missing item.id_num in line.item JSON'})
        try:
            item = Item.objects.get(pk=item_id)
        except Item.DoesNotExist:
            raise ValidationError({'lines': f'Item {item_id} not found'})
        try:
            wh = Warehouse.objects.get(code=rl.warehouse_code)
        except Warehouse.DoesNotExist:
            raise ValidationError({'lines': f'Warehouse code {rl.warehouse_code} not found'})

        unit_cost = float(rl.unit_cost) if rl.unit_cost is not None else float((pol.cost or {}).get('unit') or 0)

        # The receipt line is the whole act of receiving. Its save writes the Pending the
        # way every line does (signals._LINE_CONFIG), and that Pending moves on_hand,
        # on_rc and on_po and creates the layer in one apply (D10, Bill 2026-09-21).
        # parent_line_id makes it a child of the purchase line, so that line's remaining
        # is recomputed by the one writer — the document moves when the goods do.
        receipt_line = ReceiptLine.objects.create(
            receipt=receipt,
            parent_line_id=pol.pk,
            refs={'source': {'purchase_line_id': pol.pk}},
            warehouse=wh,
            lot=rl.lot or '',
            serial_batch=rl.serial_batch or '',
            item=pol.item or {'item_id': item_id},  # Copy item JSON from PO line
            quantity={'staged': float(rl.qty), 'active': float(rl.qty), 'remaining': 0, 'received': float(rl.qty)},
            cost={'unit': unit_cost},
        )
        created_receipt_line_ids.append(receipt_line.id)
        deltas_created += 1

        # The layer exists once the Pending has applied. A locked item leaves it queued,
        # and the layer arrives with the item when the queue drains.
        receipt_line.refresh_from_db(fields=['inventory_layer'])
        if receipt_line.inventory_layer_id:
            created_stack_ids.append(receipt_line.inventory_layer_id)

    return {
        'receipt_id': receipt.id,  # type: ignore[attr-defined]
        'receipt_lines_created': created_receipt_line_ids,
        'stacks_created': created_stack_ids,
        'deltas_created': deltas_created
    }


# ---------------------------------------------------------------------------
# WorkOrder Completion - produces finished goods into inventory
# ---------------------------------------------------------------------------
__all__ = [
    # Data classes for line input
    'ReceiveLine',
    # Transaction flow conversions
    # Inventory receiving functions
    'receive_purchase',
]
