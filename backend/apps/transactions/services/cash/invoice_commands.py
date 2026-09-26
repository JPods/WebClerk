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


# ── add_cash: a Cash from the document, applied in the same transaction ─────────────

#: Where the new Cash points, and how it is applied, per document (Bill, 2026-09-26, release #9).
#: amount in the payload is what this document is paid (+) or credited (−). The Cash carries the
#: checkbook sign of its side: AR money in is +, AP money out is −, so a receipt's Cash is −amount.
ADD_CASH_SIDES = {
    'invoice': {'party': 'customer_id', 'link': 'invoice_id', 'cash_sign': 1, 'apply': 'invoice'},
    'receipt': {'party': 'vendor_id', 'link': 'receipt_id', 'cash_sign': -1, 'apply': 'receipt'},
    'order':   {'party': 'customer_id', 'link': None, 'cash_sign': 1, 'apply': None},   # a deposit
}


def add_cash(ctx) -> Dict[str, Any]:
    """POST /wcapi/<invoice|receipt|order>/<id>/add_cash/ {amount ±, method, reference, reason}.

    Bill, 2026-09-26: one service — the Cash is saved through the standard save (save_record,
    as the acting person: their rights, enumerated fields, hooks), then the command base applies
    it. The apply is completely after the save: a refused apply leaves the Cash saved and
    available, and the answer says why it did not apply (Bill's correction, same day). The apply
    runs in its own savepoint, so a refusal undoes only the application.
    An order's Cash is a deposit: unapplied, parent_model='order', and it follows the order to
    its invoice (cash_door.relink_deposits).
    """
    from apps.core.services.save import save_record
    from apps.transactions.models import Cash
    doc = ctx.obj
    model_key = ctx.model_key
    side = ADD_CASH_SIDES[model_key]
    amount = _d(ctx.data.get('amount'))
    if amount == 0:
        raise Refused(400, 'amount_required', 'Say how much: "amount" (+ pays the document, − credits it).')
    party_id = getattr(doc, side['party'], None)
    if not party_id:
        who = 'customer' if side['party'] == 'customer_id' else 'vendor'
        raise Refused(400, f'{who}_required', f'{model_key.title()} {doc.pk} names no {who}; '
                      f'money needs a party.')
    if side['apply']:
        balance = _balance(doc)
        if amount > 0 and amount > balance:     # a credit (−) is judged by the cash door's check
            raise Refused(400, 'amount_exceeds_balance',
                          f'{model_key.title()} {doc.pk} has {balance} open; {amount} was asked. '
                          f'Nothing was added.', {'balance': float(balance), 'amount': float(amount)})
    reason = (ctx.data.get('reason') or '').strip()
    cash_data = {'model_name': 'cash', side['party']: party_id,
                 'amount': str(amount * side['cash_sign']),
                 'method': ctx.data.get('method') or 'manual',
                 'reference_number': ctx.data.get('reference') or '',
                 'status': 'completed'}
    if getattr(doc, 'contact_id', None):
        cash_data['contact_id'] = doc.contact_id
    if side['link']:
        cash_data[side['link']] = doc.pk
    else:
        cash_data.update({'parent_model': model_key, 'parent_id': doc.pk})
    saved = save_record(ctx.actor, cash_data)
    cash = Cash.objects.get(pk=saved.obj_id)
    if reason:
        from apps.core.services.comment_stamp import append_comment
        append_comment(cash, 'process', reason, user=getattr(ctx.actor, 'user_id', None))
        Cash.objects.filter(pk=cash.pk).update(comments=cash.comments)

    applied = None
    if side['apply']:
        from django.db import transaction
        acted_by = getattr(ctx.actor, 'user_id', None)
        why = reason or f'add_cash on {model_key} {doc.pk}'
        try:
            with transaction.atomic():           # the application alone; the Cash stands
                if side['apply'] == 'invoice':
                    applied = _apply(doc, cash.pk, amount, why, acted_by)
                else:
                    from apps.transactions.services.cash.cash_pending_receipt import apply_cash_to_receipt
                    result = apply_cash_to_receipt(cash.pk, doc.pk, amount, reason=why, acted_by=acted_by)
                    applied = {'cash_id': cash.pk, 'amount': float(amount),
                               'state': 'applied' if result.get('applied') else 'queued'}
        except ValueError as e:
            applied = {'cash_id': cash.pk, 'amount': float(amount), 'state': 'refused',
                       'reason': f'Saved, not applied to {model_key} {doc.pk}: {e}. The cash is '
                                 f'available to apply.'}
    doc.refresh_from_db()
    t = doc.totals or {}
    return {'cash_id': cash.pk, 'cash_amount': float(cash.amount), 'applied': applied,
            'deposit': side['apply'] is None,
            'balance': t.get('balance'), 'received': t.get('received'), 'paid': t.get('paid')}


def register() -> None:
    from apps.core.services.verbs import register_command
    register_command('invoice', 'apply_balance', apply_balance)
    for model_key in ADD_CASH_SIDES:
        register_command(model_key, 'add_cash', add_cash)
