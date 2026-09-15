"""
Inventory Event Emitter — Captures structured events for LLM observational learning.

This service is called from signals or service layer after inventory-affecting
operations to log events that the LLM can use to learn patterns and provide
intelligent assistance.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def is_inventory_events_enabled() -> bool:
    """Check if inventory event logging is enabled."""
    return getattr(settings, 'INVENTORY_EVENTS_ENABLED', True)


class InventoryEventEmitter:
    """
    Emits structured events for LLM observational learning.
    Called from signals or service layer after inventory-affecting operations.
    """
    
    @classmethod
    def emit(
        cls,
        category: str,
        event_type: str,
        item_id: int | None = None,
        *,
        user=None,
        transaction_type: str = '',
        transaction_id: int | None = None,
        transaction_ida: str = '',
        line_id: int | None = None,
        quantity_before: Decimal | float | None = None,
        quantity_after: Decimal | float | None = None,
        unit_cost: Decimal | float | None = None,
        unit_price: Decimal | float | None = None,
        customer_id: int | None = None,
        customer_name: str = '',
        vendor_id: int | None = None,
        vendor_name: str = '',
        reason: str = '',
        tags: list | None = None,
        payload: dict | None = None,
    ) -> Optional[Any]:  # Returns InventoryEvent or None
        """
        Create an inventory event with enriched context.
        
        Args:
            category: Event category (transaction, adjustment, alert, etc.)
            event_type: Specific event type (order_line_add, below_reorder, etc.)
            item_id: ID of the item affected
            user: Django user object (None for system events)
            transaction_type: Type of transaction (order, invoice, purchase, etc.)
            transaction_id: ID of the parent transaction
            transaction_ida: Human-readable transaction ID (SO-1234, etc.)
            line_id: ID of the specific line
            quantity_before: Quantity before the change
            quantity_after: Quantity after the change
            unit_cost: Item unit cost
            unit_price: Item unit price
            customer_id: Related customer ID
            customer_name: Related customer name
            vendor_id: Related vendor ID
            vendor_name: Related vendor name
            reason: Human-provided or inferred reason for the change
            tags: List of semantic tags for categorization
            payload: Raw JSON payload with additional details
            
        Returns:
            InventoryEvent instance or None if events are disabled
        """
        if not is_inventory_events_enabled():
            return None
        
        # Import here to avoid circular imports
        from apps.ai_assistant.models import InventoryEvent
        
        try:
            # Fetch item for enrichment if available
            item_data = {}
            qty_buckets = {}
            if item_id:
                try:
                    from apps.products.models import Item
                    item = Item.objects.filter(id=item_id).only('data').first()
                    if item and item.data:
                        item_data = item.data
                        qty_buckets = item_data.get('quantity', {})
                except Exception as e:
                    logger.debug(f"Could not fetch item {item_id}: {e}")
            
            # Compute delta
            delta = None
            if quantity_before is not None and quantity_after is not None:
                delta = Decimal(str(quantity_after)) - Decimal(str(quantity_before))
            
            event = InventoryEvent.objects.create(
                category=category,
                event_type=event_type,
                
                # Actor
                user_id=user.id if user else None,
                user_name=getattr(user, 'display_name', None) or (str(user) if user else ''),
                is_system=user is None,
                
                # Subject
                item_id=item_id,
                item_code=item_data.get('ida', ''),
                item_description=(
                    item_data.get('description', {}).get('en', '')
                    if isinstance(item_data.get('description'), dict)
                    else item_data.get('description', '')
                ),
                
                # Context
                transaction_type=transaction_type,
                transaction_id=transaction_id,
                transaction_ida=transaction_ida,
                line_id=line_id,
                customer_id=customer_id,
                customer_name=customer_name,
                vendor_id=vendor_id,
                vendor_name=vendor_name,
                
                # Quantities
                quantity_before=Decimal(str(quantity_before)) if quantity_before is not None else None,
                quantity_after=Decimal(str(quantity_after)) if quantity_after is not None else None,
                quantity_delta=delta,
                unit_cost=Decimal(str(unit_cost)) if unit_cost is not None else None,
                unit_price=Decimal(str(unit_price)) if unit_price is not None else None,
                
                # Buckets
                on_hand=qty_buckets.get('on_hand'),
                on_order=qty_buckets.get('on_so'),
                on_purchase=qty_buckets.get('on_po'),
                available=qty_buckets.get('available'),
                reorder_point=qty_buckets.get('reorder_point'),
                
                # Semantic
                reason=reason,
                tags=tags or [],
                payload=payload or {},
            )
            
            # Process with LLM immediately (Phase 2+)
            cls._process_with_llm(event)
            
            # Check for alerts (Phase 3)
            cls._check_alerts(event, qty_buckets)
            
            return event
            
        except Exception as e:
            logger.error(f"Failed to emit inventory event: {e}", exc_info=True)
            return None
    
    @classmethod
    def emit_line_event(
        cls,
        event_type: str,
        line,
        transaction,
        *,
        user=None,
        quantity_before: Decimal | float | None = None,
        reason: str = '',
    ):
        """
        Convenience method for transaction line events.
        
        Args:
            event_type: Event type (order_line_add, invoice_line_update, etc.)
            line: The transaction line instance
            transaction: The parent transaction instance
            user: Django user object
            quantity_before: Previous quantity (for updates)
            reason: Reason for the change
        """
        item = getattr(line, 'item', {}) or {}
        item_id = item.get('id_num') or item.get('id') or item.get('item_id')
        
        qty = getattr(line, 'quantity', {}) or {}
        quantity_after = qty.get('staged', 0) or qty.get('active', 0) or 0
        
        price = getattr(line, 'price', {}) or {}
        cost = getattr(line, 'cost', {}) or {}
        
        # Build payload with line and transaction context
        payload = {
            'line': {
                'id': line.id,
                'line_number': getattr(line, 'line_number', None),
                'quantity': qty,
                'price': price,
                'cost': cost,
            },
            'transaction': {
                'id': transaction.id,
                'ida': getattr(transaction, 'ida', ''),
                'status': getattr(transaction, 'status', ''),
            }
        }
        
        # Add customer/vendor if available
        customer_id = None
        customer_name = ''
        vendor_id = None
        vendor_name = ''
        
        if hasattr(transaction, 'customer_id') and transaction.customer_id:
            customer_id = transaction.customer_id
            customer_name = getattr(transaction, 'customer_name', '')
            payload['customer'] = {'id': customer_id, 'name': customer_name}
        
        if hasattr(transaction, 'vendor_id') and transaction.vendor_id:
            vendor_id = transaction.vendor_id
            vendor_name = getattr(transaction, 'vendor_name', '')
            payload['vendor'] = {'id': vendor_id, 'name': vendor_name}
        
        return cls.emit(
            category='transaction',
            event_type=event_type,
            item_id=item_id,
            user=user,
            transaction_type=transaction._meta.model_name,
            transaction_id=transaction.id,
            transaction_ida=getattr(transaction, 'ida', ''),
            line_id=line.id,
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            unit_cost=cost.get('unit'),
            unit_price=price.get('unit'),
            customer_id=customer_id,
            customer_name=customer_name,
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            reason=reason,
            payload=payload,
        )
    
    @classmethod
    def _process_with_llm(cls, event) -> None:
        """
        Generate LLM summary for the event (Phase 2).
        Runs synchronously for small volume - can be made async later.
        """
        try:
            from apps.ai_assistant.services.llm_observer import LLMInventoryObserver
            observer = LLMInventoryObserver()
            summary = observer.summarize_event(event)
            
            if summary:
                event.llm_summary = summary
                event.llm_processed_at = timezone.now()
                event.save(update_fields=['llm_summary', 'llm_processed_at'])
                
        except Exception as e:
            logger.debug(f"LLM processing skipped: {e}")
    
    @classmethod
    def _check_alerts(cls, event, qty_buckets: dict) -> None:
        """
        Check for inventory alerts based on the event (Phase 3).
        Creates additional alert events if thresholds are crossed.
        """
        if not qty_buckets:
            return
        
        on_hand = qty_buckets.get('on_hand')
        reorder_point = qty_buckets.get('reorder_point')
        safety_stock = qty_buckets.get('safety_stock')
        
        if on_hand is None:
            return
        
        # Only trigger alerts for quantity-decreasing events
        if event.quantity_delta is None or event.quantity_delta >= 0:
            return
        
        # Check reorder point
        if reorder_point and on_hand < reorder_point:
            # Check if we just crossed the threshold
            prev_on_hand = on_hand - event.quantity_delta
            if prev_on_hand >= reorder_point:
                cls.emit(
                    category='alert',
                    event_type='below_reorder',
                    item_id=event.item_id,
                    quantity_before=prev_on_hand,
                    quantity_after=on_hand,
                    reason=f"Dropped below reorder point ({reorder_point}) due to {event.event_type}",
                    tags=['reorder_needed', 'auto_detected'],
                    payload={
                        'triggered_by_event_id': str(event.event_id),
                        'threshold': float(reorder_point),
                    }
                )
        
        # Check safety stock
        if safety_stock and on_hand < safety_stock:
            prev_on_hand = on_hand - event.quantity_delta
            if prev_on_hand >= safety_stock:
                cls.emit(
                    category='alert',
                    event_type='below_safety',
                    item_id=event.item_id,
                    quantity_before=prev_on_hand,
                    quantity_after=on_hand,
                    reason=f"Dropped below safety stock ({safety_stock}) due to {event.event_type}",
                    tags=['critical', 'stockout_risk', 'auto_detected'],
                    payload={
                        'triggered_by_event_id': str(event.event_id),
                        'threshold': float(safety_stock),
                    }
                )
