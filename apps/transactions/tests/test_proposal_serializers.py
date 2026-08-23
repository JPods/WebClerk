import pytest
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import serializers
from apps.transactions.models import Proposal, ProposalLine
from apps.transactions.serializers.transaction_serializers import ProposalSerializer, ProposalLineSerializer
from apps.core.models import Contact


class ProposalSerializerTest(TestCase):
    """Test cases for ProposalSerializer."""

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
            'customer_name', 'vendor_name', 'cost', 'sell', 'totals', 'total', 'balance',
            'finance', 'flow',
            'source', 'action', 'line_count',
            'lines', 'dt_created', 'dt_modified', 'version'
        ]

        for field in expected_fields:
            self.assertIn(field, data)

    def test_proposal_serializer_customer_name(self):
        """Test customer name resolution."""
        serializer = ProposalSerializer(self.proposal)
        data = serializer.data

        self.assertEqual(data['customer_name'], "John Doe")

    def test_proposal_serializer_vendor_name(self):
        """Test vendor name resolution."""
        serializer = ProposalSerializer(self.proposal)
        data = serializer.data

        self.assertEqual(data['vendor_name'], "Jane Smith")

    def test_proposal_serializer_computed_fields(self):
        """Test computed fields via totals envelope."""
        serializer = ProposalSerializer(self.proposal)
        data = serializer.data

        # totals envelope is the source of truth for all computed values
        self.assertIn('totals', data)
        self.assertIn('total', data)
        self.assertIn('balance', data)

    def test_proposal_serializer_line_count(self):
        """Test line count calculation."""
        # Create some line items
        ProposalLine.objects.create(
            parent=self.proposal,
            description="Item 1",
            quantity=1
        )
        ProposalLine.objects.create(
            parent=self.proposal,
            description="Item 2",
            quantity=2
        )

        serializer = ProposalSerializer(self.proposal)
        data = serializer.data

        self.assertEqual(data['line_count'], 2)

    def test_proposal_serializer_status_validation(self):
        """Test status field validation."""
        serializer = ProposalSerializer()

        # Valid status
        self.assertEqual(serializer.validate_status("planned"), "planned")

        # Invalid status
        with self.assertRaises(serializers.ValidationError):
            serializer.validate_status("invalid_status")

    def test_proposal_serializer_customer_validation(self):
        """Test customer validation."""
        serializer = ProposalSerializer()

        # Valid customer (exists)
        result = serializer.validate_customer_id(self.customer.id)
        self.assertEqual(result, self.customer.id)

        # Invalid customer (doesn't exist)
        with self.assertRaises(serializers.ValidationError):
            serializer.validate_customer_id(99999)

    def test_proposal_serializer_vendor_validation(self):
        """Test vendor validation."""
        serializer = ProposalSerializer()

        # Valid vendor (exists)
        result = serializer.validate_vendor_id(self.vendor.id)
        self.assertEqual(result, self.vendor.id)

        # Invalid vendor (doesn't exist)
        with self.assertRaises(serializers.ValidationError):
            serializer.validate_vendor_id(99999)

    def test_proposal_serializer_cross_field_validation(self):
        """Test cross-field validation."""
        serializer = ProposalSerializer()

        # Same customer and vendor should fail
        data = {
            'customer_id': self.customer.id,
            'vendor_id': self.customer.id,
            'status': 'planned'
        }

        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.validate(data)

        self.assertIn("Customer and vendor cannot be the same entity", str(cm.exception))

    def test_proposal_serializer_status_transition_validation(self):
        """Test status transition validation."""
        serializer = ProposalSerializer(instance=self.proposal)

        # Valid transition: planned -> sent
        data = {'status': 'sent'}
        result = serializer.validate(data)
        self.assertEqual(result['status'], 'sent')

        # Invalid transition: planned -> accepted (should fail)
        data = {'status': 'accepted'}
        with self.assertRaises(serializers.ValidationError):
            serializer.validate(data)


