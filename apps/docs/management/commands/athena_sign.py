"""
Athena signing command — hash protected files and update the manifest.

Usage:
    # Sign all known checkpoints and create/update the manifest Document
    python manage.py athena_sign

    # Add a new file to the manifest
    python manage.py athena_sign --add /var/www/webclerk-static/sort/index.html --type static_file

    # List current checkpoints
    python manage.py athena_sign --list

    # Verify all checkpoints now (same as Celery task, but immediate)
    python manage.py athena_sign --verify
"""
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.docs.models import Document


class Command(BaseCommand):
    help = 'Athena: sign files and manage the integrity manifest'

    def add_arguments(self, parser):
        parser.add_argument('--add', type=str, help='Add a file path to the manifest')
        parser.add_argument('--type', type=str, default='static_file',
                            help='Checkpoint type (static_file, wcapi, robotics, allie)')
        parser.add_argument('--remove', type=str, help='Remove a file path from the manifest')
        parser.add_argument('--list', action='store_true', help='List all checkpoints')
        parser.add_argument('--verify', action='store_true', help='Verify all checkpoints now')
        parser.add_argument('--sign-all', action='store_true', default=True,
                            help='Re-hash all existing checkpoints (default)')

    def get_or_create_manifest(self):
        doc = Document.objects.filter(ida='athena-manifest', is_deleted=False).first()
        if not doc:
            doc = Document.objects.create(
                ida='athena-manifest',
                name='Athena Integrity Manifest',
                description='Signed hashes for all protected files. Verified every 4 hours.',
                status='active',
                config={
                    'checkpoints': [],
                    'last_sign': None,
                    'last_check': None,
                    'last_result': None,
                    'check_count': 0,
                },
                refs={'keywords': ['athena', 'security', 'integrity', 'manifest']},
            )
            self.stdout.write(self.style.SUCCESS(f'Created manifest Document id={doc.id}'))
        return doc

    def hash_file(self, path):
        p = Path(path)
        if not p.exists():
            return None
        return hashlib.sha256(p.read_bytes()).hexdigest()

    def handle(self, *args, **options):
        doc = self.get_or_create_manifest()
        manifest = doc.config or {}
        checkpoints = manifest.get('checkpoints', [])

        if options.get('add'):
            path = options['add']
            h = self.hash_file(path)
            if h is None:
                self.stderr.write(self.style.ERROR(f'File not found: {path}'))
                return

            # Update or add
            existing = next((c for c in checkpoints if c['path'] == path), None)
            if existing:
                existing['hash'] = h
                existing['signed'] = datetime.now(timezone.utc).isoformat()
                existing['type'] = options['type']
                self.stdout.write(f'Updated: {path} → {h[:16]}...')
            else:
                checkpoints.append({
                    'path': path,
                    'hash': h,
                    'signed': datetime.now(timezone.utc).isoformat(),
                    'type': options['type'],
                })
                self.stdout.write(f'Added: {path} → {h[:16]}...')

        elif options.get('remove'):
            path = options['remove']
            before = len(checkpoints)
            checkpoints = [c for c in checkpoints if c['path'] != path]
            if len(checkpoints) < before:
                self.stdout.write(f'Removed: {path}')
            else:
                self.stderr.write(f'Not found: {path}')

        elif options.get('list'):
            if not checkpoints:
                self.stdout.write('No checkpoints in manifest.')
                return
            self.stdout.write(f'\n{"Path":<60} {"Type":<15} {"Hash":<20} {"Signed"}')
            self.stdout.write('─' * 120)
            for cp in checkpoints:
                self.stdout.write(
                    f'{cp["path"]:<60} {cp.get("type",""):<15} '
                    f'{cp["hash"][:16]}...  {cp.get("signed","")}'
                )
            self.stdout.write(f'\n{len(checkpoints)} checkpoint(s)')
            last = manifest.get('last_check')
            result = manifest.get('last_result')
            if last:
                self.stdout.write(f'Last check: {last} — {result}')
            return

        elif options.get('verify'):
            passed = 0
            failed = 0
            for cp in checkpoints:
                path = cp['path']
                expected = cp['hash']
                actual = self.hash_file(path)
                if actual is None:
                    self.stderr.write(self.style.ERROR(f'MISSING  {path}'))
                    failed += 1
                elif actual != expected:
                    self.stderr.write(self.style.ERROR(
                        f'TAMPERED {path} (expected {expected[:16]}..., got {actual[:16]}...)'
                    ))
                    failed += 1
                else:
                    self.stdout.write(self.style.SUCCESS(f'OK       {path}'))
                    passed += 1
            self.stdout.write(f'\n{passed} passed, {failed} failed')
            return

        else:
            # Default: re-sign all existing checkpoints
            if not checkpoints:
                self.stdout.write('No checkpoints to sign. Use --add to add files.')
                return
            now = datetime.now(timezone.utc).isoformat()
            for cp in checkpoints:
                h = self.hash_file(cp['path'])
                if h is None:
                    self.stderr.write(self.style.WARNING(f'MISSING: {cp["path"]}'))
                    continue
                cp['hash'] = h
                cp['signed'] = now
                self.stdout.write(f'Signed: {cp["path"]} → {h[:16]}...')

        manifest['checkpoints'] = checkpoints
        manifest['last_sign'] = datetime.now(timezone.utc).isoformat()
        doc.config = manifest
        doc.save(update_fields=['config'])
        self.stdout.write(self.style.SUCCESS(
            f'\nManifest saved — {len(checkpoints)} checkpoint(s)'
        ))
