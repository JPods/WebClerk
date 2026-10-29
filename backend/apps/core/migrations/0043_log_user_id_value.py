"""Log keeps who acted as a value (Bill, 2026-10-28; core.models audit C-8).

Log.user was a foreign key with SET_NULL: deleting a contact erased who acted on every row they
caused, past the log's append-only rule. It becomes user_id, a plain number — the same column
and its values, without the constraint — as Lesson keeps contact_id. The log definition (layout,
access field sets, field groups, behaviours) names the field user_id.
"""
from django.db import migrations, models

DROP_FK = """
DO $$
DECLARE c text;
BEGIN
  FOR c IN SELECT con.conname FROM pg_constraint con
           JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = ANY (con.conkey)
           WHERE con.conrelid = 'logs'::regclass AND con.contype = 'f' AND a.attname = 'user_id'
  LOOP
    EXECUTE 'ALTER TABLE logs DROP CONSTRAINT ' || quote_ident(c);
  END LOOP;
END $$;
"""


def _renamed(value):
    """Every field reference 'user' in a layout part becomes 'user_id'."""
    if isinstance(value, dict):
        out = {k: _renamed(v) for k, v in value.items()}
        if out.get('field') == 'user':
            out['field'] = 'user_id'
            if out.get('label') == 'user':
                out['label'] = 'user_id'
        return out
    if isinstance(value, list):
        out = []
        for v in value:
            v = 'user_id' if v == 'user' else _renamed(v)
            if not (v == 'user_id' and v in out):
                out.append(v)
        return out
    return value


def rename_in_definition(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for d in Setting.objects.filter(purpose='wc:model', parent_model='log'):
        config = _renamed(dict(d.config or {}))
        behaviors = dict(config.get('behaviors') or {})
        if 'user' in behaviors:
            behaviors['user_id'] = behaviors.pop('user')
        config['behaviors'] = behaviors
        Setting.objects.filter(pk=d.pk).update(config=config)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0042_fill_layouts'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunSQL(DROP_FK, migrations.RunSQL.noop)],
            state_operations=[
                migrations.RemoveIndex(model_name='log', name='logs_user_id_0b6e40_idx'),
                migrations.RemoveField(model_name='log', name='user'),
                migrations.AddField(
                    model_name='log', name='user_id',
                    field=models.BigIntegerField(blank=True, db_index=True, null=True,
                                                 help_text='Who: the contact id of a person or an agent login')),
                migrations.AddIndex(
                    model_name='log',
                    index=models.Index(fields=['user_id', 'dt_created'], name='logs_user_id_0b6e40_idx')),
            ],
        ),
        migrations.RunPython(rename_in_definition, migrations.RunPython.noop),
    ]
