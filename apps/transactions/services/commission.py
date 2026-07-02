"""
Commission Service — calculate, assign, and accrue commissions.

Three calculation methods:
  - revenue: rate_pct × level_factor × extended_price
  - margin:  rate_pct × level_factor × (extended_price - extended_cost)
  - script:  execute a stored script from the rep/vendor record

The price_level factor is the wc2 insight: a 10% commission with a 70% factor
for wholesale = 7% effective rate. This handles the reality that margins differ
by price level, so commissions should too.

Commission flows: proposal → order → invoice. Set on proposal, carried forward.
Accrued on invoice journalize. Reversed on return/credit.

Users WILL override defaults. Design for it — every field is overridable at
the line level, and the header aggregates from lines.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
import time

from django.apps import apps as dj_apps
from django.db import transaction


def _now_ms():
    return int(time.time() * 1000)


def _get_setting_gl(setting_name: str, *keys: str) -> str:
    """Look up a GL account code from a Setting record's data JSON.

    Walks nested keys: _get_setting_gl('commission_config', 'gl_accounts', 'expense')
    reads Setting(name='commission_config').data['gl_accounts']['expense'].

    For flat keys: _get_setting_gl('gl_account_defaults', 'commission_expense')
    reads Setting(name='gl_account_defaults').data['commission_expense'].
    """
    try:
        Setting = dj_apps.get_model('core', 'Setting')
        setting = Setting.objects.filter(name=setting_name, is_active=True).first()
        if not setting or not setting.data:
            return ''
        val = setting.data
        for key in keys:
            if isinstance(val, dict):
                val = val.get(key)
            else:
                return ''
        return val if isinstance(val, str) and val.strip() else ''
    except Exception:
        return ''


# Default level factors — wc2 pattern
# Retail gets full commission, wholesale gets reduced, distributor gets less
DEFAULT_LEVEL_FACTORS = {
    'retail': 1.0,
    'wholesale': 0.7,
    'distributor': 0.5,
    'employee': 0.0,
    'cost': 0.0,
}


def empty_commission() -> dict:
    """Empty commission object — the schema for header and line."""
    return {
        'reps': [],
        'total': 0.0,
        'basis': '',          # "revenue" | "margin" | "script" | "" (not set)
        'accrued': False,
        'dt_accrued': 0,
    }


def empty_rep_entry(rep_id: int = 0, rep_ida: str = '', name: str = '',
                    rate_pct: float = 0, split_pct: float = 100,
                    level_factor: float = 1.0, basis: str = 'revenue') -> dict:
    """One rep's commission entry."""
    return {
        'rep_id': rep_id,
        'rep_ida': rep_ida,
        'name': name,
        'rate_pct': rate_pct,
        'split_pct': split_pct,
        'level_factor': level_factor,
        'effective_rate': round(rate_pct * level_factor / 100 * (split_pct / 100) * 100, 4),
        'basis': basis,
        'amount': 0.0,
        'override': False,
        'override_reason': '',
    }


def get_rep_commission_config(rep_id: int) -> dict:
    """Load commission config from rep's OrgBase record.

    Looks in org.financial.rep.commissions for rate_pct and
    org.data or org.prefs for level_factors and script.

    Returns: {rate_pct, basis, level_factors, script_id}
    """
    try:
        OrgBase = dj_apps.get_model('orgs', 'OrgBase')
        rep = OrgBase.objects.get(pk=rep_id)
        financial = rep.financial or {}
        rep_fin = financial.get('rep', {})
        commissions = rep_fin.get('commissions', {})

        prefs = rep.prefs or {}
        commission_prefs = prefs.get('commission', {})

        return {
            'rate_pct': commissions.get('rate_pct', 0),
            'basis': commission_prefs.get('basis', 'revenue'),
            'level_factors': commission_prefs.get('level_factors', DEFAULT_LEVEL_FACTORS),
            'script_id': commission_prefs.get('script_id', 0),
        }
    except Exception:
        return {'rate_pct': 0, 'basis': 'revenue', 'level_factors': DEFAULT_LEVEL_FACTORS, 'script_id': 0}


def get_customer_rep_ids(customer_id: int) -> list[int]:
    """Get rep IDs assigned to a customer.

    Looks in customer.refs.links.reps or customer.relations for rep assignments.
    """
    try:
        OrgBase = dj_apps.get_model('orgs', 'OrgBase')
        customer = OrgBase.objects.get(pk=customer_id)
        refs = customer.refs or {}
        links = refs.get('links', {})
        rep_links = links.get('reps', [])
        if isinstance(rep_links, list):
            return [r.get('id') or r.get('rep_id') for r in rep_links if isinstance(r, dict)]
        relations = customer.relations or {}
        return relations.get('rep_ids', [])
    except Exception:
        return []


