import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.transactions.models import Proposal, ProposalLine
from apps.core.models import Contact


class ProposalModelTest(TestCase):
    """Test cases for Proposal model."""

    def setUp(self):
        """Set up test data."""
        self.customer = Contact.objects.create(
            name_first="John",
            name_last="Doe",
            email="john.doe@example.com"
        )
        self.vendor = Contact.objects.create(
            name_first="Jane",
            name_last="Smith",
            email="jane.smith@example.com"
        )

    def test_proposal_creation(self):
        """Test basic proposal creation."""
        proposal = Proposal.objects.create(
            ida="PROP-001",
            status="planned",
            customer_id=self.customer.id,
            vendor_id=self.vendor.id
        )

        self.assertEqual(proposal.ida, "PROP-001")
        self.assertEqual(proposal.status, "planned")
        self.assertEqual(proposal.customer_id, self.customer.id)
        self.assertEqual(proposal.vendor_id, self.vendor.id)
        self.assertIsNotNone(proposal.dt_created)
        self.assertIsNotNone(proposal.dt_modified)

    def test_proposal_str_method(self):
        """Test string representation of proposal."""
        proposal = Proposal.objects.create(
            ida="PROP-001",
            status="planned",
            customer_id=self.customer.id
        )

        expected_str = f"Proposal #{proposal.id} (PROP-001)"
        self.assertEqual(str(proposal), expected_str)

    def test_proposal_name_property(self):
        """Test name property getter and setter."""
        proposal = Proposal.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Test getter with no name fields
        self.assertEqual(proposal.name, "")

        # Test setter (should set _transient_name)
        proposal.name = "Test Proposal"
        self.assertEqual(proposal._transient_name, "Test Proposal")
        self.assertEqual(proposal.name, "Test Proposal")

    def test_proposal_status_choices(self):
        """Test that status choices are properly defined."""
        expected_choices = [
            ('planned', 'Planned'),
            ('released', 'Released'),
            ('in_progress', 'In Progress'),
            ('hold', 'Hold'),
            ('complete', 'Complete'),
            ('canceled', 'Canceled'),
        ]

        self.assertEqual(Proposal.STATUS_CHOICES, expected_choices)

    def test_proposal_update_sell_cost_totals_without_persist(self):
        """Test update_sell_cost_totals method without persistence."""
        proposal = Proposal.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Create some line items
        line1 = ProposalLine.objects.create(
            parent=proposal,
            description="Item 1",
            quantity=2,
            price={'sell': 10.00, 'cost': 8.00, 'extended': 20.00},
            cost={'extended': 16.00}
        )
        line2 = ProposalLine.objects.create(
            parent=proposal,
            description="Item 2",
            quantity=1,
            price={'sell': 15.00, 'cost': 12.00, 'extended': 15.00},
            cost={'extended': 12.00}
        )

        # Test totals calculation
        result = proposal.update_sell_cost_totals(persist=False)

        self.assertIn('sell', result)
        self.assertIn('cost', result)
        self.assertIn('totals', result)

        # Check sell totals
        self.assertEqual(result['sell']['line_sum_goods'], 35.00)  # 20 + 15
        self.assertEqual(result['sell']['total'], 35.00)

        # Check cost totals
        self.assertEqual(result['cost']['line_sum_goods'], 28.00)  # 16 + 12
        self.assertEqual(result['cost']['total'], 28.00)

        # Check margin calculations
        self.assertEqual(result['totals']['total'], 35.00)
        self.assertEqual(result['totals']['cost'], 28.00)
        self.assertEqual(result['totals']['margin'], 7.00)
        self.assertAlmostEqual(result['totals']['margin_pc'], 20.00, places=2)

    def test_proposal_update_sell_cost_totals_with_persist(self):
        """Test update_sell_cost_totals method with persistence."""
        proposal = Proposal.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Create a line item
        ProposalLine.objects.create(
            parent=proposal,
            description="Test Item",
            quantity=1,
            price={'sell': 100.00, 'cost': 80.00, 'extended': 100.00},
            cost={'extended': 80.00}
        )

        # Update totals with persistence
        result = proposal.update_sell_cost_totals(persist=True)

        # Refresh from database
        proposal.refresh_from_db()

        # Check that totals were saved
        self.assertEqual(proposal.sell['total'], 100.00)
        self.assertEqual(proposal.cost['total'], 80.00)
        self.assertEqual(proposal.totals['total'], 100.00)
        self.assertEqual(proposal.totals['cost'], 80.00)
        self.assertEqual(proposal.totals['margin'], 20.00)


class ProposalLineModelTest(TestCase):
    """Test cases for ProposalLine model."""

    def setUp(self):
        """Set up test data."""
        self.customer = Contact.objects.create(
            name_first="John",
            name_last="Doe",
            email="john.doe@example.com"
        )
        self.proposal = Proposal.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

    def test_proposal_line_creation(self):
        """Test basic proposal line creation."""
        line = ProposalLine.objects.create(
            parent=self.proposal,
            description="Test Item",
            quantity=5,
            price={'sell': 20.00, 'cost': 15.00},
            discount_amount=2.00
        )

        self.assertEqual(line.parent, self.proposal)
        self.assertEqual(line.description, "Test Item")
        self.assertEqual(line.quantity, 5)
        self.assertEqual(line.price['sell'], 20.00)
        self.assertEqual(line.price['cost'], 15.00)
        self.assertEqual(line.discount_amount, 2.00)

    def test_proposal_line_parent_ref_property(self):
        """Test parent_ref_id property."""
        line = ProposalLine.objects.create(
            parent=self.proposal,
            description="Test Item",
            quantity=1
        )

        # Test getter
        self.assertEqual(line.parent_ref_id, self.proposal.id)

        # Test setter
        new_proposal = Proposal.objects.create(
            status="planned",
            customer_id=self.customer.id
        )
        line.parent_ref_id = new_proposal.id
        self.assertEqual(line.parent_id, new_proposal.id)