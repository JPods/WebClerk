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


def _resolve_parent_fk(LineModel, HeaderModel, model_key: str) -> str:
    """Return the attname (e.g. 'invoice_id') of the FK on LineModel
    that points to HeaderModel.  Falls back to '{model_key}_id'."""
    from django.db.models import ForeignKey
    for f in LineModel._meta.get_fields():
        if isinstance(f, ForeignKey) and f.related_model is HeaderModel:
            return f.attname          # e.g. 'invoice_id'
    return f"{model_key}_id"          # conventional fallback


# Tolerance for calculation comparison (0.01 = 1 cent)
CALC_TOLERANCE = Decimal("0.01")
# Pending type codes — mirrors line_item_service._get_pending_type
_PENDING_TYPE_MAP = {
    'proposal': 'PP',
    'order': 'SO',
    'invoice': 'IN',
    'purchase': 'PO',
    'workorder': 'WO',
}


def _create_pending_from_deltas(
    header_obj: 'Model',
    model_key: str,
    pending_deltas: List[Dict[str, Any]],
) -> int:
    """Convert the collected pending_deltas array into Pending records.

    Backend-authoritative:
      • ``pending_type`` is derived from ``model_key``.
      • ``parent_id`` / ``parent_model`` on the header determine whether this
        is a transfer.  For transfers (e.g. order → invoice) a single Pending
        captures on_in, on_so release, and on_hand deduction.
      • ``invoice_line_id`` + ``order_line_id`` are stored in every record.
        The pair must be unique — if a duplicate already exists the record is
        skipped.

    Returns the number of Pending records created.
    """
    from apps.core.models import Pending
    from apps.products.models import Item

    pending_type = _PENDING_TYPE_MAP.get(model_key.lower(), 'XX')
    parent_id = getattr(header_obj, 'parent_id', None)
    parent_model = getattr(header_obj, 'parent_model', None) or ''
    is_transfer = bool(parent_id and parent_model)
    doc_ida = getattr(header_obj, 'ida', '') or str(header_obj.pk)

    created_count = 0
    seen_pairs: set = set()

    def _bucket_key_for_type_code(type_code: str) -> str | None:
        return {
            'SO': 'on_so',
            'PO': 'on_po',
            'WO': 'on_wo',
            'PP': 'on_p',
            'IN': 'on_in',
        }.get(type_code)

    for delta in pending_deltas:
        item_id = delta['item_id']
        line_id = delta['line_id']           # the saved new-line PK
        source_line_id = delta.get('source_line_id')  # FK to source line (transfer)
        quantity = delta['quantity']
        is_qty_change = delta.get('is_qty_change', False)  # True for qty change on existing line

        # ── Build the pair key ───────────────────────────────────────
        # For invoice-from-order: invoice_line_id = line_id, order_line_id = source_line_id
        if model_key.lower() == 'invoice':
            invoice_line_id = line_id
            order_line_id = source_line_id
        elif model_key.lower() == 'order':
            order_line_id = line_id
            invoice_line_id = source_line_id
        else:
            invoice_line_id = None
            order_line_id = None

        pair = (invoice_line_id, order_line_id)
        if pair in seen_pairs:
            logger.warning(
                'Duplicate pair skipped in same batch: IL=%s OL=%s item=%s',
                invoice_line_id, order_line_id, item_id,
            )
            continue
        seen_pairs.add(pair)

        # ── DB-level duplicate guard ─────────────────────────────────
        if invoice_line_id and order_line_id:
            dup = Pending.objects.filter(
                model_name='item',
                record_id=str(item_id),
                purpose='inventory_line_add',
                dt_processed=0,
                data__invoice_line_id=invoice_line_id,
                data__order_line_id=order_line_id,
            ).exists()
            if dup:
                logger.warning(
                    'Duplicate pending blocked: IL=%s OL=%s item=%s',
                    invoice_line_id, order_line_id, item_id,
                )
                continue

        # ── Build quantity buckets ───────────────────────────────────
        # Determine reason based on whether this is a qty change or new line
        qty_direction = 'increase' if quantity > 0 else 'decrease'
        default_reason = (
            f'{pending_type.lower()} qty {qty_direction}'
            if is_qty_change
            else f'{pending_type.lower()} line add'
        )
        pending_data: Dict[str, Any] = {
            'type_id': pending_type,
            'item_id': item_id,
            'item_num': delta.get('item_ida', str(item_id)),
            'doc_id': doc_ida,
            'doc_pk': header_obj.pk,
            'line_id': line_id,
            'line_num': 0,
            # Quantity buckets — zeroed, then set by type
            'on_so': 0, 'on_po': 0, 'on_wo': 0,
            'on_in': 0, 'on_r': 0, 'on_p': 0, 'on_hand': 0,
            # Pricing snapshot
            'unit_cost': delta.get('unit_cost', 0),
            'unit_price': delta.get('unit_price', 0),
            # Audit
            'reason': default_reason,
            'take_action': 1,
            'changed_by': '',
            'quantity_delta': quantity if is_qty_change else 0,  # For qty changes, store the delta
            'transaction_type': model_key.lower(),
            'transaction_model': header_obj._meta.model_name,
            # Line-pair IDs (one pending per pair; forbids duplicates)
            'invoice_line_id': invoice_line_id,
            'order_line_id': order_line_id,
            'links': {},
        }

        target_bucket = _bucket_key_for_type_code(pending_type)
        if target_bucket:
            pending_data[target_bucket] = quantity

        if is_transfer and parent_model:
            source_type_code = _PENDING_TYPE_MAP.get(str(parent_model).lower())
            source_bucket = _bucket_key_for_type_code(source_type_code or '')
            if source_bucket:
                pending_data[source_bucket] = pending_data.get(source_bucket, 0) - quantity
                pending_data['links'][str(parent_model).lower()] = {'parent_id': parent_id}
                pending_data['reason'] = (
                    f"{pending_type.lower()} line add (releases {source_bucket})"
                )

        if pending_type == 'IN':
            pending_data['on_hand'] = pending_data.get('on_hand', 0) - quantity
            if is_transfer and parent_model:
                pending_data['reason'] = (
                    f"in line add (releases source, deducts on_hand)"
                )

        # Look up item.ida for the name field
        item_ida = delta.get('item_ida', str(item_id))
        try:
            item_obj = Item.objects.only('ida').get(pk=item_id)
            item_ida = item_obj.ida or str(item_id)
        except Item.DoesNotExist:
            pass

        # Use different purpose and name for qty changes vs line adds
        if is_qty_change:
            pending_purpose = 'inventory_qty_change'
            pending_name = f'{pending_type} Qty Change: {item_ida}'
        else:
            pending_purpose = 'inventory_line_add'
            pending_name = f'{pending_type} Line Add: {item_ida}'

        Pending.objects.create(
            model_name='item',
            record_id=str(item_id),
            purpose=pending_purpose,
            name=pending_name,
            data=pending_data,
        )
        created_count += 1
        logger.debug(
            "Pending created: type=%s item=%s line=%s src=%s",
            pending_type, item_id, line_id, source_line_id,
        )

    logger.info("Created %d pending records for %s #%s", created_count, model_key, header_obj.pk)
    return created_count

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


