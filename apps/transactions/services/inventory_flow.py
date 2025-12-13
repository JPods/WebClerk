from __future__ import annotations

from typing import Any, Dict, List, Optional
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.transactions.models import SalesOrder, SalesOrderLine, Invoice, InvoiceLine, PurchaseOrder
from apps.products.models.item import Item
from apps.products.models.inventory_layer import InventoryLayer
from apps.products.models.inventory_reservation import InventoryReservation
from apps.core.models.pending import Pending


class InventoryFlowError(Exception):
    """Custom exception for inventory flow operations."""
    pass


@transaction.atomic
def reserve_inventory_for_order(order: SalesOrder) -> Dict[str, int]:
    """
    Create inventory reservations for sales order lines.

    Reserves available inventory to prevent overselling. Only reserves for items
    with sufficient available stock.

    Returns:
        {
            'reservations_created': int,
            'lines_reserved': int,
            'total_quantity_reserved': float
        }
    """
    if order.status not in ['confirmed', 'released']:
        raise InventoryFlowError("Order must be confirmed or released to reserve inventory")

    reservations_created = 0
    lines_reserved = 0
    total_reserved = Decimal(0)

    for line in SalesOrderLine.objects.filter(parent=order).select_related('parent'):
        qty_needed = _get_order_quantity_needed(line)
        if qty_needed <= 0:
            continue

        item_id = _resolve_item_id_from_line(line)
        if not item_id:
            continue

        try:
            item = Item.objects.get(pk=item_id)
        except Item.DoesNotExist:
            continue

        # Check available inventory across all warehouses
        available_layers = InventoryLayer.objects.filter(
            item=item,
            quantity__available__gt=0
        ).order_by('dt_created')  # FIFO

        qty_to_reserve = qty_needed
        for layer in available_layers:
            if qty_to_reserve <= 0:
                break

            available = Decimal(str(layer.quantity.get('available', 0)))
            reserve_qty = min(qty_to_reserve, available)

            if reserve_qty > 0:
                # Create reservation
                reservation = InventoryReservation.objects.create(
                    item=item,
                    warehouse=layer.warehouse,
                    quantity_reserved=float(reserve_qty),
                    source_type='sales_order',
                    source_id=order.id,
                    source_line_id=line.id,
                    expires_at=None,  # No expiration for confirmed orders
                )

                # Update layer available quantity
                layer.quantity['available'] = float(available - reserve_qty)
                layer.save(update_fields=['quantity'])

                qty_to_reserve -= reserve_qty
                reservations_created += 1

        if qty_to_reserve < qty_needed:  # At least some quantity reserved
            lines_reserved += 1
            total_reserved += (qty_needed - qty_to_reserve)

    return {
        'reservations_created': reservations_created,
        'lines_reserved': lines_reserved,
        'total_quantity_reserved': float(total_reserved)
    }


