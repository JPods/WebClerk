"""The six org definitions' 'all' access set learns the leaves their schema gained on
2026-11-07 (readme 106): source_name (orgs 0013) and config.defaults.fields.* /
config.defaults.formatting.* (an org's own defaults for its documents), and forgets the
loose config.ship_via that orgs 0014 moved. A role granted '@all' reads this stored set
(Bill, 2026-09-20: "a leaf added later is in no list until someone adds it"), so without
this the door projected an org's defaults out on read and refused them on write. Frozen:
the leaves are literals here, as grow_access_leaves computed them from the schema.
"""
from django.db import migrations

ORGS = ('customer', 'vendor', 'manufacturer', 'rep', 'employee', 'other_org')
NEW_LEAVES = ('source_name',
              'config.defaults.fields.dt_needed_days', 'config.defaults.fields.priority',
              'config.defaults.fields.rep_id', 'config.defaults.fields.ship_via',
              'config.defaults.formatting.currency', 'config.defaults.formatting.date_format',
              'config.defaults.formatting.locale', 'config.defaults.formatting.number_precision')
GONE = ('config.ship_via',)


def grown(config):
    """The definition's config with its 'all' set grown and pruned; unchanged when it has no sets."""
    config = dict(config or {})
    access = config.get('access')
    if not isinstance(access, dict) or not isinstance(access.get('sets'), dict):
        return config
    sets = dict(access['sets'])
    current = [leaf for leaf in (sets.get('all') or []) if leaf not in GONE]
    for leaf in NEW_LEAVES:
        if leaf not in current:
            current.append(leaf)
    sets['all'] = sorted(current)
    config['access'] = {**access, 'sets': sets}
    return config


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model', parent_model__in=ORGS):
        if not isinstance(s.config, dict):
            continue
        config = grown(s.config)
        if config != s.config:
            Setting.objects.filter(pk=s.pk).update(config=config)


class Migration(migrations.Migration):
    dependencies = [('core', '0072_defaults_in_each_models_setting')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
