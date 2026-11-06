"""The company profile's section is ``defaults`` (Bill, 2026-11-05: "config.defaults, not
metadata"): 0062 wrote it as ``default``; one name, the plural, in config."""
from django.db import migrations


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for company in Setting.objects.filter(purpose='wc:company_profile'):
        config = dict(company.config or {})
        if 'default' in config:
            config['defaults'] = config.pop('default')
            Setting.objects.filter(pk=company.pk).update(config=config)


class Migration(migrations.Migration):
    dependencies = [('core', '0063_terms_is_a_lookup_in_stored_behaviors')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
