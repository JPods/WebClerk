"""One active report per verb hook slot (Bill, 2026-09-24).

A slot is ``<model>.<verb>_pre`` or ``<model>.<verb>_post``. To put a new report in a
slot, the old one must be made inactive first. Report.save refuses with coaching; this
index is what makes two concurrent saves unable to both succeed. A report's own points
(``invoice.report_after``) are shared and are not slots.
"""
from django.db import migrations

SLOT = r"(config->'hooks'->>'point')"

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_alter_userdailylog_user'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(f"CREATE UNIQUE INDEX reports_one_active_hook_per_slot ON reports ({SLOT}) "
                 f"WHERE is_active AND {SLOT} ~ '^\\w+\\.\\w+_(pre|post)$';"),
            reverse_sql="DROP INDEX IF EXISTS reports_one_active_hook_per_slot;",
        ),
    ]
