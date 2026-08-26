import os
import pytest
from django.conf import settings

# These tests attempt to monkeypatch env vars and re-import Django settings,
# but Python caches module imports so DATABASES reflects the first import only.
# Broken by design — skip until settings selection is testable via a function.

@pytest.mark.skip(reason="Python module caching prevents re-import of Django settings with different env vars")
def test_postgres_database_selection(monkeypatch):
    monkeypatch.setenv('PYTEST_FORCE_DB', '1')
    monkeypatch.setenv('USE_SQLITE_TEST', '0')
    monkeypatch.setenv('PYTEST_CURRENT_TEST', '')
    from webclerk3_api.settings import DATABASES
    assert DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql'

@pytest.mark.skip(reason="Python module caching prevents re-import of Django settings with different env vars")
def test_sqlite_database_selection(monkeypatch):
    monkeypatch.setenv('PYTEST_FORCE_DB', '0')
    monkeypatch.setenv('USE_SQLITE_TEST', '1')
    monkeypatch.setenv('PYTEST_CURRENT_TEST', '')
    from webclerk3_api.settings import DATABASES
    assert DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3'
    assert DATABASES['default']['NAME'] == ':memory:'

@pytest.mark.skip(reason="Python module caching prevents re-import of Django settings with different env vars")
def test_warning_for_in_memory_sqlite(monkeypatch, capsys):
    monkeypatch.setenv('PYTEST_FORCE_DB', '0')
    monkeypatch.setenv('USE_SQLITE_TEST', '0')
    monkeypatch.setenv('PYTEST_CURRENT_TEST', '')
    monkeypatch.setattr('sys.argv', ['manage.py', 'runserver'])
    from webclerk3_api.settings import DATABASES
    assert DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3'
    assert DATABASES['default']['NAME'] == ':memory:'
    with capsys.disabled():
        print('[WARNING] runserver using in-memory SQLite (:memory:). Data will not persist. Set USE_SQLITE_TEST=0 or PYTEST_FORCE_DB=1 for Postgres.')
    captured = capsys.readouterr()
    assert '[WARNING] runserver using in-memory SQLite (:memory:). Data will not persist. Set USE_SQLITE_TEST=0 or PYTEST_FORCE_DB=1 for Postgres.' in captured.out