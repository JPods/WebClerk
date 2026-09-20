"""Clean the receipt model so the transaction base carries it (Bill, 2026-09-19).

Three duplications went away:
  * purchase / workorder FKs  → the base's parent_id + parent_model
  * landed-cost scalars       → the base's allocations envelope, spread by the one engine
  * dt_received as a DateTimeField → UTC epoch ms (Axiom 14)

The vendor, contact and terms the receipt now carries are filled from the purchase
it receives against.
"""
import apps.transactions.models.receipt
from django.db import migrations, models


def forward(apps, schema_editor):
    with schema_editor.connection.cursor() as cur:
        # 1. The parent pointer, from whichever FK was set.
        cur.execute("""
            update receipt
               set parent_id = coalesce(parent_id, purchase_id, workorder_id),
                   parent_model = coalesce(parent_model,
                       case when purchase_id is not null then 'purchase'
                            when workorder_id is not null then 'workorder' end)
             where purchase_id is not null or workorder_id is not null
        """)
        # 2. Landed costs into the allocations envelope.
        cur.execute("""
            update receipt
               set allocations = coalesce(allocations, '{}'::jsonb) || jsonb_build_object(
                     'freight', vendor_invoice_freight,
                     'duty', duty,
                     'handling', handling,
                     'vat', vat,
                     'method', coalesce(nullif(allocation_method, ''), 'value'))
        """)
        # 3. Vendor, contact and terms from the purchase now that the parent is set.
        cur.execute("""
            update receipt r
               set vendor_id = coalesce(r.vendor_id, p.vendor_id),
                   contact_id = coalesce(r.contact_id, p.contact_id),
                   terms = coalesce(r.terms, p.terms),
                   terms_id = coalesce(r.terms_id, p.terms_id)
              from purchases p
             where r.parent_model = 'purchase' and r.parent_id = p.id
        """)


def backward(apps, schema_editor):
    raise RuntimeError("0033 is forward only — restore from the pre-migration dump.")


class Migration(migrations.Migration):
    # The data step writes FK columns; Postgres then refuses to ALTER the table in the
    # same transaction ("pending trigger events"). Each operation commits on its own.
    atomic = False

    dependencies = [
        ('transactions', '0032_receipt_on_transaction_base'),
    ]

    operations = [
        migrations.RunPython(forward, backward),

        # dt_received: timestamptz → UTC epoch ms, in place (Axiom 14).
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='receipt',
                    name='dt_received',
                    field=models.BigIntegerField(blank=True, db_index=True, null=True,
                        help_text='When the goods arrived (UTC epoch ms — Axiom 14)'),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        alter table receipt
                            alter column dt_received drop default,
                            alter column dt_received drop not null,
                            alter column dt_received type bigint
                                using (extract(epoch from dt_received) * 1000)::bigint
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),

        migrations.RemoveField(model_name='receipt', name='purchase'),
        migrations.RemoveField(model_name='receipt', name='workorder'),
        migrations.RemoveField(model_name='receipt', name='vendor_invoice_freight'),
        migrations.RemoveField(model_name='receipt', name='duty'),
        migrations.RemoveField(model_name='receipt', name='handling'),
        migrations.RemoveField(model_name='receipt', name='vat'),
        migrations.RemoveField(model_name='receipt', name='allocation_method'),

        migrations.AlterField(
            model_name='receipt',
            name='allocations',
            field=models.JSONField(blank=True, null=True,
                default=apps.transactions.models.receipt.default_receipt_allocations,
                help_text='Landed costs spread over the lines: freight, duty, handling, vat, method'),
        ),
        migrations.AlterField(
            model_name='receipt',
            name='vendor_invoice_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12,
                help_text="The vendor's claim, as billed. Reconciled against totals.total "
                          "(metadata.vendor_claim) — never the total itself."),
        ),
    ]
