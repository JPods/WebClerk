"""Transaction save service with line dirty tracking and calculation verification.

This service handles atomic saving of transactions with their lines, including:
1. Dirty line tracking - only saves lines marked as `_dirty: true`
2. Math verification - WC3 recalculates and compares to R25 values
3. Item ID immutability - prevents changing item_id on existing lines

Usage from R25:
```typescript
// Lines are provided INSIDE record.lines (consistent with /wcapi/save/ pattern)
const response = await wcapi.saveTransaction({
  model_name: 'invoice',
  record: {
    id: 123,
    totals: {...},
    finance: {...},
    lines: [                                              // <-- Lines go HERE
      { id: 1, _dirty: false, quantity: {...}, price: {...} },  // Skipped
      { id: 2, _dirty: true, quantity: {...}, price: {...} },   // Saved
      { _dirty: true, quantity: {...}, price: {...} },          // New line, saved
    ]
  }
});
```
"""

from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
import logging

from django.db import transaction as db_transaction

if TYPE_CHECKING:
    from django.db.models import Model

logger = logging.getLogger(__name__)


# Tolerance for calculation comparison (0.01 = 1 cent)
CALC_TOLERANCE = Decimal("0.01")


def _d(val: Any, places: int = 2) -> Decimal:
    """Convert value to Decimal with specified precision."""
    try:
        d = Decimal(str(val) if val is not None else "0")
        return d.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0")


def _compare_values(expected: Any, actual: Any, tolerance: Decimal = CALC_TOLERANCE) -> bool:
    """Compare two numeric values within tolerance."""
    try:
        exp = _d(expected)
        act = _d(actual)
        return abs(exp - act) <= tolerance
    except Exception:
        return expected == actual


class CalculationMismatchError(Exception):
    """Raised when R25 calculations don't match WC3 recalculation."""
    def __init__(self, field: str, r25_value: Any, wc3_value: Any, line_id: Optional[int] = None):
        self.field = field
        self.r25_value = r25_value
        self.wc3_value = wc3_value
        self.line_id = line_id
        location = f"line {line_id}" if line_id else "header"
        super().__init__(
            f"Calculation mismatch on {location}.{field}: "
            f"R25 sent {r25_value}, WC3 calculated {wc3_value}"
        )


class ItemIdChangeError(Exception):
    """Raised when attempting to change item_id on an existing line."""
    def __init__(self, line_id: int, old_item_id: Any, new_item_id: Any):
        self.line_id = line_id
        self.old_item_id = old_item_id
        self.new_item_id = new_item_id
        super().__init__(
            f"Item_id cannot be changed for line {line_id}. "
            f"Current: {old_item_id}, Attempted: {new_item_id}. "
            f"To change the item, delete this line and add a new line with the correct item."
        )


def calculate_line_extended(line_data: Dict[str, Any]) -> Dict[str, Decimal]:
    """Calculate line-level extended values from inputs.
    
    Returns:
        Dict with calculated values: gross, discount_amount, extended, 
        gross_cost, discount_cost, cost_extended
    """
    qty = _d(line_data.get('quantity', {}).get('placed', 0))
    
    # Price calculations
    price = line_data.get('price', {}) or {}
    unit_price = _d(price.get('unit', 0))
    discount_pc = _d(price.get('discount_percent', 0))

    gross = qty * unit_price
    raw_discount_amount = price.get('discount_amount', None)
    if raw_discount_amount is None:
        discount_amount = gross * (discount_pc / Decimal("100"))
    else:
        discount_amount = _d(raw_discount_amount)
    extended = gross - discount_amount

    # Cost calculations
    cost = line_data.get('cost', {}) or {}
    unit_cost = _d(cost.get('unit', 0))
    discount_cost_pc = _d(cost.get('discount_percent', 0))

    gross_cost = qty * unit_cost
    raw_cost_discount = cost.get('discount_amount', None)
    if raw_cost_discount is None:
        discount_cost = gross_cost * (discount_cost_pc / Decimal("100"))
    else:
        discount_cost = _d(raw_cost_discount)
    cost_extended = gross_cost - discount_cost
    
    return {
        'gross': gross,
        'discount_amount': discount_amount,
        'extended': extended,
        'gross_cost': gross_cost,
        'discount_cost': discount_cost,
        'cost_extended': cost_extended,
    }


