"""Settings and Reports follow terms as text (Bill, 2026-10-22: "Terms as text, yes. Users
will not think in terms of FK for terms.").

The FKs left in accounts 0018 / orgs 0011 / transactions 0051. What named them:
  - 'terms_fk' / 'terms_fk_id' — the org and document FK — as a list entry, a dict key
    or a layout field object ({"field": "terms_fk", ...}) in wc:model Settings and form
    Reports. Removed.
  - 'term' / 'term_id' — the cash and ledger FK — in the cash and ledger definitions.
    'term' is renamed 'terms', 'term_id' removed; the stored 'lookup' behavior is dropped
    (there is nothing to look up).
  - a stored 'terms' select behavior: a static list (net_30, ...) that no Term ida ever
    matched, and an override wins over the live list. Dropped, so the options come from
    the Term records (value = ida) as field_behaviors builds them.
"""
from django.db import migrations

GONE = {'terms_fk', 'terms_fk_id'}
RENAME_IN = {'cash', 'ledger'}                       # wc:model parent_model
RENAME_REPORTS = {'FORM-CASH', 'FORM-LEDGER'}


def is_field(value, name):
    return isinstance(value, dict) and value.get('field') == name


def prune(value):
    if isinstance(value, dict):
        return {k: prune(v) for k, v in value.items() if k not in GONE}
    if isinstance(value, list):
        return [prune(v) for v in value
                if not (isinstance(v, str) and v in GONE) and not any(is_field(v, name) for name in GONE)]
    return value


def rename(value):
    if isinstance(value, dict):
        if is_field(value, 'term'):
            value = {**value, 'field': 'terms', **({'label': 'terms'} if value.get('label') == 'term' else {})}
        return {('terms' if k == 'term' else k): rename(v) for k, v in value.items() if k != 'term_id'}
    if isinstance(value, list):
        return ['terms' if v == 'term' else rename(v) for v in value
                if v != 'term_id' and not is_field(v, 'term_id')]
    return value


def drop_behaviors(config, renamed):
    behaviors = config.get('behaviors') if isinstance(config, dict) else None
    if not isinstance(behaviors, dict):
        return config
    kept = {k: v for k, v in behaviors.items()
            if not ((k == 'term' and renamed) or (k == 'terms' and isinstance(v, dict) and v.get('type') == 'select'))}
    return {**config, 'behaviors': kept} if kept != behaviors else config


def leaves(config, renamed):
    config = drop_behaviors(prune(config), renamed)
    return rename(config) if renamed else config


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for pk, purpose, parent_model, config in (Setting.objects.filter(config__icontains='term')
                                              .values_list('pk', 'purpose', 'parent_model', 'config')
                                              .iterator()):
        new = leaves(config, purpose == 'wc:model' and parent_model in RENAME_IN)
        if new != config:
            Setting.objects.filter(pk=pk).update(config=new)
    Report = apps.get_model('core', 'Report')
    for pk, ida, config in (Report.objects.filter(config__icontains='term')
                            .values_list('pk', 'ida', 'config').iterator()):
        new = leaves(config, ida in RENAME_REPORTS)
        if new != config:
            Report.objects.filter(pk=pk).update(config=new)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_dd_card_unassigned_emails'),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
