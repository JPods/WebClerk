"""One Pending purpose list (Bill, 2026-10-29; core.models audit C-2, V-4).

A Pending's purpose names the work it waits to do; the family leads the name. pending.PURPOSES
is the one list: the code takes its purposes from it, and this writes it into the pending
definition (config.selectlists.purpose).

1. Stored rows take the new names: opening_balance → inventory_opening, allocation →
   inventory_allocation, sync.bundle_out → sync_bundle_out.
2. Rows whose purpose has no writer or handler go: line_event, inventory_delta,
   inventory_discrepancy, and small_sting (one stale row on alice_log).
3. The pending definition's purpose list becomes PURPOSES.
"""
from django.db import migrations

RENAMED = {'opening_balance': 'inventory_opening', 'allocation': 'inventory_allocation',
           'sync.bundle_out': 'sync_bundle_out'}
DEAD = ('line_event', 'inventory_delta', 'inventory_discrepancy', 'small_sting')


def rename(apps, schema_editor):
    Pending = apps.get_model('core', 'Pending')
    for old, new in RENAMED.items():
        Pending.objects.filter(purpose=old).update(purpose=new)
    Pending.objects.filter(purpose__in=DEAD).delete()


def write_list(apps, schema_editor):
    from apps.core.models.pending import PURPOSES
    Setting = apps.get_model('core', 'Setting')
    for d in Setting.objects.filter(purpose='wc:model', parent_model='pending'):
        config = dict(d.config or {})
        lists = dict(config.get('selectlists') or {})
        lists['purpose'] = [{'value': v, 'label': label} for v, label in PURPOSES.items()]
        config['selectlists'] = lists
        Setting.objects.filter(pk=d.pk).update(config=config)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0040_rebuild_select_lists'),
    ]

    operations = [
        migrations.RunPython(rename, migrations.RunPython.noop),
        migrations.RunPython(write_list, migrations.RunPython.noop),
    ]
