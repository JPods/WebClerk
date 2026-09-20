"""Housekeeping — what Alice raises each week, and never decides on her own.

Bill, 2026-09-19:
  * "Alice should flag a receipt with no lines as a draft that must be completed. She
    should flag them to be deleted if they are so old. Same with order, invoices, and
    other transactions without lines."
  * "Alice should automatically convert negative invoices over 3 days old or the close
    of an accounting period from - invoice to + cash."

The first is a list. The second moves money between an AR balance and unapplied cash, so
this module proposes it and shows the arithmetic; the posting waits for a person, the way
every other cash decision in WC3 does.

Thresholds live in the company profile (`config.housekeeping`), so a company can set its
own: draft_days (default 7), delete_days (default 90), negative_invoice_days (default 3).
"""
from __future__ import annotations

import logging
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.apps import apps as dj_apps

logger = logging.getLogger(__name__)

#: every transaction that should have lines
LINE_MODELS = ('quote', 'order', 'invoice', 'purchase', 'workorder', 'receipt')

DEFAULTS = {'draft_days': 7, 'delete_days': 90, 'negative_invoice_days': 3}


def policy() -> Dict[str, int]:
    """Company thresholds, falling back to the defaults."""
    try:
        company = dj_apps.get_model('core', 'Setting').objects.filter(
            purpose='wc:company_profile').only('config').first()
        stored = ((company.config or {}).get('housekeeping') or {}) if company else {}
    except Exception:
        stored = {}
    return {key: int(stored.get(key, default)) for key, default in DEFAULTS.items()}


def _age_days(dt_created: Optional[int], now_ms: int) -> int:
    return int((now_ms - (dt_created or now_ms)) / 86_400_000)


def line_less_documents(now_ms: Optional[int] = None) -> Dict[str, List[dict]]:
    """Transactions with no lines: drafts to finish, and old ones to delete.

    A document with no lines commits nothing and owes nothing — it is an intention
    someone abandoned. Returns {'complete': [...], 'delete': [...]}, oldest first.
    """
    now_ms = now_ms or int(time.time() * 1000)
    limits = policy()
    out: Dict[str, List[dict]] = {'complete': [], 'delete': []}

    for model_name in LINE_MODELS:
        Model = dj_apps.get_model('transactions', model_name)
        rows = Model.objects.filter(is_deleted=False).exclude(
            status__in=('complete', 'canceled')).only('id', 'ida', 'status', 'dt_created')
        for header in rows:
            if header.lines.filter(is_deleted=False).exists():
                continue
            age = _age_days(header.dt_created, now_ms)
            if age < limits['draft_days']:
                continue
            record = {'model': model_name, 'id': header.pk, 'ida': header.ida,
                      'status': header.status, 'age_days': age,
                      'why': 'no lines — an intention nobody finished'}
            out['delete' if age >= limits['delete_days'] else 'complete'].append(record)

    for bucket in out.values():
        bucket.sort(key=lambda r: -r['age_days'])
    return out


def negative_invoices_to_convert(now_ms: Optional[int] = None) -> List[dict]:
    """Credit balances old enough to become unapplied cash.

    Bill: in WC2 negative invoices were applied to positive ones; keeping the heads
    straight is easier if a credit simply becomes money the customer has on account.
    The money must never be hidden — it shows as a ledger row either way.

    Proposal only: each row carries the invoice, the credit, its age and the cash record
    that would be created. A person (or a period close) says go.
    """
    now_ms = now_ms or int(time.time() * 1000)
    days = policy()['negative_invoice_days']
    Invoice = dj_apps.get_model('transactions', 'Invoice')
    cutoff = now_ms - days * 86_400_000

    out = []
    for invoice in Invoice.objects.filter(is_deleted=False, dt_created__lt=cutoff).only(
            'id', 'ida', 'customer_id', 'totals', 'dt_created', 'is_locked'):
        balance = Decimal(str((invoice.totals or {}).get('balance') or 0))
        if balance >= 0:
            continue
        out.append({
            'invoice_id': invoice.pk, 'ida': invoice.ida, 'customer_id': invoice.customer_id,
            'credit': float(-balance), 'age_days': _age_days(invoice.dt_created, now_ms),
            'journalized': bool(invoice.is_locked),
            'proposal': {'create': 'cash', 'amount': float(-balance), 'kind': 'unapplied',
                         'then': 'settle the invoice to zero through an adjustment'},
            'why': f'credit balance older than {days} days — money the customer has on account',
        })
    return sorted(out, key=lambda r: -r['age_days'])


def weekly_list(now_ms: Optional[int] = None) -> Dict[str, Any]:
    """Everything Alice raises in one call: stale commitments, line-less drafts,
    credit balances. She asks; she does not act."""
    from apps.transactions.services.close_transaction import stale_commitments
    limits = policy()
    drafts = line_less_documents(now_ms)
    return {
        'policy': limits,
        'stale_commitments': stale_commitments(days=30, now_ms=now_ms),
        'drafts_to_complete': drafts['complete'],
        'drafts_to_delete': drafts['delete'],
        'negative_invoices': negative_invoices_to_convert(now_ms),
    }


__all__ = ['policy', 'line_less_documents', 'negative_invoices_to_convert', 'weekly_list']
