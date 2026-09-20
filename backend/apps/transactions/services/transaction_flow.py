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


def _copy_common_line_fields(src: QuoteLine | OrderLine | PurchaseLine,
                             dst: OrderLine | InvoiceLine | PurchaseLine):
    """Copy scalar + JSON attributes from one line to a new line instance.

    Uses centralized LINE_JSON_FIELDS_TO_COPY for maintainability. Adding a
    new JSONField to line models requires only updating the constant (tests
    enforce parity). Missing attributes are ignored to allow phased rollout.
    Parent relationships (parent_ref_id) handled in model save().
    """
    # Scalar fields
    if hasattr(dst, 'status'):
        dst.status = getattr(src, 'status', None)  # type: ignore[attr-defined]

    # JSON / dict fields (shallow clone to detach references)
    for field_name in LINE_JSON_FIELDS_TO_COPY:
        if hasattr(src, field_name):
            val = getattr(src, field_name) or {}
            if isinstance(val, dict):
                setattr(dst, field_name, val.copy())
            else:
                # Non-dict JSON-like (unlikely) – assign as-is to avoid mutation issues
                setattr(dst, field_name, val)

    # Flow lineage & quantity snapshot injection (metadata.parent_link)
    try:
        parent_obj = getattr(src, 'parent', None)
        if parent_obj is not None and getattr(parent_obj, 'pk', None):
            meta = getattr(dst, 'metadata', {}) or {}
            if isinstance(meta, dict):
                plink = meta.get('parent_link') or {}
                if isinstance(plink, dict):
                    # Only set if absent to preserve prior chain if multi-hop
                    plink.setdefault('parent_id', parent_obj.pk)
                    plink.setdefault('parent_model', parent_obj._meta.model_name)  # type: ignore[attr-defined]
                    # Quantity snapshot (best-effort) – capture ordered/extended style hints if present
                    qty_src = getattr(src, 'quantity', {}) or {}
                    if isinstance(qty_src, dict):
                        q_parent = {}
                        for k in ('staged', 'active', 'remaining', 'shipped', 'packed', 'extended', 'unit'):
                            if k in qty_src:
                                q_parent[k] = qty_src.get(k)
                        if q_parent:
                            plink.setdefault('quantity_at_parent', q_parent)
                    meta['parent_link'] = plink
                setattr(dst, 'metadata', meta)
    except Exception:  # pragma: no cover - defensive
        pass

    # Ensure serial reservations scaffold present inside refs
    try:
        refs = getattr(dst, 'refs', {}) or {}
        if isinstance(refs, dict):
            serials = refs.get('serials')
            if serials is None:
                refs['serials'] = []  # list of {id, serial_number, status, qty?, lot?}
            # Preserve linkage chain; if src had refs.links.linkage propagate it.
            try:
                src_refs = getattr(src, 'refs', {}) or {}
                src_links = (src_refs.get('links') or {}) if isinstance(src_refs, dict) else {}
                linkage_ids = []
                if isinstance(src_links, dict):
                    linkage_ids = src_links.get('linkage') or []
                links = refs.setdefault('links', {"linkage": []})
                if isinstance(links, dict) and linkage_ids and not links.get('linkage'):
                    links['linkage'] = list(linkage_ids)  # copy ids
            except Exception:
                pass
            setattr(dst, 'refs', refs)
    except Exception:  # pragma: no cover
        pass


# ---------------------------------------------------------------------------
# Linkage helpers (DISABLED - use LinkageEntry if needed)
# ---------------------------------------------------------------------------
def ensure_linkage_for_lines(lines) -> Optional[int]:
    """Linkage functionality removed. Returns None.
    
    TODO: Reimplement using LinkageEntry if cross-transaction linking is needed.
    """
    return None


