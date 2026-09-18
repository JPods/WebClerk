"""
One-shot script: Apply 4 terms equally across invoices, create ledger entries.
Run via: python manage.py shell < tools/apply_terms_and_ledgers.py
"""
from apps.transactions.models import Invoice
from apps.accounts.models import Term, Ledger
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

terms = list(Term.objects.all().order_by("id"))
invoices = list(Invoice.objects.filter(is_deleted=False).order_by("id"))
print(f"Terms: {[t.name for t in terms]}")
print(f"Invoices: {len(invoices)}")

now = timezone.now()
ledgers_created = 0

for i, inv in enumerate(invoices):
    term = terms[i % len(terms)]

    # Update invoice terms field
    inv.terms = term.name
    inv.save(update_fields=["terms"])

    # Payment details
    period_count = term.period_count or 1
    days_in_period = term.days_in_period or term.days_due or 30
    gt = Decimal(str(inv.totals.get("grand_total", 0) if inv.totals else 0))
    payment_amount = gt / period_count if period_count > 0 else gt

    # Discount
    discount_due = None
    discount_potential = None
    if term.discount_rate and term.days_discount:
        discount_due = now + timedelta(days=term.days_discount)
        discount_potential = gt * Decimal(str(term.discount_rate)) / Decimal("100")

    for p in range(period_count):
        period_due = now + timedelta(days=(term.days_due or 30) + (p * days_in_period))
        Ledger.objects.create(
            ida=f"L-{inv.ida}-{p+1}",
            invoice=inv,
            term=term,
            org_id=inv.customer_id,
            model_name="invoice",
            parent_id=inv.id,
            source=f"invoice#{inv.id}",
            value_original=payment_amount,
            value_available=payment_amount,
            dt_due=period_due,
            dt_journaled=0,
            dt_recorded=now,
            dt_discount_due=discount_due,
            discount_potential=discount_potential if p == 0 else None,
            dt_applied=None,
            is_cleared=False,
            is_void=False,
        )
        ledgers_created += 1

    print(f"  Invoice {inv.ida} (id={inv.id}) -> term={term.name}, {period_count} ledger(s)")

print(f"\nDone: {len(invoices)} invoices updated, {ledgers_created} ledger entries created")

for t in terms:
    c = Invoice.objects.filter(is_deleted=False, terms=t.name).count()
    lc = Ledger.objects.filter(term=t).count()
    print(f"  {t.name}: {c} invoices, {lc} ledgers")
