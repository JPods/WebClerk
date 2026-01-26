# Generated manually for id_record -> record_id rename

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_remove_auditlog_user_id_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='pending',
            old_name='id_record',
            new_name='record_id',
        ),
    ]
