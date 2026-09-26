"""Commands on an invoice's money: POST /wcapi/invoice/<id>/apply_balance/.

Bill, 2026-09-26: applying a customer's money to an invoice is ordinary commerce, "nothing
special. Any company should be able to quickly do the same with any customer." One
command, whose payload picks the rule; more rules will follow, each a named case here
(one source, an iteration library of rules — not parallel endpoints).

Rules
- ``oldest`` (no payload): the customer's available Cash, oldest first, up to the invoice
  balance. What it does not cover stays open.
- ``cash`` (``{"cash_id": n, "amount": x}``): that payment's stated amount to this invoice.

Every application goes through ``apply_cash_to_invoice`` — the one checked path (the cash row
lock, the customer match, the journal's available). received is never written here; it is
Σ of the applications (fix #2).

Lock order: the command holds the invoice (run_command locks its record) and then each
cash; the cash-side apply takes cash, then invoice. Two applies racing on one invoice from
opposite sides can deadlock; Postgres aborts one and the caller retries. Named, not hidden.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List

from apps.core.services.door import Refused

RULES = ('oldest', 'cash')


def _d(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal('0.01'))


def _balance(invoice) -> Decimal:
    return _d((invoice.totals or {}).get('balance'))


def _apply(invoice, cash_id: int, amount: Decimal, reason: str, acted_by) -> Dict[str, Any]:
    from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice
    try:
        apply_cash_to_invoice(cash_id, invoice.pk, amount, reason=reason, acted_by=acted_by)
    except ValueError as e:                     # the checked path refused: say so, coached
        raise Refused(409, 'apply_refused', f'Cash {cash_id} was not applied to invoice '
                      f'{invoice.pk}: {e}', {'cash_id': cash_id, 'amount': float(amount)})
    return {'cash_id': cash_id, 'amount': float(amount)}


def _rule_oldest(ctx, invoice, acted_by) -> List[Dict[str, Any]]:
    from apps.transactions.models import Cash
    if not invoice.customer_id:
        raise Refused(400, 'customer_required',
                      f'Invoice {invoice.pk} names no customer, so it has no balance to draw on.')
    remaining = _balance(invoice)
    applied = []
    funds = (Cash.objects.filter(customer_id=invoice.customer_id, available__gt=0)
             .order_by('dt_created', 'pk'))
    for cash in funds:
        if remaining <= 0:
            break
        if not cash.holds_money:
            continue
        take = min(_d(cash.available), remaining)
        applied.append(_apply(invoice, cash.pk, take,
                              ctx.data.get('reason') or 'apply_balance: oldest first', acted_by))
        remaining -= take
    return applied


def _rule_cash(ctx, invoice, acted_by) -> List[Dict[str, Any]]:
    cash_id = ctx.data.get('cash_id')
    amount = _d(ctx.data.get('amount'))
    if not cash_id:
        raise Refused(400, 'cash_id_required', 'Name the payment: {"cash_id": n, "amount": x}.')
    if amount <= 0:
        raise Refused(400, 'amount_required', 'Say how much of the payment to apply: "amount" > 0.')
    balance = _balance(invoice)
    if amount > balance:
        raise Refused(400, 'amount_exceeds_balance',
                      f'Invoice {invoice.pk} has {balance} open; {amount} was asked. Nothing was '
                      f'applied.', {'balance': float(balance), 'amount': float(amount)})
    return [_apply(invoice, int(cash_id), amount,
                   ctx.data.get('reason') or f'apply_balance: cash {cash_id}', acted_by)]


_RULE_FNS = {'oldest': _rule_oldest, 'cash': _rule_cash}


def apply_balance(ctx) -> Dict[str, Any]:
    """Apply a customer's money to this invoice by a rule (see the module docstring)."""
    invoice = ctx.obj
    rule = ctx.data.get('rule') or ('cash' if ctx.data.get('cash_id') else 'oldest')
    if rule not in _RULE_FNS:
        raise Refused(400, 'unknown_rule', f'apply_balance has no rule {rule!r}; rules: '
                      f'{", ".join(RULES)}.', {'rules': list(RULES)})
    acted_by = getattr(ctx.actor, 'user_id', None)
    applied = _RULE_FNS[rule](ctx, invoice, acted_by)
    invoice.refresh_from_db()
    t = invoice.totals or {}
    return {'rule': rule, 'applied': applied, 'received': t.get('received'),
            'balance': t.get('balance'), 'cash_state': t.get('cash_state')}


def register() -> None:
    from apps.core.services.verbs import register_command
    register_command('invoice', 'apply_balance', apply_balance)
