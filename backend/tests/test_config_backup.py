"""Alice's disk copy of Settings and Reports: zipped, dated, a rolling window and a monthly
archive (Bill, 2026-10-29)."""
import gzip
import json
from datetime import datetime, timedelta, timezone

import pytest

from apps.core.services import config_backup


@pytest.mark.django_db
def test_rolling_copy_monthly_archive_and_prune(tmp_path, settings):
    settings.DATA_DIR = tmp_path
    day = datetime(2026, 10, 29, 1, tzinfo=timezone.utc)

    first = config_backup.back_up('settings', now=day)
    assert first['archived'] and first['count'] >= 0
    with gzip.open(first['path']) as f:
        assert json.load(f)['kind'] == 'settings'

    # A second day in the same month: rolling copy only, the month's archive is kept as it was.
    assert config_backup.back_up('settings', now=day + timedelta(days=1))['archived'] == ''

    # Past the window: the oldest rolling copy goes, both archives stay.
    later = day + timedelta(days=config_backup.ROLLING_DAYS + 1)
    assert config_backup.back_up('settings', now=later)['pruned'] == 1
    rolling = sorted(p.name for p in (tmp_path / 'backups/settings/rolling').iterdir())
    archive = sorted(p.name for p in (tmp_path / 'backups/settings/archive').iterdir())
    assert len(rolling) == 2 and len(archive) == 2
