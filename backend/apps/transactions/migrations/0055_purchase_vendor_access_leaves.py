"""The purchase definition's 'all' access set learns the vendor block's leaves (0054 moved the
vendor out of bill_to). A role granted '@all' reads this stored set (Bill, 2026-09-20: "a leaf
added later is in no list until someone adds it"), so without this the door projected the
vendor block out on read: the form showed the block's title over blank fields. Frozen: the
leaves are literals here, as grow_access_leaves computes them from the schema.
"""
from django.db import migrations

NEW_LEAVES = ('addresses.vendor.attention', 'addresses.vendor.company', 'addresses.vendor.contact_id',
              'addresses.vendor.full_address', 'addresses.vendor.instructions',
              'emails.vendor.email', 'emails.vendor.email_id',
              'phones.vendor.number', 'phones.vendor.phone_id')


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
    for s in Setting.objects.filter(purpose='wc:model', parent_model__iexact='purchase'):
        if not isinstance(s.config, dict):
            continue
        config = grown(s.config)
        if config != s.config:
            Setting.objects.filter(pk=s.pk).update(config=config)
    from apps.core.services.access import clear_cache
    clear_cache('purchase')


class Migration(migrations.Migration):
    dependencies = [('transactions', '0054_purchase_vendor_block')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
