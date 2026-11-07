"""Defaults live in each model's own wc:model Setting (Bill, 2026-11-07; readme 106 A):
``config.defaults`` = {fields, formatting}. The company profile's ``defaults`` (terms,
order_new) move out: every document's block carries what the profile gave it, orgs and the
rest take the shipped blocks; the old ``config.formatting`` section folds into
``defaults.formatting`` and is gone (one home, nested so a field cannot collide with a
formatting key). And source_name on every org definition: the contact's list, the form's
contact column (readme 106 B).

Frozen: everything this migration needs is a literal here (the lead's rule, as 0025 — a
migration never imports live service code, so a fresh install runs what wc_demo ran). The
bundles were given the same transform on 2026-11-07.
"""
from django.db import migrations

SELL = ('quote', 'order', 'invoice')
BUY = ('purchase', 'receipt')
FORMATTING_KEYS = ('currency', 'locale', 'date_format', 'number_precision')
SHIPPED_FORMATTING = {'currency': 'USD', 'locale': 'en-US', 'date_format': 'short', 'number_precision': 2}
SHIPPED_FIELDS = {
    **{m: {'terms': 'N30', 'price_level': 'retail', 'dt_needed_days': 14, 'priority': 'medium'} for m in SELL + BUY},
    'workorder': {'dt_needed_days': 14, 'priority': 'medium'},
    'customer': {'terms': 'N30', 'price_level': 'retail'},
    'vendor': {'terms': 'N30'},
    'manufacturer': {'terms': 'N30'},
}
SOURCE_NAMES = [('direct', 'Direct'), ('referral', 'Referral'), ('social_media', 'Social Media'),
                ('website', 'Website'), ('trade_show', 'Trade Show'), ('cold_call', 'Cold Call'),
                ('email_campaign', 'Email Campaign'), ('repeat', 'Repeat Customer'),
                ('partner', 'Partner'), ('other', 'Other')]
ORGS = ('customer', 'vendor', 'manufacturer', 'rep', 'employee', 'other_org')


def fields_from_company(model_key, company_defaults):
    """The pre-106 company profile's {terms, order_new: {days, priority}} as this model's block."""
    shipped = dict(SHIPPED_FIELDS.get(model_key, {}))
    if not isinstance(company_defaults, dict) or not company_defaults:
        return shipped
    terms = company_defaults.get('terms')
    order_new = company_defaults.get('order_new') if isinstance(company_defaults.get('order_new'), dict) else {}
    carried = {'terms': terms, 'dt_needed_days': order_new.get('days'), 'priority': order_new.get('priority')}
    return {k: (carried[k] if k in carried and carried[k] not in (None, '') else v) for k, v in shipped.items()}


def migrate_definition(model_key, config, company_defaults):
    """A definition's config in the new shape: ``defaults`` = {fields, formatting}, the old
    ``formatting`` section folded in and gone. The fields are what the company profile gave
    every document before, else the shipped ones; the new shape is left as it is."""
    config = dict(config or {})
    old = config.get('defaults')
    if isinstance(old, dict) and set(old) <= {'fields', 'formatting'} and ('fields' in old or 'formatting' in old):
        fields = dict(old.get('fields') or {})
        formatting = dict(old.get('formatting') or {})
    else:
        fields = {k: v for k, v in (old or {}).items() if v not in (None, '')} if isinstance(old, dict) else {}
        fields = fields or fields_from_company(model_key, company_defaults)
        formatting = {}
    legacy = config.pop('formatting', None)
    if isinstance(legacy, dict):
        formatting = {**legacy, **formatting}
    config['defaults'] = {'fields': fields,
                          'formatting': {**SHIPPED_FORMATTING, **{k: v for k, v in formatting.items() if k in FORMATTING_KEYS}}}
    return config


def org_definition_with_source_name(config, contact_list=None):
    """The org definition's config with source_name: the list (the contact's where it exists),
    a select behavior, and the field in the form's contact column (the one holding email)."""
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
