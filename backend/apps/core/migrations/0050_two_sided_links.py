"""Two-sided links across all models (Bill, 2026-10-31: "any and all models can be related to
each other via .refs.links").

1. An action's refs.links is the open map every model has: its company set ``all`` lists
   ``refs.links`` in place of the Gantt-only leaves (refs.links.children.id, …); a set outside
   roles see keeps none — untyped data is not shown outside the company.
2. Each link stored on one side only is written on the other (reciprocal_links.keep).
"""
from django.db import migrations


def open_action_links(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model', parent_model='action'):
        config = dict(s.config or {})
        access = dict(config.get('access') or {})
        sets = dict(access.get('sets') or {})
        changed = False
        for name, leaves in sets.items():
            if not isinstance(leaves, list):
                continue
            # The company's own set takes the open map; a set outside roles see may not hold
            # untyped data (access validation), so it keeps no links at all — as on every model.
            kept = [p for p in leaves if not (isinstance(p, str) and p.startswith('refs.links'))]
            if name == 'all':
                kept.append('refs.links')
            if kept != leaves:
                sets[name] = kept
                changed = True
        if changed:
            access['sets'] = sets
            config['access'] = access
            Setting.objects.filter(pk=s.pk).update(config=config)


def backfill(apps, schema_editor):
    """Only id, refs (and an org's type) are read: a migration runs before later migrations
    add other columns, and a deferred field on some models reloads itself without end."""
    from types import SimpleNamespace
    from django.apps import apps as live
    from apps.core.services import reciprocal_links as rl
    from apps.core.services.door import resolve_model

    # A model with no table yet (a test's own model) has nothing to backfill.
    tables = set(schema_editor.connection.introspection.table_names())
    for model_cls in live.get_models():
        if model_cls._meta.proxy or not any(f.name == 'refs' for f in model_cls._meta.concrete_fields):
            continue
        if model_cls._meta.db_table not in tables:
            continue
        is_org = model_cls._meta.model_name == 'orgbase'
        if not is_org:
            try:
                key = resolve_model(model_cls._meta.model_name)[1]
            except Exception:  # noqa: BLE001 - not a wcapi model
                continue
        cols = ['id', 'refs'] + (['org_type'] if is_org else [])
        for row in model_cls.objects.exclude(refs__links={}).exclude(refs__links=None).values(*cols).iterator():
            rl.keep(row['org_type'] if is_org else key, {}, SimpleNamespace(pk=row['id'], refs=row['refs']))


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0049_edit_in_list'),
    ]

    operations = [
        migrations.RunPython(open_action_links, migrations.RunPython.noop),
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
