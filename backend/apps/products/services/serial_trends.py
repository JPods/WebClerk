"""Serial trend consolidation service.

Queries all serials for an item, aggregates config.actions[] data,
and writes/updates a Document(purpose='serial_trends') record.

The serial_trends document gives item-level visibility into defect rates,
warranty patterns, inspection results, and lifecycle metrics across all
serialized units — without querying individual serial records.

If data outgrows one document record, additional sequence records are created.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone as tz
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.docs.models.document import Document
from apps.products.models.serial import Serial
from apps.products.models.item import Item


# -- Standard lifecycle action names (match Setting.serial.config) -----------

LIFECYCLE_ACTIONS = {
    'Received on purchase order', 'Made available', 'Reserved for order',
    'Issued in invoice', 'Returned from customer', 'Removed from order',
    'Removed from invoice', 'Voided from purchase order', 'Return to vendor',
    'Referenced in document', 'Warranty claim opened', 'Marked as damaged',
    'Scrapped',
}

# Actions whose presence indicates a defect or quality issue
DEFECT_INDICATORS = {
    'Marked as damaged', 'Warranty claim opened', 'Returned from customer',
}


def consolidate_serial_trends(item_id: int) -> Optional[Document]:
    """Query all serials for an item and consolidate into a serial_trends Document.

    Creates the Document if it doesn't exist. Updates if it does.
    Returns the Document record, or None if the item has no serials.
    """
    try:
        item = Item.objects.get(pk=item_id)
    except Item.DoesNotExist:
        return None

    serials = Serial.objects.filter(item_id=item_id).only(
        'id', 'serial_ida', 'model_ida', 'status', 'warranty', 'config',
    )

    serial_count = serials.count()
    if serial_count == 0:
        return None

    # -- Aggregate --
    status_dist: Counter = Counter()
    defects_by_type: Counter = Counter()
    defects_total = 0
    inspections_total = 0
    inspections_passed = 0
    warranty_active = 0
    warranty_expiring_30d = 0
    warranty_claims = 0
    days_to_claim: list[int] = []
    days_on_plan: list[int] = []
    days_to_issue: list[int] = []
    costs: list[float] = []
    prices: list[float] = []
    returns = 0
    scrapped = 0
    recent_actions: list[dict] = []
    user_actions: Counter = Counter()

    now_ms = int(timezone.now().timestamp() * 1000)
    thirty_days_ms = 30 * 24 * 3600 * 1000

    for serial in serials:
        status_dist[serial.status] += 1
        cfg = serial.config or {}
        actions = cfg.get('actions', [])

        # Cost/price from config
        cost = cfg.get('cost', 0.0)
        price = cfg.get('price', 0.0)
        if cost:
            costs.append(float(cost))
        if price:
            prices.append(float(price))

        # Days on plan
        dop = cfg.get('days_on_plan', 0)
        if dop:
            days_on_plan.append(dop)

        # Warranty
        warranty = serial.warranty or {}
        if warranty.get('dt_end'):
            try:
                end_dt = datetime.fromisoformat(str(warranty['dt_end']))
                end_ms = int(end_dt.timestamp() * 1000)
                if end_ms > now_ms:
                    warranty_active += 1
                    if end_ms - now_ms < thirty_days_ms:
                        warranty_expiring_30d += 1
            except (ValueError, TypeError):
                pass

        # Process actions
        dt_received_ms = None
        dt_issued_ms = None

        for act in actions:
            action_name = act.get('action', '')
            act_dt = act.get('dt', 0)

            # Track lifecycle timestamps
            if action_name == 'Received on purchase order':
                dt_received_ms = act_dt
            elif action_name == 'Issued in invoice':
                dt_issued_ms = act_dt
                if dt_received_ms:
                    days_to_issue.append(
                        (dt_issued_ms - dt_received_ms) // (86400 * 1000)
                    )

            # Defects
            if action_name in DEFECT_INDICATORS:
                defects_total += 1
                defects_by_type[action_name] += 1

            # Warranty claims
            if action_name == 'Warranty claim opened':
                warranty_claims += 1
                if dt_issued_ms:
                    days_to_claim.append(
                        (act_dt - dt_issued_ms) // (86400 * 1000)
                    )

            # Returns and scraps
            if action_name == 'Returned from customer':
                returns += 1
            if action_name == 'Scrapped':
                scrapped += 1

            # Inspections (user-defined actions containing 'inspect')
            if 'inspect' in action_name.lower():
                inspections_total += 1
                if act.get('status_after') in ('available', 'issued'):
                    inspections_passed += 1

            # User-defined actions (not in standard lifecycle)
            if action_name not in LIFECYCLE_ACTIONS:
                user_actions[action_name] += 1

            # Recent actions (last 30 days)
            if act_dt and (now_ms - act_dt) < thirty_days_ms:
                recent_actions.append({
                    'action': action_name,
                    'serial_ida': serial.serial_ida,
                    'dt': act_dt,
                    'notes': act.get('notes', ''),
                })

    # Sort recent by dt descending, keep top 20
    recent_actions.sort(key=lambda x: x.get('dt', 0), reverse=True)
    recent_actions = recent_actions[:20]

    # -- Build trend data --
    def _safe_avg(values: list) -> float:
        return round(sum(values) / len(values), 2) if values else 0.0

    avg_cost = _safe_avg(costs)
    avg_price = _safe_avg(prices)
    avg_margin = round(avg_price - avg_cost, 2)

    trend_data = {
        'item_id': item_id,
        'item_ida': getattr(item, 'ida', str(item_id)),
        'dt_consolidated': now_ms,
        'serial_count': serial_count,
        'status_distribution': dict(status_dist),
        'defects': {
            'total': defects_total,
            'by_type': dict(defects_by_type),
            'defect_rate': round(defects_total / serial_count, 3) if serial_count else 0,
        },
        'warranty': {
            'active': warranty_active,
            'expiring_30d': warranty_expiring_30d,
            'claims_total': warranty_claims,
            'claim_rate': round(warranty_claims / serial_count, 3) if serial_count else 0,
            'avg_days_to_claim': _safe_avg(days_to_claim),
        },
        'inspections': {
            'total': inspections_total,
            'pass_rate': round(inspections_passed / inspections_total, 2) if inspections_total else 0,
        },
        'lifecycle': {
            'avg_days_on_plan': _safe_avg(days_on_plan),
            'avg_days_to_issue': _safe_avg(days_to_issue),
            'return_rate': round(returns / serial_count, 3) if serial_count else 0,
            'scrap_rate': round(scrapped / serial_count, 3) if serial_count else 0,
        },
        'cost': {
            'avg_unit_cost': avg_cost,
            'avg_unit_price': avg_price,
            'avg_margin': avg_margin,
            'margin_percent': round(avg_margin / avg_price, 2) if avg_price else 0,
        },
        'user_actions': dict(user_actions),
        'recent_actions': recent_actions,
    }

    # -- Write to Document --
    with transaction.atomic():
        doc, created = Document.objects.update_or_create(
            purpose='serial_trends',
            config__item_id=item_id,
            sequence=0,
            defaults={
                'name': f'Serial Trends — {getattr(item, "ida", item_id)}',
                'status': 'active',
                'config': {'item_id': item_id, 'item_ida': getattr(item, 'ida', str(item_id))},
                'body': '',
                'description': f'Consolidated serial trend data for {getattr(item, "ida", item_id)}',
            },
        )
        doc.config = doc.config or {}
        doc.config['item_id'] = item_id
        doc.config['data'] = trend_data
        doc.save(update_fields=['config'])

    return doc


def ensure_serial_trends_document(item_id: int) -> Document:
    """Create a serial_trends Document for an item if one doesn't exist.

    Called when an item becomes serialized (is_serialized=True).
    """
    try:
        item = Item.objects.get(pk=item_id)
    except Item.DoesNotExist:
        return None

    doc, created = Document.objects.get_or_create(
        purpose='serial_trends',
        config__item_id=item_id,
        sequence=0,
        defaults={
            'name': f'Serial Trends — {getattr(item, "ida", item_id)}',
            'status': 'active',
            'config': {'item_id': item_id, 'item_ida': getattr(item, 'ida', str(item_id))},
            'description': f'Consolidated serial trend data for {getattr(item, "ida", item_id)}',
        },
    )
    return doc
