from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("transactions", "0011_add_header_json_columns"),
    ]

    operations = [
        migrations.RunSQL(
            sql=r"""
            ALTER TABLE IF EXISTS invoices DROP COLUMN IF EXISTS invoice_no;
            """,
            reverse_sql=r"""
            ALTER TABLE IF EXISTS invoices ADD COLUMN IF NOT EXISTS invoice_no varchar(64) DEFAULT '';
            """,
        ),
    ]
