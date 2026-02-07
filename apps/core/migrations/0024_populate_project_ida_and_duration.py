# Generated data migration

from django.db import migrations


def populate_project_ida_and_duration(apps, schema_editor):
    """
    Copy project_id into project_ida (as string) where project_ida is empty.
    Set duration to 7 where it is null or 0.
    """
    Action = apps.get_model('core', 'Action')
    
    # Update project_ida from project_id where empty or null
    for action in Action.objects.filter(project_ida__isnull=True).exclude(project_id=0):
        action.project_ida = str(action.project_id)
        action.save(update_fields=['project_ida'])
    
    for action in Action.objects.filter(project_ida='').exclude(project_id=0):
        action.project_ida = str(action.project_id)
        action.save(update_fields=['project_ida'])
    
    # Update duration to 7 where null or 0
    Action.objects.filter(duration__isnull=True).update(duration=7)
    Action.objects.filter(duration=0).update(duration=7)


def reverse_populate(apps, schema_editor):
    # No need to reverse - data is still valid
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_action_project_ida'),
    ]

    operations = [
        migrations.RunPython(populate_project_ida_and_duration, reverse_populate),
    ]
