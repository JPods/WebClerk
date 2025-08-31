from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection
import json

"""Comprehensive live schema verification utility.

Features:
  * Compare model concrete fields vs DB columns (missing / extra)
  * Optional PostgreSQL type comparison (basic mapping)
  * Optional index name presence check (model Meta.indexes vs pg_indexes)
  * Optional check constraint name presence check
  * Filter by app (--app) or single model (--model app_label.ModelName)

Exit codes:
  0 success (no diffs OR diffs allowed)
  1 diffs found and --fail-on-diff specified

Examples:
  ./bin/python manage.py verify_schema --app orgs --types --indexes --constraints --json
  ./bin/python manage.py verify_schema --model orgs.OrgBase --expect-no access --fail-on-diff
  ./bin/python manage.py verify_schema --all --types
"""


PG_TYPE_ALIASES = {
    # django field class name -> acceptable postgres physical types
    'CharField': {'text', 'varchar'},
    'TextField': {'text'},
    'UUIDField': {'uuid'},
    'IntegerField': {'int4'},
    'PositiveIntegerField': {'int4'},
    'BigIntegerField': {'int8'},
    'BigAutoField': {'int8'},
    'AutoField': {'int4'},
    'BooleanField': {'bool'},
    'JSONField': {'jsonb', 'json'},
    'DateTimeField': {'timestamp', 'timestamptz'},
    'DateField': {'date'},
    'FloatField': {'float8', 'float4'},
    'DecimalField': {'numeric'},
}


