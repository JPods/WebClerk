"""The switch for line contacts (Bill, 2026-11-12: "a default to turn this line/serial contact
on and off"): each sell document's definition gains ``config.defaults.features.line_contacts``,
off, where it has none. A staff member turns it on in the Defaults console.

Frozen: the models and the switch are literals here (core/services/defaults.py FEATURES).
"""
from django.db import migrations

MODELS = ('quote', 'order', 'invoice')
SWITCH = 'line_contacts'


def with_switch(config):
    """The definition's config with the switch, off, when its defaults name none."""
    config = dict(config or {})
    defaults = dict(config.get('defaults') or {})
    features = dict(defaults.get('features') or {})
    if SWITCH in features:
        return config
    features[SWITCH] = False
    defaults['features'] = features
    config['defaults'] = defaults
    return config


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model'):
        if (s.parent_model or '').lower() not in MODELS or not isinstance(s.config, dict):
            continue
        config = with_switch(s.config)
        if config != s.config:
            Setting.objects.filter(pk=s.pk).update(config=config)
    from apps.core.services import definition
    for key in MODELS:
        definition.clear(key)


class Migration(migrations.Migration):
    dependencies = [('transactions', '0059_line_contacts')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
