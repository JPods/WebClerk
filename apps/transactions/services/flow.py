from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Sequence

from django.db import transaction
from django.core.exceptions import ValidationError

from apps.transactions.models import (
    Proposal, ProposalLine,
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
# when creating a new transactional line from another (proposal -> order,
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
    # Extended / newer additions (may be no-ops until fields are present):
    'metadata', 'refs', 'prefs', 'comments'
)


@dataclass
class ReceiveLine:
    po_line_id: int
    qty: Decimal | float | int
    warehouse_code: str
    unit_cost: float | int | Decimal | None = None
    lot: str | None = None
    serial_batch: str | None = None


def _copy_common_line_fields(src: ProposalLine | OrderLine | PurchaseLine,
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
                        for k in ('ordered', 'placed', 'shipped', 'packed', 'extended', 'unit', 'remaining'):
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


def proposal_to_order(proposal: Proposal, order_no: Optional[str] = None) -> Order:
    so = Order.objects.create(order_no=order_no or f"SO-{proposal.pk or 'new'}")
    src_lines = list(ProposalLine.objects.filter(parent=proposal).order_by('id'))
    # Linkage disabled - pass None
    linkage_id = None
    # Copy lines after ensuring linkage id
    for pl in src_lines:
        sol = OrderLine(parent=so)
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
        # proposal quantity schema can be different; leave as-is and let later edits normalize
        sol.save()
    return so


@transaction.atomic
def order_to_invoice(so: Order, invoice_no: Optional[str] = None) -> Invoice:
    # invoice_no is deprecated; ida is auto-generated from id.
    inv = Invoice.objects.create()
    src_lines = list(OrderLine.objects.filter(parent=so).order_by('id'))
    linkage_id = ensure_linkage_for_lines(src_lines) if src_lines else None
    for sol in src_lines:
        il = InvoiceLine(parent=inv)
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
def order_to_purchase_order(so: Order, po_no: Optional[str] = None) -> Purchase:
    """Create a supporting Purchase from an Order.

    Propagates / creates linkage id across involved lines to maintain unified
    comment & lineage chain.
    """
    po = Purchase.objects.create(po_no=po_no or f"PO-SO-{so.pk or 'new'}")
    src_lines = list(OrderLine.objects.filter(parent=so).order_by('id'))
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


def _resolve_item_id_from_line(line: PurchaseLine | OrderLine | ProposalLine | WorkOrderLine) -> Optional[int]:
    item = getattr(line, 'item', {}) or {}
    # Prefer id_num, fallback: try 'id' or 'item_id' if present
    return item.get('id_num') or item.get('id') or item.get('item_id')


@transaction.atomic
def receive_purchase_order(po: Purchase,
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
        - adjust_inventory: For manual inventory adjustments
        - receive_inventory_changes: High-level dispatcher for all receiving actions
    """
    from apps.transactions.models.receipt import Receipt, ReceiptLine
    from apps.core.models.pending import Pending
    from django.utils import timezone
    import uuid

    if not receipt_id:
        raise ValidationError({'receipt_id': 'Required'})

    receipt = Receipt.objects.create(
        ida=receipt_id,
        source_type=Receipt.SOURCE_PURCHASE,
        purchase=po,
    )
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

        # Create ReceiptLine record to track what was received
        receipt_line = ReceiptLine.objects.create(
            receipt=receipt,
            purchase_line=pol,
            warehouse=wh,
            inventory_layer=stack,
            lot=rl.lot or '',
            serial_batch=rl.serial_batch or '',
            item=pol.item or {'item_id': item_id},  # Copy item JSON from PO line
            quantity={'placed': float(rl.qty), 'received': float(rl.qty)},
            cost={'unit': unit_cost, 'extended': float(rl.qty) * unit_cost},
        )
        created_receipt_line_ids.append(receipt_line.id)

        # Create inventory delta for item-level quantity tracking
        qty_received = Decimal(str(rl.qty))
        record_id = f"{item_id}_{int(timezone.now().timestamp() * 1000000)}_{uuid.uuid4().hex[:8]}"

        Pending.objects.create(
            model_name='inventory_delta',
            record_id=record_id,
            purpose='inventory_delta',
            name=f"Inventory delta for item {item_id}",
            data={
                'item_id': item_id,
                'warehouse_id': wh.id,
                'quantity_on_hand_delta': float(qty_received),  # Increase on-hand
                'quantity_on_order_delta': 0,
                'quantity_on_po_delta': -float(qty_received),  # Decrease on-PO
                'source_type': 'purchase_receipt',
                'source_id': receipt.id,
                'source_line_id': receipt_line.id,  # Reference ReceiptLine instead of PurchaseLine
                'unit_cost': unit_cost,
                'notes': f"Purchase receipt {receipt.ida} - received {qty_received} units",
                'created_at': timezone.now().isoformat()
            }
        )
        deltas_created += 1

        # Optional: update PO line received quantity hint
        if isinstance(pol.quantity, dict):
            prev = pol.quantity.get('received') or 0
            try:
                pol.quantity['received'] = float(prev) + float(rl.qty)
            except Exception:
                pol.quantity['received'] = float(rl.qty)
            pol.save(update_fields=['quantity', 'dt_modified', 'version'])

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
                       lines: Sequence[CompleteWorkOrderLine]) -> dict:
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
        - receive_purchase_order: For receiving goods from vendors (PO)
        - adjust_inventory: For manual inventory adjustments
        - receive_inventory_changes: High-level dispatcher for all receiving actions
    """
    from apps.transactions.models.receipt import Receipt, ReceiptLine
    from apps.core.models.pending import Pending
    from django.utils import timezone
    import uuid

    if not receipt_id:
        raise ValidationError({'receipt_id': 'Required'})

    receipt = Receipt.objects.create(
        ida=receipt_id,
        source_type=Receipt.SOURCE_WORKORDER,
        workorder=wo,
    )
    created_stack_ids: list[int] = []
    created_receipt_line_ids: list[int] = []
    deltas_created = 0

    for cl in lines:
        try:
            wol = WorkOrderLine.objects.select_related('workorder_id').get(pk=cl.wo_line_id, workorder_id=wo)
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
            source_doc_id=receipt.id,  # type: ignore[attr-defined]
        )
        # Use provided unit_cost or estimate from workorder line cost
        unit_cost = float(cl.unit_cost) if cl.unit_cost is not None else float((wol.cost or {}).get('unit') or 0)
        stack.update_cost_after_receipt(unit_cost)
        stack.save()
        created_stack_ids.append(stack.id)

        # Create ReceiptLine record to track what was completed
        receipt_line = ReceiptLine.objects.create(
            receipt=receipt,
            workorder_line=wol,
            warehouse=wh,
            inventory_layer=stack,
            lot=cl.lot or '',
            serial_batch=cl.serial_batch or '',
            item=wol.item or {'item_id': item_id},  # Copy item JSON from WO line
            quantity={'placed': float(cl.qty_completed), 'received': float(cl.qty_completed)},
            cost={'unit': unit_cost, 'extended': float(cl.qty_completed) * unit_cost},
        )
        created_receipt_line_ids.append(receipt_line.id)

        # Create inventory delta for item-level quantity tracking
        qty_completed = Decimal(str(cl.qty_completed))
        record_id = f"{item_id}_{int(timezone.now().timestamp() * 1000000)}_{uuid.uuid4().hex[:8]}"

        Pending.objects.create(
            model_name='inventory_delta',
            record_id=record_id,
            purpose='inventory_delta',
            name=f"Inventory delta for item {item_id}",
            data={
                'item_id': item_id,
                'warehouse_id': wh.id,
                'quantity_on_hand_delta': float(qty_completed),  # Increase on-hand (produced)
                'quantity_on_wo_delta': -float(qty_completed),   # Decrease on-WO (no longer WIP)
                'source_type': 'workorder_completion',
                'source_id': receipt.id,
                'source_line_id': receipt_line.id,  # Reference ReceiptLine
                'unit_cost': unit_cost,
                'notes': f"WorkOrder completion {receipt.ida} - produced {qty_completed} units",
                'created_at': timezone.now().isoformat()
            }
        )
        deltas_created += 1

        # Optional: update WO line completed quantity hint
        if isinstance(wol.quantity, dict):
            prev = wol.quantity.get('completed') or 0
            try:
                wol.quantity['completed'] = float(prev) + float(cl.qty_completed)
            except Exception:
                wol.quantity['completed'] = float(cl.qty_completed)
            wol.save(update_fields=['quantity', 'dt_modified', 'version'])

    return {
        'receipt_id': receipt.id,  # type: ignore[attr-defined]
        'receipt_lines_created': created_receipt_line_ids,
        'stacks_created': created_stack_ids,
        'deltas_created': deltas_created
    }


# ---------------------------------------------------------------------------
# Inventory Adjustment - manual corrections, cycle counts, write-offs
# ---------------------------------------------------------------------------
@dataclass
class AdjustmentLine:
    """Data for an inventory adjustment line."""
    item_id: int
    qty_delta: Decimal | float | int  # Positive = add, Negative = remove
    warehouse_code: str
    reason: str  # e.g., 'cycle_count', 'damage', 'shrinkage', 'found'
    unit_cost: float | int | Decimal | None = None
    lot: str | None = None
    serial_batch: str | None = None


@transaction.atomic
def adjust_inventory(adjustment_id: str,
                     lines: Sequence[AdjustmentLine],
                     notes: str = '') -> dict:
    """Perform manual inventory adjustments.

    Used for:
    - Cycle count corrections
    - Damage/shrinkage write-offs
    - Found inventory additions
    - Opening balance entries

    Args:
        adjustment_id: Client-provided adjustment identifier (stored in receipt.ida)
        lines: Sequence of AdjustmentLine objects with item, qty_delta, warehouse
        notes: Optional overall notes for the adjustment

    Returns a summary dict with created receipt id, stack ids, and deltas created.

    See also:
        - receive_purchase_order: For receiving goods from vendors (PO)
        - complete_workorder: For workorder completion (manufacturing)
        - receive_inventory_changes: High-level dispatcher for all receiving actions
    """
    from apps.transactions.models.receipt import Receipt, ReceiptLine
    from apps.core.models.pending import Pending
    from django.utils import timezone
    import uuid

    if not adjustment_id:
        raise ValidationError({'adjustment_id': 'Required'})

    receipt = Receipt.objects.create(
        ida=adjustment_id,
        source_type=Receipt.SOURCE_ADJUSTMENT,
    )
    created_stack_ids: list[int] = []
    created_receipt_line_ids: list[int] = []
    deltas_created = 0

    for al in lines:
        try:
            item = Item.objects.get(pk=al.item_id)
        except Item.DoesNotExist:
            raise ValidationError({'lines': f'Item {al.item_id} not found'})
        try:
            wh = Warehouse.objects.get(code=al.warehouse_code)
        except Warehouse.DoesNotExist:
            raise ValidationError({'lines': f'Warehouse code {al.warehouse_code} not found'})

        qty_delta = Decimal(str(al.qty_delta))
        unit_cost = float(al.unit_cost) if al.unit_cost is not None else 0.0
        stack = None
        
        # Create inventory layer stack for positive adjustments only
        if qty_delta > 0:
            stack = InventoryLayer.objects.create(
                item=item,
                warehouse=wh,
                quantity={'received': float(qty_delta), 'issued': 0, 'scrapped': 0},
                lot=al.lot or '',
                serial_batch=al.serial_batch or '',
                source_doc_type='inventory_adjustment',
                source_doc_id=receipt.id,  # type: ignore[attr-defined]
            )
            if unit_cost > 0:
                stack.update_cost_after_receipt(unit_cost)
            stack.save()
            created_stack_ids.append(stack.id)

        # Create ReceiptLine record to track the adjustment
        receipt_line = ReceiptLine.objects.create(
            receipt=receipt,
            warehouse=wh,
            inventory_layer=stack,  # None for negative adjustments
            lot=al.lot or '',
            serial_batch=al.serial_batch or '',
            adjustment_reason=al.reason,
            item={'item_id': al.item_id, 'item_number': item.item_number, 'name': item.name},
            quantity={'adjustment': float(qty_delta)},  # Can be negative
            cost={'unit': unit_cost, 'extended': float(qty_delta) * unit_cost} if unit_cost else {},
        )
        created_receipt_line_ids.append(receipt_line.id)

        # Create inventory delta for item-level quantity tracking
        record_id = f"{al.item_id}_{int(timezone.now().timestamp() * 1000000)}_{uuid.uuid4().hex[:8]}"

        Pending.objects.create(
            model_name='inventory_delta',
            record_id=record_id,
            purpose='inventory_delta',
            name=f"Inventory adjustment for item {al.item_id}",
            data={
                'item_id': al.item_id,
                'warehouse_id': wh.id,
                'quantity_on_hand_delta': float(qty_delta),  # Direct on-hand change
                'source_type': 'inventory_adjustment',
                'source_id': receipt.id,
                'source_line_id': receipt_line.id,  # Reference ReceiptLine
                'adjustment_reason': al.reason,
                'unit_cost': unit_cost if unit_cost else None,
                'notes': f"Inventory adjustment {receipt.ida} - {al.reason}: {qty_delta:+} units" + (f" - {notes}" if notes else ""),
                'created_at': timezone.now().isoformat()
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
# High-Level Dispatcher - routes to appropriate handler by source type
# ---------------------------------------------------------------------------
def receive_inventory_changes(source_type: str,
                              source: Purchase | WorkOrder | None,
                              receipt_id: str,
                              lines: Sequence[ReceiveLine | CompleteWorkOrderLine | AdjustmentLine]) -> dict:
    """High-level dispatcher for inventory receiving operations.

    Routes to the appropriate handler based on source_type:
    - 'purchase' -> receive_purchase_order()
    - 'workorder' -> complete_workorder()
    - 'adjustment' -> adjust_inventory()

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
        - receive_purchase_order: Direct call for PO receiving
        - complete_workorder: Direct call for workorder completion
        - adjust_inventory: Direct call for manual adjustments
    """
    if source_type == 'purchase':
        if not isinstance(source, Purchase):
            raise ValidationError({'source': 'Expected Purchase instance for source_type=purchase'})
        return receive_purchase_order(source, receipt_id, lines)  # type: ignore[arg-type]
    
    elif source_type == 'workorder':
        if not isinstance(source, WorkOrder):
            raise ValidationError({'source': 'Expected WorkOrder instance for source_type=workorder'})
        return complete_workorder(source, receipt_id, lines)  # type: ignore[arg-type]
    
    elif source_type == 'adjustment':
        return adjust_inventory(receipt_id, lines)  # type: ignore[arg-type]
    
    else:
        raise ValidationError({'source_type': f"Invalid source_type '{source_type}'. Expected: purchase, workorder, adjustment"})


__all__ = [
    # Data classes for line input
    'ReceiveLine',
    'CompleteWorkOrderLine',
    'AdjustmentLine',
    # Transaction flow conversions
    'proposal_to_order',
    'order_to_invoice',
    'order_to_purchase_order',
    # Inventory receiving functions
    'receive_purchase_order',
    'complete_workorder',
    'adjust_inventory',
    'receive_inventory_changes',
    # Legacy aliases (deprecated)
    'proposal_to_sales_order',
    'sales_order_to_invoice',
    'sales_order_to_purchase_order',
]

# Legacy aliases for backwards compatibility
proposal_to_sales_order = proposal_to_order
sales_order_to_invoice = order_to_invoice
sales_order_to_purchase_order = order_to_purchase_order
