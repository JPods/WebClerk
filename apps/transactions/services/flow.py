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
from apps.docs.models.linkage import Linkage
from apps.docs.models.linkage_index import LinkageIndex
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
# Linkage helpers
# ---------------------------------------------------------------------------
def ensure_linkage_for_lines(lines) -> int:
    """Ensure a shared linkage id exists for the provided source lines.

    If any line already has a linkage id in refs.links.linkage, that id is
    returned. Otherwise a new Linkage record is created (purpose=transaction_flow)
    and assigned to all lines (persisted). Returns the linkage id.
    """
    existing_id = None
    for ln in lines:
        refs = getattr(ln, 'refs', {}) or {}
        if isinstance(refs, dict):
            links = refs.get('links') or {}
            if isinstance(links, dict):
                linkage_list = links.get('linkage') or []
                if isinstance(linkage_list, list) and linkage_list:
                    existing_id = linkage_list[0]
                    break
    if existing_id:
        return existing_id
    linkage = Linkage.objects.create(purpose='transaction_flow')
    # Populate linkage.refs.links with initial line ids grouped by table name
    links_container = linkage.refs.get('links') if isinstance(getattr(linkage, 'refs', {}), dict) else None
    if not isinstance(links_container, dict):
        linkage.refs = linkage.refs if isinstance(linkage.refs, dict) else {}
        linkage.refs['links'] = {}
        links_container = linkage.refs['links']
    for ln in lines:
        try:
            table = ln._meta.db_table  # type: ignore[attr-defined]
            lst = links_container.setdefault(table, [])
            if ln.pk:
                lst.append(ln.pk)
                # Maintain index row; ignore duplicates during rebuild flows
                try:
                    LinkageIndex.objects.get_or_create(linkage=linkage, table_name=table, record_id=ln.pk)
                except Exception:
                    pass
        except Exception:
            continue
    linkage.save(update_fields=['refs', 'dt_modified', 'version'])  # type: ignore[attr-defined]
    for ln in lines:
        try:
            refs = getattr(ln, 'refs', {}) or {}
            if not isinstance(refs, dict):
                refs = {}
            links = refs.setdefault('links', {"linkage": []})
            linkage_list = links.setdefault('linkage', [])
            if not linkage_list:
                linkage_list.append(linkage.id)
            setattr(ln, 'refs', refs)
            ln.save(update_fields=['refs', 'dt_modified', 'version'])  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover
            pass
    return linkage.id


def proposal_to_order(proposal: Proposal, order_no: Optional[str] = None) -> Order:
    so = Order.objects.create(order_no=order_no or f"SO-{proposal.pk or 'new'}")
    src_lines = list(ProposalLine.objects.filter(parent=proposal).order_by('id'))
    if src_lines:
        linkage_id = ensure_linkage_for_lines(src_lines)
    else:
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


def _resolve_item_id_from_line(line: PurchaseLine | OrderLine | ProposalLine) -> Optional[int]:
    item = getattr(line, 'item', {}) or {}
    # Prefer id_num, fallback: try 'id' or 'item_id' if present
    return item.get('id_num') or item.get('id') or item.get('item_id')


@transaction.atomic
def receive_purchase_order(po: Purchase,
                           receipt_no: str,
                           lines: Sequence[ReceiveLine]) -> dict:
    """Post a receipt for a PO, create inventory stacks, and inventory deltas.

    When goods are received:
    - Increases quantity_on_hand
    - Decreases quantity_on_po
    - Creates inventory layer stacks for warehouse tracking

    Returns a summary dict with created receipt id, stack ids, and deltas created.
    """
    from apps.transactions.models.receipt import Receipt
    from apps.core.models.pending import Pending
    from django.utils import timezone
    import uuid

    if not receipt_no:
        raise ValidationError({'receipt_no': 'Required'})

    receipt = Receipt.objects.create(receipt_no=receipt_no)
    created_stack_ids: list[int] = []
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
                'source_line_id': pol.id,
                'unit_cost': unit_cost,
                'notes': f"Purchase receipt {receipt.receipt_no} - received {qty_received} units",
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
        'stacks_created': created_stack_ids,
        'deltas_created': deltas_created
    }


__all__ = [
    'ReceiveLine',
    'proposal_to_sales_order',
    'sales_order_to_invoice',
    'sales_order_to_purchase_order',
    'receive_purchase_order',
]
