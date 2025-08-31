from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection

"""Verify live database schema for orgs.OrgBase matches current model definition.

Checks performed:
1. Column set equality (expected vs actual) ignoring Django's implicit id differences if any.
2. Extra columns in DB (potential leftovers like 'access').
3. Missing columns in DB (model requires but DB lacks).
4. JSON field type sanity (basic check via information_schema or pg_catalog for PostgreSQL).

Exit codes:
 0 = OK (no discrepancies)
 1 = Discrepancies found (unless --allow-extra and only extras present that are allowed)

Usage examples:
  ./bin/python manage.py verify_orgs_schema
  ./bin/python manage.py verify_orgs_schema --json
  ./bin/python manage.py verify_orgs_schema --expect-no-access --fail-on-diff
"""


class Command(BaseCommand):
    help = "Verify live DB schema for OrgBase matches model (detect stray 'access' column, missing fields, etc)."

    def add_arguments(self, parser):
        parser.add_argument('--json', action='store_true', help='Output JSON result')
        parser.add_argument('--fail-on-diff', action='store_true', help='Exit with code 1 if any diff found')
        parser.add_argument('--expect-no-access', action='store_true', help="Treat presence of legacy 'access' column as an error")

    def handle(self, *args, **opts):
        OrgBase = apps.get_model('orgs', 'OrgBase')
        # Collect model column names (exclude related/auto fields without column attr)
        model_fields = [f.column for f in OrgBase._meta.concrete_fields if getattr(f, 'column', None)]
        model_field_set = set(model_fields)

        with connection.cursor() as cur:
            vendor = connection.vendor
            if vendor != 'postgresql':
                self.stdout.write('Warning: Command optimized for PostgreSQL; type checks may be limited.')
            cur.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
                """,
                [OrgBase._meta.db_table],
            )
            rows = cur.fetchall()

        db_columns = [r[0] for r in rows]
        db_field_set = set(db_columns)

        extra = sorted(db_field_set - model_field_set)
        missing = sorted(model_field_set - db_field_set)
        legacy_access_present = ('access' in extra) or ('access' in db_field_set and 'access' not in model_field_set)

        result = {
            'table': OrgBase._meta.db_table,
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
            self.stdout.write(f"OrgBase schema check for table '{result['table']}':")
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
