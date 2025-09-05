import hashlib
from pathlib import Path
from fnmatch import fnmatch
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from apps.docs.models.document import Document

README_ROOTS = [
    'readmes',  # primary docs folder
]
MD_EXTS = {'.md', '.markdown'}


def file_checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


class Command(BaseCommand):
    help = 'Sync markdown readme files into Document rows (table_name=readme, slug=derived).'

    def add_arguments(self, parser):
        parser.add_argument('--delete-missing', action='store_true', help='Delete Document rows whose source file disappeared')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--root', action='append', help='Additional root directory to scan (can repeat)')
        parser.add_argument('--modified-since', type=str, help='Only consider files modified since this UTC ISO8601 or epoch ms (e.g. 2025-09-05T12:00:00Z or 1725537600000)')
        parser.add_argument('--pattern', action='append', help='Glob pattern to include (e.g. docs/*.md). If any provided, only matching files are processed. Repeatable.')
        parser.add_argument('--force', action='store_true', help='Force update body & checksum even if unchanged (refresh metadata)')
        parser.add_argument('--max-bytes', type=int, default=0, help='If >0, skip (or truncate if --truncate) files larger than this many bytes')
        parser.add_argument('--truncate', action='store_true', help='When used with --max-bytes, truncate oversized file bodies instead of skipping')
        parser.add_argument('--allow-empty', action='store_true', help='Persist empty markdown files (default: skip)')
        parser.add_argument('--export-index', action='store_true', help='Emit a docs index JSON after sync (derived from discovered set)')
        parser.add_argument('--index-path', type=str, default='docs_index.json', help='Path for exported index (default docs_index.json)')

    def handle(self, *args, **options):
        roots = list(README_ROOTS)
        if options.get('root'):
            roots.extend(options['root'])
        dry = options.get('dry_run')
        delete_missing = options.get('delete_missing')
        force = options.get('force')
        patterns = options.get('pattern') or []
        max_bytes = options.get('max_bytes') or 0
        truncate = options.get('truncate')
        allow_empty = options.get('allow_empty')
        modified_since_raw = options.get('modified_since')
        modified_since_ts: int | None = None
        if modified_since_raw:
            # Accept epoch ms or ISO8601 ending with Z (coarse parse)
            if modified_since_raw.isdigit():
                try:
                    modified_since_ts = int(modified_since_raw)
                except ValueError:
                    raise CommandError("Invalid --modified-since epoch value")
            else:
                # naive parse: YYYY-MM-DDTHH:MM:SSZ
                try:
                    from datetime import datetime
                    dt = datetime.strptime(modified_since_raw, '%Y-%m-%dT%H:%M:%SZ')
                    modified_since_ts = int(dt.timestamp() * 1000)
                except Exception as exc:
                    raise CommandError(f"Invalid --modified-since format: {exc}")

        project_root = Path('.').resolve()

        discovered: dict[str, dict] = {}
        skipped_large = 0
        truncated_ct = 0
        skipped_empty = 0
        pattern_filtered = 0
        index_records: list[dict] = []

        for rel_root in roots:
            root_path = (project_root / rel_root).resolve()
            if not root_path.exists():
                self.stdout.write(self.style.WARNING(f"Missing root: {root_path}"))
                continue
            for path in root_path.rglob('*'):
                if not (path.is_file() and path.suffix.lower() in MD_EXTS):
                    continue
                rel = path.relative_to(project_root).as_posix()
                if patterns and not any(fnmatch(rel, p) for p in patterns):
                    pattern_filtered += 1
                    continue
                if modified_since_ts is not None:
                    try:
                        mtime_ms = int(path.stat().st_mtime * 1000)
                    except OSError:
                        continue
                    if mtime_ms < modified_since_ts:
                        continue
                try:
                    raw_bytes = path.read_bytes()
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Read error {path}: {e}"))
                    continue
                if max_bytes and len(raw_bytes) > max_bytes:
                    if truncate:
                        raw_slice = raw_bytes[:max_bytes]
                        truncated_ct += 1
                    else:
                        skipped_large += 1
                        continue
                else:
                    raw_slice = raw_bytes
                try:
                    text = raw_slice.decode('utf-8', errors='replace')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Decode error {path}: {e}"))
                    continue
                if not text.strip() and not allow_empty:
                    skipped_empty += 1
                    continue
                slug_base = slugify(path.stem)
                if slug_base == 'readme':  # include parent folder for generic README.md names
                    slug_base = slugify(path.parent.name + '-' + slug_base)
                slug = slug_base[:230]
                checksum = hashlib.sha256(raw_bytes).hexdigest()
                # first line (# Title) extraction
                first_line = text.strip().splitlines()[0] if text.strip() else ''
                title = first_line.lstrip('# ').strip() if first_line.startswith('#') else path.stem
                # Extract headings (H1/H2 only for light index)
                headings: list[str] = []
                for line in text.splitlines():
                    if line.startswith('#'):
                        # take up to second level, ignore deeper for brevity
                        if line.startswith('###'):
                            continue
                        clean = line.lstrip('# ').strip()
                        if clean:
                            headings.append(clean)
                payload = {
                    'slug': slug,
                    'name': title,
                    'description': f'Readme imported from {rel}',
                    'body': text,
                    'table_name': 'readme',
                    'data': {
                        'category': 'readme',
                        'source_path': rel,
                        'checksum': checksum,
                        'bytes': len(raw_bytes),
                        'truncated': bool(max_bytes and len(raw_bytes) > max_bytes and truncate),
                        'headings': headings[:50],
                    },
                    'security_level': 0,
                }
                index_records.append({
                    'slug': slug,
                    'title': title,
                    'path': rel,
                    'bytes': len(raw_bytes),
                    'headings': headings[:50],
                })
                # handle slug collision inside same scan (rare)
                base_for_collision = slug
                idx = 2
                while slug in discovered:
                    suffix = f'-{idx}'
                    slug = (base_for_collision[: 230 - len(suffix)] + suffix)
                    payload['slug'] = slug
                    idx += 1
                discovered[slug] = payload

        existing = {d.slug: d for d in Document.objects.filter(table_name='readme')}
        created = 0
        updated = 0
        unchanged = 0
        with transaction.atomic():
            for slug, payload in discovered.items():
                doc = existing.get(slug)
                if not doc:
                    if dry:
                        self.stdout.write(self.style.NOTICE(f"[DRY] create {slug}"))
                        continue
                    Document.objects.create(**payload)
                    created += 1
                    continue
                new_checksum = payload['data']['checksum']
                old_checksum = (doc.data or {}).get('checksum') if isinstance(doc.data, dict) else None
                body_changed = doc.body != payload['body']
                if force or new_checksum != old_checksum or body_changed:
                    if dry:
                        self.stdout.write(self.style.NOTICE(f"[DRY] update {slug}"))
                        continue
                    for k, v in payload.items():
                        setattr(doc, k, v)
                    doc.save()
                    updated += 1
                else:
                    unchanged += 1

            if delete_missing:
                missing_slugs = set(existing.keys()) - set(discovered.keys())
                for slug in missing_slugs:
                    if dry:
                        self.stdout.write(self.style.WARNING(f"[DRY] delete missing {slug}"))
                        continue
                    existing[slug].delete()
                    self.stdout.write(self.style.WARNING(f"Deleted missing readme {slug}"))

        self.stdout.write(self.style.SUCCESS(
            "Sync complete. Created={c} Updated={u} Unchanged={n} Discovered={d} SkippedLarge={sl} Truncated={tr} SkippedEmpty={se} PatternFiltered={pf}".format(
                c=created, u=updated, n=unchanged, d=len(discovered), sl=skipped_large, tr=truncated_ct, se=skipped_empty, pf=pattern_filtered
            )
        ))
        if options.get('export_index'):
            try:
                import json
                out_path = Path(options['index_path'])
                with out_path.open('w', encoding='utf-8') as fh:
                    json.dump(index_records, fh, indent=2)
                self.stdout.write(self.style.SUCCESS(f"Wrote index {out_path} ({len(index_records)} docs)"))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"Index export failed: {exc}"))