@transaction.atomic
def release_inventory_on_invoice(invoice: Invoice) -> Dict[str, float]:
    """
    Release inventory reservations and create inventory deltas when invoice is created.

    This permanently removes quantities from available inventory as the sale is confirmed (or adds for returns).
    Creates Pending delta records for on_hand and on_order changes.

    Returns:
        {
            'reservations_released': int,
            'deltas_created': int,
            'total_quantity_processed': float
        }
    """
    if invoice.status not in ['sent', 'paid']:
        raise InventoryFlowError("Invoice must be sent or paid to release inventory")

    reservations_released = 0
    deltas_created = 0
    total_processed = Decimal(0)

    for line in InvoiceLine.objects.filter(parent=invoice).select_related('parent'):
        qty_invoiced = _get_invoice_quantity_invoiced(line)
        if qty_invoiced == 0:
            continue

        item_id = _resolve_item_id_from_line(line)
        if not item_id:
            continue

        # Find and release reservations for this invoice's order (only for positive invoices)
        order_id = _get_order_id_from_invoice_line(line)
        if order_id and qty_invoiced > 0:
            reservations = InventoryReservation.objects.filter(
                source_type='sales_order',
                source_id=order_id,
                source_line_id__in=_get_order_line_ids_from_invoice_line(line),
                quantity_reserved__gt=0
            )

            qty_to_release = qty_invoiced
            for reservation in reservations:
                if qty_to_release <= 0:
                    break

                reserved_qty = Decimal(str(reservation.quantity_reserved))
                release_qty = min(qty_to_release, reserved_qty)

                # Update reservation
                reservation.quantity_reserved = float(reserved_qty - release_qty)
                if reservation.quantity_reserved <= 0:
                    reservation.delete()
                else:
                    reservation.save(update_fields=['quantity_reserved'])

                # Update inventory layer (reduce available)
                try:
                    layer = InventoryLayer.objects.get(
                        item_id=reservation.item_id,
                        warehouse=reservation.warehouse
                    )
                    available = Decimal(str(layer.quantity.get('available', 0)))
                    layer.quantity['available'] = float(available - release_qty)
                    # Move to issued
                    issued = Decimal(str(layer.quantity.get('issued', 0)))
                    layer.quantity['issued'] = float(issued + release_qty)
                    layer.save(update_fields=['quantity'])
                except InventoryLayer.DoesNotExist:
                    # Layer might have been merged or removed - log this for audit purposes
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Inventory layer not found for item {reservation.item_id} "
                        f"warehouse {reservation.warehouse_id} when releasing reservation "
                        f"{reservation.id}. This may indicate data inconsistency or "
                        f"manual inventory adjustments."
                    )
                    
                    # Attempt to create a new layer with zero balance as fallback
                    try:
                        from apps.products.models.inventory_layer import InventoryLayer
                        fallback_layer = InventoryLayer.objects.create(
                            item=reservation.item,
                            warehouse=reservation.warehouse,
                            quantity={'available': 0, 'on_hand': 0, 'issued': 0},
                            unit_cost=reservation.item.default_cost or 0
                        )
                        logger.info(
                            f"Created fallback inventory layer {fallback_layer.id} "
                            f"for item {reservation.item_id} warehouse {reservation.warehouse_id}"
                        )
                    except Exception as fallback_error:
                        logger.error(
                            f"Failed to create fallback inventory layer for "
                            f"item {reservation.item_id} warehouse {reservation.warehouse_id}: {fallback_error}"
                        )

                qty_to_release -= release_qty
                reservations_released += 1

            total_processed += (qty_invoiced - qty_to_release)

        # Create inventory deltas for invoiced quantity (positive or negative)
        _create_inventory_delta(
            item_id=item_id,
            source_type='invoice_line',
            source_id=invoice.id,
            source_line_id=line.id,
            quantity_on_hand_delta=-qty_invoiced,  # Decrease on-hand for sales, increase for returns
            quantity_on_order_delta=-qty_invoiced,  # Decrease on-order for sales, increase for returns
            warehouse_id=getattr(line, 'warehouse_id', None),
            notes=f"Invoice {invoice.id} - {'shipped' if qty_invoiced > 0 else 'returned'} {abs(qty_invoiced)} units"
        )
        deltas_created += 1
        total_processed += abs(qty_invoiced)

    return {
        'reservations_released': reservations_released,
        'deltas_created': deltas_created,
        'total_quantity_processed': float(total_processed)
    }


def _get_order_quantity_needed(line: SalesOrderLine) -> Decimal:
    """Get quantity that still needs to be fulfilled/reserved."""
    qty = line.quantity or {}
    ordered = Decimal(str(qty.get('remaining', qty.get('ordered', 0))))
    reserved = Decimal(str(qty.get('reserved', 0)))
    return ordered - reserved


def _get_invoice_quantity_invoiced(line: InvoiceLine) -> Decimal:
    """Get quantity being invoiced."""
    qty = line.quantity or {}
    return Decimal(str(qty.get('remaining', qty.get('packed', 0))))


