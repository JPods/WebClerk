"""Bulk serial receive and ship services.

Serial Load JSON — Alice normalizes any vendor document (packing list,
spreadsheet, scan log, EDI) into this standard format. The bulk receive
service creates Serial records and sets quantity.active = count.

Shipping — select serial numbers for an invoice line. Quantity shipped
must match quantity selected. No partial — exact match required.
"""
from __future__ import annotations

from typing import Optional
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.products.models.serial import Serial
from apps.products.models.item import Item


# ---------------------------------------------------------------------------
# Serial Load JSON Schema
# ---------------------------------------------------------------------------
#
# Alice produces this from any vendor document:
#
# {
#     "item_ida": "WDG-001",
#     "description": "Widget A — batch received 2026-08-09",
#     "dt": 1723190400000,
#     "purchase_id": 100,
#     "purchase_line_id": 301,
#     "vendor_id": 42,
#     "warehouse_id": 1,
#     "cost": 4.80,
#     "warranty_days": 365,
#     "count": 3,
#     "serials": [
#         {
#             "serial_ida": "SN-0001",
#             "model_ida": "MDL-A",
#             "description": "Unit 1",
#             "qr_code": "",
#             "notes": "Inspected OK"
#         },
#         {
#             "serial_ida": "SN-0002",
#             "model_ida": "MDL-A"
#         },
#         {
#             "serial_ida": "SN-0003",
#             "model_ida": "MDL-B",
#             "notes": "Packaging damaged, unit OK"
#         }
#     ]
# }
#
# Rules:
#   - count must match len(serials)
#   - item_ida must resolve to an existing Item
#   - Each serial entry needs at minimum serial_ida
#   - Header fields (vendor_id, purchase_id, cost, warranty_days) apply
#     to all serials unless overridden per-entry
#   - Alice validates before submitting — rejects if count != len(serials)


def validate_serial_load(payload: dict) -> list[str]:
    """Validate a serial load JSON payload. Returns list of error strings (empty = valid)."""
    errors = []

    item_ida = payload.get('item_ida', '')
    if not item_ida:
        errors.append('item_ida is required')
    elif not Item.objects.filter(ida=item_ida).exists():
        errors.append(f'Item not found: {item_ida}')

    serials = payload.get('serials', [])
    count = payload.get('count', 0)

    if not serials:
        errors.append('serials array is empty')
    elif count != len(serials):
        errors.append(f'count ({count}) does not match serials length ({len(serials)})')

    for i, s in enumerate(serials):
        if not s.get('serial_ida'):
            errors.append(f'serials[{i}]: serial_ida is required')

    return errors


@transaction.atomic
def bulk_receive_serials(payload: dict) -> dict:
    """Create Serial records from a serial load JSON and set quantity.active = count.

    Args:
        payload: Serial load JSON (see schema above)

    Returns:
        {
            "item_id": int,
            "count": int,
            "serial_ids": [int, ...],
            "errors": [str, ...]  (empty on success)
        }
    """
    errors = validate_serial_load(payload)
    if errors:
        return {'item_id': None, 'count': 0, 'serial_ids': [], 'errors': errors}

    item = Item.objects.get(ida=payload['item_ida'])
    now = timezone.now()
    now_ms = int(now.timestamp() * 1000)

    # Header defaults
    vendor_id = payload.get('vendor_id')
    purchase_id = payload.get('purchase_id')
    purchase_line_id = payload.get('purchase_line_id')
    warehouse_id = payload.get('warehouse_id')
    header_cost = float(payload.get('cost', 0.0))
    warranty_days = payload.get('warranty_days', 0)

    serial_ids = []

    for entry in payload['serials']:
        # Per-entry overrides
        unit_cost = float(entry.get('cost', header_cost))
        unit_warranty = entry.get('warranty_days', warranty_days)

        serial = Serial(
            item=item,
            item_ida=item.ida or str(item.pk),
            serial_ida=entry['serial_ida'],
            model_ida=entry.get('model_ida', ''),
            description=entry.get('description', ''),
            qr_code=entry.get('qr_code', ''),
            status='received',
            site={'warehouse_id': warehouse_id} if warehouse_id else {},
            config={
                'customer_id': None,
                'vendor_id': vendor_id,
                'invoice_id': None,
                'order_id': None,
                'purchase_id': purchase_id,
                'purchase_line_ref': purchase_line_id,
                'sales_line_ref': None,
                'cost': unit_cost,
                'price': 0.0,
                'discount': 0.0,
                'dt_received': now.isoformat(),
                'dt_shipped': None,
                'days_on_plan': 0,
                'floor_plan': {'is_active': False, 'dt_expires': None, 'plan_line': None},
                'actions': [
                    {
                        'action': 'Received on purchase order',
                        'dt': now_ms,
                        'status_before': None,
                        'status_after': 'received',
                        'doc_type': 'purchase',
                        'doc_id': purchase_id,
                        'cost': unit_cost,
                        'notes': entry.get('notes', ''),
                        'by': 'alice',
                    }
                ],
            },
        )

        if unit_warranty:
            serial.warranty = {
                'days': unit_warranty,
                'dt_start': None,
                'dt_end': None,
            }

        serial.save()
        serial_ids.append(serial.pk)

    # Set quantity.active on the purchase line if provided
    if purchase_line_id:
        _set_line_quantity_active(purchase_line_id, len(serial_ids))

    return {
        'item_id': item.pk,
        'count': len(serial_ids),
        'serial_ids': serial_ids,
        'errors': [],
    }


