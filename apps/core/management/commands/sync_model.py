"""
Sync model data between local and remote databases.

Usage:
    # Pull remote → local  (overwrite local table with remote data)
    python manage.py sync_model contact --direction to-local

    # Push local → remote  (overwrite remote table with local data)
    python manage.py sync_model contact --direction to-remote

    # Sync ALL blessed models at once (remote → local)
    python manage.py sync_model all --direction to-local

    # Dry-run (count records, show plan, don't touch target)
    python manage.py sync_model action --direction to-local --dry-run

    # List available model names
    python manage.py sync_model --list

    # Use app_label.ModelName instead of WCAPI blessed key
    python manage.py sync_model core.Action --direction to-local

Flow:
    1. Connect to both databases (source + target)
    2. Serialize all rows from source via Django ORM
    3. TRUNCATE target table (CASCADE)
    4. Bulk-insert serialized rows into target
    5. Reset PostgreSQL sequence to max(id) + 1
"""
import getpass
import json
import os
import socket
import sys
import time
import logging
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction, IntegrityError

from common.migration_check import (
    check_migration_parity,
    check_migration_parity_for_model,
    format_remediation,
)

try:
    from decouple import config as env
except ImportError:
    env = lambda key, default='': os.environ.get(key, default)

logger = logging.getLogger('wcapi.sync_model')

# ── sync_model Connection name (get_or_create'd on first run) ───────
_SYNC_CONNECTION_NAME = 'sync_model'

# ── database alias names used within this command only ──────────────
_LOCAL_ALIAS = '_sync_local'
_REMOTE_ALIAS = '_sync_remote'

# ── audit log file ──────────────────────────────────────────────────
_LOG_DIR = Path(settings.BASE_DIR) / 'logs'
_LOG_FILE = _LOG_DIR / 'sync_model.log'


def _log_audit(*, model_label, table, direction, src_label, tgt_label,
               src_host, tgt_host, src_count, tgt_count, rows_synced,
               elapsed, dry_run, status='OK', error=None):
    """Append a structured line to logs/sync_model.log."""
    _LOG_DIR.mkdir(exist_ok=True)

    user = getpass.getuser()
    hostname = socket.gethostname()
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    cmd = ' '.join(sys.argv)

    parts = [
        f"[{ts}]",
        f"user={user}@{hostname}",
        f"model={model_label}",
        f"table={table}",
        f"direction={direction}",
        f"src={src_label}@{src_host}({src_count})",
        f"tgt={tgt_label}@{tgt_host}({tgt_count})",
        f"rows_synced={rows_synced}",
        f"elapsed={elapsed:.1f}s",
        f"dry_run={dry_run}",
        f"status={status}",
        f"cmd=\"{cmd}\"",
    ]
    if error:
        parts.append(f"error=\"{error}\"")

    line = '  '.join(parts)

    try:
        with open(_LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except OSError as exc:
        logger.warning("Could not write audit log: %s", exc)

    # Also emit via Python logger for structured logging integrations
    logger.info(line)


def _db_config(prefix):
    """Build a Django DATABASES dict entry from LOCAL_ or REMOTE_ env vars."""
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env(f'{prefix}_DATABASE_NAME', default=env('DATABASE_NAME', default='commerce_expert')),
        'USER': env(f'{prefix}_DATABASE_USER', default=env('DATABASE_USER', default='postgres')),
        'PASSWORD': env(f'{prefix}_DATABASE_PASS', default=env('DATABASE_PASS', default='')),
        'HOST': env(f'{prefix}_DATABASE_HOST', default=env('DATABASE_HOST', default='localhost')),
        'PORT': env(f'{prefix}_DATABASE_PORT', default=env('DATABASE_PORT', default='5432')),
        'ATOMIC_REQUESTS': False,
        'AUTOCOMMIT': True,
        'TIME_ZONE': settings.TIME_ZONE,
        'CONN_MAX_AGE': 0,
        'CONN_HEALTH_CHECKS': False,
        'OPTIONS': {},
    }