def _resolve_item_id_from_line(line) -> Optional[int]:
    """Extract item ID from line's item JSON."""
    item = getattr(line, 'item', {}) or {}
    return item.get('id_num') or item.get('id') or item.get('item_id')


def _get_order_id_from_invoice_line(line: InvoiceLine) -> Optional[int]:
    """Get original sales order ID from invoice line refs."""
    refs = getattr(line, 'refs', {}) or {}
    source = refs.get('source', {})
    return source.get('sales_order_id')


def _get_order_line_ids_from_invoice_line(line: InvoiceLine) -> List[int]:
    """Get original sales order line IDs from invoice line refs."""
    refs = getattr(line, 'refs', {}) or {}
    source = refs.get('source', {})
    order_line_id = source.get('sales_order_line_id')
    return [order_line_id] if order_line_id else []


@transaction.atomic
def cancel_order_inventory_reservations(order: SalesOrder) -> Dict[str, int]:
    """
    Release all inventory reservations for a canceled order.

    Returns:
        {
            'reservations_canceled': int,
            'quantity_restored': float
        }
    """
    reservations = InventoryReservation.objects.filter(
        source_type='sales_order',
        source_id=order.id
    )

    canceled_count = 0
    quantity_restored = Decimal(0)

    for reservation in reservations:
        qty_reserved = Decimal(str(reservation.quantity_reserved))

        # Restore to inventory layer
        try:
            layer = InventoryLayer.objects.get(
                item=reservation.item,
                warehouse=reservation.warehouse
            )
            available = Decimal(str(layer.quantity.get('available', 0)))
            layer.quantity['available'] = float(available + qty_reserved)
            layer.save(update_fields=['quantity'])
        except InventoryLayer.DoesNotExist:
            # Layer not found - this could indicate:
            # 1. Layer was manually deleted
            # 2. Layer was merged into another layer
            # 3. Data inconsistency
            
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Inventory layer not found when canceling reservation "
                f"for item {reservation.item_id} warehouse {reservation.warehouse_id}. "
                f"Reservation quantity {qty_reserved} will not be restored to inventory."
            )
            
            # Create a pending task to investigate this discrepancy
            _create_inventory_discrepancy_pending(
                item_id=reservation.item_id,
                warehouse_id=reservation.warehouse_id,
                missing_quantity=float(qty_reserved),
                source_reservation_id=reservation.id,
                discrepancy_type='missing_layer_on_cancel'
            )

        quantity_restored += qty_reserved
        reservation.delete()
        canceled_count += 1

    return {
        'reservations_canceled': canceled_count,
        'quantity_restored': float(quantity_restored)
    }


def create_inventory_deltas_for_order(order: SalesOrder) -> int:
    """
    Create inventory deltas when a sales order is created.

    Increases quantity_on_order for all order lines (or decreases for returns).

    Returns:
        Number of deltas created
    """
    deltas_created = 0

    for line in SalesOrderLine.objects.filter(parent=order):
        qty_ordered = _get_order_quantity_needed(line)
        if qty_ordered == 0:
            continue

        item_id = _resolve_item_id_from_line(line)
        if not item_id:
            continue

        _create_inventory_delta(
            item_id=item_id,
            source_type='sales_order_line',
            source_id=order.id,
            source_line_id=line.id,
            quantity_on_order_delta=qty_ordered,  # Increase on-order (or decrease for returns)
            notes=f"Sales order {order.id} - ordered {qty_ordered} units"
        )
        deltas_created += 1

    return deltas_created


