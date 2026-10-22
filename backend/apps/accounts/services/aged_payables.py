"""
Aged Payables Report Service
==============================

Mirror of aged_receivables.py for the AP side.

Produces payee aging by bucket from the payable Ledger rows (source='AP').
Data comes from Ledger records (single source of truth for payables).

It read model_name='purchase' until 2026-10-22, but payables are written by the receipt
(model_name='receipt'), so the report never showed a payable (Bill: fix on the Small-Sting
branch). A payee is the vendor org, else the contact a payable is owed to (a Small-Sting's
filer); each section says which (payee_model 'org' or 'contact').
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from django.apps import apps as dj_apps
from django.db import models
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast


def _to_date(dt) -> Optional[date]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.date()
    return dt


def _days_past_due(due_date: date, as_of: date) -> int:
    return (as_of - due_date).days


def _bucket_key(days: int) -> str:
    if days < -30:
        return 'future'
    if days < 0:
        return 'current'
    if days < 30:
        return 'period_1'
    if days < 60:
        return 'period_2'
    return 'period_3'


def aged_payables_report(
    as_of_date: Optional[date] = None,
    vendor_ids: Optional[list] = None,
    min_balance: Decimal = Decimal('0.01'),
) -> dict:
    """Generate aged payables data for all vendors (or a subset).

    Returns:
        {
            'as_of_date': '2026-09-11',
            'vendors': [
                {
                    'id': 42,
                    'name': 'Vendor Name',
                    'balance_due': 12500.00,
                    'open_purchases': 0.00,
                    'aging': {
                        'future': 0, 'current': 0,
                        'period_1': 0, 'period_2': 0, 'period_3': 12500.00,
                    },
                    'lines': [...],
                },
            ],
            'grand_totals': {...},
        }
    """
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    OrgBase = dj_apps.get_model('orgs', 'OrgBase')
    Contact = dj_apps.get_model('core', 'Contact')
    Purchase = dj_apps.get_model('transactions', 'Purchase')

    if as_of_date is None:
        as_of_date = date.today()

    # The open payables: every AP row with a balance and a payee.
    ledger_qs = (Ledger.objects.filter(source='AP', value_available__isnull=False)
                 .exclude(value_available=0)
                 .filter(models.Q(org_id__isnull=False) | models.Q(contact_id__isnull=False)))

    if vendor_ids:
        ledger_qs = ledger_qs.filter(org_id__in=vendor_ids)

    # Group by payee: the org when there is one, else the contact.
    vendor_ledgers: dict[tuple, list] = {}
    for ledger in ledger_qs.values(
        'id', 'org_id', 'contact_id', 'model_name', 'parent_id',
        'value_original', 'value_available', 'dt_due', 'dt_recorded',
        'ida',
    ):
        payee = ('org', ledger['org_id']) if ledger['org_id'] else ('contact', ledger['contact_id'])
        vendor_ledgers.setdefault(payee, []).append(ledger)

    # Build vendor sections
    vendors = []
    grand = {
        'balance_due': Decimal('0'), 'future': Decimal('0'),
        'current': Decimal('0'), 'period_1': Decimal('0'),
        'period_2': Decimal('0'), 'period_3': Decimal('0'),
    }

    if not vendor_ledgers:
        return {
            'as_of_date': as_of_date.isoformat(),
            'vendors': [],
            'grand_totals': {k: float(v) for k, v in grand.items()},
        }

    org_ids = [pid for kind, pid in vendor_ledgers if kind == 'org']
    contact_ids = [pid for kind, pid in vendor_ledgers if kind == 'contact']
    payees = {('org', o.id): o for o in OrgBase.objects.filter(id__in=org_ids)}
    payees.update({('contact', c.id): c for c in Contact.objects.filter(id__in=contact_ids)})

    # Open purchase totals per vendor
    open_po_qs = Purchase.objects.filter(
        vendor_id__in=org_ids,
        status__in=['planned', 'released', 'in_progress'],
    ).values('vendor_id').annotate(
        _total=Cast(KeyTextTransform('total', 'totals'), output_field=models.DecimalField(max_digits=18, decimal_places=6)),
    ).annotate(total=models.Sum('_total'))
    open_po_map = {
        row['vendor_id']: Decimal(str(row['total'] or 0))
        for row in open_po_qs
    }

    for payee_key in sorted(vendor_ledgers, key=lambda k: (k[0], k[1])):
        payee_model, payee_id = payee_key
        org = payees.get(payee_key)
        if not org:
            continue

        ledgers = vendor_ledgers[payee_key]
        lines = []
        vend_aging = {
            'future': Decimal('0'), 'current': Decimal('0'),
            'period_1': Decimal('0'), 'period_2': Decimal('0'),
            'period_3': Decimal('0'),
        }
        vend_balance = Decimal('0')

        for led in ledgers:
            val_available = Decimal(str(led['value_available'] or 0))
            val_original = Decimal(str(led['value_original'] or 0))
            due_date = _to_date(led['dt_due'])
            rec_date = _to_date(led['dt_recorded'])

            if due_date:
                days = _days_past_due(due_date, as_of_date)
            else:
                days = 0

            bucket = _bucket_key(days)

            line_buckets = {
                'future': Decimal('0'), 'current': Decimal('0'),
                'period_1': Decimal('0'), 'period_2': Decimal('0'),
                'period_3': Decimal('0'),
            }
            line_buckets[bucket] = val_available
            vend_aging[bucket] += val_available
            vend_balance += val_available

            lines.append({
                'type': {'receipt': 'RC'}.get(led['model_name'], 'PO'),
                'parent_id': led['parent_id'],
                'number': led.get('ida', ''),
                'date': rec_date.isoformat() if rec_date else '',
                'original': float(val_original),
                'balance': float(val_available),
                'future': float(line_buckets['future']),
                'current': float(line_buckets['current']),
                'period_1': float(line_buckets['period_1']),
                'period_2': float(line_buckets['period_2']),
                'period_3': float(line_buckets['period_3']),
                'days': max(days, 0),
            })

        if abs(vend_balance) < min_balance:
            continue

        lines.sort(key=lambda x: x['date'])
        vend_open_po = open_po_map.get(payee_id, Decimal('0')) if payee_model == 'org' else Decimal('0')

        if payee_model == 'org':
            name = getattr(org, 'display_name', '') or getattr(org, 'company', '')
        else:
            name = (' '.join(p for p in (org.name_first, org.name_last) if p) or org.email or '')
        vendor_data = {
            'id': payee_id,
            'payee_model': payee_model,
            'name': name,
            'balance_due': float(vend_balance),
            'open_purchases': float(vend_open_po),
            'aging': {k: float(v) for k, v in vend_aging.items()},
            'lines': lines,
        }
        vendors.append(vendor_data)

        grand['balance_due'] += vend_balance
        for k in ('future', 'current', 'period_1', 'period_2', 'period_3'):
            grand[k] += vend_aging[k]

    vendors.sort(key=lambda v: v['name'].lower())

    return {
        'as_of_date': as_of_date.isoformat(),
        'vendors': vendors,
        'grand_totals': {k: float(v) for k, v in grand.items()},
    }
