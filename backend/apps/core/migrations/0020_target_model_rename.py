"""model_name → target_model on Report and Notification (Bill, 2026-09-26).

The REST door refuses ``model_name`` in every body (it was the routing key; the model is
now the URL path), so a field of that name could not be set by a user. The field meaning
"the model this record is about" is renamed ``target_model``. System models (Ledger,
Pending, AuditLog, ...) keep ``model_name``.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_comments_flat_data'),
    ]

    operations = [
        migrations.RenameField(model_name='report', old_name='model_name', new_name='target_model'),
        migrations.RenameField(model_name='notification', old_name='model_name', new_name='target_model'),
        migrations.AlterModelOptions(
            name='report',
            options={'ordering': ['target_model', 'sort_order', 'name']},
        ),
    ]
