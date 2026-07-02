"""Transaction totals recalculation service.

The core totals engine — called after any line change to keep header
totals consistent. Works with all transaction types (proposal, order,
invoice, purchase, workorder).

All calculations are server-side authoritative (Axiom: backend is source of truth).

See: readmes/topics/transactions/transactions-totals.md
"""
import logging
from decimal import Decimal
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _d(x: Any, places: int = 2) -> Decimal:
    """Safe Decimal coercion with rounding."""
    try:
        d = Decimal(str(x))
        return d.quantize(Decimal(10) ** -places) if places >= 0 else d
    except Exception:
        return Decimal(0)


# ---------------------------------------------------------------------------
# Model resolution helpers
# ---------------------------------------------------------------------------

def _resolve_header_and_lines(transaction_id: int, model_name: str):
    """Load the header and its lines. Returns (header, lines_queryset).

    Handles all transaction types via the model registry.
    """
    from apps.core.constants.model_registry import get_model_meta

    meta = get_model_meta(model_name)
    if not meta:
        raise ValueError(f"Unknown model: {model_name}")

    HeaderModel = meta.import_model()
    try:
        header = HeaderModel.objects.get(pk=transaction_id)
    except HeaderModel.DoesNotExist:
        raise ValueError(f"{model_name} #{transaction_id} not found")

    if not hasattr(header, 'lines'):
        raise ValueError(f"{model_name} #{transaction_id} has no lines relation")

    return header, header.lines.all()


def _is_sell_side(model_name: str) -> bool:
    """Determine if this is a sell-side transaction (has price envelope on lines)."""
    sell_types = {'proposal', 'order', 'invoice', 'proposal_line', 'order_line', 'invoice_line'}
    return model_name.lower().replace('-', '_') in sell_types


# ---------------------------------------------------------------------------
# recalculate_totals — the core function
# ---------------------------------------------------------------------------

def recalculate_totals(
    transaction_id: int,
    model_name: str,
) -> Dict[str, Any]:
    """Recalculate all totals for a transaction header.

    Called after any line change (add, update, delete).

    Steps:
      1. Load all lines for the transaction
      2. For each line: compute extended price/cost, sum tax, sum shipping
      3. Calculate header totals: subtotal, tax, shipping, total, margin
      4. Update header: totals JSON, total and balance (denormalized decimals)
      5. Return the computed totals

    Works for both sell-side (proposal/order/invoice) and exec-side
    (purchase/workorder) transactions.
    """
    header, lines = _resolve_header_and_lines(transaction_id, model_name)
    is_sell = _is_sell_side(model_name)

    # Accumulators
    subtotal = Decimal(0)       # sum of line extended sell prices
    cost_total = Decimal(0)     # sum of line extended costs
    tax_total = Decimal(0)      # sum of line taxes
    shipping_total = Decimal(0) # sum of line shipping + handling
    discount_total = Decimal(0) # sum of line discounts
    lines_recalculated = 0

    for line in lines:
        qty_data = getattr(line, 'quantity', None) or {}
        qty = _d(qty_data.get('staged', 0) or qty_data.get('active', 0) or 0)

        # ── Sell side (price envelope) ─────────────────────────────────
        if is_sell:
            price_data = getattr(line, 'price', None) or {}
            unit_price = _d(price_data.get('unit', 0))
            price_extended = _d(qty * unit_price)
            discount_amt = _d(price_data.get('discount_amount', 0))
            subtotal += price_extended - discount_amt
            discount_total += discount_amt

        # ── Cost side ──────────────────────────────────────────────────
        cost_data = getattr(line, 'cost', None) or {}
        unit_cost = _d(cost_data.get('unit', 0))
        cost_extended = _d(qty * unit_cost)
        cost_total += cost_extended

        # Cost-side surcharges
        shipping_total += _d(cost_data.get('shipping', 0))
        shipping_total += _d(cost_data.get('handling', 0))

        # ── Tax ────────────────────────────────────────────────────────
        tax_data = getattr(line, 'tax', None) or {}
        tax_total += _d(tax_data.get('sales', 0))

        lines_recalculated += 1

    # If exec-side (purchase/workorder), subtotal is the cost total
    if not is_sell:
        subtotal = cost_total

    # Header-level cost freight (separate from line shipping)
    header_cost = getattr(header, 'cost', None) or {}
    header_freight = _d(header_cost.get('freight', 0))
    shipping_total += header_freight

    # ── Calculate header tax from rate if no line-level tax ────────
    # If tax_total is still 0 but header has a tax rate, apply it
    finance = getattr(header, 'finance', None) or {}
    if tax_total == 0 and finance.get('sales_tax_rate'):
        header_tax_rate = _d(finance['sales_tax_rate'], places=6)
        # Normalize: if rate > 1, treat as percentage
        if header_tax_rate > 1:
            header_tax_rate = header_tax_rate / 100
        taxable = subtotal - discount_total
        tax_total = _d(taxable * header_tax_rate)

    # ── Grand total ────────────────────────────────────────────────
    total = subtotal + tax_total + shipping_total
    margin = subtotal - cost_total
    margin_pc = float(_d((margin / subtotal * 100))) if subtotal > 0 else 0.0

    # ── Received / balance (for invoices) ──────────────────────────
    existing_totals = getattr(header, 'totals', None) or {}
    received = _d(existing_totals.get('received', 0))
    balance = total - received

    # ── Build the totals dict ──────────────────────────────────────
    totals = {
        'subtotal': float(subtotal),
        'discount': float(discount_total),
        'taxable': float(subtotal - discount_total),
        'tax': float(tax_total),
        'shipping': float(shipping_total),
        'other': float(_d(existing_totals.get('other', 0))),
        'total': float(total),
        'cost': float(cost_total),
        'margin': float(margin),
        'margin_pc': margin_pc,
        'received': float(received),
        'balance': float(balance),
    }

    # ── Persist to header ──────────────────────────────────────────
    header.totals = totals
    header.total = _d(total)
    header.balance = _d(balance)

    update_fields = ['totals', 'total', 'balance']
    header.save(update_fields=update_fields)

    logger.info(
        "Recalculated totals for %s #%s: subtotal=%.2f tax=%.2f total=%.2f margin=%.1f%%",
        model_name, transaction_id, float(subtotal), float(tax_total),
        float(total), margin_pc,
    )

    return {
        'subtotal': float(subtotal),
        'tax': float(tax_total),
        'shipping': float(shipping_total),
        'total': float(total),
        'balance': float(balance),
        'margin': float(margin),
        'margin_pc': margin_pc,
        'lines_recalculated': lines_recalculated,
    }


