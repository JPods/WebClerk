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

Bill's rulings, 2026-10-22 (classes, review, due date):

- **Due date.** "Net 10 days or as set in company setting record" — the payable is due under the
  Term named at company profile config.small_stings.term, default N10: admin time, but limited.
- **Classes.** The company defines classes of sting (config.small_stings.classes: key, label,
  amount, review). A sting names one, and the class sets its value; an amount that differs from
  the class amount is refused (the company sets the price of a class, not the filer). A sting
  that names no class is worth what it names, else $1.72.
- **Review.** "Create the payable at once, before the review." A class with review=true still
  files its payable and journal at once; the payable is under review and cash is refused
  against it until staff approve. Approve releases it for payment. Reject reverses its journal
  (mirror rows, nothing erased), writes the payable off (totals.adjusted = total, so its ledger
  row stays with nothing available) and closes it. The review state lives on the Action:
  metadata.review.state is the one source of truth (not_required | pending | approved | rejected).
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.utils import timezone

from apps.core.services.door import Actor, Refused

#: A sting that names no value is worth $1.72 (Bill, 2026-10-22).
DEFAULT_STING_AMOUNT = Decimal('1.72')

#: "Net 10 days or as set in company setting record" (Bill, 2026-10-22).
DEFAULT_STING_TERM = 'N10'

#: metadata.review.state on the sting's Action — the one place the review lives.
REVIEW_NOT_REQUIRED, REVIEW_PENDING = 'not_required', 'pending'
REVIEW_APPROVED, REVIEW_REJECTED = 'approved', 'rejected'


def _sting_config() -> Dict[str, Any]:
    """company profile config.small_stings — the term and the classes."""
    from apps.core.models import Setting
    company = Setting.objects.filter(purpose='wc:company_profile', is_active=True).first()
    config = (company.config or {}) if company and isinstance(company.config, dict) else {}
    block = config.get('small_stings') or {}
    if not isinstance(block, dict):
        raise Refused(409, 'sting_config', 'company profile config.small_stings must be an object '
                      '{term, classes}.')
    return block


def sting_term_ida() -> str:
    """The Term a sting's payable is due under: config.small_stings.term, else N10."""
    from apps.accounts.services.terms_ledger import named_term_ida
    named = str(_sting_config().get('term') or '').strip() or DEFAULT_STING_TERM
    try:
        return named_term_ida(named)
    except ValueError as e:
        raise Refused(409, 'sting_term', f'A sting is due under the term in company profile '
                      f'config.small_stings.term (default {DEFAULT_STING_TERM}): {e} Nothing was '
                      f'filed.', {'term': named})


def sting_classes() -> List[Dict[str, Any]]:
    """The company's sting classes, each {key, label, amount (Decimal), review (bool)}.
    A class that is not money above zero is the company's error, refused by name."""
    raw = _sting_config().get('classes') or []
    if not isinstance(raw, list):
        raise Refused(409, 'sting_config', 'company profile config.small_stings.classes must be a '
                      'list of {key, label, amount, review}.')
    classes = []
    for entry in raw:
        key = str((entry or {}).get('key') or '').strip().lower() if isinstance(entry, dict) else ''
        if not key:
            raise Refused(409, 'sting_config', f'A sting class in company profile '
                          f'config.small_stings.classes has no key: {entry!r}.')
        try:
            amount = Decimal(str(entry.get('amount'))).quantize(Decimal('0.01'))
        except (InvalidOperation, ValueError):
            amount = Decimal('0')
        if amount <= 0:
            raise Refused(409, 'sting_config', f'Sting class "{key}" in company profile '
                          f'config.small_stings.classes needs an amount above zero '
                          f'({entry.get("amount")!r} is set).', {'class': key})
        classes.append({'key': key, 'label': str(entry.get('label') or key),
                        'amount': amount, 'review': bool(entry.get('review'))})
    return classes


def _describe(classes) -> str:
    return '; '.join(f'{c["key"]} ({c["label"]}, ${c["amount"]}'
                     f'{", reviewed before payment" if c["review"] else ""})' for c in classes)


