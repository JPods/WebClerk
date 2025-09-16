from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("transactions", "0007_add_header_identifiers"),
    ]

    operations = [
        migrations.RunSQL(
            sql=r"""
            -- Add missing baseline columns to sales_order_lines
            ALTER TABLE IF EXISTS sales_order_lines
                ADD COLUMN IF NOT EXISTS price_level varchar(50),
                ADD COLUMN IF NOT EXISTS status varchar(50);

            -- Add missing baseline columns to invoice_lines
            ALTER TABLE IF EXISTS invoice_lines
                ADD COLUMN IF NOT EXISTS price_level varchar(50),
                ADD COLUMN IF NOT EXISTS status varchar(50);
            """,
            reverse_sql=r"""
            ALTER TABLE IF EXISTS sales_order_lines
                DROP COLUMN IF EXISTS price_level,
                DROP COLUMN IF EXISTS status;

            ALTER TABLE IF EXISTS invoice_lines
                DROP COLUMN IF EXISTS price_level,
                DROP COLUMN IF EXISTS status;
            """,
        ),
    ]
