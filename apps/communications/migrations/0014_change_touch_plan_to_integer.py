"""Change touch.plan from JSONField to PositiveSmallIntegerField (N days follow-up)."""
from django.db import migrations, models


def clear_json_plan(apps, schema_editor):
    """Set all existing plan values to 0 before column type change."""
    schema_editor.execute("UPDATE touches SET plan = '0' WHERE plan IS NOT NULL")


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0013_add_touch_linkage_id'),
    ]

    operations = [
        migrations.RunPython(clear_json_plan, migrations.RunPython.noop),
        migrations.RunSQL(
            "ALTER TABLE touches ALTER COLUMN plan TYPE smallint USING 0",
            "ALTER TABLE touches ALTER COLUMN plan TYPE jsonb USING '[]'::jsonb",
        ),
        migrations.AlterField(
            model_name='touch',
            name='plan',
            field=models.PositiveSmallIntegerField(
                default=0,
                db_index=True,
                help_text='Follow-up in N days from dt_created. 0 = no follow-up. Due when dt_created + (plan * 86400000) <= now.',
            ),
        ),
    ]
