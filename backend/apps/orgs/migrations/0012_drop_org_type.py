"""The org `type` column goes (Bill approved, allie-89; done 2026-10-22).

It held a classification (distributor, end_user, ...) that nothing read: 22 of 27 orgs in
wc_demo were blank, 4 said 'company', 1 said 'customer' — org_type is the role. What
named it in the org wc:model Settings (customer, vendor, manufacturer, rep, employee,
other_org),
the same seven places in each: the access set 'all', the card/form/list/detail layouts,
field_groups and its stored behavior. Removed before the column.
"""
from django.db import migrations

ORG_MODELS = ('customer', 'vendor', 'manufacturer', 'rep', 'employee', 'other_org')


def without_type(value):
    if isinstance(value, dict):
        return {k: without_type(v) for k, v in value.items()}
    if isinstance(value, list):
        return [without_type(v) for v in value
                if v != 'type' and not (isinstance(v, dict) and v.get('field') == 'type')]
    return value


def org_config_without_type(config):
    config = without_type(config)
    behaviors = config.get('behaviors') if isinstance(config, dict) else None
    if isinstance(behaviors, dict) and 'type' in behaviors:
        config = {**config, 'behaviors': {k: v for k, v in behaviors.items() if k != 'type'}}
    return config


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for pk, config in (Setting.objects.filter(parent_model__in=ORG_MODELS)
                       .values_list('pk', 'config').iterator()):
        new = org_config_without_type(config)
        if new != config:
            Setting.objects.filter(pk=pk).update(config=new)


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0011_terms_text'),
        ('core', '0025_terms_text_setting_leaves'),
    ]

    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
        migrations.RemoveField(model_name='orgbase', name='type'),
    ]
