"""Select lists support, they do not police (Bill, 2026-10-29): rebuild every model's lists
from what is in use, so the door's check (select_lists.py) asks people only about values that
are really new.

1. Action drift, repaired first so it does not join the lists: kanban columns and statuses spelled
   several ways, priorities off the 1–6 scale, 'follow-up'; the 30 actions owned by contact 69
   (which never existed — field_change_requests' "default to claude") go to Alice's login.
2. Every list a definition holds, and every field whose model declares choices, becomes:
   the list it had ∪ the model's declared choices ∪ the key-like values its records hold.
   A value with spaces or sentences is not taken from the data (it stays in its row).
   terms lists go: a record's terms are Term idas, which the door checks against the Term table.
   contact.role lists the roles access knows.
"""
import re

from decouple import config
from django.db import connection, migrations

KEY = re.compile(r'^[A-Za-z0-9_:.\-]{1,64}$')
KANBAN = {'done': 'Complete', 'backlog': 'Backlog', 'In Progress': 'InProcess',
          'in_progress': 'InProcess', 'doing': 'InProcess', 'todo': 'Backlog', 'Todo': 'Backlog'}
STATUS = {'complete': 'completed', 'Open': 'open', 'in_progress': 'active', 'planned': 'open'}
INTEGER = ('IntegerField', 'PositiveIntegerField', 'SmallIntegerField', 'BigIntegerField',
           'PositiveSmallIntegerField')


def repair_actions(apps, schema_editor):
    Action = apps.get_model('core', 'Action')
    Contact = apps.get_model('core', 'Contact')
    for old, new in KANBAN.items():
        Action.objects.filter(kanban_column=old).update(kanban_column=new)
    for old, new in STATUS.items():
        Action.objects.filter(status=old).update(status=new)
    Action.objects.filter(priority__gt=6).update(priority=6)
    Action.objects.filter(priority__lt=1).update(priority=1)
    Action.objects.filter(action_type='follow-up').update(action_type='follow_up')
    email = (config('ALICE_WC_EMAIL', default='') or '').strip().lower()
    alice = Contact.objects.filter(email__iexact=email).values_list('id', flat=True).first() if email else None
    if alice and not Contact.objects.filter(pk=69).exists():
        Action.objects.filter(contact_id=69).update(contact_id=alice)


def _options(value):
    if isinstance(value, dict):
        value = value.get('choices') or value.get('options') or []
    out = []
    for o in value if isinstance(value, list) else []:
        v = o.get('value') if isinstance(o, dict) else o
        if v not in (None, ''):
            out.append({'value': v, 'label': (o.get('label') if isinstance(o, dict) else None) or str(v)})
    return out


def _in_use(model_cls, field):
    col = model_cls._meta.get_field(field).column
    with connection.cursor() as cur:
        cur.execute(f'SELECT DISTINCT "{col}"::text FROM "{model_cls._meta.db_table}" '
                    f'WHERE "{col}" IS NOT NULL')
        return sorted(v for (v,) in cur.fetchall() if v and KEY.match(v))


def rebuild(apps, schema_editor):
    from apps.core.services.access import PORTAL_ROLES, STAFF_ROLES
    from apps.core.utils import registry
    Setting = apps.get_model('core', 'Setting')
    setting_table = Setting._meta.db_table
    for d in Setting.objects.filter(purpose='wc:model'):
        key = d.parent_model or ''
        model_cls = registry.resolve(key)
        if model_cls is None or (model_cls._meta.db_table == setting_table and key != 'setting'):
            continue
        fields = {f.name: f for f in model_cls._meta.concrete_fields}
        config_ = dict(d.config or {})
        lists = dict(config_.get('selectlists') or {})
        lists.pop('terms', None)
        names = set(lists) | {n for n, f in fields.items() if f.choices}
        for name in sorted(names):
            if name not in fields:
                continue
            field = fields[name]
            integer = field.get_internal_type() in INTEGER
            merged, seen = [], set()
            candidates = _options(lists.get(name)) + [
                {'value': v, 'label': str(label)} for v, label in (field.choices or []) if v not in (None, '')]
            if key == 'contact' and name == 'role':
                candidates += [{'value': r, 'label': r} for r in (*STAFF_ROLES, *PORTAL_ROLES)]
            candidates += [{'value': int(v) if integer and v.lstrip('-').isdigit() else v, 'label': v}
                           for v in _in_use(model_cls, name)]
            for o in candidates:
                if str(o['value']) in seen:
                    continue
                seen.add(str(o['value']))
                merged.append(o)
            if merged:
                lists[name] = merged
        config_['selectlists'] = lists
        Setting.objects.filter(pk=d.pk).update(config=config_)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0039_purpose_lists_in_definitions'),
    ]

    operations = [
        migrations.RunPython(repair_actions, migrations.RunPython.noop),
        migrations.RunPython(rebuild, migrations.RunPython.noop),
    ]
