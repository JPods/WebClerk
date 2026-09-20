"""Transaction totals recalculation service.

The core totals engine — called after any line change to keep header
totals consistent. Works with all transaction types (quote, order,
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


from common.decimals import safe_decimal as _d  # noqa: E302


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


def is_sell_side(model_name: str) -> bool:
    """Determine if this is a sell-side transaction (has price envelope on lines).

    Single source of truth for sell-side detection by model name.
    Sell-side = quote, order, invoice (and their line variants).
    Exec-side = purchase, workorder, receipt (no price envelope).

    For line-level detection on a model instance, prefer:
        hasattr(line, 'price')
    which is always accurate since BaseSellLineModel defines the price field.
    """
    from apps.transactions.models.base_line_model import _normalize_line_kind
    kind = _normalize_line_kind(model_name)
    return kind in ('quote', 'order', 'invoice')



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

    Works for both sell-side (quote/order/invoice) and exec-side
    (purchase/workorder) transactions.
    """
    header, lines = _resolve_header_and_lines(transaction_id, model_name)
    old_total = (getattr(header, 'totals', None) or {}).get('total', 0)
    computed = compute_totals(header, lines, model_name)
    totals = computed['totals']
    tax_decisions = computed['tax_decisions']

    # ── Tax audit trail ─────────────────────────────────────────────
    if tax_decisions:
        meta = getattr(header, 'metadata', None) or {}
        if not isinstance(meta, dict):
            meta = {}
        meta['tax_decisions'] = {
            'dt': datetime.now(timezone.utc).isoformat(),
            'exempt': computed['is_exempt'],
            'header_rate': computed['header_rate'],
            'jurisdiction': computed['jurisdiction'],
            'lines': tax_decisions,
        }
        header.metadata = meta

    # ── Validate against Pydantic schema (PJPV Layer 1) ─────────
    totals = _validate_totals(totals)

    # ── Persist to header ──────────────────────────────────────────
    header.totals = totals

    update_fields = ['totals']
    if tax_decisions:
        update_fields.append('metadata')
    header.save(update_fields=update_fields)

    # ── Then each line's totals, on the line (after the header save, so a
    #    journalized document's lock stops both) — queryset update, no signals ──
    LineModel = lines.model if hasattr(lines, 'model') else None
    if LineModel is not None:
        for line in lines:
            new = computed['line_totals'].get(line.pk)
            if new is not None and new != (line.totals or {}):
                LineModel.objects.filter(pk=line.pk).update(totals=new)

    # A ledger echoes its primary record: rebuild whenever the total changes.
    if _d(old_total) != _d(totals['total']):
        if model_name == 'invoice':
            from apps.accounts.services.ledger_balance import on_invoice_save
            on_invoice_save(header, replace_ledgers=True)
        elif model_name == 'receipt':                       # AP works as AR does
            from apps.accounts.services.ledger_balance import on_receipt_save
            on_receipt_save(header)

    logger.info(
        "Recalculated totals for %s #%s: amount=%.2f tax=%.2f total=%.2f margin=%.1f%%",
        model_name, transaction_id, totals['amount'], totals['tax'],
        totals['total'], totals['margin_pc'],
    )

    return {
        'amount': totals['amount'],
        'tax': totals['tax'],
        'shipping': totals['shipping'],
        'finance_charge': totals['finance_charge'],
        'total': totals['total'],
        'balance': totals['balance'],
        'margin': totals['margin'],
        'margin_pc': totals['margin_pc'],
        'lines_recalculated': computed['lines_recalculated'],
    }


def _customer_is_exempt(customer_id) -> bool:
    """A customer with a tax exempt code pays no tax on any line.

    Simplification (Bill, 2026-09-19): where exemption is common, the real answer is
    a tax service (a Connection), not a flag. This keeps the common case honest until then.
    """
    if not customer_id:
        return False
    from django.apps import apps as _apps
    fin = (_apps.get_model('orgs', 'OrgBase').objects.filter(pk=customer_id)
           .values_list('financial', flat=True).first()) or {}
    settings = ((fin.get('common') or {}).get('settings') or {})
    return bool(settings.get('tax_exempt') or settings.get('tax_exempt_id'))


