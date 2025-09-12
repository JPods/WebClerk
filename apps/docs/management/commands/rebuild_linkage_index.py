from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.docs.models.linkage import Linkage
from apps.docs.models.linkage_index import LinkageIndex


class Command(BaseCommand):
    help = "Rebuild linkage_index from Linkage.refs.links JSON."

    def add_arguments(self, parser):  # pragma: no cover trivial
        parser.add_argument('--purge', action='store_true', help='Purge existing linkage_index rows before rebuild')
        parser.add_argument('--batch', type=int, default=500, help='Batch size for scanning linkages')
        parser.add_argument('--limit', type=int, default=0, help='Limit number of linkage rows processed (0=all)')

    def handle(self, *args, **opts):
        batch = max(1, int(opts.get('batch') or 500))
        limit = max(0, int(opts.get('limit') or 0))
        purge = bool(opts.get('purge'))

        if purge:
            self.stdout.write('Purging linkage_index...')
            LinkageIndex.objects.all().delete()

        qs = Linkage.objects.order_by('id')
        if limit:
            qs = qs[:limit]

        created = 0
        scanned = 0
        for start in range(0, qs.count(), batch):
            chunk = list(qs[start:start+batch])
            if not chunk:
                break
            with transaction.atomic():
                for lk in chunk:
                    scanned += 1
                    refs = getattr(lk, 'refs', {}) or {}
                    links = refs.get('links') if isinstance(refs, dict) else None
                    if not isinstance(links, dict):
                        continue
                    for table, ids in links.items():
                        if not isinstance(ids, list):
                            continue
                        for rid in ids:
                            try:
                                _, was_created = LinkageIndex.objects.get_or_create(
                                    linkage=lk, table_name=table, record_id=int(rid)
                                )
                                if was_created:
                                    created += 1
                            except Exception:
                                # Skip invalid entries silently
                                continue
        self.stdout.write(self.style.SUCCESS(
            f"rebuild_linkage_index: scanned={scanned} created={created} purge={purge}"
        ))