class TransferQuantityError(Exception):
    """Raised when a transfer line requests more than source remaining qty."""

    def __init__(self, source_model: str, source_line_id: int, requested: float, remaining: float):
        self.source_model = source_model
        self.source_line_id = source_line_id
        self.requested = requested
        self.remaining = remaining
        super().__init__(
            f"Transfer quantity exceeds source remaining for "
            f"{source_model}_line #{source_line_id}: requested={requested}, remaining={remaining}"
        )


class InsufficientInventoryError(Exception):
    """Raised when transfer requires more inventory than currently available."""

    def __init__(self, item_id: int, sku: str, required: float, available: float):
        self.item_id = item_id
        self.sku = sku
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient inventory for item {sku} (id={item_id}): "
            f"required={required}, available={available}"
        )


def _line_staged_qty(line_data: Dict[str, Any]) -> float:
    """Get the effective line quantity from line data.

    Pending and transfer validations should follow the user's current qty,
    which is stored in quantity.active. For legacy payloads without active,
    fall back to staged.
    """
    qty_data = line_data.get('quantity') or {}
    if not isinstance(qty_data, dict):
        return 0.0
    return float(
        qty_data.get('active', 0)
        or qty_data.get('staged', 0)
        or qty_data.get('placed', 0)
        or qty_data.get('actioned', 0)
        or 0
    )


