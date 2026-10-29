"""Alice's disk copy of the records a company builds by hand: Settings and Reports.

Every model definition, list, form, card, panel, select list, AI agent and report a company has
shaped lives in these two tables; commerce data has its own backup. Alice writes each nightly
(config_backup_task) into the data folder, zipped and dated (Bill, 2026-10-29: "disk space is cheap"):

    <DATA_DIR>/backups/<kind>/rolling/<kind>-<database>-YYYY-MM-DD.json.gz   kept ROLLING_DAYS
    <DATA_DIR>/backups/<kind>/archive/<kind>-<database>-YYYY-MM.json.gz      the month's first, kept

Every row is written with every column, so a file restores what it holds.
"""
from __future__ import annotations

import gzip
import json
import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import connection

logger = logging.getLogger(__name__)

ROLLING_DAYS = 30
KINDS = {'settings': ('core', 'Setting'), 'reports': ('core', 'Report')}


def _folder(kind: str, which: str) -> Path:
    path = Path(settings.DATA_DIR) / 'backups' / kind / which
    path.mkdir(parents=True, exist_ok=True)
    return path


def _rows(kind: str) -> list[dict]:
    from django.apps import apps
    model = apps.get_model(*KINDS[kind])
    return list(model.objects.order_by('id').values())


def back_up(kind: str, *, now: datetime | None = None) -> dict[str, Any]:
    """Write today's copy of `kind`, start the month's archive if it has none, prune the rolling."""
    now = now or datetime.now(timezone.utc)
    database = connection.settings_dict.get('NAME') or 'db'
    rows = _rows(kind)
    content = json.dumps({'kind': kind, 'database': database, 'exported_at': now.isoformat(),
                          'count': len(rows), 'rows': rows}, default=str).encode()

    rolling = _folder(kind, 'rolling') / f'{kind}-{database}-{now:%Y-%m-%d}.json.gz'
    with gzip.open(rolling, 'wb') as f:
        f.write(content)
    archive = _folder(kind, 'archive') / f'{kind}-{database}-{now:%Y-%m}.json.gz'
    archived = not archive.exists()
    if archived:
        shutil.copy2(rolling, archive)

    cutoff = f'{kind}-{database}-{now - timedelta(days=ROLLING_DAYS):%Y-%m-%d}.json.gz'
    pruned = 0
    for old in _folder(kind, 'rolling').glob(f'{kind}-{database}-*.json.gz'):
        if old.name < cutoff:
            old.unlink()
            pruned += 1

    logger.info('config_backup: %d %s to %s (%d bytes zipped)%s', len(rows), kind, rolling,
                rolling.stat().st_size, ', archived' if archived else '')
    return {'path': str(rolling), 'count': len(rows), 'size_bytes': rolling.stat().st_size,
            'archived': str(archive) if archived else '', 'pruned': pruned}
