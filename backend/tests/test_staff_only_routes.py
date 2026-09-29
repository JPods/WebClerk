"""Routes whose handlers take no Actor are staff-only (Bill, 2026-09-28).

`_manage`, the receivables reports, GL export and checkout pricing never see who is asking,
so none of them scopes its queries. A portal customer there applied another org's cash to
another org's invoice and read another org's aging (audit A4-H-1, A4-H-2). A portal person
reaches their own contact, customer and transactions through the door, which scopes every
query to them; these routes refuse them, and a login with no role, before any handler runs.
"""
import pytest
from rest_framework.test import APIClient

from apps.core.models import Contact

pytestmark = pytest.mark.django_db

ROUTES = [
    ('post', '/wcapi/_manage/', {'action': 'get_accounting_dashboard', 'params': {}}),
    ('post', '/wcapi/_manage/', {'action': 'apply_cash_to_invoice',
                                 'params': {'cash_id': 1, 'invoice_id': 1, 'amount': '1'}}),
    ('get', '/wcapi/reports/aged_receivables/', None),
    ('get', '/wcapi/reports/statement/1/', None),
    ('get', '/wcapi/reports/gl-export/', None),
    ('get', '/wcapi/cash/checkout-pricing/1/', None),
]


def _client(role, **extra):
    user = Contact.objects.create(email=f'{role or "norole"}@example.com', role=role, **extra)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _call(client, method, path, body):
    return getattr(client, method)(path, body, format='json') if body is not None \
        else getattr(client, method)(path)


@pytest.mark.parametrize('role', ['customer', 'buyer', 'vendor', 'manufacturer', 'user'])
@pytest.mark.parametrize('method,path,body', ROUTES)
def test_a_non_staff_login_is_refused_before_the_handler(role, method, path, body):
    response = _call(_client(role), method, path, body)
    assert response.status_code == 403, (path, response.status_code)
    assert 'staff' in str(response.content).lower()


@pytest.mark.parametrize('method,path,body', ROUTES)
def test_an_anonymous_visitor_is_refused(method, path, body):
    response = _call(APIClient(), method, path, body)
    assert response.status_code in (401, 403)


def test_a_staff_role_reaches_manage():
    response = _call(_client('accounting'), 'post', '/wcapi/_manage/',
                     {'action': 'get_report_registry', 'params': {}})
    assert response.status_code != 403, response.content


def test_commission_tools_still_need_django_staff():
    """The inner tier stands: a staff role without is_staff cannot run commission tools."""
    response = _call(_client('sales'), 'post', '/wcapi/_manage/',
                     {'action': 'get_commission_report', 'params': {}})
    assert response.status_code == 403
    assert 'staff_required' in str(response.content)