def create_inventory_deltas_for_purchase_order(po: PurchaseOrder) -> int:
    """
    Create inventory deltas when a purchase order is created.

    Increases quantity_on_po for all PO lines (or decreases for returns).

    Returns:
        Number of deltas created
    """
    deltas_created = 0

    from apps.transactions.models import PurchaseOrderLine
    for line in PurchaseOrderLine.objects.filter(parent=po):
        qty_ordered = getattr(line, 'quantity', {}).get('ordered', 0) or 0
        if qty_ordered == 0:
            continue

        item_id = _resolve_item_id_from_line(line)
        if not item_id:
            continue

        _create_inventory_delta(
            item_id=item_id,
            source_type='purchase_order_line',
            source_id=po.id,
            source_line_id=line.id,
            quantity_on_po_delta=Decimal(str(qty_ordered)),  # Increase on-PO (or decrease for returns)
            notes=f"Purchase order {po.id} - ordered {qty_ordered} units"
        )
        deltas_created += 1

    return deltas_created


def _create_inventory_delta(
    item_id: int,
    source_type: str,
    source_id: int,
    source_line_id: Optional[int],
    quantity_on_hand_delta: Decimal = Decimal('0'),
    quantity_on_order_delta: Decimal = Decimal('0'),
    quantity_on_po_delta: Decimal = Decimal('0'),
    warehouse_id: Optional[int] = None,
    unit_cost: Optional[Decimal] = None,
    notes: str = "",
    process_immediately: bool = False
) -> Pending:
    """
    Create a pending inventory delta record for later processing.

    This follows the WebClerk2 dInventory approach using the Pending model.

    Args:
        process_immediately: If True, process the delta immediately instead of queuing
    """
    import uuid

    record_id = f"{item_id}_{int(timezone.now().timestamp() * 1000000)}_{uuid.uuid4().hex[:8]}"

    data = {
        'item_id': item_id,
        'warehouse_id': warehouse_id,
        'quantity_on_hand_delta': float(quantity_on_hand_delta),
        'quantity_on_order_delta': float(quantity_on_order_delta),
        'quantity_on_po_delta': float(quantity_on_po_delta),
        'source_type': source_type,
        'source_id': source_id,
        'source_line_id': source_line_id,
        'unit_cost': float(unit_cost) if unit_cost else None,
        'notes': notes,
        'created_at': timezone.now().isoformat()
    }

    pending = Pending.objects.create(
        model_name='inventory_delta',
        record_id=record_id,
        purpose='inventory_delta',
        name=f"Inventory delta for item {item_id}",
        data=data
    )

    # Process immediately if requested
    if process_immediately:
        process_inventory_deltas_immediately([item_id])

    return pending


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
                data__item_id__in=item_ids
            ).select_for_update()

            # Group by item
            item_deltas = {}
            for delta in deltas:
                item_id = delta.data.get('item_id')
                if item_id not in item_deltas:
                    item_deltas[item_id] = []
                item_deltas[item_id].append(delta)

            # Process each item
            for item_id, item_deltas_list in item_deltas.items():
                try:
                    item = Item.objects.select_for_update().get(pk=item_id)

                    # Calculate total changes
                    on_hand_change = sum(Decimal(str(d.data.get('quantity_on_hand_delta', 0))) for d in item_deltas_list)
                    on_order_change = sum(Decimal(str(d.data.get('quantity_on_order_delta', 0))) for d in item_deltas_list)
                    on_po_change = sum(Decimal(str(d.data.get('quantity_on_po_delta', 0))) for d in item_deltas_list)

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
        data=data
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

    data = delta.data or {}

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
        'sales_order_line', 'purchase_order_line', 'invoice_line',
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
            data__item_id=item_id
        ).aggregate(
            on_hand_sum=Sum('data__quantity_on_hand_delta'),
            on_order_sum=Sum('data__quantity_on_order_delta'),
            on_po_sum=Sum('data__quantity_on_po_delta')
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
    'reserve_inventory_for_order',
    'release_inventory_on_invoice',
    'cancel_order_inventory_reservations',
    'create_inventory_deltas_for_order',
    'create_inventory_deltas_for_purchase_order',
    '_create_inventory_delta',
    'process_inventory_deltas_immediately',
    'validate_inventory_delta',
    'audit_inventory_consistency',
    'InventoryFlowError',
]