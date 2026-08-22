"""
Alice Inventory Watchdog — Detect over/understock and velocity anomalies.

Scans for:
1. Items below inventory_min (reorder point) — understock
2. Items above inventory_max — overstock
3. Items with negative on_hand — data error
4. Dead stock (on_hand > 0, no sales in 90+ days)
5. Quantity mismatches (available != on_hand - allocated)

Extends the existing InventoryEventEmitter alert system with periodic
batch scanning. The emitter catches real-time threshold crossings;
this watchdog catches accumulated drift and items that were never set
up with proper thresholds.

Creates AliceObservation records for anything requiring attention.

Called by: inventory_watchdog_task (Celery, nightly)
"""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger('alice.inventory')


def run_inventory_watchdog(limit: int = 1000) -> dict:
    """Run all inventory checks. Returns summary of findings."""
    results = {}
    results['understock'] = check_understock(limit)
    results['overstock'] = check_overstock(limit)
    results['negative_on_hand'] = check_negative_on_hand(limit)
    results['quantity_mismatch'] = check_quantity_mismatch(limit)
    results['dead_stock'] = check_dead_stock(limit)

    total_obs = sum(r.get('observations', 0) for r in results.values())
    logger.info("Inventory watchdog complete: %d observations created", total_obs)
    return results


def check_understock(limit: int = 1000) -> dict:
    """Find items where on_hand < inventory_min (reorder point)."""
    from apps.products.models import Item

    observations = 0
    understock_items = []

    # Items with both on_hand and inventory_min set (include demo — users learn there)
    items = Item.objects.filter(
        is_active=True,
        quantity__on_hand__isnull=False,
        quantity__inventory_min__isnull=False,
    ).only('id', 'ida', 'quantity', 'name')[:limit]

    for item in items:
        qty = item.quantity or {}
        on_hand = qty.get('on_hand', 0) or 0
        inv_min = qty.get('inventory_min', 0) or 0

        if inv_min > 0 and on_hand < inv_min:
            shortfall = inv_min - on_hand
            understock_items.append({
                'id': item.id,
                'ida': item.ida,
                'on_hand': on_hand,
                'reorder_point': inv_min,
                'shortfall': shortfall,
            })

            _create_observation(
                category='alert',
                model_name='item',
                record_id=item.id,
                message=f"Item {item.ida} below reorder point: "
                        f"{on_hand} on hand, min={inv_min} (short {shortfall})",
                detail=f"Item: {item.name or item.ida}. "
                       f"Consider placing a purchase order.",
                dedup_key=f"understock_{item.id}",
                priority=1,
            )
            observations += 1

    return {
        'items_checked': len(items),
        'understock_count': len(understock_items),
        'observations': observations,
    }


def check_overstock(limit: int = 1000) -> dict:
    """Find items where on_hand > inventory_max."""
    from apps.products.models import Item

    observations = 0
    overstock_items = []

    items = Item.objects.filter(
        is_active=True,
        quantity__on_hand__isnull=False,
        quantity__inventory_max__isnull=False,
    ).only('id', 'ida', 'quantity', 'name')[:limit]

    for item in items:
        qty = item.quantity or {}
        on_hand = qty.get('on_hand', 0) or 0
        inv_max = qty.get('inventory_max', 0) or 0

        if inv_max > 0 and on_hand > inv_max:
            excess = on_hand - inv_max
            overstock_items.append({
                'id': item.id,
                'ida': item.ida,
                'on_hand': on_hand,
                'max_stock': inv_max,
                'excess': excess,
            })

            _create_observation(
                category='alert',
                model_name='item',
                record_id=item.id,
                message=f"Item {item.ida} above max stock: "
                        f"{on_hand} on hand, max={inv_max} (excess {excess})",
                detail=f"Item: {item.name or item.ida}. "
                       f"Excess inventory ties up capital. "
                       f"Consider promotions or returns to vendor.",
                dedup_key=f"overstock_{item.id}",
                priority=0,
            )
            observations += 1

    return {
        'items_checked': len(items),
        'overstock_count': len(overstock_items),
        'observations': observations,
    }


def check_negative_on_hand(limit: int = 1000) -> dict:
    """Find items with negative on_hand — indicates data error."""
    from apps.products.models import Item

    observations = 0

    # JSONField query for negative values — check in Python
    items = Item.objects.filter(
        is_active=True,
        quantity__on_hand__isnull=False,
    ).only('id', 'ida', 'quantity', 'name')[:limit]

    negative_items = []
    for item in items:
        qty = item.quantity or {}
        on_hand = qty.get('on_hand', 0) or 0
        if on_hand < 0:
            negative_items.append({
                'id': item.id,
                'ida': item.ida,
                'on_hand': on_hand,
            })

    if negative_items:
        # One observation for all negative items (batch)
        detail_lines = [
            f"  {ni['ida']}: on_hand={ni['on_hand']}"
            for ni in negative_items[:20]
        ]
        if len(negative_items) > 20:
            detail_lines.append(f"  ... and {len(negative_items) - 20} more")

        _create_observation(
            category='anomaly',
            model_name='item',
            message=f"{len(negative_items)} items have negative on_hand quantities",
            detail="Negative on_hand indicates overselling or data entry error.\n"
                   + "\n".join(detail_lines),
            dedup_key=f"negative_on_hand_{timezone.now().strftime('%Y-%W')}",
            priority=2,
        )
        observations += 1

    return {
        'items_checked': len(items),
        'negative_count': len(negative_items),
        'observations': observations,
    }


