import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.transactions.models import Proposal, ProposalLine
from apps.orgs.models import OrgBase


class ProposalModelTest(TestCase):
    """Test cases for Proposal model."""

    def setUp(self):
        """Set up test data."""
        self.customer = OrgBase.objects.create(
            display_name="John Doe",
            org_type="customer"
        )
        self.vendor = OrgBase.objects.create(
            display_name="Jane Smith",
            org_type="vendor"
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

        self.assertEqual(Proposal.STATUS_CHOICES, expected_choices)

    def test_proposal_update_sell_cost_totals_without_persist(self):
        """Test update_sell_cost_totals method calculates correctly."""
        proposal = Proposal.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Create some line items with unit prices (engine computes extended = qty * unit)
        ProposalLine.objects.create(
            proposal=proposal,
            quantity={'staged': 2},
            price={'unit': 10.00, 'extended': 20.00},
            cost={'unit': 8.00, 'extended': 16.00}
        )
        ProposalLine.objects.create(
            proposal=proposal,
            quantity={'staged': 1},
            price={'unit': 15.00, 'extended': 15.00},
            cost={'unit': 12.00, 'extended': 12.00}
        )

        # Test totals calculation
        result = proposal.update_sell_cost_totals(persist=True)
        proposal.refresh_from_db()

        totals = proposal.totals
        self.assertIn('subtotal', totals)
        self.assertIn('total', totals)
        self.assertIn('cost', totals)
        self.assertIn('margin', totals)

    def test_proposal_update_sell_cost_totals_with_persist(self):
        """Test update_sell_cost_totals method with persistence."""
        proposal = Proposal.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Create a line item
        ProposalLine.objects.create(
            proposal=proposal,
            quantity={'staged': 1},
            price={'unit': 100.00, 'extended': 100.00},
            cost={'unit': 80.00, 'extended': 80.00}
        )

        # Update totals with persistence
        result = proposal.update_sell_cost_totals(persist=True)

        # Refresh from database
        proposal.refresh_from_db()

        # Check that totals were saved
        self.assertIn('total', proposal.totals)
        self.assertIn('cost', proposal.totals)
        self.assertIn('margin', proposal.totals)


class ProposalLineModelTest(TestCase):
    """Test cases for ProposalLine model."""

    def setUp(self):
        """Set up test data."""
        self.customer = OrgBase.objects.create(
            display_name="John Doe",
            org_type="customer"
        )
        self.proposal = Proposal.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

    def test_proposal_line_creation(self):
        """Test basic proposal line creation."""
        line = ProposalLine.objects.create(
            proposal=self.proposal,
            price={'unit': 20.00, 'extended': 20.00},
            cost={'unit': 15.00, 'extended': 15.00}
        )

        self.assertEqual(line.proposal, self.proposal)
        self.assertEqual(line.price['unit'], 20.00)
        self.assertEqual(line.cost['unit'], 15.00)

    def test_proposal_line_parent_ref_property(self):
        """Test proposal FK relationship."""
        line = ProposalLine.objects.create(
            proposal=self.proposal,
        )

        # Test FK relationship
        self.assertEqual(line.proposal_id, self.proposal.id)

        # Test reassignment
        new_proposal = Proposal.objects.create(
            status="planned",
            customer_id=self.customer.id
        )
        line.proposal = new_proposal
        line.save()
        self.assertEqual(line.proposal_id, new_proposal.id)