"""Alice's to-dos are Actions, not Settings (Bill, 2026-10-28). Moves any Setting purpose
alice_pending to an Action (purpose alice, config.alice = {role, model, details}); an inactive
one is a resolved to-do."""
from django.db import migrations


def move(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    Action = apps.get_model('core', 'Action')
    moved = 0
    for s in Setting.objects.filter(purpose='alice_pending').order_by('id'):
        details = dict(s.config or {})
        details.pop('category', None)
        Action.objects.create(
            purpose='alice', action={'en': s.name or ''},
            status='open' if s.is_active else 'complete',
            kanban_column='Backlog' if s.is_active else 'Complete',
            config={'alice': {'role': s.role or '', 'model': s.parent_model or '',
                              'details': details}},
            metadata={'agent': True, 'source_agent': 'alice'},
            dt_created=s.dt_created, dt_modified=s.dt_modified,
        )
        moved += 1
    Setting.objects.filter(purpose='alice_pending').delete()
    if moved:
        print(f"\n  Alice to-dos moved to Actions: {moved}")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_delete_old_logs'),
    ]

    operations = [
        migrations.RunPython(move, migrations.RunPython.noop),
    ]
