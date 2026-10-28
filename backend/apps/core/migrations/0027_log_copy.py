"""Copy every log into the one Log (Bill, 2026-10-28).

AuditLog → audit, RefsMismatchLog → refs_mismatch, Setting purpose alice_log → alice,
AliceCoachingLog → coaching, SerialLog → the serial's own config.actions. APILog and
UserDailyLog are empty and are not copied (UserDailyLog: deleted, Bill). Historical models skip
CoreModel.save, so uuid, ida (= str(pk)) and dt_modified are set here. A user id that names no
user is kept in config.user_id rather than written to the FK.
"""
import uuid

from django.db import migrations
from django.db.models import F
from django.db.models.functions import Cast
from django.db.models import CharField

BATCH = 500


def _copy(Log, rows):
    made = Log.objects.bulk_create(rows, batch_size=BATCH)
    return len(made)


def copy_logs(apps, schema_editor):
    Log = apps.get_model('core', 'Log')
    User = apps.get_model(*__import__('django.conf', fromlist=['settings']).settings.AUTH_USER_MODEL.split('.'))
    users = set(User.objects.values_list('pk', flat=True))

    def entry(purpose, action, dt, *, user_id=None, model_name='', record_id=None, name='',
              changes=None, details=None):
        details = dict(details or {})
        if user_id is not None and user_id not in users:
            details['user_id'] = user_id
            user_id = None
        config = {k: v for k, v in (('name', name), ('changes', changes), ('details', details)) if v}
        return Log(uuid=uuid.uuid4(), purpose=purpose, action=action or '', user_id=user_id,
                   model_name=model_name or '', record_id=record_id, config=config,
                   refs={}, dt_created=dt or 0, dt_modified=dt or 0)

    counts = {}

    AuditLog = apps.get_model('core', 'AuditLog')
    rows = [entry('audit', a.action, a.dt_created, user_id=a.user_id, model_name=a.model_name,
                  record_id=a.record_id, changes=a.changes,
                  details={k: v for k, v in {
                      'ip_address': a.ip_address, 'user_agent': a.user_agent,
                      'session_id': a.session_id, 'metadata': a.metadata}.items() if v})
            for a in AuditLog.objects.order_by('id').iterator()]
    counts['audit'] = _copy(Log, rows)

    RefsMismatchLog = apps.get_model('core', 'RefsMismatchLog')
    rows = [entry('refs_mismatch', r.mismatch_type, r.dt_created, user_id=r.user_id,
                  model_name=r.parent_model, record_id=r.parent_id,
                  details={'related_model': r.related_model, 'fk_field': r.fk_field,
                           'fk_ids': r.fk_ids, 'refs_ids': r.refs_ids, 'only_in_fk': r.only_in_fk,
                           'only_in_refs': r.only_in_refs, 'caller': r.caller,
                           **({'context': r.details} if r.details else {})})
            for r in RefsMismatchLog.objects.order_by('id').iterator()]
    counts['refs_mismatch'] = _copy(Log, rows)

    Setting = apps.get_model('core', 'Setting')
    rows = []
    for s in Setting.objects.filter(purpose='alice_log').order_by('id').iterator():
        config = dict(s.config or {})
        user_id = config.pop('user_id', None)
        config.pop('category', None)
        rows.append(entry('alice', s.role, s.dt_created, user_id=user_id,
                          model_name=s.parent_model, name=s.name, details=config))
    counts['alice'] = _copy(Log, rows)

    AliceCoachingLog = apps.get_model('ai_assistant', 'AliceCoachingLog')
    rows = [entry('coaching', 'passed' if c.passed else 'completed' if c.completed else 'started',
                  c.dt_completed or c.dt_started or c.dt_created,
                  details={'contact_id': c.contact_id, 'drill_id': c.drill_id,
                          'document_id': c.document_id, 'drill_name': c.drill_name,
                          'category': c.category, 'score': c.score,
                          'duration_seconds': c.duration_seconds,
                          'dt_started': c.dt_started, 'dt_completed': c.dt_completed})
            for c in AliceCoachingLog.objects.order_by('id').iterator()]
    counts['coaching'] = _copy(Log, rows)

    Log.objects.filter(ida='').update(ida=Cast(F('id'), output_field=CharField()))

    # A serial's history is its own config.actions (Bill: config.actions stays).
    Serial = apps.get_model('products', 'Serial')
    SerialLog = apps.get_model('products', 'SerialLog')
    folded = 0
    for sl in SerialLog.objects.order_by('serial_id', 'dt').iterator():
        serial = Serial.objects.filter(pk=sl.serial_id).first()
        if serial is None:
            continue
        cfg = dict(serial.config or {})
        old = dict(sl.config or {})
        action = {'action': sl.action, 'dt': sl.dt,
                  'status_before': old.get('status_before') or None,
                  'status_after': old.get('status_before') or serial.status or ''}
        for k in ('doc_type', 'doc_id', 'notes'):
            if old.get(k):
                action[k] = old[k]
        actions = list(cfg.get('actions') or [])
        actions.append(action)
        cfg['actions'] = sorted(actions, key=lambda a: a.get('dt') or 0)
        Serial.objects.filter(pk=serial.pk).update(config=cfg)
        folded += 1
    counts['serial_actions'] = folded

    print(f"\n  Log copy: {counts}")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_log'),
        ('products', '0023_catalog_line_item_optional'),
        ('ai_assistant', '0011_is_locked_deleted'),
    ]

    operations = [
        migrations.RunPython(copy_logs, migrations.RunPython.noop),
    ]
