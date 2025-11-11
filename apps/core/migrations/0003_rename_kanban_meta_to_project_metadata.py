# Generated manually for renaming kanban_meta to project_metadata

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_add_project_fields'),
    ]

    operations = [
        migrations.RenameField(
            model_name='action',
            old_name='kanban_meta',
            new_name='project_metadata',
        ),
    ]