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
from apps.products.models.inventory_layer import InventoryLayer
import time


def _now_ms():
    return int(time.time() * 1000)


def _dec(v) -> Decimal:
    """Safe decimal conversion."""
    if v is None:
        return Decimal('0')
    return Decimal(str(v))


def get_item_inventory_summary(item_id: int, warehouse_id: int = None) -> Dict:
    """Get inventory summary for an item — on hand, available, cost layers.

    Returns: {item_id, on_hand, layers: [{layer_id, qty_available, unit_cost, dt_received}]}
    """
    qs = InventoryLayer.objects.filter(
        item_id=item_id,
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
