from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

class Command(BaseCommand):
    help = "Seed Setting rows for wcapi per model (disabled by default)."

    def handle(self, *args, **options):
        Setting = apps.get_model("core", "Setting")
        created = 0
        with transaction.atomic():
            for Model in apps.get_models():
                key = Model._meta.model_name
                if not Setting.objects.filter(purpose="wcapi", model_name=key).exists():
                    Setting.objects.create(
                        purpose="wcapi",
                        model_name=key,
                        is_active=False,
                        data={"allow_fields": None, "rules": {}},
                    )
                    created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} wcapi Setting rows"))