def calculate_line_commission(
    line_price_extended: float,
    line_cost_extended: float,
    price_level: str,
    rep_configs: list[dict],
    basis_override: str = '',
) -> dict:
    """Calculate commission for one line.

    Args:
        line_price_extended: selling price × qty
        line_cost_extended: cost × qty
        price_level: 'retail', 'wholesale', 'distributor', etc.
        rep_configs: [{rep_id, rep_ida, name, rate_pct, split_pct, basis, level_factors}]
        basis_override: force basis for all reps on this line

    Returns: commission object for the line
    """
    margin = line_price_extended - line_cost_extended
    reps = []
    total = 0.0

    for config in rep_configs:
        rate_pct = config.get('rate_pct', 0)
        if rate_pct == 0:
            continue

        split_pct = config.get('split_pct', 100)
        basis = basis_override or config.get('basis', 'revenue')
        level_factors = config.get('level_factors', DEFAULT_LEVEL_FACTORS)
        level_factor = level_factors.get(price_level or 'retail', 1.0)

        # Calculate base amount
        if basis == 'margin':
            base_amount = margin
        elif basis == 'script':
            # Script execution would go here — for now, fall back to revenue
            base_amount = line_price_extended
        else:  # revenue (default)
            base_amount = line_price_extended

        # rate × level_factor × split
        amount = round(base_amount * (rate_pct / 100) * level_factor * (split_pct / 100), 2)

        effective_rate = round(rate_pct * level_factor * (split_pct / 100), 4)

        reps.append({
            'rep_id': config.get('rep_id', 0),
            'rep_ida': config.get('rep_ida', ''),
            'name': config.get('name', ''),
            'rate_pct': rate_pct,
            'split_pct': split_pct,
            'level_factor': level_factor,
            'effective_rate': effective_rate,
            'basis': basis,
            'amount': amount,
            'override': False,
            'override_reason': '',
        })
        total += amount

    return {
        'reps': reps,
        'total': round(total, 2),
        'basis': basis_override or (rep_configs[0].get('basis', 'revenue') if rep_configs else ''),
        'accrued': False,
        'dt_accrued': 0,
    }


def populate_transaction_commission(transaction_id: int, model_name: str) -> dict:
    """Auto-populate commission on a transaction from customer's rep assignments.

    Reads customer → reps → rep configs → calculates per line → aggregates to header.
    Does NOT overwrite lines that already have override=True.

    Args:
        transaction_id: PK of the transaction (order, proposal, invoice, purchase)
        model_name: 'order', 'proposal', 'invoice', 'purchase'

    Returns: {header_total, lines_updated, reps: [{rep_id, name, total}]}
    """
    # Resolve models
    model_map = {
        'order': ('transactions', 'Order', 'transactions', 'OrderLine', 'order_id'),
        'proposal': ('transactions', 'Proposal', 'transactions', 'ProposalLine', 'proposal_id'),
        'invoice': ('transactions', 'Invoice', 'transactions', 'InvoiceLine', 'invoice_id'),
        'purchase': ('transactions', 'Purchase', 'transactions', 'PurchaseLine', 'purchase_id'),
    }

    if model_name not in model_map:
        return {'error': f'Unknown model: {model_name}'}

    h_app, h_model, l_app, l_model, l_fk = model_map[model_name]
    HeaderModel = dj_apps.get_model(h_app, h_model)
    LineModel = dj_apps.get_model(l_app, l_model)

    try:
        header = HeaderModel.objects.get(pk=transaction_id)
    except HeaderModel.DoesNotExist:
        return {'error': f'{model_name} {transaction_id} not found'}

    # Get reps for this customer
    customer_id = header.customer_id
    if not customer_id:
        return {'error': 'No customer on transaction', 'header_total': 0}

    rep_ids = get_customer_rep_ids(customer_id)
    if not rep_ids:
        return {'header_total': 0, 'lines_updated': 0, 'reps': [], 'message': 'No reps assigned to customer'}

    # Load rep configs
    OrgBase = dj_apps.get_model('orgs', 'OrgBase')
    rep_configs = []
    for rep_id in rep_ids:
        config = get_rep_commission_config(rep_id)
        try:
            rep = OrgBase.objects.get(pk=rep_id)
            config['rep_id'] = rep_id
            config['rep_ida'] = rep.ida
            config['name'] = rep.display_name
        except OrgBase.DoesNotExist:
            continue
        # If multiple reps, default split evenly
        config['split_pct'] = round(100.0 / len(rep_ids), 2)
        rep_configs.append(config)

    if not rep_configs:
        return {'header_total': 0, 'lines_updated': 0, 'reps': []}

    # Calculate per line
    lines = LineModel.objects.filter(**{l_fk: transaction_id})
    header_total = 0.0
    lines_updated = 0
    rep_totals = {rc['rep_id']: 0.0 for rc in rep_configs}

    price_level = header.price_level or 'retail'

    with transaction.atomic():
        for line in lines:
            existing = line.commission or {}
            # Don't overwrite manual overrides
            if existing.get('reps') and any(r.get('override') for r in existing.get('reps', [])):
                header_total += existing.get('total', 0)
                continue

            price_data = line.price or {}
            cost_data = line.cost or {}
            price_ext = float(price_data.get('extended', 0) or 0)
            cost_ext = float(cost_data.get('extended', 0) or 0)

            if price_ext == 0:
                continue

            line_commission = calculate_line_commission(
                price_ext, cost_ext, price_level, rep_configs
            )

            line.commission = line_commission
            line.save(update_fields=['commission'])
            lines_updated += 1
            header_total += line_commission['total']

            for rep_entry in line_commission['reps']:
                rid = rep_entry['rep_id']
                if rid in rep_totals:
                    rep_totals[rid] += rep_entry['amount']

        # Update header
        header_commission = {
            'reps': [
                {
                    'rep_id': rc['rep_id'],
                    'rep_ida': rc['rep_ida'],
                    'name': rc['name'],
                    'rate_pct': rc['rate_pct'],
                    'split_pct': rc['split_pct'],
                    'basis': rc.get('basis', 'revenue'),
                    'amount': round(rep_totals.get(rc['rep_id'], 0), 2),
                }
                for rc in rep_configs
            ],
            'total': round(header_total, 2),
            'basis': rep_configs[0].get('basis', 'revenue'),
            'accrued': False,
            'dt_accrued': 0,
        }
        header.commission = header_commission
        header.save(update_fields=['commission'])

    return {
        'header_total': round(header_total, 2),
        'lines_updated': lines_updated,
        'reps': [
            {'rep_id': rc['rep_id'], 'name': rc['name'], 'total': round(rep_totals.get(rc['rep_id'], 0), 2)}
            for rc in rep_configs
        ],
    }


