from __future__ import annotations

import os
import subprocess
import shutil
import sys
import django
from typing import Iterable, Sequence
from pathlib import Path
from dataclasses import dataclass
from django.conf import settings
from django.core.management import call_command
from django.db import connection

# Default seed commands (idempotent where possible)
DEFAULT_SEED_COMMANDS: Sequence[str] = (
    "load_default_company",
    "load_default_access",
    "seed_orgs",
    "seed_documents",
    "seed_projects",
    "seed_transactions",
    "seed_relationships",  # enrich cross-entity lightweight links (contacts<->comm methods, org contact lists, order line contacts)
)


@dataclass
class ResetResult:
    db_name: str
    recreated: bool
    migrations_applied: bool
    superusers: int
    seed_commands_run: list[str]


def _terminate_connections(db_name: str):
    with connection.cursor() as cur:
        try:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid();",
                [db_name],
            )
        except Exception:
            pass  # best effort only


def _drop_and_create(db_name: str):
    # We need a server-level connection; use env vars or django settings DATABASES
    params = settings.DATABASES['default']
    # Temporarily connect to maintenance DB (postgres) using psql for simplicity
    host = params.get('HOST') or 'localhost'
    port = params.get('PORT') or '5432'
    user = params.get('USER') or os.getenv('USER')

    def run_psql(sql: str):
        if not shutil.which('psql'):
            raise RuntimeError('psql binary not found in PATH; cannot perform drop/create.')
        cmd = [
            'psql', '-h', host, '-p', str(port), '-U', str(user), '-d', 'postgres',
            '-c', sql,
        ]
        # In non-interactive flows ensure PGPASSWORD respected if set; rely on .pgpass otherwise
        subprocess.run(cmd, check=False)

    run_psql(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{db_name}' AND pid <> pg_backend_pid();")
    run_psql(f'DROP DATABASE IF EXISTS "{db_name}";')
    run_psql(f'CREATE DATABASE "{db_name}";')


def _create_superusers(n: int):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    created = 0
    for i in range(1, n + 1):
        email = f"{i}@{i}.com"
        if User.objects.filter(email=email).exists():
            continue
        # Map to legacy naming first_/last_ to first_name/last_name manager expects
        u = User.objects.create_superuser(
            email=email,
            username=email,
            password='1111pass',
            first_name=f'first_{i}',
            last_name=f'last_{i}',
        )
        created += 1
    return created


def full_reset_and_seed(
    *,
    destructive: bool = True,
    seed_commands: Iterable[str] | None = None,
    create_superusers: int = 3,
    skip_seed: bool = False,
    nuke_migrations: bool = False,
    auto_make_migrations: bool = False,
) -> ResetResult:
    """Destructive local reset: drop DB, migrate, seed, create superusers.

    Parameters:
      destructive: Guard flag; if False raises RuntimeError (safety).
      seed_commands: Iterable of management command names to run after migrate.
      create_superusers: Number of patterned superusers to create (1@1.com...).
      skip_seed: If True skips seed commands but still creates superusers.

        Returns ResetResult summarizing actions.

        Extra dev-only options:
            nuke_migrations: Delete all numbered migration files (except __init__.py) for first‑party apps BEFORE migrate.
            auto_make_migrations: If True and nuke_migrations used, run makemigrations prior to migrate.
    """
    # ------------------------------------------------------------------
    # Environment safety guard: ensure using the project virtualenv python
    # and expected Django major version (5.x). Override with ALLOW_SYSTEM_PY=1.
    # ------------------------------------------------------------------
    try:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
        expected_python = os.path.join(project_root, 'bin', 'python')
        if os.path.exists(expected_python):  # only enforce if venv bootstrap exists
            if sys.executable != expected_python and not os.getenv('ALLOW_SYSTEM_PY'):
                raise RuntimeError(
                    f"Environment guard: running with sys.executable={sys.executable} but expected {expected_python}. "
                    "Activate the project virtualenv or set ALLOW_SYSTEM_PY=1 to override."
                )
        dj_version = django.get_version()
        if not dj_version.startswith('5.') and not os.getenv('ALLOW_SYSTEM_PY'):
            raise RuntimeError(
                f"Environment guard: Django {dj_version} detected; expected 5.x. Activate correct env or ALLOW_SYSTEM_PY=1 to bypass."
            )
    except RuntimeError:
        raise
    except Exception:
        # Non-fatal guard failure (avoid blocking if detection logic changes)
        pass
    if not settings.DEBUG:
        # Extra guard; allow override via env
        if not os.getenv('FORCE_FULL_RESET'):
            raise RuntimeError('Refusing to run full_reset_and_seed with DEBUG=False (set FORCE_FULL_RESET=1 to override).')
    if not destructive:
        raise RuntimeError('destructive=False: refusing to proceed.')

    params = settings.DATABASES['default']
    db_name = params['NAME']

    # Terminate active sessions from other clients (best effort)
    _terminate_connections(db_name)

    # Close any active Django connections BEFORE dropping to avoid stale cursors
    try:
        from django.db import connections
        for conn in connections.all():  # close all (in case of multiple databases)
            try:
                conn.close()
            except Exception:
                pass
    except Exception:
        pass

    _drop_and_create(db_name)

    # Close again to ensure fresh post-create connections
    try:
        from django.db import connections
        for conn in connections.all():
            try:
                conn.close()
            except Exception:
                pass
    except Exception:
        pass

    # Optional destructive migration nuke (local only). We detect local apps by presence of apps/*/migrations.
    if nuke_migrations:
        apps_dir = Path(project_root) / 'apps'
        for mig in apps_dir.rglob('migrations'):
            if not mig.is_dir():
                continue
            for f in mig.glob('[0-9][0-9][0-9][0-9]*.py'):
                try:
                    f.unlink()
                except Exception:
                    pass
        if auto_make_migrations:
            try:
                call_command('makemigrations', interactive=False, verbosity=0)
            except Exception:
                pass

    # Force a fresh connection and run migrations (baseline assumed committed OR just regenerated)
    try:
        connection.close()  # safety
        connection.ensure_connection()
    except Exception:
        pass
    call_command('migrate', interactive=False)

    run_cmds: list[str] = []
    if not skip_seed:
        for cmd in (seed_commands or DEFAULT_SEED_COMMANDS):
            try:
                call_command(cmd)
                run_cmds.append(cmd)
            except Exception:  # non-fatal seed errors
                pass
        # Light synthetic reseed for residual empty tables
        try:
            call_command('reseed_all_models', '--no-flush', '--per-model', '2')
            run_cmds.append('reseed_all_models')
        except Exception:
            pass

    su_created = _create_superusers(create_superusers) if create_superusers > 0 else 0

    return ResetResult(
        db_name=db_name,
        recreated=True,
        migrations_applied=True,
        superusers=su_created,
        seed_commands_run=run_cmds,
    )

__all__ = [
    'full_reset_and_seed',
    'ResetResult',
]
