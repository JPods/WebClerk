"""
Cash integration tests.

Reads go through /wcapi/get/, writes through /wcapi/save/.
These tests verify model behavior.
"""
import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.transactions.models import Cash, Invoice
from apps.core.models import Contact
from apps.orgs.models import OrgBase

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_user(db):
    return Contact.objects.create(
        email='paytest@example.com',
        name_first='Pay',
        name_last='Tester',
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def api_client(staff_user):
    client = APIClient()
    client.force_authenticate(user=staff_user)
    return client


@pytest.fixture
def customer(db):
    return OrgBase.objects.create(company="John Doe", org_type="customer")


@pytest.fixture
def vendor(db):
    return OrgBase.objects.create(company="Jane Smith", org_type="vendor")


@pytest.fixture
def contact(db):
    return Contact.objects.create(
        name_first="John",
        name_last="Doe",
        email="john.doe@example.com"
    )


@pytest.fixture
def invoice(db, customer, vendor):
    return Invoice.objects.create(
        status="sent",
        customer_id=customer.id,
        vendor_id=vendor.id,
        totals={'total': 100.00, 'received': 0.00, 'balance': 100.00}
    )


def test_cash_creation(invoice, contact):
    """Test that a cash entry can be created directly."""
    cash = Cash.objects.create(
        invoice=invoice,
        contact_id=contact.pk,
        amount=Decimal('75.50'),
        gateway='stripe',
        status='pending',
    )
    assert cash.id is not None
    assert cash.amount == Decimal('75.50')
    assert cash.status == 'pending'


def test_cash_str_format(invoice, contact):
    """Test that Cash __str__ uses signed format (+amount)."""
    cash = Cash.objects.create(
        invoice=invoice,
        contact_id=contact.pk,
        amount=Decimal('75.50'),
        status='pending',
    )
    s = str(cash)
    # __str__ uses :+.2f format, producing +75.50 for positive amounts
    assert '+75.50' in s
    assert 'pending' in s


def test_cash_has_no_viewset_route():
    """Cash is read through /wcapi/get/ only (Bill, 2026-09-23: one read channel)."""
    from django.urls import NoReverseMatch
    with pytest.raises(NoReverseMatch):
        reverse('transactions:cash-list')
