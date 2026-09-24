from __future__ import annotations

from typing import Any, Dict, List, Optional
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.transactions.models import Order, OrderLine, Invoice, InvoiceLine, Purchase
from apps.products.models.item import Item
from apps.products.models.inventory_layer import InventoryLayer
from apps.products.models.inventory_reservation import InventoryReservation
from apps.core.models.pending import Pending


class InventoryFlowError(Exception):
    """Custom exception for inventory flow operations."""
    pass


def _resolve_item_id_from_line(line) -> Optional[int]:
    """Extract item ID from line's item JSON."""
    item = getattr(line, 'item', {}) or {}
    return item.get('id_num') or item.get('id') or item.get('item_id')


def process_inventory_deltas_immediately(item_ids: List[int]) -> Dict[str, Any]:
    """
    Process inventory deltas immediately for specified items.

    This bypasses the queue for critical inventory updates that need to happen in real-time.

    Returns:
        {
            'processed_deltas': int,
            'updated_items': int,
            'errors': List[str]
        }
    """
    from django.db import transaction

    processed_deltas = 0
    updated_items = 0
    errors = []

    try:
        with transaction.atomic():
            # Get all unprocessed deltas for these items
            deltas = Pending.objects.filter(
                model_name='inventory_delta',
                purpose='inventory_delta',
                dt_processed=0,
                config__item_id__in=item_ids
            ).select_for_update()

            # Group by item
            item_deltas = {}
            for delta in deltas:
                item_id = delta.config.get('item_id')
                if item_id not in item_deltas:
                    item_deltas[item_id] = []
                item_deltas[item_id].append(delta)

            # Process each item
            for item_id, item_deltas_list in item_deltas.items():
                try:
                    item = Item.objects.select_for_update().get(pk=item_id)

                    # Calculate total changes
                    on_hand_change = sum(Decimal(str(d.config.get('quantity_on_hand_delta', 0))) for d in item_deltas_list)
                    on_order_change = sum(Decimal(str(d.config.get('quantity_on_order_delta', 0))) for d in item_deltas_list)
                    on_po_change = sum(Decimal(str(d.config.get('quantity_on_po_delta', 0))) for d in item_deltas_list)

                    # Update item quantities
                    if hasattr(item, 'quantity') and item.quantity:
                        qty = item.quantity
                    else:
                        qty = {}

                    qty['on_hand'] = float(Decimal(str(qty.get('on_hand', 0))) + on_hand_change)
                    qty['on_order'] = float(Decimal(str(qty.get('on_order', 0))) + on_order_change)
                    qty['on_po'] = float(Decimal(str(qty.get('on_po', 0))) + on_po_change)

                    item.quantity = qty
                    item.save(update_fields=['quantity', 'dt_modified', 'version'])

                    # Mark deltas as processed
                    for delta in item_deltas_list:
                        delta.mark_processed()

                    processed_deltas += len(item_deltas_list)
                    updated_items += 1

                except Item.DoesNotExist:
                    errors.append(f"Item {item_id} not found")
                    continue
                except Exception as e:
                    errors.append(f"Error processing item {item_id}: {str(e)}")
                    continue

    except Exception as e:
        errors.append(f"Transaction error: {str(e)}")

    return {
        'processed_deltas': processed_deltas,
        'updated_items': updated_items,
        'errors': errors
    }


def _create_inventory_discrepancy_pending(
    item_id: int,
    warehouse_id: int,
    missing_quantity: float,
    source_reservation_id: int,
    discrepancy_type: str
) -> Pending:
    """Create a pending task to investigate inventory discrepancies.
    
    This helps track data inconsistencies that need manual review.
    """
    import uuid
    from django.utils import timezone
    
    record_id = f"discrepancy_{item_id}_{warehouse_id}_{int(timezone.now().timestamp() * 1000000)}_{uuid.uuid4().hex[:8]}"
    
    data = {
        'item_id': item_id,
        'warehouse_id': warehouse_id,
        'missing_quantity': missing_quantity,
        'source_reservation_id': source_reservation_id,
        'discrepancy_type': discrepancy_type,
        'detected_at': timezone.now().isoformat(),
        'status': 'pending_investigation'
    }
    
    return Pending.objects.create(
        model_name='inventory_discrepancy',
        record_id=record_id,
        purpose='inventory_discrepancy',
        name=f"Inventory discrepancy for item {item_id}",
        config=data
    )


