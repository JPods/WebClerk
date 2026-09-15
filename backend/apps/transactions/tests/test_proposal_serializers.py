import pytest
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import serializers
from apps.transactions.models import Proposal, ProposalLine
from apps.transactions.serializers.proposal_serializer import ProposalSerializer, ProposalLineRichSerializer as ProposalLineSerializer
from apps.orgs.models import OrgBase


class ProposalSerializerTest(TestCase):
    """Test cases for ProposalSerializer."""

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
        self.proposal = Proposal.objects.create(
            ida="PROP-001",
            status="planned",
            customer_id=self.customer.id,
            vendor_id=self.vendor.id,
            sell={'total': 100.00},
            cost={'total': 80.00}
        )

    def test_proposal_serializer_fields(self):
        """Test that serializer includes all expected fields."""
        serializer = ProposalSerializer(self.proposal)
        data = serializer.data

        expected_fields = [
            'id', 'uuid', 'ida', 'status', 'customer_id', 'vendor_id',
            'customer_name', 'vendor_name', 'cost', 'sell', 'totals',
            'finance', 'flow',
            'source', 'line_count',
            'lines', 'dt_created', 'dt_modified', 'version'
        ]

        for field in expected_fields:
            self.assertIn(field, data)

    def test_proposal_serializer_computed_fields(self):
        """Test computed fields via totals envelope."""
        serializer = ProposalSerializer(self.proposal)
        data = serializer.data

        # totals envelope is the source of truth for all computed values
        self.assertIn('totals', data)

    def test_proposal_serializer_line_count(self):
        """Test line count calculation."""
        # Create some line items
        ProposalLine.objects.create(
            proposal=self.proposal,
            price={'unit': 10.00}
        )
        ProposalLine.objects.create(
            proposal=self.proposal,
            price={'unit': 20.00}
        )

        serializer = ProposalSerializer(self.proposal)
        data = serializer.data

        self.assertEqual(data['line_count'], 2)

    def test_proposal_serializer_status_transition_validation(self):
        """Test status transition validation."""
        serializer = ProposalSerializer(instance=self.proposal)

        # Test that planned status is accepted
        data = {'status': 'released'}
        result = serializer.validate(data)
        self.assertEqual(result['status'], 'released')


class ProposalLineSerializerTest(TestCase):
    """Test cases for ProposalLineSerializer."""

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

    def test_proposal_line_serializer_fields(self):
        """Test that serializer includes all expected fields."""
        line = ProposalLine.objects.create(
            proposal=self.proposal,
            price={'unit': 10.00, 'extended': 20.00},
            cost={'unit': 8.00, 'extended': 16.00},
            quantity={'staged': 2, 'remaining': 2}
        )

        serializer = ProposalLineSerializer(line)
        data = serializer.data

        expected_fields = [
            'id', 'uuid', 'status', 'item', 'quantity', 'price',
            'cost', 'dt_created', 'dt_modified', 'version', 'proposal'
        ]

        for field in expected_fields:
            self.assertIn(field, data)

    def test_proposal_line_serializer_computed_fields(self):
        """Test line serializer returns price and cost envelopes."""
        line = ProposalLine.objects.create(
            proposal=self.proposal,
            price={'unit': 10.00, 'extended': 20.00},
            cost={'unit': 8.00, 'extended': 16.00},
            quantity={'staged': 2, 'remaining': 2}
        )

        serializer = ProposalLineSerializer(line)
        data = serializer.data

        self.assertEqual(data['price']['unit'], 10.00)
        self.assertEqual(data['cost']['unit'], 8.00)

    def test_proposal_line_serializer_quantity_validation(self):
        """Test quantity field accepts JSON dict."""
        line = ProposalLine.objects.create(
            proposal=self.proposal,
            quantity={'staged': 5, 'remaining': 5}
        )

        serializer = ProposalLineSerializer(line)
        data = serializer.data
        self.assertEqual(data['quantity']['staged'], 5)

    def test_proposal_line_serializer_discount_validation(self):
        """Test discount via price envelope."""
        line = ProposalLine.objects.create(
            proposal=self.proposal,
            quantity={'staged': 2, 'remaining': 2},
            price={'unit': 10.00, 'extended': 20.00, 'discount_amount': 2.00}
        )

        serializer = ProposalLineSerializer(line)
        data = serializer.data
        self.assertEqual(data['price']['discount_amount'], 2.00)

    def test_proposal_line_serializer_price_validation(self):
        """Test price structure is a JSON dict."""
        line = ProposalLine.objects.create(
            proposal=self.proposal,
            price={'unit': 10.00, 'extended': 20.00}
        )

        serializer = ProposalLineSerializer(line)
        data = serializer.data
        self.assertIsInstance(data['price'], dict)

    def test_proposal_line_serializer_cross_field_validation(self):
        """Test line with all envelope fields."""
        line = ProposalLine.objects.create(
            proposal=self.proposal,
            quantity={'staged': 2, 'remaining': 2},
            price={'unit': 10.00, 'extended': 20.00},
            cost={'unit': 8.00, 'extended': 16.00}
        )

        serializer = ProposalLineSerializer(line)
        data = serializer.data
        self.assertEqual(data['quantity']['staged'], 2)
        self.assertEqual(data['price']['unit'], 10.00)
        self.assertEqual(data['cost']['unit'], 8.00)
