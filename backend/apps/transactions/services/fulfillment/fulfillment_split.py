"""Order split by vendor and commission invoicing.

Tradeshow pattern from wc2 — a three-step process:

  Step 1 — Split Order by Vendor (Report: "Split by Vendor"):
    One tradeshow order → N orders, one per manufacturer/vendor.
    Lines with no vendor stay in the original order.
    Each vendor order is sent to that manufacturer to fulfill.

  Step 2 — Manufacturer Fulfills:
    Each vendor-specific order is fulfilled by the manufacturer,
    who ships directly to the customer.

  Step 3 — Commission Invoice (Report: "Commission Invoice"):
    After fulfillment, each vendor order → commission invoice.
    The manufacturer is the 'customer' (they owe us commission).
    Commission lines carry on_so just like real inventory.

Both steps are triggered via Report records in the report selection dialog.
Most companies never use this — it's for the minority that rep other
manufacturers' products.

Usage:
    from apps.transactions.services.fulfillment.fulfillment_split import (
        split_order_by_vendor,
        create_commission_invoice,
    )

    # Step 1: User selects "Split by Vendor" report on order
    result = split_order_by_vendor(order_id=123)

    # Step 3: After fulfillment, user selects "Commission Invoice"
    # report on each vendor-specific order
    result = create_commission_invoice(order_id=456)

If the manufacturer is also the vendor, their vendor_id is used.
Vendor_id is the only grouping key — no manufacturer_id branching.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from django.db import transaction

from apps.transactions.models import Order, OrderLine

logger = logging.getLogger(__name__)


def _now_ms() -> int:
    return int(time.time() * 1000)


# ---------------------------------------------------------------------------
# Step 1 — Split Order by Vendor
# ---------------------------------------------------------------------------

@transaction.atomic
def split_order_by_vendor(order_id: int) -> Dict[str, Any]:
    """Split an order's lines by vendor into separate orders.

    Lines are grouped by item_fk.vendor_id. Each vendor group becomes
    a new order with that vendor set on the header. Lines with no vendor
    stay in the original order.

    The original order's customer, terms, price_level carry forward to
    each vendor order. Source lines are marked as transferred.

    Args:
        order_id: Source order PK

    Returns:
        {source_order_id, retained_line_count, vendor_orders[]}
    """
    try:
        source = Order.objects.select_for_update().get(pk=order_id)
    except Order.DoesNotExist:
        return {'error': f'Order {order_id} not found'}

    lines = list(
        OrderLine.objects.select_for_update()
        .filter(order=source)
        .select_related('item_fk')
    )

    if not lines:
        return {'error': 'Order has no lines'}

    # Group lines by vendor
    vendor_groups: Dict[Optional[int], List[OrderLine]] = defaultdict(list)
    for line in lines:
        item = line.item_fk
        vid = item.vendor_id if item else None
        vendor_groups[vid].append(line)

    # Lines with no vendor stay in the original order
    retained_lines = vendor_groups.pop(None, [])

    vendors_with_lines = [v for v in vendor_groups if v is not None]
    if not vendors_with_lines:
        return {
            'source_order_id': order_id,
            'retained_line_count': len(retained_lines),
            'vendor_orders': [],
            'message': 'No lines with vendors — nothing to split',
        }

    # Copy header fields
    header_fields: Dict[str, Any] = {}
    for field in (
        "customer_id", "contact_id", "price_level",
        "attention",
        "terms", "terms_fk_id", "conditions_id", "conditions_description",
    ):
        val = getattr(source, field, None)
        if val is not None:
            header_fields[field] = val

    # Resolve vendor names
    from django.apps import apps
    OrgBase = apps.get_model('orgs', 'OrgBase')
    vendor_names = {}
    for org in OrgBase.objects.filter(pk__in=vendors_with_lines).only('pk', 'display_name'):
        vendor_names[org.pk] = org.display_name or f'Vendor #{org.pk}'

    # Create one new order per vendor
    vendor_orders = []
    flow_children = []

    for vid, vlines in vendor_groups.items():
        if vid is None:
            continue

        new_order = Order.objects.create(
            status='confirmed',
            vendor_id=vid,
            parent_model='order',
            parent_id=source.pk,
            refs={
                'source': {
                    'order_id': source.pk,
                    'split_by_vendor': True,
                    'vendor_id': vid,
                },
            },
            flow={
                'source': [{'type': 'order', 'id': source.pk}],
                'children': [],
            },
            **header_fields,
        )

        # Copy lines to new order
        line_count = 0
        for src_line in vlines:
            new_line = _copy_line(src_line, new_order, source.pk)
            line_count += 1

            # Mark source line as transferred
            src_line.status = 'transferred'
            src_refs = src_line.refs or {}
            src_refs['split'] = {
                'target_order_id': new_order.pk,
                'target_line_id': new_line.pk,
                'vendor_id': vid,
            }
            src_line.refs = src_refs
            src_line.save(update_fields=['status', 'refs', 'dt_modified', 'version'])

        if hasattr(new_order, 'update_sell_cost_totals'):
            new_order.update_sell_cost_totals()

        vendor_orders.append({
            'order_id': new_order.pk,
            'order_ida': new_order.ida,
            'vendor_id': vid,
            'vendor_name': vendor_names.get(vid, f'Vendor #{vid}'),
            'line_count': line_count,
        })
        flow_children.append({'type': 'order', 'id': new_order.pk, 'vendor_id': vid})

    # Update source order
    source.status = 'split'
    flow = source.flow or {}
    flow['children'] = flow_children
    source.flow = flow
    source.save(update_fields=['status', 'flow', 'dt_modified', 'version'])

    if retained_lines and hasattr(source, 'update_sell_cost_totals'):
        source.update_sell_cost_totals()

    logger.info(
        'Split order #%d: %d vendor orders, %d lines retained',
        order_id, len(vendor_orders), len(retained_lines),
    )

    return {
        'source_order_id': order_id,
        'retained_line_count': len(retained_lines),
        'vendor_orders': vendor_orders,
    }


def _copy_line(
    src_line: OrderLine,
    target_order: Order,
    source_order_id: int,
) -> OrderLine:
    """Copy an order line to a new order."""
    kwargs = {
        "order": target_order,
        "status": "pending",
        "price_level": getattr(src_line, "price_level", "") or "",
        "quantity": dict(getattr(src_line, "quantity", None) or {}),
        "cost": dict(getattr(src_line, "cost", None) or {}),
        "tax": dict(getattr(src_line, "tax", None) or {}),
        "physical": dict(getattr(src_line, "physical", None) or {}),
        "item": dict(getattr(src_line, "item", None) or {}),
        "price": dict(getattr(src_line, "price", None) or {}),
        "refs": {
            "source": {
                "order_line_id": src_line.pk,
                "order_id": source_order_id,
                "split_by_vendor": True,
            },
        },
    }
    item_fk_id = getattr(src_line, "item_fk_id", None)
    if item_fk_id:
        kwargs["item_fk_id"] = item_fk_id

    return OrderLine.objects.create(**kwargs)


# ---------------------------------------------------------------------------
# Step 3 — Commission Invoice (after manufacturer fulfills)
# ---------------------------------------------------------------------------

@transaction.atomic
def create_commission_invoice(
    order_id: int,
) -> Dict[str, Any]:
    """Create a commission invoice for a vendor-specific order.

    Called after the manufacturer fulfills the order. The manufacturer
    becomes the 'customer' on the invoice — they owe us commission.
    Commission lines carry on_so through the Pending system just like
    real product lines.

    Args:
        order_id: Vendor-specific order PK (from split_order_by_vendor)

    Returns:
        {invoice_id, invoice_ida, vendor_id, vendor_name, commission_total, line_count}
    """
    from apps.transactions.models import Invoice, InvoiceLine
    from apps.transactions.services.line_manage import (
        LineItemService, _should_track_inventory,
    )

    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return {'error': f'Order {order_id} not found'}

    vendor_id = order.vendor_id
    if not vendor_id:
        return {'error': 'Order has no vendor — cannot create commission invoice'}

    lines = list(OrderLine.objects.filter(order=order).select_related('item_fk'))
    if not lines:
        return {'error': 'Order has no lines'}

    # Resolve vendor name
    from django.apps import apps
    OrgBase = apps.get_model('orgs', 'OrgBase')
    vendor_name = ''
    try:
        vendor = OrgBase.objects.get(pk=vendor_id)
        vendor_name = vendor.display_name or f'Vendor #{vendor_id}'
    except OrgBase.DoesNotExist:
        vendor_name = f'Vendor #{vendor_id}'

    # Get commission data
    order_comm = order.commission or {}

    # Create invoice — manufacturer is the 'customer' (they owe us)
    invoice = Invoice.objects.create(
        status='pending',
        customer_id=vendor_id,
        vendor_id=vendor_id,
        parent_model='order',
        parent_id=order.pk,
        price_level=getattr(order, 'price_level', '') or '',
        refs={
            'source': {
                'order_id': order.pk,
                'commission_invoice': True,
                'original_customer_id': order.customer_id,
            },
        },
        flow={
            'source': [{'type': 'order', 'id': order.pk}],
            'children': [],
        },
        metadata={
            'invoice_type': 'commission',
            'vendor_id': vendor_id,
            'vendor_name': vendor_name,
        },
    )

    commission_total = 0.0
    line_count = 0
    lis = LineItemService(create_pending=True)

    for src_line in lines:
        # Get commission amount for this line
        line_comm = getattr(src_line, 'commission', None) or {}
        comm_amount = line_comm.get('total', 0)

        if not comm_amount:
            # Prorate header commission by line's share of order total
            header_total = order_comm.get('total', 0)
            if header_total:
                src_price = (src_line.price or {}).get('extended', 0) or 0
                order_sell = (order.sell or {}).get('total', 0) or 0
                if order_sell > 0:
                    comm_amount = round(header_total * (src_price / order_sell), 2)

        if not comm_amount:
            continue

        # Mirror source quantity so on_so tracks like real inventory
        src_qty = dict(getattr(src_line, 'quantity', None) or {})
        qty_staged = src_qty.get('staged', 0) or src_qty.get('active', 0) or 1

        item_data = dict(getattr(src_line, 'item', None) or {})
        item_data['commission_line'] = True

        unit_comm = round(comm_amount / qty_staged, 4) if qty_staged else comm_amount

        inv_line = InvoiceLine(
            invoice=invoice,
            status='pending',
            line_type='commission',
            item=item_data,
            item_fk_id=getattr(src_line, 'item_fk_id', None),
            quantity={
                'staged': qty_staged,
                'active': qty_staged,
                'remaining': qty_staged,
            },
            price={
                'unit': unit_comm,
                'extended': comm_amount,
                'unit_base': unit_comm,
            },
            cost={'unit': 0, 'extended': 0},
            refs={
                'source': {
                    'order_line_id': src_line.pk,
                    'order_id': order.pk,
                    'commission_invoice': True,
                },
            },
        )
        inv_line._pending_created = True
        inv_line.save()

        # Create Pending record — on_so tracking like real inventory
        if _should_track_inventory('invoice'):
            item_fk = src_line.item_fk
            if item_fk:
                lis._create_pending_for_line_add(
                    transaction=invoice,
                    transaction_type='invoice',
                    line=inv_line,
                    item=item_fk,
                    quantity=float(qty_staged),
                    unit_cost=0,
                    unit_price=float(unit_comm),
                )

        commission_total += comm_amount
        line_count += 1

    if line_count == 0:
        invoice.delete()
        return {'error': 'No commission amounts found on order lines'}

    if hasattr(invoice, 'update_sell_cost_totals'):
        invoice.update_sell_cost_totals()

    # Update order flow
    flow = order.flow or {}
    children = flow.get('children', [])
    children.append({
        'type': 'invoice',
        'id': invoice.pk,
        'commission_invoice': True,
    })
    flow['children'] = children
    order.flow = flow
    order.save(update_fields=['flow', 'dt_modified', 'version'])

    logger.info(
        'Commission invoice #%d for order #%d, vendor=%s, total=%.2f',
        invoice.pk, order_id, vendor_name, commission_total,
    )

    return {
        'invoice_id': invoice.pk,
        'invoice_ida': invoice.ida,
        'vendor_id': vendor_id,
        'vendor_name': vendor_name,
        'commission_total': commission_total,
        'line_count': line_count,
    }
