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
    assert roles_filled_by('quote', 'company') == () and roles_filled_by('receipt', 'vendor') == ()
