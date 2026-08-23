"""
Ledger System Tests
===================

Tests for the AR ledger pipeline:
  Invoice save → ledger records created → org aging updated
  Payment save → negative ledger → org balance reduced

Covers:
  1. Schedule computation (single, multi-period, discount terms)
  2. Ledger record creation from invoice save
  3. Payment ledger creation
  4. Aging bucket calculation
  5. Full pipeline through transaction_save → on_invoice_save

Run:
    cd webClerk3
    python -m pytest apps/accounts/tests/test_ledger.py -v --no-header -o "addopts="
"""
import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

pytestmark = pytest.mark.django_db(transaction=True)


# ─── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def org():
    """Create a test customer org."""
    from apps.orgs.models import OrgBase
    return OrgBase.objects.create(
        display_name="Test Customer Ledger",
        org_type="customer",
    )


@pytest.fixture
def term_net30():
    """Create a Net 30 term."""
    from apps.accounts.models import Term
    return Term.objects.create(
        name="N30",
        description="Net 30 Days",
        period_count=1,
        days_due=30,
    )


@pytest.fixture
def term_3pay90():
    """Create a 3-Pay Net 90 term (3 equal installments, 30 days apart)."""
    from apps.accounts.models import Term
    return Term.objects.create(
        name="3PAY90",
        description="3 Payments Net 90",
        period_count=3,
        days_due=90,
        days_in_period=30,
    )


@pytest.fixture
def term_2_10_net30():
    """Create a 2/10 Net 30 term (2% discount if paid within 10 days)."""
    from apps.accounts.models import Term
    return Term.objects.create(
        name="2/10N30",
        description="2% 10 Net 30",
        period_count=1,
        days_due=30,
        discount_rate=0.02,
        days_discount=10,
    )


@pytest.fixture
def invoice(org, term_net30):
    """Create a test invoice linked to org with Net 30 terms."""
    from apps.transactions.models import Invoice
    inv = Invoice.objects.create(
        status='planned',
        customer=org,
        total=Decimal('1000'),
        totals={'subtotal': 1000, 'total': 1000},
        prefs={'payment_terms': {'id': str(term_net30.id), 'name': 'Net 30 Days'}},
    )
    return inv


@pytest.fixture
def item():
    """Create a test item for line-level tests."""
    from apps.products.models import Item
    try:
        return Item.objects.get(pk=243)
    except Item.DoesNotExist:
        return Item.objects.create(
            pk=243,
            name="Ledger Test Item",
            ida="LEDGER-243",
            sku="LDG-243",
        )


# ─── 1. Schedule Computation ──────────────────────────────────────────

class TestComputeSchedule:
    """Tests for compute_schedule() — pure math, no DB."""

    def test_single_payment_net30(self, term_net30):
        from apps.accounts.services.terms_ledger import compute_schedule
        dt = datetime(2026, 3, 1, tzinfo=timezone.utc)
        entries = compute_schedule(dt, Decimal('1000'), term_net30)

        assert len(entries) == 1
        assert entries[0].share == Decimal('1')
        assert entries[0].due == dt + timedelta(days=30)
        assert entries[0].discount_due is None

    def test_multi_period_3pay(self, term_3pay90):
        from apps.accounts.services.terms_ledger import compute_schedule
        dt = datetime(2026, 3, 1, tzinfo=timezone.utc)
        entries = compute_schedule(dt, Decimal('1000'), term_3pay90)

        assert len(entries) == 3
        # Shares must sum to exactly 1.0
        total_share = sum(e.share for e in entries)
        assert total_share == Decimal('1')
        # Due dates staggered by 30 days
        assert entries[0].due == dt + timedelta(days=30)
        assert entries[1].due == dt + timedelta(days=60)
        assert entries[2].due == dt + timedelta(days=90)

    def test_discount_term(self, term_2_10_net30):
        from apps.accounts.services.terms_ledger import compute_schedule
        dt = datetime(2026, 3, 1, tzinfo=timezone.utc)
        entries = compute_schedule(dt, Decimal('1000'), term_2_10_net30)

        assert len(entries) == 1
        assert entries[0].discount_rate == Decimal('0.02')
        assert entries[0].discount_due == dt + timedelta(days=10)
        assert entries[0].due == dt + timedelta(days=30)

    def test_epoch_ms_invoice_date(self, term_net30):
        """compute_schedule accepts epoch milliseconds as invoice date."""
        from apps.accounts.services.terms_ledger import compute_schedule
        # 2026-03-01 00:00:00 UTC in epoch ms
        epoch_ms = 1772006400000
        entries = compute_schedule(epoch_ms, Decimal('500'), term_net30)
        assert len(entries) == 1
        assert entries[0].share == Decimal('1')


