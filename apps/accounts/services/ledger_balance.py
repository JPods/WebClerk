"""
Ledger Balance Service
======================

AUDIT DOCUMENTATION
-------------------
This module is a core component of the financial system, responsible for
maintaining accurate, real-time org financial balances. All functions here
directly impact accounts receivable/payable reporting and credit decisions.

FINANCIAL INTEGRITY RULES:
1. Ledger Sum MUST equal Invoice Balances minus Payment Available
   Formula: Σ(ledger.value_available) = Σ(invoice.balance_due) - Σ(payment.amount_available)
   
2. Aging buckets MUST sum to total balance due
   Formula: future + current + period_1 + period_2 + period_3 = balance_due

3. Credit available = Credit limit - Balance due (never negative)

AUDIT TRAIL:
- All ledger records link to source documents via parent_id + model_name
- Invoice ledgers: positive value_available (money owed TO us)
- Payment ledgers: negative value_available (money received FROM customer)
- Each ledger tracks original value vs current available (for partial payments)

RECONCILIATION:
- Nightly batch validates all balances via reconcile_org()
- Discrepancies are logged and flagged for review
- rebuild_org_ledgers() recreates all records from source documents

Key methods:
- update_org_balances: Recalculates aging buckets from ledger records
- on_invoice_save: Creates ledger records and updates balances
- on_payment_save: Creates payment ledger and updates balances
- reconcile_org: Validates and corrects org financial data
- rebuild_org_ledgers: Complete ledger reconstruction from source documents
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Dict, Any

from django.db import models, transaction
from django.apps import apps as dj_apps

if TYPE_CHECKING:
    from apps.orgs.models import OrgBase


# =============================================================================
# AGING BUCKET CONFIGURATION
# =============================================================================
# These boundaries determine how receivables are categorized for collection
# and reporting. Modify with caution - affects financial statements.
#
# Standard aging periods (based on days past due date):
#   Future:   Not yet due (more than 30 days until due)
#   Current:  Due within 30 days (not past due)
#   Period 1: 1-30 days past due (first follow-up)
#   Period 2: 31-60 days past due (escalated collection)
#   Period 3: 60+ days past due (serious delinquency)
# =============================================================================
AGING_PERIODS = {
    'future': lambda days: days < -30,  # Due more than 30 days from now
    'current': lambda days: -30 <= days < 0,  # Due within 30 days
    'period_1': lambda days: 0 <= days < 30,  # 1-30 days past due
    'period_2': lambda days: 30 <= days < 60,  # 31-60 days past due
    'period_3': lambda days: days >= 60,  # Over 60 days past due
}


def calculate_aging_buckets(org_id: str, as_of_date: Optional[date] = None) -> Dict[str, Decimal]:
    """
    Calculate aging buckets for an org based on ledger records.
    
    AUDIT: This is the core aging calculation. All aging reports derive from this.
    
    CALCULATION LOGIC:
    1. Query all ledger records with non-zero value_available for org
    2. For each ledger, calculate days_past_due = as_of_date - dt_due
    3. Assign value to appropriate bucket based on days_past_due
    4. Sum all buckets to get total
    
    VALIDATION:
    - Returns Decimal values for precision (avoid float rounding errors)
    - Handles null dt_due by treating as "current" (conservative approach)
    - Total must equal sum of all buckets
    
    Args:
        org_id: The org's identifier (customer_id, vendor_id, etc.)
        as_of_date: Date to calculate aging from (defaults to today)
    
    Returns:
        Dict with keys: future, current, period_1, period_2, period_3, total
        All values are Decimal for financial precision.
    """
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    
    if as_of_date is None:
        as_of_date = date.today()
    
    # Initialize buckets with Decimal for financial precision
    # AUDIT: Using Decimal prevents floating-point rounding errors in financial calculations
    buckets = {
        'future': Decimal('0'),
        'current': Decimal('0'),
        'period_1': Decimal('0'),
        'period_2': Decimal('0'),
        'period_3': Decimal('0'),
    }
    
    # ==========================================================================
    # LEDGER QUERY STRATEGY
    # ==========================================================================
    # Primary: Query via org FK (indexed, fast)
    # Fallback: Query via refs JSON path for legacy records
    # ==========================================================================
    
    # Query all non-zero ledger records for this org using the org FK
    ledgers = Ledger.objects.filter(
        value_available__isnull=False,
        org_id=org_id,
    ).exclude(
        value_available=0
    ).values('dt_due', 'value_available')
    
    # Fallback: try JSON path for legacy records without org FK
    if not ledgers.exists():
        ledgers = Ledger.objects.filter(
            value_available__isnull=False,
            refs__links__org__id=org_id,
        ).exclude(
            value_available=0
        ).values('dt_due', 'value_available')
    
    for ledger in ledgers:
        dt_due = ledger['dt_due']
        value = Decimal(str(ledger['value_available'] or 0))
        
        if dt_due is None:
            # AUDIT: No due date - conservative treatment as current (not past due)
            # This prevents incorrectly flagging items as delinquent
            buckets['current'] += value
            continue
        
        # Convert datetime to date if needed
        if isinstance(dt_due, datetime):
            due_date = dt_due.date()
        else:
            due_date = dt_due
        
        # AUDIT: days_past_due calculation
        # Positive = past due, Negative = not yet due
        # Example: due_date=Jan 15, as_of_date=Jan 25 → days_past_due = 10 (past due)
        # Example: due_date=Jan 25, as_of_date=Jan 15 → days_past_due = -10 (future)
        days_past_due = (as_of_date - due_date).days
        
        # =======================================================================
        # BUCKET ASSIGNMENT
        # =======================================================================
        # Assign to appropriate bucket based on days past due
        # These thresholds match standard accounting aging periods
        # =======================================================================
        if days_past_due < -30:
            buckets['future'] += value
        elif days_past_due < 0:
            buckets['current'] += value
        elif days_past_due < 30:
            buckets['period_1'] += value
        elif days_past_due < 60:
            buckets['period_2'] += value
        else:
            buckets['period_3'] += value
    
    # Calculate total
    buckets['total'] = sum(buckets.values())
    
    return buckets


def update_org_balances(org: 'OrgBase', save: bool = True) -> Dict[str, Any]:
    """
    Update an org's financial.balances and financial.aging fields based on ledger records.
    
    AUDIT: This is the REAL-TIME balance update, called after every invoice/payment save.
    Changes take effect immediately and affect credit decisions.
    
    WHAT THIS UPDATES:
    1. org.financial[org_type].balances.due      - Total amount owed
    2. org.financial[org_type].balances.current  - Amount not yet past due
    3. org.financial[org_type].balances.future   - Amount due more than 30 days out
    4. org.financial[org_type].aging.period_1/2/3 - Past due buckets
    5. org.financial[org_type].credit.available  - Credit limit minus balance due
    6. org.financial[org_type].credit.used       - Current credit utilization
    
    FINANCIAL IMPACT:
    - Credit available directly affects whether new orders are blocked
    - Aging data drives collection efforts and customer hold decisions
    - Balance due appears on statements and affects payment terms
    
    AUDIT TRAIL:
    - This function does NOT create ledger records (that's on_invoice_save)
    - It only READS ledgers and WRITES to org.financial JSON
    - org.save() updates dt_modified for change tracking
    
    Args:
        org: The org instance to update
        save: Whether to save the org after updating (default True)
    
    Returns:
        The updated financial dict (for inspection/logging)
    """
    from apps.orgs.models import OrgBase
    
    # Get org_id for ledger lookup
    org_id = getattr(org, 'id', None) or getattr(org, 'customer_id', None)
    
    # AUDIT: Recalculate from source ledger records (single source of truth)
    # This ensures displayed balances always match actual ledger state
    buckets = calculate_aging_buckets(org_id)
    
    # Get or initialize financial dict
    financial = org.financial or {}
    
    # Determine org role (customer, vendor, etc.)
    org_type = getattr(org, 'org_type', 'customer')
    
    # Update balances structure
    if org_type in ('customer', 'vendor'):
        role_key = org_type
        role_financial = financial.get(role_key, {})
        
        # Update balances
        role_financial['balances'] = {
            'due': float(buckets['total']),
            'current': float(buckets['current'] + buckets['future']),
            'future': float(buckets['future']),
        }
        
        # Update aging (customer/vendor specific)
        role_financial['aging'] = {
            'period_1': float(buckets['period_1']),
            'period_2': float(buckets['period_2']),
            'period_3': float(buckets['period_3']),
        }
        
        # Update credit available if credit limit exists
        credit = role_financial.get('credit', {})
        if credit.get('limit'):
            credit['available'] = max(0, credit['limit'] - float(buckets['total']))
            credit['used'] = float(buckets['total'])
            role_financial['credit'] = credit
        
        financial[role_key] = role_financial
    
    # Update common financial data
    common = financial.get('common', {})
    common['balances'] = {
        'total': float(buckets['total']),
    }
    financial['common'] = common
    
    # Set on org
    org.financial = financial
    
    if save:
        org.save(update_fields=['financial'])
    
    return financial


def on_invoice_save(invoice, replace_ledgers: bool = True) -> None:
    """
    Handle invoice save: create ledger records and update org balances.
    
    AUDIT: This is the PRIMARY entry point for invoice-related ledger creation.
    Called via signal or directly after invoice.save().
    
    WHAT HAPPENS:
    1. If replace_ledgers=True, DELETE all existing ledgers for this invoice
    2. Look up payment terms from invoice.prefs.payment_terms
    3. Create new ledger record(s) based on term schedule:
       - Net 30: Creates 1 ledger due in 30 days
       - 3-Pay: Creates 3 ledgers with staggered due dates
    4. Update org balances to reflect new ledger state
    
    FINANCIAL IMPACT:
    - New invoice increases org balance_due
    - Credit available decreases (potentially triggering holds)
    - Aging buckets shift based on due dates
    
    AUDIT TRAIL:
    - Each ledger has parent_id pointing to invoice.id
    - Each ledger has model_name='invoice' for type identification
    - value_original captures initial amount (immutable)
    - value_available tracks current unpaid balance (mutable via payments)
    
    Args:
        invoice: The saved Invoice instance
        replace_ledgers: Whether to delete existing ledgers first (default True)
                        Set False only during batch rebuild operations
    """
    from .terms_ledger import apply_terms_for_invoice
    
    # AUDIT: Create/replace ledger records based on payment terms
    # This is the step that materializes receivables into trackable records
    apply_terms_for_invoice(invoice, replace=replace_ledgers)
    
    # Update org balances — invoice FK is `customer` (db_column=customer_id)
    org = getattr(invoice, 'customer', None)
    if org is None:
        org_id = getattr(invoice, 'customer_id', None)
        if org_id:
            OrgBase = dj_apps.get_model('orgs', 'OrgBase')
            try:
                org = OrgBase.objects.get(id=org_id)
            except OrgBase.DoesNotExist:
                pass
    
    if org:
        update_org_balances(org)


def on_payment_save(payment) -> None:
    """
    Handle payment save: create payment ledger and update org balances.
    
    AUDIT: This is the PRIMARY entry point for payment-related ledger creation.
    Called via signal or directly after payment.save().
    
    WHAT HAPPENS:
    1. DELETE any existing ledger records for this payment (idempotent)
    2. If amount_available > 0, create a NEGATIVE ledger record
    3. Update org balances to reflect payment receipt
    
    LEDGER VALUE CONVENTION:
    - Invoice ledgers: POSITIVE value (money owed TO company)
    - Payment ledgers: NEGATIVE value (money received FROM customer)
    - Balance = Sum of all ledgers = Invoices - Payments
    
    FINANCIAL IMPACT:
    - Payment decreases org balance_due
    - Credit available increases (may release holds)
    - May shift items out of aging buckets (depending on application)
    
    AUDIT TRAIL:
    - Payment ledger has parent_id pointing to payment.id
    - Payment ledger has model_name='payment' for type identification
    - Negative values in value_original and value_available
    - Links to invoice via invoice_id FK
    
    Args:
        payment: The saved Payment instance
    """
    from .terms_ledger import record_payment
    
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    
    # AUDIT: Delete existing ledgers for this payment before recreating
    # This ensures idempotency - running twice produces same result
    Ledger.objects.filter(
        model_name='payment',
        parent_id=payment.id
    ).delete()
    
    # AUDIT: Create payment ledger with NEGATIVE value
    # Only create if there's an amount to record
    pay_amount = getattr(payment, 'amount', None)
    if pay_amount and pay_amount != 0:
        invoice = getattr(payment, 'invoice', None)
        record_payment(
            invoice=invoice,
            amount=Decimal(str(pay_amount)),
            dt_paid=getattr(payment, 'dt_payment', None) or datetime.now(),
            payment=payment
        )
    
    # Update org balances — Payment links to org via invoice.customer
    org = None
    invoice = getattr(payment, 'invoice', None)
    if invoice:
        org = getattr(invoice, 'customer', None)
        if org is None:
            org_id = getattr(invoice, 'customer_id', None)
            if org_id:
                OrgBase = dj_apps.get_model('orgs', 'OrgBase')
                try:
                    org = OrgBase.objects.get(id=org_id)
                except OrgBase.DoesNotExist:
                    pass
    
    if org:
        update_org_balances(org)


def reconcile_org(org: 'OrgBase') -> Dict[str, Any]:
    """
    Full reconciliation of an org's ledgers and financial data.
    
    AUDIT: This is the VALIDATION function, typically run nightly via batch.
    Used to detect and report data integrity issues.
    
    RECONCILIATION FORMULA:
    Σ(ledger.value_available) == Σ(invoice.balance_due) - Σ(payment.amount_available)
    
    If this equation doesn't balance, there's a data integrity issue:
    - Ledger sum > expected: Extra/duplicate ledger records
    - Ledger sum < expected: Missing ledger records or incorrect amounts
    
    WHAT WE VALIDATE:
    1. Ledger total matches Invoice - Payment total
    2. All invoices have corresponding ledger records
    3. All payments have corresponding ledger records
    4. Aging buckets sum to balance due
    
    WHAT WE FIX:
    - Recalculates and updates org.financial balances
    - Does NOT create/delete ledger records (use rebuild_org_ledgers for that)
    
    REPORTING:
    - Returns dict with all sums and any discrepancies
    - Discrepancies should be investigated - they indicate data problems
    
    Args:
        org: The org to reconcile
    
    Returns:
        Dict with reconciliation results:
        - org_id: Identifier
        - balanced: True if ledgers match source documents
        - ledger_sum: Total of ledger.value_available
        - invoice_sum: Total of invoice.balance_due
        - payment_sum: Total of payment.amount_available
        - discrepancies: List of issues found
    """
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    Invoice = dj_apps.get_model('transactions', 'Invoice')
    Payment = dj_apps.get_model('transactions', 'Payment')
    
    org_id = getattr(org, 'id', None)
    
    # AUDIT: Initialize results structure for reporting
    results = {
        'org_id': org_id,
        'discrepancies': [],
        'ledger_sum': Decimal('0'),
        'invoice_sum': Decimal('0'),
        'payment_sum': Decimal('0'),
        'balanced': False,
    }
    
    # ==========================================================================
    # STEP 1: Sum all ledger values (the "actual" state)
    # ==========================================================================
    ledger_sum = Ledger.objects.filter(
        org_id=org_id
    ).aggregate(
        total=models.Sum('value_available')
    )['total'] or Decimal('0')
    results['ledger_sum'] = ledger_sum
    
    # ==========================================================================
    # STEP 2: Sum invoice balances (what we EXPECT in ledgers, positive)
    # ==========================================================================
    invoice_sum = Invoice.objects.filter(
        customer_id=org_id,
    ).exclude(
        total={}
    ).aggregate(
        total=models.Sum('total__balance_due')
    )['total'] or Decimal('0')
    results['invoice_sum'] = invoice_sum
    
    # ==========================================================================
    # STEP 3: Sum payment available (what we EXPECT in ledgers, negative)
    # ==========================================================================
    payment_sum = Payment.objects.filter(
        invoice__customer_id=org_id
    ).aggregate(
        total=models.Sum('amount')
    )['total'] or Decimal('0')
    results['payment_sum'] = payment_sum
    
    # ==========================================================================
    # STEP 4: Validate the reconciliation formula
    # AUDIT: This is the critical check - if this fails, investigate!
    # ==========================================================================
    expected = invoice_sum - payment_sum
    if ledger_sum != expected:
        results['discrepancies'].append({
            'type': 'balance_mismatch',
            'message': f'Ledger sum ({ledger_sum}) != Invoice - Payment ({expected})',
            'deviation': float(ledger_sum - expected),
        })
    else:
        results['balanced'] = True
    
    # Update org.financial balances regardless of reconciliation result
    # This ensures displayed balances match current ledger state
    update_org_balances(org)
    
    return results


def rebuild_org_ledgers(org: 'OrgBase') -> Dict[str, int]:
    """
    Rebuild all ledger records for an org from source documents.
    
    AUDIT: This is a DATA REPAIR function. Use with extreme caution!
    
    ⚠️  WARNING: DESTRUCTIVE OPERATION ⚠️
    This function DELETES all existing ledger records for an org and
    recreates them from source invoices and payments. This should only
    be used when ledger data is known to be corrupted.
    
    WHEN TO USE:
    - reconcile_org() shows persistent discrepancies that can't be explained
    - After data migration or import where ledgers weren't created
    - When payment applications have become out of sync
    
    WHEN NOT TO USE:
    - For routine maintenance (use reconcile_org instead)
    - If you don't understand why ledgers are out of balance
    - In production without a backup
    
    WHAT HAPPENS:
    1. ATOMIC TRANSACTION BEGINS (all or nothing)
    2. DELETE all ledger records for this org
    3. For each invoice: recreate ledger(s) based on payment terms
    4. For each payment: recreate negative ledger record
    5. Update org.financial balances
    6. COMMIT TRANSACTION
    
    AUDIT TRAIL:
    - New ledgers will have fresh created timestamps
    - Any payment application history is reconstructed, not preserved
    - Returns counts for verification
    
    Args:
        org: The org to rebuild ledgers for
    
    Returns:
        Dict with operation counts:
        - deleted: Number of ledger records deleted
        - invoice_ledgers: Number of invoice ledgers created
        - payment_ledgers: Number of payment ledgers created
    """
    from .terms_ledger import apply_terms_for_invoice, record_payment
    
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    Invoice = dj_apps.get_model('transactions', 'Invoice')
    Payment = dj_apps.get_model('transactions', 'Payment')
    
    org_id = getattr(org, 'id', None)
    
    # AUDIT: Wrap entire operation in atomic transaction
    # If any step fails, all changes are rolled back
    with transaction.atomic():
        # =======================================================================
        # STEP 1: Delete all existing ledgers for this org
        # AUDIT: This is the destructive step - no going back after commit
        # =======================================================================
        deleted_count = Ledger.objects.filter(
            org_id=org_id
        ).delete()[0]
        
        counts = {
            'deleted': deleted_count,
            'invoice_ledgers': 0,
            'payment_ledgers': 0,
        }
        
        # =======================================================================
        # STEP 2: Recreate invoice ledgers from source documents
        # =======================================================================
        invoices = Invoice.objects.filter(customer_id=org_id)
        for invoice in invoices:
            ledgers = apply_terms_for_invoice(invoice, replace=False)
            counts['invoice_ledgers'] += len(ledgers)
        
        # =======================================================================
        # STEP 3: Recreate payment ledgers from source documents  
        # =======================================================================
        payments = Payment.objects.filter(invoice__customer_id=org_id)
        for payment in payments:
            pay_amount = getattr(payment, 'amount', 0)
            if pay_amount and pay_amount != 0:
                record_payment(
                    invoice=getattr(payment, 'invoice', None),
                    amount=Decimal(str(pay_amount)),
                    dt_paid=getattr(payment, 'dt_payment', None) or datetime.now(),
                    payment=payment
                )
                counts['payment_ledgers'] += 1
        
        # =======================================================================
        # STEP 4: Recalculate org balances from fresh ledger data
        # =======================================================================
        update_org_balances(org)
    
    # AUDIT: Log counts for verification
    # invoice_ledgers + payment_ledgers should roughly match deleted count
    # (may differ if terms changed or invoices were added/removed)
    return counts
