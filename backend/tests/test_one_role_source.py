"""contact.role is a login's one role (Bill, 2026-10-29; core.models audit step 3).

/me reports it as login does; contact.refs.roles claims nothing. Anyone may sign up, as on any
e-commerce site, and becomes a customer of its own; any more authority is an admin's to grant
by changing contact.role (Bill, 2026-10-30).
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
def test_a_sign_up_is_a_customer_of_its_own():
    from apps.orgs.models import OrgBase, OrgType
    theirs = OrgBase.objects.create(company='zz Acme Sign-up', org_type=OrgType.CUSTOMER)
    email = f'{get_random_string(8).lower()}@example.com'
    resp = APIClient().post('/wcapi/register/', {
        'email': email, 'password': get_random_string(20) + 'A1!',
        'company': 'zz Acme Sign-up', 'portal_role': 'rep'}, format='json')
    assert resp.status_code == 201, resp.content
    user = resp.json()['data']['user']
    assert user['roles'] == ['customer'] and user['is_portal'] is True

    contact = Contact.objects.get(email=email)
    assert contact.role == 'customer'                        # 'rep' asked for, not granted
    assert contact.customer_id and contact.customer_id != theirs.pk   # never matched by name
    org = OrgBase.objects.get(pk=contact.customer_id)
    assert org.org_type == OrgType.CUSTOMER and org.company == 'zz Acme Sign-up'
