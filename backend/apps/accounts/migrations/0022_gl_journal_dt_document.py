from django.db import migrations, models


# A GL row carries the period it belongs to as well as the moment it was posted (Bill,
# 2026-11-27: "dt_created will be best. It is simple."): dt_document is its document's
# dt_created. Rows already posted take theirs here; a row whose document is gone, or that
# never had one (a manual entry, an adjustment), keeps the time it was posted.
DOCUMENTS = {'invoice': 'Invoice', 'cash': 'Cash', 'receipt': 'Receipt',
             'workorder': 'WorkOrder', 'purchase': 'Purchase'}


def backfill(apps, schema_editor):
    GlJournal = apps.get_model('accounts', 'GlJournal')
    for source_model in GlJournal.objects.values_list('source_model', flat=True).distinct():
        name = DOCUMENTS.get((source_model or '').removesuffix('_reversal'))
        rows = GlJournal.objects.filter(source_model=source_model, dt_document=0)
        if name:
            Document = apps.get_model('transactions', name)
            ids = set(rows.values_list('source_id', flat=True)) - {None}
            for pk, created in Document.objects.filter(pk__in=ids).values_list('pk', 'dt_created'):
                if created:
                    rows.filter(source_id=pk).update(dt_document=created)
    GlJournal.objects.filter(dt_document=0, dt_journaled__gt=0).update(dt_document=models.F('dt_journaled'))
    GlJournal.objects.filter(dt_document=0).update(dt_document=models.F('dt_created'))


def with_document_date(node, key=''):
    """The journal definition's config with dt_document beside dt_journaled wherever a list
    names it (access sets, role lists, form, card, detail), and beside dt_created in the list's
    columns. A list that already names dt_document is left alone. Frozen here."""
    if isinstance(node, dict):
        return {k: with_document_date(v, k) for k, v in node.items()}
    if not isinstance(node, list):
        return node
    out = [with_document_date(v) for v in node]
    if any(v == 'dt_document' or (isinstance(v, dict) and v.get('field') == 'dt_document') for v in out):
        return out
    beside = 'dt_created' if key == 'columns' else 'dt_journaled'
    for i, v in enumerate(out):
        if v == beside:
            return out[:i + 1] + ['dt_document'] + out[i + 1:]
        if isinstance(v, dict) and v.get('field') == beside:
            twin = {**v, 'field': 'dt_document', 'label': 'dt_document'}
            return out[:i + 1] + [twin] + out[i + 1:]
    return out


def name_it_in_the_definition(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for setting in Setting.objects.filter(purpose='wc:model', parent_model='gl_journal'):
        config = with_document_date(setting.config or {})
        if config != setting.config:
            Setting.objects.filter(pk=setting.pk).update(config=config)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0021_unallocated_receipt_account'),
        ('transactions', '0063_receipt_freight_label'),
        ('core', '0076_role_employee_becomes_support'),
    ]

    operations = [
        migrations.AddField(
            model_name='gljournal',
            name='dt_document',
            field=models.BigIntegerField(db_index=True, default=0, help_text="UTC epoch ms of the source document's dt_created; the row's reporting period."),
        ),
        migrations.RunPython(backfill, migrations.RunPython.noop),
        migrations.RunPython(name_it_in_the_definition, migrations.RunPython.noop),
    ]