# ─── 2. Ledger Record Creation ────────────────────────────────────────

class TestCreateLedgerRecords:
    """Tests for create_ledger_records() and apply_terms_for_invoice()."""

    def test_creates_single_ledger_net30(self, invoice, term_net30):
        from apps.accounts.services.terms_ledger import apply_terms_for_invoice
        from apps.accounts.models import Ledger

        ledgers = apply_terms_for_invoice(invoice, term=term_net30, replace=True)

        assert len(ledgers) == 1
        db_ledger = Ledger.objects.get(pk=ledgers[0].pk)
        assert db_ledger.model_name == 'invoice'
        assert db_ledger.source == 'AR'
        assert db_ledger.parent_id == invoice.id
        assert db_ledger.invoice_id == invoice.id
        assert db_ledger.term_id == term_net30.id
        assert float(db_ledger.value_original) == 1000.0
        assert float(db_ledger.value_available) == 1000.0
        assert db_ledger.org_id == invoice.customer_id

    def test_creates_3_ledgers_multi_period(self, org, term_3pay90):
        from apps.transactions.models import Invoice
        from apps.accounts.services.terms_ledger import apply_terms_for_invoice
        from apps.accounts.models import Ledger

        inv = Invoice.objects.create(
            status='planned',
            customer=org,
            total=Decimal('900'),
            prefs={'payment_terms': {'id': str(term_3pay90.id)}},
        )
        ledgers = apply_terms_for_invoice(inv, term=term_3pay90, replace=True)

        assert len(ledgers) == 3
        values = sorted([float(l.value_original) for l in ledgers])
        assert sum(values) == pytest.approx(900.0, abs=0.01)

        # All should link to same invoice and org
        for l in ledgers:
            db_l = Ledger.objects.get(pk=l.pk)
            assert db_l.invoice_id == inv.id
            assert db_l.org_id == org.id

    def test_replace_deletes_old_ledgers(self, invoice, term_net30):
        from apps.accounts.services.terms_ledger import apply_terms_for_invoice
        from apps.accounts.models import Ledger

        # Create first batch
        apply_terms_for_invoice(invoice, term=term_net30, replace=True)
        assert Ledger.objects.filter(invoice_id=invoice.id).count() == 1

        # Replace should delete old and create new
        apply_terms_for_invoice(invoice, term=term_net30, replace=True)
        assert Ledger.objects.filter(invoice_id=invoice.id).count() == 1

    def test_no_term_returns_empty(self, org):
        """Invoice without payment terms → no ledgers created."""
        from apps.transactions.models import Invoice
        from apps.accounts.services.terms_ledger import apply_terms_for_invoice

        inv = Invoice.objects.create(
            status='planned',
            customer=org,
            total=Decimal('500'),
            prefs={},
        )
        ledgers = apply_terms_for_invoice(inv)
        assert ledgers == []

    def test_resolves_term_by_name(self, org, term_net30):
        """Term resolution via prefs.payment_terms.name fallback."""
        from apps.transactions.models import Invoice
        from apps.accounts.services.terms_ledger import apply_terms_for_invoice

        inv = Invoice.objects.create(
            status='planned',
            customer=org,
            total=Decimal('750'),
            prefs={'payment_terms': {'name': 'Net 30 Days'}},
        )
        ledgers = apply_terms_for_invoice(inv)
        assert len(ledgers) == 1
        assert float(ledgers[0].value_original) == 750.0


# ─── 3. Payment Ledger ────────────────────────────────────────────────

class TestPaymentLedger:
    """Tests for record_payment() — negative value ledger."""

    def test_creates_negative_ledger(self, invoice):
        from apps.accounts.services.terms_ledger import record_payment
        from apps.accounts.models import Ledger

        now = datetime.now(timezone.utc)
        ledger = record_payment(
            invoice=invoice,
            amount=Decimal('400'),
            dt_paid=now,
        )

        db_l = Ledger.objects.get(pk=ledger.pk)
        assert db_l.model_name == 'payment'
        assert float(db_l.value_original) == -400.0
        assert float(db_l.value_available) == -400.0
        assert db_l.org_id == invoice.customer_id
        assert db_l.invoice_id == invoice.id


