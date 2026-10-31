"""+ add on a panel opens the new record's card (Bill, 2026-10-30).

A contact's definition gains its add card, config.layout.card.add, when it lacks one — the card
"+ add" on an org's Contacts panel opens. Nothing a company has is overwritten.
"""
from django.db import migrations


def add_card(apps, schema_editor):
    from apps.core import layouts
    Setting = apps.get_model('core', 'Setting')
    shipped = (layouts.build('contact').get('card') or {}).get('add')
    if not shipped:
        return
    for d in Setting.objects.filter(purpose='wc:model', parent_model='contact'):
        config = dict(d.config or {})
        layout = dict(config.get('layout') or {})
        card = dict(layout.get('card') or {})
        if 'add' in card:
            continue
        card['add'] = shipped
        layout['card'] = card
        config['layout'] = layout
        Setting.objects.filter(pk=d.pk).update(config=config)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0047_drop_dead_role_models'),
    ]

    operations = [
        migrations.RunPython(add_card, migrations.RunPython.noop),
    ]
