"""A specification's status has a list (definition_scan on a fresh install, 2026-11-06): the
definition held an empty one, so the form drew an empty select. A best-guess baseline a staff
member edits; a definition with a non-empty list keeps its own."""
from django.db import migrations

STATUS = [{'value': 'draft', 'label': 'Draft'}, {'value': 'active', 'label': 'Active'},
          {'value': 'retired', 'label': 'Retired'}]


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model', parent_model='specification'):
        if not isinstance(s.config, dict):
            continue
        lists = dict(s.config.get('selectlists') or {})
        if not lists.get('status'):
            lists['status'] = [dict(o) for o in STATUS]
            Setting.objects.filter(pk=s.pk).update(config={**s.config, 'selectlists': lists})


class Migration(migrations.Migration):
    dependencies = [('core', '0068_tax_code_id_leaf_is_a_number')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
