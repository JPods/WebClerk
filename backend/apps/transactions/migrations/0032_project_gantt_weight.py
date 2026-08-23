"""Set prefs.gantt.weight on all existing projects.

Top-level projects with actions get weight=3 (normal).
Sprint/child projects get weight=0 (hidden from Gantt dropdown).
Projects with no actions and no children get weight=1 (low).
"""
from django.db import migrations


def set_gantt_weights(apps, schema_editor):
    Project = apps.get_model('transactions', 'Project')
    Action = apps.get_model('core', 'Action')

    # Collect project IDs that have actions
    project_ids_with_actions = set(
        Action.objects.filter(is_active=True)
        .values_list('project_id', flat=True)
        .distinct()
    )

    # Collect project IDs that are parents (have children)
    parent_ids = set(
        Project.objects.filter(id_parent__isnull=False, is_active=True)
        .values_list('id_parent', flat=True)
        .distinct()
    )

    for proj in Project.objects.filter(is_active=True):
        prefs = proj.prefs or {}
        if not isinstance(prefs, dict):
            prefs = {}

        gantt = prefs.get('gantt', {})
        if not isinstance(gantt, dict):
            gantt = {}

        # Skip if already set
        if 'weight' in gantt:
            continue

        is_child = proj.id_parent is not None
        has_actions = proj.pk in project_ids_with_actions
        is_parent = proj.pk in parent_ids

        if is_child:
            # Sprint/child projects: hidden by default
            gantt['weight'] = 0
        elif is_parent or has_actions:
            # Top-level with children or actions: normal visibility
            gantt['weight'] = 3
        else:
            # Top-level, no actions, no children: low
            gantt['weight'] = 1

        prefs['gantt'] = gantt
        proj.prefs = prefs
        proj.save(update_fields=['prefs'])


def reverse_gantt_weights(apps, schema_editor):
    """Remove gantt.weight from prefs (reversible)."""
    Project = apps.get_model('transactions', 'Project')
    for proj in Project.objects.filter(is_active=True):
        prefs = proj.prefs or {}
        if isinstance(prefs, dict) and 'gantt' in prefs:
            gantt = prefs['gantt']
            if isinstance(gantt, dict) and 'weight' in gantt:
                del gantt['weight']
                if not gantt:
                    del prefs['gantt']
                proj.prefs = prefs
                proj.save(update_fields=['prefs'])


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0031_receipt_landed_cost_fields'),
    ]

    operations = [
        migrations.RunPython(set_gantt_weights, reverse_gantt_weights),
    ]
