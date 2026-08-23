"""Transaction totals recalculation service.

The core totals engine — called after any line change to keep header
totals consistent. Works with all transaction types (proposal, order,
invoice, purchase, workorder).

All calculations are server-side authoritative (Axiom: backend is source of truth).
Output validated against TransactionTotals Pydantic schema (PJPV Layer 1).

See: readmes/topics/transactions/transactions-totals.md
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _validate_totals(totals: Dict[str, Any]) -> Dict[str, Any]:
    """Validate totals dict against TransactionTotals Pydantic schema.

    Fail-hard: if the schema rejects the data, the save fails. If we fail,
    we fix. Soft fallbacks hide problems — hard failures surface them.
    Promoted from fail-open 2026-08-23.
    """
    from common.schemas.transaction_envelopes import TransactionTotals
    validated = TransactionTotals(**totals)
    return validated.model_dump()


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

    # Resolve header tax rate for per-line application
    finance = getattr(header, 'finance', None) or {}
    header_tax_rate = _d(finance.get('sales_tax_rate', 0), places=6)
    # Normalize: if rate > 1, treat as percentage (e.g., 8.25 → 0.0825)
    if header_tax_rate > 1:
        header_tax_rate = header_tax_rate / 100
    # Check if transaction is tax exempt
    tax_envelope = getattr(header, 'tax', None) or {}
    is_exempt = bool(tax_envelope.get('exempt_code'))
    tax_jurisdiction_name = finance.get('sales_tax_name', '')
    tax_decisions: List[Dict[str, Any]] = []

    for line in lines:
        qty_data = getattr(line, 'quantity', None) or {}
        qty = _d(qty_data.get('staged', 0) or qty_data.get('active', 0) or 0)
        cost_data = getattr(line, 'cost', None) or {}
        lt = getattr(line, 'line_type', 'product') or 'product'

        # ── Route by line_type ────────────────────────────────────────
        # tax      → extended goes to tax_total (special taxes: environmental, recycling, etc.)
        # shipping → extended goes to shipping_total (freight lines, handling charges)
        # discount → extended subtracts from subtotal
        # product  → normal: extended goes to subtotal, taxed at header rate

        if lt == 'tax':
            # Special tax line — amount routes directly to tax total
            unit = _d(cost_data.get('unit', 0))
            if is_sell:
                price_data = getattr(line, 'price', None) or {}
                unit = _d(price_data.get('unit', 0)) or unit
            tax_total += _d(qty * unit)
            lines_recalculated += 1
            continue

        if lt == 'shipping':
            # Shipping/freight line — amount routes to shipping total
            unit = _d(cost_data.get('unit', 0))
            if is_sell:
                price_data = getattr(line, 'price', None) or {}
                unit = _d(price_data.get('unit', 0)) or unit
            shipping_total += _d(qty * unit)
            lines_recalculated += 1
            continue

        # ── Product and discount lines ────────────────────────────────
        price_extended = Decimal(0)
        discount_amt = Decimal(0)

        if is_sell:
            price_data = getattr(line, 'price', None) or {}
            unit_price = _d(price_data.get('unit', 0))
            price_extended = _d(qty * unit_price)
            discount_amt = _d(price_data.get('discount_amount', 0))
            if lt == 'discount':
                subtotal -= price_extended
                discount_total += price_extended
            else:
                subtotal += price_extended - discount_amt
                discount_total += discount_amt

        # ── Cost side ──────────────────────────────────────────────────
        unit_cost = _d(cost_data.get('unit', 0))
        cost_extended = _d(qty * unit_cost)
        if lt != 'discount':
            cost_total += cost_extended

        # Cost-side surcharges (on product lines only)
        shipping_total += _d(cost_data.get('shipping', 0))
        shipping_total += _d(cost_data.get('handling', 0))

        # ── Tax (per product line) ────────────────────────────────────
        # Priority: line-level tax override > header rate > zero
        # If customer is exempt, all lines are zero tax.
        # If item is non-taxable (cost.tax_code == 'EXEMPT' or 'NONTAXABLE'), skip.
        if lt == 'product':
            line_tax_data = getattr(line, 'tax', None) or {}
            line_tax_rate_override = _d(line_tax_data.get('sales_rate', 0), places=6)
            line_tax_sales = _d(line_tax_data.get('sales', 0))

            if line_tax_rate_override > 0:
                # Line has explicit tax rate override (user set per-line rate)
                if line_tax_rate_override > 1:
                    line_tax_rate_override = line_tax_rate_override / 100
                line_taxable = price_extended - discount_amt if is_sell else cost_extended
                line_tax = _d(line_taxable * line_tax_rate_override)
                tax_total += line_tax
                tax_decisions.append({
                    'line_id': getattr(line, 'pk', None),
                    'rate': float(line_tax_rate_override),
                    'taxable': float(line_taxable),
                    'tax': float(line_tax),
                    'source': 'line_override',
                    'jurisdiction': tax_jurisdiction_name,
                })
            elif line_tax_sales > 0:
                # Line has explicit tax amount (user override or prior calc)
                tax_total += line_tax_sales
                tax_decisions.append({
                    'line_id': getattr(line, 'pk', None),
                    'rate': None,
                    'taxable': None,
                    'tax': float(line_tax_sales),
                    'source': 'line_amount',
                    'jurisdiction': tax_jurisdiction_name,
                })
            elif not is_exempt and header_tax_rate > 0:
                line_tax_code = (cost_data.get('tax_code', '') or '').upper()
                item_exempt = line_tax_code in ('EXEMPT', 'NONTAXABLE', 'NON-TAXABLE')
                if not item_exempt:
                    line_taxable = price_extended - discount_amt if is_sell else cost_extended
                    line_tax = _d(line_taxable * header_tax_rate)
                    tax_total += line_tax
                    tax_decisions.append({
                        'line_id': getattr(line, 'pk', None),
                        'rate': float(header_tax_rate),
                        'taxable': float(line_taxable),
                        'tax': float(line_tax),
                        'source': 'header_rate',
                        'jurisdiction': tax_jurisdiction_name,
                    })
                else:
                    tax_decisions.append({
                        'line_id': getattr(line, 'pk', None),
                        'rate': 0,
                        'taxable': 0,
                        'tax': 0,
                        'source': 'item_exempt',
                        'jurisdiction': tax_jurisdiction_name,
                    })

        lines_recalculated += 1

    # If exec-side (purchase/workorder), subtotal is the cost total
    if not is_sell:
        subtotal = cost_total

    # Header-level cost freight (separate from line shipping)
    header_cost = getattr(header, 'cost', None) or {}
    header_freight = _d(header_cost.get('freight', 0))
    shipping_total += header_freight

    # ── Tax on shipping (WC2: <>aTaxRateShipping per jurisdiction) ─
    # finance.tax_on_shipping_rate or tax.shipping carries the rate
    shipping_tax_rate = _d(tax_envelope.get('shipping', 0) or finance.get('tax_on_shipping_rate', 0), places=6)
    if shipping_tax_rate > 1:
        shipping_tax_rate = shipping_tax_rate / 100
    if not is_exempt and shipping_tax_rate > 0 and shipping_total > 0:
        tax_total += _d(shipping_total * shipping_tax_rate)

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

    # ── Tax audit trail ─────────────────────────────────────────────
    if tax_decisions:
        meta = getattr(header, 'metadata', None) or {}
        if not isinstance(meta, dict):
            meta = {}
        meta['tax_decisions'] = {
            'dt': datetime.now(timezone.utc).isoformat(),
            'exempt': is_exempt,
            'header_rate': float(header_tax_rate),
            'jurisdiction': tax_jurisdiction_name,
            'lines': tax_decisions,
        }
        header.metadata = meta

    # ── Validate against Pydantic schema (PJPV Layer 1) ─────────
    totals = _validate_totals(totals)

    # ── Persist to header ──────────────────────────────────────────
    header.totals = totals
    header.total = _d(total)
    header.balance = _d(balance)

    update_fields = ['totals', 'total', 'balance']
    if tax_decisions:
        update_fields.append('metadata')
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
# update_received — payment-side balance update (PJPV single engine)
# ---------------------------------------------------------------------------

def update_received(
    header,
    new_received: Decimal,
) -> Dict[str, Any]:
    """Update the received amount and recompute balance on a transaction header.

    Called by payment_application, payment_pending, and signals after a payment
    is applied or unapplied. This is the ONLY function that should modify
    totals.received and totals.balance outside of recalculate_totals().

    Does NOT re-sum lines — only updates the payment side of the envelope.
    """
    new_received = _d(new_received)
    totals = getattr(header, 'totals', None) or {}
    total = _d(totals.get('total', 0))
    new_balance = _d(total - new_received)

    totals['received'] = float(new_received)
    totals['balance'] = float(new_balance)
    totals = _validate_totals(totals)
    header.totals = totals
    header.total = _d(total)
    header.balance = new_balance

    header.save(update_fields=['totals', 'total', 'balance'])

    logger.info(
        "Updated received for %s #%s: received=%.2f balance=%.2f",
        header._meta.model_name, header.pk, float(new_received), float(new_balance),
    )

    return {
        'total': float(total),
        'received': float(new_received),
        'balance': float(new_balance),
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