def _validate_transfer_quantities_and_inventory(
    *,
    model_key: str,
    parent_model: str,
    lines_data: List[Dict[str, Any]],
) -> None:
    """Validate transfer requests before creating/updating lines.

    Rules:
    1) Sum transferred qty per source line and block if request > source.remaining.
    2) For transfer-to-invoice, block when required qty exceeds item available stock.
    """
    from apps.core.utils import registry

    source_line_key = f"{parent_model}line"
    SourceLineModel = registry.resolve(source_line_key)
    if SourceLineModel is None:
        logger.warning("Transfer validation skipped; unresolved source line model: %s", source_line_key)
        return

    requested_by_source_line: Dict[int, float] = {}
    requested_by_item: Dict[int, float] = {}

    for line_data in lines_data:
        if line_data.get('id') is not None:
            continue

        qty_staged = _line_staged_qty(line_data)
        if qty_staged <= 0:
            continue

        refs = line_data.get('refs') or {}
        source_info = refs.get('source') or {}
        src_line_id = source_info.get(f'{parent_model}_line_id')
        if src_line_id:
            src_line_id = int(src_line_id)
            requested_by_source_line[src_line_id] = requested_by_source_line.get(src_line_id, 0.0) + qty_staged

        item_data = line_data.get('item', {}) or {}
        item_id = item_data.get('id') or item_data.get('item_id')
        if item_id:
            item_id = int(item_id)
            requested_by_item[item_id] = requested_by_item.get(item_id, 0.0) + qty_staged

    if requested_by_source_line:
        source_lines = {
            src.pk: src
            for src in SourceLineModel.objects.select_for_update().filter(
                pk__in=list(requested_by_source_line.keys())
            )
        }

        for src_line_id, requested in requested_by_source_line.items():
            src_line = source_lines.get(src_line_id)
            if src_line is None:
                raise TransferQuantityError(parent_model, src_line_id, requested, 0.0)

            src_qty = dict(getattr(src_line, 'quantity', None) or {})
            remaining = float(src_qty.get('remaining', 0) or 0)
            if requested > remaining + 1e-9:
                raise TransferQuantityError(parent_model, src_line_id, requested, remaining)

    if requested_by_item:
        from apps.products.models import Item

        item_map = {
            item.pk: item
            for item in Item.objects.select_for_update().filter(
                pk__in=list(requested_by_item.keys())
            )
        }

        for item_id, required_qty in requested_by_item.items():
            item_obj = item_map.get(item_id)
            if item_obj is None:
                raise InsufficientInventoryError(item_id, str(item_id), required_qty, 0.0)

            quantity = dict(getattr(item_obj, 'quantity', None) or {})
            available = float(quantity.get('available', quantity.get('on_hand', 0)) or 0)
            if required_qty > available + 1e-9:
                sku = item_obj.sku or item_obj.ida or str(item_id)
                raise InsufficientInventoryError(item_id, sku, required_qty, available)


