from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("transactions", "0006_align_header_columns"),
    ]

    operations = [
        migrations.RunSQL(
            sql=r"""
            ALTER TABLE IF EXISTS sales_orders
                ADD COLUMN IF NOT EXISTS order_no varchar(64) DEFAULT '';
            ALTER TABLE IF EXISTS invoices
                ADD COLUMN IF NOT EXISTS invoice_no varchar(64) DEFAULT '';
            ALTER TABLE IF EXISTS purchase_orders
                ADD COLUMN IF NOT EXISTS po_no varchar(64) DEFAULT '';
            ALTER TABLE IF EXISTS proposals
                ADD COLUMN IF NOT EXISTS name varchar(128) DEFAULT '';
            """,
            reverse_sql=r"""
            -- Safe reverse: drop columns if exist
            ALTER TABLE IF EXISTS sales_orders DROP COLUMN IF EXISTS order_no;
            ALTER TABLE IF EXISTS invoices DROP COLUMN IF EXISTS invoice_no;
            ALTER TABLE IF EXISTS purchase_orders DROP COLUMN IF EXISTS po_no;
            ALTER TABLE IF EXISTS proposals DROP COLUMN IF EXISTS name;
            """,
        ),
    ]