def _tax_policy() -> Dict[str, bool]:
    """Company switches (Bill, 2026-09-19), both off by default:
    tax_on_shipping — tax a line's shipping share at the shipping rate;
    tax_on_costs    — tax purchases/costs (VAT-style). Off: no tax on costs at all.
    Company profile config.tax_policy = {"tax_on_shipping": bool, "tax_on_costs": bool}."""
    try:
        from django.apps import apps as _apps
        company = _apps.get_model('core', 'Setting').objects.filter(
            purpose='wc:company_profile').only('config').first()
        policy = ((company.config or {}).get('tax_policy') or {}) if company else {}
    except Exception:
        policy = {}
    return {'tax_on_shipping': bool(policy.get('tax_on_shipping', False)),
            'tax_on_costs': bool(policy.get('tax_on_costs', False))}


LINE_TOTAL_KEYS = ('amount', 'discount', 'taxable', 'tax', 'shipping', 'other',
                   'finance_charge', 'cost', 'margin', 'total')


def _allocate(total: Decimal, weights: List[Decimal]) -> List[Decimal]:
    """Split total into cents by weight; the last share takes the remainder so they add exactly."""
    n = len(weights)
    if n == 0 or total == 0:
        return [Decimal(0)] * n
    base = sum(weights, Decimal(0))
    if base == 0:
        weights, base = [Decimal(1)] * n, Decimal(n)
    shares, given = [], Decimal(0)
    for i, w in enumerate(weights):
        share = total - given if i == n - 1 else _d(total * w / base)
        shares.append(share)
        given += share
    return shares


def _discounted_unit(unit: Decimal, qty: Decimal, pct: Decimal, flat: Decimal, places: int) -> Decimal:
    """The customer's discounted unit price, in the price's precision (Bill: discounted unit first).

    When a line has both a percent and a dollar discount, the larger one applies (Bill,
    2026-09-19). The dollar discount is for the whole line, so per unit it is flat ÷ qty."""
    by_pct = unit * pct / 100
    by_flat = (flat / qty) if qty else Decimal(0)
    return _d(unit - max(by_pct, by_flat, Decimal(0)), places=places)


