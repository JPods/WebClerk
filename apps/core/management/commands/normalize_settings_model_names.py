from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting
from apps.core.constants.model_registry import get_model_meta, get_model_meta_by_endpoint


class Command(BaseCommand):
    help = "Normalize existing Setting.model_name values to canonical singular keys."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Print changes without saving')
        parser.add_argument('--limit', type=int, default=0, help='Limit number of rows to process (0 = all)')

    def handle(self, *args, **options):
        dry = options['dry_run']
        limit = options['limit']
        qs = Setting.objects.all()
        if limit:
            qs = qs[:limit]
        updated = 0
        total = 0
        for s in qs:
            total += 1
            original = (s.model_name or '').strip().lower() if s.model_name else ''
            if not original:
                continue
            meta = get_model_meta(original) or get_model_meta_by_endpoint(original)
            if not meta:
                self.stdout.write(self.style.WARNING(f"Skip id={s.id}: unknown model_name '{original}'"))
                continue
            new_key = meta.key
            if new_key != original:
                self.stdout.write(f"id={s.id}: {original} -> {new_key}")
                if not dry:
                    s.model_name = new_key
                    s.save(update_fields=['model_name', 'dt_modified', 'version'])
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"Done. scanned={total}, updated={updated}, dry_run={dry}"))
