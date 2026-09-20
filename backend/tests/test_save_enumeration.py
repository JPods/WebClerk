"""What a role may write is an enumeration in a Setting, not a filter.

Bill, 2026-09-20: *"the role access to view/edit must come from a Setting record
enumerated list. Not a filter, but an enumeration."*

/wcapi/transaction/save/ asked three questions — is the user authenticated, may this role
edit this *model*, may they see this *row*. All three are filters; none says which fields.
So once edit was true every header field was writable, while /wcapi/save/ allowed only
what the enumeration named. That was a Bite 1 finding.
"""
import pytest
from django.utils.crypto import get_random_string

from apps.core.models.setting import Setting
from apps.core.services import access
from apps.transactions.views.wcapi import _leaf_paths, _not_enumerated


def _login(django_user_model, email, role):
    return django_user_model.objects.create_user(
        email=email, password=get_random_string(20), role=role,
        name_first='P', name_last='User')


@pytest.fixture
def order_policy(db):
    """Update the order model's own Setting — purpose + parent_model is not unique, so a
    second one is read or ignored depending on which .first() returns."""
    s = Setting.objects.filter(purpose='wc:model', parent_model='order',
                               is_deleted=False).first()
    assert s is not None, "the order model has no wc:model Setting"
    before = dict(s.config or {})
    s.config = ({
        'access': {
            'sets': {'all': ['id', 'status', 'attention', 'dt_needed', 'totals.total',
                             'lines.quantity.active', 'lines.price.unit']},
            'roles': {
                'sales': {'view': ['@all'], 'edit': ['@all'], 'scope': {}, 'create': True},
                'warehouse': {'view': ['@all'], 'edit': ['status'], 'scope': {}, 'create': False},
                'customer': {'view': ['@all'], 'edit': ['attention', 'dt_needed',
                                                        'lines.quantity.active'],
                             'scope': {}, 'create': True},
            }}})
    s._setting_update_authorized = True
    s.save(update_fields=['config'])
    access.clear_cache()
    yield s
    s.config = before
    s._setting_update_authorized = True
    s.save(update_fields=['config'])
    access.clear_cache()


@pytest.mark.django_db
def test_a_role_may_write_only_what_its_list_names(django_user_model, order_policy):
    warehouse = _login(django_user_model, 'wh@example.fake', 'warehouse')

    assert _not_enumerated(warehouse, 'order', {'status': 'released'}) == []
    # the field-level hole: edit was true on the model, so this used to be accepted
    assert _not_enumerated(warehouse, 'order', {'totals': {'total': 999}}) == ['totals.total']


@pytest.mark.django_db
def test_every_denied_path_is_reported_not_just_the_first(django_user_model, order_policy):
    warehouse = _login(django_user_model, 'wh2@example.fake', 'warehouse')

    denied = _not_enumerated(warehouse, 'order',
                             {'attention': 'x', 'dt_needed': 1, 'totals': {'total': 9}})

    assert denied == ['attention', 'dt_needed', 'totals.total']


@pytest.mark.django_db
def test_a_role_holding_the_full_set_writes_anything_in_it(django_user_model, order_policy):
    sales = _login(django_user_model, 'sales@example.fake', 'sales')

    assert _not_enumerated(sales, 'order', {'attention': 'x', 'totals': {'total': 9}}) == []


@pytest.mark.django_db
def test_line_fields_are_checked_under_the_lines_prefix(django_user_model, order_policy):
    """A line's permissions live on the header's block, prefixed 'lines.'."""
    customer = _login(django_user_model, 'cust@example.fake', 'customer')

    assert _not_enumerated(customer, 'order', {'quantity': {'active': 3}}, prefix='lines.') == []
    assert _not_enumerated(customer, 'order', {'price': {'unit': 1.00}},
                           prefix='lines.') == ['lines.price.unit']


@pytest.mark.django_db
def test_naming_a_record_is_not_changing_it(django_user_model, order_policy):
    warehouse = _login(django_user_model, 'wh3@example.fake', 'warehouse')

    assert _not_enumerated(warehouse, 'order',
                           {'id': 7, 'uuid': 'abc', 'version': 2, 'status': 'released'}) == []


def test_a_payload_is_flattened_to_the_leaves_the_list_speaks():
    assert _leaf_paths({'totals': {'total': 10, 'tax': 1}, 'status': 'open'}) == {
        'totals.total', 'totals.tax', 'status'}


def test_the_portal_fields_are_named_in_the_setting_not_in_a_view():
    """They were a tuple in apps/transactions/views/wcapi.py — so the one place that says
    what a role may write did not say it."""
    from apps.core.services.access import (PORTAL_ORDER_FIELDS, PORTAL_ORDER_MODELS,
                                           PORTAL_ORDER_ROLES)

    assert PORTAL_ORDER_MODELS == frozenset({'order', 'quote'})
    assert PORTAL_ORDER_ROLES == ('customer', 'buyer')     # not rep: it has its own grant
    # notes is not a field of any model, and comments is a parent path a positive list
    # may not name (Bill, 2026-09-20)
    assert 'notes' not in PORTAL_ORDER_FIELDS
    assert 'comments' not in PORTAL_ORDER_FIELDS
    assert 'totals.total' not in PORTAL_ORDER_FIELDS
