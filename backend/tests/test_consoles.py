"""The flight simulator's consoles are Settings (readme 100; Bill 2026-11-05: wire the steps in),
and so is the defaults console (readme 106; kind 'defaults', beside the simulations)."""
import pytest
from django.core.management import call_command

from apps.core.consoles import CONSOLES, SCENARIOS, console_settings
from apps.core.models import Setting

pytestmark = pytest.mark.django_db


def _rates():
    """The inventory and cash scripts read the company's tax jurisdiction and carrier."""
    call_command('seed_shipping_service', verbosity=0)
    call_command('seed_tax_jurisdictions', verbosity=0)


def test_every_console_seeds_once_with_its_steps(chart_of_accounts):
    _rates()
    call_command('seed_consoles', verbosity=0)
    rows = {s.ida: s for s in Setting.objects.filter(purpose='wc:console')}
    assert sorted(rows) == sorted([c['id'] for c in CONSOLES] + ['defaults'])
    assert [rows[c['id']].config['sequence'] for c in CONSOLES] == list(range(1, len(CONSOLES) + 1))
    assert rows['defaults'].config['kind'] == 'defaults' and 'steps' not in rows['defaults'].config
    assert all(rows[c['id']].config['kind'] == 'sim' for c in CONSOLES)
    for sim_id in SCENARIOS:
        steps = rows[sim_id].config['steps']
        assert steps and all({'step', 'title', 'instruction'} <= set(s) for s in steps), sim_id
    assert rows['gl-audit'].config['steps'] == []      # no scenario yet: the description only
    call_command('seed_consoles', verbosity=0)         # a second run keeps the company's edits
    assert Setting.objects.filter(purpose='wc:console').count() == len(CONSOLES) + 1


def test_the_shipped_set_is_what_the_console_reads(chart_of_accounts):
    _rates()
    payloads = console_settings()
    first = next(p for p in payloads if p['ida'] == 'first-customer')
    assert first['config']['first_model'] == 'contact' and first['config']['needs_item'] is False
    assert first['config']['steps'][0]['title'] == 'Create a Contact'


def test_the_defaults_walk_sits_between_first_sale_and_inventory():
    """Bill, 2026-11-08: the d30338b walk is a lesson in the new-user sequence — after first-sale,
    before inventory; its ida is not 'defaults' (the defaults console's)."""
    ids = [c['id'] for c in CONSOLES]
    assert ids.index('first-sale') + 1 == ids.index('defaults-walk') == ids.index('inventory') - 1
    assert 'defaults' not in ids
    assert SCENARIOS['first-sale']()['next_sim'] == 'defaults-walk'
    walk = SCENARIOS['defaults-walk']()
    assert walk['prerequisite'] == 'first-sale' and walk['next_sim'] == 'inventory'
    assert [s['step'] for s in walk['steps']] == list(range(1, 8))
    assert [s['model'] for s in walk['steps']] == ['customer', 'quote', 'quote', 'invoice', 'purchase', 'setting', 'invoice']
    assert walk['steps'][2]['expected_fields']['price_level'] == 'wholesale'
    assert 'never automatic' in walk['steps'][6]['explanation']
    assert walk['steps'][6]['exit_point']['name']
    labels = [c['label'] for c in CONSOLES]
    assert labels[ids.index('defaults-walk')].startswith('4. ') and labels[ids.index('inventory')].startswith('5. ')
