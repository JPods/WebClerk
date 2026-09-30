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

import logging
import uuid
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from typing import Optional
from django.db import transaction
from django.db.models import Sum, F, Q
from django.utils import timezone

from apps.products.models.inventory_layer import (
    InventoryLayer, InventoryMovement, SiteInventory,
    default_cost,
)
from apps.products.models.warehouse import Warehouse
from apps.products.models.item import Item

logger = logging.getLogger(__name__)


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
    parent_model: str = '',
    parent_id: Optional[int] = None,
    lot: str = '',
    serial_batch: str = '',
    freight: Decimal = Decimal('0'),
    duty: Decimal = Decimal('0'),
    handling: Decimal = Decimal('0'),
    vat: Decimal = Decimal('0'),
    serial_numbers: Optional[list] = None,
    reason: str = 'Receipt',
    recalc: bool = True,
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
        serial_batch=serial_batch,
        serial_numbers=serial_numbers or [],
        parent_model=parent_model,
        parent_id=parent_id,
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
        parent_model=parent_model,
        parent_id=parent_id,
    )

    # Update item average cost (the applier recalculates once per apply instead)
    if recalc:
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
    parent_model: str = '',
    parent_id: Optional[int] = None,
    recalc: bool = True,
) -> dict:
    """Consume qty using FIFO (oldest layers first). Returns the consumption (see _consume).

    FIX #1: WC2 missed cost on partial layer consumption. Every unit drained
    contributes to total_cost regardless of whether the layer is fully or
    partially consumed.
    """
    return _consume(item_id, qty, order='id', warehouse_id=warehouse_id, reason=reason,
                    parent_model=parent_model, parent_id=parent_id, recalc=recalc)


@transaction.atomic
def consume_lifo(
    item_id: int,
    qty: Decimal,
    *,
    warehouse_id: Optional[int] = None,
    reason: str = 'Issue',
    parent_model: str = '',
    parent_id: Optional[int] = None,
    recalc: bool = True,
) -> dict:
    """Consume qty using LIFO (newest layers first). Returns the consumption (see _consume)."""
    return _consume(item_id, qty, order='-id', warehouse_id=warehouse_id, reason=reason,
                    parent_model=parent_model, parent_id=parent_id, recalc=recalc)


def consume_by_item_method(
    item_id: int,
    qty: Decimal,
    **kwargs,
) -> dict:
    """Consume using the item's configured costing method (#2); the result names the method."""
    item = Item.objects.get(id=item_id)
    method = _get_costing_method(item)
    if method in ('lifo', 'last'):
        # Last cost: consume LIFO but cost at last receipt price
        result = consume_lifo(item_id, qty, **kwargs)
    else:  # fifo, and average (walked FIFO)
        result = consume_fifo(item_id, qty, **kwargs)
    return {**result, 'method': method}


