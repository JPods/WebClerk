"""
center_demo_dates — Shift demo-tagged dates to center on today.

Usage:
    python manage.py center_demo_dates              # dry run
    python manage.py center_demo_dates --apply       # apply shifts
    python manage.py center_demo_dates --target 2026-12-01  # center on a specific date

Only touches records tagged as demo data:
  - refs.source = "demo-baseline"   (seed_demo_transactions)
  - refs.demo_source = "demo-baseline"  (seed_demo)

Refuses to run if no demo-tagged records are found (safety gate).
Run after loading demo data so dates always look current.

Each table is shifted independently so its dt_created average lands on
the target date. Line tables inherit the shift from their parent header.
Uses raw SQL to bypass Django signals (avoids totals recalculation errors).
"""
import json
from datetime import datetime, timezone

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Avg, Q


DEMO_SOURCE = 'demo-baseline'

DT_FIELDS = [
    'dt_created', 'dt_modified', 'dt_approved', 'dt_last_used',
    'dt_start', 'dt_deadline', 'dt_expected', 'dt_completed', 'dt_updated',
    'dt_start_original', 'dt_end_original',
]

JSON_FIELDS = [
    'config', 'metadata', 'refs', 'prefs', 'actions', 'comments',
    'impact', 'retrospection', 'action', 'description', 'assigned_to',
    'created_by', 'start_by', 'deadline_by', 'expected_by',
    'completed_by', 'updated_by', 'end_by', 'project_metadata',
]

# Header tables and their line children (lines inherit parent's shift)
TABLE_GROUPS = [
    # (app_label, header_model, [line_models...])
    ('core', 'Action', []),
    ('transactions', 'Proposal', ['ProposalLine']),
    ('transactions', 'Order', ['OrderLine']),
    ('transactions', 'Invoice', ['InvoiceLine']),
    ('transactions', 'Purchase', ['PurchaseLine']),
    ('transactions', 'Payment', []),
    ('transactions', 'WorkOrder', ['WorkOrderLine']),
    ('transactions', 'Requisition', ['RequisitionLine']),
    ('transactions', 'Receipt', ['ReceiptLine']),
]


def _demo_filter():
    """QuerySet filter for demo-tagged records (either tagging convention)."""
    return Q(refs__source=DEMO_SOURCE) | Q(refs__demo_source=DEMO_SOURCE)


def _demo_sql_where():
    """SQL WHERE clause for demo-tagged records in the refs JSON column."""
    return (
        "(refs->>'source' = %s OR refs->>'demo_source' = %s)"
    )


def _demo_sql_params():
    return [DEMO_SOURCE, DEMO_SOURCE]


def _shift_json_dates(obj, shift_ms):
    """Recursively shift epoch-ms values (1.7e12–1.9e12) in a dict/list."""
    changed = False
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (int, float)) and 1_700_000_000_000 < v < 1_900_000_000_000:
                obj[k] = int(v + shift_ms)
                changed = True
            elif isinstance(v, (dict, list)):
                if _shift_json_dates(v, shift_ms):
                    changed = True
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, (int, float)) and 1_700_000_000_000 < v < 1_900_000_000_000:
                obj[i] = int(v + shift_ms)
                changed = True
            elif isinstance(v, (dict, list)):
                if _shift_json_dates(v, shift_ms):
                    changed = True
    return changed


def _get_demo_ids(Model):
    """Return set of PKs for demo-tagged records."""
    return set(Model.objects.filter(_demo_filter()).values_list('pk', flat=True))


def _get_line_ids(LineModel, header_ids, header_fk_field):
    """Return set of line PKs whose parent header is in header_ids."""
    if not header_ids:
        return set()
    return set(
        LineModel.objects.filter(
            **{f'{header_fk_field}__in': header_ids}
        ).values_list('pk', flat=True)
    )


def _shift_table(Model, shift_ms, pk_set, apply=False):
    """Shift date fields on records in pk_set. Returns summary lines."""
    if not pk_set:
        return []
    table = Model._meta.db_table
    model_fields = {f.name: f.column for f in Model._meta.get_fields() if hasattr(f, 'column')}
    results = []
    id_list = list(pk_set)

    # Scalar BigInt fields
    for fname in DT_FIELDS:
        if fname not in model_fields:
            continue
        col = model_fields[fname]
        if apply:
            sql = (f'UPDATE {table} SET {col} = {col} + %s '
                   f'WHERE id = ANY(%s) AND {col} IS NOT NULL AND {col} != 0')
            with connection.cursor() as cursor:
                cursor.execute(sql, [shift_ms, id_list])
                if cursor.rowcount:
                    results.append(f'  {fname}: {cursor.rowcount} rows')
        else:
            sql = (f'SELECT COUNT(*) FROM {table} '
                   f'WHERE id = ANY(%s) AND {col} IS NOT NULL AND {col} != 0')
            with connection.cursor() as cursor:
                cursor.execute(sql, [id_list])
                ct = cursor.fetchone()[0]
                if ct:
                    results.append(f'  {fname}: {ct} rows')

    # JSON envelope fields
    json_cols = [f for f in JSON_FIELDS if f in model_fields]
    if json_cols:
        updated = 0
        for obj in Model.objects.filter(pk__in=pk_set):
            obj_changed = False
            update_vals = {}
            for fname in json_cols:
                val = getattr(obj, fname, None)
                if val and isinstance(val, (dict, list)):
                    if _shift_json_dates(val, shift_ms):
                        obj_changed = True
                        update_vals[fname] = json.dumps(val)
            if obj_changed:
                if apply:
                    set_clause = ', '.join(f'{fname} = %s' for fname in update_vals)
                    sql = f'UPDATE {table} SET {set_clause} WHERE id = %s'
                    with connection.cursor() as cursor:
                        cursor.execute(sql, list(update_vals.values()) + [obj.pk])
                updated += 1
        if updated:
            results.append(f'  JSON envelopes: {updated} rows')

    return results