def compute_totals(header, lines, model_name: str) -> Dict[str, Any]:
    """The one totals calculation. Pure: reads header and lines, writes nothing.

    Bill's line model (2026-09-19): most actions happen on the line, and every
    document number is the sum of the same number on its lines:
        header totals.X = Σ line totals.X
    The customer's discounted unit comes first; the line amount is qty × that unit,
    and the line's discount is derived (gross − amount), so every line ties. The gap
    to an exact percentage is a rounding difference.

    Document-level inputs in header ``allocations`` are spread over the lines:
    discount_percent / discount_amount (by the lines' amounts, as a per-unit
    reduction), shipping and other (exact cents, last line takes the remainder).

    ``header`` and each line may be a model instance or any object with the same
    attributes (the pre-save verifier passes unsaved payload data).

    Returns {'totals', 'line_totals': {pk: {...}}, 'tax_decisions', 'is_exempt',
    'header_rate', 'jurisdiction', 'lines_recalculated'}. ``totals`` is not validated.
    """
    is_sell = is_sell_side(model_name)
    # A soft-deleted or inactive line is not part of the document (recheck 2).
    lines = [l for l in lines
             if not getattr(l, 'is_deleted', False) and getattr(l, 'is_active', True)
             and not ((getattr(l, 'item', None) or {}).get('is_deleted'))]

    finance = getattr(header, 'finance', None) or {}
    header_tax_rate = _d(finance.get('sales_tax_rate', 0), places=6)
    if header_tax_rate > 1:                      # 8.25 is read as 8.25%
        header_tax_rate = header_tax_rate / 100
    tax_envelope = getattr(header, 'tax', None) or {}
    is_exempt = bool(tax_envelope.get('exempt_code') or finance.get('tax_exempt_id') or finance.get('tax_exempt'))
    if not is_exempt:
        is_exempt = _customer_is_exempt(getattr(header, 'customer_id', None))
    tax_jurisdiction_name = finance.get('sales_tax_name', '')
    shipping_tax_rate = _d(tax_envelope.get('shipping', 0) or finance.get('tax_on_shipping_rate', 0), places=6)
    if shipping_tax_rate > 1:
        shipping_tax_rate = shipping_tax_rate / 100
    policy = _tax_policy()
    if is_exempt or not policy['tax_on_shipping']:
        shipping_tax_rate = Decimal(0)

    alloc = getattr(header, 'allocations', None) or {}
    doc_pct = _d(alloc.get('discount_percent', 0), places=6)
    doc_amt = _d(alloc.get('discount_amount', 0))
    doc_shipping = _d(alloc.get('shipping', 0))
    doc_other = _d(alloc.get('other', 0))
    # A receipt's landed costs are its document allocations — the AP mirror of
    # shipping and other on a sell document. They spread over the lines, so what we
    # owe the vendor is still Σ line totals (Bill, 2026-09-19).
    landed = {}
    if model_name == 'receipt':
        landed = {k: _d(alloc.get(k, 0) or 0) for k in ('freight', 'duty', 'handling', 'vat')}
        doc_shipping += landed['freight']
        doc_other += landed['duty'] + landed['handling'] + landed['vat']

    def num(env, key, places=2):
        return _d((env or {}).get(key, 0) or 0, places=places)

    # ── Pass 1: each product line's discounted unit before the document discount ──
    goods = []   # (line, qty, unit, line_unit, places) for product lines
    for line in lines:
        if (getattr(line, 'line_type', 'product') or 'product') != 'product':
            continue
        qty = num(getattr(line, 'quantity', None), 'active', places=6)
        env = (getattr(line, 'price', None) if is_sell else getattr(line, 'cost', None)) or {}
        places = int(env.get('precision', 2) or 2)
        unit = num(env, 'unit', places=6)
        line_unit = _discounted_unit(unit, qty, num(env, 'discount_percent', 6),
                                     num(env, 'discount_amount'), places)
        goods.append((line, qty, unit, line_unit, places))
    # A fixed order, so the remainder always lands on the same line (recheck 2).
    goods.sort(key=lambda g: (getattr(g[0], 'line_number', 0) or 0, getattr(g[0], 'pk', 0) or 0))

    # ── The document discount, as a per-unit reduction ────────────────────
    doc_share = {}
    if is_sell and goods and (doc_pct or doc_amt):
        pre = [_d(q * lu) for (_, q, _, lu, _) in goods]
        # Both set: the larger discount applies (Bill, 2026-09-19).
        if doc_amt and doc_amt >= _d(sum(pre, Decimal(0)) * doc_pct / 100):
            doc_pct = Decimal(0)
            for (line, *_), share in zip(goods, _allocate(doc_amt, pre)):
                doc_share[id(line)] = share

    line_totals: Dict[Any, Dict[str, Any]] = {}
    tax_decisions: List[Dict[str, Any]] = []
    amounts = {}

    for line, qty, unit, line_unit, places in goods:
        if doc_pct:
            du = _d(line_unit * (1 - doc_pct / 100), places=places)
        elif id(line) in doc_share and qty:
            du = _d(line_unit - doc_share[id(line)] / qty, places=places)
        else:
            du = line_unit
        amount = _d(qty * du)
        gross = _d(qty * unit)
        amounts[id(line)] = amount

        cost_env = getattr(line, 'cost', None) or {}
        cplaces = int(cost_env.get('precision', 2) or 2)
        cost_unit = _discounted_unit(num(cost_env, 'unit', 6), qty, num(cost_env, 'discount_percent', 6),
                                     num(cost_env, 'discount_amount'), cplaces)
        cost = _d(qty * cost_unit) if is_sell else amount

        # The line's tax rate: typed on the line, else exempt / non-taxable 0, else the header's
        line_tax_env = getattr(line, 'tax', None) or {}
        typed = num(line_tax_env, 'sales_rate', 6)
        source = line_tax_env.get('rate_source')
        tax_code = (cost_env.get('tax_code', '') or '').upper()
        if source == 'line':
            rate, source = (typed / 100 if typed > 1 else typed), 'line'
        elif not is_sell and not policy['tax_on_costs']:
            rate, source = Decimal(0), 'costs_not_taxed'
        elif is_exempt:
            rate, source = Decimal(0), 'exempt'
        elif tax_code in ('EXEMPT', 'NONTAXABLE', 'NON-TAXABLE'):
            rate, source = Decimal(0), 'item_exempt'
        else:
            rate, source = header_tax_rate, 'header'

        line_totals[id(line)] = {
            'discounted_unit': float(du),
            'amount': amount,
            'discount': gross - amount if is_sell else Decimal(0),
            'taxable': amount if rate > 0 else Decimal(0),
            'tax_rate': float(rate),
            'rate_source': source,
            'tax': _d(amount * rate),
            'shipping': num(cost_env, 'shipping') + num(cost_env, 'handling'),
            'other': Decimal(0),
            'finance_charge': Decimal(0),
            'cost': cost,
        }
        tax_decisions.append({'line_id': getattr(line, 'pk', None), 'rate': float(rate),
                              'taxable': float(amount if rate > 0 else 0),
                              'tax': float(_d(amount * rate)), 'source': source,
                              'jurisdiction': tax_jurisdiction_name})

    # ── Document shipping (+ ship-via % of goods) and other: exact cents by amount ──
    goods_amount = sum(amounts.values(), Decimal(0))
    shipping_to_spread = doc_shipping
    if is_sell:
        from apps.transactions.services.fulfillment.fulfillment_freight import percent_of_goods_shipping
        ship_charge = percent_of_goods_shipping(getattr(header, 'ship_via', '') or '', goods_amount)
        if ship_charge is not None:
            shipping_to_spread += _d(ship_charge)
    weights = [amounts[id(g[0])] for g in goods]
    for (line, *_), s_share, o_share in zip(goods, _allocate(shipping_to_spread, weights), _allocate(doc_other, weights)):
        lt = line_totals[id(line)]
        lt['shipping'] += s_share
        lt['other'] += o_share

    # ── Non-product lines ─────────────────────────────────────────────
    for line in lines:
        lt_type = getattr(line, 'line_type', 'product') or 'product'
        if lt_type == 'product':
            continue
        qty = num(getattr(line, 'quantity', None), 'active', places=6)
        env = (getattr(line, 'price', None) if is_sell else getattr(line, 'cost', None)) or {}
        value = _d(qty * num(env, 'unit', 6))
        t = {k: Decimal(0) for k in LINE_TOTAL_KEYS}
        if lt_type == 'tax':
            t['tax'] = value
        elif lt_type == 'shipping':
            t['shipping'] = value
        elif lt_type == 'finance_charge':
            t['finance_charge'] = value
        elif lt_type == 'discount' and is_sell:
            # Only a settlement (cash) discount reaches here; a document discount lives in
            # allocations. One sign convention: it always reduces.
            t['amount'] = -abs(value)
            t['discount'] = abs(value)
        line_totals[id(line)] = t

    # ── Finish each line: tax on its shipping, margin, total ──────────
    for t in line_totals.values():
        for k in LINE_TOTAL_KEYS:
            t.setdefault(k, Decimal(0))
        if t['shipping'] and shipping_tax_rate:
            t['tax'] += _d(t['shipping'] * shipping_tax_rate)
            t['taxable'] += t['shipping']
        t['margin'] = t['amount'] - t['cost'] if is_sell else Decimal(0)
        t['total'] = t['amount'] + t['tax'] + t['shipping'] + t['other'] + t['finance_charge']

    # ── The document: Σ of its lines ──────────────────────────────────
    doc = {k: sum((t[k] for t in line_totals.values()), Decimal(0)) for k in LINE_TOTAL_KEYS}
    margin_pc = float(_d(doc['margin'] / doc['amount'] * 100)) if doc['amount'] > 0 else 0.0

    existing_totals = getattr(header, 'totals', None) or {}
    received = _d(existing_totals.get('received', 0))
    adjusted = _d(existing_totals.get('adjusted', 0))      # write-offs, small balances, FX
    # AP settles with 'paid' where AR settles with 'received'.
    settled = _d(existing_totals.get('paid', 0)) if model_name == 'receipt' else received
    balance = doc['total'] - settled - adjusted
    state = ''
    if model_name == 'invoice':
        from apps.transactions.services.cash.cash_pending import cash_state
        state = cash_state(doc['total'], received + adjusted)

    totals = {k: float(v) for k, v in doc.items()}
    totals.update({'margin_pc': margin_pc, 'received': float(received), 'adjusted': float(adjusted),
                   'balance': float(balance), 'cash_state': state})
    if model_name == 'receipt':
        totals.update({k: float(v) for k, v in landed.items()})
        totals['paid'] = float(settled)

    by_pk = {}
    for line in lines:
        t = line_totals.get(id(line))
        if t is None:
            continue
        by_pk[getattr(line, 'pk', None)] = {k: (float(v) if isinstance(v, Decimal) else v) for k, v in t.items()}

    return {
        'totals': totals,
        'line_totals': by_pk,
        'tax_decisions': tax_decisions,
        'is_exempt': is_exempt,
        'header_rate': float(header_tax_rate),
        'jurisdiction': tax_jurisdiction_name,
        'lines_recalculated': len(line_totals),
    }


