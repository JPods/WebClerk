from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction
from django.utils import timezone

from common.models import BaseModel

class Command(BaseCommand):
    help = "Refresh keyword lists for BaseModel subclasses where metadata.flags.keywords_pending is True."

    def add_arguments(self, parser):
        parser.add_argument('--model', help="Limit to single app_label.ModelName")
        parser.add_argument('--batch-size', type=int, default=200, help='Objects processed per DB write batch')
        parser.add_argument('--limit', type=int, default=0, help='Max objects overall (0 = no limit)')
        parser.add_argument('--dry-run', action='store_true', help='Show counts but do not write changes')
        parser.add_argument('--verbose-objects', action='store_true', help='List each processed object id')

    def handle(self, *args, **opts):
        target = (opts.get('model') or '').lower()
        batch_size = opts['batch_size']
        limit = opts['limit']
        dry_run = opts['dry_run']
        verbose_objs = opts['verbose_objects']

        total_processed = 0
        total_models = 0
        started = timezone.now()

        for model in apps.get_models():
            if not issubclass(model, BaseModel) or model is BaseModel:
                continue
            label = f"{model._meta.app_label}.{model.__name__}".lower()
            if target and label != target:
                continue
            qs = getattr(model.objects, 'keyword_pending', lambda: None)()
            if qs is None:
                continue
            # Restrict selected fields to reduce payload
            qs = qs.only('id', 'metadata', 'refs')
            if limit:
                qs = qs[:max(limit - total_processed, 0)]
            pending_count = qs.count()
            if pending_count == 0:
                continue
            total_models += 1
            self.stdout.write(f"{label}: pending={pending_count}")
            if dry_run:
                total_processed += pending_count
                if limit and total_processed >= limit:
                    break
                continue

            buffer = []
            for obj in qs.iterator(chunk_size=batch_size):
                # Compute keywords in-memory without calling save()
                obj.update_keywords()  # clears flag & sets keywords
                buffer.append(obj)
                total_processed += 1
                if verbose_objs:
                    self.stdout.write(f"  processed id={obj.pk}")
                if len(buffer) >= batch_size:
                    self._bulk_flush(model, buffer)
                if limit and total_processed >= limit:
                    break
            if buffer:
                self._bulk_flush(model, buffer)
            if limit and total_processed >= limit:
                break

        duration = (timezone.now() - started).total_seconds()
        self.stdout.write(self.style.SUCCESS(
            f"Completed: models={total_models} objects={total_processed} time={duration:.2f}s dry_run={dry_run}"))

    def _bulk_flush(self, model, buffer):
        # Persist refs & metadata only (avoid save() side-effects like re-marking pending)
        with transaction.atomic():
            model.objects.bulk_update(buffer, ['refs', 'metadata'])
        buffer.clear()
