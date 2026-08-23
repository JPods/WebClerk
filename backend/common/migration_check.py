"""
Migration Mismatch Checker — Compare schema state between two databases.

Compares the django_migrations table across two PostgreSQL databases to
detect schema drift before data sync.  Designed to run as a pre-flight
check in sync_model, sync_database, or write-through mode.

Usage:
    from common.migration_check import check_migration_parity

    report = check_migration_parity('_sync_local', '_sync_remote')
    if not report.ok:
        for err in report.errors:
            print(err)

Three check levels:
  1. Missing migrations   — applied on one side but not the other
  2. Unapplied migrations — migration files exist locally but haven't been
                            applied to one of the databases
  3. Table-level drift     — tables that exist in one DB but not the other
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from django.apps import apps
from django.db import connections

logger = logging.getLogger('wcapi.migration_check')


# ── Data classes ────────────────────────────────────────────────────


@dataclass
class MigrationEntry:
    """A single row from django_migrations."""
    app: str
    name: str
    applied: str  # timestamp string


@dataclass
class MigrationReport:
    """Result of comparing migration states between two databases."""

    # True when schemas are fully aligned
    ok: bool = True

    # Human-readable error/warning messages
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Detailed breakdown
    local_only: List[Tuple[str, str]] = field(default_factory=list)   # (app, name)
    remote_only: List[Tuple[str, str]] = field(default_factory=list)  # (app, name)
    tables_local_only: List[str] = field(default_factory=list)
    tables_remote_only: List[str] = field(default_factory=list)

    # Summary counts
    local_count: int = 0
    remote_count: int = 0

    def as_dict(self) -> dict:
        """Serializable summary for Bundle.conflicts or JSON logging."""
        return {
            'ok': self.ok,
            'errors': self.errors,
            'warnings': self.warnings,
            'local_migration_count': self.local_count,
            'remote_migration_count': self.remote_count,
            'local_only_migrations': [f"{a}.{n}" for a, n in self.local_only],
            'remote_only_migrations': [f"{a}.{n}" for a, n in self.remote_only],
            'tables_local_only': self.tables_local_only,
            'tables_remote_only': self.tables_remote_only,
        }

    def format_report(self, *, color: bool = True) -> str:
        """Format a human-readable report suitable for terminal output."""
        lines = []

        if self.ok:
            lines.append("  ✓ Migration parity OK  "
                         f"(local={self.local_count}, remote={self.remote_count})")
            if self.warnings:
                for w in self.warnings:
                    lines.append(f"  ⚠ {w}")
            return '\n'.join(lines)

        lines.append(f"  ✗ Migration MISMATCH  "
                     f"(local={self.local_count}, remote={self.remote_count})")
        lines.append("")

        if self.local_only:
            lines.append(f"  Migrations applied LOCALLY only ({len(self.local_only)}):")
            for app, name in self.local_only[:20]:
                lines.append(f"    ▸ {app} / {name}")
            if len(self.local_only) > 20:
                lines.append(f"    … and {len(self.local_only) - 20} more")
            lines.append("")

        if self.remote_only:
            lines.append(f"  Migrations applied on REMOTE only ({len(self.remote_only)}):")
            for app, name in self.remote_only[:20]:
                lines.append(f"    ▸ {app} / {name}")
            if len(self.remote_only) > 20:
                lines.append(f"    … and {len(self.remote_only) - 20} more")
            lines.append("")

        if self.tables_local_only:
            lines.append(f"  Tables in LOCAL only ({len(self.tables_local_only)}):")
            for t in self.tables_local_only[:20]:
                lines.append(f"    ▸ {t}")
            if len(self.tables_local_only) > 20:
                lines.append(f"    … and {len(self.tables_local_only) - 20} more")
            lines.append("")

        if self.tables_remote_only:
            lines.append(f"  Tables in REMOTE only ({len(self.tables_remote_only)}):")
            for t in self.tables_remote_only[:20]:
                lines.append(f"    ▸ {t}")
            if len(self.tables_remote_only) > 20:
                lines.append(f"    … and {len(self.tables_remote_only) - 20} more")
            lines.append("")

        for err in self.errors:
            lines.append(f"  ERROR: {err}")

        return '\n'.join(lines)


# ── Internal helpers ────────────────────────────────────────────────


def _fetch_migrations(db_alias: str) -> Set[Tuple[str, str]]:
    """Fetch the set of (app, name) tuples from django_migrations."""
    sql = "SELECT app, name FROM django_migrations ORDER BY app, name"
    try:
        with connections[db_alias].cursor() as cursor:
            cursor.execute(sql)
            return {(row[0], row[1]) for row in cursor.fetchall()}
    except Exception as exc:
        logger.warning("Could not read django_migrations from '%s': %s", db_alias, exc)
        raise


def _fetch_tables(db_alias: str) -> Set[str]:
    """Fetch the set of user table names from the public schema."""
    sql = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """
    try:
        with connections[db_alias].cursor() as cursor:
            cursor.execute(sql)
            return {row[0] for row in cursor.fetchall()}
    except Exception as exc:
        logger.warning("Could not read table list from '%s': %s", db_alias, exc)
        raise


