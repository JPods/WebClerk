"""line.totals and header allocations (Bill, 2026-09-19: "suffer now; align while we have no users").

Every line gets a totals envelope, the results of the line math, and the header's
totals.X is Σ line.totals.X. Document-level inputs (a discount, shipping, landed
costs) live in the header's allocations and are spread over the lines by amount.

Existing lines are seeded from the values already stored (price.amount or
cost.extended, cost.extended, tax.sales, price.discount_amount), so documents that
are journalized, which the engine may not recompute, still show their numbers.
backfill_totals then recomputes every document that is not locked.
"""
from django.db import migrations, models

LINES = ('quoteline', 'orderline', 'invoiceline', 'purchaseline', 'workorderline',
         'requisitionline', 'receiptline')
HEADERS = ('quote', 'order', 'invoice', 'purchase', 'workorder')
SELL_LINE_TABLES = ('quote_lines', 'order_lines', 'invoice_lines')
EXEC_LINE_TABLES = ('purchase_lines', 'work_order_lines', 'requisition_lines', 'receipt_line')


def seed(apps, schema_editor):
    n = lambda path: f"coalesce(nullif({path}, '')::numeric, 0)"
    with schema_editor.connection.cursor() as cur:
        for t in SELL_LINE_TABLES:
            cur.execute(f"""
                update {t} set totals = jsonb_build_object(
                    'amount',   {n("price->>'amount'")},
                    'discount', {n("price->>'discount_amount'")},
                    'tax',      {n("tax->>'sales'")},
                    'cost',     {n("cost->>'extended'")},
                    'margin',   {n("price->>'amount'")} - {n("cost->>'extended'")},
                    'total',    {n("price->>'amount'")} + {n("tax->>'sales'")},
                    'seeded',   true)
                where totals is null or totals = '{{}}'::jsonb
            """)
        for t in EXEC_LINE_TABLES:
            cur.execute(f"select 1 from information_schema.columns where table_name=%s and column_name='totals'", [t])
            if not cur.fetchone():
                continue
            cur.execute(f"""
                update {t} set totals = jsonb_build_object(
                    'amount', {n("cost->>'extended'")},
                    'cost',   {n("cost->>'extended'")},
                    'total',  {n("cost->>'extended'")},
                    'seeded', true)
                where totals is null or totals = '{{}}'::jsonb
            """)


def strip_results(apps, schema_editor):
    """Results now live in line.totals only: drop them from the input envelopes."""
    with schema_editor.connection.cursor() as cur:
        for t in SELL_LINE_TABLES:
            cur.execute(f"update {t} set price = price - 'amount' where jsonb_typeof(price)='object' and price ? 'amount'")
        for t in SELL_LINE_TABLES + EXEC_LINE_TABLES:
            cur.execute("select 1 from information_schema.tables where table_name=%s", [t])
            if not cur.fetchone():
                continue
            cur.execute(f"update {t} set cost = cost - 'extended' where jsonb_typeof(cost)='object' and cost ? 'extended'")
            cur.execute(f"update {t} set tax = tax - 'sales' where jsonb_typeof(tax)='object' and tax ? 'sales'")
            cur.execute(f"""update {t} set tax = tax - 'rate_source'
                            where jsonb_typeof(tax)='object' and tax ? 'rate_source' and tax->>'rate_source' <> 'line'""")


def rewrite_paths(apps, schema_editor):
    """Settings and Reports that name a line result now name line totals."""
    pairs = (('price.amount', 'totals.amount'), ('cost.extended', 'totals.cost'))
    with schema_editor.connection.cursor() as cur:
        for table in ('settings', 'reports'):
            cur.execute("""select column_name, data_type from information_schema.columns
                           where table_schema='public' and table_name=%s
                             and data_type in ('text','character varying','jsonb','json')""", [table])
            for column, dtype in cur.fetchall():
                for old, new in pairs:
                    cast = f'::{dtype}' if dtype in ('jsonb', 'json') else ''
                    text = f'{column}::text' if cast else column
                    cur.execute(f"update {table} set {column} = replace({text}, %s, %s){cast} where {text} like %s",
                                [old, new, f'%{old}%'])


class Migration(migrations.Migration):
    dependencies = [('transactions', '0029_price_amount')]
    operations = [
        *[migrations.AddField(model_name=m, name='totals',
                              field=models.JSONField(blank=True, default=dict, null=True)) for m in LINES],
        *[migrations.AddField(model_name=m, name='allocations',
                              field=models.JSONField(blank=True, default=dict, null=True)) for m in HEADERS],
        migrations.RunPython(seed, migrations.RunPython.noop),
        migrations.RunPython(strip_results, migrations.RunPython.noop),
        migrations.RunPython(rewrite_paths, migrations.RunPython.noop),
    ]