def verify_line_calculations(line_data: Dict[str, Any], line_id: Optional[int] = None) -> None:
    """Verify R25's line calculations match WC3 recalculation.
    
    Raises:
        CalculationMismatchError: If calculations don't match within tolerance
    """
    calculated = calculate_line_extended(line_data)
    
    price = line_data.get('price', {}) or {}
    cost = line_data.get('cost', {}) or {}
    
    # Verify price.extended
    r25_extended = price.get('extended')
    if r25_extended is not None:
        if not _compare_values(r25_extended, calculated['extended']):
            raise CalculationMismatchError(
                'price.extended', r25_extended, float(calculated['extended']), line_id
            )
    
    # Verify price.discount_amount
    r25_discount = price.get('discount_amount')
    if r25_discount is not None:
        if not _compare_values(r25_discount, calculated['discount_amount']):
            raise CalculationMismatchError(
                'price.discount_amount', r25_discount, float(calculated['discount_amount']), line_id
            )
    
    # Verify cost.extended
    r25_cost_extended = cost.get('extended')
    if r25_cost_extended is not None:
        if not _compare_values(r25_cost_extended, calculated['cost_extended']):
            raise CalculationMismatchError(
                'cost.extended', r25_cost_extended, float(calculated['cost_extended']), line_id
            )


def calculate_header_totals(lines: List[Dict[str, Any]], header_data: Dict[str, Any]) -> Dict[str, Decimal]:
    """Calculate header totals from lines.
    
    Returns:
        Dict with calculated header totals
    """
    subtotal = Decimal("0")
    cost_total = Decimal("0")
    
    for line in lines:
        item = line.get('item', {}) or {}
        if item.get('is_deleted'):
            continue
        
        price = line.get('price', {}) or {}
        cost = line.get('cost', {}) or {}
        
        subtotal += _d(price.get('extended', 0))
        cost_total += _d(cost.get('extended', 0))
    
    totals = header_data.get('totals', {}) or {}
    finance = header_data.get('finance', {}) or {}
    
    discount = _d(totals.get('discount', 0))
    taxable = subtotal - discount
    
    tax_rate = _d(finance.get('sales_tax_rate', 0))
    tax = taxable * (tax_rate / Decimal("100"))
    
    shipping = _d(totals.get('shipping', 0))
    other = _d(totals.get('other', 0))
    
    total = taxable + tax + shipping + other
    
    margin = total - cost_total
    margin_pc = (margin / total * Decimal("100")) if total > 0 else Decimal("0")
    
    received = _d(totals.get('received', 0))
    balance = total - received
    
    return {
        'subtotal': subtotal,
        'discount': discount,
        'taxable': taxable,
        'tax': tax,
        'shipping': shipping,
        'other': other,
        'total': total,
        'cost': cost_total,
        'margin': margin,
        'margin_pc': margin_pc,
        'received': received,
        'balance': balance,
    }


def verify_header_calculations(
    header_data: Dict[str, Any], 
    lines: List[Dict[str, Any]]
) -> None:
    """Verify R25's header calculations match WC3 recalculation.
    
    Raises:
        CalculationMismatchError: If calculations don't match within tolerance
    """
    calculated = calculate_header_totals(lines, header_data)
    
    totals = header_data.get('totals', {}) or {}
    
    # Fields to verify
    fields_to_check = ['subtotal', 'taxable', 'tax', 'total', 'cost', 'margin', 'balance']
    
    for field in fields_to_check:
        r25_value = totals.get(field)
        if r25_value is not None:
            wc3_value = calculated.get(field, Decimal("0"))
            if not _compare_values(r25_value, wc3_value):
                raise CalculationMismatchError(field, r25_value, float(wc3_value))


