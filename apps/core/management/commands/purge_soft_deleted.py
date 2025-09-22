from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from django.apps import apps
from typing import Any, Iterable, cast

class Command(BaseCommand):
    help = "Hard delete objects whose soft-delete retention has expired."

    def handle(self, *args, **options):
        now = timezone.now()
        try:
            ledger_model = apps.get_model("core", "SoftDeleteLedger")
        except LookupError:
            ledger_model = None
        if ledger_model is None:
            raise CommandError("Model core.SoftDeleteLedger not found. Ensure the model exists and is in INSTALLED_APPS.")
        due = cast(Iterable[Any], ledger_model.objects.filter(purge_at__lte=now).select_related("content_type"))
        count = 0
        with transaction.atomic():
            for entry in due:
                model = entry.content_type.model_class()
                if not model:
                    entry.delete()
                    continue
                try:
                    obj = model.objects.get(pk=entry.object_id)
                except model.DoesNotExist:  # type: ignore[attr-defined]
                    entry.delete()
                    continue
                obj.delete()
                entry.delete()
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Purged {count} soft-deleted objects."))