"""Tests for line serializer JSON deep-merge behavior.

Verifies that PATCH/PUT operations on line JSON fields deep-merge
rather than replacing the entire field. This ensures that updating
only quantity.transferred preserves the existing quantity.staged value.
"""

import pytest
from rest_framework.test import APIRequestFactory
from apps.transactions.serializers.line_serializers import (
    OrderLineSerializer,
    InvoiceLineSerializer,
)
from apps.transactions.models import Order, OrderLine, Invoice, InvoiceLine
from apps.products.models import Item


@pytest.fixture
def api_factory():
    return APIRequestFactory()


@pytest.fixture
def test_item(db):
    """Create a test item for use in line tests."""
    return Item.objects.create(
        name="Test Item",
        ida="TEST-SERIAL-001",
        price={"base": 100},
        cost={"standard": 50},
    )


@pytest.fixture
def test_order(db):
    """Create a test order."""
    return Order.objects.create(status="draft", ida="ORD-001")


@pytest.fixture
def test_invoice(db):
    """Create a test invoice."""
    return Invoice.objects.create(status="draft", ida="INV-001")


@pytest.mark.django_db
class TestOrderLineSerializerMerge:
    """Test JSON deep-merge behavior for OrderLineSerializer."""

    def test_update_transferred_preserves_staged(self, api_factory, test_item, test_order):
        """PATCH with only transferred should preserve existing staged value."""
        # Create initial line
        line = OrderLine.objects.create(
            order=test_order,
            item_fk=test_item,
            quantity={"staged": 10, "transferred": 0, "remaining": 10},
            price={"unit": 100, "extended": 1000},
        )

        # Simulate PATCH request context
        request = api_factory.patch('/fake/')
        
        # Update only transferred
        serializer = OrderLineSerializer(
            instance=line,
            data={"quantity": {"transferred": 5}},
            partial=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        updated_line = serializer.save()

        # Verify staged was preserved and remaining recalculated
        assert updated_line.quantity["staged"] == 10
        assert updated_line.quantity["transferred"] == 5
        # remaining should be recalculated by normalize_quantity_map
        assert updated_line.quantity["remaining"] == 5.0

    def test_update_price_unit_preserves_extended(self, api_factory, test_item, test_order):
        """PATCH with only price.unit should preserve existing price keys."""
        line = OrderLine.objects.create(
            order=test_order,
            item_fk=test_item,
            quantity={"staged": 5, "transferred": 5, "remaining": 0},
            price={"unit": 100, "extended": 500, "discount_percent": 10},
        )

        request = api_factory.patch('/fake/')
        
        serializer = OrderLineSerializer(
            instance=line,
            data={"price": {"unit": 150}},
            partial=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        updated_line = serializer.save()

        # Verify discount_percent was preserved
        assert updated_line.price["unit"] == 150
        assert updated_line.price["discount_percent"] == 10

    def test_update_item_description_preserves_item_id(self, api_factory, test_item, test_order):
        """PATCH with only item.description should preserve existing item_id."""
        line = OrderLine.objects.create(
            order=test_order,
            item_fk=test_item,
            item={"item_id": test_item.pk, "description": "Original Desc"},
            quantity={"staged": 1, "transferred": 1, "remaining": 0},
        )

        request = api_factory.patch('/fake/')
        
        serializer = OrderLineSerializer(
            instance=line,
            data={"item": {"description": "Updated Desc"}},
            partial=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        updated_line = serializer.save()

        # Verify item_id was preserved
        assert updated_line.item["item_id"] == test_item.pk
        assert updated_line.item["description"] == "Updated Desc"


@pytest.mark.django_db
class TestInvoiceLineSerializerMerge:
    """Test JSON deep-merge behavior for InvoiceLineSerializer."""

    def test_invoice_remaining_always_zero(self, api_factory, test_item, test_invoice):
        """Invoice lines should always have remaining = 0 after any update."""
        line = InvoiceLine.objects.create(
            invoice=test_invoice,
            item_fk=test_item,
            quantity={"staged": 10, "transferred": 10, "remaining": 0},
            price={"unit": 100, "extended": 1000},
        )

        request = api_factory.patch('/fake/')
        
        serializer = InvoiceLineSerializer(
            instance=line,
            data={"quantity": {"transferred": 5}},
            partial=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        updated_line = serializer.save()

        # Invoice remaining should always be 0
        assert updated_line.quantity["remaining"] == 0
        # staged should sync with transferred if not explicitly set differently
        assert updated_line.quantity["transferred"] == 5
