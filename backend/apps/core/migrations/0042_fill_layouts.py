"""Every model has its list, detail, form, panel and card (Bill, 2026-10-29).

Each model definition gains only the layout parts it lacks — from layouts.json, or a guess from
the model's fields (apps/core/layouts). A form with sections but no fields gains a header of the
model's cards in front. Nothing a company has is overwritten.
"""
from django.db import migrations


def fill(apps, schema_editor):
    from apps.core import layouts
    Setting = apps.get_model('core', 'Setting')
    for d in Setting.objects.filter(purpose='wc:model').exclude(parent_model=''):
        layout, filled = layouts.fill(d.parent_model, (d.config or {}).get('layout'))
        if filled:
            config = dict(d.config or {})
            config['layout'] = layout
            Setting.objects.filter(pk=d.pk).update(config=config)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0041_pending_purposes'),
    ]

    operations = [
        migrations.RunPython(fill, migrations.RunPython.noop),
    ]
