"""Portal role policy — what a customer and a vendor may see and change.

Bill, 2026-09-17:
  - editing is staff-only for now; customer and vendor portal users are view-only
  - a customer sees their price, not other prices, and no costs
  - a vendor sees no prices and only their last cost
  - a vendor sees the inventory numbers, so they can keep the customer never over
    and never short

Bill, 2026-09-18: positive lists. The policy is data in the model's wc:model
Setting (config.access); nothing leaves the server unless a role's list names
the leaf. No list → nothing. Agents may act as another role to test it.
"""
import pytest
from django.utils.crypto import get_random_string

from apps.core.models.setting import Setting
from apps.core.services import access
from apps.core.services.field_projection import filter_response_data
from apps.core.services.role_filter import get_allowed_fields, user_price_level
from apps.orgs.models import OrgBase


ITEM_RECORD = {
    'id': 1, 'ida': 'W-1', 'uuid': 'abc', 'name': 'Widget', 'description': 'A widget',
    'sku': 'WDG-1', 'kind': 'part', 'uom': 'ea',
    'price': {'base': 10.0, 'msrp': 20.0, 'retail': 18.0, 'wholesale': 12.0,
              'distributor': 11.0},
    'cost': {'standard': 8.0, 'last': 7.5, 'avg': 7.9, 'landed': 8.4},
    'quantity': {'on_hand': 40, 'available': 35, 'on_po': 10, 'min': 10, 'max': 50},
}

CUSTOMER_VIEW = ['id', 'ida', 'name', 'description', 'sku', 'kind', 'uom',
                 'price.$user.price_level']
VENDOR_VIEW = ['id', 'ida', 'uuid', 'name', 'description', 'sku', 'cost.last',
               'quantity.on_hand', 'quantity.available', 'quantity.on_po',
               'quantity.min', 'quantity.max']
STAFF_EDIT = ['name', 'description', 'sku']


@pytest.fixture
def item_policy(db):
    """The 2026-09-17 item policy as a wc:model Setting."""
    s = Setting.objects.filter(purpose='wc:model', parent_model='item').first() or Setting(
        purpose='wc:model', parent_model='item', name='Item Model Definition', ida='wc-model-item')
    s.config = {**(s.config or {}), 'access': {'roles': {
                    'customer': {'view': CUSTOMER_VIEW, 'edit': [], 'scope': {}},
                    'vendor': {'view': VENDOR_VIEW, 'edit': [], 'scope': {}},
                    'superuser': {'view': VENDOR_VIEW + ['price.retail'],
                                  'edit': STAFF_EDIT, 'scope': {}},
                }}}
    s._setting_create_authorized = True
    s._setting_update_authorized = True
    s.save()
    access.clear_cache()
    yield s
    access.clear_cache()


def _login(django_user_model, email, role, org_kind=None, price_level=''):
    """A login is a Contact (AUTH_USER_MODEL); its role is contact.role."""
    kwargs = {}
    if org_kind:
        kwargs[org_kind] = OrgBase.objects.create(display_name=f'{org_kind} co',
                                                   org_type=org_kind, price_level=price_level)
    return django_user_model.objects.create_user(
        email=email, password=get_random_string(20), role=role,
        name_first='P', name_last='User', **kwargs)


@pytest.mark.django_db
class TestCustomerPortal:
    def test_sees_their_price_and_no_other_prices(self, django_user_model, item_policy):
        user = _login(django_user_model, 'cust@example.fake', 'customer', 'customer', 'wholesale')
        assert user_price_level(user) == 'wholesale'
        visible = filter_response_data(user, 'item', ITEM_RECORD)
        assert visible.get('price') == {'wholesale': 12.0}

    def test_sees_no_costs(self, django_user_model, item_policy):
        user = _login(django_user_model, 'cust2@example.fake', 'customer', 'customer', 'retail')
        assert 'cost' not in filter_response_data(user, 'item', ITEM_RECORD)

    def test_no_price_at_all_when_org_has_no_price_level(self, django_user_model, item_policy):
        """An unresolved price level drops the field — it never widens to every tier."""
        user = _login(django_user_model, 'cust3@example.fake', 'customer', 'customer', '')
        assert 'price' not in filter_response_data(user, 'item', ITEM_RECORD)

    def test_edits_nothing(self, django_user_model, item_policy):
        user = _login(django_user_model, 'cust4@example.fake', 'customer', 'customer', 'retail')
        for model in ('order', 'invoice', 'quote', 'item', 'contact'):
            assert get_allowed_fields(user, model, mode='edit') == [], model