def _collect_indexes_for_table(table: str):
    with connection.cursor() as cur:
        cur.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = ANY (current_schemas(false))
              AND tablename = %s
        """, [table.split('.')[-1]])
        return {r[0] for r in cur.fetchall()}


def _collect_constraints_for_table(table: str):
    with connection.cursor() as cur:
        cur.execute("""
            SELECT conname
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            JOIN pg_namespace n ON t.relnamespace = n.oid
            WHERE t.relname = %s AND n.nspname = ANY (current_schemas(false))
        """, [table.split('.')[-1]])
        return {r[0] for r in cur.fetchall()}


class Command(BaseCommand):
    help = "Verify live DB schema matches Django models (columns, types, indexes, constraints)."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--app', help='Limit to a single app label')
        group.add_argument('--model', help='Limit to one model (format app_label.ModelName)')
        group.add_argument('--all', action='store_true', help='Scan all concrete models (default if none specified)')
        parser.add_argument('--types', action='store_true', help='Compare PostgreSQL column types')
        parser.add_argument('--indexes', action='store_true', help='Check presence of model-declared index names')
        parser.add_argument('--constraints', action='store_true', help='Check presence of model-declared check constraint names')
        parser.add_argument('--json', action='store_true', help='JSON output')
        parser.add_argument('--fail-on-diff', action='store_true', help='Exit code 1 if any diffs detected')
        parser.add_argument('--ignore-extra', action='store_true', help='Do not treat extra DB columns as diffs')
        parser.add_argument('--ignore-missing', action='store_true', help='Do not treat missing DB columns as diffs')

    def handle(self, *args, **opts):
        vendor = connection.vendor
        if vendor != 'postgresql' and (opts['types'] or opts['indexes'] or opts['constraints']):
            self.stdout.write('Warning: Type / index / constraint checks are tuned for PostgreSQL.')

        target_models = []
        if opts.get('model'):
            try:
                app_label, model_name = opts['model'].split('.', 1)
                target_models = [apps.get_model(app_label, model_name)]
            except Exception as e:  # pragma: no cover
                raise SystemExit(f"Invalid --model value: {e}")
        else:
            for m in apps.get_models():
                if opts.get('app') and m._meta.app_label != opts['app']:
                    continue
                target_models.append(m)
        # If neither model nor app specified, default is all (already collected)

        report = []
        any_diff = False

        for model in target_models:
            table = model._meta.db_table
            # Skip proxy / unmanaged
            if model._meta.proxy or not model._meta.managed:
                continue
            model_cols = [f.column for f in model._meta.concrete_fields if getattr(f, 'column', None)]
            model_set = set(model_cols)
            # Use Django introspection for reliable column listing (avoids accidental
            # leakage of information_schema meta attribute names observed in tests).
            with connection.cursor() as cur:
                description = connection.introspection.get_table_description(cur, table)
                db_cols = [c.name for c in description]
                db_set = set(db_cols)

                rows = []
                if opts['types'] and vendor == 'postgresql':
                    # Separate lightweight query for Postgres physical types.
                    cur.execute(
                        """
                        SELECT column_name, udt_name
                        FROM information_schema.columns
                        WHERE table_name = %s
                        ORDER BY ordinal_position
                        """,
                        [table.split('.')[-1]],
                    )
                    rows = cur.fetchall()
            extra = sorted(db_set - model_set)
            missing = sorted(model_set - db_set)

            type_mismatches = []
            if opts['types'] and vendor == 'postgresql' and rows:
                pg_types = {r[0]: r[1] for r in rows}
                for f in model._meta.concrete_fields:
                    col = f.column
                    db_type = pg_types.get(col)
                    if not db_type:
                        continue
                    expected_set = PG_TYPE_ALIASES.get(f.__class__.__name__)
                    if expected_set and db_type not in expected_set:
                        type_mismatches.append({
                            'column': col,
                            'model_field': f.__class__.__name__,
                            'db_type': db_type,
                            'expected_any_of': sorted(expected_set),
                        })

            index_diffs = {}
            if opts['indexes'] and vendor == 'postgresql':
                declared = {ix.name for ix in getattr(model._meta, 'indexes', [])}
                existing = _collect_indexes_for_table(table)
                missing_idx = sorted(declared - existing)
                extra_idx = sorted(existing - declared)
                if declared:
                    index_diffs = {'missing': missing_idx, 'extra': extra_idx}

            constraint_diffs = {}
            if opts['constraints'] and vendor == 'postgresql':
                declared_c = {c.name for c in getattr(model._meta, 'constraints', []) if hasattr(c, 'name')}
                existing_c = _collect_constraints_for_table(table)
                missing_c = sorted(declared_c - existing_c)
                # We normally ignore extra constraints (could be PK/FK/internal) unless they collide with names
                if declared_c:
                    constraint_diffs = {'missing': missing_c}

            diff = {
                'app': model._meta.app_label,
                'model': model.__name__,
                'table': table,
                'extra_columns': extra,
                'missing_columns': missing,
                'type_mismatches': type_mismatches,
            }
            if index_diffs:
                diff['index_diffs'] = index_diffs
            if constraint_diffs:
                diff['constraint_diffs'] = constraint_diffs

            treat_extra = not opts['ignore_extra'] and extra
            treat_missing = not opts['ignore_missing'] and missing
            has_diff = bool(treat_extra or treat_missing or type_mismatches or (index_diffs and (index_diffs.get('missing'))) or (constraint_diffs and constraint_diffs.get('missing')))
            diff['ok'] = not has_diff
            if has_diff:
                any_diff = True
            report.append(diff)

        if opts['json']:
            self.stdout.write(json.dumps({'results': report}, indent=2))
        else:
            for d in report:
                status = 'OK' if d['ok'] else 'DIFF'
                self.stdout.write(f"[{status}] {d['app']}.{d['model']} table={d['table']}")
                if not d['ok']:
                    if d['extra_columns']:
                        self.stdout.write(f"  extra: {d['extra_columns']}")
                    if d['missing_columns']:
                        self.stdout.write(f"  missing: {d['missing_columns']}")
                    if d['type_mismatches']:
                        for tm in d['type_mismatches'][:10]:
                            self.stdout.write(f"  type! {tm['column']} model={tm['model_field']} db={tm['db_type']} expected_any={tm['expected_any_of']}")
                    if 'index_diffs' in d and d['index_diffs'].get('missing'):
                        self.stdout.write(f"  missing indexes: {d['index_diffs']['missing']}")
                    if 'constraint_diffs' in d and d['constraint_diffs'].get('missing'):
                        self.stdout.write(f"  missing constraints: {d['constraint_diffs']['missing']}")

        if any_diff and opts['fail_on_diff']:
            raise SystemExit(1)