def accrue_commission(transaction_id: int, model_name: str, ida_prefix: str = '') -> dict:
    """Accrue commission to GL — fires after invoice journalize.

    Creates GL entries: Commission Expense (debit) / Commission Payable (credit)
    per rep. Marks commission as accrued.

    Returns: {created: int, entries: [{rep, account, debit, credit}]}
    """
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')

    model_map = {
        'invoice': ('transactions', 'Invoice'),
        'order': ('transactions', 'Order'),
    }
    if model_name not in model_map:
        return {'created': 0, 'error': 'Commission accrual only on invoices/orders'}

    app, model = model_map[model_name]
    Model = dj_apps.get_model(app, model)

    try:
        header = Model.objects.get(pk=transaction_id)
    except Model.DoesNotExist:
        return {'created': 0, 'error': f'{model_name} {transaction_id} not found'}

    comm = header.commission or {}
    if comm.get('accrued'):
        return {'created': 0, 'error': 'Already accrued'}

    reps = comm.get('reps', [])
    if not reps:
        return {'created': 0, 'error': 'No commission to accrue'}

    # Resolve GL accounts: commission object → rep record → commission_config setting → gl_account_defaults setting → hardcoded
    comm_gl = comm.get('gl', {})

    created = 0
    entries = []

    with transaction.atomic():
        for rep in reps:
            amount = rep.get('amount', 0)
            if amount <= 0:
                continue

            # Per-rep GL resolution chain
            rep_gl = {}
            rep_id = rep.get('rep_id')
            if rep_id:
                try:
                    OrgBase = dj_apps.get_model('orgs', 'OrgBase')
                    rep_org = OrgBase.objects.get(pk=rep_id)
                    rep_gl = (rep_org.gl_accounts or {})
                except Exception:
                    pass

            # Resolution: invoice.commission.gl → rep.gl_accounts → commission_config → gl_account_defaults → hardcoded
            comm_expense = (
                comm_gl.get('expense')
                or rep_gl.get('commission_expense') or rep_gl.get('expense')
                or _get_setting_gl('commission_config', 'gl_accounts', 'expense')
                or _get_setting_gl('gl_account_defaults', 'commission_expense')
                or 'EXP-COMMISSIONS-000'
            )
            comm_payable = (
                comm_gl.get('payable')
                or rep_gl.get('commission_payable') or rep_gl.get('payable')
                or _get_setting_gl('commission_config', 'gl_accounts', 'payable')
                or _get_setting_gl('gl_account_defaults', 'commission_payable')
                or 'LIAB-COMMPAY-000'
            )

            rep_name = rep.get('name', f"Rep #{rep.get('rep_id', '?')}")
            ida_base = f'{ida_prefix}CM-{header.ida}-{rep.get("rep_ida", "")}'

            # Commission Expense debit
            GlJournal.objects.create(
                ida=f'{ida_base}-EXP',
                account=comm_expense,
                debit=amount,
                credit=None,
                source='automation',
                type='general',
                source_id=transaction_id,
                source_model=f'{model_name}_commission',
            )
            entries.append({'rep': rep_name, 'account': comm_expense, 'debit': amount, 'credit': 0})

            # Commission Payable credit
            GlJournal.objects.create(
                ida=f'{ida_base}-PAY',
                account=comm_payable,
                debit=None,
                credit=amount,
                source='automation',
                type='general',
                source_id=transaction_id,
                source_model=f'{model_name}_commission',
            )
            entries.append({'rep': rep_name, 'account': comm_payable, 'debit': 0, 'credit': amount})
            created += 2

        # Mark accrued
        comm['accrued'] = True
        comm['dt_accrued'] = _now_ms()
        header.commission = comm
        Model.objects.filter(pk=transaction_id).update(commission=comm, dt_modified=_now_ms())

    return {'created': created, 'entries': entries, 'total_accrued': comm.get('total', 0)}