# ─── 4. Aging Buckets ─────────────────────────────────────────────────

class TestAgingBuckets:
    """Tests for calculate_aging_buckets()."""

    def test_single_current_ledger(self, invoice, term_net30):
        from apps.accounts.services.terms_ledger import apply_terms_for_invoice
        from apps.accounts.services.ledger_balance import calculate_aging_buckets
        from datetime import date

        apply_terms_for_invoice(invoice, term=term_net30, replace=True)

        # As of invoice creation date, the ledger due in 30 days is "current"
        buckets = calculate_aging_buckets(invoice.customer_id, as_of_date=date.today())
        assert buckets['total'] > 0
        # The ledger should be in current or future bucket (due in ~30 days)
        assert (buckets['current'] + buckets['future']) == buckets['total']

    def test_past_due_ledger(self, org, term_net30):
        """A ledger due 45 days ago should be in period_1 (1-30 days past) or period_2."""
        from apps.transactions.models import Invoice
        from apps.accounts.services.terms_ledger import apply_terms_for_invoice
        from apps.accounts.services.ledger_balance import calculate_aging_buckets
        from apps.accounts.models import Ledger
        from datetime import date

        inv = Invoice.objects.create(
            status='planned',
            customer=org,
            total=Decimal('500'),
            prefs={'payment_terms': {'id': str(term_net30.id)}},
        )
        apply_terms_for_invoice(inv, term=term_net30, replace=True)

        # Manually backdate the ledger's due date to 45 days ago
        ledger = Ledger.objects.filter(invoice_id=inv.id).first()
        ledger.dt_due = datetime.now(timezone.utc) - timedelta(days=45)
        ledger.save(update_fields=['dt_due'])

        buckets = calculate_aging_buckets(org.id, as_of_date=date.today())
        # 45 days past due → period_2 (31-60 days past)
        assert buckets['period_2'] == Decimal('500')

    def test_payment_reduces_balance(self, invoice, term_net30):
        """Invoice $1000 - Payment $400 = $600 balance."""
        from apps.accounts.services.terms_ledger import apply_terms_for_invoice, record_payment
        from apps.accounts.services.ledger_balance import calculate_aging_buckets
        from datetime import date

        apply_terms_for_invoice(invoice, term=term_net30, replace=True)
        record_payment(invoice=invoice, amount=Decimal('400'), dt_paid=datetime.now(timezone.utc))

        buckets = calculate_aging_buckets(invoice.customer_id, as_of_date=date.today())
        assert buckets['total'] == Decimal('600')


# ─── 5. on_invoice_save Integration ───────────────────────────────────

class TestOnInvoiceSave:
    """Tests for on_invoice_save() — the wired entry point."""

    def test_creates_ledgers_and_updates_org(self, org, term_net30):
        from apps.transactions.models import Invoice
        from apps.accounts.services.ledger_balance import on_invoice_save
        from apps.accounts.models import Ledger

        inv = Invoice.objects.create(
            status='planned',
            customer=org,
            total=Decimal('2000'),
            prefs={'payment_terms': {'id': str(term_net30.id)}},
        )

        on_invoice_save(inv, replace_ledgers=True)

        # Ledger records created
        ledger_count = Ledger.objects.filter(invoice_id=inv.id).count()
        assert ledger_count == 1

        # Org balances updated
        org.refresh_from_db()
        fin = org.financial or {}
        customer_fin = fin.get('customer', {})
        balances = customer_fin.get('balances', {})
        assert balances.get('due', 0) == pytest.approx(2000.0, abs=0.01)

    def test_replace_on_re_save(self, org, term_net30):
        """Re-saving invoice replaces ledgers (idempotent)."""
        from apps.transactions.models import Invoice
        from apps.accounts.services.ledger_balance import on_invoice_save
        from apps.accounts.models import Ledger

        inv = Invoice.objects.create(
            status='planned',
            customer=org,
            total=Decimal('1500'),
            prefs={'payment_terms': {'id': str(term_net30.id)}},
        )

        on_invoice_save(inv)
        on_invoice_save(inv)  # Second call should replace, not duplicate

        assert Ledger.objects.filter(invoice_id=inv.id).count() == 1
