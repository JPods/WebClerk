"""
Quote integration tests.

The QuoteViewSet carries actions only: reads go through /wcapi/get/, writes through
/wcapi/save/ or /wcapi/transaction/save/.
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
    return OrgBase.objects.create(company="John Doe", org_type="customer")


@pytest.fixture
def vendor(db):
    return OrgBase.objects.create(company="Jane Smith", org_type="vendor")


def test_quote_has_no_list_or_detail_route():
    """Reads go through /wcapi/get/ only (Bill, 2026-09-23: all gets flow through one
    channel). The viewset carries actions, never a second list or detail read."""
    from django.urls import NoReverseMatch
    for name, kwargs in (('transactions:quote-list', {}), ('transactions:quote-detail', {'pk': 1})):
        with pytest.raises(NoReverseMatch):
            reverse(name, kwargs=kwargs)


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