@pytest.mark.django_db
class TestVendorPortal:
    def test_sees_last_cost_only_and_no_prices(self, django_user_model, item_policy):
        user = _login(django_user_model, 'vend@example.fake', 'vendor', 'vendor')
        visible = filter_response_data(user, 'item', ITEM_RECORD)
        assert visible.get('cost') == {'last': 7.5}
        assert 'price' not in visible

    def test_sees_the_inventory_numbers(self, django_user_model, item_policy):
        """So the vendor can keep the customer never over and never short."""
        user = _login(django_user_model, 'vend2@example.fake', 'vendor', 'vendor')
        quantity = filter_response_data(user, 'item', ITEM_RECORD).get('quantity', {})
        for key in ('on_hand', 'available', 'on_po', 'min', 'max'):
            assert key in quantity, key

    def test_edits_nothing(self, django_user_model, item_policy):
        user = _login(django_user_model, 'vend4@example.fake', 'vendor', 'vendor')
        for model in ('purchase', 'item', 'action', 'project'):
            assert get_allowed_fields(user, model, mode='edit') == [], model


@pytest.mark.django_db
class TestPositiveList:
    def test_superuser_is_a_list_not_a_bypass(self, django_user_model, item_policy):
        user = django_user_model.objects.create_superuser(
            email='staff@example.fake', password=get_random_string(20),
            name_first='S', name_last='T', username='')
        assert get_allowed_fields(user, 'item', mode='edit') == STAFF_EDIT
        visible = filter_response_data(user, 'item', ITEM_RECORD)
        assert 'price' in visible and set(visible['price']) == {'retail'}

    def test_no_list_means_nothing(self, django_user_model, item_policy):
        """A role with no block on the model sees nothing — fail closed."""
        user = _login(django_user_model, 'rep@example.fake', 'rep')
        assert filter_response_data(user, 'item', ITEM_RECORD) == {}

    def test_user_role_is_no_access(self, django_user_model, item_policy):
        user = _login(django_user_model, 'plain@example.fake', 'user')
        assert access.user_role(user) is None
        assert filter_response_data(user, 'item', ITEM_RECORD) == {}

    def test_parent_path_is_refused(self, item_policy):
        """A container is not a leaf: the guard refuses 'price', accepts 'price.retail'."""
        problems = access.validate_access('item', {'roles': {'vendor': {'view': ['price']}}})
        assert any("'price' is not a leaf" in p for p in problems)
        assert access.validate_access('item', {'roles': {'vendor': {'view': ['price.retail']}}}) == []

    def test_projection_keeps_only_named_leaves(self):
        from apps.core.services.field_projection import filter_data_by_fields
        assert filter_data_by_fields(ITEM_RECORD, ['price.retail', 'cost.last']) == {
            'price': {'retail': 18.0}, 'cost': {'last': 7.5}}

    def test_guard_refuses_a_wildcard(self, item_policy):
        from django.core.exceptions import ValidationError
        item_policy.config['access']['roles']['vendor']['view'] = ['*']
        item_policy._setting_update_authorized = True
        with pytest.raises(ValidationError):
            item_policy.save()

    def test_agent_acting_as_customer_sees_what_a_customer_sees(self, django_user_model, item_policy):
        agent = _login(django_user_model, 'agent@example.fake', 'agent', 'customer', 'wholesale')
        access.apply_act_as_user(agent, {access.ACT_AS_HEADER: 'customer'})
        assert access.user_role(agent) == 'customer'
        assert filter_response_data(agent, 'item', ITEM_RECORD).get('price') == {'wholesale': 12.0}

    def test_only_agents_may_act_as(self, django_user_model, item_policy):
        from rest_framework.exceptions import PermissionDenied
        vendor = _login(django_user_model, 'v9@example.fake', 'vendor', 'vendor')
        with pytest.raises(PermissionDenied):
            access.apply_act_as_user(vendor, {access.ACT_AS_HEADER: 'customer'})
        agent = _login(django_user_model, 'a9@example.fake', 'agent')
        with pytest.raises(PermissionDenied):
            access.apply_act_as_user(agent, {access.ACT_AS_HEADER: 'superuser'})