def _set_line_quantity_active(purchase_line_id: int, count: int):
    """Set quantity.active on a PurchaseLine to match the serial count."""
    from apps.transactions.models.purchase_line import PurchaseLine
    try:
        line = PurchaseLine.objects.get(pk=purchase_line_id)
        qty = line.quantity or {}
        qty['active'] = count
        qty['remaining'] = max(0, count - float(qty.get('children_active_total', 0)))
        line.quantity = qty
        line.save(update_fields=['quantity'])
    except PurchaseLine.DoesNotExist:
        pass


# ---------------------------------------------------------------------------
# Shipping — select serials for invoice line
# ---------------------------------------------------------------------------

def available_serials_for_item(item_id: int, status: str = 'available') -> list[dict]:
    """List serials available for shipping for a given item.

    Returns list of {id, serial_ida, model_ida, description, status, cost, site}.
    """
    serials = Serial.objects.filter(
        item_id=item_id,
        status=status,
        is_active=True,
    ).order_by('serial_ida')

    return [
        {
            'id': s.pk,
            'serial_ida': s.serial_ida,
            'model_ida': s.model_ida,
            'description': s.description,
            'status': s.status,
            'cost': (s.config or {}).get('cost', 0.0),
            'site': s.site or {},
        }
        for s in serials
    ]


def auto_select_serials(item_id: int, qty_required: int, strategy: str = 'fifo') -> list[dict]:
    """Auto-select available serials for an item to match qty_required.

    Strategies:
      - fifo: oldest received first (default — matches FIFO cost layer)
      - lifo: newest received first
      - cost_low: lowest cost first (maximize margin)
      - cost_high: highest cost first (move expensive inventory)

    Returns list of {id, serial_ida, model_ida, cost} or raises ValueError
    if not enough available serials.
    """
    ordering = {
        'fifo': 'dt_created',
        'lifo': '-dt_created',
        'cost_low': 'config__cost',
        'cost_high': '-config__cost',
    }

    order_by = ordering.get(strategy, 'dt_created')

    available = Serial.objects.filter(
        item_id=item_id,
        status='available',
        is_active=True,
    ).order_by(order_by)

    total_available = available.count()
    if total_available < qty_required:
        raise ValueError(
            f'Need {qty_required} serials but only {total_available} available for item {item_id}'
        )

    selected = available[:qty_required]
    return [
        {
            'id': s.pk,
            'serial_ida': s.serial_ida,
            'model_ida': s.model_ida,
            'cost': (s.config or {}).get('cost', 0.0),
        }
        for s in selected
    ]


def validate_serial_selection(serial_ids: list[int], item_id: int, qty_required: int) -> list[str]:
    """Validate that selected serials match the required quantity.

    Rules:
      - len(serial_ids) must equal qty_required (exact match, no partial)
      - All serials must belong to the same item
      - All serials must be available (status = 'available')
      - No duplicates
    """
    errors = []

    if len(serial_ids) != qty_required:
        errors.append(
            f'Selected {len(serial_ids)} serials but quantity requires {qty_required} — must match exactly'
        )

    if len(serial_ids) != len(set(serial_ids)):
        errors.append('Duplicate serial IDs in selection')

    serials = Serial.objects.filter(pk__in=serial_ids)

    if serials.count() != len(serial_ids):
        found = set(serials.values_list('pk', flat=True))
        missing = set(serial_ids) - found
        errors.append(f'Serial IDs not found: {missing}')

    for s in serials:
        if s.item_id != item_id:
            errors.append(f'Serial {s.serial_ida} (id={s.pk}) belongs to item {s.item_id}, not {item_id}')
        if s.status != 'available':
            errors.append(f'Serial {s.serial_ida} (id={s.pk}) status is {s.status}, not available')

    return errors


@transaction.atomic
def issue_serials_on_invoice(
    serial_ids: list[int],
    customer_id: int,
    invoice_id: int,
    invoice_line_id: int = None,
    price: float = 0.0,
    discount: float = 0.0,
) -> dict:
    """Issue selected serials on an invoice line.

    All selected serials move to status='issued', warranty starts,
    config updated with customer/invoice/price.

    Args:
        serial_ids: List of Serial PKs to issue
        customer_id: Customer receiving the goods
        invoice_id: Invoice document ID
        invoice_line_id: Invoice line ID (optional)
        price: Unit price
        discount: Unit discount

    Returns:
        {
            "count": int,
            "issued": [{serial_id, serial_ida, status}, ...],
            "errors": [str, ...]
        }
    """
    serials = Serial.objects.filter(pk__in=serial_ids).select_for_update()
    issued = []
    errors = []

    for serial in serials:
        if serial.status != 'available':
            errors.append(f'{serial.serial_ida}: status is {serial.status}, cannot issue')
            continue

        serial.issue_on_invoice(
            customer_id=customer_id,
            invoice_id=invoice_id,
            sales_line_ref=invoice_line_id,
            price=price,
            cost=float((serial.config or {}).get('cost', 0.0)),
            discount=discount,
        )

        issued.append({
            'serial_id': serial.pk,
            'serial_ida': serial.serial_ida,
            'status': serial.status,
        })

    return {
        'count': len(issued),
        'issued': issued,
        'errors': errors,
    }