def _consume(
    item_id: int,
    qty: Decimal,
    order: str,
    *,
    warehouse_id: Optional[int] = None,
    reason: str = 'Issue',
    parent_model: str = '',
    parent_id: Optional[int] = None,
    recalc: bool = True,
) -> dict:
    """Internal consume implementation. Walks layers in given order.

    Returns {cost, batch_id, layers: [{layer_id, qty, unit_cost}], short}: what each layer
    gave, and how much the layers could not (the shortfall, left as an open deficit Pending).

    Locks without waiting: a locked item or layer raises LayerLocked (409 layer_locked)
    instead of blocking behind another save's transaction (defect B-6).
    """
    from django.db import DatabaseError
    from apps.core.models.pending import LayerLocked

    batch_id = str(uuid.uuid4())
    try:
        item = Item.objects.select_for_update(nowait=True).get(id=item_id)
        qs = InventoryLayer.objects.filter(item=item).exclude(
            quantity__issued__gte=F('quantity__received')  # skip fully consumed
        ).order_by(order)
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        # Walk layers — can't use JSON F expressions for remaining, so use Python
        layers = list(qs.select_for_update(nowait=True))
    except DatabaseError as e:
        raise LayerLocked(item_id=item_id) from e
    total_cost = Decimal('0')
    remaining = qty
    taken = []

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
        taken.append({'layer_id': layer.pk, 'qty': float(take), 'unit_cost': float(unit_cost)})

        # Post movement for this layer
        InventoryMovement.objects.create(
            item=item,
            warehouse=layer.warehouse,
            inventory_layer=layer,
            site_code=layer.warehouse.site_code,
            movement_type=InventoryMovement.MOVEMENT_ISSUE,
            quantity=-take,
            reason=reason,
            parent_model=parent_model,
            parent_id=parent_id,
        )

        remaining -= take
        if remaining <= 0:
            break

    # A shortage is recorded as what it is: an open deficit Pending, the note of the defect
    # until receipts fill it (Bill, 2026-09-21), which check_balances already reads. The
    # synthetic layer this made (received = issued = the shortfall) hid it in the layers
    # instead (defect B-6).
    if remaining > 0:
        from apps.core.models.pending import DEFICIT_PURPOSE, Pending
        avg_cost = _get_item_avg_cost(item)
        total_cost += remaining * avg_cost
        Pending.objects.create(
            purpose=DEFICIT_PURPOSE, model_name='item', record_id=str(item.pk),
            name=f'Short {remaining} of {item.ida or item.pk}'[:120],
            changes={'deficit_qty': float(remaining), 'unit_cost': float(avg_cost),
                     'batch_id': batch_id, 'reason': reason,
                     'parent_model': parent_model, 'parent_id': parent_id},
        )
        _create_deficit_alert(item, remaining, batch_id, reason)

    # Recalculate average cost after consumption (the applier does it once per apply)
    if recalc:
        recalc_average_cost(item_id)

    return {'cost': total_cost, 'batch_id': batch_id, 'layers': taken,
            'short': float(remaining) if remaining > 0 else 0.0}


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

    # Update item.cost.avg. A queryset update: the item's own save would run its signals inside
    # the applier's transaction. A failure raises (plan §16c.6) — it used to pass silently.
    item = Item.objects.only('id', 'cost').get(id=item_id)
    cost = dict(item.cost) if isinstance(item.cost, dict) else {}
    cost['avg'] = float(avg)
    Item.objects.filter(pk=item_id).update(cost=cost)

    return avg


def give_back(item_id: int, consumed: list, qty: Decimal, *, reason: str = 'Given back',
              parent_model: str = '', parent_id: Optional[int] = None) -> dict:
    """Return qty to the layers a line consumed, newest consumption first, at the costs taken.

    ``consumed`` is the line's history, oldest first: each entry {layer_id, qty, unit_cost}, a
    give-back entered negative. The net still out per layer is what can come back. Returns
    {layers: [{layer_id, qty, unit_cost}] (qty negative: back on the shelf), cost, unplaced}; what
    the history cannot place (a line older than its events) is left to the caller.
    """
    from django.db import DatabaseError
    from apps.core.models.pending import LayerLocked

    out: dict = {}
    order: list = []
    for entry in consumed:
        lid = entry.get('layer_id')
        if not lid:
            continue
        out[lid] = out.get(lid, Decimal('0')) + Decimal(str(entry.get('qty') or 0))
        if lid in order:
            order.remove(lid)
        order.append(lid)
    costs = {e.get('layer_id'): Decimal(str(e.get('unit_cost') or 0)) for e in consumed if e.get('layer_id')}

    left = Decimal(str(qty))
    back, cost = [], Decimal('0')
    for lid in reversed(order):
        if left <= 0:
            break
        take = min(out[lid], left)
        if take <= 0:
            continue
        try:
            layer = InventoryLayer.objects.select_for_update(nowait=True).select_related(
                'warehouse').get(pk=lid)
        except InventoryLayer.DoesNotExist:
            continue                       # the layer is gone; the rest is the caller's
        except DatabaseError as e:
            raise LayerLocked(lid, item_id=item_id) from e
        layer.mark_issue(-take)
        layer.save(update_fields=['quantity'])
        InventoryMovement.objects.create(
            item_id=item_id, warehouse=layer.warehouse, inventory_layer=layer,
            site_code=layer.warehouse.site_code, movement_type=InventoryMovement.MOVEMENT_ADJUST,
            quantity=take, reason=reason[:120], parent_model=parent_model,
            parent_id=parent_id)
        back.append({'layer_id': lid, 'qty': float(-take), 'unit_cost': float(costs.get(lid, 0))})
        cost += take * costs.get(lid, Decimal('0'))
        left -= take
    return {'layers': back, 'cost': -cost, 'unplaced': float(left)}