class ProposalLineSerializerTest(TestCase):
    """Test cases for ProposalLineSerializer."""

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

    def test_proposal_line_serializer_fields(self):
        """Test that serializer includes all expected fields."""
        line = ProposalLine.objects.create(
            parent=self.proposal,
            description="Test Item",
            quantity=2,
            price={'sell': 10.00, 'cost': 8.00},
            discount_amount=1.00
        )

        serializer = ProposalLineSerializer(line)
        data = serializer.data

        expected_fields = [
            'id', 'parent', 'item_id', 'description', 'quantity', 'price',
            'discount_amount', 'extended_price', 'item_name', 'unit_cost',
            'line_margin', 'dt_created', 'dt_modified', 'version'
        ]

        for field in expected_fields:
            self.assertIn(field, data)

    def test_proposal_line_serializer_computed_fields(self):
        """Test computed fields calculation."""
        line = ProposalLine.objects.create(
            parent=self.proposal,
            description="Test Item",
            quantity=2,
            price={'sell': 10.00, 'cost': 8.00},
            discount_amount=1.00
        )

        serializer = ProposalLineSerializer(line)
        data = serializer.data

        # extended_price = (2 * 10.00) - 1.00 = 19.00
        self.assertEqual(data['extended_price'], 19.00)

        # unit_cost = 8.00
        self.assertEqual(data['unit_cost'], 8.00)

        # line_margin = (10.00 - 8.00) * 2 - 1.00 = 3.00
        self.assertEqual(data['line_margin'], 3.00)

        # item_name should fallback to description
        self.assertEqual(data['item_name'], "Test Item")

    def test_proposal_line_serializer_quantity_validation(self):
        """Test quantity validation."""
        serializer = ProposalLineSerializer()

        # Valid quantity
        self.assertEqual(serializer.validate_quantity(5), 5)

        # Invalid quantity (zero)
        with self.assertRaises(serializers.ValidationError):
            serializer.validate_quantity(0)

        # Invalid quantity (negative)
        with self.assertRaises(serializers.ValidationError):
            serializer.validate_quantity(-1)

    def test_proposal_line_serializer_discount_validation(self):
        """Test discount amount validation."""
        serializer = ProposalLineSerializer()

        # Valid discount
        self.assertEqual(serializer.validate_discount_amount(5.00), 5.00)
        self.assertEqual(serializer.validate_discount_amount(0), 0)

        # Invalid discount (negative)
        with self.assertRaises(serializers.ValidationError):
            serializer.validate_discount_amount(-1.00)

    def test_proposal_line_serializer_price_validation(self):
        """Test price structure validation."""
        serializer = ProposalLineSerializer()

        # Valid price
        valid_price = {'sell': 10.00, 'cost': 8.00}
        self.assertEqual(serializer.validate_price(valid_price), valid_price)

        # Invalid price (not a dict)
        with self.assertRaises(serializers.ValidationError):
            serializer.validate_price("not_a_dict")

        # Invalid price (missing sell)
        with self.assertRaises(serializers.ValidationError):
            serializer.validate_price({'cost': 8.00})

        # Invalid price (negative sell)
        with self.assertRaises(serializers.ValidationError):
            serializer.validate_price({'sell': -10.00, 'cost': 8.00})

        # Invalid price (negative cost)
        with self.assertRaises(serializers.ValidationError):
            serializer.validate_price({'sell': 10.00, 'cost': -8.00})

    def test_proposal_line_serializer_cross_field_validation(self):
        """Test cross-field validation."""
        serializer = ProposalLineSerializer()

        # Valid data
        valid_data = {
            'quantity': 2,
            'price': {'sell': 10.00, 'cost': 8.00},
            'discount_amount': 1.00
        }
        result = serializer.validate(valid_data)
        self.assertEqual(result, valid_data)

        # Invalid data (discount exceeds extended price)
        invalid_data = {
            'quantity': 2,
            'price': {'sell': 10.00, 'cost': 8.00},
            'discount_amount': 25.00  # Exceeds 2 * 10.00 = 20.00
        }

        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.validate(invalid_data)

        self.assertIn("Discount amount cannot exceed the extended price", str(cm.exception))