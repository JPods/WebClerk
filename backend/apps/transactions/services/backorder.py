"""
Backorder Management Service — GAP-04

Tracks unfulfilled order line quantities. Backorder entries feed forecasting
and PO generation. Fulfillment clears backorder entries.

All functions single-purpose. Called from order_production.py and wcapi/manage.
"""
from __future__ import annotations
from typing import List, Dict
from django.db import transaction
from apps.core.models.action import Action
import time


def _now_ms():
    return int(time.time() * 1000)


def create_backorder_entries(lines: List[Dict]) -> List[int]:
    """Create Action records tracking backordered quantities.

    lines: [{'order_id', 'order_line_id', 'item_fk_id', 'qty_backordered'}, ...]

    Each backorder is an Action with kanban_column='backorder' and metadata
    tracking the source order, line, item, and quantity.

    Returns: list of Action IDs created.
    """
    now = _now_ms()
    action_ids = []

    for line in lines:
        action = Action.objects.create(
            action={'en': f"Backorder: {line['qty_backordered']} units"},
            description={'en': f"Order #{line['order_id']} line #{line['order_line_id']}"},
            status='open',
            kanban_column='backorder',
            priority=2,
            project_name='Backorders',
            project_ida='backorders',
            dt_created=now,
            dt_modified=now,
            metadata={
                'health': 'backorder',
                'order_id': line['order_id'],
                'order_line_id': line['order_line_id'],
                'item_fk_id': line['item_fk_id'],
                'qty_backordered': line['qty_backordered'],
                'qty_fulfilled': 0,
            },
        )
        action_ids.append(action.pk)

    return action_ids


def get_open_backorders(item_id: int = None) -> List[Dict]:
    """Get all open backorder entries, optionally filtered by item.

    Returns: list of {action_id, order_id, order_line_id, item_fk_id, qty_backordered, qty_fulfilled}
    """
    qs = Action.objects.filter(
        kanban_column='backorder',
        status='open',
    )
    if item_id:
        qs = qs.filter(metadata__item_fk_id=item_id)

    results = []
    for a in qs:
        meta = a.metadata or {}
        results.append({
            'action_id': a.pk,
            'order_id': meta.get('order_id'),
            'order_line_id': meta.get('order_line_id'),
            'item_fk_id': meta.get('item_fk_id'),
            'qty_backordered': meta.get('qty_backordered', 0),
            'qty_fulfilled': meta.get('qty_fulfilled', 0),
            'qty_remaining': meta.get('qty_backordered', 0) - meta.get('qty_fulfilled', 0),
        })

    return results


def fulfill_backorder(action_id: int, qty_fulfilled: int) -> Dict:
    """Record fulfillment against a backorder entry.

    If fully fulfilled, closes the action.

    Returns: {action_id, qty_remaining, status}
    """
    action = Action.objects.get(pk=action_id)
    meta = action.metadata or {}

    prev_fulfilled = meta.get('qty_fulfilled', 0)
    total_fulfilled = prev_fulfilled + qty_fulfilled
    qty_backordered = meta.get('qty_backordered', 0)
    qty_remaining = max(0, qty_backordered - total_fulfilled)

    meta['qty_fulfilled'] = total_fulfilled
    action.metadata = meta
    action.dt_modified = _now_ms()

    if qty_remaining <= 0:
        action.status = 'complete'
        action.kanban_column = 'done'

    action.save(update_fields=['metadata', 'status', 'kanban_column', 'dt_modified'])

    return {
        'action_id': action.pk,
        'qty_remaining': qty_remaining,
        'status': action.status,
    }


def get_backorder_summary_by_item() -> List[Dict]:
    """Aggregate open backorders by item for forecast/purchasing.

    Returns: [{item_fk_id, total_backordered, total_fulfilled, total_remaining}]
    """
    backorders = get_open_backorders()
    by_item: Dict[int, Dict] = {}

    for bo in backorders:
        item_id = bo['item_fk_id']
        if item_id not in by_item:
            by_item[item_id] = {'item_fk_id': item_id, 'total_backordered': 0, 'total_fulfilled': 0, 'total_remaining': 0}
        by_item[item_id]['total_backordered'] += bo['qty_backordered']
        by_item[item_id]['total_fulfilled'] += bo['qty_fulfilled']
        by_item[item_id]['total_remaining'] += bo['qty_remaining']

    return list(by_item.values())
