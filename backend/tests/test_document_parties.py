"""The party blocks a document carries are declared once (common/schemas/aspects.DOCUMENT_PARTIES)
and everything else follows that table. On 2026-11-12 a purchase's vendor block reached the
form blank because the schema, the stored access set, the layout and the party fill each kept
their own list and one was missed. These tests are the check that they cannot drift again."""
import json
import pathlib
import re

import pytest
from django.conf import settings

from apps.core.services import field_leaves as fl
from common.schemas.aspects import ASPECT_ENTRIES, DOCUMENT_PARTIES, party_roles, roles_filled_by

BACKEND = pathlib.Path(settings.BASE_DIR)
PARTY_PATH = re.compile(r'^(addresses|emails|phones)\.([a-z_]+)\.')


def _party_paths(node):
    """Every 'addresses.<role>.x' style path named anywhere in a layout."""
    if isinstance(node, dict):
        for value in node.values():
            yield from _party_paths(value)
    elif isinstance(node, list):
        for value in node:
            yield from _party_paths(value)
    elif isinstance(node, str) and PARTY_PATH.match(node):
        yield node


@pytest.mark.parametrize('model_key', sorted(DOCUMENT_PARTIES))
def test_the_schema_names_exactly_the_tables_blocks(model_key):
    leaves = fl.model_leaves(model_key)['leaves']
    for aspect in ASPECT_ENTRIES:
        named = {leaf.split('.')[1] for leaf in leaves if leaf.startswith(f'{aspect}.')}
        assert named == set(party_roles(model_key)), f'{model_key}.{aspect}'


@pytest.mark.parametrize('model_key', sorted(DOCUMENT_PARTIES))
def test_the_shipped_layout_names_only_the_tables_blocks(model_key):
    layouts = json.loads((BACKEND / 'apps/core/layouts/layouts.json').read_text())
    roles = set(party_roles(model_key))
    strays = sorted({p for p in _party_paths(layouts.get(model_key, {})) if PARTY_PATH.match(p).group(2) not in roles})
    assert not strays, f'{model_key} layout names blocks the document does not carry: {strays}'


@pytest.mark.parametrize('bundle', ['init-bundle.json', 'settings-bundle.json', 'demo-bundle.json'])
def test_a_shipped_access_set_holds_every_blocks_leaves(bundle):
    """A role granted '@all' reads the stored set: a block's leaf missing from it is projected
    out on read and refused on write."""
    data = json.loads((BACKEND / bundle).read_text())
    checked = 0
    for setting in data.get('settings') or []:
        key = str(setting.get('parent_model') or '').lower()
        stored = (((setting.get('config') or {}).get('access') or {}).get('sets') or {}).get('all')
        if setting.get('purpose') != 'wc:model' or key not in DOCUMENT_PARTIES or not isinstance(stored, list):
            continue
        wanted = {leaf for leaf in fl.model_leaves(key)['leaves'] if leaf.split('.')[0] in ASPECT_ENTRIES}
        missing = sorted(wanted - set(stored))
        assert not missing, f'{bundle} {key}: the all set lacks {missing}'
        checked += 1
    if bundle != 'demo-bundle.json':
        assert checked, f'{bundle}: no document definition with an all set was checked'


def test_who_fills_what():
    assert roles_filled_by('purchase', 'vendor') == ('vendor',)
    assert roles_filled_by('purchase', 'company') == ('bill_to', 'ship_to')
    assert roles_filled_by('quote', 'customer') == ('bill_to', 'ship_to')
    assert roles_filled_by('quote', 'company') == () and roles_filled_by('receipt', 'vendor') == ('vendor',)


# ── readme 109 P4: one home for the counterparty's contact details ──────────────

@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_superuser(
        email='parties@example.com', password=None, name_first='Par', name_last='Ties', username='')


def _saved(admin, model_key, cls, **fields):
    from apps.core.services.door import Actor
    from apps.core.services.new import new_record
    from apps.core.services.save import save_record
    actor = Actor(user=admin, kind='user', source='wcapi')
    doc = cls.objects.get(pk=new_record(actor, model_key, {}).obj_id)
    save_record(actor, {'id': doc.pk, 'version': doc.version, **fields}, model_key=model_key)
    doc.refresh_from_db()
    return doc


