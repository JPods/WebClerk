from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Optional, Sequence

from django.db import transaction
from django.core.exceptions import ValidationError

from apps.transactions.models.line_variants import (
    Proposal, ProposalLine,
    SalesOrder, SalesOrderLine,
    Invoice, InvoiceLine,
    PurchaseOrder, PurchaseOrderLine,
)
from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse
from apps.products.models.inventory_layer import InventoryStack


@dataclass
class ReceiveLine:
    po_line_id: int
    qty: Decimal | float | int
    warehouse_code: str
    unit_cost: float | int | Decimal | None = None
    lot: str | None = None
    serial_batch: str | None = None


def _copy_common_line_fields(src: ProposalLine | SalesOrderLine | PurchaseOrderLine,
                             dst: SalesOrderLine | InvoiceLine | PurchaseOrderLine):
    # Copy JSON envelopes and scalars that make sense; parent_ref_id is set in save()
    dst.status = src.status
    dst.type_sale = src.type_sale
    dst.probability = getattr(src, 'probability', None)
    # Use setattr to keep static type checkers from mis-inferring JSONField descriptors
    setattr(dst, 'item', (getattr(src, 'item', {}) or {}).copy())
    setattr(dst, 'quantity', (getattr(src, 'quantity', {}) or {}).copy())
    setattr(dst, 'cost', (getattr(src, 'cost', {}) or {}).copy())
    setattr(dst, 'price', (getattr(src, 'price', {}) or {}).copy())
    setattr(dst, 'tax', (getattr(src, 'tax', {}) or {}).copy())
    setattr(dst, 'action', (getattr(src, 'action', {}) or {}).copy())
    setattr(dst, 'physical', (getattr(src, 'physical', {}) or {}).copy())
    setattr(dst, 'flow', (getattr(src, 'flow', {}) or {}).copy())
    setattr(dst, 'source', (getattr(src, 'source', {}) or {}).copy())


@transaction.atomic
def proposal_to_sales_order(proposal: Proposal, order_no: Optional[str] = None) -> SalesOrder:
    so = SalesOrder.objects.create(order_no=order_no or f"SO-{proposal.pk or 'new'}")
    # Copy lines
    for pl in ProposalLine.objects.filter(parent=proposal).order_by('id'):
        sol = SalesOrderLine(parent=so)
        _copy_common_line_fields(pl, sol)
        # proposal quantity schema can be different; leave as-is and let later edits normalize
        sol.save()
    return so


@transaction.atomic
def sales_order_to_invoice(so: SalesOrder, invoice_no: Optional[str] = None) -> Invoice:
    inv = Invoice.objects.create(invoice_no=invoice_no or f"INV-{so.pk or 'new'}")
    for sol in SalesOrderLine.objects.filter(parent=so).order_by('id'):
        il = InvoiceLine(parent=inv)
        _copy_common_line_fields(sol, il)
        # price becomes authoritative for billing; leave quantities/prices as provided
        il.save()
    return inv


def _resolve_item_id_from_line(line: PurchaseOrderLine | SalesOrderLine | ProposalLine) -> Optional[int]:
    item = getattr(line, 'item', {}) or {}
    # Prefer id_num, fallback: try 'id' or 'item_id' if present
    return item.get('id_num') or item.get('id') or item.get('item_id')


@transaction.atomic
def receive_purchase_order(po: PurchaseOrder,
                           receipt_no: str,
                           lines: Sequence[ReceiveLine]) -> dict:
    """Post a receipt for a PO and create inventory stacks accordingly.

    Returns a summary dict with created receipt id and stack ids.
    """
    from apps.transactions.models.purchase_receipt import PurchaseReceipt

    if not receipt_no:
        raise ValidationError({'receipt_no': 'Required'})

    receipt = PurchaseReceipt.objects.create(receipt_no=receipt_no)
    created_stack_ids: list[int] = []
    for rl in lines:
        try:
            pol = PurchaseOrderLine.objects.select_related('parent').get(pk=rl.po_line_id, parent=po)
        except PurchaseOrderLine.DoesNotExist:
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

        stack = InventoryStack.objects.create(
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

        # Optional: update PO line received quantity hint
        if isinstance(pol.quantity, dict):
            prev = pol.quantity.get('received') or 0
            try:
                pol.quantity['received'] = float(prev) + float(rl.qty)
            except Exception:
                pol.quantity['received'] = float(rl.qty)
            pol.save(update_fields=['quantity', 'dt_modified', 'version'])

    return {'receipt_id': receipt.id, 'stacks_created': created_stack_ids}  # type: ignore[attr-defined]


__all__ = [
    'ReceiveLine',
    'proposal_to_sales_order',
    'sales_order_to_invoice',
    'receive_purchase_order',
]
