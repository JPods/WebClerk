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
    """Journalize a payment — Cash debit, AR credit.

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

    # Determine accounts — check org overrides
    cash_account = DEFAULTS['cash']
    ar_account = DEFAULTS['ar']

    # Payment may link to an invoice which has a customer
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
                    ar_account = ar_override
        except Exception:
            pass

    created = 0
    posting_list = []
    with transaction.atomic():
        ida_base = f'{ida_prefix}CJ-{payment.ida}' if ida_prefix else f'CJ-{payment.ida}'
        # Cash debit
        GlJournal.objects.create(
            ida=f'{ida_base}-{cash_account}',
            account=cash_account,
            debit=float(amount),
            credit=None,
            source='automation',
            type='general',
            source_id=payment_id,
            source_model='payment',
        )
        created += 1
        posting_list.append({'account': cash_account, 'debit': float(amount), 'credit': 0, 'purpose': 'cash_receipt'})

        # AR credit
        GlJournal.objects.create(
            ida=f'{ida_base}-{ar_account}',
            account=ar_account,
            debit=None,
            credit=float(amount),
            source='automation',
            type='general',
            source_id=payment_id,
            source_model='payment',
        )
        created += 1
        posting_list.append({'account': ar_account, 'debit': 0, 'credit': float(amount), 'purpose': 'accounts_receivable'})

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
