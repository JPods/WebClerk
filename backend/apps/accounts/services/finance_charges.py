"""Finance charges — interest on past-due customer balances, as records.

Each monthly assessment creates, per customer with a qualifying past-due
balance, one finance-charge invoice: a single finance_charge line, due on
receipt, journalized (AR / finance_charge_income) with its own AR ledger so it
ages and appears on the statement like any other invoice. The charge is a
record someone can see, question, and reverse; totals only summarize it.

Rules come from company profile config.receivables (no defaults — a missing
key stops the run with the key named):
  finance_charge_pct          monthly percent of the past-due balance (1.1 = 1.1%)
  finance_charge_grace_days   days past due before a balance is charged
  finance_charge_term         Term ida for the charge invoice (DOR)
  finance_charge_minimum      smallest charge worth issuing, in currency

Balances already created by a finance charge are not charged again (no
interest on interest). One assessment per customer per month.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timezone
from decimal import Decimal, ROUND_HALF_UP

from django.apps import apps as dj_apps
from django.db import transaction

logger = logging.getLogger(__name__)

REQUIRED_KEYS = ('finance_charge_pct', 'finance_charge_grace_days', 'finance_charge_term', 'finance_charge_minimum')


def receivables_config() -> dict:
    """company profile config.receivables, or ValueError naming what is missing."""
    Setting = dj_apps.get_model('core', 'Setting')
    company = Setting.objects.filter(purpose='wc:company_profile', is_active=True).first()
    config = (company.config or {}).get('receivables') if company and isinstance(company.config, dict) else None
    if not isinstance(config, dict):
        raise ValueError('Company profile has no config.receivables section.')
    missing = [k for k in REQUIRED_KEYS if config.get(k) in (None, '')]
    if missing:
        raise ValueError(f'config.receivables is missing: {", ".join(missing)}.')
    return config


def _due_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).date() if value.tzinfo else value.date()
    return value if isinstance(value, date) else None


def past_due_balances(as_of: date, grace_days: int) -> dict[int, list]:
    """Open invoice ledgers more than grace_days past due, by customer org id,
    excluding balances that are themselves finance charges."""
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    by_org: dict[int, list] = {}
    # No is_void filter: nothing could void a ledger row, so it excluded nothing and
    # implied a void concept that does not exist. Voiding belongs to the document.
    rows = (Ledger.objects.filter(value_available__gt=0, org_id__isnull=False,
                                  invoice_id__isnull=False, dt_due__isnull=False)
            .select_related('invoice'))
    for ledger in rows:
        refs = ledger.invoice.refs if isinstance(ledger.invoice.refs, dict) else {}
        if refs.get('finance_charge'):
            continue
        due = _due_date(ledger.dt_due)
        if due and (as_of - due).days > grace_days:
            by_org.setdefault(ledger.org_id, []).append(ledger)
    return by_org


def assess_finance_charges(as_of: date | None = None, dry_run: bool = False) -> dict:
    """Create this month's finance-charge invoices. Returns what was (or would be) charged."""
    from apps.accounts.services.journalize import journalize_invoice
    from apps.accounts.services.ledger_balance import on_invoice_save
    from apps.transactions.services.pricing.totals_compute import recalculate_totals

    as_of = as_of or datetime.now(timezone.utc).date()
    config = receivables_config()
    rate = Decimal(str(config['finance_charge_pct']))
    grace = int(config['finance_charge_grace_days'])
    minimum = Decimal(str(config['finance_charge_minimum']))
    term = str(config['finance_charge_term'])
    period = as_of.strftime('%Y-%m')

    Invoice = dj_apps.get_model('transactions', 'Invoice')
    InvoiceLine = dj_apps.get_model('transactions', 'InvoiceLine')
    OrgBase = dj_apps.get_model('orgs', 'OrgBase')
    result = {'as_of': as_of.isoformat(), 'period': period, 'rate_pct': float(rate),
              'grace_days': grace, 'charged': [], 'skipped': []}

    for org_id, ledgers in sorted(past_due_balances(as_of, grace).items()):
        org = OrgBase.objects.filter(pk=org_id).first()
        name = (org.company or org.company) if org else f'org {org_id}'
        already = Invoice.objects.filter(customer_id=org_id, refs__finance_charge__period=period).first()
        if already:
            result['skipped'].append({'customer': name, 'reason': f'already assessed for {period} ({already.ida})'})
            continue
        base = sum((Decimal(str(l.value_available)) for l in ledgers), Decimal('0'))
        amount = (base * rate / Decimal(100)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if amount < minimum:
            result['skipped'].append({'customer': name, 'reason': f'charge {amount} below minimum {minimum}'})
            continue
        entry = {'customer': name, 'past_due': float(base), 'charge': float(amount),
                 'invoices': sorted({l.invoice.ida for l in ledgers})}
        if dry_run:
            result['charged'].append(entry)
            continue
        with transaction.atomic():
            invoice = Invoice.objects.create(
                customer_id=org_id, status='released', terms=term,
                company=getattr(org, 'company', '') or '',
                refs={'finance_charge': {'period': period, 'as_of': as_of.isoformat(), 'rate_pct': float(rate),
                                         'past_due': float(base), 'ledger_ids': [l.pk for l in ledgers]}},
            )
            InvoiceLine.objects.create(
                invoice=invoice, line_type='finance_charge',
                item={'description': f'Finance charge {rate}% on {base} past due more than {grace} days, as of {as_of.isoformat()} '
                                     f'({", ".join(entry["invoices"])})'},
                quantity={'active': 1, 'staged': 1, 'remaining': 1},
                price={'unit': float(amount)},
                cost={'unit': 0},
            )
            recalculate_totals(invoice.pk, 'invoice')
            invoice.refresh_from_db()
            posted = journalize_invoice(invoice.pk)
            if posted.get('error'):
                raise ValueError(f'Finance charge {invoice.ida} did not journalize: {posted["error"]}')
            invoice.refresh_from_db()
            on_invoice_save(invoice, replace_ledgers=True)
        entry['invoice'] = invoice.ida
        result['charged'].append(entry)
        logger.info('Finance charge %s: %s %s on %s past due', invoice.ida, name, amount, base)
    return result
