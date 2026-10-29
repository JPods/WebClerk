"""Every model has its list, detail, form, panel and card, from one backend source
(apps/core/layouts; Bill, 2026-10-29). A company's layout is never overwritten: only what it
lacks is added."""
import pytest

from apps.core import layouts
from apps.core.layouts import guess


def test_every_designed_model_has_every_part():
    for key, layout in layouts.designed().items():
        missing = [p for p in layouts.PARTS if not layouts._has(layout, p)]
        assert not missing, (key, missing)


@pytest.mark.django_db
def test_a_model_not_designed_is_guessed_whole(monkeypatch):
    monkeypatch.setattr(layouts, '_designed', {})
    built = layouts.build('address')
    assert all(layouts._has(built, p) for p in layouts.PARTS)
    header = built['form']['default']['sections'][0]
    assert header['type'] == 'header' and header['columns']
    assert built['form']['default']['edit_rules'] == guess.EDIT_RULES


@pytest.mark.django_db
def test_fill_keeps_what_a_company_has():
    mine = {'list': {'default': {'columns': [{'field': 'city'}]}, 'mine': {'columns': []}},
            'form': {'default': {'sections': [{'type': 'tabs', 'tabs': []}]}}}
    filled, parts = layouts.fill('address', mine)
    assert filled['list'] == mine['list'] and 'list' not in parts
    sections = filled['form']['default']['sections']
    assert sections[0]['type'] == 'header' and sections[-1] == {'type': 'tabs', 'tabs': []}
    assert {'card', 'panel', 'detail', 'form'} <= set(parts)


def test_a_transaction_form_has_its_lines():
    form = guess.form('invoice', {'identity': {'title': 'identity', 'fields': []}})
    assert [s['type'] for s in form['sections']][:2] == ['header', 'line_card']
    assert form['family'] == 'sell'
