# Rename Action model project_id field to id_project

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_rename_model_name_to_model_target'),
    ]

    operations = [
        migrations.RenameField(
            model_name='action',
            old_name='project_id',
            new_name='id_project',
        ),
    ]