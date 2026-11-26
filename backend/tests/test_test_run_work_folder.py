"""A test run never writes the server's work folder (lead, 2026-11-26).

Pytest wrote to the shared work/logs/webclerk3.log (and balance-events.jsonl, logs/hooks/,
bundles/), so a test run read as live errors to anyone watching the server. settings.WORK_DIR is
the one source for every path under the work folder; a test run gets its own, named for its
private test database (WC_TEST_DB_NAME), beside the server's.
"""
import os
from pathlib import Path

from django.conf import settings


def _server_work_dir() -> Path:
    from decouple import config
    return Path(config('WORK_DIR', default=str(Path(settings.DATA_DIR).parent / 'work')))


def test_a_test_run_has_its_own_work_folder_named_for_its_test_database():
    work = Path(settings.WORK_DIR)
    assert work != _server_work_dir()
    assert _server_work_dir() not in work.parents
    assert work.name == os.environ.get('WC_TEST_DB_NAME', 'test_commerce_expert_new')


def test_the_logs_follow_the_work_folder():
    work = Path(settings.WORK_DIR)
    assert Path(settings.LOG_DIR) == work / 'logs'
    assert Path(settings.LOGGING['handlers']['file']['filename']).parent == work / 'logs'
    assert Path(settings.BALANCE_EVENT_LOG_PATH).parent == work / 'logs'