def _fetch_column_map(db_alias: str) -> Dict[str, Set[str]]:
    """
    Fetch {table_name: {col1, col2, …}} for every table in the public schema.

    Used for column-level drift detection between databases.
    """
    sql = """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """
    result: Dict[str, Set[str]] = {}
    try:
        with connections[db_alias].cursor() as cursor:
            cursor.execute(sql)
            for table, col in cursor.fetchall():
                result.setdefault(table, set()).add(col)
    except Exception as exc:
        logger.warning("Could not read column info from '%s': %s", db_alias, exc)
        raise
    return result


# ── Public API ──────────────────────────────────────────────────────


def check_migration_parity(
    local_alias: str,
    remote_alias: str,
    *,
    include_tables: bool = True,
    include_columns: bool = False,
    skip_apps: Optional[Set[str]] = None,
) -> MigrationReport:
    """
    Compare migration state between two database connections.

    Args:
        local_alias:     Django DB alias for the local database.
        remote_alias:    Django DB alias for the remote database.
        include_tables:  Also compare table-level existence (default True).
        include_columns: Also compare column-level drift (default False, slower).
        skip_apps:       Set of app labels to ignore (e.g. {'contenttypes', 'sessions'}).

    Returns:
        MigrationReport with ok=True when schemas are aligned.
    """
    report = MigrationReport()
    skip = skip_apps or set()

    # ── 1. Compare migrations ───────────────────────────────────────
    try:
        local_migs = _fetch_migrations(local_alias)
        remote_migs = _fetch_migrations(remote_alias)
    except Exception as exc:
        report.ok = False
        report.errors.append(f"Could not read migrations: {exc}")
        return report

    # Filter out skipped apps
    if skip:
        local_migs = {(a, n) for a, n in local_migs if a not in skip}
        remote_migs = {(a, n) for a, n in remote_migs if a not in skip}

    report.local_count = len(local_migs)
    report.remote_count = len(remote_migs)

    local_only = sorted(local_migs - remote_migs)
    remote_only = sorted(remote_migs - local_migs)

    if local_only:
        report.ok = False
        report.local_only = local_only
        report.errors.append(
            f"{len(local_only)} migration(s) applied locally but missing on remote. "
            "Run 'python manage.py migrate' on the remote database, or roll back "
            "local migrations before syncing."
        )

    if remote_only:
        report.ok = False
        report.remote_only = remote_only
        report.errors.append(
            f"{len(remote_only)} migration(s) applied on remote but missing locally. "
            "Pull the latest migration files and run 'python manage.py migrate' locally."
        )

    # ── 2. Compare tables ───────────────────────────────────────────
    if include_tables:
        try:
            local_tables = _fetch_tables(local_alias)
            remote_tables = _fetch_tables(remote_alias)
        except Exception as exc:
            report.warnings.append(f"Could not compare tables: {exc}")
            return report

        # Exclude Django internals that may legitimately differ
        _IGNORE_TABLES = {
            'django_migrations', 'django_session', 'django_admin_log',
            'django_content_type', 'auth_permission',
        }
        local_tables -= _IGNORE_TABLES
        remote_tables -= _IGNORE_TABLES

        tbl_local_only = sorted(local_tables - remote_tables)
        tbl_remote_only = sorted(remote_tables - local_tables)

        if tbl_local_only:
            report.tables_local_only = tbl_local_only
            report.warnings.append(
                f"{len(tbl_local_only)} table(s) exist locally but not on remote: "
                + ', '.join(tbl_local_only[:5])
                + (f' … +{len(tbl_local_only) - 5} more' if len(tbl_local_only) > 5 else '')
            )

        if tbl_remote_only:
            report.tables_remote_only = tbl_remote_only
            report.warnings.append(
                f"{len(tbl_remote_only)} table(s) exist on remote but not locally: "
                + ', '.join(tbl_remote_only[:5])
                + (f' … +{len(tbl_remote_only) - 5} more' if len(tbl_remote_only) > 5 else '')
            )

    # ── 3. Column-level drift (opt-in, slower) ──────────────────────
    if include_columns:
        try:
            local_cols = _fetch_column_map(local_alias)
            remote_cols = _fetch_column_map(remote_alias)
        except Exception as exc:
            report.warnings.append(f"Could not compare columns: {exc}")
            return report

        # Only compare tables that exist on both sides
        common_tables = set(local_cols.keys()) & set(remote_cols.keys())
        col_diffs = []
        for table in sorted(common_tables):
            lcols = local_cols[table]
            rcols = remote_cols[table]
            local_extra = sorted(lcols - rcols)
            remote_extra = sorted(rcols - lcols)
            if local_extra or remote_extra:
                col_diffs.append({
                    'table': table,
                    'local_only': local_extra,
                    'remote_only': remote_extra,
                })

        if col_diffs:
            report.ok = False
            count = len(col_diffs)
            report.errors.append(
                f"Column-level drift in {count} table(s). "
                "Migrations are likely out of sync."
            )
            for diff in col_diffs[:10]:
                t = diff['table']
                if diff['local_only']:
                    report.warnings.append(
                        f"  {t}: columns LOCAL only → {', '.join(diff['local_only'])}"
                    )
                if diff['remote_only']:
                    report.warnings.append(
                        f"  {t}: columns REMOTE only → {', '.join(diff['remote_only'])}"
                    )

    return report


