"""Utility script to delete all numbered migration files (except __init__.py) under apps/* and regenerate fresh 0001_initial migrations.

Usage (from project root, ensure venv active):

    ./bin/python -m common.rebuild.nuke_migrations

Optionally pass --no-makemigrations to skip regeneration (diagnostic).
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import os
from django.core.management import call_command

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APPS_DIR = PROJECT_ROOT / 'apps'


def nuke(no_make: bool = False, verbose: bool = True):
    removed = []
    for mig_dir in APPS_DIR.rglob('migrations'):
        if not mig_dir.is_dir():
            continue
        for f in mig_dir.glob('[0-9][0-9][0-9][0-9]*.py'):
            try:
                f.unlink()
                removed.append(f)
            except Exception:
                pass
    if verbose:
        print(f"Removed {len(removed)} migration files.")
    if not no_make:
        call_command('makemigrations', interactive=False)
    return removed


def main(argv=None):  # pragma: no cover
    parser = argparse.ArgumentParser(description='Nuke and regenerate project app migrations (DEV ONLY).')
    parser.add_argument('--no-makemigrations', dest='no_make', action='store_true', help='Skip regeneration step.')
    args = parser.parse_args(argv)
    # Safety: refuse if DEBUG not true unless override
    from django.conf import settings
    if not settings.DEBUG and not os.getenv('FORCE_NUKE_MIGRATIONS'):
        print('Refusing to nuke migrations with DEBUG=False (set FORCE_NUKE_MIGRATIONS=1 to override).', file=sys.stderr)
        return 2
    nuke(no_make=args.no_make)
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
