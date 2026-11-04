"""One spelling per status word (Bill, 2026-11-04): canceled, complete, on_hold.

The lists had both spellings because select_lists.add_value added whatever code wrote
(readme 105). Rewrites every model's status column, each wc:model Setting's selectlists,
every locked_statuses / status_transitions a Setting's config holds, and a bundle's
payload_path (its file sits in a folder named for its status; the folder is renamed by hand). Derived from the
lists, not hand-edited; no reverse — the old spellings were never intended.
"""
from django.db import migrations
from django.db.models import CharField

MAP = {'cancelled': 'canceled', 'completed': 'complete', 'onhold': 'on_hold', 'hold': 'on_hold'}
LABEL = {'canceled': 'Canceled', 'complete': 'Complete', 'on_hold': 'On Hold'}


def _word(v):
    return MAP.get(v, v) if isinstance(v, str) else v


def _options(options):
    """A select list's options, one spelling each, order kept, first occurrence wins."""
    out, seen = [], set()
    for o in options or []:
        value = _word(o.get('value') if isinstance(o, dict) else o)
        if value in seen:
            continue
        seen.add(value)
        label = (o.get('label') if isinstance(o, dict) else None) or str(value)
        if value in LABEL:
            label = LABEL[value]
        out.append({'value': value, 'label': label} if isinstance(o, dict) else value)
    return out


def _walk(node):
    """config with the three places a status word lives rewritten; everything else untouched."""
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k == 'selectlists' and isinstance(v, dict):
                out[k] = {f: (_options(o) if f == 'status' and isinstance(o, list) else o)
                          for f, o in v.items()}
            elif k == 'locked_statuses' and isinstance(v, list):
                out[k] = list(dict.fromkeys(_word(x) for x in v))
            elif k == 'status_transitions' and isinstance(v, dict):
                out[k] = {_word(s): (list(dict.fromkeys(_word(x) for x in t)) if isinstance(t, list) else t)
                          for s, t in v.items()}
            else:
                out[k] = _walk(v)
        return out
    if isinstance(node, list):
        return [_walk(x) for x in node]
    return node


def forward(apps, schema_editor):
    for model in apps.get_models():
        try:
            field = model._meta.get_field('status')
        except Exception:
            continue
        if not isinstance(field, CharField) or not field.concrete:
            continue
        for old, new in MAP.items():
            model.objects.filter(status=old).update(status=new)
    Bundle = apps.get_model('sync', 'Bundle')
    for bundle in Bundle.objects.exclude(config=None).iterator():
        path = (bundle.config or {}).get('payload_path') if isinstance(bundle.config, dict) else None
        if isinstance(path, str) and '/completed/' in path:
            Bundle.objects.filter(pk=bundle.pk).update(
                config={**bundle.config, 'payload_path': path.replace('/completed/', '/complete/')})
    Setting = apps.get_model('core', 'Setting')
    for setting in Setting.objects.exclude(config=None).iterator():
        if not isinstance(setting.config, dict):
            continue
        config = _walk(setting.config)
        if config != setting.config:
            Setting.objects.filter(pk=setting.pk).update(config=config)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0053_list_orderby'),
        ('accounts', '0019_ledger_contact_small_sting_accounts'),
        ('ai_assistant', '0013_delete_logs_moved_to_core'),
        ('communications', '0011_is_locked_deleted'),
        ('docs', '0008_is_locked_deleted'),
        ('orgs', '0012_drop_org_type'),
        ('products', '0024_delete_seriallog'),
        ('sync', '0010_is_locked_deleted'),
        ('transactions', '0053_price_level_words'),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
