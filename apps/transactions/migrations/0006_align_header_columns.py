from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("transactions", "0005_remove_salesorderline_quantity_invoiced"),
    ]

    operations = [
        migrations.RunSQL(
            sql=r"""
            -- Add missing TransactionBaseModel columns to invoices and sales_orders if they don't exist
            ALTER TABLE IF EXISTS invoices
                ADD COLUMN IF NOT EXISTS status varchar(32) DEFAULT 'planned',
                ADD COLUMN IF NOT EXISTS priority varchar(32),
                ADD COLUMN IF NOT EXISTS price_level varchar(50),
                ADD COLUMN IF NOT EXISTS customer_id bigint DEFAULT 0,
                ADD COLUMN IF NOT EXISTS manufacturer_id bigint DEFAULT 0,
                ADD COLUMN IF NOT EXISTS vendor_id bigint DEFAULT 0;

            ALTER TABLE IF EXISTS sales_orders
                ADD COLUMN IF NOT EXISTS status varchar(32) DEFAULT 'planned',
                ADD COLUMN IF NOT EXISTS priority varchar(32),
                ADD COLUMN IF NOT EXISTS price_level varchar(50),
                ADD COLUMN IF NOT EXISTS customer_id bigint DEFAULT 0,
                ADD COLUMN IF NOT EXISTS manufacturer_id bigint DEFAULT 0,
                ADD COLUMN IF NOT EXISTS vendor_id bigint DEFAULT 0;
            """,
            reverse_sql=r"""
            -- Safe reverse: drop columns if present (no-op if absent)
            ALTER TABLE IF EXISTS invoices
                DROP COLUMN IF EXISTS status,
                DROP COLUMN IF EXISTS priority,
                DROP COLUMN IF EXISTS price_level,
                DROP COLUMN IF EXISTS customer_id,
                DROP COLUMN IF EXISTS manufacturer_id,
                DROP COLUMN IF EXISTS vendor_id;

            ALTER TABLE IF EXISTS sales_orders
                DROP COLUMN IF EXISTS status,
                DROP COLUMN IF EXISTS priority,
                DROP COLUMN IF EXISTS price_level,
                DROP COLUMN IF EXISTS customer_id,
                DROP COLUMN IF EXISTS manufacturer_id,
                DROP COLUMN IF EXISTS vendor_id;
            """,
        ),
    ]