def check_migration_parity_for_model(
    model_cls,
    local_alias: str,
    remote_alias: str,
) -> MigrationReport:
    """
    Check migration parity for a single model's app only.

    Faster than a full check — useful before syncing a single model.
    """
    app_label = model_cls._meta.app_label
    report = check_migration_parity(
        local_alias, remote_alias,
        include_tables=False,
        include_columns=False,
    )

    # Filter to only this app's discrepancies
    report.local_only = [(a, n) for a, n in report.local_only if a == app_label]
    report.remote_only = [(a, n) for a, n in report.remote_only if a == app_label]

    # Re-evaluate ok status based on filtered results
    if not report.local_only and not report.remote_only:
        report.ok = True
        report.errors = []
    else:
        report.ok = False
        report.errors = []
        if report.local_only:
            report.errors.append(
                f"{len(report.local_only)} migration(s) for '{app_label}' applied locally "
                f"but missing on remote."
            )
        if report.remote_only:
            report.errors.append(
                f"{len(report.remote_only)} migration(s) for '{app_label}' applied on remote "
                f"but missing locally."
            )

    # Check that the model's table exists on both sides
    table = model_cls._meta.db_table
    for alias, label in [(local_alias, 'LOCAL'), (remote_alias, 'REMOTE')]:
        try:
            tables = _fetch_tables(alias)
            if table not in tables:
                report.ok = False
                report.errors.append(
                    f"Table '{table}' does not exist on {label}. "
                    f"Run 'python manage.py migrate {app_label}' on {label}."
                )
        except Exception as exc:
            report.warnings.append(f"Could not check tables on {label}: {exc}")

    return report


def format_remediation(report: MigrationReport) -> str:
    """
    Generate actionable remediation steps for a failed migration check.

    Returns a multi-line string with numbered steps.
    """
    if report.ok:
        return "  No action needed — schemas are in sync."

    steps = []
    step = 1

    if report.remote_only:
        steps.append(
            f"  {step}. Pull latest migration files from version control:\n"
            f"        git pull origin main\n"
            f"     Then apply them locally:\n"
            f"        python manage.py migrate"
        )
        step += 1

    if report.local_only:
        steps.append(
            f"  {step}. Apply local migrations to the remote database:\n"
            f"        DB_MODE=remote python manage.py migrate\n"
            f"     Or, if the local migrations are experimental, roll them back:\n"
            f"        python manage.py migrate <app> <previous_migration>"
        )
        step += 1

    if report.tables_local_only:
        steps.append(
            f"  {step}. Tables exist locally but not on remote ({len(report.tables_local_only)}).\n"
            f"     If intentional (new app), run migrations on remote.\n"
            f"     If stale, drop locally:\n"
            f"        DROP TABLE IF EXISTS {', '.join(report.tables_local_only[:3])} CASCADE;"
        )
        step += 1

    if report.tables_remote_only:
        steps.append(
            f"  {step}. Tables exist on remote but not locally ({len(report.tables_remote_only)}).\n"
            f"     Pull migration files and run 'python manage.py migrate'."
        )
        step += 1

    if not steps:
        steps.append(f"  {step}. Review the error details above and resolve manually.")

    return '\n\n'.join(steps)
