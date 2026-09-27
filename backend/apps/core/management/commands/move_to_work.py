"""Move working files into the work folders (Bill, 2026-09-27; common/work_folders.py).

    python manage.py move_to_work            # dry run: says what would move
    python manage.py move_to_work --apply    # stop the server and Celery first (chroma is a live database)

Moves data/bundles, data/logs, data/chroma, data/import-digest, the repo's backend/logs and the
layout state that lived inside the repo. A log already at the destination gets the old lines in front;
any other file already there is left where it is and named. Bundle payload paths need no rewrite: they were 'bundles/…' under DATA_DIR and are
'bundles/…' under WORK_DIR. Documents drop the absolute 'full' path; the key is the only path.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from common.work_folders import work_folder


class Command(BaseCommand):
    help = 'Move working files out of data/ and the repo into WORK_DIR (dry run unless --apply).'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Move the files (default: dry run).')

    def handle(self, *args, **options):
        apply = options['apply']
        data, base = Path(settings.DATA_DIR), Path(settings.BASE_DIR)
        moves = [
            (data / 'bundles', work_folder('bundles')),
            (data / 'logs', work_folder('logs')),
            (data / 'chroma', work_folder('cache', 'chroma')),
            (data / 'import-digest', work_folder('imports/digest')),
            (base / 'logs', work_folder('logs')),
        ]
        state = base / 'apps' / 'ai_assistant' / 'data'
        files = [(state / n, work_folder('state') / n) for n in ('layout_dismissals.json', 'layout_history.json')]
        moved = kept = 0
        for src, dst in moves:
            if not src.is_dir():
                continue
            for f in sorted(p for p in src.rglob('*') if p.is_file()):
                m, k = self._move(f, dst / f.relative_to(src), apply)
                moved, kept = moved + m, kept + k
            if apply:
                for d in sorted((p for p in src.rglob('*') if p.is_dir()), reverse=True):
                    if not any(d.iterdir()):
                        d.rmdir()
                if src.is_dir() and not any(src.iterdir()):
                    src.rmdir()
        for src, dst in files:
            if src.is_file():
                m, k = self._move(src, dst, apply)
                moved, kept = moved + m, kept + k
        stripped = self._strip_document_full(apply)
        verb = 'Moved' if apply else 'Would move'
        self.stdout.write(f'{verb} {moved} file(s); {kept} already at the destination (left, named above); '
                          f'{stripped} document path(s) {"lose" if apply else "would lose"} "full".')
        if not apply:
            self.stdout.write('Dry run. Stop the server and Celery, then: python manage.py move_to_work --apply')

    def _move(self, src: Path, dst: Path, apply: bool):
        if dst.exists() and src.suffix in ('.log', '.jsonl'):
            # Starting any command opens a fresh log in work/logs: the old lines go in front of it.
            if apply:
                dst.write_bytes(src.read_bytes() + dst.read_bytes())
                src.unlink()
            return 1, 0
        if dst.exists():
            self.stdout.write(f'  exists, left: {src} (at {dst})')
            return 0, 1
        if apply:
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
        return 1, 0

    def _strip_document_full(self, apply: bool) -> int:
        from apps.docs.models import Document
        docs = [d for d in Document.objects.filter(path__has_key='full').only('pk', 'path')]
        if apply:
            for d in docs:
                path = {k: v for k, v in d.path.items() if k != 'full'}
                # A derived pointer, not a business field: a raw update, no Pending.
                Document.objects.filter(pk=d.pk).update(path=path)
        return len(docs)
