"""The shared bundle key moves from config.key (returned by the API) to
encryption.credentials.sync_key (never leaves the server). Import plan §17.5, 2026-09-27."""
from django.db import migrations


def move_keys(apps, schema_editor):
    Connection = apps.get_model('sync', 'Connection')
    for conn in Connection.objects.all().only('pk', 'config', 'encryption'):
        config = dict(conn.config) if isinstance(conn.config, dict) else {}
        if 'key' not in config:
            continue
        key = config.pop('key')
        enc = dict(conn.encryption) if isinstance(conn.encryption, dict) else {}
        creds = dict(enc.get('credentials') or {})
        if key and key != 'self-connection':      # the literal self key is not kept; the seeder makes a random one
            creds.setdefault('sync_key', key)
        enc['credentials'] = creds
        Connection.objects.filter(pk=conn.pk).update(config=config, encryption=enc)


class Migration(migrations.Migration):
    dependencies = [('sync', '0008_comments_flat_default')]
    operations = [migrations.RunPython(move_keys, migrations.RunPython.noop)]
