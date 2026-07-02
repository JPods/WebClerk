"""
Credit Check Service — warnings, not barriers.

Credit limits are advisory. Violating them requires user acknowledgement,
stored as an audit trail in transaction.metadata.credit_warnings[].

Never blocks a transaction. Only warns.
"""
from __future__ import annotations
from typing import Dict, List, Optional
from django.apps import apps as dj_apps
import time


def _now_ms():
    return int(time.time() * 1000)


def _get_nested(d: dict, *keys, default=None):
    """Walk a nested dict safely."""
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k)
        if d is None:
            return default
    return d


def check_credit_limit(customer_id: int, new_amount: float = 0) -> Dict:
    """Check customer credit limit vs balance due + new_amount.

    Never blocks — only warns.

    Returns:
        {warning, limit, balance_due, new_amount, total_exposure,
         amount_over, message}
    """
    OrgBase = dj_apps.get_model('orgs', 'OrgBase')
    try:
        org = OrgBase.objects.get(pk=customer_id)
    except OrgBase.DoesNotExist:
        return {
            'warning': False,
            'limit': 0,
            'balance_due': 0,
            'new_amount': float(new_amount),
            'total_exposure': float(new_amount),
            'amount_over': 0,
            'message': f'Customer #{customer_id} not found',
        }

    financial = org.financial if isinstance(org.financial, dict) else {}
    limit = float(_get_nested(financial, 'customer', 'credit', 'limit', default=0) or 0)
    balance_due = float(_get_nested(financial, 'customer', 'balances', 'due', default=0) or 0)

    total_exposure = balance_due + float(new_amount)
    amount_over = max(0, total_exposure - limit) if limit > 0 else 0
    warning = limit > 0 and total_exposure > limit

    if warning:
        message = (
            f'Credit limit warning: exposure ${total_exposure:,.2f} '
            f'exceeds limit ${limit:,.2f} by ${amount_over:,.2f}'
        )
    else:
        message = 'Within credit limit' if limit > 0 else 'No credit limit set'

    return {
        'warning': warning,
        'limit': limit,
        'balance_due': balance_due,
        'new_amount': float(new_amount),
        'total_exposure': total_exposure,
        'amount_over': amount_over,
        'message': message,
    }


def acknowledge_credit_override(
    transaction_id: int,
    model_name: str,
    contact_id: int,
    reason: str = '',
) -> Dict:
    """Store acknowledgement that a credit limit was overridden.

    Writes to transaction.metadata.credit_warnings[] as an audit trail.
    The transaction record is identified by model_name + transaction_id.

    Returns: {acknowledged, transaction_id, model_name, warning_record}
    """
    Model = dj_apps.get_model('transactions', model_name.capitalize())
    instance = Model.objects.get(pk=transaction_id)

    # Get current credit check to record the amount_over
    customer_id = None
    if hasattr(instance, 'customer_id'):
        customer_id = instance.customer_id
    elif hasattr(instance, 'customer'):
        customer_id = getattr(instance.customer, 'pk', None)

    amount_over = 0
    if customer_id:
        check = check_credit_limit(customer_id)
        amount_over = check.get('amount_over', 0)

    warning_record = {
        'type': 'over_limit',
        'amount_over': amount_over,
        'acknowledged_by': contact_id,
        'reason': reason,
        'dt': _now_ms(),
    }

    metadata = instance.metadata if isinstance(instance.metadata, dict) else {}
    warnings_list = metadata.get('credit_warnings', [])
    if not isinstance(warnings_list, list):
        warnings_list = []
    warnings_list.append(warning_record)
    metadata['credit_warnings'] = warnings_list
    instance.metadata = metadata
    instance.save(update_fields=['metadata'])

    return {
        'acknowledged': True,
        'transaction_id': transaction_id,
        'model_name': model_name,
        'warning_record': warning_record,
    }


def check_bad_check_history(customer_id: int) -> Dict:
    """Check customer for bounced check / bad payment history.

    Looks at financial.customer.complaints for bad_check entries
    and at Payment records with status 'bounced' or 'returned'.

    Returns: {warning, bad_check_count, last_bad_check_dt, message}
    """
    OrgBase = dj_apps.get_model('orgs', 'OrgBase')
    try:
        org = OrgBase.objects.get(pk=customer_id)
    except OrgBase.DoesNotExist:
        return {
            'warning': False,
            'bad_check_count': 0,
            'last_bad_check_dt': None,
            'message': f'Customer #{customer_id} not found',
        }

    bad_check_count = 0
    last_bad_check_dt = None

    # Check financial.customer.complaints
    financial = org.financial if isinstance(org.financial, dict) else {}
    complaints = _get_nested(financial, 'customer', 'complaints', default=[])
    if isinstance(complaints, list):
        for c in complaints:
            if isinstance(c, dict) and c.get('type') in ('bad_check', 'bounced', 'returned'):
                bad_check_count += 1
                c_dt = c.get('dt')
                if c_dt and (last_bad_check_dt is None or c_dt > last_bad_check_dt):
                    last_bad_check_dt = c_dt

    # Check Payment records for bounced/returned
    try:
        Payment = dj_apps.get_model('transactions', 'Payment')
        bounced = Payment.objects.filter(
            customer_id=customer_id,
            status__in=['bounced', 'returned', 'nsf'],
        ).order_by('-dt_created')

        bad_check_count += bounced.count()
        if bounced.exists():
            latest = bounced.first()
            latest_dt = getattr(latest, 'dt_created', None)
            if latest_dt and (last_bad_check_dt is None or latest_dt > last_bad_check_dt):
                last_bad_check_dt = latest_dt
    except Exception:
        pass  # Payment model may not have these fields yet

    warning = bad_check_count > 0
    if warning:
        message = (
            f'Bad check warning: {bad_check_count} bounced/returned payment(s) on file'
        )
    else:
        message = 'No bad check history'

    return {
        'warning': warning,
        'bad_check_count': bad_check_count,
        'last_bad_check_dt': last_bad_check_dt,
        'message': message,
    }


def get_credit_warnings_for_transaction(
    transaction_id: int,
    model_name: str,
) -> List[Dict]:
    """Read credit warning audit trail from transaction.metadata.credit_warnings.

    Returns: list of warning records
    """
    Model = dj_apps.get_model('transactions', model_name.capitalize())
    try:
        instance = Model.objects.get(pk=transaction_id)
    except Model.DoesNotExist:
        return []

    metadata = instance.metadata if isinstance(instance.metadata, dict) else {}
    warnings = metadata.get('credit_warnings', [])
    return warnings if isinstance(warnings, list) else []
