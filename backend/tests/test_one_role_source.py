"""contact.role is a login's one role (Bill, 2026-10-29; core.models audit step 3).

/me reports it as login does; contact.refs.roles claims nothing; a sign-up is granted no role —
an admin sets contact.role.
"""
import pytest
from django.utils.crypto import get_random_string
from rest_framework.test import APIClient

from apps.core.models import Contact


def _me(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client.get('/wcapi/me/').json()['data']['user']


@pytest.mark.django_db
def test_me_reads_the_role_not_refs():
    cust = Contact.objects.create(email=f'{get_random_string(8)}@example.com', role='customer',
                                  is_active=True, refs={'roles': ['user_vendor', 'admin']})
    me = _me(cust)
    assert me['roles'] == ['customer'] and me['is_portal'] is True

    clerk = Contact.objects.create(email=f'{get_random_string(8)}@example.com', role='user',
                                   is_active=True, refs={'roles': ['user_customer']})
    me = _me(clerk)
    assert me['roles'] == [] and me['is_portal'] is False            # 'user' is no role


@pytest.mark.django_db
def test_portal_sign_up_is_granted_no_role():
    email = f'{get_random_string(8).lower()}@example.com'
    resp = APIClient().post('/wcapi/register/', {
        'email': email, 'password': get_random_string(20) + 'A1!',
        'company': f'zz {get_random_string(6)}', 'portal_role': 'customer'}, format='json')
    assert resp.status_code == 201, resp.content
    user = resp.json()['data']['user']
    assert user['roles'] == [] and user['is_portal'] is False

    contact = Contact.objects.get(email=email)
    assert contact.role == 'user' and 'roles' not in (contact.refs or {}) and not contact.customer_id
