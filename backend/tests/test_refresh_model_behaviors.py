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
    assert _typed(get_field_behaviors('serial')['serial_ida']) == {'type': 'text'}   # its own number, not a pointer


def test_refresh_adds_what_is_missing_and_upgrades_a_number_to_its_lookup_only():
    config = {'behaviors': {'rep_id': {'type': 'number', 'label': 'Rep'},
                            'description': {'type': 'textarea', 'label': 'My words'}}}
    out, changes, kept = refreshed('order_line', config)
    assert out['behaviors']['rep_id'] == {'type': 'lookup', 'model': 'rep', 'display': 'company', 'label': 'Rep'}
    assert out['behaviors']['description'] == {'type': 'textarea', 'label': 'My words'}   # a staff edit stays
    assert 'customer_id' in changes and 'item_fk' in out['behaviors'] and kept == []
    assert refreshed('order_line', out) == (out, [], [])                                   # idempotent
    xref, _c, _k = refreshed('item_xref', {'behaviors': {'item_ida': {'type': 'text', 'label': 'Item'}}})
    assert xref['behaviors']['item_ida'] == {'type': 'lookup', 'model': 'item', 'value': 'ida', 'label': 'Item'}   # the old text default of an _ida


def test_an_entry_a_person_changed_is_reported_and_left_alone():
    """The lead's rule (2026-11-05): additive never overwrites what a person changed. A stored
    number with a key the code never gave it, or a lookup pointed elsewhere, is theirs."""
    config = {'behaviors': {'rep_id': {'type': 'number', 'help': 'the rep who gets the commission'},
                            'customer_id': {'type': 'lookup', 'model': 'contact'}}}
    out, changes, kept = refreshed('order_line', config)
    assert sorted(kept) == ['customer_id', 'rep_id']
    assert out['behaviors']['rep_id'] == config['behaviors']['rep_id']
    assert out['behaviors']['customer_id'] == config['behaviors']['customer_id']
    assert 'rep_id' not in changes and 'customer_id' not in changes


def test_a_stored_lookup_learns_the_keys_the_code_added():
    config = {'behaviors': {'terms': {'type': 'lookup', 'model': 'term', 'display': 'ida', 'value': 'ida', 'label': 'Terms'}}}
    out, changes, _kept = refreshed('order', config)
    assert 'terms' in changes and out['behaviors']['terms']['pick'] == 'list' and out['behaviors']['terms']['label'] == 'Terms'


@pytest.mark.parametrize('bundle', ['settings-bundle.json', 'init-bundle.json', 'demo-bundle.json'])
def test_the_shipped_definitions_carry_every_behavior_the_code_computes(bundle):
    data = json.loads((ROOT / bundle).read_text())
    stale = {}
    for item in data['settings']:
        if item.get('purpose') == 'wc:model' and isinstance(item.get('config'), dict):
            _config, changes, _kept = refreshed(item['parent_model'], item['config'])
            if changes:
                stale[item['parent_model']] = changes
    assert stale == {}, 'run: manage.py refresh_model_behaviors --bundles'


def test_a_lookup_on_no_registered_model_is_repointed():
    """ai_message's FKs were stored as lookups on 'aimessage' (a key no registry has): a
    search that could never find. Nobody meant that, so it is the code's to fix."""
    out, changes, kept = refreshed('ai_message', {'behaviors': {'parent': {'type': 'lookup', 'model': 'aimessage', 'display': 'ida', 'label': 'parent'}}})
    assert 'parent' in changes and kept == []
    assert out['behaviors']['parent']['model'] == 'ai_message' and out['behaviors']['parent']['label'] == 'parent'


def test_an_org_pointer_stored_on_customer_is_the_old_default_and_follows_its_role():
    out, changes, kept = refreshed('item', {'behaviors': {'vendor': {'type': 'lookup', 'model': 'customer', 'display': 'display_name', 'label': 'vendor'}}})
    assert 'vendor' in changes and kept == [] and out['behaviors']['vendor']['model'] == 'vendor'
