"""Each model's purposes are its definition's list (Bill, 2026-10-28): config.selectlists.purpose
on its wc:model Setting, edited by an administrator and enforced by the door and Log.write.

Per definition this:
- folds config.select_lists into config.selectlists (one key; selectlists wins a conflict),
  every list but purpose moved as it is;
- rebuilds selectlists.purpose from the starting list (below), the list it already had, the
  purpose field's inline options, and the key-like purposes its own records use — dropping
  the generic standard/template/test/internal list no record uses. A model with nothing to
  list gets one entry, user_defined, for an administrator to replace (Bill: "just set it to
  user define"). A model with no purpose field, or a page over another model's table, gets
  no list (unchecked);
- leaves the purpose field's behaviour as text (the list makes it a dropdown).

It also moves a log written as a Setting (purpose alice_log) into the Log, as 0027 did.
"""
import re
import uuid

from django.db import connection, migrations

BOILERPLATE = {'standard', 'template', 'test', 'internal'}
USER_DEFINED = {'value': 'user_defined', 'label': 'User defined'}
KEY = re.compile(r'^[A-Za-z0-9_:.\-]{1,64}$')
_opt = lambda values: [{'value': v, 'label': v} for v in values]          # noqa: E731
START = {
    'action': [{'value': 'alice', 'label': 'Alice — her to-do'}],
    'address': [{'value': v, 'label': v.title()} for v in
                ('billing', 'shipping', 'mailing', 'location', 'other')],
    'document': [{'value': v, 'label': v.title()} for v in
                 ('attachment', 'template', 'image', 'reference', 'certificate')],
    'log': [
        {'value': 'audit', 'label': 'Audit — a change to an audited record'},
        {'value': 'alice', 'label': 'Alice — what Alice observed'},
        {'value': 'refs_mismatch', 'label': "Refs mismatch — a record's FK and refs.links disagree"},
        {'value': 'coaching', 'label': 'Coaching — a drill a person ran'},
        {'value': 'inventory', 'label': "Inventory — a document line changed an item's quantity"},
        {'value': 'quiz', 'label': "Quiz — a person's answer to a training question"},
    ],
    'setting': _opt((
        'wc:model', 'wc:system', 'wc:admin', 'wc:company_profile', 'wc:wchq_connection',
        'wc:cash_gateway', 'wc:shipping_service', 'wc:security', 'wc:dd_card', 'wc:escalation',
        'wc:hook_points', 'wc:ai', 'wc:page_help', 'wc:ui', 'wc:db_defaults', 'wc:keywords',
        'wc:selectlist', 'wc:feature', 'wc:schema_map', 'wc:collaborate', 'wc:qa_counters',
        'wc:qa_questions', 'wc:test_parade', 'device_status', 'accounting_interface',
        'user:campaign')),
}


def _options(value):
    """A select list in either old shape: [{value, label}] or {label, choices, allow_custom}."""
    if isinstance(value, dict):
        value = value.get('choices') or value.get('options') or []
    out = []
    for o in value if isinstance(value, list) else []:
        v = o.get('value') if isinstance(o, dict) else o
        if v not in (None, ''):
            out.append({'value': str(v), 'label': (o.get('label') if isinstance(o, dict) else None) or str(v)})
    return out


def _used_purposes(model_cls):
    with connection.cursor() as cur:
        cur.execute(f'SELECT DISTINCT purpose FROM "{model_cls._meta.db_table}" '
                    f"WHERE coalesce(purpose, '') <> ''")
        return {p for (p,) in cur.fetchall() if KEY.match(p)}


def rebuild(apps, schema_editor):
    from apps.core.utils import registry        # the live model for each key: its table
    Setting = apps.get_model('core', 'Setting')
    setting_table = Setting._meta.db_table
    for d in Setting.objects.filter(purpose='wc:model'):
        key = d.parent_model or ''
        config = dict(d.config or {})
        lists = dict(config.pop('select_lists', None) or {})
        lists.update(config.get('selectlists') or {})
        behaviors = dict(config.get('behaviors') or {})
        inline = _options((behaviors.get('purpose') or {}).get('options'))

        model_cls = registry.resolve(key)
        has_purpose = model_cls is not None and 'purpose' in {
            f.name for f in model_cls._meta.concrete_fields}
        alias = (model_cls is not None and model_cls._meta.db_table == setting_table
                 and key != 'setting')
        purposes = []
        if has_purpose and not alias:
            used = _used_purposes(model_cls)
            seen = set()
            start = {o['value'] for o in START.get(key, [])}
            for o in START.get(key, []) + _options(lists.get('purpose')) + inline + _opt(sorted(used)):
                v = o['value']
                if v in seen or (v in BOILERPLATE and v not in used and v not in start):
                    continue
                seen.add(v)
                purposes.append(o)
            lists['purpose'] = purposes or [USER_DEFINED]
        else:
            lists.pop('purpose', None)
        if 'purpose' in behaviors:
            behaviors['purpose'] = {'type': 'text'}
            config['behaviors'] = behaviors
        config['selectlists'] = lists
        Setting.objects.filter(pk=d.pk).update(config=config)


def fold_alice_log(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    Log = apps.get_model('core', 'Log')
    for s in Setting.objects.filter(purpose='alice_log'):
        details = dict(s.config or {})
        details.pop('category', None)
        entry = Log.objects.create(
            uuid=uuid.uuid4(), purpose='alice', action=s.role or '', model_name=s.parent_model or '',
            config={'name': s.name, 'details': details}, refs={},
            dt_created=s.dt_created or 0, dt_modified=s.dt_created or 0)
        Log.objects.filter(pk=entry.pk).update(ida=str(entry.pk))
        Setting.objects.filter(pk=s.pk).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0038_strip_pdfme_templates'),
    ]

    operations = [
        migrations.RunPython(fold_alice_log, migrations.RunPython.noop),   # first: not a purpose
        migrations.RunPython(rebuild, migrations.RunPython.noop),
    ]
