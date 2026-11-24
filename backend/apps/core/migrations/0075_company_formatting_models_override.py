"""Formatting has a company default, and a model stores only what it overrides (Bill, 2026-11-24:
"we should have a company default with an override by model.field or model.leaf").

Until now every model definition stored all four formatting keys, so there was no level above
it to inherit from. This gives the company profile ``config.defaults.formatting`` (the shipped
block where it has none) and removes from each model definition the keys that equal the
company's: those were seeded, not chosen. A key a model set to something else stays as that
model's override. A model that chose the shipped value on purpose cannot be told from a seeded
one; it now follows the company.
"""
from django.db import migrations

SHIPPED_FORMATTING = {'currency': 'USD', 'locale': 'en-US', 'date_format': 'short', 'number_precision': 2}


def company_block(config):
    """The company profile's config with its formatting block in place; (config, formatting)."""
    config = dict(config) if isinstance(config, dict) else {}
    defaults = config.get('defaults') if isinstance(config.get('defaults'), dict) else {}
    own = defaults.get('formatting') if isinstance(defaults.get('formatting'), dict) else {}
    formatting = {**SHIPPED_FORMATTING, **{k: v for k, v in own.items() if k in SHIPPED_FORMATTING and v not in (None, '')}}
    config['defaults'] = {'formatting': formatting}
    return config, formatting


def model_overrides(config, company):
    """A model definition's config, its formatting cut to what differs from the company's."""
    if not isinstance(config, dict) or not isinstance(config.get('defaults'), dict):
        return config
    block = config['defaults'].get('formatting')
    if not isinstance(block, dict):
        return config
    kept = {k: v for k, v in block.items() if k in SHIPPED_FORMATTING and v not in (None, '') and v != company.get(k)}
    return {**config, 'defaults': {**config['defaults'], 'formatting': kept}}


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    company = Setting.objects.filter(purpose='wc:company_profile').order_by('id').first()
    formatting = dict(SHIPPED_FORMATTING)
    if company:
        config, formatting = company_block(company.config)
        Setting.objects.filter(pk=company.pk).update(config=config)
    for s in Setting.objects.filter(purpose='wc:model'):
        config = model_overrides(s.config, formatting)
        if config != s.config:
            Setting.objects.filter(pk=s.pk).update(config=config)


class Migration(migrations.Migration):
    dependencies = [('core', '0074_inquiry_forms_drop_tester_exemption')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