def _find_header_fk(LineModel, header_name):
    """Find the FK field name on a line model that points to its header."""
    header_name_lower = header_name.lower()
    for f in LineModel._meta.get_fields():
        if hasattr(f, 'related_model') and f.related_model:
            if f.related_model.__name__ == header_name:
                return f.name
    # Fallback: convention-based
    for candidate in [header_name_lower, f'{header_name_lower}_id']:
        if any(mf.name == candidate for mf in LineModel._meta.get_fields()):
            return candidate
    return None


class Command(BaseCommand):
    help = 'Shift demo-tagged dates to center on today (or a target date).'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Apply the shifts (default is dry run)')
        parser.add_argument('--target', type=str, default=None,
                            help='Target center date (YYYY-MM-DD). Default: today.')

    def handle(self, *args, **options):
        apply = options['apply']
        if options['target']:
            target_date = datetime.strptime(options['target'], '%Y-%m-%d').replace(
                hour=12, tzinfo=timezone.utc)
        else:
            target_date = datetime.now(timezone.utc).replace(
                hour=12, minute=0, second=0, microsecond=0)

        target_ms = int(target_date.timestamp() * 1000)
        mode = 'APPLYING' if apply else 'DRY RUN'

        # Safety gate: check that demo data exists somewhere
        total_demo = 0
        for app_label, header_name, _ in TABLE_GROUPS:
            try:
                M = apps.get_model(app_label, header_name)
                total_demo += M.objects.filter(_demo_filter()).count()
            except LookupError:
                pass
        if total_demo == 0:
            self.stderr.write(
                '\nNo demo-tagged records found (refs.source or refs.demo_source '
                f'= "{DEMO_SOURCE}").\n'
                'This command only shifts demo data. Tag records first via '
                'seed_demo / seed_demo_transactions.\n'
            )
            return

        self.stdout.write(f'\n{mode} — centering demo dates on {target_date.date()}')
        self.stdout.write(f'Demo records found: {total_demo}\n')

        for app_label, header_name, line_names in TABLE_GROUPS:
            try:
                HeaderModel = apps.get_model(app_label, header_name)
            except LookupError:
                continue

            header_ids = _get_demo_ids(HeaderModel)
            if not header_ids:
                continue

            avg = HeaderModel.objects.filter(
                pk__in=header_ids
            ).exclude(
                dt_created=0
            ).exclude(
                dt_created=None
            ).aggregate(a=Avg('dt_created'))['a']

            if not avg:
                continue

            shift_ms = int(target_ms - avg)
            shift_days = shift_ms / 1000 / 86400
            current_center = datetime.fromtimestamp(avg / 1000, tz=timezone.utc).date()

            if abs(shift_days) < 0.5:
                self.stdout.write(
                    f'{header_name} ({len(header_ids)} demo): already centered, skip')
                continue

            self.stdout.write(
                f'\n{header_name} ({len(header_ids)} demo records): '
                f'{current_center} → {target_date.date()} ({shift_days:+.1f} days)'
            )
            results = _shift_table(HeaderModel, shift_ms, header_ids, apply=apply)
            for line in results:
                self.stdout.write(line)

            # Line tables: find lines belonging to demo headers
            for line_name in line_names:
                try:
                    LineModel = apps.get_model(app_label, line_name)
                except LookupError:
                    continue

                fk_field = _find_header_fk(LineModel, header_name)
                if not fk_field:
                    self.stderr.write(
                        f'  WARNING: cannot find FK from {line_name} → {header_name}')
                    continue

                line_ids = _get_line_ids(LineModel, header_ids, fk_field)
                if not line_ids:
                    continue

                self.stdout.write(f'  {line_name} ({len(line_ids)} records):')
                results = _shift_table(LineModel, shift_ms, line_ids, apply=apply)
                for line in results:
                    self.stdout.write(f'  {line}')

        self.stdout.write(
            f'\n{"Done." if apply else "Dry run complete. Use --apply to execute."}\n')
