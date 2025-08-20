from django.apps import apps
from django.db import models
from django.core.management.base import BaseCommand
import json

class Command(BaseCommand):
    help = "Build VIEW_CONFIG for all models and print as JSON"

    def build_view_config(self, authorities=('user', 'admin', 'superadmin')):
        view_config = {}
        for authority in authorities:
            view_config[authority] = {}
            for app_config in apps.get_app_configs():
                for model in app_config.get_models():
                    model_name = model.__name__
                    # List: id + all CharFields
                    list_fields = ['id'] + [
                        field.name for field in model._meta.fields
                        if isinstance(field, models.CharField)
                    ]
                    # Detail: all fields
                    detail_fields = [field.name for field in model._meta.fields]
                    view_config[authority][model_name] = {
                        'list': list_fields,
                        'detail': detail_fields,
                    }
        return view_config

    def handle(self, *args, **options):
        config = self.build_view_config()
        print(json.dumps(config, indent=2))