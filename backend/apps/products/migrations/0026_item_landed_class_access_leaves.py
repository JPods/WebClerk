"""The item definition's 'all' access set learns config.landed_class.<freight|duty|handling|vat>
(Bill, 2026-11-26: an item's class for each of a receipt's charges). A role granted '@all' reads
this stored set ("a leaf added later is in no list until someone adds it", Bill, 2026-09-20), so
without this the door would ignore the labels on save and project them out on read. Frozen: the
leaves are literals here, as grow_access_leaves computes them from the schema.
"""
from django.db import migrations

NEW_LEAVES = ('config.landed_class.duty', 'config.landed_class.freight',
              'config.landed_class.handling', 'config.landed_class.vat')


def grown(config):
    """The definition's config with its 'all' set grown; unchanged when it has no sets."""
    config = dict(config or {})
    access = config.get('access')
    if not isinstance(access, dict) or not isinstance(access.get('sets'), dict) \
            or not isinstance(access['sets'].get('all'), list):
        return config
    sets = dict(access['sets'])
    current = list(sets['all'])
    for leaf in NEW_LEAVES:
        if leaf not in current:
            current.append(leaf)
    sets['all'] = sorted(current)
    config['access'] = {**access, 'sets': sets}
    return config


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model', parent_model__iexact='item'):
        if not isinstance(s.config, dict):
            continue
        config = grown(s.config)
        if config != s.config:
            Setting.objects.filter(pk=s.pk).update(config=config)
    from apps.core.services.access import clear_cache
    clear_cache('item')


class Migration(migrations.Migration):
    dependencies = [('products', '0025_item_margin_pct_own')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