# ---------------------------------------------------------------------------
# recalculate_line — single line recalc + parent totals update
# ---------------------------------------------------------------------------

def recalculate_line(
    line_id: int,
    model_name: str,
) -> Dict[str, Any]:
    """Recalculate a single line's extended values and update parent totals.

    Recomputes price.extended and cost.extended from qty and unit values,
    then calls recalculate_totals on the parent transaction.

    Returns the line-level result plus the parent totals result.
    """
    from apps.core.constants.model_registry import get_model_meta

    meta = get_model_meta(model_name)
    if not meta:
        raise ValueError(f"Unknown line model: {model_name}")

    LineModel = meta.import_model()
    try:
        line = LineModel.objects.get(pk=line_id)
    except LineModel.DoesNotExist:
        raise ValueError(f"{model_name} #{line_id} not found")

    # Get quantity
    qty_data = getattr(line, 'quantity', None) or {}
    qty = _d(qty_data.get('staged', 0) or qty_data.get('active', 0) or 0)

    line_result = {'line_id': line_id, 'quantity': float(qty)}

    # Recalc price.extended (sell-side lines)
    if hasattr(line, 'price') and isinstance(line.price, dict):
        unit_price = _d(line.price.get('unit', 0))
        discount_pct = _d(line.price.get('discount_percent', 0))
        gross = _d(qty * unit_price)
        discount_amt = _d(gross * discount_pct / 100) if discount_pct else _d(line.price.get('discount_amount', 0))
        extended = float(_d(gross - discount_amt))
        line.price['discount_amount'] = float(discount_amt)
        line.price['extended'] = extended
        line_result['price_extended'] = extended

    # Recalc cost.extended
    if hasattr(line, 'cost') and isinstance(line.cost, dict):
        unit_cost = _d(line.cost.get('unit', 0))
        cost_discount_pct = _d(line.cost.get('discount_percent', 0))
        gross_cost = _d(qty * unit_cost)
        cost_discount_amt = _d(gross_cost * cost_discount_pct / 100) if cost_discount_pct else _d(line.cost.get('discount_amount', 0))
        cost_extended = float(_d(gross_cost - cost_discount_amt))
        line.cost['discount_amount'] = float(cost_discount_amt)
        line.cost['extended'] = cost_extended
        line_result['cost_extended'] = cost_extended

    # Save the line
    update_fields = []
    if hasattr(line, 'price'):
        update_fields.append('price')
    if hasattr(line, 'cost'):
        update_fields.append('cost')
    if update_fields:
        line.save(update_fields=update_fields)

    # Now recalculate parent totals
    parent = getattr(line, 'parent', None)
    if parent is None:
        return {'line': line_result, 'totals': None, 'message': 'No parent transaction found'}

    # Determine parent model_name from the parent object
    parent_model_name = parent._meta.model_name
    parent_id = parent.pk

    totals_result = recalculate_totals(parent_id, parent_model_name)

    return {
        'line': line_result,
        'totals': totals_result,
    }