# ---------------------------------------------------------------------------
# update_received — cash-side balance update (PJPV single engine)
# ---------------------------------------------------------------------------

def update_received(
    header,
    new_received: Decimal,
    new_adjusted: Optional[Decimal] = None,
) -> Dict[str, Any]:
    """Update what has been received (money) and adjusted (write-offs, small balances,
    FX) on a transaction header, and recompute balance = total − received − adjusted.

    Called by cash_pending and signals after a cash entry is applied or unapplied.
    This is the ONLY function that should modify totals.received / adjusted /
    balance outside of recalculate_totals(). Does NOT re-sum lines.
    """
    new_received = _d(new_received)
    totals = getattr(header, 'totals', None) or {}
    adjusted = _d(totals.get('adjusted', 0)) if new_adjusted is None else _d(new_adjusted)
    total = _d(totals.get('total', 0))
    new_balance = _d(total - new_received - adjusted)

    from apps.transactions.services.cash.cash_pending import cash_state

    totals['received'] = float(new_received)
    totals['adjusted'] = float(adjusted)
    totals['balance'] = float(new_balance)
    totals['cash_state'] = cash_state(total, new_received + adjusted)
    totals = _validate_totals(totals)
    header.totals = totals

    header.save(update_fields=['totals'])

    logger.info(
        "Updated received for %s #%s: received=%.2f adjusted=%.2f balance=%.2f",
        header._meta.model_name, header.pk, float(new_received), float(adjusted), float(new_balance),
    )

    return {
        'total': float(total),
        'received': float(new_received),
        'adjusted': float(adjusted),
        'balance': float(new_balance),
        'cash_state': totals['cash_state'],
    }


