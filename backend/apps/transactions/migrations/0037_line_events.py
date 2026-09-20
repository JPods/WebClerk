"""What happens to a workorder line lives on the line (Bill, 2026-09-20).

A document line is something a person sends to someone. A change event is not sent
anywhere — it is what happened to this line. So WorkOrderCompletion rows become
``workorder_line.events[]``, appended by the pending applier so the movement and the
record of it are one apply under one lock.
"""
from django.db import migrations, models

import apps.transactions.models.workorder_line


def forward(apps, schema_editor):
    """Carry any completion rows onto their line as events."""
    with schema_editor.connection.cursor() as cur:
        cur.execute("""
            select to_regclass('workorder_completion') is not null
        """)
        if not cur.fetchone()[0]:
            return
        cur.execute("""
            update work_order_lines l
               set events = coalesce(l.events, '[]'::jsonb) || sub.events
              from (
                select c.parent_line_id as line_id,
                       jsonb_agg(jsonb_build_object(
                           'id', md5(c.id::text || c.dt_created::text),
                           'kind', 'completion',
                           'dt', c.dt_created,
                           'by', coalesce(c.metadata->'count'->>'counted_by', ''),
                           'qty', coalesce((c.quantity->>'active')::numeric, 0),
                           'warehouse_id', c.warehouse_id,
                           'lot', c.lot,
                           'serial_batch', c.serial_batch,
                           'layer_id', c.inventory_layer_id,
                           'unit_cost', (c.cost->>'unit')::numeric
                       ) order by c.id) as events
                  from workorder_completion c
                 where c.parent_line_id is not null
                 group by c.parent_line_id
              ) sub
             where l.id = sub.line_id
        """)


def backward(apps, schema_editor):
    raise RuntimeError("0037 is forward only — restore from the pre-migration dump.")


class Migration(migrations.Migration):
    atomic = False          # the data step writes jsonb; the table drop follows separately

    dependencies = [
        ('transactions', '0036_workorder_kind'),
    ]

    operations = [
        migrations.AddField(
            model_name='workorderline',
            name='events',
            field=models.JSONField(
                blank=True,
                default=apps.transactions.models.workorder_line.default_events,
                help_text='What happened to this line: completions and counts, each an event',
            ),
        ),
        migrations.RunPython(forward, backward),
        migrations.DeleteModel(name='WorkOrderCompletion'),
    ]
