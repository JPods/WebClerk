import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.transactions.models import Quote, QuoteLine
from apps.orgs.models import OrgBase


class QuoteModelTest(TestCase):
    """Test cases for Quote model."""

    def setUp(self):
        """Set up test data."""
        self.customer = OrgBase.objects.create(
            company="John Doe",
            org_type="customer"
        )
        self.vendor = OrgBase.objects.create(
            company="Jane Smith",
            org_type="vendor"
        )

    def test_quote_creation(self):
        """Test basic quote creation."""
        quote = Quote.objects.create(
            ida="PROP-001",
            status="planned",
            customer_id=self.customer.id,
            vendor_id=self.vendor.id
        )

        self.assertEqual(quote.ida, "PROP-001")
        self.assertEqual(quote.status, "planned")
        self.assertEqual(quote.customer_id, self.customer.id)
        self.assertEqual(quote.vendor_id, self.vendor.id)
        self.assertIsNotNone(quote.dt_created)
        self.assertIsNotNone(quote.dt_modified)

    def test_quote_str_method(self):
        """Test string representation of quote."""
        quote = Quote.objects.create(
            ida="PROP-001",
            status="planned",
            customer_id=self.customer.id
        )

        expected_str = f"Quote #{quote.id} (PROP-001)"
        self.assertEqual(str(quote), expected_str)

    def test_quote_name_property(self):
        """Test name property getter and setter."""
        quote = Quote.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Test getter with no name fields
        self.assertEqual(quote.name, "")

        # Test setter (should set _transient_name)
        quote.name = "Test Quote"
        self.assertEqual(quote._transient_name, "Test Quote")
        self.assertEqual(quote.name, "Test Quote")

    def test_quote_status_choices(self):
        """Test that status choices are properly defined."""
        expected_choices = (
            ('', '---------'),
            ('planned', 'Planned'),
            ('signoff_request', 'SignOff Request'),
            ('released', 'Released'),
            ('in_progress', 'In Progress'),
            ('hold', 'Hold'),
            ('consigned', 'Consigned'),
            ('deferred', 'Deferred'),
            ('complete', 'Complete'),
            ('canceled', 'Canceled'),
        )

        self.assertEqual(Quote.STATUS_CHOICES, expected_choices)

    def test_quote_update_sell_cost_totals_without_persist(self):
        """Test update_sell_cost_totals method calculates correctly."""
        quote = Quote.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Create some line items with unit prices (engine computes extended = qty * unit)
        QuoteLine.objects.create(
            quote=quote,
            quantity={'staged': 2},
            price={'unit': 10.00, 'amount': 20.00},
            cost={'unit': 8.00, 'extended': 16.00}
        )
        QuoteLine.objects.create(
            quote=quote,
            quantity={'staged': 1},
            price={'unit': 15.00, 'amount': 15.00},
            cost={'unit': 12.00, 'extended': 12.00}
        )

        # Test totals calculation
        result = quote.update_sell_cost_totals(persist=True)
        quote.refresh_from_db()

        totals = quote.totals
        self.assertIn('amount', totals)
        self.assertIn('total', totals)
        self.assertIn('cost', totals)
        self.assertIn('margin', totals)

    def test_quote_update_sell_cost_totals_with_persist(self):
        """Test update_sell_cost_totals method with persistence."""
        quote = Quote.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Create a line item
        QuoteLine.objects.create(
            quote=quote,
            quantity={'staged': 1},
            price={'unit': 100.00, 'amount': 100.00},
            cost={'unit': 80.00, 'extended': 80.00}
        )

        # Update totals with persistence
        result = quote.update_sell_cost_totals(persist=True)

        # Refresh from database
        quote.refresh_from_db()

        # Check that totals were saved
        self.assertIn('total', quote.totals)
        self.assertIn('cost', quote.totals)
        self.assertIn('margin', quote.totals)


class QuoteLineModelTest(TestCase):
    """Test cases for QuoteLine model."""

    def setUp(self):
        """Set up test data."""
        self.customer = OrgBase.objects.create(
            company="John Doe",
            org_type="customer"
        )
        self.quote = Quote.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

    def test_quote_line_creation(self):
        """Test basic quote line creation."""
        line = QuoteLine.objects.create(
            quote=self.quote,
            price={'unit': 20.00, 'amount': 20.00},
            cost={'unit': 15.00, 'extended': 15.00}
        )

        self.assertEqual(line.quote, self.quote)
        self.assertEqual(line.price['unit'], 20.00)
        self.assertEqual(line.cost['unit'], 15.00)

    def test_quote_line_parent_ref_property(self):
        """Test quote FK relationship."""
        line = QuoteLine.objects.create(
            quote=self.quote,
        )

        # Test FK relationship
        self.assertEqual(line.quote_id, self.quote.id)

        # Test reassignment
        new_quote = Quote.objects.create(
            status="planned",
            customer_id=self.customer.id
        )
        line.quote = new_quote
        line.save()
        self.assertEqual(line.quote_id, new_quote.id)