def _register_both_dbs():
    """Temporarily register both local and remote as Django DB aliases."""
    local_cfg = _db_config('LOCAL')
    remote_cfg = _db_config('REMOTE')

    # Inject into Django's connection handler
    settings.DATABASES[_LOCAL_ALIAS] = local_cfg
    settings.DATABASES[_REMOTE_ALIAS] = remote_cfg

    # Force Django to pick up the new entries
    for alias in (_LOCAL_ALIAS, _REMOTE_ALIAS):
        if alias in connections._connections.__dict__:
            del connections._connections.__dict__[alias]

    return local_cfg, remote_cfg


def _cleanup_dbs():
    """Close and remove temporary DB aliases."""
    for alias in (_LOCAL_ALIAS, _REMOTE_ALIAS):
        try:
            connections[alias].close()
        except Exception:
            pass
        settings.DATABASES.pop(alias, None)


def _resolve_model(model_name):
    """
    Resolve a model name to a Django model class.

    Accepted formats:
      - WCAPI blessed key: 'contact', 'action', 'order', etc.
      - app_label.ModelName: 'core.Contact', 'products.Item'
    """
    blessed = getattr(settings, 'WCAPI_BLESSED_MODELS', {})

    # Try blessed key first (case-insensitive)
    key = model_name.lower().replace('-', '_')
    if key in blessed:
        app_model = blessed[key]
        app_label, class_name = app_model.split('.')
        try:
            return apps.get_model(app_label, class_name)
        except LookupError:
            raise CommandError(
                f"WCAPI_BLESSED_MODELS['{key}'] = '{app_model}' but "
                f"no Django model '{class_name}' found in app '{app_label}'."
            )

    # Try app_label.ModelName format
    if '.' in model_name:
        app_label, class_name = model_name.rsplit('.', 1)
        try:
            return apps.get_model(app_label, class_name)
        except LookupError:
            raise CommandError(f"No model '{class_name}' in app '{app_label}'.")

    raise CommandError(
        f"Unknown model '{model_name}'. "
        f"Use a WCAPI blessed key (e.g. 'contact') or app_label.ModelName (e.g. 'core.Contact').\n"
        f"Run with --list to see available models."
    )


def _reset_sequence(model, db_alias):
    """Reset the PostgreSQL auto-increment sequence to max(id) + 1."""
    table = model._meta.db_table
    pk_col = model._meta.pk.column
    sql = (
        f"SELECT setval(pg_get_serial_sequence('{table}', '{pk_col}'), "
        f"COALESCE(MAX({pk_col}), 0) + 1, false) FROM \"{table}\""
    )
    try:
        with connections[db_alias].cursor() as cursor:
            cursor.execute(sql)
    except Exception as exc:
        # Non-fatal — sequence may not exist for tables with UUID PKs
        logger.debug("Sequence reset skipped for %s: %s", table, exc)