def sting_class(key) -> Optional[Dict[str, Any]]:
    """The class a sting names, or None when it names none. An unknown class is refused with
    the classes the company defines."""
    key = str(key or '').strip().lower()
    if not key:
        return None
    classes = sting_classes()
    for c in classes:
        if c['key'] == key:
            return c
    raise Refused(400, 'sting_class', f'"{key}" is not a sting class. '
                  + (f'This company\'s classes: {_describe(classes)}. Or leave the class out '
                     f'for a sting worth what it names (${DEFAULT_STING_AMOUNT} if it names nothing).'
                     if classes else 'This company defines no sting classes (company profile '
                     'config.small_stings.classes); leave the class out.'),
                  {'class': key, 'classes': [c['key'] for c in classes]})


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
                     record_id='', contact_id: Optional[int] = None, amount=None,
                     sting_class_key: str = '') -> Dict[str, Any]:
    """File a sting: the complaint, its payable and its journal, all or nothing.

    ``sting_class_key`` names one of the company's classes; the class sets the amount and
    whether the payable waits for review."""
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
    klass = sting_class(sting_class_key)
    if klass is None:
        amount = sting_amount(amount)
    else:
        named = None if amount in (None, '') else sting_amount(amount)
        if named is not None and named != klass['amount']:
            raise Refused(400, 'sting_amount', f'A "{klass["key"]}" sting is worth '
                          f'${klass["amount"]}, set by the company; {named} was given. Leave the '
                          f'amount out, or leave the class out to name your own.',
                          {'class': klass['key'], 'amount': str(named)})
        amount = klass['amount']
    review = REVIEW_PENDING if klass and klass['review'] else REVIEW_NOT_REQUIRED
    term = sting_term_ida()

    # The payee is always the person who filed it, never their org (Bill, 2026-10-22).
    payee_id = int(contact_id) if contact_id not in (None, '') else actor.user_id
    # Staff may file for someone who phoned it in; a portal user files only for themself.
    from apps.core.services.access import is_portal
    if is_portal(actor) and payee_id != actor.user_id:
        raise Refused(403, 'sting_payee', 'You can file a sting only for yourself; it is owed '
                      'to the person who files it.', {'contact_id': payee_id})
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
            'class': klass['key'] if klass else '', 'term': term,
            'review': {'state': review},
        }})
        action = Action.objects.get(pk=saved.obj_id)

        # 2. The payable. Our own books, written because the sting was filed: the company's
        #    record (a system write through the door), not the filer's to edit.
        system = Actor.system('command')
        saved = save_record(system, {
            'model_name': 'receipt', 'source_type': Receipt.SOURCE_SMALL_STING,
            'contact_id': payee_id, 'parent_model': 'action', 'parent_id': action.pk,
            'terms': term,
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
        'class': klass['key'] if klass else '',
        'term': term,
        'review': review,
        'message': (f'Small-Sting filed: {action.ida}. ${amount} is owed to the filer '
                    f'(receipt {receipt.ida}, {term}); '
                    + ('it is under review: staff approve it before it is paid.'
                       if review == REVIEW_PENDING else
                       'pay it in cash with the receipt\'s add_cash.')),
    }


# ── Review ────────────────────────────────────────────────────────────

def _sting_action(action_id=None, receipt_id=None):
    """The sting's Action, by its id or its receipt's."""
    from apps.core.models import Action
    from apps.transactions.models import Receipt
    if receipt_id not in (None, '') and action_id in (None, ''):
        receipt = Receipt.objects.filter(pk=receipt_id, source_type=Receipt.SOURCE_SMALL_STING).first()
        if receipt is None:
            raise Refused(404, 'sting_not_found', f'Receipt {receipt_id} is not a Small-Sting.')
        action_id = receipt.parent_id
    if action_id in (None, ''):
        raise Refused(400, 'sting_required', 'Name the sting: "action_id" (its STING- Action) or '
                      '"receipt_id" (its payable).')
    action = Action.objects.filter(pk=action_id).first()
    if action is None or (action.metadata or {}).get('type') != 'small_sting':
        raise Refused(404, 'sting_not_found', f'Action {action_id} is not a Small-Sting.')
    return action


def _sting_receipt(action):
    from apps.transactions.models import Receipt
    receipt = Receipt.objects.filter(parent_model='action', parent_id=action.pk,
                                     source_type=Receipt.SOURCE_SMALL_STING).first()
    if receipt is None:
        raise Refused(409, 'sting_payable', f'Sting {action.ida} has no payable.', {'action_id': action.pk})
    return receipt


def review_state(action) -> str:
    return ((action.metadata or {}).get('review') or {}).get('state') or REVIEW_NOT_REQUIRED


def sting_payment_refusal(receipt) -> Optional[str]:
    """Why cash may not be applied to this sting payable yet, or None when it may.
    Read from the sting's Action, where the review lives."""
    if getattr(receipt, 'source_type', None) != 'small_sting' or receipt.parent_model != 'action':
        return None
    from apps.core.models import Action
    action = Action.objects.filter(pk=receipt.parent_id).first()
    state = review_state(action) if action else REVIEW_NOT_REQUIRED
    if state == REVIEW_PENDING:
        return (f'Sting {action.ida} is under review: it is paid once staff approve it '
                f'(manage action approve_small_sting). Nothing was paid.')
    if state == REVIEW_REJECTED:
        return (f'Sting {action.ida} was rejected on review; nothing is owed on it. '
                f'Nothing was paid.')
    return None


def _reviewer(actor: Actor) -> None:
    from apps.core.services.access import is_portal
    if not getattr(actor, 'user_id', None) or is_portal(actor):
        raise Refused(403, 'sting_reviewer', 'Only staff review a sting; it is approved or '
                      'rejected by the company, not by the person who files it.')


def _write_review(actor: Actor, action, state: str, note: str, status: Optional[str] = None,
                  **extra) -> int:
    from apps.core.services.save import save_record
    dt = int(timezone.now().timestamp() * 1000)
    metadata = dict(action.metadata or {})
    metadata['review'] = {**(metadata.get('review') or {}), 'state': state, 'dt_reviewed': dt,
                          'reviewed_by': actor.user_id, 'note': note, **extra}
    data = {'model_name': 'action'}
    if status:
        data['status'] = status
    save_record(actor, data, record_id=action.pk, server_set={'metadata': metadata})
    return dt


def _pending_review(action) -> None:
    state = review_state(action)
    if state != REVIEW_PENDING:
        raise Refused(409, 'sting_not_under_review',
                      f'Sting {action.ida} is not under review (it is {state.replace("_", " ")}).',
                      {'action_id': action.pk, 'state': state})


def approve_small_sting(actor: Actor, *, action_id=None, receipt_id=None, note: str = '') -> Dict[str, Any]:
    """Staff approve a sting under review: its payable is released for payment."""
    _reviewer(actor)
    with transaction.atomic():
        action = _sting_action(action_id, receipt_id)
        _pending_review(action)
        receipt = _sting_receipt(action)
        dt = _write_review(actor, action, REVIEW_APPROVED, (note or '').strip())
    return {'success': True, 'action_id': action.pk, 'action_ida': action.ida,
            'receipt_id': receipt.pk, 'review': REVIEW_APPROVED, 'dt_reviewed': dt,
            'message': f'Sting {action.ida} approved: receipt {receipt.ida} may now be paid in cash.'}


def reject_small_sting(actor: Actor, *, action_id=None, receipt_id=None, reason: str = '') -> Dict[str, Any]:
    """Staff reject a sting under review. Its journal is reversed (mirror rows — the original
    and its reversal both stay), its payable is written off and closed; nothing is deleted."""
    from apps.accounts.services.ledger_balance import reverse_gl_entries
    from apps.core.services.comment_stamp import append_comment
    from apps.transactions.models import Receipt
    from apps.transactions.services.cash.cash_pending_receipt import _applied, refresh_receipt_paid

    _reviewer(actor)
    reason = (reason or '').strip()
    if not reason:
        raise Refused(400, 'reason_required', 'Say why the sting is rejected: "reason" is kept '
                      'on the sting and its payable.')
    with transaction.atomic():
        action = _sting_action(action_id, receipt_id)
        _pending_review(action)
        receipt = Receipt.objects.select_for_update().get(pk=_sting_receipt(action).pk)
        if _applied(receipt_id=receipt.pk):
            raise Refused(409, 'sting_paid', f'Sting {action.ida} has cash applied; reverse the '
                          f'payment before rejecting it.', {'receipt_id': receipt.pk})
        reversed_rows = reverse_gl_entries(receipt, reason=f'Small-Sting rejected: {reason}')
        if not reversed_rows:
            raise Refused(409, 'sting_journal', f'Sting {action.ida} has no standing journal to '
                          f'reverse; nothing was rejected.', {'receipt_id': receipt.pk})
        # Closed, not deleted: written off in full, so its ledger row stays with nothing open.
        # dt_journaled stays set — the rejected payable is final, and is not posted again.
        totals = dict(receipt.totals or {})
        totals['adjusted'] = totals.get('total') or 0
        receipt.totals = totals
        receipt.status = 'canceled'
        append_comment(receipt, 'process', f'Small-Sting rejected on review: {reason}',
                       user=actor.user_id, source='small_sting_review')
        receipt.save(update_fields=['totals', 'status', 'comments', 'dt_modified', 'version'])
        refresh_receipt_paid(receipt)
        dt = _write_review(actor, action, REVIEW_REJECTED, reason, status='canceled',
                           reversed_rows=reversed_rows)
    return {'success': True, 'action_id': action.pk, 'action_ida': action.ida,
            'receipt_id': receipt.pk, 'review': REVIEW_REJECTED, 'dt_reviewed': dt,
            'reversed_rows': reversed_rows,
            'message': f'Sting {action.ida} rejected: its journal is reversed and receipt '
                       f'{receipt.ida} is closed with nothing owed.'}