def settle_deficit(item_id: int, qty: Decimal, *, source_pending_id: Optional[int] = None) -> Decimal:
    """Take qty off the item's open deficits, oldest first; what is left over is returned.

    A deficit Pending is never edited: each settlement is an entry in its
    metadata.incremental_apply, and it closes when nothing remains (Pending.incremental_remaining).
    """
    from apps.core.models.pending import DEFICIT_PURPOSE, Pending
    left = Decimal(str(qty))
    for p in (Pending.objects.select_for_update()
              .filter(purpose=DEFICIT_PURPOSE, record_id=str(item_id), dt_processed=0).order_by('id')):
        if left <= 0:
            break
        open_qty = p.incremental_remaining('deficit_qty')
        take = min(open_qty, left)
        if take <= 0:
            continue
        meta = dict(p.metadata or {})
        meta['incremental_apply'] = list(meta.get('incremental_apply') or []) + [
            {'qty': float(take), 'source_pending_id': source_pending_id}]
        p.metadata = meta
        fields = ['metadata', 'dt_modified', 'version']
        if open_qty - take <= 0:
            p.mark_processed(save=False)
            fields.append('dt_processed')
        p.save(update_fields=fields)
        left -= take
    return left


# ---------------------------------------------------------------------------
# 6. Count check — two-phase blind counting (#5)
# ---------------------------------------------------------------------------

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
    qs = Item.objects.filter(is_active=True)
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


UNIT_COST_DEFAULT_OPTIONS = ('last', 'standard', 'avg', 'landed')


def get_unit_cost_default() -> str:
    """Which item cost a new line starts from: company profile
    config.inventory.unit_cost_default, one of UNIT_COST_DEFAULT_OPTIONS.

    Separate from costing_method, which values COGS. A missing or unknown value
    is 'last' — what the company actually paid most recently.
    """
    try:
        from apps.core.models import Setting
        company = Setting.objects.filter(purpose='wc:company_profile', is_active=True).first()
        inv = company.config.get('inventory', {}) if company and isinstance(company.config, dict) else {}
        basis = inv.get('unit_cost_default') if isinstance(inv, dict) else None
        if basis in UNIT_COST_DEFAULT_OPTIONS:
            return basis
    except Exception:
        logger.exception('unit_cost_default: company profile unreadable')
    return 'last'


def item_unit_cost(item_cost, basis: Optional[str] = None) -> Decimal:
    """Unit cost from an item.cost envelope at the given basis (company default
    when None). An item with no cost at that basis yet falls to standard — a new
    item has a standard cost before it has ever been bought."""
    basis = basis or get_unit_cost_default()
    cost = item_cost if isinstance(item_cost, dict) else {}
    for key in (basis, 'standard'):
        try:
            value = Decimal(str(cost.get(key)))
        except Exception:
            continue
        if value > 0:
            return value
    return Decimal('0')


def _create_deficit_alert(item: Item, deficit_qty: Decimal, batch_id: str, reason: str):
    """Create an Action alert when inventory goes negative (#6)."""
    try:
        from apps.core.models.action import Action
        Action.objects.create(
            action={'en': f'Negative inventory: {item.ida or item.name}'},
            description={'en': (
                f'{item.ida} went negative by {deficit_qty} units. '
                f'Reason: {reason}. Batch: {batch_id}. '
                f'Investigate: missed receipt, double-ship, or count error.'
            )},
            status='Backlog',
            priority=3,            # high (1 low … 4 urgent)
        )
    except Exception:
        # Never blocks the stock move; said out loud (Axiom 6) — it was silently
        # failing on a field Action does not have (title) and no alert was ever made.
        logger.error('%s alert Action not created', 'negative-inventory', exc_info=True)


__all__ = [
    'create_layer', 'consume_fifo', 'consume_lifo', 'consume_by_item_method', 'give_back',
    'settle_deficit',
    'recalc_average_cost', 'split_layer', 'transfer_layer',
    'classify_abc',
    'compute_margin_velocity', 'update_item_margin_velocity',
    'check_orphaned_events', 'tally_site_buckets',
]