def save_transaction_with_lines(
    model_key: str,
    header_data: Dict[str, Any],
    lines_data: List[Dict[str, Any]],
    *,
    request: Any,
    verify_calculations: bool = True,
    save_only_dirty: bool = True,
) -> Dict[str, Any]:
    """Save a transaction with its lines atomically.
    
    Args:
        model_key: Transaction model key (e.g., 'invoice', 'order')
        header_data: Transaction header data including id for updates
        lines_data: List of line data, each may have `_dirty` flag
        request: Django request for permissions
        verify_calculations: If True, verify R25 calculations match WC3
        save_only_dirty: If True, only save lines with `_dirty: true`
    
    Returns:
        Dict with saved header, lines, and any calculation warnings
    
    Raises:
        CalculationMismatchError: If verify_calculations=True and calcs don't match
        ItemIdChangeError: If attempting to change item_id on existing line
    """
    from apps.core.utils import registry
    from apps.core.services.wcapi import filter_input_fields
    
    # Resolve models
    HeaderModel = registry.resolve(model_key)
    if not HeaderModel:
        raise ValueError(f"Unknown transaction model: {model_key}")
    
    # Determine line model
    line_model_key = f"{model_key}line"
    LineModel = registry.resolve(line_model_key)
    if not LineModel:
        raise ValueError(f"Unknown line model: {line_model_key}")
    
    header_id = header_data.get('id')
    result = {
        'header': None,
        'lines': [],
        'lines_saved': 0,
        'lines_skipped': 0,
        'calculation_warnings': [],
        'action': 'created' if header_id is None else 'updated',
    }
    
    with db_transaction.atomic():
        # Verify calculations before saving (fail fast)
        if verify_calculations:
            # Verify each dirty line
            for line_data in lines_data:
                is_dirty = line_data.get('_dirty', True)  # Default dirty if not specified
                if is_dirty or not save_only_dirty:
                    line_id = line_data.get('id')
                    verify_line_calculations(line_data, line_id)
            
            # Verify header totals
            verify_header_calculations(header_data, lines_data)
        
        # Save header
        header_clean = filter_input_fields(HeaderModel, header_data)
        # Remove internal flags
        header_clean.pop('_dirty', None)
        
        if header_id:
            header_obj = HeaderModel.objects.select_for_update().get(pk=header_id)
            for k, v in header_clean.items():
                setattr(header_obj, k, v)
            header_obj.save()
        else:
            header_obj = HeaderModel.objects.create(**header_clean)
            header_id = header_obj.pk
        
        result['header'] = {'id': header_obj.pk}
        
        # Process lines
        existing_lines = {
            line.pk: line 
            for line in LineModel.objects.filter(parent_id=header_id).select_for_update()
        }
        
        for line_data in lines_data:
            line_id = line_data.get('id')
            is_dirty = line_data.get('_dirty', True)  # Default dirty if not specified
            
            # Skip non-dirty existing lines
            if line_id is not None and save_only_dirty and not is_dirty:
                result['lines_skipped'] += 1
                result['lines'].append({
                    'id': line_id,
                    'action': 'skipped',
                    'reason': 'not_dirty'
                })
                continue
            
            # Clean line data
            line_clean = filter_input_fields(LineModel, line_data)
            line_clean.pop('_dirty', None)
            line_clean['parent_id'] = header_id
            
            if line_id:
                # Update existing line
                existing_line = existing_lines.get(line_id)
                if not existing_line:
                    raise LookupError(f"Line {line_id} not found for transaction {header_id}")
                
                # Verify item_id hasn't changed
                current_item = getattr(existing_line, 'item', {}) or {}
                new_item = line_data.get('item', {}) or {}
                current_item_id = current_item.get('item_id')
                new_item_id = new_item.get('item_id')
                
                if (current_item_id is not None and 
                    new_item_id is not None and 
                    current_item_id != new_item_id):
                    raise ItemIdChangeError(line_id, current_item_id, new_item_id)
                
                for k, v in line_clean.items():
                    setattr(existing_line, k, v)
                existing_line.save()
                
                result['lines_saved'] += 1
                result['lines'].append({
                    'id': line_id,
                    'action': 'updated'
                })
            else:
                # Create new line
                new_line = LineModel.objects.create(**line_clean)
                result['lines_saved'] += 1
                result['lines'].append({
                    'id': new_line.pk,
                    'action': 'created'
                })
                
                # Create pending inventory record for new lines
                try:
                    from apps.transactions.services.line_item_service import LineItemService
                    service = LineItemService(create_pending=True)
                    service._create_pending_for_new_line(
                        parent=header_obj,
                        parent_model_key=model_key,
                        line=new_line,
                        line_data=line_data,
                    )
                    logger.debug(f"Created pending inventory record for new line {new_line.pk}")
                except Exception as pending_err:
                    logger.warning(f"Failed to create pending for line {new_line.pk}: {pending_err}")
    
    logger.info(
        "Transaction saved: model=%s header_id=%s lines_saved=%s lines_skipped=%s",
        model_key, header_id, result['lines_saved'], result['lines_skipped']
    )
    
    return result
