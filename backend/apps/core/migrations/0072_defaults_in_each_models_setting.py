"""Defaults live in each model's own wc:model Setting (Bill, 2026-11-07; readme 106 A):
``config.defaults`` = {fields, formatting}. The company profile's ``defaults`` (terms,
order_new) move out: every document's block carries what the profile gave it, orgs and the
rest take the shipped blocks; the old ``config.formatting`` section folds into
``defaults.formatting`` and is gone (one home, nested so a field cannot collide with a
formatting key). And source_name on every org definition: the contact's list, the form's
contact column (readme 106 B). The transform is core/services/defaults.migrate_definition,
the same the bundles were given.
"""
from django.db import migrations

ORGS = ('customer', 'vendor', 'manufacturer', 'rep', 'employee', 'other_org')


def org_definition_with_source_name(config, contact_list=None):
    """The org definition's config with source_name: the list (the contact's where it exists),
    a select behavior, and the field in the form's contact column (the one holding email)."""
    from apps.core.services.select_lists import SOURCE_NAMES
    config = dict(config or {})
    lists = dict(config.get('selectlists') or {})
    if not lists.get('source_name'):
        lists['source_name'] = list(contact_list) if contact_list else [{'value': v, 'label': l} for v, l in SOURCE_NAMES]
    config['selectlists'] = lists
    behaviors = dict(config.get('behaviors') or {})
    behaviors.setdefault('source_name', {'type': 'select', 'label': 'source_name'})
    config['behaviors'] = behaviors
    layout = config.get('layout')
    form = (layout or {}).get('form') if isinstance(layout, dict) else None
    default = form.get('default') if isinstance(form, dict) else None
    for section in (default or {}).get('sections') or []:
        if section.get('type') != 'header':
            continue
        for column in section.get('columns') or []:
            names = [f.get('field') if isinstance(f, dict) else f for f in column.get('fields') or []]
            if 'email' in names and 'source_name' not in names:
                column['fields'] = list(column.get('fields') or []) + [{'field': 'source_name', 'label': 'source_name'}]
                break
        break
    return config


def forward(apps, schema_editor):
    from apps.core.services.defaults import migrate_definition
    Setting = apps.get_model('core', 'Setting')
    company = Setting.objects.filter(purpose='wc:company_profile').first()
    company_defaults = (company.config or {}).get('defaults') if company and isinstance(company.config, dict) else None
    contact = Setting.objects.filter(purpose='wc:model', parent_model='contact').first()
    contact_list = ((contact.config or {}).get('selectlists') or {}).get('source_name') if contact else None
    for s in Setting.objects.filter(purpose='wc:model'):
        if not isinstance(s.config, dict):
            continue
        config = migrate_definition(s.parent_model or '', s.config, company_defaults)
        if s.parent_model in ORGS:
            config = org_definition_with_source_name(config, contact_list)
        if config != s.config:
            Setting.objects.filter(pk=s.pk).update(config=config)
    if company and isinstance(company.config, dict) and 'defaults' in company.config:
        Setting.objects.filter(pk=company.pk).update(config={k: v for k, v in company.config.items() if k != 'defaults'})


class Migration(migrations.Migration):
    dependencies = [('core', '0071_cash_card_counts_money_only'), ('orgs', '0013_source_name_on_every_org')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
