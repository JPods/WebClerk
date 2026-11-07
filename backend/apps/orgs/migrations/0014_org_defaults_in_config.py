"""An org carries its own defaults for its documents in config.defaults = {fields, formatting}
(readme 106, "Orgs carry their own defaults"): a loose config.ship_via (Riverside's 'USPS')
moves into config.defaults.fields.ship_via in the lists' spelling. The transform is
core/services/defaults.migrate_org_config."""
from django.db import migrations


def forward(apps, schema_editor):
    from apps.core.services.defaults import migrate_org_config
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
