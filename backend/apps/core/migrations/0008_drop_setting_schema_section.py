# The wc:model Setting "schema" section is removed (Bill, 2026-09-18). It named each model's
# Pydantic module and classes — a copy of what code already declares in
# common.schemas.defaults. The copy went stale (67 of 70 pointed at common.schemas.<model>,
# which no longer exists) and save-time envelope validation silently switched off.
# Code is now the only source; there is nothing in the Setting to drift.

import json

from django.db import migrations


def drop_schema_section(apps, schema_editor):
    with schema_editor.connection.cursor() as cur:
        cur.execute("select id, config from settings where purpose = 'wc:model' and config ? 'schema'")
        for pk, config in cur.fetchall():
            config = json.loads(config) if isinstance(config, str) else config
            config.pop('schema')
            cur.execute('update settings set config = %s where id = %s', [json.dumps(config), pk])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_drop_report_script_columns'),
    ]

    operations = [
        migrations.RunPython(drop_schema_section, migrations.RunPython.noop),
    ]
