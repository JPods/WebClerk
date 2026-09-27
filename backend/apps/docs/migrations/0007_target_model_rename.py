"""model_name → target_model on Document and Tag (Bill, 2026-09-26). See core 0020."""
from django.db import migrations, models

# RenameField renames the column, and Postgres carries the column into every index on it, so
# the named indexes below need no SQL. Only the migration state still lists the old field name
# in them; the state-only Remove/Add brings it level with Meta.indexes.


class Migration(migrations.Migration):

    dependencies = [
        ('docs', '0006_comments_flat_default'),
    ]

    operations = [
        migrations.RenameField(model_name='document', old_name='model_name', new_name='target_model'),
        migrations.RenameField(model_name='tag', old_name='model_name', new_name='target_model'),
        migrations.SeparateDatabaseAndState(state_operations=[
            migrations.RemoveIndex(model_name='document', name='doc_model_record_idx'),
            migrations.AddIndex(
                model_name='document',
                index=models.Index(fields=['target_model', 'record_id'], name='doc_model_record_idx'),
            ),
            migrations.RemoveIndex(model_name='tag', name='tag_model_name_idx'),
            migrations.AddIndex(
                model_name='tag',
                index=models.Index(fields=['target_model'], name='tag_model_name_idx'),
            ),
        ]),
        migrations.AlterField(
            model_name='document',
            name='record_id',
            field=models.BigIntegerField(blank=True, db_index=True, null=True,
                                         help_text="PK of the linked record in target_model's table"),
        ),
    ]
