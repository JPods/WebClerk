from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("transactions", "0008_align_line_columns"),
    ]

    operations = [
        migrations.RunSQL(
            sql=r"""
            ALTER TABLE IF EXISTS sales_order_lines ADD COLUMN IF NOT EXISTS parent_ref_id bigint;
            ALTER TABLE IF EXISTS invoice_lines ADD COLUMN IF NOT EXISTS parent_ref_id bigint;
            -- Backfill from parent_id
            UPDATE sales_order_lines SET parent_ref_id = parent_id WHERE parent_ref_id IS NULL;
            UPDATE invoice_lines SET parent_ref_id = parent_id WHERE parent_ref_id IS NULL;
            CREATE INDEX IF NOT EXISTS sol_parent_ref_idx ON sales_order_lines(parent_ref_id);
            CREATE INDEX IF NOT EXISTS invl_parent_ref_idx ON invoice_lines(parent_ref_id);
            """,
            reverse_sql=r"""
            DROP INDEX IF EXISTS sol_parent_ref_idx;
            DROP INDEX IF EXISTS invl_parent_ref_idx;
            ALTER TABLE IF EXISTS sales_order_lines DROP COLUMN IF EXISTS parent_ref_id;
            ALTER TABLE IF EXISTS invoice_lines DROP COLUMN IF EXISTS parent_ref_id;
            """,
        ),
    ]
