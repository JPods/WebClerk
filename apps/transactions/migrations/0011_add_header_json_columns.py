from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("transactions", "0010_backfill_sales_order_link_key"),
    ]

    operations = [
        migrations.RunSQL(
            sql=r"""
            -- Align header JSON columns with TransactionBaseModel on invoices and sales_orders
            ALTER TABLE IF EXISTS invoices
                ADD COLUMN IF NOT EXISTS calc jsonb DEFAULT '{}'::jsonb,
                ADD COLUMN IF NOT EXISTS flow jsonb DEFAULT '{}'::jsonb,
                ADD COLUMN IF NOT EXISTS source jsonb DEFAULT '{}'::jsonb,
                ADD COLUMN IF NOT EXISTS action jsonb DEFAULT '{}'::jsonb;

            ALTER TABLE IF EXISTS sales_orders
                ADD COLUMN IF NOT EXISTS calc jsonb DEFAULT '{}'::jsonb,
                ADD COLUMN IF NOT EXISTS flow jsonb DEFAULT '{}'::jsonb,
                ADD COLUMN IF NOT EXISTS source jsonb DEFAULT '{}'::jsonb,
                ADD COLUMN IF NOT EXISTS action jsonb DEFAULT '{}'::jsonb;

            ALTER TABLE IF EXISTS work_orders
                ADD COLUMN IF NOT EXISTS calc jsonb DEFAULT '{}'::jsonb,
                ADD COLUMN IF NOT EXISTS flow jsonb DEFAULT '{}'::jsonb,
                ADD COLUMN IF NOT EXISTS source jsonb DEFAULT '{}'::jsonb,
                ADD COLUMN IF NOT EXISTS action jsonb DEFAULT '{}'::jsonb;
            """,
            reverse_sql=r"""
            ALTER TABLE IF EXISTS invoices
                DROP COLUMN IF EXISTS calc,
                DROP COLUMN IF EXISTS flow,
                DROP COLUMN IF EXISTS source,
                DROP COLUMN IF EXISTS action;

            ALTER TABLE IF NOT EXISTS sales_orders
                DROP COLUMN IF EXISTS calc,
                DROP COLUMN IF EXISTS flow,
                DROP COLUMN IF EXISTS source,
                DROP COLUMN IF EXISTS action;

            ALTER TABLE IF NOT EXISTS work_orders
                DROP COLUMN IF EXISTS calc,
                DROP COLUMN IF EXISTS flow,
                DROP COLUMN IF EXISTS source,
                DROP COLUMN IF EXISTS action;
            """,
        ),
    ]