def validate_inventory_delta(delta: Pending) -> Dict[str, Any]:
    """
    Validate inventory delta data integrity.

    Returns:
        {
            'is_valid': bool,
            'errors': List[str],
            'warnings': List[str]
        }
    """
    errors = []
    warnings = []

    data = delta.config or {}

    # Required fields
    required_fields = ['item_id', 'source_type', 'source_id']
    for field in required_fields:
        if field not in data or data[field] is None:
            errors.append(f"Missing required field: {field}")

    # Item existence
    item_id = data.get('item_id')
    if item_id:
        try:
            Item.objects.get(pk=item_id)
        except Item.DoesNotExist:
            errors.append(f"Item {item_id} does not exist")

    # Quantity validation
    quantity_fields = ['quantity_on_hand_delta', 'quantity_on_order_delta', 'quantity_on_po_delta']
    for field in quantity_fields:
        value = data.get(field, 0)
        if not isinstance(value, (int, float)):
            errors.append(f"Invalid {field}: must be numeric")
        elif abs(value) > 1000000:  # Reasonable upper bound
            warnings.append(f"Large {field} value: {value}")

    # Source type validation
    valid_source_types = [
        'order_line', 'purchase_line', 'invoice_line',
        'purchase_receipt', 'inventory_adjustment'
    ]
    source_type = data.get('source_type')
    if source_type and source_type not in valid_source_types:
        warnings.append(f"Unknown source_type: {source_type}")

    return {
        'is_valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }


def audit_inventory_consistency() -> Dict[str, Any]:
    """
    Audit inventory consistency by comparing calculated vs stored quantities.

    Returns:
        {
            'total_items': int,
            'consistent_items': int,
            'inconsistent_items': int,
            'discrepancies': List[Dict]
        }
    """
    from django.db.models import Sum

    discrepancies = []
    consistent_items = 0
    inconsistent_items = 0

    # Get all items with quantities
    items = Item.objects.exclude(quantity__isnull=True).exclude(quantity={})

    for item in items:
        item_id = item.id
        stored_qty = item.quantity or {}

        stored_on_hand = Decimal(str(stored_qty.get('on_hand', 0)))
        stored_on_order = Decimal(str(stored_qty.get('on_order', 0)))
        stored_on_po = Decimal(str(stored_qty.get('on_po', 0)))

        # Calculate from deltas
        delta_sums = Pending.objects.filter(
            model_name='inventory_delta',
            purpose='inventory_delta',
            config__item_id=item_id
        ).aggregate(
            on_hand_sum=Sum('config__quantity_on_hand_delta'),
            on_order_sum=Sum('config__quantity_on_order_delta'),
            on_po_sum=Sum('config__quantity_on_po_delta')
        )

        calc_on_hand = Decimal(str(delta_sums['on_hand_sum'] or 0))
        calc_on_order = Decimal(str(delta_sums['on_order_sum'] or 0))
        calc_on_po = Decimal(str(delta_sums['on_po_sum'] or 0))

        # Check consistency (allowing for small floating point differences)
        tolerance = Decimal('0.01')

        if (abs(stored_on_hand - calc_on_hand) > tolerance or
            abs(stored_on_order - calc_on_order) > tolerance or
            abs(stored_on_po - calc_on_po) > tolerance):

            inconsistent_items += 1
            discrepancies.append({
                'item_id': item_id,
                'item_name': str(item),
                'stored': {
                    'on_hand': float(stored_on_hand),
                    'on_order': float(stored_on_order),
                    'on_po': float(stored_on_po)
                },
                'calculated': {
                    'on_hand': float(calc_on_hand),
                    'on_order': float(calc_on_order),
                    'on_po': float(calc_on_po)
                },
                'differences': {
                    'on_hand': float(stored_on_hand - calc_on_hand),
                    'on_order': float(stored_on_order - calc_on_order),
                    'on_po': float(stored_on_po - calc_on_po)
                }
            })
        else:
            consistent_items += 1

    return {
        'total_items': len(items),
        'consistent_items': consistent_items,
        'inconsistent_items': inconsistent_items,
        'discrepancies': discrepancies
    }


__all__ = [
    'process_inventory_deltas_immediately',
    'validate_inventory_delta',
    'audit_inventory_consistency',
    'InventoryFlowError',
]