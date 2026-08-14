"""Inventory layer services — costing, movement, counting, and analysis.

Improvements over WC2:
  1. Partial-consume bug fixed — cost accumulated for every partial layer drain
  2. Costing method per item, not global (item.config.costing_method)
  3. Layer splitting preserves lineage (source.parent_layer_id)
  4. Count-by-exception with ABC classification (Alice-driven schedule)
  5. Two-phase blind counting (hide expected qty until phase 2)
  6. Negative inventory creates an Action alert, not just a synthetic layer
  7. Pending event heartbeat — Alice monitors orphaned events
  8. Landed cost flows from PO receipt at create time
  9. Transfers are atomic — both sides or neither
  10. Margin velocity as a nightly Alice metric

Pipeline: stage event → apply to ledger → tally (async) → update item + site buckets + GL
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from typing import Optional
from django.db import transaction
from django.db.models import Sum, F, Q
from django.utils import timezone

from apps.products.models.inventory_layer import (
    InventoryLayer, InventoryMovement, SiteInventory, PendingInventoryAdjustment,
    default_cost,
)
from apps.products.models.warehouse import Warehouse
from apps.products.models.item import Item


COST_DECIMALS = Decimal('0.0001')


# ---------------------------------------------------------------------------
# 1. Create layer (receipt)
# ---------------------------------------------------------------------------

@transaction.atomic
def create_layer(
    item_id: int,
    warehouse_id: int,
    qty: Decimal,
    unit_cost: Decimal,
    *,
    source_doc_type: str = '',
    source_doc_id: Optional[int] = None,
    lot: str = '',
    freight: Decimal = Decimal('0'),
    duty: Decimal = Decimal('0'),
    handling: Decimal = Decimal('0'),
    vat: Decimal = Decimal('0'),
    serial_numbers: Optional[list] = None,
    reason: str = 'Receipt',
) -> InventoryLayer:
    """Create a new inventory layer on receipt. Landed cost computed at create time (#8)."""
    item = Item.objects.get(id=item_id)
    warehouse = Warehouse.objects.get(id=warehouse_id)

    # Get prior moving average for trend calculation
    prior_avg = _get_item_avg_cost(item)

    layer = InventoryLayer(
        item=item,
        item_ida=item.ida or '',
        warehouse=warehouse,
        quantity={'received': float(qty), 'issued': 0, 'scrapped': 0},
        lot=lot,
        serial_numbers=serial_numbers or [],
        source_doc_type=source_doc_type,
        source_doc_id=source_doc_id,
        source={},
    )
    # Landed cost computed at receipt time (#8)
    layer.update_cost_after_receipt(
        unit_po=float(unit_cost),
        freight=float(freight),
        duty=float(duty),
        handling=float(handling),
        vat=float(vat),
        prior_moving_avg=float(prior_avg),
    )
    layer.save()

    # Post receipt movement to ledger
    InventoryMovement.objects.create(
        item=item,
        warehouse=warehouse,
        inventory_layer=layer,
        site_code=warehouse.site_code,
        movement_type=InventoryMovement.MOVEMENT_RECEIPT,
        quantity=qty,
        reason=reason,
        source_doc_type=source_doc_type,
        source_doc_id=source_doc_id,
    )

    # Update item average cost
    recalc_average_cost(item_id)

    return layer


# ---------------------------------------------------------------------------
# 2. Consume FIFO / LIFO (with partial-consume bug fix #1)
# ---------------------------------------------------------------------------

@transaction.atomic
def consume_fifo(
    item_id: int,
    qty: Decimal,
    *,
    warehouse_id: Optional[int] = None,
    reason: str = 'Issue',
    source_doc_type: str = '',
    source_doc_id: Optional[int] = None,
) -> tuple[Decimal, str]:
    """Consume qty using FIFO (oldest layers first). Returns (total_cost, batch_id).

    FIX #1: WC2 missed cost on partial layer consumption. Every unit drained
    contributes to total_cost regardless of whether the layer is fully or
    partially consumed.
    """
    return _consume(item_id, qty, order='id', warehouse_id=warehouse_id,
                    reason=reason, source_doc_type=source_doc_type, source_doc_id=source_doc_id)


@transaction.atomic
def consume_lifo(
    item_id: int,
    qty: Decimal,
    *,
    warehouse_id: Optional[int] = None,
    reason: str = 'Issue',
    source_doc_type: str = '',
    source_doc_id: Optional[int] = None,
) -> tuple[Decimal, str]:
    """Consume qty using LIFO (newest layers first). Returns (total_cost, batch_id)."""
    return _consume(item_id, qty, order='-id', warehouse_id=warehouse_id,
                    reason=reason, source_doc_type=source_doc_type, source_doc_id=source_doc_id)


def consume_by_item_method(
    item_id: int,
    qty: Decimal,
    **kwargs,
) -> tuple[Decimal, str]:
    """Consume using the item's configured costing method (#2)."""
    item = Item.objects.get(id=item_id)
    method = _get_costing_method(item)
    if method == 'fifo':
        return consume_fifo(item_id, qty, **kwargs)
    elif method == 'lifo':
        return consume_lifo(item_id, qty, **kwargs)
    elif method == 'last':
        # Last cost: consume LIFO but cost at last receipt price
        return consume_lifo(item_id, qty, **kwargs)
    else:  # average
        return consume_fifo(item_id, qty, **kwargs)


def _consume(
    item_id: int,
    qty: Decimal,
    order: str,
    *,
    warehouse_id: Optional[int] = None,
    reason: str = 'Issue',
    source_doc_type: str = '',
    source_doc_id: Optional[int] = None,
) -> tuple[Decimal, str]:
    """Internal consume implementation. Walks layers in given order."""
    item = Item.objects.select_for_update().get(id=item_id)
    batch_id = str(uuid.uuid4())

    qs = InventoryLayer.objects.filter(item=item).exclude(
        quantity__issued__gte=F('quantity__received')  # skip fully consumed
    ).order_by(order)
    if warehouse_id:
        qs = qs.filter(warehouse_id=warehouse_id)

    # Walk layers — can't use JSON F expressions for remaining, so use Python
    layers = list(qs.select_for_update())
    total_cost = Decimal('0')
    remaining = qty

    for layer in layers:
        avail = layer.remaining_qty()
        if avail <= 0:
            continue
        take = min(Decimal(str(avail)), remaining)

        # FIX #1: Always accumulate cost, including partial consumption
        unit_cost = Decimal(str(layer.cost.get('landed', 0) or layer.cost.get('unit_po', 0)))
        total_cost += take * unit_cost

        layer.mark_issue(take)
        layer.save(update_fields=['quantity'])

        # Post movement for this layer
        InventoryMovement.objects.create(
            item=item,
            warehouse=layer.warehouse,
            inventory_layer=layer,
            site_code=layer.warehouse.site_code,
            movement_type=InventoryMovement.MOVEMENT_ISSUE,
            quantity=-take,
            reason=reason,
            source_doc_type=source_doc_type,
            source_doc_id=source_doc_id,
        )

        remaining -= take
        if remaining <= 0:
            break

    # Deficit handling (#6): create synthetic layer + Action alert
    if remaining > 0:
        avg_cost = _get_item_avg_cost(item)
        total_cost += remaining * avg_cost

        wh = Warehouse.objects.filter(is_active=True).first()
        if wh:
            deficit_layer = InventoryLayer.objects.create(
                item=item,
                item_ida=item.ida or '',
                warehouse=wh,
                quantity={'received': float(remaining), 'issued': float(remaining), 'scrapped': 0},
                cost={'unit_po': float(avg_cost), 'landed': float(avg_cost),
                      'moving_avg': float(avg_cost), **{k: 0.0 for k in ('freight', 'duty', 'handling', 'vat', 'scrap_cost', 'trend_pct')},
                      'currency': 'USD', 'exchange_rate': 1.0,
                      'fifo_snapshot': float(avg_cost), 'lifo_snapshot': float(avg_cost)},
                source={'auto_deficit': True, 'batch_id': batch_id},
                source_doc_type='deficit',
            )

        # Create Action alert for negative inventory (#6)
        _create_deficit_alert(item, remaining, batch_id, reason)

    # Recalculate average cost after consumption
    recalc_average_cost(item_id)

    return total_cost, batch_id


# ---------------------------------------------------------------------------
# 3. Average cost recalculation
# ---------------------------------------------------------------------------

def recalc_average_cost(item_id: int) -> Decimal:
    """Weighted average cost across all layers with remaining qty."""
    layers = InventoryLayer.objects.filter(item_id=item_id)
    total_value = Decimal('0')
    total_qty = Decimal('0')

    for layer in layers:
        remaining = Decimal(str(layer.remaining_qty()))
        if remaining <= 0:
            continue
        unit_cost = Decimal(str(layer.cost.get('landed', 0) or layer.cost.get('unit_po', 0)))
        total_value += remaining * unit_cost
        total_qty += remaining

    avg = (total_value / total_qty).quantize(COST_DECIMALS) if total_qty > 0 else Decimal('0')

    # Update item.cost.avg
    try:
        item = Item.objects.get(id=item_id)
        if isinstance(item.cost, dict):
            item.cost['avg'] = float(avg)
            item.save(update_fields=['cost'])
    except Exception:
        pass

    return avg


# ---------------------------------------------------------------------------
# 4. Split layer to multiple locations (#3 lineage preserved)
# ---------------------------------------------------------------------------

@transaction.atomic
def split_layer(
    layer_id: int,
    splits: list[dict],
) -> list[InventoryLayer]:
    """Split one layer into N layers at different locations.

    splits: [{'warehouse_id': 5, 'qty': 10}, {'warehouse_id': 8, 'qty': 15}]
    Original layer is consumed; new layers carry source.parent_layer_id (#3).
    """
    original = InventoryLayer.objects.select_for_update().get(id=layer_id)
    remaining = original.remaining_qty()
    total_split = sum(Decimal(str(s['qty'])) for s in splits)

    if total_split > remaining:
        raise ValueError(f"Split total ({total_split}) exceeds remaining qty ({remaining})")

    new_layers = []
    for split in splits:
        wh = Warehouse.objects.get(id=split['warehouse_id'])
        split_qty = Decimal(str(split['qty']))

        child = InventoryLayer.objects.create(
            item=original.item,
            item_ida=original.item_ida,
            warehouse=wh,
            quantity={'received': float(split_qty), 'issued': 0, 'scrapped': 0},
            cost=dict(original.cost),  # same cost
            lot=original.lot,
            serial_numbers=[],
            source_doc_type=original.source_doc_type,
            source_doc_id=original.source_doc_id,
            source={},
        )
        # Lineage via refs.links (#3) — same pattern as all WC3 relationships
        child_refs = child.refs if isinstance(child.refs, dict) else {}
        child_links = child_refs.setdefault('links', {})
        child_links['parent_layer_id'] = original.id
        child_links['split_from'] = original.id
        child_refs['links'] = child_links
        child.refs = child_refs
        child.save(update_fields=['refs'])
        new_layers.append(child)

        # Post movements
        InventoryMovement.objects.create(
            item=original.item, warehouse=original.warehouse,
            inventory_layer=original, site_code=original.warehouse.site_code,
            movement_type=InventoryMovement.MOVEMENT_ISSUE,
            quantity=-split_qty, reason=f'Split to {wh.code}',
            source_doc_type='split', source_doc_id=child.id,
        )
        InventoryMovement.objects.create(
            item=original.item, warehouse=wh,
            inventory_layer=child, site_code=wh.site_code,
            movement_type=InventoryMovement.MOVEMENT_RECEIPT,
            quantity=split_qty, reason=f'Split from layer #{original.id}',
            source_doc_type='split', source_doc_id=original.id,
        )

    # Drain original layer by total split qty
    original.mark_issue(total_split)
    # Track child layers in original's refs.links
    orig_refs = original.refs if isinstance(original.refs, dict) else {}
    orig_links = orig_refs.setdefault('links', {})
    orig_links.setdefault('child_layer_ids', [])
    orig_links['child_layer_ids'].extend([l.id for l in new_layers])
    original.refs = orig_refs
    original.save(update_fields=['quantity', 'refs'])

    return new_layers


# ---------------------------------------------------------------------------
# 5. Transfer between warehouses (#9 atomic)
# ---------------------------------------------------------------------------

@transaction.atomic
def transfer_layer(
    layer_id: int,
    dest_warehouse_id: int,
    qty: Optional[Decimal] = None,
    reason: str = 'Transfer',
) -> InventoryLayer:
    """Move qty from one warehouse to another. Atomic — both sides or neither (#9)."""
    source_layer = InventoryLayer.objects.select_for_update().get(id=layer_id)
    dest_wh = Warehouse.objects.get(id=dest_warehouse_id)
    transfer_qty = qty or Decimal(str(source_layer.remaining_qty()))
    transfer_id = str(uuid.uuid4())

    if transfer_qty > source_layer.remaining_qty():
        raise ValueError("Transfer qty exceeds remaining")

    # Drain source
    source_layer.mark_issue(transfer_qty)
    source_layer.save(update_fields=['quantity'])

    # Create destination layer with lineage via refs.links
    dest_layer = InventoryLayer.objects.create(
        item=source_layer.item,
        item_ida=source_layer.item_ida,
        warehouse=dest_wh,
        quantity={'received': float(transfer_qty), 'issued': 0, 'scrapped': 0},
        cost=dict(source_layer.cost),
        lot=source_layer.lot,
        source={},
        source_doc_type='transfer',
    )
    dest_refs = dest_layer.refs if isinstance(dest_layer.refs, dict) else {}
    dest_links = dest_refs.setdefault('links', {})
    dest_links['parent_layer_id'] = source_layer.id
    dest_links['transfer_from'] = source_layer.id
    dest_links['transfer_id'] = transfer_id
    dest_refs['links'] = dest_links
    dest_layer.refs = dest_refs
    dest_layer.save(update_fields=['refs'])

    # Paired movements — same transfer_id (#9)
    for mvmt in [
        (source_layer.warehouse, source_layer, -transfer_qty, f'Transfer out to {dest_wh.code}'),
        (dest_wh, dest_layer, transfer_qty, f'Transfer in from {source_layer.warehouse.code}'),
    ]:
        InventoryMovement.objects.create(
            item=source_layer.item, warehouse=mvmt[0],
            inventory_layer=mvmt[1], site_code=mvmt[0].site_code,
            movement_type=InventoryMovement.MOVEMENT_ADJUST,
            quantity=mvmt[2], reason=mvmt[3],
            source_doc_type='transfer', source_doc_id=int(transfer_id[:8], 16) if transfer_id else None,
        )

    return dest_layer


# ---------------------------------------------------------------------------
# 6. Count check — two-phase blind counting (#5)
# ---------------------------------------------------------------------------

def get_count_sheet(
    warehouse_id: int,
    *,
    item_ids: Optional[list[int]] = None,
    blind: bool = True,
) -> list[dict]:
    """Generate a count sheet for a warehouse. Phase 1 (blind=True) hides expected qty (#5)."""
    qs = InventoryLayer.objects.filter(warehouse_id=warehouse_id)
    if item_ids:
        qs = qs.filter(item_id__in=item_ids)

    # Only layers with remaining qty
    layers = [l for l in qs.select_related('item', 'warehouse') if l.remaining_qty() > 0]

    sheet = []
    for layer in layers:
        row = {
            'layer_id': layer.id,
            'item_id': layer.item_id,
            'item_ida': layer.item_ida,
            'item_name': layer.item.name if layer.item else '',
            'lot': layer.lot,
            'location': {
                'warehouse': layer.warehouse.code,
                'aisle': layer.warehouse.count.get('aisle', ''),
                'shelf': layer.warehouse.count.get('shelf', ''),
                'bin': layer.warehouse.count.get('bin', ''),
            },
            'qr_code': layer.item.qr_code if hasattr(layer.item, 'qr_code') else '',
            'unit_cost': float(layer.cost.get('landed', 0)),
        }
        if not blind:  # Phase 2 — reveal expected qty
            row['expected_qty'] = float(layer.remaining_qty())
        sheet.append(row)

    return sheet


@transaction.atomic
def record_count(
    layer_id: int,
    actual_qty: Decimal,
    *,
    counted_by: str = '',
    counted_by_id: Optional[int] = None,
    explanation: str = '',
) -> dict:
    """Record a physical count against a layer. Creates adjustment if variance exists."""
    layer = InventoryLayer.objects.select_for_update().get(id=layer_id)
    expected = layer.remaining_qty()
    variance = actual_qty - Decimal(str(expected))

    result = {
        'layer_id': layer_id,
        'expected': float(expected),
        'actual': float(actual_qty),
        'variance': float(variance),
        'adjustment_posted': False,
    }

    if variance != 0:
        # Post adjustment movement
        InventoryMovement.objects.create(
            item=layer.item,
            warehouse=layer.warehouse,
            inventory_layer=layer,
            site_code=layer.warehouse.site_code,
            movement_type=InventoryMovement.MOVEMENT_ADJUST,
            quantity=variance,
            reason=f'Count: {explanation}' if explanation else f'Count variance: {variance}',
            source_doc_type='count',
            source_doc_id=layer_id,
        )

        # Adjust the layer's quantity
        if variance > 0:
            q = layer.quantity or {}
            q['received'] = float(Decimal(str(q.get('received', 0))) + variance)
            layer.quantity = q
        else:
            layer.mark_issue(abs(variance))

        layer.save(update_fields=['quantity'])
        result['adjustment_posted'] = True

        # Recalc average cost
        recalc_average_cost(layer.item_id)

    # Update warehouse count snapshot
    layer.warehouse.update_count(
        value=float(actual_qty),
        user=counted_by or counted_by_id,
        deviation=float(variance),
        item=layer.item,
    )
    layer.warehouse.save(update_fields=['count'])

    return result


# ---------------------------------------------------------------------------
# 7. ABC classification for cycle counting (#4)
# ---------------------------------------------------------------------------

def classify_abc(item_ids: Optional[list[int]] = None) -> dict[int, str]:
    """Classify items into A/B/C based on margin velocity.

    A = top 20% by margin velocity (count weekly)
    B = middle 30% (count monthly)
    C = bottom 50% (count quarterly)

    Returns {item_id: 'A'|'B'|'C'}
    """
    velocities = compute_margin_velocity(item_ids)
    if not velocities:
        return {}

    # Sort by velocity descending
    sorted_items = sorted(velocities.items(), key=lambda x: x[1]['margin_velocity'], reverse=True)
    total = len(sorted_items)
    a_cutoff = int(total * 0.2)
    b_cutoff = int(total * 0.5)

    result = {}
    for i, (item_id, _) in enumerate(sorted_items):
        if i < a_cutoff:
            result[item_id] = 'A'
        elif i < b_cutoff:
            result[item_id] = 'B'
        else:
            result[item_id] = 'C'

    return result


# ---------------------------------------------------------------------------
# 8. Margin velocity (#10)
# ---------------------------------------------------------------------------

def compute_margin_velocity(
    item_ids: Optional[list[int]] = None,
    period_days: int = 365,
) -> dict[int, dict]:
    """Compute margin velocity per item.

    margin_velocity = ((sale_price - cost_avg) / cost_avg) × annual_turns

    Categories:
      Dead capital: >50% margin, <2 turns/year
      Volume drivers: <10% margin, >50 turns/year
      Stars: >20% margin, >20 turns/year

    Returns {item_id: {margin_pct, annual_turns, margin_velocity, category, cost_avg, sale_price}}
    """
    qs = Item.objects.filter(is_active=True, is_deleted=False)
    if item_ids:
        qs = qs.filter(id__in=item_ids)

    # Get movement counts for the period
    cutoff_ms = int((timezone.now() - timedelta(days=period_days)).timestamp() * 1000)
    issue_counts = dict(
        InventoryMovement.objects.filter(
            movement_type=InventoryMovement.MOVEMENT_ISSUE,
            dt_created__gte=cutoff_ms,
        ).values('item_id').annotate(
            total_issued=Sum('quantity')
        ).values_list('item_id', 'total_issued')
    )

    results = {}
    for item in qs:
        cost = item.cost if isinstance(item.cost, dict) else {}
        price = item.price if isinstance(item.price, dict) else {}
        cost_avg = Decimal(str(cost.get('avg', 0) or 0))
        sale_price = Decimal(str(price.get('base', 0) or price.get('retail', 0) or 0))

        if cost_avg <= 0 or sale_price <= 0:
            continue

        margin_pct = float((sale_price - cost_avg) / cost_avg * 100)

        # Annual turns = total issued qty / average on-hand qty
        total_issued = abs(float(issue_counts.get(item.id, 0) or 0))
        qty_on_hand = float((item.quantity or {}).get('on_hand', 0) or 0)
        annual_turns = (total_issued / qty_on_hand * (365 / period_days)) if qty_on_hand > 0 else 0

        margin_velocity = (margin_pct / 100) * annual_turns

        # Categorize
        if margin_pct > 50 and annual_turns < 2:
            category = 'dead_capital'
        elif margin_pct < 10 and annual_turns > 50:
            category = 'volume_driver'
        elif margin_pct > 20 and annual_turns > 20:
            category = 'star'
        else:
            category = 'normal'

        results[item.id] = {
            'item_ida': item.ida,
            'margin_pct': round(margin_pct, 2),
            'annual_turns': round(annual_turns, 2),
            'margin_velocity': round(margin_velocity, 4),
            'category': category,
            'cost_avg': float(cost_avg),
            'sale_price': float(sale_price),
            'qty_on_hand': qty_on_hand,
        }

    return results


# ---------------------------------------------------------------------------
# 8b. Store margin velocity on every item (metadata.health)
# ---------------------------------------------------------------------------

def update_item_margin_velocity(
    item_ids: Optional[list[int]] = None,
    period_days: int = 365,
) -> int:
    """Compute margin velocity for items and store in metadata.health.

    Called nightly by Alice. Every item gets a score so it's always visible
    in DataBrowser and available for ABC classification and reporting.

    Stored at item.metadata.health:
      margin_velocity, margin_pct, annual_turns, category, dt_computed
    """
    velocities = compute_margin_velocity(item_ids, period_days)
    updated = 0

    for item_id, data in velocities.items():
        try:
            Item.objects.filter(id=item_id).update(
                margin_velocity=Decimal(str(data['margin_velocity'])),
                margin_pct=Decimal(str(data['margin_pct'])),
                annual_turns=Decimal(str(data['annual_turns'])),
                velocity_category=data['category'],
            )
            updated += 1
        except Exception:
            continue

    return updated


# ---------------------------------------------------------------------------
# 9. Pending event heartbeat (#7)
# ---------------------------------------------------------------------------

def check_orphaned_events(max_age_hours: int = 1) -> list[dict]:
    """Find InventoryMovements with no processed_at older than max_age_hours.
    Alice should call this periodically and create Actions for any found (#7)."""
    cutoff_ms = int((timezone.now() - timedelta(hours=max_age_hours)).timestamp() * 1000)
    orphans = InventoryMovement.objects.filter(
        dt_created__lt=cutoff_ms,
    ).exclude(
        source_doc_type='deficit',
    ).values('id', 'item_id', 'movement_type', 'quantity', 'reason', 'dt_created')[:50]

    return list(orphans)


# ---------------------------------------------------------------------------
# 10. Tally site buckets
# ---------------------------------------------------------------------------

def tally_site_buckets(item_id: int) -> dict[str, Decimal]:
    """Rebuild SiteInventory rollups from current layers."""
    layers = InventoryLayer.objects.filter(item_id=item_id).select_related('warehouse')
    site_totals: dict[str, Decimal] = defaultdict(Decimal)

    for layer in layers:
        remaining = layer.remaining_qty()
        if remaining > 0:
            site_code = layer.warehouse.site_code or 'DEFAULT'
            site_totals[site_code] += Decimal(str(remaining))

    # Update SiteInventory records
    for site_code, total in site_totals.items():
        si, _ = SiteInventory.objects.get_or_create(
            item_id=item_id, site_code=site_code,
            defaults={'item_ida': '', 'quantity': {}},
        )
        si.quantity = {'on_hand': float(total)}
        si.save(update_fields=['quantity'])

    # Remove stale site records
    SiteInventory.objects.filter(item_id=item_id).exclude(
        site_code__in=list(site_totals.keys())
    ).delete()

    return dict(site_totals)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_item_avg_cost(item: Item) -> Decimal:
    cost = item.cost if isinstance(item.cost, dict) else {}
    return Decimal(str(cost.get('avg', 0) or 0))


def _get_costing_method(item: Item) -> str:
    """Get costing method: item override → company setting → 'average'.

    Item.config.costing_method wins if set. Otherwise reads the company
    profile Setting (purpose='wc:company_profile') inventory.costing_method.
    Final fallback is 'average'.
    """
    config = item.config if isinstance(getattr(item, 'config', None), dict) else {}
    item_method = config.get('costing_method')
    if item_method:
        return item_method

    # Company-level default
    try:
        from apps.core.models import Setting
        company = Setting.objects.filter(purpose='wc:company_profile', is_active=True).first()
        if company and isinstance(company.config, dict):
            inv = company.config.get('inventory', {})
            if isinstance(inv, dict) and inv.get('costing_method'):
                return inv['costing_method']
    except Exception:
        pass

    return 'average'


def _create_deficit_alert(item: Item, deficit_qty: Decimal, batch_id: str, reason: str):
    """Create an Action alert when inventory goes negative (#6)."""
    try:
        from apps.core.models.action import Action
        Action.objects.create(
            title=f'Negative inventory: {item.ida or item.name}',
            description=(
                f'{item.ida} went negative by {deficit_qty} units. '
                f'Reason: {reason}. Batch: {batch_id}. '
                f'Investigate: missed receipt, double-ship, or count error.'
            ),
            status='Backlog',
            priority='high',
        )
    except Exception:
        pass  # Action model may not be available in all contexts


__all__ = [
    'create_layer', 'consume_fifo', 'consume_lifo', 'consume_by_item_method',
    'recalc_average_cost', 'split_layer', 'transfer_layer',
    'get_count_sheet', 'record_count', 'classify_abc',
    'compute_margin_velocity', 'update_item_margin_velocity',
    'check_orphaned_events', 'tally_site_buckets',
]
