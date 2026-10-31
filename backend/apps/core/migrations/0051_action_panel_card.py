"""The Actions panel is the shared linked-records panel (Bill, 2026-10-31): its columns show the
action itself and who it is assigned to, and an action opens in its card (action, status, due,
assigned to) — the card "+ add" uses too.

A definition still holding the old shipped columns takes the new ones; one a company changed
keeps its own. The card is added where there is none.
"""
from django.db import migrations

OLD_PANEL = ['ida', 'purpose', 'status', 'action_type', 'priority', 'dt_deadline']


def update(apps, schema_editor):
    from apps.core import layouts
    shipped = layouts.build('action')
    panel, card = shipped.get('panel'), (shipped.get('card') or {}).get('add')
    Setting = apps.get_model('core', 'Setting')
    for d in Setting.objects.filter(purpose='wc:model', parent_model='action'):
        config = dict(d.config or {})
        layout = dict(config.get('layout') or {})
        changed = False
        held = [c.get('field') for c in layout.get('panel') or [] if isinstance(c, dict)]
        if panel and held in ([], OLD_PANEL):
            layout['panel'] = panel
            changed = True
        cards = dict(layout.get('card') or {})
        if card and 'add' not in cards:
            cards['add'] = card
            layout['card'] = cards
            changed = True
        if changed:
            config['layout'] = layout
            Setting.objects.filter(pk=d.pk).update(config=config)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0050_two_sided_links'),
    ]

    operations = [
        migrations.RunPython(update, migrations.RunPython.noop),
    ]
