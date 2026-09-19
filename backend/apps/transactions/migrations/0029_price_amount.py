"""price.extended → price.amount, totals.subtotal → totals.amount (Bill, 2026-09-19).

"amount" at both levels: a line's price.amount is its total before tax, and it
adds into the document's totals.amount. total stays "everything added" (amount +
line taxes + shipping + finance charge + other). No alias.

1. Stored JSON: the key is renamed in every sell line's price and every
   transaction header's totals.
2. Settings and Reports that name the fields: the paths, the panel column name
   and the labels are rewritten.
"""
from django.db import migrations

LINE_TABLES = ('quote_lines', 'order_lines', 'invoice_lines')
HEADER_TABLES = ('quotes', 'orders', 'invoices', 'purchases', 'work_orders', 'receipt')
TEXT_REPLACEMENTS = (
    ('price.extended', 'price.amount'),
    ('totals.subtotal', 'totals.amount'),
    ('lines[].extended', 'lines[].amount'),
    ('"field": "extended"', '"field": "amount"'),
    ('"label": "Extended"', '"label": "Amount"'),
    ('"label": "Subtotal"', '"label": "Amount"'),
    ('"name": "subtotal"', '"name": "amount"'),
)
TEXT_TABLES = ('settings', 'reports')


def _existing(cur, table):
    cur.execute("select 1 from information_schema.tables where table_schema='public' and table_name=%s", [table])
    return cur.fetchone() is not None


def _rename_key(cur, table, column, old, new):
    cur.execute(f"""
        update {table}
           set {column} = ({column} - %s) || jsonb_build_object(%s, {column}->%s)
         where jsonb_typeof({column}) = 'object' and {column} ? %s
    """, [old, new, old, old])


def _rewrite_text(cur, table, pairs):
    cur.execute("""
        select column_name, data_type from information_schema.columns
         where table_schema='public' and table_name=%s and data_type in ('text','character varying','jsonb','json')
    """, [table])
    for column, dtype in cur.fetchall():
        for old, new in pairs:
            if dtype in ('jsonb', 'json'):
                cur.execute(f"""update {table} set {column} = replace({column}::text, %s, %s)::{dtype}
                                where {column}::text like %s""", [old, new, f'%{old}%'])
            else:
                cur.execute(f"""update {table} set {column} = replace({column}, %s, %s)
                                where {column} like %s""", [old, new, f'%{old}%'])


def forwards(apps, schema_editor):
    with schema_editor.connection.cursor() as cur:
        for t in LINE_TABLES:
            if _existing(cur, t):
                _rename_key(cur, t, 'price', 'extended', 'amount')
        for t in HEADER_TABLES:
            if _existing(cur, t):
                _rename_key(cur, t, 'totals', 'subtotal', 'amount')
        for t in TEXT_TABLES:
            if _existing(cur, t):
                _rewrite_text(cur, t, TEXT_REPLACEMENTS)


def backwards(apps, schema_editor):
    with schema_editor.connection.cursor() as cur:
        for t in LINE_TABLES:
            if _existing(cur, t):
                _rename_key(cur, t, 'price', 'amount', 'extended')
        for t in HEADER_TABLES:
            if _existing(cur, t):
                _rename_key(cur, t, 'totals', 'amount', 'subtotal')
        for t in TEXT_TABLES:
            if _existing(cur, t):
                _rewrite_text(cur, t, [(b, a) for a, b in TEXT_REPLACEMENTS])


class Migration(migrations.Migration):
    dependencies = [('transactions', '0028_on_rc')]
    operations = [migrations.RunPython(forwards, backwards)]
