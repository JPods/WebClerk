"""Clean up Document records with broken local paths.

Fixes:
  1. Deletes faker/seed test records (lorem ipsum status values)
  2. Tags local-only documents (SketchUp indexed, PRT digests) with scope='local'
  3. Updates uploaded file path.url to use WCHQ base URL
  4. Removes dead references (old webClerk3 paths, Windows paths)

Usage:
    python manage.py cleanup_document_paths --dry-run   # preview changes
    python manage.py cleanup_document_paths              # apply changes
"""
import json
from django.core.management.base import BaseCommand
from apps.docs.models.document import Document

WCHQ_URL = "https://www.webclerk.com"


class Command(BaseCommand):
    help = "Clean up Document records with broken local paths"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Preview changes without applying them',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        prefix = "[DRY RUN] " if dry_run else ""

        # ── 1. Delete faker/seed test records ──
        # These have lorem ipsum in the status field — clearly test data
        faker_ids = []
        for doc in Document.objects.filter(id__lte=10):
            status = doc.status or ''
            # Faker records have multi-word lorem ipsum in status
            if len(status) > 20 and ' ' in status:
                faker_ids.append(doc.id)
        faker_count = len(faker_ids)
        if faker_count:
            self.stdout.write(f"{prefix}Deleting {faker_count} faker/test document records (ids: {faker_ids})")
            if not dry_run:
                Document.objects.filter(id__in=faker_ids).delete()

        # ── 2. Delete dead references (old paths that no longer exist) ──
        dead_paths = []
        for doc in Document.objects.exclude(path__isnull=True).exclude(path='{}'):
            path_str = str(doc.path) if doc.path else ''
            # Old webClerk3 directory (retired)
            if 'webClerk3' in path_str and 'D:\\\\' in path_str:
                dead_paths.append(doc.id)
            # Windows D:\ paths from old deployment
            elif 'D:\\\\JPods' in path_str or 'D:\\\\' in path_str:
                dead_paths.append(doc.id)

        if dead_paths:
            self.stdout.write(f"{prefix}Deleting {len(dead_paths)} dead reference documents (old Windows/webClerk3 paths)")
            if not dry_run:
                Document.objects.filter(id__in=dead_paths).delete()

        # ── 3. Tag local-only documents with scope in config ──
        local_categories = {
            'sketchup': 'SketchUp',
            'prt-digest': 'prt_digest',
            'allie-prt-watch': 'prt_digest',
        }

        tagged_count = 0
        for doc in Document.objects.exclude(path__isnull=True):
            path_str = str(doc.path) if doc.path else ''
            scope = None

            if 'SketchUp' in path_str and doc.status == 'indexed':
                scope = 'local'
                category = 'sketchup_code'
            elif 'prt-digest' in path_str or 'allie-prt-watch' in path_str:
                scope = 'local'
                category = 'prt_digest'
            elif '/Volumes/Allie/jpods/library' in path_str:
                scope = 'local'
                category = 'jpods_library'
            else:
                continue

            config = doc.config if isinstance(doc.config, dict) else {}
            if config.get('scope') == scope:
                continue  # already tagged

            config['scope'] = scope
            config['content_category'] = category
            tagged_count += 1

            if not dry_run:
                doc.config = config
                doc.save(update_fields=['config'])

        if tagged_count:
            self.stdout.write(f"{prefix}Tagged {tagged_count} documents as scope='local'")

        # ── 4. Update uploaded file URLs to use WCHQ base ──
        upload_count = 0
        for doc in Document.objects.exclude(path__isnull=True):
            path = doc.path
            if not isinstance(path, dict):
                continue

            url = path.get('url', '')
            full = str(path.get('full', ''))
            storage = path.get('storage', '')

            # Skip inline storage — already portable
            if storage == 'inline':
                continue

            # Update relative wcapi URLs to absolute WCHQ URLs
            if url and url.startswith('/wcapi/document/') and storage == 'local':
                path['url'] = f"{WCHQ_URL}{url}"
                upload_count += 1
                if not dry_run:
                    doc.path = path
                    doc.save(update_fields=['path'])

            # Update relative static URLs to absolute WCHQ URLs
            elif url and url.startswith('/static/') and storage == 'local':
                path['url'] = f"{WCHQ_URL}{url}"
                upload_count += 1
                if not dry_run:
                    doc.path = path
                    doc.save(update_fields=['path'])

        if upload_count:
            self.stdout.write(f"{prefix}Updated {upload_count} document URLs to use {WCHQ_URL}")

        # ── Summary ──
        self.stdout.write(self.style.SUCCESS(
            f"\n{prefix}Cleanup complete: "
            f"{faker_count} faker deleted, "
            f"{len(dead_paths)} dead refs deleted, "
            f"{tagged_count} tagged local, "
            f"{upload_count} URLs updated"
        ))
