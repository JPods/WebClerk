"""
Inventory Stacks / FIFO-LIFO Service — GAP-04

Each PO receiving creates a cost layer (InventoryLayer).
Invoice shipping consumes from layers in FIFO or LIFO order.
Tracks weighted average cost vs stack values for COGS accuracy.

All functions single-purpose. Called from wcapi/manage.
"""
from __future__ import annotations
from typing import Dict, Optional, Literal
from decimal import Decimal
from django.db import transaction
from apps.products.models.inventory_layer import InventoryLayer, PendingInventoryAdjustment
import time


def _now_ms():
    return int(time.time() * 1000)


def _dec(v) -> Decimal:
    """Safe decimal conversion."""
    if v is None:
        return Decimal('0')
    return Decimal(str(v))


def receive_inventory(
    item_id: int,
    warehouse_id: int,
    qty_received: int,
    unit_cost: Decimal,
    source_type: str = 'purchase',
    source_id: int = None,
    lot: str = '',
    serial_numbers: list = None,
) -> Dict:
    """Create a new inventory layer from a PO receiving.

    Each receiving = one cost layer with qty and cost.

    Returns: {layer_id, qty_received, unit_cost, item_id}
    """
    now = _now_ms()

    layer = InventoryLayer.objects.create(
        item_id=item_id,
        warehouse_id=warehouse_id,
        quantity={
            'received': qty_received,
            'issued': 0,
            'scrapped': 0,
        },
        cost={
            'unit_po': str(unit_cost),
            'landed': str(unit_cost),
            'currency': 'USD',
        },
        source={
            'type': source_type,
            'id': source_id,
        },
        lot=lot or '',
        serial_numbers=serial_numbers or [],
        is_locked=False,
        dt_created=now,
        dt_modified=now,
    )

    return {
        'layer_id': layer.pk,
        'qty_received': qty_received,
        'unit_cost': str(unit_cost),
        'item_id': item_id,
        'warehouse_id': warehouse_id,
    }


def consume_inventory(
    item_id: int,
    qty_to_consume: int,
    method: Literal['fifo', 'lifo'] = 'fifo',
    warehouse_id: int = None,
    source_type: str = 'invoice',
    source_id: int = None,
) -> Dict:
    """Consume inventory from stacks in FIFO or LIFO order.

    Walks through layers oldest-first (FIFO) or newest-first (LIFO),
    consuming from each until qty_to_consume is satisfied.

    Returns: {
        consumed: [{layer_id, qty_consumed, unit_cost}],
        total_consumed, total_cost, weighted_avg_cost,
        qty_short (if insufficient)
    }
    """
    ordering = 'dt_created' if method == 'fifo' else '-dt_created'

    qs = InventoryLayer.objects.filter(
        item_id=item_id,
        is_locked=False,
        is_deleted=False,
    )
    if warehouse_id:
        qs = qs.filter(warehouse_id=warehouse_id)

    layers = qs.order_by(ordering)

    consumed = []
    remaining = qty_to_consume
    total_cost = Decimal('0')

    with transaction.atomic():
        for layer in layers:
            if remaining <= 0:
                break

            qty_data = layer.quantity or {}
            available = (qty_data.get('received', 0) - qty_data.get('issued', 0) - qty_data.get('scrapped', 0))

            if available <= 0:
                continue

            take = min(available, remaining)
            unit_cost = _dec(layer.cost.get('unit_po', 0) if layer.cost else 0)
            line_cost = unit_cost * take

            # Update layer
            qty_data['issued'] = qty_data.get('issued', 0) + take
            layer.quantity = qty_data
            layer.dt_modified = _now_ms()
            layer.save(update_fields=['quantity', 'dt_modified'])

            consumed.append({
                'layer_id': layer.pk,
                'qty_consumed': take,
                'unit_cost': str(unit_cost),
                'line_cost': str(line_cost),
            })

            total_cost += line_cost
            remaining -= take

    total_consumed = qty_to_consume - remaining
    weighted_avg = (total_cost / total_consumed) if total_consumed > 0 else Decimal('0')

    return {
        'consumed': consumed,
        'total_consumed': total_consumed,
        'total_cost': str(total_cost),
        'weighted_avg_cost': str(weighted_avg),
        'qty_short': remaining if remaining > 0 else 0,
        'method': method,
    }


def get_item_inventory_summary(item_id: int, warehouse_id: int = None) -> Dict:
    """Get inventory summary for an item — on hand, available, cost layers.

    Returns: {item_id, on_hand, layers: [{layer_id, qty_available, unit_cost, dt_received}]}
    """
    qs = InventoryLayer.objects.filter(
        item_id=item_id,
        is_deleted=False,
    )
    if warehouse_id:
        qs = qs.filter(warehouse_id=warehouse_id)

    layers = []
    total_on_hand = 0
    total_value = Decimal('0')

    for layer in qs.order_by('dt_created'):
        qty = layer.quantity or {}
        available = qty.get('received', 0) - qty.get('issued', 0) - qty.get('scrapped', 0)
        if available <= 0:
            continue

        unit_cost = _dec(layer.cost.get('unit_po', 0) if layer.cost else 0)
        layers.append({
            'layer_id': layer.pk,
            'qty_available': available,
            'unit_cost': str(unit_cost),
            'layer_value': str(unit_cost * available),
            'dt_received': layer.dt_created,
            'lot': layer.lot or '',
        })
        total_on_hand += available
        total_value += unit_cost * available

    weighted_avg = (total_value / total_on_hand) if total_on_hand > 0 else Decimal('0')

    return {
        'item_id': item_id,
        'on_hand': total_on_hand,
        'total_value': str(total_value),
        'weighted_avg_cost': str(weighted_avg),
        'layer_count': len(layers),
        'layers': layers,
    }