def quote_to_order(quote: Quote, order_no: Optional[str] = None) -> Order:
    so = Order.objects.create(order_no=order_no or f"SO-{quote.pk or 'new'}")
    src_lines = list(QuoteLine.objects.filter(quote=quote).order_by('id'))
    # Linkage disabled - pass None
    linkage_id = None
    # Copy lines after ensuring linkage id
    for pl in src_lines:
        sol = OrderLine(order=so)
        _copy_common_line_fields(pl, sol)
        if linkage_id:
            # Ensure propagated (could already be present from copy)
            refs = getattr(sol, 'refs', {}) or {}
            if isinstance(refs, dict):
                links = refs.setdefault('links', {"linkage": []})
                lst = links.setdefault('linkage', [])
                if not lst:
                    lst.append(linkage_id)
                setattr(sol, 'refs', refs)
        # quote quantity schema can be different; leave as-is and let later edits normalize
        sol.save()
    return so


@transaction.atomic
def order_to_invoice(so: Order, invoice_no: Optional[str] = None) -> Invoice:
    # invoice_no is deprecated; ida is auto-generated from id.
    inv = Invoice.objects.create()
    src_lines = list(OrderLine.objects.filter(order=so).order_by('id'))
    linkage_id = ensure_linkage_for_lines(src_lines) if src_lines else None
    for sol in src_lines:
        il = InvoiceLine(invoice=inv)
        _copy_common_line_fields(sol, il)
        if linkage_id:
            refs = getattr(il, 'refs', {}) or {}
            if isinstance(refs, dict):
                links = refs.setdefault('links', {"linkage": []})
                lst = links.setdefault('linkage', [])
                if not lst:
                    lst.append(linkage_id)
                setattr(il, 'refs', refs)
        # price becomes authoritative for billing; leave quantities/prices as provided
        il.save()
    return inv


