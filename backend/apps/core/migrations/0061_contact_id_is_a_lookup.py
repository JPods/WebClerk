"""A contact pointer held as a plain integer shows as a contact, not a number (2026-11-05).

Cash.contact_id (and any model whose contact_id is an integer column, not a ForeignKey) read
{'type': 'number'} in its stored behaviors; the form showed the id. It is a lookup on contact,
as field_behaviors now computes it (the lead's review of 6510d7f).
"""
from django.apps import apps as dj_apps
from django.db import migrations

INTS = ('IntegerField', 'BigIntegerField', 'PositiveIntegerField')


def forward(apps, schema_editor):
    from apps.core.constants.model_registry import get_model_meta
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model'):
        meta = get_model_meta(s.parent_model)
        if not meta or not isinstance(s.config, dict):
            continue
        try:
            field = meta.import_model()._meta.get_field('contact_id')
        except Exception:
            continue
        if field.__class__.__name__ not in INTS:
            continue
        behaviors = dict(s.config.get('behaviors') or {})
        want = {**(behaviors.get('contact_id') or {}), 'type': 'lookup', 'model': 'contact', 'display': 'attention'}
        want.pop('options', None)
        if behaviors.get('contact_id') != want:
            behaviors['contact_id'] = want
            Setting.objects.filter(pk=s.pk).update(config={**s.config, 'behaviors': behaviors})


class Migration(migrations.Migration):
    dependencies = [('core', '0060_layout_fields_the_model_has')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
