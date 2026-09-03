"""
Erosion Service Tests
=====================

Tests for the erosion detection pipeline:
  Invoice/Order save → margin erosion detected → Erosion records created
  Payment save → late-payment carrying cost → Erosion record created
  Discount detection → standalone erosion record

Covers:
  1. Margin erosion (invoice vs order, invoice vs proposal)
  2. Late-payment carrying cost
  3. Discount erosion
  4. Org erosion summary
  5. No-erosion cases (margin improved, on-time payment)

Run:
    cd webClerk3
    python -m pytest apps/accounts/tests/test_erosion.py -v --no-header -o "addopts="
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
        display_name="Erosion Test Customer",
        org_type="customer",
    )


@pytest.fixture
def proposal(org):
    """Create a proposal with 40% margin."""
    from apps.transactions.models import Proposal
    return Proposal.objects.create(
        status='planned',
        customer=org,
        totals={
            'subtotal': 1000, 'discount': 0, 'total': 1000,
            'cost': 600, 'margin': 400, 'margin_pc': 40,
        },
    )


@pytest.fixture
def order_from_proposal(org, proposal):
    """Create an order linked to proposal with 35% margin (eroded by 5pp)."""
    from apps.transactions.models import Order
    return Order.objects.create(
        status='planned',
        customer=org,
        parent_id=proposal.id,
        parent_model='proposal',
        totals={
            'subtotal': 1000, 'discount': 0, 'total': 1000,
            'cost': 650, 'margin': 350, 'margin_pc': 35,
        },
    )


@pytest.fixture
def invoice_from_order(org, order_from_proposal):
    """Create an invoice linked to order with 31% margin (eroded further)."""
    from apps.transactions.models import Invoice
    return Invoice.objects.create(
        status='planned',
        customer=org,
        parent_id=order_from_proposal.id,
        parent_model='order',
        totals={
            'subtotal': 1000, 'discount': 0, 'total': 1000,
            'cost': 690, 'margin': 310, 'margin_pc': 31,
        },
    )


@pytest.fixture
def invoice_with_discount(org):
    """Create an invoice with a $50 discount applied."""
    from apps.transactions.models import Invoice
    return Invoice.objects.create(
        status='planned',
        customer=org,
        totals={
            'subtotal': 1000, 'discount': 50, 'total': 950,
            'cost': 600, 'margin': 350, 'margin_pc': 36.84,
        },
    )


@pytest.fixture
def term_net30():
    """Create a Net 30 term for ledger tests."""
    from apps.accounts.models import Term
    return Term.objects.create(
        name="N30",
        description="Net 30 Days",
        period_count=1,
        days_due=30,
    )


@pytest.fixture
def contact():
    """Create a test contact for payment tests."""
    from apps.core.models import Contact
    return Contact.objects.create(
        name_first="Test",
        name_last="Payer",
        email="test.payer@example.com",
    )


# ─── 1. Margin Erosion ───────────────────────────────────────────────

class TestMarginErosion:
    """Tests for detect_margin_erosion()."""

    def test_detects_erosion_invoice_vs_order(self, invoice_from_order, order_from_proposal):
        from apps.accounts.services.value_erosion import detect_margin_erosion
        from apps.accounts.models import Erosion

        events = detect_margin_erosion(invoice_from_order)

        # Should detect erosion vs order (margin dropped 350 → 310 = $40)
        assert len(events) >= 1
        order_erosion = [e for e in events if e.parent_model == 'order']
        assert len(order_erosion) == 1
        assert order_erosion[0].amount == Decimal('40')
        assert order_erosion[0].category == 'margin'
        assert order_erosion[0].source_model == 'invoice'
        assert order_erosion[0].org_id == invoice_from_order.customer_id

    def test_walks_full_chain_invoice_to_proposal(self, invoice_from_order, order_from_proposal, proposal):
        from apps.accounts.services.value_erosion import detect_margin_erosion

        events = detect_margin_erosion(invoice_from_order)

        # Should detect erosion vs both order AND proposal
        models_found = {e.parent_model for e in events}
        assert 'order' in models_found
        assert 'proposal' in models_found

        # Proposal erosion: 400 - 310 = $90
        proposal_erosion = [e for e in events if e.parent_model == 'proposal']
        assert proposal_erosion[0].amount == Decimal('90')

    def test_no_erosion_when_margin_improves(self, org):
        """If invoice margin is higher than order, no erosion should be recorded."""
        from apps.transactions.models import Order, Invoice
        from apps.accounts.services.value_erosion import detect_margin_erosion

        order = Order.objects.create(
            status='planned', customer=org,
            totals={'total': 1000, 'cost': 700, 'margin': 300, 'margin_pc': 30},
        )
        invoice = Invoice.objects.create(
            status='planned', customer=org,
            parent_id=order.id, parent_model='order',
            totals={'total': 1000, 'cost': 600, 'margin': 400, 'margin_pc': 40},
        )

        events = detect_margin_erosion(invoice)
        assert events == []

    def test_idempotent_replace(self, invoice_from_order, order_from_proposal):
        """Running detect_margin_erosion twice replaces, not duplicates."""
        from apps.accounts.services.value_erosion import detect_margin_erosion
        from apps.accounts.models import Erosion

        detect_margin_erosion(invoice_from_order)
        detect_margin_erosion(invoice_from_order)

        # Should have exactly 2 records (one per ancestor), not 4
        count = Erosion.objects.filter(
            source_model='invoice', source_id=invoice_from_order.id, is_auto=True,
        ).count()
        assert count == 2  # one vs order, one vs proposal

    def test_no_parent_returns_empty(self, org):
        """Invoice without parent chain → no erosion."""
        from apps.transactions.models import Invoice
        from apps.accounts.services.value_erosion import detect_margin_erosion

        invoice = Invoice.objects.create(
            status='planned', customer=org,
            totals={'total': 1000, 'cost': 600, 'margin': 400, 'margin_pc': 40},
        )
        events = detect_margin_erosion(invoice)
        assert events == []


# ─── 2. Late Payment Erosion ─────────────────────────────────────────

class TestLatePaymentErosion:
    """Tests for detect_late_payment()."""

    def test_detects_late_payment(self, org, term_net30, contact):
        from apps.transactions.models import Invoice, Payment
        from apps.accounts.services.terms_ledger import apply_terms_for_invoice
        from apps.accounts.services.value_erosion import detect_late_payment

        invoice = Invoice.objects.create(
            status='planned', customer=org,
            totals={'total': 1000, 'subtotal': 1000},
            prefs={'payment_terms': {'id': str(term_net30.id)}},
        )
        apply_terms_for_invoice(invoice, term=term_net30, replace=True)

        # Backdate ledger due date to 15 days ago
        from apps.accounts.models import Ledger
        ledger = Ledger.objects.filter(invoice_id=invoice.id).first()
        ledger.dt_due = datetime.now(timezone.utc) - timedelta(days=15)
        ledger.save(update_fields=['dt_due'])

        payment = Payment.objects.create(
            invoice=invoice, amount=Decimal('500'),
            dt_payment=datetime.now(timezone.utc),
            status='completed',
            contact_id=contact.id,
        )

        erosion = detect_late_payment(payment)

        assert erosion is not None
        assert erosion.category == 'late_payment'
        assert erosion.amount > 0
        assert erosion.org_id == org.id
        # 500 * 0.0005 * 15 = $3.75
        assert erosion.amount == Decimal('3.75')

    def test_no_erosion_on_time_payment(self, org, term_net30, contact):
        """Payment before due date → no erosion."""
        from apps.transactions.models import Invoice, Payment
        from apps.accounts.services.terms_ledger import apply_terms_for_invoice
        from apps.accounts.services.value_erosion import detect_late_payment

        invoice = Invoice.objects.create(
            status='planned', customer=org,
            totals={'total': 1000, 'subtotal': 1000},
            prefs={'payment_terms': {'id': str(term_net30.id)}},
        )
        apply_terms_for_invoice(invoice, term=term_net30, replace=True)

        # Due date is 30 days from now — payment today is on time
        payment = Payment.objects.create(
            invoice=invoice, amount=Decimal('500'),
            dt_payment=datetime.now(timezone.utc),
            status='completed',
            contact_id=contact.id,
        )

        erosion = detect_late_payment(payment)
        assert erosion is None


# ─── 3. Discount Erosion ─────────────────────────────────────────────

class TestDiscountErosion:
    """Tests for detect_discount_erosion()."""

    def test_detects_discount(self, invoice_with_discount):
        from apps.accounts.services.value_erosion import detect_discount_erosion

        erosion = detect_discount_erosion(invoice_with_discount)

        assert erosion is not None
        assert erosion.category == 'discount'
        assert erosion.amount == Decimal('50')
        assert erosion.source_model == 'invoice'

    def test_no_discount_no_erosion(self, org):
        """Invoice with no discount → no erosion."""
        from apps.transactions.models import Invoice
        from apps.accounts.services.value_erosion import detect_discount_erosion

        invoice = Invoice.objects.create(
            status='planned', customer=org,
            totals={'total': 1000, 'cost': 600, 'margin': 400, 'discount': 0},
        )
        erosion = detect_discount_erosion(invoice)
        assert erosion is None


# ─── 4. Org Summary ──────────────────────────────────────────────────

class TestOrgErosionSummary:
    """Tests for get_org_erosion_summary()."""

    def test_summary_aggregates(self, invoice_from_order, order_from_proposal, proposal, invoice_with_discount):
        from apps.accounts.services.value_erosion import (
            detect_margin_erosion, detect_discount_erosion, get_org_erosion_summary,
        )

        # Generate erosion events
        detect_margin_erosion(invoice_from_order)
        detect_discount_erosion(invoice_with_discount)

        org_id = invoice_from_order.customer_id
        summary = get_org_erosion_summary(org_id, days=90)

        assert summary['total'] > 0
        assert summary['count'] >= 2
        assert 'margin' in summary['by_category']
        assert summary['period_days'] == 90


# ─── 5. Metadata ↔ Erosion Sync ──────────────────────────────────────

class TestMetadataErosionSync:
    """Tests for sync_metadata_erosions() and post_save_hook integration."""

    def test_sync_creates_erosion_and_writes_back_id(self, org):
        """Pending metadata entry → Erosion record created → erosion_id written back."""
        from apps.accounts.services.value_erosion import sync_metadata_erosions
        from apps.accounts.models import Erosion

        org.metadata.setdefault('small_stings', [])
        org.metadata['small_stings'].append({
            'category': 'price_override',
            'amount': 12.50,
            'dt': 1709913600000,
            'note': 'Manual override on widget',
            'erosion_id': None,
        })
        org.save()

        count = sync_metadata_erosions(org)

        assert count == 1
        entry = org.metadata['small_stings'][0]
        assert entry['erosion_id'] is not None
        erosion = Erosion.objects.get(pk=entry['erosion_id'])
        assert erosion.category == 'price_override'
        assert erosion.amount == Decimal('12.50')
        assert erosion.source_model == 'orgbase'
        assert erosion.source_id == org.id
        assert erosion.is_auto is False

    def test_sync_skips_already_synced_entries(self, org):
        """Entries with existing erosion_id should not be re-created."""
        from apps.accounts.services.value_erosion import sync_metadata_erosions

        org.metadata.setdefault('erosions', [])
        org.metadata['erosions'].append({
            'category': 'margin',
            'amount': 100.00,
            'dt': 1709913600000,
            'note': 'Already synced',
            'erosion_id': 999,  # already synced
        })
        org.save()

        count = sync_metadata_erosions(org)
        assert count == 0

    def test_sync_handles_both_arrays(self, org):
        """Both small_stings and erosions arrays are processed."""
        from apps.accounts.services.value_erosion import sync_metadata_erosions
        from apps.accounts.models import Erosion

        org.metadata.setdefault('small_stings', [])
        org.metadata.setdefault('erosions', [])
        org.metadata['small_stings'].append({
            'category': 'discount',
            'amount': 5.00,
            'dt': 1709913600000,
            'note': 'Sting 1',
        })
        org.metadata['erosions'].append({
            'category': 'rework',
            'amount': 250.00,
            'dt': 1709913600000,
            'note': 'Rework cost',
        })
        org.save()

        count = sync_metadata_erosions(org)

        assert count == 2
        assert org.metadata['small_stings'][0]['erosion_id'] is not None
        assert org.metadata['erosions'][0]['erosion_id'] is not None
        assert Erosion.objects.count() == 2

    def test_sync_ignores_zero_amount(self, org):
        """Entries with zero or negative amount are skipped."""
        from apps.accounts.services.value_erosion import sync_metadata_erosions

        org.metadata.setdefault('small_stings', [])
        org.metadata['small_stings'].append({
            'category': 'other',
            'amount': 0,
            'note': 'Zero amount',
        })
        org.save()

        count = sync_metadata_erosions(org)
        assert count == 0

    def test_post_save_hook_triggers_sync(self, org):
        """BaseModel.post_save_hook should sync pending erosion annotations."""
        from apps.accounts.models import Erosion

        org.metadata.setdefault('erosions', [])
        org.metadata['erosions'].append({
            'category': 'bad_debt',
            'amount': 500.00,
            'dt': 1709913600000,
            'note': 'Write-off',
        })
        org.save()

        # Simulate what save_view does
        msg = org.post_save_hook({})
        assert '1 erosion record(s) created' in (msg or '')

        # Verify the Erosion record exists
        assert Erosion.objects.filter(
            source_model='orgbase',
            source_id=org.id,
            category='bad_debt',
        ).exists()

        # Verify erosion_id was written back
        org.refresh_from_db()
        entry = org.metadata['erosions'][0]
        assert entry['erosion_id'] is not None
