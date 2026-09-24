"""security_level is a BaseModel field: an integer on every table.

products_inventoryreservation drifted to varchar(default '') outside the migrations (0001 made it
an IntegerField). Convert it back only where it drifted; on a database built from migrations the
column is already integer and this does nothing. Bill, 2026-09-23: correct and migrate, minimal
time on reservations.
"""
from django.db import migrations

SQL = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'products_inventoryreservation'
          AND column_name = 'security_level' AND data_type <> 'integer'
    ) THEN
        ALTER TABLE products_inventoryreservation ALTER COLUMN security_level DROP DEFAULT;
        UPDATE products_inventoryreservation SET security_level = '0'
            WHERE security_level IS NULL OR security_level !~ '^[0-9]+$';
        ALTER TABLE products_inventoryreservation
            ALTER COLUMN security_level TYPE integer USING security_level::integer;
        ALTER TABLE products_inventoryreservation ALTER COLUMN security_level SET NOT NULL;
    END IF;
END $$;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0014_alter_inventoryreservation_item'),
    ]

    operations = [
        migrations.RunSQL(SQL, reverse_sql=migrations.RunSQL.noop),
    ]
