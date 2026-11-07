"""An org carries its own defaults for its documents in config.defaults = {fields, formatting}
(readme 106, "Orgs carry their own defaults"): a loose config.ship_via (Riverside's 'USPS')
moves into config.defaults.fields.ship_via in the lists' spelling. Frozen: the transform
is here, never imported from live code (the lead's rule, as 0025)."""
from django.db import migrations


def migrate_org_config(config):
    config = dict(config or {})
    loose = config.pop('ship_via', None)
    block = config.get('defaults') if isinstance(config.get('defaults'), dict) else {}
    fields = dict(block.get('fields') or {}) if isinstance(block.get('fields'), dict) else {}
    if loose not in (None, '') and not fields.get('ship_via'):
        fields['ship_via'] = str(loose).strip().lower()
    if fields or 'defaults' in config or loose is not None:
        config['defaults'] = {'fields': fields, 'formatting': dict(block.get('formatting') or {})}
    return config


def forward(apps, schema_editor):
    OrgBase = apps.get_model('orgs', 'OrgBase')
    for org in OrgBase.objects.exclude(config={}).only('pk', 'config'):
        if not isinstance(org.config, dict) or not ('ship_via' in org.config or 'defaults' in org.config):
            continue
        config = migrate_org_config(org.config)
        if config != org.config:
            OrgBase.objects.filter(pk=org.pk).update(config=config)


class Migration(migrations.Migration):
    dependencies = [('orgs', '0013_source_name_on_every_org')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
