"""Defaults live in each model's own wc:model Setting, seen together in the defaults console
(readme 106 A; Bill, 2026-11-07). core/services/defaults.py: model_defaults is the one reader,
checked_defaults the one gate (Setting.save), shipped_defaults what a fresh installation and the
migration start with, migrate_definition the transform the migration and the bundles got."""
import pytest
from django.core.exceptions import ValidationError

from apps.core.consoles import console_settings
from apps.core.services import definition, select_lists
from apps.core.services.defaults import (FORMATTING_KEYS, SHIPPED_FIELDS, SHIPPED_FORMATTING, checked_defaults,
                                         defaults_schema, migrate_definition, model_defaults, model_formatting,
                                         shipped_defaults)
from apps.core.services.door import Actor
from tests.conftest import make_setting

pytestmark = pytest.mark.django_db


def _definition(model_key, defaults):
    """The model's definition with this defaults block: made, or the one the fixtures seeded."""
    from apps.core.models import Setting
    setting = Setting.objects.filter(purpose='wc:model', parent_model=model_key).first()
    if setting is None:
        return make_setting(purpose='wc:model', parent_model=model_key, name=model_key, config={'defaults': defaults})
    setting.config = {**(setting.config or {}), 'defaults': defaults}
    setting._setting_create_authorized = True
    setting.save()
    return setting


def test_the_reader_reads_the_models_own_definition(chart_of_accounts):
    from apps.accounts.models import Term
    Term.objects.get_or_create(ida='N10', defaults={'name': 'N10', 'is_active': True})
    _definition('quote', {'fields': {'terms': 'N10', 'priority': '', 'dt_needed_days': 7}})
    definition.clear()
    assert model_defaults('quote') == {'terms': 'N10', 'dt_needed_days': 7}, 'blanks left out'
    assert model_formatting('quote') == SHIPPED_FORMATTING, 'the shipped formatting where none is stored'
    assert model_defaults('workorder') == {}, 'a model with no definition, or no block, has no defaults'


def test_a_default_naming_a_field_the_model_lacks_is_refused(chart_of_accounts):
    with pytest.raises(ValidationError, match='fields'):
        _definition('quote', {'fields': {'colour': 'blue'}})
    with pytest.raises(ValidationError, match='fields'):
        _definition('customer', {'fields': {'dt_needed_days': 3}})      # a customer has no dt_needed


def test_only_the_two_blocks_and_the_four_formatting_keys(chart_of_accounts):
    with pytest.raises(ValidationError, match='nothing else'):
        _definition('quote', {'terms': 'N30'})                           # the pre-106 flat shape
    with pytest.raises(ValidationError, match='formatting takes'):
        _definition('quote', {'fields': {}, 'formatting': {'timezone': 'UTC'}})
    s = _definition('quote', {'fields': {}, 'formatting': {'currency': 'EUR'}})
    assert s.config['defaults']['formatting'] == {**SHIPPED_FORMATTING, 'currency': 'EUR'}


def test_a_listed_value_is_stored_in_the_lists_spelling_and_an_unlisted_one_refused(chart_of_accounts, django_user_model):
    admin = django_user_model.objects.create_superuser(email='d@example.com', password=None, name_first='D', name_last='D', username='')
    s = _definition('quote', {'fields': {}})
    select_lists.replace_list('quote', 'priority', [{'value': 'low'}, {'value': 'medium'}], actor=Actor(user=admin, kind='user', source='wcapi'))
    s.refresh_from_db()
    s.config = {**s.config, 'defaults': {'fields': {'priority': 'Medium'}}}
    s._setting_create_authorized = True
    s.save()
    assert s.config['defaults']['fields']['priority'] == 'medium'
    s.config = {**s.config, 'defaults': {'fields': {'priority': 'urgent'}}}
    with pytest.raises(ValidationError, match='not on its list'):
        s.save()


def test_every_shipped_block_passes_its_own_gate(chart_of_accounts):
    """Completeness is visible block by block: what we ship must be what the gate admits."""
    from apps.accounts.models import Term
    Term.objects.get_or_create(ida='N30', defaults={'name': 'N30', 'is_active': True})
    for model_key in SHIPPED_FIELDS:
        block = checked_defaults(model_key, shipped_defaults(model_key))
        assert block['fields'] == SHIPPED_FIELDS[model_key], model_key
        assert set(block['formatting']) == set(FORMATTING_KEYS)
        assert defaults_schema(model_key) is not None, f'{model_key} has a <Model>SettingDefaults schema'


def test_the_migration_transform_carries_the_company_values_and_folds_formatting():
    company = {'terms': 'N10', 'order_new': {'days': 21, 'priority': 'high'}}
    legacy = {'behaviors': {'terms': {'type': 'lookup'}}, 'defaults': {}, 'formatting': {'currency': 'CAD', 'locale': 'en-CA'}}
    out = migrate_definition('order', legacy, company)
    assert out['defaults'] == {'fields': {'terms': 'N10', 'price_level': 'retail', 'dt_needed_days': 21, 'priority': 'high'},
                               'formatting': {**SHIPPED_FORMATTING, 'currency': 'CAD', 'locale': 'en-CA'}}
    assert 'formatting' not in out and out['behaviors'] == legacy['behaviors']
    assert migrate_definition('customer', {'defaults': {}}, company)['defaults']['fields'] == {'terms': 'N10', 'price_level': 'retail'}
    assert migrate_definition('contact', {}, company)['defaults'] == {'fields': {}, 'formatting': SHIPPED_FORMATTING}
    again = migrate_definition('order', out, None)
    assert again == out, 'the new shape is left as it is'


def test_the_defaults_console_lists_the_models_and_the_shared_fields():
    console = next(c for c in console_settings() if c['ida'] == 'defaults')
    assert console['config']['kind'] == 'defaults'
    assert set(SHIPPED_FIELDS) <= set(console['config']['models'])
    assert console['config']['shared'] == ['terms', 'price_level', 'dt_needed_days', 'priority', 'source_name']
    assert all(c['config'].get('kind') == 'sim' for c in console_settings() if c['ida'] != 'defaults')
