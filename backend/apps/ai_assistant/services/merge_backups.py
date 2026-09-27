"""Contact merge backups (config.backup): a one-day safety net, cleaned nightly by Alice.

Kept from contact_parser, which was deleted with the paste importer (import plan §17: WebClerk
parses no file or pasted text; cleanup happens outside and comes in as a bundle)."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def clean_merge_backups(max_age_hours: int = 24, dry_run: bool = False) -> dict[str, Any]:
    """Remove config.backup entries older than max_age_hours.

    Called by Alice nightly. Backups are a safety net for accidental merges,
    not permanent storage. One day is enough time to catch a mistake.

    Returns {'cleaned': N, 'skipped': N}.
    """
    import datetime
    from apps.core.models.contact import Contact

    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=max_age_hours)
    cutoff_iso = cutoff.isoformat()

    # Find contacts with config.backup
    contacts = Contact.objects.filter(
        config__has_key='backup',
    ).exclude(config__backup={})

    cleaned = 0
    skipped = 0

    for c in contacts.iterator(chunk_size=100):
        config = c.config or {}
        backup = config.get('backup', {})
        dt_backup = backup.get('dt_backup', '')

        if not dt_backup:
            # No timestamp — clean it (legacy)
            if not dry_run:
                del config['backup']
                c.config = config
                c._setting_update_authorized = True
                c.save(update_fields=['config'])
            cleaned += 1
            continue

        if dt_backup < cutoff_iso:
            if not dry_run:
                del config['backup']
                c.config = config
                c.save(update_fields=['config'])
            cleaned += 1
        else:
            skipped += 1

    logger.info('Merge backup cleanup: %d cleaned, %d skipped (< %dh old)',
                cleaned, skipped, max_age_hours)
    return {'cleaned': cleaned, 'skipped': skipped}

