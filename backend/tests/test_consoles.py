"""The flight simulator's consoles are Settings (readme 100; Bill 2026-11-05: wire the steps in)."""
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
    assert sorted(rows) == sorted(c['id'] for c in CONSOLES)
    assert [rows[c['id']].config['sequence'] for c in CONSOLES] == list(range(1, len(CONSOLES) + 1))
    for sim_id in SCENARIOS:
        steps = rows[sim_id].config['steps']
        assert steps and all({'step', 'title', 'instruction'} <= set(s) for s in steps), sim_id
    assert rows['gl-audit'].config['steps'] == []      # no scenario yet: the description only
    call_command('seed_consoles', verbosity=0)         # a second run keeps the company's edits
    assert Setting.objects.filter(purpose='wc:console').count() == len(CONSOLES)


def test_the_shipped_set_is_what_the_console_reads(chart_of_accounts):
    _rates()
    payloads = console_settings()
    first = next(p for p in payloads if p['ida'] == 'first-customer')
    assert first['config']['first_model'] == 'contact' and first['config']['needs_item'] is False
    assert first['config']['steps'][0]['title'] == 'Create a Contact'
