# python manage.py fix_basemodel_fields
from django.core.management.base import BaseCommand
from django.apps import apps
import uuid
from common.models import BaseModel, default_metadata, default_refs, default_prefs

class Command(BaseCommand):
    help = "Ensure all BaseModel fields are populated for all models inheriting BaseModel"

    def handle(self, *args, **kwargs):
        # Find all models that inherit from BaseModel
        for model in apps.get_models():
            if issubclass(model, BaseModel) and model is not BaseModel:
                self.stdout.write(f"Checking {model.__name__}...")
                for obj in model.objects.all():
                    changed = False
                    if not getattr(obj, 'uuid', None):
                        obj.uuid = uuid.uuid4()
                        changed = True
                    if not getattr(obj, 'metadata', None):
                        obj.metadata = default_metadata()
                        changed = True
                    if not getattr(obj, 'refs', None):
                        obj.refs = default_refs()
                        changed = True
                    if not getattr(obj, 'prefs', None):
                        obj.prefs = default_prefs()
                        changed = True
                    # Add ida field if missing or empty
                    if hasattr(obj, 'ida') and not getattr(obj, 'ida', None):
                        obj.ida = str(obj.id)
                        changed = True
                    if changed:
                        obj.save()
                        self.stdout.write(f"Updated {model.__name__} id={obj.id}")