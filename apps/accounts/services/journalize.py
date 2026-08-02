"""
Journalize Service — Line-Level GL Posting
==========================================

Follows wc2 pattern: walk each line item, look up item.gls per line,
create proper Revenue/COGS/Inventory/AR entries per line, consolidate
by GL account per document.

Three journal types:
  - Sales Journal (invoices): AR debit, Revenue credit, COGS debit, Inventory credit
  - Purchase Journal (purchase receipts): Inventory debit, AP credit
  - Cash Journal (payments): Cash debit, AR credit

WebClerk is commerce, not accounting. We produce GL journal entries.
Accounting programs consume them.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
import time

from django.apps import apps as dj_apps
from django.db import transaction


def _now_ms():
    return int(time.time() * 1000)


def _get_item_gls(item_id: int) -> dict:
    """Look up GL accounts for an item. Returns {revenue, cogs, inventory, purchase}."""
    try:
        Item = dj_apps.get_model('products', 'Item')
        item = Item.objects.get(pk=item_id)
        return item.gls or {}
    except Exception:
        return {}


def _get_org_gl_override(org_id: int, key: str) -> Optional[str]:
    """Check if org has a GL account override for a given key (ar, revenue, cash)."""
    try:
        OrgBase = dj_apps.get_model('orgs', 'OrgBase')
        org = OrgBase.objects.get(pk=org_id)
        gl_accounts = org.gl_accounts or {}
        return gl_accounts.get(key) if gl_accounts.get(key) else None
    except Exception:
        return None


def _get_category_gl(category: str) -> str:
    """Look up GL account for an expense category bucket.

    Reads the gl_map from the payment field_access Setting.
    Freehand entries that aren't in the map get default_gl.
    """
    if not category:
        return 'EXP-MISC-000'
    try:
        Setting = dj_apps.get_model('core', 'Setting')
        setting = Setting.objects.filter(
            purpose='field_access', parent_model='payment',
        ).first()
        if setting:
            sl = (setting.config or {}).get('select_lists', {}).get('category', {})
            gl = sl.get('gl_map', {}).get(category)
            if gl:
                return gl
            return sl.get('default_gl', 'EXP-MISC-000')
    except Exception:
        pass
    return 'EXP-MISC-000'


# Default fallback accounts
DEFAULTS = {
    'ar': 'ASSET-AR-000',
    'cash': 'ASSET-CASH-000',
    'ap': 'LIAB-ACCTSPAY-000',
    'revenue': 'REV-SALES-000',
    'cogs': 'COGS-PRODUCTS-000',
    'inventory': 'ASSET-INVENTORY-000',
}


def journalize_invoice(invoice_id: int, ida_prefix: str = '') -> dict:
    """Journalize a single invoice — line-level GL posting.

    For each invoice line:
      - Debit AR (customer's AR account or default)
      - Credit Revenue (item.gls.revenue)
      - Debit COGS (item.gls.cogs)
      - Credit Inventory (item.gls.inventory)

    Consolidates by GL account, then writes GlJournal records.
    Marks invoice metadata with gl_accounts.posted = true.

    Args:
        invoice_id: Invoice PK
        ida_prefix: prefix for journal ida (e.g., 'zzz' for test)

    Returns:
        {created: int, postings: [{account, debit, credit, purpose}], error: str}
    """
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')
    Invoice = dj_apps.get_model('transactions', 'Invoice')
    InvoiceLine = dj_apps.get_model('transactions', 'InvoiceLine')

    try:
        invoice = Invoice.objects.get(pk=invoice_id)
    except Invoice.DoesNotExist:
        return {'created': 0, 'error': f'Invoice {invoice_id} not found'}

    # Guard against double-posting
    if GlJournal.objects.filter(source_id=invoice_id, source_model='invoice').exists():
        return {'created': 0, 'error': 'Already journalized'}

    lines = InvoiceLine.objects.filter(invoice_id=invoice_id)
    if not lines.exists():
        return {'created': 0, 'error': 'No lines to journalize'}

    # Determine customer AR account
    customer_id = invoice.customer_id
    ar_account = DEFAULTS['ar']
    if customer_id:
        override = _get_org_gl_override(customer_id, 'ar')
        if override:
            ar_account = override

    # Accumulate postings by account
    postings = {}  # {account: {debit: Decimal, credit: Decimal, purpose: str}}

    def _add(account, side, amount, purpose):
        if account not in postings:
            postings[account] = {'debit': Decimal('0'), 'credit': Decimal('0'), 'purpose': purpose}
        postings[account][side] += amount

    for line in lines:
        # Get extended price from line
        price_data = line.price or {}
        extended = Decimal(str(price_data.get('extended', 0) or 0))
        if extended == 0:
            continue

        # Get item GL accounts
        item_id = line.item_fk_id
        if not item_id:
            item_data = line.item or {}
            item_id = item_data.get('item_id')

        item_gls = _get_item_gls(item_id) if item_id else {}

        # Revenue account — check customer override first, then item, then default
        rev_account = item_gls.get('revenue') or DEFAULTS['revenue']
        if customer_id:
            cust_rev = _get_org_gl_override(customer_id, 'revenue')
            if cust_rev:
                rev_account = cust_rev

        cogs_account = item_gls.get('cogs') or DEFAULTS['cogs']
        inv_account = item_gls.get('inventory') or DEFAULTS['inventory']

        # AR debit (what customer owes)
        _add(ar_account, 'debit', extended, 'accounts_receivable')

        # Revenue credit (what we earned)
        _add(rev_account, 'credit', extended, 'sales_revenue')

        # COGS debit + Inventory credit (cost side)
        # Use item cost if available, otherwise skip COGS
        qty_data = line.quantity or {}
        qty = Decimal(str(qty_data.get('active', 0) or 0))
        item_cost = Decimal('0')
        if item_id:
            try:
                Item = dj_apps.get_model('products', 'Item')
                item = Item.objects.get(pk=item_id)
                cost_data = item.cost or {}
                item_cost = Decimal(str(cost_data.get('standard', cost_data.get('average', 0)) or 0))
            except Exception:
                pass

        if item_cost > 0 and qty > 0:
            cogs_amount = item_cost * qty
            _add(cogs_account, 'debit', cogs_amount, 'cost_of_goods')
            _add(inv_account, 'credit', cogs_amount, 'inventory')

    if not postings:
        return {'created': 0, 'error': 'No amounts to post'}

    # Verify balance (debits = credits)
    total_debit = sum(p['debit'] for p in postings.values())
    total_credit = sum(p['credit'] for p in postings.values())
    if total_debit != total_credit:
        return {'created': 0, 'error': f'Out of balance: debit={total_debit} credit={total_credit}', 'postings': []}

    # Write GlJournal records
    created = 0
    posting_list = []
    with transaction.atomic():
        for account, data in postings.items():
            ida = f'{ida_prefix}SJ-{invoice.ida}-{account}' if ida_prefix else f'SJ-{invoice.ida}-{account}'
            if data['debit'] > 0:
                GlJournal.objects.create(
                    ida=ida,
                    account=account,
                    debit=float(data['debit']),
                    credit=None,
                    source='automation',
                    type='sales',
                    source_id=invoice_id,
                    source_model='invoice',
                )
                created += 1
                posting_list.append({'account': account, 'debit': float(data['debit']), 'credit': 0, 'purpose': data['purpose']})
            if data['credit'] > 0:
                GlJournal.objects.create(
                    ida=ida,
                    account=account,
                    debit=None,
                    credit=float(data['credit']),
                    source='automation',
                    type='sales',
                    source_id=invoice_id,
                    source_model='invoice',
                )
                created += 1
                posting_list.append({'account': account, 'debit': 0, 'credit': float(data['credit']), 'purpose': data['purpose']})

        # Mark invoice as journalized
        meta = invoice.metadata or {}
        meta['gl_accounts'] = {
            'event': 'invoice_journalized',
            'posted': True,
            'dt_posted': _now_ms(),
            'journal_count': created,
        }
        Invoice.objects.filter(pk=invoice_id).update(
            metadata=meta,
            is_locked=True,
            dt_modified=_now_ms(),
        )

    # Accrue commission if present on this invoice
    commission_result = None
    invoice.refresh_from_db()
    comm = invoice.commission or {}
    if comm.get('reps') and not comm.get('accrued'):
        try:
            from apps.transactions.services.commission import accrue_commission
            commission_result = accrue_commission(invoice_id, 'invoice', ida_prefix=ida_prefix)
            created += commission_result.get('created', 0)
            posting_list.extend(commission_result.get('entries', []))
        except Exception:
            pass  # commission accrual failure should not block invoice journalization

    result = {'created': created, 'postings': posting_list, 'invoice_ida': invoice.ida}
    if commission_result:
        result['commission_accrued'] = commission_result.get('total_accrued', 0)
    return result


def journalize_payment(payment_id: int, ida_prefix: str = '') -> dict:
    """Journalize a payment — checkbook convention (signed amounts).

    Positive amount (received): Cash debit, AR credit — money in.
    Negative amount (disbursed): AP debit, Cash credit — money out.

    Args:
        payment_id: Payment PK
        ida_prefix: prefix for journal ida

    Returns:
        {created: int, postings: [...], error: str}
    """
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')
    Payment = dj_apps.get_model('transactions', 'Payment')

    try:
        payment = Payment.objects.get(pk=payment_id)
    except Payment.DoesNotExist:
        return {'created': 0, 'error': f'Payment {payment_id} not found'}

    if GlJournal.objects.filter(source_id=payment_id, source_model='payment').exists():
        return {'created': 0, 'error': 'Already journalized'}

    amount = Decimal(str(getattr(payment, 'amount', 0) or 0))
    if amount == 0:
        return {'created': 0, 'error': 'Zero amount'}

    abs_amount = abs(amount)
    is_received = amount > 0  # positive = money in, negative = money out

    # Determine accounts — check org overrides
    cash_account = DEFAULTS['cash']

    if is_received:
        # AR receipt: Cash debit, AR credit
        offset_account = DEFAULTS['ar']
        invoice_id = getattr(payment, 'invoice_id', None)
        if invoice_id:
            try:
                Invoice = dj_apps.get_model('transactions', 'Invoice')
                inv = Invoice.objects.get(pk=invoice_id)
                if inv.customer_id:
                    cash_override = _get_org_gl_override(inv.customer_id, 'cash')
                    ar_override = _get_org_gl_override(inv.customer_id, 'ar')
                    if cash_override:
                        cash_account = cash_override
                    if ar_override:
                        offset_account = ar_override
            except Exception:
                pass
        debit_account, debit_purpose = cash_account, 'cash_receipt'
        credit_account, credit_purpose = offset_account, 'accounts_receivable'
    else:
        # Disbursement: Expense debit (from category bucket), Cash credit
        # Category → GL mapping lives in Setting select_lists
        offset_account = _get_category_gl(getattr(payment, 'category', ''))
        purchase_id = getattr(payment, 'purchase_id', None)
        if purchase_id:
            try:
                Purchase = dj_apps.get_model('transactions', 'Purchase')
                po = Purchase.objects.get(pk=purchase_id)
                if po.vendor_id:
                    cash_override = _get_org_gl_override(po.vendor_id, 'cash')
                    if cash_override:
                        cash_account = cash_override
            except Exception:
                pass
        debit_account, debit_purpose = offset_account, 'expense'
        credit_account, credit_purpose = cash_account, 'cash_disbursement'

    created = 0
    posting_list = []
    with transaction.atomic():
        ida_base = f'{ida_prefix}CJ-{payment.ida}' if ida_prefix else f'CJ-{payment.ida}'

        GlJournal.objects.create(
            ida=f'{ida_base}-{debit_account}',
            account=debit_account,
            debit=float(abs_amount),
            credit=None,
            source='automation',
            type='general',
            source_id=payment_id,
            source_model='payment',
        )
        created += 1
        posting_list.append({'account': debit_account, 'debit': float(abs_amount), 'credit': 0, 'purpose': debit_purpose})

        GlJournal.objects.create(
            ida=f'{ida_base}-{credit_account}',
            account=credit_account,
            debit=None,
            credit=float(abs_amount),
            source='automation',
            type='general',
            source_id=payment_id,
            source_model='payment',
        )
        created += 1
        posting_list.append({'account': credit_account, 'debit': 0, 'credit': float(abs_amount), 'purpose': credit_purpose})

        # Mark payment as journalized
        meta = payment.metadata or {}
        meta['gl_accounts'] = {
            'event': 'payment_journalized',
            'posted': True,
            'dt_posted': _now_ms(),
        }
        Payment.objects.filter(pk=payment_id).update(
            metadata=meta,
            is_locked=True,
            dt_modified=_now_ms(),
        )

    return {'created': created, 'postings': posting_list, 'payment_ida': payment.ida}


def journalize_purchase(purchase_id: int, ida_prefix: str = '') -> dict:
    """Journalize a purchase order receipt — Inventory debit, AP credit.

    For each purchase line:
      - Debit Inventory (item.gls.inventory)
      - Credit AP (item.gls.purchase or default)

    Args:
        purchase_id: Purchase PK
        ida_prefix: prefix for journal ida

    Returns:
        {created: int, postings: [...], error: str}
    """
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')
    Purchase = dj_apps.get_model('transactions', 'Purchase')
    PurchaseLine = dj_apps.get_model('transactions', 'PurchaseLine')

    try:
        purchase = Purchase.objects.get(pk=purchase_id)
    except Purchase.DoesNotExist:
        return {'created': 0, 'error': f'Purchase {purchase_id} not found'}

    if GlJournal.objects.filter(source_id=purchase_id, source_model='purchase').exists():
        return {'created': 0, 'error': 'Already journalized'}

    lines = PurchaseLine.objects.filter(purchase_id=purchase_id)
    if not lines.exists():
        return {'created': 0, 'error': 'No lines to journalize'}

    postings = {}

    def _add(account, side, amount, purpose):
        if account not in postings:
            postings[account] = {'debit': Decimal('0'), 'credit': Decimal('0'), 'purpose': purpose}
        postings[account][side] += amount

    for line in lines:
        # PurchaseLine uses 'cost' not 'price'
        cost_data = getattr(line, 'cost', None) or getattr(line, 'price', None) or {}
        extended = Decimal(str(cost_data.get('extended', 0) or 0))
        if extended == 0:
            continue

        item_id = line.item_fk_id
        if not item_id:
            item_data = line.item or {}
            item_id = item_data.get('item_id')

        item_gls = _get_item_gls(item_id) if item_id else {}

        inv_account = item_gls.get('inventory') or DEFAULTS['inventory']
        ap_account = item_gls.get('purchase') or DEFAULTS['ap']

        _add(inv_account, 'debit', extended, 'inventory')
        _add(ap_account, 'credit', extended, 'accounts_payable')

    if not postings:
        return {'created': 0, 'error': 'No amounts to post'}

    total_debit = sum(p['debit'] for p in postings.values())
    total_credit = sum(p['credit'] for p in postings.values())
    if total_debit != total_credit:
        return {'created': 0, 'error': f'Out of balance: debit={total_debit} credit={total_credit}'}

    created = 0
    posting_list = []
    with transaction.atomic():
        for account, data in postings.items():
            ida = f'{ida_prefix}PJ-{purchase.ida}-{account}' if ida_prefix else f'PJ-{purchase.ida}-{account}'
            if data['debit'] > 0:
                GlJournal.objects.create(
                    ida=ida,
                    account=account,
                    debit=float(data['debit']),
                    credit=None,
                    source='automation',
                    type='purchase',
                    source_id=purchase_id,
                    source_model='purchase',
                )
                created += 1
                posting_list.append({'account': account, 'debit': float(data['debit']), 'credit': 0, 'purpose': data['purpose']})
            if data['credit'] > 0:
                GlJournal.objects.create(
                    ida=ida,
                    account=account,
                    debit=None,
                    credit=float(data['credit']),
                    source='automation',
                    type='purchase',
                    source_id=purchase_id,
                    source_model='purchase',
                )
                created += 1
                posting_list.append({'account': account, 'debit': 0, 'credit': float(data['credit']), 'purpose': data['purpose']})

        meta = purchase.metadata or {}
        meta['gl_accounts'] = {
            'event': 'purchase_journalized',
            'posted': True,
            'dt_posted': _now_ms(),
        }
        Purchase.objects.filter(pk=purchase_id).update(
            metadata=meta,
            is_locked=True,
            dt_modified=_now_ms(),
        )

    return {'created': created, 'postings': posting_list, 'purchase_ida': purchase.ida}


def batch_journalize(ida_prefix: str = 'zzz-') -> dict:
    """Journalize all un-journalized invoices, payments, and purchases.

    Like wc2's batch journalize — finds all documents without gl_accounts.posted
    and journals them.

    Args:
        ida_prefix: prefix for all journal idas (default 'zzz-' for test)

    Returns:
        {invoices: [...], payments: [...], purchases: [...], total_created: int}
    """
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')
    Invoice = dj_apps.get_model('transactions', 'Invoice')
    Payment = dj_apps.get_model('transactions', 'Payment')
    Purchase = dj_apps.get_model('transactions', 'Purchase')

    results = {
        'invoices': [],
        'payments': [],
        'purchases': [],
        'total_created': 0,
        'errors': [],
    }

    # Find un-journalized invoices (have lines, not yet posted)
    posted_inv_ids = set(GlJournal.objects.filter(source_model='invoice').values_list('source_id', flat=True))
    invoices = Invoice.objects.exclude(pk__in=posted_inv_ids).filter(is_active=True)
    for inv in invoices:
        result = journalize_invoice(inv.pk, ida_prefix=ida_prefix)
        if result.get('created', 0) > 0:
            results['invoices'].append(result)
            results['total_created'] += result['created']
        elif result.get('error') and result['error'] != 'No lines to journalize':
            results['errors'].append(f'Invoice {inv.ida}: {result["error"]}')

    # Find un-journalized payments
    posted_pay_ids = set(GlJournal.objects.filter(source_model='payment').values_list('source_id', flat=True))
    payments = Payment.objects.exclude(pk__in=posted_pay_ids).filter(is_active=True)
    for pay in payments:
        result = journalize_payment(pay.pk, ida_prefix=ida_prefix)
        if result.get('created', 0) > 0:
            results['payments'].append(result)
            results['total_created'] += result['created']
        elif result.get('error') and result['error'] != 'Zero amount':
            results['errors'].append(f'Payment {pay.ida}: {result["error"]}')

    # Find un-journalized purchases
    posted_po_ids = set(GlJournal.objects.filter(source_model='purchase').values_list('source_id', flat=True))
    purchases = Purchase.objects.exclude(pk__in=posted_po_ids).filter(is_active=True)
    for po in purchases:
        result = journalize_purchase(po.pk, ida_prefix=ida_prefix)
        if result.get('created', 0) > 0:
            results['purchases'].append(result)
            results['total_created'] += result['created']
        elif result.get('error') and result['error'] != 'No lines to journalize':
            results['errors'].append(f'Purchase {po.ida}: {result["error"]}')

    return results


# ---------------------------------------------------------------------------
# BOM Journal — inventory transfer on assembly build
# ---------------------------------------------------------------------------

def journalize_bom_build(batch_id: str, parent_item_id: int, qty: Decimal, component_costs: list[dict], ida_prefix: str = '') -> dict:
    """Journal entry for a BOM assembly build.

    Debits finished-goods inventory (parent), credits component inventory (each child).
    component_costs: [{item_id, item_ida, cost, qty}] from consume_bom.

    Args:
        batch_id: from consume_bom batch_id
        parent_item_id: assembled item
        qty: build quantity
        component_costs: list of consumed components with costs
    """
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')

    if GlJournal.objects.filter(batch_id=batch_id, source_model='bom_build').exists():
        return {'created': 0, 'error': 'Already journalized'}

    parent_gls = _get_item_gls(parent_item_id)
    fg_account = parent_gls.get('inventory') or DEFAULTS['inventory']

    postings = {}

    def _add(account, side, amount, purpose):
        if account not in postings:
            postings[account] = {'debit': Decimal('0'), 'credit': Decimal('0'), 'purpose': purpose}
        postings[account][side] += amount

    # Total component cost becomes finished goods value
    total_component_cost = Decimal('0')
    for comp in component_costs:
        comp_gls = _get_item_gls(comp.get('item_id'))
        comp_account = comp_gls.get('inventory') or DEFAULTS['inventory']
        comp_cost = Decimal(str(comp.get('cost', 0))) * Decimal(str(comp.get('qty', 0)))
        _add(comp_account, 'credit', comp_cost, 'component_consumed')
        total_component_cost += comp_cost

    # Finished goods debit
    _add(fg_account, 'debit', total_component_cost, 'finished_goods_produced')

    if not postings:
        return {'created': 0, 'error': 'No amounts to post'}

    created = 0
    posting_list = []
    with transaction.atomic():
        for account, data in postings.items():
            for side in ('debit', 'credit'):
                if data[side] > 0:
                    GlJournal.objects.create(
                        ida=f'{ida_prefix}BM-{batch_id[:8]}-{account}',
                        account=account,
                        debit=float(data['debit']) if side == 'debit' else None,
                        credit=float(data['credit']) if side == 'credit' else None,
                        source='automation',
                        type='bom',
                        source_id=parent_item_id,
                        source_model='bom_build',
                        batch_id=batch_id,
                    )
                    created += 1
                    posting_list.append({'account': account, side: float(data[side]), 'purpose': data['purpose']})

    return {'created': created, 'postings': posting_list, 'batch_id': batch_id}


def journalize_adjustment(item_id: int, qty: Decimal, cost: Decimal, reason: str = '', ida_prefix: str = '') -> dict:
    """Journal entry for an inventory adjustment (scrap, draw, count variance).

    Debit/credit inventory + offset to adjustment expense account.
    Positive qty = found extra (debit inventory, credit adjustment).
    Negative qty = lost/scrapped (credit inventory, debit adjustment).
    """
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')

    item_gls = _get_item_gls(item_id)
    inv_account = item_gls.get('inventory') or DEFAULTS['inventory']
    adj_account = item_gls.get('cogs') or DEFAULTS['cogs']  # adjustments hit COGS by default

    amount = abs(qty * cost)
    if amount == 0:
        return {'created': 0, 'error': 'Zero amount'}

    created = 0
    posting_list = []
    batch_id = f'ADJ-{item_id}-{int(time.time())}'

    with transaction.atomic():
        if qty > 0:
            # Found extra inventory
            GlJournal.objects.create(
                ida=f'{ida_prefix}ADJ-{inv_account}', account=inv_account,
                debit=float(amount), credit=None, source='automation', type='adjustment',
                source_id=item_id, source_model='adjustment', batch_id=batch_id,
                note=reason,
            )
            GlJournal.objects.create(
                ida=f'{ida_prefix}ADJ-{adj_account}', account=adj_account,
                debit=None, credit=float(amount), source='automation', type='adjustment',
                source_id=item_id, source_model='adjustment', batch_id=batch_id,
                note=reason,
            )
        else:
            # Lost/scrapped inventory
            GlJournal.objects.create(
                ida=f'{ida_prefix}ADJ-{adj_account}', account=adj_account,
                debit=float(amount), credit=None, source='automation', type='adjustment',
                source_id=item_id, source_model='adjustment', batch_id=batch_id,
                note=reason,
            )
            GlJournal.objects.create(
                ida=f'{ida_prefix}ADJ-{inv_account}', account=inv_account,
                debit=None, credit=float(amount), source='automation', type='adjustment',
                source_id=item_id, source_model='adjustment', batch_id=batch_id,
                note=reason,
            )
        created = 2
        posting_list = [
            {'account': inv_account, 'amount': float(amount), 'side': 'debit' if qty > 0 else 'credit'},
            {'account': adj_account, 'amount': float(amount), 'side': 'credit' if qty > 0 else 'debit'},
        ]

    return {'created': created, 'postings': posting_list, 'batch_id': batch_id}


# ---------------------------------------------------------------------------
# Account summary — $ by account code by period (for Accounting tab)
# ---------------------------------------------------------------------------

def account_summary_by_period(year: int, month: int) -> list[dict]:
    """Summarize GL journal entries by account for a given month.

    Returns the data users retype into their accounting program:
    [{account, account_name, debit, credit, net}] sorted by account.
    """
    from django.db.models import Sum, Q
    from datetime import date

    GlJournal = dj_apps.get_model('accounts', 'GlJournal')
    GlAccount = dj_apps.get_model('accounts', 'GlAccount')

    period_start = date(year, month, 1)
    if month == 12:
        period_end = date(year + 1, 1, 1)
    else:
        period_end = date(year, month + 1, 1)

    # Convert to epoch ms for dt_created filter
    import calendar
    start_ms = int(calendar.timegm(period_start.timetuple()) * 1000)
    end_ms = int(calendar.timegm(period_end.timetuple()) * 1000)

    entries = (
        GlJournal.objects
        .filter(dt_created__gte=start_ms, dt_created__lt=end_ms)
        .values('account')
        .annotate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit'),
        )
        .order_by('account')
    )

    # Build account name lookup
    account_names = dict(
        GlAccount.objects.filter(is_active=True)
        .values_list('ida', 'name')
    )

    result = []
    total_debit = Decimal('0')
    total_credit = Decimal('0')
    for row in entries:
        d = Decimal(str(row['total_debit'] or 0))
        c = Decimal(str(row['total_credit'] or 0))
        total_debit += d
        total_credit += c
        result.append({
            'account': row['account'],
            'account_name': account_names.get(row['account'], ''),
            'debit': float(d),
            'credit': float(c),
            'net': float(d - c),
        })

    return result


# ---------------------------------------------------------------------------
# Export formatter — one function, all formats
# ---------------------------------------------------------------------------

def export_journals(
    year: int,
    month: int,
    format: str = 'csv',
    division: str = '',
) -> str:
    """Export GL journal entries for a period in the specified format.

    Formats: 'csv', 'json', 'quickbooks_iif', 'tab'
    This is what the user downloads or sends to their bookkeeper.
    Most users just read the account_summary_by_period screen and retype.
    """
    import json as json_lib
    from datetime import date

    GlJournal = dj_apps.get_model('accounts', 'GlJournal')

    period_start = date(year, month, 1)
    if month == 12:
        period_end = date(year + 1, 1, 1)
    else:
        period_end = date(year, month + 1, 1)

    import calendar
    start_ms = int(calendar.timegm(period_start.timetuple()) * 1000)
    end_ms = int(calendar.timegm(period_end.timetuple()) * 1000)

    qs = GlJournal.objects.filter(dt_created__gte=start_ms, dt_created__lt=end_ms).order_by('account', 'id')
    if division:
        qs = qs.filter(division=division)

    records = list(qs.values('account', 'debit', 'credit', 'type', 'source_model',
                             'source_id', 'division', 'batch_id', 'note', 'ida'))

    if format == 'json':
        return json_lib.dumps({'period': f'{year}-{month:02d}', 'entries': records}, indent=2, default=str)

    if format == 'quickbooks_iif':
        lines = ['!TRNS\tTRNSTYPE\tDATE\tACCNT\tAMOUNT\tMEMO']
        lines.append('!SPL\tTRNSTYPE\tDATE\tACCNT\tAMOUNT\tMEMO')
        lines.append('!ENDTRNS')
        for rec in records:
            amt = (rec['debit'] or 0) - (rec['credit'] or 0)
            lines.append(f'TRNS\tGENERAL JOURNAL\t{period_start.strftime("%m/%d/%Y")}\t{rec["account"]}\t{amt:.2f}\t{rec.get("note", "")}')
            lines.append(f'SPL\tGENERAL JOURNAL\t{period_start.strftime("%m/%d/%Y")}\t{rec["account"]}\t{-amt:.2f}\t')
            lines.append('ENDTRNS')
        return '\n'.join(lines)

    if format == 'tab':
        lines = ['Account\tDebit\tCredit\tType\tDivision\tBatch\tNote']
        for rec in records:
            lines.append(f'{rec["account"]}\t{rec["debit"] or ""}\t{rec["credit"] or ""}\t{rec["type"] or ""}\t{rec["division"] or ""}\t{rec["batch_id"] or ""}\t{rec.get("note", "")}')
        return '\n'.join(lines)

    # Default: CSV
    lines = ['Account,Debit,Credit,Type,Division,Batch,Note']
    for rec in records:
        note = str(rec.get('note', '')).replace(',', ';').replace('"', "'")
        lines.append(f'{rec["account"]},{rec["debit"] or ""},{rec["credit"] or ""},{rec["type"] or ""},{rec["division"] or ""},{rec["batch_id"] or ""},"{note}"')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Tax summary by jurisdiction — for quarterly filing
# ---------------------------------------------------------------------------

def tax_summary_by_period(year: int, month: int, months: int = 1) -> list[dict]:
    """Summarize tax collected by jurisdiction for a given period.

    Small businesses file sales tax quarterly — they need total by state/jurisdiction.
    months=3 gives a quarterly view.

    Returns: [{jurisdiction, jurisdiction_name, tax_collected, invoice_count}]
    """
    from datetime import date
    import calendar

    InvoiceLine = dj_apps.get_model('transactions', 'InvoiceLine')

    period_start = date(year, month, 1)
    end_month = month + months - 1
    end_year = year
    while end_month > 12:
        end_month -= 12
        end_year += 1
    period_end = date(end_year, end_month + 1, 1) if end_month < 12 else date(end_year + 1, 1, 1)

    start_ms = int(calendar.timegm(period_start.timetuple()) * 1000)
    end_ms = int(calendar.timegm(period_end.timetuple()) * 1000)

    lines = InvoiceLine.objects.filter(
        dt_created__gte=start_ms, dt_created__lt=end_ms,
    ).values_list('tax', 'invoice_id')

    by_jurisdiction: dict[str, dict] = {}
    invoice_ids_by_jur: dict[str, set] = {}

    for tax_data, inv_id in lines:
        if not isinstance(tax_data, dict):
            continue
        jur = tax_data.get('jurisdiction', '') or tax_data.get('code', '') or 'unknown'
        tax_amt = Decimal(str(tax_data.get('amount', 0) or tax_data.get('sales_amount', 0) or 0))
        if tax_amt == 0:
            continue
        if jur not in by_jurisdiction:
            by_jurisdiction[jur] = {'tax_collected': Decimal('0'), 'jurisdiction_name': jur}
            invoice_ids_by_jur[jur] = set()
        by_jurisdiction[jur]['tax_collected'] += tax_amt
        invoice_ids_by_jur[jur].add(inv_id)

    return [
        {'jurisdiction': jur, 'jurisdiction_name': data['jurisdiction_name'],
         'tax_collected': float(data['tax_collected']),
         'invoice_count': len(invoice_ids_by_jur.get(jur, set()))}
        for jur, data in sorted(by_jurisdiction.items())
    ]


# ---------------------------------------------------------------------------
# Reconciliation flag — period-level "I verified this"
# ---------------------------------------------------------------------------

def mark_period_reconciled(year: int, month: int, reconciled_by: str = '') -> dict:
    """Mark a period as reconciled — user confirms GL export matches accounting package."""
    from apps.core.models.setting import Setting
    import time

    setting, _ = Setting.objects.get_or_create(
        purpose='accounting_interface',
        parent_model='setting',
        defaults={'ida': 'accounting-interface', 'config': {}},
    )
    config = setting.config or {}
    reconciled = config.setdefault('reconciled_periods', {})
    key = f'{year}-{month:02d}'
    reconciled[key] = {
        'reconciled': True,
        'reconciled_by': reconciled_by,
        'dt_reconciled': int(time.time() * 1000),
    }
    setting.config = config
    setting.save(update_fields=['config'])
    return reconciled[key]


def get_reconciliation_status(year: int, month: int) -> dict:
    """Check if a period has been marked as reconciled."""
    from apps.core.models.setting import Setting
    try:
        setting = Setting.objects.get(purpose='accounting_interface', parent_model='setting')
        key = f'{year}-{month:02d}'
        return (setting.config or {}).get('reconciled_periods', {}).get(key, {'reconciled': False})
    except Setting.DoesNotExist:
        return {'reconciled': False}
