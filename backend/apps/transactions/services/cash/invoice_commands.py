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
cash, in pk order; the cash-side apply (and a card settling) takes cash, then invoice. Two
applies racing on one invoice from opposite sides can deadlock; Postgres aborts one and the
caller retries. The full fix lets a command lock its cash before the record (run_command);
recorded as an open item, not hidden (Fable, 2026-09-26).
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
    """One application through the checked path. ValueError when it refuses; the result says
    whether it applied or only queued (Pending._apply_cash queues only on a locked row; any
    other failure raises)."""
    from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice
    result = apply_cash_to_invoice(cash_id, invoice.pk, amount, reason=reason, acted_by=acted_by)
    return {'cash_id': cash_id, 'amount': float(amount),
            'state': 'applied' if result.get('applied') else 'queued'}


def _rule_oldest(ctx, invoice, acted_by) -> List[Dict[str, Any]]:
    from apps.transactions.models import Cash
    if not invoice.customer_id:
        raise Refused(400, 'customer_required',
                      f'Invoice {invoice.pk} names no customer, so it has no balance to draw on.')
    from django.db import transaction
    from apps.transactions.services.cash.cash_pending import _queued_net, refresh_cash_available
    remaining = _balance(invoice)
    applied = []
    ids = list(Cash.objects.filter(customer_id=invoice.customer_id, available__gt=0)
               .values_list('pk', flat=True))
    # Locked in pk order (one order for every caller), then used oldest first.
    funds = list(Cash.objects.select_for_update().filter(pk__in=ids).order_by('pk'))
    funds.sort(key=lambda c: (c.dt_created or 0, c.pk))
    reason = ctx.data.get('reason') or 'apply_balance: oldest first'
    for cash in funds:
        if remaining <= 0:
            break
        if not cash.holds_money:
            continue
        # What the journal says it has now, less what is already queued (not the pre-read number).
        take = min(refresh_cash_available(cash, before_use=True) - _queued_net(cash), remaining)
        if take <= 0:
            continue
        try:
            with transaction.atomic():          # a refused application undoes only itself;
                entry = _apply(invoice, cash.pk, take, reason, acted_by)   # the rest stands
        except ValueError as e:
            applied.append({'cash_id': cash.pk, 'amount': float(take), 'state': 'refused',
                            'reason': str(e)})
            continue
        applied.append(entry)
        if entry['state'] == 'applied':
            remaining -= take
    return applied


def _rule_cash(ctx, invoice, acted_by) -> List[Dict[str, Any]]:
    cash_id = ctx.data.get('cash_id')
    amount = _d(ctx.data.get('amount'))
    if not cash_id:
        raise Refused(400, 'cash_id_required', 'Name the payment: {"cash_id": n, "amount": x}.')
    if amount <= 0:
        raise Refused(400, 'amount_required', 'Say how much of the payment to apply: "amount" > 0.')
    _may_use_cash(ctx.actor, int(cash_id))
    balance = _balance(invoice)
    if amount > balance:
        raise Refused(400, 'amount_exceeds_balance',
                      f'Invoice {invoice.pk} has {balance} open; {amount} was asked. Nothing was '
                      f'applied.', {'balance': float(balance), 'amount': float(amount)})
    try:
        return [_apply(invoice, int(cash_id), amount,
                       ctx.data.get('reason') or f'apply_balance: cash {cash_id}', acted_by)]
    except ValueError as e:                     # the named payment was refused: coached 409
        raise Refused(409, 'apply_refused', f'Cash {cash_id} was not applied to invoice '
                      f'{invoice.pk}: {e}', {'cash_id': cash_id, 'amount': float(amount)})


def _may_use_cash(actor, cash_id: int) -> None:
    """Naming a payment moves a Cash record: the actor must see it and may edit Cash (the
    invoice edit that run_command checked is not enough — Fable). A guarded actor naming a
    payment it cannot see gets 404, never another party's details."""
    if not getattr(actor, 'is_guarded', False):
        return
    from apps.core.services.record_serialize import visible_queryset
    from apps.core.services.role_filter import get_user_filter_config
    if not visible_queryset('cash', actor=actor)[1].filter(pk=cash_id).exists():
        raise Refused(404, 'not_found', 'Payment not found', {'cash_id': cash_id})
    if not (get_user_filter_config(actor, 'cash') or {}).get('edit'):
        raise Refused(403, 'edit_not_permitted', 'Your role may not apply payments.', 'cash')


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
