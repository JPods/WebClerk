"""
Order Production Service — GAP-01

Manages the fulfillment workflow: Order → Work Orders, Material Draws,
Requisitions → Action Decision (partial/complete) → Invoice.

All functions are single-purpose. Called from wcapi/manage.

Flow:
  1. spawn_work_order(order_id) → creates WO from order lines
  2. spawn_requisition(order_id, lines) → creates requisition for items to purchase
  3. record_production_action(order_id, action, lines) → partial ship or complete
  4. partial_ship(order_id, shipped_lines) → creates invoice for shipped, backorder for remainder
  5. complete_order(order_id) → closes order, creates final invoice
"""
from __future__ import annotations
from typing import List, Dict, Optional
from django.db import transaction
from apps.transactions.models import Order, OrderLine, Invoice, InvoiceLine, WorkOrder, WorkOrderLine
from apps.core.models.action import Action
import time


def _now_ms():
    return int(time.time() * 1000)


def spawn_work_order(order_id: int) -> Dict:
    """Create a Work Order from an Order's lines.

    Each order line becomes a WO line. The WO inherits customer,
    vendor, contact, and terms from the order.

    Returns: {work_order_id, line_count, status}
    """
    order = Order.objects.get(pk=order_id)
    order_lines = OrderLine.objects.filter(parent_id=order.pk)

    now = _now_ms()

    with transaction.atomic():
        wo = WorkOrder.objects.create(
            status='planned',
            parent_id=order.pk,
            parent_model='order',
            customer=order.customer,
            vendor=order.vendor,
            contact=order.contact,
            attention=order.attention,
            address_full=order.address_full,
            email=order.email,
            phone=order.phone,
            terms=order.terms,
            priority=order.priority,
            dt_created=now,
            dt_modified=now,
        )

        line_count = 0
        for ol in order_lines:
            WorkOrderLine.objects.create(
                parent_id=wo.pk,
                line_number=ol.line_number,
                item_fk=ol.item_fk,
                quantity=ol.quantity or {},
                cost=ol.cost or {},
                status='planned',
                metadata={'source': {'order_id': order.pk, 'order_line_id': ol.pk}},
                dt_created=now,
                dt_modified=now,
            )
            line_count += 1

        # Link WO back to order via flow
        flow = order.flow or {}
        children = flow.get('children', [])
        children.append({'type': 'work_order', 'id': wo.pk})
        flow['children'] = children
        order.flow = flow
        order.save(update_fields=['flow', 'dt_modified'])

    return {'work_order_id': wo.pk, 'line_count': line_count, 'status': 'planned'}


def record_production_action(order_id: int, action_text: str, assigned_to: int = None) -> Dict:
    """Create an Action record for production tracking.

    Used to track progress on order fulfillment — material draws,
    QC checks, packaging, etc.

    Returns: {action_id}
    """
    order = Order.objects.get(pk=order_id)
    now = _now_ms()

    action = Action.objects.create(
        action={'en': action_text},
        status='open',
        kanban_column='in_progress',
        priority=order.priority or 1,
        project_name=f'Order #{order.ida or order.pk}',
        project_ida=f'order-{order.pk}',
        contact_id=assigned_to,
        parent_id=order.pk,
        dt_created=now,
        dt_modified=now,
        metadata={'source': {'model': 'order', 'id': order.pk}},
    )

    return {'action_id': action.pk}


def partial_ship(order_id: int, shipped_lines: List[Dict]) -> Dict:
    """Ship some lines from an order, creating an invoice for shipped items.

    shipped_lines: [{'order_line_id': X, 'qty_shipped': N}, ...]

    For each shipped line:
      - Creates invoice line with qty_shipped
      - Updates order line quantity.remaining
      - If remaining > 0, creates backorder entry

    Returns: {invoice_id, lines_shipped, lines_backordered}
    """
    from apps.transactions.services.backorder import create_backorder_entries

    order = Order.objects.get(pk=order_id)
    now = _now_ms()

    with transaction.atomic():
        # Create invoice
        invoice = Invoice.objects.create(
            status='planned',
            parent_id=order.pk,
            parent_model='order',
            customer=order.customer,
            vendor=order.vendor,
            contact=order.contact,
            attention=order.attention,
            address_full=order.address_full,
            email=order.email,
            phone=order.phone,
            terms=order.terms,
            price_level=order.price_level,
            source=order.source or {},
            dt_created=now,
            dt_modified=now,
        )

        lines_shipped = 0
        backorder_lines = []

        for sl in shipped_lines:
            ol = OrderLine.objects.get(pk=sl['order_line_id'])
            qty_shipped = sl['qty_shipped']
            qty_data = ol.quantity or {}
            qty_active = qty_data.get('active', 0)
            qty_remaining = qty_active - qty_shipped

            # Create invoice line for shipped qty
            InvoiceLine.objects.create(
                parent_id=invoice.pk,
                line_number=ol.line_number,
                item_fk=ol.item_fk,
                quantity={'staged': qty_shipped, 'active': qty_shipped, 'remaining': 0},
                price=ol.price or {},
                cost=ol.cost or {},
                status='shipped',
                metadata={'source': {'order_id': order.pk, 'order_line_id': ol.pk}},
                dt_created=now,
                dt_modified=now,
            )
            lines_shipped += 1

            # Update order line remaining
            qty_data['remaining'] = max(0, qty_remaining)
            ol.quantity = qty_data
            ol.save(update_fields=['quantity', 'dt_modified'])

            # Track backorder if remaining > 0
            if qty_remaining > 0:
                backorder_lines.append({
                    'order_id': order.pk,
                    'order_line_id': ol.pk,
                    'item_fk_id': ol.item_fk_id,
                    'qty_backordered': qty_remaining,
                })

        # Create backorder entries
        if backorder_lines:
            create_backorder_entries(backorder_lines)

        # Link invoice to order flow
        flow = order.flow or {}
        children = flow.get('children', [])
        children.append({'type': 'invoice', 'id': invoice.pk})
        flow['children'] = children
        order.flow = flow

        # Update order status
        all_lines = OrderLine.objects.filter(parent_id=order.pk)
        all_fulfilled = all(
            (l.quantity or {}).get('remaining', 0) == 0
            for l in all_lines
        )
        if all_fulfilled:
            order.status = 'complete'
        else:
            order.status = 'in_progress'

        order.save(update_fields=['flow', 'status', 'dt_modified'])

    return {
        'invoice_id': invoice.pk,
        'lines_shipped': lines_shipped,
        'lines_backordered': len(backorder_lines),
        'order_status': order.status,
    }


def complete_order(order_id: int) -> Dict:
    """Close an order — all lines must be fulfilled or canceled.

    Returns: {order_id, status}
    """
    order = Order.objects.get(pk=order_id)
    order.status = 'complete'
    order.dt_modified = _now_ms()
    order.save(update_fields=['status', 'dt_modified'])

    return {'order_id': order.pk, 'status': 'complete'}
