"""The one read channel (Bill, 2026-09-23).

"All /GET/ should flow through one channel with authorization required to do more than
see items with publish = 1." Publish is security_level (0 = unpublished, readmes/96); the
anonymous visitor is the public role in code, access.PUBLIC_READ: items only, public leaves
only.
"""
import pytest
from rest_framework.test import APIClient

from apps.core.models import Contact
from apps.core.services import access
from apps.core.services.record_serialize import visible_queryset
from apps.products.models import Item
from apps.transactions.models import Quote

pytestmark = pytest.mark.django_db


@pytest.fixture
def items(db):
    published = Item.objects.create(
        ida='PUB-1', name='Published widget', sku='PUB-1', security_level=access.PUBLIC_LEVEL,
        price={'retail': 20.0, 'wholesale': 12.0, 'distributor': 10.0, 'msrp': 25.0,
               'currency': 'USD'},
        cost={'unit': 7.0},
    )
    unpublished = Item.objects.create(ida='HID-1', name='Hidden widget', sku='HID-1')
    return published, unpublished


def test_anonymous_sees_only_published_items(items):
    published, unpublished = items
    _cls, qs = visible_queryset('item', user=None)
    assert list(qs.values_list('pk', flat=True)) == [published.pk]


def test_anonymous_sees_no_other_model(items):
    Contact.objects.create(email='someone@example.com', security_level=access.PUBLIC_LEVEL)
    _cls, qs = visible_queryset('contact', user=None)
    assert not qs.exists()


def test_anonymous_get_projects_to_public_leaves(items):
    published, _ = items
    response = APIClient().get('/wcapi/get/', {'model_name': 'item'})
    assert response.status_code == 200
    rows = response.json()['data']['results']
    assert [r['ida'] for r in rows] == ['PUB-1']
    row = rows[0]
    assert row['price'] == {'retail': 20.0, 'currency': 'USD'}
    for private in ('cost', 'vendor_id', 'margin_pct', 'quantity', 'metadata', 'gls'):
        assert private not in row


def test_anonymous_get_unpublished_item_by_id_is_empty(items):
    _, unpublished = items
    response = APIClient().get('/wcapi/get/', {'model_name': 'item', 'id': unpublished.pk})
    assert response.status_code == 200
    assert response.json()['data']['record'] is None


def test_anonymous_get_of_a_non_public_model_is_refused(items):
    response = APIClient().get('/wcapi/get/', {'model_name': 'contact'})
    assert response.status_code == 401


def test_anonymous_search_matches_public_text_leaves_only(items):
    response = APIClient().get('/wcapi/get/', {'model_name': 'item', 'search': 'widget'})
    assert [r['ida'] for r in response.json()['data']['results']] == ['PUB-1']


def test_contact_search_requires_login():
    response = APIClient().get('/wcapi/ai/contact/search/', {'q': 'a'})
    assert response.status_code in (401, 403)


def test_action_cannot_reach_a_record_its_caller_cannot_read(db):
    """A viewset action looks its record up through visible_queryset: a signed-in user
    whose role shows them no quotes gets 404, not the quote."""
    quote = Quote.objects.create(status='planned')
    portal = Contact.objects.create(email='portal@example.com', role='customer')
    client = APIClient()
    client.force_authenticate(user=portal)
    response = client.post(f'/wcapi/quote/{quote.pk}/convert-to-order/', {}, format='json')
    assert response.status_code == 404


# ── Gate 1: security_level ──────────────────────────────────────────────

def _person(role, **extra):
    return Contact.objects.create(email=f'{role}-lvl@example.com', role=role, **extra)


@pytest.mark.parametrize('role, seen', [
    ('customer', {1, 2}),
    ('vendor', {1, 2, 3}),
    ('rep', {1, 2, 3}),
    ('employee', {1, 2, 3, 4}),
    ('agent', {1, 2, 3, 4}),
    ('admin', {0, 1, 2, 3, 4, 5, 9}),
])
def test_level_ladder(role, seen):
    """Staff see 0 (unpublished); everyone else sees 0 < level <= their ceiling."""
    for level in (0, 1, 2, 3, 4, 5, 9):
        Item.objects.create(ida=f'LVL-{level}', name=f'L{level}', security_level=level)
    q = access.level_q(_person(role))
    assert set(Item.objects.filter(q).values_list('security_level', flat=True)) == seen


def test_a_login_with_no_role_sees_nothing():
    Item.objects.create(ida='LVL-NR', name='x', security_level=1)
    assert not Item.objects.filter(access.level_q(_person('user'))).exists()


def test_new_records_start_where_bill_ruled():
    """Items start unpublished (0); every other new record starts at 1 so its creator
    sees it (Bill, 2026-09-23)."""
    from apps.core.services.door import Actor
    from apps.core.services.save import save_record
    admin = _person('admin', is_staff=True, is_superuser=True)
    item = save_record(Actor(user=admin), {'model_name': 'item', 'ida': 'NEW-I', 'name': 'n'})
    quote = save_record(Actor(user=admin), {'model_name': 'quote', 'name': 'NEW-Q'})
    assert Item.objects.get(pk=item.obj_id).security_level == 0
    assert Quote.objects.get(pk=quote.obj_id).security_level == 1


# ── A person's own record ───────────────────────────────────────────────

def test_a_login_with_no_role_reaches_its_own_contact_and_no_other():
    """Bill, 2026-09-23: a person always reaches their own contact, role or none."""
    me = Contact.objects.create(email='me@example.com', role='user')
    other = Contact.objects.create(email='other@example.com', role='user', security_level=1)
    _cls, qs = visible_queryset('contact', user=me)
    assert set(qs.values_list('pk', flat=True)) == {me.pk}
    assert other.pk not in set(qs.values_list('pk', flat=True))


def test_a_login_with_no_role_may_not_create():
    """The create gate: a role with no block for the model creates nothing."""
    from apps.core.services.door import Actor, Refused
    from apps.core.services.save import save_record
    me = Contact.objects.create(email='nocreate@example.com', role='user')
    with pytest.raises(Refused) as refused:
        save_record(Actor(user=me), {'model_name': 'quote', 'name': 'NOPE'})
    assert refused.value.status == 403
    assert refused.value.code == 'create_not_permitted'
