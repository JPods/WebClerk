"""A receipt line is a child line like any other (Bill, 2026-09-19).

`purchase_line` and `workorder_line` FKs → the base's `parent_line_id`, so the parent
line's `remaining` is recomputed from its children by the one writer instead of a
`quantity['received']` hint that normalize_quantity_map drops.
"""
from django.db import migrations


def forward(apps, schema_editor):
    with schema_editor.connection.cursor() as cur:
        cur.execute("""
            update receipt_line
               set parent_line_id = coalesce(parent_line_id, purchase_line_id, workorder_line_id),
                   refs = coalesce(refs, '{}'::jsonb) || jsonb_build_object('source',
                       -- refs.source may be JSON null, which coalesce does not catch;
                       -- concatenating onto it would build an array, not an object.
                       (case when jsonb_typeof(refs->'source') = 'object'
                             then refs->'source' else '{}'::jsonb end) || case
                           when purchase_line_id is not null
                               then jsonb_build_object('purchase_line_id', purchase_line_id)
                           when workorder_line_id is not null
                               then jsonb_build_object('workorder_line_id', workorder_line_id)
                           else '{}'::jsonb end)
             where purchase_line_id is not null or workorder_line_id is not null
        """)


def backward(apps, schema_editor):
    raise RuntimeError("0034 is forward only — restore from the pre-migration dump.")


class Migration(migrations.Migration):
    atomic = False          # the data step writes an FK column; the drops follow separately

    dependencies = [
        ('transactions', '0033_receipt_cleanup_for_base'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
        migrations.RemoveField(model_name='receiptline', name='purchase_line'),
        migrations.RemoveField(model_name='receiptline', name='workorder_line'),
    ]
