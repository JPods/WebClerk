from django.core.management.base import BaseCommand
from apps.core.constants.model_registry import VALID_MODEL_NAMES, get_model_meta
from apps.core.models.setting import Setting

class Command(BaseCommand):
    help = 'Create workbench fields settings for all models'

    def handle(self, *args, **options):
        for model_name in VALID_MODEL_NAMES:
            meta = get_model_meta(model_name)
            if not meta:
                continue
            model = meta.import_model()
            fields = model._meta.get_fields()
            field_names = [f.name for f in fields]
            list_fields = ['id']
            char_fields = [f.name for f in fields if f.__class__.__name__ == 'CharField'][:3]
            list_fields += char_fields
            detail_fields = field_names
            data = {
                'list': list_fields,
                'detail': detail_fields
            }
            setting, created = Setting.objects.get_or_create(
                model_target=model_name,
                purpose="workbench_fields",
                defaults={'data': data}
            )
            self.stdout.write(f'{"Created" if created else "Updated"} setting for {model_name}')