class Command(BaseCommand):
    help = "Sync model data between local and remote PostgreSQL databases"

    def add_arguments(self, parser):
        parser.add_argument(
            'model_name',
            nargs='?',
            default=None,
            help='WCAPI model key (e.g. "contact") or app.Model (e.g. "core.Contact")',
        )
        parser.add_argument(
            '--direction',
            choices=['to-local', 'to-remote'],
            help='"to-local" = remote → local; "to-remote" = local → remote',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show record counts and plan without modifying data',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            dest='list_models',
            help='List all available model names and exit',
        )
        parser.add_argument(
            '--no-confirm',
            action='store_true',
            help='Skip the confirmation prompt',
        )
        parser.add_argument(
            '--conflict',
            choices=['record', 'new'],
            default='record',
            help='Conflict resolution: "record" (default) updates existing, "new" creates new record at destination',
        )
        parser.add_argument(
            '--check-migrations',
            action='store_true',
            help='Run migration parity check only (no data sync)',
        )
        parser.add_argument(
            '--skip-migration-check',
            action='store_true',
            help='Skip the pre-flight migration parity check before syncing',
        )
        parser.add_argument(
            '--check-columns',
            action='store_true',
            help='Include column-level drift detection (slower, used with --check-migrations)',
        )

    def handle(self, *args, **options):
        # ── list mode ───────────────────────────────────────────────
        if options['list_models']:
            return self._list_models()

        # ── migration check only mode ───────────────────────────────
        if options['check_migrations']:
            return self._check_migrations_only(
                model_name=options['model_name'],
                include_columns=options['check_columns'],
            )

        # ── validate args ───────────────────────────────────────────
        model_name = options['model_name']
        direction = options['direction']
        conflict_mode = options['conflict']

        if not model_name:
            raise CommandError("Provide a model_name or use --list.")
        if not direction:
            raise CommandError("--direction is required (to-local or to-remote).")

        dry_run = options['dry_run']

        # ── "all" mode: sync every blessed model ────────────────────
        if model_name.lower() == 'all':
            return self._sync_all(direction, dry_run, options['no_confirm'], conflict_mode)

        model = _resolve_model(model_name)
        table = model._meta.db_table

        if direction == 'to-local':
            src_alias, tgt_alias = _REMOTE_ALIAS, _LOCAL_ALIAS
            src_label, tgt_label = 'REMOTE', 'LOCAL'
        else:
            src_alias, tgt_alias = _LOCAL_ALIAS, _REMOTE_ALIAS
            src_label, tgt_label = 'LOCAL', 'REMOTE'

        # ── set up dual connections ─────────────────────────────────
        local_cfg, remote_cfg = _register_both_dbs()

        try:
            # ── pre-flight migration check ──────────────────────────
            if not options['skip_migration_check']:
                mig_report = check_migration_parity_for_model(
                    model, _LOCAL_ALIAS, _REMOTE_ALIAS,
                )
                if not mig_report.ok:
                    self.stdout.write('')
                    self.stdout.write(self.style.ERROR(
                        '  ⚠ MIGRATION MISMATCH DETECTED'
                    ))
                    self.stdout.write(mig_report.format_report())
                    self.stdout.write('')
                    self.stdout.write(self.style.WARNING(
                        '  Remediation steps:'
                    ))
                    self.stdout.write(format_remediation(mig_report))
                    self.stdout.write('')
                    if not options['no_confirm']:
                        answer = input(
                            '  Continue despite migration mismatch? '
                            'Type "yes" to proceed, anything else to abort: '
                        )
                        if answer.strip().lower() != 'yes':
                            self.stdout.write(self.style.ERROR('  Aborted.'))
                            return
                    else:
                        self.stdout.write(self.style.WARNING(
                            '  --no-confirm set: proceeding despite mismatch.'
                        ))

            self._run_sync(
                model, table,
                src_alias, tgt_alias,
                src_label, tgt_label,
                local_cfg, remote_cfg,
                dry_run, options['no_confirm'],
                conflict_mode,
            )
        finally:
            _cleanup_dbs()

    # ────────────────────────────────────────────────────────────────
    #  Sync all blessed models
    # ────────────────────────────────────────────────────────────────

    def _sync_all(self, direction, dry_run, no_confirm, conflict_mode):
        blessed = getattr(settings, 'WCAPI_BLESSED_MODELS', {})
        if not blessed:
            raise CommandError("No WCAPI_BLESSED_MODELS defined in settings.")

        if direction == 'to-local':
            src_alias, tgt_alias = _REMOTE_ALIAS, _LOCAL_ALIAS
            src_label, tgt_label = 'REMOTE', 'LOCAL'
        else:
            src_alias, tgt_alias = _LOCAL_ALIAS, _REMOTE_ALIAS
            src_label, tgt_label = 'LOCAL', 'REMOTE'

        # Resolve all models first, skip unresolvable ones
        models_to_sync = []
        skipped = []
        for key, app_model in sorted(blessed.items()):
            app_label, class_name = app_model.split('.')
            try:
                model = apps.get_model(app_label, class_name)
                models_to_sync.append((key, model))
            except LookupError:
                skipped.append((key, app_model))

        total = len(models_to_sync)
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"  sync_model ALL: {total} models  {src_label} → {tgt_label}"
        ))
        if skipped:
            self.stdout.write(self.style.WARNING(
                f"  Skipping {len(skipped)} unresolvable: "
                + ", ".join(k for k, _ in skipped)
            ))
        self.stdout.write("")

        if not dry_run and not no_confirm:
            answer = input(f"  Sync all {total} models {src_label} → {tgt_label}? Type 'yes': ")
            if answer.strip().lower() != 'yes':
                self.stdout.write(self.style.ERROR("  Aborted."))
                return

        local_cfg, remote_cfg = _register_both_dbs()
        succeeded = 0
        failed = []

        try:
            for i, (key, model) in enumerate(models_to_sync, 1):
                table = model._meta.db_table
                self.stdout.write(self.style.MIGRATE_HEADING(
                    f"\n  [{i}/{total}] {key} ({model._meta.label})"
                ))
                try:
                    self._run_sync(
                        model, table,
                        src_alias, tgt_alias,
                        src_label, tgt_label,
                        local_cfg, remote_cfg,
                        dry_run, True,  # no_confirm=True (already confirmed above)
                        conflict_mode,
                    )
                    succeeded += 1
                except Exception as exc:
                    failed.append((key, str(exc)[:120]))
                    self.stdout.write(self.style.ERROR(
                        f"  ✗ {key}: {str(exc)[:120]}"
                    ))
        finally:
            _cleanup_dbs()

        # ── summary ─────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write("═" * 65)
        self.stdout.write(self.style.SUCCESS(
            f"  SYNC ALL COMPLETE: {succeeded}/{total} succeeded"
        ))
        if failed:
            self.stdout.write(self.style.ERROR(f"  Failed ({len(failed)}):"))
            for key, err in failed:
                self.stdout.write(self.style.ERROR(f"    - {key}: {err}"))
        if skipped:
            self.stdout.write(self.style.WARNING(
                f"  Skipped ({len(skipped)}): " + ", ".join(k for k, _ in skipped)
            ))
        self.stdout.write("═" * 65)

    # ────────────────────────────────────────────────────────────────
    #  Core sync logic
    # ────────────────────────────────────────────────────────────────

    def _run_sync(self, model, table, src_alias, tgt_alias,
                  src_label, tgt_label, local_cfg, remote_cfg,
                  dry_run, no_confirm, conflict_mode):

        # Count source records
        src_count = model.objects.using(src_alias).count()
        tgt_count = model.objects.using(tgt_alias).count()

        src_host = local_cfg['HOST'] if src_label == 'LOCAL' else remote_cfg['HOST']
        tgt_host = local_cfg['HOST'] if tgt_label == 'LOCAL' else remote_cfg['HOST']

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"  sync_model: {model._meta.label}"))
        self.stdout.write(f"  Table:       {table}")
        self.stdout.write(f"  Source:      {src_label} @ {src_host}  ({src_count:,} rows)")
        self.stdout.write(f"  Target:      {tgt_label} @ {tgt_host}  ({tgt_count:,} rows)")
        self.stdout.write(f"  Direction:   {src_label} → {tgt_label}")
        self.stdout.write("")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("  Dry run — no changes made."))
            _log_audit(
                model_label=model._meta.label, table=table,
                direction=f"{src_label}→{tgt_label}",
                src_label=src_label, tgt_label=tgt_label,
                src_host=src_host, tgt_host=tgt_host,
                src_count=src_count, tgt_count=tgt_count,
                rows_synced=0, elapsed=0, dry_run=True,
            )
            return

        # ── confirm ─────────────────────────────────────────────────
        if not no_confirm:
            self.stdout.write(self.style.WARNING(
                f"  This will DELETE all {tgt_count:,} rows in {tgt_label}.{table}\n"
                f"  and replace them with {src_count:,} rows from {src_label}."
            ))
            answer = input("\n  Type 'yes' to proceed: ")
            if answer.strip().lower() != 'yes':
                self.stdout.write(self.style.ERROR("  Aborted."))
                _log_audit(
                    model_label=model._meta.label, table=table,
                    direction=f"{src_label}→{tgt_label}",
                    src_label=src_label, tgt_label=tgt_label,
                    src_host=src_host, tgt_host=tgt_host,
                    src_count=src_count, tgt_count=tgt_count,
                    rows_synced=0, elapsed=0, dry_run=False,
                    status='ABORTED',
                )
                return

        t0 = time.time()
        inserted = 0
        updated = 0
        fk_conflicts = []
        try:
            # ── step 1: serialize from source ───────────────────────
            self.stdout.write(f"  [1/4] Reading {src_count:,} rows from {src_label}...", ending='')
            self.stdout.flush()

            qs = model.objects.using(src_alias).all().order_by('pk')
            data_json = serializers.serialize('json', qs)
            records = json.loads(data_json)

            self.stdout.write(self.style.SUCCESS(f" {len(records):,} serialized"))

            # ── step 2: update/insert into target ──────────────────
            self.stdout.write(f"  [2/4] Syncing {len(records):,} rows into {tgt_label}...", ending='')
            self.stdout.flush()

            stream = StringIO(data_json)
            objects = list(serializers.deserialize('json', stream))

            batch_size = 500
            with connections[tgt_alias].cursor() as cursor:
                cursor.execute(f'ALTER TABLE "{table}" DISABLE TRIGGER ALL')

            try:
                with transaction.atomic(using=tgt_alias):
                    for i in range(0, len(objects), batch_size):
                        batch = objects[i:i + batch_size]
                        for obj in batch:
                            try:
                                # Savepoint per row so a single IntegrityError
                                # doesn't poison the whole PostgreSQL transaction.
                                with transaction.atomic(using=tgt_alias):
                                    obj.save(using=tgt_alias)
                                inserted += 1
                            except IntegrityError as exc:
                                pk = obj.object.pk
                                try:
                                    existing = model.objects.using(tgt_alias).get(pk=pk)
                                    uuid_field = None
                                    for field in model._meta.fields:
                                        if field.get_internal_type() == 'UUIDField':
                                            uuid_field = field.name
                                            break
                                    uuid_match = True
                                    if uuid_field:
                                        src_uuid = getattr(obj.object, uuid_field, None)
                                        tgt_uuid = getattr(existing, uuid_field, None)
                                        uuid_match = (src_uuid == tgt_uuid)
                                    if uuid_match:
                                        changed = False
                                        for field in model._meta.fields:
                                            fname = field.name
                                            # Skip id (PK) and uuid (immutable cross-DB key).
                                            # ida flows from source like any other field —
                                            # only uuid is truly immutable across databases
                                            # (see §25 Sync Topologies in data-sync docs).
                                            if fname in ('id', uuid_field):
                                                continue
                                            src_val = getattr(obj.object, fname, None)
                                            tgt_val = getattr(existing, fname, None)
                                            if src_val != tgt_val:
                                                setattr(existing, fname, src_val)
                                                changed = True
                                        if changed:
                                            existing.save(using=tgt_alias)
                                            updated += 1
                                        else:
                                            inserted += 1  # row already matches
                                    else:
                                        if conflict_mode == 'new':
                                            # Create new record at destination
                                            obj.object.pk = None
                                            obj.save(using=tgt_alias)
                                            inserted += 1
                                        else:
                                            conflict_info = {
                                                'pk': pk,
                                                'fields': {k: repr(v) for k, v in obj.object.__dict__.items() if k != '_state'},
                                                'error': str(exc),
                                                'reason': 'UUID mismatch',
                                            }
                                            fk_conflicts.append(conflict_info)
                                except model.DoesNotExist:
                                    if conflict_mode == 'new':
                                        obj.object.pk = None
                                        obj.save(using=tgt_alias)
                                        inserted += 1
                                    else:
                                        conflict_info = {
                                            'pk': pk,
                                            'fields': {k: repr(v) for k, v in obj.object.__dict__.items() if k != '_state'},
                                            'error': str(exc),
                                            'reason': 'No target row with matching PK',
                                        }
                                        fk_conflicts.append(conflict_info)
            finally:
                with connections[tgt_alias].cursor() as cursor:
                    cursor.execute(f'ALTER TABLE "{table}" ENABLE TRIGGER ALL')

            self.stdout.write(self.style.SUCCESS(f" {inserted:,} inserted"))

            # ── step 4: reset sequence ──────────────────────────────
            self.stdout.write(f"  [4/4] Resetting PK sequence...", ending='')
            self.stdout.flush()

            _reset_sequence(model, tgt_alias)

            self.stdout.write(self.style.SUCCESS(" done"))

            elapsed = time.time() - t0
            elapsed_ms = int(elapsed * 1000)
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(
                f"  ✓ {model._meta.label}: {inserted:,} rows synced, {updated:,} updated "
                f"{src_label} → {tgt_label} in {elapsed:.1f}s"
            ))
            if fk_conflicts:
                self.stdout.write(self.style.ERROR(
                    f"  FK conflicts detected: {len(fk_conflicts)} rows failed to insert"
                ))
            self.stdout.write("")

            # ── Bundle record ───────────────────────────────────────
            self._save_bundle(
                model_label=model._meta.label, table=table,
                src_label=src_label, tgt_label=tgt_label,
                src_host=src_host, tgt_host=tgt_host,
                src_count=src_count, tgt_count=tgt_count,
                rows_synced=inserted, updated=updated,
                elapsed_ms=elapsed_ms,
                fk_conflicts=fk_conflicts,
            )

            # ── audit log ───────────────────────────────────────────
            _log_audit(
                model_label=model._meta.label, table=table,
                direction=f"{src_label}→{tgt_label}",
                src_label=src_label, tgt_label=tgt_label,
                src_host=src_host, tgt_host=tgt_host,
                src_count=src_count, tgt_count=tgt_count,
                rows_synced=inserted, elapsed=elapsed, dry_run=False,
                error=json.dumps({'fk_conflicts': fk_conflicts, 'updated': updated}) if fk_conflicts or updated else None,
            )

        except Exception as exc:
            elapsed = time.time() - t0
            _log_audit(
                model_label=model._meta.label, table=table,
                direction=f"{src_label}→{tgt_label}",
                src_label=src_label, tgt_label=tgt_label,
                src_host=src_host, tgt_host=tgt_host,
                src_count=src_count, tgt_count=tgt_count,
                rows_synced=inserted, elapsed=elapsed, dry_run=False,
                status='ERROR', error=str(exc),
            )
            raise

    # ────────────────────────────────────────────────────────────────
    #  Bundle logging
    # ────────────────────────────────────────────────────────────────

    def _save_bundle(self, *, model_label, table, src_label, tgt_label,
                     src_host, tgt_host, src_count, tgt_count,
                     rows_synced, updated, elapsed_ms, fk_conflicts):
        """Create a lightweight sync.Bundle record for this sync run."""
        try:
            from apps.sync.models import Bundle, Connection

            connection, _ = Connection.objects.using('default').get_or_create(
                name=_SYNC_CONNECTION_NAME,
                defaults={
                    'type': 'internal',
                    'config': {
                        'description': 'Internal sync_model management command',
                    },
                    'purpose': 'sync',
                    'status': 'active',
                },
            )

            direction = 'pull' if tgt_label == 'LOCAL' else 'push'
            has_conflicts = bool(fk_conflicts)

            if has_conflicts:
                status = 'warning'
                alert = 'warning'
            else:
                status = 'success'
                alert = 'none'

            Bundle.objects.using('default').create(
                connection=connection,
                direction=direction,
                config={
                    'model': model_label,
                    'table': table,
                    'src': f"{src_label}@{src_host}",
                    'tgt': f"{tgt_label}@{tgt_host}",
                    'src_count': src_count,
                    'tgt_count': tgt_count,
                    'updated': updated,
                },
                status=status,
                alert=alert,
                duration=elapsed_ms,
                size=rows_synced,
                conflicts=fk_conflicts if has_conflicts else None,
            )
            self.stdout.write(f"  Bundle recorded (direction={direction}, "
                             f"status={status}, size={rows_synced})")
        except Exception as exc:
            # Non-fatal: don't let bundle logging break a successful sync
            logger.warning("Could not save Bundle record: %s", exc)
            self.stdout.write(self.style.WARNING(
                f"  Bundle record skipped: {exc}"
            ))

    # ────────────────────────────────────────────────────────────────
    #  Migration check only mode
    # ────────────────────────────────────────────────────────────────

    def _check_migrations_only(self, model_name=None, include_columns=False):
        """Run migration parity check without syncing any data."""
        local_cfg, remote_cfg = _register_both_dbs()

        try:
            self.stdout.write('')
            self.stdout.write(self.style.MIGRATE_HEADING(
                '  Migration Parity Check: LOCAL ↔ REMOTE'
            ))
            self.stdout.write(f"  Local:   {local_cfg['HOST']}:{local_cfg['PORT']}/{local_cfg['NAME']}")
            self.stdout.write(f"  Remote:  {remote_cfg['HOST']}:{remote_cfg['PORT']}/{remote_cfg['NAME']}")
            self.stdout.write('')

            if model_name and model_name.lower() != 'all':
                model = _resolve_model(model_name)
                self.stdout.write(f"  Scope: {model._meta.label} ({model._meta.db_table})")
                self.stdout.write('')
                report = check_migration_parity_for_model(
                    model, _LOCAL_ALIAS, _REMOTE_ALIAS,
                )
            else:
                report = check_migration_parity(
                    _LOCAL_ALIAS, _REMOTE_ALIAS,
                    include_tables=True,
                    include_columns=include_columns,
                )

            self.stdout.write(report.format_report())

            if not report.ok:
                self.stdout.write('')
                self.stdout.write(self.style.WARNING('  Remediation steps:'))
                self.stdout.write(format_remediation(report))

            self.stdout.write('')

        finally:
            _cleanup_dbs()

    # ────────────────────────────────────────────────────────────────
    #  List mode
    # ────────────────────────────────────────────────────────────────

    def _list_models(self):
        blessed = getattr(settings, 'WCAPI_BLESSED_MODELS', {})
        self.stdout.write(self.style.MIGRATE_HEADING("\nAvailable model names:\n"))
        self.stdout.write(f"  {'Key':<28} {'App.Model':<35} {'Table'}")
        self.stdout.write(f"  {'─' * 28} {'─' * 35} {'─' * 30}")

        for key, app_model in sorted(blessed.items()):
            app_label, class_name = app_model.split('.')
            try:
                model = apps.get_model(app_label, class_name)
                table = model._meta.db_table
            except LookupError:
                table = '(model not found)'
            self.stdout.write(f"  {key:<28} {app_model:<35} {table}")

        self.stdout.write(f"\n  Total: {len(blessed)} models\n")
