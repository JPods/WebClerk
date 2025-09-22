from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.core.models import SoftDeleteLedger

class Command(BaseCommand):
    help = "Hard delete objects whose soft-delete retention has expired."

    def handle(self, *args, **options):
        now = timezone.now()
        due = SoftDeleteLedger.objects.filter(purge_at__lte=now).select_related("content_type")
        count = 0
        with transaction.atomic():
            for entry in due:
                model = entry.content_type.model_class()
                if not model:
                    entry.delete()
                    continue
                try:
                    obj = model.objects.get(pk=entry.object_id)
                except model.DoesNotExist:  # type: ignore
                    entry.delete()
                    continue
                # Hard delete target, then remove ledger row
                obj.delete()
                entry.delete()
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Purged {count} soft-deleted objects."))