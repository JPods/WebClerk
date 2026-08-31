"""Migration health checks.

PRE-PRODUCTION NOTE:
    Migrations may be deleted, squashed, or reset at any time until we are
    in a production release. Any test that depends on a specific migration
    file, migration count, or migration history should be written with this
    in mind. Do NOT assert on migration filenames or counts -- assert on
    the result (the schema is consistent, no conflicts, no pending changes).

    Once we cut a production release, migration history becomes immutable
    and these tests can be tightened.
"""
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]

pytestmark = [pytest.mark.smoke, pytest.mark.fast]


@pytest.mark.django_db
def test_no_migration_conflicts():
    """Verify no conflicting migrations exist (duplicate leaf nodes).

    This is the #1 cause of mass test errors -- a duplicate migration file
    prevents the test DB from being created at all.
    """
    result = subprocess.run(
        [sys.executable, 'manage.py', 'showmigrations', '--plan'],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert result.returncode == 0, (
        f"Migration conflict detected:\n{result.stderr}\n{result.stdout}"
    )


def test_no_pending_migrations():
    """Verify makemigrations --check finds no unapplied model changes.

    PRE-PRODUCTION: This test may need to be skipped during active
    development sprints where model changes are in progress.
    """
    result = subprocess.run(
        [sys.executable, 'manage.py', 'makemigrations', '--check', '--dry-run'],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert result.returncode == 0, (
        f"Pending model changes need migrations:\n{result.stdout}\n{result.stderr}"
    )
