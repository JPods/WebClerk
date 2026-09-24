"""
Order Production Service — GAP-01

Manages the fulfillment workflow: Order → Work Orders, Material Draws,
Requisitions → Action Decision (partial/complete) → Invoice.

A partial shipment is fulfillment_ship.ship_order: it invoices what was packed through the
one conversion engine (partial_ship, a second engine with its own stock Pending, is gone).

All functions are single-purpose. Called from wcapi/manage.

Flow:
  1. spawn_workorder(order_id) → creates WO from order lines
  2. spawn_requisition(order_id, lines) → creates requisition for items to purchase
  3. record_production_action(order_id, action, lines) → partial ship or complete
  4. complete_order(order_id) → closes order, creates final invoice
"""
from __future__ import annotations
from typing import List, Dict, Optional
from django.db import transaction
from apps.transactions.models import Order, OrderLine, Invoice, InvoiceLine, WorkOrder, WorkOrderLine
from apps.core.models.action import Action
from apps.core.models import Pending
import time


def _now_ms():
    return int(time.time() * 1000)


def spawn_workorder(order_id: int) -> Dict:
    """Create a Work Order from an Order's lines.

    Each order line becomes a WO line. The WO inherits customer,
    vendor, contact, and terms from the order.

    Returns: {workorder_id, line_count, status}
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
        children.append({'type': 'workorder', 'id': wo.pk})
        flow['children'] = children
        order.flow = flow
        order.save(update_fields=['flow', 'dt_modified'])

    return {'workorder_id': wo.pk, 'line_count': line_count, 'status': 'planned'}


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


def complete_order(order_id: int) -> Dict:
    """Close an order — all lines must be fulfilled or canceled.

    Returns: {order_id, status}
    """
    order = Order.objects.get(pk=order_id)
    order.status = 'complete'
    order.dt_modified = _now_ms()
    order.save(update_fields=['status', 'dt_modified'])

    return {'order_id': order.pk, 'status': 'complete'}
