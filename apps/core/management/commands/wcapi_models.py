from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = "List installed Django models as dotted paths and canonical model keys."

    def handle(self, *args, **options):
        for Model in apps.get_models():
            app_label = Model._meta.app_label
            dotted = f"{app_label}.{Model.__name__}"
            key = Model._meta.model_name
            self.stdout.write(f"{key:24s} -> {dotted}")