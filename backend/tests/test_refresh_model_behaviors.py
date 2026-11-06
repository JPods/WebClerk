"""An integer pointer is a lookup, and the stored definitions carry what the code computes
(Bill, 2026-11-05: "the vast majority of user input fields should have a selectlist"). The
form reads the stored behaviors, never the code: a rule the code learns reaches no form until
refresh_model_behaviors writes it, and the shipped bundles must carry it or a fresh install
draws numbers where names belong."""
import json
from pathlib import Path

import pytest

from apps.core.management.commands.refresh_model_behaviors import refreshed
from apps.core.services.field_behaviors import get_field_behaviors


def _typed(beh):
    return {k: v for k, v in beh.items() if k != 'label'}

ROOT = Path(__file__).resolve().parent.parent


def test_an_integer_pointer_is_a_lookup_on_the_model_its_stem_names():
    line = {k: _typed(v) for k, v in get_field_behaviors('order_line').items()}
    assert line['rep_id'] == {'type': 'lookup', 'model': 'rep', 'display': 'company'}
    assert line['customer_id'] == {'type': 'lookup', 'model': 'customer', 'display': 'company'}
    assert line['assigned_to_id'] == {'type': 'lookup', 'model': 'contact', 'display': 'attention'}
    assert line['parent_line_id'] == {'type': 'number'}          # no model named parent_line
    assert _typed(get_field_behaviors('cash')['contact_id']) == {'type': 'lookup', 'model': 'contact', 'display': 'attention'}
    assert _typed(get_field_behaviors('item_xref')['item_ida']) == {'type': 'lookup', 'model': 'item', 'value': 'ida'}


def test_refresh_adds_what_is_missing_and_upgrades_a_number_to_its_lookup_only():
    config = {'behaviors': {'rep_id': {'type': 'number', 'label': 'Rep'},
                            'description': {'type': 'textarea', 'label': 'My words'}}}
    out, changes = refreshed('order_line', config)
    assert out['behaviors']['rep_id'] == {'type': 'lookup', 'model': 'rep', 'display': 'company', 'label': 'Rep'}
    assert out['behaviors']['description'] == {'type': 'textarea', 'label': 'My words'}   # a staff edit stays
    assert 'customer_id' in changes and 'item_fk' in out['behaviors']
    assert refreshed('order_line', out) == (out, [])                                       # idempotent


def test_a_stored_lookup_learns_the_keys_the_code_added():
    config = {'behaviors': {'terms': {'type': 'lookup', 'model': 'term', 'display': 'ida', 'value': 'ida', 'label': 'Terms'}}}
    out, changes = refreshed('order', config)
    assert 'terms' in changes and out['behaviors']['terms']['pick'] == 'list' and out['behaviors']['terms']['label'] == 'Terms'


@pytest.mark.parametrize('bundle', ['settings-bundle.json', 'init-bundle.json', 'demo-bundle.json'])
def test_the_shipped_definitions_carry_every_behavior_the_code_computes(bundle):
    data = json.loads((ROOT / bundle).read_text())
    stale = {}
    for item in data['settings']:
        if item.get('purpose') == 'wc:model' and isinstance(item.get('config'), dict):
            _config, changes = refreshed(item['parent_model'], item['config'])
            if changes:
                stale[item['parent_model']] = changes
    assert stale == {}, 'run: manage.py refresh_model_behaviors --bundles'