def check_quantity_mismatch(limit: int = 1000) -> dict:
    """Check that available == on_hand - allocated for all items."""
    from apps.products.models import Item

    observations = 0
    mismatches = []

    items = Item.objects.filter(
        is_active=True,
        quantity__on_hand__isnull=False,
        quantity__allocated__isnull=False,
        quantity__available__isnull=False,
    ).only('id', 'ida', 'quantity')[:limit]

    for item in items:
        qty = item.quantity or {}
        on_hand = Decimal(str(qty.get('on_hand', 0) or 0))
        allocated = Decimal(str(qty.get('allocated', 0) or 0))
        available = Decimal(str(qty.get('available', 0) or 0))
        expected = on_hand - allocated

        if abs(available - expected) > Decimal('0.001'):
            mismatches.append({
                'id': item.id,
                'ida': item.ida,
                'on_hand': float(on_hand),
                'allocated': float(allocated),
                'available': float(available),
                'expected': float(expected),
            })

    if mismatches:
        detail_lines = [
            f"  {m['ida']}: avail={m['available']} expected={m['expected']} "
            f"(on_hand={m['on_hand']} - alloc={m['allocated']})"
            for m in mismatches[:20]
        ]

        _create_observation(
            category='anomaly',
            model_name='item',
            message=f"{len(mismatches)} items have quantity calculation mismatches",
            detail="available should equal on_hand - allocated.\n"
                   + "\n".join(detail_lines),
            dedup_key=f"qty_mismatch_{timezone.now().strftime('%Y-%W')}",
            priority=1,
        )
        observations += 1

    return {
        'items_checked': len(items),
        'mismatch_count': len(mismatches),
        'observations': observations,
    }


def check_dead_stock(limit: int = 1000) -> dict:
    """Find items with on_hand > 0 but no sales activity in 90+ days.

    Uses the velocity_category field if populated, otherwise checks
    last_sale_dt from item stats.
    """
    from apps.products.models import Item

    observations = 0
    now = timezone.now()
    cutoff = now - timezone.timedelta(days=90)
    cutoff_ms = int(cutoff.timestamp() * 1000)

    # Items already tagged as dead_capital by margin_tracker
    dead_by_tag = Item.objects.filter(
        is_active=True,
        velocity_category='dead_capital',
        quantity__on_hand__gt=0,
    ).count()

    # Items with on_hand > 0 and no recent transaction lines
    # Check via stats.last_sale_dt if available
    items_with_stock = Item.objects.filter(
        is_active=True,
        quantity__on_hand__gt=0,
    ).exclude(
        velocity_category='dead_capital',  # already tagged
    ).only('id', 'ida', 'quantity', 'stats', 'name')[:limit]

    newly_dead = []
    for item in items_with_stock:
        stats = item.stats if isinstance(item.stats, dict) else {}
        last_sale = stats.get('last_sale_dt') or stats.get('dt_last_sold', 0)
        if isinstance(last_sale, (int, float)) and last_sale > 0:
            if last_sale < cutoff_ms:
                on_hand = (item.quantity or {}).get('on_hand', 0)
                newly_dead.append({
                    'id': item.id,
                    'ida': item.ida,
                    'on_hand': on_hand,
                    'days_since_sale': (now.timestamp() * 1000 - last_sale) / 86400000,
                })

    total_dead = dead_by_tag + len(newly_dead)
    if total_dead > 0:
        detail = f"Tagged dead_capital: {dead_by_tag}\n"
        detail += f"Newly identified (no sales 90+ days): {len(newly_dead)}\n"
        if newly_dead:
            for nd in newly_dead[:15]:
                detail += f"  {nd['ida']}: {nd['on_hand']} on hand, " \
                          f"{nd['days_since_sale']:.0f} days since last sale\n"

        _create_observation(
            category='alert',
            model_name='item',
            message=f"{total_dead} items are dead stock (on hand, no sales 90+ days)",
            detail=detail,
            dedup_key=f"dead_stock_{now.strftime('%Y-%W')}",
            priority=0,
        )
        observations += 1

    return {
        'items_checked': len(items_with_stock),
        'dead_tagged': dead_by_tag,
        'dead_new': len(newly_dead),
        'observations': observations,
    }


# ── Helpers ──────────────────────────────────────────────────────────

def _create_observation(category, model_name, message, detail='',
                        record_id=None, dedup_key='', priority=0):
    """Create an AliceObservation, deduped."""
    try:
        from apps.ai_assistant.models_alice import AliceObservation

        if dedup_key:
            if AliceObservation.objects.filter(
                dedup_key=dedup_key, resolved=False
            ).exists():
                return

        AliceObservation.objects.create(
            category=category,
            source='alice',
            priority=priority,
            message=message,
            detail=detail,
            model_name=model_name,
            record_id=record_id,
            dedup_key=dedup_key,
        )
    except Exception as e:
        logger.warning("Failed to create inventory observation: %s", e)