def _update_parent_children_active(
    header_obj: 'Model',
    child_line_id: int,
    new_active: float,
) -> bool:
    """Update the parent line's children_active entry when a child's active
    qty changes.

    Finds the parent via header_obj.parent_model / parent_id and the child
    line's refs.source.<parent_model>_line_id.  Updates the children_active
    tracker on the parent line with the new active value and recomputes
    remaining = active − children_active.sum.

    Returns True if a parent line was updated, False otherwise.
    """
    parent_model = getattr(header_obj, 'parent_model', None)
    parent_id = getattr(header_obj, 'parent_id', None)
    if not parent_model or not parent_id:
        return False

    from apps.core.utils import registry

    source_line_key = f"{parent_model}line"
    SourceLineModel = registry.resolve(source_line_key)
    if SourceLineModel is None:
        return False

    # Find which source line this child references
    # Read the child line's refs.source to get the parent line id
    model_key = header_obj.__class__.__name__.lower()
    child_line_key = f"{model_key}line"
    ChildLineModel = registry.resolve(child_line_key)
    if not ChildLineModel:
        return False

    try:
        child_line = ChildLineModel.objects.get(pk=child_line_id)
    except ChildLineModel.DoesNotExist:
        return False

    refs = getattr(child_line, 'refs', None) or {}
    source_info = refs.get('source') or {}
    src_line_id = source_info.get(f'{parent_model}_line_id')
    if not src_line_id:
        return False

    try:
        src_line = SourceLineModel.objects.select_for_update().get(pk=src_line_id)
    except SourceLineModel.DoesNotExist:
        logger.warning("Parent line %s #%s not found for children_active update", source_line_key, src_line_id)
        return False

    q = dict(getattr(src_line, 'quantity', None) or {})
    active = float(q.get('active', 0) or 0)

    # Update children_active tracker
    children = q.get('children_active', {'sum': 0, 'lines': []})
    if not isinstance(children, dict):
        children = {'sum': 0, 'lines': []}
    lines_list = children.get('lines', [])
    if not isinstance(lines_list, list):
        lines_list = []

    # Find and update the existing child entry, or log warning
    found = False
    for entry in lines_list:
        if entry.get('id') == child_line_id:
            entry['active'] = new_active
            found = True
            break
    if not found:
        # Child not tracked yet — add it (shouldn't normally happen)
        lines_list.append({'id': child_line_id, 'active': new_active})

    children_sum = sum(float(c.get('active', 0) or 0) for c in lines_list)
    children['sum'] = children_sum
    children['lines'] = lines_list
    q['children_active'] = children
    q['remaining'] = max(0.0, active - children_sum)

    src_line.quantity = q
    src_line._pending_created = True
    src_line.save(update_fields=['quantity', 'dt_modified', 'version'])

    logger.debug(
        "Updated parent %s #%s children_active: child=%s active=%s sum=%s remaining=%s",
        source_line_key, src_line_id, child_line_id, new_active,
        children_sum, q['remaining'],
    )
    return True


def _update_source_lines_after_transfer(
    header_obj: 'Model',
    model_key: str,
    lines_data: List[Dict[str, Any]],
) -> int:
    """After saving a *new* transferred transaction, update *each* source
    (parent) line's ``children_active`` tracker and recompute remaining.

    Universal remaining formula:
      remaining = active − children_active["sum"]

    At creation time the child's active == child's staged == what was
    transferred from the parent.  The ``children_active`` dict stored
    on the parent line records every child and its current active qty
    so that later edits can simply update the entry and recompute.

    Returns number of source lines updated.

    The frontend stamps every transferred line's refs.source with:
        { "<source_type>_line_id": <pk>, "<source_type>_id": <pk>,
          "converted_from": "<source_type>" }
    """
    parent_model = getattr(header_obj, 'parent_model', None)
    parent_id = getattr(header_obj, 'parent_id', None)
    if not parent_model or not parent_id:
        return 0

    from apps.core.utils import registry

    source_line_key = f"{parent_model}line"
    SourceLineModel = registry.resolve(source_line_key)
    if SourceLineModel is None:
        logger.warning("_update_source_lines_after_transfer: cannot resolve %s", source_line_key)
        return 0

    # We need the saved child line PKs — map source_line_id → child_line_id
    # by reading the result lines that were just saved.
    # The child line PKs were added to `result['lines']` during the save loop,
    # but we don't have the result dict here.  Instead, look up by source ref.
    from apps.core.utils import registry as reg
    child_line_key = f"{model_key}line"
    ChildLineModel = reg.resolve(child_line_key)

    updated = 0
    with db_transaction.atomic():
        for ld in lines_data:
            refs = ld.get('refs') or {}
            source_info = refs.get('source') or {}
            src_line_id = source_info.get(f'{parent_model}_line_id')
            if not src_line_id:
                continue

            qty_data = ld.get('quantity') or {}
            child_active = 0.0
            if isinstance(qty_data, dict):
                child_active = float(qty_data.get('active', 0) or qty_data.get('staged', 0) or 0)
            if child_active <= 0:
                continue

            # Find the child line PK from the saved line (look up by source ref)
            child_line_id = ld.get('id') or 0
            if not child_line_id and ChildLineModel:
                # Fallback: query child lines that reference this source line
                try:
                    child_line = ChildLineModel.objects.filter(
                        **{_resolve_parent_fk(ChildLineModel, type(header_obj), model_key): header_obj.pk}
                    ).filter(
                        refs__source__contains={f'{parent_model}_line_id': src_line_id}
                    ).order_by('-pk').first()
                    if child_line:
                        child_line_id = child_line.pk
                except Exception:
                    pass

            try:
                src_line = SourceLineModel.objects.select_for_update().get(pk=src_line_id)
            except SourceLineModel.DoesNotExist:
                logger.warning("Source line %s #%s not found", source_line_key, src_line_id)
                continue

            q = dict(getattr(src_line, 'quantity', None) or {})
            active = float(q.get('active', 0) or 0)

            # Build/update children_active tracker
            children = q.get('children_active', {'sum': 0, 'lines': []})
            if not isinstance(children, dict):
                children = {'sum': 0, 'lines': []}
            lines_list = children.get('lines', [])
            if not isinstance(lines_list, list):
                lines_list = []

            # Append this child
            lines_list.append({'id': child_line_id, 'active': child_active})
            children_sum = sum(float(c.get('active', 0) or 0) for c in lines_list)
            children['sum'] = children_sum
            children['lines'] = lines_list
            q['children_active'] = children

            # Recompute remaining = active − children_active.sum
            q['remaining'] = max(0.0, active - children_sum)

            # Also keep transferred for backward compat
            q['transferred'] = float(q.get('transferred', 0) or 0) + child_active

            src_line.quantity = q

            save_fields = ['quantity', 'dt_modified', 'version']
            if q['remaining'] <= 0:
                src_line.status = 'transferred'
                save_fields.append('status')

            src_line._pending_created = True
            src_line.save(update_fields=save_fields)
            updated += 1
            logger.debug(
                "Updated source %s #%s: children_active=%s remaining=%s",
                source_line_key, src_line_id, children, q['remaining'],
            )

    return updated


