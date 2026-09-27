"""model_name → target_model on AliceObservation and AlicePreset (Bill, 2026-09-26). See core 0020."""
from django.db import migrations, models

# RenameField renames the column, and Postgres carries the column into every index on it, so
# the named indexes below need no SQL. Only the migration state still lists the old field name
# in them; the state-only Remove/Add brings it level with Meta.indexes.


class Migration(migrations.Migration):

    dependencies = [
        ('ai_assistant', '0009_comments_flat_default'),
    ]

    operations = [
        migrations.RenameField(model_name='aliceobservation', old_name='model_name', new_name='target_model'),
        migrations.RenameField(model_name='alicepreset', old_name='model_name', new_name='target_model'),
        migrations.SeparateDatabaseAndState(state_operations=[
            migrations.RemoveIndex(model_name='alicepreset', name='alicepreset_type_model_idx'),
            migrations.AddIndex(
                model_name='alicepreset',
                index=models.Index(fields=['preset_type', 'target_model'], name='alicepreset_type_model_idx'),
            ),
        ]),
    ]
