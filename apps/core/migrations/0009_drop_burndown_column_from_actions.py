from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_alter_setting_purpose"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE actions DROP COLUMN IF EXISTS burndown",
            reverse_sql="ALTER TABLE actions ADD COLUMN burndown SMALLINT NOT NULL DEFAULT 0",
        ),
    ]
