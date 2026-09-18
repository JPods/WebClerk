# The Athena token moves from Connection.config to Connection.encryption (2026-09-18).
# config is shown in the UI and returned by the API; the token must only be read by the
# server. db_init already wrote encryption.athena_token while every reader looked in
# config, so tokens issued by db_init never authenticated. One home now.

import json

from django.db import migrations


def move_token(apps, schema_editor):
    with schema_editor.connection.cursor() as cur:
        cur.execute("select id, config, encryption from connections where config ? 'athena_token'")
        for pk, config, encryption in cur.fetchall():
            config = json.loads(config) if isinstance(config, str) else (config or {})
            encryption = json.loads(encryption) if isinstance(encryption, str) else (encryption or {})
            token = config.pop('athena_token')
            if token and not encryption.get('athena_token'):
                encryption['athena_token'] = token
            cur.execute('update connections set config = %s, encryption = %s where id = %s',
                        [json.dumps(config), json.dumps(encryption), pk])


class Migration(migrations.Migration):

    dependencies = [
        ('sync', '0004_cash_rename'),
    ]

    operations = [
        migrations.RunPython(move_token, migrations.RunPython.noop),
    ]