def calculate_line_extended(line_data: Dict[str, Any]) -> Dict[str, Decimal]:
    """Calculate line-level extended values from inputs.
    
    Returns:
        Dict with calculated values: gross, discount_amount, extended, 
        gross_cost, discount_cost, cost_extended
    """
    qty_data = line_data.get('quantity', {}) or {}
    # Use canonical field names: staged (committed) or active (user input)
    qty = _d(qty_data.get('staged', 0) or qty_data.get('active', 0))
    
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

    Collect-then-create pattern (2026-02-21):
      1. Save header + lines inside an atomic block (signals suppressed).
      2. After all saves, the backend collects pending deltas — one per
         new line, keyed by (invoice_line_id, order_line_id) to forbid
         duplicate pairs.
      3. Create Pending records from the collection.
      4. One dispatch signal after all pending records exist.

    The backend is authoritative — transfer detection uses parent_id /
    parent_model on the header, not front-end refs.

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

    # Resolve the FK field on LineModel that points to HeaderModel.
    parent_fk_attname = _resolve_parent_fk(LineModel, HeaderModel, model_key)

    header_id = header_data.get('id')
    result: Dict[str, Any] = {
        'header': None,
        'lines': [],
        'lines_saved': 0,
        'lines_skipped': 0,
        'calculation_warnings': [],
        'action': 'created' if header_id is None else 'updated',
    }

    # ── Collection for deferred pending creation ──────────────────────
    # Each element holds the data needed to create ONE Pending record.
    # Built during the save loop, converted to Pending records afterwards.
    pending_deltas: List[Dict[str, Any]] = []

    with db_transaction.atomic():
        # Verify calculations before saving (fail fast)
        if verify_calculations:
            for line_data in lines_data:
                is_dirty = line_data.get('_dirty', True)
                if is_dirty or not save_only_dirty:
                    line_id = line_data.get('id')
                    verify_line_calculations(line_data, line_id)
            verify_header_calculations(header_data, lines_data)

        # Save header
        header_clean = filter_input_fields(HeaderModel, header_data)
        header_clean.pop('_dirty', None)
        if not header_id:
            header_clean.pop('id', None)

        if header_id:
            header_obj = HeaderModel.objects.select_for_update().get(pk=header_id)
            for k, v in header_clean.items():
                setattr(header_obj, k, v)
            header_obj.save()
        else:
            header_obj = HeaderModel.objects.create(**header_clean)
            header_id = header_obj.pk

        # ── Denormalize org (customer/vendor/manufacturer) into refs.links ──
        try:
            from apps.transactions.services.denormalize_org_links import denormalize_org_links
            if denormalize_org_links(header_obj, model_key):
                header_obj.save(update_fields=['refs'])
                logger.debug("Denormalized org links for %s #%s", model_key, header_id)
        except Exception as org_err:
            logger.warning("Failed to denormalize org links for %s #%s: %s", model_key, header_id, org_err)

        result['header'] = {'id': header_obj.pk}

        # Validate transfer quantities against source.remaining before line saves.
        parent_model = getattr(header_obj, 'parent_model', None)
        parent_id = getattr(header_obj, 'parent_id', None)
        if parent_model and parent_id:
            _validate_transfer_quantities_and_inventory(
                model_key=model_key,
                parent_model=str(parent_model),
                lines_data=lines_data,
            )

        # ── Phase 1: Save all lines (signals suppressed) ────────────
        # Track the line_increment counter for auto-assigning line_number
        current_line_increment = getattr(header_obj, 'line_increment', 10) or 10

        existing_lines = {
            line.pk: line
            for line in LineModel.objects.filter(**{parent_fk_attname: header_id}).select_for_update()
        }

        for line_data in lines_data:
            line_id = line_data.get('id')
            is_dirty = line_data.get('_dirty', True)

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
            line_clean[parent_fk_attname] = header_id

            if line_id:
                # Update existing line
                existing_line = existing_lines.get(line_id)
                if not existing_line:
                    raise LookupError(f"Line {line_id} not found for transaction {header_id}")

                current_item = getattr(existing_line, 'item', {}) or {}
                new_item = line_data.get('item', {}) or {}
                current_item_id = current_item.get('item_id')
                new_item_id = new_item.get('item_id')

                if (current_item_id is not None and
                    new_item_id is not None and
                    current_item_id != new_item_id):
                    raise ItemIdChangeError(line_id, current_item_id, new_item_id)

                # ── Capture old quantity before update for delta calculation ──
                old_qty_data = getattr(existing_line, 'quantity', {}) or {}
                old_qty_effective = float(
                    old_qty_data.get('active', 0)
                    or old_qty_data.get('staged', 0)
                    or old_qty_data.get('placed', 0)
                    or old_qty_data.get('actioned', 0)
                    or 0
                )

                # JSON fields that should deep-merge (not replace) on update
                json_merge_fields = {'item', 'quantity', 'cost', 'price', 'tax', 'action', 'physical', 'flow', 'source'}
                for k, v in line_clean.items():
                    # Deep-merge JSON fields to preserve existing keys not in the update
                    if k in json_merge_fields and isinstance(v, dict):
                        existing_val = getattr(existing_line, k, None)
                        if existing_val and isinstance(existing_val, dict):
                            v = {**existing_val, **v}
                    setattr(existing_line, k, v)
                existing_line._pending_created = True  # Suppress signal
                existing_line.save()

                # ── Check for quantity change and create pending delta ──
                new_qty_data = getattr(existing_line, 'quantity', {}) or {}
                new_qty_effective = float(
                    new_qty_data.get('active', 0)
                    or new_qty_data.get('staged', 0)
                    or new_qty_data.get('placed', 0)
                    or new_qty_data.get('actioned', 0)
                    or 0
                )
                quantity_delta = new_qty_effective - old_qty_effective

                if quantity_delta != 0 and current_item_id:
                    # Collect pending delta for quantity change on existing line
                    cost_data = line_data.get('cost', {}) or {}
                    price_data = line_data.get('price', {}) or {}
                    pending_deltas.append({
                        'item_id': current_item_id,
                        'item_ida': current_item.get('ida', str(current_item_id)),
                        'quantity': quantity_delta,  # Delta, not absolute
                        'line_id': existing_line.pk,
                        'source_line_id': None,  # Not a transfer
                        'unit_cost': float(cost_data.get('unit', 0) or (getattr(existing_line, 'cost', {}) or {}).get('unit', 0) or 0),
                        'unit_price': float(price_data.get('unit', 0) or (getattr(existing_line, 'price', {}) or {}).get('unit', 0) or 0),
                        'line_data': line_data,
                        'is_qty_change': True,  # Flag to indicate this is a qty change, not new line
                    })

                # ── Update parent's children_active when child active changes ──
                old_active = float(old_qty_data.get('active', 0) or 0)
                new_active = float(new_qty_data.get('active', 0) or 0)
                if old_active != new_active:
                    _update_parent_children_active(
                        header_obj=header_obj,
                        child_line_id=line_id,
                        new_active=new_active,
                    )

                result['lines_saved'] += 1
                result['lines'].append({
                    'id': line_id,
                    'line_number': getattr(existing_line, 'line_number', 0),
                    'action': 'updated'
                })
            else:
                # Create new line — suppress signal so no pending is created
                # by the post_save handler.  We build pending_deltas below.
                # Auto-assign line_number if not provided or zero
                incoming_ln = line_clean.get('line_number', 0) or 0
                if incoming_ln == 0:
                    line_clean['line_number'] = current_line_increment
                    current_line_increment += 10
                new_line = LineModel(**line_clean)
                new_line._pending_created = True
                new_line.save()
                result['lines_saved'] += 1
                result['lines'].append({
                    'id': new_line.pk,
                    'line_number': getattr(new_line, 'line_number', 0),
                    'action': 'created'
                })

                # ── Collect pending delta for this line ──────────────
                # The backend determines item_id, quantity, cost, price
                # from the saved line — no reliance on front-end refs.
                item_data = line_data.get('item', {}) or {}
                item_id = (
                    item_data.get('id')
                    or item_data.get('item_id')
                    or (getattr(new_line, 'item', None) or {}).get('id')
                    or (getattr(new_line, 'item', None) or {}).get('item_id')
                )
                qty_data = line_data.get('quantity', {}) or {}
                # Use canonical field names: staged (committed) or active (user input)
                qty_staged = float(
                    qty_data.get('active', 0)
                    or qty_data.get('staged', 0)
                    or qty_data.get('placed', 0)
                    or qty_data.get('actioned', 0)
                    or 0
                )
                if not qty_staged and hasattr(new_line, 'quantity') and isinstance(new_line.quantity, dict):
                    qty_staged = float(
                        new_line.quantity.get('active', 0)
                        or new_line.quantity.get('staged', 0)
                        or new_line.quantity.get('placed', 0)
                        or new_line.quantity.get('actioned', 0)
                        or 0
                    )

                cost_data = line_data.get('cost', {}) or {}
                price_data = line_data.get('price', {}) or {}

                # Backend-authoritative transfer detection:
                # If header has parent_id + parent_model, this is a transfer.
                # The source order_line_id comes from refs.source on the
                # line_data (stamped by R25) — but we also look it up from
                # the persisted new_line.refs as a fallback.
                source_line_id = None
                parent_model = getattr(header_obj, 'parent_model', None)
                if parent_model:
                    refs = line_data.get('refs') or {}
                    source_info = refs.get('source') or {}
                    source_line_id = source_info.get(f'{parent_model}_line_id')
                    if not source_line_id and isinstance(getattr(new_line, 'refs', None), dict):
                        source_line_id = ((new_line.refs or {}).get('source') or {}).get(f'{parent_model}_line_id')

                if item_id and qty_staged:
                    pending_deltas.append({
                        'item_id': item_id,
                        'item_ida': item_data.get('ida', str(item_id)),
                        'quantity': qty_staged,
                        'line_id': new_line.pk,
                        'source_line_id': source_line_id,
                        'unit_cost': float(cost_data.get('unit', 0) or 0),
                        'unit_price': float(price_data.get('unit', 0) or 0),
                        'line_data': line_data,
                    })

    # ── Persist bumped line_increment back to the header ──────────
    if hasattr(header_obj, 'line_increment') and header_obj.line_increment != current_line_increment:
        header_obj.line_increment = current_line_increment
        header_obj.save(update_fields=['line_increment'])

    # ── Phase 2: Create Pending records from collected deltas ────────
    # Runs OUTSIDE the atomic block — lines are already committed with IDs.
    # One Pending per delta; the (invoice_line_id, order_line_id) pair is
    # stored in every record to forbid duplicates.
    if pending_deltas:
        try:
            _create_pending_from_deltas(
                header_obj=header_obj,
                model_key=model_key,
                pending_deltas=pending_deltas,
            )
        except Exception as pend_err:
            logger.warning("Failed to create pending records: %s", pend_err)

    # ── Phase 3: Update source lines (transfer only) ────────────────
    if result['action'] == 'created' and getattr(header_obj, 'parent_id', None):
        try:
            src_updated = _update_source_lines_after_transfer(
                header_obj, model_key, lines_data,
            )
            if src_updated:
                logger.info(
                    "Updated %d source %s lines after transfer (target %s #%s)",
                    src_updated, getattr(header_obj, 'parent_model', '?'),
                    model_key, header_id,
                )
                result['source_lines_updated'] = src_updated
        except Exception as src_err:
            logger.warning("Failed to update source lines after transfer: %s", src_err)

    # ── Phase 4: Single dispatch signal after all pending created ────
    if pending_deltas:
        from apps.products.dispatch_pending import dispatch_pending_processing
        dispatch_pending_processing(limit=200, caller='transaction_save')

    # ── Phase 5: Ledger / AR hooks (invoice only) ────────────────────
    # Creates ledger records based on payment terms, updates org aging.
    # Mirrors legacy 4D Ledger_InvSave: delete-and-recreate pattern.
    # Creates a Pending 'ledger_sync' command; marks it processed on success.
    # On failure the Pending stays unprocessed for Celery retry.
    if model_key == 'invoice':
        try:
            from apps.accounts.services.ledger_balance import on_invoice_save
            on_invoice_save(header_obj, replace_ledgers=True)
            logger.info("Ledger sync completed for invoice #%s", header_id)
        except Exception as ledger_err:
            # on_invoice_save already creates an unprocessed Pending internally
            # when the org-balance step fails.  If the *entire* call fails
            # (e.g. term lookup blew up before any ledger was written) we
            # create a retry Pending here so Celery can pick it up.
            logger.warning(
                "Ledger sync failed for invoice #%s: %s — "
                "creating retry Pending for Celery.",
                header_id, ledger_err,
            )
            try:
                from apps.core.models import Pending
                from apps.accounts.services.ledger_balance import PURPOSE_LEDGER_SYNC
                Pending.objects.create(
                    model_name='invoice',
                    record_id=str(header_id),
                    purpose=PURPOSE_LEDGER_SYNC,
                    name=f'Ledger Sync Retry: Invoice {getattr(header_obj, "ida", header_id)}',
                    data={
                        'invoice_id': header_id,
                        'invoice_ida': getattr(header_obj, 'ida', '') or str(header_id),
                        'org_id': getattr(header_obj, 'customer_id', None),
                        'ledger_ids': [],
                        'total_original': 0,
                        'reason': f'phase5_exception: {str(ledger_err)[:200]}',
                    },
                )
            except Exception as pend_err:
                logger.error(
                    "Could not create ledger-sync retry Pending for invoice #%s: %s",
                    header_id, pend_err,
                )

    # ── Phase 6: Erosion detection (invoice, order) ──────────────────
    # Detects margin erosion vs ancestor proposals/orders and discount erosion.
    if model_key in ('invoice', 'order'):
        try:
            from apps.accounts.services.erosion import detect_margin_erosion, detect_discount_erosion
            erosion_events = detect_margin_erosion(header_obj)
            discount_event = detect_discount_erosion(header_obj)
            total_events = len(erosion_events) + (1 if discount_event else 0)
            if total_events:
                logger.info("Erosion: %s event(s) detected for %s #%s", total_events, model_key, header_id)
        except Exception as erosion_err:
            logger.warning("Erosion detection failed for %s #%s: %s", model_key, header_id, erosion_err)

    logger.info(
        "Transaction saved: model=%s header_id=%s lines_saved=%s lines_skipped=%s pending_created=%s",
        model_key, header_id, result['lines_saved'], result['lines_skipped'], len(pending_deltas),
    )

    return result
