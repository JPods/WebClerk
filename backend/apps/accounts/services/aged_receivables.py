"""
Aged Receivables Report Service
================================

Produces the data for two documents:
1. Aged Receivables Report (internal) — all customers with aging detail
2. Customer Statement (customer-facing) — single customer with response area

Both share the same data structure. The print layout JSON controls presentation.

Data comes from Ledger records (single source of truth for receivables).
Company settings control statement messages, finance charge rate, and send thresholds.
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


def get_company_receivables_config() -> dict:
    """Load receivables config from company_profile Setting."""
    Setting = dj_apps.get_model('core', 'Setting')
    try:
        setting = Setting.objects.filter(
            purpose='wc:company_profile', parent_model='setting',
        ).first()
        if setting:
            return (setting.config or {}).get('receivables', {})
    except Exception:
        pass
    return {}


def aged_receivables_report(
    as_of_date: Optional[date] = None,
    customer_ids: Optional[list] = None,
    min_balance: Decimal = Decimal('0.01'),
) -> dict:
    """Generate aged receivables data for all customers (or a subset).

    Returns the complete data structure needed by both the internal report
    and customer-facing statements.

    Args:
        as_of_date: Date to age against (defaults to today)
        customer_ids: Limit to specific customers (None = all with balance)
        min_balance: Minimum absolute balance to include (filters zero-balance)

    Returns:
        {
            'as_of_date': '2026-08-06',
            'company': {...},
            'receivables_config': {...},
            'customers': [
                {
                    'id': 42,
                    'name': 'Contact Name',
                    'company': 'Company Name',
                    'attention': 'Accounts Payable',
                    'address': {...},
                    'phone': '...',
                    'fax': '...',
                    'balance_due': 6148.60,
                    'open_orders': 0.00,
                    'summary': 6148.60,
                    'aging': {
                        'future': 0, 'current': 0,
                        'period_1': 0, 'period_2': 0, 'period_3': 6148.60,
                    },
                    'lines': [
                        {
                            'type': 'Inv',
                            'number': '0220-3338',
                            'date': '2011-01-21',
                            'original': 6148.60,
                            'balance': 6148.60,
                            'future': 0, 'current': 0,
                            'period_1': 0, 'period_2': 0, 'period_3': 6148.60,
                            'days': 5676,
                            'finance': 12796.47,
                        },
                        ...
                    ],
                },
                ...
            ],
            'grand_totals': {
                'balance_due': ..., 'future': ..., 'current': ...,
                'period_1': ..., 'period_2': ..., 'period_3': ...,
            },
        }
    """
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    OrgBase = dj_apps.get_model('orgs', 'OrgBase')
    Order = dj_apps.get_model('transactions', 'Order')
    Setting = dj_apps.get_model('core', 'Setting')

    if as_of_date is None:
        as_of_date = date.today()

    receivables_config = get_company_receivables_config()
    finance_pct = Decimal(str(receivables_config.get('finance_charge_pct', 0)))

    # Get company info for header
    company_info = {}
    try:
        cp = Setting.objects.filter(
            purpose='wc:company_profile', parent_model='setting',
        ).first()
        if cp:
            company_info = (cp.config or {}).get('company', {})
    except Exception:
        pass

    # ── Query all non-zero ledgers grouped by org ──
    ledger_qs = Ledger.objects.filter(
        value_available__isnull=False,
        org_id__isnull=False,
    ).exclude(value_available=0)

    if customer_ids:
        ledger_qs = ledger_qs.filter(org_id__in=customer_ids)

    # Group ledgers by org
    org_ledgers: dict[int, list] = {}
    for ledger in ledger_qs.select_related('org').values(
        'id', 'org_id', 'model_name', 'parent_id',
        'value_original', 'value_available', 'dt_due', 'dt_recorded',
        'ida',
    ):
        org_id = ledger['org_id']
        if org_id not in org_ledgers:
            org_ledgers[org_id] = []
        org_ledgers[org_id].append(ledger)

    # ── Build customer sections ──
    customers = []
    grand = {
        'balance_due': Decimal('0'), 'future': Decimal('0'),
        'current': Decimal('0'), 'period_1': Decimal('0'),
        'period_2': Decimal('0'), 'period_3': Decimal('0'),
    }

    # Get org details
    org_ids = list(org_ledgers.keys())
    if not org_ids:
        return {
            'as_of_date': as_of_date.isoformat(),
            'company': company_info,
            'receivables_config': receivables_config,
            'customers': [],
            'grand_totals': {k: float(v) for k, v in grand.items()},
        }

    orgs = {
        o.id: o for o in OrgBase.objects.filter(id__in=org_ids)
    }

    # Get open order totals per customer
    open_orders_qs = Order.objects.filter(
        customer_id__in=org_ids,
        status__in=['planned', 'released', 'in_progress'],
    ).values('customer_id').annotate(
        _total=Cast(KeyTextTransform('total', 'totals'), output_field=models.DecimalField(max_digits=18, decimal_places=6)),
    ).annotate(total=models.Sum('_total'))
    open_orders_map = {
        row['customer_id']: Decimal(str(row['total'] or 0))
        for row in open_orders_qs
    }

    for org_id in sorted(org_ids):
        org = orgs.get(org_id)
        if not org:
            continue

        ledgers = org_ledgers[org_id]

        # Build detail lines and customer totals
        lines = []
        cust_aging = {
            'future': Decimal('0'), 'current': Decimal('0'),
            'period_1': Decimal('0'), 'period_2': Decimal('0'),
            'period_3': Decimal('0'),
        }
        cust_balance = Decimal('0')

        for led in ledgers:
            val_available = Decimal(str(led['value_available'] or 0))
            val_original = Decimal(str(led['value_original'] or 0))
            due_date = _to_date(led['dt_due'])
            rec_date = _to_date(led['dt_recorded'])

            # Determine type
            model_name = led.get('model_name', '')
            if model_name == 'payment':
                line_type = 'Pay'
            elif model_name == 'invoice':
                line_type = 'Inv'
            else:
                line_type = model_name[:3].capitalize() if model_name else '?'

            # Age the line
            if due_date:
                days = _days_past_due(due_date, as_of_date)
            else:
                days = 0

            bucket = _bucket_key(days)

            # Finance charge: monthly rate × months past due × balance
            finance = Decimal('0')
            if finance_pct > 0 and days > 0 and val_available > 0:
                months = Decimal(str(max(days, 0))) / Decimal('30')
                finance = val_available * (finance_pct / Decimal('100')) * months

            # Build per-bucket amounts for this line
            line_buckets = {
                'future': Decimal('0'), 'current': Decimal('0'),
                'period_1': Decimal('0'), 'period_2': Decimal('0'),
                'period_3': Decimal('0'),
            }
            line_buckets[bucket] = val_available

            cust_aging[bucket] += val_available
            cust_balance += val_available

            lines.append({
                'type': line_type,
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
                'finance': float(finance.quantize(Decimal('0.01'))),
            })

        # Skip customers below minimum balance
        if abs(cust_balance) < min_balance:
            continue

        # Sort lines by date
        lines.sort(key=lambda x: x['date'])

        # Open orders for this customer
        cust_open_orders = open_orders_map.get(org_id, Decimal('0'))

        # Contact info
        contact_name = ''
        attention = ''
        phone = ''
        fax = ''
        address = {}
        try:
            Contact = dj_apps.get_model('core', 'Contact')
            contact = Contact.objects.filter(customer_id=org_id).first()
            if contact:
                contact_name = getattr(contact, 'display_name', '') or ''
                attention = getattr(contact, 'attention', '') or 'Accounts Payable'
                phone_obj = getattr(contact, 'phone', None)
                if phone_obj:
                    phone = str(phone_obj)
                # Try refs for additional contact info
                refs = getattr(contact, 'refs', None) or {}
                if isinstance(refs, dict):
                    fax = refs.get('fax', '')
        except Exception:
            pass

        # Determine aging period for message selection
        if float(cust_aging['period_3']) > 0:
            aging_period = 'period_3'
        elif float(cust_aging['period_2']) > 0:
            aging_period = 'period_2'
        elif float(cust_aging['period_1']) > 0:
            aging_period = 'period_1'
        else:
            aging_period = None

        # Get period message from config
        messages = receivables_config.get('messages', {})
        period_msg = messages.get(aging_period, {}) if aging_period else {}

        customer_data = {
            'id': org_id,
            'name': contact_name,
            'company': getattr(org, 'display_name', '') or getattr(org, 'company', ''),
            'attention': attention,
            'address': address,
            'phone': phone,
            'fax': fax,
            'balance_due': float(cust_balance),
            'open_orders': float(cust_open_orders),
            'summary': float(cust_balance + cust_open_orders),
            'aging': {k: float(v) for k, v in cust_aging.items()},
            'aging_period': aging_period,
            'heading': period_msg.get('heading', ''),
            'closing': period_msg.get('closing', ''),
            'lines': lines,
        }
        customers.append(customer_data)

        # Accumulate grand totals
        grand['balance_due'] += cust_balance
        for k in ('future', 'current', 'period_1', 'period_2', 'period_3'):
            grand[k] += cust_aging[k]

    # Sort customers by company name
    customers.sort(key=lambda c: c['company'].lower())

    return {
        'as_of_date': as_of_date.isoformat(),
        'company': company_info,
        'receivables_config': receivables_config,
        'customers': customers,
        'grand_totals': {k: float(v) for k, v in grand.items()},
    }


def customer_statement(customer_id: int, as_of_date: Optional[date] = None) -> dict:
    """Generate statement data for a single customer.

    Convenience wrapper — returns same structure as aged_receivables_report
    but for one customer, with response_area options included.
    """
    report = aged_receivables_report(
        as_of_date=as_of_date,
        customer_ids=[customer_id],
    )

    # Add response area options (from company settings or defaults)
    report['response_area'] = [
        'The check is in the mail.',
        "I don't have copies of invoices. (please send needed invoices)",
        'Payment is due to be mailed on ____________.',
        'Other:',
    ]

    return report
