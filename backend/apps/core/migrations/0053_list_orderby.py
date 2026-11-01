"""Every list reads in one order: what was asked, else config.orderby, else sequence, else newest
first (Bill, 2026-11-01; apps/core/services/list_order). Each model definition without an
orderby takes the first guess; one a company has set is left as it is."""
from django.db import migrations


def seed_orderby(apps, schema_editor):
    from apps.core.services.list_order import DEFAULT
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model'):
        config = dict(s.config or {})
        if isinstance(config.get('orderby'), list):
            continue
        config['orderby'] = list(DEFAULT.get(s.parent_model, []))
        Setting.objects.filter(pk=s.pk).update(config=config)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0052_panel_columns'),
    ]

    operations = [
        migrations.RunPython(seed_orderby, migrations.RunPython.noop),
    ]
