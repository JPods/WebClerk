"""A served layout keeps a computed column when the role may view its source.

Found 2026-11-03 (wc3-layouts browser walk): the customer list defined twelve columns and
drew eight. filter_setting_layout tested each column's field against the role's leaf set,
and OrgBase/Contact COMPUTED_FIELDS (display_name, phone, address_full, domain) are no
leaves — filter_response_data had served them all along, by COMPUTED_FROM. One rule, both
places.
"""
import pytest
from django.utils.crypto import get_random_string

from apps.core.models.setting import Setting
from apps.core.services import access
from apps.core.services.door import Actor
from apps.core.services.field_projection import filter_setting_layout

COLUMNS = [{'field': 'ida'}, {'field': 'display_name'}, {'field': 'phone'}, {'field': 'company'}]


@pytest.fixture
def customer_policy(db):
    s = Setting.objects.filter(purpose='wc:model', parent_model='customer').first() or Setting(
        purpose='wc:model', parent_model='customer', name='Customer Model Definition',
        ida='wc-model-customer')
    s.config = {**(s.config or {}),
                'layout': {'list': {'default': {'columns': COLUMNS}}},
                # company (display_name's source) is viewable; phone_id (phone's) is not
                'access': {'roles': {'admin': {'view': ['id', 'ida', 'company'], 'edit': [],
                                               'scope': {}}}}}
    s._setting_create_authorized = True
    s.save()
    access.clear_cache()
    yield s
    access.clear_cache()


@pytest.mark.django_db
def test_computed_column_stays_when_its_source_is_viewable(django_user_model, customer_policy):
    user = django_user_model.objects.create_user(
        email='admin@example.fake', password=get_random_string(20), role='admin',
        name_first='A', name_last='Dmin')
    served = filter_setting_layout(Actor(user=user), {
        'purpose': 'wc:model', 'parent_model': 'customer', 'config': customer_policy.config})
    fields = [c['field'] for c in served['config']['layout']['list']['default']['columns']]
    assert fields == ['ida', 'display_name', 'company']
