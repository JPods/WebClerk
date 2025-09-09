from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection
from apps.core.services.wcapi_registry import to_model_name


class Command(BaseCommand):
    help = "Verify live DB schema for OrgBase matches model (detect stray 'access' column, missing fields, etc)."

    def add_arguments(self, parser):
        parser.add_argument('--json', action='store_true', help='Output JSON result')
        parser.add_argument('--fail-on-diff', action='store_true', help='Exit with code 1 if any diff found')
        parser.add_argument('--expect-no-access', action='store_true',
                            help="Treat presence of legacy 'access' column as an error")

    def handle(self, *args, **opts):
        OrgBase = apps.get_model('orgs', 'OrgBase')
        model_key = OrgBase._meta.db_table          # physical table (plural)
        model_name = to_model_name(model_key) or (model_key[:-1] if model_key.endswith('s') else model_key)

        # Collect model column names
        model_fields = [
            f.column for f in OrgBase._meta.concrete_fields
            if getattr(f, 'column', None)
        ]
        model_field_set = set(model_fields)

        # Query PostgreSQL system catalogs (no information_schema.table-name usage)
        with connection.cursor() as cur:
            if connection.vendor != 'postgresql':
                self.stdout.write('Warning: Optimized for PostgreSQL; results may vary on other vendors.')
            # c.relname matches physical db_table (model_key), not model_name.
            cur.execute(
                """
                SELECT a.attname AS column_name,
                       format_type(a.atttypid, a.atttypmod) AS data_type
                FROM pg_attribute a
                JOIN pg_class c ON a.attrelid = c.oid
                JOIN pg_namespace n ON c.relnamespace = n.oid
                WHERE c.relkind = 'r'
                  AND c.relname = %s
                  AND n.nspname = ANY (current_schemas(false))
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                ORDER BY a.attnum
                """,
                [model_key],
            )
            rows = cur.fetchall()

        db_columns = [r[0] for r in rows]
        db_field_set = set(db_columns)

        extra = sorted(db_field_set - model_field_set)
        missing = sorted(model_field_set - db_field_set)
        legacy_access_present = (
            'access' in extra
            or ('access' in db_field_set and 'access' not in model_field_set)
        )

        result = {
            'model_key': model_key,
            'model_name': model_name,
            'model_fields': sorted(model_field_set),
            'db_columns': db_columns,
            'extra_columns': extra,
            'missing_columns': missing,
            'legacy_access_present': legacy_access_present,
            'ok': (not missing) and (not extra or (extra == ['access'] and not opts['expect_no_access'])),
        }

        if opts['json']:
            import json
            self.stdout.write(json.dumps(result, indent=2))
        else:
            self.stdout.write(
                f"OrgBase schema check for model '{result['model_name']}' (key='{result['model_key']}'):"
            )
            if result['ok']:
                self.stdout.write('  OK: schema matches model.')
            else:
                if missing:
                    self.stdout.write(f"  MISSING columns: {missing}")
                if extra:
                    self.stdout.write(f"  EXTRA columns: {extra}")
                if legacy_access_present:
                    self.stdout.write("  Legacy 'access' column still present.")

        if (not result['ok']) and opts['fail-on-diff']:
            raise SystemExit(1)
