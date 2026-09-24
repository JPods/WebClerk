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
    from apps.core.services.door import Actor
    return Actor(user=django_user_model.objects.create_user(
        email=email, password=get_random_string(20), role=role,
        name_first='P', name_last='User'))           # access checks take an Actor


@pytest.fixture
def order_policy(db):
    """Update the order model's own Setting — purpose + parent_model is not unique, so a
    second one is read or ignored depending on which .first() returns."""
    s = Setting.objects.filter(purpose='wc:model', parent_model='order').first()
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


def test_a_collection_of_child_records_is_walked_not_offered_as_one_leaf():
    """``lines`` is a collection, not a leaf.

    The walker recursed into dicts only, so a list fell through and the bare key ``lines``
    was offered — a path no role names and none should. The screen's save was refused for
    every role. The enumeration has always spoken ``lines.item.item_id``; nothing produced
    that path from a real payload.
    """
    paths = _leaf_paths({'status': 'open',
                         'lines': [{'item': {'item_id': 5}, 'quantity': {'active': 2}}]},
                        collections=frozenset({'lines'}))

    assert paths == {'status', 'lines.item.item_id', 'lines.quantity.active'}
    assert 'lines' not in paths


def test_a_line_field_is_named_once_not_once_per_row():
    """No index: a role is granted ``lines.price.unit``, not ``lines.0.price.unit``."""
    paths = _leaf_paths({'lines': [{'price': {'unit': 1}},
                                   {'price': {'unit': 2}},
                                   {'quantity': {'active': 9}}]},
                        collections=frozenset({'lines'}))

    assert paths == {'lines.price.unit', 'lines.quantity.active'}


def test_only_a_declared_collection_is_walked():
    """Bill, 2026-09-20: *"We can narrowly define what objects can be accepted as objects."*

    ``lines`` is declared on transaction headers. Anything else a caller sends as a list of
    objects stays a leaf — named by no role, therefore refused. Undeclared fails closed.
    """
    payload = {'lines': [{'price': {'unit': 1}}],
               'widgets': [{'price': {'unit': 2}}]}

    walked = _leaf_paths(payload, collections=frozenset({'lines'}))

    assert 'lines.price.unit' in walked
    assert 'widgets' in walked              # offered whole, so no role names it
    assert 'widgets.price.unit' not in walked


def test_the_collection_declaration_is_what_the_leaf_map_builds_from():
    """One declaration, two readers — they cannot drift, because there is nothing to sync."""
    from apps.core.services import field_leaves

    declared = field_leaves.collections('order')

    assert 'lines' in declared
    child, max_rows = declared['lines']
    assert child == 'order_line'
    assert max_rows == field_leaves.COLLECTION_MAX_ROWS
    # and the leaf map carries that child's leaves under that key
    assert any(p.startswith('lines.') for p in field_leaves.model_leaves('order')['leaves'])
    # a model with no collection declares none
    assert field_leaves.collections('contact') == {}


def test_no_collection_is_named_data_or_any_other_claimed_key():
    """Bill, 2026-09-20: *"I think our collections should be named something other
    than .data."*

    ``data`` already means DRF's request body, the response envelope, a legacy nested
    payload, and a model column that became ``config``. A collection called ``data`` would
    reach save_view's legacy unwrapping and be merged into the record as fields — the rows
    silently flattened into the header. Same for ``record`` and ``options``, which the
    envelope claims first. This asserts it for every model that declares a collection, so
    the next one cannot reintroduce it.
    """
    from apps.core.services import field_leaves

    for model_key in field_leaves.TRANSACTION_HEADERS:
        for payload_key in field_leaves.collections(model_key):
            assert payload_key not in field_leaves.RESERVED_COLLECTION_KEYS, (
                f"{model_key} declares a collection named '{payload_key}', which the "
                f"request envelope claims before the walker sees it")


def test_a_collection_has_a_size_the_enumeration_cannot_give_it():
    """A positive list governs shape, never volume: a caller may name only permitted
    fields and still send a hundred thousand rows."""
    from apps.core.services import field_leaves
    from apps.transactions.views.wcapi import _collection_too_large

    cap = field_leaves.COLLECTION_MAX_ROWS

    assert _collection_too_large('order', {'lines': [{} for _ in range(cap)]}) is None
    too_many = _collection_too_large('order', {'lines': [{} for _ in range(cap + 1)]})
    assert too_many and str(cap) in too_many
    # a model that declares no collection has nothing to cap
    assert _collection_too_large('contact', {'lines': [{} for _ in range(cap + 1)]}) is None


def test_a_list_of_scalars_is_a_value_not_a_collection():
    """Only a list of records is walked. A scalar list stays a leaf, so it stays governed —
    and an empty list stays a leaf too, deliberately: nothing in it says which collection it
    meant to be, and a refusal is visible where a silent pass is not."""
    assert _leaf_paths({'tags': ['a', 'b']}) == {'tags'}
    assert _leaf_paths({'lines': []}) == {'lines'}


@pytest.mark.django_db
def test_the_screens_own_save_payload_is_enumerated_line_by_line(django_user_model, order_policy):
    """The shape ``saveTransactionWithLines`` sends, after save_view merges ``record`` up.

    This is the payload that was refused 403 for every role. The test above it passed the
    whole time because it handed a *single line dict* to ``prefix='lines.'`` — the caller
    convention, not the path production takes.
    """
    customer = _login(django_user_model, 'cust2@example.fake', 'customer')

    assert _not_enumerated(customer, 'order', {
        'id': 7, 'model_name': 'order', 'attention': 'ring the bell',
        'lines': [{'id': 1, 'quantity': {'active': 3}, '_dirty': True}],
        'options': {'verify_calculations': False, 'save_only_dirty': False},
    }) == []


@pytest.mark.django_db
def test_a_line_field_outside_the_list_is_still_refused(django_user_model, order_policy):
    """Walking the collection must not become a grant of the whole collection."""
    customer = _login(django_user_model, 'cust3@example.fake', 'customer')

    assert _not_enumerated(customer, 'order', {
        'lines': [{'quantity': {'active': 3}}, {'price': {'unit': 1.00}}],
    }) == ['lines.price.unit']


@pytest.mark.django_db
def test_the_request_envelope_is_not_a_field(django_user_model, order_policy):
    """``options`` names the request and ``_dirty`` is the screen's own bookkeeping.
    Neither is a field of any record, so a positive list may not name them."""
    warehouse = _login(django_user_model, 'wh4@example.fake', 'warehouse')

    assert _not_enumerated(warehouse, 'order', {
        'status': 'released',
        'options': {'verify_calculations': True, 'save_only_dirty': True},
        'lines': [{'_dirty': True}],
    }) == []


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