# ---------------------------------------------------------------------------
# update_paid — AP cash-side balance update (mirrors update_received)
# ---------------------------------------------------------------------------

def update_paid(
    header,
    new_paid: Decimal,
) -> Dict[str, Any]:
    """Update the paid amount and recompute balance on a Receipt header.

    AP mirror of update_received(). Called by cash_pending_receipt after
    a cash_out cash is applied or unapplied. This is the ONLY function
    that should modify totals.paid and totals.balance on a Receipt.

    Does NOT re-sum lines — only updates the cash side of the envelope.
    """
    new_paid = _d(new_paid)
    totals = getattr(header, 'totals', None) or {}
    total = _d(totals.get('total', 0))
    new_balance = _d(total - new_paid)

    totals['paid'] = float(new_paid)
    totals['balance'] = float(new_balance)
    header.totals = totals

    header.save(update_fields=['totals'])

    logger.info(
        "Updated paid for %s #%s: paid=%.2f balance=%.2f",
        header._meta.model_name, header.pk, float(new_paid), float(new_balance),
    )

    return {
        'total': float(total),
        'paid': float(new_paid),
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

    Delegates extended computation to the model's save() method, which calls
    ensure_json_defaults() → _calculate_extended_cost() (all lines) and
    _calculate_extended_price() (sell-side lines). Single source of truth.

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

    # Save the line — ensure_json_defaults() recomputes all extended values
    update_fields = ['cost']
    if hasattr(line, 'price'):
        update_fields.append('price')
    line.save(update_fields=update_fields)

    # Build result from the model's computed values
    qty_data = getattr(line, 'quantity', None) or {}
    qty = _d(qty_data.get('active', 0) or 0)
    line_result = {'line_id': line_id, 'quantity': float(qty)}


    # Now recalculate parent totals
    parent = getattr(line, 'parent', None)
    if parent is None:
        return {'line': line_result, 'totals': None, 'message': 'No parent transaction found'}

    parent_model_name = parent._meta.model_name
    parent_id = parent.pk
    totals_result = recalculate_totals(parent_id, parent_model_name)

    return {
        'line': line_result,
        'totals': totals_result,
    }
