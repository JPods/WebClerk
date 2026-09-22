"""
Line Item Service - Single Point of Authority for transaction line management.

Handles adding, updating, and managing transaction line items across all
transaction types (order, quote, invoice, purchase, workorder).

Includes deferred inventory adjustment via Pending records to reduce lock contention
on Item records. When quantity changes occur, a Pending record is created instead of
directly modifying the Item. A background process applies these changes when the
Item record is not locked.

Usage:
    from apps.transactions.services.line_manage import LineItemService
    
    service = LineItemService()
    line = service.add_item_to_transaction(transaction, item_id=123, quantity=5)
    
    # With pending inventory disabled (for imports/testing):
    service = LineItemService(create_pending=False)
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
import logging

from django.db import transaction as db_transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.products.models import Item
from apps.core.models import Pending
from apps.transactions.models.base_line_model import (
    default_item,
    default_quantity,
    default_price,
    default_cost,
    normalize_price_map,
    normalize_cost_map,
    _normalize_line_kind,
    forecast_probability,
    quantity_bucket_deltas,
)

# Import trace debugging utilities
from apps.transactions.services.trace_debug import (
    trace_line_add,
    trace_pending_created,
    should_trace,
)

if TYPE_CHECKING:
    from apps.transactions.models import (
        OrderLine,
        QuoteLine,
        InvoiceLine,
        PurchaseLine,
        WorkOrderLine,
    )

logger = logging.getLogger(__name__)



def _get_line_model(transaction_type: str):
    """Get the line model class for a transaction type.

    Derives the line model from the model registry using the canonical
    '{type}_line' key. No hardcoded mapping — single source of truth.
    """
    from apps.core.constants.model_registry import get_model_meta

    kind = _normalize_line_kind(transaction_type)
    line_key = f'{kind}_line'
    meta = get_model_meta(line_key)
    if not meta:
        raise ValueError(f"Unknown transaction type: {transaction_type}")
    return meta.import_model()


def _get_line_fk_field(line_model) -> str:
    """Discover the FK field name on a line model that points to its parent header.

    Uses Django model introspection — no hardcoded mapping needed.
    Falls back to the parent header's model_name if introspection fails.
    """
    from django.db.models import ForeignKey

    # The class is TransactionBaseModel. This imported BaseTransactionModel,
    # which does not exist, so the ImportError fired before the fallback below
    # could ever run and took the whole line-add path with it. Import errors
    # are caught here so the documented fallback is actually reachable.
    try:
        from apps.transactions.models.base_transaction_model import TransactionBaseModel

        for f in line_model._meta.get_fields():
            if isinstance(f, ForeignKey) and issubclass(f.related_model, TransactionBaseModel):
                return f.name
    except ImportError:
        logger.warning(
            'TransactionBaseModel unavailable; falling back to name-derived FK '
            'for %s', line_model._meta.model_name,
        )

    # Fallback: strip 'line' suffix from model name (e.g. 'orderline' -> 'order')
    model_name = line_model._meta.model_name.lower()
    return model_name.replace('line', '')


def _is_sales_transaction(transaction_type: str) -> bool:
    """Determine if a transaction type is sales-side (uses price) vs exec-side (uses cost).

    Delegates to the single source of truth: totals.is_sell_side().
    """
    from apps.transactions.services.pricing.totals_compute import is_sell_side
    return is_sell_side(transaction_type)


def _is_exec_transaction(transaction_type: str) -> bool:
    """Determine if a transaction type is execution-side (uses cost)."""
    kind = _normalize_line_kind(transaction_type)
    return kind in ('purchase', 'workorder')


# -----------------------------------------------------------------------------
# Pending Inventory Type Codes (mirrors WebClerk2 DInventory.typeID)
# -----------------------------------------------------------------------------
PENDING_TYPE_MAP = {
    'order': 'SO',
    'quote': 'QT',  # Quotes don't affect inventory until converted
    'invoice': 'IN',
    'receipt': 'RC',
    'purchase': 'PO',
    'workorder': 'WO',
}

# Purposes for pending records
PURPOSE_LINE_ADD = 'inventory_line_add'
PURPOSE_LINE_QTY_CHANGE = 'inventory_qty_change'
PURPOSE_LINE_DELETE = 'inventory_line_delete'
PURPOSE_LINE_COST_CHANGE = 'inventory_cost_change'


def _get_pending_type(transaction_type: str) -> str:
    """Get the pending type code for a transaction type."""
    key = transaction_type.lower().replace('-', '_')
    return PENDING_TYPE_MAP.get(key, 'XX')


def _line_item_id(line) -> int | None:
    """The item a line moves: the FK first, then the item JSON's id_num / id / item_id.

    The quantity-change and delete builders read only item.item_id, so a line whose
    JSON carried id_num wrote a Pending with no record_id — it could never apply, and
    the bucket it should have released stayed committed (11 such deletes in wc_demo).
    """
    fk_id = getattr(line, 'item_fk_id', None)
    if fk_id:
        return fk_id
    item = line.item if isinstance(getattr(line, 'item', None), dict) else {}
    return item.get('id_num') or item.get('id') or item.get('item_id') or getattr(line, 'item_id', None)


def _receipt_layer(line, receipt, *, create: bool) -> dict:
    """What a receipt pending does to the layer, carried in the pending itself.

    Bill, 2026-09-21: "Layers must change with items." The applier moves the layer by
    the pending's on_hand in the same transaction that moves the item, and the pending
    is processed only when both are saved. A new line creates its layer; a change or a
    delete moves the layer the line already has.
    """
    layer_id = getattr(line, 'inventory_layer_id', None)
    if layer_id and not create:
        return {'layer_id': layer_id}
    warehouse_id = getattr(line, 'warehouse_id', None)
    if not warehouse_id:
        raise ValidationError({'warehouse': f'receipt line {line.pk} has no warehouse — '
                                            'received goods must land in a layer'})
    cost = line.cost if isinstance(line.cost, dict) else {}
    return {
        'line_id': line.pk,
        'create': {
            'warehouse_id': warehouse_id,
            'lot': getattr(line, 'lot', '') or '',
            'serial_batch': getattr(line, 'serial_batch', '') or '',
            'unit_cost': float(cost.get('unit') or 0),
            'source_doc_type': getattr(receipt, 'source_type', '') or 'purchase_receipt',
            'source_doc_id': receipt.pk,
        },
    }


def _should_track_inventory(transaction_type: str) -> bool:
    """
    Determine if a transaction type should create pending inventory records.
    
    Quotes track on_qt (forecast bucket) - qty times probability.
    Sales Orders reserve inventory (qtyOnSO).
    Invoices issue inventory (qtyOnHand decreases).
    Purchase Orders reserve incoming (qtyOnPO).
    Work Orders reserve for production (qtyOnWO).
    """
    kind = _normalize_line_kind(transaction_type)
    # All transaction types track inventory (including quotes for forecast)
    return True


def _is_quote(transaction_type: str) -> bool:
    """Check if transaction type is a quote (tracks on_qt forecast bucket)."""
    kind = _normalize_line_kind(transaction_type)
    return kind == 'quote'


class LineItemService:
    """
    Single Point of Authority for managing transaction line items.
    
    Supports both sales transactions (quote, order, invoice) 
    and purchase transactions (purchase, workorder).
    
    Key behaviors:
    - Sales transactions: price.unit is the primary value
    - Purchase transactions: cost.unit is the primary value
    - Quantity changes create Pending records for deferred inventory updates
    
    Pending Record Flow:
    1. Line added → Pending record with purpose='inventory_line_add'
    2. Quantity changed → Pending record with purpose='inventory_qty_change' (delta)
    3. Line deleted → Pending record with purpose='inventory_line_delete' (negative)
    4. Background processor applies changes to Item when not locked
    """
    
    def __init__(self, create_pending: bool = True):
        """
        Initialize the LineItemService.
        
        Args:
            create_pending: If True, creates Pending records for inventory changes.
                           Set to False for imports, testing, or when you'll handle
                           inventory updates separately.
        """
        self.create_pending = create_pending
    
    def add_item_to_transaction(
        self,
        transaction,
        item_id: int,
        quantity: Union[int, float, Decimal] = 1,
        unit_price: Optional[Union[float, Decimal]] = None,
        unit_cost: Optional[Union[float, Decimal]] = None,
        price_level: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Add an item to a transaction as a new line.
        
        Args:
            transaction: The parent transaction (Order, Quote, Invoice, Purchase, WorkOrder)
            item_id: ID of the item to add
            quantity: Quantity to order (default: 1)
            unit_price: Override unit price (if None, uses item's default price)
            unit_cost: Override unit cost (if None, uses item's default cost)
            price_level: Price level to use for pricing lookup
            **kwargs: Additional fields to set on the line
            
        Returns:
            The created line instance
            
        Raises:
            ValidationError: If item not found or invalid parameters
        """
        # Get the item
        try:
            item = Item.objects.get(pk=item_id)
        except Item.DoesNotExist:
            raise ValidationError(f"Item with ID {item_id} not found")
        
        # Determine transaction type
        transaction_type = getattr(transaction, 'model_name', None) or transaction._meta.model_name
        
        # Get the appropriate line model
        LineModel = _get_line_model(transaction_type)
        
        # Build the item JSON envelope
        item_data = self._build_item_envelope(item)
        
        # Build quantity envelope
        quantity_data = self._build_quantity_envelope(transaction_type, quantity)
        
        # Build price envelope (for sales transactions)
        price_data = None
        if _is_sales_transaction(transaction_type):
            price_data = self._build_price_envelope(
                item, 
                quantity=quantity, 
                unit_price=unit_price,
                price_level=price_level or getattr(transaction, 'price_level', None)
            )
        
        # Build cost envelope
        cost_data = self._build_cost_envelope(
            item, 
            quantity=quantity, 
            unit_cost=unit_cost,
            is_primary=_is_exec_transaction(transaction_type)
        )
        
        # Determine next line number
        next_line_number = self._get_next_line_number(transaction)
        item_data['line_number'] = next_line_number
        item_data['sequence'] = next_line_number
        
        # Determine the correct FK field name for this line model
        fk_field = _get_line_fk_field(LineModel)
        
        # Create the line
        line_kwargs = {
            fk_field: transaction,
            'item': item_data,
            'quantity': quantity_data,
            'cost': cost_data,
            'price_level': price_level or getattr(transaction, 'price_level', None),
        }
        
        # Add price for sell-side transactions
        if price_data:
            line_kwargs['price'] = price_data
        
        # Merge any additional kwargs
        line_kwargs.update(kwargs)
        
        line = LineModel(**line_kwargs)
        
        line.save()        # the line's own door writes the Pending (line_door.post_line_change)
        
        # TRACE: Line added
        trace_line_add(
            transaction_type=transaction_type,
            transaction_pk=transaction.pk,
            transaction_ida=getattr(transaction, 'ida', '') or str(transaction.pk),
            item_id=item.pk,
            item_ida=item.ida or item.sku or item.name,
            quantity=float(quantity),
            unit_price=price_data.get('unit', 0) if price_data else 0,
            unit_cost=cost_data.get('unit', 0),
            line_pk=line.pk,
        )
        
        return line
    
    def add_item_from_search_result(
        self,
        transaction,
        search_result: Dict[str, Any],
        quantity: Union[int, float, Decimal] = 1,
        **kwargs
    ) -> Any:
        """
        Add an item from a search result dictionary.
        
        This is useful when adding items from the frontend search component
        where you have a dict with various field naming conventions.
        
        Args:
            transaction: The parent transaction
            search_result: Dict containing item data (supports multiple field naming conventions)
            quantity: Quantity to order
            **kwargs: Additional fields to set on the line
            
        Returns:
            The created line instance
        """
        # Extract item ID from various possible field names
        item_id = (
            search_result.get('item_id') or 
            search_result.get('id') or 
            search_result.get('itemId')
        )
        
        if not item_id:
            raise ValidationError("Item ID not found in search result")
        
        # Extract price/cost overrides if provided
        unit_price = self._extract_price_from_search(search_result)
        unit_cost = self._extract_cost_from_search(search_result)
        
        return self.add_item_to_transaction(
            transaction=transaction,
            item_id=item_id,
            quantity=quantity,
            unit_price=unit_price,
            unit_cost=unit_cost,
            **kwargs
        )
    
    def update_line(
        self,
        line,
        updates: Dict[str, Any]
    ) -> Any:
        """
        Update a transaction line.
        
        Args:
            line: The line instance to update
            updates: Dict of field updates. Supports nested paths like 'quantity.staged'
            
        Returns:
            The updated line instance
        """
        for field, value in updates.items():
            if '.' in field:
                # Handle nested updates like 'quantity.staged' or 'price.unit'
                parts = field.split('.')
                obj = getattr(line, parts[0], {}) or {}
                if isinstance(obj, dict):
                    obj[parts[1]] = value
                    setattr(line, parts[0], obj)
            else:
                setattr(line, field, value)
        
        # Recalculate extended values
        self._recalculate_line(line)
        
        line.save()
        return line
    
    def update_quantity(
        self,
        line,
        quantity: Union[int, float, Decimal]
    ) -> Any:
        """
        Update the quantity on a line and recalculate extensions.
        
        All types use the same logic:
          active = new qty (the user input).
          Standalone (no parent): staged = active.
          Transferred (has parent): staged unchanged.
          remaining = active − children_active.sum (or just active if no children).
        
        Creates a Pending record with the quantity delta for deferred
        inventory adjustment.
        
        Args:
            line: The line to update
            quantity: New quantity value
            
        Returns:
            The updated line
        """
        # What the bucket holds is what this line still commits — its remaining, not its
        # active (Bill, 2026-09-19). With children unchanged the two deltas are equal;
        # the difference is that measuring remaining shows when an edit takes a line
        # below what has already moved downstream, instead of silently pushing the
        # bucket negative.
        from apps.transactions.services import line_parent as _line_parent

        old_quantity = 0
        if isinstance(line.quantity, dict):
            old_quantity = float(line.quantity.get('active', 0) or 0)

        new_quantity = float(quantity)
        consumed = float(_line_parent.children_active_sum(line) or 0)
        old_remaining = old_quantity - consumed
        new_remaining = new_quantity - consumed
        quantity_delta = new_remaining - old_remaining
        if new_remaining < 0:
            logger.warning(
                "[line_manage] %s line %s set to %s while %s has already moved downstream — "
                "remaining goes to %s. The commitment bucket follows the document; fix the "
                "document (convert less, or close it) rather than the bucket.",
                line._meta.model_name, line.pk, new_quantity, consumed, new_remaining,
            )
        
        if not isinstance(line.quantity, dict):
            line.quantity = {}
        
        # active IS the user input
        line.quantity['active'] = new_quantity
        
        transaction = line.parent
        transaction_type = getattr(transaction, 'model_name', None) or transaction._meta.model_name

        # staged is the creation snapshot and remaining is computed on save
        # (normalize_quantity_map). Neither is written here.

        self._recalculate_line(line)
        line.save()
        
        return line
    
    def update_price(
        self,
        line,
        unit_price: Union[float, Decimal]
    ) -> Any:
        """
        Update the unit price on a line and recalculate extensions.
        
        Only applicable to sales transactions.
        
        Args:
            line: The line to update
            unit_price: New unit price
            
        Returns:
            The updated line
        """
        if not hasattr(line, 'price'):
            raise ValidationError("Cannot update price on execution-side transactions")
        
        if not isinstance(line.price, dict):
            line.price = default_price()
        
        line.price['unit'] = float(unit_price)
        self._recalculate_line(line)
        line.save()
        return line
    
    def update_cost(
        self,
        line,
        unit_cost: Union[float, Decimal]
    ) -> Any:
        """
        Update the unit cost on a line and recalculate extensions.
        
        Args:
            line: The line to update
            unit_cost: New unit cost
            
        Returns:
            The updated line
        """
        if not isinstance(line.cost, dict):
            line.cost = default_cost()
        
        line.cost['unit'] = float(unit_cost)
        self._recalculate_line(line)
        line.save()
        return line
    
    def apply_discount(
        self,
        line,
        discount_percent: Optional[float] = None,
        discount_amount: Optional[float] = None
    ) -> Any:
        """
        Apply a discount to a line.
        
        Args:
            line: The line to update
            discount_percent: Percentage discount (0-100)
            discount_amount: Fixed amount discount
            
        Returns:
            The updated line
        """
        if hasattr(line, 'price') and isinstance(line.price, dict):
            if discount_percent is not None:
                line.price['discount_percent'] = float(discount_percent)
                # Calculate amount from percent
                unit = line.price.get('unit', 0)
                qty = (line.quantity.get('active', 0)) if isinstance(line.quantity, dict) else 0
                line.price['discount_amount'] = float(unit * qty * discount_percent / 100)
            elif discount_amount is not None:
                line.price['discount_amount'] = float(discount_amount)
        
        self._recalculate_line(line)
        line.save()
        return line
    
    def delete_line(self, line) -> None:
        """Delete a transaction line outright. Lines have no soft delete (Bill, 2026-09-22).

        The line's post_delete signal writes the Pending that releases what it held,
        the same door an add or a change goes through; this method writes none of its own.
        """
        line.delete()

    def duplicate_line(
        self,
        line,
        quantity: Optional[Union[int, float, Decimal]] = None
    ) -> Any:
        """
        Duplicate an existing line.
        
        Args:
            line: The line to duplicate
            quantity: Optional new quantity (defaults to original)
            
        Returns:
            The new duplicated line
        """
        # Get parent transaction
        transaction = line.parent
        
        # Get next line number
        next_line_number = self._get_next_line_number(transaction)
        
        # Clone the line data
        new_line = line.__class__()
        for field in line._meta.fields:
            if field.name not in ('id', 'pk', 'created_at', 'updated_at'):
                setattr(new_line, field.name, getattr(line, field.name))
        
        # Update line number
        if isinstance(new_line.item, dict):
            new_line.item['line_number'] = next_line_number
            new_line.item['sequence'] = next_line_number
        
        # Update quantity if provided
        if quantity is not None and isinstance(new_line.quantity, dict):
            new_line.quantity['staged'] = float(quantity)
            new_line.quantity['active'] = float(quantity)
            self._recalculate_line(new_line)
        
        new_line.pk = None
        new_line.id = None
        new_line.save()
        
        return new_line
    
    def validate_item_change(
        self,
        line,
        new_item_id: int
    ) -> None:
        """
        Validate that changing an item on an existing line is allowed.
        
        Per system rules, item_id cannot be changed on existing lines.
        
        Args:
            line: The existing line
            new_item_id: The proposed new item ID
            
        Raises:
            ValidationError: If item change is not allowed
        """
        if line.pk is None:
            # New line, item can be set
            return
        
        current_item_id = None
        if isinstance(line.item, dict):
            current_item_id = line.item.get('item_id')
        
        if current_item_id and current_item_id != new_item_id:
            raise ValidationError(
                "Item cannot be changed on existing lines. "
                "Please delete this line and add a new line with the correct item."
            )
    
    def get_lines_for_transaction(self, transaction) -> List[Any]:
        """Every line on a transaction. A deleted line is gone, so there is nothing to filter."""
        return list(transaction.lines.all())
    
    def calculate_line(
        self,
        line
    ) -> Any:
        """
        Recalculate a line's extended values without saving.
        
        Args:
            line: The line to calculate
            
        Returns:
            The line with updated calculations
        """
        self._recalculate_line(line)
        return line
    
    # -------------------------------------------------------------------------
    # Private helper methods
    # -------------------------------------------------------------------------
    
    def _build_item_envelope(self, item: Item) -> Dict[str, Any]:
        """Build the item JSON envelope from an Item model."""
        envelope = default_item()
        envelope['item_id'] = item.pk
        envelope['ida_item'] = getattr(item, 'ida', '') or getattr(item, 'item_code', '') or ''
        envelope['uuid_item'] = str(getattr(item, 'uuid', '')) if hasattr(item, 'uuid') else ''
        envelope['description'] = getattr(item, 'description', '') or ''
        envelope['description_text'] = getattr(item, 'description_text', '') or envelope['description']
        uom_raw = getattr(item, 'unit_of_measure', '') or 'EA'
        envelope['unit_measure'] = uom_raw
        # Compute UOM divisor for pricing (e.g., DZ=12 means price per dozen)
        from apps.products.uom import to_base_factor, get_category
        uom_factor = to_base_factor(uom_raw)
        if uom_factor and get_category(uom_raw) == 'count' and uom_factor != 1.0:
            envelope['uom_divisor'] = uom_factor
        else:
            envelope['uom_divisor'] = 1.0
        
        # Include item's quantity defaults for reference
        item_record = getattr(item, 'record', {}) or {}
        if isinstance(item_record, dict) and 'quantity' in item_record:
            envelope['quantity'] = item_record['quantity']
        
        # Include item's price and cost for reference
        if isinstance(item_record, dict):
            if 'price' in item_record:
                envelope['price'] = item_record['price']
            if 'cost' in item_record:
                envelope['cost'] = item_record['cost']
        
        return envelope
    
    def _build_quantity_envelope(
        self,
        transaction_type: str,
        quantity: Union[int, float, Decimal]
    ) -> Dict[str, Any]:
        """Build the quantity JSON envelope.

        All types use the same logic:
          active = quantity (user input), staged = quantity, remaining = quantity.
          normalize_quantity_map() handles transferred vs standalone on save.
        """
        envelope = default_quantity(transaction_type)
        qty = float(quantity)
        envelope['active'] = qty
        envelope['staged'] = qty
        envelope['remaining'] = qty
        return envelope
    
    def _build_price_envelope(
        self,
        item: Item,
        quantity: Union[int, float, Decimal],
        unit_price: Optional[Union[float, Decimal]] = None,
        price_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build the price JSON envelope for sales transactions."""
        envelope = default_price()
        
        # Determine unit price
        if unit_price is not None:
            envelope['unit'] = float(unit_price)
            envelope['unit_base'] = float(unit_price)
        else:
            # Get from item
            item_record = getattr(item, 'record', {}) or {}
            item_price = item_record.get('price', {}) if isinstance(item_record, dict) else {}
            
            # Check price level tiers first
            if price_level and isinstance(item_price, dict):
                tiers = item_price.get('tiers', [])
                for tier in tiers:
                    if isinstance(tier, dict) and tier.get('level') == price_level:
                        tier_price = tier.get('price')
                        if tier_price is not None:
                            envelope['unit'] = float(tier_price)
                            envelope['unit_base'] = float(item_price.get('base', tier_price))
                            break
            
            # Fall back to base price
            if envelope['unit'] == 0 and isinstance(item_price, dict):
                base_price = item_price.get('base', 0)
                envelope['unit'] = float(base_price)
                envelope['unit_base'] = float(base_price)
        
        # Calculate extended — apply UOM divisor for count-based units
        # e.g., if UOM is DZ (dozen), unit price is per dozen, qty is in dozens
        # The divisor adjusts unit price from per-each to per-UOM when the item's
        # base price is stored per-each but sold in multiples.
        envelope['amount'] = float(Decimal(str(quantity)) * Decimal(str(envelope['unit'])))

        return envelope

    def _build_cost_envelope(
        self,
        item: Item,
        quantity: Union[int, float, Decimal],
        unit_cost: Optional[Union[float, Decimal]] = None,
        is_primary: bool = False
    ) -> Dict[str, Any]:
        """Build the cost JSON envelope."""
        envelope = default_cost()
        
        # Determine unit cost
        if unit_cost is not None:
            envelope['unit'] = float(unit_cost)
            envelope['unit_base'] = float(unit_cost)
        else:
            # Get from item
            item_record = getattr(item, 'record', {}) or {}
            item_cost = item_record.get('cost', {}) if isinstance(item_record, dict) else {}
            
            if isinstance(item_cost, dict):
                # Try standard, last, avg in order
                for key in ('standard', 'last', 'avg'):
                    val = item_cost.get(key)
                    if val is not None and val != 0:
                        envelope['unit'] = float(val)
                        envelope['unit_base'] = float(val)
                        break
        
        # Calculate extended
        envelope['amount'] = float(Decimal(str(quantity)) * Decimal(str(envelope['unit'])))
        
        return envelope
    
    def _get_next_line_number(self, transaction) -> int:
        """Get the next available line number for a transaction."""
        existing_lines = transaction.lines.all()
        max_line_num = 0
        
        for line in existing_lines:
            if isinstance(line.item, dict):
                line_num = line.item.get('line_number', 0) or 0
                max_line_num = max(max_line_num, line_num)
        
        return max_line_num + 1
    
    def _recalculate_line(self, line) -> None:
        """Recalculate extended values on a line.

        Delegates to the model's ensure_json_defaults() which calls
        _calculate_extended_cost() (all lines) and _calculate_extended_price()
        (sell-side lines). Single source of truth — no independent computation.
        """
        line.ensure_json_defaults()
    
    def _extract_price_from_search(self, search_result: Dict[str, Any]) -> Optional[float]:
        """Extract unit price from a search result dict."""
        candidates = [
            search_result.get('unit_price'),
            search_result.get('price'),
            search_result.get('priceA'),
            search_result.get('price_a'),
        ]
        
        for candidate in candidates:
            if candidate is None:
                continue
            if isinstance(candidate, (int, float)):
                return float(candidate)
            if isinstance(candidate, str):
                try:
                    return float(candidate)
                except ValueError:
                    continue
            if isinstance(candidate, dict):
                # Handle nested price object
                for key in ('base', 'retail', 'sell', 'unit'):
                    val = candidate.get(key)
                    if val is not None:
                        try:
                            return float(val)
                        except (TypeError, ValueError):
                            continue
        
        return None
    
    def _extract_cost_from_search(self, search_result: Dict[str, Any]) -> Optional[float]:
        """Extract unit cost from a search result dict."""
        candidates = [
            search_result.get('unit_cost'),
            search_result.get('cost'),
            search_result.get('costA'),
        ]
        
        for candidate in candidates:
            if candidate is None:
                continue
            if isinstance(candidate, (int, float)):
                return float(candidate)
            if isinstance(candidate, str):
                try:
                    return float(candidate)
                except ValueError:
                    continue
            if isinstance(candidate, dict):
                # Handle nested cost object
                for key in ('avg', 'last', 'standard', 'unit'):
                    val = candidate.get(key)
                    if val is not None:
                        try:
                            return float(val)
                        except (TypeError, ValueError):
                            continue
        
        return None

    # -------------------------------------------------------------------------
    # Pending Inventory Methods
    # -------------------------------------------------------------------------

# Convenience function for single import
def add_item_to_transaction(transaction, item_id: int, quantity: int = 1, **kwargs):
    """Convenience function to add an item to a transaction."""
    service = LineItemService()
    return service.add_item_to_transaction(transaction, item_id, quantity, **kwargs)
