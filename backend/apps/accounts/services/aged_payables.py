"""
Aged Payables Report Service
==============================

Mirror of aged_receivables.py for the AP side.

Produces vendor aging by bucket from Ledger records where model_name='purchase'.
Data comes from Ledger records (single source of truth for payables).
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
    Purchase = dj_apps.get_model('transactions', 'Purchase')

    if as_of_date is None:
        as_of_date = date.today()

    # Query payable ledgers (purchase-sourced, non-zero balance)
    ledger_qs = Ledger.objects.filter(
        model_name='purchase',
        value_available__isnull=False,
        org_id__isnull=False,
    ).exclude(value_available=0)

    if vendor_ids:
        ledger_qs = ledger_qs.filter(org_id__in=vendor_ids)

    # Group by vendor
    vendor_ledgers: dict[int, list] = {}
    for ledger in ledger_qs.values(
        'id', 'org_id', 'model_name', 'parent_id',
        'value_original', 'value_available', 'dt_due', 'dt_recorded',
        'ida',
    ):
        org_id = ledger['org_id']
        if org_id not in vendor_ledgers:
            vendor_ledgers[org_id] = []
        vendor_ledgers[org_id].append(ledger)

    # Build vendor sections
    vendors = []
    grand = {
        'balance_due': Decimal('0'), 'future': Decimal('0'),
        'current': Decimal('0'), 'period_1': Decimal('0'),
        'period_2': Decimal('0'), 'period_3': Decimal('0'),
    }

    org_ids = list(vendor_ledgers.keys())
    if not org_ids:
        return {
            'as_of_date': as_of_date.isoformat(),
            'vendors': [],
            'grand_totals': {k: float(v) for k, v in grand.items()},
        }

    orgs = {o.id: o for o in OrgBase.objects.filter(id__in=org_ids)}

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

    for org_id in sorted(org_ids):
        org = orgs.get(org_id)
        if not org:
            continue

        ledgers = vendor_ledgers[org_id]
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
                'type': 'PO',
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
        vend_open_po = open_po_map.get(org_id, Decimal('0'))

        vendor_data = {
            'id': org_id,
            'name': getattr(org, 'display_name', '') or getattr(org, 'company', ''),
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
