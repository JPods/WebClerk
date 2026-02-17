"""
Line Item Service - Single Point of Authority for transaction line management.

Handles adding, updating, and managing transaction line items across all
transaction types (order, proposal, invoice, purchase_order, work_order).

Includes deferred inventory adjustment via Pending records to reduce lock contention
on Item records. When quantity changes occur, a Pending record is created instead of
directly modifying the Item. A background process applies these changes when the
Item record is not locked.

Usage:
    from apps.transactions.services.line_item_service import LineItemService
    
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
        ProposalLine,
        InvoiceLine,
        PurchaseLine,
        WorkOrderLine,
    )

logger = logging.getLogger(__name__)


# Model mapping for dynamic line creation
LINE_MODEL_MAP = {
    'order': 'apps.transactions.models.OrderLine',
    'proposal': 'apps.transactions.models.ProposalLine',
    'invoice': 'apps.transactions.models.InvoiceLine',
    'purchase': 'apps.transactions.models.PurchaseLine',
    'purchase_order': 'apps.transactions.models.PurchaseLine',
    'purchaseorder': 'apps.transactions.models.PurchaseLine',
    'workorder': 'apps.transactions.models.WorkOrderLine',
    'receipt': 'apps.transactions.models.ReceiptLine',
}

# FK field names for each line model (the field pointing to the parent transaction)
# All line models now use consistent naming: order, proposal, invoice, purchase, workorder
LINE_FK_FIELD_MAP = {
    'orderline': 'order',
    'proposalline': 'proposal',
    'invoiceline': 'invoice',
    'purchaseline': 'purchase',
    'workorderline': 'workorder',
    'receiptline': 'receipt',
}


def _get_line_model(transaction_type: str):
    """Get the line model class for a transaction type."""
    from django.apps import apps
    
    key = transaction_type.lower().replace('-', '_')
    model_path = LINE_MODEL_MAP.get(key)
    if not model_path:
        raise ValueError(f"Unknown transaction type: {transaction_type}")
    
    app_label, model_name = model_path.rsplit('.', 1)
    # Extract just the app name from the full path
    app_name = app_label.split('.')[-1]  # 'apps.transactions.models' -> 'models' -> need 'transactions'
    app_name = 'transactions'
    return apps.get_model(app_name, model_name)


def _is_sales_transaction(transaction_type: str) -> bool:
    """Determine if a transaction type is sales-side (uses price) vs exec-side (uses cost)."""
    kind = _normalize_line_kind(transaction_type)
    return kind in ('proposal', 'order', 'invoice')


def _is_exec_transaction(transaction_type: str) -> bool:
    """Determine if a transaction type is execution-side (uses cost)."""
    kind = _normalize_line_kind(transaction_type)
    return kind in ('purchase', 'workorder')


# -----------------------------------------------------------------------------
# Pending Inventory Type Codes (mirrors WebClerk2 DInventory.typeID)
# -----------------------------------------------------------------------------
PENDING_TYPE_MAP = {
    'order': 'SO',
    'proposal': 'PP',  # Proposals don't affect inventory until converted
    'invoice': 'IN',
    'receipt': 'RC',
    'purchase': 'PO',
    'purchase_order': 'PO',
    'purchaseorder': 'PO',
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


def _should_track_inventory(transaction_type: str) -> bool:
    """
    Determine if a transaction type should create pending inventory records.
    
    Proposals track on_p (forecast bucket) - qty times probability.
    Sales Orders reserve inventory (qtyOnSO).
    Invoices issue inventory (qtyOnHand decreases).
    Purchase Orders reserve incoming (qtyOnPO).
    Work Orders reserve for production (qtyOnWO).
    """
    kind = _normalize_line_kind(transaction_type)
    # All transaction types track inventory (including proposals for forecast)
    return True


def _is_proposal(transaction_type: str) -> bool:
    """Check if transaction type is a proposal (tracks on_p forecast bucket)."""
    kind = _normalize_line_kind(transaction_type)
    return kind == 'proposal'


class LineItemService:
    """
    Single Point of Authority for managing transaction line items.
    
    Supports both sales transactions (proposal, order, invoice) 
    and purchase transactions (purchase_order, work_order).
    
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
            transaction: The parent transaction (Order, Proposal, Invoice, Purchase, WorkOrder)
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
        model_name = LineModel._meta.model_name.lower()
        fk_field = LINE_FK_FIELD_MAP.get(model_name, 'parent')
        
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
        
        # Mark line to prevent signal from creating duplicate pending
        if self.create_pending and _should_track_inventory(transaction_type):
            line._pending_created = True
        
        line.save()
        
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
        
        # Create pending inventory record for quantity tracking
        if self.create_pending and _should_track_inventory(transaction_type):
            self._create_pending_for_line_add(
                transaction=transaction,
                transaction_type=transaction_type,
                line=line,
                item=item,
                quantity=float(quantity),
                unit_cost=cost_data.get('unit', 0),
                unit_price=price_data.get('unit', 0) if price_data else 0,
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
            updates: Dict of field updates. Supports nested paths like 'quantity.placed'
            
        Returns:
            The updated line instance
        """
        for field, value in updates.items():
            if '.' in field:
                # Handle nested updates like 'quantity.placed' or 'price.unit'
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
        
        Creates a Pending record with the quantity delta for deferred
        inventory adjustment.
        
        Args:
            line: The line to update
            quantity: New quantity value
            
        Returns:
            The updated line
        """
        # Get old quantity for delta calculation
        old_quantity = 0
        if isinstance(line.quantity, dict):
            old_quantity = float(line.quantity.get('placed', 0) or 0)
        
        new_quantity = float(quantity)
        quantity_delta = new_quantity - old_quantity
        
        if not isinstance(line.quantity, dict):
            line.quantity = {}
        
        line.quantity['placed'] = new_quantity
        self._recalculate_line(line)
        line.save()
        
        # Create pending record for the quantity change delta
        if self.create_pending and quantity_delta != 0:
            transaction = line.parent
            transaction_type = getattr(transaction, 'model_name', None) or transaction._meta.model_name
            
            if _should_track_inventory(transaction_type):
                self._create_pending_for_qty_change(
                    transaction=transaction,
                    transaction_type=transaction_type,
                    line=line,
                    quantity_delta=quantity_delta,
                )
        
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
                qty = line.quantity.get('placed', 0) if isinstance(line.quantity, dict) else 0
                line.price['discount_amount'] = float(unit * qty * discount_percent / 100)
            elif discount_amount is not None:
                line.price['discount_amount'] = float(discount_amount)
        
        self._recalculate_line(line)
        line.save()
        return line
    
    def delete_line(
        self,
        line,
        soft: bool = True
    ) -> None:
        """
        Delete a transaction line.
        
        Creates a Pending record to release reserved inventory.
        
        Args:
            line: The line to delete
            soft: If True, marks as deleted. If False, hard deletes.
        """
        # Get current quantity to release
        current_quantity = 0
        if isinstance(line.quantity, dict):
            current_quantity = float(line.quantity.get('placed', 0) or 0)
        
        # Create pending record to release inventory before modifying line
        if self.create_pending and current_quantity > 0:
            transaction = line.parent
            transaction_type = getattr(transaction, 'model_name', None) or transaction._meta.model_name
            
            if _should_track_inventory(transaction_type):
                self._create_pending_for_line_delete(
                    transaction=transaction,
                    transaction_type=transaction_type,
                    line=line,
                    quantity_released=current_quantity,
                )
        
        if soft:
            if isinstance(line.item, dict):
                line.item['is_deleted'] = True
                line.save()
            else:
                line.item = {'is_deleted': True}
                line.save()
        else:
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
            new_line.quantity['placed'] = float(quantity)
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
    
    def get_lines_for_transaction(
        self,
        transaction,
        include_deleted: bool = False
    ) -> List[Any]:
        """
        Get all lines for a transaction.
        
        Args:
            transaction: The parent transaction
            include_deleted: If True, includes soft-deleted lines
            
        Returns:
            List of line instances
        """
        lines = transaction.lines.all()
        
        if not include_deleted:
            # Filter out soft-deleted lines
            lines = [
                line for line in lines
                if not (isinstance(line.item, dict) and line.item.get('is_deleted'))
            ]
        
        return list(lines)
    
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
        envelope['unit_measure'] = getattr(item, 'unit_of_measure', '') or 'EA'
        
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
        """Build the quantity JSON envelope."""
        envelope = default_quantity(transaction_type)
        envelope['placed'] = float(quantity)
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
        
        # Calculate extended
        envelope['extended'] = float(Decimal(str(quantity)) * Decimal(str(envelope['unit'])))
        
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
        envelope['extended'] = float(Decimal(str(quantity)) * Decimal(str(envelope['unit'])))
        
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
        """Recalculate extended values on a line."""
        quantity = 0
        if isinstance(line.quantity, dict):
            quantity = line.quantity.get('placed', 0) or 0
        
        # Calculate price extended (for sell-side)
        if hasattr(line, 'price') and isinstance(line.price, dict):
            unit_price = line.price.get('unit', 0) or 0
            discount_amount = line.price.get('discount_amount', None)
            discount_percent = line.price.get('discount_percent', 0) or 0
            precision = line.price.get('precision', 2)
            gross = float(quantity) * float(unit_price)
            if discount_amount is None or (discount_amount == 0 and discount_percent):
                discount_amount = gross * float(discount_percent) / 100.0
            line.price['discount_amount'] = round(float(discount_amount or 0), precision)
            extended = round(gross - float(discount_amount or 0), precision)
            line.price['extended'] = extended

        # Calculate cost extended (includes cost discount)
        if isinstance(line.cost, dict):
            unit_cost = line.cost.get('unit', 0) or 0
            discount_cost_amount = line.cost.get('discount_amount', None)
            discount_cost_percent = line.cost.get('discount_percent', 0) or 0
            precision = line.cost.get('precision', 2)
            gross_cost = float(quantity) * float(unit_cost)
            if discount_cost_amount is None or (discount_cost_amount == 0 and discount_cost_percent):
                discount_cost_amount = gross_cost * float(discount_cost_percent) / 100.0
            line.cost['discount_amount'] = round(float(discount_cost_amount or 0), precision)
            extended_cost = round(gross_cost - float(discount_cost_amount or 0), precision)
            line.cost['extended'] = extended_cost
    
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

    def _create_pending_for_line_add(
        self,
        transaction,
        transaction_type: str,
        line,
        item: Item,
        quantity: float,
        unit_cost: float = 0,
        unit_price: float = 0,
    ) -> Pending:
        """
        Create a Pending record when a new line is added.
        
        This records the quantity reservation for later application to
        the Item record when it's not locked.
        
        Args:
            transaction: Parent transaction
            transaction_type: Type code (order, invoice, etc.)
            line: The created line
            item: The Item model
            quantity: Quantity being reserved/committed
            unit_cost: Unit cost at time of add
            unit_price: Unit price at time of add
            
        Returns:
            The created Pending record
        """
        pending_type = _get_pending_type(transaction_type)
        
        # Get probability from transaction for proposals (default to 100% = 1.0)
        probability = 1.0
        if pending_type == 'PP':
            # Try to get probability from transaction header
            prob_raw = getattr(transaction, 'probability', None)
            if prob_raw is None and hasattr(transaction, 'metadata') and isinstance(transaction.metadata, dict):
                prob_raw = transaction.metadata.get('probability')
            if prob_raw is not None:
                try:
                    probability = float(prob_raw) / 100.0 if float(prob_raw) > 1.0 else float(prob_raw)
                except (TypeError, ValueError):
                    probability = 1.0
        
        # Build pending data similar to WebClerk2 DInventory structure
        pending_data = {
            'type_id': pending_type,
            'item_num': item.ida or str(item.pk),
            'item_id': item.pk,
            'doc_id': getattr(transaction, 'ida', '') or str(transaction.pk),
            'doc_pk': transaction.pk,
            'line_id': line.pk,
            'line_num': line.item.get('line_number', 0) if isinstance(line.item, dict) else 0,
            
            # Quantity buckets - initialized to 0, set based on type below
            'on_so': 0,
            'on_po': 0,
            'on_wo': 0,
            'on_in': 0,
            'on_r': 0,
            'on_p': 0,
            'on_hand': 0,
            
            # Pricing snapshot
            'unit_cost': unit_cost,
            'unit_price': unit_price,
            
            # Audit
            'reason': f'{pending_type.lower()} line add',
            'take_action': 1,  # 1 = apply, matches WebClerk2
            'changed_by': '',  # Will be set by request context if available
            
            # Transaction reference
            'transaction_type': transaction_type,
            'transaction_model': transaction._meta.model_name,
            
            # Parent links (populated for child transactions)
            'links': {},
        }
        
        # Set quantity buckets based on pending type
        if pending_type == 'PP':
            pending_data['on_p'] = quantity * probability
        elif pending_type == 'SO':
            pending_data['on_so'] = quantity
        elif pending_type == 'PO':
            pending_data['on_po'] = quantity
        elif pending_type == 'WO':
            pending_data['on_wo'] = quantity
        elif pending_type == 'IN':
            # Invoice: track on_in, release on_so, deduct on_hand
            pending_data['on_in'] = quantity
            parent_id = getattr(transaction, 'parent_id', None)
            if parent_id:
                # Invoice from Order: release order commitment and deduct inventory
                pending_data['on_so'] = -quantity
                pending_data['on_hand'] = -quantity
                pending_data['links']['order'] = {'parent_id': parent_id}
                pending_data['reason'] = 'in line add (releases so, deducts on_hand)'
        elif pending_type == 'RC':
            # Receipt: track on_r, release source commitment, add on_hand
            pending_data['on_r'] = quantity
            # Check for purchase parent
            purchase_id = getattr(transaction, 'purchase_id', None)
            if purchase_id:
                pending_data['on_po'] = -quantity
                pending_data['on_hand'] = quantity
                pending_data['links']['purchase'] = {'parent_id': purchase_id}
                pending_data['reason'] = 'rc line add (releases po, adds on_hand)'
            else:
                # Check for workorder parent
                workorder_id = getattr(transaction, 'workorder_id', None)
                if workorder_id:
                    pending_data['on_wo'] = -quantity
                    pending_data['on_hand'] = quantity
                    pending_data['links']['workorder'] = {'parent_id': workorder_id}
                    pending_data['reason'] = 'rc line add (releases wo, adds on_hand)'
        
        pending = Pending.objects.create(
            model_name='item',
            record_id=str(item.pk),
            purpose=PURPOSE_LINE_ADD,
            name=f'{pending_type} Line Add: {item.ida or item.pk}',
            data=pending_data,
        )
        
        # TRACE: Pending created for line add
        trace_pending_created(
            purpose=PURPOSE_LINE_ADD,
            pending_pk=pending.pk,
            item_id=item.pk,
            item_ida=item.ida or item.sku or item.name,
            pending_type=pending_type,
            data=pending_data,
        )
        
        logger.debug(
            f"Created pending inventory record: {pending.pk} "
            f"for item {item.pk}, qty={quantity}, type={pending_type}"
        )
        
        return pending

    def _create_pending_for_new_line(
        self,
        parent,
        parent_model_key: str,
        line,
        line_data: dict,
    ) -> 'Pending':
        """
        Create a Pending record for a newly created line from save_view.py.
        
        This method bridges the save_view.py direct line creation with the
        inventory pending system. It extracts the item_id and quantity from
        the line_data and creates the appropriate pending record.
        
        Args:
            parent: The parent transaction object (Order, Proposal, etc.)
            parent_model_key: The model key ('order', 'proposal', etc.)
            line: The created line object
            line_data: The raw dict data used to create the line
            
        Returns:
            The created Pending record, or None if not applicable
        """
        # Normalize transaction type
        tx_type_map = {
            'order': 'order',
            'proposal': 'proposal',
            'quote': 'proposal',
            'invoice': 'invoice',
            'purchase': 'purchase',
            'purchaseorder': 'purchase',
            'workorder': 'workorder',
        }
        transaction_type = tx_type_map.get(parent_model_key.lower())
        
        if not transaction_type:
            logger.debug(f"_create_pending_for_new_line: No inventory tracking for {parent_model_key}")
            return None
        
        if not _should_track_inventory(transaction_type):
            return None
        
        # Extract item_id from line_data or line object
        item_id = None
        item_data = line_data.get('item', {}) or {}
        if isinstance(item_data, dict):
            item_id = item_data.get('id') or item_data.get('item_id')
        if not item_id and hasattr(line, 'item') and isinstance(line.item, dict):
            item_id = line.item.get('id') or line.item.get('item_id')
        if not item_id and hasattr(line, 'item_id'):
            item_id = line.item_id
        
        if not item_id:
            logger.debug(f"_create_pending_for_new_line: No item_id found for line {line.pk}")
            return None
        
        # Get the Item
        try:
            item = Item.objects.get(pk=item_id)
        except Item.DoesNotExist:
            logger.warning(f"_create_pending_for_new_line: Item {item_id} not found")
            return None
        
        # Extract quantity from line_data or line object
        quantity = 0
        qty_data = line_data.get('quantity', {}) or {}
        if isinstance(qty_data, dict):
            quantity = float(qty_data.get('placed', 0) or qty_data.get('ordered', 0) or 0)
        elif isinstance(qty_data, (int, float)):
            quantity = float(qty_data)
        if not quantity and hasattr(line, 'quantity') and isinstance(line.quantity, dict):
            quantity = float(line.quantity.get('placed', 0) or line.quantity.get('ordered', 0) or 0)
        
        if not quantity:
            logger.debug(f"_create_pending_for_new_line: Zero quantity for line {line.pk}")
            return None
        
        # Extract cost/price
        unit_cost = 0
        unit_price = 0
        cost_data = line_data.get('cost', {}) or {}
        if isinstance(cost_data, dict):
            unit_cost = float(cost_data.get('unit', 0) or 0)
        price_data = line_data.get('price', {}) or {}
        if isinstance(price_data, dict):
            unit_price = float(price_data.get('unit', 0) or 0)
        
        # Mark line as having pending created (prevents signal from duplicating)
        line._pending_created = True
        
        # Create the pending record using existing method
        return self._create_pending_for_line_add(
            transaction=parent,
            transaction_type=transaction_type,
            line=line,
            item=item,
            quantity=quantity,
            unit_cost=unit_cost,
            unit_price=unit_price,
        )

    def _create_pending_for_qty_change(
        self,
        transaction,
        transaction_type: str,
        line,
        quantity_delta: float,
    ) -> Pending:
        """
        Create a Pending record when quantity changes on an existing line.
        
        Records only the delta (change) in quantity, not the absolute value.
        
        Args:
            transaction: Parent transaction
            transaction_type: Type code
            line: The updated line
            quantity_delta: Change in quantity (positive = increase, negative = decrease)
            
        Returns:
            The created Pending record
        """
        pending_type = _get_pending_type(transaction_type)
        
        # Get item info from line
        item_id = None
        item_ida = ''
        if isinstance(line.item, dict):
            item_id = line.item.get('item_id')
            item_ida = line.item.get('ida_item', '')
        
        # Get current costs from line
        unit_cost = 0
        unit_price = 0
        if isinstance(line.cost, dict):
            unit_cost = line.cost.get('unit', 0)
        if hasattr(line, 'price') and isinstance(line.price, dict):
            unit_price = line.price.get('unit', 0)
        
        # Get probability from transaction for proposals (default to 100% = 1.0)
        probability = 1.0
        if pending_type == 'PP':
            prob_raw = getattr(transaction, 'probability', None)
            if prob_raw is None and hasattr(transaction, 'metadata') and isinstance(transaction.metadata, dict):
                prob_raw = transaction.metadata.get('probability')
            if prob_raw is not None:
                try:
                    probability = float(prob_raw) / 100.0 if float(prob_raw) > 1.0 else float(prob_raw)
                except (TypeError, ValueError):
                    probability = 1.0
        
        pending_data = {
            'type_id': pending_type,
            'item_num': item_ida or str(item_id),
            'item_id': item_id,
            'doc_id': getattr(transaction, 'ida', '') or str(transaction.pk),
            'doc_pk': transaction.pk,
            'line_id': line.pk,
            'line_num': line.item.get('line_number', 0) if isinstance(line.item, dict) else 0,
            
            # Quantity delta buckets (matching Item.quantity keys)
            'on_so': quantity_delta if pending_type == 'SO' else 0,
            'on_po': quantity_delta if pending_type == 'PO' else 0,
            'on_wo': quantity_delta if pending_type == 'WO' else 0,
            'on_in': quantity_delta if pending_type == 'IN' else 0,
            'on_r': quantity_delta if pending_type == 'RC' else 0,
            'on_p': quantity_delta * probability if pending_type == 'PP' else 0,  # Proposals track forecast
            
            # Pricing snapshot
            'unit_cost': unit_cost,
            'unit_price': unit_price,
            
            # Audit
            'reason': f'{pending_type.lower()} qty {"increase" if quantity_delta > 0 else "decrease"}',
            'take_action': 1,
            'changed_by': '',
            'quantity_delta': quantity_delta,
            
            # Transaction reference
            'transaction_type': transaction_type,
            'transaction_model': transaction._meta.model_name,
        }
        
        pending = Pending.objects.create(
            model_name='item',
            record_id=str(item_id) if item_id else '',
            purpose=PURPOSE_LINE_QTY_CHANGE,
            name=f'{pending_type} Qty Change: {item_ida or item_id} ({quantity_delta:+.2f})',
            data=pending_data,
        )
        
        logger.debug(
            f"Created pending qty change: {pending.pk} "
            f"for item {item_id}, delta={quantity_delta:+.2f}, type={pending_type}"
        )
        
        return pending

    def _create_pending_for_line_delete(
        self,
        transaction,
        transaction_type: str,
        line,
        quantity_released: float,
    ) -> Pending:
        """
        Create a Pending record when a line is deleted (soft or hard).
        
        Records the quantity to be released back from reservation.
        
        Args:
            transaction: Parent transaction
            transaction_type: Type code
            line: The line being deleted
            quantity_released: Quantity being released (positive value)
            
        Returns:
            The created Pending record
        """
        pending_type = _get_pending_type(transaction_type)
        
        # Get item info from line
        item_id = None
        item_ida = ''
        if isinstance(line.item, dict):
            item_id = line.item.get('item_id')
            item_ida = line.item.get('ida_item', '')
        
        # Get current costs from line
        unit_cost = 0
        unit_price = 0
        if isinstance(line.cost, dict):
            unit_cost = line.cost.get('unit', 0)
        if hasattr(line, 'price') and isinstance(line.price, dict):
            unit_price = line.price.get('unit', 0)
        
        # When a line is deleted, we release the reservation (negative delta)
        release_qty = -quantity_released
        
        # Get probability from transaction for proposals (default to 100% = 1.0)
        probability = 1.0
        if pending_type == 'PP':
            prob_raw = getattr(transaction, 'probability', None)
            if prob_raw is None and hasattr(transaction, 'metadata') and isinstance(transaction.metadata, dict):
                prob_raw = transaction.metadata.get('probability')
            if prob_raw is not None:
                try:
                    probability = float(prob_raw) / 100.0 if float(prob_raw) > 1.0 else float(prob_raw)
                except (TypeError, ValueError):
                    probability = 1.0
        
        pending_data = {
            'type_id': pending_type,
            'item_num': item_ida or str(item_id),
            'item_id': item_id,
            'doc_id': getattr(transaction, 'ida', '') or str(transaction.pk),
            'doc_pk': transaction.pk,
            'line_id': line.pk,
            'line_num': line.item.get('line_number', 0) if isinstance(line.item, dict) else 0,
            
            # Negative quantity = release reservation (matching Item.quantity keys)
            'on_so': release_qty if pending_type == 'SO' else 0,
            'on_po': release_qty if pending_type == 'PO' else 0,
            'on_wo': release_qty if pending_type == 'WO' else 0,
            'on_in': release_qty if pending_type == 'IN' else 0,  # Negative = reverse
            'on_r': release_qty if pending_type == 'RC' else 0,   # Negative = reverse
            'on_p': release_qty * probability if pending_type == 'PP' else 0,  # Proposals track forecast
            
            # Pricing snapshot
            'unit_cost': unit_cost,
            'unit_price': unit_price,
            
            # Audit
            'reason': f'{pending_type.lower()} line delete',
            'take_action': 1,
            'changed_by': '',
            'quantity_released': quantity_released,
            
            # Transaction reference
            'transaction_type': transaction_type,
            'transaction_model': transaction._meta.model_name,
        }
        
        pending = Pending.objects.create(
            model_name='item',
            record_id=str(item_id) if item_id else '',
            purpose=PURPOSE_LINE_DELETE,
            name=f'{pending_type} Line Delete: {item_ida or item_id} (-{quantity_released:.2f})',
            data=pending_data,
        )
        
        logger.debug(
            f"Created pending line delete: {pending.pk} "
            f"for item {item_id}, released={quantity_released:.2f}, type={pending_type}"
        )
        
        return pending


# Convenience function for single import
def add_item_to_transaction(transaction, item_id: int, quantity: int = 1, **kwargs):
    """Convenience function to add an item to a transaction."""
    service = LineItemService()
    return service.add_item_to_transaction(transaction, item_id, quantity, **kwargs)
