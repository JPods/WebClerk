"""Small-Stings — a fine a customer assesses on us for an unresolved problem.

Bill, 2026-10-22: every Small-Sting creates a payable. It is a P&L event, owed to the person
who filed it, and settled by a cash payment ("we want to force visibility") — it ages and is
paid like any payable, never credited against an invoice.

Filing writes, in one transaction or not at all:

1. the **Action** — the complaint, as the person filing it (their rights, through the door);
2. the **payable** — a Receipt with source_type 'small_sting': contact = the filer, no vendor,
   parent = the Action, one line with no item (the sting's ida and complaint) at its amount.
   Received, so its total is Σ lines, and its Ledger row names the filer as payee;
3. the **journal** — Dr 6550-small_sting_expense / Cr 2230-small_stings_payable, by the one
   posting path (journalize_receipt).

Paying it is the receipt's add_cash (POST /wcapi/receipt/<id>/add_cash/): the payment names
the filer, and posts Dr 2230 / Cr cash. The payable and its journal are the record; nothing
else is written for it.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional

from django.db import transaction
from django.utils import timezone

from apps.core.services.door import Actor, Refused

#: A sting that names no value is worth $1.72 (Bill, 2026-10-22).
DEFAULT_STING_AMOUNT = Decimal('1.72')


def sting_amount(raw) -> Decimal:
    """The sting's value: what it names, else $1.72. Refused unless it is money above zero."""
    if raw in (None, ''):
        return DEFAULT_STING_AMOUNT
    try:
        amount = Decimal(str(raw)).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError):
        raise Refused(400, 'sting_amount', f'"{raw}" is not an amount. Leave it out for the '
                      f'${DEFAULT_STING_AMOUNT} default.', {'amount': str(raw)})
    if amount <= 0:
        raise Refused(400, 'sting_amount', f'A sting is worth more than nothing ({amount} was '
                      f'given). Leave it out for the ${DEFAULT_STING_AMOUNT} default.',
                      {'amount': str(amount)})
    return amount


def file_small_sting(actor: Actor, *, complaint: str, severity=3, model_name: str = '',
                     record_id='', contact_id: Optional[int] = None, amount=None) -> Dict[str, Any]:
    """File a sting: the complaint, its payable and its journal, all or nothing."""
    from apps.accounts.services.journalize import journalize_receipt
    from apps.accounts.services.terms_ledger import apply_terms_for_payable
    from apps.accounts.models import Ledger
    from apps.core.models import Action, Contact
    from apps.core.services.save import save_record
    from apps.transactions.models import Receipt
    from apps.transactions.services.receive_commands import receive_receipt

    complaint = (complaint or '').strip()
    if not complaint:
        raise Refused(400, 'complaint_required', 'Say what went wrong: "complaint" is required.')
    try:
        severity = min(max(int(severity), 1), 5)
    except (TypeError, ValueError):
        raise Refused(400, 'severity', f'severity is 1 (minor) to 5 (business-stopping); '
                      f'"{severity}" was given.')
    amount = sting_amount(amount)

    # The payee is always the person who filed it, never their org (Bill, 2026-10-22).
    payee_id = int(contact_id) if contact_id not in (None, '') else actor.user_id
    if not payee_id or not Contact.objects.filter(pk=payee_id).exists():
        raise Refused(400, 'payee_required', 'A sting is owed to the person who filed it: sign in, '
                      'or name the filing contact ("contact_id").', {'contact_id': payee_id})

    now = timezone.now()
    ida = f'STING-{now.strftime("%Y%m%dT%H%M%S")}{now.microsecond // 1000:03d}'   # two in a second stay two
    with transaction.atomic():
        # 1. The complaint, as the person filing it.
        saved = save_record(actor, {
            'model_name': 'action', 'status': 'open', 'priority': severity,
            'action': f'Small-Sting: {complaint[:100]}', 'description': complaint,
            'contact_id': payee_id,
        }, server_set={'ida': ida, 'metadata': {
            'type': 'small_sting', 'severity': severity, 'model_name': model_name or '',
            'record_id': str(record_id) if record_id else '', 'amount': str(amount),
            'dt_filed': int(now.timestamp() * 1000), 'source': {'type': 'user_complaint'},
        }})
        action = Action.objects.get(pk=saved.obj_id)

        # 2. The payable. Our own books, written because the sting was filed: the company's
        #    record (a system write through the door), not the filer's to edit.
        system = Actor.system('command')
        saved = save_record(system, {
            'model_name': 'receipt', 'source_type': Receipt.SOURCE_SMALL_STING,
            'contact_id': payee_id, 'parent_model': 'action', 'parent_id': action.pk,
            'lines': [{'item': {'description': f'{action.ida}: {complaint}'[:500]},
                       'quantity': {'staged': 1},
                       'cost': {'unit': float(amount), 'precision': 2}}],
        })
        receipt = Receipt.objects.get(pk=saved.obj_id)
        receive_receipt(receipt, actor=system)
        receipt.refresh_from_db()
        total = Decimal(str((receipt.totals or {}).get('total') or 0)).quantize(Decimal('0.01'))
        if total != amount:
            raise Refused(500, 'sting_payable', f'The sting payable came to {total}, not {amount}; '
                          f'nothing was filed.', {'receipt_id': receipt.pk})
        try:
            apply_terms_for_payable(receipt, replace=True)   # raise here, not in a signal's log
        except ValueError as e:
            raise Refused(409, 'sting_payable', f'The sting could not be made payable: {e}. '
                          f'Nothing was filed.')
        if not Ledger.objects.filter(parent_id=receipt.pk, model_name='receipt',
                                     contact_id=payee_id).exists():
            raise Refused(500, 'sting_payable', 'The sting payable wrote no ledger row for its '
                          'payee; nothing was filed.', {'receipt_id': receipt.pk})

        # 3. The journal: Dr small_sting_expense / Cr small_stings_payable.
        try:
            posted = journalize_receipt(receipt.pk)
        except Exception as e:                         # an unmapped role is UndefinedAccountError
            raise Refused(409, 'sting_journal', f'The sting could not be posted: {e} Nothing was '
                          f'filed.')
        if not posted.get('created'):
            raise Refused(409, 'sting_journal', f'The sting could not be posted: '
                          f'{posted.get("error") or "nothing posted"}. Nothing was filed.')

    return {
        'success': True,
        'action_id': action.pk,
        'action_ida': action.ida,
        'receipt_id': receipt.pk,
        'receipt_ida': receipt.ida,
        'payee_contact_id': payee_id,
        'amount': float(amount),
        'message': f'Small-Sting filed: {action.ida}. ${amount} is owed to the filer '
                   f'(receipt {receipt.ida}); pay it in cash with the receipt\'s add_cash.',
    }
