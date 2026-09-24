"""
Quote integration tests.

The QuoteViewSet carries actions only: reads go through GET /wcapi/quote/[<id>/], writes
through POST /wcapi/quote/ and PUT /wcapi/quote/<id>/ (lines included).
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
    """Converting is a command on the quote: POST /wcapi/quote/<id>/convert/ {to}. A quote
    with no lines is refused with the reason, not a missing route."""
    quote = Quote.objects.create(status='planned', customer_id=customer.id)
    response = api_client.post(f'/wcapi/quote/{quote.pk}/convert/', {'to': 'order'}, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.content
    assert response.json()['error']['code'] == 'no_lines'
