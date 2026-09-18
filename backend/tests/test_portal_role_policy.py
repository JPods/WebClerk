"""Portal role policy — what a customer and a vendor may see and change.

Bill, 2026-09-17:
  - editing is staff-only for now; customer and vendor portal users are view-only
  - a customer sees their price, not other prices, and no costs
  - a vendor sees no prices and only their last cost
  - a vendor sees the inventory numbers, so they can keep the customer never over
    and never short
"""
import pytest
from django.utils.crypto import get_random_string

from apps.core.models import Contact, UserProfile
from apps.core.services.field_projection import filter_response_data
from apps.core.services.role_filter import get_allowed_fields, get_denied_fields, user_price_level
from apps.orgs.models import OrgBase
from apps.products.models import Item


ITEM_RECORD = {
    'id': 1, 'ida': 'W-1', 'uuid': 'abc', 'name': 'Widget', 'description': 'A widget',
    'sku': 'WDG-1', 'kind': 'part', 'uom': 'ea',
    'price': {'base': 10.0, 'msrp': 20.0, 'retail': 18.0, 'wholesale': 12.0,
              'distributor': 11.0},
    'cost': {'standard': 8.0, 'last': 7.5, 'avg': 7.9, 'landed': 8.4},
    'quantity': {'on_hand': 40, 'available': 35, 'on_po': 10,
                 'min': 5, 'max': 60,
                 'min': 10, 'max': 50},
}


def _portal_user(django_user_model, email, role, org_kind, price_level=''):
    """A portal user: Django user → UserProfile → Contact → org, with the role
    on contact.refs.roles (how WC3 assigns roles)."""
    org = OrgBase.objects.create(display_name=f'{org_kind} co', org_type=org_kind,
                                 price_level=price_level)
    contact = Contact.objects.create(
        email=email, name_first='P', name_last='User',
        **{org_kind: org}, refs={'roles': [role]})
    user = django_user_model.objects.create_user(
        email=f'login_{email}', password=get_random_string(20))
    UserProfile.objects.create(user=user, contact=contact, cached_roles=[role])
    return user, org


@pytest.mark.django_db
class TestCustomerPortal:
    def test_sees_their_price_and_no_other_prices(self, django_user_model):
        user, _ = _portal_user(django_user_model, 'cust@example.fake',
                               'user_customer', 'customer', price_level='wholesale')
        assert user_price_level(user) == 'wholesale'

        visible = filter_response_data(user, 'item', ITEM_RECORD)
        assert visible.get('price') == {'wholesale': 12.0}
        for tier in ('base', 'msrp', 'retail', 'distributor'):
            assert tier not in visible.get('price', {})

    def test_sees_no_costs(self, django_user_model):
        user, _ = _portal_user(django_user_model, 'cust2@example.fake',
                               'user_customer', 'customer', price_level='retail')
        visible = filter_response_data(user, 'item', ITEM_RECORD)
        assert 'cost' not in visible
        assert 'cost' in get_denied_fields(user, 'item')

    def test_no_price_at_all_when_org_has_no_price_level(self, django_user_model):
        """An unresolved price level drops the field — it never widens to every tier."""
        user, _ = _portal_user(django_user_model, 'cust3@example.fake',
                               'user_customer', 'customer', price_level='')
        visible = filter_response_data(user, 'item', ITEM_RECORD)
        assert 'price' not in visible

    def test_edits_nothing(self, django_user_model):
        user, _ = _portal_user(django_user_model, 'cust4@example.fake',
                               'user_customer', 'customer', price_level='retail')
        for model in ('order', 'invoice', 'proposal', 'item', 'contact'):
            assert get_allowed_fields(user, model, mode='edit') == [], model


@pytest.mark.django_db
class TestVendorPortal:
    def test_sees_last_cost_only_and_no_prices(self, django_user_model):
        user, _ = _portal_user(django_user_model, 'vend@example.fake',
                               'user_vendor', 'vendor')
        visible = filter_response_data(user, 'item', ITEM_RECORD)
        assert visible.get('cost') == {'last': 7.5}
        assert 'price' not in visible

    def test_sees_the_inventory_numbers(self, django_user_model):
        """So the vendor can keep the customer never over and never short."""
        user, _ = _portal_user(django_user_model, 'vend2@example.fake',
                               'user_vendor', 'vendor')
        visible = filter_response_data(user, 'item', ITEM_RECORD)
        quantity = visible.get('quantity', {})
        for key in ('on_hand', 'available', 'on_po',
                    'min', 'max', 'min', 'max'):
            assert key in quantity, key

    def test_identity_fields(self, django_user_model):
        user, _ = _portal_user(django_user_model, 'vend3@example.fake',
                               'user_vendor', 'vendor')
        visible = filter_response_data(user, 'item', ITEM_RECORD)
        for key in ('ida', 'uuid', 'name', 'description', 'sku'):
            assert key in visible, key

    def test_edits_nothing(self, django_user_model):
        user, _ = _portal_user(django_user_model, 'vend4@example.fake',
                               'user_vendor', 'vendor')
        for model in ('purchase', 'item', 'action', 'project'):
            assert get_allowed_fields(user, model, mode='edit') == [], model


@pytest.mark.django_db
def test_staff_still_edits(django_user_model):
    """Editing is staff-only, not nobody-only."""
    user = django_user_model.objects.create_superuser(
        email='staff@example.fake', password=get_random_string(20),
        name_first='S', name_last='T', username='')
    assert get_allowed_fields(user, 'item', mode='edit') == ['*']
