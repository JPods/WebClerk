"""
Quote integration tests.

The DRF QuoteViewSet is ReadOnly -- all writes go through /wcapi/save/
or /wcapi/transaction/save/. These tests verify the read endpoints work
and skip write-dependent workflows that require the full wcapi pipeline.
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.transactions.models import Quote
from apps.orgs.models import OrgBase
from apps.core.models import Contact

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_user(db):
    return Contact.objects.create(
        email='proptest@example.com',
        name_first='Prop',
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
    return OrgBase.objects.create(display_name="John Doe", org_type="customer")


@pytest.fixture
def vendor(db):
    return OrgBase.objects.create(display_name="Jane Smith", org_type="vendor")


def test_quote_list_endpoint(api_client):
    """Test that the quote list endpoint returns 200."""
    url = reverse('transactions:quote-list')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK


def test_quote_detail_endpoint(api_client, customer, vendor):
    """Test that the quote detail endpoint returns 200 for an existing quote."""
    quote = Quote.objects.create(
        status='planned',
        customer_id=customer.id,
        vendor_id=vendor.id,
    )
    url = reverse('transactions:quote-detail', kwargs={'pk': quote.pk})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK


def test_quote_list_is_read_only(api_client, customer, vendor):
    """POST to quote-list should return 405 (ReadOnly viewset)."""
    url = reverse('transactions:quote-list')
    response = api_client.post(url, {
        'ida': 'PROP-RO-001',
        'status': 'planned',
        'customer_id': customer.id,
        'vendor_id': vendor.id,
    }, format='json')
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_quote_convert_to_order_endpoint_exists(api_client, customer):
    """Test that the convert-to-order action endpoint exists (POST required)."""
    quote = Quote.objects.create(
        status='planned',
        customer_id=customer.id,
    )
    url = reverse('transactions:quote-convert-to-order', kwargs={'pk': quote.pk})
    # Should return something other than 404 (the endpoint exists)
    response = api_client.post(url, {}, format='json')
    assert response.status_code != status.HTTP_404_NOT_FOUND