def test_company_is_identity_and_the_details_come_from_the_block(admin, model_defaults):
    from apps.orgs.models import Customer, Vendor
    from apps.transactions.models import Purchase, Quote
    block = {'contact_id': None, 'company': 'Parts Inc', 'attention': 'Sal',
             'full_address': '9 Mill St, Denver, CO 80201', 'instructions': ''}
    seller = Vendor.objects.create(company='Parts Inc', addresses={'bill_to': block},
                                   phones={'bill_to': {'number': '303-555-0100'}},
                                   emails={'bill_to': {'email': 'ap@parts.test'}})
    po = _saved(admin, 'purchase', Purchase, vendor_id=seller.pk)
    assert set(po.company) == {'id', 'ida', 'name', 'is_individual'} and po.company['name'] == 'Parts Inc'
    assert (po.address_full, po.phone, po.email) == ('9 Mill St, Denver, CO 80201', '303-555-0100', 'ap@parts.test')

    buyer = Customer.objects.create(company='Acme Corp', addresses={'bill_to': {**block, 'company': 'Acme Corp',
                                                                                'full_address': '1 Main St'}})
    q = _saved(admin, 'quote', Quote, customer_id=buyer.pk)
    assert set(q.company) == {'id', 'ida', 'name', 'is_individual'} and q.company['name'] == 'Acme Corp'
    assert q.address_full == '1 Main St'


def test_the_counterparty_of_a_purchase_is_its_vendor_even_with_a_customer(admin, model_defaults):
    """A drop shipment carries both; the purchase's company is who we buy from."""
    from apps.orgs.models import Customer, Vendor
    from apps.transactions.models import Purchase
    seller = Vendor.objects.create(company='Parts Inc')
    buyer = Customer.objects.create(company='Acme Corp')
    po = _saved(admin, 'purchase', Purchase, vendor_id=seller.pk, customer_id=buyer.pk)
    assert po.company['name'] == 'Parts Inc'


def test_the_migration_keeps_every_detail_and_moves_every_path():
    import importlib
    from types import SimpleNamespace
    m = importlib.import_module('apps.transactions.migrations.0056_counterparty_details_in_the_party_block')
    old = SimpleNamespace(company={'id': 7, 'ida': '7', 'name': 'Parts Inc', 'contact_id': 3, 'attention': 'Sal',
                                   'full_address': '9 Mill St', 'phone': '303', 'email': 'a@b.test',
                                   'domain': 'b.test', 'is_individual': False},
                          addresses={}, emails={}, phones={})
    moved = m.moved_document(old, 'vendor')
    assert moved['company'] == {'id': 7, 'ida': '7', 'name': 'Parts Inc', 'is_individual': False}
    assert moved['addresses']['vendor'] == {'contact_id': 3, 'company': 'Parts Inc', 'attention': 'Sal',
                                            'full_address': '9 Mill St', 'instructions': ''}
    assert moved['emails'] == {'vendor': {'email': 'a@b.test'}} and moved['phones'] == {'vendor': {'number': '303'}}
    done = SimpleNamespace(**{**vars(old), **moved})
    assert m.moved_document(done, 'vendor') == {}, 'done once'
    # a block someone already filled is the truth: it is not overwritten
    kept = SimpleNamespace(company=dict(old.company), addresses={'vendor': {'company': 'Typed', 'full_address': 'X'}},
                           emails={}, phones={})
    assert 'addresses' not in m.moved_document(kept, 'vendor')

    layout = {'list': [{'field': 'company.name'}, {'field': 'company.email'}, {'field': 'company.domain'}]}
    assert m.moved_layout(layout, 'bill_to') == {'list': [{'field': 'company.name'}, {'field': 'emails.bill_to.email'}]}
    access = m.moved_access({'sets': {'all': ['company.name', 'company.phone', 'phones.bill_to.number']},
                             'roles': {'rep': {'view': ['company.full_address'], 'edit': []}}}, 'bill_to')
    assert access['sets']['all'] == ['company.name', 'phones.bill_to.number']
    assert access['roles']['rep']['view'] == ['addresses.bill_to.full_address']


@pytest.mark.parametrize('bundle', ['init-bundle.json', 'settings-bundle.json'])
def test_no_shipped_definition_names_a_company_detail(bundle):
    data = json.loads((BACKEND / bundle).read_text())
    for setting in data.get('settings') or []:
        key = str(setting.get('parent_model') or '').lower()
        if setting.get('purpose') == 'wc:model' and key in DOCUMENT_PARTIES:
            text = json.dumps({'layout': setting['config'].get('layout'), 'access': setting['config'].get('access')})
            for detail in ('attention', 'full_address', 'phone', 'email', 'contact_id', 'domain'):
                assert f'"company.{detail}"' not in text, f'{bundle} {key}: company.{detail}'


def test_the_receipt_form_names_no_purchase_or_ship_to_field():
    """Bill, 2026-11-12: a receipt has no ship-to, and the server sends it no ``purchase`` object."""
    layouts = json.loads((BACKEND / 'apps/core/layouts/layouts.json').read_text())
    text = json.dumps(layouts['receipt'])
    assert '"purchase.' not in text and 'config.ship_to' not in text
