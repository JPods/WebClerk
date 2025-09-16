from django.db import migrations


SQL = r"""
-- Rename 'order_line' key to 'sales_order_line' inside refs.links JSON for sales_orders
UPDATE sales_orders
SET refs = jsonb_set(
    COALESCE(refs, '{}'::jsonb),
    '{links}',
    (
      CASE
        WHEN refs ? 'links' THEN
          (
            CASE
              WHEN (refs->'links') ? 'order_line' THEN
                (refs->'links') - 'sales_order_line' || jsonb_build_object('sales_order_line', refs->'links'->'order_line') - 'order_line'
              ELSE (refs->'links')
            END
          )
        ELSE '{}'::jsonb
      END
    )
)
WHERE TRUE;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("transactions", "0009_parent_ref_id_backfill"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql="""
        -- Reverse: move sales_order_line back to order_line
        UPDATE sales_orders
        SET refs = jsonb_set(
            COALESCE(refs, '{}'::jsonb),
            '{links}',
            (
              CASE
                WHEN refs ? 'links' THEN
                  (
                    CASE
                      WHEN (refs->'links') ? 'sales_order_line' THEN
                        (refs->'links') - 'order_line' || jsonb_build_object('order_line', refs->'links'->'sales_order_line') - 'sales_order_line'
                      ELSE (refs->'links')
                    END
                  )
                ELSE '{}'::jsonb
              END
            )
        )
        WHERE TRUE;
        """),
    ]