@transaction.atomic
def order_to_purchase(so: Order, po_no: Optional[str] = None) -> Purchase:
    """Create a supporting Purchase from an Order.

    Propagates / creates linkage id across involved lines to maintain unified
    comment & lineage chain.
    """
    po = Purchase.objects.create(po_no=po_no or f"PO-SO-{so.pk or 'new'}")
    src_lines = list(OrderLine.objects.filter(order=so).order_by('id'))
    linkage_id = ensure_linkage_for_lines(src_lines) if src_lines else None
    for sol in src_lines:
        pol = PurchaseLine(purchase=po)
        _copy_common_line_fields(sol, pol)
        if linkage_id:
            refs = getattr(pol, 'refs', {}) or {}
            if isinstance(refs, dict):
                links = refs.setdefault('links', {"linkage": []})
                lst = links.setdefault('linkage', [])
                if not lst:
                    lst.append(linkage_id)
                setattr(pol, 'refs', refs)
        pol.save()
    return po


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
        - complete_workorder: For workorder completion (manufacturing)
        - count_inventory: For inventory counts and corrections
        - receive_inventory_changes: High-level dispatcher for all receiving actions
    """
    from apps.transactions.models.receipt import Receipt
    from apps.transactions.models.receipt_line import ReceiptLine
    from apps.core.models.pending import Pending
    from django.utils import timezone
    import uuid

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

        # Create inventory layer stack for warehouse tracking
        stack = InventoryLayer.objects.create(
            item=item,
            warehouse=wh,
            quantity={'received': float(rl.qty), 'issued': 0, 'scrapped': 0},
            lot=rl.lot or '',
            serial_batch=rl.serial_batch or '',
            source_doc_type='purchase_receipt',
            source_doc_id=receipt.id,  # type: ignore[attr-defined]
        )
        unit_cost = float(rl.unit_cost) if rl.unit_cost is not None else float((pol.cost or {}).get('unit') or 0)
        stack.update_cost_after_receipt(unit_cost)
        stack.save()
        created_stack_ids.append(stack.id)

        # Create ReceiptLine record to track what was received. parent_line_id makes it
        # a child of the purchase line, so that line's remaining is recomputed by the one
        # writer — the document moves when the goods do.
        receipt_line = ReceiptLine.objects.create(
            receipt=receipt,
            parent_line_id=pol.pk,
            refs={'source': {'purchase_line_id': pol.pk}},
            warehouse=wh,
            inventory_layer=stack,
            lot=rl.lot or '',
            serial_batch=rl.serial_batch or '',
            item=pol.item or {'item_id': item_id},  # Copy item JSON from PO line
            quantity={'staged': float(rl.qty), 'active': float(rl.qty), 'remaining': 0, 'received': float(rl.qty)},
            cost={'unit': unit_cost},
        )
        created_receipt_line_ids.append(receipt_line.id)

        # Move the buckets through the shape that applies itself: model_name 'item'
        # with a purpose in INVENTORY_PURPOSES. 'inventory_delta' was dispatched by
        # nothing, so every receipt through this path used to leave the buckets behind.
        qty_received = Decimal(str(rl.qty))
        Pending.objects.create(
            model_name='item',
            record_id=str(item_id),
            purpose='receipt_line_add',
            name=f"Receipt {receipt.ida} - item {item_id}",
            changes={
                'on_po': -float(qty_received),   # goods arrived: no longer on order
                'on_hand': float(qty_received),
                'on_rc': float(qty_received),    # received this period
            },
            config={
                'item_id': item_id,
                'warehouse_id': wh.id,
                'source_type': 'purchase_receipt',
                'source_id': receipt.id,
                'source_line_id': receipt_line.id,
                'unit_cost': unit_cost,
                'notes': f"Purchase receipt {receipt.ida} - received {qty_received} units",
            }
        )
        deltas_created += 1

    return {
        'receipt_id': receipt.id,  # type: ignore[attr-defined]
        'receipt_lines_created': created_receipt_line_ids,
        'stacks_created': created_stack_ids,
        'deltas_created': deltas_created
    }


# ---------------------------------------------------------------------------
# WorkOrder Completion - produces finished goods into inventory
# ---------------------------------------------------------------------------
@dataclass
class CompleteWorkOrderLine:
    """Data for completing a workorder line (producing finished goods)."""
    wo_line_id: int
    qty_completed: Decimal | float | int
    warehouse_code: str
    unit_cost: float | int | Decimal | None = None
    lot: str | None = None
    serial_batch: str | None = None


@transaction.atomic
def complete_workorder(wo: WorkOrder,
                       receipt_id: str,
                       lines: Sequence[CompleteWorkOrderLine],
                       completed_by: str = '') -> dict:
    """Complete a WorkOrder, producing finished goods into inventory.

    When a workorder is completed:
    - Increases quantity_on_hand (finished goods produced)
    - Decreases quantity_on_wo (no longer in WIP)
    - Creates inventory layer stacks for warehouse tracking

    Args:
        wo: The WorkOrder being completed
        receipt_id: Client-provided receipt identifier (stored in ida field)
        lines: Sequence of CompleteWorkOrderLine objects with qty, warehouse, etc.

    Returns a summary dict with created receipt id, stack ids, and deltas created.

    See also:
        - receive_purchase: For receiving goods from vendors (PO)
        - count_inventory: For inventory counts and corrections
        - receive_inventory_changes: High-level dispatcher for all receiving actions
    """
    from apps.core.models.pending import Pending

    if not receipt_id:
        raise ValidationError({'receipt_id': 'Required'})

    # Production is not receiving (Bill, 2026-09-20). A receipt says goods came from
    # outside and carries a vendor, terms and an AP ledger; a workorder owes nobody, so
    # its output is an event on the workorder line and can never become a payable.
    created_stack_ids: list[int] = []
    created_event_ids: list[str] = []
    deltas_created = 0

    for cl in lines:
        try:
            wol = WorkOrderLine.objects.select_related('workorder').get(pk=cl.wo_line_id, workorder_id=wo)
        except WorkOrderLine.DoesNotExist:
            raise ValidationError({'lines': f'wo_line_id {cl.wo_line_id} not found for this WorkOrder'})
        
        item_id = _resolve_item_id_from_line(wol)
        if not item_id:
            raise ValidationError({'lines': f'wo_line_id {cl.wo_line_id} missing item.id_num in line.item JSON'})
        try:
            item = Item.objects.get(pk=item_id)
        except Item.DoesNotExist:
            raise ValidationError({'lines': f'Item {item_id} not found'})
        try:
            wh = Warehouse.objects.get(code=cl.warehouse_code)
        except Warehouse.DoesNotExist:
            raise ValidationError({'lines': f'Warehouse code {cl.warehouse_code} not found'})

        # Create inventory layer stack for warehouse tracking
        stack = InventoryLayer.objects.create(
            item=item,
            warehouse=wh,
            quantity={'received': float(cl.qty_completed), 'issued': 0, 'scrapped': 0},
            lot=cl.lot or '',
            serial_batch=cl.serial_batch or '',
            source_doc_type='workorder_completion',
            source_doc_id=wol.pk,       # the line; the event's id is on the layer's refs
        )
        # Use provided unit_cost or estimate from workorder line cost
        unit_cost = float(cl.unit_cost) if cl.unit_cost is not None else float((wol.cost or {}).get('unit') or 0)
        stack.update_cost_after_receipt(unit_cost)
        stack.save()
        created_stack_ids.append(stack.id)

        # One pending: it moves the buckets and records the event on the line, in the
        # same apply. No on_rc — that bucket counts goods received from outside, and
        # nothing arrived from outside here; work in progress became stock.
        qty_completed = Decimal(str(cl.qty_completed))
        event_id = uuid.uuid4().hex
        Pending.objects.create(
            model_name='item',
            record_id=str(item_id),
            purpose='line_event',
            name=f"WorkOrder completion {receipt_id} - item {item_id}",
            changes={
                'on_wo': -float(qty_completed),   # no longer work in progress
                'on_hand': float(qty_completed),  # produced
            },
            config={
                'item_id': item_id,
                'line_model': 'WorkOrderLine',
                'line_id': wol.pk,
                'event': {
                    'id': event_id,
                    'kind': 'completion',
                    'dt': _now_ms(),
                    'by': completed_by,
                    'qty': float(qty_completed),
                    'warehouse_id': wh.id,
                    'warehouse_code': wh.code,
                    'lot': cl.lot or '',
                    'serial_batch': cl.serial_batch or '',
                    'layer_id': stack.id,
                    'unit_cost': unit_cost,
                    'run': receipt_id,
                },
                'source_type': 'workorder_completion',
                'source_id': wo.id,
                'unit_cost': unit_cost,
                'notes': f"WorkOrder completion {receipt_id} - produced {qty_completed} units",
            }
        )
        created_event_ids.append(event_id)
        deltas_created += 1

    return {
        'workorder_id': wo.id,  # type: ignore[attr-defined]
        'events_created': created_event_ids,
        'stacks_created': created_stack_ids,
        'deltas_created': deltas_created
    }


# ---------------------------------------------------------------------------
# Inventory Count - a workorder used as an audit tool
# ---------------------------------------------------------------------------
@dataclass
class CountLine:
    """One item counted, in the counter's own terms.

    ``counted`` is what the person saw on the shelf. Nobody computes a variance to type
    in (Bill, 2026-09-20): the book figure is captured as the line's ``staged`` and the
    difference is shown, so an off count is a signal to hunt harder.
    """
    item_id: int
    counted: Decimal | float | int
    warehouse_code: str
    reason: str = 'cycle_count'          # cycle_count, damage, shrinkage, found, opening
    unit_cost: float | int | Decimal | None = None
    lot: str | None = None
    serial_batch: str | None = None


@transaction.atomic
def count_inventory(count_id: str,
                    lines: Sequence[CountLine],
                    counted_by: str,
                    notes: str = '',
                    contact_id: int | None = None) -> dict:
    """Count inventory through a workorder used as an audit tool.

    Replaces the old ``adjust_inventory``, which created a receipt — a document that says
    goods came from outside and owes a vendor. A count owes nobody: it is a workorder of
    kind 'count', its lines commit nothing, and completing a line moves on_hand to the
    number the counter wrote down.

    Bill, 2026-09-20: *"In wc2 adjustments were loosely held together by date, but with a
    workorder controlling multiple lines there is a responsible person directly
    involved."* So ``counted_by`` is required: a count with nobody's name on it is the
    thing this replaces, and it is refused here rather than accepted and wondered about
    later.

    Each completion is the count evidence: warehouse, lot, the book figure at count time,
    what was counted, who counted it, and whether the book moved while the count was open.

    Args:
        count_id: client-provided identifier (stored in workorder.ida)
        lines: what was counted, per item
        counted_by: the person answerable for this count — required
        notes: optional note for the whole count
        contact_id: that person's contact record, when known

    Returns a summary with the workorder id, its completions, layers and deltas.
    """
    from apps.transactions.models.workorder import WorkOrder
    from apps.transactions.models.workorder_line import WorkOrderLine
    from apps.core.models.pending import Pending

    if not count_id:
        raise ValidationError({'count_id': 'Required'})
    if not (counted_by or '').strip():
        raise ValidationError({'counted_by': 'A count needs the person answerable for it'})

    wo = WorkOrder.objects.create(
        ida=count_id,
        kind=WorkOrder.KIND_COUNT,
        source_name='inventory_count',
        contact_id=contact_id,
        status='complete',           # a count is finished when it is posted
        metadata={'count': {'notes': notes, 'counted_by': counted_by,
                            'lines': len(list(lines))}},
    )
    created_stack_ids: list[int] = []
    created_event_ids: list[str] = []
    variance_total = 0.0
    deltas_created = 0

    for cl in lines:
        try:
            item = Item.objects.get(pk=cl.item_id)
        except Item.DoesNotExist:
            raise ValidationError({'lines': f'Item {cl.item_id} not found'})
        try:
            wh = Warehouse.objects.get(code=cl.warehouse_code)
        except Warehouse.DoesNotExist:
            raise ValidationError({'lines': f'Warehouse code {cl.warehouse_code} not found'})

        counted = Decimal(str(cl.counted))
        book_at_count = Decimal(str((item.quantity or {}).get('on_hand') or 0))

        # The line: staged is the book, active is what the counter saw. A count line
        # commits no bucket (quantity_bucket_deltas), so opening one reserves nothing.
        line = WorkOrderLine.objects.create(
            workorder=wo,
            item={'item_id': item.pk, 'id_num': item.pk,
                  'item_number': getattr(item, 'item_number', ''), 'name': item.name},
            quantity={'staged': float(book_at_count), 'active': float(counted)},
            cost={'unit': float(cl.unit_cost)} if cl.unit_cost else {},
        )

        item.refresh_from_db()
        book_now = Decimal(str((item.quantity or {}).get('on_hand') or 0))
        delta = counted - book_now
        unit_cost = float(cl.unit_cost) if cl.unit_cost is not None else 0.0

        # Found stock needs a cost layer; missing stock takes from the layers that exist.
        stack = None
        if delta > 0:
            stack = InventoryLayer.objects.create(
                item=item,
                warehouse=wh,
                quantity={'received': float(delta), 'issued': 0, 'scrapped': 0},
                lot=cl.lot or '',
                serial_batch=cl.serial_batch or '',
                source_doc_type='inventory_count',
                source_doc_id=line.pk,      # the line that carries the count event
            )
            if unit_cost > 0:
                stack.update_cost_after_receipt(unit_cost)
            stack.save()
            created_stack_ids.append(stack.id)

        event_id = uuid.uuid4().hex
        event = {
            'id': event_id,
            'kind': 'count',
            'dt': _now_ms(),
            'by': counted_by,
            'qty': float(counted),           # what this line has had done to it
            'warehouse_id': wh.id,
            'warehouse_code': wh.code,
            'lot': cl.lot or '',
            'serial_batch': cl.serial_batch or '',
            'layer_id': stack.id if stack else None,
            'unit_cost': unit_cost or None,
            'reason': cl.reason,
            'run': count_id,
            'book_at_count': float(book_at_count),
            'counted': float(counted),
            'book_now': float(book_now),
            'variance': float(counted - book_at_count),
            # If the book moved while the count was open, the counter's number still
            # wins — and the move is on the record rather than swallowed.
            'moved_during_count': book_now != book_at_count,
            'applied': float(delta),
        }
        variance_total += float(counted - book_at_count)
        created_event_ids.append(event_id)

        Pending.objects.create(
            model_name='item',
            record_id=str(item.pk),
            purpose='line_event',
            name=f"Count {count_id} - item {item.pk}",
            changes={'on_hand': float(delta)} if delta else {},
            config={
                'item_id': item.pk,
                'line_model': 'WorkOrderLine',
                'line_id': line.pk,
                'event': event,
                'warehouse_id': wh.id,
                'source_type': 'inventory_count',
                'source_id': wo.id,
                'reason': cl.reason,
                'counted_by': counted_by,
                'unit_cost': unit_cost or None,
                'notes': f"Count {count_id} - counted {counted}, book {book_now} ({delta:+})"
                         + (f" - {notes}" if notes else ""),
            }
        )
        if delta:
            deltas_created += 1

    return {
        'workorder_id': wo.id,  # type: ignore[attr-defined]
        'ida': wo.ida,
        'counted_by': counted_by,
        'events_created': created_event_ids,
        'stacks_created': created_stack_ids,
        'deltas_created': deltas_created,
        'variance_total': round(variance_total, 4),
    }


# ---------------------------------------------------------------------------
# High-Level Dispatcher - routes to appropriate handler by source type
# ---------------------------------------------------------------------------
def receive_inventory_changes(source_type: str,
                              source: Purchase | WorkOrder | None,
                              receipt_id: str,
                              lines: Sequence[ReceiveLine | CompleteWorkOrderLine | CountLine]) -> dict:
    """High-level dispatcher for inventory receiving operations.

    Routes to the appropriate handler based on source_type:
    - 'purchase' -> receive_purchase()
    - 'workorder' -> complete_workorder()
    - 'count' (or 'adjustment') -> count_inventory()

    Args:
        source_type: One of 'purchase', 'workorder', 'adjustment'
        source: The source transaction (Purchase or WorkOrder), None for adjustments
        receipt_id: Client-provided receipt identifier
        lines: Sequence of line objects (type must match source_type)

    Returns a summary dict from the appropriate handler.

    Raises:
        ValidationError: If source_type is invalid or lines don't match expected type

    Example:
        # Receive against a PO
        receive_inventory_changes('purchase', po, 'RCV-001', receive_lines)
        
        # Complete a workorder
        receive_inventory_changes('workorder', wo, 'WO-COMP-001', complete_lines)
        
        # Manual adjustment
        receive_inventory_changes('adjustment', None, 'ADJ-001', adjustment_lines)

    See also:
        - receive_purchase: Direct call for PO receiving
        - complete_workorder: Direct call for workorder completion
        - count_inventory: Direct call for inventory counts
    """
    if source_type == 'purchase':
        if not isinstance(source, Purchase):
            raise ValidationError({'source': 'Expected Purchase instance for source_type=purchase'})
        return receive_purchase(source, receipt_id, lines)  # type: ignore[arg-type]
    
    elif source_type == 'workorder':
        if not isinstance(source, WorkOrder):
            raise ValidationError({'source': 'Expected WorkOrder instance for source_type=workorder'})
        return complete_workorder(source, receipt_id, lines)  # type: ignore[arg-type]
    
    elif source_type in ('count', 'adjustment'):
        # 'adjustment' is the old name for what is now a count workorder: a correction
        # owes nobody, so it is never a receipt (Bill, 2026-09-20).
        return count_inventory(receipt_id, lines)  # type: ignore[arg-type]

    else:
        raise ValidationError({'source_type': f"Invalid source_type '{source_type}'. Expected: purchase, workorder, count"})


__all__ = [
    # Data classes for line input
    'ReceiveLine',
    'CompleteWorkOrderLine',
    'CountLine',
    # Transaction flow conversions
    'quote_to_order',
    'order_to_invoice',
    'order_to_purchase',
    # Inventory receiving functions
    'receive_purchase',
    'complete_workorder',
    'count_inventory',
    'receive_inventory_changes',
]
